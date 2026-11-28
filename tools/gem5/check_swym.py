#!/usr/bin/env python3
"""Compile and run the standalone ``swym N`` latency-policy harness.

m19-gem5-001: ``swym N`` is total ``1 + N`` cycles with ``N = immu18[11:0]``
(12 bits, no cap).  The figure lives in ``arch/dadao/wuming_latency.hh``
(``swymCycles`` / ``extraFromTotal``), which is plain C++ over the generated
cycle table, so this check compiles it directly -- no gem5 build required.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"),
                        help="gem5 worktree (default .work/source/gem5)")
    parser.add_argument("--out", type=Path,
                        default=Path(".work/build/gem5/dadao-swym-policy-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    latency = source / "src/arch/dadao/wuming_latency.hh"
    if not latency.exists():
        print(f"check-swym-policy: {latency} is missing; "
              "run `make apply-series` first", file=sys.stderr)
        return 1

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(source / "src"),
        str(source / "src/arch/dadao/wuming_cycles.cc"),
        str(ROOT / "tools/gem5/swym_policy_test.cc"),
        "-o", str(out),
    ]
    print("check-swym-policy: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-swym-policy: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-swym-policy: run: {out}")
    run = subprocess.run([str(out)])
    print(f"check-swym-policy: rc={run.returncode}")
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
