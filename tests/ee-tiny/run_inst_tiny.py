#!/usr/bin/env python3
"""run_inst_tiny.py — 跑 `tests/inst/<册>/*.S`（汇编 + 宏）用例，三方逐字节对照。

被测对象（M13 用户裁定 2026-11-12）：`tests/inst/01-load-store/*.S`，一行一个用例，
**期望值内联**，宏层 `tests/inst/macros/inst_test.inc`（`TEST_LD` / `TEST_ST` /
`TEST_FAULT` / `__CHECK_RD`；失败 ⇒ `SYS_EXIT(检查点号)`）。

一个 `.S` 产出**一个镜像**（`m15-testcases-007` 起；`CASE_N=0`）：
  全部非故障用例顺序执行、逐检查点把实测 8 字节写进结果缓冲，随后**进入故障链**——
  每个故障例依次执行其触发指令，hmon 落点（`.faultpad` 的 `__pad`）核对 `cause_id`
  低 16 位 one-hot 后跳下一例，最后一例落到收尾（`SYS_WRITEC` 逐字节打印结果缓冲 +
  `SYS_EXIT(0)`）。判据 = 三方退出码同为 0 **且** 输出字节流逐字节相同，
  长度 = `8 × 检查点数`（链例检查点；故障例结果不写入缓冲）。

  故障例的成败由此表达：异常**没有**发生 ⇒ 该例体末尾的 `__EXIT(点号)` ⇒ 该镜像红；
  `cause_id` 大类不符 ⇒ 落点 `__EXIT(点号)` ⇒ 该镜像红（且后续例不再执行）。
  单例调试路径仍由 `-defsym CASE_N=<点号>` 提供（`_start` 直接跳该例，之后仍按链
  续跑；只比退出码，不打印缓冲），不进门控。

三平台 = 同一份 ELF：
  * chipyard `WumingTinyConfig`（Verilator harness，`+loadmem=<elf>`）
  * QEMU system `kaiwu-tiny`（`-bios <bootrom> -kernel <elf>`）
  * gem5 FS `tiny`（`configs/dadao/fs.py --bootrom <bootrom> --kernel <elf>
    --semihost on`；`m16-gem5-011` 起 `--semihost` 默认 `off`，必须显式开）

判据里没有任何「写死的用例数/字节数」：检查点数由 `.S` 现场统计，字节数由检查点数
派生，三方比较用 `cmp` 语义（全字节）。

用法：
    python3 tests/ee-tiny/run_inst_tiny.py                         # 01 册全部 id
    python3 tests/ee-tiny/run_inst_tiny.py --id ld.o_rrii_ra       # 单个
    python3 tests/ee-tiny/run_inst_tiny.py --books-root tests/inst \
        --platforms qemu                                          # 全部册（L2 门控）
    python3 tests/ee-tiny/run_inst_tiny.py --platforms qemu        # 快速自查
    python3 tests/ee-tiny/run_inst_tiny.py --json-out <f>          # 逐例记录

`--books-root`（`make check-inst-asm` 用）：扫描该根的**全部子目录**，凡含 `.S` 的册
即为载体目录。**全部册共用同一份布局** `tests/ee-tiny/inst_tiny.lds`
（`m15-testcases-006`；册目录内不再有 `.lds`），`--lds` 只用于覆盖它。
`--vectors` 可重复（单/多目录），与 `--books-root` 可叠加。

退出码：0 = 全部一致；1 = 有失败；2 = setup 错（缺工具/缺 BootROM/0 载体）。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "tools" / "infra"))
import paths  # noqa: E402
import writer_guard  # noqa: E402

FAULT_CODE = {"CFXMEM": 0xF1, "CFXREG": 0xF2, "ILLI": 0xF8,
              "MALIGN": 0xFC, "IALIGN": 0xFD,
              # 控制流（06）额外用到：保留编码 UNDI、RAS 上溢/下溢（`spec/Kaiwu §7.1`）
              "UNDI": 0xF9, "RASOF": 0xFA, "RASUF": 0xFB}
# ⚠ `m15-testcases-007` 起故障例链式合并进同一镜像，本文件**不再**按它判退出码
# （失败 = 点号，见 `__EXIT \pt`）。保留为**monitor 段编码表**：三方差分工具
# （`tools/testcases/parity/fp_diff.py` 等）仍按它解读历史/单例记录。

# 链例用例行（检查点计数的口径：每个 TEST_LD*/TEST_ST*/TEST_MOV*/TEST_CS*/TEST_WI*/__CHECK_* 一行
# = 一个检查点；`TEST_LDM`/`TEST_STM` 每行只记一个检查点，与宏内单次 `__REC` 对齐；
# `TEST_MOV1`/`TEST_CS*`（02-reg-copy）/`TEST_WI*`（03-wyde-imm）/`TEST_AR*`
# （04-arith-logic-octa 算术/逻辑族）同理，多条 `__VERIFY_*` 断言共用一个点号）
#
# `__PT_*`（m15-testcases-004 整例宏化）：**一整条用例 = 一行宏调用**，点号是该行的
# **第一个实参**（`__PT_SC_LD\t7, sc.b.ar, …`）。宏体（`.macro`..`.endm`）由
# `iter_code_lines` 跳过，故宏内的 `__CHECK_*` 不进计数；「一行 = 一个检查点」由
# `check_inst_macro_scope` 的 S6/S7/S8 静态判据保证（宏体恰 1 处断言、点号引用 `\pt`、
# 正文不得留裸 `__CHECK_*`），本文件只负责按点号字面量校验连续性（`pts_ok`，语义不变）。
CHAIN_CASE_RE = re.compile(r"^\t(TEST_LD\w*|TEST_ST\w*|TEST_MOV\w*|TEST_CS\w*|"
                           r"TEST_WI\w*|TEST_AR\w*|TEST_BR\w*|TEST_FP\w*|"
                           r"__CHECK_(?:RD|MEM)\w*|__PT_\w*)\b")
# 链例行**写下的点号字面量**（断言用：点号必须等于它在文件里的序号，不能只靠计数器自增）
CHAIN_PT_RE = re.compile(r"^\t(?:TEST_LD\w*|TEST_ST\w*|TEST_MOV\w*|TEST_CS\w*|"
                         r"TEST_WI\w*|TEST_AR\w*|TEST_BR\w*|TEST_FP\w*|"
                         r"__CHECK_(?:RD|MEM)\w*)\s+(\d+),")
# `__PT_*` 用例行的点号 = **第一个实参**；该宏允许只有点号一个实参
# （如 `__PT_RF_COPY_N31 9` 这类形状固定、无需其它操作数的用例）⇒ 行尾逗号可省。
CHAIN_PT_PT_RE = re.compile(r"^\t__PT_\w*\s+(\d+)\s*(?:,|$)")
FAULT_RE = re.compile(r"^\tTEST_FAULT(?:_MOV|_CS2|_CS|_M|_WI)?\s+(\d+),\s*(\S+?),\s*(\S+?),\s*"
                      r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN|UNDI|RASOF|RASUF)\b")
FAULT_ENC_RE = re.compile(r"^\tTEST_FAULT_ENC\s+(\d+),\s*"
                          r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN|UNDI|RASOF|RASUF)\b")
# 06-control-flow 的故障宏：`TEST_FAULT_CF(pt, 故障名, 编码字)` 与
#   `TEST_FAULT_RAS(pt, 故障名, call/ret 全文)` / `TEST_FAULT_RASUF_MEM(pt, ret 全文)`
FAULT_CF_RE = re.compile(r"^\tTEST_FAULT_CF\s+(\d+),\s*"
                         r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN|UNDI|RASOF|RASUF)\b")
# `TEST_FAULT_CF1(pt, 寄存器, 值, 故障名, 编码字)`：故障名前还有两个参数
FAULT_CF1_RE = re.compile(r"^\tTEST_FAULT_CF1\s+(\d+),\s*\S+,\s*\S+?,\s*"
                          r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN|UNDI|RASOF|RASUF)\b")
FAULT_RAS_RE = re.compile(r"^\tTEST_FAULT_RAS\s+(\d+),\s*"
                          r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN|UNDI|RASOF|RASUF)\b")
# `TEST_FAULT_RASUF_MEM(pt, ret 全文)`：MemRAS 条目计数 0 ⇒ 固定 RASUF
FAULT_RASUF_MEM_RE = re.compile(r"^\tTEST_FAULT_RASUF_MEM\s+(\d+),")
# `TEST_FAULT_BR{1,2}(pt, 助记符, …, 故障名, 目标)`：故障名在目标之前
FAULT_BR_RE = re.compile(r"^\tTEST_FAULT_BR[12]\s+(\d+),.*,\s*"
                         r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN|UNDI|RASOF|RASUF)\b")
# `TEST_FAULT_ADDR0(pt, 助记符, 故障名)`：rrii 跳转/调用的目标地址 0 ⇒ CFXMEM
FAULT_ADDR0_RE = re.compile(r"^\tTEST_FAULT_ADDR0\s+(\d+),\s*\S+,\s*"
                            r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN|UNDI|RASOF|RASUF)\b")
# 04-arith-logic-octa 算术/逻辑族与 05-arith-addr 的故障宏
# （`TEST_FAULT_{DUAL,ALU3,ALU_ORRI,ALU_SI,ALU_CMPI}` = 04 族；
#   `TEST_FAULT_{BBD,DBB,RB_SI}` = 05 族，参数 = 检查点, 助记符, 故障名, …）
FAULT_AR_RE = re.compile(r"^\tTEST_FAULT_(?:DUAL|ALU3|ALU_ORRI|ALU_SI|ALU_CMPI|BBD|DBB|RB_SI)"
                         r"\s+(\d+),\s*"
                         r"(\S+?),\s*(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN)\b")
# 07-floating-point 的原始编码故障例（目的 rf0 / root 的 n≠2 ⇒ ILLI）
FAULT_FP_RE = re.compile(r"^\tTEST_FAULT_FP\s+(\d+),\s*"
                         r"(CFXMEM|CFXREG|ILLI|MALIGN|IALIGN)\b")
END_RE = re.compile(r"^\t__TEST_END\b")
# `.S` 内可以定义**文件专用宏**（m15-testcases-002：宏作用域下沉），宏体里出现的
# `__CHECK_*`/`TEST_*` 行**不是**用例行 ⇒ 扫描（本文件与 `check_case_ledger`）一律
# 跳过 `.macro`..`.endm` 之间的行，否则检查点数/用例身份会被宏体污染。
MACRO_START_RE = re.compile(r"^\s*\.macro\b")
MACRO_END_RE = re.compile(r"^\s*\.endm\b")


def iter_code_lines(text: str):
    """逐行产出 `.S` 文本，**跳过宏定义体**（`.macro`..`.endm`）。"""
    in_macro = False
    for line in text.splitlines():
        if in_macro:
            if MACRO_END_RE.match(line):
                in_macro = False
            continue
        if MACRO_START_RE.match(line):
            in_macro = True
            continue
        yield line


DEFAULT_LDS = "tests/ee-tiny/inst_tiny.lds"
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
    for line in iter_code_lines(path.read_text(encoding="utf-8")):
        if END_RE.match(line):
            in_chain = False
            continue
        if in_chain and CHAIN_CASE_RE.match(line):
            checks += 1
            m = CHAIN_PT_RE.match(line) or CHAIN_PT_PT_RE.match(line)
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
            continue
        m = FAULT_AR_RE.match(line)
        if m:
            faults.append({"pt": int(m.group(1)), "reg": m.group(2),
                           "fault": m.group(3)})
            pts.append(int(m.group(1)))
            continue
        m = FAULT_FP_RE.match(line)
        if m:
            faults.append({"pt": int(m.group(1)), "reg": "-",
                           "fault": m.group(2)})
            pts.append(int(m.group(1)))
            continue
        m = FAULT_CF_RE.match(line) or FAULT_CF1_RE.match(line)
        if m:
            faults.append({"pt": int(m.group(1)), "reg": "-",
                           "fault": m.group(2)})
            pts.append(int(m.group(1)))
            continue
        m = FAULT_RAS_RE.match(line)
        if m:
            faults.append({"pt": int(m.group(1)), "reg": "-",
                           "fault": m.group(2)})
            pts.append(int(m.group(1)))
            continue
        m = FAULT_RASUF_MEM_RE.match(line)
        if m:
            faults.append({"pt": int(m.group(1)), "reg": "-",
                           "fault": "RASUF"})
            pts.append(int(m.group(1)))
            continue
        m = FAULT_BR_RE.match(line) or FAULT_ADDR0_RE.match(line)
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
    cmd = [str(qemu), "-M", "kaiwu-tiny", "-bios", str(bootrom),
           "-kernel", str(elf),
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=%s" % out,
           "-nographic"]
    return _run(cmd, log, timeout, out)


def run_gem5(gem5: Path, config: Path, elf: Path, bootrom: Path, out: Path,
             log: Path, outdir: Path, timeout: int, extra=()):
    out.unlink(missing_ok=True)
    cmd = [str(gem5), "--outdir=%s" % outdir, str(config),
           "--profile", "tiny", "--bootrom", str(bootrom),
           "--kernel", str(elf), "--semihost", "on", "--console-out", str(out)]
    cmd += list(extra)
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
    """跑一个镜像（每 `.S` 恰好一个：链例 + 故障链）；返回记录（含三方 rc 与字节流比较）。"""
    src, lds, expected = task
    stem = src.stem
    outdir = cfg["work"] / src.stem
    outdir.mkdir(parents=True, exist_ok=True)
    rec = {"file": src.name, "case_n": 0, "kind": "chain", "expected": expected,
           "platforms": {}, "ok": False, "notes": []}
    try:
        elf = build(cfg["toolbin"], src, lds, 0, outdir, stem)
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
                                   cfg["timeouts"]["gem5"], cfg["gem5_args"])
        else:
            rc, data, _ = run_chipyard(cfg["chipyard"], elf, out, log,
                                       cfg["timeouts"]["chipyard"],
                                       cfg["chipyard_env"])
        rec["platforms"][plat] = {"rc": rc, "bytes": len(data)}

    # 判据：三方退出码同为 0 + 字节流逐字节一致 + 长度 = 8 × 链例检查点数。
    # 故障例不写结果缓冲 ⇒ 链例字节流不受故障链影响；故障链自身靠 in-guest 断言
    # （落点核 one-hot、每例末尾 `__EXIT 点号` 兜「异常没发生」）。
    rcs = {p: rec["platforms"][p]["rc"] for p in rec["platforms"]}
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
    ap.add_argument("--vectors", action="append", default=None,
                    help="载体目录（可重复；默认 tests/inst/01-load-store）")
    ap.add_argument("--books-root", default=None,
                    help="扫描该根下所有含 .S 的子目录作为册载体"
                         "（如 tests/inst ⇒ 全部册）")
    ap.add_argument("--lds", default=None,
                    help="覆盖链接布局（默认 tests/ee-tiny/inst_tiny.lds，"
                         "全部册共用）")
    ap.add_argument("--id", action="append", default=None,
                    help="只跑这些 id（可重复；默认全部）")
    ap.add_argument("--platforms", default="chipyard,qemu,gem5")
    ap.add_argument("--chain-only", action="store_true",
                    help="历史开关：`m15-testcases-007` 起每 `.S` 只有一个镜像（链例 + "
                         "故障链），本开关已无效果，保留仅为 CLI 兼容")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--gem5", default=str(_REPO / DEFAULT_GEM5))
    ap.add_argument("--gem5-config", default=str(_REPO / DEFAULT_GEM5_CONFIG))
    ap.add_argument("--gem5-args", default="",
                    help="附加给 gem5 配置的 argv（如 '--cpu-type timing'），"
                         "用来在同一份配置上比较 CPU 模型")
    ap.add_argument("--chipyard", default=None)
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 1) - 2),
                    help="并发镜像数（默认 = 全量核 − 2；节点 40 核 -> 38、主控机 64 核 -> 62）")
    ap.add_argument("--timeout-qemu", type=int, default=120)
    ap.add_argument("--timeout-gem5", type=int, default=300)
    ap.add_argument("--timeout-chipyard", type=int, default=900)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--scan-only", action="store_true",
                    help="只做现场统计与点号/上限断言（不建镜像、不跑）")
    writer_guard.add_arguments(ap)
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
    need = []
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

    # ISS-373: refusing on an active writer and the start/finish md5 of every
    # binary used must happen before the first image is built/run.  **只登记
    # 本平台集合真的会用的二进制**：`--platforms qemu` 的 L2 门控不该被并行
    # 的 gem5/chipyard 构建挡住（未参与比较的二进制不构成假红来源）。
    used = [str(qemu), str(toolbody / "llvm-mc"), str(toolbody / "ld.lld"),
            str(bootrom)]
    if "gem5" in plats:
        used.append(str(Path(args.gem5)))
    if "chipyard" in plats:
        used.append(str(chipyard))
    if args.scan_only:
        # 只读源码统计，不消费任何二进制 ⇒ 不做 read guard（空清单会被
        # 解释成「全组件」，那会把只读统计误挡在并行构建外面）。
        guard = None
    else:
        guard = writer_guard.start_guard(args, used, label="run_asm_suite")

    # 载体目录（册）：`--vectors` 可重复；`--books-root` 扫描其下所有含 `.S` 的子目录。
    dirs = []
    if args.vectors:
        dirs += [Path(d) for d in args.vectors]
    elif not args.books_root:
        dirs.append(Path(_REPO / DEFAULT_VECTORS))
    if args.books_root:
        root = Path(args.books_root)
        if not root.is_dir():
            print("run_asm_suite: ERROR: --books-root 不是目录: %s" % root,
                  file=sys.stderr)
            return 2
        dirs += sorted(p for p in root.iterdir()
                       if p.is_dir() and any(p.glob("*.S")))
    # 去重（`--vectors` 与 `--books-root` 可能指到同一册；否则镜像会被跑两遍）
    seen = set()
    dirs = [d for d in dirs if not (d in seen or seen.add(d))]
    # 链接布局：**单一默认 + `--lds` 覆盖**（m15-testcases-006；册目录内不再有 `.lds`，
    # 也**不**再按册自动挑选——布局是全局单点，避免「某册悄悄换布局」）。
    lds = Path(args.lds) if args.lds else Path(_REPO / DEFAULT_LDS)
    if not lds.exists():
        print("run_asm_suite: ERROR: lds 不存在: %s" % lds, file=sys.stderr)
        return 2
    lds_by_dir = {d: lds for d in dirs}

    pairs = []
    for d in dirs:
        pairs += [(Path(p), lds_by_dir[d]) for p in glob.glob(str(d / "*.S"))]
    if args.id:
        pairs = [p for p in pairs if p[0].stem in set(args.id)]
    srcs = [p[0] for p in sorted(pairs)]
    if not srcs:
        print("run_asm_suite: ERROR: 0 个载体（%s）"
              % ", ".join(str(d) for d in dirs), file=sys.stderr)
        return 2
    lds_of = {src: lds for src, lds in pairs}

    # 生成物落在 `harness/`（`manage_tests.SCOPE_MAP` 已登记的 inst 产物目录）：
    # 新开顶层目录会被 `manage_tests` 的「未归属目录」判据打红。
    work = Path(args.work_dir) if args.work_dir else \
        paths.test_artifacts_dir() / "harness" / "inst-asm"
    logdir = Path(args.log_dir) if args.log_dir else work / "log"
    work.mkdir(parents=True, exist_ok=True)
    logdir.mkdir(parents=True, exist_ok=True)
    cfg = {"toolbin": toolbody, "qemu": qemu,
           "gem5": Path(args.gem5), "gem5_config": Path(args.gem5_config),
           "chipyard": chipyard, "bootrom": bootrom, "work": work,
           "gem5_args": shlex.split(args.gem5_args),
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
        # 每 `.S` 恰一个镜像（链例 + 故障链；`m15-testcases-007`）
        tasks.append((src, lds_of[src], info["checks"]))

    print("run_asm_suite: %d 个 id / %d 个镜像（每 .S 一个）/ 平台 %s / jobs=%d"
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
            detail = "检查点 %d / %s B / rc %s" % (
                rec["expected"],
                rec.get("bytes", {}),
                {p: v["rc"] for p, v in rec["platforms"].items()})
            print("  [%s] %-22s %-11s %s" % (tag, rec["file"], rec["kind"],
                                             detail))
            for n in rec["notes"]:
                print("         %s" % n)

    npass = sum(1 for r in records if r["ok"])
    nfault = sum(len(meta[r["file"]]["faults"]) for r in records)
    print("-" * 72)
    print("run_asm_suite: %d/%d 镜像通过（%d 个 id；链例 + 故障链 %d 例）"
          % (npass, len(records), len(srcs), nfault))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"schema": "inst-asm-suite/1", "records": records}, indent=1) + "\n")
    guard_ok = writer_guard.finish_guard(guard)
    return 0 if (npass == len(records) and guard_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
