"""Integer/rational IEEE binary32/binary64 reference primitives.

The implementation uses exact integer ratios for finite arithmetic and never
uses host floating-point results as architectural answers. Semantics follow
the repository FP contract; explicitly open contract cases raise FPGap.
"""
from fractions import Fraction
from math import isqrt


class FPGap(Exception):
    pass


class Format:
    def __init__(self, precision, exponent_bits, bias):
        self.p = precision
        self.eb = exponent_bits
        self.bias = bias
        self.fbits = precision - 1
        self.emax = bias
        self.emin = 1 - bias
        self.sign_shift = self.fbits + exponent_bits
        self.exp_mask = (1 << exponent_bits) - 1
        self.frac_mask = (1 << self.fbits) - 1
        self.width = self.sign_shift + 1
        self.mask = (1 << self.width) - 1
        self.qbit = 1 << (self.fbits - 1)
        self.canonical_qnan = (self.exp_mask << self.fbits) | self.qbit
        self.canonical_snan = (self.exp_mask << self.fbits) | 1
        self.inf = self.exp_mask << self.fbits


F32 = Format(24, 8, 127)
F64 = Format(53, 11, 1023)
NV, DZ, OF, UF, NX = 1, 2, 4, 8, 16


def decode(bits, fmt):
    bits &= fmt.mask
    sign = bits >> fmt.sign_shift
    exp = (bits >> fmt.fbits) & fmt.exp_mask
    frac = bits & fmt.frac_mask
    if exp == fmt.exp_mask:
        if not frac:
            return sign, 'inf', None, frac
        return sign, 'nan', None, frac
    if exp == 0:
        if not frac:
            return sign, 'zero', Fraction(0), 0
        val = Fraction(frac, 1) * Fraction(2) ** (fmt.emin - fmt.fbits)
    else:
        val = Fraction((1 << fmt.fbits) | frac, 1) * Fraction(2) ** (exp - fmt.bias - fmt.fbits)
    return sign, 'finite', (-val if sign else val), frac


def _floor_log2(x):
    n, d = x.numerator, x.denominator
    e = n.bit_length() - d.bit_length()
    if e >= 0:
        if n < (d << e):
            e -= 1
    elif (n << -e) < d:
        e -= 1
    return e


def _round_integer(n, d, mode, sign):
    q, rem = divmod(n, d)
    if not rem:
        return q, False
    inc = False
    if mode == 0:  # RNE
        inc = 2 * rem > d or (2 * rem == d and (q & 1) != 0)
    elif mode == 2:  # RDN
        inc = bool(sign)
    elif mode == 3:  # RUP
        inc = not sign
    return q + int(inc), True


def _round_scaled(value, shift, mode, sign):
    n, d = value.numerator, value.denominator
    if shift >= 0:
        n <<= shift
    else:
        d <<= -shift
    return _round_integer(n, d, mode, sign)


def _overflow_to_inf(sign, mode):
    return mode == 0 or (mode == 3 and sign == 0) or (mode == 2 and sign == 1)


def encode_fraction(value, fmt, mode):
    if value == 0:
        return 0, 0
    sign = int(value < 0)
    x = abs(value)
    e = _floor_log2(x)
    if e > fmt.emax:
        if _overflow_to_inf(sign, mode):
            return (sign << fmt.sign_shift) | fmt.inf, OF | NX
        max_finite = (fmt.exp_mask - 1) << fmt.fbits | fmt.frac_mask
        return (sign << fmt.sign_shift) | max_finite, OF | NX
    if e >= fmt.emin:
        sig, inexact = _round_scaled(x, fmt.fbits - e, mode, sign)
        if sig == (1 << fmt.p):
            sig >>= 1
            e += 1
        if e > fmt.emax:
            if _overflow_to_inf(sign, mode):
                return (sign << fmt.sign_shift) | fmt.inf, OF | NX
            max_finite = (fmt.exp_mask - 1) << fmt.fbits | fmt.frac_mask
            return (sign << fmt.sign_shift) | max_finite, OF | NX
        exp = e + fmt.bias
        bits = (sign << fmt.sign_shift) | (exp << fmt.fbits) | (sig & fmt.frac_mask)
    else:
        sig, inexact = _round_scaled(x, fmt.fbits - fmt.emin, mode, sign)
        if sig >= (1 << fmt.fbits):
            bits = (sign << fmt.sign_shift) | (1 << fmt.fbits)
        else:
            bits = (sign << fmt.sign_shift) | sig
    flags = NX if inexact else 0
    # Tininess-after-rounding: only an inexact subnormal/zero result underflows.
    if inexact and (bits >> fmt.fbits) & fmt.exp_mask == 0:
        flags |= UF
    return bits, flags


def nan_result(bits, fmt):
    sign, kind, _, payload = decode(bits, fmt)
    if kind != 'nan':
        return fmt.canonical_qnan, NV
    if not payload & fmt.qbit:
        return (sign << fmt.sign_shift) | fmt.inf | (payload | fmt.qbit), NV
    return bits & fmt.mask, 0


def _nan_inputs(a, b, fmt):
    for x in (a, b):
        if x is not None and decode(x, fmt)[1] == 'nan':
            out, flags = nan_result(x, fmt)
            return out, flags
    return None


def _pack_special(sign, kind, fmt, payload=None):
    if kind == 'inf':
        return (sign << fmt.sign_shift) | fmt.inf
    if kind == 'zero':
        return sign << fmt.sign_shift
    return (sign << fmt.sign_shift) | fmt.inf | (fmt.canonical_qnan & fmt.frac_mask if payload is None else payload | fmt.qbit)


def arithmetic(op, a_bits, b_bits, fmt, mode):
    a = decode(a_bits, fmt)
    b = decode(b_bits, fmt)
    nan = _nan_inputs(a_bits, b_bits, fmt)
    if nan:
        return nan
    sa, ka, va, _ = a
    sb, kb, vb, _ = b
    if op in ('add', 'sub'):
        original_ka, original_kb = ka, kb
        original_sa, original_sb = sa, sb
        if op == 'sub':
            sb ^= 1
            if kb == 'finite':
                vb = -vb
        if ka == 'inf' and kb == 'inf' and sa != sb:
            return fmt.canonical_qnan, NV
        if ka == 'inf': return _pack_special(sa, 'inf', fmt), 0
        if kb == 'inf': return _pack_special(sb, 'inf', fmt), 0
        result = va + vb
        if result == 0:
            same_signed_zeros = original_ka == original_kb == 'zero' and original_sa == (original_sb ^ int(op == 'sub'))
            zero_sign = original_sa if same_signed_zeros else int(mode == 2)
            return _pack_special(zero_sign, 'zero', fmt), 0
    elif op == 'mul':
        if (ka == 'inf' and kb == 'zero') or (kb == 'inf' and ka == 'zero'):
            return fmt.canonical_qnan, NV
        sign = sa ^ sb
        if ka == 'inf' or kb == 'inf': return _pack_special(sign, 'inf', fmt), 0
        if ka == 'zero' or kb == 'zero': return _pack_special(sign, 'zero', fmt), 0
        result = va * vb
    elif op == 'div':
        sign = sa ^ sb
        if (ka == 'zero' and kb == 'zero') or (ka == 'inf' and kb == 'inf'):
            return fmt.canonical_qnan, NV
        if ka == 'inf' or kb == 'zero':
            return _pack_special(sign, 'inf', fmt), DZ if kb == 'zero' and ka != 'inf' else 0
        if ka == 'zero' or kb == 'inf': return _pack_special(sign, 'zero', fmt), 0
        result = va / vb
    elif op == 'rem':
        if ka == 'inf' or kb == 'zero': return fmt.canonical_qnan, NV
        if kb == 'inf' or ka == 'zero': return a_bits & fmt.mask, 0
        quotient = va / vb
        qabs = abs(quotient)
        q, rem = divmod(qabs.numerator, qabs.denominator)
        if 2 * rem > qabs.denominator or (2 * rem == qabs.denominator and q & 1):
            q += 1
        if quotient < 0: q = -q
        result = va - q * vb
        if result == 0: return _pack_special(sa, 'zero', fmt), 0
    elif op == 'scalb':
        if kb == 'nan' or ka == 'nan':
            return nan_result(a_bits if ka == 'nan' else b_bits, fmt)
        if kb not in ('finite', 'zero') or (kb == 'finite' and vb.denominator != 1):
            raise FPGap('scaleB exponent operand is not a finite integer-valued float')
        n = 0 if kb == 'zero' else vb.numerator
        if ka == 'inf' or ka == 'zero': return a_bits & fmt.mask, 0
        if abs(n) > 20000:
            sign = sa
            if n > 0:
                if _overflow_to_inf(sign, mode):
                    return _pack_special(sign, 'inf', fmt), OF | NX
                max_finite = ((fmt.exp_mask - 1) << fmt.fbits) | fmt.frac_mask
                return (sign << fmt.sign_shift) | max_finite, OF | NX
            tiny = ((mode == 3 and sign == 0) or (mode == 2 and sign == 1))
            return (sign << fmt.sign_shift) | int(tiny), UF | NX
        result = va * (Fraction(1 << n) if n >= 0 else Fraction(1, 1 << -n))
    else:
        raise AssertionError(op)
    bits, flags = encode_fraction(result, fmt, mode)
    return bits, flags


def sqrt(bits, fmt, mode):
    sign, kind, value, payload = decode(bits, fmt)
    if kind == 'nan': return nan_result(bits, fmt)
    if kind == 'inf':
        return (fmt.canonical_qnan, NV) if sign else (bits & fmt.mask, 0)
    if kind == 'zero':
        if sign:
            raise FPGap('rootn(-0, 2) is unspecified by SimRISC-07')
        return bits & fmt.mask, 0
    if sign: return fmt.canonical_qnan, NV
    e = _floor_log2(value) // 2
    shift = fmt.fbits - e
    n, d = value.numerator, value.denominator
    if shift >= 0: n <<= 2 * shift
    else: d <<= -2 * shift
    q = isqrt(n // d)
    exact = q * q * d == n
    if not exact:
        if mode == 0:
            cmp = 4 * n - d * (2 * q + 1) ** 2
            if cmp > 0 or (cmp == 0 and q & 1): q += 1
        elif mode == 3:
            q += 1
    if q >= 1 << fmt.p:
        q >>= 1
        e += 1
    out = ((e + fmt.bias) << fmt.fbits) | (q & fmt.frac_mask)
    inexact = not exact
    return out, NX if inexact else 0


def convert_float(bits, src, dst, mode):
    sign, kind, value, payload = decode(bits, src)
    if kind == 'nan':
        out, flags = nan_result(bits, src)
        dst_payload = payload >> max(0, src.fbits - dst.fbits) if src.fbits >= dst.fbits else payload << (dst.fbits - src.fbits)
        return (sign << dst.sign_shift) | dst.inf | (dst_payload & dst.frac_mask) | dst.qbit, flags
    if kind == 'inf': return _pack_special(sign, 'inf', dst), 0
    if kind == 'zero': return _pack_special(sign, 'zero', dst), 0
    out, flags = encode_fraction(value, dst, mode)
    return out, flags


def convert_int(value, dst, mode):
    return encode_fraction(Fraction(value), dst, mode)


def convert_to_int(bits, src, width, signed, mode):
    sign, kind, value, _ = decode(bits, src)
    lo = -(1 << (width - 1)) if signed else 0
    hi = (1 << (width - (1 if signed else 0))) - 1
    if kind in ('nan', 'inf'):
        return (lo if sign and signed else hi), NV
    x = abs(value)
    q, rem = divmod(x.numerator, x.denominator)
    if mode == 0 and (2 * rem > x.denominator or (2 * rem == x.denominator and q & 1)): q += 1
    elif mode == 2 and sign and rem: q += 1
    elif mode == 3 and not sign and rem: q += 1
    result = -q if sign else q
    if result < lo: return lo, NV
    if result > hi: return hi, NV
    # Contract does not settle whether an inexact f2i sets NX.
    if rem: raise FPGap('convert_f2i precision-loss NX behavior is unspecified')
    return result & ((1 << width) - 1), 0


def classify(bits, fmt):
    sign, kind, value, payload = decode(bits, fmt)
    if kind == 'inf': idx = 0 if sign else 7
    elif kind == 'zero': idx = 3 if sign else 4
    elif kind == 'nan': idx = 8 if not payload & fmt.qbit else 9
    elif value < 0:
        idx = 1 if ((bits >> fmt.fbits) & fmt.exp_mask) else 2
    else:
        idx = 6 if ((bits >> fmt.fbits) & fmt.exp_mask) else 5
    return 1 << idx


def _nan_flags(bits, fmt):
    """Return (is_nan, is_signaling) for one operand bit pattern."""
    _, kind, _, payload = decode(bits, fmt)
    if kind != 'nan':
        return False, False
    return True, not bool(payload & fmt.qbit)


def minmax(op, a_bits, b_bits, fmt):
    """IEEE 754-2019 §9.6 minimumNumber/maximumNumber (contract-fp §19).

    ``op`` is ``'min'`` or ``'max'``.  Single NaN returns the number; two NaNs
    return the canonical quiet NaN.  sNaN input raises NV even when the result
    is the other (numeric) operand.  ``−0 < +0`` is honoured.
    """
    a = decode(a_bits, fmt)
    b = decode(b_bits, fmt)
    a_nan, a_snan = _nan_flags(a_bits, fmt)
    b_nan, b_snan = _nan_flags(b_bits, fmt)
    flags = NV if (a_snan or b_snan) else 0
    if a_nan and b_nan:
        return fmt.canonical_qnan, flags
    if a_nan:
        return b_bits & fmt.mask, flags
    if b_nan:
        return a_bits & fmt.mask, flags

    sa, ka, va, _ = a
    sb, kb, vb, _ = b
    if ka == 'zero' and kb == 'zero':
        less, equal = bool(sa and not sb), sa == sb
    elif ka == 'inf' and kb == 'inf':
        less, equal = bool(sa and not sb), sa == sb
    elif ka == 'inf':
        less, equal = bool(sa), False              # -Inf < finite < +Inf
    elif kb == 'inf':
        less, equal = not bool(sb), False
    else:
        less, equal = va < vb, va == vb
    if equal:
        return a_bits & fmt.mask, flags
    take_a = less if op == 'min' else not less
    return (a_bits if take_a else b_bits) & fmt.mask, flags


_ROUND_SELECT = {0x01: 'rne', 0x02: 'rna', 0x04: 'rtz',
                 0x08: 'rup', 0x10: 'rdn', 0x20: 'dyn'}
_DYN_ROUND = {0: 'rne', 1: 'rtz', 2: 'rdn', 3: 'rup'}


def round_to_integral(bits, fmt, select, mode):
    """IEEE 754-2019 §5.3.1 roundToIntegral (contract-fp §18).

    ``select`` is the one-hot immu6 selector; only ``0x20`` reads the dynamic
    rounding mode and only ``0x20`` may set NX (and only when the value
    changes).  The sign of a zero result follows the input.
    """
    sign, kind, value, payload = decode(bits, fmt)
    if kind == 'nan':
        flags = NV if not payload & fmt.qbit else 0
        return fmt.canonical_qnan, flags
    if kind in ('inf', 'zero'):
        return bits & fmt.mask, 0
    if select not in _ROUND_SELECT:
        raise FPGap('roundToIntegral selector is not one-hot')
    direction = _ROUND_SELECT[select]
    if direction == 'dyn':
        direction = _DYN_ROUND[mode]
    if abs(value) >= 1 << fmt.p:
        return bits & fmt.mask, 0                 # already an integer
    n, d = abs(value).numerator, abs(value).denominator
    q, rem = divmod(n, d)
    inc = False
    if rem:
        if direction == 'rne':
            inc = 2 * rem > d or (2 * rem == d and (q & 1) != 0)
        elif direction == 'rna':
            inc = 2 * rem >= d
        elif direction == 'rup':
            inc = not sign
        elif direction == 'rdn':
            inc = bool(sign)
    magnitude = q + int(inc)
    flags = NX if (select == 0x20 and rem) else 0
    if magnitude == 0:
        return sign << fmt.sign_shift, flags
    out, _ = encode_fraction(Fraction(-magnitude if sign else magnitude), fmt, 0)
    return out, flags


def fma(a_bits, b_bits, c_bits, fmt, mode):
    """IEEE 754-2019 fusedMultiplyAdd (contract-fp §20).

    The exact product is added to the addend and rounded once.  Invalid
    ``0 × ±Inf`` takes precedence over qNaN propagation for NV.
    """
    a = decode(a_bits, fmt)
    b = decode(b_bits, fmt)
    c = decode(c_bits, fmt)
    snan = NV if any(x[1] == 'nan' and not x[3] & fmt.qbit for x in (a, b, c)) else 0
    ka, kb, kc = a[1], b[1], c[1]
    invalid = (ka == 'zero' and kb == 'inf') or (ka == 'inf' and kb == 'zero')
    if invalid or 'nan' in (ka, kb, kc):
        return fmt.canonical_qnan, (NV if (invalid or snan) else 0)

    prod_sign = a[0] ^ b[0]
    if ka == 'inf' or kb == 'inf':
        if kc == 'inf' and c[0] != prod_sign:
            return fmt.canonical_qnan, NV
        return _pack_special(prod_sign, 'inf', fmt), 0
    prod = a[2] * b[2] if ka != 'zero' and kb != 'zero' else Fraction(0)
    if kc == 'inf':
        return c_bits & fmt.mask, 0
    cval = c[2] if kc == 'finite' else Fraction(0)
    exact = prod + cval
    if exact == 0:
        prod_zero, c_zero = (ka == 'zero' or kb == 'zero'), kc == 'zero'
        zero_sign = (prod_sign if prod_zero and c_zero and prod_sign == c[0]
                     else int(mode == 2))
        return _pack_special(zero_sign, 'zero', fmt), 0
    return encode_fraction(exact, fmt, mode)
