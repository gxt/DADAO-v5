#!/usr/bin/env python3
"""Min ROM probe for QEMU-049t: RAM mapping (C1 step2: single RAM segment) +
out-of-range access/fetch fault semantics (CFXMEM vs the test-machine unmapped
convention).

Spec sources (expectations derived by hand from spec/ + ADRs, never from the
QEMU implementation):
  - spec/Kaiwu-测试机运行环境.md §1.1 (internal-address-space split:
    RAM RAM_BASE 16 MiB as the single RAM segment / boot ROM; C1
    step2 removed the legacy 0xffff_0000_0000 RAM and the exit-port device)
    and §1.2 (out-of-range access AND fetch both fault; CFXMEM (monitor) vs
    test-machine unmapped -> CFXMEM).
  - .tao/adr/adr-0020-see-semihosting.md D15 and adr-0004-test-machine.md
    R3 (rev. 2026-10-11: RAM base -> RAM_BASE) + D5.8 (frozen
    fault-code table: CFXMEM monitor index 1; unmapped => CFXMEM).
  - spec/DADAO-12-SEE-主管系统运行环境.md §2.1 (cfxha = addr[47:42]; illegal
    internal-address-space access => CFXMEM).
  - contracts/opcodes.yaml (ld.o/st.o/jump/set.zw/or.w encodings).

Routing implemented by QEMU-049t (ADR-0020 D15):
  * address inside the umon segment (cfxha 0) but outside RAM => CFXMEM (monitor)
    (both data access and instruction fetch).
  * any other unmapped address (incl. the power segment, cfxha 63, and the
    removed legacy RAM 0xffff_0000_0000) => CFXMEM (monitor).

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
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_049t")
TIMEOUT = 10

# TESTCASES-093t: the body runs at RESET_PC + 0x1000 inside the
# 4 MiB bootrom-image, after the shared power -> hmon identity-PTW prelude.
ROM_BASE = _prelude.ROM_BASE
RAM_BASE = _MACH.ram_base
RAM_SIZE = _MACH["ram_size"]
OLD_RAM_BASE = 0xFFFF_0000_0000
OLD_RAM_SIZE = 16 * 1024 * 1024

# Exit codes (ADR-0004 D5.8 + ADR-0020 D15): every execution-time synchronous
# exception enters the current run-mode monitor (DADAO-12 §5.2), so a fault
# case is judged on the monitor frame and leaves through SYS_EXIT(0).
EXIT_PASS = 0x00
# Monitor cause ids (DADAO-12 §5.2(二)) and the body's run mode.
C_CFXMEM = 1 << 1
MODE_H = 3

# Monitor-frame observer (DADAO-12 §5.2 steps 5-7): the body runs in hypv, so
# the monitor is cfx_hmon (cfx3) and the handler reads its own cg5 frame.
OFF_MONITOR = 0x300
MONITOR = ROM_BASE + OFF_MONITOR
CG5_PREV_MODE_RC, CG5_CAUSE_ID_RC, CG5_CAUSE_IP_RC, CG5_CAUSE_INFO_RC = 0, 2, 3, 4
CG3_SWITCH_MODE_RC, CG3_EXCP_VECTOR_RC = 8, 10
PTW_ENABLE_CG, PTW_ENABLE_RC = 8, 8

# Out-of-range addresses
CFX0_OOB = 0x0000_0100_0000           # cfxha 0 (umon): no RAM there => CFXMEM (monitor)
CFX63_OOB = 0xFFC0_0000_0000           # cfxha 63 (power): outside RAM/ROM => CFXMEM


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
def cfx2rc(ha, cg, rc, rd): return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def cfx2rd(ha, cg, rc, rd): return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd


def swym():              return 0x47880000


# Semihosting SYS_EXIT (ADR-0020 D8: SYS_EXIT replaces the legacy MMIO halt device).
SEMIHOST_TAG = 0x3FF00              # immu18[17:8] == 0x3FF (0x3FF00-0x3FFFF) -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = EXIT_BLOCK       # argument block {reason, code}, in RAM


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

def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers=None):
    """Shared prelude: body at RESET_PC + 0x1000 in the 4 MiB ROM image."""
    return _prelude.build_rom(prog, handlers or {})


def fault_at(p):
    """ROM address of the next appended instruction (the faulting one)."""
    return ROM_BASE + 4 * len(p)


def setup_monitor(p):
    """Point cfx_hmon's hypv vector at MONITOR (the body runs in hypv)."""
    p += load_rd(6, MODE_H) + [cfx2rc(3, 3, CG3_SWITCH_MODE_RC, 6)]
    p += load_rd(6, MONITOR) + [cfx2rc(3, 3, CG3_EXCP_VECTOR_RC, 6)]
    return p


# `excp_cause_id` is a *field* register, not a single value (contract-see
# §6.1/§6.1.1; ADR-0056 D3): [15:0] = one-hot big class, [63:48] = the CFXMEM
# sub-cause (wyde3), [47:32] = the CFXPERM sub-cause (wyde2), [31:16] reserved.
# Every CFXMEM in this probe is a non-page-table fault, i.e. [57] NONPTW.
CAUSE_LOW16 = 0xFFFF
CAUSE_WYDES = 0xFFFF_FFFF_0000_0000
CAUSE_RESERVED_31_16 = 0xFFFF_0000
SUB_NONPTW = 1 << 57


def cause_id_expect(cls, sub=0):
    """[(mask, expected)] over the three fields of `excp_cause_id`."""
    return [(CAUSE_LOW16, cls), (CAUSE_WYDES, sub), (CAUSE_RESERVED_31_16, 0)]


def frame_expect(prev_mode, cause, ip, info, sub=0):
    """Full monitor frame: the four saved fields, each read from cg5.

    `cause` is compared per field: the low 16 bits must be the big class and
    the expected sub-cause must be exactly one-hot in its own wyde with the
    other wyde and [31:16] zero (the pre-m14-qemu-005 assertion compared the
    whole 64-bit word against `1 << 1`).
    """
    return {"exit": EXIT_PASS, "rd10": prev_mode,
            "rd11": cause_id_expect(cause, sub),
            "rd12": ip, "rd13": info}


def monitor_words(reptw=False):
    """Read the cfx_hmon hypv frame back (cause id / cause_ip / cause_info /
    prev_run_mode), then leave through SYS_EXIT (DADAO-12 §5.2 steps 5-7).

    `reptw` re-enables the page table first: a case that faults with
    `ptw_enable=0` left the memory window translating nothing, so the SYS_EXIT
    argument-block store would itself be CFXMEM (DADAO-12 §2.2 step 1).
    """
    words = []
    if reptw:
        words += load_rd(6, 1) + [cfx2rc(4, PTW_ENABLE_CG, PTW_ENABLE_RC, 6)]
    return (words
            + [cfx2rd(3, 5, CG5_PREV_MODE_RC, 10),
               cfx2rd(3, 5, CG5_CAUSE_ID_RC, 11),
               cfx2rd(3, 5, CG5_CAUSE_IP_RC, 12),
               cfx2rd(3, 5, CG5_CAUSE_INFO_RC, 13)]
            + exit_seq(EXIT_PASS))


# ---------------------------------------------------------------------------
# QEMU runner + dump parsing
# ---------------------------------------------------------------------------

def run(rom):
    """4 MiB `bootrom-image`, no `-kernel`, one QEMU process per case."""
    return _prelude.run(rom, WORKDIR, qemu=QEMU, timeout=TIMEOUT)

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


# -- acc 2: RAM read/write (offset 0x1000) --------------------------------
@case("ram_rw", "RAM RAM_BASE read/write")
def _ram_rw():
    prog = load_rb(3, RAM_BASE + 0x1000) + load_rd(4, 0xCAFEF00D) + [st_o(4, 3, 0)]
    prog += [ld_o(5, 3, 0)] + exit_seq(0x00)
    return build_rom(prog), {"exit": 0x00, "rd5": 0xCAFEF00D}


# -- acc 2: legacy RAM segment removed (C1 step2) --------------------------
@case("old_ram_unmapped", "legacy RAM 0xffff_0000_0000 removed => data access CFXMEM (monitor)")
def _old_ram_unmapped():
    prog = []
    setup_monitor(prog)
    prog += load_rb(3, OLD_RAM_BASE + 0x1000)
    ip = fault_at(prog)
    prog.append(ld_o(5, 3, 0))
    prog += exit_seq(0x7E)                   # not reached: the handler exits
    return build_rom(prog, {OFF_MONITOR: monitor_words()}), \
        frame_expect(MODE_H, C_CFXMEM, ip, OLD_RAM_BASE + 0x1000,
                                  sub=SUB_NONPTW)


# -- acc 2: no second mapped RAM region -------------------------------------
@case("legacy_ram_gone", "write to 0xffff_0000_0000 => CFXMEM (monitor) (RAM is the only RAM)")
def _legacy_ram_gone():
    prog = []
    setup_monitor(prog)
    prog += load_rb(3, OLD_RAM_BASE + 0x2000) + load_rd(4, 0xAAAA_5555)
    ip = fault_at(prog)
    prog.append(st_o(4, 3, 0))
    prog += exit_seq(0x7E)                   # not reached: the handler exits
    return build_rom(prog, {OFF_MONITOR: monitor_words()}), \
        frame_expect(MODE_H, C_CFXMEM, ip, OLD_RAM_BASE + 0x2000,
                                  sub=SUB_NONPTW)


# -- acc 2: RAM top 8 bytes ------------------------------------------------
@case("ram_top", "RAM last 8 bytes (top of 16 MiB) read/write")
def _ram_top():
    prog = load_rb(3, RAM_BASE + RAM_SIZE - 8) + load_rd(4, 0xDEAD_BEEF) + [st_o(4, 3, 0)]
    prog += [ld_o(5, 3, 0)] + exit_seq(0x00)
    return build_rom(prog), {"exit": 0x00, "rd5": 0xDEAD_BEEF}


# -- acc 2: RAM is executable (fetch from RAM) ---------------------------
@case("ram_exec", "fetch/execute from RAM (write code then jump)")
def _ram_exec():
    # The fragment executed from RAM is the semihosting SYS_EXIT trap: the
    # main program pre-loads rd16 = 0x18, rb16 = SEMI_BLOCK and the {0x20026,
    # 0x1A} block, then stores the trap word into RAM and jumps to it.
    fragment_word = trap(0, SEMIHOST_TAG)    # SYS_EXIT trap, executed from RAM
    prog = load_rd(8, ADP_STOPPED_APPLICATION_EXIT)
    prog += load_rb(16, SEMI_BLOCK) + [st_o(8, 16, 0)]     # block[0] = 0x20026
    prog += load_rd(9, 0x1A) + [st_o(9, 16, 8)]            # block[1] = 0x1A
    prog += load_rd(16, 0x18)                # rd16 = SYS_EXIT service number
    prog += load_rb(2, RAM_BASE + 0x2000)   # code target in RAM
    prog += load_rd(7, fragment_word << 32)  # place word in the high 32 bits
    prog += [st_o(7, 2, 0)]                  # store word at RAM 0x2000
    prog += [jump_rrii(2, 0, 0)]             # fetch/execute it
    prog += exit_seq(0x7E)                   # not reached
    return build_rom(prog), {"exit": 0x1A}


# -- acc 4: out-of-range DATA access ----------------------------------------
@case("oob_data_cfxmem", "ptw_enable=0 + data access in the memory window => CFXMEM (monitor)")
def _oob_data_cfxmem():
    # TESTCASES-093t §3 category C: the prelude enables PTW, so the spec's
    # "memory-window access with ptw_enable=0 => CFXMEM" precondition is
    # rebuilt explicitly (DADAO-12 §2.2 step 1) instead of relying on the
    # legacy PTW-off machine.  The handler re-enables PTW before reporting:
    # the SYS_EXIT block store needs a live page table.
    prog = []
    setup_monitor(prog)
    prog += load_rd(6, 0) + [cfx2rc(4, PTW_ENABLE_CG, PTW_ENABLE_RC, 6)]
    prog += load_rb(3, CFX0_OOB)
    ip = fault_at(prog)
    prog.append(ld_o(5, 3, 0))
    prog += exit_seq(0x7E)                   # not reached: the handler exits
    return build_rom(prog, {OFF_MONITOR: monitor_words(reptw=True)}), \
        frame_expect(MODE_H, C_CFXMEM, ip, CFX0_OOB, sub=SUB_NONPTW)


@case("oob_data_unmapped", "data access cfxha63 unmapped => CFXMEM")
def _oob_data_unmapped():
    prog = []
    setup_monitor(prog)
    prog += load_rb(3, CFX63_OOB)
    ip = fault_at(prog)
    prog.append(ld_o(5, 3, 0))
    prog += exit_seq(0x7E)                   # not reached: the handler exits
    return build_rom(prog, {OFF_MONITOR: monitor_words()}), \
        frame_expect(MODE_H, C_CFXMEM, ip, CFX63_OOB, sub=SUB_NONPTW)


# -- acc 4: out-of-range FETCH (instruction fetch path) ----------------------
@case("oob_fetch_cfxmem", "ptw_enable=0 + fetch in the memory window => CFXMEM (monitor)")
def _oob_fetch_cfxmem():
    # Same category C rebuild as oob_data_cfxmem (DADAO-12 §2.2 step 1).  A
    # fetch fault is precise: cause_ip is the illegal IP itself, i.e. the
    # fetch address (DADAO-12 §5.2 step 5, §5 「IP 停留在非法地址」).
    prog = []
    setup_monitor(prog)
    prog += load_rd(6, 0) + [cfx2rc(4, PTW_ENABLE_CG, PTW_ENABLE_RC, 6)]
    prog += load_rb(3, CFX0_OOB)
    prog.append(jump_rrii(3, 0, 0))
    prog += exit_seq(0x7E)                   # not reached: the handler exits
    return build_rom(prog, {OFF_MONITOR: monitor_words(reptw=True)}), \
        frame_expect(MODE_H, C_CFXMEM, CFX0_OOB, CFX0_OOB, sub=SUB_NONPTW)


@case("oob_fetch_unmapped", "fetch cfxha63 unmapped => CFXMEM")
def _oob_fetch_unmapped():
    prog = []
    setup_monitor(prog)
    prog += load_rb(3, CFX63_OOB)
    prog.append(jump_rrii(3, 0, 0))
    prog += exit_seq(0x7E)                   # not reached: the handler exits
    return build_rom(prog, {OFF_MONITOR: monitor_words()}), \
        frame_expect(MODE_H, C_CFXMEM, CFX63_OOB, CFX63_OOB, sub=SUB_NONPTW)


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
            detail = "ok"
            if "rd10" in exp:
                detail = ("frame prev_mode=%d cause_id=0x%x cause_ip=0x%x "
                          "cause_info=0x%x" % (obs["rd10"], obs["rd11"],
                                               obs["rd12"], obs["rd13"]))
            return True, detail, exp
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
