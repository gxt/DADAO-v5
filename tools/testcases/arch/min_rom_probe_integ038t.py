#!/usr/bin/env python3
"""Min ROM probe for INTEG-038t: address-space Step 1 (PTBR / ptw_enable).

Spec sources (expectations derived by hand from spec/ + the frozen ADR, never
from the QEMU implementation):
  - spec/DADAO-12-SEE-主管系统运行环境.md §2.1/§2.2: CPU address 48 bits;
    addr[47:42] == 0 is the memory window (VA[41:0]); 1..63 are cfx internal
    spaces; single PTBR stores PPN[55:16] (64 KiB aligned, no valid bit);
    ptw_enable = 0 => high6=0 access/fetch => CFXMEM (current-mode cfx, never
    a pmem pass-through); write PTBR / enable=1 has no implicit TLB flush;
    reset PTBR = 0, ptw_enable = 0.
  - spec/DADAO-12 §4.5 cfx_ptw register table: cfx_ptw_enable (cg8 rc8),
    cfx_ptw_ptbr (cg9 rc0); pahi/pthi/perm entries are gone.
  - spec/DADAO-12 §5.2: reserved cfx (7-14, 19-61) plain ld/st => CFXMEM.
  - .tao/adr/adr-0039-address-space-ptbr-ptw.md D1–D8（Step 1）
  - spec/Machine-01-测试机运行环境.md §1.2/§3 (test-machine exit codes and the
    Step 1 implementation scope).
  - contracts/opcodes.yaml (ld/st/jump/set.zw/or.w/cfx2rd/cfx2rc encodings).

Not covered here (explicitly out of Step 1; see the task's completion notes):
  - PTE format / page-table walk / page faults: the walk is not implemented,
    so ptw_enable=1 is a BLOCKED case for Step 2; this probe only asserts the
    explicit fail-closed behaviour.
  - TLB invalidate semantics: the model has no TLB yet, so "no implicit
    invalidate" is a structural property of the register writes.

Observation channels:
  * register results -> QEMU `-d cpu` dump (last dump block, same convention as
    min_rom_probe_034t..049t).
  * fault codes -> process exit code (QEMU fault→exit mapping).
  * pass/fail -> semihosting SYS_EXIT (ADR-0020 D8).

Usage:
  min_rom_probe_integ038t.py                 # run all checks
  min_rom_probe_integ038t.py --only NAME     # run one check (used by run.sh --inject)
  min_rom_probe_integ038t.py --list

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
WORKDIR = "/tmp/opencode/INTEG-038t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0xFC00_0000_0000
RAM_SIZE = 16 * 1024 * 1024

# Exit codes (ADR-0004 D5.8 / Machine-01 §1.2)
EXIT_PASS = 0x00
EXIT_CFXMEM = 0x81
EXIT_UNMAPPED = 0x87

# Memory window address (high6 == 0) and reserved cfx address (cfxha 7).
VA_WINDOW = 0x0000_0000_1000
RESERVED_CFX = 7 << 42

# cfx_ptw register coordinates (DADAO-12 §4.5)
PTW_HA = 4
PTW_ENABLE_CG, PTW_ENABLE_RC = 8, 8
PTBR_CG, PTBR_RC = 9, 0

SEMIHOST_TAG = 0x3FF00
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = 0xFC00_00FF_F000

PTBR_MASK = 0x00FF_FFFF_FFFF_0000


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


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers=None):
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers or {}):
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(handlers[off])
    while len(rom) < 0x400:
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
    for n in range(1, 16):
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


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


# -- Step 1-a: ptw_enable = 0, high6 = 0 => CFXMEM (data) -------------------
@case("ptw_off_data", "ptw_enable=0 + high6=0 data access => CFXMEM 0x81")
def _ptw_off_data():
    prog = load_rb(3, VA_WINDOW) + [ld_o(5, 3, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


@case("ptw_off_store", "ptw_enable=0 + high6=0 store => CFXMEM 0x81")
def _ptw_off_store():
    prog = load_rb(3, VA_WINDOW) + load_rd(4, 0x1234) + [st_o(4, 3, 0)]
    prog += exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


# -- Step 1-a: fetch path is treated the same -------------------------------
@case("ptw_off_fetch", "ptw_enable=0 + high6=0 fetch => CFXMEM 0x81")
def _ptw_off_fetch():
    prog = load_rb(3, VA_WINDOW) + [jump_rrii(3, 0, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


# -- Step 1-e: reset values -------------------------------------------------
@case("ptbr_reset", "reset PTBR = 0 (register read + dump)")
def _ptbr_reset():
    prog = [cfx2rd(PTW_HA, PTBR_CG, PTBR_RC, 5)] + exit_seq(0x00)
    return build_rom(prog), {"exit": EXIT_PASS, "rd5": 0, "ptbr": 0}


@case("ptw_enable_reset", "reset ptw_enable = 0 (register read + dump)")
def _ptw_enable_reset():
    prog = [cfx2rd(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 5)] + exit_seq(0x00)
    return build_rom(prog), {"exit": EXIT_PASS, "rd5": 0, "ptw_enable": 0}


# -- Step 1 (single PTBR): write/readback, PPN[55:16] only ------------------
@case("ptbr_write", "PTBR write/readback keeps PPN[55:16], clears [15:0]")
def _ptbr_write():
    val = 0x00AB_CDEF_1234_5678
    prog = load_rd(17, val)
    prog += [cfx2rc(PTW_HA, PTBR_CG, PTBR_RC, 17)]
    prog += [cfx2rd(PTW_HA, PTBR_CG, PTBR_RC, 5)]
    prog += exit_seq(0x00)
    return build_rom(prog), {"exit": EXIT_PASS, "rd5": val & PTBR_MASK,
                             "ptbr": val & PTBR_MASK}


@case("ptbr_high_bits", "PTBR write clears [63:56] as well")
def _ptbr_high_bits():
    val = 0xFFAB_CDEF_1234_5678
    prog = load_rd(17, val)
    prog += [cfx2rc(PTW_HA, PTBR_CG, PTBR_RC, 17)]
    prog += [cfx2rd(PTW_HA, PTBR_CG, PTBR_RC, 5)]
    prog += exit_seq(0x00)
    exp = val & PTBR_MASK
    return build_rom(prog), {"exit": EXIT_PASS, "rd5": exp, "ptbr": exp}


# -- Step 1 (ptw_enable register): write/readback, 1-bit --------------------
@case("ptw_enable_write", "ptw_enable write/readback (1)")
def _ptw_enable_write():
    prog = load_rd(17, 1)
    prog += [cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 17)]
    prog += [cfx2rd(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 5)]
    prog += exit_seq(0x00)
    return build_rom(prog), {"exit": EXIT_PASS, "rd5": 1, "ptw_enable": 1}


H = ROM_BASE + 0x100
CFXREG = 1 << 2


# -- single PTBR / removed pahi-pthi: absent register => CFXREG --------------
def _absent_register_case(cg, rc):
    prog = load_rd(24, H) + [cfx2rc(PTW_HA, 3, 10, 24)]   # cfx4 hypv vector
    prog += [cfx2rd(PTW_HA, cg, rc, 5)]                    # absent register
    prog += exit_seq(0xEE)                                 # must not be reached
    return build_rom(prog, {0x100: exit_seq(0x52)}), {
        "exit": 0x52, "cid4": CFXREG, "syncn4": 1}


@case("no_second_ptbr", "single PTBR: cg9 rc1 does not exist => CFXREG")
def _no_second_ptbr():
    return _absent_register_case(PTBR_CG, 1)


@case("no_pthi", "pthi removed: cg10 rc0 does not exist => CFXREG")
def _no_pthi():
    return _absent_register_case(10, 0)


# -- Step 1-c: reserved cfx plain ld/st => CFXMEM ---------------------------
@case("reserved_ld", "reserved cfx (7) ld => CFXMEM 0x81")
def _reserved_ld():
    prog = load_rb(3, RESERVED_CFX) + [ld_o(5, 3, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


@case("reserved_st", "reserved cfx (7) st => CFXMEM 0x81")
def _reserved_st():
    prog = load_rb(3, RESERVED_CFX) + load_rd(4, 0x55) + [st_o(4, 3, 0)]
    prog += exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


@case("reserved_fetch", "reserved cfx (7) fetch => CFXMEM 0x81")
def _reserved_fetch():
    prog = load_rb(3, RESERVED_CFX) + [jump_rrii(3, 0, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


@case("reserved_19", "reserved cfx (19) ld => CFXMEM 0x81")
def _reserved_19():
    prog = load_rb(3, 19 << 42) + [ld_o(5, 3, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


# -- control: cfx internal (power/RAM) ld/st is unaffected ------------------
@case("cfx_internal_ld_st", "power/RAM direct ld/st still works")
def _cfx_internal_ld_st():
    prog = load_rb(3, RAM_BASE + 0x1000) + load_rd(4, 0xCAFEF00D)
    prog += [st_o(4, 3, 0), ld_o(5, 3, 0)] + exit_seq(0x00)
    return build_rom(prog), {"exit": EXIT_PASS, "rd5": 0xCAFEF00D}


# -- Step 1-b / BLOCKED: ptw_enable = 1 with no page walk -------------------
@case("ptw_on_fail_closed", "ptw_enable=1 high6=0: explicit fail-closed (no silent success)")
def _ptw_on_fail_closed():
    prog = load_rd(17, 1)
    prog += [cfx2rc(PTW_HA, PTW_ENABLE_CG, PTW_ENABLE_RC, 17)]
    prog += load_rb(3, VA_WINDOW) + [ld_o(5, 3, 0)]
    prog += exit_seq(0xEE)
    return build_rom(prog), {"exit": 1, "stderr_has": "page-table walk"}


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
                if k == "stderr_has":
                    if v not in err:
                        diffs.append("stderr lacks %r" % v)
                    continue
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
            print("%-24s %s" % (n, d))
        return 0

    names = [args.only] if args.only else [n for n, _, _ in CASES]
    failed = 0
    for n in names:
        ok, why, exp = run_case(n)
        if ok:
            print("PASS %-24s %s" % (n, why))
        else:
            failed += 1
            print("FAIL %-24s %s (exp=%r)" % (n, why, exp))
    print("%d/%d passed" % (len(names) - failed, len(names)))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
