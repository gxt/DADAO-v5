#!/usr/bin/env python3
"""TESTCASES-094t §2: minimal two-cfx asynchronous-capture probe (ADR-0061 R2).

Purpose (ownership decision, not a replacement for INTEG-050t/051t): decide
whether a failure to deliver TIMER (source cfxha 15) / PMEM_DMA (source cfxha
32) is a *test-asset* or a *QEMU* defect.  The probe contains no SBI provider,
no harness beyond what is needed to observe deliveries, and no INTEG-050t/051t
code.

Model under test (ADR-0061 R2, spec/DADAO-12 §4.7/§5.1/§5.4):

  * every asynchronous source is delivered to ``cfx_hart`` (cfxha 15) through
    its supv single vector ``cg15 rc15`` / ``rc6``; the source identity is the
    *source cfxha* (TIMER 15, PMEM_DMA 32), never an ``excp_cause_id``;
  * ``cfx_hart cg15 rc4`` is the capture bitmap and ``rc4`` the pending bitmap
    (both HW/RO; a software write changes nothing); ``rc0``–``rc2`` are the
    pre-entry mode/cfx/cause_ip snapshot;
  * delivery is gated only by the **running mode monitor**'s ``cg15 rc3`` mask
    (bit = source cfxha, 1 = masked, reset all-1).  A masked source only sets
    ``cg15 rc5``; opening the mask delivers it;
  * one instruction boundary merges every pending-allowed source into a single
    capture (frame = bitmap union, pending -= frame, ``excp_async_num`` +1);
  * cg15 is a **capture buffer**, not a live frame: every entry overwrites it
    (no ``src_frame != 0`` gate, no ``frame_valid``, no software clear);
  * ``escape imms18 = 2`` (cg15 selector) is not an asynchronous return: the
    selected frame is invalid, so the current cfx raises ``CFXESC`` and nothing
    changes.  ``imms18 = 3`` and a non-zero SBZ field raise ``ILLI``.

Expectations are derived by hand from the frozen spec / contract:
  - spec/DADAO-12 §4.7 (cfx_hart cg15 seven slots, timer), §4.9 (cfx_pmem DMA),
    §5.1 (escape frame selector), §5.4 (capture buffer, mask/pending, one
    frame, every entry overwrites), §3.6 (cause ids);
  - .tao/contracts/contract-see.md §3 «统一异步中断» (hart-first, one frame);
  - ADR-0061 R2.
Never from the QEMU implementation.

Bootstrap (body runs in hmon / cfx3, hypv, via the shared prelude):
  1. open ``cfx_hart`` / ``cfx_smon`` for supv (``hypv_cg_reg_deleg = 0x8``)
     and let ``trap cfx_smon`` through (cfx_smon's supv cfxtrap bit 15 = 0);
  2. install ``cfx_hart cg15 rc15`` = async capture handler, ``rc6`` = supv (2);
  3. install cfx_smon's supv vector = capture hand-off / sync recorder and
     cfx_hart's own supv vector = ``escape`` frame-error recorder;
  4. poison cfx_hmon's hypv vector (any monitor hop would exit FAIL);
  5. leave every monitor mask at reset (all-1); each case opens the source
     bits it needs through ``cfx2rc cfx_hmon, cg15, rc3``.

Observation: everything is checked in-program and reported through the
semihosting SYS_EXIT code (0 = pass).  Cases read the capture and counters
the handler copied to RAM; no ``-d cpu`` dump is used.

Usage:
  min_rom_probe_async_094t.py [--qemu PATH] [--only NAME] [--list]
Exit code: 0 iff every requested case passed.
"""

import argparse
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
for _sub in (("tools", "testcases", "lib"), ("tools", "testcases", "arch"),
             ("tools", "infra")):
    _p = os.path.join(_REPO, *_sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import node_probe_prelude as _prelude  # noqa: E402

DEFAULT_QEMU = _prelude.default_qemu()
QEMU = DEFAULT_QEMU
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_async_094t")
TIMEOUT = 60

ROM_BASE = _prelude.ROM_BASE
RAM_BASE = _prelude.RAM_BASE

HART_HA, PMEM_HA, SMON_HA, HMON_HA = 15, 32, 2, 3
HART_CG, HART_TIMER_CG, PMEM_DMA_CG = 8, 16, 15
MON_CG, MON_MASK_RC = 15, 3

# cfx_hart cg15 (DADAO-12 §4.7; ADR-0061 D7): rc0..rc6, rc7-rc15 reserved.
RC_PREV_MODE, RC_PREV_CFX, RC_CAUSE_IP = 0, 1, 2
RC_FRAME, RC_PENDING, RC_VECTOR, RC_SWITCH = 4, 5, 15, 14
# cg5 sync frame / cg4 counters / cg3 vectors+delegation.
CG5_CAUSE_ID_RC = 2
CG4_ASYNC_NUM_RC = 4
CG3_EXCP_VECTOR_RC, CG3_DELEG_RC = 15, 12

# Source identity = source cfxha (ADR-0061 D2/D3).
SRC_TIMER = 1 << HART_HA
SRC_PMEM = 1 << PMEM_HA
SRC_BOTH = SRC_TIMER | SRC_PMEM

ILLI = 1 << 8
CFXESC = 1 << 3
CTRL_ENABLE = 1 << 0
CTRL_START = 1 << 0
ST_BUSY = 1 << 0
ST_DONE = 1 << 1
ST_ERROR = 1 << 2
ALL1 = (1 << 64) - 1
DELEG_OPEN = 0xFFFFFFFFFFFE7FC7

PMEM_SRC = _prelude.PMEM_BASE
DATA_PA = RAM_BASE + 0x4000

# Body-relative handler slots (0x400 apart: the smon handler holds the capture
# hand-off plus the sync-cause recorder).
OFF_ASYNC_HND = 0x2000
OFF_SMON_HND = 0x2400
OFF_HART_SYNC_HND = 0x2800
OFF_POISON = 0x2C00

# RAM state block; rb5 = RAM_BASE and every slot stays below 0x800 (the ld/st
# imm12 field is sign-extended, 0x800 would address cfx_power's BootROM).
RAM_SEQ = 0x020          # async entries so far
RAM_FRAME = 0x028        # cg15 rc4 at entry
RAM_PENDING = 0x030      # cg15 rc5 at entry
RAM_IP = 0x038           # cg15 rc2 at entry
RAM_PREVM = 0x040        # cg15 rc0 at entry
RAM_PREVC = 0x048        # cg15 rc1 at entry
RAM_TIMER_N = 0x050      # entries carrying bit 15
RAM_PMEM_N = 0x058       # entries carrying bit 32
RAM_CFXESC_N = 0x060     # sync CFXESC recorded inside the handler
RAM_ILLI_N = 0x068       # sync ILLI recorded inside the handler
RAM_HANDOFF = 0x070      # 1 while the handler hands off to cfx_smon
RAM_ARM_IP = 0x078       # body address that armed the current timer

# Timing-model-neutral bounds (TESTCASES-102t): QEMU drives the virtual clock
# from host time, so arm a 10 ms relative deadline and poll with a bounded
# iteration count (a lost event still terminates in failure).
DELTA_NS = 10_000_000
ARM_RETRIES = 8
MAX_WAIT = 4_000_000
MAX_DMA_WAIT = 300_000

W_NOW, W_CMP, W_DEAD, W_MAX, W_TMP = 20, 21, 22, 23, 24


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
def add_si(rd, imms18):      return (0x59 << 24) | (rd << 18) | (imms18 & 0x3FFFF)
def cfx2rd(ha, cg, rc, rd):  return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def cfx2rc(ha, cg, rc, rd):  return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def trap(ha, immu18):        return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
def escape(ha, imms18):      return (0x7E << 24) | (ha << 18) | (imms18 & 0x3FFFF)


def _orrr(op, ha, hb, hc, hd):
    return (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd


def and_o(rdhb, rdhc, rdhd):  return _orrr(0x40, 0x08, rdhb, rdhc, rdhd)
def cmp_uo(rdhb, rdhc, rdhd): return _orrr(0x40, 0x2A, rdhb, rdhc, rdhd)
def add_uo(lo, hi, a, b):     return _orrr(0x50, hi, lo, a, b)


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
# Handlers: capture recorder + smon hand-off + sync-frame recorder + poison
# ---------------------------------------------------------------------------

def _inc(a, off, rd):
    a.emit(ld_o(rd, 5, off))
    a.emit(add_si(rd, 1))
    a.emit(st_o(rd, 5, off))


def _count_source(a, frame_rd, srcbit, off, tag):
    """Increment `off` once when bit `srcbit` is in the capture bitmap."""
    skip = "src_%s_%d" % (tag, len(a.words))
    a.emit(*load_rd(38, srcbit))
    a.emit(and_o(38, frame_rd, 38))
    a.br("z", 38, 0, skip)
    _inc(a, off, 36)
    a.mark(skip)


def _record_capture(a):
    """Copy the cg15 capture into RAM before anything else can overwrite it."""
    a.emit(cfx2rd(HART_HA, 15, RC_FRAME, 30))
    a.emit(cfx2rd(HART_HA, 15, RC_PENDING, 31))
    a.emit(cfx2rd(HART_HA, 15, RC_CAUSE_IP, 32))
    a.emit(cfx2rd(HART_HA, 15, RC_PREV_MODE, 33))
    a.emit(cfx2rd(HART_HA, 15, RC_PREV_CFX, 34))
    a.emit(ld_o(36, 5, RAM_SEQ))
    a.emit(add_si(36, 1))
    a.emit(st_o(36, 5, RAM_SEQ))
    a.emit(st_o(30, 5, RAM_FRAME))
    a.emit(st_o(31, 5, RAM_PENDING))
    a.emit(st_o(32, 5, RAM_IP))
    a.emit(st_o(33, 5, RAM_PREVM))
    a.emit(st_o(34, 5, RAM_PREVC))
    _count_source(a, 30, SRC_TIMER, RAM_TIMER_N, "t")
    _count_source(a, 30, SRC_PMEM, RAM_PMEM_N, "p")


def build_async_handler(extra=None):
    """Record the capture, run optional in-handler probes, then hand off.

    `extra` words run after the capture has been copied to RAM (ILLI/CFXESC
    encoding cases); they must not rely on rd30..rd39 surviving.
    """
    a = Asm()
    _record_capture(a)
    if extra:
        a.emit(*extra)
    a.emit(*load_rd(36, 1))
    a.emit(st_o(36, 5, RAM_HANDOFF))
    a.emit(trap(SMON_HA, 0))            # cfx_smon supv vector = hand-off
    a.emit(*exit_seq(0x6F))             # unreachable on a correct return
    return a.resolve()


def build_smon_handler():
    """cfx_smon supv vector: capture hand-off (or the sync-cause recorder).

    The hand-off rebuilds cfx_smon's cg5 frame from the capture the async
    handler copied to RAM (ADR-0061 D4: the software carries the capture into
    its own context and returns through smon), then `escape`s to the capture's
    `cause_ip`.  A sync exception raised inside the handler is recorded and
    skipped through the same frame.
    """
    a = Asm()
    a.emit(ld_o(30, 5, RAM_HANDOFF))
    sync_path = "smon_sync_%d" % len(a.words)
    a.br("z", 30, 0, sync_path)
    a.emit(ld_o(30, 5, RAM_PREVM))
    a.emit(cfx2rc(SMON_HA, 5, 0, 30))
    a.emit(ld_o(30, 5, RAM_PREVC))
    a.emit(cfx2rc(SMON_HA, 5, 1, 30))
    a.emit(ld_o(30, 5, RAM_IP))
    a.emit(cfx2rc(SMON_HA, 5, 3, 30))
    a.emit(*load_rd(30, 0))
    a.emit(st_o(30, 5, RAM_HANDOFF))
    a.emit(escape(SMON_HA, 0))          # cg5 frame, offset 0: capture's cause_ip
    a.emit(*exit_seq(0x7F))             # unreachable: escape switches away

    a.mark(sync_path)
    a.emit(cfx2rd(SMON_HA, 5, CG5_CAUSE_ID_RC, 30))
    cfxesc = "s_cfxesc_%d" % len(a.words)
    done = "s_done_%d" % len(a.words)
    a.emit(*load_rd(31, CFXESC))
    a.br("eq", 30, 31, cfxesc)
    _inc(a, RAM_ILLI_N, 32)
    a.br("z", 0, 0, done)
    a.mark(cfxesc)
    _inc(a, RAM_CFXESC_N, 32)
    a.mark(done)
    a.emit(escape(SMON_HA, 1))          # cg5 frame, +4: skip the bad instruction
    return a.resolve()


def build_hart_sync_handler():
    """cfx_hart's own supv vector: `escape` frame errors raise CFXESC in the
    *current cfx* (§5.1), i.e. here.  Record the cause and skip the word."""
    a = Asm()
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_ID_RC, 30))
    a.emit(*load_rd(31, CFXESC))
    cfxesc = "h_cfxesc_%d" % len(a.words)
    other = "h_other_%d" % len(a.words)
    a.br("eq", 30, 31, cfxesc)
    _inc(a, RAM_ILLI_N, 32)
    a.br("z", 0, 0, other)
    a.mark(cfxesc)
    _inc(a, RAM_CFXESC_N, 32)
    a.mark(other)
    a.emit(escape(HART_HA, 1))          # cfx_hart cg5 frame, +4
    return a.resolve()


def build_poison():
    """cfx_hmon hypv vector: any monitor hop is a failure (never reached)."""
    a = Asm()
    a.emit(*exit_seq(0x7E))
    return a.resolve()


def handlers(main_extra=None):
    return {
        OFF_ASYNC_HND: build_async_handler(main_extra),
        OFF_SMON_HND: build_smon_handler(),
        OFF_HART_SYNC_HND: build_hart_sync_handler(),
        OFF_POISON: build_poison(),
    }


# ---------------------------------------------------------------------------
# Program helpers (body runs in hmon / cfx3, hypv)
# ---------------------------------------------------------------------------

def hmon_addr(off):
    return ROM_BASE + off


def ram_ld(a, off, rd):
    a.emit(ld_o(rd, 5, off))


def need_eq(a, rd, want, code, tag):
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
    a.emit(*load_rd(22, mask))
    a.emit(cfx2rc(ha, MON_CG, MON_MASK_RC, 22))


def frame_rd(a, rd):
    a.emit(cfx2rd(HART_HA, 15, RC_FRAME, rd))


def pending_rd(a, rd):
    a.emit(cfx2rd(HART_HA, 15, RC_PENDING, rd))


def timer_arm(a, delta=DELTA_NS, tag="t"):
    """Cancel, then arm cmp = now + delta; retry if the deadline already passed."""
    retry = "ta_%s_reset" % tag
    done = "ta_%s_ok" % tag
    a.emit(*load_rd(W_MAX, ARM_RETRIES))
    a.mark(retry)
    a.emit(*load_rd(W_TMP, ALL1))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, W_TMP))        # cmp = ~0: cancel
    a.emit(*load_rd(W_TMP, 0))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, W_TMP))        # ctrl = 0
    # Lower bound for cause_ip: the arm marker is the address of this word, so
    # no capture can carry an earlier cause_ip than it.
    _idx = len(a.words)
    a.emit(*load_rd(W_TMP, ROM_BASE + 4 * _idx))
    a.emit(st_o(W_TMP, 5, RAM_ARM_IP))
    a.emit(cfx2rd(HART_HA, HART_CG, 2, W_NOW))        # cycle == cfx_time value
    a.emit(*load_rd(W_TMP, delta))
    a.emit(add_uo(W_DEAD, W_CMP, W_NOW, W_TMP))       # W_DEAD = now + delta
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, W_DEAD))
    a.emit(*load_rd(W_TMP, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, W_TMP))
    a.emit(cfx2rd(HART_HA, HART_CG, 2, W_CMP))
    a.emit(cmp_uo(W_CMP, W_CMP, W_DEAD))
    a.emit(*load_rd(W_TMP, 1))
    a.br("ne", W_CMP, W_TMP, done)                    # now < deadline -> armed
    a.emit(add_si(W_MAX, -1))
    a.br("nz", W_MAX, 0, retry)
    a.emit(*exit_seq(0x7A))                           # cannot arm in the future
    a.mark(done)


def dma_status_clear(a):
    a.emit(*load_rd(22, ST_DONE | ST_ERROR))
    a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, 4, 22))


def dma_start(a, irq_en=True):
    for rc, val in ((0, PMEM_SRC), (1, DATA_PA), (2, 8),
                    (3, CTRL_START)):
        a.emit(*load_rd(22, val))
        a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, rc, 22))


def dma_wait(a, rd=6):
    poll = "dma_poll_%d" % len(a.words)
    done = poll + "_done"
    a.emit(*load_rd(18, ST_BUSY))
    a.emit(*load_rd(20, MAX_DMA_WAIT))
    a.mark(poll)
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, 4, rd))
    a.emit(and_o(rd, rd, 18))
    a.br("z", rd, 0, done)
    a.emit(add_si(20, -1))
    a.br("nz", 20, 0, poll)
    a.emit(*exit_seq(0x7D))                           # DMA never completed
    a.mark(done)


def delay_loop(a, count, tag, rd=25):
    a.emit(*load_rd(rd, count))
    head = "dl_%s_%d" % (tag, len(a.words))
    tail = head + "_end"
    a.mark(head)
    a.br("z", rd, 0, tail)
    a.emit(add_si(rd, -1))
    a.br("nz", rd, 0, head)
    a.mark(tail)


def wait_ram(a, off, want, code_lost, tag):
    """Bounded poll until RAM[off] == want (lost => exit `code_lost`)."""
    head = "w_%s" % tag
    done = head + "_ok"
    a.emit(*load_rd(W_MAX, MAX_WAIT))
    a.mark(head)
    a.emit(ld_o(W_TMP, 5, off))
    a.emit(*load_rd(18, want))
    a.br("eq", W_TMP, 18, done)
    a.emit(add_si(W_MAX, -1))
    a.br("nz", W_MAX, 0, head)
    a.emit(*exit_seq(code_lost))
    a.mark(done)


def wait_pending(a, mask, want_set, code_lost, tag):
    """Bounded poll until cg15 rc5 has every/any of `mask` (or none of it)."""
    head = "p_%s" % tag
    done = head + "_ok"
    a.emit(*load_rd(W_MAX, MAX_WAIT))
    a.mark(head)
    a.emit(cfx2rd(HART_HA, 15, RC_PENDING, W_TMP))
    a.emit(*load_rd(18, mask))
    a.emit(and_o(W_TMP, W_TMP, 18))
    a.br("eq" if want_set else "z", W_TMP, 18, done)
    a.emit(add_si(W_MAX, -1))
    a.br("nz", W_MAX, 0, head)
    a.emit(*exit_seq(code_lost))
    a.mark(done)


# ---------------------------------------------------------------------------
# Bootstrap: supv hand-off plumbing + poison vector; masks stay at reset
# ---------------------------------------------------------------------------

def hmon_setup():
    ins = load_rb(5, RAM_BASE)                        # handler state block base
    # cfx_hart cg15 / cfx_smon cg5 for supv: whole-group opening (0x8).
    ins += load_rd(21, DELEG_OPEN)
    ins += [cfx2rc(HART_HA, 3, CG3_DELEG_RC, 21),
            cfx2rc(SMON_HA, 3, CG3_DELEG_RC, 21)]
    # Let supv `trap cfx_smon` through (cfx_smon supv cfxtrap bit 15 = 0).
    ins += load_rd(21, ALL1 & ~SRC_TIMER)
    ins += [cfx2rc(SMON_HA, 2, 0, 21)]
    # cfx_smon supv vector: capture hand-off / sync recorder.
    ins += load_rd(21, hmon_addr(OFF_SMON_HND))
    ins += [cfx2rc(SMON_HA, 2, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart's own supv vector: `escape` frame errors (CFXESC/ILLI).
    ins += load_rd(21, hmon_addr(OFF_HART_SYNC_HND))
    ins += [cfx2rc(HART_HA, 2, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart cg15: supv async vector + fixed switch mode.
    ins += load_rd(21, hmon_addr(OFF_ASYNC_HND))
    ins += [cfx2rc(HART_HA, 15, RC_VECTOR, 21)]
    ins += load_rd(21, 2)
    ins += [cfx2rc(HART_HA, 15, RC_SWITCH, 21)]
    # Any sync exception delivered to cfx_hmon (monitor hop) => poison => FAIL.
    ins += load_rd(21, hmon_addr(OFF_POISON))
    ins += [cfx2rc(HMON_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    return ins


def build_rom(prog, hnd=None):
    return _prelude.build_rom(prog, hnd, hmon_extra=hmon_setup())


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


@case("timer_capture",
      "TIMER -> one capture bit15; snapshot/async_num; capture kept after return")
def _timer_capture():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm(a, tag="tc")
    wait_ram(a, RAM_SEQ, 1, 0x011, "tc")
    ram_ld(a, RAM_FRAME, 5)
    need_eq(a, 5, SRC_TIMER, 0x012, "frame")
    ram_ld(a, RAM_PENDING, 6)
    need_eq(a, 6, 0, 0x013, "pending_consumed")
    ram_ld(a, RAM_PREVM, 7)
    need_eq(a, 7, 3, 0x014, "prev_mode")
    ram_ld(a, RAM_PREVC, 8)
    need_eq(a, 8, HMON_HA, 0x015, "prev_cfx")
    # cause_ip: 4-byte aligned, at/after the arm marker.
    ram_ld(a, RAM_IP, 10)
    a.emit(*load_rd(24, 3))
    a.emit(and_o(23, 10, 24))
    need_eq(a, 23, 0, 0x016, "ip_align")
    need_mask_set(a, 10, ALL1, 0x017, "ip_nonzero")
    ram_ld(a, RAM_ARM_IP, 11)
    a.emit(cmp_uo(24, 10, 11))
    a.br("nn", 24, 0, "tc_ip_ok")
    a.emit(*exit_seq(0x018))
    a.mark("tc_ip_ok")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 12))
    need_eq(a, 12, 1, 0x019, "async_num")
    # Entry configuration: supv single vector (cg15 rc15) + fixed switch mode 2.
    a.emit(cfx2rd(HART_HA, 15, RC_VECTOR, 13))
    need_eq(a, 13, hmon_addr(OFF_ASYNC_HND), 0x01D, "vector")
    a.emit(cfx2rd(HART_HA, 15, RC_SWITCH, 14))
    need_eq(a, 14, 2, 0x01E, "switch_mode")
    frame_rd(a, 13)                                   # capture is a snapshot
    need_eq(a, 13, SRC_TIMER, 0x01A, "capture_kept")
    pending_rd(a, 14)
    need_mask_clr(a, 14, SRC_TIMER, 0x01B, "pending_clear")
    delay_loop(a, 3000, "quiet")
    ram_ld(a, RAM_SEQ, 15)
    need_eq(a, 15, 1, 0x01C, "no_extra_entry")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers()), {"exit": 0}


@case("masked_pending_release",
      "masked TIMER only sets pending bit15; opening the mask delivers it")
def _masked_pending_release():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1)                    # everything masked
    timer_arm(a, tag="mp")
    wait_pending(a, SRC_TIMER, True, 0x021, "mp")
    ram_ld(a, RAM_SEQ, 5)
    need_eq(a, 5, 0, 0x022, "no_entry")
    frame_rd(a, 6)
    need_eq(a, 6, 0, 0x023, "no_capture")
    pending_rd(a, 7)
    need_mask_set(a, 7, SRC_TIMER, 0x024, "pending15")
    need_mask_clr(a, 7, 1 << 17, 0x025, "no_pending17")
    set_mon_mask(a, HMON_HA, 0)                       # release
    wait_ram(a, RAM_SEQ, 1, 0x026, "mpr")
    ram_ld(a, RAM_FRAME, 8)
    need_eq(a, 8, SRC_TIMER, 0x027, "frame")
    pending_rd(a, 9)
    need_mask_clr(a, 9, SRC_TIMER, 0x028, "pending_cleared")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers()), {"exit": 0}


@case("pmem_capture",
      "PMEM_DMA -> capture bit32 in cfx_hart; source cfx / monitor never enter")
def _pmem_capture():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_PMEM)
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    wait_ram(a, RAM_SEQ, 1, 0x031, "pc")
    ram_ld(a, RAM_FRAME, 5)
    need_eq(a, 5, SRC_PMEM, 0x032, "frame")
    ram_ld(a, RAM_PENDING, 6)
    need_eq(a, 6, 0, 0x033, "pending_consumed")
    ram_ld(a, RAM_PREVM, 7)
    need_eq(a, 7, 3, 0x034, "prev_mode")
    ram_ld(a, RAM_PREVC, 8)
    need_eq(a, 8, HMON_HA, 0x035, "prev_cfx")
    a.emit(cfx2rd(PMEM_HA, 4, CG4_ASYNC_NUM_RC, 9))
    need_eq(a, 9, 0, 0x036, "source_no_entry")
    a.emit(cfx2rd(HMON_HA, 4, CG4_ASYNC_NUM_RC, 10))
    need_eq(a, 10, 0, 0x037, "monitor_no_entry")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 11))
    need_eq(a, 11, 1, 0x038, "hart_entry")
    frame_rd(a, 12)
    need_eq(a, 12, SRC_PMEM, 0x039, "capture_kept")
    dma_status_clear(a)                               # source ack
    pending_rd(a, 13)
    need_mask_clr(a, 13, SRC_PMEM, 0x03A, "ack_no_pending")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers()), {"exit": 0}


@case("one_frame_multi",
      "TIMER+PMEM pending => one capture, bitmap union, async_num +1")
def _one_frame_multi():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1)                    # both masked
    dma_status_clear(a)
    timer_arm(a, tag="ofm")
    dma_start(a)
    dma_wait(a)
    wait_pending(a, SRC_TIMER, True, 0x041, "ofm0")
    wait_pending(a, SRC_PMEM, True, 0x042, "ofm1")
    ram_ld(a, RAM_SEQ, 5)
    need_eq(a, 5, 0, 0x043, "none_yet")
    frame_rd(a, 6)
    need_eq(a, 6, 0, 0x044, "no_capture")
    pending_rd(a, 7)
    need_mask_set(a, 7, SRC_BOTH, 0x045, "both_pending")
    set_mon_mask(a, HMON_HA, 0)                       # one write opens both
    wait_ram(a, RAM_SEQ, 1, 0x046, "ofm2")
    ram_ld(a, RAM_FRAME, 8)
    need_eq(a, 8, SRC_BOTH, 0x047, "union")
    ram_ld(a, RAM_PENDING, 9)
    need_eq(a, 9, 0, 0x048, "consumed")
    ram_ld(a, RAM_TIMER_N, 10)
    need_eq(a, 10, 1, 0x049, "timer_in_capture")
    ram_ld(a, RAM_PMEM_N, 11)
    need_eq(a, 11, 1, 0x04A, "pmem_in_capture")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 12))
    need_eq(a, 12, 1, 0x04B, "one_entry")
    delay_loop(a, 5000, "no_second")
    ram_ld(a, RAM_SEQ, 13)
    need_eq(a, 13, 1, 0x04C, "not_serial")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers()), {"exit": 0}


@case("overwrite_two_entries",
      "second entry overwrites cg15 (no frame gate); first capture kept until then")
def _overwrite_two_entries():
    a = Asm()
    set_mon_mask(a, HMON_HA, 0)                       # open TIMER + PMEM
    dma_status_clear(a)
    dma_start(a)
    dma_wait(a)
    wait_ram(a, RAM_SEQ, 1, 0x051, "ow1")
    ram_ld(a, RAM_FRAME, 5)
    need_eq(a, 5, SRC_PMEM, 0x052, "first_capture")
    frame_rd(a, 6)                                    # still readable: no clear
    need_eq(a, 6, SRC_PMEM, 0x053, "first_kept")
    timer_arm(a, tag="ow2")                           # second event, cg15 not empty
    wait_ram(a, RAM_SEQ, 2, 0x054, "ow3")
    ram_ld(a, RAM_FRAME, 7)
    need_eq(a, 7, SRC_TIMER, 0x055, "second_overwrites")
    ram_ld(a, RAM_PENDING, 8)
    need_eq(a, 8, 0, 0x056, "pending_consumed")
    ram_ld(a, RAM_PREVM, 9)
    need_eq(a, 9, 3, 0x057, "second_prev_mode")
    ram_ld(a, RAM_PREVC, 10)
    need_eq(a, 10, HMON_HA, 0x058, "second_prev_cfx")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 11))
    need_eq(a, 11, 2, 0x059, "two_entries")
    ram_ld(a, RAM_TIMER_N, 12)
    need_eq(a, 12, 1, 0x05A, "timer_once")
    ram_ld(a, RAM_PMEM_N, 13)
    need_eq(a, 13, 1, 0x05B, "pmem_once")
    delay_loop(a, 3000, "quiet2")
    ram_ld(a, RAM_SEQ, 14)
    need_eq(a, 14, 2, 0x05C, "no_extra_entry")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers()), {"exit": 0}


def _no_async_return_extra():
    """escape imms18 = 2 (cg15 selector): not an asynchronous return."""
    return [escape(HART_HA, 2)]


@case("escape_cg15_cfxesc",
      "escape imms18=2 => CFXESC inside the handler; cg15/counters untouched")
def _escape_cg15_cfxesc():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm(a, tag="ec")
    wait_ram(a, RAM_SEQ, 1, 0x061, "ec")
    ram_ld(a, RAM_CFXESC_N, 5)
    need_eq(a, 5, 1, 0x062, "cfxesc_once")
    ram_ld(a, RAM_ILLI_N, 6)
    need_eq(a, 6, 0, 0x063, "no_illi")
    ram_ld(a, RAM_FRAME, 7)                           # capture not cleared
    need_eq(a, 7, SRC_TIMER, 0x064, "capture_kept")
    frame_rd(a, 8)
    need_eq(a, 8, SRC_TIMER, 0x065, "cg15_unchanged")
    ram_ld(a, RAM_PREVM, 9)
    need_eq(a, 9, 3, 0x066, "prev_untouched")
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 10))
    need_eq(a, 10, 1, 0x067, "one_entry")
    delay_loop(a, 3000, "quiet_esc")
    ram_ld(a, RAM_SEQ, 11)
    need_eq(a, 11, 1, 0x068, "still_one_capture")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers(main_extra=_no_async_return_extra())), \
        {"exit": 0}


def _ill_extra():
    """Bad escape encodings: 3 (cg15 +4) and 4 ([17:2] SBZ nonzero)."""
    return [escape(HART_HA, 3), escape(HART_HA, 4)]


@case("escape_ill",
      "escape imms18=3 and [17:2]!=0 => ILLI inside the handler; capture kept")
def _escape_ill():
    a = Asm()
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm(a, tag="ei")
    wait_ram(a, RAM_SEQ, 1, 0x071, "ei")
    ram_ld(a, RAM_ILLI_N, 5)
    need_eq(a, 5, 2, 0x072, "illi_twice")
    ram_ld(a, RAM_CFXESC_N, 6)
    need_eq(a, 6, 0, 0x073, "no_cfxesc")
    ram_ld(a, RAM_FRAME, 7)
    need_eq(a, 7, SRC_TIMER, 0x074, "capture_kept")
    frame_rd(a, 8)
    need_eq(a, 8, SRC_TIMER, 0x075, "cg15_unchanged")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers(main_extra=_ill_extra())), {"exit": 0}


@case("ro_bitmaps",
      "cg15 rc4/rc4 ignore software writes, before and after a capture")
def _ro_bitmaps():
    a = Asm()
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, 15, RC_FRAME, 22))
    a.emit(cfx2rc(HART_HA, 15, RC_PENDING, 22))
    frame_rd(a, 5)
    need_eq(a, 5, 0, 0x081, "ro_frame_pre")
    pending_rd(a, 6)
    need_eq(a, 6, 0, 0x082, "ro_pending_pre")
    set_mon_mask(a, HMON_HA, ALL1 & ~SRC_TIMER)
    timer_arm(a, tag="ro")
    wait_ram(a, RAM_SEQ, 1, 0x083, "ro")
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, 15, RC_FRAME, 22))
    a.emit(cfx2rc(HART_HA, 15, RC_PENDING, 22))
    frame_rd(a, 7)
    need_eq(a, 7, SRC_TIMER, 0x084, "ro_frame_post")
    pending_rd(a, 8)
    need_eq(a, 8, 0, 0x085, "ro_pending_post")
    a.emit(*exit_seq(0))
    return build_rom(a.resolve(), handlers()), {"exit": 0}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_case(name):
    for n, d, fn in CASES:
        if n != name:
            continue
        rom, exp = fn()
        rc, _log = _prelude.run(rom, WORKDIR, qemu=QEMU, timeout=TIMEOUT,
                                dump=False)
        if rc is None:
            return False, "TIMEOUT"
        ok = (rc == exp["exit"])
        return ok, "rc=0x%02x (exp=0x%02x)" % (rc, exp["exit"])
    raise KeyError(name)


def main():
    global QEMU
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--qemu", default=None)
    args = ap.parse_args()
    if args.qemu:
        QEMU = args.qemu

    if args.list:
        for n, d, _fn in CASES:
            print("%-26s %s" % (n, d))
        return 0

    if not os.path.isfile(QEMU):
        print("[FAIL] QEMU binary not found: %s" % QEMU)
        return 2

    names = [n for n, _d, _fn in CASES]
    if args.only is not None:
        if args.only not in names:
            print("[FAIL] no case named %r" % args.only)
            return 1
        names = [args.only]

    all_ok = True
    for n in names:
        ok, why = run_case(n)
        print("[%s] %-26s %s" % ("PASS" if ok else "FAIL", n, why))
        if not ok:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
