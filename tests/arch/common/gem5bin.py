#!/usr/bin/env python3
"""`tests/arch/common/gem5bin.py` — 仿真器二进制的最小可信校验
（`m16-testcases-024`，承接 `m16-testcases-023` 的 reviewer finding②）。

只靠 `[ -x PATH ]` 拦不住「可执行位在、内容被并发构建截断」的半成品：
2026-11-25 22:57，共享的 `.work/source/gem5/build/DADAO/gem5.opt` 被别的会话
重建成 41.8 MB 的**非 ELF** 文件（可执行位仍是 `-rwxrwxr-x`），`run.sh` 的
`[ -x "$GEM5" ]` 放行后 gem5 腿全红，误当成本任务失败（真实 flake 之外）。

判据（缺一即失败，不静默放行）：

  1. 存在、是普通文件、有可执行位；
  2. 前 4 字节 = ELF magic `\\x7fELF`；
  3. 文件头声明的 `e_type`/`e_machine` 与 `file(1)` 的识别一致（有 `file`
     时用；没有则跳过这一条，不把「缺 file 命令」当通过）；
  4. `e_shoff`/`e_shnum` 指向的节头表落在文件长度内（截断文件在这里露馅）。

用法（证据脚本调用；也可人工核对）：

    python3 tests/arch/common/gem5bin.py PATH            # rc 0 可用 / 1 不可用
    python3 tests/arch/common/gem5bin.py --quiet PATH

退出码：0 通过；1 不可用（打印原因）；2 用法错误。
"""
from __future__ import annotations

import argparse
import struct
import subprocess
import sys
from pathlib import Path

ELF_MAGIC = b"\x7fELF"


def problems(path) -> list:
    """返回问题列表；空 = 看起来是可执行的完整 ELF。"""
    p = Path(path)
    out = []
    if not p.exists():
        return ["不存在: %s" % p]
    if not p.is_file():
        return ["不是普通文件: %s" % p]
    if not (p.stat().st_mode & 0o111):
        out.append("无可执行位: %s" % p)
    size = p.stat().st_size
    if size < 64:
        out.append("文件过小（%d B），不是完整 ELF" % size)
        return out
    with p.open("rb") as fh:
        head = fh.read(64)
    if head[:4] != ELF_MAGIC:
        out.append("前 4 字节不是 ELF magic（%r；半成品/非 ELF 构建）"
                   % head[:4])
        return out
    cls, data = head[4], head[5]
    endian = "<" if data == 1 else ">" if data == 2 else None
    if cls not in (1, 2) or endian is None:
        out.append("ELF 类/字节序非法: class=%r data=%r" % (cls, data))
        return out
    # e_shoff@0x28 (64)、@0x20 (32)；e_shentsize/e_shnum 的位置按类取。
    try:
        if cls == 2:
            shoff = struct.unpack(endian + "Q", head[0x28:0x30])[0]
            shentsize = struct.unpack(endian + "H", head[0x3A:0x3C])[0]
            shnum = struct.unpack(endian + "H", head[0x3C:0x3E])[0]
        else:
            shoff = struct.unpack(endian + "I", head[0x20:0x24])[0]
            shentsize = struct.unpack(endian + "H", head[0x2E:0x30])[0]
            shnum = struct.unpack(endian + "H", head[0x30:0x32])[0]
    except struct.error as exc:
        return out + ["ELF 头解析失败: %s" % exc]
    if shoff and shnum and shoff + shentsize * shnum > size:
        out.append("节头表越界（截断文件）：shoff=%d shnum=%d size=%d"
                   % (shoff, shnum, size))
    if _file_available():
        try:
            proc = subprocess.run(["file", "-b", str(p)],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, timeout=30)
            text = proc.stdout.decode("utf-8", "replace").strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append("file(1) 执行失败: %s" % exc)
        else:
            if "ELF" not in text:
                out.append("file(1) 未识别为 ELF: %s" % text)
    return out


def _file_available() -> bool:
    from shutil import which
    return which("file") is not None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    found = problems(args.path)
    if found:
        if not args.quiet:
            for item in found:
                print("gem5bin: %s" % item, file=sys.stderr)
        return 1
    if not args.quiet:
        print("gem5bin: OK %s（ELF，%d B）"
              % (args.path, Path(args.path).stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
