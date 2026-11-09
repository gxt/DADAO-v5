#!/usr/bin/env python3
"""Declarations of submodule patch sets (manifest ``submodule_patch``).

See ``docs/Process-01-组件补丁组织与构建编排.md`` §14 (rev. 2026-11-09): a
component may carry v5 patch sets for the submodules of its upstream checkout,
declared in ``manifests/components.lock.toml`` as::

    [[component]]
    name = "chipyard"
    ...
    [[component.submodule_patch]]
    path = "generators/testchipip"
    patch_dir = "components/chipyard/submodules/testchipip/patches"
    patch_series = "components/chipyard/submodules/testchipip/series"

The pinned base commit of such a set is **not** repeated here: it is the
``commit`` recorded for the same ``path`` in the component's
``submodule_lock`` (``manifests/chipyard-submodules.lock.toml``), so the two
cannot drift apart.

This module is the single reader of that schema; ``apply_series.py``,
``check_patch_tree.py``, ``make_patch.py`` and ``manifest_check.py`` all use it
instead of re-parsing the manifest (the four used to disagree otherwise).
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA1 = re.compile(r"^[0-9a-f]{40}$")


def load_lock(relpath: str) -> dict:
    path = ROOT / relpath
    if not path.is_file():
        raise SystemExit(f"submodule-patch: lock file {relpath} does not exist")
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"submodule-patch: cannot parse {relpath}: {exc}") from exc


def patch_sets(component: dict) -> list[dict]:
    """Return the declared submodule patch sets of *component* (may be empty).

    Each entry is ``{"path", "patch_dir", "patch_series"}``; all three keys are
    required -- nothing is derived from anything else (same rule as the
    top-level ``patch_dir``/``patch_series`` pair, §2).
    """
    name = component.get("name", "?")
    sets: list[dict] = []
    seen: set[str] = set()
    for raw in component.get("submodule_patch", []):
        sub_path = raw.get("path", "")
        patch_dir = raw.get("patch_dir", "")
        patch_series = raw.get("patch_series", "")
        if not sub_path or not patch_dir or not patch_series:
            raise SystemExit(
                f"submodule-patch: component {name}: every submodule_patch entry needs "
                f"path/patch_dir/patch_series (got {raw!r})"
            )
        if sub_path in seen:
            raise SystemExit(
                f"submodule-patch: component {name}: duplicate submodule "
                f"patch set for {sub_path!r}"
            )
        seen.add(sub_path)
        sets.append(
            {"path": sub_path, "patch_dir": patch_dir, "patch_series": patch_series}
        )
    return sets


def lock_commits(component: dict) -> dict[str, str]:
    """``{submodule path: pinned commit}`` from the component's ``submodule_lock``."""
    name = component.get("name", "?")
    lock = component.get("submodule_lock", "")
    if not lock:
        raise SystemExit(
            f"submodule-patch: component {name} declares submodule_patch entries but "
            "no submodule_lock; the pinned base commit of a submodule patch set lives "
            "there (docs/Process-01 §14)"
        )
    commits: dict[str, str] = {}
    for entry in load_lock(lock).get("submodule", []):
        path = entry.get("path", "")
        commit = entry.get("commit", "")
        if path:
            commits[path] = commit
    return commits


def base_commit(component: dict, sub_path: str) -> str:
    """Pinned base commit of *sub_path* inside *component*'s checkout."""
    commits = lock_commits(component)
    commit = commits.get(sub_path, "")
    if not SHA1.fullmatch(commit):
        raise SystemExit(
            f"submodule-patch: component {component.get('name', '?')}: submodule "
            f"{sub_path!r} has no pinned commit in {component.get('submodule_lock')}"
        )
    return commit


def worktree(source: Path, sub_path: str) -> Path:
    """Worktree directory of *sub_path* inside the component source *source*."""
    return source / sub_path
