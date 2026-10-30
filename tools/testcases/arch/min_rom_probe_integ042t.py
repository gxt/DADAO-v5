#!/usr/bin/env python3
"""Min ROM probe for INTEG-042t: cfx_pmem 64 KiB SRAM + SRAM<->PA DMA (Step 4).

Expectations are derived by hand from the frozen spec + ADRs, never from the
QEMU implementation:
  - spec/DADAO-12 §2.1 (cfx_pmem 64 KiB SRAM at internal offset 0x3ff_0000_0000; reserved
    cfx 6-14/19-61 => CFXMEM), §4.9 (cg15 DMA registers dma_src/dma_dst/
    dma_size/dma_ctrl/dma_status, direction, 42/56-bit masking, 30-bit size
    1..2^29, START self-clear, BUSY/DONE(W1C)/ERROR(W1C)/ERR_CODE one-hot,
    PMEM_DMA = 1 << 8 maskable), §3.6 (1<<8 owned by cfx_pmem).
  - .tao/adr/adr-0042-cfx-internal-dma.md D3/D4/D6/D7.1-D7.4.
  - spec/Machine-01-测试机运行环境.md §1.1 (SRAM window 0x47ff_0000_0000)
    and §3 (DMA may read RAM/boot ROM, may write RAM only).
  - contracts/cfx-aliases.txt (cfx_pmem = cfx17, cfx_cache = cfx5).

Out of scope (documented as deferred): multi-hart PMEM_DMA receiver rules,
device-local DMA, cfx access permissions (Step 6), fence.vma/fence.i.

Observation channels (same convention as min_rom_probe_034t..integ040t):
  * register results -> QEMU `-d cpu` dump (last dump block);
  * fault cause -> the target cfx's cause id/info copied to rd10/rd11 by the
    probe handler; pending -> cfx_pmem_excp_pending (cg5 rc5);
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

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
QEMU = DEFAULT_QEMU
WORKDIR = "/tmp/opencode/INTEG-042t"
TIMEOUT = 20

ROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0xFC00_0000_0000
RAM_SIZE = 16 * 1024 * 1024

# cfxha / internal address space (DADAO-12 §2.1, Machine-01 §1.1)
PMEM_HA = 17
PMEM_BASE = 0x47ff_0000_0000          # cfx17, SRAM internal offset 0x3ff_0000_0000
PMEM_SRAM_CFX_OFFSET = 0x3ff_0000_0000
PMEM_OLD_BASE = PMEM_HA << 42         # 0x0000_4400_0000_0000 (offset 0, now invalid)
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
CAUSE_PMEM_DMA = 1 << 8
CG5_CAUSE_ID_RC, CG5_CAUSE_INFO_RC, CG5_PENDING_RC = 2, 4, 5
CG3_SWITCH_MODE_RC, CG3_EXCP_VECTOR_RC, CG3_EXCP_MASK_RC = 8, 10, 11
MODE_H = 3

EXIT_PASS = 0x00
EXIT_CFXMEM = 0x81

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
SEMI_BLOCK = 0xFC00_00FF_F000

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
    """Report `code` via semihosting SYS_EXIT -> host $? (ADR-0020 D8)."""
    return ([jump_iiii(1)]
            + load_rb(16, SEMI_BLOCK)
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


# ---------------------------------------------------------------------------
# Program-building helpers.  Scratch: rd17 (register writes), rd18 (poll mask),
# rb3/rb4 (addresses); observation registers rd5-rd12 stay untouched.
# ---------------------------------------------------------------------------

def store64(p, addr, value, rb=3, rd=17):
    p += load_rb(rb, addr)
    p += load_rd(rd, value)
    p.append(st_o(rd, rb, 0))


def load64(p, addr, rd=6, rb=4):
    p += load_rb(rb, addr)
    p.append(ld_o(rd, rb, 0))


def pmem_w(p, rc, val):
    p += load_rd(17, val)
    p.append(cfx2rc(PMEM_HA, PMEM_DMA_CG, rc, 17))


def pmem_r(p, rc, rd):
    p.append(cfx2rd(PMEM_HA, PMEM_DMA_CG, rc, rd))


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
    p += load_rd(18, 1)
    start = len(p)
    pmem_r(p, DMA_STATUS_RC, rd)
    p.append(and_o(rd, rd, 18))
    p.append(br_ne(rd, 0, start - len(p)))


PMEM_CFXREG_HANDLER = ([cfx2rd(PMEM_HA, 5, CG5_CAUSE_ID_RC, 10),
                        cfx2rd(PMEM_HA, 5, CG5_CAUSE_INFO_RC, 11)]
                       + exit_seq(EXIT_PASS))

HMON_CFXREG_HANDLER = ([cfx2rd(3, 5, CG5_CAUSE_ID_RC, 10),
                        cfx2rd(3, 5, CG5_CAUSE_INFO_RC, 11)]
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


def mask_pmem_dma(p, mask=CAUSE_PMEM_DMA):
    p += load_rd(17, mask)
    p.append(cfx2rc(PMEM_HA, MODE_H, CG3_EXCP_MASK_RC, 17))


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers=None, words_at=None):
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers or {}):
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(handlers[off])
    for off in sorted(words_at or {}):
        if len(rom) > off:
            raise ValueError("words_at offset overlaps the program/handlers")
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(words_at[off])
    while len(rom) < 0x500:
        rom += words_to_bytes([swym()])
    return bytes(rom)


# ---------------------------------------------------------------------------
# QEMU runner + dump parsing
# ---------------------------------------------------------------------------

def run(rom):
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
    o["pend17"] = lasthex(log, r"CFX17 PREVM:[^\n]* PEND:([0-9a-f]+)")
    o["cid17"] = lasthex(log, r"CFX17 PREVM:[^\n]* CID:([0-9a-f]+)")
    o["asyncn17"] = lasthex(log, r"CFX17 ID:[^\n]* ASYNCN:([0-9a-f]+)")
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
    p += load_rb(3, PMEM_BASE + off)
    p += load_rd(rd, value)
    p.append(st_o(rd, 3, 0))


# -- CPU direct SRAM access ------------------------------------------------
@case("sram_ldst_roundtrip", "CPU ld/st the 64 KiB SRAM at the new base 0x47ff_0000_0000")
def _sram_ldst_roundtrip():
    p = []
    fill_sram(p, 0x0000, MAGIC)
    fill_sram(p, 0xFFF8, MAGIC2)
    load64(p, PMEM_BASE + 0x0000, rd=5)
    load64(p, PMEM_BASE + 0xFFF8, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC2}


@case("sram_oob_cfxmem", "SRAM offset >= 64 KiB => CFXMEM (0x81)")
def _sram_oob_cfxmem():
    p = load_rb(3, PMEM_BASE + PMEM_SRAM_SIZE)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p), {"exit": EXIT_CFXMEM}


@case("sram_old_offset_cfxmem", "internal offset 0 (old base) is outside the SRAM")
def _sram_old_offset_cfxmem():
    p = load_rb(3, PMEM_OLD_BASE)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p), {"exit": EXIT_CFXMEM}


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
    # First word of the ROM is `jump_iiii(1)` (this program's own first word).
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


# -- PMEM_DMA async interrupt / masking ----------------------------------
#
# PMEM_DMA is maskable, and the reset inner_cfx_mask is all-ones, so an
# interrupt can only enter a cfx the hart is already executing in: the probe
# first enters cfx_pmem through a non-maskable CFXREG (a reserved cg15 rc),
# which switches inner_cfx_mask to cfx_pmem's hypv switch_cfx_mask (0) and
# makes cfx_pmem the current cfx.  From there the DMA completion is delivered
# to cfx_pmem itself (DADAO-12 §5.2 steps 3-5, §4.9).
def _make_irq_handler(spin=True):
    w = [cfx2rd(PMEM_HA, 5, CG5_CAUSE_ID_RC, 10),
         cfx2rd(PMEM_HA, 5, CG5_CAUSE_INFO_RC, 11)]
    w += load_rd(17, CAUSE_PMEM_DMA)
    br_idx = len(w)
    w.append(0)
    w += [set_zw_rd(5, 0, 1)]
    w += load_rd(17, ST_DONE)
    w += [cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 17)]
    w += exit_seq(EXIT_PASS)
    first = len(w)
    w[br_idx] = br_ne(10, 17, first - br_idx)
    w += load_rd(17, CTRL_START | CTRL_IRQ_EN)
    w += [cfx2rc(PMEM_HA, PMEM_DMA_CG, DMA_CTRL_RC, 17)]
    w += load_rd(18, 1)
    loop = len(w)
    w += [cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_STATUS_RC, 6)]
    w += [and_o(6, 6, 18)]
    w += [br_ne(6, 0, loop - len(w))]
    if spin:
        w += [jump_iiii(0)]
    else:
        w.append(cfx2rd(PMEM_HA, 5, CG5_PENDING_RC, 8))
        w += exit_seq(EXIT_PASS)
    return w


PMEM_IRQ_HANDLER = _make_irq_handler(spin=True)
PMEM_MASK_HANDLER = _make_irq_handler(spin=False)


def _enter_pmem_via_cfxreg(p):
    """Enter cfx_pmem with a non-maskable CFXREG (reserved cg15 rc); the
    handler takes over from there."""
    p.append(cfx2rd(PMEM_HA, PMEM_DMA_CG, DMA_RESERVED_RC, 5))


def _pmem_entry_setup(p, handler_addr, cause_mask):
    setup_pmem_vector(p, handler_addr)
    p += load_rd(17, cause_mask)
    p.append(cfx2rc(PMEM_HA, MODE_H, CG3_EXCP_MASK_RC, 17))
    p += load_rd(17, 0)                    # switch_cfx_mask = 0 (unmask on entry)
    p.append(cfx2rc(PMEM_HA, MODE_H, 9, 17))


@case("pmem_dma_irq_delivered", "IRQ_EN=1 delivers PMEM_DMA to cfx_pmem")
def _pmem_dma_irq_delivered():
    p = []
    _pmem_entry_setup(p, PMEM_HANDLER, cause_mask=0)
    fill_sram(p, 0x0000, MAGIC)
    status_clear(p)
    dma_setup(p, PMEM_BASE, DATA_A, 8, 0)  # latched, not started
    _enter_pmem_via_cfxreg(p)
    p += exit_seq(0xEE)                    # not reached: the handler exits
    return build_rom(p, {OFF_PMEM_HANDLER: PMEM_IRQ_HANDLER}), \
        {"exit": EXIT_PASS, "rd10": CAUSE_PMEM_DMA, "rd11": ST_DONE,
         "rd5": 1, "asyncn17": 1, "cid17": CAUSE_PMEM_DMA}


@case("pmem_dma_masked_pending", "masked PMEM_DMA only records cfx_pmem pending")
def _pmem_dma_masked_pending():
    p = []
    _pmem_entry_setup(p, PMEM_HANDLER, cause_mask=CAUSE_PMEM_DMA)
    fill_sram(p, 0x0000, MAGIC)
    status_clear(p)
    dma_setup(p, PMEM_BASE, DATA_A, 8, 0)
    _enter_pmem_via_cfxreg(p)
    p += exit_seq(0xEE)                    # not reached: the handler exits
    return build_rom(p, {OFF_PMEM_HANDLER: PMEM_MASK_HANDLER}), \
        {"exit": EXIT_PASS, "rd5": 0, "rd8": CAUSE_PMEM_DMA, "asyncn17": 0}


# -- cfx numbering / aliases ---------------------------------------------
@case("cfx5_cache_cfxreg", "cfx5 = cache is allocated but unimplemented => CFXREG")
def _cfx5_cache_cfxreg():
    p = []
    setup_hmon_vector(p, HMON_HANDLER)
    p.append(cfx2rd(CACHE_HA, 8, 0, 5))     # cfx_cache cg8 rc0
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_HMON_HANDLER: HMON_CFXREG_HANDLER}), \
        {"exit": EXIT_PASS, "rd10": CAUSE_CFXREG}


@case("cfx6_reserved_cfxmem", "cfx6 is reserved: plain ld/st => CFXMEM")
def _cfx6_reserved_cfxmem():
    p = load_rb(3, RESERVED_BASE)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p), {"exit": EXIT_CFXMEM}


@case("pmem_cg15_reserved_cfxreg", "cg15 rc5 is reserved => CFXREG in cfx_pmem")
def _pmem_cg15_reserved_cfxreg():
    p = []
    _pmem_entry_setup(p, PMEM_HANDLER, cause_mask=0)
    _enter_pmem_via_cfxreg(p)
    p += exit_seq(0xEE)                    # not reached: the handler exits
    return build_rom(p, {OFF_PMEM_HANDLER: PMEM_CFXREG_HANDLER}), \
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
