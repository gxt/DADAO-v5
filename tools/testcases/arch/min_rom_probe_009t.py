#!/usr/bin/env python3
"""Min ROM probe for op 0x5A: `aip.si rbha, imms18` (formerly `rela.si`).

History: QEMU-009t verified `rela.si` (page-aligned base `PC & ~0xFFF`).  That
instruction was deleted and op 0x5A was re-assigned to `aip.si`
(ADR-0029 D1; SPEC-164t does not touch it).  The probe body is kept, but the
oracle is now the *current* contract:

- `rbha = IP + (sign_extend(imms18) << 12)`, full 64-bit arithmetic
- `IP` = address of the executing instruction itself (= `rb0` read value),
  no `±4` pipeline bias and **no page masking**
- `ha==0` (rb0 destination) → ILLI (0x88)
- the destination's previous high 16 bits are ignored (full 64-bit result)

Exit codes (ADR-0004 D5.8):
  0x00 = PASS, 0x88 = ILLI, 0x89 = UNDI, 0x8A = RASOF, 0x8B = RASUF

Usage: python3 tools/testcases/arch/min_rom_probe_009t.py
"""

import struct
import subprocess
import sys
import os
import tempfile

# D6 compliance: resolve probe artifact dir via paths.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths

def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d

QEMU = ".work/build/qemu/qemu-system-dadao"

# ── Instruction encoding ──────────────────────────────────────────────

def encode_rrii(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_riii(op, ha, imms18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (imms18 & 0x3FFFF))

def encode_iiii(op, immu24):
    return struct.pack('>I', (op << 24) | (immu24 & 0xFFFFFF))

def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_orrr(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_oiii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)

def set_ow_rd(rd, wpN, immu16):
    """set.ow rd, wpN, immu16 (op=0x4D)"""
    return encode_rwii(0x4D, rd, wpN, immu16)

def set_zw_rb(rb, immu16):
    return encode_rwii(0x4E, rb, 0, immu16)

def or_w_rb(rb, wpN, immu16):
    return encode_rwii(0x4A, rb, wpN, immu16)

def or_w_rd(rd, wpN, immu16):
    return encode_rwii(0x48, rd, wpN, immu16)

def add_si_rd(rd, imms18):
    return encode_riii(0x59, rd, imms18 & 0x3FFFF)

def add_si_rb(rb, imms18):
    return encode_riii(0x5B, rb, imms18 & 0x3FFFF)

def add_o_bbd(rbhb, rbhc, rdhd):
    """add.o rbhb, rbhc, rdhd (OPC-octa, ha=0x30)"""
    return encode_orrr(0x40, 0x30, rbhb, rbhc, rdhd)

def sub_o_bbd(rbhb, rbhc, rdhd):
    """sub.o rbhb, rbhc, rdhd (OPC-octa, ha=0x31)"""
    return encode_orrr(0x40, 0x31, rbhb, rbhc, rdhd)

def cmp_uo_rd(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd (OPC-octa, ha=0x2A)"""
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def cmp_uo_dbb(rdhb, rbhc, rbhd):
    """cmp.uo rdhb, rbhc, rbhd (OPC-octa, ha=0x32)"""
    return encode_orrr(0x40, 0x32, rdhb, rbhc, rbhd)

def xor_o(rdhb, rdhc, rdhd):
    """xor.o rdhb, rdhc, rdhd (OPC-octa, ha=0x0A)"""
    return encode_orrr(0x40, 0x0A, rdhb, rdhc, rdhd)

def and_o(rdhb, rdhc, rdhd):
    """and.o rdhb, rdhc, rdhd (OPC-octa, ha=0x08)"""
    return encode_orrr(0x40, 0x08, rdhb, rdhc, rdhd)

def ld_o_rd(rdha, rbhb, imms12):
    """ld.o rdha, rbhb, imms12 (op=0x20)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x20, rdha, rbhb, hc, hd)

def st_o_rd(rdha, rbhb, imms12):
    """st.o rdha, rbhb, imms12 (op=0x21)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)

def ld_o_rb(rbha, rbhb, imms12):
    """ld.o-rb rbha, rbhb, imms12 (op=0x22)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x22, rbha, rbhb, hc, hd)

def st_o_rb(rbha, rbhb, imms12):
    """st.o-rb rbha, rbhb, imms12 (op=0x23)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x23, rbha, rbhb, hc, hd)

def rb2rd(rdha, rbhb, immu6):
    """rb2rd rdha, rbhb, immu6 (OPC-octa, ha=0x36)"""
    return encode_orrr(0x40, 0x36, rdha, rbhb, immu6)

def rd2rb(rbha, rdhb, immu6):
    """rd2rb rbha, rdhb, immu6 (OPC-octa, ha=0x37)"""
    return encode_orrr(0x40, 0x37, rbha, rdhb, immu6)

def rb2rb(rbha, rbhb, immu6):
    """rb2rb rbha, rbhb, immu6 (OPC-octa, ha=0x34)"""
    return encode_orrr(0x40, 0x34, rbha, rbhb, immu6)

def aip_si_rb(rbha, imms18):
    """aip.si rbha, imms18 (op=0x5A; formerly rela.si, ADR-0029 D1)."""
    return encode_riii(0x5A, rbha, imms18 & 0x3FFFF)

def br_ne(rdha, rdhb, imms12):
    """br.ne rdha, rdhb, imms12 (op=0x6F)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x6F, rdha, rdhb, hc, hd)

def fence():
    """fence cfx0, 0 (ciii op=0x79; ADR-0044: no-op padding)."""
    return struct.pack('>I', 0x79000000)

def swym():
    return encode_oiii(0x47, 0x22, 0)

def illi_poison():
    """fence cfx0, hb=1 (op=0x79, immu18=0x1000) — ILLI poison after fence
    became an implemented instruction (SPEC-164t)."""
    return encode_oiii(0x79, 0x00, 0x1000)

def trap_sys_exit():
    """trap cfx_umon, 0x3FF00 — semihosting tag (immu18[17:8]==0x3FF (0x3FF00-0x3FFFF))."""
    return encode_oiii(0x7F, 0x00, SEMIHOST_TAG)

# ── Semihosting SYS_EXIT (ADR-0020 D8: exit port removed) ──────────────
# The exit channel is the semihosting SYS_EXIT service.  `aip.si` (op 0x5A) is
# a live M1 instruction (ADR-0029), so this probe now runs against the current
# contract (see the module docstring).

SEMI_BLOCK = 0xFC00_00FF_F000       # {reason, code} block inside RAM (16 MiB)
SEMIHOST_TAG = 0x3FF00              # immu18[17:8] == 0x3FF (0x3FF00-0x3FFFF) -> semihosting trap

def semi_exit(code_rd):
    """store code_rd into SEMI_BLOCK[1] then `trap` (SYS_EXIT); +1 insn."""
    return [st_o_rd(code_rd, 16, 8), trap_sys_exit()]

# ── Terminators ───────────────────────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

# ── ROM builder ───────────────────────────────────────────────────────

def build_rom(test_insns):
    """Build ROM: [trampoline | test_insns | UNDI | padding].

    Trampoline sets rb1=SP, rb2=rb17=RAM base, and primes the semihosting
    SYS_EXIT argument block (ADR-0020 D8)."""
    trampoline = [
        encode_rwii(0x4E, 1, 0, 0x0000),   # set.zw rb1, wp0, 0x0000
        encode_rwii(0x4A, 1, 1, 0x00FF),   # or.w rb1, wp1, 0x00FF (SP)
        encode_rwii(0x4A, 1, 2, 0xFC00),
        encode_rwii(0x4E, 2, 2, 0xFC00),   # set.zw rb2, wp0, 0x0000
        encode_rwii(0x4E, 16, 0, 0x0000),  # set.zw rb16, wp0, 0x0000
        encode_rwii(0x4A, 16, 1, 0x00FF),  # or.w rb16, wp1, 0x00FF
        encode_rwii(0x4A, 16, 0, 0xF000),  # or.w rb16, wp0, 0xF000 (block)
        encode_rwii(0x4A, 16, 2, 0xFC00),
        encode_rwii(0x4C, 8, 0, 0x0026),   # set.zw rd8, wp0, 0x0026
        encode_rwii(0x48, 8, 1, 0x0002),   # or.w rd8, wp1, 0x0002 -> rd8 = 0x20026
        encode_rrii(0x21, 8, 16, 0, 0),    # block[0] = 0x20026
        encode_rwii(0x4C, 16, 0, 0x0018),  # set.zw rd16, wp0, 0x0018 (SYS_EXIT)
        encode_rwii(0x4E, 17, 2, 0xFC00),  # set.zw rb17, wp0, 0x0000 (RAM base)
    ]
    rom = b''
    for insn in trampoline:
        rom += insn
    for insn in test_insns:
        rom += insn
    rom += UNDI_TERMINATOR
    while len(rom) < 64:
        rom += fence()
    return rom

def run_test(rom_data, kernel_data=None, timeout=10):
    if kernel_data is None:
        kernel_data = fence() * 4
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(rom_data); rom_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(kernel_data); kernel_path = f.name
    try:
        result = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic',
             '-bios', rom_path, '-kernel', kernel_path,
             '-semihosting-config', 'enable=on,target=native'],
            capture_output=True, timeout=timeout, text=True)
        return result.returncode, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rom_path); os.unlink(kernel_path)

# ── Exit codes ────────────────────────────────────────────────────────

PASS_EXIT = 0
ILLI_EXIT = 136    # 0x88
UNDI_EXIT = 137    # 0x89
RASOF_EXIT = 138   # 0x8A
RASUF_EXIT = 139   # 0x8B
MALIGN_EXIT = 140  # 0x8C

# ── Helper: set up rb18 as a scratch address ──────────────────────────
# rb18 = 0x0000_FFFF_0000_0100 (RAM + 0x100)

SETUP_RB18 = [
    encode_rwii(0x4E, 18, 2, 0xFC00),  # set.zw rb18, wp2, 0xFFFF
    encode_rwii(0x4A, 18, 0, 0x0100),  # or.w rb18, wp0, 0x0100 → RAM+0x100
]

# ── Exact-value aip.si checker (rework: assert the value, not just "no crash") ──
# 期望值由 Python 按 contract-isa §7（aip.si）+ ADR-0029 D1 独立算出（不从实现反推）：
#   result = (IP + (sext(imms18) << 12)) mod 2^64      （整 64 位，无页对齐）
# IP = ROM_BASE + (TRAMPOLINE_LEN + aip_idx) * 4（aip 在本测试内的下标）

ROM_BASE = 0xFFFFFFFF0000
TRAMPOLINE_LEN = 13         # len(build_rom()'s trampoline list)
EXACT_EXP_RB = 20           # scratch RB holding the expected value
EXACT_RD_CMP = 21           # scratch RD holding the cmp result
EXACT_RD_ZERO = 22          # scratch RD holding 0

def load_rb64(rb, value):
    """Load a full 64-bit constant into an RB (set.zw wp3 + or.w wp2/wp1/wp0)."""
    return [
        encode_rwii(0x4E, rb, 3, (value >> 48) & 0xFFFF),
        encode_rwii(0x4A, rb, 2, (value >> 32) & 0xFFFF),
        encode_rwii(0x4A, rb, 1, (value >> 16) & 0xFFFF),
        encode_rwii(0x4A, rb, 0, value & 0xFFFF),
    ]

def aip_exact_test(dest_rb, imm_signed, dest_high16=0, dest_low48=None):
    """set dest -> aip.si dest, imm -> compare dest against the §7 expectation."""
    seq = [encode_rwii(0x4E, dest_rb, 3, dest_high16 & 0xFFFF)]   # set.zw dest, wp3, high16
    if dest_low48 is not None:
        seq += [
            encode_rwii(0x4A, dest_rb, 2, (dest_low48 >> 32) & 0xFFFF),
            encode_rwii(0x4A, dest_rb, 1, (dest_low48 >> 16) & 0xFFFF),
            encode_rwii(0x4A, dest_rb, 0, dest_low48 & 0xFFFF),
        ]
    aip_idx = len(seq)
    pc = ROM_BASE + (TRAMPOLINE_LEN + aip_idx) * 4
    expected = (pc + (imm_signed << 12)) & 0xFFFFFFFFFFFFFFFF
    seq.append(aip_si_rb(dest_rb, imm_signed & 0x3FFFF))
    seq += load_rb64(EXACT_EXP_RB, expected)
    seq += [
        cmp_uo_dbb(EXACT_RD_CMP, dest_rb, EXACT_EXP_RB),   # 0 if equal
        set_zw_rd(EXACT_RD_ZERO, 0x0000),
        br_ne(EXACT_RD_CMP, EXACT_RD_ZERO, 4),            # != 0 (mismatch) -> FAIL
        set_zw_rd(18, 0x0000), *semi_exit(18),        # equal: PASS (fall-through)
        set_zw_rd(18, 0x0001), *semi_exit(18),        # not-equal: FAIL (branch target)
    ]
    return seq

# ── Test cases ────────────────────────────────────────────────────────

TESTS = [
    # ── aip.si exact-value verification (IP-relative, ADR-0029 D1) ────

    # T1: aip.si rb1, imms18=0 → rb1 = IP (the aip instruction's own address)
    ("T1 aip.si rb1 imms18=0 (exact value)",
     aip_exact_test(1, 0, 0xABCD),
     PASS_EXIT,
     "aip.si rb1 value wrong (base/offset)"),

    # T2: aip.si rb2, imms18=1 → rb2 = IP + 0x1000
    ("T2 aip.si rb2 imms18=1 (exact value, +1 page)",
     aip_exact_test(2, 1, 0xABCD),
     PASS_EXIT,
     "aip.si rb2 value wrong (offset <<12 not applied?)"),

    # T3: aip.si rb3, imms18=-1 → rb3 = IP - 0x1000 (18-bit signed)
    ("T3 aip.si rb3 imms18=-1 (exact value, -1 page)",
     aip_exact_test(3, -1, 0xABCD),
     PASS_EXIT,
     "aip.si rb3 value wrong (negative offset sign?)"),

    # T4: aip.si rb0 → ILLI (destination rb0 illegal, rule dst_rb0)
    ("T4 aip.si rb0 → ILLI",
     [aip_si_rb(0, 0)],
     ILLI_EXIT,
     "aip.si rb0 not ILLI"),

    # T5: destination preloaded with a full 64-bit value → result is IP, not
    # that value (IP is not the destination register).
    ("T5 aip.si base=IP not dest self-ref (exact, dest preloaded)",
     aip_exact_test(5, 0, 0x1234, 0x56789ABC),
     PASS_EXIT,
     "aip.si rb5 value wrong (base is destination self-reference?)"),

    # T6: offset 2 pages, exact value
    ("T6 aip.si rb6 imms18=2 (exact value, offset applied)",
     aip_exact_test(6, 2, 0xAAAA),
     PASS_EXIT,
     "aip.si rb6 value wrong (offset formula)"),

    # T7: destination high 16 bits are ignored (full 64-bit result, no
    # page masking and no high-half preservation)
    ("T7 aip.si ignores dest high 16 bits (exact, dest high16=0xFFFF)",
     aip_exact_test(7, 0, 0xFFFF, 0x12345678),
     PASS_EXIT,
     "aip.si rb7 result is not the full 64-bit IP+offset"),

    # T8: full 64-bit result with a preloaded destination
    ("T8 aip.si rb8 imms18=0 (exact value, dest preloaded)",
     aip_exact_test(8, 0, 0x1111, 0x222233334444),
     PASS_EXIT,
     "aip.si rb8 value wrong"),

    # T9: negative offset -2 pages, exact value
    ("T9 aip.si negative offset -2 (exact value)",
     aip_exact_test(9, -2, 0xABCD),
     PASS_EXIT,
     "aip.si rb9 value wrong (negative offset)"),

    # T10: large positive offset (imms18 = 0x1FFFF, 18-bit max positive)
    ("T10 aip.si large positive offset (exact value, imms18=0x1FFFF)",
     aip_exact_test(10, 0x1FFFF, 0xABCD),
     PASS_EXIT,
     "aip.si rb10 value wrong (large offset / sign extension)"),

    # T11: base is IP, not the destination's old value (strong check)
    ("T11 aip.si base=IP not dest old value (strong check)",
     [set_zw_rb(11, 0x1234),     # rb11 = 0x0000123400000000
      or_w_rb(11, 1, 0x5678),    # rb11 = 0x0000123456780000
      or_w_rb(11, 0, 0x9ABC),    # rb11 = 0x0000123456789ABC
      aip_si_rb(11, 0),          # rb11 = IP
      st_o_rb(11, 17, 0),        # store rb11 to RAM base
      ld_o_rd(12, 17, 0),        # load to rd12
      set_zw_rd(13, 0x1234),     # rd13 = 0x1234
      or_w_rd(13, 1, 0x5678),    # rd13 = 0x12345678
      or_w_rd(13, 0, 0x9ABC),    # rd13 = 0x123456789ABC
      cmp_uo_rd(14, 12, 13),     # rd14 = cmp(rd12, old value)
      set_zw_rd(15, 0x0000),
      br_ne(14, 15, 4),          # not equal (correct) → skip FAIL → PASS
      set_zw_rd(18, 0x0001),     # equal: FAIL (dest self-reference)
      *semi_exit(18),
      set_zw_rd(18, 0x0000),     # not-equal: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "aip.si base is the destination's old value (should be IP)"),

    # T12: full 64-bit result equals IP (no 48-bit truncation, no high-half
    # preservation).  The old "high 16 preserved" check is obsolete: aip.si is
    # a full 64-bit operation.
    ("T12 aip.si full 64-bit result equals IP (strong check)",
     [set_zw_rb(12, 0x1234),     # rb12 = 0x0000000000001234 (wp0 = 0x1234)
      or_w_rb(12, 3, 0x1234),    # rb12 = 0x1234000000001234
      aip_si_rb(12, 0),          # rb12 = IP (full 64-bit)
      rb2rd(13, 12, 1),          # rd13 = actual
      *load_rb64(20, ROM_BASE + (TRAMPOLINE_LEN + 2) * 4),  # expected IP
      rb2rd(14, 20, 1),          # rd14 = expected
      cmp_uo_rd(15, 13, 14),     # 0 if equal
      set_zw_rd(17, 0x0000),
      br_ne(15, 17, 4),          # not equal → FAIL
      set_zw_rd(18, 0x0000),     # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),     # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "aip.si full 64-bit result != IP"),
]

# ── CTL self-check ────────────────────────────────────────────────────

CTL_CHECKS = [
    ("CTL: st.o PASS but expect ILLI (wrong)",
     [set_zw_rd(18, 0x0000), *semi_exit(18)],
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect wrong values"),
    ("CTL: ILLI but expect PASS (wrong)",
     [illi_poison()],
     PASS_EXIT,
     "Self-check FAILED: probe cannot detect ILLI"),
]

# ── Runner ────────────────────────────────────────────────────────────

def run_test_group(tests, group_name):
    passed = failed = 0
    fail_details = []
    for item in tests:
        name, insns, expected, fail_desc = item
        rom = build_rom(insns)
        code, stderr = run_test(rom)
        if code == expected:
            status = "PASS"; passed += 1
        else:
            status = "FAIL"; failed += 1
            fail_details.append((name, expected, code, fail_desc))
        print(f"  {status} {name} (exit=0x{code:02X}, expect=0x{expected:02X})")
    return passed, failed, fail_details

def main():
    print("=== QEMU-009t: rela.si base address verification ===\n")

    # Run CTL self-checks first
    print("CTL self-checks (should FAIL to prove probe can detect errors):")
    ctl_passed, ctl_failed, ctl_details = run_test_group(CTL_CHECKS, "CTL")
    if ctl_failed == len(CTL_CHECKS):
        print("  ✓ CTL: All self-checks failed as expected (probe can detect errors)\n")
    else:
        print(f"  ✗ CTL: {ctl_passed}/{len(CTL_CHECKS)} passed (should all fail!)\n")

    # Run main tests
    print("Main tests:")
    main_passed, main_failed, main_details = run_test_group(TESTS, "Main")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Main results: {main_passed}/{main_passed + main_failed} passed, {main_failed} failed")
    if ctl_failed == len(CTL_CHECKS):
        print(f"CTL self-check: OK (can detect errors)")
    else:
        print(f"CTL self-check: FAILED (cannot detect errors!)")

    if main_failed == 0 and ctl_failed == len(CTL_CHECKS):
        print("Overall: PASS      PROBE_EXIT=0")
        return 0
    else:
        print("Overall: FAIL      PROBE_EXIT=1")
        if main_details:
            print("\nFailed tests:")
            for name, expected, actual, desc in main_details:
                print(f"  - {name}: exit=0x{actual:02X} (expect=0x{expected:02X})")
        return 1

if __name__ == "__main__":
    sys.exit(main())
