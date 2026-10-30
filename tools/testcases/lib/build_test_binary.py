#!/usr/bin/env python3
"""Build test binary from ISA vector YAML for dadao-m1 QEMU testing.

Binary layout (loaded at BINARY_BASE = 0xFC00_0000_0000, the single RAM segment):
  [section 1] loader   - Set rd/rb/ra registers from input_state, write memory
  [section 2] test     - Raw encoding word(s) (struct.pack('>I', w); the
                         optional `sequence:` emits several in order)
  [section 3] dumper   - Dump state to state-dump region (diagnostics only)
  [section 4] exit     - Compare expected_state with actual, write exit code

Design decisions (ADR-0009):
  D1: raw-encoding via struct.pack, no llvm-mc
  D2: guest-internal comparison via XOR+ORR accumulator
  D4: RD scratch=rd60-63, RB scratch=rb60-63, RA not scratch
  D5: exit code 0x00=PASS, 0x01-0x7F=FAIL, 0x80+=machine fault

Exit channel (ADR-0020 D8: semihosting SYS_EXIT replaces the legacy MMIO halt device):
  the PASS/FAIL epilogue writes the 64-bit argument block
  {ADP_Stopped_ApplicationExit, code} into RAM and issues
  `rd16 = 0x18 (SYS_EXIT); rb16 = block; trap` -- the reported status is the
  low byte of `code` (contract-semihosting.md §3/§5).  The harness must run
  QEMU with `-semihosting-config enable=on,target=native` (ADR-0020 D7).
  Machine faults still surface as QEMU's own exit code (0x80|cause_bit), not
  through SYS_EXIT.

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

# Memory map (ADR-0004 R3 + rev. 2026-10-11 / ADR-0020 D15): the single RAM
# segment is at 0xFC00_0000_0000 (16 MiB, cfxha 63).
BINARY_BASE = 0xFC00_0000_0000        # RAM entry point
# SYS_EXIT argument block {reason, code} (ADR-0020 D8).  Writable RAM near the
# top, above the downward-growing stack (SP starts at RAM + 0x00ff_0000).
EXIT_BLOCK  = 0xFC00_00FD_0000        # SYS_EXIT argument-block address
DUMP_BASE   = 0xFC00_00FE_0000        # State-dump region base
DUMP_SIZE   = 0x408                  # 1032 bytes: rd[0]+rd[1..63]+rb[0]+rb[1..63]+pc
RD_DUMP_OFF = 0x008                  # rd[1] starts at +0x008 (rd[0] slot at +0x000 is reserved)
RB_DUMP_OFF = 0x208                  # rb[1] starts at +0x208 (rb[0] slot at +0x200 is reserved)
PC_DUMP_OFF = 0x400                  # pc (rb0 via rb2rd→st.o-rd) at +0x400

# Semihosting SYS_EXIT (contract-semihosting.md §1/§3/§5; ADR-0020 D1/D8)
SEMIHOST_TAG = 0x3FF00               # immu18[17:8] == 0x3FF (0x3FF00-0x3FFFF) -> semihosting trap
SYS_EXIT = 0x18                      # SYS_EXIT service number
ADP_STOPPED_APPLICATION_EXIT = 0x20026

# Register conventions (ADR-0009 D4)
TEMP_RD     = 60                      # rd60: temp for loading expected values
ACCUM_RD    = 61                      # rd61: XOR+ORR accumulator
EXIT_RD     = 62                      # rd62: exit code / temp
DUMP_RD     = 63                      # rd63: temp for dump
MEM_RB      = 61                      # rb61: temp for memory address
DUMP_RB     = 62                      # rb62: dump pointer

# Window the harness treats as "code of the test image".  Vectors are written
# with the tested instruction at BINARY_BASE (ADR-0004 D2.2), so a value inside
# this window denotes a location *in the image* and must move with the loader
# prologue inserted in front of the instruction; anything outside it is an
# absolute data address (RAS entry, MRPTR, ...) and stays as the vector wrote it.
IMAGE_WINDOW = 0x10000

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

def encode_st_b_rd(rdha, rbhb, imms12):
    """st.b rd, rb, offset (rrii, op=0x18). Store RD byte to memory."""
    return (0x18 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_st_w_rd(rdha, rbhb, imms12):
    """st.w rd, rb, offset (rrii, op=0x19). Store RD wyde (2 bytes) to memory."""
    return (0x19 << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_st_t_rd(rdha, rbhb, imms12):
    """st.t rd, rb, offset (rrii, op=0x1A). Store RD tetra (4 bytes) to memory."""
    return (0x1A << 24) | (rdha << 18) | (rbhb << 12) | (imms12 & 0xFFF)

def encode_st_o_rd(rdha, rbhb, imms12):
    """st.o rd, rb, offset (rrii, op=0x21). Store RD octa (8 bytes) to memory."""
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
    """swym (oiii, op=0x47, ha=0x22). No-op / placeholder. word=0x47880000."""
    return 0x47880000

def encode_illi_poison():
    """ILLI 毒饵：word=0x79001000（`fence cfx0, hb=1`）。

    `fence` 的 `hb = immu18[17:12]` 为 SBZ，非 0 ⇒ ILLI（`encode_sbz`，SimRISC-11
    §屏障指令）；与 cfx 资源域/权限无关，也不会随指令增删而失效。QEMU
    `trans_fence_ciii_cfx` 对该编码调 `gen_exception_illegal` ⇒ ILLI(0x88)。
    """
    return 0x79001000

def encode_jump_iiii(imms24):
    """jump imms24 (iiii, op=0x70). PC = rb0 + (imms24 << 2).
    Fields: imms24 split into 4 × 6-bit chunks at [23:18],[17:12],[11:6],[5:0]."""
    return (0x70 << 24) | (imms24 & 0xFFFFFF)

def encode_trap(cfxha, immu18):
    """trap cfxha, immu18 (ciii, op=0x7F).
    Fields: cfxha[23:18], immu18[17:0].  immu18[17:8]==0x3FF (0x3FF00-0x3FFFF) selects the
    semihosting short-circuit (contract-semihosting.md §1; ADR-0020 D1)."""
    return (0x7F << 24) | (cfxha << 18) | (immu18 & 0x3FFFF)


def _relocate_code_addr(value, shift):
    """Shift the 48-bit address field of a RAS value when it denotes code in the
    test image (see IMAGE_WINDOW); the recursive count in [63:48] is kept.

    Values outside the image window (absolute data addresses) are returned
    unchanged — shifting those would fabricate addresses the vector never
    mentions (e.g. the MemRAS spill target derived from MRPTR).
    """
    if not shift:
        return value
    count = value >> 48
    addr = value & 0xFFFFFFFFFFFF
    if BINARY_BASE <= addr < BINARY_BASE + IMAGE_WINDOW:
        addr += shift
    return (count << 48) | (addr & 0xFFFFFFFFFFFF)


# Width lookup: mnemonic suffix -> (byte_width, encode_ld_fn)
_LD_WIDTH_MAP = {
    'b': (1, encode_ld_ub),
    'w': (2, encode_ld_uw),
    't': (4, encode_ld_ut),
    'o': (8, encode_ld_o),
}

# Store encoding lookup: mnemonic suffix -> encode_st_fn (rd form)
_ST_WIDTH_MAP = {
    'b': encode_st_b_rd,
    'w': encode_st_w_rd,
    't': encode_st_t_rd,
    'o': encode_st_o_rd,
}

# Instruction families whose mnemonic encodes the memory access width
# (SimRISC-01 取数存数 / SimRISC-02 寄存器复制 / SimRISC-12 原子指令).
_WIDTH_BEARING_FAMILIES = ("ld", "st", "ldm", "stm", "lr", "sc")

# Neutral access for the memory payload of every other instruction: the
# `input_state.memory` / `expected_state.memory` entries of a non-load/store
# case are plain 64-bit data words (e.g. a RAS entry), i.e. exactly one octa.
_OCT_WIDTH = (8, encode_ld_o, encode_st_o_rd)

# contracts/opcodes.yaml is the single source of truth for the mnemonic set
# (lazy-loaded: the harness must also import cleanly for stand-alone checks).
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_OPCODES_PATH = os.path.join(_ROOT_DIR, "contracts", "opcodes.yaml")
_KNOWN_MNEMONICS = None

def known_mnemonics():
    """Return the set of mnemonics defined in contracts/opcodes.yaml.

    Raises RuntimeError when the table is missing: without it an unknown
    mnemonic cannot be told apart from a data-only one, and guessing would
    silently pick a wrong access width (ISS-098).
    """
    global _KNOWN_MNEMONICS
    if _KNOWN_MNEMONICS is None:
        if not os.path.isfile(_OPCODES_PATH):
            raise RuntimeError(
                "contracts/opcodes.yaml not found (looked at %s); the mnemonic "
                "set is required for memory-width derivation" % _OPCODES_PATH)
        with open(_OPCODES_PATH) as f:
            table = yaml.safe_load(f)
        _KNOWN_MNEMONICS = {r["mnemonic"] for r in table if r.get("mnemonic")}
    return _KNOWN_MNEMONICS


def case_label(vector_case):
    """Human-readable case tag used in error messages (`id` + mnemonic)."""
    cid = vector_case.get("id", "<no id>")
    mnem = vector_case.get("mnemonic", "<no mnemonic>")
    return f"case {cid!r} (mnemonic {mnem!r})"


def derive_width_from_mnemonic(mnemonic):
    """Derive memory access width from a width-bearing mnemonic.

    Only `ld`/`st`/`ldm`/`stm`/`lr`/`sc` carry the access width in their
    mnemonic; ask `derive_memory_width()` for the case-level answer (it also
    handles data-only instructions such as `call`/`ret`).

    Uses the last character of the width suffix to determine width:
    b->1, w->2, t->4, o->8. Handles ld.ub/uw/ut/sb/sw/st, st.b/w/t/o,
    ldm.ub/uw/ut/sb/sw/st, stm.b/w/t/o.

    `lr`/`sc` carry the width as the SECOND dot-separated segment
    (`lr.o.nn`, `sc.t.ar`; ADR-0034 D3: width first, storage order second), so
    their width token is not the last segment.  Everything else keeps the
    existing last-segment rule (default path unchanged).

    Returns (byte_width, encode_ld_fn, encode_st_fn).
    """
    parts = mnemonic.split('.')
    if parts[0] in ("lr", "sc") and len(parts) >= 2:
        width_token = parts[1]
    else:
        width_token = parts[-1]
    width_char = width_token[-1]  # last char: b/w/t/o
    if width_char not in _LD_WIDTH_MAP:
        raise ValueError(f"Unknown mnemonic suffix for width derivation: {mnemonic}")
    byte_width, encode_ld_fn = _LD_WIDTH_MAP[width_char]
    encode_st_fn = _ST_WIDTH_MAP[width_char]
    return byte_width, encode_ld_fn, encode_st_fn


def derive_memory_width(vector_case):
    """Return (byte_width, encode_ld_fn, encode_st_fn) for the case's memory payload.

    * width-bearing mnemonic (`ld.*`/`st.*`/`ldm.*`/`stm.*`/`lr.*`/`sc.*`) —
      the access width is the instruction's width (ADR-0009 补注续二);
    * any other mnemonic that exists in contracts/opcodes.yaml — the memory
      payload is plain data, accessed as one octa (`call`'s spilled RAS entry,
      `ret`'s MemRAS entry, ...);
    * anything else — explicit error naming the case, never a silent guess
      (ISS-098: `call` used to raise a bare ValueError and `ret` was silently
      treated as a 4-byte access because the mnemonic ends in `t`).
    """
    mnemonic = vector_case.get("mnemonic") or ""
    if not mnemonic:
        # No mnemonic to derive from (e.g. hand-written probe cases): keep the
        # historical octa default.
        return _OCT_WIDTH
    if mnemonic.split('.')[0] in _WIDTH_BEARING_FAMILIES:
        try:
            return derive_width_from_mnemonic(mnemonic)
        except ValueError as exc:
            raise ValueError(f"{case_label(vector_case)}: {exc}") from None
    if mnemonic not in known_mnemonics():
        raise ValueError(
            f"{case_label(vector_case)}: unknown mnemonic {mnemonic!r} "
            f"(not in {_OPCODES_PATH}); cannot derive the memory access width")
    return _OCT_WIDTH

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

def emit_sys_exit(code_rd):
    """Emit the semihosting SYS_EXIT epilogue (ADR-0020 D8).

    Writes the 64-bit argument block {ADP_Stopped_ApplicationExit, code} to
    EXIT_BLOCK in RAM, then issues
        rd16 = 0x18 (SYS_EXIT); rb16 = EXIT_BLOCK; trap (semihosting tag).
    `code_rd` is the register holding the exit code; its low byte becomes the
    host process status (contract-semihosting.md §3/§5).  SYS_EXIT never
    returns, so the emitted block must end the program.
    """
    words = []
    # rb16 = EXIT_BLOCK (argument-block pointer)
    words.extend(emit_load_imm64_rb(16, EXIT_BLOCK))
    # block[0] = 0x20026 (ADP_Stopped_ApplicationExit)
    words.extend(emit_load_imm64_rd(16, ADP_STOPPED_APPLICATION_EXIT))
    words.append(encode_st_o_rd(16, 16, 0))
    # block[1] = exit code (low byte = host status)
    words.append(encode_st_o_rd(code_rd, 16, 8))
    # rd16 = SYS_EXIT; trap with the semihosting tag
    words.extend(emit_load_imm64_rd(16, SYS_EXIT))
    words.append(encode_trap(0, SEMIHOST_TAG))
    return words

# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def build_loader(vector_case):
    """Build loader section: set input_state registers and memory.

    Memory writes use width-appropriate store (st.b/w/t/o) derived from
    the vector's mnemonic, per ADR-0009 补注续二.
    """
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

    # Write memory (width-appropriate store per ADR-0009 补注续二)
    memory = input_state.get("memory") or []
    if memory:
        # Store width from the case (load/store width, else one octa per entry)
        _, _, encode_st_fn = derive_memory_width(vector_case)
        for mem_entry in memory:
            addr = int(mem_entry["address"], 16) if isinstance(mem_entry["address"], str) else mem_entry["address"]
            val = int(mem_entry["value"], 16) if isinstance(mem_entry["value"], str) else mem_entry["value"]
            # Load address into MEM_RB
            words.extend(emit_load_imm64_rb(MEM_RB, addr))
            # Load value into TEMP_RD
            words.extend(emit_load_imm64_rd(TEMP_RD, val))
            # Store: st.b/w/t/o rd, rb, 0 (width from mnemonic)
            words.append(encode_st_fn(TEMP_RD, MEM_RB, 0))

    return words, len(words)


def build_test_section(vector_case):
    """Build test section: the instruction(s) under test.

    Default (unchanged, byte-identical): exactly one raw encoding word from
    ``encoding.word``.

    Optional ``sequence: [word, word, ...]`` emits several raw encoding words
    back to back.  It exists for `sc`, whose success path is only reachable
    after a same-address `lr` (SimRISC-12 原子指令) and therefore cannot be
    expressed by a single instruction (QEMU-067t; see the task book's
    "已知边界").  When ``sequence`` is absent the behaviour is byte-identical
    to before.
    """
    sequence = vector_case.get("sequence")
    if sequence:
        return [int(w, 16) if isinstance(w, str) else w for w in sequence]
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


def build_exit_section(vector_case, dump_mode=False, loader_words=0, relocate_ra=False):
    """Build exit section: compare expected state and report via SYS_EXIT.

    For encoding/overlap class: report 0x00 (PASS) directly.
    For semantic/boundary class: compare expected vs actual, report PASS/FAIL.
    For legality class with expected_fault: report safety-net FAIL (if fault
    doesn't happen, we want to know).

    The exit channel is the semihosting SYS_EXIT service (ADR-0020 D8): the
    epilogue writes {ADP_Stopped_ApplicationExit, code} to RAM and traps with
    the semihosting tag, so the host `$?` is `code`'s low byte.  Machine faults
    still surface as QEMU's own exit code (0x80|cause_bit).

    Args:
        loader_words: Number of 32-bit words in the loader section.
        relocate_ra: If True, adjust expected_state.ra low 48 bits by
            loader_words*4 (for call push return address relocation).
            Only enabled for call semantic cases; other RA writes (rd2ra etc.)
            do not need relocation.
    """
    words = []
    expected_state = vector_case.get("expected_state")
    expected_fault = vector_case.get("expected_fault")

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
        # Code-address relocation (P1): a vector's RA entry may hold the
        # instruction's return address (PC+4 == BINARY_BASE+4) because the
        # vector assumes the tested instruction sits at BINARY_BASE.  The
        # harness inserts a loader prologue, so the actual return address is
        # BINARY_BASE + loader_bytes + 4: shift only addresses that point into
        # the image window, leaving absolute data addresses (stale RAS entries,
        # MRPTR) untouched.
        # Only for call push return addresses (relocate_ra=True); other RA
        # writes (rd2ra etc.) store raw values that don't need relocation.
        ra_expected = expected_state.get("ra") or {}
        loader_bytes = loader_words * 4 if relocate_ra else 0
        for reg_name, val_str in sorted(ra_expected.items()):
            ra_num = int(reg_name.replace("ra", ""))
            expected_val = int(val_str, 16) if isinstance(val_str, str) else val_str
            expected_val = _relocate_code_addr(expected_val, loader_bytes)
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
            # Access width from the case (load/store width, else one octa)
            _, encode_ld_fn, _ = derive_memory_width(vector_case)
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

    # Report via SYS_EXIT based on the comparison result.
    if expected_fault:
        # Legality case: expect fault, safety net if fault doesn't happen
        words.extend(emit_load_imm64_rd(EXIT_RD, 1))  # FAIL code
        words.extend(emit_sys_exit(EXIT_RD))
    elif dump_mode:
        # Dump mode: spin instead of exiting
        # jump rb0, rd0, 0 -> spin at current PC
        words.append(encode_jump_rrii(0, 0, 0))
    else:
        # Normal mode: compare and exit via SYS_EXIT
        # Layout (word indices from the br.nz itself):
        #   [b]                 br.nz rd61, N  -> if != 0, jump to FAIL block
        #   [b+1 .. b+P]        PASS block: EXIT_RD = 0; SYS_EXIT  (P words)
        #   [b+P+1 ..]          FAIL block: EXIT_RD = 1; SYS_EXIT
        # v5 branch base = the br.nz instruction's own PC (ISS-309): the offset
        # is derived from the word indices, so `N = (fail start) - (br index)`.
        pass_block = emit_load_imm64_rd(EXIT_RD, 0) + emit_sys_exit(EXIT_RD)
        fail_block = emit_load_imm64_rd(EXIT_RD, 1) + emit_sys_exit(EXIT_RD)
        br_index = len(words)
        fail_index = br_index + 1 + len(pass_block)
        words.append(encode_br_nz_rd(ACCUM_RD, fail_index - br_index))
        words.extend(pass_block)
        words.extend(fail_block)

    return words


def build_branch_test_binary(vector_case, dump_mode=False):
    """Build test binary for branch/jump semantic tests (expected_pc != None).

    Uses poison pattern to verify branch/jump behavior.
    delta = expected_pc - BINARY_BASE (ADR-0009 D6).

    TAKEN layout (delta=8):
      [loader] [branch] [fence-hb→ILLI poison] [exit section]
      - branch target (imm=2, PC+8) = poison+1 = exit section start → PASS
      - if branch wrongly NOT taken → falls into poison → ILLI(0x88) → FAIL

    NOT-TAKEN layout (delta=4):
      [loader] [branch] [trampoline jump→exit] [fence-hb→ILLI poison] [exit section]
      - branch target (imm=2, PC+8) = poison → ILLI(0x88) if wrongly taken
      - if branch correctly NOT taken → falls through to trampoline → jumps
        over poison to exit section → PASS

    v5 branch base = instruction's own PC (Addr = rb0 + (imm<<2)).
    trampoline: jump-iiii with imms24=2 → target = PC + 8 = exit section.
    """
    words = []
    expected_pc = vector_case.get("expected_pc")
    delta = int(expected_pc, 16) - BINARY_BASE

    # Section 1: loader (set input_state registers)
    # For call semantic cases, shift the *code* addresses in input_state.ra by
    # loader_bytes: the vector writes the return address as PC+4 for an
    # instruction at BINARY_BASE, while the harness executes the call after the
    # loader, so the actual return address is BINARY_BASE + loader_bytes + 4.
    # That keeps the C2 recursive-fold path reachable (ra63 low48 == return
    # address) without fabricating absolute data addresses: MRPTR, spilled
    # entries and stale RAS addresses outside the image window are left alone
    # (the expected MemRAS spill target must keep matching MRPTR).
    # expected_state.ra is shifted the same way in build_exit_section.
    import copy
    if delta == 8 and vector_case.get("mnemonic") == "call":
        adj_case = copy.deepcopy(vector_case)
        adj_input = adj_case.get("input_state") or {}
        adj_ra = adj_input.get("ra") or {}
        # Pre-compute loader_words from original input_state
        _, pre_loader_words = build_loader(vector_case)
        loader_bytes = pre_loader_words * 4
        if loader_bytes > 0:
            for reg_name, val_str in list(adj_ra.items()):
                val = int(val_str, 16) if isinstance(val_str, str) else val_str
                shifted = _relocate_code_addr(val, loader_bytes)
                if shifted != val:
                    adj_ra[reg_name] = hex(shifted)
        loader_words_list, loader_words = build_loader(adj_case)
    else:
        loader_words_list, loader_words = build_loader(vector_case)
    words.extend(loader_words_list)

    # Section 2: test instruction (branch/jump encoding)
    words.extend(build_test_section(vector_case))

    if delta == 8:
        # TAKEN: [branch] [fence-hb→ILLI poison] [exit section]
        # branch jumps over poison to exit; not-taken falls into poison
        words.append(encode_illi_poison())
    elif delta == 4:
        # NOT-TAKEN: [branch] [trampoline] [fence-hb→ILLI poison] [exit section]
        # branch target = PC+8 = poison
        # falls through → trampoline jumps over poison to exit
        words.append(encode_jump_iiii(2))  # PC + (2<<2) = PC+8 = exit section
        words.append(encode_illi_poison())
    else:
        raise ValueError(f"Unexpected delta={delta} (expected_pc={expected_pc}, BINARY_BASE=0x{BINARY_BASE:X})")

    # Section 3: dumper (diagnostics only in dump mode)
    if dump_mode:
        words.extend(build_dumper_section())

    # Section 4: exit (compare + write exit code)
    # RA relocation only for call semantic cases (unconditional jump with RA push)
    is_call = delta == 8 and vector_case.get("mnemonic") == "call"
    words.extend(build_exit_section(vector_case, dump_mode, loader_words=loader_words, relocate_ra=is_call))

    # Pack as big-endian 32-bit words
    blob = b""
    for w in words:
        blob += struct.pack(">I", w)

    return blob


def build_ret_binary(vector_case, dump_mode=False):
    """Build a test binary for `ret` semantic cases from the vector itself.

    Layout (word indices; L = (expected_pc - BINARY_BASE) / 4):

      w0            jump → loader (skips the landing-pad area)
      w1..w(L-1)    swym filler (never executed)
      wL            landing pad: jump → exit section
      w(L+1)..      loader: `input_state` as written in the vector (rd/rb/ra/memory)
      w(L+1+k)      ret: the vector's instruction (`encoding.word`)
      +1            fence-hb→ILLI poison (safety net: reached only if `ret` falls through)
      [+dumper]     dump mode only
      exit          compare `expected_state`, report via SYS_EXIT

    Execution: w0 → loader → ret → (PC = RA target = expected_pc) → wL →
    exit section → PASS/FAIL.

    Why this shape (ISS-098):
      - `ret` takes its target from the return-address stack, so the vector's
        `input_state.ra` (and the MemRAS entry in `input_state.memory`) is used
        verbatim: no synthetic `call` overwrites ra63 any more, and
        `expected_state.ra` is compared without relocation.
      - The only harness-provided piece is the landing pad *at* the vector's
        own expected_pc: `ret` must land on executable code to let the state
        comparison run.  The pad index is derived from expected_pc, so a `ret`
        that returns anywhere other than the vector's target never reaches the
        exit section (fault or poison) and the case cannot PASS.
      - expected_pc must therefore denote an address the harness can populate
        (inside the image window).  A vector that claims an unmapped return
        target cannot be observed by the harness: it is rejected explicitly —
        that shape belongs in a legality case (`expected_fault: UNMAPPED`).
    """
    expected_pc = vector_case.get("expected_pc")
    if expected_pc is None:
        raise ValueError(
            f"{case_label(vector_case)}: build_ret_binary needs expected_pc "
            f"(the return target); cases without it go through the default "
            f"builder")
    if vector_case.get("sequence"):
        raise ValueError(
            f"{case_label(vector_case)}: `sequence` is not supported for ret "
            f"(the landing-pad layout places exactly one instruction under test)")
    target = int(expected_pc, 16) if isinstance(expected_pc, str) else expected_pc
    offset = target - BINARY_BASE
    if offset % 4:
        raise ValueError(
            f"{case_label(vector_case)}: expected_pc {expected_pc} is not "
            f"4-byte aligned")
    landing = offset // 4
    if not 1 <= landing < IMAGE_WINDOW // 4:
        raise ValueError(
            f"{case_label(vector_case)}: expected_pc {expected_pc} is outside "
            f"the harness image window [{hex(BINARY_BASE)}, "
            f"{hex(BINARY_BASE + IMAGE_WINDOW)}); `ret` cannot be observed "
            f"landing on unmapped memory — express that shape as a legality "
            f"case with expected_fault: UNMAPPED")

    words = [encode_jump_iiii(landing + 1)]      # w0: entry → loader
    words.extend([encode_swym()] * (landing - 1))  # filler, never executed
    pad_pos = len(words)                          # == landing
    words.append(0)                               # landing pad (filled below)

    # Loader: the vector's input_state, RA included (no stripping).
    loader_words_list, _loader_words = build_loader(vector_case)
    words.extend(loader_words_list)

    # The instruction under test.
    words.extend(build_test_section(vector_case))

    # Fall-through safety net: only reachable if `ret` does not transfer control.
    words.append(encode_illi_poison())

    if dump_mode:
        words.extend(build_dumper_section())

    exit_index = len(words)
    # jump-iiii base is the instruction's own PC, so the delta is a word count.
    words[pad_pos] = encode_jump_iiii(exit_index - pad_pos)

    # No RA relocation: the vector's RA values are the ones that were loaded.
    words.extend(build_exit_section(vector_case, dump_mode, loader_words=0))

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
        dump_mode: If True, exit section spins instead of exiting via SYS_EXIT

    Returns bytes to be loaded at BINARY_BASE.
    """
    # Routing for control-flow instructions with expected_pc:
    # - ret: landing pad placed at the vector's own expected_pc (build_ret_binary)
    # - call: unconditional jump → TAKEN layout (via build_branch_test_binary)
    # - others (branch/jump): existing taken/not-taken layout
    if vector_case.get("expected_pc") is not None:
        mnemonic = vector_case.get("mnemonic", "")
        if mnemonic == "ret":
            return build_ret_binary(vector_case, dump_mode)
        # call and other branch/jump → existing branch builder
        return build_branch_test_binary(vector_case, dump_mode)

    words = []

    # Section 1: loader
    loader_words_list, loader_words = build_loader(vector_case)
    words.extend(loader_words_list)

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
    words.extend(build_exit_section(vector_case, dump_mode, loader_words=loader_words))

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
                        help="Build in dump mode (spin after dumper, no SYS_EXIT)")
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
