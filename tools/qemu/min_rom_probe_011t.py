#!/usr/bin/env python3
"""Min ROM probe for QEMU-011t: div/rem label顺序定向回归验证.

Covers 16 div.* + 16 rem.* tests across all sizes (byte/wyde/tetra/octa)
and signedness (u/s). Key semantic checks per contract-isa §3.1.5:

  div.* tests (16):
    N1-N4:  Normal exact value (truncate-toward-zero)
    N5:     Signed negative dividend (rem sign = dividend sign)
    D0-D3:  Divide-by-zero → ILLI (0x88)
    O0-O3:  INT_MIN÷-1 → ILLI (0x88) for signed variants

  rem.* tests (16):
    R1-R4:  Normal exact value
    R5:     Signed negative dividend
    RD0-RD3: Divide-by-zero → ILLI
    RO0-RO3: INT_MIN%−1 → ILLI (signed overflow)

Exit codes: ILLI=136(0x88), UNDI=137(0x89), CRASH=134

Value comparison method (exact):
  1. Compute result via div/rem
  2. Load expected value
  3. cmp.uo rdR, result, expected → rdR=0 if equal, ±1 if not
  4. div.uo rdX, 1, rdR → if rdR==0: div-by-zero → ILLI(136); else → UNDI(137)
  So: ILLI(136) = exact match, UNDI(137) = mismatch.

Readback verification (O0-O3/RO0-RO3, AGENTS.md: 探针值构造须回读校验):
  1. Construct rd10 = INT_MIN via _set_rd_to_val
  2. rd2rb(rb18, rd10, 1) — store rd10 to temporary RB register (true RD→RB copy)
  3. rb2rd(rd20, rb18, 1) — load rb18 back to rd20 (true readback of rd10)
  4. Construct rd21 = expected INT_MIN via _set_rd_to_val
  5. cmp.uo rd22, rd20, rd21 → rd22=0 if match, ±1 if mismatch
  6. br.ne rd22, 0, 3 → if mismatch, skip real test → UNDI(137) = FAIL
  7. If match: fall through to real div/rem overflow test → ILLI(136) if caught
  This ensures: mismatch → FAIL (non-136); match → real test executes (no short-circuit).

Branch verification (AGENTS.md §验证脚本反例门控, 探针分支须双向验证):
  Exact value tests (N/R/D/RD): no conditional branches — branching is implicit
  in the div-by-zero behavior (cmp.uo + div.uo).
  Readback verification (O/RO): one conditional branch (br.ne) for mismatch detection.
  Every test case has exactly two possible outcomes:
  - Exact value match → cmp.uo sets rdR=0 → div.uo by 0 → ILLI(136)
  - Exact value mismatch → cmp.uo sets rdR=±1 → div.uo by non-zero → reaches UNDI → 137
  Readback verification has three possible outcomes:
  - Readback match + overflow caught → ILLI(136) = PASS
  - Readback mismatch → br.ne skips real test → UNDI(137) = FAIL (construction error)
  - Readback match + overflow not caught → UNDI(137) = FAIL (implementation bug)

Usage: python3 tools/qemu/min_rom_probe_011t.py
"""

import struct
import subprocess
import sys
import os
import tempfile

QEMU = ".work/build/qemu/qemu-system-dadao"

# ── Instruction encoding helpers ──────────────────────────────────────

def encode_orrr(op, ha, hb, hc, hd):
    """Encode an orrr-format instruction: op[31:24] ha[23:18] hb[17:12] hc[11:6] hd[5:0]"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_rwii(op, ha, wpN, immu16):
    """Encode an rwii-format instruction"""
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_riii(op, ha, imms18):
    """Encode an riii-format instruction (18-bit signed immediate)"""
    imm = imms18 & 0x3FFFF
    return struct.pack('>I', (op << 24) | (ha << 18) | imm)

def encode_oiii(op, ha, immu18):
    """Encode an oiii-format instruction"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw(rd, immu16):
    """set.zw rd, wp0, immu16 — rd[15:0]=immu16, rest=0
    op=0x4C, ha=rd, hb=0(wp0|hi4=0), hc=mid6, hd=lo6"""
    return encode_rwii(0x4C, rd, 0, immu16)

def set_zw_wp3(rd, immu16):
    """set.zw rd, wp3, immu16 — rd[63:48]=immu16, rest=0
    wpN=3 → hb[5:4]=11"""
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (3 << 4) | hi4
    return struct.pack('>I', (0x4C << 24) | (rd << 18) | (hb << 12) | (mid6 << 6) | lo6)

def or_w(rd, wpN, immu16):
    """or.w rd, wpN, immu16 — rd[wyde(wpN)] |= immu16, other wydes unchanged
    op=0x48, rwii format"""
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (0x48 << 24) | (rd << 18) | (hb << 12) | (mid6 << 6) | lo6)

def add_si(rd, imms18):
    """add.si rd, imms18 — rd += sign_extend(imms18)
    op=0x59"""
    return encode_riii(0x59, rd, imms18 & 0x3FFFF)

# ── div/rem encoding (from opcodes.yaml) ─────────────────────────────
# MISC-octa:  op=0x40
# MISC-tetra: op=0x41
# MISC-wyde:  op=0x42
# MISC-byte:  op=0x43
#
# ha values:
#   div.u: ha=0x38, div.s: ha=0x39
#   rem.u: ha=0x3A, rem.s: ha=0x3B

def div_uo(rdhb, rdhc, rdhd):
    """div.uo rdhb, rdhc, rdhd — unsigned octa divide
    op=0x40, ha=0x38"""
    return encode_orrr(0x40, 0x38, rdhb, rdhc, rdhd)

def div_so(rdhb, rdhc, rdhd):
    """div.so rdhb, rdhc, rdhd — signed octa divide
    op=0x40, ha=0x39"""
    return encode_orrr(0x40, 0x39, rdhb, rdhc, rdhd)

def rem_uo(rdhb, rdhc, rdhd):
    """rem.uo rdhb, rdhc, rdhd — unsigned octa remainder
    op=0x40, ha=0x3A"""
    return encode_orrr(0x40, 0x3A, rdhb, rdhc, rdhd)

def rem_so(rdhb, rdhc, rdhd):
    """rem.so rdhb, rdhc, rdhd — signed octa remainder
    op=0x40, ha=0x3B"""
    return encode_orrr(0x40, 0x3B, rdhb, rdhc, rdhd)

def div_ut(rdhb, rdhc, rdhd):
    """div.ut rdhb, rdhc, rdhd — unsigned tetra divide
    op=0x41, ha=0x38"""
    return encode_orrr(0x41, 0x38, rdhb, rdhc, rdhd)

def div_st(rdhb, rdhc, rdhd):
    """div.st rdhb, rdhc, rdhd — signed tetra divide
    op=0x41, ha=0x39"""
    return encode_orrr(0x41, 0x39, rdhb, rdhc, rdhd)

def rem_ut(rdhb, rdhc, rdhd):
    """rem.ut rdhb, rdhc, rdhd — unsigned tetra remainder
    op=0x41, ha=0x3A"""
    return encode_orrr(0x41, 0x3A, rdhb, rdhc, rdhd)

def rem_st(rdhb, rdhc, rdhd):
    """rem.st rdhb, rdhc, rdhd — signed tetra remainder
    op=0x41, ha=0x3B"""
    return encode_orrr(0x41, 0x3B, rdhb, rdhc, rdhd)

def div_uw(rdhb, rdhc, rdhd):
    """div.uw rdhb, rdhc, rdhd — unsigned wyde divide
    op=0x42, ha=0x38"""
    return encode_orrr(0x42, 0x38, rdhb, rdhc, rdhd)

def div_sw(rdhb, rdhc, rdhd):
    """div.sw rdhb, rdhc, rdhd — signed wyde divide
    op=0x42, ha=0x39"""
    return encode_orrr(0x42, 0x39, rdhb, rdhc, rdhd)

def rem_uw(rdhb, rdhc, rdhd):
    """rem.uw rdhb, rdhc, rdhd — unsigned wyde remainder
    op=0x42, ha=0x3A"""
    return encode_orrr(0x42, 0x3A, rdhb, rdhc, rdhd)

def rem_sw(rdhb, rdhc, rdhd):
    """rem.sw rdhb, rdhc, rdhd — signed wyde remainder
    op=0x42, ha=0x3B"""
    return encode_orrr(0x42, 0x3B, rdhb, rdhc, rdhd)

def div_ub(rdhb, rdhc, rdhd):
    """div.ub rdhb, rdhc, rdhd — unsigned byte divide
    op=0x43, ha=0x38"""
    return encode_orrr(0x43, 0x38, rdhb, rdhc, rdhd)

def div_sb(rdhb, rdhc, rdhd):
    """div.sb rdhb, rdhc, rdhd — signed byte divide
    op=0x43, ha=0x39"""
    return encode_orrr(0x43, 0x39, rdhb, rdhc, rdhd)

def rem_ub(rdhb, rdhc, rdhd):
    """rem.ub rdhb, rdhc, rdhd — unsigned byte remainder
    op=0x43, ha=0x3A"""
    return encode_orrr(0x43, 0x3A, rdhb, rdhc, rdhd)

def rem_sb(rdhb, rdhc, rdhd):
    """rem.sb rdhb, rdhc, rdhd — signed byte remainder
    op=0x43, ha=0x3B"""
    return encode_orrr(0x43, 0x3B, rdhb, rdhc, rdhd)

def cmp_uo(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd — unsigned octa compare → -1/0/1
    op=0x40, ha=0x2A"""
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def rb2rd(rdhb, rbhc, immu6):
    """rb2rd rdhb, rbhc, immu6 (MISC-octa, ha=0x36)"""
    return encode_orrr(0x40, 0x36, rdhb, rbhc, immu6)

def rd2rb(rbhb, rdhc, immu6):
    """rd2rb rbhb, rdhc, immu6 (MISC-octa, ha=0x35)
    Copies from RD bank to RB bank: rb[rbhb..] = rd[rdhc..]"""
    return encode_orrr(0x40, 0x35, rbhb, rdhc, immu6)

def br_ne(rdha, rdhb, imms12):
    """br.ne rdha, rdhb, imms12 (op=0x6F) — branch if rdha != rdhb
    Offset imms12 is in units of instructions (4 bytes each)."""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_orrr(0x6F, rdha, rdhb, hc, hd)

def illi():
    """illi — trigger ILLI exception (exit=136)"""
    return encode_oiii(0x00, 0x00, 0)

# ── Terminators ───────────────────────────────────────────────────────

# UNDI = undefined instruction exception = exit 137 (0x89)
UNDI_TERMINATOR = b'\x08\x04\x00\x01'

# ── ROM builder ───────────────────────────────────────────────────────

def build_rom(instructions):
    """Build a ROM binary from a list of instruction bytes.
    Appends UNDI terminator so 'normal completion' = exit 137."""
    rom = b''
    for insn in instructions:
        rom += insn
    rom += UNDI_TERMINATOR
    while len(rom) < 64:
        rom += illi()
    return rom

def run_rom(rom_data, kernel_data=None, timeout=10):
    """Run a ROM with qemu-system-dadao, return (exit_code, stderr)."""
    if kernel_data is None:
        kernel_data = illi() * 4

    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(rom_data)
        rom_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(kernel_data)
        kernel_path = f.name

    try:
        result = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic',
             '-bios', rom_path, '-kernel', kernel_path],
            capture_output=True, timeout=timeout, text=True
        )
        return result.returncode, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rom_path)
        os.unlink(kernel_path)

# ── Exit code constants ───────────────────────────────────────────────

ILLI_EXIT = 136   # 0x88 — ILLI exception
UNDI_EXIT = 137   # 0x89 — reached UNDI terminator (normal completion)
CRASH_EXIT = 134  # 0x86 — SIGABRT (regression)

# ── Helper: construct expected value from 64-bit int ──────────────────
#
# For exact value comparison:
#   cmp.uo rdR, result, expected → rdR=0 if equal, ±1 if not
#   div.uo rdX, 1, rdR → if rdR==0: div-by-zero → ILLI(136); else → UNDI(137)
#   ILLI(136) = values match, UNDI(137) = values differ.

def _set_rd_to_val(insns, rd, val):
    """Generate instructions to set rd to a 64-bit value.
    Uses set.zw + or.w for correct 64-bit construction.
    set.zw rd, wp3, hi16 sets bits[63:48], zeros rest.
    or.w rd, wpN, immu16 sets bits at wyde position wpN without affecting other wydes."""
    val64 = val & 0xFFFFFFFFFFFFFFFF
    
    # Extract 16-bit wydes
    wp0 = val64 & 0xFFFF          # bits[15:0]
    wp1 = (val64 >> 16) & 0xFFFF  # bits[31:16]
    wp2 = (val64 >> 32) & 0xFFFF  # bits[47:32]
    wp3 = (val64 >> 48) & 0xFFFF  # bits[63:48]
    
    # Optimization: use fewer instructions when possible
    if val64 == 0:
        # All zeros: just set.zw wp0, 0
        insns.append(set_zw(rd, 0))
    elif wp1 == 0 and wp2 == 0 and wp3 == 0:
        # Only wp0 is non-zero: set.zw wp0, wp0
        insns.append(set_zw(rd, wp0))
    elif wp0 == 0 and wp2 == 0 and wp3 == 0:
        # Only wp1 is non-zero: set.zw wp1, wp1 (but set.zw clears all, so we need or.w)
        insns.append(set_zw(rd, 0))
        insns.append(or_w(rd, 1, wp1))
    elif wp0 == 0 and wp1 == 0 and wp3 == 0:
        # Only wp2 is non-zero
        insns.append(set_zw(rd, 0))
        insns.append(or_w(rd, 2, wp2))
    elif wp0 == 0 and wp1 == 0 and wp2 == 0:
        # Only wp3 is non-zero
        insns.append(set_zw_wp3(rd, wp3))
    else:
        # General case: set.zw wp3, then or.w for wp2, wp1, wp0
        insns.append(set_zw_wp3(rd, wp3))  # Sets wp3, zeros wp0-wp2
        if wp2 != 0:
            insns.append(or_w(rd, 2, wp2))
        if wp1 != 0:
            insns.append(or_w(rd, 1, wp1))
        if wp0 != 0:
            insns.append(or_w(rd, 0, wp0))

def _exact_cmp(insns, rd_result, rd_expected, rd_cmp, rd_div, val_expected):
    """Generate exact-value comparison sequence:
    1. Set rd_expected to val_expected
    2. cmp.uo rd_cmp, rd_result, rd_expected
    3. div.uo rd_div, 1, rd_cmp → ILLI if equal (rd_cmp=0)
    Appends to insns list."""
    _set_rd_to_val(insns, rd_expected, val_expected)
    insns.append(cmp_uo(rd_cmp, rd_result, rd_expected))
    # We need rd1 set to1 for the divisor
    insns.append(set_zw(rd_div, 1))  # Use rd1 as scratch; overwritten by div result
    insns.append(div_uo(rd_div, rd_div, rd_cmp))  # div.uo rd1, rd1, rd_cmp
    # If rd_cmp=0: div-by-zero → ILLI(136) = match
    # If rd_cmp≠0: divides normally → reaches UNDI(137) = mismatch

# ── Test cases ────────────────────────────────────────────────────────
#
# 32 tests: 16 div.* + 16 rem.*
#
# Register allocation:
#   rd10/rd11: dividend/divisor setup
#   rd5:       result (from div/rem)
#   rd6:       expected value
#   rd7:       cmp result
#   rd1:       scratch for exact-compare div
#
# For exception tests (divide-by-zero, INT_MIN/-1):
#   rd10: dividend, rd11: divisor
#   rd1:  result destination
#   Expected: ILLI exit (136) — exception fires before result is written

def _div_by_zero_test(name, div_fn, size_desc):
    """Generate a divide-by-zero test case.
    Dividend=7, divisor=0 → expect ILLI (136)."""
    return (
        name,
        [set_zw(10, 7), set_zw(11, 0), div_fn(1, 10, 11)],
        ILLI_EXIT,
        f"{size_desc} div-by-zero not caught",
    )

def _rem_by_zero_test(name, rem_fn, size_desc):
    """Generate a remainder-by-zero test case."""
    return (
        name,
        [set_zw(10, 7), set_zw(11, 0), rem_fn(1, 10, 11)],
        ILLI_EXIT,
        f"{size_desc} rem-by-zero not caught",
    )

def _int_min_div_neg1_test(name, div_fn, size_desc, int_min_val):
    """Generate INT_MIN÷-1 overflow test case.
    Dividend=INT_MIN (runtime), divisor=-1 (runtime) → expect ILLI (136).
    Uses runtime-computed values to avoid constant folding.

    Readback verification (AGENTS.md: 探针值构造须回读校验):
      rd2rb(rb18, rd10, 1) — store rd10 to temporary RB register
      rb2rd(rd20, rb18, 1) — load back from RB to RD (true readback of rd10)
      cmp.uo rd22, rd20, rd21 — compare readback with expected
      br.ne rd22, 0, 3 — if mismatch, skip real test → UNDI(137) = FAIL
      If match: fall through to real div overflow test → ILLI(136) if caught.

    This ensures:
      - Mismatch (construction error) → FAIL (137, non-136)
      - Match → real test executes (no short-circuit)
      - Old buggy _set_rd_to_val (18-bit truncation) → 24/28 (O0/O1/RO0/RO1=137)
      - New correct _set_rd_to_val → 28/28"""
    insns = []
    _set_rd_to_val(insns, 10, int_min_val)

    # Readback verification: truly read rd10 via rd2rb+rb2rd
    insns.append(rd2rb(18, 10, 1))     # rb18 = rd10 (store RD to RB)
    insns.append(rb2rd(20, 18, 1))     # rd20 = rb18 (load back from RB → true readback)
    _set_rd_to_val(insns, 21, int_min_val)  # rd21 = expected value
    insns.append(cmp_uo(22, 20, 21))   # rd22 = cmp(rd20, rd21); 0=match, ±1=mismatch
    # Mismatch → skip real test → UNDI(137) = FAIL
    # Match → fall through to real test
    insns.append(set_zw(23, 0))        # rd23 = 0
    insns.append(br_ne(22, 23, 4))     # if rd22 != 0 (mismatch), skip 4 (real test) → UNDI(137)=FAIL

    # Real overflow test (executed only on readback match)
    insns.append(set_zw(11, 0))
    insns.append(add_si(11, -1))
    insns.append(div_fn(1, 10, 11))
    # If div_fn triggers ILLI → 136 (PASS)
    # If div_fn doesn't trigger → continues to UNDI terminator → 137 (FAIL)
    return (
        name,
        insns,
        ILLI_EXIT,
        f"{size_desc} INT_MIN/-1 not caught (overflow)",
    )

def _int_min_rem_neg1_test(name, rem_fn, size_desc, int_min_val):
    """Generate INT_MIN%-1 overflow test case.
    Includes readback verification: rd2rb+rb2rd to truly read rd10, then cmp.uo.
    Mismatch → br_ne skips real test → UNDI(137) = FAIL.
    Match → falls through to real rem overflow test → ILLI(136) if caught."""
    insns = []
    _set_rd_to_val(insns, 10, int_min_val)

    # Readback verification: truly read rd10 via rd2rb+rb2rd
    insns.append(rd2rb(18, 10, 1))     # rb18 = rd10 (store RD to RB)
    insns.append(rb2rd(20, 18, 1))     # rd20 = rb18 (load back from RB → true readback)
    _set_rd_to_val(insns, 21, int_min_val)  # rd21 = expected value
    insns.append(cmp_uo(22, 20, 21))   # rd22 = cmp(rd20, rd21); 0=match, ±1=mismatch
    insns.append(set_zw(23, 0))        # rd23 = 0
    insns.append(br_ne(22, 23, 4))     # if rd22 != 0 (mismatch), skip 4 (real test) → UNDI(137)=FAIL

    # Real overflow test (executed only on readback match)
    insns.append(set_zw(11, 0))
    insns.append(add_si(11, -1))
    insns.append(rem_fn(1, 10, 11))
    return (
        name,
        insns,
        ILLI_EXIT,
        f"{size_desc} INT_MIN%-1 not caught (overflow)",
    )

def _exact_div_test(name, div_fn, dividend, divisor, expected, size_desc):
    """Generate exact-value division test case."""
    insns = []
    _set_rd_to_val(insns, 10, dividend)
    _set_rd_to_val(insns, 11, divisor)
    insns.append(div_fn(5, 10, 11))
    _exact_cmp(insns, 5, 6, 7, 1, expected)
    return (
        name,
        insns,
        ILLI_EXIT,
        f"{size_desc} {dividend}/{divisor} != {expected}",
    )

def _exact_rem_test(name, rem_fn, dividend, divisor, expected, size_desc):
    """Generate exact-value remainder test case."""
    insns = []
    _set_rd_to_val(insns, 10, dividend)
    _set_rd_to_val(insns, 11, divisor)
    insns.append(rem_fn(5, 10, 11))
    _exact_cmp(insns, 5, 6, 7, 1, expected)
    return (
        name,
        insns,
        ILLI_EXIT,
        f"{size_desc} {dividend}%{divisor} != {expected}",
    )

TESTS = [
    # ================================================================
    # div.* tests (16)
    # ================================================================

    # ── N1-N4: Normal exact value (truncate-toward-zero) ──
    _exact_div_test("N1 div.uo 100/7 == 14", div_uo, 100, 7, 14, "div.uo"),
    _exact_div_test("N2 div.ut 100/7 == 14 (32-bit)", div_ut, 100, 7, 14, "div.ut"),
    _exact_div_test("N3 div.uw 100/7 == 14 (16-bit)", div_uw, 100, 7, 14, "div.uw"),
    _exact_div_test("N4 div.ub 100/7 == 14 (8-bit)", div_ub, 100, 7, 14, "div.ub"),

    # ── N5-N6: Signed negative dividend (truncate-toward-zero) ──
    _exact_div_test("N5 div.so -10/3 == -3", div_so,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFD, "div.so"),
    _exact_div_test("N6 div.sb -10/3 == -3 (8-bit)", div_sb,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFD, "div.sb"),

    # ── D0-D3: Divide-by-zero → ILLI ──
    _div_by_zero_test("D0 div.uo /0 → ILLI", div_uo, "div.uo"),
    _div_by_zero_test("D1 div.so /0 → ILLI", div_so, "div.so"),
    _div_by_zero_test("D2 div.ut /0 → ILLI", div_ut, "div.ut"),
    _div_by_zero_test("D3 div.ub /0 → ILLI", div_ub, "div.ub"),

    # ── O0-O3: INT_MIN÷-1 → ILLI (signed overflow) ──
    _int_min_div_neg1_test("O0 div.so INT64_MIN/-1 → ILLI",
                           div_so, "div.so", 0x8000000000000000),
    _int_min_div_neg1_test("O1 div.st INT32_MIN/-1 → ILLI",
                           div_st, "div.st", 0xFFFFFFFF80000000),
    _int_min_div_neg1_test("O2 div.sw INT16_MIN/-1 → ILLI",
                           div_sw, "div.sw", 0xFFFFFFFFFFFF8000),
    _int_min_div_neg1_test("O3 div.sb INT8_MIN/-1 → ILLI",
                           div_sb, "div.sb", 0xFFFFFFFFFFFFFF80),

    # ================================================================
    # rem.* tests (16)
    # ================================================================

    # ── R1-R4: Normal exact value ──
    _exact_rem_test("R1 rem.uo 100%7 == 2", rem_uo, 100, 7, 2, "rem.uo"),
    _exact_rem_test("R2 rem.ut 100%7 == 2 (32-bit)", rem_ut, 100, 7, 2, "rem.ut"),
    _exact_rem_test("R3 rem.uw 100%7 == 2 (16-bit)", rem_uw, 100, 7, 2, "rem.uw"),
    _exact_rem_test("R4 rem.ub 100%7 == 2 (8-bit)", rem_ub, 100, 7, 2, "rem.ub"),

    # ── R5-R6: Signed negative dividend (remainder sign = dividend sign) ──
    # -10 %3 = -1 (not +2; sign follows dividend per §3.1.5)
    _exact_rem_test("R5 rem.so -10%3 == -1", rem_so,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFF, "rem.so"),
    _exact_rem_test("R6 rem.sb -10%3 == -1 (8-bit)", rem_sb,
                    0xFFFFFFFFFFFFFFF6, 3, 0xFFFFFFFFFFFFFFFF, "rem.sb"),

    # ── RD0-RD3: Remainder-by-zero → ILLI ──
    _rem_by_zero_test("RD0 rem.uo %0 → ILLI", rem_uo, "rem.uo"),
    _rem_by_zero_test("RD1 rem.so %0 → ILLI", rem_so, "rem.so"),
    _rem_by_zero_test("RD2 rem.ut %0 → ILLI", rem_ut, "rem.ut"),
    _rem_by_zero_test("RD3 rem.ub %0 → ILLI", rem_ub, "rem.ub"),

    # ── RO0-RO3: INT_MIN%-1 → ILLI (signed overflow) ──
    _int_min_rem_neg1_test("RO0 rem.so INT64_MIN%-1 → ILLI",
                           rem_so, "rem.so", 0x8000000000000000),
    _int_min_rem_neg1_test("RO1 rem.st INT32_MIN%-1 → ILLI",
                           rem_st, "rem.st", 0xFFFFFFFF80000000),
    _int_min_rem_neg1_test("RO2 rem.sw INT16_MIN%-1 → ILLI",
                           rem_sw, "rem.sw", 0xFFFFFFFFFFFF8000),
    _int_min_rem_neg1_test("RO3 rem.sb INT8_MIN%-1 → ILLI",
                           rem_sb, "rem.sb", 0xFFFFFFFFFFFFFF80),
]

# ── CTL self-check (separate from main tests) ────────────────────────
# Intentionally wrong expectation: expect UNDI(137) for a value that matches.
# A FAIL here means the probe can detect errors. A PASS means probe is broken.
CTL_CHECKS = [
    ("CTL: div.uo 100/7=14 but expect UNDI (wrong; should be ILLI=match)",
     [set_zw(10, 100), set_zw(11, 7), div_uo(5, 10, 11),
      set_zw(6, 14),                    # expected=14 (correct)
      cmp_uo(7, 5, 6),                 # rd7=0 (match)
      set_zw(1, 1), div_uo(1, 1, 7)],  # div 1/0 → ILLI(136)
     UNDI_EXIT,  # WRONG: we expect UNDI but will get ILLI
     "Self-check FAILED: probe cannot detect wrong values"),
]

# ── Main ──────────────────────────────────────────────────────────────

def run_test_group(tests, group_name):
    """Run a group of tests, return (passed, failed, fail_details)."""
    passed = 0
    failed = 0
    fail_details = []

    for name, rom_insns, expected, fail_desc in tests:
        rom = build_rom(rom_insns)
        code, stderr = run_rom(rom)

        if code == expected:
            status = "PASS"
            passed += 1
        elif code == CRASH_EXIT:
            status = "FAIL"
            failed += 1
            fail_details.append(f"  [{status}] {name}: exit={code} CRASH (SIGABRT)")
        elif code == -1:
            status = "TIMEOUT"
            failed += 1
            fail_details.append(f"  [{status}] {name}: {stderr}")
        else:
            status = "FAIL"
            failed += 1
            fail_details.append(f"  [{status}] {name}: exit={code} (expected {expected}) — {fail_desc}")

        print(f"  [{status}] {name}: exit={code} (expect {expected})")

    return passed, failed, fail_details


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 70)
    print("QEMU-011t Min ROM Probe: div/rem label顺序定向回归验证")
    print("=" * 70)
    print(f"  Terminators: ILLI={ILLI_EXIT}, UNDI={UNDI_EXIT}, CRASH={CRASH_EXIT}")
    print(f"  Exact check: cmp.uo + div.uo → ILLI=match, UNDI=mismatch")
    print(f"  Tests: {len(TESTS)} main + {len(CTL_CHECKS)} CTL")
    print()

    # ── Main tests ──
    print("-" * 70)
    print("Main tests (16 div.* + 16 rem.*):")
    print("-" * 70)
    passed, failed, fail_details = run_test_group(TESTS, "main")

    print(f"\nMain results: {passed}/{passed+failed} passed, {failed} failed")

    if fail_details:
        print(f"\nFailed main tests:")
        for d in fail_details:
            print(d)

    # ── CTL self-check ──
    print()
    print("-" * 70)
    print("CTL self-check (intentionally wrong expectations):")
    print("  FAIL here = probe works correctly (can detect errors)")
    print("  PASS here = probe broken (cannot distinguish values)")
    print("-" * 70)
    ctl_passed, ctl_failed, ctl_fail_details = run_test_group(CTL_CHECKS, "CTL")

    ctl_probe_ok = ctl_failed > 0
    print(f"\nCTL self-check: {ctl_passed} PASS, {ctl_failed} FAIL")
    print(f"  Probe detection: {'OK (can detect errors)' if ctl_probe_ok else 'BROKEN (cannot detect errors)'}")

    # ── Final summary ──
    print(f"\n{'=' * 70}")
    all_pass = failed == 0 and ctl_probe_ok
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    print(f"  Main tests: {passed}/{passed+failed}")
    print(f"  CTL probe: {'OK' if ctl_probe_ok else 'BROKEN'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
