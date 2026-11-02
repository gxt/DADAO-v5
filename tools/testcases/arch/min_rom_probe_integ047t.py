#!/usr/bin/env python3
"""Min ROM probe for INTEG-047t: cfx_pmem DMA 的 SBI 契约与最小验证（FID 6/7/8）.

Two kinds of checks:

  * ``doc`` (pure Python, no QEMU): parse ``spec/DADAO-22`` §1/§9 and
    ``.tao/contracts/contract-see.md`` and assert the SBI table shape.
  * ``runtime`` (min-ROM, QEMU): the probe embeds a **test-only** cfx_pmem SBI
    provider in the ROM handler area.  It is NOT a production implementation:
    the repository has no firmware host for cfx_pmem yet (smon does not
    dispatch SBI functions, see INTEG-046t), so FID 6/7/8 are only exercised
    here, and the production provider is left to a separate task.

Expectations are derived by hand from the frozen spec / contract:
  - spec/DADAO-22 §1 (error codes; -5 = SBI_ERR_BUSY), §9 (FID 0-8 table,
    START/STATUS/WAIT semantics; no SBI_PMEM_GET_SRAM).
  - .tao/contracts/contract-see.md §2 / §5 (projection of the same rules).
  - spec/DADAO-12 §4.9 (cg15 DMA hardware semantics: START self-clear,
    BUSY/DONE(W1C)/ERROR(W1C)/ERR_CODE one-hot, BUSY ignores writes).
  Never from the QEMU implementation.

Observation channels (same convention as min_rom_probe_integ042t.py):
  * register results -> QEMU `-d cpu` dump (last dump block);
  * pass/fail -> semihosting SYS_EXIT (ADR-0020 D8).

The encoder / run() / observe() / bootstrap_rom() helpers are copied in place
from min_rom_probe_integ042t.py (no import, to keep the two case tables
independent); that file is not modified.

The ``start_busy_returns_busy`` case needs the 1 ms BUSY window to survive
between two traps.  Under the default virtual clock the host-side `-d cpu`
dump between traps is slow enough to consume that window (pre-check: not
observable).  The case therefore runs with ``-icount shift=0`` (1 ns per
instruction, so 1 ms >> a few dozen instructions) and self-checks its result,
reporting pass/fail through the semihosting exit code.  ``-icount`` disables
the register dump in this QEMU build, hence the self-check channel.

Usage:
  min_rom_probe_integ047t.py --doc          # doc checks only (offline)
  min_rom_probe_integ047t.py                # doc + runtime
  min_rom_probe_integ047t.py --only NAME    # one check (run.sh --inject)
  min_rom_probe_integ047t.py --list
  min_rom_probe_integ047t.py --qemu PATH

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import re
import struct
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
QEMU = DEFAULT_QEMU
WORKDIR = "/tmp/opencode/INTEG-047t"
TIMEOUT = 40

SPEC_SBI = os.path.join(_REPO, "spec", "DADAO-22-SBI-主管系统二进制接口.md")
CONTRACT_SEE = os.path.join(_REPO, ".tao", "contracts", "contract-see.md")

ROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0xFC00_0000_0000

# cfxha / internal address space (DADAO-12 §2.1, Machine-01 §1.1)
PMEM_HA = 17
PMEM_BASE = 0x47ff_0000_0000          # cfx17, SRAM internal offset 0x3ff_0000_0000
PMEM_OLD_BASE = PMEM_HA << 42         # internal offset 0 (outside the SRAM)

# cg15 DMA registers (DADAO-12 §4.9)
PMEM_DMA_CG = 15
DMA_SRC_RC, DMA_DST_RC, DMA_SIZE_RC, DMA_CTRL_RC, DMA_STATUS_RC = 0, 1, 2, 3, 4

# dma_ctrl / dma_status bits (DADAO-12 §4.9)
CTRL_START = 1 << 0
CTRL_DIR = 1 << 1
ST_BUSY = 1 << 0
ST_DONE = 1 << 1
ST_ERROR = 1 << 2
ERR_SIZE = 1 << 3
ERR_CFX_RANGE = 1 << 4

CAUSE_CFXTRAP = 1 << 0
CG5_CAUSE_ID_RC, CG5_CAUSE_INFO_RC = 2, 4
CG3_SWITCH_MODE_RC, CG3_EXCP_VECTOR_RC = 8, 10
MODE_H = 3

# SBI error codes (DADAO-22 §1)
SBI_SUCCESS = 0
SBI_ERR_NOT_SUPPORTED = -2
SBI_ERR_BUSY = -5
NEG5 = SBI_ERR_BUSY & 0xFFFF_FFFF_FFFF_FFFF
NEG2 = SBI_ERR_NOT_SUPPORTED & 0xFFFF_FFFF_FFFF_FFFF

EXIT_PASS = 0x00
EXIT_BUSY_FIRST = 0xE1
EXIT_BUSY_SECOND = 0xE2

DATA_A = RAM_BASE + 0x1000

OFF_PMEM_HANDLER = 0x800
PMEM_HANDLER = ROM_BASE + OFF_PMEM_HANDLER

SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = 0xFC00_00FF_F000

MAGIC = 0x1122_3344_5566_7788
MAGIC2 = 0x99AA_BBCC_DDEE_FF00


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
def cfx2rd(ha, cg, rc, rd):  return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def cfx2rc(ha, cg, rc, rd):  return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def trap(ha, immu18):        return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
def escape(ha, imms18):      return (0x7E << 24) | (ha << 18) | (imms18 & 0x3FFFF)
def swym():                  return 0x47880000


def _orrr(op, ha, hb, hc, hd):
    return (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd


def and_o(rdhb, rdhc, rdhd):
    return _orrr(0x40, 0x08, rdhb, rdhc, rdhd)


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
    """Report `code` via semihosting SYS_EXIT -> host $? (ADR-0020 D8)."""
    return ([jump_iiii(1)]
            + load_rb(16, SEMI_BLOCK)
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


class Asm:
    """Tiny label-based assembler over the encoders above (word granularity)."""

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
            # Empirically (and per rb0 == current IP in this ISA model) the
            # taken target is `idx + off`; see the runtime cases.
            off = self.labels[label] - idx
            self.words[idx] = (br_eq if kind == "eq" else br_ne)(rd_a, rd_b, off)
        return self.words


# ---------------------------------------------------------------------------
# Test-only cfx_pmem SBI provider (FID 6/7/8).
#
# **测试专用，非生产实现**：本仓库当前没有 cfx_pmem 的固件承载者（smon 不做
# 功能分发），这里只是探针内嵌的一段 ROM 处理代码，用来验证契约可执行性。
# ---------------------------------------------------------------------------
def build_provider():
    a = Asm()
    a.mark("disp")
    a.emit(cfx2rd(PMEM_HA, 5, CG5_CAUSE_ID_RC, 20))
    a.emit(*load_rd(21, CAUSE_CFXTRAP))
    a.br("ne", 20, 21, "unknown")
    a.emit(cfx2rd(PMEM_HA, 5, CG5_CAUSE_INFO_RC, 20))   # cause_info = immu18
    a.emit(*load_rd(21, 0x3FFFF))
    a.emit(and_o(20, 20, 21))
    a.emit(*load_rd(21, 6))
    a.br("eq", 20, 21, "dma_start")
    a.emit(*load_rd(21, 7))
    a.br("eq", 20, 21, "dma_status")
    a.emit(*load_rd(21, 8))
    a.br("eq", 20, 21, "dma_wait")
    a.mark("unknown")
    a.emit(escape(PMEM_HA, 1))                          # leave rd8 untouched
    # FID 6: START -- only the BUSY check, then register move.
    a.mark("dma_start")
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 21))
    a.emit(*load_rd(22, ST_BUSY))
    a.emit(and_o(21, 21, 22))
    a.br("ne", 21, 0, "busy")
    a.emit(*load_rd(22, 1))
    a.emit(and_o(21, 16, 22))                           # rd21 = rd16 & 1 (dir)
    a.emit(*load_rd(23, CTRL_START))
    a.br("eq", 21, 0, "ctrl_ready")
    a.emit(*load_rd(23, CTRL_START | CTRL_DIR))
    a.mark("ctrl_ready")
    a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_SRC_RC, 17))
    a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_DST_RC, 18))
    a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_SIZE_RC, 19))
    a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_CTRL_RC, 23))
    a.emit(*load_rd(8, SBI_SUCCESS))
    a.emit(escape(PMEM_HA, 1))
    a.mark("busy")
    a.emit(*load_rd(8, NEG5))
    a.emit(escape(PMEM_HA, 1))
    # FID 7: STATUS -- raw dma_status, no error mapping, no W1C.
    a.mark("dma_status")
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 8))
    a.emit(escape(PMEM_HA, 1))
    # FID 8: WAIT -- reserved: no clock/timer, never poll, never fake timeout.
    a.mark("dma_wait")
    a.emit(*load_rd(8, NEG2))
    a.emit(escape(PMEM_HA, 1))
    return a.resolve()


PROVIDER = build_provider()


# ---------------------------------------------------------------------------
# Program-building helpers (body runs in hmon / cfx3, hypv mode).
# ---------------------------------------------------------------------------

def setup_provider(a, handler=None):
    if handler is None:
        # The ROM body is prefixed by the bootstrap (BOOTSTRAP_OFF bytes), so
        # the handler's *absolute* address is its build offset plus that shift.
        handler = PMEM_HANDLER + BOOTSTRAP_OFF
    a.emit(*load_rd(17, MODE_H))
    a.emit(cfx2rc(PMEM_HA, MODE_H, CG3_SWITCH_MODE_RC, 17))
    a.emit(*load_rd(17, handler))
    a.emit(cfx2rc(PMEM_HA, MODE_H, CG3_EXCP_VECTOR_RC, 17))


def fill_sram(a, off, value=MAGIC):
    a.emit(*load_rb(3, PMEM_BASE + off))
    a.emit(*load_rd(17, value))
    a.emit(st_o(17, 3, 0))


def store64(a, addr, value, rd=17, rb=3):
    a.emit(*load_rb(rb, addr))
    a.emit(*load_rd(rd, value))
    a.emit(st_o(rd, rb, 0))


def load64(a, addr, rd, rb=4):
    """Load a 64-bit word; clobbers `rb` only."""
    a.emit(*load_rb(rb, addr))
    a.emit(ld_o(rd, rb, 0))


def status_clear(a):
    a.emit(*load_rd(20, ST_DONE | ST_ERROR))
    a.emit(cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 20))


def sbi_params(a, dir_, src, dst, size):
    a.emit(*load_rd(16, dir_))
    a.emit(*load_rd(17, src))
    a.emit(*load_rd(18, dst))
    a.emit(*load_rd(19, size))


def poll_busy_clear(a, rd=12):
    a.mark("poll")
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, rd))
    a.emit(*load_rd(20, ST_BUSY))
    a.emit(and_o(rd, rd, 20))
    a.br("ne", rd, 0, "poll")


def build_rom(prog, handlers=None):
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers or {}):
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(handlers[off])
    while len(rom) < 0x500:
        rom += words_to_bytes([swym()])
    return bytes(rom)


# ---------------------------------------------------------------------------
# QEMU runner + dump parsing
# ---------------------------------------------------------------------------

def run(rom, icount_shift=None):
    os.makedirs(WORKDIR, exist_ok=True)
    rp = os.path.join(WORKDIR, "rom.bin")
    kp = os.path.join(WORKDIR, "kernel.bin")
    lp = os.path.join(WORKDIR, "cpu.log")
    with open(rp, "wb") as f:
        f.write(rom)
    with open(kp, "wb") as f:
        f.write(b"\x00" * 16)
    cmd = [QEMU, "-M", "dadao-m1", "-nographic", "-bios", rp, "-kernel", kp,
           "-semihosting-config", "enable=on,target=native",
           "-d", "cpu", "-D", lp]
    if icount_shift is not None:
        cmd += ["-icount", "shift=%d" % icount_shift]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, text=True)
        rc = r.returncode & 0xFF
        err = r.stderr
    except subprocess.TimeoutExpired:
        return None, "", "TIMEOUT"
    with open(lp) as f:
        log = f.read()
    return rc, log, err


def lasthex(log, pat):
    m = None
    for x in re.finditer(pat, log):
        m = x
    return int(m.group(1), 16) if m else None


def observe(log):
    o = {}
    for n in (5, 6, 7, 8, 9, 10, 11, 12):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    return o


# ---------------------------------------------------------------------------
# Runtime cases
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc, icount_shift=None):
    def deco(fn):
        CASES.append((name, desc, fn, icount_shift))
        return fn
    return deco


@case("start_cfx_to_pa", "SBI START dir=0 copies SRAM -> PA; STATUS = DONE")
def _start_cfx_to_pa():
    a = Asm()
    setup_provider(a)
    fill_sram(a, 0x0000, MAGIC)
    store64(a, DATA_A, 0)
    status_clear(a)
    sbi_params(a, 0, PMEM_BASE, DATA_A, 8)
    a.emit(trap(PMEM_HA, 6))
    a.emit(and_o(5, 8, 8))                  # rd5 = START return
    poll_busy_clear(a)
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 6))
    load64(a, DATA_A, rd=7)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), {OFF_PMEM_HANDLER: PROVIDER}), \
        {"exit": EXIT_PASS, "rd5": SBI_SUCCESS, "rd6": ST_DONE, "rd7": MAGIC}


@case("start_pa_to_cfx", "SBI START dir=1 copies PA -> SRAM; STATUS = DONE")
def _start_pa_to_cfx():
    a = Asm()
    setup_provider(a)
    store64(a, DATA_A, MAGIC2)
    fill_sram(a, 0x0200, 0)
    status_clear(a)
    sbi_params(a, 1, DATA_A, PMEM_BASE + 0x0200, 8)
    a.emit(trap(PMEM_HA, 6))
    a.emit(and_o(5, 8, 8))
    poll_busy_clear(a)
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 6))
    load64(a, PMEM_BASE + 0x0200, rd=7)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), {OFF_PMEM_HANDLER: PROVIDER}), \
        {"exit": EXIT_PASS, "rd5": SBI_SUCCESS, "rd6": ST_DONE, "rd7": MAGIC2}


@case("status_raw_equals_cg15", "FID 7 returns the raw dma_status (bit-equal to cg15 rc4)")
def _status_raw_equals_cg15():
    a = Asm()
    setup_provider(a)
    status_clear(a)
    sbi_params(a, 0, PMEM_BASE, DATA_A, 0)  # size=0 -> hardware SIZE error
    a.emit(trap(PMEM_HA, 6))
    a.emit(and_o(5, 8, 8))                  # rd5 = START return
    a.emit(trap(PMEM_HA, 7))
    a.emit(and_o(6, 8, 8))                  # rd6 = SBI STATUS
    a.emit(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 7))  # rd7 = raw read
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), {OFF_PMEM_HANDLER: PROVIDER}), \
        {"exit": EXIT_PASS, "rd5": SBI_SUCCESS,
         "rd6": ST_ERROR | ERR_SIZE, "rd7": ST_ERROR | ERR_SIZE}


@case("no_sbi_side_validation", "START returns 0 for bad size/src; only ERR_CODE judges")
def _no_sbi_side_validation():
    a = Asm()
    setup_provider(a)
    status_clear(a)
    sbi_params(a, 0, PMEM_BASE, DATA_A, 0)  # size = 0: illegal, SBI must not check
    a.emit(trap(PMEM_HA, 6))
    a.emit(and_o(5, 8, 8))                  # rd5 = 0
    a.emit(trap(PMEM_HA, 7))
    a.emit(and_o(6, 8, 8))                  # rd6 = ERROR | SIZE
    status_clear(a)
    sbi_params(a, 0, PMEM_OLD_BASE, DATA_A, 8)  # src outside SRAM
    a.emit(trap(PMEM_HA, 6))
    a.emit(and_o(7, 8, 8))                  # rd7 = 0
    a.emit(trap(PMEM_HA, 7))
    a.emit(and_o(8, 8, 8))                  # rd8 = ERROR | CFX_RANGE
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), {OFF_PMEM_HANDLER: PROVIDER}), \
        {"exit": EXIT_PASS, "rd5": SBI_SUCCESS, "rd6": ST_ERROR | ERR_SIZE,
         "rd7": SBI_SUCCESS, "rd8": ST_ERROR | ERR_CFX_RANGE}


@case("wait_not_supported", "FID 8 is reserved: returns -2 and starts no transfer")
def _wait_not_supported():
    a = Asm()
    setup_provider(a)
    fill_sram(a, 0x0000, MAGIC)
    store64(a, DATA_A, 0)
    status_clear(a)
    sbi_params(a, 0, PMEM_BASE, DATA_A, 8)  # parameters latched, no START
    a.emit(trap(PMEM_HA, 8))
    a.emit(and_o(5, 8, 8))                  # rd5 = -2
    a.emit(trap(PMEM_HA, 7))
    a.emit(and_o(6, 8, 8))                  # rd6 = 0 (no transfer, not busy)
    load64(a, DATA_A, rd=7)                 # rd7 = 0 (destination untouched)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), {OFF_PMEM_HANDLER: PROVIDER}), \
        {"exit": EXIT_PASS, "rd5": NEG2, "rd6": 0, "rd7": 0}


@case("start_busy_returns_busy",
      "two back-to-back STARTs: first 0, second -5 (icount; self-checked)",
      icount_shift=0)
def _start_busy_returns_busy():
    a = Asm()
    setup_provider(a)
    fill_sram(a, 0x0000, MAGIC)
    store64(a, DATA_A, 0)
    status_clear(a)
    sbi_params(a, 0, PMEM_BASE, DATA_A, 8)
    a.emit(trap(PMEM_HA, 6))
    a.emit(and_o(5, 8, 8))                  # rd5 = first START
    a.emit(trap(PMEM_HA, 6))                # second START, immediately
    a.emit(and_o(6, 8, 8))                  # rd6 = second START
    a.emit(*load_rd(20, SBI_SUCCESS))
    a.br("eq", 5, 20, "first_ok")
    a.emit(*exit_seq(EXIT_BUSY_FIRST))
    a.mark("first_ok")
    a.emit(*load_rd(20, NEG5))
    a.br("eq", 6, 20, "second_ok")
    a.emit(*exit_seq(EXIT_BUSY_SECOND))
    a.mark("second_ok")
    # Completion / copy correctness is covered by start_cfx_to_pa; polling to
    # completion here would need ~1e6 instructions (1 ms at shift=0) and is
    # irrelevant to the busy contract.
    a.emit(*exit_seq(EXIT_PASS))
    # -icount shift=0 => 1 ns/instr, so the 1 ms BUSY window spans ~1e6
    # instructions.  The register dump is empty under -icount, so the case
    # self-checks and reports through the semihosting exit code.
    return build_rom(a.resolve(), {OFF_PMEM_HANDLER: PROVIDER}), {"exit": EXIT_PASS}


# ---------------------------------------------------------------------------
# doc case: spec / contract table shape (offline, no QEMU)
# ---------------------------------------------------------------------------

DOC_CASE = "doc_spec_contract_shape"

FIDS_0_5 = [
    (0, "SBI_PMEM_GET_PM_COUNT", "—", "rd8 = count"),
    (1, "SBI_PMEM_GET_PM_START", "rd16 = idx", "rb8 = start"),
    (2, "SBI_PMEM_GET_PM_SIZE", "rd16 = idx", "rd8 = size"),
    (3, "SBI_PMEM_GET_PM_ATTR", "rd16 = idx", "rd8 = attr"),
    (4, "SBI_PMEM_ALLOC_PAGE", "rd16 = size_hint", "rd8 = ppn"),
    (5, "SBI_PMEM_FREE_PAGE", "rd16 = ppn", "—"),
]
FIDS_6_8 = {6: "SBI_PMEM_DMA_START",
            7: "SBI_PMEM_DMA_STATUS",
            8: "SBI_PMEM_DMA_WAIT"}
ERR_BASE = {0: "SBI_SUCCESS", -1: "SBI_ERR_FAILED", -2: "SBI_ERR_NOT_SUPPORTED",
            -3: "SBI_ERR_INVALID_PARAM", -4: "SBI_ERR_NO_DEVICE",
            -5: "SBI_ERR_BUSY"}


def _split_row(line):
    """Split a markdown table row on unescaped '|' (keeps escaped pipes)."""
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
        print("[%s] %-38s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            failures.append(name)

    spec = open(SPEC_SBI, encoding="utf-8").read()
    contract = open(CONTRACT_SEE, encoding="utf-8").read()

    sec9 = _section(spec, "## 9. 物理存储器管理（cfx_pmem）", "## 10.")
    rows9 = _table_rows(sec9)
    fids = [int(r[0]) for r in rows9]
    check("fid_set_is_0_to_8", sorted(fids) == list(range(9)), str(sorted(fids)))
    check("fid_no_duplicates", len(fids) == len(set(fids)),
          "rows=%d unique=%d" % (len(fids), len(set(fids))))
    print("  measured FID set: %s" % sorted(fids))

    by_fid = {int(r[0]): r for r in rows9}
    for fid, name, inp, out in FIDS_0_5:
        r = by_fid.get(fid)
        ok = bool(r) and len(r) >= 4 and r[1] == name and r[2] == inp and r[3] == out
        check("fid_%d_unchanged" % fid, ok,
              "name=%r in=%r out=%r" % (r[1], r[2], r[3]) if r else "missing")
    for fid, name in FIDS_6_8.items():
        r = by_fid.get(fid)
        ok = bool(r) and len(r) >= 5 and r[1] == name
        check("fid_%d_name" % fid, ok, "name=%r" % (r[1] if r else None))

    sec1 = _section(spec, "**错误码**：", "**嵌套调用**")
    errs = {}
    for r in _table_rows(sec1):
        if len(r) >= 2:
            errs[int(r[0])] = r[1]
    check("err_codes_0_to_-5", errs == ERR_BASE, str(sorted(errs.items())))
    check("err_busy_is_-5", errs.get(-5) == "SBI_ERR_BUSY", str(errs.get(-5)))

    # §9 must not *define* SBI_PMEM_GET_SRAM.  The only allowed literal mention
    # is the normative sentence saying it is NOT provided (task §接口规范 1).
    sram_rows = [r for r in rows9 if len(r) >= 2 and r[1] == "SBI_PMEM_GET_SRAM"]
    sram_handlers = sec9.count("cfx_pmem_get_sram")
    sram_mentions = [l for l in sec9.splitlines() if "SBI_PMEM_GET_SRAM" in l]
    sram_ok = (not sram_rows and sram_handlers == 0
               and all("不提供" in l for l in sram_mentions))
    check("no_get_sram_defined_in_spec9", sram_ok,
          "rows=%d handlers=%d mentions=%d (only negation allowed)"
          % (len(sram_rows), sram_handlers, len(sram_mentions)))
    check("no_get_sram_in_contract", "SBI_PMEM_GET_SRAM" not in contract,
          "occurrences=%d" % contract.count("SBI_PMEM_GET_SRAM"))

    sec5 = _section(contract, "## §5 SBI 调用约定", "---")
    check("contract_sec5_has_busy", "SBI_ERR_BUSY" in sec5,
          "SBI_ERR_BUSY count=%d" % sec5.count("SBI_ERR_BUSY"))
    sec2 = _section(contract, "## §2 核内地址空间与复位", "## §3")
    check("contract_sec2_has_dma_sbi", "SBI_PMEM_DMA_START" in sec2
          and "SBI_PMEM_DMA_STATUS" in sec2 and "SBI_PMEM_DMA_WAIT" in sec2,
          "FID 6/7/8 names in §2")

    print("doc: %d checks, %d failed" % (8 + len(FIDS_0_5) + len(FIDS_6_8),
                                         len(failures)))
    return 0 if not failures else 1


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

BOOTSTRAP_OFF = 0x48
STAGE_OFF = 0x24


def bootstrap_prefix():
    ins = load_rd(22, ROM_BASE + STAGE_OFF) + [cfx2rc(3, 3, 10, 22), trap(3, 0)]
    ins += [swym()] * (STAGE_OFF // 4 - len(ins))
    assert len(ins) == STAGE_OFF // 4, len(ins)
    return ins


def bootstrap_stage():
    ins = load_rd(20, 0)
    for cg in (0, 1, 2, 3):
        ins += [cfx2rc(63, cg, 1, 20), cfx2rc(63, cg, 3, 20)]
    ins += [swym()] * (STAGE_OFF // 4 - len(ins))
    assert len(ins) == STAGE_OFF // 4, len(ins)
    return ins


def bootstrap_rom(rom):
    return words_to_bytes(bootstrap_prefix()) + words_to_bytes(bootstrap_stage()) + rom


def run_case(name):
    for n, d, fn, icount in CASES:
        if n == name:
            rom, exp = fn()
            rc, log, err = run(bootstrap_rom(rom), icount_shift=icount)
            if rc is None:
                return False, "TIMEOUT", exp
            obs = observe(log) if icount is None else {}
            obs["exit"] = rc
            diffs = []
            for k, v in exp.items():
                av = obs.get(k)
                if av != v:
                    diffs.append("%s exp=0x%x got=%s" % (
                        k, v, ("0x%x" % av) if av is not None else "None"))
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
        print("%-28s %s" % (DOC_CASE, "doc: spec/contract SBI table shape (offline)"))
        for n, d, _fn, icount in CASES:
            print("%-28s %s%s" % (n, d, " [-icount]" if icount is not None else ""))
        return 0

    if args.only:
        if args.only == DOC_CASE:
            return run_doc()
        ok, why, exp = run_case(args.only)
        print("%s %-28s %s%s" % ("PASS" if ok else "FAIL", args.only, why,
                                 "" if ok else " (exp=%r)" % (exp,)))
        return 0 if ok else 1

    failed = 0
    if run_doc() != 0:
        failed += 1
    if args.doc:
        print("%d failed" % failed)
        return 0 if failed == 0 else 1

    names = [n for n, _d, _fn, _i in CASES]
    runtime_failed = 0
    for n in names:
        ok, why, exp = run_case(n)
        if ok:
            print("PASS %-28s %s" % (n, why))
        else:
            runtime_failed += 1
            print("FAIL %-28s %s (exp=%r)" % (n, why, exp))
    failed += runtime_failed
    print("%d/%d runtime passed" % (len(names) - runtime_failed, len(names)))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
