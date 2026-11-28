#!/usr/bin/env python3
"""Resolve DADAO-v5 install/product directory paths from the single source of truth.

Reads ``manifests/install-dirs.lock.toml`` and provides functions that return
absolute, ``realpath``-resolved ``pathlib.Path`` objects.  Also exposes a CLI
for Makefile integration (``--make``) and single-key queries.

All paths are resolved through ``Path(__file__).resolve()`` so that calls via
symbolic links (e.g. ``~/tao/…`` → ``/mnt/tao/…``) still return real paths.

``DADAO_INSTALL_ROOT`` (m20-infra-004) overrides the whole install root for one
task: when set, ``sdk_dir`` becomes that root and every other key keeps its
manifest-relative position under it (``.dadao/cross-toolchain`` →
``<root>/cross-toolchain``).  Unset ⇒ byte-identical default behaviour.  An
empty/whitespace, relative, non-directory or uncreatable value is an explicit
error (rc=2), never a silent fallback to the shared root: a task that meant to
test a private root must not silently read the shared one.
"""
from __future__ import annotations

import os
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

_INSTALL_ROOT_ENV = "DADAO_INSTALL_ROOT"


def _die(message: str) -> None:
    """Report an install-root misuse and exit (rc=2, fail-closed)."""
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(2)


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


def install_root_override() -> Path | None:
    """Return the validated ``DADAO_INSTALL_ROOT`` value, or ``None`` when unset.

    Only *unset* means "use the manifest".  A set-but-empty value is a mistake
    (a shell that meant to pass a root), so it fails instead of falling back.
    The returned path is absolute + ``realpath``; existence is validated (an
    absent root is accepted only when its nearest existing ancestor is writable,
    i.e. ``mkdir -p`` could create it later).
    """
    if _INSTALL_ROOT_ENV not in os.environ:
        return None
    raw = os.environ[_INSTALL_ROOT_ENV].strip()
    if not raw:
        _die(
            f"{_INSTALL_ROOT_ENV} is set but empty/whitespace; unset it to use "
            "manifests/install-dirs.lock.toml, or give an absolute private "
            "install root (the default is never assumed for a set variable)"
        )
    path = Path(raw)
    if not path.is_absolute():
        _die(
            f"{_INSTALL_ROOT_ENV}={raw!r} is not absolute; a private install "
            "root must be given as an absolute path (resolve it first, e.g. "
            "with $(abspath ...) in make)"
        )
    if path.exists():
        if not path.is_dir():
            _die(f"{_INSTALL_ROOT_ENV}={raw!r} exists but is not a directory")
        return path.resolve()
    ancestor = path
    while not ancestor.exists():
        parent = ancestor.parent
        if parent == ancestor:  # pragma: no cover - '/' always exists
            _die(f"{_INSTALL_ROOT_ENV}={raw!r} does not exist and cannot be created")
        ancestor = parent
    if not os.access(ancestor, os.W_OK):
        _die(
            f"{_INSTALL_ROOT_ENV}={raw!r} does not exist and cannot be created: "
            f"nearest existing ancestor {ancestor} is not writable"
        )
    return path.resolve()


def _manifest_relative(data: dict[str, str], key: str) -> str:
    """Position of ``key`` on the manifest *relative to* ``sdk_dir``."""
    sdk = Path(data["sdk_dir"])
    value = Path(data[key])
    try:
        rel = value.relative_to(sdk)
    except ValueError:
        _die(
            f"manifest key {key}={str(value)!r} is not under sdk_dir={str(sdk)!r}; "
            f"{_INSTALL_ROOT_ENV} can only relocate a tree that lives under sdk_dir"
        )
    return "" if str(rel) == "." else str(rel)


def _resolve_key(key: str, data: dict[str, str]) -> Path:
    """Resolve one manifest key, honouring the ``DADAO_INSTALL_ROOT`` override."""
    override = install_root_override()
    if override is None:
        return _resolve(data[key])
    rel = _manifest_relative(data, key)
    return (override / rel).resolve() if rel else override


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    """Absolute, realpath-resolved repository root."""
    return _REPO_ROOT


def sdk_dir() -> Path:
    """Absolute path to the SDK install/product root."""
    return _resolve_key("sdk_dir", _load_manifest())


def host_toolchain_dir() -> Path:
    """Absolute path to the host cross-toolchain prefix."""
    return _resolve_key("host_toolchain_dir", _load_manifest())


def host_toolchain_bin() -> Path:
    """Absolute path to the host toolchain ``bin/`` directory."""
    return host_toolchain_dir() / "bin"


def host_tools_dir() -> Path:
    """Absolute path to the host-only tools root (INFRA-050t).

    Host tools (e.g. the ``lli`` value-level oracle) are never target-side
    tools, so they live in their own root instead of ``cross-toolchain``.
    """
    return _resolve_key("host_tools_dir", _load_manifest())


def host_tools_bin() -> Path:
    """Absolute path to the host-only tools ``bin/`` directory."""
    return host_tools_dir() / "bin"


def target_sysroot_dir() -> Path:
    """Absolute path to the target sysroot."""
    return _resolve_key("target_sysroot_dir", _load_manifest())


def test_artifacts_dir() -> Path:
    """Absolute path to the test artifacts directory."""
    return _resolve_key("test_artifacts_dir", _load_manifest())


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
        resolved = _resolve_key(key, data)
        name = key.upper()
        print(f"{name} := {resolved}")
    # Also export repo_root-derived helpers
    print(f"REPO_ROOT := {_REPO_ROOT}")
    print(f"HOST_TOOLCHAIN_BIN := {_resolve_key('host_toolchain_dir', data) / 'bin'}")
    print(f"HOST_TOOLS_BIN := {_resolve_key('host_tools_dir', data) / 'bin'}")


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
