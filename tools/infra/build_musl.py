#!/usr/bin/env python3
"""Build the musl library for dadao-unknown-elf and check the produced ELFs.

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

INFRA-085t stage A1 ("shared library and PIC") adds a second, SHARED mode
(``--shared``, ``make build-musl-shared``):

4. **shared build** -- ``./configure`` *without* ``--disable-shared`` (musl
   compiles the ``.lo`` objects with ``-fPIC`` and links ``lib/libc.so``) plus
   ``LDFLAGS`` that pin the contract's dynamic-section shape: GNU hash only and
   a ``DT_SONAME`` (``contract-dynlink.md`` §5 rulings 6/7, §6.1).
5. **shared checks** -- ``readelf``-level facts read straight out of the file:
   ET_DYN / big-endian / EM_DADAO, ``PT_DYNAMIC``, ``DT_SONAME`` == ``libc.so``,
   ``DT_GNU_HASH``, and the ABSENCE of ``DT_HASH`` / ``DT_RELR`` / ``DT_RELRSZ``
   / the version tags and of every ``.gnu.version*`` section.
6. **ld.so symlink** -- ``libc.so`` is installed next to a
   ``ld-musl-dadao.so.1 -> libc.so`` symlink in the target sysroot lib dir
   (ADR-0016 D5; the path ``/lib/ld-musl-dadao.so.1`` is what
   ``contract-dynlink.md`` §6.1 fixes as ``PT_INTERP``), and the symlink is
   checked to resolve to the built ``libc.so`` byte-for-byte.

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
code and the link result (``clang``, ``ld.lld``), their resolved path, size,
mtime, ctime and ``--version`` line in ``obj/.dadao-toolchain-stamp``; a
mismatch -- or a missing stamp -- runs ``make clean`` first and records the new
stamp before building, and the decision is always logged.

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

# ── shared-object (dynamic linkage) names, INFRA-085t stage A1 ──────────────
# contract-dynlink.md §6.1: PT_INTERP = /lib/ld-musl-dadao.so.1, that path being
# a symlink to libc.so; musl's own name for the DSO is "libc.so"
# (ldso/dynlink.c sets `ldso.name = ldso.shortname = "libc.so"`), which is what
# the DT_SONAME and the symlink target below use.
SONAME = "libc.so"
LDSO_NAME = "ld-musl-dadao.so.1"
# musl's configure probes `--hash-style=both` into LDFLAGS_AUTO; §5 ruling 6
# ("only GNU hash, no DT_HASH") and the required DT_SONAME are imposed here.
# LDFLAGS_ALL = $(LDFLAGS_AUTO) $(LDFLAGS) and lld reads the LAST occurrence of
# --hash-style, so the trailing --hash-style=gnu wins.
#
# `-Wl,-shared` is not redundant with musl's Makefile: the DADAO clang driver
# forwards only -T/-L/-e/-u/-s/-r to ld.lld (clang/lib/Driver/ToolChains/
# DADAO.cpp Linker::ConstructJob), so a bare driver-level `-shared` never
# reaches the linker and the "shared" link silently produces an ET_EXEC with no
# .dynamic at all (see issues.yaml ISS-239).  Passing it through -Wl, is the
# build-side way to get a real shared link without touching musl's Makefile
# (ADR-0026 D2: the build call site passes the behaviour explicitly).
SHARED_LDFLAGS = f"-Wl,-shared -Wl,--hash-style=gnu -Wl,-soname,{SONAME}"

# ELF constants used by the shared-object checks (gABI ch. 5 + lld's values).
PT_LOAD = 1
PT_DYNAMIC = 2
ET_DYN = 3
DT_NULL = 0
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


def config_records(shared: bool) -> bool:
    """True when the existing config.mak was generated for the wanted mode.

    Both modes build in the same in-tree directory, and musl records its
    configure command line in config.mak; switching modes therefore has to
    re-run configure, otherwise ``make build-musl`` would silently keep the
    shared configuration (and with it libc.so) after a ``build-musl-shared``
    run -- i.e. the static target would stop proving the --disable-shared
    configuration.
    """
    config = MUSL_SRC / "config.mak"
    if not config.is_file():
        return False
    text = config.read_text(errors="replace")
    return ("--disable-shared" in text) != shared


# ── toolchain staleness guard (INFRA-085t) ──────────────────────────────────
# See the module docstring ("A toolchain stamp guards both modes").  The stamp
# lives inside musl's generated obj/ directory: musl's .gitignore covers /obj/,
# so the source tree stays clean for check-source-state, and `make clean`
# (which removes obj/) both invalidates it and is itself the remedy.
#
# Why not a sha256 of the binaries: the installed clang is 4.0 GB and lld
# 2.1 GB, i.e. >6 GB of I/O on every single build for a guard that has to be
# cheap enough to run unconditionally.  size+ctime+mtime cannot miss a rewrite
# (any write to an existing file bumps ctime, which user space cannot set
# back), and the version line adds the upstream revision the binaries were
# built from.  A preserved-mtime copy still lands as a new ctime (and usually
# a new inode), so the "reinstalled with the same timestamp" case is covered.
STAMP_TOOLS = ("clang", "ld.lld")
STAMP_REL = Path("obj") / ".dadao-toolchain-stamp"


def toolchain_stamp() -> str:
    """One line per code-deciding toolchain binary: what the objects were built by."""
    lines = []
    for tool in STAMP_TOOLS:
        path = TOOLCHAIN_BIN / tool
        real = path.resolve()
        st = real.stat()
        res = run([str(path), "--version"])
        version = ((res.stdout.splitlines() or [""])[0] if res.returncode == 0
                   else f"rc={res.returncode}")
        lines.append(f"{tool} -> {real} size={st.st_size} "
                     f"mtime={st.st_mtime_ns} ctime={st.st_ctime_ns} {version}")
    return "\n".join(lines) + "\n"


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
    if stored.strip() == current.strip():
        return False, "toolchain stamp unchanged (objects are up to date)", current
    return True, "toolchain stamp changed", current


def build_musl(jobs: int, reconfig: bool, shared: bool) -> int:
    if not MUSL_SRC.is_dir():
        print(f"build-musl: ERROR: {MUSL_SRC} not found -- run 'make fetch apply-series'",
              file=sys.stderr)
        return 2
    env = toolchain_env()
    if reconfig or not config_records(shared):
        cmd = ["./configure", f"--target={TARGET}",
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
    if changed:
        print(f"build-musl: {reason} => 'make clean' (full rebuild)")
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
    else:
        print(f"build-musl: {reason} => incremental build")
    res = run(["make", f"-j{jobs}"], cwd=MUSL_SRC, env=env)
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
    exp_soname = SONAME if not inject else f"{SONAME}.bogus"
    soname = dyn_string(info, tags, DT_SONAME)
    checks = [
        ("shared object parsed", "no parse error", info["parse_error"] or "no parse error",
         info["parse_error"] is None),
        ("ELF class", "2 (ELFCLASS64)", str(info["ei_class"]),
         info["ei_class"] == exp_class),
        ("ELF data", "2 (ELFDATA2MSB, big-endian)", str(info["ei_data"]),
         info["ei_data"] == exp_data),
        ("ELF type", "3 (ET_DYN)", str(info["e_type"]), info["e_type"] == exp_type),
        ("e_machine", f"0x{EM_DADAO:04x} (EM_DADAO)", f"0x{info['e_machine']:04x}",
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
        if not args.no_install:
            libdir = Path(args.libdir) if args.libdir else paths.target_sysroot_dir() / "lib"
            link = install_ldso(so, libdir)
            print(f"build-musl: installed {libdir / SONAME} + {link} -> {SONAME}")
            checks += check_ldso_symlink(link, so, args.inject)
        if report_checks(checks, "shared"):
            return 1
        if args.no_smoke:
            print(f"build-musl: shared OK ({len(checks)}/{len(checks)} checks) so={so}")
            return 0

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
