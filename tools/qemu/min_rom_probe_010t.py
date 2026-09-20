#!/usr/bin/env python3
"""Min ROM probe for QEMU-010t ldm.o-rb and stm.o-rb (RB multi-register load/store).

Covers 12 vectors from tests/vectors/isa/mem-rb.yaml for ldm.o-rb + stm.o-rb:

ldm.o-rb (6 vectors):
  1. encoding: ldm.o-rb rb1,rb3,rd2,1 with rb3=RAM base → no crash
  2. legality ILLI: rb0 as dest → 0x88
  3. legality MALIGN: EA unaligned (rd2=7) → 0x8C
  4. legality UNMAPPED: rb3=0 → EA=0 → 0x87
  5. semantic: rb1 <- mem[RAM+0x100] = 0x42 → rb1=0x42
  6. boundary: rb1 <- mem[RAM+0] = 0xDEADBEEF → rb1=0xDEADBEEF

stm.o-rb (6 vectors):
  7. encoding: stm.o-rb rb1,rb3,rd2,1 with rb3=RAM base → no crash
  8. legality ILLI: rb0 as src → 0x88
  9. legality MALIGN: EA unaligned (rd2=7) → 0x8C
  10. legality UNMAPPED: rb3=0 → EA=0 → 0x87
  11. semantic: mem[RAM+0x100] = rb1 (0x42), readback via ldm.o-rb + cmp.uo-rb
  12. boundary: mem[RAM+0] = rb1 (0xDEADBEEF), readback via ldm.o-rb + cmp.uo-rb

Additional tests:
  13-24. Extended tests for ldm.o-rb + stm.o-rb (ILLI multi, MALIGN 4B, semantic multi)
  25-26. EA 48-bit truncation verification (ldm.o-rb + stm.o-rb)

Exit codes (ADR-0004 D5.8):
  0x00 = PASS, 0x87 = UNMAPPED, 0x88 = ILLI, 0x8C = MALIGN

Usage: python3 tools/qemu/min_rom_probe_010t.py
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

def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_riii(op, ha, imms18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (imms18 & 0x3FFFF))

def encode_oiii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)

def set_zw_rb(rb, wpN, immu16):
    """set.zw rbha, wpN, immu16 (op=0x4E, rwii)"""
    return encode_rwii(0x4E, rb, wpN, immu16)

def or_w_rb(rb, wpN, immu16):
    return encode_rwii(0x4A, rb, wpN, immu16)

def or_w_rd(rd, wpN, immu16):
    """or.w rdha, wpN, immu16 (op=0x48, rwii)"""
    return encode_rwii(0x48, rd, wpN, immu16)

def st_o(rdha, rbhb, imms12):
    """st.o rdha, rbhb, imms12 (op=0x21)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)

def ldm_o_rb(rbha, rbhb, rdhc, immu6):
    """ldm.o-rb rbha, rbhb, rdhc, immu6 (op=0x3A, rrri)"""
    return encode_rrii(0x3A, rbha, rbhb, rdhc, immu6)

def stm_o_rb(rbha, rbhb, rdhc, immu6):
    """stm.o-rb rbha, rbhb, rdhc, immu6 (op=0x3B, rrri)"""
    return encode_rrii(0x3B, rbha, rbhb, rdhc, immu6)

def ld_o_rd(rdha, rbhb, imms12):
    """ld.o rdha, rbhb, imms12 (op=0x20, rrii)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x20, rdha, rbhb, hc, hd)

def cmp_uo(rdhb, rbhc, rbhd):
    """cmp.uo rdhb, rbhc, rbhd (MISC-octa, op=0x40, ha=0x2A, orrr)
    NOTE: This compares RD operands. For RB operands, use cmp_uo_rb."""
    return encode_rrii(0x40, 0x2A, rdhb, rbhc, rbhd)

def cmp_uo_rb(rdhb, rbhc, rbhd):
    """cmp.uo-rb rdhb, rbhc, rbhd (MISC-octa, op=0x40, ha=0x29, orrr)
    Compares RB operands and returns result in RD."""
    return encode_rrii(0x40, 0x29, rdhb, rbhc, rbhd)

def br_nz(rdha, imms18):
    """br.nz rdha, imms18 (op=0x6B)"""
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)

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
        set_zw_rb(1, 2, 0xFFFF),   # set.zw rb1, wp2, 0xFFFF → 0x0000_FFFF_0000_0000
        or_w_rb(1, 1, 0x00FF),     # or.w rb1, wp1, 0x00FF → 0x0000_FFFF_00FF_0000 (SP)
        set_zw_rb(2, 2, 0xFFFF),   # set.zw rb2, wp2, 0xFFFF → 0x0000_FFFF_0000_0000
        set_zw_rb(16, 2, 0xFFFF),  # set.zw rb16, wp2, 0xFFFF → 0x0000_FFFF_0000_0000
        or_w_rb(16, 1, 0x8000),    # or.w rb16, wp1, 0x8000 → exit port
        set_zw_rb(17, 2, 0xFFFF),  # set.zw rb17, wp2, 0xFFFF → RAM base
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
UNMAPPED_EXIT = 135 # 0x87
MALIGN_EXIT = 140  # 0x8C

# ── Test cases ────────────────────────────────────────────────────────
# After trampoline: rb16=exit port, rb17=RAM base, rb2=RAM base
# ldm.o-rb rbha, rbhb, rdhc, immu6: loads immu6 RB regs from EA=rbhb+rdhc

TESTS = [
    # T1: encoding — ldm.o-rb rb1, rb3, rd2, 1 with rb3=RAM, rd2=0 → no crash → PASS
    # Covers: mem-rb.yaml encoding vector 0x3A043081
    ("T1 encoding: ldm.o-rb rb1,rb3,rd2,1 no crash",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = 0x0000_FFFF_0000_0000 (RAM base)
      set_zw_rd(2, 0),            # rd2 = 0 (offset)
      ldm_o_rb(1, 3, 2, 1),      # ldm.o-rb rb1, rb3, rd2, 1
      set_zw_rd(18, 0),           # rd18 = 0 (PASS)
      st_o(18, 16, 0)],           # exit 0x00
     PASS_EXIT,
     "ldm.o-rb encoding crashed"),

    # T2: ILLI — rbha=rb0 → 0x88
    # Covers: mem-rb.yaml legality ILLI vector 0x3A003081
    ("T2 ILLI: ldm.o-rb rb0 dest",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 0),            # rd2 = 0
      ldm_o_rb(0, 3, 2, 1)],     # ldm.o-rb rb0, rb3, rd2, 1 → ILLI
     ILLI_EXIT,
     "ldm.o-rb rb0 dest not ILLI"),

    # T3: ILLI — immu6=0 → 0x88
    ("T3 ILLI: ldm.o-rb immu6=0",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 0),            # rd2 = 0
      ldm_o_rb(1, 3, 2, 0)],     # ldm.o-rb rb1, rb3, rd2, 0 → ILLI
     ILLI_EXIT,
     "ldm.o-rb immu6=0 not ILLI"),

    # T4: ILLI — rbha+immu6>64 → 0x88
    ("T4 ILLI: ldm.o-rb rb60+8>64",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 0),            # rd2 = 0
      ldm_o_rb(60, 3, 2, 8)],    # ldm.o-rb rb60, rb3, rd2, 8 → ILLI (60+8=68>64)
     ILLI_EXIT,
     "ldm.o-rb rb60+8 not ILLI"),

    # T5: MALIGN — EA=RAM+7, unaligned (needs 8B align) → 0x8C
    # Covers: mem-rb.yaml legality MALIGN vector (rd2=7)
    ("T5 MALIGN: ldm.o-rb EA=RAM+7",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = 0x0000_FFFF_0000_0000
      set_zw_rd(2, 7),            # rd2 = 7 (offset)
      ldm_o_rb(1, 3, 2, 1)],     # EA = 0x0000_FFFF_0000_0007 → MALIGN
     MALIGN_EXIT,
     "ldm.o-rb unaligned not MALIGN"),

    # T6: UNMAPPED — rb3=0, rd2=0, EA=0 → unmapped → 0x87
    # Covers: mem-rb.yaml legality UNMAPPED vector
    ("T6 UNMAPPED: ldm.o-rb EA=0",
     [set_zw_rd(2, 0),            # rd2 = 0
      ldm_o_rb(1, 3, 2, 1)],     # rb3=0 (reset), EA=0 → unmapped
     UNMAPPED_EXIT,
     "ldm.o-rb EA=0 not UNMAPPED"),

    # T7: semantic — rb1 <- mem[RAM+0x100] = 0x42 → rb1=0x42
    # Covers: mem-rb.yaml semantic vector (rb1=0x42)
    ("T7 semantic: ldm.o-rb rb1=0x42",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      # Store 0x42 to RAM+0x100
      set_zw_rd(18, 0x0042),      # rd18 = 0x42
      st_o(18, 17, 0x100),        # st.o rd18, rb17, 0x100 → RAM+0x100 = 0x42
      # Execute ldm.o-rb
      set_zw_rd(2, 0x100),        # rd2 = 0x100 (offset)
      ldm_o_rb(1, 3, 2, 1),      # ldm.o-rb rb1, rb3, rd2, 1 → rb1 = mem[RAM+0x100]
      # Compare rb1 with expected 0x42
      set_zw_rb(19, 0, 0x0042),   # rb19 = 0x42 (expected)
      cmp_uo_rb(18, 1, 19),      # cmp.uo-rb rd18, rb1, rb19 → rd18=0 if equal
      br_nz(18, 2),               # br.nz rd18, +2 → if not equal, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),            # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],           # exit 0x01
     PASS_EXIT,
     "ldm.o-rb semantic: rb1 != 0x42"),

    # T8: boundary — rb1 <- mem[RAM+0] = 0xDEADBEEF → rb1=0xDEADBEEF
    # Covers: mem-rb.yaml boundary vector
    ("T8 boundary: ldm.o-rb rb1=0xDEADBEEF",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      # Store 0xDEADBEEF to RAM+0
      set_zw_rd(18, 0xBEEF),      # rd18 = 0xBEEF
      or_w_rd(18, 1, 0xDEAD),     # rd18 = 0xDEADBEEF
      st_o(18, 17, 0),            # st.o rd18, rb17, 0 → RAM+0 = 0xDEADBEEF
      # Execute ldm.o-rb
      set_zw_rd(2, 0),            # rd2 = 0 (offset)
      ldm_o_rb(1, 3, 2, 1),      # ldm.o-rb rb1, rb3, rd2, 1 → rb1 = mem[RAM+0]
      # Compare rb1 with expected 0xDEADBEEF
      set_zw_rb(19, 0, 0xBEEF),   # rb19 = 0xBEEF
      or_w_rb(19, 1, 0xDEAD),     # rb19 = 0xDEADBEEF
      cmp_uo_rb(18, 1, 19),      # cmp.uo-rb rd18, rb1, rb19 → rd18=0 if equal
      br_nz(18, 2),               # br.nz rd18, +2 → if not equal, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),            # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],           # exit 0x01
     PASS_EXIT,
     "ldm.o-rb boundary: rb1 != 0xDEADBEEF"),

    # T9: ILLI — rbha=rb0 + immu6>1 (rb0 dest always ILLI regardless of count)
    ("T9 ILLI: ldm.o-rb rb0 multi",
     [set_zw_rb(3, 2, 0xFFFF),
      set_zw_rd(2, 0),
      ldm_o_rb(0, 3, 2, 4)],     # ldm.o-rb rb0, rb3, rd2, 4 → ILLI
     ILLI_EXIT,
     "ldm.o-rb rb0 multi not ILLI"),

    # T10: MALIGN — EA=RAM+4 (4-byte aligned but not 8-byte) → 0x8C
    ("T10 MALIGN: ldm.o-rb EA=RAM+4",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 4),            # rd2 = 4 (offset)
      ldm_o_rb(1, 3, 2, 1)],     # EA = RAM+4 → MALIGN (needs 8B)
     MALIGN_EXIT,
     "ldm.o-rb 4-byte offset not MALIGN"),

    # T11: semantic multi — load 2 regs into rb10,rb11, check rb10=0xAA
    ("T11 semantic: ldm.o-rb 2 regs",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      # Store 0xAA to RAM+0x200 and 0xBB to RAM+0x208
      set_zw_rd(18, 0x00AA),
      st_o(18, 17, 0x200),        # RAM+0x200 = 0xAA
      set_zw_rd(18, 0x00BB),
      st_o(18, 17, 0x208),        # RAM+0x208 = 0xBB
      # Execute ldm.o-rb rb10, rb3, rd2, 2
      set_zw_rd(2, 0x200),        # rd2 = 0x200
      ldm_o_rb(10, 3, 2, 2),     # rb10 = mem[RAM+0x200], rb11 = mem[RAM+0x208]
      # Check rb10 = 0xAA
      set_zw_rb(19, 0, 0x00AA),   # rb19 = 0xAA
      cmp_uo_rb(18, 10, 19),     # cmp.uo-rb rd18, rb10, rb19
      br_nz(18, 2),               # if rb10 != 0xAA, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),            # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],           # exit 0x01
     PASS_EXIT,
     "ldm.o-rb 2 regs: rb10 != 0xAA"),

    # T12: encoding — ldm.o-rb with immu6=3 (multiple regs)
    ("T12 encoding: ldm.o-rb immu6=3",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 0x300),        # rd2 = 0x300 (offset in RAM)
      ldm_o_rb(5, 3, 2, 3),      # ldm.o-rb rb5, rb3, rd2, 3 → loads rb5,rb6,rb7
      set_zw_rd(18, 0),
      st_o(18, 16, 0)],           # exit 0x00
     PASS_EXIT,
     "ldm.o-rb immu6=3 crashed"),

    # ── stm.o-rb tests ─────────────────────────────────────────────────
    # T13: encoding — stm.o-rb rb1, rb3, rd2, 1 with rb3=RAM, rd2=0 → no crash
    ("T13 encoding: stm.o-rb rb1,rb3,rd2,1 no crash",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rb(1, 0, 0x0042),   # rb1 = 0x42 (source value)
      set_zw_rd(2, 0x100),       # rd2 = 0x100 (offset in RAM)
      stm_o_rb(1, 3, 2, 1),     # stm.o-rb rb1, rb3, rd2, 1 → store rb1 to RAM+0x100
      set_zw_rd(18, 0),
      st_o(18, 16, 0)],          # exit 0x00
     PASS_EXIT,
     "stm.o-rb encoding crashed"),

    # T14: ILLI — rbha=rb0 → 0x88
    ("T14 ILLI: stm.o-rb rb0 src",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 0),           # rd2 = 0
      stm_o_rb(0, 3, 2, 1)],    # stm.o-rb rb0, rb3, rd2, 1 → ILLI
     ILLI_EXIT,
     "stm.o-rb rb0 src not ILLI"),

    # T15: ILLI — immu6=0 → 0x88
    ("T15 ILLI: stm.o-rb immu6=0",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 0),           # rd2 = 0
      stm_o_rb(1, 3, 2, 0)],    # stm.o-rb rb1, rb3, rd2, 0 → ILLI
     ILLI_EXIT,
     "stm.o-rb immu6=0 not ILLI"),

    # T16: ILLI — rbha+immu6>64 → 0x88
    ("T16 ILLI: stm.o-rb rb60+8>64",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rd(2, 0),           # rd2 = 0
      stm_o_rb(60, 3, 2, 8)],   # stm.o-rb rb60, rb3, rd2, 8 → ILLI (60+8=68>64)
     ILLI_EXIT,
     "stm.o-rb rb60+8 not ILLI"),

    # T17: MALIGN — EA=RAM+7, unaligned (needs 8B align) → 0x8C
    ("T17 MALIGN: stm.o-rb EA=RAM+7",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rb(1, 0, 0x0042),   # rb1 = 0x42
      set_zw_rd(2, 7),           # rd2 = 7 (offset)
      stm_o_rb(1, 3, 2, 1)],    # EA = RAM+7 → MALIGN
     MALIGN_EXIT,
     "stm.o-rb unaligned not MALIGN"),

    # T18: UNMAPPED — rb3=0, rd2=0, EA=0 → unmapped → 0x87
    ("T18 UNMAPPED: stm.o-rb EA=0",
     [set_zw_rb(1, 0, 0x0042),   # rb1 = 0x42
      set_zw_rd(2, 0),           # rd2 = 0
      stm_o_rb(1, 3, 2, 1)],    # rb3=0 (reset), EA=0 → unmapped
     UNMAPPED_EXIT,
     "stm.o-rb EA=0 not UNMAPPED"),

    # T19: semantic — stm.o-rb stores rb1=0x42 to RAM+0x100, readback via ldm.o-rb + cmp.uo-rb
    ("T19 semantic: stm.o-rb rb1=0x42",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rb(1, 0, 0x0042),   # rb1 = 0x42 (value to store)
      set_zw_rd(2, 0x100),       # rd2 = 0x100 (offset)
      # Store: stm.o-rb rb1, rb3, rd2, 1 → mem[RAM+0x100] = rb1 (0x42)
      stm_o_rb(1, 3, 2, 1),
      # Readback: ldm.o-rb rb20, rb3, rd2, 1 → rb20 = mem[RAM+0x100]
      ldm_o_rb(20, 3, 2, 1),
      # Compare: rb1 vs rb20
      cmp_uo_rb(18, 1, 20),     # cmp.uo-rb rd18, rb1, rb20 → rd18=0 if equal
      br_nz(18, 2),              # if not equal, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),           # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],          # exit 0x01
     PASS_EXIT,
     "stm.o-rb semantic: rb1 != rb20 after round-trip"),

    # T20: boundary — stm.o-rb stores rb1=0xDEADBEEF to RAM+0, readback via ldm.o-rb + cmp.uo-rb
    ("T20 boundary: stm.o-rb rb1=0xDEADBEEF",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rb(1, 0, 0xBEEF),   # rb1 = 0xBEEF
      or_w_rb(1, 1, 0xDEAD),     # rb1 = 0xDEADBEEF (value to store)
      set_zw_rd(2, 0),           # rd2 = 0 (offset)
      # Store: stm.o-rb rb1, rb3, rd2, 1 → mem[RAM+0] = rb1 (0xDEADBEEF)
      stm_o_rb(1, 3, 2, 1),
      # Readback: ldm.o-rb rb20, rb3, rd2, 1 → rb20 = mem[RAM+0]
      ldm_o_rb(20, 3, 2, 1),
      # Compare: rb1 vs rb20
      cmp_uo_rb(18, 1, 20),     # cmp.uo-rb rd18, rb1, rb20 → rd18=0 if equal
      br_nz(18, 2),              # if not equal, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),           # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],          # exit 0x01
     PASS_EXIT,
     "stm.o-rb boundary: rb1 != rb20 after round-trip"),

    # T21: ILLI — rbha=rb0 + immu6>1 (rb0 src always ILLI regardless of count)
    ("T21 ILLI: stm.o-rb rb0 multi",
     [set_zw_rb(3, 2, 0xFFFF),
      set_zw_rd(2, 0),
      stm_o_rb(0, 3, 2, 4)],    # stm.o-rb rb0, rb3, rd2, 4 → ILLI
     ILLI_EXIT,
     "stm.o-rb rb0 multi not ILLI"),

    # T22: MALIGN — EA=RAM+4 (4-byte aligned but not 8-byte) → 0x8C
    ("T22 MALIGN: stm.o-rb EA=RAM+4",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rb(1, 0, 0x0042),   # rb1 = 0x42
      set_zw_rd(2, 4),           # rd2 = 4 (offset)
      stm_o_rb(1, 3, 2, 1)],    # EA = RAM+4 → MALIGN (needs 8B)
     MALIGN_EXIT,
     "stm.o-rb 4-byte offset not MALIGN"),

    # T23: semantic multi — store 2 regs rb10=0xAA,rb11=0xBB, readback + check
    ("T23 semantic: stm.o-rb 2 regs",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      # Pre-clear RAM so stale data can't pass
      set_zw_rd(18, 0),
      st_o(18, 17, 0x200),       # RAM+0x200 = 0 (clear)
      st_o(18, 17, 0x208),       # RAM+0x208 = 0 (clear)
      # Set source regs
      set_zw_rb(10, 0, 0x00AA),  # rb10 = 0xAA
      set_zw_rb(11, 0, 0x00BB),  # rb11 = 0xBB
      set_zw_rd(2, 0x200),       # rd2 = 0x200
      # Store: stm.o-rb rb10, rb3, rd2, 2 → mem[0x200]=rb10, mem[0x208]=rb11
      stm_o_rb(10, 3, 2, 2),
      # Readback: ldm.o-rb rb20, rb3, rd2, 2 → rb20=mem[0x200], rb21=mem[0x208]
      ldm_o_rb(20, 3, 2, 2),
      # Check rb10 vs rb20 (0xAA)
      cmp_uo_rb(18, 10, 20),    # cmp.uo-rb rd18, rb10, rb20
      br_nz(18, 6),              # if rb10 != rb20, skip to FAIL (6 insns ahead)
      # Check rb11 vs rb21 (0xBB)
      cmp_uo_rb(18, 11, 21),    # cmp.uo-rb rd18, rb11, rb21
      br_nz(18, 4),              # if rb11 != rb21, skip to FAIL (4 insns ahead)
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),           # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],          # exit 0x01
     PASS_EXIT,
     "stm.o-rb 2 regs: round-trip mismatch"),

    # T24: encoding — stm.o-rb with immu6=3 (multiple regs, no crash)
    ("T24 encoding: stm.o-rb immu6=3",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = RAM base
      set_zw_rb(5, 0, 0x1111),   # rb5 = 0x1111
      set_zw_rb(6, 0, 0x2222),   # rb6 = 0x2222
      set_zw_rb(7, 0, 0x3333),   # rb7 = 0x3333
      set_zw_rd(2, 0x300),       # rd2 = 0x300 (offset in RAM)
      stm_o_rb(5, 3, 2, 3),     # stm.o-rb rb5, rb3, rd2, 3 → stores rb5,rb6,rb7
      set_zw_rd(18, 0),
      st_o(18, 16, 0)],          # exit 0x00
     PASS_EXIT,
     "stm.o-rb immu6=3 crashed"),

    # T25: EA truncation — ldm.o-rb with rb[hb] high 16 bits non-zero
    # rb3 = 0x0001_FFFF_0000_0000, rd2 = 0x100
    # EA after truncation = 0x0000_FFFF_0000_0100 (RAM+0x100, mapped)
    # EA without truncation = 0x0001_FFFF_0000_0100 (unmapped → 0x87)
    ("T25 EA truncation: ldm.o-rb high bits",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = 0x0000_FFFF_0000_0000 (RAM base)
      or_w_rb(3, 3, 0x0001),     # rb3 = 0x0001_FFFF_0000_0000 (high bits non-zero)
      set_zw_rd(2, 0x100),       # rd2 = 0x100
      # Store 0x42 to RAM+0x100 (using rb17 which is RAM base)
      set_zw_rd(18, 0x0042),
      st_o(18, 17, 0x100),       # RAM+0x100 = 0x42
      # Execute ldm.o-rb with rb3 having high bits
      ldm_o_rb(1, 3, 2, 1),     # EA = (rb3 + rd2) & 0x0000FFFFFFFFFFFF = RAM+0x100
      # Check rb1 = 0x42 (should be loaded from RAM+0x100)
      set_zw_rb(19, 0, 0x0042),
      cmp_uo_rb(18, 1, 19),     # cmp.uo-rb rd18, rb1, rb19
      br_nz(18, 2),              # if not equal, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),           # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],          # exit 0x01
     PASS_EXIT,
     "ldm.o-rb EA truncation: rb1 != 0x42 (truncation failed?)"),

    # T26: EA truncation — stm.o-rb with rb[hb] high 16 bits non-zero
    # rb3 = 0x0001_FFFF_0000_0000, rd2 = 0x100
    # EA after truncation = 0x0000_FFFF_0000_0100 (RAM+0x100, mapped)
    # EA without truncation = 0x0001_FFFF_0000_0100 (unmapped → 0x87)
    ("T26 EA truncation: stm.o-rb high bits",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = 0x0000_FFFF_0000_0000 (RAM base)
      or_w_rb(3, 3, 0x0001),     # rb3 = 0x0001_FFFF_0000_0000 (high bits non-zero)
      set_zw_rd(2, 0x100),       # rd2 = 0x100
      # Store 0x42 to RAM+0x100 using stm.o-rb with rb3 having high bits
      set_zw_rb(1, 0, 0x0042),   # rb1 = 0x42
      stm_o_rb(1, 3, 2, 1),     # EA = (rb3 + rd2) & 0x0000FFFFFFFFFFFF = RAM+0x100
      # Readback via ldm.o-rb using rb17 (RAM base)
      ldm_o_rb(20, 17, 2, 1),   # rb20 = mem[RAM+0x100]
      # Check rb20 = 0x42 (should be stored to RAM+0x100)
      set_zw_rb(19, 0, 0x0042),
      cmp_uo_rb(18, 20, 19),    # cmp.uo-rb rd18, rb20, rb19
      br_nz(18, 2),              # if not equal, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),           # exit 0x00
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],          # exit 0x01
     PASS_EXIT,
     "stm.o-rb EA truncation: rb20 != 0x42 (truncation failed?)"),

    # T27: 48-bit top boundary — ldm.o-rb 2 regs with rb[hb] bit48 set
    # rb3 = 0x0001_FFFF_0000_0000 (bit 48 set), rd2 = 0, immu6 = 2
    # EA = (rb3 + 0) & mask = 0x0000_FFFF_0000_0000 (RAM base)
    # i=0: load rb20 from RAM+0x000 (0xAA), i=1: load rb21 from RAM+0x008 (0xBB)
    # Without loop-internal mask: same (base already masked, +8 stays 48-bit)
    # With loop-internal mask: same (redundant but spec-correct)
    # This test verifies multi-reg load with high-bit rb[hb] works correctly.
    ("T27 boundary: ldm.o-rb 2 regs high bits",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = 0x0000_FFFF_0000_0000
      or_w_rb(3, 3, 0x0001),     # rb3 = 0x0001_FFFF_0000_0000 (bit 48 set)
      set_zw_rd(2, 0),           # rd2 = 0
      # Store test values to RAM base and RAM+8
      set_zw_rd(18, 0x00AA),
      st_o(18, 17, 0),           # RAM+0x000 = 0xAA
      set_zw_rd(18, 0x00BB),
      st_o(18, 17, 8),           # RAM+0x008 = 0xBB
      # ldm.o-rb rb20, rb3, rd2, 2 → rb20=mem[RAM+0], rb21=mem[RAM+8]
      ldm_o_rb(20, 3, 2, 2),
      # Check rb20 = 0xAA
      set_zw_rb(19, 0, 0x00AA),
      cmp_uo_rb(18, 20, 19),
      br_nz(18, 2),
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],
     PASS_EXIT,
     "ldm.o-rb 2 regs high bits: rb20 != 0xAA"),

    # T28: 48-bit top boundary — stm.o-rb 2 regs with rb[hb] bit48 set
    # rb3 = 0x0001_FFFF_0000_0000 (bit 48 set), rd2 = 0, immu6 = 2
    # EA = (rb3 + 0) & mask = 0x0000_FFFF_0000_0000 (RAM base)
    # Store rb10=0xCC, rb11=0xDD to RAM+0 and RAM+8, readback via ldm.o-rb
    ("T28 boundary: stm.o-rb 2 regs high bits",
     [set_zw_rb(3, 2, 0xFFFF),   # rb3 = 0x0000_FFFF_0000_0000
      or_w_rb(3, 3, 0x0001),     # rb3 = 0x0001_FFFF_0000_0000 (bit 48 set)
      set_zw_rd(2, 0),           # rd2 = 0
      # Pre-clear RAM
      set_zw_rd(18, 0),
      st_o(18, 17, 0),           # RAM+0x000 = 0
      st_o(18, 17, 8),           # RAM+0x008 = 0
      # Set source regs
      set_zw_rb(10, 0, 0x00CC),  # rb10 = 0xCC
      set_zw_rb(11, 0, 0x00DD),  # rb11 = 0xDD
      # stm.o-rb rb10, rb3, rd2, 2 → store rb10,rb11 to RAM+0, RAM+8
      stm_o_rb(10, 3, 2, 2),
      # Readback via ldm.o-rb using rb17 (RAM base)
      ldm_o_rb(20, 17, 2, 2),   # rb20=mem[RAM+0], rb21=mem[RAM+8]
      # Check rb20 = 0xCC
      set_zw_rb(19, 0, 0x00CC),
      cmp_uo_rb(18, 20, 19),
      br_nz(18, 5),              # if rb20 != 0xCC, skip to FAIL (5 insns ahead)
      # Check rb21 = 0xDD
      set_zw_rb(19, 0, 0x00DD),
      cmp_uo_rb(18, 21, 19),
      br_nz(18, 2),              # if rb21 != 0xDD, skip to FAIL
      # PASS
      set_zw_rd(18, 0),
      st_o(18, 16, 0),
      # FAIL
      set_zw_rd(18, 1),
      st_o(18, 16, 0)],
     PASS_EXIT,
     "stm.o-rb 2 regs high bits: round-trip mismatch"),
]

# ── CTL self-check ────────────────────────────────────────────────────

CTL_CHECKS = [
    ("CTL: ldm.o-rb PASS but expect ILLI (wrong)",
     [set_zw_rb(3, 2, 0xFFFF), set_zw_rd(2, 0),
      ldm_o_rb(1, 3, 2, 1),     # valid → PASS
      set_zw_rd(18, 0), st_o(18, 16, 0)],
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect valid ldm.o-rb"),
    ("CTL: ldm.o-rb ILLI but expect PASS (wrong)",
     [set_zw_rb(3, 2, 0xFFFF), set_zw_rd(2, 0),
      ldm_o_rb(0, 3, 2, 1)],    # ILLI (rb0 dest)
     PASS_EXIT,
     "Self-check FAILED: probe cannot detect ILLI"),
    ("CTL: ldm.o-rb MALIGN but expect PASS (wrong)",
     [set_zw_rb(3, 2, 0xFFFF), set_zw_rd(2, 7),
      ldm_o_rb(1, 3, 2, 1)],    # MALIGN (unaligned)
     PASS_EXIT,
     "Self-check FAILED: probe cannot detect MALIGN"),
    ("CTL: stm.o-rb PASS but expect ILLI (wrong)",
     [set_zw_rb(3, 2, 0xFFFF), set_zw_rb(1, 0, 0x42), set_zw_rd(2, 0),
      stm_o_rb(1, 3, 2, 1),     # valid → PASS
      set_zw_rd(18, 0), st_o(18, 16, 0)],
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect valid stm.o-rb"),
    ("CTL: stm.o-rb ILLI but expect PASS (wrong)",
     [set_zw_rb(3, 2, 0xFFFF), set_zw_rd(2, 0),
      stm_o_rb(0, 3, 2, 1)],    # ILLI (rb0 src)
     PASS_EXIT,
     "Self-check FAILED: probe cannot detect stm.o-rb ILLI"),
    ("CTL: stm.o-rb MALIGN but expect PASS (wrong)",
     [set_zw_rb(3, 2, 0xFFFF), set_zw_rb(1, 0, 0x42), set_zw_rd(2, 7),
      stm_o_rb(1, 3, 2, 1)],    # MALIGN (unaligned)
     PASS_EXIT,
     "Self-check FAILED: probe cannot detect stm.o-rb MALIGN"),
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
        elif code == -1:
            status = "TIMEOUT"; failed += 1
            fail_details.append(f"  [{status}] {name}: TIMEOUT")
        else:
            status = "FAIL"; failed += 1
            fail_details.append(f"  [{status}] {name}: exit=0x{code:02X} (expect 0x{expected:02X}) — {fail_desc}")
        print(f"  [{status}] {name}: exit=0x{code:02X} (expect 0x{expected:02X})")
    return passed, failed, fail_details

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 70)
    print("QEMU-010t Min ROM Probe (ldm.o-rb + stm.o-rb)")
    print("=" * 70)

    print("-" * 70)
    print("Main tests:")
    print("-" * 70)
    passed, failed, fail_details = run_test_group(TESTS, "main")
    print(f"\nMain results: {passed}/{passed+failed} passed, {failed} failed")
    if fail_details:
        print("\nFailed:")
        for d in fail_details: print(d)

    print("\n" + "-" * 70)
    print("CTL self-check:")
    print("-" * 70)
    ctl_p, ctl_f, ctl_details = run_test_group(CTL_CHECKS, "CTL")
    ctl_ok = ctl_f == len(CTL_CHECKS)
    if not ctl_ok:
        print(f"  WARNING: {ctl_p} CTL check(s) passed with wrong expectations — probe is BROKEN")
    print(f"  Probe: {'OK (can detect errors)' if ctl_ok else 'BROKEN'}")

    print(f"\n{'=' * 70}")
    all_pass = failed == 0 and ctl_ok
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
