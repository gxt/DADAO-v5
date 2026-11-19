#!/usr/bin/env python3
"""check_vastptw — `tools/chipyard/ptw/vastptw.S` 的独立判据（`m16-chipyard-006`）。

探针把 19 个 8 字节实测值（11 个寄存器/路由检查点 + 4 个故障用例 × {cause_id,
cause_info}）写进结果缓冲。本脚本**不保存期望常量**，而是现场从：

  * `.tao/contracts/contract-see.md` §6.1（cause 大类 `1 << N`）与 §6.1.1（子原因位表，
    逐位等价于 `spec/DADAO-12 §3.6`）解析位号；
  * `.tao/adr/adr-0056-cause-id-subcause-encoding.md`（D2）解析同一组位号，

两侧逐位互校后，用它构造期望值（`AGENTS.md`「Independent oracle」）。寄存器侧的
期望值按 `spec/DADAO-12 §4.5` 的存储口径当场算（PTBR 只存 `PPN[55:16]`、ASID 只存
`[15:0]`、addr_start 只存 `VA[41:0]`）。

判据：
  * 记录数 == 19、每条 8 字节；
  * 每条记录逐位等于期望（不做掩码）；
  * `CFXMEM` 记录的结构规则：`[31:16]` 保留 = 0、wyde2 全 0（`CFXPERM` 的 wyde）、
    wyde3 内恰一位；
  * `cause_info` == 被访问的 VA。

用法：
  check_vastptw.py --stream <file> [--root <repo>]
  check_vastptw.py --self-test [--root <repo>]     # 合成坏流 ⇒ 每条断言都有可达 FAIL 路径
"""

from __future__ import annotations

import argparse
import pathlib
import re
import struct
import sys

# 探针的记录顺序（`vastptw.S`）：检查点 1..11 各 1 条，之后 4 个故障用例各 2 条
# （cause_id、cause_info）。这里只记「哪一个语义」，值全部现场算。
REGISTER_CHECKS = ["enable reset", "enable write 1", "enable write 0",
                   "ptbr mask", "asid mask", "addr_start mask",
                   "addr_size roundtrip", "cg7 desc", "cg7 start",
                   "internal read enable=0", "internal read enable=1"]
# 故障用例：(名字, 子原因类, VA)  类 D = 数据缺失类 / I = 取指缺失类 / N = NONPTW
FAULT_CASES = [("data VA, enable=1", "D", 0x1000),
               ("fetch VA, enable=1", "I", 0x2000),
               ("data VA, enable=0", "N", 0x1000),
               ("fetch VA, enable=0", "N", 0x2000)]
N_RECORDS = len(REGISTER_CHECKS) + 2 * len(FAULT_CASES)
FIRST_FAULT = len(REGISTER_CHECKS)


# ---------------------------------------------------------------------------
# 合约 / ADR 现场解析（同名位号必须唯一，冲突即报错）
# ---------------------------------------------------------------------------
def _unique(pairs, what):
    table = {}
    for name, bit in pairs:
        if name in table and table[name] != bit:
            raise SystemExit("check_vastptw: %s has two bit numbers for %s (%d / %d)"
                             % (what, name, table[name], bit))
        table[name] = bit
    return table


def contract_table(root: pathlib.Path) -> dict:
    text = (root / ".tao/contracts/contract-see.md").read_text(encoding="utf-8")
    start = text.find("### §6.1.1")
    end = text.find("### §6.2")
    if start < 0 or end < 0:
        raise SystemExit("check_vastptw: contract-see §6.1.1 not found")
    sub_pairs = []
    for line in text[start:end].splitlines():
        m = re.match(r"^\|\s*`\[(\d+)\]`\s*\|\s*wyde(\d)\s*\|\s*`([A-Z0-9_]+)`\s*\|\s*`([A-Z0-9_]+)`",
                     line)
        if m:
            sub_pairs.append((m.group(3), int(m.group(1)), int(m.group(2)), m.group(4)))
    sub = _unique([(n, b) for n, b, _, _ in sub_pairs], "contract-see §6.1.1")
    wyde = _unique([(n, w) for n, _, w, _ in sub_pairs], "contract-see §6.1.1 (wyde)")
    owner = _unique([(n, c) for n, _, _, c in sub_pairs], "contract-see §6.1.1 (cause)")
    # `| `1 << 1` | `CFXMEM` | ... |` 行（§6.1 的 cause 表）
    class_pairs = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*`1 << (\d+)`\s*\|\s*`([A-Z0-9_]+)`", line)
        if m:
            class_pairs.append((m.group(2), int(m.group(1))))
    return {"sub": sub, "wyde": wyde, "owner": owner,
            "class": _unique(class_pairs, "contract-see §6.1")}


def adr_table(root: pathlib.Path) -> dict:
    text = (root / ".tao/adr/adr-0056-cause-id-subcause-encoding.md").read_text(
        encoding="utf-8")
    pairs = [(m.group(2), int(m.group(1)))
             for m in re.finditer(r"`(\d+) ([A-Z0-9_]+)`", text)]
    return _unique(pairs, "ADR-0056")


def bit_table(root: pathlib.Path) -> dict:
    c = contract_table(root)
    a = adr_table(root)
    problems = []
    for name in ("NONPTW", "DGPTRAP", "IGPTRAP", "ADWBFAIL"):
        if name not in c["sub"]:
            problems.append("contract-see §6.1.1 missing %s" % name)
            continue
        if name in a and a[name] != c["sub"][name]:
            problems.append("%s: contract [%d] != ADR-0056 [%d]"
                            % (name, c["sub"][name], a[name]))
        if c["owner"].get(name) != "CFXMEM":
            problems.append("%s owned by %s, expected CFXMEM" % (name, c["owner"].get(name)))
        if c["wyde"].get(name) != 3:
            problems.append("%s in wyde%d, expected wyde3" % (name, c["wyde"].get(name)))
    if "CFXMEM" not in c["class"]:
        problems.append("contract-see §6.1 missing the CFXMEM class row")
    if problems:
        raise SystemExit("check_vastptw: bit table cross-check failed: " + "; ".join(problems))
    return c


# ---------------------------------------------------------------------------
# 期望值（`DADAO-12 §4.5` 的存储口径 + 合约位号）
# ---------------------------------------------------------------------------
def expected_records(table: dict) -> list:
    cfxmem = 1 << table["class"]["CFXMEM"]
    subs = {"N": 1 << table["sub"]["NONPTW"],
            "D": 1 << table["sub"]["DGPTRAP"],
            "I": 1 << table["sub"]["IGPTRAP"]}
    recs = [0,                          # 1 enable reset (TLB-03)
            1,                          # 2 write 1 -> read 1
            0,                          # 3 write 0 -> read 0
            ((1 << 40) - 1) << 16,      # 4 PTBR keeps PPN[55:16] only
            (1 << 16) - 1,              # 5 ASID keeps [15:0]
            (1 << 42) - 1,              # 6 addr_start keeps VA[41:0]
            0x123456789ABCDEF0,         # 7 addr_size 64-bit round trip
            0, 0,                       # 8/9 cfx_ptw has no cg7 space block
            0x55, 0x55]                 # 10/11 internal marker, enable 0 / 1
    for _, kind, va in FAULT_CASES:
        recs += [cfxmem | subs[kind], va]
    if len(recs) != N_RECORDS:
        raise SystemExit("check_vastptw: expected %d records, built %d"
                         % (N_RECORDS, len(recs)))
    return recs


# ---------------------------------------------------------------------------
# 判据
# ---------------------------------------------------------------------------
def parse_stream(path: pathlib.Path) -> list:
    return unpack(path.read_bytes())


def unpack(data: bytes) -> list:
    if len(data) % 8:
        return None                     # 非整记录 ⇒ 由条数断言报 FAIL
    return [struct.unpack(">Q", data[i:i + 8])[0] for i in range(0, len(data), 8)]


def check(recs, expected: list, table: dict) -> list:
    if recs is None:
        return ["stream is not a whole number of 8-byte records"]
    fails = []
    if len(recs) != len(expected):
        fails.append("record count %d != %d" % (len(recs), len(expected)))
    for i, (got, want) in enumerate(zip(recs, expected)):
        if got != want:
            fails.append("record %d: got 0x%016x want 0x%016x" % (i, got, want))
    cfxmem = 1 << table["class"]["CFXMEM"]
    for i in range(FIRST_FAULT, min(len(recs), len(expected)), 2):
        cid = recs[i]
        if cid & 0xFFFF != cfxmem:
            fails.append("record %d: low cause 0x%04x != CFXMEM" % (i, cid & 0xFFFF))
        if (cid >> 16) & 0xFFFF:
            fails.append("record %d: [31:16] reserved must be 0 (got 0x%04x)"
                         % (i, (cid >> 16) & 0xFFFF))
        if (cid >> 32) & 0xFFFF:
            fails.append("record %d: wyde2 must be 0 for CFXMEM (got 0x%04x)"
                         % (i, (cid >> 32) & 0xFFFF))
        wyde3 = (cid >> 48) & 0xFFFF
        if bin(wyde3).count("1") != 1:
            fails.append("record %d: wyde3 must be one-hot (got 0x%04x)" % (i, wyde3))
    return fails


# ---------------------------------------------------------------------------
# 自检：合成坏流 ⇒ 每条断言都能 FAIL
# ---------------------------------------------------------------------------
def selftest(table: dict) -> int:
    expected = expected_records(table)
    fails = 0

    def report(name, recs):
        nonlocal fails
        got = check(recs, expected, table)
        if got:
            print("  [PASS] %-34s rejected (%s)" % (name, got[0]))
            return
        print("  [FAIL] %-34s accepted" % name)
        fails += 1

    if check(list(expected), expected, table):
        print("  [FAIL] control stream rejected: %s"
              % "; ".join(check(list(expected), expected, table)))
        fails += 1
    else:
        print("  [PASS] control stream accepted (19 records)")

    i_d1 = FIRST_FAULT + 0            # 用例 1 的 cause_id（DGPTRAP）
    i_d2 = FIRST_FAULT + 2            # 用例 2 的 cause_id（IGPTRAP）
    i_d3 = FIRST_FAULT + 4            # 用例 3 的 cause_id（NONPTW）

    # 子原因位号是绝对位号（DGPTRAP = [52] ⇒ 1 << 52），落位由 wyde 归属保证
    m = list(expected); m[i_d1] &= ~(1 << table["sub"]["DGPTRAP"])
    report("sub-cause bit cleared", m)
    m = list(expected); m[i_d3] = (m[i_d3] & 0xFFFF) | (1 << table["sub"]["ADWBFAIL"])
    report("sub-cause wrong bit", m)
    m = list(expected); m[i_d3] = (m[i_d3] & 0xFFFF) | (1 << 33)
    report("sub-cause in the CFXPERM wyde", m)
    m = list(expected); m[i_d3 + 1] = 0x7F1C0000
    report("cause_info is not the address", m)
    m = list(expected); m[i_d2] |= 1 << 20
    report("reserved [31:16] bit set", m)
    m = list(expected); m[4] = 0xFFFFFFFFFFFFFFFF
    report("ASID mask not applied", m)
    m = list(expected); m[6] = 0x0
    report("addr_size not stored", m)
    report("record truncated", expected[:-1])
    report("extra record", expected + [0])
    report("stream not 8-byte aligned", None)

    if (table["sub"]["NONPTW"] == 57 and table["sub"]["DGPTRAP"] == 52
            and table["sub"]["IGPTRAP"] == 48 and table["class"]["CFXMEM"] == 1):
        print("  [PASS] bit table parsed live (CFXMEM=1<<1, IGPTRAP=[48], "
              "DGPTRAP=[52], NONPTW=[57]) + ADR-0056 D2 cross-check")
    else:
        print("  [FAIL] parsed bit table != the contract's values")
        fails += 1
    return 1 if fails else 0


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stream", help="result-buffer dump from the vastptw probe")
    ap.add_argument("--root", default=None,
                    help="repository root (default: three levels up from this file)")
    ap.add_argument("--self-test", action="store_true",
                    help="synthetic mutant streams must be rejected")
    args = ap.parse_args()
    root = pathlib.Path(args.root) if args.root else pathlib.Path(__file__).resolve().parents[3]

    table = bit_table(root)
    if args.self_test:
        print("check_vastptw: self-test")
        return selftest(table)
    if not args.stream:
        ap.error("--stream or --self-test is required")

    expected = expected_records(table)
    recs = parse_stream(pathlib.Path(args.stream))
    fails = check(recs, expected, table)
    print("check_vastptw: records=%s expected=%d"
          % ("?" if recs is None else len(recs), len(expected)))
    for f in fails:
        print("  [FAIL] %s" % f)
    if fails:
        return 1
    print("check_vastptw: PASS (register face + address routing, %d records)" % len(recs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
