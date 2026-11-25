#!/usr/bin/env python3
"""`tests/arch/common/runlimit.py` — arch 载体的失败形态上限（`ISS-522`）。

**问题形态**：arch 载体（QEMU/gem5）在「未装载当前模式监视器」等异常路径上
拿不到 semihosting `SYS_EXIT`，模拟器会一直跑到超时；同时 `-d cpu` 把每条
指令都写进 dump。实测本机 QEMU 约 **200 MB/s**，60 s 就是 ~12 GB（`ISS-522`
记录 11.7 GB / tmpfs 16 G 被打满）。

**本模块只提供一处机制**（所有 arch carrier 共用，避免各驱动各写一份）：

  * **短时限**：默认 `DEFAULT_TIMEOUT` = 10 s，`DADAO_ARCH_TIMEOUT` 可放宽
    （调试长用例时用；非法值**显式失败**，不静默回退）；
  * **dump 上限**：`-d cpu` 的输出文件在**运行中**按 `DADAO_ARCH_DUMP_MAX`
    （默认 128 MiB）实时监视，超限立刻终止进程 ⇒ 判据在写满磁盘**之前**
    结束，不是等进程自己停；子进程另设 `RLIMIT_FSIZE`（= `ulimit -f`，略高于
    轮询上限）作内核硬上限：**证据脚本被外部强杀、模拟器成孤儿时仍被截住**
    （`m16-testcases-021` 并入）；
  * **失败即截断**：超时/超限/非零退出后把 dump 截断到头部 `HEAD_BYTES`
    （保留最小失败现场），通过时保留完整 dump 作证据。

`rc` 约定（沿用各驱动既有约定，新增 `-3`）：`-2` = 超时、`-3` = dump 超限
（进程已被终止）；其余 = 进程自身退出码。

用法：

    res = runlimit.run(cmd, timeout=runlimit.timeout(TIMEOUT), dump=cpu_log,
                       cwd=str(work))
    if res.timed_out:
        problems.append("模拟器超时（%ds）" % res.timeout)
    elif res.dump_capped:
        problems.append("`-d cpu` dump %d B 超过上限 %d B（已终止并截断）"
                        % (res.dump_bytes, runlimit.max_dump_bytes()))
    elif res.rc != 0:
        problems.append("模拟器退出码 %d" % res.rc)
    ...
    runlimit.finish_dump(cpu_log, res)      # 读完 MODE 观测之后调用
"""
from __future__ import annotations

import os
import resource
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT = 10            # s：失败路径不再等 60 s
TIMEOUT_ENV = "DADAO_ARCH_TIMEOUT"
DEFAULT_MAX_DUMP = 128 << 20    # B：`-d cpu` dump 上限
DUMP_ENV = "DADAO_ARCH_DUMP_MAX"
HEAD_BYTES = 1 << 20            # B：失败后保留的 dump 头部
POLL_SECONDS = 0.05             # dump 大小/时限的检查间隔
KILL_GRACE = 3.0                # SIGTERM 后等多久再 SIGKILL

RC_TIMEOUT = -2
RC_DUMP_CAPPED = -3


class RunLimitError(ValueError):
    """时限/上限的环境变量非法（显式失败，不静默用缺省顶替）。"""


def _env_int(name, default, minimum):
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw, 0)
    except ValueError:
        raise RunLimitError("%s=%r 不是整数" % (name, raw))
    if value < minimum:
        raise RunLimitError("%s=%r 必须 ≥ %d" % (name, raw, minimum))
    return value


def timeout(default=DEFAULT_TIMEOUT):
    """本次运行的模拟器时限（秒）；`DADAO_ARCH_TIMEOUT` 放宽。"""
    return _env_int(TIMEOUT_ENV, default, 1)


def max_dump_bytes():
    """`-d cpu` dump 的字节上限；`DADAO_ARCH_DUMP_MAX` 调整。"""
    return _env_int(DUMP_ENV, DEFAULT_MAX_DUMP, 1)


def dfilter(lo, hi):
    """`-dfilter` 参数（观测过滤，不影响 guest 语义）；窗口为空 ⇒ 显式失败。"""
    if hi <= lo:
        raise RunLimitError("-dfilter 窗口为空: [%#x, %#x)" % (lo, hi))
    return ["-dfilter", "0x%x+0x%x" % (lo, hi - lo)]


@dataclass
class RunResult:
    rc: int
    output: bytes
    timed_out: bool
    dump_capped: bool
    dump_bytes: int
    timeout: int


def _terminate(proc):
    """整组终止（shim 会再起 gem5；只杀直接子进程会留下孤儿继续写 dump）。"""
    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        return
    for sig, grace in ((signal.SIGTERM, KILL_GRACE), (signal.SIGKILL, 0.0)):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            continue


def _set_fsize_limit(limit):
    """子进程侧 `RLIMIT_FSIZE`（`ulimit -f`）：孤儿进程的内核硬上限（ISS-522）。"""
    def _apply():
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
        except (ValueError, OSError):
            pass
    return _apply


def run(cmd, *, timeout, dump=None, env=None, cwd=None):
    """跑一条模拟器命令，带时限与 dump 上限；返回 `RunResult`。"""
    timeout = int(timeout)
    if timeout <= 0:
        raise RunLimitError("timeout 必须 > 0（收到 %r）" % timeout)
    dump_path = Path(dump) if dump is not None else None
    if dump_path is not None:
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        if dump_path.exists():
            dump_path.unlink()
    limit = max_dump_bytes()
    timed_out = False
    dump_capped = False
    # 内核上限略高于轮询上限：让轮询先命中，保留 FAIL 形态可判。
    preexec = (_set_fsize_limit(limit + HEAD_BYTES)
               if dump_path is not None else None)
    with tempfile.TemporaryFile() as out_file:
        proc = subprocess.Popen(cmd, stdout=out_file, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env, cwd=cwd,
                                start_new_session=True, preexec_fn=preexec)
        deadline = time.monotonic() + timeout
        while True:
            if proc.poll() is not None:
                break
            if (dump_path is not None and dump_path.is_file()
                    and dump_path.stat().st_size > limit):
                dump_capped = True
                _terminate(proc)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                _terminate(proc)
                break
            time.sleep(POLL_SECONDS)
        proc.wait()
        out_file.seek(0)
        output = out_file.read()
    rc = proc.returncode
    dump_bytes = (dump_path.stat().st_size
                  if dump_path is not None and dump_path.is_file() else 0)
    if dump_capped:
        rc = RC_DUMP_CAPPED
    elif timed_out:
        rc = RC_TIMEOUT
    return RunResult(rc=rc, output=output, timed_out=timed_out,
                     dump_capped=dump_capped, dump_bytes=dump_bytes,
                     timeout=timeout)


def finish_dump(path, res, head=HEAD_BYTES):
    """失败/超限时把 dump 截断到头部；通过的运行保留完整 dump（证据）。"""
    if path is None:
        return
    p = Path(path)
    if not p.is_file():
        return
    if not (res.timed_out or res.dump_capped or res.rc != 0):
        return
    if p.stat().st_size > head:
        with p.open("r+b") as stream:
            stream.truncate(head)
