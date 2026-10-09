#!/usr/bin/env python3
"""Min ROM probe for QEMU-008t Control Flow + RB instructions.

Architecture: test code runs from ROM (same as 005t/006t probe pattern).
Kernel binary provides test data (loaded at RAM base).

Tests cover:
- br.n/br.nn/br.z/br.nz/br.p/br.np rd: taken/not-taken
- br.eq/br.ne rd: taken/not-taken
- br.z/br.nz rb: taken/not-taken
- br.z rd0 special (always taken), br.nz rd0 special (never taken)
- jump-iiii: unconditional PC-relative
- call-iiii/call-rrii + ret: RegRAS push/pop round-trip
- ld.o-rb/st.o-rb: RB load/store
- rb2rd/rd2rb/rb2rb: register block copy
- add.o/sub.o/add.si-rb: RB arithmetic (full 64-bit)
- cmp.uo: RB unsigned comparison
- ILLI checks: rb0 dest for RB ops

Exit codes (ADR-0004 D5.8):
  0x00 = PASS, 0x88 = ILLI, 0x89 = UNDI, 0x8A = RASOF, 0x8B = RASUF

Usage: python3 tools/qemu/min_rom_probe_008t.py
"""

import struct
import subprocess
import sys
import os
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
    """add.o rbhb, rbhc, rdhd (MISC-octa, ha=0x30)"""
    return encode_orrr(0x40, 0x30, rbhb, rbhc, rdhd)

def sub_o_bbd(rbhb, rbhc, rdhd):
    """sub.o rbhb, rbhc, rdhd (MISC-octa, ha=0x31)"""
    return encode_orrr(0x40, 0x31, rbhb, rbhc, rdhd)

def cmp_uo_rd(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd (MISC-octa, ha=0x2A)"""
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def cmp_uo_dbb(rdhb, rbhc, rbhd):
    """cmp.uo rdhb, rbhc, rbhd (MISC-octa, ha=0x32)"""
    return encode_orrr(0x40, 0x32, rdhb, rbhc, rbhd)

def xor_o(rdhb, rdhc, rdhd):
    """xor.o rdhb, rdhc, rdhd (MISC-octa, ha=0x0A)"""
    return encode_orrr(0x40, 0x0A, rdhb, rdhc, rdhd)

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

def rb2rd(rdhb, rbhc, immu6):
    """rb2rd rdhb, rbhc, immu6 (MISC-octa, ha=0x36)"""
    return encode_orrr(0x40, 0x36, rdhb, rbhc, immu6)

def rd2rb(rbhb, rdhc, immu6):
    """rd2rb rbhb, rdhc, immu6 (MISC-octa, ha=0x35)"""
    return encode_orrr(0x40, 0x35, rbhb, rdhc, immu6)

def rb2rb(rbhb, rbhc, immu6):
    """rb2rb rbhb, rbhc, immu6 (MISC-octa, ha=0x34)"""
    return encode_orrr(0x40, 0x34, rbhb, rbhc, immu6)

def jump_iiii(imms24):
    """jump imms24 (op=0x70)"""
    return encode_iiii(0x70, imms24 & 0xFFFFFF)

def jump_rrii(rbha, rdhb, imms12):
    """jump rbha, rdhb, imms12 (op=0x71)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x71, rbha, rdhb, hc, hd)

def call_iiii(imms24):
    """call imms24 (op=0x74)"""
    return encode_iiii(0x74, imms24 & 0xFFFFFF)

def call_rrii(rbha, rdhb, imms12):
    """call rbha, rdhb, imms12 (op=0x75)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x75, rbha, rdhb, hc, hd)

def ret_riii(rdha, imms18):
    """ret rdha, imms18 (op=0x76)"""
    return encode_riii(0x76, rdha, imms18 & 0x3FFFF)

def br_n(rdha, imms18):
    """br.n rdha, imms18 (op=0x68)"""
    return encode_riii(0x68, rdha, imms18 & 0x3FFFF)

def br_nn(rdha, imms18):
    """br.nn rdha, imms18 (op=0x69)"""
    return encode_riii(0x69, rdha, imms18 & 0x3FFFF)

def br_z(rdha, imms18):
    """br.z rdha, imms18 (op=0x6A)"""
    return encode_riii(0x6A, rdha, imms18 & 0x3FFFF)

def br_nz(rdha, imms18):
    """br.nz rdha, imms18 (op=0x6B)"""
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)

def br_p(rdha, imms18):
    """br.p rdha, imms18 (op=0x6C)"""
    return encode_riii(0x6C, rdha, imms18 & 0x3FFFF)

def br_np(rdha, imms18):
    """br.np rdha, imms18 (op=0x6D)"""
    return encode_riii(0x6D, rdha, imms18 & 0x3FFFF)

def br_eq(rdha, rdhb, imms12):
    """br.eq rdha, rdhb, imms12 (op=0x6E)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x6E, rdha, rdhb, hc, hd)

def br_ne(rdha, rdhb, imms12):
    """br.ne rdha, rdhb, imms12 (op=0x6F)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x6F, rdha, rdhb, hc, hd)

def br_z_rb(rbha, imms18):
    """br.z-rb rbha, imms18 (op=0x72)"""
    return encode_riii(0x72, rbha, imms18 & 0x3FFFF)

def br_nz_rb(rbha, imms18):
    """br.nz-rb rbha, imms18 (op=0x73)"""
    return encode_riii(0x73, rbha, imms18 & 0x3FFFF)

def fence():
    return encode_oiii(0x77, 0x00, 0)

def swym():
    return encode_oiii(0x77, 0x22, 0)

def trap_sys_exit():
    """trap cfx_umon, 0x30000 — semihosting tag (immu18[17:16]==2'b11)."""
    return encode_oiii(0x7F, 0x00, SEMIHOST_TAG)

# ── Semihosting SYS_EXIT (ADR-0020 D8: exit port removed) ──────────────
# Trampoline sets rb16 = SEMI_BLOCK, writes block[0] = 0x20026 and sets
# rd16 = 0x18 (SYS_EXIT).  Each terminal writes the code into block[1] and traps.

SEMI_BLOCK = 0x0000_00FF_F000       # {reason, code} block inside RAM@0 (16 MiB)
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap

def semi_exit(code_rd):
    """store code_rd into SEMI_BLOCK[1] then `trap` (SYS_EXIT); +1 insn."""
    return [st_o_rd(code_rd, 16, 8), trap_sys_exit()]

# ── Terminators ───────────────────────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

# ── ROM builder ───────────────────────────────────────────────────────

def build_rom(test_insns):
    """Build ROM: [trampoline | test_insns | UNDI | padding].

    Trampoline sets rb1=SP, rb2=rb17=RAM@0 base, and primes the semihosting
    SYS_EXIT argument block (ADR-0020 D8)."""
    trampoline = [
        encode_rwii(0x4E, 1, 0, 0x0000),   # set.zw rb1, wp0, 0x0000 -> rb1 = 0
        encode_rwii(0x4A, 1, 1, 0x00FF),   # or.w rb1, wp1, 0x00FF -> rb1 = 0x00FF0000 (SP)
        encode_rwii(0x4E, 2, 0, 0x0000),   # set.zw rb2, wp0, 0x0000 -> rb2 = 0 (RAM base)
        encode_rwii(0x4E, 16, 0, 0x0000),  # set.zw rb16, wp0, 0x0000 -> rb16 = 0
        encode_rwii(0x4A, 16, 1, 0x00FF),  # or.w rb16, wp1, 0x00FF -> rb16 = 0x00FF0000
        encode_rwii(0x4A, 16, 0, 0xF000),  # or.w rb16, wp0, 0xF000 -> rb16 = 0x00FFF000 (block)
        encode_rwii(0x4C, 8, 0, 0x0026),   # set.zw rd8, wp0, 0x0026
        encode_rwii(0x48, 8, 1, 0x0002),   # or.w rd8, wp1, 0x0002 -> rd8 = 0x20026
        st_o_rd(8, 16, 0),                 # block[0] = 0x20026
        encode_rwii(0x4C, 16, 0, 0x0018),  # set.zw rd16, wp0, 0x0018 (SYS_EXIT)
        encode_rwii(0x4E, 17, 0, 0x0000),  # set.zw rb17, wp0, 0x0000 -> rb17 = 0 (RAM base)
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
    encode_rwii(0x4E, 18, 0, 0x0000),  # set.zw rb18, wp0, 0x0000
    encode_rwii(0x4A, 18, 0, 0x0100),  # or.w rb18, wp0, 0x0100 → RAM@0 + 0x100
]

# ── Test cases ────────────────────────────────────────────────────────
# After trampoline: rb16=SYS_EXIT argument block, rb17=rb2=RAM@0 base

TESTS = [
    # ── Branch taken/not-taken tests ──────────────────────────────────

    # T1: br.z rd0 → always taken (§5.2.2 special case)
    ("T1 br.z rd0 → always taken",
     [br_z(0, 4),               # br.z rd0, +3 → always taken (rd0=0)
      set_zw_rd(18, 0x0001),    # skipped: FAIL
      *semi_exit(18),       # skipped: FAIL
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.z rd0 not always taken"),

    # T2: br.nz rd0 → never taken (§5.2.2 special case)
    ("T2 br.nz rd0 → never taken",
     [br_nz(0, 4),              # br.nz rd0, +3 → never taken (rd0=0)
      set_zw_rd(18, 0x0000),    # fall through: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.nz rd0 not never taken"),

    # T3: br.nz rd!=0 taken
    ("T3 br.nz rd!=0 taken",
     [set_zw_rd(18, 0x0001),    # rd18 = 1
      br_nz(18, 4),             # br.nz rd18, +3 → taken
      set_zw_rd(19, 0x0001),    # skipped: FAIL
      *semi_exit(19),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.nz taken failed"),

    # T4: br.z rd!=0 not taken
    ("T4 br.z rd!=0 not taken",
     [set_zw_rd(18, 0x0001),    # rd18 = 1
      br_z(18, 4),              # br.z rd18, +3 → not taken (rd18!=0)
      set_zw_rd(18, 0x0000),    # fall through: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.z not-taken failed"),

    # T5: br.n negative taken
    ("T5 br.n negative taken",
     [set_zw_rd(18, 0x0001),    # rd18 = 1
      add_si_rd(18, -1),        # rd18 = 0 (but we need negative)
      # Actually: set.ow to get -1
      encode_rwii(0x4D, 18, 0, 0xFFFF),  # set.ow rd18, wp0, 0xFFFF → rd18=-1
      br_n(18, 4),              # br.n rd18, +3 → taken (negative)
      set_zw_rd(18, 0x0001),    # skipped: FAIL
      *semi_exit(18),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.n negative taken failed"),

    # T6: br.nn non-negative taken
    ("T6 br.nn non-negative taken",
     [set_zw_rd(18, 0x0001),    # rd18 = 1 (positive)
      br_nn(18, 4),             # br.nn rd18, +3 → taken
      set_zw_rd(18, 0x0001),    # skipped: FAIL
      *semi_exit(18),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.nn positive taken failed"),

    # T7: br.p positive taken
    ("T7 br.p positive taken",
     [set_zw_rd(18, 0x0001),    # rd18 = 1 (positive)
      br_p(18, 4),              # br.p rd18, +3 → taken
      set_zw_rd(18, 0x0001),    # skipped: FAIL
      *semi_exit(18),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.p positive taken failed"),

    # T8: br.np non-positive taken (zero)
    ("T8 br.np zero taken",
     [set_zw_rd(18, 0x0000),    # rd18 = 0
      br_np(18, 4),             # br.np rd18, +3 → taken (zero is non-positive)
      set_zw_rd(18, 0x0001),    # skipped: FAIL
      *semi_exit(18),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.np zero taken failed"),

    # T9: br.eq equal taken
    ("T9 br.eq equal taken",
     [set_zw_rd(18, 0x0042),    # rd18 = 0x42
      set_zw_rd(19, 0x0042),    # rd19 = 0x42
      br_eq(18, 19, 4),         # br.eq rd18, rd19, +3 → taken
      set_zw_rd(20, 0x0001),    # skipped: FAIL
      *semi_exit(20),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.eq equal taken failed"),

    # T10: br.ne not-equal taken
    ("T10 br.ne not-equal taken",
     [set_zw_rd(18, 0x0042),    # rd18 = 0x42
      set_zw_rd(19, 0x0043),    # rd19 = 0x43
      br_ne(18, 19, 4),         # br.ne rd18, rd19, +3 → taken
      set_zw_rd(20, 0x0001),    # skipped: FAIL
      *semi_exit(20),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.ne not-equal taken failed"),

    # T11: br.z-rb rb!=0 not taken
    ("T11 br.z-rb rb!=0 not taken",
     SETUP_RB18 + [
      br_z_rb(18, 4),           # br.z-rb rb18, +3 → not taken (rb18!=0)
      set_zw_rd(18, 0x0000),    # fall through: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.z-rb rb!=0 not-taken failed"),

    # T12: br.nz-rb rb!=0 taken
    ("T12 br.nz-rb rb!=0 taken",
     SETUP_RB18 + [
      br_nz_rb(18, 4),          # br.nz-rb rb18, +3 → taken
      set_zw_rd(18, 0x0001),    # skipped: FAIL
      *semi_exit(18),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "br.nz-rb rb!=0 taken failed"),

    # ── jump-iiii test ────────────────────────────────────────────────

    # T13: jump-iiii forward
    ("T13 jump-iiii forward",
     [jump_iiii(4),              # jump +4 → skip fail arm (offset +1 terminal)
      set_zw_rd(18, 0x0001),    # skipped: FAIL
      *semi_exit(18),
      set_zw_rd(18, 0x0000),    # landed: PASS
      *semi_exit(18)],
     PASS_EXIT,
     "jump-iiii forward failed"),

    # ── call/ret round-trip ───────────────────────────────────────────

    # T14: call-iiii + ret → RegRAS push/pop
    # call pushes return address (PC+4), jumps to target
    # target: ret rd0, 0 → pops return address, jumps back
    # After ret, fall through to PASS
    ("T14 call-iiii + ret round-trip",
     [call_iiii(4),              # call +3 → push ret_addr, jump to target
      set_zw_rd(18, 0x0000),    # return here: PASS
      *semi_exit(18),       # exit PASS
      # target (at +3):
      ret_riii(0, 0)],          # ret rd0, 0 → pop, jump back to after call
     PASS_EXIT,
     "call+ret round-trip failed"),

    # T15: call-rrii + ret
    # call-rrii: PC = rbha + rdhb + (imms12 << 2)
    # Use rb0 (PC) as base: call rb0, rd0, +3 → PC = PC + (3<<2) = PC+12
    # That's 3 instructions ahead: call(0), set_zw(1), st_o(2), target at (3)
    ("T15 call-rrii + ret round-trip",
     [call_rrii(0, 0, 4),       # call rb0, rd0, +4 → PC = PC+16, push ret
      set_zw_rd(18, 0x0000),    # return here: PASS
      *semi_exit(18),       # exit PASS
      # target (at +3 instructions from call = PC+12):
      ret_riii(0, 0)],          # ret → pop, jump back
     PASS_EXIT,
     "call-rrii+ret round-trip failed"),

    # T16: Nested call/ret (2 levels) — exercises RegRAS shift-down/shift-up
    # Flow: main → func1 → func2 → func2 ret → func1 ret → main ret
    # func1 call pushes ret(main+1), func2 call pushes ret(func1+1)
    # This exercises §5.6.1 case 3 (shift down) and §5.6.2 case 2 (shift up).
    ("T16 Nested call/ret (2 levels)",
     [call_iiii(4),              # call func1 (target = idx 3), push ret(idx 1)
      set_zw_rd(18, 0x0000),    # main return: PASS
      *semi_exit(18),
      # func1 (at idx 3):
      call_iiii(2),              # call func2 (target = next ret, +1 terminal below)
      ret_riii(0, 0),            # func1 return (pops to idx 1)
      # func2 (at idx 5):
      ret_riii(0, 0)],           # func2 return (pops to idx 4)
     PASS_EXIT,
     "Nested call/ret failed"),

    # ── RB load/store tests ───────────────────────────────────────────

    # T18: st.o-rb + ld.o-rb round-trip
    ("T18 st.o-rb + ld.o-rb round-trip",
     SETUP_RB18 + [
      set_zw_rb(19, 0x0042),    # rb19 = 0x42
      st_o_rb(19, 17, 0),       # st.o-rb rb19, rb17, 0 → store to RAM base
      ld_o_rb(20, 17, 0),       # ld.o-rb rb20, rb17, 0 → load back
      rb2rd(21, 20, 1),         # rb2rd rd21, rb20, 1 → copy to rd for comparison
      set_zw_rd(22, 0x0042),    # expected = 0x42
      cmp_uo_rd(23, 21, 22),    # cmp.uo rd23, rd21, rd22
      set_zw_rd(24, 0x0000),    # if equal (0), PASS
      br_ne(23, 24, 2),         # br.ne rd23, rd24, +2 → if not equal, skip to FAIL
      set_zw_rd(18, 0x0000),    # PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "st.o-rb/ld.o-rb round-trip mismatch"),

    # T19: ld.o-rb rb0 → ILLI
    ("T19 ld.o-rb rb0 → ILLI",
     [ld_o_rb(0, 17, 0)],
     ILLI_EXIT,
     "ld.o-rb rb0 not ILLI"),

    # T20: st.o-rb rb0 → ILLI
    # NOTE (ISS-120 drift): contract-isa §1.3.2 (ADR-0015 D3) — for st.o/stm.o
    # the `rbha` field is a data SOURCE; rb0 reads as the current instruction
    # address and is LEGAL.  (Only ld.o/ldm.o destination rb0 is ILLI.)
    ("T20 st.o-rb rb0 (source reads PC, legal)",
     [set_zw_rb(19, 0x0042),
      st_o_rb(0, 17, 0x40),      # store rb0 (PC) to RAM+0x40 — legal
      set_zw_rd(18, 0x0000),
      *semi_exit(18)],
     PASS_EXIT,
     "st.o-rb rb0 source should be legal"),

    # ── RB block copy tests ───────────────────────────────────────────

    # T21: rb2rd round-trip
    ("T21 rb2rd round-trip",
     [set_zw_rb(19, 0x0099),    # rb19 = 0x99
      rb2rd(20, 19, 1),         # rb2rd rd20, rb19, 1
      set_zw_rd(21, 0x0099),    # expected = 0x99
      cmp_uo_rd(22, 20, 21),    # cmp.uo rd22, rd20, rd21
      set_zw_rd(23, 0x0000),
      br_ne(22, 23, 4),         # if not equal, skip 3 → FAIL path
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "rb2rd round-trip mismatch"),

    # T22: rd2rb + rb2rd round-trip
    ("T22 rd2rb + rb2rd round-trip",
     [set_zw_rd(19, 0x00AB),    # rd19 = 0xAB
      rd2rb(20, 19, 1),         # rd2rb rb20, rd19, 1
      rb2rd(21, 20, 1),         # rb2rd rd21, rb20, 1
      cmp_uo_rd(22, 21, 19),    # cmp.uo rd22, rd21, rd19
      set_zw_rd(23, 0x0000),
      br_ne(22, 23, 4),         # if not equal, skip 3 → FAIL path
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "rd2rb+rb2rd round-trip mismatch"),

    # T23: rb2rb round-trip
    ("T23 rb2rb round-trip",
     [set_zw_rb(19, 0x00CD),    # rb19 = 0xCD
      rb2rb(20, 19, 1),         # rb2rb rb20, rb19, 1
      rb2rd(21, 20, 1),         # rb2rd rd21, rb20, 1
      set_zw_rd(22, 0x00CD),    # expected = 0xCD
      cmp_uo_rd(23, 21, 22),
      set_zw_rd(24, 0x0000),
      br_ne(23, 24, 4),         # if not equal, skip 3 → FAIL path
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "rb2rb round-trip mismatch"),

    # T24: rb2rb rb0 dest → ILLI
    ("T24 rb2rb rb0 dest → ILLI",
     [rb2rb(0, 19, 1)],
     ILLI_EXIT,
     "rb2rb rb0 dest not ILLI"),

    # T25: rd2rb rb0 dest → ILLI
    ("T25 rd2rb rb0 dest → ILLI",
     [set_zw_rd(19, 0x0042),
      rd2rb(0, 19, 1)],
     ILLI_EXIT,
     "rd2rb rb0 dest not ILLI"),

    # T26: rb2rd rd0 dest → ILLI
    ("T26 rb2rd rd0 dest → ILLI",
     [rb2rd(0, 19, 1)],
     ILLI_EXIT,
     "rb2rd rd0 dest not ILLI"),

    # ── RB arithmetic tests ───────────────────────────────────────────

    # T27: add.o full 64-bit (high bits preserved)
    # Uses cmp.uo to verify full 64-bit result (not rb2rd → cmp.uo-rd
    # which may mask high bits). If add.o truncates to 48 bits, this
    # test will FAIL because the comparison checks bits[63:48].
    ("T27 add.o full 64-bit",
     [set_zw_rb(19, 0x0010),    # rb19 = 0x10
      encode_rwii(0x4A, 19, 3, 0x1234),  # or.w rb19, wp3, 0x1234 → rb19=0x1234_0000_0000_0010
      set_zw_rd(20, 0x0020),    # rd20 = 0x20
      add_o_bbd(21, 19, 20),    # rb21 = rb19 + rd20 = 0x1234_0000_0000_0030
      # Expected: rb22 = 0x1234_0000_0000_0030
      set_zw_rb(22, 0x0030),    # rb22 = 0x30
      encode_rwii(0x4A, 22, 3, 0x1234),  # or.w rb22, wp3, 0x1234 → rb22=0x1234_0000_0000_0030
      cmp_uo_dbb(23, 21, 22),    # cmp.uo rd23, rb21, rb22 (full 64-bit compare)
      set_zw_rd(24, 0x0000),    # expected = 0 (equal)
      br_ne(23, 24, 4),         # if not equal, skip 3 → FAIL path
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "add.o full 64-bit wrong (truncated?)"),

    # T28: sub.o full 64-bit
    # Uses cmp.uo for full 64-bit verification.
    ("T28 sub.o full 64-bit",
     [set_zw_rb(19, 0x0050),    # rb19 = 0x50
      set_zw_rd(20, 0x0020),    # rd20 = 0x20
      sub_o_bbd(21, 19, 20),    # rb21 = rb19 - rd20 = 0x30
      set_zw_rb(22, 0x0030),    # expected rb22 = 0x30
      cmp_uo_dbb(23, 21, 22),    # cmp.uo rd23, rb21, rb22
      set_zw_rd(24, 0x0000),
      br_ne(23, 24, 4),         # if not equal, skip 3 → FAIL
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "sub.o wrong"),

    # T29: add.si-rb full 64-bit
    # Uses cmp.uo for full 64-bit verification.
    ("T29 add.si-rb full 64-bit",
     [set_zw_rb(19, 0x0010),    # rb19 = 0x10
      add_si_rb(19, 5),         # rb19 += 5 → 0x15
      set_zw_rb(20, 0x0015),    # expected rb20 = 0x15
      cmp_uo_dbb(21, 19, 20),    # cmp.uo rd21, rb19, rb20
      set_zw_rd(22, 0x0000),
      br_ne(21, 22, 4),         # if not equal, skip to FAIL (offset +1 terminal)
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "add.si-rb wrong"),

    # T30: add.o rb0 dest → ILLI
    ("T30 add.o rb0 dest → ILLI",
     [set_zw_rd(20, 0x0010),
      add_o_bbd(0, 19, 20)],
     ILLI_EXIT,
     "add.o rb0 dest not ILLI"),

    # T31: sub.o rb0 dest → ILLI
    ("T31 sub.o rb0 dest → ILLI",
     [set_zw_rd(20, 0x0010),
      sub_o_bbd(0, 19, 20)],
     ILLI_EXIT,
     "sub.o rb0 dest not ILLI"),

    # T32: add.si-rb rb0 dest → ILLI
    ("T32 add.si-rb rb0 dest → ILLI",
     [add_si_rb(0, 5)],
     ILLI_EXIT,
     "add.si-rb rb0 dest not ILLI"),

    # ── cmp.uo test ────────────────────────────────────────────────

    # T33: cmp.uo equal → 0
    ("T33 cmp.uo equal → 0",
     [set_zw_rb(19, 0x0042),    # rb19 = 0x42
      set_zw_rb(20, 0x0042),    # rb20 = 0x42
      cmp_uo_dbb(21, 19, 20),    # rd21 = cmp(rb19, rb20) = 0
      set_zw_rd(22, 0x0000),    # expected = 0
      cmp_uo_rd(23, 21, 22),
      set_zw_rd(24, 0x0000),
      br_ne(23, 24, 4),         # if not equal, skip 3 → FAIL
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "cmp.uo equal not 0"),

    # T34: cmp.uo less → -1
    # cmp.uo returns -1/0/1 as 64-bit signed values
    # -1 = 0xFFFFFFFFFFFFFFFF, 0 = 0, 1 = 1
    # To check -1: result != 0 AND result != 1
    ("T34 cmp.uo less → -1",
     [set_zw_rb(19, 0x0010),    # rb19 = 0x10
      set_zw_rb(20, 0x0020),    # rb20 = 0x20
      cmp_uo_dbb(21, 19, 20),    # rd21 = cmp(0x10, 0x20) = -1
      # Check rd21 != 0
      set_zw_rd(22, 0x0000),    # zero
      cmp_uo_rd(23, 21, 22),    # cmp(rd21, 0) → 0 if rd21==0, else !=0
      br_ne(23, 22, 4),         # if cmp!=0 (rd21!=0), skip to next check (+1 terminal)
      set_zw_rd(18, 0x0001),    # rd21 was 0 → FAIL
      *semi_exit(18),
      # Check rd21 != 1
      set_zw_rd(24, 0x0001),    # one
      cmp_uo_rd(25, 21, 24),    # cmp(rd21, 1) → 0 if rd21==1, else !=0
      br_ne(25, 22, 4),         # if cmp!=0 (rd21!=1), skip to PASS (+1 terminal)
      set_zw_rd(18, 0x0001),    # rd21 was 1 → FAIL
      *semi_exit(18),
      # rd21 is neither 0 nor 1, so it must be -1 → PASS
      set_zw_rd(18, 0x0000),
      *semi_exit(18)],
     PASS_EXIT,
     "cmp.uo less not -1"),

    # T35: cmp.uo greater → 1
    ("T35 cmp.uo greater → 1",
     [set_zw_rb(19, 0x0030),    # rb19 = 0x30
      set_zw_rb(20, 0x0010),    # rb20 = 0x10
      cmp_uo_dbb(21, 19, 20),    # rd21 = cmp(0x30, 0x10) = 1
      set_zw_rd(22, 0x0001),    # expected = 1
      cmp_uo_rd(23, 21, 22),
      set_zw_rd(24, 0x0000),
      br_ne(23, 24, 4),         # if not equal, skip 3 → FAIL
      set_zw_rd(18, 0x0000),    # equal: PASS
      *semi_exit(18),
      set_zw_rd(18, 0x0001),    # not-equal: FAIL
      *semi_exit(18)],
     PASS_EXIT,
     "cmp.uo greater not 1"),

    # T36: cmp.uo rdhb=0 → ILLI
    ("T36 cmp.uo rd0 dest → ILLI",
     [set_zw_rb(19, 0x0010),
      set_zw_rb(20, 0x0020),
      cmp_uo_dbb(0, 19, 20)],
     ILLI_EXIT,
     "cmp.uo rd0 dest not ILLI"),

    # ── RASUF test ────────────────────────────────────────────────────

    # T37: ret with empty RAS → RASUF
    ("T37 ret empty RAS → RASUF",
     [ret_riii(0, 0)],          # ret with empty stack → RASUF
     RASUF_EXIT,
     "ret empty RAS not RASUF"),

    # ── RASOF test ─────────────────────────────────────────────────────

    # T38: Deep call chain → RASOF (64 calls fill all 63 ra slots, 64th overflows)
    # Each call_i pushes ret(i+1) and jumps to the next call.
    # After 63 calls, ra1-ra63 are all valid. The 64th call checks ra1,
    # finds it valid → RASOF (§5.6.1 case 3, §9).
    # Uses RegRAS shift-down (F1 fix) to propagate entries to ra1.
    ("T38 deep call → RASOF",
     [call_iiii(1)] * 64 +      # 64 chained calls (64th triggers RASOF)
     [set_zw_rd(18, 0x0001),    # if RASOF didn't trigger → FAIL
      *semi_exit(18)],
     RASOF_EXIT,
     "deep call not RASOF"),
]

# ── CTL self-check ────────────────────────────────────────────────────

CTL_CHECKS = [
    ("CTL: st.o PASS but expect ILLI (wrong)",
     [set_zw_rd(18, 0x0000), *semi_exit(18)],
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect wrong values"),
    ("CTL: br.nz rd0 never-taken but expect taken (wrong)",
     [br_nz(0, 4),              # never taken
      set_zw_rd(18, 0x0000),    # fall through: PASS
      *semi_exit(18)],
     ILLI_EXIT,                  # wrong expectation
     "Self-check FAILED: probe cannot detect br.nz rd0 behavior"),
    ("CTL: ILLI but expect PASS (wrong)",
     [fence()],
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
    print("QEMU-008t Min ROM Probe (Control Flow + RB instructions)")
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
