#!/usr/bin/env python3
"""build-busybox (m14-linux-030): static musl busybox 1.38.0 for dadao-unknown-elf.

K6 needs a *static* busybox (no ldso, ADR-0052 as revised 2026-11-17) carrying a
minimal applet set: ``sh`` + ``ls/cat/echo/mkdir/rm/cp/mv/grep/ps``.  This
script is the one build entry point (``make build-busybox``); the minimal
config's *source of truth* is ``components/busybox/config.min``.

What it does
------------
1. **Config** -- ``make allnoconfig`` (everything off), flip the fragment's
   ``CONFIG_<SYM>=y`` entries on, ``make silentoldconfig`` so Kconfig resolves
   ``select``/depends, then **re-assert** every requested symbol is still ``y``
   (busybox silently turns a symbol off when a dependency is unmet -- that must
   fail here, never produce a smaller shell).  Symbols the task book wants left
   out (PAM, line editing/job control) are asserted absent.
2. **Build** -- ``make -j.. CC=<generated wrapper> HOSTCC=<host cc>``.  The
   DADAO clang driver is *freestanding* (no implicit libc link, see
   ``clang/lib/Driver/ToolChains/DADAO.cpp``), so the wrapper appends musl's
   ``lib/crt1.o`` + ``lib/libc.a`` to the **final** link only (``-c/-E/-S/-M``
   and the relocatable ``-r`` links stay untouched).  Headers come from the
   musl source tree, exactly like the project static user-space flow: the target
   sysroot under ``.dadao/dadao-unknown-elf`` is the picolibc install and does
   **not** carry musl's ``features.h``.
3. **Provenance** -- ``SOURCE_DATE_EPOCH`` = the component commit's committer
   time, so ``AUTOCONF_TIMESTAMP`` (which busybox embeds in
   ``libbb/messages.c``'s banner) and therefore the ELF hash are reproducible
   across runs (``scripts/kconfig/confdata.c`` honours it).
4. **Artefact** -- ELF header/program headers are parsed here in Python (no
   readelf dependency): ``ELF64``/big-endian/``machine 0xDA0``/``ET_EXEC`` and
   **no** ``PT_INTERP`` / ``PT_DYNAMIC``.  The binary is copied to
   ``.work/build/busybox/busybox`` (build product root) and its sha256 printed.

Prerequisites (missing ones are hard errors, never silent fallbacks)
--------------------------------------------------------------------
* ``make fetch`` -- the component checkout ``.work/source/busybox`` at the
  ``busybox`` commit pinned in ``manifests/components.lock.toml``.
* ``tools/infra/apply_series.py --component busybox`` -- the v5 patch set
  (source tree then sits at pinned-commit + 1, tree clean).
* ``make install-host`` -- ``.dadao/cross-toolchain/bin/clang``/``ld.lld``.
* ``make build-musl`` -- ``.work/source/musl/lib/{crt1.o,libc.a}``.

Runtime checks (``busybox --version`` / ``--list`` under ``qemu-dadao``) are
*not* done here: they belong to the K6 evidence (the runtime gate is
``m18-linux-003``).  ``.work/evidence/m14-linux-030/run.sh`` runs them.
"""
from __future__ import annotations

import argparse
import codecs
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT = "busybox"
TARGET = "dadao-unknown-elf"
COMPONENTS_LOCK = REPO_ROOT / "manifests" / "components.lock.toml"
FRAGMENT = REPO_ROOT / "components" / "busybox" / "config.min"

# Single source of truth for the toolchain bin/ and the musl build tree
# (`tools/infra/build_musl.py` owns both paths; no second copy here).
sys.path.insert(0, str(REPO_ROOT))
from tools.infra import build_musl  # noqa: E402

TOOLCHAIN_BIN = build_musl.TOOLCHAIN_BIN
MUSL_SRC = build_musl.MUSL_SRC

# Headers as the *project's* static user-space flow uses them (same order as
# build_musl.py's MUSL_INCLUDE_DIRS).
MUSL_INCLUDE_DIRS = ("arch/dadao", "arch/generic", "obj/src/internal",
                     "src/include", "src/internal", "obj/include", "include")

# Absent-by-design (task book: no PAM, no line editing / job control).
FORBIDDEN = ("CONFIG_PAM", "CONFIG_FEATURE_EDITING", "CONFIG_FEATURE_TAB_COMPLETION")

EM_DADAO = 0xDA0
PT_DYNAMIC = 2
PT_INTERP = 3


class SetupError(RuntimeError):
    """Prerequisite missing: the caller must fix the environment first."""


def run(cmd: list[str], *, cwd: Path, env: dict | None = None,
        timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=timeout)
    return proc


def run_checked(cmd: list[str], *, cwd: Path, env: dict | None = None,
                what: str) -> subprocess.CompletedProcess[str]:
    proc = run(cmd, cwd=cwd, env=env)
    if proc.returncode != 0:
        raise SetupError(f"{what}: rc={proc.returncode}\n$ {' '.join(cmd)}\n{proc.stdout}")
    return proc


# ── manifest / layout ───────────────────────────────────────────────────────

def component() -> dict:
    with COMPONENTS_LOCK.open("rb") as stream:
        manifest = tomllib.load(stream)
    for entry in manifest.get("component", []):
        if entry.get("name") == COMPONENT:
            return entry
    raise SetupError(f"{COMPONENTS_LOCK.name}: component {COMPONENT!r} is not registered")


def work_root() -> Path:
    with COMPONENTS_LOCK.open("rb") as stream:
        manifest = tomllib.load(stream)
    root = manifest.get("work_root", "")
    if not root or Path(root).is_absolute():
        raise SetupError(f"{COMPONENTS_LOCK.name}: work_root must be repo-relative, got {root!r}")
    return REPO_ROOT / root


def source_dir() -> Path:
    return work_root() / "source" / COMPONENT


def build_dir() -> Path:
    return work_root() / "build" / COMPONENT


# ── toolchain / prerequisites ───────────────────────────────────────────────

def require_prerequisites() -> tuple[Path, Path]:
    clang = TOOLCHAIN_BIN / "clang"
    for tool in (clang, TOOLCHAIN_BIN / "ld.lld", TOOLCHAIN_BIN / "llvm-strip"):
        if not tool.is_file():
            raise SetupError(f"{tool} not found -- run `make install-host` first")
    for product in (MUSL_SRC / "lib" / "crt1.o", MUSL_SRC / "lib" / "libc.a"):
        if not product.is_file():
            raise SetupError(f"{product} not found -- run `make build-musl` first")
    src = source_dir()
    if not (src / ".git").exists():
        raise SetupError(
            f"{src} is not a git checkout -- run `make fetch` "
            f"(manifest pins {COMPONENT} at its exact commit)")
    return clang, src


def commit_epoch(src: Path, commit: str) -> int:
    proc = run_checked(["git", "log", "-1", "--format=%ct", commit], cwd=src,
                       what="git log for the pinned commit")
    return int(proc.stdout.strip())


def check_source_state(src: Path, commit: str) -> None:
    """The tree must be the pinned commit plus the applied v5 patch set (clean)."""
    head = run_checked(["git", "rev-parse", "HEAD"], cwd=src, what="git rev-parse").stdout.strip()
    ancestor = run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=src)
    if ancestor.returncode != 0:
        raise SetupError(
            f"{src}: HEAD {head[:12]} is not a descendant of the pinned commit "
            f"{commit[:12]} -- run `make fetch` for {COMPONENT}")
    status = run_checked(["git", "status", "--porcelain"], cwd=src,
                         what="git status").stdout
    if status.strip():
        raise SetupError(
            f"{src}: worktree is not clean (patch series not applied, or local edits):\n"
            f"{status.rstrip()}\nrun `tools/infra/apply_series.py --component {COMPONENT}`")


def toolchain_env(epoch: int) -> dict:
    """Environment for every child: reproducible timestamp, no inherited knobs."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("CC", "CXX", "CFLAGS", "LDFLAGS", "CPPFLAGS", "HOSTCC",
                        "CROSS_COMPILE", "ARCH", "KBUILD_BUILD_TIMESTAMP")}
    env["SOURCE_DATE_EPOCH"] = str(epoch)
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    env["TZ"] = "UTC"
    env["PATH"] = f"{TOOLCHAIN_BIN}:{env.get('PATH', '')}"
    return env


def write_cc_wrapper(build: Path, clang: Path) -> Path:
    """`clang --target=... <musl headers>` + explicit crt/libc on final links."""
    tools_dir = build / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    wrapper = tools_dir / "cc-dadao"
    inc = " ".join(f'-I"{MUSL_SRC / d}"' for d in MUSL_INCLUDE_DIRS)
    body = f"""#!/bin/sh
# Generated by tools/linux/build_busybox.py (runtime artefact, do not edit).
# Compile: the DADAO driver is freestanding and the target sysroot is the
# picolibc install, so musl's own headers are passed explicitly.
# Final link: append crt1.o + libc.a (the driver does not add them).
T={TARGET}
CLANG="{clang}"
MUSL="{MUSL_SRC}"
INC="-nostdinc {inc}"
LIB="-L\"$MUSL/lib\""
link=1
for a in "$@"; do
  case "$a" in -c|-E|-S|-M|-MM|-r) link=0 ;; esac
done
if [ "$link" = 1 ]; then
  exec "$CLANG" --target=$T $INC $LIB "$@" "$MUSL/lib/crt1.o" "$MUSL/lib/libc.a"
fi
exec "$CLANG" --target=$T $INC "$@"
"""
    if not wrapper.is_file() or wrapper.read_text(encoding="utf-8") != body:
        wrapper.write_text(body, encoding="utf-8")
    wrapper.chmod(0o755)
    return wrapper


# ── config ──────────────────────────────────────────────────────────────────

FRAGMENT_RE = re.compile(r"^(CONFIG_[A-Z0-9_]+)=(.*)$")
SETTING_RE = re.compile(r"^(?:CONFIG_([A-Z0-9_]+)=|# CONFIG_([A-Z0-9_]+) is not set$)")


def read_fragment() -> dict[str, str]:
    if not FRAGMENT.is_file():
        raise SetupError(f"config fragment {FRAGMENT} is missing")
    wanted: dict[str, str] = {}
    for lineno, raw in enumerate(FRAGMENT.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = FRAGMENT_RE.match(line)
        if not match:
            raise SetupError(f"{FRAGMENT}:{lineno}: expected `CONFIG_<SYM>=<value>`, got {line!r}")
        symbol, value = match.group(1), match.group(2)
        if symbol in wanted:
            raise SetupError(f"{FRAGMENT}:{lineno}: duplicate {symbol}")
        wanted[symbol] = value
    if not wanted:
        raise SetupError(f"{FRAGMENT}: no CONFIG_ entry -- refusing to build an empty shell")
    return wanted


def config_state(text: str) -> dict[str, str]:
    """`.config` -> {symbol: value}; unset symbols map to `'n'`."""
    state: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("# CONFIG_") and line.endswith(" is not set"):
            state[line[len("# "):-len(" is not set")]] = "n"
            continue
        if line.startswith("CONFIG_") and "=" in line:
            symbol, _, value = line.partition("=")
            state[symbol] = value
    return state


def apply_fragment(src: Path, wanted: dict[str, str]) -> None:
    config = src / ".config"
    if not config.is_file():
        raise SetupError(f"{config} missing after allnoconfig")
    lines = config.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        match = SETTING_RE.match(line)
        symbol = f"CONFIG_{match.group(1) or match.group(2)}" if match else None
        if symbol and symbol in wanted:
            out.append(f"{symbol}={wanted[symbol]}")
            seen.add(symbol)
        else:
            out.append(line)
    missing = sorted(set(wanted) - seen)
    if missing:
        # allnoconfig enumerates every known symbol: an absent one is a typo in
        # the fragment (or an upstream rename), never "just defaults".
        raise SetupError(f"fragment symbols unknown to this busybox tree: {', '.join(missing)}")
    config.write_text("\n".join(out) + "\n", encoding="utf-8")


def assert_config(src: Path, wanted: dict[str, str]) -> None:
    state = config_state((src / ".config").read_text(encoding="utf-8"))
    bad = [f"{sym}={wanted[sym]} -> {state.get(sym, 'absent')}"
           for sym in sorted(wanted) if state.get(sym) != wanted[sym]]
    if bad:
        raise SetupError(
            "config: requested symbols did not survive Kconfig dependency "
            "resolution (enable the missing dependency in components/busybox/"
            "config.min):\n  " + "\n  ".join(bad))
    leftovers = [f"{sym}={state.get(sym, 'absent')}" for sym in FORBIDDEN
                 if state.get(sym, "n") != "n"]
    if leftovers:
        raise SetupError("config: symbols that must stay off are enabled: "
                         + ", ".join(leftovers))


# ── config currency (two-way: the fragment IS the only truth source) ────────

FRAGMENT_RECORD_NAME = ".dadao-busybox-fragment"


def read_fragment_record(build: Path) -> set[str] | None:
    path = build / FRAGMENT_RECORD_NAME
    if not path.is_file():
        return None
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()}


def write_fragment_record(build: Path, wanted: dict[str, str]) -> None:
    (build / FRAGMENT_RECORD_NAME).write_text(
        "".join(f"{symbol}\n" for symbol in sorted(wanted)), encoding="utf-8")


def config_stale_reason(src: Path, build: Path, wanted: dict[str, str]) -> str | None:
    """Why `.config` may NOT be reused, or ``None`` when it is current.

    The fragment is the single source of truth, so *shrinking* it must count as
    a change just like adding a symbol: the record of the symbol set that
    produced this `.config` is compared **both ways** (a subset test alone would
    keep a stale `.config` alive after a symbol is deleted -- exactly the
    reviewer's I-B counterexample).  Values are then re-checked against the
    fragment so a hand-edited `.config` is also regenerated instead of trusted.
    """
    recorded = read_fragment_record(build)
    current = set(wanted)
    if recorded is None:
        return "no fragment record (the .config predates the two-way check)"
    if recorded != current:
        removed = sorted(recorded - current)
        added = sorted(current - recorded)
        return ("fragment symbol set changed: "
                f"added={added or 'none'} removed={removed or 'none'}")
    config = src / ".config"
    if not config.is_file():
        return "no .config"
    state = config_state(config.read_text(encoding="utf-8"))
    drifted = [f"{sym}={state.get(sym, 'absent')} (want {val})"
               for sym, val in sorted(wanted.items()) if state.get(sym) != val]
    if drifted:
        return "'.config' drifted from the fragment: " + ", ".join(drifted)
    forbidden = [f"{sym}={state.get(sym, 'n')}" for sym in FORBIDDEN
                 if state.get(sym, "n") != "n"]
    if forbidden:
        return "'.config' has symbols that must stay off: " + ", ".join(forbidden)
    return None


# ── build stamp (stale-object guard) ────────────────────────────────────────

STAMP_NAME = ".dadao-busybox-stamp"


def build_stamp(clang: Path, wrapper: Path) -> str:
    """Digest of every *build input* outside the component's own source.

    busybox's kbuild is incremental, so a rebuilt toolchain / musl archive would
    otherwise relink with stale objects and look fine (`build-musl` keeps the
    same guard).  The toolchain binaries are multi-GB, so they contribute
    size+mtime; the two archives are small enough to hash.
    """
    digest = hashlib.sha256()
    digest.update(b"busybox-build-stamp/1\0" + TARGET.encode() + b"\0")
    for tool in (clang, TOOLCHAIN_BIN / "ld.lld", TOOLCHAIN_BIN / "llvm-strip"):
        stat = tool.stat()
        digest.update(f"tool {tool.name} {stat.st_size} {stat.st_mtime_ns}\0".encode())
    for archive in (MUSL_SRC / "lib" / "crt1.o", MUSL_SRC / "lib" / "libc.a"):
        digest.update(f"musl {archive.name}\0".encode())
        digest.update(hashlib.sha256(archive.read_bytes()).digest())
    digest.update(b"fragment\0" + FRAGMENT.read_bytes())
    digest.update(b"wrapper\0" + wrapper.read_bytes())
    return digest.hexdigest()


def stale_reason(build: Path, stamp: str) -> str | None:
    path = build / STAMP_NAME
    if not path.is_file():
        return "no build stamp"
    if path.read_text(encoding="utf-8").strip() != stamp:
        return "toolchain/musl/config changed since the last build"
    return None


# ── applet table (generated by the build) ───────────────────────────────────

def applet_names(header: Path) -> list[str]:
    """Applet names from the generated ``include/applet_tables.h``.

    The array literal is ``const char applet_names[] ALIGN1 = "" "ash" "\\0" …``,
    i.e. one C string per applet with an explicit NUL separator.
    """
    if not header.is_file():
        raise SetupError(f"{header} missing -- did the build generate applet tables?")
    match = re.search(r"applet_names\[\][^=]*=(.*?);", header.read_text(encoding="utf-8"),
                      re.S)
    if not match:
        raise SetupError(f"{header}: no applet_names array")
    literals = re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1))
    joined = "".join(codecs.decode(literal, "unicode_escape") for literal in literals)
    names = sorted(name for name in joined.split("\x00") if name)
    if not names:
        raise SetupError(f"{header}: applet_names is empty")
    return names


# ── ELF checks (independent of readelf) ─────────────────────────────────────

def elf_program_header_types(path: Path) -> tuple[int, int, int, int, set[int]]:
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise SetupError(f"{path}: not an ELF file")
    ei_class, ei_data = data[4], data[5]
    e_type, e_machine = struct.unpack_from(">HH", data, 16)
    e_phoff, = struct.unpack_from(">Q", data, 32)
    e_phentsize, e_phnum = struct.unpack_from(">HH", data, 54)
    types: set[int] = set()
    for index in range(e_phnum):
        off = e_phoff + index * e_phentsize
        p_type, = struct.unpack_from(">I", data, off)
        types.add(p_type)
    return ei_class, ei_data, e_type, e_machine, types


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the static musl busybox for dadao-unknown-elf "
                    "(m14-linux-030).")
    parser.add_argument("--jobs", type=int,
                        default=int(os.environ.get("JOBS") or 32),
                        help="parallel make jobs (default: $JOBS or 32)")
    parser.add_argument("--hostcc", default=os.environ.get("HOSTCC") or "gcc",
                        help="host compiler for busybox's own kconfig/table tools")
    parser.add_argument("--clean", action="store_true",
                        help="`make clean` first (idempotency / reproducibility runs)")
    parser.add_argument("--check-config", action="store_true",
                        help="only report whether `.config` is current w.r.t. "
                             "config.min (two-way); exit 1 when a rebuild would "
                             "regenerate it")
    args = parser.parse_args()

    if args.check_config:
        try:
            wanted = read_fragment()
            stale = config_stale_reason(source_dir(), build_dir(), wanted)
        except SetupError as exc:
            print(f"build-busybox: FAIL\n{exc}", file=sys.stderr)
            return 1
        if stale is None:
            print(f"build-busybox: config current ({len(wanted)} fragment symbols)")
            return 0
        print(f"build-busybox: config STALE: {stale}")
        return 1

    try:
        entry = component()
        if not entry.get("enabled"):
            raise SetupError(f"component {COMPONENT}: not enabled in the lock")
        commit = entry.get("commit", "")
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise SetupError(f"component {COMPONENT}: needs a full 40-char commit")
        clang, src = require_prerequisites()
        check_source_state(src, commit)
        epoch = commit_epoch(src, commit)
        env = toolchain_env(epoch)
        build = build_dir()
        build.mkdir(parents=True, exist_ok=True)
        wrapper = write_cc_wrapper(build, clang)

        stamp = build_stamp(clang, wrapper)
        reason = "--clean" if args.clean else stale_reason(build, stamp)
        if reason:
            print(f"build-busybox: {reason} => make clean")
            run_checked(["make", "clean"], cwd=src, env=env, what="make clean")
            (build / STAMP_NAME).unlink(missing_ok=True)
        else:
            print("build-busybox: build inputs unchanged (incremental)")

        wanted = read_fragment()
        stale = config_stale_reason(src, build, wanted)
        if stale is None:
            print(f"build-busybox: config current ({len(wanted)} fragment symbols)")
        else:
            print(f"build-busybox: configuring ({len(wanted)} symbols, "
                  f"{FRAGMENT.relative_to(REPO_ROOT)}): {stale}")
            run_checked(["make", f"HOSTCC={args.hostcc}", "allnoconfig"],
                        cwd=src, env=env, what="make allnoconfig")
            apply_fragment(src, wanted)
            run_checked(["make", f"HOSTCC={args.hostcc}", "silentoldconfig"],
                        cwd=src, env=env, what="make silentoldconfig")
            assert_config(src, wanted)
            write_fragment_record(build, wanted)

        print(f"build-busybox: building (jobs={args.jobs}, "
              f"CC={wrapper.relative_to(REPO_ROOT)})")
        # ARCH=dadao: busybox's default `ARCH` is `uname -m` (the *host*), which
        # is wrong for a cross build and would drag in x86-only assembly
        # (see the ported libbb/Kbuild.src.patch).  STRIP must be the LLVM one:
        # the host binutils `strip` cannot read a DADAO ELF.
        proc = run(["make", f"-j{args.jobs}", "ARCH=dadao", f"CC={wrapper}",
                    f"HOSTCC={args.hostcc}",
                    f"STRIP={TOOLCHAIN_BIN / 'llvm-strip'}"], cwd=src, env=env)
        if proc.returncode != 0:
            raise SetupError(f"make rc={proc.returncode}\n{proc.stdout}")

        artefact = src / "busybox"
        if not artefact.is_file():
            raise SetupError(f"{artefact} was not produced (make said success)")
        ei_class, ei_data, e_type, e_machine, phdrs = elf_program_header_types(artefact)
        problems = []
        if ei_class != 2:
            problems.append(f"class={ei_class} (want ELF64)")
        if ei_data != 2:
            problems.append(f"data={ei_data} (want MSB)")
        if e_type != 2:
            problems.append(f"e_type={e_type} (want ET_EXEC)")
        if e_machine != EM_DADAO:
            problems.append(f"e_machine=0x{e_machine:x} (want 0xda0)")
        if PT_INTERP in phdrs:
            problems.append("PT_INTERP present (not static)")
        if PT_DYNAMIC in phdrs:
            problems.append("PT_DYNAMIC present (not static)")
        if problems:
            raise SetupError("artefact is not the required static DADAO ELF: "
                             + "; ".join(problems))

        product = build / "busybox"
        shutil.copy2(artefact, product)
        digest = hashlib.sha256(product.read_bytes()).hexdigest()
        if hashlib.sha256(artefact.read_bytes()).hexdigest() != digest:
            raise SetupError(f"copy to {product} does not match the build product")
        # Downstream K6 tasks (initramfs applet links, m14-linux-031) read these
        # two product-side copies instead of the throw-away source tree.
        shutil.copy2(src / ".config", build / ".config")
        applets = applet_names(src / "include" / "applet_tables.h")
        (build / "applets.txt").write_text("".join(f"{name}\n" for name in applets),
                                           encoding="utf-8")
        print(f"build-busybox: product {product.relative_to(REPO_ROOT)} "
              f"({product.stat().st_size} bytes, sha256 {digest})")
        print(f"build-busybox: {len(applets)} applet(s): {' '.join(applets)}")
        (build / STAMP_NAME).write_text(stamp + "\n", encoding="utf-8")
        (build / STAMP_NAME).write_text(stamp + "\n", encoding="utf-8")
        print("build-busybox: PASS")
        return 0
    except SetupError as exc:
        print(f"build-busybox: FAIL\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
