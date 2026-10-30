#!/usr/bin/env python3
"""Min ROM probe for INTEG-039t: address-space Step 2 (PTE / page walk / page
permissions).

Expectations are derived by hand from the frozen spec + ADRs, never from the
QEMU implementation:
  - spec/DADAO-12-SEE-主管系统运行环境.md §2.2.1–§2.2.6: 64-bit PTE fields
    (HSJU[63:60], PPN[55:16] / superpage PPN[55:29], SPF/GPF[15:8], flags
    [7:0] with P=0 SP=1 D=2 A=3 X=5 W=6 R=7), two-level tables (L1/L2 64 KiB,
    8192 entries, VA[41:29]/[28:16] indexes, VA[15:0] offset), 512 MiB
    superpage / 64 KiB page, PA 56 bits, HSJU rules, R/W/X orthogonal checks,
    exception priority P=0 → SPF/GPF → HSJU → R/W/X, page-table faults enter
    cfx_ptw, A/D fields defined but no update point without a TLB.
  - .tao/adr/adr-0040-pte-pagewalk-permissions.md D1–D10.
  - spec/Machine-01-测试机运行环境.md §1.2/§3 (test-machine scope: page tables
    live in pmem; A/D maintenance and TLB are later steps).
  - contracts/opcodes.yaml (ld.o/st.o/jump/set.zw/or.w/cfx2rd/cfx2rc/trap/
    escape encodings); contracts/cfx-aliases.txt (cfx_ptw = cfx4).

Out of scope here (Step 3+): TLB (CLEAN/FLUSH/INVALID), A/D write-back, DMA,
boot handoff, cfx access permissions and the Linux user/kernel split.

Observation channels (same convention as min_rom_probe_034t..049t):
  * register results -> QEMU `-d cpu` dump (last dump block);
  * fault cause -> cfx_ptw's cause id copied to rd10 by the probe handler
    (proves the fault entered cfx_ptw), cause info (faulting VA) -> rd11 and
    cause ip (precise faulting IP; the VA itself for fetch faults) -> rd12;
  * pass/fail -> semihosting SYS_EXIT (ADR-0020 D8).

Usage:
  min_rom_probe_integ039t.py                 # run all checks
  min_rom_probe_integ039t.py --only NAME     # run one check (used by run.sh)
  min_rom_probe_integ039t.py --list
  min_rom_probe_integ039t.py --qemu PATH

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
WORKDIR = "/tmp/opencode/INTEG-039t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0xFC00_0000_0000
RAM_SIZE = 16 * 1024 * 1024

# Exit codes (ADR-0004 D5.8 / Machine-01 §1.2): a page-table fault that reaches
# cfx_ptw is handled by the probe handler, so every case exits with SYS_EXIT 0.
EXIT_PASS = 0x00
EXIT_CFXMEM = 0x81

# cfx_ptw (cfx4) register coordinates (DADAO-12 §4.5)
PTW_HA = 4
PTW_ENABLE_CG, PTW_ENABLE_RC = 8, 8
PTBR_CG, PTBR_RC = 9, 0
CAUSE_ID_RC, CAUSE_INFO_RC, CAUSE_IP_RC = 2, 4, 3
SWITCH_MODE_RC, EXCP_VECTOR_RC = 8, 10

# Page-table physical layout (all 64 KiB aligned; PTBR/table pages live in pmem,
# i.e. the test-machine RAM segment).
PT_L1_PA = RAM_BASE + 0x00000
PT_L2_PA = RAM_BASE + 0x10000
PT_L2B_PA = RAM_BASE + 0x20000
DATA_PA = RAM_BASE + 0x400000          # 4 MiB into RAM
DATA2_PA = RAM_BASE + 0x500000         # 5 MiB into RAM
DATA3_PA = RAM_BASE + 0x600000         # 6 MiB into RAM (superpage offset)
# PTBR stores PPN[55:16] in place (DADAO-12 §2.2): value == page-table PA
# with [15:0] cleared, i.e. base = PTBR.
PTBR = PT_L1_PA & 0x00FF_FFFF_FFFF_0000

# Page-table fault handler (runs in cfx_ptw / hypv): copy the cause id and
# cause info, then leave via semihosting.  Its host exit code is always 0; the
# probe judges the (rd10, rd11) pair.
OFF_PTW_HANDLER = 0x300
# Per-mode handler used to execute an access in U/J/S mode (trap target's
# hypv switch_run_mode selects the mode; the handler escapes back to ROM).
OFF_MODE_HANDLER = 0x400
MODE_HANDLER = ROM_BASE + OFF_MODE_HANDLER
PTW_HANDLER = ROM_BASE + OFF_PTW_HANDLER

# HSJU is PTE[63:60]: H=bit63, S=bit62, J=bit61, U=bit60 (DADAO-12 §2.2.3),
# i.e. nibble bits H=3, S=2, J=1, U=0.
MODE_U, MODE_J, MODE_S, MODE_H = 0, 1, 2, 3
HSJU_ALL = 0xF
HSJU_OF_MODE = {MODE_U: 0x1, MODE_J: 0x2, MODE_S: 0x4, MODE_H: 0x8}

PTE_P = 1 << 0
PTE_SP = 1 << 1
PTE_D = 1 << 2
PTE_A = 1 << 3
PTE_X = 1 << 5
PTE_W = 1 << 6
PTE_R = 1 << 7
PPN_MASK = 0x00FF_FFFF_FFFF_0000
SPPN_MASK = 0x00FF_FFFF_E000_0000

# cfx_ptw cause ids (DADAO-12 §4.5)
C_NUPERM = 1 << 8
C_NJPERM = 1 << 9
C_NSPERM = 1 << 10
C_NHPERM = 1 << 11
C_NXPERM = 1 << 12
C_NWPERM = 1 << 13
C_NRPERM = 1 << 14
C_IGPTRAP = 1 << 16
C_ISPTRAP = 1 << 17
C_IGPFTRAP = 1 << 18
C_ISPFTRAP = 1 << 19
C_DGPTRAP = 1 << 20
C_DSPTRAP = 1 << 21
C_DGPFTRAP = 1 << 22
C_DSPFTRAP = 1 << 23

SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = 0xFC00_00FF_F000


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
def jump_rrii(rb, rd, off):  return _rrii(0x71, rb, rd, off)
def jump_iiii(imms24):       return (0x70 << 24) | (imms24 & 0xFFFFFF)
def cfx2rd(ha, cg, rc, rd):  return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def cfx2rc(ha, cg, rc, rd):  return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def trap(ha, immu18):        return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
def escape(ha, imms18):      return (0x7E << 24) | (ha << 18) | (imms18 & 0x3FFFF)
def swym():                  return 0x47880000


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
# Program-building helpers (rd17/rb3/rb4/rb5 are scratch; rd5/rd6/rd10/rd11
# are the observation registers and are never used as scratch)
# ---------------------------------------------------------------------------

def store64(p, addr, value, rb=3, rd=17):
    p += load_rb(rb, addr)
    p += load_rd(rd, value)
    p.append(st_o(rd, rb, 0))


def setup_ptbr(p, enable=True):
    p += load_rd(17, PTBR)
    p.append(cfx2rc(PTW_HA, PTBR_CG, PTBR_RC, 17))
    if enable:
        p += load_rd(17, 1)
        p.append(cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 17))


def setup_ptw_handler(p):
    """Route cfx_ptw faults to OFF_PTW_HANDLER from every run mode, and make
    cfx_ptw entry always switch to H-mode (so the handler can use cg5/cg3)."""
    for m in range(4):
        p += load_rd(17, MODE_H)
        p.append(cfx2rc(PTW_HA, m, SWITCH_MODE_RC, 17))
        p += load_rd(17, PTW_HANDLER)
        p.append(cfx2rc(PTW_HA, m, EXCP_VECTOR_RC, 17))


def setup_mode_handler(p, target_ha, mode):
    """trap target_ha (from H) enters MODE_HANDLER with inner_run_mode = mode."""
    p += load_rd(17, mode)
    p.append(cfx2rc(target_ha, MODE_H, SWITCH_MODE_RC, 17))
    p += load_rd(17, MODE_HANDLER)
    p.append(cfx2rc(target_ha, MODE_H, EXCP_VECTOR_RC, 17))


def pte(pa=0, hsju=HSJU_ALL, r=True, w=True, x=True, p=True, sp=False,
        frags=0xFF, a=False, d=False, reserved=0, bit4=False,
        ppn_override=None):
    val = (hsju & 0xF) << 60
    val |= (reserved & 0xF) << 56
    if ppn_override is not None:
        val |= ppn_override
    elif sp:
        val |= pa & SPPN_MASK
    else:
        val |= pa & PPN_MASK
    val |= (frags & 0xFF) << 8
    if r: val |= PTE_R
    if w: val |= PTE_W
    if x: val |= PTE_X
    if a: val |= PTE_A
    if d: val |= PTE_D
    if sp: val |= PTE_SP
    if p: val |= PTE_P
    if bit4: val |= 1 << 4
    return val


def install_l2_page(p, l1_idx=0, l2_idx=0, pa=DATA_PA, l2_pa=PT_L2_PA, **kw):
    store64(p, l2_pa + l2_idx * 8, pte(pa=pa, **kw))
    store64(p, PT_L1_PA + l1_idx * 8, pte(pa=l2_pa, p=True, sp=False))


def install_superpage(p, l1_idx=0, pa=RAM_BASE, **kw):
    store64(p, PT_L1_PA + l1_idx * 8, pte(pa=pa, sp=True, **kw))


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def code_bytes(words):
    return words_to_bytes(words)


def store_code(p, pa, words, rb=3, rd=17):
    """Write a list of instruction words to physical address `pa`."""
    data = words_to_bytes(words)
    for off in range(0, len(data), 8):
        chunk = data[off:off + 8].ljust(8, b"\x00")
        val = int.from_bytes(chunk, "big")
        store64(p, pa + off, val, rb=rb, rd=rd)


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
    for n in (5, 6, 10, 11, 12):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    o["ptbr"] = lasthex(log, r"PTBR: ([0-9a-f]+)")
    o["ptw_enable"] = lasthex(log, r"PTW_ENABLE: (\d+)")
    o["cid4"] = lasthex(log, r"CFX04 PREVM:[^\n]* CID:([0-9a-f]+)")
    o["syncn4"] = lasthex(log, r"CFX04 ID:[^\n]* SYNCN:([0-9a-f]+)")
    return o


# ---------------------------------------------------------------------------
# Case model + builders
# ---------------------------------------------------------------------------

CASES = []
MAGIC = 0x1122_3344_5566_7788
MAGIC2 = 0x99AA_BBCC_DDEE_FF00
MAGIC3 = 0x0F1E_2D3C_4B5A_6978


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


PTW_HANDLER_WORDS = ([cfx2rd(PTW_HA, 5, CAUSE_ID_RC, 10),
                      cfx2rd(PTW_HA, 5, CAUSE_INFO_RC, 11),
                      cfx2rd(PTW_HA, 5, CAUSE_IP_RC, 12)]
                     + exit_seq(EXIT_PASS))


def mode_handler(target_ha, rd=5):
    """L2 handler body: clear rd10, do the access, escape back to the trap PC+4."""
    return ([set_zw_rd(10, 0, 0)]
            + [ld_o(rd, 3, 0)]
            + [escape(target_ha, 1)])


def fault_at(p):
    """ROM address of the next appended instruction (the faulting one)."""
    return ROM_BASE + 4 * len(p)


def fault_expect(cause, va, ip, **extra):
    exp = {"exit": EXIT_PASS, "rd10": cause, "rd11": va, "rd12": ip,
           "syncn4": 1, "cid4": cause}
    exp.update(extra)
    return exp


# -- success: L1 next-level + L2 normal page --------------------------------
@case("l2_page_load", "L1 next-level + L2 page: VA[15:0] -> PA 56-bit load")
def _l2_page_load():
    p = []
    install_l2_page(p)
    store64(p, DATA_PA + 0x40, MAGIC)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_0000_0000 + 0x40)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC}


@case("l2_page_store", "L1 next-level + L2 page: store via VA lands at the PA")
def _l2_page_store():
    p = []
    install_l2_page(p)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_0000_0040)
    p += load_rd(4, MAGIC)
    p.append(st_o(4, 3, 0))
    p += load_rb(4, DATA_PA + 0x40)
    p.append(ld_o(6, 4, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": MAGIC}


@case("page_offset", "64 KiB page offset VA[15:0] kept in PA[15:0]")
def _page_offset():
    p = []
    install_l2_page(p, l2_idx=0, pa=DATA2_PA)
    off = 0x2340
    store64(p, DATA2_PA + off, MAGIC2)
    setup_ptbr(p)
    p += load_rb(3, off)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC2}


@case("l1_index_select", "VA[41:29] selects the L1 entry / L2 table")
def _l1_index_select():
    p = []
    install_l2_page(p, l1_idx=0, l2_idx=0, pa=DATA_PA, l2_pa=PT_L2_PA)
    install_l2_page(p, l1_idx=1, l2_idx=0, pa=DATA2_PA, l2_pa=PT_L2B_PA)
    store64(p, DATA_PA, MAGIC)
    store64(p, DATA2_PA, MAGIC2)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_0000_0000)
    p.append(ld_o(5, 3, 0))
    p += load_rb(3, 0x0000_2000_0000)
    p.append(ld_o(6, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC2}


@case("l2_index_select", "VA[28:16] selects the L2 entry")
def _l2_index_select():
    p = []
    store64(p, PT_L2_PA + 0 * 8, pte(pa=DATA_PA))
    store64(p, PT_L2_PA + 3 * 8, pte(pa=DATA2_PA))
    store64(p, PT_L1_PA, pte(pa=PT_L2_PA, p=True, sp=False))
    store64(p, DATA_PA, MAGIC)
    store64(p, DATA2_PA, MAGIC2)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_0000_0000)
    p.append(ld_o(5, 3, 0))
    p += load_rb(3, 0x0000_0003_0000)
    p.append(ld_o(6, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC2}


@case("superpage_load", "L1 superpage (SP=1): 512 MiB page, PPN[55:29]")
def _superpage_load():
    p = []
    off = 0x0065_4320
    install_superpage(p, l1_idx=1)
    store64(p, RAM_BASE + off, MAGIC3)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_2000_0000 + off)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC3}


@case("superpage_ppn_low_cleared", "superpage PPN[28:16] is forced to zero, no fault")
def _superpage_ppn_low_cleared():
    p = []
    off = 0x00A5_A5A0
    junk = 0x1FFF_0000  # PPN[28:16] non-zero
    store64(p, PT_L1_PA + 1 * 8,
            pte(pa=RAM_BASE, sp=True, ppn_override=(RAM_BASE & SPPN_MASK) | junk))
    store64(p, RAM_BASE + off, MAGIC3)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_2000_0000 + off)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC3}


@case("reserved_bits_ignored", "reserved [59:56] and bit4 are ignored")
def _reserved_bits_ignored():
    p = []
    install_l2_page(p, reserved=0xF, bit4=True)
    store64(p, DATA_PA, MAGIC)
    setup_ptbr(p)
    p += load_rb(3, 0)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC}


@case("fetch_translated", "instruction fetch through an X=1 page")
def _fetch_translated():
    p = []
    code = [set_zw_rd(5, 0, 0x1234)] + exit_seq(EXIT_PASS)
    install_l2_page(p, pa=DATA2_PA)
    store_code(p, DATA2_PA, code)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_0000_0000)
    p.append(jump_rrii(3, 0, 0))
    p += exit_seq(0xEE)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": 0x1234}


@case("ad_not_updated", "A/D stay 0 after a load and a store (no TLB in Step 2)")
def _ad_not_updated():
    p = []
    orig = pte(pa=DATA_PA, a=False, d=False)
    install_l2_page(p, a=False, d=False)
    setup_ptbr(p)
    p += load_rb(3, 0x40)
    p.append(ld_o(5, 3, 0))
    p += load_rd(4, MAGIC2)
    p.append(st_o(4, 3, 0))
    p += load_rb(4, PT_L2_PA)
    p.append(ld_o(6, 4, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": orig}


@case("ad_preserved", "A=1/D=1 in the PTE are left untouched")
def _ad_preserved():
    p = []
    orig = pte(pa=DATA_PA, a=True, d=True)
    install_l2_page(p, a=True, d=True)
    store64(p, DATA_PA, MAGIC)
    setup_ptbr(p)
    p += load_rb(3, 0)
    p.append(ld_o(5, 3, 0))
    p += load_rb(4, PT_L2_PA)
    p.append(ld_o(6, 4, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": orig}


# -- SPF/GPF fragment selection ---------------------------------------------
@case("spf_frag0_ok", "superpage SPF bit0 set, VA[28:26]=0 -> access ok")
def _spf_frag0_ok():
    p = []
    install_superpage(p, l1_idx=1, frags=0x01)
    store64(p, RAM_BASE + 0x80, MAGIC)
    setup_ptbr(p)
    p += load_rb(3, 0x0000_2000_0080)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC}


@case("spf_frag1_fault", "superpage SPF bit0 only: VA[28:26]=1 -> DSPFTRAP")
def _spf_frag1_fault():
    # Fragment 1 lies at offset 64-128 MiB, outside the 16 MiB test RAM, so the
    # selection is proven by the *fault* (bit8 alone is not enough for VA[28:26]=1).
    p = []
    frag = 1
    va = 0x0000_2000_0000 + (frag << 26) + 0x80
    install_superpage(p, l1_idx=1, frags=0x01)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DSPFTRAP, va, ip)


@case("spf_frag0_fault", "superpage SPF bit for VA[28:26]=0 clear -> DSPFTRAP")
def _spf_frag0_fault():
    p = []
    frag = 1
    va = 0x0000_2000_0000 + 0x80
    install_superpage(p, l1_idx=1, frags=1 << frag)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DSPFTRAP, va, ip)


@case("gpf_frag1_ok", "normal page GPF bit for VA[15:13]=1 present -> access ok")
def _gpf_frag1_ok():
    p = []
    frag = 1
    off = (frag << 13) + 0x40
    install_l2_page(p, frags=1 << frag)
    store64(p, DATA_PA + off, MAGIC)
    setup_ptbr(p)
    p += load_rb(3, off)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC}


@case("gpf_frag0_fault", "normal page GPF bit for VA[15:13]=0 clear -> DGPFTRAP")
def _gpf_frag0_fault():
    p = []
    frag = 1
    va = 0x40
    install_l2_page(p, frags=1 << frag)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DGPFTRAP, va, ip)


# -- page misses ------------------------------------------------------------
@case("l1_p0_dgtrap", "L1 P=0 SP=0 data access -> DGPTRAP")
def _l1_p0_dgtrap():
    p = []
    va = 0x1000
    store64(p, PT_L1_PA, pte(pa=PT_L2_PA, p=False, sp=False))
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DGPTRAP, va, ip)


@case("l1_p0_isptrap", "L1 P=0 SP=1 fetch -> ISPTRAP")
def _l1_p0_isptrap():
    p = []
    va = 0x0000_2000_1000
    store64(p, PT_L1_PA + 1 * 8, pte(pa=RAM_BASE, sp=True, p=False))
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    p.append(jump_rrii(3, 0, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_ISPTRAP, va, va)


@case("l2_p0_igtrap", "L2 P=0 fetch -> IGPTRAP")
def _l2_p0_igtrap():
    p = []
    va = 0x1000
    store64(p, PT_L2_PA, pte(pa=DATA_PA, p=False, sp=False))
    store64(p, PT_L1_PA, pte(pa=PT_L2_PA, p=True, sp=False))
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    p.append(jump_rrii(3, 0, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_IGPTRAP, va, va)


@case("l2_p0_dgtrap", "L2 P=0 -> DGPTRAP (store path)")
def _l2_p0_dgtrap():
    p = []
    va = 0x1000
    store64(p, PT_L2_PA, pte(pa=DATA_PA, p=False, sp=False))
    store64(p, PT_L1_PA, pte(pa=PT_L2_PA, p=True, sp=False))
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    p += load_rd(4, MAGIC)
    ip = fault_at(p)
    p.append(st_o(4, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DGPTRAP, va, ip)


# -- HSJU: four run modes ---------------------------------------------------
def _hsju_case(mode, ok):
    target_ha = {MODE_U: 0, MODE_J: 1, MODE_S: 2, MODE_H: 3}[mode]
    va = 0x40
    p = []
    install_l2_page(p, hsju=HSJU_ALL if ok else (HSJU_ALL & ~HSJU_OF_MODE[mode]))
    store64(p, DATA_PA + va, MAGIC)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    if mode == MODE_H:
        ip = fault_at(p)
        p.append(ld_o(5, 3, 0))
        p += exit_seq(EXIT_PASS)
        if ok:
            exp = {"exit": EXIT_PASS, "rd5": MAGIC}
        else:
            exp = fault_expect(C_NHPERM, va, ip)
    else:
        setup_mode_handler(p, target_ha, mode)
        p.append(trap(target_ha, 0))
        p += exit_seq(EXIT_PASS)
        if ok:
            exp = {"exit": EXIT_PASS, "rd5": MAGIC, "rd10": 0}
        else:
            exp = fault_expect(
                {MODE_U: C_NUPERM, MODE_J: C_NJPERM, MODE_S: C_NSPERM}[mode],
                va, MODE_HANDLER + 4)
    handlers = {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}
    if mode != MODE_H:
        handlers[OFF_MODE_HANDLER] = mode_handler(target_ha)
    return build_rom(p, handlers), exp


@case("hsju_u_ok", "U-mode page (U=1) accessible in U mode")
def _hsju_u_ok():
    return _hsju_case(MODE_U, True)


@case("hsju_u_fail", "U-mode page without U bit -> NUPERM")
def _hsju_u_fail():
    return _hsju_case(MODE_U, False)


@case("hsju_j_ok", "J-mode page (J=1) accessible in J mode")
def _hsju_j_ok():
    return _hsju_case(MODE_J, True)


@case("hsju_j_fail", "J-mode page without J bit -> NJPERM")
def _hsju_j_fail():
    return _hsju_case(MODE_J, False)


@case("hsju_s_ok", "S-mode page (S=1) accessible in S mode")
def _hsju_s_ok():
    return _hsju_case(MODE_S, True)


@case("hsju_s_fail", "S-mode page without S bit -> NSPERM")
def _hsju_s_fail():
    return _hsju_case(MODE_S, False)


@case("hsju_h_ok", "H-mode page (H=1) accessible in H mode")
def _hsju_h_ok():
    return _hsju_case(MODE_H, True)


@case("hsju_h_fail", "H-mode page without H bit -> NHPERM")
def _hsju_h_fail():
    return _hsju_case(MODE_H, False)


# -- R/W/X ------------------------------------------------------------------
@case("nrperm", "R=0 load -> NRPERM")
def _nrperm():
    p = []
    va = 0x80
    install_l2_page(p, r=False)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_NRPERM, va, ip)


@case("nwperm", "W=0 store -> NWPERM")
def _nwperm():
    p = []
    va = 0x80
    install_l2_page(p, w=False)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    p += load_rd(4, MAGIC)
    ip = fault_at(p)
    p.append(st_o(4, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_NWPERM, va, ip)


@case("nxperm", "X=0 fetch -> NXPERM")
def _nxperm():
    p = []
    va = 0x0000_0000_0100
    install_l2_page(p, x=False)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    p.append(jump_rrii(3, 0, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_NXPERM, va, va)


# -- exception priority (ADR-0040 D8) --------------------------------------
@case("prio_p0_over_perm", "L1 P=0 + HSJU=0 + R=0 -> IGPTRAP (missing page wins)")
def _prio_p0_over_perm():
    p = []
    va = 0x1000
    store64(p, PT_L1_PA, pte(pa=PT_L2_PA, p=False, sp=False, hsju=0, r=False))
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DGPTRAP, va, ip)


@case("prio_spf_over_perm", "SPF bit 0 + HSJU=0 + R=0 -> DSPFTRAP")
def _prio_spf_over_perm():
    p = []
    va = 0x0000_2000_0080
    install_superpage(p, l1_idx=1, frags=0, hsju=0, r=False)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DSPFTRAP, va, ip)


@case("prio_gpf_over_perm", "GPF bit 0 + HSJU=0 + R=0 -> DGPFTRAP")
def _prio_gpf_over_perm():
    p = []
    va = 0x80
    install_l2_page(p, frags=0, hsju=0, r=False)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DGPFTRAP, va, ip)


@case("prio_hsju_over_rwx", "HSJU=0 + R=0 -> NHPERM (HSJU wins over R)")
def _prio_hsju_over_rwx():
    p = []
    va = 0x80
    install_l2_page(p, hsju=0, r=False)
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_NHPERM, va, ip)


@case("prio_l2p_over_perm", "L2 P=0 + HSJU=0 + R=0 -> DGPTRAP")
def _prio_l2p_over_perm():
    p = []
    va = 0x80
    store64(p, PT_L2_PA, pte(pa=DATA_PA, p=False, sp=False, hsju=0, r=False))
    store64(p, PT_L1_PA, pte(pa=PT_L2_PA, p=True, sp=False))
    setup_ptw_handler(p)
    setup_ptbr(p)
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p, {OFF_PTW_HANDLER: PTW_HANDLER_WORDS}), fault_expect(C_DGPTRAP, va, ip)


# -- regression: ptw_enable=0 still CFXMEM (Step 1 unchanged) ---------------
@case("ptw_off_still_cfxmem", "ptw_enable=0 memory window access still CFXMEM")
def _ptw_off_still_cfxmem():
    p = []
    p += load_rb(3, 0x1000)
    p.append(ld_o(5, 3, 0))
    p += exit_seq(0xEE)
    return build_rom(p), {"exit": EXIT_CFXMEM}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

# ADR-0045 D4: only hmon may access the default-masked cfx resources, so every
# min-ROM body runs in hmon (cfx3).  The power stage at offset 0 installs the
# hmon hypv vector and traps hmon; the original body starts at BOOTSTRAP_OFF.
BOOTSTRAP_OFF = 0x48
STAGE_OFF = 0x24


def bootstrap_prefix():
    ins = load_rd(22, ROM_BASE + STAGE_OFF) + [cfx2rc(3, 3, 10, 22), trap(3, 0)]
    ins += [swym()] * (STAGE_OFF // 4 - len(ins))
    assert len(ins) == STAGE_OFF // 4, len(ins)
    return ins


def bootstrap_stage():
    # hmon stage: clear cfx_power's cfxmem/cfxexe for user/hypv so the body
    # and any cfx0 handler can use RAM and fetch this ROM (ADR-0045 D2).
    ins = load_rd(20, 0)
    for cg in (0, 1, 2, 3):
        ins += [cfx2rc(63, cg, 1, 20), cfx2rc(63, cg, 3, 20)]
    ins += [swym()] * (STAGE_OFF // 4 - len(ins))
    assert len(ins) == STAGE_OFF // 4, len(ins)
    return ins


def bootstrap_rom(rom):
    return words_to_bytes(bootstrap_prefix()) + words_to_bytes(bootstrap_stage()) + rom


def shift_rom_expect(exp):
    # Only code-address expectations move with the bootstrap body; handler
    # addresses (>=0x300) and data values stay put.
    for k in list(exp):
        v = exp[k]
        if (k.startswith("cip") or k == "rd12") and isinstance(v, int) \
                and ROM_BASE <= v < ROM_BASE + 0x10000:
            exp[k] = v + BOOTSTRAP_OFF
    return exp


def run_case(name):
    for n, d, fn in CASES:
        if n == name:
            rom, exp = fn()
            rom = bootstrap_rom(rom)
            exp = shift_rom_expect(exp)
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
