#!/usr/bin/env python3
"""Independent oracle for TESTCASES-058t: ``ftfma``/``fofma`` (fusedMultiplyAdd).

Spec sources (expectations are derived from these, NEVER from QEMU/LLVM and
never from softfloat or a host ``fma``):
  * ``spec/SimRISC-07 §2.5 融合乘加（fusedMultiplyAdd）`` -- exact product,
    ONE rounding of the exact sum, rf0[33:32] mode, the special-value rules
    (qNaN/sNaN, ``0 x Inf``, ``Inf + (-Inf)``, zero sign, OF/UF/NX);
  * ``.tao/contracts/contract-fp.md §20 `fma` `` -- the same, frozen;
  * ``spec/SimRISC-00 §浮点状态寄存器`` / ``contract-fp.md §1`` -- rf0 layout:
    ``[33:32]`` round mode, ``[4:0]`` flags (NV DZ OF UF NX); writes update only
    those bits;
  * ADR-0004 D2 -- rf0 reset value ``0x7FF8_0000_7FC0_0000``.

Arithmetic is exact: IEEE bit patterns are decoded to ``fractions.Fraction``,
the product and the sum stay exact, and the final value is rounded **once**
with integer arithmetic.  ``two_step_expect`` models the *wrong* ``fmul`` +
``foadd`` sequence and exists only to prove the discriminators really differ
and to drive a reachable-FAIL injection.

Probe contract
--------------
The C probes print raw observations only; the operand table lives here too and
the judge compares the printed operands with this table.  A mistyped C literal
is therefore a hard FAIL, never a silent pass.

Self proof (``--selftest``)
---------------------------
1. the spec's own counter-example (``a = 1+2^-23``, ``b = 1-2^-23``,
   ``c = -1`` -> ``0xA880_0000`` = ``-2^-46``) and a hand-written boundary
   table (qNaN / sNaN / ``0xInf`` / ``Inf-Inf`` / zero sign / overflow /
   underflow) state the expected bits directly, so a broken rule engine is red;
2. every discriminator case must have ``fused != two_step`` (valid cases);
3. finite round-to-nearest results are re-derived through a second,
   independent implementation (CPython's correctly-rounded ``float`` for
   binary64 and ``struct.pack('>f')`` for binary32 -- binary64 has 53 >= 2*24+2
   bits, so the double rounding is innocuous for the normal range);
4. ``encode``/``decode`` round-trip for every table operand;
5. wrong-expectation injections (expected value replaced by the two-step value,
   sNaN NV forced to 0) must be reported red, so the judge itself has a
   reachable FAIL path.

Usage
-----
  oracle_fma.py --selftest
  oracle_fma.py --dump          # expected table for hand review
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
from fractions import Fraction

# ── formats ────────────────────────────────────────────────────────────────
FMT = {
    "ft": {"w": 32, "fracbits": 23, "eb": 8, "p": 24, "bias": 127,
           "emax": 127, "emin": -126, "signpos": 31},
    "fo": {"w": 64, "fracbits": 52, "eb": 11, "p": 53, "bias": 1023,
           "emax": 1023, "emin": -1022, "signpos": 63},
}

# rf0 (FCSR) layout: [63:51]/[31:22] read-only qNaN, [33:32] mode, [4:0] flags.
RF0_RESET = 0x7FF800007FC00000
RF0_WRITABLE = (0x3 << 32) | 0x1F
RF0_READONLY = RF0_RESET & ~RF0_WRITABLE

FLAG_NV, FLAG_DZ, FLAG_OF, FLAG_UF, FLAG_NX = 0x01, 0x02, 0x04, 0x08, 0x10
FLAG_ALL = 0x1F

MODE_NAMES = {0: "RNE", 1: "RTZ", 2: "RDN", 3: "RUP"}


# ── bit level helpers ─────────────────────────────────────────────────────
def _expall(fmt):
    return (1 << FMT[fmt]["eb"]) - 1


def _mask(fmt):
    return (1 << FMT[fmt]["w"]) - 1


def qnan_bits(fmt):
    f = FMT[fmt]
    return (_expall(fmt) << f["fracbits"]) | (1 << (f["fracbits"] - 1))


def inf_bits(fmt, sign=0):
    f = FMT[fmt]
    return (sign << f["signpos"]) | (_expall(fmt) << f["fracbits"])


def classify(bits, fmt):
    """Return {kind, sign, value (Fraction|None), quiet (bool|None)}."""
    f = FMT[fmt]
    bits &= _mask(fmt)
    sign = (bits >> f["signpos"]) & 1
    expf = (bits >> f["fracbits"]) & _expall(fmt)
    frac = bits & ((1 << f["fracbits"]) - 1)
    if expf == _expall(fmt):
        if frac == 0:
            return {"kind": "inf", "sign": sign, "value": None, "quiet": None}
        return {"kind": "nan", "sign": sign, "value": None,
                "quiet": bool(frac >> (f["fracbits"] - 1))}
    if expf == 0:
        if frac == 0:
            return {"kind": "zero", "sign": sign, "value": Fraction(0),
                    "quiet": None}
        m, e = frac, 1 - f["bias"] - f["fracbits"]
    else:
        m, e = frac | (1 << f["fracbits"]), expf - f["bias"] - f["fracbits"]
    val = Fraction(m) * (Fraction(2) ** e)
    return {"kind": "subnormal" if expf == 0 else "normal", "sign": sign,
            "value": -val if sign else val, "quiet": None}


def exact_value(bits, fmt):
    d = classify(bits, fmt)
    return d["value"]


def floor_log2(a):
    """floor(log2(a)) for a positive Fraction, exactly."""
    assert a > 0
    e = a.numerator.bit_length() - a.denominator.bit_length()
    two = Fraction(2)
    while two ** e > a:
        e -= 1
    while two ** (e + 1) <= a:
        e += 1
    return e


def _round_int_half_even(q):
    n, d = q.numerator, q.denominator
    k, r = divmod(n, d)
    twice = 2 * r
    if twice > d or (twice == d and (k % 2) == 1):
        return k + 1
    return k


def encode(value, fmt, mode=0):
    """Encode a Fraction into ``fmt`` with ONE rounding under ``mode``.

    ``mode`` is rf0[33:32]: 0 RNE, 1 RTZ, 2 RDN, 3 RUP.  Returns (bits, flags).
    """
    f = FMT[fmt]
    sign = 1 if value < 0 else 0
    a = -value if value < 0 else value
    if a == 0:
        return sign << f["signpos"], 0
    e = floor_log2(a)
    if e > f["emax"]:
        return _overflow_bits(fmt, sign, mode), FLAG_OF | FLAG_NX
    if e >= f["emin"]:
        q = a / (Fraction(2) ** (e - f["fracbits"]))
        n, inexact = _round_quantum(q, mode, sign)
        if n == (1 << f["p"]):
            n >>= 1
            e += 1
            if e > f["emax"]:
                return _overflow_bits(fmt, sign, mode), FLAG_OF | FLAG_NX
        bits = ((sign << f["signpos"]) | ((e + f["bias"]) << f["fracbits"]) |
                (n - (1 << f["fracbits"])))
        return bits, (FLAG_NX if inexact else 0)
    # subnormal range; tininess is detected AFTER rounding (spec §2.5)
    q = a / (Fraction(2) ** (f["emin"] - f["fracbits"]))
    n, inexact = _round_quantum(q, mode, sign)
    if n == 0:
        return sign << f["signpos"], FLAG_UF | FLAG_NX
    if n >= (1 << f["fracbits"]):        # rounded up to the minimum normal
        return (sign << f["signpos"]) | (1 << f["fracbits"]), \
            (FLAG_NX if inexact else 0)
    return ((sign << f["signpos"]) | n), \
        ((FLAG_UF | FLAG_NX) if inexact else 0)


def _round_quantum(a, mode, sign):
    """Round a >= 0 to an integer under ``mode``; directed modes use the sign.

    Returns (integer, inexact).
    """
    fl = a.numerator // a.denominator
    inexact = a.denominator != 1
    if mode == 0:                                    # RNE
        rem = a - fl
        if rem > Fraction(1, 2):
            n = fl + 1
        elif rem < Fraction(1, 2):
            n = fl
        else:
            n = fl if fl % 2 == 0 else fl + 1
    elif mode == 1:                                  # RTZ
        n = fl
    elif mode == 3:                                  # RUP (toward +inf)
        n = fl + 1 if (inexact and sign == 0) else fl
    elif mode == 2:                                  # RDN (toward -inf)
        n = fl + 1 if (inexact and sign == 1) else fl
    else:
        raise AssertionError("bad mode %r" % (mode,))
    return n, inexact


def _overflow_bits(fmt, sign, mode):
    f = FMT[fmt]
    inf = (sign << f["signpos"]) | (_expall(fmt) << f["fracbits"])
    maxfin = ((sign << f["signpos"]) |
              ((_expall(fmt) - 1) << f["fracbits"]) |
              ((1 << f["fracbits"]) - 1))
    if mode == 0:
        return inf
    if mode == 1:
        return maxfin
    if mode == 3:
        return inf if sign == 0 else maxfin
    return inf if sign == 1 else maxfin               # RDN


# ── expectations ──────────────────────────────────────────────────────────
def zero_bits(fmt, sign):
    return sign << FMT[fmt]["signpos"]


def fma_expect(a, b, c, fmt, rmode=0, want_step=False):
    """Exact IEEE-754 fusedMultiplyAdd with ONE rounding.

    Returns {"out": bits, "flags": int, "step": two-step bits | None}.
    """
    ka = classify(a, fmt)
    kb = classify(b, fmt)
    kc = classify(c, fmt)
    f = FMT[fmt]

    kinds = (ka["kind"], kb["kind"], kc["kind"])
    snan = any(k == "nan" and not v["quiet"]
               for k, v in zip(kinds, (ka, kb, kc)))
    qnan = any(k == "nan" for k in kinds)
    infzero = ((ka["kind"] == "zero" and kb["kind"] == "inf") or
               (ka["kind"] == "inf" and kb["kind"] == "zero"))

    # 0 x Inf outranks NaN propagation: NV even when c is a quiet NaN.
    if infzero:
        return {"out": qnan_bits(fmt), "flags": FLAG_NV, "step": None}
    if snan:
        return {"out": qnan_bits(fmt), "flags": FLAG_NV,
                "step": None}
    if qnan:
        return {"out": qnan_bits(fmt), "flags": 0, "step": None}

    prod_sign = ka["sign"] ^ kb["sign"]
    if ka["kind"] == "inf" or kb["kind"] == "inf":
        if kc["kind"] == "inf" and kc["sign"] != prod_sign:
            return {"out": qnan_bits(fmt), "flags": FLAG_NV, "step": None}
        return {"out": inf_bits(fmt, prod_sign), "flags": 0, "step": None}
    if kc["kind"] == "inf":
        return {"out": c & _mask(fmt), "flags": 0, "step": None}

    exact = ka["value"] * kb["value"] + kc["value"]
    step = two_step_expect(a, b, c, fmt, rmode) if want_step else None
    if exact == 0:
        prod_zero = ka["kind"] == "zero" or kb["kind"] == "zero"
        c_zero = kc["kind"] == "zero"
        if prod_zero and c_zero and prod_sign == kc["sign"]:
            return {"out": zero_bits(fmt, prod_sign), "flags": 0, "step": step}
        return {"out": zero_bits(fmt, 1 if rmode == 2 else 0), "flags": 0,
                "step": step}
    out, flags = encode(exact, fmt, rmode)
    return {"out": out, "flags": flags, "step": step}


def two_step_expect(a, b, c, fmt, rmode=0):
    """The WRONG sequence: round(a*b) then round(product + c).  Finite only."""
    ka, kb, kc = classify(a, fmt), classify(b, fmt), classify(c, fmt)
    for k in (ka, kb, kc):
        if k["value"] is None:
            raise ValueError("two_step expects finite operands")
    prod = ka["value"] * kb["value"]
    prod_sign = ka["sign"] ^ kb["sign"]
    if prod == 0:
        pbits = zero_bits(fmt, prod_sign)
    else:
        pbits, _ = encode(prod, fmt, rmode)
    x = exact_value(pbits, fmt)
    s = x + kc["value"]
    if s == 0:
        kx = classify(pbits, fmt)
        if kx["kind"] == "zero" and kc["kind"] == "zero" \
                and kx["sign"] == kc["sign"]:
            return zero_bits(fmt, kx["sign"])
        return zero_bits(fmt, 1 if rmode == 2 else 0)
    out, _ = encode(s, fmt, rmode)
    return out


# ── operand tables (the probes print these labels; a typo is a FAIL) ─────
def _both(label, ft, fo, rmode=0):
    return [(label, "ft", ft[0], ft[1], ft[2], rmode),
            (label, "fo", fo[0], fo[1], fo[2], rmode)]


# format constants
C = {
    "ft": {"zero": 0x00000000, "nzero": 0x80000000, "one": 0x3F800000,
           "mone": 0xBF800000, "two": 0x40000000, "inf": 0x7F800000,
           "ninf": 0xFF800000, "qnan": 0x7FC00000, "snan": 0x7F800001,
           "minsub": 0x00000001, "maxfin": 0x7F7FFFFF,
           "one_p": 0x3F800001, "one_m": 0x3F7FFFFE, "half": 0x33800000,
           "onehalf": 0x3FC00000},
    "fo": {"zero": 0x0000000000000000, "nzero": 0x8000000000000000,
           "one": 0x3FF0000000000000, "mone": 0xBFF0000000000000,
           "two": 0x4000000000000000, "inf": 0x7FF0000000000000,
           "ninf": 0xFFF0000000000000, "qnan": 0x7FF8000000000000,
           "snan": 0x7FF0000000000001, "minsub": 0x0000000000000001,
           "maxfin": 0x7FEFFFFFFFFFFFFF,
           "one_p": 0x3FF0000000000001, "one_m": 0x3FEFFFFFFFFFFFFF,
           "half": 0x3CA0000000000000, "onehalf": 0x3FF8000000000000},
}


def _const(fmt, name):
    return C[fmt][name]


def _tt(label, rmode=0, **kw):
    """Build a two-format case from named constants (ft/fo symmetric)."""
    return _both(label,
                 (_const("ft", kw["a"]), _const("ft", kw["b"]),
                  _const("ft", kw["c"])),
                 (_const("fo", kw["a"]), _const("fo", kw["b"]),
                  _const("fo", kw["c"])), rmode)


# Single-rounding discriminators: the fused result differs from fmul+foadd.
DISC_CASES = [
    # spec §2.5 counter-example: exact -2^-46 vs +0 (product rounds to 1).
    ("ft_spec", "ft", 0x3F800001, 0x3F7FFFFE, 0xBF800000, 0),
    # square with a cancelling addend: exact 2^-46 vs +0.
    ("ft_square", "ft", 0x3F800001, 0x3F800001, 0xBF800002, 0),
    # both candidates non-zero, one ulp apart (harder than the 0-vs-x pair).
    ("ft_both", "ft", 0x3F800001, 0x3F800001, 0xBF800001, 0),
    ("fo_spec", "fo", 0x3FF0000000000001, 0x3FEFFFFFFFFFFFFE,
     0xBFF0000000000000, 0),
    ("fo_square", "fo", 0x3FF0000000000001, 0x3FF0000000000001,
     0xBFF0000000000002, 0),
    ("fo_both", "fo", 0x3FEFFFFFFFFFFFF8, 0x3FEFFFFFFFFFFFF8,
     0xBFF0000000000000, 0),
]

# Boundary / flag matrix (value + rf0[4:0] on separate assertions).
SPECIAL_CASES = []
SPECIAL_CASES += _tt("qnan_a", a="qnan", b="one", c="one")
SPECIAL_CASES += _tt("qnan_c", a="one", b="one", c="qnan")
SPECIAL_CASES += _tt("snan_a", a="snan", b="one", c="one")
SPECIAL_CASES += _tt("snan_c", a="one", b="one", c="snan")
SPECIAL_CASES += _tt("zeroxinf_qnan", a="zero", b="inf", c="qnan")
SPECIAL_CASES += _tt("inf_minus_inf", a="inf", b="one", c="ninf")
SPECIAL_CASES += _tt("inf_same", a="inf", b="two", c="inf")
SPECIAL_CASES += _tt("inf_c", a="one", b="two", c="ninf")
SPECIAL_CASES += _tt("zero_rne", a="one", b="one", c="mone")
SPECIAL_CASES += _tt("zero_rdn", rmode=2, a="one", b="one", c="mone")
SPECIAL_CASES += _tt("zeroprod_negzero", rmode=2, a="zero", b="one",
                     c="nzero")
SPECIAL_CASES += _tt("ovf_rne", a="maxfin", b="two", c="zero")
SPECIAL_CASES += _tt("ovf_rtz", rmode=1, a="maxfin", b="two", c="zero")
SPECIAL_CASES += _tt("sub_exact", a="minsub", b="one", c="zero")
SPECIAL_CASES += _tt("sub_inexact", a="minsub", b="onehalf", c="zero")
SPECIAL_CASES += _tt("sub_to_zero", a="minsub", b="minsub", c="one")
SPECIAL_CASES += _tt("nx_normal", a="one_p", b="one_p", c="zero")
SPECIAL_CASES += _tt("tie_rne", a="one_p", b="one", c="half")
SPECIAL_CASES += _tt("tie_rtz", rmode=1, a="one_p", b="one", c="half")
SPECIAL_CASES += _tt("tie_rdn", rmode=2, a="one_p", b="one", c="half")
SPECIAL_CASES += _tt("tie_rup", rmode=3, a="one_p", b="one", c="half")
# negative tie: RDN rounds away from zero, RUP toward zero (asymmetry)
SPECIAL_CASES += [("negtie_rdn", "ft", 0xBF800001, 0x3F800000, 0xB3800000, 2),
                  ("negtie_rdn", "fo", 0xBFF0000000000001, 0x3FF0000000000000,
                   0xBCA0000000000000, 2),
                  ("negtie_rup", "ft", 0xBF800001, 0x3F800000, 0xB3800000, 3),
                  ("negtie_rup", "fo", 0xBFF0000000000001, 0x3FF0000000000000,
                   0xBCA0000000000000, 3)]

# The end-to-end C path (`fma`/`fmaf` from C) keeps a distinct group so the
# disassembly/libcall checks and the C-side injection are unambiguous.
CPATH_CASES = [
    ("c_disc_ft", "ft", 0x3F800001, 0x3F800001, 0xBF800000, 0),
    ("c_basic_ft", "ft", 0x3FC00000, 0x40000000, 0xBF800000, 0),
    ("c_disc_fo", "fo", 0x3FF0000000000001, 0x3FF0000000000001,
     0xBFF0000000000002, 0),
    ("c_basic_fo", "fo", 0x3FF8000000000000, 0x4000000000000000,
     0xBFF0000000000000, 0),
]

# `acc += a * b` (llvm.fmuladd contraction): the addend is the printed c.
CONTRACT_CASES = [
    ("contract_disc_ft", "ft", 0x3F800001, 0x3F800001, 0xBF800002, 0),
    ("contract_basic_ft", "ft", 0x40000000, 0x40400000, 0x41200000, 0),
    ("contract_disc_fo", "fo", 0x3FF0000000000001, 0x3FF0000000000001,
     0xBFF0000000000002, 0),
    ("contract_basic_fo", "fo", 0x4000000000000000, 0x4008000000000000,
     0x4024000000000000, 0),
]

GROUPS = {
    "disc": DISC_CASES,
    "discasm": DISC_CASES,
    "csel": DISC_CASES,
    "special": SPECIAL_CASES,
    "cpath": CPATH_CASES,
    "contract": CONTRACT_CASES,
}

# Labels that MUST have fused != two-step (valid discriminator cases).
MUST_DIFFER = {("disc", c[0]) for c in DISC_CASES} | \
              {("csel", c[0]) for c in DISC_CASES} | \
              {("contract", "contract_disc_ft"),
               ("contract", "contract_disc_fo")}

# Groups where the two-step value is printed and judged.
TWO_STEP_GROUPS = ("disc", "contract", "csel")


def case_of(group, label, fmt):
    for c in GROUPS[group]:
        if c[0] == label and c[1] == fmt:
            return c
    raise KeyError("%s/%s/%s" % (group, label, fmt))


# ── algorithm-level data (C probes re-generate it; hashes must match) ────
LCG_MUL, LCG_INC, MASK32 = 1664525, 1013904223, 0xFFFFFFFF
FNV_INIT = 14695981039346656037
FNV_PRIME = 1099511628211

DOT_LENGTHS = (16, 64, 256)
GEMM_N = 4
HORNER_DEGS_FO = (5, 9)
HORNER_DEGS_FT = (5,)


def lcg_stream(seed, n):
    u = seed & MASK32
    out = []
    for _ in range(n):
        u = (u * LCG_MUL + LCG_INC) & MASK32
        out.append(u)
    return out


def _ratio_bits(u, fmt):
    """value = (int32)u / 2^31, encoded exactly in ``fmt``."""
    s = u - (1 << 32) if u >= (1 << 31) else u
    if s == 0:
        return 0
    bits, _ = encode(Fraction(s, 1 << 31), fmt, 0)
    return bits


def gen_bits(seed, n, fmt="fo"):
    return [_ratio_bits(u, fmt) for u in lcg_stream(seed, n)]


def fnv_u64(h, v):
    for i in range(8):
        h ^= (v >> (8 * i)) & 0xFF
        h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def dot_seeds(n):
    return (0x12345678 + n) & MASK32, (0x0BADF00D + n) & MASK32


def horner_seeds(deg, fmt):
    return (0x33333333 + deg) & MASK32, (0x44444444 + deg) & MASK32


def dot_expect(n, form="fma"):
    sa, sb = dot_seeds(n)
    a, b = gen_bits(sa, n), gen_bits(sb, n)
    data = FNV_INIT
    for v in a + b:
        data = fnv_u64(data, v)
    acc, flags, h = 0, 0, FNV_INIT
    for i in range(n):
        r = fma_expect(a[i], b[i], acc, "fo", 0, want_step=True)
        acc = r["out"]
        flags |= r["flags"]
        h = fnv_u64(h, acc)
    step = 0
    for i in range(n):
        step = two_step_expect(a[i], b[i], step, "fo", 0)
    return {"group": "dot", "len": n, "form": form, "data": data, "out": acc,
            "hash": h, "flags": flags, "step": step}


def gemm_expect():
    a = gen_bits(0x11111111, GEMM_N * GEMM_N)
    b = gen_bits(0x22222222, GEMM_N * GEMM_N)
    data = FNV_INIT
    for v in a + b:
        data = fnv_u64(data, v)
    cells = []
    flags = 0
    for i in range(GEMM_N):
        for j in range(GEMM_N):
            acc = 0
            for k in range(GEMM_N):
                r = fma_expect(a[i * GEMM_N + k], b[k * GEMM_N + j], acc,
                               "fo", 0)
                acc = r["out"]
                flags |= r["flags"]
            cells.append(((i, j), acc))
    return {"group": "gemm", "data": data, "cells": cells, "flags": flags}


def horner_expect(deg, fmt="fo"):
    sc, sx = horner_seeds(deg, fmt)
    coef = gen_bits(sc, deg + 1, fmt)
    x = gen_bits(sx, 1, fmt)[0]
    data = FNV_INIT
    for v in coef + [x]:
        data = fnv_u64(data, v)
    p, h, flags = coef[deg], FNV_INIT, 0
    for i in range(deg - 1, -1, -1):
        r = fma_expect(p, x, coef[i], fmt, 0)
        p = r["out"]
        flags |= r["flags"]
        h = fnv_u64(h, p)
    step = coef[deg]
    for i in range(deg - 1, -1, -1):
        step = two_step_expect(step, x, coef[i], fmt, 0)
    return {"group": "horner", "deg": deg, "fmt": fmt, "data": data,
            "out": p, "hash": h, "flags": flags, "step": step}


# ── probe output parsing ─────────────────────────────────────────────────
def _kv(line):
    out = {}
    for tok in line.split()[1:]:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        out[k] = v
    return out


def parse(text):
    """Parse the probes' raw output into records; unknown lines are junk."""
    parsed = {"obs": [], "alg": [], "init": [], "restore": [], "junk": []}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("OBS "):
            rec = _kv(line)
            for k in ("a", "b", "c", "out", "pre", "post"):
                if k in rec:
                    rec[k] = int(rec[k], 16)
            for k in ("rm",):
                if k in rec:
                    rec[k] = int(rec[k], 0)
            if "step" in rec:
                rec["step"] = int(rec["step"], 16)
            parsed["obs"].append(rec)
        elif line.startswith("ALG "):
            rec = _kv(line)
            for k in ("data", "out", "hash", "pre", "post"):
                if k in rec:
                    rec[k] = int(rec[k], 16)
            for k in ("len", "row", "col", "deg"):
                if k in rec:
                    rec[k] = int(rec[k], 0)
            parsed["alg"].append(rec)
        elif line.startswith("INIT "):
            rec = _kv(line)
            rec["rf0"] = int(rec["rf0"], 16)
            parsed["init"].append(rec)
        elif line.startswith("RESTORE "):
            rec = _kv(line)
            rec["expect"] = int(rec["expect"], 16)
            rec["got"] = int(rec["got"], 16)
            parsed["restore"].append(rec)
        else:
            parsed["junk"].append(line)
    return parsed


def _check(name, expected, actual, ok, detail=""):
    return {"name": name, "expected": expected, "actual": actual,
            "ok": bool(ok), "detail": detail}


def judge_rf0(pre, post, flags, name, detail=""):
    """Flags / mode preservation / write mask on one observation."""
    w = RF0_WRITABLE
    ro = RF0_READONLY
    out = []
    out.append(_check("%s pre flags cleared" % name, "0x00",
                      "0x%02x" % (pre & FLAG_ALL),
                      (pre & FLAG_ALL) == 0,
                      "the probe clears rf0[4:0] before every observation"))
    out.append(_check("%s flags" % name, "0x%02x" % flags,
                      "0x%02x" % (post & FLAG_ALL), (post & FLAG_ALL) == flags,
                      detail))
    out.append(_check("%s mode preserved" % name, "0x%x" % ((pre >> 32) & 3),
                      "0x%x" % ((post >> 32) & 3),
                      ((pre >> 32) & 3) == ((post >> 32) & 3)))
    out.append(_check("%s rf0 write mask" % name, "read-only bits intact",
                      "(post^pre)&~W = 0x%x" % ((post ^ pre) & ~w),
                      ((post ^ pre) & ~w) == 0,
                      "read-only = 0x%x" % ro))
    return out


def judge_obs(rec, mutation=None):
    """Judge one OBS record against the spec-derived expectation.

    ``mutation`` (injection self-test only):
      * ``"two_step"``  -- use the two-step value as the expectation
        (models a wrong oracle / a fmul+fadd degradation baseline);
      * ``"flags_zero"`` -- expect NV = 0 on sNaN inputs.
    """
    group, fmt, label = rec["group"], rec["fmt"], rec["label"]
    case = case_of(group, label, fmt)
    _, _, a, b, c, rmode = case
    checks = []
    name = "%s/%s/%s" % (group, fmt, label)
    checks.append(_check(
        name + " operands", "a=%x b=%x c=%x rm=%d" % (a, b, c, rmode),
        "a=%x b=%x c=%x rm=%s" % (rec.get("a"), rec.get("b"), rec.get("c"),
                                  rec.get("rm")),
        (rec.get("a") == a and rec.get("b") == b and rec.get("c") == c
         and rec.get("rm") == rmode)))
    exp = fma_expect(a, b, c, fmt, rmode, want_step=group in TWO_STEP_GROUPS)
    want_out = exp["out"]
    want_flags = exp["flags"]
    if mutation == "two_step":
        if exp["step"] is None:
            want_out = exp["out"]
        else:
            want_out = exp["step"]
    if mutation == "flags_zero":
        want_flags = 0
    checks.append(_check(name + " value", "0x%x" % want_out,
                         "0x%x" % rec["out"], rec["out"] == want_out,
                         "fused=%s two_step=%s" % (
                             hex(exp["out"]),
                             "-" if exp["step"] is None else hex(exp["step"]))))
    checks.extend(judge_rf0(rec["pre"], rec["post"], want_flags, name))
    if group in TWO_STEP_GROUPS and exp["step"] is not None:
        checks.append(_check(name + " two-step value", "0x%x" % exp["step"],
                             "0x%x" % rec["step"], rec["step"] == exp["step"],
                             "the non-fused sequence"))
        if (group, label) in MUST_DIFFER:
            checks.append(_check(
                name + " fused != two-step", "different",
                "fused=0x%x two-step=0x%x" % (rec["out"], rec["step"]),
                rec["out"] != rec["step"],
                "valid discriminator (fused=%s two-step=%s)"
                % (hex(exp["out"]), hex(exp["step"]))))
    return checks


def judge_init(rec):
    return [_check("rf0 reset value (ADR-0004 D2)", "0x%016x" % RF0_RESET,
                   "0x%016x" % rec["rf0"], rec["rf0"] == RF0_RESET,
                   "the guest must enter main with the architectural reset")]


def judge_restore(rec):
    return [_check("restore/%s" % rec.get("group"), "0x%016x" % rec["expect"],
                   "0x%016x" % rec["got"], rec["got"] == rec["expect"],
                   "rf0 restored (mode kept, flags cleared)")]


def judge_alg(rec):
    """Judge one ALG record (dot / gemm / horner)."""
    group = rec["group"]
    checks = []
    if group == "dot":
        form = rec.get("form", "fma")
        exp = dot_expect(rec["len"], form)
        name = "dot/%s/%d/%s" % (rec["fmt"], rec["len"], form) \
            if "fmt" in rec else "dot/%d/%s" % (rec["len"], form)
    elif group == "gemm":
        exp = gemm_expect()
        i, j = rec["row"], rec["col"]
        exp = {"data": exp["data"], "out": dict(exp["cells"])[(i, j)],
               "flags": exp["flags"]}
        name = "gemm/%d/%d" % (i, j)
    elif group == "horner":
        exp = horner_expect(rec["deg"], rec.get("fmt", "fo"))
        name = "horner/%s/%d" % (exp["fmt"], rec["deg"])
    else:
        return [_check("unknown ALG group %r" % group, "known", group, False)]
    checks.append(_check(name + " data stream", "0x%016x" % exp["data"],
                         "0x%016x" % rec["data"], rec["data"] == exp["data"],
                         "C and oracle must generate the same inputs"))
    checks.append(_check(name + " value", "0x%016x" % exp["out"],
                         "0x%016x" % rec["out"], rec["out"] == exp["out"]))
    if "hash" in exp and "hash" in rec:
        checks.append(_check(name + " per-step hash", "0x%016x" % exp["hash"],
                             "0x%016x" % rec["hash"],
                             rec["hash"] == exp["hash"],
                             "FNV-1a over every intermediate accumulator"))
    if "pre" in rec and "post" in rec:
        checks.extend(judge_rf0(rec["pre"], rec["post"], exp["flags"], name,
                                "accumulated flags of the whole sequence"))
    return checks


# ── self test ─────────────────────────────────────────────────────────────
def selftest():
    checks = []

    def add(name, expected, actual, ok, detail=""):
        checks.append(_check(name, expected, actual, ok, detail))

    # 1. spec counter-example, stated directly (spec §2.5)
    r = fma_expect(0x3F800001, 0x3F7FFFFE, 0xBF800000, "ft", 0,
                   want_step=True)
    add("selftest spec ft fused = -2^-46 (0xA8800000)", "0xA8800000",
        "0x%08X" % r["out"], r["out"] == 0xA8800000)
    add("selftest spec ft two-step = +0", "0x00000000",
        "0x%08X" % r["step"], r["step"] == 0x00000000)
    add("selftest spec ft fused != two-step", "different", "same",
        r["out"] != r["step"])

    # 2. hand-written boundary table (flags/values stated directly)
    hand = [
        ("qnan_a ft", 0x00, 0x7FC00000, (0x7FC00000, 0x3F800000, 0x3F800000)),
        ("snan_a ft", 0x01, 0x7FC00000, (0x7F800001, 0x3F800000, 0x3F800000)),
        ("snan_c fo", 0x01, 0x7FF8000000000000,
         (0x3FF0000000000000, 0x3FF0000000000000, 0x7FF0000000000001)),
        ("0xinf qnan c ft", 0x01, 0x7FC00000,
         (0x00000000, 0x7F800000, 0x7FC00000)),
        ("inf-inf ft", 0x01, 0x7FC00000, (0x7F800000, 0x3F800000, 0xFF800000)),
        ("overflow ft", 0x14, 0x7F800000, (0x7F7FFFFF, 0x40000000, 0x00000000)),
        ("underflow ft", 0x18, 0x00000002, (0x00000001, 0x3FC00000, 0x00000000)),
        ("zero RDN ft", 0x00, 0x80000000, (0x3F800000, 0x3F800000, 0xBF800000),
         2),
    ]
    for row in hand:
        label, want_flags, want_bits, ops = row[:4]
        rmode = row[4] if len(row) > 4 else 0
        fmt = "fo" if label.endswith("fo") else "ft"
        r = fma_expect(ops[0], ops[1], ops[2], fmt, rmode)
        add("selftest %s value" % label, "0x%x" % want_bits,
            "0x%x" % r["out"], r["out"] == want_bits)
        add("selftest %s flags" % label, "0x%02x" % want_flags,
            "0x%02x" % r["flags"], r["flags"] == want_flags)

    # 3. every declared discriminator really differs
    for label, fmt, a, b, c, rmode in DISC_CASES:
        r = fma_expect(a, b, c, fmt, rmode, want_step=True)
        add("selftest discriminator %s differs" % label, "different",
            "fused=0x%x step=0x%x" % (r["out"], r["step"]),
            r["out"] != r["step"])

    # 4. encode/decode round-trip on every table operand
    bad = []
    for group, cases in GROUPS.items():
        for label, fmt, a, b, c, rmode in cases:
            for bits in (a, b, c):
                d = classify(bits, fmt)
                if d["value"] is None:
                    continue
                enc, _ = encode(d["value"], fmt, 0)
                if d["kind"] == "zero":
                    enc = zero_bits(fmt, d["sign"])
                if enc != (bits & _mask(fmt)):
                    bad.append((label, fmt, hex(bits), hex(enc)))
    add("selftest encode/decode round-trip", [], bad, not bad)

    # 5. second implementation: CPython's correctly-rounded conversions (RNE)
    diffs = []
    for label, fmt, a, b, c, rmode in DISC_CASES:
        r = fma_expect(a, b, c, fmt, rmode)
        exact = exact_value(a, fmt) * exact_value(b, fmt) + exact_value(c, fmt)
        if fmt == "fo":
            host = struct.unpack(">Q", struct.pack(">d", float(exact)))[0]
            want = "0x%016x" % r["out"]
            got = "0x%016x" % host
        else:
            # 53 >= 2*24+2 => binary64 -> binary32 double rounding is innocuous
            host = struct.unpack(">I", struct.pack(">f", float(exact)))[0]
            want = "0x%08x" % r["out"]
            got = "0x%08x" % host
        if got != want:
            diffs.append((label, want, got))
    add("selftest host cross-check (RNE, discriminators)", [], diffs,
        not diffs)

    # 6. reachable FAIL: the judge must go red on injected wrong expectations
    sample = next(r for r in SPECIAL_CASES if r[0] == "snan_a" and r[1] == "ft")
    rec = {"group": "special", "fmt": sample[1], "label": sample[0],
           "a": sample[2], "b": sample[3], "c": sample[4], "rm": sample[5],
           "out": fma_expect(sample[2], sample[3], sample[4], sample[1])["out"],
           "pre": 0x7FF800007FC00000, "post": 0x7FF800007FC00001}
    add("selftest judge snan_a green", "all ok", "see below",
        all(c["ok"] for c in judge_obs(rec)))
    add("selftest judge flags_zero injection is red", "red", "green",
        not all(c["ok"] for c in judge_obs(rec, "flags_zero")))
    disc = next(r for r in DISC_CASES if r[0] == "ft_spec")
    rec2 = {"group": "disc", "fmt": "ft", "label": "ft_spec",
            "a": disc[2], "b": disc[3], "c": disc[4], "rm": 0,
            "out": fma_expect(disc[2], disc[3], disc[4], "ft")["out"],
            "step": 0, "pre": 0x7FF800007FC00000, "post": 0x7FF800007FC00000}
    add("selftest judge ft_spec green", "all ok", "see below",
        all(c["ok"] for c in judge_obs(rec2)))
    add("selftest judge two_step injection is red", "red", "green",
        not all(c["ok"] for c in judge_obs(rec2, "two_step")))

    # 7. the algorithm model is self-consistent: on a short dot the fused and
    #    two-step sequences end in different values (on longer sums the final
    #    rounding absorbs the difference, which is why the probe also hashes
    #    every intermediate accumulator).
    d = dot_expect(16)
    add("selftest dot16 fused != two-step", "different",
        "fused=0x%x two-step=0x%x" % (d["out"], d["step"]),
        d["out"] != d["step"])
    return checks


def dump():
    for group, cases in GROUPS.items():
        print("== %s" % group)
        for label, fmt, a, b, c, rmode in cases:
            r = fma_expect(a, b, c, fmt, rmode,
                           want_step=group in TWO_STEP_GROUPS)
            print("%-20s %s a=%016x b=%016x c=%016x rm=%d -> out=%016x "
                  "flags=0x%02x step=%s" % (
                      label, fmt, a, b, c, rmode, r["out"], r["flags"],
                      "-" if r["step"] is None else "0x%016x" % r["step"]))
    print("== algorithm")
    for n in DOT_LENGTHS:
        d = dot_expect(n)
        print("dot len=%d out=%016x hash=%016x flags=0x%02x step=%016x"
              % (n, d["out"], d["hash"], d["flags"], d["step"]))
    g = gemm_expect()
    print("gemm data=%016x %s" % (g["data"], " ".join(
        "(%d,%d)=%016x" % (i, j, v) for (i, j), v in g["cells"])))
    for deg in HORNER_DEGS_FO + HORNER_DEGS_FT:
        h = horner_expect(deg, "fo" if deg in HORNER_DEGS_FO else "ft")
        print("horner %s deg=%d out=%016x hash=%016x flags=0x%02x step=%016x"
              % (h["fmt"], deg, h["out"], h["hash"], h["flags"], h["step"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dump", action="store_true")
    args = ap.parse_args(argv)
    if args.dump:
        dump()
        return 0
    checks = selftest()
    fails = [c for c in checks if not c["ok"]]
    for c in checks:
        print("%s %s | expected=%s | actual=%s%s" % (
            "PASS" if c["ok"] else "FAIL", c["name"], c["expected"],
            c["actual"], (" | " + c["detail"]) if c["detail"] else ""))
    print("selftest: total=%d pass=%d fail=%d"
          % (len(checks), len(checks) - len(fails), len(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
