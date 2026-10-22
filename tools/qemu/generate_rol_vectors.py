#!/usr/bin/env python3
"""Generate tests/vectors/rol/rol.yaml — L3 semantic vectors for `rol.{o,t,w,b}`.

Source of truth (Spec-first, no QEMU/LLVM reverse-engineering):
  * contracts/opcodes.yaml            — encoding (op/ha/mask/value), id, format
  * spec/SimRISC-04 §2.2.3            — rol.o definition
  * spec/SimRISC-08/09/10 §2.2.2      — rol.t/.w/.b width/mod/ILLI rules
  * contracts/legality_rules.yaml     — dst_rd0 / encode_sbz

The expected value is derived from the rotate definition itself:
    rol(x, n, W) = ((x << (n mod W)) | (x >> (W - (n mod W)))) & (2**W - 1)
and stored zero-extended to 64 bits (SPEC-069t value semantics).

`rol` identities are `scope: m9`, so they cannot live under
`tests/vectors/isa/` (validate_vectors.py requires `tests/vectors/isa/*.yaml`
ids to be M1 identities).  They live in their own directory, following the
`tests/vectors/rev/` + `tests/vectors/bitcnt/` precedent, and are wired into
`check-qemu-semantics` via the Makefile carrier list.

Usage:
  python3 tools/qemu/generate_rol_vectors.py           # write the YAML
  python3 tools/qemu/generate_rol_vectors.py --check   # fail if committed YAML drifts
"""

from __future__ import annotations

import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES = os.path.join(ROOT, "contracts", "opcodes.yaml")
OUT = os.path.join(ROOT, "tests", "vectors", "rol", "rol.yaml")

WIDTH = {"rol.o": 64, "rol.t": 32, "rol.w": 16, "rol.b": 8}

# Spec-mandated rotate amounts (orrr register form) per width.
ORRR_AMOUNTS = {
    64: [0, 1, 31, 32, 63, 65],   # 65 proves rdhd[5:0] => mod 64
    32: [0, 1, 15, 31, 35],       # 35 proves rdhd[4:0] => mod 32
    16: [0, 1, 7, 15, 19],        # 19 proves rdhd[3:0] => mod 16
    8: [0, 1, 3, 7, 11],          # 11 proves rdhd[2:0] => mod 8
}
# orri immediate form: only 0..W-1 is legal; W itself is ILLI.
ORRI_AMOUNTS = {
    64: [0, 1, 62, 63],
    32: [0, 1, 30, 31],
    16: [0, 1, 14, 15],
    8: [0, 1, 6, 7],
}

DEST_OLD = 0xFFFFFFFFFFFFFFFF       # proves the result is written in full
SRC_PATTERN = 0xA5C396F1DEADBEEF    # nontrivial bit pattern


def _int(v):
    if isinstance(v, int):
        return v
    return int(str(v).strip(), 0)


def _hex64(v):
    return "0x%016X" % (v & 0xFFFFFFFFFFFFFFFF)


def rol(x, n, width):
    """Logical rotate left of the low `width` bits (independent oracle)."""
    mask = (1 << width) - 1
    x &= mask
    n %= width
    return ((x << n) | (x >> (width - n))) & mask


def src_for(width):
    """Low `width` bits = pattern; higher bits set to exercise truncation."""
    mask = (1 << width) - 1
    return (0xFFFFFFFFFFFFFFFF & ~mask) | (SRC_PATTERN & mask)


def build_word(rec, hb, hc, hd):
    op = _int(rec["op"])
    ha = _int(rec["ha"])
    return (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd


def case(rec, cls, word, input_state, expected_state, fault, spec_cite, notes):
    return {
        "mnemonic": rec["mnemonic"],
        "id": rec["id"],
        "format": rec["format"],
        "class": cls,
        "encoding": {"word": "0x%08X" % word},
        "input_state": input_state,
        "expected_state": expected_state,
        "expected_pc": None,
        "expected_fault": fault,
        "status": "active",
        "deferred_reason": None,
        "spec_cite": spec_cite,
        "notes": notes,
    }


def rd_state(rd1=None, rd2=None, rd3=None):
    rd = {}
    if rd1 is not None:
        rd["rd1"] = _hex64(rd1)
    if rd2 is not None:
        rd["rd2"] = _hex64(rd2)
    if rd3 is not None:
        rd["rd3"] = _hex64(rd3)
    return {"rd": rd, "rb": {}, "ra": {}, "memory": []}


def out_state(value):
    return {"rd": {"rd1": _hex64(value)}, "rb": {}, "ra": {}, "memory": []}


def gen_cases(rec):
    mnem = rec["mnemonic"]
    width = WIDTH[mnem]
    spec = rec["spec_cite"]
    out = []

    # 1. encoding: legal fields, no fault
    word = build_word(rec, 1, 2, 0)
    out.append(case(rec, "encoding", word, {}, None, None, spec,
                    "encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI"))

    if rec["format"] == "orrr":
        # 2. semantic: register-form amounts (incl. mod-W overflow of rdhd)
        for amount in ORRR_AMOUNTS[width]:
            src = src_for(width)
            word = build_word(rec, 1, 2, 3)
            exp = rol(src, amount, width)
            out.append(case(
                rec, "semantic", word,
                rd_state(rd1=DEST_OLD, rd2=src, rd3=amount), out_state(exp), None,
                spec,
                "%s orrr: rd2(src)=%s rd3(amount)=%d -> amount mod %d = %d, W=%d"
                % (mnem, _hex64(src), amount, width, amount % width, width)))
        # 3. boundary: maximum legal register amount (W-1)
        amount = width - 1
        src = src_for(width)
        word = build_word(rec, 1, 2, 3)
        out.append(case(
            rec, "boundary", word,
            rd_state(rd1=DEST_OLD, rd2=src, rd3=amount),
            out_state(rol(src, amount, width)), None, spec,
            "boundary %s orrr: rd3=%d=W-1, W=%d" % (mnem, amount, width)))
    else:
        # 2. semantic: immediate amounts
        for amount in ORRI_AMOUNTS[width]:
            src = src_for(width)
            word = build_word(rec, 1, 2, amount)
            exp = rol(src, amount, width)
            out.append(case(
                rec, "semantic", word,
                rd_state(rd1=DEST_OLD, rd2=src), out_state(exp), None, spec,
                "%s orri: rd2(src)=%s immu6=%d, W=%d"
                % (mnem, _hex64(src), amount, width)))
        # 3. boundary: maximum legal immediate (W-1)
        amount = width - 1
        src = src_for(width)
        word = build_word(rec, 1, 2, amount)
        out.append(case(
            rec, "boundary", word,
            rd_state(rd1=DEST_OLD, rd2=src),
            out_state(rol(src, amount, width)), None, spec,
            "boundary %s orri: immu6=%d=W-1, W=%d" % (mnem, amount, width)))
        # 4. legality: immu6 out of range (immu6 == W) => ILLI
        if width < 64:
            word = build_word(rec, 1, 2, width)
            out.append(case(
                rec, "legality", word, {}, None, "ILLI",
                spec + "; SimRISC-00 §指令域说明",
                "legality %s orri: immu6=%d > W-1=%d -> ILLI (encode_sbz)"
                % (mnem, width, width - 1)))

    # 5. legality: destination rd0 => ILLI (dst_rd0)
    word = build_word(rec, 0, 2, 0)
    out.append(case(
        rec, "legality", word, {}, None, "ILLI",
        spec + "; SimRISC-00 §数据寄存器",
        "legality %s: dest rdHB=rd0 -> ILLI (dst_rd0)" % mnem))

    return out


def main() -> int:
    with open(OPCODES, encoding="utf-8") as fh:
        records = yaml.safe_load(fh)
    rol_recs = [r for r in records if r.get("mnemonic", "").split(".")[0] == "rol"]
    assert len(rol_recs) == 8, len(rol_recs)

    cases = []
    for rec in rol_recs:
        cases.extend(gen_cases(rec))

    text = "".join([
        "# Generated by tools/qemu/generate_rol_vectors.py — DO NOT EDIT\n",
        "# Source: contracts/opcodes.yaml + SimRISC-04/08/09/10 §2.2 + legality_rules\n",
        "# Independent oracle: rol(x, n, W) = ((x << (n%W)) | (x >> (W-n%W))) & (2^W-1)\n\n",
        yaml.dump(cases, default_flow_style=False, allow_unicode=True, width=120),
    ])

    if "--check" in sys.argv:
        with open(OUT, encoding="utf-8") as fh:
            committed = fh.read()
        if committed != text:
            print("generate_rol_vectors: FAIL (committed YAML drifts from generator)")
            return 1
        print("generate_rol_vectors: PASS (%d cases, byte-identical)" % len(cases))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("generate_rol_vectors: wrote %s (%d cases, %d identities)"
          % (os.path.relpath(OUT, ROOT), len(cases), len(rol_recs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
