#!/usr/bin/env python3
"""Path guard: validate install-dirs manifest + scan for symlink prefixes in versioned files.

Checks (all fail-closed):

  1. ``manifests/install-dirs.lock.toml`` exists, has all required keys,
     all values are relative paths, and child dirs are under ``sdk_dir``.
  2. Scans version-controlled scripts/build files for the symlink prefix
     ``/home/ubuntu/tao`` (must use real path or relative path instead).
  3. Residue gate (``--residue``): detect unexpected untracked temp files
     matching ``*_tmp*``/``*_gate*``/``*.orig``/``*.rej`` patterns.

Exit code: non-zero on any violation.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests" / "install-dirs.lock.toml"
REFS_MANIFEST = ROOT / "manifests" / "references.lock.toml"

REQUIRED_KEYS = ("sdk_dir", "host_toolchain_dir", "host_tools_dir", "target_sysroot_dir", "test_artifacts_dir")
CHILD_KEYS = ("host_toolchain_dir", "host_tools_dir", "target_sysroot_dir", "test_artifacts_dir")

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


# ---------------------------------------------------------------------------
# Residue gate
# ---------------------------------------------------------------------------

# Patterns for unexpected temp/residue files
_RESIDUE_PATTERNS = ["*_tmp*", "*_gate*", "*.orig", "*.rej"]

# Directories that are allowed to contain untracked files
_RESIDUE_WHITELIST = [".tao/tasks", ".work"]


def check_residue(errors: list[str], root: Path | None = None) -> None:
    """Detect unexpected untracked temp files matching residue patterns.

    Uses ``git ls-files --others --exclude-standard`` to find untracked
    files, then matches against ``_RESIDUE_PATTERNS``.  Files under
    whitelisted directories are ignored.
    """
    scan_root = root if root else ROOT
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, cwd=scan_root,
    )
    if result.returncode != 0:
        errors.append(f"git ls-files --others failed: {result.stderr.strip()}")
        return

    untracked = result.stdout.strip().splitlines()
    if not untracked:
        return

    # Build whitelist prefixes relative to scan_root
    whitelist_prefixes = []
    for wdir in _RESIDUE_WHITELIST:
        if root:
            # In --root mode, no .tao/.work whitelist applies
            continue
        whitelist_prefixes.append(wdir + "/")

    for relpath_str in untracked:
        # Check whitelist
        is_whitelisted = False
        for prefix in whitelist_prefixes:
            if relpath_str.startswith(prefix):
                is_whitelisted = True
                break
        if is_whitelisted:
            continue

        # Check against residue patterns
        fname = Path(relpath_str).name
        for pattern in _RESIDUE_PATTERNS:
            # Simple glob-style matching using fnmatch
            import fnmatch
            if fnmatch.fnmatch(fname, pattern) or fnmatch.fnmatch(relpath_str, pattern):
                errors.append(f"residue: unexpected untracked file: {relpath_str}")
                break


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--residue", action="store_true",
        help="Run residue gate: detect unexpected untracked temp files.",
    )
    parser.add_argument(
        "--root", type=str, default=None,
        help="Override scan root directory (default: repo root). Only used with --residue.",
    )
    args = parser.parse_args()

    errors: list[str] = []

    if args.residue:
        root_override = Path(args.root).resolve() if args.root else None
        if root_override and not root_override.is_dir():
            print(f"ERROR: --root directory does not exist: {root_override}", file=sys.stderr)
            return 1
        check_residue(errors, root_override)
    else:
        check_manifest(errors)
        check_ref_paths(errors)
        check_symlink_prefix(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.residue:
        print("check-no-residue: PASS")
    else:
        print("check-dirs: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
