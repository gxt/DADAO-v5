#!/usr/bin/env python3
"""Spec read-only guard: verify read-only spec volumes against a sha256 lock.

``manifests/spec-readonly.lock.toml`` pins the ``sha256`` of every read-only
spec volume (``spec/SimRISC-*``, ``spec/DADAO-1x``/``DADAO-2x``,
``spec/Toolchain-01``, ``spec/Machine-01``).  Those volumes are read-only
inputs and must not be modified without the user's explicit, prior
authorization (recorded verbatim) and a lock update in the *same* change.
This gate makes that rule mechanical: it recomputes each locked file's
``sha256`` and fails closed on any mismatch or missing file.

See ``spec/Process-06-spec目录保护规范.md`` (§5).  Read-only: never writes.

``--root DIR`` checks another tree (e.g. a temp copy used for injection
self-tests); the lock is read from ``<root>/manifests/spec-readonly.lock.toml``
and every locked ``path`` is resolved relative to ``<root>``.  Default root is
the repository root.

Exit code: non-zero on any mismatch / missing file / malformed lock.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_REL = "manifests/spec-readonly.lock.toml"
SPEC_PREFIX = "spec/"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_entries(lock_path: Path, errors: list[str]) -> list[tuple[str, str, str]]:
    """Parse the lock into ``(path, sha256, group)`` entries, collecting errors."""
    if not lock_path.is_file():
        errors.append(f"lock file not found: {lock_path}")
        return []
    try:
        with lock_path.open("rb") as stream:
            data = tomllib.load(stream)
    except Exception as exc:  # noqa: BLE001 - report any parse failure verbatim
        errors.append(f"cannot parse {lock_path}: {exc}")
        return []

    if data.get("format") != 1:
        errors.append(f"{LOCK_REL}: unsupported format {data.get('format')!r} (expected 1)")

    entries = data.get("spec", [])
    if not isinstance(entries, list) or not entries:
        errors.append(f"{LOCK_REL}: no [[spec]] entries")
        return []

    parsed: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for i, entry in enumerate(entries, 1):
        path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not path:
            errors.append(f"{LOCK_REL}: [[spec]] #{i} missing 'path'")
            continue
        if not isinstance(digest, str) or not digest:
            errors.append(f"{LOCK_REL}: [[spec]] #{i} ({path}) missing 'sha256'")
            continue
        if path in seen:
            errors.append(f"{LOCK_REL}: duplicate path {path!r}")
            continue
        seen.add(path)
        if not path.startswith(SPEC_PREFIX):
            errors.append(f"{LOCK_REL}: {path!r} is not under {SPEC_PREFIX!r}")
            continue
        parsed.append((path, digest, entry.get("group", "")))
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify read-only spec volumes against a sha256 lock (SPEC-119t)."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="root dir to check (default: repo root); lock read from <root>/" + LOCK_REL,
    )
    parser.add_argument("--verbose", action="store_true", help="print every checked volume")
    parser.add_argument("--list", action="store_true", help="print the locked volume paths and exit")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-spec-readonly: ERROR: --root directory does not exist: {root}", file=sys.stderr)
        return 1

    lock_path = root / LOCK_REL
    errors: list[str] = []
    entries = load_entries(lock_path, errors)
    if errors:
        for error in errors:
            print(f"check-spec-readonly: {error}", file=sys.stderr)
        print(f"check-spec-readonly: FAIL ({len(errors)} lock error(s))", file=sys.stderr)
        return 1

    if args.list:
        for path, _digest, group in entries:
            print(f"{path}\t{group}")
        return 0

    for path, literal, _group in entries:
        target = root / path
        if not target.is_file():
            errors.append(f"MISSING {path}: expected file not found under {root}")
            continue
        computed = sha256_file(target)
        if computed == literal:
            if args.verbose:
                print(f"check-spec-readonly: OK {path}: literal={literal} computed={computed}")
        else:
            if args.verbose:
                print(f"check-spec-readonly: MISMATCH {path}: literal={literal} computed={computed}")
            errors.append(
                f"MISMATCH {path}: expected={literal} actual={computed} "
                "(modify requires prior user authorization + lock update, see Process-06 §5)"
            )

    if errors:
        for error in errors:
            print(f"check-spec-readonly: {error}", file=sys.stderr)
        print(
            f"check-spec-readonly: FAIL ({len(errors)}/{len(entries)} volume(s) mismatched or missing)",
            file=sys.stderr,
        )
        return 1

    print(f"check-spec-readonly: {len(entries)} read-only spec volume(s) OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
