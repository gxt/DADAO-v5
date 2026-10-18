#!/usr/bin/env python3
"""libc-test user-mode suite runner (TESTCASES-047t; static round first).

Drives the manifest-locked ``libc-test`` corpus (``TESTCASES-044t``) through the
**user-mode** (``qemu-dadao``) flow, one link mode per invocation
(``--link-mode static|dynamic``, no default: the two rounds are separate runs by
design, static first).

Enumeration (live, never hard-coded)
------------------------------------
A *case* is a translation unit that upstream itself builds into an executable:

* upstream's Makefile builds exactly ``$(wildcard src/*/*.c)`` (one level under
  ``src/``), so a recursive glob is **not** the corpus view;
* a case must carry ``main`` (the DSO helpers declared by ``*.mk`` and the
  compile-only ``src/api/*.c`` conformance units have none);
* ``src/common/`` is the suite's own harness (``test.h``, ``t_printf``,
  ``t_memfill`` ...), not a case.

``src/api/`` is the one exception, mirroring upstream: all ``src/api/*.c`` are
compiled and linked into the single ``api/main`` executable
(``$(B)/api/main.exe: $(api.OBJS)`` in upstream's Makefile), because those TUs
are declaration-conformance checks with no ``main`` of their own.

``src/math/gen/`` (depth 3, 26 ``.c`` with ``main``/templates) is upstream's
*test generator* ("tools for generating testcases", needs mpfr; the templates
contain ``___`` placeholders) and is not built by upstream either.  It is
collected as a structural exclusion with its reason and live count, never
silently dropped.

Pipeline per case::

    clang --target=dadao-unknown-elf -nostdinc <musl headers> -I src/common \
          -std=c99 -D_POSIX_C_SOURCE=200809L -fno-builtin -frounding-math \
          <dynamic round only: -fPIC> \
          -c <case>.c  -> <case>.o

    # static line: P1 musl products, lld DEFAULT base (never -T dadao.lds)
    # compiler-rt builtins are grouped with libc.a (they reference each other):
    ld.lld -o <case>.elf <musl>/lib/crt1.o <case>.o <libtest.a> \
           --start-group <musl>/lib/libc.a <builtins archive> --end-group
    qemu-dadao <case>.elf

    # dynamic line: P2 musl products (same driver, next round); the builtins
    # archive is appended for the same reason as the static line (binary128
    # TF libcalls; libc.so hides its own compiler-rt members)
    ld.lld -o <case>.elf <musl>/lib/crt1.o <case>.o <libtest.a> <musl>/lib/libc.so \
           <builtins archive> -dynamic-linker /lib/ld-musl-dadao.so.1
    qemu-dadao -L <guest-root> <case>.elf

``-fPIC`` is a **dynamic-round compile flag only** (TESTCASES-049t / ISS-259
candidate (2)): a user TU that takes the *address* of a libc.so data object
(``environ``, ``signgam``, ``stdin``/``stdout``) otherwise needs an
``R_DADAO_COPY`` copy relocation, which lld refuses by design (ADR-0026 D7(2) /
contract-dynlink §10(2)).  The image stays a non-PIE ``ET_EXEC`` (no ``-pie``);
the flag only changes how the data address is formed.  The static round is
**not** touched, so its command line stays byte-identical; each case's compile
command line is recorded in the JSON/report so the split is auditable per case
(``compile_cmd``).

Base address (ISS-247): the link line carries **no** ``-T``/linker script, so
lld's default base is used; ``tests/scripts/dadao.lds`` (``RAM ORIGIN =
0xFC00_0000_0000``) cannot be loaded by ``qemu-user`` on this 47-bit host VA.
Every image's minimum ``PT_LOAD`` is read back from the file and an image at
the scripted base is rejected.

Static link modality: ``<musl>/lib/libc.a`` is named explicitly.  ``-L
<musl>/lib -lc`` would pick ``libc.so`` from the same directory (no
``PT_INTERP``, ``PT_DYNAMIC`` present) and ``qemu-user`` then segfaults --
same finding as TESTCASES-046t / QEMU-062t.

TESTCASES-050t item 3: the static line also carries the compiler-rt builtins
archive that clang's own driver would use (``clang -target
dadao-unknown-elf -print-libgcc-file-name``, installed by INFRA-088t), inside
the same ``--start-group`` as ``libc.a``: ``functional/tgmath`` emits
``__muldc3``/``__divdc3`` complex-arithmetic helpers that neither musl nor the
program provides.  Both link lines carry that archive: with ``long double`` =
binary128 (ADR-0030 D1) user TUs and the ``src/common/mtest.c`` harness emit TF
libcalls, and ``libc.so`` hides its own compiler-rt members
(``--exclude-libs=ALL``, upstream musl policy), so the archive must appear on
the dynamic line as well.

Independent oracle (AGENTS.md "Independent oracle")
--------------------------------------------------
The expectation is **never** derived from LLVM, QEMU or anything in this repo:

* a libc-test case reports through its own harness: ``t_error()`` (src/common/
  print.c) sets ``t_status`` and ``main`` returns it, so *guest exit status 0*
  means the case's own checks passed.  The expected value is the constant ``0``
  fixed by the corpus source;
* the corpus is manifest-locked (``components/libc-test``);
* ``src/musl/pleval.c`` checks musl's own plural evaluator against values
  computed by the compiler from the same rule (``_w = e``) -- independent of
  this repository's toolchain beyond plain C semantics;
* the math cases compare against vectors baked into the corpus (``mtest``),
  not against anything we generate.

Classification (counted live, never hard-coded)
-----------------------------------------------
* ``pass``        built + ran + guest exit 0 (the case's own ``t_status``).
* ``fail``        built + ran, guest exit != 0 and no declared gap signature
                  explains it: a real defect.  A guest killed by a signal is a
                  ``fail`` too (the program died); the signal number is kept.
* ``known-fail``  the failure is explained by a row of the **per-case basis
                  table** (``KNOWN_FAIL_BASES``), with that row's evidence
                  recomputed live: ``ISS-246`` (``__thread``: clang
                  ``thread-local storage is not supported for the current
                  target`` / backend ``GlobalTLSAddress``); ``ISS-251``
                  (musl's ``%s`` is parse-only -- ``src/time/strptime.c`` --
                  while the corpus asserts glibc's fill-``tm`` behaviour at
                  ``src/functional/strptime.c:112``); ``ADR-0030`` (the target
                  still declares ``long double`` = binary64 /
                  ``LDBL_MANT_DIG=53``; ADR-0030 is Accepted and schedules
                  binary128 in M9, so the five ``math/*l`` ulperr failures
                  disappear then).  A failure without a registered basis stays
                  a ``fail``; nothing else may be relabelled (ISS-226).  The
                  audit prints each row's basis and rejects an unattributed
                  ``known-fail`` and any unclassified ``fail``.
* ``excluded``    declared up front, structural, with a per-entry reason and a
                  live count: upstream's test *generator* tree
                  (``src/math/gen/**``), the ``dlopen`` cases (a static image
                  has no dynamic loader; in the dynamic round dlopen is out
                  of the declared M8 scope -- ADR-0025 D2 / INFRA-085t item 7
                  -- and the TLS DSO helpers cannot compile under ISS-246),
                  and an ``src/api`` conformance TU
                  that names an identifier the locked musl does not provide.
* ``blocked``     a build/run gap prevents the case from reaching its own
                  verdict: compile/link failure, missing symbol, unloadable
                  image, host-signal kill of qemu, timeout, or a **library
                  capability gap** -- today: ``pthread_create`` returns EAGAIN
                  because the musl port has no ``__clone`` (``src/thread/
                  clone.c`` answers ``-ENOSYS``, ``src/thread/dadao/`` has no
                  ``clone.s``; INFRA-082t declares the single-thread boundary).
                  ``blocked > 0 => rc = 1`` (ISS-248 gate rule: incomplete
                  coverage must not look green).

Exit status: 0 = no ``fail`` and no ``blocked``; 1 = otherwise; 2 = setup error
(missing tool / source / library product / zero cases).

Structural closure (lessons §2.21): the driver enumerates live, requires the
executed set to equal the discovered set minus the declared exclusions, and
prints both numbers.  A silently skipped case makes the run fail.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
import paths as _paths  # noqa: E402

TOOLCHAIN_BIN = str(_paths.host_toolchain_bin())

DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_SRC = ".work/source/libc-test"
DEFAULT_MUSL = ".work/source/musl"
DEFAULT_WORK_DIR = str(_paths.test_artifacts_dir() / "libc-test-user")
DEFAULT_LOG_DIR = ".work/log/testcases"
DEFAULT_TIMEOUT = 60
DYNAMIC_LINKER = "/lib/ld-musl-dadao.so.1"

# Public include set for *user* translation units -- the header view a program
# sees, not musl's own build view.  musl's internal headers must stay off this
# path: src/include/errno.h maps ``errno`` to the hidden ``___errno_location``
# (src/include/errno.h:9-12), which libc.a defines but libc.so keeps LOCAL
# HIDDEN (readelf -sW libc.so: ``___errno_location`` = LOCAL/HIDDEN, only
# ``__errno_location`` is exported).  A user TU compiled with the internal
# headers therefore links statically but fails dynamically with
# ``undefined hidden symbol: ___errno_location`` -- a driver-side include bug,
# not a target gap (verified: ipc_msg with this set links and exits 0).
MUSL_USER_INCLUDE_DIRS = ("arch/dadao", "arch/generic", "obj/include",
                          "include")

# Upstream config.mak.def minus the glibc-only block and the -Werror family
# (the task's stated口径: warnings are not build errors here).
#
# `-g` is dropped (it is in upstream's CFLAGS): the DADAO integrated assembler
# rejects the 4-byte relocations DWARF emits ("relocatable operand in a
# 1/2/4-byte data field ... use '.dd.o64'"), for *every* TU, independent of the
# test source.  Debug info is irrelevant to running the corpus; this is a
# toolchain gap, recorded in the task's findings, not a test failure.
BASE_CFLAGS = ("-std=c99", "-D_POSIX_C_SOURCE=200809L",
               "-Wall", "-Wno-unused-function", "-Wno-missing-braces",
               "-Wno-unused", "-Wno-overflow", "-Wno-unknown-pragmas",
               "-fno-builtin", "-frounding-math")

# src/api conformance units are compiled by upstream with -D_XOPEN_SOURCE=700.
API_CFLAGS = ("-D_XOPEN_SOURCE=700",)

# Per-case flags taken from upstream's <case>.mk files (the only two entries
# that matter for the enumerated set).  src/musl/pleval.mk: "$(N).CFLAGS := -w"
# with the comment "with gcc -Wno-parentheses -Wno-bool-compare is needed" --
# clang 23 classifies the chained comparison in that test as an *error*
# (-Wparentheses), which -w alone cannot demote, so -Wno-error=parentheses is
# the clang spelling of upstream's intent.
PER_CASE_CFLAGS = {
    "musl/pleval.c": ("-w", "-Wno-error=parentheses"),
}

# Dynamic round only (TESTCASES-049t / ISS-259 candidate (2)): the user TU is
# compiled position-independent.  Without it a data reference such as
# ``environ`` (functional/env), ``signgam`` (math/lgamma*) or ``stdin``/
# ``stdout`` (regression/fflush-exit, fgetwc-buffering, rewind-clear-error,
# setvbuf-unget) needs an R_DADAO_COPY copy relocation, which lld refuses by
# design (ADR-0026 D7(2) / contract-dynlink §10(2)) -- the case then never
# reaches its own verdict.  With -fPIC the data address is formed through the
# GOT and the same executable links as a plain non-PIE ET_EXEC (no -pie).
# The static round keeps its exact previous command line (this tuple is only
# appended when cfg["mode"] == "dynamic").
DYNAMIC_USER_CFLAGS = ("-fPIC",)

# The expected guest exit status for a passing case: libc-test's main returns
# t_status (0 = no t_error call).  Injected (wrong) by the evidence script.
EXPECTED_GUEST_EXIT = 0

# ---------------------------------------------------------------------------
# known-fail admission: a per-case evidence table (INFRA-087t).
#
# The rule stays "no unattributed known-fail" (ISS-226); it is no longer
# hard-bound to a single issue.  Each admitted cause names the evidence that
# must hold for the specific case, and the audit recomputes it per row:
#
#   ISS-246  compile-time ``__thread`` gap: a live TLS source scan must hit the
#            case *and* clang's first diagnostic must be the TLS one.
#   ISS-251  musl semantics: ``%s`` is parse-only (musl 1.2.6
#            ``src/time/strptime.c``; the DADAO patch series does not touch
#            that file) while libc-test asserts glibc's fill-``tm`` behaviour
#            (``src/functional/strptime.c:112``, under the corpus' own
#            ``/* Glibc */`` heading).  Evidence: the musl parse-only comment,
#            the corpus call site, and the case's own ``%s`` diagnostic.
# ---------------------------------------------------------------------------
ISS246_ID = "ISS-246"
ISS246_PATTERNS = (
    "thread-local storage is not supported",
    "GlobalTLSAddress",
)

ISS251_ID = "ISS-251"
ISS251_MUSL_COMMENT = (
    "Parse only. Effect on tm is unspecified",
    "and presently no effect is implemented",
)
ISS251_CALL_SITE = re.compile(
    r'checkStrptime\("683078400",\s*"%s",\s*&tm2\)')
ISS251_DIAGNOSTIC = '"%s": for "683078400"'

# The admitted causes, keyed by issue id: a case's ``known_fail_basis`` must be
# one of these keys and must satisfy the corresponding live evidence check.
ADR0030_ID = "ADR-0030"
ADR0030_FILE = os.path.join(REPO_ROOT, ".tao", "adr",
                            "adr-0030-long-double-binary128.md")
ADR0030_CASE_LIST = re.compile(r"math/\{([a-z0-9,]+)\}")

KNOWN_FAIL_BASES = {
    ISS246_ID: "live TLS scan hit + clang thread-local-storage diagnostic",
    ISS251_ID: "musl %s parse-only comment + corpus call site + %s diagnostic",
    ADR0030_ID: ("ADR-0030 Accepted (binary128 / M9) + target LDBL_MANT_DIG=53 "
                 "+ ulperr diagnostic"),
}

# Live scan basis for the known-fail table (the task's rule 1: scan every
# enumerable case's sources for TLS declarations, print the hit list and the
# count).  A case's *extra* upstream-declared TUs are part of its sources, so
# `functional/tls_align` is hit through `tls_align_dso.c` -- exactly the TU
# that fails to compile.
TLS_RE = re.compile(r"__thread|_Thread_local|\bthread_local\b")

# Declared library capability gaps: a run-time failure whose first reported
# error line matches one of these is a *gap in the platform*, reported as
# `blocked` with the pointer below -- never as `pass`, never as `known-fail`.
GAP_SIGNATURES = (
    # musl __clone() -> -ENOSYS (src/thread/clone.c); pthread_create
    # translates every clone failure to EAGAIN.
    (re.compile(r"pthread_create\(.*failed: Resource temporarily unavailable"),
     "pthread_create -> EAGAIN: musl port has no __clone "
     "(src/thread/clone.c returns -ENOSYS; src/thread/dadao/ has no clone.s; "
     "INFRA-082t single-thread boundary)"),
    (re.compile(r"thrd_create\(.*failed: Resource temporarily unavailable"),
     "thrd_create -> EAGAIN: musl port has no __clone (INFRA-082t)"),
    (re.compile(r"posix_spawnp?\(.*(?:failed, got 38|errno = 38)"),
     "posix_spawn -> ENOSYS: musl's posix_spawn calls __clone() "
     "(src/process/posix_spawn.c:198), which the port answers -ENOSYS "
     "(src/thread/clone.c; INFRA-082t single-thread boundary)"),
    (re.compile(r"popen\(.*failed \(errno = 38\)"),
     "popen -> ENOSYS: musl's popen uses posix_spawn -> __clone(), answered "
     "-ENOSYS by the port (src/thread/clone.c; INFRA-082t)"),
)

# Root-cause notes for non-pass cases (documentation only -- they never change
# the class).  Every entry was established from the corpus/libc/qemu/toolchain
# sources during the run, and is quoted in the task's report.
CASE_NOTES = {
    "functional/ipc_msg":
        "root cause: musl port __dadao_argmask (arch/dadao/syscall_arch.h:63) "
        "lists only read/write/readv/writev/brk/munmap/mmap/set_tid_address/"
        "set_robust_list/futex/getrandom/ioctl; msgctl/msgsnd/msgrcv get "
        "mask 0, so their pointer arguments are placed in the RD bank.",
    "functional/ipc_sem":
        "root cause (ISS-256 ①, fixed by LLVM-101t; NOT the argmask table, "
        "which ISS-249 closed): the 8-byte `union semun` is a *variadic* "
        "argument.  DADAO passes <=64B aggregates by value (contract-abi §6.4, "
        "and §5 keeps that split for varargs), but clang's DADAO ABI inherited "
        "DefaultABIInfo::EmitVAArg, whose non-virtual classifyArgumentType "
        "calls every aggregate indirect -- so the callee dereferenced the "
        "save-area slot instead of reading it (arg.buf read as garbage => "
        "EFAULT).",
    "functional/ipc_shm":
        "root cause (ISS-256 ②, fixed by LLVM-101t; NOT the argmask table): "
        "shmat() is `return (void *)syscall(...)`, so the tail-jump to "
        "__syscall_ret forwarded that call's i64 result in rd8 while the "
        "caller of shmat() reads a *pointer* from rb8 (contract-abi §4.4) -- "
        "`p` was a stale stack/image address => shmdt EINVAL.  A tail call is "
        "now demoted to call+ret when the callee's return locations differ "
        "from the function's own.",
    "functional/socket":
        "root cause: same __dadao_argmask gap -- sendto(206)/recvfrom(207) "
        "carry the sockaddr pointer in argument 4/5, unlisted => EINVAL/"
        "EFAULT (a native reproducer shows bind+getsockname work, sendto "
        "fails under qemu with the same arguments).",
    "functional/strptime":
        "known-fail basis ISS-251 (musl semantics, not a port defect): musl "
        "src/time/strptime.c:133-139 treats `%s` as parse-only -- \"Parse "
        "only. Effect on tm is unspecified and presently no effect is "
        "implemented.\" (upstream 1.2.6 verbatim; the DADAO patch series does "
        "not touch that file) -- while the corpus asserts glibc's fill-tm "
        "behaviour at src/functional/strptime.c:112 (under its own "
        "/* Glibc */ heading).  musl is kept as upstream; the corpus is "
        "read-only (patchless).",
    "math/acoshl":
        "known-fail basis ADR-0030 (Accepted; long double -> binary128 in M9): "
        "target declares long double == double (LDBL_MANT_DIG=53, "
        "musl arch/dadao/bits/float.h:24); musl's long-double implementation "
        "deviates from the corpus' double vectors by more than its ulp bar.",
    "math/asinhl":
        "known-fail basis ADR-0030 (Accepted; long double -> binary128 in M9): "
        "target declares long double == double (LDBL_MANT_DIG=53); "
        "musl's long-double implementation deviates from the corpus' double "
        "vectors by more than its ulp bar.",
    "math/erfcl":
        "known-fail basis ADR-0030 (Accepted; long double -> binary128 in M9): "
        "target declares long double == double (LDBL_MANT_DIG=53); "
        "musl's erfcl deviates from the corpus' double erfc vectors.",
    "math/lgammal":
        "known-fail basis ADR-0030 (Accepted; long double -> binary128 in M9): "
        "target declares long double == double (LDBL_MANT_DIG=53); "
        "musl's lgammal deviates from the corpus' double lgamma vectors "
        "(10.5 ulp on the failing vector).",
    "math/tgammal":
        "known-fail basis ADR-0030 (Accepted; long double -> binary128 in M9): "
        "target declares long double == double (LDBL_MANT_DIG=53); "
        "musl's tgammal deviates from the corpus' double tgamma vectors.",
    "functional/setjmp":
        "root cause: declared port gap -- sigsetjmp is not implemented "
        "(INFRA-082t 遗留 ⑧: src/signal/sigsetjmp.c is an upstream empty slot; "
        "using it fails at link time).",
    "functional/tgmath":
        "root cause (TESTCASES-047t static round, fixed by TESTCASES-050t): "
        "the static link line carried no compiler-rt builtins, so __muldc3 "
        "(complex multiply helper) was undefined.  The static line now links "
        "``clang -print-libgcc-file-name``'s archive inside the same "
        "--start-group as libc.a; the dynamic round always resolved it from "
        "libc.so.",
    "regression/mbsrtowcs-overflow":
        "root cause: musl's DADAO port declares 'typedef int wchar_t' "
        "(arch/dadao/bits/alltypes.h.in:29) while clang's target reports "
        "__WCHAR_TYPE__ = unsigned int; 'wchar_t ws[] = L\"XXXXX\"' is then "
        "an array-initializer type mismatch (the same signed/unsigned "
        "disagreement also makes wcscmp/wcsncmp prototypes clash).",
    "regression/flockfile-list":
        "root cause: qemu-user died on host signal 7 (SIGBUS) -- a QEMU-side "
        "fault, the case never reached its verdict.",
    "regression/setenv-oom":
        "root cause: qemu-user died on host signal 5 (SIGTRAP) after the case "
        "set RLIMIT_AS -- a QEMU-side fault, the case never reached its "
        "verdict.",
}

# Notes that only hold in one link mode (documentation only).
MODE_CASE_NOTES = {
    ("dynamic", "musl/pleval"):
        "dynamic-round link gap, expected upstream: __pleval is a *hidden* "
        "musl internal symbol (src/locale/pleval.h:6), so libc.so does not "
        "export it; upstream's own src/musl/pleval.mk says 'do not build and "
        "run the dynamic link tests (__pleval is no longer public)'.  The "
        "driver keeps the case in the executed set (same enumeration as the "
        "static round) and records the link error as blocked.",
}

# Declared structural exclusions inside the discovered set (per entry reason).
# Everything is counted live; an entry that no longer reproduces is reported as
# such (never assumed).
STRUCTURAL_EXCLUSIONS = {
    "functional/dlopen.c":
        "static musl image has no dynamic loader: the case dlopen()s a sibling "
        "DSO.  ADR-0025 D2 defers dlopen to M9+; structurally impossible in "
        "the static round (the dynamic round is the place for it).",
    "functional/tls_align_dlopen.c":
        "dlopen-based TLS case: it dlopen()s tls_align_dso.so and dlsyms its "
        "TLS variables.  A static image has no dynamic loader (ADR-0025 D2: "
        "dlopen deferred to M9+), so the case cannot reach a verdict here.",
    "functional/tls_init_dlopen.c":
        "dlopen-based TLS case (dlopen of tls_init_dso.so + dlsym).  A static "
        "image has no dynamic loader (ADR-0025 D2: dlopen deferred to M9+).",
    "regression/tls_get_new-dtv.c":
        "dlopen + pthread-based dynamic-TLS regression test; a static image "
        "has no dynamic loader (ADR-0025 D2) and the port has no threads.",
}

# Dynamic-round reasons for the same four entries: the static wording ("a
# static image has no dynamic loader") would be false here, so it is replaced
# rather than reused.  Two independent boundaries keep the cases out of the
# dynamic round: (1) dlopen itself is out of the declared M8 scope (ADR-0025
# D2 / INFRA-085t item 7: M8 does not require dlopen), and (2) the driver does
# not build the per-case DSO helpers, while the TLS DSOs additionally cannot
# compile (ISS-246) and need module-level TLS relocations that lld rejects
# (ADR-0025 D2).  These are scope/structural boundaries, not verdicts.
DYNAMIC_EXCLUSION_REASONS = {
    "functional/dlopen.c":
        "dynamic round: dlopen is out of the declared M8 scope (ADR-0025 D2 "
        "defers it to M9+; INFRA-085t item 7) and the driver does not build the "
        "sibling DSO helper (dlopen.mk: dlopen_dso.so).  Declared scope "
        "boundary, not a capability claim -- a non-TLS DSO probe works.",
    "functional/tls_align_dlopen.c":
        "dynamic round: the DSO helper tls_align_dso.c declares __thread (the "
        "target cannot compile it; ISS-246) and module-level TLS relocations "
        "(TLS_DTPMOD/DTPREL/TPREL) are rejected by lld, deferred to M9+ "
        "(ADR-0025 D2) -- the case cannot reach a verdict.",
    "functional/tls_init_dlopen.c":
        "dynamic round: the DSO helper tls_init_dso.c declares __thread "
        "(ISS-246) and needs module-level TLS relocations rejected by lld, "
        "deferred to M9+ (ADR-0025 D2) -- the case cannot reach a verdict.",
    "regression/tls_get_new-dtv.c":
        "dynamic round: dlopen + pthread dynamic-TLS regression; the DSO "
        "helper declares __thread (ISS-246), module-level TLS relocations are "
        "deferred to M9+ (ADR-0025 D2), and the port has no threads (ISS-252) "
        "-- the case cannot reach a verdict.",
}

# Extra translation units linked into a case, exactly as upstream's per-case
# .mk files declare them.  src/functional/tls_align.mk:
#   $(N)-static.LDLIBS := $(B)/$(D)/tls_align_dso.o
# (the DSO is built as a shared object for the dynamic binary and as a plain
# object for the -static one).  Without it the case cannot link: the test
# references the DSO's `t` symbol.
EXTRA_CASE_SOURCES = {
    "functional/tls_align": ["functional/tls_align_dso.c"],
}

# src/api TUs that the locked musl cannot compile: excluded per TU only if the
# declared signature really appears in the compiler output (otherwise reported
# as a mismatch, so the declaration cannot rot into a silent skip).
API_TU_GAPS = {
    "api/unistd.c":
        ("_PC_TIMESTAMP_RESOLUTION",
         "upstream libc-test api TU names _PC_TIMESTAMP_RESOLUTION, a "
         "POSIX.1-2024 addition absent from the locked musl 1.2.6 "
         "<unistd.h> (corpus newer than the libc); structural corpus/libc "
         "mismatch, not a target gap"),
}

# Machine-fault exits (ADR-0004 D5.8): the guest left through a machine fault
# and its own verdict failed -> `fail`, with the fault named.  A guest killed
# by a Linux-signal path instead shows up as 128+signo (reported as a signal).
FAULT_NAMES = {
    0x87: "UNMAPPED", 0x88: "ILLI", 0x89: "UNDI", 0x8A: "RASOF",
    0x8B: "RASUF", 0x8C: "MALIGN", 0x8D: "IALIGN",
}

# The scripted base of tests/scripts/dadao.lds (ISS-247).
SCRIPTED_BASE = 0xFC0000000000

PT_LOAD = 1
PT_INTERP = 3

MAIN_RE = re.compile(r"\bmain\s*\(")
THREAD_RE = re.compile(r"\b(pthread_create|thrd_create)\s*\(")


class SetupError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def run(cmd, timeout=None, stdin_data=None):
    """Run cmd; return (rc, stdout, stderr, timed_out). rc is None on timeout."""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout,
                              input=stdin_data)
        return (proc.returncode,
                proc.stdout.decode("utf-8", errors="replace"),
                proc.stderr.decode("utf-8", errors="replace"), False)
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode("utf-8", errors="replace")
        err = (exc.stderr or b"").decode("utf-8", errors="replace")
        return None, out, err, True


def require_file(path: str, what: str) -> None:
    if not os.path.isfile(path):
        raise SetupError(f"{what} not found: {path}")


def require_exec(path: str, what: str) -> None:
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        raise SetupError(f"{what} not executable: {path}")


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


def read_text(path: str) -> str:
    with open(path, "r", errors="replace") as fh:
        return fh.read()


def first_error_line(stdout: str, stderr: str) -> str:
    """First diagnostic the case itself printed (its t_error format is
    ``<file>:<line>: ...``); fall back to the first non-empty line."""
    for line in stdout.splitlines():
        if re.match(r"^\S+\.c:\d+: ", line.strip()):
            return line.strip()
    for text in (stdout, stderr):
        for line in text.splitlines():
            if line.strip():
                return line.strip()
    return "(no output)"


def first_tool_error(stderr: str) -> str:
    """First ``error:`` line of a compiler/linker diagnostic, which is what
    actually decided the exit status (warnings may precede it)."""
    for line in stderr.splitlines():
        if "error:" in line or "undefined symbol" in line:
            return line.strip()
    for line in stderr.splitlines():
        if line.strip():
            return line.strip()
    return "(no stderr)"


def gap_signature(stdout: str, stderr: str):
    text = stdout + "\n" + stderr
    for pat, why in GAP_SIGNATURES:
        m = pat.search(text)
        if m:
            return why, m.group(0)
    return None


def find_line(path: str, needle: str):
    """1-based line number of the first line containing ``needle``, or None."""
    for num, line in enumerate(read_text(path).splitlines(), 1):
        if needle in line:
            return num
    return None


def iss251_evidence(case, musl_root: str):
    """Recompute the ISS-251 basis for one case; return (ok, evidence).

    Three independent facts, none of them taken from the case's class:
    1. musl's ``%s`` branch carries the parse-only comment (the semantic
       authority; read from the locked musl tree);
    2. the corpus source carries the ``%s`` call site (assertion line);
    3. the case's own first diagnostic is that ``%s`` assertion -- so the
       basis explains *this* failure, not a look-alike.
    """
    musl_src = os.path.join(musl_root, "src", "time", "strptime.c")
    try:
        musl_text = read_text(musl_src)
    except OSError:
        return False, f"musl source missing: {musl_src}"
    first = ISS251_MUSL_COMMENT[0]
    second = ISS251_MUSL_COMMENT[1]
    c_line = find_line(musl_src, first)
    if c_line is None or second not in musl_text:
        return False, f"musl parse-only comment not found in {musl_src}"
    # The comment must sit in the '%s' branch, not somewhere else in the file.
    surrounded = musl_text.splitlines()[max(0, c_line - 5):c_line + 2]
    if not any("case 's':" in line for line in surrounded):
        return False, (f"musl parse-only comment at {musl_src}:{c_line} is "
                       f"not inside the '%s' branch")
    corpus_hit = None
    for path in case.sources:
        line = find_line(path, "683078400")
        if line is not None and ISS251_CALL_SITE.search(read_text(path)):
            rel = os.path.relpath(path, os.path.dirname(
                os.path.dirname(path))).replace(os.sep, "/")
            corpus_hit = (rel, line)
            break
    if corpus_hit is None:
        return False, "corpus %s call site not present in the case's sources"
    if ISS251_DIAGNOSTIC not in (case.first_error or ""):
        return False, (f"case diagnostic does not name the %s assertion: "
                       f"{case.first_error or '(none)'}")
    evidence = (f"musl src/time/strptime.c:{c_line} "
                f"\"{first} ...\"; corpus {corpus_hit[0]}:{corpus_hit[1]} "
                f"checkStrptime(\"683078400\", \"%s\", &tm2); observed: "
                f"{case.first_error}")
    return True, evidence


def adr0030_evidence(case, musl_root: str):
    """Recompute the ADR-0030 basis; return (ok, evidence).

    The ADR fixes ``long double`` = binary128 and defers it to M9.  Five facts,
    none taken from the case's class:
    1. the case is a ``math/*l`` case whose own diagnostic carries a ``ulperr``
       (the precision class the ADR names, not a look-alike);
    2. ADR-0030 is ``Accepted`` (decision authority);
    3. its D1 requires binary128 / ``LDBL_MANT_DIG`` = 113;
    4. the ADR lists this very case among the five that must disappear, and
       its D7 schedules the work in M9;
    5. the locked target still declares ``LDBL_MANT_DIG`` = 53 -- exactly the
       documented gap M9 removes.
    """
    name = os.path.basename(case.cid)
    if not case.cid.startswith("math/") or not name.endswith("l"):
        return False, "not a math/*l case"
    if "ulperr" not in (case.first_error or ""):
        return False, "diagnostic carries no ulperr"
    try:
        adr_text = read_text(ADR0030_FILE)
    except OSError:
        return False, f"ADR-0030 missing: {ADR0030_FILE}"
    status_line = find_line(ADR0030_FILE, "**状态**：Accepted")
    if status_line is None:
        return False, "ADR-0030 is not Accepted"
    d1_line = find_line(ADR0030_FILE, "### D1 ")
    if d1_line is None or not re.search(r"LDBL_MANT_DIG.{0,12}113", adr_text):
        return False, "ADR-0030 D1 does not state LDBL_MANT_DIG = 113"
    d7_line = find_line(ADR0030_FILE, "### D7 ")
    if d7_line is None:
        return False, "ADR-0030 has no D7 scheduling decision"
    d7_block = adr_text.splitlines()[d7_line - 1:d7_line + 8]
    if not any("M9" in line for line in d7_block):
        return False, "ADR-0030 D7 does not schedule the work in M9"
    m = ADR0030_CASE_LIST.search(adr_text)
    if not m:
        return False, "ADR-0030 does not list the five math cases"
    listed = {"math/" + n.strip() for n in m.group(1).split(",")}
    if case.cid not in listed:
        return False, f"ADR-0030's case list does not contain {case.cid}"
    list_line = find_line(ADR0030_FILE, m.group(0))
    float_h = os.path.join(musl_root, "arch", "dadao", "bits", "float.h")
    mant = re.search(r"#define\s+LDBL_MANT_DIG\s+(\d+)", read_text(float_h))
    if not mant or mant.group(1) != "53":
        return False, (f"target does not declare LDBL_MANT_DIG=53 "
                       f"({mant.group(1) if mant else 'missing'})")
    evidence = (f"ADR-0030 Accepted (line {status_line}); D1 line {d1_line} "
                f"binary128 / LDBL_MANT_DIG=113; D7 line {d7_line} -> M9; "
                f"ADR lists the case (line {list_line}); target musl "
                f"arch/dadao/bits/float.h:{find_line(float_h, '#define LDBL_MANT_DIG')} "
                f"LDBL_MANT_DIG=53; observed: {case.first_error}")
    return True, evidence


def attribute_known_fail_bases(case, musl_root: str):
    """Promote a *genuine* failure to ``known-fail`` when a registered basis
    explains it, with that basis' evidence recomputed live.

    Only ``fail`` rows are eligible: a pass or a blocked row is never
    relabelled, and a failure that no basis explains stays ``fail`` (the audit
    rejects any known-fail row whose basis does not hold, and any leftover
    ``fail`` row).
    """
    if case.klass != "fail":
        return
    for basis, evidence_fn in ((ISS251_ID, iss251_evidence),
                               (ADR0030_ID, adr0030_evidence)):
        ok, evidence = evidence_fn(case, musl_root)
        if ok:
            case.klass = "known-fail"
            case.known_fail_basis = basis
            case.known_fail_evidence = evidence
            case.reason = f"{basis}: {evidence}"
            return


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------
class Case:
    __slots__ = ("cid", "path", "sources", "klass", "exit", "reason",
                 "first_error", "elf", "min_pt_load", "interp", "uses_thread",
                 "tls_hits", "link_cmd", "compile_cmds", "outdir", "stdout",
                 "notes", "known_fail_basis", "known_fail_evidence")

    def __init__(self, cid, path, sources=None):
        self.cid = cid                       # e.g. "functional/argv" / "api/main"
        self.path = path                     # e.g. "src/functional/argv.c"
        self.sources = sources or [path]
        self.klass = "blocked"
        self.exit = None
        self.reason = ""
        self.first_error = ""
        self.elf = ""
        self.min_pt_load = None
        self.interp = ""
        self.uses_thread = False
        self.tls_hits = []                   # source files matching TLS_RE
        self.link_cmd = []
        self.compile_cmds = []               # per-TU clang command lines
        self.outdir = ""
        self.stdout = ""
        self.notes = []
        self.known_fail_basis = ""           # ISS-246 / ISS-251, else ""
        self.known_fail_evidence = ""        # live evidence for that basis

    def as_dict(self):
        return dict(case=self.cid, path=self.path, klass=self.klass,
                    exit=self.exit, reason=self.reason,
                    first_error=self.first_error, notes=self.notes,
                    elf=self.elf,
                    min_pt_load=(None if self.min_pt_load is None
                                 else hex(self.min_pt_load)),
                    pt_interp=self.interp,
                    uses_thread=self.uses_thread,
                    tls_hits=self.tls_hits,
                    known_fail_basis=self.known_fail_basis,
                    known_fail_evidence=self.known_fail_evidence,
                    compile_cmd=self.compile_cmds,
                    link_cmd=self.link_cmd, work_dir=self.outdir)


def discover(src_root: str):
    """Return (cases, excluded, census).

    ``cases``    -- runnable cases, one per upstream-built TU with ``main``,
                    plus the composite ``api/main`` conformance executable.
    ``excluded`` -- (id, reason) pairs: discovered entries excluded up front.
    ``census``   -- live counts for the coverage-boundary statement.
    """
    all_c = sorted(glob.glob(os.path.join(src_root, "**", "*.c"),
                             recursive=True))
    built_glob = sorted(glob.glob(os.path.join(src_root, "*", "*.c")))

    cases, excluded = [], []
    per_dir = {}
    api_sources = []
    depth2_with_main = set()
    api_main_rel = "api/main.c"
    for path in built_glob:
        rel = os.path.relpath(path, src_root).replace(os.sep, "/")
        d = rel.split("/")[0]
        per_dir.setdefault(d, dict(total=0, with_main=0, no_main=0))
        per_dir[d]["total"] += 1
        has_main = bool(MAIN_RE.search(read_text(path)))
        if rel == api_main_rel:
            # Handled by the composite api case below (upstream links all
            # src/api/*.o + api/main.c into api/main.exe).
            if has_main:
                per_dir[d]["with_main"] += 1
                depth2_with_main.add(rel)
            continue
        if rel.startswith("common/"):
            per_dir[d]["with_main" if has_main else "no_main"] += 1
            continue
        if not has_main:
            per_dir[d]["no_main"] += 1
            if d == "api":
                api_sources.append(path)
            continue
        per_dir[d]["with_main"] += 1
        depth2_with_main.add(rel)
        if rel in STRUCTURAL_EXCLUSIONS:
            excluded.append((rel, STRUCTURAL_EXCLUSIONS[rel]))
            continue
        extra = [os.path.join(src_root, e)
                 for e in EXTRA_CASE_SOURCES.get(rel[:-2], ())]
        cases.append(Case(rel[:-2], path, [path] + extra))

    # Composite api case: upstream links all src/api/*.o + api/main.c into
    # api/main.exe, because the api TUs are declaration-conformance checks with
    # no main of their own.
    api_main = os.path.join(src_root, api_main_rel)
    if os.path.isfile(api_main) and api_main_rel in depth2_with_main:
        if api_main_rel in STRUCTURAL_EXCLUSIONS:
            excluded.append((api_main_rel, STRUCTURAL_EXCLUSIONS[api_main_rel]))
        else:
            cases.append(Case("api/main", api_main_rel,
                              sorted(api_sources + [api_main])))

    # Depth-3 corpus files with main: upstream does not build them (its glob is
    # src/*/*.c).  They are upstream's test generator + templates.
    deeper = [p for p in all_c
              if os.path.relpath(p, src_root).count(os.sep) >= 2
              and MAIN_RE.search(read_text(p))]
    for path in sorted(deeper):
        rel = os.path.relpath(path, src_root).replace(os.sep, "/")
        excluded.append((rel,
                         "upstream's Makefile builds only src/*/*.c; this file "
                         "lives under src/math/gen/ -- the suite's *test "
                         "generator* ('tools for generating testcases', needs "
                         "mpfr), not a test case (templates carry '___' "
                         "placeholders)"))

    cases.sort(key=lambda c: c.cid)
    # Self-consistency of the enumeration: every main-carrying file found by
    # the live scan must be either a case or a declared exclusion.  Computed
    # from the scan, not from the case list, so a dropped case cannot hide.
    census_ok = (len(cases) + len(excluded) == len(depth2_with_main) + len(deeper))
    census = dict(
        recursive_c=len(all_c),
        built_glob_c=len(built_glob),
        discovered_with_main=len(depth2_with_main) + len(deeper),
        deeper_with_main=len(deeper),
        per_dir=per_dir,
        census_ok=census_ok,
    )
    return cases, excluded, census


# ---------------------------------------------------------------------------
# build / run
# ---------------------------------------------------------------------------
def gen_api_options_h(cfg, work_dir):
    """Reproduce upstream's $(B)/common/options.h from src/common/options.h.in.

    Upstream pipes the preprocessor output through awk; the file is generated
    into our work dir (the source tree stays read-only: patchless corpus).
    """
    tpl = os.path.join(cfg["src"], "src", "common", "options.h.in")
    out = os.path.join(work_dir, "include", "options.h")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [cfg["clang"], "-target", "dadao-unknown-elf"] + cfg["musl_incs"] + \
        ["-std=c99", "-D_POSIX_C_SOURCE=200809L", "-E", "-"]
    with open(tpl, "rb") as fh:
        rc, stdout, err, timed = run(cmd, stdin_data=fh.read())
    if timed or rc != 0:
        raise SetupError("preprocessing src/common/options.h.in failed: "
                         + (err.strip().splitlines() or ["(no stderr)"])[0])
    lines, started = [], False
    for line in stdout.splitlines():
        if "optiongroups_unistd_end" in line:
            started = True
            continue
        if not started or not line.strip() or line.strip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        lines.append(f"#define {parts[0]} {parts[-1]}")
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return os.path.dirname(out), len(lines)


def build_common_lib(cfg, work_dir):
    """Archive the suite's harness TUs (src/common/*.c minus runtest.c).

    runtest.c is the standalone fork/waitpid harness that embeds main() -- the
    cases are run directly under qemu instead, exactly as the task states.
    """
    src_common = os.path.join(cfg["src"], "src", "common")
    outdir = os.path.join(work_dir, "common")
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    objs = []
    for path in sorted(glob.glob(os.path.join(src_common, "*.c"))):
        name = os.path.basename(path)
        if name == "runtest.c":
            continue
        obj = os.path.join(outdir, name[:-2] + ".o")
        cmd = ([cfg["clang"], "-target", "dadao-unknown-elf"] + cfg["musl_incs"]
               + ["-I", src_common] + list(BASE_CFLAGS)
               + ["-c", path, "-o", obj])
        rc, _o, err, timed = run(cmd)
        if timed or rc != 0:
            raise SetupError(f"harness TU {name} failed to compile: "
                             f"{first_tool_error(err)}")
        objs.append(obj)
    ar = shutil.which("ar")
    if not ar:
        raise SetupError("host 'ar' not found (needed to archive src/common)")
    lib = os.path.join(work_dir, "libtest.a")
    if os.path.exists(lib):
        os.unlink(lib)
    rc, _o, err, timed = run([ar, "rc", lib] + objs)
    if timed or rc != 0:
        raise SetupError("ar failed: " + (err.strip() or "(no stderr)"))
    return lib, [os.path.basename(o) for o in objs]


def build_and_run(case, cfg, work_dir, api_inc=None):
    outdir = os.path.join(work_dir, cfg["mode"], case.cid)
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    case.outdir = outdir
    case.uses_thread = any(THREAD_RE.search(read_text(p)) for p in case.sources)
    case.tls_hits = [os.path.relpath(p, cfg["src_root"]).replace(os.sep, "/")
                     for p in case.sources if TLS_RE.search(read_text(p))]

    incs = list(cfg["musl_incs"])
    if api_inc:
        incs += ["-I", api_inc]
    incs += ["-I", os.path.join(cfg["src"], "src", "common")]
    extra = list(API_CFLAGS) if case.cid.startswith("api/") else []
    # Dynamic-round-only PIC compile (TESTCASES-049t); static stays as before.
    mode_cflags = list(DYNAMIC_USER_CFLAGS) if cfg["mode"] == "dynamic" else []

    objs = []
    for idx, src in enumerate(case.sources):
        rel = os.path.relpath(src, cfg["src_root"]).replace(os.sep, "/")
        obj = os.path.join(outdir, f"{idx:03d}_{os.path.basename(src)[:-2]}.o")
        cmd = ([cfg["clang"], "-target", "dadao-unknown-elf"] + incs
               + list(BASE_CFLAGS) + extra + mode_cflags
               + list(PER_CASE_CFLAGS.get(rel, ())) + ["-c", src, "-o", obj])
        case.compile_cmds.append(cmd)
        rc, _o, err, timed = run(cmd)
        if timed or rc != 0:
            first = first_tool_error(err)
            hit = next((p for p in ISS246_PATTERNS if p in err), None)
            if hit:
                case.klass = "known-fail"
                case.known_fail_basis = ISS246_ID
                case.known_fail_evidence = (
                    f"live TLS scan hit {case.tls_hits}; clang diagnostic "
                    f"{hit!r} (clang rc={rc} on {os.path.basename(src)})")
                case.reason = (f"{ISS246_ID} {hit!r}: {first} "
                               f"(clang rc={rc} on {os.path.basename(src)})")
            elif rel in API_TU_GAPS and API_TU_GAPS[rel][0] in err:
                sig, why = API_TU_GAPS[rel]
                case.notes.append(f"excluded api TU {rel} ({sig}): {why}; "
                                  f"compiler said: {first[:160]}")
                continue
            elif timed:
                case.klass = "blocked"
                case.reason = f"compile timeout on {os.path.basename(src)}"
                case.first_error = first
                return case
            else:
                case.klass = "blocked"
                case.reason = (f"compile error rc={rc} on "
                               f"{os.path.basename(src)}: {first[:240]}")
                case.first_error = first
                return case
            if case.klass == "known-fail":
                case.first_error = first
                return case
        objs.append(obj)

    elf = os.path.join(outdir, case.cid.replace("/", "_") + ".elf")
    common = [cfg["crt1"]] + objs + [cfg["libtest"]]
    if cfg["mode"] == "static":
        # libc.a and the compiler-rt builtins reference each other (libc's
        # long-double helpers call builtins, and tgmath's complex arithmetic
        # emits __muldc3/__divdc3), so they are one lld --start-group.
        # TESTCASES-050t item 3.
        link = ([cfg["ldlld"], "-o", elf] + common
                + ["--start-group", cfg["libc"], cfg["builtins"],
                   "--end-group"])
    else:
        # The dynamic line needs the builtins archive too: `long double` is
        # binary128 (ADR-0030 D1), so user TUs and the libtest harness
        # (src/common/mtest.c) emit TF libcalls, and libc.so hides its own
        # compiler-rt members (--exclude-libs=ALL, upstream musl policy) --
        # they cannot resolve user references.  In a normal build the driver
        # links builtins itself (INFRA-088t); this driver calls ld.lld
        # directly, so it appends the archive explicitly (same archive as the
        # static line, TESTCASES-050t item 3).
        link = ([cfg["ldlld"], "-o", elf] + common
                + [cfg["libc"], cfg["builtins"],
                   "-dynamic-linker", DYNAMIC_LINKER])
    case.link_cmd = link
    rc, _o, err, timed = run(link)
    if timed or rc != 0:
        case.klass = "blocked"
        first = first_tool_error(err)
        case.first_error = first
        case.reason = ("link timeout" if timed
                       else f"link error rc={rc}: {first[:240]}")
        return case
    case.elf = elf

    # Link-shape checks (ISS-247 base, static/dynamic modality) straight from
    # the file.
    try:
        case.min_pt_load = min_pt_load(elf)
        case.interp = pt_interp(elf).decode("utf-8", errors="replace").rstrip("\0")
    except ValueError as exc:
        case.klass = "blocked"
        case.reason = f"ELF parse failed: {exc}"
        return case
    if case.min_pt_load == SCRIPTED_BASE:
        case.klass = "blocked"
        case.reason = (f"ELF min PT_LOAD is the scripted dadao.lds base "
                       f"0x{SCRIPTED_BASE:x} (ISS-247)")
        return case
    if cfg["mode"] == "static" and case.interp:
        case.klass = "blocked"
        case.reason = f"static image carries PT_INTERP {case.interp!r}"
        return case
    if cfg["mode"] == "dynamic" and case.interp != DYNAMIC_LINKER:
        case.klass = "blocked"
        case.reason = (f"dynamic image PT_INTERP {case.interp!r} != "
                       f"{DYNAMIC_LINKER!r}")
        return case

    cmd = [cfg["qemu"]]
    if cfg["mode"] == "dynamic":
        cmd += ["-L", cfg["guest_root"]]
    cmd += [elf]
    rc, stdout, stderr, timed = run(cmd, timeout=cfg["timeout"])
    case.stdout = stdout
    if timed:
        case.klass = "blocked"
        gap = gap_signature(stdout, stderr)
        case.reason = (f"timeout after {cfg['timeout']}s"
                       + (f"; first reported gap: {gap[1]}" if gap else ""))
        case.first_error = first_error_line(stdout, stderr)
        return case
    if rc is None:
        case.klass = "blocked"
        case.reason = "qemu did not return an exit code"
        return case
    if rc < 0:
        case.klass = "blocked"
        case.reason = f"qemu killed by host signal {-rc}"
        return case
    case.exit = rc
    if rc == EXPECTED_GUEST_EXIT:
        case.klass = "pass"
        case.reason = "exit 0 (case's own t_status == 0)"
        return case
    case.first_error = first_error_line(stdout, stderr)
    gap = gap_signature(stdout, stderr)
    if gap:
        case.klass = "blocked"
        case.reason = f"library capability gap: {gap[0]} [{gap[1]}]"
        return case
    case.klass = "fail"
    if rc in FAULT_NAMES:
        case.reason = (f"guest exit 0x{rc:02X} (machine fault "
                       f"{FAULT_NAMES[rc]}, ADR-0004 D5.8); first error: "
                       f"{case.first_error[:200]}")
    elif rc > 128:
        case.reason = (f"guest died from signal {rc - 128}; first error: "
                       f"{case.first_error[:200]}")
    else:
        case.reason = f"guest exit {rc}, expected {EXPECTED_GUEST_EXIT}: " \
                      f"{case.first_error[:240]}"
    return case


def attribute_port_gaps(case, mode):
    """Apply the declared platform-gap rules *after* the case has run.

    Only documentation and the `fail` -> `blocked` demotion for cases that
    cannot possibly reach a verdict on this port; a `pass` and an attributed
    `known-fail` are never touched.
    """
    if case.cid in CASE_NOTES:
        case.notes.append(CASE_NOTES[case.cid])
    if (mode, case.cid) in MODE_CASE_NOTES:
        case.notes.append(MODE_CASE_NOTES[(mode, case.cid)])
    if case.klass not in ("fail", "blocked"):
        return
    if case.uses_thread:
        observed = case.reason
        case.klass = "blocked"
        case.reason = ("thread-dependent case; musl port has no __clone "
                       "(src/thread/clone.c returns -ENOSYS, src/thread/"
                       "dadao/ has no clone.s; INFRA-082t single-thread "
                       "boundary), so the case cannot reach its verdict. "
                       f"Observed: {observed}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="libc-test user-mode suite (TESTCASES-047t)")
    ap.add_argument("--link-mode", choices=("static", "dynamic"), required=True,
                    help="exactly one link mode per invocation (no default)")
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--filter", default=None,
                    help="only cases whose id matches this regex (pilots)")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--report-out", default=None)
    args = ap.parse_args()

    mode = args.link_mode
    cfg = {
        "mode": mode,
        "clang": abspath(args.clang),
        "ldlld": abspath(args.ldlld),
        "qemu": abspath(args.qemu),
        "src": abspath(args.src),
        "timeout": args.timeout,
    }
    musl = abspath(args.musl)
    cfg["musl_incs"] = ["-nostdinc"]
    for d in MUSL_USER_INCLUDE_DIRS:
        cfg["musl_incs"] += ["-I", os.path.join(musl, d)]
    cfg["src_root"] = os.path.join(abspath(args.src), "src")
    cfg["crt1"] = os.path.join(musl, "lib", "crt1.o")
    cfg["libc"] = os.path.join(musl, "lib",
                               "libc.a" if mode == "static" else "libc.so")
    work_dir = abspath(args.work_dir)

    try:
        require_exec(cfg["clang"], "clang")
        require_exec(cfg["ldlld"], "ld.lld")
        require_exec(cfg["qemu"], "qemu-dadao")
        require_file(cfg["crt1"], "musl crt1.o")
        require_file(cfg["libc"], f"musl {os.path.basename(cfg['libc'])}")
        for d in MUSL_USER_INCLUDE_DIRS:
            if not os.path.isdir(os.path.join(musl, d)):
                raise SetupError(f"musl include dir not found: {musl}/{d}")
        if not os.path.isdir(cfg["src"]):
            raise SetupError(f"libc-test source not found: {cfg['src']} "
                             "(run 'make fetch' first)")
        src_root = os.path.join(cfg["src"], "src")
        if not os.path.isdir(src_root):
            raise SetupError(f"corpus root not found: {src_root}")
        if not os.path.isfile(os.path.join(musl, "lib", "libc.a")):
            raise SetupError("static musl libc.a missing (build-musl)")

        # compiler-rt builtins for BOTH link lines (TESTCASES-050t item 3 +
        # ADR-0030 binary128): the archive clang's own driver would use,
        # queried rather than guessed (INFRA-088t installs it).  The static
        # round groups it with libc.a so tgmath's __muldc3/__divdc3 resolve;
        # with `long double` = binary128 the harness (src/common/mtest.c) and
        # user TUs emit TF libcalls, and libc.so hides its own compiler-rt
        # members (--exclude-libs=ALL), so the dynamic round needs it too.
        b_rc, b_out, b_err, b_timed = run(
            [cfg["clang"], "-target", "dadao-unknown-elf",
             "-print-libgcc-file-name"], timeout=60)
        builtins = (b_out or "").strip()
        if b_timed or b_rc != 0 or not builtins:
            raise SetupError(
                "clang -target dadao-unknown-elf -print-libgcc-file-name "
                f"failed: rc={b_rc} {(b_err or '').strip()[:300]}")
        require_file(builtins, "compiler-rt builtins archive")
        cfg["builtins"] = builtins

        os.makedirs(work_dir, exist_ok=True)
        cfg["libtest"], common_objs = build_common_lib(cfg, work_dir)
        api_inc, options_defines = gen_api_options_h(cfg, work_dir)

        cases, excluded, census = discover(src_root)
        if mode == "dynamic":
            # The static wording ("no dynamic loader in a static image") would
            # not describe the dynamic round; replace it per entry.
            excluded = [(eid, DYNAMIC_EXCLUSION_REASONS.get(eid, reason))
                        for eid, reason in excluded]
        if not cases:
            raise SetupError(f"no cases discovered under {src_root}")

        if mode == "dynamic":
            guest_root = os.path.join(work_dir, mode, "root")
            os.makedirs(os.path.join(guest_root, "lib"), exist_ok=True)
            shutil.copyfile(cfg["libc"],
                            os.path.join(guest_root, "lib",
                                         "ld-musl-dadao.so.1"))
            cfg["guest_root"] = guest_root
    except SetupError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    lines = []

    def emit(text=""):
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        lines.append(text)

    discovered = len(cases) + len(excluded)
    emit(f"run_libc_test_user_suite: mode={mode} "
         f"discovered={discovered} excluded={len(excluded)} "
         f"cases={len(cases)} (现场统计, 非写死)")
    emit(f"  corpus: {cfg['src']} (patchless, manifest-locked)")
    emit(f"  harness: {len(common_objs)} TU archived into libtest.a "
         f"(src/common/*.c minus runtest.c)")
    emit(f"  api: src/api/*.c compiled as one conformance executable "
         f"(upstream api/main.exe shape; options.h defines={options_defines})")
    emit(f"  oracle: expected guest exit {EXPECTED_GUEST_EXIT} "
         f"(each case returns its own t_status)")
    emit(f"  link base: lld default (no -T / no linker script; ISS-247)")
    if mode == "static":
        emit(f"  static link: --start-group {cfg['libc']} {cfg['builtins']} "
             f"--end-group (compiler-rt builtins from "
             f"clang -print-libgcc-file-name)")
    emit(f"  work dir: {work_dir}")

    # Recomputed here (not inside discover) so a case dropped *after* the
    # enumeration is caught: every main-carrying file must be a case or a
    # declared exclusion.
    census_ok = (len(cases) + len(excluded)
                 == census["discovered_with_main"])
    census["census_checked"] = census_ok
    if not census_ok:
        emit(f"[FAIL] census: cases({len(cases)}) + excluded({len(excluded)}) "
             f"!= discovered_with_main({census['discovered_with_main']})")
    selected = cases
    if args.filter:
        rx = re.compile(args.filter)
        selected = [c for c in cases if rx.search(c.cid)]
        if not selected:
            raise SetupError(f"no case matches --filter {args.filter!r}")

    results = []
    # known-fail table basis: live scan (rule 1 of the task), printed before the
    # run so the report can be checked line by line against it.
    tls_cases = []
    for case in selected:
        hits = [os.path.relpath(p, cfg["src_root"]).replace(os.sep, "/")
                for p in case.sources if TLS_RE.search(read_text(p))]
        if hits:
            tls_cases.append((case.cid, hits))
    emit(f"  known-fail admission: live TLS scan of {len(selected)} case(s) "
         f"-> {len(tls_cases)} hit(s); admitted causes = "
         f"{', '.join(sorted(KNOWN_FAIL_BASES))}")
    for cid, hits in tls_cases:
        emit(f"    TLS-HIT {cid}: {', '.join(hits)}")
    tls_ids = {cid for cid, _ in tls_cases}

    for case in selected:
        build_and_run(case, cfg, work_dir, api_inc)
        attribute_port_gaps(case, mode)
        attribute_known_fail_bases(case, musl)
        act = "?" if case.exit is None else str(case.exit)
        base = "?" if case.min_pt_load is None else hex(case.min_pt_load)
        emit(f"  {case.klass.upper():10s} {case.cid} exit={act} base={base} "
             f"thread={int(case.uses_thread)}  ({case.reason})")
        if case.klass == "known-fail":
            emit(f"             known-fail basis: {case.known_fail_basis} "
                 f"-- {case.known_fail_evidence}")
        for note in case.notes:
            emit(f"             note: {note}")
        results.append(case)

    # Structural closure: every selected case was executed exactly once, and
    # the selection itself is the discovered set minus the declared exclusions.
    executed = [r.cid for r in results]
    expect_ids = [c.cid for c in selected]
    closure_ok = executed == expect_ids and len(set(executed)) == len(executed)
    if not args.filter:
        closure_ok = closure_ok and len(expect_ids) == len(cases)
    if not closure_ok:
        emit(f"[FAIL] closure: executed {len(executed)} case(s) != "
             f"discovered-minus-excluded {len(expect_ids)}")

    counts = {k: sum(1 for r in results if r.klass == k)
              for k in ("pass", "fail", "known-fail", "blocked")}
    total = len(results)
    # A `known-fail` row is admissible only if its registered basis holds *live*
    # for this very case: ISS-246 = TLS scan hit + the TLS diagnostic; ISS-251 =
    # musl's parse-only `%s` comment + the corpus call site + the case's own `%s`
    # diagnostic.  Nothing else may be relabelled into the table (ISS-226).
    bad_known = []
    for r in results:
        if r.klass != "known-fail":
            continue
        if r.known_fail_basis == ISS246_ID:
            basis_ok = (r.cid in tls_ids
                        and any(p in r.first_error for p in ISS246_PATTERNS))
        elif r.known_fail_basis == ISS251_ID:
            basis_ok, _ev = iss251_evidence(r, musl)
        elif r.known_fail_basis == ADR0030_ID:
            basis_ok, _ev = adr0030_evidence(r, musl)
        else:
            basis_ok = False
        if not basis_ok:
            bad_known.append(f"{r.cid} (basis={r.known_fail_basis or 'none'})")
    # Reverse direction: a live ISS-251 or ADR-0030 failure may not silently
    # stay a `fail` (removing an admission would otherwise hide the basis), and
    # after the long-double row is admitted no unclassified `fail` may remain.
    missed_basis = [r.cid for r in results
                    if r.klass != "known-fail" and iss251_evidence(r, musl)[0]]
    missed_adr = [r.cid for r in results
                  if r.klass != "known-fail" and adr0030_evidence(r, musl)[0]]
    unexplained_fail = [r.cid for r in results if r.klass == "fail"]
    tls_that_pass = [r.cid for r in results
                     if r.klass == "pass" and r.cid in tls_ids]
    classification_ok = not (bad_known or missed_basis or missed_adr
                             or unexplained_fail)
    emit("  known-fail basis per case (recomputed live):")
    rows = [r for r in results if r.klass == "known-fail"]
    if rows:
        for r in rows:
            emit(f"    {r.cid}: {r.known_fail_basis or 'none'} -- "
                 f"{r.known_fail_evidence or '(no evidence)'}")
    else:
        emit("    (none)")
    if bad_known:
        emit(f"[FAIL] known-fail without live basis evidence: {bad_known}")
    if missed_basis:
        emit(f"[FAIL] live ISS-251 failure(s) not admitted as known-fail: "
             f"{missed_basis}")
    if missed_adr:
        emit(f"[FAIL] live ADR-0030 failure(s) not admitted as known-fail: "
             f"{missed_adr}")
    if unexplained_fail:
        emit(f"[FAIL] unclassified failure(s) remain: {unexplained_fail}")
    if tls_that_pass:
        emit(f"  note: TLS-hit case(s) that pass (legitimately not in the "
             f"table): {tls_that_pass}")
    emit(f"\nlibc-test-user: mode={mode} discovered={discovered} "
         f"excluded={len(excluded)} total={total} pass={counts['pass']} "
         f"fail={counts['fail']} known-fail={counts['known-fail']} "
         f"blocked={counts['blocked']}")
    for eid, reason in excluded:
        emit(f"  EXCLUDED {eid}: {reason}")
    for r in results:
        if r.klass in ("known-fail", "fail", "blocked"):
            emit(f"  {r.klass.upper()} {r.cid}: {r.reason}")
    if args.filter:
        emit("  note: --filter run (pilot); counts are a subset")

    json_out = abspath(args.json_out) if args.json_out else \
        os.path.join(DEFAULT_LOG_DIR, f"libc-test-user-{mode}.json")
    report_out = abspath(args.report_out) if args.report_out else \
        os.path.join(DEFAULT_LOG_DIR, f"libc-test-user-{mode}.log")
    os.makedirs(os.path.dirname(json_out) or ".", exist_ok=True)
    with open(json_out, "w") as fh:
        json.dump(dict(mode=mode, expected_exit=EXPECTED_GUEST_EXIT,
                       discovered=discovered, total=total, counts=counts,
                       excluded=[dict(id=n, reason=r) for n, r in excluded],
                       builtins=cfg["builtins"],
                       census=census, closure_ok=closure_ok,
                       classification_ok=classification_ok,
                       known_fail_bases=KNOWN_FAIL_BASES,
                       tls_scan=dict(
                           scanned=len(selected),
                           hits=[dict(case=cid, files=hits)
                                 for cid, hits in tls_cases],
                           pass_hits=tls_that_pass),
                       filtered=bool(args.filter),
                       cases=[r.as_dict() for r in results]), fh, indent=2)
    with open(report_out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
        for r in results:
            fh.write(f"{r.cid} {r.klass} exit={r.exit} "
                     f"base={r.min_pt_load} reason={r.reason}\n")
            fh.write("  first_error: " + (r.first_error or "-") + "\n")
            if r.known_fail_basis:
                fh.write("  known_fail_basis: " + r.known_fail_basis + "\n")
                fh.write("  known_fail_evidence: "
                         + r.known_fail_evidence + "\n")
            if r.tls_hits:
                fh.write("  tls_hits: " + ", ".join(r.tls_hits) + "\n")
            for note in r.notes:
                fh.write("  note: " + note + "\n")
            for cc in r.compile_cmds:
                fh.write("  compile: " + " ".join(cc) + "\n")
            fh.write("  link: " + " ".join(r.link_cmd) + "\n")
    emit(f"  artifacts: {json_out} , {report_out}")

    ok = (counts["fail"] == 0 and counts["blocked"] == 0 and closure_ok
          and census_ok and classification_ok)
    emit("run_libc_test_user_suite: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
