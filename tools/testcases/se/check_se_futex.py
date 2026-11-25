#!/usr/bin/env python3
"""Cross-engine futex details probe (ISS-345 / m20-gem5-002).

``futex_probe.c`` asserts the futex(2) behaviour fixed by m20-gem5-002:
non-owner ``FUTEX_UNLOCK_PI`` is ``EPERM``, ``FUTEX_REQUEUE`` /
``FUTEX_CMP_REQUEUE`` return the woken+requeued count and reject negative
counts with ``EINVAL``, and the wait timeout/invalid-timespec branches still
return ``ETIMEDOUT``/``EINVAL``.  This driver builds the probe, runs it on:

    host     cc + the host kernel -- the oracle (this really is Linux)
    gem5-se  gem5 SE
    qemu     qemu-user

and requires every engine to reproduce the *host*'s assertion lines and to end
with ``SUMMARY ... fails=0``.

The waiter leak is a host-side allocation inside the simulator and cannot be
seen from the guest.  The driver therefore measures the simulator's peak RSS
(``wait4`` rusage) for ``leak N`` (invalid/expired waits) and ``wake N`` (the
same number of syscalls that never allocate a waiter): a leaking early-return
branch makes the leak run's peak grow by the waiter size times N; a fixed one
stays within page-granular noise of the wake run.

Exit status: 0 only when every check passes; 2 on a setup error.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
sys.path.insert(0, str(REPO_ROOT / "tools" / "infra"))
import paths as _paths  # noqa: E402

PROBE = Path(__file__).resolve().parent / "futex_probe.c"

DEFAULT_WORK_DIR = str(_paths.test_artifacts_dir() / "se-futex")
DEFAULT_MUSL = ".work/source/musl"
DEFAULT_GEM5 = ".work/source/gem5/build/DADAO/gem5.opt"
DEFAULT_SE = ".work/source/gem5/configs/dadao/se.py"
DEFAULT_CLANG = ".dadao/cross-toolchain/bin/clang"
DEFAULT_LDL = ".dadao/cross-toolchain/bin/ld.lld"
DEFAULT_QEMU = ".dadao/cross-toolchain/bin/qemu-dadao"
BUILTINS = (
    ".dadao/cross-toolchain/lib/clang/23/lib/"
    "dadao-unknown-unknown-elf/libclang_rt.builtins.a",
    ".dadao/cross-toolchain/lib/clang/23/lib/"
    "dadao-unknown-unknown-linux/libclang_rt.builtins.a",
)

ASSERTION_RE = re.compile(r"^(PASS|FAIL) (\S+) ")
SUMMARY_RE = re.compile(r"^SUMMARY checks=(-?\d+) fails=(-?\d+)$", re.MULTILINE)
CALL_RE = re.compile(r'^\s+check\("', re.MULTILINE)

failures = 0
checks = 0
floor = 0


class SetupError(RuntimeError):
    pass


def check(name: str, expected, actual) -> None:
    global failures, checks
    checks += 1
    ok = expected == actual
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: "
          f"expected={expected} actual={actual}")
    if not ok:
        failures += 1


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def run(cmd: list[str], cwd: Path | None, out: Path, err: Path,
        timeout: int) -> int:
    """Run cmd; return its own exit code (None on timeout -> -1)."""
    with out.open("wb") as stdout, err.open("wb") as stderr:
        try:
            proc = subprocess.run(cmd, cwd=cwd, stdout=stdout, stderr=stderr,
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            return -1
    return proc.returncode


def run_rusage(cmd: list[str], cwd: Path, out: Path, err: Path,
               timeout: int) -> tuple[int, int, bool]:
    """Run cmd, returning (exit code, peak RSS in KiB, timed out).

    ``subprocess`` hides the child rusage; ``os.wait4`` reports the peak RSS of
    exactly this child, which is what the leak check needs.
    """
    pid = os.fork()
    if pid == 0:  # child
        try:
            os.chdir(cwd)
            fd_out = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            fd_err = os.open(err, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            fd_in = os.open(os.devnull, os.O_RDONLY)
            os.dup2(fd_in, 0)
            os.dup2(fd_out, 1)
            os.dup2(fd_err, 2)
            os.execv(cmd[0], cmd)
        except OSError:
            pass
        os._exit(127)

    deadline = time.time() + timeout
    timed_out = False
    while True:
        wpid, status, rusage = os.wait4(pid, os.WNOHANG)
        if wpid == pid:
            break
        if time.time() > deadline:
            timed_out = True
            os.kill(pid, 9)
            wpid, status, rusage = os.wait4(pid, 0)
            break
        time.sleep(0.02)
    rc = os.waitstatus_to_exitcode(status) if not timed_out else -1
    return rc, int(rusage.ru_maxrss), timed_out


def shared(out: Path) -> list[str]:
    """The assertion lines of one run, in order."""
    if not out.exists():
        return []
    lines = []
    for line in out.read_text(errors="replace").splitlines():
        if ASSERTION_RE.match(line):
            lines.append(line)
    return lines


def evaluate(engine: str, rc: int, out: Path,
             ref: list[str] | None = None) -> None:
    check(f"{engine}-rc", 0, rc)
    text = out.read_text(errors="replace") if out.exists() else ""
    summary = SUMMARY_RE.search(text)
    check(f"{engine}-summary-present", True, summary is not None)
    check(f"{engine}-summary-fails", 0,
          int(summary.group(2)) if summary else -1)
    check(f"{engine}-no-fail", 0,
          sum(1 for line in text.splitlines() if line.startswith("FAIL ")))
    lines = shared(out)
    if ref is None:
        check(f"{engine}-shared-count-floor", True, len(lines) >= floor)
        return
    check(f"{engine}-shared-count", len(ref), len(lines))
    diff = [(want, got) for want, got in zip(ref, lines) if want != got]
    check(f"{engine}-agrees-with-host", 0, len(diff))
    for want, got in diff[:8]:
        print(f"       host:      {want}")
        print(f"       {engine}: {got}")


def gem5_cmd(args, gem5: Path, se: Path, guest_elf: Path, work: Path,
             tag: str, guest_args: list[str]) -> list[str]:
    return [
        str(gem5), "--outdir", str(work / f"m5-{tag}"), str(se),
        "--binary", str(guest_elf),
        "--guest-stdout", str(work / f"gem5-{tag}.out"),
        "--guest-stderr", str(work / f"gem5-{tag}.err"),
        "--guest-stdin", "/dev/null",
        "--args", " ".join(guest_args),
    ]


def main() -> int:
    global floor

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR,
                    help="runtime directory for binaries and logs")
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldl", default=DEFAULT_LDL)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--gem5", default=DEFAULT_GEM5)
    ap.add_argument("--gem5-config", default=DEFAULT_SE)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--leak-n", type=int, default=200000,
                    help="iterations for the leak/wake RSS comparison")
    ap.add_argument("--leak-rss-limit", type=int, default=4 * 1024,
                    help="max extra host peak RSS (KiB) of the leak run")
    ap.add_argument("--skip-leak", action="store_true")
    args = ap.parse_args()

    work = resolve(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    floor = len(CALL_RE.findall(PROBE.read_text(errors="replace")))
    musl = resolve(args.musl)
    clang = resolve(args.clang)
    ldl = resolve(args.ldl)
    qemu = resolve(args.qemu)
    gem5 = resolve(args.gem5)
    se = resolve(args.gem5_config)
    builtins = next((resolve(p) for p in BUILTINS if resolve(p).is_file()),
                    None)
    for path, what in ((clang, "clang"), (ldl, "ld.lld"), (qemu, "qemu-dadao"),
                       (gem5, "gem5.opt"), (se, "se.py"),
                       (musl / "lib/libc.a", "libc.a")):
        if not path.is_file():
            raise SetupError(f"{what} not found: {path}")

    host_elf = work / "probe-host"
    rc = run(["cc", "-std=c99", "-D_GNU_SOURCE", "-O1", "-Wall", "-pthread",
              str(PROBE), "-o", str(host_elf)], None, work / "cc-host.out",
             work / "cc-host.err", args.timeout)
    check("host-compile", 0, rc)
    obj = work / "probe.o"
    rc = run([str(clang), "-target", "dadao-unknown-elf", "-nostdinc",
              "-I", str(musl / "arch/dadao"),
              "-I", str(musl / "arch/generic"),
              "-I", str(musl / "obj/include"),
              "-I", str(musl / "include"),
              "-std=c99", "-D_GNU_SOURCE", "-O1", "-Wall", "-c",
              str(PROBE), "-o", str(obj)], None, work / "cc-guest.out",
             work / "cc-guest.err", args.timeout)
    check("guest-compile", 0, rc)
    guest_elf = work / "probe.elf"
    rc = run([str(ldl), "-o", str(guest_elf), str(musl / "lib/crt1.o"),
              str(obj), "--start-group", str(musl / "lib/libc.a"),
              str(builtins), "--end-group"], None, work / "ld.out",
             work / "ld.err", args.timeout)
    check("guest-link", 0, rc)
    if failures:
        print("\nsetup failed before running engines")
        return 2

    # The host is the oracle: run it first and use its lines as the reference.
    host_out = work / "host.out"
    rc = run([str(host_elf)], work, host_out, work / "host.err", args.timeout)
    ref = shared(host_out)
    evaluate("host", rc, host_out)
    if not ref:
        raise SetupError("the host run produced no assertion lines")

    engine_runs = {
        "gem5-se": (
            gem5_cmd(args, gem5, se, guest_elf, work, "plain", ["check"]),
            work, work / "gem5-plain.out",
            work / "gem5-plain.sim.out", work / "gem5-plain.sim.err"),
        "qemu": (
            [str(qemu), "-R", "4G", str(guest_elf), "check"],
            work, work / "qemu.out", work / "qemu.out", work / "qemu.err"),
    }
    for engine, (cmd, cwd, out, sim_out, sim_err) in engine_runs.items():
        rc = run(cmd, cwd, sim_out, sim_err, args.timeout)
        evaluate(engine, rc, out, ref)

    if not args.skip_leak:
        # Peak RSS of `leak N` vs `wake N`: the same syscall volume, but only
        # the wait loop reaches the early-return branches.  A leaked waiter
        # per call shows up as ~waiter-size x N of extra peak; the fixed code
        # stays within page-granular noise of the control run.
        n = args.leak_n
        rss = {}
        for mode in ("leak", "wake"):
            tag = f"{mode}-{n}"
            out = work / f"gem5-{tag}.out"
            cmd = gem5_cmd(args, gem5, se, guest_elf, work, tag,
                           [mode, str(n)])
            rc, peak, timed_out = run_rusage(
                cmd, work, work / f"gem5-{tag}.sim.out",
                work / f"gem5-{tag}.sim.err", args.timeout)
            check(f"gem5-{tag}-rc", 0, rc)
            check(f"gem5-{tag}-completed", False, timed_out)
            text = out.read_text(errors="replace") if out.exists() else ""
            m = SUMMARY_RE.search(text)
            check(f"gem5-{tag}-summary-fails", 0,
                  int(m.group(2)) if m else -1)
            rss[mode] = peak
        delta = rss["leak"] - rss["wake"]
        print(f"[INFO] gem5 peak RSS: leak {n}={rss['leak']} KiB, "
              f"wake {n}={rss['wake']} KiB, delta={delta} KiB "
              f"({delta * 1024 / n:.2f} B/iteration)")
        check("gem5-waiter-leak-peak-delta", True, delta < args.leak_rss_limit)

    print(f"\n{checks - failures}/{checks} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SetupError as exc:
        print(f"setup error: {exc}", file=sys.stderr)
        sys.exit(2)
