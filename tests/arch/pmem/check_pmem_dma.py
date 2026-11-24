#!/usr/bin/env python3
"""`tests/arch/pmem/check_pmem_dma.py` — cfx32 DMA 完成中断 + 同界多源的
QEMU/gem5 驱动（`m16-testcases-014`）。

载体：`tests/arch/pmem/pmem_dma.S`（与 RTL 承载**同一份** case 源）。QEMU/gem5
用 flat bin 从 `ENTRY=0x0010_0000` 装入；RTL 用 `pmem_dma.lds` 的
`0xffff_ff01_0100`。两者都通过 `--defsym` 覆盖地址，槽序完全一致。

判据（Independent oracle）：`pmem_oracle.py` 从 `spec/DADAO-12
§4.6/§4.9/§5.1/§5.4`、`ADR-0061`、`contract-see`、`contracts/opcodes.yaml`
现场派生；`cause_ip` 按本 ELF 符号精确断言。驱动把原始签名流过 oracle 后，
向 `--signature-out` 写**归一化**签名（每槽 1 = 该槽通过本平台 oracle），供
`run_arch.py` 做跨平台逐槽比较（QEMU/RTL 的原始地址不同，不能直接比）。

用例：
  * `arch-pmem-001`（hmon/hypv，55 槽）：DMA / 状态 / 一致性 clean+invalidate /
    ILLI / 捕获 / `escape imms18=2 ⇒ CFXESC` / 同界多源一次进入 / ack / 覆盖；
  * `arch-pmem-002`（smon/supv、umon/user，10 槽）：DMA 在 hypv 启动、完成落在
    目标模式，各写自己 monitor 的掩码行 → pending → 放行 → 投递。

用法：
  check_pmem_dma.py --only arch-pmem-001 --qemu PATH --mode hmon \\
      [--work-dir DIR] [--signature-out PATH] [--bootrom PATH] \\
      [--cache-model on|off] [--cfx-access LIST] [--timeout N] \\
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
_ARCH = _HERE.parents[1]               # tests/arch
_REPO = _HERE.parents[3]               # 仓库根

for _sub in (("tests", "shared"), ("tests", "arch"), ("tools", "testcases", "lib"),
             ("tools", "infra"), ("tests", "arch", "pmem")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

import paths as _paths                     # noqa: E402
import pmem_oracle as oracle               # noqa: E402

CASES = {"arch-pmem-001": ("hmon",), "arch-pmem-002": ("smon", "umon")}
MODE_CODE = {"hmon": 3, "smon": 2, "umon": 0}
ENTRY = 0x00100000
SIG_BUF = 0x00105000
EXITB = 0x00105800
LDS = _HERE.with_name("pmem_dma_qemu.lds")
SRC = _HERE.with_name("pmem_dma.S")
SLOTS = {"arch-pmem-001": 55, "arch-pmem-002": 10}
TIMEOUT = 180


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
    obj = work / ("pmem_dma_%s.o" % mode)
    cmd = [str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
           "-filetype=obj", "-I", str(_REPO),
           "-defsym", "TMODE=%d" % code,
           "-defsym", "ENTRY=%#x" % ENTRY,
           "-defsym", "SIG_BUF=%#x" % SIG_BUF,
           "-defsym", "EXITB=%#x" % EXITB]
    if mode == "umon":
        # step5 页表 PTE0 的 HSJU=0xC（U=0）；把镜像所在超页置 U=1。
        cmd += ["-defsym", "PTW_UMAP=1"]
    rc, out = _run(cmd + [str(SRC), "-o", str(obj)], 60)
    if rc != 0:
        raise SetupError("llvm-mc %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-800:]))
    elf = work / ("pmem_dma_%s.elf" % mode)
    rc, out = _run([str(tools["ld.lld"]), "-T", str(LDS), str(obj),
                    "-o", str(elf)], 60)
    if rc != 0:
        raise SetupError("ld.lld %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-800:]))
    image = work / ("pmem_dma_%s.bin" % mode)
    rc, out = _run([str(tools["llvm-objcopy"]), "-O", "binary", str(elf),
                    str(image)], 60)
    if rc != 0:
        raise SetupError("llvm-objcopy %s 失败 rc=%d: %s"
                         % (mode, rc, out.decode("utf-8", "replace")[-800:]))
    syms = oracle.elf_symbols(str(tools["llvm-nm"]), str(elf))
    exp = oracle.expected(str(_REPO), code, syms)
    return image, elf, exp, syms


def _engine(engine):
    return ([sys.executable, str(engine)] if str(engine).endswith(".py")
            else [str(engine)])


def run_case(case_id, mode, args, tools, work):
    image, elf, exp, syms = build(mode, tools, work)
    console = work / ("%s_%s.out" % (case_id, mode))
    if console.exists():
        console.unlink()
    machine = "kaiwu-vast,bootrom-image=" + str(tools["bootrom"])
    if args.cache_model == "on":
        machine += ",cache-model=on"
    cmd = _engine(args.qemu) + [
        "-machine", machine,
        "-kernel", str(image),
        "-semihosting-config", "enable=on,target=native,chardev=semi",
        "-chardev", "file,id=semi,path=" + str(console),
        "-display", "none", "-nographic"]
    if not str(args.qemu).endswith(".py"):
        # 逐 cycle 的 timer/DMA 竞态需要确定的虚拟时间（RTL 侧本来就是确定时钟）。
        cmd += ["-icount", "shift=0,align=off,sleep=off"]
    rc, out = _run(cmd, args.timeout)
    problems = []
    if rc == -2:
        problems.append("模拟器超时（%ds）" % args.timeout)
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
    print("check_pmem_dma --selfcheck（不启动模拟器）")
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
    work = Path(tempfile.mkdtemp(prefix="pmem-dma-selfcheck-"))
    try:
        for case_id, modes in CASES.items():
            for mode in modes:
                _, _, exp, _ = build(mode, tools, work)
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
    ap.add_argument("--qemu")
    ap.add_argument("--mode", default=None)
    ap.add_argument("--work-dir")
    ap.add_argument("--signature-out")
    ap.add_argument("--bootrom", default=None)
    # `run_arch` 的 env 载体参数；本例用独立 flat bin，`--cfx-access` 不需要
    # 权限准备（显式接受后忽略，不静默改变语义）。
    ap.add_argument("--cfx-access", default=None)
    ap.add_argument("--cache-model", default="on", choices=("on", "off"))
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
    if not args.only or not args.qemu:
        ap.error("--only 和 --qemu 必填")
    if args.only not in CASES:
        ap.error("未知 case %r（允许 %s）" % (args.only, sorted(CASES)))
    modes = CASES[args.only]
    mode = args.mode or modes[0]
    if mode not in modes:
        ap.error("%s 不允许 --mode %s（允许 %s）"
                 % (args.only, mode, list(modes)))
    try:
        tools = _toolchain(args.bootrom)
    except SetupError as exc:
        print("check_pmem_dma: SETUP: %s" % exc, file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir
            else Path(tempfile.mkdtemp(prefix="pmem-dma-run-")))
    work.mkdir(parents=True, exist_ok=True)
    return run_case(args.only, mode, args, tools, work)


if __name__ == "__main__":
    sys.exit(main())
