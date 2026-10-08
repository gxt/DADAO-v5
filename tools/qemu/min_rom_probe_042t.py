#!/usr/bin/env python3
"""QEMU-042t evidence probe: DADAO M1 ELF loader (path A) + raw-bin compat.

Contract sources (spec-first; encodings NOT taken from QEMU):
  - contracts/opcodes.yaml            (instruction op/ha/masks)
  - .tao/knowledge/contract-elf.md §1/§5/§6
  - .tao/adr/adr-0004-test-machine.md (D1 memory map, D2.2/D2.3 load paths)

What it checks (each printed as "[PASS]/[FAIL] name: expected -> actual"):
  ELF path (A):
    * entry:   ELF with e_entry != RAM base; a `fence` (ILLI) poison sits at the
               RAM base, so the program can only report success if the
               loader really set PC = e_entry.
    * segments: .rodata/.data file bytes are placed at VA=PA; a `.bss` tail
               (p_memsz > p_filesz) reads back as zero; nonzero data is checked.
    * bounds:  a PT_LOAD that exactly fills RAM (16 MiB) and one that exactly
               fills ROM (64 KiB) load and run (no false rejection).
  raw-bin path (B, M1-M3):
    * -bios trampoline + flat -kernel still runs and exits 0.
    * ROM blob exactly 64 KiB and RAM image exactly 16 MiB are accepted.
  Negatives (load-stage, non-zero exit + explicit message):
    * malformed ELF: EI_CLASS / EI_DATA / e_machine / e_flags version /
      e_flags reserved / e_type / Phdr out of file bounds / p_filesz > p_memsz /
      segment outside mapped regions / truncated header / non-ELF without -bios.
    * oversize: ELF segment > RAM; raw-bin ROM blob > 64 KiB; raw-bin RAM image
      > 16 MiB (message must carry the actual size and the limit).

Usage:
  elf_probe_042t.py                 # run all checks
  elf_probe_042t.py --only NAME     # run a single check (used by --inject)

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import struct
import subprocess
import sys

def _repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != "/":
        if os.path.isfile(os.path.join(d, "manifests", "components.lock.toml")):
            return d
        d = os.path.dirname(d)
    raise RuntimeError("repo root not found (manifests/components.lock.toml)")


REPO_ROOT = _repo_root()
QEMU = os.path.join(REPO_ROOT, ".work/build/qemu/qemu-system-dadao")
WORKDIR = "/tmp/opencode/QEMU-042t"
TIMEOUT = 20

# Memory map (ADR-0004 D1)
RAM_BASE = 0xFFFF_0000_0000
RAM_SIZE = 16 * 1024 * 1024
ROM_BASE = 0xFFFF_FFFF_0000
ROM_SIZE = 64 * 1024
SEMI_BLOCK = 0xFFFF_00FF_F000        # SYS_EXIT argument block {reason, code}, in RAM
SEMIHOST_TAG = 0x30000               # immu18[17:16] == 2'b11 -> semihosting trap
ADP_STOPPED_APPLICATION_EXIT = 0x20026

EM_DADAO = 0x0DA0
EHDR_SIZE = 64
PHDR_SIZE = 56

# ---------------------------------------------------------------------------
# Instruction encoding (contracts/opcodes.yaml)
# ---------------------------------------------------------------------------

def set_zw_rd(rd, wp, imm):
    return (0x4C << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)

def or_w_rd(rd, wp, imm):
    return (0x48 << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)

def set_zw_rb(rb, wp, imm):
    return (0x4E << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)

def or_w_rb(rb, wp, imm):
    return (0x4A << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)

def st_o_rd(rd, rb, off):
    return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)

def ld_o_rd(rd, rb, off):
    return (0x20 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)

def xor_o(d, a, b):
    return 0x40280000 | (d << 12) | (a << 6) | b

def or_o(d, a, b):
    return 0x40240000 | (d << 12) | (a << 6) | b

def br_nz(rd, off_words):
    return (0x6B << 24) | (rd << 18) | (off_words & 0x3FFFF)

def jump_rrii(rb, rd, off_words):
    return (0x71 << 24) | (rb << 18) | (rd << 12) | (off_words & 0xFFF)

def trap(ha, immu18):
    return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)


def swym():
    return 0x77880000

def fence():
    return 0x77000000

def imm64_rd(rd, val):
    words = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            words.append(or_w_rd(rd, wp, w))
    return words

def imm64_rb(rb, val):
    words = [set_zw_rb(rb, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        w = (val >> (16 * wp)) & 0xFFFF
        if w:
            words.append(or_w_rb(rb, wp, w))
    return words

def code_set_semi_block():
    """rb16 = SEMI_BLOCK; block[0] = 0x20026 (ADR-0020 D8)."""
    return ([set_zw_rb(16, 2, 0xFFFF), or_w_rb(16, 1, 0x00FF), or_w_rb(16, 0, 0xF000)]
            + imm64_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o_rd(8, 16, 0)])

def code_exit(code):
    return (code_set_semi_block() + imm64_rd(9, code & 0xFF) + [st_o_rd(9, 16, 8)]
            + imm64_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)])

def code_data_checks(data_vaddr, checks):
    """acc(rd18) = OR over XOR(expected, memory); FAIL(1) if acc != 0."""
    words = code_set_semi_block()
    words += imm64_rb(17, data_vaddr)
    words += [set_zw_rd(18, 0, 0)]
    for off, val in checks:
        words += imm64_rd(16, val)
        words.append(ld_o_rd(17, 17, off))
        words.append(xor_o(16, 16, 17))
        words.append(or_o(18, 18, 16))
    pass_arm = imm64_rd(16, 0) + [st_o_rd(16, 16, 8)] + imm64_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)]
    fail_arm = imm64_rd(16, 1) + [st_o_rd(16, 16, 8)] + imm64_rd(16, 0x18) + [trap(0, SEMIHOST_TAG)]
    words.append(br_nz(18, 1 + len(pass_arm)))   # -> fail arm
    words += pass_arm                            # PASS (exit 0)
    words += fail_arm                            # FAIL (exit 1)
    return words

def words_to_bytes(words):
    return b"".join(struct.pack(">I", w) for w in words)

# ---------------------------------------------------------------------------
# ELF64 (big-endian) builder
# ---------------------------------------------------------------------------

def p16(x):
    return struct.pack(">H", x)

def p32(x):
    return struct.pack(">I", x)

def p64(x):
    return struct.pack(">Q", x)

def build_elf(entry, segments, *, e_type=2, e_machine=EM_DADAO, e_flags=1,
              ei_class=2, ei_data=2, phoff=EHDR_SIZE, ph_size=PHDR_SIZE,
              phnum=None):
    n = len(segments) if phnum is None else phnum
    ehdr = bytes([0x7F, ord("E"), ord("L"), ord("F"), ei_class, ei_data, 1, 0])
    ehdr += b"\x00" * 8
    ehdr += (p16(e_type) + p16(e_machine) + p32(1) + p64(entry) +
             p64(phoff) + p64(0) + p32(e_flags) + p16(EHDR_SIZE) +
             p16(ph_size) + p16(n) + p16(0) + p16(0) + p16(0))
    assert len(ehdr) == EHDR_SIZE, len(ehdr)

    phdrs = b""
    for s in segments:
        phdrs += p32(s["p_type"]) + p32(s.get("p_flags", 5))
        phdrs += p64(s["p_offset"]) + p64(s["p_vaddr"]) + p64(s["p_vaddr"])
        phdrs += p64(s["p_filesz"]) + p64(s["p_memsz"]) + p64(s.get("p_align", 0x10000))

    blob = bytearray(ehdr + phdrs)
    for s in segments:
        data = s.get("data", b"")
        if not data:
            continue
        end = s["p_offset"] + len(data)
        if end > len(blob):
            blob.extend(b"\x00" * (end - len(blob)))
        blob[s["p_offset"]:s["p_offset"] + len(data)] = data
    return bytes(blob)

def patch(blob, off, fmt, val):
    b = struct.pack(fmt, val)
    return blob[:off] + b + blob[off + len(b):]

# ---------------------------------------------------------------------------
# Test images
# ---------------------------------------------------------------------------

DATA_VADDR = RAM_BASE + 0x400
TEXT_VADDR_OFF = 0x400          # text segment occupies [RAM_BASE, RAM_BASE+0x400)
ENTRY_OFF = 0x100               # e_entry = RAM_BASE + 0x100 (poison at base)

RODATA0 = 0xDEADBEEFCAFEBABE
RODATA1 = 0x0123456789ABCDEF
DATA0 = 0x1122334455667788
DATA1 = 0x99AABBCCDDEEFF00
DATA_CHECKS = [(0, RODATA0), (8, RODATA1), (16, DATA0), (24, DATA1),
               (32, 0), (40, 0)]     # offsets 32/40 are the .bss tail

DATA_BYTES = (p64(RODATA0) + p64(RODATA1) + p64(DATA0) + p64(DATA1))


def text_with_entry(code_words):
    pre = ENTRY_OFF // 4
    words = [fence()] + [swym()] * (pre - 1) + code_words
    blob = words_to_bytes(words)
    assert len(blob) <= TEXT_VADDR_OFF, len(blob)
    return blob + b"\x00" * (TEXT_VADDR_OFF - len(blob))


def elf_segments_positive():
    """ELF with .text + (.rodata/.data/.bss) PT_LOAD, distinct entry."""
    text = text_with_entry(code_data_checks(DATA_VADDR, DATA_CHECKS))
    seg_text = dict(p_type=1, p_flags=5, p_offset=0x10000, p_vaddr=RAM_BASE,
                    p_filesz=len(text), p_memsz=len(text), data=text,
                    p_align=0x10000)
    seg_data = dict(p_type=1, p_flags=6, p_offset=0x10000 + TEXT_VADDR_OFF,
                    p_vaddr=DATA_VADDR, p_filesz=len(DATA_BYTES),
                    p_memsz=len(DATA_BYTES) + 16, data=DATA_BYTES, p_align=8)
    return build_elf(RAM_BASE + ENTRY_OFF, [seg_text, seg_data])


def elf_bss_only_offset():
    """Extra PT_LOAD with p_filesz==0 and an out-of-file p_offset: ELF says the
    p_offset of a zero-filesz segment is undefined, so it must NOT be rejected;
    the memsz is zero-filled."""
    text = text_with_entry(code_data_checks(DATA_VADDR, DATA_CHECKS))
    seg_text = dict(p_type=1, p_flags=5, p_offset=0x10000, p_vaddr=RAM_BASE,
                    p_filesz=len(text), p_memsz=len(text), data=text,
                    p_align=0x10000)
    seg_data = dict(p_type=1, p_flags=6, p_offset=0x10000 + TEXT_VADDR_OFF,
                    p_vaddr=DATA_VADDR, p_filesz=len(DATA_BYTES),
                    p_memsz=len(DATA_BYTES) + 16, data=DATA_BYTES, p_align=8)
    seg_bss = dict(p_type=1, p_flags=6, p_offset=0x100000,
                   p_vaddr=RAM_BASE + 0x800, p_filesz=0, p_memsz=8, p_align=8)
    return build_elf(RAM_BASE + ENTRY_OFF, [seg_text, seg_data, seg_bss])


def elf_exact_ram():
    """Single PT_LOAD whose p_memsz exactly fills RAM (16 MiB)."""
    text = text_with_entry(code_exit(0))
    seg = dict(p_type=1, p_flags=5, p_offset=0x10000, p_vaddr=RAM_BASE,
               p_filesz=len(text), p_memsz=RAM_SIZE, data=text, p_align=0x10000)
    return build_elf(RAM_BASE + ENTRY_OFF, [seg])


def elf_exact_rom():
    """Single PT_LOAD in ROM whose p_memsz exactly fills ROM (64 KiB)."""
    code = code_exit(0)
    data = words_to_bytes(code)
    seg = dict(p_type=1, p_flags=5, p_offset=0x1000, p_vaddr=ROM_BASE,
               p_filesz=len(data), p_memsz=ROM_SIZE, data=data, p_align=0x1000)
    return build_elf(ROM_BASE, [seg])


# ---------------------------------------------------------------------------
# QEMU runner
# ---------------------------------------------------------------------------

def write_tmp(name, data):
    os.makedirs(WORKDIR, exist_ok=True)
    path = os.path.join(WORKDIR, name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def run_qemu(elf_path=None, bios=None, kernel=None):
    args = [QEMU, "-M", "dadao-m1", "-nographic",
            "-semihosting-config", "enable=on,target=native"]
    if bios:
        args += ["-bios", bios]
    if kernel:
        args += ["-kernel", kernel]
    if elf_path:
        args += ["-kernel", elf_path]
    try:
        r = subprocess.run(args, capture_output=True, timeout=TIMEOUT, text=True,
                           stdin=subprocess.DEVNULL)
        return r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


# trampoline (ADR-0004 D6.4) for the raw-bin path
def build_trampoline():
    return words_to_bytes([
        set_zw_rb(1, 2, 0xFFFF),
        or_w_rb(1, 1, 0x00FF),
        set_zw_rb(2, 2, 0xFFFF),
        jump_rrii(2, 0, 0),
    ])


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

CHECKS = []

def check(name, desc=""):
    def deco(fn):
        CHECKS.append((name, desc, fn))
        return fn
    return deco


def msg_has(stderr, *needles):
    return all(n in stderr for n in needles)

def ok(msg):
    return True, msg

def bad(msg):
    return False, msg


@check("elf_data_bss", "ELF entry=e_entry, .rodata/.data placed, .bss zero")
def c_elf_data_bss():
    p = write_tmp("pos_data.elf", elf_segments_positive())
    rc, err = run_qemu(elf_path=p)
    if rc != 0:
        return bad("exit=%d (expected 0); stderr=%r" % (rc, err[:200]))
    return ok("exit=0")


@check("elf_bss_only_offset", "PT_LOAD p_filesz==0 with undefined p_offset accepted")
def c_elf_bss_only_offset():
    p = write_tmp("bss_only.elf", elf_bss_only_offset())
    rc, err = run_qemu(elf_path=p)
    if rc != 0:
        return bad("exit=%d (expected 0); stderr=%r" % (rc, err[:300]))
    return ok("exit=0")


@check("elf_fill_ram_exact", "ELF PT_LOAD p_memsz exactly 16 MiB runs (no false reject)")
def c_elf_fill_ram_exact():
    p = write_tmp("exact_ram.elf", elf_exact_ram())
    rc, err = run_qemu(elf_path=p)
    if rc != 0:
        return bad("exit=%d (expected 0); stderr=%r" % (rc, err[:300]))
    return ok("exit=0")


@check("elf_fill_rom_exact", "ELF PT_LOAD in ROM p_memsz exactly 64 KiB runs")
def c_elf_fill_rom_exact():
    p = write_tmp("exact_rom.elf", elf_exact_rom())
    rc, err = run_qemu(elf_path=p)
    if rc != 0:
        return bad("exit=%d (expected 0); stderr=%r" % (rc, err[:300]))
    return ok("exit=0")


@check("rawbin_compat", "-bios trampoline + flat -kernel exits 0 (M1-M3 path)")
def c_rawbin_compat():
    rom = write_tmp("tramp.bin", build_trampoline())
    ker = write_tmp("flat_ok.bin", words_to_bytes(code_exit(0)))
    rc, err = run_qemu(bios=rom, kernel=ker)
    if rc != 0:
        return bad("exit=%d (expected 0); stderr=%r" % (rc, err[:200]))
    return ok("exit=0")


@check("rawbin_rom_exact", "ROM blob exactly 64 KiB accepted")
def c_rawbin_rom_exact():
    rom = build_trampoline()
    rom += words_to_bytes([swym()]) * ((ROM_SIZE - len(rom)) // 4)
    assert len(rom) == ROM_SIZE, len(rom)
    rp = write_tmp("tramp_exact.bin", rom)
    ker = write_tmp("flat_ok.bin", words_to_bytes(code_exit(0)))
    rc, err = run_qemu(bios=rp, kernel=ker)
    if rc != 0:
        return bad("exit=%d (expected 0); stderr=%r" % (rc, err[:200]))
    return ok("exit=0 (ROM=64 KiB)")


@check("rawbin_ram_exact", "RAM image exactly 16 MiB accepted")
def c_rawbin_ram_exact():
    rom = build_trampoline()
    ker = words_to_bytes(code_exit(0))
    ker += words_to_bytes([swym()]) * ((RAM_SIZE - len(ker)) // 4)
    assert len(ker) == RAM_SIZE, len(ker)
    rp = write_tmp("tramp.bin", rom)
    kp = write_tmp("flat_exact_ram.bin", ker)
    rc, err = run_qemu(bios=rp, kernel=kp)
    if rc != 0:
        return bad("exit=%d (expected 0); stderr=%r" % (rc, err[:200]))
    return ok("exit=0 (RAM=16 MiB)")


# ---- malformed ELF negatives (load-stage, non-zero exit + message) ----

def _good_elf():
    return elf_segments_positive()


def _expect_load_error(blob, name, *needles):
    p = write_tmp(name, blob)
    rc, err = run_qemu(elf_path=p)
    if rc == 0:
        return bad("exit=0 (expected non-zero load error)")
    if not msg_has(err, *needles):
        return bad("exit=%d but stderr lacks %s: %r" % (rc, needles, err[:250]))
    return ok("exit=%d, msg ok" % rc)


@check("neg_bad_class", "EI_CLASS != ELFCLASS64 rejected")
def c_neg_bad_class():
    b = bytearray(_good_elf()); b[4] = 1
    return _expect_load_error(bytes(b), "neg_class.elf", "EI_CLASS")


@check("neg_bad_data", "EI_DATA != ELFDATA2MSB rejected")
def c_neg_bad_data():
    b = bytearray(_good_elf()); b[5] = 1
    return _expect_load_error(bytes(b), "neg_data.elf", "EI_DATA")


@check("neg_bad_machine", "e_machine != EM_DADAO rejected")
def c_neg_bad_machine():
    b = patch(_good_elf(), 18, ">H", 0x1234)
    return _expect_load_error(b, "neg_machine.elf", "e_machine")


@check("neg_bad_flags_ver", "e_flags[7:0] != 1 rejected")
def c_neg_bad_flags_ver():
    b = patch(_good_elf(), 48, ">I", 2)
    return _expect_load_error(b, "neg_flags_ver.elf", "e_flags")


@check("neg_bad_flags_res", "e_flags reserved bits[31:8] rejected")
def c_neg_bad_flags_res():
    b = patch(_good_elf(), 48, ">I", 0x101)   # version 1 + reserved bit 8
    return _expect_load_error(b, "neg_flags_res.elf", "reserved bits")


@check("neg_bad_type", "e_type != ET_EXEC rejected")
def c_neg_bad_type():
    b = patch(_good_elf(), 16, ">H", 1)
    return _expect_load_error(b, "neg_type.elf", "e_type")


@check("neg_phdr_oob", "program header table out of file bounds rejected")
def c_neg_phdr_oob():
    g = _good_elf()
    b = patch(g, 32, ">Q", len(g) + 64)      # e_phoff beyond EOF
    return _expect_load_error(b, "neg_phdr_oob.elf",
                              "program header table out of file bounds")


@check("neg_filesz_gt_memsz", "PT_LOAD p_filesz > p_memsz rejected")
def c_neg_filesz_gt_memsz():
    g = _good_elf()
    ph1 = EHDR_SIZE + PHDR_SIZE             # second program header
    memsz = struct.unpack_from(">Q", g, ph1 + 40)[0]
    b = patch(g, ph1 + 32, ">Q", memsz + 8)  # p_filesz = p_memsz + 8
    return _expect_load_error(b, "neg_filesz.elf", "p_filesz")


@check("neg_seg_out_of_range", "PT_LOAD vaddr outside mapped regions rejected")
def c_neg_seg_out_of_range():
    g = _good_elf()
    ph1 = EHDR_SIZE + PHDR_SIZE
    b = patch(g, ph1 + 16, ">Q", 0xFFFF_0200_0000)  # outside RAM
    return _expect_load_error(b, "neg_range.elf", "outside the mapped regions")


@check("neg_elf_truncated", "ELF magic but header shorter than Elf64_Ehdr rejected")
def c_neg_elf_truncated():
    return _expect_load_error(b"\x7fELF" + b"\x00" * 12, "neg_trunc.elf",
                              "smaller than Elf64_Ehdr")


@check("neg_bad_magic_no_bios", "non-ELF kernel without -bios rejected")
def c_neg_bad_magic_no_bios():
    p = write_tmp("not_elf.bin", words_to_bytes([swym()] * 4))
    rc, err = run_qemu(elf_path=p)          # no -bios
    if rc == 0:
        return bad("exit=0 (expected non-zero)")
    if not msg_has(err, "bad magic"):
        return bad("exit=%d but stderr lacks 'bad magic': %r" % (rc, err[:250]))
    return ok("exit=%d, msg ok" % rc)


# ---- oversize negatives ----

@check("oversize_elf_seg", "ELF segment p_memsz > RAM rejected with sizes")
def c_oversize_elf_seg():
    g = _good_elf()
    ph0 = EHDR_SIZE
    b = patch(g, ph0 + 40, ">Q", RAM_SIZE + 0x1000)   # first PT_LOAD memsz
    # keep p_vaddr at RAM base; interval now exceeds RAM
    p = write_tmp("oversize_elf.elf", b)
    rc, err = run_qemu(elf_path=p)
    if rc == 0:
        return bad("exit=0 (expected non-zero)")
    if not msg_has(err, "outside the mapped regions", "RAM"):
        return bad("exit=%d but stderr lacks region info: %r" % (rc, err[:300]))
    return ok("exit=%d, msg ok" % rc)


@check("oversize_rom_blob", "raw-bin ROM blob > 64 KiB rejected with actual size")
def c_oversize_rom_blob():
    rom = build_trampoline() + words_to_bytes([swym()]) * ((ROM_SIZE + 4 - len(build_trampoline())) // 4)
    rom = rom[:ROM_SIZE + 1]
    assert len(rom) == ROM_SIZE + 1, len(rom)
    rp = write_tmp("rom_oversize.bin", rom)
    ker = write_tmp("flat_ok.bin", words_to_bytes(code_exit(0)))
    rc, err = run_qemu(bios=rp, kernel=ker)
    if rc == 0:
        return bad("exit=0 (expected non-zero)")
    if not msg_has(err, str(ROM_SIZE + 1), str(ROM_SIZE)):
        return bad("exit=%d but stderr lacks actual/limit size: %r" % (rc, err[:300]))
    return ok("exit=%d, msg ok (actual=%d limit=%d)" % (rc, ROM_SIZE + 1, ROM_SIZE))


@check("oversize_ram_image", "raw-bin RAM image > 16 MiB rejected with actual size")
def c_oversize_ram_image():
    rom = write_tmp("tramp.bin", build_trampoline())
    ker = words_to_bytes(code_exit(0))
    ker += words_to_bytes([swym()]) * ((RAM_SIZE + 4 - len(ker)) // 4)
    ker = ker[:RAM_SIZE + 1]
    assert len(ker) == RAM_SIZE + 1, len(ker)
    kp = write_tmp("flat_oversize.bin", ker)
    rc, err = run_qemu(bios=rom, kernel=kp)
    if rc == 0:
        return bad("exit=0 (expected non-zero)")
    if not msg_has(err, str(RAM_SIZE + 1), str(RAM_SIZE)):
        return bad("exit=%d but stderr lacks actual/limit size: %r" % (rc, err[:300]))
    return ok("exit=%d, msg ok (actual=%d limit=%d)" % (rc, RAM_SIZE + 1, RAM_SIZE))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_checks(only=None):
    all_ok = True
    selected = [(n, d, f) for (n, d, f) in CHECKS if only is None or n == only]
    if not selected:
        print("[FAIL] no check named %r" % only)
        return False
    for name, desc, fn in selected:
        passed, detail = fn()
        tag = "PASS" if passed else "FAIL"
        print("[%s] %-24s expected: %s -> %s" % (tag, name, desc, detail))
        if not passed:
            all_ok = False
    return all_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="run a single check by name")
    ap.add_argument("--list", action="store_true", help="list check names")
    args = ap.parse_args()

    if args.list:
        for n, d, _ in CHECKS:
            print(n, "-", d)
        return 0

    if not os.path.isfile(QEMU):
        print("[FAIL] QEMU binary not found: %s" % QEMU)
        return 2

    okall = run_checks(args.only)
    print("RESULT: %s" % ("PASS" if okall else "FAIL"))
    return 0 if okall else 1


if __name__ == "__main__":
    sys.exit(main())
