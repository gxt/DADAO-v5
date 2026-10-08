#!/usr/bin/env python3
"""Min ROM probe for QEMU-022t: TB continuation fix (gen_update_pc).

Tests that dadao_tr_tb_stop correctly updates env->pc when a TB is cut
due to TCG op buffer overflow or max_insns limit.

Test cases:
  T1: 96 st.o-rd stores → exit=0 (baseline, should pass regardless of fix)
  T2: 100 st.o-rd stores → exit=0 (before fix: exit=124 TIMEOUT)
  T3: 510 set.zw instructions → exit=0 (before fix: exit=124 TIMEOUT)

CTL self-check:
  CTL1: st.o PASS but expect TIMEOUT (wrong) — probe broken if passes
  CTL2: fence but expect PASS (wrong) — probe broken if passes

Usage: python3 tools/qemu/min_rom_probe_022t.py
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

def encode_rwii(op, ha, wpN, immu16):
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    hb = (wpN << 4) | hi4
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (mid6 << 6) | lo6)

def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)

# ── Common instruction mnemonics ──────────────────────────────────────

def set_zw_rd(rd, immu16):
    return encode_rwii(0x4C, rd, 0, immu16)

def or_w_rd(rd, wpN, immu16):
    return encode_rwii(0x48, rd, wpN, immu16)

def st_o_rd(rdha, rbhb, imms12):
    """st.o rdha, rbhb, imms12 (op=0x21, rrii)"""
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F; hd = imm & 0x3F
    if imms12 < 0: hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)

def fence():
    return encode_orri(0x77, 0x00, 0, 0, 0)


# ── Semihosting SYS_EXIT (ADR-0020 D8: replaces the legacy MMIO halt device) ──

SEMI_BLOCK = 0xFFFF_00FF_F000       # argument block {reason, code}, in RAM
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026


def trap(ha, immu18):
    return struct.pack('>I', (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF))


def semi_exit(code_rd):
    """rb16 = SEMI_BLOCK; block = {0x20026, code_rd}; rd16 = 0x18; trap."""
    return ([encode_rwii(0x4E, 16, 2, 0xFFFF), encode_rwii(0x4A, 16, 1, 0x00FF),
             encode_rwii(0x4A, 16, 0, 0xF000)]
            + [set_zw_rd(8, 0x0026), or_w_rd(8, 1, 0x0002)]
            + [st_o_rd(8, 16, 0)]
            + [st_o_rd(code_rd, 16, 8)]
            + [set_zw_rd(16, 0x0018)]
            + [trap(0, SEMIHOST_TAG)])

# ── Terminators and ROM builder ───────────────────────────────────────

UNDI_TERMINATOR = b'\x08\x04\x00\x01'

def build_rom(test_insns):
    """Build ROM: [trampoline | test_insns | UNDI | padding].
    Trampoline sets up:
      rb1  = SP (0xFFFF_00FF_0000)
      rb16 = the SYS_EXIT argument block (rebuilt by semi_exit)
      rb17 = DUMP_BASE (0xFFFF_00FE_0000) — RAM for st.o stores
      rd18 = 0 (PASS value)
      rd19 = 1 (FAIL value)
    """
    trampoline = [
        encode_rwii(0x4E, 1, 2, 0xFFFF),  # set.zw rb1, wp2, 0xFFFF
        encode_rwii(0x4A, 1, 1, 0x00FF),  # or.w rb1, wp1, 0x00FF (SP)
        encode_rwii(0x4E, 16, 2, 0xFFFF), # set.zw rb16, wp2, 0xFFFF
        encode_rwii(0x4A, 16, 1, 0x00FF), # rb16 = 0xFFFF00FF0000 (dead; semi_exit rebuilds it)
        encode_rwii(0x4E, 17, 2, 0xFFFF), # set.zw rb17, wp2, 0xFFFF (RAM base)
        set_zw_rd(18, 0),                  # rd18 = 0 (PASS)
        set_zw_rd(19, 1),                  # rd19 = 1 (FAIL)
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
             '-bios', rom_path, '-kernel', kernel_path,
             '-semihosting-config', 'enable=on,target=native'],
            capture_output=True, timeout=timeout, text=True)
        return result.returncode, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    finally:
        os.unlink(rom_path); os.unlink(kernel_path)

# ── Exit codes ────────────────────────────────────────────────────────

PASS_EXIT = 0; TIMEOUT_EXIT = 124; ILLI_EXIT = 136

# ── Test case builders ────────────────────────────────────────────────

def make_st_o_rd_sequence(n):
    """Generate n st.o-rd stores to RAM (rb17 = DUMP_BASE).
    Each store: st.o rdN, rb17, N*8 (N=1..n, rdN is pre-set to 0 by trampoline
    for rd18, others are 0 by default).
    Uses rd1..rdN for variety; rd0 stores would be silently ignored.
    After all stores, report PASS (0) via SYS_EXIT.
    """
    insns = []
    for i in range(1, n + 1):
        rd = ((i - 1) % 62) + 1  # cycle rd1..rd62, skip rd0 and rd63(scratch)
        offset = (i * 8) & 0xFFF
        insns.append(st_o_rd(rd, 17, offset))
    # PASS: SYS_EXIT(0)
    insns += semi_exit(18)
    return insns

def make_set_zw_sequence(n):
    """Generate n set.zw instructions then report PASS.
    Each set.zw writes an immediate to a different rd (cycles rd1..rd62).
    After all set.zw, report PASS (0) via SYS_EXIT.
    """
    insns = []
    for i in range(1, n + 1):
        rd = ((i - 1) % 62) + 1  # cycle rd1..rd62
        insns.append(set_zw_rd(rd, i & 0xFFFF))
    # Reset rd18=0 (may have been overwritten by set.zw cycle) before PASS
    insns.append(set_zw_rd(18, 0))
    # PASS: SYS_EXIT(0)
    insns += semi_exit(18)
    return insns

# ── Test definitions ──────────────────────────────────────────────────

TESTS = [
    ("T1 96 st.o-rd → exit=0 (baseline)",
     make_st_o_rd_sequence(96),
     PASS_EXIT,
     "96 st.o-rd should always PASS (no TB cut)"),

    ("T2 100 st.o-rd → exit=0 (was TIMEOUT before fix)",
     make_st_o_rd_sequence(100),
     PASS_EXIT,
     "100 st.o-rd TIMEOUT means TB continuation bug persists"),

    ("T3 510 set.zw → exit=0 (was TIMEOUT before fix)",
     make_set_zw_sequence(510),
     PASS_EXIT,
     "510 set.zw TIMEOUT means TB continuation bug persists"),
]

CTL_CHECKS = [
    ("CTL1: st.o PASS but expect TIMEOUT (wrong)",
     semi_exit(18),
     TIMEOUT_EXIT,
     "Self-check FAILED: probe cannot detect PASS vs TIMEOUT"),
    ("CTL2: fence but expect PASS (wrong)",
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
    print("QEMU-022t Min ROM Probe (TB continuation fix)")
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
