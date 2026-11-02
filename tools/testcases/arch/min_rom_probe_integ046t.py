#!/usr/bin/env python3
"""INTEG-046t probe: step5 BootROM chain (power -> hmon -> smon).

Expectations come from the task's interface spec
(.tao/tasks/integ/INTEG-046t-Step5启动链落地.md §接口规范 1/2/3/5) and
ADR-0043 D1/D2/D4/D5/D8/D9/D10/D11/D13/D14, not from the firmware code.

The probe drives the 256 KiB BootROM through the new machine property:

  qemu-system-dadao -M dadao-m1,bootrom-image=step5.bin \
      -semihosting-config enable=on,target=native -d cpu -dfilter ...

Observation channels:
  * the last `-d cpu` dump block (rd5-rd14, PTBR/PTW_ENABLE, cfx vectors);
  * host `$?` = SYS_EXIT status (:0, or the 0xB1-0xB9 failure codes);
  * stage PCs in the dump blocks (dfilter keeps only the three stage windows).

Every negative case patches the baseline image on disk (table header/flags/
sizes, an ELF header/segment field, or the power handoff immediate) and
asserts the *specific* failure code; a case fails when the expected code is
not observed, so each has a reachable FAIL path.

Usage:
  min_rom_probe_integ046t.py [--qemu PATH] [--bootrom-image PATH]
                              [--only NAME] [--list]
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
DEFAULT_BOOTROM = os.path.join(_REPO, ".dadao/tests/bootrom/step5/bootrom_step5.bin")
WORKDIR = "/tmp/opencode/INTEG-046t/probe"
TIMEOUT = 60

QEMU = DEFAULT_QEMU
BOOTROM_IMAGE = DEFAULT_BOOTROM

# BootROM geometry / table (task §接口规范 1)
ROM_BASE = 0xFFFF_FFFC_0000
ROM_SIZE = 0x40000
POWER_OFF = 0x30000
HDR_MAGIC = 0x44424F54
BOOT_MAGIC = 0x30001
COUNT = 2

# Stage windows and cfx/mode (ADR-0043 D1/D4/D5)
POWER_WIN = (0xFFFF_FFFF_0000, 0x1_0000)
HMON_WIN = (0x0FFF_0000_0000, 0x1_0000)
SMON_WIN = (0x0BFF_0000_0000, 0x1_0000)
H_ENTRY = HMON_WIN[0]
S_ENTRY = SMON_WIN[0]

# Observations (firmware writes these into rd10-rd14; task §接口规范 3)
MARK_POWER = 0x504F5745   # "POWE"
MARK_HMON = 0x484D4F4E    # "HMON"
MARK_SMON = 0x534D4F4E    # "SMON"
MAGIC1 = 0x1122_3344_5566_7788
MAGIC2 = 0x99AA_BBCC_DDEE_FF00
PTE = 0x4000_0000_0000_FFE3

# Failure codes (task §接口规范 5)
E_B1, E_B2, E_B3, E_B4, E_B5, E_B6, E_B7, E_B8, E_B9 = (
    0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9)

FLAG_REQUIRED, FLAG_LOAD, FLAG_VERIFY = 1, 2, 4


def be16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def be32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def be64(b, o):
    return struct.unpack_from(">Q", b, o)[0]


def put64(b, o, v):
    struct.pack_into(">Q", b, o, v)


def table_entry(img, typ):
    for i in range(COUNT):
        off = 16 + i * 32
        if be32(img, off) == typ:
            return off
    raise AssertionError("entry type %d missing" % typ)


def elf_phoff(img, entry_off):
    elf_off = be64(img, entry_off + 8)
    return elf_off, be64(img, elf_off + 32)


def first_load_phdr(img, entry_off):
    elf_off, phoff = elf_phoff(img, entry_off)
    for i in range(be16(img, elf_off + 56)):
        p = elf_off + phoff + i * 56
        if be32(img, p) == 1:
            return p
    raise AssertionError("no PT_LOAD")


def patch_trap_magic(img, magic):
    """Patch the first `trap cfx_hmon, <imm>` word in the power window."""
    for off in range(POWER_OFF, ROM_SIZE - 3, 4):
        w = be32(img, off)
        if (w >> 24) == 0x7F and ((w >> 18) & 0x3F) == 3 and (w & 0x3FFFF) < 0x3FF00:
            struct.pack_into(">I", img, off, (w & ~0x3FFFF) | (magic & 0x3FFFF))
            return
    raise AssertionError("power trap instruction not found")


def run(image, dump=True):
    os.makedirs(WORKDIR, exist_ok=True)
    ip = os.path.join(WORKDIR, "case.bin")
    lp = os.path.join(WORKDIR, "case.log")
    with open(ip, "wb") as f:
        f.write(image)
    cmd = [QEMU, "-M", "dadao-m1,bootrom-image=" + ip, "-nographic",
           "-semihosting-config", "enable=on,target=native"]
    if dump:
        cmd += ["-d", "cpu", "-dfilter",
                "0xffffffff0000+0x1000,0x0fff00000000+0x10000,0x0bff00000000+0x10000",
                "-D", lp]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, text=True)
        rc = proc.returncode & 0xFF
        err = proc.stderr
    except subprocess.TimeoutExpired:
        return None, [], "TIMEOUT"
    blocks = []
    if dump and os.path.exists(lp):
        with open(lp, "r", errors="replace") as f:
            text = f.read()
        for chunk in text.split("PC: ")[1:]:
            lines = chunk.splitlines()
            pc = int(lines[0].strip(), 16) if lines else None
            blk = {"pc": pc}
            for ln in lines:
                for m in re.finditer(r"RD\[(\d\d)\]: ([0-9a-f]+)", ln):
                    blk["rd%d" % int(m.group(1))] = int(m.group(2), 16)
                m = re.search(r"^MODE: (\d+)", ln)
                if m:
                    blk["mode"] = int(m.group(1))
                m = re.search(r"^CFXCODE: (\d+)", ln)
                if m:
                    blk["cfxcode"] = int(m.group(1))
                m = re.search(r"^PTBR: ([0-9a-f]+) PTW_ENABLE: (\d+)", ln)
                if m:
                    blk["ptbr"] = int(m.group(1), 16)
                    blk["ptw"] = int(m.group(2))
                m = re.search(r"^CFX([0-9a-f]{2}) M(\d) SWMODE:([0-9a-f]+) "
                              r"SWMASK:[0-9a-f]+ VEC:([0-9a-f]+)", ln)
                if m:
                    blk["swmode:%s:%s" % (m.group(1), m.group(2))] = int(m.group(3), 16)
                    blk["vec:%s:%s" % (m.group(1), m.group(2))] = int(m.group(4), 16)
            blocks.append(blk)
    return rc, blocks, err


def in_win(pc, win):
    return pc is not None and win[0] <= pc < win[0] + win[1]


def last(blocks):
    return blocks[-1] if blocks else {}


def stage_block(blocks, win, cfxcode, mode):
    for b in blocks:
        if in_win(b.get("pc"), win) and b.get("cfxcode") == cfxcode and b.get("mode") == mode:
            return b
    return None


CASES = []


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def base_image():
    with open(BOOTROM_IMAGE, "rb") as f:
        return bytearray(f.read())


def load_negative(patch):
    img = base_image()
    patch(img)
    return bytes(img)


@case("chain_basic", "power->hmon->smon execute; three stage markers; rc=0")
def _chain_basic():
    rc, blocks, err = run(base_image())
    if rc is None:
        return False, "TIMEOUT"
    b_pow = stage_block(blocks, POWER_WIN, 63, 3)
    b_h = stage_block(blocks, HMON_WIN, 3, 3)
    b_s = stage_block(blocks, SMON_WIN, 2, 2)
    o = last(blocks)
    checks = {
        "rc": (rc, 0),
        "power_pc/mode": (b_pow is not None, True),
        "hmon_pc/mode": (b_h is not None, True),
        "smon_pc/mode": (b_s is not None, True),
        "rd10": (o.get("rd10"), MARK_POWER),
        "rd11": (o.get("rd11"), MARK_HMON),
        "rd12": (o.get("rd12"), MARK_SMON),
        "rd13(poison)": (o.get("rd13"), 0),
    }
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("vectors", "cfx_hmon/cfx_smon vectors + smon switch_run_mode")
def _vectors():
    rc, blocks, _ = run(base_image())
    o = last(blocks)
    checks = {
        "rc": (rc, 0),
        "cfx_hmon M3 VEC": (o.get("vec:03:3"), H_ENTRY),
        "cfx_smon M3 VEC": (o.get("vec:02:3"), S_ENTRY),
        "cfx_smon M3 SWMODE": (o.get("swmode:02:3"), 2),
    }
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("deleg_dump", "cfx_ptw/cfx_pmem/cfx_smon cg_reg_deleg = 0x8 (all cg open, bit3 fixed)")
def _deleg_dump():
    rc, blocks, _ = run(base_image())
    o = last(blocks)
    checks = {"rc": (rc, 0),
              "rd17(ptw)": (o.get("rd17"), 0x8),
              "rd18(pmem)": (o.get("rd18"), 0x8),
              "rd19(smon)": (o.get("rd19"), 0x8)}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("power_bootrom_read", "smon reads the power BootROM header; power stays closed")
def _power_bootrom_read():
    rc, blocks, _ = run(base_image())
    o = last(blocks)
    checks = {"rc": (rc, 0),
              "rd20(bootrom hdr)": (o.get("rd20"), 0x4442_4F54_0001_0002),
              "rd21(power supv cfxmem)": (o.get("rd21"), 0xFFFF_FFFF_FFFF_FFF3),
              "rd22(power deleg)": (o.get("rd22"), 0xFFFF_FFFF_FFFF_FFFF)}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("ptw_state", "PTBR=0 and PTW_ENABLE=1 at smon exit")
def _ptw_state():
    rc, blocks, _ = run(base_image())
    o = last(blocks)
    checks = {"rc": (rc, 0), "ptbr": (o.get("ptbr"), 0), "ptw": (o.get("ptw"), 1)}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("pte_value", "DMA from PA 0x8000 returns 0x4000_0000_0000_FFE3")
def _pte_value():
    rc, blocks, _ = run(base_image())
    o = last(blocks)
    checks = {"rc": (rc, 0), "rd14": (o.get("rd14"), PTE)}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("va_pa_both_ways", "VA write->DMA PA read and DMA PA write->VA read")
def _va_pa():
    rc, blocks, _ = run(base_image())
    o = last(blocks)
    checks = {"rc": (rc, 0), "rd5": (o.get("rd5"), MAGIC1),
              "rd6": (o.get("rd6"), MAGIC1), "rd7": (o.get("rd7"), MAGIC2)}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("no_resume_poison", "power/hmon park poison words stay 0")
def _no_poison():
    rc, blocks, _ = run(base_image())
    o = last(blocks)
    checks = {"rc": (rc, 0), "rd13(poison)": (o.get("rd13"), 0)}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("bad_table_magic", "header magic corrupted => 0xB1")
def _bad_table_magic():
    def p(img):
        img[0] ^= 0xFF
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B1, "rc=%r expected 0x%02x" % (rc, E_B1)


@case("flags_sbz", "entry flags bit3 set => 0xB2")
def _flags_sbz():
    def p(img):
        off = table_entry(img, 1)
        struct.pack_into(">I", img, off + 4, be32(img, off + 4) | 8)
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B2, "rc=%r expected 0x%02x" % (rc, E_B2)


@case("image_oversize", "hmon table size > 64 KiB => 0xB3")
def _image_oversize():
    def p(img):
        off = table_entry(img, 1)
        put64(img, off + 16, 0x10001)
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B3, "rc=%r expected 0x%02x" % (rc, E_B3)


@case("bad_elf_header", "hmon ELF magic corrupted => 0xB4")
def _bad_elf_header():
    def p(img):
        off = be64(img, table_entry(img, 1) + 8)
        img[off] = 0
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B4, "rc=%r expected 0x%02x" % (rc, E_B4)


@case("bad_elf_segment", "hmon PT_LOAD outside hmon SRAM => 0xB5")
def _bad_elf_segment():
    def p(img):
        ph = first_load_phdr(img, table_entry(img, 1))
        put64(img, ph + 24, H_ENTRY + 0x10000)
        put64(img, ph + 16, H_ENTRY + 0x10000)
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B5, "rc=%r expected 0x%02x" % (rc, E_B5)


@case("smon_not_required_bad_elf", "smon REQUIRED=0 + bad ELF: skipped, chain fails visibly")
def _smon_not_required():
    def p(img):
        off = table_entry(img, 2)
        struct.pack_into(">I", img, off + 4, be32(img, off + 4) & ~FLAG_REQUIRED)
        elf = be64(img, off + 8)
        img[elf] = 0
    rc, blocks, _ = run(load_negative(p))
    o = last(blocks)
    not_all_markers = not (o.get("rd10") == MARK_POWER and
                           o.get("rd11") == MARK_HMON and
                           o.get("rd12") == MARK_SMON)
    ok = rc is not None and rc != 0 and not_all_markers
    return ok, "rc=%r markers=%s" % (rc, (o.get("rd10"), o.get("rd11"), o.get("rd12")))


@case("hmon_magic_mismatch", "power hands a different boot magic => hmon 0xB7")
def _magic_mismatch():
    def p(img):
        struct.pack_into(">I", img, 8, 0x30002)
        patch_trap_magic(img, 0x30002)
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B7, "rc=%r expected 0x%02x" % (rc, E_B7)


@case("flags_verify_off", "VERIFY=0 still loads a valid ELF; chain passes")
def _verify_off():
    def p(img):
        for typ in (1, 2):
            off = table_entry(img, typ)
            struct.pack_into(">I", img, off + 4,
                             be32(img, off + 4) & ~FLAG_VERIFY)
    rc, blocks, _ = run(load_negative(p))
    o = last(blocks)
    ok = (rc == 0 and o.get("rd10") == MARK_POWER and
          o.get("rd11") == MARK_HMON and o.get("rd12") == MARK_SMON)
    return ok, "rc=%r rd10-12=%s" % (rc, (o.get("rd10"), o.get("rd11"), o.get("rd12")))


def main():
    global QEMU, BOOTROM_IMAGE
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--bootrom-image", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.qemu:
        QEMU = args.qemu
    BOOTROM_IMAGE = args.bootrom_image or DEFAULT_BOOTROM

    if args.list:
        for n, d, _ in CASES:
            print("%-28s %s" % (n, d))
        return 0
    if not os.path.isfile(QEMU):
        print("[FAIL] QEMU binary not found: %s" % QEMU)
        return 2
    if not os.path.isfile(BOOTROM_IMAGE):
        print("[FAIL] bootrom image not found: %s (run make build-bootrom)" %
              BOOTROM_IMAGE)
        return 2

    names = [args.only] if args.only else [n for n, _, _ in CASES]
    failed = 0
    for n in names:
        fn = dict((x, f) for x, _, f in CASES).get(n)
        if fn is None:
            print("FAIL %-28s no such case" % n)
            failed += 1
            continue
        ok, why = fn()
        print("%s %-28s %s" % ("PASS" if ok else "FAIL", n, why))
        if not ok:
            failed += 1
    print("%d/%d passed" % (len(names) - failed, len(names)))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
