#!/usr/bin/env python3
"""check_causeid — `excp_cause_id` 全宽判据（`m16-chipyard-003`）。

`tools/chipyard/excp/causeid.S` 从**异常帧**（固件 hmon 保存的 `cg5 rc2` /
`cg5 rc4`）把整 64 位 `excp_cause_id` 与 `excp_cause_info` 逐字节打印出来；本脚本
把它按「每个用例 16 字节（cause_id, cause_info）」切分并逐条判定。

期望值**现场从合约解析**，不写魔数（`AGENTS.md`「Independent oracle」）：

  * 大类取值与 `[15:0] one-hot` / `[31:16]` 保留规则：`contract-see §6.1`；
  * 子原因位号、wyde 归属、目标 cause：`contract-see §6.1.1`，并与
    `spec/DADAO-12 §3.6` 的两张 wyde 表**逐位互校**（两张独立表不一致即中止）；
  * `cause_info` 语义（`CFXMEM`/`MALIGN`/`IALIGN` 恒为地址；`ADR-0056 D4`）。

判定项（每条用例）：

  1. `cause_id` **全 64 位**等于期望（低 16 位大类 + 该 cause 独占 wyde 内的**恰一位**
     子原因，其余位全 0）—— 不是掩码比较；
  2. 反向断言：`[31:16] == 0`；非 `CFXMEM`/`CFXPERM` 的 cause **两个 wyde 全 0**；
     `CFXMEM` 的 wyde2 全 0、`CFXPERM` 的 wyde3 全 0；
  3. 子原因位在 wyde 内**恰一位**（禁多位/零位，`§3.6 (五)`）；
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
    ("cfxmem_data",   "CFXMEM", "NONPTW", 0x10_0000_0000),
    ("cfxmem_fetch",  "CFXMEM", "NONPTW", 0x10_0000_0000),
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
    r"^\|\s*`\[(\d+)\]`\s*\|\s*wyde(\d)\s*\|\s*`([A-Z0-9_]+)`\s*\|\s*`([A-Z0-9_]+)`\s*\|")
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
    # §6.1.1 子原因表（18 行）
    sub = {}
    rows = 0
    for line in section(text, "### §6.1.1 子原因位表",
                        "### §6.2").splitlines():
        m = SUBCAUSE_CONTRACT_RE.match(line)
        if m:
            bit, wyde, name, cause = (int(m.group(1)), int(m.group(2)),
                                      m.group(3), m.group(4))
            if name in sub:
                raise SystemExit(
                    "check_causeid: ERROR: duplicate sub-cause %r" % name)
            sub[name] = (bit, wyde, cause)
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

    # 合约表 18 行（8 权限类 + 10 缺失/回写/非页表类）
    eq("contract §6.1.1 sub-cause rows", 18, rows)
    eq("contract §6.1.1 permission rows (wyde2)", 8,
       sum(1 for v in sub.values() if v[1] == 2))
    eq("contract §6.1.1 memory rows (wyde3)", 10,
       sum(1 for v in sub.values() if v[1] == 3))
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
    # 归属互斥：每个 cause 只有一个 wyde
    eq("wyde2 names all target CFXPERM", ["CFXPERM"],
       sorted({v[2] for v in sub.values() if v[1] == 2}))
    eq("wyde3 names all target CFXMEM", ["CFXMEM"],
       sorted({v[2] for v in sub.values() if v[1] == 3}))
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
    value = classes[cls]
    if sc is not None:
        value |= 1 << sub[sc][0]
    return value


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
    for i, (label, cls, sc, info) in enumerate(CASES):
        cid, inf = struct.unpack(">QQ",
                                 raw[i * RECORD:(i + 1) * RECORD])
        want = expected_cause_id(classes, sub, cls, sc)
        # 1. 全 64 位相等（不再是 `& 0xFFFF` 掩码比较）
        eq("%s: cause_id full width" % label, want, cid)
        cause, wyde2, wyde3 = split_wydes(cid)
        # 2. 反向断言：保留区与归属互斥
        eq("%s: [31:16] reserved" % label, 0, (cid >> 16) & 0xFFFF)
        if cls == "CFXMEM":
            eq("%s: wyde2 must be 0 for CFXMEM" % label, 0, wyde2)
            eq("%s: wyde3 sub-cause one-hot" % label, 1,
               bin(wyde3).count("1"))
            eq("%s: wyde3 reserved [63:58] == 0" % label, 0, wyde3 >> 10)
        elif cls == "CFXPERM":
            eq("%s: wyde3 must be 0 for CFXPERM" % label, 0, wyde3)
            eq("%s: wyde2 sub-cause one-hot" % label, 1,
               bin(wyde2).count("1"))
            eq("%s: wyde2 reserved [47:40] == 0" % label, 0, wyde2 >> 8)
        else:
            eq("%s: no sub-cause wyde for %s" % (label, cls), (0, 0),
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
