#!/usr/bin/env python3
"""Min ROM probe for QEMU-033t: mreg_range_overlap run-time ILLI 0x88.

Spec: SimRISC-02 §寄存器组之间块赋值.
Rule: contracts/legality_rules.yaml `mreg_range_overlap` (kind: static, fault: ILLI).
      Same-group block copies (rd2rd / rb2rb) whose source range and destination
      range intersect (complete coincidence included) are illegal.
Exit code: ADR-0004 D5.8 — ILLI = 0x88 (returncode 136).

Cases (encodings taken from contracts/opcodes.yaml, not from QEMU):
  T1 rd2rd {rd4:rd5}, {rd2:rd3}  dst=[4,6) src=[2,4) disjoint      -> PASS (copy verified)
  T2 rd2rd {rd3:rd4}, {rd2:rd3}  dst=[3,5) src=[2,4) partial       -> ILLI 0x88
  T3 rd2rd {rd3:rd3}, {rd3:rd3}  dst=[3,4) src=[3,4) complete      -> ILLI 0x88
  T4 rd2rd {rd2:rd3}, {rd3:rd4}  dst=[2,4) src=[3,5) partial       -> ILLI 0x88
  T5 rb2rb {rb4:rb5}, {rb2:rb3}  dst=[4,6) src=[2,4) disjoint      -> PASS (copy verified)
  T6 rb2rb {rb3:rb4}, {rb2:rb3}  dst=[3,5) src=[2,4) partial       -> ILLI 0x88
  T7 rb2rb {rb3:rb3}, {rb3:rb3}  dst=[3,4) src=[3,4) complete      -> ILLI 0x88
  T8 rd2ra {ra3:ra4}, {rd3:rd4}  cross-group (RD->RA, same index)  -> PASS (copy verified)
  T9 rd2rb {rb3:rb4}, {rd3:rd4}  cross-group (RD->RB, same index)  -> PASS (copy verified)

Cross-group controls T8/T9 prove the check is applied to rd2rd/rb2rb only
(structurally non-overlapping groups are not affected).

Reverse gate: removing the overlap check makes T2/T3/T4/T6/T7 fall through to
the UNDI terminator (exit 0x89) instead of ILLI 0x88 => probe FAILs.

Layout convention (same as min_rom_probe_032t.py): ROM at 0xFFFFFFFF0000 with a
6-instruction trampoline; test instructions start at TEST_BASE = ROM_BASE+0x18.
"""
import os
import struct
import subprocess
import sys
import tempfile

# D6 compliance: resolve probe artifact dir via paths.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths


def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d


QEMU = ".work/build/qemu/qemu-system-dadao"

ROM_BASE = 0xFFFFFFFF0000
TEST_BASE = ROM_BASE + 0x18  # test instructions start after 6-insn trampoline


def addr_of(idx):
    """Byte address of test instruction at index idx."""
    return TEST_BASE + idx * 4


# ── Instruction encoding (op / ha values from contracts/opcodes.yaml) ──

def encode_riii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))


def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)


def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)


def encode_rrii(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)


def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)


def set_zw_rb(rb, immu16):
    return encode_rwii(0x4E, rb, 0, immu16)


def st_o_rd(rdha, rbhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)


def st_o_rd_pass():
    return st_o_rd(18, 16, 0)


def st_o_rd_fail():
    return st_o_rd(19, 16, 0)


def cmp_uo_rd(rdhb, rdhc, rdhd):
    return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)


def cmp_uo_dbb(rdhb, rbhc, rbhd):
    return encode_orri(0x40, 0x32, rdhb, rbhc, rbhd)


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


# Same-group block copies (mreg_range_overlap applies)
def rd2rd(rdhb, rdhc, immu6):
    return encode_orri(0x40, 0x2C, rdhb, rdhc, immu6 & 0x3F)


def rb2rb(rbhb, rbhc, immu6):
    return encode_orri(0x40, 0x34, rbhb, rbhc, immu6 & 0x3F)


# Cross-group block copies (mreg_range_overlap does NOT apply)
def rd2ra(rahb, rdhc, immu6):
    return encode_orri(0x40, 0x2D, rahb, rdhc, immu6 & 0x3F)


def ra2rd(rdhb, rahc, immu6):
    return encode_orri(0x40, 0x2E, rdhb, rahc, immu6 & 0x3F)


def rd2rb(rbhb, rdhc, immu6):
    return encode_orri(0x40, 0x35, rbhb, rdhc, immu6 & 0x3F)


def rb2rd(rdhb, rbhc, immu6):
    return encode_orri(0x40, 0x36, rdhb, rbhc, immu6 & 0x3F)


def swym():
    return struct.pack('>I', 0x77880000)


# ── Assertion block (same proven pattern as 030t / 032t) ───────────────
#
# Layout (N checks):
#   [2*i]   cmp(flag, actual_i, expected_i)   (cmp.uo for RD, cmp.uo for RB)
#   [2*i+1] br_nz(flag, 2*(N-i)+1)            → FAIL arm
#   [2*N]   set_zw(18, 0); [2*N+1] st_o_pass()   ← exit 0
#   [2*N+2] set_zw(19, fc); [2*N+3] st_o_fail()  ← exit fc

def build_assertion(checks, fail_code):
    N = len(checks)
    insns = []
    for i, (actual, expected, flag, bank) in enumerate(checks):
        offset = 2 * (N - i) + 1
        if bank == 'rb':
            insns.append(cmp_uo_dbb(flag, actual, expected))
        else:
            insns.append(cmp_uo_rd(flag, actual, expected))
        insns.append(br_nz(flag, offset))
    insns.append(set_zw_rd(18, 0))
    insns.append(st_o_rd_pass())
    insns.append(set_zw_rd(19, fail_code))
    insns.append(st_o_rd_fail())
    return insns


UNDI_TERMINATOR = b'\x08\x04\x00\x01'


def build_rom(test_insns):
    trampoline = [
        encode_rwii(0x4E, 1, 2, 0xFFFF),   # rb1 = 0xFFFF00000000 (stack)
        encode_rwii(0x4A, 1, 1, 0x00FF),   # rb1 = 0xFFFF00FF0000
        encode_rwii(0x4E, 2, 2, 0xFFFF),   # rb2 = 0xFFFF00000000 (RAM)
        encode_rwii(0x4E, 16, 2, 0xFFFF),  # rb16 = 0xFFFF00000000
        encode_rwii(0x4A, 16, 1, 0x8000),  # rb16 = 0xFFFF80000000 (exit port)
        encode_rwii(0x4E, 17, 2, 0xFFFF),  # rb17 = 0xFFFF00000000
    ]
    rom = b''.join(trampoline) + b''.join(test_insns) + UNDI_TERMINATOR
    while len(rom) < 64:
        rom += swym()
    return rom


# ── QEMU execution ─────────────────────────────────────────────────────

def run_test(rom_data, timeout=10):
    kernel_data = swym() * 4
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(kernel_data)
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


# ── Exit codes (ADR-0004 D5.8) ─────────────────────────────────────────

PASS_EXIT = 0x00
ILLI_EXIT = 0x88

# Expected values: set.zw writes word0 (bits[63:48]); the other 48 bits are 0.
VAL_A = 0x1111
VAL_B = 0x2222


# ── Test cases ─────────────────────────────────────────────────────────

def case_t1_rd2rd_disjoint():
    """rd2rd {rd4:rd5}, {rd2:rd3}: disjoint ranges -> legal copy, verify result."""
    insns = [
        set_zw_rd(2, VAL_A),          # src rd2
        set_zw_rd(3, VAL_B),          # src rd3
        rd2rd(4, 2, 2),               # rd4 <- rd2, rd5 <- rd3
        set_zw_rd(20, VAL_A),         # expected rd4
        set_zw_rd(21, VAL_B),         # expected rd5
    ]
    insns += build_assertion([(4, 20, 22, 'rd'), (5, 21, 23, 'rd')], 0x42)
    return insns, PASS_EXIT


def case_t2_rd2rd_partial():
    """rd2rd {rd3:rd4}, {rd2:rd3}: dst=[3,5) src=[2,4) -> ILLI."""
    return [set_zw_rd(2, VAL_A), set_zw_rd(3, VAL_B), rd2rd(3, 2, 2)], ILLI_EXIT


def case_t3_rd2rd_complete():
    """rd2rd {rd3:rd3}, {rd3:rd3}: identical 1-element ranges -> ILLI."""
    return [rd2rd(3, 3, 1)], ILLI_EXIT


def case_t4_rd2rd_partial_dst_first():
    """rd2rd {rd2:rd3}, {rd3:rd4}: dst=[2,4) src=[3,5) -> ILLI."""
    return [set_zw_rd(3, VAL_A), set_zw_rd(4, VAL_B), rd2rd(2, 3, 2)], ILLI_EXIT


def case_t5_rb2rb_disjoint():
    """rb2rb {rb4:rb5}, {rb2:rb3}: disjoint -> legal copy, verify result."""
    insns = [
        set_zw_rb(2, VAL_A),          # src rb2
        set_zw_rb(3, VAL_B),          # src rb3
        rb2rb(4, 2, 2),               # rb4 <- rb2, rb5 <- rb3
        set_zw_rb(20, VAL_A),         # expected rb4
        set_zw_rb(21, VAL_B),         # expected rb5
    ]
    insns += build_assertion([(4, 20, 22, 'rb'), (5, 21, 23, 'rb')], 0x42)
    return insns, PASS_EXIT


def case_t6_rb2rb_partial():
    """rb2rb {rb3:rb4}, {rb2:rb3}: dst=[3,5) src=[2,4) -> ILLI."""
    return [set_zw_rb(2, VAL_A), set_zw_rb(3, VAL_B), rb2rb(3, 2, 2)], ILLI_EXIT


def case_t7_rb2rb_complete():
    """rb2rb {rb3:rb3}, {rb3:rb3}: identical 1-element ranges -> ILLI."""
    return [rb2rb(3, 3, 1)], ILLI_EXIT


def case_t8_rd2ra_cross_group():
    """rd2ra {ra3:ra4}, {rd3:rd4}: cross-group same-index -> legal (not covered)."""
    insns = [
        set_zw_rd(3, VAL_A),          # src rd3
        set_zw_rd(4, VAL_B),          # src rd4
        rd2ra(3, 3, 2),               # ra3 <- rd3, ra4 <- rd4
        ra2rd(20, 3, 2),              # rd20 <- ra3, rd21 <- ra4 (read back)
        set_zw_rd(22, VAL_A),         # expected
        set_zw_rd(23, VAL_B),         # expected
    ]
    insns += build_assertion([(20, 22, 24, 'rd'), (21, 23, 25, 'rd')], 0x42)
    return insns, PASS_EXIT


def case_t9_rd2rb_cross_group():
    """rd2rb {rb3:rb4}, {rd3:rd4}: cross-group same-index -> legal (not covered)."""
    insns = [
        set_zw_rd(3, VAL_A),          # src rd3
        set_zw_rd(4, VAL_B),          # src rd4
        rd2rb(3, 3, 2),               # rb3 <- rd3, rb4 <- rd4
        rb2rd(20, 3, 2),              # rd20 <- rb3, rd21 <- rb4 (read back)
        set_zw_rd(22, VAL_A),         # expected
        set_zw_rd(23, VAL_B),         # expected
    ]
    insns += build_assertion([(20, 22, 24, 'rd'), (21, 23, 25, 'rd')], 0x42)
    return insns, PASS_EXIT


CASES = [
    ("T1 rd2rd {rd4:rd5},{rd2:rd3} disjoint -> PASS",
     case_t1_rd2rd_disjoint()),
    ("T2 rd2rd {rd3:rd4},{rd2:rd3} partial -> ILLI 0x88",
     case_t2_rd2rd_partial()),
    ("T3 rd2rd {rd3:rd3},{rd3:rd3} complete -> ILLI 0x88",
     case_t3_rd2rd_complete()),
    ("T4 rd2rd {rd2:rd3},{rd3:rd4} partial (dst first) -> ILLI 0x88",
     case_t4_rd2rd_partial_dst_first()),
    ("T5 rb2rb {rb4:rb5},{rb2:rb3} disjoint -> PASS",
     case_t5_rb2rb_disjoint()),
    ("T6 rb2rb {rb3:rb4},{rb2:rb3} partial -> ILLI 0x88",
     case_t6_rb2rb_partial()),
    ("T7 rb2rb {rb3:rb3},{rb3:rb3} complete -> ILLI 0x88",
     case_t7_rb2rb_complete()),
    ("T8 rd2ra {ra3:ra4},{rd3:rd4} cross-group -> PASS",
     case_t8_rd2ra_cross_group()),
    ("T9 rd2rb {rb3:rb4},{rd3:rd4} cross-group -> PASS",
     case_t9_rd2rb_cross_group()),
]


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 70)
    print("QEMU-033t Min ROM Probe (mreg_range_overlap run-time ILLI 0x88)")
    print("=" * 70)

    passed = failed = 0
    fail_details = []
    for name, (insns, expected) in CASES:
        rom = build_rom(insns)
        code, stderr = run_test(rom)
        if code == expected:
            status = "PASS"
            passed += 1
        elif code == -1:
            status = "TIMEOUT"
            failed += 1
            fail_details.append(f"  [TIMEOUT] {name}")
        else:
            status = "FAIL"
            failed += 1
            fail_details.append(
                f"  [FAIL] {name}: exit=0x{code:02X} (expect 0x{expected:02X})")
        print(f"  [{status}] {name}: exit=0x{code:02X} (expect 0x{expected:02X})")
        if stderr and code != expected:
            print(f"      stderr: {stderr[:200]}")

    print("-" * 70)
    print(f"Main: {passed}/{passed + failed} passed, {failed} failed")
    if fail_details:
        print("Failed:")
        for d in fail_details:
            print(d)

    all_pass = failed == 0
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
