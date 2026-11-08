#!/usr/bin/env python3
"""Min ROM probe for INTEG-040t: address-space Step 3 (TLB / G / A-D / CFXMEM).

Expectations are derived by hand from the frozen spec + ADRs, never from the
QEMU implementation:
  - spec/DADAO-12 §2.2.1/§2.2.2 第二步 (TLB lookup: no tlb_enable, ASID match
    with G bypass, page-granular match, hit does not re-read the PTE, only a
    successful walk fills, miss faults go to the current run-mode monitor),
    §2.2.5 (G semantics, A/D maintenance), §4.5 (cg12 interface: control
    op/scope/ASID_ANY, 16-bit ASID, start/size; A/D write-back failure => monitor
    CFXMEM with cause_info
    = PTE PA).
  - .tao/adr/adr-0041-tlb-ad.md D2-D10; .tao/adr/adr-0040-pte-pagewalk-
    permissions.md D11 (G).
  - spec/Machine-v5-测试机运行环境.md §1.2/§3.
  - contracts/cfx-aliases.txt (cfx_ptw = cfx4), contracts/opcodes.yaml.

Out of scope here (Step 4+): DMA, boot handoff, cfx access permissions and the
Linux user/kernel split.

Observation channels (same convention as min_rom_probe_034t..integ039t):
  * register results -> QEMU `-d cpu` dump (last dump block);
  * fault cause -> current run-mode monitor's cause id copied to rd10,
    cause info -> rd11 (faulting VA, or the PTE PA for CFXMEM), cause ip ->
    rd12; TLB ASID register read back -> `TLBASID` dump line;
  * pass/fail -> semihosting SYS_EXIT (ADR-0020 D8).

The handler comes in two flavours:
  * EXIT -- record rd10/rd11/rd12 and leave (the fault ends the case);
  * SKIP -- record and `escape cfx<mon>, [excp_cause_ip, 4]`, so the case can
    keep running and observe the state a failed/faulting operation left behind.

Usage:
  min_rom_probe_integ040t.py                 # run all checks
  min_rom_probe_integ040t.py --only NAME     # run one check (used by run.sh)
  min_rom_probe_integ040t.py --list
  min_rom_probe_integ040t.py --qemu PATH

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

DEFAULT_QEMU = _prelude.default_qemu()
QEMU = DEFAULT_QEMU
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_integ040t")
TIMEOUT = 10

# TESTCASES-093t: the body runs at RESET_PC + 0x1000 inside the
# 4 MiB bootrom-image, after the shared power -> hmon identity-PTW prelude.
ROM_BASE = _prelude.ROM_BASE
RAM_BASE = _MACH.ram_base
RAM_SIZE = _MACH["ram_size"]

EXIT_PASS = 0x00
EXIT_CFXMEM = 0xF1    # monitor: hypv + CFXMEM index 1

# cfx_ptw (cfx4) register coordinates (DADAO-12 §4.5)
PTW_HA = 4
PTW_ENABLE_CG, PTW_ENABLE_RC = 8, 8
PTBR_CG, PTBR_RC = 9, 0
TLB_CG = 12
TLB_CONTROL_RC, TLB_ASID_RC, TLB_START_RC, TLB_SIZE_RC = 0, 1, 2, 3
CAUSE_ID_RC, CAUSE_INFO_RC, CAUSE_IP_RC = 2, 4, 3
SWITCH_MODE_RC, EXCP_VECTOR_RC = 8, 10

# Page-table physical layout (TESTCASES-093t §3 category C, D3).
# The shared prelude already installed an identity table at PT_PA and left
# PTBR = PT_PA with ptw_enable = 1; a case *extends that live table* instead
# of switching PTBR away from it, so the entries it does not use keep their
# identity mapping (RAM data pages, page-table reads and `exit_block` stay
# reachable).  Table/L2/data pages live in the L1[3] window
# (0x6000_0000..0x7FFF_FFFF) whose identity superpage the cases never touch.
PT_L1_PA = _prelude.PT_PA
PT_L1B_PA = 0x7FF1_0000
PT_L2_PA = 0x7FF2_0000
PT_L2B_PA = 0x7FF3_0000
DATA_PA = 0x6000_0000
DATA2_PA = 0x6100_0000
DATA3_PA = 0x6200_0000
PTBR = PT_L1_PA & 0x00FF_FFFF_FFFF_0000

# CFXMEM carrier: a page table inside the boot ROM.  PTBR must be 64 KiB
# aligned, so the table base is the reset-window base (RESET_PC), not the body
# base (ROM_BASE = RESET_PC + 0x1000, TESTCASES-093t §2).  The L1 entry for
# VA[41:29] = 0x1FFF therefore sits at RESET_PC + 0x1FFF*8 = +0xFFF8, inside
# the 64 KiB reset window.  PTE reads succeed, A/D write-back must fail
# (ROM is RO).  VA[47:42] = 0, so the access stays in the PTW memory window.
ROM_TABLE_PA = _prelude.RESET_PC
ROM_PTE_PA = ROM_TABLE_PA + 0x1FFF * 8
ROM_PTE_OFF = ROM_PTE_PA - ROM_BASE
ROM_L1_IDX = 0x1FFF
ROM_VA = (ROM_L1_IDX << 29) | 0x40

OFF_PTW_HANDLER = 0x300
OFF_MODE_HANDLER = 0x400
OFF_HMON_HANDLER = 0x500
MODE_HANDLER = ROM_BASE + OFF_MODE_HANDLER
PTW_HANDLER = ROM_BASE + OFF_PTW_HANDLER
HMON_HANDLER = ROM_BASE + OFF_HMON_HANDLER

MODE_U, MODE_J, MODE_S, MODE_H = 0, 1, 2, 3
HSJU_ALL = 0xF
HSJU_OF_MODE = {MODE_U: 0x1, MODE_J: 0x2, MODE_S: 0x4, MODE_H: 0x8}

PTE_P = 1 << 0
PTE_SP = 1 << 1
PTE_D = 1 << 2
PTE_A = 1 << 3
PTE_G = 1 << 4
PTE_X = 1 << 5
PTE_W = 1 << 6
PTE_R = 1 << 7
PPN_MASK = 0x00FF_FFFF_FFFF_0000
SPPN_MASK = 0x00FF_FFFF_E000_0000

# monitor cause ids (DADAO-12 §2.2.6/§5.2 + Machine-v5 §7.1)
C_CFXREG = 1 << 2
# Page-table / TLB-hit faults go to the current run-mode monitor
# (DADAO-12 §2.2.6/§5.2 + Machine-v5 §7.1): missing/fragment/A-D => CFXMEM,
# HSJU/R/W/X => CFXPERM.  There is no PTWERR or page-level one-hot cause.
C_CFXMEM = 1 << 1
C_CFXPERM = 1 << 7

# cfx_ptw_tlb_control encoding (DADAO-12 §4.5): op[1:0], scope[3:2], bit4=ASID_ANY
OP_NONE, OP_CLEAN, OP_INVALID, OP_FLUSH = 0, 1, 2, 3
SCOPE_ALL, SCOPE_VA, SCOPE_RANGE, SCOPE_RESERVED = 0, 1, 2, 3


def tlb_ctrl(op, scope, asid_any=False):
    return (op & 0x3) | ((scope & 0x3) << 2) | (0x10 if asid_any else 0)


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
    """Semihosting SYS_EXIT with the profile `exit_block` (TESTCASES-093t §2).

    No cfx register access: the epilogue also runs in U/J/S mode where cfx_ptw
    writes are denied.  Cases keep the prelude's identity table live; only the
    ones that switch PTBR call `restore_prelude_ptbr()` themselves.
    """
    return _prelude.exit_seq(code)


# ---------------------------------------------------------------------------
# Program-building helpers (rd17/rb3/rb4 are scratch; rd5/rd6/rd7/rd10/rd11/
# rd12 are the observation registers and are never used as scratch)
# ---------------------------------------------------------------------------

def store64(p, addr, value, rb=3, rd=17):
    p += load_rb(rb, addr)
    p += load_rd(rd, value)
    p.append(st_o(rd, rb, 0))


def load64(p, addr, rd=6, rb=4):
    p += load_rb(rb, addr)
    p.append(ld_o(rd, rb, 0))


def setup_ptbr(p, ptbr=PTBR, enable=True, flush=True):
    # Category C (TESTCASES-093t §3): switching PTBR does not flush the TLB, so
    # drop the prelude's identity entries first.  `tlb_ptbr_write_no_flush`
    # keeps `flush=False` on purpose (it asserts exactly that behaviour).
    if flush:
        p += load_rd(17, 0x12)          # tlb_control: invalid, all, ASID_ANY
        p.append(cfx2rc(PTW_HA, TLB_CG, TLB_CONTROL_RC, 17))
    p += load_rd(17, ptbr)
    p.append(cfx2rc(PTW_HA, PTBR_CG, PTBR_RC, 17))
    if enable:
        p += load_rd(17, 1)
        p.append(cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 17))


def restore_prelude_ptbr(p):
    """Category C (TESTCASES-093t §3): hand the address space back to the
    prelude's identity table so `exit_block` is reachable after a case switched
    PTBR (writing PTBR does not invalidate the TLB: flush explicitly)."""
    p += load_rd(17, 1)
    p.append(cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 17))
    p += load_rd(17, _prelude.PT_PA)
    p.append(cfx2rc(PTW_HA, PTBR_CG, PTBR_RC, 17))
    p += load_rd(17, 0x12)
    p.append(cfx2rc(PTW_HA, TLB_CG, TLB_CONTROL_RC, 17))


def set_asid(p, asid):
    p += load_rd(17, asid)
    p.append(cfx2rc(PTW_HA, TLB_CG, TLB_ASID_RC, 17))


def tlb_reg(p, rc, val):
    p += load_rd(17, val)
    p.append(cfx2rc(PTW_HA, TLB_CG, rc, 17))


def tlb_cmd(p, val):
    tlb_reg(p, TLB_CONTROL_RC, val)


def tlb_range(p, start, size):
    tlb_reg(p, TLB_START_RC, start)
    tlb_reg(p, TLB_SIZE_RC, size)


def setup_ptw_handler(p, words=None):
    """Route page-table/TLB-hit faults to the current run-mode monitor: each
    cfx0-3 row m gets its own handler variant (self cause read + self escape)."""
    for m in range(4):
        # Run the handler in hypv so cfx cg5 cause reads are not blocked by
        # the supv cg_reg_deleg check; H is the only source cfx allowed to
        # read the other monitors' cg5 frames.
        p += load_rd(17, MODE_H)
        p.append(cfx2rc(m, m, SWITCH_MODE_RC, 17))
        p += load_rd(17, PTW_HANDLER + m * 0x40)
        p.append(cfx2rc(m, m, EXCP_VECTOR_RC, 17))


def setup_hmon_handler(p, words):
    """Route CFXREG faults raised in hypv to the current-mode monitor
    (cfx_hmon; DADAO-12 §5.2)."""
    p += load_rd(17, MODE_H)
    p.append(cfx2rc(3, MODE_H, SWITCH_MODE_RC, 17))
    p += load_rd(17, HMON_HANDLER)
    p.append(cfx2rc(3, MODE_H, EXCP_VECTOR_RC, 17))


def setup_mode_handler(p, target_ha, mode):
    """trap target_ha (from H) enters MODE_HANDLER with inner_run_mode = mode."""
    p += load_rd(17, mode)
    p.append(cfx2rc(target_ha, MODE_H, SWITCH_MODE_RC, 17))
    p += load_rd(17, MODE_HANDLER)
    p.append(cfx2rc(target_ha, MODE_H, EXCP_VECTOR_RC, 17))


def pte(pa=0, hsju=HSJU_ALL, r=True, w=True, x=True, p=True, sp=False,
        frags=0xFF, a=False, d=False, g=False, reserved=0, ppn_override=None):
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
    if g: val |= PTE_G
    if a: val |= PTE_A
    if d: val |= PTE_D
    if sp: val |= PTE_SP
    if p: val |= PTE_P
    return val


def install_page(p, l1_idx=0, l2_idx=0, pa=DATA_PA, l2_pa=PT_L2_PA, l1_pa=PT_L1_PA,
                 **kw):
    store64(p, l2_pa + l2_idx * 8, pte(pa=pa, **kw))
    store64(p, l1_pa + l1_idx * 8, pte(pa=l2_pa, p=True, sp=False))


def set_page_pte(p, l2_idx=0, pa=DATA_PA, l2_pa=PT_L2_PA, **kw):
    store64(p, l2_pa + l2_idx * 8, pte(pa=pa, **kw))


def load_va(p, va, rd=5):
    p += load_rb(3, va)
    p.append(ld_o(rd, 3, 0))


def store_va(p, va, value, rd=4):
    p += load_rb(3, va)
    p += load_rd(rd, value)
    p.append(st_o(rd, 3, 0))


def load_va_fault(p, va, rd=5):
    """Append `ld.o rd, [rb3]` and return its ROM address (the faulting IP)."""
    p += load_rb(3, va)
    ip = fault_at(p)
    p.append(ld_o(rd, 3, 0))
    return ip


def store_va_fault(p, va, value, rd=4):
    """Append `st.o rd, [rb3]` and return its ROM address (the faulting IP)."""
    p += load_rb(3, va)
    p += load_rd(rd, value)
    ip = fault_at(p)
    p.append(st_o(rd, 3, 0))
    return ip


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers=None, words_at=None):
    """Shared prelude: body at RESET_PC + 0x1000 in the 4 MiB ROM image."""
    return _prelude.build_rom(prog, handlers, words_at)

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
    for n in (5, 6, 7, 10, 11, 12):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    o["tblasid"] = lasthex(log, r"TLBASID: ([0-9a-f]+)")
    for cfxha in range(4):
        o["cid%d" % cfxha] = lasthex(
            log, r"CFX%02d PREVM:[^\n]* CID:([0-9a-f]+)" % cfxha)
        o["syncn%d" % cfxha] = lasthex(
            log, r"CFX%02d ID:[^\n]* SYNCN:([0-9a-f]+)" % cfxha)
    return o


# ---------------------------------------------------------------------------
# Case model + builders
# ---------------------------------------------------------------------------

CASES = []
# Extra checks run only on demand (`--only`), so the parity matrix's frozen
# case set/count stays unchanged.
EXTRA_CASES = []
MAGIC = 0x1122_3344_5566_7788
MAGIC2 = 0x99AA_BBCC_DDEE_FF00
MAGIC3 = 0x0F1E_2D3C_4B5A_6978


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def extra_case(name, desc):
    def deco(fn):
        EXTRA_CASES.append((name, desc, fn))
        return fn
    return deco


def monitor_words(cfxha, skip):
    """Read the faulted monitor's cfx cg5 cause frame and exit/escape."""
    words = [cfx2rd(cfxha, 5, CAUSE_ID_RC, 10),
             cfx2rd(cfxha, 5, CAUSE_INFO_RC, 11),
             cfx2rd(cfxha, 5, CAUSE_IP_RC, 12)]
    return words + ([escape(cfxha, 1)] if skip else exit_seq(EXIT_PASS))


def monitor_handler_dict(skip):
    return {OFF_PTW_HANDLER + m * 0x40: monitor_words(m, skip)
            for m in range(4)}

# Current-mode monitor (cfx_hmon) equivalent: the CFXREG from a cfx2rd/cfx2rc
# is delivered to the hypv monitor (DADAO-12 §5.2), so read its cause frame.
HMON_EXIT_WORDS = ([cfx2rd(3, 5, CAUSE_ID_RC, 10),
                    cfx2rd(3, 5, CAUSE_INFO_RC, 11),
                    cfx2rd(3, 5, CAUSE_IP_RC, 12)]
                   + exit_seq(EXIT_PASS))

HMON_SKIP_WORDS = ([cfx2rd(3, 5, CAUSE_ID_RC, 10),
                    cfx2rd(3, 5, CAUSE_INFO_RC, 11),
                    cfx2rd(3, 5, CAUSE_IP_RC, 12),
                    escape(3, 1)])


def mode_handler(target_ha, rd=5):
    """S/J/U handler body: do the access, escape back to the trap PC+4."""
    return ([ld_o(rd, 3, 0)] + [escape(target_ha, 1)])


def fault_at(p):
    """ROM address of the next appended instruction (the faulting one)."""
    return ROM_BASE + 4 * len(p)


def fault_expect(cause, va, ip, cfxha=MODE_H, **extra):
    exp = {"exit": EXIT_PASS, "rd10": cause, "rd11": va, "rd12": ip,
           "syncn%d" % cfxha: 1, "cid%d" % cfxha: cause}
    exp.update(extra)
    return exp


def fault_expect_hmon(cause, va, ip, **extra):
    """Same observation, but the CFXREG frame lives on the current-mode
    monitor (cfx_hmon, DADAO-12 §5.2)."""
    exp = {"exit": EXIT_PASS, "rd10": cause, "rd11": va, "rd12": ip,
           "syncn3": 1, "cid3": cause}
    exp.update(extra)
    return exp


def data_setup(p):
    store64(p, DATA_PA, MAGIC)
    store64(p, DATA2_PA, MAGIC2)


# -- ASID isolation / hit semantics ----------------------------------------
@case("tlb_asid_isolated", "ASID change misses the old entry and re-walks")
def _tlb_asid_isolated():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)                         # ASID 0: fill -> DATA
    set_page_pte(p, pa=DATA2_PA)            # PTE now maps DATA2
    set_asid(p, 1)
    load_va(p, 0x0, rd=6)                   # ASID 1: miss -> walk -> DATA2
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC2,
                          "tblasid": 1}


@case("tlb_hit_no_pte_reread", "hit does not re-read the PTE (edited PTE ignored)")
def _tlb_hit_no_pte_reread():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)                         # fill -> DATA
    set_page_pte(p, pa=DATA2_PA)            # a walk would now yield DATA2
    load_va(p, 0x0, rd=6)                   # hit -> still DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC}


@case("tlb_g_cross_asid", "G=1 entry is reused across ASIDs")
def _tlb_g_cross_asid():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, g=True)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)                         # ASID 0 fill (G)
    set_page_pte(p, pa=DATA2_PA, g=True)
    set_asid(p, 1)
    load_va(p, 0x0, rd=6)                   # ASID 1 hits the G entry -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC}


@case("tlb_g_kept_asid_invalid", "ASID_ANY=0 invalidation skips G entries")
def _tlb_g_kept_asid_invalid():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, g=True)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)                         # fill G entry
    set_page_pte(p, pa=DATA2_PA, g=True)
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=False))
    load_va(p, 0x0, rd=6)                   # G entry survived -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC}


@case("tlb_g_removed_asid_any", "ASID_ANY=1 invalidation includes G entries")
def _tlb_g_removed_asid_any():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, g=True)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA, g=True)
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=True))
    load_va(p, 0x0, rd=6)                   # deleted -> re-walk -> DATA2
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC2}


@case("tlb_non_g_removed_asid", "ASID_ANY=0 invalidation removes matching ASID")
def _tlb_non_g_removed_asid():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=False))
    load_va(p, 0x0, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC2}


# -- permissions on a hit ---------------------------------------------------
@case("tlb_hit_hsju_perm", "hit uses the entry's HSJU, not the edited PTE")
def _tlb_hit_hsju_perm():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, hsju=HSJU_OF_MODE[MODE_S])
    data_setup(p)
    setup_ptw_handler(p)
    setup_mode_handler(p, 2, MODE_S)        # cfx_smon trap enters S mode
    setup_ptbr(p)
    p += load_rb(3, 0x0)
    p.append(trap(2, 0))                    # S-mode load fills the entry
    set_page_pte(p, pa=DATA_PA, hsju=HSJU_ALL)  # a walk would now succeed
    ip = load_va_fault(p, 0x0)              # H mode: entry HSJU=S -> CFXPERM
    p += exit_seq(0x7E)
    handlers = monitor_handler_dict(False)
    handlers[OFF_MODE_HANDLER] = mode_handler(2)
    return build_rom(p, handlers), fault_expect(C_CFXPERM, 0x0, ip)


@case("tlb_hit_nwperm", "hit uses the entry's W, not the edited PTE")
def _tlb_hit_nwperm():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, w=False)
    data_setup(p)
    setup_ptw_handler(p)
    setup_ptbr(p)
    load_va(p, 0x0)                         # read fill (W=0 stored in entry)
    set_page_pte(p, pa=DATA_PA, w=True)     # a walk would now allow the store
    ip = store_va_fault(p, 0x0, MAGIC2)     # hit -> CFXPERM
    p += exit_seq(0x7E)
    return build_rom(p, monitor_handler_dict(False)), \
        fault_expect(C_CFXPERM, 0x0, ip)


@case("tlb_hit_gpf_fault", "hit checks the page's GPF fragment bit per access")
def _tlb_hit_gpf_fault():
    # TESTCASES-093t §3 category C: the entry is filled by a load (A=1, D=0), so
    # QEMU's soft TLB keeps the page read-only and the *store* below forces a
    # fill, i.e. the hit-time GPF check of DADAO-12 §2.2.5 runs.  A second load
    # would be served by QEMU's fast TLB without re-checking the fragment.
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, frags=1 << 1)   # fragment 1 only
    store64(p, DATA_PA + 0x2040, MAGIC)
    setup_ptw_handler(p)
    setup_ptbr(p)
    load_va(p, 0x2040)                      # VA[15:13]=1 present -> fill
    ip = store_va_fault(p, 0x40, MAGIC2, rd=4)   # same page, VA[15:13]=0
    p += exit_seq(0x7E)
    return build_rom(p, monitor_handler_dict(False)), \
        fault_expect(C_CFXMEM, 0x40, ip)


# -- fill only after a fully valid walk ------------------------------------
@case("tlb_no_fill_on_perm_fault", "permission fault does not fill the TLB")
def _tlb_no_fill_on_perm_fault():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, r=False)        # CFXPERM on read
    data_setup(p)
    setup_ptw_handler(p)
    setup_ptbr(p)
    ip = load_va_fault(p, 0x0)              # CFXPERM -> handler skips
    set_page_pte(p, pa=DATA2_PA)            # now readable, maps DATA2
    load_va(p, 0x0, rd=6)                   # must re-walk -> DATA2
    p += exit_seq(EXIT_PASS)
    return build_rom(p, monitor_handler_dict(True)), \
        fault_expect(C_CFXPERM, 0x0, ip, rd5=0, rd6=MAGIC2)


# -- A/D maintenance --------------------------------------------------------
@case("ad_fill_no_writeback", "fill alone never writes A/D back")
def _ad_fill_no_writeback():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, a=False, d=False)
    store64(p, DATA_PA, MAGIC)
    setup_ptbr(p)
    load_va(p, 0x0)
    load64(p, PT_L2_PA, rd=6)               # PTE still A=0/D=0
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC,
                          "rd6": pte(pa=DATA_PA, a=False, d=False)}


@case("ad_read_sets_a", "CLEAN after a load writes back A=1, D=0")
def _ad_read_sets_a():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, a=False, d=False)
    store64(p, DATA_PA, MAGIC)
    setup_ptbr(p)
    load_va(p, 0x0)
    tlb_cmd(p, tlb_ctrl(OP_CLEAN, SCOPE_ALL, asid_any=True))
    load64(p, PT_L2_PA, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC,
                          "rd6": pte(pa=DATA_PA, a=True, d=False)}


@case("ad_write_sets_ad", "CLEAN after a store writes back A=1 and D=1")
def _ad_write_sets_ad():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, a=False, d=False)
    data_setup(p)
    setup_ptbr(p)
    store_va(p, 0x0, MAGIC3)
    tlb_cmd(p, tlb_ctrl(OP_CLEAN, SCOPE_ALL, asid_any=True))
    load64(p, PT_L2_PA, rd=6)
    load64(p, DATA_PA, rd=7)                # the store really landed
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd7": MAGIC3,
                          "rd6": pte(pa=DATA_PA, a=True, d=True)}


@case("ad_clean_keeps_entry", "CLEAN writes back and keeps the entry")
def _ad_clean_keeps_entry():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, a=False, d=False)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    tlb_cmd(p, tlb_ctrl(OP_CLEAN, SCOPE_ALL, asid_any=True))
    set_page_pte(p, pa=DATA2_PA)            # a walk would now yield DATA2
    load_va(p, 0x0, rd=6)                   # entry kept -> hit -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": MAGIC}


@case("ad_flush_writes_deletes", "FLUSH writes A/D back and deletes the entry")
def _ad_flush_writes_deletes():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, a=False, d=False)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    tlb_cmd(p, tlb_ctrl(OP_FLUSH, SCOPE_ALL, asid_any=True))
    load64(p, PT_L2_PA, rd=6)               # A=1 written back
    set_page_pte(p, pa=DATA2_PA)
    load_va(p, 0x0, rd=7)                   # deleted -> re-walk -> DATA2
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS,
                          "rd6": pte(pa=DATA_PA, a=True, d=False),
                          "rd7": MAGIC2}


@case("ad_invalid_no_writeback", "INVALID deletes without writing A/D back")
def _ad_invalid_no_writeback():
    p = []
    orig = pte(pa=DATA_PA, a=False, d=False)
    install_page(p, l2_idx=0, pa=DATA_PA, a=False, d=False)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=True))
    load64(p, PT_L2_PA, rd=6)               # PTE untouched
    set_page_pte(p, pa=DATA2_PA)
    load_va(p, 0x0, rd=7)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": orig, "rd7": MAGIC2}


@case("ad_writeback_preserves_fields", "A/D write-back ORs only A/D bits")
def _ad_writeback_preserves_fields():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, a=False, d=False, reserved=0xF)
    data_setup(p)
    setup_ptbr(p)
    store_va(p, 0x0, MAGIC3)
    tlb_cmd(p, tlb_ctrl(OP_CLEAN, SCOPE_ALL, asid_any=True))
    load64(p, PT_L2_PA, rd=6)
    load64(p, DATA_PA, rd=7)                # the store really landed
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd7": MAGIC3,
                          "rd6": pte(pa=DATA_PA, a=True, d=True, reserved=0xF)}


# -- CFXMEM: A/D write-back into the read-only boot ROM --------------------
def rom_pte_setup(p):
    store64(p, RAM_BASE + 0x40, MAGIC)
    setup_ptw_handler(p)
    setup_ptbr(p, ptbr=ROM_TABLE_PA)        # page table lives in the ROM
    load_va(p, ROM_VA)                      # fill from the ROM PTE


ROM_PTE_WORDS = [((pte(pa=RAM_BASE, sp=True, frags=0xFF) >> 32) & 0xFFFFFFFF),
                 (pte(pa=RAM_BASE, sp=True, frags=0xFF) & 0xFFFFFFFF)]


@case("ptwerr_clean_keeps_entry", "failed CLEAN reports CFXMEM and keeps the entry")
def _ptwerr_clean_keeps_entry():
    p = []
    rom_pte_setup(p)
    tlb_cmd(p, tlb_ctrl(OP_CLEAN, SCOPE_ALL, asid_any=True))    # -> CFXMEM
    p += [set_zw_rd(10, 0, 0)]                                  # clear the record
    tlb_cmd(p, tlb_ctrl(OP_CLEAN, SCOPE_ALL, asid_any=True))    # entry kept
    restore_prelude_ptbr(p)                                     # exit_block
    p += exit_seq(EXIT_PASS)
    return build_rom(p, monitor_handler_dict(True),
                     words_at={ROM_PTE_OFF: ROM_PTE_WORDS}), \
        {"exit": EXIT_PASS, "rd10": C_CFXMEM, "rd11": ROM_PTE_PA,
         "rd5": MAGIC, "syncn3": 2, "cid3": C_CFXMEM}


@case("ptwerr_flush_keeps_entry", "failed FLUSH keeps the dirty entry")
def _ptwerr_flush_keeps_entry():
    p = []
    rom_pte_setup(p)
    tlb_cmd(p, tlb_ctrl(OP_FLUSH, SCOPE_ALL, asid_any=True))    # -> CFXMEM
    load_va(p, ROM_VA, rd=5)                                    # still usable
    p += [set_zw_rd(10, 0, 0)]
    tlb_cmd(p, tlb_ctrl(OP_FLUSH, SCOPE_ALL, asid_any=True))    # CFXMEM again
    restore_prelude_ptbr(p)                                     # exit_block
    p += exit_seq(EXIT_PASS)
    return build_rom(p, monitor_handler_dict(True),
                     words_at={ROM_PTE_OFF: ROM_PTE_WORDS}), \
        {"exit": EXIT_PASS, "rd10": C_CFXMEM, "rd11": ROM_PTE_PA,
         "rd5": MAGIC, "syncn3": 2, "cid3": C_CFXMEM}


@extra_case("ptwerr_monitor_cfxmem_exit",
      "A/D write-back failure with an invalid monitor vector exits as monitor CFXMEM")
def _ptwerr_monitor_cfxmem_exit():
    p = []
    store64(p, RAM_BASE + 0x40, MAGIC)
    # No monitor handler: point cfx_hmon's hypv vector at an unmapped cfxha63
    # address.  The A/D write-back fault enters the H monitor, whose fetch of
    # that vector raises the direct machine fault; the exit code must be the
    # monitor CFXMEM segment for hypv (0xF1).
    p += load_rd(17, 0xFFFF_0000_0000)
    p.append(cfx2rc(3, MODE_H, EXCP_VECTOR_RC, 17))
    setup_ptbr(p, ptbr=ROM_TABLE_PA)
    load_va(p, ROM_VA)                      # fill a dirty entry from the ROM PTE
    tlb_cmd(p, tlb_ctrl(OP_CLEAN, SCOPE_ALL, asid_any=True))  # A/D write-back fails
    p += exit_seq(EXIT_PASS)                # unreachable on success
    return build_rom(p, words_at={ROM_PTE_OFF: ROM_PTE_WORDS}), \
        {"exit": EXIT_CFXMEM}


@case("ptwerr_invalid_no_writeback", "INVALID needs no write-back (no monitor fault)")
def _ptwerr_invalid_no_writeback():
    p = []
    rom_pte_setup(p)
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=True))  # no write-back
    load64(p, ROM_PTE_PA, rd=6)                                 # ROM PTE: A=0
    load_va(p, ROM_VA, rd=7)                                    # re-walk works
    restore_prelude_ptbr(p)                                     # exit_block
    p += exit_seq(EXIT_PASS)
    return build_rom(p, monitor_handler_dict(True),
                     words_at={ROM_PTE_OFF: ROM_PTE_WORDS}), \
        {"exit": EXIT_PASS, "rd10": 0,
         "rd6": pte(pa=RAM_BASE, sp=True, frags=0xFF), "rd7": MAGIC}


# -- op / scope / ASID combinations ---------------------------------------
@case("tlb_op_none_noop", "op=00 is a no-op (no exception, no deletion)")
def _tlb_op_none_noop():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_cmd(p, tlb_ctrl(OP_NONE, SCOPE_ALL, asid_any=True))
    load_va(p, 0x0, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd10": 0, "rd6": MAGIC}


@case("tlb_op_none_scope_reserved", "op=00 wins over scope=11 (no CFXREG)")
def _tlb_op_none_scope_reserved():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptw_handler(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_cmd(p, tlb_ctrl(OP_NONE, SCOPE_RESERVED))   # must be a silent no-op
    load_va(p, 0x0, rd=6)                           # entry untouched -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p, monitor_handler_dict(True)), \
        {"exit": EXIT_PASS, "rd10": 0, "rd6": MAGIC}


@case("tlb_op_none_range_size0", "op=00 wins over range+size=0 (no CFXREG)")
def _tlb_op_none_range_size0():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptw_handler(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_range(p, 0x0, 0)
    tlb_cmd(p, tlb_ctrl(OP_NONE, SCOPE_RANGE))      # must be a silent no-op
    load_va(p, 0x0, rd=6)                           # entry untouched -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p, monitor_handler_dict(True)), \
        {"exit": EXIT_PASS, "rd10": 0, "rd6": MAGIC}


@case("tlb_scope_reserved_cfxreg", "scope=11 => CFXREG")
def _tlb_scope_reserved_cfxreg():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_hmon_handler(p, HMON_EXIT_WORDS)
    setup_ptbr(p)
    load_va(p, 0x0)
    p += load_rd(17, tlb_ctrl(OP_INVALID, SCOPE_RESERVED))
    ip = fault_at(p)
    p.append(cfx2rc(PTW_HA, TLB_CG, TLB_CONTROL_RC, 17))
    p += exit_seq(0x7E)
    return build_rom(p, {OFF_HMON_HANDLER: HMON_EXIT_WORDS}), \
        fault_expect_hmon(C_CFXREG, None, ip, rd11=None)


@case("tlb_range_size0_cfxreg", "range with size=0 => CFXREG and no deletion")
def _tlb_range_size0_cfxreg():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_hmon_handler(p, HMON_SKIP_WORDS)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_range(p, 0x0, 0)
    p += load_rd(17, tlb_ctrl(OP_INVALID, SCOPE_RANGE))
    ip = fault_at(p)
    p.append(cfx2rc(PTW_HA, TLB_CG, TLB_CONTROL_RC, 17))
    load_va(p, 0x0, rd=6)                   # entry untouched -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p, {OFF_HMON_HANDLER: HMON_SKIP_WORDS}), \
        fault_expect_hmon(C_CFXREG, None, ip, rd11=None, rd6=MAGIC)


@case("tlb_scope_va", "scope=VA matches only the page containing start")
def _tlb_scope_va():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    install_page(p, l2_idx=1, pa=DATA2_PA)
    data_setup(p)
    store64(p, DATA3_PA, MAGIC3)
    setup_ptbr(p)
    load_va(p, 0x0, rd=5)                   # page 0: MAGIC
    load_va(p, 0x10000, rd=7)               # page 1: MAGIC2
    # Both entries are cached; rewrite both PTEs (a re-walk swaps the targets).
    set_page_pte(p, l2_idx=0, pa=DATA3_PA)
    set_page_pte(p, l2_idx=1, pa=DATA_PA)
    tlb_range(p, 0x0, 1)                    # size ignored for scope=VA
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_VA, asid_any=True))
    load_va(p, 0x0, rd=6)                   # page 0 deleted -> re-walk -> DATA3
    load_va(p, 0x10000, rd=5)               # page 1 kept -> still DATA2
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd7": MAGIC2, "rd6": MAGIC3,
                          "rd5": MAGIC2}


@case("tlb_scope_range_hit", "range overlapping a page deletes it")
def _tlb_scope_range_hit():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_range(p, 0xF000, 0x2000)            # [0xF000,0x11000) overlaps page 0
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_RANGE, asid_any=True))
    load_va(p, 0x0, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": MAGIC2}


@case("tlb_scope_range_miss", "range outside the page leaves it cached")
def _tlb_scope_range_miss():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_range(p, 0x30000, 0x1000)           # does not overlap page 0
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_RANGE, asid_any=True))
    load_va(p, 0x0, rd=6)                   # still cached -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": MAGIC}


@case("tlb_scope_all", "scope=all ignores start/size")
def _tlb_scope_all():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    tlb_range(p, 0xDEAD000, 0x1000)         # junk window, must be ignored
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=True))
    load_va(p, 0x0, rd=6)
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": MAGIC2}


@case("tlb_asid_any0_mismatch", "ASID_ANY=0 does not touch another ASID")
def _tlb_asid_any0_mismatch():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    set_asid(p, 1)
    load_va(p, 0x0)                         # fill under ASID 1
    set_page_pte(p, pa=DATA2_PA)
    set_asid(p, 0)
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=False))  # ASID 0 only
    set_asid(p, 1)
    load_va(p, 0x0, rd=6)                   # ASID 1 entry survived -> DATA
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": MAGIC, "tblasid": 1}


@case("tlb_asid_any1_all", "ASID_ANY=1 invalidates entries of every ASID")
def _tlb_asid_any1_all():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    data_setup(p)
    setup_ptbr(p)
    set_asid(p, 1)
    load_va(p, 0x0)
    set_page_pte(p, pa=DATA2_PA)
    set_asid(p, 0)
    tlb_cmd(p, tlb_ctrl(OP_INVALID, SCOPE_ALL, asid_any=True))
    set_asid(p, 1)
    load_va(p, 0x0, rd=6)                   # deleted -> re-walk -> DATA2
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd6": MAGIC2}


# -- regressions: bypass / no implicit flush / ASID register --------------
@case("tlb_bypass_ptw_off", "ptw_enable=0 bypasses the TLB -> CFXMEM")
def _tlb_bypass_ptw_off():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA)
    store64(p, DATA_PA, MAGIC)
    setup_ptbr(p)
    load_va(p, 0x0)                         # entry exists now
    p += load_rd(17, 0)
    p.append(cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 17))
    load_va(p, 0x0)                         # ptw off -> CFXMEM
    p += exit_seq(0x7E)
    return build_rom(p), {"exit": EXIT_CFXMEM}


@case("tlb_ptbr_write_no_flush", "writing PTBR does not invalidate the TLB")
def _tlb_ptbr_write_no_flush():
    p = []
    install_page(p, l2_idx=0, pa=DATA_PA, l1_pa=PT_L1_PA)
    install_page(p, l2_idx=0, pa=DATA2_PA, l1_pa=PT_L1B_PA, l2_pa=PT_L2B_PA)
    data_setup(p)
    setup_ptbr(p, ptbr=PTBR)
    load_va(p, 0x0)                         # fill from L1 -> DATA
    setup_ptbr(p, ptbr=PT_L1B_PA & 0x00FF_FFFF_FFFF_0000, enable=False, flush=False)
    load_va(p, 0x0, rd=6)                   # entry kept -> DATA (not DATA2)
    restore_prelude_ptbr(p)                 # PTBR was switched away
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": MAGIC, "rd6": MAGIC}


@case("tlb_asid_reg_roundtrip", "ASID register is 16 bits wide")
def _tlb_asid_reg_roundtrip():
    p = []
    set_asid(p, 0xBEEF)
    p.append(cfx2rd(PTW_HA, TLB_CG, TLB_ASID_RC, 5))
    set_asid(p, 0x1_2345)
    p.append(cfx2rd(PTW_HA, TLB_CG, TLB_ASID_RC, 6))
    p += exit_seq(EXIT_PASS)
    return build_rom(p), {"exit": EXIT_PASS, "rd5": 0xBEEF, "rd6": 0x2345,
                          "tblasid": 0x2345}



# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_case(name):
    for n, d, fn in CASES + EXTRA_CASES:
        if n == name:
            rom, exp = fn()
            # rd12 (cause ip) is not asserted when the expectation omits it:
            # A/D write-back failures are raised from the command write, whose
            # precise PC is checked by the CFXREG cases instead.
            exp = {k: v for k, v in exp.items() if v is not None}
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
