#!/usr/bin/env python3
"""Export a component worktree as a tree-shaped patch set.

See ``docs/spec/component-patching.md`` (v5 spec, effective 2026-09-23):

* one patch per upstream file -- ``patches/<upstream-relative-path>.patch``
* patch bodies are **raw** ``git diff`` output (no mbox headers, no numbering)
* ``patches/series`` lists every patch path (relative to ``patches/``), sorted
  lexicographically

The worktree may be dirty: the export is the *net* difference between the
pinned base commit and the current working tree (``git diff <base>``), so a
path that was created and later modified still yields exactly one patch whose
content is the final state.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA1 = re.compile(r"^[0-9a-f]{40}$")


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


def changed_paths(source: Path, commit: str) -> list[str]:
    # Intent-to-add so newly created (untracked) files show up in `git diff`.
    subprocess.run(["git", "-C", str(source), "add", "-A", "-N"], check=True)
    out = git("diff", "--name-only", commit, cwd=source)
    return [line for line in out.splitlines() if line.strip()]


def export(source: Path, commit: str, patches_dir: Path) -> list[str]:
    paths = changed_paths(source, commit)
    for rel in paths:
        body = git("diff", commit, "--", rel, cwd=source)
        target = patches_dir / f"{rel}.patch"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    return sorted(f"{rel}.patch" for rel in paths)


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
    patches_dir = series_path.parent

    paths = changed_paths(source, commit)
    if not paths:
        print(f"make-patch: {args.component} has no changes against {commit[:12]}")
        return 0

    if args.dry_run:
        for rel in sorted(paths):
            print(f"make-patch: would write patches/{rel}.patch")
        return 0

    # Replace the previous patch set wholesale: stale patches must not survive.
    if patches_dir.exists():
        for entry in patches_dir.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    patches_dir.mkdir(parents=True, exist_ok=True)

    series = export(source, commit, patches_dir)
    series_path.write_text("\n".join(series) + "\n")
    print(f"make-patch: {args.component} wrote {len(series)} patches to {patches_dir}")
    print(f"make-patch: series {series_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
