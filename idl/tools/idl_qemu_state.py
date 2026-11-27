#!/usr/bin/env python3
"""idl_qemu_state.py — 取 QEMU 的「入口态 / 末态」观测面（m17-idl-003 判据）。

口径（与 `tests/ee-tiny/run_inst_tiny.py` 的 QEMU 平台一致）：

  * 命令 = `tests/shared/signature.py` 的 `_capture_qemu` 同一组参数
    （`-M kaiwu-tiny -bios … -kernel … -semihosting-config … -chardev file`），
    只额外加 `-accel tcg,one-insn-per-tb=on -d cpu -D <log>`：每个 TB 一条
    `cpu_dump_state` 记录（TB = 一条指令）；
  * `-d cpu` 的记录是**该指令执行前**的架构状态 ⇒ 入口记录 = 应用入口（ELF
    `e_entry`）执行前，末记录 = 收尾 semihosting trap 执行前；
  * 判据是「最终架构状态」，不是逐指令 trace（trace 归 `m17-idl-004`）。

输出 JSON：

    {"entry": <state>, "last": <state>, "qemu_rc": <int>, "guest_out_hex": "…"}

`<state>` = `{ip, mode, cfx, rd[64], rb[64], rf[64], ra[64], cfx_regs}`：
`cfx_regs[cfxha]` = 该 cfx 的 `cg4 rc0–rc6`（id/version/trap/sync/async/escape/
scratch）与 `cg15 rc3`（async_mask），取自 dump 里同一条 `CFXnn …` 行
（`m17-idl-025`）。实现只读 QEMU 的文本观测面，不解释指令语义。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QEMU = REPO_ROOT / ".dadao" / "cross-toolchain" / "bin" / "qemu-system-dadao"

_BANK_RE = re.compile(r"(RD|RB|RF|RA)\[(\d\d)\]: ([0-9a-f]{16})")
# `cpu_dump_state` 的 cfx 计数/掩码行（`m17-idl-025`）：
# CFXnn ID:… VER:… TRAPN:… SYNCN:… ASYNCN:… ESCN:… SCRN:… GIM:…
_CFX_RE = re.compile(
    r"CFX(\d\d) ID:([0-9a-f]+) VER:([0-9a-f]+) TRAPN:([0-9a-f]+) "
    r"SYNCN:([0-9a-f]+) ASYNCN:([0-9a-f]+) ESCN:([0-9a-f]+) "
    r"SCRN:([0-9a-f]+) GIM:([0-9a-f]+)")
_CFX_FIELDS = ("id", "ver", "trap_num", "sync_num", "async_num",
               "escape_num", "scratch_num", "async_mask")


def parse_cfx_regs(line):
    """解析一条 `CFXnn …` 计数/掩码行；返回 `(cfxha, {field: value})` 或 None。

    字段映射：cg4 rc0 id / rc1 ver / rc2 trap_num / rc3 sync_num / rc4 async_num /
    rc5 escape_num / rc6 scratch_num；cg15 rc3 async_mask（GIM）。
    """
    m = _CFX_RE.match(line)
    if m is None:
        return None
    return int(m.group(1)), {name: int(m.group(i + 2), 16)
                             for i, name in enumerate(_CFX_FIELDS)}


def elf_entry(path):
    data = Path(path).read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 2:
        raise SystemExit("not a big-endian ELF64: %s" % path)
    (entry,) = struct.unpack_from(">Q", data, 24)
    return entry


def parse_dumps(path, entry):
    """流式解析 `-d cpu` 记录；返回 (entry_state, last_state, n_records)。"""
    entry_state = None
    last_state = None
    cur = None
    n = 0

    def finish(rec):
        nonlocal entry_state, last_state
        if rec is None:
            return
        last_state = rec
        if rec["ip"] == entry and entry_state is None:
            entry_state = dict(rec)

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("PC: "):
                finish(cur)
                n += 1
                cur = {"ip": int(line.split()[1], 16), "mode": None,
                       "cfx": None,
                       "rd": [0] * 64, "rb": [0] * 64,
                       "rf": [0] * 64, "ra": [0] * 64,
                       "cfx_regs": {}}
                continue
            if cur is None:
                continue
            if line.startswith("MODE: "):
                cur["mode"] = int(line.split()[1], 0)
            elif line.startswith("CFXCODE: "):
                cur["cfx"] = int(line.split()[1], 0)
            elif line[:2] in ("RD", "RB", "RF", "RA"):
                for bank, idx, val in _BANK_RE.findall(line):
                    cur[bank.lower()][int(idx)] = int(val, 16)
            elif line.startswith("CFX"):
                hit = parse_cfx_regs(line)
                if hit is not None:
                    cfxha, regs = hit
                    cur["cfx_regs"][cfxha] = regs
    finish(cur)
    return entry_state, last_state, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--elf", required=True)
    ap.add_argument("--qemu", default=str(DEFAULT_QEMU))
    ap.add_argument("--bootrom", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--guest-out", required=True,
                    help="semihosting chardev 输出文件（QEMU 侧签名流）")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep-log", action="store_true")
    args = ap.parse_args(argv)

    entry = elf_entry(args.elf)
    log_fd, log_path = tempfile.mkstemp(prefix="qemu-cpu-", suffix=".log")
    os.close(log_fd)
    guest_out = Path(args.guest_out)
    if guest_out.exists():
        guest_out.unlink()
    cmd = [args.qemu, "-M", "kaiwu-tiny",
           "-bios", args.bootrom, "-kernel", args.elf,
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=%s" % guest_out,
           "-nographic",
           "-accel", "tcg,one-insn-per-tb=on",
           "-d", "cpu", "-D", log_path]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=args.timeout)
        rc = proc.returncode
        if rc != 0:
            sys.stderr.write("idl_qemu_state: qemu rc=%d stderr=%s\n"
                             % (rc, proc.stderr.decode("utf-8", "replace")))
        entry_state, last_state, n = parse_dumps(log_path, entry)
        if entry_state is None:
            raise SystemExit("idl_qemu_state: entry state %#x not in dump"
                             % entry)
        if last_state is None:
            raise SystemExit("idl_qemu_state: no cpu dump records")
        blob = guest_out.read_bytes() if guest_out.exists() else b""
        out = {"elf": str(args.elf), "entry_ip": entry, "n_records": n,
               "qemu_rc": rc, "guest_out_hex": blob.hex(),
               "entry": entry_state, "last": last_state}
        Path(args.json_out).write_text(json.dumps(out), encoding="utf-8")
        print("idl_qemu_state: %s records=%d rc=%d entry=%#x last=%#x out=%dB"
              % (Path(args.elf).name, n, rc, entry_state["ip"],
                 last_state["ip"], len(blob)))
        return 0
    finally:
        if not args.keep_log:
            try:
                os.unlink(log_path)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
