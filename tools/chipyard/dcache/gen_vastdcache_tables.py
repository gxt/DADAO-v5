#!/usr/bin/env python3
"""gen_vastdcache_tables.py -- page tables / data for `vastdcache.S` (m16-chipyard-009).

Single source of truth for the probe's geometry: the VAs, the PTEs, the data
magics and the cache-set arithmetic are computed here and emitted as an
assembler include (`--emit inc`).  The RTL's indexing is therefore checked
against an independent computation, not against a copy of the RTL.

Geometry (`DADAO-12` §2.2.1-§2.2.4, `m16-chipyard-009` user ruling):

  L1 index = VA[41:29]   L2 index = VA[28:16]   offset = VA[15:0] (64 KiB page)
  normal page: page = PTE[55:16], fragment = VA[15:13] (GPF)
  PTE: HSJU[63:60] | PPN[55:16] | frags[15:8] | R[7] W[6] X[5] G[4] A[3] D[2]
       | SP[1] | P[0]; **big endian**.

Physical layout (PA, `spec/Kaiwu §1.1` PA RAM).  Every line the probe uses is
in group **64** (`PA[12:6] == 64`), while the page-table lines (PA 0x8000 and
0x1_0000) are in group 0, so the data/fill traffic cannot evict a page-table
line by accident:

  0x0000_8000  L1 entry for VA index 0x1000 (PTBR = 0)
  0x0001_0000  L2 table (also mapped at VA 2 TiB + 0x1_0000 for PTE writes)
  0x0004_1000  A: hit/miss line
  0x0004_3000  B0..B7: the eight ways of one group (stride 0x2000)
  0x0005_3000  L9 / L10 / fresh 1..5
  0x0006_1000  fresh 6..8
  0x0007_0000  old target of the PTW page (64 KiB page 7)
  0x0009_0000  new target after the PTE rewrite (64 KiB page 9)
  0x0008_0000  code page (offset 0x1000 has the instruction word the probe
               stores; the fetch path has no I-cache yet, so it reads memory)

`PA_CODE + 0x1000` (0x8_1000) is also in group 64: the 8 fresh fills of the
write-back section evict the dirty code line after the data path already sees
the new value, which is exactly the write-back timing the task asks for.

The cause one-hots (`UNDI`, `CFXTRAP`) are parsed from
`.tao/contracts/contract-see.md` §6.1 through the PTW checker's parser (the
same copy the other Vast probes use), never hard-coded here.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]

VA_BASE = 0x200_0000_0000          # kernel window: VA = PA + 2 TiB
PAGE = 0x1_0000

PA_L1E = 0x0_8000                  # L1 entry for VA index 0x1000
PA_L2 = 0x1_0000
PA_A = 0x4_1000
PA_B = [0x4_3000 + i * 0x2000 for i in range(8)]     # B0..B7 (one group)
PA_L9 = 0x5_3000
PA_L10 = 0x5_5000
PA_FRESH = [0x5_7000, 0x5_9000, 0x5_B000, 0x5_D000, 0x5_F000,
            0x6_1000, 0x6_3000, 0x6_5000]
PA_PAGE = 0x7_0000
PA_PAGE_OLD = 0x7_0000      # 64 KiB-aligned normal page (PTE[55:16] = 7)
PA_PAGE_NEW = 0x9_0000      # 64 KiB-aligned normal page (PTE[55:16] = 9)
PA_CODE_PAGE = 0x8_0000
PA_CODE = PA_CODE_PAGE + 0x1000

# m16-chipyard-010: the instruction cache is now real, so the probe has to evict
# the code line from it explicitly before the fetch can observe the write-back.
# Eight one-line "return" blocks in the *same* instruction-cache group as the
# code line (PA[12:6] = 64) and with distinct tags do that by LRU.
PA_EVICT_PAGES = [2, 3, 10, 11, 12, 13, 14, 15]
PA_EVICT = [(p << 16) | 0x1000 for p in PA_EVICT_PAGES]
VA_EVICT = [VA_BASE + pa for pa in PA_EVICT]

VA_A = VA_BASE + PA_A
VA_B = [VA_BASE + pa for pa in PA_B]
VA_L9 = VA_BASE + PA_L9
VA_L10 = VA_BASE + PA_L10
VA_FRESH = [VA_BASE + pa for pa in PA_FRESH]
VA_PAGE = VA_BASE + PA_PAGE
VA_CODE = VA_BASE + PA_CODE
VA_L2SELF = VA_BASE + PA_L2

OFF_L2_SELF = 1 * 8
OFF_L2_PAGE = 7 * 8
OFF_L2_CODE = 8 * 8

# ---- values ---------------------------------------------------------------
M_A = 0xC0DE_0000_0000_0100
M_B = [0xC0DE_0000_0000_0200 + i for i in range(8)]
M_L9 = 0xC0DE_0000_0000_0300
M_L10 = 0xC0DE_0000_0000_0301
M_FRESH = [0xC0DE_0000_0000_0400 + i for i in range(8)]
M_PAGE_OLD = 0x9A9A_0000_0000_0100
M_PAGE_NEW = 0x9A9A_0000_0000_0200
MARK_JUMP1 = 0x0C0D_E001
MARK_JUMP2 = 0x0C0D_E002
MARK_JUMP3 = 0x0C0D_E003
FAIL_POINT_1 = 0x21                # `__pad` failure code (= table index)
FAIL_POINT_2 = 0x22

# `__pad` slot index -> resume label offset in `.text` (two independent jumps).
# Slot offset inside the framework's `.faulttab` (base + 8 + point*8).
SLOT_OFF_1 = 8 + FAIL_POINT_1 * 8


def pte(pa, r=1, w=1, x=1, g=0, a=1, d=1, sp=0, p=1, frags=0xFF, hsju=0xF):
    """Assemble a PTE (big-endian value)."""
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


PTE_L1 = pte(PA_L2)                         # VA index 0x1000 -> L2 table
PTE_SELF = pte(PA_L2)                       # VA 2 TiB + 0x1_0000 -> itself
PTE_DATA = pte(0x4_0000)                    # VA 0x4_0000 page (A/B lines)
PTE_DATA1 = pte(0x5_0000)                   # VA 0x5_0000 page (L9/L10/fresh)
PTE_DATA2 = pte(0x6_0000)                   # VA 0x6_0000 page (fresh 6..8)
PTE_PAGE_OLD = pte(PA_PAGE_OLD)             # VA 0x7_0000 -> 0x7_8000
PTE_PAGE_NEW = pte(PA_PAGE_NEW)             # after the in-core rewrite
PTE_CODE = pte(PA_CODE_PAGE)                # VA 0x8_0000 (X=1)
PTE_EVICT = {p: pte(p << 16) for p in PA_EVICT_PAGES}

L2 = [0] * 16
L2[1] = PTE_SELF
L2[4] = PTE_DATA
L2[5] = PTE_DATA1
L2[6] = PTE_DATA2
L2[7] = PTE_PAGE_OLD
L2[8] = PTE_CODE
for p, v in PTE_EVICT.items():
    L2[p] = v


def cause_one_hots(root: pathlib.Path) -> tuple[int, int]:
    """`(UNDI, CFXTRAP)` one-hots from the contract's §6.1 cause table."""
    # `m16-chipyard-018`：cfx4 的 checker 已迁到 `tests/arch/ptw/`，位号解析
    # 复用同一份 `bit_table`（避免第二套 contract-see §6.1/§6.1.1 解析）。
    spec = importlib.util.spec_from_file_location(
        "ptw_regs_bits",
        HERE.parents[2] / "tests" / "arch" / "ptw" / "check_ptw_regs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    table = mod.bit_table(root)
    cls = table["class"]
    for name in ("UNDI", "CFXTRAP"):
        if name not in cls:
            raise SystemExit("gen_vastdcache: contract-see §6.1 missing %s" % name)
    return 1 << cls["UNDI"], 1 << cls["CFXTRAP"]


def check_geometry() -> None:
    """The probe's whole point: all data lines share one group, the page-table
    lines live in a different one."""
    idx = lambda pa: (pa >> 6) & 0x7F
    data = [PA_A] + PA_B + [PA_L9, PA_L10] + PA_FRESH + [PA_CODE]
    if any(idx(pa) != 64 for pa in data):
        raise SystemExit("gen_vastdcache: a data line is outside group 64: %r"
                         % [(hex(pa), idx(pa)) for pa in data if idx(pa) != 64])
    if idx(PA_L1E) != 0 or idx(PA_L2) != 0:
        raise SystemExit("gen_vastdcache: a page-table line is not in group 0")
    if (PA_CODE >> 6) & 0x7F != 64:
        raise SystemExit("gen_vastdcache: the code line is not in group 64")
    # m16-chipyard-010: every evictor line shares the code line's group and its
    # tag is distinct from the code line and from its siblings.
    if any(((pa >> 6) & 0x7F) != 64 for pa in PA_EVICT):
        raise SystemExit("gen_vastdcache: an evictor line is outside group 64")
    ev_tags = {(pa >> 13) for pa in PA_EVICT} | {(PA_CODE >> 13)}
    if len(ev_tags) != len(PA_EVICT) + 1:
        raise SystemExit("gen_vastdcache: evictor/code tags collide")
    # L2[page] must map VA page `page` to that page itself (an off-by-one here
    # sends a jump to a different line and the eviction never happens).
    for pnum in PA_EVICT_PAGES + [PA_CODE_PAGE >> 16]:
        if L2[pnum] != pte(pnum << 16):
            raise SystemExit("gen_vastdcache: L2[%d] does not map VA page %d"
                             % (pnum, pnum))


def emit_inc(out, undi: int, cfxtrap: int) -> None:
    w = lambda name, value: out.write(".equ %s, 0x%X\n" % (name, value))
    w("VA_BASE", VA_BASE)
    w("VA_L2SELF", VA_L2SELF)
    w("VA_A", VA_A)
    for i, va in enumerate(VA_B):
        w("VA_B%d" % i, va)
    w("VA_L9", VA_L9)
    w("VA_L10", VA_L10)
    for i, va in enumerate(VA_FRESH):
        w("VA_F%d" % (i + 1), va)
    w("VA_PAGE", VA_PAGE)
    w("VA_CODE", VA_CODE)
    for i, (pa, va) in enumerate(zip(PA_EVICT, VA_EVICT)):
        w("PA_EV%d" % i, pa)
        w("VA_EV%d" % i, va)
    for i, pnum in enumerate(PA_EVICT_PAGES):
        w("PTE_EV%d" % i, PTE_EVICT[pnum])
    w("PA_L1E", PA_L1E)
    w("PA_L2", PA_L2)
    w("PA_A", PA_A)
    for i, pa in enumerate(PA_B):
        w("PA_B%d" % i, pa)
    w("PA_L9", PA_L9)
    w("PA_L10", PA_L10)
    for i, pa in enumerate(PA_FRESH):
        w("PA_F%d" % (i + 1), pa)
    w("PA_PAGE_OLD", PA_PAGE_OLD)
    w("PA_PAGE_NEW", PA_PAGE_NEW)
    w("PA_CODE", PA_CODE)
    w("OFF_L2_PAGE", OFF_L2_PAGE)
    w("M_A", M_A)
    for i, m in enumerate(M_B):
        w("M_B%d" % i, m)
    w("M_L9", M_L9)
    w("M_L10", M_L10)
    for i, m in enumerate(M_FRESH):
        w("M_F%d" % (i + 1), m)
    w("M_PAGE_OLD", M_PAGE_OLD)
    w("M_PAGE_NEW", M_PAGE_NEW)
    w("MARK_JUMP1", MARK_JUMP1)
    w("MARK_JUMP2", MARK_JUMP2)
    w("MARK_JUMP3", MARK_JUMP3)
    w("FAIL_POINT_1", FAIL_POINT_1)
    w("FAIL_POINT_2", FAIL_POINT_2)
    w("SLOT_OFF_1", SLOT_OFF_1)
    w("PTE_PAGE_NEW", PTE_PAGE_NEW)
    w("PTE_PAGE_OLD", PTE_PAGE_OLD)
    w("PTE_L1", PTE_L1)
    w("PTE_SELF", PTE_SELF)
    w("PTE_DATA", PTE_DATA)
    w("PTE_DATA1", PTE_DATA1)
    w("PTE_DATA2", PTE_DATA2)
    w("PTE_CODE", PTE_CODE)
    w("UNDI_ONEHOT", undi)
    w("CFXTRAP_ONEHOT", cfxtrap)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", choices=["inc"], default="inc")
    ap.add_argument("--root", type=pathlib.Path, default=ROOT)
    ap.add_argument("--check-geometry", action="store_true")
    args = ap.parse_args(argv)
    check_geometry()
    if args.check_geometry:
        print("gen_vastdcache: geometry ok (data group 64, page-table group 0)")
        return 0
    undi, cfxtrap = cause_one_hots(args.root)
    if args.emit == "inc":
        emit_inc(sys.stdout, undi, cfxtrap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
