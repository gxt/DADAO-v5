#!/usr/bin/env python3
"""Apply each enabled component's tree-shaped patch set with ``git apply``.

See ``docs/spec/component-patching.md`` (v5 spec, effective 2026-09-23).
``git apply`` is the only supported application path; authorship and commit
messages are deliberately **not** preserved (the patch set carries the change,
not a history).

The worktree must sit exactly on the component's pinned base commit; applying
on top of anything else is refused. Application is idempotent: a worktree whose
content already equals the fully-patched state is skipped.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_manifest() -> dict:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        return tomllib.load(stream)


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def main() -> int:
    manifest = load_manifest()
    enabled = [c for c in manifest.get("component", []) if c.get("enabled")]
    if not enabled:
        print("apply-series: no components enabled")
        return 0

    source_root = ROOT / manifest.get("work_root", ".work") / "source"
    for component in enabled:
        source = source_root / component["name"]
        if not (source / ".git").exists():
            raise SystemExit(f"apply-series: missing source {source}; run make fetch")

        head = git("rev-parse", "HEAD", cwd=source).stdout.strip()
        if head != component["commit"]:
            raise SystemExit(
                f"apply-series: {component['name']} HEAD ({head[:12]}) is not its "
                f"base commit ({component['commit'][:12]}); refusing to apply patches"
            )

        patches_dir = ROOT / component["patch_dir"]
        series_path = ROOT / component["patch_series"]
        patches = [
            patches_dir / line.strip()
            for line in series_path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not patches:
            print(f"apply-series: {component['name']} has an empty series")
            continue

        # Idempotence: every patch applies in reverse => the worktree already
        # holds the fully-patched content.
        if all(
            git("apply", "--check", "--reverse", str(patch), cwd=source, check=False).returncode
            == 0
            for patch in patches
        ):
            print(f"apply-series: {component['name']} already applied; skipping")
            continue

        for patch in patches:
            result = git("apply", "--check", str(patch), cwd=source, check=False)
            if result.returncode != 0:
                raise SystemExit(
                    f"apply-series: {component['name']}: patch does not apply cleanly: "
                    f"{patch.relative_to(ROOT)}\n{result.stderr.strip()}"
                )
        for patch in patches:
            git("apply", str(patch), cwd=source)
        print(f"apply-series: {component['name']} applied {len(patches)} patches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
