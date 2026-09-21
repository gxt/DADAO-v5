#!/usr/bin/env python3
"""Min ROM probe for QEMU-013t: RA instruction semantics (ld.o-ra/st.o-ra,
ldm.o-ra/stm.o-ra, rd2ra/ra2rd) + MemRAS support (§5.6.1/§5.6.2 case 3).

Tests cover:
  M1: ld.o-ra/st.o-ra normal (RAM round-trip)
  M2: ld.o-ra MALIGN (unaligned → 0x8C)
  M3: ldm.o-ra normal (multi-register load from RAM)
  M4: stm.o-ra normal (multi-register store to RAM)
  M5: ldm.o-ra ILLI (immu6=0 → 0x88)
  M6: stm.o-ra ILLI (ra+immu6>64 → 0x88)
  M7: ldm.o-ra MALIGN (unaligned → 0x8C)
  B1: rd2ra normal (RD→RA block copy)
  B2: ra2rd normal (RA→RD block copy)
  B3: rd2ra→ra2rd round-trip (2 registers)
  B4: rd2ra ILLI (immu6=0 → 0x88)
  B5: ra2rd ILLI (immu6=0 → 0x88)
  B6: ra2rd ILLI (dest=rd0 → 0x88)
  B7: rd2ra ILLI (range overflow → 0x88)
  B8: ra2rd ILLI (range overflow → 0x88)
  B9: rd2ra/ra2rd overlap (ascending order read-before-write)
  R1: MemRAS round-trip (set ra0 buffer, deep calls spill to MemRAS)
  R2: RASOF without MemRAS (64 calls → 0x8A)
  X1: MemRAS spill refcount overflow (ra0.hi16=0xFFFF) → RASOF 0x8A
  X2: MemRAS pop refcount underflow (ra0.hi16=0, low48!=0) → RASUF 0x8B
  X3: MemRAS invalid content (entry hi16=0) → RASUF 0x8B; ra0 unchanged (precise)
      (read-back via -d cpu dump, parsed by last_ra_dump)

Usage: python3 tools/qemu/min_rom_probe_013t.py
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

def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_riii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

def encode_iiii(op, immu24):
    return struct.pack('>I', (op << 24) | (immu24 & 0xFFFFFF))

def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

# ── Common instruction mnemonics ──────────────────────────────────────

def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)

def or_w_rd(rd, wpN, immu16):
    return encode_rwii(0x48, rd, wpN, immu16)

def st_o_rd(rdha, rbhb, imms12):
    """st.o rdha, rbhb, imms12 (op=0x21, rrii) - general store to RAM"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)

def ld_o_rd(rdha, rbhb, imms12):
    """ld.o rdha, rbhb, imms12 (op=0x20, rrii) - general load from RAM"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x20, rdha, rbhb, hc, hd)

def st_o_rd_pass():
    """st.o rd18, rb16, 0 — assumes rd18==0 (set by caller)"""
    return encode_rrii(0x21, 18, 16, 0, 0)

def st_o_rd_fail():
    """st.o rd19, rb16, 0 — assumes rd19==1 (set by caller)"""
    return encode_rrii(0x21, 19, 16, 0, 0)

def cmp_uo_rd(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd (MISC ha=0x2A)"""
    return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)

def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)

def call_iiii(imms24):
    return encode_iiii(0x74, imms24 & 0xFFFFFF)

def ret_riii(rdha, imms18):
    return encode_riii(0x76, rdha, imms18 & 0x3FFFF)

def illi():
    return encode_orri(0x00, 0x00, 0, 0, 0)

# ── RA instruction mnemonics ──────────────────────────────────────────

def ld_o_ra(raha, rbhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x24, raha, rbhb, hc, hd)

def st_o_ra(raha, rbhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x25, raha, rbhb, hc, hd)

def ldm_o_ra(raha, rbhb, rdhc, immu6):
    return encode_rrii(0x3C, raha, rbhb, rdhc, immu6 & 0x3F)

def stm_o_ra(raha, rbhb, rdhc, immu6):
    return encode_rrii(0x3D, raha, rbhb, rdhc, immu6 & 0x3F)

def words(*pairs):
    """Build a 64-bit RD value from (wpN, immu16) pairs: first set.zw, rest or.w."""
    out = []
    for i, (wp, val) in enumerate(pairs):
        out.append(encode_rwii(0x4C if i == 0 else 0x48, 18, wp, val))
    return out

def rd2ra(rahb, rdhc, immu6):
    """rd2ra (MISC ha=0x2D)"""
    return encode_orri(0x40, 0x2D, rahb, rdhc, immu6 & 0x3F)

def ra2rd(rdhb, rahc, immu6):
    """ra2rd (MISC ha=0x2E)"""
    return encode_orri(0x40, 0x2E, rdhb, rahc, immu6 & 0x3F)

# ── Terminators and ROM builder ───────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

def build_rom(test_insns):
    """Build ROM: [trampoline | test_insns | UNDI | padding]."""
    trampoline = [
        encode_rwii(0x4E, 1, 2, 0xFFFF),  # set.zw rb1, wp2, 0xFFFF
        encode_rwii(0x4A, 1, 1, 0x00FF),  # or.w rb1, wp1, 0x00FF (SP)
        encode_rwii(0x4E, 2, 2, 0xFFFF),  # set.zw rb2, wp2, 0xFFFF
        encode_rwii(0x4E, 16, 2, 0xFFFF), # set.zw rb16, wp2, 0xFFFF
        encode_rwii(0x4A, 16, 1, 0x8000), # or.w rb16, wp1, 0x8000 (exit port)
        encode_rwii(0x4E, 17, 2, 0xFFFF), # set.zw rb17, wp2, 0xFFFF (RAM base)
    ]
    rom = b''.join(trampoline) + b''.join(test_insns) + UNDI_TERMINATOR
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

def run_test_dcpu(rom_data, kernel_data=None, timeout=10):
    """Like run_test but with -d cpu, returning (exit_code, log_text).
    Used for precise-exception read-back: parse RA[00] etc. from the fault dump."""
    if kernel_data is None:
        kernel_data = illi() * 4
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(rom_data); rom_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(kernel_data); kernel_path = f.name
    log_path = rom_path + '.cpu.log'
    try:
        result = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic',
             '-bios', rom_path, '-kernel', kernel_path,
             '-d', 'cpu', '-D', log_path],
            capture_output=True, timeout=timeout, text=True)
        with open(log_path) as lf:
            return result.returncode, lf.read()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rom_path); os.unlink(kernel_path)
        if os.path.exists(log_path):
            os.unlink(log_path)

def last_ra_dump(log_text):
    """Return the last RA[00] value seen in a -d cpu dump, or None."""
    import re
    m = None
    for mm in re.finditer(r'RA\[00\]:\s*([0-9a-fA-F]{16})', log_text):
        m = mm
    return int(m.group(1), 16) if m else None

# ── Exit codes ────────────────────────────────────────────────────────

PASS_EXIT = 0; ILLI_EXIT = 136; RASOF_EXIT = 138; RASUF_EXIT = 139; MALIGN_EXIT = 140

# ── Helper: PASS/FAIL epilogue ────────────────────────────────────────
# All tests use: set rd18=0, set rd19=1 before the test body.
# PASS = st.o rd18, rb16, 0 (rd18=0)
# FAIL = st.o rd19, rb16, 0 (rd19=1)

def pass_fail_epilogue(offset_to_pass):
    """Generate epilogue: br_nz skips to FAIL, then PASS, then FAIL."""
    # offset_to_pass: how many instructions br_nz should skip to reach FAIL
    return [
        st_o_rd_pass(),              # PASS (rd18=0, rb16=exit port)
        set_zw_rd(19, 0x0001),      # rd19 = 1 (FAIL value)
        st_o_rd_fail(),              # FAIL
    ]

# ── Test cases ────────────────────────────────────────────────────────

TESTS = [
    # ── ld.o-ra / st.o-ra tests ───────────────────────────────────────

    # M1: ld.o-ra/st.o-ra normal (RAM round-trip)
    # Construct 0xDEADBEEFCAFEBABE in rd18, rd2ra→ra10, st.o-ra to RAM,
    # ld.o-ra back to ra11, ra2rd→rd19, compare.
    ("M1 ld.o-ra/st.o-ra normal (RAM round-trip)",
     [set_zw_rd(18, 0xDEAD), or_w_rd(18, 1, 0xBEEF),
      or_w_rd(18, 2, 0xCAFE), or_w_rd(18, 3, 0xBABE),
      set_zw_rd(20, 0),         # rd20=0 for PASS
      rd2ra(10, 18, 1),         # ra10 = 0xDEADBEEFCAFEBABE
      st_o_ra(10, 17, 16),      # mem64[RAM+16] = ra10
      ld_o_ra(11, 17, 16),      # ra11 = mem64[RAM+16]
      ra2rd(19, 11, 1),         # rd19 = ra11
      cmp_uo_rd(20, 18, 19),    # rd20 = cmp(rd18, rd19) — OVERWRITES rd20!
      br_nz(20, 2),             # mismatch → skip to FAIL
      st_o_rd(20, 16, 0),       # PASS (rd20=0 from cmp equal result)
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT,
     "ld.o-ra/st.o-ra round-trip failed"),

    # M2: ld.o-ra MALIGN (unaligned → 0x8C)
    ("M2 ld.o-ra MALIGN (unaligned → 0x8C)",
     [ld_o_ra(10, 17, 1),         # EA = RAM+1 → MALIGN
      set_zw_rd(18, 0x0001), st_o_rd_pass()],
     MALIGN_EXIT,
     "ld.o-ra unaligned didn't trigger MALIGN"),

    # M3: ldm.o-ra normal (multi-register load from RAM)
    ("M3 ldm.o-ra normal (multi-register load from RAM)",
     [set_zw_rd(18, 0x00AA), st_o_rd(18, 17, 16),  # mem64[RAM+16]=0xAA
      set_zw_rd(19, 0x00BB), st_o_rd(19, 17, 24),   # mem64[RAM+24]=0xBB
      set_zw_rd(20, 16),          # rd20 = 16 (offset)
      ldm_o_ra(10, 17, 20, 2),    # ra10=mem[RAM+16]=0xAA, ra11=mem[RAM+24]=0xBB
      ra2rd(21, 10, 2),           # rd21=ra10=0xAA, rd22=ra11=0xBB
      set_zw_rd(23, 0x00AA), set_zw_rd(24, 0x00BB),
      cmp_uo_rd(25, 21, 23),      # compare rd21 vs 0xAA
      br_nz(25, 5),
      cmp_uo_rd(25, 22, 24),      # compare rd22 vs 0xBB
      br_nz(25, 3),
      set_zw_rd(18, 0), st_o_rd_pass(),
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT,
     "ldm.o-ra normal failed"),

    # M4: stm.o-ra normal (multi-register store to RAM)
    ("M4 stm.o-ra normal (multi-register store to RAM)",
     [set_zw_rd(18, 0x00CC), set_zw_rd(19, 0x00DD),
      rd2ra(10, 18, 2),           # ra10=0xCC, ra11=0xDD
      set_zw_rd(20, 32),          # offset=32
      stm_o_ra(10, 17, 20, 2),    # mem[RAM+32]=ra10, mem[RAM+40]=ra11
      ld_o_ra(11, 17, 32),        # ra11 = mem[RAM+32] = 0xCC
      ra2rd(21, 11, 1),           # rd21 = ra11 = 0xCC
      cmp_uo_rd(25, 21, 18),      # compare rd21 vs 0xCC
      br_nz(25, 3),
      set_zw_rd(18, 0), st_o_rd_pass(),
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT,
     "stm.o-ra normal failed"),

    # M5-M7: ILLI and MALIGN
    ("M5 ldm.o-ra ILLI (immu6=0 → 0x88)",
     [ldm_o_ra(10, 17, 0, 0), set_zw_rd(18, 0x0001), st_o_rd_pass()],
     ILLI_EXIT, "ldm.o-ra immu6=0 didn't trigger ILLI"),

    ("M6 stm.o-ra ILLI (ra62+3>64 → 0x88)",
     [stm_o_ra(62, 17, 0, 3), set_zw_rd(18, 0x0001), st_o_rd_pass()],
     ILLI_EXIT, "stm.o-ra ra62+3 didn't trigger ILLI"),

    ("M7 ldm.o-ra MALIGN (unaligned → 0x8C)",
     [set_zw_rd(18, 1), ldm_o_ra(10, 17, 18, 1),
      set_zw_rd(18, 0x0001), st_o_rd_pass()],
     MALIGN_EXIT, "ldm.o-ra unaligned didn't trigger MALIGN"),

    # ── rd2ra / ra2rd tests ───────────────────────────────────────────

    # B1: rd2ra normal
    ("B1 rd2ra normal (RD→RA block copy)",
     [set_zw_rd(18, 0x0042), rd2ra(10, 18, 1), ra2rd(19, 10, 1),
      cmp_uo_rd(20, 18, 19), br_nz(20, 3),
      set_zw_rd(18, 0), st_o_rd_pass(),
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT, "rd2ra normal failed"),

    # B2: ra2rd normal — compare the copied value against a KNOWN constant
    # (not against a second copy of the same source, which cannot detect a wrong value).
    ("B2 ra2rd normal (RA→RD block copy)",
     [set_zw_rd(18, 0x00AB), or_w_rd(18, 1, 0xCD00),   # rd18 = 0xCD0000AB
      rd2ra(10, 18, 1),                                 # ra10 = 0xCD0000AB
      st_o_ra(10, 17, 0x40),                            # RAM[base+0x40] = 0xCD0000AB (side effect)
      set_zw_rd(18, 0), ra2rd(18, 10, 1),               # rd18 = ra10
      set_zw_rd(20, 0x00AB), or_w_rd(20, 1, 0xCD00),    # rd20 = 0xCD0000AB (expected)
      cmp_uo_rd(22, 18, 20), br_nz(22, 3),
      set_zw_rd(18, 0), st_o_rd_pass(),
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT, "ra2rd normal failed (copied value wrong)"),

    # B3: rd2ra→ra2rd round-trip (2 registers)
    ("B3 rd2ra→ra2rd round-trip (2 registers)",
     [set_zw_rd(18, 0x00AA), set_zw_rd(19, 0x00BB),
      rd2ra(10, 18, 2), ra2rd(20, 10, 2),
      cmp_uo_rd(22, 18, 20), br_nz(22, 5),
      cmp_uo_rd(22, 19, 21), br_nz(22, 3),
      set_zw_rd(18, 0), st_o_rd_pass(),
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT, "rd2ra→ra2rd round-trip failed"),

    # B4-B8: ILLI checks
    ("B4 rd2ra ILLI (immu6=0 → 0x88)",
     [rd2ra(10, 18, 0), set_zw_rd(18, 0x0001), st_o_rd_pass()],
     ILLI_EXIT, "rd2ra immu6=0 didn't trigger ILLI"),

    ("B5 ra2rd ILLI (immu6=0 → 0x88)",
     [ra2rd(18, 10, 0), set_zw_rd(18, 0x0001), st_o_rd_pass()],
     ILLI_EXIT, "ra2rd immu6=0 didn't trigger ILLI"),

    ("B6 ra2rd ILLI (dest=rd0 → 0x88)",
     [ra2rd(0, 10, 1), set_zw_rd(18, 0x0001), st_o_rd_pass()],
     ILLI_EXIT, "ra2rd dest=rd0 didn't trigger ILLI"),

    ("B7 rd2ra ILLI (ra62+3>64 → 0x88)",
     [rd2ra(62, 18, 3), set_zw_rd(18, 0x0001), st_o_rd_pass()],
     ILLI_EXIT, "rd2ra ra62+3 didn't trigger ILLI"),

    ("B8 ra2rd ILLI (rd62+3>64 → 0x88)",
     [ra2rd(62, 10, 3), set_zw_rd(18, 0x0001), st_o_rd_pass()],
     ILLI_EXIT, "ra2rd rd62+3 didn't trigger ILLI"),

    # B9: rd2ra→ra2rd adjacent windows.
    # NOTE (reviewer F3): rd2ra's source is RD, destination RA; ra2rd's source is RA,
    # destination RD — different register groups with NO aliasing. So §4.9.3's
    # "overlapping source/destination (ascending read-before-write)" rule is
    # VACUOUS for M1's rd2ra/ra2rd (it would apply to same-group copies). This case
    # only verifies that a 2-element window survives a round-trip in each direction.
    ("B9 rd2ra→ra2rd adjacent windows (aliasing not applicable)",
     [set_zw_rd(18, 0x0042), set_zw_rd(19, 0x0043),
      rd2ra(19, 18, 2),           # ra19=rd18=0x42, ra20=rd19=0x43
      ra2rd(20, 19, 2),           # rd20=ra19=0x42, rd21=ra20=0x43
      set_zw_rd(22, 0x0042), set_zw_rd(23, 0x0043),
      cmp_uo_rd(24, 20, 22), br_nz(24, 5),
      cmp_uo_rd(24, 21, 23), br_nz(24, 3),
      set_zw_rd(18, 0), st_o_rd_pass(),
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT, "rd2ra overlap failed"),

    # ── MemRAS tests ──────────────────────────────────────────────────

    # R1: MemRAS round-trip
    # Set ra0 = RAM+0x8000 (enables MemRAS), then 65 chained calls.
    # With MemRAS, the 64th call spills to MemRAS instead of RASOF.
    # Each call returns to the next instruction, which is a ret → pops next.
    # Final return → set rd18=0, PASS.
    #
    # Code layout: [ra0 setup] [call0] [PASS code] [call1,ret,illi] ... [call64,ret,illi] [ret]
    # call0 jumps 3 instructions forward (into the chain). Subsequent calls chain with call+3,ret,illi.
    # Each call pushes a distinct return address. The chain of rets unwinds.
    ("R1 MemRAS round-trip (65 calls, no RASOF)",
     [encode_rwii(0x4C, 18, 2, 0xFFFF),  # set.zw rd18, wp2, 0xFFFF → 0xFFFF_0000_0000_0000
      encode_rwii(0x48, 18, 0, 0x8000),  # or.w rd18, wp0, 0x8000 → 0xFFFF_0000_8000
      rd2ra(0, 18, 1),                    # ra0 = rd18 = 0xFFFF_0000_8000
      call_iiii(3),                       # call → target (idx3), ret_addr = next
      set_zw_rd(18, 0), st_o_rd_pass(),  # return point → PASS
     ] +
     [t for i in range(1, 65) for t in [call_iiii(3), ret_riii(0, 0), illi()]] +
     [ret_riii(0, 0)],
     PASS_EXIT,
     "MemRAS round-trip failed (RASOF with MemRAS enabled)"),

    # R2: RASOF without MemRAS (64 chained calls)
    # Same pattern as012t R2b: [call_iiii(1)] * 64 → RASOF
    ("R2 RASOF without MemRAS (64 calls → 0x8A)",
     [call_iiii(1)] * 64 +
     [set_zw_rd(18, 0x0001), st_o_rd_pass()],
     RASOF_EXIT,
     "RASOF not triggered without MemRAS"),

    # ── MemRAS exception paths (F2) ───────────────────────────────────
    # X1: MemRAS refcount overflow at spill (ra0.hi16==0xFFFF) → RASOF
    ("X1 MemRAS spill refcount overflow (ra0.hi16=0xFFFF) → 0x8A",
     words((3, 0xFFFF), (2, 0xFFFF), (0, 0x8000)) +   # rd18 = 0xFFFF_FFFF_0000_8000
     [rd2ra(0, 18, 1)] +
     [call_iiii(1)] * 64 +
     [set_zw_rd(18, 0x0001), st_o_rd_pass()],
     RASOF_EXIT, "MemRAS refcount overflow didn't trigger RASOF"),

    # X2: MemRAS refcount underflow at pop (ra0.hi16==0, low48!=0) → RASUF
    ("X2 MemRAS pop refcount underflow (ra0.hi16=0) → 0x8B",
     words((3, 0x0000), (2, 0xFFFF), (0, 0x8000)) +   # rd18 = 0x0000_FFFF_0000_8000
     [rd2ra(0, 18, 1), ret_riii(0, 0),
      set_zw_rd(18, 0x0001), st_o_rd_pass()],
     RASUF_EXIT, "MemRAS refcount underflow didn't trigger RASUF"),

    # X3: MemRAS invalid content (entry hi16==0) → RASUF, and ra0 must be UNCHANGED
    # (precise exception, §1.3.4 / ADR-0004 D5.5). Read-back via -d cpu.
    ("X3 MemRAS invalid content (entry hi16=0) → 0x8B",
     words((3, 0x0001), (2, 0xFFFF), (0, 0x8000)) +   # rd18 = 0x0001_FFFF_0000_8000
     [rd2ra(0, 18, 1), ret_riii(0, 0),
      set_zw_rd(18, 0x0001), st_o_rd_pass()],
     RASUF_EXIT, "MemRAS invalid content didn't trigger RASUF"),

    # X4: MemRAS pop with entry hi16>1 → ra63 = (hi16-1)<<48|lo, PC = lo.
    # MemRAS[0] holds (hi16=2 | landing_addr) so the pop must store back a ra63
    # entry with refcount 1 and jump to the entry's low48 (the PASS sequence).
    # Layout: idx0-3 = entry value, idx4 = rd2ra(ra5), idx5 = st.o-ra to MemRAS[0],
    #         idx6-8 = ra0 value, idx9 = rd2ra(ra0), idx10 = ret,
    #         idx11 = PASS setup (landing = ROM 0xffff_ffff_0018 + 11*4 = 0x...0044)
    ("X4 MemRAS pop entry hi16>1 → ra63 store-back + PC=lo",
     words((3, 0x0002), (2, 0xFFFF), (1, 0xFFFF), (0, 0x0044)) +  # entry = 0x0002_FFFF_FFFF_0044
     [rd2ra(5, 18, 1),          # ra5 = entry
      st_o_ra(5, 17, 0x7F8),    # MemRAS[0] (RAM+0x7F8, fits imms12) = entry
     ] +
     words((3, 0x0001), (2, 0xFFFF), (0, 0x07F8)) +   # ra0 value: count=1, ptr=RAM+0x7F8
     [rd2ra(0, 18, 1),          # ra0 = MemRAS pointer/count
      ret_riii(0, 0),           # pop → ra63 = 0x0001_FFFF_FFFF_0044, PC = lo = 0x...0044
      ra2rd(18, 63, 1),         # read ra63 back (makes the store-back observable)
      set_zw_rd(20, 0x0044), or_w_rd(20, 1, 0xFFFF),
      or_w_rd(20, 2, 0xFFFF), or_w_rd(20, 3, 0x0001),   # rd20 = 0x0001_FFFF_FFFF_0044
      cmp_uo_rd(22, 18, 20), br_nz(22, 3),
      set_zw_rd(18, 0), st_o_rd_pass(),
      set_zw_rd(19, 0x0001), st_o_rd_fail()],
     PASS_EXIT, "MemRAS pop hi16>1 store-back wrong (ra63 mismatch)"),
]

# X3 precise-exception read-back: ra0 must be 0x0001_FFFF_0000_8000 at fault time
# (not the post-commit 0x0000_FFFF_0000_8008).
X3_RA0_EXPECT = 0x0001FFFF00008000

# ── CTL self-check ────────────────────────────────────────────────────

CTL_CHECKS = [
    ("CTL: st.o PASS but expect ILLI (wrong)",
     [set_zw_rd(18, 0), st_o_rd_pass()],
     ILLI_EXIT, "Self-check FAILED: probe cannot detect wrong values"),
    ("CTL: illi but expect PASS (wrong)",
     [illi()],
     PASS_EXIT, "Self-check FAILED: probe cannot detect ILLI"),
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
    print("QEMU-013t Min ROM Probe (RA instruction semantics)")
    print("=" * 70)

    print("-" * 70)
    print("Main tests:")
    print("-" * 70)
    passed, failed, fail_details = run_test_group(TESTS, "main")
    print(f"\nMain results: {passed}/{passed+failed} passed, {failed} failed")
    if fail_details:
        print("\nFailed:")
        for d in fail_details: print(d)

    # X3 precise-exception read-back: on RASUF (invalid MemRAS entry) ra0 must be
    # UNCHANGED (§1.3.4 / ADR-0004 D5.5). Exit code alone cannot show this.
    print("\n" + "-" * 70)
    print("X3 precise-exception read-back (ra0 unchanged at fault):")
    print("-" * 70)
    x3_insns = [i for i in TESTS if i[0].startswith("X3")][0][1]
    code, log = run_test_dcpu(build_rom(x3_insns))
    ra0 = last_ra_dump(log)
    if ra0 is None:
        print("  [FAIL] could not parse RA[00] from -d cpu dump")
        failed += 1
    elif ra0 == X3_RA0_EXPECT:
        print(f"  [PASS] ra0=0x{ra0:016X} (unchanged, expect 0x{X3_RA0_EXPECT:016X})")
    else:
        print(f"  [FAIL] ra0=0x{ra0:016X} (expect 0x{X3_RA0_EXPECT:016X}) — partial commit!")
        failed += 1

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
