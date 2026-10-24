#!/usr/bin/env python3
"""Generate tests/vectors/clmul/clmul.yaml — L3 semantic vectors for `clmul.o`.

Source of truth (Spec-first; no QEMU/LLVM reverse-engineering):
  * spec/SimRISC-04: 无进位乘法        — clmul.o: rdHC/rdHD are 64-bit GF(2)
                                  polynomials; 128-bit product, rdHA = high 64,
                                  rdHB = low 64; rd0 on one side discards that
                                  half; both rd0 or same non-rd0 dest => ILLI.
  * contracts/opcodes.yaml      — encoding (opc 0x56, fields rdha/rdhb/rdhc/rdhd)
  * ADR-0035 D2/D4/D6           — layout and rd0 rules

The expected product is derived from the definition itself, independently of
any implementation:

    clmul(a, b) = XOR over every set bit i of b of (a << i)

i.e. a per-bit AND/XOR accumulation with **no carries**, evaluated with
Python arbitrary-precision integers.  `self_check()` first proves the
implementation satisfies the GF(2) polynomial identities (`a * 1 == a`,
`(1 << k) * (1 << m) == 1 << (k + m)`, commutativity, associativity) before
any vector is emitted.

`clmul.o` is still `scope: excluded` in contracts/opcodes.yaml (the scope flip
belongs to SPEC-155t), so its vectors cannot live under `tests/vectors/isa/`
(validate_vectors.py requires isa/*.yaml ids to be M1 identities).  They live
in `tests/vectors/clmul/` and are registered as an L3 carrier in
`tools/qemu/semantics_gate.py`.

Usage:
  python3 tools/qemu/generate_clmul_vectors.py           # write the YAML
  python3 tools/qemu/generate_clmul_vectors.py --check   # fail if committed YAML drifts
"""

from __future__ import annotations

import os
import random
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES = os.path.join(ROOT, "contracts", "opcodes.yaml")
OUT = os.path.join(ROOT, "tests", "vectors", "clmul", "clmul.yaml")

MASK64 = (1 << 64) - 1
SEED = 0xC1A0  # fixed seed, recorded in the generated header
RANDOM_CASES = 64

# Fixed operand pairs mandated by the task book (coverage classes).
FIXED_PAIRS = [
    (0, 0),                       # zero * zero
    (0, 0xFFFFFFFFFFFFFFFF),      # zero operand absorbs everything
    (1, 0xA5C396F1DEADBEEF),      # a * 1 == a (x^0 is the identity)
    (1 << 0, 1 << 63),            # lowest * highest single term
    (1 << 63, 1 << 63),           # x^126 term, crosses into the high half
    (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF),  # all ones * all ones
    (1 << 63, 0xFFFFFFFFFFFFFFFF),             # dense high-half contribution
    (0xFFFFFFFFFFFFFFFF, 0x0123456789ABCDEF),  # dense * sparse-ish
]


def clmul_full(a: int, b: int) -> int:
    """Carry-less multiply over arbitrary-precision non-negative ints.

    Used only by the associativity self-check, where the intermediate product
    legitimately exceeds 64 bits (masking it would be a truncation, not an
    algebraic identity).
    """
    result = 0
    i = 0
    while b:
        if b & 1:
            result ^= a << i
        b >>= 1
        i += 1
    return result


def clmul(a: int, b: int) -> int:
    """Carry-less multiply of two 64-bit GF(2) polynomials (independent oracle)."""
    return clmul_full(a & MASK64, b & MASK64)


def self_check() -> list[str]:
    """Prove the oracle satisfies the GF(2) polynomial identities; return failures."""
    errs = []
    identity = 0x0123456789ABCDEF

    # a * 1 == a (several probes)
    for a in (0, 1, 1 << 63, identity, MASK64):
        if clmul(a, 1) != a:
            errs.append("a*1 != a for a=%#x" % a)

    # (1 << k) * (1 << m) == 1 << (k + m)
    for k, m in ((0, 0), (0, 63), (1, 2), (31, 32), (63, 63)):
        got = clmul(1 << k, 1 << m)
        want = 1 << (k + m)
        if got != want:
            errs.append("(1<<%d)*(1<<%d) = %#x, want %#x" % (k, m, got, want))

    # commutativity (>= 3 groups)
    for a, b in ((identity, MASK64), (1 << 63, 0xDEADBEEF), (0, 0xFFFF)):
        if clmul(a, b) != clmul(b, a):
            errs.append("commutativity failed for (%#x, %#x)" % (a, b))

    # associativity (>= 3 groups)
    for a, b, c in ((identity, MASK64, 0xF0F0F0F0F0F0F0F0),
                    (1 << 63, 3, 5),
                    (0xAAAA5555AAAA5555, 0x123456789ABCDEF0, 0x0F0F0F0F0F0F0F0F)):
        if clmul_full(clmul_full(a, b), c) != clmul_full(a, clmul_full(b, c)):
            errs.append("associativity failed for (%#x, %#x, %#x)" % (a, b, c))

    return errs


def _int(val) -> int:
    if isinstance(val, int):
        return val
    return int(str(val).strip(), 0)


def _hex64(val: int) -> str:
    return "0x%016X" % (val & MASK64)


def build_word(rec, ha: int, hb: int, hc: int, hd: int) -> int:
    op = _int(rec["opc"])
    return (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd


def case(rec, cls, word, input_state, expected_state, fault, notes):
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
        "spec_cite": rec["spec_cite"],
        "notes": notes,
    }


def state(rd: dict) -> dict:
    return {"rd": rd, "rb": {}, "ra": {}, "memory": []}


def gen_cases(rec) -> list:
    out = []
    old_dst = 0xAAAAAAAAAAAAAAAA  # preloaded destination value (must be replaced)
    sentinel = 0x5A5A5A5A5A5A5A5A  # untouched register (proves no stray write)

    # 1. encoding: legal fields, no fault.
    out.append(case(
        rec, "encoding", build_word(rec, 1, 2, 3, 4), {}, None, None,
        "encoding: op=0x56, fields rd1/rd2/rd3/rd4 legal; no ILLI"))

    # 2. semantic / boundary: fixed mandated pairs (rdHA=hi, rdHB=lo).
    for a, b in FIXED_PAIRS:
        prod = clmul(a, b)
        cls = "boundary" if a in (0, 1, MASK64) or b in (0, 1, MASK64) else "semantic"
        out.append(case(
            rec, cls, build_word(rec, 1, 2, 3, 4),
            state({"rd1": _hex64(old_dst), "rd2": _hex64(old_dst),
                   "rd3": _hex64(a), "rd4": _hex64(b)}),
            state({"rd1": _hex64(prod >> 64), "rd2": _hex64(prod)}), None,
            "clmul.o: rd3=%s rd4=%s -> hi=%s lo=%s (GF(2), no carries)"
            % (_hex64(a), _hex64(b), _hex64(prod >> 64), _hex64(prod))))

    # 3. semantic: fixed-seed random pairs (seed recorded in the header).
    rng = random.Random(SEED)
    for _ in range(RANDOM_CASES):
        a = rng.getrandbits(64)
        b = rng.getrandbits(64)
        prod = clmul(a, b)
        out.append(case(
            rec, "semantic", build_word(rec, 1, 2, 3, 4),
            state({"rd1": _hex64(old_dst), "rd2": _hex64(old_dst),
                   "rd3": _hex64(a), "rd4": _hex64(b)}),
            state({"rd1": _hex64(prod >> 64), "rd2": _hex64(prod)}), None,
            "clmul.o random (seed %#x): rd3=%s rd4=%s -> hi=%s lo=%s"
            % (SEED, _hex64(a), _hex64(b),
               _hex64(prod >> 64), _hex64(prod))))

    # 4. rd0 single-side discard, both directions, two examples each.
    #    {rd0, rd5}: only the low half is written to rd5; rd1 is untouched.
    for a, b in ((0x0123456789ABCDEF, 0xFEDCBA9876543210), (1 << 63, 3)):
        prod = clmul(a, b)
        out.append(case(
            rec, "semantic", build_word(rec, 0, 5, 3, 4),
            state({"rd1": _hex64(sentinel), "rd3": _hex64(a),
                   "rd4": _hex64(b)}),
            state({"rd1": _hex64(sentinel), "rd5": _hex64(prod)}), None,
            "clmul.o {rd0,rd5},rd3,rd4: high half discarded, rd5=lo=%s; "
            "sentinel rd1 unchanged" % _hex64(prod)))
    #    {rd5, rd0}: only the high half is written to rd5; rd1 is untouched.
    for a, b in ((0x0123456789ABCDEF, 0xFEDCBA9876543210), (1 << 63, 3)):
        prod = clmul(a, b)
        out.append(case(
            rec, "semantic", build_word(rec, 5, 0, 3, 4),
            state({"rd1": _hex64(sentinel), "rd3": _hex64(a),
                   "rd4": _hex64(b)}),
            state({"rd1": _hex64(sentinel), "rd5": _hex64(prod >> 64)}), None,
            "clmul.o {rd5,rd0},rd3,rd4: low half discarded, rd5=hi=%s; "
            "sentinel rd1 unchanged" % _hex64(prod >> 64)))

    # 5. overlap: destination == source must observe the pre-write source value
    #    (spec §3.5: hardware reads all sources before writing results).
    a, b = 0x0123456789ABCDEF, 0xFEDCBA9876543210
    prod = clmul(a, b)
    out.append(case(
        rec, "overlap", build_word(rec, 1, 2, 1, 4),
        state({"rd1": _hex64(a), "rd2": _hex64(old_dst), "rd4": _hex64(b)}),
        state({"rd1": _hex64(prod >> 64), "rd2": _hex64(prod)}), None,
        "clmul.o {rd1,rd2},rd1,rd4: high dest == source rd1; "
        "sources read before write -> hi=%s lo=%s"
        % (_hex64(prod >> 64), _hex64(prod))))
    out.append(case(
        rec, "overlap", build_word(rec, 1, 2, 3, 1),
        state({"rd1": _hex64(b), "rd2": _hex64(old_dst), "rd3": _hex64(a)}),
        state({"rd1": _hex64(prod >> 64), "rd2": _hex64(prod)}), None,
        "clmul.o {rd1,rd2},rd3,rd1: low dest == source rd1; "
        "sources read before write -> hi=%s lo=%s"
        % (_hex64(prod >> 64), _hex64(prod))))

    # 6. legality: dst_dual_same violations => ILLI (executed, not a table read).
    out.append(case(
        rec, "legality", build_word(rec, 0, 0, 3, 4), {}, None, "ILLI",
        "clmul.o {rd0,rd0},rd3,rd4 -> ILLI (both destinations rd0)"))
    out.append(case(
        rec, "legality", build_word(rec, 5, 5, 3, 4), {}, None, "ILLI",
        "clmul.o {rd5,rd5},rd3,rd4 -> ILLI (same non-rd0 destination)"))

    return out


def main() -> int:
    with open(OPCODES, encoding="utf-8") as fh:
        records = yaml.safe_load(fh)
    recs = [r for r in records if r.get("id") == "clmul.o_rrrr_rd"]
    if len(recs) != 1:
        print("generate_clmul_vectors: FAIL (clmul.o_rrrr_rd not found uniquely)")
        return 1
    rec = recs[0]

    errs = self_check()
    if errs:
        for e in errs:
            print("generate_clmul_vectors: self-check FAIL: %s" % e)
        return 1
    print("generate_clmul_vectors: oracle self-check PASS "
          "(identity/term/commutativity/associativity)")

    cases = gen_cases(rec)
    text = "".join([
        "# Generated by tools/qemu/generate_clmul_vectors.py — DO NOT EDIT\n",
        "# Source: spec/SimRISC-04: 无进位乘法 + contracts/opcodes.yaml + ADR-0035 D2/D4/D6\n",
        "# Independent oracle: clmul(a,b) = XOR over set bit i of b of (a << i);\n",
        "#   self-checked for a*1==a, (1<<k)*(1<<m)==1<<(k+m), commutativity,\n",
        "#   associativity.  Random cases: %d, seed %#x.\n\n" % (RANDOM_CASES, SEED),
        yaml.dump(cases, default_flow_style=False, allow_unicode=True, width=120),
    ])

    if "--check" in sys.argv:
        with open(OUT, encoding="utf-8") as fh:
            committed = fh.read()
        if committed != text:
            print("generate_clmul_vectors: FAIL (committed YAML drifts from generator)")
            return 1
        print("generate_clmul_vectors: PASS (%d cases, byte-identical)" % len(cases))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("generate_clmul_vectors: wrote %s (%d cases)"
          % (os.path.relpath(OUT, ROOT), len(cases)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
