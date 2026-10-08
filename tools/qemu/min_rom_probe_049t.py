#!/usr/bin/env python3
"""Min ROM probe for QEMU-049t: RAM@0 dual mapping (C1 step1) + out-of-range
access/fetch fault semantics (CFXMEM vs the test-machine unmapped convention).

Spec sources (expectations derived by hand from spec/ + ADRs, never from the
QEMU implementation):
  - spec/Machine-01-测试机运行环境.md §1.1 (internal-address-space split:
    RAM@0 0x0000_0000_0000 / legacy RAM 0xffff_0000_0000 16 MiB / legacy MMIO
    halt device / boot ROM; C1 step1 dual mapping) and §1.2 (out-of-range
    access AND fetch both fault; CFXMEM(0x81) vs test-machine unmapped(0x87)).
  - .tao/adr/adr-0020-see-semihosting.md D15 and adr-0004-test-machine.md
    R3 (RAM base -> all zero; C1 two-step) + D5.8 (frozen fault-code table:
    0x81 reserved for CFXMEM = 0x80 | (1<<1); 0x87 = unmapped convention).
  - spec/DADAO-12-SEE-主管系统运行环境.md §2.1 (cfxha = addr[47:42]; illegal
    internal-address-space access => CFXMEM).
  - contracts/opcodes.yaml (ld.o/st.o/jump/set.zw/or.w encodings).

Routing implemented by QEMU-049t (ADR-0020 D15):
  * address inside the umon segment (cfxha 0) but outside RAM@0 => CFXMEM 0x81
    (both data access and instruction fetch).
  * any other unmapped address (incl. the legacy power segment, cfxha 63)
    => unmapped 0x87 (historical M1-M4 convention).

Observation channels:
  * register results / mapped reads -> QEMU `-d cpu` dump (parses the LAST
    dump block; same convention as min_rom_probe_034t..044t).
  * fault codes -> process exit code via QEMU's fault mapping; normal pass/fail
    -> semihosting SYS_EXIT (ADR-0020 D8; replaces the legacy MMIO halt device).

Usage:
  min_rom_probe_049t.py                 # run all checks
  min_rom_probe_049t.py --only NAME     # run one check (used by run.sh --inject)
  min_rom_probe_049t.py --list

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import re
import struct
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
QEMU = DEFAULT_QEMU
WORKDIR = "/tmp/opencode/QEMU-049t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
RAM0_BASE = 0x0000_0000_0000
RAM0_SIZE = 16 * 1024 * 1024          # 16 MiB (QEMU-049t decision)
OLD_RAM_BASE = 0xFFFF_0000_0000
OLD_RAM_SIZE = 16 * 1024 * 1024

# Exit codes (ADR-0004 D5.8 + ADR-0020 D15)
EXIT_PASS = 0x00
EXIT_CFXMEM = 0x81
EXIT_UNMAPPED = 0x87

# Out-of-range addresses
CFX0_OOB = RAM0_BASE + RAM0_SIZE      # 0x0100_0000, cfxha 0, outside RAM@0
CFX63_OOB = 0xFC00_0000_0000          # cfxha 63 (power), unmapped


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


def ld_o(rd, rb, off):   return _rrii(0x20, rd, rb, off)
def st_o(rd, rb, off):   return _rrii(0x21, rd, rb, off)
def jump_rrii(rb, rd, off): return _rrii(0x71, rb, rd, off)
def jump_iiii(imms24):   return (0x70 << 24) | (imms24 & 0xFFFFFF)
def trap(ha, immu18):    return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)


def swym():              return 0x77880000


# Semihosting SYS_EXIT (ADR-0020 D8: SYS_EXIT replaces the legacy MMIO halt device).
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = 0xFFFF_00FF_F000       # argument block {reason, code}, in RAM


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
    """Report `code` via semihosting SYS_EXIT (ADR-0020 D8) -> host $?.

    The leading no-op `jump` ends the current TB so the last `-d cpu` dump (the
    probe's observation channel) captures the caller's state (e.g. the `ld_o`
    result) before this epilogue; rb16 = argument-block pointer; block =
    {reason, code}; rd16 = 0x18 (SYS_EXIT); `trap` with the semihosting tag.
    """
    return ([jump_iiii(1)]
            + [set_zw_rb(16, 2, 0xFFFF), or_w_rb(16, 1, 0x00FF), or_w_rb(16, 0, 0xF000)]
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog):
    """Prog at ROM offset 0; pad with swym to 0x400."""
    rom = bytearray(words_to_bytes(prog))
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
    """Extract the observed register state from the LAST dump block."""
    o = {}
    for n in range(1, 16):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
        o["rb%d" % n] = lasthex(log, r"RB\[%02d\]: ([0-9a-f]+)" % n)
    return o


# ---------------------------------------------------------------------------
# Case model + builders
# ---------------------------------------------------------------------------

CASES = []   # (name, desc, builder) ; builder() -> (rom, expected_dict)


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


# -- acc 2: RAM@0 read/write (offset 0x1000) --------------------------------
@case("ram0_rw", "RAM@0 0x0000_0000_0000 read/write")
def _ram0_rw():
    prog = load_rb(3, RAM0_BASE + 0x1000) + load_rd(4, 0xCAFEF00D) + [st_o(4, 3, 0)]
    prog += [ld_o(5, 3, 0)] + exit_seq(0x00)
    return build_rom(prog), {"exit": 0x00, "rd5": 0xCAFEF00D}


# -- acc 2: legacy RAM still read/write (offset 0x1000) ---------------------
@case("old_ram_rw", "legacy RAM 0xffff_0000_0000 read/write preserved")
def _old_ram_rw():
    prog = load_rb(3, OLD_RAM_BASE + 0x1000) + load_rd(4, 0x0BADC0DE) + [st_o(4, 3, 0)]
    prog += [ld_o(5, 3, 0)] + exit_seq(0x00)
    return build_rom(prog), {"exit": 0x00, "rd5": 0x0000_0BADC0DE}


# -- acc 2: two segments independent at the same offset ---------------------
@case("no_interference", "RAM@0 and legacy RAM independent at the same offset")
def _no_interference():
    prog = []
    prog += load_rb(3, RAM0_BASE + 0x2000)
    prog += load_rd(4, 0xAAAA_5555)
    prog += [st_o(4, 3, 0)]
    prog += load_rb(6, OLD_RAM_BASE + 0x2000)
    prog += load_rd(7, 0x1357_9BDF)
    prog += [st_o(7, 6, 0)]
    prog += [ld_o(8, 3, 0)]     # read back RAM@0
    prog += [ld_o(9, 6, 0)]     # read back legacy RAM
    prog += exit_seq(0x00)
    return build_rom(prog), {"exit": 0x00,
                             "rd8": 0x0000_0000AAAA5555,
                             "rd9": 0x0000_0001_3579BDF}


# -- acc 2: RAM@0 top 8 bytes ------------------------------------------------
@case("ram0_top", "RAM@0 last 8 bytes (top of 16 MiB) read/write")
def _ram0_top():
    prog = load_rb(3, RAM0_BASE + RAM0_SIZE - 8) + load_rd(4, 0xDEAD_BEEF) + [st_o(4, 3, 0)]
    prog += [ld_o(5, 3, 0)] + exit_seq(0x00)
    return build_rom(prog), {"exit": 0x00, "rd5": 0xDEAD_BEEF}


# -- acc 2: RAM@0 is executable (fetch from RAM@0) ---------------------------
@case("ram0_exec", "fetch/execute from RAM@0 (write code then jump)")
def _ram0_exec():
    # The fragment executed from RAM@0 is the semihosting SYS_EXIT trap: the
    # main program pre-loads rd16 = 0x18, rb16 = SEMI_BLOCK and the {0x20026,
    # 0x5A} block, then stores the trap word into RAM@0 and jumps to it.
    fragment_word = trap(0, SEMIHOST_TAG)    # SYS_EXIT trap, executed from RAM@0
    prog = load_rd(8, ADP_STOPPED_APPLICATION_EXIT)
    prog += load_rb(16, SEMI_BLOCK) + [st_o(8, 16, 0)]     # block[0] = 0x20026
    prog += load_rd(9, 0x5A) + [st_o(9, 16, 8)]            # block[1] = 0x5A
    prog += load_rd(16, 0x18)                # rd16 = SYS_EXIT service number
    prog += load_rb(2, RAM0_BASE + 0x2000)   # code target in RAM@0
    prog += load_rd(7, fragment_word << 32)  # place word in the high 32 bits
    prog += [st_o(7, 2, 0)]                  # store word at RAM@0 0x2000
    prog += [jump_rrii(2, 0, 0)]             # fetch/execute it
    prog += exit_seq(0xEE)                   # not reached
    return build_rom(prog), {"exit": 0x5A}


# -- acc 4: out-of-range DATA access ----------------------------------------
@case("oob_data_cfxmem", "data access cfxha0 outside RAM@0 => CFXMEM 0x81")
def _oob_data_cfxmem():
    prog = load_rb(3, CFX0_OOB) + [ld_o(5, 3, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


@case("oob_data_unmapped", "data access cfxha63 unmapped => 0x87")
def _oob_data_unmapped():
    prog = load_rb(3, CFX63_OOB) + [ld_o(5, 3, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_UNMAPPED}


# -- acc 4: out-of-range FETCH (instruction fetch path) ----------------------
@case("oob_fetch_cfxmem", "fetch cfxha0 outside RAM@0 => CFXMEM 0x81")
def _oob_fetch_cfxmem():
    prog = load_rb(3, CFX0_OOB) + [jump_rrii(3, 0, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_CFXMEM}


@case("oob_fetch_unmapped", "fetch cfxha63 unmapped => 0x87")
def _oob_fetch_unmapped():
    prog = load_rb(3, CFX63_OOB) + [jump_rrii(3, 0, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_UNMAPPED}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_case(name):
    for n, d, fn in CASES:
        if n == name:
            rom, exp = fn()
            rc, log = run(rom)
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
            print(n, "-", d)
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
        passed, detail, exp = run_case(name)
        print("[%s] %-18s %s -> %s" % ("PASS" if passed else "FAIL", name, desc, detail))
        if not passed:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
