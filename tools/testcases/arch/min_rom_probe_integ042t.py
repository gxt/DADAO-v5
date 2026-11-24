#!/usr/bin/env python3
"""Min ROM probe for INTEG-042t: cfx_pmem 64 KiB SRAM + SRAM<->PA DMA (Step 4).

Expectations are derived by hand from the frozen spec + ADRs, never from the
QEMU implementation:
  - spec/DADAO-12 §2.1 (cfx_pmem 64 KiB SRAM at internal offset 0x3ff_0000_0000; reserved
    cfx 6-14/16-31/35-61 => CFXMEM), §4.9 (cg15 DMA registers dma_src/dma_dst/
    dma_size/dma_ctrl/dma_status, direction, 42/56-bit masking, 30-bit size
    1..2^29, START self-clear, BUSY/DONE(W1C)/ERROR(W1C)/ERR_CODE one-hot,
    PMEM_DMA = 1 << 8 maskable), §3.6 (1<<8 owned by cfx_pmem),
    §5.4 (ADR-0061 R2: every async source is delivered to cfx_hart through
    its cg9 capture buffer; the source identity is the source cfxha 32 and the
    source mask is the running mode monitor's cg8 rc1).
  - .tao/adr/adr-0042-cfx-internal-dma.md D3/D4/D6/D7.1-D7.4.
  - spec/Kaiwu-测试机运行环境.md §1.1 (SRAM window 0x83ff_0000_0000)
    and §3 (DMA may read RAM/boot ROM, may write RAM only).
  - contracts/cfx-aliases.txt (cfx_pmem = cfx32, cfx_cache = cfx5).

Out of scope (documented as deferred): multi-hart PMEM_DMA receiver rules,
device-local DMA, cfx access permissions (Step 6), fence.vma/fence.i.

Observation channels (same convention as min_rom_probe_034t..integ040t):
  * register results -> QEMU `-d cpu` dump (last dump block);
  * fault cause -> the target cfx's cause id/info copied to rd10/rd11 by the
    probe handler; async capture/pending -> cfx_hart cg9 rc3/rc4, copied to
    RAM by the probe's cg9 handler (ADR-0061 R2: PMEM_DMA never enters
    cfx_pmem and never uses cfx_pmem's cg5);
  * pass/fail -> semihosting SYS_EXIT (ADR-0020 D8).

Usage:
  min_rom_probe_integ042t.py                 # run all checks
  min_rom_probe_integ042t.py --only NAME     # run one check (run.sh --inject)
  min_rom_probe_integ042t.py --list
  min_rom_probe_integ042t.py --qemu PATH

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import re
import struct
import subprocess
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

DEFAULT_QEMU = _prelude.default_qemu()
QEMU = DEFAULT_QEMU
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_integ042t")
TIMEOUT = 20

# TESTCASES-093t: the body runs at RESET_PC + 0x1000 inside the
# 4 MiB bootrom-image, after the shared power -> hmon identity-PTW prelude.
ROM_BASE = _prelude.ROM_BASE
RAM_BASE = _MACH.ram_base
RAM_SIZE = _MACH["ram_size"]

# cfxha / internal address space (DADAO-12 §2.1, Machine-01 §1.1)
PMEM_HA = 32
PMEM_BASE = 0x83ff_0000_0000          # cfx32, SRAM internal offset 0x3ff_0000_0000
PMEM_SRAM_CFX_OFFSET = 0x3ff_0000_0000
PMEM_OLD_BASE = PMEM_HA << 42         # 0x0000_8000_0000_0000 (offset 0, now invalid)
PMEM_SRAM_SIZE = 64 * 1024
assert PMEM_BASE == (PMEM_HA << 42) | PMEM_SRAM_CFX_OFFSET
CACHE_HA = 5
RESERVED_HA = 6
RESERVED_BASE = RESERVED_HA << 42    # 0x0000_1800_0000_0000

# cg15 DMA registers (DADAO-12 §4.9)
PMEM_DMA_CG = 15
DMA_SRC_RC, DMA_DST_RC, DMA_SIZE_RC, DMA_CTRL_RC, DMA_STATUS_RC = 0, 1, 2, 3, 4
DMA_RESERVED_RC = 5

# dma_ctrl / dma_status bits (DADAO-12 §4.9)
CTRL_START = 1 << 0
CTRL_DIR = 1 << 1                  # 0 = CFX->PA, 1 = PA->CFX
CTRL_IRQ_EN = 1 << 2
ST_BUSY = 1 << 0
ST_DONE = 1 << 1
ST_ERROR = 1 << 2
ERR_SIZE = 1 << 3                  # ERR_CODE one-hot at status[15:3]
ERR_CFX_RANGE = 1 << 4
ERR_PA_RANGE = 1 << 5
ERR_PA_FAULT = 1 << 6

# cfx exception cause ids / register coordinates
CAUSE_CFXREG = 1 << 2
CAUSE_CFXMEM = 1 << 1

# `excp_cause_id` fields (contract-see §6.1/§6.1.1; ADR-0056 D3): [15:0]
# one-hot big class, [63:48] CFXMEM sub-cause, [47:32] CFXPERM sub-cause,
# [31:16] reserved.  Every CFXMEM here is a non-page-table fault => [57].
CAUSE_LOW16 = 0xFFFF
CAUSE_WYDES = 0xFFFF_FFFF_0000_0000
CAUSE_RESERVED_31_16 = 0xFFFF_0000
NONPTW = 1 << 57


def cause_id_expect(cls, sub=0):
    """[(mask, expected)] over the three fields of `excp_cause_id`."""
    return [(CAUSE_LOW16, cls), (CAUSE_WYDES, sub), (CAUSE_RESERVED_31_16, 0)]
CG5_CAUSE_ID_RC, CG5_CAUSE_INFO_RC, CG5_CAUSE_IP_RC = 2, 4, 3
CG3_SWITCH_MODE_RC, CG3_EXCP_VECTOR_RC = 8, 10
CG3_DELEG_RC = 12
# cfx_hart cg9 (ADR-0061 D7): capture buffer slots.
RC_PREV_MODE, RC_PREV_CFX, RC_CAUSE_IP = 0, 1, 2
RC_FRAME, RC_PENDING, RC_VECTOR, RC_SWITCH = 3, 4, 5, 6
CG4_ASYNC_NUM_RC = 4
HART_HA = 15
SMON_HA = 2
MON_CG, MON_MASK_RC = 8, 1
INTR_SRC_PMEM = 1 << PMEM_HA          # async mask bit = source cfxha (32)
DELEG_OPEN = 0x8
MODE_H = 3

EXIT_PASS = 0x00

# Faulting IP of the next appended word (the instruction that will fault).
def fault_at(p):
    return ROM_BASE + 4 * len(p)

# Data addresses inside RAM
DATA_A = RAM_BASE + 0x1000
DATA_B = RAM_BASE + 0x2000
DATA_C = RAM_BASE + 0x3000

OFF_PMEM_HANDLER = 0x800
OFF_HMON_HANDLER = 0x900
PMEM_HANDLER = ROM_BASE + OFF_PMEM_HANDLER
HMON_HANDLER = ROM_BASE + OFF_HMON_HANDLER

SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = EXIT_BLOCK

MAGIC = 0x1122_3344_5566_7788
MAGIC2 = 0x99AA_BBCC_DDEE_FF00
MAGIC3 = 0x0F1E_2D3C_4B5A_6978


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


def br_eq(rdha, rdhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return _orrr(0x6E, rdha, rdhb, hc, hd)


def br_z(rdha, imms18):   return (0x6A << 24) | (rdha << 18) | (imms18 & 0x3FFFF)
def br_nz(rdha, imms18):  return (0x6B << 24) | (rdha << 18) | (imms18 & 0x3FFFF)
def br_nn(rdha, imms18):  return (0x69 << 24) | (rdha << 18) | (imms18 & 0x3FFFF)
def add_si(rd, imms18):   return (0x59 << 24) | (rd << 18) | (imms18 & 0x3FFFF)
def cmp_uo(rdhb, rdhc, rdhd): return _orrr(0x40, 0x2A, rdhb, rdhc, rdhd)


def br_ne(rdha, rdhb, imms12):
    imm = imms12 & 0xFFF
    hc = (imm >> 6) & 0x3F
    hd = imm & 0x3F
    if imms12 < 0:
        hc |= 0x20
    return _orrr(0x6F, rdha, rdhb, hc, hd)


def load_rd(rd, val):
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rd(rd, wp, x))
    return out


def load_rb(rb, val):
    out = [set_zw_rb(rb, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rb(rb, wp, x))
    return out


def exit_seq(code):
    """Semihosting SYS_EXIT with the profile `exit_block` (TESTCASES-093t §2)."""
    return _prelude.exit_seq(code)

# ---------------------------------------------------------------------------
# Program-building helpers.  Scratch: rd17 (register writes), rd18 (poll mask),
# rb3/rb4 (addresses); observation registers rd5-rd12 stay untouched.
# ---------------------------------------------------------------------------

def _e(p, *ws):
    """Append words to a plain list **or** to a `_prelude.Seq` label builder."""
    if isinstance(p, list):
        p.extend(ws)
    else:
        p.e(*ws)


def _len(p):
    return len(p) if isinstance(p, list) else len(p.w)


def store64(p, addr, value, rb=3, rd=17):
    _e(p, *load_rb(rb, addr))
    _e(p, *load_rd(rd, value))
    _e(p, st_o(rd, rb, 0))


def load64(p, addr, rd=6, rb=4):
    _e(p, *load_rb(rb, addr))
    _e(p, ld_o(rd, rb, 0))


def pmem_w(p, rc, val):
    _e(p, *load_rd(17, val))
    _e(p, cfx2rc(PMEM_HA, PMEM_DMA_CG, rc, 17))


def pmem_r(p, rc, rd):
    _e(p, cfx2rd(PMEM_HA, PMEM_DMA_CG, rc, rd))


def dma_setup(p, src, dst, size, ctrl):
    pmem_w(p, DMA_SRC_RC, src)
    pmem_w(p, DMA_DST_RC, dst)
    pmem_w(p, DMA_SIZE_RC, size)
    pmem_w(p, DMA_CTRL_RC, ctrl)


def dma_start(p, src, dst, size, irq_en=False):
    dma_setup(p, src, dst, size, CTRL_START | (CTRL_IRQ_EN if irq_en else 0))


def dma_start_pa_to_cfx(p, src, dst, size, irq_en=False):
    dma_setup(p, src, dst, size,
              CTRL_START | CTRL_DIR | (CTRL_IRQ_EN if irq_en else 0))


def status_clear(p):
    pmem_w(p, DMA_STATUS_RC, ST_DONE | ST_ERROR)


def poll_busy_clear(p, rd=5):
    """Spin until dma_status.BUSY is 0 (rd18 must hold 1)."""
    _e(p, *load_rd(18, 1))
    start = _len(p)
    pmem_r(p, DMA_STATUS_RC, rd)
    _e(p, and_o(rd, rd, 18))
    idx = _len(p)
    _e(p, br_ne(rd, 0, start - idx))


PMEM_CFXREG_HANDLER = ([cfx2rd(PMEM_HA, 5, CG5_CAUSE_ID_RC, 10),
                        cfx2rd(PMEM_HA, 5, CG5_CAUSE_INFO_RC, 11)]
                       + exit_seq(EXIT_PASS))

HMON_CFXREG_HANDLER = ([cfx2rd(3, 5, CG5_CAUSE_ID_RC, 10),
                        cfx2rd(3, 5, CG5_CAUSE_INFO_RC, 11)]
                       + exit_seq(EXIT_PASS))

# Execution-time sync fault in hypv => cfx_hmon frame (DADAO-12 §5.2 steps
# 1-7): record cause id / cause_info / cause_ip, then leave through SYS_EXIT.
HMON_FRAME_HANDLER = ([cfx2rd(3, 5, CG5_CAUSE_ID_RC, 10),
                       cfx2rd(3, 5, CG5_CAUSE_INFO_RC, 11),
                       cfx2rd(3, 5, CG5_CAUSE_IP_RC, 12)]
                      + exit_seq(EXIT_PASS))


def setup_pmem_vector(p, handler):
    p += load_rd(17, MODE_H)
    p.append(cfx2rc(PMEM_HA, MODE_H, CG3_SWITCH_MODE_RC, 17))
    p += load_rd(17, handler)
    p.append(cfx2rc(PMEM_HA, MODE_H, CG3_EXCP_VECTOR_RC, 17))


def setup_hmon_vector(p, handler):
    p += load_rd(17, MODE_H)
    p.append(cfx2rc(3, MODE_H, CG3_SWITCH_MODE_RC, 17))
    p += load_rd(17, handler)
    p.append(cfx2rc(3, MODE_H, CG3_EXCP_VECTOR_RC, 17))


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers=None, words_at=None, hmon_extra=None):
    """Shared prelude: body at RESET_PC + 0x1000 in the 4 MiB ROM image."""
    return _prelude.build_rom(prog, handlers, words_at, hmon_extra=hmon_extra)

# ---------------------------------------------------------------------------
# QEMU runner + dump parsing
# ---------------------------------------------------------------------------

def run(rom):
    """4 MiB `bootrom-image`, no `-kernel`; returns (rc, cpu_log, stderr)."""
    rc, log = _prelude.run(rom, WORKDIR, qemu=QEMU, timeout=TIMEOUT)
    return rc, log, ""

def lasthex(log, pat):
    m = None
    for x in re.finditer(pat, log):
        m = x
    return int(m.group(1), 16) if m else None


def observe(log):
    o = {}
    for n in (5, 6, 7, 8, 9, 10, 11, 12):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    o["pend32"] = lasthex(log, r"CFX32 PREVM:[^\n]* PEND:([0-9a-f]+)")
    o["cid32"] = lasthex(log, r"CFX32 PREVM:[^\n]* CID:([0-9a-f]+)")
    o["asyncn32"] = lasthex(log, r"CFX32 ID:[^\n]* ASYNCN:([0-9a-f]+)")
    return o


# ---------------------------------------------------------------------------
# Case model + builders
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def fill_sram(p, off, value=MAGIC, rd=17):
    """Write `value` into the cfx_pmem SRAM at internal offset `off`."""
    _e(p, *load_rb(3, PMEM_BASE + off))
    _e(p, *load_rd(rd, value))
    _e(p, st_o(rd, 3, 0))


# -- CPU direct SRAM access ------------------------------------------------
@case("sram_ldst_roundtrip", "CPU ld/st the 64 KiB SRAM at the new base 0x83ff_0000_0000")
def _sram_ldst_roundtrip():
    p = []
    fill_sram(p, 0x0000, MAGIC)
    fill_sram(p, 0xFFF8, MAGIC2)
    load64(p, PMEM_BASE + 0x0000, rd=5)
    load64(p, PMEM_BASE + 0xFFF8, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC2}


@case("sram_oob_cfxmem", "SRAM offset >= 64 KiB => CFXMEM (monitor)")
def _sram_oob_cfxmem():
    p = []
    setup_hmon_vector(p, HMON_HANDLER)
    p += load_rb(3, PMEM_BASE + PMEM_SRAM_SIZE)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0x7E)
    return build_rom(p, {OFF_HMON_HANDLER: HMON_FRAME_HANDLER}), \
        {"exit": EXIT_PASS, "rd10": cause_id_expect(CAUSE_CFXMEM, NONPTW),
         "rd11": PMEM_BASE + PMEM_SRAM_SIZE, "rd12": ip}


@case("sram_old_offset_cfxmem", "internal offset 0 (old base) is outside the SRAM")
def _sram_old_offset_cfxmem():
    p = []
    setup_hmon_vector(p, HMON_HANDLER)
    p += load_rb(3, PMEM_OLD_BASE)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0x7E)
    return build_rom(p, {OFF_HMON_HANDLER: HMON_FRAME_HANDLER}), \
        {"exit": EXIT_PASS, "rd10": cause_id_expect(CAUSE_CFXMEM, NONPTW), "rd11": PMEM_OLD_BASE,
         "rd12": ip}


# -- DMA both directions ---------------------------------------------------
@case("dma_cfx_to_pa", "DMA CFX->PA copies SRAM to physical memory")
def _dma_cfx_to_pa():
    p = []
    fill_sram(p, 0x0100, MAGIC)
    store64(p, DATA_A, 0, rb=3, rd=4)       # clear the destination
    status_clear(p)
    dma_start(p, PMEM_BASE + 0x0100, DATA_A, 8)
    poll_busy_clear(p)
    pmem_r(p, DMA_STATUS_RC, 6)
    load64(p, DATA_A, rd=7)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_DONE, "rd7": MAGIC}


@case("dma_pa_to_cfx", "DMA PA->CFX copies physical memory into SRAM")
def _dma_pa_to_cfx():
    p = []
    store64(p, DATA_A, MAGIC2)
    fill_sram(p, 0x0200, 0)
    status_clear(p)
    dma_start_pa_to_cfx(p, DATA_A, PMEM_BASE + 0x0200, 8)
    poll_busy_clear(p)
    pmem_r(p, DMA_STATUS_RC, 6)
    load64(p, PMEM_BASE + 0x0200, rd=7)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_DONE, "rd7": MAGIC2}


@case("dma_high_bits_ignored", "CFX low42 / PA low56 are used; high bits ignored")
def _dma_high_bits_ignored():
    p = []
    fill_sram(p, 0x0080, MAGIC3)
    status_clear(p)
    src = 0xABCD_0000_0000_0000 | (PMEM_BASE + 0x80)     # bits[63:42] set
    dst = 0xFF00_0000_0000_0000 | DATA_B                 # bits[63:56] set
    dma_start(p, src, dst, 8)
    poll_busy_clear(p)
    pmem_r(p, DMA_STATUS_RC, 6)
    load64(p, DATA_B, rd=7)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_DONE, "rd7": MAGIC3}


# -- size / address boundaries --------------------------------------------
@case("dma_size_64k_ok", "size = 64 KiB from SRAM offset 0 is legal")
def _dma_size_64k_ok():
    p = []
    fill_sram(p, 0x0000, MAGIC)
    fill_sram(p, 0xFFF8, MAGIC2)
    status_clear(p)
    dma_start(p, PMEM_BASE, RAM_BASE + 0x100000, PMEM_SRAM_SIZE)
    poll_busy_clear(p)
    pmem_r(p, DMA_STATUS_RC, 6)
    load64(p, RAM_BASE + 0x100000, rd=7)
    load64(p, RAM_BASE + 0x100000 + 0xFFF8, rd=8)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_DONE, "rd7": MAGIC,
                          "rd8": MAGIC2}


@case("dma_cfx_range_end_ok", "SRAM offset 0xFFF8 + 8 = 64 KiB is legal")
def _dma_cfx_range_end_ok():
    p = []
    fill_sram(p, 0xFFF8, MAGIC3)
    status_clear(p)
    dma_start(p, PMEM_BASE + 0xFFF8, DATA_C, 8)
    poll_busy_clear(p)
    pmem_r(p, DMA_STATUS_RC, 6)
    load64(p, DATA_C, rd=7)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_DONE, "rd7": MAGIC3}


@case("dma_cfx_range_overflow", "SRAM offset 0xFFFC + 8 exceeds 64 KiB")
def _dma_cfx_range_overflow():
    p = []
    store64(p, DATA_C, MAGIC)
    status_clear(p)
    dma_start(p, PMEM_BASE + 0xFFFC, DATA_C, 8)
    pmem_r(p, DMA_STATUS_RC, 5)
    load64(p, DATA_C, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_CFX_RANGE,
                          "rd6": MAGIC}


@case("dma_cfx_below_offset", "DMA CFX addr below 0x3ff_0000_0000 => CFX_RANGE")
def _dma_cfx_below_offset():
    p = []
    store64(p, DATA_A, MAGIC)
    status_clear(p)
    dma_start(p, PMEM_OLD_BASE, DATA_A, 8)
    pmem_r(p, DMA_STATUS_RC, 5)
    load64(p, DATA_A, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_CFX_RANGE,
                          "rd6": MAGIC}


@case("dma_size_zero", "size = 0 => setup error SIZE, no transfer")
def _dma_size_zero():
    p = []
    store64(p, DATA_A, MAGIC)
    status_clear(p)
    dma_start(p, PMEM_BASE, DATA_A, 0)
    pmem_r(p, DMA_STATUS_RC, 5)
    load64(p, DATA_A, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_SIZE,
                          "rd6": MAGIC}


@case("dma_size_over_512mib", "size > 2^29 => setup error SIZE")
def _dma_size_over_512mib():
    p = []
    status_clear(p)
    dma_start(p, PMEM_BASE, DATA_A, (1 << 29) + 1)
    pmem_r(p, DMA_STATUS_RC, 5)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_SIZE}


@case("dma_size_512mib_cfx_range", "size = 2^29 is legal; SRAM range then fails")
def _dma_size_512mib_cfx_range():
    p = []
    status_clear(p)
    dma_start(p, PMEM_BASE, DATA_A, 1 << 29)
    pmem_r(p, DMA_STATUS_RC, 5)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_CFX_RANGE}


@case("dma_pa_range_overflow", "PA + size beyond 2^56 => PA_RANGE")
def _dma_pa_range_overflow():
    p = []
    status_clear(p)
    dma_start(p, PMEM_BASE, 0x00FF_FFFF_FFFF_F000, 0x2000)
    pmem_r(p, DMA_STATUS_RC, 5)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_PA_RANGE}


@case("dma_pa_write_rom", "DMA writing the read-only boot ROM => PA_FAULT")
def _dma_pa_write_rom():
    p = []
    status_clear(p)
    dma_start(p, PMEM_BASE, ROM_BASE + 0x1000, 8)
    pmem_r(p, DMA_STATUS_RC, 5)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_PA_FAULT}


@case("dma_pa_read_rom", "DMA may read the boot ROM (PA->CFX)")
def _dma_pa_read_rom():
    p = []
    status_clear(p)
    # First two words of the (bootstrapped) body.
    dma_start_pa_to_cfx(p, ROM_BASE, PMEM_BASE + 0x0300, 8)
    poll_busy_clear(p)
    pmem_r(p, DMA_STATUS_RC, 6)
    load64(p, PMEM_BASE + 0x0300, rd=7)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_DONE,
                          "rd7": ((p[0] & 0xFFFFFFFF) << 32) |
                                 (p[1] & 0xFFFFFFFF)}


@case("dma_busy_start_ignored", "START while BUSY is ignored (first transfer wins)")
def _dma_busy_start_ignored():
    p = []
    fill_sram(p, 0x0000, MAGIC)
    fill_sram(p, 0x0040, MAGIC2)
    store64(p, DATA_A, 0)
    store64(p, DATA_B, 0)
    status_clear(p)
    dma_start(p, PMEM_BASE, DATA_A, 8)
    pmem_r(p, DMA_STATUS_RC, 5)             # BUSY must be visible
    dma_start(p, PMEM_BASE + 0x40, DATA_B, 8)   # ignored: BUSY
    poll_busy_clear(p, rd=6)
    pmem_r(p, DMA_STATUS_RC, 7)
    load64(p, DATA_A, rd=8)
    load64(p, DATA_B, rd=12)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_BUSY, "rd7": ST_DONE,
                          "rd8": MAGIC, "rd12": 0}


# -- DONE / ERROR / ERR_CODE / W1C ----------------------------------------
@case("dma_done_w1c", "DONE is cleared by W1C only")
def _dma_done_w1c():
    p = []
    fill_sram(p, 0x0000, MAGIC)
    status_clear(p)
    dma_start(p, PMEM_BASE, DATA_A, 8)
    poll_busy_clear(p, rd=5)
    pmem_r(p, DMA_STATUS_RC, 6)             # DONE set
    pmem_w(p, DMA_STATUS_RC, ST_DONE)       # W1C
    pmem_r(p, DMA_STATUS_RC, 7)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_DONE, "rd7": 0}


@case("dma_error_w1c", "ERROR W1C also clears ERR_CODE")
def _dma_error_w1c():
    p = []
    status_clear(p)
    dma_start(p, PMEM_BASE, DATA_A, 0)      # SIZE error
    pmem_r(p, DMA_STATUS_RC, 5)
    pmem_w(p, DMA_STATUS_RC, ST_ERROR)      # W1C
    pmem_r(p, DMA_STATUS_RC, 6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": ST_ERROR | ERR_SIZE,
                          "rd6": 0}


@case("dma_busy_w1c_ignored", "DONE W1C is ignored while BUSY")
def _dma_busy_w1c_ignored():
    p = []
    fill_sram(p, 0x0000, MAGIC)
    fill_sram(p, 0x0040, MAGIC2)
    status_clear(p)
    dma_start(p, PMEM_BASE, DATA_A, 8)
    poll_busy_clear(p, rd=5)                # DONE=1, left sticky
    dma_start(p, PMEM_BASE + 0x40, DATA_B, 8)   # BUSY=1, DONE still 1
    pmem_r(p, DMA_STATUS_RC, 6)             # BUSY|DONE
    pmem_w(p, DMA_STATUS_RC, ST_DONE)       # ignored while BUSY
    pmem_r(p, DMA_STATUS_RC, 7)             # still BUSY|DONE (W1C ignored)
    poll_busy_clear(p, rd=8)
    pmem_r(p, DMA_STATUS_RC, 9)             # DONE sticky through completion
    pmem_w(p, DMA_STATUS_RC, ST_DONE)
    pmem_r(p, DMA_STATUS_RC, 12)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": ST_BUSY | ST_DONE,
                          "rd7": ST_BUSY | ST_DONE, "rd9": ST_DONE,
                          "rd12": 0}


# -- PMEM_DMA async capture (ADR-0061 R2) --------------------------------
#
# Every async source is delivered to cfx_hart (cfxha 15) through its supv
# single vector `cg9 rc5`; the source identity is the source cfxha (32) and
# the capture/pending bitmaps are `cg9 rc3`/`rc4` (HW/RO).  The only source
# mask is the *running mode* monitor's `cg8 rc1` (the body runs in hypv, so
# cfx_hmon owns it); PMEM_DMA never enters cfx_pmem and cfx_pmem's cg5 is not
# involved.  cg9 is a capture buffer: the probe's handler copies it to RAM and
# returns through cfx_smon (ADR-0061 D4).
ALL1 = (1 << 64) - 1
RAM_ASTATE = RAM_BASE + 0x500
RAM_A_FRAME = 0x00
RAM_A_PENDING = 0x08
RAM_A_IP = 0x10
RAM_A_PREVM = 0x18
RAM_A_PREVC = 0x20
RAM_A_SEQ = 0x28
RAM_A_HANDOFF = 0x30

OFF_ASYNC_HND = 0xC00
OFF_SMON_HND = 0xC80
OFF_POISON = 0xD00

MAX_WAIT = 4_000_000


def build_async_handler():
    """cfx_hart cg9 rc5 (supv): copy the capture to RAM, hand off to smon."""
    a = _prelude.Seq()
    a.e(cfx2rd(HART_HA, 9, RC_FRAME, 30))
    a.e(cfx2rd(HART_HA, 9, RC_PENDING, 31))
    a.e(cfx2rd(HART_HA, 9, RC_CAUSE_IP, 32))
    a.e(cfx2rd(HART_HA, 9, RC_PREV_MODE, 33))
    a.e(cfx2rd(HART_HA, 9, RC_PREV_CFX, 34))
    a.e(ld_o(36, 5, RAM_A_SEQ))
    a.e(add_si(36, 1))
    a.e(st_o(36, 5, RAM_A_SEQ))
    a.e(st_o(30, 5, RAM_A_FRAME))
    a.e(st_o(31, 5, RAM_A_PENDING))
    a.e(st_o(32, 5, RAM_A_IP))
    a.e(st_o(33, 5, RAM_A_PREVM))
    a.e(st_o(34, 5, RAM_A_PREVC))
    a.e(*load_rd(36, 1))
    a.e(st_o(36, 5, RAM_A_HANDOFF))
    a.e(trap(SMON_HA, 0))                   # cfx_smon supv vector
    a.e(*exit_seq(0x6F))                    # unreachable on a correct return
    return a.resolve()


def build_smon_handler():
    """cfx_smon supv vector: rebuild cg5 from the capture, escape to cause_ip."""
    a = _prelude.Seq()
    a.e(ld_o(30, 5, RAM_A_HANDOFF))
    a.b("z", 30, "sync")
    a.e(ld_o(30, 5, RAM_A_PREVM))
    a.e(cfx2rc(SMON_HA, 5, 0, 30))
    a.e(ld_o(30, 5, RAM_A_PREVC))
    a.e(cfx2rc(SMON_HA, 5, 1, 30))
    a.e(ld_o(30, 5, RAM_A_IP))
    a.e(cfx2rc(SMON_HA, 5, 3, 30))
    a.e(*load_rd(30, 0))
    a.e(st_o(30, 5, RAM_A_HANDOFF))
    a.e(escape(SMON_HA, 0))                 # cg5 frame, offset 0
    a.e(*exit_seq(0x7F))                    # unreachable: escape switches away
    a.mark("sync")
    a.e(cfx2rd(SMON_HA, 5, CG5_CAUSE_ID_RC, 30))
    a.e(st_o(30, 5, RAM_A_IP))             # unexpected sync cause (diagnostic)
    a.e(escape(SMON_HA, 1))
    return a.resolve()


def build_poison():
    a = _prelude.Seq()
    a.e(*exit_seq(0x7E))
    return a.resolve()


ASYNC_HANDLERS = {
    OFF_ASYNC_HND: build_async_handler(),
    OFF_SMON_HND: build_smon_handler(),
    OFF_POISON: build_poison(),
}


def async_hmon_setup():
    """hmon-mode setup for the async cases: supv hand-off plumbing only.

    The async source mask (`cfx_hmon cg8 rc1`) is left at reset (all-1); each
    case opens/closes bit 32 through `mask_pmem_dma`.
    """
    ins = load_rb(5, RAM_ASTATE)
    ins += load_rd(17, DELEG_OPEN)
    ins += [cfx2rc(HART_HA, 3, CG3_DELEG_RC, 17),
            cfx2rc(SMON_HA, 3, CG3_DELEG_RC, 17)]
    # Let supv `trap cfx_smon` through: cfx_smon's supv cfxtrap mask bit 15
    # (source cfxha = cfx_hart) = 0.  (Not the PMEM source bit: the hand-off
    # must be a clean CFXTRAP, not a CFXPERM fallback.)
    ins += load_rd(17, ALL1 & ~(1 << HART_HA))
    ins += [cfx2rc(SMON_HA, 2, 0, 17)]
    ins += load_rd(17, ROM_BASE + OFF_SMON_HND)
    ins += [cfx2rc(SMON_HA, 2, CG3_EXCP_VECTOR_RC, 17)]
    ins += load_rd(17, ROM_BASE + OFF_ASYNC_HND)
    ins += [cfx2rc(HART_HA, 9, RC_VECTOR, 17)]
    ins += load_rd(17, 2)
    ins += [cfx2rc(HART_HA, 9, RC_SWITCH, 17)]
    ins += load_rd(17, ROM_BASE + OFF_POISON)
    ins += [cfx2rc(3, 3, CG3_EXCP_VECTOR_RC, 17)]
    return ins


def mask_pmem_dma(a, mask=INTR_SRC_PMEM):
    """Write the running mode monitor's async source mask (1 = masked)."""
    a.e(*load_rd(17, mask))
    a.e(cfx2rc(3, MON_CG, MON_MASK_RC, 17))


def need_eq(a, rd, want, code, tag):
    ok = "eq_%s_%d" % (tag, _len(a))
    a.e(*load_rd(19, want))
    a.b("eq", rd, ok, 19)
    a.e(*exit_seq(code))
    a.mark(ok)


def need_mask_set(a, rd, mask, code, tag):
    ok = "ms_%s_%d" % (tag, _len(a))
    a.e(*load_rd(19, mask))
    a.e(and_o(18, rd, 19))
    a.b("nz", 18, ok)
    a.e(*exit_seq(code))
    a.mark(ok)


def need_mask_clr(a, rd, mask, code, tag):
    ok = "mc_%s_%d" % (tag, _len(a))
    a.e(*load_rd(19, mask))
    a.e(and_o(18, rd, 19))
    a.b("z", 18, ok)
    a.e(*exit_seq(code))
    a.mark(ok)


def ram_ld(a, off, rd):
    a.e(ld_o(rd, 5, off))


def wait_ram(a, off, want, code, tag):
    head = "w_%s" % tag
    done = head + "_ok"
    a.e(*load_rd(20, MAX_WAIT))
    a.mark(head)
    a.e(ld_o(18, 5, off))
    a.e(*load_rd(19, want))
    a.b("eq", 18, done, 19)
    a.e(add_si(20, -1))
    a.b("nz", 20, head)
    a.e(*exit_seq(code))
    a.mark(done)


def wait_pending(a, mask, want_set, code, tag):
    head = "p_%s" % tag
    done = head + "_ok"
    a.e(*load_rd(20, MAX_WAIT))
    a.mark(head)
    a.e(cfx2rd(HART_HA, 9, RC_PENDING, 18))
    a.e(*load_rd(19, mask))
    a.e(and_o(18, 18, 19))
    a.b("eq" if want_set else "z", 18, done, 19)
    a.e(add_si(20, -1))
    a.b("nz", 20, head)
    a.e(*exit_seq(code))
    a.mark(done)


def delay_loop(a, count, tag, rd=20):
    a.e(*load_rd(rd, count))
    head = "dl_%s_%d" % (tag, _len(a))
    tail = head + "_end"
    a.mark(head)
    a.b("z", rd, tail)
    a.e(add_si(rd, -1))
    a.b("nz", rd, head)
    a.mark(tail)


def _build_async_case(fn):
    a = _prelude.Seq()
    fn(a)
    return build_rom(a.resolve(), ASYNC_HANDLERS, hmon_extra=async_hmon_setup())


@case("pmem_dma_capture",
      "PMEM_DMA enters cfx_hart once: cg9 capture bit32, source/monitor untouched")
def _pmem_dma_capture():
    def body(a):
        mask_pmem_dma(a, ALL1 & ~INTR_SRC_PMEM)   # open PMEM only
        fill_sram(a, 0x0000, MAGIC)
        status_clear(a)
        dma_start(a, PMEM_BASE, DATA_A, 8, irq_en=True)
        poll_busy_clear(a)
        wait_ram(a, RAM_A_SEQ, 1, 0x61, "cap")
        ram_ld(a, RAM_A_FRAME, 5)
        need_eq(a, 5, INTR_SRC_PMEM, 0x62, "frame")
        ram_ld(a, RAM_A_PENDING, 6)
        need_eq(a, 6, 0, 0x63, "pending_consumed")
        ram_ld(a, RAM_A_PREVM, 7)
        need_eq(a, 7, MODE_H, 0x64, "prev_mode")
        ram_ld(a, RAM_A_PREVC, 8)
        need_eq(a, 8, MODE_H, 0x65, "prev_cfx")
        ram_ld(a, RAM_A_IP, 9)
        a.e(*load_rd(19, 3))
        a.e(and_o(18, 9, 19))
        need_eq(a, 18, 0, 0x66, "ip_align")
        # Delivery target witness: cfx_pmem and the monitor never entered.
        a.e(cfx2rd(PMEM_HA, 4, CG4_ASYNC_NUM_RC, 10))
        need_eq(a, 10, 0, 0x67, "source_no_entry")
        a.e(cfx2rd(3, 4, CG4_ASYNC_NUM_RC, 11))
        need_eq(a, 11, 0, 0x68, "monitor_no_entry")
        a.e(cfx2rd(HART_HA, 4, CG4_ASYNC_NUM_RC, 12))
        need_eq(a, 12, 1, 0x69, "hart_entry")
        # The capture is a snapshot, kept after the software hand-off.
        a.e(cfx2rd(HART_HA, 9, RC_FRAME, 6))
        need_eq(a, 6, INTR_SRC_PMEM, 0x6A, "capture_kept")
        status_clear(a)                          # source ack (W1C)
        a.e(cfx2rd(HART_HA, 9, RC_PENDING, 7))
        a.e(*load_rd(19, INTR_SRC_PMEM))
        a.e(and_o(18, 7, 19))
        need_eq(a, 18, 0, 0x6B, "ack_no_pending")
        a.e(*exit_seq(EXIT_PASS))

    return _build_async_case(body), {"exit": EXIT_PASS}


@case("pmem_dma_masked_pending",
      "masked PMEM_DMA only sets cg9 rc4 bit32; opening the mask delivers it")
def _pmem_dma_masked_pending():
    def body(a):
        mask_pmem_dma(a, ALL1)                   # everything masked
        fill_sram(a, 0x0000, MAGIC)
        status_clear(a)
        dma_start(a, PMEM_BASE, DATA_A, 8, irq_en=True)
        poll_busy_clear(a)
        wait_pending(a, INTR_SRC_PMEM, True, 0x71, "mp")
        ram_ld(a, RAM_A_SEQ, 5)
        need_eq(a, 5, 0, 0x72, "no_entry")
        a.e(cfx2rd(HART_HA, 9, RC_FRAME, 6))
        need_eq(a, 6, 0, 0x73, "no_capture")
        a.e(cfx2rd(PMEM_HA, 4, CG4_ASYNC_NUM_RC, 7))
        need_eq(a, 7, 0, 0x74, "source_no_entry")
        mask_pmem_dma(a, 0)                      # release
        wait_ram(a, RAM_A_SEQ, 1, 0x75, "mpr")
        ram_ld(a, RAM_A_FRAME, 8)
        need_eq(a, 8, INTR_SRC_PMEM, 0x76, "frame")
        a.e(cfx2rd(HART_HA, 9, RC_PENDING, 9))
        a.e(*load_rd(19, INTR_SRC_PMEM))
        a.e(and_o(18, 9, 19))
        need_eq(a, 18, 0, 0x77, "pending_cleared")
        a.e(*exit_seq(EXIT_PASS))

    return _build_async_case(body), {"exit": EXIT_PASS}


@case("pmem_dma_ack_w1c",
      "dma_status W1C acks the source: cg9 pending drops, no stale delivery")
def _pmem_dma_ack_w1c():
    def body(a):
        mask_pmem_dma(a, ALL1)                   # keep PMEM masked
        fill_sram(a, 0x0000, MAGIC)
        status_clear(a)
        dma_start(a, PMEM_BASE, DATA_A, 8, irq_en=True)
        poll_busy_clear(a)
        wait_pending(a, INTR_SRC_PMEM, True, 0x81, "ack")
        status_clear(a)                          # W1C ack at the source
        a.e(cfx2rd(HART_HA, 9, RC_PENDING, 5))
        a.e(*load_rd(19, INTR_SRC_PMEM))
        a.e(and_o(18, 5, 19))
        need_eq(a, 18, 0, 0x82, "pending_drop")
        mask_pmem_dma(a, 0)                      # opening must not deliver
        delay_loop(a, 20000, "ackq")
        ram_ld(a, RAM_A_SEQ, 6)
        need_eq(a, 6, 0, 0x83, "no_stale")
        a.e(*exit_seq(EXIT_PASS))

    return _build_async_case(body), {"exit": EXIT_PASS}


# -- cfx numbering / aliases ---------------------------------------------
OFF_HMON_FAIL = 0x980                     # second hmon vector slot
HMON_FAIL = ROM_BASE + OFF_HMON_FAIL
# Any exception during the "legal commands" phase means a legal encoding was
# rejected: exit with a code the case does not expect.
LEGAL_PHASE_FAIL_HANDLER = exit_seq(0x19)


@case("cfx5_cache_noop",
      "cfx5 off: exist reads 0; legal cache_ctrl no-op; illegal encoding => CFXREG")
def _cfx5_cache_noop():
    # User ruling 2026-11-22 (discussing.md「M16 三方差分」cache 段): the cache
    # *model* decides whether cfx5 has effects, never whether it exists -- a
    # Linux kernel runs its cache maintenance unconditionally.  With the
    # default machine (cache-model=off) three things must hold:
    #   1. cache_exist (cg8 rc0) reads 0;
    #   2. every legal cache_ctrl encoding (selection I/D/both x operation
    #      none/clean/invalidate/flush x range all/PA line/PA span, with
    #      addr_size != 0 for the span) is accepted and completes silently;
    #   3. encoding validation is model-independent (CACHE-08/14): an illegal
    #      encoding still raises CFXREG with cause_info = the instruction word.
    # Failure modes are distinguishable: a legal command that raises exits
    # 0x19 (legal-phase handler), an illegal command that is accepted falls
    # through to exit 0x7E, and a wrong cause leaves a different rd10/rd11.
    p = []
    setup_hmon_vector(p, HMON_FAIL)         # legal phase: any fault => 0x19
    p.append(cfx2rd(CACHE_HA, 8, 0, 5))      # cache_exist => 0 with model off
    p += load_rd(17, 0x1000)                  # PA span needs size != 0
    p.append(cfx2rc(CACHE_HA, 8, 11, 17))     # cache_addr_size (cg8 rc11)
    for sel in (1, 2, 3):                     # bit15 = I, bit14 = D
        for op in (0, 1, 2, 3):               # none/clean/invalidate/flush
            for rng in (0, 1, 2):             # all / PA line / PA span
                p += load_rd(17, (sel << 14) | (rng << 2) | op)
                p.append(cfx2rc(CACHE_HA, 8, 9, 17))
    setup_hmon_vector(p, HMON_HANDLER)        # illegal phase: record cause
    p += load_rd(17, (3 << 14) | (3 << 2) | 1)  # [3:2] = 11 => illegal
    bad = cfx2rc(CACHE_HA, 8, 9, 17)
    p.append(bad)
    p += exit_seq(0x7E)                       # not reached: handler exits
    return build_rom(p, {OFF_HMON_HANDLER: HMON_CFXREG_HANDLER,
                         OFF_HMON_FAIL: LEGAL_PHASE_FAIL_HANDLER}), \
        {"exit": EXIT_PASS, "rd5": 0, "rd10": CAUSE_CFXREG, "rd11": bad}


@case("cfx6_reserved_cfxmem", "cfx6 is reserved: plain ld/st => CFXMEM")
def _cfx6_reserved_cfxmem():
    p = []
    setup_hmon_vector(p, HMON_HANDLER)
    p += load_rb(3, RESERVED_BASE)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0x7E)
    return build_rom(p, {OFF_HMON_HANDLER: HMON_FRAME_HANDLER}), \
        {"exit": EXIT_PASS, "rd10": cause_id_expect(CAUSE_CFXMEM, NONPTW), "rd11": RESERVED_BASE,
         "rd12": ip}


@case("pmem_cg15_reserved_cfxreg", "cg15 rc5 is reserved => CFXREG")
def _pmem_cg15_reserved_cfxreg():
    p = []
    # DADAO-12 §5.2: CFXREG goes to the current-mode monitor (cfx_hmon), not
    # to the accessed cfx_pmem; the monitor records the cause frame.
    setup_hmon_vector(p, HMON_HANDLER)
    p.append(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_RESERVED_RC, 5))
    p += exit_seq(0x7E)                    # not reached: the handler exits
    return build_rom(p, {OFF_HMON_HANDLER: HMON_CFXREG_HANDLER}), \
        {"exit": EXIT_PASS, "rd10": CAUSE_CFXREG, "rd5": 0}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_case(name):
    for n, d, fn in CASES:
        if n == name:
            rom, exp = fn()
            rc, log, err = run(rom)
            if rc is None:
                return False, "TIMEOUT", exp
            obs = observe(log)
            obs["exit"] = rc
            diffs = []
            for k, v in exp.items():
                av = obs.get(k)
                for mask, want in (v if isinstance(v, list) else [(None, v)]):
                    if mask is None:
                        ok = av == want
                        shown = "exp=0x%x" % want
                    else:
                        ok = av is not None and (av & mask) == want
                        shown = "exp(mask 0x%x)=0x%x" % (mask, want)
                    if not ok:
                        diffs.append("%s %s got=%s" % (
                            k, shown, ("0x%x" % av) if av is not None else "None"))
            if diffs:
                return False, "; ".join(diffs), exp
            return True, "ok", exp
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
        for n, d, _ in CASES:
            print("%-28s %s" % (n, d))
        return 0

    names = [args.only] if args.only else [n for n, _, _ in CASES]
    failed = 0
    for n in names:
        ok, why, exp = run_case(n)
        if ok:
            print("PASS %-28s %s" % (n, why))
        else:
            failed += 1
            print("FAIL %-28s %s (exp=%r)" % (n, why, exp))
    print("%d/%d passed" % (len(names) - failed, len(names)))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
