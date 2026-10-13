#!/usr/bin/env python3
"""Min ROM probe for SPEC-066t: div/rem defined-value semantics (v2).

Covers 16 div.* + 16 rem.* tests across all sizes (byte/wyde/tetra/octa)
and signedness (u/s), plus comprehensive div/rem edge cases per SPEC-066t.

Key change from v1: div-by-zero and signed overflow (INT_MIN÷-1) no longer
trigger ILLI; they produce defined values instead.  The exact-value comparison
mechanism is updated from div-by-zero-based to br.ne-based.

Test categories:
  N1-N6: Normal exact value (truncate-toward-zero) — unchanged
  D0-D7: Divide-by-zero → defined value (was ILLI, now checks result)
  O0-O3: INT_MIN÷-1 → defined value (was ILLI, now checks result)
  R1-R6: Normal exact value for rem — unchanged
  RD0-RD7: Remainder-by-zero → dividend (extended)
  RO0-RO3: INT_MIN%-1 → 0
  E0-E15: Encoding tests (rdhd=rd0, all 16 div/rem variants)

Exit codes: ILLI=136(0x88), UNDI=137(0x89), CRASH=134

Value comparison method (br.ne-based, v2):
  1. Compute result via div/rem
  2. Load expected value
  3. cmp.uo rd_cmp, result, expected → rd_cmp=0 if equal, ±1 if not
  4. set.zw rd_zero, 0
  5. br.ne rd_cmp, rd_zero, 2 → if mismatch (rd_cmp!=0), skip 2 → fence → 136
  6. set.zw rd1, 1; br.ne rd1, rd0, 2 → unconditional: skip fence → UNDI(137)
  7. fence → exit 136 (mismatch path)
  So: UNDI(137) = PASS (match), ILLI(136) = FAIL (mismatch).

Usage: python3 tools/qemu/min_rom_probe_011t.py
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

# ── Instruction encoding helpers ──────────────────────────────────────

def encode_orrr(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_riii(op, ha, imms18):
    imm = imms18 & 0x3FFFF
    return struct.pack('>I', (op << 24) | (ha << 18) | imm)

def encode_oiii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)

def set_zw_wp3(rd, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (3 << 4) | hi4
    return struct.pack('>I', (0x4C << 24) | (rd << 18) | (hb << 12) | (mid6 << 6) | lo6)

def or_w(rd, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (0x48 << 24) | (rd << 18) | (hb << 12) | (mid6 << 6) | lo6)

def add_si(rd, imms18):
    return encode_riii(0x59, rd, imms18 & 0x3FFFF)

# div/rem encoding (from opcodes.yaml)
# MISC-octa: op=0x40, MISC-tetra: op=0x41, MISC-wyde: op=0x42, MISC-byte: op=0x43
# ha: div.u=0x38, div.s=0x39, rem.u=0x3A, rem.s=0x3B

def div_uo(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x38, rdhb, rdhc, rdhd)
def div_so(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x39, rdhb, rdhc, rdhd)
def rem_uo(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x3A, rdhb, rdhc, rdhd)
def rem_so(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x3B, rdhb, rdhc, rdhd)
def div_ut(rdhb, rdhc, rdhd): return encode_orrr(0x41, 0x38, rdhb, rdhc, rdhd)
def div_st(rdhb, rdhc, rdhd): return encode_orrr(0x41, 0x39, rdhb, rdhc, rdhd)
def rem_ut(rdhb, rdhc, rdhd): return encode_orrr(0x41, 0x3A, rdhb, rdhc, rdhd)
def rem_st(rdhb, rdhc, rdhd): return encode_orrr(0x41, 0x3B, rdhb, rdhc, rdhd)
def div_uw(rdhb, rdhc, rdhd): return encode_orrr(0x42, 0x38, rdhb, rdhc, rdhd)
def div_sw(rdhb, rdhc, rdhd): return encode_orrr(0x42, 0x39, rdhb, rdhc, rdhd)
def rem_uw(rdhb, rdhc, rdhd): return encode_orrr(0x42, 0x3A, rdhb, rdhc, rdhd)
def rem_sw(rdhb, rdhc, rdhd): return encode_orrr(0x42, 0x3B, rdhb, rdhc, rdhd)
def div_ub(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x38, rdhb, rdhc, rdhd)
def div_sb(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x39, rdhb, rdhc, rdhd)
def rem_ub(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x3A, rdhb, rdhc, rdhd)
def rem_sb(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x3B, rdhb, rdhc, rdhd)

def cmp_uo(rdhb, rdhc, rdhd):
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def rb2rd(rdhb, rbhc, immu6):
    return encode_orrr(0x40, 0x36, rdhb, rbhc, immu6)

def rd2rb(rbhb, rdhc, immu6):
    return encode_orrr(0x40, 0x35, rbhb, rdhc, immu6)

def br_ne(rdha, rdhb, imms12):
    """br.ne rdha, rdhb, imms12 (op=0x6F, rrii format)
    Offset in units of instructions (4 bytes)."""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_orrr(0x6F, rdha, rdhb, hc, hd)

def fence():
    return encode_oiii(0x77, 0x00, 0)

# ── Terminators / ROM ────────────────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

def build_rom(instructions):
    """Build ROM: instructions + UNDI + fence padding to 64 bytes."""
    rom = b''
    for insn in instructions:
        rom += insn
    rom += UNDI_TERMINATOR
    while len(rom) < 64:
        rom += fence()
    return rom

def run_rom(rom_data, kernel_data=None, timeout=10):
    if kernel_data is None:
        kernel_data = fence() * 4
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rom_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False, dir=_probe_artifact_dir()) as f:
        f.write(kernel_data)
        kernel_path = f.name
    try:
        result = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic',
             '-bios', rom_path, '-kernel', kernel_path],
            capture_output=True, timeout=timeout, text=True)
        return result.returncode, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rom_path)
        os.unlink(kernel_path)

ILLI_EXIT = 136
UNDI_EXIT = 137
CRASH_EXIT = 134

# ── Helpers ───────────────────────────────────────────────────────────

def _set_rd_to_val(insns, rd, val):
    """Set rd to a 64-bit value using set.zw + or.w."""
    val64 = val & 0xFFFFFFFFFFFFFFFF
    wp0 = val64 & 0xFFFF
    wp1 = (val64 >> 16) & 0xFFFF
    wp2 = (val64 >> 32) & 0xFFFF
    wp3 = (val64 >> 48) & 0xFFFF
    if val64 == 0:
        insns.append(set_zw(rd, 0))
    elif wp1 == 0 and wp2 == 0 and wp3 == 0:
        insns.append(set_zw(rd, wp0))
    elif wp0 == 0 and wp2 == 0 and wp3 == 0:
        insns.append(set_zw(rd, 0))
        insns.append(or_w(rd, 1, wp1))
    elif wp0 == 0 and wp1 == 0 and wp3 == 0:
        insns.append(set_zw(rd, 0))
        insns.append(or_w(rd, 2, wp2))
    elif wp0 == 0 and wp1 == 0 and wp2 == 0:
        insns.append(set_zw_wp3(rd, wp3))
    else:
        insns.append(set_zw_wp3(rd, wp3))
        if wp2 != 0: insns.append(or_w(rd, 2, wp2))
        if wp1 != 0: insns.append(or_w(rd, 1, wp1))
        if wp0 != 0: insns.append(or_w(rd, 0, wp0))

def _exact_cmp(insns, rd_result, rd_expected, val_expected):
    """Exact-value comparison (br.ne-based). Appends to insns:
    [..]  set.zw rd_expected, val_expected
    [K]   cmp.uo rd_cmp, rd_result, rd_expected
    [K+1] set.zw rd_zero, 0
    [K+2] br.ne rd_cmp, rd_zero, 2   # mismatch → skip 2 → cmp.uo(0,0,0) → ILLI
    [K+3] set.zw rd1, 1              # match: prep unconditional skip
    [K+4] br.ne rd1, rd0, 1          # unconditional → skip 1 → UNDI(137)
    [K+5] cmp.uo(0, 0, 0)            # mismatch target → rdhb=0 → ILLI(136)
    → UNDI terminator

    Match:   cmp=0 → br.ne NOT taken → set.zw(1,1) → br.ne TAKEN → UNDI(137)
    Mismatch: cmp≠0 → br.ne TAKEN → cmp.uo(0,0,0) → ILLI(136)

    Exit: UNDI(137) = PASS, ILLI(136) = FAIL."""
    _set_rd_to_val(insns, rd_expected, val_expected)
    insns.append(cmp_uo(7, rd_result, rd_expected))
    insns.append(set_zw(1, 0))
    insns.append(br_ne(7, 1, 2))        # mismatch → skip 2 → cmp.uo(0,0,0)
    insns.append(set_zw(1, 1))          # match: rd1=1
    insns.append(br_ne(1, 0, 2))        # unconditional → skip 2 → UNDI
    insns.append(cmp_uo(0, 0, 0))       # mismatch target → rdhb=0 → ILLI

# ── Test case constructors ────────────────────────────────────────────

def _exact_div_test(name, div_fn, dividend, divisor, expected, size_desc):
    insns = []
    _set_rd_to_val(insns, 10, dividend)
    _set_rd_to_val(insns, 11, divisor)
    insns.append(div_fn(5, 10, 11))
    _exact_cmp(insns, 5, 6, expected)
    return (name, insns, UNDI_EXIT, f"{size_desc} {dividend}/{divisor} != {expected}")

def _exact_rem_test(name, rem_fn, dividend, divisor, expected, size_desc):
    insns = []
    _set_rd_to_val(insns, 10, dividend)
    _set_rd_to_val(insns, 11, divisor)
    insns.append(rem_fn(5, 10, 11))
    _exact_cmp(insns, 5, 6, expected)
    return (name, insns, UNDI_EXIT, f"{size_desc} {dividend}%{divisor} != {expected}")

def _div_by_zero_test(name, div_fn, expected_val, size_desc):
    insns = []
    _set_rd_to_val(insns, 10, 0x64)
    insns.append(set_zw(11, 0))
    insns.append(div_fn(1, 10, 11))
    _exact_cmp(insns, 1, 6, expected_val)
    return (name, insns, UNDI_EXIT, f"{size_desc} div-by-zero != {hex(expected_val)}")

def _rem_by_zero_test(name, rem_fn, expected_val, size_desc):
    insns = []
    _set_rd_to_val(insns, 10, 0x64)
    insns.append(set_zw(11, 0))
    insns.append(rem_fn(1, 10, 11))
    _exact_cmp(insns, 1, 6, expected_val)
    return (name, insns, UNDI_EXIT, f"{size_desc} rem-by-zero != {hex(expected_val)}")

def _int_min_div_neg1_test(name, div_fn, int_min_val, expected_val, size_desc):
    """INT_MIN÷-1 overflow test with readback verification."""
    insns = []
    _set_rd_to_val(insns, 10, int_min_val)
    # Readback verification
    insns.append(rd2rb(18, 10, 1))
    insns.append(rb2rd(20, 18, 1))
    _set_rd_to_val(insns, 21, int_min_val)
    insns.append(cmp_uo(22, 20, 21))
    insns.append(set_zw(23, 0))
    insns.append(br_ne(22, 23, 2))       # readback mismatch → skip 2 → cmp.uo(0,0,0)
    insns.append(set_zw(1, 1))           # readback OK
    insns.append(br_ne(1, 0, 2))         # unconditional skip → UNDI
    insns.append(cmp_uo(0, 0, 0))        # readback mismatch target → ILLI
    # Real overflow test
    insns.append(set_zw(11, 0))
    insns.append(add_si(11, -1))
    insns.append(div_fn(1, 10, 11))
    _exact_cmp(insns, 1, 6, expected_val)
    return (name, insns, UNDI_EXIT, f"{size_desc} INT_MIN/-1 != {hex(expected_val)}")

def _int_min_rem_neg1_test(name, rem_fn, int_min_val, expected_val, size_desc):
    """INT_MIN%-1 overflow test with readback verification."""
    insns = []
    _set_rd_to_val(insns, 10, int_min_val)
    insns.append(rd2rb(18, 10, 1))
    insns.append(rb2rd(20, 18, 1))
    _set_rd_to_val(insns, 21, int_min_val)
    insns.append(cmp_uo(22, 20, 21))
    insns.append(set_zw(23, 0))
    insns.append(br_ne(22, 23, 2))
    insns.append(set_zw(1, 1))
    insns.append(br_ne(1, 0, 2))
    insns.append(cmp_uo(0, 0, 0))
    insns.append(set_zw(11, 0))
    insns.append(add_si(11, -1))
    insns.append(rem_fn(1, 10, 11))
    _exact_cmp(insns, 1, 6, expected_val)
    return (name, insns, UNDI_EXIT, f"{size_desc} INT_MIN/-1 rem != {hex(expected_val)}")

def _encoding_rdhd_rd0_test(name, insn_bytes, size_desc):
    """Encoding test: rdhd=rd0 should not fault → UNDI(137)."""
    return (name, list(insn_bytes), UNDI_EXIT,
            f"{size_desc} rdhd=rd0 encoding rejected")

# ── Test cases ────────────────────────────────────────────────────────

TESTS = [
    # Normal exact value
    _exact_div_test("N1 div.uo 100/7 == 14", div_uo, 100, 7, 14, "div.uo"),
    _exact_div_test("N2 div.ut 100/7 == 14 (32-bit)", div_ut, 100, 7, 14, "div.ut"),
    _exact_div_test("N3 div.uw 100/7 == 14 (16-bit)", div_uw, 100, 7, 14, "div.uw"),
    _exact_div_test("N4 div.ub 100/7 == 14 (8-bit)", div_ub, 100, 7, 14, "div.ub"),
    _exact_div_test("N5 div.so -10/3 == -3", div_so,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFD, "div.so"),
    _exact_div_test("N6 div.sb -10/3 == -3 (8-bit)", div_sb,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFD, "div.sb"),

    # Divide-by-zero → defined value
    _div_by_zero_test("D0 div.so /0 → -1", div_so, -1, "div.so"),
    _div_by_zero_test("D1 div.st /0 → -1", div_st, -1, "div.st"),
    _div_by_zero_test("D2 div.sw /0 → -1", div_sw, -1, "div.sw"),
    _div_by_zero_test("D3 div.sb /0 → -1", div_sb, -1, "div.sb"),
    _div_by_zero_test("D4 div.uo /0 → max64", div_uo, 0xFFFFFFFFFFFFFFFF, "div.uo"),
    _div_by_zero_test("D5 div.ut /0 → max32", div_ut, 0x00000000FFFFFFFF, "div.ut"),
    _div_by_zero_test("D6 div.uw /0 → max16", div_uw, 0x000000000000FFFF, "div.uw"),
    _div_by_zero_test("D7 div.ub /0 → max8", div_ub, 0x00000000000000FF, "div.ub"),

    # INT_MIN÷-1 → defined value
    _int_min_div_neg1_test("O0 div.so INT64_MIN/-1 → INT64_MIN",
                           div_so, 0x8000000000000000, 0x8000000000000000, "div.so"),
    _int_min_div_neg1_test("O1 div.st INT32_MIN/-1 → 0xFFFF_FFFF_8000_0000",
                           div_st, 0xFFFFFFFF80000000, 0xFFFFFFFF80000000, "div.st"),
    _int_min_div_neg1_test("O2 div.sw INT16_MIN/-1 → 0xFFFF_FFFF_FFFF_8000",
                           div_sw, 0xFFFFFFFFFFFF8000, 0xFFFFFFFFFFFF8000, "div.sw"),
    _int_min_div_neg1_test("O3 div.sb INT8_MIN/-1 → 0xFFFF_FFFF_FFFF_FF80",
                           div_sb, 0xFFFFFFFFFFFFFF80, 0xFFFFFFFFFFFFFF80, "div.sb"),

    # Normal exact value (rem)
    _exact_rem_test("R1 rem.uo 100%7 == 2", rem_uo, 100, 7, 2, "rem.uo"),
    _exact_rem_test("R2 rem.ut 100%7 == 2 (32-bit)", rem_ut, 100, 7, 2, "rem.ut"),
    _exact_rem_test("R3 rem.uw 100%7 == 2 (16-bit)", rem_uw, 100, 7, 2, "rem.uw"),
    _exact_rem_test("R4 rem.ub 100%7 == 2 (8-bit)", rem_ub, 100, 7, 2, "rem.ub"),
    _exact_rem_test("R5 rem.so -10%3 == -1", rem_so,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFF, "rem.so"),
    _exact_rem_test("R6 rem.sb -10%3 == -1 (8-bit)", rem_sb,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFF, "rem.sb"),

    # Remainder-by-zero → dividend (extended)
    _rem_by_zero_test("RD0 rem.so %0 → 0x64", rem_so, 0x64, "rem.so"),
    _rem_by_zero_test("RD1 rem.st %0 → 0x64", rem_st, 0x64, "rem.st"),
    _rem_by_zero_test("RD2 rem.sw %0 → 0x64", rem_sw, 0x64, "rem.sw"),
    _rem_by_zero_test("RD3 rem.sb %0 → 0x64", rem_sb, 0x64, "rem.sb"),
    _rem_by_zero_test("RD4 rem.uo %0 → 0x64", rem_uo, 0x64, "rem.uo"),
    _rem_by_zero_test("RD5 rem.ut %0 → 0x64", rem_ut, 0x64, "rem.ut"),
    _rem_by_zero_test("RD6 rem.uw %0 → 0x64", rem_uw, 0x64, "rem.uw"),
    _rem_by_zero_test("RD7 rem.ub %0 → 0x64", rem_ub, 0x64, "rem.ub"),

    # INT_MIN%-1 → 0
    _int_min_rem_neg1_test("RO0 rem.so INT64_MIN%-1 → 0",
                           rem_so, 0x8000000000000000, 0, "rem.so"),
    _int_min_rem_neg1_test("RO1 rem.st INT32_MIN%-1 → 0",
                           rem_st, 0xFFFFFFFF80000000, 0, "rem.st"),
    _int_min_rem_neg1_test("RO2 rem.sw INT16_MIN%-1 → 0",
                           rem_sw, 0xFFFFFFFFFFFF8000, 0, "rem.sw"),
    _int_min_rem_neg1_test("RO3 rem.sb INT8_MIN%-1 → 0",
                           rem_sb, 0xFFFFFFFFFFFFFF80, 0, "rem.sb"),

    # Encoding tests: rdhd=rd0 accepted
    _encoding_rdhd_rd0_test("E0 div.uo rdhd=rd0", [set_zw(10, 7), div_uo(5, 10, 0)], "div.uo"),
    _encoding_rdhd_rd0_test("E1 div.so rdhd=rd0", [set_zw(10, 7), div_so(5, 10, 0)], "div.so"),
    _encoding_rdhd_rd0_test("E2 div.ut rdhd=rd0", [set_zw(10, 7), div_ut(5, 10, 0)], "div.ut"),
    _encoding_rdhd_rd0_test("E3 div.st rdhd=rd0", [set_zw(10, 7), div_st(5, 10, 0)], "div.st"),
    _encoding_rdhd_rd0_test("E4 div.uw rdhd=rd0", [set_zw(10, 7), div_uw(5, 10, 0)], "div.uw"),
    _encoding_rdhd_rd0_test("E5 div.sw rdhd=rd0", [set_zw(10, 7), div_sw(5, 10, 0)], "div.sw"),
    _encoding_rdhd_rd0_test("E6 div.ub rdhd=rd0", [set_zw(10, 7), div_ub(5, 10, 0)], "div.ub"),
    _encoding_rdhd_rd0_test("E7 div.sb rdhd=rd0", [set_zw(10, 7), div_sb(5, 10, 0)], "div.sb"),
    _encoding_rdhd_rd0_test("E8 rem.uo rdhd=rd0", [set_zw(10, 7), rem_uo(5, 10, 0)], "rem.uo"),
    _encoding_rdhd_rd0_test("E9 rem.so rdhd=rd0", [set_zw(10, 7), rem_so(5, 10, 0)], "rem.so"),
    _encoding_rdhd_rd0_test("E10 rem.ut rdhd=rd0", [set_zw(10, 7), rem_ut(5, 10, 0)], "rem.ut"),
    _encoding_rdhd_rd0_test("E11 rem.st rdhd=rd0", [set_zw(10, 7), rem_st(5, 10, 0)], "rem.st"),
    _encoding_rdhd_rd0_test("E12 rem.uw rdhd=rd0", [set_zw(10, 7), rem_uw(5, 10, 0)], "rem.uw"),
    _encoding_rdhd_rd0_test("E13 rem.sw rdhd=rd0", [set_zw(10, 7), rem_sw(5, 10, 0)], "rem.sw"),
    _encoding_rdhd_rd0_test("E14 rem.ub rdhd=rd0", [set_zw(10, 7), rem_ub(5, 10, 0)], "rem.ub"),
    _encoding_rdhd_rd0_test("E15 rem.sb rdhd=rd0", [set_zw(10, 7), rem_sb(5, 10, 0)], "rem.sb"),
]

# CTL self-check: expect ILLI for a MATCH case → should get UNDI → FAIL.
# The comparison result MATCHES (correct expected value), so the probe should
# produce UNDI(137). We expect ILLI(136) instead → FAIL → probe can detect.
CTL_CHECKS = [
    ("CTL: div.uo 100/7=14 expect ILLI (wrong; match→UNDI=137)",
     [set_zw(10, 100), set_zw(11, 7), div_uo(5, 10, 11),
      set_zw(6, 14),                   # expected=14 (CORRECT → match)
      cmp_uo(7, 5, 6),                 # rd7 = cmp(14, 14) = 0 (match)
      set_zw(1, 0),                    # rd1 = 0
      br_ne(7, 1, 2),                  # match → NOT taken → continue
      set_zw(1, 1),
      br_ne(1, 0, 2),                  # unconditional → skip 2 → UNDI(137)
      cmp_uo(0, 0, 0)],               # (not reached on match)
     ILLI_EXIT,  # WRONG: match gives UNDI(137), not ILLI(136)
     "Self-check FAILED: probe cannot detect wrong values"),
]

# ── Main ──────────────────────────────────────────────────────────────

def run_test_group(tests, group_name):
    passed = failed = 0
    fail_details = []
    for name, rom_insns, expected, fail_desc in tests:
        rom = build_rom(rom_insns)
        code, stderr = run_rom(rom)
        if code == expected:
            status = "PASS"; passed += 1
        elif code == CRASH_EXIT:
            status = "FAIL"; failed += 1
            fail_details.append(f"  [{status}] {name}: exit={code} CRASH")
        elif code == -1:
            status = "TIMEOUT"; failed += 1
            fail_details.append(f"  [{status}] {name}: {stderr}")
        else:
            status = "FAIL"; failed += 1
            fail_details.append(f"  [{status}] {name}: exit={code} (expected {expected}) — {fail_desc}")
        print(f"  [{status}] {name}: exit={code} (expect {expected})")
    return passed, failed, fail_details

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1
    print("=" * 70)
    print("SPEC-066t Min ROM Probe: div/rem defined-value semantics (v2)")
    print("=" * 70)
    print(f"  Exit codes: ILLI={ILLI_EXIT}, UNDI={UNDI_EXIT}, CRASH={CRASH_EXIT}")
    print(f"  Comparison: cmp.uo + br.ne → UNDI=match(137), ILLI=mismatch(136)")
    print(f"  Tests: {len(TESTS)} main + {len(CTL_CHECKS)} CTL")
    print()
    print("-" * 70)
    print(f"Main tests ({len(TESTS)}):")
    print("-" * 70)
    passed, failed, fail_details = run_test_group(TESTS, "main")
    print(f"\nMain results: {passed}/{passed+failed} passed, {failed} failed")
    if fail_details:
        print("\nFailed main tests:")
        for d in fail_details: print(d)
    print()
    print("-" * 70)
    print("CTL self-check:")
    print("  FAIL = probe works | PASS = probe broken")
    print("-" * 70)
    ctl_passed, ctl_failed, _ = run_test_group(CTL_CHECKS, "CTL")
    ctl_ok = ctl_failed > 0
    print(f"\nCTL: {ctl_passed} PASS, {ctl_failed} FAIL → {'OK' if ctl_ok else 'BROKEN'}")
    print(f"\n{'=' * 70}")
    all_pass = failed == 0 and ctl_ok
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    print(f"  Main: {passed}/{passed+failed} | CTL: {'OK' if ctl_ok else 'BROKEN'}")
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
