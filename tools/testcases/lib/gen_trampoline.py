#!/usr/bin/env python3
"""Generate ROM trampoline blob for the legacy dadao-tiny test harness.

The trampoline is loaded at the Tiny BootROM base via `-bios` and is kept for
the pre-contract harness (raw `-kernel` + flat ROM trampoline; the contract
boot path uses the fixed 64 KiB firmware through `bootrom-image`).  It:
  0. parks the hmon hypv vector on an unreachable cfx3 address, so a
     synchronous fault still surfaces as the machine-fault exit code the
     pre-contract oracles expect (the fixed firmware installs a real handler);
  1. sets up the stack pointer (rb1) to the profile SP;
  2. loads the profile RAM entry into rb2 and jumps there.

Geometry is read from tests/shared/machine-profiles.yaml (TESTCASES-091t); no
address is hardcoded.

Encoding references (contracts/opcodes.yaml):
  set.zw-rb: op=0x4E, rwii, (0x4E<<24)|(rbha<<18)|(wpN<<16)|immu16
  or.w-rb:   op=0x4A, rwii, (0x4A<<24)|(rbha<<18)|(wpN<<16)|immu16
  cfx2rc:    op=0x7B, crrr, (0x7B<<24)|(cfxha<<18)|(cg<<12)|(rc<<6)|rd
  jump-rrii: op=0x71, rrii, (0x71<<24)|(rbha<<18)|(rdhb<<12)|(imms12&0xFFF)

Wyde position (contract-isa §2.4):
  wp0=bits[15:0], wp1=bits[31:16], wp2=bits[47:32], wp3=bits[63:48]
"""

import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machine_profile  # noqa: E402

# Geometry comes from tests/shared/machine-profiles.yaml (TESTCASES-091t).
_PROFILE = machine_profile.load("tiny")
# Raw -kernel application entry (Tiny: kernel_base + 0x100).  The trampoline
# jumps here, not to the RAM base, so the raw image's reserved prefix and the
# fixed entry stay consistent with spec/Machine-v5 §6.
RAM_BASE = _PROFILE.entry
RAM_SIZE = _PROFILE["ram_size"]
SP = _PROFILE.sp

# Instruction encoding helpers
def encode_set_zw_rb(rbha, wpN, immu16):
    """Encode set.zw rb, wpN, imm16 (rwii format, op=0x4E)."""
    assert 0 <= rbha <= 63
    assert 0 <= wpN <= 3
    assert 0 <= immu16 <= 0xFFFF
    return (0x4E << 24) | (rbha << 18) | (wpN << 16) | immu16

def encode_or_w_rb(rbha, wpN, immu16):
    """Encode or.w rb, wpN, imm16 (rwii format, op=0x4A)."""
    assert 0 <= rbha <= 63
    assert 0 <= wpN <= 3
    assert 0 <= immu16 <= 0xFFFF
    return (0x4A << 24) | (rbha << 18) | (wpN << 16) | immu16

def encode_jump_rrii(rbha, rdhb, imms12):
    """Encode jump rb, rd, offset (rrii format, op=0x71)."""
    assert 0 <= rbha <= 63
    assert 0 <= rdhb <= 63
    # imms12 is signed 12-bit
    assert -2048 <= imms12 <= 2047
    return (0x71 << 24) | (rbha << 18) | (rdhb << 12) | (imms12 & 0xFFF)


def encode_cfx2rc(cfxha, cg, rc, rd):
    """Encode cfx2rc cfxha, cg, rc, rd (crrr format, op=0x7B)."""
    assert 0 <= cfxha <= 0x3F
    assert 0 <= cg <= 0x3F
    assert 0 <= rc <= 0x3F
    assert 0 <= rd <= 0x3F
    return (0x7B << 24) | (cfxha << 18) | (cg << 12) | (rc << 6) | rd


def generate_trampoline():
    """Generate trampoline instruction words."""
    instructions = []

    def load_addr(rb, value):
        words = [encode_set_zw_rb(rb, 0, value & 0xFFFF)]
        for wp in (1, 2, 3):
            words.append(encode_or_w_rb(rb, wp, (value >> (16 * wp)) & 0xFFFF))
        return words

    # 0. Legacy Tiny trampoline only: park the hmon hypv vector on an
    #    unreachable cfx3 address so a synchronous fault keeps surfacing as
    #    the machine-fault exit code the pre-contract harness oracles expect.
    #    (The fixed-firmware contract path uses the real handler instead.)
    instructions.extend(load_addr(3, 0x0FFF00010000))
    instructions.append(encode_cfx2rc(3, 3, 10, 3))

    # 1. rb1 = profile SP (48-bit, near the RAM top)
    instructions.extend(load_addr(1, SP))

    # 2. rb2 = profile RAM entry
    instructions.extend(load_addr(2, RAM_BASE))

    # 3. jump rb2, rd0, 0 -> PC = rb2 + 0 + 0 = RAM entry
    instructions.append(encode_jump_rrii(2, 0, 0))

    return instructions


def main():
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trampoline.bin")

    instructions = generate_trampoline()

    # Pack as big-endian 32-bit words
    blob = b""
    for word in instructions:
        blob += struct.pack(">I", word)

    with open(output_path, "wb") as f:
        f.write(blob)

    print(f"Generated {output_path} ({len(blob)} bytes, {len(instructions)} instructions)")
    for i, word in enumerate(instructions):
        print(f"  [{i}] 0x{word:08X}")


if __name__ == "__main__":
    main()
