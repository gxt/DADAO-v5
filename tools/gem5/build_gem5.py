#!/usr/bin/env python3
"""Build gem5 with the DADAO ISA (B0 skeleton).

Exit codes:
  0  gem5.opt built (``build/DADAO/gem5.opt`` under the gem5 worktree)
  1  build failed or the worktree is not prepared (apply-series missing)
  2  build dependency missing (scons not on PATH) -- BLOCKED, not a pass
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def tail(path: Path, lines: int = 80) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(data[-lines:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"))
    parser.add_argument("--build", type=Path,
                        default=Path(".work/build/gem5"))
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--scons", default=os.environ.get("SCONS", "scons"))
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    build_link = args.build if args.build.is_absolute() else ROOT / args.build
    if not (source / "SConstruct").exists():
        print(f"build-gem5: {source}/SConstruct is missing; "
              "run `make fetch`/`make apply-series` first", file=sys.stderr)
        return 1
    if not (source / "build_opts/DADAO").exists():
        print(f"build-gem5: {source}/build_opts/DADAO is missing; "
              "the GEM5-004t patch series is not applied", file=sys.stderr)
        return 1

    scons = args.scons
    scons_path = shutil.which(scons) if os.sep not in scons else scons
    if not scons_path or not os.path.exists(scons_path):
        print("build-gem5: BLOCKED -- scons is not available on PATH.",
              file=sys.stderr)
        print("  install it (e.g. `python3 -m venv .work/venv && "
              ".work/venv/bin/pip install scons`) and rerun with "
              "SCONS=.work/venv/bin/scons", file=sys.stderr)
        return 2

    log_dir = ROOT / ".work/log/gem5"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / "GEM5-004t-build.log"
    # Run *inside* the source tree: gem5 computes its build directory from
    # os.getcwd(), and `scons -C` is not equivalent here (it leaves the
    # target path anchored at the launch directory).
    cmd = [scons_path, "build/DADAO/gem5.opt", f"-j{args.jobs}"]
    print(f"build-gem5: log: {log.relative_to(ROOT)}")
    print("build-gem5: run (cwd=%s): %s" %
          (source.relative_to(ROOT), " ".join(cmd)))
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.run(cmd, cwd=source, stdout=stream,
                              stderr=subprocess.STDOUT)
    print(tail(log, 40))
    if proc.returncode != 0:
        print(f"build-gem5: FAILED rc={proc.returncode}; full log: "
              f"{log.relative_to(ROOT)}", file=sys.stderr)
        return 1

    binary = source / "build/DADAO/gem5.opt"
    if not binary.exists():
        print(f"build-gem5: scons returned 0 but {binary} is missing",
              file=sys.stderr)
        return 1

    # GEM5_BUILD is the conventional .work/build location; keep a stable link
    # to gem5's own build directory (gem5 insists on <src>/build/<variant>).
    if build_link.exists() or build_link.is_symlink():
        if not build_link.is_symlink():
            print(f"build-gem5: note: {build_link} exists and is not a "
                  "symlink; leaving it untouched")
        else:
            build_link.unlink()
    if not build_link.exists():
        build_link.parent.mkdir(parents=True, exist_ok=True)
        build_link.symlink_to((source / "build").relative_to(
            build_link.parent))
    print(f"build-gem5: PASS ({binary.relative_to(ROOT)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
