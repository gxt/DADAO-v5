#!/usr/bin/env python3
"""gen_ptw_walk_tables.py -- page tables for `ptw_walk.S` (m16-chipyard-007).

Single source of truth for the probe's page-table geometry: the VAs, the PTEs
and the expected PTE values after each A/D step are computed here and emitted as
an assembler include (`--emit inc`).  The RTL's own indexing is therefore checked
against an independent computation, not against a copy of the RTL.

Geometry (`DADAO-12` §2.2.1-§2.2.4):

  L1 index = VA[41:29]   L2 index = VA[28:16]   offset = VA[15:0] (64 KiB page)
  superpage: offset = VA[28:0], fragment = VA[28:26] (SPF), page = PTE[55:29]
  normal page: fragment = VA[15:13] (GPF), page = PTE[55:16]
  PTE: HSJU[63:60] | PPN[55:16] | frags[15:8] | R[7] W[6] X[5] G[4] A[3] D[2]
       | SP[1] | P[0]; **big endian**.

Physical layout (PA, `spec/Kaiwu §1.1` PA RAM):

  0x0000_0000  L1 table (PTBR = 0): kernel-window entry at index 0x1000,
               superpage at 0x1002, user-space fault entries at 3..6
  0x0001_0000  L2 table for L1 index 0x1000 (also the probe's data page)
  0x0003_0000  L2 table for L1 index 6 (fault cases)
  0x0005_0000  executable stub reached through a translation
  0x4000_0000  superpage fragment 0       0x4400_0000  fragment 1
"""

import argparse

VA_BASE = 0x200_0000_0000          # kernel window: VA = PA + 2 TiB

PA_L1 = 0x0000_0000
PA_L2 = 0x0001_0000
PA_L2B = 0x0003_0000
PA_CODE = 0x0005_0000
PA_FRESH = 0x0006_0000
PA_SUPER = 0x4000_0000
PA_SUPER1 = 0x4400_0000

PAGE = 0x1_0000


def pte(hsju=0xF, pa=0, frags=0xFF, r=1, w=1, x=1, g=0, a=0, d=0, sp=0, p=1):
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


# ---- virtual addresses -----------------------------------------------------
VA_DATA = VA_BASE + PA_L2               # 0x200_0001_0000: data page (self PTE at +8)
# The L2 fault table lives under L1 index 6 (`VA = 6 << 29`); it is addressed
# from the user half of the window, so the VA is not the PA + 2 TiB.
VA_L2B = 6 << 29                        # 0xc000_0000: L2 fault entries
VA_L2B0 = VA_L2B                        # 0xc000_0000: L2 P = 0
VA_L2B1 = VA_L2B + PAGE                 # 0xc001_0000: GPF bit 0 = 0
VA_L2B2 = VA_L2B + 2 * PAGE             # 0xc002_0000: HSJU = U only
VA_L2B3 = VA_L2B + 3 * PAGE             # 0xc003_0000: R=1, W=0
VA_L2B4 = VA_L2B + 4 * PAGE             # 0xc004_0000: X = 0
VA_W0 = VA_L2B + 3 * PAGE               # 0xc003_0000: R=1, W=0
VA_NOX = VA_L2B + 4 * PAGE               # 0xc004_0000: X=0
VA_CODE = VA_BASE + PA_CODE             # 0x200_0005_0000: executable stub
VA_FRESH = VA_BASE + PA_FRESH           # 0x200_0006_0000: fresh page (A/D case)
VA_SUPER = VA_BASE + PA_SUPER           # 0x200_4000_0000: superpage fragment 0
VA_SUPER1 = VA_BASE + PA_SUPER1         # 0x200_4400_0000: fragment 1
VA_L1_NP = 3 << 29                      # 0x6000_0000: L1 P=0, SP=0
VA_L1_SP = 4 << 29                      # 0x8000_0000: L1 P=0, SP=1
VA_L1_SPF = 5 << 29                     # 0xa000_0000: L1 P=1 SP=1 SPF bit 0 = 0

# ---- page tables -----------------------------------------------------------
L1 = {
    3: pte(p=0, sp=0),                        # missing page (SP=0)
    4: pte(p=0, sp=1),                        # missing superpage
    5: pte(pa=PA_SUPER, frags=0xFE, sp=1),    # superpage, fragment 0 absent
    6: pte(pa=PA_L2B),                        # normal-page table (fault cases)
    0x1000: pte(pa=PA_L2),                    # kernel-window normal pages
    0x1002: pte(pa=PA_SUPER, frags=0xFF, sp=1),  # 512 MiB superpage
}

L2 = {
    1: pte(pa=PA_L2),                         # the data page (self-referential)
    3: pte(pa=PA_L2, r=1, w=0, x=1),          # W = 0  -> NWPERM on store
    5: pte(pa=PA_CODE),                       # executable page (fetch test)
    6: pte(pa=PA_FRESH, a=0, d=0),            # fresh page (A/D write-back case)
}

L2B = {
    0: pte(p=0),                              # L2 P=0 -> DGPTRAP
    1: pte(pa=PA_L2, frags=0xFE),             # GPF bit 8 = 0 -> DGPFTRAP
    2: pte(pa=PA_L2, hsju=0x1),               # HSJU = U only -> NHPERM (hypv)
    3: pte(pa=PA_L2, r=1, w=0, x=1),          # NWPERM
    4: pte(pa=PA_L2, r=1, w=1, x=0),          # NXPERM (fetch)
}

# A/D bookkeeping expected values for the data page's own PTE (L2 index 1).
DATA_PTE_A0D0 = pte(pa=PA_L2, a=0, d=0)
DATA_PTE_A1D0 = pte(pa=PA_L2, a=1, d=0)
DATA_PTE_A1D1 = pte(pa=PA_L2, a=1, d=1)
DATA_PTE_PA = PA_L2 + 8 * 1               # physical address of L2[1]
FRESH_PTE_PA = PA_L2 + 8 * 6              # physical address of L2[6]

MAGIC0 = 0x0BAD_0FEE_1234_5678            # superpage fragment 0
MAGIC1 = 0x55AA_1234_DEAD_BEEF            # superpage fragment 1
PAYLOAD = 0x1122_3344_5566_7788           # normal-page payload at +0x700
STORE_VAL = 0xDEAD_BEEF_CAFE_F00D         # stored then read back
STUB_MARK = 0x77                          # set by the mapped stub
FRESH_MAGIC = 0xA5A5_5A5A_1234_4321       # fresh page payload at PA 0x6_0000


def _table(name, base, entries):
    out = ['.section %s, "a"' % name]
    for idx in sorted(entries):
        out.append(".org 0x%x" % (idx * 8))
        out.append(".dd.o64 0x%016x        @@ [%d]" % (entries[idx], idx))
    return out


def emit_inc():
    out = []
    out.append("@@ ptw_walk_tables.inc -- generated by tests/arch/ptw/gen_ptw_walk_tables.py")
    out.append("@@ Do not edit: geometry and expected PTE values come from there.")
    out.append("")
    for name, value in [
        ("VA_DATA", VA_DATA),
        ("VA_W0", VA_W0), ("VA_NOX", VA_NOX), ("VA_CODE", VA_CODE),
        ("VA_SUPER", VA_SUPER), ("VA_SUPER1", VA_SUPER1),
        ("VA_L1_NP", VA_L1_NP), ("VA_L1_SP", VA_L1_SP), ("VA_L1_SPF", VA_L1_SPF),
        ("VA_L2B0", VA_L2B), ("VA_L2B1", VA_L2B + PAGE),
        ("VA_L2B2", VA_L2B + 2 * PAGE), ("VA_L2B3", VA_L2B + 3 * PAGE),
        ("PTE_DATA_A0D0", DATA_PTE_A0D0), ("PTE_DATA_A1D0", DATA_PTE_A1D0),
        ("PTE_DATA_A1D1", DATA_PTE_A1D1), ("PTE_DATA_PA", DATA_PTE_PA),
        ("VA_FRESH", VA_FRESH), ("FRESH_PTE_PA", FRESH_PTE_PA),
        ("PAYLOAD", PAYLOAD), ("STORE_VAL", STORE_VAL),
        ("MAGIC0", MAGIC0), ("MAGIC1", MAGIC1), ("STUB_MARK", STUB_MARK),
        ("FRESH_MAGIC", FRESH_MAGIC),
    ]:
        out.append(".equ %-16s, 0x%016x" % (name, value))
    out.append("")
    out += _table(".pt_l1", PA_L1, L1)
    out += _table(".pt_l2", PA_L2, L2)
    out += _table(".pt_l2b", PA_L2B, L2B)
    out.append("")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="page-table include for ptw_walk.S")
    ap.add_argument("--emit", choices=["inc"], default="inc")
    args = ap.parse_args()
    print(emit_inc(), end="")


if __name__ == "__main__":
    main()
