#!/usr/bin/env python3
"""Resolve the Linux component's runtime paths from the manifests.

Single source of truth for every M14 Linux script (``tools/linux/**``): the
source / build / initramfs trees are derived from
``manifests/components.lock.toml`` (``work_root`` + the ``linux`` entry) and the
toolchain binaries from ``manifests/install-dirs.lock.toml`` (ADR-0016 D3/D4).
No script may hardcode a host path, and no other task derives these paths on
its own -- import this module.

Returned values are absolute, ``realpath``-resolved ``pathlib.Path`` objects;
they are *runtime* paths (the manifest is the record, not the task book).
"""
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
# `tools/` carries no `__init__.py` (implicit namespace packages): importing the
# sibling package only works with the repo root on `sys.path`, which is *not*
# the case when this file is run as a script.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.infra import paths as _install_dirs  # noqa: E402

_COMPONENTS_LOCK = _REPO_ROOT / "manifests" / "components.lock.toml"
_COMPONENT = "linux"


def _work_root() -> Path:
    """``work_root`` from the component lock (repo-relative, may not be absolute)."""
    with _COMPONENTS_LOCK.open("rb") as stream:
        manifest = tomllib.load(stream)
    work_root = manifest.get("work_root")
    if not work_root or Path(work_root).is_absolute():
        raise SystemExit(
            f"linux paths: work_root must be a non-empty repo-relative path in "
            f"{_COMPONENTS_LOCK.name}, got {work_root!r}"
        )
    return (_REPO_ROOT / work_root).resolve()


def linux_source_dir() -> Path:
    """Component source checkout (``make fetch`` creates it, patches apply in it).

    ``DADAO_LINUX_SOURCE`` overrides it: a task that runs kernel builds while
    another task owns the shared component tree (write-mutex, AGENTS.md §3)
    points the whole Linux tooling at its own replay of the locked patch series
    instead of reading a tree someone else is editing.
    """
    override = os.environ.get("DADAO_LINUX_SOURCE")
    if override:
        return Path(override).resolve()
    return _work_root() / "source" / _COMPONENT


def component_source_dir(name: str) -> Path:
    """``make fetch`` worktree of any locked component (read-only for consumers).

    Used by the test-suite builders that consume a locked upstream corpus (the
    LTP suite, ``m18-linux-006``) instead of the kernel tree.
    """
    return _work_root() / "source" / name


def linux_build_dir() -> Path:
    """Out-of-tree kernel build directory (disposable, under ``work_root``).

    ``DADAO_LINUX_BUILD`` overrides it for the same reason as
    ``DADAO_LINUX_SOURCE`` (a private replay while the shared build tree is
    being written by another task).  The suite root derives from its parent, so
    one override moves the whole disposable Linux work root.
    """
    override = os.environ.get("DADAO_LINUX_BUILD")
    if override:
        return Path(override).resolve()
    return _work_root() / "build" / _COMPONENT


def linux_initramfs_dir() -> Path:
    """initramfs staging directory (disposable; contents listed by its manifest)."""
    return linux_build_dir() / "initramfs"


def linux_initramfs_manifest() -> Path:
    """``manifest.json`` of the initramfs staging directory."""
    return linux_initramfs_dir() / "manifest.json"


def toolchain_bin() -> Path:
    """Cross/host toolchain ``bin/`` (``manifests/install-dirs.lock.toml``)."""
    return _install_dirs.host_toolchain_bin()
