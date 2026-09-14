#!/usr/bin/env python3
"""Export a component worktree as an ordered patch series.

v5 tooling for what DADAO-0628 produced by hand: given a component worktree
with commits stacked on top of its pinned base commit, run ``git format-patch``
over ``<base>..HEAD`` into ``components/<name>/patches/`` and rewrite the
``series`` manifest with the generated file names in order.

Only the series *format* is shared with DADAO-0628 (an ordered ``series`` list
of numbered ``.patch`` files); no patch bodies or scripts are copied.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA1 = re.compile(r"^[0-9a-f]{40}$")


def load_manifest() -> dict:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        return tomllib.load(stream)


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def format_patch(source: Path, commit: str, out_dir: Path) -> list[str]:
    return [
        Path(line).name
        for line in git(
            "format-patch", "--no-signature", "-o", str(out_dir), f"{commit}..HEAD",
            cwd=source,
        ).splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a component's ordered patch series from its worktree."
    )
    parser.add_argument("component", help="component name from components.lock.toml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the patches that would be generated without writing anything",
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

    head = git("rev-parse", "HEAD", cwd=source).strip()
    if head == commit:
        print(f"make-patch: {args.component} has no commits on top of {commit[:12]}")
        return 0
    if subprocess.run(
        ["git", "-C", str(source), "merge-base", "--is-ancestor", commit, "HEAD"],
    ).returncode != 0:
        raise SystemExit(
            f"make-patch: {args.component} HEAD ({head[:12]}) does not descend from "
            f"pinned commit ({commit[:12]})"
        )

    series_path = ROOT / component["patch_series"]
    out_dir = series_path.parent

    if args.dry_run:
        # Render into a scratch directory so --dry-run leaves no trace; the
        # patches are only needed to derive their ordered file names.
        with tempfile.TemporaryDirectory() as scratch:
            generated = format_patch(source, commit, Path(scratch))
            if not generated:
                print(f"make-patch: {args.component} produced no patches")
                return 0
            for name in generated:
                print(f"make-patch: would write {name}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    generated = format_patch(source, commit, out_dir)
    if not generated:
        print(f"make-patch: {args.component} produced no patches")
        return 0

    series_path.write_text("\n".join(generated) + "\n")
    print(f"make-patch: {args.component} wrote {len(generated)} patches to {out_dir}")
    print(f"make-patch: series {series_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
