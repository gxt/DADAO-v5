#!/usr/bin/env python3
"""Build and drive the m12-chipyard-005 integer-instruction sweep.

The vectors in ``tests/inst/base/*.yaml`` are the independent oracle: every
case carries its own expected architectural state.  This tool turns the cases
covered by the m12-chipyard-005 decoder/ALU subset into DADAO assembly, links
them into images that the chipyard ``WumingTinyConfig`` harness can load with
``+loadmem=`` (ELF) and that QEMU ``dadao-tiny`` can load as a raw kernel, and
writes the expected result bytes.

Subcommands
-----------
``list``
    Print every covered case (file, index, id, format, class, fault) and the
    live count.  Nothing is hard-coded: the count is recomputed from the YAML.

``emit OUTDIR``
    Write the assembly/linker inputs, assemble+link them, and emit:
      * ``sweep.elf`` / ``sweep.raw`` / ``sweep_expect.bin`` / ``sweep.json``
        one straight-line program covering every non-fault case;
      * ``fault_<key>.elf`` / ``.raw`` / ``.json``
        one tiny program per fault case: it prints ``PRE`` and then executes
        the faulting encoding (a core that treats the encoding as a NOP would
        reach ``POST`` and exit 0);
      * ``rd0rb0.elf`` / ``.raw`` / ``rd0rb0_expect.bin`` / ``.json``
        dedicated rd0/rb0 assertions.
    The expected bytes are derived from the vector YAML (not from QEMU), and
    QEMU is run on the same image as a second, independent comparison point.

QEMU invocation (the caller does this; ``emit`` only writes files):
    qemu-system-dadao -M dadao-tiny -bios bootrom.bin -nographic \\
        -kernel sweep.raw -semihosting-config enable=on,target=native

The guest prints its result bytes with SYS_WRITEC (one byte per call), which
both the QEMU semihosting console and the chipyard ``+semiout=`` sink write
verbatim, so the comparison is byte-exact.

Only the families implemented by ``WumingDecoder`` are covered; see
``COVERED_IDS``.  Tetra/wyde/byte (other than the `.t` arithmetic above),
memory, control flow, FP and bit manipulation belong to later milestones.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "infra"))
import paths as _paths  # noqa: E402

import yaml  # noqa: E402

sys.path.insert(0, str(ROOT / "tools" / "testcases" / "lib"))
import machine_profile  # noqa: E402

PROFILE = machine_profile.load("tiny")


def as_int(v):
    return v if isinstance(v, int) else int(str(v), 16)


def ref_loader_words(case):
    """Words the reference harness loader would emit for this case.

    ``aip.si`` expected values are relative to the instruction's own address;
    the vector assumes the reference loader layout (set.zw + one or.w per
    non-zero high wyde).  We reproduce that count to derive the offset from
    ENTRY, then relocate by the actual instruction address in our program.
    """
    inp = case.get("input_state") or {}
    n = 0
    for bank in ("rd", "rb"):
        for _, val in (inp.get(bank) or {}).items():
            v = as_int(val)
            n += 1 + sum(1 for sh in (16, 32, 48) if (v >> sh) & 0xFFFF)
    for _ in inp.get("memory") or []:
        n += 1 + 1  # address + value references (approximation; unused today)
    return n

VECTOR_FILES = (
    "tests/inst/base/reg-arith.yaml",
    "tests/inst/base/reg-logic.yaml",
    "tests/inst/base/reg-shift-extend.yaml",
    "tests/inst/base/reg-compare.yaml",
    "tests/inst/base/aip-si.yaml",
    "tests/inst/rol/rol.yaml",
)

# Instruction identities implemented by the m12-chipyard-005 decoder/ALU.
# (format is part of the identity: e.g. shl.o exists as orrr and orri.)
COVERED_IDS = {
    "and.o_orrr_rd", "or.o_orrr_rd", "xor.o_orrr_rd", "xnor.o_orrr_rd",
    "shl.o_orrr_rd", "shl.o_orri_rd", "rol.o_orrr_rd", "rol.o_orri_rd",
    "shr.uo_orrr_rd", "shr.uo_orri_rd", "shr.so_orrr_rd", "shr.so_orri_rd",
    "ext.uo_orrr_rd", "ext.uo_orri_rd", "ext.so_orrr_rd", "ext.so_orri_rd",
    "cmp.uo_orrr_rd", "cmp.so_orrr_rd",
    "add.o_orrr_bbd", "sub.o_orrr_bbd", "cmp.uo_orrr_dbb", "sub.o_orrr_dbb",
    "div.uo_orrr_rd", "div.so_orrr_rd", "rem.uo_orrr_rd", "rem.so_orrr_rd",
    "add.uo_rrrr_rd", "add.so_rrrr_rd", "sub.uo_rrrr_rd", "sub.so_rrrr_rd",
    "mul.uo_rrrr_rd", "mul.so_rrrr_rd",
    "add.si_riii_rd", "add.si_riii_rb", "aip.si_riii_rb",
    "cmp.ui_rrii_rd", "cmp.si_rrii_rd",
    "shl.t_orrr_rd", "shl.t_orri_rd", "rol.t_orrr_rd", "rol.t_orri_rd",
    "shr.ut_orrr_rd", "shr.ut_orri_rd", "shr.st_orrr_rd", "shr.st_orri_rd",
    "add.ut_orrr_rd", "add.st_orrr_rd", "sub.ut_orrr_rd", "sub.st_orrr_rd",
    "cmp.ut_orrr_rd", "cmp.st_orrr_rd", "mul.ut_orrr_rd", "mul.st_orrr_rd",
    "div.ut_orrr_rd", "div.st_orrr_rd", "rem.ut_orrr_rd", "rem.st_orrr_rd",
}

ENTRY = 0xFFFF_FF01_0100
KERNEL_BASE = 0xFFFF_FF01_0000
RAW_PREFIX = ENTRY - KERNEL_BASE
BUF = ENTRY + 0x8000          # result buffer (32 KiB past the code)
EXITBLOCK = ENTRY + 0x9000    # SYS_EXIT argument block
PRE_BLOCK = ENTRY + 0x400     # "PRE\n\0" (inside the fault image)
POST_BLOCK = ENTRY + 0x408    # "POST\n\0" (inside the fault image)
IMAGE_LIMIT = BUF - ENTRY     # code must stay below BUF

SEMIHOST_TAG = 0x3FF00
SYS_WRITEC = 0x03
SYS_WRITE0 = 0x04
SYS_EXIT = 0x18
ADP_STOPPED_APPLICATION_EXIT = 0x20026

# Scratch registers used by the generated harness only.  The covered cases use
# rd1..rd5 and rb1..rb3 (checked at emit time), so these are free.
WR_PTR = 30      # rb30: moving result-write pointer
RD_PTR = 31      # rb31: result-read pointer (not used; rb16 is reused)
ZERO_RB = 27     # rb27: permanent zero for rb -> rd copies
TMP_RD = 9       # rd9: rb -> rd copy destination
SEMI_RD = 16     # rd16 / rb16: semihosting op / pointer
TMP_RB = 29      # rb29: memory-input address


# ---------------------------------------------------------------------------
# Encoding helpers (contracts/opcodes.yaml; SimRISC field layouts)
# ---------------------------------------------------------------------------
def enc_set_zw_rd(rd, wp, imm):
    return (0x4C << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_or_w_rd(rd, wp, imm):
    return (0x48 << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_set_zw_rb(rb, wp, imm):
    return (0x4E << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_or_w_rb(rb, wp, imm):
    return (0x4A << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)


def enc_st_o_rd(rd, rb, off):
    return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)


def enc_trap(cfxha, imm18):
    return (0x7F << 24) | (cfxha << 18) | (imm18 & 0x3FFFF)


def enc_add_uo(rdha, rdhb, rdhc, rdhd):
    return (0x50 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_sub_uo(rdha, rdhb, rdhc, rdhd):
    return (0x52 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_sub_so(rdha, rdhb, rdhc, rdhd):
    return (0x53 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_mul_uo(rdha, rdhb, rdhc, rdhd):
    return (0x54 << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_add_si_rb(rbha, imms18):
    return (0x5B << 24) | (rbha << 18) | (imms18 & 0x3FFFF)


def enc_aip_si_rb(rbha, imms18):
    return (0x5A << 24) | (rbha << 18) | (imms18 & 0x3FFFF)


def enc_sub_o_dbb(rdhb, rbhc, rbhd):
    return 0x40CC0000 | (rdhb << 12) | (rbhc << 6) | rbhd


def enc_add_o_bbd(rbhb, rbhc, rdhd):
    return 0x40C00000 | (rbhb << 12) | (rbhc << 6) | rdhd


def enc_shl_t_orri(rdhb, rdhc, immu6):
    return 0x41600000 | (rdhb << 12) | (rdhc << 6) | (immu6 & 0x3F)


def load_rd(dst, value):
    """set.zw wp0 + three or.w merges -- always 4 words (fixed index math)."""
    return [
        enc_set_zw_rd(dst, 0, value & 0xFFFF),
        enc_or_w_rd(dst, 1, (value >> 16) & 0xFFFF),
        enc_or_w_rd(dst, 2, (value >> 32) & 0xFFFF),
        enc_or_w_rd(dst, 3, (value >> 48) & 0xFFFF),
    ]


def load_rb(dst, value):
    return [
        enc_set_zw_rb(dst, 0, value & 0xFFFF),
        enc_or_w_rb(dst, 1, (value >> 16) & 0xFFFF),
        enc_or_w_rb(dst, 2, (value >> 32) & 0xFFFF),
        enc_or_w_rb(dst, 3, (value >> 48) & 0xFFFF),
    ]


def word_bytes(words):
    return b"".join(struct.pack(">I", w) for w in words)


# ---------------------------------------------------------------------------
# Vector selection
# ---------------------------------------------------------------------------
def covered(case):
    return case.get("id") in COVERED_IDS


def resolved(case):
    return machine_profile.resolve_case(case, PROFILE)


def load_cases():
    out = []
    for rel in VECTOR_FILES:
        data = yaml.safe_load((ROOT / rel).read_text())
        for idx, case in enumerate(data):
            if not covered(case):
                continue
            out.append({"file": rel, "index": idx, "case": case})
    return out


def case_regs(case):
    """Registers a semantic case is expected to leave in a defined state."""
    st = case.get("expected_state") or {}
    regs = []
    for bank in ("rd", "rb"):
        for name in sorted((st.get(bank) or {}), key=lambda n: int(n[2:])):
            if name in ("rd0", "rb0"):
                continue
            regs.append((bank, int(name[2:])))
    return regs


# ---------------------------------------------------------------------------
# Assembly generation
# ---------------------------------------------------------------------------
def asm_prelude():
    # rb27 is the permanent zero used by the rb -> rd copy below.
    return load_rb(ZERO_RB, 0)


def asm_load_inputs(case):
    """Emit loads for input_state rd/rb (and octa memory entries)."""
    words = []
    inp = case.get("input_state") or {}
    for name, val in sorted((inp.get("rd") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += load_rd(int(name[2:]), as_int(val))
    for name, val in sorted((inp.get("rb") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += load_rb(int(name[2:]), as_int(val))
    for entry in inp.get("memory") or []:
        addr = as_int(entry["address"])
        val = as_int(entry["value"])
        words += load_rb(TMP_RB, addr)
        words += load_rd(TMP_RD, val)
        words.append(enc_st_o_rd(TMP_RD, TMP_RB, 0))
    if inp.get("ra"):
        raise SystemExit("inst_sweep: RA inputs are outside the m12-005 subset")
    return words


def asm_dump_regs(case):
    words = []
    for bank, num in case_regs(case):
        if bank == "rd":
            words.append(enc_st_o_rd(num, WR_PTR, 0))
        else:
            # No rb -> rd move is needed outside the covered families: sub.o
            # dbb writes rd = rb - 0 and is itself implemented.
            words.append(enc_sub_o_dbb(TMP_RD, num, ZERO_RB))
            words.append(enc_st_o_rd(TMP_RD, WR_PTR, 0))
        words.append(enc_add_si_rb(WR_PTR, 8))
    return words


def asm_print_buffer(nbytes):
    # rb16 = BUF is the argument of SYS_WRITEC; rd16 carries the service number.
    words = load_rb(SEMI_RD, BUF)
    words.append(enc_set_zw_rd(SEMI_RD, 0, SYS_WRITEC))
    for _ in range(nbytes):
        words.append(enc_trap(0, SEMIHOST_TAG | SYS_WRITEC))
        words.append(enc_add_si_rb(SEMI_RD, 1))
    return words


def asm_sys_exit(code):
    words = []
    words += load_rb(SEMI_RD, EXITBLOCK)
    words += load_rd(15, ADP_STOPPED_APPLICATION_EXIT)
    words.append(enc_st_o_rd(15, SEMI_RD, 0))
    words += load_rd(15, code)
    words.append(enc_st_o_rd(15, SEMI_RD, 8))
    words.append(enc_set_zw_rd(SEMI_RD, 0, SYS_EXIT))
    words.append(enc_trap(0, SEMIHOST_TAG | SYS_EXIT))
    return words


def asm_write0(ptr):
    return load_rb(SEMI_RD, ptr) + [
        enc_set_zw_rd(SEMI_RD, 0, SYS_WRITE0),
        enc_trap(0, SEMIHOST_TAG | SYS_WRITE0),
    ]


def check_scratch(cases):
    for entry in cases:
        case = entry["case"]
        for bank in ("rd", "rb"):
            regs = case.get("input_state", {}).get(bank) or {}
            regs = dict(regs)
            regs.update((case.get("expected_state") or {}).get(bank) or {})
            for name in regs:
                num = int(name[2:])
                if bank == "rd" and num in (TMP_RD, SEMI_RD, 15):
                    raise SystemExit(f"inst_sweep: case {case.get('id')} uses rd{num}, reserved for the harness")
                if bank == "rb" and num in (WR_PTR, TMP_RB, ZERO_RB, SEMI_RD):
                    raise SystemExit(f"inst_sweep: case {case.get('id')} uses rb{num}, reserved for the harness")


def build_sweep(cases):
    check_scratch(cases)
    words = asm_prelude()
    # Write pointer starts at BUF.
    words += load_rb(WR_PTR, BUF)
    expected = bytearray()
    manifest = []
    for entry in cases:
        case = resolved(entry["case"])
        if case.get("expected_fault"):
            continue
        words += asm_load_inputs(case)
        test_index = len(words)
        words.append(int(str(case["encoding"]["word"]), 16))
        words += asm_dump_regs(case)
        regs = case_regs(case)
        st = case.get("expected_state") or {}
        ip_reloc = 0
        if case.get("id") == "aip.si_riii_rb" and case["class"] in ("semantic", "boundary"):
            vector_ip = ENTRY + 4 * ref_loader_words(case)
            actual_ip = ENTRY + 4 * test_index
            ip_reloc = actual_ip - vector_ip
        for bank, num in regs:
            expected += (as_int(st[bank][f"{bank}{num}"]) + ip_reloc).to_bytes(8, "big")
        manifest.append({
            "file": entry["file"], "index": entry["index"], "id": case["id"],
            "format": case.get("format"), "class": case["class"],
            "regs": [f"{b}{n}" for b, n in regs],
            "bytes": len(regs) * 8,
        })
    nbytes = len(expected)
    words += asm_print_buffer(nbytes)
    words += asm_sys_exit(0)
    return words, bytes(expected), manifest, nbytes


FAULT_DATA_OFF = 0x400


def build_fault(case, word):
    words = asm_prelude()
    words += asm_write0(PRE_BLOCK)
    words += asm_load_inputs(case)
    words.append(int(str(word), 16))
    words += asm_write0(POST_BLOCK)
    words += asm_sys_exit(0)
    # The two markers must live in the loaded image: SYS_WRITE0 walks guest
    # memory until NUL, and uninitialized SRAM would make it scan for ever.
    if len(words) * 4 > FAULT_DATA_OFF:
        raise SystemExit("inst_sweep: fault program does not fit below the marker block")
    words += [0] * ((FAULT_DATA_OFF - len(words) * 4) // 4)
    words += [0x5052450A, 0x00000000, 0x504F5354, 0x0A000000]  # "PRE\n\0" + "POST\n\0"
    return words


def build_rd0rb0():
    """Dedicated rd0 / rb0 assertions.

    (a) rrrr dual-destination with rd0 as the *high* half discards that half
        and keeps rd0 readable as 0;
    (b) rd0 as the *low* half likewise discards;
    (c) a write to rb1 is observable (rb bank works);
    (d) aip.si rb1, 0 reads rb0 = the current instruction's address;
    (e) add.o rb1, rb0, rd0 reads rb0 as a source.
    """
    words = asm_prelude()
    words += load_rb(WR_PTR, BUF)
    words += load_rd(2, 5)
    words += load_rd(3, 7)
    # The semihosting scalar must be written back to rd8 (m12-004 contract):
    # SYS_WRITEC returns 0xdeadbeef (no defined return) and it also emits the
    # first byte of a known word, so the expected stream starts with 'A'.
    words += load_rd(20, 0x4120202020202020)
    words.append(enc_st_o_rd(20, WR_PTR, 0))
    words += load_rb(SEMI_RD, BUF)
    words.append(enc_set_zw_rd(SEMI_RD, 0, SYS_WRITEC))
    words.append(enc_trap(0, SEMIHOST_TAG | SYS_WRITEC))
    words.append(enc_st_o_rd(8, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected = bytearray(b"A")
    expected += (0xDEADBEEF).to_bytes(8, "big")

    # (a) add.uo {rd0, rd5}, rd2, rd3 ; dump rd0 and rd5
    words.append(enc_add_uo(0, 5, 2, 3))
    words.append(enc_st_o_rd(0, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o_rd(5, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (0).to_bytes(8, "big") + (12).to_bytes(8, "big")

    # (b) add.uo {rd5, rd0}, rd2, rd3 with a carry: the high half (1) lands in
    #     rd5 and the low half is discarded into rd0.
    words += load_rd(2, 0xFFFFFFFFFFFFFFFF)
    words += load_rd(3, 2)
    words.append(enc_add_uo(5, 0, 2, 3))
    words.append(enc_st_o_rd(5, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (1).to_bytes(8, "big")

    # (c) rb write: rb1 = 7; add.si rb1, 5 -> 12; copy to rd9 and dump.
    words += load_rb(1, 7)
    words.append(enc_add_si_rb(1, 5))
    words.append(enc_sub_o_dbb(TMP_RD, 1, ZERO_RB))
    words.append(enc_st_o_rd(TMP_RD, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (12).to_bytes(8, "big")

    # (c2) rwii or.w keeps its "or into the selected wyde" semantics (the
    #      m12-003 stub replaced the wyde instead; SimRISC-03 says OR).
    words += load_rd(1, 0xFFFF)
    words.append(enc_or_w_rd(1, 1, 0x1234))
    words.append(enc_st_o_rd(1, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (0x1234FFFF).to_bytes(8, "big")
    words.append(enc_or_w_rd(1, 1, 0x0001))
    words.append(enc_st_o_rd(1, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (0x1235FFFF).to_bytes(8, "big")

    # (d) rb0 read via aip.si: its own address is the next word.
    aip_index = len(words)
    words.append(enc_aip_si_rb(1, 0))
    words.append(enc_sub_o_dbb(TMP_RD, 1, ZERO_RB))
    words.append(enc_st_o_rd(TMP_RD, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (ENTRY + 4 * aip_index).to_bytes(8, "big")

    # (e) rb0 read as a source: add.o rb1, rb0, rd0 -> rb1 = IP.
    addo_index = len(words)
    words.append(enc_add_o_bbd(1, 0, 0))
    words.append(enc_sub_o_dbb(TMP_RD, 1, ZERO_RB))
    words.append(enc_st_o_rd(TMP_RD, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (ENTRY + 4 * addo_index).to_bytes(8, "big")

    # (f) sub.uo {rd1, rd2}, rd3, rd4: the high half is the *borrow* (0 or 1)
    #     for the ZX variant (spec/SimRISC-04 §1.1), not the high half of the
    #     128-bit wrap.  Three states: a<b (borrow 1), a==b (0), a>b (0);
    #     the a<b probe is the reviewer's 5-7 case.
    for a_val, b_val in ((5, 7), (7, 7), (9, 7), (0, 0xFFFFFFFFFFFFFFFF)):
        words += load_rd(3, a_val)
        words += load_rd(4, b_val)
        words.append(enc_sub_uo(1, 2, 3, 4))
        words.append(enc_st_o_rd(1, WR_PTR, 0))
        words.append(enc_add_si_rb(WR_PTR, 8))
        words.append(enc_st_o_rd(2, WR_PTR, 0))
        words.append(enc_add_si_rb(WR_PTR, 8))
        borrow = 1 if a_val < b_val else 0
        expected += borrow.to_bytes(8, "big")
        expected += ((a_val - b_val) & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big")

    # (g) same-pattern self-check on the signed variant: sub.so keeps the high
    #     64 bits of the sign-extended 128-bit difference, so a<b gives an
    #     all-ones high half (QEMU sub2).
    words += load_rd(3, 5)
    words += load_rd(4, 7)
    words.append(enc_sub_so(1, 2, 3, 4))
    words.append(enc_st_o_rd(1, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o_rd(2, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (0xFFFFFFFFFFFFFFFF).to_bytes(8, "big")
    expected += (0xFFFFFFFFFFFFFFFE).to_bytes(8, "big")

    # (h) and on mul.uo: the high half is the real upper 64 bits of the product.
    words += load_rd(3, 0x8000000000000000)
    words += load_rd(4, 4)
    words.append(enc_mul_uo(1, 2, 3, 4))
    words.append(enc_st_o_rd(1, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    words.append(enc_st_o_rd(2, WR_PTR, 0))
    words.append(enc_add_si_rb(WR_PTR, 8))
    expected += (2).to_bytes(8, "big") + (0).to_bytes(8, "big")

    # The SYS_WRITEC probe above printed 'A' directly (one byte); the buffer
    # dump below must cover exactly the bytes stored through WR_PTR.
    buf_bytes = len(expected) - 1
    words += asm_print_buffer(buf_bytes)
    words += asm_sys_exit(0)
    return words, bytes(expected)


# ---------------------------------------------------------------------------
# Assemble / link
# ---------------------------------------------------------------------------
LDS = """ENTRY(_start)
PHDRS {{ image PT_LOAD FLAGS(7); }}
SECTIONS
{{
  . = 0x{entry:x};
  .text : {{ *(.text .text.*) }} : image
  /DISCARD/ : {{ *(.note.GNU-stack) *(.comment) }}
}}
"""


def toolchain_bin(explicit):
    if explicit:
        return Path(explicit)
    return _paths.host_toolchain_bin()


def assemble(words, outdir, stem, tb, extra_symbols=()):
    """Write the source, assemble/link it, and return (elf, raw) paths."""
    src = outdir / f"{stem}.S"
    lds = outdir / f"{stem}.lds"
    obj = outdir / f"{stem}.o"
    elf = outdir / f"{stem}.elf"
    raw0 = outdir / f"{stem}.flat"
    raw = outdir / f"{stem}.raw"
    lds.write_text(LDS.format(entry=ENTRY))
    lines = [".text", ".globl _start", "_start:"]
    lines += [".dd.t32 0x%08x" % w for w in words]
    src.write_text("\n".join(lines) + "\n")
    subprocess.run([str(tb / "llvm-mc"), "--triple=dadao-unknown-elf", "-filetype=obj",
                    str(src), "-o", str(obj)], check=True)
    subprocess.run([str(tb / "ld.lld"), "-T", str(lds), str(obj), "-o", str(elf)], check=True)
    subprocess.run([str(tb / "llvm-objcopy"), "-O", "binary", str(elf), str(raw0)], check=True)
    data = raw0.read_bytes()
    if len(data) > IMAGE_LIMIT:
        raise SystemExit(f"inst_sweep: {stem} code {len(data)} B exceeds {IMAGE_LIMIT} B")
    raw.write_bytes(b"\x00" * RAW_PREFIX + data)
    return elf, raw


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
    print(f"covered={len(cases)} semantic_set={len(cases) - len(faults)} fault_cases={len(faults)}")
    return 0


def cmd_emit(args):
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tb = toolchain_bin(args.toolchain_bin)
    cases = load_cases()

    sem = [c for c in cases if not c["case"].get("expected_fault")]
    words, expected, manifest, nbytes = build_sweep(sem)
    elf, raw = assemble(words, outdir, "sweep", tb)
    (outdir / "sweep_expect.bin").write_bytes(expected)
    (outdir / "sweep.json").write_text(json.dumps(
        {"bytes": nbytes, "cases": manifest}, indent=1) + "\n")

    # Fault cases: every covered ILLI case, the reserved UNDI vectors, plus
    # three dedicated injections (encode_sbz, dst_rb0, defined-but-unimplemented).
    faults = []
    for entry in cases:
        if entry["case"].get("expected_fault") in ("ILLI", "UNDI"):
            case = resolved(entry["case"])
            faults.append({
                "key": f"{Path(entry['file']).stem}_{entry['index']}",
                "fault": case["expected_fault"],
                "word": case["encoding"]["word"],
                "case": case,
            })
    for entry in yaml.safe_load((ROOT / "tests/inst/base/reserved.yaml").read_text()):
        if entry.get("encoding", {}).get("reserved") and entry.get("expected_fault") == "UNDI":
            faults.append({
                "key": "reserved_" + entry["encoding"]["word"][2:],
                "fault": "UNDI",
                "word": entry["encoding"]["word"],
                "case": {"input_state": {}},
            })
    dedicated = [
        ("sbz_shlt_imm32", "ILLI", enc_shl_t_orri(1, 2, 32), False, {}),
        ("dst_rb0_addo", "ILLI", enc_add_o_bbd(0, 1, 2), False, {}),
        # Defined and legal on the golden model (QEMU executes it), but not
        # implemented by this milestone -> ILLI (spec/SimRISC-00 §6.1).
        ("unimpl_ldub", "ILLI", 0x10041000, True,
         {"rb": {"rb1": "0x%x" % ENTRY}}),
    ]
    for key, fault, word, qemu_executes, inp in dedicated:
        faults.append({"key": key, "fault": fault, "word": "0x%08x" % word,
                       "qemu_executes": qemu_executes,
                       "case": {"input_state": inp}})

    fault_meta = []
    for f in faults:
        fwords = build_fault(f["case"], f["word"])
        elf, raw = assemble(fwords, outdir, f"fault_{f['key']}", tb)
        fault_meta.append({"key": f["key"], "fault": f["fault"], "word": f["word"],
                           "qemu_executes": f.get("qemu_executes", False),
                           "elf": elf.name, "raw": raw.name})
    (outdir / "faults.json").write_text(json.dumps(fault_meta, indent=1) + "\n")

    rwords, rexpect = build_rd0rb0()
    elf, raw = assemble(rwords, outdir, "rd0rb0", tb)
    (outdir / "rd0rb0_expect.bin").write_bytes(rexpect)

    print(f"emit: outdir={outdir}")
    print(f"emit: covered={len(cases)} semantic_set={len(sem)} dumped_bytes={nbytes} "
          f"fault_images={len(faults)}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)
    p_emit = sub.add_parser("emit")
    p_emit.add_argument("outdir")
    p_emit.add_argument("--toolchain-bin", default=None)
    p_emit.set_defaults(func=cmd_emit)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
