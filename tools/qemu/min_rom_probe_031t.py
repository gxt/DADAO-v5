#!/usr/bin/env python3
"""Minimal ROM probe for QEMU-031t: verify rb0 64-bit writeback (ADR-0012 D8.3).

Creates a standalone binary that:
  1. jump +8 (forward) → taken path: rb0 set to target (64-bit)
  2. rb2rd rd1, rb0, 1 → copy rb0 to rd1
  3. Compare rd1 against expected rb0 value (target address)
  4. Write 0 (PASS) or 1 (FAIL) to exit port

If rb0 writeback is removed (old 48-bit-only), rb0 will be stale/wrong → FAIL.
"""
import os, sys, struct, subprocess, uuid

# D6 compliance: resolve probe artifact dir via paths.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tools', 'infra'))
import paths as _paths

def _probe_artifact_dir():
    d = str(_paths.test_artifacts_dir() / 'probes')
    os.makedirs(d, exist_ok=True)
    return d

# ── Instruction encoders (from contracts/opcodes.yaml) ────────────────────

def encode_set_zw_rb(rbha, wpN, immu16):
    """set.zw rb, wpN, imm16 (rwii, op=0x4E)"""
    return (0x4E << 24) | (rbha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_or_w_rb(rbha, wpN, immu16):
    """or.w rb, wpN, imm16 (rwii, op=0x4A)"""
    return (0x4A << 24) | (rbha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_set_zw_rd(rdha, wpN, immu16):
    """set.zw rd, wpN, imm16 (rwii, op=0x4C)"""
    return (0x4C << 24) | (rdha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_or_w_rd(rdha, wpN, immu16):
    """or.w rd, wpN, imm16 (rwii, op=0x48)"""
    return (0x48 << 24) | (rdha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_jump_iiii(imms24):
    """jump imms24 (iiii, op=0x70): unconditional jump, PC=rb0+(imms24<<2)"""
    return (0x70 << 24) | (imms24 & 0xFFFFFF)

def encode_rb2rd(rdhb, rbhc, immu6):
    """rb2rd rd, rb, count (orri, op=0x40, ha=0x36)"""
    return 0x40D80000 | (rdhb << 12) | (rbhc << 6) | (immu6 & 0x3F)

def encode_xor_o(rdhb, rdhc, rdhd):
    """xor.o rdX, rdY, rdZ (orrr, op=0x40, ha=0x0A)"""
    return 0x40280000 | (rdhb << 12) | (rdhc << 6) | rdhd

def encode_or_o(rdhb, rdhc, rdhd):
    """or.o rdX, rdY, rdZ (orrr, op=0x40, ha=0x09)"""
    return 0x40240000 | (rdhb << 12) | (rdhc << 6) | rdhd

def encode_st_o(rdha, rbhb, imms12):
    """st.o rd, rb, offset (rrii, op=0x21)"""
    return (0x21 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_br_nz(rdha, imms18):
    """br.nz rdha, imms18 (riii, op=0x6B)"""
    return (0x6B << 24) | (rdha << 18) | (imms18 & 0x3FFFF)

def w32(v):
    return struct.pack('>I', v)

def load_imm64_rb(rb, value):
    """Emit set.zw + or.w sequence to load 64-bit value into RB."""
    words = [encode_set_zw_rb(rb, 0, value & 0xFFFF)]
    w1 = (value >> 16) & 0xFFFF
    w2 = (value >> 32) & 0xFFFF
    w3 = (value >> 48) & 0xFFFF
    if w1: words.append(encode_or_w_rb(rb, 1, w1))
    if w2: words.append(encode_or_w_rb(rb, 2, w2))
    if w3: words.append(encode_or_w_rb(rb, 3, w3))
    return words

def load_imm64_rd(rd, value):
    """Emit set.zw + or.w sequence to load 64-bit value into RD."""
    words = [encode_set_zw_rd(rd, 0, value & 0xFFFF)]
    w1 = (value >> 16) & 0xFFFF
    w2 = (value >> 32) & 0xFFFF
    w3 = (value >> 48) & 0xFFFF
    if w1: words.append(encode_or_w_rd(rd, 1, w1))
    if w2: words.append(encode_or_w_rd(rd, 2, w2))
    if w3: words.append(encode_or_w_rd(rd, 3, w3))
    return words

# ── Probe builders ────────────────────────────────────────────────────────

EXIT_PORT = 0xFFFF_8000_0000
# BINARY_BASE = 0xFFFF_0000_1000 (trampoline loads here)

def build_probe_jump_taken():
    """Probe: jump taken → rb0 should be target address (64-bit).

    Sequence:
      [0] set.zw rb1, wp0, lo16(EXIT_PORT)   -- rb1 = EXIT_PORT base
      [1] or.w  rb1, wp1, mid16(EXIT_PORT)
      [2] or.w  rb1, wp2, hi16(EXIT_PORT)
      [3] set.zw rd62, 0, 0                   -- rd62 = 0 (PASS init)
      [4] jump +2                             -- PC = rb0 + 8 (skip1 insn)
      [5] rb2rd rd1, rb0, 1                   -- rd1 = rb0 (target addr)
      [6] (skipped by jump)                   -- this is the jump target+1
      [7] <expected rd1 value>                -- load expected into rd2
      [8-10] xor rd3, rd1, rd2; or rd62, rd62, rd3
      [11] st.o rd62, [rb1, 0]                -- write PASS/FAIL to exit port

    jump +2 at [4] → target = addr([4]) + 8 = addr([6])
    rb0 after jump = addr([6]) (64-bit, with D8.3 writeback)

    The probe checks: rb0 == expected_addr_of_([6])
    If rb0 writeback is removed → rb0 is stale → rd1 wrong → FAIL
    """
    words = []
    EXIT_LO = EXIT_PORT & 0xFFFF
    EXIT_MID = (EXIT_PORT >> 16) & 0xFFFF
    EXIT_HI = (EXIT_PORT >> 32) & 0xFFFF

    # [0-2] Load EXIT_PORT into rb1
    words.extend(load_imm64_rb(1, EXIT_PORT))
    loader_count = len(words)  # 3-4 instructions

    # [N] set.zw rd62, 0, 0 → accumulator = 0 (PASS)
    words.append(encode_set_zw_rd(62, 0, 0))
    accum_idx = len(words) - 1

    # [N+1] jump +2 → target = addr(N+1) + 8 = addr(N+3)
    jump_idx = len(words)
    words.append(encode_jump_iiii(2))  # offset=2 → +8 bytes

    # [N+2] rb2rd rd1, rb0, 1 → rd1 = rb0 (this is SKIPPED by jump)
    words.append(encode_rb2rd(1, 0, 1))  # skipped

    # [N+3] rb2rd rd1, rb0, 1 → rd1 = rb0 (jump lands here at N+3)
    rb2rd_idx = len(words)
    words.append(encode_rb2rd(1, 0, 1))

    # Now compute expected rb0 value.
    # jump at [N+1] → target = addr(N+1) + 8
    # addr(N+1) = BINARY_BASE + (N+1)*4
    # target = BINARY_BASE + (N+1)*4 + 8 = BINARY_BASE + (N+3)*4
    # rb0 after jump = target = BINARY_BASE + (N+3)*4
    # So expected rd1 = BINARY_BASE + rb2rd_idx * 4

    BINARY_BASE = 0xFFFF_0000_1000
    expected_rb0 = BINARY_BASE + rb2rd_idx * 4

    # Load expected value into rd2
    words.extend(load_imm64_rd(2, expected_rb0))

    # XOR rd1 with rd2: if equal, rd3 = 0
    words.append(encode_xor_o(3, 1, 2))

    # OR into accumulator (rd62)
    words.append(encode_or_o(62, 62, 3))

    # Write rd62 to exit port: 0 = PASS, nonzero = FAIL
    words.append(encode_st_o(62, 1, 0))

    return b''.join(w32(w) for w in words), expected_rb0, jump_idx, rb2rd_idx


def build_probe_not_taken():
    """Probe: branch not-taken → rb0 = PC+4 (64-bit) from tb_stop.

    Sequence:
      [0-2] load EXIT_PORT into rb1
      [3] set.zw rd62, 0, 0 (PASS init)
      [4] set.zw rd1, 0, 0 (rd1 = 0, for br.nz condition)
      [5] br.nz rd1, +2 → rd1=0, NOT taken, fall through
      [6] rb2rd rd1, rb0, 1 → rd1 = rb0 (should be addr[6])
      [7-...] load expected, xor, or, st.o

    br.nz not-taken → tb_stop → rb0 = pc_next = addr([6])
    expected rd1 = BINARY_BASE + rb2rd_idx * 4
    """
    words = []
    words.extend(load_imm64_rb(1, EXIT_PORT))
    words.append(encode_set_zw_rd(62, 0, 0))  # accumulator
    words.append(encode_set_zw_rd(1, 0, 0))   # rd1 = 0

    # br.nz rd1, +2 → rd1=0, condition false, NOT taken
    br_idx = len(words)
    words.append(encode_br_nz(1, 2))

    # rb2rd rd1, rb0, 1 → rd1 = rb0
    rb2rd_idx = len(words)
    words.append(encode_rb2rd(1, 0, 1))

    BINARY_BASE = 0xFFFF_0000_1000
    expected_rb0 = BINARY_BASE + rb2rd_idx * 4

    words.extend(load_imm64_rd(2, expected_rb0))
    words.append(encode_xor_o(3, 1, 2))
    words.append(encode_or_o(62, 62, 3))
    words.append(encode_st_o(62, 1, 0))

    return b''.join(w32(w) for w in words), expected_rb0, br_idx, rb2rd_idx


# ── QEMU runner ───────────────────────────────────────────────────────────

def find_qemu():
    """Find qemu-system-dadao binary."""
    import glob
    search = [
        '.work/build/qemu/qemu-system-dadao',
        '.cache/refs/qemu/build/qemu-system-dadao',
    ]
    for p in search:
        if os.path.exists(p):
            return os.path.abspath(p)
    # Try PATH
    for d in os.environ.get('PATH', '').split(':'):
        p = os.path.join(d, 'qemu-system-dadao')
        if os.path.exists(p):
            return p
    return None

def find_trampoline():
    """Find trampoline.bin."""
    search = [
        'tests/scripts/trampoline.bin',
        'tests/machine/trampoline.bin',
    ]
    for p in search:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None

def run_probe(binary_data, label, qemu_bin, trampoline_path, timeout=10):
    """Run a probe binary with QEMU and return exit code."""
    bin_path = os.path.join(_probe_artifact_dir(), f'dadao-probe-{uuid.uuid4().hex[:8]}.bin')
    with open(bin_path, 'wb') as f:
        f.write(binary_data)
    try:
        cmd = [
            qemu_bin,
            '-machine', 'dadao-m1',
            '-nographic',
            '-bios', trampoline_path,
            '-kernel', bin_path,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            exit_code = -1
        return exit_code, stderr.decode('utf-8', errors='replace')
    finally:
        try:
            os.unlink(bin_path)
        except OSError:
            pass


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    qemu_bin = find_qemu()
    trampoline = find_trampoline()
    if not qemu_bin or not trampoline:
        print(f"ERROR: qemu={qemu_bin}, trampoline={trampoline}")
        sys.exit(1)

    print(f"QEMU: {qemu_bin}")
    print(f"Trampoline: {trampoline}")
    print()

    # ── Probe 1: jump taken ──
    print("=" * 60)
    print("Probe 1: jump taken → rb0 = target (64-bit)")
    print("=" * 60)
    blob, expected, jump_idx, rb2rd_idx = build_probe_jump_taken()
    print(f"Binary: {len(blob)} bytes")
    print(f"jump at [{jump_idx}], rb2rd at [{rb2rd_idx}]")
    print(f"Expected rb0 = 0x{expected:016X}")

    exit_code, stderr = run_probe(blob, "jump-taken", qemu_bin, trampoline)
    print(f"Exit code: 0x{exit_code:02X} {'PASS' if exit_code == 0 else 'FAIL'}")
    if exit_code != 0 and stderr:
        print(f"Stderr: {stderr[:300]}")
    print()

    # ── Probe 2: branch not-taken ──
    print("=" * 60)
    print("Probe 2: branch not-taken → rb0 = PC+4 (tb_stop)")
    print("=" * 60)
    blob, expected, br_idx, rb2rd_idx = build_probe_not_taken()
    print(f"Binary: {len(blob)} bytes")
    print(f"br.nz at [{br_idx}], rb2rd at [{rb2rd_idx}]")
    print(f"Expected rb0 = 0x{expected:016X}")

    exit_code, stderr = run_probe(blob, "not-taken", qemu_bin, trampoline)
    print(f"Exit code: 0x{exit_code:02X} {'PASS' if exit_code == 0 else 'FAIL'}")
    if exit_code != 0 and stderr:
        print(f"Stderr: {stderr[:300]}")
    print()

    # Summary
    print("=" * 60)
    print("Both probes should show PASS with correct D8.3 implementation.")
    print("Remove rb0 writeback → these probes FAIL.")
    print("=" * 60)


if __name__ == '__main__':
    main()