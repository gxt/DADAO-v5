#!/usr/bin/env python3
"""Compile and run the standalone DADAO B5 execution assertion harness.

The harness is plain C++17 (no gem5 dependencies), so the B5 semantics can be
checked without a full gem5 build.  It is compiled together with the B0 decode
core (the harness needs the contract-driven decode table).

The B5 id set printed by the harness (an explicit list, one id per line) is
cross-checked here against the *live* `batch_of()` set derived from
`contracts/opcodes.yaml` + the GEM5-002t matrix, so a batch boundary change can
never silently pass.  The per-id rule_refs and the contract-wide rule counts
(dst_rd0 9, dst_rb0 2, dst_rd0_nonzero 1, mreg_zero 8, mreg_range_overflow 8,
mreg_range_overlap 2) are validated against the contract.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B5_ID = re.compile(r"^\[PASS\] b5-id (\S+)$", re.MULTILINE)

_RD0 = ("dst_rd0",)
_RB0 = ("dst_rb0",)
_MZ = ("mreg_zero", "mreg_range_overflow")
_MZ_OVL = ("dst_rd0", "mreg_zero", "mreg_range_overflow",
           "mreg_range_overlap")
_RB_Z_OVL = ("dst_rb0", "mreg_zero", "mreg_range_overflow",
             "mreg_range_overlap")

# contracts/opcodes.yaml rule_refs for the 28 B5 rows, by id.  Written out one
# id at a time: batch membership is never guessed from a mnemonic, and br.z/
# br.nz, jump/call each have two format-specific rows.
EXPECTED_RULES = {
    # register block copies
    "rd2rd_orri_rd": _MZ_OVL,
    "rd2ra_orri_ra": _MZ,
    "ra2rd_orri_ra": _RD0 + _MZ,
    "rb2rb_orri_rb": _RB_Z_OVL,
    "rd2rb_orri_rb": _RB0 + _MZ,
    "rb2rd_orri_rb": _RD0 + _MZ,
    "rd2rf_orri_rf": _MZ,
    "rf2rd_orri_rf": _RD0 + _MZ,
    # conditional assignment
    "cs.n_rrrr_rd": _RD0,
    "cs.z_rrrr_rd": _RD0,
    "cs.p_rrrr_rd": _RD0,
    "cs.eq_rrrr_rd": _RD0,
    "cs.ne_rrrr_rd": _RD0,
    # conditional branches
    "br.n_riii_rd": (),
    "br.nn_riii_rd": (),
    "br.z_riii_rd": (),
    "br.nz_riii_rd": (),
    "br.p_riii_rd": (),
    "br.np_riii_rd": (),
    "br.eq_rrii_rd": (),
    "br.ne_rrii_rd": (),
    "br.z_riii_rb": (),
    "br.nz_riii_rb": (),
    # jumps / calls / ret
    "jump_iiii_rb": (),
    "jump_rrii_rb": (),
    "call_iiii_ra": (),
    "call_rrii_ra": (),
    "ret_riii_ra": ("dst_rd0_nonzero",),
}

EXPECTED_FORMATS = {
    "rd2rd_orri_rd": "orri",
    "rd2ra_orri_ra": "orri",
    "ra2rd_orri_ra": "orri",
    "rb2rb_orri_rb": "orri",
    "rd2rb_orri_rb": "orri",
    "rb2rd_orri_rb": "orri",
    "rd2rf_orri_rf": "orri",
    "rf2rd_orri_rf": "orri",
    "cs.n_rrrr_rd": "rrrr",
    "cs.z_rrrr_rd": "rrrr",
    "cs.p_rrrr_rd": "rrrr",
    "cs.eq_rrrr_rd": "rrrr",
    "cs.ne_rrrr_rd": "rrrr",
    "br.n_riii_rd": "riii",
    "br.nn_riii_rd": "riii",
    "br.z_riii_rd": "riii",
    "br.nz_riii_rd": "riii",
    "br.p_riii_rd": "riii",
    "br.np_riii_rd": "riii",
    "br.eq_rrii_rd": "rrii",
    "br.ne_rrii_rd": "rrii",
    "br.z_riii_rb": "riii",
    "br.nz_riii_rb": "riii",
    "jump_iiii_rb": "iiii",
    "jump_rrii_rb": "rrii",
    "call_iiii_ra": "iiii",
    "call_rrii_ra": "rrii",
    "ret_riii_ra": "riii",
}

# Contract-wide rule_refs counts over the 28 B5 rows.
EXPECTED_RULE_COUNTS = {
    "dst_rd0": 9,
    "dst_rb0": 2,
    "dst_rd0_nonzero": 1,
    "mreg_zero": 8,
    "mreg_range_overflow": 8,
    "mreg_range_overlap": 2,
}


def live_b5_entries():
    """Derive the B5 rows from the contracts with the table generator."""
    path = ROOT / "tools/gem5/gen_decode_table.py"
    spec = importlib.util.spec_from_file_location("gen_decode_table", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return [entry for entry in module.load_entries() if entry.batch == "B5"]


def contract_rule_errors(entries) -> list[str]:
    """Cross-check live rule_refs/spec_cite against the contract mapping."""
    errors: list[str] = []
    by_id = {entry.id: entry for entry in entries}
    if len(by_id) != 28:
        errors.append(f"live B5 set has {len(by_id)} id(s), expected 28")
    for entry_id, rules in EXPECTED_RULES.items():
        entry = by_id.get(entry_id)
        if entry is None:
            errors.append(f"{entry_id}: missing from the live B5 set")
            continue
        if entry.rules != rules:
            errors.append(f"{entry_id}: rule_refs {entry.rules!r} != {rules!r}")
        if entry.fmt != EXPECTED_FORMATS[entry_id]:
            errors.append(
                f"{entry_id}: format {entry.fmt!r} != "
                f"{EXPECTED_FORMATS[entry_id]!r}")
        if not entry.spec_cite:
            errors.append(f"{entry_id}: missing spec_cite")
    for entry_id in by_id:
        if entry_id not in EXPECTED_RULES:
            errors.append(f"{entry_id}: unexpected live B5 id")

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
                        default=Path(".work/build/gem5/dadao-b5-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    needed = [
        source / "src/arch/dadao/decode/decode.hh",
        source / "src/arch/dadao/exec/common.hh",
        source / "src/arch/dadao/exec/b1.hh",
        source / "src/arch/dadao/exec/b5.hh",
        source / "src/arch/dadao/exec/b5.cc",
        source / "src/arch/dadao/exec/b5_test.cc",
    ]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-b5: missing input(s); run `make apply-series` first:",
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
        str(source / "src/arch/dadao/exec/b5.cc"),
        str(source / "src/arch/dadao/exec/b5_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-b5: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-b5: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-b5: run: {out}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)

    failures = run.stdout.count("[FAIL]")
    reported = sorted(B5_ID.findall(run.stdout))
    entries = live_b5_entries()
    live = sorted(entry.id for entry in entries)
    rule_errors = contract_rule_errors(entries)

    ok = True
    if "B5 coverage 28/28" not in run.stdout:
        print("check-gem5-b5: FAIL -- missing 'B5 coverage 28/28' marker",
              file=sys.stderr)
        ok = False
    if "non-B5 ids return NotB5 (236/236)" not in run.stdout:
        print("check-gem5-b5: FAIL -- missing 'non-B5 ids return NotB5 "
              "(236/236)' marker", file=sys.stderr)
        ok = False
    if len(reported) != 28:
        print(f"check-gem5-b5: FAIL -- harness listed {len(reported)} B5 ids, "
              "expected 28", file=sys.stderr)
        ok = False
    if reported != live:
        extra = sorted(set(reported) - set(live))
        missing_ids = sorted(set(live) - set(reported))
        print("check-gem5-b5: FAIL -- harness B5 id set != live batch_of() set",
              file=sys.stderr)
        if extra:
            print(f"  only in harness: {extra}", file=sys.stderr)
        if missing_ids:
            print(f"  only in contracts: {missing_ids}", file=sys.stderr)
        ok = False
    if rule_errors:
        print("check-gem5-b5: FAIL -- contract rule/spec_cite mismatch:",
              file=sys.stderr)
        for error in rule_errors:
            print(f"  {error}", file=sys.stderr)
        ok = False
    if failures != 0:
        print(f"check-gem5-b5: FAIL -- {failures} [FAIL] line(s)",
              file=sys.stderr)
        ok = False
    if run.returncode != 0:
        print(f"check-gem5-b5: FAIL -- harness rc={run.returncode}",
              file=sys.stderr)
        ok = False

    print(f"check-gem5-b5: b5 ids {len(reported)}/28, live {len(live)}, "
          f"failures {failures}, rc={run.returncode}")
    live_counts = {
        rule: sum(rule in entry.rules for entry in entries)
        for rule in EXPECTED_RULE_COUNTS
    }
    print("check-gem5-b5: rule_refs " +
          " ".join(f"{rule}={live_counts[rule]}"
                   for rule in EXPECTED_RULE_COUNTS))
    if not ok:
        return 1
    print("check-gem5-b5: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
