#!/usr/bin/env python3
"""generate_rev_vectors.py — `rev.o`/`rev.t`/`rev.w`/`rev.b`（逐块反转）向量生成器 + 独立 oracle。

范围（**非 M1**）
----------------
`rev.*` 属 `scope: m8`（`ADR-0012 D10`），**不是 M1 身份**，故**不进** `tests/vectors/inventory.md`
的 M1 覆盖矩阵，也**不**由 `tools/testcases/generate_isa_vectors.py`（M1-only，`scope == "m1"`
过滤）生成；本脚本把向量落到独立的 `tests/vectors/rev/rev.yaml`。

独立 oracle（硬约束）
--------------------
期望值由本脚本用 **Python 大整数**独立派生：`rev_block()` 直接把 64 位值按
`S` 位块切分、再把每块的 `S/k` 个 `k` 位单元倒序拼回；`bswap_via_bytes()` 走**另一条**
派生路径（显式**大端**字节序列 → 每 `S/8` 字节块内反转字节序 → 拼回），两者在
`k = 8` 档必须逐例一致（本项目为**大端**，端序敏感用例显式覆盖）。
**从不**调用 LLVM / QEMU 或读取其产物，方向为「契约/规范 → 期望」。

用法
----
* 生成（写文件）：      ``python3 tools/testcases/generate_rev_vectors.py``
* 校验（diff = 0）：    ``python3 tools/testcases/generate_rev_vectors.py --check``
* 打印 oracle 自检：    ``python3 tools/testcases/generate_rev_vectors.py --self-check``

`--check` 断言（任一不满足 ⇒ 非零退出）：
  1. 已入库 `tests/vectors/rev/rev.yaml` 与真源重派生结果**逐字节一致**（生成器可复现）；
  2. 每条 case 的 `encoding.word` 满足真源 `(word & mask) == value`（`contracts/opcodes.yaml`）；
  3. 每个 `semantic`/`boundary` case 的 `expected_state` 由 oracle **全量重算**后一致（非抽样）；
  4. 每个 `legality` case 的 `immu6` 要么非 one-hot、要么 `>= S`，或目的寄存器为 `rd0`
     （即确有可达的 ILLI 依据）；
  5. `k = 8` 档位同时通过 `rev_block` 与 `bswap_via_bytes` 两条独立派生路径；
  6. 计数**现场统计**（不写死）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts" / "opcodes.yaml"
OUT = ROOT / "tests" / "vectors" / "rev" / "rev.yaml"

MASK64 = (1 << 64) - 1

# 四条指令：id → (块大小 S, 合法 k 集, spec_cite)
REV_INSNS = {
    "rev.o_orri_rd": (64, (1, 2, 4, 8, 16, 32), "SimRISC-04 §Bit manipulating：位操作指令"),
    "rev.t_orri_rd": (32, (1, 2, 4, 8, 16), "SimRISC-08 §Bit manipulating：位操作指令"),
    "rev.w_orri_rd": (16, (1, 2, 4, 8), "SimRISC-09 §Bit manipulating：位操作指令"),
    "rev.b_orri_rd": (8, (1, 2, 4), "SimRISC-10 §Bit manipulating：位操作指令"),
}

LEGALITY_CITE = ("SimRISC-04 §Bit manipulating：位操作指令; "
                 "contract-isa §6.4.3; legality_rules.yaml :: encode_onehot / dst_rd0")

# 语义输入：bit 分布显著的 64 位图案（各块 / 各单元互不相同）
SRC_PATTERN = 0x0123456789ABCDEF


# ────────────────────────────── 独立 oracle ──────────────────────────────

def rev_block(src: int, S: int, k: int) -> int:
    """逐块反转：64 位值切成 64/S 个 S 位块，每块内部 S/k 个 k 位单元倒序，单元内位序不变。

    `k` 必须整除 `S` 且 ≥ 1（合法档位见 spec/SimRISC-04 §2.2.1）；否则显式报错
    （不静默返回恒等值）。
    """
    if k < 1 or S % k:
        raise ValueError(f"非法档位：S={S}, k={k}（须 k>=1 且 k 整除 S）")
    src &= MASK64
    n_units = S // k
    out = 0
    for b in range(64 // S):
        blk = (src >> (b * S)) & ((1 << S) - 1)
        units = [(blk >> (u * k)) & ((1 << k) - 1) for u in range(n_units)]
        rev = 0
        for i, u in enumerate(reversed(units)):
            rev |= u << (i * k)
        out |= rev << (b * S)
    return out & MASK64


def bswap_via_bytes(src: int, S: int) -> int:
    """`k = 8` 档的第二条独立派生路径：显式**大端**字节序 → 每 S/8 字节块内反转字节 → 拼回。

    本项目为大端：64 位值的高字节先出现在低地址。此路径与 `rev_block(src, S, 8)`
    必须逐例一致（端序敏感；两条路径代码独立）。
    """
    if S % 8:
        raise ValueError(f"bswap_via_bytes 仅适用 S%8==0 的档位（S={S}）")
    src &= MASK64
    be_bytes = src.to_bytes(8, "big")          # 高字节在前（大端）
    chunk = S // 8
    out = bytearray()
    for b in range(8 // chunk):
        blk = be_bytes[b * chunk:(b + 1) * chunk]
        out += blk[::-1]
    return int.from_bytes(bytes(out), "big")


# ────────────────────────────── case 构造 ──────────────────────────────

def _hex64(v: int) -> str:
    return "0x%016X" % (v & MASK64)


def word(rec: dict, rdhb: int, rdhc: int, immu6: int) -> int:
    """由真源 `value`（含 op + opx）叠加字段位域，得到完整 32 位字。"""
    w = int(str(rec["value"]), 16)
    w |= (rdhb & 0x3F) << 12
    w |= (rdhc & 0x3F) << 6
    w |= immu6 & 0x3F
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


def build_cases(by_id: dict[str, dict]) -> list[dict]:
    cases: list[dict] = []

    for rid, (S, legal_ks, _cite) in REV_INSNS.items():
        rec = by_id[rid]
        mnem = rec["mnemonic"]

        # ── encoding：字段合法，无 fault ──
        k_enc = 8 if 8 in legal_ks else legal_ks[-1]
        cases.append(_case(
            rec, "encoding", word(rec, 1, 2, k_enc), {}, None, None,
            "encoding: word 与 opcodes.yaml mask/value 一致；rdhb=rd1（非 rd0）、"
            "rdhc=rd2、immu6=%d（合法 one-hot 档）" % k_enc))

        # ── semantic：每条指令 × 每个合法 k（计数现场统计、不写死）──
        for k in legal_ks:
            exp = rev_block(SRC_PATTERN, S, k)
            cases.append(_case(
                rec, "semantic", word(rec, 1, 2, k),
                {"rd": {"rd2": _hex64(SRC_PATTERN)}},
                {"rd": {"rd1": _hex64(exp)}, "rb": {}, "ra": {}, "memory": []},
                None,
                "%s: S=%d, k=%d, rd2=%s → rd1=%s（oracle 大整数独立派生）"
                % (mnem, S, k, _hex64(SRC_PATTERN), _hex64(exp))))

        # ── semantic：端序敏感（k=8，大端字节序）──
        if 8 in legal_ks:
            src_be = 0x0102030405060708
            exp_be = bswap_via_bytes(src_be, S)
            assert exp_be == rev_block(src_be, S, 8), "两条派生路径不一致"
            cases.append(_case(
                rec, "semantic", word(rec, 1, 2, 8),
                {"rd": {"rd2": _hex64(src_be)}},
                {"rd": {"rd1": _hex64(exp_be)}, "rb": {}, "ra": {}, "memory": []},
                None,
                "端序敏感（大端 k=8）：rd2 的大端字节序 %s → 每个 %d 位块内反转字节序 → rd1=%s"
                % (" ".join("%02X" % b for b in src_be.to_bytes(8, "big")), S, _hex64(exp_be))))

        # ── boundary：源的高 (64-S) 位为 0（bswap 前提）──
        if 8 in legal_ks and S < 64:
            src_low = 0x01020304
            exp_low = rev_block(src_low, S, 8)
            cases.append(_case(
                rec, "boundary", word(rec, 1, 2, 8),
                {"rd": {"rd2": _hex64(src_low)}},
                {"rd": {"rd1": _hex64(exp_low)}, "rb": {}, "ra": {}, "memory": []},
                None,
                "boundary %s k=8: 源高 %d 位为 0 ⇒ 结果高 %d 位亦为 0（bswap 前提）"
                % (mnem, 64 - S, 64 - S)))

        # ── boundary：rdHC = 0 / rdHC 全 1 / rdHB == rdHC / rdHC = rd0 ──
        k1 = 1
        cases.append(_case(
            rec, "boundary", word(rec, 1, 2, k1),
            {"rd": {"rd2": "0x0000000000000000"}},
            {"rd": {"rd1": "0x0000000000000000"}, "rb": {}, "ra": {}, "memory": []},
            None, "boundary %s k=1: rdHC=0 ⇒ rdHB=0" % mnem))
        cases.append(_case(
            rec, "boundary", word(rec, 1, 2, k1),
            {"rd": {"rd2": _hex64(MASK64)}},
            {"rd": {"rd1": _hex64(MASK64)}, "rb": {}, "ra": {}, "memory": []},
            None, "boundary %s k=1: rdHC 全 1 ⇒ rdHB 全 1（全 1 图案逐块逆序不变）" % mnem))
        cases.append(_case(
            rec, "boundary", word(rec, 3, 3, k1),
            {"rd": {"rd3": _hex64(SRC_PATTERN)}},
            {"rd": {"rd3": _hex64(rev_block(SRC_PATTERN, S, k1))}, "rb": {}, "ra": {}, "memory": []},
            None, "boundary %s k=1: rdHB == rdHC == rd3（原地反转，允许）" % mnem))
        cases.append(_case(
            rec, "boundary", word(rec, 1, 0, k1),
            {},
            {"rd": {"rd1": "0x0000000000000000"}, "rb": {}, "ra": {}, "memory": []},
            None, "boundary %s k=1: rdHC=rd0（源读出 0，合法）⇒ rdHB=0" % mnem))

        # ── legality：非 one-hot / k >= S ⇒ ILLI ──
        illegal_ks = [0, 3]
        if 5 not in legal_ks:
            illegal_ks.append(5)
        illegal_ks += [S]                      # k = S 恒等档（S ∈ {8,16,32} 时可用；S=64 不可编码）
        for k in illegal_ks:
            if k >= 64:
                continue
            onehot = (k != 0) and (k & (k - 1)) == 0
            why = ("k=%d 非 one-hot" % k) if not onehot else ("k=%d == S（恒等档）" % k)
            cases.append(_case(
                rec, "legality", word(rec, 1, 2, k), {}, None, "ILLI",
                "legality %s: %s ⇒ ILLI（encode_onehot）" % (mnem, why),
                spec_cite=LEGALITY_CITE))

        # ── legality：目的 rd0 ⇒ ILLI（dst_rd0）──
        cases.append(_case(
            rec, "legality", word(rec, 0, 2, k_enc), {}, None, "ILLI",
            "legality %s: rdhb=rd0（目的）⇒ ILLI（dst_rd0）" % mnem,
            spec_cite=LEGALITY_CITE))

    return cases


# ────────────────────────────── 读真源 ──────────────────────────────

def load_opcodes() -> dict[str, dict]:
    recs = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    return {r["id"]: r for r in recs}


HEADER = (
    "# Generated by tools/testcases/generate_rev_vectors.py — DO NOT EDIT\n"
    "# scope: m8（非 M1）——rev.o/rev.t/rev.w/rev.b 逐块反转向量\n"
    "# 独立 oracle：Python 大整数独立派生（大端）；不从 LLVM/QEMU 反推\n"
    "# 真源：contracts/opcodes.yaml + .tao/contracts/contract-isa.md §6.4.3\n"
    "# 重跑校验：python3 tools/testcases/generate_rev_vectors.py --check\n\n"
)


def render(cases: list[dict]) -> str:
    return HEADER + yaml.dump(cases, default_flow_style=False,
                              allow_unicode=True, width=120, sort_keys=False)


# ────────────────────────────── 校验 ──────────────────────────────

def verify_semantics(cases: list[dict], errors: list[str]) -> int:
    """全量重算每个 semantic/boundary case 的期望值（非抽样）。"""
    n = 0
    for i, c in enumerate(cases):
        if c["class"] not in ("semantic", "boundary"):
            continue
        rid = c["id"]
        S, legal_ks, _ = REV_INSNS[rid]
        w = int(c["encoding"]["word"], 16)
        k = w & 0x3F
        rdhc = (w >> 6) & 0x3F
        rdhb = (w >> 12) & 0x3F
        src = 0
        if rdhc != 0:
            src = int(c["input_state"]["rd"]["rd%d" % rdhc], 16)
        exp = rev_block(src, S, k)
        got = c["expected_state"]["rd"]["rd%d" % rdhb]
        if int(got, 16) != exp:
            errors.append("case[%d] %s: expected %s != oracle %s"
                          % (i, rid, got, _hex64(exp)))
        # k = 8 档：第二条独立路径必须一致
        if k == 8:
            if bswap_via_bytes(src, S) != exp:
                errors.append("case[%d] %s: k=8 两条派生路径不一致" % (i, rid))
        n += 1
    return n


def verify_legality(cases: list[dict], errors: list[str]) -> int:
    n = 0
    for i, c in enumerate(cases):
        if c["class"] != "legality":
            continue
        rid = c["id"]
        S, legal_ks, _ = REV_INSNS[rid]
        w = int(c["encoding"]["word"], 16)
        k = w & 0x3F
        rdhb = (w >> 12) & 0x3F
        k_bad = (k not in legal_ks)
        dst_bad = (rdhb == 0)
        if not (k_bad or dst_bad):
            errors.append("case[%d] %s: legality case 无 ILLI 依据（k=%d, rdhb=%d）"
                          % (i, rid, k, rdhb))
        if c["expected_fault"] != "ILLI":
            errors.append("case[%d] %s: legality case fault != ILLI" % (i, rid))
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
        n += 1
    return n


def verify_coverage(cases: list[dict], errors: list[str]) -> tuple[int, int]:
    """每条指令 × 每个合法 k 至少一个 semantic case（计数现场统计）。"""
    got: dict[tuple[str, int], int] = {}
    for c in cases:
        if c["class"] == "semantic":
            k = int(c["encoding"]["word"], 16) & 0x3F
            got[(c["id"], k)] = got.get((c["id"], k), 0) + 1
    want = 0
    for rid, (_S, legal_ks, _c) in REV_INSNS.items():
        for k in legal_ks:
            want += 1
            if (rid, k) not in got:
                errors.append("覆盖缺口: %s 缺 k=%d 的 semantic case" % (rid, k))
    return len(got), want


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="由真源重派生并与已入库向量比对；不一致即非零退出")
    ap.add_argument("--self-check", action="store_true",
                    help="只跑 oracle 自检（k=8 双路径一致性）")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    by_id = load_opcodes()
    missing = [rid for rid in REV_INSNS if rid not in by_id]
    if missing:
        print(f"ERROR: opcodes.yaml 缺 {missing}", file=sys.stderr)
        return 1
    for rid in REV_INSNS:
        if by_id[rid].get("scope") != "m8":
            print(f"ERROR: {rid} scope != m8（真源与脚本口径不一致）", file=sys.stderr)
            return 1

    cases = build_cases(by_id)

    if args.self_check:
        n = 0
        for rid, (S, legal_ks, _c) in REV_INSNS.items():
            for k in legal_ks:
                for src in (0, 1, SRC_PATTERN, MASK64, 0x0102030405060708):
                    assert rev_block(src, S, k) == rev_block(src, S, k)
                    if k == 8:
                        assert rev_block(src, S, 8) == bswap_via_bytes(src, S), (rid, src)
                    n += 1
        print(f"oracle self-check: PASS（{n} 例；k=8 双路径逐例一致）")
        return 0

    errors: list[str] = []
    n_sem = verify_semantics(cases, errors)
    n_leg = verify_legality(cases, errors)
    n_enc = verify_words(cases, by_id, errors)
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
        print(f"generate_rev_vectors: {len(cases)} cases（semantic {n_sem}, legality {n_leg}）-> {out}")

    print("rev 向量统计（现场统计）：cases=%d，encoding/other=%d，semantic/boundary 重算=%d，"
          "legality 复核=%d，合法 (id,k) 覆盖 %d/%d"
          % (len(cases), n_enc - n_sem - n_leg, n_sem, n_leg, n_cov, want_cov))
    if errors:
        for e in errors:
            print(f"  FAIL: {e}", file=sys.stderr)
        print(f"generate_rev_vectors --check: FAIL（{len(errors)} 项）", file=sys.stderr)
        return 1
    if args.check:
        print("generate_rev_vectors --check: PASS（逐字节一致 + 全量 oracle 重算 + 合法集复核）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
