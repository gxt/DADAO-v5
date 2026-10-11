#!/usr/bin/env python3
"""Minimal picolibc end-to-end smoke test for DADAO (INFRA-057t).

Compiles a C program that calls ``printf("%d\\n", v)`` against the installed
picolibc sysroot, links it with the project crt0 / linker script and runs it
under ``qemu-system-dadao`` with semihosting, then checks the guest wrote the
expected bytes and exited with status 0.

The format string carries an argument (read from a ``volatile`` object so
clang cannot constant-fold it) **on purpose**: clang rewrites the argument-less
``printf("hi\\n")`` into ``puts("hi\\n")``, which would make ``nm`` show ``U
puts`` and silently skip the printf code path.  The test therefore asserts via
``nm`` that the object references ``printf`` (not a ``puts`` fold), so the
``__dtoa_engine`` / ``__atod_engine`` conversion path and the variant selected
by ``io-float-exact=false`` are actually exercised.

This exercises the whole port path: the picolibc headers, ``libc.a`` (stdio +
the engine-based float conversions), ``libsemihost.a`` (the ``write`` ->
SYS_WRITE 0x05 and ``_exit`` -> SYS_EXIT 0x18 stubs), the DADAO cross file /
big-endian ``long double``=f64 config, and the ``sys_semihost`` trap primitive.

Exit status: 0 = PASS, 1 = FAIL (output/exit-code mismatch or a failed step),
2 = setup error.  ``--inject`` corrupts the expected marker so the check must
report FAIL (proving the comparison is live); it restores nothing itself and is
only used by the evidence script.

Fail-closed: any non-zero compile/assemble/link/qemu step, a timeout, or a
missing tool is a failure, never a silent skip.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
SYSROOT = paths.target_sysroot_dir()
CRT0 = REPO_ROOT / "tests" / "scripts" / "codegen_crt0.s"
LDS = REPO_ROOT / "tests" / "scripts" / "dadao.lds"

PROG_C = """\
#include <stdio.h>

/* ``volatile`` so clang cannot fold the value into the format string; the
   format argument also keeps clang from rewriting printf() into puts(). */
volatile int smoke_value = 42;

int main(void)
{
    printf("%d\\n", smoke_value);
    return 0;
}
"""

EXPECTED_MARKER = "42"


def run(cmd: list[str], *, timeout: int | None = None, merge: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT if merge else subprocess.PIPE,
                          text=True, timeout=timeout)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", default=os.path.join(tempfile.gettempdir(), "opencode", "INFRA-057t", "smoke"))
    ap.add_argument("--qemu-timeout", type=int, default=30)
    ap.add_argument("--inject", action="store_true", help="corrupt the expectation to prove FAIL is reachable")
    args = ap.parse_args()

    for tool in ("clang", "llvm-mc", "ld.lld", "qemu-system-dadao"):
        if not (TOOLCHAIN_BIN / tool).exists():
            print(f"test-picolibc-smoke: ERROR: {TOOLCHAIN_BIN / tool} not found — run 'make install-host'", file=sys.stderr)
            return 2
    nm = shutil.which("nm")
    if nm is None:
        print("test-picolibc-smoke: ERROR: 'nm' not found on PATH (host binutils)", file=sys.stderr)
        return 2
    if not (SYSROOT / "lib" / "libc.a").is_file():
        print(f"test-picolibc-smoke: ERROR: {SYSROOT / 'lib' / 'libc.a'} not found — run 'make build-picolibc'", file=sys.stderr)
        return 2

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    (work / "prog.c").write_text(PROG_C)

    clang = str(TOOLCHAIN_BIN / "clang")
    res = run([clang, "-target", "dadao-unknown-elf", "-nostdlib", "-Oz",
               "-I", str(SYSROOT / "include"), "-c", str(work / "prog.c"), "-o", str(work / "prog.o")])
    if res.returncode != 0:
        print(f"test-picolibc-smoke: FAIL (compile rc={res.returncode})\n{res.stderr}", file=sys.stderr)
        return 1

    # Anti-fold guard: clang rewrites the argument-less printf("hi\n") into
    # puts("hi\n"), which bypasses the printf conversion path (and the
    # __dtoa_engine reference).  The object must reference printf, not a fold.
    res = run([nm, str(work / "prog.o")])
    if res.returncode != 0:
        print(f"test-picolibc-smoke: FAIL (nm rc={res.returncode})\n{res.stderr}", file=sys.stderr)
        return 1
    undefined: list[str] = []
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-2] == "U":
            undefined.append(parts[-1])
    print(f"test-picolibc-smoke: prog.o undefined symbols = {sorted(undefined)}")
    if "printf" not in undefined:
        print(f"test-picolibc-smoke: FAIL (printf not referenced — clang folded it away; "
              f"undefined={sorted(undefined)})", file=sys.stderr)
        return 1

    steps: list[tuple[str, list[str]]] = [
        ("assemble crt0", [str(TOOLCHAIN_BIN / "llvm-mc"), "--triple=dadao-unknown-elf", "-filetype=obj",
                           str(CRT0), "-o", str(work / "crt0.o")]),
        ("link", [str(TOOLCHAIN_BIN / "ld.lld"), "-T", str(LDS), str(work / "crt0.o"), str(work / "prog.o"),
                  str(SYSROOT / "lib" / "libc.a"), str(SYSROOT / "lib" / "libsemihost.a"), "-o", str(work / "prog.elf")]),
    ]
    for name, cmd in steps:
        res = run(cmd)
        if res.returncode != 0:
            print(f"test-picolibc-smoke: FAIL ({name} rc={res.returncode})\n{res.stderr}", file=sys.stderr)
            return 1

    qemu = [str(TOOLCHAIN_BIN / "qemu-system-dadao"), "-M", "dadao-m1", "-kernel", str(work / "prog.elf"),
            "-semihosting-config", "enable=on,target=native", "-display", "none", "-nographic", "-monitor", "none"]
    try:
        res = run(qemu, timeout=args.qemu_timeout, merge=True)
    except subprocess.TimeoutExpired:
        print(f"test-picolibc-smoke: FAIL (qemu timeout after {args.qemu_timeout}s)", file=sys.stderr)
        return 1

    marker = "XX" if args.inject else EXPECTED_MARKER
    guest_out = res.stdout
    print(f"test-picolibc-smoke: qemu rc={res.returncode} output={guest_out!r}")
    ok = res.returncode == 0 and any(marker in line for line in guest_out.splitlines())
    if not ok:
        print(f"test-picolibc-smoke: FAIL (expected exit 0 and line {marker!r})", file=sys.stderr)
        return 1
    print("test-picolibc-smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
