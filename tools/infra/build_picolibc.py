#!/usr/bin/env python3
"""Build picolibc for the DADAO-v5 ``dadao-unknown-elf`` target and install it.

This is the build half of the picolibc port (INFRA-057t).  It drives the
upstream Meson build with the DADAO cross file
(``scripts/cross-dadao.txt``, part of the component patch set) and installs the
result into the target sysroot (``target_sysroot_dir()``: headers under
``include/``, libraries under ``lib/``).

Idempotent: re-running reconfigures the same build tree and rebuilds only what
changed; the install step refreshes the sysroot.

Port scope (INFRA-057t): the DADAO LLVM backend cannot yet select some DAG
nodes the full C library needs (f64/i64 bitcast, FP setcc / select_cc, ctlz/
cttz/bswap, FP rounding libcalls).  The port therefore excludes the affected
sources (see the DADAO block in the component's ``meson.build``); they are
tracked by LLVM-079t (P0) / LLVM-080t (P1).  When those land, delete the
entries and this build produces the full library.

Tools: ``clang``/``clang++``/``ld.lld`` come from the install root's
cross-toolchain ``bin/`` (put on PATH here); ``ar``/``nm``/``strip`` are the
host binutils.  ``meson`` and ``ninja`` must be on PATH.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

REPO_ROOT = paths.repo_root()
WORK_ROOT = REPO_ROOT / ".work"
SOURCE = WORK_ROOT / "source" / "picolibc"
BUILD = WORK_ROOT / "build" / "picolibc"
CROSS_FILE = SOURCE / "scripts" / "cross-dadao.txt"
SYSROOT = paths.target_sysroot_dir()

MESON_ARGS = [
    "-Dmultilib=false",
    "-Dtests=false",
    "-Dpicocrt=true",
    "-Ddebug=false",
    # DADAO port scope: the backend cannot select the ryu float/string
    # conversion code, so select the smaller engine-based conversions.
    # `io-float-exact=false` builds dtoa_engine.c / atod_engine.c /
    # atof_engine.c, which define `__dtoa_engine` / `__atod_engine` (referenced
    # by vfprintf and conv_flt); the upstream default `true` builds the ryu
    # variant and leaves `__dtoa_engine` undefined on this target.  This is
    # passed on the command line rather than via the cross file's
    # `[project options]` because Meson re-applies CLI options on
    # `--reconfigure` but does not re-read cross-file project-option defaults
    # (the idempotent rebuild path uses `--reconfigure`).
    "-Dio-float-exact=false",
    f"-Dprefix={SYSROOT}",
    "-Dincludedir=include",
    "-Dlibdir=lib",
]


def run(cmd: list[str], *, env: dict[str, str], cwd: Path | None = None) -> None:
    print("build-picolibc:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env, cwd=cwd)


def need_tool(name: str, *, what: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"build-picolibc: ERROR: {name!r} not found on PATH ({what})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=int(os.environ.get("JOBS", "8")))
    args = ap.parse_args()

    if not SOURCE.is_dir():
        sys.exit(f"build-picolibc: ERROR: {SOURCE} missing — run 'make fetch' first")
    if not CROSS_FILE.is_file():
        sys.exit(
            f"build-picolibc: ERROR: {CROSS_FILE} missing — apply the picolibc patch "
            "series first ('make apply-series')"
        )
    toolchain_bin = paths.host_toolchain_bin()
    clang = toolchain_bin / "clang"
    if not clang.exists():
        sys.exit(
            f"build-picolibc: ERROR: {clang} not found — run 'make install-host' first"
        )

    need_tool("meson", what="host build tool")
    need_tool("ninja", what="host build tool")
    need_tool("ar", what="host binutils")

    env = dict(os.environ)
    env["PATH"] = str(toolchain_bin) + os.pathsep + env.get("PATH", "")

    SYSROOT.mkdir(parents=True, exist_ok=True)

    configured = (BUILD / "meson-private" / "coredata.dat").is_file()
    setup = ["meson", "setup"]
    if configured:
        setup.append("--reconfigure")
    setup += [str(BUILD), str(SOURCE), "--cross-file", str(CROSS_FILE), *MESON_ARGS]
    run(setup, env=env)

    run(["ninja", f"-j{args.jobs}", "-C", str(BUILD)], env=env)
    run(["meson", "install", "-C", str(BUILD), "--no-rebuild"], env=env)

    libc = SYSROOT / "lib" / "libc.a"
    semihost = SYSROOT / "lib" / "libsemihost.a"
    if not libc.is_file():
        sys.exit(f"build-picolibc: ERROR: {libc} was not installed")
    print(
        f"build-picolibc: PASS — {libc} ({libc.stat().st_size} bytes), "
        f"{semihost} ({semihost.stat().st_size} bytes), "
        f"headers under {SYSROOT / 'include'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
