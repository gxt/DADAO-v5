#!/usr/bin/env python3
"""k0_boot_probe.py — Machine-v5-Vast K1 boot probe (m14-qemu-001).

Builds the K1 firmware (`tests/shared/bootrom/k0/`: boot hmon + smon) on top of
the reused step5 power stage, builds the minimal raw/ELF probe kernel, runs it
on `qemu-system-dadao -machine dadao-vast,bootrom-image=...,-kernel ...` and
checks the frozen startup ABI of `spec/Machine-v5 §6.3` field by field.

Expectation sources (never the implementation):
  * `contracts/linux-boot.yaml` — boot info fields/values, VA/PA bias, the
    kernel-window layout, the prebuilt page table (one 512 MiB superpage) and
    the entry-state table;
  * `spec/Machine-v5 §6.3.2/§6.3.4` — the load rules (ELF 7 / raw 4), the
    entry-state values and the failure semantics;
  * `spec/DADAO-12 §2.2.3` — L1 PTE bit layout (HSJU/PPN/SPF/flags);
  * `contracts/linux-boot.yaml::rules[].id` — the rule names a bad image must
    be rejected by;
  * `tests/shared/bootrom/k0/README.md` — smon failure codes and the probe
    register map.

What "reachable FAIL" means here: every positive assertion is a live compare
against a freshly derived value (a mistyped field, PTE or register value turns
it red), the negative cases assert a *named* rejection on a deliberately broken
image, and `--inject` rewrites a real source file, proves the corresponding
assertion goes red, restores the file byte-for-byte (`cp` + md5) and proves it
is green again.

Usage:
  k0_boot_probe.py                 # full run: build + positive + negatives
  k0_boot_probe.py --list          # list the checks
  k0_boot_probe.py --only NAME     # one check (repeatable)
  k0_boot_probe.py --inject        # + the two source injections
  k0_boot_probe.py --kernel VMLINUX   # optional integration input (Linux)
Exit code: 0 iff every requested check passed.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
for _sub in (("tools", "infra"), ("tools", "testcases", "lib")):
    _p = os.path.join(_REPO, *_sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import paths as _paths  # noqa: E402
import yaml  # noqa: E402

CONTRACT = os.path.join(_REPO, "contracts", "linux-boot.yaml")
K0_DIR = os.path.join(_REPO, "tests", "shared", "bootrom", "k0")
STEP5_DIR = os.path.join(_REPO, "tests", "shared", "bootrom", "step5")
BUILD_STEP5 = os.path.join(_REPO, "tools", "testcases", "arch",
                           "build_step5_bootrom.py")
QEMU_SRC = os.path.join(_REPO, ".work", "source", "qemu")
MACHINE_C = os.path.join(QEMU_SRC, "hw", "dadao", "dadao-machine.c")
SMON_S = os.path.join(K0_DIR, "smon.S")

DEFAULT_QEMU = str(_paths.host_toolchain_bin() / "qemu-system-dadao")
TOOLCHAIN = _paths.host_toolchain_bin()
TMP_ROOT = os.environ.get("DADAO_TMP_ROOT") or "/tmp/opencode/m14-qemu-001"
WORK = os.path.join(TMP_ROOT, "k0_boot_probe")
TIMEOUT = 120

# ── contract-derived ABI values (loaded in main(); no literals below) ──────
ABI = {}
BOOT_INFO = {}      # field name -> dict(offset/width/value)
LAYOUT = {}         # partition name -> (start, end, pa_start)
EXP = {}            # register expectations for the probe kernel
KERNEL_SIZE = 0     # fixed point of the probe image size

STATS = {"passes": 0, "fails": []}


def load_contract():
    with open(CONTRACT, encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    model = spec["address_model"]
    ABI["va_pa_offset"] = model["va_pa_offset"]
    ABI["kernel_start"] = spec["va_layout"]["kernel"]["start"]
    ABI["kernel_end"] = spec["va_layout"]["kernel"]["end"]
    ABI["superpage_size"] = spec["startup_model"]["superpage_size"]
    ABI["page_size"] = spec["startup_model"]["page_size"]
    ABI["boot_info_va"] = spec["boot_info"]["va"]
    ABI["boot_info_size"] = spec["boot_info"]["size"]
    ABI["boot_info_endian"] = spec["boot_info"]["endianness"]
    for part in spec["memory_map"]:
        if part.get("start") is None:
            continue
        LAYOUT[part["name"]] = (part["start"], part["end"], part["pa_start"])
    for field in spec["boot_info"]["fields"]:
        BOOT_INFO[field["name"]] = field
    ABI["rules"] = {r["id"] for r in spec["rules"]}
    # The page table carries one 512 MiB superpage at the kernel-window base
    # (startup_model.prebuilt_page_table); its L1 index is VA[41:29]
    # (spec/DADAO-12 §2.2.1/§2.2.3), i.e. the kernel-window start >> 29 — the
    # prose "L1 index 0" means "the first entry of the kernel window".
    ABI["pte_index"] = ABI["kernel_start"] >> 29
    pa = LAYOUT["page_table"][2]
    ABI["pte"] = ((0xC << 60)                    # HSJU: H=1, S=1, U=J=0
                  | (((pa >> 16) << 16))         # PPN[55:16]
                  | (0xFF << 8)                  # SPF: every 64 MiB present
                  | 0xEF)                        # R W X G A D SP P
    # Entry-state register values (§6.3.4).
    ABI["entry_va"] = BOOT_INFO["kernel_base"]["value"]
    ABI["rb3"] = 0
    ABI["async_mask"] = 0xFFFF_FFFF_FFFF_FFFF


def fail(msg):
    STATS["fails"].append(msg)
    print("FAIL %s" % msg)


def expect(name, exp, got, fmt="%#x"):
    if exp == got:
        STATS["passes"] += 1
        print("PASS %-40s %s" % (name, fmt % exp if isinstance(exp, int) else exp))
        return True
    fail("%s: expected %s, got %s"
         % (name, fmt % exp if isinstance(exp, int) else exp,
            fmt % got if isinstance(got, int) else got))
    return False


def expect_true(name, cond, detail=""):
    if cond:
        STATS["passes"] += 1
        print("PASS %-40s %s" % (name, detail))
        return True
    fail("%s: %s" % (name, detail))
    return False


# ── helpers ────────────────────────────────────────────────────────────────
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def run(cmd, timeout=TIMEOUT, cwd=_REPO):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)
    if proc.returncode != 0:
        raise SystemExit("command failed (%d): %s\n%s"
                         % (proc.returncode, " ".join(cmd),
                            (proc.stderr or proc.stdout)[-4000:]))
    return proc.stdout


def tool(name):
    path = os.path.join(TOOLCHAIN, name)
    if not os.access(path, os.X_OK):
        raise SystemExit("missing toolchain binary: %s (run make install-host)"
                         % path)
    return path


# ── ELF (big-endian ELF64) helpers ─────────────────────────────────────────
PH_OFF = 64


def elf_read(path):
    with open(path, "rb") as fh:
        return bytearray(fh.read())


def be16(buf, off):
    return struct.unpack_from(">H", buf, off)[0]


def be32(buf, off):
    return struct.unpack_from(">I", buf, off)[0]


def be64(buf, off):
    return struct.unpack_from(">Q", buf, off)[0]


def put16(buf, off, val):
    struct.pack_into(">H", buf, off, val)


def put32(buf, off, val):
    struct.pack_into(">I", buf, off, val)


def put64(buf, off, val):
    struct.pack_into(">Q", buf, off, val)


def elf_loads(buf):
    """[(phdr offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align)]."""
    phoff = be64(buf, 32)
    phentsize = be16(buf, 54)
    phnum = be16(buf, 56)
    out = []
    for i in range(phnum):
        off = phoff + i * phentsize
        if be32(buf, off) != 1:      # PT_LOAD
            continue
        out.append((off, be64(buf, off + 16), be64(buf, off + 24),
                    be64(buf, off + 32), be64(buf, off + 40),
                    be64(buf, off + 48)))
    return out


def elf_kernel_size(buf):
    loads = elf_loads(buf)
    end = max(vaddr + memsz for (_o, vaddr, _p, _f, memsz, _a) in loads)
    return end - ABI["entry_va"]


# ── firmware / kernel build ────────────────────────────────────────────────
def build_firmware(out_dir, neg_case=0):
    """Assemble power (step5, unchanged) + k0 hmon/smon and pack the BootROM."""
    os.makedirs(out_dir, exist_ok=True)
    mc, lld, objcopy, nm = (tool("llvm-mc"), tool("ld.lld"),
                            tool("llvm-objcopy"), tool("llvm-nm"))
    defs = ["--defsym", "BOOT_INFO_PA=%d" % (ABI["boot_info_va"]
                                             - ABI["va_pa_offset"])]
    if neg_case:
        defs += ["--defsym", "SMON_NEG_CASE=%d" % neg_case]

    def assemble(src, out, lds, extra=()):
        run([mc, "--triple=dadao-unknown-elf", "-filetype=obj", *extra,
             src, "-o", out])
        run([lld, "-z", "max-page-size=0x1000", "-T", lds, out,
             "-o", out.replace(".o", ".elf")])

    assemble(os.path.join(STEP5_DIR, "power.S"),
             os.path.join(out_dir, "power.o"),
             os.path.join(STEP5_DIR, "power.lds"))
    run([objcopy, "-O", "binary", os.path.join(out_dir, "power.elf"),
         os.path.join(out_dir, "power.bin")])
    assemble(os.path.join(K0_DIR, "hmon.S"),
             os.path.join(out_dir, "hmon.o"),
             os.path.join(K0_DIR, "hmon.lds"), defs)
    assemble(os.path.join(K0_DIR, "smon.S"),
             os.path.join(out_dir, "smon.o"),
             os.path.join(K0_DIR, "smon.lds"), defs)
    name = "bootrom_k0_neg%d.bin" % neg_case if neg_case else "bootrom_k0.bin"
    run([sys.executable, BUILD_STEP5,
         "--out-dir", out_dir,
         "--power-elf", os.path.join(out_dir, "power.elf"),
         "--hmon-elf", os.path.join(out_dir, "hmon.elf"),
         "--smon-elf", os.path.join(out_dir, "smon.elf"),
         "--llvm-objcopy", objcopy, "--llvm-nm", nm,
         "--out-name", name])
    return os.path.join(out_dir, name)


def probe_defs(kernel_size):
    """--defsym values for the probe kernel: contract values + image size."""
    d = {
        "BI_VA": ABI["boot_info_va"],
        "BI_SIZE": ABI["boot_info_size"],
        "PT_VA": LAYOUT["page_table"][0],
        "PTE_INDEX": ABI["pte_index"],
        "EXIT_BLOCK_VA": ABI["entry_va"] + 0x10000,
        "EXIT_BLOCK_PA": ABI["entry_va"] - ABI["va_pa_offset"] + 0x10000,
        "EXP_MAGIC": BOOT_INFO["magic"]["value"],
        "EXP_VERSION": BOOT_INFO["version"]["value"],
        "EXP_BI_SIZE": BOOT_INFO["size"]["value"],
        "EXP_RAM_BASE": BOOT_INFO["ram_base"]["value"],
        "EXP_RAM_SIZE": BOOT_INFO["ram_size"]["value"],
        "EXP_KERNEL_BASE": BOOT_INFO["kernel_base"]["value"],
        "EXP_KERNEL_SIZE": kernel_size,
        "EXP_INITRAMFS_BASE": BOOT_INFO["initramfs_base"]["value"],
        "EXP_INITRAMFS_SIZE": 0,          # K1 installs no initramfs
        "EXP_CMDLINE_BASE": BOOT_INFO["cmdline_base"]["value"],
        "EXP_CMDLINE_SIZE": BOOT_INFO["cmdline_size"]["value"],
        "EXP_PTBR": BOOT_INFO["ptbr"]["value"],
        "EXP_PAGE_SHIFT": BOOT_INFO["page_size_log2"]["value"],
        "EXP_HART_ID": BOOT_INFO["hart_id"]["value"],
        "EXP_FLAGS": BOOT_INFO["flags"]["value"],
        "EXP_PTE0": ABI["pte"],
        "EXP_PTE1": 0,
        "EXP_PTE2": 0,
        "EXP_PTE3": 0,
        "EXP_PT_NONZERO": 1,
        "EXP_BI_TAIL_NONZERO": 0,
        "EXP_ENTRY": ABI["entry_va"],
        "EXP_BI_VA": ABI["boot_info_va"],
        "EXP_RB3": 0,
    }
    return d


def build_kernel(out_dir):
    """Build the probe kernel ELF and derive the K1 VA/PA layout + size."""
    global KERNEL_SIZE
    os.makedirs(out_dir, exist_ok=True)
    mc, lld, objcopy = tool("llvm-mc"), tool("ld.lld"), tool("llvm-objcopy")
    elf_path = os.path.join(out_dir, "probe_kernel.elf")
    raw_path = os.path.join(out_dir, "probe_kernel.bin")
    # The self-check constant EXP_KERNEL_SIZE is part of the image, so its
    # value must reach a fixed point with the image size.
    size = KERNEL_SIZE
    for _ in range(8):
        defs = []
        for key, val in probe_defs(size).items():
            # llvm-mc --defsym takes a signed 64-bit decimal integer.
            val &= 0xFFFFFFFFFFFFFFFF
            if val >= 1 << 63:
                val -= 1 << 64
            defs += ["--defsym", "%s=%d" % (key, val)]
        run([mc, "--triple=dadao-unknown-elf", "-filetype=obj", *defs,
             os.path.join(K0_DIR, "probe_kernel.S"), "-o",
             os.path.join(out_dir, "probe_kernel.o")])
        run([lld, "-z", "max-page-size=0x10000", "-T",
             os.path.join(K0_DIR, "probe_kernel.lds"),
             os.path.join(out_dir, "probe_kernel.o"), "-o", elf_path])
        run([objcopy, "-O", "binary", elf_path, raw_path])
        with open(raw_path, "rb") as fh:
            raw = fh.read()
        new_size = len(raw)
        if new_size == size:
            break
        size = new_size
    else:
        raise SystemExit("probe kernel size did not converge")
    KERNEL_SIZE = size

    # K1 ELF-VA-TO-PA: p_paddr is the PA of p_vaddr under the fixed bias.
    buf = elf_read(elf_path)
    for (off, vaddr, _paddr, _filesz, _memsz, _align) in elf_loads(buf):
        if vaddr < ABI["va_pa_offset"]:
            raise SystemExit("probe kernel segment below the kernel window")
        put64(buf, off + 24, vaddr - ABI["va_pa_offset"])
    with open(elf_path, "wb") as fh:
        fh.write(buf)
    # The raw path is the same bytes without an ELF header (RAW-ENTRY).
    if elf_kernel_size(buf) != KERNEL_SIZE:
        raise SystemExit("probe kernel ELF footprint %#x != raw size %#x"
                         % (elf_kernel_size(buf), KERNEL_SIZE))
    return elf_path, raw_path


# ── QEMU runs ──────────────────────────────────────────────────────────────
def windows(bootrom):
    """Execution windows for -dfilter: power, hmon, smon, kernel."""
    prof = _prof()
    hmon_entry = _elf_entry(bootrom, 1)
    smon_entry = _elf_entry(bootrom, 2)
    return [
        ("power", prof.reset_pc, 0x10000),
        ("hmon", hmon_entry, 0x10000),
        ("smon", smon_entry, 0x10000),
        ("kernel", ABI["entry_va"], 0x10000),
    ]


def _prof():
    import machine_profile
    return machine_profile.load("vast")


def _elf_entry(bootrom, typ):
    with open(bootrom, "rb") as fh:
        img = fh.read()
    off = None
    count = be16(img, 6)
    for i in range(count):
        base = 16 + i * 32
        if be32(img, base) == typ:
            off = be64(img, base + 8)
    if off is None:
        raise SystemExit("BootROM image has no entry of type %d" % typ)
    return be64(img, off + 24)


def run_qemu(qemu, bootrom, kernel=None, tag="run", dfilter=None,
             timeout=TIMEOUT):
    os.makedirs(WORK, exist_ok=True)
    log = os.path.join(WORK, "%s.log" % tag)
    if os.path.exists(log):
        os.unlink(log)
    if dfilter is None:
        dfilter = ",".join("0x%x+0x%x" % (base, size)
                           for (_n, base, size) in windows(bootrom))
    cmd = [qemu, "-machine", "dadao-vast,bootrom-image=" + bootrom,
           "-nographic", "-semihosting-config", "enable=on,target=native"]
    if kernel:
        cmd += ["-kernel", kernel]
    cmd += ["-d", "cpu", "-dfilter", dfilter, "-D", log]
    try:
        proc = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True,
                              timeout=timeout)
        rc = proc.returncode & 0xFF
        err = proc.stderr
    except subprocess.TimeoutExpired:
        # A payload that does not exit (e.g. Linux waiting for a console) is a
        # valid observation: the dumps written so far are still parsed.
        return None, parse_blocks(log), "TIMEOUT", log
    return rc, parse_blocks(log), err, log


def parse_blocks(path):
    blocks = []
    if not os.path.exists(path):
        return blocks
    with open(path, "r", errors="replace") as fh:
        text = fh.read()
    for chunk in text.split("PC: ")[1:]:
        lines = chunk.splitlines()
        blk = {"pc": int(lines[0].strip(), 16) if lines else None}
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
            m = re.search(r"^CFX([0-9a-f]{2}) ID:([0-9a-f]+) VER:([0-9a-f]+) "
                          r"TRAPN:([0-9a-f]+) SYNCN:([0-9a-f]+) "
                          r"ASYNCN:([0-9a-f]+) ESCN:([0-9a-f]+) "
                          r"SCRN:([0-9a-f]+) GIM:([0-9a-f]+)", ln)
            if m:
                cfx = m.group(1)
                blk["trapn:%s" % cfx] = int(m.group(4), 16)
                blk["escn:%s" % cfx] = int(m.group(7), 16)
                blk["gim:%s" % cfx] = int(m.group(9), 16)
            m = re.search(r"^CFX([0-9a-f]{2}) M(\d) SWMODE:([0-9a-f]+) "
                          r"VEC:([0-9a-f]+) TRAPMASK:([0-9a-f]+) "
                          r"MEMMASK:([0-9a-f]+) REGMASK:([0-9a-f]+) "
                          r"EXEMASK:([0-9a-f]+) INTRMASK:([0-9a-f]+)", ln)
            if m:
                blk["intrmask:%s:%s" % (m.group(1), m.group(2))] = \
                    int(m.group(9), 16)
        blocks.append(blk)
    return blocks


def stage_sequence(blocks, bootrom):
    wins = windows(bootrom)
    seq = []
    for blk in blocks:
        for idx, (_name, base, size) in enumerate(wins):
            if blk.get("pc") is not None and base <= blk["pc"] < base + size:
                seq.append(idx)
                break
    return seq


def in_kernel_window(blocks, bootrom):
    for blk in blocks:
        pc = blk.get("pc")
        if pc is not None and pc in range(ABI["entry_va"], ABI["entry_va"] + 0x10000):
            return True
    return False


# ── positive assertions ────────────────────────────────────────────────────
def check_positive(tag, rc, blocks, err, bootrom, kernel_size):
    """Assertions 1a-1f of the task book for one successful run."""
    print("-- positive run [%s]" % tag)
    expect("%s: guest exit code" % tag, 0, rc)
    last = blocks[-1] if blocks else {}
    expect("%s: rd30 self-check mask" % tag, 0, last.get("rd30", -1))
    expect("%s: MODE (supv)" % tag, 2, last.get("mode", -1))
    expect("%s: CFXCODE (smon)" % tag, 2, last.get("cfxcode", -1))
    expect("%s: PTBR" % tag, 0, last.get("ptbr", -1))
    expect("%s: PTW_ENABLE" % tag, 1, last.get("ptw", -1))
    expect("%s: CFX02 GIM (async mask)" % tag, ABI["async_mask"],
           last.get("gim:02", -1))
    expect("%s: CFX02 M2 INTRMASK" % tag, ABI["async_mask"],
           last.get("intrmask:02:2", -1))

    # 1c: boot info fields, in the §6.3.3 order of the probe register map.
    fields = [
        ("magic", "rd5", BOOT_INFO["magic"]["value"]),
        ("version", "rd6", BOOT_INFO["version"]["value"]),
        ("size", "rd7", BOOT_INFO["size"]["value"]),
        ("ram_base", "rd8", BOOT_INFO["ram_base"]["value"]),
        ("ram_size", "rd9", BOOT_INFO["ram_size"]["value"]),
        ("kernel_base", "rd10", BOOT_INFO["kernel_base"]["value"]),
        ("kernel_size", "rd11", kernel_size),
        ("initramfs_base", "rd12", BOOT_INFO["initramfs_base"]["value"]),
        ("initramfs_size", "rd13", 0),
        ("cmdline_base", "rd14", BOOT_INFO["cmdline_base"]["value"]),
        ("cmdline_size", "rd15", BOOT_INFO["cmdline_size"]["value"]),
        ("ptbr", "rd17", BOOT_INFO["ptbr"]["value"]),
        ("page_size_log2", "rd18", BOOT_INFO["page_size_log2"]["value"]),
        ("hart_id", "rd19", BOOT_INFO["hart_id"]["value"]),
        ("flags", "rd20", BOOT_INFO["flags"]["value"]),
    ]
    for name, reg, exp in fields:
        expect("%s: boot info %s" % (tag, name), exp, last.get(reg, -1))

    # 1d: page table through the prebuilt mapping.
    expect("%s: PTE[%d]" % (tag, ABI["pte_index"]), ABI["pte"],
           last.get("rd21", -1))
    expect("%s: PTE[%d]" % (tag, ABI["pte_index"] + 1), 0, last.get("rd22", -1))
    expect("%s: PTE[%d]" % (tag, ABI["pte_index"] + 2), 0, last.get("rd23", -1))
    expect("%s: PTE[%d]" % (tag, ABI["pte_index"] + 3), 0, last.get("rd24", -1))
    expect("%s: page table non-zero words" % tag, 1, last.get("rd28", -1))
    expect("%s: boot info page tail non-zero words" % tag, 0,
           last.get("rd29", -1))

    # 1e: handover registers.
    expect("%s: rb16 (entry VA)" % tag, ABI["entry_va"], last.get("rd25", -1))
    expect("%s: rb17 (boot info VA)" % tag, ABI["boot_info_va"],
           last.get("rd26", -1))
    expect("%s: rb3 (rbtp)" % tag, 0, last.get("rd27", -1))

    # 1f: execution windows power -> hmon -> smon -> kernel.
    #
    # `-d cpu` dumps are emitted per translation block, and a chained TB can be
    # logged with the previous block's PC (accel/tcg/cpu-exec.c log_cpu_exec),
    # so neighbouring windows interleave around a `call`/`trap`.  The ordering
    # claim is therefore made on first occurrences plus "no stage runs after
    # the kernel was entered", not on every single block.
    seq = stage_sequence(blocks, bootrom)
    first = {}
    for idx, stage in enumerate(seq):
        first.setdefault(stage, idx)
    expect_true("%s: all four stages executed" % tag,
                set(seq) >= {0, 1, 2, 3}, "windows seen: %s" % sorted(set(seq)))
    expect_true("%s: first executions are ordered power<hmon<smon<kernel" % tag,
                all(stage in first for stage in range(4)) and
                first[0] < first[1] < first[2] < first[3],
                "first block index: %s" % first)
    kernel_first = first.get(3)
    expect_true("%s: no earlier stage after the kernel entry" % tag,
                kernel_first is not None and
                all(stage == 3 for stage in seq[kernel_first:]),
                "tail stages: %s" % seq[max(0, len(seq) - 4):])
    expect_true("%s: CFX02 TRAPN == 1 (smon entered once)" % tag,
                last.get("trapn:02") == 1, "TRAPN=%s" % last.get("trapn:02"))
    expect("%s: CFX02 ESCN (exactly one escape)" % tag, 1,
           last.get("escn:02", -1))


# ── negative image construction ────────────────────────────────────────────
def bad_elf(dst, mutate):
    buf = elf_read(os.path.join(WORK, "probe_kernel.elf"))
    mutate(buf)
    with open(dst, "wb") as fh:
        fh.write(buf)
    return dst


def neg_loader_cases():
    """Loader-side negatives (§6.3.2): each must be rejected by name."""
    loads = elf_loads(elf_read(os.path.join(WORK, "probe_kernel.elf")))
    ph0 = loads[0][0]

    def m_entry(buf):
        put64(buf, 24, ABI["entry_va"] + 4)

    def m_overlap(buf):
        put64(buf, ph0 + 16, LAYOUT["boot_info"][0])
        put64(buf, ph0 + 24, LAYOUT["boot_info"][2])

    def m_range(buf):
        put64(buf, ph0 + 16, LAYOUT["initramfs"][0])
        put64(buf, ph0 + 24, LAYOUT["initramfs"][2])

    def m_align(buf):
        put64(buf, ph0 + 16, ABI["entry_va"] + 0x100)
        put64(buf, ph0 + 24, ABI["entry_va"] - ABI["va_pa_offset"] + 0x100)

    def m_va_to_pa(buf):
        put64(buf, ph0 + 24, ABI["entry_va"])

    def m_format(buf):
        put16(buf, 18, 0x0DA1)

    return [
        ("ELF-ENTRY", m_entry),
        ("ELF-NO-OVERLAP", m_overlap),
        ("ELF-RANGE", m_range),
        ("ELF-ALIGN", m_align),
        ("ELF-VA-TO-PA", m_va_to_pa),
        ("ELF-FORMAT", m_format),
    ]


def check_loader_negatives(qemu, bootrom):
    print("-- loader negatives (§6.3.2)")
    for rule, mutate in neg_loader_cases():
        path = bad_elf(os.path.join(WORK, "neg_%s.elf" % rule), mutate)
        rc, blocks, err, _log = run_qemu(qemu, bootrom, path, tag="neg_" + rule)
        tag = "loader %s" % rule
        expect_true("%s: rejected (rc != 0)" % tag, rc not in (0, None),
                    "rc=%r" % rc)
        expect_true("%s: stderr names the rule" % tag, rule in err,
                    (err.strip().splitlines() or [""])[-1][:120])
        expect_true("%s: no kernel execution block" % tag,
                    not in_kernel_window(blocks, bootrom), "blocks=%d"
                    % len(blocks))

    # RAW-LENGTH: 63 MiB is the kernel image region; one byte more is a
    # rejection before any load (RAW-BASE/RAW-ENTRY/RAW-BSS are properties of
    # a well-formed flat image and are exercised by the raw positive run).
    limit = LAYOUT["kernel"][1] - LAYOUT["kernel"][0]
    raw_bad = os.path.join(WORK, "neg_RAW-LENGTH.bin")
    with open(raw_bad, "wb") as fh:
        fh.write(b"\0" * (limit + 1))
    rc, blocks, err, _log = run_qemu(qemu, bootrom, raw_bad, tag="neg_RAW-LENGTH")
    expect_true("loader RAW-LENGTH: rejected (rc != 0)", rc not in (0, None),
                "rc=%r" % rc)
    expect_true("loader RAW-LENGTH: stderr names the rule", "RAW-LENGTH" in err,
                (err.strip().splitlines() or [""])[-1][:120])
    expect_true("loader RAW-LENGTH: no kernel execution block",
                not in_kernel_window(blocks, bootrom), "blocks=%d" % len(blocks))


def check_smon_negatives(qemu, kernel):
    """smon read-only validation: a patched boot info must be refused."""
    print("-- smon negatives (§7 codes 0xC2/0xC3)")
    cases = [(1, 0xC2, "size = 0x20"),
             (2, 0xC3, "kernel_base unaligned"),
             # hart_id = 5: the valid value is 0, so this case also proves the
             # injected bytes reach the boot info page (a zero-filling DMA
             # would leave smon green).
             (3, 0xC7, "hart_id = 5")]
    for neg, code, desc in cases:
        bootrom = build_firmware(os.path.join(WORK, "neg%d" % neg), neg_case=neg)
        rc, blocks, err, _log = run_qemu(qemu, bootrom, kernel,
                                         tag="smon_neg%d" % neg)
        tag = "smon neg %s" % desc
        expect("%s: guest failure code" % tag, code, rc)
        expect_true("%s: no kernel execution block" % tag,
                    not in_kernel_window(blocks, bootrom), "blocks=%d"
                    % len(blocks))


# ── source injections ──────────────────────────────────────────────────────
def rebuild_qemu(jobs):
    run(["make", "build-qemu", "JOBS=%d" % jobs], timeout=3600)
    run(["make", "install-host", "JOBS=%d" % jobs], timeout=3600)


def inject_source(path, old, new, label, qemu, jobs, rerun, need_qemu):
    """Rewrite one source line, prove the check goes red, restore via cp+md5."""
    backup = os.path.join(WORK, "inject-%s.orig" % label)
    shutil.copy2(path, backup)
    before = md5(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if text.count(old) != 1:
        raise SystemExit("injection %s: anchor not unique" % label)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new))
    injected = md5(path)
    print("-- inject %s: md5 %s -> %s" % (label, before, injected))
    expect_true("inject %s: source changed" % label, injected != before,
                "%s -> %s" % (before, injected))
    try:
        if need_qemu:
            rebuild_qemu(jobs)
        red = rerun("inject_" + label)
        expect_true("inject %s: probe FAILs" % label, not red,
                    "injected run returned %s" % ("red" if not red else "green"))
    finally:
        shutil.copy2(backup, path)
        # cp restores the original mtime; bump it so the incremental build
        # actually recompiles (a stale-mtime restore leaves the injected
        # object in place and the "green again" step would be a false red).
        os.utime(path, None)
    after = md5(path)
    expect_true("inject %s: restored via cp + md5" % label, after == before,
                "%s == %s" % (after, before))
    if need_qemu:
        rebuild_qemu(jobs)
    green = rerun("inject_" + label + "_restored")
    expect_true("inject %s: green again" % label, green,
                "restored run returned %s" % ("green" if green else "red"))


# ── main ───────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--kernel", default=None,
                    help="optional integration input (m14-linux-002 vmlinux)")
    ap.add_argument("--inject", action="store_true",
                    help="run the two source injections after the normal run")
    ap.add_argument("--jobs", type=int, default=32)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    checks = ["main", "raw", "loader-negatives", "smon-negatives"]
    if args.kernel:
        checks.append("vmlinux")
    if args.inject:
        checks.append("inject")
    if args.list:
        for name in checks:
            print(name)
        return 0
    selected = list(args.only) or checks
    if args.inject and "inject" not in selected:
        selected.append("inject")
    unknown = [c for c in selected if c not in checks]
    if unknown:
        print("unknown check(s): %s" % ", ".join(unknown), file=sys.stderr)
        return 2

    load_contract()
    os.makedirs(WORK, exist_ok=True)
    bootrom = build_firmware(WORK)
    kernel_elf, kernel_raw = build_kernel(WORK)
    elf_size = elf_kernel_size(elf_read(kernel_elf))
    print("k0: bootrom=%s kernel=%d bytes (raw+elf)" % (bootrom, elf_size))
    if not os.access(args.qemu, os.X_OK):
        raise SystemExit("qemu binary not found: %s (run make install-host)"
                         % args.qemu)

    def rerun(tag):
        """Re-run the positive ELF probe; return True when it is all green.

        The firmware is rebuilt from source on every rerun so a firmware-source
        injection is actually part of the image under test.
        """
        global STATS
        nonlocal bootrom
        bootrom = build_firmware(WORK)
        outer = STATS
        STATS = {"passes": 0, "fails": []}
        try:
            rc, blocks, err, _log = run_qemu(args.qemu, bootrom, kernel_elf, tag)
            check_positive(tag, rc, blocks, err, bootrom, elf_size)
            inner = STATS
        finally:
            globals()["STATS"] = outer
        print("   [%s] %d checks, %d failed"
              % (tag, inner["passes"] + len(inner["fails"]),
                 len(inner["fails"])))
        return not inner["fails"]

    if "main" in selected:
        print("== main (ELF path, §6.3 handover) ==")
        rc, blocks, err, _log = run_qemu(args.qemu, bootrom, kernel_elf, "main")
        check_positive("main", rc, blocks, err, bootrom, elf_size)

    if "raw" in selected:
        print("== raw path (RAW-BASE/RAW-ENTRY/RAW-BSS) ==")
        rc, blocks, err, _log = run_qemu(args.qemu, bootrom, kernel_raw, "raw")
        check_positive("raw", rc, blocks, err, bootrom, KERNEL_SIZE)

    if "loader-negatives" in selected:
        check_loader_negatives(args.qemu, bootrom)

    if "smon-negatives" in selected:
        check_smon_negatives(args.qemu, kernel_elf)

    if "vmlinux" in selected:
        print("== vmlinux integration (optional) ==")
        # Only the first kernel instruction is logged (a 4-byte window): the
        # full `-d cpu` stream of a running kernel is gigabytes, and all this
        # check needs is the state at the entry.
        rc, blocks, err, _log = run_qemu(
            args.qemu, bootrom, args.kernel, "vmlinux",
            dfilter="0x%x+0x4" % ABI["entry_va"], timeout=15)
        first = None
        for blk in blocks:
            pc = blk.get("pc")
            if pc is not None and ABI["entry_va"] <= pc < ABI["entry_va"] + 0x10000:
                first = blk
                break
        expect_true("vmlinux: kernel window executed", first is not None,
                    "blocks=%d rc=%r" % (len(blocks), rc))
        if first is not None:
            expect("vmlinux: MODE at entry (supv)", 2, first.get("mode", -1))
            expect("vmlinux: PTBR at entry", 0, first.get("ptbr", -1))
            expect("vmlinux: PTW_ENABLE at entry", 1, first.get("ptw", -1))

    if "inject" in selected:
        print("== source injections (reachable FAIL, cp + md5 restore) ==")
        # 1. boot info kernel_base field at the wrong offset (0x18 -> 0x20).
        inject_source(
            MACHINE_C,
            "dadao_wr_be64(bi + 0x18, DADAO_K0_KERNEL_BASE_VA);",
            "dadao_wr_be64(bi + 0x20, DADAO_K0_KERNEL_BASE_VA);",
            "machine-kernel-base-offset", args.qemu, args.jobs, rerun,
            need_qemu=True)
        # 2. smon writes a wrong PPN into the single superpage PTE.
        inject_source(
            SMON_S,
            "\tset.rd\trd6, PTE_VALUE\n",
            "\tset.rd\trd6, 0xC00000002000FFEF\n",   # PPN 0x2000, not 0
            "smon-pte-ppn", args.qemu, args.jobs, rerun, need_qemu=False)

    fails = STATS["fails"]
    print("\nresult: %d passed, %d failed" % (STATS["passes"], len(fails)))
    for msg in fails:
        print("  FAILED: %s" % msg)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
