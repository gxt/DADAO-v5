#!/usr/bin/env python3
"""idl_trace_common.py — 逐指令 trace 的公共口径（`m17-idl-004`）。

只放「格式与比较口径」，不放任何模型语义：

  * 记录字段与 JSONL 写法（真源说明见 `idl/docs/trace-format.md`）；
  * 寄存器写回集合的派生（四寄存器组 + RA 有效区/未定义来源规则）；
  * 大文件保护：单文件超过 `--max-bytes` 时按 `<stem>.part-NNN.jsonl` 滚动。

trace 记录（一行一个 JSON 对象）：

    {"seq": 1, "pc": "0x0000ffffff010100", "insn": "0x4c600001",
     "id": "set.zw_rwii_rd", "mn": "set.zw",
     "dst": ["rd24"], "val": ["0x0000000000000001"], "exc": null}

`dst`/`val` 是**架构寄存器的写回集合**（不是指令操作数字段）：值发生变化的寄存器
才列出，`rd0`/`rb0` 永不列出（`rb0` = IP，由 `pc` 承载），`ra1..ra63` 只列
「RACNT 有效区内」的条目（`spec/SimRISC-00 §2.4`）。`exc` 为 `None` 或
`{"cfx": <id>, "cause": "0x…", "ip": "0x…", "info": "0x…"}`。
"""
from __future__ import annotations

import json
from pathlib import Path

BANKS = ("rd", "rb", "rf", "ra")
MASK64 = (1 << 64) - 1
DEFAULT_MAX_BYTES = 1 << 20          # 1 MiB（任务约束：超过须分块/摘要）


def hex64(value):
    return "0x%016x" % (value & MASK64)


def hex32(value):
    return "0x%08x" % (value & 0xFFFFFFFF)


def reg_name(bank, idx):
    return "%s%d" % (bank, idx)


def racnt(ra0):
    return (ra0 >> 48) & 0x3F


def ra_valid_lo(ra0):
    """有效区下界（含）：`ra[64-RACNT .. 63]`；RACNT=0 时为 64（空）。"""
    return 64 - racnt(ra0)


def snapshot(machine):
    return {bank: list(machine.banks[bank]) for bank in BANKS}


def reg_delta(before, after, ra_ok, rd8_ok=True):
    """派生一次指令执行的寄存器写回集合。

    `ra_ok`：RA 条目「内容可比」集合，原地更新——落在有效区外 ⇒ 移除；
    本次被写（值变化）⇒ 加入。这样「从有效区外提升进有效区、内容来源未定义」
    的条目（`spec/SimRISC-00 §2.4`：有效区外 `ra_i` 内容未定义）不会拿来比。

    `rd8_ok=False`：semihosting「无返回/宿主时钟」服务之后 `rd8` 的对端值不是
    架构语义（`contract-semihosting §3`），整条记录跳过 `rd8`。

    返回 `(dst, val)`：寄存器名列表与并列的 64 位值列表（确定性顺序）。
    """
    dst, val = [], []
    skipped = 0
    ra_lo = ra_valid_lo(after["ra"][0])
    for bank in BANKS:
        for idx in range(64):
            if bank == "rb" and idx == 0:        # rb0 = IP，由 pc 字段承载
                continue
            if bank == "rd" and idx == 0:        # rd0 恒 0，写丢弃
                continue
            if bank == "rd" and idx == 8 and not rd8_ok:
                continue
            old = before[bank][idx]
            new = after[bank][idx]
            if bank == "ra" and idx >= 1:
                if idx < ra_lo:
                    ra_ok.discard(idx)
                    continue
                if new != old:
                    ra_ok.add(idx)
                if idx not in ra_ok:
                    skipped += 1     # 有效区内但内容来源未定义（有效区外提升）
                    continue
            if new != old:
                dst.append(reg_name(bank, idx))
                val.append(hex64(new))
    return dst, val, skipped


def init_ra_ok(banks):
    """入口态的可比 RA 集合 = 入口 RACNT 的有效区（`ra0` 另由 ra0 值比对）。"""
    return set(range(ra_valid_lo(banks["ra"][0]), 64))


def make_record(seq, pc, insn, op_id, mnemonic, dst, val, exc):
    return {
        "seq": seq,
        "pc": hex64(pc),
        "insn": None if insn is None else hex32(insn),
        "id": op_id,
        "mn": mnemonic,
        "dst": dst,
        "val": val,
        "exc": exc,
    }


def exc_object(cfx_id, cause, ip, info):
    return {"cfx": cfx_id, "cause": hex64(cause),
            "ip": hex64(ip), "info": hex64(info)}


class TraceWriter:
    """JSONL 写出器：单文件超限时滚动为 `<stem>.part-NNN.jsonl`（1 MiB 口径）。"""

    def __init__(self, path, max_bytes=DEFAULT_MAX_BYTES):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.parts = []
        self.bytes = 0
        self.count = 0
        self._fh = None
        self._part_bytes = 0
        self._index = 0

    def _open(self):
        if self._fh is None:
            if len(self.parts) == 0:
                out = self.path
            else:
                out = self.path.with_name("%s.part-%03d%s"
                                          % (self.path.stem, self._index,
                                             self.path.suffix))
            self._index += 1
            self._fh = open(out, "w", encoding="utf-8")
            self.parts.append(str(out))
            self._part_bytes = 0

    def write(self, record):
        line = json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n"
        data = line.encode("utf-8")
        if self._fh is not None and self._part_bytes + len(data) > self.max_bytes:
            self._fh.close()
            self._fh = None
        self._open()
        self._fh.write(line)
        self._part_bytes += len(data)
        self.bytes += len(data)
        self.count += 1

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        return self.parts
