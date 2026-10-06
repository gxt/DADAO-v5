#!/usr/bin/env python3
"""Min ROM probe for QEMU-028t: st.* source as rd0/rb0 should not ILLI.

Tests (ADR-0015 D1/D2/D3):
  T1: st.b rd0, [rb17, 0] → stores 0 to memory (rd0 reads as 0)
  T2: st.o rb0, [rb17, 0] → stores non-zero address (rb0 = current insn addr)
  T3: ld.o rd0, [rb17, 0] → still ILLI (destination=0)
  T4: st.o rb0 twice with gap → second address > first (proves rb0 = current insn addr)
  T5: ld.ub rdX, [rb0, 0] → no alignment issue; load succeeds (rb0 as base)

CTL self-check:
  CTL1: st.o rd0 expects ILLI (wrong; should PASS) → probe broken if passes
  CTL2: fence expects PASS (wrong) → probe broken if passes

Exit codes: PASS=0, ILLI=136(0x88), UNDI=137(0x89), CRASH=134

Usage: python3 tools/qemu/min_rom_probe_028t.py
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

def encode_rrii(op, ha, hb, hc, hd):
    """Encode an rrii-format instruction: op[31:24] ha[23:18] hb[17:12] hc[11:6] hd[5:0]"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_rwii(op, ha, wpN, immu16):
    """Encode an rwii-format instruction"""
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_orrr(op, ha, hb, hc, hd):
    """Encode an orrr-format instruction"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

def encode_oiii(op, ha, immu18):
    """Encode an oiii-format instruction"""
    return struct.pack('>I', (op << 24) | (ha << 18) | (immu18 & 0x3FFFF))

# ── Instruction mnemonics ─────────────────────────────────────────────

def set_zw(rd, immu16):
    """set.zw rd, wp0, immu16 — rd[15:0]=immu16, rest=0"""
    return encode_rwii(0x4C, rd, 0, immu16)

def set_zw_wp3(rd, immu16):
    """set.zw rd, wp3, immu16 — rd[63:48]=immu16, rest=0"""
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (3 << 4) | hi4
    return struct.pack('>I', (0x4C << 24) | (rd << 18) | (hb << 12) | (mid6 << 6) | lo6)

def or_w(rd, wpN, immu16):
    """or.w rd, wpN, immu16 — rd[wyde(wpN)] |= immu16"""
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (0x48 << 24) | (rd << 18) | (hb << 12) | (mid6 << 6) | lo6)

def st_b(rdha, rbhb, imms12):
    """st.b rdha, rbhb, imms12 (op=0x18, rrii) — store byte"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x18, rdha, rbhb, hc, hd)

def st_o(rdha, rbhb, imms12):
    """st.o rdha, rbhb, imms12 (op=0x21, rrii) — store octa (RD source)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)

def st_o_rb(rbha, rbhb, imms12):
    """st.o rbha, rbhb, imms12 (op=0x23, rrii) — store octa (RB source)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x23, rbha, rbhb, hc, hd)

def ld_o(rdha, rbhb, imms12):
    """ld.o rdha, rbhb, imms12 (op=0x20, rrii) — load octa (RD dest)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x20, rdha, rbhb, hc, hd)

def ld_ub(rdha, rbhb, imms12):
    """ld.ub rdha, rbhb, imms12 (op=0x10, rrii) — load unsigned byte (no align)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x10, rdha, rbhb, hc, hd)

def cmp_uo(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd — unsigned octa compare → -1/0/1"""
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def div_uo(rdhb, rdhc, rdhd):
    """div.uo rdhb, rdhc, rdhd — unsigned octa divide"""
    return encode_orrr(0x40, 0x38, rdhb, rdhc, rdhd)

def fence():
    """fence — trigger ILLI exception (exit=136)"""
    return encode_oiii(0x77, 0x00, 0)

# ── Terminators and ROM builder ───────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

def build_rom(test_insns):
    """Build ROM: [trampoline | test_insns | UNDI | padding].
    Trampoline (7 insns = 28 bytes):
      rd1=0, rd18=0(PASS), rd19=1(FAIL)
      rb16=exit port (0xFFFF_8000_0000)
      rb17=RAM base (0xFFFF_00FE_0000)
    """
    trampoline = [
        set_zw(1, 0),                          # rd1 = 0 (scratch)
        set_zw(18, 0),                          # rd18 = 0 (PASS value)
        set_zw(19, 1),                          # rd19 = 1 (FAIL value)
        # rb16 = exit port (0xFFFF_8000_0000)
        encode_rwii(0x4E, 16, 2, 0xFFFF),      # set.zw rb16, wp2, 0xFFFF
        encode_rwii(0x4A, 16, 1, 0x8000),       # or.w rb16, wp1, 0x8000
        # rb17 = RAM base (0xFFFF_00FE_0000) for st/ld stores
        encode_rwii(0x4E, 17, 2, 0xFFFF),      # set.zw rb17, wp2, 0xFFFF
        encode_rwii(0x4A, 17, 1, 0x00FE),       # or.w rb17, wp1, 0x00FE
    ]
    rom = b''.join(trampoline) + b''.join(test_insns) + UNDI_TERMINATOR
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
             '-bios', rom_path, '-kernel', kernel_path],
            capture_output=True, timeout=timeout, text=True)
        return result.returncode, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    finally:
        os.unlink(rom_path); os.unlink(kernel_path)

# ── Exit codes ────────────────────────────────────────────────────────

PASS_EXIT = 0; ILLI_EXIT = 136; UNDI_EXIT = 137; CRASH_EXIT = 134

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

def _exact_cmp(insns, rd_result, rd_expected, rd_cmp, rd_div, val_expected):
    """Compare rd_result with val_expected; ILLI=match, UNDI=mismatch."""
    _set_rd_to_val(insns, rd_expected, val_expected)
    insns.append(cmp_uo(rd_cmp, rd_result, rd_expected))
    insns.append(set_zw(rd_div, 1))
    insns.append(div_uo(rd_div, rd_div, rd_cmp))

# ── Test case builders ────────────────────────────────────────────────

def make_t1_st_b_rd0():
    """T1: st.b rd0, [rb17, 0] → stores 0 to RAM (rd0 reads as 0).
    Read back with ld.o and compare with 0 → ILLI if equal (PASS).

    Branch: no conditional branches. The div.uo is the comparison.
    Two outcomes:
      - st.b rd0 stores 0 → ld.o reads 0 → cmp.uo=0 → div 1/0 → ILLI(136)=PASS
      - st.b rd0 stores non-zero → ld.o reads non-zero → cmp.uo≠0 → div 1/nz → reaches UNDI(137)=FAIL
    """
    insns = [
        st_b(0, 17, 0),              # st.b rd0, [rb17, 0] → writes 0
        ld_o(3, 17, 0),              # rd3 = mem64[rb17+0] (only byte 0 = 0)
    ]
    _exact_cmp(insns, 3, 4, 5, 6, 0)
    return ("T1: st.b rd0 stores 0 → readback==0",
            insns, ILLI_EXIT,
            "st.b rd0 should store 0 (rd0 reads as 0)")

def make_t2_st_o_rb0():
    """T2: st.o rb0, [rb17, 0] → stores non-zero address (rb0 = current insn addr).
    Read back and verify it's non-zero.

    Branch: no conditional branches. Two outcomes:
      - stored value != 0 → cmp.uo ≠ 0 → div 1/nz → UNDI(137)=PASS
      - stored value == 0 → cmp.uo = 0 → div 1/0 → ILLI(136)=FAIL
    """
    insns = [
        st_o_rb(0, 17, 0),           # st.o rb0, [rb17, 0] → stores current insn addr
        ld_o(3, 17, 0),              # rd3 = stored value
    ]
    _set_rd_to_val(insns, 4, 0)      # rd4 = 0
    insns.append(cmp_uo(5, 3, 4))    # rd5 = 0 if stored==0 (BAD)
    insns.append(set_zw(6, 1))
    insns.append(div_uo(6, 6, 5))    # div 1/0 → ILLI if stored==0 (FAIL)
    # div 1/1 → reaches UNDI (PASS: stored addr is non-zero)
    return ("T2: st.o rb0 stores non-zero address",
            insns, UNDI_EXIT,
            "st.o rb0 should store current insn addr (non-zero)")

def make_t3_ld_rd0_illi():
    """T3: ld.o rd0, [rb17, 0] → still ILLI (destination=0).

    Two outcomes:
      - ILLI fires → exit=136=PASS (correct behavior)
      - No ILLI → reaches UNDI=137=FAIL (bug: should have ILLI'd)
    """
    insns = [
        ld_o(0, 17, 0),              # ld.o rd0, [rb17, 0] → ILLI
    ]
    return ("T3: ld.o rd0 dest=0 still ILLI",
            insns, ILLI_EXIT,
            "ld.o rd0 should still ILLI (destination=0)")

def make_t4_st_o_rb0_addr_order():
    """T4: st.o rb0 twice with known gap → second address > first.
    This proves rb0 = current instruction address (changes with PC).

    Trampoline = 28 bytes (7 insns). Then T4 starts:
      insn0: st.o rb0, [rb17, 0]    ← rb0 = 28 (address of this insn)
      insn1: set.zw rd2, 0           ← padding
      insn2: set.zw rd2, 0           ← padding
      insn3: st.o rb0, [rb17, 8]    ← rb0 = 40 (address of this insn)

    After: rd3 = mem[rb17+0] = 28, rd4 = mem[rb17+8] = 40
    Verify: rd4 > rd3 (cmp.uo returns 1, not 0 or -1)

    Two outcomes:
      - rd4 > rd3 → cmp.uo=1 → cmp with expected=1 → 0 → div 1/0 → ILLI(136)=PASS
      - rd4 <= rd3 → cmp.uo≠1 → cmp≠0 → div 1/nz → UNDI(137)=FAIL

    Branch offset: br_ne used to skip UNDI on mismatch. But we can use the
    div-by-zero trick instead. Let me re-think.
    
    Actually simpler: verify rd3 = expected_addr1 (28) AND rd4 = expected_addr2 (40).
    But we don't know the ROM base at probe generation time.
    
    Better: verify rd4 - rd3 = 12 (3 insns gap = 12 bytes).
    Use: rd5 = rd4 - rd3. But we don't have subtract.
    Use: cmp.uo rd5, rd4, rd3 → rd5=1 (rd4>rd3).
    Then verify rd5=1 by comparing with expected=1.

    Two outcomes (for cmp.uo rd5, rd4, rd3):
      - rd4 > rd3 (correct gap): rd5 = 1
      - rd4 == rd3 (no gap): rd5 = 0
      - rd4 < rd3 (reversed): rd5 = -1

    Then: cmp.uo rd6, rd5, 1 → rd6=0 if rd5=1 (PASS)
    Then: div.uo rd7, 1, rd6 → ILLI if rd6=0 (PASS)

    Branch verification: no conditional branches in this test.
    """
    insns = [
        st_o_rb(0, 17, 0),           # insn0: st.o rb0, [rb17, 0]
        set_zw(2, 0),                 # insn1: padding
        set_zw(2, 0),                 # insn2: padding
        st_o_rb(0, 17, 8),           # insn3: st.o rb0, [rb17, 8]
        ld_o(3, 17, 0),              # rd3 = addr of insn0
        ld_o(4, 17, 8),              # rd4 = addr of insn3
        # Verify rd4 > rd3 (proves rb0 = current insn addr, changes with PC)
        cmp_uo(5, 4, 3),             # rd5 = 1 (rd4 > rd3)
    ]
    _set_rd_to_val(insns, 6, 1)      # rd6 = 1
    insns.append(cmp_uo(7, 5, 6))    # rd7 = 0 if rd5==1 (correct)
    insns.append(set_zw(8, 1))
    insns.append(div_uo(8, 8, 7))    # div 1/0 → ILLI if rd7=0 (PASS)
    return ("T4: st.o rb0 addr order (second > first)",
            insns, ILLI_EXIT,
            "st.o rb0 should store increasing addresses")

def make_t5_ld_rb0_base():
    """T5: ld.ub rdX, [rb0, 0] → rb0 as base register for load.
    Uses ld.ub (unsigned byte, no alignment requirement) to avoid MALIGN.

    Since rb0 = current insn address, ld.ub loads the first byte of the
    ld.ub instruction itself (which is non-zero). Verify non-zero.

    Trampoline = 28 bytes. T5 starts with some insns before ld.ub.
    Let's count: T5 insns before ld.ub:
      st_o_rb(0, 17, 0)  = 4 bytes (insn0)
      ld_o(3, 17, 0)     = 4 bytes (insn1)
      set_zw(4, 0)        = 4 bytes (insn2)
    So ld.ub is at offset 28+12 = 40 from ROM base.

    ld.ub rd5, [rb0, 0]  = insn3 (at offset 40)
    rb0 = 40 at this point
    ld.ub loads byte at address 40 = first byte of the ld.ub instruction
    The first byte of ld.ub = op(0x10) << 24 → byte[0] = 0x10 >> 16 = ... wait.

    Actually, instructions are stored big-endian. ld.ub rd5, [rb0, 0] with
    op=0x10, ha=5, hb=0(rb0), hc=0, hd=0:
    encoding = 0x10 | (5<<18) | (0<<12) | (0<<6) | 0
    But op is in bits[31:24], ha in [23:18], etc.
    So the 4-byte encoding = (0x10 << 24) | (5 << 18) | (0 << 12) | (0 << 6) | 0
    = 0x10140000
    Big-endian bytes: [0x10, 0x14, 0x00, 0x00]
    First byte = 0x10 = 16

    So ld.ub rd5, [rb0, 0] loads byte 0x10 (16) into rd5.
    Verify rd5 = 16 → ILLI if match, UNDI if mismatch.

    Two outcomes:
      - rd5 = 16 (correct load from rb0) → cmp.uo=0 → div 1/0 → ILLI(136)=PASS
      - rd5 ≠ 16 → cmp.uo≠0 → div 1/nz → UNDI(137)=FAIL
    """
    insns = [
        # First store rb0 to memory so we can check it's non-zero
        st_o_rb(0, 17, 0),           # st.o rb0, [rb17, 0]
        ld_o(3, 17, 0),              # rd3 = rb0 value (non-zero addr)
        set_zw(4, 0),                 # rd4 = 0
    ]
    # Now the key test: ld.ub rd5, [rb0, 0]
    insns.append(ld_ub(5, 0, 0))     # ld.ub rd5, [rb0, 0] — loads first byte at rb0 addr
    # rd5 should be 0x10 (first byte of this ld.ub instruction)
    _exact_cmp(insns, 5, 6, 7, 8, 0x10)
    return ("T5: ld.ub rdX, [rb0, 0] loads insn byte = 0x10",
            insns, ILLI_EXIT,
            "ld.ub [rb0, 0] should load first byte of ld.ub insn (0x10)")

# ── Test definitions ──────────────────────────────────────────────────

def make_t6_st_o_rd0_no_illi():
    """T6: st.o rd0, [rb17, 0] → should NOT ILLI (rd0 is source, reads as 0).
    This is the direct counterexample test for the fix.
    If ha==0 check is present → ILLI(136)=FAIL
    If ha==0 check is removed → stores 0, reaches UNDI(137)=PASS

    Two outcomes:
      - No ILLI (fix applied) → st.o succeeds → UNDI(137)=PASS
      - ILLI (regression) → exit=136=FAIL
    """
    insns = [
        st_o(0, 17, 0),              # st.o rd0, [rb17, 0] → should store 0
        # If st.o rd0 succeeded, write exit port: st.o rd18, rb16, 0 (rd18=0 → PASS)
        st_o(18, 16, 0),
    ]
    return ("T6: st.o rd0 should NOT ILLI (counterexample gate)",
            insns, PASS_EXIT,
            "st.o rd0 should NOT ILLI (rd0 is source)")

TESTS = [
    make_t1_st_b_rd0(),
    make_t2_st_o_rb0(),
    make_t3_ld_rd0_illi(),
    make_t4_st_o_rb0_addr_order(),
    make_t5_ld_rb0_base(),
    make_t6_st_o_rd0_no_illi(),
]

CTL_CHECKS = [
    ("CTL1: st.o rd0 expects ILLI (wrong; should PASS)",
     [st_o(0, 17, 0), st_o(0, 16, 0)],  # st.o rd0 should succeed
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect st.o rd0 PASS vs ILLI"),
    ("CTL2: fence expects PASS (wrong)",
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
        code, stderr = run_test(rom, timeout=15)
        if code == expected:
            status = "PASS"; passed += 1
        elif code == 124:
            status = "TIMEOUT"; failed += 1
            fail_details.append(f"  [TIMEOUT] {name}: {fail_desc}")
        else:
            status = "FAIL"; failed += 1
            fail_details.append(f"  [FAIL] {name}: exit=0x{code:02X} (expect 0x{expected:02X}) — {fail_desc}")
        print(f"  [{status}] {name}: exit=0x{code:02X} (expect 0x{expected:02X})")
    return passed, failed, fail_details

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 70)
    print("QEMU-028t Min ROM Probe: st.* source=rd0/rb0 should not ILLI")
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
