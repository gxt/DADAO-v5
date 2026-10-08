#!/usr/bin/env python3
"""Min ROM probe for QEMU-044t: SEE/HEE run mode + cfx register file/mask/
permission + DADAO-12 §5 exception-entry/exit flow.

Spec sources (expectations derived by hand from spec/ + contracts, never from
the QEMU implementation):
  - spec/DADAO-12-SEE-主管系统运行环境.md §1 (run modes 0/1/2/3),
    §3 (cg0-cg7 shared registers, reset values), §4 (per-cfx regs / monitor
    exception tables), §5 (exception entry steps 1-10 + exception exit).
  - spec/DADAO-13-HEE-超管系统运行环境.md §1 (cg3/hypv reset values).
  - spec/SimRISC-11-其它.md §特权指令 (trap/escape/cfx2rd/cfx2rc; reserved => ILLI;
    non-existent register combination => CFXREG).
  - spec/Machine-01-测试机运行环境.md §2/§3 (test-machine cfx set cfx0/1/2/3/63;
    unimplemented cfx => CFXREG).
  - .tao/adr/adr-0020-see-semihosting.md (D9/D10/D11), adr-0004 (D2 reset).
  - contracts/opcodes.yaml (trap/escape/cfx2rd/cfx2rc op/mask/field layout).

Observation channels:
  * run mode / cfx registers / counters / cause frame -> QEMU `-d cpu` dump
    (parses the LAST dump block; same convention as min_rom_probe_034t..042t).
  * entry/return path -> process exit code (exit port), ADR-0004 D5.8.

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

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
QEMU = DEFAULT_QEMU
WORKDIR = "/tmp/opencode/QEMU-044t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
H = ROM_BASE + 0x100   # handler slot 1
H2 = ROM_BASE + 0x200  # handler slot 2
H3 = ROM_BASE + 0x180  # handler slot 3

# Run modes (DADAO-12 §1)
USER, JAIL, SUPV, HYPV = 0, 1, 2, 3
# Cause ids (DADAO-12 §4 monitor exception table)
CFXTRAP, CFXMEM, CFXREG, ILLI = 1, 2, 4, 1 << 8

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
def swym():                 return 0x77880000


def load_rd(rd, val):
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rd(rd, wp, x))
    return out


def exit_seq(code):
    """Write `code` to the exit port (rb16 = 0xffff_8000_0000) -> host $?."""
    return ([set_zw_rb(16, 2, 0xFFFF), or_w_rb(16, 1, 0x8000)] +
            load_rd(16, code) + [st_o(16, 16, 0)])


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
    for n in (5, 6, 7, 8, 9, 10):
        o["rd%d" % n] = lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
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


def base_setup_cfx63(switch_mode=None, clear_cause_mask=True):
    """hypv/cfx63 setup: optionally clear cause mask / switch mask / set mode."""
    ins = []
    if clear_cause_mask or switch_mode is not None:
        ins += [set_zw_rd(20, 0, 0)]
        if clear_cause_mask:
            ins += [cfx2rc(63, 3, 11, 20)]   # cfx63 hypv excp_cause_mask = 0
        ins += [cfx2rc(63, 3, 9, 20)]        # cfx63 hypv switch_cfx_mask = 0
    if switch_mode is not None:
        ins += load_rd(21, switch_mode)
        ins += [cfx2rc(63, 3, 8, 21)]        # cfx63 hypv switch_run_mode = X
    return ins


def hand(off, code):
    return {off: exit_seq(code)}


# -- acc 2/5/7: four run modes ---------------------------------------------
def _run_mode_case(sm):
    prog = base_setup_cfx63(switch_mode=sm)
    prog += load_rd(22, H) + [cfx2rc(63, 3, 10, 22)]   # cfx63 hypv vector = H
    trap_idx = len(prog)
    prog += [trap(63, 0)]
    prog += exit_seq(0xEE)
    exp = {
        "exit": 0x11, "mode": sm, "cfxcode": 63, "cfxmask": 0,
        "trapn:63": 1, "cid:63": CFXTRAP, "cinfo:63": 0x7FFC0000,
        "cip:63": ROM_BASE + trap_idx * 4,
        "prevm:63": HYPV, "prevmask:63": ~0 & 0xFFFFFFFFFFFFFFFF,
        "swmode:63:3": sm,
    }
    return build_rom(prog, hand(0x100, 0x11)), exp


for _sm in (USER, JAIL, SUPV, HYPV):
    def _mk(sm=_sm):
        return _run_mode_case(sm)
    _mk.__name__ = "run_mode_%d" % _sm
    case("run_mode_%d" % _sm, "switch_run_mode=%d -> run mode %d" % (_sm, _sm))(_mk)


# -- acc 3: reset values ----------------------------------------------------
@case("reset_values", "cg0-cg7 reset values per DADAO-12 §3 / DADAO-13 §1")
def _reset_values():
    prog = exit_seq(0x00)     # no cfx access; observe power-on reset state
    all1 = ~0 & 0xFFFFFFFFFFFFFFFF
    exp = {
        "exit": 0x00, "mode": HYPV, "cfxcode": 63, "cfxmask": all1,
        "gver0": 0x00090002, "gver1": 0x00090002,
        "gver2": 0x00070001, "gver3": 0x00010002,
        "gcm0": all1, "gcm1": all1, "gcm2": all1, "gcm3": 0,
        "id:0": 0, "id:1": 1, "id:2": 2, "id:3": 3, "id:63": 63,
        "scrnum:0": 4, "scrnum:63": 4,
        "swmode:63:0": SUPV, "swmode:63:1": SUPV,
        "swmode:63:2": SUPV, "swmode:63:3": HYPV,
        "swmode:0:0": SUPV, "swmode:0:3": HYPV,
        "trapn:63": 0, "syncn:63": 0, "escn:63": 0,
    }
    return build_rom(prog, {}), exp


# -- acc 3: cfx2rd/cfx2rc read/write + global_cfx_mask sharing --------------
@case("cfx_rw_share", "cfx2rd/cfx2rc rw + global_cfx_mask sharing (cfx0<->cfx63)")
def _cfx_rw_share():
    prog = []
    prog += load_rd(21, 0xABCD) + [cfx2rc(0, 0, 1, 21)]    # global_cfx_mask[0]
    prog += load_rd(22, 0x1234) + [cfx2rc(63, 6, 0, 22)]   # cfx63 scratch[0]
    prog += [cfx2rd(63, 0, 1, 6)]                          # read global via cfx63
    prog += [cfx2rd(63, 6, 0, 7)]                          # read scratch
    prog += [cfx2rd(63, 4, 6, 8)]                          # scratch_regs_num
    prog += [cfx2rd(63, 4, 0, 10)]                         # cfx_power cfx_id
    prog += exit_seq(0x00)
    exp = {"exit": 0x00, "rd6": 0xABCD, "rd7": 0x1234, "rd8": 4, "rd10": 63,
           "gcm0": 0xABCD}
    return build_rom(prog, {}), exp


# -- acc 3/7: trap counter + cause frame ------------------------------------
@case("trap_counters", "trap_num increment + cause_ip/id/info frame")
def _trap_counters():
    prog = base_setup_cfx63()
    prog += load_rd(22, H) + [cfx2rc(63, 3, 10, 22)]
    trap_idx = len(prog)
    prog += [trap(63, 0x0123)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0x11, "mode": HYPV, "trapn:63": 1, "syncn:63": 0,
           "cid:63": CFXTRAP, "cip:63": ROM_BASE + trap_idx * 4,
           "cinfo:63": 0x7F000000 | (63 << 18) | 0x0123,
           "prevm:63": HYPV}
    return build_rom(prog, hand(0x100, 0x11)), exp


# -- acc 3/7: escape -------------------------------------------------------
@case("escape_return", "escape -> cause_ip+4, escape_num++, prev mode/mask restore")
def _escape_return():
    prog = base_setup_cfx63()
    prog += load_rd(22, H) + [cfx2rc(63, 3, 10, 22)]
    trap_idx = len(prog)
    prog += [trap(63, 0)]
    # after escape returns to trap+4:
    prog += [cfx2rd(63, 4, 5, 9)]          # escape_num -> rd9
    prog += exit_seq(0x00)
    exp = {"exit": 0x00, "mode": HYPV, "rd9": 1, "escn:63": 1,
           "trapn:63": 1, "cip:63": ROM_BASE + trap_idx * 4}
    # handler: escape cfx63, imms18=1 (byte offset 4)
    return build_rom(prog, {0x100: [escape(63, 1)]}), exp


# -- acc 4: instruction-type mask -> ILLI redirect --------------------------
@case("mask_illi", "cfx trap mask bit => ILLI redirect to current-mode monitor")
def _mask_illi():
    prog = []
    prog += load_rd(23, 1) + [cfx2rc(0, 3, 6, 23)]   # cfx_umon hypv trap_mask bit0=1
    prog += load_rd(24, H) + [cfx2rc(3, 3, 10, 24)]  # cfx_hmon hypv vector = H
    trap_idx = len(prog)
    prog += [trap(0, 0)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0x22, "cid:3": ILLI, "syncn:3": 1,
           "cip:3": ROM_BASE + trap_idx * 4}
    return build_rom(prog, hand(0x100, 0x22)), exp


# -- acc 6: reserved cfxha -> ILLI ------------------------------------------
@case("reserved_illi", "reserved cfxha (7-14,19-61) => ILLI")
def _reserved_illi():
    prog = load_rd(24, H) + [cfx2rc(3, 3, 10, 24)]
    trap_idx = len(prog)
    prog += [trap(7, 0)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0x33, "cid:3": ILLI, "syncn:3": 1,
           "cip:3": ROM_BASE + trap_idx * 4}
    return build_rom(prog, hand(0x100, 0x33)), exp


# -- acc 6: unimplemented cfx -> CFXREG -------------------------------------
@case("cfxreg_unimpl", "unimplemented cfx (cfx4) access => CFXREG")
def _cfxreg_unimpl():
    prog = load_rd(24, H) + [cfx2rc(3, 3, 10, 24)]
    prog += [cfx2rd(4, 0, 0, 5)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0x44, "cid:3": CFXREG, "syncn:3": 1}
    return build_rom(prog, hand(0x100, 0x44)), exp


# -- acc 6: invalid register combination -> CFXREG --------------------------
@case("cfxreg_badcombo", "invalid cfx register combo (scratch rc>=N) => CFXREG")
def _cfxreg_badcombo():
    prog = load_rd(24, H) + [cfx2rc(0, 3, 10, 24)]   # cfx_umon hypv vector = H
    prog += [cfx2rd(0, 6, 5, 5)]                     # cfx0 scratch rc5 >= N(4)
    prog += exit_seq(0xEE)
    exp = {"exit": 0x45, "cid:0": CFXREG, "syncn:0": 1}
    return build_rom(prog, hand(0x100, 0x45)), exp


# -- acc 6: write to a read-only cfx register -> CFXREG ---------------------
@case("cfxreg_ro_write", "write to read-only cfx register (cfx_id) => CFXREG")
def _cfxreg_ro_write():
    prog = load_rd(24, H) + [cfx2rc(63, 3, 10, 24)]  # cfx_power hypv vector = H
    prog += [cfx2rc(63, 4, 0, 25)]                   # write cfx_id (RO)
    prog += exit_seq(0xEE)
    exp = {"exit": 0x46, "cid:63": CFXREG, "syncn:63": 1}
    return build_rom(prog, hand(0x100, 0x46)), exp


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
        print("[%s] %-16s %s -> %s" % ("PASS" if passed else "FAIL", name, desc, detail))
        if not passed:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
