#!/usr/bin/env python3
"""Install-set assertion (ISS-261, INFRA-098t).

The install root (ADR-0016 D9) is the only tool source for the gates and the
executors, so "a tool the gates need is missing from it" is a hard failure --
not something to discover later as a `command not found` inside a test run.
`ISS-261` was exactly that: `llvm-nm` and `llvm-readelf` existed in the build
tree (or could be generated) but were never installed.

Single source of truth
----------------------
The expected install set is read **from the Makefile itself**:
``HOST_LLVM_TOOLS`` (real copies staged by ``atomic-install``) and
``HOST_LLVM_TOOL_SYMLINKS`` (zero-copy aliases ``<link>:<target>``).  Nothing
is duplicated here, so adding/removing a tool in the Makefile automatically
extends/shrinks this assertion, and a Makefile that loses either variable is a
FAIL rather than a vacuous pass.

Checks (each has a reachable FAIL path, see ``--self-test``)
------------------------------------------------------------
1. structure: both Makefile variables exist and are non-empty; alias specs are
   ``<link>:<target>``; no name appears both as a copy and as an alias.
2. every real tool: present in the install root, executable, ``--version``
   exits 0; its size matches the build-tree counterpart (always) and, when the
   content mode is on, so does its sha256.
3. every alias: is a *relative* symlink to its declared target (a copy would
   defeat the zero-copy intent), resolves to an executable, ``--version``
   exits 0, and the target's size/sha256 matches the build tree's.
4. ``llvm-readelf -h`` parses the big-endian DADAO probe object: ``Data:`` says
   big endian and ``Machine:`` is DADAO (EM_DADAO / 0xda0).  The probe object
   is only read, never modified; a missing probe is a SKIP, a wrong parse is a
   FAIL.
5. ``llvm-ar`` round-trips that probe: two members in, ``llvm-ar t`` lists the
   same member set, ``llvm-ar x`` extracts members byte-identical to the probe
   (sha256).  (m14-llvm-001; kernel build's ``AR``.)
6. ``llvm-ranlib`` writes the archive symbol table: build with ``llvm-ar rcS``
   (no index), assert ``llvm-nm --print-armap`` shows no entries, run
   ``llvm-ranlib``, assert entries appear and ``llvm-ar t`` still lists the
   members.  (m14-llvm-001; kernel build's ``RANLIB``.  Note ``llvm-nm -s`` is
   a Mach-O option, so the GNU armap probe is ``--print-armap``.)
7. ``llvm-strip --strip-all`` keeps the object usable: still big-endian DADAO
   (``llvm-readelf -h``) and ``llvm-objdump -d`` still disassembles it.
   (m14-llvm-001; kernel build's ``STRIP``.)

The functional group (5-7) uses the same probe object and is SKIPped when it is
missing; all scratch files live under ``/tmp/opencode/check-install-tools/`` and
are removed in a ``finally`` block.

Content mode (``--sha`` / ``--sha-tools a,b``) is opt-in because the install
set is ~11 GB per side: hashing both sides costs ~2 min, while size+``--version``
is <1 s.  ``install-host`` runs the fast mode (it just atomic-copied the files);
the byte-identity claim for specific tools is proven on demand.

Usage
-----
  tools/infra/check_install_tools.py                     # real install root
  tools/infra/check_install_tools.py --sha-tools llvm-nm,llvm-readelf
  tools/infra/check_install_tools.py --root DIR --build-dir DIR [--sha]
  tools/infra/check_install_tools.py --self-test

Cost: ~0.2 s fast mode, + ~1.8 s per 342 MB file in content mode.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

# Build-side tool directory (the single build truth, ADR-0016 D9).
BUILD_BIN_REL = Path(".work") / "build" / "llvm" / "bin"
# Big-endian DADAO object (musl rcrt1.o, ELFDATA2MSB + EM_DADAO) used to prove
# that the installed llvm-readelf can actually dump *our* objects.  Read-only.
ELF_PROBE_REL = Path(".work") / "source" / "musl" / "obj" / "crt" / "rcrt1.o"
# Scratch root for the functional checks (m14-llvm-001).  mkdtemp per run,
# removed in a `finally` block; never inside the repo.
FUNC_TMP_REL = Path("/tmp/opencode/check-install-tools")
FUNC_TIMEOUT = 120
VERSION_TIMEOUT = 60
# `llvm-nm --print-armap` entry lines: "<symbol> in <member>".
ARMAP_LINE_RE = re.compile(r"^\s*(\S+)\s+in\s+(\S+)\s*$", re.M)
# Tools that are not LLVM `--version` CLIs: lit's `not` executes its argv as a
# command and inverts the exit status, so `not --version` is 1 by design.
# Probe it the way lit uses it (`not false` => 0).
RUN_PROBE = {"not": ["false"]}
SMALL_SHA_CHUNK = 1 << 20

MACHINE_RE = re.compile(r"^\s*Machine:\s*(.*)$", re.M)


class Report:
    """Accumulates PASS/FAIL/SKIP lines; every FAIL is counted."""

    def __init__(self, verbose: bool = True) -> None:
        self.failures = 0
        self.checks = 0
        self.verbose = verbose

    def check(self, name: str, expected: str, actual: str, ok: bool) -> bool:
        self.checks += 1
        if not ok:
            self.failures += 1
        if self.verbose or not ok:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} "
                  f"actual={actual}")
        return ok

    def skip(self, name: str, why: str) -> None:
        if self.verbose:
            print(f"[SKIP] {name}: {why}")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(SMALL_SHA_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_args(tool: str) -> list[str]:
    return RUN_PROBE.get(tool, ["--version"])


def run_probe(path: Path, tool: str) -> int | str:
    """Exit code of the tool's run probe (default ``--version``), or an error token."""
    try:
        res = subprocess.run([str(path)] + probe_args(tool),
                             capture_output=True, text=True,
                             timeout=VERSION_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return type(exc).__name__
    return res.returncode


def makefile_list(root: Path, name: str) -> list[str] | None:
    """Whitespace-separated words of a single-line ``NAME = ...`` in the Makefile."""
    makefile = root / "Makefile"
    if not makefile.is_file():
        return None
    text = makefile.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"^{re.escape(name)}\s*=\s*(\S.*?)\s*$", text, re.M)
    if match is None:
        return None
    return match.group(1).split()


def parse_aliases(specs: list[str], rep: Report) -> list[tuple[str, str]]:
    aliases: list[tuple[str, str]] = []
    for spec in specs:
        if spec.count(":") != 1 or not all(spec.split(":")):
            rep.check(f"alias spec '{spec}' is <link>:<target>", "one ':'", spec,
                      False)
            continue
        aliases.append(tuple(spec.split(":")))  # type: ignore[arg-type]
    return aliases


def check_alias(link: str, target: str, root: Path, build_bin: Path,
                sha_set: set[str] | None, rep: Report) -> None:
    """Shape + resolvability + same-binary checks for one zero-copy alias."""
    path = root / link
    rep.check(f"{link} is a relative symlink (zero-copy alias)",
              f"-> {target}", (os.readlink(path) if path.is_symlink() else
                               "not a symlink"), path.is_symlink()
              and os.readlink(path) == target)
    if not path.is_symlink() or os.readlink(path) != target:
        return
    resolved = path.resolve()
    executable = resolved.is_file() and os.access(resolved, os.X_OK)
    rep.check(f"{link} resolves to an executable", "executable file",
              f"{resolved} executable={executable}", executable)
    if resolved.is_file():
        rc = run_probe(path, target)
        rep.check(f"{link} {' '.join(probe_args(target))} rc", "0", rc, rc == 0)
        check_content(target, path, build_bin, sha_set, rep)


def check_content(name: str, installed: Path, build_bin: Path,
                  sha_set: set[str] | None, rep: Report) -> None:
    """Size (always) and sha256 (content mode) equality with the build tree."""
    if not build_bin.is_dir():
        rep.skip(f"{name} build-tree identity", f"no build tree at {build_bin}")
        return
    build = build_bin / name
    if not build.exists():
        rep.check(f"{name} build-tree counterpart exists", "present",
                  f"missing {build}", False)
        return
    inst_size = installed.stat().st_size
    build_size = build.stat().st_size
    rep.check(f"{name} size == build tree", build_size, inst_size,
              inst_size == build_size)
    if sha_set is None:
        rep.skip(f"{name} sha256 == build tree", "content mode off (--sha)")
        return
    if sha_set and name not in sha_set:
        rep.skip(f"{name} sha256 == build tree", "not in --sha-tools")
        return
    if inst_size != build_size:
        return
    build_sha = sha256_of(build)
    inst_sha = sha256_of(installed)
    rep.check(f"{name} sha256 == build tree", build_sha, inst_sha,
              build_sha == inst_sha)


def check_elf_probe(root: Path, probe: Path, rep: Report) -> None:
    """The installed llvm-readelf must dump the big-endian DADAO probe object."""
    if not probe.is_file():
        rep.skip("llvm-readelf -h big-endian DADAO object",
                 f"probe object missing at {probe}")
        return
    readelf = root / "llvm-readelf"
    if not readelf.exists():
        rep.check("llvm-readelf -h big-endian DADAO object",
                  "installed llvm-readelf", "missing", False)
        return
    try:
        res = subprocess.run([str(readelf), "-h", str(probe)],
                             capture_output=True, text=True,
                             timeout=VERSION_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        rep.check("llvm-readelf -h big-endian DADAO object", "rc=0",
                  type(exc).__name__, False)
        return
    out = res.stdout
    rep.check("llvm-readelf -h probe rc", "0", res.returncode,
              res.returncode == 0)
    data_ok = "big endian" in out.lower()
    rep.check("probe Data is big endian (ELFDATA2MSB)", "big endian",
              "big endian" if data_ok else out.lower().replace("\n", " ")[:80],
              data_ok)
    machine = MACHINE_RE.search(out)
    machine_text = machine.group(1).strip() if machine else "<no Machine line>"
    machine_ok = bool(re.search(r"(?i)(dadao|0x0?da0\b|\bda0\b)", machine_text))
    rep.check("probe Machine is DADAO (EM_DADAO 0x0da0)", "dadao/0xda0",
              machine_text, machine_ok)


def run_tool(argv: list[Path | str], cwd: Path | None = None) -> tuple[int | str, str, str]:
    """Run one installed tool; return ``(rc, stdout, stderr)`` without raising."""
    try:
        res = subprocess.run([str(a) for a in argv],
                             cwd=None if cwd is None else str(cwd),
                             capture_output=True, text=True,
                             timeout=FUNC_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return type(exc).__name__, "", ""
    return res.returncode, res.stdout, res.stderr


def required_tools(root: Path, names: tuple[str, ...], label: str,
                   rep: Report) -> bool:
    """All named tools must be present; report each miss as a FAIL."""
    present = True
    for name in names:
        path = root / name
        ok = path.exists() and os.access(path, os.X_OK)
        if not ok:
            present = False
        rep.check(f"{label}: {name} available", "executable", f"{path} "
                  f"executable={ok}", ok)
    return present


def check_ar_roundtrip(root: Path, probe: Path, work: Path, rep: Report) -> None:
    """llvm-ar: create, list and extract the probe object (m14-llvm-001)."""
    label = "llvm-ar round-trip"
    if not required_tools(root, ("llvm-ar",), label, rep):
        return
    ar = root / "llvm-ar"
    d = work / "ar"
    d.mkdir()
    members = ["member_a.o", "member_b.o"]
    for member in members:
        (d / member).write_bytes(probe.read_bytes())
    archive = "libprobe.a"
    rc, _, err = run_tool([ar, "rcs", archive, *members], cwd=d)
    rep.check(f"{label}: llvm-ar rcs rc", "0", rc, rc == 0)
    if rc != 0:
        print(f"       llvm-ar rcs stderr: {err.strip()[:200]}")
    rc, out, err = run_tool([ar, "t", archive], cwd=d)
    listed = sorted(out.split())
    rep.check(f"{label}: llvm-ar t members", ",".join(sorted(members)),
              ",".join(listed) if listed else f"<none> rc={rc} {err.strip()[:120]}",
              rc == 0 and listed == sorted(members))
    extract = work / "ar-extract"
    extract.mkdir()
    rc, _, err = run_tool([ar, "x", str(d / archive)], cwd=extract)
    rep.check(f"{label}: llvm-ar x rc", "0", rc, rc == 0)
    if rc != 0:
        print(f"       llvm-ar x stderr: {err.strip()[:200]}")
    want = sha256_of(probe)
    for member in members:
        got = extract / member
        ok = got.is_file()
        rep.check(f"{label}: {member} extracted", "present",
                  "present" if ok else "missing", ok)
        if ok:
            have = sha256_of(got)
            rep.check(f"{label}: {member} sha256 == probe", want, have,
                      have == want)


def read_armap(nm: Path, archive: Path) -> tuple[int | str, list[tuple[str, str]]]:
    """``llvm-nm --print-armap`` entries, or ``(rc, [])`` when it failed."""
    rc, out, _ = run_tool([nm, "--print-armap", archive])
    if rc != 0:
        return rc, []
    return rc, [(m.group(1), m.group(2))
                for m in ARMAP_LINE_RE.finditer(out)]


def check_ranlib_index(root: Path, probe: Path, work: Path, rep: Report) -> None:
    """llvm-ranlib: write the archive symbol table (m14-llvm-001)."""
    label = "llvm-ranlib index"
    if not required_tools(root, ("llvm-ar", "llvm-ranlib", "llvm-nm"),
                          label, rep):
        return
    ar, ranlib, nm = root / "llvm-ar", root / "llvm-ranlib", root / "llvm-nm"
    d = work / "ranlib"
    d.mkdir()
    member = "member.o"
    (d / member).write_bytes(probe.read_bytes())
    archive = "libidx.a"
    # `llvm-ar` writes a symbol table by default (SymtabWritingMode::NormalSymtab);
    # the `S` modifier selects NoSymtab, which is the state ranlib must repair.
    rc, _, err = run_tool([ar, "rcS", archive, member], cwd=d)
    rep.check(f"{label}: llvm-ar rcS (no index) rc", "0", rc, rc == 0)
    if rc != 0:
        print(f"       llvm-ar rcS stderr: {err.strip()[:200]}")
    rc, before = read_armap(nm, d / archive)
    rep.check(f"{label}: llvm-nm --print-armap rc (before)", "0", rc, rc == 0)
    rep.check(f"{label}: no archive map before ranlib", "0 entries",
              f"{len(before)} entries", not before)
    rc, _, err = run_tool([ranlib, archive], cwd=d)
    rep.check(f"{label}: llvm-ranlib rc", "0", rc, rc == 0)
    if rc != 0:
        print(f"       llvm-ranlib stderr: {err.strip()[:200]}")
    rc, after = read_armap(nm, d / archive)
    rep.check(f"{label}: llvm-nm --print-armap rc (after)", "0", rc, rc == 0)
    rep.check(f"{label}: archive map written by ranlib", ">=1 entry",
              f"{len(after)} entries", len(after) >= 1)
    if after:
        print(f"       archive map after ranlib (first 3): "
              f"{' | '.join(f'{s} in {m}' for s, m in after[:3])}")
    rc, out, err = run_tool([ar, "t", archive], cwd=d)
    listed = sorted(out.split())
    rep.check(f"{label}: members still listed", member,
              ",".join(listed) if listed else f"<none> rc={rc} {err.strip()[:120]}",
              rc == 0 and member in listed)


def check_strip(root: Path, probe: Path, work: Path, rep: Report) -> None:
    """llvm-strip --strip-all on the big-endian DADAO probe (m14-llvm-001)."""
    label = "llvm-strip --strip-all"
    if not required_tools(root, ("llvm-strip", "llvm-readelf", "llvm-objdump"),
                          label, rep):
        return
    strip, readelf, objdump = (root / "llvm-strip", root / "llvm-readelf",
                               root / "llvm-objdump")
    d = work / "strip"
    d.mkdir()
    obj = d / "probe.o"
    obj.write_bytes(probe.read_bytes())

    def header_ok(path: Path, phase: str) -> None:
        rc, out, _ = run_tool([readelf, "-h", path])
        rep.check(f"{label}: llvm-readelf -h rc ({phase})", "0", rc, rc == 0)
        data_ok = "big endian" in out.lower()
        rep.check(f"{label}: {phase} Data is big endian", "big endian",
                  "big endian" if data_ok else "<not big endian>", data_ok)
        machine = MACHINE_RE.search(out)
        machine_text = machine.group(1).strip() if machine else "<no Machine line>"
        machine_ok = bool(re.search(r"(?i)(dadao|0x0?da0\b|\bda0\b)",
                                    machine_text))
        rep.check(f"{label}: {phase} Machine is DADAO", "dadao/0xda0",
                  machine_text, machine_ok)

    header_ok(obj, "input")
    rc, _, err = run_tool([strip, "--strip-all", obj], cwd=d)
    rep.check(f"{label}: llvm-strip --strip-all rc", "0", rc, rc == 0)
    if rc != 0:
        print(f"       llvm-strip stderr: {err.strip()[:200]}")
    header_ok(obj, "stripped")
    rc, out, err = run_tool([objdump, "-d", obj])
    rep.check(f"{label}: llvm-objdump -d rc", "0", rc, rc == 0)
    lines = [line for line in out.splitlines() if line.strip()]
    rep.check(f"{label}: llvm-objdump -d non-empty", ">=1 line",
              f"{len(lines)} line(s)", bool(lines))
    if rc != 0:
        print(f"       llvm-objdump stderr: {err.strip()[:200]}")


def functional_checks(root: Path, probe: Path, rep: Report) -> None:
    """Run the m14-llvm-001 functional group on the big-endian DADAO probe."""
    if not probe.is_file():
        rep.skip("llvm-ar/llvm-ranlib/llvm-strip functional checks",
                 f"probe object missing at {probe}")
        return
    # The tools are invoked with cwd=<scratch dir>, so a --root given relative to
    # the repo must become absolute before it is exec'd.
    root = root.resolve()
    FUNC_TMP_REL.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="functional-", dir=FUNC_TMP_REL))
    try:
        check_ar_roundtrip(root, probe, work, rep)
        check_ranlib_index(root, probe, work, rep)
        check_strip(root, probe, work, rep)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_checks(root: Path, build_bin: Path, probe: Path,
               sha_set: set[str] | None, rep: Report) -> int:
    """Run every check against (root, build_bin); return failure count."""
    repo = paths.repo_root()
    tools = makefile_list(repo, "HOST_LLVM_TOOLS")
    specs = makefile_list(repo, "HOST_LLVM_TOOL_SYMLINKS")
    if not rep.check("Makefile defines HOST_LLVM_TOOLS", "non-empty",
                     "missing/empty" if not tools else f"{len(tools)} tools",
                     bool(tools)):
        return rep.failures
    if not rep.check("Makefile defines HOST_LLVM_TOOL_SYMLINKS", "non-empty",
                     "missing/empty" if not specs else f"{len(specs)} aliases",
                     bool(specs)):
        return rep.failures
    aliases = parse_aliases(specs, rep)
    overlap = sorted(set(tools) & {link for link, _ in aliases})
    rep.check("no name is both a copy and an alias", "0 overlap",
              ", ".join(overlap) if overlap else "0", not overlap)

    print(f"install root: {root}")
    print(f"build tree  : {build_bin}")
    for tool in tools:
        path = root / tool
        present = path.is_file() and os.access(path, os.X_OK)
        rep.check(f"{tool} installed and executable", "executable file",
                  f"{path} executable={present}", present)
        if not present:
            continue
        rc = run_probe(path, tool)
        rep.check(f"{tool} {' '.join(probe_args(tool))} rc", "0", rc, rc == 0)
        check_content(tool, path, build_bin, sha_set, rep)
    for link, target in aliases:
        check_alias(link, target, root, build_bin, sha_set, rep)

    check_elf_probe(root, probe, rep)
    functional_checks(root, probe, rep)
    return rep.failures


def self_test() -> int:
    """Baseline PASS + injections, each with a reachable FAIL.

    The fake tree lives under /tmp/opencode/INFRA-098t/ (never in the repo).
    Tools are shell scripts, so no multi-GB copies are involved; every mutation
    is restored with ``cp``-equivalent byte copies and md5 accounting (no git).
    The fakes dispatch on ``basename "$0"`` so the argv[0] aliases and the
    m14-llvm-001 functional group (llvm-ar / llvm-ranlib / llvm-strip) have a
    green baseline; the injected modes make each functional assert fail.
    """
    repo = paths.repo_root()
    tools = makefile_list(repo, "HOST_LLVM_TOOLS") or []
    specs = makefile_list(repo, "HOST_LLVM_TOOL_SYMLINKS") or []
    if not tools or not specs:
        print("self-test: FAIL -- cannot read the install set from the Makefile")
        return 1

    tmp_root = Path("/tmp/opencode/INFRA-098t")
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="install-tools-selftest-", dir=tmp_root))
    total_fail = 0
    try:
        build_bin = root / "build-bin"
        inst_bin = root / "inst-bin"
        build_bin.mkdir()
        inst_bin.mkdir()
        probe = root / "probe.o"
        probe.write_bytes(b"\x7fELF fake probe\n")
        good_header = root / "elf-good.txt"
        good_header.write_text(
            "ELF Header:\n  Class: ELF64\n"
            "  Data:                              2's complement, big endian\n"
            "  Machine:                           da0\n")
        bad_header = root / "elf-bad.txt"
        bad_header.write_text(
            "ELF Header:\n  Class: ELF64\n"
            "  Data:                              2's complement, little endian\n"
            "  Machine:                           Advanced Micro Devices X86-64\n")

        fake = ("#!/bin/sh\n"
                "name=$(basename \"$0\")\n"
                "case \"$name\" in\n"
                "  llvm-ar)\n"
                "    case \"$1\" in --version) echo 'fake llvm-ar'; exit 0;; esac\n"
                "    if [ \"$FAKE_AR_MODE\" = drop-member ]; then\n"
                "      case \"$1\" in r*) exec /usr/bin/ar \"$1\" \"$2\" \"$3\";; esac\n"
                "    fi\n"
                "    exec /usr/bin/ar \"$@\"\n"
                "    ;;\n"
                "  llvm-ranlib)\n"
                "    case \"$1\" in --version) echo 'fake llvm-ranlib'; exit 0;; esac\n"
                "    [ \"$FAKE_RANLIB_MODE\" = no-index ] && exit 0\n"
                "    printf '%s\\n' \"fake_symbol in ${1##*/}\" > \"${1}.idx\"\n"
                "    exit 0\n"
                "    ;;\n"
                "  llvm-nm)\n"
                "    case \"$1\" in --version) echo 'fake llvm-nm'; exit 0;; esac\n"
                "    case \"$1\" in\n"
                "      --print-armap) [ -f \"$2.idx\" ] && cat \"$2.idx\"; exit 0;;\n"
                "    esac\n"
                "    exit 0\n"
                "    ;;\n"
                "  llvm-strip)\n"
                "    case \"$1\" in --version) echo 'fake llvm-strip'; exit 0;; esac\n"
                "    [ \"$FAKE_STRIP_MODE\" = fail ] && exit 1\n"
                "    exit 0\n"
                "    ;;\n"
                "  llvm-objdump)\n"
                "    case \"$1\" in --version) echo 'fake llvm-objdump'; exit 0;; esac\n"
                "    echo '0: 00 00 fake disassembly'\n"
                "    exit 0\n"
                "    ;;\n"
                "  llvm-readelf|llvm-readobj)\n"
                "    case \"$1\" in --version) echo 'fake readelf'; exit 0;; esac\n"
                "    if [ -n \"$FAKE_ELF_HEADER\" ]; then cat \"$FAKE_ELF_HEADER\"; fi\n"
                "    exit 0\n"
                "    ;;\n"
                "  *)\n"
                "    case \"$1\" in --version) echo 'fake-tool 0.0'; exit 0;; esac\n"
                "    exit 0\n"
                "    ;;\n"
                "esac\n")
        names = list(tools) + [t for _, t in
                               (s.split(":", 1) for s in specs)] + \
            [ln for ln, _ in (s.split(":", 1) for s in specs)]
        for name in dict.fromkeys(names):
            for d in (build_bin, inst_bin):
                (d / name).write_text(fake)
                (d / name).chmod(0o755)
        for spec in specs:
            link, target = spec.split(":", 1)
            (inst_bin / link).unlink()
            (inst_bin / link).symlink_to(target)
        os.environ["FAKE_ELF_HEADER"] = str(good_header)

        def run(sha_set=None) -> tuple[int, Report]:
            rep = Report(verbose=False)
            failed = run_checks(inst_bin, build_bin, probe,
                                None if sha_set is None else set(sha_set), rep)
            return failed, rep

        def verdict(name: str, expect_red: bool, result: tuple[int, Report]) -> None:
            nonlocal total_fail
            failed, rep = result
            ok = (failed >= 1) if expect_red else (failed == 0)
            total_fail += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] self-test {name}: "
                  f"expected={'red (>=1 failure)' if expect_red else 'green'} "
                  f"actual={failed} failure(s) / {rep.checks} check(s)")

        def md5(p: Path) -> str:
            return hashlib.md5(p.read_bytes()).hexdigest()

        def restore_md5(p: Path, expected: str, label: str) -> None:
            nonlocal total_fail
            ok = p.is_file() and md5(p) == expected
            total_fail += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] self-test {label} restore: "
                  f"expected=md5 {expected} "
                  f"actual={md5(p) if p.is_file() else '<missing>'}")

        verdict("baseline", False, run())

        # 1: a tool missing from the install root must be red.
        victim = inst_bin / tools[0]
        saved = victim.read_bytes()
        victim.unlink()
        verdict(f"inject-1 (remove {tools[0]} from install root)", True, run())
        victim.write_bytes(saved)
        victim.chmod(0o755)
        restore_md5(victim, hashlib.md5(saved).hexdigest(), "inject-1")

        # 2: a same-name but different-content install copy must be red (size).
        victim = inst_bin / tools[0]
        before = md5(victim)
        victim.write_bytes(saved + b"# tampered\n")
        verdict(f"inject-2 (tamper {tools[0]} content)", True, run())
        victim.write_bytes(saved)
        victim.chmod(0o755)
        restore_md5(victim, before, "inject-2")

        # 3: a copy instead of a symlink defeats the zero-copy alias => red.
        link, target = specs[0].split(":", 1)
        alias = inst_bin / link
        alias.unlink()
        shutil.copyfile(inst_bin / target, alias)
        alias.chmod(0o755)
        verdict(f"inject-3 ({link} as a copy, not a symlink)", True, run())
        alias.unlink()
        alias.symlink_to(target)
        ok = alias.is_symlink() and os.readlink(alias) == target
        total_fail += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] self-test inject-3 restore: "
              f"expected=symlink -> {target} "
              f"actual={'symlink -> ' + os.readlink(alias) if alias.is_symlink() else 'not a symlink'}")

        # 4: content mode must catch a same-size, different-bytes copy.
        os.environ["FAKE_ELF_HEADER"] = str(good_header)
        name = tools[0]
        build_copy = build_bin / name
        build_before = md5(build_copy)
        payload = build_copy.read_bytes()
        build_copy.write_bytes(payload[:-1] + (b"X" if payload[-1:] != b"X"
                                               else b"Y"))
        sha_result = run(sha_set=frozenset({name}))
        # sizes stay equal (one byte swapped) => only the sha check can fire.
        verdict(f"inject-4 (same-size content change in build tree, "
                f"--sha-tools {name})", True, sha_result)
        build_copy.write_bytes(payload)
        restore_md5(build_copy, build_before, "inject-4")

        # 5: a little-endian / non-DADAO dump must be red.
        os.environ["FAKE_ELF_HEADER"] = str(bad_header)
        verdict("inject-5 (llvm-readelf -h prints little endian / non-DADAO)",
                True, run())
        os.environ["FAKE_ELF_HEADER"] = str(good_header)
        verdict("restore-5 (big-endian DADAO dump)", False, run())

        # 6: llvm-ar that silently drops a member must be red (round-trip).
        os.environ["FAKE_AR_MODE"] = "drop-member"
        verdict("inject-6 (llvm-ar drops a member)", True, run())
        os.environ.pop("FAKE_AR_MODE", None)
        verdict("restore-6 (llvm-ar round-trip)", False, run())

        # 7: llvm-ranlib that writes no symbol table must be red.
        os.environ["FAKE_RANLIB_MODE"] = "no-index"
        verdict("inject-7 (llvm-ranlib writes no index)", True, run())
        os.environ.pop("FAKE_RANLIB_MODE", None)
        verdict("restore-7 (llvm-ranlib index)", False, run())

        # 8: llvm-strip that fails must be red (kernel build STRIP path).
        os.environ["FAKE_STRIP_MODE"] = "fail"
        verdict("inject-8 (llvm-strip exits 1)", True, run())
        os.environ.pop("FAKE_STRIP_MODE", None)
        verdict("restore-8 (llvm-strip --strip-all)", False, run())
    finally:
        os.environ.pop("FAKE_ELF_HEADER", None)
        os.environ.pop("FAKE_AR_MODE", None)
        os.environ.pop("FAKE_RANLIB_MODE", None)
        os.environ.pop("FAKE_STRIP_MODE", None)
        shutil.rmtree(root, ignore_errors=True)

    print(f"check-install-tools: --self-test "
          f"{'PASS' if total_fail == 0 else 'FAIL'} "
          f"({total_fail} unexpected outcome(s))")
    return 0 if total_fail == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="check-install-tools (ISS-261)")
    ap.add_argument("--root", default=None,
                    help="install-root bin dir (default: paths.py "
                         "host_toolchain_bin())")
    ap.add_argument("--build-dir", default=None,
                    help=f"build-tree bin dir (default: {BUILD_BIN_REL})")
    ap.add_argument("--elf-object", default=None,
                    help=f"big-endian DADAO probe object (default: "
                         f"{ELF_PROBE_REL})")
    ap.add_argument("--sha", action="store_true",
                    help="also compare sha256 of every installed tool (slow: "
                         "~11 GB per side)")
    ap.add_argument("--sha-tools", default=None,
                    help="comma-separated subset to sha256-compare")
    ap.add_argument("--self-test", action="store_true",
                    help="baseline + injected counter-examples in a temp tree")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    repo = paths.repo_root()
    root = Path(args.root) if args.root else Path(paths.host_toolchain_bin())
    build_bin = (Path(args.build_dir) if args.build_dir else repo / BUILD_BIN_REL)
    probe = (Path(args.elf_object) if args.elf_object
             else repo / ELF_PROBE_REL)
    sha_set: set[str] | None = None
    if args.sha:
        sha_set = set()
    if args.sha_tools:
        sha_set = {t.strip() for t in args.sha_tools.split(",") if t.strip()}

    if not root.is_dir():
        print(f"check-install-tools: FAIL -- install root bin dir missing "
              f"({root}); run 'make install-host'")
        return 1
    rep = Report()
    failed = run_checks(root, build_bin, probe, sha_set, rep)
    if failed:
        print(f"check-install-tools: FAIL ({failed}/{rep.checks} check(s)) -- "
              f"run 'make install-host'")
        return 1
    print(f"check-install-tools: PASS ({rep.checks} check(s); install root "
          f"carries the Makefile's install set and every entry is the build "
          f"tree's binary)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
