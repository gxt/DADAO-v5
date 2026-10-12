#!/usr/bin/env python3
"""Apply only gem5's tree-shaped patch series (Process-01 E5)."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "infra"))
from apply_series import (  # noqa: E402
    expected_tree,
    git,
    head_matches_patches,
    worktree_clean,
)


def main() -> int:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    matches = [c for c in manifest["component"] if c["name"] == "gem5"]
    if len(matches) != 1 or not matches[0].get("enabled"):
        raise SystemExit("apply-gem5: gem5 must be enabled exactly once")
    component = matches[0]
    base = component["commit"]
    source = ROOT / manifest.get("work_root", ".work") / "source" / "gem5"
    if not (source / ".git").exists():
        raise SystemExit("apply-gem5: missing source; run make fetch-gem5")
    series = ROOT / component["patch_series"]
    patches = [
        ROOT / component["patch_dir"] / line.strip()
        for line in series.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not patches:
        raise SystemExit("apply-gem5: empty series is not a valid gem5 baseline")
    head = git("rev-parse", "HEAD", cwd=source).stdout.strip()
    if head_matches_patches(source, base, patches):
        if not worktree_clean(source):
            raise SystemExit("apply-gem5: patched source is dirty; refusing")
        print("apply-gem5: already applied (base+1, matching tree)")
        return 0
    if head != base or not worktree_clean(source):
        raise SystemExit(
            "apply-gem5: source must be clean at the pinned base or at "
            "base+1 matching the patch set"
        )
    for patch in patches:
        if git("apply", "--check", "--reverse", str(patch), cwd=source,
               check=False).returncode == 0:
            continue
        check = git("apply", "--check", str(patch), cwd=source, check=False)
        if check.returncode:
            raise SystemExit(
                f"apply-gem5: {patch.relative_to(ROOT)} does not apply: "
                f"{check.stderr.strip()}"
            )
        git("apply", str(patch), cwd=source)
    git("add", "-A", cwd=source)
    if git("write-tree", cwd=source).stdout.strip() != expected_tree(
        source, base, patches
    ):
        raise SystemExit("apply-gem5: staged tree does not match patch series")
    git("commit", "-q", "-m", "dadao: gem5 patch series", cwd=source)
    print("apply-gem5: applied and committed gem5 patch series")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
