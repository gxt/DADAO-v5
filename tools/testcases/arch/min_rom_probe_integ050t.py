#!/usr/bin/env python3
"""Min ROM probe for INTEG-050t: cfx_time (cfxha 34) + single-hart cfx_hart
timer (cfxha 15), including the 64-bit cycle/insn test-machine counters.

Two kinds of checks:

  * ``doc`` (pure Python, no QEMU): parse ``spec/DADAO-12`` §4.7/§4.10,
    ``spec/DADAO-22`` §7/§10 and ``.tao/contracts/contract-see.md`` §3 and
    assert the post-INTEG-050t rc layout / 64-bit wording / FID names.
  * ``runtime`` (min-ROM, QEMU): the probe embeds **test-only** SBI providers
    for cfx_time (FID 0 = SBI_TIME_GET) and cfx_hart (FID 0 = SBI_HART_GET_ID,
    FID 1 = SBI_HART_SET_TIMER).  This is NOT a production provider: the repo
    has no firmware host for these cfx yet (same convention as
    min_rom_probe_integ047t.py).

Asynchronous model (ADR-0061 R2, spec/DADAO-12 §4.7/§5.4): TIMER is a source
identified by its cfxha (bit 15), not by an ``excp_cause_id``.  It is delivered
to ``cfx_hart``'s supv single vector (``cg15 rc15``/``rc6``) as an entry capture:
``cg15 rc4`` = captured sources, ``rc4`` = still-pending sources (both HW/RO),
``rc0``–``rc2`` = pre-entry mode/cfx/cause_ip.  The source mask is the running
mode monitor's ``cg15 rc3`` (bit 15, 1 = masked), and the source's own
``timer_ctrl`` IMASK only defers (``cg15 rc5`` bit 15 set, no entry).  ``cg15`` is
a capture buffer, not a return frame: every entry overwrites it and the
software carries the capture out and returns through ``cfx_smon`` (the probe
models that hand-off).

Expectations are derived by hand from the frozen spec / contract:
  - spec/DADAO-12 §4.7 (cfx_hart: cg8 rc0 hart_id, rc2 cycle 64-bit, rc3 insn
    64-bit, rc4 timer_cmp, rc5 timer_ctrl ENABLE/IMASK/ISTATUS, rc6/rc7
    reserved; cg15 capture buffer; TIMER delivered hart-first), §4.10 (cfx_time:
    cg10 rc0 time_freq, rc1 time_value 64-bit, rc2-rc63 reserved), §5.4.
  - spec/DADAO-22 §7 / §10 (SBI_HART_GET_ID / SBI_HART_SET_TIMER /
    SBI_TIME_GET; 64-bit timeout/value).
  - .tao/contracts/contract-see.md §3 (test-machine projection: 1 GHz,
    1 count = 1 ns, cycle = virtual clock, insn = per-instruction count).
  Never from the QEMU implementation.

Observation channels (same convention as min_rom_probe_integ047t.py):
  * register / fault-frame results -> QEMU `-d cpu` dump (last dump block);
  * timer / counter cases -> in-program self-checks with a semihosting
    SYS_EXIT exit code (no `-d cpu` dump).

Timing model (TESTCASES-102t): the probe uses no instruction clock.  A wait
reads the current `cfx_time`, sets a relative deadline, and polls it with a
bounded loop.  Assertions are architecture-visible properties: nothing fires
before the deadline, the event is visible inside a bounded window, ISTATUS /
pending semantics, one-shot vs re-trigger, monotonicity, and the `cmp = ~0`
disable.  The window is deliberately wide (see `DELTA_NS` / `WINDOW_NS`): with
the default virtual clock QEMU drives `cfx_time` from host time, so a timer
delivery can slip by the host scheduling latency (measured 0.5-7 ms on a
loaded host), which no instruction-count bound can cover while still being
comparable on gem5.

Bootstrap (the probe body runs in hmon / cfx3, hypv):
  1. power stage: set cfx_hmon hypv_excp_vector, then `trap cfx_hmon, 0`.
  2. hmon stage: install the cfx_hart / cfx_time sync vectors and the
     cfx_hart cg15 async vector + cfx_smon hand-off vector, open the supv
     delegation for cfx_hart cg15 / cfx_smon cg5, and clear cfx_power's
     cfxmem/cfxexe source masks for all four modes (so the ROM handler stays
     fetchable / RAM readable while inner_cfx_code = 15/34).  The async source
     masks (`cfx_hmon cg15 rc3`, used while the body runs in hypv) stay at
     their all-1 reset; each timer case opens bit 15 explicitly.

Usage:
  min_rom_probe_integ050t.py --doc          # doc checks only (offline)
  min_rom_probe_integ050t.py                # doc + runtime
  min_rom_probe_integ050t.py --only NAME    # one check (run.sh --inject)
  min_rom_probe_integ050t.py --list
  min_rom_probe_integ050t.py --qemu PATH

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import re
import struct
import sys

import os, sys

# TESTCASES-091t: probe geometry from the single profile source
# (contracts/machine.yaml + contracts/exec-envs.yaml); runtime execution stays BLOCKED until
# QEMU-079/080 provide the Tiny/Vast machines.
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
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_integ050t")
TIMEOUT = 90

SPEC_SEE = os.path.join(_REPO, "spec", "DADAO-12-SEE-主管系统运行环境.md")
SPEC_SBI = os.path.join(_REPO, "spec", "DADAO-22-SBI-主管系统二进制接口.md")
CONTRACT_SEE = os.path.join(_REPO, ".tao", "contracts", "contract-see.md")

# TESTCASES-094t §1: the body runs at RESET_PC + 0x1000 inside the 4 MiB
# bootrom-image, after the shared power -> hmon identity-PTW prelude.
ROM_BASE = _prelude.ROM_BASE
RAM_BASE = _MACH.ram_base

HART_HA = 15
TIME_HA = 34
CACHE_HA = 5
SMON_HA = 2
HMON_HA = 3
HART_CG = 8
HART_TIMER_CG = 16
TIME_CG = 10
MON_CG, MON_MASK_RC = 15, 3
CG5_CAUSE_ID_RC, CG5_CAUSE_IP_RC, CG5_CAUSE_INFO_RC = 2, 3, 4
CG3_EXCP_VECTOR_RC = 15
CG3_DELEG_RC = 12
CG4_ASYNC_NUM_RC = 4
# cfx_hart cg15 (ADR-0061 D7): capture buffer slots.
RC_PREV_MODE, RC_PREV_CFX, RC_CAUSE_IP = 0, 1, 2
RC_FRAME, RC_PENDING, RC_VECTOR, RC_SWITCH = 4, 5, 15, 14

CFXTRAP = 1 << 0
CFXREG = 1 << 2
CFXESC = 1 << 3
SRC_TIMER = 1 << HART_HA          # source identity = source cfxha (bit 15)
DELEG_OPEN = 0xFFFFFFFFFFFE7FC7
CTRL_ENABLE = 1 << 0
CTRL_IMASK = 1 << 1
CTRL_ISTATUS = 1 << 2

TIME_FREQ = 1_000_000_000
ALL1 = (1 << 64) - 1
BIT63 = 1 << 63

EXIT_PASS = 0x00
EXIT_FAIL = 0x61   # guest FAIL segment (spec/Kaiwu §7.1)

# Timing-model-neutral bounds (TESTCASES-102t).  DELTA_NS is the nominal
# relative deadline; WINDOW_NS is the tolerated delay between the deadline and
# the architecture-visible event.  Basis: without an instruction clock QEMU's
# QEMU_CLOCK_VIRTUAL is host-time driven, so the observed delivery slip was
# 0.5-7 ms on this (loaded) host; the 10 ms nominal deadline leaves >10x that
# slip available *before* the deadline, and the 1 s window (100x nominal)
# still fails an event that never arrives (the bounded poll records zero).
DELTA_NS = 10_000_000
WINDOW_NS = 1_000_000_000
# Bounded poll: one iteration is ~7 instructions, so reaching the 10 ms
# deadline needs ~1.4M iterations on gem5 (1 ns/instruction); 4M gives >2x
# margin (on QEMU that is ~300 ms of head room).  The bound is only the
# lost-event safety net: a passing case exits at the deadline.
MAX_WAIT = 4_000_000

# Wait-loop scratch registers.  The cfx_hart timer handler uses rd20/rd21, so
# the body keeps its timing state in rd22..rd28.
W_NOW, W_CMP, W_DEAD, W_BOUND, W_MAX, W_WIT, W_TMP = range(22, 29)

# ROM layout: the shared prelude owns the power -> hmon hand-off; this probe's
# hmon-mode setup (masks, vectors) is appended to the prelude's hmon segment,
# and the body starts at ROM_BASE (RESET_PC + 0x1000).
OFF_FH3 = 0x700       # CFXREG handler for faults raised at the hmon monitor
OFF_FH15 = 0x740      # CFXREG handler for faults raised at cfx_hart
OFF_FH34 = 0x780      # CFXREG handler for faults raised at cfx_time
OFF_HART_PROVIDER = 0x800
OFF_TIME_PROVIDER = 0x880
OFF_ASYNC_HND = 0x900      # cfx_hart cg15 capture recorder
OFF_SMON_HND = 0x980      # cfx_smon supv vector: capture hand-off
OFF_HART_SYNC_HND = 0xA00  # cfx_hart supv vector: escape frame-error recorder
OFF_POISON = 0xA80        # cfx_hmon hypv vector: any monitor hop is a failure

RAM_STATE = 0x3000    # handler-recorded cause frame / counter
# Async capture block (handler copy; ld/st imm12 keeps them below RAM_STATE+0x800).
RAM_ASYNC_SEQ = RAM_STATE + 0x20     # async entries
RAM_ASYNC_FRAME = RAM_STATE + 0x28   # cg15 rc4 at entry
RAM_ASYNC_PENDING = RAM_STATE + 0x30 # cg15 rc5 at entry
RAM_ASYNC_IP = RAM_STATE + 0x38      # cg15 rc2 at entry
RAM_ASYNC_PREVM = RAM_STATE + 0x40   # cg15 rc0 at entry
RAM_ASYNC_PREVC = RAM_STATE + 0x48   # cg15 rc1 at entry
RAM_HANDOFF = RAM_STATE + 0x50       # 1 while the handler hands off to smon

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
    return _orrr(0x40, 0x2A, rdhb, rdhc, rdhd)


def add_uo(lo, hi, src_a, src_b):
    """add.uo {hi, lo}, src_a, src_b: 128-bit unsigned add (carry -> hi).

    Used only to build `deadline + WINDOW`; the two destinations must differ
    (SimRISC-04 §1.1 legality), and `hi` is discarded.
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
# Test-only SBI providers + fault handlers (ROM slots).
# ---------------------------------------------------------------------------

def build_fault_handler(ha):
    """Record the sync CFXREG frame and resume after the faulting insn."""
    a = Asm()
    a.emit(cfx2rd(ha, 5, CG5_CAUSE_ID_RC, 10))
    a.emit(cfx2rd(ha, 5, CG5_CAUSE_IP_RC, 11))
    a.emit(add_si(12, 1))
    a.emit(escape(ha, 1))
    return a.resolve()


def build_hart_provider():
    """cfx_hart's hypv sync vector: SBI provider (`trap cfx_hart`).

    Asynchronous TIMER no longer arrives here: under ADR-0061 R2 every async
    source enters through cfx_hart cg15 rc15 (`OFF_ASYNC_HND`), so this vector
    only serves the test-only SBI calls and (unexpectedly) other sync causes.
    """
    a = Asm()
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_ID_RC, 20))
    a.emit(*load_rd(21, CFXTRAP))
    a.br("eq", 20, 21, "hart_sbi")
    a.emit(escape(HART_HA, 1))
    # --- SBI dispatch (trap cfx_hart, func = immu18) ---
    a.mark("hart_sbi")
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_INFO_RC, 20))
    a.emit(*load_rd(21, 0x3FFFF))
    a.emit(and_o(20, 20, 21))
    a.br("ne", 20, 0, "hart_sbi_not_id")
    # FID 0: SBI_HART_GET_ID -> rd8
    a.emit(*load_rd(8, 0))
    a.emit(escape(HART_HA, 1))
    a.mark("hart_sbi_not_id")
    a.emit(*load_rd(21, 1))
    a.br("ne", 20, 21, "hart_sbi_unknown")
    # FID 1: SBI_HART_SET_TIMER(rd16 = 64-bit absolute timeout)
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, 16))
    a.emit(*load_rd(17, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, 17))
    a.emit(*load_rd(8, 0))
    a.emit(escape(HART_HA, 1))
    a.mark("hart_sbi_unknown")
    a.emit(escape(HART_HA, 1))
    return a.resolve()


def build_async_handler():
    """cfx_hart cg15 rc15 (supv): copy the entry capture to RAM, hand off.

    The capture is read first (any later entry overwrites it), stored in the
    probe's RAM block, and then handed to cfx_smon exactly as ADR-0061 D4
    prescribes ("关中断窗口把 cg15 搬到本任务现场，再进入 cfx_smon").  A correct
    hand-off never returns here: the smon frame returns to the capture's
    `cause_ip`.
    """
    a = Asm()
    a.emit(cfx2rd(HART_HA, 15, RC_FRAME, 30))
    a.emit(cfx2rd(HART_HA, 15, RC_PENDING, 31))
    a.emit(cfx2rd(HART_HA, 15, RC_CAUSE_IP, 32))
    a.emit(cfx2rd(HART_HA, 15, RC_PREV_MODE, 33))
    a.emit(cfx2rd(HART_HA, 15, RC_PREV_CFX, 34))
    a.emit(ld_o(36, 5, RAM_ASYNC_SEQ))
    a.emit(add_si(36, 1))
    a.emit(st_o(36, 5, RAM_ASYNC_SEQ))
    a.emit(st_o(30, 5, RAM_ASYNC_FRAME))
    a.emit(st_o(31, 5, RAM_ASYNC_PENDING))
    a.emit(st_o(32, 5, RAM_ASYNC_IP))
    a.emit(st_o(33, 5, RAM_ASYNC_PREVM))
    a.emit(st_o(34, 5, RAM_ASYNC_PREVC))
    a.emit(*load_rd(36, 1))
    a.emit(st_o(36, 5, RAM_HANDOFF))
    a.emit(trap(SMON_HA, 0))            # cfx_smon supv vector = hand-off
    a.emit(*exit_seq(0x6F))             # unreachable on a correct return
    return a.resolve()


def build_smon_handler():
    """cfx_smon supv vector: rebuild the sync frame from the capture and
    `escape` to its cause_ip (software-side return through smon)."""
    a = Asm()
    a.emit(ld_o(30, 5, RAM_HANDOFF))
    sync_path = "smon_sync_%d" % len(a.words)
    a.br("z", 30, 0, sync_path)
    a.emit(ld_o(30, 5, RAM_ASYNC_PREVM))
    a.emit(cfx2rc(SMON_HA, 5, 0, 30))
    a.emit(ld_o(30, 5, RAM_ASYNC_PREVC))
    a.emit(cfx2rc(SMON_HA, 5, 1, 30))
    a.emit(ld_o(30, 5, RAM_ASYNC_IP))
    a.emit(cfx2rc(SMON_HA, 5, 3, 30))
    a.emit(*load_rd(30, 0))
    a.emit(st_o(30, 5, RAM_HANDOFF))
    a.emit(escape(SMON_HA, 0))          # cg5 frame, offset 0: capture's cause_ip
    a.emit(*exit_seq(0x7F))             # unreachable: escape switches away

    a.mark(sync_path)
    # Unexpected sync exception in supv: record the cause and skip the word.
    a.emit(cfx2rd(SMON_HA, 5, CG5_CAUSE_ID_RC, 30))
    a.emit(st_o(30, 5, RAM_STATE + 0x00))
    a.emit(escape(SMON_HA, 1))
    return a.resolve()


def build_hart_sync_handler():
    """cfx_hart's own supv vector: an `escape` frame error raises CFXESC in
    the current cfx (§5.1).  Record it and skip the word."""
    a = Asm()
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_ID_RC, 30))
    a.emit(*load_rd(31, CFXESC))
    cfxesc = "h_cfxesc_%d" % len(a.words)
    other = "h_other_%d" % len(a.words)
    a.br("eq", 30, 31, cfxesc)
    a.emit(escape(HART_HA, 1))
    a.br("z", 0, 0, other)
    a.mark(cfxesc)
    a.emit(*load_rd(31, 1))
    a.emit(st_o(31, 5, RAM_STATE + 0x58))   # CFXESC seen (unexpected)
    a.mark(other)
    a.emit(escape(HART_HA, 1))
    return a.resolve()


def build_poison():
    """cfx_hmon hypv vector: any monitor hop is a failure (never reached)."""
    a = Asm()
    a.emit(*exit_seq(0x7E))
    return a.resolve()


def build_time_provider():
    a = Asm()
    a.emit(cfx2rd(TIME_HA, 5, CG5_CAUSE_ID_RC, 20))
    a.emit(*load_rd(21, CFXTRAP))
    a.br("ne", 20, 21, "time_bad")
    a.emit(cfx2rd(TIME_HA, 5, CG5_CAUSE_INFO_RC, 20))
    a.emit(*load_rd(21, 0x3FFFF))
    a.emit(and_o(20, 20, 21))
    a.br("ne", 20, 0, "time_bad")
    # FID 0: SBI_TIME_GET -> rd8 = cfx_time_value (64-bit)
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 8))
    a.mark("time_bad")
    a.emit(escape(TIME_HA, 1))
    return a.resolve()


HANDLERS = {
    OFF_FH3: build_fault_handler(3),
    OFF_FH15: build_fault_handler(HART_HA),
    OFF_FH34: build_fault_handler(TIME_HA),
    OFF_HART_PROVIDER: build_hart_provider(),
    OFF_TIME_PROVIDER: build_time_provider(),
    OFF_ASYNC_HND: build_async_handler(),
    OFF_SMON_HND: build_smon_handler(),
    OFF_HART_SYNC_HND: build_hart_sync_handler(),
    OFF_POISON: build_poison(),
}


# ---------------------------------------------------------------------------
# Program-building helpers (body runs in hmon / cfx3, hypv mode).
# ---------------------------------------------------------------------------

def hmon_addr(off):
    """Body-relative address inside the shared prelude's body image."""
    return ROM_BASE + off


def set_vector(a, ha, off):
    a.emit(*load_rd(21, hmon_addr(off)))
    a.emit(cfx2rc(ha, 3, CG3_EXCP_VECTOR_RC, 21))


def ram_load(a, off, rd):
    a.emit(*load_rb(3, RAM_BASE))
    a.emit(ld_o(rd, 3, off))


def check_frame(a, expected_ip, ordinal, flag=14):
    """Assert cid == CFXREG and cip == expected_ip (record `ordinal` if not)."""
    cid_ok = "cid_ok_%d" % ordinal
    cip_ok = "cip_ok_%d" % ordinal
    a.emit(*load_rd(20, CFXREG))
    a.br("eq", 10, 20, cid_ok)
    a.emit(*load_rd(flag, ordinal))
    a.mark(cid_ok)
    a.emit(*load_rd(20, expected_ip))
    a.br("eq", 11, 20, cip_ok)
    a.emit(*load_rd(flag, ordinal))
    a.mark(cip_ok)


def finish(a, fail_flag=14, fail_code=EXIT_FAIL):
    ok = "finish_ok_%d" % len(a.words)
    a.emit(*load_rd(20, 0))
    a.br("eq", fail_flag, 20, ok)
    a.emit(*exit_seq(fail_code))
    a.mark(ok)
    a.emit(*exit_seq(EXIT_PASS))


def set_mon_mask(a, mask):
    """Write the running mode's async source mask (cfx_hmon cg15 rc3; 1=masked)."""
    a.emit(*load_rd(21, mask))
    a.emit(cfx2rc(HMON_HA, MON_CG, MON_MASK_RC, 21))


def delay_loop(a, rd, count, tag):
    a.emit(*load_rd(rd, count))
    a.mark("dl_%s" % tag)
    a.emit(add_si(rd, -1))
    a.br("nz", rd, 0, "dl_%s" % tag)


# ---------------------------------------------------------------------------
# Model-neutral timing helpers (TESTCASES-102t)
# ---------------------------------------------------------------------------

def _timer_count_cond(want, off=0x20):
    """Witness: cmp(RAM_STATE+off, want) -> 0 iff the count equals `want`."""

    def emit(a, rd):
        a.emit(*load_rb(3, RAM_BASE))
        a.emit(ld_o(rd, 3, RAM_STATE + off))
        a.emit(*load_rd(W_TMP, want))
        a.emit(cmp_uo(rd, rd, W_TMP))

    return emit


def _cfx_mask_cond(read_cfx, mask):
    """Witness: read_cfx(rd) & mask -> non-zero iff the bit is set."""

    def emit(a, rd):
        a.emit(read_cfx(rd))
        a.emit(*load_rd(W_TMP, mask))
        a.emit(and_o(rd, rd, W_TMP))

    return emit


def _pending_timer(rd):
    """cg15 rc5 (async_src_pending), bit 15 = the TIMER source cfxha."""
    return cfx2rd(HART_HA, 15, RC_PENDING, rd)


def _ctrl_istatus(rd):
    return cfx2rd(HART_HA, HART_TIMER_CG, 0, rd)


ARM_RETRIES = 8


def arm_timer(a, delta=DELTA_NS, ctrl=CTRL_ENABLE, base=0, tag="a"):
    """Cancel, then arm cmp = now + delta and program ctrl.

    `base` is the probe's delivery-counter baseline (the counter is probe
    bookkeeping in RAM, not hardware state).  The arm is retried if the host
    clock already passed the deadline by the time the write landed: without a
    deterministic instruction clock a host preemption between the time read
    and the cmp write would otherwise arm an already-expired timer and fire
    before the probe's "nothing before the deadline" check.  `cmp = ~0` plus
    `ctrl = 0` cancel a half-armed timer and drop the source's pending bit
    (DADAO-12 §4.7: writing timer_cmp acks the source).
    """
    retry = "arm_%s_reset" % tag
    done = "arm_%s_ok" % tag
    a.emit(*load_rd(W_MAX, ARM_RETRIES))
    a.mark(retry)
    a.emit(*load_rd(W_TMP, ALL1))                    # cmp = ~0: cancel
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, W_TMP))
    a.emit(*load_rd(W_TMP, 0))                       # ctrl = 0
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, W_TMP))
    a.emit(*load_rb(3, RAM_BASE))                    # witness baseline
    a.emit(*load_rd(W_TMP, base))
    a.emit(st_o(W_TMP, 3, RAM_ASYNC_SEQ))
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, W_NOW))
    a.emit(*load_rd(W_TMP, delta))                   # >= 10 ms: not imms18
    a.emit(add_uo(W_DEAD, W_CMP, W_NOW, W_TMP))      # W_DEAD = now + delta
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, W_DEAD))
    _set_bound(a, W_DEAD)
    a.emit(*load_rd(W_TMP, ctrl))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, W_TMP))
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, W_CMP))       # still in the future?
    a.emit(cmp_uo(W_CMP, W_CMP, W_DEAD))
    a.emit(*load_rd(W_TMP, 1))
    a.br("ne", W_CMP, W_TMP, done)                   # <= deadline -> armed
    a.emit(add_si(W_MAX, -1))
    a.br("nz", W_MAX, 0, retry)
    a.emit(*exit_seq(0x7A))                          # cannot arm in the future
    a.mark(done)


def arm_timer_sbi(a, delta=DELTA_NS, tag="sbi"):
    """arm_timer() through SBI_HART_SET_TIMER, with the same cancel+retry guard.

    The provider writes cmp/ctrl from rd16; the trap and the provider body sit
    between the time read and the cmp write, so a host preemption there could
    arm an already-expired timer.  Cancel (cmp = ~0) and retry, exactly as in
    arm_timer().
    """
    retry = "arms_%s_reset" % tag
    done = "arms_%s_ok" % tag
    a.emit(*load_rd(W_MAX, ARM_RETRIES))
    a.mark(retry)
    a.emit(*load_rd(W_TMP, ALL1))                    # cmp = ~0: cancel
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, W_TMP))
    a.emit(*load_rd(W_TMP, 0))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, W_TMP))
    a.emit(*load_rb(3, RAM_BASE))
    a.emit(st_o(W_TMP, 3, RAM_ASYNC_SEQ))         # baseline 0
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, W_NOW))
    a.emit(*load_rd(W_TMP, delta))                   # >= 10 ms: not imms18
    a.emit(add_uo(W_DEAD, W_CMP, W_NOW, W_TMP))      # W_DEAD = now + delta
    _set_bound(a, W_DEAD)
    a.emit(and_o(16, W_DEAD, W_DEAD))
    a.emit(trap(HART_HA, 1))
    a.emit(and_o(5, 8, 8))
    a.br("z", 5, 0, "arms_%s_ret" % tag)
    a.emit(*exit_seq(0x61))
    a.mark("arms_%s_ret" % tag)
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, W_CMP))
    a.emit(cmp_uo(W_CMP, W_CMP, W_DEAD))
    a.emit(*load_rd(W_TMP, 1))
    a.br("ne", W_CMP, W_TMP, done)
    a.emit(add_si(W_MAX, -1))
    a.br("nz", W_MAX, 0, retry)
    a.emit(*exit_seq(0x7A))
    a.mark(done)


def _set_bound(a, deadline_rd):
    """W_BOUND = deadline + WINDOW_NS (add.uo: lo=W_BOUND, hi=W_CMP)."""
    a.emit(*load_rd(W_TMP, WINDOW_NS))
    a.emit(add_uo(W_BOUND, W_CMP, deadline_rd, W_TMP))


def check_quiet(a, deadline_rd, cond, zero_is_met, code, tag):
    """Assert `cond` is NOT met while cfx_time < deadline.

    Sampling order matters: the witness is read *first*, then the clock.  If
    the clock sample is still before the deadline, the witness sample was
    taken even earlier, so a met condition is a genuine early delivery.  If
    the clock already passed the deadline the check is inconclusive (the
    guest cannot turn the host clock back) and is skipped; sampling the clock
    first would misjudge a preemption between the two reads as an early
    delivery.
    """
    done = "q_%s" % tag
    cond(a, W_WIT)
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, W_NOW))
    a.emit(cmp_uo(W_CMP, W_NOW, deadline_rd))
    a.br("nn", W_CMP, 0, done)
    a.br("nz" if zero_is_met else "z", W_WIT, 0, done)
    a.emit(*exit_seq(code))
    a.mark(done)


def wait_cond(a, bound_rd, cond, zero_is_met, tag, code_late, code_lost):
    """Bounded poll for `cond`, with a two-sided window.

    `bound_rd` is deadline + WINDOW_NS: an event seen after it is "late"
    (`code_late`), an event never seen before the bound or MAX_WAIT is "lost"
    (`code_lost`).  Both fail paths are reachable.
    """
    head = "w_%s" % tag
    got = head + "_got"
    lost = head + "_lost"
    ok = head + "_ok"
    a.emit(*load_rd(W_MAX, MAX_WAIT))
    a.mark(head)
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, W_NOW))
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


# ---------------------------------------------------------------------------
# QEMU runner + dump parsing
# ---------------------------------------------------------------------------

def run(rom, dump=True):
    """4 MiB `bootrom-image`, no `-kernel`; returns (rc, cpu_log, stderr)."""
    rc, log = _prelude.run(rom, WORKDIR, qemu=QEMU, timeout=TIMEOUT,
                           dump=dump)
    return rc, log, ""


def lasthex(log, pat):
    m = None
    for x in re.finditer(pat, log):
        m = x
    return int(m.group(1), 16) if m else None


def observe(log):
    o = {}
    for n in range(5, 15):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    return o


def build_rom(prog, handlers=None):
    """Shared prelude: body at RESET_PC + 0x1000; the hmon setup (masks and
    exception vectors for cfx_hart/cfx_time) runs inside the prelude's hmon
    segment, so `hmon_addr(off)` is body-relative (TESTCASES-094t §1)."""
    return _prelude.build_rom(prog, handlers, hmon_extra=hmon_setup())


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def hmon_setup():
    # TESTCASES-094t §1: the power->hmon hand-off and the power-mask clearing
    # live in the shared prelude; only the probe-specific mask/vector setup
    # stays here.  (This was the former power prefix + hmon stage.)
    # Source masks are cleared for bit15/bit34 in hmon, cfx_hart and cfx_time
    # (hypv row only): once a trap/escape has run, inner_cfx_code stays at the
    # trapped cfx in this model, so later cross-cfx reads must not be denied.
    MASK_HMON = 0x7FFF_FFFB_FFFF_7FF7
    # rb5 = RAM_BASE, used by the handlers for their state blocks.
    ins = load_rb(5, RAM_BASE)
    ins += load_rd(21, MASK_HMON)
    # hmon: hypv cfx{trap,mem,reg,exe} (no cgN rc4: ADR-0061 D5 deleted it).
    for rc in (0, 1, 2, 3):
        ins += [cfx2rc(3, 3, rc, 21)]
    # the async source mask is cfx_hmon cg15 rc3; leave it at the all-1 reset
    # (each timer case opens bit 15 explicitly).
    # cfx_hart: hypv cfx{trap,mem,reg,exe} (SBI trap + cross-cfx reads)
    for rc in (0, 1, 2, 3):
        ins += [cfx2rc(HART_HA, 3, rc, 21)]
    # cfx_time: hypv cfx{trap,mem,reg,exe} (cross-cfx reads after a trap)
    for rc in (0, 1, 2, 3):
        ins += [cfx2rc(TIME_HA, 3, rc, 21)]
    # install exception vectors for cfx_hart / cfx_time
    ins += load_rd(21, hmon_addr(OFF_HART_PROVIDER)) + [cfx2rc(HART_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    ins += load_rd(21, hmon_addr(OFF_TIME_PROVIDER)) + [cfx2rc(TIME_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    # clear cfx_power's cfxmem/cfxexe for all four modes (ROM fetch + RAM)
    ins += load_rd(20, 0)
    for cg in (0, 1, 2, 3):
        ins += [cfx2rc(63, cg, 1, 20), cfx2rc(63, cg, 3, 20)]
    # ---- async capture plumbing (ADR-0061 R2 / D4) ----
    # supv delegation for cfx_hart cg15 and cfx_smon cg5 (whole-group 0x8)
    ins += load_rd(21, DELEG_OPEN)
    ins += [cfx2rc(HART_HA, 3, CG3_DELEG_RC, 21),
            cfx2rc(SMON_HA, 3, CG3_DELEG_RC, 21)]
    # let supv `trap cfx_smon` through (cfx_smon supv cfxtrap bit 15 = 0)
    ins += load_rd(21, ALL1 & ~SRC_TIMER)
    ins += [cfx2rc(SMON_HA, 2, 0, 21)]
    # cfx_smon supv vector: hand-off (rebuild cg5 from the capture, escape)
    ins += load_rd(21, hmon_addr(OFF_SMON_HND))
    ins += [cfx2rc(SMON_HA, 2, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart's own supv vector: escape frame errors raise CFXESC here
    ins += load_rd(21, hmon_addr(OFF_HART_SYNC_HND))
    ins += [cfx2rc(HART_HA, 2, CG3_EXCP_VECTOR_RC, 21)]
    # cfx_hart cg15: supv async vector + fixed switch mode
    ins += load_rd(21, hmon_addr(OFF_ASYNC_HND))
    ins += [cfx2rc(HART_HA, 15, RC_VECTOR, 21)]
    ins += load_rd(21, 2)
    ins += [cfx2rc(HART_HA, 15, RC_SWITCH, 21)]
    # any monitor hop is a failure
    ins += load_rd(21, hmon_addr(OFF_POISON))
    ins += [cfx2rc(HMON_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    return ins


# ---------------------------------------------------------------------------
# Runtime cases
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc, dump=True):
    def deco(fn):
        CASES.append((name, desc, fn, dump))
        return fn
    return deco


@case("time_freq_value", "cfx_time cg10 rc0 = 1 GHz; rc1 monotonic non-decreasing")
def _time_freq_value():
    a = Asm()
    a.emit(cfx2rd(TIME_HA, TIME_CG, 0, 5))
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 6))
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 7))
    ok = "tf_ok"
    a.emit(cmp_uo(20, 7, 6))
    a.br("nn", 20, 0, ok)
    a.emit(*exit_seq(EXIT_FAIL))
    a.mark(ok)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve()), {
        "exit": EXIT_PASS, "rd5": TIME_FREQ,
        "rd6": lambda o: o["rd6"] is not None and 0 <= o["rd6"] < BIT63,
        "rd7": lambda o: o["rd7"] is not None and 0 <= o["rd7"] < BIT63,
    }


@case("time_ro_cfxreg", "cfx_time writes/rc2/rc63 are CFXREG with cid/cip")
def _time_ro_cfxreg():
    a = Asm()
    set_vector(a, 3, OFF_FH3)          # DADAO-12 §5.2: CFXREG -> current monitor (hmon)
    n = 0

    def fault(insn):
        nonlocal n
        n += 1
        idx = len(a.words)
        a.emit(insn)
        check_frame(a, hmon_addr(0) + idx * 4, n)

    fault(cfx2rc(TIME_HA, TIME_CG, 0, 5))
    fault(cfx2rc(TIME_HA, TIME_CG, 1, 5))
    fault(cfx2rd(TIME_HA, TIME_CG, 2, 5))
    last_idx = len(a.words)
    a.emit(cfx2rd(TIME_HA, TIME_CG, 63, 5))
    check_frame(a, hmon_addr(0) + last_idx * 4, 4)
    finish(a)
    return build_rom(a.resolve(), HANDLERS), {
        "exit": EXIT_PASS, "rd14": 0, "rd12": 4,
        "rd10": CFXREG, "rd11": hmon_addr(0) + last_idx * 4,
    }


@case("hart_id_zero", "cfx_hart cg8 rc0 = 0; SBI_HART_GET_ID = 0")
def _hart_id_zero():
    a = Asm()
    a.emit(cfx2rd(HART_HA, HART_CG, 0, 5))
    a.emit(trap(HART_HA, 0))
    a.emit(and_o(6, 8, 8))
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS, "rd5": 0, "rd6": 0}


@case("hart_reserved_unimpl", "cfx_hart rc1/rc6/rc7 and RO writes => CFXREG")
def _hart_reserved_unimpl():
    a = Asm()
    set_vector(a, 3, OFF_FH3)          # DADAO-12 §5.2: CFXREG -> current monitor (hmon)
    n = 0

    def fault(insn):
        nonlocal n
        n += 1
        idx = len(a.words)
        a.emit(insn)
        check_frame(a, hmon_addr(0) + idx * 4, n)

    a.emit(*load_rd(22, 0))
    fault(cfx2rd(HART_HA, HART_CG, 1, 5))
    fault(cfx2rd(HART_HA, HART_CG, 6, 5))
    fault(cfx2rd(HART_HA, HART_CG, 7, 5))
    fault(cfx2rc(HART_HA, HART_CG, 0, 22))
    fault(cfx2rc(HART_HA, HART_CG, 2, 22))
    last_idx = len(a.words)
    a.emit(cfx2rc(HART_HA, HART_CG, 3, 22))
    check_frame(a, hmon_addr(0) + last_idx * 4, 6)
    finish(a)
    return build_rom(a.resolve(), HANDLERS), {
        "exit": EXIT_PASS, "rd14": 0, "rd12": 6,
        "rd10": CFXREG, "rd11": hmon_addr(0) + last_idx * 4,
    }


@case("cycle_insn_read", "cycle/insn readable, monotonic, non-negative, RO")
def _cycle_insn_read():
    a = Asm()
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 5))
    a.emit(cfx2rd(HART_HA, HART_CG, 3, 6))
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 7))
    a.emit(cfx2rd(HART_HA, HART_CG, 3, 8))
    flag = 13
    # monotonic (allow equality)
    ok1, ok2 = "ci_mono_c", "ci_mono_i"
    a.emit(cmp_uo(20, 7, 5))
    a.br("nn", 20, 0, ok1)
    a.emit(*load_rd(flag, 1))
    a.mark(ok1)
    a.emit(cmp_uo(20, 8, 6))
    a.br("nn", 20, 0, ok2)
    a.emit(*load_rd(flag, 2))
    a.mark(ok2)
    # non-negative (< 2^63) and insn > 0
    a.emit(*load_rd(21, BIT63))
    a.emit(and_o(20, 5, 21))
    ok3 = "ci_nonneg_c"
    a.br("z", 20, 0, ok3)
    a.emit(*load_rd(flag, 3))
    a.mark(ok3)
    a.emit(and_o(20, 6, 21))
    ok4 = "ci_nonneg_i"
    a.br("z", 20, 0, ok4)
    a.emit(*load_rd(flag, 4))
    a.mark(ok4)
    ok5 = "ci_insn_pos"
    a.br("nz", 6, 0, ok5)
    a.emit(*load_rd(flag, 5))
    a.mark(ok5)
    # writes to RO rc2/rc3 => CFXREG
    set_vector(a, 3, OFF_FH3)          # DADAO-12 §5.2: CFXREG -> current monitor (hmon)
    a.emit(*load_rd(22, 0))
    for n, rc in ((1, 2), (2, 3)):
        idx = len(a.words)
        a.emit(cfx2rc(HART_HA, HART_CG, rc, 22))
        check_frame(a, hmon_addr(0) + idx * 4, n)
    finish(a)
    return build_rom(a.resolve(), HANDLERS), {
        "exit": EXIT_PASS, "rd13": 0, "rd14": 0, "rd12": 2,
        "rd5": lambda o: o["rd5"] is not None and o["rd5"] < BIT63,
        "rd6": lambda o: o["rd6"] is not None and 0 < o["rd6"] < BIT63,
    }


@case("cycle_insn_monotonic",
      "cycle strictly advances and insn delta >= N over a 100k-iteration loop",
      dump=False)
def _cycle_insn_monotonic():
    N = 100000
    a = Asm()
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 5))
    a.emit(cfx2rd(HART_HA, HART_CG, 3, 6))
    delay_loop(a, 22, N, "main")                     # >= 2 instructions/iter
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 7))
    a.emit(cfx2rd(HART_HA, HART_CG, 3, 8))
    # cycle = virtual-clock ns: the loop must make it strictly increase.
    # (How many ns per instruction is engine-defined; only monotonicity and
    # the per-instruction `insn` counter are contract properties.)
    a.emit(cmp_uo(20, 7, 5))
    a.emit(*load_rd(21, 1))
    a.br("eq", 20, 21, "mono_c")
    a.emit(*exit_seq(0x61))
    a.mark("mono_c")
    # insn counts executed instructions: each iteration is >= 2 of them.
    a.emit(and_o(20, 6, 6))
    a.emit(add_si(20, N))
    a.emit(cmp_uo(21, 8, 20))
    a.br("nn", 21, 0, "mono_i")
    a.emit(*exit_seq(0x62))
    a.mark("mono_i")
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_ctrl_rw", "timer_ctrl writes accept bit0/bit1, ignore bit2")
def _timer_ctrl_rw():
    a = Asm()
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, 22))          # cmp = all-ones (disabled)
    for val, rd in ((0, 5), (1, 6), (3, 7), (5, 8)):
        a.emit(*load_rd(22, val))
        a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, 22))
        a.emit(cfx2rd(HART_HA, HART_TIMER_CG, 0, rd))
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {
        "exit": EXIT_PASS, "rd5": 0, "rd6": CTRL_ENABLE,
        "rd7": CTRL_ENABLE | CTRL_IMASK, "rd8": CTRL_ENABLE,
    }


@case("timer_istatus", "ISTATUS = ENABLE && cmp!=~0 && time>=cmp", dump=False)
def _timer_istatus():
    a = Asm()
    # cmp is read before the ENABLE write, so the monotonic clock has already
    # reached it when timer_ctrl lands: ISTATUS must read as set.
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 22))          # now (ENABLE still 0)
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, 22))          # cmp = now
    a.emit(*load_rd(W_TMP, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, W_TMP))
    a.emit(cfx2rd(HART_HA, HART_TIMER_CG, 0, 5))
    a.emit(*load_rd(W_TMP, CTRL_ISTATUS))
    a.emit(and_o(5, 5, W_TMP))
    ok = "ist_set"
    a.br("nz", 5, 0, ok)
    a.emit(*exit_seq(0x61))
    a.mark(ok)
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, 22))          # cmp = ~0 -> never matches
    a.emit(cfx2rd(HART_HA, HART_TIMER_CG, 0, 6))
    a.emit(*load_rd(W_TMP, CTRL_ISTATUS))
    a.emit(and_o(6, 6, W_TMP))
    ok2 = "ist_clear"
    a.br("z", 6, 0, ok2)
    a.emit(*exit_seq(0x62))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_cmp_clears",
      "writing a new cmp clears ISTATUS and re-arms (second delivery)",
      dump=False)
def _timer_cmp_clears():
    a = Asm()
    set_mon_mask(a, ALL1 & ~SRC_TIMER)               # open the TIMER source
    arm_timer(a)
    check_quiet(a, W_DEAD, _timer_count_cond(1), True, 0x61, "cmpq")
    wait_cond(a, W_BOUND, _timer_count_cond(1), True, "cmp1", 0x62, 0x63)
    # New cmp at now+DELTA: the arm must clear ISTATUS and re-arm.
    arm_timer(a, base=1, tag="cmp2")
    a.emit(cfx2rd(HART_HA, HART_TIMER_CG, 0, 5))
    a.emit(*load_rd(W_TMP, CTRL_ISTATUS))
    a.emit(and_o(5, 5, W_TMP))
    a.br("z", 5, 0, "cmp_ist")
    a.emit(*exit_seq(0x64))
    a.mark("cmp_ist")
    # ISTATUS is clear; the re-armed timer must still deliver once more.
    wait_cond(a, W_BOUND, _timer_count_cond(2), True, "cmp2", 0x65, 0x66)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_ones_disable", "cmp=~0 + ENABLE=1 never matches", dump=False)
def _timer_ones_disable():
    a = Asm()
    # cmp = ~0 is "disabled" regardless of how fast the clock runs, so the
    # fixed work loop below is a valid model-neutral check (no deadline).
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, 22))
    a.emit(*load_rd(21, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, 21))
    delay_loop(a, 22, 2000, "ones")
    a.emit(cfx2rd(HART_HA, HART_TIMER_CG, 0, 5))
    a.emit(*load_rd(20, CTRL_ISTATUS))
    a.emit(and_o(20, 5, 20))
    ok = "ones_ist"
    a.br("z", 20, 0, ok)
    a.emit(*exit_seq(0x61))
    a.mark(ok)
    ram_load(a, RAM_ASYNC_SEQ, 6)
    ok2 = "ones_no_irq"
    a.br("z", 6, 0, ok2)
    a.emit(*exit_seq(0x62))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_interrupt",
      "expiry enters cfx_hart once; cg15 capture bit15, ISTATUS, async_num+1",
      dump=False)
def _timer_interrupt():
    a = Asm()
    set_mon_mask(a, ALL1 & ~SRC_TIMER)
    arm_timer(a)
    check_quiet(a, W_DEAD, _timer_count_cond(1), True, 0x61, "irqq")
    wait_cond(a, W_BOUND, _timer_count_cond(1), True, "irq", 0x62, 0x63)
    # Delivery target is cfx_hart; the capture names the source by cfxha.
    ram_load(a, RAM_ASYNC_FRAME, 6)
    a.emit(*load_rd(20, SRC_TIMER))
    ok1 = "irq_frame"
    a.br("eq", 6, 20, ok1)
    a.emit(*exit_seq(0x64))
    a.mark(ok1)
    ram_load(a, RAM_ASYNC_PENDING, 7)
    ok2 = "irq_no_pending"
    a.br("z", 7, 0, ok2)
    a.emit(*exit_seq(0x65))
    a.mark(ok2)
    # cause_ip is 4-byte aligned and non-zero (the interrupted boundary).
    ram_load(a, RAM_ASYNC_IP, 8)
    a.emit(*load_rd(20, 3))
    a.emit(and_o(20, 8, 20))
    ok3 = "irq_ip_align"
    a.br("z", 20, 0, ok3)
    a.emit(*exit_seq(0x66))
    a.mark(ok3)
    a.emit(cfx2rd(HART_HA, HART_TIMER_CG, 0, 9))
    a.emit(*load_rd(W_TMP, CTRL_ISTATUS))
    a.emit(and_o(9, 9, W_TMP))
    ok4 = "irq_istatus"
    a.br("nz", 9, 0, ok4)
    a.emit(*exit_seq(0x67))
    a.mark(ok4)
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 10))
    a.emit(*load_rd(20, 1))
    ok5 = "irq_async_num"
    a.br("eq", 10, 20, ok5)
    a.emit(*exit_seq(0x68))
    a.mark(ok5)
    delay_loop(a, 22, 3000, "irq_quiet")            # one-shot: no re-entry
    ram_load(a, RAM_ASYNC_SEQ, 11)
    ok6 = "irq_once"
    a.br("eq", 11, 20, ok6)
    a.emit(*exit_seq(0x69))
    a.mark(ok6)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_imask_pending",
      "IMASK defers TIMER into cg15 rc5 bit15; release delivers once",
      dump=False)
def _timer_imask_pending():
    a = Asm()
    set_mon_mask(a, ALL1 & ~SRC_TIMER)
    arm_timer(a, DELTA_NS, CTRL_ENABLE | CTRL_IMASK)
    check_quiet(a, W_DEAD, _timer_count_cond(1), True, 0x61, "imq")
    wait_cond(a, W_BOUND, _cfx_mask_cond(_pending_timer, SRC_TIMER), False,
              "imp", 0x62, 0x63)
    # Still no delivery while IMASK is set.
    ram_load(a, RAM_ASYNC_SEQ, 5)
    ok1 = "imask_count0"
    a.br("z", 5, 0, ok1)
    a.emit(*exit_seq(0x64))
    a.mark(ok1)
    # ISTATUS is set at expiry even while deferred.
    a.emit(cfx2rd(HART_HA, HART_TIMER_CG, 0, 6))
    a.emit(*load_rd(W_TMP, CTRL_ISTATUS))
    a.emit(and_o(6, 6, W_TMP))
    ok2 = "imask_istatus"
    a.br("nz", 6, 0, ok2)
    a.emit(*exit_seq(0x65))
    a.mark(ok2)
    # Release IMASK -> the pending bit re-kicks and delivers exactly once.
    a.emit(*load_rd(21, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 0, 21))
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, W_NOW))
    _set_bound(a, W_NOW)
    wait_cond(a, W_BOUND, _timer_count_cond(1), True, "imrel", 0x66, 0x67)
    ram_load(a, RAM_ASYNC_FRAME, 7)
    a.emit(*load_rd(20, SRC_TIMER))
    ok3 = "imask_frame"
    a.br("eq", 7, 20, ok3)
    a.emit(*exit_seq(0x68))
    a.mark(ok3)
    a.emit(cfx2rd(HART_HA, 15, RC_PENDING, 8))
    a.emit(*load_rd(20, SRC_TIMER))
    a.emit(and_o(20, 8, 20))
    ok5 = "imask_pending_clear"
    a.br("z", 20, 0, ok5)
    a.emit(*exit_seq(0x69))
    a.mark(ok5)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_retrigger", "re-armed one-shot: second entry overwrites cg15",
      dump=False)
def _timer_retrigger():
    a = Asm()
    set_mon_mask(a, ALL1 & ~SRC_TIMER)
    for tag, want in (("first", 1), ("second", 2)):
        arm_timer(a, base=want - 1, tag=tag)
        check_quiet(a, W_DEAD, _timer_count_cond(want), True,
                    0x61 if want == 1 else 0x63, "rtq_%s" % tag)
        wait_cond(a, W_BOUND, _timer_count_cond(want), True,
                  "rt_%s" % tag, 0x62 if want == 1 else 0x64,
                  0x65 if want == 1 else 0x66)
        ram_load(a, RAM_ASYNC_FRAME, 5)
        a.emit(*load_rd(20, SRC_TIMER))
        ok = "rt_frame_%s" % tag
        a.br("eq", 5, 20, ok)
        a.emit(*exit_seq(0x67 if want == 1 else 0x69))
        a.mark(ok)
    a.emit(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 6))
    a.emit(*load_rd(20, 2))
    ok2 = "rt_async_num"
    a.br("eq", 6, 20, ok2)
    a.emit(*exit_seq(0x6B))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_ack_pending",
      "timer_cmp reload acks the source: pending drops, no stale delivery",
      dump=False)
def _timer_ack_pending():
    a = Asm()
    set_mon_mask(a, ALL1)      # keep TIMER masked
    arm_timer(a, tag="ack")
    wait_cond(a, W_BOUND, _cfx_mask_cond(_pending_timer, SRC_TIMER), False,
              "ackp", 0x61, 0x62)
    a.emit(*load_rd(21, ALL1))                      # cmp = ~0: cancel + ack
    a.emit(cfx2rc(HART_HA, HART_TIMER_CG, 1, 21))
    a.emit(cfx2rd(HART_HA, 15, RC_PENDING, 5))
    a.emit(*load_rd(20, SRC_TIMER))
    a.emit(and_o(20, 5, 20))
    ok1 = "ack_pending_drop"
    a.br("z", 20, 0, ok1)
    a.emit(*exit_seq(0x63))
    a.mark(ok1)
    # Opening the mask now must not deliver the acked event.
    set_mon_mask(a, 0)
    delay_loop(a, 22, 20000, "ack_quiet")
    ram_load(a, RAM_ASYNC_SEQ, 6)
    ok2 = "ack_no_stale"
    a.br("z", 6, 0, ok2)
    a.emit(*exit_seq(0x64))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("sbi_time_monotonic", "SBI_TIME_GET is strictly monotonic over a work loop",
      dump=False)
def _sbi_time_monotonic():
    N = 5000
    a = Asm()
    a.emit(trap(TIME_HA, 0))
    a.emit(and_o(5, 8, 8))                           # t1
    delay_loop(a, 22, N, "sbi_time")                 # 2 instructions/iter
    a.emit(trap(TIME_HA, 0))
    a.emit(and_o(6, 8, 8))                           # t2
    # t2 >= t1 + 1: strictly increasing (how fast is engine-defined)
    a.emit(and_o(20, 5, 5))
    a.emit(add_si(20, 1))
    a.emit(cmp_uo(21, 6, 20))
    ok = "sbi_time_delta"
    a.br("nn", 21, 0, ok)
    a.emit(*exit_seq(0x61))
    a.mark(ok)
    a.emit(cfx2rd(TIME_HA, TIME_CG, 0, 7))
    a.emit(*load_rd(20, TIME_FREQ))
    ok2 = "sbi_time_freq"
    a.br("eq", 7, 20, ok2)
    a.emit(*exit_seq(0x62))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("sbi_hart_set_timer", "SBI_HART_SET_TIMER arms and delivers TIMER",
      dump=False)
def _sbi_hart_set_timer():
    a = Asm()
    set_mon_mask(a, ALL1 & ~SRC_TIMER)               # open the TIMER source
    arm_timer_sbi(a)
    check_quiet(a, W_DEAD, _timer_count_cond(1), True, 0x62, "sbiq")
    wait_cond(a, W_BOUND, _timer_count_cond(1), True, "sbi", 0x63, 0x64)
    ram_load(a, RAM_ASYNC_FRAME, 7)
    a.emit(*load_rd(20, SRC_TIMER))
    ok3 = "sbi_st_frame"
    a.br("eq", 7, 20, ok3)
    a.emit(*exit_seq(0x65))
    a.mark(ok3)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("regress_unimpl_cfx",
      "cfx5 (cache) has a register row; cfx33 (llc) has none => CFXREG")
def _regress_unimpl_cfx():
    a = Asm()
    set_vector(a, 3, OFF_FH3)
    # cfx5 is implemented in this profile even with the cache model off:
    # cg8 rc0 (cache_exist) reads 0 and cg0 rc0 (its user-mode cfxtrap mask)
    # is a legal register.  Stale pre-ADR-0045 expectations (CFXREG for any
    # cfx5 read) are no longer architecture.
    a.emit(cfx2rd(CACHE_HA, 8, 0, 5))
    a.emit(cfx2rd(CACHE_HA, 0, 0, 6))
    # A cfx the profile does not implement has no register row: read => CFXREG
    # (spec/Kaiwu §3; cfx33/llc is absent from this profile's list).
    idx = len(a.words)
    a.emit(cfx2rd(33, 0, 0, 5))
    check_frame(a, hmon_addr(0) + idx * 4, 1)
    finish(a)
    return build_rom(a.resolve(), HANDLERS), {
        "exit": EXIT_PASS, "rd14": 0, "rd12": 1, "rd5": 0,
        "rd10": CFXREG, "rd11": hmon_addr(0) + idx * 4,
    }


# ---------------------------------------------------------------------------
# doc case: spec / contract table shape (offline, no QEMU)
# ---------------------------------------------------------------------------

DOC_CASE = "doc_shape"


def _split_row(line):
    cells, cur, i = [], [], 0
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def _section(text, start, end):
    if start not in text:
        raise AssertionError("section start not found: %r" % start)
    body = text.split(start, 1)[1]
    if end is not None:
        if end not in body:
            raise AssertionError("section end not found: %r" % end)
        body = body.split(end, 1)[0]
    return body


def _table_rows(sec):
    rows = []
    for line in sec.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _split_row(line)
        if cells and re.fullmatch(r"-?\d+", cells[0]):
            rows.append(cells)
    return rows


def run_doc():
    failures = []

    def check(name, ok, detail):
        print("[%s] %-40s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            failures.append(name)

    see = open(SPEC_SEE, encoding="utf-8").read()
    sbi = open(SPEC_SBI, encoding="utf-8").read()
    contract = open(CONTRACT_SEE, encoding="utf-8").read()

    sec47 = _section(see, "### 4.7 cfx_hart - hart management", "### 4.8")
    rows47 = {(int(r[0]), r[1]): r for r in _table_rows(sec47)}
    want47 = {
        (8, "0"): ("cfx_hart_hart_id", "RO"),
        (8, "2"): ("cfx_hart_cycle", "RO"),
        (8, "3"): ("cfx_hart_insn", "RO"),
        (8, "4"): ("cfx_hart_timer_cmp", "RW"),
        (8, "5"): ("cfx_hart_timer_ctrl", "RW"),
    }
    for key, (regname, access) in want47.items():
        r = rows47.get(key)
        ok = bool(r) and len(r) >= 6 and r[3] == regname and r[5] == access
        check("cfx_hart_%s_%s" % key, ok,
              "row=%r" % (r,))
    for key in ((8, "1"), (8, "6"), (8, "7")):
        r = rows47.get(key)
        ok = bool(r) and len(r) >= 6 and r[3] == "—"
        check("cfx_hart_reserved_%s" % (key,), ok, "row=%r" % (r,))
    check("cfx_hart_no_128bit_split",
          not any(k for k in rows47 if k[1] in ("2", "3", "4", "5")
                  and rows47[k][3] in ("cfx_hart_cycle_lo", "cfx_hart_cycle_hi",
                                       "cfx_hart_insn_lo", "cfx_hart_insn_hi")),
          "old lo/hi rows absent")
    check("cfx_hart_cycle_64bit", "64 位" in rows47[(8, "2")][6],
          rows47[(8, "2")][6])
    check("cfx_hart_insn_64bit", "64 位" in rows47[(8, "3")][6],
          rows47[(8, "3")][6])
    check("cfx_hart_no_old_names",
          "cycle_lo" not in sec47 and "cycle_hi" not in sec47 and
          "insn_lo" not in sec47 and "insn_hi" not in sec47,
          "cycle_lo/hi + insn_lo/hi absent")

    # ADR-0061 R2: cg15 is a seven-slot capture buffer (two HW/RO bitmaps),
    # and the async source mask lives on the running mode's monitor (cg15 rc3).
    want9 = {
        (9, "0"): ("cfx_hart_async_prev_run_mode", "HW/RW"),
        (9, "1"): ("cfx_hart_async_prev_cfx_code", "HW/RW"),
        (9, "2"): ("cfx_hart_async_cause_ip", "HW/RW"),
        (9, "3"): ("cfx_hart_async_src_frame", "HW/RO"),
        (9, "4"): ("cfx_hart_async_src_pending", "HW/RO"),
        (9, "5"): ("cfx_hart_async_excp_vector", "RW"),
        (9, "6"): ("cfx_hart_async_switch_run_mode", "RW"),
    }
    for key, (regname, access) in want9.items():
        r = rows47.get(key)
        ok = bool(r) and len(r) >= 6 and r[3] == regname and r[5] == access
        check("cfx_hart_cg15_%s_%s" % key, ok, "row=%r" % (r,))
    check("cfx_hart_cg15_capture_buffer",
          "捕获缓冲" in sec47 and "每次异步进入整体覆盖" in sec47,
          "cg15 described as a capture buffer overwritten on every entry")
    check("cfx_hart_cg15_no_valid_bit", "无有效位" in sec47,
          "no frame-valid bit on the capture")
    sec44 = _section(see, "### 4.4 cfx_hmon", "### 4.5")
    rows44 = {(int(r[0]), r[1]): r for r in _table_rows(sec44)}
    r = rows44.get((8, "1"))
    check("hmon_async_mask_row",
          bool(r) and len(r) >= 6 and r[3] == "cfx_hmon_async_intr_mask"
          and r[4] == "全1" and r[5] == "RW",
          "row=%r" % (r,))
    check("hmon_no_cfx_intr_mask_rows",
          not any(k[1] == "4" for k in rows44) and "hypv_cfx_intr_mask" not in sec44,
          "cg0-cg3 rc4 source masks are gone (ADR-0061 D5)")

    sec410 = _section(see, "### 4.10 cfx_time - 全局时间计数器", "### 4.11")
    rows410 = {(int(r[0]), r[1]): r for r in _table_rows(sec410)}
    for rc, regname in (("0", "cfx_time_freq"), ("1", "cfx_time_value")):
        r = rows410.get((10, rc))
        ok = bool(r) and len(r) >= 6 and r[3] == regname and r[5] == "RO"
        check("cfx_time_rc%s" % rc, ok, "row=%r" % (r,))
    check("cfx_time_rc1_64bit", "64 位" in rows410[(10, "1")][6],
          rows410[(10, "1")][6])
    check("cfx_time_reserved_2_63",
          (10, "2-63") in rows410 and rows410[(10, "2-63")][3] == "—",
          "row=%r" % (rows410.get((10, "2-63")),))
    check("cfx_time_no_old_rc", (10, "7") not in rows410 and (10, "8") not in rows410,
          "rc7/rc8 absent")

    sec7 = _section(sbi, "## 7. Hart管理（cfx_hart）", "## 8.")
    rows7 = {int(r[0]): r for r in _table_rows(sec7) if re.fullmatch(r"\d+", r[0])}
    check("sbi_fid0_get_id", rows7[0][1] == "SBI_HART_GET_ID", rows7[0][1])
    check("sbi_fid1_set_timer", rows7[1][1] == "SBI_HART_SET_TIMER", rows7[1][1])
    check("sbi_set_timer_64bit", "64 位" in rows7[1][4], rows7[1][4])
    sec10 = _section(sbi, "## 10. 全局时间（cfx_time）", "## 11.")
    rows10 = {int(r[0]): r for r in _table_rows(sec10) if re.fullmatch(r"\d+", r[0])}
    check("sbi_time_get", rows10[0][1] == "SBI_TIME_GET", rows10[0][1])
    check("sbi_time_get_64bit", "64 位" in rows10[0][4], rows10[0][4])

    sec3 = _section(contract, "## §3 cfx 与权限", "## §4")
    check("contract_cfx_time", "cfx_time" in sec3 and "1_000_000_000" in sec3,
          "cfx_time + 1 GHz present")
    check("contract_cfx_hart_cycle_insn",
          "cfx_hart_cycle" in sec3 or ("cycle" in sec3 and "insn" in sec3),
          "cycle/insn present")
    check("contract_async_boundary",
          "异步边界" in sec3 and "PMEM_DMA" in sec3 and "TIMER" in sec3,
          "async boundary entry present")

    print("doc: %d failed" % len(failures))
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
            obs = observe(log) if dump else {}
            obs["exit"] = rc
            diffs = []
            for k, v in exp.items():
                av = obs.get(k)
                try:
                    ok = v(obs) if callable(v) else (av == v)
                except Exception as exc:                  # noqa: BLE001
                    ok = False
                    diffs.append("%s raised %r" % (k, exc))
                    continue
                if not ok:
                    diffs.append("%s exp=%r got=%r" % (
                        k, v, ("0x%x" % av) if isinstance(av, int) else av))
            if diffs:
                return False, "; ".join(diffs), exp
            return True, "ok", exp
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
        print("%-26s %s" % (DOC_CASE, "doc: spec/contract rc layout + 64-bit wording"))
        for n, d, _fn, _dump in CASES:
            print("%-26s %s" % (n, d))
        return 0

    if args.only:
        if args.only == DOC_CASE:
            return run_doc()
        ok, why, exp = run_case(args.only)
        print("%s %-26s %s%s" % ("PASS" if ok else "FAIL", args.only, why,
                                 "" if ok else " (exp=%r)" % (exp,)))
        return 0 if ok else 1

    failed = 0
    if run_doc() != 0:
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
    print("%d/%d runtime passed" % (len(names) - runtime_failed, len(names)))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
