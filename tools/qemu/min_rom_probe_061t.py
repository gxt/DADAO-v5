#!/usr/bin/env python3
"""Min ROM probe for QEMU-061t: `aip.si` (IP-relative addressing, op 0x5A) decode
+ semantics.

Spec sources (expectations derived by hand from spec/ + ADRs, never from the
QEMU implementation):
  - spec/SimRISC-05-64位地址运算.md §3.4 (IP-relative addressing):
        rbHA = IP + (sign_extend(imms18) << 12)
    * IP = the address of the instruction ITSELF (= the rb0 read value; this ISA
      has no ±4 pipeline offset) and its low 12 bits are NOT cleared
      (auipc style, unlike the retired page-aligned rela.si wording);
    * imms18 is an 18-bit SIGNED count of 4 KiB blocks (<< 12, no << 2);
    * the result is written in full 64 bits to the RB bank; destination rb0
      => ILLI.
  - .tao/adr/adr-0029-rela-si-auipc-pairing.md D1 + §修订注记 (instruction name
    `rela.si` -> `aip.si`; `IP` = current instruction address, not "next").
  - contracts/opcodes.yaml (`aip.si_riii_rb`: op=0x5A, mask=0xFF000000,
    rbha[23:18], imms18[17:0] signed).
  - components/qemu patches (cpu.h): DADAO_ROM_BASE = 0xffff_ffff_0000,
    DADAO_RESET_PC = DADAO_ROM_BASE => the program below executes from ROM_BASE,
    so the i-th word of the program sits at ROM_BASE + 4*i.

Observation channels:
  * register results -> QEMU `-d cpu` dump (parses the LAST dump block; same
    convention as min_rom_probe_034t..049t).  The final `jump` of the exit
    epilogue forces a TB boundary so the last dump already contains the result
    of the measured instruction.
  * fault codes -> process exit code via QEMU's fault mapping (0x88 = ILLI,
    0x89 = UNDI); normal pass/fail -> semihosting SYS_EXIT (ADR-0020 D8).

What the cases discriminate (each expectation is derived from ROM_BASE + the
instruction's own index, i.e. from the spec + the ROM layout, not from QEMU):
  * `aip_zero`            - base is IP, and 0x5A is NOT UNDI (rc would be 0x89);
                            a `PC+4`-style base (DADAO-0628 wording) would give
                            ROM_BASE+4 and fail.
  * `aip_pos_block`       - scale is << 12 (4 KiB), not << 2 / bytes.
  * `aip_neg_block`       - imms18 is signed (sign extension).
  * `aip_ip_low_bits`,
    `aip_ip_tracks_pc`    - IP low 12 bits are NOT cleared, and IP tracks the
                            instruction's own address (indices 0 vs 3 differ).
  * `aip_max_pos`         - imms18 = +131071 pushes bit 48 => the full 64-bit
                            result is kept (48-bit truncation would fail).
  * `aip_min_neg`         - imms18 = -131072 (signed lower bound).
  * `aip_dst_rb0_illi`    - destination rb0 => ILLI (0x88).

Usage:
  min_rom_probe_061t.py                 # run all checks
  min_rom_probe_061t.py --only NAME     # run one check
  min_rom_probe_061t.py --list
  min_rom_probe_061t.py --qemu PATH

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
WORKDIR = "/tmp/opencode/QEMU-061t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000          # DADAO_ROM_BASE / DADAO_RESET_PC (cpu.h)

# Exit codes (ADR-0004 D5.8)
EXIT_PASS = 0x00
EXIT_ILLI = 0x88
EXIT_UNDI = 0x89

MASK64 = 0xFFFF_FFFF_FFFF_FFFF


# ---------------------------------------------------------------------------
# Encoders (contracts/opcodes.yaml)
# ---------------------------------------------------------------------------

def _rwii(op, ha, wp, imm):
    hb = (wp << 4) | ((imm >> 12) & 0xF)
    return (op << 24) | (ha << 18) | (hb << 12) | (((imm >> 6) & 0x3F) << 6) | (imm & 0x3F)


def set_zw_rd(rd, wp, imm): return _rwii(0x4C, rd, wp, imm & 0xFFFF)
def set_zw_rb(rb, wp, imm): return _rwii(0x4E, rb, wp, imm & 0xFFFF)
def or_w_rb(rb, wp, imm):   return _rwii(0x4A, rb, wp, imm & 0xFFFF)


def _rrii(op, ha, hb, off):
    imm = off & 0xFFF
    return (op << 24) | (ha << 18) | (hb << 12) | (((imm >> 6) & 0x3F) << 6) | (imm & 0x3F)


def st_o(rd, rb, off):   return _rrii(0x21, rd, rb, off)
def jump_iiii(imms24):   return (0x70 << 24) | (imms24 & 0xFFFFFF)
def trap(ha, immu18):    return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
def swym():              return 0x77880000


def aip_si(rbha, imms18):
    """aip.si rbHA, imms18 - op 0x5A, rbha[23:18], imms18[17:0] (signed)."""
    return (0x5A << 24) | ((rbha & 0x3F) << 18) | (imms18 & 0x3FFFF)


def load_rd(rd, val):
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(_rwii(0x48, rd, wp, x))     # or.w rd, wpN, immu16
    return out


# Semihosting SYS_EXIT (ADR-0020 D8: SYS_EXIT replaces the legacy MMIO halt device).
SEMIHOST_TAG = 0x30000              # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = 0xFC00_00FF_F000       # argument block {reason, code}, in RAM


def exit_seq(code):
    """Report `code` via semihosting SYS_EXIT -> host $?.

    The leading no-op `jump` ends the current TB so the last `-d cpu` dump (the
    probe's observation channel) already contains the measured instruction's
    register effect; rb16 = argument-block pointer; block = {reason, code};
    rd16 = 0x18 (SYS_EXIT); `trap` with the semihosting tag.
    """
    return ([jump_iiii(1)]
            + [set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),
               or_w_rb(16, 0, 0xF000), or_w_rb(16, 2, 0xFC00)]
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog):
    """Program at ROM offset 0; pad with swym to 0x400."""
    rom = bytearray(words_to_bytes(prog))
    while len(rom) < 0x400:
        rom += words_to_bytes([swym()])
    return bytes(rom)


# ---------------------------------------------------------------------------
# Independent oracle (host side, from spec/SimRISC-05 §1.4 + the ROM layout)
# ---------------------------------------------------------------------------

def sext18(v):
    """Sign-extend an 18-bit immediate (spec/SimRISC-05 §1.4)."""
    v &= 0x3FFFF
    return v - 0x40000 if v & 0x20000 else v


def expected_result(index, imms18):
    """rbHA = IP + (sign_extend(imms18) << 12); IP = ROM_BASE + 4*index."""
    ip = (ROM_BASE + 4 * index) & MASK64
    return (ip + (sext18(imms18) << 12)) & MASK64


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
    for n in range(1, 21):
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


@case("aip_zero", "aip.si rb1, 0: rb1 = IP (not UNDI, not PC+4)")
def _aip_zero():
    prefix = []
    idx = len(prefix)
    prog = prefix + [aip_si(1, 0)] + exit_seq(EXIT_PASS)
    return build_rom(prog), {"exit": EXIT_PASS, "rb1": expected_result(idx, 0)}


@case("aip_pos_block", "aip.si rb2, +1: rb2 = IP + 0x1000 (<<12, not <<2)")
def _aip_pos_block():
    prefix = []
    idx = len(prefix)
    prog = prefix + [aip_si(2, 1)] + exit_seq(EXIT_PASS)
    return build_rom(prog), {"exit": EXIT_PASS, "rb2": expected_result(idx, 1)}


@case("aip_neg_block", "aip.si rb3, -1: rb3 = IP - 0x1000 (signed imms18)")
def _aip_neg_block():
    prefix = []
    idx = len(prefix)
    prog = prefix + [aip_si(3, -1)] + exit_seq(EXIT_PASS)
    return build_rom(prog), {"exit": EXIT_PASS, "rb3": expected_result(idx, -1)}


@case("aip_ip_low_bits", "aip.si rb4 @idx3: IP low 12 bits not cleared")
def _aip_ip_low_bits():
    prefix = [swym(), swym(), swym()]
    idx = len(prefix)
    prog = prefix + [aip_si(4, 1)] + exit_seq(EXIT_PASS)
    return build_rom(prog), {"exit": EXIT_PASS, "rb4": expected_result(idx, 1)}


@case("aip_ip_tracks_pc", "aip.si rb5 @idx3: IP = this instruction's own address")
def _aip_ip_tracks_pc():
    prefix = [swym(), swym(), swym()]
    idx = len(prefix)
    prog = prefix + [aip_si(5, 0)] + exit_seq(EXIT_PASS)
    return build_rom(prog), {"exit": EXIT_PASS, "rb5": expected_result(idx, 0)}


@case("aip_max_pos", "aip.si rb6, +131071: bit 48 set (full 64-bit result)")
def _aip_max_pos():
    prefix = []
    idx = len(prefix)
    prog = prefix + [aip_si(6, 131071)] + exit_seq(EXIT_PASS)
    return build_rom(prog), {"exit": EXIT_PASS, "rb6": expected_result(idx, 131071)}


@case("aip_min_neg", "aip.si rb7, -131072: s18 lower bound")
def _aip_min_neg():
    prefix = []
    idx = len(prefix)
    prog = prefix + [aip_si(7, -131072)] + exit_seq(EXIT_PASS)
    return build_rom(prog), {"exit": EXIT_PASS, "rb7": expected_result(idx, -131072)}


@case("aip_dst_rb0_illi", "aip.si rb0, 0: destination rb0 => ILLI 0x88")
def _aip_dst_rb0_illi():
    prog = [aip_si(0, 0)] + exit_seq(0xEE)
    return build_rom(prog), {"exit": EXIT_ILLI}


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
