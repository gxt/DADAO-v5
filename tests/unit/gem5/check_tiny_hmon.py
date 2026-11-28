#!/usr/bin/env python3
"""check_tiny_hmon — Kaiwu-Tiny cfx_power + cfx3 hmon acceptance runner.

Builds the §6.2 two-piece load (fixed 8 KiB BootROM image + SRAM-only app ELF)
from `tests/unit/gem5/tiny_hmon/` and `tests/ee-tiny/`, runs the application
on the gem5 Tiny FS profile, and compares the guest-exported result table
against the independent oracle in `tests/unit/gem5/tiny_hmon/expected.yaml`
(spec-derived cause ids, ELF-symbol IPs, and profile-derived cg7 offsets).

The BootROM is the *shared* firmware (power stub + the minimal save-and-jump
hmon handler of m13-integ-007); the gem5 case carries no dispatch handler of
its own.  Cause records are the four hmon SRAM data slots the application
reads at its landing address (page base 0xC00, page offsets
+0x00/+0x08/+0x10/+0x18) -- except the CFXESC
record, which `spec/DADAO-12 §5.2(一)` delivers to the *current* cfx (cfx63):
that frame is read from cfx63's own cg5 and the monitor's slots are asserted
to be unchanged (`kind: monitor_unchanged`, the reverse assertion).  The
BootROM digest is not hardcoded here: it is cross-checked against
`expected.yaml:shared_bootrom_md5`.

Usage:
    python3 tests/unit/gem5/check_tiny_hmon.py [--gem5 BIN] [--config fs.py]
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

ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = ROOT / "tests" / "unit" / "gem5" / "tiny_hmon"
SHARED_ASM = ROOT / "tests" / "shared" / "asm"
TINY_FW = ROOT / "tests" / "ee-tiny"   # m15-testcases-011
BUILDER = ROOT / "tools" / "testcases" / "arch" / "build_tiny_bootrom.py"
DEFAULT_GEM5 = ROOT / ".work" / "source" / "gem5" / "build" / "DADAO" / "gem5.opt"
DEFAULT_CONFIG = ROOT / ".work" / "source" / "gem5" / "configs" / "dadao" / "fs.py"
PASS_EXIT = 0x21
# Every Tiny geometry constant the case relies on, read back from the gem5
# profile (`fs.py --dump-geometry`) and compared with expected.yaml.
GEOMETRY_KEYS = (
    "bootrom_base", "bootrom_size", "reset_pc",
    "sram_base", "sram_size", "hmon_base", "hmon_size",
    "entry", "image_window", "dump_base", "dump_size",
    "signature_base", "signature_size", "exit_block",
)

sys.path.insert(0, str(ROOT / "tools" / "infra"))
import paths  # noqa: E402
import writer_guard  # noqa: E402

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


def patch_elf(src: Path, dst: Path, *, entry=None, paddr=None,
              mem_size=None) -> None:
    """Copy `src` and rewrite e_entry / the first PT_LOAD's vaddr+paddr+size.

    `mem_size` shrinks p_filesz/p_memsz too: a negative probe that moves a
    segment into the BootROM/hmon SRAM must keep the segment small enough to
    fit *inside* the target region, so the loader's target-specific rejection
    (not the generic "outside the image window") is what fires.
    """
    data = bytearray(src.read_bytes())
    if entry is not None:
        struct.pack_into(">Q", data, 24, entry)
    if paddr is not None or mem_size is not None:
        phoff = struct.unpack_from(">Q", data, 32)[0]
        phentsize, phnum = struct.unpack_from(">HH", data, 54)
        for i in range(phnum):
            off = phoff + i * phentsize
            if struct.unpack_from(">I", data, off)[0] != 1:
                continue
            if paddr is not None:
                struct.pack_into(">Q", data, off + 16, paddr)
                struct.pack_into(">Q", data, off + 24, paddr)
            if mem_size is not None:
                struct.pack_into(">Q", data, off + 32, mem_size)
                struct.pack_into(">Q", data, off + 40, mem_size)
            break
        else:
            raise SystemExit("check_tiny_hmon: internal: no PT_LOAD to patch")
    dst.write_bytes(data)


def dump_geometry(gem5: Path, config: Path, work: Path) -> dict[str, int]:
    """Read the effective Tiny geometry from the gem5 profile itself."""
    out_dir = work / "geometry"
    out_dir.mkdir(parents=True, exist_ok=True)
    r = run([str(gem5.resolve()), "--outdir", str(out_dir.resolve()),
             str(config.resolve()), "--profile", "tiny", "--dump-geometry"])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)
    geo: dict[str, int] = {}
    for line in r.stdout.splitlines():
        if not line.startswith("GEM5_GEOMETRY "):
            continue
        key, _, value = line.split(" ", 1)[1].partition("=")
        geo[key] = int(value, 0)
    return geo


def run_gem5(gem5: Path, config: Path, work: Path, tag: str, kernel: Path,
             bootrom: Path | None, max_ticks: int,
             dumps: list[str] | None = None) -> subprocess.CompletedProcess:
    run_dir = work / f"run-{tag}"
    out_dir = work / f"out-{tag}"
    run_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(gem5.resolve()), "--outdir", str(out_dir.resolve()),
           str(config.resolve()), "--profile", "tiny",
           "--kernel", str(kernel.resolve()), "--semihost", "on"]
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
    writer_guard.add_arguments(ap)
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

    # ISS-373: refuse on an active writer, then hash what we read at both ends.
    guard = writer_guard.start_guard(
        args, [str(gem5), str(config), str(tc / "llvm-mc"),
               str(tc / "ld.lld"), str(tc / "llvm-nm"),
               str(tc / "llvm-objcopy")], label="check_tiny_hmon")

    work = (Path(args.work_dir) if args.work_dir
            else ROOT / ".dadao" / "tests" / "tiny-hmon").resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    bld = load_builder()
    oracle = yaml.safe_load((CASE_DIR / "expected.yaml").read_text())
    prof = oracle["profile"]

    # ---- profile geometry: oracle == the gem5 Tiny profile in force ---------
    geo = dump_geometry(gem5, config, work)
    missing = [k for k in GEOMETRY_KEYS if k not in prof or k not in geo]
    report(not missing, "profile geometry keys present", "none missing",
           ", ".join(missing) if missing else "none")
    for key in GEOMETRY_KEYS:
        if key not in prof or key not in geo:
            continue
        report(geo[key] == prof[key], f"profile geometry {key}",
               hex(prof[key]), hex(geo[key]))

    # ---- build inputs: shared firmware + application ------------------------
    power_elf = build_elf(tc, TINY_FW / "cfx_power_tiny.S", TINY_FW / "cfx_power_tiny.lds",
                          work, "power")
    shared_hmon = build_elf(tc, TINY_FW / "cfx_hmon_tiny.S", TINY_FW / "cfx_hmon_tiny.lds",
                            work, "shared_hmon")
    app_elf = build_elf(tc, CASE_DIR / "tiny_hmon.S", CASE_DIR / "tiny_hmon.lds",
                        work, "tiny_hmon")
    hmon_code = flatten(tc, shared_hmon, work / "shared_hmon.bin")
    syms = symbols(tc, app_elf, power_elf)
    ns: dict[str, object] = dict(prof)
    ns.update(syms)

    shared_img, shared_meta = build_image(bld, work, tc, power_elf, shared_hmon,
                                          "shared")

    # ---- shared firmware identity: builder == oracle -----------------------
    report(len(shared_img) == bld.BOOTROM_SIZE, "shared BootROM size",
           bld.BOOTROM_SIZE, len(shared_img))
    shared_md5 = hashlib.md5(shared_img).hexdigest()
    report(shared_md5 == oracle["shared_bootrom_md5"], "shared BootROM md5",
           oracle["shared_bootrom_md5"], shared_md5)
    print(f"  [info] shared hmon segment = {shared_meta['hmon_len']} B "
          f"(code {len(hmon_code)} B), "
          f"power segment = {shared_meta['power_len']} B")

    # ---- image layout (spec/Kaiwu §6.1/§6.2) ---------------------------
    # Every size/offset below comes from the builder (the single source for
    # the 8 KiB geometry: bootrom size, table at 0x1F00, hmon at 0x800).
    img, meta, tag = shared_img, shared_meta, "shared"
    report(len(img) == bld.BOOTROM_SIZE, f"{tag} image size",
           bld.BOOTROM_SIZE, len(img))
    table_off = bld.TABLE_OFF
    table_fits = table_off + bld.TABLE_SIZE <= len(img)
    report(table_fits, f"{tag} table inside image",
           f"{table_off:#x}+{bld.TABLE_SIZE:#x} <= {len(img):#x}",
           f"{table_off:#x}+{bld.TABLE_SIZE:#x} <= {len(img):#x}"
           if table_fits else "outside")
    if table_fits:
        magic = struct.unpack_from(">I", img, table_off)[0]
        version, count = struct.unpack_from(">HH", img, table_off + 4)
        boot_magic = struct.unpack_from(">I", img, table_off + 8)[0]
        typ, flags, off, size, resv = struct.unpack_from(
            ">IIQQQ", img, table_off + bld.TABLE_HDR)
        hdr_actual = (hex(magic), version, count, hex(boot_magic))
        ent_actual = (typ, hex(flags), hex(off), resv)
    else:
        magic = version = count = boot_magic = None
        typ = flags = off = size = resv = None
        hdr_actual = ent_actual = (None, None, None, None)
    report((magic, version, count, boot_magic) ==
           (bld.MAGIC, bld.VERSION, bld.COUNT, bld.DEFAULT_BOOT_MAGIC),
           f"{tag} table header",
           (hex(bld.MAGIC), bld.VERSION, bld.COUNT,
            hex(bld.DEFAULT_BOOT_MAGIC)),
           hdr_actual)
    report((typ, flags, off, resv) ==
           (1, bld.DEFAULT_HMON_FLAGS, bld.HMON_SEG_OFF, 0),
           f"{tag} hmon entry", (1, hex(bld.DEFAULT_HMON_FLAGS),
                                 hex(bld.HMON_SEG_OFF), 0),
           ent_actual)
    report(size == meta["hmon_len"] and size % 8 == 0 and
           0 < size <= bld.HMON_SEG_MAX, f"{tag} hmon segment size",
           f"{meta['hmon_len']} B (8-aligned, <= {bld.HMON_SEG_MAX:#x})",
           f"{size} B")
    # m19-testcases-005 layout contract: the segment carries only the code
    # (>= bld.HMON_CODE_MIN, 8-aligned by the builder) and stops below the
    # 0xC00 data page, so power never copies over the data slots.
    report(bld.HMON_CODE_MIN <= len(hmon_code) <= bld.HMON_DATA_BASE,
           f"{tag} hmon code length",
           f"[{bld.HMON_CODE_MIN:#x}, {bld.HMON_DATA_BASE:#x}]",
           f"{len(hmon_code):#x} B")
    report(meta["hmon_len"] == (len(hmon_code) + 7) & ~7,
           f"{tag} hmon segment length == 8-aligned code length",
           f"{(len(hmon_code) + 7) & ~7:#x}", f"{meta['hmon_len']:#x}")
    report(meta["hmon_len"] % 8 == 0 and
           meta["hmon_len"] <= bld.HMON_DATA_BASE,
           f"{tag} hmon segment stops below the data base",
           f"8-aligned, <= {bld.HMON_DATA_BASE:#x}",
           f"{meta['hmon_len']} B")
    report(not any(img[bld.RESERVED_OFF:bld.TABLE_OFF]),
           f"{tag} reserved region is zero", "all zero",
           "all zero" if not any(img[bld.RESERVED_OFF:bld.TABLE_OFF])
           else "non-zero")

    # ---- application ELF obeys the two-piece load contract ------------------
    entry, loads = elf_entry_and_loads(app_elf)
    report(entry == prof["entry"], "app ELF e_entry", hex(prof["entry"]),
           hex(entry))
    h_entry, _ = elf_entry_and_loads(shared_hmon)
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
    r = run_gem5(gem5, config, work, "hmon", app_elf, shared_meta["path"],
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

    # ---- the power stub installed exactly the firmware's hmon code ----------
    if dump_file.is_file():
        sram = dump_file.read_bytes()
        hmon_len = shared_meta["hmon_len"]
        segment = shared_img[bld.HMON_SEG_OFF:bld.HMON_SEG_OFF + hmon_len]
        report(len(sram) == prof["hmon_size"], "hmon SRAM dump size",
               prof["hmon_size"], len(sram))
        report(sram[:len(hmon_code)] == hmon_code,
               "hmon SRAM code == firmware code",
               f"{len(hmon_code)} B byte-identical",
               "identical" if sram[:len(hmon_code)] == hmon_code else "differs")
        report(sram[len(hmon_code):hmon_len] == segment[len(hmon_code):],
               "hmon SRAM alignment padding == firmware padding",
               f"{hmon_len - len(hmon_code)} B", "identical"
               if sram[len(hmon_code):hmon_len] == segment[len(hmon_code):]
               else "differs")
        # The data page lives above the segment end (power copies only the
        # table `size` bytes), so it keeps its SRAM value and is written at
        # run time: power writes +0x18, the handler writes +0x00..+0x28.
        report(not any(sram[hmon_len:bld.HMON_DATA_BASE]),
               "hmon SRAM gap below the data page is untouched",
               f"{bld.HMON_DATA_BASE - hmon_len} B zero",
               "all zero" if not any(sram[hmon_len:bld.HMON_DATA_BASE])
               else "non-zero")
        # Page offsets are builder constants; the absolute dump offsets are
        # HMON_DATA_BASE + page offset (page at hmon SRAM + 0xC00).
        slot_offs = tuple(
            bld.HMON_DATA_BASE + off for off in
            (bld.HMON_SLOT_CAUSE_ID, bld.HMON_SLOT_CAUSE_IP,
             bld.HMON_SLOT_CAUSE_INFO, bld.HMON_SLOT_RETURN))
        last = next(r for r in reversed(oracle["records"])
                    if r.get("kind") == "cause")
        want_slots = tuple(evaluate(last[k], ns) for k in
                           ("cause_id", "ip", "info", "return_slot"))
        got_slots = tuple(int.from_bytes(sram[off:off + 8], "big")
                          for off in slot_offs)
        report(got_slots == want_slots, "hmon SRAM data slots (last fault)",
               tuple(hex(v) for v in want_slots),
               tuple(hex(v) for v in got_slots))
        tail_off = bld.HMON_DATA_BASE + bld.HMON_DATA_SIZE
        report(not any(sram[tail_off:]),
               "hmon SRAM stack above the data page is zero",
               f"{len(sram) - tail_off} B zero",
               "all zero" if not any(sram[tail_off:]) else "non-zero")
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
        kind = want.get("kind")
        if kind == "check":
            exp = evaluate(want["expect"], ns)
            report(got[0] == want["id"], f"record {idx} check id",
                   want["id"], got[0])
            report(got[1] == exp, f"record {idx} check {want['id']} value",
                   hex(exp), hex(got[1]))
            report(got[2] == exp, f"record {idx} check {want['id']} guest copy",
                   hex(exp), hex(got[2]))
            report(got[3] == 0, f"record {idx} check {want['id']} reserved",
                   0, got[3])
        elif kind == "cause":
            ip = evaluate(want["ip"], ns)
            info = evaluate(want["info"], ns)
            ret = evaluate(want["return_slot"], ns)
            cid = evaluate(want["cause_id"], ns)
            report(got[0] == cid, f"record {idx} cause {want['cause']}",
                   hex(cid), hex(got[0]))
            report(got[1] == ip, f"record {idx} cause_ip", hex(ip), hex(got[1]))
            report(got[2] == info, f"record {idx} cause_info", hex(info),
                   hex(got[2]))
            report(got[3] == ret, f"record {idx} return_slot", hex(ret),
                   hex(got[3]))
        elif kind == "cfx_cause":
            # A cause frame read from the *current* cfx's own cg5 (§5.2(一):
            # CFXESC is delivered to the current cfx, not to the monitor).
            label = f"record {idx} cfx cause {want['cause']} ({want['cfx']})"
            report(got[0] == evaluate(want["cause_id"], ns), label,
                   hex(evaluate(want["cause_id"], ns)), hex(got[0]))
            report(got[1] == evaluate(want["ip"], ns),
                   f"record {idx} cfx cause_ip",
                   hex(evaluate(want["ip"], ns)), hex(got[1]))
            report(got[2] == evaluate(want["info"], ns),
                   f"record {idx} cfx cause_info",
                   hex(evaluate(want["info"], ns)), hex(got[2]))
            report(got[3] == evaluate(want["prev_cfx"], ns),
                   f"record {idx} cfx prev_cfx_code",
                   hex(evaluate(want["prev_cfx"], ns)), hex(got[3]))
        elif kind == "monitor_unchanged":
            # Reverse assertion: the monitor's SRAM data slots must still hold
            # the previous monitor entry (the CFXESC frame did not run hmon).
            report(got[0] == evaluate(want["cause_id"], ns),
                   f"record {idx} monitor untouched: still "
                   f"{want['after']}", hex(evaluate(want["cause_id"], ns)),
                   hex(got[0]))
            report(got[1] == evaluate(want["ip"], ns),
                   f"record {idx} monitor untouched cause_ip",
                   hex(evaluate(want["ip"], ns)), hex(got[1]))
            report(got[2] == evaluate(want["info"], ns),
                   f"record {idx} monitor untouched cause_info",
                   hex(evaluate(want["info"], ns)), hex(got[2]))
            report(got[3] == evaluate(want["return_slot"], ns),
                   f"record {idx} monitor untouched return_slot",
                   hex(evaluate(want["return_slot"], ns)), hex(got[3]))
        else:
            report(False, f"record {idx} kind",
                   "check|cause|cfx_cause|monitor_unchanged", kind)

    # ---- loader negatives: each must fail loudly, never silently -----------
    bad_dir = work / "bad"
    bad_dir.mkdir()
    cases = []
    r = run_gem5(gem5, config, work, "no-bootrom", app_elf, None, args.max_ticks)
    cases.append(("missing --bootrom", r, "requires --bootrom"))
    short = work / "bootrom_short.bin"
    short.write_bytes(shared_img[:bld.BOOTROM_SIZE - 1])
    r = run_gem5(gem5, config, work, "bootrom-short", app_elf, short,
                 args.max_ticks)
    cases.append((f"BootROM not {bld.BOOTROM_SIZE} bytes", r,
                  f"exactly {bld.BOOTROM_SIZE} bytes"))
    for name, base, needle in (
            ("BootROM", prof["bootrom_base"], "targets the BootROM"),
            ("hmon SRAM", prof["hmon_base"], "targets the hmon SRAM")):
        elf = bad_dir / f"ptload_{name.split()[0].lower()}.elf"
        # A 4-byte segment entirely inside the target region.
        patch_elf(app_elf, elf, paddr=base, mem_size=4)
        r = run_gem5(gem5, config, work, f"ptload-{name.split()[0].lower()}",
                     elf, shared_meta["path"], args.max_ticks)
        cases.append((f"PT_LOAD into {name}", r, needle))
    elf = bad_dir / "entry_not_fixed.elf"
    patch_elf(app_elf, elf, entry=prof["entry"] + 0x40)
    r = run_gem5(gem5, config, work, "entry-not-fixed", elf,
                 shared_meta["path"], args.max_ticks)
    cases.append((f"e_entry != {hex(prof['entry'])}", r,
                  f"fixed at {hex(prof['entry'])}"))
    for name, proc, needle in cases:
        combined = proc.stdout + proc.stderr
        report(proc.returncode != 0, f"negative: {name} rc", "!= 0",
               proc.returncode)
        report(needle in combined, f"negative: {name} message", needle,
               "found" if needle in combined else "missing")

    guard_ok = writer_guard.finish_guard(guard)
    if FAILS:
        print(f"\ncheck_tiny_hmon: FAIL ({FAILS}/{CHECKS})")
        return 1
    if not guard_ok:
        return 1
    print(f"\ncheck_tiny_hmon: PASS ({CHECKS} checks, "
          f"{len(expected)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
