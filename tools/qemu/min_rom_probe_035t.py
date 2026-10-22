#!/usr/bin/env python3
"""Min ROM probe for QEMU-035t: FP bit-level semantics (sign/classify/compare).

Spec sources (expectations are derived from these, never from QEMU):
  - spec/SimRISC-07: 浮点符号位操作指令 / 浮点比较指令 / 浮点分类指令
  - spec/SimRISC-00: 浮点寄存器
  - .tao/contracts/contract-fp.md §7 / §8 / §9
The classify category bits are NOT hand-copied: they are parsed at import time
from the §7 table of spec/SimRISC-07 (`load_class_bits_from_spec`); a missing
or malformed table is an explicit non-zero FAIL.  `--oracle` prints the parsed
category↔bit mapping and cross-checks it against all 20 sample values.
Encodings: contracts/opcodes.yaml.
Exit codes: ADR-0004 D5.8 (PASS=0x00, ILLI=0x88).

Instructions under test (10):
  sign     (4): ftsgnj ftsgnn fosgnj fosgnn   (orrr)
  classify (2): ftcls focls                   (orri, block immu6 1..63)
  compare  (4): ftqcmp ftscmp foqcmp foscmp   (orrr, result -> rd)

Agreed per-format conventions (spec open points, see task §1.4):
  * sign injection operates on the full 64-bit rf register: only the format
    sign bit (bit31 for ft, bit63 for fo) is replaced, every other bit is
    preserved.  This makes rfHD=rf0 -> abs() and rfHC==rfHD -> copy/negate
    fall out with no special case.
  * classify uses the low 32 bits (ft) / all 64 bits (fo) and clears [63:10].
  * compare writes a full 64-bit rd integer; unordered returns a fixed NaN:
      quiet compare     -> qNaN  0x7FC00000 (ft) / 0x7FF8000000000000 (fo)
      signaling compare -> sNaN  0x7F800001 (ft) / 0x7FF0000000000001 (fo)
    (the sNaN payload follows task §1.4; the qNaN matches the FCSR qNaN
    fields, both with sign bit 0).

Verification channels (same as min_rom_probe_034t.py):
  * value cases  -> QEMU `-d cpu` dump, parsing the *last* RF[]/RD[] dump.
  * fault cases  -> process exit code (ILLI 0x88).
  * E2E cases    -> in-ROM compare + SYS_EXIT PASS/FAIL epilogue.

Reverse gate (.work/evidence/QEMU-035t/run.sh --inject): reverting any of the
10 implementations makes the corresponding cases FAIL.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

# D6 compliance: resolve probe artifact dir via paths.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths  # noqa: E402


def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d


QEMU = ".work/build/qemu/qemu-system-dadao"

ROM_BASE = 0xFFFFFFFF0000

# FCSR reset value (target/dadao/cpu.h::DADAO_RESET_RF0, SimRISC-00: 浮点状态寄存器)
RESET0 = 0x7FF800007FC00000

PASS_EXIT = 0x00
ILLI_EXIT = 0x88

# ── Instruction encoding (op / ha values from contracts/opcodes.yaml) ──

# ROM terminator: a deterministic ILLI word.  `fence` used to be the poison,
# but since SPEC-164t it is an implemented legal instruction (and its old op is
# no longer decoded), so the poison is the remaining excluded family `cfxld`
# (op=0x7C, ha=0x00, scope=excluded) -> exit 0x88.
ILLI = 0x7C000000                 # cfxld -> ILLI (exit 0x88)
SWYM = 0x47880000                 # swym (padding, op=0x47 ha=0x22)


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


# ── Instructions under test (ha from contracts/opcodes.yaml) ──

def ftsgnn(hb, hc, hd):
    return encode_orri(0x44, 0x16, hb, hc, hd)


def ftsgnj(hb, hc, hd):
    return encode_orri(0x44, 0x17, hb, hc, hd)


def fosgnn(hb, hc, hd):
    return encode_orri(0x44, 0x1E, hb, hc, hd)


def fosgnj(hb, hc, hd):
    return encode_orri(0x44, 0x1F, hb, hc, hd)


def ftqcmp(hb, hc, hd):
    return encode_orri(0x44, 0x20, hb, hc, hd)


def ftscmp(hb, hc, hd):
    return encode_orri(0x44, 0x21, hb, hc, hd)


def foqcmp(hb, hc, hd):
    return encode_orri(0x44, 0x28, hb, hc, hd)


def foscmp(hb, hc, hd):
    return encode_orri(0x44, 0x29, hb, hc, hd)


def ftcls(hb, hc, hd):
    return encode_orri(0x44, 0x00, hb, hc, hd)


def focls(hb, hc, hd):
    return encode_orri(0x44, 0x08, hb, hc, hd)


# ── Setup helpers ──────────────────────────────────────────────────────

def load_imm64_rd(rd, val):
    """Build an arbitrary 64-bit value in rd using set.zw + or.w (trusted M1)."""
    insns = [set_zw_rd(rd, val & 0xFFFF)]
    for wp in range(1, 4):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            insns.append(or_w_rd(rd, wp, w))
    return insns


def set_rf(rf, val):
    """Load rf[rf] = val (uses rd31 as scratch; rd2rf/wyde writes are trusted)."""
    return load_imm64_rd(31, val) + [rd2rf(rf, 31, 1)]


# ── Semihosting SYS_EXIT (ADR-0020 D8: replaces the legacy MMIO halt device) ──

SEMI_BLOCK = 0xFC00_00FF_F000       # argument block {reason, code}, in RAM
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026


def trap_ciii(cfxha, immu18):
    return encode_riii(0x7F, cfxha, immu18 & 0x3FFFF)


def semi_exit(code_rd):
    """rb16 = SEMI_BLOCK; block = {0x20026, code_rd}; rd16 = 0x18; trap."""
    return ([set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF), or_w_rb(16, 0, 0xF000), or_w_rb(16, 2, 0xFC00)]
            + load_imm64_rd(8, ADP_STOPPED_APPLICATION_EXIT)
            + [st_o_rd(8, 16, 0)]
            + [st_o_rd(code_rd, 16, 8)]
            + load_imm64_rd(16, 0x18)
            + [trap_ciii(0, SEMIHOST_TAG)])


# ── ROM assembly ───────────────────────────────────────────────────────

TRAMPOLINE = [
    set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),  # rb16 = 0xFC00_00FF_0000 (dead; semi_exit rebuilds it)
    set_zw_rb(17, 2, 0xFC00),                          # rb17 = 0xFC0000000000 (RAM)
    encode_rwii(0x4C, 40, 0, 0x0001),                  # rd40 = 1 (TB-split branch flag)
]


def build_rom(test_insns):
    """Value-case ROM: body + ILLI terminator (the RF/RD comparison is the check)."""
    rom = b''.join(TRAMPOLINE) + b''.join(test_insns) + struct.pack('>I', ILLI)
    while len(rom) < 64:
        rom += struct.pack('>I', SWYM)
    return rom


def build_fault_rom(test_insns):
    """Fault-case ROM: body + PASS epilogue.

    If the instruction under test does NOT fault, the PASS epilogue writes 0 to
    SYS_EXIT (exit 0x00), which differs from the expected fault code => FAIL.
    This gives every fault case a reachable FAIL path (appending ILLI instead
    would mask a missing legality check)."""
    return (b''.join(TRAMPOLINE) + b''.join(test_insns) +
            b''.join([set_zw_rd(18, 0)] + semi_exit(18)))


def build_e2e_rom(test_insns):
    return b''.join(TRAMPOLINE) + b''.join(test_insns)


# ── QEMU execution ─────────────────────────────────────────────────────

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
    """Run with `-d cpu`; return (exit_code, log_text)."""
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
    """Return the last <bank>[idx] value in a `-d cpu` dump, or None."""
    pat = re.compile(r'%s\[%02d\]:\s*([0-9a-fA-F]{16})' % (bank, idx))
    m = None
    for mm in pat.finditer(log_text):
        m = mm
    return int(m.group(1), 16) if m else None


# ── E2E assertion epilogue (compare rd(s), SYS_EXIT PASS/FAIL) ─────────

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


# ── Case model ─────────────────────────────────────────────────────────

class Case:
    def __init__(self, name, insns, expect_exit=None,
                 expect_rf=None, expect_rd=None, e2e=False, classify=None):
        self.name = name
        self.insns = insns
        self.expect_exit = expect_exit
        self.expect_rf = expect_rf or {}
        self.expect_rd = expect_rd or {}
        self.e2e = e2e
        # rd index -> category alias: assert exactly that one bit is set and
        # rd[63:10] == 0 (SimRISC-07: 浮点分类指令: only [9:0] is used).
        self.classify = classify or {}


def value_case(name, insns, expect_rf=None, expect_rd=None, classify=None):
    body = list(insns) + [br_nz(40, 1)]        # rd40=1 -> taken, target = next, TB split
    return Case(name, body, expect_exit=ILLI_EXIT,
                expect_rf=expect_rf, expect_rd=expect_rd, classify=classify)


# ══════════════════════════════════════════════════════════════════════
#  Expected-value constants (hand-derived, see module docstring)
# ══════════════════════════════════════════════════════════════════════

# fo float64 patterns
FO_P1 = 0x3FF0000000000000   # +1.0
FO_N1 = 0xBFF0000000000000   # -1.0
FO_P3 = 0x4008000000000000   # +3.0
FO_N3 = 0xC008000000000000   # -3.0

# ft float32 patterns
FT_P1 = 0x3F800000           # +1.0
FT_P2 = 0x40000000           # +2.0
FT_P3 = 0x40400000           # +3.0
FT_N1 = 0xBF800000           # -1.0
FT_N2 = 0xC0000000           # -2.0
FT_QNAN = 0x7FC00000
FT_SNAN = 0x7F800001
FO_QNAN = 0x7FF8000000000000
FO_SNAN = 0x7FF0000000000001

# 10 classification category bits.  **Independent oracle**: parsed from
# `spec/SimRISC-07: 浮点分类指令` at import time, never hand-copied here.  A missing /
# renamed section or a malformed table is a hard FAIL (explicit non-zero exit),
# never a silent fallback.
SPEC_FP = (os.environ.get('DADAO_FP_SPEC')
           or os.path.join(_REPO_ROOT, 'spec', 'SimRISC-07-浮点运算.md'))

# probe category alias -> spec table name (aliases only; **no bit numbers**)
SPEC_CLASS_NAME = {
    "sNaN": "signalingNaN",
    "qNaN": "quietNaN",
    "negInf": "negativeInfinity",
    "negNormal": "negativeNormal",
    "negSubnormal": "negativeSubnormal",
    "negZero": "negativeZero",
    "posZero": "positiveZero",
    "posSubnormal": "positiveSubnormal",
    "posNormal": "positiveNormal",
    "posInf": "positiveInfinity",
}


class SpecOracleError(RuntimeError):
    pass


def load_class_bits_from_spec(path=SPEC_FP):
    """Derive {alias: 1 << bit} from the `| bit | class |` table of spec §7."""
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except OSError as e:
        raise SpecOracleError("cannot read %s: %s" % (path, e))
    m = re.search(r'^## 7\. 浮点分类指令\s*$(.*?)(?=^## |\Z)',
                  text, re.M | re.S)
    if not m:
        raise SpecOracleError("%s: section '## 7. 浮点分类指令' not found" % path)
    rows = re.findall(r'^\|\s*(\d+)\s*\|\s*([A-Za-z]+)\s*\|',
                      m.group(1), re.M)
    if len(rows) != 10:
        raise SpecOracleError(
            "%s §7: expected 10 table rows, parsed %d: %r"
            % (path, len(rows), rows))
    by_name = {}
    for bit, name in rows:
        if name in by_name:
            raise SpecOracleError("%s §7: duplicate class %r" % (path, name))
        by_name[name] = int(bit)
    if set(by_name) != set(SPEC_CLASS_NAME.values()):
        raise SpecOracleError(
            "%s §7: class names %r != expected %r"
            % (path, sorted(by_name), sorted(SPEC_CLASS_NAME.values())))
    if sorted(by_name.values()) != list(range(10)):
        raise SpecOracleError(
            "%s §7: bits %r are not exactly 0..9"
            % (path, sorted(by_name.values())))
    return {alias: 1 << by_name[spec]
            for alias, spec in SPEC_CLASS_NAME.items()}


try:
    CLS = load_class_bits_from_spec()
except SpecOracleError as _spec_err:
    print("ERROR: classify oracle could not be derived from spec: %s" % _spec_err)
    sys.exit(1)

# ft / fo 10-class sample values
FT_CLASS_VALS = [
    ("negInf", 0xFF800000), ("negNormal", 0xBF800000),
    ("negSubnormal", 0x80000001), ("negZero", 0x80000000),
    ("posZero", 0x00000000), ("posSubnormal", 0x00000001),
    ("posNormal", 0x3F800000), ("posInf", 0x7F800000),
    ("sNaN", 0x7F800001), ("qNaN", 0x7FC00000),
]
FO_CLASS_VALS = [
    ("negInf", 0xFFF0000000000000), ("negNormal", 0xBFF0000000000000),
    ("negSubnormal", 0x8000000000000001), ("negZero", 0x8000000000000000),
    ("posZero", 0x0000000000000000), ("posSubnormal", 0x0000000000000001),
    ("posNormal", 0x3FF0000000000000), ("posInf", 0x7FF0000000000000),
    ("sNaN", 0x7FF0000000000001), ("qNaN", 0x7FF8000000000000),
]


def ieee_class(value, isdbl):
    """Classify a raw bit pattern by IEEE-754 rules only (no spec table, no QEMU).

    This is the value-level half of the oracle: it says which category a sample
    *is*, while the spec table says which bit that category uses."""
    if isdbl:
        val, signpos, mantbits, expbits = value & 0xFFFFFFFFFFFFFFFF, 63, 52, 11
    else:
        val, signpos, mantbits, expbits = value & 0xFFFFFFFF, 31, 23, 8
    sign = (val >> signpos) & 1
    exp = (val >> mantbits) & ((1 << expbits) - 1)
    man = val & ((1 << mantbits) - 1)
    if exp == (1 << expbits) - 1:
        if man == 0:
            return "negInf" if sign else "posInf"
        return "qNaN" if (man >> (mantbits - 1)) & 1 else "sNaN"
    if exp == 0:
        if man == 0:
            return "negZero" if sign else "posZero"
        return "negSubnormal" if sign else "posSubnormal"
    return "negNormal" if sign else "posNormal"


def check_class_oracle():
    """Cross-check the spec-derived masks against the 20 sample values.

    Two independent halves must agree: (1) the spec §7 table maps category ->
    bit, (2) IEEE-754 bit-pattern rules map each sample value -> category.
    Because every expectation is a single bit and the 10 masks are pairwise
    distinct/disjoint, a swapped spec row, a swapped implementation bit or a
    mislabelled sample makes this fail."""
    problems = []
    if len(CLS) != 10:
        problems.append("spec oracle has %d categories (expect 10)" % len(CLS))
    masks = sorted(CLS.values())
    if masks != [1 << i for i in range(10)]:
        problems.append("spec oracle masks %r are not the 10 single bits"
                        % masks)
    for label, vals, isdbl in (("FT", FT_CLASS_VALS, False),
                               ("FO", FO_CLASS_VALS, True)):
        names = [nm for nm, _ in vals]
        if len(names) != 10 or len(set(names)) != 10:
            problems.append("%s_CLASS_VALS names not 10 distinct: %r"
                            % (label, names))
            continue
        if set(names) != set(CLS):
            problems.append("%s_CLASS_VALS names %r != oracle %r"
                            % (label, sorted(names), sorted(CLS)))
        for nm, val in vals:
            derived = ieee_class(val, isdbl)
            if derived != nm:
                problems.append(
                    "%s sample 0x%0*X labelled %s but IEEE rules say %s"
                    % (label, 16 if isdbl else 8, val, nm, derived))
        ms = [CLS[nm] for nm in names]
        for nm, m in zip(names, ms):
            if m & (m - 1):
                problems.append("%s mask for %s is not a single bit: 0x%X"
                                % (label, nm, m))
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                if ms[i] & ms[j]:
                    problems.append("%s masks overlap: %s/0x%X vs %s/0x%X"
                                    % (label, names[i], ms[i],
                                       names[j], ms[j]))
    return problems


def print_class_oracle():
    """Print the spec -> bit mapping and the oracle cross-check result."""
    print("classify oracle: %s §7 (parsed, not hand-copied)" % SPEC_FP)
    for alias in ("sNaN", "qNaN", "negInf", "negNormal", "negSubnormal",
                  "negZero", "posZero", "posSubnormal", "posNormal", "posInf"):
        print("  %-13s spec=%-17s bit=%d"
              % (alias, SPEC_CLASS_NAME[alias], CLS[alias].bit_length() - 1))

CASES = []

# ── sign: fo (bit63) ───────────────────────────────────────────────────
CASES.append(value_case(
    "SG1 fosgnj (+1,+3) -> +1",
    set_rf(10, FO_P1) + set_rf(11, FO_P3) + [fosgnj(5, 10, 11)],
    expect_rf={5: FO_P1}))
CASES.append(value_case(
    "SG2 fosgnj (+1,-3) -> -1",
    set_rf(10, FO_P1) + set_rf(11, FO_N3) + [fosgnj(5, 10, 11)],
    expect_rf={5: FO_N1}))
CASES.append(value_case(
    "SG3 fosgnj (-1,+3) -> +1",
    set_rf(10, FO_N1) + set_rf(11, FO_P3) + [fosgnj(5, 10, 11)],
    expect_rf={5: FO_P1}))
CASES.append(value_case(
    "SG4 fosgnj (-1,-3) -> -1",
    set_rf(10, FO_N1) + set_rf(11, FO_N3) + [fosgnj(5, 10, 11)],
    expect_rf={5: FO_N1}))
CASES.append(value_case(
    "SG5 fosgnn (+1,+3) -> -1 (sign inverted)",
    set_rf(10, FO_P1) + set_rf(11, FO_P3) + [fosgnn(5, 10, 11)],
    expect_rf={5: FO_N1}))
CASES.append(value_case(
    "SG6 fosgnn (+1,-3) -> +1 (sign inverted)",
    set_rf(10, FO_P1) + set_rf(11, FO_N3) + [fosgnn(5, 10, 11)],
    expect_rf={5: FO_P1}))
CASES.append(value_case(
    "SG7 fosgnn (-1,+3) -> -1 (sign inverted)",
    set_rf(10, FO_N1) + set_rf(11, FO_P3) + [fosgnn(5, 10, 11)],
    expect_rf={5: FO_N1}))
CASES.append(value_case(
    "SG8 fosgnn (-1,-3) -> +1 (sign inverted)",
    set_rf(10, FO_N1) + set_rf(11, FO_N3) + [fosgnn(5, 10, 11)],
    expect_rf={5: FO_P1}))
CASES.append(value_case(
    "SG9 fosgnj (-1, rf0) -> abs = +1",
    set_rf(10, FO_N1) + [fosgnj(5, 10, 0)],
    expect_rf={5: FO_P1}))
CASES.append(value_case(
    "SG10 fosgnn (-1, rf0) -> -abs = -1",
    set_rf(10, FO_N1) + [fosgnn(5, 10, 0)],
    expect_rf={5: FO_N1}))
CASES.append(value_case(
    "SG11 fosgnj (-1,-1) HC==HD -> copy = -1",
    set_rf(10, FO_N1) + [fosgnj(5, 10, 10)],
    expect_rf={5: FO_N1}))
CASES.append(value_case(
    "SG12 fosgnn (-1,-1) HC==HD -> negate = +1",
    set_rf(10, FO_N1) + [fosgnn(5, 10, 10)],
    expect_rf={5: FO_P1}))

# ── sign: ft (bit31, full 64-bit convention) ───────────────────────────
FA = 0x123456783F800000       # bit31=0, high32=0x12345678
FB = 0xDEADBEEFBF800000       # bit31=1, high32=0xDEADBEEF
FC = 0xCAFEBABEBF800000       # bit31=1, high32=0xCAFEBABE
FD = 0x0000000040000000       # bit31=0, high32=0
CASES.append(value_case(
    "SG13 ftsgnj (bit31=0, bit31=1) -> set bit31, high32 preserved",
    set_rf(10, FA) + set_rf(11, FB) + [ftsgnj(5, 10, 11)],
    expect_rf={5: 0x12345678BF800000}))
CASES.append(value_case(
    "SG14 ftsgnn (bit31=0, bit31=1) -> clear bit31, high32 preserved",
    set_rf(10, FA) + set_rf(11, FB) + [ftsgnn(5, 10, 11)],
    expect_rf={5: 0x123456783F800000}))
CASES.append(value_case(
    "SG15 ftsgnj (bit31=1, bit31=0) -> clear bit31, high32 preserved",
    set_rf(10, FC) + set_rf(11, FD) + [ftsgnj(5, 10, 11)],
    expect_rf={5: 0xCAFEBABE3F800000}))
CASES.append(value_case(
    "SG16 ftsgnn (bit31=1, bit31=0) -> set bit31, high32 preserved",
    set_rf(10, FC) + set_rf(11, FD) + [ftsgnn(5, 10, 11)],
    expect_rf={5: 0xCAFEBABEBF800000}))
CASES.append(value_case(
    "SG17 ftsgnj (bit31=1, rf0) -> abs (clear bit31)",
    set_rf(10, FC) + [ftsgnj(5, 10, 0)],
    expect_rf={5: 0xCAFEBABE3F800000}))
CASES.append(value_case(
    "SG18 ftsgnn (bit31=1, rf0) -> -abs (set bit31)",
    set_rf(10, FC) + [ftsgnn(5, 10, 0)],
    expect_rf={5: 0xCAFEBABEBF800000}))
CASES.append(value_case(
    "SG19 ftsgnj (HC==HD, bit31=1) -> copy",
    set_rf(10, FC) + [ftsgnj(5, 10, 10)],
    expect_rf={5: 0xCAFEBABEBF800000}))
CASES.append(value_case(
    "SG20 ftsgnn (HC==HD, bit31=1) -> negate",
    set_rf(10, FC) + [ftsgnn(5, 10, 10)],
    expect_rf={5: 0xCAFEBABE3F800000}))

# ── sign: dst rf0 -> ILLI ──────────────────────────────────────────────
CASES.append(Case("FS1 ftsgnj dst rf0 -> ILLI",
                  [ftsgnj(0, 10, 11)], expect_exit=ILLI_EXIT))
CASES.append(Case("FS2 fosgnn dst rf0 -> ILLI",
                  [fosgnn(0, 10, 11)], expect_exit=ILLI_EXIT))

# ── classify: ft (low 32) all 10 classes ───────────────────────────────
for i, (nm, val) in enumerate(FT_CLASS_VALS):
    CASES.append(value_case(
        "CL%02d ftcls %s -> bit%d" % (i + 1, nm, CLS[nm].bit_length() - 1),
        set_rf(8, val) + [ftcls(4, 8, 1)],
        expect_rd={4: CLS[nm]}, classify={4: nm}))

# ── classify: fo all 10 classes ────────────────────────────────────────
for i, (nm, val) in enumerate(FO_CLASS_VALS):
    CASES.append(value_case(
        "CL%02d focls %s -> bit%d" % (i + 11, nm, CLS[nm].bit_length() - 1),
        set_rf(8, val) + [focls(4, 8, 1)],
        expect_rd={4: CLS[nm]}, classify={4: nm}))

# ── classify: block form, per-element results, [63:10] clear ───────────
CASES.append(value_case(
    "CL21 ftcls {rd4:rd6},{rf8:rf10} block of 3",
    set_rf(8, 0xFF800000) + set_rf(9, 0x00000000) + set_rf(10, 0x7FC00000) +
    [ftcls(4, 8, 3)],
    expect_rd={4: CLS["negInf"], 5: CLS["posZero"], 6: CLS["qNaN"]},
    classify={4: "negInf", 5: "posZero", 6: "qNaN"}))
CASES.append(value_case(
    "CL22 focls {rd4:rd6},{rf8:rf10} block of 3",
    set_rf(8, 0x8000000000000001) + set_rf(9, 0x7FF0000000000000) +
    set_rf(10, 0x7FF0000000000001) + [focls(4, 8, 3)],
    expect_rd={4: CLS["negSubnormal"], 5: CLS["posInf"], 6: CLS["sNaN"]},
    classify={4: "negSubnormal", 5: "posInf", 6: "sNaN"}))
CASES.append(value_case(
    "CL23 ftcls {rd4:rd6},{rf8:rf10} single element (immu6=1)",
    set_rf(8, 0x80000000) + [ftcls(4, 8, 1)],
    expect_rd={4: CLS["negZero"]}, classify={4: "negZero"}))

# ── classify: format boundaries (same class, different values) ─────────
# ft float32: max normal 0x7F7FFFFF, min normal 0x00800000,
#             max subnormal 0x007FFFFF, min normal (negative) 0x80800000
CASES.append(value_case(
    "CL24 ftcls max normal 0x7F7FFFFF -> posNormal",
    set_rf(8, 0x7F7FFFFF) + [ftcls(4, 8, 1)],
    expect_rd={4: CLS["posNormal"]}, classify={4: "posNormal"}))
CASES.append(value_case(
    "CL25 ftcls min normal 0x00800000 -> posNormal",
    set_rf(8, 0x00800000) + [ftcls(4, 8, 1)],
    expect_rd={4: CLS["posNormal"]}, classify={4: "posNormal"}))
CASES.append(value_case(
    "CL26 ftcls max subnormal 0x007FFFFF -> posSubnormal",
    set_rf(8, 0x007FFFFF) + [ftcls(4, 8, 1)],
    expect_rd={4: CLS["posSubnormal"]}, classify={4: "posSubnormal"}))
CASES.append(value_case(
    "CL27 ftcls min normal negative 0x80800000 -> negNormal",
    set_rf(8, 0x80800000) + [ftcls(4, 8, 1)],
    expect_rd={4: CLS["negNormal"]}, classify={4: "negNormal"}))
# fo float64: max normal 0x7FEFFFFFFFFFFFFF, min normal 0x0010000000000000,
#             max subnormal 0x000FFFFFFFFFFFFF
CASES.append(value_case(
    "CL28 focls max normal 0x7FEF_FFFFFFFFFFFF -> posNormal",
    set_rf(8, 0x7FEFFFFFFFFFFFFF) + [focls(4, 8, 1)],
    expect_rd={4: CLS["posNormal"]}, classify={4: "posNormal"}))
CASES.append(value_case(
    "CL29 focls min normal 0x0010_000000000000 -> posNormal",
    set_rf(8, 0x0010000000000000) + [focls(4, 8, 1)],
    expect_rd={4: CLS["posNormal"]}, classify={4: "posNormal"}))
CASES.append(value_case(
    "CL30 focls max subnormal 0x000F_FFFFFFFFFFFF -> posSubnormal",
    set_rf(8, 0x000FFFFFFFFFFFFF) + [focls(4, 8, 1)],
    expect_rd={4: CLS["posSubnormal"]}, classify={4: "posSubnormal"}))

# ── classify: legality ─────────────────────────────────────────────────
CASES.append(Case("FL1 ftcls immu6=0 -> ILLI",
                  [ftcls(4, 8, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL2 focls immu6=0 -> ILLI",
                  [focls(4, 8, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL3 ftcls src rf62+4>64 -> ILLI",
                  [ftcls(4, 62, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL4 ftcls dst rd60+8>64 -> ILLI",
                  [ftcls(60, 8, 8)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL5 focls src rf63+2>64 -> ILLI",
                  [focls(4, 63, 2)], expect_exit=ILLI_EXIT))
CASES.append(Case("FL6 focls dst rd63+2>64 -> ILLI",
                  [focls(63, 8, 2)], expect_exit=ILLI_EXIT))

# ── compare: ft (low 32, full 64-bit rd result) ────────────────────────
CASES.append(value_case(
    "CM01 ftqcmp 3>2 -> 1",
    set_rf(10, FT_P3) + set_rf(11, FT_P2) + [ftqcmp(4, 10, 11)],
    expect_rd={4: 1}))
CASES.append(value_case(
    "CM02 ftqcmp 2==2 -> 0",
    set_rf(10, FT_P2) + set_rf(11, FT_P2) + [ftqcmp(4, 10, 11)],
    expect_rd={4: 0}))
CASES.append(value_case(
    "CM03 ftqcmp 2<3 -> -1",
    set_rf(10, FT_P2) + set_rf(11, FT_P3) + [ftqcmp(4, 10, 11)],
    expect_rd={4: 0xFFFFFFFFFFFFFFFF}))
CASES.append(value_case(
    "CM04 ftqcmp +0 == -0 -> 0",
    set_rf(10, 0x00000000) + set_rf(11, 0x80000000) + [ftqcmp(4, 10, 11)],
    expect_rd={4: 0}))
CASES.append(value_case(
    "CM05 ftqcmp -0 == +0 -> 0",
    set_rf(10, 0x80000000) + set_rf(11, 0x00000000) + [ftqcmp(4, 10, 11)],
    expect_rd={4: 0}))
CASES.append(value_case(
    "CM06 ftqcmp -2 < +1 -> -1",
    set_rf(10, FT_N2) + set_rf(11, FT_P1) + [ftqcmp(4, 10, 11)],
    expect_rd={4: 0xFFFFFFFFFFFFFFFF}))
CASES.append(value_case(
    "CM07 ftqcmp -1 > -2 -> 1",
    set_rf(10, FT_N1) + set_rf(11, FT_N2) + [ftqcmp(4, 10, 11)],
    expect_rd={4: 1}))
CASES.append(value_case(
    "CM08 ftqcmp with qNaN -> ft qNaN (sign 0)",
    set_rf(10, FT_QNAN) + set_rf(11, FT_P2) + [ftqcmp(4, 10, 11)],
    expect_rd={4: FT_QNAN}))
CASES.append(value_case(
    "CM09 ftscmp with qNaN -> ft sNaN (sign 0)",
    set_rf(10, FT_QNAN) + set_rf(11, FT_P2) + [ftscmp(4, 10, 11)],
    expect_rd={4: FT_SNAN}))
CASES.append(value_case(
    "CM10 ftscmp with sNaN -> ft sNaN",
    set_rf(10, FT_SNAN) + set_rf(11, FT_P2) + [ftscmp(4, 10, 11)],
    expect_rd={4: FT_SNAN}))
CASES.append(value_case(
    "CM11 ftqcmp with sNaN -> ft qNaN",
    set_rf(10, FT_SNAN) + set_rf(11, FT_P2) + [ftqcmp(4, 10, 11)],
    expect_rd={4: FT_QNAN}))
CASES.append(value_case(
    "CM12 ftscmp normal 3>2 -> 1 (same as qcmp)",
    set_rf(10, FT_P3) + set_rf(11, FT_P2) + [ftscmp(4, 10, 11)],
    expect_rd={4: 1}))
CASES.append(value_case(
    "CM13 ftqcmp ignores high 32 bits (2.0 vs 1.0 with junk high)",
    set_rf(10, 0xFFFFFFFF40000000) + set_rf(11, 0xDEADBEEF3F800000) +
    [ftqcmp(4, 10, 11)],
    expect_rd={4: 1}))

# ── compare: fo ────────────────────────────────────────────────────────
CASES.append(value_case(
    "CM14 foqcmp 3>2 -> 1",
    set_rf(10, FO_P3) + set_rf(11, 0x4000000000000000) + [foqcmp(4, 10, 11)],
    expect_rd={4: 1}))
CASES.append(value_case(
    "CM15 foqcmp 2==2 -> 0",
    set_rf(10, 0x4000000000000000) + set_rf(11, 0x4000000000000000) +
    [foqcmp(4, 10, 11)],
    expect_rd={4: 0}))
CASES.append(value_case(
    "CM16 foqcmp 2<3 -> -1",
    set_rf(10, 0x4000000000000000) + set_rf(11, FO_P3) + [foqcmp(4, 10, 11)],
    expect_rd={4: 0xFFFFFFFFFFFFFFFF}))
CASES.append(value_case(
    "CM17 foqcmp +0 == -0 -> 0",
    set_rf(10, 0x0000000000000000) + set_rf(11, 0x8000000000000000) +
    [foqcmp(4, 10, 11)],
    expect_rd={4: 0}))
CASES.append(value_case(
    "CM18 foqcmp -1 > -2 -> 1",
    set_rf(10, FO_N1) + set_rf(11, 0xC000000000000000) + [foqcmp(4, 10, 11)],
    expect_rd={4: 1}))
CASES.append(value_case(
    "CM19 foqcmp with qNaN -> fo qNaN (sign 0)",
    set_rf(10, FO_QNAN) + set_rf(11, 0x4000000000000000) + [foqcmp(4, 10, 11)],
    expect_rd={4: FO_QNAN}))
CASES.append(value_case(
    "CM20 foscmp with qNaN -> fo sNaN (sign 0)",
    set_rf(10, FO_QNAN) + set_rf(11, 0x4000000000000000) + [foscmp(4, 10, 11)],
    expect_rd={4: FO_SNAN}))
CASES.append(value_case(
    "CM21 foscmp with sNaN -> fo sNaN",
    set_rf(10, FO_SNAN) + set_rf(11, 0x4000000000000000) + [foscmp(4, 10, 11)],
    expect_rd={4: FO_SNAN}))
CASES.append(value_case(
    "CM22 foqcmp with sNaN -> fo qNaN",
    set_rf(10, FO_SNAN) + set_rf(11, 0x4000000000000000) + [foqcmp(4, 10, 11)],
    expect_rd={4: FO_QNAN}))
CASES.append(value_case(
    "CM23 foscmp normal 2<3 -> -1 (same as qcmp)",
    set_rf(10, 0x4000000000000000) + set_rf(11, FO_P3) + [foscmp(4, 10, 11)],
    expect_rd={4: 0xFFFFFFFFFFFFFFFF}))

# ── E2E cases (in-ROM compare + SYS_EXIT) ────────────────────────────
_e1 = (set_rf(10, FO_N1) + set_rf(11, FO_N3) + [fosgnj(5, 10, 11), rf2rd(20, 5, 1)] +
       load_imm64_rd(22, FO_N1) + e2e_epilogue([(20, 22, 24)], 0x45))
CASES.append(Case("E1 fosgnj (-1,-3) -> -1 (SYS_EXIT assertion)", _e1,
                  expect_exit=PASS_EXIT, e2e=True))

_e2 = (set_rf(8, 0x7F800000) + [ftcls(4, 8, 1)] +
       load_imm64_rd(22, CLS["posInf"]) + e2e_epilogue([(4, 22, 24)], 0x46))
CASES.append(Case("E2 ftcls posInf bit set (SYS_EXIT assertion)", _e2,
                  expect_exit=PASS_EXIT, e2e=True))

_e3 = (set_rf(10, FT_P3) + set_rf(11, FT_P2) + [ftqcmp(4, 10, 11)] +
       load_imm64_rd(22, 1) + e2e_epilogue([(4, 22, 24)], 0x47))
CASES.append(Case("E3 ftqcmp 3>2 -> 1 (SYS_EXIT assertion)", _e3,
                  expect_exit=PASS_EXIT, e2e=True))


# ── Runner ────────────────────────────────────────────────────────────

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
        for idx, name in sorted(case.classify.items()):
            got = last_reg(log, 'RD', idx)
            bit = CLS[name].bit_length() - 1
            one = got is not None and got == (1 << bit)
            upper = got is not None and (got >> 10) == 0
            good = one and upper
            ok = ok and good
            details.append(
                f"RD[{idx:02d}] classify {name} bit{bit}: "
                f"exactly-1-bit={'OK' if one else 'FAIL'}, "
                f"[63:10]==0 {'OK' if upper else 'FAIL'} "
                f"(got={'0x%016X' % got if got is not None else 'MISSING'})")
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
    """Prove each assertion kind has a reachable FAIL path.

    Each case below carries a deliberately wrong expectation, so run_case()
    must report failure.  If any is reported OK the assertion machinery is
    broken (e.g. tautological comparison)."""
    os.chdir(_REPO_ROOT)
    print("=" * 78)
    print("QEMU-035t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    results = []

    # 1. RF value comparison (wrong expected rf value)
    c1 = value_case("selftest rf-value", set_rf(10, FO_N1) + [fosgnj(5, 10, 10)],
                    expect_rf={5: 0x0000000000000000})
    ok1, _ = run_case(c1)
    results.append(("RF value comparison FAIL path", ok1 is False))

    # 2. RD value comparison (wrong expected rd value)
    c2 = value_case("selftest rd-value", set_rf(10, FT_P3) + set_rf(11, FT_P2) +
                    [ftqcmp(4, 10, 11)], expect_rd={4: 0})
    ok2, _ = run_case(c2)
    results.append(("RD value comparison FAIL path", ok2 is False))

    # 3. fault case (illegal classify is caught; a legal one exits 0 != ILLI)
    c3 = Case("selftest fault", [ftcls(4, 8, 1)], expect_exit=ILLI_EXIT)
    ok3, _ = run_case(c3)
    results.append(("fault exit-code FAIL path", ok3 is False))

    # 4. E2E SYS_EXIT assertion (wrong expected -> FAIL arm -> exit != 0)
    insns = (set_rf(10, FT_P3) + set_rf(11, FT_P2) + [ftqcmp(4, 10, 11)] +
             load_imm64_rd(22, 0) + e2e_epilogue([(4, 22, 24)], 0x48))
    c4 = Case("selftest e2e", insns, expect_exit=PASS_EXIT, e2e=True)
    ok4, _ = run_case(c4)
    results.append(("E2E SYS_EXIT assertion FAIL path", ok4 is False))

    allok = True
    for name, v in results:
        if not v:
            allok = False
        print(f"  [{'PASS' if v else 'FAIL'}] {name} must be detected as FAIL")
    print(f"\nSelf-test: {'PASS' if allok else 'FAIL'}")
    return 0 if allok else 1


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    problems = check_class_oracle()
    if problems:
        print("ERROR: classify oracle cross-check failed:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print_class_oracle()

    print("=" * 78)
    print("QEMU-035t Min ROM Probe (FP bit-level: sign/classify/compare, 10 insns)")
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
        print_class_oracle()
        problems = check_class_oracle()
        for p in problems:
            print(f"  [FAIL] {p}")
        print("Oracle: %s (%d categories, bits %s)"
              % ("PASS" if not problems else "FAIL", len(CLS),
                 sorted(CLS[n].bit_length() - 1 for n in CLS)))
        sys.exit(0 if not problems else 1)
    sys.exit(main())
