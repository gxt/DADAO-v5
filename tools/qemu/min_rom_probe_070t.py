#!/usr/bin/env python3
"""Min ROM probe for QEMU-070t: ftfma/fofma (fused multiply-add).

Spec sources (expectations derived from these, never from QEMU):
  - spec/SimRISC-07 §2.5 融合乘加（fusedMultiplyAdd）
  - .tao/contracts/contract-fp.md §20 `fma`
  - spec/SimRISC-00 §浮点状态寄存器 (rf0[33:32] mode, rf0[4:0] flags)
  - contracts/opcodes.yaml (encoding: op 0x5E / 0x5F, rrrr = ha/hb/hc/hd)

Independent oracle: every expected value is computed here with exact rational
arithmetic (`fractions.Fraction`) that models fusedMultiplyAdd(a,b,c) as
"exact a*b + c, then ONE rounding".  Nothing is taken from QEMU/softfloat and
no host floating-point arithmetic is used for expectations.  The two-step
oracle (round(a*b) then add c) is implemented separately and used to prove the
single-rounding discriminators really differ.

Case model (every assertion has a reachable FAIL path):
  * GEN  16 (a,b,c) triples x 2 formats: mixed signs/magnitudes;
  * FUS  single-rounding discriminators ft/fo (spec's 0xA8800000 example);
  * NAN  qNaN/sNaN in each operand position, double NaN, payload qNaN,
         0×Inf + qNaN (NV must still be raised);
  * ZERO ±0 sign rules (RDN ⇒ -0), same-sign zeros, zero product + c;
  * INF  Inf product with finite/same-signed/opposite-signed addend, Inf×Inf,
         Inf + qNaN;
  * BND  overflow (OF+NX), exact subnormal, inexact subnormal (UF+NX),
         subnormal operand;
  * MODE 0.75 ulp and 0.5 ulp cases x RNE/RTZ/RDN/RUP x 2 formats;
  * ALI  destination aliases each of the three sources (read-before-write);
  * RF0  rf0 as a source reads the FCSR qNaN;
  * IL   destination rf0 ⇒ ILLI.
Every value case also asserts rf0[4:0] flags and that rf0[33:32] is preserved.

Exit codes: ADR-0004 D5.8 (PASS=0x00, ILLI=0x88).
Usage: min_rom_probe_070t.py [--selftest|--oracle]
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
from fractions import Fraction

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths  # noqa: E402


def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d


QEMU = ".work/build/qemu/qemu-system-dadao"

# FCSR reset value (target/dadao/cpu.h::DADAO_RESET_RF0, SimRISC-00)
RESET0 = 0x7FF800007FC00000

PASS_EXIT = 0x00
ILLI_EXIT = 0x88

# rf0[4:0] exception bits (SimRISC-00 table / softfloat enum)
FLAG_NV = 0x01
FLAG_OF = 0x04
FLAG_UF = 0x08
FLAG_NX = 0x10

# ── Instruction encoding (op / ha from contracts/opcodes.yaml) ─────────

ILLI = 0x47801000                 # fence fm=1 -> ILLI
SWYM = 0x47880000                 # swym (padding)


def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) |
                       (hc << 6) | (hd & 0x3F))


def encode_rrrr(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) |
                       (hc << 6) | (hd & 0x3F))


def encode_riii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))


def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) |
                       (mid6 << 6) | lo6)


def encode_rrii(op, ha, hb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) |
                       (hc << 6) | hd)


# M1 integer instructions, used only for setup / assertion (trusted)
def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)


def or_w_rd(rd, wp, immu16):
    return encode_rwii(0x48, rd, wp, immu16)


def set_zw_rb(rb, wp, immu16):
    return encode_rwii(0x4E, rb, wp, immu16)


def or_w_rb(rb, wp, immu16):
    return encode_rwii(0x4A, rb, wp, immu16)


def st_o_rd(rdha, rbhb, imms12):
    return encode_rrii(0x21, rdha, rbhb, imms12)


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


def rd2rf(rfhb, rdhc, hd):
    return encode_orri(0x40, 0x3D, rfhb, rdhc, hd)


# ── Instructions under test ────────────────────────────────────────────

def ftfma(ha, hb, hc, hd):
    return encode_rrrr(0x5E, ha, hb, hc, hd)


def fofma(ha, hb, hc, hd):
    return encode_rrrr(0x5F, ha, hb, hc, hd)


# ── Setup helpers ──────────────────────────────────────────────────────

def load_imm64_rd(rd, val):
    """Build an arbitrary 64-bit value in rd (trusted M1 set.zw + or.w)."""
    insns = [set_zw_rd(rd, val & 0xFFFF)]
    for wp in range(1, 4):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            insns.append(or_w_rd(rd, wp, w))
    return insns


def set_rf(rf, val):
    """Load rf[rf] = val (uses rd31 as scratch; rd2rf writes are trusted)."""
    return load_imm64_rd(31, val) + [rd2rf(rf, 31, 1)]


def set_fcsr_mode(mode):
    """Write rf0[33:32] = mode (rf0 write mask also clears flags)."""
    assert mode in MODE_NAMES
    return set_rf(0, mode << 32)


# ── Semihosting SYS_EXIT (ADR-0020 D8) ─────────────────────────────────

SEMI_BLOCK = 0xFC00_00FF_F000
SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026


def trap_ciii(cfxha, immu18):
    return encode_riii(0x7F, cfxha, immu18 & 0x3FFFF)


def semi_exit(code_rd):
    return ([set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),
             or_w_rb(16, 0, 0xF000), or_w_rb(16, 2, 0xFC00)] +
            load_imm64_rd(8, ADP_STOPPED_APPLICATION_EXIT) +
            [st_o_rd(8, 16, 0)] +
            [st_o_rd(code_rd, 16, 8)] +
            load_imm64_rd(16, 0x18) +
            [trap_ciii(0, SEMIHOST_TAG)])


# ── ROM assembly ───────────────────────────────────────────────────────

TRAMPOLINE = [
    set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),
    set_zw_rb(17, 2, 0xFC00),
    encode_rwii(0x4C, 40, 0, 0x0001),          # rd40 = 1 (TB-split flag)
]


def build_rom(test_insns):
    rom = b''.join(TRAMPOLINE) + b''.join(test_insns) + struct.pack('>I', ILLI)
    while len(rom) < 64:
        rom += struct.pack('>I', SWYM)
    return rom


def build_fault_rom(test_insns):
    """If the instruction under test does NOT fault, exit 0 != ILLI (reachable
    FAIL); appending ILLI would mask a missing legality check."""
    return (b''.join(TRAMPOLINE) + b''.join(test_insns) +
            b''.join([set_zw_rd(18, 0)] + semi_exit(18)))


# ── QEMU execution ─────────────────────────────────────────────────────

def run_dcpu(rom_data, timeout=10):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(b'\x00' * 16)
        kp = f.name
    lp = rp + '.cpu.log'
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp,
             '-semihosting-config', 'enable=on,target=native',
             '-d', 'cpu', '-D', lp],
            capture_output=True, timeout=timeout, text=True)
        with open(lp) as lf:
            return r.returncode, lf.read()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rp)
        os.unlink(kp)
        if os.path.exists(lp):
            os.unlink(lp)


def run_plain(rom_data, timeout=10):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(b'\x00' * 16)
        kp = f.name
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp,
             '-semihosting-config', 'enable=on,target=native'],
            capture_output=True, timeout=timeout, text=True)
        return r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rp)
        os.unlink(kp)


def last_reg(log_text, bank, idx):
    pat = re.compile(r'%s\[%02d\]:\s*([0-9a-fA-F]{16})' % (bank, idx))
    m = None
    for mm in pat.finditer(log_text):
        m = mm
    return int(m.group(1), 16) if m else None


# ══════════════════════════════════════════════════════════════════════
#  Independent oracle: exact fusedMultiplyAdd, one rounding
# ══════════════════════════════════════════════════════════════════════

FT = {"signpos": 31, "fracbits": 23, "expbits": 8, "bias": 127}
FO = {"signpos": 63, "fracbits": 52, "expbits": 11, "bias": 1023}
for _f in (FT, FO):
    _f["expall"] = (1 << _f["expbits"]) - 1
    _f["emax"] = _f["expall"] - 1 - _f["bias"]
    _f["emin"] = 1 - _f["bias"]
    _f["prec"] = _f["fracbits"] + 1

MODE_NAMES = {0: "RNE", 1: "RTZ", 2: "RDN", 3: "RUP"}
QNAN = {id(FT): 0x7FC00000, id(FO): 0x7FF8000000000000}


def signbit(bits, fmt):
    return (bits >> fmt["signpos"]) & 1


def parse(bits, fmt):
    sign = (bits >> fmt["signpos"]) & 1
    exp = (bits >> fmt["fracbits"]) & fmt["expall"]
    man = bits & ((1 << fmt["fracbits"]) - 1)
    if exp == fmt["expall"]:
        if man == 0:
            kind = "inf"
        else:
            kind = "qnan" if (man >> (fmt["fracbits"] - 1)) & 1 else "snan"
    elif exp == 0:
        kind = "zero" if man == 0 else "subnormal"
    else:
        kind = "normal"
    return sign, exp, man, kind


def exact_value(bits, fmt):
    """Exact value as Fraction for finite inputs; None for Inf/NaN."""
    sign, exp, man, kind = parse(bits, fmt)
    if kind in ("inf", "qnan", "snan"):
        return None
    if kind == "zero":
        return Fraction(0)
    if kind == "subnormal":
        v = Fraction(man, 1 << fmt["fracbits"]) * \
            Fraction(2) ** (1 - fmt["bias"])
    else:
        v = (Fraction(man, 1 << fmt["fracbits"]) + 1) * \
            Fraction(2) ** (exp - fmt["bias"])
    return -v if sign else v


def qnan_bits(fmt):
    return QNAN[id(fmt)]


def floor_log2(v):
    """floor(log2(v)) for a positive Fraction, exactly."""
    assert v > 0
    e = v.numerator.bit_length() - v.denominator.bit_length()
    if v < Fraction(2) ** e:
        e -= 1
    assert Fraction(2) ** e <= v < Fraction(2) ** (e + 1)
    return e


def round_quantum(av, mode, sign):
    """Round av >= 0 to an integer.

    Directed modes are applied on the signed value: RUP = toward +inf,
    RDN = toward -inf; therefore the absolute value rounds up for RDN when
    sign == 1 and for RUP when sign == 0.
    Returns (integer, inexact).
    """
    fl = av.numerator // av.denominator
    inexact = av.denominator != 1
    if mode == "RNE":
        rem = av - fl
        if rem > Fraction(1, 2):
            n = fl + 1
        elif rem < Fraction(1, 2):
            n = fl
        else:
            n = fl if fl % 2 == 0 else fl + 1
    elif mode == "RTZ":
        n = fl
    elif mode == "RUP":
        n = fl + 1 if (inexact and sign == 0) else fl
    elif mode == "RDN":
        n = fl + 1 if (inexact and sign == 1) else fl
    else:
        raise AssertionError(mode)
    return n, inexact


def overflow_bits(sign, fmt, mode):
    inf = (sign << fmt["signpos"]) | (fmt["expall"] << fmt["fracbits"])
    maxfin = ((sign << fmt["signpos"]) |
              ((fmt["expall"] - 1) << fmt["fracbits"]) |
              ((1 << fmt["fracbits"]) - 1))
    if mode == "RNE":
        return inf
    if mode == "RTZ":
        return maxfin
    if mode == "RUP":
        return inf if sign == 0 else maxfin
    return inf if sign == 1 else maxfin          # RDN


def round_exact(v, sign, fmt, mode):
    """Round a non-zero exact magnitude v (Fraction) to fmt.

    Returns (bits, flags); flags use rf0[4:0] positions.
    """
    assert v > 0
    e = floor_log2(v)
    if e > fmt["emax"]:
        return overflow_bits(sign, fmt, mode), FLAG_OF | FLAG_NX
    if e >= fmt["emin"]:
        q = v / Fraction(2) ** (e - fmt["fracbits"])
        n, inexact = round_quantum(q, mode, sign)
        if n == (1 << fmt["prec"]):
            n >>= 1
            e += 1
            if e > fmt["emax"]:
                return overflow_bits(sign, fmt, mode), FLAG_OF | FLAG_NX
        bits = ((sign << fmt["signpos"]) |
                ((e + fmt["bias"]) << fmt["fracbits"]) |
                (n - (1 << fmt["fracbits"])))
        return bits, (FLAG_NX if inexact else 0)
    # subnormal range (tininess detected after rounding: rounding up to the
    # minimum normal is not an underflow).
    q = v / Fraction(2) ** (fmt["emin"] - fmt["fracbits"])
    n, inexact = round_quantum(q, mode, sign)
    if n == 0:
        return (((sign << fmt["signpos"])), FLAG_UF | FLAG_NX)
    if n >= (1 << fmt["fracbits"]):
        # rounded up to the minimum normal: inexact but not tiny afterwards
        return ((sign << fmt["signpos"]) |
                (1 << fmt["fracbits"])), (FLAG_NX if inexact else 0)
    flags = (FLAG_UF | FLAG_NX) if inexact else 0
    return ((sign << fmt["signpos"]) | n), flags


def zero_sign_bits(sign, fmt):
    return sign << fmt["signpos"]


def fma_bits(a, b, c, fmt, mode):
    """IEEE 754 fusedMultiplyAdd(a,b,c) with one rounding.

    Returns (result_bits, flags).  Mode is one of RNE/RTZ/RDN/RUP.
    Special-case order follows IEEE 754-2019 §7.2 and spec §2.5.
    """
    _, _, _, ka = parse(a, fmt)
    _, _, _, kb = parse(b, fmt)
    _, _, _, kc = parse(c, fmt)

    nan_a, nan_b, nan_c = (ka in ("qnan", "snan"), kb in ("qnan", "snan"),
                           kc in ("qnan", "snan"))
    snan = "snan" in (ka, kb, kc)
    infzero = ((ka == "zero" and kb == "inf") or
               (ka == "inf" and kb == "zero"))

    # 0×Inf outranks NaN propagation: NV even when c is a (quiet) NaN.
    if infzero:
        return qnan_bits(fmt), FLAG_NV
    if snan:
        return qnan_bits(fmt), FLAG_NV
    if nan_a or nan_b or nan_c:
        return qnan_bits(fmt), 0

    sa, sb, sc = signbit(a, fmt), signbit(b, fmt), signbit(c, fmt)
    prod_sign = sa ^ sb

    # Inf product
    if ka == "inf" or kb == "inf":
        if kc == "inf":
            if sc != prod_sign:
                return qnan_bits(fmt), FLAG_NV      # Inf + (-Inf)
            return ((prod_sign << fmt["signpos"]) |
                    (fmt["expall"] << fmt["fracbits"])), 0
        return ((prod_sign << fmt["signpos"]) |
                (fmt["expall"] << fmt["fracbits"])), 0

    if kc == "inf":
        return c, 0

    # Both product and addend finite: exact arithmetic, then one rounding.
    va, vb, vc = exact_value(a, fmt), exact_value(b, fmt), exact_value(c, fmt)
    exact = va * vb + vc
    if exact == 0:
        prod_zero = (ka == "zero" or kb == "zero")
        c_zero = (kc == "zero")
        if prod_zero and c_zero and prod_sign == sc:
            return zero_sign_bits(prod_sign, fmt), 0
        return zero_sign_bits(1 if mode == "RDN" else 0, fmt), 0
    sign = 0 if exact > 0 else 1
    return round_exact(abs(exact), sign, fmt, mode)


def two_step_bits(a, b, c, fmt, mode):
    """Naive non-fused emulation: round(a*b) then round(prod + c).

    Used only to prove the fused discriminators differ.  Finite inputs only.
    """
    sa, sb = signbit(a, fmt), signbit(b, fmt)
    prod = exact_value(a, fmt) * exact_value(b, fmt)
    if prod == 0:
        pbits = zero_sign_bits(sa ^ sb, fmt)
    else:
        pbits, _ = round_exact(abs(prod), 0 if prod > 0 else 1, fmt, mode)
    xv = exact_value(pbits, fmt)
    cv = exact_value(c, fmt)
    s = xv + cv
    if s == 0:
        kx = parse(pbits, fmt)[3]
        kc = parse(c, fmt)[3]
        sx, sc = signbit(pbits, fmt), signbit(c, fmt)
        if kx == "zero" and kc == "zero" and sx == sc:
            return zero_sign_bits(sx, fmt), 0
        return zero_sign_bits(1 if mode == "RDN" else 0, fmt), 0
    return round_exact(abs(s), 0 if s > 0 else 1, fmt, mode)


# ── Sample cross-checks (a mistyped constant is a hard FAIL) ───────────

def to_ft_bits(x):
    return struct.unpack('>I', struct.pack('>f', x))[0]


def to_fo_bits(x):
    return struct.unpack('>Q', struct.pack('>d', x))[0]


def sample_checks():
    """Hand-written bit patterns with their intended decoded values."""
    return [
        (to_ft_bits(1.5), FT, 1.5, 2e-7, "ft 1.5"),
        (to_ft_bits(-2.25), FT, -2.25, 2e-7, "ft -2.25"),
        (to_ft_bits(1e-10), FT, 1e-10, 2e-17, "ft 1e-10"),
        (0x3F800001, FT, 1 + 2.0 ** -23, 1e-7, "ft spec a"),
        (0x3F7FFFFE, FT, 1 - 2.0 ** -23, 1e-7, "ft spec b"),
        (0xA8800000, FT, -(2.0 ** -46), 1e-16, "ft spec result"),
        (to_fo_bits(1.5), FO, 1.5, 1e-16, "fo 1.5"),
        (to_fo_bits(-2.25), FO, -2.25, 1e-16, "fo -2.25"),
        (0x3FF0000000000001, FO, 1 + 2.0 ** -52, 1e-16, "fo spec a"),
        (0x3FEFFFFFFFFFFFFE, FO, 1 - 2.0 ** -52, 1e-16, "fo spec b"),
        (0xB970000000000000, FO, -(2.0 ** -104), 1e-300, "fo spec result"),
    ]


def structural_anchors():
    return [
        (0x7FC00000, FT, "qnan", "ft qNaN"),
        (0x7F800001, FT, "snan", "ft sNaN"),
        (0x7F800000, FT, "inf", "ft +Inf"),
        (0xFF800000, FT, "inf", "ft -Inf"),
        (0x7FF8000000000000, FO, "qnan", "fo qNaN"),
        (0x7FF0000000000001, FO, "snan", "fo sNaN"),
    ]


def check_samples():
    """Cross-check hand-written bit patterns against their intended values."""
    problems = []
    for bits, fmt, dec, tol, label in sample_checks():
        v = exact_value(bits, fmt)
        if v is None:
            problems.append("%s: not finite" % label)
            continue
        if abs(float(v) - dec) > tol:
            problems.append("%s 0x%X decodes to %.17g, want %.17g"
                            % (label, bits, float(v), dec))
    for bits, fmt, cls, label in structural_anchors():
        if parse(bits, fmt)[3] != cls:
            problems.append("%s 0x%X class %s != %s"
                            % (label, bits, parse(bits, fmt)[3], cls))
    return problems


def spec_anchors():
    """Literal spec/contract expectations, independent of the oracle code."""
    anchors = []
    # spec §2.5 discriminator: exact product then one rounding = -2^-46
    ft_fused = fma_bits(0x3F800001, 0x3F7FFFFE, 0xBF800000, FT, "RNE")
    ft_two = two_step_bits(0x3F800001, 0x3F7FFFFE, 0xBF800000, FT, "RNE")
    anchors.append(("ft fused discriminator = 0xA8800000",
                    ft_fused == (0xA8800000, 0)))
    anchors.append(("ft two-step discriminator = +0 (differs)", ft_two == (0, 0)))
    anchors.append(("ft fused != two-step", ft_fused[0] != ft_two[0]))
    # fo analogue: (1+2^-52)(1-2^-52)-1 = -2^-104
    fo_fused = fma_bits(0x3FF0000000000001, 0x3FEFFFFFFFFFFFFE,
                        0xBFF0000000000000, FO, "RNE")
    fo_two = two_step_bits(0x3FF0000000000001, 0x3FEFFFFFFFFFFFFE,
                           0xBFF0000000000000, FO, "RNE")
    anchors.append(("fo fused discriminator = 0xB970000000000000",
                    fo_fused == (0xB970000000000000, 0)))
    anchors.append(("fo two-step discriminator = +0", fo_two == (0, 0)))
    anchors.append(("fo fused != two-step", fo_fused[0] != fo_two[0]))
    # FUS3/FUS4: c is exactly representable but the fused sum differs from
    # round(1*1) + c (the old c = "1+half-ulp" rounded to -1.0 => no contrast).
    v_ft = fma_bits(0x3F800001, 0x3F800001, 0xBF800002, FT, "RNE")
    v_ft2 = two_step_bits(0x3F800001, 0x3F800001, 0xBF800002, FT, "RNE")
    anchors.append(("ft FUS3 fused != two-step", v_ft[0] != v_ft2[0]))
    v_fo = fma_bits(0x3FF0000000000001, 0x3FF0000000000001,
                    0xBFF0000000000002, FO, "RNE")
    v_fo2 = two_step_bits(0x3FF0000000000001, 0x3FF0000000000001,
                          0xBFF0000000000002, FO, "RNE")
    anchors.append(("fo FUS4 fused != two-step", v_fo[0] != v_fo2[0]))
    # canonical NaN + NV policy
    anchors.append(("sNaN => canonical qNaN + NV",
                    fma_bits(0x7F800001, 0x3F800000, 0x00000000, FT, "RNE")
                    == (0x7FC00000, FLAG_NV)))
    anchors.append(("payload qNaN => canonical qNaN",
                    fma_bits(0x7FC12345, 0x3F800000, 0x00000000, FT, "RNE")
                    == (0x7FC00000, 0)))
    anchors.append(("0*Inf + qNaN => +qNaN + NV",
                    fma_bits(0x00000000, 0x7F800000, 0x7FC00000, FT, "RNE")
                    == (0x7FC00000, FLAG_NV)))
    anchors.append(("Inf + (-Inf product) => qNaN + NV",
                    fma_bits(0x7F800000, 0x3F800000, 0xFF800000, FT, "RNE")
                    == (0x7FC00000, FLAG_NV)))
    anchors.append(("exact zero in RDN => -0",
                    fma_bits(0x3F800000, 0x3F800000, 0xBF800000, FT, "RDN")
                    == (0x80000000, 0)))
    anchors.append(("exact zero in RNE => +0",
                    fma_bits(0x3F800000, 0x3F800000, 0xBF800000, FT, "RNE")
                    == (0x00000000, 0)))
    # mode sensitivity of 1 + 3*2^-25 (0.75 ulp)
    a, b = to_ft_bits(1.0), to_ft_bits(1.0)
    c = 0x33C00000
    outs = {m: fma_bits(a, b, c, FT, m)[0] for m in MODE_NAMES.values()}
    anchors.append(("ft 0.75ulp RNE/RUP = 0x3F800001",
                    outs["RNE"] == 0x3F800001 and outs["RUP"] == 0x3F800001))
    anchors.append(("ft 0.75ulp RTZ/RDN = 0x3F800000",
                    outs["RTZ"] == 0x3F800000 and outs["RDN"] == 0x3F800000))
    return anchors


# ── Case model ─────────────────────────────────────────────────────────

class Case:
    def __init__(self, name, insns, expect_exit=None, expect_rf=None,
                 expect_flags=None, expect_mode=None):
        self.name = name
        self.insns = insns
        self.expect_exit = expect_exit
        self.expect_rf = expect_rf or {}
        self.expect_flags = expect_flags
        self.expect_mode = expect_mode


def value_case(name, insns, expect_rf, expect_flags, expect_mode):
    body = list(insns) + [br_nz(40, 1)]
    return Case(name, body, expect_exit=ILLI_EXIT, expect_rf=expect_rf,
                expect_flags=expect_flags, expect_mode=expect_mode)


def fma_case(tag, fmt, mode, a, b, c, ha=5, hb=10, hc=11, hd=12,
             label=None):
    """One FMA case with oracle-derived result and flags."""
    insn = ftfma if fmt is FT else fofma
    out, flags = fma_bits(a, b, c, fmt, MODE_NAMES[mode])
    name = "%s rf0=%s %s -> 0x%X%s" % (
        tag, MODE_NAMES[mode], label if label else
        ("a=0x%X b=0x%X c=0x%X" % (a, b, c)), out,
        " flags=0x%02X" % flags if flags else "")
    return value_case(
        name,
        set_rf(10, a) + set_rf(11, b) + set_rf(12, c) +
        set_fcsr_mode(mode) + [insn(ha, hb, hc, hd)],
        expect_rf={ha: out}, expect_flags=flags, expect_mode=mode)


CASES = []

# ── GEN: 16 general triples x 2 formats ────────────────────────────────
GEN_TRIPLES = [
    (1.5, 2.0, 0.25),
    (-2.25, 0.5, -1.5),
    (3.0, -4.0, 1000.0),
    (100.0, 3.0, 1e-20),
    (0.1, 10.0, -0.1),
    (-7.0, 0.25, 0.0),
    (1e-10, 1e10, 7.0),
    (123456.0, 0.75, -12345.0),
    (2.0 ** 20, 2.0 ** -20, 1.0),
    (-1.0, 1.0, 3.0),
    (1.0, 1.0, -1.0),                 # exact zero
    (0.5, 0.5, 0.25),
    (-0.5, 0.5, -0.25),
    (7.0, 11.0, -77.0),               # exact zero
    (3.5, 2.0, 0.125),
    (-3.5, -2.0, -0.125),
]
for _i, (x, y, z) in enumerate(GEN_TRIPLES):
    CASES.append(fma_case("GEN%d ft" % (_i + 1), FT, 0,
                          to_ft_bits(x), to_ft_bits(y), to_ft_bits(z),
                          label="(%r,%r,%r)" % (x, y, z)))
for _i, (x, y, z) in enumerate(GEN_TRIPLES):
    CASES.append(fma_case("GEN%d fo" % (_i + 1), FO, 0,
                          to_fo_bits(x), to_fo_bits(y), to_fo_bits(z),
                          label="(%r,%r,%r)" % (x, y, z)))

# ── FUS: explicit single-rounding discriminators ───────────────────────
CASES.append(fma_case("FUS1 ft", FT, 0, 0x3F800001, 0x3F7FFFFE, 0xBF800000,
                      label="spec a=1+2^-23 b=1-2^-23 c=-1"))
CASES.append(fma_case("FUS2 fo", FO, 0, 0x3FF0000000000001,
                      0x3FEFFFFFFFFFFFFE, 0xBFF0000000000000,
                      label="fo a=1+2^-52 b=1-2^-52 c=-1"))
# variants where the fused result and the two-step result differ: the exact
# product needs rounding, and c cancels the *rounded* product exactly.
CASES.append(fma_case("FUS3 ft", FT, 0, 0x3F800001, 0x3F800001,
                      0xBF800002, label="(1+2^-23)^2+c, c=-(1+2^-22)"))
CASES.append(fma_case("FUS4 fo", FO, 0, 0x3FF0000000000001,
                      0x3FF0000000000001, 0xBFF0000000000002,
                      label="(1+2^-52)^2+c, c=-(1+2^-51)"))

# ── NAN: qNaN/sNaN positions, double NaN, payload, 0×Inf ───────────────
FT_Q, FT_S = 0x7FC00000, 0x7F800001
FO_Q, FO_S = 0x7FF8000000000000, 0x7FF0000000000001
for tag, fmt, q, s, one, zero in (("NAN ft", FT, FT_Q, FT_S,
                                   to_ft_bits(1.0), 0),
                                  ("NAN fo", FO, FO_Q, FO_S,
                                   to_fo_bits(1.0), 0)):
    inf = ((fmt["expall"]) << fmt["fracbits"])
    CASES.append(fma_case(tag + " qNaN_a", fmt, 0, q, one, zero,
                          label="qNaN*a+c"))
    CASES.append(fma_case(tag + " qNaN_b", fmt, 0, one, q, zero,
                          label="a*qNaN+c"))
    CASES.append(fma_case(tag + " qNaN_c", fmt, 0, one, one, q,
                          label="a*b+qNaN"))
    CASES.append(fma_case(tag + " sNaN_a", fmt, 0, s, one, zero,
                          label="sNaN*a+c"))
    CASES.append(fma_case(tag + " sNaN_b", fmt, 0, one, s, zero,
                          label="a*sNaN+c"))
    CASES.append(fma_case(tag + " sNaN_c", fmt, 0, one, one, s,
                          label="a*b+sNaN"))
    CASES.append(fma_case(tag + " twoNaN", fmt, 0, q, one, s,
                          label="qNaN*a+sNaN => NV"))
    CASES.append(fma_case(tag + " payload", fmt, 0, q | 0x1234, one, zero,
                          label="payload qNaN => canonical"))
    CASES.append(fma_case(tag + " zero_x_inf_qnan", fmt, 0, zero, inf, q,
                          label="0*Inf+qNaN => NV"))

# ── ZERO: zero-sign rules ──────────────────────────────────────────────
for tag, fmt, one, two, five in (("ZERO ft", FT, to_ft_bits(1.0),
                                  to_ft_bits(2.0), to_ft_bits(5.0)),
                                 ("ZERO fo", FO, to_fo_bits(1.0),
                                  to_fo_bits(2.0), to_fo_bits(5.0))):
    pz = 0
    nz = 1 << fmt["signpos"]
    for mode in MODE_NAMES:
        CASES.append(fma_case("%s opp%d" % (tag, mode), fmt, mode,
                              pz, two, nz,
                              label="(+0*2)+(-0) rf0=%s" % MODE_NAMES[mode]))
    CASES.append(fma_case(tag + " same", fmt, 0, nz, two, nz,
                          label="(-0*2)+(-0) => -0"))
    CASES.append(fma_case(tag + " zeroprod5", fmt, 0, pz, two, five,
                          label="(+0*2)+5 => 5"))
    ntwo = (1 << fmt["signpos"]) | two
    nfive = (1 << fmt["signpos"]) | five
    CASES.append(fma_case(tag + " zeroprod-5", fmt, 0, nz, ntwo, nfive,
                          label="(-0*-2)+(-5) => -5"))

# ── INF: product/addend combinations ───────────────────────────────────
for tag, fmt, one, two, negtwo in (
        ("INF ft", FT, to_ft_bits(1.0), to_ft_bits(2.0), to_ft_bits(-2.0)),
        ("INF fo", FO, to_fo_bits(1.0), to_fo_bits(2.0), to_fo_bits(-2.0))):
    inf = fmt["expall"] << fmt["fracbits"]
    ninf = inf | (1 << fmt["signpos"])
    q = qnan_bits(fmt)
    CASES.append(fma_case(tag + " prod_fin", fmt, 0, inf, two, one,
                          label="Inf*2+1 => +Inf"))
    CASES.append(fma_case(tag + " prod_same", fmt, 0, ninf, two, ninf,
                          label="-Inf*2+(-Inf) => -Inf"))
    CASES.append(fma_case(tag + " opp", fmt, 0, inf, two, ninf,
                          label="Inf*2+(-Inf) => NV"))
    CASES.append(fma_case(tag + " infxinf", fmt, 0, inf, inf, ninf,
                          label="Inf*Inf+(-Inf) => NV"))
    CASES.append(fma_case(tag + " negprod", fmt, 0, ninf, two, inf,
                          label="-Inf*2+(+Inf) => NV"))
    CASES.append(fma_case(tag + " inf_qnan", fmt, 0, inf, two, q,
                          label="Inf*2+qNaN => qNaN, no NV"))

# ── BND: overflow / underflow / subnormal ──────────────────────────────
for tag, fmt, maxfin, minnorm in (
        ("BND ft", FT, 0x7F7FFFFF, 0x00800000),
        ("BND fo", FO, 0x7FEFFFFFFFFFFFFF, 0x0010000000000000)):
    two = to_ft_bits(2.0) if fmt is FT else to_fo_bits(2.0)
    half = to_ft_bits(0.5) if fmt is FT else to_fo_bits(0.5)
    one = to_ft_bits(1.0) if fmt is FT else to_fo_bits(1.0)
    CASES.append(fma_case(tag + " of", fmt, 0, maxfin, two, 0,
                          label="max*2+0 => Inf OF|NX"))
    CASES.append(fma_case(tag + " sub_exact", fmt, 0, minnorm, half, 0,
                          label="minnormal*0.5 => exact subnormal"))
    if fmt is FT:
        a, b, c = 0x00800001, 0x3F800001, 0x80800000
        lab = "inexact subnormal => UF|NX"
    else:
        a, b, c = 0x0010000000000001, 0x3FF0000000000001, \
            0x8010000000000000
        lab = "inexact subnormal => UF|NX"
    CASES.append(fma_case(tag + " uf", fmt, 0, a, b, c, label=lab))
    CASES.append(fma_case(tag + " subop", fmt, 0, 1, two, 0,
                          label="subnormal*2+0 => exact 2^-148"))

# ── MODE: 0.75 ulp and 0.5 ulp, all four modes ─────────────────────────
for tag, fmt, one, c075, c050 in (
        ("MODE ft", FT, to_ft_bits(1.0), 0x33C00000, 0x33800000),
        ("MODE fo", FO, to_fo_bits(1.0), 0x3CA8000000000000,
         0x3CA0000000000000)):
    negone = one | (1 << fmt["signpos"])
    neg075 = c075 | (1 << fmt["signpos"])
    neg050 = c050 | (1 << fmt["signpos"])
    for mode in MODE_NAMES:
        CASES.append(fma_case("%s p75-%s" % (tag, mode), fmt, mode,
                              one, one, c075,
                              label="1+0.75ulp rf0=%s" % MODE_NAMES[mode]))
        CASES.append(fma_case("%s n75-%s" % (tag, mode), fmt, mode,
                              negone, one, neg075,
                              label="-(1+0.75ulp) rf0=%s" % MODE_NAMES[mode]))
        CASES.append(fma_case("%s tie-%s" % (tag, mode), fmt, mode,
                              one, one, c050,
                              label="1+0.5ulp (tie) rf0=%s" % MODE_NAMES[mode]))

# ── ALI: destination aliases each source (read-before-write) ───────────
for tag, fmt in (("ALI ft", FT), ("ALI fo", FO)):
    one = to_ft_bits(1.5) if fmt is FT else to_fo_bits(1.5)
    two = to_ft_bits(2.0) if fmt is FT else to_fo_bits(2.0)
    c = to_ft_bits(0.25) if fmt is FT else to_fo_bits(0.25)
    out = fma_bits(one, two, c, fmt, "RNE")[0]
    CASES.append(value_case(
        tag + " dst=a", set_rf(10, one) + set_rf(11, two) +
        set_rf(12, c) + set_fcsr_mode(0) +
        [ftfma(10, 10, 11, 12) if fmt is FT else fofma(10, 10, 11, 12)],
        expect_rf={10: out}, expect_flags=0, expect_mode=0))
    CASES.append(value_case(
        tag + " dst=b", set_rf(10, one) + set_rf(11, two) +
        set_rf(12, c) + set_fcsr_mode(0) +
        [ftfma(11, 10, 11, 12) if fmt is FT else fofma(11, 10, 11, 12)],
        expect_rf={11: out}, expect_flags=0, expect_mode=0))
    CASES.append(value_case(
        tag + " dst=c", set_rf(10, one) + set_rf(11, two) +
        set_rf(12, c) + set_fcsr_mode(0) +
        [ftfma(12, 10, 11, 12) if fmt is FT else fofma(12, 10, 11, 12)],
        expect_rf={12: out}, expect_flags=0, expect_mode=0))

# ── RF0: rf0 as a source reads the FCSR qNaN ───────────────────────────
CASES.append(value_case(
    "RF0 ft source reads qNaN",
    set_rf(10, to_ft_bits(2.0)) + set_rf(12, to_ft_bits(0.25)) +
    set_fcsr_mode(0) + [ftfma(5, 0, 10, 12)],
    expect_rf={5: FT_Q}, expect_flags=0, expect_mode=0))
CASES.append(value_case(
    "RF0 fo source reads qNaN",
    set_rf(10, to_fo_bits(2.0)) + set_rf(12, to_fo_bits(0.25)) +
    set_fcsr_mode(0) + [fofma(5, 0, 10, 12)],
    expect_rf={5: FO_Q}, expect_flags=0, expect_mode=0))

# ── IL: destination rf0 ⇒ ILLI (fault epilogue: no fault exits 0) ──────
CASES.append(Case("IL1 ftfma dst rf0 -> ILLI", [ftfma(0, 10, 11, 12)],
                  expect_exit=ILLI_EXIT))
CASES.append(Case("IL2 fofma dst rf0 -> ILLI", [fofma(0, 10, 11, 12)],
                  expect_exit=ILLI_EXIT))


# ── Runner ────────────────────────────────────────────────────────────

def run_case(case):
    if case.expect_rf or case.expect_flags is not None:
        rom = build_rom(case.insns)
        code, log = run_dcpu(rom)
        if code != case.expect_exit:
            return False, [f"exit=0x{code & 0xFF:02X} "
                           f"(expect 0x{case.expect_exit:02X})"]
        details = []
        ok = True
        for idx, exp in sorted(case.expect_rf.items()):
            got = last_reg(log, 'RF', idx)
            good = got == exp
            ok = ok and good
            details.append(
                f"RF[{idx:02d}] expect=0x{exp:016X} got="
                f"{'0x%016X' % got if got is not None else 'MISSING'} "
                f"{'OK' if good else 'MISMATCH'}")
        rf0 = last_reg(log, 'RF', 0)
        if case.expect_flags is not None:
            got = None if rf0 is None else rf0 & 0x1F
            good = got == case.expect_flags
            ok = ok and good
            details.append(f"rf0[4:0] expect=0x{case.expect_flags:02X} got="
                           f"{'0x%02X' % got if got is not None else 'MISSING'} "
                           f"{'OK' if good else 'MISMATCH'}")
        if case.expect_mode is not None:
            got = None if rf0 is None else (rf0 >> 32) & 0x3
            good = got == case.expect_mode
            ok = ok and good
            details.append(f"rf0[33:32] expect={case.expect_mode} got="
                           f"{got if got is not None else 'MISSING'} "
                           f"{'OK' if good else 'MISMATCH'}")
        if rf0 is not None:
            ro = rf0 & ~0x30000001F
            good = ro == (RESET0 & ~0x30000001F)
            ok = ok and good
            details.append(f"rf0 read-only bits expect=0x"
                           f"{RESET0 & ~0x30000001F:016X} got=0x{ro:016X} "
                           f"{'OK' if good else 'MISMATCH'}")
        return ok, details
    if case.expect_exit == ILLI_EXIT:
        rom = build_fault_rom(case.insns)
    else:
        rom = build_rom(case.insns)
    code, stderr = run_plain(rom)
    good = (code == case.expect_exit)
    detail = f"exit=0x{code & 0xFF:02X} (expect 0x{case.expect_exit:02X})"
    if not good and stderr and code != -1:
        detail += f" stderr={stderr[:120]}"
    return good, [detail]


def selftest():
    """Prove each assertion kind has a reachable FAIL path."""
    os.chdir(_REPO_ROOT)
    print("=" * 78)
    print("QEMU-070t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    good = fma_bits(0x3F800000, 0x3F800000, 0x00000000, FT, "RNE")[0]
    cs = [
        ("RF value comparison",
         value_case("selftest rf", set_rf(10, 0x3F800000) +
                    set_rf(11, 0x3F800000) + set_rf(12, 0) +
                    set_fcsr_mode(0) + [ftfma(5, 10, 11, 12)],
                    expect_rf={5: 0xDEADBEEF}, expect_flags=0,
                    expect_mode=0)),
        ("rf0 flags comparison",
         value_case("selftest flags", set_rf(10, 0x7F7FFFFF) +
                    set_rf(11, 0x40000000) + set_rf(12, 0) +
                    set_fcsr_mode(0) + [ftfma(5, 10, 11, 12)],
                    expect_rf={5: 0x7F800000}, expect_flags=0,
                    expect_mode=0)),
        ("rf0 rounding-mode preservation",
         value_case("selftest mode", set_rf(10, 0x3F800000) +
                    set_rf(11, 0x3F800000) + set_rf(12, 0) +
                    set_fcsr_mode(2) + [ftfma(5, 10, 11, 12)],
                    expect_rf={5: good}, expect_flags=0, expect_mode=0)),
        ("fault exit-code",
         Case("selftest fault", [ftfma(5, 10, 11, 12)],
              expect_exit=ILLI_EXIT)),
    ]
    results = []
    for name, c in cs:
        ok, _ = run_case(c)
        results.append((name, ok is False))
    allok = True
    for name, v in results:
        if not v:
            allok = False
        print(f"  [{'PASS' if v else 'FAIL'}] {name} must be detected as FAIL")
    print(f"\nSelf-test: {'PASS' if allok else 'FAIL'}")
    return 0 if allok else 1


def print_oracle():
    problems = check_samples()
    anchors = spec_anchors()
    print("fusedMultiplyAdd oracle (exact rational arithmetic, not QEMU)")
    print("  spec anchors (literal expectations, independent of oracle code):")
    bad = 0
    for name, ok in anchors:
        if not ok:
            bad += 1
        print("    [%s] %s" % ("PASS" if ok else "FAIL", name))
    for p in problems:
        print("  [FAIL] " + p)
    ncase = len(CASES)
    nsamples = len(sample_checks()) + len(structural_anchors())
    print("  samples: %d bit-pattern cross-checks; anchors: %d"
          % (nsamples, len(anchors)))
    print("Oracle: %s (%d cases, %d anchor checks)"
          % ("PASS" if not problems and not bad else "FAIL", ncase,
             len(anchors)))
    return 0 if (not problems and not bad) else 1


def category_counts():
    prefixes = ("GEN", "FUS", "NAN", "ZERO", "INF", "BND", "MODE", "ALI",
                "RF0", "IL")
    return {p: sum(1 for c in CASES if c.name.startswith(p))
            for p in prefixes}


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1
    problems = check_samples()
    if problems:
        print("ERROR: sample matrix cross-check failed:")
        for p in problems:
            print("  - " + p)
        return 1
    bad_anchor = [n for n, ok in spec_anchors() if not ok]
    if bad_anchor:
        print("ERROR: spec anchor check failed: " + ", ".join(bad_anchor))
        return 1
    print("=" * 78)
    print("QEMU-070t Min ROM Probe (ftfma/fofma, fused single rounding)")
    print("=" * 78)

    passed = failed = 0
    failed_names = []
    for case in CASES:
        ok, details = run_case(case)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
            failed_names.append(case.name)
        print(f"  [{status}] {case.name}")
        for d in details:
            print(f"          {d}")

    print("-" * 78)
    cc = category_counts()
    print("coverage: " + ", ".join("%s=%d" % (k, v) for k, v in cc.items()))
    print(f"Main: {passed}/{passed + failed} passed, {failed} failed")
    if failed_names:
        print("Failed:")
        for n in failed_names:
            print(f"  - {n}")
    print(f"\nOverall: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--oracle" in sys.argv:
        sys.exit(print_oracle())
    sys.exit(main())
