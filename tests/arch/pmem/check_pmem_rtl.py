#!/usr/bin/env python3
"""`tests/arch/pmem/check_pmem_rtl.py` — cfx32 DMA 完成中断 + 同界多源的 RTL 承载
（`m16-testcases-014`；`run_arch.py` 的 chipyard 后端按 `check_<cfx_dir>_rtl.py`
发现）。

载体：`tests/arch/pmem/pmem_dma.S` + `pmem_dma.lds`（`WumingVastConfig`，
`+loadmem` 到 `0xffff_ff01_0100`）。与 QEMU/gem5 驱动共用**同一份** case 源与
`pmem_oracle.py` 的 oracle；本驱动把原始签名流过 oracle 后，向
`--signature-out` 写归一化签名（每槽 1 = 通过本平台 oracle）。

RTL 的 PA 测试窗经 step5 BootROM 的首张页表访问（PTE0：VA = PA，HSJU=0xC）；
DMA 直接以 PA 读写同一窗，与 QEMU/gem5 的语义一致。

用法：
  check_pmem_rtl.py --only arch-pmem-001 --sim PATH --mode hmon \\
      [--work-dir DIR] [--signature-out PATH] [--timeout N] \\
      [--selfcheck] [--list]

退出码：0 通过；1 判据失败；2 用法/缺件/配置错误。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_ARCH = _HERE.parents[1]
_REPO = _HERE.parents[3]

for _sub in (("tests", "shared"), ("tests", "arch"), ("tools", "infra")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

import paths as _paths                     # noqa: E402
import pmem_oracle as oracle               # noqa: E402

CASES = {"arch-pmem-001": ("hmon",), "arch-pmem-002": ("smon", "umon")}
MODE_CODE = {"hmon": 3, "smon": 2, "umon": 0}
SLOTS = {"arch-pmem-001": 55, "arch-pmem-002": 10}
SRC = _HERE.with_name("pmem_dma.S")
LDS = _HERE.with_name("pmem_dma.lds")
MAX_CYCLES = 20000000
TIMEOUT = 600


class SetupError(RuntimeError):
    pass


def _toolchain():
    bin_dir = _paths.host_toolchain_bin()
    tools = {name: bin_dir / name
             for name in ("llvm-mc", "ld.lld", "llvm-nm")}
    for name, path in tools.items():
        if not path.is_file():
            raise SetupError("缺 %s: %s（make install-host）" % (name, path))
    return tools


def _run(cmd, timeout, cwd=None):
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout,
                              stdin=subprocess.DEVNULL, cwd=cwd)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        return -2, exc.stdout or b""


def build(mode, tools, work):
    code = MODE_CODE[mode]
    obj = work / ("pmem_dma_%s.o" % mode)
    rc, out = _run([str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
                    "-filetype=obj", "-I", str(_REPO),
                    "-defsym", "TMODE=%d" % code,
                    "-defsym", "RTL_PTW_TABLE=1", str(SRC), "-o", str(obj)], 60)
    if rc != 0:
        raise SetupError("llvm-mc %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-800:]))
    elf = work / ("pmem_dma_%s.elf" % mode)
    rc, out = _run([str(tools["ld.lld"]), "-T", str(LDS), str(obj),
                    "-o", str(elf)], 60)
    if rc != 0:
        raise SetupError("ld.lld %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-800:]))
    syms = oracle.elf_symbols(str(tools["llvm-nm"]), str(elf))
    exp = oracle.expected(str(_REPO), code, syms)
    return elf, exp


def run_case(case_id, mode, args, tools, work):
    elf, exp = build(mode, tools, work)
    console = work / ("%s_%s.out" % (case_id, mode))
    if console.exists():
        console.unlink()
    cmd = [str(Path(args.sim).resolve()), "+permissive", "+verbose",
           "+loadmem=" + str(elf), "+semiout=" + str(console),
           "+max-cycles=%d" % MAX_CYCLES, "+permissive-off", "none"]
    rc, out = _run(cmd, args.timeout, cwd=str(work))
    problems = []
    if rc == -2:
        problems.append("RTL 超时（%ds）" % args.timeout)
    elif rc != 0:
        problems.append("RTL 退出码 %d" % rc)
    blob = console.read_bytes() if console.is_file() else b""
    got = None
    try:
        got = oracle.unpack(blob)
    except oracle.OracleError as exc:
        problems.append("签名流: %s" % exc)
    if got is not None:
        problems += oracle.check(got, exp)
    result = {
        "case": case_id, "mode": mode, "platform": "chipyard",
        "sim": str(args.sim), "elf": str(elf),
        "signature_slots": got, "problems": problems,
        "verdict": "PASS" if not problems else "FAIL", "command": cmd,
    }
    (work / ("run_%s_%s.json" % (case_id, mode))).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if problems:
        for p in problems:
            print("  [FAIL] %s/%s: %s" % (case_id, mode, p))
        return 1
    if args.signature_out:
        out_path = Path(args.signature_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"".join((1).to_bytes(8, "big") for _ in exp))
    print("  PASS %s/%s（%d 槽）" % (case_id, mode, len(exp)))
    return 0


def selfcheck():
    problems = []
    print("=" * 72)
    print("check_pmem_rtl --selfcheck（不启动仿真器）")
    print("=" * 72)
    for path, what in ((SRC, "case 源"), (LDS, "RTL 链接布局")):
        if path.is_file():
            print("  PASS  %s: %s" % (what, path.relative_to(_REPO)))
        else:
            problems.append("缺 %s: %s" % (what, path))
    try:
        tools = _toolchain()
    except SetupError as exc:
        print("  FAIL  工具链: %s" % exc)
        return 1
    work = Path(tempfile.mkdtemp(prefix="pmem-dma-rtl-selfcheck-"))
    try:
        for case_id, modes in CASES.items():
            for mode in modes:
                _, exp = build(mode, tools, work)
                want = SLOTS[case_id]
                if len(exp) != want:
                    problems.append("%s/%s: 期望 %d 槽 ≠ %d"
                                    % (case_id, mode, len(exp), want))
                else:
                    print("  PASS  %s/%s 期望 %d 槽（现场派生）"
                          % (case_id, mode, len(exp)))
    except SetupError as exc:
        problems.append(str(exc))
    for p in problems:
        print("  [FAIL] %s" % p)
    print("selfcheck: %s" % ("PASS" if not problems else "FAIL"))
    return 0 if not problems else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--sim")
    ap.add_argument("--mode", default=None)
    ap.add_argument("--work-dir")
    ap.add_argument("--signature-out")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for case_id, modes in CASES.items():
            print("%s %s" % (case_id, ",".join(modes)))
        return 0
    if args.selfcheck:
        return selfcheck()
    if not args.only or not args.sim:
        ap.error("--only 和 --sim 必填")
    if args.only not in CASES:
        ap.error("未知 case %r（允许 %s）" % (args.only, sorted(CASES)))
    modes = CASES[args.only]
    mode = args.mode or modes[0]
    if mode not in modes:
        ap.error("%s 不允许 --mode %s（允许 %s）"
                 % (args.only, mode, list(modes)))
    try:
        tools = _toolchain()
    except SetupError as exc:
        print("check_pmem_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2
    # 仿真器以 work 为 cwd 启动 ⇒ 相对路径会解析到别处：统一成绝对路径。
    work = (Path(args.work_dir).resolve() if args.work_dir
            else Path(tempfile.mkdtemp(prefix="pmem-dma-rtl-run-")).resolve())
    work.mkdir(parents=True, exist_ok=True)
    return run_case(args.only, mode, args, tools, work)


if __name__ == "__main__":
    sys.exit(main())
