#!/usr/bin/env python3
"""Toolchain *content* identity: GNU ELF build-id, ``sha256`` fallback (INFRA-101t).

Why this module exists (``LLVM-122t`` night run, 2026-10-22): the freshness
gates used the tool binaries' **mtime** as a proxy for "the toolchain changed".
``make install-host`` re-links ``clang`` deterministically after any codegen
input change (``touch`` one ``.td``), so the installed ``clang`` is
**byte-identical** with a new mtime.  The proxy reported "changed" and forced a
full musl rebuild plus a compiler-rt builtins rebuild; one L2 run (which embeds
``install-host``) then cost hours instead of ~20 min.

The identity used here is derived from the bytes only:

* primary: the ELF ``NT_GNU_BUILD_ID`` note (a few KB to read -- both
  ``clang`` and ``ld.lld`` carry one);
* fallback: ``sha256`` of the whole file, with a one-time warning (a toolchain
  without GNU build-id is not the supported configuration; the fallback keeps
  the gate meaningful instead of silently skipping the check).

``mtime`` / ``ctime`` / ``size`` are **not** part of any identity.  ``ctime``
was already excluded in ``ISS-263``; this module removes ``mtime`` (and size)
for the same reason: they are inode metadata, not content.

The ELF note is parsed in pure Python on purpose: the gates must work on hosts
that have no ``readelf`` (the install root is not required to carry one, and
``check-musl-freshness`` is an L1 gate on a fresh checkout).

CLI (used by ``Makefile::build-builtins`` to write the builtins sidecar):

    python3 tools/infra/toolchain_id.py --write <stamp-file> \\
        --tool-dir .work/build/llvm/bin [--tool clang --tool ld.lld] \\
        [--archive <libclang_rt.builtins.a>]

``--self-test`` injects synthetic ELFs (build-id / no build-id) and proves the
identity is stable under a pure mtime change and moves when the bytes move.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import subprocess
import sys
from pathlib import Path

ELF_MAGIC = b"\x7fELF"
ELFCLASS32, ELFCLASS64 = 1, 2
ELFDATA2LSB, ELFDATA2MSB = 1, 2
SHT_NOTE = 7
PT_NOTE = 4
NT_GNU_BUILD_ID = 3
GNU_NOTE_NAME = b"GNU"
# Upper bound for a note area we are willing to slurp (notes are tiny; this only
# guards against a corrupt header pointing at the whole file).
MAX_NOTE_AREA = 1 << 20

# One warning per binary per process: the fallback reads (and hashes) the whole
# file -- for a 4 GB clang that is a real cost, and it must be said out loud
# once rather than on every stamp line.
_WARNED: set[str] = set()


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── ELF note parsing ────────────────────────────────────────────────────────
def _notes_build_id(area: bytes, endian: str) -> str | None:
    """``NT_GNU_BUILD_ID`` hex from a raw note area, or ``None``."""
    pos = 0
    while pos + 12 <= len(area):
        namesz, descsz, ntype = struct.unpack_from(endian + "III", area, pos)
        pos += 12
        if namesz > len(area) or descsz > len(area):
            return None
        name = area[pos:pos + namesz]
        pos += (namesz + 3) & ~3
        desc = area[pos:pos + descsz]
        pos += (descsz + 3) & ~3
        if ntype == NT_GNU_BUILD_ID and name.rstrip(b"\0") == GNU_NOTE_NAME and desc:
            return desc.hex()
    return None


def _read_at(f, offset: int, size: int) -> bytes:
    if offset < 0 or size < 0 or size > MAX_NOTE_AREA:
        return b""
    f.seek(offset)
    return f.read(size)


def elf_build_id(path: Path) -> str | None:
    """Return the ``NT_GNU_BUILD_ID`` of an ELF file as hex, or ``None``.

    Section headers are tried first (the canonical ``.note.gnu.build-id``), then
    ``PT_NOTE`` program headers -- a stripped binary may lose the section table
    but keeps the segment.  Anything unparsable is ``None`` (the caller falls
    back to ``sha256``; nothing here raises on a non-ELF file).
    """
    try:
        with open(path, "rb") as f:
            ident = f.read(16)
            if len(ident) < 16 or ident[:4] != ELF_MAGIC:
                return None
            cls, data = ident[4], ident[5]
            if cls not in (ELFCLASS32, ELFCLASS64):
                return None
            if data == ELFDATA2LSB:
                endian = "<"
            elif data == ELFDATA2MSB:
                endian = ">"
            else:
                return None
            rest = f.read(64 - 16)
            # ELF32 header ends at 52 bytes (36 after e_ident); ELF64 at 64 (48).
            if len(rest) < (48 if cls == ELFCLASS64 else 36):
                return None
            if cls == ELFCLASS64:
                (_etype, _mach, _ver, _entry, phoff, shoff, _flags, _ehsize,
                 phentsize, phnum, shentsize, shnum, shstrndx) = \
                    struct.unpack_from(endian + "HHIQQQIHHHHHH", rest, 0)
            else:
                (_etype, _mach, _ver, _entry, phoff, shoff, _flags, _ehsize,
                 phentsize, phnum, shentsize, shnum, shstrndx) = \
                    struct.unpack_from(endian + "HHIIIIIHHHHHH", rest, 0)

            # 1) the section named `.note.gnu.build-id` (when the table is there)
            if shoff and shnum and shstrndx < shnum and shentsize:
                shdrs = _read_at(f, shoff, shentsize * shnum)
                if len(shdrs) == shentsize * shnum:
                    def field(idx: int) -> tuple[int, int, int, int]:
                        off = idx * shentsize
                        if cls == ELFCLASS64:
                            (nm, typ, _fl, _ad, off_, size, _ln, _inf,
                             _al, _es) = struct.unpack_from(
                                 endian + "IIQQQQIIQQ", shdrs, off)
                        else:
                            (nm, typ, _fl, _ad, off_, size, _ln, _inf,
                             _al, _es) = struct.unpack_from(
                                 endian + "IIIIIIIIII", shdrs, off)
                        return nm, typ, off_, size

                    _nm, _typ, stroff, strsize = field(shstrndx)
                    names = _read_at(f, stroff, strsize)
                    order = list(range(shnum))
                    named = []
                    for idx in order:
                        nm, typ, off_, size = field(idx)
                        if typ != SHT_NOTE:
                            continue
                        label = b""
                        if names and nm < len(names):
                            label = names[nm:names.find(b"\0", nm)]
                        named.append((label == b".note.gnu.build-id", off_, size))
                    named.sort(reverse=True)  # the named section first
                    for _is_build_id, off_, size in named:
                        bid = _notes_build_id(_read_at(f, off_, size), endian)
                        if bid:
                            return bid

            # 2) PT_NOTE segments (section table stripped / absent)
            if phoff and phnum and phentsize:
                phdrs = _read_at(f, phoff, phentsize * phnum)
                if len(phdrs) == phentsize * phnum:
                    for idx in range(phnum):
                        off = idx * phentsize
                        if cls == ELFCLASS64:
                            ptype, _pf, poff, _va, _pa, fsz, _msz, _al = \
                                struct.unpack_from(endian + "IIQQQQQQ", phdrs, off)
                        else:
                            ptype, poff, _va, _pa, fsz, _msz, _pf, _al = \
                                struct.unpack_from(endian + "IIIIIIII", phdrs, off)
                        if ptype != PT_NOTE:
                            continue
                        bid = _notes_build_id(_read_at(f, poff, fsz), endian)
                        if bid:
                            return bid
    except (OSError, struct.error):
        return None
    return None


def content_id(path: Path, *, warn: bool = True) -> tuple[str, str]:
    """``("build-id"|"sha256", value)`` -- the content identity of a binary."""
    bid = elf_build_id(path)
    if bid:
        return "build-id", bid
    key = str(path)
    if warn and key not in _WARNED:
        _WARNED.add(key)
        print(f"toolchain-id: WARNING: no GNU build-id in {path}; falling back "
              f"to sha256 of the whole file (slower; a GNU toolchain carries a "
              f"build-id, so this is an unsupported configuration)",
              file=sys.stderr)
    return "sha256", sha256_of(path)


def version_line(path: Path) -> str:
    """First line of ``--version`` (a display/extra guard, never the criterion)."""
    try:
        res = subprocess.run([str(path), "--version"], capture_output=True,
                             text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return "version=unavailable"
    if res.returncode != 0:
        return f"version=rc={res.returncode}"
    first = (res.stdout.splitlines() or [""])[0]
    return first or "version=unavailable"


def stamp_line(tool: str, path: Path) -> str:
    """``<tool> -> <realpath> <kind>=<value> <version line>``.

    The path stays for readability/debugging; only ``<kind>=<value>`` is a
    criterion (gates compare ``kind``/``value`` per tool, never the path).
    """
    real = path.resolve()
    kind, value = content_id(path)
    return f"{tool} -> {real} {kind}={value} {version_line(path)}"


def stamp_text(tool_dir: Path, tools: tuple[str, ...] | list[str]) -> str:
    return "\n".join(stamp_line(t, tool_dir / t) for t in tools) + "\n"


def stamp_entries(text: str) -> dict[str, tuple[str, str]]:
    """Parse ``<tool> -> <path> <kind>=<value> ...`` lines into a dict.

    Lines that do not carry ``build-id=``/``sha256=`` (e.g. the retired
    ``mtime=`` format) are skipped, so a caller can detect them separately with
    :func:`is_legacy_stamp`.
    """
    out: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] != "->":
            continue
        for token in parts[2:]:
            for kind in ("build-id", "sha256"):
                if token.startswith(kind + "="):
                    out[parts[0]] = (kind, token.split("=", 1)[1])
                    break
            if parts[0] in out:
                break
    return out


def is_legacy_stamp(text: str) -> bool:
    """A stamp written before INFRA-101t (``mtime=`` proxy) ⇒ needs migration."""
    return "mtime=" in text


# ── sidecar writer (builtins archive) ───────────────────────────────────────
def write_sidecar(out: Path, tool_dir: Path, tools: tuple[str, ...] | list[str],
                  archive: Path | None = None) -> str:
    """Write the toolchain identity of the *archive producer* next to the archive."""
    lines = [stamp_line(t, tool_dir / t) for t in tools]
    if archive is not None:
        lines.append(f"archive-sha256={sha256_of(archive)}")
    text = "\n".join(lines) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return text


def read_sidecar(path: Path) -> tuple[dict[str, tuple[str, str]], str | None]:
    """``({tool: (kind, value)}, archive sha256 or None)``; empty dict when absent."""
    try:
        text = path.read_text()
    except OSError:
        return {}, None
    archive = None
    for line in text.splitlines():
        if line.startswith("archive-sha256="):
            archive = line.split("=", 1)[1].strip()
    return stamp_entries(text), archive


# ── self-test ───────────────────────────────────────────────────────────────
def test_elf_with_build_id(build_id: bytes, *, with_sections: bool = True) -> bytes:
    """Minimal ELF64/LE carrying ``build_id`` as an ``NT_GNU_BUILD_ID`` note.

    Test fixture for ``--self-test`` here and in the freshness gates (one ELF
    layout implementation, not one per test).  ``with_sections=False`` leaves
    the section table out, so the parser must find the note through ``PT_NOTE``.
    """
    endian = "<"
    note = (struct.pack(endian + "III", len(GNU_NOTE_NAME) + 1, len(build_id),
                        NT_GNU_BUILD_ID) + GNU_NOTE_NAME + b"\0" + build_id)
    note += b"\0" * ((4 - len(note) % 4) % 4)
    ehsize, phentsize, shentsize = 64, 56, 64
    phnum = 1
    note_off = ehsize
    ph_off = note_off + len(note)
    shstr = b"\0.note.gnu.build-id\0"
    shstr_off = ph_off + phentsize * phnum
    sh_off = shstr_off + len(shstr)
    sh_off += (8 - sh_off % 8) % 8
    shnum = 2 if with_sections else 0
    shstrndx = 1 if with_sections else 0
    shoff = sh_off if with_sections else 0
    total = (sh_off + shentsize * shnum) if with_sections else shstr_off
    blob = bytearray(total)

    blob[0:16] = ELF_MAGIC + bytes((ELFCLASS64, ELFDATA2LSB, 1)) + b"\0" * 9
    struct.pack_into(endian + "HHIQQQIHHHHHH", blob, 16,
                     # e_type, e_machine, e_version, e_entry, e_phoff, e_shoff
                     2, 0x3E, 1, 0, ph_off, shoff,
                     # e_flags, e_ehsize, e_phentsize, e_phnum
                     0, ehsize, phentsize, phnum,
                     # e_shentsize, e_shnum, e_shstrndx
                     shentsize, shnum, shstrndx)
    blob[note_off:note_off + len(note)] = note
    struct.pack_into(endian + "IIQQQQQQ", blob, ph_off,
                     PT_NOTE, 4, note_off, 0, 0, len(note), len(note), 4)
    if with_sections:
        blob[shstr_off:shstr_off + len(shstr)] = shstr
        # section 1: .note.gnu.build-id, SHT_NOTE
        struct.pack_into(endian + "IIQQQQIIQQ", blob, sh_off + shentsize,
                         1, SHT_NOTE, 0, 0, note_off, len(note), 0, 0, 4, 0)
    return bytes(blob)


def self_test() -> int:
    """Baseline + injections; every expectation has a reachable FAIL."""
    import tempfile

    print("toolchain-id --self-test (ELF note parse + content identity)")
    tmp_root = Path("/tmp/opencode/INFRA-101t")
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="toolchain-id-selftest-", dir=str(tmp_root)))
    bad = 0

    def verdict(name: str, expected: str, actual: str, ok: bool) -> None:
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] self-test {name}: "
              f"expected={expected} actual={actual}")

    try:
        bid_a = bytes.fromhex("de2e20d7e585817e19924fa5b26746ca5099cb59")
        bid_b = bytes.fromhex("585596725c4908cd13d42a9b4303dbfc77ec6a55")
        for sections in (True, False):
            path = root / f"elf-sections-{sections}"
            path.write_bytes(test_elf_with_build_id(bid_a, with_sections=sections))
            got = elf_build_id(path)
            verdict(f"parse build-id (section table={sections})", bid_a.hex(),
                    got, got == bid_a.hex())

        # no build-id in an ELF (plain phdr-less blob) => sha256 fallback
        plain = root / "not-an-elf"
        plain.write_bytes(b"not an elf at all\n")
        kind, value = content_id(plain, warn=False)
        verdict("non-ELF falls back to sha256", "sha256",
                f"{kind}", kind == "sha256" and value == sha256_of(plain))

        # mtime is NOT part of the identity; content is.
        tool_dir = root / "bin"
        tool_dir.mkdir()
        fake = tool_dir / "clang"
        fake.write_bytes(test_elf_with_build_id(bid_a))
        before = stamp_text(tool_dir, ("clang",))
        import os
        st = fake.stat()
        os.utime(fake, ns=(st.st_atime_ns, st.st_mtime_ns + 123_456_789))
        after_mtime = stamp_text(tool_dir, ("clang",))
        verdict("mtime-only change keeps the identity", "identical",
                "identical" if before == after_mtime else "different",
                before == after_mtime)
        fake.write_bytes(test_elf_with_build_id(bid_b))
        after_content = stamp_text(tool_dir, ("clang",))
        entry = stamp_entries(after_content).get("clang")
        verdict("content change moves the identity", f"build-id={bid_b.hex()}",
                str(entry), entry == ("build-id", bid_b.hex()))

        text = stamp_text(tool_dir, ("clang",))
        verdict("stamp has no mtime= and no size=", "absent",
                "mtime=" + ("present" if "mtime=" in text else "absent")
                + " size=" + ("present" if "size=" in text else "absent"),
                "mtime=" not in text and "size=" not in text)

        legacy = "clang -> /x/clang size=1 mtime=2 clang version 23\n"
        verdict("legacy stamp detected", "True", str(is_legacy_stamp(legacy)),
                is_legacy_stamp(legacy))
        verdict("current stamp is not legacy", "False", str(is_legacy_stamp(text)),
                not is_legacy_stamp(text))
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)

    print(f"toolchain-id: --self-test {'PASS' if bad == 0 else 'FAIL'} "
          f"({bad} unexpected outcome(s))")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="toolchain content identity")
    ap.add_argument("--write", type=Path,
                    help="write a stamp/sidecar to this path")
    ap.add_argument("--tool-dir", type=Path,
                    help="directory holding the tool binaries")
    ap.add_argument("--tool", action="append", default=None,
                    help="tool name to record (repeatable; default clang, ld.lld)")
    ap.add_argument("--archive", type=Path, default=None,
                    help="optional archive whose sha256 is recorded (sidecar)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    tools = tuple(args.tool or ("clang", "ld.lld"))
    if args.write is None or args.tool_dir is None:
        ap.error("--write and --tool-dir are required (or use --self-test)")
    for tool in tools:
        if not (args.tool_dir / tool).is_file():
            print(f"toolchain-id: ERROR: tool not found: {args.tool_dir / tool}",
                  file=sys.stderr)
            return 2
    if args.archive is not None and not args.archive.is_file():
        print(f"toolchain-id: ERROR: archive not found: {args.archive}",
              file=sys.stderr)
        return 2
    text = write_sidecar(args.write, args.tool_dir, tools, args.archive)
    print(f"toolchain-id: wrote {args.write}")
    print(text.rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
