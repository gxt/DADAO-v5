#!/usr/bin/env python3
"""make_vmlinux.py — build and self-check the DADAO kernel (`make linux-vmlinux`).

What it does, in order:

1. `make ARCH=dadao ... vmlinux` in the out-of-tree build directory resolved by
   `tools/linux/paths.py` (the real kernel build, not a hand-linked object).
2. Product assertions from `contract-linux-boot` §3.1 / §3.3:
     * ELF64, big endian, `e_machine = 0x0DA0`, `ET_EXEC`;
     * `e_entry = 0x0200_0010_0000` (`kernel_base`);
     * only `PT_LOAD` plus non-loading `PT_GNU_STACK`/`PT_NOTE`;
     * every `PT_LOAD`: `p_vaddr = p_paddr + 2 TiB`, `p_vaddr % 0x10000 == 0`,
       `p_align >= 0x10000`, and `[p_vaddr, p_vaddr + p_memsz)` inside the
       kernel image area `[0x0200_0010_0000, 0x0200_0400_0000)`;
     * `llvm-nm -u vmlinux` is empty.
3. Code-range guard (ADR-0036 D4/D7, user ruling 2026-11-13): relink once with
   `--emit-relocs` to expose the REL26 edges, run
   `tools/infra/check_code_range.py`, and stop if the executable span reaches
   30 MiB or the REL26 margin drops below 2 MiB.  The model is **not** switched
   to `-mcmodel=large` automatically: that needs a user ruling.

Usage:
  python3 tools/linux/make_vmlinux.py [--jobs N] [--skip-code-range]

Exit status: 0 = built and checked; 1 = build or check failed; 2 = setup error.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.linux import make_defconfig as defconfig  # noqa: E402
from tools.linux import paths as linux_paths  # noqa: E402

KERNEL_BASE = 0x0000_0200_0010_0000
KERNEL_END = 0x0000_0200_0400_0000
VA_PA_OFFSET = 0x0000_0200_0000_0000
PAGE_SIZE = 0x1_0000
EM_DADAO = 0x0DA0
ET_EXEC = 2
#: ADR-0036 packing budget + the 2 MiB guard margin (task rule).
EXEC_SPAN_LIMIT = 30 * 1024 * 1024
REL26_MARGIN_MIN = 2 * 1024 * 1024

_EXEC_SPAN_RE = re.compile(r"exec_span\s*:\s*(\d+) B.*\[ok\]")
_REL26_MARGIN_RE = re.compile(r"margin (\d+) B")


class CheckError(Exception):
    """A product assertion failed."""


def _run(cmd: list[str]) -> int:
    print(f"[INFO] {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd)


def _readelf(tool: str, flag: str, elf: Path) -> str:
    proc = subprocess.run([tool, flag, str(elf)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise CheckError(f"`{tool} {flag}` failed for {elf.name}: {proc.stderr.strip()}")
    return proc.stdout


def _parse_program_headers(text: str) -> list[tuple[str, str, str, str, str, str, str]]:
    """Parse `llvm-readelf -l` rows: Type Off VirtAddr PhysAddr FileSiz MemSiz Flg Align."""
    rows = []
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) < 8 or not tokens[0].isupper():
            continue
        if tokens[0] in {"Type", "Elf"}:
            continue
        try:
            int(tokens[1], 16)
        except ValueError:
            continue
        # Flg may be two tokens ("R E") or one ("RW"); Align is always last.
        rows.append((tokens[0], tokens[2], tokens[3], tokens[4], tokens[5],
                     " ".join(tokens[6:-1]), tokens[-1]))
    return rows


def verify_vmlinux(elf: Path, tools: dict[str, str]) -> None:
    if not elf.is_file():
        raise CheckError(f"{elf.name} was not produced")

    # Parse the ELF header directly: exact numbers, no dependence on how
    # llvm-readelf spells the machine name.
    raw = elf.read_bytes()[:64]
    if len(raw) < 64:
        raise CheckError("file is shorter than an ELF64 header")
    if raw[:4] != b"\x7fELF":
        raise CheckError("missing ELF magic")
    if raw[4] != 2:
        raise CheckError("not ELFCLASS64")
    if raw[5] != 2:
        raise CheckError("not big endian (EI_DATA != 2)")
    e_type = int.from_bytes(raw[16:18], "big")
    e_machine = int.from_bytes(raw[18:20], "big")
    e_entry = int.from_bytes(raw[24:32], "big")
    e_flags = int.from_bytes(raw[48:52], "big")
    if e_type != ET_EXEC:
        raise CheckError(f"e_type != ET_EXEC (got {e_type})")
    if e_machine != EM_DADAO:
        raise CheckError(f"e_machine != 0x{EM_DADAO:04x} (got 0x{e_machine:04x})")
    if e_entry != KERNEL_BASE:
        raise CheckError(
            f"e_entry != 0x{KERNEL_BASE:016x} (got 0x{e_entry:016x})"
        )
    if e_flags & 0xF != 1:
        raise CheckError(f"e_flags version field != 1 (got 0x{e_flags:x})")

    header = _readelf(tools["READELF"], "-h", elf)
    if "Class:" not in header or "ELF64" not in header:
        raise CheckError("not an ELF64 image")
    if "big endian" not in header:
        raise CheckError("not big endian")

    program_headers = _readelf(tools["READELF"], "-l", elf)
    rows = _parse_program_headers(program_headers)
    types = {row[0] for row in rows}
    unexpected = types - {"LOAD", "GNU_STACK", "NOTE"}
    if unexpected:
        raise CheckError(f"unexpected program header types: {sorted(unexpected)}")
    if "LOAD" not in types:
        raise CheckError("no PT_LOAD segment")
    ptypes = re.search(r"There are (\d+) program headers", program_headers)
    if ptypes and len(rows) != int(ptypes.group(1)):
        raise CheckError(
            f"parsed {len(rows)} program headers, readelf reports {ptypes.group(1)}"
        )

    for ptype, vaddr, paddr, filesz, memsz, _flags, align in rows:
        if ptype != "LOAD":
            continue
        vaddr, paddr = int(vaddr, 16), int(paddr, 16)
        memsz, align = int(memsz, 16), int(align, 16)
        if vaddr - paddr != VA_PA_OFFSET:
            raise CheckError(
                f"PT_LOAD p_vaddr=0x{vaddr:x} is not p_paddr + 2 TiB (p_paddr=0x{paddr:x})"
            )
        if vaddr % PAGE_SIZE:
            raise CheckError(f"PT_LOAD p_vaddr=0x{vaddr:x} is not 64 KiB aligned")
        if align < PAGE_SIZE:
            raise CheckError(f"PT_LOAD p_align=0x{align:x} < 0x{PAGE_SIZE:x}")
        if not KERNEL_BASE <= vaddr:
            raise CheckError(f"PT_LOAD p_vaddr=0x{vaddr:x} is below kernel_base")
        if vaddr + memsz > KERNEL_END:
            raise CheckError(
                f"PT_LOAD [0x{vaddr:x}, 0x{vaddr + memsz:x}) leaves the kernel image area"
            )

    undefined = subprocess.run([tools["NM"], "-u", str(elf)],
                               capture_output=True, text=True)
    if undefined.returncode != 0:
        raise CheckError(f"llvm-nm -u failed: {undefined.stderr.strip()}")
    if undefined.stdout.strip():
        raise CheckError("vmlinux has undefined symbols:\n" + undefined.stdout.strip())


def check_code_range(cmd: list[str], tools: dict[str, str], workdir: Path) -> None:
    """Relink with --emit-relocs, gate REL26 margin and exec span, restore."""
    elf = linux_paths.linux_build_dir() / "vmlinux"
    tmpdir = Path(tempfile.mkdtemp(prefix="m14-linux-vmlinux-", dir="/tmp/opencode"))
    reloc = tmpdir / "vmlinux.reloc"
    try:
        with_relocs = f"{defconfig.LDFLAGS_VMLINUX} --emit-relocs"
        rc = _run(cmd + [f"LDFLAGS_vmlinux={with_relocs}", "-j1", "vmlinux"])
        if rc != 0:
            raise CheckError(f"relink with --emit-relocs failed (exit {rc})")
        shutil.copy2(elf, reloc)
        rc = _run(cmd + [f"LDFLAGS_vmlinux={defconfig.LDFLAGS_VMLINUX}", "-j1", "vmlinux"])
        if rc != 0:
            raise CheckError(f"restoring the plain vmlinux failed (exit {rc})")

        report = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "infra" / "check_code_range.py"),
             str(reloc)],
            capture_output=True, text=True,
        )
        print(report.stdout, end="" if report.stdout.endswith("\n") else "\n")
        if report.returncode != 0:
            raise CheckError(
                "check_code_range failed (exec span >= 30 MiB or REL26 edge > 32 MiB); "
                "do NOT switch -mcmodel=large automatically -- report for a user ruling"
            )
        span = _EXEC_SPAN_RE.search(report.stdout)
        margin = _REL26_MARGIN_RE.search(report.stdout)
        if not span:
            raise CheckError("could not read exec_span from check_code_range output")
        if not margin:
            raise CheckError("could not read the REL26 margin from check_code_range output")
        if int(span.group(1)) >= EXEC_SPAN_LIMIT:
            raise CheckError(
                f"exec_span {int(span.group(1))} B reached the 30 MiB packing budget; "
                "report for a user ruling before switching code model"
            )
        if int(margin.group(1)) < REL26_MARGIN_MIN:
            raise CheckError(
                f"REL26 margin {int(margin.group(1))} B is below the 2 MiB guard; "
                "report for a user ruling before switching code model"
            )
        print(f"[PASS] code range: exec_span={int(span.group(1))} B, "
              f"REL26 margin={int(margin.group(1))} B")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=defconfig.default_jobs(),
                        help="parallel make jobs (default: JOBS or nproc/2)")
    parser.add_argument("--skip-code-range", action="store_true",
                        help="skip the relink-based code-range guard (evidence only)")
    args = parser.parse_args()

    try:
        cmd, tools = defconfig.kernel_make_base()
    except defconfig.SetupError as exc:
        print(f"make_vmlinux: SETUP ERROR: {exc}", file=sys.stderr)
        return 2

    if not (linux_paths.linux_build_dir() / ".config").is_file():
        print("make_vmlinux: SETUP ERROR: .config is missing; "
              "run `make linux-defconfig` first", file=sys.stderr)
        return 2

    try:
        rc = _run(cmd + [f"-j{args.jobs}", "vmlinux"])
        if rc != 0:
            print(f"make_vmlinux: FAIL: `make vmlinux` exited {rc}", file=sys.stderr)
            defconfig.next_step_hint()
            return 1

        elf = linux_paths.linux_build_dir() / "vmlinux"
        verify_vmlinux(elf, tools)
        print(f"[PASS] vmlinux ELF: entry=0x{KERNEL_BASE:016x}, "
              f"size={elf.stat().st_size} B")

        if args.skip_code_range:
            print("[INFO] code-range guard skipped on request")
        else:
            check_code_range(cmd, tools, linux_paths.linux_build_dir())

        print("make_vmlinux: PASS")
        return 0
    except CheckError as exc:
        print(f"make_vmlinux: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
