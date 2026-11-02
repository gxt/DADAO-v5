#!/usr/bin/env python3
"""Compile and run the standalone DADAO B4 execution assertion harness.

The harness is plain C++17 (no gem5 dependencies), so the B4 semantics can be
checked without a full gem5 build.  It is compiled together with the B0 decode
core (the harness needs the contract-driven decode table).

The B4 id set printed by the harness (an explicit list, one id per line) is
cross-checked here against the *live* `batch_of()` set derived from
`contracts/opcodes.yaml` + the GEM5-002t matrix, so a batch boundary change can
never silently pass.  The rule_refs counts are validated against the contract
(dst_rd0 63, encode_sbz 12, encode_onehot 3).
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B4_ID = re.compile(r"^\[PASS\] b4-id (\S+)$", re.MULTILINE)

_RD0 = ("dst_rd0",)
_SBZ = ("dst_rd0", "encode_sbz")
_ONEHOT = ("dst_rd0", "encode_onehot")

# contracts/opcodes.yaml rule_refs for the 63 B4 rows, by id.  Written out one
# id at a time: batch membership is never guessed from a mnemonic, and
# shl/rol/shr have both an orrr and an orri row.
EXPECTED_RULES = {
    # 32-bit add/sub/mul/div/rem
    "add.ut_orrr_rd": _RD0,
    "add.st_orrr_rd": _RD0,
    "sub.ut_orrr_rd": _RD0,
    "sub.st_orrr_rd": _RD0,
    "mul.ut_orrr_rd": _RD0,
    "mul.st_orrr_rd": _RD0,
    "div.ut_orrr_rd": _RD0,
    "div.st_orrr_rd": _RD0,
    "rem.ut_orrr_rd": _RD0,
    "rem.st_orrr_rd": _RD0,
    # 32-bit compare / shift
    "cmp.ut_orrr_rd": _RD0,
    "cmp.st_orrr_rd": _RD0,
    "shl.t_orrr_rd": _RD0,
    "rol.t_orrr_rd": _RD0,
    "shr.ut_orrr_rd": _RD0,
    "shr.st_orrr_rd": _RD0,
    "shl.t_orri_rd": _SBZ,
    "rol.t_orri_rd": _SBZ,
    "shr.ut_orri_rd": _SBZ,
    "shr.st_orri_rd": _SBZ,
    # 16-bit add/sub/mul/div/rem
    "add.uw_orrr_rd": _RD0,
    "add.sw_orrr_rd": _RD0,
    "sub.uw_orrr_rd": _RD0,
    "sub.sw_orrr_rd": _RD0,
    "mul.uw_orrr_rd": _RD0,
    "mul.sw_orrr_rd": _RD0,
    "div.uw_orrr_rd": _RD0,
    "div.sw_orrr_rd": _RD0,
    "rem.uw_orrr_rd": _RD0,
    "rem.sw_orrr_rd": _RD0,
    # 16-bit compare / shift
    "cmp.uw_orrr_rd": _RD0,
    "cmp.sw_orrr_rd": _RD0,
    "shl.w_orrr_rd": _RD0,
    "rol.w_orrr_rd": _RD0,
    "shr.uw_orrr_rd": _RD0,
    "shr.sw_orrr_rd": _RD0,
    "shl.w_orri_rd": _SBZ,
    "rol.w_orri_rd": _SBZ,
    "shr.uw_orri_rd": _SBZ,
    "shr.sw_orri_rd": _SBZ,
    # 8-bit add/sub/mul/div/rem
    "add.ub_orrr_rd": _RD0,
    "add.sb_orrr_rd": _RD0,
    "sub.ub_orrr_rd": _RD0,
    "sub.sb_orrr_rd": _RD0,
    "mul.ub_orrr_rd": _RD0,
    "mul.sb_orrr_rd": _RD0,
    "div.ub_orrr_rd": _RD0,
    "div.sb_orrr_rd": _RD0,
    "rem.ub_orrr_rd": _RD0,
    "rem.sb_orrr_rd": _RD0,
    # 8-bit compare / shift
    "cmp.ub_orrr_rd": _RD0,
    "cmp.sb_orrr_rd": _RD0,
    "shl.b_orrr_rd": _RD0,
    "rol.b_orrr_rd": _RD0,
    "shr.ub_orrr_rd": _RD0,
    "shr.sb_orrr_rd": _RD0,
    "shl.b_orri_rd": _SBZ,
    "rol.b_orri_rd": _SBZ,
    "shr.ub_orri_rd": _SBZ,
    "shr.sb_orri_rd": _SBZ,
    # per-block reverse
    "rev.t_orri_rd": _ONEHOT,
    "rev.w_orri_rd": _ONEHOT,
    "rev.b_orri_rd": _ONEHOT,
}

# Contract-wide rule_refs counts over the 63 B4 rows.
EXPECTED_RULE_COUNTS = {
    "dst_rd0": 63,
    "encode_sbz": 12,
    "encode_onehot": 3,
}


def live_b4_entries():
    """Derive the B4 rows from the contracts with the table generator."""
    path = ROOT / "tools/gem5/gen_decode_table.py"
    spec = importlib.util.spec_from_file_location("gen_decode_table", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return [entry for entry in module.load_entries() if entry.batch == "B4"]


def contract_rule_errors(entries) -> list[str]:
    """Cross-check live rule_refs/spec_cite against the contract mapping."""
    errors: list[str] = []
    by_id = {entry.id: entry for entry in entries}
    if len(by_id) != 63:
        errors.append(f"live B4 set has {len(by_id)} id(s), expected 63")
    for entry_id, rules in EXPECTED_RULES.items():
        entry = by_id.get(entry_id)
        if entry is None:
            errors.append(f"{entry_id}: missing from the live B4 set")
            continue
        if entry.rules != rules:
            errors.append(f"{entry_id}: rule_refs {entry.rules!r} != {rules!r}")
        if entry.fmt != ("orri" if entry_id.endswith("_orri_rd") else "orrr"):
            errors.append(
                f"{entry_id}: format {entry.fmt!r} != expected "
                f"{'orri' if entry_id.endswith('_orri_rd') else 'orrr'!r}")
        if not entry.spec_cite:
            errors.append(f"{entry_id}: missing spec_cite")
    for entry_id in by_id:
        if entry_id not in EXPECTED_RULES:
            errors.append(f"{entry_id}: unexpected live B4 id")

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
                        default=Path(".work/build/gem5/dadao-b4-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    needed = [
        source / "src/arch/dadao/decode/decode.hh",
        source / "src/arch/dadao/exec/common.hh",
        source / "src/arch/dadao/exec/b4.hh",
        source / "src/arch/dadao/exec/b4.cc",
        source / "src/arch/dadao/exec/b4_test.cc",
    ]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-b4: missing input(s); run `make apply-series` first:",
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
        str(source / "src/arch/dadao/exec/b4.cc"),
        str(source / "src/arch/dadao/exec/b4_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-b4: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-b4: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-b4: run: {out}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)

    failures = run.stdout.count("[FAIL]")
    reported = sorted(B4_ID.findall(run.stdout))
    entries = live_b4_entries()
    live = sorted(entry.id for entry in entries)
    rule_errors = contract_rule_errors(entries)

    ok = True
    if "B4 coverage 63/63" not in run.stdout:
        print("check-gem5-b4: FAIL -- missing 'B4 coverage 63/63' marker",
              file=sys.stderr)
        ok = False
    if "non-B4 ids return NotB4 (201/201)" not in run.stdout:
        print("check-gem5-b4: FAIL -- missing 'non-B4 ids return NotB4 "
              "(201/201)' marker", file=sys.stderr)
        ok = False
    if len(reported) != 63:
        print(f"check-gem5-b4: FAIL -- harness listed {len(reported)} B4 ids, "
              "expected 63", file=sys.stderr)
        ok = False
    if reported != live:
        extra = sorted(set(reported) - set(live))
        missing_ids = sorted(set(live) - set(reported))
        print("check-gem5-b4: FAIL -- harness B4 id set != live batch_of() set",
              file=sys.stderr)
        if extra:
            print(f"  only in harness: {extra}", file=sys.stderr)
        if missing_ids:
            print(f"  only in contracts: {missing_ids}", file=sys.stderr)
        ok = False
    if rule_errors:
        print("check-gem5-b4: FAIL -- contract rule/spec_cite mismatch:",
              file=sys.stderr)
        for error in rule_errors:
            print(f"  {error}", file=sys.stderr)
        ok = False
    if failures != 0:
        print(f"check-gem5-b4: FAIL -- {failures} [FAIL] line(s)",
              file=sys.stderr)
        ok = False
    if run.returncode != 0:
        print(f"check-gem5-b4: FAIL -- harness rc={run.returncode}",
              file=sys.stderr)
        ok = False

    print(f"check-gem5-b4: b4 ids {len(reported)}/63, live {len(live)}, "
          f"failures {failures}, rc={run.returncode}")
    if not ok:
        return 1
    print("check-gem5-b4: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
