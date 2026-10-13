#!/usr/bin/env python3
"""Resolve DADAO-v5 install/product directory paths from the single source of truth.

Reads ``manifests/install-dirs.lock.toml`` and provides functions that return
absolute, ``realpath``-resolved ``pathlib.Path`` objects.  Also exposes a CLI
for Makefile integration (``--make``) and single-key queries.

All paths are resolved through ``Path(__file__).resolve()`` so that calls via
symbolic links (e.g. ``~/tao/…`` → ``/mnt/tao/…``) still return real paths.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_THIS = Path(__file__).resolve()          # real path of this file
_REPO_ROOT = _THIS.parents[2]            # repo root (two levels up from tools/infra/)
_MANIFEST = _REPO_ROOT / "manifests" / "install-dirs.lock.toml"

_REQUIRED_KEYS = ("sdk_dir", "host_toolchain_dir", "host_tools_dir", "target_sysroot_dir", "test_artifacts_dir")


def _load_manifest() -> dict[str, str]:
    """Load and validate the install-dirs lock file."""
    if not _MANIFEST.is_file():
        print(f"ERROR: manifest not found: {_MANIFEST}", file=sys.stderr)
        sys.exit(1)
    with _MANIFEST.open("rb") as f:
        data = tomllib.load(f)
    for key in _REQUIRED_KEYS:
        val = data.get(key)
        if val is None:
            print(f"ERROR: missing key {key!r} in {_MANIFEST}", file=sys.stderr)
            sys.exit(1)
        p = Path(val)
        if p.is_absolute():
            print(f"ERROR: {key} must be a relative path, got {val!r}", file=sys.stderr)
            sys.exit(1)
    return data  # type: ignore[return-value]


def _resolve(relative: str) -> Path:
    """Resolve a repo-root-relative path to absolute+realpath."""
    return (_REPO_ROOT / relative).resolve()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    """Absolute, realpath-resolved repository root."""
    return _REPO_ROOT


def sdk_dir() -> Path:
    """Absolute path to the SDK install/product root."""
    return _resolve(_load_manifest()["sdk_dir"])


def host_toolchain_dir() -> Path:
    """Absolute path to the host cross-toolchain prefix."""
    return _resolve(_load_manifest()["host_toolchain_dir"])


def host_toolchain_bin() -> Path:
    """Absolute path to the host toolchain ``bin/`` directory."""
    return host_toolchain_dir() / "bin"


def host_tools_dir() -> Path:
    """Absolute path to the host-only tools root (INFRA-050t).

    Host tools (e.g. the ``lli`` value-level oracle) are never target-side
    tools, so they live in their own root instead of ``cross-toolchain``.
    """
    return _resolve(_load_manifest()["host_tools_dir"])


def host_tools_bin() -> Path:
    """Absolute path to the host-only tools ``bin/`` directory."""
    return host_tools_dir() / "bin"


def target_sysroot_dir() -> Path:
    """Absolute path to the target sysroot."""
    return _resolve(_load_manifest()["target_sysroot_dir"])


def test_artifacts_dir() -> Path:
    """Absolute path to the test artifacts directory."""
    return _resolve(_load_manifest()["test_artifacts_dir"])


# Map key names to resolver functions for CLI dispatch.
_GETTERS: dict[str, callable] = {  # type: ignore[type-arg]
    "repo_root": repo_root,
    "sdk_dir": sdk_dir,
    "host_toolchain_dir": host_toolchain_dir,
    "host_toolchain_bin": host_toolchain_bin,
    "host_tools_dir": host_tools_dir,
    "host_tools_bin": host_tools_bin,
    "target_sysroot_dir": target_sysroot_dir,
    "test_artifacts_dir": test_artifacts_dir,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_make_vars() -> None:
    """Print ``NAME := value`` lines for Makefile ``$(eval)`` inclusion."""
    data = _load_manifest()
    for key in _REQUIRED_KEYS:
        resolved = _resolve(data[key])
        name = key.upper()
        print(f"{name} := {resolved}")
    # Also export repo_root-derived helpers
    print(f"REPO_ROOT := {_REPO_ROOT}")
    print(f"HOST_TOOLCHAIN_BIN := {_resolve(data['host_toolchain_dir']) / 'bin'}")
    print(f"HOST_TOOLS_BIN := {_resolve(data['host_tools_dir']) / 'bin'}")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} --make | <key>", file=sys.stderr)
        print(f"Keys: {', '.join(_GETTERS)}", file=sys.stderr)
        return 1

    arg = sys.argv[1]
    if arg == "--make":
        _print_make_vars()
        return 0

    getter = _GETTERS.get(arg)
    if getter is None:
        print(f"ERROR: unknown key {arg!r}; valid keys: {', '.join(_GETTERS)}", file=sys.stderr)
        return 1

    print(getter())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
