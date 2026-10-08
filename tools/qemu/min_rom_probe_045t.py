#!/usr/bin/env python3
"""Min ROM probe for QEMU-045t: complete `trap`/`escape` semantics and
`cfx2rd`/`cfx2rc` full register face (deepening/verification on the QEMU-044t
baseline; trigger-path wiring was delivered by 044t).

Spec sources (expectations derived by hand from spec/ + contracts, never from
the QEMU implementation):
  - spec/DADAO-12-SEE-主管系统运行环境.md §1 (run modes), §3 (cg0-cg7
    register tables, per-cfx cg4-cg7, RO/RW, scratch_regs_num), §4 (monitor
    exception table: cause ids), §5 异常进入流程 steps 1-10 + 异常退出流程
    steps 0-4 (escape: escape_cfx_mask / prev_cfx_mask / prev_run_mode /
    escape_num++ / PC = excp_cause_ip + (imms18<<2)).
  - spec/SimRISC-11-其它.md §特权指令 (trap ciii; escape ciii with
    `imms20` byte offset, `%4==0`, addr = excp_cause_ip + imms20, encoding
    imms18<<2, N may be negative; cfx2rd/cfx2rc crrr; reserved cfxha 7-14,
    19-61 => ILLI; non-existent register combination / RO-write => CFXREG).
  - spec/Machine-01-测试机运行环境.md §2/§3 (test-machine cfx set
    cfx0/1/2/3/63; hypv+user only).
  - spec/Toolchain-01 (escape byte offset %4==0; assembly imms20 = imms18<<2).
  - .tao/adr/adr-0020-see-semihosting.md (D9/D10/D11); adr-0004 (D2 reset,
    D5.8 exit codes).
  - contracts/opcodes.yaml (trap_ciii_cfx / escape_ciii_cfx / cfx2rd_crrr_cfx /
    cfx2rc_crrr_cfx / jump_iiii_rb / st.o_rrii_rd field layouts).

Observation channels:
  * run mode / cfx registers / counters / cause frame / rd[] -> QEMU `-d cpu`
    dump (parses the LAST dump block; same convention as min_rom_probe_044t.py).
  * exception entry/return path -> process exit code (exit port), ADR-0004 D5.8.

Instruction encodings (contracts/opcodes.yaml):
  trap   ciii  op 0x7F  cfxha=ha[23:18]  immu18=(hb,hc,hd)   (unsigned)
  escape ciii  op 0x7E  cfxha=ha[23:18]  imms18=(hb,hc,hd)   (signed)
  cfx2rd crrr  op 0x7A  cfxha=ha[23:18] cghb=hb rchc=hc rdhd=hd
  cfx2rc crrr  op 0x7B  cfxha=ha[23:18] cghb=hb rchc=hc rdhd=hd
  jump   iiii  op 0x70  imms24=bits[23:0] (signed)  PC = rb0 + (imms24<<2)
  st.o   rrii  op 0x21  rdha=ha[23:18] rbhb=hb[17:12] imms12=bits[11:0]

Cases (acceptance 2-6):
  trap_vector_roundtrip (acc 2,3) general trap cfx0 enters vector; cause_id/
                                  cause_ip/cause_info; escape back +4; escape_num++.
  trap_mask_illi        (acc 2)   instruction-type trap mask forbid => ILLI.
  escape_fwd_offset     (acc 4)   imms18=+3 => PC = cause_ip + 12.
  escape_neg_offset     (acc 4)   imms18 negative => PC falls back before trap.
  escape_cross_mask     (acc 4,6) cross-cfx escape forbidden (step 0) => ILLI.
  escape_cross_allowed  (acc 3)   cross-cfx escape allowed restores non-reset
                                  prev_run_mode / prev_cfx_mask.
  cfx2_full_regface     (acc 5)   cfx2rd/cfx2rc cg0-cg7 read/write roundtrip
                                  (RO/RW, scratch, cfx0<->cfx63 sharing).
  cfx2_cg3_nonhypv      (acc 5/6) cg3 access outside hypv => CFXREG.
  cfxreg_cg_oor         (acc 6)   non-existent cg (>=8) => CFXREG.
  cfxreg_rc_oor         (acc 6)   non-existent rc (cg0 rc12) => CFXREG.
  cfxreg_scratch_oor    (acc 6)   scratch rc >= scratch_regs_num => CFXREG.
  cfxreg_ro_write       (acc 6)   write to RO register => CFXREG.
  reserved_illi         (acc 6)   reserved cfxha via cfx2rd (7) => ILLI.
  trap_reserved_illi    (acc 2,6) reserved cfxha via trap (7) => ILLI.

Usage:
  min_rom_probe_045t.py                # run all checks
  min_rom_probe_045t.py --only NAME    # run one check (used by run.sh --inject)
  min_rom_probe_045t.py --list

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
WORKDIR = "/tmp/opencode/QEMU-045t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
H = ROM_BASE + 0x100    # generic handler slot (cfx0 / cfx3)
EXIT_A = 0x200          # jump targets for the escape-offset cases
EXIT_B = 0x240
EXIT_C = 0x280
EXIT_NEG = 0x2C0
EXIT_CONT = 0x300

# Run modes (DADAO-12 §1)
USER, JAIL, SUPV, HYPV = 0, 1, 2, 3
# Cause ids (DADAO-12 §4 monitor exception table; one-hot)
CFXTRAP, CFXMEM, CFXREG, ILLI = 1, 2, 4, 1 << 8

ALL1 = (1 << 64) - 1

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
def jump_iiii(imms24):      return (0x70 << 24) | (imms24 & 0xFFFFFF)
def swym():                 return 0x77880000


def load_rd(rd, val):
    """rd = val via set.zw + or.w (word-by-word construction)."""
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rd(rd, wp, x))
    return out


def exit_seq(code):
    """Write `code` to the exit port (rb16 = 0xffff_8000_0000) -> host $?.

    rb16 = 0x0000_FFFF_8000_0000 built from set.zw (wp2=0xFFFF) + or.w (wp1=0x8000).
    """
    return ([set_zw_rb(16, 2, 0xFFFF), or_w_rb(16, 1, 0x8000)]
            + load_rd(16, code) + [st_o(16, 16, 0)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers):
    """prog at ROM offset 0; handlers = {byte offset: word list}; pad to 0x400."""
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers):
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(handlers[off])
    while len(rom) < 0x400:
        rom += words_to_bytes([swym()])
    return bytes(rom)


def jump_to(cur_idx, target_off):
    """jump at program index `cur_idx` to ROM byte offset `target_off`."""
    return jump_iiii(target_off // 4 - cur_idx)


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
    """Extract observed state from the LAST dump block.

    Notes on patterns: the dump prints decimal for MODE/CFXCODE, and the field
    `ASYNCN` contains the substring `SYNCN`, so SYNCN must be anchored to the
    register line (`ID:... SYNCN:` with a leading space, plus a trailing space
    before ESCN) to avoid mis-matching ASYNCN.
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
        o["trapn:%d" % ha] = lasthex(log, t + r" ID:[^\n]* TRAPN:([0-9a-f]+)")
        o["syncn:%d" % ha] = lasthex(log, t + r" ID:[^\n]* SYNCN:([0-9a-f]+)")
        o["escn:%d" % ha] = lasthex(log, t + r" ID:[^\n]*ESCN:([0-9a-f]+)")
        o["scrnum:%d" % ha] = lasthex(log, t + r" ID:[^\n]*SCRN:([0-9a-f]+)")
        o["cid:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]* CID:([0-9a-f]+)")
        o["cip:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*CIP:([0-9a-f]+)")
        o["cinfo:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*CINFO:([0-9a-f]+)")
        o["prevm:%d" % ha] = lasthex(log, t + r" PREVM:([0-9a-f]+)")
        o["prevmask:%d" % ha] = lasthex(log, t + r" PREVM:[^\n]*PREVMASK:([0-9a-f]+)")
    for n in range(5, 56):
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


def set_cfx_vector(cfxha, mode_cg, vec):
    """cfx2rc cfxha, cg=mode_cg, rc=10 (excp_vector), <- rd22."""
    return load_rd(22, vec) + [cfx2rc(cfxha, mode_cg, 10, 22)]


def hand(off, code):
    return {off: exit_seq(code)}


# -- acc 2/3: general trap enters vector + escape roundtrip -----------------
@case("trap_vector_roundtrip",
      "general trap cfx0 enters vector; cause frame; escape +4; escape_num++")
def _trap_vector_roundtrip():
    prog = set_cfx_vector(0, 3, H)          # cfx0 hypv excp_vector = H
    trap_idx = len(prog)
    prog += [trap(0, 0x0123)]               # immu18[17:16]=0 (general)
    # escape returns to trap+4:
    prog += [cfx2rd(0, 4, 5, 9)]            # escape_num -> rd9
    prog += [cfx2rd(0, 5, 3, 10)]           # cause_ip   -> rd10
    prog += [cfx2rd(0, 5, 0, 11)]           # prev_run_mode -> rd11
    prog += [cfx2rd(0, 5, 1, 12)]           # prev_cfx_mask -> rd12
    prog += exit_seq(0x00)
    exp = {
        "exit": 0x00,
        "cfxcode": 0, "mode": HYPV, "cfxmask": ALL1,
        "trapn:0": 1, "syncn:0": 0, "escn:0": 1,
        "cid:0": CFXTRAP,
        "cip:0": ROM_BASE + trap_idx * 4,
        "cinfo:0": (0x7F << 24) | (0 << 18) | 0x0123,
        "prevm:0": HYPV, "prevmask:0": ALL1,
        "rd9": 1, "rd10": ROM_BASE + trap_idx * 4,
        "rd11": HYPV, "rd12": ALL1,
    }
    # handler: escape cfx0, imms18=1 (byte offset +4)
    return build_rom(prog, {0x100: [escape(0, 1)]}), exp


# -- acc 2: instruction-type trap mask forbid => ILLI -----------------------
@case("trap_mask_illi", "instruction-type trap mask forbid => ILLI redirect")
def _trap_mask_illi():
    prog = load_rd(23, 1) + [cfx2rc(0, 3, 6, 23)]   # cfx0 hypv trap_mask bit0=1
    prog += set_cfx_vector(3, 3, H)                 # cfx3 hypv excp_vector = H
    trap_idx = len(prog)
    prog += [trap(0, 0)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0x22, "cid:3": ILLI, "syncn:3": 1,
           "cip:3": ROM_BASE + trap_idx * 4}
    return build_rom(prog, hand(0x100, 0x22)), exp


# -- acc 4: escape forward offset (imms18 = +3 => cause_ip + 12) ------------
@case("escape_fwd_offset", "escape imms18=+3 => PC = cause_ip + 12")
def _escape_fwd_offset():
    prog = set_cfx_vector(0, 3, H)
    trap_idx = len(prog)
    prog += [trap(0, 0)]
    j1 = len(prog)
    prog += [jump_to(j1, EXIT_A)]      # cause_ip + 4
    j2 = len(prog)
    prog += [jump_to(j2, EXIT_B)]      # cause_ip + 8
    j3 = len(prog)
    prog += [jump_to(j3, EXIT_C)]      # cause_ip + 12  <-- expected target
    handlers = {0x100: [escape(0, 3)],
                EXIT_A: exit_seq(0x66),
                EXIT_B: exit_seq(0x77),
                EXIT_C: exit_seq(0x99)}
    exp = {"exit": 0x99, "escn:0": 1, "trapn:0": 1}
    return build_rom(prog, handlers), exp


# -- acc 4: escape negative offset (backward) -------------------------------
@case("escape_neg_offset", "escape negative imms18 => PC falls back before trap")
def _escape_neg_offset():
    J = 8
    prog = [swym()] * J
    prog[0] = jump_to(0, J * 4)        # skip the negative target on first pass
    prog[1] = jump_to(1, EXIT_NEG)     # NEGATIVE TARGET (index 1)
    prog += set_cfx_vector(0, 3, H)
    trap_idx = len(prog)
    prog += [trap(0, 0)]
    prog += exit_seq(0xEE)             # taken only if offset were wrong
    imms = 1 - trap_idx                # target = index 1 (negative offset)
    handlers = {0x100: [escape(0, imms)],
                EXIT_NEG: exit_seq(0xAA)}
    exp = {"exit": 0xAA, "escn:0": 1, "trapn:0": 1}
    return build_rom(prog, handlers), exp


# -- acc 4/6: cross-cfx escape forbidden (step 0) => ILLI -------------------
@case("escape_cross_mask", "cross-cfx escape forbidden (escape_cfx_mask) => ILLI")
def _escape_cross_mask():
    prog = load_rd(23, 1) + [cfx2rc(63, 3, 7, 23)]   # cfx63 hypv escape_mask bit0=1
    prog += set_cfx_vector(3, 3, H)                  # cfx3 hypv excp_vector = H
    trap_idx = len(prog)
    prog += [escape(0, 0)]                           # cross cfx63 -> cfx0, forbidden
    prog += exit_seq(0xEE)
    exp = {"exit": 0xCC, "cid:3": ILLI, "syncn:3": 1,
           "cip:3": ROM_BASE + trap_idx * 4}
    return build_rom(prog, hand(0x100, 0xCC)), exp


# -- acc 3: cross-cfx escape allowed restores non-reset prev mode/mask ------
@case("escape_cross_allowed",
      "cross-cfx escape allowed restores prev_run_mode / prev_cfx_mask")
def _escape_cross_allowed():
    prog = load_rd(20, 0) + [cfx2rc(63, 3, 7, 20)]   # cfx63 hypv escape_mask = 0
    prog += load_rd(20, ROM_BASE + EXIT_CONT) + [cfx2rc(63, 5, 3, 20)]  # cause_ip
    prog += load_rd(20, USER) + [cfx2rc(63, 5, 0, 20)]       # prev_run_mode = USER
    prog += load_rd(20, 0xDEADBEEF) + [cfx2rc(63, 5, 1, 20)] # prev_cfx_mask
    prog += [escape(0, 0)]                    # cfx63 -> cfx0 (allowed)
    exp = {
        "exit": 0xBB, "mode": USER, "cfxmask": 0xDEADBEEF,
        "escn:63": 1, "prevm:63": USER, "prevmask:63": 0xDEADBEEF,
    }
    return build_rom(prog, {EXIT_CONT: exit_seq(0xBB)}), exp


# -- acc 5: cfx2rd/cfx2rc full register face (cg0-cg7), read-back -----------
@case("cfx2_full_regface",
      "cfx2rd/cfx2rc cg0-cg7 read/write roundtrip (cfx0 + cfx63 sharing)")
def _cfx2_full_regface():
    prog = []
    # cg4/cg5 RO reads (reset values from DADAO-12 §3/§4): version, scratch_regs_num,
    # cause_nonmaskable (monitor set = bits 0,1,2,8..13)
    prog += [cfx2rd(0, 4, 1, 53), cfx2rd(0, 4, 6, 54), cfx2rd(0, 5, 63, 55)]
    # cg0 rc1 global_cfx_mask[0]: write via cfx0, read back via cfx63 (shared)
    prog += load_rd(20, 0x1111) + [cfx2rc(0, 0, 1, 20), cfx2rd(63, 0, 1, 30)]
    # cg0/1/2/3 rc8 switch_run_mode per mode
    prog += load_rd(20, 2) + [cfx2rc(0, 0, 8, 20), cfx2rd(0, 0, 8, 31)]
    prog += load_rd(20, 1) + [cfx2rc(0, 1, 8, 20), cfx2rd(0, 1, 8, 32)]
    prog += load_rd(20, 0) + [cfx2rc(0, 2, 8, 20), cfx2rd(0, 2, 8, 33)]
    prog += load_rd(20, 3) + [cfx2rc(0, 3, 8, 20), cfx2rd(0, 3, 8, 34)]
    # cg3 rc12 cg_reg_deleg (hypv only) RW
    prog += load_rd(20, 0xCAFE) + [cfx2rc(0, 3, 12, 20), cfx2rd(0, 3, 12, 35)]
    # cg4 rc0 cfx_id (RO), rc2 trap_num (RO)
    prog += [cfx2rd(0, 4, 0, 36), cfx2rd(0, 4, 2, 37)]
    # cg5 rc3 cause_ip (RW), rc0 prev_run_mode (RW), rc1 prev_cfx_mask (RW)
    prog += load_rd(20, 0x5555) + [cfx2rc(0, 5, 3, 20), cfx2rd(0, 5, 3, 38)]
    prog += load_rd(20, 1) + [cfx2rc(0, 5, 0, 20), cfx2rd(0, 5, 0, 39)]
    prog += load_rd(20, 0x9999) + [cfx2rc(0, 5, 1, 20), cfx2rd(0, 5, 1, 40)]
    prog += load_rd(20, 7) + [cfx2rc(0, 5, 5, 20), cfx2rd(0, 5, 5, 41)]
    prog += [cfx2rd(0, 5, 2, 42)]            # cg5 rc2 cause_id (RO)
    # cg6 scratch rc0 / rc3 (RW, N=4)
    prog += load_rd(20, 0xAAAA) + [cfx2rc(0, 6, 0, 20), cfx2rd(0, 6, 0, 43)]
    prog += load_rd(20, 0xBBBB) + [cfx2rc(0, 6, 3, 20), cfx2rd(0, 6, 3, 44)]
    # cg7 rc0 sram_block_sel / rc1 sram_addr (RW)
    prog += load_rd(20, 0x1234) + [cfx2rc(0, 7, 0, 20), cfx2rd(0, 7, 0, 45)]
    prog += load_rd(20, 0x5678) + [cfx2rc(0, 7, 1, 20), cfx2rd(0, 7, 1, 46)]
    # cg2 rc1 global_cfx_mask[2] (distinct per-mode shared reg)
    prog += load_rd(20, 0x2222) + [cfx2rc(0, 2, 1, 20), cfx2rd(0, 2, 1, 47)]
    # cfx63 (power): write cause_ip / scratch[1], read back
    prog += load_rd(20, 0x12345678) + [cfx2rc(63, 5, 3, 20), cfx2rd(63, 5, 3, 48)]
    prog += load_rd(20, 0xFFFF) + [cfx2rc(63, 6, 1, 20), cfx2rd(63, 6, 1, 49)]
    prog += exit_seq(0x00)
    exp = {
        "exit": 0x00, "gcm0": 0x1111, "gcm2": 0x2222,
        "rd30": 0x1111, "rd31": 2, "rd32": 1, "rd33": 0, "rd34": 3,
        "rd35": 0xCAFE, "rd36": 0, "rd37": 0,
        "rd38": 0x5555, "rd39": 1, "rd40": 0x9999, "rd41": 7, "rd42": 0,
        "rd43": 0xAAAA, "rd44": 0xBBBB,
        "rd45": 0x1234, "rd46": 0x5678, "rd47": 0x2222,
        "rd48": 0x12345678, "rd49": 0xFFFF,
        "rd53": 0x00010000, "rd54": 4, "rd55": 0x3F07,
    }
    return build_rom(prog, {}), exp


# -- acc 5/6: cg3 access outside hypv => CFXREG -----------------------------
@case("cfx2_cg3_nonhypv", "cg3 register access outside hypv mode => CFXREG")
def _cfx2_cg3_nonhypv():
    # cfx0 user (cg0) and hypv (cg3) vectors both -> H
    prog = set_cfx_vector(0, 0, H) + set_cfx_vector(0, 3, H)
    # allow cfx2rd cfx0 from user mode (clear cfx0 user cfx2rd_mask)
    prog += load_rd(20, 0) + [cfx2rc(0, 0, 2, 20)]
    # drop to user mode via allowed cross-cfx escape from cfx63
    prog += load_rd(20, 0) + [cfx2rc(63, 3, 7, 20)]                    # escape_mask = 0
    prog += load_rd(20, ROM_BASE + EXIT_CONT) + [cfx2rc(63, 5, 3, 20)]  # cause_ip
    prog += load_rd(20, USER) + [cfx2rc(63, 5, 0, 20)]       # prev_run_mode = USER
    prog += load_rd(20, 0) + [cfx2rc(63, 5, 1, 20)]          # prev_cfx_mask = 0
    prog += [escape(0, 0)]                                   # -> user mode @ EXIT_CONT
    exp = {"exit": 0xCC, "cid:0": CFXREG, "syncn:0": 1,
           "cip:0": ROM_BASE + EXIT_CONT}
    handlers = {0x100: exit_seq(0xCC),
                EXIT_CONT: [cfx2rd(0, 3, 1, 30)] + exit_seq(0xEE)}
    return build_rom(prog, handlers), exp


# -- acc 6: non-existent cg (>=8) => CFXREG --------------------------------
@case("cfxreg_cg_oor", "non-existent cg (cg8) => CFXREG")
def _cfxreg_cg_oor():
    prog = set_cfx_vector(0, 3, H) + set_cfx_vector(0, 0, H)
    fault_idx = len(prog)
    prog += [cfx2rd(0, 8, 0, 30)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0xCC, "cid:0": CFXREG, "syncn:0": 1,
           "cip:0": ROM_BASE + fault_idx * 4}
    return build_rom(prog, hand(0x100, 0xCC)), exp


# -- acc 6: non-existent rc (cg0 rc12) => CFXREG ---------------------------
@case("cfxreg_rc_oor", "non-existent rc (cg0 rc12) => CFXREG")
def _cfxreg_rc_oor():
    prog = set_cfx_vector(0, 3, H) + set_cfx_vector(0, 0, H)
    fault_idx = len(prog)
    prog += [cfx2rd(0, 0, 12, 30)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0xCC, "cid:0": CFXREG, "syncn:0": 1,
           "cip:0": ROM_BASE + fault_idx * 4}
    return build_rom(prog, hand(0x100, 0xCC)), exp


# -- acc 6: scratch rc >= scratch_regs_num => CFXREG -----------------------
@case("cfxreg_scratch_oor", "scratch rc >= scratch_regs_num (=4) => CFXREG")
def _cfxreg_scratch_oor():
    prog = set_cfx_vector(0, 3, H) + set_cfx_vector(0, 0, H)
    fault_idx = len(prog)
    prog += [cfx2rd(0, 6, 4, 30)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0xCC, "cid:0": CFXREG, "syncn:0": 1,
           "cip:0": ROM_BASE + fault_idx * 4}
    return build_rom(prog, hand(0x100, 0xCC)), exp


# -- acc 6: write to RO register => CFXREG ---------------------------------
@case("cfxreg_ro_write", "write to RO register (cg4 rc0 cfx_id) => CFXREG")
def _cfxreg_ro_write():
    prog = set_cfx_vector(0, 3, H) + set_cfx_vector(0, 0, H)
    prog += load_rd(25, 0x1234)
    fault_idx = len(prog)
    prog += [cfx2rc(0, 4, 0, 25)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0xCC, "cid:0": CFXREG, "syncn:0": 1,
           "cip:0": ROM_BASE + fault_idx * 4}
    return build_rom(prog, hand(0x100, 0xCC)), exp


# -- acc 6: reserved cfxha via cfx2rd => ILLI ------------------------------
@case("reserved_illi", "reserved cfxha (7) via cfx2rd => ILLI")
def _reserved_illi():
    prog = set_cfx_vector(3, 3, H)
    fault_idx = len(prog)
    prog += [cfx2rd(7, 0, 0, 30)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0x33, "cid:3": ILLI, "syncn:3": 1,
           "cip:3": ROM_BASE + fault_idx * 4}
    return build_rom(prog, hand(0x100, 0x33)), exp


# -- acc 2/6: reserved cfxha via trap => ILLI ------------------------------
@case("trap_reserved_illi", "reserved cfxha (7) via trap => ILLI")
def _trap_reserved_illi():
    prog = set_cfx_vector(3, 3, H)
    fault_idx = len(prog)
    prog += [trap(7, 0)]
    prog += exit_seq(0xEE)
    exp = {"exit": 0x33, "cid:3": ILLI, "syncn:3": 1,
           "cip:3": ROM_BASE + fault_idx * 4}
    return build_rom(prog, hand(0x100, 0x33)), exp


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
        print("[%s] %-20s %s -> %s" % ("PASS" if passed else "FAIL", name, desc, detail))
        if not passed:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
