#!/usr/bin/env python3
"""Min ROM probe for QEMU-009t: rela.si base address verification.

Architecture: test code runs from ROM (same as 005t/006t/008t probe pattern).
Kernel binary provides test data (loaded at RAM base).

Tests cover:
- rela.si base address is rb[0] (PC), NOT rb[ha] (self-reference)
- Formula: rbha = (PC & ~0xFFF) + sign_extend(imms18 << 12)
- High 16 bits preserved (not 48-bit truncation)
- ha==0 → ILLI (0x88)
- Negative offset (imms18 < 0)

Exit codes (ADR-0004 D5.8):
  0x00 = PASS, 0x88 = ILLI, 0x89 = UNDI, 0x8A = RASOF, 0x8B = RASUF

Usage: python3 tools/qemu/min_rom_probe_009t.py
"""

import struct
import subprocess
import sys
import os
import tempfile

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

def add_so_rb(rbhb, rbhc, rdhd):
    """add.so rbhb, rbhc, rdhd (MISC-octa, ha=0x20)"""
    return encode_orrr(0x40, 0x20, rbhb, rbhc, rdhd)

def sub_so_rb(rbhb, rbhc, rdhd):
    """sub.so rbhb, rbhc, rdhd (MISC-octa, ha=0x28)"""
    return encode_orrr(0x40, 0x28, rbhb, rbhc, rdhd)

def cmp_uo_rd(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd (MISC-octa, ha=0x2A)"""
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def cmp_uo_rb(rdhb, rbhc, rbhd):
    """cmp.uo-rb rdhb, rbhc, rbhd (MISC-octa, ha=0x29)"""
    return encode_orrr(0x40, 0x29, rdhb, rbhc, rbhd)

def xor_o(rdhb, rdhc, rdhd):
    """xor.o rdhb, rdhc, rdhd (MISC-octa, ha=0x0A)"""
    return encode_orrr(0x40, 0x0A, rdhb, rdhc, rdhd)

def and_o(rdhb, rdhc, rdhd):
    """and.o rdhb, rdhc, rdhd (MISC-octa, ha=0x08)"""
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
    """rb2rd rdha, rbhb, immu6 (MISC-octa, ha=0x36)"""
    return encode_orrr(0x40, 0x36, rdha, rbhb, immu6)

def rd2rb(rbha, rdhb, immu6):
    """rd2rb rbha, rdhb, immu6 (MISC-octa, ha=0x37)"""
    return encode_orrr(0x40, 0x37, rbha, rdhb, immu6)

def rb2rb(rbha, rbhb, immu6):
    """rb2rb rbha, rbhb, immu6 (MISC-octa, ha=0x34)"""
    return encode_orrr(0x40, 0x34, rbha, rbhb, immu6)

def rela_si_rb(rbha, imms18):
    """rela.si rbha, imms18 (op=0x5A)"""
    return encode_riii(0x5A, rbha, imms18 & 0x3FFFF)

def br_ne(rdha, rdhb, imms12):
    """br.ne rdha, rdhb, imms12 (op=0x6F)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x6F, rdha, rdhb, hc, hd)

def illi():
    return encode_oiii(0x00, 0x00, 0)

def swym():
    return encode_oiii(0x77, 0x00, 0)

# ── Terminators ───────────────────────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

# ── ROM builder ───────────────────────────────────────────────────────

def build_rom(test_insns):
    """Build ROM: [trampoline | test_insns | UNDI | padding].
    Trampoline sets rb1=SP, rb2=RAM base, rb16=exit port, rb17=RAM base."""
    trampoline = [
        encode_rwii(0x4E, 1, 2, 0xFFFF),  # set.zw rb1, wp2, 0xFFFF → 0x0000_FFFF_0000_0000
        encode_rwii(0x4A, 1, 1, 0x00FF),  # or.w rb1, wp1, 0x00FF → 0x0000_FFFF_00FF_0000 (SP)
        encode_rwii(0x4E, 2, 2, 0xFFFF),  # set.zw rb2, wp2, 0xFFFF → 0x0000_FFFF_0000_0000
        encode_rwii(0x4E, 16, 2, 0xFFFF), # set.zw rb16, wp2, 0xFFFF → 0x0000_FFFF_0000_0000
        encode_rwii(0x4A, 16, 1, 0x8000), # or.w rb16, wp1, 0x8000 → exit port
        encode_rwii(0x4E, 17, 2, 0xFFFF), # set.zw rb17, wp2, 0xFFFF → RAM base
    ]
    rom = b''
    for insn in trampoline:
        rom += insn
    for insn in test_insns:
        rom += insn
    rom += UNDI_TERMINATOR
    while len(rom) < 64:
        rom += illi()
    return rom

def run_test(rom_data, kernel_data=None, timeout=10):
    if kernel_data is None:
        kernel_data = illi() * 4
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(rom_data); rom_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(kernel_data); kernel_path = f.name
    try:
        result = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic',
             '-bios', rom_path, '-kernel', kernel_path],
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
    encode_rwii(0x4E, 18, 2, 0xFFFF),  # set.zw rb18, wp2, 0xFFFF
    encode_rwii(0x4A, 18, 0, 0x0100),  # or.w rb18, wp0, 0x0100 → RAM+0x100
]

# ── Exact-value rela checker (rework: assert the value, not just "no crash") ──
# 期望值由 Python 按 contract-isa §4.7 独立算出（不从实现反推）：
#   result = (dest_high16 << 48) | (((PC & ~0xFFF) + sext(imms18 << 12)) & 0xFFFFFFFFFFFF)
# PC = ROM_BASE + (TRAMPOLINE_LEN + rela_idx) * 4（rela 在本测试内的下标）

ROM_BASE = 0xFFFFFFFF0000
TRAMPOLINE_LEN = 6          # see build_rom()
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

def rela_exact_test(dest_rb, imm_signed, dest_high16, dest_low48=None):
    """set dest -> rela.si dest, imm -> compare dest against the §4.7 expectation."""
    seq = [encode_rwii(0x4E, dest_rb, 3, dest_high16 & 0xFFFF)]   # set.zw dest, wp3, high16
    if dest_low48 is not None:
        seq += [
            encode_rwii(0x4A, dest_rb, 2, (dest_low48 >> 32) & 0xFFFF),
            encode_rwii(0x4A, dest_rb, 1, (dest_low48 >> 16) & 0xFFFF),
            encode_rwii(0x4A, dest_rb, 0, dest_low48 & 0xFFFF),
        ]
    rela_idx = len(seq)
    pc = ROM_BASE + (TRAMPOLINE_LEN + rela_idx) * 4
    low48 = ((pc & ~0xFFF) + (imm_signed << 12)) & 0xFFFFFFFFFFFF
    expected = ((dest_high16 & 0xFFFF) << 48) | low48
    seq.append(rela_si_rb(dest_rb, imm_signed & 0x3FFFF))
    seq += load_rb64(EXACT_EXP_RB, expected)
    seq += [
        cmp_uo_rb(EXACT_RD_CMP, dest_rb, EXACT_EXP_RB),   # 0 if equal
        set_zw_rd(EXACT_RD_ZERO, 0x0000),
        br_ne(EXACT_RD_CMP, EXACT_RD_ZERO, 3),            # != 0 (not equal) -> branch to FAIL
        set_zw_rd(18, 0x0000), st_o_rd(18, 16, 0),        # equal: PASS (fall-through)
        set_zw_rd(18, 0x0001), st_o_rd(18, 16, 0),        # not-equal: FAIL (branch target)
    ]
    return seq

# ── Test cases ────────────────────────────────────────────────────────

TESTS = [
    # ── rela.si base address verification ─────────────────────────────

    # T1: rela.si rb1, imms18=0 → rb1 = (PC & ~0xFFF) + 0
    # PC is around ROM_BASE (0xFFFFFFFF0000), so (PC & ~0xFFF) = 0xFFFFFFFF0000
    # If base were rb[ha] (self-reference), rb1=0 → result=0 (wrong)
    # If base is rb[0] (PC), result = 0xFFFFFFFF0000 (correct)
    # We can't easily verify the exact address, but we can verify it doesn't crash
    # and the result is non-zero (proving it's not self-reference from rb1=0)
    ("T1 rela.si rb1 imms18=0 (exact value)",
     rela_exact_test(1, 0, 0xABCD),
     PASS_EXIT,
     "rela.si rb1 value wrong (base/offset/high16)"),

    # T2: rela.si rb2, imms18=1 → rb2 = (PC & ~0xFFF) + (1 << 12)
    # = 0xFFFFFFFF0000 + 0x1000 = 0xFFFFFFFF1000
    # If base were rb[ha] (self-reference), rb2=0x0000FFFF00000000 → result different
    ("T2 rela.si rb2 imms18=1 (exact value, +1 page)",
     rela_exact_test(2, 1, 0xABCD),
     PASS_EXIT,
     "rela.si rb2 value wrong (offset <<12 not applied?)"),

    # T3: rela.si rb3, imms18=-1 → rb3 = (PC & ~0xFFF) + (-1 << 12)
    # = 0xFFFFFFFF0000 - 0x1000 = 0xFFFFFFFEF000
    # Negative offset: imms18=0x3FFFF (18-bit -1)
    ("T3 rela.si rb3 imms18=-1 (exact value, -1 page)",
     rela_exact_test(3, -1, 0xABCD),
     PASS_EXIT,
     "rela.si rb3 value wrong (negative offset sign?)"),

    # T4: rela.si rb0 → ILLI (ha==0 is illegal)
    ("T4 rela.si rb0 → ILLI",
     [rela_si_rb(0, 0)],
     ILLI_EXIT,
     "rela.si rb0 not ILLI"),

    # T5: Verify base is PC, not self-reference
    # Strategy: Set rb5 to a known value (e.g., 0x123456789ABCDEF0),
    # then rela.si rb5, imms18=0
    # If base were rb[ha], result = rb5 + 0 = rb5 (unchanged)
    # If base is PC, result = (PC & ~0xFFF) + 0 = PC-aligned
    # We can verify by storing rb5 to memory and checking it's NOT the original value
    # (since PC is around 0xFFFFFFFF0000, not 0x123456789ABCDEF0)
    ("T5 rela.si base=PC not self-ref (exact, dest preloaded low48)",
     rela_exact_test(5, 0, 0x1234, 0x56789ABC),
     PASS_EXIT,
     "rela.si rb5 value wrong (base is self-reference rb[ha]?)"),

    # T6: Verify formula with specific offset
    # rela.si rb6, imms18=2 → rb6 = (PC & ~0xFFF) + (2 << 12) = PC_aligned + 0x2000
    # We can't verify exact value without knowing PC, but we can verify
    # the result is different from what self-reference would give
    ("T6 rela.si rb6 imms18=2 (exact value, offset applied)",
     rela_exact_test(6, 2, 0xAAAA),
     PASS_EXIT,
     "rela.si rb6 value wrong (offset formula)"),

    # T7: Verify high 16 bits preserved
    # Set rb7 to have non-zero high 16 bits, then rela.si rb7, 0
    # Result should have same high 16 bits as original rb7
    # We can verify by storing rb7 and checking high bits
    ("T7 rela.si preserves high 16 bits (exact, high16=0xFFFF)",
     rela_exact_test(7, 0, 0xFFFF, 0x12345678),
     PASS_EXIT,
     "rela.si rb7 high 16 bits not preserved (48-bit truncation?)"),

    # T8: Verify rela.si result is usable (store to RAM via rb8)
    # After rela.si, rb8 points to ROM_BASE. We can't write to ROM,
    # but we can verify the instruction doesn't crash.
    ("T8 rela.si rb8 imms18=0 (exact value, dest preloaded)",
     rela_exact_test(8, 0, 0x1111, 0x222233334444),
     PASS_EXIT,
     "rela.si rb8 value wrong"),

    # T9: Verify negative offset doesn't wrap incorrectly
    # rela.si rb9, imms18=0x3FFFE (18-bit -2)
    # = (PC & ~0xFFF) + (-2 << 12) = PC_aligned - 0x2000
    ("T9 rela.si negative offset -2 (exact value)",
     rela_exact_test(9, -2, 0xABCD),
     PASS_EXIT,
     "rela.si rb9 value wrong (negative offset)"),

    # T10: Verify large positive offset
    # rela.si rb10, imms18=0x1FFFF (18-bit max positive = 262143)
    # = (PC & ~0xFFF) + (262143 << 12) = PC_aligned + 0x7FFFF000
    ("T10 rela.si large positive offset (exact value, imms18=0x1FFFF)",
     rela_exact_test(10, 0x1FFFF, 0xABCD),
     PASS_EXIT,
     "rela.si rb10 value wrong (large offset / sign extension)"),

    # T11: Verify base is PC, NOT self-reference (strong check)
    # Set rb11 to a known value (0x123456789ABCDEF0),
    # then rela.si rb11, 0
    # If base were self-reference: result = rb11 + 0 = 0x123456789ABCDEF0
    # If base is PC: result = (PC & ~0xFFF) + 0 = 0xFFFFFFFF0000
    # We can verify by comparing rb11 with expected PC-aligned value
    ("T11 rela.si base=PC not self-ref (strong check)",
     [set_zw_rb(11, 0x1234),     # rb11 = 0x0000123400000000
      or_w_rb(11, 1, 0x5678),    # rb11 = 0x0000123456780000
      or_w_rb(11, 0, 0x9ABC),    # rb11 = 0x0000123456789ABC
      rela_si_rb(11, 0),         # rb11 = (PC & ~0xFFF) + 0
      # Now rb11 should be 0xFFFFFFFF0000 (PC-aligned), NOT 0x123456789ABC
      # Verify by storing to RAM and loading to rd
      st_o_rb(11, 17, 0),        # store rb11 to RAM base
      ld_o_rd(12, 17, 0),        # load to rd12
      # rd12 should be 0xFFFFFFFF0000, not 0x123456789ABC
      # We can't easily compare, but we can verify it's not the original value
      # by checking if rd12 != 0x123456789ABC
      set_zw_rd(13, 0x1234),     # rd13 = 0x1234
      or_w_rd(13, 1, 0x5678),    # rd13 = 0x12345678
      or_w_rd(13, 0, 0x9ABC),    # rd13 = 0x123456789ABC
      cmp_uo_rd(14, 12, 13),     # rd14 = cmp(rd12, rd13)
      set_zw_rd(15, 0x0000),     # expected: not equal (0)
      br_ne(14, 15, 3),          # if not equal, skip 3 → PASS
      set_zw_rd(18, 0x0001),     # equal: FAIL (self-reference detected!)
      st_o_rd(18, 16, 0),
      set_zw_rd(18, 0x0000),     # not-equal: PASS
      st_o_rd(18, 16, 0)],
     PASS_EXIT,
     "rela.si base is self-reference (should be PC)"),

    # T12: Verify high 16 bits preserved (strong check)
    # Set rb12 high 16 bits to 0x1234, then rela.si rb12, 0
    # If high 16 bits preserved: result high 16 = 0x1234
    # If high 16 bits truncated: result high 16 = 0x0000
    # We can verify by comparing result with result AND 0x0000FFFFFFFFFFFF
    ("T12 rela.si preserves high 16 bits (strong check)",
     [set_zw_rb(12, 0x1234),     # rb12 = 0x0000000000001234 (wp0 = 0x1234)
      or_w_rb(12, 3, 0x1234),    # rb12[63:48] |= 0x1234 → rb12 = 0x1234000000001234
      rela_si_rb(12, 0),         # rb12 = (PC & ~0xFFF) + 0, high 16 should be preserved
      # Now rb12 should have high 16 = 0x1234 (preserved from original)
      # Use rb2rd to copy rb12 to rd13 for verification
      rb2rd(13, 12, 1),          # rd13 = rb12
      # rd13 should have high 16 = 0x1234
      # Verify by comparing rd13 with rd13 AND 0x0000FFFFFFFFFFFF
      # Build mask 0x0000FFFFFFFFFFFF in rd14
      set_ow_rd(14, 3, 0x0000),  # rd14 = 0x0000FFFFFFFFFFFFFFFF (all ones except wp3=0)
      # set.ow sets one wyde to the value, rest to all ones
      # With wp3=0x0000, rd14 = 0x0000FFFFFFFFFFFFFFFF... wait that's 48 bits of ones plus wp3=0
      # Actually: set.ow rd14, wp3, 0x0000 → rd14[63:48]=0x0000, rd14[47:0]=all ones
      # = 0x0000FFFFFFFFFFFF ← exactly what we want!
      and_o(15, 13, 14),         # rd15 = rd13 & 0x0000FFFFFFFFFFFF
      cmp_uo_rd(16, 13, 15),     # rd16 = cmp(rd13, rd15)
      set_zw_rd(17, 0x0000),     # expected: not equal → cmp result ≠ 0
      br_ne(16, 17, 3),          # if rd16≠0 (not equal), skip 3 → PASS
      set_zw_rd(18, 0x0001),     # rd16==0 (equal): FAIL (high bits truncated!)
      st_o_rd(18, 16, 0),
      set_zw_rd(18, 0x0000),     # rd16≠0 (not-equal): PASS
      st_o_rd(18, 16, 0)],
     PASS_EXIT,
     "rela.si high 16 bits truncated (should be preserved)"),
]

# ── CTL self-check ────────────────────────────────────────────────────

CTL_CHECKS = [
    ("CTL: st.o PASS but expect ILLI (wrong)",
     [set_zw_rd(18, 0x0000), st_o_rd(18, 16, 0)],
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect wrong values"),
    ("CTL: ILLI but expect PASS (wrong)",
     [illi()],
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
