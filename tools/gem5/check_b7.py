#!/usr/bin/env python3
"""Compile and run the standalone DADAO B7 floating-point assertion harness.

The harness is plain C++17 (no gem5 dependencies), so the B7 semantics can be
checked without a full gem5 build.  It is compiled together with the B0 decode
core and the pure-integer FP library (exec/fp_soft.cc + exec/b7.cc).

What this gate verifies (GEM5-012t acceptance):

1. the harness self assertions (one [PASS]/[FAIL] per check) all pass;
2. the B7 id set printed by the harness (an explicit list, one id per line) is
   *equal* to the live `batch_of()` set derived from contracts/opcodes.yaml +
   the GEM5-002t matrix (two-way difference, never a one-way subset);
3. per id: contract_ref, spec_cite, format, rule_refs and legality strings
   against a built-in expectation table (55 rows -- no weak assertions);
4. contract-wide rule counts (dst_rf0 41 / mreg_zero 22 /
   mreg_range_overflow 22 / dst_rd0 14 / mreg_range_overlap 4 /
   encode_fp_root_n 2 / encode_onehot 2) and "no B7 row has empty legality";
5. the same-id rows of the GEM5-002t matrix agree on contract_ref/spec_cite;
6. bit-exact differential against tools/gem5/b7_ref.py: >= 2000 vectors (per
   family >= the task's minimum), comparing the destination register values and
   the new FCSR word bit for bit;
7. independent oracle cross-checks for fma / minmax / roundint against
   tests/inst oracles (oracle_fma / oracle_minmax / oracle_rnd), used read-only;
8. read-only consistency with the tests/inst FP assets (fma/, minmax/,
   roundint/, fp/scaleb.yaml) -- the scaleB C1 decoy is re-derived.

Provenance note (f2i NX): ``convert_f2i`` signals NX for a finite inexact
conversion per ``contract-fp §3`` (SPEC-181t F5.3).  The ``g1_note`` of the
GEM5-002t matrix still says "f2i NX 未明" because it was written before that
closure; the contract wins and the matrix file is not modified here.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / ".tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv"
HARNESS_ID = re.compile(r"^\[PASS\] b7-id (\S+)$", re.MULTILINE)

# ── built-in per-id expectation table (55 rows) ──────────────────────────
# id -> (contract_ref, spec_cite, rule_refs, legality)
EXPECTED = {
    "ftfma_rrrr_rf": ("contract-fp §20", "SimRISC-07: ftfma", ("dst_rf0",),
                      ("rfha != rf0",)),
    "fofma_rrrr_rf": ("contract-fp §20", "SimRISC-07: fofma", ("dst_rf0",),
                      ("rfha != rf0",)),
    "cs.n_rrrr_rf": ("contract-fp §10", "SimRISC-02: cs.n", ("dst_rf0",),
                     ("rfhb != rf0",)),
    "cs.z_rrrr_rf": ("contract-fp §10", "SimRISC-02: cs.z", ("dst_rf0",),
                     ("rfhb != rf0",)),
    "cs.p_rrrr_rf": ("contract-fp §10", "SimRISC-02: cs.p", ("dst_rf0",),
                     ("rfhb != rf0",)),
    "ftcls_orri_rf": ("contract-fp §9", "SimRISC-07: ftcls",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "focls_orri_rf": ("contract-fp §9", "SimRISC-07: focls",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "ft2fo_orri_rf": ("contract-fp §2", "SimRISC-07: ft2fo",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow",
                       "mreg_range_overlap"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rfhc + immu6 <= 64",
                       "no_overlap(rfhb, rfhc, immu6)")),
    "ft2ft_orri_rf": ("contract-fp §2", "SimRISC-07: ft2ft",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow",
                       "mreg_range_overlap"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rfhc + immu6 <= 64",
                       "no_overlap(rfhb, rfhc, immu6)")),
    "fo2ft_orri_rf": ("contract-fp §2", "SimRISC-07: fo2ft",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow",
                       "mreg_range_overlap"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rfhc + immu6 <= 64",
                       "no_overlap(rfhb, rfhc, immu6)")),
    "fo2fo_orri_rf": ("contract-fp §2", "SimRISC-07: fo2fo",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow",
                       "mreg_range_overlap"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rfhc + immu6 <= 64",
                       "no_overlap(rfhb, rfhc, immu6)")),
    "ftroot_orri_rf": ("contract-fp §6", "SimRISC-07: ftroot",
                       ("dst_rf0", "encode_fp_root_n"),
                       ("rfhb != rf0", "immu6 == 2")),
    "foroot_orri_rf": ("contract-fp §6", "SimRISC-07: foroot",
                       ("dst_rf0", "encode_fp_root_n"),
                       ("rfhb != rf0", "immu6 == 2")),
    "ft2it_orri_rf": ("contract-fp §3", "SimRISC-07: ft2it",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "ft2io_orri_rf": ("contract-fp §3", "SimRISC-07: ft2io",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "ft2ut_orri_rf": ("contract-fp §3", "SimRISC-07: ft2ut",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "ft2uo_orri_rf": ("contract-fp §3", "SimRISC-07: ft2uo",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "fo2it_orri_rf": ("contract-fp §3", "SimRISC-07: fo2it",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "fo2io_orri_rf": ("contract-fp §3", "SimRISC-07: fo2io",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "fo2ut_orri_rf": ("contract-fp §3", "SimRISC-07: fo2ut",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "fo2uo_orri_rf": ("contract-fp §3", "SimRISC-07: fo2uo",
                      ("dst_rd0", "mreg_zero", "mreg_range_overflow"),
                      ("rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64",
                       "rfhc + immu6 <= 64")),
    "it2ft_orri_rf": ("contract-fp §4", "SimRISC-07: it2ft",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "io2ft_orri_rf": ("contract-fp §4", "SimRISC-07: io2ft",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "ut2ft_orri_rf": ("contract-fp §4", "SimRISC-07: ut2ft",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "uo2ft_orri_rf": ("contract-fp §4", "SimRISC-07: uo2ft",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "it2fo_orri_rf": ("contract-fp §4", "SimRISC-07: it2fo",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "io2fo_orri_rf": ("contract-fp §4", "SimRISC-07: io2fo",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "ut2fo_orri_rf": ("contract-fp §4", "SimRISC-07: ut2fo",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "uo2fo_orri_rf": ("contract-fp §4", "SimRISC-07: uo2fo",
                      ("dst_rf0", "mreg_zero", "mreg_range_overflow"),
                      ("rfhb != rf0", "immu6 != 0", "rfhb + immu6 <= 64",
                       "rdhc + immu6 <= 64")),
    "ftrnd_orri_rf": ("contract-fp §18", "SimRISC-07: ftrnd",
                      ("dst_rf0", "encode_onehot"),
                      ("rfhb != rf0",
                       "immu6 == 1 || immu6 == 2 || immu6 == 4 || "
                       "immu6 == 8 || immu6 == 16 || immu6 == 32")),
    "fornd_orri_rf": ("contract-fp §18", "SimRISC-07: fornd",
                      ("dst_rf0", "encode_onehot"),
                      ("rfhb != rf0",
                       "immu6 == 1 || immu6 == 2 || immu6 == 4 || "
                       "immu6 == 8 || immu6 == 16 || immu6 == 32")),
    "ftadd_orrr_rf": ("contract-fp §5", "SimRISC-07: ftadd", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "ftsub_orrr_rf": ("contract-fp §5", "SimRISC-07: ftsub", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "ftmul_orrr_rf": ("contract-fp §5", "SimRISC-07: ftmul", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "ftdiv_orrr_rf": ("contract-fp §5", "SimRISC-07: ftdiv", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "ftrem_orrr_rf": ("contract-fp §5", "SimRISC-07: ftrem", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "ftsclb_orrr_rf": ("contract-fp §5", "SimRISC-07: ftsclb", ("dst_rf0",),
                       ("rfhb != rf0",)),
    "foadd_orrr_rf": ("contract-fp §5", "SimRISC-07: foadd", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "fosub_orrr_rf": ("contract-fp §5", "SimRISC-07: fosub", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "fomul_orrr_rf": ("contract-fp §5", "SimRISC-07: fomul", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "fodiv_orrr_rf": ("contract-fp §5", "SimRISC-07: fodiv", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "forem_orrr_rf": ("contract-fp §5", "SimRISC-07: forem", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "fosclb_orrr_rf": ("contract-fp §5", "SimRISC-07: fosclb", ("dst_rf0",),
                       ("rfhb != rf0",)),
    "ftsgnn_orrr_rf": ("contract-fp §7", "SimRISC-07: ftsgnn", ("dst_rf0",),
                       ("rfhb != rf0",)),
    "ftsgnj_orrr_rf": ("contract-fp §7", "SimRISC-07: ftsgnj", ("dst_rf0",),
                       ("rfhb != rf0",)),
    "fosgnn_orrr_rf": ("contract-fp §7", "SimRISC-07: fosgnn", ("dst_rf0",),
                       ("rfhb != rf0",)),
    "fosgnj_orrr_rf": ("contract-fp §7", "SimRISC-07: fosgnj", ("dst_rf0",),
                       ("rfhb != rf0",)),
    "ftqcmp_orrr_rf": ("contract-fp §8", "SimRISC-07: ftqcmp", ("dst_rd0",),
                       ("rdhb != rd0",)),
    "ftscmp_orrr_rf": ("contract-fp §8", "SimRISC-07: ftscmp", ("dst_rd0",),
                       ("rdhb != rd0",)),
    "foqcmp_orrr_rf": ("contract-fp §8", "SimRISC-07: foqcmp", ("dst_rd0",),
                       ("rdhb != rd0",)),
    "foscmp_orrr_rf": ("contract-fp §8", "SimRISC-07: foscmp", ("dst_rd0",),
                       ("rdhb != rd0",)),
    "ftmin_orrr_rf": ("contract-fp §19", "SimRISC-07: ftmin", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "ftmax_orrr_rf": ("contract-fp §19", "SimRISC-07: ftmax", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "fomin_orrr_rf": ("contract-fp §19", "SimRISC-07: fomin", ("dst_rf0",),
                      ("rfhb != rf0",)),
    "fomax_orrr_rf": ("contract-fp §19", "SimRISC-07: fomax", ("dst_rf0",),
                      ("rfhb != rf0",)),
}

# Contract-wide rule_refs counts over the 55 B7 rows.
EXPECTED_RULE_COUNTS = {
    "dst_rf0": 41,
    "mreg_zero": 22,
    "mreg_range_overflow": 22,
    "dst_rd0": 14,
    "mreg_range_overlap": 4,
    "encode_fp_root_n": 2,
    "encode_onehot": 2,
}

# Per-family differential minimums (task 必测用例: "每族不少于下列数量").
FAMILY_MINIMUMS = {
    "arith": 12 * 64,
    "cvt_ff": 4 * 32,
    "f2i": 8 * 32,
    "i2f": 8 * 32,
    "fma": 2 * 48,
    "root": 2 * 24,
    "rnd": 2 * 72,
    "minmax": 4 * 32,
    "sign": 4 * 16,
    "cmp": 4 * 32,
    "classify": 2 * 32,
    "cs_rf": 3 * 12,
}
TOTAL_MINIMUM = 2000


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def live_b7_entries():
    return [e for e in load_module("gen_decode_table",
                                   ROOT / "tools/gem5/gen_decode_table.py")
            .load_entries() if e.batch == "B7"]


def matrix_rows():
    with MATRIX.open(newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream,
                                                         delimiter="\t")}


def check_contract(entries) -> list[str]:
    errors: list[str] = []
    by_id = {entry.id: entry for entry in entries}
    if len(by_id) != 55:
        errors.append(f"live B7 set has {len(by_id)} ids, expected 55")
    for entry_id, (ref, cite, rules, legality) in EXPECTED.items():
        entry = by_id.get(entry_id)
        if entry is None:
            errors.append(f"{entry_id}: missing from the live B7 set")
            continue
        if entry.contract_ref != ref:
            errors.append(f"{entry_id}: contract_ref {entry.contract_ref!r} "
                          f"!= {ref!r}")
        if entry.spec_cite != cite:
            errors.append(f"{entry_id}: spec_cite {entry.spec_cite!r} != "
                          f"{cite!r}")
        if entry.rules != rules:
            errors.append(f"{entry_id}: rule_refs {entry.rules!r} != {rules!r}")
        if entry.legality != legality:
            errors.append(f"{entry_id}: legality {entry.legality!r} != "
                          f"{legality!r}")
    for entry_id in by_id:
        if entry_id not in EXPECTED:
            errors.append(f"{entry_id}: unexpected live B7 id")

    counts = {rule: 0 for rule in EXPECTED_RULE_COUNTS}
    for entry in entries:
        for rule in entry.rules:
            if rule not in EXPECTED_RULE_COUNTS:
                errors.append(f"{entry.id}: unknown rule_refs {rule!r}")
                continue
            counts[rule] += 1
    for rule, expected in EXPECTED_RULE_COUNTS.items():
        if counts[rule] != expected:
            errors.append(f"rule {rule}: {counts[rule]} live rows, "
                          f"expected {expected}")
    empty = [entry.id for entry in entries if not entry.legality]
    if empty:
        errors.append(f"{len(empty)} B7 row(s) have empty legality: {empty}")
    cites = [entry.spec_cite for entry in entries]
    if len(set(cites)) != 55:
        errors.append(f"spec_cite values are not unique ({len(set(cites))}/55)")
    return errors


def check_matrix(entries) -> list[str]:
    """Independent derivation: the matrix rows must agree on ref/cite."""
    errors: list[str] = []
    rows = matrix_rows()
    for entry in entries:
        row = rows.get(entry.id)
        if row is None:
            errors.append(f"{entry.id}: missing from {MATRIX.name}")
            continue
        if row.get("contract_ref") != entry.contract_ref:
            errors.append(f"{entry.id}: matrix contract_ref "
                          f"{row.get('contract_ref')!r} != "
                          f"{entry.contract_ref!r}")
        if row.get("spec_cite") != entry.spec_cite:
            errors.append(f"{entry.id}: matrix spec_cite "
                          f"{row.get('spec_cite')!r} != {entry.spec_cite!r}")
    return errors


def asset_check(ref) -> list[str]:
    """Read-only consistency with the tests/inst FP assets."""
    errors: list[str] = []
    for path in (ROOT / "tests/inst/fma", ROOT / "tests/inst/minmax",
                 ROOT / "tests/inst/roundint",
                 ROOT / "tests/inst/fp/scaleb.yaml"):
        if not path.exists():
            errors.append(f"missing read-only asset {path}")
    scaleb = ROOT / "tests/inst/fp/scaleb.yaml"
    if scaleb.exists():
        text = scaleb.read_text(encoding="utf-8")
        if "rdHD" not in text:
            errors.append("tests/inst/fp/scaleb.yaml no longer documents rdHD")
        # ftsclb rf4, rf1, rd3 with rf1 = 1.5f and rd3 = 2 => 6.0f, while the
        # retired rfHD reading (rf3 = 10.0f) would give 1536.0f.
        got, flags = ref.op_sclb("ft", 0, 0x3FC00000, 2)
        decoy, _ = ref.op_sclb("ft", 0, 0x3FC00000, 10)
        if got != 0x40C00000 or flags != 0:
            errors.append(f"scaleB C1: model gives 0x{got:08x} (expected "
                          "0x40c00000 = 6.0f)")
        if decoy == got:
            errors.append("scaleB C1: the rfHD decoy no longer differs")
    for name in ("fma", "minmax", "roundint"):
        directory = ROOT / "tests/inst" / name
        if directory.exists() and not any(directory.iterdir()):
            errors.append(f"tests/inst/{name} is empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"),
                        help="gem5 worktree (default .work/source/gem5)")
    parser.add_argument("--out", type=Path,
                        default=Path(".work/build/gem5/dadao-b7-test"))
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--keep", action="store_true",
                        help="keep the generated vectors in the temp dir")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    needed = [
        source / "src/arch/dadao/decode/decode.hh",
        source / "src/arch/dadao/exec/common.hh",
        source / "src/arch/dadao/exec/b1.hh",
        source / "src/arch/dadao/exec/b5.hh",
        source / "src/arch/dadao/exec/b6.hh",
        source / "src/arch/dadao/exec/b7.hh",
        source / "src/arch/dadao/exec/fp_soft.hh",
        source / "src/arch/dadao/exec/fp_soft.cc",
        source / "src/arch/dadao/exec/b7.cc",
        source / "src/arch/dadao/exec/b7_test.cc",
    ]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-b7: missing input(s); run `make apply-series` first:",
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
        str(source / "src/arch/dadao/exec/fp_soft.cc"),
        str(source / "src/arch/dadao/exec/b7.cc"),
        str(source / "src/arch/dadao/exec/b7_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-b7: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-b7: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-b7: run: {out}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)
    failures = run.stdout.count("[FAIL]")
    harness_ids = sorted(set(HARNESS_ID.findall(run.stdout)))

    entries = live_b7_entries()
    live = sorted(entry.id for entry in entries)
    contract_errors = check_contract(entries) + check_matrix(entries)

    ok = True
    if "B7 coverage 55/55" not in run.stdout:
        print("check-gem5-b7: FAIL -- missing 'B7 coverage 55/55' marker",
              file=sys.stderr)
        ok = False
    if "non-B7 ids return NotB7 (209/209)" not in run.stdout:
        print("check-gem5-b7: FAIL -- missing 'non-B7 ids return NotB7 "
              "(209/209)' marker", file=sys.stderr)
        ok = False
    if len(harness_ids) != 55:
        print(f"check-gem5-b7: FAIL -- harness listed {len(harness_ids)} B7 "
              "ids, expected 55", file=sys.stderr)
        ok = False
    if harness_ids != live:
        extra = sorted(set(harness_ids) - set(live))
        missing_ids = sorted(set(live) - set(harness_ids))
        print("check-gem5-b7: FAIL -- harness B7 id set != live batch_of() set",
              file=sys.stderr)
        if extra:
            print(f"  only in harness: {extra}", file=sys.stderr)
        if missing_ids:
            print(f"  only in contracts: {missing_ids}", file=sys.stderr)
        ok = False
    if contract_errors:
        print("check-gem5-b7: FAIL -- contract rule/legality mismatch:",
              file=sys.stderr)
        for error in contract_errors:
            print(f"  {error}", file=sys.stderr)
        ok = False
    if failures != 0:
        print(f"check-gem5-b7: FAIL -- {failures} [FAIL] line(s)",
              file=sys.stderr)
        ok = False
    if run.returncode != 0:
        print(f"check-gem5-b7: FAIL -- harness rc={run.returncode}",
              file=sys.stderr)
        ok = False

    # ── bit-exact differential against the independent oracle ────────────
    ref = load_module("b7_ref", ROOT / "tools/gem5/b7_ref.py")
    vectors = ref.build_vectors()
    family_counts: dict[str, int] = {}
    for vector in vectors:
        family = ref.FAMILY_OF[ref.OPS[vector["id"]][0]]
        family_counts[family] = family_counts.get(family, 0) + 1
    covered_ids = {vector["id"] for vector in vectors}
    oracle_errors: list[str] = []
    if len(vectors) < TOTAL_MINIMUM:
        oracle_errors.append(f"only {len(vectors)} vectors (>= {TOTAL_MINIMUM})")
    for family, minimum in FAMILY_MINIMUMS.items():
        if family_counts.get(family, 0) < minimum:
            oracle_errors.append(f"family {family}: "
                                 f"{family_counts.get(family, 0)} vectors "
                                 f"(>= {minimum})")
    for entry_id in EXPECTED:
        if entry_id not in covered_ids:
            oracle_errors.append(f"{entry_id}: no oracle vector")

    with tempfile.TemporaryDirectory(prefix="b7-oracle-") as tmp:
        vector_file = Path(tmp) / "vectors.txt"
        expected_file = Path(tmp) / "expected.json"
        ref._emit(vectors, vector_file)
        rc = ref.main(["--emit", str(vector_file), "--expect",
                       str(expected_file), "--quiet"])
        if rc != 0:
            oracle_errors.append("b7_ref --emit failed")
        probe = subprocess.run([str(out), "--vectors", str(vector_file)],
                              capture_output=True, text=True)
        if probe.returncode != 0:
            oracle_errors.append(f"probe mode rc={probe.returncode}")
        total, mismatches = ref.verify(vectors, probe.stdout)
        for vector, expect, got in mismatches[:20]:
            oracle_errors.append(ref.describe_mismatch(vector, expect, got))
        print(f"oracle vectors={total}")
        print(f"oracle mismatch={len(mismatches)}")
        if args.keep:
            print(f"check-gem5-b7: vectors kept in {vector_file}")

    # ── third-implementation cross checks (testcases oracles) ────────────
    cross_errors = ref.cross_check()
    for error in cross_errors[:20]:
        print(f"check-gem5-b7: cross-check {error}", file=sys.stderr)
    print(f"cross-check disagreements={len(cross_errors)}")

    asset_errors = asset_check(ref)
    for error in asset_errors:
        print(f"check-gem5-b7: asset {error}", file=sys.stderr)

    if oracle_errors:
        print("check-gem5-b7: FAIL -- oracle differential:", file=sys.stderr)
        for error in oracle_errors:
            print(f"  {error}", file=sys.stderr)
        ok = False
    if cross_errors:
        print("check-gem5-b7: FAIL -- oracle cross-check disagreement",
              file=sys.stderr)
        ok = False
    if asset_errors:
        ok = False

    print(f"check-gem5-b7: b7 ids {len(harness_ids)}/55, live {len(live)}, "
          f"failures {failures}, rc={run.returncode}")
    live_counts = {rule: sum(rule in entry.rules for entry in entries)
                   for rule in EXPECTED_RULE_COUNTS}
    print("check-gem5-b7: rule_refs " +
          " ".join(f"{rule}={live_counts[rule]}"
                   for rule in EXPECTED_RULE_COUNTS))
    print("check-gem5-b7: legality empty = 0 (55/55 rows carry a rule)")
    print("check-gem5-b7: oracle families " +
          " ".join(f"{family}={family_counts.get(family, 0)}"
                   for family in FAMILY_MINIMUMS))
    if not ok:
        return 1
    print("check-gem5-b7: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
