#!/usr/bin/env python3
"""Min ROM probe for QEMU-036t: FP conversion family (20 insns, softfloat).

Spec sources (expectations derived by hand from these, never from QEMU):
  - spec/SimRISC-07 §格式转换指令
  - spec/SimRISC-00 §浮点寄存器 / §浮点状态寄存器
  - .tao/knowledge/contract-fp.md §1 / §2 / §3 / §4
Encodings: contracts/opcodes.yaml.  Exit codes: ADR-0004 D5.8 (PASS=0x00,
ILLI=0x88).

Instructions under test (20):
  convert_ff  (4): ft2ft ft2fo fo2ft fo2fo        (orri, block immu6 1..63)
  convert_f2i (8): ft2it ft2io ft2ut ft2uo fo2it fo2io fo2ut fo2uo
  convert_i2f (8): it2ft io2ft ut2ft uo2ft it2fo io2fo ut2fo uo2fo

Expected-value provenance (task §6.1, see /tmp derivation in completion notes):
  * RNE float->float bit patterns use the host struct anchor.
  * Non-RNE (RTZ/RDN/RUP) patterns were derived with an exact rational
    round-to-float32 routine; the f64 inputs are exact binary fractions
    (1 +/- 2^-24, 1 +/- 2^-24 +/- 2^-30, etc.).
  * f2i uses round-toward-zero truncation, saturating at INT/INT_MAX/MIN
    with NV on NaN/Inf/out-of-range (spec §格式转换指令).  Per the task
    decision (§8-2), f2i does not raise NX for precision loss.
  * i2f rounds per rf0[33:32] and raises NX when inexact.
  * NaN payload conversion follows IEEE754 (float32 mantissa << 29 for
    widening; narrowing keeps the top mantissa bits).  sNaN input raises NV
    and returns a quiet NaN (spec §格式转换指令).
  * ft results are zero-extended to 64 bits except the same-format register
    moves ft2ft/fo2fo, which preserve all 64 bits (spec calls them
    "浮点寄存器间搬移"; cf. contract-fp §14 set.ft value transfer).

Verification channels (same as min_rom_probe_034t/035t):
  * value cases -> QEMU `-d cpu` dump, parsing the *last* RF[]/RD[] dump.
  * fault cases -> process exit code (ILLI 0x88).
  * E2E cases   -> in-ROM compare + exit-port PASS/FAIL epilogue.

Reverse gate (.work/evidence/QEMU-036t/run.sh --inject) reverts parts of the
implementation and requires the corresponding cases to FAIL.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
from fractions import Fraction

# D6 compliance: resolve probe artifact dir via paths.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths  # noqa: E402


def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d


QEMU = ".work/build/qemu/qemu-system-dadao"

# FCSR reset value (target/dadao/cpu.h::DADAO_RESET_RF0)
RESET0 = 0x7FF800007FC00000

PASS_EXIT = 0x00
ILLI_EXIT = 0x88

# rf0[4:0] accrued exception bits
NV = 0x01
OF = 0x04
UF = 0x08
NX = 0x10
FLAG_OF_NX = OF | NX
FLAG_UF_NX = UF | NX

# ── Instruction encoding (op / ha from contracts/opcodes.yaml) ────────────

ILLI = 0x77000000
SWYM = 0x77880000

# rf0[33:32] rounding mode selectors (SimRISC-00 §浮点状态寄存器)
RNE, RTZ, RDN, RUP = 0, 1, 2, 3


def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)


def encode_rrii(op, ha, hb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)


def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | (hd & 0x3F))


def encode_riii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))


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


def cmp_uo_rd(rdhb, rdhc, rdhd):
    return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


def rd2rf(rfhb, rdhc, hd):
    return encode_orri(0x40, 0x3D, rfhb, rdhc, hd)


def rf2rd(rdhb, rfhc, hd):
    return encode_orri(0x40, 0x3E, rdhb, rfhc, hd)


# ── Instructions under test (ha from contracts/opcodes.yaml) ──────────────

def ft2fo(hb, hc, hd):
    return encode_orri(0x44, 0x01, hb, hc, hd)


def ft2ft(hb, hc, hd):
    return encode_orri(0x44, 0x02, hb, hc, hd)


def fo2ft(hb, hc, hd):
    return encode_orri(0x44, 0x09, hb, hc, hd)


def fo2fo(hb, hc, hd):
    return encode_orri(0x44, 0x0A, hb, hc, hd)


def ft2it(hb, hc, hd):
    return encode_orri(0x44, 0x30, hb, hc, hd)


def ft2io(hb, hc, hd):
    return encode_orri(0x44, 0x31, hb, hc, hd)


def ft2ut(hb, hc, hd):
    return encode_orri(0x44, 0x32, hb, hc, hd)


def ft2uo(hb, hc, hd):
    return encode_orri(0x44, 0x33, hb, hc, hd)


def it2ft(hb, hc, hd):
    return encode_orri(0x44, 0x34, hb, hc, hd)


def io2ft(hb, hc, hd):
    return encode_orri(0x44, 0x35, hb, hc, hd)


def ut2ft(hb, hc, hd):
    return encode_orri(0x44, 0x36, hb, hc, hd)


def uo2ft(hb, hc, hd):
    return encode_orri(0x44, 0x37, hb, hc, hd)


def fo2it(hb, hc, hd):
    return encode_orri(0x44, 0x38, hb, hc, hd)


def fo2io(hb, hc, hd):
    return encode_orri(0x44, 0x39, hb, hc, hd)


def fo2ut(hb, hc, hd):
    return encode_orri(0x44, 0x3A, hb, hc, hd)


def fo2uo(hb, hc, hd):
    return encode_orri(0x44, 0x3B, hb, hc, hd)


def it2fo(hb, hc, hd):
    return encode_orri(0x44, 0x3C, hb, hc, hd)


def io2fo(hb, hc, hd):
    return encode_orri(0x44, 0x3D, hb, hc, hd)


def ut2fo(hb, hc, hd):
    return encode_orri(0x44, 0x3E, hb, hc, hd)


def uo2fo(hb, hc, hd):
    return encode_orri(0x44, 0x3F, hb, hc, hd)


# ── Setup helpers ─────────────────────────────────────────────────────────

def load_imm64_rd(rd, val):
    insns = [set_zw_rd(rd, val & 0xFFFF)]
    for wp in range(1, 4):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            insns.append(or_w_rd(rd, wp, w))
    return insns


def set_rf(rf, val):
    """Load rf[rf] = val (uses rd31 as scratch; rd2rf writes are trusted)."""
    return load_imm64_rd(31, val) + [rd2rf(rf, 31, 1)]


def set_rd(rd, val):
    return load_imm64_rd(rd, val)


def set_round_mode(mode):
    """Set rf0[33:32] via rd2rf(rf0) — goes through the FCSR write mask."""
    return set_rf(0, mode << 32)


def rf0_with(mode=0, flags=0):
    return RESET0 | (mode << 32) | flags


# ── ROM assembly ──────────────────────────────────────────────────────────

TRAMPOLINE = [
    set_zw_rb(16, 2, 0xFFFF), or_w_rb(16, 1, 0x8000),  # rb16 = 0xFFFF80000000
    set_zw_rb(17, 2, 0xFFFF),                          # rb17 = 0xFFFF00000000
    encode_rwii(0x4C, 40, 0, 0x0001),                  # rd40 = 1
]


def build_rom(test_insns):
    rom = b''.join(TRAMPOLINE) + b''.join(test_insns) + struct.pack('>I', ILLI)
    while len(rom) < 64:
        rom += struct.pack('>I', SWYM)
    return rom


def build_fault_rom(test_insns):
    """Body + PASS epilogue: if no fault occurs the exit code is 0x00 != 0x88."""
    return (b''.join(TRAMPOLINE) + b''.join(test_insns) +
            b''.join([set_zw_rd(18, 0), st_o_rd(18, 16, 0)]))


def build_e2e_rom(test_insns):
    return b''.join(TRAMPOLINE) + b''.join(test_insns)


# ── QEMU execution ────────────────────────────────────────────────────────

def run_plain(rom_data, timeout=10):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(b'\x00' * 16)
        kp = f.name
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp],
            capture_output=True, timeout=timeout, text=True)
        return r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rp)
        os.unlink(kp)


def run_dcpu(rom_data, timeout=10):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(b'\x00' * 16)
        kp = f.name
    lp = rp + '.cpu.log'
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp,
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


def last_reg(log_text, bank, idx):
    pat = re.compile(r'%s\[%02d\]:\s*([0-9a-fA-F]{16})' % (bank, idx))
    m = None
    for mm in pat.finditer(log_text):
        m = mm
    return int(m.group(1), 16) if m else None


# ── E2E assertion epilogue ────────────────────────────────────────────────

def e2e_epilogue(checks, fail_code):
    """checks: list of (actual_rd, expected_rd, flag_rd)."""
    N = len(checks)
    insns = []
    for i, (actual, expected, flag) in enumerate(checks):
        offset = 2 * (N - i) + 1
        insns.append(cmp_uo_rd(flag, actual, expected))
        insns.append(br_nz(flag, offset))
    insns.append(set_zw_rd(18, 0))
    insns.append(st_o_rd(18, 16, 0))          # PASS: exit 0
    insns.append(set_zw_rd(19, fail_code))
    insns.append(st_o_rd(19, 16, 0))          # FAIL: exit fail_code
    return insns


# ── Independent expectation derivation (no LLVM, no QEMU) ─────────────────
#
# These routines re-derive the hard-coded expectations from first principles
# so that verify_derivations() can prove the literals were not copied from a
# QEMU/LLVM run:
#   * RNE anchors use the host struct (allowed by task §6.1).
#   * Non-RNE patterns use an exact rational rounder over the binary value.
#   * f2i constants are plain integer bounds / truncation.

def _f64_value(bits):
    """Return (sign, Fraction|None) for a float64 bit pattern (None = NaN/inf)."""
    sign = (bits >> 63) & 1
    exp = (bits >> 52) & 0x7FF
    man = bits & ((1 << 52) - 1)
    if exp == 0x7FF:
        return sign, None
    if exp == 0:
        m, e = man, -1074
    else:
        m, e = (1 << 52) | man, exp - 1023 - 52
    v = Fraction(m) * (Fraction(2) ** e) if e >= 0 else Fraction(m, 2 ** (-e))
    return sign, v


def _f32_bits(sign, exp, man):
    return (sign << 31) | (exp << 23) | (man & 0x7FFFFF)


def _round_mag_to_f32_bits(sign, value, mode):
    """Exact round of the magnitude `value` (Fraction) to float32 bits."""
    if value == 0:
        return sign << 31
    k = value.numerator.bit_length() - value.denominator.bit_length()
    if Fraction(2) ** k > value:
        k -= 1
    while Fraction(2) ** (k + 1) <= value:
        k += 1
    if k < -126:
        unit, e32 = Fraction(1, 2 ** 149), 0
    else:
        unit, e32 = Fraction(2) ** (k - 23), k + 127
    x = value / unit
    fl = x.numerator // x.denominator
    frac = x - fl
    if frac == 0 or mode == 'to_zero':
        r = fl
    elif mode == 'down':
        r = fl if sign == 0 else fl + 1
    elif mode == 'up':
        r = fl + 1 if sign == 0 else fl
    else:  # nearest_even
        r = fl if frac < Fraction(1, 2) else (
            fl + 1 if frac > Fraction(1, 2) else (fl if fl % 2 == 0 else fl + 1))
    if e32 == 0:
        if r >= (1 << 23):
            e32, r = 1, r - (1 << 23)
        if r == 0:
            return sign << 31
        return _f32_bits(sign, 0, r)
    if r >= (1 << 24):
        r >>= 1
        e32 += 1
    if e32 >= 255:
        return _f32_bits(sign, 0xFF, 0)
    return _f32_bits(sign, e32, r - (1 << 23))


def _derive_fo2ft(bits, mode):
    """Exact float64 -> float32 for a finite value; NaN/inf handled directly."""
    sign, v = _f64_value(bits)
    if v is None:
        exp = (bits >> 52) & 0x7FF
        if (bits & ((1 << 52) - 1)) == 0:
            return _f32_bits(sign, 0xFF, 0)          # inf
        return _f32_bits(sign, 0xFF, ((bits >> 29) & 0x7FFFFF) | (1 << 22))
    r = _round_mag_to_f32_bits(sign, v, mode)
    # overflow detection: exact value beyond float32 max -> inf
    if v >= Fraction(2 ** 128 - 2 ** 104):
        return _f32_bits(sign, 0xFF, 0)
    return r


def _derive_int_to_f32(n, signed, mode):
    """Exact integer -> float32 (RNE/RTZ/RDN/RUP)."""
    sign = 0
    v = n
    if signed and n < 0:
        sign, v = 1, -n
    return _round_mag_to_f32_bits(sign, Fraction(v), mode)


def _derive_ft2fo_nan_payload(bits):
    """Widening NaN: float32 mantissa << 29 (quiet bit stays set)."""
    sign = (bits >> 31) & 1
    return (sign << 63) | (0x7FF << 52) | ((bits & 0x7FFFFF) << 29)


def verify_derivations():
    """Return list of (label, ok). Proves the literals below are derivable."""
    checks = []
    M = {'nearest_even': 'RNE', 'to_zero': 'RTZ', 'down': 'RDN', 'up': 'RUP'}
    exp = {
        (0x3FF0000010000000, 'nearest_even'): 0x3F800000,
        (0x3FF0000010000000, 'to_zero'): 0x3F800000,
        (0x3FF0000010000000, 'down'): 0x3F800000,
        (0x3FF0000010000000, 'up'): 0x3F800001,
        (0x3FF0000010400000, 'nearest_even'): 0x3F800001,
        (0x3FF0000010400000, 'to_zero'): 0x3F800000,
        (0x3FF0000010400000, 'down'): 0x3F800000,
        (0x3FF0000010400000, 'up'): 0x3F800001,
        (0xBFF0000010000000, 'nearest_even'): 0xBF800000,
        (0xBFF0000010000000, 'to_zero'): 0xBF800000,
        (0xBFF0000010000000, 'down'): 0xBF800001,
        (0xBFF0000010000000, 'up'): 0xBF800000,
        (0x3690000000000000, 'nearest_even'): 0x00000000,
        (0x36A4000000000000, 'nearest_even'): 0x00000001,
        (0x7FEFFFFFFFFFFFFF, 'nearest_even'): 0x7F800000,
        (0xFFEFFFFFFFFFFFFF, 'nearest_even'): 0xFF800000,
        (0x7FF82468A0000000, 'nearest_even'): 0x7FC12345,
    }
    for (bits, mode), want in exp.items():
        got = _derive_fo2ft(bits, mode)
        checks.append((f"fo2ft 0x{bits:016X} {M[mode]} = 0x{want:08X}", got == want))

    # host RNE anchor for a plain widening pair
    f = struct.unpack('>f', struct.pack('>I', 0x3FC00000))[0]
    checks.append(("host struct ft2fo 1.5f = 0x3FF8000000000000",
                   struct.unpack('>Q', struct.pack('>d', f))[0] == 0x3FF8000000000000))

    # NaN payload rule
    checks.append(("ft2fo qNaN payload 0x7FC12345 = 0x7FF82468A0000000",
                   _derive_ft2fo_nan_payload(0x7FC12345) == 0x7FF82468A0000000))

    # i2f non-RNE
    checks.append(("it2ft 2^24+3 RNE = 0x4B800002",
                   _derive_int_to_f32(2 ** 24 + 3, True, 'nearest_even') == 0x4B800002))
    checks.append(("it2ft 2^24+3 RTZ = 0x4B800001",
                   _derive_int_to_f32(2 ** 24 + 3, True, 'to_zero') == 0x4B800001))
    checks.append(("it2ft 2^24+3 RDN = 0x4B800001",
                   _derive_int_to_f32(2 ** 24 + 3, True, 'down') == 0x4B800001))
    checks.append(("it2ft 2^24+3 RUP = 0x4B800002",
                   _derive_int_to_f32(2 ** 24 + 3, True, 'up') == 0x4B800002))
    checks.append(("it2ft 2^24+1 RNE = 0x4B800000",
                   _derive_int_to_f32(2 ** 24 + 1, True, 'nearest_even') == 0x4B800000))
    checks.append(("ut2ft 0xFFFFFFFF RNE = 0x4F800000",
                   _derive_int_to_f32(0xFFFFFFFF, False, 'nearest_even') == 0x4F800000))
    checks.append(("uo2ft 2^64-1 RNE = 0x5F800000",
                   _derive_int_to_f32(2 ** 64 - 1, False, 'nearest_even') == 0x5F800000))
    checks.append(("it2ft -16 = 0xC1800000",
                   _derive_int_to_f32(-16, True, 'nearest_even') == 0xC1800000))

    # f2i integer bounds / truncation
    checks.append(("f2i INT32 bounds", (_f2i_bounds_check())))
    return checks


def _f2i_bounds_check():
    return (INT32_MAX == 2 ** 31 - 1 and INT32_MIN_SEXT == (-2 ** 31) & 0xFFFFFFFFFFFFFFFF
            and INT64_MAX == 2 ** 63 - 1 and INT64_MIN == 2 ** 63
            and UINT32_MAX == 2 ** 32 - 1 and UINT64_MAX == 2 ** 64 - 1
            and int(2.75) == 2 and int(-2.75) == -2)


# ── Case model ────────────────────────────────────────────────────────────

class Case:
    def __init__(self, name, insns, expect_exit=None,
                 expect_rf=None, expect_rd=None, e2e=False):
        self.name = name
        self.insns = insns
        self.expect_exit = expect_exit
        self.expect_rf = expect_rf or {}
        self.expect_rd = expect_rd or {}
        self.e2e = e2e


def value_case(name, insns, expect_rf=None, expect_rd=None):
    body = list(insns) + [br_nz(40, 1)]
    return Case(name, body, expect_exit=ILLI_EXIT,
                expect_rf=expect_rf, expect_rd=expect_rd)


# ══════════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════════

INT32_MAX = 0x7FFFFFFF
INT32_MIN_SEXT = 0xFFFFFFFF80000000
INT64_MAX = 0x7FFFFFFFFFFFFFFF
INT64_MIN = 0x8000000000000000
UINT32_MAX = 0x00000000FFFFFFFF
UINT64_MAX = 0xFFFFFFFFFFFFFFFF

# ft / fo sample values
FT_1 = 0x3F800000
FT_1_5 = 0x3FC00000
FT_N2_5 = 0xC0200000
FT_2_75 = 0x40300000
FT_N2_75 = 0xC0300000
FT_3E9 = 0x4F32D05E        # 3.0e9, exactly representable in ft
FT_1E10 = 0x501502F9       # 1.0e10 (out of int32 range)
FT_1E30 = 0x7149F2CA       # 1.0e30 (out of int64 range)
FT_SUB = 0x00000001        # 2^-149 (smallest positive subnormal)
FT_QNAN = 0x7FC00000
FT_SNAN = 0x7F800001
FT_QNAN_PAY = 0x7FC12345   # qNaN with payload

FO_1 = 0x3FF0000000000000
FO_1_5 = 0x3FF8000000000000
FO_N2_5 = 0xC004000000000000
FO_2_75 = 0x4006000000000000
FO_N2_75 = 0xC006000000000000
FO_1E30 = 0x46293E5939A08CEA
FO_2N150 = 0x3690000000000000       # 2^-150
FO_125_2N149 = 0x36A4000000000000   # 1.25 * 2^-149
FO_DBL_MAX = 0x7FEFFFFFFFFFFFFF
FO_N_DBL_MAX = 0xFFEFFFFFFFFFFFFF
FO_QNAN_PAY = 0x7FF82468A0000000
FO_QNAN_LOW = 0x7FF8000000000001
FO_SNAN = 0x7FF0000000000001

CASES = []

# ══════════════════════════════════════════════════════════════════════════
#  convert_ff value cases
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "FF01 ft2fo +1.0f -> +1.0d (exact, no flags)",
    set_rf(8, FT_1) + [ft2fo(4, 8, 1)],
    expect_rf={4: FO_1, 0: rf0_with()}))

CASES.append(value_case(
    "FF02 ft2fo 1.5f -> 1.5d (exact)",
    set_rf(8, FT_1_5) + [ft2fo(4, 8, 1)],
    expect_rf={4: FO_1_5}))

CASES.append(value_case(
    "FF03 ft2fo -2.5f -> -2.5d (sign preserved)",
    set_rf(8, FT_N2_5) + [ft2fo(4, 8, 1)],
    expect_rf={4: FO_N2_5}))

CASES.append(value_case(
    "FF04 ft2fo ignores source high 32 bits",
    set_rf(8, 0xDEADBEEF3F800000) + [ft2fo(4, 8, 1)],
    expect_rf={4: FO_1}))

CASES.append(value_case(
    "FF05 ft2fo block of 3 {rf4:rf6},{rf8:rf10}",
    set_rf(8, FT_1) + set_rf(9, FT_1_5) + set_rf(10, FT_N2_5) +
    [ft2fo(4, 8, 3)],
    expect_rf={4: FO_1, 5: FO_1_5, 6: FO_N2_5}))

CASES.append(value_case(
    "FF06 fo2ft +1.0d -> +1.0f (high 32 zero-extended)",
    set_rf(8, FO_1) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_1, 0: rf0_with()}))

CASES.append(value_case(
    "FF07 fo2ft 1.5d -> 1.5f (exact)",
    set_rf(8, FO_1_5) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_1_5}))

CASES.append(value_case(
    "FF08 fo2ft 2^-150 -> +0 with UF|NX",
    set_rf(8, FO_2N150) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0x00000000, 0: rf0_with(0, FLAG_UF_NX)}))

CASES.append(value_case(
    "FF09 fo2ft 1.25*2^-149 -> subnormal 0x1 with UF|NX",
    set_rf(8, FO_125_2N149) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0x00000001, 0: rf0_with(0, FLAG_UF_NX)}))

CASES.append(value_case(
    "FF10 fo2ft +DBL_MAX -> +Inf with OF|NX",
    set_rf(8, FO_DBL_MAX) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0x7F800000, 0: rf0_with(0, FLAG_OF_NX)}))

CASES.append(value_case(
    "FF11 fo2ft -DBL_MAX -> -Inf with OF|NX",
    set_rf(8, FO_N_DBL_MAX) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0xFF800000, 0: rf0_with(0, FLAG_OF_NX)}))

CASES.append(value_case(
    "FF12 fo2ft qNaN payload narrowed -> 0x7FC12345",
    set_rf(8, FO_QNAN_PAY) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_QNAN_PAY, 0: rf0_with()}))

CASES.append(value_case(
    "FF13 fo2ft sNaN -> qNaN + NV",
    set_rf(8, FO_SNAN) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_QNAN, 0: rf0_with(0, NV)}))

CASES.append(value_case(
    "FF14 ft2fo qNaN payload widened -> 0x7FF82468A0000000",
    set_rf(8, FT_QNAN_PAY) + [ft2fo(4, 8, 1)],
    expect_rf={4: FO_QNAN_PAY, 0: rf0_with()}))

CASES.append(value_case(
    "FF15 ft2fo sNaN -> qNaN + NV",
    set_rf(8, FT_SNAN) + [ft2fo(4, 8, 1)],
    expect_rf={4: 0x7FF8000020000000, 0: rf0_with(0, NV)}))

CASES.append(value_case(
    "FF16 ft2ft moves all 64 bits unchanged",
    set_rf(8, 0x12345678DEADBEEF) + [ft2ft(4, 8, 1)],
    expect_rf={4: 0x12345678DEADBEEF, 0: rf0_with()}))

CASES.append(value_case(
    "FF17 fo2fo moves all 64 bits unchanged",
    set_rf(8, 0x0123456789ABCDEF) + [fo2fo(4, 8, 1)],
    expect_rf={4: 0x0123456789ABCDEF}))

CASES.append(value_case(
    "FF18 ft2ft block of 3 {rf4:rf6},{rf8:rf10}",
    set_rf(8, 0x1111111111111111) + set_rf(9, 0x2222222222222222) +
    set_rf(10, 0x3333333333333333) + [ft2ft(4, 8, 3)],
    expect_rf={4: 0x1111111111111111, 5: 0x2222222222222222,
               6: 0x3333333333333333}))

CASES.append(value_case(
    "FF19 fo2fo block of 3 {rf4:rf6},{rf8:rf10}",
    set_rf(8, FO_1) + set_rf(9, FO_1_5) + set_rf(10, FO_N2_5) +
    [fo2fo(4, 8, 3)],
    expect_rf={4: FO_1, 5: FO_1_5, 6: FO_N2_5}))

CASES.append(value_case(
    "FF20 ft2fo adjacent ranges (dest 4..6, src 7..9) legal",
    set_rf(7, FT_1) + set_rf(8, FT_1_5) + set_rf(9, FT_N2_5) +
    [ft2fo(4, 7, 3)],
    expect_rf={4: FO_1, 5: FO_1_5, 6: FO_N2_5}))

# ── convert_ff rounding modes (results distinguishable) ───────────────────
# tie = 1 + 2^-24 exactly between f32 neighbours 1.0 (even) and 1+2^-23
CASES.append(value_case(
    "FF21 fo2ft RNE tie -> lower (even)",
    set_round_mode(RNE) + set_rf(8, 0x3FF0000010000000) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_1, 0: rf0_with(RNE, NX)}))
CASES.append(value_case(
    "FF22 fo2ft RUP tie -> upper",
    set_round_mode(RUP) + set_rf(8, 0x3FF0000010000000) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0x3F800001, 0: rf0_with(RUP, NX)}))
CASES.append(value_case(
    "FF23 fo2ft RTZ tie -> lower",
    set_round_mode(RTZ) + set_rf(8, 0x3FF0000010000000) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_1, 0: rf0_with(RTZ, NX)}))
CASES.append(value_case(
    "FF24 fo2ft RDN positive tie -> lower",
    set_round_mode(RDN) + set_rf(8, 0x3FF0000010000000) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_1, 0: rf0_with(RDN, NX)}))
CASES.append(value_case(
    "FF25 fo2ft RNE above tie -> upper",
    set_round_mode(RNE) + set_rf(8, 0x3FF0000010400000) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0x3F800001, 0: rf0_with(RNE, NX)}))
CASES.append(value_case(
    "FF26 fo2ft RTZ above tie -> lower",
    set_round_mode(RTZ) + set_rf(8, 0x3FF0000010400000) + [fo2ft(4, 8, 1)],
    expect_rf={4: FT_1, 0: rf0_with(RTZ, NX)}))
CASES.append(value_case(
    "FF27 fo2ft RDN negative tie -> more negative",
    set_round_mode(RDN) + set_rf(8, 0xBFF0000010000000) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0xBF800001, 0: rf0_with(RDN, NX)}))
CASES.append(value_case(
    "FF28 fo2ft RUP negative tie -> toward zero",
    set_round_mode(RUP) + set_rf(8, 0xBFF0000010000000) + [fo2ft(4, 8, 1)],
    expect_rf={4: 0xBF800000, 0: rf0_with(RUP, NX)}))

# ── convert_ff legality ───────────────────────────────────────────────────
CASES.append(Case("FL01 ft2fo partial overlap -> ILLI",
                  [ft2fo(4, 3, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL02 ft2fo complete coincidence -> ILLI",
                  [ft2fo(4, 4, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL03 ft2ft complete coincidence -> ILLI",
                  [ft2ft(4, 4, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL04 fo2ft overlap (src inside dest) -> ILLI",
                  [fo2ft(4, 4, 2)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL05 fo2fo overlap (dest inside src) -> ILLI",
                  [fo2fo(5, 4, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL06 ft2fo dst rf0 -> ILLI",
                  [ft2fo(0, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL07 ft2ft dst rf0 -> ILLI",
                  [ft2ft(0, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL08 fo2ft dst rf0 -> ILLI",
                  [fo2ft(0, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL09 fo2fo dst rf0 -> ILLI",
                  [fo2fo(0, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL10 ft2fo immu6=0 -> ILLI",
                  [ft2fo(4, 8, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL11 ft2fo dest 62+4>64 -> ILLI",
                  [ft2fo(62, 8, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL12 ft2fo src 62+4>64 -> ILLI",
                  [ft2fo(4, 62, 4)], expect_exit=ILLI_EXIT))

# ══════════════════════════════════════════════════════════════════════════
#  convert_f2i value cases
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "FI01 ft2it 2.75 -> 2 (truncate, no NX)",
    set_rf(8, FT_2_75) + [ft2it(4, 8, 1)],
    expect_rd={4: 2}, expect_rf={0: rf0_with()}))
CASES.append(value_case(
    "FI02 ft2it -2.75 -> -2 (truncate toward zero)",
    set_rf(8, FT_N2_75) + [ft2it(4, 8, 1)],
    expect_rd={4: 0xFFFFFFFFFFFFFFFE}))
CASES.append(value_case(
    "FI03 ft2it qNaN -> INT32_MAX + NV",
    set_rf(8, FT_QNAN) + [ft2it(4, 8, 1)],
    expect_rd={4: INT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI04 ft2it +Inf -> INT32_MAX + NV",
    set_rf(8, 0x7F800000) + [ft2it(4, 8, 1)],
    expect_rd={4: INT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI05 ft2it -Inf -> INT32_MIN (sign-extended) + NV",
    set_rf(8, 0xFF800000) + [ft2it(4, 8, 1)],
    expect_rd={4: INT32_MIN_SEXT}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI06 ft2it 3.0e9 overflow -> INT32_MAX + NV",
    set_rf(8, FT_3E9) + [ft2it(4, 8, 1)],
    expect_rd={4: INT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI07 ft2it subnormal 2^-149 -> 0 (no NX)",
    set_rf(8, FT_SUB) + [ft2it(4, 8, 1)],
    expect_rd={4: 0}, expect_rf={0: rf0_with()}))
CASES.append(value_case(
    "FI08 ft2io 2.75 -> 2",
    set_rf(8, FT_2_75) + [ft2io(4, 8, 1)],
    expect_rd={4: 2}))
CASES.append(value_case(
    "FI09 ft2io 3.0e9 -> 3000000000",
    set_rf(8, FT_3E9) + [ft2io(4, 8, 1)],
    expect_rd={4: 3000000000}))
CASES.append(value_case(
    "FI10 ft2io +Inf -> INT64_MAX + NV",
    set_rf(8, 0x7F800000) + [ft2io(4, 8, 1)],
    expect_rd={4: INT64_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI11 ft2io -Inf -> INT64_MIN + NV",
    set_rf(8, 0xFF800000) + [ft2io(4, 8, 1)],
    expect_rd={4: INT64_MIN}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI12 ft2io 1.0e30 overflow -> INT64_MAX + NV",
    set_rf(8, FT_1E30) + [ft2io(4, 8, 1)],
    expect_rd={4: INT64_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI13 ft2ut 2.75 -> 2",
    set_rf(8, FT_2_75) + [ft2ut(4, 8, 1)],
    expect_rd={4: 2}))
CASES.append(value_case(
    "FI14 ft2ut -2.75 -> 0 + NV",
    set_rf(8, FT_N2_75) + [ft2ut(4, 8, 1)],
    expect_rd={4: 0}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI15 ft2ut qNaN -> UINT32_MAX + NV",
    set_rf(8, FT_QNAN) + [ft2ut(4, 8, 1)],
    expect_rd={4: UINT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI16 ft2ut 1.0e10 overflow -> UINT32_MAX + NV",
    set_rf(8, FT_1E10) + [ft2ut(4, 8, 1)],
    expect_rd={4: UINT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI17 ft2uo 2.75 -> 2",
    set_rf(8, FT_2_75) + [ft2uo(4, 8, 1)],
    expect_rd={4: 2}))
CASES.append(value_case(
    "FI18 ft2uo -2.75 -> 0 + NV",
    set_rf(8, FT_N2_75) + [ft2uo(4, 8, 1)],
    expect_rd={4: 0}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI19 ft2uo -Inf -> 0 + NV",
    set_rf(8, 0xFF800000) + [ft2uo(4, 8, 1)],
    expect_rd={4: 0}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI20 ft2uo 1.0e30 overflow -> UINT64_MAX + NV",
    set_rf(8, FT_1E30) + [ft2uo(4, 8, 1)],
    expect_rd={4: UINT64_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI21 fo2it 2.75 -> 2",
    set_rf(8, FO_2_75) + [fo2it(4, 8, 1)],
    expect_rd={4: 2}))
CASES.append(value_case(
    "FI22 fo2it -2.75 -> -2",
    set_rf(8, FO_N2_75) + [fo2it(4, 8, 1)],
    expect_rd={4: 0xFFFFFFFFFFFFFFFE}))
CASES.append(value_case(
    "FI23 fo2it qNaN -> INT32_MAX + NV",
    set_rf(8, FO_QNAN_LOW) + [fo2it(4, 8, 1)],
    expect_rd={4: INT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI24 fo2it +Inf -> INT32_MAX + NV",
    set_rf(8, 0x7FF0000000000000) + [fo2it(4, 8, 1)],
    expect_rd={4: INT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI25 fo2it -Inf -> INT32_MIN sign-extended + NV",
    set_rf(8, 0xFFF0000000000000) + [fo2it(4, 8, 1)],
    expect_rd={4: INT32_MIN_SEXT}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI26 fo2io 2.75 -> 2",
    set_rf(8, FO_2_75) + [fo2io(4, 8, 1)],
    expect_rd={4: 2}))
CASES.append(value_case(
    "FI27 fo2io qNaN -> INT64_MAX + NV",
    set_rf(8, FO_QNAN_LOW) + [fo2io(4, 8, 1)],
    expect_rd={4: INT64_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI28 fo2io 1.0e30 overflow -> INT64_MAX + NV",
    set_rf(8, FO_1E30) + [fo2io(4, 8, 1)],
    expect_rd={4: INT64_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI29 fo2ut 2.75 -> 2",
    set_rf(8, FO_2_75) + [fo2ut(4, 8, 1)],
    expect_rd={4: 2}))
CASES.append(value_case(
    "FI30 fo2ut qNaN -> UINT32_MAX + NV",
    set_rf(8, FO_QNAN_LOW) + [fo2ut(4, 8, 1)],
    expect_rd={4: UINT32_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI31 fo2uo 2.75 -> 2",
    set_rf(8, FO_2_75) + [fo2uo(4, 8, 1)],
    expect_rd={4: 2}))
CASES.append(value_case(
    "FI32 fo2uo qNaN -> UINT64_MAX + NV",
    set_rf(8, FO_QNAN_LOW) + [fo2uo(4, 8, 1)],
    expect_rd={4: UINT64_MAX}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI33 fo2uo -Inf -> 0 + NV",
    set_rf(8, 0xFFF0000000000000) + [fo2uo(4, 8, 1)],
    expect_rd={4: 0}, expect_rf={0: rf0_with(0, NV)}))
CASES.append(value_case(
    "FI34 ft2it block of 3 {rd4:rd6},{rf8:rf10}",
    set_rf(8, FT_2_75) + set_rf(9, 0x40600000) + set_rf(10, 0xBFA00000) +
    [ft2it(4, 8, 3)],
    expect_rd={4: 2, 5: 3, 6: 0xFFFFFFFFFFFFFFFF}))

# ── convert_f2i legality ──────────────────────────────────────────────────
CASES.append(Case("FJ01 ft2it immu6=0 -> ILLI",
                  [ft2it(4, 8, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("FJ02 ft2it dest rd62+4>64 -> ILLI",
                  [ft2it(62, 8, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("FJ03 ft2it src rf62+4>64 -> ILLI",
                  [ft2it(4, 62, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("FJ04 fo2uo immu6=0 -> ILLI",
                  [fo2uo(4, 8, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("FJ05 fo2uo src rf63+2>64 -> ILLI",
                  [fo2uo(4, 63, 2)], expect_exit=ILLI_EXIT))

# ══════════════════════════════════════════════════════════════════════════
#  convert_i2f value cases
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "IF01 it2ft 16 -> 16.0f (no flags)",
    set_rd(8, 16) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x41800000, 0: rf0_with()}))
CASES.append(value_case(
    "IF02 it2ft -16 (rd=all ones..F0) -> -16.0f",
    set_rd(8, 0xFFFFFFFFFFFFFFF0) + [it2ft(4, 8, 1)],
    expect_rf={4: 0xC1800000}))
CASES.append(value_case(
    "IF03 it2ft sign-extends source low 32 bits",
    set_rd(8, 0x00000000FFFFFFF0) + [it2ft(4, 8, 1)],
    expect_rf={4: 0xC1800000}))
CASES.append(value_case(
    "IF04 it2ft 2^24+1 -> RNE 2^24 (NX)",
    set_rd(8, 0x01000001) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x4B800000, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF05 it2ft 2^24+3 -> RNE 2^24+4 (NX)",
    set_rd(8, 0x01000003) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x4B800002, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF06 it2ft 2^24+3 RTZ -> 2^24+2 (NX)",
    set_round_mode(RTZ) + set_rd(8, 0x01000003) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x4B800001, 0: rf0_with(RTZ, NX)}))
CASES.append(value_case(
    "IF07 it2ft 2^24+3 RDN -> 2^24+2 (NX)",
    set_round_mode(RDN) + set_rd(8, 0x01000003) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x4B800001, 0: rf0_with(RDN, NX)}))
CASES.append(value_case(
    "IF08 it2ft 2^24+3 RUP -> 2^24+4 (NX)",
    set_round_mode(RUP) + set_rd(8, 0x01000003) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x4B800002, 0: rf0_with(RUP, NX)}))
CASES.append(value_case(
    "IF09 it2ft 0 -> +0.0f (no flags)",
    set_rd(8, 0) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x00000000, 0: rf0_with()}))
CASES.append(value_case(
    "IF10 io2ft -16 -> -16.0f",
    set_rd(8, 0xFFFFFFFFFFFFFFF0) + [io2ft(4, 8, 1)],
    expect_rf={4: 0xC1800000}))
CASES.append(value_case(
    "IF11 io2ft 2^24+1 -> RNE 2^24 (NX)",
    set_rd(8, 0x01000001) + [io2ft(4, 8, 1)],
    expect_rf={4: 0x4B800000, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF12 ut2ft 0xFFFFFFFF -> 2^32 (NX)",
    set_rd(8, 0xFFFFFFFF) + [ut2ft(4, 8, 1)],
    expect_rf={4: 0x4F800000, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF13 ut2ft 2^28 -> exact (no flags)",
    set_rd(8, 0x10000000) + [ut2ft(4, 8, 1)],
    expect_rf={4: 0x4D800000, 0: rf0_with()}))
CASES.append(value_case(
    "IF14 uo2ft 2^64-1 -> 2^64 (NX)",
    set_rd(8, UINT64_MAX) + [uo2ft(4, 8, 1)],
    expect_rf={4: 0x5F800000, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF15 it2fo -16 -> -16.0d",
    set_rd(8, 0xFFFFFFFFFFFFFFF0) + [it2fo(4, 8, 1)],
    expect_rf={4: 0xC030000000000000}))
CASES.append(value_case(
    "IF16 it2fo INT32_MAX -> exact double (no flags)",
    set_rd(8, INT32_MAX) + [it2fo(4, 8, 1)],
    expect_rf={4: 0x41DFFFFFFFC00000, 0: rf0_with()}))
CASES.append(value_case(
    "IF17 io2fo -16 -> -16.0d",
    set_rd(8, 0xFFFFFFFFFFFFFFF0) + [io2fo(4, 8, 1)],
    expect_rf={4: 0xC030000000000000}))
CASES.append(value_case(
    "IF18 io2fo 2^53+1 -> RNE 2^53 (NX)",
    set_rd(8, 0x0020000000000001) + [io2fo(4, 8, 1)],
    expect_rf={4: 0x4340000000000000, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF19 io2fo 2^53 -> exact (no flags)",
    set_rd(8, 0x0020000000000000) + [io2fo(4, 8, 1)],
    expect_rf={4: 0x4340000000000000, 0: rf0_with()}))
CASES.append(value_case(
    "IF20 ut2fo 0xFFFFFFFF -> 4294967295.0d exact",
    set_rd(8, 0xFFFFFFFF) + [ut2fo(4, 8, 1)],
    expect_rf={4: 0x41EFFFFFFFE00000, 0: rf0_with()}))
CASES.append(value_case(
    "IF21 uo2fo 2^64-1 -> RNE 2^64 (NX)",
    set_rd(8, UINT64_MAX) + [uo2fo(4, 8, 1)],
    expect_rf={4: 0x43F0000000000000, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF22 it2ft block of 3 {rf4:rf6},{rd8:rd10}",
    set_rd(8, 16) + set_rd(9, 0xFFFFFFFFFFFFFFF0) + set_rd(10, 0) +
    [it2ft(4, 8, 3)],
    expect_rf={4: 0x41800000, 5: 0xC1800000, 6: 0x00000000}))
CASES.append(value_case(
    "IF23 it2ft ignores source high 32 bits",
    set_rd(8, 0xDEADBEEF00000010) + [it2ft(4, 8, 1)],
    expect_rf={4: 0x41800000}))
CASES.append(value_case(
    "IF24 uo2ft uses all 64 source bits",
    set_rd(8, UINT64_MAX) + [uo2ft(4, 8, 1)],
    expect_rf={4: 0x5F800000, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "IF25 it2ft source rd0 reads as 0 -> +0.0f",
    [it2ft(4, 0, 1)],
    expect_rf={4: 0x00000000, 0: rf0_with()}))

# ── convert_i2f legality ──────────────────────────────────────────────────
CASES.append(Case("IG01 it2ft dst rf0 -> ILLI",
                  [it2ft(0, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("IG02 it2fo dst rf0 -> ILLI",
                  [it2fo(0, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("IG03 it2ft immu6=0 -> ILLI",
                  [it2ft(4, 8, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("IG04 it2ft dest rf62+4>64 -> ILLI",
                  [it2ft(62, 8, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("IG05 it2ft src rd62+4>64 -> ILLI",
                  [it2ft(4, 62, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("IG06 ut2fo dst rf0 -> ILLI",
                  [ut2fo(0, 8, 1)], expect_exit=ILLI_EXIT))

# ── E2E cases (in-ROM compare + exit port) ────────────────────────────────
_e1 = (set_rf(8, FT_1_5) + [ft2fo(4, 8, 1)] + [rf2rd(20, 4, 1)] +
       load_imm64_rd(22, FO_1_5) + e2e_epilogue([(20, 22, 24)], 0x45))
CASES.append(Case("E1 ft2fo 1.5f -> 1.5d (exit-port assertion)", _e1,
                  expect_exit=PASS_EXIT, e2e=True))

_e2 = (set_rd(8, 16) + [it2ft(4, 8, 1)] + [rf2rd(20, 4, 1)] +
       load_imm64_rd(22, 0x41800000) + e2e_epilogue([(20, 22, 24)], 0x46))
CASES.append(Case("E2 it2ft 16 -> 16.0f (exit-port assertion)", _e2,
                  expect_exit=PASS_EXIT, e2e=True))

_e3 = (set_rf(8, FT_2_75) + [ft2it(4, 8, 1)] +
       load_imm64_rd(22, 2) + e2e_epilogue([(4, 22, 24)], 0x47))
CASES.append(Case("E3 ft2it 2.75 -> 2 (exit-port assertion)", _e3,
                  expect_exit=PASS_EXIT, e2e=True))


# ── Runner ────────────────────────────────────────────────────────────────

def run_case(case):
    """Return (ok, detail_lines)."""
    if case.expect_rf or case.expect_rd:
        rom = build_rom(case.insns)
        code, log = run_dcpu(rom)
        if code != case.expect_exit:
            return False, [f"exit=0x{code & 0xFF:02X} (expect 0x{case.expect_exit:02X})"]
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
        for idx, exp in sorted(case.expect_rd.items()):
            got = last_reg(log, 'RD', idx)
            good = got == exp
            ok = ok and good
            details.append(
                f"RD[{idx:02d}] expect=0x{exp:016X} got="
                f"{'0x%016X' % got if got is not None else 'MISSING'} "
                f"{'OK' if good else 'MISMATCH'}")
        return ok, details
    else:
        if case.e2e:
            rom = build_e2e_rom(case.insns)
        elif case.expect_exit == ILLI_EXIT:
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
    print("QEMU-036t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    results = []

    # 1. RF value comparison (wrong expected rf value)
    c1 = value_case("selftest rf-value",
                    set_rf(8, FT_1) + [ft2fo(4, 8, 1)],
                    expect_rf={4: 0x0000000000000000})
    ok1, _ = run_case(c1)
    results.append(("RF value comparison FAIL path", ok1 is False))

    # 2. RF flags comparison (wrong expected FCSR flags)
    c2 = value_case("selftest rf-flags",
                    set_rf(8, FO_DBL_MAX) + [fo2ft(4, 8, 1)],
                    expect_rf={4: 0x7F800000, 0: rf0_with()})
    ok2, _ = run_case(c2)
    results.append(("FCSR flags comparison FAIL path", ok2 is False))

    # 3. RD value comparison (wrong expected rd value)
    c3 = value_case("selftest rd-value",
                    set_rf(8, FT_2_75) + [ft2it(4, 8, 1)],
                    expect_rd={4: 0})
    ok3, _ = run_case(c3)
    results.append(("RD value comparison FAIL path", ok3 is False))

    # 4. fault case: a legal conversion expected to fault runs to completion and
    #    exits 0 != ILLI, so the (wrong) fault expectation must be detected.
    c4 = Case("selftest fault", [ft2fo(4, 8, 1)], expect_exit=ILLI_EXIT)
    ok4, _ = run_case(c4)
    results.append(("fault exit-code FAIL path", ok4 is False))

    # 5. E2E exit-port assertion (wrong expected -> FAIL arm -> exit != 0)
    insns = (set_rf(8, FT_2_75) + [ft2it(4, 8, 1)] +
             load_imm64_rd(22, 0) + e2e_epilogue([(4, 22, 24)], 0x48))
    c5 = Case("selftest e2e", insns, expect_exit=PASS_EXIT, e2e=True)
    ok5, _ = run_case(c5)
    results.append(("E2E exit-port assertion FAIL path", ok5 is False))

    allok = True
    for name, v in results:
        if not v:
            allok = False
        print(f"  [{'PASS' if v else 'FAIL'}] {name} must be detected as FAIL")

    # Expectation-independence check: re-derive the hard-coded literals from
    # first principles (rational rounding / host struct), without QEMU/LLVM.
    print("  expectation derivation self-check:")
    der = verify_derivations()
    for name, v in der:
        if not v:
            allok = False
        print(f"    [{'PASS' if v else 'FAIL'}] {name}")

    print(f"\nSelf-test: {'PASS' if allok else 'FAIL'}")
    return 0 if allok else 1


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 78)
    print("QEMU-036t Min ROM Probe (FP conversion family, 20 insns, softfloat)")
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
    sys.exit(main())
