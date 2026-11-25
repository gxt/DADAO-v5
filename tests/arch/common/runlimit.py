#!/usr/bin/env python3
"""`tests/arch/common/runlimit.py` — 失败形态上限（`ISS-522`，`m16-testcases-020/021`）。

`tests/arch` 的载体都是「guest 挂住 ⇒ 只能等超时」的形态：一次失败若放任
`-d cpu` 全量 dump，会在 60 s 内写出约 11 GiB（tmpfs 16 G 被打满）。本模块是
**唯一实现**，约束三件事：

  * **短超时**：缺省 10 s；`DADAO_ARCH_TIMEOUT` 放宽。非法值显式抛
    `RunLimitError`（不静默回退）。
  * **dump 上限**：缺省 128 MiB；`DADAO_ARCH_DUMP_MAX` 调整。运行中轮询
    dump 大小，越界即 `killpg` 终止（`dump_capped`）；子进程同时设
    `RLIMIT_FSIZE`（`ulimit -f`，内核硬上限）兜底。
  * **孤儿清理**：`run()` 用 `start_new_session=True` 起子进程，结束/超时/越界
    一律 `killpg(SIGTERM→SIGKILL)`，覆盖 gem5 shim 这类「再起一级子进程」的
    载体；外部强杀驱动时由证据脚本另加 `ulimit -f` + `killpg` 兜底。
  * **失败后截断**：`finish_dump()` 把超限 dump 截到 1 MiB 并追加一行标记，
    供 `-d cpu` 解析器读到「已截断」而不是被超大文件拖死。

退出码约定（`Result.rc`）：超时 `-2`、dump 越界 `-3`，其余为子进程真实退出码
（负数是信号）。调用方必须按 `timed_out` / `dump_capped` 分别报原因。
"""

from __future__ import annotations

import os
import resource
import signal
import subprocess
import tempfile
import time

DEFAULT_TIMEOUT = 10                     # 秒（失败路径短时限）
DEFAULT_DUMP_MAX = 128 * 1024 * 1024     # 字节（`-d cpu` dump 上限）
FINISH_DUMP_KEEP = 1024 * 1024           # 字节（失败后保留的 dump 前缀）
TIMEOUT_ENV = "DADAO_ARCH_TIMEOUT"
DUMP_ENV = "DADAO_ARCH_DUMP_MAX"
POLL_INTERVAL = 0.05                     # 秒（dump 大小轮询）
KILL_GRACE = 0.5                         # 秒（SIGTERM → SIGKILL 间隔）

RC_TIMEOUT = -2
RC_DUMP_CAPPED = -3


class RunLimitError(ValueError):
    """非法 `DADAO_ARCH_*` 环境值：显式失败，不静默回退。"""


def _positive_env(name, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw, 0)
    except ValueError:
        raise RunLimitError(
            "%s=%r 不是整数（期望正整数；超时单位 s，dump 上限单位 B）"
            % (name, raw))
    if value <= 0:
        raise RunLimitError("%s=%r 必须 > 0" % (name, raw))
    return value


def timeout(fallback=None):
    """超时秒数：`DADAO_ARCH_TIMEOUT`，否则 `fallback`，否则 `DEFAULT_TIMEOUT`。"""
    return _positive_env(
        TIMEOUT_ENV, DEFAULT_TIMEOUT if fallback is None else fallback)


def max_dump_bytes():
    """`-d cpu` dump 上限字节数：`DADAO_ARCH_DUMP_MAX`。"""
    return _positive_env(DUMP_ENV, DEFAULT_DUMP_MAX)


_default_timeout = timeout            # `run(timeout=...)` 形参遮蔽模块函数


def dfilter(start, end):
    """QEMU `-dfilter` 参数：只 dump `[start, end)` 窗口内的执行。"""
    if end <= start:
        raise RunLimitError(
            "dfilter: end (0x%x) 必须大于 start (0x%x)" % (end, start))
    return ["-dfilter", "0x%x+0x%x" % (start, end - start)]


class Result:
    """一次受限运行的结果（`rc` 已按约定编码，见模块文档）。"""

    __slots__ = ("rc", "output", "timed_out", "dump_capped", "dump_bytes",
                 "timeout", "elapsed", "cmdline")

    def __init__(self):
        self.rc = None
        self.output = b""
        self.timed_out = False
        self.dump_capped = False
        self.dump_bytes = 0
        self.timeout = 0
        self.elapsed = 0.0
        self.cmdline = ""


def _signal_group(proc, sig):
    """对本进程组发信号（`start_new_session=True` ⇒ pgid = 子进程 pid）。"""
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError):
        try:
            proc.send_signal(sig)
        except (ProcessLookupError, PermissionError):
            pass


def _terminate(proc):
    """SIGTERM 整个进程组，宽限后 SIGKILL；再 wait 回收直接子进程。"""
    _signal_group(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        pass
    _signal_group(proc, signal.SIGKILL)
    try:
        proc.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        pass
    # 直接子进程已退出时组内仍可能有孙进程（gem5 shim）⇒ 再补一刀 SIGKILL。
    _signal_group(proc, signal.SIGKILL)


def _dump_size(path):
    try:
        return os.stat(path).st_size
    except OSError:
        return 0


def _set_fsize_limit(limit):
    """子进程侧 `RLIMIT_FSIZE`（`ulimit -f`）：内核硬上限兜底。"""
    def _apply():
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
        except (ValueError, OSError):
            pass
    return _apply


def run(cmd, timeout=None, dump=None, cwd=None):
    """跑 `cmd`，施加超时 / dump 上限 / 进程组清理，返回 `Result`。

    `dump` 非空时视作 QEMU `-D` 的文件：轮询其大小，越界即终止并置
    `dump_capped`；`timeout` 为 `None` 时取 `timeout()`。
    """
    limit_s = timeout if timeout is not None else _default_timeout()
    cap = max_dump_bytes() if dump else 0
    res = Result()
    res.timeout = limit_s
    res.cmdline = " ".join(str(x) for x in cmd)
    out = tempfile.TemporaryFile()
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=out,
                  stderr=subprocess.STDOUT, cwd=cwd,
                  start_new_session=True)
    if cap:
        # 内核上限略高于轮询上限，让轮询先命中（保留 fail 形态可判）。
        kwargs["preexec_fn"] = _set_fsize_limit(cap + FINISH_DUMP_KEEP)
    started = time.monotonic()
    proc = subprocess.Popen([str(x) for x in cmd], **kwargs)
    try:
        while True:
            rc = proc.poll()
            if rc is not None:
                res.rc = rc
                break
            if dump:
                res.dump_bytes = max(res.dump_bytes, _dump_size(dump))
                if res.dump_bytes > cap:
                    res.dump_capped = True
                    _terminate(proc)
                    res.rc = RC_DUMP_CAPPED
                    break
            if time.monotonic() - started >= limit_s:
                res.timed_out = True
                _terminate(proc)
                res.rc = RC_TIMEOUT
                break
            time.sleep(POLL_INTERVAL)
    finally:
        res.elapsed = time.monotonic() - started
        # 正常退出也要清掉组内残留（shim 起的下一级进程）。
        if proc.poll() is not None:
            _signal_group(proc, signal.SIGKILL)
        if dump:
            res.dump_bytes = max(res.dump_bytes, _dump_size(dump))
            if res.dump_bytes > cap and not res.timed_out:
                # 内核 `RLIMIT_FSIZE` 先杀（rc = -SIGXFSZ）时同样按越界报。
                res.dump_capped = True
                res.rc = RC_DUMP_CAPPED
        out.seek(0)
        res.output = out.read()
        out.close()
    return res


def finish_dump(path, res):
    """失败后截断 dump 到 `FINISH_DUMP_KEEP`，并记录实际字节数。"""
    if not path:
        return
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    res.dump_bytes = max(res.dump_bytes, size)
    if size <= FINISH_DUMP_KEEP:
        return
    with open(path, "r+b") as fh:
        fh.truncate(FINISH_DUMP_KEEP)
    with open(path, "ab") as fh:
        fh.write(b"\n[runlimit] `-d cpu` dump truncated: %d B -> %d B\n"
                 % (size, FINISH_DUMP_KEEP))


__all__ = ["DEFAULT_TIMEOUT", "DEFAULT_DUMP_MAX", "FINISH_DUMP_KEEP",
           "RC_TIMEOUT", "RC_DUMP_CAPPED", "RunLimitError", "Result",
           "timeout", "max_dump_bytes", "dfilter", "run", "finish_dump"]
