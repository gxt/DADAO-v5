#!/usr/bin/env python3
# Independent reference model for the DADAO FP infrastructure (m12-chipyard-011).
#
# Three things live here:
#
#   * the encode/decode primitives of the recoded ("recFN") format that the
#     core uses internally (the semantics of berkeley-hardfloat's
#     recFNFromFN / fNFromRecFN / rawFloatFromFN / rawFloatFromRecFN);
#   * an *exact* rounding oracle (`round_exact`) written from the IEEE 754
#     definitions of spec/SimRISC-07 §1.4 / §1.1 (exact rational value,
#     round the significand, tininess detected after rounding).  It is the
#     independent oracle: it never looks at the bit-level rounding algorithm;
#   * the same rounding written *bit-exactly* as the RTL does it
#     (`round_bits`, mirroring WumingRoundAnyRawFNToRecFN.scala), so the two
#     can be cross-checked in plain Python before any RTL runs.
#
# Nothing here is derived from hardfloat source code; the field layout and the
# exponent re-basing are the ones documented in WumingFP.scala (and verified
# against the hardfloat RTL by the unit bench, see `fp_unit`).
#
# Usage:
#   python3 tools/chipyard/fp_ref.py selfcheck     # bits model == exact model
#   python3 tools/chipyard/fp_ref.py vectors DIR   # write unit-bench vectors
#   python3 tools/chipyard/fp_ref.py dir           # task book directory

import os
import random
import struct
import sys

# ── formats ────────────────────────────────────────────────────────────────
FT = (8, 24)
FO = (11, 53)

# rounding directions (the codes of WumingRoundMode, i.e. hardfloat's)
RNE, RTZ, RDN, RUP, RNA = 0, 1, 2, 3, 4
MODE_NAMES = {RNE: "RNE", RTZ: "RTZ", RDN: "RDN", RUP: "RUP", RNA: "RNA"}

# DADAO five-direction encoding of the `immu6` field (ADR-0050 D2)
ONEHOT = {0x01: RNE, 0x02: RNA, 0x04: RTZ, 0x08: RUP, 0x10: RDN}


def bits(x, w):
    return x & ((1 << w) - 1)


def clz(x, w):
    """Index of the highest set bit, `w` when x == 0 (hardfloat's
    countLeadingZeros on a w-bit field)."""
    return w if x == 0 else w - 1 - x.bit_length() + 1


def raw_from_fn(ew, sw, x):
    """IEEE binary -> unpacked raw float (hardfloat rawFloatFromFN)."""
    sign = (x >> (ew + sw - 1)) & 1
    exp_in = bits(x >> (sw - 1), ew)
    fract_in = bits(x, sw - 1)
    is_zero_exp = exp_in == 0
    is_zero_fract = fract_in == 0

    norm_dist = clz(fract_in, sw - 1)
    subnorm_fract = bits(bits(fract_in << norm_dist, sw - 2) << 1, sw - 1)
    adjusted_exp = bits(
        (bits((1 << (ew + 1)) - 1 - norm_dist, ew + 1)
         if is_zero_exp else exp_in)
        + ((1 << (ew - 1)) | (2 if is_zero_exp else 1)), ew + 1)

    is_zero = is_zero_exp and is_zero_fract
    # the exponent of a zero value is pinned to 0 (see WumingFP.scala)
    if is_zero:
        adjusted_exp = 0
    is_special = ((adjusted_exp >> (ew - 1)) & 3) == 3
    sig = (0 << 1 | (0 if is_zero else 1)) << (sw - 1)
    sig |= subnorm_fract if is_zero_exp else fract_in
    return dict(is_nan=is_special and not is_zero_fract,
                is_inf=is_special and is_zero_fract,
                is_zero=is_zero, sign=sign, s_exp=adjusted_exp, sig=sig)


def recfn_from_raw(r, ew, sw):
    hi = 0 if r["is_zero"] else bits(r["s_exp"] >> (ew - 2), 3)
    if r["is_nan"]:
        hi |= 1
    return ((r["sign"] << (ew + sw))
            | (bits(hi, 3) << (sw - 1 + ew - 2))
            | (bits(r["s_exp"], ew - 2) << (sw - 1))
            | bits(r["sig"], sw - 1))


def recfn_from_fn(ew, sw, x):
    return recfn_from_raw(raw_from_fn(ew, sw, x), ew, sw)


def raw_from_recfn(ew, sw, x):
    """Recoded format -> unpacked raw float (hardfloat rawFloatFromRecFN)."""
    exp = bits(x >> (sw - 1), ew + 1)
    is_zero = ((exp >> (ew - 2)) & 7) == 0
    is_special = ((exp >> (ew - 1)) & 3) == 3
    is_nan = is_special and ((exp >> (ew - 2)) & 1) == 1
    return dict(is_nan=is_nan, is_inf=is_special and not is_nan,
                is_zero=is_zero, sign=(x >> (ew + sw)) & 1, s_exp=exp,
                sig=((0 << 1 | (0 if is_zero else 1)) << (sw - 1))
                    | bits(x, sw - 1))


def fn_from_recfn(ew, sw, x):
    """Recoded format -> IEEE binary (hardfloat fNFromRecFN)."""
    min_norm = (1 << (ew - 1)) + 2
    r = raw_from_recfn(ew, sw, x)
    is_sub = r["s_exp"] < min_norm
    sh_w = max(1, (sw - 1).bit_length())  # log2Up(sigWidth-1)
    denorm_shift = bits(1 - bits(r["s_exp"], sh_w), sh_w)
    denorm_fract = bits((r["sig"] >> 1) >> denorm_shift, sw - 1)
    exp_out = 0 if is_sub else bits(
        r["s_exp"] - ((1 << (ew - 1)) + 1), ew)
    if r["is_nan"] or r["is_inf"]:
        exp_out = (1 << ew) - 1
    fract_out = (denorm_fract if is_sub
                 else (0 if r["is_inf"] else bits(r["sig"], sw - 1)))
    return (r["sign"] << (ew + sw - 1)) | (exp_out << (sw - 1)) | fract_out


def classify_fn(ew, sw, x):
    """SimRISC-07 §5 class bits of an IEEE binary value, bit0 sNaN ... bit9
    positiveInfinity."""
    r = raw_from_fn(ew, sw, x)
    return classify_raw(r, ew, sw)


def classify_raw(r, ew, sw):
    min_norm = (1 << (ew - 1)) + 2
    quiet = r["sig"] & (1 << (sw - 2))
    sig_nan = r["is_nan"] and not quiet
    quiet_nan = r["is_nan"] and bool(quiet)
    finite_nz = not r["is_nan"] and not r["is_inf"] and not r["is_zero"]
    subnormal = r["s_exp"] < min_norm
    normal = finite_nz and not subnormal
    out = 0
    if sig_nan:
        out |= 1 << 0
    if quiet_nan:
        out |= 1 << 1
    if r["sign"] and r["is_inf"]:
        out |= 1 << 2
    if r["sign"] and normal:
        out |= 1 << 3
    if r["sign"] and finite_nz and subnormal:
        out |= 1 << 4
    if r["sign"] and r["is_zero"]:
        out |= 1 << 5
    if not r["sign"] and r["is_zero"]:
        out |= 1 << 6
    if not r["sign"] and finite_nz and subnormal:
        out |= 1 << 7
    if not r["sign"] and normal:
        out |= 1 << 8
    if not r["sign"] and r["is_inf"]:
        out |= 1 << 9
    return out


def sign_inject(hc, hd, signpos, invert):
    """copySign / negate-copySign of spec/SimRISC-07 §3 (sign at bit 31 for ft,
    63 for fo; every other bit comes from rfHC)."""
    mask = 1 << signpos
    s = hd & mask
    if invert:
        s ^= mask
    return (hc & ~mask) | s


# ── the bit-level rounding model (mirrors WumingRoundAnyRawFNToRecFN) ──────
def round_bits(ie, isig, oe, osig, r, mode, invalid_exc=False,
               infinite_exc=False):
    """Returns (recfn_out, flags) with flags in rf0 order (bit0 NV ... bit4 NX).
    The code follows the RTL expression by expression."""
    def sgn(v, w):  # signed interpretation
        return v - (1 << w) if (v >> (w - 1)) & 1 else v

    never_under = ie < oe
    never_over = ie < oe
    out_nan_exp = 7 << (oe - 2)
    out_inf_exp = 6 << (oe - 2)
    out_max_finite_exp = out_inf_exp - 1
    out_min_norm_exp = (1 << (oe - 1)) + 2
    out_min_nonzero_exp = out_min_norm_exp - osig + 1

    adj_w = oe + 2
    if ie < oe:
        s_adj = bits(sgn(r["s_exp"], ie + 2)
                     + ((1 << oe) - (1 << ie)), adj_w)
        s_adj = s_adj + (1 << adj_w) if s_adj >> (adj_w - 1) else s_adj
        s_adj = sgn(s_adj, adj_w)
    elif ie == oe:
        s_adj = sgn(r["s_exp"], ie + 2)
    else:
        s_adj = sgn(r["s_exp"], ie + 2) + ((1 << oe) - (1 << ie))

    sig_w = osig + 3
    if isig <= osig + 2:
        adj_sig = bits(r["sig"] << (osig - isig + 2), sig_w)
    else:
        high = bits(r["sig"] >> (isig - osig - 1), osig + 2)
        low = 1 if bits(r["sig"], isig - osig - 2) else 0
        adj_sig = (high << 1) | low

    denorm_steps = out_min_norm_exp - s_adj
    extra_drop = (0 if denorm_steps <= 0
                  else min(denorm_steps, sig_w))
    drop = extra_drop + 2

    full_mask = (1 << sig_w) - 1
    if drop == 0:
        below_mask = 0
    elif drop - 1 >= sig_w:
        below_mask = full_mask
    else:
        below_mask = full_mask >> (sig_w - (drop - 1))
    round_pos = (adj_sig >> (drop - 1)) & 1 if drop >= 1 else 0
    extra = 1 if (adj_sig & below_mask) else 0
    any_round = bool(round_pos or extra)

    kept = adj_sig >> drop
    round_mag_up = ((mode == RDN and r["sign"])
                    or (mode == RUP and not r["sign"]))
    inc = ((mode == RNE and round_pos and (extra or (kept & 1)))
           or (mode == RNA and round_pos)
           or (round_mag_up and any_round))
    # The result's significand is re-normalised: a subnormal result keeps the
    # redundant low bits clear so that the recoded word has exactly one
    # spelling (the decoder drops them anyway).
    rounded = bits((kept + (1 if inc else 0)) << extra_drop, osig + 1)
    carry = (rounded >> osig) & 1
    s_rounded = s_adj + carry

    common_exp = bits(s_rounded, oe + 1)
    common_fract = bits(rounded, osig - 1)

    total_under = False if never_under else s_rounded < out_min_nonzero_exp
    overflow_c = False if never_over else (s_rounded >> (oe - 1)) >= 3
    common_inexact = total_under or any_round
    common_under = common_inexact and s_rounded < out_min_norm_exp

    is_nan_out = invalid_exc or r["is_nan"]
    not_nan_inf_out = infinite_exc or r["is_inf"]
    common_case = not is_nan_out and not not_nan_inf_out and not r["is_zero"]

    overflow = common_case and overflow_c
    underflow = common_case and not never_under and common_under
    inexact = overflow or (common_case and common_inexact)

    overflow_mag_up = mode in (RNE, RNA) or round_mag_up
    peg_min = common_case and total_under and round_mag_up
    peg_max = overflow and not overflow_mag_up
    not_nan_inf = not_nan_inf_out or (overflow and overflow_mag_up)

    sign_out = 0 if is_nan_out else r["sign"]
    exp_out = common_exp
    if r["is_zero"] or total_under:
        exp_out &= ~(7 << (oe - 2))
    if peg_min:
        # (common & m) | m == m: a pegged magnitude always encodes the smallest
        # nonzero exponent, whatever the sub-quantum exponent bits were.
        exp_out &= out_min_nonzero_exp
        exp_out |= out_min_nonzero_exp
    if peg_max:
        exp_out &= ~(1 << (oe - 1))
        exp_out |= out_max_finite_exp
    if not_nan_inf:
        exp_out &= ~(1 << (oe - 2))
        exp_out |= out_inf_exp
    if is_nan_out:
        exp_out |= out_nan_exp

    quiet_bit = 1 << (osig - 2)
    if isig == osig:
        payload = bits(r["sig"], osig - 1)
    elif isig > osig:
        low = 1 if bits(r["sig"], isig - osig) else 0
        payload = bits(bits(r["sig"] >> (isig - osig), osig - 1)
                       | (low * ((1 << (osig - 1)) - 1)), osig - 1)
    else:
        payload = bits(bits(r["sig"], isig - 1) << (osig - isig), osig - 1)
    nan_fract = quiet_bit if (invalid_exc or not r["is_nan"]) \
        else (payload | quiet_bit)

    if is_nan_out or r["is_zero"] or total_under:
        fract_out = nan_fract if is_nan_out else 0
    else:
        fract_out = common_fract
    if peg_max:
        fract_out |= (1 << (osig - 1)) - 1
    fract_out = bits(fract_out, osig - 1)

    out = (sign_out << (oe + osig)) | (bits(exp_out, oe + 1) << (osig - 1)) \
        | fract_out
    flags = ((1 if inexact else 0) << 4) | ((1 if underflow else 0) << 3) \
        | ((1 if overflow else 0) << 2) \
        | ((1 if infinite_exc else 0) << 1) | (1 if invalid_exc else 0)
    return out, flags


# ── the exact oracle ──────────────────────────────────────────────────────
def _round_int(num, den, mode, negative):
    """Round the positive rational num/den to an integer (den > 0)."""
    q, rem = divmod(num, den)
    if rem == 0:
        return q, False
    if mode == RTZ:
        return q, True
    if mode == RUP:
        return (q + 1, True) if not negative else (q, True)
    if mode == RDN:
        return (q + 1, True) if negative else (q, True)
    # nearest: compare 2*rem with den
    twice = 2 * rem
    if twice > den:
        return q + 1, True
    if twice < den:
        return q, True
    if mode == RNA:
        return q + 1, True
    # RNE
    return (q + 1 if q & 1 else q), True


def round_exact(ie, isig, oe, osig, r, mode, invalid_exc=False,
                infinite_exc=False):
    """Exact IEEE rounding oracle: same input/output contract as round_bits."""
    sign = r["sign"]
    if invalid_exc:
        # canonical quiet NaN, NV
        return (((0 << (oe + osig)) | ((7 << (oe - 2)) << (osig - 1))
                 | (1 << (osig - 2))), (1 << 0))
    if r["is_nan"]:
        quiet_bit = 1 << (osig - 2)
        if isig == osig:
            payload = bits(r["sig"], osig - 1)
        elif isig > osig:
            low = 1 if bits(r["sig"], isig - osig) else 0
            payload = bits(bits(r["sig"] >> (isig - osig), osig - 1)
                           | (low * ((1 << (osig - 1)) - 1)), osig - 1)
        else:
            payload = bits(bits(r["sig"], isig - 1) << (osig - isig),
                           osig - 1)
        return (((0 << (oe + osig)) | ((7 << (oe - 2)) << (osig - 1))
                 | payload | quiet_bit), 0)
    if r["is_inf"]:
        return (((sign << (oe + osig)) | ((6 << (oe - 2)) << (osig - 1))), 0)
    if r["is_zero"]:
        return sign << (oe + osig), 0

    # exact magnitude: sig * 2^(s_exp - 2^ie - (isig-1))
    mant = r["sig"]
    e2 = r["s_exp"] - (1 << ie) - (isig - 1)
    return round_dyadic(oe, osig, sign, mant, e2, mode)


def round_dyadic(oe, osig, sign, mant, e2, mode):
    """Round the exact dyadic value ``(-1)^sign * mant * 2^e2`` to the IEEE
    format ``(oe, osig)``; returns ``(recoded word, rf0[4:0] flags)``.

    This is the *only* place a value is rounded: every arithmetic oracle below
    forms its exact result as an integer mantissa and an exponent, so the
    arithmetic oracles and the rounding oracle cannot drift apart, and none of
    them mirrors the RTL.
    """
    if mant == 0:
        return sign << (oe + osig), 0

    emin = 2 - (1 << (oe - 1))              # smallest normal exponent
    emax = (1 << (oe - 1)) - 1
    e_floor = mant.bit_length() - 1 + e2    # floor(log2(value))

    # quantum exponent (value of the last representable bit)
    qexp = max(e_floor, emin) - (osig - 1)
    # value / 2^qexp as an exact rational
    shift = e2 - qexp
    if shift >= 0:
        num, den = mant << shift, 1
    else:
        num, den = mant, 1 << (-shift)
    mag, inexact = _round_int(num, den, mode, bool(sign))

    # significand carry: normalise an exact power of two result
    e_res = qexp  # exponent of the LSB of `mag`
    if mag >= (1 << osig):
        mag >>= 1
        e_res += 1
    res_e = e_res + (mag.bit_length() - 1) if mag else 0

    if mag == 0:
        # A tiny inexact value that rounds to zero is still "tiny" (the rounded
        # magnitude is below the smallest normal), so it reports UF as well.
        return sign << (oe + osig), ((1 << 3) | (1 << 4)) if inexact else 0

    normal = res_e >= emin
    overflow = normal and res_e > emax
    tiny = not normal

    if overflow:
        to_inf = (mode in (RNE, RNA)) or (mode == RUP and not sign) \
            or (mode == RDN and sign)
        if to_inf:
            out = (sign << (oe + osig)) | ((6 << (oe - 2)) << (osig - 1))
            flags = (1 << 2) | (1 << 4)
        else:
            # peg to the largest finite magnitude: exp = outInfExp - 1
            out = ((sign << (oe + osig)) | (((6 << (oe - 2)) - 1) << (osig - 1))
                   | ((1 << (osig - 1)) - 1))
            flags = (1 << 2) | (1 << 4)
        return out, flags

    # recoded exponent: value = sig' * 2^(s_exp' - 2^oe - (osig-1))
    t = mag.bit_length() - 1
    sig_sel = mag << (osig - 1 - t)
    s_exp = res_e + (1 << oe)
    out = ((sign << (oe + osig)) | (s_exp << (osig - 1))
           | bits(sig_sel, osig - 1))
    flags = 0
    if tiny and inexact:
        flags |= (1 << 3) | (1 << 4)
    elif inexact:
        flags |= (1 << 4)
    if tiny and not inexact:
        flags = 0
    return out, flags


# ── the six-direction field ───────────────────────────────────────────────
def mode_from_onehot(immu6, fcsr_mode):
    """(legal, direction) of the `immu6` six-direction field (ADR-0050 D2)."""
    if immu6 == 0x20:
        return True, (RNE, RTZ, RDN, RUP)[fcsr_mode]
    if immu6 in ONEHOT:
        return True, ONEHOT[immu6]
    return False, None


# ── conversion oracle (m12-chipyard-012, spec/SimRISC-07 §1) ──────────────
#
# Exact oracles for the three conversion families, derived from the IEEE 754
# definitions and the DADAO flag contract (spec/SimRISC-07 §1.4): from the
# exact value of the operand, round once to the destination, then decide
# saturation / flags.  Nothing here mirrors the RTL: f2i works on the exact
# rational, i2f on the exact integer.
NV, DZ, OF, UF, NX = 1, 2, 4, 8, 16


def _widen_int(value, width, signed):
    """Widen an integer to the 64-bit `rd` width (sign or zero extension)."""
    value &= (1 << width) - 1
    if signed and (value >> (width - 1)) & 1:
        value -= 1 << width
    return value & ((1 << 64) - 1)


def f2i_exact(ew, sw, x, int_width, signed, mode):
    """Exact float -> integer oracle: (64-bit result, rf0[4:0] flags).

    NaN / Inf / a rounded result outside the destination range saturates to
    the largest (positive, including a NaN) or smallest value and raises NV
    only; a finite inexact result raises NX (spec/SimRISC-07 §1.4).
    """
    hi = (1 << (int_width - 1)) - 1 if signed else (1 << int_width) - 1
    lo = -(1 << (int_width - 1)) if signed else 0
    r = raw_from_fn(ew, sw, x)
    if r["is_nan"] or r["is_inf"]:
        # A NaN carries no sign for this purpose (hardfloat / QEMU / gem5 all
        # saturate it to the positive maximum).
        pos = not r["is_nan"] and r["sign"]
        return _widen_int(lo if pos else hi, int_width, signed), NV
    if r["is_zero"]:
        return 0, 0
    mant = r["sig"]
    e2 = r["s_exp"] - (1 << ew) - (sw - 1)
    if e2 >= 0:
        num, den = mant << e2, 1
    else:
        num, den = mant, 1 << (-e2)
    mag, inexact = _round_int(num, den, mode, bool(r["sign"]))
    value = -mag if r["sign"] else mag
    if value < lo:
        return _widen_int(lo, int_width, signed), NV
    if value > hi:
        return _widen_int(hi, int_width, signed), NV
    return _widen_int(value, int_width, signed), (NX if inexact else 0)


def i2f_exact(int_width, oe, osig, value, signed, mode):
    """Exact integer -> float oracle: (recoded output, rf0[4:0] flags).

    The integer magnitude is rounded to `osig` significant bits; a precision
    loss raises NX, an out-of-range result raises OF and returns +-Infinity
    (contract-fp §4).  An integer is never tiny, so UF is unreachable.
    """
    raw_val = value & ((1 << int_width) - 1)
    sign = 1 if (signed and (raw_val >> (int_width - 1)) & 1) else 0
    mag = (1 << int_width) - raw_val if sign else raw_val
    if mag == 0:
        return 0, 0
    k = mag.bit_length() - 1
    drop = k - (osig - 1)
    if drop <= 0:
        q, inexact = mag << (-drop), False
    else:
        q, inexact = _round_int(mag, 1 << drop, mode, bool(sign))
    if q >> osig:                       # rounding carried into a new binade
        q >>= 1
        k += 1
    emax = (1 << (oe - 1)) - 1
    if k > emax:
        # +-Infinity with OF|NX (the overflowed result is inexact by contract)
        return ((sign << (oe + osig)) | ((6 << (oe - 2)) << (osig - 1))), (OF | NX)
    t = q.bit_length() - 1
    sig_sel = q << (osig - 1 - t)
    s_exp = k + (1 << oe)
    out = ((sign << (oe + osig)) | (s_exp << (osig - 1)) | bits(sig_sel, osig - 1))
    return out, (NX if inexact else 0)


def f2f_exact(src_ew, src_sw, dst_ew, dst_sw, x, mode, force_inf_on_overflow):
    """Exact format-conversion oracle: (destination bits, rf0[4:0] flags).

    An sNaN is an invalid (arithmetic) input: NV and the canonical quiet NaN.
    A quiet NaN propagates its payload (spec/SimRISC-07 §1.4).  On overflow
    `fo2ft` returns +-Infinity whatever the direction (spec/SimRISC-07 §1.4,
    contract-fp §2); the widening direction cannot overflow.
    """
    r = raw_from_fn(src_ew, src_sw, x)
    is_sig_nan = r["is_nan"] and not ((r["sig"] >> (src_sw - 2)) & 1)
    out, flags = round_exact(src_ew, src_sw, dst_ew, dst_sw, r, mode,
                             invalid_exc=is_sig_nan)
    if force_inf_on_overflow and (flags & OF):
        out = (r["sign"] << (dst_ew + dst_sw)) | ((6 << (dst_ew - 2)) << (dst_sw - 1))
    return out, flags


# ── arithmetic oracles (m12-chipyard-013, spec/SimRISC-07 §2) ────────────
#
# Every oracle forms the *exact* result (an integer mantissa with a binary
# exponent) and hands it to `round_dyadic`, i.e. the value is rounded once from
# its exact value -- never from an intermediate rounded result.  The special
# cases follow spec/SimRISC-07: `NV` for a signalling NaN input and for the
# invalid operations, a quiet NaN input propagating its payload for add/sub/mul
# (§1.4), the canonical quiet NaN for the fused multiply-add (§2.5), `-0` below
# `+0` for the comparisons and min/max, the canonical quiet NaN for two NaN
# operands of min/max (§2.4), and `NV` from a signalling compare on any
# unordered pair (§4).
def _is_snan(r, sig_width):
    """Signalling NaN: a NaN whose payload's most significant bit is clear."""
    return r["is_nan"] and not ((r["sig"] >> (sig_width - 2)) & 1)


def _exp_all_ones(ew, sw):
    return ((1 << ew) - 1) << (sw - 1)


def _canon_qnan(ew, sw):
    """Canonical quiet NaN: sign 0, payload all zero (IEEE 754-2019 §6.2)."""
    return _exp_all_ones(ew, sw) | (1 << (sw - 2))


def _quieted(r, ew, sw):
    """The NaN `r` as a quiet NaN with its payload kept (spec §1.4)."""
    return _exp_all_ones(ew, sw) | (r["sig"] & ((1 << (sw - 1)) - 1)) \
        | (1 << (sw - 2))


def _inf_bits(sign, ew, sw):
    return (sign << (ew + sw - 1)) | _exp_all_ones(ew, sw)


def _dyadic(r, ew, sw):
    """``(sign, mant, e2)`` of a raw float with ``value = +-mant * 2^e2``."""
    mant = 0 if r["is_zero"] else r["sig"]
    return r["sign"], mant, r["s_exp"] - (1 << ew) - (sw - 1)


def _add_dyadic(x, y):
    """Exact sum of two dyadics, as ``(sign, mant, e2)``."""
    sx, mx, ex = x
    sy, my, ey = y
    e = min(ex, ey)
    v = (-mx if sx else mx) << (ex - e)
    v += (-my if sy else my) << (ey - e)
    if v < 0:
        return 1, -v, e
    return 0, v, e


def _mul_dyadic(x, y):
    sx, mx, ex = x
    sy, my, ey = y
    return sx ^ sy, mx * my, ex + ey


def _sum_or_zero(terms, mode):
    """Add dyadics; an exact zero takes the IEEE 754-2019 §6.3 sign: the common
    sign when every term has it, `-0` under RDN otherwise."""
    if not terms:
        return 0, 0, 0
    acc = terms[0]
    for t in terms[1:]:
        acc = _add_dyadic(acc, t)
    if acc[1] == 0:
        signs = {t[0] for t in terms if t[1] != 0}
        if len(signs) == 0:
            # all terms are zeros: same sign -> that sign, else the RDN rule
            if len({t[0] for t in terms}) == 1:
                return terms[0][0], 0, 0
            return (1 if mode == RDN else 0), 0, 0
        if len(signs) == 1:
            return signs.pop(), 0, 0
        return (1 if mode == RDN else 0), 0, 0
    return acc


def add_exact(ew, sw, a, b, sub, mode):
    """Exact add/sub oracle: ``(IEEE result bits, rf0[4:0] flags)``."""
    ra = raw_from_fn(ew, sw, a)
    rb = raw_from_fn(ew, sw, b)
    sign_b = rb["sign"] ^ (1 if sub else 0)

    if _is_snan(ra, sw) or _is_snan(rb, sw):
        return _canon_qnan(ew, sw), NV
    if ra["is_nan"] or rb["is_nan"]:
        src = ra if ra["is_nan"] else rb
        return _quieted(src, ew, sw), 0
    if ra["is_inf"] or rb["is_inf"]:
        if ra["is_inf"] and rb["is_inf"] and ra["sign"] != sign_b:
            return _canon_qnan(ew, sw), NV
        sign = ra["sign"] if ra["is_inf"] else sign_b
        return _inf_bits(sign, ew, sw), 0

    x = _dyadic(ra, ew, sw)
    y = _dyadic(rb, ew, sw)
    y = (sign_b,) + y[1:]
    sign, mant, e2 = _sum_or_zero([x, y], mode)
    if mant == 0:
        return sign << (ew + sw - 1), 0
    rec, flags = round_dyadic(ew, sw, sign, mant, e2, mode)
    return fn_from_recfn(ew, sw, rec), flags


def mul_exact(ew, sw, a, b, mode):
    """Exact multiply oracle: ``(IEEE result bits, rf0[4:0] flags)``."""
    ra = raw_from_fn(ew, sw, a)
    rb = raw_from_fn(ew, sw, b)
    sign = ra["sign"] ^ rb["sign"]

    if _is_snan(ra, sw) or _is_snan(rb, sw):
        return _canon_qnan(ew, sw), NV
    if ra["is_nan"] or rb["is_nan"]:
        src = ra if ra["is_nan"] else rb
        return _quieted(src, ew, sw), 0
    if (ra["is_inf"] and rb["is_zero"]) or (ra["is_zero"] and rb["is_inf"]):
        return _canon_qnan(ew, sw), NV
    if ra["is_inf"] or rb["is_inf"]:
        return _inf_bits(sign, ew, sw), 0
    if ra["is_zero"] or rb["is_zero"]:
        return sign << (ew + sw - 1), 0

    sign, mant, e2 = _mul_dyadic(_dyadic(ra, ew, sw), _dyadic(rb, ew, sw))
    rec, flags = round_dyadic(ew, sw, sign, mant, e2, mode)
    return fn_from_recfn(ew, sw, rec), flags


def fma_exact(ew, sw, a, b, c, mode):
    """Exact fused multiply-add oracle: ``(IEEE result bits, flags)``.

    `a * b` is formed exactly and added to `c` exactly; the sum is rounded once
    (spec/SimRISC-07 §2.5).  The NaN result is the canonical quiet NaN.
    """
    ra = raw_from_fn(ew, sw, a)
    rb = raw_from_fn(ew, sw, b)
    rc = raw_from_fn(ew, sw, c)
    sign_prod = ra["sign"] ^ rb["sign"]
    # The product is infinite only when both factors are numbers; a NaN
    # multiplicand makes the product NaN even if the other factor is an
    # infinity (spec/SimRISC-07 §2.5: the Inf rule is "Inf x finite non-zero").
    prod_inf = (ra["is_inf"] or rb["is_inf"]) and \
        not (ra["is_nan"] or rb["is_nan"])

    inf_zero = (ra["is_inf"] and rb["is_zero"]) or \
        (ra["is_zero"] and rb["is_inf"])
    inf_diff = prod_inf and rc["is_inf"] and (sign_prod != rc["sign"])

    if _is_snan(ra, sw) or _is_snan(rb, sw) or _is_snan(rc, sw):
        return _canon_qnan(ew, sw), NV
    if inf_zero or inf_diff:
        return _canon_qnan(ew, sw), NV
    if ra["is_nan"] or rb["is_nan"] or rc["is_nan"]:
        return _canon_qnan(ew, sw), 0
    if prod_inf or rc["is_inf"]:
        sign = sign_prod if prod_inf else rc["sign"]
        return _inf_bits(sign, ew, sw), 0

    prod = _mul_dyadic(_dyadic(ra, ew, sw), _dyadic(rb, ew, sw))
    addend = _dyadic(rc, ew, sw)
    sign, mant, e2 = _sum_or_zero([prod, addend], mode)
    if mant == 0:
        return sign << (ew + sw - 1), 0
    rec, flags = round_dyadic(ew, sw, sign, mant, e2, mode)
    return fn_from_recfn(ew, sw, rec), flags


def _order_key(x, ew, sw):
    """Monotone key of an IEEE encoding (``-0`` below ``+0``)."""
    w = ew + sw
    x &= (1 << w) - 1
    sign = (x >> (w - 1)) & 1
    return (~x) & ((1 << w) - 1) if sign else (x | (1 << (w - 1)))


def cmp_exact(ew, sw, a, b, signaling):
    """Compare oracle: ``(64-bit result, rf0[4:0] flags)``.

    Ordered pairs give 1 / 0 / -1; an unordered pair gives a quiet NaN (quiet
    compare) or a signalling NaN (signalling compare), sign bit clear.  `NV`
    follows spec/SimRISC-07 §4: a signalling compare raises it for **any**
    unordered pair, quiet NaN included (IEEE 754-2019 §5.7.1), while a quiet
    compare raises no flag.
    """
    ra = raw_from_fn(ew, sw, a)
    rb = raw_from_fn(ew, sw, b)
    nv = NV if (signaling and (ra["is_nan"] or rb["is_nan"])) else 0
    if ra["is_nan"] or rb["is_nan"]:
        nan = _exp_all_ones(ew, sw) | ((1 << 0) if signaling else (1 << (sw - 2)))
        return nan, nv
    if ra["is_zero"] and rb["is_zero"]:
        return 0, 0                     # every zero encoding compares equal
    ka = _order_key(a, ew, sw)
    kb = _order_key(b, ew, sw)
    if ka > kb:
        return 1, 0
    if ka < kb:
        return (1 << 64) - 1, 0
    return 0, 0


def minmax_exact(ew, sw, a, b, is_max):
    """minimumNumber/maximumNumber oracle: ``(64-bit result, flags)``.

    A single NaN returns the number, two NaNs return the canonical quiet NaN,
    and a signalling NaN input raises `NV` either way (spec §2.4).
    """
    ra = raw_from_fn(ew, sw, a)
    rb = raw_from_fn(ew, sw, b)
    nv = NV if (_is_snan(ra, sw) or _is_snan(rb, sw)) else 0
    if ra["is_nan"] and rb["is_nan"]:
        return _canon_qnan(ew, sw), nv
    if ra["is_nan"]:
        return b & ((1 << (ew + sw)) - 1), nv
    if rb["is_nan"]:
        return a & ((1 << (ew + sw)) - 1), nv
    ka = _order_key(a, ew, sw)
    kb = _order_key(b, ew, sw)
    pick_a = (ka >= kb) if is_max else (ka <= kb)
    return (a if pick_a else b) & ((1 << (ew + sw)) - 1), nv


# ── vector domains used by the self-check and the unit bench ──────────────
def sample_raw(ie, isig, n, rng):
    """Raw floats covering every corner the rounding primitive must handle:
    zero, infinity, quiet/signalling NaN, subnormal, tiny, the largest finite
    values, the overflow boundary and plain random values.  The significand is
    a full `isig`-bit one (hidden bit set, the extra top bit clear), so the two
    low bits fed to the round-to-own-format case are real dropped bits.
    """
    min_norm = (1 << (ie - 1)) + 2
    max_exp = (1 << ie) - 1
    out = []

    def mk(sign, s_exp, sig, kind="normal"):
        sig = bits(sig, isig) | (1 << (isig - 1)) if kind != "special" else \
            bits(sig, isig)
        return dict(is_nan=kind == "nan", is_inf=kind == "inf",
                    is_zero=kind == "zero", sign=sign, s_exp=s_exp, sig=sig)

    for sign in (0, 1):
        out.append(mk(sign, 0, 0, "zero"))
        out.append(mk(sign, 0, 0, "inf"))
        out.append(mk(sign, 0, 1 << (isig - 2), "nan"))          # qNaN
        out.append(mk(sign, 0, 1 << (isig - 2) | 1, "nan"))      # qNaN+payload
        out.append(mk(sign, 0, 1, "nan"))                        # sNaN
        out.append(mk(sign, min_norm, 1 << (isig - 1)))          # 1.0
        out.append(mk(sign, min_norm, (1 << isig) - 1))          # 1.111..
        out.append(mk(sign, min_norm - 1, (1 << isig) - 1))      # max subnormal
        out.append(mk(sign, min_norm - 1, 1 << (isig - 1)))
        out.append(mk(sign, 1, 1 << (isig - 1)))                 # tiny
        out.append(mk(sign, 0, 1))                               # tiny
        out.append(mk(sign, ((3 << (ie - 1)) - 2), (1 << isig) - 1))  # near max
        out.append(mk(sign, ((3 << (ie - 1)) - 3), (1 << isig) - 1))
        out.append(mk(sign, max_exp, 1 << (isig - 1)))           # overflow
    for _ in range(n):
        sign = rng.getrandbits(1)
        kind = rng.random()
        if kind < 0.6:      # normal, any exponent
            s_exp = rng.randrange(min_norm, (3 << (ie - 1)) - 1)
        elif kind < 0.85:   # subnormal / denormalising
            s_exp = rng.randrange(1, min_norm)
        else:               # tiny .. zero, and the overflow region
            s_exp = rng.choice([0, rng.randrange(0, min_norm),
                                (3 << (ie - 1)) - 1, 3 << (ie - 1)])
        out.append(mk(sign, s_exp, rng.getrandbits(isig)))
    return out


def sample_fn(ew, sw, n, rng):
    """Interesting IEEE bit patterns plus random ones."""
    w = ew + sw
    pats = []
    exp_all = (1 << ew) - 1
    for sign in (0, 1):
        pats += [sign << (w - 1),
                 (sign << (w - 1)) | 1,
                 (sign << (w - 1)) | (1 << (sw - 2)),
                 (sign << (w - 1)) | ((1 << (sw - 1)) - 1),
                 (sign << (w - 1)) | ((1 << (sw - 1)) - 2),
                 (sign << (w - 1)) | (1 << (ew + sw - 2)),
                 (sign << (w - 1)) | (exp_all << (sw - 1)),
                 (sign << (w - 1)) | (exp_all << (sw - 1)) | 1,
                 (sign << (w - 1)) | (exp_all << (sw - 1)) | (1 << (sw - 2)),
                 (sign << (w - 1)) | (exp_all << (sw - 1)) | ((1 << (sw - 1)) - 1)]
    for _ in range(n):
        pats.append(rng.getrandbits(w))
    for _ in range(n // 4):   # subnormal / tiny neighbourhood
        e = rng.randrange(0, 6)
        pats.append((rng.getrandbits(1) << (w - 1))
                    | (e << (sw - 1)) | rng.getrandbits(sw - 1))
    for _ in range(n // 4):   # near the largest normal values
        e = exp_all - 1 - rng.randrange(0, 3)
        pats.append((rng.getrandbits(1) << (w - 1))
                    | (e << (sw - 1)) | rng.getrandbits(sw - 1))
    return pats


def _arith_patterns(ew, sw):
    """The operand patterns the arithmetic family must get right: every special
    value, the extremes of the exponent range, the subnormal boundary and the
    exact-cancellation partner of each."""
    w = ew + sw
    exp_all = (1 << ew) - 1
    min_norm = 1 << (sw - 1)          # exponent field of the smallest normal
    pats = []
    for sign in (0, 1):
        s = sign << (w - 1)
        pats += [s,                                  # +-0
                 s | 1,                              # +-smallest subnormal
                 s | (min_norm - 1),                 # +-largest subnormal
                 s | min_norm,                       # +-smallest normal
                 s | min_norm | 1,
                 s | (min_norm | (1 << (sw - 2))),   # +-1.0
                 s | (min_norm | 1),                 # 1 + ulp
                 s | ((exp_all - 1) << (sw - 1)) | ((1 << (sw - 1)) - 1),
                 s | ((exp_all - 1) << (sw - 1)),    # +-largest finite
                 s | (exp_all << (sw - 1)),          # +-inf
                 s | (exp_all << (sw - 1)) | 1,      # sNaN
                 s | (exp_all << (sw - 1)) | (1 << (sw - 2)),  # qNaN
                 s | (exp_all << (sw - 1)) | (1 << (sw - 2)) | 0x3F]
    # the sub/super-normal boundary of both formats
    pats += [min_norm - 1, min_norm, min_norm + 1, 1, 2]
    pats += [((1 << (ew - 1)) << (sw - 1)), ((1 << (ew - 1)) - 1) << (sw - 1)]
    return pats


def sample_pairs(ew, sw, n, rng):
    """``(a, b)`` pairs for add/sub/mul: the structural cases (exact
    cancellation, both zeros of every sign, operands on the same binade, far
    apart exponents) plus random pairs."""
    pats = _arith_patterns(ew, sw)
    w = ew + sw
    mask = (1 << w) - 1
    pairs = []
    for a in pats:
        pairs.append((a, a))                       # equal
        pairs.append((a, a ^ (1 << (w - 1))))      # negated -> cancellation
        pairs.append((a, pats[(pats.index(a) + 3) % len(pats)]))
    one = (1 << (ew - 1)) << (sw - 1) | (1 << (ew - 1))   # 1.0 encoding
    for delta in (0, 1, 2, sw - 1, sw, sw + 1, sw + 3, 2 * sw):
        for _ in range(max(1, n // 16)):
            a = rng.getrandbits(w) & mask
            ea = (a >> (sw - 1)) & ((1 << ew) - 1)
            nb = (a & ((1 << (sw - 1)) - 1)) | (a & (1 << (w - 1)))
            ne = min(max(ea + rng.choice([-delta, delta]), 0), (1 << ew) - 1)
            pairs.append((a, nb | (ne << (sw - 1))))
    for _ in range(n):
        pairs.append((rng.getrandbits(w) & mask, rng.getrandbits(w) & mask))
    # a tiny operand next to a huge one (the far path of the alignment)
    for _ in range(n // 4):
        ea = rng.randrange(1, (1 << ew) - 1)
        eb = max(1, min((1 << ew) - 2, ea + rng.choice([-1, 1]) *
                        rng.randrange(sw, 2 * sw + 6)))
        a = (rng.getrandbits(1) << (w - 1)) | (ea << (sw - 1)) | \
            rng.getrandbits(sw - 1)
        b = (rng.getrandbits(1) << (w - 1)) | (eb << (sw - 1)) | \
            rng.getrandbits(sw - 1)
        pairs.append((a, b))
    _ = one
    return pairs


def sample_fma_triples(ew, sw, n, rng):
    """``(a, b, c)`` triples for the fused multiply-add: the single-rounding
    counterexample of spec/SimRISC-07 §2.5, c chosen as (minus) the rounded or
    the exact product (catastrophic cancellation of the fused sum), overflow and
    underflow of the product, and random triples."""
    w = ew + sw
    mask = (1 << w) - 1
    exp_all = (1 << ew) - 1
    one = ((1 << (ew - 1)) << (sw - 1)) | (1 << (ew - 1))
    triples = []
    # Spec §2.5 counterexample: (1 + ulp)(1 - ulp) - 1 = -ulp^2 for ft.
    a = one + 1 if sw == 24 else one + 1
    b = one - 1 if sw == 24 else one - 1
    triples.append((a, b, (1 << (w - 1)) | one))         # -1
    # A NaN multiplicand makes the product NaN even next to an infinity, so
    # `qNaN x Inf + (-Inf)` is a propagation (no NV) while `Inf x 1 + (-Inf)`
    # is the invalid Inf + (-Inf) (spec/SimRISC-07 §2.5).
    qnan = (exp_all << (sw - 1)) | (1 << (sw - 2))
    inf = exp_all << (sw - 1)
    triples += [(qnan, inf, (1 << (w - 1)) | inf),
                (qnan, inf, inf),
                (inf, one, (1 << (w - 1)) | inf),
                (inf, one, inf),
                (0, inf, qnan)]
    # exact cancellation of the fused sum: c = -(a*b) when that is representable
    for _ in range(n // 4):
        ea = rng.randrange(1, exp_all - 1)
        a = (ea << (sw - 1)) | (1 << (sw - 1)) | rng.getrandbits(sw - 2)
        b = one
        triples.append((a, b, ((1 << (w - 1)) | (ea << (sw - 1)) |
                               (1 << (sw - 1)) | (a & ((1 << (sw - 2)) - 1)))))
    # product at the extremes with an addend just below / above it
    for ea, eb in ((exp_all - 2, 2), (2, exp_all - 2), (exp_all - 2, exp_all - 2),
                   (1, 1), (1, 2), (2, 1)):
        a = (ea << (sw - 1)) | (1 << (sw - 1)) | ((1 << (sw - 1)) - 1)
        b = (eb << (sw - 1)) | (1 << (sw - 1)) | ((1 << (sw - 1)) - 1)
        for c in (0, one, (1 << (w - 1)) | one, 1, (1 << (w - 1)) | 1,
                  (exp_all - 1) << (sw - 1)):
            triples.append((a, b, c))
    for a in _arith_patterns(ew, sw):
        triples.append((a, one, one))
        triples.append((a, one, 0))
        triples.append((a, 0, one))
        triples.append((a, a, a))
    for _ in range(n):
        triples.append((rng.getrandbits(w) & mask, rng.getrandbits(w) & mask,
                        rng.getrandbits(w) & mask))
    # random triples whose product and addend are within a few binades (where
    # the fused sum can cancel)
    for _ in range(n):
        ea = rng.randrange(1, exp_all - 1)
        eb = rng.randrange(1, exp_all - 1)
        ec = max(1, min(exp_all - 1, ea + eb - (1 << (ew - 1)) +
                        rng.randrange(-4, 5)))
        triples.append(((rng.getrandbits(1) << (w - 1)) | (ea << (sw - 1)) |
                        rng.getrandbits(sw - 1),
                        (rng.getrandbits(1) << (w - 1)) | (eb << (sw - 1)) |
                        rng.getrandbits(sw - 1),
                        (rng.getrandbits(1) << (w - 1)) | (ec << (sw - 1)) |
                        rng.getrandbits(sw - 1)))
    return triples


def sample_ints(int_width, n, rng):
    """Integer patterns covering the conversion boundaries: 0, +-1, the
    largest/smallest values of the width, the powers of two around the
    significand width of both formats (24 and 53 bits) and their neighbours,
    plus random patterns.
    """
    mask = (1 << int_width) - 1
    pats = [0, 1, 2, 3, 1 << (int_width - 1), (1 << (int_width - 1)) - 1,
            (1 << (int_width - 1)) + 1, mask, mask - 1, mask >> 1]
    for sh in (2, 8, 16, 22, 23, 24, 25, 31, 32, 33, 52, 53, 54, 62, 63):
        if sh < int_width:
            for base in (1 << sh, (1 << sh) - 1, (1 << sh) + 1):
                pats += [base & mask, (-base) & mask]
    for _ in range(n):
        pats.append(rng.getrandbits(int_width))
    return pats


def recfn_value(x, ew, sw):
    """The IEEE value a recoded word denotes (NaN payloads compare as a bare
    NaN, and every zero encoding compares equal)."""
    r = raw_from_recfn(ew, sw, x)
    if r["is_nan"]:
        return "nan"
    return fn_from_recfn(ew, sw, x)


def raw_pack(r, ie, isig):
    """Pack a raw float into the 128-bit bench word: sign, isZero, isInf,
    isNaN, sExp (ie+2 bits, two's complement), sig (isig+1 bits)."""
    v = r["sign"]
    v = (v << 1) | int(r["is_zero"])
    v = (v << 1) | int(r["is_inf"])
    v = (v << 1) | int(r["is_nan"])
    v = (v << (ie + 2)) | bits(r["s_exp"], ie + 2)
    v = (v << (isig + 1)) | bits(r["sig"], isig + 1)
    return v


def raw_unpack(v, ie, isig):
    sig = bits(v, isig + 1)
    v >>= isig + 1
    s_exp = bits(v, ie + 2)
    v >>= ie + 2
    is_nan = v & 1
    v >>= 1
    is_inf = v & 1
    v >>= 1
    is_zero = v & 1
    v >>= 1
    sign = v & 1
    return dict(is_nan=bool(is_nan), is_inf=bool(is_inf),
                is_zero=bool(is_zero), sign=sign, s_exp=s_exp, sig=sig)


def selfcheck(n=4000, seed=20260111):
    rng = random.Random(seed)
    bad = 0
    checked = 0
    cases = [
        ("ft round", FT, (8, 26), FT),
        ("fo round", FO, (11, 55), FO),
        ("fo2ft", FO, (11, 55), FT),
        ("ft2fo", FT, (8, 26), FO),
    ]
    for name, (ie, isig), raw_fmt, (oe, osig) in cases:
        for r in sample_raw(ie, isig, n, rng):
            for mode in (RNE, RTZ, RDN, RUP, RNA):
                a = round_bits(ie, isig, oe, osig, r, mode)
                b = round_exact(ie, isig, oe, osig, r, mode)
                checked += 1
                if recfn_value(a[0], oe, osig) != recfn_value(b[0], oe, osig) \
                        or a[1] != b[1]:
                    bad += 1
                    if bad <= 10:
                        print(f"  [{name} {MODE_NAMES[mode]}] "
                              f"in={raw_pack(r, ie, isig):x} "
                              f"bits={a[0]:x}/{a[1]} exact={b[0]:x}/{b[1]}")
    print(f"selfcheck: {checked} (input, mode) pairs, {bad} mismatches")
    return 0 if bad == 0 else 1


def main(argv):
    if len(argv) > 1 and argv[1] == "selfcheck":
        n = int(argv[2]) if len(argv) > 2 else 4000
        return selfcheck(n)
    if len(argv) > 1 and argv[1] == "roundtrip":
        bad = 0
        rng = random.Random(7)
        for (ew, sw) in (FT, FO):
            for x in sample_fn(ew, sw, 2000, rng):
                if fn_from_recfn(ew, sw, recfn_from_fn(ew, sw, x)) != x:
                    bad += 1
        print(f"roundtrip mismatches: {bad}")
        return 0 if bad == 0 else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
