#!/usr/bin/env python3
"""Min ROM probe for QEMU-037t: FP softfloat arithmetic + root (14 insns).

Spec sources (expectations derived by hand from these, never from QEMU/LLVM):
  - spec/SimRISC-07 §S2D1 (arith) / §S1D1 (root)
  - spec/SimRISC-00 §浮点寄存器 / §浮点状态寄存器
  - .tao/knowledge/contract-fp.md §1 / §5 / §6 / §16
Encodings: contracts/opcodes.yaml.  Exit codes: ADR-0004 D5.8 (PASS=0x00,
ILLI=0x88).

Instructions under test (14):
  arith (12): ftadd ftsub ftmul ftdiv ftrem ftsclb
              foadd fosub fomul fodiv forem fosclb        (orrr)
  root   (2): ftroot foroot                               (orri, immu6 == 2)

Expected-value provenance (task §6.1):
  * Finite arithmetic results are computed by an in-probe exact-rational
    rounder (fractions.Fraction + round-to-format) for all four rf0 rounding
    modes; no LLVM and no QEMU output is consulted.
  * rem uses the IEEE 754 nearest-quotient / ties-to-even rule derived from
    the exact ratio (3 rem 2 == -1, not fmod's +1).
  * sqrt uses an integer-square-root of the exact operand, rounded to format.
  * NaN / Inf / zero / subnormal edge results are the IEEE 754-defined
    outcomes; the default generated qNaN is the FCSR qNaN pattern
    (0x7FC00000 / 0x7FF8000000000000).
  * rootn(-0, 2) is explicitly UNSPECIFIED by spec §S1D1/§16: only the
    no-fault / flag behaviour is asserted, never the result value.

Verification channels (same as min_rom_probe_034t/035t/036t):
  * value cases -> QEMU `-d cpu` dump, parsing the *last* RF[] dump.
  * fault cases -> process exit code (ILLI 0x88).
  * E2E cases   -> in-ROM compare + SYS_EXIT PASS epilogue.

Reverse gate (.work/evidence/QEMU-037t/run.sh --inject) injects individually
attributed regressions into the implementation and requires the matching
cases to FAIL.
"""
import math
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
DZ = 0x02
OF = 0x04
UF = 0x08
NX = 0x10
FLAG_OF_NX = OF | NX
FLAG_UF_NX = UF | NX

ILLI = 0x77000000
SWYM = 0x77880000

# rf0[33:32] rounding mode selectors (SimRISC-00 §浮点状态寄存器)
RNE, RTZ, RDN, RUP = 0, 1, 2, 3

# ── Instruction encoding (op / ha from contracts/opcodes.yaml) ────────────


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


def encode_orrr(op, ha, hb, hc, hd):
    return encode_orri(op, ha, hb, hc, hd)


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
# arith: orrr, op 0x44, hb = dest, hc/hd = sources.

def ftadd(hb, hc, hd):
    return encode_orrr(0x44, 0x10, hb, hc, hd)


def ftsub(hb, hc, hd):
    return encode_orrr(0x44, 0x11, hb, hc, hd)


def ftmul(hb, hc, hd):
    return encode_orrr(0x44, 0x12, hb, hc, hd)


def ftdiv(hb, hc, hd):
    return encode_orrr(0x44, 0x13, hb, hc, hd)


def ftrem(hb, hc, hd):
    return encode_orrr(0x44, 0x14, hb, hc, hd)


def ftsclb(hb, hc, hd):
    return encode_orrr(0x44, 0x15, hb, hc, hd)


def foadd(hb, hc, hd):
    return encode_orrr(0x44, 0x18, hb, hc, hd)


def fosub(hb, hc, hd):
    return encode_orrr(0x44, 0x19, hb, hc, hd)


def fomul(hb, hc, hd):
    return encode_orrr(0x44, 0x1A, hb, hc, hd)


def fodiv(hb, hc, hd):
    return encode_orrr(0x44, 0x1B, hb, hc, hd)


def forem(hb, hc, hd):
    return encode_orrr(0x44, 0x1C, hb, hc, hd)


def fosclb(hb, hc, hd):
    return encode_orrr(0x44, 0x1D, hb, hc, hd)


# root: orri, op 0x44, hb = dest, hc = source, hd = n

def ftroot(hb, hc, n):
    return encode_orri(0x44, 0x06, hb, hc, n)


def foroot(hb, hc, n):
    return encode_orri(0x44, 0x0E, hb, hc, n)


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


# ── Semihosting SYS_EXIT (ADR-0020 D8: replaces the legacy MMIO halt device) ──

SEMI_BLOCK = 0x0000_00FF_F000       # argument block {reason, code}, in RAM
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026


def trap_ciii(cfxha, immu18):
    return encode_riii(0x7F, cfxha, immu18 & 0x3FFFF)


def semi_exit(code_rd):
    """rb16 = SEMI_BLOCK; block = {0x20026, code_rd}; rd16 = 0x18; trap."""
    return ([set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF), or_w_rb(16, 0, 0xF000)]
            + load_imm64_rd(8, ADP_STOPPED_APPLICATION_EXIT)
            + [st_o_rd(8, 16, 0)]
            + [st_o_rd(code_rd, 16, 8)]
            + load_imm64_rd(16, 0x18)
            + [trap_ciii(0, SEMIHOST_TAG)])


def set_rd(rd, val):
    return load_imm64_rd(rd, val)


def set_round_mode(mode):
    """Set rf0[33:32] via rd2rf(rf0) — goes through the FCSR write mask."""
    return set_rf(0, mode << 32)


def rf0_with(mode=0, flags=0):
    return RESET0 | (mode << 32) | flags


# ── ROM assembly ──────────────────────────────────────────────────────────

TRAMPOLINE = [
    set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),  # rb16 = 0x00000000FF0000 (dead; semi_exit rebuilds it)
    set_zw_rb(17, 0, 0x0000),                          # rb17 = 0x000000000000
    encode_rwii(0x4C, 40, 0, 0x0001),                  # rd40 = 1 (TB-split branch)
]


def build_rom(test_insns):
    rom = b''.join(TRAMPOLINE) + b''.join(test_insns) + struct.pack('>I', ILLI)
    while len(rom) < 64:
        rom += struct.pack('>I', SWYM)
    return rom


def build_fault_rom(test_insns):
    """Body + PASS epilogue: a missing fault exits 0x00 != 0x88."""
    return (b''.join(TRAMPOLINE) + b''.join(test_insns) +
            b''.join([set_zw_rd(18, 0)] + semi_exit(18)))


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
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp, '-semihosting-config', 'enable=on,target=native'],
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


def last_reg(log_text, bank, idx):
    pat = re.compile(r'%s\[%02d\]:\s*([0-9a-fA-F]{16})' % (bank, idx))
    m = None
    for mm in pat.finditer(log_text):
        m = mm
    return int(m.group(1), 16) if m else None


def e2e_epilogue(checks, fail_code):
    """checks: list of (actual_rd, expected_rd, flag_rd)."""
    N = len(checks)
    pass_arm = [set_zw_rd(18, 0)] + semi_exit(18)             # PASS: exit 0
    fail_arm = [set_zw_rd(19, fail_code)] + semi_exit(19)     # FAIL: exit fail_code
    P = len(pass_arm)
    insns = []
    for i, (actual, expected, flag) in enumerate(checks):
        offset = 2 * (N - i) + (P - 1)
        insns.append(cmp_uo_rd(flag, actual, expected))
        insns.append(br_nz(flag, offset))
    insns += pass_arm
    insns += fail_arm
    return insns


# ══════════════════════════════════════════════════════════════════════════
#  Independent exact-rational oracle (no LLVM, no QEMU)
# ══════════════════════════════════════════════════════════════════════════

def _f32v(bits):
    s = (bits >> 31) & 1
    e = (bits >> 23) & 0xFF
    m = bits & 0x7FFFFF
    if e == 0xFF:
        return s, None, m != 0
    if e == 0:
        return s, Fraction(m, 2 ** 149), False
    return s, Fraction((1 << 23) | m, 2 ** 23) * Fraction(2) ** (e - 127), False


def _f64v(bits):
    s = (bits >> 63) & 1
    e = (bits >> 52) & 0x7FF
    m = bits & ((1 << 52) - 1)
    if e == 0x7FF:
        return s, None, m != 0
    if e == 0:
        return s, Fraction(m, 2 ** 1074), False
    return s, Fraction((1 << 52) | m, 2 ** 52) * Fraction(2) ** (e - 1023), False


def _round_bits(sign, value, ebits, fbits, mode):
    """Round non-negative Fraction `value` to IEEE bits with `sign`."""
    emin = 1 - (2 ** (ebits - 1) - 2)
    maxexp = 2 ** ebits - 1
    bias = 2 ** (ebits - 1) - 1
    if value == 0:
        return sign << (ebits + fbits)
    k = value.numerator.bit_length() - value.denominator.bit_length()
    if Fraction(2) ** k > value:
        k -= 1
    while Fraction(2) ** (k + 1) <= value:
        k += 1
    if k < emin:
        unit, e = Fraction(1, 2 ** (fbits - emin)), 0
    else:
        unit, e = Fraction(2) ** (k - fbits), k + bias
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
    if e == 0:
        if r >= (1 << fbits):
            e, r = 1, r - (1 << fbits)
        if r == 0:
            return sign << (ebits + fbits)
        return (sign << (ebits + fbits)) | r
    if r >= (1 << (fbits + 1)):
        r >>= 1
        e += 1
    if e >= maxexp:
        return (sign << (ebits + fbits)) | (maxexp << fbits)
    return (sign << (ebits + fbits)) | (e << fbits) | (r - (1 << fbits))


def rb32(sign, value, mode='nearest_even'):
    return _round_bits(sign, value, 8, 23, mode)


def rb64(sign, value, mode='nearest_even'):
    return _round_bits(sign, value, 11, 52, mode)


def _sqrt_frac(v, extra=90):
    num = v.numerator * (1 << (2 * extra))
    r = math.isqrt(num // v.denominator)
    return Fraction(r, 1 << extra)


def _rem_exact(x, y):
    """IEEE 754 remainder: x - n*y, n = nearest integer to x/y, ties to even."""
    q = x / y
    fl = q.numerator // q.denominator
    if q.denominator == 1:
        n = q.numerator
    else:
        frac = q - fl
        if frac < Fraction(1, 2):
            n = fl
        elif frac > Fraction(1, 2):
            n = fl + 1
        else:
            n = fl if fl % 2 == 0 else fl + 1
    return x - n * y


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
    body = list(insns) + [br_nz(40, 1)]        # rd40=1 -> taken to ILLI, TB split
    return Case(name, body, expect_exit=ILLI_EXIT,
                expect_rf=expect_rf, expect_rd=expect_rd)


# ══════════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════════

# ft (float32)
F0 = 0x00000000
FN0 = 0x80000000
F0_5 = 0x3F000000
F0_75 = 0x3F400000
F2_5 = 0x40200000
F1 = 0x3F800000
FN1 = 0xBF800000
F1_5 = 0x3FC00000
F2 = 0x40000000
F3 = 0x40400000
F4 = 0x40800000
F5 = 0x40A00000
F12 = 0x41400000
FMAX = 0x7F7FFFFF
FNMAX = 0xFF7FFFFF
FINF = 0x7F800000
FNINF = 0xFF800000
FQNAN = 0x7FC00000
FSNAN = 0x7F800001
FSUBMIN = 0x00000001               # 2^-149
FTIE = 0x33800000                  # 2^-24 (halfway at 1.0)
FABOVE = 0x33C00000                # 3*2^-25 (0.75 ulp above 1.0)
FABOVE_N = 0xB3C00000
FSQRT2 = 0x3FB504F3

# fo (float64)
D0 = 0x0000000000000000
D0_5 = 0x3FE0000000000000
D0_75 = 0x3FE8000000000000
D1 = 0x3FF0000000000000
DN1 = 0xBFF0000000000000
D1_5 = 0x3FF8000000000000
D2 = 0x4000000000000000
D3 = 0x4008000000000000
D4 = 0x4010000000000000
D5 = 0x4014000000000000
D12 = 0x4028000000000000
DMAX = 0x7FEFFFFFFFFFFFFF
DNMAX = 0xFFEFFFFFFFFFFFFF
DINF = 0x7FF0000000000000
DQNAN = 0x7FF8000000000000
DSNAN = 0x7FF0000000000001
DSUBMIN = 0x0000000000000001       # 2^-1074
DABOVE = 0x3CA8000000000000        # 3*2^-54 (0.75 ulp above 1.0)
DABOVE_N = 0xBCA8000000000000
DSQRT2 = 0x3FF6A09E667F3BCD

CASES = []

# ══════════════════════════════════════════════════════════════════════════
#  arith: normal operands (exact results)
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "AR01 ftadd 1.0+2.0 = 3.0 (exact, no flags)",
    set_rf(8, F1) + set_rf(9, F2) + [ftadd(4, 8, 9)],
    expect_rf={4: F3, 0: rf0_with()}))
CASES.append(value_case(
    "AR02 ftsub 5.0-2.0 = 3.0",
    set_rf(8, F5) + set_rf(9, F2) + [ftsub(4, 8, 9)],
    expect_rf={4: F3}))
CASES.append(value_case(
    "AR03 ftmul 1.5*2.0 = 3.0",
    set_rf(8, F1_5) + set_rf(9, F2) + [ftmul(4, 8, 9)],
    expect_rf={4: F3}))
CASES.append(value_case(
    "AR04 ftdiv 3.0/2.0 = 1.5",
    set_rf(8, F3) + set_rf(9, F2) + [ftdiv(4, 8, 9)],
    expect_rf={4: F1_5}))
CASES.append(value_case(
    "AR05 foadd 1.0+2.0 = 3.0",
    set_rf(8, D1) + set_rf(9, D2) + [foadd(4, 8, 9)],
    expect_rf={4: D3, 0: rf0_with()}))
CASES.append(value_case(
    "AR06 fosub 5.0-2.0 = 3.0",
    set_rf(8, D5) + set_rf(9, D2) + [fosub(4, 8, 9)],
    expect_rf={4: D3}))
CASES.append(value_case(
    "AR07 fomul 1.5*2.0 = 3.0",
    set_rf(8, D1_5) + set_rf(9, D2) + [fomul(4, 8, 9)],
    expect_rf={4: D3}))
CASES.append(value_case(
    "AR08 fodiv 3.0/2.0 = 1.5",
    set_rf(8, D3) + set_rf(9, D2) + [fodiv(4, 8, 9)],
    expect_rf={4: D1_5}))

# ── four rf0 rounding modes (all four results pairwise distinct) ──────────
CASES.append(value_case(
    "AR09 ftadd RNE 1.0+FABOVE -> up (0x3F800001) + NX",
    set_round_mode(RNE) + set_rf(8, F1) + set_rf(9, FABOVE) + [ftadd(4, 8, 9)],
    expect_rf={4: 0x3F800001, 0: rf0_with(RNE, NX)}))
CASES.append(value_case(
    "AR10 ftadd RTZ 1.0+FABOVE -> down (0x3F800000) + NX",
    set_round_mode(RTZ) + set_rf(8, F1) + set_rf(9, FABOVE) + [ftadd(4, 8, 9)],
    expect_rf={4: F1, 0: rf0_with(RTZ, NX)}))
CASES.append(value_case(
    "AR11 ftadd RDN -1.0+(-FABOVE) -> -1.0000001 + NX",
    set_round_mode(RDN) + set_rf(8, FN1) + set_rf(9, FABOVE_N) + [ftadd(4, 8, 9)],
    expect_rf={4: 0xBF800001, 0: rf0_with(RDN, NX)}))
CASES.append(value_case(
    "AR12 ftadd RUP -1.0+(-FABOVE) -> -1.0 + NX",
    set_round_mode(RUP) + set_rf(8, FN1) + set_rf(9, FABOVE_N) + [ftadd(4, 8, 9)],
    expect_rf={4: FN1, 0: rf0_with(RUP, NX)}))
CASES.append(value_case(
    "AR13 foadd RNE 1.0+DABOVE -> up + NX",
    set_round_mode(RNE) + set_rf(8, D1) + set_rf(9, DABOVE) + [foadd(4, 8, 9)],
    expect_rf={4: 0x3FF0000000000001, 0: rf0_with(RNE, NX)}))
CASES.append(value_case(
    "AR14 foadd RTZ 1.0+DABOVE -> down + NX",
    set_round_mode(RTZ) + set_rf(8, D1) + set_rf(9, DABOVE) + [foadd(4, 8, 9)],
    expect_rf={4: D1, 0: rf0_with(RTZ, NX)}))
CASES.append(value_case(
    "AR15 foadd RDN -1.0+(-DABOVE) -> -1.000...1 + NX",
    set_round_mode(RDN) + set_rf(8, DN1) + set_rf(9, DABOVE_N) + [foadd(4, 8, 9)],
    expect_rf={4: 0xBFF0000000000001, 0: rf0_with(RDN, NX)}))
CASES.append(value_case(
    "AR16 foadd RUP -1.0+(-DABOVE) -> -1.0 + NX",
    set_round_mode(RUP) + set_rf(8, DN1) + set_rf(9, DABOVE_N) + [foadd(4, 8, 9)],
    expect_rf={4: DN1, 0: rf0_with(RUP, NX)}))

# ── divide by zero / invalid / overflow / underflow ───────────────────────
CASES.append(value_case(
    "AR17 ftdiv 1.0/0.0 -> +Inf + DZ",
    set_rf(8, F1) + set_rf(9, F0) + [ftdiv(4, 8, 9)],
    expect_rf={4: FINF, 0: rf0_with(0, DZ)}))
CASES.append(value_case(
    "AR18 ftdiv -1.0/0.0 -> -Inf + DZ",
    set_rf(8, FN1) + set_rf(9, F0) + [ftdiv(4, 8, 9)],
    expect_rf={4: FNINF, 0: rf0_with(0, DZ)}))
CASES.append(value_case(
    "AR19 ftdiv 1.0/-0.0 -> -Inf + DZ",
    set_rf(8, F1) + set_rf(9, FN0) + [ftdiv(4, 8, 9)],
    expect_rf={4: FNINF, 0: rf0_with(0, DZ)}))
CASES.append(value_case(
    "AR20 fodiv 1.0/0.0 -> +Inf + DZ",
    set_rf(8, D1) + set_rf(9, D0) + [fodiv(4, 8, 9)],
    expect_rf={4: DINF, 0: rf0_with(0, DZ)}))
CASES.append(value_case(
    "AR21 ftdiv 0.0/0.0 -> qNaN + NV",
    set_rf(8, F0) + set_rf(9, F0) + [ftdiv(4, 8, 9)],
    expect_rf={4: FQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "AR22 ftsub Inf-Inf -> qNaN + NV",
    set_rf(8, FINF) + set_rf(9, FINF) + [ftsub(4, 8, 9)],
    expect_rf={4: FQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "AR23 ftmul Inf*0.0 -> qNaN + NV",
    set_rf(8, FINF) + set_rf(9, F0) + [ftmul(4, 8, 9)],
    expect_rf={4: FQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "AR24 fodiv 0.0/0.0 -> qNaN + NV",
    set_rf(8, D0) + set_rf(9, D0) + [fodiv(4, 8, 9)],
    expect_rf={4: DQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "AR25 foadd Inf+(-Inf) -> qNaN + NV",
    set_rf(8, DINF) + set_rf(9, 0xFFF0000000000000) + [foadd(4, 8, 9)],
    expect_rf={4: DQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "AR26 fomul Inf*0.0 -> qNaN + NV",
    set_rf(8, DINF) + set_rf(9, D0) + [fomul(4, 8, 9)],
    expect_rf={4: DQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "AR27 ftadd FLT_MAX+FLT_MAX -> +Inf + OF|NX",
    set_rf(8, FMAX) + set_rf(9, FMAX) + [ftadd(4, 8, 9)],
    expect_rf={4: FINF, 0: rf0_with(0, FLAG_OF_NX)}))
CASES.append(value_case(
    "AR28 ftadd -FLT_MAX+-FLT_MAX -> -Inf + OF|NX",
    set_rf(8, FNMAX) + set_rf(9, FNMAX) + [ftadd(4, 8, 9)],
    expect_rf={4: FNINF, 0: rf0_with(0, FLAG_OF_NX)}))
CASES.append(value_case(
    "AR29 foadd DBL_MAX+DBL_MAX -> +Inf + OF|NX",
    set_rf(8, DMAX) + set_rf(9, DMAX) + [foadd(4, 8, 9)],
    expect_rf={4: DINF, 0: rf0_with(0, FLAG_OF_NX)}))
CASES.append(value_case(
    "AR30 ftmul 2^-149 * 0.5 -> +0 + UF|NX",
    set_rf(8, FSUBMIN) + set_rf(9, F0_5) + [ftmul(4, 8, 9)],
    expect_rf={4: F0, 0: rf0_with(0, FLAG_UF_NX)}))
CASES.append(value_case(
    "AR31 fomul 2^-1074 * 0.5 -> +0 + UF|NX",
    set_rf(8, DSUBMIN) + set_rf(9, D0_5) + [fomul(4, 8, 9)],
    expect_rf={4: D0, 0: rf0_with(0, FLAG_UF_NX)}))

# ══════════════════════════════════════════════════════════════════════════
#  rem
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "RE01 ftrem 5.0 rem 2.0 = 1.0",
    set_rf(8, F5) + set_rf(9, F2) + [ftrem(4, 8, 9)],
    expect_rf={4: F1, 0: rf0_with()}))
CASES.append(value_case(
    "RE02 ftrem 3.0 rem 2.0 = -1.0 (tie-to-even; fmod would give +1)",
    set_rf(8, F3) + set_rf(9, F2) + [ftrem(4, 8, 9)],
    expect_rf={4: FN1, 0: rf0_with()}))
CASES.append(value_case(
    "RE03 ftrem 2.5 rem 1.0 = 0.5 (non-tie quotient)",
    set_rf(8, F2_5) + set_rf(9, F1) + [ftrem(4, 8, 9)],
    expect_rf={4: F0_5}))
CASES.append(value_case(
    "RE04 ftrem -5.0 rem 2.0 = -1.0 (result sign = dividend)",
    set_rf(8, 0xC0A00000) + set_rf(9, F2) + [ftrem(4, 8, 9)],
    expect_rf={4: FN1}))
CASES.append(value_case(
    "RE05 ftrem 1.0 rem 0.0 -> qNaN + NV (IEEE invalid, not DZ)",
    set_rf(8, F1) + set_rf(9, F0) + [ftrem(4, 8, 9)],
    expect_rf={4: FQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "RE06 ftrem Inf rem 2.0 -> qNaN + NV",
    set_rf(8, FINF) + set_rf(9, F2) + [ftrem(4, 8, 9)],
    expect_rf={4: FQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "RE07 ftrem 3.0 rem Inf = 3.0 (no flags)",
    set_rf(8, F3) + set_rf(9, FINF) + [ftrem(4, 8, 9)],
    expect_rf={4: F3, 0: rf0_with()}))
CASES.append(value_case(
    "RE08 ftrem 0.0 rem 3.0 = +0.0",
    set_rf(8, F0) + set_rf(9, F3) + [ftrem(4, 8, 9)],
    expect_rf={4: F0, 0: rf0_with()}))
CASES.append(value_case(
    "RE09 forem 5.0 rem 2.0 = 1.0",
    set_rf(8, D5) + set_rf(9, D2) + [forem(4, 8, 9)],
    expect_rf={4: D1}))
CASES.append(value_case(
    "RE10 forem 3.0 rem 2.0 = -1.0 (tie-to-even)",
    set_rf(8, D3) + set_rf(9, D2) + [forem(4, 8, 9)],
    expect_rf={4: DN1}))
CASES.append(value_case(
    "RE11 forem 1.0 rem 0.0 -> qNaN + NV",
    set_rf(8, D1) + set_rf(9, D0) + [forem(4, 8, 9)],
    expect_rf={4: DQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "RE12 forem Inf rem 2.0 -> qNaN + NV",
    set_rf(8, DINF) + set_rf(9, D2) + [forem(4, 8, 9)],
    expect_rf={4: DQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "RE13 forem 3.0 rem Inf = 3.0",
    set_rf(8, D3) + set_rf(9, DINF) + [forem(4, 8, 9)],
    expect_rf={4: D3}))

# ══════════════════════════════════════════════════════════════════════════
#  scalb  (rfHD is an integer-valued float; n is that integer)
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "SC01 ftsclb 3.0 * 2^2 = 12.0",
    set_rf(8, F3) + set_rf(9, F2) + [ftsclb(4, 8, 9)],
    expect_rf={4: F12, 0: rf0_with()}))
CASES.append(value_case(
    "SC02 ftsclb 3.0 * 2^-2 = 0.75 (negative n)",
    set_rf(8, F3) + set_rf(9, 0xC0000000) + [ftsclb(4, 8, 9)],
    expect_rf={4: F0_75}))
CASES.append(value_case(
    "SC03 ftsclb 1.0 * 2^200 -> +Inf + OF|NX",
    set_rf(8, F1) + set_rf(9, 0x43480000) + [ftsclb(4, 8, 9)],
    expect_rf={4: FINF, 0: rf0_with(0, FLAG_OF_NX)}))
CASES.append(value_case(
    "SC04 ftsclb 1.0 * 2^-200 -> +0 + UF|NX",
    set_rf(8, F1) + set_rf(9, 0xC3480000) + [ftsclb(4, 8, 9)],
    expect_rf={4: F0, 0: rf0_with(0, FLAG_UF_NX)}))
CASES.append(value_case(
    "SC05 ftsclb 0.0 * 2^5 = +0.0 (no flags)",
    set_rf(8, F0) + set_rf(9, 0x40A00000) + [ftsclb(4, 8, 9)],
    expect_rf={4: F0, 0: rf0_with()}))
CASES.append(value_case(
    "SC06 ftsclb -0.0 * 2^5 = -0.0 (sign preserved)",
    set_rf(8, FN0) + set_rf(9, 0x40A00000) + [ftsclb(4, 8, 9)],
    expect_rf={4: FN0, 0: rf0_with()}))
CASES.append(value_case(
    "SC07 ftsclb Inf * 2^5 = +Inf (no flags)",
    set_rf(8, FINF) + set_rf(9, 0x40A00000) + [ftsclb(4, 8, 9)],
    expect_rf={4: FINF, 0: rf0_with()}))
CASES.append(value_case(
    "SC08 fosclb 3.0 * 2^2 = 12.0",
    set_rf(8, D3) + set_rf(9, D2) + [fosclb(4, 8, 9)],
    expect_rf={4: D12, 0: rf0_with()}))
CASES.append(value_case(
    "SC09 fosclb 3.0 * 2^-2 = 0.75 (negative n)",
    set_rf(8, D3) + set_rf(9, 0xC000000000000000) + [fosclb(4, 8, 9)],
    expect_rf={4: D0_75}))
CASES.append(value_case(
    "SC10 fosclb 1.0 * 2^2000 -> +Inf + OF|NX",
    set_rf(8, D1) + set_rf(9, 0x409F400000000000) + [fosclb(4, 8, 9)],
    expect_rf={4: DINF, 0: rf0_with(0, FLAG_OF_NX)}))
CASES.append(value_case(
    "SC11 fosclb 1.0 * 2^-2000 -> +0 + UF|NX",
    set_rf(8, D1) + set_rf(9, 0xC09F400000000000) + [fosclb(4, 8, 9)],
    expect_rf={4: D0, 0: rf0_with(0, FLAG_UF_NX)}))
CASES.append(value_case(
    "SC12 fosclb 0.0 * 2^5 = +0.0 (no flags)",
    set_rf(8, D0) + set_rf(9, 0x4014000000000000) + [fosclb(4, 8, 9)],
    expect_rf={4: D0, 0: rf0_with()}))

# ══════════════════════════════════════════════════════════════════════════
#  root (rootn(x, 2) == sqrt)
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "RO01 ftroot 4.0 -> 2.0 (exact, no flags)",
    set_rf(8, F4) + [ftroot(4, 8, 2)],
    expect_rf={4: F2, 0: rf0_with()}))
CASES.append(value_case(
    "RO02 ftroot 2.0 -> 0x3FB504F3 + NX",
    set_rf(8, F2) + [ftroot(4, 8, 2)],
    expect_rf={4: FSQRT2, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "RO03 ftroot -4.0 -> qNaN + NV",
    set_rf(8, 0xC0800000) + [ftroot(4, 8, 2)],
    expect_rf={4: FQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "RO04 ftroot +Inf -> +Inf (no flags)",
    set_rf(8, FINF) + [ftroot(4, 8, 2)],
    expect_rf={4: FINF, 0: rf0_with()}))
CASES.append(value_case(
    "RO05 ftroot +0.0 -> +0.0",
    set_rf(8, F0) + [ftroot(4, 8, 2)],
    expect_rf={4: F0, 0: rf0_with()}))
CASES.append(value_case(
    "RO06 ftroot -0.0 -> UNSPECIFIED value; only no-fault/flags asserted",
    set_rf(8, FN0) + [ftroot(4, 8, 2)],
    expect_rf={0: rf0_with()}))
CASES.append(value_case(
    "RO07 foroot 4.0 -> 2.0 (exact)",
    set_rf(8, D4) + [foroot(4, 8, 2)],
    expect_rf={4: D2, 0: rf0_with()}))
CASES.append(value_case(
    "RO08 foroot 2.0 -> 0x3FF6A09E667F3BCD + NX",
    set_rf(8, D2) + [foroot(4, 8, 2)],
    expect_rf={4: DSQRT2, 0: rf0_with(0, NX)}))
CASES.append(value_case(
    "RO09 foroot -4.0 -> qNaN + NV",
    set_rf(8, 0xC010000000000000) + [foroot(4, 8, 2)],
    expect_rf={4: DQNAN, 0: rf0_with(0, NV)}))
CASES.append(value_case(
    "RO10 foroot +Inf -> +Inf",
    set_rf(8, DINF) + [foroot(4, 8, 2)],
    expect_rf={4: DINF, 0: rf0_with()}))

# root n != 2 -> ILLI (encode_fp_root_n)
CASES.append(Case("RO11 ftroot n=1 -> ILLI", [ftroot(4, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("RO12 ftroot n=3 -> ILLI", [ftroot(4, 8, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("RO13 ftroot n=0 -> ILLI", [ftroot(4, 8, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("RO14 foroot n=3 -> ILLI", [foroot(4, 8, 3)], expect_exit=ILLI_EXIT))
CASES.append(Case("RO15 foroot n=1 -> ILLI", [foroot(4, 8, 1)], expect_exit=ILLI_EXIT))
CASES.append(Case("RO16 ftroot dst rf0 -> ILLI", [ftroot(0, 8, 2)], expect_exit=ILLI_EXIT))
CASES.append(Case("RO17 foroot dst rf0 -> ILLI", [foroot(0, 8, 2)], expect_exit=ILLI_EXIT))

# ══════════════════════════════════════════════════════════════════════════
#  dst_rf0: one case per instruction (all 14)
# ══════════════════════════════════════════════════════════════════════════

CASES.append(Case("DR01 ftadd dst rf0 -> ILLI", [ftadd(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR02 ftsub dst rf0 -> ILLI", [ftsub(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR03 ftmul dst rf0 -> ILLI", [ftmul(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR04 ftdiv dst rf0 -> ILLI", [ftdiv(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR05 ftrem dst rf0 -> ILLI", [ftrem(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR06 ftsclb dst rf0 -> ILLI", [ftsclb(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR07 foadd dst rf0 -> ILLI", [foadd(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR08 fosub dst rf0 -> ILLI", [fosub(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR09 fomul dst rf0 -> ILLI", [fomul(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR10 fodiv dst rf0 -> ILLI", [fodiv(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR11 forem dst rf0 -> ILLI", [forem(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR12 fosclb dst rf0 -> ILLI", [fosclb(0, 8, 9)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR13 ftroot dst rf0 -> ILLI", [ftroot(0, 8, 2)], expect_exit=ILLI_EXIT))
CASES.append(Case("DR14 foroot dst rf0 -> ILLI", [foroot(0, 8, 2)], expect_exit=ILLI_EXIT))

# ══════════════════════════════════════════════════════════════════════════
#  read-before-write (source aliases destination)
# ══════════════════════════════════════════════════════════════════════════

CASES.append(value_case(
    "RW01 ftadd rf4,rf4,rf5 reads old rf4 (3+2=5), rf5 untouched",
    set_rf(4, F3) + set_rf(5, F2) + [ftadd(4, 4, 5)],
    expect_rf={4: F5, 5: F2, 0: rf0_with()}))
CASES.append(value_case(
    "RW02 ftadd rf5,rf4,rf5 reads old rf5 (3+2=5)",
    set_rf(4, F3) + set_rf(5, F2) + [ftadd(5, 4, 5)],
    expect_rf={4: F3, 5: F5}))

# ══════════════════════════════════════════════════════════════════════════
#  E2E (in-ROM compare + SYS_EXIT)
# ══════════════════════════════════════════════════════════════════════════

_e1 = (set_rf(8, F1) + set_rf(9, F2) + [ftadd(4, 8, 9)] + [rf2rd(20, 4, 1)] +
       load_imm64_rd(22, F3) + e2e_epilogue([(20, 22, 24)], 0x45))
CASES.append(Case("E1 ftadd 1+2=3 (SYS_EXIT assertion)", _e1,
                  expect_exit=PASS_EXIT, e2e=True))

_e2 = (set_rf(8, F4) + [ftroot(4, 8, 2)] + [rf2rd(20, 4, 1)] +
       load_imm64_rd(22, F2) + e2e_epilogue([(20, 22, 24)], 0x46))
CASES.append(Case("E2 ftroot 4->2 (SYS_EXIT assertion)", _e2,
                  expect_exit=PASS_EXIT, e2e=True))


# ══════════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════════

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


# ── Independent derivation self-check ─────────────────────────────────────
#
# Recompute the hard-coded finite value literals from first principles
# (exact rationals / integer sqrt) for all four rounding modes.  If a literal
# were copied from QEMU/LLVM this check would reveal it.

def verify_derivations():
    checks = []

    def chk(label, got, want=True):
        checks.append((label, got == want))

    # operand patterns decode to the intended exact values
    chk("FABOVE == 3*2^-25", _f32v(FABOVE)[1] == Fraction(3, 2 ** 25))
    chk("DABOVE == 3*2^-54", _f64v(DABOVE)[1] == Fraction(3, 2 ** 54))
    chk("FTIE == 2^-24", _f32v(FTIE)[1] == Fraction(1, 2 ** 24))
    chk("FSUBMIN == 2^-149", _f32v(FSUBMIN)[1] == Fraction(1, 2 ** 149))
    chk("DSUBMIN == 2^-1074", _f64v(DSUBMIN)[1] == Fraction(1, 2 ** 1074))

    # arith normal
    chk("1+2 ft", rb32(0, Fraction(3)), F3)
    chk("5-2 ft", rb32(0, Fraction(3)), F3)
    chk("1.5*2 ft", rb32(0, Fraction(3)), F3)
    chk("3/2 ft", rb32(0, Fraction(3, 2)), F1_5)
    chk("1+2 fo", rb64(0, Fraction(3)), D3)
    chk("3/2 fo", rb64(0, Fraction(3, 2)), D1_5)

    # four rounding modes, mixed signs => four distinct patterns
    chk("RNE 1+above ft", rb32(0, 1 + Fraction(3, 2 ** 25), 'nearest_even'), 0x3F800001)
    chk("RTZ 1+above ft", rb32(0, 1 + Fraction(3, 2 ** 25), 'to_zero'), F1)
    chk("RDN -(1+above) ft", rb32(1, 1 + Fraction(3, 2 ** 25), 'down'), 0xBF800001)
    chk("RUP -(1+above) ft", rb32(1, 1 + Fraction(3, 2 ** 25), 'up'), FN1)
    chk("RNE 1+above fo", rb64(0, 1 + Fraction(3, 2 ** 54), 'nearest_even'),
        0x3FF0000000000001)
    chk("RTZ 1+above fo", rb64(0, 1 + Fraction(3, 2 ** 54), 'to_zero'), D1)
    chk("RDN -(1+above) fo", rb64(1, 1 + Fraction(3, 2 ** 54), 'down'),
        0xBFF0000000000001)
    chk("RUP -(1+above) fo", rb64(1, 1 + Fraction(3, 2 ** 54), 'up'), DN1)

    # overflow / underflow literals
    chk("FLT_MAX == (2-2^-23)*2^127",
        _f32v(FMAX)[1] == Fraction((1 << 24) - 1, 2 ** 23) * Fraction(2) ** 127)
    chk("DBL_MAX == (2-2^-52)*2^1023",
        _f64v(DMAX)[1] == Fraction((1 << 53) - 1, 2 ** 52) * Fraction(2) ** 1023)

    # rem: exact nearest-quotient ties-to-even
    chk("5 rem 2 = 1", _rem_exact(Fraction(5), Fraction(2)) == 1)
    chk("3 rem 2 = -1", _rem_exact(Fraction(3), Fraction(2)) == -1)
    chk("2.5 rem 1 = 0.5", _rem_exact(Fraction(5, 2), Fraction(1)) == Fraction(1, 2))
    chk("-5 rem 2 = -1", _rem_exact(Fraction(-5), Fraction(2)) == -1)
    chk("3 rem 2 fo = -1", rb64(1, abs(_rem_exact(Fraction(3), Fraction(2)))),
        DN1)

    # scalb exact values
    chk("3*2^2", rb32(0, Fraction(3) * Fraction(2) ** 2), F12)
    chk("3*2^-2", rb32(0, Fraction(3) * Fraction(2) ** -2), F0_75)
    chk("3*2^2 fo", rb64(0, Fraction(3) * Fraction(2) ** 2), D12)
    chk("3*2^-2 fo", rb64(0, Fraction(3) * Fraction(2) ** -2), D0_75)

    # sqrt
    chk("sqrt4 ft", rb32(0, _sqrt_frac(Fraction(4))), F2)
    chk("sqrt2 ft", rb32(0, _sqrt_frac(Fraction(2))), FSQRT2)
    chk("sqrt4 fo", rb64(0, _sqrt_frac(Fraction(4))), D2)
    chk("sqrt2 fo", rb64(0, _sqrt_frac(Fraction(2))), DSQRT2)

    # leftover operand patterns
    chk("F2_5 == 2.5", _f32v(F2_5)[1] == Fraction(5, 2))
    chk("-5.0 ft bits", _f32v(0xC0A00000)[1] == 5)
    chk("200.0 ft", _f32v(0x43480000)[1] == 200)
    chk("-200.0 ft", _f32v(0xC3480000)[1] == 200)
    chk("2000.0 fo", _f64v(0x409F400000000000)[1] == 2000)
    chk("5.0 ft", _f32v(0x40A00000)[1] == 5)
    return checks


def selftest():
    """Prove each assertion kind has a reachable FAIL path."""
    os.chdir(_REPO_ROOT)
    print("=" * 78)
    print("QEMU-037t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    results = []

    # 1. RF value comparison (wrong expected rf value)
    c1 = value_case("selftest rf-value",
                    set_rf(8, F1) + set_rf(9, F2) + [ftadd(4, 8, 9)],
                    expect_rf={4: 0x0000000000000000})
    ok1, _ = run_case(c1)
    results.append(("RF value comparison FAIL path", ok1 is False))

    # 2. RF flags comparison (wrong expected FCSR flags)
    c2 = value_case("selftest rf-flags",
                    set_rf(8, F1) + set_rf(9, F0) + [ftdiv(4, 8, 9)],
                    expect_rf={4: FINF, 0: rf0_with()})
    ok2, _ = run_case(c2)
    results.append(("FCSR flags comparison FAIL path", ok2 is False))

    # 3. fault case: a legal op expected to fault runs to completion (exit 0)
    c3 = Case("selftest fault", [ftadd(4, 8, 9)], expect_exit=ILLI_EXIT)
    ok3, _ = run_case(c3)
    results.append(("fault exit-code FAIL path", ok3 is False))

    # 4. E2E SYS_EXIT assertion (wrong expected -> FAIL arm -> exit != 0)
    insns = (set_rf(8, F1) + set_rf(9, F2) + [ftadd(4, 8, 9)] + [rf2rd(20, 4, 1)] +
             load_imm64_rd(22, 0) + e2e_epilogue([(20, 22, 24)], 0x48))
    c4 = Case("selftest e2e", insns, expect_exit=PASS_EXIT, e2e=True)
    ok4, _ = run_case(c4)
    results.append(("E2E SYS_EXIT assertion FAIL path", ok4 is False))

    allok = True
    for name, v in results:
        if not v:
            allok = False
        print(f"  [{'PASS' if v else 'FAIL'}] {name} must be detected as FAIL")

    print("  expectation derivation self-check:")
    for name, v in verify_derivations():
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
    print("QEMU-037t Min ROM Probe (FP arith 12 + root 2, softfloat)")
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
