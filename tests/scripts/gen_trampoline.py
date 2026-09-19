#!/usr/bin/env python3
"""Generate ROM trampoline blob for dadao-m1 test machine.

The trampoline is loaded at boot ROM base (0xffff_ffff_0000) via QEMU -bios.
It sets up the stack pointer (rb1) and jumps to the RAM entry point
(0xffff_0000_0000) where the test binary is loaded via -kernel.

Trampoline instructions (from ADR-0004 D6.4):
  1. set.zw rb1, wp2, 0xffff   -> rb1 = 0x0000_ffff_0000_0000 (wyde2=0xffff)
  2. or.w   rb1, wp1, 0x00ff   -> rb1 = 0x0000_ffff_00ff_0000 (wyde1|=0x00ff, SP)
  3. set.zw rb2, wp2, 0xffff   -> rb2 = 0x0000_ffff_0000_0000 (wyde2=0xffff)
  4. jump   rb2, rd0, 0        -> PC = rb2 + rd0 + 0 = 0xffff_0000_0000

Encoding references (contracts/opcodes.yaml):
  set.zw-rb: op=0x4E, rwii, (0x4E<<24)|(rbha<<18)|(wpN<<16)|immu16
  or.w-rb:   op=0x4A, rwii, (0x4A<<24)|(rbha<<18)|(wpN<<16)|immu16
  jump-rrii: op=0x71, rrii, (0x71<<24)|(rbha<<18)|(rdhb<<12)|(imms12&0xFFF)

Wyde position (contract-isa §2.4):
  wp0=bits[15:0], wp1=bits[31:16], wp2=bits[47:32], wp3=bits[63:48]
"""

import struct
import sys
import os

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


def generate_trampoline():
    """Generate trampoline instruction words."""
    instructions = []

    # 1. set.zw rb1, wp2, 0xffff -> rb1 = 0x0000_ffff_0000_0000
    instructions.append(encode_set_zw_rb(1, 2, 0xFFFF))

    # 2. or.w rb1, wp1, 0x00ff -> rb1 = 0x0000_ffff_00ff_0000 (SP)
    instructions.append(encode_or_w_rb(1, 1, 0x00FF))

    # 3. set.zw rb2, wp2, 0xffff -> rb2 = 0x0000_ffff_0000_0000
    instructions.append(encode_set_zw_rb(2, 2, 0xFFFF))

    # 4. jump rb2, rd0, 0 -> PC = rb2 + 0 + 0 = 0xffff_0000_0000
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
