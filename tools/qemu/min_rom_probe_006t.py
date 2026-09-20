#!/usr/bin/env python3
"""Min ROM probe for QEMU-006t RD Load/Store + MALIGN + jump/br.nz.

Architecture: test code runs from ROM (same as 005t probe pattern).
Kernel binary provides test data (loaded at RAM base).

Tests cover:
- Legal st.o to exit port → PASS (0x00)
- Legal ld.o from aligned RAM → no crash
- Unaligned ld.o/st.o → MALIGN (0x8C)
- ILLI: rdha=0, immu6=0, rdha+immu6>64
- br.nz rd: taken/not-taken
- stm.o/ldm.o round-trip

Exit codes (ADR-0004 D5.8):
  0x00 = PASS, 0x88 = ILLI, 0x89 = UNDI, 0x8C = MALIGN

Usage: python3 tools/qemu/min_rom_probe_006t.py
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

def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_oiii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)

def set_zw_rb(rb, immu16):
    return encode_rwii(0x4E, rb, 0, immu16)

def or_w_rb(rb, wpN, immu16):
    return encode_rwii(0x4A, rb, wpN, immu16)

def add_si_rb(rb, imms18):
    return encode_riii(0x5B, rb, imms18 & 0x3FFFF)

def cmp_uo(rdhb, rdhc, rdhd):
    return encode_rrii(0x40, 0x2A, rdhb, rdhc, rdhd)

def div_uo(rdhb, rdhc, rdhd):
    return encode_rrii(0x40, 0x38, rdhb, rdhc, rdhd)

def ld_o(rdha, rbhb, imms12):
    """ld.o rdha, rbhb, imms12 (op=0x20)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x20, rdha, rbhb, hc, hd)

def st_o(rdha, rbhb, imms12):
    """st.o rdha, rbhb, imms12 (op=0x21)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)

def ld_ub(rdha, rbhb, imms12):
    """ld.ub rdha, rbhb, imms12 (op=0x10)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x10, rdha, rbhb, hc, hd)

def st_t(rdha, rbhb, imms12):
    """st.t rdha, rbhb, imms12 (op=0x1A)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x1A, rdha, rbhb, hc, hd)

def ldm_o(rdha, rbhb, rdhc, immu6):
    return encode_rrii(0x38, rdha, rbhb, rdhc, immu6)

def stm_o(rdha, rbhb, rdhc, immu6):
    return encode_rrii(0x39, rdha, rbhb, rdhc, immu6)

def stm_b(rdha, rbhb, rdhc, immu6):
    """stm.b rdha, rbhb, rdhc, immu6 (op=0x30)"""
    return encode_rrii(0x30, rdha, rbhb, rdhc, immu6)

def stm_w(rdha, rbhb, rdhc, immu6):
    """stm.w rdha, rbhb, rdhc, immu6 (op=0x31)"""
    return encode_rrii(0x31, rdha, rbhb, rdhc, immu6)

def stm_t(rdha, rbhb, rdhc, immu6):
    """stm.t rdha, rbhb, rdhc, immu6 (op=0x32)"""
    return encode_rrii(0x32, rdha, rbhb, rdhc, immu6)

def jump_rrii(rbha, rdhb, imms12):
    """jump rbha, rdhb, imms12 (op=0x71)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x71, rbha, rdhb, hc, hd)

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
    Trampoline sets rb1=SP, rb2=RAM base, rb16=exit port, rb17=RAM base.
    All addresses are 48-bit: 0x0000_FFFF_xxxx_xxxx.
    set.zw wp2 sets bits[47:32]=0xFFFF, zeros bits[63:48] and bits[31:0]."""
    trampoline = [
        # rb1 = SP = 0x0000_FFFF_00FF_0000
        set_zw_rb(1, 0xFFFF),     # set.zw rb1, wp0, 0xFFFF → rb1=0xFFFF (WRONG for SP)
        # Actually need: set.zw rb1, wp2, 0xFFFF → rb1[47:32]=0xFFFF
        # Then: or.w rb1, wp1, 0x00FF → rb1[31:16] |= 0x00FF
        # set.zw wp2: encode_rwii(0x4E, 1, 2, 0xFFFF)
    ]
    # Use explicit wp2 encoding for correct 48-bit addresses
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
MALIGN_EXIT = 140  # 0x8C
UNMAPPED_EXIT = 135 # 0x87

# ── Test cases ────────────────────────────────────────────────────────
# After trampoline: rb16=exit port, rb17=RAM base, rb2=RAM base

TESTS = [
    # T1: st.o 0 to exit port → PASS (exit 0x00)
    ("T1 st.o 0 → exit port PASS",
     [set_zw_rd(18, 0x0000),    # rd18 = 0
      st_o(18, 16, 0)],         # st.o rd18, rb16, 0 → exit 0x00
     PASS_EXIT,
     "st.o to exit port failed"),

    # T2: st.o 1 → exit code 1
    ("T2 st.o 1 → exit code 1",
     [set_zw_rd(18, 0x0001),    # rd18 = 1
      st_o(18, 16, 0)],         # st.o rd18, rb16, 0 → exit 0x01
     1,
     "st.o FAIL code failed"),

    # T3: ld.o from RAM (aligned) + PASS
    ("T3 ld.o from RAM (aligned)",
     [ld_o(18, 17, 0),          # ld.o rd18, rb17, 0 (RAM+0, aligned)
      set_zw_rd(18, 0x0000),
      st_o(18, 16, 0)],
     PASS_EXIT,
     "ld.o from RAM crashed"),

    # T4: ld.o from RAM+8 (aligned)
    ("T4 ld.o from RAM+8 (aligned)",
     [ld_o(18, 17, 8),          # ld.o rd18, rb17, 8
      set_zw_rd(18, 0x0000),
      st_o(18, 16, 0)],
     PASS_EXIT,
     "ld.o from RAM+8 crashed"),

    # T5: Unaligned ld.o (RAM+1) → MALIGN
    ("T5 ld.o RAM+1 → MALIGN",
     [encode_rwii(0x4E, 18, 2, 0xFFFF),  # rb18 = 0x0000FFFF_00000000
      encode_rwii(0x4A, 18, 0, 0x0001),  # rb18 |= 0x0001 → RAM+1
      ld_o(19, 18, 0)],                  # ld.o rd19, rb18, 0 → unaligned
     MALIGN_EXIT,
     "ld.o unaligned not MALIGN"),

    # T6: Unaligned ld.o (RAM+4) → MALIGN (needs 8-byte align)
    ("T6 ld.o RAM+4 → MALIGN",
     [ld_o(18, 17, 4)],          # EA = rb17+4 = 0x0000FFFF_00000004 (4-byte, not 8-byte)
     MALIGN_EXIT,
     "ld.o at 4-byte offset not MALIGN"),

    # T7: ld.o rd0 → ILLI
    ("T7 ld.o rd0 → ILLI",
     [ld_o(0, 17, 0)],
     ILLI_EXIT,
     "ld.o rd0 not ILLI"),

    # T8: st.o rd0 → ILLI
    ("T8 st.o rd0 → ILLI",
     [st_o(0, 16, 0)],
     ILLI_EXIT,
     "st.o rd0 not ILLI"),

    # T9: ldm.o immu6=0 → ILLI
    ("T9 ldm.o immu6=0 → ILLI",
     [set_zw_rd(19, 0),
      ldm_o(18, 17, 19, 0)],
     ILLI_EXIT,
     "ldm.o immu6=0 not ILLI"),

    # T10: ldm.o rdha+immu6>64 → ILLI
    ("T10 ldm.o rd60+8>64 → ILLI",
     [set_zw_rd(19, 0),
      ldm_o(60, 17, 19, 8)],
     ILLI_EXIT,
     "ldm.o rd60+8 not ILLI"),

    # T11: Legal ldm.o (2 regs from RAM)
    ("T11 ldm.o 2 regs (legal)",
     [set_zw_rd(19, 0),
      ldm_o(20, 17, 19, 2),     # ldm.o rd20, rb17, rd19, 2
      set_zw_rd(18, 0x0000),
      st_o(18, 16, 0)],
     PASS_EXIT,
     "Legal ldm.o crashed"),

    # T12: stm.o+ldm.o round-trip (exact value)
    # Use rb18 = RAM+0x100 for data area
    ("T12 stm.o+ldm.o round-trip",
     [encode_rwii(0x4E, 18, 2, 0xFFFF),  # rb18 = 0x0000FFFF_00000000
      encode_rwii(0x4A, 18, 0, 0x0100),  # rb18 |= 0x0100 → RAM+0x100
      set_zw_rd(20, 0x0042),             # rd20 = 0x42
      set_zw_rd(19, 0),                  # rd19 = 0 (offset)
      stm_o(20, 18, 19, 1),              # stm.o rd20, rb18, rd19, 1
      ldm_o(21, 18, 19, 1),              # ldm.o rd21, rb18, rd19, 1
      set_zw_rd(22, 0x0042),             # expected = 0x42
      cmp_uo(23, 21, 22),                # cmp.uo rd23, rd21, rd22
      div_uo(24, 23, 23)],               # div-by-zero if equal → ILLI
     ILLI_EXIT,
     "stm.o/ldm.o round-trip mismatch"),

    # T13: Unaligned stm.o → MALIGN
    ("T13 stm.o unaligned → MALIGN",
     [encode_rwii(0x4E, 18, 2, 0xFFFF),  # rb18 = 0x0000FFFF_00000000
      encode_rwii(0x4A, 18, 0, 0x0001),  # rb18 = RAM+1
      set_zw_rd(20, 0x0042), set_zw_rd(19, 0),
      stm_o(20, 18, 19, 1)],
     MALIGN_EXIT,
     "stm.o unaligned not MALIGN"),

    # T14: ld.ub (byte, no alignment)
    ("T14 ld.ub RAM+1 (byte, no align)",
     [ld_ub(18, 17, 1),         # ld.ub rd18, rb17, 1 (byte)
      set_zw_rd(18, 0x0000),
      st_o(18, 16, 0)],
     PASS_EXIT,
     "ld.ub from RAM+1 crashed"),

    # T15: br.nz rd=0 not taken → PASS
    ("T15 br.nz rd0 not taken → PASS",
     [set_zw_rd(18, 0x0000),    # rd18 = 0
      br_nz(18, 2),             # br.nz rd18, +2 → not taken
      set_zw_rd(19, 0x0000),
      st_o(19, 16, 0)],         # PASS
     PASS_EXIT,
     "br.nz not-taken failed"),

    # T16: br.nz rd=1 taken → skip fail
    ("T16 br.nz rd!=0 taken → PASS",
     [set_zw_rd(18, 0x0001),    # rd18 = 1
      br_nz(18, 3),             # br.nz rd18, +3 → taken, skip 2 insns + land at PASS
      set_zw_rd(19, 0x0001),    # skipped: rd19 = 1 (FAIL)
      st_o(19, 16, 0),          # skipped: st.o FAIL
      set_zw_rd(19, 0x0000),    # landed: rd19 = 0 (PASS)
      st_o(19, 16, 0)],
     PASS_EXIT,
     "br.nz taken failed"),

    # T17: ILLI: stm.o immu6=0
    ("T17 stm.o immu6=0 → ILLI",
     [set_zw_rd(20, 0x42), set_zw_rd(19, 0),
      stm_o(20, 17, 19, 0)],
     ILLI_EXIT,
     "stm.o immu6=0 not ILLI"),

    # T18: Unaligned ld.uw → MALIGN (wyde=2 byte align)
    ("T18 ld.uw RAM+1 → MALIGN",
     [encode_rrii(0x11, 18, 17, 0, 1)],  # ld.uw rd18, rb17, 1
     MALIGN_EXIT,
     "ld.uw unaligned not MALIGN"),

    # T19: Unaligned ld.ut → MALIGN (tetra=4 byte align)
    ("T19 ld.ut RAM+2 → MALIGN",
     [encode_rrii(0x12, 18, 17, 0, 2)],  # ld.ut rd18, rb17, 2
     MALIGN_EXIT,
     "ld.ut unaligned not MALIGN"),

    # T20: Unaligned single st.o → MALIGN (J3 fix)
    ("T20 st.o RAM+1 → MALIGN",
     [encode_rwii(0x4E, 18, 2, 0xFFFF),  # rb18 = 0x0000FFFF_00000000
      encode_rwii(0x4A, 18, 0, 0x0001),  # rb18 = RAM+1
      set_zw_rd(20, 0x0042),             # rd20 = 0x42
      st_o(20, 18, 0)],                  # st.o rd20, rb18, 0 → unaligned
     MALIGN_EXIT,
     "st.o unaligned not MALIGN"),

    # T21: Unaligned st.o RAM+4 → MALIGN (J3 fix, needs 8-byte align)
    ("T21 st.o RAM+4 → MALIGN",
     [set_zw_rd(20, 0x0042),
      st_o(20, 17, 4)],                  # EA = rb17+4 = RAM+4 (4-byte, not 8-byte)
     MALIGN_EXIT,
     "st.o at 4-byte offset not MALIGN"),

    # T22: st.t to exit port → ILLI (J4 fix, ADR-0004 D3/D5.6)
    ("T22 st.t exit port → ILLI",
     [set_zw_rd(18, 0x0042),
      st_t(18, 16, 0)],                  # st.t rd18, rb16, 0 → exit port (non-8B)
     ILLI_EXIT,
     "st.t to exit port not ILLI"),

    # T23: st.t to exit port +4 → ILLI (J4 fix)
    ("T23 st.t exit+4 → ILLI",
     [set_zw_rd(18, 0x0042),
      st_t(18, 16, 4)],                  # st.t rd18, rb16, 4 → exit port + 4
     ILLI_EXIT,
     "st.t to exit+4 not ILLI"),

    # T24: ROM store → ILLI (J5 fix, ADR-0004 D5.6)
    # ROM base = 0xffff_ffff_0000; rb0 = PC (translation-time)
    # st.o with imms12=4 so EA = rb0+4 is 8-byte aligned ROM address
    # (MALIGN priority > ILLI per D5.6, so must be aligned to reach ROM-store check)
    ("T24 st.o ROM → ILLI",
     [set_zw_rd(18, 0x0042),
      st_o(18, 0, 4)],                   # st.o rd18, rb0, 4 → EA = PC+4, ROM, aligned
     ILLI_EXIT,
     "st.o to ROM not ILLI"),

    # T25: jump-rrii e2e (J1 fix, should not SIGABRT)
    # jump rb2, rd0, 0 → PC = rb2 + rd0 + 0 = RAM base
    # RAM base has kernel = illi() → ILLI exit (not crash)
    ("T25 jump-rrii → no crash (ILLI)",
     [jump_rrii(2, 0, 0)],               # jump to RAM base (trampoline set rb2=RAM base)
     ILLI_EXIT,                           # kernel is illi → 0x88
     "jump-rrii crashed (SIGABRT)"),

    # T26: br.nz taken with correct PC target (J2 fix)
    # Branch instruction at offset +48 from trampoline end (after 6 trampoline insns)
    # rb0 = current instruction PC (translation-time), not TB start
    # Layout: set.zw rd18,1; br.nz rd18,+2; set.zw rd19,1; st.o rd19,rb16,0 (FAIL); st.o rd0,rb16,0 (PASS)
    ("T26 br.nz taken → skip to PASS",
     [set_zw_rd(18, 0x0001),             # rd18 = 1
      br_nz(18, 3),                      # br.nz rd18, +3 → taken, skip 2 insns
      set_zw_rd(19, 0x0001),             # skipped: rd19 = 1 (FAIL)
      st_o(19, 16, 0),                   # skipped: FAIL
      set_zw_rd(19, 0x0000),             # landed: rd19 = 0 (PASS)
      st_o(19, 16, 0)],
     PASS_EXIT,
     "br.nz taken wrong PC target"),

    # T27: br.nz not-taken → fall through to PASS (J2 fix verification)
    ("T27 br.nz not-taken → PASS",
     [set_zw_rd(18, 0x0000),             # rd18 = 0
      br_nz(18, 3),                      # br.nz rd18, +3 → not taken
      set_zw_rd(19, 0x0000),             # rd19 = 0 (PASS)
      st_o(19, 16, 0)],
     PASS_EXIT,
     "br.nz not-taken failed"),

    # T28: stm.o → exit port → ILLI (J4 fix, ADR-0004 D5.6)
    # stm.o generates 8B store, same as st.o; device handler can't distinguish.
    # Translate-layer runtime check catches EA in exit port range.
    ("T28 stm.o exit port → ILLI",
     [set_zw_rd(20, 0x0042),             # rd20 = 0x42
      set_zw_rd(19, 0),                  # rd19 = 0 (offset)
      stm_o(20, 16, 19, 1)],             # stm.o rd20, rb16, rd19, 1 → exit port
     ILLI_EXIT,
     "stm.o to exit port not ILLI"),

    # T29: stm.t → exit port → ILLI (J4 fix, ADR-0004 D5.6)
    ("T29 stm.t exit port → ILLI",
     [set_zw_rd(20, 0x0042),
      set_zw_rd(19, 0),
      stm_t(20, 16, 19, 1)],             # stm.t rd20, rb16, rd19, 1 → exit port
     ILLI_EXIT,
     "stm.t to exit port not ILLI"),

    # T30: stm.w → exit port → ILLI (J4 fix, ADR-0004 D5.6)
    ("T30 stm.w exit port → ILLI",
     [set_zw_rd(20, 0x0042),
      set_zw_rd(19, 0),
      stm_w(20, 16, 19, 1)],             # stm.w rd20, rb16, rd19, 1 → exit port
     ILLI_EXIT,
     "stm.w to exit port not ILLI"),

    # T31: stm.b → exit port → ILLI (J4 fix, ADR-0004 D5.6)
    ("T31 stm.b exit port → ILLI",
     [set_zw_rd(20, 0x0042),
      set_zw_rd(19, 0),
      stm_b(20, 16, 19, 1)],             # stm.b rd20, rb16, rd19, 1 → exit port
     ILLI_EXIT,
     "stm.b to exit port not ILLI"),

    # T32: stm.o exit+1 (unaligned) → MALIGN (J6 fix, ADR-0004 D5.6 priority)
    # EA = exit+1, unaligned for 8B → MO_ALIGN_8 triggers MALIGN (not ILLI)
    ("T32 stm.o exit+1 (unaligned) → MALIGN",
     [set_zw_rd(20, 0x0042),
      set_zw_rd(19, 1),                   # rd19 = 1 (offset)
      stm_o(20, 16, 19, 1)],              # stm.o rd20, rb16, rd19, 1 → EA=exit+1
     MALIGN_EXIT,
     "stm.o unaligned exit not MALIGN"),

    # T33: stm.t exit+2 (unaligned) → MALIGN (J6 fix)
    # EA = exit+2, unaligned for 4B (2 mod 4 ≠ 0) → MO_ALIGN_4 triggers MALIGN
    ("T33 stm.t exit+2 (unaligned) → MALIGN",
     [set_zw_rd(20, 0x0042),
      set_zw_rd(19, 2),                   # rd19 = 2 (offset)
      stm_t(20, 16, 19, 1)],              # stm.t rd20, rb16, rd19, 1 → EA=exit+2
     MALIGN_EXIT,
     "stm.t unaligned exit not MALIGN"),

    # T34: stm.w exit+1 (unaligned) → MALIGN (J6 fix)
    # EA = exit+1, unaligned for 2B (1 mod 2 ≠ 0) → MO_ALIGN_2 triggers MALIGN
    ("T34 stm.w exit+1 (unaligned) → MALIGN",
     [set_zw_rd(20, 0x0042),
      set_zw_rd(19, 1),                   # rd19 = 1 (offset)
      stm_w(20, 16, 19, 1)],              # stm.w rd20, rb16, rd19, 1 → EA=exit+1
     MALIGN_EXIT,
     "stm.w unaligned exit not MALIGN"),
]

# ── CTL self-check ────────────────────────────────────────────────────

CTL_CHECKS = [
    ("CTL: st.o PASS but expect MALIGN (wrong)",
     [set_zw_rd(18, 0x0000), st_o(18, 16, 0)],
     MALIGN_EXIT,
     "Self-check FAILED: probe cannot detect wrong values"),
    ("CTL: stm.o exit ILLI but expect PASS (wrong)",
     [set_zw_rd(20, 0x0042), set_zw_rd(19, 0), stm_o(20, 16, 19, 1)],
     PASS_EXIT,
     "Self-check FAILED: probe cannot detect stm.o exit-port ILLI"),
    ("CTL: stm.o unaligned exit MALIGN but expect ILLI (wrong)",
     [set_zw_rd(20, 0x0042), set_zw_rd(19, 1), stm_o(20, 16, 19, 1)],
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect alignment priority"),
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
    print("QEMU-006t Min ROM Probe (load/store + MALIGN + jump/br.nz)")
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
    # CTL checks have WRONG expectations on purpose.
    # All should FAIL (= probe detects errors) -> ctl_f == len(CTL_CHECKS).
    # If any PASS (= probe can't detect that error), probe is broken.
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