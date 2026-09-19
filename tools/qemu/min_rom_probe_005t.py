#!/usr/bin/env python3
"""Min ROM probe for QEMU-005t RD integer semantics (v3).

Changes from v2:
- N2 fix: helper_raise_exception now uses cpu_loop_exit_restore(GETPC()),
  so INT_MIN/-1 deterministically exits 136 (no TB replay).
- div.sb N2 test: use correct div.sb encoding (op=0x43) instead of div_so (op=0x40).
- mul_sb: opcode fixed from 0x25 to 0x31 (matching opcodes.yaml).
- swym: opcode fixed from 0x7C to 0x77.
- CTL self-check: separated from main pass/fail count (self-check FAIL = probe works).
- Exact value comparison: cmp.uo + div.uo for precise equality checks.

Value comparison method (exact):
  1. Compute result
  2. Load expected value
  3. cmp.uo rdR, result, expected → rdR=0 if equal, ±1 if not
  4. div.uo rdX, 1, rdR → if rdR==0: divide-by-zero → ILLI(136); else → UNDI(137)
  So: ILLI(136) = values match, UNDI(137) = values differ.

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
    """Encode an rrrr-format instruction: op[31:24] rdha[23:18] rdhb[17:12] rdhc[11:6] rdhd[5:0]"""
    return struct.pack('>I', (op << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd)

def encode_orrr(op, ha, hb, hc, hd):
    """Encode an orrr-format instruction: op[31:24] ha[23:18] hb[17:12] hc[11:6] hd[5:0]"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_orri(op, ha, hb, hc, immu6):
    """Encode an orri-format instruction"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | (immu6 & 0x3F))

def encode_riii(op, ha, imms18):
    """Encode an riii-format instruction (18-bit signed immediate)"""
    imm = imms18 & 0x3FFFF  # 18 bits
    return struct.pack('>I', (op << 24) | (ha << 18) | imm)

def encode_rwii(op, ha, wpN, immu16):
    """Encode an rwii-format instruction"""
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_oiii(op, ha, immu18):
    """Encode an oiii-format instruction"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw(rd, immu16):
    """set.zw rd, wp0, immu16 — set rd[15:0]=immu16, rest=0"""
    return encode_rwii(0x4C, rd, 0, immu16)

def add_si(rd, imms18):
    """add.si rd, imms18 — rd += sign_extend(imms18)"""
    return encode_riii(0x59, rd, imms18 & 0x3FFFF)

def div_uo(rdhb, rdhc, rdhd):
    """div.uo rdhb, rdhc, rdhd — unsigned 64-bit divide (MISC-octa orrr)
    op=0x40, ha=0x38"""
    return encode_orrr(0x40, 0x38, rdhb, rdhc, rdhd)

def div_so(rdhb, rdhc, rdhd):
    """div.so rdhb, rdhc, rdhd — signed 64-bit divide (MISC-octa orrr)
    op=0x40, ha=0x39"""
    return encode_orrr(0x40, 0x39, rdhb, rdhc, rdhd)

def div_sb(rdhb, rdhc, rdhd):
    """div.sb rdhb, rdhc, rdhd — signed 8-bit divide (MISC-byte orrr)
    op=0x43, ha=0x39"""
    return encode_orrr(0x43, 0x39, rdhb, rdhc, rdhd)

def rem_uo(rdhb, rdhc, rdhd):
    """rem.uo rdhb, rdhc, rdhd — unsigned 64-bit remainder (MISC-octa orrr)
    op=0x40, ha=0x3A"""
    return encode_orrr(0x40, 0x3A, rdhb, rdhc, rdhd)

def rem_so(rdhb, rdhc, rdhd):
    """rem.so rdhb, rdhc, rdhd — signed 64-bit remainder (MISC-octa orrr)
    op=0x40, ha=0x3B"""
    return encode_orrr(0x40, 0x3B, rdhb, rdhc, rdhd)

def cmp_uo(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd — unsigned 64-bit compare → -1/0/1
    op=0x40, ha=0x2A"""
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def ext_ub_orri(rdhb, rdhc, immu6):
    """ext.ub rdhb, rdhc, immu6 — zero-extend byte from bit immu6 (orri)
    op=0x43, ha=0x18"""
    return encode_orri(0x43, 0x18, rdhb, rdhc, immu6)

def ext_sb_orri(rdhb, rdhc, immu6):
    """ext.sb rdhb, rdhc, immu6 — sign-extend byte from bit immu6 (orri)
    op=0x43, ha=0x19"""
    return encode_orri(0x43, 0x19, rdhb, rdhc, immu6)

def ext_ub_orrr(rdhb, rdhc, rdhd):
    """ext.ub rdhb, rdhc, rdhd — zero-extend byte from bit rdhd (orrr)
    op=0x43, ha=0x10"""
    return encode_orrr(0x43, 0x10, rdhb, rdhc, rdhd)

def ext_sb_orrr(rdhb, rdhc, rdhd):
    """ext.sb rdhb, rdhc, rdhd — sign-extend byte from bit rdhd (orrr)
    op=0x43, ha=0x11"""
    return encode_orrr(0x43, 0x11, rdhb, rdhc, rdhd)

def ext_so_orri(rdhb, rdhc, immu6):
    """ext.so rdhb, rdhc, immu6 — sign-extend octa from bit immu6 (orri)
    op=0x40, ha=0x19"""
    return encode_orri(0x40, 0x19, rdhb, rdhc, immu6)

def add_sb(rdhb, rdhc, rdhd):
    """add.sb rdhb, rdhc, rdhd — signed 8-bit add, sign-extend result
    MISC-byte orrr: op=0x43, ha=0x21"""
    return encode_orrr(0x43, 0x21, rdhb, rdhc, rdhd)

def add_ub(rdhb, rdhc, rdhd):
    """add.ub rdhb, rdhc, rdhd — unsigned 8-bit add, zero-extend result
    MISC-byte orrr: op=0x43, ha=0x20"""
    return encode_orrr(0x43, 0x20, rdhb, rdhc, rdhd)

def mul_sb(rdhb, rdhc, rdhd):
    """mul.sb rdhb, rdhc, rdhd — signed 8-bit multiply, sign-extend result
    MISC-byte orrr: op=0x43, ha=0x31"""
    return encode_orrr(0x43, 0x31, rdhb, rdhc, rdhd)

def shl_uo_orri(rdhb, rdhc, immu6):
    """shl.uo rdhb, rdhc, immu6 — left shift octa by immediate (orri)
    op=0x40, ha=0x1C"""
    return encode_orri(0x40, 0x1C, rdhb, rdhc, immu6)

def shr_uo_orri(rdhb, rdhc, immu6):
    """shr.uo rdhb, rdhc, immu6 — logical right shift octa by immediate (orri)
    op=0x40, ha=0x1A"""
    return encode_orri(0x40, 0x1A, rdhb, rdhc, immu6)

def illi():
    """illi — trigger ILLI exception (exit=136)"""
    return encode_oiii(0x00, 0x00, 0)

def swym():
    """swym 0 — NOP (op=0x77)"""
    return encode_oiii(0x77, 0x00, 0)

# ── Terminators ───────────────────────────────────────────────────────

# UNDI = undefined instruction exception = exit 137 (0x89)
# Using reserved encoding 0x08040001 which decodes as UNDI.
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

ILLI_EXIT = 136   # 0x88 — runtime ILLI exception
UNDI_EXIT = 137   # 0x89 — reached UNDI terminator (normal completion)
CRASH_EXIT = 134  # 0x86 — SIGABRT (regression)

# ── Test cases ────────────────────────────────────────────────────────
#
# Exact value comparison (v3):
#   cmp.uo rdR, result, expected → rdR=0 if equal, ±1 if not
#   div.uo rdX, 1, rdR → if rdR==0: div-by-zero → ILLI(136); else → UNDI(137)
#   So: ILLI(136) = exact match, UNDI(137) = mismatch.
#
# Exception check: code that should trigger ILLI → expect 136.
#   If it completes → UNDI(137) = FAIL.
#

TESTS = [
    # ── N1: div.uo/rem.uo result correctness (exact values) ──
    # div.uo 100/7 = 14 (exact check)
    ("N1 div.uo 100/7 == 14 (exact)",
     [set_zw(10, 100), set_zw(11, 7), div_uo(5, 10, 11),   # rd5 = 100/7 = 14
      set_zw(6, 14),                                          # rd6 = expected 14
      cmp_uo(7, 5, 6),                                        # rd7 = 0 if equal
      div_uo(1, 7, 7)],                                       # div-by-zero if rd7==0
     ILLI_EXIT,
     "div.uo 100/7 != 14 — N1 bug (gen_zero_extend UB)"),

    # rem.uo 100%7 = 2 (exact check)
    ("N1 rem.uo 100%7 == 2 (exact)",
     [set_zw(10, 100), set_zw(11, 7), rem_uo(5, 10, 11),   # rd5 = 100%7 = 2
      set_zw(6, 2),                                           # rd6 = expected 2
      cmp_uo(7, 5, 6),                                        # rd7 = 0 if equal
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "rem.uo 100%7 != 2 — N1 bug"),

    # Regression: div.uo 0/7 == 0 (exact check)
    ("N1 div.uo 0/7 == 0 (exact, regression)",
     [set_zw(10, 0), set_zw(11, 7), div_uo(5, 10, 11),     # rd5 = 0/7 = 0
      set_zw(6, 0),                                           # rd6 = expected 0
      cmp_uo(7, 5, 6),                                        # rd7 = 0 if equal
      div_uo(1, 7, 7)],                                       # div-by-zero if rd7==0
     ILLI_EXIT,
     "div.uo 0/7 != 0 (unexpected)"),

    # ── N2: INT_MIN ÷ -1 runtime ILLI ──
    # div.so INT_MIN/-1 (computed divisor) → ILLI
    # With cpu_loop_exit_restore fix, this should deterministically exit 136.
    ("N2 div.so INT64_MIN/-1 (computed divisor) → ILLI",
     [encode_rwii(0x4C, 2, 3, 0x8000),  # set.zw rd2, wp3, 0x8000 → INT64_MIN
       add_si(3, -1),                      # rd3 = -1 (runtime computed)
       div_so(1, 2, 3)],
     ILLI_EXIT,
     "INT64_MIN/-1 not caught — N2 bug"),

    # div.sb INT8_MIN/-1 (computed divisor) → ILLI
    # Uses correct div.sb encoding (op=0x43, ha=0x39), NOT div_so (op=0x40).
    ("N2 div.sb INT8_MIN/-1 (computed divisor) → ILLI",
     [set_zw(2, 0x0080),  # rd2 = 128
      add_si(2, -256),     # rd2 = -128 = INT8_MIN
      set_zw(3, 0), add_si(3, -1),  # rd3 = -1 (computed)
      div_sb(1, 2, 3)],    # div.sb: op=0x43, ha=0x39
     ILLI_EXIT,
     "INT8_MIN/-1 not caught — N2 bug (div.sb)"),

    # ── B1: Legal div/rem regression (must NOT crash) ──
    ("B1 legal div.uo completes normally",
     [set_zw(10, 100), set_zw(11, 7), div_uo(5, 10, 11)],
     UNDI_EXIT,
     "Legal div.uo crashed (B1 regression: SIGABRT)"),

    ("B1 legal rem.uo completes normally",
     [set_zw(10, 100), set_zw(11, 7), rem_uo(5, 10, 11)],
     UNDI_EXIT,
     "Legal rem.uo crashed (B1 regression)"),

    ("B1 legal div.so completes normally",
     [set_zw(2, 0xFFF2), add_si(2, -14),  # rd2 = -14
      set_zw(3, 3), div_so(1, 2, 3)],
     UNDI_EXIT,
     "Legal div.so crashed (B1 regression)"),

    # ── B2: ext.*_orrr hd>N → ILLI ──
    ("B2 ext.ub orrr rdhd=8 (>N=7) → ILLI",
     [set_zw(2, 0xFF),    # rd2 = source
      set_zw(3, 8),       # rd3 = 8 (> N=7)
      ext_ub_orrr(1, 2, 3)],
     ILLI_EXIT,
     "ext.ub orrr hd=8 not caught — B2 bug"),

    ("B2 ext.ub orri rdhd=8 (>N=7) → ILLI (control)",
     [set_zw(2, 0xFF),
      ext_ub_orri(1, 2, 8)],
     ILLI_EXIT,
     "ext.ub orri hd=8 not caught (unexpected)"),

    ("B2 ext.ub orrr rdhd=2 (legal) completes",
     [set_zw(2, 0xFF),
      set_zw(3, 2),
      ext_ub_orrr(1, 2, 3)],
     UNDI_EXIT,
     "ext.ub orrr hd=2 failed (unexpected)"),

    # ── B3: Fixed-width sign/zero extension (exact values) ──
    # add.sb 0x40+0x40 = 0x80 → sign-extended = 0xFF...80 = -128
    ("B3 add.sb 0x40+0x40 == -128 (exact)",
     [set_zw(2, 0x0040), set_zw(3, 0x0040), add_sb(5, 2, 3),  # rd5 = sign_ext(0x80) = -128
      set_zw(6, 0x0080), add_si(6, -256),                       # rd6 = 128 - 256 = -128
      cmp_uo(7, 5, 6),                                           # rd7 = 0 if equal
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "add.sb 0x40+0x40 != -128 (sign-extend wrong)"),

    # mul.sb 0x0A * -2 = -20 → sign-extended = 0xFF...EC
    ("B3 mul.sb 10 * -2 == -20 (exact)",
     [set_zw(2, 0x000A), set_zw(3, 0), add_si(3, -2), mul_sb(5, 2, 3),  # rd5 = sign_ext(-20)
      set_zw(6, 0), add_si(6, -20),                                       # rd6 = -20
      cmp_uo(7, 5, 6),                                                    # rd7 = 0 if equal
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "mul.sb 10*-2 != -20 (sign-extend wrong)"),

    # ── B4: ext high-bit fill (exact values) ──
    # ext.ub pos=2: zero_extend(0xFF[2:0]) = 0x7
    ("B4 ext.ub orri pos=2 == 0x7 (exact)",
     [set_zw(2, 0x00FF), ext_ub_orri(1, 2, 2),  # rd1 = 0x7
      set_zw(6, 7),
      cmp_uo(7, 1, 6),
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "ext.ub pos=2 != 0x7 (wrong)"),

    # ext.sb pos=2: sign_extend(0xF[2:0]) = sign_ext(0x3)
    # ext.sb preserves rdhb[63:8], so we must init rd1 with high bits set.
    # With rd1=-1 first: rd1[7:0]=0xFF, rd1[63:8]=0xFF...FF → rd1=-1
    ("B4 ext.sb orri pos=2 == -1 (exact, high bits preserved)",
     [set_zw(2, 0x000F),
      set_zw(1, 0), add_si(1, -1),                # rd1 = -1 (all ones, sets high bits)
      ext_sb_orri(1, 2, 2),                       # rd1 = sign_ext(0x3), high bits preserved
      set_zw(6, 0), add_si(6, -1),               # rd6 = -1
      cmp_uo(7, 1, 6),
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "ext.sb pos=2 != -1 (wrong)"),

    # ext.so pos=2: sign_extend(0xF[2:0]) = -1
    ("B4 ext.so orri pos=2 == -1 (exact)",
     [set_zw(2, 0x000F), ext_so_orri(1, 2, 2),  # rd1 = sign_ext(0x3) = -1
      set_zw(6, 0), add_si(6, -1),
      cmp_uo(7, 1, 6),
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "ext.so pos=2 != -1 (wrong)"),

    # ── Shift (exact values) ──
    # shl.uo 0xF << 4 = 0xF0
    ("shl.uo 0xF << 4 == 0xF0 (exact)",
     [set_zw(2, 0x000F), shl_uo_orri(1, 2, 4),  # rd1 = 0xF0
      set_zw(6, 0x00F0),
      cmp_uo(7, 1, 6),
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "shl.uo 0xF<<4 != 0xF0 (wrong)"),

    # shr.uo 0xF0 >> 4 = 0x0F
    ("shr.uo 0xF0 >> 4 == 0x0F (exact)",
     [set_zw(2, 0x00F0), shr_uo_orri(1, 2, 4),  # rd1 = 0x0F
      set_zw(6, 0x000F),
      cmp_uo(7, 1, 6),
      div_uo(1, 7, 7)],
     ILLI_EXIT,
     "shr.uo 0xF0>>4 != 0x0F (wrong)"),

    # ── div by zero ──
    ("div.uo /0 (constant) → ILLI",
     [set_zw(2, 7), set_zw(3, 0), div_uo(1, 2, 3)],
     ILLI_EXIT,
     "div by zero not caught (unexpected)"),

    ("div.uo /0 (computed) → ILLI",
     [set_zw(2, 7), set_zw(3, 0), add_si(3, 0), div_uo(1, 2, 3)],
     ILLI_EXIT,
     "div by zero (computed) not caught (unexpected)"),
]

# ── CTL self-check (separate from main tests) ────────────────────────
# These are intentionally wrong expectations. A FAIL here means the probe
# can detect semantic errors (good). A PASS means the probe can't distinguish
# (bad — indicates the probe method is broken).
CTL_CHECKS = [
    # ext.ub pos=2 → 0x7 (≠0). If we expect UNDI(137) but cmp gives ILLI(136),
    # that means 0x7 == 0x7 (match). So expecting UNDI is WRONG → should FAIL.
    ("CTL self-check: ext.ub=7 but expect UNDI (wrong, should be ILLI=match)",
     [set_zw(2, 0xFF), ext_ub_orri(1, 2, 2),   # rd1 = 0x7
      set_zw(6, 7),                               # rd6 = 7 (expected)
      cmp_uo(7, 1, 6),                            # rd7 = 0 (match)
      div_uo(1, 7, 7)],                           # div-by-zero → ILLI(136)
     UNDI_EXIT,  # WRONG expectation: we expect UNDI but will get ILLI
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
    print("QEMU-005t Min ROM Probe (v3: exact values + N2 fix + CTL separated)")
    print("=" * 70)
    print(f"  Terminators: ILLI={ILLI_EXIT}, UNDI={UNDI_EXIT}, CRASH={CRASH_EXIT}")
    print(f"  Exact check: cmp.uo + div.uo → ILLI=match, UNDI=mismatch")
    print()

    # ── Main tests ──
    print("-" * 70)
    print("Main tests:")
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

    # For CTL: FAIL is the expected outcome (probe detects the wrong expectation)
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
