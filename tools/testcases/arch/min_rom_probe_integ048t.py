#!/usr/bin/env python3
"""INTEG-048t probe: `cfx_<name>_hypv_cg_reg_deleg` enforcement (supv only).

Expectations are derived by hand from
  - spec/DADAO-13 §1 (cg3 `rc12` = `cfx_<cfxname>_hypv_cg_reg_deleg`, reset
    all-ones, RW, bit3 hardware-fixed 1, bit=0 allows supv, bit=1 denies);
  - spec/DADAO-12 §3/§4/§5 (per-cfx cg0-cg7 register rows, cause ids, the
    exception-entry flow; the monitor of the current run mode receives
    `CFXPERM` = 1<<7, `CFXREG` = 1<<2);
  - .tao/tasks/integ/INTEG-048t-*.md §已裁定语义 R1-R6 (user rulings
    2026-10-31): rejection = `CFXPERM` including cg3 (no cg3 exception),
    bitmap covers all 64 cg (bit index = cg number), no self exemption,
    hypv is not constrained, user/jail keep the two-axis model, and the
    firmware convention of opening a whole cfx with `cg3 rc12 = 0x8`;
  - ADR-0045 D1/D2/D6 (two-axis masks, CFXPERM to the current-mode monitor).
Not from the QEMU implementation.

Probe layout (one ROM per case, `-bios` 64 KiB window at 0xffff_ffff_0000):
  * reset runs power (cfx63/hypv); a 2-instruction prefix hands over to
    hmon (cfx3/hypv) exactly like INTEG-044t/045t (hmon is the only cfx that
    power may trap to at reset);
  * the hmon body installs the probe base (probe-only, never firmware
    policy): cfx_power cfxexe rows for the body fetch, the cfx_smon supv
    monitor that receives `CFXPERM` (running in hypv so it can read cg5),
    and cfx_smon supv cfxmem bit0 for the semihosting block (see below);
    then per-case deleg / cfxreg vectors and `trap` into supv (or user);
  * observation: the last `-d cpu` dump block (rd values, cfx cause frames,
    cfx mask rows) plus the SYS_EXIT status.

The semihosting argument block lives in **cfx_smon SRAM** (0x0bff_0000_0ff0):
the RAM window is partition 63 (power), so a supv store there would need
`cfx_power cfxmem` bit0/bit2 - exactly the bits the power cases assert stay
closed.  The handler runs as cfx2 (self => cfx axis bypassed) and the supv
body gets cfx2 supv cfxmem bit0 only; that keeps every power case's
`CFX63 M2 MEMMASK` untouched (0xffff_ffff_ffff_fff7).

Every case compares exact values, so each has a reachable FAIL path (the gate
removed / the mask opened / bit3 not forced change the observed value).

Usage:
  min_rom_probe_integ048t.py [--qemu PATH] [--only NAME] [--list]
Exit code: 0 iff every requested case passed.
"""

import argparse
import os
import re
import struct
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
QEMU = DEFAULT_QEMU
WORKDIR = "/tmp/opencode/INTEG-048t/probe"
TIMEOUT = 20

ROM_BASE = 0xFFFF_FFFF_0000

# ROM offsets (bytes).  The hmon body starts right after the power prefix;
# the supv/user bodies and the two handler slots are placed far enough apart.
BODY_OFF = 0x024       # hmon (cfx3/hypv) setup body
SUPV_OFF = 0x200       # supv body (cfx0, or cfx2 for self/power cases)
USER_OFF = 0x300       # user body (cfx0)
FAULT_OFF = 0x380      # generic fault slot (cfx0 user-row vector)
HAND_OFF = 0x600       # CFXPERM handler (cfx_smon supv vector, runs hypv)
EXIT_OFF = 0x780       # split exit slot (ends the body TB before the dump)
SENTINEL_OFF = 0x1000  # power BootROM word read/written by the power cases
SENTINEL = 0x1122_3344_5566_7788
IMAGE_END = SENTINEL_OFF + 8

POWER_ADDR = ROM_BASE + SENTINEL_OFF   # 0xffff_ffff_1000 (page 2 of -bios)
SEMI_BLOCK = 0x0BFF_0000_0FF0          # cfx_smon SRAM (cfx2)

# Run modes (DADAO-12 §1)
USER, JAIL, SUPV, HYPV = 0, 1, 2, 3
# Cause ids (DADAO-12 §4 monitor exception table)
CFXREG = 1 << 2
CFXPERM = 1 << 7
ALL1 = (1 << 64) - 1

# Reset mask rows (ADR-0045 D4): everything but source hmon (cfx3) is denied.
MASK_DEFAULT = 0xFFFF_FFFF_FFFF_FFF7
MASK_HMON = 0x7FFF_FFFF_FFFF_FFF7

DELEG_OPEN = 0x0000_0000_0000_0008     # bit3 (fixed 1) only => all cg allowed
POWER_CFXMEM_OPEN = 0xFFFF_FFFF_FFFF_FFF3  # bit2 (source smon) cleared

# Semihosting SYS_EXIT (ADR-0020 D8)
SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026

# ---------------------------------------------------------------------------
# Encoders (contracts/opcodes.yaml)
# ---------------------------------------------------------------------------

def set_zw_rd(rd, wp, imm): return (0x4C << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)
def or_w_rd(rd, wp, imm):   return (0x48 << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)
def set_zw_rb(rb, wp, imm): return (0x4E << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)
def or_w_rb(rb, wp, imm):   return (0x4A << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)
def st_o(rd, rb, off):      return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)
def cfx2rd(ha, cg, rc, rd): return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def cfx2rc(ha, cg, rc, rd): return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def trap(ha, immu18):       return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
def jump_iiii(imms24):      return (0x70 << 24) | (imms24 & 0xFFFFFF)
def swym():                 return 0x47880000


def ld_o(rd, rb, off):
    imm = off & 0xFFF
    return (0x20 << 24) | (rd << 18) | (rb << 12) | imm


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
    """SYS_EXIT with the argument block in cfx_smon SRAM (see module doc)."""
    return ([set_zw_rb(16, 0, 0x0FF0), or_w_rb(16, 2, 0x0BFF)]
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(body, sections):
    """power prefix at 0, `body` at BODY_OFF, `sections` = {offset: words}."""
    rom = bytearray(words_to_bytes(bootstrap_prefix()))
    if len(rom) > BODY_OFF:
        raise AssertionError("power prefix overlaps BODY_OFF (%d bytes)" % len(rom))
    while len(rom) < BODY_OFF:
        rom += words_to_bytes([swym()])
    rom += words_to_bytes(body)
    if len(rom) > min([off for off in sections] + [SENTINEL_OFF]):
        raise AssertionError("hmon body overlaps the next section (0x%x)" % len(rom))
    for off in sorted(sections):
        if len(rom) > off:
            raise AssertionError("section at 0x%x overlaps (len 0x%x)" % (off, len(rom)))
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(sections[off])
    if len(rom) > SENTINEL_OFF:
        raise AssertionError("code overlaps the power sentinel (0x%x)" % len(rom))
    while len(rom) < SENTINEL_OFF:
        rom += words_to_bytes([swym()])
    rom += struct.pack(">Q", SENTINEL)
    if len(rom) != IMAGE_END:
        raise AssertionError("bad image size %d" % len(rom))
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
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    with open(lp) as f:
        log = f.read()
    return rc, log


def lasthex(log, pat):
    m = None
    for x in re.finditer(pat, log):
        m = x
    return int(m.group(1), 16) if m else None


def observe(log):
    """Extract the observations from the LAST dump block.

    Anchors: SYNCN must be preceded by a space (ASYNCN contains "SYNCN");
    the cause frame is on the `CFXxx PREVM:` line.
    """
    o = {}
    o["mode"] = None
    m = None
    for x in re.finditer(r"^MODE: (\d+)", log, re.MULTILINE):
        m = x
    if m:
        o["mode"] = int(m.group(1), 10)
    for n in range(5, 56):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    for ha in (0, 1, 2, 3, 4, 17, 63):
        t = "CFX%02d" % ha
        o["cid:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]* CID:([0-9a-f]+)")
        o["cip:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*CIP:([0-9a-f]+)")
        o["cinfo:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*CINFO:([0-9a-f]+)")
        o["syncn:%d" % ha] = lasthex(log, t + r" ID:[^\n]*? SYNCN:([0-9a-f]+)")
        for md in range(4):
            o["memmask:%d:%d" % (ha, md)] = lasthex(
                log, t + r" M%d SWMODE:[^\n]* MEMMASK:([0-9a-f]+)" % md)
            o["regmask:%d:%d" % (ha, md)] = lasthex(
                log, t + r" M%d SWMODE:[^\n]* REGMASK:([0-9a-f]+)" % md)
    return o


# ---------------------------------------------------------------------------
# Case model + program builders
# ---------------------------------------------------------------------------

CASES = []   # (name, desc, builder) ; builder() -> [(label, rom, expected)]


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def bootstrap_prefix():
    """power(cfx63/hypv) -> hmon(cfx3/hypv): hmon is power's only trap target."""
    return load_rd(22, ROM_BASE + BODY_OFF) + [cfx2rc(3, 3, 10, 22), trap(3, 0)]


def probe_base():
    """Probe-only base installed by hmon/hypv (never firmware policy).

    * cfx_power cfxexe rows: supv body as cfx0 (bit0) / cfx2 (bit2), user body
      as cfx0 (bit0), handler as cfx2 in hypv (bit2).  cfx_power cfxmem is
      deliberately NOT touched (the power cases assert its reset value).
    * cfx_smon supv monitor = CFXPERM handler, entered in hypv (so it may read
      cfx_smon cg5); cause/switch masks opened.
    * cfx_smon supv cfxmem bit0 = 0: lets the supv cfx0 body place the
      semihosting block in cfx_smon SRAM without opening power's cfxmem.
    """
    p = []
    p += load_rd(20, 0xFFFF_FFFF_FFFF_FFF2) + [cfx2rc(63, SUPV, 3, 20)]
    p += load_rd(20, 0xFFFF_FFFF_FFFF_FFF6) + [cfx2rc(63, USER, 3, 20)]
    p += load_rd(20, 0xFFFF_FFFF_FFFF_FFF3) + [cfx2rc(63, HYPV, 3, 20)]
    p += load_rd(22, ROM_BASE + HAND_OFF) + [cfx2rc(2, SUPV, 10, 22)]
    p += load_rd(22, HYPV) + [cfx2rc(2, SUPV, 8, 22)]
    p += load_rd(22, 0) + [cfx2rc(2, SUPV, 11, 22)]
    p += load_rd(22, 0) + [cfx2rc(2, SUPV, 9, 22)]
    p += load_rd(20, 0xFFFF_FFFF_FFFF_FFFE) + [cfx2rc(2, SUPV, 1, 20)]
    p += load_rd(20, 0xFFFF_FFFF_FFFF_FFFE) + [cfx2rc(2, USER, 1, 20)]
    return p


def set_deleg(cfxha, value):
    """hmon (cfx3/hypv) writes cfx_<name>_hypv_cg_reg_deleg (cg3 rc12)."""
    return load_rd(20, value) + [cfx2rc(cfxha, 3, 12, 20)]


def open_supv_cfxreg(cfxha, src):
    """hmon clears the supv cfxreg mask bit of `src` (isolates the deleg axis)."""
    return load_rd(20, ALL1 & ~(1 << src)) + [cfx2rc(cfxha, SUPV, 2, 20)]


def open_user_cfxreg(cfxha, src):
    return load_rd(20, ALL1 & ~(1 << src)) + [cfx2rc(cfxha, USER, 2, 20)]


def read_supv_cfxreg(cfxha, rd):
    """hmon reads the supv cfxreg row back (isolation evidence for rd24)."""
    return [cfx2rd(cfxha, SUPV, 2, rd)]


def open_hypv_cfxreg(cfxha, src):
    """hmon clears the hypv-row cfxreg mask bit of `src` (handler readback)."""
    return load_rd(20, ALL1 & ~(1 << src)) + [cfx2rc(cfxha, HYPV, 2, 20)]


def set_power_cfxmem(value):
    return load_rd(20, value) + [cfx2rc(63, SUPV, 1, 20)]


def enter_supv_cfx0():
    """trap cfx0 from hmon: cfx0 hypv row vector/switch = supv body."""
    p = load_rd(22, ROM_BASE + SUPV_OFF) + [cfx2rc(0, 3, 10, 22)]
    p += load_rd(22, SUPV) + [cfx2rc(0, 3, 8, 22)]
    p += load_rd(22, 0) + [cfx2rc(0, 3, 9, 22)]
    p += load_rd(22, 0) + [cfx2rc(0, 3, 11, 22)]
    p += [trap(0, 0)]
    return p


def enter_supv_cfx2():
    """trap cfx_smon from hmon: cfx_smon hypv row vector/switch = supv body."""
    p = load_rd(22, ROM_BASE + SUPV_OFF) + [cfx2rc(2, 3, 10, 22)]
    p += load_rd(22, SUPV) + [cfx2rc(2, 3, 8, 22)]
    p += [trap(2, 0)]
    return p


def enter_user_cfx0():
    """trap cfx0 from hmon: cfx0 hypv row vector = user body, switch = user."""
    p = load_rd(22, ROM_BASE + USER_OFF) + [cfx2rc(0, 3, 10, 22)]
    p += load_rd(22, USER) + [cfx2rc(0, 3, 8, 22)]
    p += [trap(0, 0)]
    return p


def handler(extra=()):
    """CFXPERM handler: record cause frame, optional readback, exit 0xEE."""
    h = [cfx2rd(2, 5, 2, 20), cfx2rd(2, 5, 3, 21), cfx2rd(2, 5, 4, 22)]
    h += list(extra)
    h += exit_seq(0xEE)
    return h


def fault_slot(code):
    return exit_seq(code)


def info_rd(ha, cg, rc, rd):
    return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd


def info_rc(ha, cg, rc, rd):
    return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd


def one(rom, exp):
    return [("", rom, exp)]


# -- 1-5: positive cases under deleg = 0x8 --------------------------------

PTW_PTBR = 0x0000_1234_5678_0000


@case("open_ptw_cg9", "deleg=0x8: supv cfx_ptw cg9 rc0 (PTBR) write/read")
def _open_ptw_cg9():
    body = load_rd(20, PTW_PTBR) + [cfx2rc(4, 9, 0, 20)]
    body += [cfx2rd(4, 9, 0, 10)]
    body += exit_seq(0x00)
    prog = probe_base() + set_deleg(4, DELEG_OPEN) + open_supv_cfxreg(4, 0)
    prog += enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd10": PTW_PTBR})


@case("open_ptw_cg8", "deleg=0x8: supv cfx_ptw cg8 rc8 (ptw_enable) 1 -> 0")
def _open_ptw_cg8():
    body = load_rd(20, 1) + [cfx2rc(4, 8, 8, 20)]
    body += [cfx2rd(4, 8, 8, 10)]
    body += [cfx2rc(4, 8, 8, 0)] + [cfx2rd(4, 8, 8, 11)]
    body += exit_seq(0x00)
    prog = probe_base() + set_deleg(4, DELEG_OPEN) + open_supv_cfxreg(4, 0)
    prog += enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd10": 1, "rd11": 0})


@case("open_pmem_cg15", "deleg=0x8: supv cfx_pmem cg15 rc4 (dma_status) read")
def _open_pmem_cg15():
    body = [cfx2rd(17, 15, 4, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(17, DELEG_OPEN) + open_supv_cfxreg(17, 0)
    prog += enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    # The pre-deleg implementation answered CFXREG (cg15 has no cfx_reg_ptr
    # entry); a CFXPERM or a CFXREG would both leave exit 0xEE.
    return one(rom, {"exit": 0x00, "rd10": 0})


@case("open_smon_cg5_self", "deleg=0x8, source=target=cfx_smon: supv reads cg5 rc2")
def _open_smon_cg5_self():
    body = [cfx2rd(2, 5, 2, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(2, DELEG_OPEN) + enter_supv_cfx2()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd10": 1})   # cause_id = CFXTRAP (1)


@case("open_cg7", "deleg=0x8: supv cfx_ptw cg7 rc0 (space desc) read => 0, no CFXPERM")
def _open_cg7():
    # cg7 is a read-only space description (DADAO-12 §3.8): a write would be
    # CFXREG regardless of delegation, so the gate is proved by a read of
    # cfx_ptw space[0]; cfx_ptw has no internal space => 0.
    body = [cfx2rd(4, 7, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(4, DELEG_OPEN) + open_supv_cfxreg(4, 0)
    prog += enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd10": 0})


# -- 6/8: closed cfx (hmon) with the 0x8 control ---------------------------

@case("closed_hmon_cg0", "cfx_hmon deleg=~0: supv cg0 rc0 => CFXPERM; 0x8 => ok")
def _closed_hmon_cg0():
    out = []
    for label, deleg in (("closed", ALL1), ("open", DELEG_OPEN)):
        body = [cfx2rd(3, 0, 0, 10)] + exit_seq(0x00)
        prog = probe_base() + set_deleg(3, deleg) + open_supv_cfxreg(3, 0)
        prog += read_supv_cfxreg(3, 24) + enter_supv_cfx0()
        rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
        if deleg == ALL1:
            exp = {"exit": 0xEE, "cid:2": CFXPERM,
                   "cinfo:2": info_rd(3, 0, 0, 10), "cip:2": ROM_BASE + SUPV_OFF}
        else:
            exp = {"exit": 0x00, "rd10": MASK_HMON}
        exp["rd24"] = ALL1 & ~1
        out.append((label, rom, exp))
    return out


@case("closed_hmon_cg8", "cfx_hmon deleg=~0: supv cg8 rc1 => CFXPERM (bitmap >= 8)")
def _closed_hmon_cg8():
    body = [cfx2rd(3, 8, 1, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(3, ALL1) + open_supv_cfxreg(3, 0)
    prog += read_supv_cfxreg(3, 24) + enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rd(3, 8, 1, 10),
                     "cip:2": ROM_BASE + SUPV_OFF,
                     "rd24": ALL1 & ~1})


# -- 7/7a-7f: cfx_power ---------------------------------------------------

@case("closed_power_cg4", "cfx_power deleg=~0: supv cg4 rc0 => CFXPERM")
def _closed_power_cg4():
    body = [cfx2rd(63, 4, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(63, ALL1) + open_supv_cfxreg(63, 2)
    prog += read_supv_cfxreg(63, 24) + enter_supv_cfx2()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rd(63, 4, 0, 10),
                     "cip:2": ROM_BASE + SUPV_OFF,
                     "rd24": ALL1 & ~(1 << 2)})


@case("open_power_bootrom", "power cfxmem bit2=0: supv cfx2 ld.o [0xffff_ffff_1000]")
def _open_power_bootrom():
    # The jump ends the body translation block, so the loaded value is part of
    # the next dump block (the exit slot); a single TB would only dump the
    # pre-load state.
    body = load_rb(4, POWER_ADDR) + [ld_o(20, 4, 0)]
    body.append(jump_iiii((EXIT_OFF - SUPV_OFF) // 4 - len(body)))
    prog = probe_base() + set_power_cfxmem(POWER_CFXMEM_OPEN)
    prog += enter_supv_cfx2()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler(),
                           EXIT_OFF: exit_seq(0x00)})
    return one(rom, {"exit": 0x00, "rd20": SENTINEL})


@case("closed_power_bootrom", "power cfxmem bit2=1: same ld => CFXPERM")
def _closed_power_bootrom():
    body = load_rb(4, POWER_ADDR) + [ld_o(20, 4, 0)] + exit_seq(0x00)
    prog = probe_base() + set_power_cfxmem(MASK_DEFAULT)
    prog += enter_supv_cfx2()
    ld_idx = len(load_rb(4, POWER_ADDR))
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM, "cinfo:2": POWER_ADDR,
                     "cip:2": ROM_BASE + SUPV_OFF + 4 * ld_idx})


@case("power_bootrom_store", "power cfxmem bit2=0: st.o boot ROM => ILLI (exit 0x88)")
def _power_bootrom_store():
    body = load_rb(4, POWER_ADDR) + [st_o(20, 4, 0)] + exit_seq(0x00)
    prog = probe_base() + set_power_cfxmem(POWER_CFXMEM_OPEN)
    prog += enter_supv_cfx2()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    # ADR-0004 D5.6: ROM is read-only; the store never reaches a handler, the
    # test machine reports ILLI (0x80 | ... -> DADAO_EXIT_ILLI = 0x88).
    return one(rom, {"exit": 0x88})


@case("power_control_write", "default axes: supv write cfx_power cg2 rc1 => CFXPERM")
def _power_control_write():
    body = [cfx2rc(63, 2, 1, 0)] + exit_seq(0x00)
    prog = probe_base() + enter_supv_cfx2()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rc(63, 2, 1, 0),
                     "cip:2": ROM_BASE + SUPV_OFF,
                     "memmask:63:2": MASK_DEFAULT})


@case("power_cg7_closed", "deleg=~0 (cfxreg isolated): supv cfx_power cg7 => CFXPERM")
def _power_cg7_closed():
    body = [cfx2rd(63, 7, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(63, ALL1) + open_supv_cfxreg(63, 2)
    prog += read_supv_cfxreg(63, 24) + enter_supv_cfx2()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rd(63, 7, 0, 10),
                     "cip:2": ROM_BASE + SUPV_OFF,
                     "rd24": ALL1 & ~(1 << 2)})


@case("no_power_full_open", "0x8 for ptw/pmem/smon only: power stays closed")
def _no_power_full_open():
    body = [cfx2rd(63, 4, 0, 10)] + exit_seq(0x00)
    prog = probe_base()
    prog += set_deleg(4, DELEG_OPEN) + set_deleg(17, DELEG_OPEN)
    prog += set_deleg(2, DELEG_OPEN) + open_supv_cfxreg(63, 2)
    prog += read_supv_cfxreg(63, 24) + enter_supv_cfx2()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rd(63, 4, 0, 10),
                     "cip:2": ROM_BASE + SUPV_OFF,
                     "rd24": ALL1 & ~(1 << 2),
                     "memmask:63:2": MASK_DEFAULT})


# -- 9-13: cg3 ------------------------------------------------------------

@case("cg3_supv_perm_rd", "supv read of cg3 => CFXPERM (not CFXREG) even at deleg=0x8")
def _cg3_supv_perm_rd():
    body = [cfx2rd(4, 3, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(4, DELEG_OPEN) + open_supv_cfxreg(4, 0)
    prog += read_supv_cfxreg(4, 24) + enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rd(4, 3, 0, 10),
                     "cip:2": ROM_BASE + SUPV_OFF,
                     "rd24": ALL1 & ~1})


@case("cg3_supv_perm_wr", "supv write of cg3 rc12 => CFXPERM; deleg unchanged")
def _cg3_supv_perm_wr():
    bad = 0xFFFF_FFFF_FFFF_FFF0     # bit3=0; a wrong write would read 0x...FFF8
    body = load_rd(20, bad) + [cfx2rc(17, 3, 12, 20)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(17, DELEG_OPEN) + open_supv_cfxreg(17, 0)
    prog += read_supv_cfxreg(17, 24) + open_hypv_cfxreg(17, 2)
    prog += enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body,
                           HAND_OFF: handler([cfx2rd(17, 3, 12, 23)])})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rc(17, 3, 12, 20),
                     "cip:2": ROM_BASE + SUPV_OFF + 16,
                     "rd23": DELEG_OPEN, "rd24": ALL1 & ~1})


@case("cg3_bit3_locked", "hypv writes deleg=0: reads 0x8, supv cg3 still CFXPERM")
def _cg3_bit3_locked():
    body = [cfx2rd(4, 3, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(4, 0) + open_supv_cfxreg(4, 0)
    prog += read_supv_cfxreg(4, 24) + open_hypv_cfxreg(4, 2)
    prog += enter_supv_cfx0()
    rom = build_rom(prog, {SUPV_OFF: body,
                           HAND_OFF: handler([cfx2rd(4, 3, 12, 23)])})
    return one(rom, {"exit": 0xEE, "cid:2": CFXPERM,
                     "cinfo:2": info_rd(4, 3, 0, 10),
                     "cip:2": ROM_BASE + SUPV_OFF,
                     "rd23": DELEG_OPEN, "rd24": ALL1 & ~1})


@case("cg3_hypv_allowed", "hypv reads/writes cfx_ptw cg3 (legal register group)")
def _cg3_hypv_allowed():
    body = [cfx2rd(4, 3, 0, 10)]
    body += load_rd(20, 0xFFFF_FFFF_FFFF_CAFE) + [cfx2rc(4, 3, 12, 20)]
    body += [cfx2rd(4, 3, 12, 11)] + exit_seq(0x00)
    prog = probe_base() + body
    rom = build_rom(prog, {HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd10": MASK_DEFAULT,
                     "rd11": 0xFFFF_FFFF_FFFF_CAFE})


@case("bit3_forced", "hypv writes 0 / 0x...fff7 to deleg: bit3 reads back 1")
def _bit3_forced():
    body = [cfx2rc(4, 3, 12, 0)] + [cfx2rd(4, 3, 12, 10)]
    body += load_rd(20, MASK_DEFAULT) + [cfx2rc(4, 3, 12, 20)]
    body += [cfx2rd(4, 3, 12, 11)] + exit_seq(0x00)
    prog = probe_base() + body
    rom = build_rom(prog, {HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd10": DELEG_OPEN, "rd11": ALL1})


# -- 14-17: self / hypv / user -------------------------------------------

@case("self_not_exempt", "source=target=cfx_smon: deleg=~0 => CFXPERM; 0x8 => ok")
def _self_not_exempt():
    out = []
    for label, deleg in (("closed", ALL1), ("open", DELEG_OPEN)):
        body = [cfx2rd(2, 5, 2, 10)] + exit_seq(0x00)
        prog = probe_base() + set_deleg(2, deleg) + enter_supv_cfx2()
        rom = build_rom(prog, {SUPV_OFF: body, HAND_OFF: handler()})
        if deleg == ALL1:
            exp = {"exit": 0xEE, "cid:2": CFXPERM,
                   "cinfo:2": info_rd(2, 5, 2, 10),
                   "cip:2": ROM_BASE + SUPV_OFF}
        else:
            exp = {"exit": 0x00, "rd10": 1}
        out.append((label, rom, exp))
    return out


@case("hypv_unaffected", "deleg=~0 but hypv reads cfx_ptw cg2 rc0 => ok")
def _hypv_unaffected():
    body = [cfx2rd(4, 2, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(4, ALL1) + body
    rom = build_rom(prog, {HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd10": MASK_DEFAULT})


@case("user_unaffected", "deleg=~0: user reads cfx_ptw cg0 rc0 => ok (no deleg)")
def _user_unaffected():
    body = [cfx2rd(4, 0, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(4, ALL1) + open_user_cfxreg(4, 0)
    prog += enter_user_cfx0()
    rom = build_rom(prog, {USER_OFF: body, HAND_OFF: handler(),
                           FAULT_OFF: fault_slot(0xCC)})
    return one(rom, {"exit": 0x00, "rd10": MASK_DEFAULT, "mode": 0})


@case("user_cg3_cfxreg", "user reads cfx0 cg3 => CFXREG (deleg does not apply)")
def _user_cg3_cfxreg():
    body = [cfx2rd(0, 3, 0, 10)] + exit_seq(0x00)
    prog = probe_base() + set_deleg(4, ALL1)
    # cfx0 user-row vector -> fault slot; the entry mode (user row switch) is
    # left at its reset value (supv), so the fault slot exits in supv.
    prog += load_rd(22, ROM_BASE + FAULT_OFF) + [cfx2rc(0, USER, 10, 22)]
    prog += load_rd(22, 0) + [cfx2rc(0, USER, 11, 22)]
    prog += enter_user_cfx0()
    rom = build_rom(prog, {USER_OFF: body, HAND_OFF: handler(),
                           FAULT_OFF: fault_slot(0xCC)})
    return one(rom, {"exit": 0xCC, "cid:0": CFXREG,
                     "cinfo:0": info_rd(0, 3, 0, 10),
                     "cip:0": ROM_BASE + USER_OFF})


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_case(name):
    for n, d, fn in CASES:
        if n != name:
            continue
        ok = True
        details = []
        for label, rom, exp in fn():
            rc, log = run(rom)
            tag = name + (":" + label if label else "")
            if rc is None:
                ok = False
                details.append("%s TIMEOUT" % tag)
                continue
            obs = observe(log)
            obs["exit"] = rc
            diffs = []
            for k, v in exp.items():
                av = obs.get(k)
                if av != v:
                    diffs.append("%s exp=0x%x got=%s" % (
                        k, v, ("0x%x" % av) if av is not None else "None"))
            if diffs:
                ok = False
                details.append("%s %s" % (tag, "; ".join(diffs)))
        return ok, ("ok" if ok else " | ".join(details))
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
            print("%-24s %s" % (n, d))
        return 0

    if not os.path.isfile(QEMU):
        print("[FAIL] QEMU binary not found: %s" % QEMU)
        return 2

    selected = [(n, d) for (n, d, _) in CASES if args.only is None or n == args.only]
    if not selected:
        print("[FAIL] no case named %r" % args.only)
        return 1

    all_ok = True
    for name, desc in selected:
        passed, detail = run_case(name)
        print("[%s] %-24s %s -> %s" % ("PASS" if passed else "FAIL", name, desc, detail))
        if not passed:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
