#!/usr/bin/env python3
"""Min ROM probe for QEMU-072t: ftrnd/fornd roundToIntegral (six modes).

Spec sources (expectations derived from these, never from QEMU):
  - spec/SimRISC-07: 取整（roundToIntegral） 取整（roundToIntegral）  (one-hot immu6 table)
  - .tao/contracts/contract-fp.md §18 `roundint`
  - spec/SimRISC-00: 浮点状态寄存器 (rf0[33:32] mode, rf0[4:0] flags)
  - contracts/opcodes.yaml (encoding; ha 0x03 = ftrnd, 0x0B = fornd)

Independent oracle: every expected value is computed here from the IEEE-754
bit pattern with exact rational arithmetic (`fractions.Fraction`), not by
calling QEMU/softfloat and not by using host floats.  Sample bit patterns are
cross-checked against their intended decimal values, so a mistyped constant is
a hard FAIL (never a silent pass).

Case model (all assertions have a reachable FAIL path):
  * value matrix: 6 modes x 24 values x 2 formats -> result bits AND
    rf0 flags AND rf0 rounding-mode preservation;
  * static codes are exercised with a *different* rf0[33:32] value, proving
    they ignore the dynamic direction; the 4-mode x matrix DYN cases prove
    mode sensitivity (the `--oracle` summary prints the differing groups);
  * NX/NV dedicated cases (static never sets NX; 0x20 sets NX iff inexact;
    qNaN never sets NV; sNaN always sets NV);
  * ILLI: immu6=0x03 (non-one-hot), immu6=0, destination rf0.

NaN policy: contract-fp.md §18 fixes the canonical qNaN result
(0x7FC00000 / 0x7FF8000000000000) for qNaN and sNaN inputs; sNaN also sets NV.

Exit codes: ADR-0004 D5.8 (PASS=0x00, ILLI=0x88).
Usage: min_rom_probe_072t.py [--selftest|--oracle]
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

FLAG_NV = 0x01
FLAG_NX = 0x10

# ── Instruction encoding (op / ha from contracts/opcodes.yaml) ─────────

ILLI = 0x77801000                 # fence fm=1 -> ILLI
SWYM = 0x77880000                 # swym (padding)


def encode_orri(op, ha, hb, hc, hd):
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


def cmp_uo_rd(rdhb, rdhc, rdhd):
    return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


def rd2rf(rfhb, rdhc, hd):
    return encode_orri(0x40, 0x3D, rfhb, rdhc, hd)


def rf2rd(rdhb, rfhc, hd):
    return encode_orri(0x40, 0x3E, rdhb, rfhc, hd)


# ── Instructions under test ────────────────────────────────────────────

def ftrnd(hb, hc, code):
    return encode_orri(0x44, 0x03, hb, hc, code)


def fornd(hb, hc, code):
    return encode_orri(0x44, 0x0B, hb, hc, code)


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
    """Write rf0[33:32] = mode (rf0 write mask keeps flags/read-only bits)."""
    assert mode in MODE_NAMES
    return set_rf(0, mode << 32)


# ── Semihosting SYS_EXIT (ADR-0020 D8) ─────────────────────────────────

SEMI_BLOCK = 0xFC00_00FF_F000
SEMIHOST_TAG = 0x30000
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
#  Independent oracle: exact IEEE-754 roundToIntegral from bit patterns
# ══════════════════════════════════════════════════════════════════════

FT = {"signpos": 31, "fracbits": 23, "expbits": 8, "bias": 127}
FO = {"signpos": 63, "fracbits": 52, "expbits": 11, "bias": 1023}

MODE_NAMES = {0: "RNE", 1: "RTZ", 2: "RDN", 3: "RUP"}
CODE_MODE = {0x01: "RNE", 0x02: "RNA", 0x04: "RTZ", 0x08: "RUP",
             0x10: "RDN"}
STATIC_CODES = [0x01, 0x02, 0x04, 0x08, 0x10]
DYN_CODE = 0x20


def parse(bits, fmt):
    sign = (bits >> fmt["signpos"]) & 1
    exp = (bits >> fmt["fracbits"]) & ((1 << fmt["expbits"]) - 1)
    man = bits & ((1 << fmt["fracbits"]) - 1)
    expall = (1 << fmt["expbits"]) - 1
    if exp == expall:
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
    sign, exp, man, kind = parse(bits, fmt)
    if kind in ("inf", "qnan", "snan"):
        return None
    if kind == "zero":
        return Fraction(0)
    if kind == "subnormal":
        v = Fraction(man, 1 << fmt["fracbits"]) * Fraction(2) ** (1 - fmt["bias"])
    else:
        v = (Fraction(man, 1 << fmt["fracbits"]) + 1) * \
            Fraction(2) ** (exp - fmt["bias"])
    return -v if sign else v


def round_value(v, mode):
    """Round a Fraction to an integer with the given IEEE direction."""
    floor = v.numerator // v.denominator
    if v.denominator == 1:
        return floor
    if mode == "RTZ":
        return int(v)                     # Python int() truncates toward 0
    if mode == "RUP":
        return -((-v.numerator) // v.denominator)
    if mode == "RDN":
        return floor
    rem = v - floor
    if rem < Fraction(1, 2):
        return floor
    if rem > Fraction(1, 2):
        return floor + 1
    if mode == "RNA":                     # ties away from zero
        return floor if v < 0 else floor + 1
    assert mode == "RNE", mode
    return floor if floor % 2 == 0 else floor + 1


def encode_int(n, sign_zero, fmt):
    """Exact encoding of an integer (|n| <= 2^p or a power of two)."""
    sign = sign_zero if n == 0 else (1 if n < 0 else 0)
    if n == 0:
        return sign << fmt["signpos"]
    a = abs(n)
    e = a.bit_length() - 1
    expf = e + fmt["bias"]
    if e <= fmt["fracbits"]:
        man = (a << (fmt["fracbits"] - e)) - (1 << fmt["fracbits"])
    else:
        assert a == (1 << e), n             # only 2^p reaches here
        man = 0
    return (sign << fmt["signpos"]) | (expf << fmt["fracbits"]) | man


def mode_of(code, rf0_mode):
    return CODE_MODE[code] if code != DYN_CODE else MODE_NAMES[rf0_mode]


def expected(bits, fmt, code, rf0_mode):
    """Return (result_bits, flags, rounded_int_or_None)."""
    sign, exp, man, kind = parse(bits, fmt)
    if kind in ("qnan", "snan"):
        qnan = (0x7FF8 << 48) if fmt is FO else 0x7FC00000
        return qnan, (FLAG_NV if kind == "snan" else 0), None
    if kind == "inf":
        return bits, 0, None
    v = exact_value(bits, fmt)
    n = round_value(v, mode_of(code, rf0_mode))
    out = encode_int(n, sign, fmt)
    flags = FLAG_NX if (code == DYN_CODE and Fraction(n) != v) else 0
    return out, flags, n


# ── Value matrix (bit patterns cross-checked against their decimals) ───

# (label, bits, kind, decimal value or None)
FT_VALUES = [
    ("+0.0", 0x00000000, "zero", 0.0),
    ("-0.0", 0x80000000, "zero", 0.0),
    ("+0.4", 0x3ECCCCCD, "normal", 0.4),
    ("-0.4", 0xBECCCCCD, "normal", -0.4),
    ("+0.5", 0x3F000000, "normal", 0.5),
    ("-0.5", 0xBF000000, "normal", -0.5),
    ("+1.5", 0x3FC00000, "normal", 1.5),
    ("-1.5", 0xBFC00000, "normal", -1.5),
    ("+2.5", 0x40200000, "normal", 2.5),
    ("-2.5", 0xC0200000, "normal", -2.5),
    ("+3.5", 0x40600000, "normal", 3.5),
    ("-3.5", 0xC0600000, "normal", -3.5),
    ("+1.0", 0x3F800000, "normal", 1.0),
    ("-1.0", 0xBF800000, "normal", -1.0),
    ("2^24", 0x4B800000, "normal", 16777216.0),
    ("+Inf", 0x7F800000, "inf", None),
    ("-Inf", 0xFF800000, "inf", None),
    ("qNaN", 0x7FC00000, "qnan", None),
    ("sNaN", 0x7F800001, "snan", None),
    ("submin+", 0x00000001, "subnormal", None),
    ("submin-", 0x80000001, "subnormal", None),
    ("submax+", 0x007FFFFF, "subnormal", None),
]

FO_VALUES = [
    ("+0.0", 0x0000000000000000, "zero", 0.0),
    ("-0.0", 0x8000000000000000, "zero", 0.0),
    ("+0.4", 0x3FD999999999999A, "normal", 0.4),
    ("-0.4", 0xBFD999999999999A, "normal", -0.4),
    ("+0.5", 0x3FE0000000000000, "normal", 0.5),
    ("-0.5", 0xBFE0000000000000, "normal", -0.5),
    ("+1.5", 0x3FF8000000000000, "normal", 1.5),
    ("-1.5", 0xBFF8000000000000, "normal", -1.5),
    ("+2.5", 0x4004000000000000, "normal", 2.5),
    ("-2.5", 0xC004000000000000, "normal", -2.5),
    ("+3.5", 0x400C000000000000, "normal", 3.5),
    ("-3.5", 0xC00C000000000000, "normal", -3.5),
    ("+1.0", 0x3FF0000000000000, "normal", 1.0),
    ("-1.0", 0xBFF0000000000000, "normal", -1.0),
    ("2^53", 0x4340000000000000, "normal", 9007199254740992.0),
    ("+Inf", 0x7FF0000000000000, "inf", None),
    ("-Inf", 0xFFF0000000000000, "inf", None),
    ("qNaN", 0x7FF8000000000000, "qnan", None),
    ("sNaN", 0x7FF0000000000001, "snan", None),
    ("submin+", 0x0000000000000001, "subnormal", None),
    ("submin-", 0x8000000000000001, "subnormal", None),
    ("submax+", 0x000FFFFFFFFFFFFF, "subnormal", None),
]


def check_samples():
    """Cross-check every sample bit pattern against its intended value."""
    problems = []
    for name, values, fmt, tol in (("FT", FT_VALUES, FT, 2e-7),
                                   ("FO", FO_VALUES, FO, 1e-16)):
        labels = [v[0] for v in values]
        if len(labels) != len(set(labels)):
            problems.append("%s labels not unique: %r" % (name, labels))
        for label, bits, want_kind, dec in values:
            sign, exp, man, kind = parse(bits, fmt)
            if kind != want_kind:
                problems.append("%s %s 0x%X class %s != %s"
                                % (name, label, bits, kind, want_kind))
                continue
            if label.startswith("-") and sign != 1:
                problems.append("%s %s sign bit is 0" % (name, label))
            if label.startswith("+") and sign != 0:
                problems.append("%s %s sign bit is 1" % (name, label))
            if dec is not None:
                v = float(exact_value(bits, fmt))
                if abs(v - dec) > tol:
                    problems.append("%s %s 0x%X decodes to %.17g, want %.17g"
                                    % (name, label, bits, v, dec))
    return problems


def mode_sensitive_groups():
    """Groups (fmt, value) whose DYN expected result depends on rf0 mode."""
    groups = []
    for values, fmt in ((FT_VALUES, FT), (FO_VALUES, FO)):
        for label, bits, kind, _ in values:
            if kind in ("qnan", "snan", "inf"):
                continue
            outs = {m: expected(bits, fmt, DYN_CODE, m)[0] for m in MODE_NAMES}
            if len(set(outs.values())) > 1:
                groups.append((label, fmt is FO, outs))
    return groups


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


CASES = []

# value matrix: 5 static codes (each with a *different* rf0[33:32]) + DYN
for fi, (values, fmt, isdbl, tag) in enumerate(
        ((FT_VALUES, FT, False, "ft"), (FO_VALUES, FO, True, "fo"))):
    insn = ftrnd if not isdbl else fornd
    for code in STATIC_CODES:
        # static directions must ignore rf0[33:32]: use RUP unless the static
        # direction itself is RUP, then use RDN (always a different mode).
        rf0m = 2 if code == 0x08 else 3
        for label, bits, kind, _ in values:
            out, flags, _n = expected(bits, fmt, code, rf0m)
            CASES.append(value_case(
                "%s static 0x%02X %s -> 0x%X (rf0=%s)"
                % (tag, code, label, out, MODE_NAMES[rf0m]),
                set_rf(10, bits) + set_fcsr_mode(rf0m) + [insn(5, 10, code)],
                expect_rf={5: out}, expect_flags=flags, expect_mode=rf0m))
    for rf0m in MODE_NAMES:
        for label, bits, kind, _ in values:
            out, flags, _n = expected(bits, fmt, DYN_CODE, rf0m)
            CASES.append(value_case(
                "%s dyn rf0=%s %s -> 0x%X" % (tag, MODE_NAMES[rf0m], label, out),
                set_rf(10, bits) + set_fcsr_mode(rf0m) +
                [insn(5, 10, DYN_CODE)],
                expect_rf={5: out}, expect_flags=flags, expect_mode=rf0m))

# NX / NV dedicated cases
FT_15, FT_10, FT_QNAN, FT_SNAN = 0x3FC00000, 0x3F800000, 0x7FC00000, 0x7F800001
FO_15, FO_QNAN, FO_SNAN = 0x3FF8000000000000, 0x7FF8000000000000, \
    0x7FF0000000000001
CASES.append(value_case(
    "NX1 ft static trunc(1.5) -> 1, NX not set",
    set_rf(10, FT_15) + set_fcsr_mode(3) + [ftrnd(5, 10, 0x04)],
    expect_rf={5: 0x3F800000}, expect_flags=0, expect_mode=3))
CASES.append(value_case(
    "NX2 ft static RNE(1.5) -> 2, NX not set",
    set_rf(10, FT_15) + set_fcsr_mode(1) + [ftrnd(5, 10, 0x01)],
    expect_rf={5: 0x40000000}, expect_flags=0, expect_mode=1))
CASES.append(value_case(
    "NX3 ft dyn RNE(1.5) -> 2, NX set",
    set_rf(10, FT_15) + set_fcsr_mode(0) + [ftrnd(5, 10, 0x20)],
    expect_rf={5: 0x40000000},
    expect_flags=FLAG_NX, expect_mode=0))
CASES.append(value_case(
    "NX4 ft dyn RNE(1.0) -> 1, NX not set (exact)",
    set_rf(10, FT_10) + set_fcsr_mode(0) + [ftrnd(5, 10, 0x20)],
    expect_rf={5: FT_10}, expect_flags=0, expect_mode=0))
CASES.append(value_case(
    "NX5 ft dyn qNaN -> canonical qNaN, NV not set",
    set_rf(10, FT_QNAN) + set_fcsr_mode(0) + [ftrnd(5, 10, 0x20)],
    expect_rf={5: FT_QNAN}, expect_flags=0, expect_mode=0))
CASES.append(value_case(
    "NX6 ft dyn sNaN -> canonical qNaN, NV set",
    set_rf(10, FT_SNAN) + set_fcsr_mode(0) + [ftrnd(5, 10, 0x20)],
    expect_rf={5: FT_QNAN}, expect_flags=FLAG_NV, expect_mode=0))
CASES.append(value_case(
    "NX7 ft static 0x04 sNaN -> canonical qNaN, NV set",
    set_rf(10, FT_SNAN) + set_fcsr_mode(3) + [ftrnd(5, 10, 0x04)],
    expect_rf={5: FT_QNAN}, expect_flags=FLAG_NV, expect_mode=3))
CASES.append(value_case(
    "NX8 fo dyn RNE(1.5) -> 2, NX set",
    set_rf(10, FO_15) + set_fcsr_mode(0) + [fornd(5, 10, 0x20)],
    expect_rf={5: 0x4000000000000000},
    expect_flags=FLAG_NX, expect_mode=0))
CASES.append(value_case(
    "NX9 fo static trunc(1.5) -> 1, NX not set",
    set_rf(10, FO_15) + set_fcsr_mode(3) + [fornd(5, 10, 0x04)],
    expect_rf={5: 0x3FF0000000000000}, expect_flags=0, expect_mode=3))
CASES.append(value_case(
    "NX10 fo dyn sNaN -> canonical qNaN, NV set",
    set_rf(10, FO_SNAN) + set_fcsr_mode(0) + [fornd(5, 10, 0x20)],
    expect_rf={5: FO_QNAN}, expect_flags=FLAG_NV, expect_mode=0))

# alias / source-rf0 / negative-NaN edge cases
CASES.append(value_case(
    "AL1 ft source==dest (ftrnd rf10,rf10,0x04) -> 1",
    set_rf(10, FT_15) + set_fcsr_mode(3) + [ftrnd(10, 10, 0x04)],
    expect_rf={10: 0x3F800000}, expect_flags=0, expect_mode=3))
CASES.append(value_case(
    "AL2 fo source==dest (fornd rf10,rf10,0x01) -> 2",
    set_rf(10, FO_15) + set_fcsr_mode(3) + [fornd(10, 10, 0x01)],
    expect_rf={10: 0x4000000000000000}, expect_flags=0, expect_mode=3))
CASES.append(value_case(
    "AL3 ft source rf0 (reads FCSR qNaN low 32) -> canonical qNaN",
    set_fcsr_mode(0) + [ftrnd(5, 0, 0x04)],
    expect_rf={5: FT_QNAN}, expect_flags=0, expect_mode=0))
CASES.append(value_case(
    "AL4 ft dyn -qNaN -> canonical +qNaN, NV not set",
    set_rf(10, 0xFFC00000) + set_fcsr_mode(0) + [ftrnd(5, 10, 0x20)],
    expect_rf={5: FT_QNAN}, expect_flags=0, expect_mode=0))

# ILLI cases (fault epilogue: a missing legality check exits 0 != 0x88)
CASES.append(Case("IL1 ftrnd immu6=0x03 (non-one-hot) -> ILLI",
                  [ftrnd(5, 10, 0x03)], expect_exit=ILLI_EXIT))
CASES.append(Case("IL2 fornd immu6=0 -> ILLI",
                  [fornd(5, 10, 0x00)], expect_exit=ILLI_EXIT))
CASES.append(Case("IL3 ftrnd dst rf0 -> ILLI",
                  [ftrnd(0, 10, 0x01)], expect_exit=ILLI_EXIT))


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
    print("QEMU-072t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    results = []
    cs = [
        ("RF value comparison",
         value_case("selftest rf", set_rf(10, FT_15) + set_fcsr_mode(0) +
                    [ftrnd(5, 10, 0x01)], expect_rf={5: 0xDEADBEEF},
                    expect_flags=0, expect_mode=0)),
        ("rf0 flags comparison",
         value_case("selftest flags", set_rf(10, FT_15) + set_fcsr_mode(0) +
                    [ftrnd(5, 10, 0x20)], expect_rf={5: 0x40000000},
                    expect_flags=0, expect_mode=0)),
        ("rf0 rounding-mode preservation",
         value_case("selftest mode", set_rf(10, FT_15) + set_fcsr_mode(0) +
                    [ftrnd(5, 10, 0x01)], expect_rf={5: 0x40000000},
                    expect_flags=0, expect_mode=3)),
        ("fault exit-code",
         Case("selftest fault", [ftrnd(5, 10, 0x01)],
              expect_exit=ILLI_EXIT)),
    ]
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
    groups = mode_sensitive_groups()
    print("roundToIntegral oracle (exact rational arithmetic, not QEMU)")
    for code in STATIC_CODES:
        outs = sorted({expected(bits, fmt, code, 0)[0]
                       for values, fmt in ((FT_VALUES, FT), (FO_VALUES, FO))
                       for _l, bits, _k, _d in values})
        print("  static 0x%02X (%s): %d distinct result patterns"
              % (code, CODE_MODE[code], len(outs)))
    print("  dynamic 0x20: %d (format,value) groups differ across "
          "RNE/RTZ/RDN/RUP" % len(groups))
    for label, isdbl, outs in groups[:6]:
        print("    %s %-5s " % ("fo" if isdbl else "ft", label) +
              " ".join("%s->0x%X" % (MODE_NAMES[m], outs[m]) for m in outs))
    problems = check_samples()
    for p in problems:
        print("  [FAIL] " + p)
    print("Oracle: %s (%d ft + %d fo samples, %d mode-sensitive groups)"
          % ("PASS" if not problems and groups else "FAIL",
             len(FT_VALUES), len(FO_VALUES), len(groups)))
    return 0 if (not problems and groups) else 1


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
    print("=" * 78)
    print("QEMU-072t Min ROM Probe (ftrnd/fornd, six roundToIntegral modes)")
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
    if "--oracle" in sys.argv:
        sys.exit(print_oracle())
    sys.exit(main())
