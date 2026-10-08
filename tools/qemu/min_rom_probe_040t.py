#!/usr/bin/env python3
"""Min ROM probe for QEMU-040t: `sub.o rdhb, rbhc, rbhd` (RB − RB → RD) semantics.

Spec: ADR-0012 D9.1 / SimRISC-05 §加减操作.
Encoding (contracts/opcodes.yaml): op=0x40, ha=0x33, mask=0xFFFC0000, value=0x40CC0000.
Semantics: rdhb = rbhc − rbhd (full 64-bit two's-complement). ILLI: rdhb == rd0.
Exit codes (ADR-0004 D5.8): ILLI = 0x88 (136), UNDI = 0x89 (137).

Cases (encodings taken from contracts/opcodes.yaml, not from QEMU):
  T1 sub.o rd18, rb2, rb3   rb2=5,  rb3=2        -> rd18=3            (PASS)
  T2 sub.o rd18, rb2, rb3   rb2=2,  rb3=5        -> rd18=-3 (0xFF..FFFD)  (PASS)
  T3 sub.o rd18, rb2, rb3   rb2=0x2_0000_0000,
                            rb3=0x1_0000_0000    -> rd18=0x1_0000_0000  (full 64-bit, PASS)
  T4 sub.o rd0,  rb2, rb3   destination rd0      -> ILLI 0x88
  T5 reserved MISC-octa slot (110-111, ha=0x37)  -> UNDI 0x89 (decode still open)
  T6 sub.o rd18, rb0, rb3   rb0 as source (legal) -> rd18 = instr_addr - 4  (PASS)

Reverse gate: reverting trans_sub_o_orrr_dbb to an ILLI stub makes T1/T2/T3/T6
fall to ILLI 0x88 (not their expected values); widening the decode pattern so
that ha=0x37 also matches makes T5 exit 0 instead of UNDI 0x89.

Layout convention (same as min_rom_probe_033t.py): ROM at 0xFFFFFFFF0000 with a
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


def set_ow_rd(rd, immu16):
    """set.ow rd, immu16 (wp0): rd = immu16 | 0xFFFF_FFFF_FFFF_0000."""
    return encode_rwii(0x4D, rd, 0, immu16)


def set_zw_rb(rb, immu16):
    return encode_rwii(0x4E, rb, 0, immu16)


def or_w_rd(rd, wpN, immu16):
    return encode_rwii(0x48, rd, wpN, immu16)


def or_w_rb(rb, wpN, immu16):
    return encode_rwii(0x4A, rb, wpN, immu16)


def st_o_rd(rdha, rbhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)


# ── Semihosting SYS_EXIT (ADR-0020 D8: replaces the legacy MMIO halt device) ──

SEMI_BLOCK = 0xFFFF_00FF_F000       # argument block {reason, code}, in RAM
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026


def semi_exit(code_rd):
    """rb16 = SEMI_BLOCK; block = {0x20026, code_rd}; rd16 = 0x18; trap."""
    return ([encode_rwii(0x4E, 16, 2, 0xFFFF), encode_rwii(0x4A, 16, 1, 0x00FF),
             encode_rwii(0x4A, 16, 0, 0xF000)]
            + [encode_rwii(0x4C, 8, 0, 0x0026), encode_rwii(0x48, 8, 1, 0x0002)]
            + [st_o_rd(8, 16, 0)]
            + [st_o_rd(code_rd, 16, 8)]
            + [encode_rwii(0x4C, 16, 0, 0x0018)]
            + [encode_riii(0x7F, 0, SEMIHOST_TAG)])

def cmp_uo_rd(rdhb, rdhc, rdhd):
    return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)


def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)


def sub_o_dbb(rdhb, rbhc, rbhd):
    """sub.o rdhb, rbhc, rbhd — new instruction (ha=0x33)."""
    return encode_orri(0x40, 0x33, rdhb, rbhc, rbhd)


def reserved_octa_neighbor(rdhb, rbhc, rbhd):
    """Reserved MISC-octa slot 110-111 (ha=0x37) — must decode to UNDI."""
    return encode_orri(0x40, 0x37, rdhb, rbhc, rbhd)


def swym():
    return struct.pack('>I', 0x77880000)


# ── Assertion block (same proven pattern as 033t) ──────────────────────
#
# Layout (N checks):
#   [2*i]   cmp_uo_rd(flag_i, actual_i, expected_i)  → flag = (actual == expected) ? 0 : ±1
#   [2*i+1] br_nz(flag_i, 2*(N-i)+1)                 → non-zero (unequal) ⇒ FAIL arm
#   [2*N]   set_zw_rd(18, 0); [2*N+1] st_o_pass()       ← exit 0
#   [2*N+2] set_zw_rd(19, fc); [2*N+3] st_o_fail()      ← exit fc

def build_assertion(checks, fail_code):
    N = len(checks)
    pass_arm = [set_zw_rd(18, 0)] + semi_exit(18)           # PASS: exit 0
    fail_arm = [set_zw_rd(19, fail_code)] + semi_exit(19)   # FAIL: exit fail_code
    P = len(pass_arm)
    insns = []
    for i, (actual, expected, flag) in enumerate(checks):
        offset = 2 * (N - i) + (P - 1)
        insns.append(cmp_uo_rd(flag, actual, expected))
        insns.append(br_nz(flag, offset))
    insns += pass_arm
    insns += fail_arm
    return insns


UNDI_TERMINATOR = b'\x08\x04\x00\x01'


def build_rom(test_insns):
    trampoline = [
        encode_rwii(0x4E, 1, 2, 0xFFFF),   # rb1 = 0xFFFF00FF0000 (stack)
        encode_rwii(0x4A, 1, 1, 0x00FF),
        encode_rwii(0x4E, 2, 2, 0xFFFF),   # rb2 = 0xFFFF00000000 (RAM)
        encode_rwii(0x4E, 16, 2, 0xFFFF),  # rb16 = 0xFFFF00000000
        encode_rwii(0x4A, 16, 1, 0x00FF),  # rb16 = 0xFFFF80000000 (dead; semi_exit rebuilds it)
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
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp, '-semihosting-config', 'enable=on,target=native'],
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
UNDI_EXIT = 0x89


# ── Test cases ─────────────────────────────────────────────────────────

def case_t1_positive():
    """rb2=5, rb3=2 → rd18=3."""
    insns = [
        set_zw_rb(2, 5),
        set_zw_rb(3, 2),
        sub_o_dbb(18, 2, 3),        # rd18 = rb2 - rb3
        set_zw_rd(20, 3),           # expected
    ]
    insns += build_assertion([(18, 20, 22)], 0x41)
    return insns, PASS_EXIT


def case_t2_negative():
    """rb2=2, rb3=5 → rd18 = -3 = 0xFFFF_FFFF_FFFF_FFFD (full 64-bit)."""
    insns = [
        set_zw_rb(2, 2),
        set_zw_rb(3, 5),
        sub_o_dbb(18, 2, 3),        # rd18 = 2 - 5 = -3
        set_ow_rd(20, 0xFFFD),      # expected 0xFFFF_FFFF_FFFF_FFFD
    ]
    insns += build_assertion([(18, 20, 22)], 0x42)
    return insns, PASS_EXIT


def case_t3_full64_high_bits():
    """rb2=0x2_0000_0000, rb3=0x1_0000_0000 → rd18=0x1_0000_0000 (bit 32 participates)."""
    insns = [
        set_zw_rb(2, 0),
        or_w_rb(2, 2, 0x0002),      # rb2 = 0x0000_0002_0000_0000
        set_zw_rb(3, 0),
        or_w_rb(3, 2, 0x0001),      # rb3 = 0x0000_0001_0000_0000
        sub_o_dbb(18, 2, 3),        # rd18 = 0x0000_0001_0000_0000
        set_zw_rd(20, 0),
        or_w_rd(20, 2, 0x0001),     # expected 0x0000_0001_0000_0000
    ]
    insns += build_assertion([(18, 20, 22)], 0x43)
    return insns, PASS_EXIT


def case_t4_rd0_illi():
    """sub.o rd0, rb2, rb3 → ILLI (rdhb == rd0)."""
    return [set_zw_rb(2, 5), set_zw_rb(3, 2), sub_o_dbb(0, 2, 3)], ILLI_EXIT


def case_t5_reserved_neighbor_undi():
    """Reserved MISC-octa slot 110-111 (ha=0x37) → UNDI."""
    return [reserved_octa_neighbor(18, 2, 3)], UNDI_EXIT


def case_t6_rb0_source_legal():
    """rb0 as source is legal: rd18 = rb0 - 4 = (instruction address) - 4."""
    insns = [set_zw_rb(3, 4)]
    idx = len(insns)                # index of the sub.o instruction
    insns.append(sub_o_dbb(18, 0, 3))
    expected = addr_of(idx) - 4     # rb0 = current instruction address
    # Construct expected in rd20 (all four 16-bit words): 0x0000_FFFF_FFFF_00xx
    insns.append(set_zw_rd(20, expected & 0xFFFF))              # bits[15:0]
    insns.append(or_w_rd(20, 1, (expected >> 16) & 0xFFFF))     # bits[31:16]
    insns.append(or_w_rd(20, 2, (expected >> 32) & 0xFFFF))     # bits[47:32]
    insns.append(or_w_rd(20, 3, (expected >> 48) & 0xFFFF))     # bits[63:48]
    insns += build_assertion([(18, 20, 22)], 0x44)
    return insns, PASS_EXIT


CASES = [
    ("T1 sub.o rd18,rb2,rb3 (5-2=3) -> PASS", case_t1_positive()),
    ("T2 sub.o rd18,rb2,rb3 (2-5=-3, full 64-bit) -> PASS", case_t2_negative()),
    ("T3 sub.o rd18,rb2,rb3 (bit32 difference) -> PASS", case_t3_full64_high_bits()),
    ("T4 sub.o rd0,rb2,rb3 (dst rd0) -> ILLI 0x88", case_t4_rd0_illi()),
    ("T5 reserved octa slot ha=0x37 -> UNDI 0x89", case_t5_reserved_neighbor_undi()),
    ("T6 sub.o rd18,rb0,rb3 (rb0 source legal) -> PASS", case_t6_rb0_source_legal()),
]


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 70)
    print("QEMU-040t Min ROM Probe (sub.o_orrr_dbb: RB − RB → RD)")
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
