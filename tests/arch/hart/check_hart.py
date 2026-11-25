#!/usr/bin/env python3
"""`tests/arch/hart/check_hart.py` — `cfx_hart`（cfxha 15）QEMU/gem5 驱动
（`m16-testcases-013`）。

载体：`tests/arch/hart/cfx15.S`（与 RTL 承载**同一份** case 源）。QEMU 用
flat bin 从 `ENTRY=0x0010_0000` 装入；RTL 用 `cfx15.lds` 的
`0xffff_ff01_0100`。两者都通过 `--defsym` 覆盖地址，槽序完全一致。

判据（Independent oracle）：`check_cfx15.py` 从 `spec/DADAO-12 §4.7/§5.4`、
`ADR-0061`、`contract-see`、`contracts/opcodes.yaml` 现场派生；`cause_ip`
按本 ELF 符号精确断言。驱动把原始签名流过 oracle 后，向
`--signature-out` 写**归一化**签名（每槽 1 = 该槽通过本平台 oracle），
供 `run_arch.py` 做跨平台逐槽比较（QEMU/RTL 的原始地址不同，不能直接比）。

用例：
  * `arch-hart-001`（hmon/hypv，80 槽）：cg8 寄存器面 + 保留/非法编码 +
    屏蔽→pending→放行 + 捕获/覆盖/RO/`escape` + jump 目标精确点；
  * `arch-hart-002`（smon/supv、umon/user，40 槽）：同一捕获/覆盖/`escape`/
    jump 流程，掩码取当前模式 monitor（cfx_smon / cfx_umon）。

用法：
  check_hart.py --only arch-hart-001 --qemu PATH --mode hmon \\
      [--work-dir DIR] [--signature-out PATH] [--bootrom PATH] \\
      [--timeout N] [--selfcheck] [--list]

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
_ARCH = _HERE.parents[1]               # tests/arch
_REPO = _HERE.parents[3]               # 仓库根

for _sub in (("tests", "shared"), ("tests", "arch"), ("tools", "testcases", "lib"),
             ("tools", "infra")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)

import paths as _paths                     # noqa: E402
import check_cfx15 as oracle               # noqa: E402
from common import runlimit                # noqa: E402

CASES = {"arch-hart-001": ("hmon",), "arch-hart-002": ("smon", "umon")}
MODE_CODE = {"hmon": 3, "smon": 2, "umon": 0}
ENTRY = 0x00100000
SIG_BUF = 0x00105000
EXITB = 0x00105800
HMON_BASE = 0x00108000
LDS = _HERE.with_name("cfx15_qemu.lds")
SRC = _HERE.with_name("cfx15.S")
TIMEOUT = runlimit.DEFAULT_TIMEOUT   # 失败路径短时限（ISS-522）


class SetupError(RuntimeError):
    pass


def _toolchain(bootrom_override=None):
    bin_dir = _paths.host_toolchain_bin()
    tools = {name: bin_dir / name
             for name in ("llvm-mc", "llvm-objcopy", "ld.lld", "llvm-nm")}
    for name, path in tools.items():
        if not path.is_file():
            raise SetupError("缺 %s: %s（make install-host）" % (name, path))
    bootrom = (Path(bootrom_override) if bootrom_override
               else _paths.test_artifacts_dir() / "bootrom" / "step5"
               / "bootrom_step5.bin").resolve()
    if not bootrom.is_file():
        raise SetupError("缺 Vast step5 BootROM: %s（make build-bootrom）"
                         % bootrom)
    tools["bootrom"] = bootrom
    return tools


def _run(cmd, timeout):
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        return -2, exc.stdout or b""


def build(mode, tools, work):
    code = MODE_CODE[mode]
    obj = work / ("cfx15_%s.o" % mode)
    cmd = [str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
           "-filetype=obj", "-I", str(_REPO),
           "-defsym", "TMODE=%d" % code,
           "-defsym", "ENTRY=%#x" % ENTRY,
           "-defsym", "SIG_BUF=%#x" % SIG_BUF,
           "-defsym", "EXITB=%#x" % EXITB,
           "-defsym", "HMON_BASE=%#x" % HMON_BASE]
    if mode == "umon":
        # QEMU step5 页表在 PA 0；把镜像所在超页置 U=1（仅 QEMU 承载）。
        cmd += ["-defsym", "PTW_UMAP=1"]
    rc, out = _run(cmd + [str(SRC), "-o", str(obj)], 60)
    if rc != 0:
        raise SetupError("llvm-mc %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-500:]))
    elf = work / ("cfx15_%s.elf" % mode)
    rc, out = _run([str(tools["ld.lld"]), "-T", str(LDS), str(obj),
                    "-o", str(elf)], 60)
    if rc != 0:
        raise SetupError("ld.lld %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-500:]))
    image = work / ("cfx15_%s.bin" % mode)
    rc, out = _run([str(tools["llvm-objcopy"]), "-O", "binary", str(elf),
                    str(image)], 60)
    if rc != 0:
        raise SetupError("llvm-objcopy %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-500:]))
    syms = oracle.elf_symbols(str(tools["llvm-nm"]), str(elf))
    exp = oracle.expected(str(_REPO), code, syms)
    return image, elf, exp, syms


def _engine(engine):
    return [sys.executable, str(engine)] if str(engine).endswith(".py") else [str(engine)]


def run_case(case_id, mode, args, tools, work):
    image, elf, exp, syms = build(mode, tools, work)
    console = work / ("%s_%s.out" % (case_id, mode))
    if console.exists():
        console.unlink()
    cmd = _engine(args.qemu) + [
        "-machine", "kaiwu-vast,bootrom-image=" + str(tools["bootrom"]),
        "-kernel", str(image),
        "-semihosting-config", "enable=on,target=native,chardev=semi",
        "-chardev", "file,id=semi,path=" + str(console),
        "-display", "none", "-nographic"]
    if not str(args.qemu).endswith(".py"):
        # 逐 cycle 搜索需要确定的虚拟时间（RTL 侧本来就是确定时钟）。
        cmd += ["-icount", "shift=0,align=off,sleep=off"]
    res = runlimit.run(cmd, timeout=args.timeout)
    rc = res.rc
    problems = []
    if res.timed_out:
        problems.append("模拟器超时（%ds）" % res.timeout)
    elif rc != 0:
        problems.append("模拟器退出码 %d" % rc)
    blob = console.read_bytes() if console.is_file() else b""
    got = None
    try:
        got = oracle.unpack(blob)
    except oracle.OracleError as exc:
        problems.append("签名流: %s" % exc)
    if got is not None:
        problems += oracle.check(got, exp)
    result = {
        "case": case_id, "mode": mode, "platform": "driver",
        "engine": str(args.qemu), "elf": str(elf),
        "timeout_s": res.timeout,
        "signature_slots": got, "problems": problems,
        "verdict": "PASS" if not problems else "FAIL",
        "command": cmd,
    }
    (work / ("run_%s_%s.json" % (case_id, mode))).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if problems:
        for p in problems:
            print("  [FAIL] %s/%s: %s" % (case_id, mode, p))
        return 1
    # 归一化签名：每槽 1 = 该槽通过本平台 oracle。
    if args.signature_out:
        out_path = Path(args.signature_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"".join((1).to_bytes(8, "big") for _ in exp))
    print("  PASS %s/%s（%d 槽）" % (case_id, mode, len(exp)))
    return 0


def selfcheck():
    problems = []
    print("=" * 72)
    print("check_hart --selfcheck（不启动模拟器）")
    print("=" * 72)
    for path, what in ((SRC, "case 源"), (LDS, "QEMU 链接布局")):
        if path.is_file():
            print("  PASS  %s: %s" % (what, path.relative_to(_REPO)))
        else:
            problems.append("缺 %s: %s" % (what, path))
    try:
        tools = _toolchain()
    except SetupError as exc:
        print("  FAIL  工具链: %s" % exc)
        return 1
    work = Path(tempfile.mkdtemp(prefix="hart-selfcheck-"))
    try:
        for case_id, modes in CASES.items():
            for mode in modes:
                _, _, exp, _ = build(mode, tools, work)
                want = 80 if case_id == "arch-hart-001" else 40
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
    ap.add_argument("--qemu")
    ap.add_argument("--mode", default=None)
    ap.add_argument("--work-dir")
    ap.add_argument("--signature-out")
    ap.add_argument("--bootrom", default=None)
    # `run_arch` 的 env 载体参数；本例用独立 flat bin，不需要权限准备，显式接受
    # 后忽略（不静默改变语义）。
    ap.add_argument("--cfx-access", default=None)
    ap.add_argument("--cache-model", default=None)
    ap.add_argument("--timeout", type=int, default=None,
                    help="模拟器时限（秒）；缺省 = $DADAO_ARCH_TIMEOUT 或 %d"
                         % TIMEOUT)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for case_id, modes in CASES.items():
            print("%s %s" % (case_id, ",".join(modes)))
        return 0
    if args.selfcheck:
        return selfcheck()
    if not args.only or not args.qemu:
        ap.error("--only 和 --qemu 必填")
    if args.only not in CASES:
        ap.error("未知 case %r（允许 %s）" % (args.only, sorted(CASES)))
    modes = CASES[args.only]
    mode = args.mode or modes[0]
    if mode not in modes:
        ap.error("%s 不允许 --mode %s（允许 %s）" % (args.only, mode, list(modes)))
    if args.timeout is None:
        args.timeout = runlimit.timeout()

    try:
        tools = _toolchain(args.bootrom)
    except (SetupError, runlimit.RunLimitError) as exc:
        print("check_hart: SETUP: %s" % exc, file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir
            else Path(tempfile.mkdtemp(prefix="hart-run-")))
    work.mkdir(parents=True, exist_ok=True)
    return run_case(args.only, mode, args, tools, work)


if __name__ == "__main__":
    sys.exit(main())
