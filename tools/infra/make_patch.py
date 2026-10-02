#!/usr/bin/env python3
"""Export a component worktree as a tree-shaped patch set.

See ``docs/spec/component-patching.md`` (v5 spec, effective 2026-09-23):

* one patch per upstream file -- ``patches/<upstream-relative-path>.patch``
* patch bodies are **raw** ``git diff`` output (no mbox headers, no numbering)
* ``components/<name>/series`` lists every patch path (relative to ``patches/``),
  sorted lexicographically; it lives **outside** ``patches/`` so that the
  wholesale wipe below cannot destroy it, and so ``patches/`` stays a pure
  mirror of the upstream tree

The worktree may be dirty: the export is the *net* difference between the
pinned base commit and the current working tree (``git diff <base>``), so a
path that was created and later modified still yields exactly one patch whose
content is the final state.

§6.2 (idempotent write): patches are only rewritten when their content actually
changes, preserving mtimes and avoiding needless index/header refreshes.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA1 = re.compile(r"^[0-9a-f]{40}$")
INDEX_RE = re.compile(r"^index [0-9a-f]+\.\.[0-9a-f]+.*$", re.MULTILINE)


def load_manifest() -> dict:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        return tomllib.load(stream)


def git(*args: str, cwd: Path, check: bool = True) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=check,
    ).stdout


def _normalize_index(text: str) -> str:
    """Strip the ``index`` line for comparison.

    The ``index`` line contains blob hashes whose abbreviation length varies
    with ``core.abbrev``.  Stripping it lets us compare the actual diff content
    (headers + hunks) without false negatives from hash abbreviation changes.
    """
    return re.sub(r"^index [0-9a-f]+\.\.[0-9a-f]+.*\n", "", text, flags=re.MULTILINE)


def changed_paths(source: Path, commit: str) -> list[str]:
    # Intent-to-add so newly created (untracked) files show up in `git diff`.
    subprocess.run(["git", "-C", str(source), "add", "-A", "-N"], check=True)
    out = git("diff", "--name-only", commit, cwd=source)
    return [line for line in out.splitlines() if line.strip()]


def export(
    source: Path,
    commit: str,
    rel_paths: list[str],
    patches_dir: Path,
) -> tuple[list[str], int]:
    """Export patches for *rel_paths* into *patches_dir*.

    Returns ``(series_entries, num_skipped_unchanged)``.
    §6.2: only writes when content differs from the existing file on disk.
    Comparison normalizes the ``index`` line to handle varying ``core.abbrev``.
    """
    skipped = 0
    written = 0
    for rel in rel_paths:
        body = git("diff", commit, "--", rel, cwd=source)
        target = patches_dir / f"{rel}.patch"
        # §6.2 idempotent write: compare before writing
        # Normalize index line for comparison (core.abbrev varies).
        if target.is_file() and _normalize_index(target.read_text()) == _normalize_index(body):
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        written += 1
    series = sorted(f"{rel}.patch" for rel in rel_paths)
    print(f"make-patch: {written} written, {skipped} unchanged (skipped)")
    return series, skipped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a component worktree as a tree-shaped patch set."
    )
    parser.add_argument("component", help="component name from components.lock.toml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the patches that would be written, without writing anything",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    components = {c.get("name"): c for c in manifest.get("component", [])}
    component = components.get(args.component)
    if component is None:
        known = ", ".join(sorted(n for n in components if n)) or "none"
        raise SystemExit(f"make-patch: unknown component {args.component!r} (known: {known})")

    commit = component.get("commit", "")
    if not SHA1.fullmatch(commit):
        raise SystemExit(
            f"make-patch: component {args.component} has no pinned commit; "
            "accept its baseline ADR first"
        )

    source = ROOT / manifest.get("work_root", ".work") / "source" / args.component
    if not (source / ".git").exists():
        raise SystemExit(f"make-patch: missing source {source}; run make fetch")

    if subprocess.run(
        ["git", "-C", str(source), "merge-base", "--is-ancestor", commit, "HEAD"],
    ).returncode != 0:
        raise SystemExit(
            f"make-patch: {args.component} HEAD does not descend from pinned commit "
            f"({commit[:12]})"
        )

    series_path = ROOT / component["patch_series"]
    patches_dir = ROOT / component["patch_dir"]

    paths = changed_paths(source, commit)
    if not paths:
        print(f"make-patch: {args.component} has no changes against {commit[:12]}")
        return 0

    if args.dry_run:
        for rel in sorted(paths):
            print(f"make-patch: would write patches/{rel}.patch")
        return 0

    # Remove stale patches (paths no longer changed).
    expected_names = {f"{rel}.patch" for rel in paths}
    if patches_dir.exists():
        for entry in sorted(patches_dir.rglob("*.patch")):
            rel_name = str(entry.relative_to(patches_dir))
            if rel_name not in expected_names:
                entry.unlink()
                print(f"make-patch: removed stale patch {rel_name}")

    patches_dir.mkdir(parents=True, exist_ok=True)
    series, _skipped = export(source, commit, paths, patches_dir)
    series_path.write_text("\n".join(series) + "\n")
    print(f"make-patch: {args.component} wrote {len(series)} patches to {patches_dir}")
    print(f"make-patch: series {series_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())