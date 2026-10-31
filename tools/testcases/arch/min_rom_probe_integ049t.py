#!/usr/bin/env python3
"""INTEG-049t probe: cg7 internal space description registers (16 blocks x 4).

Expectations are derived by hand from
  - spec/DADAO-12 §2.1 (core-internal address space: smon/hmon/pmem 64 KiB
    SRAM at `0x3ff_0000_0000`, power 256 KiB BootROM at `0x3ff_fffc_0000`,
    `start + size <= 2^42`), §3.8 (cg7 = internal space description; 16 blocks
    of `rc = 4i+0..3` = desc/start/size/attr; `exists = 0` => start/size/attr
    read 0; all read-only, a write of any rc => `CFXREG`), and §4/§5 (cause
    ids, exception entry flow);
  - .tao/contracts/contract-see.md §3 (cg7 block-level contract) and §2 (核内
    地址映射);
  - .tao/tasks/integ/INTEG-049t-*.md「已确认口径」(user-given block table,
    2026-10-31): smon/hmon `desc=0x3 attr=R|W|X`; pmem `desc=0x3 attr=R|W`
    (X=0); power `desc=0x5 attr=R|X`;
  - spec/Machine-01 §3 (test-machine cfx set; unimplemented cfx => CFXREG).
Not from the QEMU implementation.

Probe layout (one ROM per case, `-bios` window at 0xffff_ffff_0000):
  * reset runs power (cfx63/hypv); a 2-instruction prefix hands over to hmon
    (cfx3/hypv) exactly like INTEG-044t/045t/048t;
  * the body runs in hmon/hypv, which the reset masks already allow to read
    every implemented cfx's registers, so no permission surgery is needed;
  * observation: the last `-d cpu` dump block (rd values, cfx cause frames)
    plus the SYS_EXIT status.

Every case compares exact values (or an exact all-64-rc checksum), so each has
a reachable FAIL path; the `space_*` cases additionally re-derive the §2.1
identity `(cfxha << 42) | start` and the `start + size <= 2^42` bound in the
probe (independent arithmetic, not a QEMU read-back).

Usage:
  min_rom_probe_integ049t.py [--qemu PATH] [--only NAME] [--list]
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
WORKDIR = "/tmp/opencode/INTEG-049t/probe"
TIMEOUT = 20

ROM_BASE = 0xFFFF_FFFF_0000
BODY_OFF = 0x024        # hmon (cfx3/hypv) body, right after the power prefix
HAND_OFF = 0x900        # CFXREG handler slot (cfx_hmon hypv vector)
IMAGE_END = HAND_OFF + 0x040

# Run modes (DADAO-12 §1)
USER, JAIL, SUPV, HYPV = 0, 1, 2, 3
# Cause ids (DADAO-12 §4 monitor exception table)
CFXREG = 1 << 2

# cg7 block 0 per cfx (spec/DADAO-12 §2.1 + §3.8; user-given test-machine table)
#   desc: bit0 exists, bit1 SRAM, bit2 ROM
#   attr: bit0 R, bit1 W, bit2 X
BLOCK0 = {
    2:  (0x3, 0x3FF_0000_0000, 0x1_0000, 0x7),   # smon  SRAM R|W|X
    3:  (0x3, 0x3FF_0000_0000, 0x1_0000, 0x7),   # hmon  SRAM R|W|X
    17: (0x3, 0x3FF_0000_0000, 0x1_0000, 0x3),   # pmem  SRAM R|W (X=0)
    63: (0x5, 0x3FF_FFFC_0000, 0x4_0000, 0x5),   # power ROM  R|X
}
# §2.1 core-internal start addresses (independent of the cg7 read-back)
FULL_ADDR = {
    2: 0x0BFF_0000_0000,
    3: 0x0FFF_0000_0000,
    17: 0x47FF_0000_0000,
    63: 0xFFFF_FFFC_0000,
}
POW2_42 = 1 << 42

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
def swym():                 return 0x47880000


def or_o(hb, hc, hd):
    """or.o rdhb, rdhc, rdhd (orrr, opc 0x40 / ha 0x09)."""
    return 0x40240000 | (hb << 12) | (hc << 6) | hd


def xor_o(hb, hc, hd):
    """xor.o rdhb, rdhc, rdhd (orrr, opc 0x40 / ha 0x0A)."""
    return 0x40280000 | (hb << 12) | (hc << 6) | hd


def load_rd(rd, val):
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rd(rd, wp, x))
    return out


def exit_seq(code):
    """SYS_EXIT with the argument block in RAM (same convention as 045t)."""
    return ([set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),
             or_w_rb(16, 0, 0xF000), or_w_rb(16, 2, 0xFC00)]
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])


def info_rd(ha, cg, rc, rd):
    return cfx2rd(ha, cg, rc, rd)


def info_rc(ha, cg, rc, rd):
    return cfx2rc(ha, cg, rc, rd)


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(body, sections):
    """power prefix at 0, `body` at BODY_OFF, `sections` = {offset: words}."""
    rom = bytearray(words_to_bytes(bootstrap_prefix()))
    if len(rom) > BODY_OFF:
        raise AssertionError("power prefix overlaps BODY_OFF")
    while len(rom) < BODY_OFF:
        rom += words_to_bytes([swym()])
    rom += words_to_bytes(body)
    for off in sorted(sections):
        if len(rom) > off:
            raise AssertionError("section at 0x%x overlaps (len 0x%x)" % (off, len(rom)))
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(sections[off])
    if len(rom) > IMAGE_END:
        raise AssertionError("image too big (0x%x > 0x%x)" % (len(rom), IMAGE_END))
    while len(rom) < IMAGE_END:
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
    """Extract the observations from the LAST dump block.

    `SYNCN` must be anchored to a space (ASYNCN contains the substring) and the
    cause frame lives on the `CFXxx PREVM:` line.
    """
    o = {"mode": None}
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
    return o


# ---------------------------------------------------------------------------
# Case model + program builders
# ---------------------------------------------------------------------------

CASES = []   # (name, desc, builder); builder() -> [(label, rom, exp, post)]


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def bootstrap_prefix():
    """power(cfx63/hypv) -> hmon(cfx3/hypv): hmon is power's only trap target."""
    return load_rd(22, ROM_BASE + BODY_OFF) + [cfx2rc(3, 3, 10, 22), trap(3, 0)]


def probe_base():
    """Install the CFXREG vector of the hmon/hypv row (handler slot)."""
    return load_rd(20, ROM_BASE + HAND_OFF) + [cfx2rc(3, 3, 10, 20)]


def handler():
    """CFXREG handler: record the cfx_hmon cause frame, exit 0xCC."""
    h = [cfx2rd(3, 5, 2, 20), cfx2rd(3, 5, 3, 21), cfx2rd(3, 5, 4, 22)]
    return h + exit_seq(0xCC)


def one(rom, exp, post=None):
    return [("", rom, exp, post)]


def read_block(cfxha, base_rd):
    """Read cg7 rc0..3 of `cfxha` into base_rd..base_rd+3."""
    return [cfx2rd(cfxha, 7, i, base_rd + i) for i in range(4)]


def or_accumulate(cfxha, rcs, acc_rd, tmp_rd):
    """acc = OR of cg7[rc] over `rcs` (any read fault diverts to the handler)."""
    out = [set_zw_rd(acc_rd, 0, 0)]
    for rc in rcs:
        out.append(cfx2rd(cfxha, 7, rc, tmp_rd))
        out.append(or_o(acc_rd, acc_rd, tmp_rd))
    return out


def xor_all(cfxha, acc_rd, tmp_rd, diff_rd, exp_rd):
    """acc |= xor difference of all 64 rc against BLOCK0[cfxha] (0 if absent)."""
    blk = BLOCK0.get(cfxha, (0, 0, 0, 0))
    out = [set_zw_rd(acc_rd, 0, 0)]
    for rc in range(64):
        exp = blk[rc % 4] if rc < 4 else 0
        out.append(cfx2rd(cfxha, 7, rc, tmp_rd))
        if exp:
            out += load_rd(exp_rd, exp)
            out.append(xor_o(diff_rd, tmp_rd, exp_rd))
        else:
            out.append(xor_o(diff_rd, tmp_rd, 0))     # rd0 == 0
        out.append(or_o(acc_rd, acc_rd, diff_rd))
    return out


def space_arith(cfxha):
    """§2.1/§3.8 arithmetic re-derivation of the observed block 0."""
    def check(obs):
        errs = []
        desc, start, size, attr = (obs.get("rd10"), obs.get("rd11"),
                                   obs.get("rd12"), obs.get("rd13"))
        if None in (desc, start, size, attr):
            return ["block 0 not observed"]
        if start >= POW2_42:
            errs.append("start 0x%x not a 42-bit offset" % start)
        if start + size > POW2_42:
            errs.append("start+size 0x%x exceeds 2^42" % (start + size))
        if cfxha == 63 and start + size != POW2_42:
            errs.append("power start+size 0x%x != 2^42" % (start + size))
        full = (cfxha << 42) | start
        if full != FULL_ADDR[cfxha]:
            errs.append("(cfxha<<42)|start 0x%x != §2.1 0x%x"
                        % (full, FULL_ADDR[cfxha]))
        return errs
    return check


# -- 1-4: the four space-bearing cfx ---------------------------------------

def _space_case(cfxha):
    body = probe_base() + read_block(cfxha, 10) + exit_seq(0x00)
    rom = build_rom(body, {HAND_OFF: handler()})
    desc, start, size, attr = BLOCK0[cfxha]
    exp = {"exit": 0x00, "rd10": desc, "rd11": start, "rd12": size,
           "rd13": attr}
    return one(rom, exp, space_arith(cfxha))


@case("space_smon", "cfx2 cg7 space[0]: desc/start/size/attr = 3/3ff_0000_0000/1_0000/7")
def _space_smon():
    return _space_case(2)


@case("space_hmon", "cfx3 cg7 space[0]: desc/start/size/attr = 3/3ff_0000_0000/1_0000/7")
def _space_hmon():
    return _space_case(3)


@case("space_pmem", "cfx17 cg7 space[0]: desc/start/size/attr = 3/3ff_0000_0000/1_0000/3 (X=0)")
def _space_pmem():
    return _space_case(17)


@case("space_power", "cfx63 cg7 space[0]: desc/start/size/attr = 5/3ff_fffc_0000/4_0000/5 (X=1)")
def _space_power():
    return _space_case(63)


# -- 5/6: implemented cfx without any space --------------------------------

def _no_space(cfxha):
    body = (probe_base() + or_accumulate(cfxha, range(64), 40, 11)
            + exit_seq(0x00))
    rom = build_rom(body, {HAND_OFF: handler()})
    return one(rom, {"exit": 0x00, "rd40": 0})


@case("no_space_umon", "cfx0: all 64 cg7 rc read 0 (16 blocks all exists=0)")
def _no_space_umon():
    return _no_space(0)


@case("no_space_ptw", "cfx4: all 64 cg7 rc read 0 (16 blocks all exists=0)")
def _no_space_ptw():
    return _no_space(4)


# -- 7: only space[0] is populated ----------------------------------------

@case("space1_15_zero", "cfx2/3/17/63: rc4..rc63 (space[1..15]) OR-accumulate to 0")
def _space1_15_zero():
    body = probe_base()
    accs = {2: 40, 3: 41, 17: 42, 63: 43}
    for cfxha, acc in accs.items():
        body += or_accumulate(cfxha, range(4, 64), acc, 11)
    body += exit_seq(0x00)
    rom = build_rom(body, {HAND_OFF: handler()})
    exp = {"exit": 0x00}
    for acc in accs.values():
        exp["rd%d" % acc] = 0
    return one(rom, exp)


# -- 8: desc / attr bit-level rules ---------------------------------------

def _desc_attr_rules(obs):
    errs = []
    pairs = ((2, "rd30", "rd31"), (3, "rd32", "rd33"),
             (17, "rd34", "rd35"), (63, "rd36", "rd37"))
    for cfxha, dk, ak in pairs:
        d, a = obs.get(dk), obs.get(ak)
        if d is None or a is None:
            errs.append("cfx%d desc/attr not observed" % cfxha)
            continue
        if d & ~0x3F:
            errs.append("cfx%d desc reserved bits set: 0x%x" % (cfxha, d))
        if not (d & 0x1):
            errs.append("cfx%d desc exists=0" % cfxha)
        if bin((d >> 1) & 0x1F).count("1") != 1:
            errs.append("cfx%d desc type not one-hot: 0x%x" % (cfxha, d))
        if a & ~0x3F:
            errs.append("cfx%d attr reserved bits set: 0x%x" % (cfxha, a))
        if a & 0x38:
            errs.append("cfx%d attr cacheable/shareable/volatile set: 0x%x"
                        % (cfxha, a))
    return errs


@case("desc_attr_reserved", "space[0] desc: reserved=0, exists=1, type one-hot; attr: reserved/c/s/v=0")
def _desc_attr_reserved():
    body = probe_base()
    for cfxha, rd in ((2, 30), (3, 32), (17, 34), (63, 36)):
        body += [cfx2rd(cfxha, 7, 0, rd), cfx2rd(cfxha, 7, 3, rd + 1)]
    body += exit_seq(0x00)
    rom = build_rom(body, {HAND_OFF: handler()})
    exp = {"exit": 0x00}
    for cfxha, rd in ((2, 30), (3, 32), (17, 34), (63, 36)):
        exp["rd%d" % rd] = BLOCK0[cfxha][0]
        exp["rd%d" % (rd + 1)] = BLOCK0[cfxha][3]
    return one(rom, exp, _desc_attr_rules)


# -- 9: every rc of a space-bearing cfx is readable and matches the table --

@case("ro_all_rc", "cfx2/cfx63: rc0..rc63 readable, xor-check vs table; rc0-3/rc60-63 sampled")
def _ro_all_rc():
    body = probe_base()
    body += xor_all(2, 10, 11, 12, 25)
    body += xor_all(63, 13, 11, 12, 25)
    # disjoint sample windows: cfx2 -> rd30..37, cfx63 -> rd38..45
    for cfxha, rd in ((2, 30), (63, 38)):
        body += [cfx2rd(cfxha, 7, rc, rd + rc) for rc in range(4)]
        body += [cfx2rd(cfxha, 7, rc, rd + 4 + (rc - 60))
                 for rc in range(60, 64)]
    body += exit_seq(0x00)
    rom = build_rom(body, {HAND_OFF: handler()})
    exp = {"exit": 0x00, "rd10": 0, "rd13": 0}
    for cfxha, rd in ((2, 30), (63, 38)):
        for rc in range(4):
            exp["rd%d" % (rd + rc)] = BLOCK0[cfxha][rc]
        for rc in range(60, 64):
            exp["rd%d" % (rd + 4 + (rc - 60))] = 0
    return one(rom, exp)


# -- 10: any cg7 write is CFXREG ------------------------------------------

@case("write_cfxreg", "cfx3 (self) cg7 write rc0/rc21/rc63 => CFXREG, exact cid/cip/cinfo")
def _write_cfxreg():
    out = []
    for rc in (0, 21, 63):
        body = probe_base() + load_rd(25, 0x1234)
        fault_idx = len(body)
        body += [cfx2rc(3, 7, rc, 25)] + exit_seq(0x00)
        rom = build_rom(body, {HAND_OFF: handler()})
        exp = {"exit": 0xCC, "cid:3": CFXREG,
               "cip:3": ROM_BASE + BODY_OFF + 4 * fault_idx,
               "cinfo:3": info_rc(3, 7, rc, 25), "syncn:3": 1}
        out.append(("rc%d" % rc, rom, exp, None))
    return out


# -- 11: unimplemented cfx still raises CFXREG ----------------------------

@case("unimpl_cfx", "cfx5 (cache, unimplemented) cg7 rc0 read => CFXREG")
def _unimpl_cfx():
    body = probe_base()
    fault_idx = len(body)
    body += [cfx2rd(5, 7, 0, 30)] + exit_seq(0x00)
    rom = build_rom(body, {HAND_OFF: handler()})
    # ci < 0 is raised with target = the current run mode (hypv => cfx_hmon).
    return one(rom, {"exit": 0xCC, "cid:3": CFXREG,
                     "cip:3": ROM_BASE + BODY_OFF + 4 * fault_idx,
                     "cinfo:3": info_rd(5, 7, 0, 30), "syncn:3": 1})


# -- 12: reads have no side effects ---------------------------------------

@case("read_stable", "same rc read twice returns the same value (no side effect)")
def _read_stable():
    body = probe_base()
    body += [cfx2rd(63, 7, 1, 10), cfx2rd(63, 7, 1, 11)]
    body += [cfx2rd(2, 7, 2, 12), cfx2rd(2, 7, 2, 13)]
    body += [cfx2rd(17, 7, 3, 30), cfx2rd(17, 7, 3, 31)]
    body += exit_seq(0x00)
    rom = build_rom(body, {HAND_OFF: handler()})
    exp = {"exit": 0x00,
           "rd10": BLOCK0[63][1], "rd11": BLOCK0[63][1],
           "rd12": BLOCK0[2][2], "rd13": BLOCK0[2][2],
           "rd30": BLOCK0[17][3], "rd31": BLOCK0[17][3]}
    return one(rom, exp)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_case(name):
    for n, d, fn in CASES:
        if n != name:
            continue
        ok = True
        details = []
        for label, rom, exp, post in fn():
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
            if post is not None:
                diffs.extend(post(obs))
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
            print("%-22s %s" % (n, d))
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
        print("[%s] %-22s %s -> %s" % ("PASS" if passed else "FAIL", name, desc, detail))
        if not passed:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
