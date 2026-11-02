#!/usr/bin/env python3
"""Compile and run the standalone DADAO B1 execution assertion harness.

The harness is plain C++17 (no gem5 dependencies), so the B1 semantics can be
checked without a full gem5 build.  It is compiled together with the B0 decode
core (the harness needs the contract-driven decode table).

The B1 id set printed by the harness (an explicit list, one id per line) is
cross-checked here against the *live* `batch_of()` set derived from
`contracts/opcodes.yaml` + the GEM5-002t matrix, so a batch boundary change can
never silently pass.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B1_ID = re.compile(r"^\[PASS\] b1-id (\S+)$", re.MULTILINE)


def live_b1_ids() -> list[str]:
    """Derive the B1 set from the contracts with the table generator."""
    path = ROOT / "tools/gem5/gen_decode_table.py"
    spec = importlib.util.spec_from_file_location("gen_decode_table", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return [entry.id for entry in module.load_entries() if entry.batch == "B1"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"),
                        help="gem5 worktree (default .work/source/gem5)")
    parser.add_argument("--out", type=Path,
                        default=Path(".work/build/gem5/dadao-b1-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    needed = [
        source / "src/arch/dadao/decode/decode.hh",
        source / "src/arch/dadao/exec/b1.hh",
        source / "src/arch/dadao/exec/b1.cc",
        source / "src/arch/dadao/exec/b1_test.cc",
    ]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-b1: missing input(s); run `make apply-series` first:",
              file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(source / "src"),
        str(source / "src/arch/dadao/decode/decode.cc"),
        str(source / "src/arch/dadao/exec/b1.cc"),
        str(source / "src/arch/dadao/exec/b1_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-b1: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-b1: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-b1: run: {out}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)

    failures = run.stdout.count("[FAIL]")
    reported = sorted(B1_ID.findall(run.stdout))
    live = sorted(live_b1_ids())

    ok = True
    if "B1 coverage 38/38" not in run.stdout:
        print("check-gem5-b1: FAIL -- missing 'B1 coverage 38/38' marker",
              file=sys.stderr)
        ok = False
    if len(reported) != 38:
        print(f"check-gem5-b1: FAIL -- harness listed {len(reported)} B1 ids, "
              "expected 38", file=sys.stderr)
        ok = False
    if reported != live:
        extra = sorted(set(reported) - set(live))
        missing_ids = sorted(set(live) - set(reported))
        print("check-gem5-b1: FAIL -- harness B1 id set != live batch_of() set",
              file=sys.stderr)
        if extra:
            print(f"  only in harness: {extra}", file=sys.stderr)
        if missing_ids:
            print(f"  only in contracts: {missing_ids}", file=sys.stderr)
        ok = False
    if failures != 0:
        print(f"check-gem5-b1: FAIL -- {failures} [FAIL] line(s)",
              file=sys.stderr)
        ok = False
    if run.returncode != 0:
        print(f"check-gem5-b1: FAIL -- harness rc={run.returncode}",
              file=sys.stderr)
        ok = False

    print(f"check-gem5-b1: b1 ids {len(reported)}/38, live {len(live)}, "
          f"failures {failures}, rc={run.returncode}")
    if not ok:
        return 1
    print("check-gem5-b1: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
