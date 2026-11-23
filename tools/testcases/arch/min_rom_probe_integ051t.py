#!/usr/bin/env python3
"""Min ROM probe for INTEG-051t: hart-first asynchronous arbitration.

The probe checks the test-machine convention after ADR-0060:

  * ``doc`` (pure Python, no QEMU): the contract-see arbitration entry and the
    patch tree (no monitor/source pending bitmap, no ``async_enable``, one
    async entry function, masks read only inside it).
  * ``runtime`` (min-ROM, QEMU): every asynchronous source (TIMER ``1<<17``,
    PMEM_DMA ``1<<18``) is delivered to **cfx_hart** (cfxha 15) through its
    single supv vector ``cfx_hart cg9 rc6``; the frame/masks/pending all live
    in ``cfx_hart cg9``; masks are indexed by the *source* cfxha (15/32) while
    ``async_pending`` is indexed by the *cause id* (1<<17/1<<18).

Expectations are derived by hand from the frozen spec / contract:
  - spec/DADAO-12 §3.9 (cg9 register table), §5.2(四) (hart-first entry),
    §5.1/§5.3 (escape frame selector: imms18 in {0,1,2}, 3 => ILLI),
    §4.7 (cfx_hart TIMER/IMASK), §4.9 (cfx_pmem PMEM_DMA).
  - .tao/contracts/contract-see.md «统一异步中断仲裁（测试机约定，hart-first）».
  Never from the QEMU implementation.

Observation channels: everything (frame fields, pending bits, counters) is
checked in-program and reported through the semihosting SYS_EXIT code, so no
case depends on a ``-d cpu`` dump block.

Bootstrap (body runs in hmon / cfx3, hypv, via the shared prelude):
  1. open cfx_hart's supv deleg for cg8/cg9 (``hypv_cg_reg_deleg = 0x8``) and
     the same for cfx_smon (the sync handler for ILLI/CFXREG);
  2. install ``cfx_hart cg9 rc6`` = async handler, ``rc7`` = supv (2);
  3. install cfx_smon's supv vector = sync-exception recorder;
  4. poison cfx_hmon's hypv vector (any monitor hop would exit FAIL);
  5. leave the five cg9 source masks at their reset value (all-1); each case
     opens them through ``cfx2rc cfx_hart, cg9, rc8/rc11/rc12``.

Usage:
  min_rom_probe_integ051t.py --doc          # offline checks only
  min_rom_probe_integ051t.py                # offline + runtime
  min_rom_probe_integ051t.py --only NAME    # one check (used by run.sh --inject)
  min_rom_probe_integ051t.py --list
  min_rom_probe_integ051t.py --qemu PATH

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import re
import struct
import sys

# TESTCASES-091t: probe geometry from the single profile source.
_MACH_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if os.path.join(_MACH_REPO, "tools", "testcases", "lib") not in sys.path:
    sys.path.insert(0, os.path.join(_MACH_REPO, "tools", "testcases", "lib"))
import machine_profile as _machine_profile  # noqa: E402
import node_probe_prelude as _prelude  # noqa: E402

_MACH = _machine_profile.load(os.environ.get("DADAO_TEST_PROFILE") or "tiny")
RAM_BASE = _MACH.ram_base
RAM_END = _MACH.ram_end
SP = _MACH.sp
BOOTROM_BASE = _MACH.bootrom_base
ENTRY = _MACH.entry
EXIT_BLOCK = _MACH.exit_block

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_QEMU = _prelude.default_qemu()
QEMU = DEFAULT_QEMU
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_integ051t")
TIMEOUT = 120

CONTRACT_SEE = os.path.join(_REPO, ".tao", "contracts", "contract-see.md")
PATCH_DIR = os.path.join(_REPO, "components", "qemu", "patches", "target", "dadao")
PATCH_FILES = ("cpu.h.patch", "cpu.c.patch", "helper.c.patch")

# TESTCASES-094t §1: the body runs at RESET_PC + 0x1000 after the shared
# power -> hmon identity-PTW prelude.
ROM_BASE = _prelude.ROM_BASE

HART_HA = 15
PMEM_HA = 32
HMON_HA = 3
SMON_HA = 2
POWER_HA = 63
HART_CG = 8
PMEM_DMA_CG = 15

# cfx_hart cg9 (DADAO-12 §3.9): rc0..rc12.
RC_PREV_MODE, RC_PREV_CFX, RC_CAUSE_IP, RC_CAUSE_ID = 0, 1, 2, 3
RC_SAVED_GLOBAL, RC_PENDING, RC_VECTOR, RC_SWITCH = 4, 5, 6, 7
RC_GLOBAL_MASK = 8
RC_MODE_MASK_USER, RC_MODE_MASK_JAIL, RC_MODE_MASK_SUPV, RC_MODE_MASK_HYPV = 9, 10, 11, 12

# cg5 (sync frame) / cg4 counters.
CG5_CAUSE_ID_RC, CG5_CAUSE_IP_RC, CG5_CAUSE_INFO_RC, CG5_PENDING_RC = 2, 3, 4, 5
CG4_ASYNC_NUM_RC = 4
CG3_CFX_INTR_MASK_RC = 4
CG3_EXCP_VECTOR_RC = 10
DMA_SRC_RC, DMA_DST_RC, DMA_SIZE_RC, DMA_CTRL_RC, DMA_STATUS_RC = 0, 1, 2, 3, 4

TIMER = 1 << 17
PMEM_DMA = 1 << 18
ILLI = 1 << 8
CFXREG = 1 << 2
CTRL_START = 1 << 0
CTRL_IRQ_EN = 1 << 2
CTRL_ENABLE = 1 << 0
CTRL_IMASK = 1 << 1
ST_BUSY = 1 << 0
ST_DONE = 1 << 1
ST_ERROR = 1 << 2
ERR_PA_FAULT = 1 << 3
ERR_CODE_SHIFT = 3

PMEM_BASE = (PMEM_HA << 42) | 0x3FF00000000
DATA_PA = RAM_BASE + 0x4000

ALL1 = (1 << 64) - 1
# Five source masks: bit = *source cfxha*, 1 = masked.
MASK_TIMER_OPEN = ALL1 & ~(1 << HART_HA)   # TIMER (15) open, PMEM (32) masked
MASK_PMEM_OPEN = ALL1 & ~(1 << PMEM_HA)    # PMEM (32) open, TIMER (15) masked
MASK_BOTH = ALL1                           # both masked
# The contract's "open a cfx for supv" value: only the fixed bit3 stays set.
DELEG_OPEN = 0x8

EXIT_PASS = 0x00
EXIT_FAIL = 0x61   # guest FAIL segment (spec/Kaiwu §7.1)

# Timing-model-neutral bounds (TESTCASES-102t).
DELTA_NS = 10_000_000
WINDOW_NS = 1_000_000_000
MAX_WAIT = 4_000_000
MAX_DMA_WAIT = 300_000
ARM_RETRIES = 8

W_TMP = 19
W_NOW, W_CMP = 20, 21
W_DEAD, W_BOUND, W_MAX, W_WIT = 26, 27, 28, 29

# ROM layout: body-relative handler slots.
OFF_MAIN_HND = 0x2000
OFF_FRAME_HND = 0x2200
OFF_SMON_HND = 0x2400
OFF_POISON = 0x2600
ROM_END = 0x2800

# RAM state block (zero-filled; rb5 = RAM_BASE).
RAM_STATE = 0x3000
RAM_SEQ = RAM_STATE + 0x00           # total async deliveries
RAM_DEPTH = RAM_STATE + 0x08         # nesting depth
RAM_REENT = RAM_STATE + 0x10         # 1 if a delivery nested inside a handler
RAM_LAST_ID = RAM_STATE + 0x18
RAM_LAST_IP = RAM_STATE + 0x20
RAM_LAST_PREVM = RAM_STATE + 0x28
RAM_LAST_PREVC = RAM_STATE + 0x30
RAM_LAST_SAVED = RAM_STATE + 0x38
RAM_INSIDE_G = RAM_STATE + 0x40
RAM_TIMER_N = RAM_STATE + 0x48
RAM_PMEM_N = RAM_STATE + 0x50
RAM_SYNC_N = RAM_STATE + 0x58
RAM_SYNC_ID = RAM_STATE + 0x60
RAM_ILLI_N = RAM_STATE + 0x68
RAM_CFXREG_N = RAM_STATE + 0x70
RAM_ARM_IP = RAM_STATE + 0x78        # body address of the arm marker

SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = EXIT_BLOCK


# ---------------------------------------------------------------------------
# Encoders (contracts/opcodes.yaml)
# ---------------------------------------------------------------------------

def _rwii(op, ha, wp, imm):
    hb = (wp << 4) | ((imm >> 12) & 0xF)
    return (op << 24) | (ha << 18) | (hb << 12) | (((imm >> 6) & 0x3F) << 6) | (imm & 0x3F)


def set_zw_rd(rd, wp, imm): return _rwii(0x4C, rd, wp, imm & 0xFFFF)
def or_w_rd(rd, wp, imm):   return _rwii(0x48, rd, wp, imm & 0xFFFF)
def set_zw_rb(rb, wp, imm): return _rwii(0x4E, rb, wp, imm & 0xFFFF)
def or_w_rb(rb, wp, imm):   return _rwii(0x4A, rb, wp, imm & 0xFFFF)


def _rrii(op, ha, hb, off):
    imm = off & 0xFFF
    return (op << 24) | (ha << 18) | (hb << 12) | (((imm >> 6) & 0x3F) << 6) | (imm & 0x3F)


def ld_o(rd, rb, off):       return _rrii(0x20, rd, rb, off)
def st_o(rd, rb, off):       return _rrii(0x21, rd, rb, off)
def jump_iiii(imms24):       return (0x70 << 24) | (imms24 & 0xFFFFFF)
def add_si(rd, imms18):      return (0x59 << 24) | (rd << 18) | (imms18 & 0x3FFFF)
def cfx2rd(ha, cg, rc, rd):  return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def cfx2rc(ha, cg, rc, rd):  return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def trap(ha, immu18):        return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
def escape(ha, imms18):      return (0x7E << 24) | (ha << 18) | (imms18 & 0x3FFFF)
def swym():                  return 0x47880000


def _orrr(op, ha, hb, hc, hd):
    return (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd


def and_o(rdhb, rdhc, rdhd):
    return _orrr(0x40, 0x08, rdhb, rdhc, rdhd)


def cmp_uo(rdhb, rdhc, rdhd):
    """cmp.uo rdHB, rdHC, rdHD -> -1/0/1 (contracts/opcodes.yaml, ha 0x2A)."""
    return _orrr(0x40, 0x2A, rdhb, rdhc, rdhd)


def add_uo(lo, hi, src_a, src_b):
    """add.uo {hi, lo}, src_a, src_b: 128-bit unsigned add (carry -> hi)."""
    return _orrr(0x50, hi, lo, src_a, src_b)


def br_ne(rdha, rdhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return _orrr(0x6F, rdha, rdhb, hc, hd)


def br_eq(rdha, rdhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return _orrr(0x6E, rdha, rdhb, hc, hd)


def br_nz(rdha, imms18):  return (0x6B << 24) | (rdha << 18) | (imms18 & 0x3FFFF)
def br_z(rdha, imms18):   return (0x6A << 24) | (rdha << 18) | (imms18 & 0x3FFFF)
def br_nn(rdha, imms18):  return (0x69 << 24) | (rdha << 18) | (imms18 & 0x3FFFF)


def load_rd(rd, val):
    val &= 0xFFFF_FFFF_FFFF_FFFF
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rd(rd, wp, x))
    return out


def load_rb(rb, val):
    val &= 0xFFFF_FFFF_FFFF_FFFF
    out = [set_zw_rb(rb, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rb(rb, wp, x))
    return out


def exit_seq(code):
    """Semihosting SYS_EXIT with the profile `exit_block` (TESTCASES-094t §0)."""
    return _prelude.exit_seq(code)


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


class Asm:
    """Tiny label-based assembler (word granularity)."""

    def __init__(self):
        self.words = []
        self.labels = {}
        self.fixups = []

    def emit(self, *ws):
        self.words.extend(ws)

    def mark(self, name):
        if name in self.labels:
            raise ValueError("duplicate label %r" % name)
        self.labels[name] = len(self.words)

    def br(self, kind, rd_a, rd_b, label):
        self.fixups.append((len(self.words), kind, rd_a, rd_b, label))
        self.words.append(0)

    def resolve(self):
        for idx, kind, rd_a, rd_b, label in self.fixups:
            if label not in self.labels:
                raise ValueError("undefined label %r" % label)
            off = self.labels[label] - idx
            if kind == "eq":
                self.words[idx] = br_eq(rd_a, rd_b, off)
            elif kind == "ne":
                self.words[idx] = br_ne(rd_a, rd_b, off)
            elif kind == "nz":
                self.words[idx] = br_nz(rd_a, off)
            elif kind == "z":
                self.words[idx] = br_z(rd_a, off)
            elif kind == "nn":
                self.words[idx] = br_nn(rd_a, off)
            else:
                raise ValueError("bad branch kind %r" % kind)
        return self.words


# ---------------------------------------------------------------------------
# Async handler (cfx_hart cg9 frame) + sync recorder + poison
# ---------------------------------------------------------------------------

def _inc(a, off, rd):
    a.emit(ld_o(rd, 5, off))
    a.emit(add_si(rd, 1))
    a.emit(st_o(rd, 5, off))


def build_async_handler(extra=None):
    """Record the cg9 frame, then escape back to ``async_cause_ip``.

    Registers 30..39 are handler scratch; the body only uses 5..25.
    `extra` words run inside the frame after the recording (ILLI/CFXREG
    encoding cases).  Each word must not clobber rd30..rd39 expectations.
    """
    a = Asm()
    a.emit(cfx2rd(HART_HA, 9, RC_CAUSE_ID, 30))
    a.emit(cfx2rd(HART_HA, 9, RC_CAUSE_IP, 31))
    a.emit(cfx2rd(HART_HA, 9, RC_PREV_MODE, 32))
    a.emit(cfx2rd(HART_HA, 9, RC_PREV_CFX, 33))
    a.emit(cfx2rd(HART_HA, 9, RC_SAVED_GLOBAL, 34))
    a.emit(cfx2rd(HART_HA, 9, RC_GLOBAL_MASK, 35))
    a.emit(ld_o(36, 5, RAM_SEQ))
    a.emit(ld_o(37, 5, RAM_DEPTH))
    okd = "depth0_%d" % len(a.words)
    a.br("z", 37, 0, okd)
    a.emit(*load_rd(38, 1))
    a.emit(st_o(38, 5, RAM_REENT))
    a.mark(okd)
    a.emit(add_si(37, 1))
    a.emit(st_o(37, 5, RAM_DEPTH))
    a.emit(add_si(36, 1))
    a.emit(st_o(36, 5, RAM_SEQ))
    a.emit(st_o(30, 5, RAM_LAST_ID))
    a.emit(st_o(31, 5, RAM_LAST_IP))
    a.emit(st_o(32, 5, RAM_LAST_PREVM))
    a.emit(st_o(33, 5, RAM_LAST_PREVC))
    a.emit(st_o(34, 5, RAM_LAST_SAVED))
    a.emit(st_o(35, 5, RAM_INSIDE_G))
    # Per-source counter: TIMER (1<<17) or PMEM_DMA (1<<18).
    a.emit(*load_rd(38, TIMER))
    timer_lbl = "src_t_%d" % len(a.words)
    after_lbl = "src_a_%d" % len(a.words)
    a.br("eq", 30, 38, timer_lbl)
    _inc(a, RAM_PMEM_N, 36)
    a.br("z", 0, 0, after_lbl)
    a.mark(timer_lbl)
    _inc(a, RAM_TIMER_N, 36)
    a.mark(after_lbl)
    if extra:
        a.emit(*extra)
    a.emit(*load_rd(36, 0))
    a.emit(st_o(36, 5, RAM_DEPTH))
    a.emit(escape(HART_HA, 2))          # cg9 frame, offset 0
    return a.resolve()


def build_frame_handler():
    """PMEM handler that arms TIMER inside the live cg9 frame (no-nesting)."""
    a = Asm()
    body = build_async_handler()[:-1]   # drop the trailing escape
    a.emit(*body)
    # Arm TIMER for now+500 while cause_id != 0 (event arrival mode = supv =>
    # the event is filtered by cg9 rc11, which the body opened).
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 36))
    a.emit(add_si(36, 500))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 36))
    a.emit(*load_rd(36, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 36))
    a.emit(*load_rd(37, 4000))
    tag = "frame_delay"
    a.mark(tag)
    a.emit(add_si(37, -1))
    a.br("nz", 37, 0, tag)
    # Inside the frame the second source must not be delivered ...
    a.emit(ld_o(38, 5, RAM_TIMER_N))
    ok0 = "frame_nohart"
    a.br("z", 38, 0, ok0)
    a.emit(*exit_seq(0x71))
    a.mark(ok0)
    # ... but its pending bit (cause-id bit 17) must be recorded.
    a.emit(cfx2rd(HART_HA, 9, RC_PENDING, 38))
    a.emit(*load_rd(39, TIMER))
    a.emit(and_o(38, 38, 39))
    ok1 = "frame_pending"
    a.br("nz", 38, 0, ok1)
    a.emit(*exit_seq(0x72))
    a.mark(ok1)
    a.emit(escape(HART_HA, 2))
    return a.resolve()


def build_smon_handler():
    """cfx_smon supv vector: record a sync cause and skip the instruction."""
    a = Asm()
    a.emit(cfx2rd(SMON_HA, 5, CG5_CAUSE_ID_RC, 30))
    a.emit(cfx2rd(SMON_HA, 5, CG5_CAUSE_IP_RC, 31))
    _inc(a, RAM_SYNC_N, 32)
    a.emit(st_o(30, 5, RAM_SYNC_ID))
    a.emit(*load_rd(33, ILLI))
    illi_lbl = "s_illi_%d" % len(a.words)
    after_illi = "s_ai_%d" % len(a.words)
    a.br("eq", 30, 33, illi_lbl)
    a.emit(*load_rd(33, CFXREG))
    cfxreg_lbl = "s_cfxr_%d" % len(a.words)
    after_all = "s_all_%d" % len(a.words)
    a.br("eq", 30, 33, cfxreg_lbl)
    a.br("z", 0, 0, after_all)
    a.mark(illi_lbl)
    _inc(a, RAM_ILLI_N, 32)
    a.br("z", 0, 0, after_all)
    a.mark(cfxreg_lbl)
    _inc(a, RAM_CFXREG_N, 32)
    a.mark(after_all)
    a.mark(after_illi)
    a.emit(escape(SMON_HA, 1))          # cg5 frame, +4: skip the bad instruction
    return a.resolve()


def build_poison():
    """cfx_hmon hypv vector: any monitor hop is a failure (never reached)."""
    a = Asm()
    a.emit(*exit_seq(0x7E))
    return a.resolve()


def handlers(main_extra=None, frame=False):
    return {
        OFF_MAIN_HND: build_async_handler(main_extra),
        OFF_FRAME_HND: build_frame_handler(),
        OFF_SMON_HND: build_smon_handler(),
        OFF_POISON: build_poison(),
    }


# ---------------------------------------------------------------------------
# Program helpers (body runs in hmon / cfx3, hypv)
# ---------------------------------------------------------------------------

def hmon_addr(off):
    """Body-relative address inside the shared prelude's body image."""
    return ROM_BASE + off


def ram_ld(a, off, rd):
    a.emit(ld_o(rd, 5, off))


def ram_st(a, off, rd):
    a.emit(st_o(rd, 5, off))


def need_eq(a, rd, want, code, tag):
    """Exit `code` unless rd == want (each check has its own FAIL code)."""
    ok = "eq_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(24, want))
    a.br("eq", rd, 24, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def need_same(a, rd_a, rd_b, code, tag):
    ok = "same_%s_%d" % (tag, len(a.words))
    a.br("eq", rd_a, rd_b, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def need_mask_set(a, rd, mask, code, tag):
    ok = "ms_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(24, mask))
    a.emit(and_o(23, rd, 24))
    a.br("nz", 23, 0, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def need_mask_clr(a, rd, mask, code, tag):
    ok = "mc_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(24, mask))
    a.emit(and_o(23, rd, 24))
    a.br("z", 23, 0, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def async_open(a):
    """Open the global + hypv/supv source masks (body is hypv; handler supv)."""
    a.emit(*load_rd(22, 0))
    for rc in (RC_GLOBAL_MASK, RC_MODE_MASK_SUPV, RC_MODE_MASK_HYPV):
        a.emit(cfx2rc(HART_HA, 9, rc, 22))


def set_global_mask(a, mask):
    a.emit(*load_rd(22, mask))
    a.emit(cfx2rc(HART_HA, 9, RC_GLOBAL_MASK, 22))


def set_mode_mask(a, rc, mask):
    a.emit(*load_rd(22, mask))
    a.emit(cfx2rc(HART_HA, 9, rc, 22))


def release_frame(a, clear_pending=True):
    """Software frame release: cause_id = 0 (and optionally pending = 0)."""
    a.emit(*load_rd(22, 0))
    if clear_pending:
        a.emit(cfx2rc(HART_HA, 9, RC_PENDING, 22))
    a.emit(cfx2rc(HART_HA, 9, RC_CAUSE_ID, 22))


def pending_rd(a, rd):
    a.emit(cfx2rd(HART_HA, 9, RC_PENDING, rd))


def cause_id_rd(a, rd):
    a.emit(cfx2rd(HART_HA, 9, RC_CAUSE_ID, rd))


def timer_now(a, rd):
    a.emit(cfx2rd(HART_HA, HART_CG, 2, rd))           # cycle == cfx_time value


def dma_setup(a, src, dst, size, ctrl, rd=22):
    for rc, val in ((DMA_SRC_RC, src), (DMA_DST_RC, dst),
                    (DMA_SIZE_RC, size), (DMA_CTRL_RC, ctrl)):
        a.emit(*load_rd(rd, val))
        a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, rc, rd))


def dma_start(a, irq_en=True, dst=DATA_PA):
    dma_setup(a, PMEM_BASE, dst, 8, CTRL_START | (CTRL_IRQ_EN if irq_en else 0))


def dma_status_clear(a):
    a.emit(*load_rd(22, ST_DONE | ST_ERROR))
    a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 22))


def dma_wait(a, rd=6):
    poll = "dma_poll_%d" % len(a.words)
    done = poll + "_done"
    a.emit(*load_rd(18, 1))
    a.emit(*load_rd(20, MAX_DMA_WAIT))
    a.mark(poll)
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, rd))
    a.emit(and_o(rd, rd, 18))
    a.br("z", rd, 0, done)
    a.emit(add_si(20, -1))
    a.br("nz", 20, 0, poll)
    a.emit(*exit_seq(0x7D))                          # DMA never completed
    a.mark(done)


def delay_loop(a, count, tag, rd=23):
    a.emit(*load_rd(rd, count))
    head = "dl_%s_%d" % (tag, len(a.words))
    tail = head + "_end"
    a.mark(head)
    a.br("z", rd, 0, tail)
    a.emit(add_si(rd, -1))
    a.br("nz", rd, 0, head)
    a.mark(tail)


# ---------------------------------------------------------------------------
# Model-neutral timing helpers (TESTCASES-102t)
# ---------------------------------------------------------------------------

def _count_cond(off, want):
    def emit(a, rd):
        a.emit(ld_o(rd, 5, off))
        a.emit(*load_rd(W_TMP, want))
        a.emit(cmp_uo(rd, rd, W_TMP))

    return emit


def _mask_cond(read_reg, mask):
    def emit(a, rd):
        read_reg(a, rd)
        a.emit(*load_rd(W_TMP, mask))
        a.emit(and_o(rd, rd, W_TMP))

    return emit


def _set_bound(a, deadline_rd):
    a.emit(*load_rd(W_TMP, WINDOW_NS))
    a.emit(add_uo(W_BOUND, W_CMP, deadline_rd, W_TMP))


def settle_bound(a):
    timer_now(a, W_NOW)
    _set_bound(a, W_NOW)


def check_quiet(a, deadline_rd, cond, zero_is_met, code, tag):
    done = "q_%s" % tag
    cond(a, W_WIT)
    timer_now(a, W_NOW)
    a.emit(cmp_uo(W_CMP, W_NOW, deadline_rd))
    a.br("nn", W_CMP, 0, done)
    a.br("nz" if zero_is_met else "z", W_WIT, 0, done)
    a.emit(*exit_seq(code))
    a.mark(done)


def wait_cond(a, bound_rd, cond, zero_is_met, tag, code_late, code_lost):
    head = "w_%s" % tag
    got = head + "_got"
    lost = head + "_lost"
    ok = head + "_ok"
    a.emit(*load_rd(W_MAX, MAX_WAIT))
    a.mark(head)
    timer_now(a, W_NOW)
    cond(a, W_WIT)
    a.br("z" if zero_is_met else "nz", W_WIT, 0, got)
    a.emit(cmp_uo(W_CMP, W_NOW, bound_rd))
    a.br("nn", W_CMP, 0, lost)
    a.emit(add_si(W_MAX, -1))
    a.br("nz", W_MAX, 0, head)
    a.mark(lost)
    a.emit(*exit_seq(code_lost))
    a.mark(got)
    a.emit(cmp_uo(W_CMP, W_NOW, bound_rd))
    a.emit(*load_rd(W_TMP, 1))
    a.br("ne", W_CMP, W_TMP, ok)                     # now <= bound
    a.emit(*exit_seq(code_late))
    a.mark(ok)


def timer_arm_window(a, delta=DELTA_NS, ctrl=CTRL_ENABLE, base_hart=0,
                     base_seq=0, tag="t"):
    """Cancel, then arm cmp = now + delta; leaves W_DEAD/W_BOUND."""
    retry = "tw_%s_reset" % tag
    done = "tw_%s_ok" % tag
    a.emit(*load_rd(W_MAX, ARM_RETRIES))
    a.mark(retry)
    a.emit(*load_rd(W_TMP, ALL1))                    # cmp = ~0: cancel
    a.emit(cfx2rc(HART_HA, HART_CG, 4, W_TMP))
    a.emit(*load_rd(W_TMP, 0))                       # ctrl = 0
    a.emit(cfx2rc(HART_HA, HART_CG, 5, W_TMP))
    a.emit(cfx2rc(HART_HA, 9, RC_PENDING, W_TMP))    # clear pending (cg9 rc5)
    a.emit(*load_rd(W_TMP, base_hart))               # witness baseline
    a.emit(st_o(W_TMP, 5, RAM_TIMER_N))
    a.emit(*load_rd(W_TMP, base_seq))
    a.emit(st_o(W_TMP, 5, RAM_SEQ))
    a.emit(*load_rd(W_TMP, ROM_BASE + 0))            # arm marker (low bound)
    a.emit(st_o(W_TMP, 5, RAM_ARM_IP))
    timer_now(a, W_NOW)
    a.emit(*load_rd(W_TMP, delta))
    a.emit(add_uo(W_DEAD, W_CMP, W_NOW, W_TMP))      # W_DEAD = now + delta
    a.emit(cfx2rc(HART_HA, HART_CG, 4, W_DEAD))
    _set_bound(a, W_DEAD)
    a.emit(*load_rd(W_TMP, ctrl))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, W_TMP))
    timer_now(a, W_CMP)                              # still in the future?
    a.emit(cmp_uo(W_CMP, W_CMP, W_DEAD))
    a.emit(*load_rd(W_TMP, 1))
    a.br("ne", W_CMP, W_TMP, done)
    a.emit(add_si(W_MAX, -1))
    a.br("nz", W_MAX, 0, retry)
    a.emit(*exit_seq(0x7A))
    a.mark(done)


# ---------------------------------------------------------------------------
# QEMU runner + bootstrap
# ---------------------------------------------------------------------------

def run(rom, dump=False):
    rc, log = _prelude.run(rom, WORKDIR, qemu=QEMU, timeout=TIMEOUT,
                           dump=dump)
    if not dump:
        log = ""
    return rc, log, ""


def build_rom(prog, hnd=None, vector_off=OFF_MAIN_HND):
    return _prelude.build_rom(prog, hnd, hmon_extra=hmon_setup(vector_off))


def hmon_setup(vector_off=OFF_MAIN_HND):
    ins = load_rb(5, RAM_BASE)                        # handler state block base
    # cfx_hart / cfx_smon: open the supv deleg for cg8/cg9 (and cg5), i.e. the
    # contract's "0x8" whole-group opening (bit3 stays hardware-fixed 1).
    ins += load_rd(21, DELEG_OPEN)
    ins += [cfx2rc(HART_HA, 3, 12, 21), cfx2rc(SMON_HA, 3, 12, 21)]
    # cfx_smon supv vector: sync-exception recorder (ILLI/CFXREG from the
    # async handler runs in supv, so this is the current-mode monitor).
    ins += load_rd(21, hmon_addr(OFF_SMON_HND))
    ins += [cfx2rc(SMON_HA, 2, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart cg9: single supv async vector; masks stay at reset (all-1).
    ins += load_rd(21, hmon_addr(vector_off))
    ins += [cfx2rc(HART_HA, 9, RC_VECTOR, 21)]
    ins += load_rd(21, 2)
    ins += [cfx2rc(HART_HA, 9, RC_SWITCH, 21)]
    # Any async delivery to cfx_hmon (monitor hop) => poison => FAIL.
    ins += load_rd(21, hmon_addr(OFF_POISON))
    ins += [cfx2rc(HMON_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    return ins


# ---------------------------------------------------------------------------
# Runtime cases
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc, dump=False):
    def deco(fn):
        CASES.append((name, desc, fn, dump))
        return fn
    return deco


@case("cg9_reset_defaults",
      "cg9 reset: frame/pending 0, switch=supv, five masks all-1")
def _cg9_reset_defaults():
    a = Asm()
    for rc, want, code in ((RC_PREV_MODE, 0, 0x001), (RC_PREV_CFX, 0, 0x002),
                           (RC_CAUSE_IP, 0, 0x003), (RC_CAUSE_ID, 0, 0x004),
                           (RC_SAVED_GLOBAL, 0, 0x005), (RC_PENDING, 0, 0x006)):
        a.emit(cfx2rd(HART_HA, 9, rc, 5))
        need_eq(a, 5, want, code, "d%d" % rc)
    a.emit(cfx2rd(HART_HA, 9, RC_SWITCH, 5))
    need_eq(a, 5, 2, 0x007, "swmode")
    a.emit(cfx2rd(HART_HA, 9, RC_VECTOR, 5))
    need_eq(a, 5, hmon_addr(OFF_MAIN_HND), 0x008, "vector")
    for rc, code in ((RC_GLOBAL_MASK, 0x009), (RC_MODE_MASK_USER, 0x00A),
                     (RC_MODE_MASK_JAIL, 0x00B), (RC_MODE_MASK_SUPV, 0x00C),
                     (RC_MODE_MASK_HYPV, 0x00D)):
        a.emit(cfx2rd(HART_HA, 9, rc, 6))
        need_eq(a, 6, ALL1, code, "m%d" % rc)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("timer_frame_hart",
      "TIMER -> cfx_hart cg9: cause 1<<17, prev hypv/hmon, ip aligned, escape")
def _timer_frame_hart():
    a = Asm()
    async_open(a)
    timer_arm_window(a, tag="tfh")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "tfh", 0x011, 0x012)
    ram_ld(a, RAM_LAST_ID, 5)
    need_eq(a, 5, TIMER, 0x013, "cid")
    ram_ld(a, RAM_LAST_PREVM, 6)
    need_eq(a, 6, 3, 0x014, "prev_mode")
    ram_ld(a, RAM_LAST_PREVC, 7)
    need_eq(a, 7, HMON_HA, 0x015, "prev_cfx")
    ram_ld(a, RAM_LAST_SAVED, 8)
    need_eq(a, 8, 0, 0x016, "saved_mask")
    ram_ld(a, RAM_INSIDE_G, 9)
    need_eq(a, 9, ALL1, 0x017, "inside_global")
    # cause_ip: 4-byte aligned, inside the body, at/after the arm marker.
    ram_ld(a, RAM_LAST_IP, 10)
    a.emit(*load_rd(24, 3))
    a.emit(and_o(23, 10, 24))
    need_eq(a, 23, 0, 0x018, "ip_align")
    need_mask_set(a, 10, ALL1, 0x019, "ip_nonzero")
    need_mask_clr(a, 10, ~((ROM_BASE + 0x1000) - 1), 0x01A, "ip_range")
    ram_ld(a, RAM_ARM_IP, 11)
    a.emit(cmp_uo(24, 10, 11))
    a.br("nn", 24, 0, "ip_after_arm")
    a.emit(*exit_seq(0x01B))
    a.mark("ip_after_arm")
    # escape restored the global mask (saved value 0); frame still live.
    a.emit(cfx2rd(HART_HA, 9, RC_GLOBAL_MASK, 12))
    need_eq(a, 12, 0, 0x01C, "global_restored")
    cause_id_rd(a, 13)
    need_eq(a, 13, TIMER, 0x01D, "escape_keeps_cause")
    # Restored run mode = hypv: cg3 is hypv-only (CFXREG otherwise); restored
    # cfx = hmon: cfx_pmem's hypv row only allows source hmon (bit3) by reset.
    a.emit(*load_rd(14, 0))
    a.emit(cfx2rd(HART_HA, 3, 0, 14))
    need_mask_set(a, 14, 1, 0x01E, "mode_hypv")
    a.emit(cfx2rd(PMEM_HA, 4, CG4_ASYNC_NUM_RC, 15))
    need_eq(a, 15, 0, 0x01F, "cfx_hmon")
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("pmem_frame_hart",
      "PMEM_DMA -> cfx_hart cg9, not the source cfx or a monitor")
def _pmem_frame_hart():
    a = Asm()
    async_open(a)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "pfh", 0x021, 0x022)
    ram_ld(a, RAM_LAST_ID, 5)
    need_eq(a, 5, PMEM_DMA, 0x023, "cid")
    ram_ld(a, RAM_LAST_PREVM, 6)
    need_eq(a, 6, 3, 0x024, "prev_mode")
    ram_ld(a, RAM_LAST_PREVC, 7)
    need_eq(a, 7, HMON_HA, 0x025, "prev_cfx")
    # Delivery target witness: neither the source cfx nor the monitor entered.
    a.emit(cfx2rd(PMEM_HA, 4, CG4_ASYNC_NUM_RC, 8))
    need_eq(a, 8, 0, 0x026, "src_no_entry")
    a.emit(cfx2rd(HMON_HA, 4, CG4_ASYNC_NUM_RC, 9))
    need_eq(a, 9, 0, 0x027, "monitor_no_entry")
    cause_id_rd(a, 10)
    need_eq(a, 10, PMEM_DMA, 0x028, "escape_keeps_cause")
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("mask_index_source",
      "mask bit = source cfxha (15), not the cause id bit (17)")
def _mask_index_source():
    a = Asm()
    async_open(a)
    # Phase 1: source bit15 open, cause-id bit17 masked -> must still deliver.
    set_global_mask(a, ALL1 & ~(1 << HART_HA))
    timer_arm_window(a, tag="m17")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "mi1", 0x031, 0x032)
    release_frame(a)
    # Phase 2: source bit15 masked (bit17 open) -> blocks; pending keeps 1<<17.
    set_global_mask(a, ALL1 & ~(1 << 17))
    timer_arm_window(a, base_seq=1, base_hart=1, tag="m15")
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, TIMER), False, "mi2", 0x033, 0x034)
    ram_ld(a, RAM_TIMER_N, 5)
    need_eq(a, 5, 1, 0x035, "blocked")
    pending_rd(a, 6)
    need_mask_set(a, 6, TIMER, 0x036, "pend17")
    need_mask_clr(a, 6, 1 << 15, 0x037, "pend_not_maskbit")
    # Phase 3: release the mask -> delivery.
    set_global_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 2), True, "mi3", 0x038, 0x039)
    pending_rd(a, 7)
    need_mask_clr(a, 7, TIMER, 0x03A, "pend_cleared")
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("mode_mask_row",
      "mode row = run mode at arrival: hypv(rc12) blocks, supv(rc11) does not")
def _mode_mask_row():
    a = Asm()
    async_open(a)
    # Phase 1: supv row fully masked, hypv row open; body is hypv -> delivers.
    set_mode_mask(a, RC_MODE_MASK_SUPV, ALL1)
    timer_arm_window(a, tag="mm1")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "mm1", 0x041, 0x042)
    release_frame(a)
    # Phase 2: hypv row masked -> blocks with pending; supv row open.
    set_mode_mask(a, RC_MODE_MASK_SUPV, 0)
    set_mode_mask(a, RC_MODE_MASK_HYPV, 1 << HART_HA)
    timer_arm_window(a, base_seq=1, base_hart=1, tag="mm2")
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, TIMER), False, "mm2", 0x043, 0x044)
    ram_ld(a, RAM_TIMER_N, 5)
    need_eq(a, 5, 1, 0x045, "blocked_hypv")
    set_mode_mask(a, RC_MODE_MASK_HYPV, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 2), True, "mm3", 0x046, 0x047)
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("pending_or_order",
      "pending bits 1<<17/1<<18 (OR); both open => source 15 first, then 32")
def _pending_or_order():
    a = Asm()
    async_open(a)
    set_global_mask(a, MASK_BOTH)
    dma_status_clear(a)
    timer_arm_window(a, tag="poo")
    dma_start(a)
    dma_wait(a)
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, TIMER), False, "poo0",
              0x04F, 0x050)
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, PMEM_DMA), False, "poo1",
              0x051, 0x052)
    delay_loop(a, 400, "settle")
    pending_rd(a, 5)
    need_mask_set(a, 5, TIMER, 0x053, "p17")
    need_mask_set(a, 5, PMEM_DMA, 0x054, "p18")
    need_mask_clr(a, 5, 1 << 15, 0x055, "no_maskbits")
    ram_ld(a, RAM_SEQ, 6)
    need_eq(a, 6, 0, 0x056, "none_yet")
    set_global_mask(a, 0)                             # single write, both ready
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "poo2", 0x057, 0x058)
    ram_ld(a, RAM_PMEM_N, 7)
    need_eq(a, 7, 0, 0x059, "pmem_held")
    pending_rd(a, 8)
    need_mask_clr(a, 8, TIMER, 0x05A, "p17_cleared")
    need_mask_set(a, 8, PMEM_DMA, 0x05B, "p18_kept")
    release_frame(a, clear_pending=False)             # keep pending 18
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "poo3", 0x05C, 0x05D)
    ram_ld(a, RAM_SEQ, 9)
    need_eq(a, 9, 2, 0x05E, "both_once")
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("dedup_same_source",
      "two PMEM completions while masked merge into one pending bit/delivery")
def _dedup_same_source():
    a = Asm()
    async_open(a)
    set_global_mask(a, MASK_BOTH)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    pending_rd(a, 5)
    need_mask_set(a, 5, PMEM_DMA, 0x061, "pending")
    ram_ld(a, RAM_SEQ, 6)
    need_eq(a, 6, 0, 0x062, "none_yet")
    set_global_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "dd", 0x063, 0x064)
    release_frame(a)
    delay_loop(a, 5000, "still")
    ram_ld(a, RAM_PMEM_N, 7)
    need_eq(a, 7, 1, 0x065, "still_once")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("no_nest_frame",
      "TIMER inside a live PMEM cfx_hart frame => pending only, delivered after escape")
def _no_nest_frame():
    a = Asm()
    async_open(a)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "nn1", 0x071, 0x072)
    ram_ld(a, RAM_SEQ, 5)
    need_eq(a, 5, 1, 0x073, "one_frame")
    ram_ld(a, RAM_REENT, 6)
    need_eq(a, 6, 0, 0x074, "no_reent")
    # The frame handler already proved pending 17 was recorded; here the cg9
    # frame is still live (escape does not clear it) and pending 17 is kept.
    pending_rd(a, 7)
    need_mask_set(a, 7, TIMER, 0x075, "pending17")
    # Software moves the vector back to the plain handler before releasing the
    # frame; the parked TIMER then enters through it (the frame handler would
    # arm another timer and treat itself as a first frame).
    a.emit(*load_rd(22, hmon_addr(OFF_MAIN_HND)))
    a.emit(cfx2rc(HART_HA, 9, RC_VECTOR, 22))
    release_frame(a, clear_pending=False)             # frame release => deliver
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "nn2", 0x076, 0x077)
    ram_ld(a, RAM_SEQ, 8)
    need_eq(a, 8, 2, 0x078, "two_total")
    ram_ld(a, RAM_REENT, 9)
    need_eq(a, 9, 0, 0x079, "no_nesting")
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers(), vector_off=OFF_FRAME_HND), {"exit": EXIT_PASS}


@case("release_reenter",
      "frame live => pending only; write cause_id=0 + pending=0 => quiet; new event enters")
def _release_reenter():
    a = Asm()
    async_open(a)
    timer_arm_window(a, tag="rr1")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "rr1", 0x081, 0x082)
    cause_id_rd(a, 5)
    need_eq(a, 5, TIMER, 0x083, "cause_kept")
    # Second event with the frame still live: pending only, no entry.
    timer_arm_window(a, base_seq=1, base_hart=1, tag="rr2")
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, TIMER), False, "rr2", 0x084, 0x085)
    ram_ld(a, RAM_TIMER_N, 6)
    need_eq(a, 6, 1, 0x086, "no_entry")
    # Release: cause_id = 0 and clear the pending bit.  Nothing may enter.
    release_frame(a)
    delay_loop(a, 2000, "quiet")
    ram_ld(a, RAM_TIMER_N, 7)
    need_eq(a, 7, 1, 0x087, "quiet_after_release")
    # A new event after the release enters again.
    timer_arm_window(a, base_seq=1, base_hart=1, tag="rr3")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 2), True, "rr3", 0x088, 0x089)
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


def _ill_extra():
    """Bad escape encodings: 3 (cg9 +4) and 4 ([17:2] SBZ nonzero)."""
    return [escape(HART_HA, 3), escape(HART_HA, 4)]


@case("escape_ill",
      "escape imms18=3 and [17:2]!=0 => ILLI in supv (recorded), then normal escape")
def _escape_ill():
    a = Asm()
    async_open(a)
    timer_arm_window(a, tag="ei")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "ei", 0x091, 0x092)
    ram_ld(a, RAM_ILLI_N, 5)
    need_eq(a, 5, 2, 0x093, "illi_twice")
    ram_ld(a, RAM_CFXREG_N, 6)
    need_eq(a, 6, 0, 0x094, "no_cfxreg")
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers(main_extra=_ill_extra())), {"exit": EXIT_PASS}


def _reserved_extra():
    """Reserved cg9 rc13/rc15: each access must raise CFXREG."""
    return [cfx2rd(HART_HA, 9, 13, 39), cfx2rd(HART_HA, 9, 15, 39)]


@case("cg9_reserved",
      "cg9 rc13/rc15 are reserved: read => CFXREG (not silently 0)")
def _cg9_reserved():
    a = Asm()
    async_open(a)
    timer_arm_window(a, tag="cr")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "cr", 0x0A1, 0x0A2)
    ram_ld(a, RAM_CFXREG_N, 5)
    need_eq(a, 5, 2, 0x0A3, "cfxreg_twice")
    ram_ld(a, RAM_ILLI_N, 6)
    need_eq(a, 6, 0, 0x0A4, "no_illi")
    release_frame(a)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers(main_extra=_reserved_extra())), {"exit": EXIT_PASS}


# ---------------------------------------------------------------------------
# Offline cases: contract entry + patch-tree structure
# ---------------------------------------------------------------------------

DOC_CASE = "doc_shape"
STRUCT_CASE = "no_async_enable"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _contract_entry(text):
    """Return the «统一异步中断仲裁» bullet body (empty string when absent)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("- **统一异步中断仲裁"):
            body = [line]
            for nxt in lines[i + 1:]:
                if nxt.startswith("- ") or nxt.startswith("#"):
                    break
                body.append(nxt)
            return "\n".join(body)
    return ""


def _patch_text():
    return "\n".join(_read(os.path.join(PATCH_DIR, p)) for p in PATCH_FILES)


def _helper_source():
    """Patch body of helper.c with the leading '+' removed."""
    raw = _read(os.path.join(PATCH_DIR, "helper.c.patch"))
    return "\n".join(l[1:] if l.startswith("+") and not l.startswith("+++") else l
                     for l in raw.splitlines())


def _function_body(src, signature):
    """Body of the *definition* line matching `signature` (skips prototypes)."""
    lines = src.splitlines()
    start = None
    for i, line in enumerate(lines):
        if signature not in line:
            continue
        defn = False
        for probe in lines[i:i + 8]:
            if "{" in probe:
                defn = True
                break
            if ";" in probe:
                break
        if defn:
            start = i
            break
    if start is None:
        return ""
    depth = 0
    seen_open = False
    out = []
    for line in lines[start:]:
        out.append(line)
        depth += line.count("{") - line.count("}")
        if "{" in line:
            seen_open = True
        if seen_open and depth == 0:
            break
    return "\n".join(out)


def run_doc():
    failures = []

    def check(name, ok, detail):
        print("[%s] %-40s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            failures.append(name)

    contract = _read(CONTRACT_SEE)
    entry = _contract_entry(contract)
    check("contract_arbitration_entry", bool(entry),
          "«统一异步中断仲裁» bullet found" if entry else "MISSING bullet")
    for token, why in (
            ("pending", "delivery pending is defined"),
            ("cfx_hart cg9 rc5", "the single pending record is cg9 rc5"),
            ("源 cause id", "pending bit = source cause id"),
            ("投递目标 = `cfx_hart`", "hart-first delivery target named"),
            ("升序", "lowest source cfxha first"),
            ("单层", "single-layer delivery"),
            ("补投", "mask release re-delivers"),
            ("合并", "same-source duplicate events merge"),
            ("不引入", "no async_enable-style gate"),
            ("async_enable", "async_enable named as not introduced"),
            ("ADR-0060", "hart-first decision cited"),
    ):
        check("entry_%s" % token.replace(" ", "_").replace("`", ""), token in entry, why)

    patches = _patch_text()
    check("patch_no_monitor_pending", "env->cfx[ci].pending |=" not in patches,
          "no target/monitor cg5 pending writes remain")
    check("patch_no_async_enable", "async_enable" not in patches,
          "no async_enable field")
    check("patch_cg9_pending", "async.pending" in patches,
          "pending lives in cfx_hart cg9 rc5")
    check("patch_cause_17_18",
          "DADAO_CAUSE_TIMER      (1ULL << 17)" in patches and
          "DADAO_CAUSE_PMEM_DMA    (1ULL << 18)" in patches,
          "macro cause ids 1<<17 / 1<<18")

    print("doc: %d failed" % len(failures))
    return 0 if not failures else 1


def run_structure():
    failures = []

    def check(name, ok, detail):
        print("[%s] %-40s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            failures.append(name)

    src = _helper_source()
    arbitrate = _function_body(src, "bool dadao_async_arbitrate(CPUState *cs)")
    enter = _function_body(src, "static bool dadao_async_enter(CPUDADAOState *env")
    check("arbitrate_found", bool(arbitrate), "arbiter body extracted")
    check("async_enter_found", bool(enter), "hart-first entry body extracted")
    for bad in ("cfx_intr_mask", "global_cfx_intr_mask"):
        check("enter_no_%s" % bad, bad not in enter,
              "monitor masks do not decide async delivery")
    check("masks_in_enter", "mode_intr_mask" in enter and
          "global_intr_mask" in enter,
          "both mask axes are evaluated in the async entry")
    check("single_async_entry", arbitrate.count("dadao_async_enter(") == 1,
          "one async entry call site (count=%d)" %
          arbitrate.count("dadao_async_enter("))
    check("source_15_before_32",
          "DADAO_CFXHA_HART" in src and "DADAO_CFXHA_PMEM" in src,
          "candidate table lists cfx_hart (15) and cfx_pmem (32)")
    src_table = src[src.find("dadao_async_sources[] ="):]
    src_table = src_table[:src_table.find("};")]
    check("lowest_cfxha_order",
          src_table.find("DADAO_CFXHA_HART") < src_table.find("DADAO_CFXHA_PMEM"),
          "table order is cfx_hart (15) before cfx_pmem (32)")
    check("pending_only_cg9", "async.pending" in src and
          "env->cfx[ci].pending |=" not in src,
          "pending writes target cg9 only")
    check("escape_frame_selector", "imms18 & ~0x3u" in src and "sel == 3" in src,
          "escape validates {0,1,2} / cg9 selector")
    check("cause_check_macro", "DADAO_CAUSE_MACRO16" in src,
          "dadao_cause_check accepts the macro [31:16] space")

    patches = _patch_text()
    check("patch_no_async_enable", "async_enable" not in patches,
          "patch tree has no async_enable")
    check("patch_no_monitor_pending", "env->cfx[ci].pending |=" not in patches,
          "patch tree has no monitor/target pending write")

    print("structure: %d failed" % len(failures))
    return 0 if not failures else 1


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_case(name):
    for n, d, fn, dump in CASES:
        if n == name:
            rom, exp = fn()
            rc, log, err = run(rom, dump=dump)
            if rc is None:
                return False, "TIMEOUT", exp
            diffs = []
            for k, v in exp.items():
                av = rc if k == "exit" else None
                if av != v:
                    diffs.append("%s exp=%r got=%r" % (k, v, av))
            if diffs:
                return False, "; ".join(diffs), exp
            return True, "rc=0x%02x" % rc, exp
    raise KeyError(name)


def main():
    global QEMU
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--qemu", default=None)
    args = ap.parse_args()
    if args.qemu:
        QEMU = args.qemu

    if args.list:
        print("%-26s %s" % (DOC_CASE, "offline: contract arbitration entry"))
        print("%-26s %s" % (STRUCT_CASE, "offline: patch-tree shape"))
        for n, d, _fn, _dump in CASES:
            print("%-26s %s" % (n, d))
        return 0

    if args.only:
        if args.only == DOC_CASE:
            return run_doc()
        if args.only == STRUCT_CASE:
            return run_structure()
        ok, why, exp = run_case(args.only)
        print("%s %-26s %s%s" % ("PASS" if ok else "FAIL", args.only, why,
                                 "" if ok else " (exp=%r)" % (exp,)))
        return 0 if ok else 1

    failed = 0
    if run_doc() != 0:
        failed += 1
    if run_structure() != 0:
        failed += 1
    if args.doc:
        print("%d failed" % failed)
        return 0 if failed == 0 else 1

    if not os.path.isfile(QEMU):
        print("[FAIL] QEMU binary not found: %s" % QEMU)
        return 2

    names = [n for n, _d, _fn, _i in CASES]
    runtime_failed = 0
    for n in names:
        ok, why, exp = run_case(n)
        if ok:
            print("PASS %-26s %s" % (n, why))
        else:
            runtime_failed += 1
            print("FAIL %-26s %s (exp=%r)" % (n, why, exp))
    failed += runtime_failed
    total = len(names) + 2
    print("%d/%d checks passed" % (total - failed, total))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
