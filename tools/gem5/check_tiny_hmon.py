#!/usr/bin/env python3
"""check_tiny_hmon — Machine-v5-Tiny cfx_power + cfx3 hmon acceptance runner.

Builds the §6.2 two-piece load (fixed 64 KiB BootROM image + SRAM-only app ELF)
from `tests/arch/hmon/` and `tests/shared/bootrom/tiny/`, runs the application
on the gem5 Tiny FS profile, and compares the guest-exported result table
against the independent oracle in `tests/arch/hmon/expected.yaml`
(spec-derived cause ids, ELF-symbol IPs, and profile-derived cg7 offsets).

The BootROM digest is *not* hardcoded here: it is cross-checked against
`expected.yaml:shared_bootrom_md5` and the chipyard checked-in
`bootrom.tiny.hex` payload, so a firmware change only needs the oracle/builder
updated (one source of truth, no second copy to drift).

Usage:
    python3 tools/gem5/check_tiny_hmon.py [--gem5 BIN] [--config fs.py]
        [--work-dir DIR] [--max-ticks N] [--toolchain-bin DIR]

Exit codes: 0 all checks pass; 1 any check fails; 2 missing build input.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / "tests" / "arch" / "hmon"
SHARED_ASM = ROOT / "tests" / "shared" / "asm"
TINY_FW = ROOT / "tests" / "shared" / "bootrom" / "tiny"
BUILDER = ROOT / "tools" / "testcases" / "arch" / "build_tiny_bootrom.py"
CHIPYARD_HEX = (ROOT / "components" / "chipyard" / "patches" / "generators" /
                "dadao-wuming" / "src" / "main" / "resources" / "dadao" /
                "bootrom" / "bootrom.tiny.hex.patch")
DEFAULT_GEM5 = ROOT / ".work" / "source" / "gem5" / "build" / "DADAO" / "gem5.opt"
DEFAULT_CONFIG = ROOT / ".work" / "source" / "gem5" / "configs" / "dadao" / "fs.py"
PASS_EXIT = 0x21

sys.path.insert(0, str(ROOT / "tools" / "infra"))
import paths  # noqa: E402

FAILS = 0
CHECKS = 0


def load_builder():
    spec = importlib.util.spec_from_file_location("build_tiny_bootrom", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def report(ok: bool, name: str, expected, actual) -> None:
    global FAILS, CHECKS
    CHECKS += 1
    if ok:
        print(f"  [PASS] {name}: expected={expected} actual={actual}")
    else:
        FAILS += 1
        print(f"  [FAIL] {name}: expected={expected} actual={actual}")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def need_tool(tc: Path, name: str) -> Path:
    tool = tc / name
    if not tool.is_file():
        print(f"check_tiny_hmon: ERROR: {name} not found under {tc}",
              file=sys.stderr)
        raise SystemExit(2)
    return tool


def assemble(tc: Path, src: Path, obj: Path) -> None:
    r = run([str(tc / "llvm-mc"), "--triple=dadao-unknown-elf",
             "-filetype=obj", "-I", str(CASE_DIR), "-I", str(SHARED_ASM),
             str(src), "-o", str(obj)])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)


def link(tc: Path, lds: Path, obj: Path, elf: Path) -> None:
    r = run([str(tc / "ld.lld"), "-T", str(lds), str(obj), "-o", str(elf)])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)


def build_elf(tc: Path, src: Path, lds: Path, work: Path, stem: str) -> Path:
    obj = work / f"{stem}.o"
    elf = work / f"{stem}.elf"
    assemble(tc, src, obj)
    link(tc, lds, obj, elf)
    return elf


def flatten(tc: Path, elf: Path, out: Path) -> bytes:
    r = run([str(tc / "llvm-objcopy"), "-O", "binary", str(elf), str(out)])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)
    return out.read_bytes()


def symbols(tc: Path, *elfs: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for elf in elfs:
        r = run([str(tc / "llvm-nm"), str(elf)])
        if r.returncode != 0:
            print(r.stdout + r.stderr, file=sys.stderr)
            raise SystemExit(2)
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) != 3:
                continue
            value, _kind, name = parts
            try:
                out.setdefault(name, int(value, 16))
            except ValueError:
                continue
    return out


def evaluate(expr, ns: dict) -> int:
    if isinstance(expr, int):
        return expr
    return int(eval(str(expr), {"__builtins__": {}}, ns))


def read_records(path: Path) -> list[tuple[int, int, int, int]]:
    data = path.read_bytes()
    records = []
    for off in range(0, len(data) - 31, 32):
        rec = tuple(int.from_bytes(data[off + i:off + i + 8], "big")
                    for i in (0, 8, 16, 24))
        if rec[0] == 0:
            break
        records.append(rec)
    return records


def build_image(bld, work: Path, tc: Path, power: Path, hmon: Path,
                name: str) -> tuple[bytes, dict]:
    out_dir = work / f"img-{name}"
    args = argparse.Namespace(out_dir=str(out_dir),
                              power_elf=str(power), hmon_elf=str(hmon),
                              llvm_objcopy=str(tc / "llvm-objcopy"),
                              llvm_nm=str(tc / "llvm-nm"))
    try:
        path, image, _ranges, power_len, hmon_len = bld.build(
            args, bld.HMON_SEG_MAX, bld.DEFAULT_BOOT_MAGIC,
            bld.DEFAULT_HMON_FLAGS, f"bootrom_{name}.bin")
        bld.verify_image(image, bld.DEFAULT_BOOT_MAGIC, bld.DEFAULT_HMON_FLAGS)
    except bld.BuildError as exc:
        print(f"check_tiny_hmon: ERROR: {name} BootROM build failed: {exc}",
              file=sys.stderr)
        raise SystemExit(2)
    return image, {"path": Path(path), "power_len": power_len,
                   "hmon_len": hmon_len}


def chipyard_image(bld, work: Path) -> bytes:
    """Decode the checked-in chipyard sparse hex (inside its patch file)."""
    text = []
    for raw in CHIPYARD_HEX.read_text().splitlines():
        if raw.startswith("+++"):
            continue
        if raw.startswith("+"):
            text.append(raw[1:])
    hex_path = work / "chipyard_bootrom.tiny.hex"
    hex_path.write_text("\n".join(text) + "\n")
    try:
        return bld.hex_to_bytes(str(hex_path), bld.BOOTROM_SIZE)
    except bld.BuildError as exc:
        print(f"check_tiny_hmon: ERROR: chipyard hex: {exc}", file=sys.stderr)
        raise SystemExit(2)


def elf_entry_and_loads(path: Path) -> tuple[int, list[dict]]:
    data = path.read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 2:
        print(f"check_tiny_hmon: ERROR: {path} is not ELF64 big-endian",
              file=sys.stderr)
        raise SystemExit(2)
    entry = struct.unpack_from(">Q", data, 24)[0]
    phoff = struct.unpack_from(">Q", data, 32)[0]
    phentsize, phnum = struct.unpack_from(">HH", data, 54)
    loads = []
    for i in range(phnum):
        off = phoff + i * phentsize
        ptype = struct.unpack_from(">I", data, off)[0]
        if ptype != 1:
            continue
        vaddr, paddr = struct.unpack_from(">QQ", data, off + 16)
        memsz = struct.unpack_from(">Q", data, off + 40)[0]
        loads.append({"vaddr": vaddr, "paddr": paddr, "memsz": memsz})
    return entry, loads


def patch_elf(src: Path, dst: Path, *, entry=None, paddr=None) -> None:
    """Copy `src` and rewrite e_entry / the first PT_LOAD's vaddr+paddr."""
    data = bytearray(src.read_bytes())
    if entry is not None:
        struct.pack_into(">Q", data, 24, entry)
    if paddr is not None:
        phoff = struct.unpack_from(">Q", data, 32)[0]
        phentsize, phnum = struct.unpack_from(">HH", data, 54)
        for i in range(phnum):
            off = phoff + i * phentsize
            if struct.unpack_from(">I", data, off)[0] != 1:
                continue
            struct.pack_into(">Q", data, off + 16, paddr)
            struct.pack_into(">Q", data, off + 24, paddr)
            break
        else:
            raise SystemExit("check_tiny_hmon: internal: no PT_LOAD to patch")
    dst.write_bytes(data)


def run_gem5(gem5: Path, config: Path, work: Path, tag: str, kernel: Path,
             bootrom: Path | None, max_ticks: int,
             dumps: list[str] | None = None) -> subprocess.CompletedProcess:
    run_dir = work / f"run-{tag}"
    out_dir = work / f"out-{tag}"
    run_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(gem5.resolve()), "--outdir", str(out_dir.resolve()),
           str(config.resolve()), "--profile", "tiny",
           "--kernel", str(kernel.resolve())]
    if bootrom is not None:
        cmd += ["--bootrom", str(bootrom.resolve())]
    cmd += ["--max-ticks", str(max_ticks)]
    for dump in dumps or []:
        cmd += ["--dump-mem", dump]
    proc = run(cmd, cwd=run_dir)
    (run_dir / "gem5.stdout").write_text(proc.stdout)
    (run_dir / "gem5.stderr").write_text(proc.stderr)
    return proc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gem5", default=str(DEFAULT_GEM5))
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--max-ticks", type=int, default=200_000_000)
    ap.add_argument("--toolchain-bin", default=str(paths.host_toolchain_bin()))
    args = ap.parse_args()

    gem5 = Path(args.gem5)
    config = Path(args.config)
    if not gem5.is_file():
        print(f"check_tiny_hmon: ERROR: gem5 not found: {gem5} "
              "(run 'make build-gem5')", file=sys.stderr)
        return 2
    if not config.is_file():
        print(f"check_tiny_hmon: ERROR: fs.py not found: {config}",
              file=sys.stderr)
        return 2
    tc = Path(args.toolchain_bin)
    need_tool(tc, "llvm-mc")
    need_tool(tc, "ld.lld")
    need_tool(tc, "llvm-nm")
    need_tool(tc, "llvm-objcopy")

    work = (Path(args.work_dir) if args.work_dir
            else ROOT / ".dadao" / "tests" / "tiny-hmon")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    bld = load_builder()
    oracle = yaml.safe_load((CASE_DIR / "expected.yaml").read_text())
    prof = oracle["profile"]

    # ---- build inputs: shared firmware, test dispatch firmware, application --
    power_elf = build_elf(tc, TINY_FW / "power.S", TINY_FW / "power.lds",
                          work, "power")
    shared_hmon = build_elf(tc, TINY_FW / "hmon.S", TINY_FW / "hmon.lds",
                            work, "shared_hmon")
    test_hmon = build_elf(tc, CASE_DIR / "tiny_hmon_handler.S",
                          CASE_DIR / "tiny_hmon_handler.lds", work,
                          "tiny_hmon_handler")
    app_elf = build_elf(tc, CASE_DIR / "tiny_hmon.S", CASE_DIR / "tiny_hmon.lds",
                        work, "tiny_hmon")
    syms = symbols(tc, app_elf, power_elf)
    ns: dict[str, object] = dict(prof)
    ns.update(syms)

    shared_img, shared_meta = build_image(bld, work, tc, power_elf, shared_hmon,
                                          "shared")
    test_img, test_meta = build_image(bld, work, tc, power_elf, test_hmon, "test")

    # ---- shared firmware identity: builder == chipyard hex == oracle --------
    report(len(shared_img) == bld.BOOTROM_SIZE, "shared BootROM size",
           bld.BOOTROM_SIZE, len(shared_img))
    shared_md5 = hashlib.md5(shared_img).hexdigest()
    report(shared_md5 == oracle["shared_bootrom_md5"], "shared BootROM md5",
           oracle["shared_bootrom_md5"], shared_md5)
    chip = chipyard_image(bld, work)
    report(chip == shared_img, "shared BootROM == chipyard checked-in hex",
           "byte-identical", "identical" if chip == shared_img
           else f"differs (chipyard md5 {hashlib.md5(chip).hexdigest()})")
    print(f"  [info] shared hmon segment = {shared_meta['hmon_len']} B, "
          f"power segment = {shared_meta['power_len']} B")

    # ---- image layout (spec/Machine-v5 §6.1/§6.2) ---------------------------
    for tag, img, meta in (("shared", shared_img, shared_meta),
                           ("test", test_img, test_meta)):
        report(len(img) == 65536, f"{tag} image size", 65536, len(img))
        magic = struct.unpack_from(">I", img, bld.TABLE_OFF)[0]
        version, count = struct.unpack_from(">HH", img, bld.TABLE_OFF + 4)
        boot_magic = struct.unpack_from(">I", img, bld.TABLE_OFF + 8)[0]
        report((magic, version, count, boot_magic) ==
               (bld.MAGIC, bld.VERSION, 1, 0x30001),
               f"{tag} table header", (hex(bld.MAGIC), 1, 1, hex(0x30001)),
               (hex(magic), version, count, hex(boot_magic)))
        typ, flags, off, size, resv = struct.unpack_from(
            ">IIQQQ", img, bld.TABLE_OFF + bld.TABLE_HDR)
        report((typ, flags, off, resv) ==
               (1, bld.DEFAULT_HMON_FLAGS, bld.HMON_SEG_OFF, 0),
               f"{tag} hmon entry", (1, hex(bld.DEFAULT_HMON_FLAGS),
                                     hex(bld.HMON_SEG_OFF), 0),
               (typ, hex(flags), hex(off), resv))
        report(size == meta["hmon_len"] and size % 8 == 0 and
               0 < size <= bld.HMON_SEG_MAX, f"{tag} hmon segment size",
               f"{meta['hmon_len']} B (8-aligned, <= 8 KiB)", f"{size} B")
        report(not any(img[bld.RESERVED_OFF:bld.TABLE_OFF]),
               f"{tag} reserved 40 KiB is zero", "all zero",
               "all zero" if not any(img[bld.RESERVED_OFF:bld.TABLE_OFF])
               else "non-zero")

    # ---- application ELF obeys the two-piece load contract ------------------
    entry, loads = elf_entry_and_loads(app_elf)
    report(entry == prof["entry"], "app ELF e_entry", hex(prof["entry"]),
           hex(entry))
    h_entry, _ = elf_entry_and_loads(test_hmon)
    report(h_entry == prof["hmon_base"], "handler ELF entry",
           hex(prof["hmon_base"]), hex(h_entry))
    report(len(loads) == 1, "app ELF PT_LOAD count", 1, len(loads))
    for seg in loads:
        inside = (prof["sram_base"] <= seg["paddr"] and
                  seg["paddr"] + seg["memsz"] <=
                  prof["sram_base"] + prof["sram_size"])
        report(inside, "app ELF PT_LOAD inside SRAM",
               f"[{hex(prof['sram_base'])}, "
               f"{hex(prof['sram_base'] + prof['sram_size'])})",
               f"[{hex(seg['paddr'])}, {hex(seg['paddr'] + seg['memsz'])})")

    # ---- run: power -> hmon hand-off -> application -------------------------
    dump_file = work / "hmon_sram.bin"
    r = run_gem5(gem5, config, work, "hmon", app_elf, test_meta["path"],
                 args.max_ticks,
                 [f"{hex(prof['hmon_base'])}:{prof['hmon_size']}:"
                  f"{dump_file}"])
    (work / "gem5.stdout").write_text(r.stdout)
    (work / "gem5.stderr").write_text(r.stderr)
    report(r.returncode == PASS_EXIT, "gem5 guest exit", hex(PASS_EXIT),
           hex(r.returncode & 0xFF))
    report("hmon-ok" in r.stdout, "semihosting with trap cfx63",
           "console contains hmon-ok",
           "found" if "hmon-ok" in r.stdout else "missing")
    report("GEM5_EXIT_CAUSE=semi:ADP_Stopped_ApplicationExit" in r.stderr,
           "semihosting stop cause", "semi:ADP_Stopped_ApplicationExit",
           next((ln for ln in r.stderr.splitlines()
                 if ln.startswith("GEM5_EXIT_CAUSE=")), "missing"))

    # ---- the power stub installed exactly the firmware's hmon segment -------
    if dump_file.is_file():
        sram = dump_file.read_bytes()
        hmon_len = test_meta["hmon_len"]
        segment = test_img[bld.HMON_SEG_OFF:bld.HMON_SEG_OFF + hmon_len]
        report(sram[:hmon_len] == segment, "hmon SRAM == firmware segment",
               f"{hmon_len} B byte-identical",
               "identical" if sram[:hmon_len] == segment else "differs")
        report(not any(sram[hmon_len:]), "hmon SRAM tail is zero",
               f"{len(sram) - hmon_len} B zero",
               "all zero" if not any(sram[hmon_len:]) else "non-zero")
        report(len(sram) == prof["hmon_size"], "hmon SRAM dump size",
               prof["hmon_size"], len(sram))
    else:
        report(False, "hmon SRAM dump", "dump file", "missing")

    # ---- result table vs the independent oracle ----------------------------
    result_path = work / "run-hmon" / "hmon_results.bin"
    if not result_path.is_file():
        report(False, "result table exported", "hmon_results.bin", "missing")
        print(f"\ncheck_tiny_hmon: FAIL ({FAILS}/{CHECKS})")
        return 1
    actual = read_records(result_path)
    expected = oracle["records"]
    report(len(actual) == len(expected), "record count", len(expected),
           len(actual))
    for idx in range(min(len(actual), len(expected))):
        want = expected[idx]
        got = actual[idx]
        if want["kind"] == "check":
            exp = evaluate(want["expect"], ns)
            report(got[0] == want["id"], f"record {idx} check id",
                   want["id"], got[0])
            report(got[1] == exp, f"record {idx} check {want['id']} value",
                   hex(exp), hex(got[1]))
            report(got[2] == exp, f"record {idx} check {want['id']} guest copy",
                   hex(exp), hex(got[2]))
            report(got[3] == 0, f"record {idx} check {want['id']} reserved",
                   0, got[3])
        else:
            ip = evaluate(want["ip"], ns)
            info = evaluate(want["info"], ns)
            hpc = evaluate(want["handler_pc"], ns)
            cid = evaluate(want["cause_id"], ns)
            report(got[0] == cid, f"record {idx} cause {want['cause']}",
                   hex(cid), hex(got[0]))
            report(got[1] == ip, f"record {idx} cause_ip", hex(ip), hex(got[1]))
            report(got[2] == info, f"record {idx} cause_info", hex(info),
                   hex(got[2]))
            report(got[3] == hpc, f"record {idx} handler PC", hex(hpc),
                   hex(got[3]))

    # ---- loader negatives: each must fail loudly, never silently -----------
    bad_dir = work / "bad"
    bad_dir.mkdir()
    cases = []
    r = run_gem5(gem5, config, work, "no-bootrom", app_elf, None, args.max_ticks)
    cases.append(("missing --bootrom", r, "requires --bootrom"))
    short = work / "bootrom_short.bin"
    short.write_bytes(test_img[:65535])
    r = run_gem5(gem5, config, work, "bootrom-short", app_elf, short,
                 args.max_ticks)
    cases.append(("BootROM not 64 KiB", r, "exactly 65536 bytes"))
    for name, base, needle in (
            ("BootROM", prof["bootrom_base"], "targets the BootROM"),
            ("hmon SRAM", prof["hmon_base"], "targets the hmon SRAM")):
        elf = bad_dir / f"ptload_{name.split()[0].lower()}.elf"
        patch_elf(app_elf, elf, paddr=base)
        r = run_gem5(gem5, config, work, f"ptload-{name.split()[0].lower()}",
                     elf, test_meta["path"], args.max_ticks)
        cases.append((f"PT_LOAD into {name}", r, needle))
    elf = bad_dir / "entry_not_fixed.elf"
    patch_elf(app_elf, elf, entry=prof["entry"] + 0x40)
    r = run_gem5(gem5, config, work, "entry-not-fixed", elf,
                 test_meta["path"], args.max_ticks)
    cases.append((f"e_entry != {hex(prof['entry'])}", r,
                  f"fixed at {hex(prof['entry'])}"))
    for name, proc, needle in cases:
        combined = proc.stdout + proc.stderr
        report(proc.returncode != 0, f"negative: {name} rc", "!= 0",
               proc.returncode)
        report(needle in combined, f"negative: {name} message", needle,
               "found" if needle in combined else "missing")

    if FAILS:
        print(f"\ncheck_tiny_hmon: FAIL ({FAILS}/{CHECKS})")
        return 1
    print(f"\ncheck_tiny_hmon: PASS ({CHECKS} checks, "
          f"{len(expected)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
