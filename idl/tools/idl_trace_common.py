#!/usr/bin/env python3
"""idl_trace_common.py — 逐指令 trace 的公共口径（`m17-idl-004`）。

只放「格式与比较口径」，不放任何模型语义：

  * 记录字段与 JSONL 写法（真源说明见 `idl/docs/trace-format.md`）；
  * 寄存器写回集合的派生（四寄存器组全 64 槽按值比）；
  * 大文件保护：单文件超过 `--max-bytes` 时按 `<stem>.part-NNN.jsonl` 滚动。

trace 记录（一行一个 JSON 对象）：

    {"seq": 1, "pc": "0x0000ffffff010100", "insn": "0x4c600001",
     "id": "set.zw_rwii_rd", "mn": "set.zw",
     "dst": ["rd24"], "val": ["0x0000000000000001"], "exc": null}

`dst`/`val` 是**架构寄存器的写回集合**（不是指令操作数字段）：值发生变化的寄存器
才列出，`rd0`/`rb0` 永不列出（`rb0` = IP，由 `pc` 承载）；`ra1..ra63` 是逻辑视图的
**全部 64 槽**（`ra0` 另含），按环形约定（`phys(i) = 1 + ((base + i) % 63)`，
`spec/SimRISC-00 §2.4.3`）与各平台实现逐槽一致，因此窗口外残留槽也按值参与比较。
`exc` 为 `None` 或 `{"cfx": <id>, "cause": "0x…", "ip": "0x…", "info": "0x…"}`。
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


def snapshot(machine):
    """架构（逻辑）视图：四组全 64 槽；RA 已按环形映射换算（sim §2.4.3）。"""
    snap = machine.snapshot()
    return {bank: list(snap[bank]) for bank in BANKS}


def reg_delta(before, after, rd8_ok=True):
    """派生一次指令执行的寄存器写回集合（四组全 64 槽按值比）。

    `before`/`after` 是**逻辑视图**快照（RA 已经环形映射换算）。所有值变化的
    槽都进 `dst`/`val`——包括 `RACNT` 有效区外的残留槽（统一环形约定保证两侧
    逐槽一致，见 `spec/SimRISC-00 §2.4.3`）。不再有窗口过滤、来源继承或跳过集。

    `rd8_ok=False`：semihosting「无返回/宿主时钟」服务之后 `rd8` 的对端值不是
    架构语义（`contract-semihosting §3`），整条记录跳过 `rd8`。

    返回 `(dst, val)`：寄存器名列表、并列的 64 位值列表（确定性顺序）。
    """
    dst, val = [], []
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
            if new != old:
                dst.append(reg_name(bank, idx))
                val.append(hex64(new))
    return dst, val


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
    """JSONL 写出器：单文件超限时滚动为 `<stem>.part-NNN.jsonl`（1 MiB 口径）。

    记录只含 `idl/docs/trace-format.md §1` 的字段；比较口径在 `reg_delta`，
    不再携带任何跳过集元数据。
    """

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
