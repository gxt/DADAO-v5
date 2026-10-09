#!/usr/bin/env python3
"""Min ROM probe for QEMU-046t: semihosting (decode-layer short-circuit +
shared-layer reuse + full 25-service set + SYS_EXIT).

Spec sources (all expectations are derived by hand from spec/ + contracts/,
never from the QEMU implementation):
  - spec/Machine-01-测试机运行环境.md §5 (semihosting: entry tag
    immu18[17:16]==2'b11, calling convention rd16/rb16/rd31, the authoritative
    25-service table, pc+=4 return, SYS_EXIT replaces the legacy MMIO halt device).
  - .tao/adr/adr-0020-see-semihosting.md D1/D2/D3/D4/D5/D6/D8/D10/D14.
  - .tao/knowledge/contract-semihosting.md §1-§6.
  - .tao/knowledge/contract-abi.md §2.1 (SP = rb1 / rbsp), §4.1/§4.4.
  - Arm Semihosting (AArch32/AArch64, Release 2.0): service number values and
    the argument-block field layouts used by the shared responder.

Observation channels:
  * run mode / cfx frame / rd[] / PC -> QEMU `-d cpu` dump (last dump block;
    each trap/escape/cfx2* helper ends its TB, so the start-of-TB dump of the
    next block shows the semihosting return in rd31).
  * SYS_EXIT / SYS_EXIT_EXTENDED -> process exit code (host $?). The shared
    responder implements the ADR-0020 D8 halt (SYS_EXIT replaces the legacy
    MMIO exit device) by calling exit(code), so $? equals the semihosting
    status code.
  * WRITEC / WRITE0 console output and native file I/O -> files on the host
    (the probe passes a file chardev and creates/reads real files).

Instruction encodings (contracts/opcodes.yaml):
  trap    ciii  op 0x7F  cfxha=ha[23:18]  immu18=(hb,hc,hd)
  cfx2rc  crrr  op 0x7B  cfxha=ha[23:18] cghb=hb rchc=hc rdhd=hd
  set.zw  rwii  op 0x4C(rd)/0x4E(rb)   reg[23:18] wp[17:16] immu16[15:0]
  or.w    rwii  op 0x48(rd)/0x4A(rb)
  ld.o    rrii  op 0x20  rdha=ha[23:18] rbhb=hb[17:12] imms12[11:0]
  st.o    rrii  op 0x21
  jump    iiii  op 0x70  imms24[23:0]

Cases:
  semihost_tag_path   (acc 2)  immu18[17:16]==2'b11 -> served, PC+=4, no vector
  semihost_cfxha_agnostic (acc 2) tag works with a reserved cfxha (7)
  general_trap_path   (acc 2)  immu18[17:16]!=2'b11 -> CFXTRAP enters vector
  bank_num_rd16       (acc 3)  n=0 reads rd16 (rd17 decorrelated)
  bank_arg_rb16       (acc 3)  n=1 reads rb16 (rb17 decorrelated)
  ret_rd31            (acc 3)  return lands in rd31, rd30 untouched
  svc_*               (acc 4)  all 25 service numbers exercised (>=1 each)
  iserror_be64        (acc 6)  argument block read as 64-bit big-endian
  exit_*              (acc 5)  SYS_EXIT / SYS_EXIT_EXTENDED -> host $?

Usage:
  min_rom_probe_046t.py                # run all checks
  min_rom_probe_046t.py --only NAME    # run one check (used by run.sh)
  min_rom_probe_046t.py --list

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
WORKDIR = "/tmp/opencode/QEMU-046t"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0x0000_0000_0000
H = ROM_BASE + 0x100            # vector handler slot in ROM
TAG = 0x30000                  # immu18 with immu18[17:16] == 2'b11

# RAM (kernel image) layout, loaded at RAM_BASE.
K_OPEN = 0x100                 # OPEN argument block
K_SVC = 0x140                  # per-service argument block (handle carrier)
K_SVC2 = 0x180                 # secondary argument block
K_BUF = 0x300                  # read/write buffer
K_PATH = 0x400                 # host path strings
K_STR = 0x500                  # misc strings (WRITEC/WRITE0/SYSTEM)

# Service numbers (Arm Semihosting values; Machine-01 §5.3).
SVC_TABLE = [
    ("OPEN", 0x01), ("CLOSE", 0x02), ("WRITEC", 0x03), ("WRITE0", 0x04),
    ("WRITE", 0x05), ("READ", 0x06), ("READC", 0x07), ("ISERROR", 0x08),
    ("ISTTY", 0x09), ("SEEK", 0x0a), ("FLEN", 0x0c), ("TMPNAM", 0x0d),
    ("REMOVE", 0x0e), ("RENAME", 0x0f), ("CLOCK", 0x10), ("TIME", 0x11),
    ("SYSTEM", 0x12), ("ERRNO", 0x13), ("GET_CMDLINE", 0x15),
    ("HEAPINFO", 0x16), ("EXIT", 0x18), ("SYNCCACHE", 0x19),
    ("EXIT_EXTENDED", 0x20), ("ELAPSED", 0x30), ("TICKFREQ", 0x31),
]
SERVICE_IDS = set(v for _, v in SVC_TABLE)

ADP_STOPPED_APPLICATION_EXIT = 0x20026

# Cause ids (DADAO-12 §4 monitor exception table; one-hot).
CFXTRAP = 1
ILLI = 1 << 8


class Present:
    """Expectation marker: the observed value must merely be present."""
    def __repr__(self):
        return "PRESENT"

PRESENT = Present()


# ---------------------------------------------------------------------------
# Encoders (contracts/opcodes.yaml)
# ---------------------------------------------------------------------------

def set_zw_rd(rd, wp, imm): return (0x4C << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)
def or_w_rd(rd, wp, imm):   return (0x48 << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)
def set_zw_rb(rb, wp, imm): return (0x4E << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)
def or_w_rb(rb, wp, imm):   return (0x4A << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)
def ld_o(rd, rb, off):      return (0x20 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)
def st_o(rd, rb, off):      return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)
def cfx2rc(ha, cg, rc, rd): return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def trap(ha, immu18):       return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
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


def set_addr(rb, addr):
    """rb = addr (48-bit) via set.zw (word 3) + or.w (words 2..0)."""
    ws = [set_zw_rb(rb, 3, (addr >> 48) & 0xFFFF)]
    for wp in (2, 1, 0):
        x = (addr >> (16 * wp)) & 0xFFFF
        if x:
            ws.append(or_w_rb(rb, wp, x))
    return ws


def exit_seq(code):
    """Report `code` via semihosting SYS_EXIT (ADR-0020 D8) -> host $?.

    rb16 = SEMI_BLOCK (argument-block pointer); block = {reason, code};
    rd16 = 0x18 (SYS_EXIT); `trap` with the semihosting tag.  The low byte of
    `code` becomes the process status (contract-semihosting.md §3/§5).

    The leading no-op `jump` ends the current TB so that the last `-d cpu` dump
    (the probe's observation channel) captures the caller's state *before* this
    epilogue -- the same role the MMIO halt-device store used to play.
    """
    return ([jump_iiii(1)]
            + [set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF), or_w_rb(16, 0, 0xF000)]
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, TAG)])


def sh_call(num, blk_addr, cfxha=0):
    """rd16 = service number; rb16 = argument-block pointer; semihosting trap."""
    return load_rd(16, num) + set_addr(16, blk_addr) + [trap(cfxha, TAG)]


def set_cfx_vector(cfxha, mode_cg, vec):
    """cfx2rc cfxha, cg=mode_cg, rc=10 (excp_vector) <- rd22."""
    return load_rd(22, vec) + [cfx2rc(cfxha, mode_cg, 10, 22)]


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def blk(*vals):
    """Big-endian 64-bit argument-block fields."""
    return b"".join(struct.pack(">Q", v & 0xFFFFFFFFFFFFFFFF) for v in vals)


def build_rom(prog, handlers=None):
    """prog at ROM offset 0; handlers = {byte offset: word list}; pad to 0x400."""
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers or {}):
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(handlers[off])
    while len(rom) < 0x400:
        rom += words_to_bytes([swym()])
    return bytes(rom)


def build_kernel(data):
    """Kernel image loaded at RAM_BASE; data = {offset: bytes}; pad to 0x800."""
    buf = bytearray(0x800)
    for off, b in data.items():
        buf[off:off + len(b)] = b
    return bytes(buf)


# ---------------------------------------------------------------------------
# QEMU runner + dump parsing
# ---------------------------------------------------------------------------

def run(rom, kern, inb=b"", args="dadao046"):
    os.makedirs(WORKDIR, exist_ok=True)
    rp = os.path.join(WORKDIR, "rom.bin")
    kp = os.path.join(WORKDIR, "kernel.bin")
    ip = os.path.join(WORKDIR, "in.bin")
    op = os.path.join(WORKDIR, "out.bin")
    lp = os.path.join(WORKDIR, "cpu.log")
    with open(rp, "wb") as f:
        f.write(rom)
    with open(kp, "wb") as f:
        f.write(kern)
    with open(ip, "wb") as f:
        f.write(inb)
    if os.path.exists(op):
        os.remove(op)
    cmd = [QEMU, "-M", "dadao-m1", "-nographic", "-bios", rp, "-kernel", kp,
           "-d", "cpu", "-D", lp,
           "-chardev", "file,id=semi,path=%s,input-path=%s" % (op, ip),
           "-semihosting-config",
           "enable=on,target=native,chardev=semi,arg=%s" % args]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, text=True)
        rc = r.returncode & 0xFF
        err = r.stderr
    except subprocess.TimeoutExpired:
        return None, "", b"", "TIMEOUT"
    with open(lp) as f:
        log = f.read()
    out = open(op, "rb").read() if os.path.exists(op) else b""
    return rc, log, out, err


def _lasthex(log, pat):
    m = None
    for x in re.finditer(pat, log):
        m = x
    return int(m.group(1), 16) if m else None


def observe(log):
    """Extract observed state from the LAST dump block."""
    o = {}
    o["pc"] = _lasthex(log, r"PC: ([0-9a-f]+)")
    for ha in (0,):
        t = "CFX%02d" % ha
        o["cid:%d" % ha] = _lasthex(log, t + r" PREVM:[^\n]* CID:([0-9a-f]+)")
        o["trapn:%d" % ha] = _lasthex(log, t + r" ID:[^\n]* TRAPN:([0-9a-f]+)")
    for n in range(0, 64):
        o["rd%d" % n] = _lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    return o


# ---------------------------------------------------------------------------
# Case model + builders
# ---------------------------------------------------------------------------

CASES = []   # (name, desc, services, builder)
COVERED_SERVICES = set()


def case(name, desc, services=()):
    def deco(fn):
        CASES.append((name, desc, tuple(services), fn))
        return fn
    return deco


def _file(name, data=b""):
    return os.path.join(WORKDIR, name)


def _std_rom(prog, handlers=None):
    return build_rom(prog, handlers)


# -- acc 2: semihosting tag -> served, PC+=4, never enters the vector --------
@case("semihost_tag_path", "immu18[17:16]==2'b11 => semihosting, PC+=4, no vector",
      services=[0x31])
def _semihost_tag_path():
    # cfx0 hypv vector -> handler that exits 0xEE (the "vector entered" marker).
    prog = set_cfx_vector(0, 3, H)
    trap_idx = len(prog)
    prog += sh_call(0x31, 0)          # TICKFREQ: returns 1000000000
    prog += exit_seq(0x5A)
    exp = {"exit": 0x5A, "rd31": 1000000000, "rd30": 0,
           "cid:0": 0, "trapn:0": 0}
    handlers = {0x100: exit_seq(0xEE)}
    return _std_rom(prog, handlers), build_kernel({}), b"", exp


# -- acc 2: the semihosting tag is independent of cfxha ---------------------
@case("semihost_cfxha_agnostic",
      "semihosting tag is honoured with a reserved cfxha (7)",
      services=[0x31])
def _semihost_cfxha_agnostic():
    # cfxha 7 is reserved (SimRISC-11: reserved => ILLI) for a general trap.
    # With the semihosting tag it must still be served, proving the tag decides
    # and cfxha is irrelevant (Machine-01 §5.1 / ADR-0020 D1).
    prog = sh_call(0x31, 0, cfxha=7)
    prog += exit_seq(0x5E)
    exp = {"exit": 0x5E, "rd31": 1000000000}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 2: general trap (tag miss) -> CFXTRAP enters the vector -------------
@case("general_trap_path", "immu18[17:16]!=2'b11 => CFXTRAP enters vector",
      services=[])
def _general_trap_path():
    prog = set_cfx_vector(0, 3, H)
    trap_idx = len(prog)
    prog += [trap(0, 0x0123)]         # tag miss
    prog += exit_seq(0xEE)            # only reached if the vector was NOT taken
    exp = {"exit": 0x42, "cid:0": CFXTRAP, "trapn:0": 1}
    handlers = {0x100: exit_seq(0x42)}
    return _std_rom(prog, handlers), build_kernel({}), b"", exp


# -- acc 3: bank selection (n=0 -> rd16) ------------------------------------
@case("bank_num_rd16", "common_semi_arg(cs,0) reads rd16 (rd17 decorrelated)",
      services=[0x31])
def _bank_num_rd16():
    # rd16 = TICKFREQ (0x31); rd17 = TIME (0x11).  If the hook read the wrong
    # register the responder would dispatch TIME and rd31 would not be 1e9.
    prog = load_rd(16, 0x31) + load_rd(17, 0x11)
    prog += set_addr(16, 0) + [trap(0, TAG)]
    prog += exit_seq(0x5B)
    exp = {"exit": 0x5B, "rd31": 1000000000}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 3: bank selection (n=1 -> rb16) ------------------------------------
@case("bank_arg_rb16", "common_semi_arg(cs,1) reads rb16 (rb17 decorrelated)",
      services=[0x08])
def _bank_arg_rb16():
    # ISERROR(block@rb16 = {-1}) => 1.  rb17 points at a zeroed block; if the
    # hook read rb17 the status word would be 0 and the result 0.
    prog = load_rd(16, 0x08)
    prog += set_addr(16, RAM_BASE + K_SVC)
    prog += set_addr(17, RAM_BASE + K_BUF)
    prog += [trap(0, TAG)]
    prog += exit_seq(0x5C)
    exp = {"exit": 0x5C, "rd31": 1}
    kern = build_kernel({K_SVC: blk(0xFFFFFFFFFFFFFFFF), K_BUF: blk(0)})
    return _std_rom(prog), kern, b"", exp


# -- acc 3: return value goes to rd31, rd30 untouched -----------------------
@case("ret_rd31", "semihosting return is written to rd31 only",
      services=[0x11])
def _ret_rd31():
    # TIME (0x11) returns a non-zero epoch second count; rd30 must stay 0.
    prog = sh_call(0x11, 0)
    prog += exit_seq(0x5D)
    exp = {"exit": 0x5D, "rd31": PRESENT, "rd30": 0}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 4: SVC_OPEN --------------------------------------------------------
@case("svc_open", "SYS_OPEN returns a handle", services=[0x01])
def _svc_open():
    path = _file("semi_a.txt").encode() + b"\0"
    prog = sh_call(0x01, RAM_BASE + K_OPEN)
    prog += exit_seq(0x60)
    kern = build_kernel({K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path) - 1),
                         K_PATH: path})
    exp = {"exit": 0x60, "rd31": 1}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_CLOSE -------------------------------------------------------
@case("svc_close", "SYS_CLOSE of an open handle returns 0", services=[0x02])
def _svc_close():
    path = _file("semi_a.txt").encode() + b"\0"
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x01, RAM_BASE + K_OPEN)   # OPEN
    prog += [st_o(31, 1, K_SVC + 0)]           # handle -> svc block
    prog += sh_call(0x02, RAM_BASE + K_SVC)    # CLOSE
    prog += exit_seq(0x61)
    kern = build_kernel({K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path) - 1),
                         K_PATH: path})
    exp = {"exit": 0x61, "rd31": 0}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_WRITEC ------------------------------------------------------
@case("svc_writec", "SYS_WRITEC writes one byte to the console",
      services=[0x03])
def _svc_writec():
    prog = sh_call(0x03, RAM_BASE + K_STR)
    prog += exit_seq(0x62)
    exp = {"exit": 0x62, "rd31": 0xdeadbeef, "out": b"Y"}
    return _std_rom(prog), build_kernel({K_STR: b"Y"}), b"", exp


# -- acc 4: SVC_WRITE0 ------------------------------------------------------
@case("svc_write0", "SYS_WRITE0 writes a NUL-terminated string",
      services=[0x04])
def _svc_write0():
    prog = sh_call(0x04, RAM_BASE + K_STR)
    prog += exit_seq(0x63)
    exp = {"exit": 0x63, "rd31": 0xdeadbeef, "out": b"hi046"}
    return _std_rom(prog), build_kernel({K_STR: b"hi046\0"}), b"", exp


# -- acc 4: SVC_WRITE -------------------------------------------------------
@case("svc_write", "SYS_WRITE writes a buffer to a host file", services=[0x05])
def _svc_write():
    path = _file("semi_b.txt").encode() + b"\0"
    if os.path.exists(_file("semi_b.txt")):
        os.remove(_file("semi_b.txt"))
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x01, RAM_BASE + K_OPEN)   # OPEN(write)
    prog += [st_o(31, 1, K_SVC + 0)]           # handle
    prog += sh_call(0x05, RAM_BASE + K_SVC)    # WRITE
    prog += exit_seq(0x64)
    kern = build_kernel({K_OPEN: blk(RAM_BASE + K_PATH, 4, len(path) - 1),
                         K_SVC: blk(0, RAM_BASE + K_BUF, 4),
                         K_PATH: path, K_BUF: b"WXYZ"})
    exp = {"exit": 0x64, "rd31": 0, "file": ("semi_b.txt", b"WXYZ")}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_READ --------------------------------------------------------
@case("svc_read", "SYS_READ reads a host file into a buffer",
      services=[0x06])
def _svc_read():
    path = _file("semi_a.txt").encode() + b"\0"
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x01, RAM_BASE + K_OPEN)   # OPEN(read)
    prog += [st_o(31, 1, K_SVC + 0)]           # handle
    prog += sh_call(0x06, RAM_BASE + K_SVC)    # READ
    prog += [ld_o(50, 1, K_BUF)]
    prog += exit_seq(0x65)
    kern = build_kernel({K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path) - 1),
                         K_SVC: blk(0, RAM_BASE + K_BUF, 8),
                         K_PATH: path})
    exp = {"exit": 0x65, "rd31": 0, "rd50": 0x4142434445464748}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_READC -------------------------------------------------------
@case("svc_readc", "SYS_READC reads one character from the console",
      services=[0x07])
def _svc_readc():
    # READC uses common_semi_stack_bottom()-1 = rb1-1 as the 1-byte buffer.
    prog = set_addr(1, RAM_BASE + K_BUF + 1)
    prog += sh_call(0x07, 0)
    prog += exit_seq(0x66)
    exp = {"exit": 0x66, "rd31": 0x51}
    return _std_rom(prog), build_kernel({}), b"Q", exp


# -- acc 4: SVC_ISERROR -----------------------------------------------------
@case("svc_iserror", "SYS_ISERROR of a negative status word returns non-zero",
      services=[0x08])
def _svc_iserror():
    prog = sh_call(0x08, RAM_BASE + K_SVC)
    prog += exit_seq(0x67)
    exp = {"exit": 0x67, "rd31": 1}
    return _std_rom(prog), build_kernel({K_SVC: blk(0xFFFFFFFFFFFFFFFF)}), b"", exp


# -- acc 4: SVC_ISTTY -------------------------------------------------------
@case("svc_istty", "SYS_ISTTY of a plain file returns 0", services=[0x09])
def _svc_istty():
    path = _file("semi_a.txt").encode() + b"\0"
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x01, RAM_BASE + K_OPEN)
    prog += [st_o(31, 1, K_SVC + 0)]
    prog += sh_call(0x09, RAM_BASE + K_SVC)
    prog += exit_seq(0x68)
    kern = build_kernel({K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path) - 1),
                         K_PATH: path})
    exp = {"exit": 0x68, "rd31": 0}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_SEEK --------------------------------------------------------
@case("svc_seek", "SYS_SEEK succeeds (returns 0)", services=[0x0a])
def _svc_seek():
    path = _file("semi_a.txt").encode() + b"\0"
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x01, RAM_BASE + K_OPEN)
    prog += [st_o(31, 1, K_SVC + 0)]
    prog += sh_call(0x0a, RAM_BASE + K_SVC)   # {handle, offset=4}
    prog += exit_seq(0x69)
    kern = build_kernel({K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path) - 1),
                         K_SVC: blk(0, 4),
                         K_PATH: path})
    exp = {"exit": 0x69, "rd31": 0}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_FLEN --------------------------------------------------------
@case("svc_flen", "SYS_FLEN reports the host file length", services=[0x0c])
def _svc_flen():
    path = _file("semi_a.txt").encode() + b"\0"
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x01, RAM_BASE + K_OPEN)
    prog += [st_o(31, 1, K_SVC + 0)]
    prog += sh_call(0x0c, RAM_BASE + K_SVC)
    prog += exit_seq(0x6A)
    kern = build_kernel({K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path) - 1),
                         K_PATH: path})
    exp = {"exit": 0x6A, "rd31": 8}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_TMPNAM ------------------------------------------------------
@case("svc_tmpnam", "SYS_TMPNAM writes a temporary name into the buffer",
      services=[0x0d])
def _svc_tmpnam():
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x0d, RAM_BASE + K_SVC)    # {buf, id, buflen}
    prog += [ld_o(50, 1, K_BUF + 0), ld_o(51, 1, K_BUF + 8)]
    prog += exit_seq(0x6B)
    kern = build_kernel({K_SVC: blk(RAM_BASE + K_BUF, 0x11, 128)})
    exp = {"exit": 0x6B, "rd31": 0, "rd50": PRESENT}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_REMOVE ------------------------------------------------------
@case("svc_remove", "SYS_REMOVE deletes an existing host file",
      services=[0x0e])
def _svc_remove():
    c = _file("semi_c.txt")
    with open(c, "wb") as f:
        f.write(b"remove-me")
    path = c.encode() + b"\0"
    prog = sh_call(0x0e, RAM_BASE + K_SVC)
    prog += exit_seq(0x6C)
    kern = build_kernel({K_SVC: blk(RAM_BASE + K_PATH, len(path) - 1),
                         K_PATH: path})
    exp = {"exit": 0x6C, "rd31": 0, "file_absent": "semi_c.txt"}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_RENAME ------------------------------------------------------
@case("svc_rename", "SYS_RENAME renames an existing host file",
      services=[0x0f])
def _svc_rename():
    d = _file("semi_d.txt")
    d2 = _file("semi_d2.txt")
    for p in (d, d2):
        if os.path.exists(p):
            os.remove(p)
    with open(d, "wb") as f:
        f.write(b"rename-me")
    op = d.encode() + b"\0"
    np = d2.encode() + b"\0"
    prog = sh_call(0x0f, RAM_BASE + K_SVC)     # {oname, olen, nname, nlen}
    prog += exit_seq(0x6D)
    kern = build_kernel({K_SVC: blk(RAM_BASE + K_PATH, len(op) - 1,
                                    RAM_BASE + K_SVC2, len(np) - 1),
                         K_PATH: op, K_SVC2: np})
    exp = {"exit": 0x6D, "rd31": 0,
           "file_absent": "semi_d.txt", "file_present": "semi_d2.txt"}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_CLOCK -------------------------------------------------------
@case("svc_clock", "SYS_CLOCK returns a value", services=[0x10])
def _svc_clock():
    prog = sh_call(0x10, 0)
    prog += exit_seq(0x6E)
    exp = {"exit": 0x6E, "rd31": PRESENT}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 4: SVC_TIME --------------------------------------------------------
@case("svc_time", "SYS_TIME returns epoch seconds", services=[0x11])
def _svc_time():
    prog = sh_call(0x11, 0)
    prog += exit_seq(0x6F)
    exp = {"exit": 0x6F, "rd31": PRESENT}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 4: SVC_SYSTEM ------------------------------------------------------
@case("svc_system", "SYS_SYSTEM executes a host command", services=[0x12])
def _svc_system():
    cmd = b"exit 7\0"
    prog = sh_call(0x12, RAM_BASE + K_SVC)     # {cmd, len}
    prog += exit_seq(0x70)
    kern = build_kernel({K_SVC: blk(RAM_BASE + K_STR, len(cmd) - 1),
                         K_STR: cmd})
    exp = {"exit": 0x70, "rd31": 0x700}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_ERRNO -------------------------------------------------------
@case("svc_errno", "SYS_ERRNO returns the host errno (0 with no prior error)",
      services=[0x13])
def _svc_errno():
    prog = sh_call(0x13, 0)
    prog += exit_seq(0x71)
    exp = {"exit": 0x71, "rd31": 0}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 4: SVC_GET_CMDLINE -------------------------------------------------
@case("svc_get_cmdline", "SYS_GET_CMDLINE writes the semihosting argv",
      services=[0x15])
def _svc_get_cmdline():
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x15, RAM_BASE + K_SVC)    # {buf, buflen}
    prog += [ld_o(50, 1, K_BUF)]
    prog += exit_seq(0x72)
    kern = build_kernel({K_SVC: blk(RAM_BASE + K_BUF, 128)})
    # arg=dadao046 -> cmdline "dadao046"; first 8 bytes big-endian.
    exp = {"exit": 0x72, "rd31": 0, "rd50": 0x646164616F303436}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_HEAPINFO ----------------------------------------------------
@case("svc_heapinfo", "SYS_HEAPINFO writes the heap/stack parameters",
      services=[0x16])
def _svc_heapinfo():
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x16, RAM_BASE + K_SVC)    # {heap_base,..,stack_limit}
    prog += [ld_o(50, 1, K_SVC + 0)]
    prog += exit_seq(0x73)
    kern = build_kernel({K_SVC: blk(0, 0, 0, 0)})
    exp = {"exit": 0x73, "rd31": 0, "rd50": PRESENT}
    return _std_rom(prog), kern, b"", exp


# -- acc 4/5: SVC_EXIT ------------------------------------------------------
@case("svc_exit", "SYS_EXIT propagates the status code to host $?",
      services=[0x18])
def _svc_exit():
    prog = sh_call(0x18, RAM_BASE + K_SVC)     # {reason, subcode}
    prog += exit_seq(0xEE)                     # unreachable if EXIT works
    kern = build_kernel({K_SVC: blk(ADP_STOPPED_APPLICATION_EXIT, 0x42)})
    exp = {"exit": 0x42}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_SYNCCACHE ---------------------------------------------------
@case("svc_synccache", "SYS_SYNCCACHE returns success", services=[0x19])
def _svc_synccache():
    prog = sh_call(0x19, 0)
    prog += exit_seq(0x74)
    exp = {"exit": 0x74, "rd31": 0}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 4/5: SVC_EXIT_EXTENDED --------------------------------------------
@case("svc_exit_extended", "SYS_EXIT_EXTENDED propagates its exit code",
      services=[0x20])
def _svc_exit_extended():
    prog = sh_call(0x20, RAM_BASE + K_SVC)     # {reason, exitcode}
    prog += exit_seq(0xEE)
    kern = build_kernel({K_SVC: blk(ADP_STOPPED_APPLICATION_EXIT, 0x43)})
    exp = {"exit": 0x43}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_ELAPSED -----------------------------------------------------
@case("svc_elapsed", "SYS_ELAPSED returns 0 and writes the tick count",
      services=[0x30])
def _svc_elapsed():
    prog = set_addr(1, RAM_BASE)
    prog += sh_call(0x30, RAM_BASE + K_SVC)
    prog += [ld_o(50, 1, K_SVC + 0)]
    prog += exit_seq(0x75)
    kern = build_kernel({K_SVC: blk(0)})
    exp = {"exit": 0x75, "rd31": 0, "rd50": PRESENT}
    return _std_rom(prog), kern, b"", exp


# -- acc 4: SVC_TICKFREQ ----------------------------------------------------
@case("svc_tickfreq", "SYS_TICKFREQ returns the tick frequency",
      services=[0x31])
def _svc_tickfreq():
    prog = sh_call(0x31, 0)
    prog += exit_seq(0x76)
    exp = {"exit": 0x76, "rd31": 1000000000}
    return _std_rom(prog), build_kernel({}), b"", exp


# -- acc 6: 64-bit big-endian argument block --------------------------------
@case("iserror_be64", "argument block field read as 64-bit big-endian",
      services=[0x08])
def _iserror_be64():
    # 0x8000000000000001 has bit63 set => negative as int64 => ISERROR=1.
    # A little-endian read (0x0100000000000080) or a 32-bit read would be
    # positive => ISERROR=0.
    prog = sh_call(0x08, RAM_BASE + K_SVC)
    prog += exit_seq(0x77)
    exp = {"exit": 0x77, "rd31": 1}
    return _std_rom(prog), build_kernel({K_SVC: blk(0x8000000000000001)}), b"", exp


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _expected_file(path):
    return os.path.exists(os.path.join(WORKDIR, path))


def run_case(name):
    global COVERED_SERVICES
    for n, d, svcs, fn in CASES:
        if n == name:
            rom, kern, inb, exp = fn()
            rc, log, out, err = run(rom, kern, inb)
            if rc is None:
                return False, "TIMEOUT", exp
            obs = observe(log)
            obs["exit"] = rc
            obs["out"] = out
            COVERED_SERVICES |= set(svcs)
            diffs = []
            for k, v in exp.items():
                if k == "file":
                    fname, fdata = v
                    got = open(os.path.join(WORKDIR, fname), "rb").read() \
                        if os.path.exists(os.path.join(WORKDIR, fname)) else None
                    if got != fdata:
                        diffs.append("file %s exp=%r got=%r" % (fname, fdata, got))
                    continue
                if k == "file_absent":
                    if _expected_file(v):
                        diffs.append("file %s expected absent but present" % v)
                    continue
                if k == "file_present":
                    if not _expected_file(v):
                        diffs.append("file %s expected present but absent" % v)
                    continue
                av = obs.get(k)
                if v is PRESENT:
                    if av is None:
                        diffs.append("%s exp=PRESENT got=None" % k)
                elif av != v:
                    diffs.append("%s exp=%s got=%s" % (
                        k, ("0x%x" % v) if isinstance(v, int) else v,
                        ("0x%x" % av) if isinstance(av, int) else av))
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
        for n, d, svcs, _ in CASES:
            print("%-20s services=%s  %s" % (
                n, ",".join("0x%02x" % s for s in svcs), d))
        print("distinct service ids covered: %d" % len(set(
            s for _, _, svcs, _ in CASES for s in svcs)))
        print("required service ids: %d" % len(SERVICE_IDS))
        return 0

    if not os.path.isfile(QEMU):
        print("[FAIL] QEMU binary not found: %s" % QEMU)
        return 2

    os.makedirs(WORKDIR, exist_ok=True)
    # Fixtures: file A read by the OPEN/READ/SEEK/FLEN/ISTTY/CLOSE cases.
    with open(_file("semi_a.txt"), "wb") as f:
        f.write(b"ABCDEFGH")

    selected = [(n, d) for (n, d, _s, _f) in CASES
                if args.only is None or n == args.only]
    if not selected:
        print("[FAIL] no case named %r" % args.only)
        return 1

    all_ok = True
    covered = set()
    for name, desc in selected:
        passed, detail, exp = run_case(name)
        for n, d, svcs, _ in CASES:
            if n == name:
                covered |= set(svcs)
        print("[%s] %-20s %s -> %s" % ("PASS" if passed else "FAIL", name, desc, detail))
        if not passed:
            all_ok = False

    # Service coverage is only meaningful for a full run.
    if args.only is None:
        missing = SERVICE_IDS - covered
        if missing:
            print("[FAIL] service ids not covered: %s"
                  % ",".join("0x%02x" % s for s in sorted(missing)))
            all_ok = False
        else:
            print("[PASS] service coverage: all %d service ids exercised"
                  % len(SERVICE_IDS))

    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
