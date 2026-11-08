#!/usr/bin/env python3
"""Min ROM probe for INTEG-051t: unified asynchronous interrupt arbitration.

The probe checks the test-machine arbitration convention:

  * ``doc`` (pure Python, no QEMU): the ``contract-see`` arbitration entry and
    the patch tree (no cross-cfx pending bitmap, no ``async_enable``, exactly
    one async ``cfx_enter`` call site, no mask copy in the arbiter).
  * ``runtime`` (min-ROM, QEMU): pending lives in the *target* cfx's
    ``cg5 rc5`` (TIMER ``1<<10`` -> ``cfx_hart``, PMEM_DMA ``1<<8`` ->
    ``cfx_pmem``), the lowest target cfxha wins (15 before 32), one source per
    ``dadao_cpu_exec_interrupt()``, masks keep the pending bit and a later kick
    re-delivers it, and the target cfx is entered directly (no monitor hop).

Expectations are derived by hand from the frozen spec / contract:
  - spec/DADAO-12 §5.2 (exception entry step 3: cfx_intr_mask +
    global_cfx_intr_mask; pending on a masked source), §4.7
    (cfx_hart: TIMER 1<<10, cause_info 0, IMASK),
    §4.9 (cfx_pmem: PMEM_DMA 1<<8, cause_info = dma_status).
  - .tao/contracts/contract-see.md «统一异步中断仲裁（测试机约定）» and the
    two-level filter entries.
  Never from the QEMU implementation.

Observation channels:
  * everything (pending bits, counters, cause id/info, order witnesses) is
    checked in-program and reported through the semihosting SYS_EXIT code, so
    no case depends on a ``-d cpu`` dump block.  ``-d cpu`` logs a full state
    block per translated TB, which would explode while polling a DMA that
    needs a million virtual ns, so the run uses no dump at all;
  * timer cases read the current cycle/cfx_time, set a relative deadline and
    poll it with a bounded loop (``DELTA_NS``/``MAX_WAIT``); async waits poll
    the pending bit or the handler counter with a time window and an
    iteration bound.  Nothing assumes an instruction clock, so QEMU and gem5
    run the same probe (TESTCASES-102t).

Bootstrap (body runs in hmon / cfx3, hypv):
  1. power stage: cfx_hmon hypv_excp_vector = stage, then ``trap cfx_hmon, 0``.
  2. hmon stage: clear the hypv ``cfxtrap/cfxmem/cfxreg/cfxexe`` and
     ``cfx_intr_mask`` masks of cfx_hmon / cfx_pmem / cfx_hart for bits 3/15/32
     (cross-cfx access after a delivery keeps ``inner_cfx_code`` at the target),
     clear cfx_hmon ``global_cfx_intr_mask`` bits 15/32, install the cfx_pmem /
     cfx_hart hypv vectors, set cfx_hmon's hypv vector to a poison routine
     (any monitor hop would exit FAIL) and clear cfx_power's cfxmem/cfxexe for
     all four modes (ROM fetch + RAM access from the handler cfx).

Handlers record to a RAM state block: total delivery counter, nesting depth and
re-entrancy flag, per-source count/id/cause_info, plus one order witness each
(PMEM handler reads cfx_hart ``escape_num``, HART handler reads cfx_pmem
``excp_async_num``) so "lowest cfxha first" is checked without an order array.

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

import os, sys

# TESTCASES-091t: probe geometry from the single profile source
# (tests/shared/machine-profiles.yaml); runtime execution stays BLOCKED until
# QEMU-079/080 provide the Tiny/Vast machines.
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
SP_OFF = SP - RAM_BASE
BOOTROM_BASE = _MACH.bootrom_base
ENTRY = _MACH.entry
EXIT_BLOCK = _MACH.exit_block
RAM_W2 = (RAM_BASE >> 32) & 0xFFFF
RAM_W1 = (RAM_BASE >> 16) & 0xFFFF
RAM_W0 = RAM_BASE & 0xFFFF
SP_W2 = (SP >> 32) & 0xFFFF
SP_W1 = (SP >> 16) & 0xFFFF
SP_W0 = SP & 0xFFFF
EXIT_W2 = (EXIT_BLOCK >> 32) & 0xFFFF
EXIT_W1 = (EXIT_BLOCK >> 16) & 0xFFFF
EXIT_W0 = EXIT_BLOCK & 0xFFFF

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_QEMU = _prelude.default_qemu()
QEMU = DEFAULT_QEMU
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_integ051t")
TIMEOUT = 120

CONTRACT_SEE = os.path.join(_REPO, ".tao", "contracts", "contract-see.md")
PATCH_DIR = os.path.join(_REPO, "components", "qemu", "patches", "target", "dadao")
PATCH_FILES = ("cpu.h.patch", "cpu.c.patch", "helper.c.patch")

# TESTCASES-094t §1: the body runs at RESET_PC + 0x1000 inside the 4 MiB
# bootrom-image, after the shared power -> hmon identity-PTW prelude.
ROM_BASE = _prelude.ROM_BASE
RAM_BASE = _MACH.ram_base

HART_HA = 15
PMEM_HA = 32
HMON_HA = 3
POWER_HA = 63
HART_CG = 8
PMEM_DMA_CG = 15

CG5_CAUSE_ID_RC, CG5_CAUSE_IP_RC, CG5_CAUSE_INFO_RC, CG5_PENDING_RC = 2, 3, 4, 5
CG4_ASYNC_NUM_RC, CG4_ESCAPE_NUM_RC = 4, 5
CG3_CFX_INTR_MASK_RC = 4
CG3_SWITCH_MODE_RC = 8
CG3_EXCP_VECTOR_RC = 10
DMA_SRC_RC, DMA_DST_RC, DMA_SIZE_RC, DMA_CTRL_RC, DMA_STATUS_RC = 0, 1, 2, 3, 4

TIMER = 1 << 10
PMEM_DMA = 1 << 8
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
# global_cfx_intr_mask: bit = target cfxha, 1 = masked.
MASK_TIMER_OPEN = ALL1 & ~((1 << 15))    # TIMER (15) open, PMEM_DMA (32) masked
MASK_PMEM_OPEN = ALL1 & ~((1 << 32))     # PMEM_DMA (32) open, TIMER (15) masked
MASK_BOTH = ALL1                         # both masked
# cfxtrap/cfxmem/cfxreg/cfxexe + cfx_intr_mask allow bits 3/15/32 (the three
# cfxhas the body and the handlers read/write across).
MASK_CROSS = ALL1 & ~((1 << 3) | (1 << 15) | (1 << 32))

EXIT_PASS = 0x00
EXIT_FAIL = 0x61   # guest FAIL segment (spec/Machine-v5 §7.1)

# Timing-model-neutral bounds (TESTCASES-102t).  DELTA_NS = nominal relative
# deadline; WINDOW_NS = tolerated deadline-to-event delay.  Without an
# instruction clock QEMU drives cfx_time from host time, so a delivery can
# slip by the host scheduling latency (measured 0.5-7 ms, more under load).
# The 10 ms nominal deadline leaves >10x that slip before the deadline; the
# 1 s window (100x nominal) still bounds a lost event, which also ends the
# poll at MAX_WAIT.
DELTA_NS = 10_000_000
WINDOW_NS = 1_000_000_000
# Poll iterations: reaching the 10 ms deadline needs ~1.4M iterations on
# gem5 (1 ns/instruction, ~7 instructions/iteration); 4M gives >2x margin.
MAX_WAIT = 4_000_000
# A DMA completion takes 1 us on gem5 and 1 ms on QEMU (test-machine
# latencies); 300k iterations (~5 instructions each) cover the QEMU 1 ms with
# a wide margin.
MAX_DMA_WAIT = 300_000
ARM_RETRIES = 8

# Wait-loop scratch.  Async handlers use rd30..rd39 and the body keeps its
# recorded values in rd5..rd13, so the timing helpers use rd19..rd29.
W_TMP = 19
W_NOW, W_CMP = 20, 21
W_DEAD, W_BOUND, W_MAX, W_WIT = 26, 27, 28, 29

# ROM layout: the shared prelude owns the power -> hmon hand-off; this probe's
# power-mode and hmon-mode setup is appended to the prelude's segments, and the
# body starts at ROM_BASE (RESET_PC + 0x1000).
OFF_HART_HND = 0x2000
OFF_PMEM_HND = 0x2100
OFF_POISON = 0x2200
ROM_END = 0x2400

# RAM state block (zero-filled RAM; rb5 = RAM_BASE).
RAM_STATE = 0x3000
RAM_SEQ = RAM_STATE + 0x00          # total deliveries
RAM_DEPTH = RAM_STATE + 0x08        # nesting depth
RAM_REENT = RAM_STATE + 0x10        # 1 if a delivery nested inside a handler
RAM_PMEM_N = RAM_STATE + 0x20
RAM_PMEM_ID = RAM_STATE + 0x28
RAM_PMEM_INFO = RAM_STATE + 0x30
RAM_PMEM_SAW_HART_ESC = RAM_STATE + 0x38
RAM_HART_N = RAM_STATE + 0x40
RAM_HART_ID = RAM_STATE + 0x48
RAM_HART_INFO = RAM_STATE + 0x50
RAM_HART_SAW_PMEM_ASYNC = RAM_STATE + 0x58

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
    """add.uo {hi, lo}, src_a, src_b: 128-bit unsigned add (carry -> hi).

    Only used to build `deadline + WINDOW`; the two destinations must differ
    (SimRISC-04 §1.1) and `hi` is discarded.
    """
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
# Async handlers (ROM slots) + poison monitor vector
# ---------------------------------------------------------------------------

def build_async_handler(ha, n_off, id_off, info_off, saw_off, saw_ha,
                        saw_cg, saw_rc):
    """Record a delivery, then escape back to the interrupted instruction.

    Registers 30..35 are handler scratch; the body only uses 5..25.
    """
    a = Asm()
    a.emit(cfx2rd(ha, 5, CG5_CAUSE_ID_RC, 30))        # own cfx cause id
    a.emit(cfx2rd(ha, 5, CG5_CAUSE_INFO_RC, 31))      # own cfx cause info
    a.emit(cfx2rd(saw_ha, saw_cg, saw_rc, 32))        # order witness
    a.emit(ld_o(33, 5, RAM_SEQ))
    a.emit(ld_o(34, 5, RAM_DEPTH))
    okd = "depth0_%d_%d" % (ha, len(a.words))
    a.br("z", 34, 0, okd)                             # depth == 0 -> no nesting
    a.emit(*load_rd(35, 1))
    a.emit(st_o(35, 5, RAM_REENT))
    a.mark(okd)
    a.emit(add_si(34, 1))
    a.emit(st_o(34, 5, RAM_DEPTH))
    a.emit(add_si(33, 1))
    a.emit(st_o(33, 5, RAM_SEQ))
    a.emit(st_o(30, 5, id_off))
    a.emit(st_o(31, 5, info_off))
    a.emit(st_o(32, 5, saw_off))
    a.emit(ld_o(33, 5, n_off))
    a.emit(add_si(33, 1))
    a.emit(st_o(33, 5, n_off))
    a.emit(*load_rd(34, 0))
    a.emit(st_o(34, 5, RAM_DEPTH))
    a.emit(escape(ha, 0))
    return a.resolve()


def build_pmem_handler(frame_probe=False):
    """cfx_pmem handler; `frame_probe` arms TIMER inside the frame (case 10)."""
    a = Asm()
    ins = build_async_handler(PMEM_HA, RAM_PMEM_N, RAM_PMEM_ID, RAM_PMEM_INFO,
                              RAM_PMEM_SAW_HART_ESC, HART_HA, 4,
                              CG4_ESCAPE_NUM_RC)
    # drop the trailing escape: the frame probe appends its own body first
    body = ins[:-1]
    a.emit(*body)
    if frame_probe:
        # arm TIMER for now+500 (inside the pmem frame: global mask is all-1)
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
        # inside the frame the second source must not be delivered ...
        a.emit(ld_o(38, 5, RAM_HART_N))
        ok0 = "frame_nohart"
        a.br("z", 38, 0, ok0)
        a.emit(*exit_seq(0x71))                       # nested/early delivery
        a.mark(ok0)
        # ... but its pending bit must be recorded in cfx_hart cg5 rc5 bit10
        a.emit(cfx2rd(HART_HA, 5, CG5_PENDING_RC, 38))
        a.emit(*load_rd(39, TIMER))
        a.emit(and_o(38, 38, 39))
        ok1 = "frame_pending"
        a.br("nz", 38, 0, ok1)
        a.emit(*exit_seq(0x72))                       # event lost inside frame
        a.mark(ok1)
    a.emit(escape(PMEM_HA, 0))
    return a.resolve()


def build_hart_handler():
    return build_async_handler(HART_HA, RAM_HART_N, RAM_HART_ID, RAM_HART_INFO,
                               RAM_HART_SAW_PMEM_ASYNC, PMEM_HA, 4,
                               CG4_ASYNC_NUM_RC)


def build_poison():
    """cfx_hmon vector: any monitor hop is a failure (never reached normally)."""
    a = Asm()
    a.emit(*exit_seq(0x7E))
    return a.resolve()


def handlers(pmem_frame=False):
    return {
        OFF_HART_HND: build_hart_handler(),
        OFF_PMEM_HND: build_pmem_handler(pmem_frame),
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


def need_eq(a, rd, want, code, tag):
    """Exit `code` unless rd == want (each check has its own FAIL code)."""
    ok = "eq_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(24, want))
    a.br("eq", rd, 24, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def need_same(a, rd_a, rd_b, code, tag):
    """Exit `code` unless rd_a == rd_b (both preserved)."""
    ok = "same_%s_%d" % (tag, len(a.words))
    a.br("eq", rd_a, rd_b, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def need_mask_set(a, rd, mask, code, tag):
    """Exit `code` unless (rd & mask) != 0."""
    ok = "ms_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(24, mask))
    a.emit(and_o(23, rd, 24))
    a.br("nz", 23, 0, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def need_mask_clr(a, rd, mask, code, tag):
    """Exit `code` unless (rd & mask) == 0."""
    ok = "mc_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(24, mask))
    a.emit(and_o(23, rd, 24))
    a.br("z", 23, 0, ok)
    a.emit(*exit_seq(code))
    a.mark(ok)


def set_global_mask(a, mask):
    a.emit(*load_rd(22, mask))
    a.emit(cfx2rc(HMON_HA, 8, 1, 22))


def set_hmon_intr_mask(a, mask):
    a.emit(*load_rd(22, mask))
    a.emit(cfx2rc(HMON_HA, 3, CG3_CFX_INTR_MASK_RC, 22))


def pend(a, ha, rd):
    a.emit(cfx2rd(ha, 5, CG5_PENDING_RC, rd))


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
    """Poll dma_status.BUSY until it clears, with a bounded iteration count.

    Without an instruction clock the DMA latency is 1 us on gem5 and 1 ms on
    QEMU; both are finite, so a bound (not an instruction-time assumption)
    keeps this from hanging.  Exhaustion is an explicit guest FAIL.
    """
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
    """Bounded settle loop.

    The head re-tests the counter, so an async delivery that resumes the loop
    with the counter already at 0 exits instead of underflowing (the delivery
    can land on the decrement instruction).
    """
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
    """Witness: cmp(RAM_BASE+off, want) -> 0 iff the counter equals `want`."""

    def emit(a, rd):
        a.emit(ld_o(rd, 5, off))
        a.emit(*load_rd(W_TMP, want))
        a.emit(cmp_uo(rd, rd, W_TMP))

    return emit


def _mask_cond(read_cfx, mask):
    """Witness: read_cfx(rd) & mask -> non-zero iff the bit is set."""

    def emit(a, rd):
        a.emit(read_cfx(rd))
        a.emit(*load_rd(W_TMP, mask))
        a.emit(and_o(rd, rd, W_TMP))

    return emit


def _pending_hart(rd):
    return cfx2rd(HART_HA, 5, CG5_PENDING_RC, rd)


def _pending_pmem(rd):
    return cfx2rd(PMEM_HA, 5, CG5_PENDING_RC, rd)


def _set_bound(a, deadline_rd):
    """W_BOUND = deadline + WINDOW_NS (add.uo: lo = W_BOUND, hi = W_CMP)."""
    a.emit(*load_rd(W_TMP, WINDOW_NS))
    a.emit(add_uo(W_BOUND, W_CMP, deadline_rd, W_TMP))


def settle_bound(a):
    """W_BOUND = now + WINDOW_NS (bound for an event expected right away)."""
    timer_now(a, W_NOW)
    _set_bound(a, W_NOW)


def check_quiet(a, deadline_rd, cond, zero_is_met, code, tag):
    """Assert `cond` is NOT met while the clock is still before the deadline.

    The witness is sampled *first*, then the clock: if the clock is still
    before the deadline, the witness sample was taken even earlier, so a met
    condition is a genuine early delivery.  If the clock already passed the
    deadline the check is inconclusive and skipped; clock-first sampling
    would misjudge a preemption between the two reads as an early delivery.
    """
    done = "q_%s" % tag
    cond(a, W_WIT)
    timer_now(a, W_NOW)
    a.emit(cmp_uo(W_CMP, W_NOW, deadline_rd))
    a.br("nn", W_CMP, 0, done)
    a.br("nz" if zero_is_met else "z", W_WIT, 0, done)
    a.emit(*exit_seq(code))
    a.mark(done)


def wait_cond(a, bound_rd, cond, zero_is_met, tag, code_late, code_lost):
    """Bounded poll for `cond` with a two-sided window.

    `bound_rd` = deadline + WINDOW_NS: an event first seen after it is "late"
    (`code_late`); an event never seen before the bound or MAX_WAIT is "lost"
    (`code_lost`).  Both fail paths are reachable.
    """
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
    """Cancel, then arm cmp = now + delta; leaves W_DEAD/W_BOUND.

    Without a deterministic instruction clock a host preemption between the
    clock read and the cmp write would arm an already-expired timer; cancel
    (cmp = ~0, ctrl = 0, pending = 0) and retry while the clock is not yet in
    the future.  The witness counters are restored to the given baseline
    (probe bookkeeping in RAM, not hardware state).
    """
    retry = "tw_%s_reset" % tag
    done = "tw_%s_ok" % tag
    a.emit(*load_rd(W_MAX, ARM_RETRIES))
    a.mark(retry)
    a.emit(*load_rd(W_TMP, ALL1))                    # cmp = ~0: cancel
    a.emit(cfx2rc(HART_HA, HART_CG, 4, W_TMP))
    a.emit(*load_rd(W_TMP, 0))                       # ctrl = 0
    a.emit(cfx2rc(HART_HA, HART_CG, 5, W_TMP))
    a.emit(cfx2rc(HART_HA, 5, CG5_PENDING_RC, W_TMP))
    a.emit(*load_rd(W_TMP, base_hart))               # witness baseline
    a.emit(st_o(W_TMP, 5, RAM_HART_N))
    a.emit(*load_rd(W_TMP, base_seq))
    a.emit(st_o(W_TMP, 5, RAM_SEQ))
    timer_now(a, W_NOW)
    a.emit(*load_rd(W_TMP, delta))                   # >= 10 ms: not imms18
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
    """4 MiB `bootrom-image`, no `-kernel`; returns (rc, cpu_log, stderr).

    Every check is in-program, so no case needs a `-d cpu` dump; keeping it
    off avoids a full state block per TB while polling a DMA that takes
    1 ms of QEMU virtual time.
    """
    rc, log = _prelude.run(rom, WORKDIR, qemu=QEMU, timeout=TIMEOUT,
                           dump=dump)
    if not dump:
        log = ""
    return rc, log, ""


def build_rom(prog, hnd=None):
    """Shared prelude: body at RESET_PC + 0x1000; the probe-specific power and
    hmon setup (cross-cfx masks, handlers, poison vector) runs in the prelude's
    segments, so `hmon_addr(off)` is body-relative (TESTCASES-094t §1)."""
    return _prelude.build_rom(prog, hnd, hmon_extra=hmon_setup())


def hmon_setup():
    # TESTCASES-094t §1: the power->hmon hand-off and the power-mask clearing
    # live in the shared prelude; only the probe-specific mask/vector/handler
    # setup stays here.
    ins = load_rb(5, RAM_BASE)                        # handler state block base
    ins += load_rd(21, MASK_CROSS)
    # cfx_hmon: hypv cfx{trap,mem,reg,exe} + cfx_intr_mask; global mask 15/32 off
    for rc in (0, 1, 2, 3, CG3_CFX_INTR_MASK_RC):
        ins += [cfx2rc(HMON_HA, 3, rc, 21)]
    ins += [cfx2rc(HMON_HA, 8, 1, 21)]
    # cfx_pmem: hypv cfg masks + cfx_intr_mask, vector
    for rc in (0, 1, 2, 3, CG3_CFX_INTR_MASK_RC):
        ins += [cfx2rc(PMEM_HA, 3, rc, 21)]
    ins += load_rd(21, hmon_addr(OFF_PMEM_HND))
    ins += [cfx2rc(PMEM_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart: hypv cfg masks + cfx_intr_mask, vector
    ins += load_rd(21, MASK_CROSS)
    for rc in (0, 1, 2, 3, CG3_CFX_INTR_MASK_RC):
        ins += [cfx2rc(HART_HA, 3, rc, 21)]
    ins += load_rd(21, hmon_addr(OFF_HART_HND))
    ins += [cfx2rc(HART_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_power: allow ROM fetch + RAM access from any cfx (cfxmem/cfxexe = 0)
    ins += load_rd(20, 0)
    for cg in (0, 1, 2, 3):
        ins += [cfx2rc(POWER_HA, cg, 1, 20), cfx2rc(POWER_HA, cg, 3, 20)]
    # any delivery to cfx_hmon (monitor hop) => poison => FAIL
    ins += load_rd(21, hmon_addr(OFF_POISON))
    ins += [cfx2rc(HMON_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    # start from a clean pending state (software 0 = cancel)
    ins += [cfx2rc(PMEM_HA, 5, CG5_PENDING_RC, 20)]
    ins += [cfx2rc(HART_HA, 5, CG5_PENDING_RC, 20)]
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


@case("pmem_pending_in_pmem",
      "masked PMEM_DMA pending lands in cfx_pmem cg5 rc5 bit8 only")
def _pmem_pending_in_pmem():
    a = Asm()
    set_global_mask(a, MASK_TIMER_OPEN)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    pend(a, PMEM_HA, 5)
    need_mask_set(a, 5, PMEM_DMA, 0xA1, "p_pend")
    pend(a, HART_HA, 6)
    need_mask_clr(a, 6, PMEM_DMA, 0xA2, "h_no_pend")
    ram_ld(a, RAM_SEQ, 7)
    need_eq(a, 7, 0, 0xA3, "no_deliver")
    set_global_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "pp",
              0xA9, 0xAA)
    ram_ld(a, RAM_PMEM_N, 8)
    need_eq(a, 8, 1, 0xA4, "pmem_once")
    ram_ld(a, RAM_PMEM_ID, 9)
    need_eq(a, 9, PMEM_DMA, 0xA5, "pmem_cid")
    ram_ld(a, RAM_PMEM_INFO, 10)
    need_eq(a, 10, ST_DONE, 0xA6, "pmem_info")
    pend(a, PMEM_HA, 11)
    need_mask_clr(a, 11, PMEM_DMA, 0xA7, "pending_cleared")
    ram_ld(a, RAM_SEQ, 12)
    need_eq(a, 12, 1, 0xA8, "seq_one")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("timer_pending_in_hart",
      "masked TIMER pending lands in cfx_hart cg5 rc5 bit10 only")
def _timer_pending_in_hart():
    a = Asm()
    set_global_mask(a, MASK_PMEM_OPEN)
    timer_arm_window(a, tag="tph")
    wait_cond(a, W_BOUND, _mask_cond(_pending_hart, TIMER), False, "tph",
              0xB8, 0xB9)
    ram_ld(a, RAM_SEQ, 5)
    need_eq(a, 5, 0, 0xB1, "no_deliver")
    pend(a, HART_HA, 6)
    need_mask_set(a, 6, TIMER, 0xB2, "h_pend")
    pend(a, PMEM_HA, 7)
    need_mask_clr(a, 7, TIMER, 0xB3, "p_no_pend")
    set_global_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_HART_N, 1), True, "tphd",
              0xBA, 0xBB)
    ram_ld(a, RAM_HART_N, 8)
    need_eq(a, 8, 1, 0xB4, "hart_once")
    ram_ld(a, RAM_HART_ID, 9)
    need_eq(a, 9, TIMER, 0xB5, "hart_cid")
    ram_ld(a, RAM_HART_INFO, 10)
    need_eq(a, 10, 0, 0xB6, "hart_info")
    pend(a, HART_HA, 11)
    need_mask_clr(a, 11, TIMER, 0xB7, "pending_cleared")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("pending_no_cross_cfx",
      "S/H pending stay in their own target cfx; release order 15 then 32")
def _pending_no_cross_cfx():
    a = Asm()
    set_global_mask(a, MASK_BOTH)
    dma_status_clear(a)
    timer_arm_window(a, tag="pnc")
    dma_start(a)
    dma_wait(a)
    wait_cond(a, W_BOUND, _mask_cond(_pending_hart, TIMER), False, "pnct",
              0xCC, 0xCD)
    delay_loop(a, 400, "settle")                     # DMA completion settle
    pend(a, HART_HA, 5)
    need_mask_set(a, 5, TIMER, 0xC1, "h_timer")
    need_mask_clr(a, 5, PMEM_DMA, 0xC2, "h_no_pmem")
    pend(a, PMEM_HA, 6)
    need_mask_set(a, 6, PMEM_DMA, 0xC3, "p_pmem")
    need_mask_clr(a, 6, TIMER, 0xC4, "p_no_timer")
    ram_ld(a, RAM_SEQ, 7)
    need_eq(a, 7, 0, 0xC5, "none_yet")
    # release TIMER only: PMEM_DMA must stay pending in cfx_pmem
    set_global_mask(a, MASK_TIMER_OPEN)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_HART_N, 1), True, "pnc15",
              0xCE, 0xCF)
    ram_ld(a, RAM_HART_N, 8)
    need_eq(a, 8, 1, 0xC6, "timer_first")
    ram_ld(a, RAM_PMEM_N, 9)
    need_eq(a, 9, 0, 0xC7, "pmem_held")
    pend(a, PMEM_HA, 10)
    need_mask_set(a, 10, PMEM_DMA, 0xC8, "pmem_pending_kept")
    set_global_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "pnc32",
              0xD0, 0xD1)
    ram_ld(a, RAM_PMEM_N, 11)
    need_eq(a, 11, 1, 0xC9, "pmem_after")
    ram_ld(a, RAM_SEQ, 12)
    need_eq(a, 12, 2, 0xCA, "both_once")
    pend(a, PMEM_HA, 13)
    need_mask_clr(a, 13, PMEM_DMA, 0xCB, "pmem_cleared")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("global_mask_block",
      "global bit15 blocks TIMER only; PMEM_DMA still delivered; re-kick")
def _global_mask_block():
    a = Asm()
    set_global_mask(a, MASK_PMEM_OPEN)                # TIMER masked
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "gmbp",
              0x79, 0x7A)
    ram_ld(a, RAM_PMEM_N, 5)
    need_eq(a, 5, 1, 0x71, "pmem_delivered")
    ram_ld(a, RAM_HART_N, 6)
    need_eq(a, 6, 0, 0x72, "timer_not_yet")
    timer_arm_window(a, base_seq=1, tag="gmb")
    wait_cond(a, W_BOUND, _mask_cond(_pending_hart, TIMER), False, "gmbt",
              0x7B, 0x7C)
    ram_ld(a, RAM_HART_N, 7)
    need_eq(a, 7, 0, 0x73, "timer_blocked")
    pend(a, HART_HA, 8)
    need_mask_set(a, 8, TIMER, 0x74, "timer_pending_kept")
    set_global_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_HART_N, 1), True, "gmbd",
              0x7D, 0x7E)
    ram_ld(a, RAM_HART_N, 9)
    need_eq(a, 9, 1, 0x75, "timer_delivered_once")
    ram_ld(a, RAM_PMEM_N, 10)
    need_eq(a, 10, 1, 0x76, "pmem_still_once")
    ram_ld(a, RAM_SEQ, 11)
    need_eq(a, 11, 2, 0x77, "seq_two")
    pend(a, HART_HA, 12)
    need_mask_clr(a, 12, TIMER, 0x78, "timer_cleared")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("per_cfx_mask_block",
      "cfx_intr_mask reads the *current* cfx row, indexed by target cfxha")
def _per_cfx_mask_block():
    a = Asm()
    set_global_mask(a, 0)
    dma_status_clear(a)
    # Phase 1 (current cfx == hmon): hmon's hypv row masks target cfxha 32 and
    # cfx_pmem's own row also masks 32 -> the DMA must not be delivered.
    a.emit(*load_rd(22, 1 << 32))
    a.emit(cfx2rc(HMON_HA, 3, CG3_CFX_INTR_MASK_RC, 22))
    a.emit(cfx2rc(PMEM_HA, 3, CG3_CFX_INTR_MASK_RC, 22))
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _mask_cond(_pending_pmem, PMEM_DMA), False, "pcm1",
              0x6B, 0x6C)
    ram_ld(a, RAM_PMEM_N, 5)
    need_eq(a, 5, 0, 0x61, "pmem_blocked")
    pend(a, PMEM_HA, 6)
    need_mask_set(a, 6, PMEM_DMA, 0x62, "pmem_pending_kept")
    # Phase 2 (reverse): release the *current* cfx row only.  cfx_pmem's own row
    # still masks bit32, so a delivery proves the arbiter/cfx_enter reads the
    # current cfx row with the target cfxha as bit index.
    set_hmon_intr_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "pcm2",
              0x6D, 0x6E)
    ram_ld(a, RAM_PMEM_N, 7)
    need_eq(a, 7, 1, 0x63, "current_row_only")
    pend(a, PMEM_HA, 8)
    need_mask_clr(a, 8, PMEM_DMA, 0x64, "pmem_cleared")
    # Phase 3: a different source (TIMER, target 15) is not blocked by bit32.
    timer_arm_window(a, base_seq=1, tag="pcm")
    wait_cond(a, W_BOUND, _count_cond(RAM_HART_N, 1), True, "pcm3",
              0x6F, 0x70)
    ram_ld(a, RAM_HART_N, 9)
    need_eq(a, 9, 1, 0x65, "timer_not_blocked")
    ram_ld(a, RAM_SEQ, 10)
    need_eq(a, 10, 2, 0x66, "seq_two")
    ram_ld(a, RAM_HART_ID, 11)
    need_eq(a, 11, TIMER, 0x67, "timer_cid")
    # cleanup: clear cfx_pmem's own bit32 (from cfx 15, allowed by bootstrap)
    a.emit(*load_rd(22, 0))
    a.emit(cfx2rc(PMEM_HA, 3, CG3_CFX_INTR_MASK_RC, 22))
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("intr_mask_tail_kick",
      "cfx_intr_mask bit32 blocks PMEM_DMA; the cfx2rc tail kick refires")
def _intr_mask_tail_kick():
    a = Asm()
    set_global_mask(a, 0)
    # delivery filters on the *current* cfx row (hmon, the body's cfx)
    set_hmon_intr_mask(a, 1 << PMEM_HA)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _mask_cond(_pending_pmem, PMEM_DMA), False, "imt1",
              0xF6, 0xF7)
    ram_ld(a, RAM_PMEM_N, 5)
    need_eq(a, 5, 0, 0xF1, "filter_blocked")
    pend(a, PMEM_HA, 6)
    need_mask_set(a, 6, PMEM_DMA, 0xF2, "pending_kept")
    set_hmon_intr_mask(a, 0)                          # generic cfx2rc write tail
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "imt2",
              0xF8, 0xF9)
    ram_ld(a, RAM_PMEM_N, 7)
    need_eq(a, 7, 1, 0xF3, "delivered_once")
    ram_ld(a, RAM_PMEM_ID, 8)
    need_eq(a, 8, PMEM_DMA, 0xF4, "cid")
    pend(a, PMEM_HA, 9)
    need_mask_clr(a, 9, PMEM_DMA, 0xF5, "pending_cleared")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("timer_imask_hold",
      "IMASK holds TIMER in cfx_hart pending; ctrl release delivers once")
def _timer_imask_hold():
    a = Asm()
    set_global_mask(a, 0)
    timer_arm_window(a, ctrl=CTRL_ENABLE | CTRL_IMASK, tag="tih")
    check_quiet(a, W_DEAD, _count_cond(RAM_HART_N, 1), True, 0x109, "tihq")
    wait_cond(a, W_BOUND, _mask_cond(_pending_hart, TIMER), False, "tihp",
              0x106, 0x107)
    ram_ld(a, RAM_HART_N, 5)
    need_eq(a, 5, 0, 0x101, "not_delivered")
    pend(a, HART_HA, 6)
    need_mask_set(a, 6, TIMER, 0x102, "pending_kept")
    a.emit(*load_rd(22, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 22))           # release IMASK
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_HART_N, 1), True, "tihd",
              0x10A, 0x10B)
    ram_ld(a, RAM_HART_N, 7)
    need_eq(a, 7, 1, 0x103, "delivered_once")
    ram_ld(a, RAM_HART_ID, 8)
    need_eq(a, 8, TIMER, 0x104, "cid")
    pend(a, HART_HA, 9)
    need_mask_clr(a, 9, TIMER, 0x105, "pending_cleared")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("low_cfxha_first",
      "both pending + one mask write => TIMER (15) first, PMEM (32) after escape")
def _low_cfxha_first():
    a = Asm()
    set_global_mask(a, MASK_BOTH)
    dma_status_clear(a)
    timer_arm_window(a, tag="lcf")
    dma_start(a)
    dma_wait(a)
    wait_cond(a, W_BOUND, _mask_cond(_pending_hart, TIMER), False, "lcft",
              0x11A, 0x11B)
    delay_loop(a, 400, "settle")
    ram_ld(a, RAM_SEQ, 5)
    need_eq(a, 5, 0, 0x111, "none_yet")
    set_global_mask(a, 0)                             # single write, both ready
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_SEQ, 2), True, "lcf2",
              0x11C, 0x11D)
    ram_ld(a, RAM_HART_N, 6)
    need_eq(a, 6, 1, 0x112, "timer_once")
    ram_ld(a, RAM_PMEM_N, 7)
    need_eq(a, 7, 1, 0x113, "pmem_once")
    ram_ld(a, RAM_SEQ, 8)
    need_eq(a, 8, 2, 0x114, "two_total")
    ram_ld(a, RAM_REENT, 9)
    need_eq(a, 9, 0, 0x115, "no_nesting")
    ram_ld(a, RAM_HART_ID, 10)
    need_eq(a, 10, TIMER, 0x116, "timer_cid")
    ram_ld(a, RAM_PMEM_ID, 11)
    need_eq(a, 11, PMEM_DMA, 0x117, "pmem_cid")
    # order witnesses: TIMER entered with 0 pmem deliveries; PMEM entered after
    # the TIMER frame had escaped (escape_num == 1)
    ram_ld(a, RAM_HART_SAW_PMEM_ASYNC, 12)
    need_eq(a, 12, 0, 0x118, "timer_first")
    ram_ld(a, RAM_PMEM_SAW_HART_ESC, 13)
    need_eq(a, 13, 1, 0x119, "pmem_after_escape")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("escape_kick",
      "TIMER expiry inside a cfx_pmem frame is held, delivered after escape")
def _escape_kick():
    a = Asm()
    set_global_mask(a, 0)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "esk1",
              0x127, 0x128)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_HART_N, 1), True, "esk2",
              0x129, 0x12A)
    ram_ld(a, RAM_PMEM_N, 5)
    need_eq(a, 5, 1, 0x121, "pmem_frame")
    ram_ld(a, RAM_HART_N, 6)
    need_eq(a, 6, 1, 0x122, "timer_after_escape")
    ram_ld(a, RAM_SEQ, 7)
    need_eq(a, 7, 2, 0x123, "both")
    ram_ld(a, RAM_REENT, 8)
    need_eq(a, 8, 0, 0x124, "no_nesting")
    ram_ld(a, RAM_HART_ID, 9)
    need_eq(a, 9, TIMER, 0x125, "timer_cid")
    ram_ld(a, RAM_PMEM_SAW_HART_ESC, 10)
    need_eq(a, 10, 0, 0x126, "timer_came_later")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers(pmem_frame=True)), {"exit": EXIT_PASS}


@case("direct_target",
      "both sources land in their own cfx handler; cfx_hmon poison silent")
def _direct_target():
    a = Asm()
    set_global_mask(a, 0)
    dma_status_clear(a)
    a.emit(cfx2rd(HMON_HA, 4, CG4_ASYNC_NUM_RC, 5))   # monitor async count (before)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "dt1",
              0x137, 0x138)
    ram_ld(a, RAM_PMEM_N, 6)
    need_eq(a, 6, 1, 0x131, "pmem_own")
    # The TIMER event is the only pending source now: its own kick must wake the
    # vCPU (no mask write happens between the expiry and this check).
    timer_arm_window(a, base_seq=1, tag="dt")
    wait_cond(a, W_BOUND, _count_cond(RAM_HART_N, 1), True, "dt2",
              0x139, 0x13A)
    ram_ld(a, RAM_HART_N, 7)
    need_eq(a, 7, 1, 0x132, "hart_own")
    ram_ld(a, RAM_PMEM_ID, 8)
    need_eq(a, 8, PMEM_DMA, 0x133, "pmem_cid")
    ram_ld(a, RAM_HART_ID, 9)
    need_eq(a, 9, TIMER, 0x134, "hart_cid")
    a.emit(cfx2rd(HMON_HA, 4, CG4_ASYNC_NUM_RC, 10))  # monitor async count (after)
    need_same(a, 10, 5, 0x135, "no_monitor_hop")
    ram_ld(a, RAM_SEQ, 11)
    need_eq(a, 11, 2, 0x136, "two_total")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("dedup_same_source",
      "default clock: two DMA completions while masked merge into one delivery")
def _dedup_same_source():
    a = Asm()
    set_global_mask(a, MASK_TIMER_OPEN)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    pend(a, PMEM_HA, 5)
    need_mask_set(a, 5, PMEM_DMA, 0x141, "pending")
    ram_ld(a, RAM_SEQ, 6)
    need_eq(a, 6, 0, 0x142, "none_yet")
    set_global_mask(a, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "dd",
              0x146, 0x147)
    ram_ld(a, RAM_PMEM_N, 7)
    need_eq(a, 7, 1, 0x143, "merged_once")
    pend(a, PMEM_HA, 8)
    need_mask_clr(a, 8, PMEM_DMA, 0x144, "cleared")
    delay_loop(a, 5000, "still")                      # bounded work, no deadline
    ram_ld(a, RAM_PMEM_N, 9)
    need_eq(a, 9, 1, 0x145, "still_once")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("pmem_error_info",
      "default clock: PA_FAULT with IRQ_EN => cause_id 1<<8, cause_info ERROR|ERR_CODE")
def _pmem_error_info():
    a = Asm()
    set_global_mask(a, 0)
    dma_status_clear(a)
    dma_setup(a, PMEM_BASE, ROM_BASE + 0x1000, 8, CTRL_START | CTRL_IRQ_EN)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "perr",
              0x156, 0x157)
    ram_ld(a, RAM_PMEM_N, 5)
    need_eq(a, 5, 1, 0x151, "delivered")
    ram_ld(a, RAM_PMEM_ID, 6)
    need_eq(a, 6, PMEM_DMA, 0x152, "cid")
    ram_ld(a, RAM_PMEM_INFO, 7)
    need_eq(a, 7, ST_ERROR | (ERR_PA_FAULT << ERR_CODE_SHIFT), 0x153, "cinfo")
    pend(a, PMEM_HA, 8)
    need_mask_clr(a, 8, PMEM_DMA, 0x154, "cleared")
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 9))
    need_mask_set(a, 9, ST_ERROR, 0x155, "status_error")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


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
        # A prototype ends with ';' before any '{'; take the definition.
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
            ("pending", "pending recorded in the target cfx"),
            ("目标 cfx", "pending belongs to the target cfx"),
            ("cg5 rc5", "cg5 rc5 is the single record"),
            ("cfx_hart", "TIMER target named"),
            ("cfx_pmem", "PMEM_DMA target named"),
            ("位索引 = 目标 cfxha", "mask bit index = target cfxha"),
            ("升序", "lowest target cfxha first"),
            ("单层", "single-layer delivery"),
            ("补投", "mask release re-delivers"),
            ("合并", "same-source duplicate events merge"),
            ("不引入", "no async_enable-style gate"),
            ("async_enable", "async_enable named as not introduced"),
            (u"DADAO-12 §5", "spec citation"),
            ("ADR-0045 D3", "ADR citation"),
    ):
        check("entry_%s" % token.replace(" ", "_"), token in entry, why)

    patches = _patch_text()
    check("patch_no_hart_async_pending", "hart_async_pending" not in patches,
          "no cross-cfx pending bitmap")
    check("patch_no_async_enable", "async_enable" not in patches,
          "no async_enable field")
    check("patch_no_per_source_bool",
          "pmem_dma_irq;" not in patches and "hart_irq;" not in patches,
          "per-source bool flags removed")

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
    enter = _function_body(src, "static uint64_t cfx_enter(CPUDADAOState *env")
    check("arbitrate_found", bool(arbitrate), "arbiter body extracted")
    check("cfx_enter_found", bool(enter), "cfx_enter body extracted")
    for bad in ("cfx_intr_mask", "global_cfx_intr_mask"):
        check("arbiter_no_%s" % bad, bad not in arbitrate,
              "mask decision not copied into the arbiter")
    check("single_async_cfx_enter", src.count(", false, &entered)") == 1,
          "one async cfx_enter call site (count=%d)" %
          src.count(", false, &entered)"))
    check("async_enter_in_arbiter", "cfx_enter(env, cause, cfxha" in arbitrate,
          "the async entry is inside the arbiter")

    mask_rel = re.compile(r"1ULL\s*<<\s*target")
    all_hits = sum(len(mask_rel.findall(l)) for l in src.splitlines())
    enter_hits = len(mask_rel.findall(enter))
    check("mask_expr_only_in_cfx_enter", all_hits == enter_hits and enter_hits >= 2,
          "mask 1ULL<<target: total=%d in cfx_enter=%d" % (all_hits, enter_hits))
    src_table = src[src.find("dadao_async_sources[] ="):]
    src_table = src_table[:src_table.find("};")]
    order_ok = ("DADAO_CFXHA_HART" in src_table and
                "DADAO_CFXHA_PMEM" in src_table and
                src_table.find("DADAO_CFXHA_HART") <
                src_table.find("DADAO_CFXHA_PMEM"))
    check("lowest_cfxha_order", order_ok,
          "candidate table lists cfx_hart (15) before cfx_pmem (32)")

    patches = _patch_text()
    check("patch_no_async_enable", "async_enable" not in patches,
          "patch tree has no async_enable")
    check("patch_no_hart_async_pending", "hart_async_pending" not in patches,
          "patch tree has no cross-cfx bitmap")

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
        print("%-26s %s" % (STRUCT_CASE, "offline: no async_enable / mask copy"))
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
