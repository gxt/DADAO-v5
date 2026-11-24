#!/usr/bin/env python3
"""check_causeid — `excp_cause_id` 全宽判据（`m16-chipyard-003`）。

`tools/chipyard/excp/causeid.S` 从**异常帧**（固件 hmon 保存的 `cg5 rc2` /
`cg5 rc4`）把整 64 位 `excp_cause_id` 与 `excp_cause_info` 逐字节打印出来；本脚本
把它按「每个用例 16 字节（cause_id, cause_info）」切分并逐条判定。

期望值**现场从合约解析**，不写魔数（`AGENTS.md`「Independent oracle」）：

  * 大类取值与 `[15:0] one-hot` / `[31:16]` 保留规则：`contract-see §6.1`；
  * 高位位图位号与扁平不变式：`contract-see §6.1.1`，并与
    `spec/DADAO-12 §3.6` 的两张位图表**逐位互校**（两张独立表不一致即中止；
    `ADR-0062 D1/D3`）；
  * `cause_info` 语义（地址类原因恒为地址；`ADR-0062 D4`）。

判定项（每条用例）：

  1. `cause_id` **全 64 位**等于期望（低 16 位大类，或 PTW 故障的高位位图恰一位，
     其余位全 0）—— 不是掩码比较；
  2. 反向断言：`[31:16] == 0`；`CFXMEM`/`CFXPERM` 的 `[63:32]` 全 0；PTW 故障
     低位 cause = 0、高位位图恰一位；`[39]`/`[47:40]`/`[57]`/`[63:58]` 恒 0；
  3. 高位位图在 `[32..38]`/`[48..56]` 内**恰一位**（禁多位/零位，`§3.6 (五)`）；
  4. 本 profile 可判定的 `cause_info` 恒为地址的用例：`CFXMEM`（数据/取指）、
     `MALIGN`、`IALIGN`。

用法：
  check_causeid.py --stream FILE [--contract PATH] [--spec PATH]
  check_causeid.py --stream FILE --selfcheck     # 只验表解析与位号派生
退出码：0 ⇔ 每条判定通过。
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

RECORD = 16                      # 每用例 2 × 8 字节（cause_id, cause_info）
RAM_BASE = 0xFFFF_FF00_0000      # `tests/shared/asm/machine-tiny.inc`

# 用例表（与 `tools/chipyard/excp/causeid.S` 的用例顺序一一对应；本表只写
# 「哪个用例、哪个大类、哪个子原因符号名、info 期望」，**位号由合约解析**）。
CASES = [
    ("cfxmem_data",   "CFXMEM", None,     0x10_0000_0000),
    ("cfxmem_fetch",  "CFXMEM", None,     0x10_0000_0000),
    ("illi",          "ILLI",   None,     None),
    ("undi",          "UNDI",   None,     None),
    ("malign",        "MALIGN", None,     RAM_BASE + 1),
    ("cfxreg",        "CFXREG", None,     None),
    ("cfxtrap",       "CFXTRAP", None,    None),
    ("ialign",        "IALIGN", None,     RAM_BASE + 2),
]

PASS = 0
FAIL = 0


def ok(name, expected, actual):
    global PASS
    PASS += 1
    print("  [PASS] %s | expected=%s actual=%s" % (name, expected, actual))


def bad(name, expected, actual):
    global FAIL
    FAIL += 1
    print("  [FAIL] %s | expected=%s actual=%s" % (name, expected, actual))


def eq(name, expected, actual):
    fmt = (lambda v: hex(v)) if isinstance(expected, int) else str
    if expected == actual:
        ok(name, fmt(expected), fmt(actual))
    else:
        bad(name, fmt(expected), fmt(actual))


def read(p) -> str:
    p = Path(p)
    try:
        return p.read_text(encoding="utf-8")
    except OSError as exc:
        print("check_causeid: ERROR: cannot read %s: %s" % (p, exc),
              file=sys.stderr)
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# 合约解析
# ---------------------------------------------------------------------------
CLASS_RE = re.compile(r"^\|\s*`1 << (\d+)`\s*\|\s*`([A-Z0-9_]+)`\s*\|")
SUBCAUSE_CONTRACT_RE = re.compile(
    r"^\|\s*`\[(\d+)\]`\s*\|\s*wyde(\d)\s+[^|]*\|\s*`([A-Z0-9_]+)`\s*\|")
SUBCAUSE_SPEC_RE = re.compile(
    r"^\|\s*`\[(\d+)\]`\s*\|\s*([A-Z0-9_]+)\s*\|")


def section(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        raise SystemExit("check_causeid: ERROR: section %r not found" % start)
    j = text.find(end, i)
    return text[i:j if j > 0 else len(text)]


def parse_contract(path: Path):
    """→ (classes{name: value}, subcauses{name: (absbit, wyde, cause)}, rows)"""
    text = read(path)
    # §6.1 的 11 项 cause 表（`| `1 << 1` | `CFXMEM` | ...`）
    classes = {}
    for line in section(text, "### §6.1 `excp_cause_info`",
                        "### §6.1.1").splitlines():
        m = CLASS_RE.match(line)
        if m:
            classes[m.group(2)] = 1 << int(m.group(1))
    # §6.1.1 高位位图表（16 行）
    sub = {}
    rows = 0
    for line in section(text, "### §6.1.1 高位位图表",
                        "### §6.2").splitlines():
        m = SUBCAUSE_CONTRACT_RE.match(line)
        if m:
            bit, wyde, name = int(m.group(1)), int(m.group(2)), m.group(3)
            if name in sub:
                raise SystemExit(
                    "check_causeid: ERROR: duplicate bitmap bit %r" % name)
            sub[name] = (bit, wyde, None)
            rows += 1
    return classes, sub, rows


def parse_spec(path: Path):
    """`spec/DADAO-12 §3.6` 的两张 wyde 表 → {name: absbit}（独立第二来源）。"""
    text = read(path)
    sec = section(text, "### 3.6 cg5 - 异常现场寄存器", "### 3.7")
    bits = {}
    for line in sec.splitlines():
        m = SUBCAUSE_SPEC_RE.match(line)
        if m:
            bit, name = int(m.group(1)), m.group(2)
            if name in bits:
                raise SystemExit(
                    "check_causeid: ERROR: spec duplicate sub-cause %r" % name)
            bits[name] = bit
    return bits


def check_tables(args):
    classes, sub, rows = parse_contract(args.contract)
    spec = parse_spec(args.spec)

    # 合约表 16 行（7 权限类 + 8 缺失类 + 1 A/D 回写）
    eq("contract §6.1.1 bitmap rows", 16, rows)
    eq("contract §6.1.1 permission rows (wyde2)", 7,
       sum(1 for v in sub.values() if v[1] == 2))
    eq("contract §6.1.1 memory rows (wyde3)", 9,
       sum(1 for v in sub.values() if v[1] == 3))
    # ADR-0062 D3：两个否定位删除
    eq("contract §6.1.1 deleted [39]/[57] absent", [],
       sorted(set(sub) & {"NCFXPERM", "NONPTW"}))
    # 两张独立表逐位互校
    eq("spec §3.6 sub-cause names == contract names", sorted(spec), sorted(sub))
    mism = [n for n in sorted(set(spec) & set(sub)) if spec[n] != sub[n][0]]
    eq("spec §3.6 bit == contract §6.1.1 bit (per name)", [], mism)
    # 位号必须落在自己 wyde 的 16 位窗口内（错 wyde 即红）
    for name, (bit, wyde, cause) in sorted(sub.items()):
        base = 32 if wyde == 2 else 48
        eq("  %s: absolute bit inside wyde%d [%d, %d)" % (name, wyde, base,
                                                          base + 16),
           True, base <= bit < base + 16)
    # 扁平区间：wyde2 只放 [32..39)、wyde3 只放 [48..57)
    eq("wyde2 bitmap bits in [32,39)", [],
       sorted(n for n, (b, w, _) in sub.items() if w == 2 and not 32 <= b < 39))
    eq("wyde3 bitmap bits in [48,57)", [],
       sorted(n for n, (b, w, _) in sub.items() if w == 3 and not 48 <= b < 57))
    # 大类取值
    for name, want in (("CFXMEM", 2), ("CFXPERM", 0x80), ("CFXREG", 4),
                       ("CFXTRAP", 1), ("CFXESC", 8), ("ILLI", 0x100),
                       ("UNDI", 0x200), ("MALIGN", 0x1000), ("IALIGN", 0x2000)):
        eq("contract §6.1 class %s" % name, want, classes.get(name))
    # 每个用例的大类/子原因都必须能在表里找到
    for label, cls, sc, _ in CASES:
        eq("  %s: class %s in contract" % (label, cls), True, cls in classes)
        if sc is not None:
            eq("  %s: sub-cause %s in contract" % (label, sc), True, sc in sub)
            eq("  %s: %s targets %s" % (label, sc, cls), cls,
               sub[sc][2] if sc in sub else None)
    return classes, sub


def expected_cause_id(classes, sub, cls, sc):
    # 扁平：PTW 故障只置高位位图（低位 cause = 0）；其余只置大类位
    if sc is not None:
        return 1 << sub[sc][0]
    return classes[cls]


def split_wydes(v):
    return v & 0xFFFF, (v >> 32) & 0xFFFF, (v >> 48) & 0xFFFF


def check_stream(stream: Path, classes, sub):
    raw = stream.read_bytes()
    eq("stream bytes (%d records x 16)" % len(CASES), RECORD * len(CASES),
       len(raw))
    if len(raw) < RECORD * len(CASES):
        print("check_causeid: stream is short; the guest did not reach every "
              "case", file=sys.stderr)
        return
    reserved = (1 << 7) | (0xFF << 8) | (1 << 25) | (0x3F << 26)
    valid_high = (0x7F) | (0x1FF << 16)
    for i, (label, cls, sc, info) in enumerate(CASES):
        cid, inf = struct.unpack(">QQ",
                                 raw[i * RECORD:(i + 1) * RECORD])
        want = expected_cause_id(classes, sub, cls, sc)
        # 1. 全 64 位相等（不是 `& 0xFFFF` 掩码比较）
        eq("%s: cause_id full width" % label, want, cid)
        cause, wyde2, wyde3 = split_wydes(cid)
        high = cid >> 32
        # 2. 扁平不变式
        eq("%s: [31:16] reserved" % label, 0, (cid >> 16) & 0xFFFF)
        eq("%s: reserved high bits" % label, 0, high & reserved)
        if sc is not None:
            eq("%s: PTW bitmap only (low cause = 0)" % label, 0, cause)
            eq("%s: bitmap one-hot" % label, 1, bin(high).count("1"))
            eq("%s: bitmap inside [32..38]/[48..56]" % label, 0,
               high & ~valid_high)
        else:
            eq("%s: %s high bitmap is 0" % (label, cls), (0, 0),
               (wyde2, wyde3))
            eq("%s: cause class is one-hot" % label, 1, bin(cause).count("1"))
        # 3. cause_info（本 profile 可判定的恒为地址的用例）
        if info is not None:
            eq("%s: cause_info is the address" % label, info, inf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", required=True,
                    help="SYS_WRITEC 字节流（每用例 16 字节）")
    ap.add_argument("--contract",
                    default=str(REPO / ".tao/contracts/contract-see.md"))
    ap.add_argument("--spec", default=str(
        REPO / "spec/DADAO-12-SEE-主管系统运行环境.md"))
    ap.add_argument("--selfcheck", action="store_true",
                    help="只验合约/Spec 表解析与位号派生")
    args = ap.parse_args()

    classes, sub = check_tables(args)
    if not args.selfcheck:
        check_stream(Path(args.stream), classes, sub)
    print("\ncheck_causeid: PASS=%d FAIL=%d" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
