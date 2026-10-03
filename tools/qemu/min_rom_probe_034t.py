#!/usr/bin/env python3
"""Min ROM probe for QEMU-034t: FP execution-layer base + RF data-movement family.

Spec sources (expectations are derived by hand from these, never from QEMU):
  - spec/SimRISC-00 §浮点寄存器 / §浮点状态寄存器
  - spec/SimRISC-01 §存取RF寄存器
  - spec/SimRISC-02 §寄存器组之间块赋值 / §浮点条件赋值
  - spec/SimRISC-03 §立即数常数赋值：Immediate constant
  - .tao/knowledge/contract-fp.md §1 / §10 / §11 / §12 / §13
Encodings: contracts/opcodes.yaml.
Exit codes: ADR-0004 D5.8 (PASS=0x00, ILLI=0x88, MALIGN=0x8C).

Instructions under test (16):
  rf_mem  (8): ld.t ld.o ldm.t ldm.o st.t st.o stm.t stm.o  (-rf)
  rf_move (2): rd2rf rf2rd
  set_w   (1): set.w (-rf)
  cs_rf   (5): cs.n cs.z cs.p cs.eq cs.ne (-rf)

Verification channels:
  * value cases  -> QEMU `-d cpu` dump, parsing the *last* RF[]/RD[] dump
                    (state at the start of the fault TB, i.e. after commit).
  * fault cases  -> process exit code (ILLI 0x88 / MALIGN 0x8C).
  * E2E cases    -> in-ROM compare + exit-port PASS/FAIL epilogue.

Reverse gate (see .work/evidence/QEMU-034t/run.sh --inject): reverting any
implementation makes the corresponding cases FAIL.
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

# FCSR reset value (target/dadao/cpu.h::DADAO_RESET_RF0, SimRISC-00 §浮点状态寄存器)
RESET0 = 0x7FF800007FC00000
# FCSR write mask: [33:32] rounding mode + [4:0] exception status
FCSR_MASK = 0x000000030000001F

PASS_EXIT = 0x00
ILLI_EXIT = 0x88
MALIGN_EXIT = 0x8C

# ── Instruction encoding (op / ha values from contracts/opcodes.yaml) ──

ILLI = 0x77000000                 # illi 0 -> ILLI
SWYM = 0x77020000                 # swym (padding)
UNDI_TERMINATOR = 0x08040001      # 033t convention (never reached)


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


def encode_rrri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | (hd & 0x3F))


def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | (hd & 0x3F))


def encode_rrrr(op, ha, hb, hc, hd):
    return encode_orri(op, ha, hb, hc, hd)


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


def ld_ut_rd(rdha, rbhb, imms12):
    return encode_rrii(0x12, rdha, rbhb, imms12)


def ld_o_rd(rdha, rbhb, imms12):
    return encode_rrii(0x20, rdha, rbhb, imms12)


def st_o_rd(rdha, rbhb, imms12):
    return encode_rrii(0x21, rdha, rbhb, imms12)


def st_t_rd(rdha, rbhb, imms12):
    return encode_rrii(0x1A, rdha, rbhb, imms12)


def cmp_uo_rd(rdhb, rdhc, rdhd):
    return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


# Instructions under test
def ld_t_rf(rfha, rbhb, imms12):
    return encode_rrii(0x16, rfha, rbhb, imms12)


def st_t_rf(rfha, rbhb, imms12):
    return encode_rrii(0x17, rfha, rbhb, imms12)


def ld_o_rf(rfha, rbhb, imms12):
    return encode_rrii(0x26, rfha, rbhb, imms12)


def st_o_rf(rfha, rbhb, imms12):
    return encode_rrii(0x27, rfha, rbhb, imms12)


def ldm_t_rf(rfha, rbhb, rdhc, hd):
    return encode_rrri(0x2E, rfha, rbhb, rdhc, hd)


def stm_t_rf(rfha, rbhb, rdhc, hd):
    return encode_rrri(0x2F, rfha, rbhb, rdhc, hd)


def ldm_o_rf(rfha, rbhb, rdhc, hd):
    return encode_rrri(0x3E, rfha, rbhb, rdhc, hd)


def stm_o_rf(rfha, rbhb, rdhc, hd):
    return encode_rrri(0x3F, rfha, rbhb, rdhc, hd)


def rd2rf(rfhb, rdhc, hd):
    return encode_orri(0x40, 0x3D, rfhb, rdhc, hd)


def rf2rd(rdhb, rfhc, hd):
    return encode_orri(0x40, 0x3E, rdhb, rfhc, hd)


def set_w_rf(rfha, wpN, immu16):
    return encode_rwii(0x4F, rfha, wpN, immu16)


def cs_n_rf(rdha, rfhb, rfhc, rfhd):
    return encode_rrrr(0x61, rdha, rfhb, rfhc, rfhd)


def cs_z_rf(rdha, rfhb, rfhc, rfhd):
    return encode_rrrr(0x63, rdha, rfhb, rfhc, rfhd)


def cs_p_rf(rdha, rfhb, rfhc, rfhd):
    return encode_rrrr(0x65, rdha, rfhb, rfhc, rfhd)


def cs_eq_rf(rdha, rdhb, rfhc, rfhd):
    return encode_rrrr(0x5E, rdha, rdhb, rfhc, rfhd)


def cs_ne_rf(rdha, rdhb, rfhc, rfhd):
    return encode_rrrr(0x5F, rdha, rdhb, rfhc, rfhd)


def load_imm64_rd(rd, val):
    """Build an arbitrary 64-bit value in rd using set.zw + or.w (trusted M1)."""
    insns = [set_zw_rd(rd, val & 0xFFFF)]
    for wp in range(1, 4):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            insns.append(or_w_rd(rd, wp, w))
    return insns


def set_rf(rf, val):
    """Load rf[rf] = val (uses rd31 as scratch; rd2rf is itself under test)."""
    return load_imm64_rd(31, val) + [rd2rf(rf, 31, 1)]


# ── ROM assembly ───────────────────────────────────────────────────────

TRAMPOLINE = [
    set_zw_rb(16, 2, 0xFFFF), or_w_rb(16, 1, 0x8000),  # rb16 = 0xFFFF80000000 (exit port)
    set_zw_rb(17, 2, 0xFFFF),                          # rb17 = 0xFFFF00000000 (RAM)
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
    the exit port (exit 0x00), which differs from the expected fault code => FAIL.
    This gives every fault case a reachable FAIL path (appending ILLI instead
    would mask a missing legality check)."""
    return (b''.join(TRAMPOLINE) + b''.join(test_insns) +
            b''.join([set_zw_rd(18, 0), st_o_rd(18, 16, 0)]))


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
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp],
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


# ── E2E assertion epilogue (compare rd(s), exit port PASS/FAIL) ─────────

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


# ── Case model ─────────────────────────────────────────────────────────
#
# expect_exit           : plain run, check process exit code
# expect_rf / expect_rd : `-d cpu` run; ROM = insns + TB-split branch + illi;
#                         check parsed last-dump register values. The tb-split
#                         branch (`br_nz rd40, 1`, rd40=1) guarantees the writes
#                         are committed in an earlier TB than the fault dump.

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
    body = list(insns) + [br_nz(40, 1)]        # rd40=1 -> taken, target = next, TB split
    return Case(name, body, expect_exit=ILLI_EXIT,
                expect_rf=expect_rf, expect_rd=expect_rd)


# ══════════════════════════════════════════════════════════════════════
#  Case definitions
# ══════════════════════════════════════════════════════════════════════

CASES = []

# ── set.w-rf ──────────────────────────────────────────────────────────
CASES.append(value_case(
    "S1 set.w rf0 wp2=3 -> [33:32]=3, rest unchanged",
    [set_w_rf(0, 2, 0x0003)],
    expect_rf={0: RESET0 | (0x3 << 32)}))
CASES.append(value_case(
    "S2 set.w rf0 wp0=0x0011 -> [4:0]=0x11",
    [set_w_rf(0, 0, 0x0011)],
    expect_rf={0: RESET0 | 0x11}))
CASES.append(value_case(
    "S3 set.w rf0 wp1=0xFFFF -> complete no-op",
    [set_w_rf(0, 1, 0xFFFF)],
    expect_rf={0: RESET0}))
CASES.append(value_case(
    "S4 set.w rf0 wp3=0xFFFF -> complete no-op",
    [set_w_rf(0, 3, 0xFFFF)],
    expect_rf={0: RESET0}))
CASES.append(value_case(
    "S5 set.w rf5 wp1=0xABCD -> only that wyde set",
    [set_w_rf(5, 1, 0xABCD)],
    expect_rf={5: 0x00000000ABCD0000}))
CASES.append(value_case(
    "S6 set.w rf5 wp1=0xABCD + wp3=0x1234 -> other 48 bits preserved",
    [set_w_rf(5, 1, 0xABCD), set_w_rf(5, 3, 0x1234)],
    expect_rf={5: 0x12340000ABCD0000}))
CASES.append(value_case(
    "S7 set.w rf5 wp0=0xBEEF -> low wyde set",
    [set_w_rf(5, 0, 0xBEEF)],
    expect_rf={5: 0x000000000000BEEF}))

# ── rd2rf / rf2rd ─────────────────────────────────────────────────────
_RD2 = 0x1111222233334444
_RD3 = 0x5555666677778888
CASES.append(value_case(
    "M1 rd2rf {rf10:rf11},{rd2:rd3},2 -> per-element full word",
    load_imm64_rd(2, _RD2) + load_imm64_rd(3, _RD3) + [rd2rf(10, 2, 2)],
    expect_rf={10: _RD2, 11: _RD3}))
CASES.append(value_case(
    "M2 rd2rf dest rf0 -> FCSR write mask, rf1 full",
    load_imm64_rd(6, 0xFFFFFFFFFFFFFFFF) + load_imm64_rd(7, 0x00000000000000AA) +
    [rd2rf(0, 6, 2)],
    expect_rf={0: RESET0 | (0xFFFFFFFFFFFFFFFF & FCSR_MASK), 1: 0xAA}))
CASES.append(value_case(
    "M3 rf2rd {rd20:rd21},{rf0:rf1},2 -> full 64-bit rf0 read",
    [set_w_rf(0, 2, 0x0003), rf2rd(20, 0, 2)],
    expect_rd={20: RESET0 | (0x3 << 32), 21: 0x0000000000000000}))
CASES.append(value_case(
    "M4 rf2rd {rd20:rd21},{rf10:rf11},2 -> per-element full word",
    load_imm64_rd(2, _RD2) + load_imm64_rd(3, _RD3) + [rd2rf(10, 2, 2), rf2rd(20, 10, 2)],
    expect_rd={20: _RD2, 21: _RD3}))

# ── ld.t / st.t / ld.o / st.o (-rf) ───────────────────────────────────
_LV = 0xDEADBEEFCAFEBABE
CASES.append(value_case(
    "L1 st.o-rf/ld.o-rf round trip",
    set_rf(10, _LV) + [st_o_rf(10, 17, 0), ld_o_rf(11, 17, 0)],
    expect_rf={11: _LV}))
CASES.append(value_case(
    "L2 st.o-rf source rf0 -> full 64-bit read",
    [st_o_rf(0, 17, 8), ld_o_rd(20, 17, 8)],
    expect_rd={20: RESET0}))
CASES.append(value_case(
    "L3 ld.o-rf dest rf0 -> FCSR write mask",
    load_imm64_rd(30, 0x0000000700000003) + [st_o_rd(30, 17, 16), ld_o_rf(0, 17, 16)],
    expect_rf={0: RESET0 | (0x0000000700000003 & FCSR_MASK)}))
CASES.append(value_case(
    "L4 st.t-rf stores low 32 bits only",
    set_rf(10, 0xAABBCCDD11223344) + [st_t_rf(10, 17, 24), ld_ut_rd(20, 17, 24)],
    expect_rd={20: 0x0000000011223344}))
CASES.append(value_case(
    "L5 ld.t-rf into rf12 (low 32, sign-extended per task MO_BESL)",
    load_imm64_rd(30, 0x80000001) + [st_t_rd(30, 17, 28), ld_t_rf(12, 17, 28)],
    expect_rf={12: 0xFFFFFFFF80000001}))
CASES.append(value_case(
    "L6 ld.t-rf into rf0 keeps [63:32], writes low 32",
    load_imm64_rd(30, 0xDEADBEEF) + [st_t_rd(30, 17, 32), ld_t_rf(0, 17, 32)],
    expect_rf={0: (RESET0 & 0xFFFFFFFF00000000) | 0x00000000DEADBEEF}))

# ── ldm / stm (-rf) ───────────────────────────────────────────────────
_U1 = 0x0102030405060708
_U2 = 0xF1F2F3F4F5F6F7F8
_U3 = 0xDEADBEEF12345678
CASES.append(value_case(
    "U1 stm.o/ldm.o {rf10:rf12} multi round trip",
    set_rf(10, _U1) + set_rf(11, _U2) + set_rf(12, _U3) +
    [stm_o_rf(10, 17, 0, 3), ldm_o_rf(20, 17, 0, 3)],
    expect_rf={20: _U1, 21: _U2, 22: _U3}))
CASES.append(value_case(
    "U2 stm.t/ldm.t {rf10:rf12} multi round trip",
    set_rf(10, 0x0000000011223344) + set_rf(11, 0x0000000055667788) +
    set_rf(12, 0x00000000000000AA) +
    [stm_t_rf(10, 17, 0, 3), ldm_t_rf(20, 17, 0, 3)],
    expect_rf={20: 0x0000000011223344, 21: 0x0000000055667788, 22: 0x00000000000000AA}))
CASES.append(value_case(
    "U3 ldm.o with nonzero rd offset (rd5=64)",
    load_imm64_rd(5, 64) + set_rf(10, _U1) + set_rf(11, _U2) +
    [stm_o_rf(10, 17, 5, 2), ldm_o_rf(20, 17, 5, 2)],
    expect_rf={20: _U1, 21: _U2}))

# ── cs.*-rf ───────────────────────────────────────────────────────────
_CA = 0xAAAA5555AAAA5555
_CB = 0x5555AAAA5555AAAA
CASES.append(value_case(
    "C1 cs.n true (rd10<0) -> rf5=rf6",
    load_imm64_rd(10, 0xFFFFFFFFFFFFFFFF) + set_rf(6, _CA) + set_rf(7, _CB) +
    [cs_n_rf(10, 5, 6, 7)],
    expect_rf={5: _CA}))
CASES.append(value_case(
    "C2 cs.n false (rd10>0) -> rf5=rf7",
    load_imm64_rd(10, 1) + set_rf(6, _CA) + set_rf(7, _CB) +
    [cs_n_rf(10, 5, 6, 7)],
    expect_rf={5: _CB}))
CASES.append(value_case(
    "C3 cs.z true (rd10==0) -> rf5=rf6",
    [set_zw_rd(10, 0), ] + set_rf(6, _CA) + set_rf(7, _CB) + [cs_z_rf(10, 5, 6, 7)],
    expect_rf={5: _CA}))
CASES.append(value_case(
    "C4 cs.z false (rd10!=0) -> rf5=rf7",
    load_imm64_rd(10, 5) + set_rf(6, _CA) + set_rf(7, _CB) + [cs_z_rf(10, 5, 6, 7)],
    expect_rf={5: _CB}))
CASES.append(value_case(
    "C5 cs.p true (rd10>0) -> rf5=rf6",
    load_imm64_rd(10, 1) + set_rf(6, _CA) + set_rf(7, _CB) + [cs_p_rf(10, 5, 6, 7)],
    expect_rf={5: _CA}))
CASES.append(value_case(
    "C6 cs.p false (rd10<0) -> rf5=rf7",
    load_imm64_rd(10, 0xFFFFFFFFFFFFFFFF) + set_rf(6, _CA) + set_rf(7, _CB) +
    [cs_p_rf(10, 5, 6, 7)],
    expect_rf={5: _CB}))
CASES.append(value_case(
    "C7 cs.eq true (rd10==rd11) -> rf5=rf7",
    load_imm64_rd(10, 5) + load_imm64_rd(11, 5) + set_rf(5, _CA) + set_rf(7, _CB) +
    [cs_eq_rf(10, 11, 5, 7)],
    expect_rf={5: _CB}))
CASES.append(value_case(
    "C8 cs.eq false (rd10!=rd11) -> rf5 unchanged",
    load_imm64_rd(10, 5) + load_imm64_rd(11, 6) + set_rf(5, _CA) + set_rf(7, _CB) +
    [cs_eq_rf(10, 11, 5, 7)],
    expect_rf={5: _CA}))
CASES.append(value_case(
    "C9 cs.ne true (rd10!=rd11) -> rf5=rf7",
    load_imm64_rd(10, 5) + load_imm64_rd(11, 6) + set_rf(5, _CA) + set_rf(7, _CB) +
    [cs_ne_rf(10, 11, 5, 7)],
    expect_rf={5: _CB}))
CASES.append(value_case(
    "C10 cs.ne false (rd10==rd11) -> rf5 unchanged",
    load_imm64_rd(10, 5) + load_imm64_rd(11, 5) + set_rf(5, _CA) + set_rf(7, _CB) +
    [cs_ne_rf(10, 11, 5, 7)],
    expect_rf={5: _CA}))
CASES.append(value_case(
    "C16 cs.eq source rf0 -> full 64-bit read",
    load_imm64_rd(10, 7) + load_imm64_rd(11, 7) + set_rf(5, _CA) +
    [cs_eq_rf(10, 11, 5, 0)],
    expect_rf={5: RESET0}))
CASES.append(value_case(
    "C17 cs.n source rf0 -> full 64-bit read",
    load_imm64_rd(10, 0xFFFFFFFFFFFFFFFF) + set_rf(5, _CA) +
    [cs_n_rf(10, 5, 0, 7)],
    expect_rf={5: RESET0}))

# ── fault cases: ILLI 0x88 / MALIGN 0x8C ──────────────────────────────
CASES.append(Case("F1 rd2rf hd=0 -> ILLI", [rd2rf(10, 2, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("F2 rf2rd hd=0 -> ILLI", [rf2rd(20, 10, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("F3 rd2rf rfhb+hd>64 -> ILLI", [rd2rf(62, 2, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("F4 rd2rf rdhc+hd>64 -> ILLI", [rd2rf(10, 62, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("F5 rf2rd rdhb+hd>64 -> ILLI", [rf2rd(62, 10, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("F6 rf2rd rfhc+hd>64 -> ILLI", [rf2rd(20, 62, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("F7 ldm.t hd=0 -> ILLI", [ldm_t_rf(10, 17, 0, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("F8 stm.t hd=0 -> ILLI", [stm_t_rf(10, 17, 0, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("F9 ldm.o hd=0 -> ILLI", [ldm_o_rf(10, 17, 0, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("F10 stm.o hd=0 -> ILLI", [stm_o_rf(10, 17, 0, 0)], expect_exit=ILLI_EXIT))
CASES.append(Case("F11 ldm.t {rf62:rf65} -> ILLI", [ldm_t_rf(62, 17, 0, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("F12 stm.t {rf62:rf65} -> ILLI", [stm_t_rf(62, 17, 0, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("F13 ldm.o {rf62:rf65} -> ILLI", [ldm_o_rf(62, 17, 0, 4)], expect_exit=ILLI_EXIT))
CASES.append(Case("F14 stm.o {rf63:rf64} -> ILLI", [stm_o_rf(63, 17, 0, 2)], expect_exit=ILLI_EXIT))
CASES.append(Case("F15 ld.o-rf unaligned (RAM+1) -> MALIGN", [ld_o_rf(10, 17, 1)], expect_exit=MALIGN_EXIT))
CASES.append(Case("F16 ld.t-rf unaligned (RAM+2) -> MALIGN", [ld_t_rf(10, 17, 2)], expect_exit=MALIGN_EXIT))
CASES.append(Case("F17 st.o-rf unaligned (RAM+4) -> MALIGN", [st_o_rf(10, 17, 4)], expect_exit=MALIGN_EXIT))
CASES.append(Case("F18 st.t-rf unaligned (RAM+2) -> MALIGN", [st_t_rf(10, 17, 2)], expect_exit=MALIGN_EXIT))
CASES.append(Case("F19 ldm.o unaligned (offset rd6=1) -> MALIGN",
                  load_imm64_rd(6, 1) + [ldm_o_rf(20, 17, 6, 1)], expect_exit=MALIGN_EXIT))
CASES.append(Case("F20 cs.n dest rf0 -> ILLI", [cs_n_rf(10, 0, 6, 7)], expect_exit=ILLI_EXIT))
CASES.append(Case("F21 cs.z dest rf0 -> ILLI", [cs_z_rf(10, 0, 6, 7)], expect_exit=ILLI_EXIT))
CASES.append(Case("F22 cs.p dest rf0 -> ILLI", [cs_p_rf(10, 0, 6, 7)], expect_exit=ILLI_EXIT))
CASES.append(Case("F23 cs.eq dest rf0 (a->hc) -> ILLI", [cs_eq_rf(10, 11, 0, 7)], expect_exit=ILLI_EXIT))
CASES.append(Case("F24 cs.ne dest rf0 (a->hc) -> ILLI", [cs_ne_rf(10, 11, 0, 7)], expect_exit=ILLI_EXIT))

# ── E2E cases (in-ROM compare + exit port) ────────────────────────────
_e1 = (load_imm64_rd(30, _LV) + [st_o_rd(30, 17, 0), ld_o_rf(10, 17, 0), rf2rd(20, 10, 1)] +
       load_imm64_rd(22, _LV) + e2e_epilogue([(20, 22, 24)], 0x42))
CASES.append(Case("E1 ld.o-rf/st.o-rf round trip (exit-port assertion)", _e1,
                  expect_exit=PASS_EXIT, e2e=True))

_e2 = ([set_w_rf(0, 2, 0x0003), rf2rd(20, 0, 1)] +
       load_imm64_rd(22, RESET0 | (0x3 << 32)) + e2e_epilogue([(20, 22, 24)], 0x43))
CASES.append(Case("E2 set.w-rf rf0 mask + rf2rd (exit-port assertion)", _e2,
                  expect_exit=PASS_EXIT, e2e=True))

_e3 = (set_rf(6, _CA) + set_rf(7, _CB) + load_imm64_rd(10, 0xFFFFFFFFFFFFFFFF) +
       [cs_n_rf(10, 5, 6, 7), rf2rd(20, 5, 1)] +
       load_imm64_rd(22, _CA) + e2e_epilogue([(20, 22, 24)], 0x44))
CASES.append(Case("E3 cs.n true arm (exit-port assertion)", _e3,
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
        return ok, details
    else:
        if case.e2e:
            rom = build_e2e_rom(case.insns)
        elif case.expect_exit in (ILLI_EXIT, MALIGN_EXIT):
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

    Each case below carries a deliberately wrong expectation, so run_case() must
    report failure. If any of them is reported OK the assertion machinery is
    broken (e.g. tautological comparison), and the self-test fails.
    """
    os.chdir(_REPO_ROOT)
    print("=" * 78)
    print("QEMU-034t probe self-test (every assertion kind must be able to FAIL)")
    print("=" * 78)
    results = []

    # 1. RF value comparison (wrong expected rf value)
    c1 = value_case("selftest rf-value", [set_w_rf(5, 0, 0xBEEF)],
                    expect_rf={5: 0x0000000000000000})
    ok1, _ = run_case(c1)
    results.append(("RF value comparison FAIL path", ok1 is False))

    # 2. fault case (instruction is legal, so PASS epilogue exits 0 != ILLI)
    c2 = Case("selftest fault", [set_w_rf(5, 0, 0x0001)], expect_exit=ILLI_EXIT)
    ok2, _ = run_case(c2)
    results.append(("fault exit-code FAIL path", ok2 is False))

    # 3. E2E exit-port assertion (wrong expected -> FAIL arm -> exit 0x42 != 0)
    insns = (load_imm64_rd(30, 0xDEADBEEFCAFEBABE) +
             [st_o_rd(30, 17, 0), ld_o_rf(10, 17, 0), rf2rd(20, 10, 1)] +
             load_imm64_rd(22, 0xDEADBEEFCAFEBABF) +
             e2e_epilogue([(20, 22, 24)], 0x42))
    c3 = Case("selftest e2e", insns, expect_exit=PASS_EXIT, e2e=True)
    ok3, _ = run_case(c3)
    results.append(("E2E exit-port assertion FAIL path", ok3 is False))

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

    print("=" * 78)
    print("QEMU-034t Min ROM Probe (FP base + RF data-movement family, 16 insns)")
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
