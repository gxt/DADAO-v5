#!/usr/bin/env python3
"""llvm-test-suite user-mode runner (TESTCASES-048t; static round first).

Drives the manifest-locked ``llvm-test-suite`` corpus (``LLVM-093t``; lock
``2919e551...``, ``patchless`` -> the source tree is read-only) through the
**user-mode** (``qemu-dadao``) flow, one link mode per round
(``--link-mode static|dynamic``, no default: the two rounds are separate runs
by design, static first; ``--link-mode both`` runs static to completion and
then dynamic over the *same* enumeration snapshot, which is what the full run
uses).

Enumeration (live, never hard-coded)
------------------------------------
Scope A -- the only tree this task runs:

* ``SingleSource/Benchmarks/**/*.c``: one case per translation unit that
  carries ``main`` (upstream's ``llvm_singlesource()`` builds one executable
  per source file);
* ``MultiSource/Benchmarks/**`` and ``MultiSource/Applications/**``: one case
  per **program directory** (a directory with an immediate ``*.c`` that
  defines ``main``).  The translation units of a program are upstream's own
  curated ``llvm_multisource(<target> <sources...>)`` list when the program's
  CMakeLists has one (``jpeg-6a`` -> ``cjpeg`` + the jpeg library sources,
  ``lua`` -> ``lua`` but not ``luac``, ``cfrac`` -> not ``pfactor`` ...);
  otherwise every immediate ``*.c`` of the directory.  The task book's
  shorthand "every .c in the directory" would put a *second* ``main`` on the
  link line for ``lua``/``jpeg-6a``/``cfrac`` -- a driver artefact, not a
  suite result; the curated list is upstream's own statement of the program.

Scope B -- counted only, declared not run in this task: ``SingleSource/
Regression``, ``SingleSource/UnitTests``, ``MultiSource/{UnitTests,Examples}``.

Scope C -- structural exclusions with a live count and a per-entry reason:
``External/**`` (excluded by the user's 2026-10-15 ruling), non-C suffixes
(no C++ standard library in the sysroot, no Fortran front end), and
``MicroBenchmarks/**`` (live ``.c`` count, of which 0 carry ``main``).

Neither B nor C is ever counted as a pass.

Per-case pipeline::

    clang --target=dadao-unknown-elf -nostdinc <musl user headers> \
          <upstream CMake flags> -O2 -DNDEBUG -w -DSMALL_PROBLEM_SIZE \
          -c <TU>  -> <TU>.o            # one per TU of the program

    # static round: P1 musl products, lld DEFAULT base (never -T dadao.lds)
    ld.lld -o <p>.elf <musl>/lib/crt1.o <objs> \
           --start-group <musl>/lib/libc.a <clang -print-libgcc-file-name> \
           --end-group
    qemu-dadao <p>.elf <upstream RUN_OPTIONS>

    # dynamic round: P2 musl products, next round; the compile line adds
    # -fPIC (see below) but no other flag changes
    ld.lld -o <p>.elf <musl>/lib/crt1.o <objs> \
           --start-group <musl>/lib/libc.so <builtins archive> --end-group \
           -dynamic-linker /lib/ld-musl-dadao.so.1
    qemu-dadao -L <guest-root> <p>.elf <upstream RUN_OPTIONS>

The compiler-rt builtins archive is the one clang's own driver would use
(``clang -target dadao-unknown-elf -print-libgcc-file-name``; installed by
INFRA-088t) and is linked in both rounds: complex-arithmetic programs emit
``__muldc3``/``__divdc3`` calls (mandel, RSBench) that neither musl nor the
programs provide.  libc and builtins are wrapped in one lld ``--start-group``
because they reference each other.

The dynamic round compiles with ``-fPIC`` (documented deviation from "same
compile section"): without it a user TU that takes the address of a libc.so
data object (``stdout``/``stderr`` -- every program that prints) needs an
``R_DADAO_COPY`` copy relocation, which lld refuses by design (ADR-0026 D7(2)
/ contract-dynlink §10(2)); measured in the pilot:
``ld.lld: error: cannot create a copy relocation for symbol 'stdout'``.
The image stays a non-PIE ``ET_EXEC`` (no ``-pie``); the flag only changes how
the data address is formed.  The static command line stays byte-identical, and
every compile command is recorded in the JSON, so the split is auditable.
Same finding as TESTCASES-047t / TESTCASES-049t (ISS-259 candidate (2)).

The static link line names ``libc.a`` **explicitly**: ``-L <musl>/lib -lc``
would pick ``libc.so`` from the same directory (no ``PT_INTERP``, but
``PT_DYNAMIC`` present) and ``qemu-user`` then segfaults (TESTCASES-046t /
QEMU-062t).  Base address (ISS-247): no ``-T``/linker script is passed, so
lld's default base is used; ``tests/scripts/dadao.lds`` (``RAM ORIGIN =
0xFC00_0000_0000``) cannot be loaded by ``qemu-user`` on this 47-bit host VA.
Every image's minimum ``PT_LOAD`` and its ``PT_INTERP`` are read back from the
file (the modality is asserted, not assumed).

Run configuration (upstream CMake, parsed live)
-----------------------------------------------
Upstream's per-directory ``CFLAGS``/``CPPFLAGS``/``add_definitions`` and
``RUN_OPTIONS`` are what make a reference output reproducible (Polybench's
``-DPOLYBENCH_DUMP_ARRAYS`` + ``-DSMALL_DATASET``, Olden's small
``RUN_OPTIONS``, FreeBench's ``-DVERSION=...``, ``-fcommon`` ...).  The driver
therefore evaluates the CMake directives on the path from the tree root to
the program directory with a small, documented evaluator:

* the platform variables are pinned to this target: ``SMALL_PROBLEM_SIZE=ON``,
  ``LARGE_PROBLEM_SIZE=OFF``, ``TARGET_OS=Linux``, ``ENDIAN=big`` (ADR-0003
  D1), ``ARCH=Dadao``, ``CMAKE_SYSTEM_NAME=Linux``, plus
  ``TEST_SUITE_SUPPRESS_WARNINGS=ON`` and
  ``COMPILER_HAS_NO_DEFINE_TARGET_OS_MACROS=ON``;
* ``set``/``list(APPEND|REMOVE)``/``add_definitions``/
  ``target_compile_options``/``include_directories`` and
  ``target_include_directories``/``llvm_test_data`` are tracked for ``CFLAGS``,
  ``CPPFLAGS``, ``RUN_OPTIONS``, the ``-I`` set and the run inputs; ``if``/
  ``elseif``/``else``
  support ``NOT``/``AND``/``OR``/``DEFINED``/``STREQUAL``/``MATCHES``.  An
  undefined variable is false -- CMake's own rule, not a guess;
* a construct the evaluator cannot parse makes the case **blocked**
  (``upstream CMake configuration not derivable``), never a silent
  guess-and-run;
* include paths (TESTCASES-050t): the ``-I`` set is the one upstream declares
  on the unit's CMakeLists chain (``include_directories`` /
  ``target_include_directories``), with ``${CMAKE_CURRENT_SOURCE_DIR}``
  expanded and relative entries resolved against the declaring directory.  A
  unit whose chain declares none is compiled with ``-I<unit_dir>`` (CMake's
  ``CMAKE_CURRENT_SOURCE_DIR`` view) and the record says which of the two
  applied (``cmake.include_dir_source``).  A literal ``${...}`` never reaches a
  compile line: an unexpanded variable makes the case blocked;
* the compiler line keeps upstream's global ``-DNDEBUG -w``.  ``-Werror=
  date-time`` is *not* taken over: it is an upstream reproducibility policy
  that would turn a ``__DATE__`` use into a build error unrelated to the
  target (recorded here, no case in scope A trips it);
* ``-l<name>`` link flags from upstream are not passed: musl keeps libm
  inside ``libc.a``/``libc.so`` and the lock has no separate ``libsocket``/
  ``libnsl``; the dropped flags are recorded per case.

``RUN_OPTIONS`` is a shell fragment upstream (``< input``, quoted argument
groups, ``%S`` substitution).  It is parsed with ``shlex`` plus an explicit
``< file`` stdin redirection -- **not** run through a shell -- so the timeout
kills exactly the guest process.  Each case runs in a per-case *copy* of its
program directory, because upstream's ``WORKDIR %S`` lets programs write
their outputs next to the sources and the corpus is ``patchless``.
``llvm_test_data()`` inputs are copied into that same per-case directory, the
way CMake copies them next to the executable: mediabench's ``testimg.ppm`` and
``mei16v2.m2v`` live in ``../data`` and are named relatively by ``RUN_OPTIONS``.

Independent oracle (AGENTS.md "Independent oracle")
---------------------------------------------------
The expectation comes from upstream's own reference file, never from LLVM,
QEMU or anything in this repository:

* ``reference_for`` order: ``.reference_output.small`` (the
  ``SMALL_PROBLEM_SIZE`` build) > ``.reference_output.big-endian`` (this
  machine is big-endian, ADR-0003 D1) > ``.reference_output``.  Upstream's
  own ``llvm_test_traditional`` uses the same precedence; the combined
  ``.<endian>-endian.<size>`` variant never exists in the locked corpus;
* a reference file is upstream's whole output *document*: the program's
  interleaved stdout+stderr plus a bare ``exit N\\n`` tail that
  ``RunSafely.sh:257`` appends (no separator -- a binary program's last byte
  is glued to ``exit``).  Three forms occur in scope A:
  - text document (161 units): compared byte-for-byte; the exit status is
    implicitly checked through the tail;
  - a single md5 line (52 units, ``HASH_PROGRAM_OUTPUT``): the hash covers
    that same document (``HashProgramOutput.sh`` runs after RunSafely), so
    md5(output + ``exit N\\n``) must equal it;
  - a binary document (3 units, ``oggenc``/``imp``/``cjpeg``): compared
    byte-for-byte, with the same ``exit N\\n`` tail;
  Upstream's ``RunSafely.sh`` points stdout and stderr at the *same* file
  (``timeit --redirect-output``, tools/timeit.c:891-894), so a reference
  covers the interleaved stream -- Polybench dumps its arrays to ``stderr``
  and its reference hash covers exactly that text;
* the reference file is named after upstream's ``TEST_NAME`` -- the
  ``llvm_multisource`` target name, which differs from the directory name for
  29 programs (``jpeg-6a`` -> ``cjpeg.reference_output``,
  ``SMALL_PROBLEM_SIZE``-era source paths ...).  Reading ``<dir>/<dir>.
  reference_output`` would silently lose those oracles;
* no reference file (6 units): the only achievable verdict is "ran to
  completion with exit 0"; the output sha256 is recorded and the result is
  marked ``exit-only`` in the record/report.  **This is not an output
  equivalence verdict** and is counted separately (``pass_exit_only``).

Classification (counted live, never hard-coded)
-----------------------------------------------
* ``pass``        built + linked + ran; the oracle matched (see three forms
                  above), or exit 0 for the exit-only units.
* ``fail``        built + ran, the oracle did NOT match (output document /
                  md5 / exit tail mismatch).  A real defect; the first line of
                  the program's own output is recorded.
* ``known-fail``  the failure is explained by a row of the **per-case basis
                  table** (``KNOWN_FAIL_BASES``) with that row's evidence
                  recomputed live.  Two causes are admitted:
                  * ``ISS-246`` (``__thread``: clang ``thread-local storage is
                    not supported for the current target`` / backend
                    ``GlobalTLSAddress``) -- requires a live TLS declaration
                    scan hit in the case's *own* sources **and** that exact
                    diagnostic.  Expected 0 here: the suite's C programs do not
                    use TLS.
                  * ``ISS-265`` (upstream references that encode glibc
                    semantics) -- admission is **per case, never per class**:
                    ``ISS265_ADMISSION`` names exactly the three cases the
                    user ruled known-fail (``ClamAV`` = interleaved-stream
                    order, ``obsequi``/``ft`` = musl-vs-glibc PRNG seeding),
                    and each row's live check must hold:
                    ``ClamAV`` -- the actual and expected documents have the
                    same size and the same line multiset (only the order
                    differs); ``obsequi``/``ft`` -- a live seed+draw call in
                    the case's own sources, plus a probe (built with the same
                    clang/musl and run under the same qemu) showing musl's
                    ``random()``/``rand()`` sequence after seed 1 differs from
                    the host glibc's.
                  No other cause is admitted (the older "sole basis = ISS-246"
                  wording is superseded by INFRA-087t's per-case-evidence
                  rule; a row whose evidence does not hold leaves the case
                  ``fail``, so the round stays red).
* ``blocked``     a build/run gap prevents the case from reaching its own
                  verdict: compile/link failure, missing symbol, an image at
                  the scripted base, a wrong PT_INTERP/modality, qemu killed
                  by a host signal, timeout (``--timeout`` seconds; the
                  ``124``/timeout case is *blocked*, never pass/fail), or
                  non-derivable upstream CMake configuration.
                  ``blocked > 0 => rc = 1`` (ISS-248 gate rule: incomplete
                  coverage must not look green).  A completed run whose
                  oracle mismatch is caused by the platform never executing
                  the work (``PLATFORM_GAP_SIGNATURES``, live signature
                  required) is filed as ``blocked`` too, never as ``fail``.
* ``excluded``    declared up front, structural, with a reason.  Scope A's
  entries are ``MultiSource/Applications/siod`` (BSD ``d_namlen`` on a target
  without the ``linux`` predefine) and
  ``MultiSource/Benchmarks/MiBench/office-ispell`` (BSD ``<sgtty.h>``, absent
  from musl and from the corpus) -- both are missing *platform APIs*, not
  missing include paths (TESTCASES-050t items 1/4).  Excluded cases are counted
  live, keep their reason in the JSON/report, and never count as a pass; a
  registry entry that no longer matches a discovered unit fails the census
  audit.  B/C are reported as counts and are **not** passes.

Per-case run timeouts (TESTCASES-050t item 2) are the ``CASE_TIMEOUTS`` table:
values measured on this host (``run_seconds`` in the JSON) plus a 120 s
margin, rounded up to the next minute, applied in addition to ``--timeout``
(effective timeout = ``max``).  ``DEFAULT_TIMEOUT`` stays at the baseline
300 s; it is not raised globally because only a handful of programs need more,
and every other case would then be able to burn that budget before a hang is
reported.  ``unix-smail`` is not in the table because it completes: measured
0.11 s in both link modes (TESTCASES-054t), far below the 300 s baseline.

Every case record keeps: compile command lines, link command, run argv, work
directory, oracle file, stdout sha256 + size, min ``PT_LOAD``, ``PT_INTERP``
and the derived upstream flags -- so the report can be audited line by line.

A round's summary carries the six numbers
``total/pass/fail/known-fail/blocked/excluded``.  ``pass`` is also split into
``pass_reference`` (real oracle) and ``pass_exit_only`` (exit-only, not an
equivalence verdict).

Exit status: 0 = no ``fail`` and no ``blocked`` and the census/closure audit
holds; 1 = otherwise; 2 = setup error (missing tool / source / library
product / zero cases).

Structural closure (lessons §2.21): the driver enumerates live, requires the
executed set to equal the discovered scope-A set (minus ``--only``/``--limit``
pilot selection) and prints both numbers; a silently skipped case makes the
run fail.  Counts are printed, never hard-coded.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ctypes
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import struct
import subprocess
import time
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases"))
import paths as _paths  # noqa: E402
import run_artifacts as _run_artifacts  # noqa: E402

TOOLCHAIN_BIN = str(_paths.host_toolchain_bin())

DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_SRC = ".work/source/llvm-test-suite"
DEFAULT_MUSL = ".work/source/musl"
DEFAULT_WORK_DIR = str(_paths.test_artifacts_dir() / "llvm-ts-user")
# Baseline budget (the value TESTCASES-048t's full runs used).  It is *not*
# raised globally: only the few genuinely slow programs need more, and a global
# raise would let every other case burn that time before a hang is reported.
# The genuinely slow programs get their own measured budgets in
# ``CASE_TIMEOUTS`` instead.  ``unix-smail`` is not one of them: it completes in
# 0.11 s in both link modes (TESTCASES-054t), well inside this baseline.
DEFAULT_TIMEOUT = 300
DEFAULT_JOBS = 4
BUILD_TIMEOUT = 300

# Per-case run timeouts (TESTCASES-050t, re-measured in TESTCASES-054t): six
# programs need more than the default on this host; their 300 s truncation in
# TESTCASES-048t was a timeout *setting*, not a property of the program.
# Formula (documented, not guessed):
#
#     value = ceil((measured run_seconds + 120 s margin) / 60) * 60
#
# with ``run_seconds`` measured at jobs=1 on this host (recorded per case in
# the run JSON and in CASE_TIMEOUT_BASIS below).  ``--timeout`` stays a floor:
# the effective timeout is ``max(--timeout, table value)``.  ``unix-smail`` is
# deliberately absent because it completes in 0.11 s (both link modes,
# TESTCASES-054t), far below the 300 s baseline, so it needs no entry.
CASE_TIMEOUTS = {
    "MultiSource/Applications/lemon": 480,      # 331.43 -> 451.43 -> 480
    "MultiSource/Applications/lua": 1320,       # 1141.74/1167.14 -> 1320
    "MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC": 480,  # 349.54 -> 480
    "MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench": 720,  # 533.44/541.58 -> 720
    "MultiSource/Benchmarks/mafft": 1620,       # 1452.82 -> 1572.82 -> 1620
    "MultiSource/Benchmarks/nbench": 480,       # 312.20 -> 432.20 -> 480
}

# Why the table above holds these values (quoted in the report; the measured
# seconds live in the run JSON, so this string is provenance, not a number).
CASE_TIMEOUT_BASIS = {
    "MultiSource/Applications/lemon":
        "measured run 331.43 s (guest children die of SIGSEGV; see "
        "PLATFORM_GAP_SIGNATURES) + 120 s margin, rounded up to 60 s -> 480 s",
    "MultiSource/Applications/lua":
        "measured complete run 1141.74 s (static) / 1167.14 s (dynamic) at "
        "jobs=1 + 120 s margin -> 1287.14 s, rounded up to 60 s -> 1320 s "
        "(TESTCASES-054t; both rounds PASS with the md5 oracle)",
    "MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC":
        "measured complete run 349.54 s + 120 s margin, rounded up to 60 s "
        "-> 480 s",
    "MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench":
        "measured complete run 533.44 s (static) / 541.58 s (dynamic) at "
        "jobs=1 + 120 s margin -> 661.58 s, rounded up to 60 s -> 720 s "
        "(TESTCASES-054t; both rounds PASS, stdout byte-exact)",
    "MultiSource/Benchmarks/mafft":
        "measured complete run 1452.82 s + 120 s margin, rounded up to 60 s "
        "-> 1620 s",
    "MultiSource/Benchmarks/nbench":
        "measured complete run 312.20 s + 120 s margin, rounded up to 60 s "
        "-> 480 s",
}

TARGET = "dadao-unknown-elf"
DYNAMIC_LINKER = "/lib/ld-musl-dadao.so.1"

# Public include set for *user* translation units (the same header view the
# sister driver tools/testcases/run_libc_test_user_suite.py uses, and for the
# same verified reason): musl's own build view (src/include/errno.h) maps
# ``errno`` to the hidden ``___errno_location``, which libc.a defines but
# libc.so keeps LOCAL HIDDEN -- a user TU compiled with the internal headers
# links statically and fails dynamically with ``undefined hidden symbol:
# ___errno_location``.  That would be a driver include bug, not a suite result.
MUSL_USER_INCLUDE_DIRS = ("arch/dadao", "arch/generic", "obj/include",
                          "include")

# Upstream's global compiler policy (CMakeLists.txt:59-66) minus
# ``-Werror=date-time`` (see the module docstring).
BASE_CFLAGS = ("-O2", "-DNDEBUG", "-w")

# cmake/modules/TestSuite.cmake:49-50 -- the verification (not scoring) size
# knob; it changes the workload size, never the program's own verdict.
SMALL_PROBLEM_CFLAGS = ("-DSMALL_PROBLEM_SIZE",)

A_MULTI_TREES = ("MultiSource/Benchmarks", "MultiSource/Applications")
B_TREES = ("SingleSource/Regression", "SingleSource/UnitTests",
           "MultiSource/UnitTests", "MultiSource/Examples")
SCAN_TREES = ("SingleSource", "MultiSource", "MicroBenchmarks")
C_SUFFIXES = (".cc", ".cpp", ".cxx", ".C", ".m", ".mm",
              ".f", ".f77", ".f90", ".F", ".F90")

MAIN_RE = re.compile(r"\b(?:int|void)\s+main\s*\(")
EXIT_TAIL_RE = re.compile(rb"exit (\d+)\n$")
HEX32_RE = re.compile(r"^[0-9a-f]{32}$")

# ISS-246 is the only compile-time cause the per-case basis table admits; see
# ISS265_ADMISSION below for the run-time (reference portability) rows.
ISS246_ID = "ISS-246"
ISS246_PATTERNS = (
    "thread-local storage is not supported",
    "GlobalTLSAddress",
)
TLS_RE = re.compile(r"__thread|_Thread_local|\bthread_local\b")

# ISS-265 (user ruling 2026-10-18: known-fail).  Admission is **per case** and
# closed: only the three cases named here can be reclassified, and only while
# that row's live check holds.  A fourth failing case never reaches this table,
# so no class-wide escape hatch exists.  ``kind``/``api`` select the check:
#   interleave -- same bytes and same line multiset, only the line order differs
#                 (upstream compares one interleaved stdout+stderr stream);
#   prng       -- live seed+draw in the case's own sources, and a live probe
#                 showing musl's ``api`` sequence != the host glibc's.
ISS265_ID = "ISS-265"
ISS265_ADMISSION = {
    "MultiSource/Applications/ClamAV": dict(
        kind="interleave",
        why="upstream's reference is one interleaved stdout+stderr document; "
            "the guest swaps the positions of clamscan's cli_dbgmsg "
            "'Initializing the engine (devel-20071218)' line and the "
            "database-age warning, so the bytes and line multiset match while "
            "the order differs"),
    "MultiSource/Applications/obsequi": dict(
        kind="prng",
        api="random",
        why="init.c:63 calls srandom(1) and init.c:66 seeds the Zobrist "
            "tables with random(); musl's lagged-Fibonacci seeding is not "
            "glibc's 16807/Schrage sequence, so the node/cutoff counters "
            "differ while 'Winner found: 5000' agrees"),
    "MultiSource/Benchmarks/Ptrdist/ft": dict(
        kind="prng",
        api="rand",
        why="ft.c:54 maps srandom->srand and graph.c:40 maps random->rand; "
            "musl's rand() is a 64-bit LCG (src/prng/rand.c) whereas glibc's "
            "rand() follows random(), so the generated graph and its output "
            "differ (host glibc reproduces the reference hash)"),
}
ISS265_SEED_RE = re.compile(r"\b(?:srandom|srand)\s*\(")
# Two values per API after seed 1; printed by ISS265_PRNG_PROBE below.
ISS265_PRNG_PROBE = """\
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
\tsrandom(1);
\tprintf("random %ld %ld\\n", (long)random(), (long)random());
\tsrand(1);
\tprintf("rand %ld %ld\\n", (long)rand(), (long)rand());
\treturn 0;
}
"""

KNOWN_FAIL_BASES = {
    ISS246_ID: "live TLS declaration scan hit in the case's own sources + "
               "clang thread-local-storage diagnostic",
    ISS265_ID: "per-case admission table ISS265_ADMISSION (exactly ClamAV / "
               "obsequi / ft): interleaving-only document difference, or a "
               "live musl-vs-glibc PRNG sequence divergence",
}

# Programs upstream does not add under ``SMALL_PROBLEM_SIZE`` (its tree
# CMakeLists guards the ``add_subdirectory`` with ``if(NOT DEFINED
# SMALL_PROBLEM_SIZE)``): the task book's scope A is "every program directory",
# so they stay in the set and are run; the note keeps the deviation auditable.
UPSTREAM_SMALL_PRUNE = {
    "MultiSource/Applications/lua":
        "upstream skips this program when SMALL_PROBLEM_SIZE is defined "
        "(MultiSource/Applications/CMakeLists.txt: 'if(NOT DEFINED "
        "SMALL_PROBLEM_SIZE) add_subdirectory(lua)'); kept in scope A per the "
        "task book's program-directory rule and run anyway",
    "MultiSource/Benchmarks/mafft":
        "upstream skips this program when SMALL_PROBLEM_SIZE is defined "
        "(MultiSource/Benchmarks/CMakeLists.txt: 'if(NOT DEFINED "
        "SMALL_PROBLEM_SIZE) add_subdirectory(mafft)'); kept in scope A per "
        "the task book's program-directory rule and run anyway",
}

# Upstream's Polybench template lives under SingleSource/Benchmarks but
# ``Polybench/utilities/`` has no CMakeLists.txt, so upstream never builds it.
# The book's enumeration rule (".c with main under SingleSource/Benchmarks")
# counts it; it is executed and its result reported like any other case.
POLYBENCH_TEMPLATE = "SingleSource/Benchmarks/Polybench/utilities/template-for-new-benchmark"

# Declared structural exclusions inside the enumerated scope-A set
# (TESTCASES-050t item 4).  Only causes that cannot be fixed on the driver
# side belong here -- a missing *path* is a driver bug (see the include
# mechanism below), a missing *platform API* is not.  Each entry needs a
# reason that names the corpus source and the platform fact; the corpus and
# the headers are read-only (patchless), so no shim is added.
STRUCTURAL_EXCLUSIONS = {
    "MultiSource/Applications/siod":
        "siod's slibu.c:733 selects ``namlen = r->d_namlen`` in its BSD "
        "branch (``#if defined(sun) || defined(sgi) || defined(linux)`` is "
        "false) -- ``linux``/``unix`` are GCC/clang *host* predefines that "
        "this bare-metal target does not have (clang -target "
        "dadao-unknown-elf -dM: no linux/unix/__linux__), so the branch "
        "cannot be selected without adding a macro upstream never sets; "
        "musl's struct dirent (arch/generic/bits/dirent.h:5) has no "
        "``d_namlen`` field at all.  Corpus and headers are read-only, so "
        "the case is excluded with this reason instead of patched.",
    "MultiSource/Benchmarks/MiBench/office-ispell":
        "office-ispell's term.c:91 includes <sgtty.h>, the BSD terminal "
        "interface header (sgtty/gtty).  musl has no such header and the "
        "locked corpus does not ship one either (no sgtty.h under "
        "MultiSource/Benchmarks/MiBench/office-ispell), so this is a missing "
        "*platform API*, not a missing include path: no -I can supply it.  "
        "The case is excluded with this reason; no shim header is added "
        "(corpus is patchless, task book forbids a fake header).",
}

# Dynamic round only (TESTCASES-049t / ISS-259 candidate (2), the same finding
# tools/testcases/run_libc_test_user_suite.py records): a user TU that takes the
# address of a libc.so data object (``stdout``/``stderr``/``environ`` -- every
# program that prints) otherwise needs an ``R_DADAO_COPY`` copy relocation,
# which lld refuses by design (ADR-0026 D7(2) / contract-dynlink §10(2)):
#   ld.lld: error: cannot create a copy relocation for symbol 'stdout':
#   R_DADAO_COPY is not emitted by this implementation ...
# With -fPIC the data address is formed through the GOT and the image stays a
# plain non-PIE ET_EXEC (no -pie).  The static round is untouched, so its
# command line stays byte-identical; every compile command is recorded per
# case, so the split is auditable.
DYNAMIC_USER_CFLAGS = ("-fPIC",)

# Per-case run preparation that upstream performs through CMake custom
# commands (documented; not a general generator framework).  sqlite3's
# CMakeLists builds ``${CMAKE_CURRENT_BINARY_DIR}/test15.sql`` by running
# ``${TCL_TCLSH} smalltest.tcl`` before the test; the tcl script also writes
# test1.sql..test5.sql, which ``commands`` reads.  Without it the program
# cannot reach its own verdict ("can't open test1.sql"), which would be a
# harness artefact, not a suite result.
CASE_PREPARE = {
    "MultiSource/Applications/sqlite3": (
        ["tclsh", "smalltest.tcl"],
        "upstream CMake runs ${TCL_TCLSH} smalltest.tcl (SMALL_PROBLEM_SIZE) "
        "to generate test1.sql..test5.sql before the test"),
    # lua's CMakeLists declares an add_custom_command/target (lua_input) that
    # copies bench/test/input + *.lua into the binary dir and runs
    # generate_inputs.sh, which *generates* the large inputs
    # (moments-input400000.txt, regexmatch-input2000.txt, wc-input3000.txt ...).
    # Without it alltests.lua aborts at bench/moments.lua with
    # "input/moments-input400000.txt: No such file or directory" -- an
    # upstream-build artefact, not a program result (TESTCASES-050t).
    "MultiSource/Applications/lua": (
        ["sh", "generate_inputs.sh"],
        "upstream's lua_input custom command runs generate_inputs.sh in the "
        "build dir to generate input/moments-input400000.txt and the other "
        "large benchmark inputs"),
}

# Directories the program expects beside its sources but never names on the
# command line: JM/lencod reads ``data/encoder_small.cfg``, whose
# ``ReconFile``/``OutputFile`` are ``Output/test_rec.yuv``/``Output/test.264``
# (encoder_small.cfg:18-19) and opens them without creating ``Output/``.
# Upstream's ``WORKDIR %S`` runs the binary in a copy of the program directory
# of a build tree where that directory exists, so it has to be pre-created in
# the per-case copy; without it the case fails for a missing directory, not
# because of the code under test (ISS-276).  The table is deliberately
# per-case -- no config-file parser -- and names exactly the relative path the
# corpus declares.
CASE_PREPARE_DIRS = {
    "MultiSource/Applications/JM/lencod": ("Output",),
}

# Root-cause notes for non-pass cases (documentation only -- the class is still
# decided by the oracle/classification rules above).
CASE_NOTES = {
    "MultiSource/Benchmarks/Prolangs-C/archie-client":
        "upstream guards both llvm_multisource(archie) and the "
        "target_include_directories() that provides <copyright.h> behind "
        "check_function_exists(re_comp) (CMakeLists.txt:4 and :15); musl "
        "provides no re_comp/re_exec (BSD regex API, absent from musl's "
        "headers), so upstream's own configuration does not build this target "
        "on this libc and the link stops at 'undefined symbol: re_comp'.  The "
        "corpus' regex.c implements re_comp only under NOREGEX, which "
        "pmachine.h defines for legacy platforms only (u3b2/hpux/ISC/CUTCP/"
        "OS2/MSDOS), not for Linux -- no stub is taken.  The directory is "
        "still counted by the book's .c-with-main rule and kept `blocked` "
        "(the book's wording for this case), not `excluded`.",
    "SingleSource/Benchmarks/Misc/aarch64-init-cpu-features":
        "AArch64-only test: it calls __init_cpu_features and reads "
        "__aarch64_cpu_features, runtime symbols only AArch64's libc provides; "
        "upstream adds the file to the target only when "
        "check_symbol_exists(__init_cpu_features) succeeds.  Not buildable "
        "for dadao-unknown-elf.",
    "MultiSource/Applications/ClamAV":
        "oracle mismatch is interleaving-sensitive: the output has the same "
        "38065 B of program text (plus the 7 B 'exit 0' tail) but the line "
        "'Initializing the engine (devel-20071218)' (cli_dbgmsg, "
        "libclamav_readdb.c:277) sits before the database-age warnings in "
        "this run and after them in the reference; stdout/stderr buffering "
        "decides that position.  Reported as `fail` by the oracle rule (a "
        "stale/interleaving-sensitive reference is not relabelled).",
}

# Run-completion gaps that make a *completed* run unable to reach the case's
# own verdict: the program runs and exits, but the work itself never executes.
# Same idea as run_libc_test_user_suite.py's gap signatures, but keyed per case
# because the evidence is a corpus-specific diagnostic.  An entry is used only
# when its live signature is actually present in the run output; without it the
# case keeps the oracle's verdict (``fail``).  A gap can be a platform defect
# or corpus-level undefined behaviour that only manifests on this ABI; the
# per-case reason carries the attribution.
PLATFORM_GAP_SIGNATURES = {
    "MultiSource/Applications/lemon": (
        b"Error while running on: ",
        "corpus undefined behaviour, not a compiler/qemu backend defect: "
        "lemon.c:334 declares Configtable_clear with an empty parameter list "
        "(no prototype) and lemon.c:1127-1133 calls it as "
        "Configtable_clear(0) with an int argument, while lemon.c:4839-4840 "
        "defines the parameter as int(*f)(struct config *).  C11/N1570 "
        "6.5.2.2p6: with no prototype only the default argument promotions "
        "apply, so 0 stays int; the definition's parameter after promotion is "
        "a pointer, the types are not compatible and neither listed exception "
        "applies -> undefined behaviour (p8: no other implicit conversions are "
        "performed, so no pointer is ever formed).  clang faithfully emits "
        "'call void @Configtable_clear(i32 0)'; the same call through a "
        "prototype emits 'call void @Configtable_clear(ptr null)' and writes "
        "rb16 (rd2rb {rb16}, {rd4}), whereas without the prototype the caller "
        "only does 'set.zw rd16, wp0, 0x0' while Configtable_clear reads f "
        "from rb16 (rb2rb {rb32}, {rb16}) and therefore calls a stale pointer. "
        "x86-64 ('xorl %edi,%edi') and riscv64 ('li a0,0') pass int and "
        "pointer arguments in the same register, so the same undefined "
        "behaviour happens to work there; only the bank-separated ABI exposes "
        "it.  The parent then prints 'Error while running on: <input>' for "
        "every input (that line is the recorded first_error), exits 0 and "
        "produces no parser, so the md5 oracle cannot be reached.  "
        "Attribution: corpus UB (ISS-277); not ISS-269/qemu, not QEMU-063t, "
        "not ISS-267."),
}

# Cases whose host-signal death is a known qemu defect (reason pointer).
QEMU_SIGNAL_ISSUES = {
}

# Machine-fault exits (ADR-0004 D5.8): the guest left through a machine fault.
FAULT_NAMES = {
    0x87: "UNMAPPED", 0x88: "ILLI", 0x89: "UNDI", 0x8A: "RASOF",
    0x8B: "RASUF", 0x8C: "MALIGN", 0x8D: "IALIGN",
}

# The scripted base of tests/scripts/dadao.lds (ISS-247).
SCRIPTED_BASE = 0xFC0000000000

PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3


class SetupError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def run_bytes(cmd, timeout=None, cwd=None, stdin_path=None):
    """Run cmd; return (rc, stdout_bytes, stderr_bytes, timed_out).

    ``timed_out`` is True when the timeout fired (the process group is killed,
    so the guest itself dies, not only a wrapper); ``rc`` is then the killed
    process' return code and must not be interpreted as a program verdict.
    """
    stdin = subprocess.DEVNULL
    if stdin_path:
        stdin = open(stdin_path, "rb")
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, stdin=stdin,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                start_new_session=True)
    except OSError as exc:
        if stdin_path:
            stdin.close()
        return 127, b"", str(exc).encode(), False
    try:
        out, err = proc.communicate(timeout=timeout)
        timed = False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        out, err = proc.communicate()
        timed = True
    finally:
        if stdin_path:
            stdin.close()
    return proc.returncode, out, err, timed


def run_stream(cmd, out_path, timeout=None, cwd=None, stdin_path=None):
    """Run cmd with stdout+stderr on ONE fd, as upstream's RunSafely does.

    ``timeit --redirect-output`` points ``stdout`` and ``stderr`` at the same
    file (tools/timeit.c:891-894), so a reference output is the *interleaved*
    stream: Polybench dumps its arrays to ``stderr`` (polybench.h
    ``POLYBENCH_DUMP_TARGET stderr``) and its ``.reference_output`` hash
    covers that text.  Two separate pipes would silently lose it.

    Returns (rc, combined_bytes, timed_out); rc is None on timeout.
    """
    stdin = subprocess.DEVNULL
    if stdin_path:
        stdin = open(stdin_path, "rb")
    try:
        with open(out_path, "wb") as out:
            proc = subprocess.Popen(cmd, cwd=cwd, stdin=stdin, stdout=out,
                                    stderr=subprocess.STDOUT,
                                    start_new_session=True)
            try:
                proc.wait(timeout=timeout)
                timed = False
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                proc.wait()
                timed = True
    except OSError as exc:
        return 127, str(exc).encode(), False
    finally:
        if stdin_path:
            stdin.close()
    with open(out_path, "rb") as fh:
        data = fh.read()
    return proc.returncode, data, timed


def build_fpcmp(suite_root: str, work_dir: str):
    """Build upstream's own fpcmp (host tool) from the locked corpus.

    ``llvm_test_traditional`` compares with ``${FPCMP}`` and adds ``-r``/``-a``/
    ``-i`` when the program's CMake sets the tolerance knobs.  Reusing the
    corpus' ``tools/fpcmp.c`` keeps the comparison exactly upstream's instead
    of a re-implementation.
    """
    source = os.path.join(suite_root, "tools", "fpcmp.c")
    if not os.path.isfile(source):
        return None, "tools/fpcmp.c missing from the corpus"
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        return None, "host cc/gcc not found"
    out = os.path.join(work_dir, "fpcmp")
    rc, _out, err_b, timed = run_bytes([cc, "-O2", "-o", out, source, "-lm"],
                                      timeout=120)
    if timed or rc != 0:
        return None, ("fpcmp build failed rc="
                      f"{rc}: {err_b.decode('utf-8', 'replace')[:160]}")
    return out, ""


def require_file(path: str, what: str) -> None:
    if not os.path.isfile(path):
        raise SetupError(f"{what} not found: {path}")


def require_exec(path: str, what: str) -> None:
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        raise SetupError(f"{what} not executable: {path}")


def read_text(path: str) -> str:
    with open(path, "r", errors="replace") as fh:
        return fh.read()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def first_tool_error(stderr: str) -> str:
    for line in stderr.splitlines():
        if "error:" in line or "undefined symbol" in line:
            return line.strip()
    for line in stderr.splitlines():
        if line.strip():
            return line.strip()
    return "(no stderr)"


def first_output_line(stdout: bytes, stderr: bytes) -> str:
    for blob in (stdout, stderr):
        text = blob.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line.strip():
                return line.strip()[:240]
    return "(no output)"


def elf_program_headers(path: str):
    """Minimal ELF64 big-endian program-header reader (independent of QEMU)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ValueError(f"{path}: not an ELF file")
    if data[4] != 2 or data[5] != 2:
        raise ValueError(f"{path}: expected ELFCLASS64/ELFDATA2MSB, "
                         f"got class={data[4]} data={data[5]}")
    (e_phoff,) = struct.unpack_from(">Q", data, 32)
    (e_phentsize, e_phnum) = struct.unpack_from(">HH", data, 54)
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, _p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, \
            _p_align = struct.unpack_from(">IIQQQQQQ", data, off)
        phdrs.append(dict(type=p_type, offset=p_offset, vaddr=p_vaddr,
                          filesz=p_filesz, memsz=p_memsz))
        if p_type == PT_INTERP:
            phdrs[-1]["interp"] = data[p_offset:p_offset + p_filesz]
    return phdrs


def min_pt_load(path: str) -> int:
    return min(p["vaddr"] for p in elf_program_headers(path)
               if p["type"] == PT_LOAD)


def pt_interp(path: str) -> bytes:
    for p in elf_program_headers(path):
        if p["type"] == PT_INTERP:
            return p.get("interp", b"")
    return b""


def has_pt_dynamic(path: str) -> bool:
    return any(p["type"] == PT_DYNAMIC for p in elf_program_headers(path))


# ---------------------------------------------------------------------------
# upstream CMake: a small, documented evaluator (CFLAGS/CPPFLAGS/RUN_OPTIONS)
# ---------------------------------------------------------------------------
CMAKE_ARG_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+')
CMAKE_CMD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$", re.S)
CMAKE_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
FALSE_CONSTANTS = {"", "0", "OFF", "NO", "FALSE", "N", "IGNORE", "NOTFOUND"}

CMAKE_PLATFORM_VARS = {
    "SMALL_PROBLEM_SIZE": ["ON"],
    "LARGE_PROBLEM_SIZE": ["OFF"],
    "TARGET_OS": ["Linux"],
    "ENDIAN": ["big"],
    "ARCH": ["Dadao"],
    "CMAKE_SYSTEM_NAME": ["Linux"],
    "TEST_SUITE_SUPPRESS_WARNINGS": ["ON"],
    "TEST_SUITE_BENCHMARKING_ONLY": ["OFF"],
    "COMPILER_HAS_NO_DEFINE_TARGET_OS_MACROS": ["ON"],
}


def strip_cmake_comment(line: str) -> str:
    out, quote = [], False
    for ch in line:
        if ch == '"':
            quote = not quote
        if ch == "#" and not quote:
            break
        out.append(ch)
    return "".join(out)


def cmake_commands(text: str):
    """Yield (command, args_string) for each logical CMake command.

    Commands may span lines (ClamAV's multi-line source list, multi-line
    ``set``); the parenthesis depth tells us when the command ends.
    """
    buf, depth = "", 0
    for raw in text.splitlines():
        line = strip_cmake_comment(raw).strip()
        if not buf and not line:
            continue
        buf = (buf + " " + line).strip() if buf else line
        depth += line.count("(") - line.count(")")
        if depth <= 0:
            m = CMAKE_CMD_RE.match(buf)
            if m:
                yield m.group(1).lower(), m.group(2)
            buf, depth = "", 0
    if buf:
        m = CMAKE_CMD_RE.match(buf)
        if m:
            yield m.group(1).lower(), m.group(2)


def cmake_tokens(args: str):
    """Split a CMake argument list the way CMake stores the values.

    A wholly quoted argument (``"-n 30 15 30"``) loses its quotes; quotes
    embedded in an unquoted argument (``-DVERSION="1.00"``) are kept -- that
    is what CMake itself does (verified with cmake 3.28 against this suite's
    FreeBench directive).
    """
    tokens = []
    for token in CMAKE_ARG_RE.findall(args):
        if len(token) >= 2 and token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        tokens.append(token)
    return tokens


def expand_cmake_arg(arg: str, variables) -> list:
    """CMake unquoted ``${VAR}`` expansion: a list becomes several arguments."""
    if "${" not in arg:
        return [arg]
    value = CMAKE_VAR_RE.sub(
        lambda m: ";".join(variables.get(m.group(1), [])), arg)
    return value.split(";")


def cmake_truth(value: str) -> bool:
    return value.upper() not in FALSE_CONSTANTS


class _CondParser:
    """Recursive-descent evaluator for the CMake condition subset in use."""

    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.pos = 0
        self.vars = variables

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        value = self.or_expr()
        if self.pos != len(self.tokens):
            raise ValueError(f"trailing tokens: {self.tokens[self.pos:]}")
        return value

    def or_expr(self):
        value = self.and_expr()
        while self.peek() is not None and self.peek().upper() == "OR":
            self.take()
            rhs = self.and_expr()
            value = value or rhs
        return value

    def and_expr(self):
        value = self.unary()
        while self.peek() is not None and self.peek().upper() == "AND":
            self.take()
            rhs = self.unary()
            value = value and rhs
        return value

    def unary(self):
        tok = self.peek()
        if tok is None:
            raise ValueError("unexpected end of condition")
        if tok.upper() == "NOT":
            self.take()
            return not self.unary()
        if tok.upper() == "DEFINED":
            self.take()
            name = self.take().strip('"')
            return name in self.vars
        return self.comparison()

    def atom_value(self):
        tok = self.take()
        if tok == "(":
            value = self.or_expr()
            self.take()  # ')'
            return "1" if value else "0"
        if tok.startswith('"') and tok.endswith('"'):
            return tok[1:-1]
        return ";".join(self.vars.get(tok, []))

    def comparison(self):
        left = self.atom_value()
        tok = self.peek()
        if tok is not None and tok.upper() in ("STREQUAL", "MATCHES", "EQUAL"):
            op = self.take().upper()
            right = self.atom_value()
            if op == "STREQUAL":
                return left == right
            if op == "MATCHES":
                return re.search(right, left) is not None
            try:
                return float(left) == float(right)
            except ValueError:
                return False
        return cmake_truth(left)


def eval_cmake_condition(expr: str, variables) -> bool:
    expanded = CMAKE_VAR_RE.sub(
        lambda m: ";".join(variables.get(m.group(1), [])), expr)
    tokens = [t for t in CMAKE_ARG_RE.findall(expanded) if t]
    return _CondParser(tokens, variables).parse()


class CMakeConfig:
    """Derived per-program upstream build/run configuration."""

    __slots__ = ("definitions", "cflags", "ldflags", "run_options", "notes",
                 "unresolved", "fp_tolerance", "fp_abstolerance",
                 "fp_ignorewhitespace", "test_data", "include_dirs",
                 "include_dir_decls", "include_dir_source")

    def __init__(self):
        self.definitions = []   # add_definitions / target_compile_options
        self.cflags = []
        self.ldflags = []
        self.run_options = []
        self.notes = []
        self.unresolved = []
        self.include_dirs = []  # include_directories / target_include_directories
        # Which CMakeLists.txt declared each include dir (audit trail).
        self.include_dir_decls = []
        # "cmake" when the -I set comes from upstream's own declarations,
        # "unit-dir-fallback" when the unit declares none (CMake's
        # CMAKE_CURRENT_SOURCE_DIR view, see prepare_cases).
        self.include_dir_source = ""
        # upstream llvm_test_data(): (source file, destination name) pairs that
        # CMake copies next to the executable before the run.
        self.test_data = []
        # upstream's fpcmp knobs (llvm_test_traditional: FP_TOLERANCE,
        # FP_ABSTOLERANCE, FP_IGNOREWHITESPACE)
        self.fp_tolerance = ""
        self.fp_abstolerance = ""
        self.fp_ignorewhitespace = False

    def as_dict(self):
        return dict(cflags=self.cflags, ldflags=self.ldflags,
                    run_options=" ".join(self.run_options),
                    test_data=[d for _s, d in self.test_data],
                    include_dirs=self.include_dirs,
                    include_dir_decls=self.include_dir_decls,
                    include_dir_source=self.include_dir_source,
                    fp_tolerance=self.fp_tolerance,
                    fp_abstolerance=self.fp_abstolerance,
                    fp_ignorewhitespace=self.fp_ignorewhitespace,
                    notes=self.notes, unresolved=self.unresolved)


def derive_cmake_config(suite_root: str, tree_root: str, unit_dir: str):
    """Evaluate the CMakeLists chain ``tree_root -> unit_dir`` (inclusive)."""
    variables = {k: list(v) for k, v in CMAKE_PLATFORM_VARS.items()}
    variables["CMAKE_SOURCE_DIR"] = [suite_root]
    config = CMakeConfig()

    chain = []
    rel = os.path.relpath(unit_dir, tree_root)
    parts = [] if rel == "." else rel.split(os.sep)
    for i in range(len(parts) + 1):
        chain.append(os.path.join(tree_root, *parts[:i]))

    for directory in chain:
        path = os.path.join(directory, "CMakeLists.txt")
        if not os.path.isfile(path):
            continue
        variables["CMAKE_CURRENT_SOURCE_DIR"] = [directory]
        # The driver compiles in a per-case *copy* of this directory, so the
        # source directory is what a generated-header style -I must name.
        variables["CMAKE_CURRENT_BINARY_DIR"] = [directory]
        stack = []  # (parent_active, this_branch_active, branch_taken)

        def active():
            return all(frame[1] for frame in stack)

        for command, argstr in cmake_commands(read_text(path)):
            args = [a for t in cmake_tokens(argstr) for a in
                    expand_cmake_arg(t, variables)]
            try:
                if command in ("if", "elseif"):
                    condition = CMAKE_ARG_RE.findall(argstr)
                    condition = " ".join(condition)
                    truth = eval_cmake_condition(condition, variables)
                    if command == "if":
                        stack.append((active(), truth, truth))
                    else:
                        if not stack:
                            raise ValueError("elseif without if")
                        parent, _cur, taken = stack[-1]
                        branch = (not taken) and truth
                        stack[-1] = (parent, branch, taken or truth)
                elif command == "else":
                    if not stack:
                        raise ValueError("else without if")
                    parent, _cur, taken = stack[-1]
                    stack[-1] = (parent, not taken, True)
                elif command == "endif":
                    if not stack:
                        raise ValueError("endif without if")
                    stack.pop()
                elif not active():
                    continue
                elif command == "set":
                    if not args:
                        raise ValueError("set without variable")
                    variables[args[0]] = args[1:]
                elif command == "list" and args:
                    if args[0].upper() in ("APPEND", "REMOVE") and len(args) > 1:
                        name = args[1]
                        current = list(variables.get(name, []))
                        if args[0].upper() == "APPEND":
                            current.extend(args[2:])
                        else:
                            current = [a for a in current if a not in args[2:]]
                        variables[name] = current
                elif command == "add_definitions":
                    config.definitions.extend(args)
                elif command in ("include_directories",
                                 "target_include_directories"):
                    # Upstream's own -I set (archie-client's <copyright.h>,
                    # Burg's BINARY_DIR); target_include_directories' PRIVATE/
                    # PUBLIC/... keywords are qualifiers, not paths.
                    #
                    # CMake resolves a relative include dir against the
                    # *current source dir* of the CMakeLists that declares
                    # it, and ${CMAKE_CURRENT_SOURCE_DIR} has already been
                    # expanded above; a leftover ${...} is an unexpanded
                    # variable, i.e. a path the driver cannot derive -- that
                    # must surface as ``blocked``, never as a literal -I.
                    dirs = list(args)
                    if command == "target_include_directories":
                        dirs = dirs[1:]
                    for d in dirs:
                        if d in ("PRIVATE", "PUBLIC", "INTERFACE",
                                 "SYSTEM", "BEFORE", "AFTER"):
                            continue
                        if "${" in d:
                            raise ValueError(
                                f"unexpanded variable in include dir {d!r}")
                        resolved = d if os.path.isabs(d) else \
                            os.path.join(directory, d)
                        resolved = os.path.normpath(resolved)
                        if resolved in config.include_dirs:
                            continue
                        rel_cml = os.path.relpath(path, suite_root)
                        config.include_dirs.append(resolved)
                        config.include_dir_decls.append(
                            f"{rel_cml}:({command})")
                elif command == "llvm_test_data":
                    # TestSuite.cmake: llvm_test_data(<target> [MUST_COPY]
                    #   [SOURCE_DIR <dir>] [DEST_SUFFIX <s>] <file>...)
                    # copies the named inputs next to the executable (the
                    # directory RUN_OPTIONS' WORKDIR %S selects).
                    if not args:
                        raise ValueError("llvm_test_data without target")
                    source_dir = variables["CMAKE_CURRENT_SOURCE_DIR"][0]
                    dest_suffix = ""
                    rest = list(args[1:])
                    i = 0
                    while i < len(rest):
                        arg = rest[i]
                        if arg == "MUST_COPY":
                            i += 1
                            continue
                        if arg in ("SOURCE_DIR", "DEST_SUFFIX"):
                            if i + 1 >= len(rest):
                                raise ValueError(f"{arg} without value")
                            if arg == "SOURCE_DIR":
                                source_dir = rest[i + 1]
                            else:
                                dest_suffix = rest[i + 1]
                            i += 2
                            continue
                        config.test_data.append(
                            (os.path.join(source_dir, arg),
                             arg + dest_suffix))
                        i += 1
                elif command == "target_compile_options":
                    config.definitions.extend(
                        a for a in args[1:]
                        if a not in ("PRIVATE", "PUBLIC", "INTERFACE"))
            except ValueError as exc:
                config.unresolved.append(f"{path}: ({command} {argstr[:80]}) "
                                         f"-> {exc}")
            except Exception as exc:  # noqa: BLE001 - never guess silently
                config.unresolved.append(f"{path}: ({command} {argstr[:80]}) "
                                         f"-> {type(exc).__name__}: {exc}")
        if stack:
            config.unresolved.append(f"{path}: unbalanced if/endif")

    config.cflags = (list(config.definitions)
                     + list(variables.get("CFLAGS", []))
                     + list(variables.get("CPPFLAGS", [])))
    config.ldflags = list(variables.get("LDFLAGS", []))
    config.run_options = list(variables.get("RUN_OPTIONS", []))
    config.fp_tolerance = " ".join(variables.get("FP_TOLERANCE", []))
    config.fp_abstolerance = " ".join(variables.get("FP_ABSTOLERANCE", []))
    config.fp_ignorewhitespace = cmake_truth(
        "".join(variables.get("FP_IGNOREWHITESPACE", [])))
    return config


# ---------------------------------------------------------------------------
# enumeration
# ---------------------------------------------------------------------------
class Case:
    __slots__ = ("cid", "tree", "kind", "unit_dir", "sources", "target",
                 "cmake", "run_argv", "stdin_name", "oracle",
                 "oracle_kind", "oracle_path", "expected_exit",
                 "expected_doc", "expected_hash", "klass", "exit",
                 "reason", "first_error", "elf", "min_pt_load", "interp",
                 "compile_cmds", "link_cmd", "run_cmd", "outdir", "stdout",
                 "seconds", "compare", "compare_cmd",
                 "stdout_sha256", "stdout_size", "tls_hits",
                 "known_fail_basis", "known_fail_evidence", "notes",
                 "run_seconds", "run_timeout")

    def __init__(self, cid, tree, kind, unit_dir, sources, target=None):
        self.cid = cid
        self.tree = tree
        self.kind = kind                 # "single" | "multi"
        self.unit_dir = unit_dir
        self.sources = sources
        self.target = target or os.path.basename(unit_dir)
        self.cmake = None
        self.run_argv = []
        self.stdin_name = None
        self.oracle = None
        self.oracle_kind = "none"        # stdout | md5 | raw | none
        self.oracle_path = ""
        self.expected_exit = 0
        self.expected_doc = b""
        self.expected_hash = ""
        self.klass = "blocked"
        self.exit = None
        self.reason = ""
        self.first_error = ""
        self.elf = ""
        self.min_pt_load = None
        self.interp = ""
        self.compile_cmds = []
        self.link_cmd = []
        self.run_cmd = []
        self.outdir = ""
        self.stdout = b""
        self.seconds = 0.0
        self.compare = "bytes"           # "bytes" | "fpcmp"
        self.compare_cmd = []
        self.stdout_sha256 = ""
        self.stdout_size = 0
        self.tls_hits = []
        self.known_fail_basis = ""
        self.known_fail_evidence = ""
        self.notes = []
        self.run_seconds = 0.0   # guest run wall clock (timeout-table basis)
        self.run_timeout = None  # effective run timeout used for this case

    def as_dict(self, mode):
        return dict(mode=mode, case=self.cid, tree=self.tree, kind=self.kind,
                    unit_dir=self.unit_dir, target=self.target,
                    sources=[os.path.relpath(s, self.unit_dir) for s in
                             self.sources],
                    klass=self.klass, exit=self.exit,
                    expected_exit=self.expected_exit,
                    reason=self.reason, first_error=self.first_error,
                    oracle_kind=self.oracle_kind,
                    oracle_file=self.oracle_path,
                    stdout_sha256=self.stdout_sha256,
                    stdout_size=self.stdout_size,
                    seconds=round(self.seconds, 2),
                    compare=self.compare, compare_cmd=self.compare_cmd,
                    elf=self.elf,
                    run_seconds=round(self.run_seconds, 2),
                    run_timeout=self.run_timeout,
                    min_pt_load=(None if self.min_pt_load is None
                                 else hex(self.min_pt_load)),
                    pt_interp=self.interp,
                    known_fail_basis=self.known_fail_basis,
                    known_fail_evidence=self.known_fail_evidence,
                    tls_hits=self.tls_hits,
                    compile_cmd=self.compile_cmds,
                    link_cmd=self.link_cmd, run_cmd=self.run_cmd,
                    cmake=self.cmake.as_dict() if self.cmake else None,
                    notes=self.notes, work_dir=self.outdir)


def has_main(path: str) -> bool:
    return bool(MAIN_RE.search(read_text(path)))


def multi_target_name(unit_dir: str) -> str:
    """Upstream's TEST_NAME: the ``llvm_multisource(<target> ...)`` argument."""
    path = os.path.join(unit_dir, "CMakeLists.txt")
    if os.path.isfile(path):
        for command, argstr in cmake_commands(read_text(path)):
            if command != "llvm_multisource":
                continue
            tokens = cmake_tokens(argstr)
            if tokens:
                return tokens[0]
    return os.path.basename(unit_dir)


def curated_sources(unit_dir: str, target: str):
    """Upstream's ``llvm_multisource(<target> <sources...>)`` list, if any."""
    path = os.path.join(unit_dir, "CMakeLists.txt")
    if not os.path.isfile(path):
        return None
    variables = {k: list(v) for k, v in CMAKE_PLATFORM_VARS.items()}
    variables["CMAKE_CURRENT_SOURCE_DIR"] = [unit_dir]
    variables["CMAKE_SOURCE_DIR"] = [unit_dir]
    for command, argstr in cmake_commands(read_text(path)):
        if command == "set" or command == "list":
            args = [a for t in cmake_tokens(argstr) for a in
                    expand_cmake_arg(t, variables)]
            if command == "set" and args:
                variables[args[0]] = args[1:]
            elif args and args[0].upper() == "APPEND" and len(args) > 1:
                variables.setdefault(args[1], []).extend(args[2:])
            continue
        if command != "llvm_multisource":
            continue
        args = [a for t in cmake_tokens(argstr) for a in
                expand_cmake_arg(t, variables)]
        if not args or args[0] != target:
            continue
        listed = [a for a in args[1:] if a.endswith(".c")]
        if not listed:
            return None
        resolved = []
        for item in listed:
            path = item if os.path.isabs(item) else os.path.join(unit_dir, item)
            resolved.append(os.path.normpath(path))
        return resolved
    return None


def discover(suite_root: str):
    """Return (cases, census) with scope A live counts and B/C census."""
    cases = []
    seen = set()

    # A1: SingleSource/Benchmarks, one case per .c carrying main.
    single_root = os.path.join(suite_root, "SingleSource", "Benchmarks")
    single_files = sorted(glob.glob(os.path.join(single_root, "**", "*.c"),
                                    recursive=True))
    single_units = [p for p in single_files if has_main(p)]
    for path in single_units:
        cid = os.path.relpath(path, suite_root).replace(os.sep, "/")[:-2]
        cases.append(Case(cid, "SingleSource/Benchmarks", "single",
                          os.path.dirname(path), [path],
                          os.path.splitext(os.path.basename(path))[0]))
    for case in cases:
        if case.cid == POLYBENCH_TEMPLATE:
            case.notes.append(
                "upstream's Polybench template: Polybench/utilities/ has no "
                "CMakeLists.txt, so upstream never builds it; counted by the "
                "book's .c-with-main rule and executed here")

    # A2: MultiSource trees, one case per program directory.
    multi_dirs = {}
    for tree in A_MULTI_TREES:
        root = os.path.join(suite_root, tree)
        found = []
        for directory, _dirs, files in os.walk(root):
            c_files = sorted(f for f in files if f.endswith(".c"))
            if not c_files:
                continue
            if not any(has_main(os.path.join(directory, f)) for f in c_files):
                continue
            found.append(directory)
        # A nested program directory would be a second main in the parent's
        # target; none exists in the locked corpus -- assert instead of guess.
        found.sort()
        for a, b in zip(found, found[1:]):
            if b.startswith(a + os.sep):
                raise SetupError(f"nested program directories: {a} / {b}")
        multi_dirs[tree] = found
        for directory in found:
            if directory in seen:
                raise SetupError(f"duplicate program directory: {directory}")
            seen.add(directory)
            target = multi_target_name(directory)
            sources = curated_sources(directory, target)
            listing = os.path.join(directory, "CMakeLists.txt")
            if sources is None:
                sources = sorted(glob.glob(os.path.join(directory, "*.c")))
                if os.path.isfile(listing):
                    note = ("TU set: upstream's llvm_multisource() names no "
                            "source list; all immediate *.c compiled together")
                else:
                    note = ("TU set: no CMakeLists.txt; all immediate *.c "
                            "compiled together")
            else:
                note = (f"TU set: upstream llvm_multisource({target} ...) "
                        f"curated list")
            cid = os.path.relpath(directory, suite_root).replace(os.sep, "/")
            case = Case(cid, tree, "multi", directory, sources, target)
            case.notes.append(note)
            if cid in UPSTREAM_SMALL_PRUNE:
                case.notes.append(UPSTREAM_SMALL_PRUNE[cid])
            cases.append(case)

    cases.sort(key=lambda c: c.cid)

    # Declared structural exclusions (TESTCASES-050t item 4): removed from the
    # executed set, counted live, and every declared id must still reproduce --
    # a registry entry that no longer matches a discovered unit is a FAIL, not
    # a silent no-op.
    excluded = []
    kept = []
    for case in cases:
        reason = STRUCTURAL_EXCLUSIONS.get(case.cid)
        if reason is None:
            kept.append(case)
        else:
            excluded.append((case.cid, reason))
    cases = kept
    unmatched_exclusions = sorted(set(STRUCTURAL_EXCLUSIONS)
                                  - {cid for cid, _r in excluded})

    # A round census: recomputed from the same raw scans, never from len().
    census = {}
    census["a_single_c_files"] = len(single_files)
    census["a_single_units"] = len(single_units)
    audit = {
        "a_single_c_files": len(single_files),
        "a_single_units": len(single_units),
        "a_single_units_without_main": len(single_files) - len(single_units),
        "a_multi_units": {tree: len(multi_dirs[tree])
                          for tree in A_MULTI_TREES},
    }
    # ``a_units`` = executed set; ``a_discovered`` = raw enumeration, so
    # ``total == discovered - excluded`` can be checked from the JSON.
    census["a_units"] = len(cases)
    census["a_discovered"] = len(cases) + len(excluded)
    census["a_excluded"] = [dict(id=cid, reason=reason)
                            for cid, reason in excluded]
    census["a_unmatched_exclusions"] = unmatched_exclusions
    census["a_audit"] = audit

    # B: counted, declared not run.
    def count_single_with_main(tree):
        root = os.path.join(suite_root, tree)
        files = glob.glob(os.path.join(root, "**", "*.c"), recursive=True)
        return len(files), sum(1 for p in files if has_main(p))

    def count_multi_units(tree):
        root = os.path.join(suite_root, tree)
        units = 0
        for directory, _dirs, files in os.walk(root):
            c_files = [f for f in files if f.endswith(".c")]
            if c_files and any(has_main(os.path.join(directory, f))
                               for f in c_files):
                units += 1
        return units

    b = {}
    for tree in B_TREES:
        if tree.startswith("SingleSource/"):
            total, with_main = count_single_with_main(tree)
            b[tree] = dict(rule=".c translation unit with main",
                           c_files=total, units=with_main)
        else:
            b[tree] = dict(rule="program directory (immediate .c with main)",
                           units=count_multi_units(tree))
    census["b"] = b
    census["b_units"] = sum(v["units"] for v in b.values())

    # C: structural exclusions, live counts.
    external_root = os.path.join(suite_root, "External")
    external_c = glob.glob(os.path.join(external_root, "**", "*.c"),
                           recursive=True)
    suffix_counts = {}
    for tree in SCAN_TREES:
        for path in glob.glob(os.path.join(suite_root, tree, "**", "*"),
                              recursive=True):
            if not os.path.isfile(path):
                continue
            suffix = os.path.splitext(path)[1]
            if suffix in C_SUFFIXES:
                suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
    micro_root = os.path.join(suite_root, "MicroBenchmarks")
    micro_c = glob.glob(os.path.join(micro_root, "**", "*.c"), recursive=True)
    c = {
        "External": dict(rule="user ruling 2026-10-15: excluded",
                         c_files=len(external_c),
                         units_with_main=sum(1 for p in external_c
                                             if has_main(p))),
        "non-c-suffixes": dict(rule="no C++ stdlib in sysroot / no Fortran "
                                    "front end", counts=suffix_counts,
                               total=sum(suffix_counts.values())),
        "MicroBenchmarks": dict(rule="no .c with main (0 objects this batch)",
                                c_files=len(micro_c),
                                units_with_main=sum(1 for p in micro_c
                                                    if has_main(p))),
    }
    census["c"] = c

    # Census self-check: the executed set plus the declared exclusions must be
    # exactly the raw A enumeration.
    expected = (audit["a_single_units"]
                + sum(audit["a_multi_units"].values()))
    census["a_census_ok"] = (len(cases) + len(excluded) == expected
                             and not unmatched_exclusions)
    return cases, excluded, census


# ---------------------------------------------------------------------------
# oracle
# ---------------------------------------------------------------------------
def reference_for(case: Case):
    """Upstream reference output, same precedence as llvm_test_traditional."""
    base = os.path.join(case.unit_dir, case.target)
    for suffix in (".reference_output.small", ".reference_output.big-endian",
                   ".reference_output"):
        path = base + suffix
        if os.path.isfile(path):
            return path
    return None


def load_oracle(case: Case, suite_root: str):
    """Fill case.oracle_* from upstream's reference file (or leave exit-only).

    Upstream's reference *is* the whole output file produced by RunSafely:
    the program's interleaved stdout+stderr plus a bare ``exit N\\n`` tail
    (RunSafely.sh:257; no separator is inserted, so a binary program's last
    byte is glued to ``exit``).  The hash form (``HASH_PROGRAM_OUTPUT``)
    hashes that same file, so its reference is a single md5 line.
    """
    path = reference_for(case)
    if path is None:
        case.oracle_kind = "none"
        case.expected_exit = 0
        case.notes.append("oracle: exit-only (no upstream reference output; "
                          "NOT an output-equivalence verdict)")
        return
    case.oracle = path
    case.oracle_path = os.path.relpath(path, suite_root).replace(os.sep, "/")
    with open(path, "rb") as fh:
        data = fh.read()
    tail = EXIT_TAIL_RE.search(data)
    if tail:
        case.expected_exit = int(tail.group(1))
    text = None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    if text is not None and len(text.strip().splitlines()) == 1 \
            and HEX32_RE.match(text.strip()):
        case.oracle_kind = "md5"
        case.expected_hash = text.strip()
        # The hash pins the whole document including RunSafely's "exit N"
        # tail, so the expected exit code cannot be read out of this form.
        case.expected_exit = None
        return
    case.expected_doc = data
    case.oracle_kind = "stdout" if text is not None else "raw"


def parse_run_options(case: Case, cmake: CMakeConfig):
    """Turn upstream's RUN_OPTIONS shell fragment into argv + stdin file."""
    fragment = " ".join(cmake.run_options).replace("%S", case.unit_dir)
    try:
        tokens = shlex.split(fragment)
    except ValueError as exc:
        cmake.unresolved.append(f"RUN_OPTIONS {fragment!r}: {exc}")
        return
    argv = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "<":
            i += 1
            if i >= len(tokens):
                cmake.unresolved.append(f"RUN_OPTIONS {fragment!r}: '<' "
                                        f"without file")
                return
            target = tokens[i]
            path = target if os.path.isabs(target) else os.path.join(
                case.unit_dir, target)
            if not os.path.isfile(path):
                cmake.unresolved.append(f"RUN_OPTIONS input not found: "
                                        f"{target}")
                return
            case.stdin_name = target
            i += 1
            continue
        if token in (">", ">>", "2>", "2>&1", "|", "&&"):
            cmake.unresolved.append(f"RUN_OPTIONS {fragment!r}: unsupported "
                                    f"shell operator {token!r}")
            return
        argv.append(token)
        i += 1
    case.run_argv = argv


# ---------------------------------------------------------------------------
# build / run
# ---------------------------------------------------------------------------
def _slug(cid: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", cid)


def copy_unit_tree(case: Case, run_dir: str):
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(case.unit_dir, run_dir)


def platform_gap_reason(case: Case, actual_doc: bytes):
    """Declared run-completion gap whose live signature is present, if any.

    Returns (reason, matched_line) or None.  The matched line becomes the
    case's ``first_error`` so the record carries the program's own diagnostic.
    """
    gap = PLATFORM_GAP_SIGNATURES.get(case.cid)
    if not gap:
        return None
    signature, reason = gap
    if signature not in actual_doc:
        return None
    text = actual_doc.decode("utf-8", errors="replace")
    line = next((ln.strip() for ln in text.splitlines()
                 if signature.decode() in ln), "")
    return reason, line


def _build_and_run(case: Case, cfg, work_dir):
    """Compile -> link -> check image shape -> run -> classify one case."""
    outdir = os.path.join(work_dir, cfg["mode"], _slug(case.cid))
    run_dir = os.path.join(outdir, "run")
    objdir = os.path.join(outdir, "obj")
    case.outdir = outdir
    case.tls_hits = [os.path.relpath(p, case.unit_dir).replace(os.sep, "/")
                     for p in case.sources if TLS_RE.search(read_text(p))]
    if case.cmake is not None and case.cmake.unresolved:
        case.klass = "blocked"
        case.reason = ("upstream CMake configuration not derivable: "
                       + "; ".join(case.cmake.unresolved)[:400])
        return case

    try:
        copy_unit_tree(case, run_dir)
        shutil.rmtree(objdir, ignore_errors=True)
        os.makedirs(objdir, exist_ok=True)
        # Upstream llvm_test_data() copies inputs into the target directory;
        # RUN_OPTIONS then names them relatively (mediabench's testimg.ppm /
        # mei16v2.m2v live in ../data, not in the program directory).
        for src_path, dest_name in (case.cmake.test_data if case.cmake else []):
            dest = os.path.join(run_dir, dest_name)
            if os.path.isdir(src_path):
                shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(src_path, dest)
            elif os.path.isfile(src_path):
                parent = os.path.dirname(dest)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                shutil.copyfile(src_path, dest)
            else:
                raise FileNotFoundError(
                    f"upstream llvm_test_data source missing: {src_path}")
    except OSError as exc:
        case.klass = "blocked"
        case.reason = f"work-tree setup failed: {exc}"
        return case

    # ISS-276: a path the program names in its *config file* never appears in
    # RUN_OPTIONS, so the scan below cannot see it; CASE_PREPARE_DIRS holds
    # the explicit list.  Creating the directory changes no expectation -- the
    # oracle and classification stay as they are.
    for rel_dir in CASE_PREPARE_DIRS.get(case.cid, ()):
        target = os.path.join(run_dir, rel_dir)
        try:
            os.makedirs(target, exist_ok=True)
        except OSError as exc:
            case.klass = "blocked"
            case.reason = (f"work-tree setup failed: cannot create "
                           f"{rel_dir}/: {exc}")
            return case
        case.notes.append(f"created run-dir directory {rel_dir}/ "
                          "(declared in the program's config file)")

    # Upstream's WORKDIR %S lets programs write next to the sources; a path in
    # RUN_OPTIONS whose parent directory does not exist in the corpus (e.g.
    # JM/ldecod's 'Output/test_dec.yuv') is created in the per-case copy, never
    # in the read-only corpus.
    for token in case.run_argv:
        if token.startswith("-") or "=" in token or "/" not in token:
            continue
        parent = os.path.dirname(os.path.join(run_dir, token))
        if parent and not os.path.isdir(parent):
            try:
                os.makedirs(parent, exist_ok=True)
                case.notes.append(f"created run-dir output path "
                                  f"{os.path.relpath(parent, run_dir)}/")
            except OSError:
                pass

    if case.cid in CASE_PREPARE:
        command, why = CASE_PREPARE[case.cid]
        rc, out, err_b, timed = run_bytes(command, timeout=BUILD_TIMEOUT,
                                          cwd=run_dir)
        if timed or rc != 0:
            case.klass = "blocked"
            detail = (err_b or out).decode("utf-8", errors="replace").strip()
            case.reason = (f"run-input generation failed ({' '.join(command)}, "
                           f"rc={rc}): {why}; {detail[:200]}")
            return case
        case.notes.append(f"run inputs generated: {' '.join(command)} ({why})")

    inc_flags = []
    if case.cmake:
        for directory in case.cmake.include_dirs:
            inc_flags += ["-I", directory]
    flags = (["-target", TARGET] + cfg["musl_incs"] + inc_flags
             + list(BASE_CFLAGS) + list(SMALL_PROBLEM_CFLAGS)
             + (list(DYNAMIC_USER_CFLAGS) if cfg["mode"] == "dynamic" else [])
             + (case.cmake.cflags if case.cmake else []))
    objs = []
    for idx, src in enumerate(case.sources):
        obj = os.path.join(objdir, f"{idx:03d}_"
                                   f"{os.path.splitext(os.path.basename(src))[0]}.o")
        cmd = [cfg["clang"]] + flags + ["-c", src, "-o", obj]
        case.compile_cmds.append(cmd)
        rc, _out, err_b, timed = run_bytes(cmd, timeout=BUILD_TIMEOUT,
                                          cwd=run_dir)
        err = err_b.decode("utf-8", errors="replace")
        if timed or rc != 0:
            case.first_error = first_tool_error(err)
            hit = next((p for p in ISS246_PATTERNS if p in err), None)
            if hit and case.tls_hits:
                case.klass = "known-fail"
                case.known_fail_basis = ISS246_ID
                case.known_fail_evidence = (
                    f"live TLS scan hit {case.tls_hits}; clang diagnostic "
                    f"{hit!r} (rc={rc} on {os.path.basename(src)})")
                case.reason = (f"{ISS246_ID} {hit!r}: {case.first_error} "
                               f"(clang rc={rc} on {os.path.basename(src)})")
            elif timed:
                case.klass = "blocked"
                case.reason = (f"compile timeout after {BUILD_TIMEOUT}s on "
                               f"{os.path.basename(src)}")
            else:
                case.klass = "blocked"
                case.reason = (f"compile error rc={rc} on "
                               f"{os.path.basename(src)}: "
                               f"{case.first_error[:240]}")
            return case
        objs.append(obj)

    elf = os.path.join(outdir, case.target + ".elf")
    # musl static archive and compiler-rt builtins reference each other
    # (libc's long-double helpers call builtins and vice versa), so they are
    # linked as one lld group; without builtins, complex-arithmetic programs
    # (mandel, RSBench) fail with "undefined symbol: __muldc3/__divdc3".
    libs = ["--start-group", cfg["libc"], cfg["builtins"], "--end-group"]
    if cfg["mode"] == "static":
        link = [cfg["ldlld"], "-o", elf, cfg["crt1"]] + objs + libs
    else:
        link = ([cfg["ldlld"], "-o", elf, cfg["crt1"]] + objs + libs
                + ["-dynamic-linker", DYNAMIC_LINKER])
    case.link_cmd = link
    rc, _out, err_b, timed = run_bytes(link, timeout=BUILD_TIMEOUT, cwd=run_dir)
    if timed or rc != 0:
        case.klass = "blocked"
        if timed:
            case.reason = f"link timeout after {BUILD_TIMEOUT}s"
        else:
            case.first_error = first_tool_error(
                err_b.decode("utf-8", errors="replace"))
            case.reason = f"link error rc={rc}: {case.first_error[:240]}"
        return case
    case.elf = elf

    # Image-shape checks straight from the file (ISS-247 base + modality).
    try:
        case.min_pt_load = min_pt_load(elf)
        case.interp = pt_interp(elf).decode("utf-8", errors="replace") \
            .rstrip("\0")
        dynamic = has_pt_dynamic(elf)
    except ValueError as exc:
        case.klass = "blocked"
        case.reason = f"ELF parse failed: {exc}"
        return case
    if case.min_pt_load == SCRIPTED_BASE:
        case.klass = "blocked"
        case.reason = ("ELF min PT_LOAD is the scripted dadao.lds base "
                       f"0x{SCRIPTED_BASE:x} (ISS-247)")
        return case
    if cfg["mode"] == "static" and case.interp:
        case.klass = "blocked"
        case.reason = f"static image carries PT_INTERP {case.interp!r}"
        return case
    if cfg["mode"] == "static" and dynamic:
        case.klass = "blocked"
        case.reason = ("static image carries PT_DYNAMIC (library on the link "
                       "line is a shared object, not an archive)")
        return case
    if cfg["mode"] == "dynamic" and case.interp != DYNAMIC_LINKER:
        case.klass = "blocked"
        case.reason = (f"dynamic image PT_INTERP {case.interp!r} != "
                       f"{DYNAMIC_LINKER!r}")
        return case
    if cfg["mode"] == "dynamic" and not dynamic:
        case.klass = "blocked"
        case.reason = ("dynamic image has no PT_DYNAMIC (library on the link "
                       "line is an archive, not libc.so)")
        return case

    cmd = [cfg["qemu"]]
    if cfg["mode"] == "dynamic":
        cmd += ["-L", cfg["guest_root"]]
    cmd += [elf] + list(case.run_argv)
    case.run_cmd = cmd
    stdin_path = (os.path.join(run_dir, case.stdin_name)
                  if case.stdin_name else None)
    # Per-case timeout table (TESTCASES-050t): five programs are genuinely slow
    # and were truncated at 300 s in TESTCASES-048t; their measured durations
    # widen the budget for those cases only.  ``--timeout`` remains a floor.
    case.run_timeout = max(cfg["timeout"], CASE_TIMEOUTS.get(case.cid, 0))
    run_started = time.monotonic()
    rc, stdout, timed = run_stream(
        cmd, os.path.join(outdir, "combined.out"), timeout=case.run_timeout,
        cwd=run_dir, stdin_path=stdin_path)
    case.run_seconds = time.monotonic() - run_started
    case.stdout = stdout
    case.stdout_sha256 = sha256_bytes(stdout)
    case.stdout_size = len(stdout)
    if timed:
        case.klass = "blocked"
        case.reason = (f"timeout after {case.run_timeout}s (blocked, not "
                       f"pass/fail)")
        case.first_error = first_output_line(stdout, b"")
        return case
    if rc is None:
        case.klass = "blocked"
        case.reason = "qemu did not return an exit code"
        return case
    if rc < 0:
        case.klass = "blocked"
        case.reason = f"qemu killed by host signal {-rc}"
        issue = QEMU_SIGNAL_ISSUES.get(case.cid)
        if issue:
            case.reason += f" (qemu-user crash; see {issue})"
        case.first_error = first_output_line(stdout, b"")
        return case
    case.exit = rc
    case.first_error = first_output_line(stdout, b"")

    if case.oracle_kind == "none":
        if rc == case.expected_exit:
            case.klass = "pass"
            case.reason = (f"exit {rc}; exit-only (expected "
                           f"{case.expected_exit}), NOT an output-equivalence "
                           f"verdict; output sha256 recorded")
        else:
            case.klass = "fail"
            case.reason = (f"guest exit {rc}, expected {case.expected_exit} "
                           f"(exit-only oracle); first output: "
                           f"{case.first_error[:200]}")
        return case

    # Upstream's comparison unit is the whole output file: the interleaved
    # stdout+stderr plus the bare ``exit N\n`` tail RunSafely appends.
    actual_doc = stdout + (b"exit %d\n" % rc)

    if case.oracle_kind == "md5":
        actual = hashlib.md5(actual_doc).hexdigest()
        # The upstream hash (HASH_PROGRAM_OUTPUT, HashProgramOutput.sh) covers
        # the whole output file, *including* RunSafely's bare "exit N" tail.
        # A matching hash therefore already pins the exit code; requiring a
        # guest exit of 0 on top of it false-fails baselines that exit non-zero
        # (gnugo's reference is md5(output+"exit 1\n")).
        if actual == case.expected_hash:
            case.klass = "pass"
            case.reason = (f"md5(output+exit) == {case.expected_hash} "
                           f"({case.oracle_path}); exit {rc} is part of the "
                           f"hashed document")
        else:
            gap = platform_gap_reason(case, actual_doc)
            if gap:
                case.klass = "blocked"
                case.reason = (f"blocked: the run completed (exit {rc}) "
                               f"but cannot reach the oracle -- {gap[0]}")
                case.first_error = gap[1] or case.first_error
                return case
            case.klass = "fail"
            case.reason = (f"oracle mismatch ({case.oracle_path}): "
                           f"md5(output+exit)={actual} expected "
                           f"{case.expected_hash}, exit {rc} (the exit code is "
                           f"inside the hashed document)")
        return case

    # Reference form: upstream compares the whole output document.  When the
    # program's CMake sets FP_TOLERANCE/FP_ABSTOLERANCE/FP_IGNOREWHITESPACE,
    # upstream compares with fpcmp (its own tool, built here from the locked
    # corpus' tools/fpcmp.c with the host compiler) -- byte equality would be
    # stricter than upstream and would turn float formatting differences into
    # false failures.
    fp = case.cmake
    use_fpcmp = bool(fp and (fp.fp_tolerance or fp.fp_abstolerance
                             or fp.fp_ignorewhitespace)
                     and cfg.get("fpcmp"))
    if use_fpcmp:
        actual_path = os.path.join(outdir, "actual.out")
        with open(actual_path, "wb") as fh:
            fh.write(actual_doc)
        cmd = [cfg["fpcmp"]]
        if fp.fp_tolerance:
            cmd += ["-r", fp.fp_tolerance]
        if fp.fp_abstolerance:
            cmd += ["-a", fp.fp_abstolerance]
        if fp.fp_ignorewhitespace:
            cmd += ["-i"]
        cmd += [actual_path, case.oracle]
        case.compare = "fpcmp"
        case.compare_cmd = cmd
        _rc, _out, _err, timed = run_bytes(cmd, timeout=60)
        matched = (not timed and _rc == 0)
    else:
        matched = actual_doc == case.expected_doc

    if matched:
        case.klass = "pass"
        label = "raw output+exit" if case.oracle_kind == "raw" \
            else "output+exit"
        how = "fpcmp" if use_fpcmp else "byte-exact"
        case.reason = (f"{label} ({case.oracle_path}): matched ({how}), "
                       f"exit {rc}")
    else:
        gap = platform_gap_reason(case, actual_doc)
        if gap:
            case.klass = "blocked"
            case.reason = (f"blocked: the run completed (exit {rc}) but "
                           f"cannot reach the oracle -- {gap[0]}")
            case.first_error = gap[1] or case.first_error
            return case
        case.klass = "fail"
        detail = []
        if not use_fpcmp and actual_doc != case.expected_doc:
            detail.append(f"output differs ({len(actual_doc)} B vs "
                          f"{len(case.expected_doc)} B, sha256 "
                          f"{sha256_bytes(actual_doc)[:16]})")
        if use_fpcmp:
            detail.append("fpcmp reported a difference "
                          f"(tolerance={fp.fp_tolerance or '-'} "
                          f"abstol={fp.fp_abstolerance or '-'} "
                          f"ignore-ws={fp.fp_ignorewhitespace})")
        if rc != case.expected_exit:
            detail.append(f"exit {rc} != {case.expected_exit}")
        if rc in FAULT_NAMES:
            detail.append(f"machine fault {FAULT_NAMES[rc]} (0x{rc:02X}, "
                          f"ADR-0004 D5.8)")
        case.reason = (f"oracle mismatch ({case.oracle_path}): "
                       + "; ".join(detail)
                       + f"; first output: {case.first_error[:160]}")
    return case


def build_and_run(case: Case, cfg, work_dir):
    """Time one case (the wall-clock evidence behind the duration estimate)."""
    started = time.monotonic()
    try:
        return _build_and_run(case, cfg, work_dir)
    finally:
        case.seconds = time.monotonic() - started


# ---------------------------------------------------------------------------
# known-fail audit
# ---------------------------------------------------------------------------
def iss246_evidence(case: Case):
    """Recompute the ISS-246 basis for one case; return (ok, evidence)."""
    if not case.tls_hits:
        return False, "no live TLS declaration in the case's own sources"
    if not any(p in case.first_error for p in ISS246_PATTERNS):
        return False, (f"first diagnostic is not the TLS one: "
                       f"{case.first_error or '(none)'}")
    return True, (f"live TLS scan hit {case.tls_hits}; diagnostic "
                  f"{next(p for p in ISS246_PATTERNS if p in case.first_error)!r}")


def iss265_host_prng_sequences():
    """Host libc's ``random()``/``rand()`` sequences after seed 1 (live)."""
    try:
        libc = ctypes.CDLL(None)
        libc.srandom.argtypes = [ctypes.c_uint]
        libc.random.restype = ctypes.c_long
        libc.srand.argtypes = [ctypes.c_uint]
        libc.rand.restype = ctypes.c_int
        libc.srandom(1)
        seq_random = (libc.random(), libc.random())
        libc.srand(1)
        seq_rand = (libc.rand(), libc.rand())
    except (OSError, AttributeError) as exc:
        return None, f"host libc has no random()/rand(): {exc}"
    return {"random": seq_random, "rand": seq_rand}, ""


def iss265_prng_sequences(cfg, cache):
    """Guest musl vs host glibc PRNG sequences (live, one probe per round).

    The probe is compiled with the same clang/target/musl headers and linked
    against the same ``cfg['libc']`` as the suite, then run under the same
    qemu, so the guest numbers come from the library actually under test.  The
    host numbers come from this process' own libc (glibc on the reference
    host).  Result: ``(dict(guest=..., host=...), "")`` or ``(None, why)``.
    """
    key = (cfg.get("mode"), cfg.get("libc"))
    if key in cache:
        return cache[key]
    host, host_err = iss265_host_prng_sequences()
    if host is None:
        cache[key] = (None, host_err)
        return cache[key]
    probe_dir = os.path.join(cfg["work_dir"], f"iss265-prng-{cfg['mode']}")
    src = os.path.join(probe_dir, "iss265_prng_probe.c")
    obj = os.path.join(probe_dir, "iss265_prng_probe.o")
    elf = os.path.join(probe_dir, "iss265_prng_probe.elf")

    def fail(why):
        cache[key] = (None, why)
        return cache[key]

    try:
        os.makedirs(probe_dir, exist_ok=True)
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(ISS265_PRNG_PROBE)
    except OSError as exc:
        return fail(f"cannot write PRNG probe: {exc}")
    compile_cmd = ([cfg["clang"], "-target", TARGET] + cfg["musl_incs"]
                   + list(BASE_CFLAGS) + ["-c", src, "-o", obj])
    rc, _out, err_b, timed = run_bytes(compile_cmd, timeout=BUILD_TIMEOUT,
                                       cwd=probe_dir)
    if timed or rc != 0:
        return fail(f"PRNG probe compile failed rc={rc}: "
                    f"{first_tool_error(err_b.decode('utf-8', 'replace'))}")
    link_cmd = ([cfg["ldlld"], "-o", elf, cfg["crt1"], obj,
                 "--start-group", cfg["libc"], cfg["builtins"], "--end-group"])
    if cfg["mode"] == "dynamic":
        link_cmd += ["-dynamic-linker", DYNAMIC_LINKER]
    rc, _out, err_b, timed = run_bytes(link_cmd, timeout=BUILD_TIMEOUT,
                                       cwd=probe_dir)
    if timed or rc != 0:
        return fail(f"PRNG probe link failed rc={rc}: "
                    f"{first_tool_error(err_b.decode('utf-8', 'replace'))}")
    run_cmd = [cfg["qemu"]]
    if cfg["mode"] == "dynamic":
        run_cmd += ["-L", cfg["guest_root"]]
    run_cmd += [elf]
    rc, guest_out, _err_b, timed = run_bytes(run_cmd, timeout=60,
                                             cwd=probe_dir)
    if timed or rc != 0:
        return fail(f"PRNG probe run failed rc={rc}")
    guest = {}
    for line in guest_out.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] in ("random", "rand"):
            try:
                guest[parts[0]] = (int(parts[1]), int(parts[2]))
            except ValueError:
                pass
    if set(guest) != {"random", "rand"}:
        return fail(f"PRNG probe output unparsable: {guest_out[:120]!r}")
    cache[key] = ({"guest": guest, "host": host}, "")
    return cache[key]


def iss265_evidence(case: Case, cfg, cache):
    """Recompute one ISS-265 admission row; return (ok, evidence).

    A missing row is refused (the admission is per case), and so is any row
    whose live condition does not hold -- such a case stays ``fail``.
    """
    row = ISS265_ADMISSION.get(case.cid)
    if row is None:
        return False, ("not an admitted ISS-265 case (admission is per case, "
                       "never per class)")
    if case.exit is None:
        return False, "no guest exit code (the run produced no verdict)"
    if case.oracle_kind == "md5":
        actual_doc = case.stdout + (b"exit %d\n" % case.exit)
        mismatched = hashlib.md5(actual_doc).hexdigest() != case.expected_hash
        exit_ok = case.exit == 0
        exit_why = f"exit {case.exit} (ruled runs exit 0)"
    elif case.oracle_kind in ("stdout", "raw"):
        actual_doc = case.stdout + (b"exit %d\n" % case.exit)
        mismatched = actual_doc != case.expected_doc
        exit_ok = case.exit == case.expected_exit
        exit_why = (f"exit {case.exit} == expected {case.expected_exit}"
                    if exit_ok else
                    f"exit {case.exit} != expected {case.expected_exit}")
    else:
        return False, (f"oracle form {case.oracle_kind!r} cannot carry this "
                       f"basis")
    if not mismatched:
        return False, "the oracle matched, so there is no failure to explain"
    if not exit_ok:
        return False, f"exit differs from the ruled runs: {exit_why}"

    if row["kind"] == "interleave":
        if len(actual_doc) != len(case.expected_doc):
            return False, (f"document sizes differ ({len(actual_doc)} B vs "
                           f"{len(case.expected_doc)} B): not an "
                           f"interleaving-only difference")
        if sorted(actual_doc.splitlines()) != sorted(
                case.expected_doc.splitlines()):
            return False, ("line multisets differ: not an interleaving-only "
                           "difference")
        return True, (f"same {len(actual_doc)} B / "
                      f"{len(actual_doc.splitlines())} lines, only the line "
                      f"order differs; {row['why']}")

    if row["kind"] != "prng":
        return False, f"unknown admission kind {row['kind']!r}"

    api = row["api"]
    draw_re = re.compile(r"\b" + re.escape(api) + r"\s*\(")
    seed_hits, draw_hits = [], []
    for src in case.sources:
        try:
            text = read_text(src)
        except OSError:
            continue
        if ISS265_SEED_RE.search(text):
            seed_hits.append(os.path.basename(src))
        if draw_re.search(text):
            draw_hits.append(os.path.basename(src))
    if not seed_hits or not draw_hits:
        return False, (f"no live seed+{api}() call in the case's own "
                       f"sources (seed={seed_hits or 'none'}, "
                       f"draw={draw_hits or 'none'})")
    if cfg is None:
        return False, "no run configuration for the live PRNG probe"
    seqs, err = iss265_prng_sequences(cfg, cache)
    if seqs is None:
        return False, f"live PRNG probe unavailable: {err}"
    guest, host = seqs["guest"][api], seqs["host"][api]
    if tuple(guest) == tuple(host):
        return False, (f"musl and glibc {api}() sequences after seed 1 are "
                       f"identical ({guest}): the libc basis does not hold")
    return True, (f"live seed in {', '.join(seed_hits)} + {api}() in "
                  f"{', '.join(draw_hits)}; musl {api}() after seed 1 = "
                  f"{guest} != glibc {host}; {row['why']}")


def iss265_admission_selfcheck():
    """Reverse check: the ISS-265 table is closed and refuses loose cases.

    Returns a list of problems (empty = ok).  Each negative probe is a
    reachable FAIL path: an unlisted case must be refused even when its
    documents look like an interleave, and a listed case whose oracle matched
    must be refused too.
    """
    problems = []
    expected = {
        "MultiSource/Applications/ClamAV": "interleave",
        "MultiSource/Applications/obsequi": "prng",
        "MultiSource/Benchmarks/Ptrdist/ft": "prng",
    }
    got = {cid: row.get("kind") for cid, row in ISS265_ADMISSION.items()}
    if got != expected:
        problems.append(f"admission table {got} != {expected}")

    unlisted = Case("MultiSource/Applications/lua", "MultiSource/Applications",
                    "multi", "", [])
    unlisted.klass = "fail"
    unlisted.oracle_kind = "stdout"
    unlisted.exit = 0
    unlisted.expected_exit = 0
    unlisted.stdout = b"b\na\n"
    unlisted.expected_doc = b"a\nb\nexit 0\n"
    ok, why = iss265_evidence(unlisted, None, {})
    if ok:
        problems.append(f"unlisted case admitted: {why}")

    matched = Case("MultiSource/Applications/ClamAV",
                   "MultiSource/Applications", "multi", "", [])
    matched.klass = "fail"
    matched.oracle_kind = "stdout"
    matched.exit = 0
    matched.expected_exit = 0
    matched.stdout = b"a\n"
    matched.expected_doc = b"a\nexit 0\n"
    ok, why = iss265_evidence(matched, None, {})
    if ok:
        problems.append(f"admitted case without a mismatch accepted: {why}")
    return problems


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def prepare_cases(cases, suite_root: str):
    for case in cases:
        tree_root = os.path.join(suite_root, case.tree)
        case.cmake = derive_cmake_config(suite_root, tree_root, case.unit_dir)
        # Include path: upstream's own ``include_directories`` /
        # ``target_include_directories`` declarations on the unit's CMakeLists
        # chain (already expanded and resolved by the evaluator).  A unit that
        # declares none -- no CMakeLists.txt at all (Polybench's template), or
        # the declaration sits in a branch upstream would not take on this libc
        # (archie-client's ``check_function_exists(re_comp)``) -- is compiled
        # with ``-I<unit_dir>``, CMake's CMAKE_CURRENT_SOURCE_DIR view, and the
        # source of the -I set is recorded in the JSON.
        if case.cmake.include_dirs:
            case.cmake.include_dir_source = "cmake"
        else:
            case.cmake.include_dirs = [case.unit_dir]
            case.cmake.include_dir_source = (
                "unit-dir-fallback (no include_directories/"
                "target_include_directories declaration applies to this unit)")
        parse_run_options(case, case.cmake)
        dropped = [a for a in case.cmake.ldflags
                   if a.startswith("-l") and a != "-lm"]
        if dropped:
            case.notes.append(
                "upstream -l flags not passed (musl keeps libm in libc; the "
                "lock has no separate " + ", ".join(dropped) + ")")
        load_oracle(case, suite_root)
        if case.cid in CASE_NOTES:
            case.notes.append(CASE_NOTES[case.cid])
    return cases


def run_round(cases, cfg, work_dir, jobs, args, excluded, progress=None):
    """Execute one link-mode round; return (results, counts, audit)."""
    results = []
    total = len(cases)
    done = {"n": 0}

    def note(case):
        done["n"] += 1
        if progress:
            exit_txt = "?" if case.exit is None else str(case.exit)
            progress(f"[{done['n']}/{total}] {case.klass.upper():10s} "
                     f"{case.cid} exit={exit_txt} "
                     f"({case.seconds:.1f}s)")

    if jobs <= 1:
        for case in cases:
            build_and_run(case, cfg, work_dir)
            results.append(case)
            note(case)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(build_and_run, case, cfg, work_dir): case
                       for case in cases}
            for future in concurrent.futures.as_completed(futures):
                case = future.result()
                results.append(case)
                note(case)
    results.sort(key=lambda c: c.cid)

    # ISS-265 admission runs after the round: a ``fail`` may become
    # ``known-fail`` only when its own row's live evidence holds.  The PRNG
    # probe is built once per round here (sequentially), never inside the
    # worker threads.
    iss265_cache = {}
    iss265_refused = []
    for r in results:
        if r.klass != "fail" or r.cid not in ISS265_ADMISSION:
            continue
        basis_ok, evidence = iss265_evidence(r, cfg, iss265_cache)
        if not basis_ok:
            iss265_refused.append(f"{r.cid}: {evidence}")
            continue
        r.klass = "known-fail"
        r.known_fail_basis = ISS265_ID
        r.known_fail_evidence = evidence
        r.reason = f"{ISS265_ID} (per-case basis holds): {r.reason}"

    counts = {k: sum(1 for r in results if r.klass == k)
              for k in ("pass", "fail", "known-fail", "blocked", "excluded")}
    counts["excluded"] = len(excluded)
    total = len(results)
    counts["total"] = total
    counts["pass_recorded"] = sum(1 for r in results
                                  if r.klass == "pass"
                                  and r.oracle_kind != "none")
    counts["pass_exit_only"] = sum(1 for r in results
                                   if r.klass == "pass"
                                   and r.oracle_kind == "none")

    executed = [r.cid for r in results]
    expected_ids = [c.cid for c in cases]
    closure_ok = executed == expected_ids and len(set(executed)) == len(executed)
    if not args.only and args.limit is None:
        closure_ok = closure_ok and len(cases) == args.expected_a_units

    bad_known = []
    for r in results:
        if r.klass != "known-fail":
            continue
        if r.known_fail_basis == ISS246_ID:
            basis_ok, _evidence = iss246_evidence(r)
        elif r.known_fail_basis == ISS265_ID:
            basis_ok, _evidence = iss265_evidence(r, cfg, iss265_cache)
        else:
            basis_ok = False
        if not basis_ok:
            bad_known.append(f"{r.cid} (basis={r.known_fail_basis or 'none'} "
                             f"does not hold)")
    misrouted = [r.cid for r in results
                 if r.klass == "known-fail" and r.known_fail_basis == ISS265_ID
                 and r.cid not in ISS265_ADMISSION]
    if misrouted:
        bad_known.extend(f"{cid} (ISS-265 admission is per case)"
                         for cid in misrouted)
    admission_problems = iss265_admission_selfcheck()
    unexplained = [r.cid for r in results if r.klass == "fail"]
    classification_ok = not bad_known and not admission_problems
    ok = (counts["fail"] == 0 and counts["blocked"] == 0 and closure_ok
          and classification_ok and cfg["census_ok"])
    return results, counts, dict(
        closure_ok=closure_ok, classification_ok=classification_ok,
        bad_known=bad_known, unexplained=unexplained,
        iss265_refused=iss265_refused,
        admission_problems=admission_problems, ok=ok)


def emit_round(cfg, cases, results, counts, audit, census, args, excluded,
               lines):
    mode = cfg["mode"]

    def emit(text=""):
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        lines.append(text)

    oracle_counts = {k: sum(1 for c in cases if c.oracle_kind == k)
                     for k in ("stdout", "md5", "raw", "none")}
    emit(f"run_llvm_ts_user: mode={mode} cases={len(cases)} "
         f"(现场枚举, 非写死)")
    emit(f"  suite: {cfg['src']} (patchless, manifest-locked)")
    emit(f"  link base: lld default (no -T / no linker script; ISS-247)")
    emit(f"  musl headers: -nostdinc + public user view "
         f"{', '.join(MUSL_USER_INCLUDE_DIRS)}")
    emit(f"  compile: -target {TARGET} {' '.join(BASE_CFLAGS)} "
         f"{' '.join(SMALL_PROBLEM_CFLAGS)} + upstream CMake flags")
    from_cmake = sum(1 for c in cases
                     if c.cmake.include_dir_source == "cmake")
    emit(f"  include dirs: from CMake declarations = {from_cmake} case(s); "
         f"unit-dir fallback = {len(cases) - from_cmake} case(s) "
         f"(per-case set + source in the JSON)")
    emit(f"  oracle: upstream reference, precedence "
         f".small > .big-endian > default; forms: stdout+exit="
         f"{oracle_counts['stdout']} md5={oracle_counts['md5']} "
         f"raw={oracle_counts['raw']} none(exit-only)={oracle_counts['none']}")
    emit(f"  work dir: {cfg['work_dir']}")
    emit(f"  scope A census: SingleSource/Benchmarks "
         f"{census['a_audit']['a_single_units']}/"
         f"{census['a_audit']['a_single_c_files']} .c with main; "
         + ", ".join(f"{t} {n} program dirs"
                      for t, n in census["a_audit"]["a_multi_units"].items())
         + f"; A discovered {census['a_discovered']} = executed "
           f"{census['a_units']} + excluded {len(excluded)}")
    emit(f"  scope B census (NOT run): "
         + ", ".join(f"{t} {v['units']}"
                     for t, v in census["b"].items())
         + f"; B total {census['b_units']}")
    emit(f"  scope C census: External .c={census['c']['External']['c_files']} "
         f"(with main {census['c']['External']['units_with_main']}); "
         f"non-C suffixes "
         f"{census['c']['non-c-suffixes']['counts']}; MicroBenchmarks "
         f".c={census['c']['MicroBenchmarks']['c_files']} (with main "
         f"{census['c']['MicroBenchmarks']['units_with_main']})")
    emit(f"  known-fail admission: {', '.join(sorted(KNOWN_FAIL_BASES))} "
         f"(per-case evidence recomputed live)")
    emit(f"  tolerance comparison: "
         + (f"upstream fpcmp at {cfg['fpcmp']}"
            if cfg.get("fpcmp") else
            f"fpcmp unavailable ({cfg.get('fpcmp_note', '-')}); byte-exact "
            f"only"))

    for case in cases:
        base = "?" if case.min_pt_load is None else hex(case.min_pt_load)
        act = "?" if case.exit is None else str(case.exit)
        emit(f"  {case.klass.upper():10s} {case.cid} exit={act} base={base} "
             f"oracle={case.oracle_kind}  ({case.reason})")
        if case.klass == "known-fail":
            emit(f"             basis: {case.known_fail_basis} -- "
                 f"{case.known_fail_evidence}")
        for note in case.notes:
            emit(f"             note: {note}")

    if not audit["closure_ok"]:
        emit(f"[FAIL] closure: executed {len(results)} case(s) != discovered "
             f"scope-A set {len(cases)}")
    if audit["bad_known"]:
        emit(f"[FAIL] known-fail without live basis evidence: "
             f"{audit['bad_known']}")
    if audit.get("admission_problems"):
        emit(f"[FAIL] ISS-265 admission self-check (closed per-case table): "
             f"{audit['admission_problems']}")
    if audit.get("iss265_refused"):
        emit(f"  ISS-265 rows refused (basis does not hold => stay fail): "
             f"{audit['iss265_refused']}")
    if audit["unexplained"]:
        emit(f"[FAIL] unclassified failure(s) remain: {audit['unexplained']}")

    emit(f"\nllvm-ts-user: mode={mode} total={counts['total']} "
         f"pass={counts['pass']} fail={counts['fail']} "
         f"known-fail={counts['known-fail']} blocked={counts['blocked']} "
         f"excluded={counts['excluded']}")
    emit(f"  pass split: reference oracle={counts['pass_recorded']} / "
         f"exit-only (NOT equivalence)={counts['pass_exit_only']}")
    for eid, reason in excluded:
        emit(f"  EXCLUDED {eid}: {reason}")
    for r in results:
        if r.klass in ("fail", "known-fail", "blocked"):
            emit(f"  {r.klass.upper()} {r.cid}: {r.reason}")
    if args.only or args.limit is not None:
        emit("  note: --only/--limit pilot run; counts are a subset "
             "(excluded is the declared scope-wide set)")
    emit("run_llvm_ts_user: " + ("PASS" if audit["ok"] else "FAIL"))
    return audit["ok"]


def _round_path(path: str, mode: str, both: bool):
    if not both:
        return path
    root, ext = os.path.splitext(path)
    return f"{root}-{mode}{ext}"


def write_artifacts(cfg, cases, results, counts, audit, census, args,
                    excluded):
    mode = cfg["mode"]
    both = cfg.get("both_rounds", False)
    json_out = abspath(args.json_out)
    report_out = abspath(args.report_out)
    json_out = _round_path(json_out, mode, both)
    report_out = _round_path(report_out, mode, both)
    record = dict(mode=mode, suite=cfg["src"],
                  seed=dict(target=TARGET, base="lld default",
                            musl_headers=list(MUSL_USER_INCLUDE_DIRS),
                            base_cflags=list(BASE_CFLAGS),
                            small_problem=list(SMALL_PROBLEM_CFLAGS),
                            case_timeouts=CASE_TIMEOUTS,
                            case_timeout_basis=CASE_TIMEOUT_BASIS),
                  discovered=census["a_discovered"],
                  excluded=[dict(id=cid, reason=reason)
                            for cid, reason in excluded],
                  total=counts["total"], counts=counts,
                  oracle_counts={k: sum(1 for c in cases
                                        if c.oracle_kind == k)
                                 for k in ("stdout", "md5", "raw", "none")},
                  census=census, closure_ok=audit["closure_ok"],
                  classification_ok=audit["classification_ok"],
                  known_fail_bases=KNOWN_FAIL_BASES,
                  filtered=bool(args.only or args.limit is not None),
                  cases=[r.as_dict(mode) for r in results])
    os.makedirs(os.path.dirname(json_out) or ".", exist_ok=True)
    with open(json_out, "w") as fh:
        json.dump(record, fh, indent=2)
    return json_out, report_out, record


def main() -> int:
    ap = argparse.ArgumentParser(
        description="llvm-test-suite user-mode suite (TESTCASES-048t)")
    ap.add_argument("--link-mode", choices=("static", "dynamic", "both"),
                    required=True,
                    help="one link mode per round (no default); 'both' runs "
                         "static to completion, then dynamic, over the same "
                         "enumeration snapshot")
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--suite-src", default=DEFAULT_SRC)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="per-case run timeout in seconds (timeout => blocked); "
                         "a floor: CASE_TIMEOUTS entries win when larger")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS,
                    help="parallel cases (default 4; never all cores)")
    ap.add_argument("--only", action="append", default=None,
                    help="run only cases whose id matches this regex "
                         "(repeatable; pilots)")
    ap.add_argument("--limit", type=int, default=None,
                    help="run the first N enumerated cases (pilots)")
    ap.add_argument("--list", action="store_true",
                    help="print scope A/B/C census and per-unit derived "
                         "configuration, build nothing")
    ap.add_argument("--json-out", required=True,
                    help="per-case JSON result file (required; relative paths "
                         "resolve against the caller's CWD).  With "
                         "--link-mode both the mode suffix is appended once "
                         "(<stem>-static.json / <stem>-dynamic.json).  Each "
                         "round also creates "
                         "<work-dir>/<UTC>-llvm-ts-user-<mode>/ with "
                         "run.json/run.log/meta.json (INFRA-093t)")
    ap.add_argument("--report-out", default=None,
                    help="human-readable report (default: same path as "
                         "--json-out with a .log extension)")
    ap.add_argument("--inject-wrong-oracle", default=None, metavar="REGEX",
                    help="evidence only: after loading the upstream oracle, "
                         "corrupt the expectation of matching cases so the "
                         "normal comparison must FAIL (proves the FAIL path)")
    args = ap.parse_args()
    # docs/Process-08 §1.2: a subset run (--only/--limit) must never land in
    # authoritative/.  Reject before any directory is created.
    subset_bits = []
    if args.only:
        subset_bits.append(f"--only {args.only!r}")
    if args.limit is not None:
        subset_bits.append(f"--limit {args.limit}")
    guard = _run_artifacts.subset_authoritative_error(
        " ".join(subset_bits) or None, args.work_dir)
    if guard:
        sys.stderr.write(f"ERROR: {guard}\n")
        return 2
    json_out = abspath(args.json_out)
    report_out = (abspath(args.report_out) if args.report_out else
                  os.path.splitext(json_out)[0] + ".log")
    args.json_out = json_out
    args.report_out = report_out

    if args.jobs < 1:
        sys.stderr.write("ERROR: --jobs must be >= 1\n")
        return 2

    suite_root = abspath(args.suite_src)
    musl = abspath(args.musl)
    work_dir = abspath(args.work_dir)
    cfg = {
        "src": suite_root,
        "clang": abspath(args.clang),
        "ldlld": abspath(args.ldlld),
        "qemu": abspath(args.qemu),
        "timeout": args.timeout,
        "work_dir": work_dir,
    }
    cfg["musl_incs"] = ["-nostdinc"]
    for d in MUSL_USER_INCLUDE_DIRS:
        cfg["musl_incs"] += ["-I", os.path.join(musl, d)]

    try:
        require_exec(cfg["clang"], "clang")
        require_exec(cfg["ldlld"], "ld.lld")
        require_exec(cfg["qemu"], "qemu-dadao")
        require_file(os.path.join(musl, "lib", "crt1.o"), "musl crt1.o")
        require_file(os.path.join(musl, "lib", "libc.a"), "musl libc.a")
        require_file(os.path.join(musl, "lib", "libc.so"), "musl libc.so")
        for d in MUSL_USER_INCLUDE_DIRS:
            if not os.path.isdir(os.path.join(musl, d)):
                raise SetupError(f"musl include dir not found: {musl}/{d}")
        # compiler-rt builtins: the same archive clang's driver would add
        # (INFRA-088t's installed toolchain), queried rather than guessed.
        b_rc, b_out, b_err, b_timed = run_bytes(
            [cfg["clang"], "-target", TARGET, "-print-libgcc-file-name"],
            timeout=60)
        builtins = b_out.decode("utf-8", "replace").strip()
        if b_rc != 0 or b_timed or not builtins:
            raise SetupError(
                "clang -print-libgcc-file-name failed: "
                + b_err.decode("utf-8", "replace").strip()[:300])
        require_file(builtins, "compiler-rt builtins archive")
        cfg["builtins"] = builtins
        if not os.path.isdir(suite_root):
            raise SetupError(f"llvm-test-suite source not found: {suite_root} "
                             "(run 'make fetch' first)")
        cases, excluded, census = discover(suite_root)
        if not cases:
            raise SetupError(f"no scope-A cases discovered under {suite_root}")
        prepare_cases(cases, suite_root)
        if args.inject_wrong_oracle:
            rx = re.compile(args.inject_wrong_oracle)
            hit = 0
            for case in cases:
                if not rx.search(case.cid):
                    continue
                hit += 1
                if case.oracle_kind == "md5":
                    case.expected_hash = "0" * 32
                elif case.oracle_kind in ("stdout", "raw"):
                    case.expected_doc = case.expected_doc + b"\x00injected"
                elif case.oracle_kind == "none":
                    # exit-only expectation: make the expected exit unreachable
                    # (a one-shot program cannot return 77 by accident here).
                    case.expected_exit = 77
                    case.notes.append("INJECTED wrong expectation (evidence "
                                      "run): expected exit 77")
            if not hit:
                sys.stderr.write("ERROR: --inject-wrong-oracle matched no "
                                 "case\n")
                return 2
            sys.stderr.write(f"INJECTED wrong oracle into {hit} case(s)\n")
        cfg["census_ok"] = census["a_census_ok"]
        args.expected_a_units = len(cases)
        os.makedirs(work_dir, exist_ok=True)
        cfg["fpcmp"], cfg["fpcmp_note"] = build_fpcmp(suite_root, work_dir)
    except SetupError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    selected = cases
    if args.only:
        patterns = [re.compile(p) for p in args.only]
        for pattern in patterns:
            if not any(pattern.search(c.cid) for c in cases):
                hit_excluded = [cid for cid in STRUCTURAL_EXCLUSIONS
                                if pattern.search(cid)]
                if hit_excluded:
                    sys.stderr.write(
                        f"ERROR: --only {pattern.pattern!r} matches declared "
                        f"exclusion(s) {hit_excluded}; excluded cases are not "
                        f"executed (see STRUCTURAL_EXCLUSIONS)\n")
                else:
                    sys.stderr.write(f"ERROR: --only {pattern.pattern!r} "
                                     f"matches no scope-A case\n")
                return 2
        selected = [c for c in cases
                    if any(p.search(c.cid) for p in patterns)]
        if not selected:
            sys.stderr.write(f"ERROR: no case matches --only {args.only}\n")
            return 2
    if args.limit is not None:
        selected = selected[:args.limit]
        if not selected:
            sys.stderr.write("ERROR: --limit selected no case\n")
            return 2

    if args.list:
        print(f"scope A: {census['a_units']} cases executed + "
              f"{len(excluded)} excluded = {census['a_discovered']} "
              f"discovered (SingleSource/Benchmarks "
              f"{census['a_audit']['a_single_units']}, "
              + ", ".join(f"{t} {n}" for t, n
                          in census["a_audit"]["a_multi_units"].items())
              + ")")
        for eid, reason in excluded:
            print(f"EXCLUDED {eid}: {reason}")
        print(f"scope B (NOT run): {census['b_units']} units: "
              + ", ".join(f"{t} {v['units']}" for t, v in census["b"].items()))
        print(f"scope C: External .c {census['c']['External']['c_files']}, "
              f"non-C suffixes {census['c']['non-c-suffixes']['counts']}, "
              f"MicroBenchmarks .c "
              f"{census['c']['MicroBenchmarks']['c_files']} (with main "
              f"{census['c']['MicroBenchmarks']['units_with_main']})")
        print(f"census_ok={census['a_census_ok']}")
        for case in selected:
            oracle = case.oracle_path or "exit-only"
            stdin = f" < {case.stdin_name}" if case.stdin_name else ""
            print(f"{case.cid}\tTUs={len(case.sources)}"
                  f"\toracle={case.oracle_kind}:{oracle}"
                  f"\trun={' '.join(case.run_argv) or '-'}{stdin}"
                  f"\tcflags={' '.join(case.cmake.cflags) or '-'}")
        return 0

    modes = ["static", "dynamic"] if args.link_mode == "both" else \
        [args.link_mode]
    cfg["both_rounds"] = len(modes) > 1
    rounds = []
    overall_ok = True
    for mode in modes:
        cfg["mode"] = mode
        cfg["libc"] = os.path.join(musl, "lib",
                                   "libc.a" if mode == "static"
                                   else "libc.so")
        cfg["crt1"] = os.path.join(musl, "lib", "crt1.o")
        if mode == "dynamic":
            guest_root = os.path.join(work_dir, mode, "root")
            os.makedirs(os.path.join(guest_root, "lib"), exist_ok=True)
            shutil.copyfile(cfg["libc"],
                            os.path.join(guest_root, "lib",
                                         "ld-musl-dadao.so.1"))
            cfg["guest_root"] = guest_root
        # INFRA-093t: each round (and therefore each mode) owns its directory;
        # the timestamp is taken before the round starts.
        round_started = _run_artifacts.iso_utc()
        run_dir = _run_artifacts.create_run_dir(
            work_dir, "llvm-ts-user", mode)
        lines = []
        results, counts, audit = run_round(
            selected, cfg, work_dir, args.jobs, args, excluded,
            progress=lambda msg: print(msg, flush=True))
        ok = emit_round(cfg, selected, results, counts, audit, census,
                        args, excluded, lines)
        json_out, report_out, record = write_artifacts(
            cfg, selected, results, counts, audit, census, args, excluded)
        lines.append(f"  artifacts: {json_out} , {report_out}")
        lines.append(f"  run dir: {run_dir} (run.json/run.log/meta.json)")
        report_text = "\n".join(lines) + "\n"
        for r in results:
            report_text += (
                f"{r.cid} {r.klass} exit={r.exit} "
                f"oracle={r.oracle_kind} base={r.min_pt_load} "
                f"run_seconds={r.run_seconds:.2f} "
                f"run_timeout={r.run_timeout} "
                f"reason={r.reason}\n")
            report_text += "  first_error: " + (r.first_error or "-") + "\n"
            if r.known_fail_basis:
                report_text += ("  known_fail_basis: "
                                + r.known_fail_basis + "\n")
                report_text += ("  known_fail_evidence: "
                                + r.known_fail_evidence + "\n")
            if r.tls_hits:
                report_text += "  tls_hits: " + ", ".join(r.tls_hits) + "\n"
            for note in r.notes:
                report_text += "  note: " + note + "\n"
            for cc in r.compile_cmds:
                report_text += "  compile: " + " ".join(cc) + "\n"
            report_text += "  link: " + " ".join(r.link_cmd) + "\n"
            report_text += "  run: " + " ".join(r.run_cmd) + "\n"
            report_text += (f"  stdout: {r.stdout_size} B sha256="
                            f"{r.stdout_sha256}\n")
        meta = _run_artifacts.build_meta(
            sys.argv, "llvm-ts-user", mode, run_dir, round_started,
            _run_artifacts.toolchain_summary(
                cfg["clang"], cfg["ldlld"], cfg["qemu"], cfg["libc"], musl))
        _run_artifacts.write_run_dir(run_dir, record, report_text, meta,
                                     json_out, report_out)
        overall_ok = overall_ok and ok
        rounds.append(dict(mode=mode, counts=counts, ok=ok,
                           json=json_out, report=report_out, run=run_dir))

    if len(rounds) > 1:
        print("\nllvm-ts-user: both rounds finished (static first):")
        for item in rounds:
            c = item["counts"]
            print(f"  {item['mode']}: total={c['total']} pass={c['pass']} "
                  f"fail={c['fail']} known-fail={c['known-fail']} "
                  f"blocked={c['blocked']} excluded={c['excluded']} "
                  f"rc={'0' if item['ok'] else '1'}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
