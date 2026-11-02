#!/usr/bin/env python3
"""Build the INTEG-046t 256 KiB BootROM image from the three step5 ELFs.

Spec sources (task file is the interface truth for this artifact):
  * .tao/tasks/integ/INTEG-046t-Step5启动链落地.md §接口规范 1 (image index
    table: 16-byte big-endian header + 32-byte entries) and §接口规范 2
    (ELF image checks, enforced by the *firmware*; this builder only packs).
  * .tao/adr/adr-0043-boot-handoff.md D1/D2 (256 KiB BootROM, image index
    table, ELF images, 64 KiB reset window).

Layout produced (all big-endian):
  offset 0x00000  header + 2 entries
  offset after header/entries (16-byte aligned)  hmon.elf
  offset after hmon              (16-byte aligned)  smon.elf
  ... zero pad ...
  offset 0x30000 .. 0x3ffff    power flat bytes (linked at 0xffff_ffff_0000)

The table's boot_magic is also patched into the power stage's
`boot_magic_trap` instruction (symbol address from llvm-nm), so the handoff
immediate can be overridden without assembling a second power image.

Usage:
  build_step5_bootrom.py --out-dir DIR --power-elf P --hmon-elf H \
      --smon-elf S --llvm-objcopy OBJCOPY --llvm-nm NM [--self-test]
  build_step5_bootrom.py ... --max-image-size N     # injection / evidence

Exit code: 0 iff the image was produced and every check passed.
"""

import argparse
import os
import struct
import subprocess
import sys
import tempfile

MAGIC = 0x44424F54
VERSION = 1
COUNT = 2
DEFAULT_BOOT_MAGIC = 0x30001
BOOTROM_SIZE = 0x40000
POWER_OFF = 0x30000
POWER_WINDOW = 0x10000
POWER_ORIGIN = 0xFFFF_FFFF_0000
DEFAULT_MAX = 0x10000
FLAG_REQUIRED, FLAG_LOAD, FLAG_VERIFY = 1, 2, 4


class BuildError(Exception):
    pass


def be16(buf, off):
    return struct.unpack_from(">H", buf, off)[0]


def be32(buf, off):
    return struct.unpack_from(">I", buf, off)[0]


def be64(buf, off):
    return struct.unpack_from(">Q", buf, off)[0]


class Elf:
    """Minimal big-endian ELF64 reader (only what packing/checking needs)."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        if self.data[:4] != b"\x7fELF":
            raise BuildError("%s: not an ELF file" % path)
        if self.data[4] != 2 or self.data[5] != 2:
            raise BuildError("%s: expected ELFCLASS64/ELFDATA2MSB" % path)
        self.e_type = be16(self.data, 16)
        self.e_machine = be16(self.data, 18)
        self.e_entry = be64(self.data, 24)
        self.e_phoff = be64(self.data, 32)
        self.e_flags = be32(self.data, 48)
        self.e_ehsize = be16(self.data, 52)
        self.e_phentsize = be16(self.data, 54)
        self.e_phnum = be16(self.data, 56)
        if self.e_type != 2:
            raise BuildError("%s: e_type %d != ET_EXEC" % (path, self.e_type))
        if self.e_machine != 0x0DA0:
            raise BuildError("%s: e_machine %#x != EM_DADAO" % (path, self.e_machine))
        if self.e_flags != 1:
            raise BuildError("%s: e_flags %#x != 1" % (path, self.e_flags))
        if self.e_ehsize != 64 or self.e_phentsize != 56:
            raise BuildError("%s: unexpected Ehdr/Phdr sizes" % path)
        if self.e_phoff + self.e_phnum * 56 > len(self.data):
            raise BuildError("%s: program headers outside the file" % path)
        self.loads = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * 56
            p_type = be32(self.data, off + 0)
            if p_type != 1:  # PT_LOAD
                continue
            p_offset = be64(self.data, off + 8)
            p_vaddr = be64(self.data, off + 16)
            p_paddr = be64(self.data, off + 24)
            p_filesz = be64(self.data, off + 32)
            p_memsz = be64(self.data, off + 40)
            if p_filesz > p_memsz:
                raise BuildError("%s: PT_LOAD p_filesz > p_memsz" % path)
            if p_offset + p_filesz > len(self.data):
                raise BuildError("%s: PT_LOAD file range outside the image" % path)
            if p_vaddr != p_paddr:
                raise BuildError("%s: PT_LOAD p_vaddr != p_paddr" % path)
            self.loads.append({
                "offset": p_offset, "vaddr": p_vaddr,
                "filesz": p_filesz, "memsz": p_memsz,
            })
        if not self.loads:
            raise BuildError("%s: no PT_LOAD segment" % path)

    @property
    def memsz(self):
        return sum(seg["memsz"] for seg in self.loads)

    def entry_in_load(self):
        return any(seg["vaddr"] <= self.e_entry < seg["vaddr"] + seg["memsz"]
                   for seg in self.loads)


def align16(x):
    return (x + 15) & ~15


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise BuildError("command failed (%d): %s\n%s" % (
            proc.returncode, " ".join(cmd), proc.stderr.strip()))
    return proc.stdout


def flat_power(power_elf, objcopy, workdir):
    out = os.path.join(workdir, "power.bin")
    run([objcopy, "-O", "binary", power_elf, out])
    with open(out, "rb") as f:
        return f.read()


def nm_symbol(elf, nm, symbol):
    out = run([nm, elf])
    for line in out.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] == symbol:
            return int(fields[0], 16)
    raise BuildError("%s: symbol %s not found" % (elf, symbol))


def patch_power_magic(power_bin, symbol_off, boot_magic):
    word_off = symbol_off - POWER_ORIGIN
    if word_off < 0 or word_off + 4 > len(power_bin) or word_off % 4:
        raise BuildError("power trap symbol outside the flat image")
    word = struct.unpack_from(">I", power_bin, word_off)[0]
    if (word >> 24) != 0x7F or ((word >> 18) & 0x3F) != 3:
        raise BuildError("boot_magic_trap is not `trap cfx_hmon, ...` (%#x)" % word)
    patched = (word & ~0x3FFFF) | (boot_magic & 0x3FFFF)
    out = bytearray(power_bin)
    struct.pack_into(">I", out, word_off, patched)
    return bytes(out)


def build(args, max_size, boot_magic, hmon_flags, smon_flags, out_name):
    hmon = Elf(args.hmon_elf)
    smon = Elf(args.smon_elf)

    for name, elf in (("hmon", hmon), ("smon", smon)):
        if len(elf.data) > max_size:
            raise BuildError("%s ELF file is %d bytes > %d" %
                             (name, len(elf.data), max_size))
        if elf.memsz > max_size:
            raise BuildError("%s load footprint (sum p_memsz) is %d > %d" %
                             (name, elf.memsz, max_size))
    if not hmon.entry_in_load() or not smon.entry_in_load():
        raise BuildError("e_entry not inside a PT_LOAD segment")

    with tempfile.TemporaryDirectory(prefix="step5-") as td:
        power_bin = flat_power(args.power_elf, args.llvm_objcopy, td)
    if len(power_bin) > max_size or len(power_bin) > POWER_WINDOW:
        raise BuildError("power flat segment is %d bytes > %d" %
                         (len(power_bin), min(max_size, POWER_WINDOW)))
    sym = nm_symbol(args.power_elf, args.llvm_nm, "boot_magic_trap")
    power_bin = patch_power_magic(power_bin, sym, boot_magic)

    hmon_off = align16(16 + COUNT * 32)
    smon_off = align16(hmon_off + len(hmon.data))
    end = smon_off + len(smon.data)
    if end > POWER_OFF:
        raise BuildError("images overlap the power window (end %#x)" % end)

    image = bytearray(BOOTROM_SIZE)
    struct.pack_into(">IHHII", image, 0, MAGIC, VERSION, COUNT,
                     boot_magic, 0)
    entries = (
        (1, hmon_flags, hmon_off, len(hmon.data)),
        (2, smon_flags, smon_off, len(smon.data)),
    )
    for i, (typ, flags, off, size) in enumerate(entries):
        struct.pack_into(">IIQQQ", image, 16 + i * 32,
                         typ, flags, off, size, 0)
    image[hmon_off:hmon_off + len(hmon.data)] = hmon.data
    image[smon_off:smon_off + len(smon.data)] = smon.data
    image[POWER_OFF:POWER_OFF + len(power_bin)] = power_bin
    if len(image) != BOOTROM_SIZE:
        raise BuildError("internal: image is not exactly %d bytes" % BOOTROM_SIZE)

    out_path = os.path.join(args.out_dir, out_name)
    os.makedirs(args.out_dir, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(image)

    print("step5: header magic=%#x version=%d count=%d boot_magic=%#x" %
          (MAGIC, VERSION, COUNT, boot_magic))
    for typ, flags, off, size in entries:
        print("step5: entry type=%d flags=%#x offset=%#x size=%d" %
              (typ, flags, off, size))
    print("step5: hmon footprint=%d smon footprint=%d power=%d" %
          (hmon.memsz, smon.memsz, len(power_bin)))
    print("step5: wrote %s (%d bytes)" % (out_path, os.path.getsize(out_path)))
    return out_path


def verify_image(path, boot_magic, hmon_flags, smon_flags):
    with open(path, "rb") as f:
        img = f.read()
    if len(img) != BOOTROM_SIZE:
        raise BuildError("self-test: image is %d bytes, expected %d" %
                         (len(img), BOOTROM_SIZE))
    if be32(img, 0) != MAGIC or be16(img, 4) != VERSION or be16(img, 6) != COUNT:
        raise BuildError("self-test: header mismatch")
    if be32(img, 8) != boot_magic or be32(img, 12) != 0:
        raise BuildError("self-test: boot magic/reserved mismatch")
    img_entries = []
    for i in range(COUNT):
        typ, flags, off, size, res = struct.unpack_from(">IIQQQ", img, 16 + i * 32)
        if typ != i + 1 or res != 0:
            raise BuildError("self-test: entry %d type/reserved bad" % i)
        if off + size > POWER_OFF:
            raise BuildError("self-test: entry %d overlaps the power window" % i)
        img_entries.append((typ, flags, off, size))
    if img_entries[0][1] != hmon_flags or img_entries[1][1] != smon_flags:
        raise BuildError("self-test: flags mismatch")
    # Every image entry is an ELF with the expected machine.
    for typ, _flags, off, size in img_entries:
        if img[off:off + 4] != b"\x7fELF":
            raise BuildError("self-test: entry type %d is not an ELF" % typ)
        if be16(img, off + 18) != 0x0DA0:
            raise BuildError("self-test: entry type %d e_machine mismatch" % typ)
    # Power trap immediate equals the table boot magic.  Locate the first
    # `trap cfx_hmon, <non-semihosting immu18>` word in the power window.
    trap_word = None
    for off in range(POWER_OFF, BOOTROM_SIZE - 3, 4):
        w = struct.unpack_from(">I", img, off)[0]
        if (w >> 24) == 0x7F and ((w >> 18) & 0x3F) == 3 and (w & 0x3FFFF) < 0x3FF00:
            trap_word = w
            break
    if trap_word is None or (trap_word & 0x3FFFF) != boot_magic:
        raise BuildError("self-test: power trap immediate %r != boot magic" %
                         (None if trap_word is None else hex(trap_word)))


def self_test(args):
    """Build in a temp dir and prove the size guard can fail."""
    print("self-test: building a private copy")
    with tempfile.TemporaryDirectory(prefix="step5-selftest-") as td:
        selftest_args = argparse.Namespace(**vars(args))
        selftest_args.out_dir = td
        path = build(selftest_args, DEFAULT_MAX, DEFAULT_BOOT_MAGIC,
                     FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY,
                     FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY,
                     "self-test.bin")
        verify_image(path, DEFAULT_BOOT_MAGIC,
                     FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY,
                     FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY)
        print("self-test: layout/table/trap verify PASS")
    # The size guard must reject an image bigger than an injected limit.
    try:
        with tempfile.TemporaryDirectory(prefix="step5-selftest-neg-") as td:
            neg_args = argparse.Namespace(**vars(args))
            neg_args.out_dir = td
            build(neg_args, 4096, DEFAULT_BOOT_MAGIC,
                  FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY,
                  FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY, "neg.bin")
    except BuildError:
        print("self-test: injected --max-image-size=4096 rejected PASS")
    else:
        raise BuildError("self-test: injected size limit was not enforced")
    print("self-test: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--power-elf", required=True)
    ap.add_argument("--hmon-elf", required=True)
    ap.add_argument("--smon-elf", required=True)
    ap.add_argument("--llvm-objcopy", required=True)
    ap.add_argument("--llvm-nm", required=True)
    ap.add_argument("--boot-magic", default=hex(DEFAULT_BOOT_MAGIC))
    ap.add_argument("--hmon-flags", default=hex(FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY))
    ap.add_argument("--smon-flags", default=hex(FLAG_REQUIRED | FLAG_LOAD | FLAG_VERIFY))
    ap.add_argument("--max-image-size", type=int, default=DEFAULT_MAX)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    boot_magic = int(args.boot_magic, 0)
    hmon_flags = int(args.hmon_flags, 0)
    smon_flags = int(args.smon_flags, 0)
    if not 0 <= boot_magic < 0x3FF00:
        print("step5: boot-magic must stay below the semihosting tag range", file=sys.stderr)
        return 2
    if boot_magic == 0:
        print("step5: boot-magic must be non-zero", file=sys.stderr)
        return 2

    try:
        if args.self_test:
            return self_test(args)
        build(args, args.max_image_size, boot_magic, hmon_flags, smon_flags,
              "bootrom_step5.bin")
        verify_image(os.path.join(args.out_dir, "bootrom_step5.bin"),
                     boot_magic, hmon_flags, smon_flags)
    except BuildError as exc:
        print("step5: FAIL: %s" % exc, file=sys.stderr)
        return 1
    print("step5: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
