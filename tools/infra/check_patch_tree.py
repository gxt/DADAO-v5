#!/usr/bin/env python3
"""Check a component's tree-shaped patch set against docs/spec/component-patching.md.

Assertions (all fail-closed):

  1. every patch contains exactly one ``diff --git`` entry
  2. target paths are globally unique across the patch set
     (this is what enforces "one file, one patch" and "a new file's patch is
     its final state")
  3. ``patches/series`` and the ``patches/`` tree agree in both directions,
     and the series is sorted lexicographically
  4. the whole set applies cleanly to the pinned base commit (checked against a
     temporary index, so the caller's worktree is not touched); skipped with a
     notice when ``.work/source/<name>`` is absent
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIFF_GIT = re.compile(r"^diff --git a/(.+?) b/(.+)$")


def load_manifest() -> dict:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        return tomllib.load(stream)


def series_entries(series_path: Path) -> list[str]:
    return [
        line.strip()
        for line in series_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def patch_targets(patch: Path) -> tuple[int, list[str]]:
    """Return (number of diff --git entries, target paths)."""
    entries = 0
    targets: list[str] = []
    for line in patch.read_text(encoding="utf-8", errors="replace").splitlines():
        match = DIFF_GIT.match(line)
        if match:
            entries += 1
            targets.append(match.group(2))
    return entries, targets


def check_component(name: str, component: dict, errors: list[str]) -> None:
    series_path = ROOT / component["patch_series"]
    patches_dir = series_path.parent
    if not series_path.exists():
        errors.append(f"{name}: missing series {series_path.relative_to(ROOT)}")
        return

    entries = series_entries(series_path)
    if not entries:
        errors.append(f"{name}: series is empty")
        return
    if entries != sorted(entries):
        errors.append(f"{name}: series is not sorted lexicographically")

    # assertion 3 (forward): every listed patch exists, and no extra files.
    listed = set()
    for item in entries:
        patch = patches_dir / item
        if not patch.is_file():
            errors.append(f"{name}: series lists missing patch {item}")
            continue
        listed.add(patch.resolve())
    on_disk = {p.resolve() for p in patches_dir.rglob("*.patch")}
    for extra in sorted(on_disk - listed):
        errors.append(f"{name}: patch not listed in series: {extra.relative_to(ROOT)}")

    # assertions 1 & 2.
    seen: dict[str, str] = {}
    for item in entries:
        patch = patches_dir / item
        if not patch.is_file():
            continue
        count, targets = patch_targets(patch)
        if count != 1:
            errors.append(
                f"{name}: {item} contains {count} diff --git entries (expected exactly 1)"
            )
        for target in targets:
            if target in seen:
                errors.append(
                    f"{name}: target path {target} touched by both {seen[target]} and {item}"
                )
            else:
                seen[target] = item
        expected_name = f"{targets[0]}.patch" if count == 1 else None
        if expected_name is not None and item != expected_name:
            errors.append(
                f"{name}: {item} does not match its target path (expected {expected_name})"
            )

    # assertion 4: apply cleanly to the pinned base, using a scratch index.
    source = ROOT / ".work" / "source" / name
    if not (source / ".git").exists():
        print(f"check-patch-tree: {name}: source worktree absent; skipping apply check")
        return
    commit = component["commit"]
    with tempfile.TemporaryDirectory() as scratch:
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(Path(scratch) / "index")
        subprocess.run(
            ["git", "-C", str(source), "read-tree", commit],
            env=env, check=True, capture_output=True,
        )
        args = ["git", "-C", str(source), "apply", "--cached", "--check"]
        args += [str(patches_dir / item) for item in entries]
        result = subprocess.run(args, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(
                f"{name}: patch set does not apply cleanly to base {commit[:12]}: "
                f"{result.stderr.strip()}"
            )


def main() -> int:
    manifest = load_manifest()
    enabled = [c for c in manifest.get("component", []) if c.get("enabled")]
    if not enabled:
        print("check-patch-tree: no components enabled")
        return 0

    errors: list[str] = []
    total = 0
    for component in enabled:
        series_path = ROOT / component["patch_series"]
        if series_path.exists():
            total += len(series_entries(series_path))
        check_component(component["name"], component, errors)

    for error in errors:
        print(f"check-patch-tree: {error}", file=sys.stderr)
    if errors:
        print(f"check-patch-tree: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"check-patch-tree: {len(enabled)} component(s), {total} patches OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
