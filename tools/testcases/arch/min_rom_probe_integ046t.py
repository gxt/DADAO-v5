#!/usr/bin/env python3
"""INTEG-046t probe: step5 BootROM chain, Machine-v5-Vast current layout.

Expectations come from the frozen interface sources, not from the firmware
implementation:
  * tests/shared/bootrom/step5/README.md + hmon.S/power.S (the shipped
    power -> hmon -> test-body chain; smon is reserved and not entered --
    user ruling 2026-11-02 / ADR-0043 D1/D4);
  * .tao/tasks/integ/INTEG-046t-Step5启动链落地.md §接口规范 1/2/5 (image
    index table, ELF checks, failure codes 0xB1-0xB8);
  * spec/DADAO-12 §2.2.3 + ADR-0043 D10 (identity superpage PTE:
    HSJU=0xC (H=1,S=1,U=J=0), PPN[55:29]=i, SPF=0xFF, flags 0xEF); DADAO-13 §1 +
    ADR-0045 D4 (hypv cg3 reset rows / cg_reg_deleg).
  * tests/shared/machine-profiles.yaml (vast) for every address/size.

Layout driven here:
  * 4 MiB `bootrom-image` (Vast) at BOOTROM_BASE; no `-bios`;
  * `-kernel` supplies the **test body** at `kernel_base` (0x10_0000,
    `kernel_reserved=0`): hmon programs `cfx_umon.hypv.excp_vector = ENTRY`
    and traps there, so the body must exist or the chain ends in UNDI
    (`TESTCASES-094t §4`, task book E5);
  * the body is built here (raw words), runs as cfx_umon in hypv with PTW on,
    records its observations into rd5..rd30 and exits via semihosting.

Observation channels: the last `-d cpu` dump block (rd5-rd30, PTB R/PTW,
cfx rows), stage PCs inside the four `-dfilter` windows, and host `$?`
(SYS_EXIT status: 0, or the 0xB1-0xB8 firmware error codes).

Every runtime case compares exact values or exact stage presence, and every
negative case patches the image and asserts the specific failure code, so both
kinds have a reachable FAIL path.

Usage:
  min_rom_probe_integ046t.py [--qemu PATH] [--bootrom-image PATH]
                              [--only NAME] [--list]
Exit code: 0 iff every requested check passed.
"""

import argparse
import os
import re
import struct
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
for _sub in (("tools", "testcases", "lib"), ("tools", "testcases", "arch"),
             ("tools", "infra")):
    _p = os.path.join(_REPO, *_sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import machine_profile as _machine_profile  # noqa: E402
import node_probe_prelude as _prelude  # noqa: E402

_MACH = _machine_profile.load(os.environ.get("DADAO_TEST_PROFILE") or "vast")
BOOTROM_BASE = _MACH.bootrom_base
BOOTROM_SIZE = _MACH["bootrom_size"]
RESET_PC = _MACH.reset_pc
ENTRY = _MACH.entry
IMAGE_WINDOW = _MACH["image_window"]
KERNEL_BASE = _MACH["kernel_base"]
RAM_BASE = _MACH.ram_base
EXIT_BLOCK = _MACH.exit_block

DEFAULT_QEMU = _prelude.default_qemu()
DEFAULT_BOOTROM = os.path.join(_REPO, ".dadao/tests/bootrom/step5/"
                                     "bootrom_step5.bin")
WORKDIR = os.path.join(_prelude.TMP_ROOT, "min_rom_probe_integ046t")
TIMEOUT = 60

QEMU = DEFAULT_QEMU
BOOTROM_IMAGE = DEFAULT_BOOTROM

# BootROM geometry / image table (task §接口规范 1; same source as
# tools/testcases/arch/build_step5_bootrom.py: POWER_OFF = size - 64 KiB).
HDR_MAGIC = 0x44424F54
HDR_VERSION = 1
HDR_COUNT = 2
BOOT_MAGIC = 0x30001
HDR_WORD = (HDR_MAGIC << 32) | (HDR_VERSION << 16) | HDR_COUNT
COUNT = 2
POWER_WINDOW = 0x10000
POWER_OFF = BOOTROM_SIZE - POWER_WINDOW
POWER_WIN = (RESET_PC, POWER_WINDOW)
BODY_WIN = (ENTRY, IMAGE_WINDOW)

# Identity superpage PTE (spec/DADAO-12 §2.2.3; ADR-0043 D10):
# HSJU=0xC (H=1,S=1,U=J=0), PPN[55:29]=i, SPF=0xFF, flags P/A/D/SP/X/W/R = 0xEF.
PTE = [0xC000_0000_0000_FFEF | (i << 29) for i in range(4)]
# cfx_hmon/cfx_power hypv reset rows (DADAO-13 §1; ADR-0045 D4).
MASK_DEFAULT = 0xFFFF_FFFF_FFFF_FFF7
DELEG_RESET = 0xFFFF_FFFF_FFFF_FFFF
DMA_DONE = 1 << 1

MARK_BODY = 0x424F4459          # "BODY"
MAGIC1 = 0x1122_3344_5566_7788
MAGIC2 = 0x99AA_BBCC_DDEE_FF00
PMEM_SRAM = _prelude.PMEM_BASE + 0x1000

# Failure codes (task §接口规范 5)
E_B1, E_B2, E_B3, E_B4, E_B5, E_B6, E_B7, E_B8 = (
    0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8)

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


def entry_elf(img, typ):
    return be64(img, table_entry(img, typ) + 8)


def elf_entry(img, typ):
    return be64(img, entry_elf(img, typ) + 24)


def first_load_phdr(img, entry_off):
    elf_off = be64(img, entry_off + 8)
    phoff = be64(img, elf_off + 32)
    for i in range(be16(img, elf_off + 56)):
        p = elf_off + phoff + i * 56
        if be32(img, p) == 1:
            return p
    raise AssertionError("no PT_LOAD")


def patch_trap_magic(img, magic):
    """Patch the `trap cfx_hmon, <imm>` word in the power 64 KiB tail.

    The power flat segment lives at [BOOTROM_SIZE - 0x10000, BOOTROM_SIZE)
    (`build_step5_bootrom.py`); a 256 KiB scan window would miss it
    (task book E5).
    """
    for off in range(POWER_OFF, BOOTROM_SIZE - 3, 4):
        w = be32(img, off)
        if (w >> 24) == 0x7F and ((w >> 18) & 0x3F) == 3 and (w & 0x3FFFF) < 0x3FF00:
            struct.pack_into(">I", img, off, (w & ~0x3FFFF) | (magic & 0x3FFFF))
            return
    raise AssertionError("power trap instruction not found in "
                         "[0x%x, 0x%x)" % (POWER_OFF, BOOTROM_SIZE))


# ---------------------------------------------------------------------------
# Test body (runs at ENTRY, cfx_umon/hypv, PTW on)
# ---------------------------------------------------------------------------

def build_kernel():
    """Raw body: identity-map / DMA / cfx observations -> registers -> SYS_EXIT.

    The identity map is set up by hmon, so VA == PA; the round-trip case still
    proves both directions of the cfx_pmem DMA and the PTW mapping.  Register
    slots (rd5..rd7, rd10..rd15, rd17..rd22, rd30) are the dump channel.
    """
    s = _prelude.Seq()
    # PTE readback at PA 0..0x18 (identity map).
    s.e(*_prelude.load_rb(1, RAM_BASE))
    for i, rd in enumerate((10, 11, 12, 13)):
        s.e(_prelude.ld_o(rd, 1, i * 8))
    # Park-poison words (power/hmon must never resume into them).
    s.e(*_prelude.load_rb(2, 0x10100))
    s.e(_prelude.ld_o(14, 2, 0), _prelude.ld_o(15, 2, 8))
    # A cfx_umon/hypv read of the power BootROM is denied: cfx_power's hypv
    # cfxmem keeps source cfx0 masked (MASK_DEFAULT bit0 = 1).  hmon_fault
    # records CFXPERM in the fault slot and resumes after the load, so the
    # body observes the rejection instead of a value.
    s.e(*_prelude.load_rb(3, BOOTROM_BASE))
    s.e(_prelude.ld_o(20, 3, 0))             # rd20 <- never written (denied)
    s.e(*_prelude.load_rb(4, _MACH["fault_record"]))
    s.e(_prelude.ld_o(20, 4, 0))             # rd20 = recorded CFXPERM cause
    s.e(_prelude.cfx2rd(63, 3, 1, 21))       # cfxmem
    s.e(_prelude.cfx2rd(63, 3, 12, 22))      # cg_reg_deleg
    # hmon observations: delegation rows + the page-table DMA status.
    s.e(_prelude.cfx2rd(4, 3, 12, 17))       # cfx_ptw hypv deleg
    s.e(_prelude.cfx2rd(32, 3, 12, 18))      # cfx_pmem hypv deleg
    s.e(_prelude.cfx2rd(32, 15, 4, 19))      # cfx_pmem dma_status
    # VA -> VA readback, then VA -> PMEM DMA -> PA round trip.
    s.e(*_prelude.load_rb(5, 0x20000))
    s.e(*_prelude.load_rd(4, MAGIC1))
    s.e(_prelude.st_o(4, 5, 0))
    s.e(_prelude.ld_o(5, 5, 0))              # rd5 = VA read back
    s.e(*_prelude.load_rb(6, PMEM_SRAM))
    s.e(_prelude.st_o(4, 6, 0))              # SRAM <- MAGIC1
    s.e(*_prelude.load_rd(4, 0))
    s.e(_prelude.st_o(4, 5, 0))              # clear PA 0x20000
    s.e(*_prelude.load_rd(7, PMEM_SRAM))
    s.e(_prelude.cfx2rc(32, 15, 0, 7))       # dma_src = SRAM
    s.e(*_prelude.load_rd(7, 0x20000))
    s.e(_prelude.cfx2rc(32, 15, 1, 7))       # dma_dst = PA
    s.e(*_prelude.load_rd(7, 8))
    s.e(_prelude.cfx2rc(32, 15, 2, 7))       # dma_size
    s.e(*_prelude.load_rd(7, 1))
    s.e(_prelude.cfx2rc(32, 15, 3, 7))       # START, DIR=0 (CFX -> PA)
    dma_poll(s)
    s.e(_prelude.ld_o(6, 5, 0))              # rd6 = PA readback (DMA wrote it)
    # Reverse: PA -> SRAM -> VA.
    s.e(*_prelude.load_rd(4, MAGIC2))
    s.e(_prelude.st_o(4, 5, 8))              # PA 0x20008 <- MAGIC2
    s.e(*_prelude.load_rd(7, 0x20008))
    s.e(_prelude.cfx2rc(32, 15, 0, 7))       # dma_src = PA
    s.e(*_prelude.load_rd(7, PMEM_SRAM + 8))
    s.e(_prelude.cfx2rc(32, 15, 1, 7))       # dma_dst = SRAM + 8
    s.e(*_prelude.load_rd(7, 8))
    s.e(_prelude.cfx2rc(32, 15, 2, 7))
    s.e(*_prelude.load_rd(7, 3))             # DIR=1 (PA -> CFX) | START
    s.e(_prelude.cfx2rc(32, 15, 3, 7))
    dma_poll(s)
    s.e(_prelude.ld_o(7, 6, 8))              # rd7 = SRAM readback of the PA word
    s.e(*_prelude.load_rd(30, MARK_BODY))
    s.e(*_prelude.exit_seq(0))
    return _prelude.words_to_bytes(s.resolve())


def dma_poll(s, rd=8):
    """Spin until cfx_pmem dma_status.BUSY clears."""
    head = "dma_%d" % len(s.w)
    s.mark(head)
    s.e(_prelude.cfx2rd(32, 15, 4, rd))
    s.e(*_prelude.load_rd(9, 1))
    s.e(_prelude.and_o(rd, rd, 9))
    s.b("nz", rd, head)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(image, kernel=None, dump=True):
    os.makedirs(WORKDIR, exist_ok=True)
    ip = os.path.join(WORKDIR, "case.bin")
    lp = os.path.join(WORKDIR, "case.log")
    with open(ip, "wb") as f:
        f.write(image)
    cmd = [QEMU, "-machine",
           "%s,bootrom-image=%s" % (_machine_profile.machine_name(_MACH), ip),
           "-nographic", "-semihosting-config", "enable=on,target=native"]
    if kernel is not None:
        kp = os.path.join(WORKDIR, "body.bin")
        with open(kp, "wb") as f:
            f.write(kernel)
        cmd += ["-kernel", kp]
    if dump:
        cmd += ["-d", "cpu", "-dfilter", dfilter(image), "-D", lp]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT,
                              text=True)
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
                              r"VEC:([0-9a-f]+)", ln)
                if m:
                    blk["swmode:%s:%s" % (m.group(1), m.group(2))] = int(m.group(3), 16)
                    blk["vec:%s:%s" % (m.group(1), m.group(2))] = int(m.group(4), 16)
            blocks.append(blk)
    return rc, blocks, err


def dfilter(image):
    """The four windows that can execute: power, hmon, test body, smon."""
    hmon = elf_entry(image, 1)
    smon = elf_entry(image, 2)
    return ",".join("0x%x+0x%x" % (base, size) for base, size in (
        (POWER_WIN[0], POWER_WIN[1]),
        (hmon, POWER_WINDOW),
        (BODY_WIN[0], BODY_WIN[1]),
        (smon, POWER_WINDOW),
    ))


def in_win(pc, win):
    return pc is not None and win[0] <= pc < win[0] + win[1]


def last(blocks):
    return blocks[-1] if blocks else {}


def stage_block(blocks, win, cfxcode, mode):
    for b in blocks:
        if (in_win(b.get("pc"), win) and b.get("cfxcode") == cfxcode
                and b.get("mode") == mode):
            return b
    return None


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def base_image():
    with open(BOOTROM_IMAGE, "rb") as f:
        img = f.read()
    if len(img) != BOOTROM_SIZE:
        raise AssertionError("bootrom image is %d bytes, profile expects %d"
                             % (len(img), BOOTROM_SIZE))
    return bytearray(img)


def load_negative(patch):
    img = base_image()
    patch(img)
    return bytes(img)


def check(checks):
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return (not bad), ("ok" if not bad else "mismatch %r" % bad)


@case("chain_basic", "power->hmon->body(ENTRY) execute; rc=0; body marker")
def _chain_basic():
    img = base_image()
    rc, blocks, _ = run(img, kernel=build_kernel())
    if rc is None:
        return False, "TIMEOUT"
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "power_pc/mode": (stage_block(blocks, POWER_WIN, 63, 3) is not None, True),
        "hmon_pc/mode": (stage_block(blocks, (elf_entry(img, 1), POWER_WINDOW),
                                     3, 3) is not None, True),
        "body_pc/mode": (stage_block(blocks, BODY_WIN, 0, 3) is not None, True),
        "rd30(body marker)": (o.get("rd30"), MARK_BODY),
    })


@case("vectors", "hmon/umon vectors; smon is reserved (never entered)")
def _vectors():
    img = base_image()
    rc, blocks, _ = run(img, kernel=build_kernel())
    hmon = elf_entry(img, 1)
    smon = elf_entry(img, 2)
    o = last(blocks)
    smon_blocks = [b for b in blocks
                   if in_win(b.get("pc"), (smon, POWER_WINDOW))]
    return check({
        "rc": (rc, 0),
        "cfx_hmon M3 VEC": (o.get("vec:03:3"), hmon),
        "cfx_umon M3 VEC": (o.get("vec:00:3"), ENTRY),
        "cfx_umon M3 SWMODE": (o.get("swmode:00:3"), 3),
        "cfx_smon VEC != smon e_entry": (o.get("vec:02:3") != smon, True),
        "cfx_smon M3 SWMODE": (o.get("swmode:02:3"), 3),
        "smon never executed": (len(smon_blocks), 0),
    })


@case("deleg_dump", "hmon observations: deleg rows closed, page-table DMA DONE")
def _deleg_dump():
    rc, blocks, _ = run(base_image(), kernel=build_kernel())
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "rd17(cfx_ptw hypv deleg)": (o.get("rd17"), DELEG_RESET),
        "rd18(cfx_pmem hypv deleg)": (o.get("rd18"), DELEG_RESET),
        "rd19(dma_status)": (o.get("rd19"), DMA_DONE),
    })


@case("power_bootrom_read",
      "cfx0/hypv read of the power BootROM is denied (CFXPERM); power masks stay closed")
def _power_bootrom_read():
    rc, blocks, _ = run(base_image(), kernel=build_kernel())
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "rd20(fault cause)": (o.get("rd20"), 1 << 7),      # CFXPERM
        "rd21(power hypv cfxmem)": (o.get("rd21"), MASK_DEFAULT),
        "rd22(power hypv deleg)": (o.get("rd22"), DELEG_RESET),
    })


@case("ptw_state", "PTBR=0 and PTW_ENABLE=1 in the test body")
def _ptw_state():
    rc, blocks, _ = run(base_image(), kernel=build_kernel())
    body = stage_block(blocks, BODY_WIN, 0, 3)
    return check({
        "rc": (rc, 0),
        "body block": (body is not None, True),
        "ptbr": ((body or {}).get("ptbr"), 0),
        "ptw": ((body or {}).get("ptw"), 1),
    })


@case("pte_value", "identity superpage PTEs at PA 0..0x18 match spec/DADAO-12 §2.2.3")
def _pte_value():
    rc, blocks, _ = run(base_image(), kernel=build_kernel())
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "rd10(PTE0)": (o.get("rd10"), PTE[0]),
        "rd11(PTE1)": (o.get("rd11"), PTE[1]),
        "rd12(PTE2)": (o.get("rd12"), PTE[2]),
        "rd13(PTE3)": (o.get("rd13"), PTE[3]),
    })


@case("va_pa_both_ways", "VA readback + cfx_pmem DMA both directions")
def _va_pa():
    rc, blocks, _ = run(base_image(), kernel=build_kernel())
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "rd5(VA readback)": (o.get("rd5"), MAGIC1),
        "rd6(DMA CFX->PA readback)": (o.get("rd6"), MAGIC1),
        "rd7(DMA PA->CFX then VA readback)": (o.get("rd7"), MAGIC2),
    })


@case("no_resume_poison", "power/hmon park-poison words stay 0")
def _no_poison():
    rc, blocks, _ = run(base_image(), kernel=build_kernel())
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "rd14(poison 0x10100)": (o.get("rd14"), 0),
        "rd15(poison 0x10108)": (o.get("rd15"), 0),
    })


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
        hmon = elf_entry(img, 1)
        ph = first_load_phdr(img, table_entry(img, 1))
        put64(img, ph + 24, hmon + 0x10000)    # p_paddr
        put64(img, ph + 16, hmon + 0x10000)    # p_vaddr
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B5, "rc=%r expected 0x%02x" % (rc, E_B5)


@case("smon_not_required_bad_elf",
      "smon REQUIRED=0 + bad smon ELF: smon is reserved, chain still reaches body")
def _smon_not_required():
    def p(img):
        off = table_entry(img, 2)
        struct.pack_into(">I", img, off + 4, be32(img, off + 4) & ~FLAG_REQUIRED)
        elf = be64(img, off + 8)
        img[elf] = 0
    rc, blocks, _ = run(load_negative(p), kernel=build_kernel())
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "rd30(body marker)": (o.get("rd30"), MARK_BODY),
    })


@case("hmon_magic_mismatch", "power hands a different boot magic => hmon 0xB7")
def _magic_mismatch():
    def p(img):
        struct.pack_into(">I", img, 8, 0x30002)
        patch_trap_magic(img, 0x30002)
    rc, _, _ = run(load_negative(p), dump=False)
    return rc == E_B7, "rc=%r expected 0x%02x" % (rc, E_B7)


@case("flags_verify_off", "VERIFY=0 still loads a valid ELF; chain reaches body")
def _verify_off():
    def p(img):
        for typ in (1, 2):
            off = table_entry(img, typ)
            struct.pack_into(">I", img, off + 4,
                             be32(img, off + 4) & ~FLAG_VERIFY)
    rc, blocks, _ = run(load_negative(p), kernel=build_kernel())
    o = last(blocks)
    return check({
        "rc": (rc, 0),
        "rd30(body marker)": (o.get("rd30"), MARK_BODY),
    })


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
