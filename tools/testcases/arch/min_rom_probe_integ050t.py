#!/usr/bin/env python3
"""Min ROM probe for INTEG-050t: cfx_time (cfxha 18) + single-hart cfx_hart
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

Expectations are derived by hand from the frozen spec / contract:
  - spec/DADAO-12 §4.7 (cfx_hart: cg8 rc0 hart_id, rc2 cycle 64-bit, rc3 insn
    64-bit, rc4 timer_cmp, rc5 timer_ctrl ENABLE/IMASK/ISTATUS, rc6/rc7
    reserved; TIMER 1<<10 maskable, cause_info 0), §4.10 (cfx_time: cg10 rc0
    time_freq, rc1 time_value 64-bit, rc2-rc63 reserved).
  - spec/DADAO-22 §7 / §10 (SBI_HART_GET_ID / SBI_HART_SET_TIMER /
    SBI_TIME_GET; 64-bit timeout/value).
  - .tao/contracts/contract-see.md §3 (test-machine projection: 1 GHz,
    1 count = 1 ns, cycle = virtual clock, insn = per-instruction count).
  Never from the QEMU implementation.

Observation channels (same convention as min_rom_probe_integ047t.py):
  * register / fault-frame results -> QEMU `-d cpu` dump (last dump block);
  * timer cases -> `-icount shift=0` (1 ns/instruction) with in-program
    self-checks and a semihosting SYS_EXIT exit code (that mode has no dump).

Bootstrap (the probe body runs in hmon / cfx3, hypv):
  1. power stage: set cfx_hmon hypv_excp_vector, clear bit15/bit18 of
     cfx_hmon hypv_switch_cfx_mask, then `trap cfx_hmon, 0`.  Bit15 is the
     TIMER source gate (step 3); bit18 is needed because SBI calls use
     `trap cfx_time` (also step 3).
  2. hmon stage: clear cfx_hmon hypv_cfx_intr_mask (cg3 rc4) bit15 and
     cfx_hmon global_cfx_intr_mask (cg8 rc1) bit15 (async step 4), clear
     cfx_hart hypv_excp_cause_mask (cg3 rc11) bit10 (async step 5), install
     the cfx_hart / cfx_time exception vectors, and clear cfx_power's
     cfxmem/cfxexe source masks for all four modes (so the ROM handler stays
     fetchable / RAM readable while inner_cfx_code = 15/18).

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
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
QEMU = DEFAULT_QEMU
WORKDIR = "/tmp/opencode/INTEG-050t"
TIMEOUT = 90

SPEC_SEE = os.path.join(_REPO, "spec", "DADAO-12-SEE-主管系统运行环境.md")
SPEC_SBI = os.path.join(_REPO, "spec", "DADAO-22-SBI-主管系统二进制接口.md")
CONTRACT_SEE = os.path.join(_REPO, ".tao", "contracts", "contract-see.md")

ROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0xFC00_0000_0000

HART_HA = 15
TIME_HA = 18
HART_CG = 8
TIME_CG = 10
CG5_CAUSE_ID_RC, CG5_CAUSE_IP_RC, CG5_CAUSE_INFO_RC, CG5_PENDING_RC = 2, 3, 4, 5
CG3_EXCP_VECTOR_RC, CG3_EXCP_CAUSE_MASK_RC = 10, 11
CG3_CFX_INTR_MASK_RC = 4
CG3_SWITCH_CFX_MASK_RC = 9

CFXTRAP = 1 << 0
CFXREG = 1 << 2
TIMER = 1 << 10
CTRL_ENABLE = 1 << 0
CTRL_IMASK = 1 << 1
CTRL_ISTATUS = 1 << 2

TIME_FREQ = 1_000_000_000
ALL1 = (1 << 64) - 1
BIT63 = 1 << 63

EXIT_PASS = 0x00
EXIT_FAIL = 0xE1

# ROM layout: prefix (power) -> stage (hmon) -> body (hmon).
STAGE_OFF = 0x30
BOOTSTRAP_OFF = 0x120

OFF_FH3 = 0x700       # CFXREG handler for faults raised at the hmon monitor
OFF_FH15 = 0x740      # CFXREG handler for faults raised at cfx_hart
OFF_FH18 = 0x780      # CFXREG handler for faults raised at cfx_time
OFF_HART_PROVIDER = 0x800
OFF_TIME_PROVIDER = 0x880

RAM_STATE = 0x3000    # handler-recorded cause frame / counter

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
    """Report `code` via semihosting SYS_EXIT -> host $? (ADR-0020 D8)."""
    return ([jump_iiii(1)]
            + load_rb(16, SEMI_BLOCK)
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


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
    a = Asm()
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_ID_RC, 20))
    a.emit(*load_rd(21, CFXTRAP))
    a.br("eq", 20, 21, "hart_sbi")
    a.emit(*load_rd(21, TIMER))
    a.br("eq", 20, 21, "hart_timer")
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
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 16))
    a.emit(*load_rd(17, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 17))
    a.emit(*load_rd(8, 0))
    a.emit(escape(HART_HA, 1))
    a.mark("hart_sbi_unknown")
    a.emit(escape(HART_HA, 1))
    # --- TIMER handler: record cause frame + counter, return to cause_ip ---
    a.mark("hart_timer")
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_ID_RC, 20))
    a.emit(st_o(20, 5, RAM_STATE + 0x00))
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_INFO_RC, 20))
    a.emit(st_o(20, 5, RAM_STATE + 0x08))
    a.emit(cfx2rd(HART_HA, 5, CG5_CAUSE_IP_RC, 20))
    a.emit(st_o(20, 5, RAM_STATE + 0x10))
    a.emit(ld_o(20, 5, RAM_STATE + 0x18))
    a.emit(add_si(20, 1))
    a.emit(st_o(20, 5, RAM_STATE + 0x18))
    a.emit(escape(HART_HA, 0))
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
    OFF_FH18: build_fault_handler(TIME_HA),
    OFF_HART_PROVIDER: build_hart_provider(),
    OFF_TIME_PROVIDER: build_time_provider(),
}


# ---------------------------------------------------------------------------
# Program-building helpers (body runs in hmon / cfx3, hypv mode).
# ---------------------------------------------------------------------------

def hmon_addr(off):
    return ROM_BASE + BOOTSTRAP_OFF + off


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


def delay_loop(a, rd, count, tag):
    a.emit(*load_rd(rd, count))
    a.mark("dl_%s" % tag)
    a.emit(add_si(rd, -1))
    a.br("nz", rd, 0, "dl_%s" % tag)


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
    for n in range(5, 15):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    return o


def build_rom(prog, handlers=None):
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers or {}):
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(handlers[off])
    while len(rom) < 0x900:
        rom += words_to_bytes([swym()])
    return bytes(rom)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap_prefix():
    # cfx_hmon hypv_excp_vector = ROM_BASE + STAGE_OFF
    ins = load_rd(22, ROM_BASE + STAGE_OFF) + [cfx2rc(3, 3, CG3_EXCP_VECTOR_RC, 22)]
    # cfx_hmon hypv_switch_cfx_mask: clear bit15 (TIMER source) and bit18
    # (cfx_time traps) so step 3 lets them through.
    ins += load_rd(22, 0xFFFF_FFFF_FFFB_7FF7) + [cfx2rc(3, 3, CG3_SWITCH_CFX_MASK_RC, 22)]
    ins += [trap(3, 0)]
    ins += [swym()] * (STAGE_OFF // 4 - len(ins))
    assert len(ins) == STAGE_OFF // 4, len(ins)
    return ins


def bootstrap_stage():
    # Source masks are cleared for bit15/bit18 in hmon, cfx_hart and cfx_time
    # (hypv row only): once a trap/escape has run, inner_cfx_code stays at the
    # trapped cfx in this model, so later cross-cfx reads must not be denied.
    MASK = 0xFFFF_FFFF_FFFB_7FF7
    MASK_HMON = 0x7FFF_FFFF_FFFB_7FF7
    # rb5 = RAM_BASE, used by the timer handler for its state block.
    ins = load_rb(5, RAM_BASE)
    ins += load_rd(21, MASK_HMON)
    # hmon: hypv cfx{trap,mem,reg,exe} + cfx_intr_mask + global_cfx_intr_mask
    for rc in (0, 1, 2, 3, CG3_CFX_INTR_MASK_RC):
        ins += [cfx2rc(3, 3, rc, 21)]
    ins += [cfx2rc(3, 8, 1, 21)]
    # cfx_hart: hypv cfx{trap,mem,reg,exe} + cfx_intr_mask (self TIMER gate)
    for rc in (0, 1, 2, 3, CG3_CFX_INTR_MASK_RC):
        ins += [cfx2rc(HART_HA, 3, rc, 21)]
    # cfx_time: hypv cfx{trap,mem,reg,exe} (cross-cfx reads after a trap)
    for rc in (0, 1, 2, 3):
        ins += [cfx2rc(TIME_HA, 3, rc, 21)]
    # cfx_hart hypv_excp_cause_mask bit10 = 0 (async step 5)
    ins += load_rd(21, 0xFFFF_FFFF_FFFF_FBFF) + [cfx2rc(HART_HA, 3, CG3_EXCP_CAUSE_MASK_RC, 21)]
    # install exception vectors for cfx_hart / cfx_time
    ins += load_rd(21, hmon_addr(OFF_HART_PROVIDER)) + [cfx2rc(HART_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    ins += load_rd(21, hmon_addr(OFF_TIME_PROVIDER)) + [cfx2rc(TIME_HA, 3, CG3_EXCP_VECTOR_RC, 21)]
    # clear cfx_power's cfxmem/cfxexe for all four modes (ROM fetch + RAM)
    ins += load_rd(20, 0)
    for cg in (0, 1, 2, 3):
        ins += [cfx2rc(63, cg, 1, 20), cfx2rc(63, cg, 3, 20)]
    need = (BOOTSTRAP_OFF - STAGE_OFF) // 4
    assert len(ins) <= need, (len(ins), need)
    ins += [swym()] * (need - len(ins))
    return ins


def bootstrap_rom(rom):
    return words_to_bytes(bootstrap_prefix()) + words_to_bytes(bootstrap_stage()) + rom


# ---------------------------------------------------------------------------
# Runtime cases
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc, icount_shift=None):
    def deco(fn):
        CASES.append((name, desc, fn, icount_shift))
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
    set_vector(a, TIME_HA, OFF_FH18)
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
    set_vector(a, HART_HA, OFF_FH15)
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
    set_vector(a, HART_HA, OFF_FH15)
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
      "icount: cycle/insn advance by >= N-4096 over a 100k-instruction loop",
      icount_shift=0)
def _cycle_insn_monotonic():
    N = 100000
    a = Asm()
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 5))
    a.emit(cfx2rd(HART_HA, HART_CG, 3, 6))
    delay_loop(a, 22, N, "main")
    a.emit(cfx2rd(HART_HA, HART_CG, 2, 7))
    a.emit(cfx2rd(HART_HA, HART_CG, 3, 8))
    okc, oki = "mono_c", "mono_i"
    a.emit(and_o(20, 5, 5))
    a.emit(add_si(20, N - 4096))
    a.emit(cmp_uo(21, 7, 20))
    a.br("nn", 21, 0, okc)
    a.emit(*exit_seq(0xE1))
    a.mark(okc)
    a.emit(and_o(20, 6, 6))
    a.emit(add_si(20, N - 4096))
    a.emit(cmp_uo(21, 8, 20))
    a.br("nn", 21, 0, oki)
    a.emit(*exit_seq(0xE2))
    a.mark(oki)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_ctrl_rw", "timer_ctrl writes accept bit0/bit1, ignore bit2")
def _timer_ctrl_rw():
    a = Asm()
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))          # cmp = all-ones (disabled)
    for val, rd in ((0, 5), (1, 6), (3, 7), (5, 8)):
        a.emit(*load_rd(22, val))
        a.emit(cfx2rc(HART_HA, HART_CG, 5, 22))
        a.emit(cfx2rd(HART_HA, HART_CG, 5, rd))
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {
        "exit": EXIT_PASS, "rd5": 0, "rd6": CTRL_ENABLE,
        "rd7": CTRL_ENABLE | CTRL_IMASK, "rd8": CTRL_ENABLE,
    }


@case("timer_istatus", "icount: ISTATUS = ENABLE && cmp!=~0 && time>=cmp", icount_shift=0)
def _timer_istatus():
    a = Asm()
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 22))          # now (ENABLE still 0)
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))          # cmp = now
    a.emit(*load_rd(21, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 21))
    a.emit(cfx2rd(HART_HA, HART_CG, 5, 5))
    a.emit(*load_rd(20, CTRL_ISTATUS))
    a.emit(and_o(20, 5, 20))
    ok = "ist_set"
    a.br("nz", 20, 0, ok)
    a.emit(*exit_seq(0xE1))
    a.mark(ok)
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))          # cmp = ~0 -> never matches
    a.emit(cfx2rd(HART_HA, HART_CG, 5, 6))
    a.emit(*load_rd(20, CTRL_ISTATUS))
    a.emit(and_o(20, 6, 20))
    ok2 = "ist_clear"
    a.br("z", 20, 0, ok2)
    a.emit(*exit_seq(0xE2))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_cmp_clears", "icount: writing a new cmp clears ISTATUS and re-arms",
      icount_shift=0)
def _timer_cmp_clears():
    a = Asm()
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 22))
    a.emit(add_si(22, 1000))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))
    a.emit(*load_rd(21, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 21))
    delay_loop(a, 22, 2000, "first")
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 22))
    a.emit(add_si(22, 100000))                       # fits imms18 (positive)
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))          # new cmp: ISTATUS -> 0
    a.emit(cfx2rd(HART_HA, HART_CG, 5, 5))
    a.emit(*load_rd(20, CTRL_ISTATUS))
    a.emit(and_o(20, 5, 20))
    ok = "cmp_ist_clear"
    a.br("z", 20, 0, ok)
    a.emit(*exit_seq(0xE1))
    a.mark(ok)
    delay_loop(a, 22, 2000, "second")                # 4000 ns << 1e6 ns
    ram_load(a, RAM_STATE + 0x18, 6)
    a.emit(*load_rd(20, 1))
    ok2 = "cmp_one"
    a.br("eq", 6, 20, ok2)
    a.emit(*exit_seq(0xE2))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_ones_disable", "icount: cmp=~0 + ENABLE=1 never matches", icount_shift=0)
def _timer_ones_disable():
    a = Asm()
    a.emit(*load_rd(22, ALL1))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))
    a.emit(*load_rd(21, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 21))
    delay_loop(a, 22, 2000, "ones")
    a.emit(cfx2rd(HART_HA, HART_CG, 5, 5))
    a.emit(*load_rd(20, CTRL_ISTATUS))
    a.emit(and_o(20, 5, 20))
    ok = "ones_ist"
    a.br("z", 20, 0, ok)
    a.emit(*exit_seq(0xE1))
    a.mark(ok)
    ram_load(a, RAM_STATE + 0x18, 6)
    ok2 = "ones_no_irq"
    a.br("z", 6, 0, ok2)
    a.emit(*exit_seq(0xE2))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_interrupt", "icount: expiry delivers TIMER (0x400, info 0) once",
      icount_shift=0)
def _timer_interrupt():
    a = Asm()
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 22))
    a.emit(add_si(22, 2000))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))
    a.emit(*load_rd(21, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 21))
    delay_loop(a, 22, 4000, "irq")
    ram_load(a, RAM_STATE + 0x18, 5)
    a.emit(*load_rd(20, 1))
    ok1 = "irq_count"
    a.br("eq", 5, 20, ok1)
    a.emit(*exit_seq(0xE1))
    a.mark(ok1)
    ram_load(a, RAM_STATE + 0x00, 6)
    a.emit(*load_rd(20, TIMER))
    ok2 = "irq_cid"
    a.br("eq", 6, 20, ok2)
    a.emit(*exit_seq(0xE2))
    a.mark(ok2)
    ram_load(a, RAM_STATE + 0x08, 7)
    ok3 = "irq_cinfo"
    a.br("z", 7, 0, ok3)
    a.emit(*exit_seq(0xE3))
    a.mark(ok3)
    a.emit(cfx2rd(HART_HA, HART_CG, 5, 8))
    a.emit(*load_rd(20, CTRL_ISTATUS))
    a.emit(and_o(20, 8, 20))
    ok4 = "irq_istatus"
    a.br("nz", 20, 0, ok4)
    a.emit(*exit_seq(0xE4))
    a.mark(ok4)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_imask_pending", "icount: IMASK defers TIMER into cg5 rc5 bit10",
      icount_shift=0)
def _timer_imask_pending():
    a = Asm()
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 22))
    a.emit(add_si(22, 1000))
    a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))
    a.emit(*load_rd(21, CTRL_ENABLE | CTRL_IMASK))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 21))
    delay_loop(a, 22, 3000, "masked")
    ram_load(a, RAM_STATE + 0x18, 5)
    ok1 = "imask_count0"
    a.br("z", 5, 0, ok1)
    a.emit(*exit_seq(0xE1))
    a.mark(ok1)
    a.emit(cfx2rd(HART_HA, HART_CG, 5, 6))
    a.emit(*load_rd(20, CTRL_ISTATUS))
    a.emit(and_o(20, 6, 20))
    ok2 = "imask_istatus"
    a.br("nz", 20, 0, ok2)
    a.emit(*exit_seq(0xE2))
    a.mark(ok2)
    a.emit(cfx2rd(HART_HA, 5, CG5_PENDING_RC, 7))
    a.emit(*load_rd(20, TIMER))
    a.emit(and_o(20, 7, 20))
    ok3 = "imask_pending"
    a.br("nz", 20, 0, ok3)
    a.emit(*exit_seq(0xE3))
    a.mark(ok3)
    a.emit(*load_rd(21, CTRL_ENABLE))
    a.emit(cfx2rc(HART_HA, HART_CG, 5, 21))          # release IMASK -> deliver
    delay_loop(a, 22, 2000, "unmasked")
    ram_load(a, RAM_STATE + 0x18, 8)
    a.emit(*load_rd(20, 1))
    ok4 = "imask_delivered"
    a.br("eq", 8, 20, ok4)
    a.emit(*exit_seq(0xE4))
    a.mark(ok4)
    a.emit(cfx2rd(HART_HA, 5, CG5_PENDING_RC, 9))
    a.emit(*load_rd(20, TIMER))
    a.emit(and_o(20, 9, 20))
    ok5 = "imask_pending_clear"
    a.br("z", 20, 0, ok5)
    a.emit(*exit_seq(0xE5))
    a.mark(ok5)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("timer_retrigger", "icount: one-shot timer can be re-armed (2 deliveries)",
      icount_shift=0)
def _timer_retrigger():
    a = Asm()
    for tag, want in (("first", 1), ("second", 2)):
        a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 22))
        a.emit(add_si(22, 1000))
        a.emit(cfx2rc(HART_HA, HART_CG, 4, 22))
        a.emit(*load_rd(21, CTRL_ENABLE))
        a.emit(cfx2rc(HART_HA, HART_CG, 5, 21))
        delay_loop(a, 22, 4000, tag)
        ram_load(a, RAM_STATE + 0x18, 5)
        a.emit(*load_rd(20, want))
        ok = "retrig_%s" % tag
        a.br("eq", 5, 20, ok)
        a.emit(*exit_seq(0xE1 if want == 1 else 0xE2))
        a.mark(ok)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("sbi_time_monotonic", "icount: SBI_TIME_GET advances with instruction count",
      icount_shift=0)
def _sbi_time_monotonic():
    N = 10000
    a = Asm()
    a.emit(trap(TIME_HA, 0))
    a.emit(and_o(5, 8, 8))
    delay_loop(a, 22, N // 2, "sbi_time")            # 2 insns/iter => N insns
    a.emit(trap(TIME_HA, 0))
    a.emit(and_o(6, 8, 8))
    a.emit(and_o(20, 5, 5))
    a.emit(add_si(20, N))
    a.emit(cmp_uo(21, 6, 20))
    ok = "sbi_time_delta"
    a.br("nn", 21, 0, ok)
    a.emit(*exit_seq(0xE1))
    a.mark(ok)
    a.emit(cfx2rd(TIME_HA, TIME_CG, 0, 7))
    a.emit(*load_rd(20, TIME_FREQ))
    ok2 = "sbi_time_freq"
    a.br("eq", 7, 20, ok2)
    a.emit(*exit_seq(0xE2))
    a.mark(ok2)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("sbi_hart_set_timer", "icount: SBI_HART_SET_TIMER arms and delivers TIMER",
      icount_shift=0)
def _sbi_hart_set_timer():
    a = Asm()
    a.emit(cfx2rd(TIME_HA, TIME_CG, 1, 21))
    a.emit(add_si(21, 2000))
    a.emit(and_o(16, 21, 21))
    a.emit(trap(HART_HA, 1))
    a.emit(and_o(5, 8, 8))                           # SBI return value
    ok1 = "sbi_st_ret"
    a.br("z", 5, 0, ok1)
    a.emit(*exit_seq(0xE1))
    a.mark(ok1)
    delay_loop(a, 22, 4000, "sbi_st")
    ram_load(a, RAM_STATE + 0x18, 6)
    a.emit(*load_rd(20, 1))
    ok2 = "sbi_st_count"
    a.br("eq", 6, 20, ok2)
    a.emit(*exit_seq(0xE2))
    a.mark(ok2)
    ram_load(a, RAM_STATE + 0x00, 7)
    a.emit(*load_rd(20, TIMER))
    ok3 = "sbi_st_cid"
    a.br("eq", 7, 20, ok3)
    a.emit(*exit_seq(0xE3))
    a.mark(ok3)
    a.emit(*exit_seq(EXIT_PASS))
    return build_rom(a.resolve(), HANDLERS), {"exit": EXIT_PASS}


@case("regress_unimpl_cfx", "cfx5 (cache) and cfx16 (llc) still raise CFXREG")
def _regress_unimpl_cfx():
    a = Asm()
    set_vector(a, 3, OFF_FH3)
    n = 0

    def fault(insn):
        nonlocal n
        n += 1
        idx = len(a.words)
        a.emit(insn)
        check_frame(a, hmon_addr(0) + idx * 4, n)

    fault(cfx2rd(5, 0, 0, 5))
    last_idx = len(a.words)
    a.emit(cfx2rd(16, 0, 0, 5))
    check_frame(a, hmon_addr(0) + last_idx * 4, 2)
    finish(a)
    return build_rom(a.resolve(), HANDLERS), {
        "exit": EXIT_PASS, "rd14": 0, "rd12": 2, "rd10": CFXREG,
        "rd11": hmon_addr(0) + last_idx * 4,
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
        for n, d, _fn, icount in CASES:
            print("%-26s %s%s" % (n, d, " [-icount]" if icount is not None else ""))
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
