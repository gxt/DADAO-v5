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


# ── m12-012: format conversions ───────────────────────────────────────────
# `ha` of the 20 conversion encodings (contracts/opcodes.yaml, opc 0x44).
CVT_HA = {
    "ft2it": 0x30, "ft2io": 0x31, "ft2ut": 0x32, "ft2uo": 0x33,
    "it2ft": 0x34, "io2ft": 0x35, "ut2ft": 0x36, "uo2ft": 0x37,
    "fo2it": 0x38, "fo2io": 0x39, "fo2ut": 0x3A, "fo2uo": 0x3B,
    "it2fo": 0x3C, "io2fo": 0x3D, "ut2fo": 0x3E, "uo2fo": 0x3F,
    "ft2fo": 0x01, "fo2ft": 0x09,
}
# op -> (kind, integer width, signed, out format) of the 8 f2i instructions
F2I_DESC = {
    "ft2it": (F.FT, 32, True), "ft2io": (F.FT, 64, True),
    "ft2ut": (F.FT, 32, False), "ft2uo": (F.FT, 64, False),
    "fo2it": (F.FO, 32, True), "fo2io": (F.FO, 64, True),
    "fo2ut": (F.FO, 32, False), "fo2uo": (F.FO, 64, False),
}
# op -> (integer width, signed, out format) of the 8 i2f instructions
I2F_DESC = {
    "it2ft": (32, True, F.FT), "io2ft": (64, True, F.FT),
    "ut2ft": (32, False, F.FT), "uo2ft": (64, False, F.FT),
    "it2fo": (32, True, F.FO), "io2fo": (64, True, F.FO),
    "ut2fo": (32, False, F.FO), "uo2fo": (64, False, F.FO),
}
FCSR_BASE = 0x7FF800007FC00000


def enc_cvt(mn, dst, src, imm6):
    """A one-register conversion (`orri`, opc 0x44)."""
    return (0x44 << 24) | (CVT_HA[mn] << 18) | ((dst & 0x3F) << 12) | \
        ((src & 0x3F) << 6) | (imm6 & 0x3F)


def enc_cvt_ff(mn, dst, src, count):
    """`ft2ft`/`fo2fo`: the register-window copy form."""
    ha = 0x02 if mn == "ft2ft" else 0x0A
    return (0x44 << 24) | (ha << 18) | ((dst & 0x3F) << 12) | \
        ((src & 0x3F) << 6) | (count & 0x3F)


def _cvt_case(name, setup, exec_words, dumps, expect):
    return {"name": name, "setup": setup, "exec": exec_words,
            "dumps": dumps, "expect": expect}


CVT_MODES = (("rne", 0x01), ("rna", 0x02), ("rtz", 0x04), ("rup", 0x08),
             ("rdn", 0x10), ("dyn", 0x20))


def _cvt_imm6_setup(imm6):
    """Reset the FCSR, and for the dynamic code set `rf0[33:32]` to RTZ so the
    "follows rf0" path is distinguishable from the RNE default."""
    return fcsr_clear() + ([enc_set_w_rf(0, 2, 1)] if imm6 == 0x20 else [])


def fcsr_after(imm6, flags):
    """The `rf0` value a conversion case leaves behind: the reset qNaN bits,
    the mode the case selected (`0x20` = dynamic sets `rf0[33:32]` = RTZ) and
    the accrued flags."""
    return FCSR_BASE | ((1 if imm6 == 0x20 else 0) << 32) | flags


def cases_cvt_f2i_ft():
    """The four ft -> integer conversions, all six directions (spec/SimRISC-07
    §1.1).  2.5f and 2.7f are ties/inexacts that separate every direction."""
    out = []
    for mn in ("ft2it", "ft2io", "ft2ut", "ft2uo"):
        iw, signed = F2I_DESC[mn][1], F2I_DESC[mn][2]
        for label, imm6 in CVT_MODES:
            vals = ("2.5", "2.7", "-2.5", "-2.7") if mn == "ft2it" else ("2.7",)
            for tie in vals:
                x = {"2.5": 0x40200000, "2.7": 0x402CCCCD,
                     "-2.5": 0xC0200000, "-2.7": 0xC02CCCCD}[tie]
                value, flags = F.f2i_exact(F.FT[0], F.FT[1], x, iw, signed,
                                           _mode(imm6))
                out.append(_cvt_case(
                    f"{mn}_{label}_{tie.replace('-', 'n').replace('.', 'p')}",
                    _cvt_imm6_setup(imm6) + load_rf(1, x),
                    [enc_cvt(mn, 5, 1, imm6)],
                    [("rd", 5), ("rf", 0)], [value, fcsr_after(imm6, flags)]))
    return out


def cases_cvt_f2i_fo():
    """The four fo -> integer conversions, all six directions."""
    out = []
    for mn in ("fo2it", "fo2io", "fo2ut", "fo2uo"):
        iw, signed = F2I_DESC[mn][1], F2I_DESC[mn][2]
        for label, imm6 in CVT_MODES:
            vals = ("2.5", "2.7", "-2.5", "-2.7") if mn == "fo2it" else ("2.7",)
            for tie in vals:
                x = {"2.5": 0x4004000000000000, "2.7": 0x400599999999999A,
                     "-2.5": 0xC004000000000000,
                     "-2.7": 0xC00599999999999A}[tie]
                value, flags = F.f2i_exact(F.FO[0], F.FO[1], x, iw, signed,
                                           _mode(imm6))
                out.append(_cvt_case(
                    f"{mn}_{label}_{tie.replace('-', 'n').replace('.', 'p')}",
                    _cvt_imm6_setup(imm6) + load_rf(1, x),
                    [enc_cvt(mn, 5, 1, imm6)],
                    [("rd", 5), ("rf", 0)], [value, fcsr_after(imm6, flags)]))
    return out


def cases_cvt_i2f_ft():
    """it2ft/io2ft/ut2ft/uo2ft in all six directions: 2^24+1 forces a real
    rounding decision in ft."""
    out = []
    for mn in ("it2ft", "io2ft", "ut2ft", "uo2ft"):
        iw, signed, fmt = I2F_DESC[mn]
        for label, imm6 in CVT_MODES:
            n = 0x1000001 & ((1 << iw) - 1)
            rec, flags = F.i2f_exact(iw, fmt[0], fmt[1], n, signed, _mode(imm6))
            out.append(_cvt_case(
                f"{mn}_{label}", _cvt_imm6_setup(imm6) +
                sweep.load_rd(3, n), [enc_cvt(mn, 6, 3, imm6)],
                [("rf", 6), ("rf", 0)],
                [F.fn_from_recfn(fmt[0], fmt[1], rec), fcsr_after(imm6, flags)]))
    return out


def cases_cvt_i2f_fo():
    """io2fo/uo2fo in all six directions (2^53+1 rounds), and the exact
    it2fo/ut2fo (SBZ 0, no flags)."""
    out = []
    for mn in ("io2fo", "uo2fo"):
        iw, signed, fmt = I2F_DESC[mn]
        for label, imm6 in CVT_MODES:
            n = 0x20000000000001 & ((1 << iw) - 1)
            rec, flags = F.i2f_exact(iw, fmt[0], fmt[1], n, signed, _mode(imm6))
            out.append(_cvt_case(
                f"{mn}_{label}", _cvt_imm6_setup(imm6) +
                sweep.load_rd(3, n), [enc_cvt(mn, 6, 3, imm6)],
                [("rf", 6), ("rf", 0)],
                [F.fn_from_recfn(fmt[0], fmt[1], rec), fcsr_after(imm6, flags)]))
    return out


def cases_cvt_exact():
    """The three SBZ conversions (`ft2fo`/`it2fo`/`ut2fo`): exact, no flags."""
    out = []
    for tag, x in (("normal", 0x402CCCCD), ("subnormal", 0x00000001),
                   ("qnan", 0x7FC00000), ("inf", 0x7F800000),
                   ("nzero", 0x80000000)):
        rec, flags = F.f2f_exact(F.FT[0], F.FT[1], F.FO[0], F.FO[1], x, F.RNE)
        out.append(_cvt_case(
            f"ft2fo_{tag}", fcsr_clear() + load_rf(1, x),
            [enc_cvt("ft2fo", 4, 1, 0)],
            [("rf", 4), ("rf", 0)],
            [F.fn_from_recfn(F.FO[0], F.FO[1], rec), FCSR_BASE | flags]))
    for mn in ("it2fo", "ut2fo"):
        iw, signed, fmt = I2F_DESC[mn]
        for n in (0, 1, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000):
            if not signed:
                n &= 0xFFFFFFFF
            rec, flags = F.i2f_exact(iw, fmt[0], fmt[1], n, signed, F.RNE)
            out.append(_cvt_case(
                f"{mn}_{n:x}", fcsr_clear() + sweep.load_rd(3, n),
                [enc_cvt(mn, 6, 3, 0)],
                [("rf", 6), ("rf", 0)],
                [F.fn_from_recfn(fmt[0], fmt[1], rec), FCSR_BASE | flags]))
    return out


def cases_cvt_snan():
    """An sNaN through `ft2fo`: NV and a quiet NaN (spec/SimRISC-07 §1.4).

    The return value of a quieted sNaN is a quiet NaN; the spec does not fix
    its payload, and the three implementations disagree: this core (like
    hardfloat and gem5) returns the canonical quiet NaN, QEMU/softfloat
    propagates the input payload.  The case therefore asserts the core/model
    pair only and stays out of the QEMU cross-check.
    """
    x = 0x7F800001
    rec, flags = F.f2f_exact(F.FT[0], F.FT[1], F.FO[0], F.FO[1], x, F.RNE)
    return [_cvt_case("ft2fo_snan", fcsr_clear() + load_rf(1, x),
                      [enc_cvt("ft2fo", 4, 1, 0)],
                      [("rf", 4), ("rf", 0)],
                      [F.fn_from_recfn(F.FO[0], F.FO[1], rec), FCSR_BASE | flags])]


def cases_cvt_ff():
    """fo2ft in all six directions (overflow follows the rounding direction:
    RNE/RNA, RUP+ and RDN- give ±Inf, the other cells give ±ft_max -- see
    spec/SimRISC-07 §1.4 / IEEE 754-2019 §7.4), and the two block copies.

    The five static directions here carry the severe-overflow cells; the full
    five-direction x sign x severe/mild/midpoint matrix lives in `cvt_ff_ovf`."""
    out = []
    for label, imm6 in CVT_MODES:
        for tag, x in (("tie", 0x400599999999999A),
                       ("narrow", 0x3FF0000000000001),
                       ("ovf", 0x7FEFFFFFFFFFFFFF),
                       ("unf", 0x3690000000000000)):
            rec, flags = F.f2f_exact(F.FO[0], F.FO[1], F.FT[0], F.FT[1], x,
                                     _mode(imm6))
            out.append(_cvt_case(
                f"fo2ft_{label}_{tag}", _cvt_imm6_setup(imm6) + load_rf(1, x),
                [enc_cvt("fo2ft", 4, 1, imm6)],
                [("rf", 4), ("rf", 0)],
                [F.fn_from_recfn(F.FT[0], F.FT[1], rec), fcsr_after(imm6, flags)]))
    vals = [0x7FF800007FC00000, 0x8000000000000001, 0x3F800000DEADBEEF]
    for mn in ("ft2ft", "fo2fo"):
        out.append(_cvt_case(
            f"{mn}_block", fcsr_clear() +
            sum((load_rf(1 + i, v) for i, v in enumerate(vals)), []),
            [enc_cvt_ff(mn, 8, 1, 3)],
            [("rf", 8), ("rf", 9), ("rf", 10), ("rf", 0)],
            vals + [FCSR_BASE]))
    out.append(_cvt_case(
        "ft2ft_single", fcsr_clear() + load_rf(1, 0x12345678),
        [enc_cvt_ff("ft2ft", 2, 1, 1)],
        [("rf", 2), ("rf", 0)], [0x12345678, FCSR_BASE]))
    return out


def cases_cvt_ff_ovf():
    """`fo2ft` overflow in every cell (spec/SimRISC-07 §1.4 = IEEE 754-2019
    §7.4; `m13-testcases-011` builds the same matrix): 38 cases --

    * ``sev``: the largest double, five static directions x both signs (10);
      overflow in every direction, so the result is `±Inf` or `±ft_max` with
      `OF|NX`;
    * ``mild``: one double ulp above the midpoint between `ft_max` and 2^128,
      five directions x both signs (10); the directions that round down land on
      `ft_max`, which is *not* an overflow (`NX` only);
    * ``mid``: exactly that midpoint, i.e. the tie (10); RNE/RNA go up to
      2^128 and overflow;
    * ``dyn``: the dynamic `immu6 = 0x20` code with `rf0[33:32]` = 00/01/10/11,
      both signs (8), so the "follows `rf0`" path covers all four directions.
    """
    out = []
    sev = {"pos": 0x7FEFFFFFFFFFFFFF, "neg": 0xFFEFFFFFFFFFFFFF}
    shapes = (("sev", sev), ("mild", {"pos": 0x47EFFFFFF0000001,
                                      "neg": 0xC7EFFFFFF0000001}),
              ("mid", {"pos": 0x47EFFFFFF0000000,
                       "neg": 0xC7EFFFFFF0000000}))
    for tag, xs in shapes:
        for label, imm6 in CVT_MODES[:5]:          # the five static codes
            for sgn in ("pos", "neg"):
                x = xs[sgn]
                rec, flags = F.f2f_exact(F.FO[0], F.FO[1], F.FT[0], F.FT[1],
                                         x, _mode(imm6))
                name = (f"fo2ft_mid_{label}_{sgn}" if tag == "mid"
                        else f"fo2ft_ovf_{label}_{sgn}_{tag}")
                out.append(_cvt_case(
                    name, fcsr_clear() + load_rf(1, x),
                    [enc_cvt("fo2ft", 4, 1, imm6)],
                    [("rf", 4), ("rf", 0)],
                    [F.fn_from_recfn(F.FT[0], F.FT[1], rec),
                     fcsr_after(imm6, flags)]))
    for code, mode in enumerate((F.RNE, F.RTZ, F.RDN, F.RUP)):
        for sgn in ("pos", "neg"):
            x = sev[sgn]
            rec, flags = F.f2f_exact(F.FO[0], F.FO[1], F.FT[0], F.FT[1],
                                     x, mode)
            out.append(_cvt_case(
                f"fo2ft_ovf_dyn{code}_{sgn}_sev",
                fcsr_clear() + [enc_set_w_rf(0, 2, code)] + load_rf(1, x),
                [enc_cvt("fo2ft", 4, 1, 0x20)],
                [("rf", 4), ("rf", 0)],
                [F.fn_from_recfn(F.FT[0], F.FT[1], rec),
                 FCSR_BASE | (code << 32) | flags]))
    return out


def cases_cvt_sat():
    """Saturation and the NV / NX boundary: ±Inf, NaN, ±2^31, ±2^63, huge
    values, and the unsigned cases (a negative value that rounds to zero is
    inexact, not invalid)."""
    sat = [
        ("ft2it_pinf", "ft2it", F.FT, 0x7F800000, 32, True),
        ("ft2it_ninf", "ft2it", F.FT, 0xFF800000, 32, True),
        ("ft2it_p2p31", "ft2it", F.FT, 0x4F000000, 32, True),
        ("ft2it_n2p31", "ft2it", F.FT, 0xCF000000, 32, True),
        ("ft2io_p2p63", "ft2io", F.FT, 0x5F000000, 64, True),
        ("ft2io_n2p63", "ft2io", F.FT, 0xDF000000, 64, True),
        ("ft2it_big", "ft2it", F.FT, 0x7149F2CA, 32, True),
        ("ft2ut_big", "ft2ut", F.FT, 0x7149F2CA, 32, False),
        ("fo2io_p2p63", "fo2io", F.FO, 0x43E0000000000000, 64, True),
        ("fo2io_2p63m1", "fo2io", F.FO, 0x43DFFFFFFFFFFFFF, 64, True),
        ("fo2io_n2p63", "fo2io", F.FO, 0xC3E0000000000000, 64, True),
        ("fo2ut_p2p32", "fo2ut", F.FO, 0x41F0000000000000, 32, False),
        ("fo2ut_neg_small", "fo2ut", F.FO, 0xBFD999999999999A, 32, False),
        ("fo2ut_neg_tiny", "fo2ut", F.FO, 0xBFB999999999999A, 32, False),
        ("ft2it_qnan", "ft2it", F.FT, 0x7FC00000, 32, True),
        ("ft2it_qnan_neg", "ft2it", F.FT, 0xFFC00000, 32, True),
        ("ft2ut_snan", "ft2ut", F.FT, 0x7F800001, 32, False),
        ("fo2io_snan", "fo2io", F.FO, 0x7FF0000000000001, 64, True),
    ]
    out = []
    for name, mn, fmt, x, iw, signed in sat:
        value, flags = F.f2i_exact(fmt[0], fmt[1], x, iw, signed, F.RTZ)
        out.append(_cvt_case(name, fcsr_clear() + load_rf(1, x),
                             [enc_cvt(mn, 5, 1, 0x04)],
                             [("rd", 5), ("rf", 0)],
                             [value, FCSR_BASE | flags]))
    return out


def cases_cvt_flags():
    """`rf0[4:0]` end to end: the flags a conversion raises read back through
    `rf2rd rf0`, accumulate (sticky), and are cleared by a software write."""
    x = 0x402CCCCD
    v1, f1 = F.f2i_exact(F.FT[0], F.FT[1], x, 32, True, F.RTZ)
    v2, f2 = F.f2i_exact(F.FT[0], F.FT[1], x, 64, True, F.RNE)
    # The last case drives `fo2ft` over the overflow *and* the underflow edge.
    # RTZ pegs a positive overflow to `+ft_max` (not `+Inf`: spec/SimRISC-07
    # §1.4 = IEEE 754-2019 §7.4), so the expected word comes from the oracle
    # rather than a literal that would encode the old "always ±Inf" rule.
    v_ovf, f_ovf = F.f2f_exact(F.FO[0], F.FO[1], F.FT[0], F.FT[1],
                               0x7FEFFFFFFFFFFFFF, F.RTZ)
    v_unf, f_unf = F.f2f_exact(F.FO[0], F.FO[1], F.FT[0], F.FT[1],
                               0x3690000000000000, F.RNE)
    return [
        _cvt_case("flags_accumulate", fcsr_clear() + load_rf(1, x),
                  [enc_cvt("ft2it", 5, 1, 0x04), enc_cvt("ft2io", 6, 1, 0x01)],
                  [("rd", 5), ("rd", 6), ("rf", 0)],
                  [v1, v2, FCSR_BASE | (f1 | f2)]),
        _cvt_case("flags_clear_then_exact",
                  fcsr_clear() + load_rf(1, x) + load_rf(2, 0x40000000),
                  [enc_cvt("ft2it", 5, 1, 0x04),   # NX
                   enc_set_w_rf(0, 0, 0),          # software clear
                   enc_cvt("ft2it", 5, 2, 0x04)],  # exact: no flag
                  [("rd", 5), ("rf", 0)], [2, FCSR_BASE]),
        _cvt_case("flags_nv_sticky",
                  fcsr_clear() + load_rf(1, 0x7F800000) + load_rf(2, 0x402CCCCD),
                  [enc_cvt("ft2it", 5, 1, 0x04),   # NV
                   enc_cvt("ft2it", 6, 2, 0x04)],  # NX accumulates on top
                  [("rd", 5), ("rd", 6), ("rf", 0)],
                  [0x7FFFFFFF, 2, FCSR_BASE | 0x11]),
        _cvt_case("flags_of_uf_nx",
                  fcsr_clear() + load_rf(1, 0x7FEFFFFFFFFFFFFF) +
                  load_rf(2, 0x3690000000000000),
                  [enc_cvt("fo2ft", 4, 1, 0x04),   # OF|NX, pegged to +ft_max
                   enc_cvt("fo2ft", 5, 2, 0x01)],  # UF|NX accumulates
                  [("rf", 4), ("rf", 5), ("rf", 0)],
                  [F.fn_from_recfn(F.FT[0], F.FT[1], v_ovf), v_unf,
                   FCSR_BASE | (f_ovf | f_unf)]),
    ]


def _mode(imm6):
    """The rounding direction a static `immu6` code names (`0x20` is the
    dynamic code; the tests that use it set `rf0` = RTZ first)."""
    return {0x01: F.RNE, 0x02: F.RNA, 0x04: F.RTZ, 0x08: F.RUP,
            0x10: F.RDN, 0x20: F.RTZ}[imm6]


# ── m12-013: arithmetic family (spec/SimRISC-07 §2/§4) ────────────────────
ARITH_HA = {
    "ftadd": 0x10, "ftsub": 0x11, "ftmul": 0x12,
    "foadd": 0x18, "fosub": 0x19, "fomul": 0x1A,
    "ftmin": 0x26, "ftmax": 0x27, "fomin": 0x2E, "fomax": 0x2F,
    "ftqcmp": 0x20, "ftscmp": 0x21, "foqcmp": 0x28, "foscmp": 0x29,
    # m12-014: the multi-cycle family (spec/SimRISC-07 §2.1/§2.2)
    "ftdiv": 0x13, "ftrem": 0x14, "fodiv": 0x1B, "forem": 0x1C,
}

ROOT_HA = {"ftroot": 0x06, "foroot": 0x0E}


def enc_root(mn, dst, src, n):
    """`ftroot`/`foroot rfHB, rfHC, immu6` (`orri`, opc 0x44; n = 2 only)."""
    return (0x44 << 24) | (ROOT_HA[mn] << 18) | ((dst & 0x3F) << 12) | \
        ((src & 0x3F) << 6) | (n & 0x3F)
# rf0[33:32] -> rounding direction (spec/SimRISC-00 §浮点状态寄存器)
ARITH_MODES = (("rne", 0), ("rtz", 1), ("rdn", 2), ("rup", 3))


def enc_arith(mn, dst, hc, hd):
    """`orrr` arithmetic / compare / min-max (opc 0x44)."""
    return (0x44 << 24) | (ARITH_HA[mn] << 18) | ((dst & 0x3F) << 12) | \
        ((hc & 0x3F) << 6) | (hd & 0x3F)


def enc_fma(mn, ha, hb, hc, hd):
    """`rrrr` single-destination fused multiply-add (opc 0x5E/0x5F)."""
    opc = 0x5E if mn == "ftfma" else 0x5F
    return (opc << 24) | ((ha & 0x3F) << 18) | ((hb & 0x3F) << 12) | \
        ((hc & 0x3F) << 6) | (hd & 0x3F)


def arith_mode_setup(mode):
    """Reset the FCSR (flags and mode) and select the arithmetic direction."""
    return fcsr_clear() + [enc_set_w_rf(0, 2, mode)]


def arith_fcsr(mode, flags):
    """The `rf0` a case leaves behind: reset qNaN bits, the mode it selected
    and the accrued flags."""
    return FCSR_BASE | (mode << 32) | (flags & 0x1F)


# Operand pairs with a purpose each: exact, cancellation, the far path (huge +
# tiny), overflow, underflow, the subnormal boundary, every zero sign and the
# special values.  The 64-bit literals are the same bit patterns for ft (low
# 32 bits) and fo.
ARITH_PAIRS = [
    ("1_1", 0x3F800000, 0x3F800000, 0x3FF0000000000000, 0x3FF0000000000000),
    ("1_n1", 0x3F800000, 0xBF800000, 0x3FF0000000000000, 0xBFF0000000000000),
    ("cancel", 0x3F800001, 0xBF7FFFFF, 0x3FF0000000000001, 0xBFEFFFFFFFFFFFFF),
    ("nearcancel", 0x3F800000, 0xBF7FFFFE, 0x4000000000000000,
     0xBFFFFFFFFFFFFFFE),
    ("zp_zn", 0x00000000, 0x80000000, 0x0000000000000000,
     0x8000000000000000),
    ("zn_zn", 0x80000000, 0x80000000, 0x8000000000000000,
     0x8000000000000000),
    ("tiny_tiny", 0x00000001, 0x00000001, 0x0000000000000001,
     0x0000000000000001),
    ("subnorm_edge", 0x007FFFFF, 0x00000001, 0x000FFFFFFFFFFFFF,
     0x0000000000000001),
    ("far_big_tiny", 0x7F7FFFFF, 0x00000001, 0x7FEFFFFFFFFFFFFF,
     0x0000000000000001),
    ("far_tiny_big", 0x00000001, 0xFF7FFFFF, 0x0000000000000001,
     0xFFEFFFFFFFFFFFFF),
    ("ovf", 0x7F7FFFFF, 0x7F7FFFFF, 0x7FEFFFFFFFFFFFFF,
     0x7FEFFFFFFFFFFFFF),
    ("unf", 0x00800000, 0x3F000000, 0x0010000000000000,
     0x3FE0000000000000),
    ("exact_sub", 0x40000000, 0x3F800000, 0x4000000000000000,
     0x3FF0000000000000),
    ("third", 0x3EAAAAAB, 0x40400000, 0x3FD5555555555555,
     0x4008000000000000),
]

ARITH_TRIPLES = [
    # spec/SimRISC-07 §2.5: the fused result differs from mul-then-add
    ("spec_ft", 0x3F800001, 0x3F7FFFFE, 0xBF800000),
    ("spec_fo", 0x3FF0000000000001, 0x3FEFFFFFFFFFFFFF, 0xBFF0000000000000),
    ("cancel", 0x40000000, 0x3F800000, 0xC0000000),      # 2*1 + (-2) = 0
    ("near_cancel", 0x3F800000, 0x3F800001, 0xBF800001),
    ("prod_only", 0x3F800000, 0x40400000, 0x00000000),   # 1*3 + 0
    ("addend_only", 0x00000000, 0x3F800000, 0xC0400000),
    ("ovf", 0x7F7FFFFF, 0x40000000, 0x00000000),         # max*2 -> Inf
    ("unf", 0x00000001, 0x3F000000, 0x00000000),
    ("tiny_addend", 0x3F800000, 0x3F800000, 0x00000001),
    ("zeros", 0x00000000, 0x3F800000, 0x80000000),
    ("third_plus", 0x3EAAAAAB, 0x40400000, 0xBF800000),
]


def cases_arith_add_ft():
    return _cases_arith_add(False)


def cases_arith_add_fo():
    return _cases_arith_add(True)


def cases_arith_mul_ft():
    return _cases_arith_mul(False)


def cases_arith_mul_fo():
    return _cases_arith_mul(True)


def cases_arith_fma_ft():
    return _cases_arith_fma(False)


def cases_arith_fma_fo():
    return _cases_arith_fma(True)


def cases_arith_minmax_ft():
    return _cases_arith_minmax(False)


def cases_arith_minmax_fo():
    return _cases_arith_minmax(True)


def _pair_values(entry, fo):
    """(ft or fo) bit pattern of an `ARITH_PAIRS` entry."""
    return (entry[3], entry[4]) if fo else (entry[1], entry[2])


def _pair64(entry, fo):
    """Both operands at the 64-bit register width (ft keeps the low 32 bits)."""
    a, b = _pair_values(entry, fo)
    return a, b


def _cases_arith_add(want_fo):
    """`ftadd`/`ftsub` (or `foadd`/`fosub`) in all four `rf0` directions: the
    structural pairs of `ARITH_PAIRS` (cancellation, the far path, overflow,
    underflow, the subnormal boundary, both zero signs)."""
    out = []
    for mn, fo in (("ftadd", False), ("ftsub", False),
                   ("foadd", True), ("fosub", True)):
        if fo != want_fo:
            continue
        ew, sw = F.FO if fo else F.FT
        for label, mode in ARITH_MODES:
            for entry in ARITH_PAIRS:
                a, b = _pair64(entry, fo)
                if mn.endswith("sub"):
                    value, flags = F.add_exact(ew, sw, a, b, True, mode)
                else:
                    value, flags = F.add_exact(ew, sw, a, b, False, mode)
                out.append(_cvt_case(
                    f"{mn}_{label}_{entry[0]}",
                    arith_mode_setup(mode) + load_rf(1, a) + load_rf(2, b),
                    [enc_arith(mn, 3, 1, 2)],
                    [("rf", 3), ("rf", 0)],
                    [value, arith_fcsr(mode, flags)]))
    return out


def _cases_arith_mul(want_fo):
    """`ftmul`/`fomul` in all four directions: exact products, overflow,
    underflow, subnormal results and both zero / infinity operands."""
    out = []
    for mn, fo in (("ftmul", False), ("fomul", True)):
        if fo != want_fo:
            continue
        ew, sw = F.FO if fo else F.FT
        for label, mode in ARITH_MODES:
            for entry in ARITH_PAIRS:
                a, b = _pair64(entry, fo)
                value, flags = F.mul_exact(ew, sw, a, b, mode)
                out.append(_cvt_case(
                    f"{mn}_{label}_{entry[0]}",
                    arith_mode_setup(mode) + load_rf(1, a) + load_rf(2, b),
                    [enc_arith(mn, 3, 1, 2)],
                    [("rf", 3), ("rf", 0)],
                    [value, arith_fcsr(mode, flags)]))
        # infinity / zero operands
        inf = 0x7F800000 if not fo else 0x7FF0000000000000
        pinf = inf
        ninf = inf | (0x80000000 if not fo else 0x8000000000000000)
        for name, a, b in (("inf_zero", pinf, 0), ("zero_inf", 0, ninf),
                           ("inf_finite", pinf, 0x3F800000 if not fo
                            else 0x3FF0000000000000)):
            value, flags = F.mul_exact(ew, sw, a, b, F.RNE)
            out.append(_cvt_case(
                f"{mn}_{name}",
                arith_mode_setup(0) + load_rf(1, a) + load_rf(2, b),
                [enc_arith(mn, 3, 1, 2)], [("rf", 3), ("rf", 0)],
                [value, arith_fcsr(0, flags)]))
    return out


def _cases_arith_fma(want_fo):
    """`ftfma`/`fofma`: the single-rounding counterexample of
    spec/SimRISC-07 §2.5, exact cancellation of the fused sum, overflow and
    underflow of the product, and the addend-only / product-only shapes."""
    out = []
    for mn, fo in (("ftfma", False), ("fofma", True)):
        if fo != want_fo:
            continue
        ew, sw = F.FO if fo else F.FT
        for label, mode in ARITH_MODES:
            for name, a, b, c in ARITH_TRIPLES:
                if fo:
                    a, b, c = _fo_triple(name, a, b, c)
                else:
                    a, b, c = a & 0xFFFFFFFF, b & 0xFFFFFFFF, c & 0xFFFFFFFF
                value, flags = F.fma_exact(ew, sw, a, b, c, mode)
                out.append(_cvt_case(
                    f"{mn}_{label}_{name}",
                    arith_mode_setup(mode) + load_rf(1, a) + load_rf(2, b) +
                    load_rf(3, c),
                    [enc_fma(mn, 4, 1, 2, 3)],
                    [("rf", 4), ("rf", 0)],
                    [value, arith_fcsr(mode, flags)]))
    return out


def _fo_triple(name, a, b, c):
    """The fo spellings of the `ARITH_TRIPLES` operands (the ft literals are
    32-bit patterns and would be subnormals in fo)."""
    fo_triples = {
        "spec_ft": (0x3FF0000000000001, 0x3FEFFFFFFFFFFFFF,
                    0xBFF0000000000000),
        "spec_fo": (0x3FF0000000000001, 0x3FEFFFFFFFFFFFFF,
                    0xBFF0000000000000),
        "cancel": (0x4000000000000000, 0x3FF0000000000000,
                   0xC000000000000000),
        "near_cancel": (0x3FF0000000000000, 0x3FF0000000000001,
                        0xBFF0000000000001),
        "prod_only": (0x3FF0000000000000, 0x4008000000000000, 0),
        "addend_only": (0, 0x3FF0000000000000, 0xC008000000000000),
        "ovf": (0x7FEFFFFFFFFFFFFF, 0x4000000000000000, 0),
        "unf": (0x0000000000000001, 0x3FE0000000000000, 0),
        "tiny_addend": (0x3FF0000000000000, 0x3FF0000000000000,
                        0x0000000000000001),
        "zeros": (0, 0x3FF0000000000000, 0x8000000000000000),
        "third_plus": (0x3FD5555555555555, 0x4008000000000000,
                       0xBFF0000000000000),
    }
    return fo_triples.get(name, (a, b, c))


def cases_arith_cmp():
    """`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp` over the ordered cases and a quiet
    NaN (every form gives "unordered" there; the `NV` column follows
    spec/SimRISC-07 §4 -- signalling compare raises it, quiet compare does
    not)."""
    pairs_ft = [
        ("gt", 0x40000000, 0x3F800000), ("lt", 0x3F800000, 0x40000000),
        ("eq", 0x3F800000, 0x3F800000), ("neg_lt", 0xBF800000, 0x3F800000),
        ("neg_gt", 0xBF800000, 0xC0000000), ("zp_zn", 0x00000000,
                                             0x80000000),
        ("zn_zp", 0x80000000, 0x00000000), ("pinf", 0x7F800000, 0x7F7FFFFF),
        ("ninf", 0xFF800000, 0x7F800000), ("both_inf", 0x7F800000,
                                           0x7F800000),
        ("qnan_a", 0x7FC00000, 0x3F800000), ("qnan_b", 0x3F800000,
                                             0x7FE00001),
        ("qnan_both", 0x7FC00000, 0xFFC00000),
    ]
    out = []
    for mn, fo, signaling in (("ftqcmp", False, False), ("ftscmp", False, True),
                              ("foqcmp", True, False), ("foscmp", True, True)):
        ew, sw = F.FO if fo else F.FT
        for name, a32, b32 in pairs_ft:
            if fo:
                a = _widen_fo(a32)
                b = _widen_fo(b32)
            else:
                a, b = a32, b32
            value, flags = F.cmp_exact(ew, sw, a, b, signaling)
            out.append(_cvt_case(
                f"{mn}_{name}", fcsr_clear() + load_rf(1, a) + load_rf(2, b),
                [enc_arith(mn, 5, 1, 2)], [("rd", 5), ("rf", 0)],
                [value, FCSR_BASE | flags]))
    return out


def _widen_fo(x32):
    """The fo spelling of interest for a 32-bit literal (1.0, 2.0, +-0, +-Inf,
    qNaN); anything else keeps its value as an fo bit pattern."""
    table = {0x3F800000: 0x3FF0000000000000, 0x40000000: 0x4000000000000000,
             0xBF800000: 0xBFF0000000000000, 0xC0000000: 0xC000000000000000,
             0x7F800000: 0x7FF0000000000000, 0xFF800000: 0xFFF0000000000000,
             0x7FC00000: 0x7FF8000000000000, 0x7FE00001: 0x7FFC000000000001,
             0xFFC00000: 0xFFF8000000000000, 0x00000000: 0,
             0x80000000: 0x8000000000000000,
             # signalling NaNs of ft -> the fo spellings
             0x7F800001: 0x7FF0000000000001,
             0x7FBFFFFF: 0x7FF7FFFFFFFFFFFF}
    if x32 in table:
        return table[x32]
    return x32 << 32 if x32 else 0


def _cases_arith_minmax(want_fo):
    """`ftmin`/`ftmax`/`fomin`/`fomax`: the six boundary rules of
    spec/SimRISC-07 §2.4 (§9.6 `minimumNumber`/`maximumNumber`)."""
    pairs_ft = [
        ("ordered", 0x3F800000, 0x40000000),
        ("rev", 0x40000000, 0x3F800000),
        ("zero_signs", 0x00000000, 0x80000000),
        ("zero_signs_rev", 0x80000000, 0x00000000),
        ("pz_pz", 0x00000000, 0x00000000),
        ("nz_nz", 0x80000000, 0x80000000),
        ("equal", 0x3F800000, 0x3F800000),
        ("neg_pair", 0xBF800000, 0xC0000000),
        ("inf_gt", 0x7F800000, 0x40000000),
        ("ninf_lt", 0xFF800000, 0xC0000000),
        ("qnan_a", 0x7FC00000, 0x3F800000),
        ("qnan_b", 0x3F800000, 0xFFC00000),
        ("qnan_both", 0x7FC00000, 0x7FE00001),
        ("snan_a", 0x7F800001, 0x3F800000),
        ("snan_both", 0x7F800001, 0x7FBFFFFF),
        ("snan_qnan", 0x7F800001, 0x7FC00000),
        ("subnormal", 0x00000001, 0x00000002),
    ]
    out = []
    for mn, fo, is_max in (("ftmin", False, False), ("ftmax", False, True),
                           ("fomin", True, False), ("fomax", True, True)):
        if fo != want_fo:
            continue
        ew, sw = F.FO if fo else F.FT
        for name, a32, b32 in pairs_ft:
            a, b = (_widen_fo(a32), _widen_fo(b32)) if fo else (a32, b32)
            value, flags = F.minmax_exact(ew, sw, a, b, is_max)
            out.append(_cvt_case(
                f"{mn}_{name}", fcsr_clear() + load_rf(1, a) + load_rf(2, b),
                [enc_arith(mn, 3, 1, 2)], [("rf", 3), ("rf", 0)],
                [value, FCSR_BASE | flags]))
    return out


def cases_cmp_nan():
    """Compare with a NaN operand, both forms and both NaN classes.

    `NV` follows spec/SimRISC-07 §4: the signalling forms raise it for **any**
    unordered pair (sNaN or qNaN, IEEE 754-2019 §5.7.1), the quiet forms raise
    nothing even on an sNaN input.  The result value still follows the form
    (quiet compare -> qNaN, signalling compare -> sNaN).  QEMU implements the
    same rule (`signal_nv`), so the group is compared three ways.
    """
    out = []
    for mn, fo, signaling in (("ftqcmp", False, False), ("ftscmp", False, True),
                              ("foqcmp", True, False), ("foscmp", True, True)):
        ew, sw = F.FO if fo else F.FT
        for name, a32, b32 in (("qnan_a", 0x7FC00000, 0x3F800000),
                               ("qnan_b", 0x3F800000, 0x7FE00001),
                               ("snan_a", 0x7F800001, 0x3F800000),
                               ("snan_b", 0x3F800000, 0x7FBFFFFF),
                               ("snan_both", 0x7F800001, 0x7FBFFFFF)):
            a, b = (_widen_fo(a32), _widen_fo(b32)) if fo else (a32, b32)
            value, flags = F.cmp_exact(ew, sw, a, b, signaling)
            out.append(_cvt_case(
                f"{mn}_{name}", fcsr_clear() + load_rf(1, a) + load_rf(2, b),
                [enc_arith(mn, 5, 1, 2)], [("rd", 5), ("rf", 0)],
                [value, FCSR_BASE | flags]))
    return out


# ── m12-014: divide / root / remainder (spec/SimRISC-07 §2.1/§2.2) ────────
#
# Operand pairs with one purpose each: exact quotients, repeating quotients
# (every direction is distinguishable), 0/0 and Inf/Inf (NV), a finite value
# over +-0 (`DZ` with the right infinite sign), the infinite and zero results
# of the other operand shapes, overflow, underflow, quiet/signalling NaN, and
# the subnormal boundaries.
DIVREM_PAIRS = [
    ("one_one", 0x3F800000, 0x3F800000, 0x3FF0000000000000, 0x3FF0000000000000),
    ("three_two", 0x40400000, 0x40000000, 0x4008000000000000,
     0x4000000000000000),
    ("one_three", 0x3F800000, 0x40400000, 0x3FF0000000000000,
     0x4008000000000000),
    ("two_three", 0x40000000, 0x40400000, 0x4000000000000000,
     0x4008000000000000),
    ("zero_zero", 0x00000000, 0x00000000, 0x0000000000000000,
     0x0000000000000000),
    ("inf_inf", 0x7F800000, 0x7F800000, 0x7FF0000000000000,
     0x7FF0000000000000),
    ("one_zero", 0x3F800000, 0x00000000, 0x3FF0000000000000,
     0x0000000000000000),
    ("n_one_zero", 0xBF800000, 0x00000000, 0xBFF0000000000000,
     0x0000000000000000),
    ("one_nzero", 0x3F800000, 0x80000000, 0x3FF0000000000000,
     0x8000000000000000),
    ("zero_one", 0x00000000, 0x3F800000, 0x0000000000000000,
     0x3FF0000000000000),
    ("nzero_one", 0x80000000, 0x3F800000, 0x8000000000000000,
     0x3FF0000000000000),
    ("inf_one", 0x7F800000, 0x3F800000, 0x7FF0000000000000,
     0x3FF0000000000000),
    ("ninf_one", 0xFF800000, 0x3F800000, 0xFFF0000000000000,
     0x3FF0000000000000),
    ("one_inf", 0x3F800000, 0x7F800000, 0x3FF0000000000000,
     0x7FF0000000000000),
    ("one_ninf", 0x3F800000, 0xFF800000, 0x3FF0000000000000,
     0xFFF0000000000000),
    ("ovf", 0x7F7FFFFF, 0x3F000000, 0x7FEFFFFFFFFFFFFF,
     0x3FE0000000000000),
    ("unf", 0x00000001, 0x40000000, 0x0000000000000001,
     0x4000000000000000),
    ("tiny_tiny", 0x00000001, 0x00800000, 0x0000000000000001,
     0x0010000000000000),
    ("max_one", 0x7F7FFFFF, 0x3F800000, 0x7FEFFFFFFFFFFFFF,
     0x3FF0000000000000),
    ("one_tiny", 0x3F800000, 0x00000001, 0x3FF0000000000000,
     0x0000000000000001),
    ("subnorm_edge", 0x007FFFFF, 0x3F800000, 0x000FFFFFFFFFFFFF,
     0x3FF0000000000000),
    ("qnan", 0x7FC00123, 0x3F800000, 0x7FF8000000000123,
     0x3FF0000000000000),
    ("qnan_zero", 0x7FC00123, 0x00000000, 0x7FF8000000000123,
     0x0000000000000000),
]

# Square-root operands: exact roots, the smallest/largest normals, subnormals,
# every special value and the sign of zero.
DIVREM_UNARY = [
    ("four", 0x40800000, 0x4010000000000000),
    ("two", 0x40000000, 0x4000000000000000),
    ("one", 0x3F800000, 0x3FF0000000000000),
    ("nine", 0x41100000, 0x4022000000000000),
    ("third", 0x3EAAAAAB, 0x3FD5555555555555),
    ("half", 0x3F000000, 0x3FE0000000000000),
    ("min_norm", 0x00800000, 0x0010000000000000),
    ("max", 0x7F7FFFFF, 0x7FEFFFFFFFFFFFFF),
    ("min_sub", 0x00000001, 0x0000000000000001),
    ("max_sub", 0x007FFFFF, 0x000FFFFFFFFFFFFF),
    ("zero", 0x00000000, 0x0000000000000000),
    ("nzero", 0x80000000, 0x8000000000000000),
    ("inf", 0x7F800000, 0x7FF0000000000000),
    ("ninf", 0xFF800000, 0xFFF0000000000000),
    ("neg", 0xC0800000, 0xC010000000000000),
    ("nsub", 0x80000001, 0x8000000000000001),
    ("qnan", 0x7FC00123, 0x7FF8000000000123),
]

# Remainder pairs: the tie cases (3 rem 2 and 1 rem 0.5 both round to the even
# quotient), sign of the dividend, the three invalid shapes (both signs:
# +-Inf dividend, +-0 divisor), the pass-through shapes and a large exponent
# distance (the long-iteration case).
REM_PAIRS = [
    ("five_two", 0x40A00000, 0x40000000, 0x4014000000000000,
     0x4000000000000000),
    ("three_two", 0x40400000, 0x40000000, 0x4008000000000000,
     0x4000000000000000),
    ("two_half", 0x40200000, 0x3F000000, 0x4008000000000000,
     0x3FE0000000000000),
    ("two5_one", 0x40200000, 0x3F800000, 0x4004000000000000,
     0x3FF0000000000000),
    ("n5_two", 0xC0A00000, 0x40000000, 0xC014000000000000,
     0x4000000000000000),
    ("5_n2", 0x40A00000, 0xC0000000, 0x4014000000000000,
     0xC000000000000000),
    ("one_zero", 0x3F800000, 0x00000000, 0x3FF0000000000000,
     0x0000000000000000),
    ("one_nzero", 0x3F800000, 0x80000000, 0x3FF0000000000000,
     0x8000000000000000),
    ("inf_two", 0x7F800000, 0x40000000, 0x7FF0000000000000,
     0x4000000000000000),
    ("ninf_two", 0xFF800000, 0x40000000, 0xFFF0000000000000,
     0x4000000000000000),
    ("three_inf", 0x40400000, 0x7F800000, 0x4008000000000000,
     0x7FF0000000000000),
    ("zero_three", 0x00000000, 0x40400000, 0x0000000000000000,
     0x4008000000000000),
    ("nzero_three", 0x80000000, 0x40400000, 0x8000000000000000,
     0x4008000000000000),
    ("qnan", 0x7FC00123, 0x40000000, 0x7FF8000000000123,
     0x4000000000000000),
    ("exact", 0x40800000, 0x40000000, 0x4010000000000000,
     0x4000000000000000),
    ("tiny_max", 0x00000001, 0x7F7FFFFF, 0x0000000000000001,
     0x7FEFFFFFFFFFFFFF),
    ("max_tiny", 0x7F7FFFFF, 0x00000001, 0x7FEFFFFFFFFFFFFF,
     0x0000000000000001),
    ("sub_sub", 0x00000003, 0x00000002, 0x0000000000000003,
     0x0000000000000002),
]


def _divrem_pair(entry, fo):
    return (entry[3], entry[4]) if fo else (entry[1], entry[2])


def _cases_div(want_fo):
    """`ftdiv`/`fodiv` in all four `rf0` directions (the quotient is rounded,
    so the direction is architecturally visible)."""
    out = []
    for mn, fo in (("ftdiv", False), ("fodiv", True)):
        if fo != want_fo:
            continue
        ew, sw = F.FO if fo else F.FT
        for label, mode in ARITH_MODES:
            for entry in DIVREM_PAIRS:
                a, b = _divrem_pair(entry, fo)
                value, flags = F.div_exact(ew, sw, a, b, mode)
                out.append(_cvt_case(
                    f"{mn}_{entry[0]}_m{mode}",
                    arith_mode_setup(mode) + load_rf(1, a) + load_rf(2, b),
                    [enc_arith(mn, 3, 1, 2)],
                    [("rf", 3), ("rf", 0)],
                    [value, arith_fcsr(mode, flags)]))
    return out


def _cases_sqrt(want_fo):
    """`ftroot`/`foroot` with `immu6` = 2 in all four directions."""
    out = []
    for mn, fo in (("ftroot", False), ("foroot", True)):
        if fo != want_fo:
            continue
        ew, sw = F.FO if fo else F.FT
        for label, mode in ARITH_MODES:
            for entry in DIVREM_UNARY:
                a = entry[2] if fo else entry[1]
                value, flags = F.sqrt_exact(ew, sw, a, mode)
                out.append(_cvt_case(
                    f"{mn}_{entry[0]}_m{mode}",
                    arith_mode_setup(mode) + load_rf(1, a),
                    [enc_root(mn, 3, 1, 2)],
                    [("rf", 3), ("rf", 0)],
                    [value, arith_fcsr(mode, flags)]))
    return out


def _cases_rem(want_fo):
    """`ftrem`/`forem`: the result is exact, so one direction suffices and the
    coverage is in the operand pairs (tie-to-even, signs, invalid shapes,
    pass-through, the largest exponent distance)."""
    out = []
    for mn, fo in (("ftrem", False), ("forem", True)):
        if fo != want_fo:
            continue
        ew, sw = F.FO if fo else F.FT
        for entry in REM_PAIRS:
            a, b = _divrem_pair(entry, fo)
            value, flags = F.rem_exact(ew, sw, a, b)
            out.append(_cvt_case(
                f"{mn}_{entry[0]}",
                arith_mode_setup(0) + load_rf(1, a) + load_rf(2, b),
                [enc_arith(mn, 3, 1, 2)],
                [("rf", 3), ("rf", 0)],
                [value, arith_fcsr(0, flags)]))
    return out


def cases_div_ft():
    return _cases_div(False)


def cases_div_fo():
    return _cases_div(True)


def cases_sqrt_ft():
    return _cases_sqrt(False)


def cases_sqrt_fo():
    return _cases_sqrt(True)


def cases_rem_ft():
    return _cases_rem(False)


def cases_rem_fo():
    return _cases_rem(True)


def cases_divrem_nan():
    """Signalling NaNs across the family: `NV` plus the *canonical* quiet NaN
    (spec/SimRISC-07 §1.4; the same rule the fused multiply-add follows).

    Model-only, like the arithmetic family's `arith_nan` group: QEMU/softfloat
    keeps the quieted payload of an sNaN while this core (and hardfloat, and
    gem5) canonicalises it, so the *value* of these cases is not comparable
    byte for byte.  The `NV` bit and the "is a NaN" property are, which is what
    the `divrem_special` group asserts next to the invalid operations.
    """
    out = []
    for mn, fo, a, b, kind in (("fodiv", True, 0x7FF0000000000001,
                                0x3FF0000000000000, "div"),
                               ("fodiv", True, 0x3FF0000000000000,
                                0xFFF0000000000001, "div"),
                               ("ftdiv", False, 0x7F800001, 0x3F800000, "div"),
                               ("foroot", True, 0x7FF0000000000001, 0, "sqrt"),
                               ("ftroot", False, 0x7F800001, 0, "sqrt"),
                               ("forem", True, 0x7FF0000000000001,
                                0x4000000000000000, "rem"),
                               ("ftrem", False, 0x7F800001, 0x40000000, "rem"),
                               ("forem", True, 0x3FF0000000000000,
                                0x7FF0000000000001, "rem"),
                               # the *sign* of a propagated NaN: this core (and
                               # hardfloat) return sign 0, softfloat/QEMU keep
                               # the operand's sign -- model-only
                               ("fodiv", True, 0x3FF0000000000000,
                                0xFFF8000000000456, "div"),
                               ("ftdiv", False, 0x3F800000, 0xFFC00456,
                                "div")):
        ew, sw = F.FO if fo else F.FT
        if kind == "sqrt":
            value, flags = F.sqrt_exact(ew, sw, a, F.RNE)
            word = enc_root(mn, 3, 1, 2)
        elif kind == "div":
            value, flags = F.div_exact(ew, sw, a, b, F.RNE)
            word = enc_arith(mn, 3, 1, 2)
        else:
            value, flags = F.rem_exact(ew, sw, a, b)
            word = enc_arith(mn, 3, 1, 2)
        setup = arith_mode_setup(0) + load_rf(1, a) + load_rf(2, b)
        out.append(_cvt_case(f"divrem_snan_{mn}_{kind}", setup, [word],
                             [("rf", 3), ("rf", 0)],
                             [value, arith_fcsr(0, flags)]))
    return out


def cases_divrem_special():
    """The shapes the task calls out by name, in both formats: `0/0` and
    `Inf/Inf` (`NV` + canonical quiet NaN), `sqrt(-x)` and `sqrt(-Inf)` (`NV`
    + canonical quiet NaN), and the `DZ` lane (a finite non-zero value over
    +-0 => `±Inf` with exactly `DZ`, no `NX`).  Each entry carries its own ft
    and fo bit patterns, so the ft cases really are ft values.
    """
    div = [
        ("div_0_0", 0x00000000, 0x00000000,
         0x0000000000000000, 0x0000000000000000),
        ("div_inf_inf", 0x7F800000, 0x7F800000,
         0x7FF0000000000000, 0x7FF0000000000000),
        ("div_1_0", 0x3F800000, 0x00000000,
         0x3FF0000000000000, 0x0000000000000000),
        ("div_n1_0", 0xBF800000, 0x00000000,
         0xBFF0000000000000, 0x0000000000000000),
        ("div_1_n0", 0x3F800000, 0x80000000,
         0x3FF0000000000000, 0x8000000000000000),
        ("div_tiny_0", 0x00000001, 0x80000000,
         0x0000000000000001, 0x8000000000000000),
    ]
    root = [
        ("sqrt_neg", 0xC0800000, 0xC010000000000000),
        ("sqrt_ninf", 0xFF800000, 0xFFF0000000000000),
        ("sqrt_neg_zero", 0x80000000, 0x8000000000000000),
        ("sqrt_zero", 0x00000000, 0x0000000000000000),
        ("sqrt_inf", 0x7F800000, 0x7FF0000000000000),
    ]
    out = []
    for name, fa, fb, da, db in div:
        for fo, a, b in ((True, da, db), (False, fa, fb)):
            value, flags = F.div_exact(11 if fo else 8, 53 if fo else 24,
                                       a, b, F.RNE)
            out.append(_cvt_case(
                f"special_{name}_{'fo' if fo else 'ft'}",
                arith_mode_setup(0) + load_rf(1, a) + load_rf(2, b),
                [enc_arith("fodiv" if fo else "ftdiv", 3, 1, 2)],
                [("rf", 3), ("rf", 0)],
                [value, arith_fcsr(0, flags)]))
    for name, fa, da in root:
        for fo, a in ((True, da), (False, fa)):
            value, flags = F.sqrt_exact(11 if fo else 8, 53 if fo else 24,
                                        a, F.RNE)
            out.append(_cvt_case(
                f"special_{name}_{'fo' if fo else 'ft'}",
                arith_mode_setup(0) + load_rf(1, a),
                [enc_root("foroot" if fo else "ftroot", 3, 1, 2)],
                [("rf", 3), ("rf", 0)],
                [value, arith_fcsr(0, flags)]))
    return out


def cases_divrem_faults():
    """Legality of the multi-cycle family: `dst_rf0` on all six forms and the
    `encode_fp_root_n` rule (`immu6` = n must be 2)."""
    return [
        {"name": "fault_ftdiv_dst_rf0", "word": enc_arith("ftdiv", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_fodiv_dst_rf0", "word": enc_arith("fodiv", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftrem_dst_rf0", "word": enc_arith("ftrem", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_forem_dst_rf0", "word": enc_arith("forem", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftroot_dst_rf0", "word": enc_root("ftroot", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_foroot_dst_rf0", "word": enc_root("foroot", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftroot_n1", "word": enc_root("ftroot", 3, 1, 1),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_foroot_n3", "word": enc_root("foroot", 3, 1, 3),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_foroot_n0", "word": enc_root("foroot", 3, 1, 0),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftroot_n63", "word": enc_root("ftroot", 3, 1, 63),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
    ]


def cases_arith_fma_special():
    """FMA with a NaN factor next to an infinity, three ways.

    A NaN multiplicand makes the *product* NaN even when the other factor is
    an infinity, so `qNaN x Inf + (-Inf)` is a NaN propagation (no `NV`); the
    invalid `Inf + (-Inf)` still needs a finite non-zero multiplicand
    (spec/SimRISC-07 §2.5).  `0 x Inf + qNaN` stays invalid even though the
    addend is a quiet NaN.
    """
    out = []
    cases = (("qnan_inf_neg_inf", 0x7FF8000000000123, 0x7FF0000000000000,
              0xFFF0000000000000),
             ("qnan_inf_pos_inf", 0x7FF8000000000123, 0x7FF0000000000000,
              0x7FF0000000000000),
             ("inf_neg_inf", 0x7FF0000000000000, 0x3FF0000000000000,
              0xFFF0000000000000),
             ("inf_pos_inf", 0x7FF0000000000000, 0x3FF0000000000000,
              0x7FF0000000000000),
             ("zero_inf_qnan", 0, 0x7FF0000000000000,
              0x7FF8000000000000))
    for name, a, b, c in cases:
        value, flags = F.fma_exact(11, 53, a, b, c, F.RNE)
        out.append(_cvt_case(
            f"fofma_{name}", arith_mode_setup(0) + load_rf(1, a) +
            load_rf(2, b) + load_rf(3, c), [enc_fma("fofma", 4, 1, 2, 3)],
            [("rf", 4), ("rf", 0)], [value, arith_fcsr(0, flags)]))
    return out


def cases_arith_flags():
    """`OF`/`UF`/`NX` raised by *arithmetic* and read back through
    `rf2rd rf0`, with sticky accumulation and a software clear in between."""
    out = []
    # foadd: two large finite values overflow -> +Inf + OF|NX
    out.append(_cvt_case(
        "arithflags_add_ovf",
        arith_mode_setup(0) + load_rf(1, 0x7FEFFFFFFFFFFFFF) +
        load_rf(2, 0x7FEFFFFFFFFFFFFF),
        [enc_arith("foadd", 3, 1, 2)], [("rf", 3), ("rf", 0)],
        [0x7FF0000000000000, arith_fcsr(0, F.OF | F.NX)]))
    # fomul: tiny * 0.5 -> 0 with UF|NX
    out.append(_cvt_case(
        "arithflags_mul_unf",
        arith_mode_setup(0) + load_rf(1, 0x0000000000000001) +
        load_rf(2, 0x3FE0000000000000),
        [enc_arith("fomul", 3, 1, 2)], [("rf", 3), ("rf", 0)],
        [0, arith_fcsr(0, F.UF | F.NX)]))
    # foadd: 1/3-like inexact sum -> NX only
    v, fl = F.add_exact(11, 53, 0x3FD5555555555555, 0x3FD5555555555555,
                        False, F.RNE)
    out.append(_cvt_case(
        "arithflags_add_nx",
        arith_mode_setup(0) + load_rf(1, 0x3FD5555555555555) +
        load_rf(2, 0x3FD5555555555555),
        [enc_arith("foadd", 3, 1, 2)], [("rf", 3), ("rf", 0)],
        [v, arith_fcsr(0, fl)]))
    # sticky: an overflow then a software clear then an exact operation
    out.append(_cvt_case(
        "arithflags_sticky_and_clear",
        arith_mode_setup(0) + load_rf(1, 0x7FEFFFFFFFFFFFFF) +
        load_rf(2, 0x7FEFFFFFFFFFFFFF) + load_rf(3, 0x3FF0000000000000),
        [enc_arith("foadd", 4, 1, 2),      # OF|NX
         enc_set_w_rf(0, 0, 0),            # software clear
         enc_arith("fomul", 5, 3, 3)],     # exact: no flag
        [("rf", 4), ("rf", 5), ("rf", 0)],
        [0x7FF0000000000000, 0x3FF0000000000000, FCSR_BASE]))
    # Overflow is judged on the *rounded* exponent (spec §1.4): adding a
    # sub-ulp amount to the largest finite value leaves it finite but inexact
    # (only NX) under the directed modes that round back, while nearest/away
    # carry into the Inf exponent (OF|NX).  Three distances pin the rounding
    # decision: half an ulp (a tie; RNE rounds to even, i.e. up), three
    # quarters of an ulp (nearest rounds up) and one ulp.  The arithmetic
    # family takes its direction from `rf0[33:32]`, which encodes four modes
    # (RNE/RTZ/RDN/RUP); RNA is only reachable through the conversions' one-hot
    # code, so it stays out of this FCSR-driven group (the model anchors cover
    # it).
    for dist, addend in (("half_ulp", 0x7C90000000000000),
                         ("three_qtr_ulp", 0x7C98000000000000),
                         ("one_ulp", 0x7CA0000000000000)):
        for label, mode in (("rne", F.RNE), ("rtz", F.RTZ),
                            ("rdn", F.RDN), ("rup", F.RUP)):
            v2, fl2 = F.add_exact(11, 53, 0x7FEFFFFFFFFFFFFF, addend,
                                  False, mode)
            out.append(_cvt_case(
                f"arithflags_of_{dist}_{label}",
                arith_mode_setup(mode) + load_rf(1, 0x7FEFFFFFFFFFFFFF) +
                load_rf(2, addend),
                [enc_arith("foadd", 3, 1, 2)], [("rf", 3), ("rf", 0)],
                [v2, arith_fcsr(mode, fl2)]))
    # accumulate two arithmetic operations (NX then UF|NX)
    out.append(_cvt_case(
        "arithflags_accumulate",
        arith_mode_setup(0) + load_rf(1, 0x3FD5555555555555) +
        load_rf(2, 0x3FD5555555555555) + load_rf(3, 0x0000000000000001) +
        load_rf(4, 0x3FE0000000000000),
        [enc_arith("foadd", 5, 1, 2),      # NX
         enc_arith("fomul", 6, 3, 4)],     # UF|NX accumulates
        [("rf", 5), ("rf", 6), ("rf", 0)],
        [v, 0, arith_fcsr(0, F.NX | F.UF | F.NX)]))
    return out


def cases_arith_nan():
    """Arithmetic with NaN operands, model-only: an sNaN is quieted here (this
    core, like hardfloat and gem5, returns the canonical quiet NaN) while
    softfloat/QEMU propagates the quieted payload; the flag (NV) and the
    "is a NaN" answer agree.  A quiet NaN input keeps its payload for
    add/sub/mul (`spec/SimRISC-07 §1.4`) and is canonicalised by the fused
    multiply-add (`§2.5`)."""
    out = []
    for mn, fo in (("foadd", True), ("fomul", True)):
        ew, sw = (11, 53)
        for name, a, b in (("qnan_a", 0x7FF8000000000123, 0x3FF0000000000000),
                           ("qnan_b", 0x3FF0000000000000,
                            0xFFF8000000000456),
                           ("snan_a", 0x7FF0000000000001,
                            0x3FF0000000000000),
                           ("snan_qnan", 0x7FF0000000000001,
                            0x7FF8000000000000)):
            if mn == "fomul":
                value, flags = F.mul_exact(ew, sw, a, b, F.RNE)
            else:
                value, flags = F.add_exact(ew, sw, a, b, False, F.RNE)
            out.append(_cvt_case(
                f"{mn}_{name}", arith_mode_setup(0) + load_rf(1, a) +
                load_rf(2, b), [enc_arith(mn, 3, 1, 2)],
                [("rf", 3), ("rf", 0)], [value, arith_fcsr(0, flags)]))
    for name, a, b, c in (("qnan", 0x7FF8000000000123, 0x3FF0000000000000,
                           0x3FF0000000000000),
                          ("snan", 0x7FF0000000000001, 0x3FF0000000000000,
                           0x3FF0000000000000),
                          ("zero_inf", 0, 0x7FF0000000000000,
                           0x7FF8000000000000)):
        value, flags = F.fma_exact(11, 53, a, b, c, F.RNE)
        out.append(_cvt_case(
            f"fofma_{name}", arith_mode_setup(0) + load_rf(1, a) +
            load_rf(2, b) + load_rf(3, c), [enc_fma("fofma", 4, 1, 2, 3)],
            [("rf", 4), ("rf", 0)], [value, arith_fcsr(0, flags)]))
    return out


def cases_arith_faults():
    """Legality of the arithmetic family: `dst_rf0` for every rf destination
    and `dst_rd0` for the compare forms (spec/SimRISC-07 §2/§4)."""
    return [
        {"name": "fault_foadd_dst_rf0", "word": enc_arith("foadd", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_fosub_dst_rf0", "word": enc_arith("fosub", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_fomul_dst_rf0", "word": enc_arith("fomul", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftadd_dst_rf0", "word": enc_arith("ftadd", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_fomin_dst_rf0", "word": enc_arith("fomin", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_fomax_dst_rf0", "word": enc_arith("fomax", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_fofma_dst_rf0", "word": enc_fma("fofma", 0, 1, 2, 3),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftfma_dst_rf0", "word": enc_fma("ftfma", 0, 1, 2, 3),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_foqcmp_dst_rd0", "word": enc_arith("foqcmp", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_foscmp_dst_rd0", "word": enc_arith("foscmp", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3FF0000000000000)},
        {"name": "fault_ftqcmp_dst_rd0", "word": enc_arith("ftqcmp", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
        {"name": "fault_ftscmp_dst_rd0", "word": enc_arith("ftscmp", 0, 1, 2),
         "fault": "ILLI", "setup": load_rf(1, 0x3F800000)},
    ]


def cases_cvtfaults():
    """Legality of the conversion family: `encode_onehot` on the 15 rounded
    conversions, `encode_sbz` on the 3 exact ones, `dst_rd0`/`dst_rf0` and the
    two block copies' range/overlap rules (spec/SimRISC-07 §1.5)."""
    return [
        {"name": "fault_ft2it_onehot_zero", "word": enc_cvt("ft2it", 5, 1, 0x00),
         "fault": "ILLI", "setup": load_rf(1, 0x402CCCCD)},
        {"name": "fault_ft2it_onehot_three", "word": enc_cvt("ft2it", 5, 1, 0x03),
         "fault": "ILLI", "setup": load_rf(1, 0x402CCCCD)},
        {"name": "fault_fo2ft_onehot_21", "word": enc_cvt("fo2ft", 5, 1, 0x21),
         "fault": "ILLI", "setup": load_rf(1, 0x400599999999999A)},
        {"name": "fault_io2fo_onehot_40", "word": enc_cvt("io2fo", 6, 3, 0x40),
         "fault": "ILLI", "setup": sweep.load_rd(3, 7)},
        {"name": "fault_ft2fo_sbz", "word": enc_cvt("ft2fo", 4, 1, 0x01),
         "fault": "ILLI", "setup": load_rf(1, 0x402CCCCD)},
        {"name": "fault_it2fo_sbz", "word": enc_cvt("it2fo", 6, 3, 0x04),
         "fault": "ILLI", "setup": sweep.load_rd(3, 7)},
        {"name": "fault_ut2fo_sbz", "word": enc_cvt("ut2fo", 6, 3, 0x20),
         "fault": "ILLI", "setup": sweep.load_rd(3, 7)},
        {"name": "fault_ft2it_dst_rd0", "word": enc_cvt("ft2it", 0, 1, 0x04),
         "fault": "ILLI", "setup": load_rf(1, 0x402CCCCD)},
        {"name": "fault_ut2ft_dst_rf0", "word": enc_cvt("ut2ft", 0, 3, 0x04),
         "fault": "ILLI", "setup": sweep.load_rd(3, 7)},
        {"name": "fault_ft2fo_dst_rf0", "word": enc_cvt("ft2fo", 0, 1, 0),
         "fault": "ILLI", "setup": load_rf(1, 0x402CCCCD)},
        {"name": "fault_ft2ft_dst_rf0", "word": enc_cvt_ff("ft2ft", 0, 1, 1),
         "fault": "ILLI", "setup": load_rf(1, 0x402CCCCD)},
        {"name": "fault_ft2ft_mreg_zero", "word": enc_cvt_ff("ft2ft", 4, 1, 0),
         "fault": "ILLI", "setup": []},
        {"name": "fault_fo2fo_overlap",
         "word": enc_cvt_ff("fo2fo", 4, 3, 3), "fault": "ILLI", "setup": []},
        {"name": "fault_ft2ft_dst_range",
         "word": enc_cvt_ff("ft2ft", 62, 1, 4), "fault": "ILLI", "setup": []},
        {"name": "fault_ft2ft_src_range",
         "word": enc_cvt_ff("ft2ft", 1, 62, 4), "fault": "ILLI", "setup": []},
    ]


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
    ] + cases_cvtfaults() + cases_arith_faults() + cases_divrem_faults()


GROUPS = {
    "classify": cases_classify,
    "sign": cases_sign,
    "rfmem": cases_rfmem,
    "fcsr": cases_fcsr,
    "rf0ldt": cases_rf0ldt,
    "cvt_f2i_ft": cases_cvt_f2i_ft,
    "cvt_f2i_fo": cases_cvt_f2i_fo,
    "cvt_i2f_ft": cases_cvt_i2f_ft,
    "cvt_i2f_fo": cases_cvt_i2f_fo,
    "cvt_exact": cases_cvt_exact,
    "cvt_snan": cases_cvt_snan,
    "cvt_ff": cases_cvt_ff,
    "cvt_ff_ovf": cases_cvt_ff_ovf,
    "cvt_sat": cases_cvt_sat,
    "cvt_flags": cases_cvt_flags,
    # m12-013 arithmetic family (spec/SimRISC-07 §2/§4)
    "arith_add_ft": cases_arith_add_ft,
    "arith_add_fo": cases_arith_add_fo,
    "arith_mul_ft": cases_arith_mul_ft,
    "arith_mul_fo": cases_arith_mul_fo,
    "arith_fma_ft": cases_arith_fma_ft,
    "arith_fma_fo": cases_arith_fma_fo,
    "arith_cmp": cases_arith_cmp,
    "arith_minmax_ft": cases_arith_minmax_ft,
    "arith_minmax_fo": cases_arith_minmax_fo,
    "arith_flags": cases_arith_flags,
    "arith_nan": cases_arith_nan,
    "arith_fma_special": cases_arith_fma_special,
    "cmp_nan": cases_cmp_nan,
    # m12-014 divide / root / remainder (spec/SimRISC-07 §2.1/§2.2)
    "div_ft": cases_div_ft,
    "div_fo": cases_div_fo,
    "sqrt_ft": cases_sqrt_ft,
    "sqrt_fo": cases_sqrt_fo,
    "rem_ft": cases_rem_ft,
    "rem_fo": cases_rem_fo,
    "divrem_special": cases_divrem_special,
    "divrem_nan": cases_divrem_nan,
}

# Groups whose bytes are also compared against QEMU.  `rf0ldt` is excluded: the
# ld.t-rf0 case asserts the read-only qNaN field, which QEMU deliberately
# overrides (documented divergence, see `cases_rf0ldt`).
QEMU_GROUPS = ("classify", "sign", "rfmem", "fcsr",
               "cvt_f2i_ft", "cvt_f2i_fo", "cvt_i2f_ft", "cvt_i2f_fo",
               "cvt_exact", "cvt_ff", "cvt_sat", "cvt_flags",
               "arith_add_ft", "arith_add_fo", "arith_mul_ft",
               "arith_mul_fo", "arith_fma_ft", "arith_fma_fo", "arith_cmp",
               "arith_minmax_ft", "arith_minmax_fo", "arith_flags",
               "arith_fma_special", "cmp_nan",
               "div_ft", "div_fo", "sqrt_ft", "sqrt_fo", "rem_ft", "rem_fo",
               "divrem_special")


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
