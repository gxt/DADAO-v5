#!/usr/bin/env python3
"""Program images for the two ``m12-chipyard-018`` fetch-port probes.

Two independent probes share this generator because they are the same
instruction stream in two different memory layouts:

``timing``
    A program that runs on the ``WumingTinyConfig`` harness (``+loadmem=``).
    It performs a handful of stores first, which stalls the core long enough for
    the 8-beat fetch queue to fill, and then runs a straight-line block of
    ordinary ALU ops (``or.o``) followed by a block of shift ops (``shl.o``).
    The harness log with ``+verbose`` carries one ``exec ... cycle=`` line per
    executed instruction, so the evidence script can measure the per-instruction
    cycles directly: ``or.o`` must take one cycle (fast path), ``shl.o`` two
    (R1 = C: shift/bit-field ops take the two-cycle ``SLOW`` path).

``tb``
    A program for the standalone Verilator test bench
    (``tools/chipyard/fetch_probe/tb_fetch_probe.cpp``).  It builds a jump
    target and a store address, jumps far away and then issues one store.  The
    bench answers the store after a long delay, which is the case that proves
    the two TileLink ports are independent: the fetch port keeps prefetching
    while the data port is stalled.

``xbeat``
    A straight-line ``or.o`` stream spanning many fetch beats (m12-020).  The
    harness prints one ``exec ... cycle=`` line per instruction, so the evidence
    script measures the cost of crossing a beat boundary before/after the four
    prefetch slots and the data-priority arbitration.

All images are built from the encoders in ``tools/chipyard/inst_sweep.py`` so
there is exactly one source of instruction encoding in this module.

Usage:
    python3 tools/chipyard/fetch_probe/gen_probe.py OUTDIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "chipyard"))

import inst_sweep as S  # noqa: E402

# The bench serves the image from the reset vector in the BootROM window.
TB_BASE = 0xFFFF_FFFF_0000
TB_JUMP_OFF = 0x2000       # far outside the 64-byte fetch queue
TB_IMAGE_SIZE = 0x2100

# The store sits right at the jump target, so the fetch queue is empty (one
# demand beat) when the data access starts.
TB_ALU_COUNT = 12


def enc_jump(ha, hb, imm12):
    return (0x71 << 24) | (ha << 18) | (hb << 12) | (imm12 & 0xFFF)


def enc_or_o(rdhb, rdhc, rdhd):
    # `or.o rdHB, rdHC, rdHD` -- 1-cycle fast path (opc 0x40, sub-row 0x09).
    return (0x40 << 24) | (0x09 << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def enc_shl_o(rdhb, rdhc, rdhd):
    # `shl.o rdHB, rdHC, rdHD` -- two-cycle `SLOW` path (opc 0x40, row 0x10).
    return (0x40 << 24) | (0x10 << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def timing_program():
    """Stores to fill the queue, then a 1-cycle block and a 2-cycle block."""
    words = []
    words += S.load_rb(19, 0xFFFF_FF01_8100)   # store pointer (SRAM window)
    words += S.load_rd(20, 0x1122_3344_5566_7788)
    for i in range(6):                          # ~7 cycles each: fills 8 beats
        words.append(S.enc_st_o_rd(20, 19, 8 * i))
    words += S.load_rd(2, 0x0000_0000_0000_0003)  # shift amount
    words += S.load_rd(4, 0)                      # accumulator
    or_start = len(words)
    for _ in range(12):
        words.append(enc_or_o(4, 4, 2))
    shl_start = len(words)
    for _ in range(8):
        words.append(enc_shl_o(4, 4, 2))
    words.append(0x0000_0000)                     # UNDI: bounded stop
    return words, {"or_start": or_start, "or_end": shl_start,
                   "shl_start": shl_start, "shl_end": len(words) - 1}


XBEAT_ALU_COUNT = 400


def xbeat_program():
    """Straight-line ``or.o`` stream: two instructions per beat, no branches.

    The harness prints one ``exec ... cycle=`` line per instruction, so the
    evidence script can measure the cost of crossing a beat boundary: with the
    fetch queue draining at every crossing (m12-018) it is the SRAM round trip
    (7-8 cycles); with enough prefetch slots it is one cycle.
    """
    words = []
    words += S.load_rd(2, 3)                      # second operand of or.o
    words += S.load_rd(4, 0)                      # accumulator
    start = len(words)
    for _ in range(XBEAT_ALU_COUNT):
        words.append(enc_or_o(4, 4, 2))
    words.append(0x0000_0000)                     # UNDI: bounded stop
    return words, {"block_start": start, "block_len": XBEAT_ALU_COUNT}


def tb_program():
    """Jump far away, then store (answered slowly) and run from the queue."""
    words = []
    words += S.load_rb(1, TB_BASE + TB_JUMP_OFF)  # jump target
    words += S.load_rb(3, 0xFFFF_FF00_0000)       # data address
    words += S.load_rd(2, 0x1122_3344_5566_7788)  # store data
    jump_index = len(words)
    words.append(enc_jump(1, 0, 0))               # jump rb1, rd0, 0
    target_offset = TB_JUMP_OFF                   # in bytes from TB_BASE
    code = [S.enc_st_o_rd(2, 3, 0)]
    code += [enc_or_o(4, 4, 2) for _ in range(TB_ALU_COUNT)]
    code.append(0x0000_0000)                      # UNDI: bounded stop
    return words, code, target_offset, {"jump_index": jump_index,
                                        "alu_count": TB_ALU_COUNT}


def build_timing(outdir: Path, tb: Path):
    words, marks = timing_program()
    elf, raw = S.assemble(words, outdir, "timing", tb)
    (outdir / "timing.json").write_text(json.dumps(marks, indent=1) + "\n")
    return elf, raw, words, marks


def build_xbeat(outdir: Path, tb: Path):
    words, marks = xbeat_program()
    elf, raw = S.assemble(words, outdir, "xbeat", tb)
    (outdir / "xbeat.json").write_text(json.dumps(marks, indent=1) + "\n")
    return elf, raw, words, marks


def build_tb(outdir: Path):
    words, code, target, marks = tb_program()
    image = bytearray(TB_IMAGE_SIZE)
    head = b"".join(w.to_bytes(4, "big") for w in words)
    tail = b"".join(w.to_bytes(4, "big") for w in code)
    image[0:len(head)] = head
    image[target:target + len(tail)] = tail
    (outdir / "probe.img").write_bytes(bytes(image))
    info = {"base": TB_BASE, "size": TB_IMAGE_SIZE, "jump_target": TB_BASE + target,
            "store_addr": 0xFFFF_FF00_0000, "alu_count": marks["alu_count"]}
    (outdir / "probe.json").write_text(json.dumps(info, indent=1) + "\n")
    return info


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    outdir = Path(argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    tb = S.toolchain_bin(None)
    elf, raw, words, marks = build_timing(outdir, tb)
    info = build_tb(outdir)
    xelf, _, xwords, xmarks = build_xbeat(outdir, tb)
    print(f"xbeat: {len(xwords)} words -> {xelf.name}, "
          f"block [{xmarks['block_start']},{xmarks['block_start'] + xmarks['block_len']})")
    print(f"timing: {len(words)} words -> {elf.name} ({elf.stat().st_size} B ELF), "
          f"or block [{marks['or_start']},{marks['or_end']}) "
          f"shl block [{marks['shl_start']},{marks['shl_end']})")
    print(f"tb: image {info['size']} B at 0x{info['base']:012x}, "
          f"jump target 0x{info['jump_target']:012x}, "
          f"store 0x{info['store_addr']:012x}, {info['alu_count']} ALU ops")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
