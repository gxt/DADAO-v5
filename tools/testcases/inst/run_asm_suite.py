#!/usr/bin/env python3
"""run_asm_suite.py — 跑 `tests/inst/<册>/*.S`（汇编 + 宏）用例，三方逐字节对照。

被测对象（M13 用户裁定 2026-11-12）：`tests/inst/01-load-store/*.S`，一行一个用例，
**期望值内联**，宏层 `tests/inst/macros/inst_test.inc`（`TEST_LD` / `TEST_ST` /
`TEST_FAULT` / `__CHECK_RD`；失败 ⇒ `SYS_EXIT(检查点号)`）。

一个 `.S` 产出多种镜像（`llvm-mc -defsym CASE_N=<点号>`）：
  * `CASE_N=0`：**链例镜像**，全部非故障用例顺序执行，逐检查点把实测 8 字节写进结果
    缓冲，末尾 `SYS_WRITEC` 打印；判据 = 三方退出码同为 0 **且** 输出字节流逐字节相同，
    长度 = `8 × 检查点数`；
  * `CASE_N=<k>`：**故障例镜像**（`TEST_FAULT` 行），判据 = 三方退出码同为该故障的
    monitor 段编码 `0xF0|异常位索引`（`spec/Machine-v5 §7.1`：CFXMEM `0xF1`、
    CFXREG `0xF2`、ILLI `0xF8`、MALIGN `0xFC`、IALIGN `0xFD`）。

三平台 = 同一份 ELF：
  * chipyard `WumingTinyConfig`（Verilator harness，`+loadmem=<elf>`）
  * QEMU system `dadao-tiny`（`-bios <bootrom> -kernel <elf>`）
  * gem5 FS `tiny`（`configs/dadao/fs.py --bootrom <bootrom> --kernel <elf>`）

判据里没有任何「写死的用例数/字节数」：检查点数由 `.S` 现场统计，字节数由检查点数
派生，三方比较用 `cmp` 语义（全字节）。

用法：
    python3 tools/testcases/inst/run_asm_suite.py                    # 全部 19 个 id
    python3 tools/testcases/inst/run_asm_suite.py --id ld.o_rrii_rd  # 单个
    python3 tools/testcases/inst/run_asm_suite.py --platforms qemu   # 快速自查
    python3 tools/testcases/inst/run_asm_suite.py --chain-only       # 只跑链例
    python3 tools/testcases/inst/run_asm_suite.py --json-out <f>     # 逐例记录

退出码：0 = 全部一致；1 = 有失败；2 = setup 错（缺工具/缺 BootROM/0 载体）。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
sys.path.insert(0, str(_REPO / "tools" / "infra"))
import paths  # noqa: E402

FAULT_CODE = {"CFXMEM": 0xF1, "CFXREG": 0xF2, "ILLI": 0xF8,
              "MALIGN": 0xFC, "IALIGN": 0xFD}

# 链例用例行（检查点计数的口径：每个 TEST_LD*/TEST_ST*/__CHECK_* 一行 = 一个检查点；
# `TEST_LDM`/`TEST_STM` 每行只记一个检查点，与宏内单次 `__REC` 对齐）
CHAIN_CASE_RE = re.compile(r"^\t(TEST_LD\w*|TEST_ST\w*|__CHECK_RD|__CHECK_MEM)\b")
# 链例行**写下的点号字面量**（断言用：点号必须等于它在文件里的序号，不能只靠计数器自增）
CHAIN_PT_RE = re.compile(r"^\t(?:TEST_LD\w*|TEST_ST\w*|__CHECK_RD|__CHECK_MEM)"
                         r"\s+(\d+),")
FAULT_RE = re.compile(r"^\tTEST_FAULT(?:_M)?\s+(\d+),\s*(\S+?),\s*(\S+?),\s*"
                      r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN)\b")
FAULT_ENC_RE = re.compile(r"^\tTEST_FAULT_ENC\s+(\d+),\s*"
                          r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN)\b")
END_RE = re.compile(r"^\t__TEST_END\b")

DEFAULT_LDS = "tests/inst/01-load-store/inst-tiny.lds"
DEFAULT_VECTORS = "tests/inst/01-load-store"
DEFAULT_GEM5 = ".work/source/gem5/build/DADAO/gem5.opt"
DEFAULT_GEM5_CONFIG = ".work/source/gem5/configs/dadao/fs.py"
DEFAULT_CHIPYARD = ("sims/verilator/simulator-chipyard.harness-WumingTinyConfig")
DEFAULT_CHIPYARD_ROOT = ".work/source/chipyard"
MAX_CYCLES = "20000000"


# ---------------------------------------------------------------------------
# 现场统计
# ---------------------------------------------------------------------------
def scan_source(path: Path) -> dict:
    """从 `.S` 现场读出：链例检查点数、故障例（点号, 故障名）、点号是否连续。

    点号不变式（任务书验收 2）：**链例点号 1..N、故障例续 N+1..N+M，无跳号/重号**；
    即「失败点号 = 用例序号」。链例点号取**行内写下的字面量**（而非计数器），
    字面量与序号不符 / 解析不出 ⇒ `pts_ok = False`（fail-closed）。
    """
    checks = 0
    faults = []
    pts = []
    in_chain = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if END_RE.match(line):
            in_chain = False
            continue
        if in_chain and CHAIN_CASE_RE.match(line):
            checks += 1
            m = CHAIN_PT_RE.match(line)
            pts.append(int(m.group(1)) if m else -1)
            continue
        m = FAULT_RE.match(line)
        if m:
            faults.append({"pt": int(m.group(1)), "reg": m.group(3),
                           "fault": m.group(4)})
            pts.append(int(m.group(1)))
            continue
        m = FAULT_ENC_RE.match(line)
        if m:
            faults.append({"pt": int(m.group(1)), "reg": "-",
                           "fault": m.group(2)})
            pts.append(int(m.group(1)))
    return {"checks": checks, "faults": faults,
            "pts_ok": pts == list(range(1, len(pts) + 1))}


# ---------------------------------------------------------------------------
# 建镜像
# ---------------------------------------------------------------------------
def build(toolbin: Path, src: Path, lds: Path, case_n: int, outdir: Path,
          stem: str) -> Path:
    obj = outdir / (stem + ".o")
    elf = outdir / (stem + ".elf")
    cmd = [str(toolbin / "llvm-mc"), "--triple=dadao-unknown-elf",
           "-filetype=obj"]
    if case_n:
        cmd += ["--defsym", "CASE_N=%d" % case_n]
    cmd += [str(src), "-o", str(obj)]
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run([str(toolbin / "ld.lld"), "-T", str(lds), str(obj),
                    "-o", str(elf)], check=True, capture_output=True)
    return elf


# ---------------------------------------------------------------------------
# 三个平台：返回 (rc, stdout_bytes, log_path)
# ---------------------------------------------------------------------------
def run_qemu(qemu: Path, elf: Path, bootrom: Path, out: Path, log: Path,
             timeout: int):
    out.unlink(missing_ok=True)
    cmd = [str(qemu), "-M", "dadao-tiny", "-bios", str(bootrom),
           "-kernel", str(elf),
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=%s" % out,
           "-nographic"]
    return _run(cmd, log, timeout, out)


def run_gem5(gem5: Path, config: Path, elf: Path, bootrom: Path, out: Path,
             log: Path, outdir: Path, timeout: int):
    out.unlink(missing_ok=True)
    cmd = [str(gem5), "--outdir=%s" % outdir, str(config),
           "--profile", "tiny", "--bootrom", str(bootrom),
           "--kernel", str(elf), "--console-out", str(out)]
    return _run(cmd, log, timeout, out)


def run_chipyard(sim: Path, elf: Path, out: Path, log: Path, timeout: int,
                 env_extra: dict):
    out.unlink(missing_ok=True)
    cmd = [str(sim), "+permissive", "+loadmem=%s" % elf,
           "+semiout=%s" % out, "+max-cycles=%s" % MAX_CYCLES,
           "+permissive-off", "none"]
    return _run(cmd, log, timeout, out, env_extra)


def _run(cmd, log: Path, timeout: int, out: Path, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    with open(log, "wb") as fh:
        try:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                  timeout=timeout, env=env,
                                  stdin=subprocess.DEVNULL)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = -2                       # 超时 ≠ 任何 guest 退出码
    data = out.read_bytes() if out.is_file() else b""
    return rc, data, log


# ---------------------------------------------------------------------------
# 一个镜像 × 三平台
# ---------------------------------------------------------------------------
def check_variant(task, cfg) -> dict:
    """跑一个镜像；返回记录（含三方 rc 与字节流比较）。"""
    src, case_n, expected = task
    stem = "%s%s" % (src.stem, "" if case_n == 0 else "_fault%03d" % case_n)
    outdir = cfg["work"] / src.stem
    outdir.mkdir(parents=True, exist_ok=True)
    rec = {"file": src.name, "case_n": case_n, "kind":
           "chain" if case_n == 0 else "fault", "expected": expected,
           "platforms": {}, "ok": False, "notes": []}
    try:
        elf = build(cfg["toolbin"], src, cfg["lds"], case_n, outdir, stem)
    except (subprocess.CalledProcessError, OSError) as exc:
        rec["notes"].append("build: %s" % exc)
        return rec
    rec["elf"] = elf.name

    want = ["chipyard", "qemu", "gem5"]
    if cfg["platforms"]:
        want = [p for p in want if p in cfg["platforms"]]
    for plat in want:
        ldir = cfg["logdir"] / src.stem
        ldir.mkdir(parents=True, exist_ok=True)
        log = ldir / (stem + "." + plat + ".log")
        out = outdir / (stem + "." + plat + ".out")
        if plat == "qemu":
            rc, data, _ = run_qemu(cfg["qemu"], elf, cfg["bootrom"], out, log,
                                   cfg["timeouts"]["qemu"])
        elif plat == "gem5":
            m5dir = outdir / (stem + ".m5out")
            rc, data, _ = run_gem5(cfg["gem5"], cfg["gem5_config"], elf,
                                   cfg["bootrom"], out, log, m5dir,
                                   cfg["timeouts"]["gem5"])
        else:
            rc, data, _ = run_chipyard(cfg["chipyard"], elf, out, log,
                                       cfg["timeouts"]["chipyard"],
                                       cfg["chipyard_env"])
        rec["platforms"][plat] = {"rc": rc, "bytes": len(data)}

    # 判据
    rcs = {p: rec["platforms"][p]["rc"] for p in rec["platforms"]}
    if case_n == 0:
        good = all(rc == 0 for rc in rcs.values())
        blobs = {p: _read_or_empty(outdir / (stem + "." + p + ".out"))
                 for p in rec["platforms"]}
        if good and len(set(blobs.values())) != 1:
            good = False
            rec["notes"].append("字节流不一致: " +
                                ", ".join("%s=%s" % (p, _md5(b))
                                          for p, b in blobs.items()))
        nbytes = 8 * expected
        got = {p: len(b) for p, b in blobs.items()}
        if good and any(v != nbytes for v in got.values()):
            good = False
            rec["notes"].append("结果字节数 %s ≠ 8×检查点数 %d" % (got, nbytes))
        rec["bytes"] = got
    else:
        code = FAULT_CODE[expected]
        good = all(rc == code for rc in rcs.values())
        if not good:
            rec["notes"].append("退出码 ≠ 期望 0x%02X" % code)
    rec["ok"] = good
    return rec


def _read_or_empty(path: Path) -> bytes:
    return path.read_bytes() if path.is_file() else b""


def _md5(b: bytes) -> str:
    import hashlib
    return hashlib.md5(b).hexdigest()[:8]


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vectors", default=str(_REPO / DEFAULT_VECTORS))
    ap.add_argument("--lds", default=str(_REPO / DEFAULT_LDS))
    ap.add_argument("--id", action="append", default=None,
                    help="只跑这些 id（可重复；默认全部）")
    ap.add_argument("--platforms", default="chipyard,qemu,gem5")
    ap.add_argument("--chain-only", action="store_true")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--gem5", default=str(_REPO / DEFAULT_GEM5))
    ap.add_argument("--gem5-config", default=str(_REPO / DEFAULT_GEM5_CONFIG))
    ap.add_argument("--chipyard", default=None)
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--timeout-qemu", type=int, default=120)
    ap.add_argument("--timeout-gem5", type=int, default=300)
    ap.add_argument("--timeout-chipyard", type=int, default=900)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--scan-only", action="store_true",
                    help="只做现场统计与点号/上限断言（不建镜像、不跑）")
    args = ap.parse_args()

    toolbody = paths.host_toolchain_dir() / "bin"
    qemu = Path(args.qemu) if args.qemu else toolbody / "qemu-system-dadao"
    chipyard_root = _REPO / DEFAULT_CHIPYARD_ROOT
    chipyard = (Path(args.chipyard) if args.chipyard
                else chipyard_root / DEFAULT_CHIPYARD)
    bootrom = (Path(args.bootrom) if args.bootrom
               else paths.test_artifacts_dir() / "bootrom" / "tiny" /
               "bootrom_tiny.bin")
    plats = [p for p in args.platforms.split(",") if p]
    need = [("lds", Path(args.lds))]
    if not args.scan_only:
        need += [("qemu", qemu), ("llvm-mc", toolbody / "llvm-mc"),
                 ("ld.lld", toolbody / "ld.lld"), ("bootrom", bootrom)]
        if "gem5" in plats:
            need.append(("gem5", Path(args.gem5)))
        if "chipyard" in plats:
            need.append(("chipyard", chipyard))
    for what, path in need:
        if not Path(path).exists():
            print("run_asm_suite: ERROR: %s 不存在: %s" % (what, path),
                  file=sys.stderr)
            return 2

    srcs = sorted(Path(p) for p in glob.glob(str(Path(args.vectors) / "*.S")))
    if args.id:
        srcs = [s for s in srcs if s.stem in set(args.id)]
    if not srcs:
        print("run_asm_suite: ERROR: 0 个载体（%s）" % args.vectors,
              file=sys.stderr)
        return 2

    # 生成物落在 `harness/`（`manage_tests.SCOPE_MAP` 已登记的 inst 产物目录）：
    # 新开顶层目录会被 `manage_tests` 的「未归属目录」判据打红。
    work = Path(args.work_dir) if args.work_dir else \
        paths.test_artifacts_dir() / "harness" / "inst-asm"
    logdir = Path(args.log_dir) if args.log_dir else work / "log"
    work.mkdir(parents=True, exist_ok=True)
    logdir.mkdir(parents=True, exist_ok=True)
    cfg = {"toolbin": toolbody, "lds": Path(args.lds), "qemu": qemu,
           "gem5": Path(args.gem5), "gem5_config": Path(args.gem5_config),
           "chipyard": chipyard, "bootrom": bootrom, "work": work,
           "logdir": logdir, "platforms": plats,
           "timeouts": {"qemu": args.timeout_qemu, "gem5": args.timeout_gem5,
                        "chipyard": args.timeout_chipyard},
           "chipyard_env": {
               "LD_LIBRARY_PATH": ":".join(filter(None, [
                   str(chipyard_root / ".conda-env" / "riscv-tools" / "lib"),
                   str(chipyard_root / ".conda-env" / "lib"),
                   os.environ.get("LD_LIBRARY_PATH", "")]))}}

    tasks = []
    meta = {}
    for src in srcs:
        info = scan_source(src)
        meta[src.name] = info
        if not info["checks"] and not info["faults"]:
            print("run_asm_suite: ERROR: %s 没有用例行" % src.name,
                  file=sys.stderr)
            return 2
        if info["checks"] + len(info["faults"]) > 127:
            print("run_asm_suite: ERROR: %s 检查点 %d > 127"
                  % (src.name, info["checks"] + len(info["faults"])),
                  file=sys.stderr)
            return 2
        if not info["pts_ok"]:
            print("run_asm_suite: ERROR: %s 检查点号不是 1..N 连续（失败点号 ≠ 用例序号）"
                  % src.name, file=sys.stderr)
            return 2
        if info["checks"]:
            tasks.append((src, 0, info["checks"]))
        if not args.chain_only:
            for f in info["faults"]:
                tasks.append((src, f["pt"], f["fault"]))

    print("run_asm_suite: %d 个 id / %d 个镜像 / 平台 %s / jobs=%d"
          % (len(srcs), len(tasks), ",".join(plats), args.jobs))
    if args.scan_only:
        for src in srcs:
            info = meta[src.name]
            print("  %-22s 链例 %2d + 故障例 %d（点号 1..%d 连续；≤127）"
                  % (src.name, info["checks"], len(info["faults"]),
                     info["checks"] + len(info["faults"])))
        return 0
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for rec in pool.map(lambda t: check_variant(t, cfg), tasks):
            records.append(rec)
            tag = "PASS" if rec["ok"] else "FAIL"
            if rec["kind"] == "chain":
                detail = "检查点 %d / %s B / rc %s" % (
                    rec["expected"],
                    rec.get("bytes", {}),
                    {p: v["rc"] for p, v in rec["platforms"].items()})
            else:
                detail = "期望 0x%02X / rc %s" % (
                    FAULT_CODE[rec["expected"]],
                    {p: v["rc"] for p, v in rec["platforms"].items()})
            print("  [%s] %-22s %-11s %s" % (tag, rec["file"], rec["kind"],
                                             detail))
            for n in rec["notes"]:
                print("         %s" % n)

    npass = sum(1 for r in records if r["ok"])
    print("-" * 72)
    print("run_asm_suite: %d/%d 镜像通过（%d 个 id；链例 %d，故障例 %d）"
          % (npass, len(records), len(srcs),
             sum(1 for r in records if r["kind"] == "chain"),
             sum(1 for r in records if r["kind"] == "fault")))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"schema": "inst-asm-suite/1", "records": records}, indent=1) + "\n")
    return 0 if npass == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
