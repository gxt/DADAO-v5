#!/usr/bin/env python3
"""Check the ``index`` blob hash of ``new file mode`` patches (ISS-119).

For a ``new file mode`` patch, ``git diff`` emits ``index 0000000..<hash>``
whose ``<hash>`` is the blob hash of the newly added file.  Because the whole
file content is contained in the patch (the ``+`` lines of its single hunk),
that hash can be recomputed **hermetically** from the patch alone: rebuild the
content, feed it to ``git hash-object --stdin`` and compare with the literal
hash.  A stale literal (e.g. the hunk was edited without regenerating the
``index`` line) is a patch-hygiene defect that ``git apply`` tolerates
silently, hence this dedicated checker.

Scope / limits:

* Only ``new file mode`` patches (empty old-object hash) are asserted.
  **Modification** patches carry an old-object hash that cannot be derived
  from the hunk alone; they are deliberately **skipped** (their content
  consistency is covered by assertion ⑥ of ``check_patch_tree.py``).
* The literal hash may be abbreviated (git's ``core.abbrev``); the check is a
  prefix test against the full 40-hex blob hash.
* Reusable checker: with no path arguments it walks every enabled component's
  ``patch_dir`` from ``manifests/components.lock.toml``; explicit file/dir
  arguments override that (used by the evidence script for temp-copy
  injection).

``--fix`` rewrites only the *new* hash of mismatching new-file patches,
preserving the zero-run length and the trailing mode field, so the result is
byte-identical to a fresh ``git diff`` abbreviation.  It never touches hunk
content.  Without ``--fix`` the tool is read-only.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ``index <old>..<new>[ <mode>]`` — the trailing mode field is optional.
INDEX_RE = re.compile(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)(?: (\d+))?$")
# Matches the index line of a new-file patch for the ``--fix`` rewrite.
NEW_INDEX_RE = re.compile(r"^(index (0+)\.\.)([0-9a-f]+)(.*)$", re.MULTILINE)
HUNK_RE = re.compile(r"^@@")
# Header lines (never hunk content lines, which begin with +/-/space).
NEW_FILE_MODE_RE = re.compile(r"^new file mode \d+$", re.MULTILINE)
BINARY_RE = re.compile(r"^GIT binary patch$", re.MULTILINE)


def load_manifest() -> dict:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        return tomllib.load(stream)


def enabled_patch_dirs() -> list[Path]:
    manifest = load_manifest()
    dirs: list[Path] = []
    for component in manifest.get("component", []):
        if not component.get("enabled"):
            continue
        patch_dir = component.get("patch_dir")
        if patch_dir:
            dirs.append(ROOT / patch_dir)
    return dirs


def collect_patches(paths: list[str]) -> list[Path]:
    """Expand the CLI paths (files or dirs) into a sorted list of *.patch."""
    patches: list[Path] = []
    if paths:
        for raw in paths:
            path = Path(raw)
            if not path.exists():
                raise SystemExit(f"check-index-blobs: path not found: {raw}")
            if path.is_dir():
                patches.extend(path.rglob("*.patch"))
            else:
                patches.append(path)
        return sorted(set(p.resolve() for p in patches))
    for patch_dir in enabled_patch_dirs():
        if patch_dir.is_dir():
            patches.extend(patch_dir.rglob("*.patch"))
    return sorted(set(p.resolve() for p in patches))


def parse_index(text: str) -> tuple[str, str] | None:
    """Return ``(old_hash, new_hash)`` of the first index line, or None."""
    for line in text.splitlines():
        match = INDEX_RE.match(line)
        if match:
            return match.group(1), match.group(2)
    return None


def reconstruct_content(text: str) -> str:
    """Rebuild the added file's content from the single new-file hunk."""
    parts: list[str] = []
    trailing_newline = True
    in_hunk = False
    for line in text.splitlines():
        if HUNK_RE.match(line):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("\\"):  # "\ No newline at end of file"
            trailing_newline = False
        elif line.startswith("+"):
            parts.append(line[1:])
    body = "\n".join(parts)
    if parts and trailing_newline:
        body += "\n"
    return body


def blob_hash(content: str) -> str:
    result = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=content.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"check-index-blobs: git hash-object failed: {result.stderr.decode()}")
    return result.stdout.decode().strip()


def check_patch(patch: Path, fix: bool, verbose: bool) -> str | None:
    """Return an error string, or None when OK / skipped.

    Skipped (non new-file) patches return None and are counted separately by
    the caller via :func:`is_new_file`.
    """
    text = patch.read_text(encoding="utf-8")
    index = parse_index(text)
    if index is None:
        return f"{patch}: new file mode patch without an index line"
    old_hash, new_hash = index
    if set(old_hash) != {"0"}:
        return f"{patch}: new file mode patch with non-empty old hash {old_hash!r}"
    if BINARY_RE.search(text):
        return f"{patch}: binary new-file patches are not supported by this checker"
    content = reconstruct_content(text)
    computed = blob_hash(content)
    if verbose:
        status = "OK" if computed.startswith(new_hash) else "MISMATCH"
        print(f"check-index-blobs: {status} {patch}: literal={new_hash} computed={computed}")
    if computed.startswith(new_hash):
        return None
    if fix:
        fixed = computed[: len(new_hash)]
        new_text, count = NEW_INDEX_RE.subn(
            lambda m: f"{m.group(1)}{fixed}{m.group(4)}", text, count=1
        )
        if count != 1:
            return f"{patch}: --fix could not locate the index line"
        patch.write_text(new_text, encoding="utf-8")
        print(f"check-index-blobs: FIXED {patch}: {new_hash} -> {fixed}")
        return None
    return (
        f"{patch}: index new-hash {new_hash} does not match content blob "
        f"{computed[: len(new_hash)]} (full {computed})"
    )


def is_new_file(text: str) -> bool:
    return NEW_FILE_MODE_RE.search(text) is not None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check index blob hashes of new-file patches (ISS-119)."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="patch files/dirs to check (default: every enabled component)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite the new-hash of mismatching new-file patches in place",
    )
    parser.add_argument("--verbose", action="store_true", help="print every checked patch")
    args = parser.parse_args()

    patches = collect_patches(args.paths)
    if not patches:
        print("check-index-blobs: no patches found")
        return 0

    errors: list[str] = []
    new_file_count = 0
    skipped = 0
    for patch in patches:
        text = patch.read_text(encoding="utf-8")
        if not is_new_file(text):
            skipped += 1
            continue
        new_file_count += 1
        error = check_patch(patch, fix=args.fix, verbose=args.verbose)
        if error is not None:
            errors.append(error)

    for error in errors:
        print(f"check-index-blobs: {error}", file=sys.stderr)
    if errors:
        print(
            f"check-index-blobs: {len(errors)} mismatch(es) "
            f"({new_file_count} new-file patch(es), {skipped} modification patch(es) skipped)",
            file=sys.stderr,
        )
        return 1
    verb = "fixed" if args.fix else "OK"
    print(
        f"check-index-blobs: {new_file_count} new-file patch(es) {verb}; "
        f"{skipped} modification patch(es) skipped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
