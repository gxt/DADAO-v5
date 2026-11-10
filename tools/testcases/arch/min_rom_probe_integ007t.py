#!/usr/bin/env python3
"""min_rom_probe_integ007t.py -- QEMU probe for the Tiny hmon save-and-jump handler.

Oracle for the user ruling of 2026-11-11 (algorithm:
``.tao/knowledge/refs/m12-006-cycle-design.md`` §11):

  * hmon SRAM layout: code at 0x00 (no jump); data at 0xD8 saved rd63 /
    0xE0 cause_id / 0xE8 cause_ip / 0xF0 cause_info / 0xF8 return address;
    the image segment carries only the code, so data keeps its SRAM value;
  * the handler only saves the three cause registers, copies the framework's
    return address from 0x28 into ``excp_cause_ip``, restores rd63 and escapes;
  * the framework (= the application ELF) decides where to resume: it writes
    address A to 0x28 and the fault must resume at A, then B at B;
  * no magic check, no IALIGN rewrite, no ``+4`` policy, no park loop.

The probe builds the 64 KiB BootROM from the current sources with the shared
builder, links ``tests/arch/hmon/tiny_hmon_min.S`` as an SRAM-only application
at the fixed entry, runs QEMU ``dadao-tiny`` and compares the guest-exported
observation table against spec-derived values (one-hot cause ids from
``spec/DADAO-12 §5.2``, fault IPs from ELF symbols, and the instruction word
for ILLI/UNDI).

Usage:
  python3 tools/testcases/arch/min_rom_probe_integ007t.py [--qemu BIN]
      [--toolchain-bin DIR] [--work-dir DIR] [--timeout SEC]

Exit codes: 0 all checks pass; 1 any check fails; 2 missing build input.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import struct
import subprocess
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases", "lib"))
import machine_profile  # noqa: E402
import paths  # noqa: E402

TINY_FW = os.path.join(REPO_ROOT, "tests", "shared", "bootrom", "tiny")
APP_SRC = os.path.join(REPO_ROOT, "tests", "arch", "hmon", "tiny_hmon_min.S")
APP_LDS = os.path.join(REPO_ROOT, "tests", "shared", "linker",
                       "dadao-tiny-app.lds")
SHARED_ASM = os.path.join(REPO_ROOT, "tests", "shared", "asm")
BUILDER = os.path.join(REPO_ROOT, "tools", "testcases", "arch",
                       "build_tiny_bootrom.py")

# spec/DADAO-12 §5.2(二): excp_cause_id is one-hot over the cause bit index.
CAUSE_CFXTRAP = 1 << 0
CAUSE_CFXMEM = 1 << 1
CAUSE_ILLI = 1 << 8
CAUSE_UNDI = 1 << 9
CAUSE_MALIGN = 1 << 12
CAUSE_IALIGN = 1 << 13
# `trap cfx_hmon, boot_magic` / `trap cfx7, 0` instruction words
# (ciii: (0x7F<<24)|(cfxha<<18)|immu18; contracts/opcodes.yaml).
TRAP_HMON_WORD = (0x7F << 24) | (3 << 18) | 0x30001
TRAP_CFX7_WORD = (0x7F << 24) | (7 << 18)
# Reserved instruction word used by the UNDI case (same vector as the arch case).
UNDI_WORD = 0x08040001
# hmon layout (m13-integ-007, second revision): code at 0x00, data at 0xD8.
HMON_DATA_BASE = 0xD8
HMON_CODE_MIN = 0x2C
# Words whose encoding carries a data-slot offset (st.o rd63,[rb0,0xD8],
# ld.o rd63,[rb0,0xDC], ld.o rd63,[rb0,0xB4]).
HMON_LAYOUT_WORDS = {
    0x00: 0x21FC00D8,
    0x08: 0x21FC00D8,
    0x10: 0x21FC00D8,
    0x18: 0x21FC00D8,
    0x1C: 0x20FC00DC,
    0x24: 0x20FC00B4,
}
PASS_EXIT = 0x21
# spec/Machine-v5 §1.1 / DADAO-13 §1: hmon SRAM base == initial exception
# vector.  power must not rewrite it (m13-integ-007 second revision).
HMON_BASE = 0x0FFF_0000_0000

FAILS = 0
CHECKS = 0


def report(ok: bool, name: str, expected, actual) -> None:
    global FAILS, CHECKS
    CHECKS += 1
    if ok:
        print(f"  [PASS] {name}: expected={expected} actual={actual}")
    else:
        FAILS += 1
        print(f"  [FAIL] {name}: expected={expected} actual={actual}")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def need(path: str, what: str) -> str:
    if not os.path.isfile(path):
        print(f"integ007t: ERROR: {what} not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    return path


def load_builder():
    spec = importlib.util.spec_from_file_location("build_tiny_bootrom", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def assemble(tc, src, obj, includes):
    cmd = [os.path.join(tc, "llvm-mc"), "--triple=dadao-unknown-elf",
           "-filetype=obj"]
    for inc in includes:
        cmd += ["-I", inc]
    cmd += [src, "-o", obj]
    r = run(cmd)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)


def link(tc, lds, objs, out):
    cmd = [os.path.join(tc, "ld.lld"), "-L", os.path.dirname(lds),
           "-T", lds] + objs + ["-o", out]
    r = run(cmd)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)


def symbols(tc, elf):
    r = run([os.path.join(tc, "llvm-nm"), elf])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            try:
                out[parts[2]] = int(parts[0], 16)
            except ValueError:
                continue
    return out


def build_firmware(bld, tc, work):
    power_elf = os.path.join(work, "power.elf")
    hmon_elf = os.path.join(work, "hmon.elf")
    assemble(tc, os.path.join(TINY_FW, "power.S"), os.path.join(work, "power.o"),
             [REPO_ROOT])
    link(tc, os.path.join(TINY_FW, "power.lds"),
         [os.path.join(work, "power.o")], power_elf)
    assemble(tc, os.path.join(TINY_FW, "hmon.S"), os.path.join(work, "hmon.o"),
             [REPO_ROOT])
    link(tc, os.path.join(TINY_FW, "hmon.lds"),
         [os.path.join(work, "hmon.o")], hmon_elf)

    out_dir = os.path.join(work, "img")
    args = argparse.Namespace(out_dir=out_dir, power_elf=power_elf,
                              hmon_elf=hmon_elf,
                              llvm_objcopy=os.path.join(tc, "llvm-objcopy"),
                              llvm_nm=os.path.join(tc, "llvm-nm"))
    try:
        path, image, _ranges, _plen, hlen = bld.build(
            args, bld.HMON_SEG_MAX, bld.DEFAULT_BOOT_MAGIC,
            bld.DEFAULT_HMON_FLAGS, "bootrom_tiny.bin")
        bld.verify_image(image, bld.DEFAULT_BOOT_MAGIC, bld.DEFAULT_HMON_FLAGS)
    except bld.BuildError as exc:
        print(f"integ007t: ERROR: BootROM build failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
    return path, image, hlen, power_elf


def build_app(tc, work):
    obj = os.path.join(work, "app.o")
    elf = os.path.join(work, "app.elf")
    assemble(tc, APP_SRC, obj, [SHARED_ASM])
    link(tc, APP_LDS, [obj], elf)
    return elf


def layout_checks(bld, image, hlen):
    report(len(image) == bld.BOOTROM_SIZE, "BootROM size", bld.BOOTROM_SIZE,
           len(image))
    magic = struct.unpack_from(">I", image, bld.TABLE_OFF)[0]
    version, count = struct.unpack_from(">HH", image, bld.TABLE_OFF + 4)
    report((magic, version, count) == (bld.MAGIC, bld.VERSION, 1),
           "image table header", (hex(bld.MAGIC), 1, 1),
           (hex(magic), version, count))
    typ, _flags, off, size, _resv = struct.unpack_from(
        ">IIQQQ", image, bld.TABLE_OFF + bld.TABLE_HDR)
    report((typ, off, size) == (1, bld.HMON_SEG_OFF, hlen),
           "hmon table entry", (1, hex(bld.HMON_SEG_OFF), hlen),
           (typ, hex(off), size))
    report(size % 8 == 0 and 0 < size <= bld.HMON_SEG_MAX,
           "hmon segment size", f"8-aligned, <= {bld.HMON_SEG_MAX}", size)

    hmon = image[bld.HMON_SEG_OFF:bld.HMON_SEG_OFF + size]
    report(len(hmon) >= HMON_CODE_MIN, "hmon code present",
           f">= {HMON_CODE_MIN} B", f"{len(hmon)} B")
    report(len(hmon) <= HMON_DATA_BASE, "hmon code stays below data base",
           f"<= {HMON_DATA_BASE} B", f"{len(hmon)} B")
    for off, want in HMON_LAYOUT_WORDS.items():
        got = struct.unpack_from(">I", hmon, off)[0]
        report(got == want, f"hmon[{off:#04x}] layout word", hex(want), hex(got))
    report(size <= HMON_DATA_BASE, "power copies only the code region",
           f"table size <= {HMON_DATA_BASE}", size)


def read_records(path, count):
    data = open(path, "rb").read()
    recs = []
    for i in range(count):
        if (i + 1) * 64 > len(data):
            break
        recs.append(tuple(int.from_bytes(data[i * 64 + j:i * 64 + j + 8], "big")
                          for j in range(0, 64, 8)))
    return recs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--qemu", default=str(paths.host_toolchain_bin()
                                          / "qemu-system-dadao"))
    ap.add_argument("--toolchain-bin", default=str(paths.host_toolchain_bin()))
    ap.add_argument("--work-dir", default=str(paths.test_artifacts_dir()
                                              / "arch" / "probes" / "integ007t"))
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    qemu = os.path.abspath(args.qemu)
    need(qemu, "qemu-system-dadao")
    tc = os.path.abspath(args.toolchain_bin)
    for tool in ("llvm-mc", "ld.lld", "llvm-objcopy", "llvm-nm"):
        need(os.path.join(tc, tool), tool)
    need(APP_SRC, "application source")
    need(APP_LDS, "application linker script")

    work = args.work_dir
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    run_dir = os.path.join(work, "run")
    os.makedirs(run_dir)

    bld = load_builder()
    prof = machine_profile.load("tiny")
    image_path, image, hlen, power_elf = build_firmware(bld, tc, work)
    app_elf = build_app(tc, work)
    syms = symbols(tc, app_elf)
    psyms = symbols(tc, power_elf)
    for name in ("f_mem", "f_illi", "f_undi", "f_malign", "f_ialign",
                 "land_mem", "land_illi", "land_undi", "land_malign",
                 "land_ialign", "boot_magic_trap"):
        if name in syms:
            continue
        if name in psyms:
            syms[name] = psyms[name]
            continue
        print(f"integ007t: ERROR: symbol {name} not found", file=sys.stderr)
        return 2

    print("integ007t: layout")
    layout_checks(bld, image, hlen)

    print("integ007t: run")
    r = run([qemu, "-machine",
             "dadao-tiny,bootrom-image=" + os.path.abspath(image_path),
             "-kernel", os.path.abspath(app_elf), "-semihosting-config",
             "enable=on,target=native", "-display", "none", "-nographic"],
            cwd=run_dir, timeout=args.timeout)
    (open(os.path.join(work, "qemu.stdout"), "w")
     .write(r.stdout))
    (open(os.path.join(work, "qemu.stderr"), "w")
     .write(r.stderr))
    report(r.returncode == PASS_EXIT, "guest exit code", hex(PASS_EXIT),
           hex(r.returncode & 0xFF))
    report("hmon-min-ok" in r.stderr, "semihosting console", "hmon-min-ok",
           "found" if "hmon-min-ok" in r.stderr else "missing")

    result_path = os.path.join(run_dir, "hmon_min_results.bin")
    if not os.path.isfile(result_path):
        report(False, "observation table exported", "hmon_min_results.bin",
               "missing")
        print(f"\ninteg007t: FAIL ({FAILS}/{CHECKS})")
        return 1
    recs = read_records(result_path, 6)
    report(len(recs) == 6, "record count", 6, len(recs))
    if len(recs) != 6:
        print(f"\ninteg007t: FAIL ({FAILS}/{CHECKS})")
        return 1

    # ---- record 0: power -> hmon hand-over (CFXTRAP) --------------------
    handover = recs[0]
    report(handover[0] == 0, "record 0 id", 0, handover[0])
    report(handover[1] == CAUSE_CFXTRAP, "handover cause_id",
           hex(CAUSE_CFXTRAP), hex(handover[1]))
    report(handover[2] == syms["boot_magic_trap"], "handover cause_ip",
           hex(syms["boot_magic_trap"]), hex(handover[2]))
    report(handover[3] == TRAP_HMON_WORD, "handover cause_info",
           hex(TRAP_HMON_WORD), hex(handover[3]))
    report(handover[4] == syms["boot_magic_trap"] + 4,
           "power default return address", hex(syms["boot_magic_trap"] + 4),
           hex(handover[4]))
    report(handover[6] == HMON_BASE, "power leaves hmon vector untouched",
           hex(HMON_BASE), hex(handover[6]))

    # ---- five synchronous fault classes ----------------------------------
    cases = [
        (1, CAUSE_CFXMEM, "f_mem", "land_mem", 0x10_0000_0000,
         0x1111222233334444),
        (2, CAUSE_ILLI, "f_illi", "land_illi", TRAP_CFX7_WORD,
         0x2222333344445555),
        (3, CAUSE_UNDI, "f_undi", "land_undi", UNDI_WORD,
         0x3333444455556666),
        (4, CAUSE_MALIGN, "f_malign", "land_malign", prof.ram_base + 1,
         0x4444555566667777),
        (5, CAUSE_IALIGN, "f_ialign", "land_ialign",
         prof.entry + 0x1D01, 0x5555666677778888),
    ]
    for idx, cause, fault, land, info, sentinel in cases:
        rec = recs[idx]
        report(rec[0] == idx, f"record {idx} id", idx, rec[0])
        report(rec[1] == cause, f"record {idx} cause_id", hex(cause),
               hex(rec[1]))
        # IALIGN is the one cause whose cause_ip is the illegal target itself
        # (spec/DADAO-12 §5.0: IP stays at the illegal address); every other
        # cause records the faulting instruction address.
        ip = info if cause == CAUSE_IALIGN else syms[fault]
        report(rec[2] == ip, f"record {idx} cause_ip", hex(ip), hex(rec[2]))
        report(rec[3] == info, f"record {idx} cause_info", hex(info),
               hex(rec[3]))
        report(rec[4] == sentinel, f"record {idx} rd63 after", hex(sentinel),
               hex(rec[4]))
        report(rec[5] == sentinel, f"record {idx} saved rd63", hex(sentinel),
               hex(rec[5]))
        report(rec[6] == syms[land], f"record {idx} return slot",
               hex(syms[land]), hex(rec[6]))
        report(rec[7] == 0, f"record {idx} no +4 poison", 0, hex(rec[7]))

    # ---- the framework's A/B targets are not fault+4 ---------------------
    report(syms["land_mem"] != syms["f_mem"] + 4,
           "A target != fault+4", hex(syms["f_mem"] + 4), hex(syms["land_mem"]))
    report(syms["land_illi"] != syms["f_illi"] + 4,
           "B target != fault+4", hex(syms["f_illi"] + 4),
           hex(syms["land_illi"]))

    if FAILS:
        print(f"\ninteg007t: FAIL ({FAILS}/{CHECKS})")
        return 1
    print(f"\ninteg007t: PASS ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired:
        print("\ninteg007t: FAIL (QEMU timeout)", file=sys.stderr)
        sys.exit(1)
