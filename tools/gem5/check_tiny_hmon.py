#!/usr/bin/env python3
"""check_tiny_hmon — Machine-v5-Tiny cfx_power + cfx3 hmon acceptance runner.

Builds `tests/arch/hmon/tiny_hmon.S`, runs it on the gem5 Tiny FS profile, and
compares the guest-exported result table against the independent oracle in
`tests/arch/hmon/expected.yaml` (spec-derived cause ids, ELF-symbol IPs, and
profile-derived cg7 offsets).

Usage:
    python3 tools/gem5/check_tiny_hmon.py [--gem5 BIN] [--config fs.py]
        [--work-dir DIR] [--max-ticks N]

Exit codes: 0 all checks pass; 1 any check fails; 2 missing build input.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / "tests" / "arch" / "hmon"
SHARED_ASM = ROOT / "tests" / "shared" / "asm"
DEFAULT_GEM5 = ROOT / ".work" / "source" / "gem5" / "build" / "DADAO" / "gem5.opt"
DEFAULT_CONFIG = ROOT / ".work" / "source" / "gem5" / "configs" / "dadao" / "fs.py"
PASS_EXIT = 0x21

sys.path.insert(0, str(ROOT / "tools" / "infra"))
import paths  # noqa: E402

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


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def build(work: Path, tc: str) -> Path:
    obj = work / "tiny_hmon.o"
    elf = work / "tiny_hmon.elf"
    src = CASE_DIR / "tiny_hmon.S"
    lds = CASE_DIR / "tiny_hmon.lds"
    for tool in ("llvm-mc", "ld.lld", "llvm-nm"):
        if not (Path(tc) / tool).is_file():
            print(f"check_tiny_hmon: ERROR: {tool} not found under {tc}",
                  file=sys.stderr)
            raise SystemExit(2)
    r = run([str(Path(tc) / "llvm-mc"), "--triple=dadao-unknown-elf",
             "-filetype=obj", "-I", str(CASE_DIR), "-I", str(SHARED_ASM),
             str(src), "-o", str(obj)])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)
    r = run([str(Path(tc) / "ld.lld"), "-T", str(lds), str(obj),
             "-o", str(elf)])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)
    return elf


def symbols(elf: Path, tc: str) -> dict[str, int]:
    r = run([str(Path(tc) / "llvm-nm"), str(elf)])
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(2)
    out: dict[str, int] = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        value, _kind, name = parts
        try:
            out[name] = int(value, 16)
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

    work = Path(args.work_dir) if args.work_dir else ROOT / ".dadao" / "tests" / "tiny-hmon"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    run_dir = work / "run"
    run_dir.mkdir()

    elf = build(work, args.toolchain_bin)
    syms = symbols(elf, args.toolchain_bin)

    oracle = yaml.safe_load((CASE_DIR / "expected.yaml").read_text())
    ns: dict[str, object] = dict(oracle["profile"])
    ns.update(syms)

    r = run([str(gem5), "--outdir", str(work / "out"), str(config),
             "--profile", "tiny", "--kernel", str(elf),
             "--max-ticks", str(args.max_ticks)], cwd=run_dir)
    (work / "gem5.stdout").write_text(r.stdout)
    (work / "gem5.stderr").write_text(r.stderr)

    report(r.returncode == PASS_EXIT, "gem5 guest exit", hex(PASS_EXIT),
           hex(r.returncode & 0xFF))
    report("hmon-ok" in r.stdout, "semihosting with trap cfx63",
           "console contains hmon-ok", "found" if "hmon-ok" in r.stdout
           else "missing")
    report("GEM5_EXIT_CAUSE=semi:ADP_Stopped_ApplicationExit" in r.stderr,
           "semihosting stop cause", "semi:ADP_Stopped_ApplicationExit",
           next((ln for ln in r.stderr.splitlines()
                 if ln.startswith("GEM5_EXIT_CAUSE=")), "missing"))

    result_path = run_dir / "hmon_results.bin"
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
            report(got[0] == evaluate(want["cause_id"], ns),
                   f"record {idx} cause {want['cause']}",
                   hex(evaluate(want["cause_id"], ns)), hex(got[0]))
            report(got[1] == ip, f"record {idx} cause_ip", hex(ip), hex(got[1]))
            report(got[2] == info, f"record {idx} cause_info", hex(info),
                   hex(got[2]))
            report(got[3] == hpc, f"record {idx} handler PC", hex(hpc),
                   hex(got[3]))

    if FAILS:
        print(f"\ncheck_tiny_hmon: FAIL ({FAILS}/{CHECKS})")
        return 1
    print(f"\ncheck_tiny_hmon: PASS ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
