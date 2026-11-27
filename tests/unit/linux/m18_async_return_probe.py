#!/usr/bin/env python3
"""m18_async_return_probe.py — user-mode async return must not lose a task.

`m18-linux-007` reported that a *pure user-mode busy-wait* program is the
strongest reproducer of the "K2 async user" hang: the console ends on the
kernel's async-entry line and the task never makes progress again (no
`PTHREAD end`, no die/panic).  This probe turns that reproducer into a
standalone, deterministic case (`m18-linux-028`): a static musl program whose
threads never trap after `pthread_create` — they spin on a volatile word until a
fixed iteration count is consumed, then record `done[idx]`; main spins on
`done[]` and prints `BUSY end` only when every worker finished.

The thread stacks are supplied by the program (`pthread_attr_setstack` over a
pre-touched static array), so the workers' first runs do not take a user page
fault: the case then exercises exactly the user-mode async capture/return path
and the judged console carries only the program's own lines.  (A run without
pre-touched stacks additionally drives the *separate* kernel page-fault channel
and is not this case: the fault channel's own frame lifetime is ISS-m18-011.)

Judged facts: the program ran as `/init`, its own `BUSY end` line appears
exactly once, the QEMU exit status is the program's, and no failure text
appears.  A run that ends on `K2 async user` and has no `BUSY end` line is the
issue's signature (measured 3/3 on the pre-fix kernel).

Exit status: 0 = built and every boot judged PASS; 1 = a boot FAILED/hung;
2 = a setup/derivation input is missing.

The image is built exactly like `m18_pthread_probe.py` (K6 chain, own cpio);
``--qemu`` / ``M18A_QEMU`` selects the binary (this worktree's private build by
default when it exists, so the shared install root is never touched).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.infra import build_musl as musl_elf                  # noqa: E402
from tools.linux import config_pins as pins                    # noqa: E402
from tools.linux import make_defconfig as defconfig            # noqa: E402
from tools.linux import make_initramfs as newc                 # noqa: E402
from tools.linux import paths as linux_paths                   # noqa: E402
from tools.qemu import k0_boot_probe as k0                     # noqa: E402

TARGET = "dadao-unknown-elf"
JOBS = os.environ.get("JOBS", "32")
TIMEOUT_QEMU = int(os.environ.get("M18A_QEMU_TIMEOUT", "180"))

NTHREADS = int(os.environ.get("M18A_NTHREADS", "4"))
SPIN = int(os.environ.get("M18A_SPIN", "400000000"))

CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "n",
}

K6_SHELL_LINE = "CONFIG_DADAO_K6_SHELL=y"

BUSY_C = r"""
#include <pthread.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define N %(n)d
#define SPIN %(spin)dUL

static volatile int start;
static volatile int done[N];
static char stacks[N][65536] __attribute__((aligned(16)));

static void *worker(void *p)
{
    long idx = (long)p;
    volatile unsigned long i;

    /* Pure user-mode busy wait: after pthread_create this thread takes no
     * trap until it is done, so the only kernel entries are timer ticks. */
    while (!start)
        ;
    for (i = 0; i < SPIN; i++)
        ;
    done[idx] = 1;
    return 0;
}

int main(void)
{
    pthread_t tids[N];
    long i;

    setvbuf(stdout, 0, _IONBF, 0);
    printf("BUSY begin n=%%d spin=%%lu\n", N, SPIN);
    for (i = 0; i < N; i++)
        memset(stacks[i], 0x5a, sizeof(stacks[i]));
    for (i = 0; i < N; i++) {
        pthread_attr_t at;
        pthread_attr_init(&at);
        pthread_attr_setstack(&at, stacks[i], sizeof(stacks[i]));
        if (pthread_create(&tids[i], &at, worker, (void *)i)) {
            printf("BUSY create-fail idx=%%ld\n", i);
            return 2;
        }
    }
    start = 1;
    for (;;) {
        int all = 1;
        for (i = 0; i < N; i++)
            all = all && done[i];
        if (all)
            break;
    }
    printf("BUSY end\n");
    return 0;
}

""" % {"n": NTHREADS, "spin": SPIN}


class SetupError(RuntimeError):
    """Missing prerequisite (exit 2)."""


def image_root() -> Path:
    return linux_paths.linux_build_dir().parent / "async-return-image"


def build_root() -> Path:
    return image_root() / "build"


def image_dir() -> Path:
    return image_root() / "image"


def image_cpio() -> Path:
    return image_dir() / "initramfs.cpio"


def tool(name: str) -> Path:
    path = linux_paths.toolchain_bin() / name
    if not path.is_file():
        raise SetupError(f"{path} not found — run 'make install-host' first")
    return path


def musl_dir() -> Path:
    musl = linux_paths.linux_source_dir().parent / "musl"
    for rel in ("lib/crt1.o", "lib/libc.a"):
        if not (musl / rel).is_file():
            raise SetupError(f"{musl / rel} not found — run 'make build-musl' first")
    return musl


def include_flags(musl: Path) -> list[str]:
    return [f"-I{musl / 'arch' / 'dadao'}", f"-I{musl / 'arch' / 'generic'}",
            f"-I{musl / 'obj' / 'include'}", f"-I{musl / 'include'}"]


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run([str(c) for c in cmd], cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    if proc.returncode != 0:
        raise SetupError(f"command failed (rc={proc.returncode}): "
                         f"{' '.join(str(c) for c in cmd)}\n{proc.stdout}")
    return proc


def builtins_archive() -> Path:
    proc = subprocess.run([str(tool("clang")), f"--target={TARGET}",
                           "-rtlib=compiler-rt", "-print-libgcc-file-name"],
                          capture_output=True, text=True)
    path = Path(proc.stdout.strip())
    if proc.returncode != 0 or not path.is_file():
        raise SetupError("target builtins archive not found — run 'make install-host'")
    return path


def build_program(musl: Path) -> Path:
    build_root().mkdir(parents=True, exist_ok=True)
    src = build_root() / "busy_init.c"
    obj = build_root() / "busy_init.o"
    elf = build_root() / "busy_init"
    src.write_text(BUSY_C)
    run([tool("clang"), f"--target={TARGET}", "-O1", "-nostdinc",
         "-ffile-prefix-map=" + str(_REPO) + "=.",
         *include_flags(musl), "-c", str(src), "-o", str(obj)], cwd=_REPO)
    run([tool("ld.lld"), musl / "lib" / "crt1.o", obj,
         "--start-group", musl / "lib" / "libc.a", builtins_archive(),
         "--end-group", "-o", str(elf)], cwd=_REPO)
    elf.chmod(0o755)
    return elf


def check_static_elf(elf: Path) -> list[tuple[str, str, str, bool]]:
    info = musl_elf.parse_elf(elf)
    return [
        ("ELF type (static ET_EXEC)", "2", str(info["e_type"]), info["e_type"] == 2),
        ("e_machine EM_DADAO", "0x0da0", f"0x{info['e_machine']:04x}",
         info["e_machine"] == musl_elf.EM_DADAO),
        ("no PT_INTERP", "absent",
         "present" if any(p["type"] == 3 for p in info["phdrs"]) else "absent",
         not any(p["type"] == 3 for p in info["phdrs"])),
    ]


def build_cpio(elf_bytes: bytes) -> bytes:
    entries = [
        newc.Entry(".", newc.MODE_DIR, "dir", b""),
        newc.Entry("dev", newc.MODE_DIR, "dir", b""),
        newc.Entry("dev/console", newc.MODE_CHARDEV, "chardev", b"", 240, 0),
        newc.Entry("init", newc.MODE_FILE, "file", elf_bytes),
    ]
    entries.sort(key=lambda entry: entry.name)
    encoded = [
        newc._newc_entry(entry.name, index + 1, entry.mode, entry.data,
                         nlink=(2 if entry.kind == "dir" else 1), mtime=0,
                         rdevmajor=entry.rdevmajor, rdevminor=entry.rdevminor)
        for index, entry in enumerate(entries)
    ]
    encoded.append(newc._newc_entry(newc.CPIO_TRAILER, 0, 0, b"", nlink=1, mtime=0))
    return b"".join(encoded)


def current_initramfs_source() -> str | None:
    config = linux_paths.linux_build_dir() / ".config"
    if not config.is_file():
        return None
    m = re.search(r'^CONFIG_INITRAMFS_SOURCE="([^"]*)"', config.read_text(encoding="utf-8"),
                  re.M)
    return m.group(1) if m else None


def build_image() -> dict:
    musl = musl_dir()
    elf = build_program(musl)
    checks = check_static_elf(elf)
    failed = 0
    for name, expected, actual, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] static ELF: {name} | "
              f"期望={expected} 实际={actual}")
        failed += 0 if ok else 1
    if failed:
        raise SetupError(f"{failed}/{len(checks)} static ELF checks failed")

    elf_bytes = elf.read_bytes()
    cpio = build_cpio(elf_bytes)
    image_dir().mkdir(parents=True, exist_ok=True)
    image_cpio().write_bytes(cpio)
    if not (linux_paths.linux_build_dir() / ".config").is_file():
        rc = subprocess.call([sys.executable,
                              str(_REPO / "tools" / "linux" / "make_defconfig.py"),
                              "--jobs", JOBS], cwd=str(_REPO))
        if rc != 0:
            raise SetupError(f"make_defconfig failed (rc={rc})")
    previous = current_initramfs_source()
    lines = list(pins.config_lines(CONFIG_PINS))
    lines += [K6_SHELL_LINE, f'CONFIG_INITRAMFS_SOURCE="{image_cpio()}"']
    rc = defconfig.apply_config_lines(lines)
    if rc != 0:
        raise SetupError(f"applying the image config slice failed (rc={rc})")
    try:
        build = subprocess.call(
            [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
             "--jobs", JOBS, "--skip-code-range"], cwd=str(_REPO))
    finally:
        restore = previous if previous else str(
            linux_paths.linux_initramfs_dir() / "initramfs.cpio")
        defconfig.apply_config_lines([f'CONFIG_INITRAMFS_SOURCE="{restore}"'])
    if build != 0:
        raise SetupError(f"kernel build failed (rc={build})")

    manifest = {
        "program": {"md5": hashlib.md5(elf_bytes).hexdigest(),
                    "sha256": hashlib.sha256(elf_bytes).hexdigest(),
                    "size": len(elf_bytes)},
        "cpio": {"name": image_cpio().name, "size": len(cpio),
                 "sha256": hashlib.sha256(cpio).hexdigest()},
        "vmlinux": str(linux_paths.linux_build_dir() / "vmlinux"),
        "spin": SPIN,
    }
    (image_dir() / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[INFO] image: /init sha256={manifest['program']['sha256'][:12]} "
          f"cpio sha256={manifest['cpio']['sha256'][:12]} spin={SPIN}")
    return manifest


def firmware() -> str:
    k0.load_contract()
    if not k0.ABI:
        raise SetupError("the boot contract is empty — cannot build the bootrom")
    scratch = image_root() / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(scratch / "bootrom"), name="bootrom_m18a.bin")


def default_qemu() -> str:
    env = os.environ.get("M18A_QEMU")
    if env:
        return env
    private = _REPO / ".work" / "build" / "qemu" / "qemu-system-dadao"
    if private.is_file():
        return str(private)
    return str(linux_paths.toolchain_bin() / "qemu-system-dadao")


def boot(tag: str, qemu: str) -> tuple[int, str]:
    vmlinux = linux_paths.linux_build_dir() / "vmlinux"
    if not vmlinux.is_file():
        raise SetupError(f"{vmlinux} missing — the kernel build did not produce it")
    if not os.access(qemu, os.X_OK):
        raise SetupError(f"{qemu} missing — run 'make build-qemu'")
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={firmware()}",
           "-display", "none", "-serial", "none",
           "-chardev", "stdio,id=semi",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-kernel", str(vmlinux)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
        text = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        text = out
    log = image_root() / "log"
    log.mkdir(parents=True, exist_ok=True)
    (log / f"{tag}.log").write_text(text, encoding="utf-8")
    return rc, text


def judge(tag: str, rc: int, text: str) -> list[tuple[str, str, str, bool]]:
    checks = [
        (f"{tag}: kernel ran /init as init", "present",
         "present" if "Run /init as init process" in text else "absent",
         "Run /init as init process" in text),
        (f"{tag}: begin line", 1, text.count("BUSY begin n=%d spin=%d" %
                                             (NTHREADS, SPIN)),
         text.count("BUSY begin n=%d spin=%d" % (NTHREADS, SPIN)) == 1),
        (f"{tag}: end line", 1, text.count("BUSY end"), text.count("BUSY end") == 1),
        (f"{tag}: PID 1 exit status is the program status", "0", str(rc), rc == 0),
    ]
    bad = [line.strip() for line in text.splitlines()
           if re.search(r"(panic|Kernel panic|Attempted to kill init|BUG:|Oops|"
                        r"BUSY create-fail)", line)]
    checks.append((f"{tag}: no failure text", [], bad, not bad))
    return checks


def signature(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    tail = lines[-1].strip() if lines else "<empty>"
    n = sum(1 for ln in lines if "K2 async user" in ln)
    return f"async_user_lines={n}; last={tail!r}"


def report(checks: list[tuple[str, str, str, bool]]) -> int:
    failed = 0
    for name, expected, actual, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} | 期望={expected} 实际={actual}")
        failed += 0 if ok else 1
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--boots", type=int, default=1)
    parser.add_argument("--no-boot", action="store_true")
    parser.add_argument("--tag", default="run")
    parser.add_argument("--qemu", default=None)
    parser.add_argument("--build-only", action="store_true",
                        help="reuse the existing image/vmlinux, do not rebuild")
    args = parser.parse_args()

    try:
        if args.build_only:
            elf = build_root() / "busy_init"
            manifest = json.loads((image_dir() / "manifest.json").read_text())
            print(f"[INFO] reuse image /init sha256={manifest['program']['sha256'][:12]}")
        else:
            manifest = build_image()
        qemu = args.qemu or default_qemu()
        print(f"[INFO] qemu={qemu} md5={hashlib.md5(Path(qemu).read_bytes()).hexdigest()}")
        if args.no_boot:
            print("m18_async_return_probe: PASS (image built; boots skipped)")
            return 0
        fails = 0
        for index in range(args.boots):
            tag = f"{args.tag}-{index + 1}"
            rc, text = boot(tag, qemu)
            checks = judge(tag, rc, text)
            bad = report(checks)
            print(f"[INFO] {tag}: qemu rc={rc}; {len(checks) - bad}/{len(checks)} "
                  f"checks passed; {signature(text)}; "
                  f"log {image_root() / 'log' / (tag + '.log')}")
            fails += bad
        if fails:
            print(f"m18_async_return_probe: FAIL ({fails} check(s) across "
                  f"{args.boots} boot(s))")
            return 1
        print(f"m18_async_return_probe: PASS ({args.boots}/{args.boots} boots)")
        return 0
    except SetupError as exc:
        print(f"m18_async_return_probe: SETUP ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
