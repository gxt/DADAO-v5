#!/usr/bin/env python3
"""`tests/arch/hart/check_escape_rtl.py` — RTL `escape` 判据探针
（`m18-chipyard-002`）。

载体：`tests/arch/hart/escape_escalation.S` + `cfx15.lds`
（`WumingVastConfig`，`+loadmem` 到 `0xffffff010100`）。探针以 `SYS_EXIT 0`
表示全部判据通过（rc11 整字恢复 / 升权 `CFXESC` / 未实现目标 `CFXESC` /
`imms18 != 0 ⇒ ILLI`），非零退出码即失败的检查点（见 `.S` 头部）。

本脚本只负责汇编/链接/启动仿真器并返回仿真器**自身**退出码；不做期望值推导
（判据在 `.S` 内联，每步失败都有独立退出码）。

用法：
  check_escape_rtl.py --sim PATH [--work-dir DIR] [--timeout N]
  check_escape_rtl.py --selfcheck
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
for _sub in (("tests", "shared"), ("tools", "infra")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)

import paths as _paths  # noqa: E402

SRC = _HERE.with_name("escape_escalation.S")
LDS = _HERE.with_name("cfx15.lds")
TIMEOUT = 600


class SetupError(RuntimeError):
    pass


def _toolchain():
    bin_dir = _paths.host_toolchain_bin()
    tools = {name: bin_dir / name for name in ("llvm-mc", "ld.lld")}
    for name, path in tools.items():
        if not path.is_file():
            raise SetupError("缺 %s: %s（make install-host）" % (name, path))
    return tools


def _run(cmd, timeout, cwd=None):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout,
                          stdin=subprocess.DEVNULL, cwd=cwd)
    return proc.returncode, proc.stdout


def build(tools, work):
    obj = work / "escape_escalation.o"
    rc, out = _run([str(tools["llvm-mc"]), "--triple=dadao-unknown-elf",
                    "-filetype=obj", "-I", str(_REPO),
                    str(SRC), "-o", str(obj)], 60)
    if rc != 0:
        raise SetupError("llvm-mc 失败 rc=%d: %s"
                         % (rc, out.decode("utf-8", "replace")[-800:]))
    elf = work / "escape_escalation.elf"
    rc, out = _run([str(tools["ld.lld"]), "-T", str(LDS), str(obj),
                    "-o", str(elf)], 60)
    if rc != 0:
        raise SetupError("ld.lld 失败 rc=%d: %s"
                         % (rc, out.decode("utf-8", "replace")[-800:]))
    return elf


def selfcheck():
    ok = True
    for path, what in ((SRC, "case 源"), (LDS, "链接布局")):
        if path.is_file():
            print("  PASS  %s: %s" % (what, path.relative_to(_REPO)))
        else:
            print("  FAIL  %s: %s" % (what, path))
            ok = False
    try:
        tools = _toolchain()
    except SetupError as exc:
        print("  FAIL  工具链: %s" % exc)
        return 1
    work = Path(tempfile.mkdtemp(prefix="escape-rtl-selfcheck-"))
    try:
        build(tools, work)
        print("  PASS  assemble/link（%s）" % work)
    except SetupError as exc:
        print("  FAIL  %s" % exc)
        ok = False
    print("selfcheck: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim")
    ap.add_argument("--work-dir")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    if args.selfcheck:
        return selfcheck()
    if not args.sim:
        ap.error("--sim 必填")
    try:
        tools = _toolchain()
    except SetupError as exc:
        print("check_escape_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2
    work = (Path(args.work_dir) if args.work_dir
            else Path(tempfile.mkdtemp(prefix="escape-rtl-run-")))
    work.mkdir(parents=True, exist_ok=True)
    try:
        elf = build(tools, work)
    except SetupError as exc:
        print("check_escape_rtl: SETUP: %s" % exc, file=sys.stderr)
        return 2
    console = work / "escape_escalation.out"
    if console.exists():
        console.unlink()
    cmd = [str(Path(args.sim).resolve()), "+permissive", "+verbose",
           "+loadmem=" + str(elf), "+semiout=" + str(console),
           "+max-cycles=2000000", "+permissive-off", "none"]
    try:
        rc, out = _run(cmd, args.timeout, cwd=str(work))
    except subprocess.TimeoutExpired as exc:
        print("check_escape_rtl: RTL 超时（%ds）" % args.timeout,
              file=sys.stderr)
        sys.stderr.buffer.write((exc.stdout or b"")[-2000:])
        return 1
    (work / "run.log").write_bytes(out)
    if rc != 0:
        print("check_escape_rtl: FAIL（仿真器退出码 %d，见 %s）"
              % (rc, work / "run.log"), file=sys.stderr)
        sys.stderr.buffer.write(out[-2000:])
        return 1
    print("  PASS escape_escalation（SYS_EXIT 0）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
