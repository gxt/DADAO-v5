#!/usr/bin/env python3
"""generate_bitcnt_vectors.py — `ctlz`/`cttz`/`ctpop`（位扫描 / 位计数）向量生成器 + 独立 oracle。

范围（**非 M1**）
----------------
`ctlz`/`cttz`/`ctpop` 属 `scope: m8`（`ADR-0012 D11`），**不是 M1 身份**，故**不进**
`tests/vectors/inventory.md` 的 M1 覆盖矩阵，也**不**由 `tools/testcases/generate_isa_vectors.py`
（M1-only，`scope == "m1"` 过滤）生成；本脚本把向量落到独立的
`tests/vectors/bitcnt/bitcnt.yaml`。

语义（真源 = `spec/SimRISC-04: Bit manipulating：位操作指令` 的「位扫描与位计数」 + `.tao/contracts/contract-isa.md`）
--------------------------------------------------------------------------------------------
`hd`（= `orri` 的 6 位立即数 `immu6`，`0..63`）是**有效位上界**：参与运算的是
`rdHC[hd:0]`（共 `hd+1` 位），`hd` 以上的位**不参与**。

* `ctlz`  = 从 bit `hd` 向下数的前导零个数；
* `cttz`  = 从 bit 0 向上数的末尾零个数（到 bit `hd` 止）；
* `ctpop` = `rdHC[hd:0]` 内 1 的个数；
* 定值：`rdHC[hd:0]` **全 0** ⇒ `ctlz` = `cttz` = `hd + 1`（消除 UB），`ctpop` = `0`。

独立 oracle（硬约束）
--------------------
期望值由本脚本用 **Python 大整数**独立派生，**三条彼此独立的派生路径**：

* `oracle_bits()`：逐位循环（按 bit 下标逐个检视 / 累加）；
* `oracle_int()`：整数性质（`bit_length()` / 最低位 `x & -x` / 二进制字符串计数）；
* `oracle_str()`：MSB-first 位串（`bin(valid)[2:].zfill(hd+1)` 后按串数数），口径与
  spec 正文「从 bit `hd` 向下 / 从 bit 0 向上」逐字对应。

三条路径在**全部** `(src, hd, mnemonic)` 组合上必须逐例一致（`--self-check`）。**从不**调用
LLVM / QEMU 或读取其产物，方向为「契约/规范 → 期望」。

端序
----
本项目为**大端**：编码字在内存中按大端字节序落盘（最高有效字节在最前）。`--check`
对每个 case 显式断言 `word.to_bytes(4, "big")` 的字节序，并断言 `op` 字节（`0x40`）
出现在**最前**。

用法
----
* 生成（写文件）：      ``python3 tools/testcases/generate_bitcnt_vectors.py``
* 校验（diff = 0）：    ``python3 tools/testcases/generate_bitcnt_vectors.py --check``
* 打印 oracle 自检：    ``python3 tools/testcases/generate_bitcnt_vectors.py --self-check``

`--check` 断言（任一不满足 ⇒ 非零退出）：
  1. 已入库 `tests/vectors/bitcnt/bitcnt.yaml` 与真源重派生结果**逐字节一致**；
  2. 每条 case 的 `encoding.word` 满足真源 `(word & mask) == value`（`contracts/opcodes.yaml`）；
  3. 每个 `semantic`/`boundary` case 的 `expected_state` 由 oracle **全量重算**后一致（非抽样）；
  4. **`hd ∈ 0..63` 全部合法**：每个 `hd` 取值都至少有一个 `expected_fault is None` 的
     semantic/boundary case（无任何 `hd` 触发 ILLI）；
  5. `legality` case 的 ILLI 依据只能是 `rdhb == rd0`（`dst_rd0`）——`rdhc`/`hd` 均不产生 ILLI；
  6. **大端**：每个 case 的编码字按大端字节序可往返，且 `op` 字节在最前；
  7. 覆盖 **全量**：3 条 × `hd` ∈ `0..63`（不抽样）；计数**现场统计**（不写死）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts" / "opcodes.yaml"
OUT = ROOT / "tests" / "vectors" / "bitcnt" / "bitcnt.yaml"

MASK64 = (1 << 64) - 1

S04_BIT = "SimRISC-04: Bit manipulating：位操作指令"

# 三条指令：id → mnemonic（语义同一套，`hd` = 有效位上界）
BITCNT_INSNS = ("ctpop_orri_rd", "ctlz_orri_rd", "cttz_orri_rd")

LEGALITY_CITE = ("SimRISC-04: Bit manipulating：位操作指令; "
                 "contract-isa §6.4.4; legality_rules.yaml :: dst_rd0")

# 语义输入：低 63 位全 1、bit63 = 0 —— 使「hd 以上的位不参与」可观测
SRC_PATTERN = 0x7FFFFFFFFFFFFFFF

HD_ALL = tuple(range(64))


# ────────────────────────────── 独立 oracle（路径 1：逐位） ──────────────────────────────

def oracle_bits(src: int, hd: int, op: str) -> int:
    """逐位循环实现（路径 1）：按 bit 下标 `0..hd` 逐个检视 / 累加。

    `hd` 必须 ∈ `0..63`；否则显式报错（不静默返回恒等值）。
    """
    if not (0 <= hd <= 63):
        raise ValueError(f"非法 hd：{hd}（须 0..63）")
    src &= MASK64
    valid = src & ((1 << (hd + 1)) - 1)
    if op == "ctlz":
        n = 0
        for i in range(hd, -1, -1):
            if (valid >> i) & 1:
                break
            n += 1
        return n
    if op == "cttz":
        n = 0
        for i in range(0, hd + 1):
            if (valid >> i) & 1:
                break
            n += 1
        return n
    if op == "ctpop":
        n = 0
        for i in range(0, hd + 1):
            n += (valid >> i) & 1
        return n
    raise ValueError(f"未知操作：{op!r}")


# ────────────────────────────── 独立 oracle（路径 2：整数性质） ──────────────────────────────

def oracle_int(src: int, hd: int, op: str) -> int:
    """整数性质实现（路径 2）：`bit_length()` / `x & -x` / 二进制串计数。

    与 `oracle_bits()` 的逐位循环**代码独立**（不共享任何中间量）。
    """
    width = hd + 1
    valid = (src & MASK64) % (1 << width)
    if op == "ctlz":
        # 前导零 = 有效宽度 − 最高有效位的位置+1
        return width - valid.bit_length()
    if op == "cttz":
        if valid == 0:
            return width
        return (valid & -valid).bit_length() - 1
    if op == "ctpop":
        return format(valid, "b").count("1")
    raise ValueError(f"未知操作：{op!r}")


def oracle_str(src: int, hd: int, op: str) -> int:
    """MSB-first 位串实现（路径 3）：`bin(valid)[2:].zfill(hd+1)` 后按串数数。

    与路径 1（按 bit 下标循环）、路径 2（整数性质）**代码独立**；口径与 spec 正文的
    「从 bit `hd` 向下 / 从 bit 0 向上」逐字对应。
    """
    width = hd + 1
    valid = (src & MASK64) % (1 << width)
    s = bin(valid)[2:].zfill(width)          # 宽 width，MSB 在左
    if op == "ctlz":
        return len(s) - len(s.lstrip("0"))
    if op == "cttz":
        return len(s) - len(s.rstrip("0"))
    if op == "ctpop":
        return s.count("1")
    raise ValueError(f"未知操作：{op!r}")


def oracle(src: int, hd: int, op: str) -> int:
    """三条独立路径必须一致（不一致 ⇒ 立即显式失败）。"""
    a = oracle_bits(src, hd, op)
    b = oracle_int(src, hd, op)
    c = oracle_str(src, hd, op)
    if not (a == b == c):
        raise AssertionError(f"三条 oracle 路径不一致：src={src:#x} hd={hd} "
                             f"{op}: bits={a} int={b} str={c}")
    return a


# ────────────────────────────── case 构造 ──────────────────────────────

def _hex64(v: int) -> str:
    return "0x%016X" % (v & MASK64)


def word(rec: dict, rdhb: int, rdhc: int, hd: int) -> int:
    """由真源 `value`（含 op + opx）叠加字段位域，得到完整 32 位字。"""
    w = int(str(rec["value"]), 16)
    w |= (rdhb & 0x3F) << 12
    w |= (rdhc & 0x3F) << 6
    w |= hd & 0x3F
    return w & 0xFFFFFFFF


def _case(rec, cls, w, input_state, expected_state, expected_fault,
          notes, spec_cite=None):
    return {
        "mnemonic": rec["mnemonic"],
        "id": rec["id"],
        "format": rec["format"],
        "class": cls,
        "encoding": {"word": "0x%08X" % w},
        "input_state": input_state,
        "expected_state": expected_state,
        "expected_pc": None,
        "expected_fault": expected_fault,
        "status": "active",
        "deferred_reason": None,
        "spec_cite": spec_cite or rec.get("spec_cite", ""),
        "notes": notes,
    }


def _state(rdhb: int, value: int) -> dict:
    return {"rd": {"rd%d" % rdhb: _hex64(value)}, "rb": {}, "ra": {}, "memory": []}


def build_cases(by_id: dict[str, dict]) -> list[dict]:
    cases: list[dict] = []

    for rid in BITCNT_INSNS:
        rec = by_id[rid]
        mnem = rec["mnemonic"]
        op = mnem  # ctlz / cttz / ctpop

        # ── encoding：字段合法，无 fault ──
        cases.append(_case(
            rec, "encoding", word(rec, 1, 2, 63), {}, None, None,
            "encoding: word 与 opcodes.yaml mask/value 一致；rdhb=rd1（非 rd0）、"
            "rdhc=rd2、hd=63（合法：hd ∈ 0..63 全部合法）"))

        # ── semantic：每条指令 × 每个 hd ∈ 0..63（全量，不抽样）──
        for hd in HD_ALL:
            exp = oracle(SRC_PATTERN, hd, op)
            cases.append(_case(
                rec, "semantic", word(rec, 1, 2, hd),
                {"rd": {"rd2": _hex64(SRC_PATTERN)}},
                _state(1, exp), None,
                "%s: hd=%d（有效位 [%d:0]，宽 %d），rd2=%s → rd1=%d"
                % (mnem, hd, hd, hd + 1, _hex64(SRC_PATTERN), exp)))

        # ── boundary：定值（有效位全 0）—— hd 全量，含 hd=63 ⇒ 64 ──
        for hd in HD_ALL:
            exp = oracle(0, hd, op)
            cases.append(_case(
                rec, "boundary", word(rec, 1, 2, hd),
                {"rd": {"rd2": "0x0000000000000000"}},
                _state(1, exp), None,
                "定值 %s hd=%d：rdHC[%d:0] 全 0 ⇒ 结果 %d（ctlz/cttz = hd+1，ctpop = 0）"
                % (mnem, hd, hd, exp)))

        # ── boundary：hd 以上的位不参与（掩码可观测）──
        cases.append(_case(
            rec, "boundary", word(rec, 1, 2, 7),
            {"rd": {"rd2": _hex64(0xFFFFFFFFFFFFFFFF)}},
            _state(1, oracle(0xFF, 7, op)), None,
            "掩码 %s hd=7：源 bit63..8 全 1 但有效位 rdHC[7:0]=0xFF ⇒ 与 hd 以上无关"))

        # ── boundary：hd=0（有效宽度 1）两个取值 ──
        for bit0 in (0, 1):
            cases.append(_case(
                rec, "boundary", word(rec, 1, 2, 0),
                {"rd": {"rd2": _hex64(bit0)}},
                _state(1, oracle(bit0, 0, op)), None,
                "边界 %s hd=0（宽 1）：rdHC[0]=%d ⇒ 结果 %d"
                % (mnem, bit0, oracle(bit0, 0, op))))

        # ── boundary：hd=63 全 1 ──
        cases.append(_case(
            rec, "boundary", word(rec, 1, 2, 63),
            {"rd": {"rd2": _hex64(MASK64)}},
            _state(1, oracle(MASK64, 63, op)), None,
            "边界 %s hd=63：源全 1 ⇒ ctlz=cttz=0、ctpop=64"))

        # ── boundary：单 bit 位置（位编号约定；大端下 bit0 = LSB）──
        cases.append(_case(
            rec, "boundary", word(rec, 1, 2, 63),
            {"rd": {"rd2": "0x0000000000000001"}},
            _state(1, oracle(1, 63, op)), None,
            "位编号 %s hd=63：仅 bit0=1 ⇒ ctlz 数到 63、cttz=0、ctpop=1"))
        cases.append(_case(
            rec, "boundary", word(rec, 1, 2, 63),
            {"rd": {"rd2": "0x8000000000000000"}},
            _state(1, oracle(1 << 63, 63, op)), None,
            "位编号 %s hd=63：仅 bit63=1 ⇒ ctlz=0、cttz=63、ctpop=1"))

        # ── boundary：rdHC = rd0（源读出 0，合法；不得触发 ILLI）──
        cases.append(_case(
            rec, "boundary", word(rec, 1, 0, 31), {},
            _state(1, oracle(0, 31, op)), None,
            "边界 %s hd=31：rdhc=rd0（源读出 0，合法）⇒ 结果 %d；不得触发 ILLI"
            % (mnem, oracle(0, 31, op))))

        # ── boundary：rdHB == rdHC（原地运算，允许）──
        cases.append(_case(
            rec, "boundary", word(rec, 3, 3, 15),
            {"rd": {"rd3": _hex64(0x000000000000FFFF)}},
            _state(3, oracle(0xFFFF, 15, op)), None,
            "边界 %s hd=15：rdhb == rdhc == rd3（原地运算，允许）" % mnem))

        # ── legality：目的 rd0 ⇒ ILLI（dst_rd0）——唯一非法来源 ──
        cases.append(_case(
            rec, "legality", word(rec, 0, 2, 63), {}, None, "ILLI",
            "legality %s: rdhb=rd0（目的）⇒ ILLI（dst_rd0）；hd=63 本身合法"
            % mnem, spec_cite=LEGALITY_CITE))

    return cases


# ────────────────────────────── 读真源 ──────────────────────────────

def load_opcodes() -> dict[str, dict]:
    recs = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    return {r["id"]: r for r in recs}


HEADER = (
    "# Generated by tools/testcases/generate_bitcnt_vectors.py — DO NOT EDIT\n"
    "# scope: m8（非 M1）——ctlz/cttz/ctpop（位扫描/位计数）向量\n"
    "# 独立 oracle：Python 大整数独立派生（三条独立路径）；不从 LLVM/QEMU 反推\n"
    "# 端序：大端（op 字节在最前）\n"
    "# 真源：contracts/opcodes.yaml + .tao/contracts/contract-isa.md §6.4.4\n"
    "# 重跑校验：python3 tools/testcases/generate_bitcnt_vectors.py --check\n\n"
)


def render(cases: list[dict]) -> str:
    return HEADER + yaml.dump(cases, default_flow_style=False,
                              allow_unicode=True, width=120, sort_keys=False)


# ────────────────────────────── 校验 ──────────────────────────────

def _fields_of(case: dict) -> tuple[int, int, int]:
    w = int(case["encoding"]["word"], 16)
    return (w >> 12) & 0x3F, (w >> 6) & 0x3F, w & 0x3F   # rdhb, rdhc, hd


def verify_semantics(cases: list[dict], errors: list[str]) -> int:
    """全量重算每个 semantic/boundary case 的期望值（非抽样）。"""
    n = 0
    for i, c in enumerate(cases):
        if c["class"] not in ("semantic", "boundary"):
            continue
        rid = c["id"]
        op = {"ctpop_orri_rd": "ctpop", "ctlz_orri_rd": "ctlz",
              "cttz_orri_rd": "cttz"}[rid]
        rdhb, rdhc, hd = _fields_of(c)
        src = 0
        if rdhc != 0:
            src = int(c["input_state"]["rd"]["rd%d" % rdhc], 16)
        exp = oracle(src, hd, op)
        got = c["expected_state"]["rd"]["rd%d" % rdhb]
        if int(got, 16) != exp:
            errors.append("case[%d] %s: expected %s != oracle %d"
                          % (i, rid, got, exp))
        n += 1
    return n


def verify_all_hd_legal(cases: list[dict], errors: list[str]) -> tuple[int, int]:
    """`hd ∈ 0..63` 全部合法：每个 hd 都须有 fault=None 的 semantic/boundary case。

    返回 (已覆盖的 hd 数, 期望数 64)。**无任何 hd 触发 ILLI**。
    """
    seen = set()
    for c in cases:
        if c["class"] not in ("semantic", "boundary"):
            continue
        if c.get("expected_fault") is not None:
            errors.append("hd ∈ 0..63 应全部合法，但 case id=%s 带 fault=%r"
                          % (c["id"], c["expected_fault"]))
            continue
        _rdhb, _rdhc, hd = _fields_of(c)
        seen.add(hd)
    missing = [h for h in HD_ALL if h not in seen]
    if missing:
        errors.append("hd 全量覆盖缺口（非全合法）：缺 hd=%s" % missing[:10])
    return len(seen), len(HD_ALL)


def verify_legality(cases: list[dict], errors: list[str]) -> int:
    """legality case 的 ILLI 依据只能是 rdhb == rd0（dst_rd0）。"""
    n = 0
    for i, c in enumerate(cases):
        if c["class"] != "legality":
            continue
        rdhb, _rdhc, _hd = _fields_of(c)
        if rdhb != 0:
            errors.append("case[%d] %s: legality case 无 ILLI 依据"
                          "（rdhb=%d ≠ 0；hd 本身全部合法）" % (i, c["id"], rdhb))
        if c["expected_fault"] != "ILLI":
            errors.append("case[%d] %s: legality case fault != ILLI" % (i, c["id"]))
        n += 1
    return n


def verify_words(cases: list[dict], by_id: dict[str, dict], errors: list[str]) -> int:
    n = 0
    for i, c in enumerate(cases):
        rec = by_id.get(c["id"])
        if rec is None:
            errors.append("case[%d]: id %s 不在 opcodes.yaml" % (i, c["id"]))
            continue
        w = int(c["encoding"]["word"], 16)
        mask = int(str(rec["mask"]), 16)
        value = int(str(rec["value"]), 16)
        if (w & mask) != value:
            errors.append("case[%d] %s: word 0x%08X & mask 0x%08X != value 0x%08X"
                          % (i, c["id"], w, mask, value))
        if c["format"] != rec["format"]:
            errors.append("case[%d] %s: format %s != 真源 %s"
                          % (i, c["id"], c["format"], rec["format"]))
        # 大端：字节序往返 + op 字节在最前（大端 = 最高有效字节在最前）
        be = w.to_bytes(4, "big")
        if int.from_bytes(be, "big") != w:
            errors.append("case[%d] %s: 大端字节序往返失败" % (i, c["id"]))
        if be[0] != (value >> 24) & 0xFF:
            errors.append("case[%d] %s: 大端下 op 字节须在最前（得 0x%02X，期望 0x%02X）"
                          % (i, c["id"], be[0], (value >> 24) & 0xFF))
        n += 1
    return n


def verify_coverage(cases: list[dict], errors: list[str]) -> tuple[int, int]:
    """每条指令 × 每个 hd ∈ 0..63 至少一个 semantic case（计数现场统计）。"""
    got: dict[tuple[str, int], int] = {}
    for c in cases:
        if c["class"] == "semantic":
            _rdhb, _rdhc, hd = _fields_of(c)
            got[(c["id"], hd)] = got.get((c["id"], hd), 0) + 1
    want = 0
    for rid in BITCNT_INSNS:
        for hd in HD_ALL:
            want += 1
            if (rid, hd) not in got:
                errors.append("覆盖缺口: %s 缺 hd=%d 的 semantic case" % (rid, hd))
    return len(got), want


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="由真源重派生并与已入库向量比对；不一致即非零退出")
    ap.add_argument("--self-check", action="store_true",
                    help="只跑 oracle 自检（两条独立路径 + 不变式）")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    by_id = load_opcodes()
    missing = [rid for rid in BITCNT_INSNS if rid not in by_id]
    if missing:
        print(f"ERROR: opcodes.yaml 缺 {missing}", file=sys.stderr)
        return 1
    for rid in BITCNT_INSNS:
        if by_id[rid].get("scope") != "m8":
            print(f"ERROR: {rid} scope != m8（真源与脚本口径不一致）", file=sys.stderr)
            return 1

    if args.self_check:
        n = 0
        for rid in BITCNT_INSNS:
            op = by_id[rid]["mnemonic"]
            for hd in HD_ALL:
                for src in (0, 1, 0xFF, 1 << 63, SRC_PATTERN, MASK64,
                            0x0123456789ABCDEF):
                    v = oracle(src, hd, op)          # 三条路径一致（内部断言）
                    width = hd + 1
                    valid = src & ((1 << width) - 1)
                    if valid == 0:
                        # 定值：ctlz/cttz = hd+1，ctpop = 0
                        expected_def = width if op != "ctpop" else 0
                        if v != expected_def:
                            raise AssertionError(
                                f"定值不符：{op} hd={hd} 全 0 ⇒ {v}，期望 {expected_def}")
                    elif not (0 <= v <= width):
                        raise AssertionError(
                            f"结果越界：{op} hd={hd} src={src:#x} ⇒ {v}")
                    n += 1
        print(f"oracle self-check: PASS（{n} 例；三条独立路径逐例一致 + 定值）")
        return 0

    cases = build_cases(by_id)
    errors: list[str] = []
    n_sem = verify_semantics(cases, errors)
    n_legal = verify_legality(cases, errors)
    n_enc = verify_words(cases, by_id, errors)
    n_hd, want_hd = verify_all_hd_legal(cases, errors)
    n_cov, want_cov = verify_coverage(cases, errors)
    content = render(cases)

    out = Path(args.out)
    if args.check:
        if not out.is_file():
            print(f"ERROR: {out} 不存在", file=sys.stderr)
            return 1
        have = out.read_text(encoding="utf-8")
        if have != content:
            errors.append(f"{out}: 与真源重派生结果不一致（生成器不幂等）")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"generate_bitcnt_vectors: {len(cases)} cases"
              f"（semantic/boundary {n_sem}, legality {n_legal}）-> {out}")

    print("bitcnt 向量统计（现场统计）：cases=%d，encoding/other=%d，"
          "semantic/boundary 重算=%d，legality 复核=%d，合法 hd 覆盖 %d/%d，"
          "合法 (id,hd) 覆盖 %d/%d"
          % (len(cases), n_enc - n_sem - n_legal, n_sem, n_legal,
             n_hd, want_hd, n_cov, want_cov))
    if errors:
        for e in errors:
            print(f"  FAIL: {e}", file=sys.stderr)
        print(f"generate_bitcnt_vectors --check: FAIL（{len(errors)} 项）", file=sys.stderr)
        return 1
    if args.check:
        print("generate_bitcnt_vectors --check: PASS（逐字节一致 + 全量 oracle 重算 + "
              "hd 全合法 + 大端）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
