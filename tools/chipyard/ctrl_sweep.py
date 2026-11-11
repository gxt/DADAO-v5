#!/usr/bin/env python3
"""m12-chipyard-009 control-flow sweep: `tests/inst` ctrl vectors on the core.

The vector YAML in ``tests/inst/base/ctrl-{br,jump,call,ret}.yaml`` is the
independent oracle (``spec/SimRISC-06`` + ``spec/SimRISC-00 §2.4``): every case
carries its own expected next PC, register/RA state or fault.  This tool turns
each case into DADAO assembly, links it into a ``+loadmem=`` ELF for the
chipyard ``WumingTinyConfig`` harness plus the flat ``-kernel`` image for QEMU
``dadao-tiny``, and writes the expected result bytes.  "Same as QEMU" therefore
means "both match the shared expectation", exactly as in ``mem_sweep.py``.

Subcommands
-----------
``list``
    Print every covered case and the live counts (recomputed from the YAML).

``emit OUTDIR``
    Emit and assemble/link, into ``OUTDIR``:

      * ``ctrl_sweep.elf`` / ``.raw`` / ``ctrl_expect.bin`` / ``ctrl.json``
        one straight-line program covering the non-fault cases: a two-word flow
        record per case (see below) plus the expected register/RA dump;
      * ``ctrlfault_<key>.elf`` / ``.raw`` + ``ctrl_faults.json``
        one small program per fault case: ``PRE``, the faulting encoding,
        ``POST``.  The hmon handler skips the instruction, so POST is reached
        and its ``excp cause=...`` trace line identifies the fault;
      * ``nested`` / ``overflow`` / ``underflow`` / ``spill`` / ``refill``
        the dedicated return-address and RAS probes (+ ``*_expect.bin``).

Flow record
-----------
Only two next IPs are architecturally possible for a tested instruction: its
own +4 and its target.  Each case therefore gets a fresh two-word record:
``rec[0]`` is written by the instruction at ``A+4`` (the fall-through path) and
``rec[1]`` by the one at ``A+8`` (the taken/returned path), both cleared first.
A taken branch never executes ``A+4``, a not-taken one executes both, so the
pair identifies the actual next IP.  Vectors whose expected PC is ``@ENTRY+0x4``
mean "the instruction after the test"; their RA values are code addresses and
are relocated onto the case's landing pad ``A+8`` so that the jump is
observable (the QEMU harness relocates the same way inside its loader window).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "chipyard"))
sys.path.insert(0, str(ROOT / "tools" / "infra"))
sys.path.insert(0, str(ROOT / "tools" / "testcases" / "lib"))

import yaml  # noqa: E402

import inst_sweep as sweep  # noqa: E402
import machine_profile  # noqa: E402
import mem_sweep as memsw  # noqa: E402

PROFILE = machine_profile.load("tiny")
ENTRY = sweep.ENTRY
BUF = sweep.BUF
REC = ENTRY + 0x6000          # two-word flow record per case
SCRATCH = ENTRY + 0x7F00      # 8-byte staging word for `ld.o ra`
SEMIHOST_TAG = sweep.SEMIHOST_TAG

CTRL_FILES = (
    "tests/inst/base/ctrl-br.yaml",
    "tests/inst/base/ctrl-jump.yaml",
    "tests/inst/base/ctrl-call.yaml",
    "tests/inst/base/ctrl-ret.yaml",
)

# Shared scratch registers (same reservations as the m12-005/008 sweeps).
WR_PTR = sweep.WR_PTR          # rb30
ZERO_RB = sweep.ZERO_RB        # rb27
TMP_RD = sweep.TMP_RD          # rd9
SEMI_RD = sweep.SEMI_RD        # rd16 / rb16
TMP_RB = sweep.TMP_RB          # rb29
BASE_RB = 28                   # rb28: flow-record pointer
CNT_RB = 26                    # rb26: dump loop counter
FALL_RD = 10                   # rd10: fall-through marker value
TAKEN_RD = 11                  # rd11: taken/returned marker value
NEST_RD = 5                    # rd5: per-level counter (RAS probes)

FALL_TAG = 0x1111
TAKEN_TAG = 0x2222

FAULT_DATA_OFF = 0x400
PRE_BLOCK = ENTRY + FAULT_DATA_OFF
POST_BLOCK = ENTRY + FAULT_DATA_OFF + 8

OPC_JUMP_IIII = 0x70
OPC_BR_NZ_RB = 0x73
OPC_CALL_IIII = 0x74
OPC_RET = 0x76

ST_OPC = {"rd": 0x21, "rb": 0x23, "ra": 0x25}
LD_OPC = {"rd": 0x20, "rb": 0x22, "ra": 0x24}


def as_int(v):
    return sweep.as_int(v)


# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------
def enc_jump_iiii(imms24):
    return (OPC_JUMP_IIII << 24) | (imms24 & 0xFFFFFF)


def enc_call_iiii(imms24):
    return (OPC_CALL_IIII << 24) | (imms24 & 0xFFFFFF)


def enc_br_nz_rb(rbha, imms18):
    return (OPC_BR_NZ_RB << 24) | (rbha << 18) | (imms18 & 0x3FFFF)


def enc_ret(rdha, imms18):
    return (OPC_RET << 24) | (rdha << 18) | (imms18 & 0x3FFFF)


def enc_add_si_rd(rdha, imms18):
    """add.si rdHA, imms18 (0x59): the rd-bank form used by the probes."""
    return (0x59 << 24) | (rdha << 18) | (imms18 & 0x3FFFF)


def enc_st_o(bank, reg, rb, off=0):
    return (ST_OPC[bank] << 24) | (reg << 18) | (rb << 12) | (off & 0xFFF)


def enc_ld_o(bank, reg, rb, off=0):
    return (LD_OPC[bank] << 24) | (reg << 18) | (rb << 12) | (off & 0xFFF)


def store_word(reg, rb, off=0):
    """`st.o rdreg, [rbreg, off]` + advance the write pointer."""
    return [enc_st_o("rd", reg, rb, off), sweep.enc_add_si_rb(WR_PTR, 8)]


def rec_word(reg, off):
    """Record one word of the flow record (already in an rd register)."""
    return [enc_st_o("rd", reg, BASE_RB, off)]


# ---------------------------------------------------------------------------
# Case selection / relocation
# ---------------------------------------------------------------------------
def load_cases():
    out = []
    for rel in CTRL_FILES:
        for idx, case in enumerate(yaml.safe_load((ROOT / rel).read_text())):
            out.append({"file": rel, "index": idx,
                        "case": machine_profile.resolve_case(case, PROFILE)})
    return out


def code_window(addr):
    """True for RA values that name code inside the vector's image window."""
    return ENTRY <= addr < ENTRY + 0x1000


def relocate(value, delta):
    """Shift the 48-bit address of a RAS value that names code in the image."""
    if not delta:
        return value
    count = value >> 48
    addr = value & 0xFFFFFFFFFFFF
    if code_window(addr):
        addr += delta
    return (count << 48) | (addr & 0xFFFFFFFFFFFF)


def case_delta(case, instr_addr):
    """Relocation of the vector's code addresses onto this program's layout.

    ``call``: the pushed return address is the instruction's own + 4, so the
    vector's ``@ENTRY+0x4`` maps onto ``A+4``.  ``ret``: the popped address is
    mapped onto the case's landing pad ``A+8`` so the return jump is visible.
    """
    cid = case.get("id") or ""
    if cid.startswith("call_"):
        return instr_addr - ENTRY
    if cid.startswith("ret_"):
        return instr_addr - (ENTRY + 4) + 8
    return 0


def is_taken(case):
    """Taken / returned (True), fall-through (False), or not asserted (None).

    ``encoding`` cases only claim that the encoding word is well-formed, so the
    program does not predict a direction for them: their flow record is cleared
    again after the instruction, which still proves that the instruction
    executed and that control continued (on either path) without a fault.
    """
    if case.get("class") == "encoding":
        return None
    cid = case.get("id") or ""
    if cid.startswith(("call_", "jump_", "ret_")):
        return True
    return as_int(case["expected_pc"]) != ENTRY + 4


def expected_regs(case):
    st = case.get("expected_state") or {}
    regs = []
    for bank in ("rd", "rb", "ra"):
        for name in sorted((st.get(bank) or {}), key=lambda n: int(n[2:])):
            regs.append((bank, int(name[2:])))
    return regs


# ---------------------------------------------------------------------------
# Input state
# ---------------------------------------------------------------------------
def load_ra(num, value):
    """`ra` has no immediate form: stage the value in memory and `ld.o` it."""
    words = sweep.load_rd(TMP_RD, value)
    words += sweep.load_rb(TMP_RB, SCRATCH)
    words.append(enc_st_o("rd", TMP_RD, TMP_RB, 0))
    words.append(enc_ld_o("ra", num, TMP_RB, 0))
    return words


def load_inputs(case, delta):
    """Load rd/rb/ra and the memory entries of one case (code addrs relocated)."""
    words = []
    inp = case.get("input_state") or {}
    for name, val in sorted((inp.get("rd") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += sweep.load_rd(int(name[2:]), as_int(val))
    for name, val in sorted((inp.get("rb") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += sweep.load_rb(int(name[2:]), as_int(val))
    for name, val in sorted((inp.get("ra") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += load_ra(int(name[2:]), relocate(as_int(val), delta))
    for entry in inp.get("memory") or []:
        words += sweep.load_rb(TMP_RB, as_int(entry["address"]))
        words += sweep.load_rd(TMP_RD, relocate(as_int(entry["value"]), delta))
        words.append(enc_st_o("rd", TMP_RD, TMP_RB, 0))
    return words


def check_scratch(cases):
    reserved_rd = {TMP_RD, 15, SEMI_RD, FALL_RD, TAKEN_RD, NEST_RD}
    reserved_rb = {WR_PTR, TMP_RB, ZERO_RB, SEMI_RD, BASE_RB, CNT_RB}
    for case in cases:
        for bank, names in (("rd", reserved_rd), ("rb", reserved_rb)):
            regs = dict(case.get("input_state", {}).get(bank) or {})
            regs.update((case.get("expected_state") or {}).get(bank) or {})
            for name in regs:
                if int(name[2:]) in names:
                    raise SystemExit(
                        f"ctrl_sweep: case {case.get('id')} uses {bank}{name[2:]}, reserved")


# ---------------------------------------------------------------------------
# Straight-line sweep over the non-fault cases
# ---------------------------------------------------------------------------
def build_sweep(cases):
    check_scratch([c["case"] for c in cases])
    words = sweep.asm_prelude()                 # rb27 = permanent zero
    words += sweep.load_rb(WR_PTR, BUF)
    words += sweep.load_rb(BASE_RB, REC)
    words += sweep.load_rd(FALL_RD, FALL_TAG)
    words += sweep.load_rd(TAKEN_RD, TAKEN_TAG)

    expected = bytearray()
    manifest = []
    for entry in cases:
        case = entry["case"]
        inp = case.get("input_state") or {}
        # The RAS state must be known before every case: the vectors that do not
        # name `ra0` assume a cold stack (RACNT = 0), and earlier cases in the
        # same program may have pushed entries.
        reset_ra = [] if "ra0" in (inp.get("ra") or {}) else load_ra(0, 0)
        # The instruction address fixes the code-address relocation, so count
        # the load words first (their number does not depend on the delta).
        nload = len(load_inputs(case, 0)) + len(reset_ra)
        addr = ENTRY + 4 * (len(words) + nload + 2)   # + the two record clears
        delta = case_delta(case, addr)
        words += load_inputs(case, delta)
        words += reset_ra
        words.append(enc_st_o("rd", 0, BASE_RB, 0))    # clear rec[0]
        words.append(enc_st_o("rd", 0, BASE_RB, 8))    # clear rec[1]
        addr = ENTRY + 4 * len(words)
        words.append(as_int(case["encoding"]["word"]))
        words.append(enc_st_o("rd", FALL_RD, BASE_RB, 0))
        words.append(enc_st_o("rd", TAKEN_RD, BASE_RB, 8))
        flow = is_taken(case)
        if flow is None:
            # Encoding case: clear both words again so the record claims
            # nothing about the direction (only that control continued).
            words.append(enc_st_o("rd", 0, BASE_RB, 0))
            words.append(enc_st_o("rd", 0, BASE_RB, 8))
        words.append(sweep.enc_add_si_rb(BASE_RB, 16))
        offset = len(expected)
        regs = expected_regs(case)
        st = case.get("expected_state") or {}
        for bank, num in regs:
            words += memsw.dump_reg(bank, num)
            expected += relocate(as_int(st[bank][f"{bank}{num}"]), delta).to_bytes(8, "big")
        for m in (st.get("memory") or []):
            words += memsw.dump_mem(as_int(m["address"]), 8)
            expected += relocate(as_int(m["value"]), delta).to_bytes(8, "big")
        manifest.append({
            "file": entry["file"], "index": entry["index"], "id": case["id"],
            "format": case.get("format"), "class": case["class"],
            "addr": addr, "taken": flow,
            # A non-zero MRPTR in the injected ra0 selects the MemRAS cases
            # (C3b spill on `call`, D4b refill on `ret`).
            "memras": (as_int((inp.get("ra") or {}).get("ra0", 0)) & 0xFFFFFFFFFFFF) != 0,
            "regs": [f"{b}{n}" for b, n in regs],
            "mem": [f"0x{as_int(m['address']):x}" for m in (st.get("memory") or [])],
            "offset": offset, "bytes": len(regs) * 8 + 8 * len(st.get("memory") or []),
        })
        if len(words) * 4 > REC - ENTRY:
            raise SystemExit(f"ctrl_sweep: program reaches the record area (case {case['id']})")

    # Dump the whole flow-record array at the end (two words per case).
    words += sweep.load_rb(BASE_RB, REC)
    words += sweep.load_rb(CNT_RB, 2 * len(manifest))
    loop = len(words)
    words.append(enc_ld_o("rd", TMP_RD, BASE_RB, 0))
    words.append(enc_st_o("rd", TMP_RD, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(BASE_RB, 8))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(sweep.enc_add_si_rb(CNT_RB, -1))
    at = len(words)
    words.append(enc_br_nz_rb(CNT_RB, loop - at))
    for m in manifest:
        expected += (0 if m["taken"] is None else (0 if m["taken"] else FALL_TAG)).to_bytes(8, "big")
        expected += (0 if m["taken"] is None else TAKEN_TAG).to_bytes(8, "big")

    nbytes = len(expected)
    words += sweep.asm_print_buffer(nbytes)
    words += sweep.asm_sys_exit(0)
    return words, bytes(expected), manifest, nbytes


# ---------------------------------------------------------------------------
# Fault images
# ---------------------------------------------------------------------------
def build_fault_image(case, word):
    words = sweep.asm_prelude()
    words += sweep.asm_write0(PRE_BLOCK)
    words += load_inputs(case, 0)
    words.append(as_int(word))
    words += sweep.asm_write0(POST_BLOCK)
    words += sweep.asm_sys_exit(0)
    if len(words) * 4 > FAULT_DATA_OFF:
        raise SystemExit("ctrl_sweep: fault program does not fit below the markers")
    words += [0] * ((FAULT_DATA_OFF - len(words) * 4) // 4)
    words += [0x5052450A, 0x00000000, 0x504F5354, 0x0A000000]  # "PRE\n\0"+"POST\n\0"
    return words


def build_zero_landing_image(case, word):
    """Fault image whose tested instruction targets an all-zero word.

    ``br.eq``/``br.ne`` have a 12-bit immediate, so the vector's ``-0x400``
    target is only 4 KiB below the instruction: the landing word must be a real
    zero inside the image (an all-zero word decodes as a reserved encoding =>
    UNDI).  Layout: prelude + PRE in ``[0, 0x1000)``, the all-zero landing
    window ``[0x1000, 0x2000)``, the tested word at ``0x2000`` and POST right
    after it (the hmon handler skips the faulting instruction).
    """
    land = 0x2000
    words = sweep.asm_prelude()
    words += sweep.asm_write0(PRE_BLOCK)
    words += load_inputs(case, 0)
    at = len(words)
    words.append(enc_jump_iiii((land - at * 4) >> 2))
    if len(words) * 4 > FAULT_DATA_OFF:
        raise SystemExit("ctrl_sweep: zero-landing prelude does not fit")
    words += [0] * ((FAULT_DATA_OFF - len(words) * 4) // 4)
    words += [0x5052450A, 0x00000000, 0x504F5354, 0x0A000000]
    words += [0] * ((0x1000 - len(words) * 4) // 4)   # [0x400, 0x1000) = 0
    words += [0] * ((land - len(words) * 4) // 4)     # [0x1000, 0x2000) = 0
    words.append(as_int(word))
    words += sweep.asm_write0(POST_BLOCK)
    words += sweep.asm_sys_exit(0)
    return words


# ---------------------------------------------------------------------------
# Return-address / RAS probes
# ---------------------------------------------------------------------------
def _probe_start():
    words = sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    return words


def build_nested():
    """Three nested calls; every return site records its own tag.

    ``main -> L1 -> L2 -> L3``; L3 returns ``rd1 = 0x11``, L2 ``rd2 = 0x22``,
    L1 ``rd3 = 0x33``.  Each return site stores a tag before returning, so a
    wrong return address breaks the recorded order.  The dump is
    ``[0xB3, 0xB2, 0xB1, rd1, rd2, rd3, ra0]`` and ``ra0`` proves RACNT is back
    to 0 with MRPTR untouched.
    """
    words = _probe_start()
    for reg in (1, 2, 3):
        words += sweep.load_rd(reg, 0xDEAD)        # decoys: the rets overwrite
    main_call = len(words)
    words.append(0)                                # call L1
    # main continuation: rd1/rd2/rd3 from the three returns, then ra0.
    words.append(enc_st_o("rd", 1, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o("rd", 2, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o("rd", 3, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o("ra", 0, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words += sweep.asm_print_buffer(56)
    words += sweep.asm_sys_exit(0)

    l1 = len(words)
    words.append(0)                                # call L2
    words += sweep.load_rd(TMP_RD, 0xB1)
    words.append(enc_st_o("rd", TMP_RD, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_ret(3, 0x33))

    l2 = len(words)
    words.append(0)                                # call L3
    words += sweep.load_rd(TMP_RD, 0xB2)
    words.append(enc_st_o("rd", TMP_RD, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_ret(2, 0x22))

    l3 = len(words)
    words += sweep.load_rd(TMP_RD, 0xB3)
    words.append(enc_st_o("rd", TMP_RD, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_ret(1, 0x11))

    words[main_call] = enc_call_iiii(l1 - main_call)
    words[l1] = enc_call_iiii(l2 - l1)
    words[l2] = enc_call_iiii(l3 - l2)
    expected = bytearray()
    for v in (0xB3, 0xB2, 0xB1, 0x11, 0x22, 0x33, 0):
        expected += v.to_bytes(8, "big")
    return words, bytes(expected)


def build_overflow():
    """64 nested calls on a cold stack: the 64th push must raise RASOF.

    63 ``call``s fill RegRAS (RACNT == 63) with MRPTR == 0 (the reset value), so
    the 64th is C3b with no MemRAS: **RASOF**.  The monitor skips it, every
    level bumps rd5 and one ``ret`` per level unwinds the stack, so the dump
    proves that all 64 call sites and all 63 returns were reached and that
    ``ra0`` is back to zero.

    The blocks are laid out deepest-first (``level 63`` ... ``level 1``,
    ``level 0``, dump) so that the fall-through after the outermost level runs
    into the dump block instead of re-entering the next level.
    """
    depth = 64
    words = _probe_start()
    words += sweep.load_rd(NEST_RD, 0)
    enter = len(words)
    words.append(0)                                # jump to level 0
    blocks = {}                                    # level -> call index
    for level in range(depth - 1, 0, -1):
        blocks[level] = len(words)
        words.append(0)                            # call level + 1
        words.append(enc_add_si_rd(NEST_RD, 1))
        words.append(enc_ret(0, 0))
    level0 = len(words)
    blocks[0] = level0
    words.append(0)                                # call level 1
    words.append(enc_add_si_rd(NEST_RD, 1))
    jump_dump = len(words)
    words.append(0)                                # jump to the dump block
    dump = len(words)
    words.append(enc_st_o("ra", 0, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o("rd", NEST_RD, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words += sweep.asm_print_buffer(16)
    words += sweep.asm_sys_exit(0)
    words[enter] = enc_jump_iiii(level0 - enter)
    words[jump_dump] = enc_jump_iiii(dump - jump_dump)
    for level, idx in blocks.items():
        if level + 1 < depth:
            words[idx] = enc_call_iiii(blocks[level + 1] - idx)
        else:
            # Self-call: the push itself is what overflows (RASOF), so the
            # monitor skips it before any jump can happen.
            words[idx] = enc_call_iiii(0)
    expected = (0).to_bytes(8, "big") + (depth).to_bytes(8, "big")
    return words, bytes(expected)


def build_underflow():
    """Three cold-stack `ret`s (D4a) plus one D1 hit; nothing may change."""
    words = _probe_start()
    for reg, seed in ((1, 0x1111), (2, 0x2222), (3, 0x3333)):
        words += sweep.load_rd(reg, seed)          # decoys: a faulting ret must
                                                   # leave them untouched
    words.append(enc_ret(0, 0))                    # D4a: RACNT = 0, MRPTR = 0
    words.append(enc_ret(1, 0x2A))                 # D4a, rd1 must stay 0
    words.append(enc_ret(2, 0x2B))                 # D4a
    # D1: RACNT = 1 but the top entry's recursion count is 0 -> RASUF.
    words += load_ra(0, 0x0001000000000000)
    words += load_ra(63, 0x0000123400000000)       # {count 0, addr 0x1234}
    words.append(enc_ret(3, 0x2C))
    for bank, num in (("ra", 0), ("ra", 63), ("rd", 1), ("rd", 2), ("rd", 3)):
        words += memsw.dump_reg(bank, num)
    words += sweep.asm_print_buffer(40)
    words += sweep.asm_sys_exit(0)
    expected = bytearray()
    expected += (0x0001000000000000).to_bytes(8, "big")   # ra0 untouched
    expected += (0x0000123400000000).to_bytes(8, "big")   # ra63 untouched
    expected += (0x1111).to_bytes(8, "big")               # rd1 untouched
    expected += (0x2222).to_bytes(8, "big")               # rd2 untouched
    expected += (0x3333).to_bytes(8, "big")               # rd3 untouched
    return words, bytes(expected)


def build_spill():
    """C3b: a full RegRAS spills its oldest entry to MemRAS[MRPTR - 8].

    Injected state: RACNT = 63, MRPTR = SLOT, ``ra1`` = the oldest entry and
    ``ra63`` = a top whose address cannot be folded.  The `call` stores the
    oldest entry at ``SLOT - 8``, moves MRPTR down and pushes its own return
    address; the callee returns immediately, popping that new top.  The dump
    shows RACNT = 62, MRPTR = SLOT - 8, the old top back on ra63 and the
    spilled word in memory.
    """
    slot = ENTRY + 0x5000
    words = _probe_start()
    words += load_ra(0, (63 << 48) | slot)
    words += load_ra(1, 0x0005DDDD00000000)        # oldest entry
    words += load_ra(63, 0x0001EEEE00000000)       # top (different address)
    call_at = len(words)
    words.append(0)                                # call callee
    # Continuation: the callee's ret popped the entry the call pushed.
    words.append(enc_st_o("ra", 0, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o("ra", 63, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words += memsw.dump_mem(slot - 8, 8)
    words += sweep.asm_print_buffer(24)
    words += sweep.asm_sys_exit(0)
    callee = len(words)
    words.append(enc_ret(0, 0))
    words[call_at] = enc_call_iiii(callee - call_at)
    expected = bytearray()
    expected += ((62 << 48) | (slot - 8)).to_bytes(8, "big")  # ra0
    expected += (0x0001EEEE00000000).to_bytes(8, "big")       # ra63 (old top)
    expected += (0x0005DDDD00000000).to_bytes(8, "big")       # spilled entry
    return words, bytes(expected)


def build_refill():
    """D4b: refill from MemRAS (count > 1) and consume (count == 1).

    Both entries point at the instruction following the ``ret`` (the way the
    QEMU harness relocates code addresses), so the jump itself lands on the
    recorder and the dump proves the RAS side effects.
    """
    words = _probe_start()
    slot_a = ENTRY + 0x5200
    slot_b = ENTRY + 0x5300

    def emit_d4b(slot, entry_count):
        """Load {count, ret+4} at `slot`, ret, then record ra0/ra63."""
        words.extend(load_ra(0, slot))             # RACNT = 0, MRPTR = slot
        words.extend(sweep.load_rb(TMP_RB, slot))
        ld_at = len(words)
        words.extend(sweep.load_rd(TMP_RD, 0))     # placeholder: entry value
        words.append(enc_st_o("rd", TMP_RD, TMP_RB, 0))
        ret_at = len(words)
        entry_addr = ENTRY + 4 * (ret_at + 1)      # the instruction after ret
        words[ld_at:ld_at + 4] = sweep.load_rd(
            TMP_RD, (entry_count << 48) | entry_addr)
        words.append(enc_ret(0, 0))
        words.append(enc_st_o("ra", 0, WR_PTR, 0))
        words.append(sweep.enc_add_si_rb(WR_PTR, 8))
        words.append(enc_st_o("ra", 63, WR_PTR, 0))
        words.append(sweep.enc_add_si_rb(WR_PTR, 8))
        return entry_addr

    entry_a = emit_d4b(slot_a, 3)                  # refill: RACNT 1, MRPTR + 8
    entry_b = emit_d4b(slot_b, 1)                  # consume: RACNT 0, MRPTR + 8
    words += sweep.asm_print_buffer(32)
    words += sweep.asm_sys_exit(0)
    expected = bytearray()
    expected += ((1 << 48) | (slot_a + 8)).to_bytes(8, "big")   # ra0 after refill
    expected += ((2 << 48) | entry_a).to_bytes(8, "big")        # refilled top
    expected += (slot_b + 8).to_bytes(8, "big")                 # ra0 after consume
    # The consume path (count == 1) leaves RegRAS alone: ra63 is still the
    # entry the refill pushed.
    expected += ((2 << 48) | entry_a).to_bytes(8, "big")
    return words, bytes(expected)


def build_overflow_ffff():
    """C2 fold boundary: a full stack whose top has the maximum recursion count.

    RACNT = 63 with MRPTR = 0 and ``ra63`` = ``{0xFFFF, ip + 4}``: the return
    address *would* fold, but the recursive count may not grow past 0xFFFF
    (spec/SimRISC-00 §2.4.1 C2), so this is C3b without MemRAS => **RASOF**.
    The dump proves that neither ra0 nor ra63 was modified.
    """
    words = _probe_start()
    words += load_ra(0, 63 << 48)                  # RACNT = 63, MRPTR = 0
    ld_at = len(words)
    words += sweep.load_rd(TMP_RD, 0)              # placeholder: the RA value
    words += sweep.load_rb(TMP_RB, SCRATCH)
    words.append(enc_st_o("rd", TMP_RD, TMP_RB, 0))
    words.append(enc_ld_o("ra", 63, TMP_RB, 0))
    call_at = len(words)
    words.append(enc_call_iiii(0))                 # faults before any jump
    words[ld_at:ld_at + 4] = sweep.load_rd(
        TMP_RD, (0xFFFF << 48) | (ENTRY + 4 * (call_at + 1)))
    words.append(enc_st_o("ra", 0, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o("ra", 63, WR_PTR, 0))
    words.append(sweep.enc_add_si_rb(WR_PTR, 8))
    words += sweep.asm_print_buffer(16)
    words += sweep.asm_sys_exit(0)
    expected = bytearray()
    expected += (63 << 48).to_bytes(8, "big")                       # ra0 unchanged
    expected += ((0xFFFF << 48) | (ENTRY + 4 * (call_at + 1))).to_bytes(8, "big")
    return words, bytes(expected)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_list(_args):
    cases = load_cases()
    for entry in cases:
        case = entry["case"]
        print(f"{entry['file']}:{entry['index']}  {case['id']}  {case.get('format')}  "
              f"{case['class']}  fault={case.get('expected_fault')}")
    faults = [c for c in cases if c["case"].get("expected_fault")]
    print(f"covered={len(cases)} semantic_set={len(cases) - len(faults)} "
          f"fault_cases={len(faults)}")
    return 0


PROBES = (
    ("nested", build_nested),
    ("overflow", build_overflow),
    ("underflow", build_underflow),
    ("spill", build_spill),
    ("refill", build_refill),
    ("overflow_ffff", build_overflow_ffff),
)


def cmd_emit(args):
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tb = sweep.toolchain_bin(args.toolchain_bin)
    cases = load_cases()

    sem = [c for c in cases if not c["case"].get("expected_fault")]
    words, expected, manifest, nbytes = build_sweep(sem)
    sweep.assemble(words, outdir, "ctrl_sweep", tb)
    (outdir / "ctrl_expect.bin").write_bytes(expected)
    (outdir / "ctrl.json").write_text(json.dumps(
        {"bytes": nbytes, "cases": manifest}, indent=1) + "\n")

    meta = []
    for entry in cases:
        fault = entry["case"].get("expected_fault")
        if not fault:
            continue
        case = entry["case"]
        key = f"{Path(entry['file']).stem}_{entry['index']}"
        word = as_int(case["encoding"]["word"])
        fwords = (build_zero_landing_image(case, word) if fault == "UNDI"
                  else build_fault_image(case, word))
        sweep.assemble(fwords, outdir, f"ctrlfault_{key}", tb)
        meta.append({"key": key, "fault": fault, "word": f"0x{word:08x}",
                     "id": case["id"], "elf": f"ctrlfault_{key}.elf",
                     "raw": f"ctrlfault_{key}.raw",
                     # A control-flow fault raised *by* the tested instruction
                     # (ILLI/RASOF/RASUF) leaves the IP on it, so the monitor's
                     # "escape +4" skip resumes in the program (PRE+POST).  A
                     # CFXMEM/UNDI on this family is raised when the control
                     # transfer is fetched, so the IP sits on the bad target and
                     # the skip cannot come back: the image is terminal and the
                     # run is bounded by max-cycles (PRE only).
                     "resumable": fault in ("ILLI", "RASOF", "RASUF")})
    (outdir / "ctrl_faults.json").write_text(json.dumps(meta, indent=1) + "\n")

    for stem, fn in PROBES:
        pwords, pexpect = fn()
        sweep.assemble(pwords, outdir, stem, tb)
        (outdir / f"{stem}_expect.bin").write_bytes(pexpect)

    print(f"emit: outdir={outdir}")
    print(f"emit: covered={len(cases)} semantic_set={len(sem)} "
          f"fault_images={len(meta)} dumped_bytes={nbytes}")
    return 0


_EXEC_RE = re.compile(r"WumingCore: exec ip=0x([0-9a-f]+) inst=0x([0-9a-f]+) "
                      r"cycle=\s*(\d+)")


def cmd_cycles(args):
    """Per-case cycle count: from the case's `exec` to the next `exec`."""
    manifest = json.loads((Path(args.outdir) / "ctrl.json").read_text())
    trace = []
    for line in Path(args.log).read_text(errors="replace").splitlines():
        m = _EXEC_RE.search(line)
        if m:
            trace.append((int(m.group(1), 16), int(m.group(3))))
    index = {}
    for pos, (ip, _cyc) in enumerate(trace):
        index.setdefault(ip, []).append(pos)
    for case in manifest["cases"]:
        positions = index.get(case["addr"], [])
        if not positions:
            print(f"{case['id']:16s} {case['class']:9s} addr=0x{case['addr']:x} "
                  f"cycles=none")
            continue
        pos = positions[0]
        cycles = trace[pos + 1][1] - trace[pos][1] if pos + 1 < len(trace) else -1
        taken = "none" if case["taken"] is None else int(case["taken"])
        print(f"{case['id']:16s} {case['class']:9s} addr=0x{case['addr']:x} "
              f"taken={taken} cycles={cycles}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)
    p_emit = sub.add_parser("emit")
    p_emit.add_argument("outdir")
    p_emit.add_argument("--toolchain-bin", default=None)
    p_emit.set_defaults(func=cmd_emit)
    p_cyc = sub.add_parser("cycles")
    p_cyc.add_argument("outdir")
    p_cyc.add_argument("log")
    p_cyc.set_defaults(func=cmd_cycles)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
