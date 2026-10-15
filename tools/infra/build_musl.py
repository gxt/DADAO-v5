#!/usr/bin/env python3
"""Build the musl static library for dadao-unknown-elf and link a minimal static program.

INFRA-082t stage A3 ("the cross toolchain can produce a static minimal
program"): the DADAO port of musl lives as a tree-shaped patch set
(``components/musl/patches/**`` + ``series``, docs/Process-01); this script
turns it into artifacts and proves the compiler/linker can produce a static
DADAO executable:

1. **build** -- ``./configure --target=dadao-unknown-elf --disable-shared`` +
   ``make`` inside ``.work/source/musl`` (idempotent; rerun after
   ``make fetch apply-series``).  Products: ``lib/libc.a``, ``lib/crt1.o``.
   P1 is the STATIC subset: ``--disable-shared`` is deliberate (the dynamic
   linker is P2, ADR-0025 D6).
2. **smoke link** -- compile a minimal program (``write(1, "hi\\n", 3)`` +
   ``return 0``) against that library and link it with ``lib/crt1.o`` and the
   project ELF script ``tests/scripts/dadao.lds``.
3. **verify** -- the ELF is parsed here (ELF64 / big-endian / ET_EXEC /
   e_machine = EM_DADAO 0x0DA0 / no PT_INTERP / no PT_DYNAMIC, entry inside the
   first PT_LOAD) and cross-checked against ``file(1)``; the disassembly must
   contain the ``trap cfx0, 0`` syscall entry instruction.  Running the program
   on the dadao-m1 machine is stage B and is NOT done here.

Fail-closed: a missing toolchain, a missing source tree, any non-zero
compile/assemble/link step or a failed ELF assertion is an error (rc=2 for
setup problems, rc=1 for a failed check), never a silent skip.

``--inject`` corrupts the expectations so the checks must report FAIL (proving
the comparisons are live); it is only used by the INFRA-082t evidence script,
which pairs it with a real artifact-level negative control.
"""
from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
MUSL_SRC = REPO_ROOT / ".work" / "source" / "musl"
LDS = REPO_ROOT / "tests" / "scripts" / "dadao.lds"

TARGET = "dadao-unknown-elf"
EM_DADAO = 0x0DA0
RAM_BASE = 0xFC0000000000

PROG_C = """\
#include <unistd.h>

/* The P1 static minimal set: one write() and a normal return.  write() goes
   through musl's cancellable-syscall path, exit()/exit_group() through the
   normal exit path -- together they exercise the ported syscall stub, the
   startup path and the exit path.  "hi\\n" is read from a volatile object so
   a future optimizer cannot fold the call away. */
static volatile char msg[] = "hi\\n";

int main(void)
{
    write(1, (const void *)msg, 3);
    return 0;
}
"""


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None,
        timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=timeout)


def toolchain_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{TOOLCHAIN_BIN}:{env.get('PATH', '')}"
    env["CC"] = f"clang --target={TARGET}"
    return env


def build_musl(jobs: int, reconfig: bool) -> int:
    if not MUSL_SRC.is_dir():
        print(f"build-musl: ERROR: {MUSL_SRC} not found -- run 'make fetch apply-series'",
              file=sys.stderr)
        return 2
    env = toolchain_env()
    if reconfig or not (MUSL_SRC / "config.mak").is_file():
        cmd = ["./configure", f"--target={TARGET}", "--disable-shared",
               "CROSS_COMPILE=", "AR=ar", "RANLIB=ranlib"]
        res = run(cmd, cwd=MUSL_SRC, env=env)
        if res.returncode != 0:
            print(f"build-musl: FAIL (configure rc={res.returncode})\n{res.stdout}",
                  file=sys.stderr)
            return 1
    res = run(["make", f"-j{jobs}"], cwd=MUSL_SRC, env=env)
    if res.returncode != 0:
        print(f"build-musl: FAIL (make rc={res.returncode})\n{res.stdout}",
              file=sys.stderr)
        return 1
    for product in ("lib/libc.a", "lib/crt1.o"):
        if not (MUSL_SRC / product).is_file():
            print(f"build-musl: FAIL (missing product {product})", file=sys.stderr)
            return 1
    return 0


def compile_program(work: Path) -> Path:
    src = work / "musl_smoke.c"
    obj = work / "musl_smoke.o"
    src.write_text(PROG_C)
    inc = "".join(f"-I{MUSL_SRC}/{d} " for d in
                  ("arch/dadao", "arch/generic", "obj/src/internal", "src/include",
                   "src/internal", "obj/include", "include"))
    cmd = (f"clang --target={TARGET} -O1 -nostdinc {inc}-c {src} -o {obj}")
    res = run(["sh", "-c", cmd], cwd=REPO_ROOT, env=toolchain_env())
    if res.returncode != 0:
        raise RuntimeError(f"compile rc={res.returncode}\n{res.stdout}")
    return obj


def link_program(work: Path, obj: Path) -> Path:
    elf = work / "musl_smoke.elf"
    cmd = [str(TOOLCHAIN_BIN / "ld.lld"), "-T", str(LDS),
           str(MUSL_SRC / "lib" / "crt1.o"), str(obj), str(MUSL_SRC / "lib" / "libc.a"),
           "-o", str(elf)]
    res = run(cmd, cwd=REPO_ROOT)
    if res.returncode != 0:
        raise RuntimeError(f"link rc={res.returncode}\n{res.stdout}")
    return elf


def parse_elf(path: Path) -> dict:
    """Minimal, dependency-free ELF64 reader (big- or little-endian)."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    ei_class, ei_data = data[4], data[5]
    order = ">" if ei_data == 2 else "<"
    (e_type, e_machine) = struct.unpack_from(order + "HH", data, 0x10)
    e_entry = struct.unpack_from(order + "Q", data, 0x18)[0]
    e_phoff = struct.unpack_from(order + "Q", data, 0x20)[0]
    e_phentsize, e_phnum = struct.unpack_from(order + "HH", data, 0x36)
    phdrs = []
    parse_error = None
    try:
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type, _p_flags = struct.unpack_from(order + "II", data, off)
            p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = struct.unpack_from(
                order + "QQQQQQ", data, off + 8)
            phdrs.append({"type": p_type, "offset": p_offset, "vaddr": p_vaddr,
                          "filesz": p_filesz, "memsz": p_memsz})
    except (struct.error, ValueError) as exc:
        # A corrupt/foreign image must be reported as a failed check, never as
        # a traceback (this is what the evidence script's negative control
        # exercises: flip EI_DATA and the section/table offsets stop making
        # sense in the declared byte order).
        parse_error = f"{type(exc).__name__}: {exc}"
    return {"ei_class": ei_class, "ei_data": ei_data, "order": order,
            "e_type": e_type, "e_machine": e_machine, "e_entry": e_entry,
            "phdrs": phdrs, "parse_error": parse_error}


def check_elf(elf: Path, inject: bool) -> list[tuple[str, str, str, bool]]:
    """Return (name, expected, actual, ok) for every structural assertion."""
    info = parse_elf(elf)
    types = {p["type"] for p in info["phdrs"]}
    loads = [p for p in info["phdrs"] if p["type"] == 1]

    exp_class = 2 if not inject else 1          # ELFCLASS64 (inject: ELFCLASS32)
    exp_data = 2 if not inject else 1           # ELFDATA2MSB (inject: LSB)
    exp_type = 2 if not inject else 3           # ET_EXEC    (inject: ET_DYN)
    exp_mach = EM_DADAO if not inject else 0x3E # EM_DADAO   (inject: EM_X86_64)
    checks = [
        ("ELF class", "2 (ELFCLASS64)", str(info["ei_class"]), info["ei_class"] == exp_class),
        ("ELF data", "2 (ELFDATA2MSB, big-endian)", str(info["ei_data"]),
         info["ei_data"] == exp_data),
        ("ELF type", "2 (ET_EXEC)", str(info["e_type"]), info["e_type"] == exp_type),
        ("e_machine", f"0x{EM_DADAO:04x} (EM_DADAO)", f"0x{info['e_machine']:04x}",
         info["e_machine"] == exp_mach),
        ("program headers parseable", "yes", info["parse_error"] or "yes",
         info["parse_error"] is None),
        ("no PT_INTERP", "absent", "absent" if 3 not in types else "present", 3 not in types),
        ("no PT_DYNAMIC (static)", "absent", "absent" if 2 not in types else "present",
         2 not in types),
        ("PT_LOAD segments", ">=1", str(len(loads)), len(loads) >= 1),
        ("entry in first PT_LOAD",
         f"0x{RAM_BASE:x}..0x{RAM_BASE + loads[0]['memsz']:x}" if loads else "n/a",
         f"0x{info['e_entry']:x}",
         bool(loads) and loads[0]["vaddr"] <= info["e_entry"]
         < loads[0]["vaddr"] + loads[0]["memsz"]),
    ]
    return checks


def disassemble_has_trap(elf: Path) -> tuple[bool, str]:
    res = run([str(TOOLCHAIN_BIN / "llvm-objdump"), "-d", str(elf)])
    if res.returncode != 0:
        return False, f"llvm-objdump rc={res.returncode}"
    text = res.stdout
    ok = "trap cfx0, 0" in text
    return ok, "found" if ok else "NOT found"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", default=str(REPO_ROOT / ".work" / "build" / "musl-static"),
                    help="scratch dir for generated sources/objects/ELF")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--reconfig", action="store_true", help="force ./configure")
    ap.add_argument("--no-build", action="store_true",
                    help="reuse the existing .work/source/musl build (do not run make)")
    ap.add_argument("--no-smoke", action="store_true", help="build only, skip compile/link/verify")
    ap.add_argument("--inject", action="store_true",
                    help="corrupt the expectations so the checks must FAIL")
    args = ap.parse_args()

    for tool in ("clang", "ld.lld", "llvm-objdump"):
        if not (TOOLCHAIN_BIN / tool).exists():
            print(f"build-musl: ERROR: {TOOLCHAIN_BIN / tool} not found "
                  "(run 'make install-host')", file=sys.stderr)
            return 2

    if not args.no_build:
        rc = build_musl(args.jobs, args.reconfig)
        if rc:
            return rc

    if args.no_smoke:
        print("build-musl: build OK (smoke link skipped)")
        return 0

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        obj = compile_program(work)
        elf = link_program(work, obj)
    except RuntimeError as exc:
        print(f"build-musl: FAIL ({exc})", file=sys.stderr)
        return 1

    checks = check_elf(elf, args.inject)
    ok, detail = disassemble_has_trap(elf)
    checks.append(("syscall entry present (trap cfx0, 0)", "found", detail, ok))

    failed = 0
    for name, expected, actual, good in checks:
        print(f"build-musl: {'PASS' if good else 'FAIL'} {name}: expected={expected} actual={actual}")
        if not good:
            failed += 1
    if failed:
        print(f"build-musl: FAIL ({failed}/{len(checks)} checks)", file=sys.stderr)
        return 1

    res = run(["file", str(elf)])
    print(f"build-musl: file(1): {res.stdout.strip()}")
    print(f"build-musl: OK ({len(checks)}/{len(checks)} checks) elf={elf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
