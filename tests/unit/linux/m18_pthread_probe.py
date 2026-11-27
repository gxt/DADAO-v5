#!/usr/bin/env python3
"""m18_pthread_probe.py — M18 K6 pthread create/join closure (`m18-linux-007`).

The K6 image runs a static musl program as PID 1 from the initramfs (the same
``/init`` chain ``check-linux-k6`` uses, ``CONFIG_DADAO_K6_SHELL=y``).  This
probe's ``/init`` is a static musl test program built from ``PTHREAD_C`` below;
the image is this probe's own cpio, so no busybox/shell is involved and the
judged bytes are only the program's own.

What the program proves, and where each expectation comes from:

  * ``pthread_create`` x 4 + ``pthread_join`` (``void *`` return for even
    indices, ``pthread_exit`` value for odd ones): the return values are the
    worker's own ``0x100 + idx``; musl's ``pthread_create``/``join`` are the
    upstream implementation (components/musl), the syscall side is
    ``contract-syscall §10``/``§11`` (clone child starts at the return with
    ``rd8 = 0``; the kernel only guarantees the frame, the dual return is
    musl's wrapper).
  * ``pthread_self``: every worker sees the same handle twice and a handle
    different from main's (the thread pointer in ``rb3``, ``§10``).
  * per-thread ``__thread``: each worker writes ``idx*10+1``, waits at a
    barrier, then re-reads.  A shared/global TLS slot would let the last writer
    overwrite the others, so at least two of the re-reads differ from their own
    value -- the check is reachable, not "print a constant".
  * ``pthread_detach``: a joinable thread is detached and runs to completion;
    its line is emitted before the second barrier, so the harness sees it.
  * negative: ``pthread_create`` under ``RLIMIT_AS = 4096`` (no room for a
    thread stack) must return ``EAGAIN``.  musl turns *every* ``__clone``
    failure into ``EAGAIN`` (``src/thread/pthread_create.c``), and ``EAGAIN``'s
    value is read from the image's ``bits/errno.h``, not written here
    (``contract-syscall §4/§9``: errors are ``-errno`` in ``rd8``; the musl
    layer exposes them as the positive errno value).

Judged facts are exact lines (``PTHREAD ...``), each expected exactly once,
plus the QEMU exit status (PID 1 exit is the host process status: the kernel's
``kernel/exit.c`` DADAO patch hands it to semihosting -- the same mechanism K6
uses) and the absence of failure/panic text.

The static ELF itself is asserted first: ET_EXEC, EM_DADAO, no ``PT_INTERP``/
``PT_DYNAMIC``, and exactly one ``PT_TLS`` (the mechanism the ``__thread``
checks exercise).

Exit status: 0 = built and every boot judged PASS; 1 = a check/boot FAILED;
2 = a setup/derivation input is missing (toolchain, musl archive, kernel tree).
"""
from __future__ import annotations

import argparse
import hashlib
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
TIMEOUT_BUILD = int(os.environ.get("M18P_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("M18P_QEMU_TIMEOUT", "180"))

NTHREADS = 4

#: Every ``CONFIG_DADAO_*`` symbol of ``Kconfig.debug`` (``check-config-pins``
#: C3 requires the key set to equal the Kconfig set).  This is the production
#: boot the K6 gate uses: every probe off, the K6 continuation on.
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

#: The K6 continuation symbol lives in ``Kconfig`` (not ``Kconfig.debug``), so
#: it is not part of the pin set; kept as a name so C4 stays true.
K6_SHELL_LINE = "CONFIG_DADAO_K6_SHELL=y"

PTHREAD_C = r"""
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/resource.h>
#include <stdint.h>

#define N 4
#define NBAR (N + 2)            /* workers + detached + main */

static __thread int tls_v;
static pthread_t main_tid;
static pthread_barrier_t barrier1, barrier2;

struct arg {
    int idx;
    int detached;
    pthread_t self;
};

static void *worker(void *p)
{
    struct arg *a = p;
    pthread_t s1 = pthread_self();
    pthread_t s2 = pthread_self();

    a->self = s1;
    tls_v = a->idx * 10 + 1;
    pthread_barrier_wait(&barrier1);

    int tls2 = tls_v;
    int self_eq = pthread_equal(s1, s2) && pthread_equal(s1, a->self);
    int main_diff = !pthread_equal(s1, main_tid);
    printf("PTHREAD worker idx=%d detach=%d self-eq=%d main-diff=%d "
           "tls=%d tls2=%d\n", a->idx, a->detached, self_eq, main_diff,
           tls_v, tls2);

    pthread_barrier_wait(&barrier2);
    if (a->detached)
        return 0;
    if (a->idx & 1)
        pthread_exit((void *)(uintptr_t)(0x100 + a->idx));
    return (void *)(uintptr_t)(0x100 + a->idx);
}

int main(void)
{
    struct arg args[N + 1];
    pthread_t tids[N];
    pthread_t detached;
    int fails = 0;
    int i, rc;

    setvbuf(stdout, 0, _IONBF, 0);
    main_tid = pthread_self();
    printf("PTHREAD begin n=%d\n", N);

    if (pthread_barrier_init(&barrier1, 0, NBAR) ||
        pthread_barrier_init(&barrier2, 0, NBAR)) {
        printf("PTHREAD barrier-init fail\n");
        return 2;
    }

    memset(args, 0, sizeof(args));
    for (i = 0; i < N; i++) {
        args[i].idx = i;
        args[i].detached = 0;
        rc = pthread_create(&tids[i], 0, worker, &args[i]);
        if (rc) {
            printf("PTHREAD create-fail idx=%d rc=%d\n", i, rc);
            return 2;
        }
    }
    args[N].idx = N;
    args[N].detached = 1;
    rc = pthread_create(&detached, 0, worker, &args[N]);
    if (rc) {
        printf("PTHREAD create-fail idx=%d rc=%d\n", N, rc);
        return 2;
    }
    rc = pthread_detach(detached);
    printf("PTHREAD detach rc=%d\n", rc);
    if (rc)
        fails++;

    pthread_barrier_wait(&barrier1);
    printf("PTHREAD main-tls=%d\n", tls_v);
    if (tls_v != 0)
        fails++;
    pthread_barrier_wait(&barrier2);

    for (i = 0; i < N; i++) {
        void *ret = 0;
        rc = pthread_join(tids[i], &ret);
        printf("PTHREAD join idx=%d self-same=%d rc=%d ret=0x%lx\n",
               i, pthread_equal(tids[i], args[i].self), rc,
               (unsigned long)ret);
        if (rc || ret != (void *)(uintptr_t)(0x100 + i))
            fails++;
    }

    /*
     * Negative case: no address space left for a thread stack.  musl maps the
     * stack before clone and returns EAGAIN when the mapping fails; every
     * __clone failure is translated to EAGAIN as well.
     */
    {
        struct rlimit old, lim;
        int neg = -1;
        if (getrlimit(RLIMIT_AS, &old) == 0) {
            lim = old;
            lim.rlim_cur = 4096;
            if (lim.rlim_max != RLIM_INFINITY && lim.rlim_cur > lim.rlim_max)
                lim.rlim_cur = lim.rlim_max;
            if (setrlimit(RLIMIT_AS, &lim) == 0) {
                pthread_t bad;
                neg = pthread_create(&bad, 0, worker, &args[0]);
                setrlimit(RLIMIT_AS, &old);
            }
        }
        printf("PTHREAD neg-eagain rc=%d\n", neg);
        if (neg != EAGAIN)
            fails++;
    }

    printf("PTHREAD end fails=%d\n", fails);
    return fails ? 1 : 0;
}
"""


class SetupError(RuntimeError):
    """Missing prerequisite (exit 2)."""


def image_root() -> Path:
    """Disposable runtime root (sibling of the kernel build tree)."""
    return linux_paths.linux_build_dir().parent / "pthread-image"


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
    src = build_root() / "pthread_init.c"
    obj = build_root() / "pthread_init.o"
    elf = build_root() / "pthread_init"
    src.write_text(PTHREAD_C)
    run([tool("clang"), f"--target={TARGET}", "-O1", "-nostdinc",
         "-ffile-prefix-map=" + str(_REPO) + "=.",
         *include_flags(musl), "-c", str(src), "-o", str(obj)], cwd=_REPO)
    run([tool("ld.lld"), musl / "lib" / "crt1.o", obj,
         "--start-group", musl / "lib" / "libc.a", builtins_archive(),
         "--end-group", "-o", str(elf)], cwd=_REPO)
    elf.chmod(0o755)
    return elf


def check_static_elf(elf: Path, musl: Path) -> list[tuple[str, str, str, bool]]:
    info = musl_elf.parse_elf(elf)
    pt_tls = [p for p in info["phdrs"] if p["type"] == 7]
    return [
        ("ELF class", "2", str(info["ei_class"]), info["ei_class"] == 2),
        ("ELF data (big endian)", "2", str(info["ei_data"]), info["ei_data"] == 2),
        ("ELF type (static ET_EXEC)", "2", str(info["e_type"]), info["e_type"] == 2),
        ("e_machine EM_DADAO", "0x0da0", f"0x{info['e_machine']:04x}",
         info["e_machine"] == musl_elf.EM_DADAO),
        ("no PT_INTERP", "absent",
         "present" if any(p["type"] == 3 for p in info["phdrs"]) else "absent",
         not any(p["type"] == 3 for p in info["phdrs"])),
        ("no PT_DYNAMIC", "absent",
         "present" if any(p["type"] == 2 for p in info["phdrs"]) else "absent",
         not any(p["type"] == 2 for p in info["phdrs"])),
        ("exactly one PT_TLS (static __thread)", 1, len(pt_tls), len(pt_tls) == 1),
        ("libc.a present", "lib/libc.a", str(musl / "lib" / "libc.a"),
         (musl / "lib" / "libc.a").is_file()),
    ]


def errno_eagain(musl: Path) -> int:
    """``EAGAIN`` from the generated target header (never written here)."""
    for rel in ("obj/include/bits/errno.h", "arch/dadao/bits/errno.h",
                "arch/generic/bits/errno.h"):
        path = musl / rel
        if not path.is_file():
            continue
        m = re.search(r"^#define\s+EAGAIN\s+(\d+)", path.read_text(encoding="utf-8"),
                      re.M)
        if m:
            return int(m.group(1))
    raise SetupError("cannot derive EAGAIN from the musl headers")


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
    checks = check_static_elf(elf, musl)
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
        "program": {
            "md5": hashlib.md5(elf_bytes).hexdigest(),
            "sha256": hashlib.sha256(elf_bytes).hexdigest(),
            "size": len(elf_bytes),
        },
        "cpio": {
            "name": image_cpio().name,
            "size": len(cpio),
            "sha256": hashlib.sha256(cpio).hexdigest(),
        },
        "vmlinux": str(linux_paths.linux_build_dir() / "vmlinux"),
        "eagain": errno_eagain(musl),
    }
    import json
    (image_dir() / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[INFO] image: /init sha256={manifest['program']['sha256'][:12]} "
          f"cpio sha256={manifest['cpio']['sha256'][:12]} "
          f"EAGAIN={manifest['eagain']}")
    return manifest


def firmware() -> str:
    k0.load_contract()
    if not k0.ABI:
        raise SetupError("the boot contract is empty — cannot build the bootrom")
    scratch = image_root() / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(scratch / "bootrom"), name="bootrom_m18p.bin")


def boot(tag: str) -> tuple[int, str]:
    vmlinux = linux_paths.linux_build_dir() / "vmlinux"
    if not vmlinux.is_file():
        raise SetupError(f"{vmlinux} missing — the kernel build did not produce it")
    qemu = linux_paths.toolchain_bin() / "qemu-system-dadao"
    if not os.access(qemu, os.X_OK):
        raise SetupError(f"{qemu} missing — run 'make install-host'")
    cmd = [str(qemu), "-machine", f"kaiwu-vast,bootrom-image={firmware()}",
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


def expected_lines(eagain: int) -> list[str]:
    lines = ["PTHREAD begin n=4", "PTHREAD main-tls=0"]
    for idx in range(NTHREADS):
        lines.append(f"PTHREAD worker idx={idx} detach=0 self-eq=1 "
                     f"main-diff=1 tls={idx * 10 + 1} tls2={idx * 10 + 1}")
    lines.append(f"PTHREAD worker idx={NTHREADS} detach=1 self-eq=1 "
                 f"main-diff=1 tls={NTHREADS * 10 + 1} "
                 f"tls2={NTHREADS * 10 + 1}")
    for idx in range(NTHREADS):
        lines.append(f"PTHREAD join idx={idx} self-same=1 rc=0 "
                     f"ret=0x{0x100 + idx:x}")
    lines += ["PTHREAD detach rc=0",
              f"PTHREAD neg-eagain rc={eagain}",
              "PTHREAD end fails=0"]
    return lines


def judge(tag: str, rc: int, text: str, eagain: int) -> list[tuple[str, str, str, bool]]:
    checks: list[tuple[str, str, str, bool]] = []
    checks.append((f"{tag}: kernel ran /init as init", "present",
                   "present" if "Run /init as init process" in text else "absent",
                   "Run /init as init process" in text))
    checks.append((f"{tag}: PID 1 exit status is the program status", "0", str(rc),
                   rc == 0))
    for line in expected_lines(eagain):
        count = sum(1 for row in text.splitlines() if row.strip() == line)
        checks.append((f"{tag}: exact line {line!r}", 1, count, count == 1))
    bad = [line.strip() for line in text.splitlines()
           if re.search(r"(panic|Kernel panic|Attempted to kill init|"
                        r"BUG:|Oops|Segmentation fault|Illegal instruction|"
                        r"PTHREAD create-fail|PTHREAD barrier-init fail|"
                        r"PTHREAD end fails=[1-9])", line)]
    checks.append((f"{tag}: no failure text", [], bad, not bad))
    counts = len(re.findall(r"^PTHREAD worker idx=[0-3] ", text, re.M))
    checks.append((f"{tag}: {NTHREADS} worker lines present", NTHREADS, counts,
                   counts == NTHREADS))
    return checks


def report(checks: list[tuple[str, str, str, bool]]) -> int:
    failed = 0
    for name, expected, actual, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} | 期望={expected} 实际={actual}")
        failed += 0 if ok else 1
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--boots", type=int, default=1,
                        help="consecutive boots of the same image (default 1)")
    parser.add_argument("--no-boot", action="store_true",
                        help="build the image and assert the ELF, do not boot")
    parser.add_argument("--tag", default="run",
                        help="log-name prefix (one log per boot: <tag>-<n>.log)")
    args = parser.parse_args()

    try:
        manifest = build_image()
        if args.no_boot:
            print("m18_pthread_probe: PASS (image built; boots skipped)")
            return 0
        fails = 0
        for index in range(args.boots):
            tag = f"{args.tag}-{index + 1}"
            rc, text = boot(tag)
            checks = judge(tag, rc, text, manifest["eagain"])
            bad = report(checks)
            print(f"[INFO] {tag}: qemu rc={rc}; "
                  f"{len(checks) - bad}/{len(checks)} checks passed; "
                  f"log {image_root() / 'log' / (tag + '.log')}")
            fails += bad
        if fails:
            print(f"m18_pthread_probe: FAIL ({fails} check(s) across "
                  f"{args.boots} boot(s))")
            return 1
        print(f"m18_pthread_probe: PASS ({args.boots}/{args.boots} boots)")
        return 0
    except SetupError as exc:
        print(f"m18_pthread_probe: SETUP ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
