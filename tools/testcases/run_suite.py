#!/usr/bin/env python3
"""Reference-suite runner for DADAO-v5: ``libc-test`` + ``llvm-test-suite``
(TESTCASES-045t stage 1).

WITHDRAWN (2026-10-15; user ruling "1、删", executed by ``QEMU-060t``)
--------------------------------------------------------------------
The ``dadao-m1`` syscall service (``SYS_UMON_SYSCALL``) that this runner drove
has been withdrawn: in user mode ``trap cfx0, 0`` goes down the generic cfx
vector again (``dadao-m1`` is semihosting-only, ``Machine-01 §4.3`` /
``ADR-0020 D10``) and the musl syscall stubs have no backend left.  The
``-M dadao-m1`` path B below is therefore *not runnable*, and ``main()``
refuses to run (exit 2) instead of reporting every case as a failure.  Running
verification is now ``P3`` (``qemu-user``).  This file is kept as the record of
the stage-1 methodology and of the withdrawn path; it is **not** rewritten into
a ``qemu-user`` harness (that is ``P3``).

What it does
------------
For every selected case (one ``.c`` translation unit that carries ``main``) it
runs the project's *static* musl flow and reports the case's own verdict:

  compile ``clang --target=dadao-unknown-elf -nostdinc <musl includes> -c``
  link    ``ld.lld -T tests/scripts/dadao.lds crt1.o <obj> [libtest] libc.a``
  image   ``llvm-objcopy -O binary`` (flat ``-kernel`` image, "path B")
  run     ``qemu-system-dadao -M dadao-m1 -bios bootrom.bin -kernel <flat>``

Path B (``-bios`` + flat ``-kernel``) is mandatory: with ``-kernel <ELF>`` the
reset run mode is ``hypv`` and the user-mode ``umon`` syscall is never reached
(``contract-syscall §6``; INFRA-082t stage A1).

Why a self-built runner (and not the upstream harnesses)
--------------------------------------------------------
* ``libc-test`` upstream ships ``src/common/runtest.exe``, which needs
  ``fork``/``waitpid``/``signal``/``setrlimit`` -- impossible in the kernel-less
  ``P1`` model (``ADR-0025 D2``).
* ``llvm-test-suite`` upstream is driven by CMake + lit, which also assumes a
  hosted OS (and a second, non-QEMU backend).
So both suites are driven here directly, from their own sources, unchanged
(both lock entries are ``patchless``: this runner never writes into
``.work/source/**``).

Independent oracle (``AGENTS.md`` "Independent oracle")
-------------------------------------------------------
Expectations come from the *case*, never from DADAO/QEMU/LLVM:

* ``libc-test``: ``main`` returns ``t_status``, which is 0 iff no ``t_error``
  was raised (``src/common/print.c``) -- the suite's own verdict.
* ``llvm-test-suite``: where upstream ships a reference output the stdout + exit
  status are compared against it verbatim.  The variant order is
  ``.reference_output.small`` (the ``SMALL_PROBLEM_SIZE`` build) >
  ``.reference_output.big-endian`` (this machine is big-endian, ``ADR-0003 D1``)
  > ``.reference_output`` (see ``reference_for``).  Where upstream ships no
  reference, the only achievable stage-1 verdict is "ran to completion with
  exit 0"; the stdout sha256 is recorded so stage 3 can pin a reference.  This
  is stated in the report -- a ``pass`` there is *not* an output equivalence
  verdict.

Classification (counted live, never hard-coded)
-----------------------------------------------
* ``pass``          built + ran, the oracle matched.
* ``fail``          built + ran, the oracle did NOT match, no ENOSYS was logged.
* ``enosys``        built + ran, the oracle did NOT match, and QEMU logged one
                    or more ``umon syscall N not implemented (-ENOSYS)`` lines
                    -- the missing backend service is the root cause.  The
                    syscall numbers are recorded (stage 2 input).
* ``compile-error`` clang/ld.lld/llvm-objcopy failed.
* ``timeout``       QEMU exceeded ``--timeout``.
* ``unsupported``   declared out of scope up front, with a reason (never
                    attempted, never a silent skip).  The count is derived at
                    run time by globbing the suite tree.

An ENOSYS line alone never downgrades a case: a program may legitimately log
one (e.g. musl's stdout probe ``ioctl``) and still pass; classification is by
the case's own verdict.

Run path: ENOSYS lines are the QEMU ``qemu_log_mask(LOG_GUEST_ERROR, ...)``
messages, so ``-d guest_errors`` is passed and QEMU's stderr is parsed.

Exit status: 0 = no ``fail`` and no ``timeout``; 1 = otherwise; 2 = setup error.
``--strict`` additionally fails on ``enosys``/``compile-error``.
``--inject`` corrupts the expectations so every comparison must FAIL: it is the
reachable-FAIL path of this harness (and it disables the ENOSYS re-attribution,
because the comparison itself is what is under test).

Usage
-----
  run_suite.py                          # both suites, stage-1 subset
  run_suite.py --suite libc-test        # one suite
  run_suite.py --list                   # list the selected case ids
  run_suite.py --stage full             # every enumerable C case (stage 3)
  run_suite.py --only <case-id> ...     # a subset of the selection
  run_suite.py --json-out <path>        # full per-case records
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra"))
import paths  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
TEST_ARTIFACTS = paths.test_artifacts_dir()

MUSL_SRC = REPO_ROOT / ".work" / "source" / "musl"
LIBC_TEST = REPO_ROOT / ".work" / "source" / "libc-test"
LLVM_TS = REPO_ROOT / ".work" / "source" / "llvm-test-suite"
LDS = REPO_ROOT / "tests" / "scripts" / "dadao.lds"
DEFAULT_BOOTROM = TEST_ARTIFACTS / "bootrom" / "bootrom.bin"

TARGET = "dadao-unknown-elf"
DEFAULT_TIMEOUT = 30

# musl port include dirs (the same set tools/infra/build_musl.py uses).
MUSL_INCLUDE_DIRS = ("arch/dadao", "arch/generic", "obj/src/internal",
                     "src/include", "src/internal", "obj/include", "include")

# libc-test's own compile flags (config.mak.def), minus the glibc-only entries
# and the -Werror= family (a warning must not be conflated with a build error).
LIBC_TEST_CFLAGS = ("-std=c99", "-D_POSIX_C_SOURCE=200809L",
                    "-fno-builtin", "-frounding-math")

# libc-test's test harness support objects, linked into every libc-test case
# (src/common/runtest.c is excluded: it carries its own main()).
LIBC_TEST_COMMON = ("fdfill.c", "memfill.c", "path.c", "print.c", "rand.c",
                    "setrlim.c", "utf8.c", "vmfill.c")

ENOSYS_RE = re.compile(r"umon syscall (\d+) not implemented \(-ENOSYS\)")
REFERENCE_EXIT_RE = re.compile(r"^exit (\d+)$")
# A standalone test TU is one that carries a `main` definition.  Upstream writes
# it both ways (`int main()` and `int\nmain()`), so the declaration test allows
# arbitrary whitespace between the return type and the name.
MAIN_RE = re.compile(r"\b(?:int|void)\s+main\s*\(")

SRC_SUFFIXES = (".c", ".cc", ".cpp", ".cxx", ".C", ".m", ".mm",
                ".f", ".f77", ".f90", ".F", ".F90")

# ---------------------------------------------------------------------------
# Stage-1 selection: a small subset stratified from "simplest dependency
# signature" to "hardest", one tier per group.  Each entry records *why* it was
# picked; the tier is the selection criterion (not the expected outcome).
#   tier 1 -- pure computation: no libc service beyond write/exit
#   tier 2 -- stdio / floating point formatting (libc-internal, no heap)
#   tier 3 -- heap allocation (brk/mmap)
#   tier 4 -- time
#   tier 5 -- filesystem
# ---------------------------------------------------------------------------
LIBC_TEST_CASES = (
    ("src/functional/basename.c",
     "tier1 pure-compute: libgen, no syscall beyond write/exit", ()),
    ("src/functional/dirname.c",
     "tier1 pure-compute: libgen, no syscall beyond write/exit", ()),
    ("src/functional/udiv.c",
     "tier1 pure-compute: 64-bit div/mod", ()),
    ("src/functional/string_strchr.c",
     "tier1 pure-compute: string search", ()),
    ("src/functional/snprintf.c",
     "tier2 stdio formatting (libc-internal, no heap)", ()),
    ("src/functional/strtod_simple.c",
     "tier2 stdio + FP: strtod/snprintf/libm sin()", ()),
    ("src/regression/malloc-0.c",
     "tier3 heap: malloc(0) uniqueness -> brk/mmap", ()),
    ("src/functional/time.c",
     "tier4 time: clock_gettime/localtime", ()),
    ("src/functional/stat.c",
     "tier5 filesystem: stat/time", ()),
)

# Upstream builds SingleSource/Regression/C/gcc-c-torture/execute with these
# warnings off (execute/CMakeLists.txt: "-Wno-implicit-int -Wno-int-conversion
# -Wno-implicit-function-declaration -w"): the suite is "conventionally run
# without warnings" and its sources call abort()/exit() undeclared.  Using the
# upstream flags keeps the corpus unchanged; without them clang >= 16 rejects
# the file, which would be a toolchain-version artifact, not a DADAO result.
GCC_TORTURE_CFLAGS = ("-Wno-implicit-int", "-Wno-int-conversion",
                      "-Wno-implicit-function-declaration")

# Upstream's own small-problem-size knob (cmake/modules/TestSuite.cmake:49-50
# adds -DSMALL_PROBLEM_SIZE when the SMALL_PROBLEM_SIZE option is on, which is
# how the suite is run for verification rather than for scoring).  Benchmarks
# are built with it so a sweep stays inside a sane wall-clock budget; it changes
# the workload size only, never the program's own verdict.
#
# The *fast* stage additionally keeps out the Shootout members whose SMALL
# problem size still runs for tens of seconds on dadao-m1 (measured 2026-10-15:
# fib2 LENGTH=40 ~48 s, nestedloop/sieve ~32 s): they stay reachable through
# `--stage full` with a larger `--timeout`, so nothing is silently skipped.
BENCHMARK_TREES = ("SingleSource/Benchmarks/", "MultiSource/Benchmarks/",
                   "MultiSource/Applications/", "MicroBenchmarks/")
SMALL_PROBLEM_CFLAGS = ("-DSMALL_PROBLEM_SIZE",)

LLVM_TS_CASES = (
    ("SingleSource/Regression/C/gcc-c-torture/execute/991030-1.c",
     "tier1 pure-compute: hex-float literal; oracle = abort() on mismatch",
     GCC_TORTURE_CFLAGS),
    ("SingleSource/Regression/C/gcc-c-torture/execute/20000519-2.c",
     "tier1 pure-compute: long compare; oracle = abort() on mismatch",
     GCC_TORTURE_CFLAGS),
    ("SingleSource/Regression/C/gcc-c-torture/execute/20001112-1.c",
     "tier1 pure-compute: long long arith; oracle = abort() on mismatch",
     GCC_TORTURE_CFLAGS),
    ("SingleSource/UnitTests/2002-04-17-PrintfChar.c",
     "tier2 stdio; oracle = upstream .reference_output", ()),
    ("SingleSource/UnitTests/2003-05-12-MinIntProblem.c",
     "tier2 stdio; oracle = upstream .reference_output", ()),
    ("SingleSource/UnitTests/2003-05-31-LongShifts.c",
     "tier2 stdio shifts; oracle = upstream .reference_output", ()),
    ("SingleSource/Benchmarks/Shootout/hello.c",
     "tier3 minimal benchmark: puts", SMALL_PROBLEM_CFLAGS),
    ("SingleSource/Benchmarks/Shootout/ackermann.c",
     "tier3 minimal benchmark: recursion + printf", SMALL_PROBLEM_CFLAGS),
    ("SingleSource/Benchmarks/Shootout/random.c",
     "tier3 minimal benchmark: FP + printf (the Shootout members whose default "
     "problem size exceeds the fast-stage budget -- fib2/nestedloop/sieve -- "
     "are left to `--stage full`; see the stage-1 report)", SMALL_PROBLEM_CFLAGS),
)

# Declared out-of-scope categories (glob relative to the suite root, reason).
# Counts are derived live by globbing; nothing is skipped silently.
EXCLUSIONS = {
    "libc-test": (
        ("**/*dlopen*.c",
         "dynamic linking (dlopen / shared object): P2 not implemented "
         "(ADR-0025 D6)"),
        ("src/functional/tls_*.c",
         "static __thread/TLS unavailable: libc.tls_cnt == 0 without "
         "AT_PHDR/PHNUM (INFRA-082t stage A2+A3 legacy 4)"),
        ("src/functional/pthread_*.c",
         "multi-thread semantics: no kernel (ADR-0025 D2)"),
        ("src/functional/vfork.c",
         "process creation: no kernel (ADR-0025 D2)"),
        ("src/functional/spawn.c",
         "process creation: no kernel (ADR-0025 D2)"),
        ("src/functional/ipc_*.c",
         "SysV IPC: no kernel (ADR-0025 D2)"),
        ("src/functional/sem_*.c",
         "POSIX semaphores need threads: no kernel (ADR-0025 D2)"),
        ("src/functional/socket.c",
         "sockets: no network stack in the bare-metal model"),
        ("src/api/pthread.c", "multi-thread semantics: no kernel (ADR-0025 D2)"),
        ("src/api/signal.c", "signals: no kernel (ADR-0025 D2)"),
        ("src/api/aio.c", "async I/O needs threads: no kernel (ADR-0025 D2)"),
        ("src/api/sys_socket.c", "sockets: no network stack"),
        ("src/api/sys_ipc.c", "SysV IPC: no kernel (ADR-0025 D2)"),
        ("src/api/sys_shm.c", "SysV shared memory: no kernel (ADR-0025 D2)"),
        ("src/api/sys_msg.c", "SysV message queues: no kernel (ADR-0025 D2)"),
        ("src/api/sys_sem.c", "SysV semaphores: no kernel (ADR-0025 D2)"),
        ("src/api/sys_wait.c", "process waiting: no kernel (ADR-0025 D2)"),
        ("src/api/sys_select.c", "select/poll over fds: no kernel (ADR-0025 D2)"),
        ("src/api/poll.c", "poll over fds: no kernel (ADR-0025 D2)"),
        ("src/api/mqueue.c", "POSIX mqueues: no kernel (ADR-0025 D2)"),
    ),
    "llvm-test-suite": (
        ("External/**/*",
         "upstream External/ (incl. SPEC CFP2006/CFP2017): excluded by the "
         "user's scope decision for this task (2026-10-15)"),
    ),
}

# Non-C translation units: no frontend/runtime is available for a static,
# bare-metal target.  Counted live per suffix (only suffixes actually present
# are reported, so no category can silently match nothing).
NON_C_REASON = {
    ".cc": "C++: no C++ standard library in the static-only sysroot",
    ".cpp": "C++: no C++ standard library in the static-only sysroot",
    ".cxx": "C++: no C++ standard library in the static-only sysroot",
    ".C": "C++: no C++ standard library in the static-only sysroot",
    ".m": "Objective-C: no ObjC runtime/foundation",
    ".mm": "Objective-C++: no ObjC runtime/foundation",
    ".f": "Fortran: no Fortran frontend",
    ".f77": "Fortran: no Fortran frontend",
    ".f90": "Fortran: no Fortran frontend",
    ".F": "Fortran: no Fortran frontend",
    ".F90": "Fortran: no Fortran frontend",
}

SUITE_ROOTS = {"libc-test": LIBC_TEST, "llvm-test-suite": LLVM_TS}
SUITE_CASES = {"libc-test": LIBC_TEST_CASES, "llvm-test-suite": LLVM_TS_CASES}
# Trees scanned by ``--stage full``, by the whole-suite `unsupported` census of
# both stages, and by the non-C suffix census.
SUITE_SCAN_GLOBS = {
    "libc-test": ("src/**/*",),
    "llvm-test-suite": ("SingleSource/**/*", "MultiSource/**/*",
                        "MicroBenchmarks/**/*"),
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def run(cmd, *, cwd=None, env=None, timeout=None):
    return subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=timeout)


def toolchain_env():
    env = dict(os.environ)
    env["PATH"] = f"{TOOLCHAIN_BIN}:{env.get('PATH', '')}"
    return env


def musl_include_flags():
    return [f"-I{MUSL_SRC / d}" for d in MUSL_INCLUDE_DIRS]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reference_for(case_abs: Path, small_problem: bool = False):
    """Upstream reference output for an llvm-test-suite case, if any.

    Precedence, most specific first.  The variant names that actually occur in
    the locked corpus are ``.reference_output`` (1157), ``.reference_output.small``
    (93), ``.reference_output.big-endian`` (17), ``.reference_output.little-endian``
    (8) and ``.reference_output.AIX`` (5) -- and no case carries both a ``.small``
    and a ``.big-endian`` variant, so this order is unambiguous:

      1. ``.reference_output.small``    -- the ``SMALL_PROBLEM_SIZE`` build
         (upstream's own small-size reference, the same knob as the compile flag)
      2. ``.reference_output.big-endian`` -- this machine is big-endian
         (ADR-0003 D1)
      3. ``.reference_output``          -- the default reference

    The ``.little-endian`` / ``.AIX`` variants target other hosts and are
    deliberately not consulted on this big-endian machine.

    Returns (stdout_bytes, exit_code, used_path) or None."""
    base = case_abs.with_suffix("")
    suffixes = []
    if small_problem:
        suffixes.append(".reference_output.small")
    suffixes += [".reference_output.big-endian", ".reference_output"]
    for suffix in suffixes:
        ref = Path(f"{base}{suffix}")
        if not ref.is_file():
            continue
        text = ref.read_text(errors="replace")
        lines = text.split("\n")
        while lines and lines[-1] == "":
            lines.pop()
        if not lines:
            raise RuntimeError(f"empty reference file: {ref}")
        m = REFERENCE_EXIT_RE.match(lines[-1])
        if not m:
            raise RuntimeError(f"reference file has no trailing 'exit N': {ref}")
        stdout = "".join(f"{ln}\n" for ln in lines[:-1]).encode()
        return stdout, int(m.group(1)), str(ref.relative_to(REPO_ROOT))
    return None


def build_common_objects(work: Path, log) -> list[Path]:
    """Compile libc-test's src/common support objects (excluding runtest.c)."""
    objs = []
    for name in LIBC_TEST_COMMON:
        src = LIBC_TEST / "src" / "common" / name
        obj = work / f"common-{name}.o"
        cmd = ([str(TOOLCHAIN_BIN / "clang"), f"--target={TARGET}", "-O1",
                "-nostdinc", *musl_include_flags(),
                f"-I{LIBC_TEST / 'src' / 'common'}",
                *LIBC_TEST_CFLAGS, "-c", str(src), "-o", str(obj)])
        res = run(cmd, cwd=REPO_ROOT, env=toolchain_env())
        log.append({"cmd": " ".join(cmd), "rc": res.returncode})
        if res.returncode != 0:
            raise RuntimeError(f"common object {name} failed rc="
                               f"{res.returncode}\n{res.stdout}")
        objs.append(obj)
    return objs


def build_case(suite: str, case_abs: Path, work: Path, log, common_objs,
               cflags=()):
    """compile -> link -> flat image.  Returns (flat_path, None) or (None, err)."""
    stem = f"{suite}-{case_abs.relative_to(SUITE_ROOTS[suite])}".replace("/", "_")
    obj = work / f"{stem}.o"
    elf = work / f"{stem}.elf"
    flat = work / f"{stem}.bin"

    cmd = [str(TOOLCHAIN_BIN / "clang"), f"--target={TARGET}", "-O1",
           "-nostdinc", *musl_include_flags()]
    if suite == "libc-test":
        cmd += [f"-I{LIBC_TEST / 'src' / 'common'}", *LIBC_TEST_CFLAGS]
    cmd += [*cflags, "-c", str(case_abs), "-o", str(obj)]
    res = run(cmd, cwd=REPO_ROOT, env=toolchain_env())
    log.append({"stage": "compile", "cmd": " ".join(cmd), "rc": res.returncode,
                "stderr": res.stdout[-2000:]})
    if res.returncode != 0:
        return None, f"compile rc={res.returncode}: {res.stdout.strip().splitlines()[-1:]}"

    objs = [str(MUSL_SRC / "lib" / "crt1.o"), str(obj)]
    if common_objs:
        # `--start-lib … --end-lib` gives the support objects *archive* semantics
        # (only the members whose symbols are needed get pulled in), exactly like
        # upstream's `LDLIBS = libtest.a`.  Force-including them all would drag in
        # unused members and their whole dependency closure.
        objs += ["--start-lib", *[str(o) for o in common_objs], "--end-lib"]
    cmd = ([str(TOOLCHAIN_BIN / "ld.lld"), "-T", str(LDS), *objs,
            str(MUSL_SRC / "lib" / "libc.a"), "-o", str(elf)])
    res = run(cmd, cwd=REPO_ROOT)
    log.append({"stage": "link", "cmd": " ".join(cmd), "rc": res.returncode,
                "stderr": res.stdout[-2000:]})
    if res.returncode != 0:
        return None, f"link rc={res.returncode}: {res.stdout.strip().splitlines()}"

    cmd = [str(TOOLCHAIN_BIN / "llvm-objcopy"), "-O", "binary", str(elf), str(flat)]
    res = run(cmd, cwd=REPO_ROOT)
    log.append({"stage": "objcopy", "cmd": " ".join(cmd), "rc": res.returncode,
                "stderr": res.stdout[-2000:]})
    if res.returncode != 0:
        return None, f"objcopy rc={res.returncode}"
    return flat, None


def run_guest(qemu: str, bootrom: Path, flat: Path, timeout: int,
              out_file: Path, err_file: Path) -> dict:
    """Run the flat image on dadao-m1 through the bootrom (path B).

    The guest's stdout/stderr are redirected to *files* rather than pipes: the
    bytes stay on disk as the failure scene, and a timeout still leaves the
    partial output behind instead of discarding it with the pipe."""
    cmd = [qemu, "-M", "dadao-m1", "-nographic", "-monitor", "none",
           "-bios", str(bootrom), "-kernel", str(flat), "-d", "guest_errors"]
    timed_out = False
    with open(out_file, "wb") as fo, open(err_file, "wb") as fe:
        try:
            res = subprocess.run(cmd, stdout=fo, stderr=fe, timeout=timeout)
            rc = res.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            rc = None
    return {"timeout": timed_out, "cmd": " ".join(cmd),
            "exit": None if rc is None else rc & 0xFF,
            "stdout": out_file.read_bytes(),
            "stderr": err_file.read_bytes().decode(errors="replace")}


def excluded_files(suite: str):
    """{abs_path: reason} for every source file matched by the exclusion globs."""
    root = SUITE_ROOTS[suite]
    found: dict[Path, str] = {}
    for pattern, reason in EXCLUSIONS[suite]:
        for p in root.glob(pattern):
            if p.is_file() and p.suffix in SRC_SUFFIXES:
                found.setdefault(p, reason)
    return found


def scan_candidates(suite: str) -> dict[Path, None]:
    root = SUITE_ROOTS[suite]
    out: dict[Path, None] = {}
    for pattern in SUITE_SCAN_GLOBS[suite]:
        for p in root.glob(pattern):
            if p.is_file() and p.suffix in SRC_SUFFIXES:
                out.setdefault(p, None)
    return out


def exclusion_counts(suite: str) -> dict[str, int]:
    """Live per-category counts; a category matching nothing is reported.

    Scope note: the declared-glob categories are counted from the suite root
    (so a suite-level entry such as ``External/`` is included), while the
    mechanical non-C suffix census covers the scan face only -- the two tables
    are labelled accordingly in the report."""
    root = SUITE_ROOTS[suite]
    out: dict[str, int] = {}
    for pattern, reason in EXCLUSIONS[suite]:
        n = sum(1 for p in root.glob(pattern)
                if p.is_file() and p.suffix in SRC_SUFFIXES)
        out[f"{pattern} :: {reason}"] = n
    # Mechanical non-C suffix census: only suffixes that actually occur appear.
    census: dict[str, int] = {}
    for p in scan_candidates(suite):
        if p.suffix in NON_C_REASON:
            census[p.suffix] = census.get(p.suffix, 0) + 1
    for suffix, n in sorted(census.items()):
        out[f"**/*{suffix} :: {NON_C_REASON[suffix]}"] = n
    return out


def enumerate_all(suite: str):
    """(attemptable, unsupported) for --stage full.

    ``unsupported`` starts from every file matched by the *declared* exclusion
    globs (which may lie outside the scan face, e.g. the suite-level
    ``External/``) and then adds the scan-face census, so the per-file reasons
    and the category census cover exactly the same corpus."""
    root = SUITE_ROOTS[suite]
    unsupported: dict[str, str] = {
        str(p.relative_to(root)): reason
        for p, reason in excluded_files(suite).items()}

    attemptable: list[tuple[str, str, tuple]] = []
    for p in sorted(scan_candidates(suite)):
        rel = str(p.relative_to(root))
        if rel in unsupported:
            continue
        if p.suffix != ".c":
            unsupported[rel] = NON_C_REASON[p.suffix]
            continue
        if suite == "libc-test" and rel.startswith("src/common/"):
            unsupported[rel] = ("libc-test harness support TU (no main / the "
                                "runner links it separately)")
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError as exc:
            unsupported[rel] = f"unreadable: {exc}"
            continue
        if not MAIN_RE.search(text):
            unsupported[rel] = ("no main(): helper/kernel TU driven by the "
                               "upstream lit harness, not a standalone program")
            continue
        cflags = (SMALL_PROBLEM_CFLAGS
                  if rel.startswith(BENCHMARK_TREES) else ())
        attemptable.append((rel, "full-stage enumeration: every C case with main()",
                            cflags))
    return attemptable, unsupported


def stage_cases(suite: str, stage: str):
    """-> (attempted [(rel, why, cflags)], unsupported {rel: why})

    The `unsupported` face is the *whole-suite* census in both stages, so the
    "how much of this corpus is out of scope, and why" number is comparable
    across stages and cannot drift with the stage-1 curation."""
    all_attemptable, unsupported = enumerate_all(suite)

    if stage == "fast":
        curated = {rel: (why, cf) for rel, why, cf in SUITE_CASES[suite]}
        known = {rel for rel, _, _ in all_attemptable}
        missing = sorted(set(curated) - known)
        if missing:
            print(f"run_suite: ERROR: curated {suite} case(s) are not in the "
                  f"suite's attemptable face (renamed? excluded?): {missing}",
                  file=sys.stderr)
            raise SystemExit(2)
        return list(SUITE_CASES[suite]), unsupported
    return all_attemptable, unsupported


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", choices=("libc-test", "llvm-test-suite", "all"),
                    default="all")
    ap.add_argument("--stage", choices=("fast", "full"), default="fast",
                    help="fast = the curated stage-1 subset (default); "
                         "full = every enumerable C case with main()")
    ap.add_argument("--work-dir",
                    default=str(REPO_ROOT / ".work" / "build" / "testcases-suites"))
    ap.add_argument("--qemu", default=str(TOOLCHAIN_BIN / "qemu-system-dadao"))
    ap.add_argument("--bootrom", default=str(DEFAULT_BOOTROM))
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--only", action="append", default=[],
                    help="case id '<suite>:<relpath>' (repeatable)")
    ap.add_argument("--list", action="store_true", help="list selected cases")
    ap.add_argument("--inject", action="store_true",
                    help="corrupt the expectations: every comparison must FAIL")
    ap.add_argument("--strict", action="store_true",
                    help="also exit non-zero on enosys/compile-error "
                         "(fail/timeout are always red)")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    # Hard boundary (QEMU-060t, 2026-10-15).  The dadao-m1 syscall service
    # (SYS_UMON_SYSCALL) was withdrawn by user ruling, so path B below
    # (-M dadao-m1) has no backend for the musl syscall stubs any more: user-mode
    # trap cfx0, 0 takes the generic cfx vector again (semihosting-only).  Fail
    # closed with a clear message instead of turning every case into a failure;
    # rc=2 is this tool's "setup error" code.  Running verification is P3
    # (qemu-user).
    print("run_suite: ERROR: the dadao-m1 syscall service (SYS_UMON_SYSCALL) "
          "was withdrawn by the user ruling of 2026-10-15 (QEMU-060t): the "
          "-M dadao-m1 path B is no longer runnable (no backend for the musl "
          "syscall stubs; semihosting-only). Running verification is now P3 "
          "(qemu-user). Refusing to run.", file=sys.stderr)
    raise SystemExit(2)

    suites = (["libc-test", "llvm-test-suite"] if args.suite == "all"
              else [args.suite])

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    # ---- selection --------------------------------------------------------
    selection = {}
    faces: set[str] = set()
    for suite in suites:
        attempted, unsupported = stage_cases(suite, args.stage)
        selection[suite] = {"attempted": attempted, "unsupported": unsupported}
        faces |= {f"{suite}:{rel}" for rel, _, _ in attempted}

    if args.only:
        wanted = set(args.only)
        unknown = wanted - faces
        if unknown:
            print(f"run_suite: ERROR: unknown --only id(s): {sorted(unknown)}",
                  file=sys.stderr)
            raise SystemExit(2)
        for suite in suites:
            selection[suite]["attempted"] = [
                t for t in selection[suite]["attempted"]
                if f"{suite}:{t[0]}" in wanted]

    if args.list:
        for suite in suites:
            for rel, why, _ in selection[suite]["attempted"]:
                print(f"{suite}:{rel}\t{why}")
        return 0

    if not any(selection[s]["attempted"] for s in suites):
        print("run_suite: ERROR: empty scan face (no case selected) -> FAIL "
              "(vacuous fail-closed)", file=sys.stderr)
        return 2

    # ---- setup preconditions ---------------------------------------------
    required = [TOOLCHAIN_BIN / t for t in ("clang", "ld.lld", "llvm-objcopy")]
    required += [MUSL_SRC / "lib" / "libc.a", MUSL_SRC / "lib" / "crt1.o", LDS,
                 Path(args.qemu), Path(args.bootrom)]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        print("run_suite: ERROR: missing prerequisite(s): "
              f"{', '.join(missing)} (run 'make install-host' + 'make build-musl"
              "' + 'make build-bootrom')", file=sys.stderr)
        return 2

    records = []
    counts = {k: 0 for k in ("pass", "fail", "enosys", "compile-error",
                             "timeout", "unsupported")}
    enosys_census: dict[str, int] = {}

    common_objs: list[Path] = []
    common_log: list = []
    if selection.get("libc-test", {}).get("attempted"):
        try:
            common_objs = build_common_objects(work, common_log)
        except RuntimeError as exc:
            print(f"run_suite: ERROR: libc-test common objects failed: {exc}",
                  file=sys.stderr)
            return 2

    for suite in suites:
        root = SUITE_ROOTS[suite]
        for rel, why, cf in selection[suite]["attempted"]:
            case_abs = root / rel
            rec = {"suite": suite, "case": rel, "why": why, "id": f"{suite}:{rel}"}
            build_log: list = []

            try:
                small_problem = SMALL_PROBLEM_CFLAGS[0] in cf
                ref = (reference_for(case_abs, small_problem)
                       if suite == "llvm-test-suite" else None)
            except RuntimeError as exc:
                rec.update(status="compile-error", detail=str(exc))
                records.append(rec)
                counts["compile-error"] += 1
                print(f"COMPILE-ERROR {rec['id']}: {exc}")
                continue

            if ref is not None:
                exp_stdout, exp_exit, ref_path = ref
            else:
                exp_stdout, exp_exit, ref_path = None, 0, None

            rec["expected"] = {
                "exit": exp_exit,
                "stdout": (exp_stdout.decode(errors="backslashreplace")
                           if exp_stdout is not None else None),
                "source": (ref_path if ref_path is not None
                           else "case verdict: t_status == 0 (libc-test)"
                           if suite == "libc-test"
                           else "ran-to-completion: exit == 0 (no upstream "
                                "reference; stdout sha256 recorded)"),
            }

            flat, err = build_case(suite, case_abs, work, build_log,
                                   common_objs if suite == "libc-test" else [], cf)
            rec["build"] = build_log
            if flat is None:
                failed_stage = build_log[-1].get("stage", "?")
                cause = "link" if failed_stage == "link" else failed_stage
                stderr_txt = build_log[-1].get("stderr") or ""
                if "undefined hidden symbol" in stderr_txt or \
                        "undefined symbol" in stderr_txt:
                    cause += ": undefined symbol (check components/musl/patches/" \
                             "arch/dadao/arch.mak.patch DADAO_BACKEND_BLOCKED_SRCS" \
                             " — ISS-223/ISS-222)"
                rec.update(status="compile-error", detail=err, cause=cause)
                counts["compile-error"] += 1
                print(f"COMPILE-ERROR {rec['id']}: {cause} | {err}")
                records.append(rec)
                continue

            obs = run_guest(args.qemu, Path(args.bootrom), flat, args.timeout,
                            flat.with_suffix(".stdout"), flat.with_suffix(".stderr"))
            if obs["timeout"]:
                partial = obs["stdout"].decode(errors="backslashreplace")
                rec.update(status="timeout", detail=f">{args.timeout}s",
                           cmd=obs["cmd"], stdout_len=len(obs["stdout"]),
                           stdout_sha256=sha256(obs["stdout"]), stdout=partial,
                           qemu_stderr=obs["stderr"][-2000:])
                counts["timeout"] += 1
                print(f"TIMEOUT {rec['id']}: >{args.timeout}s "
                      f"(partial stdout {len(obs['stdout'])}B kept at "
                      f"{flat.with_suffix('.stdout')})")
                records.append(rec)
                continue

            stdout, exit_code = obs["stdout"], obs["exit"]
            syscall_nrs = sorted({int(m) for m in ENOSYS_RE.findall(obs["stderr"])})
            for nr in syscall_nrs:
                enosys_census[str(nr)] = enosys_census.get(str(nr), 0) + 1
            rec.update(exit=exit_code, stdout_len=len(stdout),
                       stdout_sha256=sha256(stdout),
                       stdout=stdout.decode(errors="backslashreplace"),
                       enosys_syscalls=syscall_nrs,
                       qemu_stderr=obs["stderr"][-2000:])

            if args.inject:
                # ``--inject`` must make *every* comparison report a mismatch.  A
                # fixed sentinel value could coincide with a case's real exit
                # status (e.g. the two libc-test cases that really do exit 1), so
                # the injected expectation is derived from the observed value
                # here: ``(exit_code + 1) & 0xFF != exit_code`` holds by
                # construction.  The reference stdout (when there is one) is
                # still compared as-is.
                exp_exit = (exit_code + 1) & 0xFF
                rec["expected"]["exit"] = exp_exit
                rec["expected"]["injected"] = True

            matched = exit_code == exp_exit
            if exp_stdout is not None and matched:
                matched = stdout == exp_stdout
            rec["matched"] = matched

            if matched:
                status = "pass"
            elif syscall_nrs and not args.inject:
                status = "enosys"
            else:
                status = "fail"
            rec["status"] = status
            counts[status] += 1
            if not args.quiet:
                extra = f" exit={exit_code} stdout={len(stdout)}B"
                if syscall_nrs:
                    extra += f" enosys={syscall_nrs}"
                if status != "pass":
                    extra += f" (oracle{'MATCHED' if matched else 'MISMATCH'})"
                print(f"{status.upper():<13} {rec['id']}{extra}")
            records.append(rec)

        for rel, reason in sorted(selection[suite]["unsupported"].items()):
            records.append({"suite": suite, "case": rel, "id": f"{suite}:{rel}",
                            "status": "unsupported", "reason": reason})
            counts["unsupported"] += 1

    # ---- summary ---------------------------------------------------------
    attempted = sum(counts[k] for k in ("pass", "fail", "enosys",
                                        "compile-error", "timeout"))
    print("")
    for suite in suites:
        row = {k: sum(1 for r in records
                      if r.get("suite") == suite and r.get("status") == k)
               for k in counts}
        n_att = sum(row[k] for k in ("pass", "fail", "enosys",
                                     "compile-error", "timeout"))
        print(f"[{suite}] attempted={n_att} pass={row['pass']} fail={row['fail']} "
              f"enosys={row['enosys']} compile-error={row['compile-error']} "
              f"timeout={row['timeout']} unsupported={row['unsupported']}")
    print(f"[total]    attempted={attempted} pass={counts['pass']} "
          f"fail={counts['fail']} enosys={counts['enosys']} "
          f"compile-error={counts['compile-error']} timeout={counts['timeout']} "
          f"unsupported={counts['unsupported']}")
    if enosys_census:
        census = " ".join(f"{nr}x{n}" for nr, n in
                          sorted(enosys_census.items(), key=lambda kv: -kv[1]))
        print(f"[enosys-census] syscall:count  {census}")

    exc = {s: exclusion_counts(s) for s in suites}
    for suite, cats in exc.items():
        for label, n in sorted(cats.items()):
            if n == 0:
                print(f"[exclusion-empty] {suite}: category matched nothing: "
                      f"{label.split(' :: ')[0]}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {"stage": args.stage, "inject": args.inject, "counts": counts,
             "enosys_census": enosys_census, "exclusions": exc,
             "libc_test_common_objects": common_log,
             "records": records}, indent=2))

    if args.inject:
        print("run_suite: --inject run: every comparison above is expected to "
              "MISMATCH")
    if counts["fail"] or counts["timeout"]:
        return 1
    if args.strict and (counts["enosys"] or counts["compile-error"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
