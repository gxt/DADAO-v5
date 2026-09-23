#!/usr/bin/env python3
"""Show locked component/reference state against the local checkouts.

Components are read from ``manifests/components.lock.toml`` and references from
``manifests/references.lock.toml``. Reference ``path`` entries are project
relative (e.g. ``.dadao/DADAO-0628``); each existing worktree is queried with
``git rev-parse HEAD`` and ``git status --porcelain``.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict:
    with (ROOT / "manifests" / name).open("rb") as stream:
        return tomllib.load(stream)


def git_value(path: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def main() -> int:
    components = load("components.lock.toml").get("component", [])
    references = load("references.lock.toml").get("reference", [])

    print("Components")
    for component in components:
        commit = component.get("commit") or "UNSET"
        state = "enabled" if component.get("enabled") else "disabled"
        print(f"  {component['name']:8} {state:8} {commit}")

    print("References")
    for reference in references:
        path = ROOT / reference["path"]
        if not path.exists():
            print(f"  {reference['id']:16} missing dirty=-   -")
            continue
        actual = git_value(path, "rev-parse", "HEAD")
        dirty_text = git_value(path, "status", "--porcelain=v1")
        dirty = len(dirty_text.splitlines()) if dirty_text not in {"", "unavailable"} else 0
        match = "MATCH" if actual == reference["head"] else "DRIFT"
        print(f"  {reference['id']:16} {match:7} dirty={dirty:<3} {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
