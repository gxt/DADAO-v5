#!/usr/bin/env python3
"""Min ROM probe for QEMU-071t: ftmin/ftmax/fomin/fomax (754-2019 min/maxNumber).

Spec sources (expectations derived from these, never from QEMU):
  - spec/SimRISC-07: 最小最大值（minimumNumber / maximumNumber） 最小最大值（minimumNumber / maximumNumber）
  - .tao/contracts/contract-fp.md §19 `minmax`
  - spec/SimRISC-00: 浮点状态寄存器 (rf0[33:32] mode, rf0[4:0] flags)
  - contracts/opcodes.yaml (encoding; op 0x44, ha 0x26/0x27/0x2E/0x2F)

Independent oracle: every expected result is derived here from the IEEE-754
bit patterns with exact rational arithmetic (`fractions.Fraction`), never by
calling QEMU/softfloat or host floats.  The six boundary rules of the spec are
implemented explicitly:
  1. ordered comparison ⇒ min picks the smaller, max the larger;
  2. −0 < +0 (differing signs are never "equal");
  3. x == y with the same sign ⇒ either operand (identical bit patterns);
  4. one NaN (q or s) ⇒ the numeric operand, NV only for an sNaN input;
  5. two NaNs ⇒ canonical qNaN 0x7FC00000 / 0x7FF8000000000000, NV if any sNaN;
  6. no rounding ⇒ NX/OF/UF never set (asserted as an exact rf0[4:0] match).

Case model (every assertion has a reachable FAIL path):
  * value + flag matrix: pairs x {min,max} x {ft,fo}; the flag column is
    asserted exactly, so a spurious NV/NX (or a missing sNaN NV) is red;
  * dedicated flag cases: qNaN input keeps NV clear, finite compares keep NX
    clear, sNaN single/double inputs set NV;
  * aliasing (dest == either source) and source rf0;
  * ILLI: destination rf0 for all four instructions (fault epilogue, so a
    missing legality check cannot pass).

Exit codes: ADR-0004 D5.8 (PASS=0x00, ILLI=0x88).
Usage: min_rom_probe_071t.py [--selftest|--oracle]
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
from fractions import Fraction

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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

ILLI = 0x47801000                 # fence fm=1 -> ILLI
SWYM = 0x47880000                 # swym (padding)

FTMIN_HA, FTMAX_HA, FOMIN_HA, FOMAX_HA = 0x26, 0x27, 0x2E, 0x2F


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


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


def rd2rf(rfhb, rdhc, hd):
    return encode_orri(0x40, 0x3D, rfhb, rdhc, hd)


# ── Instructions under test ────────────────────────────────────────────

def ftmin(hb, hc, hd):
    return encode_orri(0x44, FTMIN_HA, hb, hc, hd)


def ftmax(hb, hc, hd):
    return encode_orri(0x44, FTMAX_HA, hb, hc, hd)


def fomin(hb, hc, hd):
    return encode_orri(0x44, FOMIN_HA, hb, hc, hd)


def fomax(hb, hc, hd):
    return encode_orri(0x44, FOMAX_HA, hb, hc, hd)


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
    assert 0 <= mode <= 3
    return set_rf(0, mode << 32)


# ── Semihosting SYS_EXIT (ADR-0020 D8) ─────────────────────────────────

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
#  Independent oracle: IEEE 754-2019 minimumNumber / maximumNumber
# ══════════════════════════════════════════════════════════════════════

FT = {"signpos": 31, "fracbits": 23, "expbits": 8, "bias": 127,
      "qnan": 0x7FC00000}
FO = {"signpos": 63, "fracbits": 52, "expbits": 11, "bias": 1023,
      "qnan": 0x7FF8000000000000}


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
    """Exact Fraction value (sign applied; ±0 both map to 0)."""
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


def numeric_cmp(bits_a, bits_b, fmt):
    """IEEE numeric order, including −0 < +0 and ±Inf.  Returns -1/0/1."""
    sa, _ea, _ma, ka = parse(bits_a, fmt)
    sb, _eb, _mb, kb = parse(bits_b, fmt)
    if ka == "inf" or kb == "inf":
        # Infinities rank outside every finite value; same-signed Inf is equal.
        if ka == "inf" and kb == "inf":
            return 0 if sa == sb else (-1 if sa else 1)
        if ka == "inf":
            return -1 if sa else 1
        return 1 if sb else -1
    va = exact_value(bits_a, fmt)
    vb = exact_value(bits_b, fmt)
    if va < vb:
        return -1
    if va > vb:
        return 1
    if sa != sb:
        # Only ±0 can be numerically equal with different signs.
        return -1 if sa else 1
    return 0


def is_nan_kind(kind):
    return kind in ("qnan", "snan")


def expected(bits_a, bits_b, fmt, ismax):
    """Return (result_bits, expected rf0[4:0] flags)."""
    _sa, _ea, _ma, ka = parse(bits_a, fmt)
    _sb, _eb, _mb, kb = parse(bits_b, fmt)
    flags = FLAG_NV if ("snan" in (ka, kb)) else 0

    if is_nan_kind(ka) and is_nan_kind(kb):
        # Rule 5: two NaNs ⇒ canonical quiet NaN (any sNaN still raises NV).
        return fmt["qnan"], flags
    if is_nan_kind(ka):
        # Rule 4: single NaN ⇒ the numeric operand.
        return bits_b, flags
    if is_nan_kind(kb):
        return bits_a, flags
    # Rules 1-3 and 6: pure numeric ordering, no rounding ⇒ flags stay clear.
    cmp = numeric_cmp(bits_a, bits_b, fmt)
    if ismax:
        return (bits_a if cmp >= 0 else bits_b), 0
    return (bits_a if cmp <= 0 else bits_b), 0


# ── Sample bit patterns (cross-checked against their decimal values) ───

# (label, bits, kind, decimal value or None)
FT_VALUES = [
    ("+0.0", 0x00000000, "zero", 0.0),
    ("-0.0", 0x80000000, "zero", 0.0),
    ("+1.0", 0x3F800000, "normal", 1.0),
    ("-1.0", 0xBF800000, "normal", -1.0),
    ("+2.0", 0x40000000, "normal", 2.0),
    ("-2.0", 0xC0000000, "normal", -2.0),
    ("+Inf", 0x7F800000, "inf", None),
    ("-Inf", 0xFF800000, "inf", None),
    ("qNaN", 0x7FC00000, "qnan", None),
    ("-qNaN", 0xFFC00000, "qnan", None),
    ("sNaN", 0x7F800001, "snan", None),
    ("submin+", 0x00000001, "subnormal", None),
    ("submax+", 0x007FFFFF, "subnormal", None),
]

FO_VALUES = [
    ("+0.0", 0x0000000000000000, "zero", 0.0),
    ("-0.0", 0x8000000000000000, "zero", 0.0),
    ("+1.0", 0x3FF0000000000000, "normal", 1.0),
    ("-1.0", 0xBFF0000000000000, "normal", -1.0),
    ("+2.0", 0x4000000000000000, "normal", 2.0),
    ("-2.0", 0xC000000000000000, "normal", -2.0),
    ("+Inf", 0x7FF0000000000000, "inf", None),
    ("-Inf", 0xFFF0000000000000, "inf", None),
    ("qNaN", 0x7FF8000000000000, "qnan", None),
    ("-qNaN", 0xFFF8000000000000, "qnan", None),
    ("sNaN", 0x7FF0000000000001, "snan", None),
    ("submin+", 0x0000000000000001, "subnormal", None),
    ("submax+", 0x000FFFFFFFFFFFFF, "subnormal", None),
]

# Operand pairs exercising every boundary rule (labels from *_VALUES).
PAIRS = [
    ("ordered +1/+2", "+1.0", "+2.0"),
    ("ordered -2/+1", "-2.0", "+1.0"),
    ("ordered +2/-1", "+2.0", "-1.0"),
    ("zeros (+0,-0)", "+0.0", "-0.0"),
    ("zeros (-0,+0)", "-0.0", "+0.0"),
    ("zeros (+0,+0)", "+0.0", "+0.0"),
    ("zeros (-0,-0)", "-0.0", "-0.0"),
    ("equal +1/+1", "+1.0", "+1.0"),
    ("equal -1/-1", "-1.0", "-1.0"),
    ("single qNaN left", "qNaN", "+1.0"),
    ("single qNaN right", "+1.0", "qNaN"),
    ("single -qNaN left", "-qNaN", "+1.0"),
    ("single sNaN left", "sNaN", "+1.0"),
    ("single sNaN right", "+1.0", "sNaN"),
    ("double qNaN", "qNaN", "qNaN"),
    ("double -qNaN/qNaN", "-qNaN", "qNaN"),
    ("double sNaN/qNaN", "sNaN", "qNaN"),
    ("double qNaN/sNaN", "qNaN", "sNaN"),
    ("inf +Inf/+1", "+Inf", "+1.0"),
    ("inf -Inf/+Inf", "-Inf", "+Inf"),
    ("inf +Inf/+Inf", "+Inf", "+Inf"),
    ("subnormal vs +0", "submin+", "+0.0"),
    ("subnormal pair", "submin+", "submax+"),
    ("nan vs inf", "qNaN", "+Inf"),
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


def fmt_insns(tag):
    """(instruction constructor, format descriptor, format label)."""
    return {"ft": (ftmin, ftmax, FT), "fo": (fomin, fomax, FO)}[tag]


def build_matrix():
    """All pair x op x format cases with independently derived expectations."""
    cases = []
    for tag in ("ft", "fo"):
        fmin, fmax, fmt = fmt_insns(tag)
        labels = {v[0]: v[1] for v in (FT_VALUES if fmt is FT else FO_VALUES)}
        for pair_label, la, lb in PAIRS:
            ba, bb = labels[la], labels[lb]
            for opname, ctor, ismax in (("min", fmin, False),
                                        ("max", fmax, True)):
                want, flags = expected(ba, bb, fmt, ismax)
                cases.append(value_case(
                    "%s %s %s (%s,%s) -> 0x%X NV=%d"
                    % (tag, opname, pair_label, la, lb, want, flags),
                    set_rf(10, ba) + set_rf(11, bb) + set_fcsr_mode(0) +
                    [ctor(5, 10, 11)],
                    expect_rf={5: want}, expect_flags=flags, expect_mode=0))
    return cases


CASES = build_matrix()

# ── Dedicated flag cases (qNaN never NV; no rounding ⇒ NX never set) ───
# Expectations come from the oracle as well; the *names* state the rule under
# test so a wrong expectation cannot hide behind a hand-typed constant.

def flag_case(name, tag, ba, bb, ismax, dst, setup):
    fmin, fmax, fmt = fmt_insns(tag)
    want, flags = expected(ba, bb, fmt, ismax)
    return value_case("%s -> 0x%X NV=%d" % (name, want, flags),
                      setup + [(fmax if ismax else fmin)(dst, 10, 11)],
                      expect_rf={dst: want}, expect_flags=flags,
                      expect_mode=0)


FT_1, FT_2 = 0x3F800000, 0x40000000
FT_QNAN, FT_SNAN = 0x7FC00000, 0x7F800001
FO_1, FO_2 = 0x3FF0000000000000, 0x4000000000000000
FO_QNAN, FO_SNAN = 0x7FF8000000000000, 0x7FF0000000000001

CASES.append(flag_case(
    "FL1 ft min qNaN/+1: NV not set, NX not set", "ft", FT_QNAN, FT_1,
    False, 5, set_rf(10, FT_QNAN) + set_rf(11, FT_1) + set_fcsr_mode(0)))
CASES.append(flag_case(
    "FL2 ft max +1/sNaN: NV set, NX not set", "ft", FT_1, FT_SNAN,
    True, 5, set_rf(10, FT_1) + set_rf(11, FT_SNAN) + set_fcsr_mode(0)))
CASES.append(flag_case(
    "FL3 ft min +1/+2: NX not set (no rounding)", "ft", FT_1, FT_2,
    False, 5, set_rf(10, FT_1) + set_rf(11, FT_2) + set_fcsr_mode(0)))
CASES.append(flag_case(
    "FL4 fo max qNaN/qNaN: canonical qNaN, NV not set", "fo", FO_QNAN, FO_QNAN,
    True, 5, set_rf(10, FO_QNAN) + set_rf(11, FO_QNAN) + set_fcsr_mode(0)))
CASES.append(flag_case(
    "FL5 fo min sNaN/qNaN: canonical qNaN, NV set", "fo", FO_SNAN, FO_QNAN,
    False, 5, set_rf(10, FO_SNAN) + set_rf(11, FO_QNAN) + set_fcsr_mode(0)))
CASES.append(flag_case(
    "FL6 fo min +1/+2: NX not set (no rounding)", "fo", FO_1, FO_2,
    False, 5, set_rf(10, FO_1) + set_rf(11, FO_2) + set_fcsr_mode(0)))

# ── Aliasing / source rf0 (expectations also derived by the oracle) ────

FT_M2 = 0xC0000000
FO_M2 = 0xC000000000000000

_want, _flags = expected(FT_M2, FT_1, FT, False)
CASES.append(value_case(
    "AL1 ftmin dest==src1 (rf10,rf10,rf11) -2/1 -> 0x%X" % _want,
    set_rf(10, FT_M2) + set_rf(11, FT_1) + set_fcsr_mode(0) +
    [ftmin(10, 10, 11)],
    expect_rf={10: _want}, expect_flags=_flags, expect_mode=0))
_want, _flags = expected(FT_M2, FT_1, FT, False)
CASES.append(value_case(
    "AL2 ftmin dest==src2 (rf11,rf10,rf11) -2/1 -> 0x%X" % _want,
    set_rf(10, FT_M2) + set_rf(11, FT_1) + set_fcsr_mode(0) +
    [ftmin(11, 10, 11)],
    expect_rf={11: _want}, expect_flags=_flags, expect_mode=0))
_want, _flags = expected(FO_M2, FO_M2, FO, True)
CASES.append(value_case(
    "AL3 fomax dest==both (rf10,rf10,rf10) -2/-2 -> 0x%X" % _want,
    set_rf(10, FO_M2) + set_fcsr_mode(0) + [fomax(10, 10, 10)],
    expect_rf={10: _want}, expect_flags=_flags, expect_mode=0))
_want, _flags = expected(FT_QNAN, FT_1, FT, False)
CASES.append(value_case(
    "AL4 ftmin source rf0 (low 32 = qNaN) vs +1 -> 0x%X, NV=%d"
    % (_want, _flags),
    set_fcsr_mode(0) + set_rf(10, FT_1) + [ftmin(5, 0, 10)],
    expect_rf={5: _want}, expect_flags=_flags, expect_mode=0))
_want, _flags = expected(FO_QNAN, FO_1, FO, True)
CASES.append(value_case(
    "AL5 fomax source rf0 (64-bit qNaN) vs +1 -> 0x%X, NV=%d"
    % (_want, _flags),
    set_fcsr_mode(0) + set_rf(10, FO_1) + [fomax(5, 0, 10)],
    expect_rf={5: _want}, expect_flags=_flags, expect_mode=0))

# ── ILLI: destination rf0 (fault epilogue: missing check exits 0) ──────

for name, ctor in (("ftmin", ftmin), ("ftmax", ftmax),
                   ("fomin", fomin), ("fomax", fomax)):
    CASES.append(Case("IL %s dst rf0 -> ILLI" % name,
                      [ctor(0, 10, 11)], expect_exit=ILLI_EXIT))


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
    print("QEMU-071t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    results = []
    cs = [
        ("RF value comparison",
         value_case("selftest rf", set_rf(10, FT_1) + set_rf(11, FT_2) +
                    set_fcsr_mode(0) + [ftmin(5, 10, 11)],
                    expect_rf={5: 0xDEADBEEF}, expect_flags=0, expect_mode=0)),
        ("rf0 NV flag comparison",
         value_case("selftest flags", set_rf(10, FT_QNAN) + set_rf(11, FT_1) +
                    set_fcsr_mode(0) + [ftmin(5, 10, 11)],
                    expect_rf={5: FT_1}, expect_flags=FLAG_NV,
                    expect_mode=0)),
        ("rf0 NX flag comparison",
         value_case("selftest nx", set_rf(10, FT_1) + set_rf(11, FT_2) +
                    set_fcsr_mode(0) + [ftmax(5, 10, 11)],
                    expect_rf={5: FT_2}, expect_flags=FLAG_NX,
                    expect_mode=0)),
        ("rf0 rounding-mode preservation",
         value_case("selftest mode", set_rf(10, FT_1) + set_rf(11, FT_2) +
                    set_fcsr_mode(0) + [ftmin(5, 10, 11)],
                    expect_rf={5: FT_1}, expect_flags=0, expect_mode=3)),
        ("fault exit-code",
         Case("selftest fault", [ftmin(5, 10, 11)],
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
    problems = check_samples()
    print("min/max slow oracle (exact rational arithmetic, not QEMU)")
    print("  pairs: %d, formats: 2, ops: 2 -> %d matrix cases"
          % (len(PAIRS), len(PAIRS) * 4))
    nv = sum(1 for p in PAIRS
             for fmt, lv in ((FT, FT_VALUES), (FO, FO_VALUES))
             for ismax in (False, True)
             if expected(dict((v[0], v[1]) for v in lv)[p[1]],
                         dict((v[0], v[1]) for v in lv)[p[2]],
                         fmt, ismax)[1] == FLAG_NV)
    print("  matrix cases carrying NV: %d (sNaN operand present)" % nv)
    for p in problems:
        print("  [FAIL] " + p)
    print("Oracle: %s (%d ft + %d fo samples)"
          % ("PASS" if not problems else "FAIL",
             len(FT_VALUES), len(FO_VALUES)))
    return 0 if not problems else 1


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
    print("QEMU-071t Min ROM Probe (ftmin/ftmax/fomin/fomax, 754-2019 "
          "minimumNumber/maximumNumber)")
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
