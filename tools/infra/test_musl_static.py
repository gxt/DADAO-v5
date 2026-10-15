#!/usr/bin/env python3
"""Static musl end-to-end test for DADAO (INFRA-082t stage B).

Proves the P1 goal end to end: a *static* musl program built with
``clang -target dadao-unknown-elf`` links against the DADAO musl port
(``.work/source/musl``, built by ``make build-musl``) and **runs on the
``dadao-m1`` machine**, with the guest's stdout bytes and exit status reaching
the host unchanged.

Path B (the raw-bin dual image, ADR-0004 D2.3): the SEE bootrom firmware
(``tests/scripts/bootrom.S`` -> ``bootrom.bin``) is loaded with ``-bios``; it
configures the cfx registers and hands off to the application in ``user`` mode.
The application is the flat image (``llvm-objcopy -O binary`` of the linked
ELF, ``tests/scripts/dadao.lds``) loaded at the RAM base by ``-kernel``.
``-kernel <ELF>`` (path A) is deliberately NOT used: the reset run mode there is
``hypv``, so a user-mode ``umon`` syscall is never reached
(``contract-syscall §6``; INFRA-082t stage A1 completion note).

Each program is one property of the contract; expectations are derived
independently of both QEMU and LLVM (``contract-syscall §5``):

  exit_code      main() returns 42        -> host $? == 42 (exit_group carries
                                             the status, Machine-01 §5.5)
  hello          write(1, "hello\\n", 6)   -> stdout == b"hello\\n", $? == 0
  be_word        write(1, &word, 8) with
                 word = 0x0102030405060708 -> stdout == the *big-endian*
                                             encoding of that integer
                                             (ADR-0003 D1: EI_DATA =
                                             ELFDATA2MSB); a little-endian
                                             machine would emit the reverse
                                             byte order, so this case is
                                             endianness-sensitive (the harness
                                             asserts BE != LE, then compares)
  errno_ebadf    write(-1, ...)           -> errno == EBADF (9, asm-generic
                                             errno.h): `errno` is reached
                                             through __pthread_self(), i.e.
                                             through the TP register / TCB
                                             installed by the musl startup path
  tid            syscall(SYS_set_tid_address, &p) -> the service returns the
                                             machine's single-process thread id
                                             (DADAO_UMON_TID, printed as 8
                                             big-endian bytes); before stage B
                                             this call answered -ENOSYS
  argmask_slot   main returns __dadao_argmask(SYS_set_tid_address)
                                           -> 1: the port's pointer-argument
                                             mask has set_tid_address in slot 0,
                                             as contract-syscall §3 requires for
                                             the Linux prototype
                                             `set_tid_address(int *)`

Exit status: 0 = PASS, 1 = FAIL (mismatch / timeout / failed step), 2 = setup
error (missing toolchain, library, bootrom).  Fail-closed: never a silent skip.

``--inject`` corrupts the expectations so every comparison must FAIL (proving
the comparisons are live); it is only used by the INFRA-082t evidence script,
which pairs it with artifact-level negative controls.

Usage:
  test_musl_static.py                 # run every case
  test_musl_static.py --only NAME     # run one case
  test_musl_static.py --list
  test_musl_static.py --inject        # corrupt every expectation (must FAIL)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
TEST_ARTIFACTS = paths.test_artifacts_dir()
MUSL_SRC = REPO_ROOT / ".work" / "source" / "musl"
LDS = REPO_ROOT / "tests" / "scripts" / "dadao.lds"
DEFAULT_BOOTROM = TEST_ARTIFACTS / "bootrom" / "bootrom.bin"
TARGET = "dadao-unknown-elf"
TIMEOUT = 20

# Independent expectations (see the module docstring).
BE_WORD = 0x0102030405060708
ERRNO_EBADF = 9          # asm-generic/errno.h
SINGLE_PROCESS_TID = 1   # DADAO_UMON_TID: the kernel-less model's one process

PROG_EXIT = """\
int main(void) { return 42; }
"""

PROG_HELLO = """\
#include <unistd.h>

/* "hello\\n" lives in a volatile object so clang cannot fold the call away. */
static volatile char msg[] = "hello\\n";

int main(void)
{
    write(1, (const void *)msg, 6);
    return 0;
}
"""

PROG_BE = """\
#include <unistd.h>

/* Write the *raw bytes* of a 64-bit integer: the expected byte string is the
   big-endian encoding, so a little-endian machine would be caught here. */
static volatile unsigned long long word = 0x0102030405060708ULL;

int main(void)
{
    write(1, (const void *)&word, 8);
    return 0;
}
"""

PROG_ERRNO = """\
#include <unistd.h>
#include <errno.h>

/* fd -1 has no host stream: the umon service answers -EBADF and musl stores
   errno; errno itself is reached through __pthread_self() (the TCB reached via
   the TP register), so this exercises the startup TLS/TP path too. */
static volatile int bad_fd = -1;

int main(void)
{
    unsigned char e;
    errno = 0;
    (void)write(bad_fd, (const void *)"x", 1);
    e = (unsigned char)errno;
    write(1, (const void *)&e, 1);
    return 0;
}
"""

PROG_TID = """\
#include <unistd.h>
#include <sys/syscall.h>

/* musl's startup path calls set_tid_address unconditionally
   (src/env/__init_tls.c: __init_tp).  As a public syscall it must return the
   machine's single-process thread id instead of -ENOSYS. */
static volatile int tidptr;

int main(void)
{
    unsigned long long u = (unsigned long long)syscall(SYS_set_tid_address,
                                                       (void *)&tidptr);
    unsigned char b[8];
    int i;
    for (i = 0; i < 8; i++)
        b[i] = (unsigned char)(u >> (8 * (7 - i)));
    write(1, (const void *)b, 8);
    return 0;
}
"""

PROG_ARGMASK = """\
/* The pointer-argument mask the port uses to route syscall arguments into the
   RD / RB banks.  set_tid_address(int *) has one pointer argument in slot 0
   (contract-syscall §3), so the mask must be 0x01.  The program's exit status
   is that mask value. */
#include "syscall_arch.h"

int main(void)
{
    return __dadao_argmask(SYS_set_tid_address);
}
"""

CASES = [
    {"name": "exit_code", "desc": "main() returns 42 -> host $? == 42",
     "src": PROG_EXIT, "stdout": b"", "exit": 42},
    {"name": "hello", "desc": 'write(1, "hello\\n", 6) -> stdout + exit 0',
     "src": PROG_HELLO, "stdout": b"hello\n", "exit": 0},
    {"name": "be_word", "desc": "raw bytes of a u64 are big-endian (BE-sensitive)",
     "src": PROG_BE, "stdout": BE_WORD.to_bytes(8, "big"), "exit": 0},
    {"name": "errno_ebadf", "desc": "write(-1,..) -> errno == EBADF (9) via TP/TCB",
     "src": PROG_ERRNO, "stdout": bytes([ERRNO_EBADF]), "exit": 0},
    {"name": "tid", "desc": "set_tid_address(96) returns the single-process tid",
     "src": PROG_TID, "stdout": SINGLE_PROCESS_TID.to_bytes(8, "big"), "exit": 0},
    {"name": "argmask_slot", "desc": "argmask(96) == slot 0 (pointer argument)",
     "src": PROG_ARGMASK, "stdout": b"", "exit": 0x01},
]


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None,
        timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=timeout)


def toolchain_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{TOOLCHAIN_BIN}:{env.get('PATH', '')}"
    return env


def include_flags() -> str:
    return "".join(f"-I{MUSL_SRC}/{d} " for d in
                   ("arch/dadao", "arch/generic", "obj/src/internal",
                    "src/include", "src/internal", "obj/include", "include"))


def compile_link_flat(work: Path, name: str, src: str) -> Path:
    """Compile -> link (crt1.o + libc.a + dadao.lds) -> flat ``-kernel`` image."""
    csrc = work / f"{name}.c"
    obj = work / f"{name}.o"
    elf = work / f"{name}.elf"
    flat = work / f"{name}.bin"
    csrc.write_text(src)

    res = run(["sh", "-c", f"clang --target={TARGET} -O1 -nostdinc "
                           f"{include_flags()}-c {csrc} -o {obj}"],
              cwd=REPO_ROOT, env=toolchain_env())
    if res.returncode != 0:
        raise RuntimeError(f"compile rc={res.returncode}\n{res.stdout}")

    res = run([str(TOOLCHAIN_BIN / "ld.lld"), "-T", str(LDS),
               str(MUSL_SRC / "lib" / "crt1.o"), str(obj),
               str(MUSL_SRC / "lib" / "libc.a"), "-o", str(elf)],
              cwd=REPO_ROOT)
    if res.returncode != 0:
        raise RuntimeError(f"link rc={res.returncode}\n{res.stdout}")

    res = run([str(TOOLCHAIN_BIN / "llvm-objcopy"), "-O", "binary",
               str(elf), str(flat)], cwd=REPO_ROOT)
    if res.returncode != 0:
        raise RuntimeError(f"objcopy rc={res.returncode}\n{res.stdout}")
    return flat


def run_qemu(qemu: str, bootrom: Path, flat: Path) -> dict:
    """Run the flat image on dadao-m1 through the bootrom (path B)."""
    cmd = [qemu, "-M", "dadao-m1", "-nographic", "-monitor", "none",
           "-bios", str(bootrom), "-kernel", str(flat)]
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"timeout": True}
    return {"timeout": False, "exit": r.returncode & 0xFF,
            "stdout": r.stdout, "stderr": r.stderr}


def check(name: str, expected, actual, ok: bool) -> tuple[str, str, str, bool]:
    return (name, expected, actual, ok)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir",
                    default=str(REPO_ROOT / ".work" / "build" / "musl-e2e"),
                    help="scratch dir for generated sources/objects/images")
    ap.add_argument("--qemu", default=str(TOOLCHAIN_BIN / "qemu-system-dadao"))
    ap.add_argument("--bootrom", default=str(DEFAULT_BOOTROM))
    ap.add_argument("--only", action="append", default=[],
                    help="run only the named case(s)")
    ap.add_argument("--list", action="store_true", help="list the cases and exit")
    ap.add_argument("--inject", action="store_true",
                    help="corrupt the expectations so the checks must FAIL")
    args = ap.parse_args()

    if args.list:
        for case in CASES:
            print(f"{case['name']:<14} {case['desc']}")
        return 0

    for tool in ("clang", "ld.lld", "llvm-objcopy"):
        if not (TOOLCHAIN_BIN / tool).exists():
            print(f"test-musl-static: ERROR: {TOOLCHAIN_BIN / tool} not found "
                  "(run 'make install-host')", file=sys.stderr)
            return 2
    if not (MUSL_SRC / "lib" / "libc.a").is_file():
        print(f"test-musl-static: ERROR: {MUSL_SRC}/lib/libc.a not found "
              "(run 'make build-musl')", file=sys.stderr)
        return 2
    if not Path(args.qemu).is_file():
        print(f"test-musl-static: ERROR: qemu not found: {args.qemu} "
              "(run 'make install-host')", file=sys.stderr)
        return 2
    if not Path(args.bootrom).is_file():
        print(f"test-musl-static: ERROR: bootrom not found: {args.bootrom} "
              "(run 'make build-bootrom')", file=sys.stderr)
        return 2

    # Sanity: the BE expectation must not coincide with the LE encoding, or the
    # endianness case would not be able to fail.
    be = BE_WORD.to_bytes(8, "big")
    le = BE_WORD.to_bytes(8, "little")
    if be == le:
        print("test-musl-static: ERROR: BE/LE encodings coincide: the "
              "endianness case could not fail", file=sys.stderr)
        return 2

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    selected = [c for c in CASES if not args.only or c["name"] in args.only]
    if args.only and len(selected) != len(args.only):
        print("test-musl-static: ERROR: unknown case in --only", file=sys.stderr)
        return 2

    total = failed = 0
    for case in selected:
        name = case["name"]
        exp_stdout = case["stdout"]
        exp_exit = case["exit"]
        if args.inject:
            exp_stdout = b"\x00INJECTED"
            exp_exit = (exp_exit + 1) & 0xFF

        total += 1
        try:
            flat = compile_link_flat(work, name, case["src"])
        except RuntimeError as exc:
            failed += 1
            print(f"FAIL {name}: build failed ({exc})")
            continue

        obs = run_qemu(args.qemu, Path(args.bootrom), flat)
        if obs["timeout"]:
            failed += 1
            print(f"FAIL {name}: qemu timed out after {TIMEOUT}s")
            continue

        checks = [
            check("stdout", repr(exp_stdout), repr(obs["stdout"]),
                  obs["stdout"] == exp_stdout),
            check("exit code", str(exp_exit), str(obs["exit"]),
                  obs["exit"] == exp_exit),
        ]
        bad = [c for c in checks if not c[3]]
        if bad:
            failed += 1
            print(f"FAIL {name}: {case['desc']}")
            for cname, e, a, good in checks:
                print(f"       {'ok  ' if good else 'FAIL'} {cname}: "
                      f"expected={e} actual={a}")
        else:
            print(f"PASS {name}: {case['desc']} "
                  f"(stdout={obs['stdout']!r} exit={obs['exit']})")

    print(f"test-musl-static: {total - failed}/{total} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
