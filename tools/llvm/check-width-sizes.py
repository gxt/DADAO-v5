#!/usr/bin/env python3
"""check-width-sizes: DADAO 64-bit width / DWARF64 probe (LLVM-130t, L1).

ADR-0036 D1 makes DADAO a native 64-bit target.  Two properties must hold for
the installed toolchain, and both used to be wrong:

* `MCAsmInfo` defaults `CodePointerSize`/`CalleeSaveStackSlotSize` to 4, so
  `clang -g -c` emitted 4-byte DWARF `.debug_addr` entries and the assembler
  rejected the 48-bit relocatable address ("relocatable operand in a 1/2/4-byte
  data field ...");
* `CodePointerSize` also feeds the CFI `data_alignment_factor`.

The DADAO toolchain defaults to DWARF64 (no 32-bit DWARF relocation channel).

Checks (each is a separate PASS/FAIL line; every one has a reachable FAIL path,
see ``--self-test``):

  1.  static-assert compile, one compile per property:
      ``sizeof(void*)==8``, ``sizeof(long)==8``, ``sizeof(size_t)==8``,
      ``_Alignof(max_align_t)==16``, ``sizeof(long double)==16``,
      ``__BIGGEST_ALIGNMENT__==16``;
  2.  ``clang --target=dadao-unknown-elf -g -c`` exits 0 (the pre-fix case
      failed on the 4-byte ``.debug_addr`` relocation), and the same source
      **links** (``-nostdlib -Wl,-e,main``) so the debug info has resolved
      addresses;
  3.  ``llvm-readelf -h`` says ``Class: ELF64``;
  4.  every RELA section's ``ES`` (entsize) is 24 (``Elf64_Rela``); at least one
      RELA section must exist (vacuous = FAIL);
  5.  ``.got`` entry width is 8: ``.got`` size == 8 x #(.rela.got entries)``,
      with the live entry count printed (no hardcoded count);
  6.  ``llvm-dwarfdump --debug-info`` on the **linked** ``-g`` image: every
      compile unit reports ``addr_size = 0x08`` and ``format = DWARF64``.

Why the *linked* image for check 6: ``llvm-dwarfdump`` on a relocatable object
exits 1 for DADAO (``warning: failed to compute relocation: R_DADAO_ABS48,
Invalid data was encountered while parsing the file`` plus a
``.debug_str_offsets`` error); libObject does not apply the DADAO 48-bit wyde
relocation.  The CU header itself still prints the right values, so requiring
``rc == 0`` on the object would report a false FAIL.  After linking the
relocations are applied and the dump exits 0.  The ELF/RELA/GOT checks stay on
the object (they only need the section table).

Note on check 6: this LLVM's ``llvm-dwarfdump`` prints the CU header as
``..., format = DWARF64, ..., addr_size = 0x08 (...)``; the "Address Size: 8"
spelling used in the task book does not occur in this version.  The assertion
is made against the real output format (and additionally checks the DWARF64
format that the driver now selects by default).

Usage
-----
  tools/llvm/check-width-sizes.py                  # installed toolchain
  tools/llvm/check-width-sizes.py --self-test      # fake tools, no build needed
  tools/llvm/check-width-sizes.py --clang .work/build/llvm/bin/clang \\
                                  --target i386-unknown-elf \\
                                  --link-arg=-fuse-ld=lld      # negative control

Cost: ~2 s (8 tiny compiles/links).  Temporary work goes to
``/tmp/opencode/LLVM-130t/`` (never into the repository).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "infra"))
import paths as _paths  # noqa: E402

TARGET = "dadao-unknown-elf"
WORK_ROOT = Path("/tmp/opencode/LLVM-130t")
TIMEOUT = 120

# Expectations -- single place, read by every assertion below.
PTR_BYTES = 8
MAX_ALIGN = 16
LONG_DOUBLE_BYTES = 16
RELA_ENTSIZE = 24
ADDR_SIZE = 8
DWARF_FORMAT = "DWARF64"

# One compile per property: a single failing `_Static_assert` must not hide the
# others, and each assertion gets its own reachable FAIL path.
STATIC_PROBES = (
    ("sizeof(void*)", "sizeof(void *)", PTR_BYTES),
    ("sizeof(long)", "sizeof(long)", PTR_BYTES),
    ("sizeof(size_t)", "sizeof(size_t)", PTR_BYTES),
    ("_Alignof(max_align_t)", "_Alignof(max_align_t)", MAX_ALIGN),
    ("sizeof(long double)", "sizeof(long double)", LONG_DOUBLE_BYTES),
    ("__BIGGEST_ALIGNMENT__", "__BIGGEST_ALIGNMENT__", MAX_ALIGN),
)

# `-g` object: a function that references an external global forces debug-info
# address entries (`.debug_addr`), the section that used to carry 4-byte
# relocatable addresses.  The same source is **linked** below, because
# `llvm-dwarfdump` cannot apply the DADAO ABS48 wyde relocation to a
# relocatable object (it exits 1 with "failed to compute relocation:
# R_DADAO_ABS48"); the linked image has the addresses resolved and parses
# cleanly.
SIZES_C = """\
#include <stddef.h>

long width_global = 7;

long width_probe(long x) { return x + width_global; }

int main(void) { return (int)width_probe(1); }
"""

# `-fPIC` object: one GOT-relocated external global, so `.got` and `.rela.got`
# are both emitted and their entry widths can be related.
RELOCS_C = """\
extern long width_global;
long *width_pg = &width_global;
long width_probe(long x) { return x + width_global; }
"""

ELF_CLASS_RE = re.compile(r"^\s*Class:\s*(\S+)\s*$", re.M)
SECTION_RE = re.compile(
    r"^\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)"
    r"\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+(.*)$"
)
ADDR_SIZE_RE = re.compile(r"addr_size = 0x([0-9a-fA-F]{2})\b")
DWARF_FORMAT_RE = re.compile(r"format = (DWARF(?:32|64))\b")


class Report:
    """PASS/FAIL accumulator; keeps the failed assertion names for --self-test."""

    def __init__(self, verbose: bool = True) -> None:
        self.checks = 0
        self.failures = 0
        self.failed: list[str] = []
        self.verbose = verbose

    def check(self, name: str, expected: str, actual: str, ok: bool,
              detail: str = "") -> bool:
        self.checks += 1
        if not ok:
            self.failures += 1
            self.failed.append(name)
        if self.verbose or not ok:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} "
                  f"actual={actual}")
            if not ok and detail:
                for line in detail.splitlines()[:8]:
                    print(f"        | {line}")
        return ok


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Run argv; return (rc, stdout, stderr).  Missing tool => rc=127."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {TIMEOUT}s: {' '.join(argv)}"
    except OSError as exc:
        return 127, "", f"cannot execute {' '.join(argv)}: {exc}"
    return proc.returncode, proc.stdout, proc.stderr


def parse_elf_class(text: str) -> str | None:
    match = ELF_CLASS_RE.search(text)
    return match.group(1) if match else None


def parse_sections(text: str) -> dict[str, dict[str, int | str]]:
    """Map section name -> {type, size, entsize} from `llvm-readelf -S`."""
    sections: dict[str, dict[str, int | str]] = {}
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if not match:
            continue
        sections[match.group(1)] = {
            "type": match.group(2),
            "size": int(match.group(5), 16),
            "entsize": int(match.group(6), 16),
        }
    return sections


def check_static_sizes(tools: dict[str, Path], target: str, work: Path,
                       rep: Report) -> None:
    src = work / "static-width.c"
    for name, expr, expected in STATIC_PROBES:
        src.write_text(
            "#include <stddef.h>\n"
            f'_Static_assert(({expr}) == {expected}, "width probe {name}");\n',
            encoding="utf-8")
        rc, _out, err = _run([str(tools["clang"]), f"--target={target}", "-c",
                              str(src), "-o", str(work / "static-width.o")])
        rep.check(f"static {name} == {expected}", "compile rc=0",
                  f"rc={rc}", rc == 0, detail=err)


def check_objects(tools: dict[str, Path], target: str, work: Path,
                  rep: Report, link_args: tuple[str, ...] = ()) -> None:
    sizes_c = work / "sizes.c"
    relocs_c = work / "relocs.c"
    sizes_o = work / "sizes.o"
    sizes_elf = work / "sizes.elf"
    relocs_o = work / "relocs.o"
    sizes_c.write_text(SIZES_C, encoding="utf-8")
    relocs_c.write_text(RELOCS_C, encoding="utf-8")
    # Never read a stale artefact from an earlier run in the same dir.
    for stale in (sizes_o, sizes_elf, relocs_o):
        stale.unlink(missing_ok=True)

    # 2a: the debug compile itself.  Pre-fix this failed with
    # "relocatable operand in a 1/2/4-byte data field ..." for .debug_addr.
    rc, _out, err = _run([str(tools["clang"]), f"--target={target}", "-g", "-c",
                          str(sizes_c), "-o", str(sizes_o)])
    rep.check("`-g -c` compiles (DWARF address fields are relocatable)",
              "rc=0", f"rc={rc}", rc == 0, detail=err)

    # 2b: link the debug image.  `llvm-dwarfdump` cannot apply the DADAO ABS48
    # wyde relocation to a relocatable object (rc=1 + "failed to compute
    # relocation: R_DADAO_ABS48"), so the DWARF assertions below read the linked
    # image, where the addresses are resolved (dump rc=0).
    rc, out, err = _run([str(tools["clang"]), f"--target={target}", "-g",
                         "-nostdlib", "-Wl,-e,main", *link_args,
                         str(sizes_c), "-o", str(sizes_elf)])
    rep.check("`-g` link succeeds (debug info survives the linker)", "rc=0",
              f"rc={rc}", rc == 0, detail=(out or "") + (err or ""))

    # `-fPIC` object: GOT/RELA material for checks 4 and 5.
    rc, _out, err = _run([str(tools["clang"]), f"--target={target}", "-fPIC",
                          "-c", str(relocs_c), "-o", str(relocs_o)])
    rep.check("`-fPIC -c` compiles (GOT/RELA probe)", "rc=0", f"rc={rc}",
              rc == 0, detail=err)

    # 3: ELF class.
    rc, out, err = _run([str(tools["readelf"]), "-h", str(sizes_o)])
    elf_class = parse_elf_class(out) if rc == 0 else None
    rep.check("ELF class", "Class: ELF64", f"rc={rc}, Class={elf_class!r}",
              rc == 0 and elf_class == "ELF64", detail=out or err)

    # 4 + 5: section table.
    rc, out, err = _run([str(tools["readelf"]), "-S", str(relocs_o)])
    sections = parse_sections(out) if rc == 0 else {}
    rela = {name: sec for name, sec in sections.items()
            if sec["type"] == "RELA"}
    entsizes = sorted({int(sec["entsize"]) for sec in rela.values()})
    rep.check("RELA sections exist (vacuous = FAIL)", ">=1 RELA section",
              f"{len(rela)} section(s)", bool(rela), detail=out or err)
    rep.check("every RELA section entsize == 24", f"entsize={RELA_ENTSIZE}",
              f"entsizes={entsizes}", bool(rela) and entsizes == [RELA_ENTSIZE],
              detail=out or err)

    got = sections.get(".got")
    rela_got = sections.get(".rela.got")
    # Entry count is read live from the object (size / its own entsize), never
    # hardcoded; a missing `.rela.got` means the GOT probe did not work.
    entries = 0
    if rela_got and int(rela_got["entsize"]) > 0:
        entries = int(rela_got["size"]) // int(rela_got["entsize"])
    if got is None:
        rep.check(".got entry width == 8", f"size={ADDR_SIZE}*entries",
                  "missing .got section", False, detail=out or err)
    else:
        actual = f"{int(got['size'])} B / {entries} entr(ies)"
        rep.check(".got entry width == 8", f"size={ADDR_SIZE}*entries",
                  actual, entries > 0 and int(got["size"]) == ADDR_SIZE * entries,
                  detail=out or err)

    # 6: DWARF unit header of the **linked** image -- address size and format.
    rc, out, err = _run([str(tools["dwarfdump"]), "--debug-info", str(sizes_elf)])
    addr_sizes = [int(value, 16) for value in ADDR_SIZE_RE.findall(out)]
    formats = DWARF_FORMAT_RE.findall(out)
    detail = "\n".join(part for part in (out, err) if part)
    rep.check("DWARF CU addr_size == 8 (all units)", f"addr_size={ADDR_SIZE}",
              f"units={len(addr_sizes)}, addr_sizes={addr_sizes}",
              rc == 0 and bool(addr_sizes)
              and all(size == ADDR_SIZE for size in addr_sizes),
              detail=detail)
    rep.check("DWARF CU format == DWARF64 (all units)", f"format={DWARF_FORMAT}",
              f"units={len(formats)}, formats={formats}",
              rc == 0 and bool(formats)
              and all(fmt == DWARF_FORMAT for fmt in formats),
              detail=detail)


def run_checks(tools: dict[str, Path], target: str, work: Path,
               verbose: bool = True,
               link_args: tuple[str, ...] = ()) -> Report:
    rep = Report(verbose=verbose)
    check_static_sizes(tools, target, work, rep)
    check_objects(tools, target, work, rep, link_args)
    return rep


def resolve_tools(args: argparse.Namespace) -> dict[str, Path]:
    default_bin = _paths.host_toolchain_bin()
    return {
        "clang": Path(args.clang) if args.clang else default_bin / "clang",
        "readelf": Path(args.readelf) if args.readelf else default_bin / "llvm-readelf",
        "dwarfdump": Path(args.dwarfdump) if args.dwarfdump
        else default_bin / "llvm-dwarfdump",
    }


def missing_tools(tools: dict[str, Path]) -> list[str]:
    return [f"{name}: {path}" for name, path in tools.items() if not path.is_file()]


# --------------------------------------------------------------------------
# --self-test: fake tools, one injection per assertion.  Nothing is built and
# no real toolchain is touched; every mutation is restored from a byte copy and
# verified by md5 (no git).
# --------------------------------------------------------------------------
FAKE_CLANG = """#!/bin/sh
out=""; prev=""; src=""; compile=0
for a in "$@"; do
  if [ "$prev" = "-o" ]; then out="$a"; fi
  case "$a" in
    *.c) src="$a";;
    -c) compile=1;;
  esac
  prev="$a"
done
if [ -n "$FAKE_FAIL_MARKER" ] && grep -q "$FAKE_FAIL_MARKER" "$src" 2>/dev/null; then
  echo "fake-clang: injected compile failure ($FAKE_FAIL_MARKER)" >&2
  exit 1
fi
if [ "$compile" -eq 0 ] && [ -n "$FAKE_FAIL_LINK" ]; then
  echo "fake-clang: injected link failure" >&2
  exit 1
fi
if [ -n "$out" ]; then : > "$out"; fi
exit 0
"""

# The fakes reject a missing input file, like the real tools do: otherwise a
# failed compile/link would still be reported as a parsed .o/.elf.
FAKE_READELF = """#!/bin/sh
last=""
for a in "$@"; do last="$a"; done
if [ ! -f "$last" ]; then
  echo "fake-readelf: no such file: $last" >&2
  exit 1
fi
case " $* " in
  *" -h "*) cat "$FAKE_ELF_HEADER" 2>/dev/null; exit 0;;
  *" -S "*) cat "$FAKE_ELF_SECTIONS" 2>/dev/null; exit 0;;
esac
echo "fake-readelf: unsupported args: $*" >&2
exit 1
"""

FAKE_DWARFDUMP = """#!/bin/sh
last=""
for a in "$@"; do last="$a"; done
if [ ! -f "$last" ]; then
  echo "fake-dwarfdump: no such file: $last" >&2
  exit 1
fi
cat "$FAKE_DWARF_INFO" 2>/dev/null
exit 0
"""

GOOD_HEADER = """ELF Header:
  Magic:   7f 45 4c 46 02 02 01 00 00 00 00 00 00 00 00 00
  Class:                             ELF64
  Data:                              2's complement, big endian
  Machine:                           da0
"""

GOOD_SECTIONS = """There are 12 section headers, starting at offset 0x1e8:

Section Headers:
  [Nr] Name              Type            Address          Off    Size   ES Flg Lk Inf Al
  [ 0]                   NULL            0000000000000000 000000 000000 00      0   0  0
  [ 3] .rela.text        RELA            0000000000000000 0001e8 000030 18   I 11   2  8
  [ 4] .rela.data        RELA            0000000000000000 000218 000018 18   I 11   4  8
  [ 8] .got              PROGBITS        0000000000000000 000120 000008 00  WA  0   0  8
  [ 9] .rela.got         RELA            0000000000000000 000230 000018 18   I 11   8  8
"""

GOOD_DWARF = """.debug_info contents:
0x00000000: Compile Unit: length = 0x0000004c, format = DWARF64, version = 0x0005, unit_type = DW_UT_compile, abbr_offset = 0x0000, addr_size = 0x08 (next unit at 0x00000054)

0x0000000c: DW_TAG_compile_unit
              DW_AT_producer ("clang version 23")
"""


def _md5(path: Path) -> str:
    import hashlib
    return hashlib.md5(path.read_bytes()).hexdigest()


def self_test() -> int:
    import hashlib

    tmp_root = WORK_ROOT / "width-selftest"
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="run-", dir=tmp_root))
    total_fail = 0
    try:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, body in (("clang", FAKE_CLANG), ("llvm-readelf", FAKE_READELF),
                           ("llvm-dwarfdump", FAKE_DWARFDUMP)):
            tool = bin_dir / name
            tool.write_text(body, encoding="utf-8")
            tool.chmod(0o755)
        tools = {"clang": bin_dir / "clang", "readelf": bin_dir / "llvm-readelf",
                 "dwarfdump": bin_dir / "llvm-dwarfdump"}

        header = root / "elf-header.txt"
        sections = root / "elf-sections.txt"
        dwarf = root / "dwarf-info.txt"
        header.write_text(GOOD_HEADER, encoding="utf-8")
        sections.write_text(GOOD_SECTIONS, encoding="utf-8")
        dwarf.write_text(GOOD_DWARF, encoding="utf-8")
        os.environ["FAKE_ELF_HEADER"] = str(header)
        os.environ["FAKE_ELF_SECTIONS"] = str(sections)
        os.environ["FAKE_DWARF_INFO"] = str(dwarf)
        os.environ.pop("FAKE_FAIL_MARKER", None)

        def run(expect_red: bool, expected_name: str, label: str) -> None:
            nonlocal total_fail
            rep = run_checks(tools, TARGET, root, verbose=False)
            red = rep.failures >= 1
            hit = any(expected_name in name for name in rep.failed)
            ok = (red and hit) if expect_red else (not red)
            total_fail += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] self-test {label}: "
                  f"expected={'red via %r' % expected_name if expect_red else 'green'} "
                  f"actual={rep.failures} failure(s), failed={rep.failed}")

        def inject_file(path: Path, bad_text: str, expected_name: str,
                        label: str) -> None:
            """Overwrite with a bad copy, expect the named assertion to fail,
            restore the good bytes (cp equivalent) and verify by md5."""
            nonlocal total_fail
            good = path.read_bytes()
            good_md5 = hashlib.md5(good).hexdigest()
            path.write_text(bad_text, encoding="utf-8")
            run(True, expected_name, f"{label} (injected)")
            path.write_bytes(good)
            restored = path.is_file() and hashlib.md5(path.read_bytes()).hexdigest() == good_md5
            total_fail += 0 if restored else 1
            print(f"[{'PASS' if restored else 'FAIL'}] self-test {label} restore: "
                  f"expected=md5 {good_md5} "
                  f"actual={_md5(path) if path.is_file() else '<missing>'}")
            run(False, "", f"{label} (restored)")

        print("self-test: the [FAIL] lines below are the *injected* failures "
              "(expected); each injection is followed by its restore + green run")
        run(False, "", "baseline")

        # 1: compile-time static assertion.
        os.environ["FAKE_FAIL_MARKER"] = "sizeof(long)"
        run(True, "static sizeof(long)", "static-size injection")
        os.environ.pop("FAKE_FAIL_MARKER", None)
        run(False, "", "static-size restore")

        # 2a: the `-g -c` compile (the probe source carries the marker).
        os.environ["FAKE_FAIL_MARKER"] = "width_probe"
        run(True, "`-g -c` compiles", "g-compile injection")
        os.environ.pop("FAKE_FAIL_MARKER", None)
        run(False, "", "g-compile restore")

        # 2b: the link step of the `-g` image.
        os.environ["FAKE_FAIL_LINK"] = "1"
        run(True, "`-g` link succeeds", "link injection")
        os.environ.pop("FAKE_FAIL_LINK", None)
        run(False, "", "link restore")

        # 3: ELF class.
        inject_file(header, GOOD_HEADER.replace("ELF64", "ELF32"),
                    "ELF class", "elf-class injection")

        # 4 (vacuous): no RELA section at all.
        no_rela = "\n".join(
            line for line in GOOD_SECTIONS.splitlines()
            if " RELA " not in line) + "\n"
        inject_file(sections, no_rela, "RELA sections exist",
                    "rela-missing injection")

        # 4: RELA entsize (24 -> 16).
        bad_sections = GOOD_SECTIONS.replace(" 18   I", " 10   I")
        if bad_sections == GOOD_SECTIONS:
            # Fail closed if the injection ever stops matching: an injection
            # that changes nothing must not be reported as PASS.
            print("[FAIL] self-test rela-entsize injection: injector did not "
                  "modify the section table")
            total_fail += 1
        inject_file(sections, bad_sections, "every RELA section entsize",
                    "rela-entsize injection")

        # 5: GOT entry width (8 -> 4).
        inner = GOOD_SECTIONS.replace(
            "[ 8] .got              PROGBITS        0000000000000000 000120 000008 00  WA  0   0  8",
            "[ 8] .got              PROGBITS        0000000000000000 000120 000004 00  WA  0   0  8")
        inject_file(sections, inner, ".got entry width", "got-width injection")

        # 5 (vacuous): no .got / .rela.got at all.
        no_got = "\n".join(
            line for line in GOOD_SECTIONS.splitlines()
            if ".got" not in line) + "\n"
        inject_file(sections, no_got, ".got entry width", "got-missing injection")

        # 6a: DWARF address size (0x08 -> 0x04).
        inject_file(dwarf, GOOD_DWARF.replace("addr_size = 0x08", "addr_size = 0x04"),
                    "addr_size", "dwarf-addr-size injection")

        # 6b: DWARF format (DWARF64 -> DWARF32).
        inject_file(dwarf, GOOD_DWARF.replace("DWARF64", "DWARF32"),
                    "format", "dwarf-format injection")

        # Final word: the full fake run must be green again.
        run(False, "", "final baseline")
    finally:
        shutil.rmtree(root, ignore_errors=True)
        for key in ("FAKE_ELF_HEADER", "FAKE_ELF_SECTIONS", "FAKE_DWARF_INFO",
                    "FAKE_FAIL_MARKER", "FAKE_FAIL_LINK"):
            os.environ.pop(key, None)

    print("-" * 72)
    if total_fail:
        print(f"check-width-sizes --self-test: FAIL ({total_fail} injection(s) "
              "did not behave as required)")
        return 1
    print("check-width-sizes --self-test: PASS (every assertion has a reached "
          "FAIL path; injected fields restored by cp + md5)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DADAO 64-bit width / DWARF64 probe (LLVM-130t, L1).")
    parser.add_argument("--clang", help="clang to probe (default: install root)")
    parser.add_argument("--readelf", help="llvm-readelf (default: install root)")
    parser.add_argument("--dwarfdump", help="llvm-dwarfdump (default: install root)")
    parser.add_argument("--target", default=TARGET,
                        help=f"target triple to probe (default: {TARGET})")
    parser.add_argument("--link-arg", action="append", default=[], metavar="ARG",
                        help="extra argument for the -g link step (repeatable; "
                             "used by the 32-bit negative control for -fuse-ld=lld)")
    parser.add_argument("--keep", action="store_true",
                        help="keep the temporary work directory")
    parser.add_argument("--self-test", action="store_true",
                        help="fake-tool injection test (no toolchain required)")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    tools = resolve_tools(args)
    print("check-width-sizes -- L1 width/DWARF64 probe "
          f"(target={args.target})")
    missing = missing_tools(tools)
    if missing:
        for item in missing:
            print(f"  [FAIL] missing tool: {item}")
        print("check-width-sizes: FAIL (run `make install-host` first)")
        return 1

    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=WORK_ROOT))
    try:
        rep = run_checks(tools, args.target, work,
                         link_args=tuple(args.link_arg))
    finally:
        if args.keep:
            print(f"check-width-sizes: work dir kept at {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)

    print(f"  {rep.checks - rep.failures}/{rep.checks} assertions passed "
          "(count computed live)")
    print("-" * 72)
    if rep.failures:
        print(f"check-width-sizes: FAIL ({rep.failures} of {rep.checks} "
              f"assertions failed; tools: clang={tools['clang']})")
        return 1
    print("check-width-sizes: PASS (64-bit sizes + ELF64/rela/got + DWARF64 "
          "addr_size 8)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
