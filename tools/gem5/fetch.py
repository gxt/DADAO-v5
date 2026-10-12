#!/usr/bin/env python3
"""Fetch only the pinned gem5 component, leaving other components untouched."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "infra"))
from fetch import has_commit, sync_mirror  # noqa: E402
from apply_series import head_matches_patches  # noqa: E402


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(
            f"fetch-gem5: git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def main() -> int:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    matches = [c for c in manifest["component"] if c["name"] == "gem5"]
    if len(matches) != 1 or not matches[0].get("enabled"):
        raise SystemExit("fetch-gem5: gem5 must be enabled exactly once")
    component = matches[0]
    commit = component["commit"]
    shallow_ref = component["shallow_ref"]
    mirror = ROOT / ".cache" / "gem5.git"
    source = ROOT / manifest.get("work_root", ".work") / "source" / "gem5"

    mirror.parent.mkdir(parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    sync_mirror(
        mirror,
        component["repository"],
        commit,
        shallow=component.get("shallow", False),
        shallow_ref=shallow_ref,
    )
    if not has_commit(mirror, commit):
        raise SystemExit(f"fetch-gem5: pinned commit {commit} is unavailable")
    tag_commit = git(mirror, "rev-parse", f"refs/tags/{shallow_ref}^{{commit}}")
    if tag_commit != commit:
        raise SystemExit(
            f"fetch-gem5: tag {shallow_ref} resolves to {tag_commit}, not {commit}"
        )

    if not source.exists():
        subprocess.run(
            ["git", "clone", "--no-checkout", str(mirror), str(source)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(source), "checkout", "--detach", commit],
            check=True,
        )
    elif not (source / ".git").exists():
        raise SystemExit(f"fetch-gem5: {source} exists but is not a worktree")

    if git(source, "status", "--porcelain"):
        raise SystemExit("fetch-gem5: existing gem5 source is dirty; refusing")
    head = git(source, "rev-parse", "HEAD")
    if head != commit:
        series = ROOT / component["patch_series"]
        patches = [
            ROOT / component["patch_dir"] / line.strip()
            for line in series.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        is_descendant = subprocess.run(
            ["git", "-C", str(source), "merge-base", "--is-ancestor", commit, head]
        ).returncode == 0
        if not patches or not is_descendant or not head_matches_patches(
            source, commit, patches
        ):
            raise SystemExit(
                f"fetch-gem5: HEAD {head} is not pinned base or "
                "base+1 matching the gem5 patch set"
            )
    print(f"fetch-gem5: {shallow_ref}={commit}; clean source HEAD={head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
