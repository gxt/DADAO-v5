#!/usr/bin/env python3
"""Min ROM probe for QEMU-032t: ret rd0 with imms18 != 0 → ILLI 0x88.

Spec: SimRISC-06 §函数返回 / contract-isa §1.3.1 / §8.5.
Rule: contracts/legality_rules.yaml `dst_rd0_nonzero` (kind: static, fault: ILLI).
Exit code: ADR-0004 D5.8 — ILLI = 0x88.

Cases:
  1. positive  : `ret rd0, 0`   (rd0 + imms18 == 0) → legal, normal pop → exit 0
  2. negative  : `ret rd0, 1`   (rd0 + imms18 != 0) → ILLI 0x88
  3. negative  : `ret rd0, -1`  (rd0 + imms18 != 0) → ILLI 0x88
  4. non-rd0   : `ret rd1, 42`  (rdha != rd0)       → legal, rd1=42, normal pop → exit 0

Reverse gate: if the translate-time check is removed, cases 2/3 no longer
produce 0x88 (they fall through to RASUF 0x8B on an empty RAS) ⇒ probe FAILs.

Layout convention (same as min_rom_probe_030t.py): ROM at 0xFFFFFFFF0000 with a
6-instruction trampoline; test instructions start at TEST_BASE = ROM_BASE+0x18.
ENCODINGS are taken from contracts/opcodes.yaml (op values), not from QEMU.
"""
import os
import struct
import subprocess
import sys
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

ROM_BASE = 0xFFFFFFFF0000
TEST_BASE = ROM_BASE + 0x18  # test instructions start after 6-insn trampoline


def addr_of(idx):
    """Byte address of test instruction at index idx."""
    return TEST_BASE + idx * 4


# ── Instruction encoding (op values from contracts/opcodes.yaml) ────────

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


def encode_orri(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)


def encode_rrii(op, ha, hb, hc, hd):
    return struct.pack('>I', (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd)


def set_zw_rd(rd, immu16): return encode_rwii(0x4C, rd, 0, immu16)
def st_o_rd(rdha, rbhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return encode_rrii(0x21, rdha, rbhb, hc, hd)
def st_o_rd_pass(): return encode_rrii(0x21, 18, 16, 0, 0)
def st_o_rd_fail(): return encode_rrii(0x21, 19, 16, 0, 0)
def cmp_uo_rd(rdhb, rdhc, rdhd): return encode_orri(0x40, 0x2A, rdhb, rdhc, rdhd)
def br_nz(rdha, imms18): return encode_riii(0x6B, rdha, imms18 & 0x3FFFF)
def call_iiii(imms24): return encode_iiii(0x74, imms24 & 0xFFFFFF)
def ret_riii(rdha, imms18): return encode_riii(0x76, rdha, imms18 & 0x3FFFF)
def fence(): return struct.pack('>I', 0x77000000)


# ── Assertion block (same proven pattern as 030t) ───────────────────────

def build_assertion(checks, fail_code):
    """Emit cmp/br per check, then PASS exit(0) and FAIL exit(fail_code).

    Layout (N checks):
      [2*i]   cmp_uo(flag, actual_i, expected_i)
      [2*i+1] br_nz(flag, 2*(N-i)+1) → FAIL arm
      [2*N]   set_zw(18, 0); [2*N+1] st_o_pass()   ← exit 0
      [2*N+2] set_zw(19, fc); [2*N+3] st_o_fail()  ← exit fc
    """
    N = len(checks)
    insns = []
    for i, (actual, expected, flag) in enumerate(checks):
        offset = 2 * (N - i) + 1
        insns.append(cmp_uo_rd(flag, actual, expected))
        insns.append(br_nz(flag, offset))
    insns.append(set_zw_rd(18, 0))
    insns.append(st_o_rd_pass())
    insns.append(set_zw_rd(19, fail_code))
    insns.append(st_o_rd_fail())
    return insns


UNDI_TERMINATOR = b'\x08\x04\x00\x01'


def build_rom(test_insns):
    trampoline = [
        encode_rwii(0x4E, 1, 2, 0xFFFF),   # rb1 = 0xFFFF00000000 (stack)
        encode_rwii(0x4A, 1, 1, 0x00FF),   # rb1 = 0xFFFF00FF0000
        encode_rwii(0x4E, 2, 2, 0xFFFF),   # rb2 = 0xFFFF00000000 (RAM)
        encode_rwii(0x4E, 16, 2, 0xFFFF),  # rb16 = 0xFFFF00000000
        encode_rwii(0x4A, 16, 1, 0x8000),  # rb16 = 0xFFFF80000000 (exit port)
        encode_rwii(0x4E, 17, 2, 0xFFFF),  # rb17 = 0xFFFF00000000
    ]
    rom = b''.join(trampoline) + b''.join(test_insns) + UNDI_TERMINATOR
    while len(rom) < 64:
        rom += fence()
    return rom


# ── QEMU execution ─────────────────────────────────────────────────────

def run_test(rom_data, timeout=10):
    kernel_data = fence() * 4
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(rom_data)
        rp = f.name
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False,
                                     dir=_probe_artifact_dir()) as f:
        f.write(kernel_data)
        kp = f.name
    try:
        r = subprocess.run(
            [QEMU, '-M', 'dadao-m1', '-nographic', '-bios', rp, '-kernel', kp],
            capture_output=True, timeout=timeout, text=True)
        return r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    finally:
        os.unlink(rp)
        os.unlink(kp)


# ── Exit codes (ADR-0004 D5.8) ─────────────────────────────────────────

PASS_EXIT = 0x00
ILLI_EXIT = 0x88


def call_to(frm_idx, to_idx):
    return call_iiii(to_idx - frm_idx)


# ── Test cases ─────────────────────────────────────────────────────────

def case_positive_ret_rd0_0():
    """`ret rd0, 0` — legal. call pushes return addr, ret pops back to landing,
    landing writes exit 0. Must NOT be ILLI."""
    insns = [
        call_to(0, 4),        # [0] push ra=addr[1], jump to [4]
        set_zw_rd(18, 0),     # [1] landing: rd18 = 0 (PASS code)
        st_o_rd_pass(),       # [2] exit 0
        fence(),               # [3] padding (unreached)
        ret_riii(0, 0),       # [4] ret rd0, 0 → pop → jump addr[1] → exit 0
    ]
    return insns, PASS_EXIT


def case_negative_ret_rd0_1():
    """`ret rd0, 1` — illegal (rd0 with imms18 != 0) → ILLI 0x88.
    If the check is removed, an empty RAS yields RASUF 0x8B instead."""
    return [ret_riii(0, 1)], ILLI_EXIT


def case_negative_ret_rd0_neg1():
    """`ret rd0, -1` (18-bit two's complement 0x3FFFF) → ILLI 0x88."""
    return [ret_riii(0, 0x3FFFF)], ILLI_EXIT


def case_nonrd0_ret_rd1_42():
    """`ret rd1, 42` — rdha != rd0, no constraint. ret writes rd1=42, pops back
    to landing, landing asserts rd1 == 42 and exits 0."""
    EXPECTED = 42
    insns = [
        call_to(0, 0),        # [0] placeholder, target patched below
        set_zw_rd(20, EXPECTED),  # [1] expected value
    ]
    assertion = build_assertion([(1, 20, 21)], 0x42)
    insns += assertion            # [2 ..]
    ret_idx = len(insns)
    insns.append(ret_riii(1, EXPECTED))  # ret rd1, 42
    insns[0] = call_to(0, ret_idx)       # patch call target → ret
    return insns, PASS_EXIT


CASES = [
    ("positive: ret rd0, 0 → normal pop (exit 0)",
     case_positive_ret_rd0_0()),
    ("negative: ret rd0, 1 → ILLI (0x88)",
     case_negative_ret_rd0_1()),
    ("negative: ret rd0, -1 → ILLI (0x88)",
     case_negative_ret_rd0_neg1()),
    ("non-rd0: ret rd1, 42 → rd1=42, normal pop (exit 0)",
     case_nonrd0_ret_rd1_42()),
]


def main():
    os.chdir(_REPO_ROOT)
    if not os.path.exists(QEMU):
        print(f"ERROR: {QEMU} not found. Run 'make build-qemu' first.")
        return 1

    print("=" * 70)
    print("QEMU-032t Min ROM Probe (ret rd0, imms18 != 0 → ILLI 0x88)")
    print("=" * 70)

    passed = failed = 0
    fail_details = []
    for name, (insns, expected) in CASES:
        rom = build_rom(insns)
        code, stderr = run_test(rom)
        if code == expected:
            status = "PASS"
            passed += 1
        elif code == -1:
            status = "TIMEOUT"
            failed += 1
            fail_details.append(f"  [TIMEOUT] {name}")
        else:
            status = "FAIL"
            failed += 1
            fail_details.append(
                f"  [FAIL] {name}: exit=0x{code:02X} (expect 0x{expected:02X})")
        print(f"  [{status}] {name}: exit=0x{code:02X} (expect 0x{expected:02X})")
        if stderr and code != expected:
            print(f"      stderr: {stderr[:200]}")

    print("-" * 70)
    print(f"Main: {passed}/{passed + failed} passed, {failed} failed")
    if fail_details:
        print("Failed:")
        for d in fail_details:
            print(d)

    all_pass = failed == 0
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
