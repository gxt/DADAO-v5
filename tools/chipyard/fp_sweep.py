#!/usr/bin/env python3
"""m12-chipyard-011 sweep: the FP infrastructure on the wuming core.

The expected values come from `fp_ref` (the independent model derived from
spec/SimRISC-07 and the IEEE definitions), *not* from QEMU: every case carries
its own expected architectural state, and the same image is also run on QEMU as
a cross-check.

Groups (one image each, so a failure is localised):

``classify``
    ``ftcls``/``focls`` over the ten classes of spec/SimRISC-07 §5 for ft and
    fo (both signs, the smallest/largest normal and subnormal, quiet and
    signalling NaN), the single-register form, block forms of 2/3/4/8 elements
    and the two range boundaries (start 62 with count 2).
``sign``
    ``ftsgnj``/``ftsgnn``/``fosgnj``/``fosgnn``: ``hd = rf0`` (abs / -abs),
    ``hc == hd`` (copy / negate), random bit patterns and the special values.
``rfmem``
    the rf forms of the memory family (``ld.t``/``st.t``/``ld.o``/``st.o``,
    ``ldm.t``/``stm.t``, ``ldm.o``/``stm.o``), including ``rf0`` as a load
    destination (FCSR write mask).
``fcsr``
    ``set.w rf`` (only the addressed wyde moves), ``set.w rf0`` (wp2 = rounding
    mode, wp0 = flags, wp1/wp3 write-invalid), ``rd2rf``/``rf2rd`` (with ``rf0``
    on either side) and the ``cs.*`` rf forms.
``faults``
    the legality rules the vectors cannot express through results: ``ftcls``
    ``dst_rd0``/``mreg_zero``/range overflow, ``dst_rf0`` for the sign forms and
    for ``cs.*`` rf.

Usage: ``fp_sweep.py emit OUTDIR`` (writes the ELFs, raw kernels, expected
bytes, the per-case manifest and the fault lists) or ``list``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "chipyard"))
sys.path.insert(0, str(ROOT / "tools" / "infra"))

import fp_ref as F  # noqa: E402
import inst_sweep as sweep  # noqa: E402

ENTRY = sweep.ENTRY
CODE = ENTRY + 0x1000
BUF = ENTRY + 0x40000
EXITBLOCK = ENTRY + 0x50000
DATA = ENTRY + 0x2000          # scratch data for the rf memory forms
IMAGE_LIMIT = BUF - ENTRY

WR_PTR = sweep.WR_PTR          # rb30
TMP_RB = sweep.TMP_RB          # rb29
TMP_RD = sweep.TMP_RD          # rd9
TMP2_RD = 15                   # rd15: scratch for the rf read-back
SEMI_RD = sweep.SEMI_RD        # rd16 / rb16
ZERO_RB = sweep.ZERO_RB        # rb27


# ── encoders ──────────────────────────────────────────────────────────────
def enc_ftcls(dst, src, count, fo=False):
    """`ftcls {rdHB:..}, {rfHC:..}` (orri, opc 0x44, ha = 0x00 / 0x08)."""
    return (0x44 << 24) | ((0x08 if fo else 0x00) << 18) | \
        ((dst & 0x3F) << 12) | ((src & 0x3F) << 6) | (count & 0x3F)


def enc_sgn(dst, hc, hd, fo=False, invert=False):
    """`ftsgnj/ftsgnn/fosgnj/fosgnn rfHB, rfHC, rfHD` (orrr, opc 0x44)."""
    ha = {(False, False): 0x17, (False, True): 0x16,
          (True, False): 0x1F, (True, True): 0x1E}[(fo, invert)]
    return (0x44 << 24) | (ha << 18) | ((dst & 0x3F) << 12) | \
        ((hc & 0x3F) << 6) | (hd & 0x3F)


def enc_mem_rf(load, width, rf, rb, off=0):
    """`ld.<w>`/`st.<w>` in the rf bank (rrii: rfHA, rbHB, imms12)."""
    opc = {(True, 4): 0x16, (False, 4): 0x17,
           (True, 8): 0x26, (False, 8): 0x27}[(load, width)]
    return (opc << 24) | ((rf & 0x3F) << 18) | ((rb & 0x3F) << 12) | \
        (off & 0xFFF)


def enc_mem_rf_multi(load, width, rf, rb, rd, count):
    """`ldm.<w>`/`stm.<w>` in the rf bank (rrri: rfHA, rbHB, rdHC, immu6)."""
    opc = {(True, 4): 0x2E, (False, 4): 0x2F,
           (True, 8): 0x3E, (False, 8): 0x3F}[(load, width)]
    return (opc << 24) | ((rf & 0x3F) << 18) | ((rb & 0x3F) << 12) | \
        ((rd & 0x3F) << 6) | (count & 0x3F)


def enc_set_w_rf(rf, wp, imm16):
    return (0x4F << 24) | ((rf & 0x3F) << 18) | ((wp & 3) << 16) | (imm16 & 0xFFFF)


def enc_rd2rf(dst, src, count):
    return (0x40 << 24) | (0x3D << 18) | ((dst & 0x3F) << 12) | \
        ((src & 0x3F) << 6) | (count & 0x3F)


def enc_rf2rd(dst, src, count):
    return (0x40 << 24) | (0x3E << 18) | ((dst & 0x3F) << 12) | \
        ((src & 0x3F) << 6) | (count & 0x3F)


def enc_cs_rf(opc, pred, dst, then_src, else_src):
    return (opc << 24) | ((pred & 0x3F) << 18) | ((dst & 0x3F) << 12) | \
        ((then_src & 0x3F) << 6) | (else_src & 0x3F)


def enc_ld_o_rd(dst, rb, off=0):
    return (0x20 << 24) | ((dst & 0x3F) << 18) | ((rb & 0x3F) << 12) | \
        (off & 0xFFF)


def enc_st_o_rd(src, rb, off=0):
    return (0x21 << 24) | ((src & 0x3F) << 18) | ((rb & 0x3F) << 12) | \
        (off & 0xFFF)


def enc_st_t_rd(src, rb, off=0):
    return (0x1A << 24) | ((src & 0x3F) << 18) | ((rb & 0x3F) << 12) | \
        (off & 0xFFF)


# ── program fragments ─────────────────────────────────────────────────────
def load_rf(num, value):
    """Load a full 64-bit constant into rf `num` with four `set.w` (wp3..wp0)."""
    words = []
    for wp in (3, 2, 1, 0):
        words.append(enc_set_w_rf(num, wp, (value >> (16 * wp)) & 0xFFFF))
    return words


def store_word(addr, value):
    """Seed a 64-bit memory word through rd (no rf involvement)."""
    words = sweep.load_rb(TMP_RB, addr)
    words += sweep.load_rd(TMP_RD, value & ((1 << 64) - 1))
    words.append(enc_st_o_rd(TMP_RD, TMP_RB, 0))
    return words


def dump_rd(num):
    return [enc_st_o_rd(num, WR_PTR, 0), sweep.enc_add_si_rb(WR_PTR, 8)]


def dump_rf(num):
    """Read an rf register back through `rf2rd` into the scratch rd."""
    return ([enc_rf2rd(TMP2_RD, num, 1)] + dump_rd(TMP2_RD))


def dump_mem_word(addr):
    words = sweep.load_rb(TMP_RB, addr)
    words.append(enc_ld_o_rd(TMP_RD, TMP_RB, 0))
    return words + dump_rd(TMP_RD)


def asm_print_buffer(nbytes):
    words = sweep.load_rb(SEMI_RD, BUF)
    words.append(sweep.enc_set_zw_rd(SEMI_RD, 0, sweep.SYS_WRITEC))
    for _ in range(nbytes):
        words.append(sweep.enc_trap(0, sweep.SEMIHOST_TAG | sweep.SYS_WRITEC))
        words.append(sweep.enc_add_si_rb(SEMI_RD, 1))
    return words


def asm_sys_exit(code):
    words = sweep.load_rb(SEMI_RD, EXITBLOCK)
    words += sweep.load_rd(TMP2_RD, sweep.ADP_STOPPED_APPLICATION_EXIT)
    words.append(enc_st_o_rd(TMP2_RD, SEMI_RD, 0))
    words += sweep.load_rd(TMP2_RD, code)
    words.append(enc_st_o_rd(TMP2_RD, SEMI_RD, 8))
    words.append(sweep.enc_set_zw_rd(SEMI_RD, 0, sweep.SYS_EXIT))
    words.append(sweep.enc_trap(0, sweep.SEMIHOST_TAG | sweep.SYS_EXIT))
    return words


def asm_prelude():
    return sweep.asm_prelude()


# ── the cases ─────────────────────────────────────────────────────────────
FT_PATTERNS = [
    ("snana", 0x7F800001),          # signalling NaN, payload 1
    ("snanb", 0x7FBFFFFF),          # signalling NaN, payload all ones
    ("qnan", 0x7FC00000),           # quiet NaN
    ("qnanp", 0x7FE00001),          # quiet NaN with payload
    ("pinf", 0x7F800000),
    ("ninf", 0xFF800000),
    ("pnorm", 0x3F800000),
    ("nnorm", 0xBF800000),
    ("pnormmax", 0x7F7FFFFF),       # largest normal
    ("pnormmin", 0x00800000),       # smallest normal
    ("nsubmax", 0x807FFFFF),        # largest negative subnormal
    ("psubmin", 0x00000001),        # smallest positive subnormal
    ("nsubmin", 0x80000001),
    ("pzero", 0x00000000),
    ("nzero", 0x80000000),
]

FO_PATTERNS = [
    ("snana", 0x7FF0000000000001),
    ("snanb", 0x7FF7FFFFFFFFFFFF),
    ("qnan", 0x7FF8000000000000),
    ("qnanp", 0x7FFC000000000001),
    ("pinf", 0x7FF0000000000000),
    ("ninf", 0xFFF0000000000000),
    ("pnorm", 0x3FF0000000000000),
    ("nnorm", 0xBFF0000000000000),
    ("pnormmax", 0x7FEFFFFFFFFFFFFF),
    ("pnormmin", 0x0010000000000000),
    ("nsubmax", 0x800FFFFFFFFFFFFF),
    ("psubmin", 0x0000000000000001),
    ("nsubmin", 0x8000000000000001),
    ("pzero", 0x0000000000000000),
    ("nzero", 0x8000000000000000),
]


def cases_classify():
    out = []
    for is_fo, patterns, name in ((False, FT_PATTERNS, "ft"),
                                  (True, FO_PATTERNS, "fo")):
        ew, sw = (F.FO if is_fo else F.FT)
        for label, pattern in patterns:
            bits = F.classify_fn(ew, sw, pattern)
            out.append({
                "name": f"cls_{name}_{label}",
                "setup": load_rf(1, pattern),
                "exec": [enc_ftcls(1, 1, 1, fo=is_fo)],
                "dumps": [("rd", 1)],
                "expect": [bits],
            })
    # block forms: 2, 3, 4 and 8 elements, mixed classes
    block = [0x7F800000, 0xFF800000, 0x00000000, 0x80000000,
             0x00000001, 0x80000001, 0x00800000, 0x7F7FFFFF]
    for count in (2, 3, 4, 8):
        setup = []
        expect = []
        for i in range(count):
            setup += load_rf(1 + i, block[i])
            expect.append(F.classify_fn(F.FT[0], F.FT[1], block[i]))
        out.append({
            "name": f"cls_ft_block{count}",
            "setup": setup,
            "exec": [enc_ftcls(1, 1, count)],
            "dumps": [("rd", 1 + i) for i in range(count)],
            "expect": expect,
        })
    # the two range boundaries: start 62 + count 2 (exactly 64) and dst via rd62
    pats = [0x7FF0000000000001, 0x0000000000000000]
    out.append({
        "name": "cls_fo_range_boundary",
        "setup": load_rf(62, pats[0]) + load_rf(63, pats[1]),
        "exec": [enc_ftcls(62, 62, 2, fo=True)],
        "dumps": [("rd", 62), ("rd", 63)],
        "expect": [F.classify_fn(F.FO[0], F.FO[1], pats[0]),
                   F.classify_fn(F.FO[0], F.FO[1], pats[1])],
    })
    # ft reads only the low 32 bits of the rf register
    junk = 0xDEADBEEF7F800000
    out.append({
        "name": "cls_ft_ignores_high_half",
        "setup": load_rf(1, junk),
        "exec": [enc_ftcls(1, 1, 1)],
        "dumps": [("rd", 1)],
        "expect": [F.classify_fn(F.FT[0], F.FT[1], 0x7F800000)],
    })
    return out


def cases_sign():
    out = []
    base = [0x3F800000, 0xBF800000, 0x7F800001, 0x7FC00000, 0x00000000,
            0x80000000, 0x00000001, 0x7F7FFFFF]
    fo_base = [0x3FF0000000000000, 0xBFF0000000000000, 0x7FF0000000000001,
               0x7FF8000000000000, 0x8000000000000000, 0x0010000000000000]
    for invert in (False, True):
        for i, hc in enumerate(base):
            hd = base[(i + 3) % len(base)]
            out.append({
                "name": f"sign_ft_{'nn' if invert else 'nj'}_{i}",
                "setup": load_rf(1, hc) + load_rf(2, hd),
                "exec": [enc_sgn(3, 1, 2, fo=False, invert=invert)],
                "dumps": [("rf", 3)],
                "expect": [F.sign_inject(hc, hd, 31, invert)],
            })
        for i, hc in enumerate(fo_base):
            hd = fo_base[(i + 2) % len(fo_base)]
            out.append({
                "name": f"sign_fo_{'nn' if invert else 'nj'}_{i}",
                "setup": load_rf(1, hc) + load_rf(2, hd),
                "exec": [enc_sgn(3, 1, 2, fo=True, invert=invert)],
                "dumps": [("rf", 3)],
                "expect": [F.sign_inject(hc, hd, 63, invert)],
            })
    # hd = rf0: abs / -abs (the FCSR read has sign 0)
    fcsr = 0x7FF800007FC00000
    for invert in (False, True):
        out.append({
            "name": f"sign_ft_abs_{'neg' if invert else 'pos'}",
            "setup": load_rf(1, 0xBF812345),
            "exec": [enc_sgn(3, 1, 0, fo=False, invert=invert)],
            "dumps": [("rf", 3)],
            "expect": [F.sign_inject(0xBF812345, fcsr, 31, invert)],
        })
    # hc == hd: copy / negate
    for invert in (False, True):
        out.append({
            "name": f"sign_fo_self_{'neg' if invert else 'copy'}",
            "setup": load_rf(1, 0xC0123456789ABCDE),
            "exec": [enc_sgn(3, 1, 1, fo=True, invert=invert)],
            "dumps": [("rf", 3)],
            "expect": [F.sign_inject(0xC0123456789ABCDE,
                                     0xC0123456789ABCDE, 63, invert)],
        })
    return out


def cases_rfmem():
    out = []
    # st.o rf / ld.o rf round trip, including negative patterns.  DATA is
    # re-seeded every time so a case never depends on the previous one.
    for i, pattern in enumerate((0x7FF800007FC00000, 0x8000000000000001,
                                 0x0123456789ABCDEF)):
        out.append({
            "name": f"rfmem_st_ld_o_{i}",
            "setup": store_word(DATA, 0) + load_rf(2, pattern) +
                     sweep.load_rb(4, DATA),
            "exec": [enc_mem_rf(False, 8, 2, 4, 0),
                     enc_mem_rf(True, 8, 3, 4, 0)],
            "dumps": [("mem", DATA), ("rf", 3)],
            "expect": [pattern, pattern],
        })
    # st.t rf writes four bytes (big-endian at the address) and ld.t rf
    # sign-extends the tetra into the 64-bit register
    out.append({
        "name": "rfmem_st_t_ld_t",
        "setup": store_word(DATA, 0) + load_rf(2, 0x1122334480000001) +
                 sweep.load_rb(4, DATA),
        "exec": [enc_mem_rf(False, 4, 2, 4, 0),
                 enc_mem_rf(True, 4, 3, 4, 0)],
        "dumps": [("mem", DATA), ("rf", 3)],
        "expect": [0x8000000100000000, 0xFFFFFFFF80000001],
    })
    # ldm.o / stm.o over three registers
    vals = [0x7FF0000000000001, 0xFFF0000000000001, 0x0000000000000001]
    out.append({
        "name": "rfmem_stm_ldm_o",
        "setup": sum((load_rf(1 + i, v) for i, v in enumerate(vals)), []) +
                 sweep.load_rb(4, DATA),
        "exec": [enc_mem_rf_multi(False, 8, 1, 4, 0, 3),
                 enc_mem_rf_multi(True, 8, 5, 4, 0, 3)],
        "dumps": [("mem", DATA), ("mem", DATA + 8), ("mem", DATA + 16),
                  ("rf", 5), ("rf", 6), ("rf", 7)],
        "expect": vals + vals,
    })
    # ldm.t/stm.t: four bytes per element at base + 4*i
    tvals = [0x3F800000, 0xBF800000, 0x7FC00000]
    out.append({
        "name": "rfmem_stm_ldm_t",
        "setup": store_word(DATA + 8, 0) +
                 sum((load_rf(1 + i, v) for i, v in enumerate(tvals)), []) +
                 sweep.load_rb(4, DATA),
        "exec": [enc_mem_rf_multi(False, 4, 1, 4, 0, 3),
                 enc_mem_rf_multi(True, 4, 5, 4, 0, 3)],
        "dumps": [("mem", DATA), ("mem", DATA + 8), ("rf", 5), ("rf", 6),
                  ("rf", 7)],
        "expect": [0x3F800000BF800000, 0x7FC0000000000000,
                   0x000000003F800000, 0xFFFFFFFFBF800000,
                   0x000000007FC00000],
    })
    # rf0 as a load destination: the FCSR write mask keeps the quiet-NaN bits
    # and the SBZ columns, and takes [33:32] + [4:0] from the loaded word.
    out.append({
        "name": "rfmem_ld_o_rf0_mask",
        "setup": store_word(DATA, 0xFFFFFFFFFFFFFFFF) + sweep.load_rb(4, DATA),
        "exec": [enc_mem_rf(True, 8, 0, 4, 0)],
        "dumps": [("rf", 0)],
        "expect": [0x7FF800037FC0001F],
    })
    return out


def cases_rf0ldt():
    """`ld.t rf0`: the tetra carries the mode/flags, `[63:32]` stays and the
    read-only qNaN(ft) field is preserved (spec/SimRISC-00 §2.3.1).

    QEMU writes the low 32 bits of `rf0` wholesale here (see its
    `store_rf_tetra_dst`, which documents that it "intentionally overrides the
    read-only qNaN(ft) field"), so this group is checked against the model but
    kept out of the QEMU cross-check.
    """
    return [{
        "name": "rf0ldt_ld_t_rf0_mask",
        "setup": store_word(DATA, 0xFFFFFFFFFFFFFFFF) + sweep.load_rb(4, DATA),
        "exec": [enc_mem_rf(True, 4, 0, 4, 0)],
        "dumps": [("rf", 0)],
        "expect": [0x7FF800037FC0001F],
    }]


def fcsr_clear():
    """Reset mode and flags through `set.w rf0` so each case starts from the
    architectural reset value (the cases run one after another in one image)."""
    return [enc_set_w_rf(0, 2, 0), enc_set_w_rf(0, 0, 0)]


def cases_fcsr():
    out = []
    fcsr_reset = 0x7FF800007FC00000
    out.append({
        "name": "fcsr_reset_value",
        "setup": [],
        "exec": [],
        "dumps": [("rf", 0)],
        "expect": [fcsr_reset],
    })
    # each of the five classes through a software write (set.w wp0) ...
    for bit in range(5):
        out.append({
            "name": f"fcsr_set_flag_bit{bit}",
            "setup": [],
            "exec": fcsr_clear() + [enc_set_w_rf(0, 0, 1 << bit)],
            "dumps": [("rf", 0)],
            "expect": [fcsr_reset | (1 << bit)],
        })
    # ... and all five together, then the rounding mode through wp2
    out.append({
        "name": "fcsr_set_all_flags",
        "setup": [],
        "exec": fcsr_clear() + [enc_set_w_rf(0, 0, 0x1F)],
        "dumps": [("rf", 0)],
        "expect": [fcsr_reset | 0x1F],
    })
    for mode in range(4):
        out.append({
            "name": f"fcsr_set_mode{mode}",
            "setup": [],
            "exec": fcsr_clear() + [enc_set_w_rf(0, 2, mode)],
            "dumps": [("rf", 0)],
            "expect": [(fcsr_reset & ~0x300000000) | (mode << 32)],
        })
    # wp1/wp3 are write-invalid on rf0
    for wp in (1, 3):
        out.append({
            "name": f"fcsr_wp{wp}_write_invalid",
            "setup": [],
            "exec": fcsr_clear() + [enc_set_w_rf(0, wp, 0xFFFF)],
            "dumps": [("rf", 0)],
            "expect": [fcsr_reset],
        })
    # set.w on a normal rf register replaces only the addressed wyde
    out.append({
        "name": "fcsr_set_w_partial",
        "setup": load_rf(3, 0x0123456789ABCDEF),
        "exec": [enc_set_w_rf(3, 1, 0xAAAA)],
        "dumps": [("rf", 3)],
        "expect": [0x01234567AAAACDEF],
    })
    # rd2rf / rf2rd, with rf0 on both sides
    out.append({
        "name": "fcsr_rd2rf_rf2rd",
        "setup": sweep.load_rd(2, 0x1122334455667788) +
                 sweep.load_rd(3, 0x99AABBCCDDEEFF00),
        "exec": [enc_rd2rf(4, 2, 2), enc_rf2rd(6, 4, 2)],
        "dumps": [("rd", 6), ("rd", 7)],
        "expect": [0x1122334455667788, 0x99AABBCCDDEEFF00],
    })
    out.append({
        "name": "fcsr_rd2rf_rf0",
        "setup": sweep.load_rd(2, 0x00000003FFFFFFFF),
        "exec": fcsr_clear() + [enc_rd2rf(0, 2, 1)],
        "dumps": [("rf", 0)],
        "expect": [fcsr_reset | (3 << 32) | 0x1F],
    })
    # cs.* rf: predicate from rd, values and destination in rf
    for opc, pred, taken in ((0x61, 0x8000000000000000, True),   # cs.n
                             (0x63, 0x0000000000000000, True),   # cs.z
                             (0x65, 0x0000000000000007, True),   # cs.p
                             (0x63, 0x0000000000000007, False)):  # cs.z, not zero
        out.append({
            "name": f"fcsr_cs_rf_{opc:x}_{'t' if taken else 'f'}",
            "setup": sweep.load_rd(1, pred) +
                     load_rf(2, 0xAAAAAAAAAAAAAAAA) +
                     load_rf(3, 0x5555555555555555),
            "exec": [enc_cs_rf(opc, 1, 4, 2, 3)],
            "dumps": [("rf", 4)],
            "expect": [0xAAAAAAAAAAAAAAAA if taken else 0x5555555555555555],
        })
    return out


def cases_faults():
    return [
        {"name": "fault_ftcls_dst_rd0", "word": enc_ftcls(0, 1, 1),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_focls_dst_rd0", "word": enc_ftcls(0, 1, 1, fo=True),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftcls_mreg_zero", "word": enc_ftcls(1, 1, 0),
         "fault": "ILLI", "setup": []},
        {"name": "fault_ftcls_dst_range", "word": enc_ftcls(60, 1, 8),
         "fault": "ILLI", "setup": []},
        {"name": "fault_ftcls_src_range", "word": enc_ftcls(1, 58, 8),
         "fault": "ILLI", "setup": []},
        {"name": "fault_ftsgnj_dst_rf0", "word": enc_sgn(0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_fosgnn_dst_rf0", "word": enc_sgn(0, 1, 2, fo=True,
                                                         invert=True),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_cs_n_rf_dst_rf0",
         "word": enc_cs_rf(0x61, 1, 0, 2, 3), "fault": "ILLI",
         "setup": load_rf(2, 0x1) + load_rf(3, 0x2)},
    ]


GROUPS = {
    "classify": cases_classify,
    "sign": cases_sign,
    "rfmem": cases_rfmem,
    "fcsr": cases_fcsr,
    "rf0ldt": cases_rf0ldt,
}

# Groups whose bytes are also compared against QEMU.  `rf0ldt` is excluded: the
# ld.t-rf0 case asserts the read-only qNaN field, which QEMU deliberately
# overrides (documented divergence, see `cases_rf0ldt`).
QEMU_GROUPS = ("classify", "sign", "rfmem", "fcsr")


# ── program builders ──────────────────────────────────────────────────────
def build_group(cases):
    words = [(0x71 << 24) | ((CODE - ENTRY) >> 2)]     # jump to CODE
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    expected = bytearray()
    manifest = []
    for case in cases:
        words += case["setup"]
        words += case["exec"]
        offset = len(expected)
        for kind, num in case["dumps"]:
            if kind == "rd":
                words += dump_rd(num)
            elif kind == "rf":
                words += dump_rf(num)
            else:  # memory
                words += dump_mem_word(num)
        for value in case["expect"]:
            expected += value.to_bytes(8, "big")
        manifest.append({"name": case["name"], "offset": offset,
                         "bytes": 8 * len(case["expect"]),
                         "dumps": [f"{k}{n}" if k != "mem" else f"mem:0x{n:x}"
                                   for k, n in case["dumps"]]})
    nbytes = len(expected)
    if len(words) * 4 > IMAGE_LIMIT:
        raise SystemExit(f"fp_sweep: image too large ({len(words) * 4} B)")
    words += asm_print_buffer(nbytes)
    words += asm_sys_exit(0)
    return words, bytes(expected), manifest, nbytes


def build_fault(case):
    # Fault images start at ENTRY (no trampoline): the whole program plus the
    # PRE/POST marker block has to fit below the marker offset.
    words = asm_prelude()
    words += sweep.asm_write0(ENTRY + 0x400)
    words += case["setup"]
    words.append(case["word"])
    words += sweep.asm_write0(ENTRY + 0x408)
    words += asm_sys_exit(0)
    if len(words) * 4 > 0x400:
        raise SystemExit("fp_sweep: fault program does not fit below the marker")
    words += [0] * ((0x400 - len(words) * 4) // 4)
    words += [0x5052450A, 0x00000000, 0x504F5354, 0x0A000000]  # "PRE\n\0POST\n\0"
    return words


FAULT_BITS = {"CFXMEM": 1, "CFXREG": 2, "ILLI": 8, "UNDI": 9,
              "RASOF": 10, "RASUF": 11, "MALIGN": 12, "IALIGN": 13}


def cmd_list(_args):
    total = 0
    for name, fn in GROUPS.items():
        cases = fn()
        total += len(cases)
        print(f"{name}: {len(cases)} cases")
        for case in cases:
            print(f"  {case['name']}")
    faults = cases_faults()
    print(f"faults: {len(faults)} cases")
    for case in faults:
        print(f"  {case['name']}")
    print(f"total semantic={total} fault={len(faults)}")
    return 0


def cmd_emit(args):
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tb = sweep.toolchain_bin(args.toolchain_bin)
    total = 0
    for name, fn in GROUPS.items():
        cases = fn()
        words, expected, manifest, nbytes = build_group(cases)
        elf, raw = sweep.assemble(words, outdir, name, tb)
        (outdir / f"{name}_expect.bin").write_bytes(expected)
        (outdir / f"{name}.json").write_text(json.dumps(
            {"bytes": nbytes, "cases": manifest}, indent=1) + "\n")
        print(f"{name}: {len(cases)} cases, {nbytes} B expected")
        total += len(cases)
    faults = []
    for case in cases_faults():
        words = build_fault(case)
        elf, raw = sweep.assemble(words, outdir, case["name"], tb)
        faults.append({"key": case["name"], "elf": f"{case['name']}.elf",
                       "raw": f"{case['name']}.raw",
                       # the trace prints the one-hot cause word
                       "cause": 1 << FAULT_BITS[case["fault"]],
                       "fault": case["fault"]})
    (outdir / "faults.json").write_text(json.dumps(faults, indent=1) + "\n")
    print(f"faults: {len(faults)} images")
    print(f"total semantic={total} fault={len(faults)}")
    return 0


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("emit")
    p.add_argument("outdir")
    p.add_argument("--toolchain-bin", default=None)
    p.set_defaults(fn=cmd_emit)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
