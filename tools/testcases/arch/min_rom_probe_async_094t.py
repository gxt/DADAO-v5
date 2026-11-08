#!/usr/bin/env python3
"""TESTCASES-094t §2: minimal two-cfx asynchronous-delivery probe.

Purpose (ownership decision, not a replacement for INTEG-050t/051t): decide
whether a failure to deliver TIMER (target cfx_hart, cfxha 15) / PMEM_DMA
(target cfx_pmem, cfxha 32) is a *test-asset* or a *QEMU* defect.  The probe
contains no SBI provider, no mask bookkeeping beyond the minimum needed to
observe one event, and no INTEG-050t/051t harness code.

Expectations are derived by hand from:
  - spec/DADAO-12 §5.2 (exception entry step 3: the two-level cfx_intr_mask +
    global_cfx_intr_mask source filter; a masked async source keeps `pending`
    and is delivered on a later kick);
  - spec/DADAO-12 §4.7 (cfx_hart TIMER 1<<10, cause_info 0), §4.9
    (cfx_pmem PMEM_DMA 1<<8, cause_info = dma_status);
  - .tao/contracts/contract-see.md «统一异步中断仲裁（测试机约定）»
    (pending in the target cfx cg5 rc5, lowest target cfxha first, one source
    per arbitration, mask release re-delivers);
  - ADR-0045 D3, ADR-0043 (Vast monitor layout).
Not from the QEMU implementation.

The discriminating case pair is `timer_mask_open` vs `timer_mask_shut`: the
shut case sets bit 15 of the current cfx's `cfx_intr_mask` before arming, so
step 3 keeps blocking (`pending` is recorded, nothing is delivered); with the
bit clear the same body gets the delivery.

Observation: every check is in-program; the verdict is the host `$?` of the
semihosting SYS_EXIT (0 = pass).  All cases use the default virtual clock and
no CPU dump; the settle loops are sized so a 1-2 us timer deadline expires in
both the QEMU host-driven clock and the gem5 instruction clock.

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

HART_HA, PMEM_HA, HMON_HA, POWER_HA = 15, 32, 3, 63
HART_CG, PMEM_DMA_CG = 8, 15
TIMER = 1 << 10
PMEM_DMA = 1 << 8
CTRL_ENABLE = 1 << 0
CTRL_START = 1 << 0
CTRL_IRQ_EN = 1 << 2
ST_BUSY = 1 << 0
ST_DONE = 1 << 1
ALL1 = (1 << 64) - 1

# Body-relative slots (the body is tiny; handlers sit past every body).
OFF_HART_HND = 0x2000
OFF_PMEM_HND = 0x2100
OFF_POISON = 0x2200

# RAM state block; rb5 = RAM_BASE, and the 12-bit store offset wraps
# consistently on both sides (handler and checker use the same constant).
# RAM state block; rb5 = RAM_BASE.  Every slot must stay below 0x800: the
# ld/st imm12 field is sign-extended (0x800 == -2048 would address
# 0xffff_ffff_ffff_f800, i.e. cfx_power's BootROM window).
RAM_SEQ = 0x020          # total deliveries
RAM_SEQ15 = 0x028        # delivery ordinal of the TIMER handler
RAM_SEQ17 = 0x030        # delivery ordinal of the PMEM_DMA handler
RAM_CID15 = 0x038
RAM_CID17 = 0x040
RAM_INFO17 = 0x048

DATA_PA = RAM_BASE + 0x4000
PMEM_SRC = _prelude.PMEM_BASE          # cfx_pmem SRAM window

# cfx_hmon hypv row: both interrupt-filter levels open bits 15/32
# (DADAO-12 §5.2 step 3).
CROSS = ALL1 & ~((1 << 3) | (1 << 15) | (1 << 32))


# ---------------------------------------------------------------------------
# Minimal encoders (prelude set + the few this probe needs)
# ---------------------------------------------------------------------------

ld_o = _prelude.ld_o
add_si = _prelude.add_si
escape = _prelude.escape
load_rd = _prelude.load_rd
load_rb = _prelude.load_rb
cfx2rd = _prelude.cfx2rd
cfx2rc = _prelude.cfx2rc
and_o = _prelude.and_o
exit_seq = _prelude.exit_seq
Seq = _prelude.Seq


def need_eq(s, rd, want, code, tag):
    ok = "%s_%d" % (tag, len(s.w))
    s.e(*load_rd(24, want))
    s.b("eq", rd, ok, 24)
    s.e(*exit_seq(code))
    s.mark(ok)


def need_mask_set(s, rd, mask, code, tag):
    ok = "%s_%d" % (tag, len(s.w))
    s.e(*load_rd(24, mask))
    s.e(and_o(23, rd, 24))
    s.b("nz", 23, ok)
    s.e(*exit_seq(code))
    s.mark(ok)


def ram_ld(s, off, rd):
    s.e(ld_o(rd, 5, off))


def set_global(s, mask, rd=22):
    s.e(*load_rd(rd, mask))
    s.e(cfx2rc(HMON_HA, 8, 1, rd))


def timer_arm(s, delta, ctrl=CTRL_ENABLE, rd=22):
    s.e(cfx2rd(HART_HA, HART_CG, 2, rd))       # cycle == cfx_time value
    s.e(add_si(rd, delta))
    s.e(cfx2rc(HART_HA, HART_CG, 4, rd))       # timer_cmp
    s.e(*load_rd(rd, ctrl))
    s.e(cfx2rc(HART_HA, HART_CG, 5, rd))       # timer_ctrl


def dma_status_clear(s):
    s.e(*load_rd(22, ST_DONE | ST_BUSY))
    s.e(cfx2rc(PMEM_HA, PMEM_DMA_CG, 4, 22))


def dma_start(s):
    for rc, val in ((0, PMEM_SRC), (1, DATA_PA), (2, 8),
                    (3, CTRL_START | CTRL_IRQ_EN)):
        s.e(*load_rd(22, val))
        s.e(cfx2rc(PMEM_HA, PMEM_DMA_CG, rc, 22))


def dma_wait(s, rd=6):
    lab = "dw_%d" % len(s.w)
    s.mark(lab)
    s.e(cfx2rd(PMEM_HA, PMEM_DMA_CG, 4, rd))
    s.e(*load_rd(18, ST_BUSY))
    s.e(and_o(rd, rd, 18))
    s.b("nz", rd, lab)


def delay_loop(s, count, tag, rd=23):
    head = "dl_%s_%d" % (tag, len(s.w))
    tail = head + "_end"
    s.e(*load_rd(rd, count))
    s.mark(head)
    s.b("z", rd, tail)
    s.e(add_si(rd, -1))
    s.b("nz", rd, head)
    s.mark(tail)


# ---------------------------------------------------------------------------
# Handlers: branchless record of the delivery ordinal / cause frame
# ---------------------------------------------------------------------------

def handler(ha, seq_slot, cid_slot, info_slot=None):
    s = Seq()
    s.e(ld_o(20, 5, RAM_SEQ))
    s.e(add_si(20, 1))
    s.e(_prelude.st_o(20, 5, RAM_SEQ))
    s.e(_prelude.st_o(20, 5, seq_slot))
    s.e(cfx2rd(ha, 5, 2, 21))                  # cause_id
    s.e(_prelude.st_o(21, 5, cid_slot))
    if info_slot is not None:
        s.e(cfx2rd(ha, 5, 4, 21))              # cause_info
        s.e(_prelude.st_o(21, 5, info_slot))
    s.e(escape(ha, 0))
    return s.resolve()


def poison():
    s = Seq()
    s.e(*exit_seq(0x7E))                       # monitor hop == failure
    return s.resolve()


HANDLERS = {
    OFF_HART_HND: handler(HART_HA, RAM_SEQ15, RAM_CID15),
    OFF_PMEM_HND: handler(PMEM_HA, RAM_SEQ17, RAM_CID17, RAM_INFO17),
    OFF_POISON: poison(),
}


# ---------------------------------------------------------------------------
# Setup: power (entry mask) + hmon (filter masks, vectors, fetch/RAM access)
# ---------------------------------------------------------------------------

def hmon_setup():
    s = Seq()
    s.e(*load_rb(5, RAM_BASE))
    # step 4 upper level: cfx_hmon hypv cfx_intr_mask and global mask
    s.e(*load_rd(21, CROSS))
    s.e(cfx2rc(HMON_HA, 3, 4, 21))
    s.e(cfx2rc(HMON_HA, 8, 1, 21))
    # target cfx vectors
    s.e(*load_rd(21, ROM_BASE + OFF_PMEM_HND))
    s.e(cfx2rc(PMEM_HA, 3, 10, 21))
    s.e(*load_rd(21, ROM_BASE + OFF_HART_HND))
    s.e(cfx2rc(HART_HA, 3, 10, 21))
    # cross-cfx register reads after a trap + ROM fetch / RAM store; the
    # lower filter level uses the *current* cfx's cfx_intr_mask, and
    # inner_cfx_code stays at the last delivered/trapped cfx, so both target
    # cfx rows must allow the two sources.
    s.e(*load_rd(21, CROSS))
    for rc in (0, 1, 2, 3):
        s.e(cfx2rc(HART_HA, 3, rc, 21))
    for rc in (0, 1, 2, 3):
        s.e(cfx2rc(PMEM_HA, 3, rc, 21))
    s.e(*load_rd(21, CROSS))
    s.e(cfx2rc(HART_HA, 3, 4, 21))
    s.e(cfx2rc(PMEM_HA, 3, 4, 21))
    s.e(*load_rd(20, 0))
    for cg in (0, 1, 2, 3):
        s.e(cfx2rc(POWER_HA, cg, 1, 20), cfx2rc(POWER_HA, cg, 3, 20))
    # any monitor hop is a bug: poison vector
    s.e(*load_rd(21, ROM_BASE + OFF_POISON))
    s.e(cfx2rc(HMON_HA, 3, 10, 21))
    # clean pending
    s.e(cfx2rc(PMEM_HA, 5, 5, 20))
    s.e(cfx2rc(HART_HA, 5, 5, 20))
    return s.resolve()


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def build(body):
    return _prelude.build_rom(body, HANDLERS, hmon_extra=hmon_setup())


@case("timer_mask_open", "entry mask open => TIMER delivered once")
def _timer_mask_open():
    s = Seq()
    timer_arm(s, 2000)
    delay_loop(s, 4000, "t")
    ram_ld(s, RAM_SEQ, 5)
    need_eq(s, 5, 1, 0x61, "seq")
    ram_ld(s, RAM_CID15, 6)
    need_eq(s, 6, TIMER, 0x62, "cid")
    s.e(*exit_seq(0))
    return build(s.resolve()), {"exit": 0}


@case("timer_mask_open_default",
      "default clock: entry mask open => TIMER delivered once")
def _timer_mask_open_default():
    s = Seq()
    timer_arm(s, 2000)
    delay_loop(s, 20000, "td")
    ram_ld(s, RAM_SEQ, 5)
    need_eq(s, 5, 1, 0x63, "seq")
    s.e(*exit_seq(0))
    return build(s.resolve()), {"exit": 0}


@case("timer_mask_shut",
      "cfx_intr_mask bit15 set => pending bit10 set, no delivery")
def _timer_mask_shut():
    s = Seq()
    # current cfx is hmon; block the TIMER source at the lower filter level
    s.e(*load_rd(21, ALL1))
    s.e(cfx2rc(HMON_HA, 3, 4, 21))             # cfx_hmon hypv cfx_intr_mask
    timer_arm(s, 2000)
    delay_loop(s, 4000, "ts")
    ram_ld(s, RAM_SEQ, 5)
    need_eq(s, 5, 0, 0x64, "no_delivery")
    s.e(cfx2rd(HART_HA, 5, 5, 6))
    need_mask_set(s, 6, TIMER, 0x65, "pending")
    s.e(*exit_seq(0))
    return build(s.resolve()), {"exit": 0}


@case("pmem_mask_open", "default clock: entry mask open => PMEM_DMA delivered once")
def _pmem_mask_open():
    s = Seq()
    dma_status_clear(s)
    dma_start(s)
    dma_wait(s)
    delay_loop(s, 20000, "pd")
    ram_ld(s, RAM_SEQ, 5)
    need_eq(s, 5, 1, 0x66, "seq")
    ram_ld(s, RAM_CID17, 6)
    need_eq(s, 6, PMEM_DMA, 0x67, "cid")
    ram_ld(s, RAM_INFO17, 7)
    need_eq(s, 7, ST_DONE, 0x68, "info")
    s.e(*exit_seq(0))
    return build(s.resolve()), {"exit": 0}


@case("dual_lowest_first",
      "default clock: both masked pending, release => cfxha 15 then 32")
def _dual_lowest_first():
    s = Seq()
    set_global(s, ALL1)                        # block both levels of delivery
    dma_status_clear(s)
    timer_arm(s, 1000)
    dma_start(s)
    dma_wait(s)
    delay_loop(s, 20000, "dd")                 # let the timer expire as well
    s.e(cfx2rd(HART_HA, 5, 5, 6))
    need_mask_set(s, 6, TIMER, 0x69, "timer_pending")
    s.e(cfx2rd(PMEM_HA, 5, 5, 7))
    need_mask_set(s, 7, PMEM_DMA, 0x6A, "pmem_pending")
    set_global(s, 0)                           # release: re-kick both
    delay_loop(s, 20000, "dr")
    ram_ld(s, RAM_SEQ, 5)
    need_eq(s, 5, 2, 0x6B, "two")
    ram_ld(s, RAM_SEQ15, 6)
    need_eq(s, 6, 1, 0x6C, "timer_first")
    ram_ld(s, RAM_SEQ17, 7)
    need_eq(s, 7, 2, 0x6D, "pmem_second")
    s.e(*exit_seq(0))
    return build(s.resolve()), {"exit": 0}


@case("dedup_timer",
      "two masked expiries of one source => exactly one delivery")
def _dedup_timer():
    s = Seq()
    set_global(s, ALL1)                        # block TIMER (bit15 set)
    timer_arm(s, 500)
    delay_loop(s, 1000, "d1")
    timer_arm(s, 500)
    delay_loop(s, 1000, "d2")
    s.e(cfx2rd(HART_HA, 5, 5, 6))
    need_mask_set(s, 6, TIMER, 0x6E, "pending")
    set_global(s, 0)
    delay_loop(s, 400, "d3")
    ram_ld(s, RAM_SEQ, 5)
    need_eq(s, 5, 1, 0x6F, "one")
    s.e(*exit_seq(0))
    return build(s.resolve()), {"exit": 0}


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
