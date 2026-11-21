#!/usr/bin/env python3
"""gen_vasticache_tables.py -- page tables / geometry for `vasticache.S` (m16-chipyard-010).

Single source of truth for the probe's geometry: the VAs, the PTEs, the block
magics and the cache-group arithmetic are computed here and emitted as an
assembler include (`--emit inc`).  The RTL's indexing is therefore checked
against an independent computation, not against a copy of the RTL.

Geometry (`DADAO-12` §2.2.1-§2.2.4, user ruling 2026-11-20):

  L1 index = VA[41:29]   L2 index = VA[28:16]   offset = VA[15:0] (64 KiB page)
  normal page: page = PTE[55:16], fragment = VA[15:13] (GPF)
  PTE: HSJU[63:60] | PPN[55:16] | frags[15:8] | R[7] W[6] X[5] G[4] A[3] D[2]
       | SP[1] | P[0]; **big endian**.

The instruction cache's group index is `PA[12:6]` (line offset `PA[5:0]`,
6 + 7 = 13 < 16 ⇒ VIPT with no alias inside a 64 KiB page).

Physical layout (PA, `spec/Kaiwu §1.1` PA RAM).  Ten **instruction blocks**,
each 16 instructions = exactly one 64 B line, live at the same line offset
inside ten different 64 KiB pages (so the tags differ while the group index
does not):

  0x0000_8000  L1 entry for VA index 0x1000 (PTBR = 0)
  0x0001_0000  L2 table (page 1; nothing else lives in this page)
  0x0002_1000  A1 .. A8 = pages 2..9, offset 0x1000  -> group 64, eight ways
  0x000A_1000  A9 = page 10, offset 0x1000          -> group 64, the 9th line
  0x000B_0000  C1 = page 11, offset 0x0000          -> group 0

`C1` is the group-distinctness control: its `PA[12]` is 0 while every A line has
`PA[12] = 1`, but **both have `PA[11:6] == 0`/`64`** — with a 6-bit group index
(`PA[11:6]`) C1 would land in the A lines' group and evict one of them, which
the probe observes as a refill of A3.  With the specified 7-bit index the two
sets of lines are in different groups and nothing is evicted.

The block magics are the only expected values the checker needs; they are
emitted here so the probe and the oracle share one definition.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]

VA_BASE = 0x200_0000_0000          # kernel window: VA = PA + 2 TiB
PAGE = 0x1_0000

PA_L1E = 0x0_8000                  # L1 entry for VA index 0x1000
PA_L2 = 0x1_0000
OFF_MAIN = 0x1000                  # line offset of A1..A9 (PA[12:6] = 64)
OFF_ALT = 0x0000                   # line offset of C1   (PA[12:6] = 0)

PAGES_A = list(range(2, 11))       # pages 2..10: A1..A8 + A9
PAGE_C = 11

PA_A = [p * PAGE + OFF_MAIN for p in PAGES_A]
PA_C = PAGE_C * PAGE + OFF_ALT

VA_A = [VA_BASE + pa for pa in PA_A]
VA_C = VA_BASE + PA_C

# ---- values ---------------------------------------------------------------
M_A = [0xC0DE_0000_0000_0A00 + i for i in range(len(PA_A))]
M_C = 0xC0DE_0000_0000_0B00

#: The probe's own line lives in the core-internal SRAM window and must never
#: appear in the cache log (only translated fetches are cached).
SRAM_LINE = 0xFF01_0100


def pte(pa, r=1, w=0, x=1, g=0, a=1, d=1, sp=0, p=1, frags=0xFF, hsju=0xF):
    """Assemble a PTE (big-endian value).  Code pages are execute-only-ish:
    R = 1 (loadable), W = 0, X = 1."""
    v = (hsju & 0xF) << 60
    v |= pa & (0x00FF_FFFF_FFFF_0000 if sp == 0 else 0x00FF_FFFF_E000_0000)
    v |= (frags & 0xFF) << 8
    v |= (r & 1) << 7
    v |= (w & 1) << 6
    v |= (x & 1) << 5
    v |= (g & 1) << 4
    v |= (a & 1) << 3
    v |= (d & 1) << 2
    v |= (sp & 1) << 1
    v |= (p & 1)
    return v


PTE_L1 = pte(PA_L2)                          # VA index 0x1000 -> L2 table
PTE_CODE = {p: pte(p * PAGE) for p in PAGES_A + [PAGE_C]}

L2_SIZE = 16
L2 = [0] * L2_SIZE
for p, v in PTE_CODE.items():
    L2[p] = v


def group_of(pa: int) -> int:
    """The instruction cache's group index: PA[12:6] (7 bits)."""
    return (pa >> 6) & 0x7F


def group6_of(pa: int) -> int:
    """The *wrong* index a 6-bit implementation would use: PA[11:6]."""
    return (pa >> 6) & 0x3F


def check_geometry() -> None:
    """The probe's whole point, checked independently of the RTL:
    every A line shares group 64 while their tags differ; C1 is in group 0 and
    shares the 6-bit group with the A lines (that is what makes a 6-bit index
    observable); each block fits exactly one 64 B line."""
    if any(group_of(pa) != 64 for pa in PA_A):
        raise SystemExit("gen_vasticache: an A line is outside group 64: %r"
                         % [(hex(pa), group_of(pa)) for pa in PA_A])
    if group_of(PA_C) != 0:
        raise SystemExit("gen_vasticache: the C line is not in group 0")
    if group6_of(PA_C) != group6_of(PA_A[0]):
        raise SystemExit("gen_vasticache: C1 and A1 must share the 6-bit group "
                         "(otherwise a 6-bit index is not observable)")
    tags = {(pa >> 13) for pa in PA_A}
    if len(tags) != len(PA_A):
        raise SystemExit("gen_vasticache: two A lines share a tag")
    for pa in PA_A + [PA_C]:
        if pa % 64 != 0:
            raise SystemExit("gen_vasticache: a block start is not line-aligned")
        if pa & 0x3F:
            raise SystemExit("gen_vasticache: a block is not at line offset 0")
    if group_of(PA_L1E) != 0 or group_of(PA_L2) != 0:
        # Page-table lines must not collide with the A group by accident.
        raise SystemExit("gen_vasticache: page-table lines are not in group 0")


def emit_inc(out, blocks_per_line: int) -> None:
    w = lambda name, value: out.write(".equ %s, 0x%X\n" % (name, value))
    w("VA_BASE", VA_BASE)
    w("PA_L1E", PA_L1E)
    w("PA_L2", PA_L2)
    w("PA_C", PA_C)
    w("VA_C", VA_C)
    w("M_C", M_C)
    w("SRAM_LINE", SRAM_LINE)
    w("IC_BLOCK_INSNS", blocks_per_line)
    for i, (pa, va) in enumerate(zip(PA_A, VA_A), start=1):
        w("PA_A%d" % i, pa)
        w("VA_A%d" % i, va)
        w("M_A%d" % i, M_A[i - 1])
    w("PTE_L1", PTE_L1)
    dim = len(L2)
    w("L2_SIZE", dim)
    for i, v in enumerate(L2):
        w("PTE_L2_%d" % i, v)


BLOCK_INSNS = 16


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", choices=["inc"], default="inc")
    ap.add_argument("--root", type=pathlib.Path, default=ROOT)
    ap.add_argument("--check-geometry", action="store_true")
    args = ap.parse_args(argv)
    check_geometry()
    if args.check_geometry:
        print("gen_vasticache: geometry ok (A1..A9 group 64, C1 group 0, "
              "both share the 6-bit group; %d-instruction blocks)"
              % BLOCK_INSNS)
        return 0
    if args.emit == "inc":
        emit_inc(sys.stdout, BLOCK_INSNS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
