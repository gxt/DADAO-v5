#!/usr/bin/env python3
"""gen_ptw_tlb_tables.py -- page tables and constants for `ptw_tlb.S` (m16-chipyard-008).

Single source of truth for the TLB probe's geometry: VAs, PTEs, the PTE words
written at run time, the data magics and every expected post-operation PTE
value.  The assembler include (`--emit inc`) carries only symbols; the checker
imports this module for the expected record list, so no index or bit field is
written twice.

Geometry (`DADAO-12` §2.2.1-§2.2.4, same as `gen_ptw_walk_tables.py`):

  L1 index = VA[41:29]   L2 index = VA[28:16]   offset = VA[15:0] (64 KiB page)
  superpage: offset = VA[28:0], fragment = VA[28:26] (SPF), page = PTE[55:29]
  normal page: fragment = VA[15:13] (GPF), page = PTE[55:16]
  PTE: HSJU[63:60] | PPN[55:16] | frags[15:8] | R[7] W[6] X[5] G[4] A[3] D[2]
       | SP[1] | P[0]; **big endian**.

TLB geometry under test (`contract-tlb` TLB-02, user ruling 2026-11-19):

  normal pages 2 sets x 8 ways, set index = VA[16]
  superpages   4 fully associative entries
  both         LRU replacement (an invalid entry is taken first)

The normal pages P1..P9 all have VA[16] = 1 (set 1) so they can fill one set
without competing with the self-mapped L1/L2 table pages (VA[16] = 0).

Physical layout (PA, `spec/Kaiwu §1.1` PA RAM [0, 2 GiB)):

  0x0000_0000  L1 table (PTBR = 0): normal window at 0x1000, superpages 0x1002..0x1006
  0x0001_0000  L2 table (also self-mapped at VA_BASE + 0)
  0x0010_0000  P1..P9 data pages         0x0020_0000  their `new` mapping targets
  0x0040_0000  I/D OR-merge page (stub + data)
  0x0050_0000  I-only page (stub)
  0x0060_0000  PI stub (I-side command matrix)  0x0061_0000  its new target
  0x0070_0000  PD data page                     0x0071_0000  its new target
  0x4000_0000  superpage data (offsets 0x0..0x4000)
  0x6000_0000  new superpage targets (offsets 0x0 / 0x1000)
"""

import argparse

VA_BASE = 0x200_0000_0000          # kernel window: VA = PA + 2 TiB
PA_L1 = 0x0000_0000
PA_L2 = 0x0001_0000
PAGE = 0x1_0000

# ---- normal pages: VA[16] = 1 (set 1 of the data table) --------------------
P_INDEX = {k: 0x21 + 2 * (k - 1) for k in range(1, 10)}   # L2 indices, odd
PA_P = {k: 0x10_0000 + (k - 1) * PAGE for k in range(1, 10)}
PA_P_NEW = {k: 0x20_0000 + (k - 1) * PAGE for k in range(1, 10)}
VA_P = {k: VA_BASE + P_INDEX[k] * PAGE for k in range(1, 10)}

# ---- self-mapped table pages (VA[16] = 0, set 0) ---------------------------
VA_L2SELF = VA_BASE + 0 * PAGE     # L2 table at PA 0x1_0000 (L2 index 0)
VA_L1SELF = VA_BASE + 2 * PAGE     # L1 table at PA 0        (L2 index 2)

# ---- the remaining set-0 pages --------------------------------------------
PA_OR, PA_OR_NEW = 0x0040_0000, 0x0041_0000
VA_OR = VA_BASE + 0x20 * PAGE

PA_PX = 0x0050_0000
VA_PX = VA_BASE + 0x22 * PAGE

PA_PI, PA_PI_NEW = 0x0060_0000, 0x0061_0000
VA_PI = VA_BASE + 0x24 * PAGE

PA_PD, PA_PD_NEW = 0x0070_0000, 0x0071_0000
VA_PD = VA_BASE + 0x26 * PAGE

# ---- ASID / G case: one G = 1 and one G = 0 (same ASID) page --------------
PA_G, PA_G_NEW = 0x0080_0000, 0x0081_0000
VA_G = VA_BASE + 0x28 * PAGE
PA_NG, PA_NG_NEW = 0x0090_0000, 0x0091_0000
VA_NG = VA_BASE + 0x2a * PAGE

# ---- superpages: L1 indices 0x1002..0x1006, 4 entries + one eviction ------
PA_SUPER = 0x4000_0000
PA_SUPER_NEW = 0x6000_0000
SUPER_OFF = {k: (k - 1) * 0x1000 for k in range(1, 6)}
# The L1 index is VA[41:29]; VA_BASE already supplies 0x1000, so the k-th
# superpage sits at VA_BASE + k * 512 MiB (L1 indices 0x1001..0x1005).
SUPER_L1 = {k: 0x1000 + k for k in range(1, 6)}
VA_SUPER = {k: VA_BASE + k * 0x2000_0000 + SUPER_OFF[k] for k in range(1, 6)}

# ---- magics ----------------------------------------------------------------
M_P = {k: 0xAAAA_0000_0000_0000 + k for k in range(1, 10)}
M_P_NEW = {k: 0xBBBB_0000_0000_0000 + k for k in range(1, 10)}
M_SUPER = {k: 0x5100_0000_0000_0000 + k for k in range(1, 6)}
M_SUPER2_NEW = 0x5200_0000_0000_0002
M_SUPER1_NEW = 0x5200_0000_0000_0001
M_OR = 0x0BAD_0000_0000_0A0D
M_PD = 0x0BAD_0000_0000_0D0D
M_PD_NEW = 0x0BAD_0000_0000_0D0E
M_G = 0x6700_0000_0000_0001
M_G_NEW = 0x6700_0000_0000_0011
M_NG = 0x6E00_0000_0000_0002
M_NG_NEW = 0x6E00_0000_0000_0012
OR_STORE_VAL = 0xDEAD_BEEF_0BAD_F00D
PX_MARK = 0x7701
PI_MARK_OLD = 0x7101
PI_MARK_NEW = 0x7102
OR_STUB_MARK = 0x0F0F


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


# ---- page tables at load time ---------------------------------------------
L1 = {0x1000: pte(pa=PA_L2)}
for k in range(1, 6):
    L1[SUPER_L1[k]] = pte(pa=PA_SUPER, sp=1)

L2 = {
    0: pte(pa=PA_L2),                # self-map of the L2 table itself
    2: pte(pa=PA_L1),                # self-map of the L1 table (PA 0)
    0x20: pte(pa=PA_OR),
    0x22: pte(pa=PA_PX),
    0x24: pte(pa=PA_PI),
    0x26: pte(pa=PA_PD),
    0x28: pte(pa=PA_G, g=1),
    0x2a: pte(pa=PA_NG),
}
for k in range(1, 10):
    L2[P_INDEX[k]] = pte(pa=PA_P[k])

# ---- PTE words written at run time ----------------------------------------
PTE_P = {k: pte(pa=PA_P[k]) for k in range(1, 10)}
PTE_P_NEW = {k: pte(pa=PA_P_NEW[k]) for k in range(1, 10)}
PTE_L1_SUPER = {k: pte(pa=PA_SUPER, sp=1) for k in range(1, 6)}
PTE_L1_SUPER2_NEW = pte(pa=PA_SUPER_NEW, sp=1)
PTE_L1_SUPER1_NEW = pte(pa=PA_SUPER_NEW, sp=1)
PTE_OR = pte(pa=PA_OR)
PTE_PX = pte(pa=PA_PX)
PTE_PI = pte(pa=PA_PI)
PTE_PI_NEW = pte(pa=PA_PI_NEW)
PTE_PD = pte(pa=PA_PD)
PTE_PD_NEW = pte(pa=PA_PD_NEW)
PTE_G = pte(pa=PA_G, g=1)
PTE_G_NEW = pte(pa=PA_G_NEW, g=1)
PTE_G_A1 = pte(pa=PA_G_NEW, g=1, a=1)
PTE_NG = pte(pa=PA_NG)
PTE_NG_NEW = pte(pa=PA_NG_NEW)
PTE_NG_A1 = pte(pa=PA_NG_NEW, a=1)

# ---- PTE physical addresses (for the checker's event rules) ----------------
PTE_PA = {k: PA_L2 + P_INDEX[k] * 8 for k in range(1, 10)}
PTE_PA_SELF_L2 = PA_L2 + 0 * 8
PTE_PA_SELF_L1 = PA_L2 + 2 * 8
PTE_PA_OR = PA_L2 + 0x20 * 8
PTE_PA_PX = PA_L2 + 0x22 * 8
PTE_PA_PI = PA_L2 + 0x24 * 8
PTE_PA_PD = PA_L2 + 0x26 * 8
PTE_PA_G = PA_L2 + 0x28 * 8
PTE_PA_NG = PA_L2 + 0x2a * 8
PTE_PA_SUPER = {k: PA_L1 + SUPER_L1[k] * 8 for k in range(1, 6)}

# ---- expected PTE values after the probe's operations ----------------------
OR_PTE_A1D1 = pte(pa=PA_OR, a=1, d=1)
OR_PTE_A1D0 = pte(pa=PA_OR, a=1, d=0)
PX_PTE_A1D0 = pte(pa=PA_PX, a=1, d=0)
PX_PTE_A1D1 = pte(pa=PA_PX, a=1, d=1)


def _table(name, base, entries):
    out = ['.section %s, "a"' % name]
    for idx in sorted(entries):
        out.append(".org 0x%x" % (idx * 8))
        out.append(".dd.o64 0x%016x        @@ [%d]" % (entries[idx], idx))
    return out


def emit_inc():
    out = []
    out.append("@@ ptw_tlb_tables.inc -- generated by tests/arch/ptw/gen_ptw_tlb_tables.py")
    out.append("@@ Do not edit: geometry and expected values come from there.")
    out.append("")
    equ = [("VA_L2SELF", VA_L2SELF), ("VA_L1SELF", VA_L1SELF),
           ("VA_OR", VA_OR), ("VA_PX", VA_PX), ("VA_PI", VA_PI), ("VA_PD", VA_PD),
           ("PA_OR", PA_OR), ("PA_PI", PA_PI), ("PA_PD", PA_PD)]
    for k in range(1, 10):
        equ += [("VA_P%d" % k, VA_P[k]), ("M_P%d" % k, M_P[k]),
                ("PTE_P%d_NEW" % k, PTE_P_NEW[k]),
                ("OFF_L2_P%d" % k, P_INDEX[k] * 8)]
    for k in range(1, 6):
        equ += [("VA_S%d" % k, VA_SUPER[k]), ("M_S%d" % k, M_SUPER[k]),
                ("OFF_L1_S%d" % k, SUPER_L1[k] * 8)]
    equ += [("PTE_P1", PTE_P[1]), ("PTE_P2", PTE_P[2]),
            ("PTE_P8", PTE_P[8]), ("PTE_P9", PTE_P[9]),
            ("PTE_S1_NEW", PTE_L1_SUPER1_NEW), ("PTE_S2_NEW", PTE_L1_SUPER2_NEW),
            ("PTE_OR", PTE_OR), ("PTE_PX", PTE_PX),
            ("PTE_PI", PTE_PI), ("PTE_PI_NEW", PTE_PI_NEW),
            ("PTE_PD", PTE_PD), ("PTE_PD_NEW", PTE_PD_NEW),
            ("M_S2_NEW", M_SUPER2_NEW), ("M_S1_NEW", M_SUPER1_NEW),
            ("M_OR", M_OR), ("M_PD", M_PD), ("M_PD_NEW", M_PD_NEW),
            ("OR_STORE_VAL", OR_STORE_VAL), ("PX_MARK", PX_MARK),
            ("PI_MARK_OLD", PI_MARK_OLD), ("PI_MARK_NEW", PI_MARK_NEW),
            ("OR_STUB_MARK", OR_STUB_MARK),
            ("OFF_L2_SELF_L1", 2 * 8), ("OFF_L2_OR", 0x20 * 8),
            ("OFF_L2_PX", 0x22 * 8), ("OFF_L2_PI", 0x24 * 8), ("OFF_L2_PD", 0x26 * 8),
            ("OFF_L2_G", 0x28 * 8), ("OFF_L2_NG", 0x2a * 8),
            ("VA_G", VA_G), ("VA_NG", VA_NG),
            ("PTE_G", PTE_G), ("PTE_G_NEW", PTE_G_NEW), ("PTE_NG", PTE_NG),
            ("PTE_NG_NEW", PTE_NG_NEW), ("M_G", M_G), ("M_G_NEW", M_G_NEW),
            ("M_NG", M_NG), ("M_NG_NEW", M_NG_NEW)]
    for name, value in equ:
        out.append(".equ %-16s, 0x%016x" % (name, value))
    out.append("")
    out += _table(".pt_l1", PA_L1, L1)
    out += _table(".pt_l2", PA_L2, L2)
    out.append("")
    # data pages: one magic per page at the page's base
    out.append('.section .pages, "aw"')
    for k in range(1, 10):
        out.append(".org 0x%x" % (PA_P[k] - 0x100000))
        out.append(".dd.o64 0x%016x        @@ P%d" % (M_P[k], k))
    for k in range(1, 10):
        out.append(".org 0x%x" % (PA_P_NEW[k] - 0x100000))
        out.append(".dd.o64 0x%016x        @@ P%d new" % (M_P_NEW[k], k))
    out.append("")
    out.append('.section .super, "aw"')
    for k in range(1, 6):
        out.append(".org 0x%x" % (SUPER_OFF[k]))
        out.append(".dd.o64 0x%016x        @@ S%d" % (M_SUPER[k], k))
    out.append("")
    out.append('.section .super_new, "aw"')
    out.append(".org 0x0")
    out.append(".dd.o64 0x%016x        @@ S1 new" % M_SUPER1_NEW)
    out.append(".org 0x1000")
    out.append(".dd.o64 0x%016x        @@ S2 new" % M_SUPER2_NEW)
    out.append("")
    out.append('.section .ordata, "aw"')
    out.append(".org 0x0")
    out.append("tlb_or_stub:")
    out.append("\tset.rd\trd7, OR_STUB_MARK")
    out.append("\tjump\t[rb12, rd0, 0]")
    out.append(".org 0x800")
    out.append(".dd.o64 0x%016x        @@ OR data" % M_OR)
    out.append(".org 0x808")
    out.append(".dd.o64 0")
    out.append("")
    out.append('.section .px, "aw"')
    out.append("tlb_px_stub:")
    out.append("\tset.rd\trd7, PX_MARK")
    out.append("\tjump\t[rb12, rd0, 0]")
    out.append("")
    out.append('.section .pi, "aw"')
    out.append("tlb_pi_stub_old:")
    out.append("\tset.rd\trd7, PI_MARK_OLD")
    out.append("\tjump\t[rb12, rd0, 0]")
    out.append("")
    out.append('.section .pi_new, "aw"')
    out.append("tlb_pi_stub_new:")
    out.append("\tset.rd\trd7, PI_MARK_NEW")
    out.append("\tjump\t[rb12, rd0, 0]")
    out.append("")
    out.append('.section .pd, "aw"')
    out.append(".dd.o64 0x%016x        @@ PD data" % M_PD)
    out.append("")
    out.append('.section .pd_new, "aw"')
    out.append(".dd.o64 0x%016x        @@ PD new data" % M_PD_NEW)
    out.append("")
    out.append('.section .gdata, "aw"')
    out.append(".org 0x0")
    out.append(".dd.o64 0x%016x        @@ G = 1 page" % M_G)
    out.append(".org 0x10000")
    out.append(".dd.o64 0x%016x        @@ G = 1 new target" % M_G_NEW)
    out.append("")
    out.append('.section .ngdata, "aw"')
    out.append(".org 0x0")
    out.append(".dd.o64 0x%016x        @@ G = 0 page" % M_NG)
    out.append(".org 0x10000")
    out.append(".dd.o64 0x%016x        @@ G = 0 new target" % M_NG_NEW)
    out.append("")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="page tables for ptw_tlb.S")
    ap.add_argument("--emit", choices=["inc"], default="inc")
    args = ap.parse_args()
    print(emit_inc(), end="")


if __name__ == "__main__":
    main()
