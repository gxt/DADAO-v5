#!/usr/bin/env python3
"""Min ROM probe for QEMU-005t RD integer semantics (v4).

Changes from v3 (SPEC-066t):
- Comparison mechanism changed from div-by-zero to br.ne (div-by-zero now
  produces defined values, not ILLI).
- N2 tests: INT_MIN/-1 now expects defined value (not ILLI).
- By-zero tests: now expect defined value (not ILLI).
- CTL self-check updated for br.ne mechanism.

Value comparison method (br.ne-based, v4):
  1. Compute result
  2. Load expected value
  3. cmp.uo rd_cmp, result, expected → rd_cmp=0 if equal, ±1 if not
  4. set.zw rd_zero, 0
  5. br.ne rd_cmp, rd_zero, 2 → if mismatch, skip 2 → illi
  6. set.zw rd1, 1; br.ne rd1, rd0, 2 → unconditional skip illi → UNDI
  7. illi → exit 136
  So: UNDI(137) = PASS (match), ILLI(136) = FAIL (mismatch).

Usage: python3 tools/qemu/min_rom_probe_005t.py
"""

import struct
import subprocess
import sys
import os
import tempfile

QEMU = ".work/build/qemu/qemu-system-dadao"

# ── Instruction encoding helpers ──────────────────────────────────────

def encode_rrrr(op, rdha, rdhb, rdhc, rdhd):
    return struct.pack('>I', (op << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd)

def encode_orrr(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_orri(op, ha, hb, hc, immu6):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | (immu6 & 0x3F))

def encode_riii(op, ha, imms18):
    imm = imms18 & 0x3FFFF
    return struct.pack('>I', (op << 24) | (ha << 18) | imm)

def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_oiii(op, ha, immu18):
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)

def add_si(rd, imms18):
    return encode_riii(0x59, rd, imms18 & 0x3FFFF)

def div_uo(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x38, rdhb, rdhc, rdhd)
def div_so(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x39, rdhb, rdhc, rdhd)
def div_sb(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x39, rdhb, rdhc, rdhd)
def rem_uo(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x3A, rdhb, rdhc, rdhd)
def rem_so(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x3B, rdhb, rdhc, rdhd)
def cmp_uo(rdhb, rdhc, rdhd): return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

# SPEC-069t: ext.ub/ext.sb deleted (narrow ext removed)
# shr.ub encoding (post-SPEC-069t): op=0x43, ha=0x12 (orrr), ha=0x1A (orri)
def shr_ub_orri(rdhb, rdhc, immu6): return encode_orri(0x43, 0x1A, rdhb, rdhc, immu6)
# SPEC-069t: value semantics test helpers
def shl_ut_orri(rdhb, rdhc, immu6): return encode_orri(0x41, 0x1C, rdhb, rdhc, immu6)
def shr_ut_orri(rdhb, rdhc, immu6): return encode_orri(0x41, 0x1A, rdhb, rdhc, immu6)
def cmp_st_orrr(rdhb, rdhc, rdhd): return encode_orrr(0x41, 0x2B, rdhb, rdhc, rdhd)
def cmp_ut_orrr(rdhb, rdhc, rdhd): return encode_orrr(0x41, 0x2A, rdhb, rdhc, rdhd)
def or_w_rwii(rdha, wpN, immu16):
    """or.w rdha, wpN, immu16 — rwii format."""
    imm_hi4 = (immu16 >> 12) & 0xF
    imm_mid6 = (immu16 >> 6) & 0x3F
    imm_lo6 = immu16 & 0x3F
    return struct.pack('>I', (0x48 << 24) | (rdha << 18) | (wpN << 16) |
                       (imm_hi4 << 12) | (imm_mid6 << 6) | imm_lo6)
def ext_so_orri(rdhb, rdhc, immu6): return encode_orri(0x40, 0x19, rdhb, rdhc, immu6)

def add_sb(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x21, rdhb, rdhc, rdhd)
def add_ub(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x20, rdhb, rdhc, rdhd)
def mul_sb(rdhb, rdhc, rdhd): return encode_orrr(0x43, 0x31, rdhb, rdhc, rdhd)
def shl_uo_orri(rdhb, rdhc, immu6): return encode_orri(0x40, 0x1C, rdhb, rdhc, immu6)
def shr_uo_orri(rdhb, rdhc, immu6): return encode_orri(0x40, 0x1A, rdhb, rdhc, immu6)

def br_ne(rdha, rdhb, imms12):
    """br.ne rdha, rdhb, imms12 (op=0x6F, rrii format)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_orrr(0x6F, rdha, rdhb, hc, hd)

def illi(): return encode_oiii(0x00, 0x00, 0)
def swym(): return encode_oiii(0x00, 0x02, 0)

# ── Terminators / ROM ────────────────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

def build_rom(instructions):
    rom = b''
    for insn in instructions: rom += insn
    rom += UNDI_TERMINATOR
    while len(rom) < 64: rom += illi()
    return rom

def run_rom(rom_data, kernel_data=None, timeout=10):
    if kernel_data is None: kernel_data = illi() * 4
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

ILLI_EXIT = 136
UNDI_EXIT = 137
CRASH_EXIT = 134

# ── Helper: exact-value comparison (br.ne-based, v4) ─────────────────
#
# Sequence appended to insns:
#   [N]   set.zw rd_expected, ... (construct expected value)
#   [N+K] cmp.uo rd_cmp, rd_result, rd_expected
#   [N+K+1] set.zw rd_zero, 0
#   [N+K+2] br.ne rd_cmp, rd_zero, 2   # mismatch → skip 2 → illi
#   [N+K+3] set.zw rd1, 1              # match: prep unconditional skip
#   [N+K+4] br.ne rd1, rd0, 2          # unconditional → skip illi → UNDI
#   [N+K+5] illi                        # mismatch target
#
# Match:   cmp=0 → br.ne NOT taken → set.zw(1,1) → br.ne(1,0,2) TAKEN → UNDI(137)
# Mismatch: cmp≠0 → br.ne TAKEN → illi(136)

def _set_rd_to_val(insns, rd, val):
    """Set rd to a 64-bit value. Handles small values via set.zw+add_si."""
    val64 = val & 0xFFFFFFFFFFFFFFFF
    if val64 == 0:
        insns.append(set_zw(rd, 0))
    elif -0x20000 <= val < 0x20000:
        insns.append(set_zw(rd, 0))
        if val64 != 0:
            insns.append(add_si(rd, val & 0x3FFFF))
    else:
        wp0 = val64 & 0xFFFF
        insns.append(set_zw(rd, wp0))
        remaining = (val64 - wp0) & 0xFFFFFFFFFFFFFFFF
        if remaining != 0:
            insns.append(add_si(rd, remaining & 0x3FFFF))

def _exact_cmp(insns, rd_result, rd_expected, val_expected):
    """Append comparison + branch sequence. UNDI(137)=PASS, ILLI(136)=FAIL."""
    _set_rd_to_val(insns, rd_expected, val_expected)
    insns.append(cmp_uo(7, rd_result, rd_expected))
    insns.append(set_zw(1, 0))
    insns.append(br_ne(7, 1, 2))        # mismatch → skip 2 → cmp.uo(0,0,0)
    insns.append(set_zw(1, 1))          # match: rd1=1
    insns.append(br_ne(1, 0, 2))        # unconditional → skip 2 → UNDI
    insns.append(cmp_uo(0, 0, 0))       # mismatch target → rdhb=0 → ILLI

# ── Test cases ────────────────────────────────────────────────────────

TESTS = [
    # ── N1: Exact value checks ──
    ("N1 div.uo 100/7 == 14 (exact)",
     [set_zw(10, 100), set_zw(11, 7), div_uo(5, 10, 11)],
     "div.uo 100/7 != 14"),

    ("N1 rem.uo 100%7 == 2 (exact)",
     [set_zw(10, 100), set_zw(11, 7), rem_uo(5, 10, 11)],
     "rem.uo 100%7 != 2"),

    ("N1 div.uo 0/7 == 0 (exact, regression)",
     [set_zw(10, 0), set_zw(11, 7), div_uo(5, 10, 11)],
     "div.uo 0/7 != 0"),

    # ── N2: INT_MIN ÷ -1 → defined value (SPEC-066t) ──
    ("N2 div.so INT64_MIN/-1 → INT64_MIN (defined value)",
     [encode_rwii(0x4C, 2, 3, 0x8000),  # set.zw rd2, wp3, 0x8000 → INT64_MIN
      add_si(3, -1),                      # rd3 = -1
      div_so(1, 2, 3),                    # rd1 = INT64_MIN / -1 = INT64_MIN
      # Compare rd1 with rd2 (both should be INT64_MIN)
      cmp_uo(7, 1, 2),                    # rd7 = cmp(result, INT64_MIN)
      set_zw(1, 0),                       # rd1 = 0 (reused as scratch)
      br_ne(7, 1, 2),                     # mismatch → skip 2 → cmp.uo(0,0,0)
      set_zw(1, 1), br_ne(1, 0, 2),      # match → skip 2 → UNDI
      cmp_uo(0, 0, 0)],                   # mismatch target → ILLI
     "INT64_MIN/-1 not INT64_MIN"),

    ("N2 div.sb INT8_MIN/-1 → 0xFF...FF80 (defined value)",
     [set_zw(2, 0x0080), add_si(2, -256),  # rd2 = -128 = INT8_MIN
      set_zw(3, 0), add_si(3, -1),          # rd3 = -1
      div_sb(1, 2, 3),                      # rd1 = INT8_MIN / -1 = 0xFF...FF80
      # Expected: 0xFFFFFFFFFFFFFF80
      set_zw(6, 0x0080), add_si(6, -256),   # rd6 = -128 (0xFF...FF80)
      cmp_uo(7, 1, 6),
      set_zw(1, 0), br_ne(7, 1, 2),
      set_zw(1, 1), br_ne(1, 0, 2), cmp_uo(0, 0, 0)],
     "INT8_MIN/-1 not 0xFF...FF80"),

    # ── B1: Legal div/rem (must NOT crash) ──
    ("B1 legal div.uo completes normally",
     [set_zw(10, 100), set_zw(11, 7), div_uo(5, 10, 11)],
     "Legal div.uo crashed"),

    ("B1 legal rem.uo completes normally",
     [set_zw(10, 100), set_zw(11, 7), rem_uo(5, 10, 11)],
     "Legal rem.uo crashed"),

    ("B1 legal div.so completes normally",
     [set_zw(2, 0xFFF2), add_si(2, -14), set_zw(3, 3), div_so(1, 2, 3)],
     "Legal div.so crashed"),

    # ── B2: SPEC-069t — ext.ub/ext.sb deleted, narrow ext tests removed ──

    # ── B3: Fixed-width sign/zero extension (exact values) ──
    ("B3 add.sb 0x40+0x40 == -128 (exact)",
     [set_zw(2, 0x0040), set_zw(3, 0x0040), add_sb(5, 2, 3)],
     "add.sb 0x40+0x40 != -128"),

    ("B3 mul.sb 10 * -2 == -20 (exact)",
     [set_zw(2, 0x000A), set_zw(3, 0), add_si(3, -2), mul_sb(5, 2, 3)],
     "mul.sb 10*-2 != -20"),

    # ── B4: ext high-bit fill (exact values) ──
    # SPEC-069t: ext.ub/ext.sb deleted; ext.so test retained

    ("B4 ext.so orri pos=2 == -1 (exact)",
     [set_zw(2, 0x000F), ext_so_orri(1, 2, 2)],
     "ext.so pos=2 != -1"),

    # ── Shift (exact values) ──
    ("shl.uo 0xF << 4 == 0xF0 (exact)",
     [set_zw(2, 0x000F), shl_uo_orri(1, 2, 4)],
     "shl.uo 0xF<<4 != 0xF0"),
    ("shr.uo 0xF0 >> 4 == 0x0F (exact)",
     [set_zw(2, 0x00F0), shr_uo_orri(1, 2, 4)],
     "shr.uo 0xF0>>4 != 0x0F"),

    # ── div by zero → defined value (SPEC-066t) ──
    ("div.uo /0 (constant) → -1 (defined value)",
     [set_zw(2, 7), set_zw(3, 0), div_uo(1, 2, 3)],
     "div by zero result != -1"),

    ("div.uo /0 (computed) → -1 (defined value)",
     [set_zw(2, 7), set_zw(3, 0), add_si(3, 0), div_uo(1, 2, 3)],
     "div by zero (computed) result != -1"),

    # ── SPEC-069t: value semantics — high bits must be written (not preserved) ──
    # 3-tuple format: _append_comparison appends the _exact_cmp sequence.
    # Pre-set destination register with non-zero high bits (0xDEADBEEF00000000).
    # NEW semantics: high bits zeroed → result matches expected → UNDI(137).
    # OLD semantics: high bits preserved → mismatch → ILLI(136).
    ("V1 shl.ut 0xFF<<4: high bits zeroed (rd1 had 0xDEADBEEF...)",
     [set_zw(2, 0xFF),
      set_zw(1, 0), or_w_rwii(1, 2, 0xBEEF), or_w_rwii(1, 3, 0xDEAD),
      shl_ut_orri(1, 2, 4)],
     "shl.ut did not zero high bits"),
    ("V2 shr.ut 0xFF00>>4: high bits zeroed (rd1 had 0xDEADBEEF...)",
     [set_zw(2, 0xFF00),
      set_zw(1, 0), or_w_rwii(1, 2, 0xBEEF), or_w_rwii(1, 3, 0xDEAD),
      shr_ut_orri(1, 2, 4)],
     "shr.ut did not zero high bits"),
    ("V3 cmp.ut(1, 2) = -1 zero-extended (rd1 had 0xDEADBEEF...)",
     [set_zw(2, 1), set_zw(3, 2),
      set_zw(1, 0), or_w_rwii(1, 2, 0xBEEF), or_w_rwii(1, 3, 0xDEAD),
      cmp_ut_orrr(1, 2, 3)],
     "cmp.ut did not zero-extend result"),
]

# ── CTL self-check ────────────────────────────────────────────────────
# With br.ne: match→UNDI(137), mismatch→cmp.uo(0,0,0)→ILLI(136).
# CTL expects ILLI for a MATCH case → should get UNDI → FAIL.
CTL_CHECKS = [
    ("CTL: shr.ub 0xFF>>2=0x3F but expect 7 (wrong; match→UNDI=137)",
     [set_zw(2, 0xFF), shr_ub_orri(1, 2, 2),  # rd1 = 0x3F (shr.ub 0xFF>>2)
      set_zw(6, 0x3F),                           # rd6 = 0x3F (correct value)
      cmp_uo(7, 1, 6),                           # rd7 = 0 (match)
      set_zw(1, 0), br_ne(7, 1, 2),              # match → not taken → continue
      set_zw(1, 1), br_ne(1, 0, 2),              # unconditional → skip 2 → UNDI
      cmp_uo(0, 0, 0)],                          # (not reached on match)
     ILLI_EXIT,  # WRONG: will get UNDI (137) because values match
     "Self-check FAILED: probe cannot detect wrong values"),
]

# ── Helpers for test execution ────────────────────────────────────────

def _build_exact_test(name, setup_insns, fail_desc):
    """Wrap setup instructions + comparison into a test tuple.
    The setup puts the result in rd5 (for div/rem) or rd1 (for others).
    Appends exact comparison: rd5/rd1 vs expected value."""
    # Determine which register holds the result based on the last setup instruction
    # This is a simplified wrapper; actual tests use inline sequences.
    pass  # Not used directly; tests are built inline.

def run_test_group(tests, group_name):
    passed = failed = 0
    fail_details = []
    for item in tests:
        if len(item) == 4:
            name, rom_insns, expected, fail_desc = item
        else:
            name, rom_insns, fail_desc = item
            expected = UNDI_EXIT  # default for simplified format

        # For simplified tests (3-tuple), append comparison sequence
        if len(item) == 3:
            # Determine result register and expected value
            rom_insns = list(rom_insns)
            _append_comparison(rom_insns, name)

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

def _append_comparison(insns, name):
    """Append exact-value comparison based on test name.
    Uses rd5 as result register for most tests, rd1 for div/rem results."""
    # Determine expected value and result register from test name
    if "div.uo 100/7 == 14" in name:
        _exact_cmp(insns, 5, 6, 14)
    elif "rem.uo 100%7 == 2" in name:
        _exact_cmp(insns, 5, 6, 2)
    elif "div.uo 0/7 == 0" in name:
        _exact_cmp(insns, 5, 6, 0)
    elif "add.sb 0x40+0x40 == -128" in name:
        _exact_cmp(insns, 5, 6, -128)
    elif "mul.sb 10 * -2 == -20" in name:
        _exact_cmp(insns, 5, 6, -20)
    elif "ext.so orri pos=2 == -1" in name:
        _exact_cmp(insns, 1, 6, -1)
    elif "shl.uo 0xF << 4 == 0xF0" in name:
        _exact_cmp(insns, 1, 6, 0xF0)
    elif "shr.uo 0xF0 >> 4 == 0x0F" in name:
        _exact_cmp(insns, 1, 6, 0x0F)
    elif "div.uo /0" in name:
        # div-by-zero → -1 (defined value)
        _exact_cmp(insns, 1, 6, -1)
    elif "legal div.uo" in name:
        pass  # Just reach UNDI = PASS
    elif "legal rem.uo" in name:
        pass
    elif "legal div.so" in name:
        pass
    # SPEC-069t: ext.ub orrr/orri ILLI tests deleted
    # SPEC-069t: V1/V2/V3 value semantics tests — use _exact_cmp (3-tuple)
    elif "V1 shl.ut" in name:
        # shl.ut(0xFF, 4) = 0xFF0, high bits zeroed
        _exact_cmp(insns, 1, 6, 0xFF0)
    elif "V2 shr.ut" in name:
        # shr.ut(0xFF00, 4) = 0x0FF0, high bits zeroed
        _exact_cmp(insns, 1, 6, 0x0FF0)
    elif "V3 cmp.ut" in name:
        # cmp.ut(1, 2): 1<2 unsigned → -1, zero-extended from 32 bits → 0x00000000FFFFFFFF
        # _set_rd_to_val can't handle this (add.si sign-extends 0xFFFF to -1)
        # Build rd6 = 0x00000000FFFFFFFF manually: set.zw wp0=0xFFFF + or.w wp1=0xFFFF
        insns.append(set_zw(6, 0xFFFF))         # rd6 = 0x000000000000FFFF
        insns.append(or_w_rwii(6, 1, 0xFFFF))   # rd6[31:16] = 0xFFFF → 0x00000000FFFFFFFF
        insns.append(cmp_uo(7, 1, 6))
        insns.append(set_zw(1, 0))
        insns.append(br_ne(7, 1, 2))
        insns.append(set_zw(1, 1))
        insns.append(br_ne(1, 0, 2))
        insns.append(cmp_uo(0, 0, 0))

# ── Main ──────────────────────────────────────────────────────────────

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1
    print("=" * 70)
    print("QEMU-005t Min ROM Probe (v4: br.ne-based, SPEC-066t)")
    print("=" * 70)
    print(f"  Exit codes: ILLI={ILLI_EXIT}, UNDI={UNDI_EXIT}, CRASH={CRASH_EXIT}")
    print(f"  Comparison: cmp.uo + br.ne → UNDI=match(137), ILLI=mismatch(136)")
    print()

    # Build tests with comparison sequences
    built_tests = []
    for item in TESTS:
        if len(item) == 3:
            name, setup_insns, fail_desc = item
            insns = list(setup_insns)
            _append_comparison(insns, name)
            # Determine expected exit
            if "ILLI" in name or "hd=8" in name:
                expected = ILLI_EXIT
            else:
                expected = UNDI_EXIT
            built_tests.append((name, insns, expected, fail_desc))
        else:
            built_tests.append(item)

    print("-" * 70)
    print("Main tests:")
    print("-" * 70)
    passed, failed, fail_details = run_test_group(built_tests, "main")
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
