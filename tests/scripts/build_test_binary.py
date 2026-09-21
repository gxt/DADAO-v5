#!/usr/bin/env python3
"""Build test binary from ISA vector YAML for dadao-m1 QEMU testing.

Binary layout (loaded at BINARY_BASE = 0xffff_0000_0000):
  [section 1] loader   - Set rd/rb/ra registers from input_state, write memory
  [section 2] test     - Raw encoding word (struct.pack('>I', word))
  [section 3] dumper   - Dump state to state-dump region (diagnostics only)
  [section 4] exit     - Compare expected_state with actual, write exit code

Design decisions (ADR-0009):
  D1: raw-encoding via struct.pack, no llvm-mc
  D2: guest-internal comparison via XOR+ORR accumulator
  D4: RD scratch=rd60-63, RB scratch=rb60-63, RA not scratch
  D5: exit code 0x00=PASS, 0x01-0x7F=FAIL, 0x80+=machine fault

Instruction encodings from contracts/opcodes.yaml (SimRISC 0.5.3):
  Wyde positions: wp0=bits[15:0], wp1=bits[31:16], wp2=bits[47:32], wp3=bits[63:48]
"""

import struct
import sys
import os
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Memory map (ADR-0004 D1)
BINARY_BASE = 0xFFFF_0000_0000       # RAM entry point
EXIT_PORT   = 0xFFFF_8000_0000       # Exit port address
DUMP_BASE   = 0xFFFF_00FE_0000       # State-dump region base
DUMP_SIZE   = 0x408                  # 1032 bytes: rd[0]+rd[1..63]+rb[0]+rb[1..63]+pc
RD_DUMP_OFF = 0x008                  # rd[1] starts at +0x008 (rd[0] slot at +0x000 is reserved)
RB_DUMP_OFF = 0x208                  # rb[1] starts at +0x208 (rb[0] slot at +0x200 is reserved)
PC_DUMP_OFF = 0x400                  # pc (rb0 via rb2rd→st.o-rd) at +0x400

# Register conventions (ADR-0009 D4)
TEMP_RD     = 60                      # rd60: temp for loading expected values
ACCUM_RD    = 61                      # rd61: XOR+ORR accumulator
EXIT_RD     = 62                      # rd62: exit code / temp
DUMP_RD     = 63                      # rd63: temp for dump
TEMP_RB     = 60                      # rb60: exit port address
MEM_RB      = 61                      # rb61: temp for memory address
DUMP_RB     = 62                      # rb62: dump pointer

# ---------------------------------------------------------------------------
# Instruction encoding helpers (from contracts/opcodes.yaml)
# ---------------------------------------------------------------------------

def encode_set_zw_rd(rdha, wpN, immu16):
    """set.zw rd, wpN, imm16 (rwii, op=0x4C). Clears all bits, sets wyde."""
    return (0x4C << 24) | (rdha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_set_zw_rb(rbha, wpN, immu16):
    """set.zw rb, wpN, imm16 (rwii, op=0x4E). Clears all bits, sets wyde."""
    return (0x4E << 24) | (rbha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_or_w_rd(rdha, wpN, immu16):
    """or.w rd, wpN, imm16 (rwii, op=0x48). ORs wyde."""
    return (0x48 << 24) | (rdha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_or_w_rb(rbha, wpN, immu16):
    """or.w rb, wpN, imm16 (rwii, op=0x4A). ORs wyde."""
    return (0x4A << 24) | (rbha << 18) | (wpN << 16) | (immu16 & 0xFFFF)

def encode_st_o_rd(rdha, rbhb, imms12):
    """st.o rd, rb, offset (rrii, op=0x21). Store RD to memory."""
    return (0x21 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_st_o_rb(rbha, rbhb, imms12):
    """st.o rb, rb, offset (rrii, op=0x23). Store RB to memory."""
    return (0x23 << 24) | (rbha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_xor_o(rdhb, rdhc, rdhd):
    """xor.o rdX, rdY, rdZ (orrr, op=0x40, ha=0x0A). rdX = rdY ^ rdZ."""
    return 0x40280000 | (rdhb << 12) | (rdhc << 6) | rdhd

def encode_or_o(rdhb, rdhc, rdhd):
    """or.o rdX, rdY, rdZ (orrr, op=0x40, ha=0x09). rdX = rdY | rdZ."""
    return 0x40240000 | (rdhb << 12) | (rdhc << 6) | rdhd

def encode_br_nz_rd(rdha, imms18):
    """br.nz rd, offset (riii, op=0x6B). Branch if rd != 0."""
    return (0x6B << 24) | (rdha << 18) | (imms18 & 0x3FFFF)

def encode_jump_rrii(rbha, rdhb, imms12):
    """jump rb, rd, offset (rrii, op=0x71). PC = rb + rd + (offset << 2)."""
    return (0x71 << 24) | (rbha << 18) | (rdhb << 12) | (imms12 & 0xFFF)

def encode_rd2ra(rahb, rdhc, immu6):
    """rd2ra ra, rd, count (orri, op=0x40, ha=0x2D). Block copy RD -> RA."""
    return 0x40B40000 | (rahb << 12) | (rdhc << 6) | (immu6 & 0x3F)

def encode_rb2rd(rdhb, rbhc, immu6):
    """rb2rd rd, rb, count (orri, op=0x40, ha=0x36). Block copy RB -> RD."""
    return 0x40D80000 | (rdhb << 12) | (rbhc << 6) | (immu6 & 0x3F)

def encode_ld_ub(rdha, rbhb, imms12):
    """ld.ub rd, rb, offset (rrii, op=0x10). Load unsigned byte."""
    return (0x10 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_ld_uw(rdha, rbhb, imms12):
    """ld.uw rd, rb, offset (rrii, op=0x11). Load unsigned wyde (2 bytes)."""
    return (0x11 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_ld_ut(rdha, rbhb, imms12):
    """ld.ut rd, rb, offset (rrii, op=0x12). Load unsigned tetra (4 bytes)."""
    return (0x12 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_ld_o(rdha, rbhb, imms12):
    """ld.o rd, rb, offset (rrii, op=0x20). Load octa (8 bytes)."""
    return (0x20 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_swym():
    """swym (iiii, op=0x77). No-op / placeholder."""
    return 0x77000000

def encode_illi():
    """illi (oiii, op=0x00, ha=0x00). Illegal instruction → ILLI fault (0x88)."""
    return 0x00000000

def encode_jump_iiii(imms24):
    """jump imms24 (iiii, op=0x70). PC = rb0 + (imms24 << 2).
    Fields: imms24 split into 4 × 6-bit chunks at [23:18],[17:12],[11:6],[5:0]."""
    return (0x70 << 24) | (imms24 & 0xFFFFFF)


# Width lookup: mnemonic prefix -> (byte_width, encode_fn)
_LD_WIDTH_MAP = {
    'b': (1, encode_ld_ub),
    'w': (2, encode_ld_uw),
    't': (4, encode_ld_ut),
    'o': (8, encode_ld_o),
}

def derive_width_from_mnemonic(mnemonic):
    """Derive memory access width from store mnemonic.

    st.b / stm.b -> 1 byte, st.w / stm.w -> 2 bytes,
    st.t / stm.t -> 4 bytes, st.o / stm.o -> 8 bytes.

    Returns (byte_width, encode_ld_fn).
    """
    # Extract the last character after the final '.'
    suffix = mnemonic.rsplit('.', 1)[-1]
    if suffix not in _LD_WIDTH_MAP:
        raise ValueError(f"Unknown mnemonic suffix for width derivation: {mnemonic}")
    return _LD_WIDTH_MAP[suffix]

# ---------------------------------------------------------------------------
# Emit helpers: load 64-bit value into register
# ---------------------------------------------------------------------------

def emit_load_imm64_rd(rd, value):
    """Emit instructions to load a 64-bit value into an RD register.
    Uses set.zw (clears + sets one wyde) + 3x or.w (merge remaining wydes).
    Wyde order: wp0=bits[15:0], wp1=bits[31:16], wp2=bits[47:32], wp3=bits[63:48]
    """
    words = []
    w0 = value & 0xFFFF
    w1 = (value >> 16) & 0xFFFF
    w2 = (value >> 32) & 0xFFFF
    w3 = (value >> 48) & 0xFFFF

    # First wyde: set.zw clears all bits, then sets one wyde
    words.append(encode_set_zw_rd(rd, 0, w0))
    # Merge remaining wydes
    if w1 != 0:
        words.append(encode_or_w_rd(rd, 1, w1))
    if w2 != 0:
        words.append(encode_or_w_rd(rd, 2, w2))
    if w3 != 0:
        words.append(encode_or_w_rd(rd, 3, w3))
    return words

def emit_load_imm64_rb(rb, value):
    """Emit instructions to load a 64-bit value into an RB register."""
    words = []
    w0 = value & 0xFFFF
    w1 = (value >> 16) & 0xFFFF
    w2 = (value >> 32) & 0xFFFF
    w3 = (value >> 48) & 0xFFFF

    words.append(encode_set_zw_rb(rb, 0, w0))
    if w1 != 0:
        words.append(encode_or_w_rb(rb, 1, w1))
    if w2 != 0:
        words.append(encode_or_w_rb(rb, 2, w2))
    if w3 != 0:
        words.append(encode_or_w_rb(rb, 3, w3))
    return words

# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def build_loader(vector_case):
    """Build loader section: set input_state registers and memory."""
    words = []
    input_state = vector_case.get("input_state") or {}

    # Load RD registers
    rd_state = input_state.get("rd") or {}
    for reg_name, val_str in sorted(rd_state.items()):
        rd_num = int(reg_name.replace("rd", ""))
        if rd_num == 0:
            continue  # rd0 is hardwired zero
        value = int(val_str, 16) if isinstance(val_str, str) else val_str
        words.extend(emit_load_imm64_rd(rd_num, value))

    # Load RB registers
    rb_state = input_state.get("rb") or {}
    for reg_name, val_str in sorted(rb_state.items()):
        rb_num = int(reg_name.replace("rb", ""))
        if rb_num == 0:
            continue  # rb0 is PC
        value = int(val_str, 16) if isinstance(val_str, str) else val_str
        words.extend(emit_load_imm64_rb(rb_num, value))

    # Load RA registers (via rd2ra)
    ra_state = input_state.get("ra") or {}
    for reg_name, val_str in sorted(ra_state.items()):
        ra_num = int(reg_name.replace("ra", ""))
        value = int(val_str, 16) if isinstance(val_str, str) else val_str
        # Load value into TEMP_RD, then rd2ra to target RA
        words.extend(emit_load_imm64_rd(TEMP_RD, value))
        words.append(encode_rd2ra(ra_num, TEMP_RD, 1))

    # Write memory
    memory = input_state.get("memory") or []
    for mem_entry in memory:
        addr = int(mem_entry["address"], 16) if isinstance(mem_entry["address"], str) else mem_entry["address"]
        val = int(mem_entry["value"], 16) if isinstance(mem_entry["value"], str) else mem_entry["value"]
        # Load address into MEM_RB
        words.extend(emit_load_imm64_rb(MEM_RB, addr))
        # Load value into TEMP_RD
        words.extend(emit_load_imm64_rd(TEMP_RD, val))
        # Store: st.o rd, rb, 0
        words.append(encode_st_o_rd(TEMP_RD, MEM_RB, 0))

    return words


def build_test_section(vector_case):
    """Build test section: raw encoding word."""
    word_str = vector_case["encoding"]["word"]
    instr_word = int(word_str, 16)
    return [instr_word]


def build_dumper_section():
    """Build dumper section: dump rd/rb to state-dump region.

    State-dump layout (at DUMP_BASE):
      offset 0x0000: rd[0] slot  (8 bytes, reserved, not written; rd0 hardwired zero)
      offset 0x0008..0x01F8: rd[1..63]  (63 × 8 bytes = 504 bytes, big-endian)
      offset 0x0200: rb[0] slot  (8 bytes, reserved, not written; rb0=PC stored at +0x400)
      offset 0x0208..0x03F8: rb[1..63]  (63 × 8 bytes = 504 bytes, big-endian)
      offset 0x0400: pc (rb0 via rb2rd→st.o-rd)  (8 bytes, big-endian)
      Total: 1032 bytes (DUMP_SIZE = 0x408)

    Note: rd0=0 (hardwired), rb0=PC are special; rd[0]/rb[0] slots reserved (not written).
    """
    words = []

    # Set up DUMP_RB = DUMP_BASE
    words.extend(emit_load_imm64_rb(DUMP_RB, DUMP_BASE))

    # Dump rd[1..63]
    for i in range(1, 64):
        offset = i * 8
        if offset < 0x200:  # Within rd dump region
            words.append(encode_st_o_rd(i, DUMP_RB, offset))

    # Set up DUMP_RB = DUMP_BASE + 0x0200 for rb dump
    # We already have DUMP_RB = DUMP_BASE, use offset 0x200 directly
    # But 0x200 = 512, imms12 max = 2047, so we can use offset directly
    for i in range(1, 64):
        offset = 0x200 + i * 8
        if offset < 0x400:  # Within rb dump region
            words.append(encode_st_o_rb(i, DUMP_RB, offset))

    # Dump rb0 (PC) at offset 0x0400
    # st.o-rb requires rbha != rb0 (legality), so we use rb2rd to copy
    # rb0 into a scratch RD, then st.o-rd to store it.
    words.append(encode_rb2rd(DUMP_RD, 0, 1))   # rd63 = rb0 (PC)
    words.append(encode_st_o_rd(DUMP_RD, DUMP_RB, 0x400))

    return words


def build_exit_section(vector_case, dump_mode=False):
    """Build exit section: compare expected state and write exit code.

    For encoding/overlap class: write 0x00 (PASS) directly.
    For semantic/boundary class: compare expected vs actual, write PASS/FAIL.
    For legality class with expected_fault: write safety net FAIL (if fault
    doesn't happen, we want to know).
    """
    words = []
    expected_state = vector_case.get("expected_state")
    expected_fault = vector_case.get("expected_fault")

    # Set up exit port address in TEMP_RB
    words.extend(emit_load_imm64_rb(TEMP_RB, EXIT_PORT))

    # Initialize accumulator
    words.extend(emit_load_imm64_rd(ACCUM_RD, 0))

    if expected_state and isinstance(expected_state, dict):
        # Compare expected RD registers
        rd_expected = expected_state.get("rd") or {}
        for reg_name, val_str in sorted(rd_expected.items()):
            rd_num = int(reg_name.replace("rd", ""))
            if rd_num == 0:
                continue  # rd0 is always 0
            expected_val = int(val_str, 16) if isinstance(val_str, str) else val_str
            # Load expected value into TEMP_RD
            words.extend(emit_load_imm64_rd(TEMP_RD, expected_val))
            # XOR with actual register
            words.append(encode_xor_o(TEMP_RD, TEMP_RD, rd_num))
            # OR into accumulator
            words.append(encode_or_o(ACCUM_RD, ACCUM_RD, TEMP_RD))

        # Compare expected RB registers
        rb_expected = expected_state.get("rb") or {}
        for reg_name, val_str in sorted(rb_expected.items()):
            rb_num = int(reg_name.replace("rb", ""))
            if rb_num == 0:
                continue  # rb0 is PC, handled separately via D6 poison pattern
            expected_val = int(val_str, 16) if isinstance(val_str, str) else val_str
            # Load expected value into TEMP_RD
            words.extend(emit_load_imm64_rd(TEMP_RD, expected_val))
            # Copy actual RB into DUMP_RD via rb2rd
            words.append(encode_rb2rd(DUMP_RD, rb_num, 1))
            # XOR actual vs expected
            words.append(encode_xor_o(TEMP_RD, TEMP_RD, DUMP_RD))
            # OR into accumulator
            words.append(encode_or_o(ACCUM_RD, ACCUM_RD, TEMP_RD))

        # Compare expected RA registers
        ra_expected = expected_state.get("ra") or {}
        for reg_name, val_str in sorted(ra_expected.items()):
            ra_num = int(reg_name.replace("ra", ""))
            expected_val = int(val_str, 16) if isinstance(val_str, str) else val_str
            # Load expected value into TEMP_RD
            words.extend(emit_load_imm64_rd(TEMP_RD, expected_val))
            # Use ra2rd to read actual RA value
            # ra2rd rdX, raY, count (orri, op=0x40, ha=0x2E)
            words.append(0x40B80000 | (DUMP_RD << 12) | (ra_num << 6) | 1)
            # XOR with expected
            words.append(encode_xor_o(TEMP_RD, TEMP_RD, DUMP_RD))
            # OR into accumulator
            words.append(encode_or_o(ACCUM_RD, ACCUM_RD, TEMP_RD))

        # Compare expected memory entries
        memory = expected_state.get("memory") or []
        if memory:
            # Derive width and load encoding from mnemonic (constant per vector)
            _, encode_ld_fn = derive_width_from_mnemonic(vector_case["mnemonic"])
            for entry in memory:
                addr = int(entry["address"], 16) if isinstance(entry["address"], str) else entry["address"]
                expected_val = int(entry["value"], 16) if isinstance(entry["value"], str) else entry["value"]
                # Load address into MEM_RB(61)
                words.extend(emit_load_imm64_rb(MEM_RB, addr))
                # Read actual memory into DUMP_RD(63) using unsigned load
                words.append(encode_ld_fn(DUMP_RD, MEM_RB, 0))
                # Load expected value into TEMP_RD(60)
                words.extend(emit_load_imm64_rd(TEMP_RD, expected_val))
                # XOR actual vs expected
                words.append(encode_xor_o(TEMP_RD, TEMP_RD, DUMP_RD))
                # OR into accumulator
                words.append(encode_or_o(ACCUM_RD, ACCUM_RD, TEMP_RD))

    # Write exit code based on comparison result
    if expected_fault:
        # Legality case: expect fault, safety net if fault doesn't happen
        words.extend(emit_load_imm64_rd(EXIT_RD, 1))  # FAIL code
        words.append(encode_st_o_rd(EXIT_RD, TEMP_RB, 0))
    elif dump_mode:
        # Dump mode: spin instead of writing exit port
        # jump rb0, rd0, 0 -> spin at current PC
        words.append(encode_jump_rrii(0, 0, 0))
    else:
        # Normal mode: compare and write exit code
        # If ACCUM_RD != 0 -> FAIL
        num_cmp_instrs = len(words)
        # br.nz rd61, offset_to_fail
        # Layout:
        #   [here] br.nz rd61, N    -> if != 0, jump to fail
        #   [here+1] set.zw rd62, 0 -> PASS
        #   [here+2] st.o rd62, rb60, 0 -> write 0x00
        #   [here+3] jump rb0, rd0, M -> jump to done
        #   [here+4] set.zw rd62, 1 -> FAIL
        #   [here+5] st.o rd62, rb60, 0 -> write 0x01
        #   [here+6] done
        # br.nz offset = 4 (jump to [here+4])
        words.append(encode_br_nz_rd(ACCUM_RD, 4))
        # PASS
        words.extend(emit_load_imm64_rd(EXIT_RD, 0))
        words.append(encode_st_o_rd(EXIT_RD, TEMP_RB, 0))
        # Jump over FAIL section (offset = 3 -> jump to [here+6])
        words.append(encode_jump_rrii(0, 0, 3))
        # FAIL
        words.extend(emit_load_imm64_rd(EXIT_RD, 1))
        words.append(encode_st_o_rd(EXIT_RD, TEMP_RB, 0))

    return words


def build_branch_test_binary(vector_case, dump_mode=False):
    """Build test binary for branch/jump semantic tests (expected_pc != None).

    Uses poison pattern to verify branch/jump behavior.
    delta = expected_pc - BINARY_BASE (ADR-0009 D6).

    TAKEN layout (delta=8):
      [loader] [branch] [illi] [exit section]
      - branch target (imm=2, PC+8) = illi+1 = exit section start → PASS
      - if branch wrongly NOT taken → falls into illi → ILLI(0x88) → FAIL

    NOT-TAKEN layout (delta=4):
      [loader] [branch] [trampoline jump→exit] [illi] [exit section]
      - branch target (imm=2, PC+8) = illi → ILLI(0x88) if wrongly taken
      - if branch correctly NOT taken → falls through to trampoline → jumps
        over illi to exit section → PASS

    v5 branch base = instruction's own PC (Addr = rb0 + (imm<<2)).
    trampoline: jump-iiii with imms24=2 → target = PC + 8 = exit section.
    """
    words = []
    expected_pc = vector_case.get("expected_pc")
    delta = int(expected_pc, 16) - BINARY_BASE

    # Section 1: loader (set input_state registers)
    words.extend(build_loader(vector_case))

    # Section 2: test instruction (branch/jump encoding)
    words.extend(build_test_section(vector_case))

    if delta == 8:
        # TAKEN: [branch] [illi] [exit section]
        # branch jumps over illi to exit; not-taken falls into illi
        words.append(encode_illi())
    elif delta == 4:
        # NOT-TAKEN: [branch] [trampoline] [illi] [exit section]
        # branch target = PC+8 = illi (poison)
        # falls through → trampoline jumps over illi to exit
        words.append(encode_jump_iiii(2))  # PC + (2<<2) = PC+8 = exit section
        words.append(encode_illi())
    else:
        raise ValueError(f"Unexpected delta={delta} (expected_pc={expected_pc}, BINARY_BASE=0x{BINARY_BASE:X})")

    # Section 3: dumper (diagnostics only in dump mode)
    if dump_mode:
        words.extend(build_dumper_section())

    # Section 4: exit (compare + write exit code)
    words.extend(build_exit_section(vector_case, dump_mode))

    # Pack as big-endian 32-bit words
    blob = b""
    for w in words:
        blob += struct.pack(">I", w)

    return blob


def build_test_binary(vector_case, trusted_instrs=None, dump_mode=False):
    """Build complete test binary for a vector case.

    Args:
        vector_case: Vector case dict from YAML
        trusted_instrs: (unused) Trusted instruction encodings from contracts/opcodes.yaml
            Kept for API compatibility with task spec; encodings are hardcoded in helpers.
        dump_mode: If True, exit section spins instead of writing exit port

    Returns bytes to be loaded at BINARY_BASE.
    """
    # Branch/jump semantic: dispatch to specialized builder
    if vector_case.get("expected_pc") is not None:
        return build_branch_test_binary(vector_case, dump_mode)

    words = []

    # Section 1: loader
    words.extend(build_loader(vector_case))

    # Section 2: test instruction
    words.extend(build_test_section(vector_case))

    # Section 3: dumper (for diagnostics) — ADR-0010 D1 修法 a:
    # only emit dumper in dump mode. Normal mode doesn't need it
    # (pass/fail determined by guest comparison in exit section).
    # Dumper uses st.o-rb + rb2rd which cause TCG code-size timeout
    # when emitted unconditionally (130+ instructions).
    if dump_mode:
        words.extend(build_dumper_section())

    # Section 4: exit (compare + write exit code)
    words.extend(build_exit_section(vector_case, dump_mode))

    # Pack as big-endian 32-bit words
    blob = b""
    for w in words:
        blob += struct.pack(">I", w)

    return blob


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build test binary from ISA vector YAML")
    parser.add_argument("vector_file", help="Path to vector YAML file")
    parser.add_argument("--case", type=int, default=None,
                        help="Case index to build (0-based). If omitted, builds first semantic case.")
    parser.add_argument("--dump", action="store_true",
                        help="Build in dump mode (spin after dumper, no exit port write)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output binary file path")
    args = parser.parse_args()

    # Load vector file
    with open(args.vector_file, "r") as f:
        cases = yaml.safe_load(f)

    if not isinstance(cases, list):
        print(f"Error: vector file does not contain a list", file=sys.stderr)
        sys.exit(1)

    # Select case
    if args.case is not None:
        if args.case >= len(cases):
            print(f"Error: case index {args.case} out of range (0-{len(cases)-1})", file=sys.stderr)
            sys.exit(1)
        case = cases[args.case]
    else:
        # Find first semantic/encoding case
        case = None
        for i, c in enumerate(cases):
            if c.get("class") in ("semantic", "encoding", "boundary"):
                case = c
                break
        if case is None:
            print(f"Error: no semantic/encoding/boundary case found", file=sys.stderr)
            sys.exit(1)

    # Build binary
    blob = build_test_binary(case, dump_mode=args.dump)

    # Output
    if args.output:
        with open(args.output, "wb") as f:
            f.write(blob)
        print(f"Wrote {len(blob)} bytes to {args.output}")
    else:
        # Write to stdout
        sys.stdout.buffer.write(blob)


if __name__ == "__main__":
    main()
