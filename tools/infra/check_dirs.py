#!/usr/bin/env python3
"""Path guard: validate install-dirs manifest + scan for symlink prefixes in versioned files.

Checks (all fail-closed):

  1. ``manifests/install-dirs.lock.toml`` exists, has all four required keys,
     all values are relative paths, and child dirs are under ``sdk_dir``.
  2. Scans version-controlled scripts/build files for the symlink prefix
     ``/home/ubuntu/tao`` (must use real path or relative path instead).

Exit code: non-zero on any violation.
"""
from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests" / "install-dirs.lock.toml"
REFS_MANIFEST = ROOT / "manifests" / "references.lock.toml"

REQUIRED_KEYS = ("sdk_dir", "host_toolchain_dir", "target_sysroot_dir", "test_artifacts_dir")
CHILD_KEYS = ("host_toolchain_dir", "target_sysroot_dir", "test_artifacts_dir")

# Patterns to scan for symlink prefix violations
SCAN_GLOBS = [
    "Makefile",
    "tools/**/*.py",
    "tests/**/*.py",
    "manifests/*.toml",
]

# The symlink prefix that must not appear in version-controlled files
SYMLINK_PREFIX = "/home/ubuntu/tao"


def check_manifest(errors: list[str]) -> None:
    """Validate the install-dirs lock file."""
    if not MANIFEST.is_file():
        errors.append(f"manifest not found: {MANIFEST}")
        return

    with MANIFEST.open("rb") as f:
        data = tomllib.load(f)

    for key in REQUIRED_KEYS:
        val = data.get(key)
        if val is None:
            errors.append(f"install-dirs.lock.toml: missing key {key!r}")
            continue
        if Path(val).is_absolute():
            errors.append(f"install-dirs.lock.toml: {key} must be relative, got {val!r}")

    sdk = data.get("sdk_dir", "")
    if sdk:
        for key in CHILD_KEYS:
            child = data.get(key, "")
            if child and not child.startswith(sdk.rstrip("/") + "/") and child != sdk:
                errors.append(
                    f"install-dirs.lock.toml: {key}={child!r} is not under sdk_dir={sdk!r}"
                )


def check_ref_paths(errors: list[str]) -> None:
    """Reference worktree paths must not live under the SDK dir."""
    if not REFS_MANIFEST.is_file():
        return
    if not MANIFEST.is_file():
        return

    with MANIFEST.open("rb") as f:
        sdk_dir = tomllib.load(f).get("sdk_dir", "")
    if not sdk_dir:
        return
    sdk_prefix = sdk_dir.rstrip("/") + "/"

    with REFS_MANIFEST.open("rb") as f:
        refs = tomllib.load(f).get("reference", [])

    for ref in refs:
        ref_path = ref.get("path", "")
        if ref_path == sdk_dir or ref_path.startswith(sdk_prefix):
            errors.append(
                f"references.lock.toml: {ref['id']} path={ref_path!r} "
                f"is under sdk_dir={sdk_dir!r} (ref worktrees must not live in SDK dir)"
            )


def check_symlink_prefix(errors: list[str]) -> None:
    """Scan version-controlled files for symlink prefix violations."""
    # Collect files from git to respect .gitignore
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if result.returncode != 0:
        errors.append(f"git ls-files failed: {result.stderr.strip()}")
        return

    tracked = set(result.stdout.strip().splitlines())

    # Expand globs against tracked files
    files_to_check: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for match in ROOT.glob(pattern):
            rel = match.relative_to(ROOT)
            if str(rel) in tracked and match.is_file():
                files_to_check.add(match)

    # Exclude this file — it defines SYMLINK_PREFIX as a constant
    self_path = Path(__file__).resolve()
    for fpath in sorted(files_to_check):
        if fpath.resolve() == self_path:
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if SYMLINK_PREFIX in line:
                rel = fpath.relative_to(ROOT)
                errors.append(
                    f"{rel}:{lineno}: contains symlink prefix {SYMLINK_PREFIX!r}"
                )


def main() -> int:
    errors: list[str] = []

    check_manifest(errors)
    check_ref_paths(errors)
    check_symlink_prefix(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("check-dirs: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
