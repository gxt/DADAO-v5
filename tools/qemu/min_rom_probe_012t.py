#!/usr/bin/env python3
"""Min ROM probe for QEMU-012t: Branch PC formula + call RA §5.6.1 directed regression.

Architecture: test code runs from ROM (same as 008t/011t probe pattern).
Kernel binary provides test data (loaded at RAM base).

Tests cover:
  B1: Branch taken positive offset (br.nz rd, +3)
  B2: Branch taken negative offset (br.nz rd, -1 backward loop)
  B3: Branch not-taken → fall through to next instruction
  B4: Branch taken with br.eq (two-register)
  B5: Branch taken with br.z-rb (RB register)
  C1: call-iiii return address = call+1 (via ret→landing)
  C2: call-rrii return address = call+1 (via ret→landing)
  C3: call→ret→landing round-trip (basic RA push/pop)
  R1: RA §5.6.1 case 1 — cold push (round-trip; exact high16 checked via -d cpu)
  R2: RA §5.6.1 case 2 — same-address recursion (refcount increments, no overflow)
  R2b: RA §5.6.1 case 3 — distinct-address deep chain (depth overflow → RASOF)
  R3: RA §5.6.1 case 3 — different address (shift-down push)
  R4: RA §5.6.1 case 1+3 combined — nested call/ret (2 levels, shift push/pop)

Exit codes (ADR-0004 D5.8):
  0x00 = PASS, 0x88 = ILLI, 0x89 = UNDI, 0x8A = RASOF, 0x8B = RASUF

Usage: python3 tools/qemu/min_rom_probe_012t.py
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

def set_zw_rb(rb, immu16):
    return encode_rwii(0x4E, rb, 0, immu16)

def or_w_rb(rb, wpN, immu16):
    return encode_rwii(0x4A, rb, wpN, immu16)

def or_w_rd(rd, wpN, immu16):
    return encode_rwii(0x48, rd, wpN, immu16)

def add_si_rd(rd, imms18):
    return encode_riii(0x59, rd, imms18 & 0x3FFFF)

def st_o_rd(rdha, rbhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)

def cmp_uo_rd(rdhb, rdhc, rdhd):
    """cmp.uo rdhb, rdhc, rdhd (MISC-octa, ha=0x2A)"""
    return encode_orrr(0x40, 0x2A, rdhb, rdhc, rdhd)

def br_nz(rdha, imms18):
    return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)

def br_z(rdha, imms18):
    return encode_riii(0x6A, rdha, imms18 & 0x3FFFF)

def br_eq(rdha, rdhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x6E, rdha, rdhb, hc, hd)

def br_ne(rdha, rdhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x6F, rdha, rdhb, hc, hd)

def br_z_rb(rbha, imms18):
    return encode_riii(0x72, rbha, imms18 & 0x3FFFF)

def br_nz_rb(rbha, imms18):
    return encode_riii(0x73, rbha, imms18 & 0x3FFFF)

def jump_iiii(imms24):
    return encode_iiii(0x70, imms24 & 0xFFFFFF)

def call_iiii(imms24):
    return encode_iiii(0x74, imms24 & 0xFFFFFF)

def call_rrii(rbha, rdhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x75, rbha, rdhb, hc, hd)

def ret_riii(rdha, imms18):
    return encode_riii(0x76, rdha, imms18 & 0x3FFFF)

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

# ── Test cases ────────────────────────────────────────────────────────
# After trampoline: rb16=exit port, rb17=RAM base, rb2=RAM base

TESTS = [
    # ── Branch taken/not-taken tests ──────────────────────────────────
    # Design: set fail register BEFORE branch, then branch + offset controls which store runs.
    #   Taken: branch skips fail_store → lands on pass_set+pass_store (rd=0, exit 0x00)
    #   Not-taken: falls through to fail_store (rd=1, exit 0x01)
    # Key: fail register set BEFORE branch (so it's always available).

    # B1: Branch taken positive offset
    # Layout: setup, br, fail_path, dead, pass_path
    # Formula: target = rb0 + (imm << 2), rb0 = branch instruction address
    # br at idx2: target = idx2*4 + 24 + (4*4) = idx6 (pass_set)
    # Wrong offset (+3): lands on idx5 (dead_store, rd18=1) → exit 0x01
    ("B1 branch taken positive offset (br.nz +4)",
     [set_zw_rd(18, 0x0001),    # idx0: rd18 = 1
      set_zw_rd(19, 0x0001),    # idx1: rd19 = 1 (fail value)
      br_nz(18, 4),             # idx2: br.nz +4 → target = idx6 (pass_set)
      st_o_rd(19, 16, 0),       # idx3: [fail_store] NOT taken: exit 0x01
      set_zw_rd(18, 0x0001),    # idx4: [dead]
      st_o_rd(18, 16, 0),       # idx5: [dead_store] exit 0x01 (wrong offset lands here)
      set_zw_rd(18, 0x0000),    # idx6: [pass_set] correct target
      st_o_rd(18, 16, 0)],      # idx7: [pass_store] exit 0x00
     PASS_EXIT,
     "br.nz taken positive offset failed"),

    # B2: Branch taken negative offset (backward loop)
    # Loop: rd18 starts at 2, decrements; br.nz rd18, -1 loops until rd18=0
    # When rd18=0, br.nz not taken → fall through to PASS
    ("B2 branch taken negative offset (br.nz -1 loop)",
     [set_zw_rd(18, 0x0002),    # t0: rd18 = 2
      add_si_rd(18, -1),        # t1 L: rd18 -= 1
      br_nz(18, -1),            # t2: rd18!=0 → taken → back to t1 (t2-1 = t1)
      st_o_rd(18, 16, 0)],      # t3: [PASS] not-taken (rd18==0) → exit 0x00
     PASS_EXIT,
     "br.nz negative offset loop failed"),

    # B3: Branch not-taken → fall through to next instruction (PASS)
    # br.z rd18 (rd18!=0) → not taken → execute next instruction
    # If taken (wrong): would skip to fail path → exit 0x01
    # Formula: target = rb0 + (imm << 2), rb0 = branch instruction address
    # br at idx2: target = idx2*4 + 24 + (3*4) = idx5 (taken_target)
    ("B3 branch not-taken (br.z rd18!=0)",
     [set_zw_rd(18, 0x0001),    # idx0: rd18 = 1 (non-zero)
      set_zw_rd(19, 0x0001),    # idx1: rd19 = 1 (fail value, for taken path)
      br_z(18, 3),              # idx2: br.z rd18, +3 → NOT taken (rd18≠0), fall through
      set_zw_rd(19, 0x0000),    # idx3: not-taken: overwrite rd19 = 0 (PASS)
      st_o_rd(19, 16, 0),       # idx4: exit 0x00 (PASS)
      set_zw_rd(20, 0x0001),    # idx5: [taken target] rd20 = 1
      st_o_rd(20, 16, 0)],      # idx6: [taken target] exit 0x01 (FAIL)
     PASS_EXIT,
     "br.z not-taken failed"),

    # B4: Branch taken with br.eq (two-register comparison)
    # Formula: target = rb0 + (imm << 2), rb0 = branch instruction address
    # br at idx3: target = idx3*4 + 24 + (4*4) = idx7 (pass_set)
    # Wrong offset (+3): lands on idx6 (dead_store) → exit 0x01
    ("B4 branch taken (br.eq equal)",
     [set_zw_rd(18, 0x0042),    # idx0: rd18 = 0x42
      set_zw_rd(19, 0x0042),    # idx1: rd19 = 0x42
      set_zw_rd(20, 0x0001),    # idx2: rd20 = 1 (fail value)
      br_eq(18, 19, 4),         # idx3: br.eq +4 → target = idx7 (pass_set)
      st_o_rd(20, 16, 0),       # idx4: [fail_store] NOT taken: exit 0x01
      set_zw_rd(18, 0x0001),    # idx5: [dead]
      st_o_rd(18, 16, 0),       # idx6: [dead_store] exit 0x01 (wrong offset lands here)
      set_zw_rd(18, 0x0000),    # idx7: [pass_set] correct target
      st_o_rd(18, 16, 0)],      # idx8: [pass_store] exit 0x00
     PASS_EXIT,
     "br.eq taken failed"),

    # B5: Branch taken with br.nz-rb (RB register)
    # br at idx2: target = idx2*4 + 24 + (4*4) = idx6 (pass_set)
    # Wrong offset (+3): lands on idx5 (dead_store) → exit 0x01
    ("B5 branch taken (br.nz-rb rb!=0)",
     [set_zw_rb(18, 0x0100),    # idx0: rb18 = 0x0100
      set_zw_rd(19, 0x0001),    # idx1: rd19 = 1 (fail value)
      br_nz_rb(18, 4),          # idx2: br.nz-rb +4 → target = idx6 (pass_set)
      st_o_rd(19, 16, 0),       # idx3: [fail_store] NOT taken: exit 0x01
      set_zw_rd(18, 0x0001),    # idx4: [dead]
      st_o_rd(18, 16, 0),       # idx5: [dead_store] exit 0x01 (wrong offset lands here)
      set_zw_rd(18, 0x0000),    # idx6: [pass_set] correct target
      st_o_rd(18, 16, 0)],      # idx7: [pass_store] exit 0x00
     PASS_EXIT,
     "br.nz-rb taken failed"),

    # ── call/ret return address tests ─────────────────────────────────

    # C1: call-iiii return address = call+1
    # Layout: call, pass_set, pass_store, fail_set, fail_store, ret
    # Correct: call +5 → ret → return to pass path
    # Wrong +3: lands on fail_set → fail_store → exit 0x01 (DETECTED)
    ("C1 call-iiii return address (call+1)",
     [call_iiii(5),              # idx0: call +5 → target = idx5 (ret)
      set_zw_rd(18, 0x0000),    # idx1: return here: rd18 = 0 (PASS)
      st_o_rd(18, 16, 0),       # idx2: exit 0x00
      set_zw_rd(19, 0x0001),    # idx3: [fail_set] wrong offset lands here
      st_o_rd(19, 16, 0),       # idx4: [fail_store] exit 0x01
      ret_riii(0, 0)],          # idx5: ret (correct target)
     PASS_EXIT,
     "call-iiii return address wrong"),

    # C2: call-rrii return address = call+1
    # call rb0, rd0, +5 → target = rb0 + 0 + 20 = PC + 20
    ("C2 call-rrii return address (call+1)",
     [call_rrii(0, 0, 5),       # idx0: call +5 → target = idx5 (ret)
      set_zw_rd(18, 0x0000),    # idx1: return here: rd18 = 0 (PASS)
      st_o_rd(18, 16, 0),       # idx2: exit 0x00
      set_zw_rd(19, 0x0001),    # idx3: [fail_set]
      st_o_rd(19, 16, 0),       # idx4: [fail_store] exit 0x01
      ret_riii(0, 0)],          # idx5: ret
     PASS_EXIT,
     "call-rrii return address wrong"),

    # C3: call→ret→landing round-trip (basic)
    # Verifies RA push/pop mechanism works correctly
    ("C3 call→ret→landing round-trip",
     [call_iiii(5),              # call +5 → target = ret
      set_zw_rd(18, 0x0000),    # return: PASS
      st_o_rd(18, 16, 0),
      set_zw_rd(19, 0x0001),    # [fail_set]
      st_o_rd(19, 16, 0),       # [fail_store]
      ret_riii(0, 0)],          # ret
     PASS_EXIT,
     "call→ret round-trip failed"),

    # ── RA §5.6.1 push tests ─────────────────────────────────────────

    # R1: RA §5.6.1 case 1 — cold push (first call on empty stack)
    # NOTE: the call→ret round-trip proves the LOW 48 bits (return address) are
    # correct, but does NOT prove high16==0x0001 (a refcount>1 also round-trips).
    # The exact high16 value is checked by the direct -d cpu read in the report.
    ("R1 RA cold push (case 1: first call, round-trip)",
     [call_iiii(3),              # first call → cold push to ra63
      set_zw_rd(18, 0x0000),    # return: PASS
      st_o_rd(18, 16, 0),
      ret_riii(0, 0)],          # ret → should pop correctly
     PASS_EXIT,
     "RA cold push failed (ret didn't return correctly)"),

    # R2: RA §5.6.1 case 2 — SAME-address recursion → refcount increments.
    # The call at idx1 always has the SAME return address (addr(2)), because the
    # br.nz at idx4 jumps back to idx1 (the same call site) each iteration.
    #   64 iterations → ra63 refcount = 64 (case 2: same addr → count+1), which
    #   does NOT consume depth → NO overflow → exit 0x00.
    # Discriminator: if case 2 were broken (treated as case 3 shift-down), the
    #   64 entries would fill ra1..ra63 → RASOF (0x8A) instead of 0x00.
    ("R2 RA same-address recursion (case 2: refcount increments)",
     [set_zw_rd(18, 64),        # t0: counter = 64
      call_iiii(2),             # t1 L: target t3(S); RA = addr(t2) — SAME every iteration
      illi(),                   # t2 (dead, never reached)
      add_si_rd(18, -1),        # t3 S: counter -= 1
      br_nz(18, -3),            # t4: rd18!=0 → back to t1 (t4-3 = t1)
      set_zw_rd(18, 0x0000),    # t5: PASS
      st_o_rd(18, 16, 0)],      # t6: exit 0x00
     PASS_EXIT,
     "same-address recursion (case 2) failed — refcount not incremented"),

    # R2b: RA §5.6.1 case 3 — DISTINCT-address deep chain → depth overflow (RASOF).
    # 64 chained calls at distinct sites → ra1..ra63 all valid → 64th → RASOF.
    # This is the case-3 companion of R2 (distinguishes case 2 from case 3).
    ("R2b RA distinct-address deep chain (case 3: depth overflow)",
     [call_iiii(1)] * 64 +      # 64 chained calls (distinct return addresses)
      [set_zw_rd(18, 0x0001),   # if RASOF didn't trigger → FAIL
       st_o_rd(18, 16, 0)],
     RASOF_EXIT,
     "deep distinct-address chain didn't trigger RASOF (case 3 broken?)"),

    # R3: RA §5.6.1 case 3 — different address → shift-down push
    # func1 calls func2 (different return addresses) → shift-down
    # Verified by: nested call/ret returns to correct places
    ("R3 RA shift-down push (case 3: different addresses)",
     [call_iiii(3),              # main calls func1 → push ret(main+1)
      set_zw_rd(18, 0x0000),    # main return: PASS
      st_o_rd(18, 16, 0),
      # func1 (at idx 3):
      call_iiii(2),              # func1 calls func2 → push ret(func1+1), shift-down
      ret_riii(0, 0),            # func1 return
      # func2 (at idx 5):
      ret_riii(0, 0)],           # func2 return
     PASS_EXIT,
     "RA shift-down push (case 3) failed"),

    # R4: RA §5.6.1 case 1+3 combined — two-level nested call/ret
    # Exercises: cold push (case1) → shift-down (case3)
    # All levels must return correctly
    ("R4 RA two-level nested call/ret",
     [call_iiii(3),              # main→func1: cold push (case1)
      set_zw_rd(18, 0x0000),    # main return: PASS
      st_o_rd(18, 16, 0),
      # func1 (idx 3):
      call_iiii(3),              # func1→func2: shift-down (case3)
      ret_riii(0, 0),            # func1 return
      # func2 (idx 6):
      call_iiii(2),              # func2→func3: shift-down (case3)
      ret_riii(0, 0),            # func2 return
      # func3 (idx 8):
      ret_riii(0, 0)],           # func3 return
     PASS_EXIT,
     "two-level nested call/ret failed"),
]

# ── CTL self-check ────────────────────────────────────────────────────

CTL_CHECKS = [
    ("CTL: st.o PASS but expect ILLI (wrong)",
     [set_zw_rd(18, 0x0000), st_o_rd(18, 16, 0)],
     ILLI_EXIT,
     "Self-check FAILED: probe cannot detect wrong values"),
    ("CTL: br.nz rd0 never-taken but expect taken (wrong)",
     [br_nz(0, 3),              # never taken (rd0=0)
      set_zw_rd(18, 0x0000),    # fall through: PASS
      st_o_rd(18, 16, 0)],
     ILLI_EXIT,                  # wrong expectation
     "Self-check FAILED: probe cannot detect br.nz rd0 behavior"),
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
    print("QEMU-012t Min ROM Probe (Branch PC + call RA §5.6.1)")
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
