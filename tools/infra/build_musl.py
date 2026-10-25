#!/usr/bin/env python3
"""Build the musl library for dadao-unknown-elf and check the produced ELFs.

INFRA-082t stage A3 ("the cross toolchain can produce a static minimal
program"): the DADAO port of musl lives as a tree-shaped patch set
(``components/musl/patches/**`` + ``series``, docs/Process-01); this script
turns it into artifacts and proves the compiler/linker can produce a static
DADAO executable:

1. **build** -- ``./configure --target=dadao-unknown-elf --disable-shared
   CFLAGS=-ffp-contract=off`` + ``make`` inside ``.work/source/musl``
   (idempotent; rerun after ``make fetch apply-series``).  Products:
   ``lib/libc.a``, ``lib/crt1.o``.  P1 is the STATIC subset:
   ``--disable-shared`` is deliberate (the dynamic linker is P2, ADR-0025 D6);
   the fp-contract flag is musl's own accuracy requirement (ISS-332).
2. **smoke link** -- compile a minimal program (``write(1, "hi\\n", 3)`` +
   ``return 0``) against that library and link it with ``lib/crt1.o`` and the
   project ELF script ``tests/scripts/dadao.lds``.
3. **verify** -- the ELF is parsed here (ELF64 / big-endian / ET_EXEC /
   e_machine = EM_DADAO 0x0DA0 / no PT_INTERP / no PT_DYNAMIC, entry inside the
   first PT_LOAD) and cross-checked against ``file(1)``; the disassembly must
   contain the ``trap cfx0, 0`` syscall entry instruction.  Running the program
   on the dadao-m1 machine is stage B and is NOT done here.

INFRA-085t stage A1 ("shared library and PIC") adds a second, SHARED mode
(``--shared``, ``make build-musl-shared``):

4. **shared build** -- ``./configure`` *without* ``--disable-shared`` (musl
   compiles the ``.lo`` objects with ``-fPIC`` and links ``lib/libc.so``) plus
   ``LDFLAGS`` that pin the contract's dynamic-section shape: GNU hash only and
   a ``DT_SONAME`` (``contract-dynlink.md`` §5 rulings 6/7, §6.1).  The link
   also gets the compiler-rt builtins archive through musl's ``LIBCC`` hook
   (``__muldc3``/``__mulsc3`` / the TF set; see ``compiler_rt_builtins``).
5. **shared checks** -- ``readelf``-level facts read straight out of the file:
   ET_DYN / big-endian / EM_DADAO, ``PT_DYNAMIC``, ``DT_SONAME`` == ``libc.so``,
   ``DT_GNU_HASH``, and the ABSENCE of ``DT_HASH`` / ``DT_RELR`` / ``DT_RELRSZ``
   / the version tags and of every ``.gnu.version*`` section.
6. **ld.so symlink** -- ``libc.so`` is installed next to a
   ``ld-musl-dadao.so.1 -> libc.so`` symlink in the target sysroot lib dir
   (ADR-0016 D5; the path ``/lib/ld-musl-dadao.so.1`` is what
   ``contract-dynlink.md`` §6.1 fixes as ``PT_INTERP``), and the symlink is
   checked to resolve to the built ``libc.so`` byte-for-byte.
7. **dynamic executable** -- the smoke program is linked again against that
   ``libc.so`` as a *dynamic* executable, with the interpreter passed
   **explicitly** (``-dynamic-linker /lib/ld-musl-dadao.so.1``; lld has no
   default and its default is deliberately not changed, ADR-0026 D2).  The
   checks are the stage B1 exit criteria: the raw ``PT_INTERP`` payload must be
   the contract string byte-for-byte (NUL included) and ``DT_NEEDED`` must name
   ``libc.so``.  A negative control links the same objects *without* the flag
   and must produce no ``PT_INTERP`` (so the flag is provably load-bearing).

INFRA-108t (``ISS-303``) adds the **PIC static archive**:

8. **``lib/libc_pic.a``** -- the PIC counterpart of ``lib/libc.a``, archived
   from the ``.lo`` objects of the same member list (musl's
   ``LOBJS = $(LIBC_OBJS:.o=.lo)``, read live from the build system so the two
   archives cannot drift).  Every member is compared byte-for-byte (sha256)
   against the ``.lo`` file it was archived from, and the member order/name set
   is compared against ``libc.a`` (``.lo`` -> ``.o``).  It is installed next to
   ``libc.so`` in the target sysroot lib dir, and stays next to the build
   tree's ``libc.a``, which is where the driver looks for the PIC sibling of an
   explicit ``libc.a`` input.  Rationale: musl's ``libc.a`` is non-PIC, so a
   static PIE (``-static-pie``, or ``-pie`` + static libc) cannot link it --
   lld rejects every ``R_DADAO_ABS48`` with ``recompile with -fPIC``.  The plain
   ``-static`` line keeps using ``libc.a`` and is byte-identical.

The static and the shared configurations share one in-tree build directory, so
each mode re-runs ``./configure`` when ``config.mak`` records the other one;
the static line is never sacrificed for the shared one (the ``libc.a`` members
are the non-PIC ``.o`` objects in both modes).  The two modes write disjoint
object sets (``.o`` vs ``.lo``), so a mode switch needs no clean.

A **toolchain stamp** guards both modes against stale objects: musl's Makefile
has no dependency on the compiler binaries, so after ``make install-host`` the
existing objects would be reused by an unchanged ``make`` (LLVM-098t: 12
objects from 08:04 survived the 10:19 install and resurfaced an already fixed
code-gen bug).  The stamp records, for the two binaries that decide the object
code and the link result (``clang``, ``ld.lld``), their resolved path, **content
identity** (GNU ELF build-id, ``sha256`` when a tool carries none) and
``--version`` line in ``obj/.dadao-toolchain-stamp``; a mismatch -- or a missing
stamp -- runs ``make clean`` first and records the new stamp before building,
and the decision is always logged.  ``mtime``/``ctime``/``size`` are *not* part
of it (INFRA-101t, ``ISS-263``): ``make install-host`` re-links ``clang``
deterministically, so a byte-identical binary with a new mtime must stay green.
A stamp written in the retired ``mtime=`` format is treated as stale once (and
the log says ``stamp format migrated``), which rewrites it in the new format.

A second **source stamp** (``obj/.dadao-musl-source-stamp``) records a sha256
over every musl input file on disk, written after a successful build.  It
catches the case the toolchain stamp cannot see: a change *inside the port*
(e.g. the ISS-249 syscall argument-bank protocol) with an unchanged toolchain.
A changed digest forces ``make clean`` (musl's Makefile does not depend on every
header, so an incremental build can miss a protocol change), and
``tools/infra/check_musl_freshness.py`` (L1) compares both stamps plus the
installed ``libc.so`` against the build product, so "sources or toolchain
changed ⇒ libc.so must be rebuilt/reinstalled" is mechanically enforced.  The
digest also covers ``MUSL_CFLAGS`` -- the compile flags decide the object code
just as much as the sources do (ISS-332: libm contracted by clang's default FMA
contraction is 3 ulp off in ``math/yn``), and ``config.mak`` records them in a
file this digest skips; see ``source_stamp``.

Fail-closed: a missing toolchain, a missing source tree, any non-zero
compile/assemble/link step or a failed ELF assertion is an error (rc=2 for
setup problems, rc=1 for a failed check), never a silent skip.

``--inject`` corrupts the expectations so the checks must report FAIL (proving
the comparisons are live); it is used by the INFRA-082t / INFRA-085t evidence
scripts, which pair it with a real artifact-level negative control.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import toolchain_id as tid  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
MUSL_SRC = REPO_ROOT / ".work" / "source" / "musl"
LDS = REPO_ROOT / "tests" / "scripts" / "dadao.lds"

TARGET = "dadao-unknown-elf"
EM_DADAO = 0x0DA0
RAM_BASE = 0xFC0000000000

# ── libm must be built contraction-free (ISS-332) ───────────────────────────
# musl's libm polynomials are written as `a*b+c` and are accurate to the last
# bit only because that rounds twice.  Since LLVM-123t the backend legalises
# ISD::FMA and reports isFMAFasterThanFMulAndFAdd, so clang contracts the pair
# into a single fofma by default -- that moved libc-test's math/yn by 3 ulp
# (ISS-332).  Upstream musl's configure asks the compiler for exactly this flag;
# the cross build has to pass it explicitly.  It goes through CFLAGS (musl's
# configure writes the assignment into config.mak, and CFLAGS_ALL ends with
# $(CFLAGS), i.e. after $(CFLAGS_AUTO), so a later occurrence wins).  Only the
# libc build is affected: user code keeps the backend's FMA contraction.
MUSL_CFLAGS = "-ffp-contract=off"

# ── shared-object (dynamic linkage) names, INFRA-085t stage A1 ──────────────
# contract-dynlink.md §6.1: PT_INTERP = /lib/ld-musl-dadao.so.1, that path being
# a symlink to libc.so; musl's own name for the DSO is "libc.so"
# (ldso/dynlink.c sets `ldso.name = ldso.shortname = "libc.so"`), which is what
# the DT_SONAME and the symlink target below use.
SONAME = "libc.so"
LDSO_NAME = "ld-musl-dadao.so.1"
# INFRA-108t / ISS-303: the PIC static archive.  Same members as lib/libc.a,
# built from the -fPIC .lo objects; installed next to libc.so in the sysroot
# lib dir (and kept next to the build tree's libc.a).  The driver selects it
# for static PIE links (see clang/lib/Driver/ToolChains/DADAO.cpp).
PIC_ARCHIVE = "libc_pic.a"
# contract-dynlink.md §6.1 (ruling 5, user-confirmed 2026-10-14): the
# interpreter path written into PT_INTERP is the guest-visible
# /lib/ld-musl-dadao.so.1, which the install step makes a symlink to libc.so.
# lld has *no* default for it, so every dynamic-executable link in this build
# must pass it explicitly (ADR-0026 D2: do not change lld's default; the call
# site states the contract value).  Stage B1 = exactly this wiring.
DYNAMIC_LINKER = f"/lib/{LDSO_NAME}"
# musl's configure probes `--hash-style=both` into LDFLAGS_AUTO; §5 ruling 6
# ("only GNU hash, no DT_HASH") and the required DT_SONAME are imposed here.
# LDFLAGS_ALL = $(LDFLAGS_AUTO) $(LDFLAGS) and lld reads the LAST occurrence of
# --hash-style, so the trailing --hash-style=gnu wins.
#
# `-Wl,-shared` is explicit even though the DADAO driver now forwards a bare
# `-shared` (LLVM-096t fixed ISS-239; before that the driver dropped it and the
# "shared" link silently produced an ET_EXEC with no .dynamic at all).  Keeping
# the flag on the linker command line is the build-side statement of the
# behaviour (ADR-0026 D2: the call site passes it explicitly) and does not
# depend on the driver's forwarding list.
SHARED_LDFLAGS = f"-Wl,-shared -Wl,--hash-style=gnu -Wl,-soname,{SONAME}"

# musl links lib/libc.so with `$(LIBCC)` at the end of the rule and with
# `-Wl,--no-undefined` (configure's LDFLAGS_AUTO), so the compiler-rt builtins
# that musl's own C code calls (__muldc3/__mulsc3 from cpow/cpowf, and -- since
# `long double` = binary128, ADR-0030 D1 -- the whole TF set from printf/scanf/
# libm) must be present at that link.  The driver's `-print-libgcc-file-name`
# is the single source of truth for which archive that is (INFRA-088t made
# compiler-rt the default runtime; it is also what Makefile::install-host
# stages), so it is probed live instead of hardcoding one historical layout.
# The legacy narrow-scope archive from INFRA-079t is kept as a fallback for
# trees where install-host has not staged the per-target archive yet.
LEGACY_COMPILER_RT_BUILTINS = (REPO_ROOT / ".work" / "build"
                               / "compiler-rt-builtins" / "lib" / "linux"
                               / "libclang_rt.builtins-dadao.a")


def compiler_rt_builtins() -> Path:
    """Return the builtins archive to pass through musl's ``LIBCC`` hook."""
    clang = TOOLCHAIN_BIN / "clang"
    if clang.is_file():
        res = run([str(clang), f"--target={TARGET}", "-rtlib=compiler-rt",
                   "-print-libgcc-file-name"], env=toolchain_env())
        if res.returncode == 0:
            probe = Path(res.stdout.strip())
            if probe.is_file():
                return probe
    return LEGACY_COMPILER_RT_BUILTINS

# ELF constants used by the shared-object checks (gABI ch. 5 + lld's values).
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_PHDR = 6
PT_TLS = 7
ET_DYN = 3
DT_NULL = 0
DT_NEEDED = 1
DT_HASH = 4
DT_STRTAB = 5
DT_SONAME = 14
DT_RELRSZ = 35
DT_RELR = 36
DT_VERSYM = 0x6FFFFFF0
DT_VERDEF = 0x6FFFFFFC
DT_VERNEED = 0x6FFFFFFE
DT_GNU_HASH = 0x6FFFFEF5

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


def has_musl_cflags(config_text: str) -> bool:
    """Does a config.mak's ``CFLAGS`` line record exactly MUSL_CFLAGS?

    Exact equality, not "contains": configure writes ``CFLAGS`` from our one
    command line and nothing else appends to it (the Makefile only extends
    ``CFLAGS_ALL``), so any other value -- including an empty one written by a
    build whose MUSL_CFLAGS was emptied -- is a configuration that did not
    produce this library and must be regenerated.
    """
    for line in config_text.splitlines():
        if line.startswith("CFLAGS ="):
            return line.split("=", 1)[1].split() == MUSL_CFLAGS.split()
    return False


def config_records(shared: bool) -> bool:
    """True when the existing config.mak was generated for the wanted mode
    *and* records the compile flags the library must be built with.

    Both modes build in the same in-tree directory, and musl records its
    configure command line in config.mak; switching modes therefore has to
    re-run configure, otherwise ``make build-musl`` would silently keep the
    shared configuration (and with it libc.so) after a ``build-musl-shared``
    run -- i.e. the static target would stop proving the --disable-shared
    configuration.

    The same reasoning applies to MUSL_CFLAGS (ISS-332): the flag only reaches
    the compiler through config.mak, which configure alone writes, so a
    config.mak from before the flag existed must be regenerated -- otherwise
    every later ``make`` would keep compiling contracted libm.
    """
    config = MUSL_SRC / "config.mak"
    if not config.is_file():
        return False
    text = config.read_text(errors="replace")
    mode_ok = ("--disable-shared" in text) != shared
    return mode_ok and has_musl_cflags(text)


# ── toolchain staleness guard (INFRA-085t) ──────────────────────────────────
# See the module docstring ("A toolchain stamp guards both modes").  The stamp
# lives inside musl's generated obj/ directory: musl's .gitignore covers /obj/,
# so the source tree stays clean for check-source-state, and `make clean`
# (which removes obj/) both invalidates it and is itself the remedy.
#
# Why not a sha256 of the binaries by default: the installed clang is 4.0 GB and
# lld 2.1 GB, i.e. >6 GB of I/O on every single build for a guard that has to be
# cheap enough to run unconditionally.  The stamp therefore records the *content
# identity* the linker already put inside each binary: the GNU ELF build-id (a
# KB-sized note; INFRA-101t).  A tool without a build-id falls back to sha256,
# with a one-time warning about that cost.
#
# ctime is deliberately NOT part of it (ISS-263, 2026-10-17) and neither is
# mtime any more (INFRA-101t, 2026-10-22): both are inode metadata, not content.
# `make install-host` re-copies the same bytes with `cp -aL` + rename(2) (new
# ctime) and re-links clang deterministically (new mtime), so either attribute
# turned a byte-identical reinstall into a false "toolchain changed"
# (check-musl-freshness went red while every libc sha256 was unchanged).
STAMP_TOOLS = ("clang", "ld.lld")
STAMP_REL = Path("obj") / ".dadao-toolchain-stamp"
# A second stamp records WHAT the library was built FROM: a digest over every
# musl input file (sources, headers, Makefiles) as applied on disk.  The
# toolchain stamp alone cannot see an ISS-249-style protocol change *inside the
# port* (that change moved the syscall argument banks in musl's stub): the
# objects would be "up to date" with respect to clang, but the installed
# libc.so would still encode the old protocol.  Written after a successful
# build; checked by tools/infra/check_musl_freshness.py (L1).
SOURCE_STAMP_REL = Path("obj") / ".dadao-musl-source-stamp"
# A third stamp records the compiler-rt builtins archive the shared library was
# linked against (ISS-293, 2026-10-19): musl links ``lib/libc.so`` with
# ``LIBCC=<archive>`` and hides its members (``--exclude-libs=ALL``), so a
# stale archive is *baked into* the DSO -- every dynamic image then executes
# retired instruction encodings and dies with SIGILL, while the static round
# (separate archive on the program link line) keeps passing.  Neither the
# toolchain stamp (clang unchanged) nor the source stamp (musl unchanged) can
# see it: the archive is a link input, not a compile input.  A changed digest
# forces a relink of ``lib/libc.so`` (no full rebuild needed); checked by
# tools/infra/check_musl_freshness.py (L1).
BUILTINS_STAMP_REL = Path("obj") / ".dadao-builtins-stamp"
# Generated inside the build tree -- excluded so a rebuild cannot change its
# own input digest (configure writes config.mak; make writes obj/ and lib/).
SOURCE_STAMP_SKIP_TOP = {".git", "obj", "lib", "config.mak"}


def toolchain_stamp(tool_dir: Path = TOOLCHAIN_BIN) -> str:
    """One line per code-deciding toolchain binary: what the objects were built by.

    The criterion is the tool's *content* identity (GNU build-id, ``sha256``
    fallback), never mtime/size -- see the comment above ``STAMP_TOOLS``.
    ``tool_dir`` is a parameter so ``--self-test`` can drive a temp toolchain.
    """
    return tid.stamp_text(tool_dir, STAMP_TOOLS)


def stamp_is_legacy(text: str) -> bool:
    """Was this stamp written with the retired ``mtime=`` proxy (INFRA-101t)?"""
    return tid.is_legacy_stamp(text)


def read_stamp() -> str | None:
    try:
        return (MUSL_SRC / STAMP_REL).read_text()
    except OSError:
        return None


def write_stamp(text: str) -> None:
    path = MUSL_SRC / STAMP_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def stamp_decision() -> tuple[bool, str, str]:
    """(changed, reason, current stamp) for the build tree at MUSL_SRC.

    ``changed`` means the objects present in obj/ were produced by a different
    toolchain (or by an unknown one) and must not be reused.
    """
    current = toolchain_stamp()
    stored = read_stamp()
    if stored is None:
        return True, "no toolchain stamp recorded for this build tree", current
    if stamp_is_legacy(stored):
        # One rebuild pays for the migration: the old stamp proves nothing about
        # content, and a byte-identical toolchain is exactly what the retired
        # mtime proxy used to reject.
        return (True, "stamp format migrated (legacy mtime= stamp; one rebuild "
                      "records build-id)", current)
    if stored.strip() == current.strip():
        return False, "toolchain stamp unchanged (objects are up to date)", current
    return True, "toolchain stamp changed (build-id/sha256 of clang or ld.lld)", current


# ── source stamp (ISS-258) ──────────────────────────────────────────────────
def source_stamp() -> str:
    """One sha256 over every musl build input currently on disk.

    ``(relative path, sha256(content))`` for each regular file, with the
    generated top-level entries excluded (``obj/``, ``lib/``, ``config.mak``,
    ``.git``), plus the compile flags of MUSL_CFLAGS.  Content-based on
    purpose: a ``git checkout`` that only touches mtimes must not demand a
    rebuild, while a one-byte port change must.

    The flags belong here because they decide the object code (ISS-332): the
    same sources built with and without ``-ffp-contract=off`` differ in the
    libm objects, yet config.mak -- the file that carries them -- is generated
    and therefore skipped.  Mixing MUSL_CFLAGS in keeps the invariant
    mechanical: changing the flag moves this digest, which forces ``make
    clean`` here and turns check-musl-freshness red until the library is
    rebuilt.
    """
    digest = hashlib.sha256()
    digest.update(f"cflags {MUSL_CFLAGS}\0".encode())
    for path in sorted(MUSL_SRC.rglob("*")):
        rel = path.relative_to(MUSL_SRC)
        if rel.parts[0] in SOURCE_STAMP_SKIP_TOP or not path.is_file():
            continue
        digest.update(str(rel).encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def read_source_stamp() -> str | None:
    try:
        return (MUSL_SRC / SOURCE_STAMP_REL).read_text().strip()
    except OSError:
        return None


def write_source_stamp(text: str) -> None:
    path = MUSL_SRC / SOURCE_STAMP_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")


def source_decision() -> tuple[bool, str]:
    """(changed, reason) between the recorded source digest and the tree now.

    A changed digest forces ``make clean``: musl's Makefile does not depend on
    every header, so an incremental ``make`` can miss a protocol change (the
    ISS-249 stub change lived in ``arch/dadao/syscall_arch.h``).  The cost is
    one full rebuild of a small tree (~19 s) and it buys the guarantee that a
    product's recorded digest really describes the product.
    """
    stored = read_source_stamp()
    if stored is None:
        return True, "no source stamp recorded for this build tree"
    if stored == source_stamp():
        return False, "source stamp unchanged (objects built from these inputs)"
    return True, "musl source digest changed"


# ── builtins stamp (ISS-293) ────────────────────────────────────────────────
def builtins_digest() -> str:
    """sha256 of the compiler-rt builtins archive the shared link consumes."""
    archive = compiler_rt_builtins()
    if not archive.is_file():
        return "missing"
    return hashlib.sha256(archive.read_bytes()).hexdigest()


def read_builtins_stamp() -> str | None:
    try:
        return (MUSL_SRC / BUILTINS_STAMP_REL).read_text().strip()
    except OSError:
        return None


def write_builtins_stamp(text: str) -> None:
    path = MUSL_SRC / BUILTINS_STAMP_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")


def builtins_decision(shared: bool) -> tuple[bool, str]:
    """(changed, reason): is the DSO's recorded builtins archive still current?

    Only the shared line links the archive (``LIBCC``, ``--exclude-libs=ALL``),
    so a static build never needs a relink for this reason.  A missing stamp on
    an existing shared tree counts as changed: an unprovable product must not
    pass (the relink is cheap -- the .lo objects and libc.a stay).
    """
    if not shared:
        return False, "static line does not link the builtins archive"
    stored = read_builtins_stamp()
    if stored is None:
        return True, "no builtins stamp recorded for this build tree"
    if stored == builtins_digest():
        return False, "builtins stamp unchanged (libc.so linked this archive)"
    return True, "compiler-rt builtins archive changed"


def build_musl(jobs: int, reconfig: bool, shared: bool) -> int:
    if not MUSL_SRC.is_dir():
        print(f"build-musl: ERROR: {MUSL_SRC} not found -- run 'make fetch apply-series'",
              file=sys.stderr)
        return 2
    builtins = compiler_rt_builtins()
    if shared and not builtins.is_file():
        print(f"build-musl: ERROR: compiler-rt builtins archive "
              f"{builtins} not found -- build it first "
              f"(INFRA-079t/INFRA-088t; see those tasks' evidence scripts)",
              file=sys.stderr)
        return 2
    env = toolchain_env()
    if reconfig or not config_records(shared):
        cmd = ["./configure", f"--target={TARGET}",
               f"CFLAGS={MUSL_CFLAGS}",
               "CROSS_COMPILE=", "AR=ar", "RANLIB=ranlib"]
        if shared:
            cmd.append(f"LDFLAGS={SHARED_LDFLAGS}")
        else:
            cmd.append("--disable-shared")
        res = run(cmd, cwd=MUSL_SRC, env=env)
        if res.returncode != 0:
            print(f"build-musl: FAIL (configure rc={res.returncode})\n{res.stdout}",
                  file=sys.stderr)
            return 1
    try:
        changed, reason, current = stamp_decision()
    except OSError as exc:
        print(f"build-musl: ERROR: cannot stamp the toolchain ({exc})", file=sys.stderr)
        return 2
    src_changed, src_reason = source_decision()
    builtins_changed, builtins_reason = builtins_decision(shared)
    print(f"build-musl: toolchain: {reason}")
    print(f"build-musl: sources:   {src_reason}")
    print(f"build-musl: builtins:  {builtins_reason}")
    if changed or src_changed:
        print(f"build-musl: {'toolchain' if changed else 'sources'} changed "
              f"=> 'make clean' (full rebuild)")
        if changed:
            print("build-musl: current toolchain stamp:\n" + current.rstrip())
        res = run(["make", "clean"], cwd=MUSL_SRC, env=env)
        if res.returncode != 0:
            print(f"build-musl: FAIL (make clean rc={res.returncode})\n{res.stdout}",
                  file=sys.stderr)
            return 1
        # Record before building: obj/ has just been emptied, so whatever make
        # produces from here on *is* built by this toolchain -- a failed build
        # then resumes incrementally instead of paying another full clean.
        write_stamp(current)
    elif builtins_changed:
        # Relink only (ISS-293): musl's Makefile has no prerequisite for the
        # $(LIBCC) archive, so an incremental `make` would keep a DSO that
        # already embedded the previous one.  Dropping the target is enough --
        # the .lo objects and libc.a stay.
        so = MUSL_SRC / "lib" / SONAME
        if so.exists():
            so.unlink()
        print(f"build-musl: builtins changed => relink lib/{SONAME}")
    else:
        print("build-musl: incremental build")
    make_cmd = ["make", f"-j{jobs}"]
    if shared:
        make_cmd.append(f"LIBCC={builtins}")
    res = run(make_cmd, cwd=MUSL_SRC, env=env)
    if res.returncode != 0:
        print(f"build-musl: FAIL (make rc={res.returncode})\n{res.stdout}",
              file=sys.stderr)
        return 1
    products = ["lib/libc.a", "lib/crt1.o"]
    if shared:
        products.append(f"lib/{SONAME}")
    for product in products:
        if not (MUSL_SRC / product).is_file():
            print(f"build-musl: FAIL (missing product {product})", file=sys.stderr)
            return 1
    # Provenance: remember the exact inputs this build consumed.  Written only
    # after success (see check_musl_freshness.py).
    write_source_stamp(source_stamp())
    print(f"build-musl: recorded source stamp {read_source_stamp()} "
          f"({', '.join(products)})")
    if shared:
        write_builtins_stamp(builtins_digest())
        print(f"build-musl: recorded builtins stamp {read_builtins_stamp()}")
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


def link_dynamic_program(work: Path, obj: Path, so: Path) -> Path:
    """Link the smoke program as a DYNAMIC executable (INFRA-085t stage B1).

    ADR-0026 D2 / contract-dynlink.md §6.1: lld has no default interpreter, so
    the call site passes ``-dynamic-linker /lib/ld-musl-dadao.so.1`` explicitly
    (lld's default is deliberately NOT changed).

    No linker script is used here, and that is a deliberate, measured decision:

    * ``tests/scripts/dadao.lds`` (the static/M4 layout) declares its own PHDRS.
      lld then takes the *whole* program-header set from the script
      (``LinkerScript::createPhdrs``), i.e. ``.interp``/PT_INTERP and
      PT_DYNAMIC are never emitted -- and the link still succeeds (rc=0), so
      that script silently yields a non-interpreted ET_EXEC.  Wrong tool for
      this job.
    * ``tests/scripts/dadao-dyn.lds`` targets ET_DYN (``-shared`` / ``-pie``)
      and its single RWX segment starts at vaddr 0.  The smoke crt (crt1.o) is
      non-PIC, so an ET_EXEC at the RAM base/at 0 cannot carry it here.

    lld's own layout is therefore used: ET_EXEC, headers inside the first
    PT_LOAD (PT_PHDR), ``.interp`` present because of the flag above.  The load
    address is a P3 (qemu-user) concern; B1's criterion is structural
    (contract-dynlink.md §6.1).
    """
    elf = work / "musl_smoke_dyn.elf"
    cmd = [str(TOOLCHAIN_BIN / "ld.lld"),
           str(MUSL_SRC / "lib" / "crt1.o"), str(obj), str(so),
           "-dynamic-linker", DYNAMIC_LINKER,
           "-o", str(elf)]
    res = run(cmd, cwd=REPO_ROOT)
    if res.returncode != 0:
        raise RuntimeError(f"dynamic link rc={res.returncode}\n{res.stdout}")
    return elf


def interp_bytes(info: dict) -> bytes:
    """The raw PT_INTERP payload, NUL included (byte-level comparison)."""
    for p in info["phdrs"]:
        if p["type"] == PT_INTERP:
            return info["data"][p["offset"]:p["offset"] + p["filesz"]]
    return b""


def check_dynamic_exe(elf: Path, inject: bool) -> list[tuple[str, str, str, bool]]:
    """Return (name, expected, actual, ok) for the stage B1 criteria.

    Criteria (task book INFRA-085t stage B exit / contract-dynlink.md §6.1):
    dynamic executable with the byte-exact PT_INTERP string
    ``/lib/ld-musl-dadao.so.1`` and a DT_NEEDED entry naming libc.so.
    """
    info = parse_elf(elf)
    types = {p["type"] for p in info["phdrs"]}
    tags_list = info["dynamic"] or []
    tags = dict(tags_list)
    needed = [dyn_string_at(info, tags, val)
              for tag, val in tags_list if tag == DT_NEEDED]
    raw_interp = interp_bytes(info)

    exp_interp = DYNAMIC_LINKER if not inject else f"{DYNAMIC_LINKER}.bogus"
    exp_interp_b = exp_interp.encode() + b"\0"
    exp_needed = [SONAME] if not inject else [f"{SONAME}.bogus"]
    exp_class = 2 if not inject else 1
    exp_data = 2 if not inject else 1
    exp_type = 2 if not inject else 3          # ET_EXEC (inject: ET_DYN)
    exp_mach = EM_DADAO if not inject else 0x3E
    return [
        ("dynamic executable parsed", "no parse error",
         info["parse_error"] or "no parse error", info["parse_error"] is None),
        ("ELF class", "2 (ELFCLASS64)" if not inject else "1 (ELFCLASS32)",
         str(info["ei_class"]), info["ei_class"] == exp_class),
        ("ELF data", "2 (ELFDATA2MSB, big-endian)" if not inject else "1 (ELFDATA2LSB)",
         str(info["ei_data"]), info["ei_data"] == exp_data),
        ("ELF type", "2 (ET_EXEC)" if not inject else "3 (ET_DYN)",
         str(info["e_type"]), info["e_type"] == exp_type),
        ("e_machine", f"0x{exp_mach:04x} (EM_DADAO)" if not inject else "0x003e (EM_X86_64)",
         f"0x{info['e_machine']:04x}", info["e_machine"] == exp_mach),
        ("PT_PHDR present (headers are loadable)", "present",
         "present" if PT_PHDR in types else "absent",
         (PT_PHDR in types) if not inject else PT_PHDR not in types),
        ("PT_INTERP present", "present" if not inject else "absent",
         "present" if PT_INTERP in types else "absent",
         (PT_INTERP in types) if not inject else PT_INTERP not in types),
        ("PT_INTERP bytes",
         f"{exp_interp_b!r} ({len(exp_interp_b)} B)",
         f"{raw_interp!r} ({len(raw_interp)} B)",
         raw_interp == exp_interp_b),
        ("PT_DYNAMIC present", "present" if not inject else "absent",
         "present" if PT_DYNAMIC in types else "absent",
         (PT_DYNAMIC in types) if not inject else PT_DYNAMIC not in types),
        ("DT_NEEDED", str(exp_needed), str(needed), needed == exp_needed),
        ("DT_GNU_HASH present", "present" if not inject else "absent",
         "present" if DT_GNU_HASH in tags else "absent",
         (DT_GNU_HASH in tags) if not inject else DT_GNU_HASH not in tags),
        ("no PT_TLS (program has no TLS input)", "absent",
         "absent" if PT_TLS not in types else "present", PT_TLS not in types),
    ]



def parse_elf(path: Path) -> dict:
    """Minimal, dependency-free ELF64 reader (big- or little-endian).

    Besides the ELF header and the program headers (static path) it also
    returns the section names and the ``PT_DYNAMIC`` tag/value pairs, which the
    shared-object checks (INFRA-085t stage A1) are written against.
    """
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    ei_class, ei_data = data[4], data[5]
    order = ">" if ei_data == 2 else "<"
    (e_type, e_machine) = struct.unpack_from(order + "HH", data, 0x10)
    e_entry = struct.unpack_from(order + "Q", data, 0x18)[0]
    e_phoff = struct.unpack_from(order + "Q", data, 0x20)[0]
    e_shoff = struct.unpack_from(order + "Q", data, 0x28)[0]
    e_phentsize, e_phnum = struct.unpack_from(order + "HH", data, 0x36)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(order + "HHH", data, 0x3A)
    phdrs = []
    sections: list[str] = []
    dynamic: list[tuple[int, int]] | None = None
    parse_error = None
    try:
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type, _p_flags = struct.unpack_from(order + "II", data, off)
            p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = struct.unpack_from(
                order + "QQQQQQ", data, off + 8)
            phdrs.append({"type": p_type, "offset": p_offset, "vaddr": p_vaddr,
                          "filesz": p_filesz, "memsz": p_memsz})
        if e_shoff and e_shnum:
            shstr_hdr = e_shoff + e_shstrndx * e_shentsize
            shstr_off = struct.unpack_from(order + "Q", data, shstr_hdr + 0x18)[0]
            shstr_size = struct.unpack_from(order + "Q", data, shstr_hdr + 0x20)[0]
            shstr = data[shstr_off:shstr_off + shstr_size]
            for i in range(e_shnum):
                name_off = struct.unpack_from(order + "I", data, e_shoff + i * e_shentsize)[0]
                sections.append(shstr[name_off:shstr.index(b"\0", name_off)].decode())
        for p in phdrs:
            if p["type"] != PT_DYNAMIC:
                continue
            dynamic = []
            for off in range(p["offset"], p["offset"] + p["filesz"], 16):
                d_tag = struct.unpack_from(order + "q", data, off)[0]
                d_val = struct.unpack_from(order + "Q", data, off + 8)[0]
                if d_tag == DT_NULL:
                    break
                dynamic.append((d_tag, d_val))
            break
    except (struct.error, ValueError) as exc:
        # A corrupt/foreign image must be reported as a failed check, never as
        # a traceback (this is what the evidence script's negative control
        # exercises: flip EI_DATA and the section/table offsets stop making
        # sense in the declared byte order).
        parse_error = f"{type(exc).__name__}: {exc}"
    return {"data": data, "ei_class": ei_class, "ei_data": ei_data, "order": order,
            "e_type": e_type, "e_machine": e_machine, "e_entry": e_entry,
            "phdrs": phdrs, "sections": sections, "dynamic": dynamic,
            "parse_error": parse_error}


def vaddr_to_offset(info: dict, vaddr: int) -> int | None:
    """Translate a virtual address to a file offset via the PT_LOAD headers."""
    for p in info["phdrs"]:
        if p["type"] == PT_LOAD and p["vaddr"] <= vaddr < p["vaddr"] + p["filesz"]:
            return p["offset"] + (vaddr - p["vaddr"])
    return None


def dyn_string(info: dict, tags: dict[int, int], tag: int) -> str | None:
    """Read the NUL-terminated string a DT_* tag points at (via DT_STRTAB)."""
    if tag not in tags or DT_STRTAB not in tags:
        return None
    off = vaddr_to_offset(info, tags[DT_STRTAB] + tags[tag])
    if off is None:
        return None
    data = info["data"]
    end = data.find(b"\0", off)
    return data[off:end].decode(errors="replace") if end >= 0 else None


def dyn_string_at(info: dict, tags: dict[int, int], index: int) -> str | None:
    """Read the NUL-terminated string ``index`` bytes into DT_STRTAB (.dynstr)."""
    if DT_STRTAB not in tags:
        return None
    off = vaddr_to_offset(info, tags[DT_STRTAB] + index)
    if off is None:
        return None
    data = info["data"]
    end = data.find(b"\0", off)
    return data[off:end].decode(errors="replace") if end >= 0 else None


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_elf(elf: Path, inject: bool) -> list[tuple[str, str, str, bool]]:
    """Return (name, expected, actual, ok) for every structural assertion."""
    info = parse_elf(elf)
    types = {p["type"] for p in info["phdrs"]}
    loads = [p for p in info["phdrs"] if p["type"] == 1]

    exp_class = 2 if not inject else 1          # ELFCLASS64 (inject: ELFCLASS32)
    exp_data = 2 if not inject else 1           # ELFDATA2MSB (inject: LSB)
    exp_type = 2 if not inject else 3           # ET_EXEC    (inject: ET_DYN)
    exp_mach = EM_DADAO if not inject else 0x3E # EM_DADAO   (inject: EM_X86_64)
    exp_class_s = "2 (ELFCLASS64)" if not inject else "1 (ELFCLASS32)"
    exp_data_s = "2 (ELFDATA2MSB, big-endian)" if not inject else "1 (ELFDATA2LSB)"
    exp_type_s = "2 (ET_EXEC)" if not inject else "3 (ET_DYN)"
    exp_mach_s = "0x0da0 (EM_DADAO)" if not inject else "0x003e (EM_X86_64)"
    checks = [
        ("ELF class", exp_class_s, str(info["ei_class"]), info["ei_class"] == exp_class),
        ("ELF data", exp_data_s, str(info["ei_data"]),
         info["ei_data"] == exp_data),
        ("ELF type", exp_type_s, str(info["e_type"]), info["e_type"] == exp_type),
        ("e_machine", exp_mach_s, f"0x{info['e_machine']:04x}",
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


# ── INFRA-085t stage A1: shared object + ld.so symlink ──────────────────────
def check_shared_elf(so: Path, inject: bool) -> list[tuple[str, str, str, bool]]:
    """Return (name, expected, actual, ok) for the A1 shared-object criteria.

    Criteria (task book INFRA-085t stage A1 exit / contract-dynlink.md §5, §6.1):
    ET_DYN + big-endian, DT_SONAME + DT_GNU_HASH present, DT_HASH / DT_RELR /
    DT_RELRSZ / version tags / .gnu.version* sections absent.
    """
    info = parse_elf(so)
    tags = dict(info["dynamic"] or [])
    sections = info["sections"]
    dyn = info["dynamic"]
    version_sections = sorted(s for s in sections if s.startswith(".gnu.version"))
    version_tags = sorted(
        t for t in (DT_VERSYM, DT_VERNEED, DT_VERDEF) if t in tags)

    exp_class = 2 if not inject else 1           # ELFCLASS64 (inject: ELFCLASS32)
    exp_data = 2 if not inject else 1            # ELFDATA2MSB (inject: LSB)
    exp_type = ET_DYN if not inject else 2       # ET_DYN     (inject: ET_EXEC)
    exp_mach = EM_DADAO if not inject else 0x3E  # EM_DADAO   (inject: EM_X86_64)
    exp_class_s = "2 (ELFCLASS64)" if not inject else "1 (ELFCLASS32)"
    exp_data_s = "2 (ELFDATA2MSB, big-endian)" if not inject else "1 (ELFDATA2LSB)"
    exp_type_s = "3 (ET_DYN)" if not inject else "2 (ET_EXEC)"
    exp_mach_s = "0x0da0 (EM_DADAO)" if not inject else "0x003e (EM_X86_64)"
    exp_soname = SONAME if not inject else f"{SONAME}.bogus"
    soname = dyn_string(info, tags, DT_SONAME)
    checks = [
        ("shared object parsed", "no parse error", info["parse_error"] or "no parse error",
         info["parse_error"] is None),
        ("ELF class", exp_class_s, str(info["ei_class"]),
         info["ei_class"] == exp_class),
        ("ELF data", exp_data_s, str(info["ei_data"]),
         info["ei_data"] == exp_data),
        ("ELF type", exp_type_s, str(info["e_type"]), info["e_type"] == exp_type),
        ("e_machine", exp_mach_s, f"0x{info['e_machine']:04x}",
         info["e_machine"] == exp_mach),
        ("PT_DYNAMIC present", "present" if not inject else "absent",
         "present" if dyn is not None else "absent",
         (dyn is not None) if not inject else dyn is None),
        ("DT_SONAME", exp_soname, soname or "absent",
         soname == exp_soname),
        ("DT_GNU_HASH present", "present" if not inject else "absent",
         "present" if DT_GNU_HASH in tags else "absent",
         (DT_GNU_HASH in tags) if not inject else DT_GNU_HASH not in tags),
        ("no DT_HASH", "absent" if not inject else "present",
         "present" if DT_HASH in tags else "absent",
         (DT_HASH not in tags) if not inject else DT_HASH in tags),
        ("no DT_RELR", "absent" if not inject else "present",
         "present" if DT_RELR in tags else "absent",
         (DT_RELR not in tags) if not inject else DT_RELR in tags),
        ("no DT_RELRSZ", "absent" if not inject else "present",
         "present" if DT_RELRSZ in tags else "absent",
         (DT_RELRSZ not in tags) if not inject else DT_RELRSZ in tags),
        ("no version tags (DT_VERSYM/DT_VERNEED/DT_VERDEF)",
         "absent" if not inject else "present",
         "absent" if not version_tags else f"present {version_tags}",
         (not version_tags) if not inject else bool(version_tags)),
        ("no .gnu.version* sections", "absent" if not inject else "present",
         "absent" if not version_sections else f"present {version_sections}",
         (not version_sections) if not inject else bool(version_sections)),
    ]
    return checks


def install_ldso(so: Path, libdir: Path) -> Path:
    """Install ``libc.so`` + ``ld-musl-dadao.so.1 -> libc.so`` (ADR-0016 D5).

    Returns the symlink path.  musl's own install target creates the same pair
    (``$(DESTDIR)$(LDSO_PATHNAME)`` -> ``$(libdir)/libc.so``); doing it here keeps
    the install location under the repo's single location mechanism
    (paths.target_sysroot_dir, ADR-0016 D7) instead of a musl-side hard-coded
    prefix.
    """
    libdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(so, libdir / SONAME)
    link = libdir / LDSO_NAME
    if link.is_symlink() or link.exists():
        link.unlink()
    os.symlink(SONAME, link)
    return link


def check_ldso_symlink(link: Path, so: Path, inject: bool) -> list[tuple[str, str, str, bool]]:
    """The symlink must be a symlink, point at ``libc.so`` and resolve to it."""
    exp_target = SONAME if not inject else f"{SONAME}.bogus"
    if link.is_symlink():
        target = os.readlink(link)
        resolved = link.resolve()
        resolved_hash = sha256_of(resolved) if resolved.is_file() else "missing"
    else:
        target = "not a symlink"
        resolved_hash = "missing"
    exp_hash = sha256_of(so) if not inject else "0" * 64
    return [
        ("ld.so symlink is a symlink", "yes", "yes" if link.is_symlink() else "no",
         link.is_symlink()),
        ("ld.so symlink target", exp_target, target, target == exp_target),
        ("ld.so symlink resolves to libc.so", exp_hash, resolved_hash,
         resolved_hash == exp_hash),
    ]


# ── INFRA-108t: PIC static archive (ISS-303) ────────────────────────────────
def pic_archive_members() -> list[str]:
    """The PIC object list of the static library, read from musl's Makefile.

    ``LOBJS = $(LIBC_OBJS:.o=.lo)`` is the exact PIC counterpart of the member
    list of ``lib/libc.a`` (same objects, compiled with ``-fPIC``).  Querying
    the build system instead of re-deriving the source list here keeps the two
    archives in step: a second hand-written list would drift.

    The print target lives in a throw-away makefile passed with a second
    ``-f``; nothing inside the musl source tree is modified or left behind.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".mk", delete=False) as fh:
        fh.write(".PHONY: dadao-print-lobjs\n"
                 "dadao-print-lobjs:\n"
                 "\t@printf '%s\\n' $(LOBJS)\n")
        makefile = fh.name
    try:
        res = run(["make", "-s", "--no-print-directory", "-f", "Makefile",
                   "-f", makefile, "dadao-print-lobjs"],
                  cwd=MUSL_SRC, env=toolchain_env())
    finally:
        os.unlink(makefile)
    if res.returncode != 0:
        raise RuntimeError(f"make print-LOBJS rc={res.returncode}\n{res.stdout}")
    members = [line.strip() for line in res.stdout.splitlines()
               if line.strip().startswith("obj/") and line.strip().endswith(".lo")]
    if not members:
        raise RuntimeError("make printed no LOBJS members\n" + res.stdout)
    return members


def archive_member_names(path: Path) -> list[str]:
    """Names of an archive's members, in archive order (``ar t``)."""
    res = run(["ar", "t", str(path)])
    if res.returncode != 0:
        raise RuntimeError(f"ar t {path} rc={res.returncode}\n{res.stdout}")
    return [line for line in res.stdout.splitlines() if line.strip()]


def read_archive(path: Path) -> list[tuple[str, bytes]]:
    """(name, content) of every member of a GNU ``ar`` archive.

    Parsed here instead of shelling out to ``ar p`` per member because repeated
    basenames are legitimate (musl has ``src/malloc/free.o`` and
    ``src/malloc/mallocng/free.o``), and ``ar p <name>`` cannot address the
    second one.  Handles the GNU long-name table (``//`` + ``/N`` entries) and
    skips the symbol table.
    """
    data = path.read_bytes()
    if data[:8] != b"!<arch>\n":
        raise ValueError("not an ar archive")
    offset = 8
    longnames = b""
    members: list[tuple[str, bytes]] = []
    while offset + 60 <= len(data):
        header = data[offset:offset + 60]
        if header[58:60] != b"`\n":
            raise ValueError(f"bad ar member header at offset {offset}")
        name = header[0:16].decode("ascii").strip()
        size = int(header[48:58].decode("ascii").strip())
        body = data[offset + 60:offset + 60 + size]
        if len(body) != size:
            raise ValueError(f"truncated ar member {name!r} at offset {offset}")
        offset += 60 + size + (size & 1)
        if name == "//":
            longnames = body
            continue
        if name in ("/", "/SYM64/"):
            continue
        if name.startswith("/") and name[1:].isdigit():
            start = int(name[1:])
            end = longnames.index(b"/\n", start)
            name = longnames[start:end].decode("ascii")
        else:
            name = name.rstrip("/")
        members.append((name, body))
    return members


def build_pic_archive() -> list[tuple[str, str, str, bool]]:
    """Re-archive the ``.lo`` objects as ``lib/libc_pic.a`` and prove the result.

    Returns the check table (name, expected, actual, ok); the caller reports it
    and fails the build on any mismatch.  The decisive check compares every
    member's bytes with the ``.lo`` file it was archived from, so "this is the
    PIC build of the same libc" is verified rather than assumed; the member
    name list is compared against ``lib/libc.a`` (``.lo`` -> ``.o``) so the two
    archives cannot diverge in membership either.
    """
    members = pic_archive_members()
    archive = MUSL_SRC / "lib" / PIC_ARCHIVE
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    res = run(["ar", "rcsD", str(archive), *members], cwd=MUSL_SRC)
    if res.returncode != 0:
        raise RuntimeError(f"ar {PIC_ARCHIVE} rc={res.returncode}\n{res.stdout}")
    archived = read_archive(archive)
    archived_names = [name for name, _ in archived]
    pic_names = [Path(member).name for member in members]
    static_names = archive_member_names(MUSL_SRC / "lib" / "libc.a")
    mismatched = [
        (name, member)
        for (name, body), member in zip(archived, members)
        if hashlib.sha256(body).digest()
        != hashlib.sha256((MUSL_SRC / member).read_bytes()).digest()
    ]
    return [
        ("PIC archive built", "present",
         "present" if archive.is_file() else "absent", archive.is_file()),
        (f"{PIC_ARCHIVE} member count", str(len(members)), str(len(archived)),
         len(archived) == len(members)),
        (f"{PIC_ARCHIVE} member names == LOBJS (order)",
         f"{len(pic_names)} names", f"{len(archived_names)} names",
         archived_names == pic_names),
        (f"{PIC_ARCHIVE} member names == libc.a (.lo -> .o)",
         f"{len(static_names)} names",
         f"{len([Path(n).with_suffix('.o').name for n in archived_names])} names",
         static_names == [Path(n).with_suffix(".o").name
                          for n in archived_names]),
        (f"every {PIC_ARCHIVE} member == its source .lo (sha256)",
         f"{len(members)} match", f"{len(members) - len(mismatched)} match",
         not mismatched),
    ]


def install_pic_archive(libdir: Path) -> Path:
    """Install the PIC archive next to ``libc.so`` in the target lib dir."""
    libdir.mkdir(parents=True, exist_ok=True)
    dst = libdir / PIC_ARCHIVE
    shutil.copy2(MUSL_SRC / "lib" / PIC_ARCHIVE, dst)
    return dst


def check_installed_pic_archive(dst: Path) -> list[tuple[str, str, str, bool]]:
    """The installed PIC archive must be the build product, byte for byte."""
    src = MUSL_SRC / "lib" / PIC_ARCHIVE
    exp_hash = sha256_of(src) if src.is_file() else "missing"
    act_hash = sha256_of(dst) if dst.is_file() else "missing"
    return [
        (f"installed {PIC_ARCHIVE} present", "present",
         "present" if dst.is_file() else "absent", dst.is_file()),
        (f"installed {PIC_ARCHIVE} == build {PIC_ARCHIVE} (sha256)",
         exp_hash, act_hash, exp_hash == act_hash and exp_hash != "missing"),
    ]


def report_checks(checks: list[tuple[str, str, str, bool]], label: str) -> int:
    """Print one PASS/FAIL line per check; return the number of failures."""
    failed = 0
    for name, expected, actual, good in checks:
        print(f"build-musl: {'PASS' if good else 'FAIL'} {name}: "
              f"expected={expected} actual={actual}")
        if not good:
            failed += 1
    if failed:
        print(f"build-musl: FAIL ({failed}/{len(checks)} {label} checks)", file=sys.stderr)
    return failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", default=str(REPO_ROOT / ".work" / "build" / "musl-static"),
                    help="scratch dir for generated sources/objects/ELF")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--reconfig", action="store_true", help="force ./configure")
    ap.add_argument("--shared", action="store_true",
                    help="build/check the SHARED libc.so (PIC) instead of the static "
                         "subset (INFRA-085t stage A1)")
    ap.add_argument("--libdir", default=None,
                    help="install libc.so + the ld-musl symlink here "
                         "(default: the target sysroot lib dir, ADR-0016 D5)")
    ap.add_argument("--no-install", action="store_true",
                    help="shared mode only: skip installing libc.so + the ld.so symlink")
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
        rc = build_musl(args.jobs, args.reconfig, args.shared)
        if rc:
            return rc

    if args.shared:
        # The shared-object criteria plus the ld.so symlink; the static smoke
        # below still runs, so a regression on the static line is caught in the
        # same invocation (both modes share lib/libc.a).
        so = MUSL_SRC / "lib" / SONAME
        tag_lines = "\n".join(
            f"  ({t:#x}) {t:#x}" for t in sorted(dict(parse_elf(so)["dynamic"] or [])))
        print(f"build-musl: dynamic tags of {so}:\n{tag_lines}")
        checks = check_shared_elf(so, args.inject)
        # INFRA-108t: the PIC static archive for -static-pie.  Built from the
        # same .lo objects on every shared run (cheap: ar + content check), so
        # it can never lag behind libc.a/libc.so.
        pic_checks = build_pic_archive()
        if report_checks(pic_checks, "pic-archive"):
            return 1
        if not args.no_install:
            libdir = Path(args.libdir) if args.libdir else paths.target_sysroot_dir() / "lib"
            link = install_ldso(so, libdir)
            print(f"build-musl: installed {libdir / SONAME} + {link} -> {SONAME}")
            checks += check_ldso_symlink(link, so, args.inject)
            pic = install_pic_archive(libdir)
            print(f"build-musl: installed {pic}")
            checks += check_installed_pic_archive(pic)
        if report_checks(checks, "shared"):
            return 1
        if args.no_smoke:
            print(f"build-musl: shared OK ({len(checks)}/{len(checks)} checks) so={so}")
            return 0

        # ── stage B1: link a DYNAMIC EXECUTABLE against that libc.so ────────
        # The interpreter is passed explicitly (contract-dynlink.md §6.1,
        # ADR-0026 D2); see link_dynamic_program for why the static link
        # script cannot be reused here.
        dynwork = Path(args.work_dir)
        dynwork.mkdir(parents=True, exist_ok=True)
        try:
            dobj = compile_program(dynwork)
            delf = link_dynamic_program(dynwork, dobj, so)
        except RuntimeError as exc:
            print(f"build-musl: FAIL ({exc})", file=sys.stderr)
            return 1
        raw = interp_bytes(parse_elf(delf))
        print(f"build-musl: PT_INTERP of {delf} = "
              + " ".join(f"{b:02x}" for b in raw)
              + f"  ({raw!r})")
        dyn_checks = check_dynamic_exe(delf, args.inject)
        if report_checks(dyn_checks, "dynamic-executable"):
            return 1

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

    if report_checks(checks, "static"):
        return 1

    res = run(["file", str(elf)])
    print(f"build-musl: file(1): {res.stdout.strip()}")
    print(f"build-musl: OK ({len(checks)}/{len(checks)} checks) elf={elf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
