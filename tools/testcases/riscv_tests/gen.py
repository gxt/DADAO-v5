#!/usr/bin/env python3
"""Emit a DADAO riscv-tests port artifact from a committed case vector.

Input:  tests/riscv-tests/cases/<suite>/<name>.yaml
Output: one flat `.s` file (assembled to a raw bin by run_riscv_tests.py).

Framework mapping (m13-integ-004):
  * startup     `_start` is placed at the profile RAM entry (Tiny BootROM sets
                SP and jumps there); no C runtime.
  * signature   each check stores the observed octa at
                ENTRY + SIG_OFF + 8*i; the epilogue prints the whole region
                as hex ("SIG" + one 16-digit line per case) over semihosting,
                the equivalent of riscv-tests begin_signature/end_signature.
  * tohost      semihosting SYS_EXIT: 0 = pass, 0x40|(first failing testnum &
                0x3F) = fail (spec/Machine-v5 §7.1, ADR-0020 D8).
  * checks      compare the architectural result against the upstream
                expected value; the first mismatch is recorded and reported.

The generator is deliberately dumb: every DADAO op mapping is a table entry,
so an unsupported op fails loudly instead of emitting a silent stub.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML is required\n")
    sys.exit(2)

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

SIG_OFF = 0x4000
BUF_OFF = 0x3000
STR_OFF = 0x2000
TBL_OFF = 0x2020

# DADAO registers: rd1 = constant 1, rd2 = 0x3f, rd10/rd11 = sources,
# rd12/rd13 = result (lo/hi), rd14 = expected, rd15 = compare scratch,
# rd30 = first failing test number, rb20 = signature cursor.
RD_ONE, RD_MASK63 = "rd1", "rd2"
RD_A, RD_B, RD_LO, RD_HI = "rd10", "rd11", "rd12", "rd13"
RD_EXP, RD_CMP, RD_FAIL = "rd14", "rd15", "rd30"
RB_SIG = "rb20"


def hx(v):
    return f"0x{v:016x}"


def emit_op(op: str) -> list[str]:
    """Return the DADAO instruction sequence for one upstream mnemonic.

    Conventions: inputs in RD_A/RD_B, low result in RD_LO, high result in
    RD_HI, constant 1 in RD_ONE.  Unknown mnemonics raise (no fake pass).
    """
    if op in ("add", "addi"):
        return [f"add.uo {{{RD_HI}, {RD_LO}}}, {RD_A}, {RD_B}"]
    if op in ("sub",):
        return [f"sub.uo {{{RD_HI}, {RD_LO}}}, {RD_A}, {RD_B}"]
    if op in ("addw", "addiw"):
        return [f"add.st {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("subw",):
        return [f"sub.st {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("and", "andi"):
        return [f"and.o {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("or", "ori"):
        return [f"or.o {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("xor", "xori"):
        return [f"xor.o {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("sll", "slli"):
        return [f"shl.o {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("srl", "srli"):
        return [f"shr.uo {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("sra", "srai"):
        return [f"shr.so {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("sllw", "slliw"):
        return [f"shl.t {RD_LO}, {RD_A}, {RD_B}",
                f"ext.so {RD_LO}, {RD_LO}, 31"]
    if op in ("srlw", "srliw"):
        return [f"shr.ut {RD_LO}, {RD_A}, {RD_B}",
                f"ext.so {RD_LO}, {RD_LO}, 31"]
    if op in ("sraw", "sraiw"):
        return [f"shr.st {RD_LO}, {RD_A}, {RD_B}"]
    if op in ("slt", "slti"):
        return [f"cmp.so {RD_LO}, {RD_A}, {RD_B}",
                f"shr.so {RD_LO}, {RD_LO}, 63",
                f"and.o {RD_LO}, {RD_LO}, {RD_ONE}"]
    if op in ("sltu", "sltiu"):
        return [f"cmp.uo {RD_LO}, {RD_A}, {RD_B}",
                f"shr.so {RD_LO}, {RD_LO}, 63",
                f"and.o {RD_LO}, {RD_LO}, {RD_ONE}"]
    if op == "mul":
        return [f"mul.so {{{RD_HI}, {RD_LO}}}, {RD_A}, {RD_B}"]
    if op == "mulh":
        return [f"mul.so {{{RD_LO}, {RD_HI}}}, {RD_A}, {RD_B}"]
    if op == "mulhu":
        return [f"mul.uo {{{RD_LO}, {RD_HI}}}, {RD_A}, {RD_B}"]
    if op == "div":
        return [f"div.so {RD_LO}, {RD_A}, {RD_B}"]
    if op == "divu":
        return [f"div.uo {RD_LO}, {RD_A}, {RD_B}"]
    if op == "rem":
        return [f"rem.so {RD_LO}, {RD_A}, {RD_B}"]
    if op == "remu":
        return [f"rem.uo {RD_LO}, {RD_A}, {RD_B}"]
    raise KeyError(f"gen: no DADAO mapping for mnemonic {op!r}")


def load_rd(rd: str, val: int) -> list[str]:
    val = val & ((1 << 64) - 1)
    out = [f"\tset.zw {rd}, wp0, 0x{val & 0xFFFF:04x}"]
    for wp in (1, 2, 3):
        out.append(f"\tor.w {rd}, wp{wp}, 0x{(val >> (16 * wp)) & 0xFFFF:04x}")
    return out


def emit(case: dict) -> list[str]:
    src1 = int(case["src1"], 16)
    src2 = int(case["src2"], 16)
    expected = int(case["expected"], 16)
    tn = int(case["testnum"])
    if tn <= 0 or tn > 0xFFFF:
        raise SystemExit(f"gen: testnum {tn} cannot be encoded in a wyde")
    lines = [
        f"\t@@ case {tn}: RISC-V {case['op']} -> expected {hx(expected)}",
        f"test_{tn}:",
    ]
    lines += load_rd(RD_A, src1)
    lines += load_rd(RD_B, src2)
    lines += ["\t" + x for x in emit_op(case["op"])]
    lines += [
        f"\tst.o {RD_LO}, [{RB_SIG}, 0]",
        f"\tadd.si {RB_SIG}, 8",
    ]
    lines += load_rd(RD_EXP, expected)
    lines += [
        f"\tcmp.uo {RD_CMP}, {RD_LO}, {RD_EXP}",
        f"\tbr.z {{{RD_CMP}}}?, [rb0, ok_{tn}]",
        f"\tbr.nz {{{RD_FAIL}}}?, [rb0, ok_{tn}]",
        f"\tset.zw {RD_FAIL}, wp0, 0x{tn:04x}",
        f"ok_{tn}:",
    ]
    return lines


def render(case_doc: dict, inject: str | None = None) -> tuple[str, list[int], dict]:
    cases = case_doc["cases"]
    if inject == "guest":
        # Corrupt the *guest* comparison constant: the guest self-check must
        # fail and the host oracle must stay correct.
        cases = [dict(c) for c in cases]
        cases[0]["expected"] = hx(int(cases[0]["expected"], 16) ^ 1)
    lines = [
        f"@@ Generated from {case_doc['upstream']} "
        f"(upstream sha256 {case_doc['upstream_sha256']})",
        "@@ m13-integ-004: DADAO port framework (see "
        "tests/riscv-tests/framework/dadao_test.inc)",
        '\t.include "dadao_test.inc"',
        "\t.text",
        "\t.globl _start",
        "_start:",
        f"\tset.zw {RD_ONE}, wp0, 1",
        f"\tset.zw {RD_MASK63}, wp0, 0x003f",
        f"\tset.zw {RD_FAIL}, wp0, 0",
        f"\tLOAD_ADDR {RB_SIG}, ENTRY + 0x{SIG_OFF:x}",
    ]
    for case in cases:
        lines += emit(case)
    lines += [
        "\t@@ ---- signature dump: SIG + one 16-digit hex line per case ----",
        f"dump_sig:",
        f"\tset.zw rd16, wp0, 0x0004",
        f"\tLOAD_ADDR rb16, ENTRY + 0x{STR_OFF:x}",
        f"\ttrap cfx0, 0x3FF00",
        f"\tLOAD_ADDR rb10, ENTRY + 0x{SIG_OFF:x}",
        f"\tLOAD_ADDR rb13, ENTRY + 0x{TBL_OFF:x}",
        f"\tLOAD_ADDR rb11, ENTRY + 0x{BUF_OFF:x}",
        f"\tset.zw rd20, wp0, 0x{len(cases):04x}",
        f"\tset.zw rd27, wp0, 0x000f",
        f"\tset.zw rd28, wp0, 0x000a",
        f"\tset.zw rd29, wp0, 0x0000",
        "dump_loop:",
        "\tld.o rd21, [rb10, 0]",
        "\tset.zw rd22, wp0, 16",
        "\tset.zw rd23, wp0, 60",
        "nib_loop:",
        "\tshr.uo rd25, rd21, rd23",
        "\tand.o rd25, rd25, rd27",
        "\tadd.o rb12, rb13, rd25",
        "\tld.ub rd26, [rb12, 0]",
        "\tst.b rd26, [rb11, 0]",
        "\tadd.si rb11, 1",
        "\tadd.si rd23, -4",
        "\tadd.si rd22, -1",
        "\tbr.nz {rd22}?, [rb0, nib_loop]",
        "\tst.b rd28, [rb11, 0]",
        "\tadd.si rb11, 1",
        "\tst.b rd29, [rb11, 0]",
        "\tset.zw rd16, wp0, 4",
        f"\tLOAD_ADDR rb16, ENTRY + 0x{BUF_OFF:x}",
        "\ttrap cfx0, 0x3FF00",
        f"\tLOAD_ADDR rb11, ENTRY + 0x{BUF_OFF:x}",
        "\tadd.si rb10, 8",
        "\tadd.si rd20, -1",
        "\tbr.nz {rd20}?, [rb0, dump_loop]",
        "\t@@ ---- exit: 0 = pass, 0x40 | (first failing testnum & 0x3F) ----",
        f"\tbr.z {{{RD_FAIL}}}?, [rb0, exit_pass]",
        f"\tand.o {RD_FAIL}, {RD_FAIL}, {RD_MASK63}",
        f"\tor.w {RD_FAIL}, wp0, 0x0040",
        "\tjump [rb0, exit_common]",
        "exit_pass:",
        f"\tset.zw {RD_FAIL}, wp0, 0",
        "exit_common:",
        "\tLOAD_ADDR rb16, EXIT_BLOCK",
        "\tset.zw rd8, wp1, 0x0002",
        "\tor.w rd8, wp0, 0x0026",
        "\tst.o rd8, [rb16, 0]",
        f"\tst.o {RD_FAIL}, [rb16, 8]",
        "\tset.zw rd16, wp0, 0x0018",
        "\ttrap cfx0, 0x3FF00",
        "\tswym 0",
        "\t@@ ---- fixed data block (absolute addresses: ENTRY + STR/TBL off) ----",
        f"\t.org 0x{STR_OFF:x}",
        "\t.dd.b08 0x53, 0x49, 0x47, 0x0a, 0x00",
        f"\t.org 0x{TBL_OFF:x}",
        "\t.dd.b08 " + ", ".join(
            f"0x{b:02x}" for b in b"0123456789abcdef"),
    ]
    expected_sig = [int(c["expected"], 16) for c in case_doc["cases"]]
    meta = {"upstream": case_doc["upstream"], "cases": len(cases),
            "signature": [hx(v) for v in expected_sig]}
    return "\n".join(lines) + "\n", expected_sig, meta


def load_case_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or not isinstance(doc.get("cases"), list):
        raise SystemExit(f"gen: {path}: missing cases list")
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--inject", choices=("guest", "host"), default=None,
                    help="guest: corrupt the guest comparison constant; "
                         "host: corrupt the host oracle signature")
    ap.add_argument("--meta-json", default=None)
    args = ap.parse_args(argv)
    doc = load_case_file(args.case_file)
    asm, expected_sig, meta = render(doc, inject=args.inject)
    if args.inject == "host":
        expected_sig[0] ^= 1
        meta["signature"][0] = hx(expected_sig[0])
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(asm)
    if args.meta_json:
        with open(args.meta_json, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
