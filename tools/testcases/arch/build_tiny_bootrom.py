#!/usr/bin/env python3
"""Build the Kaiwu-Tiny 8 KiB fixed BootROM image (m12-chipyard-007; m19 layout).

Spec source: ``spec/Kaiwu-测试机运行环境.md``
  * §6.1  image index table (16-byte big-endian header + 32-byte entries);
  * §6.2  Tiny layout and the hmon load contract (M19 8 KiB geometry):

      image offset 0x0000-0x07FF  power boot stub   (flat, reset vector, <=2 KiB)
                   0x0800-0x13FF  hmon source seg  (flat, hmon SRAM base, <=3 KiB)
                   0x1400-0x1EFF  reserved          (all zero)
                   0x1F00-0x1F2F  image index table (count = 1, type = 1, 48 B)
                   0x1F30-0x1FFF  reserved          (all zero)

The builder *packs*; the firmware validates.  Every condition §6.1/§6.2 asks the
builder to enforce is enforced here and makes the tool exit non-zero:

  * power/hmon segment size <= 2 KiB / 3 KiB (link-time asserts also guard this);
  * the segments are linked at the addresses the layout implies
    (power e_entry == BootROM base, hmon e_entry == hmon SRAM base);
  * the hmon code matches the §6.2 data-page contract (0x0C00-0x0CFF outside the
    copied segment): the handler addresses the page through one second base
    register, whose bootstrap is the only rb0-relative 8-byte ld/st and reaches
    the page; see ``hmon_layout_problems`` for the exact checks;
  * the hmon table entry is 8-byte aligned (`offset`/`size`) and points at the
    hmon segment; `flags` bit31:3 are zero and bit2 is clear (a flat segment has
    no ELF structure to check, §6.1);
  * `boot_magic` sits below the semihosting tag range and is patched into the
    power stub's ``trap cfx_hmon, <magic>`` instruction;
  * the image is exactly 8 KiB; the reserved regions and every unused table
    byte are zero.

Outputs (``--out-dir``): ``bootrom_tiny.bin`` (the image the SoC boots) and,
with ``--hex-out``, the checked-in text hex that the chipyard ``wuming``
resource generator decodes into ``/dadao/bootrom/bootrom.tiny.img`` (a component
patch set cannot carry binary blobs).  The hex is *sparse*: ``@<offset>`` lines
set the write offset and byte lines append, so the reserved zeros cost one
line instead of hundreds.

Usage:
  build_tiny_bootrom.py --out-dir DIR --power-elf P --hmon-elf H \\
      --llvm-objcopy OBJCOPY --llvm-nm NM [--hex-out FILE] [--self-test]
  build_tiny_bootrom.py ... --max-segment-size N    # injection / evidence
  build_tiny_bootrom.py --check-hex IMAGE HEX       # image vs checked-in hex
  build_tiny_bootrom.py --dump IMAGE                # layout report

Exit code: 0 iff the image was produced and every check passed.
"""

import argparse
import os
import struct
import subprocess
import sys
import tempfile

MAGIC = 0x44424F54  # "DBOT"
VERSION = 1
COUNT = 1
DEFAULT_BOOT_MAGIC = 0x30001
SEMIHOST_TAG = 0x3FF00

# spec/Kaiwu §6.2 — fixed Tiny layout (image offsets, M19 8 KiB geometry).
BOOTROM_SIZE = 0x2000
POWER_SEG_OFF = 0x0000
POWER_SEG_MAX = 0x0800
HMON_SEG_OFF = 0x0800
HMON_SEG_MAX = 0x0C00
RESERVED_OFF = 0x1400           # 0x1400-0x1EFF，全零
TABLE_OFF = 0x1F00
TABLE_SIZE = 0x30               # 表头 16 B + 1 表项 32 B
TABLE_HDR = 16
TABLE_ENT = 32
# 表后保留尾（0x1F30-0x1FFF）也必须全零。
TABLE_END = TABLE_OFF + TABLE_SIZE

# spec/DADAO-12 §2.1 / contracts/machine.yaml (tiny).
BOOTROM_BASE = 0xFFFF_FFFF_0000
HMON_BASE = 0x0FFF_0000_0000

# hmon SRAM partitioning (spec/Kaiwu §6.2, M19 8 KiB geometry):
#   code 0x0000-0x0BFF  (<= 3 KiB; occupied by the copied source segment)
#   data 0x0C00-0x0CFF  (256 B, initial 0; *outside* the image segment --
#                        power copies only `size` bytes, i.e. the code)
#   stack 0x0D00-0x1FFF
HMON_DATA_BASE = 0xC00          # data page start == code region limit
HMON_DATA_SIZE = 0x100
#
# Page layout inside the data area: the firmware/framework contract
# (m19-testcases-005; `tests/ee-tiny/cfx_hmon_tiny.S` is the source of truth).
# hmon writes the three cause slots and saves the two registers it clobbers;
# power writes the default return address; the test framework may overwrite
# the return slot to redirect `escape`.
HMON_SLOT_CAUSE_ID = 0x00
HMON_SLOT_CAUSE_IP = 0x08
HMON_SLOT_CAUSE_INFO = 0x10
HMON_SLOT_RETURN = 0x18
HMON_SLOT_RD63 = 0x20
HMON_SLOT_RB63 = 0x28
# entry `jump` + 15-instruction body (0x500-0x53C).
HMON_CODE_MIN = 0x40

# 8-byte ld/st opcodes carrying a base register (contracts/opcodes.yaml:
# fields rdha[23:18] / rbhb[17:12] / imms12[11:0]); 0x20/0x21 address an RD
# register, 0x22/0x23 an RB register.
LDO_RD, STO_RD, LDO_RB, STO_RB = 0x20, 0x21, 0x22, 0x23
LDST_OPS = (LDO_RD, STO_RD, LDO_RB, STO_RB)
JUMP_REL = 0x70
ESCAPE = 0x7E
RB0 = 0
RB_BASE = 63            # the handler's data-page base register (rb63)

FLAG_REQUIRED, FLAG_LOAD, FLAG_VERIFY = 1, 2, 4
DEFAULT_HMON_FLAGS = FLAG_REQUIRED | FLAG_LOAD  # flat segment: no ELF verify


class BuildError(Exception):
    pass


def be16(buf, off):
    return struct.unpack_from(">H", buf, off)[0]


def be32(buf, off):
    return struct.unpack_from(">I", buf, off)[0]


def be64(buf, off):
    return struct.unpack_from(">Q", buf, off)[0]


def align8(x):
    return (x + 7) & ~7


def sign_extend(value, bits):
    sign = 1 << (bits - 1)
    return (value & (sign - 1)) - (value & sign)


def ldst_base(word):
    return (word >> 12) & 0x3F


def ldst_imm(word):
    return sign_extend(word & 0xFFF, 12)


def hmon_layout_problems(hmon):
    """Static re-read of the hmon code against the §6.2 data-page contract.

    The handler cannot address 0x0C00 with a single `rb0`-relative ld/st (the
    immediate is a signed 12-bit field, spec/SimRISC-01) and `rb0` reads as the
    current IP, so it keeps a second base register (rb63 = HMON_BASE + 0x0C00)
    and reaches the page with small immediates.  The bootstrap therefore has to
    be one *IP-relative* store of rb63's previous value into the page.  Checks:

      * word 0 is a relative `jump [rb0, ...]` whose target lies inside the code;
      * exactly one `rb0`-relative 8-byte ld/st: the bootstrap, and its
        effective address (instruction address + imms12) is +0x28 (saved rb63);
      * every other 8-byte ld/st is relative to rb63 and its immediate is one of
        the contract offsets: cause_id/ip/info (stores), return (load),
        saved rd63 (store + load), saved rb63 (load) -- exact multiset;
      * the final instruction is `escape cfx_hmon`.
    """
    problems = []
    words = [be32(hmon, off) for off in range(0, len(hmon) - 3, 4)]
    # §6.1 `size` is 8-byte aligned: strip the zero padding the builder appends.
    while words and words[-1] == 0:
        words.pop()
    if not words:
        return ["hmon code is empty"]

    def name(off):
        return "%#06x" % off

    entry = words[0]
    entry_target = None
    if (entry >> 24) != JUMP_REL:
        problems.append("entry %s is %#010x, not `jump [rb0, ...]`"
                        % (name(0), entry))
    else:
        # rb0 of the entry instruction is its own offset (0) ⇒ target = imms24<<2
        entry_target = sign_extend(entry & 0xFFFFFF, 24) * 4
        if not 0 < entry_target < len(hmon):
            problems.append("entry jump target %#x is outside the code (%#x B)"
                            % (entry_target, len(hmon)))

    rb0_accesses, base_accesses = [], []
    for off, word in enumerate(words):
        if (word >> 24) not in LDST_OPS:
            continue
        base = ldst_base(word)
        if base == RB0:
            rb0_accesses.append((off * 4, word, (off * 4) + ldst_imm(word)))
        elif base == RB_BASE:
            base_accesses.append((off * 4, word, ldst_imm(word)))
        else:
            problems.append("8-byte ld/st at %s uses base rb%d (only rb0 for the "
                            "bootstrap and rb%d for the data page are allowed)"
                            % (name(off * 4), base, RB_BASE))

    if len(rb0_accesses) != 1:
        problems.append("%d rb0-relative 8-byte ld/st instructions, expected "
                        "exactly 1 (the bootstrap saving rb63)"
                        % len(rb0_accesses))
    else:
        off, word, eff = rb0_accesses[0]
        if (word >> 24) != STO_RB:
            problems.append("bootstrap at %s is not `st.o rb63, [rb0, ...]` "
                            "(%#010x)" % (name(off), word))
        elif (word >> 18) & 0x3F != RB_BASE:
            problems.append("bootstrap at %s stores rb%d, expected rb%d"
                            % (name(off), (word >> 18) & 0x3F, RB_BASE))
        if entry_target is not None and entry_target != off:
            problems.append("entry jump target %#x is not the bootstrap at %#x "
                            "(the body must start with the rb63 save)"
                            % (entry_target, off))
        want = HMON_DATA_BASE + HMON_SLOT_RB63
        if eff != want:
            problems.append("bootstrap at %s reaches %#x, expected %#x "
                            "(data page + rb63 slot)" % (name(off), eff, want))

    want_words = [
        (STO_RD, HMON_SLOT_RD63),        # save rd63
        (STO_RD, HMON_SLOT_CAUSE_ID),
        (STO_RD, HMON_SLOT_CAUSE_IP),
        (STO_RD, HMON_SLOT_CAUSE_INFO),
        (LDO_RD, HMON_SLOT_RETURN),      # escape ip <- return address
        (LDO_RD, HMON_SLOT_RD63),        # restore rd63
        (LDO_RB, HMON_SLOT_RB63),        # restore rb63 (must be last)
    ]
    got_words = [(w >> 24, imm) for _off, w, imm in base_accesses]
    if sorted(got_words) != sorted(want_words):
        problems.append("rb%d data-page accesses are %s, expected %s"
                        % (RB_BASE,
                           ", ".join("%s.o %+d" % (
                               {LDO_RD: "ld", STO_RD: "st", LDO_RB: "ld",
                                STO_RB: "st"}[op], imm)
                               for op, imm in got_words) or "none",
                           ", ".join("%s.o %+d" % (
                               {LDO_RD: "ld", STO_RD: "st", LDO_RB: "ld",
                                STO_RB: "st"}[op], imm)
                               for op, imm in sorted(want_words))))
    elif got_words[-1] != (LDO_RB, HMON_SLOT_RB63):
        problems.append("the rb%d restore is not the last data-page access "
                        "(rb%d must stay valid until it is restored)"
                        % (RB_BASE, RB_BASE))

    if words[-1] != ((ESCAPE << 24) | (3 << 18)):
        problems.append("last word is %#010x, not `escape cfx_hmon`"
                        % words[-1])
    return problems


class Elf:
    """Minimal big-endian ELF64 reader: entry point + load footprint check."""

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
            if be32(self.data, off + 0) != 1:  # PT_LOAD
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
            self.loads.append({"offset": p_offset, "paddr": p_paddr,
                               "filesz": p_filesz, "memsz": p_memsz})
        if not self.loads:
            raise BuildError("%s: no PT_LOAD segment" % path)

    def require_origin(self, base, name):
        if self.e_entry != base:
            raise BuildError("%s: e_entry %#x != %#x (%s must start at its load base)"
                             % (self.path, self.e_entry, base, name))
        for seg in self.loads:
            if seg["paddr"] < base:
                raise BuildError("%s: PT_LOAD %#x is below the %s base %#x"
                                 % (self.path, seg["paddr"], name, base))


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise BuildError("command failed (%d): %s\n%s" % (
            proc.returncode, " ".join(cmd), proc.stderr.strip()))
    return proc.stdout


def flat(elf_path, objcopy, workdir, stem):
    out = os.path.join(workdir, stem + ".bin")
    run([objcopy, "-O", "binary", elf_path, out])
    with open(out, "rb") as f:
        return f.read()


def nm_symbol(elf, nm, symbol):
    for line in run([nm, elf]).splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] == symbol:
            return int(fields[0], 16)
    raise BuildError("%s: symbol %s not found" % (elf, symbol))


def patch_power_magic(power_bin, symbol_off, boot_magic):
    """Set the ``trap cfx_hmon, <boot_magic>`` immediate from the table value."""
    word_off = symbol_off - BOOTROM_BASE
    if word_off < 0 or word_off + 4 > len(power_bin) or word_off % 4:
        raise BuildError("boot_magic_trap symbol outside the flat power segment")
    word = struct.unpack_from(">I", power_bin, word_off)[0]
    if (word >> 24) != 0x7F or ((word >> 18) & 0x3F) != 3:
        raise BuildError("boot_magic_trap is not `trap cfx_hmon, ...` (%#x)" % word)
    if (word & 0x3FFFF) != DEFAULT_BOOT_MAGIC:
        raise BuildError("boot_magic_trap immediate %#x is not the source boot_magic %#x"
                         % (word & 0x3FFFF, DEFAULT_BOOT_MAGIC))
    patched = (word & ~0x3FFFF) | (boot_magic & 0x3FFFF)
    out = bytearray(power_bin)
    struct.pack_into(">I", out, word_off, patched)
    return bytes(out)


def build(args, max_segment, boot_magic, hmon_flags, out_name):
    power_elf = Elf(args.power_elf)
    hmon_elf = Elf(args.hmon_elf)
    power_elf.require_origin(BOOTROM_BASE, "power")
    hmon_elf.require_origin(HMON_BASE, "hmon")

    with tempfile.TemporaryDirectory(prefix="tinyboot-") as td:
        power_bin = flat(args.power_elf, args.llvm_objcopy, td, "power")
        hmon_bin = flat(args.hmon_elf, args.llvm_objcopy, td, "hmon")

    if len(power_bin) == 0 or len(hmon_bin) == 0:
        raise BuildError("power/hmon flat segment is empty")
    if len(power_bin) % 4 or len(hmon_bin) % 4:
        raise BuildError("power/hmon flat segment is not 4-byte aligned in size")

    # spec/Kaiwu §6.2: the hmon source segment is the *code* region only; the
    # data page at 0x0C00 must stay outside it (power copies `size` bytes).
    for slot_name, slot in (("cause_id", HMON_SLOT_CAUSE_ID),
                            ("cause_ip", HMON_SLOT_CAUSE_IP),
                            ("cause_info", HMON_SLOT_CAUSE_INFO),
                            ("return", HMON_SLOT_RETURN),
                            ("rd63", HMON_SLOT_RD63),
                            ("rb63", HMON_SLOT_RB63)):
        if slot % 8 or slot + 8 > HMON_DATA_SIZE:
            raise BuildError("internal: data-page slot %s at +%#04x is not an "
                             "8-byte slot inside the %#x-byte page"
                             % (slot_name, slot, HMON_DATA_SIZE))
    if len(hmon_bin) < HMON_CODE_MIN:
        raise BuildError("hmon segment is %d bytes: code is shorter than %#x"
                         % (len(hmon_bin), HMON_CODE_MIN))
    if len(hmon_bin) > HMON_DATA_BASE:
        raise BuildError("hmon code is %d bytes > the data page at %#x "
                         "(spec/Kaiwu §6.2: code 0x0000-0x0BFF, data 0x0C00)"
                         % (len(hmon_bin), HMON_DATA_BASE))
    layout = hmon_layout_problems(hmon_bin)
    if layout:
        raise BuildError("hmon code does not match the §6.2 data-page contract: "
                         + "; ".join(layout))
    if len(power_bin) > min(max_segment, POWER_SEG_MAX):
        raise BuildError("power segment is %d bytes > %d"
                         % (len(power_bin), min(max_segment, POWER_SEG_MAX)))
    hmon_raw = len(hmon_bin)
    hmon_size = align8(hmon_raw)  # §6.1 entry `size` is 8-byte aligned
    if hmon_size > min(max_segment, HMON_SEG_MAX):
        raise BuildError("hmon segment is %d bytes > %d"
                         % (hmon_size, min(max_segment, HMON_SEG_MAX)))
    if hmon_size != hmon_raw:
        hmon_bin = hmon_bin + b"\x00" * (hmon_size - hmon_raw)

    sym = nm_symbol(args.power_elf, args.llvm_nm, "boot_magic_trap")
    power_bin = patch_power_magic(power_bin, sym, boot_magic)

    image = bytearray(BOOTROM_SIZE)
    image[POWER_SEG_OFF:POWER_SEG_OFF + len(power_bin)] = power_bin
    image[HMON_SEG_OFF:HMON_SEG_OFF + hmon_size] = hmon_bin
    struct.pack_into(">IHHII", image, TABLE_OFF, MAGIC, VERSION, COUNT, boot_magic, 0)
    struct.pack_into(">IIQQQ", image, TABLE_OFF + TABLE_HDR,
                     1, hmon_flags, HMON_SEG_OFF, hmon_size, 0)
    if len(image) != BOOTROM_SIZE:
        raise BuildError("internal: image is not exactly %d bytes" % BOOTROM_SIZE)

    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, out_name)
    with open(out_path, "wb") as f:
        f.write(image)
    print("tiny-bootrom: layout power@%#06x(%d) hmon@%#06x(%d, padded %d) "
          "reserved@%#06x(%d) table@%#06x(count=%d type=1 flags=%#x boot_magic=%#x)"
          % (POWER_SEG_OFF, len(power_bin), HMON_SEG_OFF, hmon_raw,
             hmon_size, RESERVED_OFF, TABLE_OFF - RESERVED_OFF, TABLE_OFF, COUNT,
             hmon_flags, boot_magic))
    print("tiny-bootrom: wrote %s (%d bytes)" % (out_path, os.path.getsize(out_path)))
    ranges = [(POWER_SEG_OFF, POWER_SEG_OFF + len(power_bin)),
              (HMON_SEG_OFF, HMON_SEG_OFF + hmon_size),
              (TABLE_OFF, TABLE_OFF + TABLE_HDR + COUNT * TABLE_ENT)]
    return out_path, image, ranges, len(power_bin), hmon_size


def verify_image(image, boot_magic, hmon_flags):
    """Independent re-read of the produced bytes against §6.1/§6.2."""
    if len(image) != BOOTROM_SIZE:
        raise BuildError("verify: image is %d bytes, expected %d"
                         % (len(image), BOOTROM_SIZE))
    if be32(image, TABLE_OFF) != MAGIC:
        raise BuildError("verify: header magic mismatch")
    if be16(image, TABLE_OFF + 4) != VERSION:
        raise BuildError("verify: header version mismatch")
    if be16(image, TABLE_OFF + 6) != COUNT:
        raise BuildError("verify: header count mismatch")
    if be32(image, TABLE_OFF + 8) != boot_magic:
        raise BuildError("verify: header boot_magic mismatch")
    if be32(image, TABLE_OFF + 12) != 0:
        raise BuildError("verify: header reserved is not zero")
    typ, flags, off, size, resv = struct.unpack_from(">IIQQQ", image, TABLE_OFF + TABLE_HDR)
    if typ != 1:
        raise BuildError("verify: entry type %d != 1 (hmon)" % typ)
    if flags != hmon_flags:
        raise BuildError("verify: entry flags %#x != %#x" % (flags, hmon_flags))
    if flags & ~0x7:
        raise BuildError("verify: entry flags bit31:3 must be zero")
    if off % 8 or size % 8 or size == 0:
        raise BuildError("verify: entry offset/size must be 8-byte aligned and non-zero")
    if off != HMON_SEG_OFF or off + size > RESERVED_OFF:
        raise BuildError("verify: entry %#x+%#x is not the hmon segment" % (off, size))
    if resv != 0:
        raise BuildError("verify: entry reserved is not zero")
    if any(image[RESERVED_OFF:TABLE_OFF]):
        raise BuildError("verify: the reserved region %#x-%#x is not all zero"
                         % (RESERVED_OFF, TABLE_OFF))
    if any(image[TABLE_END:BOOTROM_SIZE]):
        raise BuildError("verify: the reserved tail %#x-%#x is not all zero"
                         % (TABLE_END, BOOTROM_SIZE))
    if not any(image[POWER_SEG_OFF:POWER_SEG_OFF + POWER_SEG_MAX]):
        raise BuildError("verify: power segment is empty")
    if not any(image[HMON_SEG_OFF:HMON_SEG_OFF + size]):
        raise BuildError("verify: hmon segment is empty")
    # spec/Kaiwu §6.2: re-read the data-page contract from the produced image.
    hmon = image[HMON_SEG_OFF:HMON_SEG_OFF + size]
    if len(hmon) < HMON_CODE_MIN:
        raise BuildError("verify: hmon code is shorter than %#x" % HMON_CODE_MIN)
    if len(hmon) > HMON_DATA_BASE:
        raise BuildError("verify: hmon code reaches the data page at %#x"
                         % HMON_DATA_BASE)
    layout = hmon_layout_problems(hmon)
    if layout:
        raise BuildError("verify: " + "; ".join(layout))


def to_hex(image, comment_lines, ranges, width=32):
    """Sparse text form: ``@<offset>`` sets the position, byte lines append.

    Only the payload ranges (power / hmon / table) are written out; the
    reserved region and the unused table tail stay implicit zeros.
    """
    lines = ["# " + c if c else "#" for c in comment_lines]
    for start, end in ranges:
        lines.append("@%06x" % start)
        for k in range(start, end, width):
            lines.append(" ".join("%02x" % b for b in image[k:min(k + width, end)]))
    return "\n".join(lines) + "\n"


def hex_to_bytes(path, size=BOOTROM_SIZE):
    image = bytearray(size)
    pos = 0
    with open(path) as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("@"):
                try:
                    pos = int(line[1:], 16)
                except ValueError:
                    raise BuildError("%s:%d: bad offset line %r" % (path, lineno, line))
                if pos > size:
                    raise BuildError("%s:%d: offset %#x is past the image" % (path, lineno, pos))
                continue
            digits = "".join(line.split())
            if len(digits) % 2:
                raise BuildError("%s:%d: odd number of hex digits" % (path, lineno))
            for k in range(0, len(digits), 2):
                if pos >= size:
                    raise BuildError("%s:%d: data runs past the image" % (path, lineno))
                image[pos] = int(digits[k:k + 2], 16)
                pos += 1
    return bytes(image)


def check_hex(image_path, hex_path):
    with open(image_path, "rb") as f:
        image = f.read()
    decoded = hex_to_bytes(hex_path, len(image))
    if decoded == image:
        print("check-hex: %s matches %s (%d bytes)" % (hex_path, image_path, len(image)))
        return 0
    if len(decoded) != len(image):
        print("check-hex: FAIL: %s decodes to %d bytes, image is %d"
              % (hex_path, len(decoded), len(image)), file=sys.stderr)
        return 1
    for i in range(len(image)):
        if decoded[i] != image[i]:
            print("check-hex: FAIL: first difference at offset %#06x (hex=%02x image=%02x)"
                  % (i, decoded[i], image[i]), file=sys.stderr)
            return 1
    return 1


def dump(image_path):
    with open(image_path, "rb") as f:
        image = f.read()
    print("dump: %s = %d bytes" % (image_path, len(image)))
    if len(image) != BOOTROM_SIZE:
        print("dump: FAIL: size is not %d" % BOOTROM_SIZE, file=sys.stderr)
        return 1
    header = "magic=%#x version=%d count=%d boot_magic=%#x reserved=%#x" % (
        be32(image, TABLE_OFF), be16(image, TABLE_OFF + 4),
        be16(image, TABLE_OFF + 6), be32(image, TABLE_OFF + 8),
        be32(image, TABLE_OFF + 12))
    print("dump: table @%#06x %s" % (TABLE_OFF, header))
    for i in range(COUNT):
        typ, flags, off, size, resv = struct.unpack_from(
            ">IIQQQ", image, TABLE_OFF + TABLE_HDR + i * TABLE_ENT)
        print("dump: entry %d type=%d flags=%#x offset=%#06x size=%d reserved=%#x"
              % (i, typ, flags, off, size, resv))
    print("dump: power[%#06x,%#06x) hmon[%#06x,%#06x) reserved[%#06x,%#06x) "
          "table[%#06x,%#06x) reserved-tail[%#06x,%#06x)"
          % (POWER_SEG_OFF, HMON_SEG_OFF, HMON_SEG_OFF, RESERVED_OFF,
             RESERVED_OFF, TABLE_OFF, TABLE_OFF, TABLE_END,
             TABLE_END, BOOTROM_SIZE))
    nonzero = sum(1 for b in image if b)
    print("dump: non-zero bytes = %d of %d" % (nonzero, len(image)))
    return 0


def self_test(args):
    """Build a private copy and prove the size guard and hex check can fail."""
    print("self-test: building a private copy")
    with tempfile.TemporaryDirectory(prefix="tinyboot-selftest-") as td:
        st = argparse.Namespace(**vars(args))
        st.out_dir = td
        path, image, ranges, _p, _h = build(st, min(POWER_SEG_MAX, HMON_SEG_MAX),
                                           DEFAULT_BOOT_MAGIC, DEFAULT_HMON_FLAGS,
                                           "self-test.bin")
        verify_image(image, DEFAULT_BOOT_MAGIC, DEFAULT_HMON_FLAGS)
        print("self-test: layout/table verify PASS")
        hex_path = os.path.join(td, "self-test.hex")
        with open(hex_path, "w") as f:
            f.write(to_hex(image, ["self-test"], ranges))
        if check_hex(path, hex_path) != 0:
            raise BuildError("self-test: hex round-trip did not match")
        print("self-test: hex round-trip PASS")
        # 1) the segment size guard must reject an injected limit.
        try:
            build(st, 64, DEFAULT_BOOT_MAGIC, DEFAULT_HMON_FLAGS, "neg-size.bin")
        except BuildError:
            print("self-test: injected --max-segment-size=64 rejected PASS")
        else:
            raise BuildError("self-test: injected segment size limit was not enforced")
        # 2) the hex check must reject a one-byte image change.
        bad = bytearray(image)
        bad[HMON_SEG_OFF] ^= 0xFF
        bad_hex = os.path.join(td, "bad.hex")
        with open(bad_hex, "w") as f:
            f.write(to_hex(bad, ["injected"], ranges))
        if check_hex(path, bad_hex) == 0:
            raise BuildError("self-test: hex check accepted a corrupted image")
        print("self-test: injected hex corruption rejected PASS")
        # 3) the reserved-zone check must reject a dirty reserved region.
        dirty = bytearray(image)
        dirty[RESERVED_OFF + 16] = 0x5A
        try:
            verify_image(dirty, DEFAULT_BOOT_MAGIC, DEFAULT_HMON_FLAGS)
        except BuildError:
            print("self-test: injected reserved-zone byte rejected PASS")
        else:
            raise BuildError("self-test: reserved-zone check did not fire")
        # 4) a table entry pointing at the wrong segment must be rejected.
        wrong = bytearray(image)
        struct.pack_into(">Q", wrong, TABLE_OFF + TABLE_HDR + 8, POWER_SEG_OFF)
        try:
            verify_image(wrong, DEFAULT_BOOT_MAGIC, DEFAULT_HMON_FLAGS)
        except BuildError:
            print("self-test: injected entry offset rejected PASS")
        else:
            raise BuildError("self-test: entry-offset check did not fire")
    print("self-test: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--power-elf", default=None)
    ap.add_argument("--hmon-elf", default=None)
    ap.add_argument("--llvm-objcopy", default=None)
    ap.add_argument("--llvm-nm", default=None)
    ap.add_argument("--boot-magic", default=hex(DEFAULT_BOOT_MAGIC))
    ap.add_argument("--hmon-flags", default=hex(DEFAULT_HMON_FLAGS))
    ap.add_argument("--max-segment-size", type=int,
                    default=max(POWER_SEG_MAX, HMON_SEG_MAX))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out-name", default="bootrom_tiny.bin")
    ap.add_argument("--hex-out", default=None,
                    help="also write the text hex image (checked-in bootrom.tiny.hex)")
    ap.add_argument("--check-hex", nargs=2, metavar=("IMAGE", "HEX"), default=None,
                    help="compare a built image against a text hex file and exit")
    ap.add_argument("--dump", default=None, help="print a layout report for IMAGE")
    args = ap.parse_args()

    try:
        if args.check_hex:
            return check_hex(args.check_hex[0], args.check_hex[1])
        if args.dump:
            return dump(args.dump)
    except BuildError as exc:
        print("tiny-bootrom: FAIL: %s" % exc, file=sys.stderr)
        return 1

    missing = [n for n in ("out_dir", "power_elf", "hmon_elf", "llvm_objcopy", "llvm_nm")
               if getattr(args, n) is None]
    if missing:
        print("tiny-bootrom: FAIL: missing required options: %s"
              % ", ".join("--" + m.replace("_", "-") for m in missing), file=sys.stderr)
        return 2

    boot_magic = int(args.boot_magic, 0)
    hmon_flags = int(args.hmon_flags, 0)
    if not 0 < boot_magic < SEMIHOST_TAG:
        print("tiny-bootrom: boot-magic must be non-zero and below the semihosting tag range",
              file=sys.stderr)
        return 2

    try:
        if args.self_test:
            return self_test(args)
        path, image, ranges, power_len, hmon_len = build(
            args, args.max_segment_size, boot_magic, hmon_flags, args.out_name)
        verify_image(image, boot_magic, hmon_flags)
        if args.hex_out:
            with open(args.hex_out, "w") as f:
                f.write(to_hex(image, [
                    "Kaiwu-Tiny fixed BootROM image (m12-chipyard-007)",
                    "Generated by tools/testcases/arch/build_tiny_bootrom.py — do not edit.",
                    "Layout (spec/Kaiwu §6.2): power %#06x..%#06x, hmon %#06x..%#06x,"
                    % (POWER_SEG_OFF, HMON_SEG_OFF, HMON_SEG_OFF, RESERVED_OFF),
                    "reserved %#06x..%#06x (all zero), image index table %#06x..%#06x."
                    % (RESERVED_OFF, TABLE_OFF, TABLE_OFF, BOOTROM_SIZE),
                    "power segment = %d B, hmon segment = %d B." % (power_len, hmon_len),
                ], ranges))
            print("tiny-bootrom: wrote hex %s" % args.hex_out)
    except BuildError as exc:
        print("tiny-bootrom: FAIL: %s" % exc, file=sys.stderr)
        return 1
    print("tiny-bootrom: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
