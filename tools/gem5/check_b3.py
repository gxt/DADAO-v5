#!/usr/bin/env python3
"""Compile and run the standalone DADAO B3 execution assertion harness.

The harness is plain C++17 (no gem5 dependencies), so the B3 semantics can be
checked without a full gem5 build.  It is compiled together with the B0 decode
core (the harness needs the contract-driven decode table).

The B3 id set printed by the harness (an explicit list, one id per line) is
cross-checked here against the *live* `batch_of()` set derived from
`contracts/opcodes.yaml` + the GEM5-002t matrix, so a batch boundary change can
never silently pass.  The rule_refs counts are validated against the contract
(dst_dual_same 7, dst_rd0 31, dst_rb0 4, rev.o's encode_onehot 1).
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B3_ID = re.compile(r"^\[PASS\] b3-id (\S+)$", re.MULTILINE)

# contracts/opcodes.yaml rule_refs for the 42 B3 rows, by id.
_RD0 = ("dst_rd0",)
EXPECTED_RULES = {
    # 128-bit rrrr arithmetic
    "add.uo_rrrr_rd": ("dst_dual_same",),
    "add.so_rrrr_rd": ("dst_dual_same",),
    "sub.uo_rrrr_rd": ("dst_dual_same",),
    "sub.so_rrrr_rd": ("dst_dual_same",),
    "mul.uo_rrrr_rd": ("dst_dual_same",),
    "mul.so_rrrr_rd": ("dst_dual_same",),
    "clmul.o_rrrr_rd": ("dst_dual_same",),
    # immediate arithmetic / compare
    "add.si_riii_rd": _RD0,
    "aip.si_riii_rb": ("dst_rb0",),
    "add.si_riii_rb": ("dst_rb0",),
    "cmp.ui_rrii_rd": _RD0,
    "cmp.si_rrii_rd": _RD0,
    # bit scan / population
    "ctpop_orri_rd": _RD0,
    "ctlz_orri_rd": _RD0,
    "cttz_orri_rd": _RD0,
    # logic
    "and.o_orrr_rd": _RD0,
    "or.o_orrr_rd": _RD0,
    "xor.o_orrr_rd": _RD0,
    "xnor.o_orrr_rd": _RD0,
    # shift / rotate
    "shl.o_orrr_rd": _RD0,
    "rol.o_orrr_rd": _RD0,
    "shr.uo_orrr_rd": _RD0,
    "shr.so_orrr_rd": _RD0,
    "shl.o_orri_rd": _RD0,
    "rol.o_orri_rd": _RD0,
    "shr.uo_orri_rd": _RD0,
    "shr.so_orri_rd": _RD0,
    # extend / reverse
    "ext.uo_orrr_rd": _RD0,
    "ext.so_orrr_rd": _RD0,
    "ext.uo_orri_rd": _RD0,
    "ext.so_orri_rd": _RD0,
    "rev.o_orri_rd": ("dst_rd0", "encode_onehot"),
    # RB address arithmetic
    "add.o_orrr_bbd": ("dst_rb0",),
    "sub.o_orrr_bbd": ("dst_rb0",),
    "cmp.uo_orrr_dbb": _RD0,
    "sub.o_orrr_dbb": _RD0,
    # 64-bit compare / divide / remainder
    "cmp.uo_orrr_rd": _RD0,
    "cmp.so_orrr_rd": _RD0,
    "div.uo_orrr_rd": _RD0,
    "div.so_orrr_rd": _RD0,
    "rem.uo_orrr_rd": _RD0,
    "rem.so_orrr_rd": _RD0,
}

# Contract-wide rule_refs counts over the 42 B3 rows.
EXPECTED_RULE_COUNTS = {
    "dst_dual_same": 7,
    "dst_rd0": 31,
    "dst_rb0": 4,
    "encode_onehot": 1,
}


def live_b3_entries():
    """Derive the B3 rows from the contracts with the table generator."""
    path = ROOT / "tools/gem5/gen_decode_table.py"
    spec = importlib.util.spec_from_file_location("gen_decode_table", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return [entry for entry in module.load_entries() if entry.batch == "B3"]


def contract_rule_errors(entries) -> list[str]:
    """Cross-check live rule_refs/spec_cite against the contract mapping."""
    errors: list[str] = []
    by_id = {entry.id: entry for entry in entries}
    for entry_id, rules in EXPECTED_RULES.items():
        entry = by_id.get(entry_id)
        if entry is None:
            errors.append(f"{entry_id}: missing from the live B3 set")
            continue
        if entry.rules != rules:
            errors.append(f"{entry_id}: rule_refs {entry.rules!r} != {rules!r}")
        if not entry.spec_cite:
            errors.append(f"{entry_id}: missing spec_cite")

    counts = {rule: 0 for rule in EXPECTED_RULE_COUNTS}
    for entry in entries:
        for rule in entry.rules:
            if rule not in EXPECTED_RULE_COUNTS:
                errors.append(f"{entry.id}: unknown rule_refs {rule!r}")
                continue
            counts[rule] += 1
    for rule, expected in EXPECTED_RULE_COUNTS.items():
        if counts[rule] != expected:
            errors.append(
                f"rule {rule}: {counts[rule]} live row(s), expected {expected}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"),
                        help="gem5 worktree (default .work/source/gem5)")
    parser.add_argument("--out", type=Path,
                        default=Path(".work/build/gem5/dadao-b3-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    needed = [
        source / "src/arch/dadao/decode/decode.hh",
        source / "src/arch/dadao/exec/common.hh",
        source / "src/arch/dadao/exec/b3.hh",
        source / "src/arch/dadao/exec/b3.cc",
        source / "src/arch/dadao/exec/b3_test.cc",
    ]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-b3: missing input(s); run `make apply-series` first:",
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
        str(source / "src/arch/dadao/exec/b3.cc"),
        str(source / "src/arch/dadao/exec/b3_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-b3: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-b3: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-b3: run: {out}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)

    failures = run.stdout.count("[FAIL]")
    reported = sorted(B3_ID.findall(run.stdout))
    entries = live_b3_entries()
    live = sorted(entry.id for entry in entries)
    rule_errors = contract_rule_errors(entries)

    ok = True
    if "B3 coverage 42/42" not in run.stdout:
        print("check-gem5-b3: FAIL -- missing 'B3 coverage 42/42' marker",
              file=sys.stderr)
        ok = False
    if "non-B3 ids return NotB3 (222/222)" not in run.stdout:
        print("check-gem5-b3: FAIL -- missing 'non-B3 ids return NotB3 "
              "(222/222)' marker", file=sys.stderr)
        ok = False
    if len(reported) != 42:
        print(f"check-gem5-b3: FAIL -- harness listed {len(reported)} B3 ids, "
              "expected 42", file=sys.stderr)
        ok = False
    if reported != live:
        extra = sorted(set(reported) - set(live))
        missing_ids = sorted(set(live) - set(reported))
        print("check-gem5-b3: FAIL -- harness B3 id set != live batch_of() set",
              file=sys.stderr)
        if extra:
            print(f"  only in harness: {extra}", file=sys.stderr)
        if missing_ids:
            print(f"  only in contracts: {missing_ids}", file=sys.stderr)
        ok = False
    if rule_errors:
        print("check-gem5-b3: FAIL -- contract rule/spec_cite mismatch:",
              file=sys.stderr)
        for error in rule_errors:
            print(f"  {error}", file=sys.stderr)
        ok = False
    if failures != 0:
        print(f"check-gem5-b3: FAIL -- {failures} [FAIL] line(s)",
              file=sys.stderr)
        ok = False
    if run.returncode != 0:
        print(f"check-gem5-b3: FAIL -- harness rc={run.returncode}",
              file=sys.stderr)
        ok = False

    print(f"check-gem5-b3: b3 ids {len(reported)}/42, live {len(live)}, "
          f"failures {failures}, rc={run.returncode}")
    if not ok:
        return 1
    print("check-gem5-b3: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
