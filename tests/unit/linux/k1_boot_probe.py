#!/usr/bin/env python3
"""k1_boot_probe.py — Kaiwu-Vast K1 boot probe (m14-linux-003).

Runs the real kernel image as the smon payload on

    qemu-system-dadao -machine kaiwu-vast,bootrom-image=<k0 BootROM> \\
                      -nographic -semihosting-config enable=on,target=native \\
                      -kernel <vmlinux>

and checks the K1 boundary fixed by the user ruling of 2026-11-14: the kernel
takes the boot info block, reports it, reaches `start_kernel()` and stops
through semihosting `SYS_EXIT(0)` **before** any clock, timer or interrupt is
initialised.

Expectation sources (never restated here):

  * ``contracts/linux-boot.yaml`` — boot info field values/offsets, the kernel
    window, the VA/PA bias and the page size;
  * the ELF program headers of the image under test — ``kernel_size`` is
    ``max(p_vaddr + p_memsz) - kernel_base``;
  * the image's own symbol table (``llvm-nm``) — ``start_kernel`` and the next
    symbol after it bound the reported return address; ``early_stack`` /
    ``early_stack_top`` bound the reported SP;
  * ``arch/dadao/kernel/head.S`` of the component source tree — the early-stack
    size (the single ``.zero N`` of the ``.bss`` stack).

Checks (each one has a reachable FAIL; the evidence harness tampers with the
kernel to prove it):

  P1  guest rc == 0
  P2  ``K1 bootinfo magic/version/size/hart`` == the contract values
  P3  ``kernel_base/ram_base/ram_size`` == the contract, ``kernel_size`` == the
      value derived from the image's own program headers
  P4  ``initramfs/ptbr/page_size_log2/flags`` == the contract (K1 installs no
      initramfs, so its size is 0)
  P5  the stack line: SP inside ``[early_stack, early_stack_top)`` while the
      kernel is still on the entry stack, and the two symbols are exactly the
      ``.zero`` size apart
  P6  the ``start_kernel`` marker: ``base`` is the ``start_kernel`` symbol,
      ``ra`` is inside ``[start_kernel, next symbol)`` — the hook is the first
      statement of ``start_kernel()`` — and SP is inside the init task's stack
      (K2 switches off the entry stack before calling it)
  P7  the completion line is present and no rejection/FAIL line is

  N1  ``--neg magic|size``: the kernel rejects the corrupted boot info with its
      fixed code (nonzero), names the field, and never prints the boot info or
      reaches ``start_kernel``

Usage::

  python3 tools/linux/k1_boot_probe.py                # positive run
  python3 tools/linux/k1_boot_probe.py --neg size     # kernel-side rejection
  python3 tools/linux/k1_boot_probe.py --neg magic
  python3 tools/linux/k1_boot_probe.py --list
  python3 tools/linux/k1_boot_probe.py --kernel <vmlinux> --qemu <binary>

The negative cases corrupt the **firmware**, not the kernel: a test-only hmon
variant DMAs one wrong field into the boot info page and a ``--defsym`` makes
smon accept that value, so the unmodified kernel is the component that
rejects it.  Neither committed firmware source is touched.

Exit status: 0 = every requested check passed; 1 = at least one FAIL; 2 = the
inputs could not be derived (contract/image/symbols missing).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import paths as _paths     # noqa: E402
from tools.qemu import k0_boot_probe as k0  # noqa: E402

TIMEOUT = int(os.environ.get("K1_BOOT_TIMEOUT", "120"))

#: Scratch root for the assembled BootROM variants (`DADAO_TMP_ROOT` selects it,
#: as for every other probe); the component's runtime paths come from paths.py.
_WORK_ROOT = os.environ.get("DADAO_TMP_ROOT") or "/tmp/opencode/m14-linux-003"
k0.TMP_ROOT = _WORK_ROOT
k0.WORK = os.path.join(_WORK_ROOT, "k1_boot_probe")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def num(text) -> int:
    """A contract value (int already) or a printed `0x...`/decimal string.

    ``<missing>`` (a field the guest did not print) yields -1: the missing-field
    check has already failed, and this keeps the remaining checks reportable.
    """
    if isinstance(text, int):
        return text
    try:
        return int(text, 0)
    except ValueError:
        return -1


class Report:
    """`[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`, plus the live counts."""

    def __init__(self) -> None:
        self.total = 0
        self.fails: list[str] = []

    def check(self, cid: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {cid} {name} | 期望={expected} 实际={actual}", flush=True)
        if not ok:
            self.fails.append(f"{cid} {name}: 期望={expected} 实际={actual}")
        return ok

def elf_program_headers(path: Path) -> list[tuple[int, int, int, int, int, int]]:
    """(p_type, p_vaddr, p_paddr, p_filesz, p_memsz, p_align) of an ELF64/BE image."""
    raw = Path(path).read_bytes()
    if raw[:4] != b"\x7fELF" or raw[5] != 2:
        raise SystemExit(f"k1_boot_probe: {path.name} is not a big-endian ELF64")
    (phoff,) = struct.unpack(">Q", raw[32:40])
    (phentsize, phnum) = struct.unpack(">HH", raw[54:58])
    rows = []
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, _flags, _p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
            struct.unpack(">IIQQQQQQ", raw[off:off + 56])
        rows.append((p_type, p_vaddr, p_paddr, p_filesz, p_memsz, p_align))
    return rows


def kernel_size_from_elf(path: Path, kernel_base: int) -> int:
    loads = [row for row in elf_program_headers(path) if row[0] == 1]
    if not loads:
        raise SystemExit(f"k1_boot_probe: {path.name} has no PT_LOAD")
    return max(vaddr + memsz for (_t, vaddr, _p, _f, memsz, _a) in loads) - kernel_base


def symbols(path: Path) -> dict[str, int]:
    nm = Path(_paths.toolchain_bin()) / "llvm-nm"
    if not nm.is_file():
        raise SystemExit(f"k1_boot_probe: {nm} missing; run `make install-host`")
    proc = subprocess.run([str(nm), "--numeric-sort", str(path)],
                          capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit(f"k1_boot_probe: llvm-nm failed: {proc.stderr.strip()}")
    out: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            out[parts[2]] = int(parts[0], 16)
    return out


def next_symbol(syms: dict[str, int], name: str) -> int:
    """Lowest symbol address strictly above @name (the enclosing function bound)."""
    base = syms[name]
    above = [addr for addr in syms.values() if addr > base]
    return min(above)


def early_stack_size() -> int:
    """The `.zero N` of head.S — the one build parameter the probe cannot infer."""
    head_s = Path(_paths.linux_source_dir()) / "arch" / "dadao" / "kernel" / "head.S"
    if not head_s.is_file():
        raise SystemExit(f"k1_boot_probe: {head_s} missing; run `make fetch "
                         f"apply-series`")
    sizes = re.findall(r"^\s*\.zero\s+(\d+)\s*$", head_s.read_text(),
                       re.MULTILINE)
    if len(sizes) != 1:
        raise SystemExit(f"k1_boot_probe: head.S must carry exactly one `.zero N` "
                         f"(the early stack), found {sizes}")
    return int(sizes[0])


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------

#: `--qemu` override (None = the install root's qemu-system-dadao).
QEMU: str | None = None


def run(rom: str, kernel: Path) -> tuple[int, str]:
    rc, _blocks, err, _log = k0.run_qemu(QEMU or k0.DEFAULT_QEMU,
                                         rom, str(kernel), "k1",
                                         dfilter="0x0+0x4", timeout=TIMEOUT)
    if rc is None:
        return 124, err or ""
    return rc, err or ""


def parse_positive(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    patterns = {
        "bootinfo1": r"^K1 bootinfo magic=(\S+) version=(\S+) size=(\S+) hart=(\S+)$",
        "bootinfo2": r"^K1 bootinfo kernel_base=(\S+) kernel_size=(\S+) "
                     r"ram_base=(\S+) ram_size=(\S+)$",
        "bootinfo3": r"^K1 bootinfo initramfs=(\S+)\+(\S+) cmdline=(\S+)\+(\S+) "
                     r"ptbr=(\S+) page_size_log2=(\S+) flags=(\S+)$",
        "stack": r"^K1 stack sp=(\S+) early_stack=(\S+)\.\.(\S+) entry_va=(\S+)$",
        "marker": r"^K1 start_kernel ra=(\S+) base=(\S+) off=(\S+) sp=(\S+) "
                  r"inside=(\S+)$",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            for index, value in enumerate(m.groups(), start=1):
                fields[f"{key}.{index}"] = value
    return fields


def check_positive(kernel: Path, rep: Report) -> None:
    syms = symbols(kernel)
    for required in ("start_kernel", "early_stack", "early_stack_top"):
        if required not in syms:
            raise SystemExit(f"k1_boot_probe: {required} is not in {kernel.name}")
    entry = k0.ABI["entry_va"]
    expected_size = kernel_size_from_elf(kernel, entry)
    stack_size = early_stack_size()

    rom = k0.build_firmware(str(Path(k0.WORK) / "bootrom"))
    rc, text = run(rom, kernel)
    print("---- guest output ----")
    print(text.strip())
    print("----------------------")

    rep.check("P1", "guest rc (SYS_EXIT 的退出码)", 0, rc)
    f = parse_positive(text)

    def get(key: str) -> str:
        if key not in f:
            rep.check("P?", f"输出缺失字段 {key}", "存在", "缺失")
            return "<missing>"
        return f[key]

    bi = k0.BOOT_INFO
    rep.check("P2", "bootinfo magic", hex(num(bi["magic"]["value"])),
              get("bootinfo1.1"))
    rep.check("P2", "bootinfo version", hex(num(bi["version"]["value"])),
              get("bootinfo1.2"))
    rep.check("P2", "bootinfo size", hex(num(bi["size"]["value"])),
              get("bootinfo1.3"))
    rep.check("P2", "bootinfo hart_id", str(num(bi["hart_id"]["value"])),
              get("bootinfo1.4"))
    rep.check("P3", "bootinfo kernel_base", hex(entry), get("bootinfo2.1"))
    rep.check("P3", "bootinfo kernel_size（ELF 程序头现场推导）",
              hex(expected_size), get("bootinfo2.2"))
    rep.check("P3", "bootinfo ram_base", hex(num(bi["ram_base"]["value"])),
              get("bootinfo2.3"))
    rep.check("P3", "bootinfo ram_size", hex(num(bi["ram_size"]["value"])),
              get("bootinfo2.4"))
    rep.check("P4", "bootinfo initramfs_base",
              hex(num(bi["initramfs_base"]["value"])), get("bootinfo3.1"))
    rep.check("P4", "bootinfo initramfs_size（K1 不装 initramfs）", "0x0",
              get("bootinfo3.2"))
    rep.check("P4", "bootinfo cmdline_base", hex(num(bi["cmdline_base"]["value"])),
              get("bootinfo3.3"))
    rep.check("P4", "bootinfo cmdline_size", hex(num(bi["cmdline_size"]["value"])),
              get("bootinfo3.4"))
    rep.check("P4", "bootinfo ptbr", hex(num(bi["ptbr"]["value"])),
              get("bootinfo3.5"))
    rep.check("P4", "bootinfo page_size_log2",
              hex(num(bi["page_size_log2"]["value"])), get("bootinfo3.6"))
    rep.check("P4", "bootinfo flags", hex(num(bi["flags"]["value"])),
              get("bootinfo3.7"))

    sp = num(get("stack.1"))
    low, high = num(get("stack.2")), num(get("stack.3"))
    rep.check("P5", "early_stack..early_stack_top（符号现场）",
              syms["early_stack_top"] - syms["early_stack"], high - low)
    rep.check("P5", "early_stack 符号", hex(syms["early_stack"]), hex(low))
    rep.check("P5", "early_stack_top 符号", hex(syms["early_stack_top"]), hex(high))
    rep.check("P5", "栈大小 == head.S 的 .zero", stack_size, high - low)
    rep.check("P5", "SP 落在 early stack 内", True, low <= sp < high)
    rep.check("P5", "entry_va（rb16）== 入口", hex(entry), get("stack.4"))

    ra = num(get("marker.1"))
    base = num(get("marker.2"))
    rep.check("P6", "start_kernel 符号", hex(syms["start_kernel"]), hex(base))
    rep.check("P6", "ra 落在 start_kernel 内（ra < 下一个符号）", True,
              syms["start_kernel"] <= ra < next_symbol(syms, "start_kernel"))
    rep.check("P6", "marker 在 start_kernel 头部（off < 0x100，先于首个子系统调用）",
              True, 0 <= num(get("marker.3")) < 0x100)
    rep.check("P6", "inside 标记", "yes", get("marker.5"))
    # K2 (m14-linux-006) leaves the static early stack for the init task's
    # stack before start_kernel(): `current` is derived from SP, and the early
    # stack carries no thread_info.  The bound is the linker's init stack.
    rep.check("P6", "start_kernel 时 SP 在 init task 栈内（init_stack 符号）",
              True,
              syms["__start_init_stack"] <= num(get("marker.4"))
              < syms["__end_init_stack"])
    rep.check("P7", "完成行（SYS_EXIT(0) 之前未开时钟/中断）", True,
              "K1 done: semihosting SYS_EXIT(0) before any clock/interrupt init"
              in text)
    rep.check("P7", "无拒绝行", [], re.findall(r"^K1 bootinfo invalid:.*$",
                                               text, re.MULTILINE))
    rep.check("P7", "`start_kernel` 标记行", True,
              bool(re.search(r"^start_kernel$", text, re.MULTILINE)))


# ---------------------------------------------------------------------------
# negative cases: corrupt the boot info in the firmware, keep the kernel
# ---------------------------------------------------------------------------

HNEG_CASE3 = (
    "\tset.rd rd6, 0x0000000000000005\n"
    "\tst.t\trd6, [rb4, 0]\n"
    "\tset.rb rb5, BOOT_INFO_PA + 0x54\n"
)
HNEG_MAGIC = (
    "\tset.rd rd6, 0x000000004442494f\n"
    "\tst.t\trd6, [rb4, 0]\n"
    "\tset.rb rb5, BOOT_INFO_PA + 0x00\n"
)
NEG = {
    # name: (hmon field value written, smon --defsym that accepts it, kernel code)
    "magic": ("0x4442494f", "BOOTINFO_MAGIC=0x4442494F", "magic", 0x01),
    "size": ("0x20", "BOOTINFO_SIZE=0x20", "size", 0x03),
}


def check_negative(which: str, kernel: Path, rep: Report) -> None:
    _written, smon_def, field, code = NEG[which]
    work = Path(k0.WORK) / f"neg_{which}"
    work.mkdir(parents=True, exist_ok=True)
    hmon = k0.K0_DIR + "/hmon_k0_vast.S"
    before = md5(Path(hmon))
    if which == "magic":
        text = Path(hmon).read_text()
        if text.count(HNEG_CASE3) != 1:
            raise SystemExit("k1_boot_probe: hmon_k0_vast.S negative-case block not unique")
        variant = work / "hmon_magic.S"
        variant.write_text(text.replace(HNEG_CASE3, HNEG_MAGIC))
        hmon_src = str(variant)
        neg_case = 3
    else:
        hmon_src = None
        neg_case = 1
    rom = k0.build_firmware(str(work), neg_case, hmon_src=hmon_src,
                            smon_defs=["--defsym", smon_def],
                            name=f"bootrom_neg_{which}.bin")
    rep.check(f"N1.{which}", "committed hmon_k0_vast.S 未被改动", before, md5(Path(hmon)))

    rc, text = run(rom, kernel)
    print(f"---- guest output ({which}) ----")
    print(text.strip())
    print("--------------------------------")
    rep.check(f"N1.{which}", "具名拒绝的退出码", code, rc)
    rep.check(f"N1.{which}", f"拒绝行点名 {field}", True,
              bool(re.search(rf"^K1 bootinfo invalid: {field} code={hex(code)}$",
                             text, re.MULTILINE)))
    rep.check(f"N1.{which}", "未打印 boot info（未进入解析后的输出）", False,
              bool(re.search(r"^K1 bootinfo magic=", text, re.MULTILINE)))
    rep.check(f"N1.{which}", "未进入 start_kernel", False,
              bool(re.search(r"^start_kernel$", text, re.MULTILINE)))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

CHECKS = ("positive", "neg:magic", "neg:size")


def main() -> int:
    global QEMU
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernel", default=None, help="vmlinux under test")
    ap.add_argument("--qemu", default=None, help="qemu-system-dadao binary")
    ap.add_argument("--neg", choices=sorted(NEG), default=None,
                    help="kernel-side boot info rejection case")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        print("\n".join(CHECKS))
        return 0

    QEMU = args.qemu
    # This probe's checks belong to the K1 image (it stops at start_kernel());
    # the default build tree now carries the K2 image, so refuse rather than
    # report K1 failures against the wrong boot boundary.
    config = _paths.linux_build_dir() / ".config"
    if not config.is_file() or \
            "CONFIG_DADAO_K1_EARLY_STOP=y" not in config.read_text(encoding="utf-8"):
        sys.exit("k1_boot_probe: the build tree is not configured for the K1 "
                 "image; run `make check-linux-k1` (it applies the K1 config "
                 "slice) or set CONFIG_DADAO_K1_EARLY_STOP=y")
    k0.load_contract()
    if not k0.ABI:
        raise SystemExit("k1_boot_probe: contract projection is empty")

    kernel = Path(args.kernel) if args.kernel else \
        Path(_paths.linux_build_dir()) / "vmlinux"
    if not kernel.is_file():
        raise SystemExit(f"k1_boot_probe: {kernel} missing; run `make linux-vmlinux`")
    print(f"k1: kernel={kernel.name} ({kernel.stat().st_size} B) "
          f"qemu={QEMU or k0.DEFAULT_QEMU}")

    rep = Report()
    if args.neg:
        check_negative(args.neg, kernel, rep)
    else:
        check_positive(kernel, rep)
    print(f"k1_boot_probe: {rep.total - len(rep.fails)}/{rep.total} PASS")
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
