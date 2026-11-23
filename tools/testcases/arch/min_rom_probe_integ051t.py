#!/usr/bin/env python3
"""Min ROM probe for INTEG-051t: hart-first asynchronous arbitration.

The probe checks the test-machine convention after ADR-0061 (including R2):

  * ``doc`` (pure Python, no QEMU): the contract-see arbitration entry and the
    patch tree (pending/frame bitmaps in cfx_hart cg9, masks on the running
    mode monitor only, no macro cause id, no async_enable, one async entry).
  * ``runtime`` (min-ROM, QEMU): every asynchronous source is identified by its
    **source cfxha** (TIMER 15, PMEM_DMA 32), never by an ``excp_cause_id``.
    Delivery is hart-first: ``cfx_hart cg9 rc3`` is the capture's source bitmap
    and ``rc4`` the pending bitmap (both HW/RO); the source mask is the *running
    mode* monitor's ``cg8 rc1`` (``cfx_<monitor>_async_intr_mask``, reset all-1).
    One instruction boundary merges every pending and allowed source into one
    capture.  cg9 is a **capture buffer**, not a live frame: every entry
    overwrites ``prev_*``/``cause_ip``/``src_frame`` (no ``frame_valid``, no
    software clear, no ``src_frame != 0`` gate); the software copies the
    capture into its task context and returns through smon (the probe models
    that with ``trap cfx_smon`` + a cfx_smon ``cg5`` frame rewrite).  Executing
    ``escape imms18 = 2`` is not an async return: cg9 is not a return frame, so
    it raises the current cfx's ``CFXESC`` and changes nothing.

Expectations are derived by hand from the frozen spec / contract:
  - spec/DADAO-12 §4.1-§4.4 (monitor async mask), §4.7 (cg9 seven slots,
    timer), §4.9 (cfx_pmem DMA), §5.1/§5.4 (escape frame selector, capture),
    §5.2/§5.3 (sync entry/exit, escape on cg5).
  - .tao/contracts/contract-see.md §3 «统一异步中断（测试机约定，hart-first）».
  Never from the QEMU implementation.

Observation channels: everything (frame fields, pending bits, counters) is
checked in-program and reported through the semihosting SYS_EXIT code, so no
case depends on a ``-d cpu`` dump block.

Bootstrap (body runs in hmon / cfx3, hypv, via the shared prelude):
  1. open cfx_hart's cg9 and cfx_smon's cg5 for supv (``hypv_cg_reg_deleg=0x8``),
     and let supv ``trap`` into cfx_smon (cfx_smon's supv ``cg2 rc0`` bit15 = 0);
  2. install ``cfx_hart cg9 rc5`` = async handler, ``rc6`` = supv (2);
  3. install cfx_smon's supv vector = async-return / sync-exception recorder;
  4. poison cfx_hmon's hypv vector (any monitor hop would exit FAIL);
  5. leave every monitor mask at its reset value (all-1); each case opens the
     source bits it needs through ``cfx2rc <monitor>, cg8, rc1``.

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

_MACH = _machine_profile.load(os.environ.get("DADAO_TEST_PROFILE") or "vast")
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
HART_CG = 8
MON_CG = 8
MON_MASK_RC = 1
PMEM_DMA_CG = 15

# cfx_hart cg9 (DADAO-12 §4.7; ADR-0061 D7): rc0..rc6, rc7-rc15 reserved.
RC_PREV_MODE, RC_PREV_CFX, RC_CAUSE_IP = 0, 1, 2
RC_FRAME, RC_PENDING, RC_VECTOR, RC_SWITCH = 3, 4, 5, 6

# cg5 (sync frame) / cg4 counters.
CG5_CAUSE_ID_RC, CG5_CAUSE_IP_RC, CG5_CAUSE_INFO_RC, CG5_PENDING_RC = 2, 3, 4, 5
CG4_ASYNC_NUM_RC = 4
CG3_EXCP_VECTOR_RC = 10
DMA_SRC_RC, DMA_DST_RC, DMA_SIZE_RC, DMA_CTRL_RC, DMA_STATUS_RC = 0, 1, 2, 3, 4

# Source identity = source cfxha (not an excp_cause_id; ADR-0061 D2).
SRC_TIMER = 1 << HART_HA          # bit 15
SRC_PMEM = 1 << PMEM_HA           # bit 32
SRC_BOTH = SRC_TIMER | SRC_PMEM

ILLI = 1 << 8
CFXREG = 1 << 2
CFXESC = 1 << 3
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

# ROM layout: body-relative handler slots (0x400 apart: the smon handler holds
# the async hand-off plus the sync-cause recorder).
OFF_MAIN_HND = 0x2000
OFF_FRAME_HND = 0x2400
OFF_SMON_HND = 0x2800
OFF_POISON = 0x2C00
OFF_HART_SYNC_HND = 0x3000     # cfx_hart's own supv sync vector (CFXESC)
ROM_END = 0x3200

# RAM state block (zero-filled; rb5 = RAM_BASE).
RAM_STATE = 0x3000
RAM_SEQ = RAM_STATE + 0x00           # total async frames entered
RAM_DEPTH = RAM_STATE + 0x08         # frame nesting depth
RAM_REENT = RAM_STATE + 0x10         # 1 if a frame nested inside a handler
RAM_LAST_FRAME = RAM_STATE + 0x18    # cg9 rc3 at entry
RAM_LAST_PENDING = RAM_STATE + 0x20  # cg9 rc4 at entry
RAM_LAST_IP = RAM_STATE + 0x28       # cg9 rc2 at entry
RAM_LAST_PREVM = RAM_STATE + 0x30
RAM_LAST_PREVC = RAM_STATE + 0x38
RAM_TIMER_N = RAM_STATE + 0x40       # frames carrying bit 15
RAM_PMEM_N = RAM_STATE + 0x48        # frames carrying bit 32
RAM_SYNC_N = RAM_STATE + 0x50
RAM_SYNC_ID = RAM_STATE + 0x58
RAM_ILLI_N = RAM_STATE + 0x60
RAM_CFXREG_N = RAM_STATE + 0x68
RAM_ARM_IP = RAM_STATE + 0x70        # body address of the arm marker
RAM_CFXESC_N = RAM_STATE + 0x78      # sync CFXESC count (escape on cg9)
RAM_HANDOFF = RAM_STATE + 0x80       # 1 while the async handler hands off to smon

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


def _count_source(a, frame_rd, srcbit, off, tag):
    """Increment `off` once when bit `srcbit` is in the frame bitmap."""
    skip = "src_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(38, srcbit))
    a.emit(and_o(38, frame_rd, 38))
    a.br("z", 38, 0, skip)
    _inc(a, off, 36)
    a.mark(skip)


def _record_capture(a):
    """Read the cg9 capture into rd30..rd34, then count it in RAM.

    Registers 30..39 are handler scratch; the body only uses 5..25.  The
    capture is read first (it is overwritten by any later entry), so the
    software-side copy is done before anything else runs.
    """
    a.emit(cfx2rd(HART_HA, 9, RC_FRAME, 30))
    a.emit(cfx2rd(HART_HA, 9, RC_PENDING, 31))
    a.emit(cfx2rd(HART_HA, 9, RC_CAUSE_IP, 32))
    a.emit(cfx2rd(HART_HA, 9, RC_PREV_MODE, 33))
    a.emit(cfx2rd(HART_HA, 9, RC_PREV_CFX, 34))
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
    a.emit(st_o(30, 5, RAM_LAST_FRAME))
    a.emit(st_o(31, 5, RAM_LAST_PENDING))
    a.emit(st_o(32, 5, RAM_LAST_IP))
    a.emit(st_o(33, 5, RAM_LAST_PREVM))
    a.emit(st_o(34, 5, RAM_LAST_PREVC))
    _count_source(a, 30, SRC_TIMER, RAM_TIMER_N, "t")
    _count_source(a, 30, SRC_PMEM, RAM_PMEM_N, "p")


def _hand_off(a):
    """Software hand-off: `trap cfx_smon`, then the smon handler rebuilds a cg5
    frame from the copied capture and `escape`s to its cause_ip (ADR-0061 D4).

    A correct hand-off never returns here: the cfx_smon `cg5` escape jumps to
    the capture's `async_cause_ip`.  Reaching the trailing exit means the
    hand-off path was lost.
    """
    a.emit(*load_rd(36, 1))
    a.emit(st_o(36, 5, RAM_HANDOFF))
    a.emit(trap(SMON_HA, 0))            # cfx_smon supv vector = hand-off handler
    a.emit(*exit_seq(0x6F))             # unreachable on a correct return


def build_async_handler(extra=None):
    """Record the cg9 capture, then hand off to smon and return.

    `extra` words run inside the capture before the hand-off (ILLI/CFXREG/
    CFXESC encoding cases).  Each word must not clobber rd30..rd39.
    """
    a = Asm()
    _record_capture(a)
    if extra:
        a.emit(*extra)
    a.emit(*load_rd(36, 0))
    a.emit(st_o(36, 5, RAM_DEPTH))
    _hand_off(a)
    return a.resolve()


def build_nested_handler():
    """First capture arms a second event; the nested capture exits the guest.

    Under R2 an entry while the handler runs overwrites cg9 as usual (the
    event is not parked behind a "live frame"): the nested handler sees
    prev_mode = supv / prev_cfx = cfx_hart and a capture bitmap that is exactly
    the new source set.  The guest exits from the nested instance, so no
    unwinding is needed.
    """
    a = Asm()
    _record_capture(a)
    # Nested capture (seq became 2): assert the overwrite and end the case.
    a.emit(ld_o(36, 5, RAM_SEQ))
    a.emit(*load_rd(37, 2))
    nested = "nest_capture_%d" % len(a.words)
    a.br("eq", 36, 37, nested)
    # First capture: arm TIMER so it expires at the current cycle, then idle.
    # The expiry sets pending bit 15 and the running mode's (smon) mask decides
    # delivery, i.e. the second entry.
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 36))
    a.emit(add_si(36, -1))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 36))
    a.emit(*load_rd(36, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 36))
    delay_loop(a, 20000, "nest")        # the nested capture exits the guest
    a.emit(*exit_seq(0x0C1))             # no nested entry happened
    a.mark(nested)
    # The nested capture must be exactly the TIMER source (overwrite, not union).
    a.emit(*load_rd(37, SRC_TIMER))
    nok0 = "nest_frame"
    a.br("eq", 30, 37, nok0)
    a.emit(*exit_seq(0x0C2))
    a.mark(nok0)
    # It entered from supv / cfx_hart: the first handler was still running.
    a.emit(*load_rd(37, 2))
    nok1 = "nest_mode"
    a.br("eq", 33, 37, nok1)
    a.emit(*exit_seq(0x0C3))
    a.mark(nok1)
    a.emit(*load_rd(37, HART_HA))
    nok2 = "nest_cfx"
    a.br("eq", 34, 37, nok2)
    a.emit(*exit_seq(0x0C4))
    a.mark(nok2)
    # The first handler was still running: depth was non-zero at this entry.
    a.emit(ld_o(37, 5, RAM_REENT))
    a.emit(*load_rd(38, 1))
    nokr = "nest_reent"
    a.br("eq", 37, 38, nokr)
    a.emit(*exit_seq(0x0C8))
    a.mark(nokr)
    # cause_ip points inside the async-handler slot (the interrupted handler).
    a.emit(*load_rd(37, ROM_BASE + OFF_FRAME_HND))
    a.emit(cmp_uo(38, 32, 37))
    nok3 = "nest_ip"
    a.br("nn", 38, 0, nok3)
    a.emit(*exit_seq(0x0C5))
    a.mark(nok3)
    # Pending was consumed by the capture; both sources were captured once.
    a.emit(*load_rd(37, SRC_TIMER))
    a.emit(and_o(38, 31, 37))
    nok4 = "nest_pending"
    a.br("z", 38, 0, nok4)
    a.emit(*exit_seq(0x0C6))
    a.mark(nok4)
    a.emit(ld_o(37, 5, RAM_PMEM_N))
    a.emit(*load_rd(38, 1))
    nok5 = "nest_counts"
    a.br("eq", 37, 38, nok5)
    a.emit(*exit_seq(0x0C7))
    a.mark(nok5)
    a.emit(*exit_seq(EXIT_PASS))
    return a.resolve()


def build_smon_handler():
    """cfx_smon supv vector: async hand-off return, or sync-cause recorder.

    The hand-off (`RAM_HANDOFF = 1`) rebuilds cfx_smon's `cg5` frame from the
    capture the async handler copied into RAM — the software-side equivalent of
    entering smon and returning to the interrupted context — then `escape`s to
    the capture's `cause_ip` with offset 0.  A sync exception raised inside the
    async handler (ILLI / CFXREG / CFXESC) is recorded and skipped.
    """
    a = Asm()
    a.emit(ld_o(30, 5, RAM_HANDOFF))
    sync_path = "smon_sync_%d" % len(a.words)
    a.br("z", 30, 0, sync_path)
    # Hand-off: rewrite the cfx_smon cg5 frame (rc0/rc1/rc3 are software-writable)
    # from the copied capture, then return to its cause_ip.
    a.emit(ld_o(30, 5, RAM_LAST_PREVM))
    a.emit(cfx2rc(SMON_HA, 5, 0, 30))
    a.emit(ld_o(30, 5, RAM_LAST_PREVC))
    a.emit(cfx2rc(SMON_HA, 5, 1, 30))
    a.emit(ld_o(30, 5, RAM_LAST_IP))
    a.emit(cfx2rc(SMON_HA, 5, 3, 30))
    a.emit(*load_rd(30, 0))
    a.emit(st_o(30, 5, RAM_HANDOFF))
    a.emit(escape(SMON_HA, 0))          # cg5 frame, offset 0: capture's cause_ip
    a.emit(*exit_seq(0x7F))             # unreachable: escape switches away

    a.mark(sync_path)
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
    a.br("eq", 30, 33, cfxreg_lbl)
    a.emit(*load_rd(33, CFXESC))
    cfxesc_lbl = "s_cfxesc_%d" % len(a.words)
    after_all = "s_all_%d" % len(a.words)
    a.br("eq", 30, 33, cfxesc_lbl)
    a.br("z", 0, 0, after_all)
    a.mark(illi_lbl)
    _inc(a, RAM_ILLI_N, 32)
    a.br("z", 0, 0, after_all)
    a.mark(cfxesc_lbl)
    _inc(a, RAM_CFXESC_N, 32)
    a.br("z", 0, 0, after_all)
    a.mark(cfxreg_lbl)
    _inc(a, RAM_CFXREG_N, 32)
    a.mark(after_all)
    a.mark(after_illi)
    a.emit(escape(SMON_HA, 1))          # cg5 frame, +4: skip the bad instruction
    return a.resolve()


def build_hart_sync_handler():
    """cfx_hart's own supv sync vector: `escape` frame errors raise CFXESC in
    the *current cfx* (§5.1), i.e. here.  Record the cause and skip the
    instruction through cfx_hart's own cg5 frame."""
    a = Asm()
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_ID_RC, 30))
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_IP_RC, 31))
    _inc(a, RAM_SYNC_N, 32)
    a.emit(st_o(30, 5, RAM_SYNC_ID))
    cfxesc_lbl = "h_cfxesc_%d" % len(a.words)
    other = "h_other_%d" % len(a.words)
    a.emit(*load_rd(33, CFXESC))
    a.br("eq", 30, 33, cfxesc_lbl)
    _inc(a, RAM_ILLI_N, 32)
    a.br("z", 0, 0, other)
    a.mark(cfxesc_lbl)
    _inc(a, RAM_CFXESC_N, 32)
    a.mark(other)
    a.emit(escape(HART_HA, 1))          # cfx_hart cg5 frame, +4
    return a.resolve()


def build_poison():
    """cfx_hmon hypv vector: any monitor hop is a failure (never reached)."""
    a = Asm()
    a.emit(*exit_seq(0x7E))
    return a.resolve()


def handlers(main_extra=None, frame=False):
    return {
        OFF_MAIN_HND: build_async_handler(main_extra),
        OFF_FRAME_HND: build_nested_handler(),
        OFF_SMON_HND: build_smon_handler(),
        OFF_HART_SYNC_HND: build_hart_sync_handler(),
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


def set_mon_mask(a, ha, mask):
    """Write monitor `ha`'s cg8 rc1 async source mask (1 = masked)."""
    a.emit(*load_rd(22, mask))
    a.emit(cfx2rc(ha, MON_CG, MON_MASK_RC, 22))


def frame_rd(a, rd):
    a.emit(cfx2rd(HART_HA, 9, RC_FRAME, rd))


def pending_rd(a, rd):
    a.emit(cfx2rd(HART_HA, 9, RC_PENDING, rd))


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
    a.emit(*load_rd(W_TMP, ALL1))                    # cmp = ~0: cancel+ack
    a.emit(cfx2rc(HART_HA, HART_CG, 4, W_TMP))
    a.emit(*load_rd(W_TMP, 0))                       # ctrl = 0
    a.emit(cfx2rc(HART_HA, HART_CG, 5, W_TMP))
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
    # cfx_hart / cfx_smon: open the supv deleg for cg9 (and cg5), i.e. the
    # contract's "0x8" whole-group opening (bit3 stays hardware-fixed 1).
    ins += load_rd(21, DELEG_OPEN)
    ins += [cfx2rc(HART_HA, 3, 12, 21), cfx2rc(SMON_HA, 3, 12, 21)]
    # Let supv `trap cfx_smon` through: cfx_smon's supv cfxtrap mask (cg2 rc0)
    # bit15 = 0 (source cfxha = cfx_hart).  Needed only by the probe's software
    # hand-off (ADR-0061 D4); the hardware async entry itself is not masked.
    ins += load_rd(21, ALL1 & ~SRC_TIMER)
    ins += [cfx2rc(SMON_HA, 2, 0, 21)]
    # cfx_smon supv vector: sync-exception recorder (ILLI/CFXREG from the
    # async handler runs in supv, so this is the current-mode monitor).
    ins += load_rd(21, hmon_addr(OFF_SMON_HND))
    ins += [cfx2rc(SMON_HA, 2, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart supv sync vector: `escape` frame errors raise CFXESC in the
    # current cfx (§5.1), which inside the async handler is cfx_hart itself.
    ins += load_rd(21, hmon_addr(OFF_HART_SYNC_HND))
    ins += [cfx2rc(HART_HA, 2, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart cg9: supv async vector + fixed switch mode; masks stay at reset.
    ins += load_rd(21, hmon_addr(vector_off))
    ins += [cfx2rc(HART_HA, 9, RC_VECTOR, 21)]
    ins += load_rd(21, 2)
    ins += [cfx2rc(HART_HA, 9, RC_SWITCH, 21)]
    # Any sync exception delivered to cfx_hmon (monitor hop) => poison => FAIL.
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
      "cg9 7 slots at reset; monitor masks all-1; rc3/rc4 HW/RO")
def _cg9_reset_defaults():
    a = Asm()
    for rc, want, code in ((RC_PREV_MODE, 0, 0x001), (RC_PREV_CFX, 0, 0x002),
                           (RC_CAUSE_IP, 0, 0x003), (RC_FRAME, 0, 0x004),
                           (RC_PENDING, 0, 0x005)):
        a.emit(cfx2rd(HART_HA, 9, rc, 5))
        need_eq(a, 5, want, code, "d%d" % rc)
    a.emit(cfx2rd(HART_HA, 9, RC_SWITCH, 5))
    need_eq(a, 5, 2, 0x006, "swmode")
    a.emit(cfx2rd(HART_HA, 9, RC_VECTOR, 5))
    need_eq(a, 5, hmon_addr(OFF_MAIN_HND), 0x007, "vector")
    # The two bitmaps are hardware-write/software-read-only: a write is ignored
    # and produces no exception.
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, 9, RC_FRAME, 22))
    a.emit(cfx2rc(HART_HA, 9, RC_PENDING, 22))
    a.emit(cfx2rd(HART_HA, 9, RC_FRAME, 6))
    need_eq(a, 6, 0, 0x008, "ro_frame")
    a.emit(cfx2rd(HART_HA, 9, RC_PENDING, 7))
    need_eq(a, 7, 0, 0x009, "ro_pending")
    # Both monitors' async masks are all-1 (masked) at reset.
    for ha, code in ((HMON_HA, 0x00A), (SMON_HA, 0x00B)):
        a.emit(cfx2rd(ha, MON_CG, MON_MASK_RC, 8))
        need_eq(a, 8, ALL1, code, "mask%d" % ha)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("timer_frame_hart",
      "TIMER -> capture bit15, prev hypv/hmon; capture kept after the return")
def _timer_frame_hart():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)       # open TIMER only
    timer_arm_window(a, tag="tfh")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "tfh", 0x011, 0x012)
    ram_ld(a, RAM_LAST_FRAME, 5)
    need_eq(a, 5, SRC_TIMER, 0x013, "capture")
    ram_ld(a, RAM_LAST_PENDING, 6)
    need_eq(a, 6, 0, 0x014, "pending_consumed")
    ram_ld(a, RAM_LAST_PREVM, 7)
    need_eq(a, 7, 3, 0x015, "prev_mode")
    ram_ld(a, RAM_LAST_PREVC, 8)
    need_eq(a, 8, HMON_HA, 0x016, "prev_cfx")
    # cause_ip: 4-byte aligned, inside the body, at/after the arm marker.
    ram_ld(a, RAM_LAST_IP, 10)
    a.emit(*load_rd(24, 3))
    a.emit(and_o(23, 10, 24))
    need_eq(a, 23, 0, 0x017, "ip_align")
    need_mask_set(a, 10, ALL1, 0x018, "ip_nonzero")
    need_mask_clr(a, 10, ~((ROM_BASE + 0x1000) - 1), 0x019, "ip_range")
    ram_ld(a, RAM_ARM_IP, 11)
    a.emit(cmp_uo(24, 10, 11))
    a.br("nn", 24, 0, "ip_after_arm")
    a.emit(*exit_seq(0x01A))
    a.mark("ip_after_arm")
    # One entry; cfx_hart's counter counts entries, not sources.
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 12))
    need_eq(a, 12, 1, 0x01B, "async_num")
    # The capture is a snapshot, not a live frame: it stays readable after the
    # software hand-off (no clear, no valid bit), and the pending bit is gone.
    frame_rd(a, 13)
    need_eq(a, 13, SRC_TIMER, 0x01C, "capture_kept")
    pending_rd(a, 14)
    need_mask_clr(a, 14, SRC_TIMER, 0x01D, "pending_cleared")
    delay_loop(a, 3000, "quiet")
    ram_ld(a, RAM_TIMER_N, 15)
    need_eq(a, 15, 1, 0x01E, "no_extra_entry")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("pmem_frame_hart",
      "PMEM_DMA -> cfx_hart frame bit32, not source cfx / monitor")
def _pmem_frame_hart():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_PMEM)        # open PMEM only
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "pfh", 0x021, 0x022)
    ram_ld(a, RAM_LAST_FRAME, 5)
    need_eq(a, 5, SRC_PMEM, 0x023, "frame")
    ram_ld(a, RAM_LAST_PREVM, 6)
    need_eq(a, 6, 3, 0x024, "prev_mode")
    ram_ld(a, RAM_LAST_PREVC, 7)
    need_eq(a, 7, HMON_HA, 0x025, "prev_cfx")
    # Delivery target witness: neither the source cfx nor the monitor entered.
    a.emit(cfx2rd(PMEM_HA, 4, CG4_ASYNC_NUM_RC, 8))
    need_eq(a, 8, 0, 0x026, "src_no_entry")
    a.emit(cfx2rd(HMON_HA, 4, CG4_ASYNC_NUM_RC, 9))
    need_eq(a, 9, 0, 0x027, "monitor_no_entry")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 10))
    need_eq(a, 10, 1, 0x028, "hart_entry")
    frame_rd(a, 11)
    need_eq(a, 11, SRC_PMEM, 0x029, "capture_kept")
    dma_status_clear(a)                               # source ack
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("mask_index_source",
      "mask bit = source cfxha 15; bit17 opens nothing")
def _mask_index_source():
    a = Asm()
    # Phase 1: source bit15 open -> delivered.
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm_window(a, tag="mi1")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "mi1", 0x031, 0x032)
    # Phase 2: bit15 masked, bit17 open -> still blocked; pending is bit15 only.
    set_mon_mask(a, HMON_HA, ALL1 & ~(1 << 17))
    timer_arm_window(a, base_seq=1, base_hart=1, tag="mi2")
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, SRC_TIMER), False, "mi2",
              0x033, 0x034)
    ram_ld(a, RAM_TIMER_N, 5)
    need_eq(a, 5, 1, 0x035, "blocked")
    pending_rd(a, 6)
    need_mask_set(a, 6, SRC_TIMER, 0x036, "pend15")
    need_mask_clr(a, 6, 1 << 17, 0x037, "no_pend17")
    frame_rd(a, 7)
    need_eq(a, 7, SRC_TIMER, 0x038, "capture_unchanged")
    # Phase 3: release the monitor mask -> delivery (one more capture).
    set_mon_mask(a, HMON_HA, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 2), True, "mi3", 0x039, 0x03A)
    pending_rd(a, 8)
    need_mask_clr(a, 8, SRC_TIMER, 0x03B, "pend_cleared")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("mode_mask_row",
      "delivery evaluates the running mode's monitor mask (hypv -> hmon)")
def _mode_mask_row():
    a = Asm()
    # Body runs hypv: hmon row masked, smon row open -> must still block.
    set_mon_mask(a, HMON_HA, ALL1)
    set_mon_mask(a, SMON_HA, 0)
    timer_arm_window(a, tag="mm1")
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, SRC_TIMER), False, "mm1",
              0x041, 0x042)
    ram_ld(a, RAM_TIMER_N, 5)
    need_eq(a, 5, 0, 0x043, "blocked_hypv")
    # Open the hypv row -> the event is delivered.
    set_mon_mask(a, HMON_HA, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "mm2", 0x044, 0x045)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("one_frame_multi",
      "TIMER+PMEM pending => one frame, bitmap union, async_num +1")
def _one_frame_multi():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1)                    # both masked
    dma_status_clear(a)
    timer_arm_window(a, tag="ofm")
    dma_start(a)
    dma_wait(a)
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, SRC_TIMER), False, "ofm0",
              0x04F, 0x050)
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, SRC_PMEM), False, "ofm1",
              0x051, 0x052)
    # Both events are pending and no frame has entered yet.
    pending_rd(a, 5)
    need_mask_set(a, 5, SRC_TIMER, 0x053, "p15")
    need_mask_set(a, 5, SRC_PMEM, 0x054, "p32")
    ram_ld(a, RAM_SEQ, 6)
    need_eq(a, 6, 0, 0x055, "none_yet")
    frame_rd(a, 7)
    need_eq(a, 7, 0, 0x056, "no_capture")
    # One mask write opens both; one instruction boundary => one capture.
    set_mon_mask(a, HMON_HA, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_SEQ, 1), True, "ofm2", 0x057, 0x058)
    ram_ld(a, RAM_LAST_FRAME, 8)
    need_eq(a, 8, SRC_BOTH, 0x059, "union")
    ram_ld(a, RAM_LAST_PENDING, 9)
    need_eq(a, 9, 0, 0x05A, "consumed")
    ram_ld(a, RAM_TIMER_N, 10)
    need_eq(a, 10, 1, 0x05B, "timer_in_capture")
    ram_ld(a, RAM_PMEM_N, 11)
    need_eq(a, 11, 1, 0x05C, "pmem_in_capture")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 12))
    need_eq(a, 12, 1, 0x05D, "one_entry")
    frame_rd(a, 13)
    need_eq(a, 13, SRC_BOTH, 0x05E, "capture_kept")
    delay_loop(a, 5000, "no_second")
    ram_ld(a, RAM_SEQ, 14)
    need_eq(a, 14, 1, 0x05F, "not_serial")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("dedup_same_source",
      "two PMEM completions while masked merge into one pending bit/frame")
def _dedup_same_source():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    pending_rd(a, 5)
    need_mask_set(a, 5, SRC_PMEM, 0x061, "pending")
    ram_ld(a, RAM_SEQ, 6)
    need_eq(a, 6, 0, 0x062, "none_yet")
    set_mon_mask(a, HMON_HA, 0)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_PMEM_N, 1), True, "dd", 0x063, 0x064)
    delay_loop(a, 5000, "still")
    ram_ld(a, RAM_PMEM_N, 7)
    need_eq(a, 7, 1, 0x065, "still_once")
    ram_ld(a, RAM_SEQ, 8)
    need_eq(a, 8, 1, 0x066, "one_frame")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("overwrite_two_entries",
      "two entries: the second overwrites cg9 (no src_frame gate, no pending block)")
def _overwrite_two_entries():
    a = Asm()
    set_mon_mask(a, HMON_HA, 0)                       # open TIMER + PMEM
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_SEQ, 1), True, "ow1", 0x0B1, 0x0B2)
    ram_ld(a, RAM_LAST_FRAME, 5)
    need_eq(a, 5, SRC_PMEM, 0x0B3, "first_capture")
    # The first capture is still in cg9 (nothing cleared it): the second entry
    # therefore happens with src_frame != 0 and must overwrite it anyway.
    frame_rd(a, 6)
    need_eq(a, 6, SRC_PMEM, 0x0B4, "first_kept")
    ram_ld(a, RAM_SEQ, 7)
    need_eq(a, 7, 1, 0x0B5, "seq1")
    timer_arm_window(a, base_seq=1, base_hart=0, tag="ow2")
    settle_bound(a)
    wait_cond(a, W_BOUND, _count_cond(RAM_SEQ, 2), True, "ow3", 0x0B6, 0x0B7)
    ram_ld(a, RAM_LAST_FRAME, 8)
    need_eq(a, 8, SRC_TIMER, 0x0B8, "second_overwrites")
    ram_ld(a, RAM_LAST_PENDING, 9)
    need_eq(a, 9, 0, 0x0B9, "pending_consumed")
    ram_ld(a, RAM_LAST_PREVM, 10)
    need_eq(a, 10, 3, 0x0BA, "second_prev_mode")
    ram_ld(a, RAM_LAST_PREVC, 11)
    need_eq(a, 11, HMON_HA, 0x0BB, "second_prev_cfx")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 12))
    need_eq(a, 12, 2, 0x0BC, "two_entries")
    ram_ld(a, RAM_TIMER_N, 13)
    need_eq(a, 13, 1, 0x0BD, "timer_once")
    ram_ld(a, RAM_PMEM_N, 14)
    need_eq(a, 14, 1, 0x0BE, "pmem_once")
    delay_loop(a, 3000, "quiet2")
    ram_ld(a, RAM_SEQ, 15)
    need_eq(a, 15, 2, 0x0BF, "no_extra_entry")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


@case("nested_capture",
      "entry inside the async handler overwrites cg9 (smon nesting by software)")
def _nested_capture():
    a = Asm()
    # Body (hypv/hmon) opens PMEM; the handler (supv) opens TIMER so its own
    # armed event is delivered while it runs.
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_PMEM)
    set_mon_mask(a, SMON_HA, ALL1 & ~SRC_TIMER)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    settle_bound(a)
    delay_loop(a, 20000, "nested")    # the nested capture exits the guest
    a.emit(*exit_seq(0x0C0))          # no nested capture happened
    return build_rom(a.resolve(), handlers(),
                     vector_off=OFF_FRAME_HND), {"exit": EXIT_PASS}


@case("ack_semantics",
      "timer_cmp reload / dma_status W1C drop src_pending; no stale delivery")
def _ack_semantics():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1)                    # keep everything masked
    # TIMER: an event is pending, then the source is acked by re-writing cmp.
    timer_arm_window(a, tag="ack1")
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, SRC_TIMER), False, "ack1",
              0x081, 0x082)
    a.emit(*load_rd(22, ALL1))                        # cmp = ~0: cancel + ack
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))
    pending_rd(a, 5)
    need_mask_clr(a, 5, SRC_TIMER, 0x083, "timer_ack")
    # Opening the mask now must not deliver a stale event.
    set_mon_mask(a, HMON_HA, 0)
    delay_loop(a, 3000, "quiet_t")
    ram_ld(a, RAM_TIMER_N, 6)
    need_eq(a, 6, 0, 0x084, "no_stale_timer")
    # PMEM: completion pending, then W1C dma_status acks it.
    set_mon_mask(a, HMON_HA, ALL1)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    wait_cond(a, W_BOUND, _mask_cond(pending_rd, SRC_PMEM), False, "ack2",
              0x085, 0x086)
    dma_status_clear(a)                               # W1C ack
    pending_rd(a, 7)
    need_mask_clr(a, 7, SRC_PMEM, 0x087, "dma_ack")
    set_mon_mask(a, HMON_HA, 0)
    delay_loop(a, 3000, "quiet_p")
    ram_ld(a, RAM_PMEM_N, 8)
    need_eq(a, 8, 0, 0x088, "no_stale_dma")
    ram_ld(a, RAM_SEQ, 9)
    need_eq(a, 9, 0, 0x089, "no_frame")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers()), {"exit": EXIT_PASS}


def _ill_extra():
    """Bad escape encodings: 3 (cg9 +4) and 4 ([17:2] SBZ nonzero)."""
    return [escape(HART_HA, 3), escape(HART_HA, 4)]


@case("escape_ill",
      "escape imms18=3 and [17:2]!=0 => ILLI in supv (recorded), then hand-off")
def _escape_ill():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm_window(a, tag="ei")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "ei", 0x091, 0x092)
    ram_ld(a, RAM_ILLI_N, 5)
    need_eq(a, 5, 2, 0x093, "illi_twice")
    ram_ld(a, RAM_CFXREG_N, 6)
    need_eq(a, 6, 0, 0x094, "no_cfxreg")
    ram_ld(a, RAM_CFXESC_N, 7)
    need_eq(a, 7, 0, 0x095, "no_cfxesc")
    frame_rd(a, 8)
    need_eq(a, 8, SRC_TIMER, 0x096, "capture_untouched")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers(main_extra=_ill_extra())), {"exit": EXIT_PASS}


def _no_async_return_extra():
    """escape imms18 = 2 (cg9 frame selector): not an async return."""
    return [escape(HART_HA, 2)]


@case("escape_no_async_return",
      "escape imms18=2 => CFXESC; cg9/run mode/cfx unchanged (R2)")
def _escape_no_async_return():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm_window(a, tag="enr")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "enr", 0x0A5, 0x0A6)
    # The extra `escape hart, 2` ran inside the capture and must have raised
    # CFXESC in supv: recorded by the cfx_smon vector, no return to the body.
    ram_ld(a, RAM_CFXESC_N, 5)
    need_eq(a, 5, 1, 0x0A7, "cfxesc_once")
    ram_ld(a, RAM_ILLI_N, 6)
    need_eq(a, 6, 0, 0x0A8, "no_illi")
    ram_ld(a, RAM_CFXREG_N, 7)
    need_eq(a, 7, 0, 0x0A9, "no_cfxreg")
    ram_ld(a, RAM_LAST_FRAME, 8)
    need_eq(a, 8, SRC_TIMER, 0x0AA, "capture_kept")
    frame_rd(a, 9)
    need_eq(a, 9, SRC_TIMER, 0x0AB, "cg9_unchanged")
    ram_ld(a, RAM_LAST_PREVM, 10)
    need_eq(a, 10, 3, 0x0AC, "prev_untouched")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 11))
    need_eq(a, 11, 1, 0x0AD, "one_entry")
    ram_ld(a, RAM_SEQ, 12)
    need_eq(a, 12, 1, 0x0AE, "one_capture")
    delay_loop(a, 3000, "quiet_esc")
    ram_ld(a, RAM_SEQ, 13)
    need_eq(a, 13, 1, 0x0AF, "still_one_capture")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), handlers(main_extra=_no_async_return_extra())), \
        {"exit": EXIT_PASS}


def _reserved_extra():
    """Reserved cg9 rc13/rc15: each access must raise CFXREG."""
    return [cfx2rd(HART_HA, 9, 13, 39), cfx2rd(HART_HA, 9, 15, 39)]


@case("cg9_reserved",
      "cg9 rc13/rc15 are reserved: read => CFXREG (not silently 0)")
def _cg9_reserved():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm_window(a, tag="cr")
    wait_cond(a, W_BOUND, _count_cond(RAM_TIMER_N, 1), True, "cr", 0x0A1, 0x0A2)
    ram_ld(a, RAM_CFXREG_N, 5)
    need_eq(a, 5, 2, 0x0A3, "cfxreg_twice")
    ram_ld(a, RAM_ILLI_N, 6)
    need_eq(a, 6, 0, 0x0A4, "no_illi")
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
    """Return the «统一异步中断» bullet body (empty string when absent)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("- **统一异步中断"):
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
          "«统一异步中断» bullet found" if entry else "MISSING bullet")
    for token, why in (
            ("async_src_pending", "the single pending bitmap is named"),
            ("cfx_hart cg9 rc4", "pending lives in cg9 rc4"),
            ("源 cfxha", "source identity is the source cfxha"),
            ("投递目标 = `cfx_hart`", "hart-first delivery target named"),
            ("一帧多源", "one-frame multi-source is defined"),
            ("不串行", "no serial split of one boundary"),
            ("每次进入覆盖", "every entry overwrites the capture"),
            ("frame_valid", "the absent valid bit is named"),
            ("task_pt_regs", "software copies the capture out and returns via smon"),
            ("不引入", "no async_enable-style gate"),
            ("async_enable", "async_enable named as not introduced"),
            ("ADR-0061", "the revision decision is cited"),
    ):
        check("entry_%s" % token.replace(" ", "_").replace("`", ""), token in entry, why)

    patches = _patch_text()
    check("patch_no_monitor_pending", "env->cfx[ci].pending |=" not in patches,
          "no target/monitor cg5 pending writes remain")
    check("patch_no_async_enable", "async_enable" not in patches,
          "no async_enable field")
    check("patch_cg9_pending", "async.src_pending" in patches,
          "pending lives in cfx_hart cg9 rc4")
    check("patch_cg9_frame", "a->src_frame" in patches,
          "the frame bitmap lives in cfx_hart cg9 rc3")
    check("patch_no_macro_cause",
          "DADAO_CAUSE_TIMER" not in patches and
          "DADAO_CAUSE_PMEM_DMA" not in patches,
          "no macro cause ids 1<<17 / 1<<18")
    check("patch_mask_on_monitor", "async_intr_mask" in patches,
          "the source mask is the monitor's cg8 rc1")
    check("patch_no_cg9_masks",
          "mode_intr_mask" not in patches and
          "global_cfx_intr_mask" not in patches,
          "no five-mask / saved-mask state on cfx_hart")

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
    allowed = _function_body(src, "static uint64_t dadao_async_allowed")
    enter = _function_body(src, "static bool dadao_async_enter(CPUDADAOState *env")
    check("arbitrate_found", bool(arbitrate), "arbiter body extracted")
    check("async_enter_found", bool(enter), "hart-first entry body extracted")
    check("mask_from_running_mode", "async_intr_mask" in allowed and
          "dadao_async_allowed(env)" in arbitrate,
          "the running mode monitor's cg8 rc1 decides delivery")
    check("frame_union", "a->src_frame = src_bits" in enter and
          "src_pending &= ~src_bits" in enter,
          "src_frame is the union and pending is consumed")
    check("single_async_entry", arbitrate.count("dadao_async_enter(") == 1,
          "one async entry call site (count=%d)" %
          arbitrate.count("dadao_async_enter("))
    for bad in ("mode_intr_mask", "global_intr_mask", "cause_id"):
        check("enter_no_%s" % bad, bad not in enter,
              "no cfx_hart mask/cause state in the entry")
    # ADR-0061 R2: cg9 is a capture buffer.  No entry gate on a previous
    # capture, no validity bit, and `escape` never returns through cg9.
    escape_body = _function_body(src, "void helper_cfx_escape(")
    check("no_capture_gate", "src_frame != 0" not in allowed,
          "a previous capture never blocks a new entry")
    check("enter_overwrites", "a->src_frame = src_bits" in enter,
          "each entry overwrites the capture bitmap")
    check("escape_no_cg9_frame",
          "src_frame" not in escape_body and "sel & 0x2u" in escape_body,
          "escape never reads/clears cg9 (cg9 selector => CFXESC)")
    check("no_macro_cause_check", "DADAO_CAUSE_MACRO16" not in src and
          "DADAO_CAUSE_TIMER" not in src,
          "dadao_cause_check has no macro-cause branch")
    check("ro_bitmap_writes_ignored",
          "case 3:" in src and "case 4:" in src and
          "HW/RO, write ignored" in src,
          "cg9 rc3/rc4 writes are ignored, not errors")

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
