#!/usr/bin/env python3
"""Compile and run the standalone DADAO decode assertion harness.

The harness is plain C++17 (no gem5 dependencies), so it can be checked
without a gem5 build.  Contract drift is caught separately by
``tools/gem5/gen_decode_table.py --check``.
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
                        default=Path(".work/build/gem5/dadao-decode-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    decode_hh = source / "src/arch/dadao/decode/decode.hh"
    if not decode_hh.exists():
        print(f"check-gem5-decode: {decode_hh} is missing; "
              "run `make apply-series` first", file=sys.stderr)
        return 1

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(source / "src"),
        str(source / "src/arch/dadao/decode/decode.cc"),
        str(source / "src/arch/dadao/decode/decode_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-decode: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-decode: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-decode: run: {out}")
    run = subprocess.run([str(out)])
    print(f"check-gem5-decode: rc={run.returncode}")
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
