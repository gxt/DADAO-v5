#!/usr/bin/env python3
"""Independent, spec-derived reference model for the 55 B7 floating-point ids.

This module is the differential oracle for `exec/b7.cc` (GEM5-012t).  It is
independent of the gem5 C++ implementation: values are exact `Fraction`s and
every rounding is an explicit integer decision derived from

  * spec/SimRISC-07 (all FP sections + appendices A/B),
  * spec/SimRISC-00 §2.3/§2.3.1 (rf / FCSR),
  * spec/SimRISC-02 §3 (cs.*-rf),
  * contract-fp §1-§10/§15/§16/§18-§20,
  * IEEE 754-2019 (user ruling 2026-11-02),

and never from LLVM, QEMU, the gem5 core or a host `float`/`double` operation.

Reuse policy (task "6) 断言 harness"): the bit-level primitives of
`tools/testcases/oracle_fma.py` (`classify` / `encode` / `exact_value`) are
imported read-only to avoid a third encoder.  The fma / minmax / roundint
families are nevertheless implemented here from scratch and cross-checked
against `oracle_fma.py` / `oracle_minmax.py` / `oracle_rnd.py` (a third
implementation): any disagreement is a hard failure.

CLI:
  --emit <vectors.txt>    write the differential vector set
  --expect <json>         write the expected results for the same vectors
  --verify <probe.txt> --expect <json>
                          compare the C++ probe output with the model
  --selftest              oracle-vs-oracle cross checks only
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from fractions import Fraction
from math import isqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASK64 = (1 << 64) - 1

RF0_RESET = 0x7FF800007FC00000
RF0_WRITABLE = (0x3 << 32) | 0x1F

FMT = {
    "ft": {"w": 32, "fracbits": 23, "eb": 8, "p": 24, "bias": 127,
           "emax": 127, "emin": -126, "signpos": 31},
    "fo": {"w": 64, "fracbits": 52, "eb": 11, "p": 53, "bias": 1023,
           "emax": 1023, "emin": -1022, "signpos": 63},
}

F_NV, F_DZ, F_OF, F_UF, F_NX = 0x01, 0x02, 0x04, 0x08, 0x10

MODES = {0: "RNE", 1: "RTZ", 2: "RDN", 3: "RUP"}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ofma = _load("oracle_fma", ROOT / "tools/testcases/oracle_fma.py")
ommx = _load("oracle_minmax", ROOT / "tools/testcases/oracle_minmax.py")
ornd = _load("oracle_rnd", ROOT / "tools/testcases/oracle_rnd.py")
gdt = _load("gen_decode_table", ROOT / "tools/gem5/gen_decode_table.py")

ENTRIES = {e.id: e for e in gdt.load_entries() if e.batch == "B7"}


# ── bit helpers ───────────────────────────────────────────────────────────
def _mask(fmt):
    return (1 << FMT[fmt]["w"]) - 1


def mask_bits(fmt, bits):
    return bits & _mask(fmt)


def sign_bit(fmt):
    return 1 << FMT[fmt]["signpos"]


def zero_bits(fmt, sign=0):
    return sign_bit(fmt) if sign else 0


def inf_bits(fmt, sign=0):
    f = FMT[fmt]
    return (sign_bit(fmt) if sign else 0) | (((1 << f["eb"]) - 1)
                                             << f["fracbits"])


def qnan_bits(fmt):
    f = FMT[fmt]
    return (((1 << f["eb"]) - 1) << f["fracbits"]) | (1 << (f["fracbits"] - 1))


def snan_bits(fmt):
    f = FMT[fmt]
    return (((1 << f["eb"]) - 1) << f["fracbits"]) | 1


def classify(fmt, bits):
    """{kind, sign, value, quiet} -- read-only oracle primitive."""
    return ofma.classify(mask_bits(fmt, bits), fmt)


def _round_quantum_rna(a, sign):
    """Round a >= 0 to an integer with RNA (nearest, ties away from zero)."""
    fl = a.numerator // a.denominator
    inexact = a.denominator != 1
    rem = a - Fraction(1, 2)
    fl_half = fl + rem  # floor + 1/2
    if a > fl_half:
        n = fl + 1
    elif a < fl_half:
        n = fl
    else:
        n = fl + 1 if sign == 0 else fl
    return n, inexact


def _encode_rna(value, fmt):
    """Encode a Fraction with ties-away rounding (ADR-0050 D2, code 0x02)."""
    f = FMT[fmt]
    sign = 1 if value < 0 else 0
    a = -value if value < 0 else value
    if a == 0:
        return sign << f["signpos"], 0
    e = ofma.floor_log2(a)
    if e > f["emax"]:
        return _overflow_bits(fmt, sign, 0), F_OF | F_NX
    if e >= f["emin"]:
        q = a / (Fraction(2) ** (e - f["fracbits"]))
        n, inexact = _round_quantum_rna(q, sign)
        if n == (1 << f["p"]):
            n >>= 1
            e += 1
            if e > f["emax"]:
                return _overflow_bits(fmt, sign, 0), F_OF | F_NX
        bits = ((sign << f["signpos"]) | ((e + f["bias"]) << f["fracbits"]) |
                (n - (1 << f["fracbits"])))
        return bits, (F_NX if inexact else 0)
    q = a / (Fraction(2) ** (f["emin"] - f["fracbits"]))
    n, inexact = _round_quantum_rna(q, sign)
    if n == 0:
        return sign << f["signpos"], F_UF | F_NX
    if n >= (1 << f["fracbits"]):
        return ((sign << f["signpos"]) | (1 << f["fracbits"])), \
            (F_NX if inexact else 0)
    return ((sign << f["signpos"]) | n), \
        ((F_UF | F_NX) if inexact else 0)


def encode(value, fmt, mode, zero_sign=0):
    """Round an exact Fraction with ONE rounding; returns (bits, flags).

    ``mode`` is 0 RNE / 1 RTZ / 2 RDN / 3 RUP (rf0), plus the conversion-only
    4 RNA (ADR-0050 D2, one-hot code 0x02).
    """
    if value == 0:
        return zero_bits(fmt, zero_sign), 0
    if mode == 4:
        return _encode_rna(value, fmt)
    return ofma.encode(value, fmt, mode)


def value_of(fmt, bits):
    return classify(fmt, bits)["value"]


def _overflow_bits(fmt, sign, mode):
    """Shape of an overflow result by direction (spec/SimRISC-07 §1.4).

    Built here instead of going through ``encode`` (which would recurse).
    ``mode`` is 0 RNE / 1 RTZ / 2 RDN / 3 RUP, plus the conversion-only
    4 RNA (ties away from zero, which overflows to infinity like RNE).
    """
    f = FMT[fmt]
    inf = inf_bits(fmt, sign)
    maxfin = ((sign_bit(fmt) if sign else 0) |
              (((1 << f["eb"]) - 2) << f["fracbits"]) |
              ((1 << f["fracbits"]) - 1))
    if mode in (0, 4):                    # RNE / RNA: ±Inf
        return inf
    if mode == 1:                         # RTZ: ±largest finite
        return maxfin
    if mode == 3:                         # RUP: +Inf / −max
        return inf if sign == 0 else maxfin
    return inf if sign == 1 else maxfin   # RDN: +max / −Inf


def _tiny_bits(fmt, sign, mode):
    value = Fraction(-1, 10 ** 400) if sign else Fraction(1, 10 ** 400)
    return encode(value, fmt, mode)


# ── per-op model ──────────────────────────────────────────────────────────
def _nan_result(fmt, flags_inputs):
    nv = any(not k["quiet"] for k in flags_inputs if k["kind"] == "nan")
    return qnan_bits(fmt), (F_NV if nv else 0)


def op_add(fmt, mode, a, b, negate_b=False):
    ka, kb = classify(fmt, a), classify(fmt, b)
    bsign = kb["sign"] ^ (1 if negate_b else 0)
    if ka["kind"] == "nan" or kb["kind"] == "nan":
        return _nan_result(fmt, [ka, kb])
    if ka["kind"] == "inf" and kb["kind"] == "inf":
        if ka["sign"] != bsign:
            return qnan_bits(fmt), F_NV
        return inf_bits(fmt, ka["sign"]), 0
    if ka["kind"] == "inf":
        return inf_bits(fmt, ka["sign"]), 0
    if kb["kind"] == "inf":
        return inf_bits(fmt, bsign), 0
    if ka["kind"] == "zero" and kb["kind"] == "zero":
        if ka["sign"] == bsign:
            return zero_bits(fmt, ka["sign"]), 0
        return zero_bits(fmt, 1 if mode == 2 else 0), 0
    if ka["kind"] == "zero":
        return mask_bits(fmt, b) ^ (sign_bit(fmt) if negate_b else 0), 0
    if kb["kind"] == "zero":
        return mask_bits(fmt, a), 0
    bvalue = -kb["value"] if negate_b else kb["value"]
    exact = ka["value"] + bvalue
    if exact == 0:
        return zero_bits(fmt, 1 if mode == 2 else 0), 0
    return encode(exact, fmt, mode)


def op_mul(fmt, mode, a, b):
    ka, kb = classify(fmt, a), classify(fmt, b)
    sign = ka["sign"] ^ kb["sign"]
    if ka["kind"] == "nan" or kb["kind"] == "nan":
        return _nan_result(fmt, [ka, kb])
    if ka["kind"] == "inf" or kb["kind"] == "inf":
        if ka["kind"] == "zero" or kb["kind"] == "zero":
            return qnan_bits(fmt), F_NV
        return inf_bits(fmt, sign), 0
    if ka["kind"] == "zero" or kb["kind"] == "zero":
        return zero_bits(fmt, sign), 0
    return encode(ka["value"] * kb["value"], fmt, mode)


def op_div(fmt, mode, a, b):
    ka, kb = classify(fmt, a), classify(fmt, b)
    sign = ka["sign"] ^ kb["sign"]
    if ka["kind"] == "nan" or kb["kind"] == "nan":
        return _nan_result(fmt, [ka, kb])
    if ka["kind"] == "inf":
        if kb["kind"] == "inf":
            return qnan_bits(fmt), F_NV
        return inf_bits(fmt, sign), 0
    if kb["kind"] == "inf":
        return zero_bits(fmt, sign), 0
    if kb["kind"] == "zero":
        if ka["kind"] == "zero":
            return qnan_bits(fmt), F_NV
        return inf_bits(fmt, sign), F_DZ
    if ka["kind"] == "zero":
        return zero_bits(fmt, sign), 0
    return encode(ka["value"] / kb["value"], fmt, mode)


def _round_half_even(q: Fraction) -> int:
    n, d = q.numerator, q.denominator
    k, r = divmod(n, d)
    twice = 2 * r
    if twice > d or (twice == d and (k % 2) == 1):
        return k + 1
    return k


def op_rem(fmt, a, b):
    ka, kb = classify(fmt, a), classify(fmt, b)
    if ka["kind"] == "nan" or kb["kind"] == "nan":
        return _nan_result(fmt, [ka, kb])
    if ka["kind"] == "inf" or kb["kind"] == "zero":
        return qnan_bits(fmt), F_NV
    if kb["kind"] == "inf" or ka["kind"] == "zero":
        return mask_bits(fmt, a), 0
    n = _round_half_even(ka["value"] / kb["value"])
    r = ka["value"] - n * kb["value"]
    if r == 0:
        return zero_bits(fmt, ka["sign"]), 0
    # exact by construction: no rounding, no flags (spec §2.1 + F5.1)
    return encode(r, fmt, 0, zero_sign=ka["sign"])


def op_sclb(fmt, mode, x, n):
    k = classify(fmt, x)
    if k["kind"] == "nan":
        return qnan_bits(fmt), (0 if k["quiet"] else F_NV)
    if k["kind"] == "inf":
        return inf_bits(fmt, k["sign"]), 0
    if k["kind"] == "zero":
        return zero_bits(fmt, k["sign"]), 0
    if n > 6000:  # far outside the format range: overflow, no iteration
        return _overflow_bits(fmt, k["sign"], mode), F_OF | F_NX
    if n < -6000:
        return _tiny_bits(fmt, k["sign"], mode)
    return encode(k["value"] * Fraction(2) ** n, fmt, mode)


def _pack_significand(fmt, sign, n, qexp, inexact, half_cmp, mode):
    """Pack an integer significand `n` at quantum 2^qexp (sqrt's rounding)."""
    f = FMT[fmt]
    increment = False
    if inexact:
        if mode == 0:
            increment = half_cmp > 0 or (half_cmp == 0 and (n & 1) != 0)
        elif mode == 1:
            increment = False
        elif mode == 2:
            increment = bool(sign)
        else:
            increment = not sign
    if increment:
        n += 1
    if n >> f["p"]:
        n >>= 1
        qexp += 1
    if n == 0:
        return zero_bits(fmt, sign), (F_UF | F_NX if inexact else 0)
    e = qexp + n.bit_length() - 1
    if e > f["emax"]:
        return _overflow_bits(fmt, sign, mode), F_OF | F_NX
    if e < f["emin"]:
        return (sign_bit(fmt) if sign else 0) | n, (F_UF | F_NX if inexact
                                                    else 0)
    expfield = e + f["bias"]
    frac = n - (1 << f["fracbits"])
    bits = (sign_bit(fmt) if sign else 0) | (expfield << f["fracbits"]) | frac
    return bits, (F_NX if inexact else 0)


def op_sqrt(fmt, mode, x):
    """IEEE square root via exact integer comparisons (no host float)."""
    f = FMT[fmt]
    k = classify(fmt, x)
    if k["kind"] == "nan":
        return qnan_bits(fmt), (0 if k["quiet"] else F_NV)
    if k["kind"] == "zero":
        return zero_bits(fmt, k["sign"]), 0  # rootn(-0, 2) model choice: -0
    if k["sign"]:
        return qnan_bits(fmt), F_NV
    if k["kind"] == "inf":
        return inf_bits(fmt), 0
    value = k["value"]
    ex = ofma.floor_log2(value)
    e = ex // 2
    qexp = max(e - (f["p"] - 1), f["emin"] - f["fracbits"])
    scaled = value / Fraction(2) ** (2 * qexp)
    n = isqrt(scaled.numerator // scaled.denominator)
    represented = Fraction(n) * Fraction(2) ** qexp
    exact = value == represented * represented
    half = Fraction((2 * n + 1) ** 2, 4) * Fraction(2) ** (2 * qexp)
    half_cmp = 0 if value == half else (1 if value > half else -1)
    return _pack_significand(fmt, 0, n, qexp, not exact, half_cmp, mode)


def op_fma(fmt, mode, a, b, c):
    ka, kb, kc = classify(fmt, a), classify(fmt, b), classify(fmt, c)
    psign = ka["sign"] ^ kb["sign"]
    zero_inf = ((ka["kind"] == "zero" and kb["kind"] == "inf") or
                (ka["kind"] == "inf" and kb["kind"] == "zero"))
    if zero_inf:
        # 0 x Inf outranks a qNaN addend (spec §2.5).
        return qnan_bits(fmt), F_NV
    if "nan" in (ka["kind"], kb["kind"], kc["kind"]):
        return _nan_result(fmt, [ka, kb, kc])
    if ka["kind"] == "inf" or kb["kind"] == "inf":
        if kc["kind"] == "inf":
            if psign != kc["sign"]:
                return qnan_bits(fmt), F_NV
            return inf_bits(fmt, psign), 0
        return inf_bits(fmt, psign), 0
    if ka["kind"] == "zero" or kb["kind"] == "zero":
        if kc["kind"] == "inf":
            return inf_bits(fmt, kc["sign"]), 0
        if kc["kind"] == "zero":
            if psign == kc["sign"]:
                return zero_bits(fmt, psign), 0
            return zero_bits(fmt, 1 if mode == 2 else 0), 0
        return mask_bits(fmt, c), 0
    if kc["kind"] == "inf":
        return inf_bits(fmt, kc["sign"]), 0
    product = ka["value"] * kb["value"]
    addend = kc["value"]
    exact = product + addend
    if exact == 0:
        return zero_bits(fmt, 1 if mode == 2 else 0), 0
    return encode(exact, fmt, mode)


def op_from_int(fmt, mode, value, width, signed):
    raw = value & ((1 << width) - 1)
    sign = bool(signed and (raw >> (width - 1)) & 1)
    mag = ((-raw) & ((1 << width) - 1)) if sign else raw
    if mag == 0:
        return zero_bits(fmt), 0
    return encode(Fraction(-mag if sign else mag), fmt, mode)


def _round_to_integer(value: Fraction, mode):
    """Round a signed Fraction (0 RNE / 1 RTZ / 2 RDN / 3 RUP / 4 RNA)."""
    n, d = value.numerator, value.denominator
    k, r = divmod(n, d)  # floor semantics, r >= 0
    if r == 0:
        return k, False
    if mode == 0:
        half = 2 * r
        if half > d or (half == d and (k % 2) == 1):
            return k + 1, True
        return k, True
    if mode == 1:  # toward zero
        return (k + 1 if value < 0 else k), True
    if mode == 2:  # toward -Inf
        return k, True
    if mode == 4:  # RNA: nearest, ties away from zero
        half = 2 * r
        if half > d:
            return k + 1, True
        if half < d:
            return k, True
        return (k + 1 if value > 0 else k), True
    return k + 1, True  # toward +Inf


def _widen(value, width, signed):
    pattern = value & ((1 << width) - 1)
    if signed and width < 64:
        return (pattern ^ (1 << (width - 1))) - (1 << (width - 1))
    return pattern


def op_to_int(fmt, mode, bits, width, signed):
    k = classify(fmt, bits)
    umax = (1 << width) - 1
    smax = (1 << (width - 1)) - 1
    smin_mag = 1 << (width - 1)
    pos_max = smax if signed else umax
    if k["kind"] == "nan":
        return _widen(pos_max, width, signed) & MASK64, F_NV
    if k["kind"] == "inf":
        if k["sign"]:
            return _widen(((-smin_mag) & umax) if signed else 0, width,
                          signed) & MASK64, F_NV
        return _widen(pos_max, width, signed) & MASK64, F_NV
    if k["kind"] == "zero":
        return 0, 0
    value = k["value"]
    n, inexact = _round_to_integer(value, mode)
    if n == 0:
        # The rounded integer is zero: representable in every target.
        return 0, (F_NX if inexact else 0)
    if n < 0:
        if not signed or -n > smin_mag:
            return _widen(((-smin_mag) & umax) if signed else 0, width,
                          signed) & MASK64, F_NV
        return _widen(n, width, signed) & MASK64, (F_NX if inexact else 0)
    if n > pos_max:
        return _widen(pos_max, width, signed) & MASK64, F_NV
    return _widen(n, width, signed) & MASK64, (F_NX if inexact else 0)


def op_convert_ff(dst_fmt, mode, src_fmt, bits):
    k = classify(src_fmt, bits)
    if k["kind"] == "nan":
        sf, df = FMT[src_fmt], FMT[dst_fmt]
        src_frac = mask_bits(src_fmt, bits) & ((1 << sf["fracbits"]) - 1)
        if df["fracbits"] >= sf["fracbits"]:
            dst_frac = src_frac << (df["fracbits"] - sf["fracbits"])
        else:
            dst_frac = src_frac >> (sf["fracbits"] - df["fracbits"])
        if dst_frac == 0:
            dst_frac = 1
        if not k["quiet"]:
            dst_frac |= 1 << (df["fracbits"] - 1)
        out = ((sign_bit(dst_fmt) if k["sign"] else 0) |
               (((1 << df["eb"]) - 1) << df["fracbits"]) | dst_frac)
        return out, (0 if k["quiet"] else F_NV)
    if k["kind"] == "inf":
        return inf_bits(dst_fmt, k["sign"]), 0
    if k["kind"] == "zero":
        return zero_bits(dst_fmt, k["sign"]), 0
    out, flags = encode(k["value"], dst_fmt, mode)
    # Overflow rides on the single rounding step: ``encode`` already returns
    # ±Inf or the largest finite value of ``dst_fmt`` as the direction
    # dictates (spec/SimRISC-07 §1.4, IEEE 754-2019 §7.4) and sets OF|NX.
    return out, flags


def op_round_int(fmt, bits, onehot, rf_mode):
    """roundToIntegral: implemented here, cross-checked against oracle_rnd."""
    f = FMT[fmt]
    k = classify(fmt, bits)
    if k["kind"] == "nan":
        return qnan_bits(fmt), (0 if k["quiet"] else F_NV)
    if k["kind"] in ("inf", "zero"):
        return mask_bits(fmt, bits), 0
    value = k["value"]
    if value.denominator == 1:
        return mask_bits(fmt, bits), 0
    if abs(value) >= Fraction(2) ** f["p"]:
        return mask_bits(fmt, bits), 0
    rules = {0x01: "even", 0x02: "away", 0x04: "zero", 0x08: "up",
             0x10: "down"}
    if onehot == 0x20:
        rule = {0: "even", 1: "zero", 2: "down", 3: "up"}[rf_mode & 3]
    else:
        rule = rules[onehot]
    if rule == "away":
        n = _round_away(value)
    else:
        n, _ = _round_to_integer(value, {"even": 0, "zero": 1, "down": 2,
                                         "up": 3}[rule])
    bits_out = zero_bits(fmt, k["sign"]) if n == 0 else encode(
        Fraction(n), fmt, 0)[0]
    flags = F_NX if (onehot == 0x20 and value.denominator != 1) else 0
    return bits_out, flags


def _round_away(value: Fraction) -> int:
    n, d = value.numerator, value.denominator
    k, r = divmod(n, d)
    if r == 0:
        return k
    if 2 * r < d:
        return k
    if 2 * r > d:
        return k + 1
    return k if value < 0 else k + 1


def op_classify(fmt, bits):
    k = classify(fmt, bits)
    bit = {
        ("nan", False): 1, ("nan", True): 0,
        ("inf", False): 9, ("inf", True): 2,
        ("normal", False): 8, ("normal", True): 3,
        ("subnormal", False): 7, ("subnormal", True): 4,
        ("zero", False): 6, ("zero", True): 5,
    }[(k["kind"], bool(k["sign"]))]
    if k["kind"] == "nan":
        bit = 1 if k["quiet"] else 0
    return 1 << bit


def op_compare(fmt, a, b):
    ka, kb = classify(fmt, a), classify(fmt, b)
    if ka["kind"] == "nan" or kb["kind"] == "nan":
        return "unordered"
    if ka["kind"] == "zero" and kb["kind"] == "zero":
        return "eq"
    if ka["kind"] == "zero":
        return "gt" if kb["sign"] else "lt"
    if kb["kind"] == "zero":
        return "lt" if ka["sign"] else "gt"
    if ka["sign"] != kb["sign"]:
        return "lt" if ka["sign"] else "gt"
    if ka["kind"] == "inf" and kb["kind"] == "inf":
        return "eq"
    if ka["kind"] == "inf":
        return "gt" if not ka["sign"] else "lt"
    if kb["kind"] == "inf":
        return "lt" if not kb["sign"] else "gt"
    if ka["value"] == kb["value"]:
        return "eq"
    if ka["value"] < kb["value"]:
        return "lt"
    return "gt"


def op_minmax(fmt, a, b, is_max):
    """minimumNumber / maximumNumber (strict), implemented here."""
    ka, kb = classify(fmt, a), classify(fmt, b)
    nv = F_NV if (("nan" == ka["kind"] and not ka["quiet"]) or
                  ("nan" == kb["kind"] and not kb["quiet"])) else 0
    if ka["kind"] == "nan" and kb["kind"] == "nan":
        return qnan_bits(fmt), nv
    if ka["kind"] == "nan":
        return mask_bits(fmt, b), nv
    if kb["kind"] == "nan":
        return mask_bits(fmt, a), nv
    rel = op_compare(fmt, a, b)
    if rel == "eq":
        if a == b:
            return mask_bits(fmt, a), 0
        # only +0 / -0 compare equal with different patterns: -0 < +0
        a_neg = bool(ka["sign"])
        pick_a = (not a_neg) if is_max else a_neg
        return mask_bits(fmt, a if pick_a else b), 0
    pick_a = (rel == "gt") if is_max else (rel == "lt")
    return mask_bits(fmt, a if pick_a else b), 0


# ── id table: op + parameters, one line per contract id ───────────────────
OPS = {
    "ftfma_rrrr_rf": ("fma", "ft"),
    "fofma_rrrr_rf": ("fma", "fo"),
    "cs.n_rrrr_rf": ("cs", "lt"),
    "cs.z_rrrr_rf": ("cs", "eq"),
    "cs.p_rrrr_rf": ("cs", "gt"),
    "ftcls_orri_rf": ("classify", "ft"),
    "focls_orri_rf": ("classify", "fo"),
    "ft2fo_orri_rf": ("cvt_ff", "ft", "fo"),
    "ft2ft_orri_rf": ("cvt_ff", "ft", "ft"),
    "fo2ft_orri_rf": ("cvt_ff", "fo", "ft"),
    "fo2fo_orri_rf": ("cvt_ff", "fo", "fo"),
    "ftroot_orri_rf": ("root", "ft"),
    "foroot_orri_rf": ("root", "fo"),
    "ft2it_orri_rf": ("f2i", "ft", 32, True),
    "ft2io_orri_rf": ("f2i", "ft", 64, True),
    "ft2ut_orri_rf": ("f2i", "ft", 32, False),
    "ft2uo_orri_rf": ("f2i", "ft", 64, False),
    "fo2it_orri_rf": ("f2i", "fo", 32, True),
    "fo2io_orri_rf": ("f2i", "fo", 64, True),
    "fo2ut_orri_rf": ("f2i", "fo", 32, False),
    "fo2uo_orri_rf": ("f2i", "fo", 64, False),
    "it2ft_orri_rf": ("i2f", "ft", 32, True),
    "io2ft_orri_rf": ("i2f", "ft", 64, True),
    "ut2ft_orri_rf": ("i2f", "ft", 32, False),
    "uo2ft_orri_rf": ("i2f", "ft", 64, False),
    "it2fo_orri_rf": ("i2f", "fo", 32, True),
    "io2fo_orri_rf": ("i2f", "fo", 64, True),
    "ut2fo_orri_rf": ("i2f", "fo", 32, False),
    "uo2fo_orri_rf": ("i2f", "fo", 64, False),
    "ftrnd_orri_rf": ("rnd", "ft"),
    "fornd_orri_rf": ("rnd", "fo"),
    "ftadd_orrr_rf": ("add", "ft"),
    "ftsub_orrr_rf": ("sub", "ft"),
    "ftmul_orrr_rf": ("mul", "ft"),
    "ftdiv_orrr_rf": ("div", "ft"),
    "ftrem_orrr_rf": ("rem", "ft"),
    "ftsclb_orrr_rf": ("sclb", "ft"),
    "foadd_orrr_rf": ("add", "fo"),
    "fosub_orrr_rf": ("sub", "fo"),
    "fomul_orrr_rf": ("mul", "fo"),
    "fodiv_orrr_rf": ("div", "fo"),
    "forem_orrr_rf": ("rem", "fo"),
    "fosclb_orrr_rf": ("sclb", "fo"),
    "ftsgnn_orrr_rf": ("sign", "ft", True),
    "ftsgnj_orrr_rf": ("sign", "ft", False),
    "fosgnn_orrr_rf": ("sign", "fo", True),
    "fosgnj_orrr_rf": ("sign", "fo", False),
    "ftqcmp_orrr_rf": ("cmp", "ft", True),
    "ftscmp_orrr_rf": ("cmp", "ft", False),
    "foqcmp_orrr_rf": ("cmp", "fo", True),
    "foscmp_orrr_rf": ("cmp", "fo", False),
    "ftmin_orrr_rf": ("minmax", "ft", False),
    "ftmax_orrr_rf": ("minmax", "ft", True),
    "fomin_orrr_rf": ("minmax", "fo", False),
    "fomax_orrr_rf": ("minmax", "fo", True),
}

FAMILY_OF = {
    "fma": "fma", "cs": "cs_rf", "classify": "classify", "cvt_ff": "cvt_ff",
    "root": "root", "f2i": "f2i", "i2f": "i2f", "rnd": "rnd",
    "add": "arith", "sub": "arith", "mul": "arith", "div": "arith",
    "rem": "arith", "sclb": "arith", "sign": "sign", "cmp": "cmp",
    "minmax": "minmax",
}


def entry_fields(inst_id):
    """(dst, srcs, imm) field names, derived from the decode roles."""
    entry = ENTRIES[inst_id]
    dst = None
    srcs = []
    imm = None
    for field in entry.fields:
        if field.role == "dst":
            dst = field
        elif field.role == "src":
            srcs.append(field)
        else:
            imm = field
    return dst, srcs, imm


# ── vector model ──────────────────────────────────────────────────────────
def conv_mode(code, rf_mode):
    """One-hot conversion code -> reference mode (4 = RNA, 0x20 = rf0)."""
    table = {0x01: 0, 0x02: 4, 0x04: 1, 0x08: 3, 0x10: 2}
    if code == 0x20:          # dynamic: rf0[33:32]
        return rf_mode
    if code not in table:
        raise AssertionError("bad conversion code 0x%02x" % code)
    return table[code]


def _init_regs(vec):
    rf = {i: (0xF00D000000000000 + i) & MASK64 for i in range(64)}
    rd = {i: (0xDAD0000000000000 + i) & MASK64 for i in range(64)}
    rd[0] = 0
    rf[0] = vec["rf"].get(0, RF0_RESET)
    for idx, value in vec["rf"].items():
        rf[idx] = value
    for idx, value in vec["rd"].items():
        rd[idx] = value
    return rf, rd


def model(vec):
    """Expected {fault, writes, fcsr} for one vector."""
    inst_id = vec["id"]
    op = OPS[inst_id]
    dst_field, src_fields, imm_field = entry_fields(inst_id)
    fields = vec["fields"]
    rf, rd = _init_regs(vec)

    def read(name):
        bank = "rd" if name.startswith("rd") else "rf"
        idx = fields[name]
        return idx, (rd[idx] if bank == "rd" else rf[idx])

    def read_float(fmt, name):
        idx, raw = read(name)
        return idx, mask_bits(fmt, raw)

    mode = (rf[0] >> 32) & 3
    flags = 0
    writes = []
    kind = op[0]

    if kind == "fma":
        fmt = op[1]
        _, a = read_float(fmt, src_fields[0].name)
        _, b = read_float(fmt, src_fields[1].name)
        _, c = read_float(fmt, src_fields[2].name)
        out, flags = op_fma(fmt, mode, a, b, c)
        dst = fields[dst_field.name]
        rf[dst] = _write_float(fmt, rf[dst], out)
        writes.append(("rf", dst, rf[dst]))
    elif kind == "cs":
        cond_sel = fields[src_fields[0].name]  # rdha: rd-bank condition
        cond = rd[cond_sel]
        if cond >= 1 << 63:
            cond -= 1 << 64
        first = rf[fields[src_fields[1].name]]
        second = rf[fields[src_fields[2].name]]
        take = {"lt": cond < 0, "eq": cond == 0, "gt": cond > 0}[op[1]]
        dst = fields[dst_field.name]
        rf[dst] = first if take else second
        writes.append(("rf", dst, rf[dst]))
    elif kind == "classify":
        fmt = op[1]
        count = fields[imm_field.name]
        dst0 = fields[dst_field.name]
        src0 = fields[src_fields[0].name]
        for i in range(count):
            value = mask_bits(fmt, rf[src0 + i])
            rd[dst0 + i] = op_classify(fmt, value)
            writes.append(("rd", dst0 + i, rd[dst0 + i]))
    elif kind == "cvt_ff":
        src_fmt, dst_fmt = op[1], op[2]
        dst0 = fields[dst_field.name]
        src0 = fields[src_fields[0].name]
        if src_fmt == dst_fmt:
            # Pure copy (ft2ft/fo2fo): 1..63 pairs, no rounding, no flags.
            for i in range(fields[imm_field.name]):
                rf[dst0 + i] = _write_float(dst_fmt, rf[dst0 + i],
                                            mask_bits(src_fmt, rf[src0 + i]))
                writes.append(("rf", dst0 + i, rf[dst0 + i]))
        else:
            code = fields[imm_field.name]
            m = 0 if code == 0 else conv_mode(code, mode)
            value = mask_bits(src_fmt, rf[src0])
            out, f = op_convert_ff(dst_fmt, m, src_fmt, value)
            flags |= f
            rf[dst0] = _write_float(dst_fmt, rf[dst0], out)
            writes.append(("rf", dst0, rf[dst0]))
    elif kind == "root":
        fmt = op[1]
        _, value = read_float(fmt, src_fields[0].name)
        out, flags = op_sqrt(fmt, mode, value)
        dst = fields[dst_field.name]
        rf[dst] = _write_float(fmt, rf[dst], out)
        writes.append(("rf", dst, rf[dst]))
    elif kind == "f2i":
        fmt, width, signed = op[1], op[2], op[3]
        dst0 = fields[dst_field.name]
        src0 = fields[src_fields[0].name]
        m = conv_mode(fields[imm_field.name], mode)
        value = mask_bits(fmt, rf[src0])
        out, f = op_to_int(fmt, m, value, width, signed)
        flags |= f
        rd[dst0] = out
        writes.append(("rd", dst0, rd[dst0]))
    elif kind == "i2f":
        fmt, width, signed = op[1], op[2], op[3]
        dst0 = fields[dst_field.name]
        src0 = fields[src_fields[0].name]
        code = fields[imm_field.name]
        m = 0 if code == 0 else conv_mode(code, mode)
        out, f = op_from_int(fmt, m, rd[src0], width, signed)
        flags |= f
        rf[dst0] = _write_float(fmt, rf[dst0], out)
        writes.append(("rf", dst0, rf[dst0]))
    elif kind == "rnd":
        fmt = op[1]
        onehot = fields[imm_field.name]
        _, value = read_float(fmt, src_fields[0].name)
        out, flags = op_round_int(fmt, value, onehot, mode)
        dst = fields[dst_field.name]
        rf[dst] = _write_float(fmt, rf[dst], out)
        writes.append(("rf", dst, rf[dst]))
    elif kind in ("add", "sub", "mul", "div", "rem", "sclb"):
        fmt = op[1]
        _, a = read_float(fmt, src_fields[0].name)
        second = src_fields[1]
        if kind == "sclb":
            exponent = rd[fields[second.name]]
            if exponent >= 1 << 63:
                exponent -= 1 << 64
            out, flags = op_sclb(fmt, mode, a, exponent)
        else:
            _, b = read_float(fmt, second.name)
            if kind == "add":
                out, flags = op_add(fmt, mode, a, b)
            elif kind == "sub":
                out, flags = op_add(fmt, mode, a, b, negate_b=True)
            elif kind == "mul":
                out, flags = op_mul(fmt, mode, a, b)
            elif kind == "div":
                out, flags = op_div(fmt, mode, a, b)
            else:
                out, flags = op_rem(fmt, a, b)
        dst = fields[dst_field.name]
        rf[dst] = _write_float(fmt, rf[dst], out)
        writes.append(("rf", dst, rf[dst]))
    elif kind == "sign":
        fmt, negate = op[1], op[2]
        sign_mask = sign_bit(fmt)
        first = mask_bits(fmt, rf[fields[src_fields[0].name]])
        second = mask_bits(fmt, rf[fields[src_fields[1].name]])
        second_sign = (second & sign_mask) != 0
        sign = (not second_sign) if negate else second_sign
        out = (first & ~sign_mask) | (sign_mask if sign else 0)
        dst = fields[dst_field.name]
        rf[dst] = _write_float(fmt, rf[dst], out)
        writes.append(("rf", dst, rf[dst]))
    elif kind == "cmp":
        fmt, quiet = op[1], op[2]
        _, a = read_float(fmt, src_fields[0].name)
        _, b = read_float(fmt, src_fields[1].name)
        rel = op_compare(fmt, a, b)
        if rel == "unordered":
            if quiet:
                out = qnan_bits(fmt)
            else:
                out = snan_bits(fmt)
                flags = F_NV
        else:
            out = {"gt": 1, "eq": 0, "lt": MASK64}[rel]
        dst = fields[dst_field.name]
        rd[dst] = out
        writes.append(("rd", dst, out))
    elif kind == "minmax":
        fmt, is_max = op[1], op[2]
        _, a = read_float(fmt, src_fields[0].name)
        _, b = read_float(fmt, src_fields[1].name)
        out, flags = op_minmax(fmt, a, b, is_max)
        dst = fields[dst_field.name]
        rf[dst] = _write_float(fmt, rf[dst], out)
        writes.append(("rf", dst, rf[dst]))
    else:  # pragma: no cover - table completeness guard
        raise AssertionError(f"unknown op {kind}")

    fcsr = (rf[0] & ~0x1F) | ((rf[0] | flags) & 0x1F)
    return {"fault": "None", "writes": writes, "fcsr": fcsr}


def _write_float(fmt, old, bits):
    if fmt == "ft":
        return (old & ~0xFFFFFFFF) | mask_bits(fmt, bits)
    return mask_bits(fmt, bits)


# ── vector generation ─────────────────────────────────────────────────────
class Lcg:
    def __init__(self, seed):
        self.state = seed & MASK64

    def next(self):
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) \
            & MASK64
        return self.state

    def below(self, n):
        return self.next() % n


def edge_bits(fmt):
    f = FMT[fmt]
    one = 0x3F800000 if fmt == "ft" else 0x3FF0000000000000
    half = 0x3F000000 if fmt == "ft" else 0x3FE0000000000000
    two = 0x40000000 if fmt == "ft" else 0x4000000000000000
    maxv = 0x7F7FFFFF if fmt == "ft" else 0x7FEFFFFFFFFFFFFF
    minsub = 1
    minnormal = (1 << f["fracbits"])
    sign = sign_bit(fmt)
    return [0, sign, one, sign | one, half, sign | half, two, sign | two,
            inf_bits(fmt), inf_bits(fmt, 1), qnan_bits(fmt), snan_bits(fmt),
            maxv, sign | maxv, minsub, sign | minsub, minnormal,
            sign | minnormal]


def rand_bits(rng, fmt, pool):
    if rng.below(100) < 45:
        return pool[rng.below(len(pool))]
    return rng.next() & _mask(fmt)


def _vec(name, inst_id, fields, rf=None, rd=None):
    return {"name": name, "id": inst_id, "fields": dict(fields),
            "rf": dict(rf or {}), "rd": dict(rd or {})}


def gen_family(family, seed, per_id):
    rng = Lcg(seed)
    vectors = []
    for inst_id, op in OPS.items():
        if FAMILY_OF[op[0]] != family:
            continue
        fmt = "ft" if op[0] == "cs" else op[1]  # cs.*-rf is a pure data move
        pool = edge_bits(fmt)
        dst_field, src_fields, imm_field = entry_fields(inst_id)
        dst_name = dst_field.name
        kind = op[0]
        for k in range(per_id):
            mode = k % 4
            fields = {}
            # Pre-existing accrued flags: the model must OR the new flags in,
            # so an "overwrite" implementation shows up as a mismatch too.
            rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32) | (k & 0x1F)}
            rd = {}
            # Destination register value: a non-zero high half for ft rows so a
            # full-64-bit miss is visible.
            dst_idx = 2 + (k % 3)
            if dst_field.bank == "rf":
                rf[dst_idx] = 0xAAAA000000000000 | k
            else:
                rd[dst_idx] = 0xBBBB000000000000 | k
            fields[dst_name] = dst_idx
            if kind in ("fma",):
                srcs = [(3, "rf"), (4, "rf"), (5, "rf")]
            elif kind == "cs":
                rd[6] = (0 - (k % 3)) & MASK64  # -1/0/1 cycling
                srcs = [(6, "rd"), (3, "rf"), (4, "rf")]
            elif kind == "classify":
                count = 1 + (k % 3)
                fields[imm_field.name] = count
                srcs = [(8 + k % 2, "rf")]
            elif kind == "cvt_ff":
                if op[1] == op[2]:  # pure copy: 1..63 pairs
                    fields[imm_field.name] = 1 + (k % 3)
                else:  # single register: one-hot code (ft2fo uses SBZ 0)
                    codes = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20)
                    fields[imm_field.name] = (
                        0 if inst_id == "ft2fo_orri_rf"
                        else codes[(k + mode) % 6])
                srcs = [(8 + k % 2, "rf")]
            elif kind == "f2i":
                # Single register: low 6 bits are the one-hot direction.
                codes = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20)
                fields[imm_field.name] = codes[(k + mode) % 6]
                srcs = [(8 + k % 2, "rf")]
            elif kind == "i2f":
                # Single register: 6 inexact forms take one-hot; the two
                # 32-bit exact forms (it2fo/ut2fo) require SBZ 0.
                codes = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20)
                fields[imm_field.name] = (
                    0 if inst_id in ("it2fo_orri_rf", "ut2fo_orri_rf")
                    else codes[(k + mode) % 6])
                srcs = [(8 + k % 2, "rd")]
            elif kind == "root":
                fields[imm_field.name] = 2
                srcs = [(3, "rf")]
            elif kind == "rnd":
                codes = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20)
                fields[imm_field.name] = codes[(k + mode) % 6]
                srcs = [(3, "rf")]
            elif kind == "sclb":
                srcs = [(3, "rf")]
                fields[src_fields[1].name] = 6
                exponents = [0, 1, -1, 2, -2, 10, -10, 149, -149, 200, -200,
                             1024, -1074, 6000, -6000, 1 << 40, -(1 << 40),
                             0x7FFFFFFFFFFFFFFF, -0x8000000000000000]
                rd[6] = exponents[k % len(exponents)] & MASK64
            else:
                srcs = [(3, "rf"), (4, "rf")]
            for pos, (base, bank) in enumerate(srcs):
                if bank == "rf":
                    rf.setdefault(base, rand_bits(rng, fmt, pool))
                else:
                    rd.setdefault(base,
                                  (rng.next() | (rng.below(2) << 63)) & MASK64)
                fields[src_fields[pos].name] = base
            if kind == "classify":
                # one vector per class for the first ten cases
                if k < 10:
                    cls_pool = [
                        snan_bits(fmt), qnan_bits(fmt), inf_bits(fmt, 1),
                        sign_bit(fmt) | 0x3F800000 if fmt == "ft" else
                        sign_bit(fmt) | 0x3FF0000000000000,
                        sign_bit(fmt) | 1, sign_bit(fmt), 0, 1,
                        0x3F800000 if fmt == "ft" else 0x3FF0000000000000,
                        inf_bits(fmt),
                    ]
                    rf[srcs[0][0]] = cls_pool[k % 10]
            name = f"b7-{inst_id}-{k:03d}"
            vectors.append(_vec(name, inst_id, fields, rf, rd))
    return vectors


FAMILY_COUNTS = {
    "arith": 64, "cvt_ff": 32, "f2i": 32, "i2f": 32, "fma": 48, "root": 24,
    "rnd": 72, "minmax": 32, "sign": 16, "cmp": 32, "classify": 32,
    "cs_rf": 12,
}


FAMILY_SEEDS = {
    "arith": 101, "cvt_ff": 202, "f2i": 303, "i2f": 404, "fma": 505,
    "root": 606, "rnd": 707, "minmax": 808, "sign": 909, "cmp": 1010,
    "classify": 1111, "cs_rf": 1212,
}


def build_vectors(seed=20261102):
    vectors = list(edge_vectors())
    for family, per_id in FAMILY_COUNTS.items():
        vectors.extend(gen_family(family, seed + FAMILY_SEEDS[family], per_id))
    return vectors


# ── probe output parsing / verification ───────────────────────────────────
def parse_probe(text):
    records = {}
    current = None
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "VECTOR" and len(parts) == 2:
            current = {"fault": None, "writes": [], "fcsr": None}
            records[parts[1]] = current
        elif parts[0] == "FAULT" and current is not None:
            current["fault"] = parts[1]
        elif parts[0] == "W" and current is not None:
            current["writes"].append((parts[1], int(parts[2]),
                                      int(parts[3], 16)))
        elif parts[0] == "FCSR" and current is not None:
            current["fcsr"] = int(parts[1], 16)
        elif parts[0] == "END":
            current = None
    return records


def verify(vectors, probe_text, verbose=False):
    records = parse_probe(probe_text)
    mismatches = []
    for vec in vectors:
        expect = model(vec)
        got = records.get(vec["name"])
        if got is None:
            mismatches.append((vec, expect, None))
            continue
        ok = (got["fault"] == expect["fault"] and
              sorted(got["writes"]) == sorted(expect["writes"]) and
              got["fcsr"] == expect["fcsr"])
        if not ok:
            mismatches.append((vec, expect, got))
        elif verbose:
            print(f"[PASS] {vec['name']}")
    return len(vectors), mismatches


def describe_mismatch(vec, expect, got):
    detail = [f"{vec['name']} ({vec['id']}) fields={vec['fields']}"]
    if got is None:
        detail.append("  probe produced no record")
        return "\n".join(detail)
    detail.append(f"  expected fault={expect['fault']} writes="
                  f"{[(b, i, hex(v)) for b, i, v in expect['writes']]} "
                  f"fcsr=0x{expect['fcsr']:016x}")
    detail.append(f"  actual   fault={got['fault']} writes="
                  f"{[(b, i, hex(v)) for b, i, v in got['writes']]} "
                  f"fcsr=0x{(got['fcsr'] or 0):016x}")
    return "\n".join(detail)


# ── oracle-vs-oracle cross checks (third implementation) ──────────────────
def cross_check(seed=7717):
    """Return a list of disagreements between this model and the testcase
    oracles for fma / minmax / roundint (plus the sqrt packer vs encode)."""
    errors = []
    rng = Lcg(seed)
    for fmt in ("ft", "fo"):
        pool = edge_bits(fmt)
        for _ in range(400):
            a = rand_bits(rng, fmt, pool)
            b = rand_bits(rng, fmt, pool)
            c = rand_bits(rng, fmt, pool)
            mode = rng.below(4)
            mine = op_fma(fmt, mode, a, b, c)
            theirs = ofma.fma_expect(a, b, c, fmt, mode)
            if mine != (theirs["out"], theirs["flags"]):
                errors.append(("fma", fmt, (a, b, c, mode), mine,
                               (theirs["out"], theirs["flags"])))
        for _ in range(400):
            a = rand_bits(rng, fmt, pool)
            b = rand_bits(rng, fmt, pool)
            is_max = rng.below(2) == 1
            mine = op_minmax(fmt, a, b, is_max)
            theirs = ommx.expect(a, b, fmt, "max" if is_max else "min")
            if mine != (theirs[0], theirs[1]):
                errors.append(("minmax", fmt, (a, b, is_max), mine, theirs))
        for _ in range(400):
            a = rand_bits(rng, fmt, pool)
            onehot = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20)[rng.below(6)]
            rf_mode = rng.below(4)
            mine = op_round_int(fmt, a, onehot, rf_mode)
            theirs = ornd.expect(a, fmt, onehot, rf_mode)
            if mine != (theirs["out"], theirs["flags"]):
                errors.append(("rnd", fmt, (a, onehot, rf_mode), mine,
                               (theirs["out"], theirs["flags"])))
        # sqrt packer vs encode: squaring a representable value must round-trip
        for _ in range(200):
            bits = rand_bits(rng, fmt, pool)
            k = classify(fmt, bits)
            if k["kind"] != "normal" or k["sign"]:
                continue
            sq = k["value"] * k["value"]
            mine = encode(sq, fmt, 0)
            root = op_sqrt(fmt, 0, bits)
            if mine != root[0:2] and root[1] == 0:
                # exact square root of a square must be exact
                errors.append(("sqrt-roundtrip", fmt, bits, root, mine))
    return errors


# ── CLI ───────────────────────────────────────────────────────────────────
def _emit(vectors, path):
    lines = []
    for vec in vectors:
        token = [vec["name"], vec["id"]]
        for name, value in vec["fields"].items():
            token.append(f"{name}=0x{value:x}")
        for idx, value in sorted(vec["rf"].items()):
            token.append(f"rf{idx}=0x{value:016x}")
        for idx, value in sorted(vec["rd"].items()):
            token.append(f"rd{idx}=0x{value:016x}")
        lines.append(" ".join(token))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--expect", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--seed", type=int, default=20261102)
    args = parser.parse_args(argv)

    if args.selftest:
        errors = cross_check()
        for error in errors[:20]:
            print(f"[FAIL] cross-check {error}")
        print(f"cross-check disagreements={len(errors)}")
        return 0 if not errors else 1

    vectors = build_vectors(args.seed)
    if args.emit:
        _emit(vectors, args.emit)
        counts = {}
        for vec in vectors:
            counts[vec["id"]] = counts.get(vec["id"], 0) + 1
        if not args.quiet:
            print(f"oracle vectors={len(vectors)} ids={len(counts)}")
    if args.expect:
        payload = []
        for vec in vectors:
            expect = model(vec)
            payload.append({"vector": vec, "expected": {
                "fault": expect["fault"],
                "writes": [[b, i, v] for b, i, v in expect["writes"]],
                "fcsr": expect["fcsr"],
            }})
        Path(args.expect).write_text(json.dumps(payload), encoding="utf-8")
    if args.verify:
        probe_text = Path(args.verify).read_text(encoding="utf-8")
        total, mismatches = verify(vectors, probe_text)
        for vec, expect, got in mismatches[:20]:
            print(describe_mismatch(vec, expect, got))
        print(f"oracle vectors={total}")
        print(f"oracle mismatch={len(mismatches)}")
        return 0 if not mismatches else 1
    return 0



# ── curated boundary vectors (spec §必测用例 list) ─────────────────────────
def edge_vectors():
    """Hand-picked boundaries from the task's 必测用例 list.

    They complement the random pool: saturation limits, exact ties, signed
    zeros, NaN classes and the scaleB/remainder special cases.  Every vector is
    still judged by the model above (never by a hard-coded expectation), so a
    wrong model shows up as a mismatch rather than being masked.
    """
    out = []
    seq = [0]

    def add(inst_id, tag, fields, rf=None, rd=None):
        seq[0] += 1
        out.append(_vec(f"edge-{inst_id}-{tag}-{seq[0]}", inst_id, fields,
                        rf, rd))

    def f32(x):
        return x & 0xFFFFFFFF

    one32, one64 = 0x3F800000, 0x3FF0000000000000
    half32, half64 = 0x3F000000, 0x3FE0000000000000
    # ---- convert_f2i: saturation and inexact boundaries ------------------
    f2i_values32 = [0, 0x80000000, f32(one32), 0xBF800000, 0x4F000000,
                    0xCF000000, 0x4F800000, 0xCF800000, 0x3FC00000,
                    0xBF800001, 0x7F7FFFFF, 0xFF7FFFFF, 0x7FC00000,
                    0x7F800001, 0x7F800000, 0xFF800000, 0x00000001,
                    0x80000001, 0x5F000000, 0xDF000000]
    f2i_values64 = [0, 0x8000000000000000, one64, 0xBFF0000000000000,
                    0x41E0000000000000, 0xC1E0000000000000,
                    0x41F0000000000000, 0xC1F0000000000000,
                    0x3FE0000000000000, 0x43E0000000000000,
                    0xC3E0000000000000, 0x43F0000000000000,
                    0x7FEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF, k_qnan(),
                    0x7FF0000000000001, 0x7FF0000000000000,
                    0xFFF0000000000000, 0x0000000000000001,
                    0x8000000000000001]
    for inst_id in ("ft2it_orri_rf", "ft2io_orri_rf", "ft2ut_orri_rf",
                    "ft2uo_orri_rf", "fo2it_orri_rf", "fo2io_orri_rf",
                    "fo2ut_orri_rf", "fo2uo_orri_rf"):
        fmt = OPS[inst_id][1]
        values = f2i_values32 if fmt == "ft" else f2i_values64
        for mode, code in enumerate((0x01, 0x04, 0x08, 0x10)):
            for pos, value in enumerate(values):
                if pos % 2 and mode != (pos % 4):
                    continue  # keep the set bounded but cover all modes
                rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                      3: value}
                add(inst_id, f"m{mode}-{pos}", {"rdhb": 2, "rfhc": 3,
                                                "immu6": code}, rf)
    # ---- convert_i2f: integer extremes -----------------------------------
    i2f_values = [0, 1, (1 << 31) - 1, 1 << 31, (1 << 32) - 1,
                  (1 << 63) - 1, 1 << 63, MASK64, (1 << 24) + 1,
                  (1 << 24) - 1, (1 << 53) + 1, 0xFFFFFFFF80000000]
    for inst_id in ("it2ft_orri_rf", "io2ft_orri_rf", "ut2ft_orri_rf",
                    "uo2ft_orri_rf", "it2fo_orri_rf", "io2fo_orri_rf",
                    "ut2fo_orri_rf", "uo2fo_orri_rf"):
        exact = inst_id in ("it2fo_orri_rf", "ut2fo_orri_rf")
        for mode, code in enumerate((0x01, 0x04, 0x08, 0x10)):
            for pos, value in enumerate(i2f_values):
                if pos % 2 and mode != (pos % 4):
                    continue
                rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32)}
                add(inst_id, f"m{mode}-{pos}", {"rfhb": 2, "rdhc": 3,
                                                "immu6": 0 if exact else code},
                    rf, {3: value & MASK64})
    # ---- roundint: six modes x ties / zeros / specials -------------------
    rnd_values32 = [0, 0x80000000, half32, 0xBF000000, 0x3FC00000,
                    0xC0000000, 0x40200000, 0xC0200000, 0x4B402000,
                    0x4B000000, 0x7F800000, 0xFF800000, 0x7FC00000,
                    0x7F800001]
    rnd_values64 = [0, 0x8000000000000000, half64, 0xBFE0000000000000,
                    0x3FF8000000000000, 0xC008000000000000,
                    0x4004000000000000, 0xC004000000000000, one64,
                    0x4330000000000000, 0x7FF0000000000000,
                    0xFFF0000000000000, k_qnan(), 0x7FF0000000000001]
    for inst_id in ("ftrnd_orri_rf", "fornd_orri_rf"):
        fmt = OPS[inst_id][1]
        values = rnd_values32 if fmt == "ft" else rnd_values64
        for onehot in (0x01, 0x02, 0x04, 0x08, 0x10, 0x20):
            for pos, value in enumerate(values):
                for mode in ((0, 1, 2, 3) if onehot == 0x20 else (0,)):
                    rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                          3: value}
                    add(inst_id, f"m{onehot:02x}-{pos}-{mode}",
                        {"rfhb": 2, "rfhc": 3, "immu6": onehot}, rf)
    # ---- arith: zeros, infinities, subnormals, overflow ------------------
    tie = {"ft": 0x33800000, "fo": 0x3CA0000000000000}  # 2^-24 / 2^-53
    for fmt in ("ft", "fo"):
        pool = edge_bits(fmt)
        for kind in ("add", "sub", "mul", "div"):
            inst_id = {"ft": {"add": "ftadd_orrr_rf", "sub": "ftsub_orrr_rf",
                              "mul": "ftmul_orrr_rf", "div": "ftdiv_orrr_rf"},
                       "fo": {"add": "foadd_orrr_rf", "sub": "fosub_orrr_rf",
                              "mul": "fomul_orrr_rf",
                              "div": "fodiv_orrr_rf"}}[fmt][kind]
            for mode in range(4):
                for pos in range(10):
                    a = pool[(pos * 3 + mode) % len(pool)]
                    b = pool[(pos * 5 + mode + 1) % len(pool)]
                    rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                          3: a, 4: b, 2: 0xAAAA000000000000}
                    add(inst_id, f"m{mode}-{pos}",
                        {"rfhb": 2, "rfhc": 3, "rfhd": 4}, rf)
                # exact half-ulp tie: 1 + 2^-(p) and -1 - 2^-(p)
                for tag, a, b in (("tie+", pool[2], tie[fmt]),
                                  ("tie-", pool[3], tie[fmt])):
                    rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                          3: a, 4: b, 2: 0xAAAA000000000000}
                    add(inst_id, f"m{mode}-{tag}",
                        {"rfhb": 2, "rfhc": 3, "rfhd": 4}, rf)
    # ---- rem: the spec examples and the special cases --------------------
    for fmt, inst_id in (("ft", "ftrem_orrr_rf"), ("fo", "forem_orrr_rf")):
        pool = edge_bits(fmt)
        for mode in range(4):
            for pos, (a, b) in enumerate([
                    (pool[2], pool[6]), (pool[3], pool[6]),
                    (pool[2], pool[4]), (pool[14], pool[4]),
                    (pool[2], pool[8]), (pool[8], pool[2]),
                    (pool[2], pool[0]), (pool[0], pool[2]),
                    (pool[8], pool[8]), (pool[10], pool[2]),
                    (pool[11], pool[2]), (pool[2], pool[11])]):
                rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                      3: a, 4: b, 2: 0xAAAA000000000000}
                add(inst_id, f"m{mode}-{pos}", {"rfhb": 2, "rfhc": 3,
                                                "rfhd": 4}, rf)
    # ---- scaleB: the exponent range and the rdHD decoy -------------------
    for fmt, inst_id in (("ft", "ftsclb_orrr_rf"), ("fo", "fosclb_orrr_rf")):
        pool = edge_bits(fmt)
        exponents = [0, 1, -1, 149, -149, 1074, -1074, 2000, -2000,
                     1 << 62, -(1 << 62)]
        for mode in range(4):
            for pos, exponent in enumerate(exponents):
                value = pool[(pos + mode) % len(pool)]
                rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                      3: value, 2: 0xAAAA000000000000, 4: 0x3F800000}
                add(inst_id, f"m{mode}-{pos}",
                    {"rfhb": 2, "rfhc": 3, "rdhd": 6}, rf,
                    {6: exponent & MASK64})
    # ---- fma: spec counterexample and the NaN/Inf/zero rules -------------
    for fmt, inst_id in (("ft", "ftfma_rrrr_rf"), ("fo", "fofma_rrrr_rf")):
        pool = edge_bits(fmt)
        cases = [
            (pool[2], pool[3], pool[4]),      # 1.0 * 1.0 + 1.0
            (pool[2], pool[3], pool[5]),      # zero sum
            (pool[0], pool[8], pool[10]),     # 0 * Inf + qNaN
            (pool[8], pool[2], pool[9]),      # Inf - Inf
            (pool[14], pool[2], pool[0]),     # tiny * 1 + 0
            (pool[12], pool[2], pool[12]),    # max * 1 + max (overflow)
            (pool[10], pool[2], pool[2]),     # qNaN * 1 + 1
            (pool[11], pool[2], pool[2]),     # sNaN * 1 + 1
            (pool[2], pool[3], pool[6]),      # 1 + 1 + 1
            (pool[3], pool[3], pool[6]),      # -1 - 1 + 1
            (pool[2], pool[2], tie[fmt]),     # 1*1 + 2^-p: exact tie
            (pool[3], pool[2], tie[fmt]),     # -1 + 2^-p: tie
        ]
        for mode in range(4):
            for pos, (a, b, c) in enumerate(cases):
                rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                      3: a, 4: b, 5: c, 2: 0xAAAA000000000000}
                add(inst_id, f"m{mode}-{pos}",
                    {"rfha": 2, "rfhb": 3, "rfhc": 4, "rfhd": 5}, rf)
    # ---- min/max: signed zeros, single/double NaN, Inf -------------------
    for fmt, (imin, imax) in (("ft", ("ftmin_orrr_rf", "ftmax_orrr_rf")),
                              ("fo", ("fomin_orrr_rf", "fomax_orrr_rf"))):
        pool = edge_bits(fmt)
        pairs = [(pool[0], pool[1]), (pool[1], pool[0]), (pool[2], pool[3]),
                 (pool[2], pool[10]), (pool[10], pool[2]),
                 (pool[10], pool[11]), (pool[11], pool[10]),
                 (pool[8], pool[9]), (pool[2], pool[2]), (pool[14], pool[0])]
        for inst_id in (imin, imax):
            for pos, (a, b) in enumerate(pairs):
                rf = {3: a, 4: b, 2: 0xAAAA000000000000}
                add(inst_id, f"{pos}", {"rfhb": 2, "rfhc": 3, "rfhd": 4}, rf)
    # ---- compare: ordering and unordered ---------------------------------
    for fmt, (ins_q, ins_s) in (("ft", ("ftqcmp_orrr_rf", "ftscmp_orrr_rf")),
                                ("fo", ("foqcmp_orrr_rf",
                                        "foscmp_orrr_rf"))):
        pool = edge_bits(fmt)
        pairs = [(pool[2], pool[3]), (pool[2], pool[2]), (pool[3], pool[2]),
                 (pool[0], pool[1]), (pool[8], pool[2]), (pool[2], pool[8]),
                 (pool[2], pool[10]), (pool[11], pool[11]),
                 (pool[14], pool[0])]
        for inst_id in (ins_q, ins_s):
            for pos, (a, b) in enumerate(pairs):
                rf = {3: a, 4: b}
                add(inst_id, f"{pos}", {"rdhb": 2, "rfhc": 3, "rfhd": 4}, rf)
    # ---- classify: the ten classes ---------------------------------------
    for fmt, inst_id in (("ft", "ftcls_orri_rf"), ("fo", "focls_orri_rf")):
        pool = edge_bits(fmt)
        for pos in range(10):
            rf = {8: pool[pos],
                  9: 0xDEADBEEFDEADBEEF}
            add(inst_id, f"{pos}", {"rdhb": 2, "rfhc": 8, "immu6": 2}, rf)
    # ---- convert_ff: payload, overflow, underflow ------------------------
    for src, dst in (("ft", "fo"), ("ft", "ft"), ("fo", "ft"), ("fo", "fo")):
        inst_id = f"{src}2{dst}_orri_rf"
        pool = edge_bits(src)
        values = pool + ([0x7FC12345] if src == "ft" else
                         [0x7FF8000000000123, 0x7FF0000000000001])
        for mode in range(4):
            for pos, value in enumerate(values):
                if pos % 3 and mode != (pos % 4):
                    continue
                rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (mode << 32),
                      8: value, 2: 0xAAAA000000000000}
                if src == dst:      # pure copy: element count
                    code = 1
                elif inst_id == "ft2fo_orri_rf":  # exact widening: SBZ
                    code = 0
                else:               # fo2ft: one-hot direction
                    code = (0x01, 0x04, 0x08, 0x10)[mode]
                add(inst_id, f"m{mode}-{pos}", {"rfhb": 2, "rfhc": 8,
                                                "immu6": code}, rf)
    # ---- fo2ft overflow: the 18 cells of spec/SimRISC-07 §1.4 ------------
    # Sign of the exact result crossed with the rounding direction; the shape
    # is ±Inf only for RNE/RNA, RUP+ and RDN-.  The dynamic code 0x20 reads
    # rf0[33:32] (00 RNE / 01 RTZ / 10 RDN / 11 RUP); the RNA code 0x02 is
    # static, so its rf0 mode is irrelevant (set to 0).
    fo_max = 0x7FEFFFFFFFFFFFFF
    for code, rf_mode in ((0x01, 0), (0x02, 0), (0x04, 1), (0x08, 3),
                          (0x10, 2), (0x20, 0), (0x20, 1), (0x20, 2),
                          (0x20, 3)):
        for pos, value in enumerate((fo_max, fo_max | (1 << 63))):
            rf = {0: (RF0_RESET & ~RF0_WRITABLE) | (rf_mode << 32), 8: value}
            add("fo2ft_orri_rf", f"of-{code:02x}-{rf_mode}-{pos}",
                {"rfhb": 2, "rfhc": 8, "immu6": code}, rf)
    # ---- sign: abs/neg/copy/negate with a NaN payload --------------------
    for fmt, (isgnn, isgnj) in (("ft", ("ftsgnn_orrr_rf", "ftsgnj_orrr_rf")),
                                ("fo", ("fosgnn_orrr_rf",
                                        "fosgnj_orrr_rf"))):
        pool = edge_bits(fmt)
        pairs = [(pool[2], pool[0]), (pool[2], pool[1]), (pool[3], pool[1]),
                 (pool[2], pool[2]), (pool[10], pool[0]), (pool[11], pool[1]),
                 (pool[0], pool[2]), (pool[14], pool[8])]
        for inst_id in (isgnn, isgnj):
            for pos, (a, b) in enumerate(pairs):
                rf = {3: a, 4: b, 2: 0xAAAA000000000000}
                add(inst_id, f"{pos}", {"rfhb": 2, "rfhc": 3, "rfhd": 4}, rf)
    # ---- cs.*-rf: condition polarity and rf0 as a source -----------------
    for inst_id, cond in (("cs.n_rrrr_rf", "lt"), ("cs.z_rrrr_rf", "eq"),
                          ("cs.p_rrrr_rf", "gt")):
        for pos, value in enumerate([0, 1, MASK64, MASK64 - 1, 1 << 63]):
            rf = {3: 0x1111111111111111, 4: 0x2222222222222222}
            add(inst_id, f"{pos}", {"rdha": 6, "rfhb": 2, "rfhc": 3,
                                    "rfhd": 4}, rf, {6: value})
        rf = {0: RF0_RESET, 3: 0x1111111111111111}
        add(inst_id, "rf0src", {"rdha": 6, "rfhb": 2, "rfhc": 0, "rfhd": 3},
            rf, {6: 0 if cond == "eq" else (1 if cond == "gt" else MASK64)})
    return out


def k_qnan():
    # fo qNaN used by the curated list (kept local to make the tables readable)
    return 0x7FF8000000000000
if __name__ == "__main__":
    sys.exit(main())
