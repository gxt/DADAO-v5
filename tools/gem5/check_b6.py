#!/usr/bin/env python3
"""Compile and run the standalone DADAO B6 execution assertion harness.

The harness is plain C++17 (no gem5 dependencies), so the B6 semantics can be
checked without a full gem5 build.  It is compiled together with the B0 decode
core (the harness needs the contract-driven decode table).

The B6 id set printed by the harness (an explicit list, one id per line) is
cross-checked here against the *live* `batch_of()` set derived from
`contracts/opcodes.yaml` + the GEM5-002t matrix, so a batch boundary change can
never silently pass.  The per-id rule_refs/legality/format and the contract-wide
rule counts (encode_cfx_reserved 5, encode_sbz 14, dst_rd0 12) are validated
against the contract.  The 12 `lr.*` rows are additionally cross-checked against
the semantic matrix (`exceptions` must mention hb + ILLI): SPEC-182t F1 is
closed in the contract (`rdhb == rd0` + `encode_sbz`), and this script fails on
any silent drift back to an empty legality.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B6_ID = re.compile(r"^\[PASS\] b6-id (\S+)$", re.MULTILINE)
MATRIX = ROOT / ".tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv"

# contracts/opcodes.yaml rule_refs for the 30 B6 rows, by id.  Written out one
# id at a time: batch membership is never guessed from a mnemonic, and the
# three LR/SC families (width x order) have distinct rows.
_RULE_CFX = ("encode_cfx_reserved",)
_RULE_CFX_SBZ = ("encode_sbz", "encode_cfx_reserved")
_RULE_LR = ("encode_sbz",)
_RULE_SC = ("dst_rd0",)

EXPECTED_RULES = {
    # system / cfx (contract-isa §13.1/§13.6)
    "swym_oiii_imm": (),
    "trap_ciii_cfx": _RULE_CFX,
    "escape_ciii_cfx": _RULE_CFX_SBZ,
    "cfx2rd_crrr_cfx": _RULE_CFX,
    "cfx2rc_crrr_cfx": _RULE_CFX,
    # fence (contract-isa §14.1, ADR-0044)
    "fence_ciii_cfx": _RULE_CFX_SBZ,
    # lr.<width>.<order> (contract-isa §14.2, SPEC-182t F1 closed)
    "lr.o.nn_orrr_rd": _RULE_LR,
    "lr.t.nn_orrr_rd": _RULE_LR,
    "lr.w.nn_orrr_rd": _RULE_LR,
    "lr.b.nn_orrr_rd": _RULE_LR,
    "lr.o.an_orrr_rd": _RULE_LR,
    "lr.t.an_orrr_rd": _RULE_LR,
    "lr.w.an_orrr_rd": _RULE_LR,
    "lr.b.an_orrr_rd": _RULE_LR,
    "lr.o.ar_orrr_rd": _RULE_LR,
    "lr.t.ar_orrr_rd": _RULE_LR,
    "lr.w.ar_orrr_rd": _RULE_LR,
    "lr.b.ar_orrr_rd": _RULE_LR,
    # sc.<width>.<order> (contract-isa §14.2)
    "sc.o.nn_orrr_rd": _RULE_SC,
    "sc.t.nn_orrr_rd": _RULE_SC,
    "sc.w.nn_orrr_rd": _RULE_SC,
    "sc.b.nn_orrr_rd": _RULE_SC,
    "sc.o.nr_orrr_rd": _RULE_SC,
    "sc.t.nr_orrr_rd": _RULE_SC,
    "sc.w.nr_orrr_rd": _RULE_SC,
    "sc.b.nr_orrr_rd": _RULE_SC,
    "sc.o.ar_orrr_rd": _RULE_SC,
    "sc.t.ar_orrr_rd": _RULE_SC,
    "sc.w.ar_orrr_rd": _RULE_SC,
    "sc.b.ar_orrr_rd": _RULE_SC,
}

_CFX = "cfxha <= 5 || cfxha == 15 || (cfxha >= 32 && cfxha <= 34) || cfxha >= 62"
_SBZ_ESCAPE = "imms18[17:1] == 0"
_SBZ_FENCE = "immu18[17:12] == 0"

EXPECTED_LEGALITY = {
    "swym_oiii_imm": (),
    "trap_ciii_cfx": (_CFX,),
    "escape_ciii_cfx": (_SBZ_ESCAPE, _CFX),
    "cfx2rd_crrr_cfx": (_CFX,),
    "cfx2rc_crrr_cfx": (_CFX,),
    "fence_ciii_cfx": (_SBZ_FENCE, _CFX),
}
for _id in EXPECTED_RULES:
    if _id.startswith("lr."):
        EXPECTED_LEGALITY[_id] = ("rdhb == rd0",)
    elif _id.startswith("sc."):
        EXPECTED_LEGALITY[_id] = ("rdhb != rd0",)

EXPECTED_FORMATS = {}
for _id in EXPECTED_RULES:
    if _id.startswith("lr.") or _id.startswith("sc."):
        EXPECTED_FORMATS[_id] = "orrr"
    elif _id.startswith("cfx2r"):
        EXPECTED_FORMATS[_id] = "crrr"
    elif _id == "swym_oiii_imm":
        EXPECTED_FORMATS[_id] = "oiii"
    else:
        EXPECTED_FORMATS[_id] = "ciii"

# Contract-wide rule_refs counts over the 30 B6 rows (SPEC-182t F1: the 12 lr
# rows added encode_sbz, so the count is 14 and not 2).
EXPECTED_RULE_COUNTS = {
    "encode_cfx_reserved": 5,
    "encode_sbz": 14,
    "dst_rd0": 12,
}


def live_b6_entries():
    """Derive the B6 rows from the contracts with the table generator."""
    path = ROOT / "tools/gem5/gen_decode_table.py"
    spec = importlib.util.spec_from_file_location("gen_decode_table", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return [entry for entry in module.load_entries() if entry.batch == "B6"]


def matrix_errors(entries) -> list[str]:
    """Cross-check the 12 lr rows against the semantic matrix (independent
    derivation of the ILLI rule: exceptions must mention hb + ILLI)."""
    errors: list[str] = []
    try:
        with MATRIX.open(newline="") as stream:
            rows = {row["id"]: row for row in csv.DictReader(stream,
                                                             delimiter="\t")}
    except OSError as exc:
        return [f"cannot read the semantic matrix {MATRIX}: {exc}"]
    for entry in entries:
        if not entry.id.startswith("lr."):
            continue
        row = rows.get(entry.id)
        if row is None:
            errors.append(f"{entry.id}: missing from {MATRIX.name}")
            continue
        exceptions = row.get("exceptions", "")
        if "hb" not in exceptions or "ILLI" not in exceptions:
            errors.append(
                f"{entry.id}: matrix exceptions {exceptions!r} does not "
                "mention hb + ILLI")
    return errors


def contract_rule_errors(entries) -> list[str]:
    """Cross-check live rule_refs/legality/format/spec_cite per id."""
    errors: list[str] = []
    by_id = {entry.id: entry for entry in entries}
    if len(by_id) != 30:
        errors.append(f"live B6 set has {len(by_id)} id(s), expected 30")
    for entry_id, rules in EXPECTED_RULES.items():
        entry = by_id.get(entry_id)
        if entry is None:
            errors.append(f"{entry_id}: missing from the live B6 set")
            continue
        if entry.rules != rules:
            errors.append(f"{entry_id}: rule_refs {entry.rules!r} != {rules!r}")
        if entry.legality != EXPECTED_LEGALITY[entry_id]:
            errors.append(
                f"{entry_id}: legality {entry.legality!r} != "
                f"{EXPECTED_LEGALITY[entry_id]!r}")
        if entry.fmt != EXPECTED_FORMATS[entry_id]:
            errors.append(
                f"{entry_id}: format {entry.fmt!r} != "
                f"{EXPECTED_FORMATS[entry_id]!r}")
        if not entry.spec_cite:
            errors.append(f"{entry_id}: missing spec_cite")
    for entry_id in by_id:
        if entry_id not in EXPECTED_RULES:
            errors.append(f"{entry_id}: unexpected live B6 id")

    # SPEC-182t F1 closure: every lr row carries the hb SBZ legality.
    lr_ids = [i for i in EXPECTED_RULES if i.startswith("lr.")]
    closed = sum(1 for i in lr_ids
                 if by_id.get(i) is not None
                 and by_id[i].legality == ("rdhb == rd0",))
    if closed != 12:
        errors.append(f"lr legality closure: {closed}/12 rows are "
                      "'rdhb == rd0' (SPEC-182t F1 drift)")

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

    cites = [entry.spec_cite for entry in entries]
    if len(set(cites)) != 30:
        errors.append(f"spec_cite values are not unique ({len(set(cites))}/30)")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"),
                        help="gem5 worktree (default .work/source/gem5)")
    parser.add_argument("--out", type=Path,
                        default=Path(".work/build/gem5/dadao-b6-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    needed = [
        source / "src/arch/dadao/decode/decode.hh",
        source / "src/arch/dadao/exec/common.hh",
        source / "src/arch/dadao/exec/b1.hh",
        source / "src/arch/dadao/exec/b5.hh",
        source / "src/arch/dadao/exec/b6.hh",
        source / "src/arch/dadao/exec/b6.cc",
        source / "src/arch/dadao/exec/b6_test.cc",
    ]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-b6: missing input(s); run `make apply-series` first:",
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
        str(source / "src/arch/dadao/exec/b6.cc"),
        str(source / "src/arch/dadao/exec/b6_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-b6: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-b6: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-b6: run: {out}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)

    failures = run.stdout.count("[FAIL]")
    reported = sorted(set(B6_ID.findall(run.stdout)))
    entries = live_b6_entries()
    live = sorted(entry.id for entry in entries)
    rule_errors = contract_rule_errors(entries) + matrix_errors(entries)

    ok = True
    if "B6 coverage 30/30" not in run.stdout:
        print("check-gem5-b6: FAIL -- missing 'B6 coverage 30/30' marker",
              file=sys.stderr)
        ok = False
    if "non-B6 ids return NotB6 (234/234)" not in run.stdout:
        print("check-gem5-b6: FAIL -- missing 'non-B6 ids return NotB6 "
              "(234/234)' marker", file=sys.stderr)
        ok = False
    if len(reported) != 30:
        print(f"check-gem5-b6: FAIL -- harness listed {len(reported)} B6 ids, "
              "expected 30", file=sys.stderr)
        ok = False
    if reported != live:
        extra = sorted(set(reported) - set(live))
        missing_ids = sorted(set(live) - set(reported))
        print("check-gem5-b6: FAIL -- harness B6 id set != live batch_of() set",
              file=sys.stderr)
        if extra:
            print(f"  only in harness: {extra}", file=sys.stderr)
        if missing_ids:
            print(f"  only in contracts: {missing_ids}", file=sys.stderr)
        ok = False
    if rule_errors:
        print("check-gem5-b6: FAIL -- contract rule/legality mismatch:",
              file=sys.stderr)
        for error in rule_errors:
            print(f"  {error}", file=sys.stderr)
        ok = False
    if failures != 0:
        print(f"check-gem5-b6: FAIL -- {failures} [FAIL] line(s)",
              file=sys.stderr)
        ok = False
    if run.returncode != 0:
        print(f"check-gem5-b6: FAIL -- harness rc={run.returncode}",
              file=sys.stderr)
        ok = False

    print(f"check-gem5-b6: b6 ids {len(reported)}/30, live {len(live)}, "
          f"failures {failures}, rc={run.returncode}")
    live_counts = {
        rule: sum(rule in entry.rules for entry in entries)
        for rule in EXPECTED_RULE_COUNTS
    }
    print("check-gem5-b6: rule_refs " +
          " ".join(f"{rule}={live_counts[rule]}"
                   for rule in EXPECTED_RULE_COUNTS))
    print("check-gem5-b6: lr legality = rdhb == rd0 (12/12, SPEC-182t F1 "
          "closed)")
    if not ok:
        return 1
    print("check-gem5-b6: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
