#!/usr/bin/env python3
"""Runtime paths of the kselftest suite (``tools/linux/suite/**``).

Every suite artefact is disposable and lives under ``work_root`` (resolved by
``tools/linux/paths.py`` from ``manifests/components.lock.toml``); nothing here
is a repo file and no host path is written into a delivered document.  The
*record* of a suite image is its manifest (``manifest.json`` next to the
archive), exactly like the K6 image (``tools/linux/make_initramfs.py``).

Layout (all under ``linux_build_dir().parent / "linux-suite"``):

  cc-static.sh        cross-CC wrapper: static musl link for guest programs
  hdrs/usr/include    kernel uapi headers (``make headers_install``)
  src/tree/           the *suite copy* of ``tools/testing/selftests`` that the
                      adaptation patches are applied to (upstream tree untouched)
  build/<dir>/        per-test build output (kselftest ``OUTPUT`` directory)
  image/              suite initramfs staging + ``initramfs.cpio`` + manifest
  runs/<stamp>/       one run: full console log, results JSON, build log
  log/                per-step build logs
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.linux import paths as linux_paths  # noqa: E402


def suite_root() -> Path:
    """Disposable suite work root (sibling of the kernel build tree)."""
    return linux_paths.linux_build_dir().parent / "linux-suite"


def cc_wrapper() -> Path:
    return suite_root() / "cc-static.sh"


def headers_dir() -> Path:
    """``--prefix`` of ``headers_install`` (headers land in ``include/``)."""
    return suite_root() / "hdrs"


def tree_dir() -> Path:
    """The ``linux`` stand-in whose ``tools/testing/selftests`` is the copy."""
    return suite_root() / "src" / "tree"


def selftests_copy() -> Path:
    return tree_dir() / "tools" / "testing" / "selftests"


def build_dir() -> Path:
    return suite_root() / "build"


def image_dir() -> Path:
    return suite_root() / "image"


def image_cpio() -> Path:
    return image_dir() / "initramfs.cpio"


def image_manifest() -> Path:
    return image_dir() / "manifest.json"


def runs_dir() -> Path:
    return suite_root() / "runs"


def log_dir() -> Path:
    return suite_root() / "log"


def ltp_root() -> Path:
    """Work root of the LTP suite build (its own tree; no kselftest paths)."""
    return suite_root() / "ltp"


def ltp_build_dir() -> Path:
    """``top_builddir`` of LTP's own Makefile system (out-of-tree build)."""
    return ltp_root() / "build"


def ltp_cc_wrapper() -> Path:
    """Cross-CC wrapper for LTP programs (static musl, public headers only)."""
    return ltp_root() / "cc-ltp.sh"
