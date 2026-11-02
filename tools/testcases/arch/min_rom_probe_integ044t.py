#!/usr/bin/env python3
"""Min ROM probe for INTEG-044t: SEE/HEE run mode + cfx register file/mask/
permission + DADAO-12 §5 exception-entry/exit flow.

Spec sources (expectations derived by hand from spec/ + contracts, never from
the QEMU implementation):
  - spec/DADAO-12-SEE-主管系统运行环境.md §1 (run modes 0/1/2/3),
    §3 (cg0-cg7 shared registers, reset values), §4 (per-cfx regs / monitor
    exception tables), §5 (exception entry steps 1-10 + exception exit).
  - spec/DADAO-13-HEE-超管系统运行环境.md §1 (cg3/hypv reset values).
  - spec/SimRISC-11-核芯功能扩展指令.md 「指令域与执行条件」 (trap/escape/cfx2rd/cfx2rc; reserved => ILLI;
    non-existent register combination => CFXREG).
  - spec/Machine-01-测试机运行环境.md §2/§3 (test-machine cfx set cfx0/1/2/3/63;
    unimplemented cfx => CFXREG).
  - .tao/adr/adr-0020-see-semihosting.md (D9/D10/D11), adr-0004 (D2 reset).
  - contracts/opcodes.yaml (trap/escape/cfx2rd/cfx2rc op/mask/field layout).

Observation channels:
  * run mode / cfx registers / counters / cause frame -> QEMU `-d cpu` dump
    (parses the LAST dump block; same convention as min_rom_probe_034t..042t).
  * entry/return path -> process exit code (semihosting SYS_EXIT, ADR-0020 D8;
    replaces the legacy MMIO halt device).

Instruction under test (encodings from contracts/opcodes.yaml):
  trap   ciii  op 0x7F  cfxha=ha[23:18]  immu18=(hb,hc,hd)
  escape ciii  op 0x7E  cfxha=ha[23:18]  imms18=(hb,hc,hd)
  cfx2rd crrr  op 0x7A  cfxha=ha[23:18] cghb=hb rchc=hc rdhd=hd
  cfx2rc crrr  op 0x7B  cfxha=ha[23:18] cghb=hb rchc=hc rdhd=hd

Cases (acceptance 2-7):
  run_mode_0/1/2/3  (acc 2,5)   switch_run_mode -> 4 run-mode encodings
  reset_values      (acc 3)     cg0-cg7 reset values per DADAO-12 §3 / DADAO-13 §1
  cfx_rw_share      (acc 3)     cfx2rd/cfx2rc rw + global_cfx_mask sharing
  trap_counters     (acc 3,7)   trap_num increment + cause_ip/id/info frame
  escape_return     (acc 3,7)   escape -> cause_ip+4, escape_num++, mode restore
  mask_illi         (acc 4)     instruction-type trap mask => ILLI redirect
  reserved_illi     (acc 6)     reserved cfxha => ILLI
  cfxreg_unimpl     (acc 6)     unimplemented cfx => CFXREG
  cfxreg_badcombo   (acc 6)     invalid register combination => CFXREG
  cfxreg_ro_write   (acc 6)     write to a read-only cfx register => CFXREG

Usage:
  min_rom_probe_044t.py                # run all checks
  min_rom_probe_044t.py --only NAME    # run one check (used by run.sh --inject)
  min_rom_probe_044t.py --list

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
WORKDIR = "/tmp/opencode/QEMU-044t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
H = ROM_BASE + 0x100   # handler slot 1
PMEM_BASE = 0x47FF_0000_0000   # cfx17 SRAM, internal offset 0x3ff_0000_0000
H2 = ROM_BASE + 0x200  # handler slot 2
H3 = ROM_BASE + 0x180  # handler slot 3

# Run modes (DADAO-12 §1)
USER, JAIL, SUPV, HYPV = 0, 1, 2, 3
# Cause ids (DADAO-12 §4 monitor exception table)
CFXTRAP, CFXMEM, CFXREG, ILLI = 1, 2, 4, 1 << 8
CFXPERM = 1 << 7

# Semihosting SYS_EXIT (ADR-0020 D8: SYS_EXIT replaces the legacy MMIO halt device).
SEMIHOST_TAG = 0x3FF00              # immu18[17:8] == 0x3FF (0x3FF00-0x3FFFF) -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026
SEMI_BLOCK = 0xFC00_00FF_F000       # argument block {reason, code}, in RAM

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
def escape(ha, imms18):     return (0x7E << 24) | (ha << 18) | (imms18 & 0x3FFFF)
def swym():                 return 0x47880000


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


def ld_o(rd, rb, off):
    imm = off & 0xFFF
    return (0x20 << 24) | (rd << 18) | (rb << 12) | (((imm >> 6) & 0x3F) << 6) | (imm & 0x3F)


def exit_seq(code):
    """Report `code` via semihosting SYS_EXIT (ADR-0020 D8) -> host $?.

    rb16 = SEMI_BLOCK (argument-block pointer); block = {reason, code};
    rd16 = 0x18 (SYS_EXIT); `trap` with the semihosting tag.  The low byte of
    `code` becomes the process status (contract-semihosting.md §3/§5).
    """
    return ([set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF), or_w_rb(16, 0, 0xF000), or_w_rb(16, 2, 0xFC00)]
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers):
    """prog at ROM offset 0; handlers = {offset: word list}; pad to 0x400."""
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers):
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


def lastdec(log, pat):
    m = None
    for x in re.finditer(pat, log):
        m = x
    return int(m.group(1), 10) if m else None


def observe(log):
    """Extract the observed state from the LAST dump block.

    Notes on patterns: the dump prints decimal for MODE/CFXCODE, and the field
    `ASYNCN` contains the substring `SYNCN`, so SYNCN must be anchored to the
    register-line (`ID:... SYNCN:` with a leading space) to avoid matching it.
    """
    o = {}
    o["mode"] = lastdec(log, r"MODE: (\d+)")
    o["cfxcode"] = lastdec(log, r"CFXCODE: (\d+)")
    o["cfxmask"] = lasthex(log, r"CFXMASK: ([0-9a-f]+)")
    for i in range(4):
        o["gver%d" % i] = lasthex(log, r"GVER%d: ([0-9a-f]+)" % i)
        o["gcm%d" % i] = lasthex(log, r"GCM%d: ([0-9a-f]+)" % i)
    for ha in (0, 1, 2, 3, 63):
        t = "CFX%02d" % ha
        o["id:%d" % ha] = lasthex(log, t + r" ID:([0-9a-f]+)")
        o["trapn:%d" % ha] = lasthex(log, t + r" ID:[^\n]*TRAPN:([0-9a-f]+)")
        o["syncn:%d" % ha] = lasthex(log, t + r" ID:[^\n]* SYNCN:([0-9a-f]+)")
        o["escn:%d" % ha] = lasthex(log, t + r" ID:[^\n]*ESCN:([0-9a-f]+)")
        o["scrnum:%d" % ha] = lasthex(log, t + r" ID:[^\n]*SCRN:([0-9a-f]+)")
        o["cid:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]* CID:([0-9a-f]+)")
        o["cip:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*CIP:([0-9a-f]+)")
        o["cinfo:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*CINFO:([0-9a-f]+)")
        o["prevm:%d" % ha] = lasthex(log, t + r" PREVM:([0-9a-f]+)")
        o["prevmask:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*PREVMASK:([0-9a-f]+)")
        for m in range(4):
            o["swmode:%d:%d" % (ha, m)] = lasthex(
                log, t + r" M%d SWMODE:([0-9a-f]+)" % m)
    for n in (5, 6, 7, 8, 9, 10, 11, 12):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    return o



# ---------------------------------------------------------------------------
# Case model + builders (INTEG-044t two-axis permission model)
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def hand(off, code):
    return {off: exit_seq(code)}


MASK_DEFAULT = 0xFFFF_FFFF_FFFF_FFF7
MASK_HMON = 0x7FFF_FFFF_FFFF_FFF7
ALL1 = (1 << 64) - 1
CFX_PERM = 1 << 7
CFX_ESC = 1 << 3
CFX_REG = 1 << 2


@case("init_masks", "four sync masks default hmon-only; interrupt masks all-1")
def _init_masks():
    p = []
    # read cfx0 user/hypv cfxtrap + cfx0 hypv cfxmem/cfxreg/cfxexe/cfx_intr
    for rc, rd in ((0, 5), (1, 6), (2, 7), (3, 8), (4, 9)):
        p.append(cfx2rd(0, 3, rc, rd))
    p.append(cfx2rd(0, 0, 0, 10))          # cfx0 user cfxtrap (same default)
    p.append(cfx2rd(3, 3, 0, 11))          # hmon own cfxtrap = 0x7FFF...F7
    p.append(cfx2rd(3, 8, 1, 12))          # hmon global_cfx_intr_mask = all-1
    p += exit_seq(0x00)
    exp = {"exit": 0x00, "cfxcode": 3,
           "rd5": MASK_DEFAULT, "rd6": MASK_DEFAULT, "rd7": MASK_DEFAULT,
           "rd8": MASK_DEFAULT, "rd9": ALL1, "rd10": MASK_DEFAULT,
           "rd11": MASK_HMON, "rd12": ALL1}
    return build_rom(p, {}), exp


@case("cfxmem_deny", "direct ld/st denied by cfxmem => CFXPERM at current monitor")
def _cfxmem_deny():
    p = load_rd(20, 1 << 3) + [cfx2rc(17, 3, 1, 20)]   # pmem cfxmem bit3=1
    p += load_rd(24, H) + [cfx2rc(3, 3, 10, 24)]        # hmon vector = H
    p += load_rb(3, PMEM_BASE)
    fault_idx = len(p)
    p += [ld_o(5, 3, 0)]
    p += exit_seq(0xEE)
    exp = {"exit": 0x22, "cid:3": CFX_PERM, "syncn:3": 1,
           "cinfo:3": PMEM_BASE, "cip:3": ROM_BASE + fault_idx * 4}
    return build_rom(p, hand(0x100, 0x22)), exp


@case("cfxmem_allow", "cfxmem allow (bit clear) lets the access through")
def _cfxmem_allow():
    p = load_rd(20, 0) + [cfx2rc(17, 3, 1, 20)]        # pmem cfxmem allow hmon
    p += load_rb(3, PMEM_BASE) + [ld_o(5, 3, 0)]
    p += exit_seq(0x00)
    # PMEM SRAM reset is 0; the load must not raise CFXPERM.
    return build_rom(p, {}), {"exit": 0x00}


@case("cfxreg_deny", "cfx2rd denied by cfxreg => CFXPERM")
def _cfxreg_deny():
    p = load_rd(20, 1 << 3) + [cfx2rc(17, 3, 2, 20)]   # pmem cfxreg bit3=1
    p += load_rd(24, H) + [cfx2rc(3, 3, 10, 24)]        # hmon vector = H
    fault_idx = len(p)
    p += [cfx2rd(17, 0, 0, 5)]
    p += exit_seq(0xEE)
    info = (0x7A << 24) | (17 << 18) | (0 << 12) | (0 << 6) | 5
    exp = {"exit": 0x22, "cid:3": CFX_PERM, "syncn:3": 1,
           "cinfo:3": info, "cip:3": ROM_BASE + fault_idx * 4}
    return build_rom(p, hand(0x100, 0x22)), exp


@case("cfxexe_deny", "fetch into another cfx denied by cfxexe => CFXPERM")
def _cfxexe_deny():
    p = []
    # cfx0: allow hmon trap, switch to S, vector H and user vector H.
    p += load_rd(20, 2) + [cfx2rc(0, 3, 8, 20)]
    p += load_rd(20, H) + [cfx2rc(0, 3, 10, 20)]
    p += load_rd(20, H) + [cfx2rc(0, 0, 10, 20)]
    # cfx63 (power) S-mode cfxexe: deny source cfx0, allow source cfx2.
    p += load_rd(20, (~(1 << 2)) & ALL1) + [cfx2rc(63, 2, 3, 20)]
    # smon (cfx2) S-mode vector = H2; body still runs in hmon H.
    p += load_rd(20, ROM_BASE + 0x200) + [cfx2rc(2, 2, 10, 20)]
    p += load_rd(20, 0) + [cfx2rc(2, 2, 11, 20)]      # cause mask = 0
    fault_idx = len(p)
    p += [trap(0, 0)]                                  # hmon -> cfx0, mode S
    p += exit_seq(0xEE)
    exp = {"exit": 0x33, "cid:2": CFX_PERM, "syncn:2": 1,
           "cinfo:2": H, "cip:2": H}
    handlers = {0x100: exit_seq(0xEE), 0x200: exit_seq(0x33)}
    return build_rom(p, handlers), exp


@case("trap_intr_mask_restore", "trap saves+masks global_cfx_intr_mask; escape restores")
def _trap_intr_mask_restore():
    p = []
    p += load_rd(20, 0x1234) + [cfx2rc(3, 8, 1, 20)]  # hmon global mask = 0x1234
    p += load_rd(20, H) + [cfx2rc(3, 3, 10, 20)]      # hmon H vector = H
    p += [trap(3, 0)]                                 # self trap: save+mask
    p.append(cfx2rd(3, 8, 1, 7))                      # handler already read rd6
    p += exit_seq(0x00)
    exp = {"exit": 0x00, "rd6": ALL1, "rd7": 0x1234, "trapn:3": 2, "escn:3": 1}
    return build_rom(p, {0x100: [cfx2rd(3, 8, 1, 6), escape(3, 1)]}), exp


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
    for k, v in list(exp.items()):
        if isinstance(v, int) and ROM_BASE <= v < ROM_BASE + 0x100:
            exp[k] = v + BOOTSTRAP_OFF
    return exp


def run_case(name):
    for n, d, fn in CASES:
        if n == name:
            rom, exp = fn()
            rom = bootstrap_rom(rom)
            exp = shift_rom_expect(exp)
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
        print("[%s] %-16s %s -> %s" % ("PASS" if passed else "FAIL", name, desc, detail))
        if not passed:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
