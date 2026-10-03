#!/usr/bin/env python3
"""check_fp_contract.py — FP 语义合约门控（SPEC-087t）。

职责（可执行、可失败；SPEC-087t §5.1）：
  1. 覆盖双向一致：fp_semantics.yaml 的 id 集合 == opcodes.yaml 中
     scope=="fp" 的 id 集合；计数 == 60（缺/多/重复 ⇒ FAIL）。
  2. 族合法且计数：每条 family ∈ 12 族枚举；每族计数 == 约定值。
  3. spec_cite 非空且匹配 ^SimRISC-0[0-7]\\b。
  4. 族完备：families 段为每族声明 required_keys（须 == 预期键集）；
     每条记录的族 required_keys 均存在（缺失 ⇒ FAIL）。
  5. legality 双向：每条 legality_refs ∈ legality_rules.yaml 的 id 集合；
     5 条 FP 规则（dst_rf0/encode_fp_root_n/mreg_zero/mreg_range_overflow/
     mreg_range_overlap）各被**精确条数**条 FP id 引用（28/28/4/35/2，SPEC-088t）；
     仅 FP 专属规则（dst_rf0/encode_fp_root_n）不得被 scope != fp 的 opcodes 记录引用
     （mreg_* 同时服务 M1，被非 fp 记录引用是预期）。
  6. 叙述锚点可达：每条 semantics_ref = contract-fp.md#<anchor>，且
     contract-fp.md 含 <a id="<anchor>">。
  7. 合规版本头：contract-fp.md 首个版本头行含 [SimRISC- 引用。

退出 0 = 通过；退出 1 = 失败。输出「检查名 + 期望/实际 + 退出码」。

Spec-first：判据来自 contracts/opcodes.yaml、contracts/legality_rules.yaml、
.tao/knowledge/contract-fp.md 与 SPEC-087t（不从 LLVM/QEMU 反推）。

Usage: python3 tools/spec/check_fp_contract.py [--repo-root .]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

EXPECTED_TOTAL = 60

# 12 族枚举与计数（SPEC-087t §1.3）
FAMILY_COUNTS = {
    "convert_ff": 4,
    "convert_f2i": 8,
    "convert_i2f": 8,
    "arith": 12,
    "root": 2,
    "sign": 4,
    "compare": 4,
    "classify": 2,
    "cs_rf": 5,
    "rf_mem": 8,
    "rf_move": 2,
    "set_w_rf": 1,
}

# FP 相关合法性规则（5 条，SPEC-088t §2.5）：各须被精确条数条 FP id 引用。
# dst_rf0/encode_fp_root_n 为 FP 专属；mreg_zero/mreg_range_overflow/mreg_range_overlap
# 与 M1 共享（被 M1 的 rule_refs 引用属预期）。
FP_RULES = ("dst_rf0", "encode_fp_root_n", "mreg_zero",
            "mreg_range_overflow", "mreg_range_overlap")

# 每条 FP 规则须被 FP id 引用的精确条数（SPEC-088t §2.6；收紧后才可对
# 「漏一条 / 漏源侧」判 FAIL）。
FP_RULE_EXACT = {
    "dst_rf0": 35,
    "encode_fp_root_n": 2,
    "mreg_zero": 28,
    "mreg_range_overflow": 28,
    "mreg_range_overlap": 4,
}

# 仅 FP 专属规则不得被 scope != fp 的 opcodes 记录引用
# （mreg_* 共享给 M1，被非 fp 记录引用是预期）。
FP_SPECIFIC_RULES = ("dst_rf0", "encode_fp_root_n")

# 每条指令记录必须携带的键（与 families 段的 required_keys 声明一致）
REQUIRED_KEYS = ["family", "spec_cite", "semantics_ref", "legality_refs"]

RE_SPEC_CITE = re.compile(r"^SimRISC-0[0-7]\b")
RE_SEM_REF = re.compile(r"^contract-fp\.md#([A-Za-z0-9_\-]+)$")
RE_VERSION_HEADER = re.compile(r"^>\s*\*\*版本[：:]\s*\d+\.\d+\.\d+\s*\*\*")

results: list[tuple[str, str, str, bool]] = []


def record(name: str, expected, actual, ok: bool | None = None) -> bool:
    if ok is None:
        ok = str(expected) == str(actual)
    results.append((name, str(expected), str(actual), ok))
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=None,
                        help="仓库根（默认: 脚本向上 2 级）")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve() if args.repo_root \
        else Path(__file__).resolve().parents[2]

    opcodes_path = repo / "contracts" / "opcodes.yaml"
    rules_path = repo / "contracts" / "legality_rules.yaml"
    sem_path = repo / "contracts" / "fp_semantics.yaml"
    contract_path = repo / ".tao" / "knowledge" / "contract-fp.md"

    for path in (opcodes_path, rules_path, sem_path, contract_path):
        if not path.is_file():
            print(f"check-fp-contract: FAIL — 缺少文件: {path}", file=sys.stderr)
            print("exit 1")
            return 1

    opcodes = yaml.safe_load(opcodes_path.read_text(encoding="utf-8"))
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))["rules"]
    sem = yaml.safe_load(sem_path.read_text(encoding="utf-8"))
    contract_text = contract_path.read_text(encoding="utf-8")

    failures: list[str] = []

    # ── 1. 覆盖双向一致 ──────────────────────────────────────────────────
    fp_ids = {o["id"] for o in opcodes if o.get("scope") == "fp"}
    insns = sem.get("instructions") or []
    sem_ids = [i.get("id") for i in insns]
    sem_id_set = set(sem_ids)

    if not record("id 计数", EXPECTED_TOTAL, len(sem_ids)):
        failures.append(f"id 计数: 期望 {EXPECTED_TOTAL}，实际 {len(sem_ids)}")
    if not record("id 无重复", len(sem_ids), len(sem_id_set)):
        failures.append(f"id 重复: 列表 {len(sem_ids)}，去重 {len(sem_id_set)}")

    missing = sorted(fp_ids - sem_id_set)
    extra = sorted(sem_id_set - fp_ids)
    if not record("覆盖（opcodes 侧缺）", 0, len(missing)):
        failures.append("fp_semantics 缺少 opcodes 侧 id: " + ", ".join(missing[:10]))
    if not record("覆盖（fp_semantics 多）", 0, len(extra)):
        failures.append("fp_semantics 多出 opcodes 侧 id: " + ", ".join(extra[:10]))

    # ── 2. 族合法且计数 ──────────────────────────────────────────────────
    families = sem.get("families") or {}
    bad_family = sorted({i.get("family") for i in insns
                         if i.get("family") not in FAMILY_COUNTS})
    if not record("family ∈ 12 族", 0, len(bad_family)):
        failures.append("非法族: " + ", ".join(str(b) for b in bad_family[:10]))

    declared = sorted(families.keys())
    if not record("families 段族集合", ",".join(sorted(FAMILY_COUNTS)),
                  ",".join(declared)):
        failures.append("families 段族集合不一致")

    cnt = Counter(i.get("family") for i in insns)
    for fam, exp in FAMILY_COUNTS.items():
        act = cnt.get(fam, 0)
        if not record(f"族计数 {fam}", exp, act):
            failures.append(f"族计数 {fam}: 期望 {exp}，实际 {act}")

    # ── 3. spec_cite 合规 ────────────────────────────────────────────────
    bad_cite = [i.get("id") for i in insns
                if not isinstance(i.get("spec_cite"), str)
                or not RE_SPEC_CITE.match(i.get("spec_cite", ""))]
    if not record("spec_cite 合规", 0, len(bad_cite)):
        failures.append("spec_cite 缺失/不合规: " + ", ".join(bad_cite[:10]))

    # ── 4. 族完备（required_keys）────────────────────────────────────────
    bad_decl = []
    for fam in FAMILY_COUNTS:
        fdef = families.get(fam)
        if not isinstance(fdef, dict) \
                or sorted(fdef.get("required_keys") or []) != sorted(REQUIRED_KEYS):
            bad_decl.append(fam)
    if not record("每族 required_keys 声明", 0, len(bad_decl)):
        failures.append("required_keys 声明缺失/不符: " + ", ".join(bad_decl[:10]))

    bad_keys = []
    for i in insns:
        fdef = families.get(i.get("family")) or {}
        for key in (fdef.get("required_keys") or []):
            if key not in i:
                bad_keys.append(f"{i.get('id')}:{key}")
    if not record("记录含族 required_keys", 0, len(bad_keys)):
        failures.append("记录缺 required_keys: " + ", ".join(bad_keys[:10]))

    # ── 5. legality 双向 ─────────────────────────────────────────────────
    rule_ids = {r["id"] for r in rules}
    ref_pairs = [(i.get("id"), ref) for i in insns
                 for ref in (i.get("legality_refs") or [])]
    bad_ref = [ref for _, ref in ref_pairs if ref not in rule_ids]
    if not record("legality_refs 均存在", 0, len(bad_ref)):
        failures.append("legality_refs 指向不存在的规则: "
                        + ", ".join(sorted(set(bad_ref))[:10]))

    ref_counts = Counter(ref for _, ref in ref_pairs)
    for rule in FP_RULES:
        n = ref_counts.get(rule, 0)
        exp = FP_RULE_EXACT[rule]
        if not record(f"FP 规则被引用 {rule}", exp, n):
            failures.append(f"FP 规则 {rule} 引用数: 期望 {exp}，实际 {n}")

    nonfp_hits = [f"{o['id']}:{ref}" for o in opcodes
                  if o.get("scope") != "fp"
                  for ref in (o.get("rule_refs") or []) if ref in FP_SPECIFIC_RULES]
    if not record("FP 专属规则未被非 fp 记录引用", 0, len(nonfp_hits)):
        failures.append("非 fp 记录引用了 FP 专属规则: " + ", ".join(nonfp_hits[:10]))

    # ── 6. 叙述锚点可达 ──────────────────────────────────────────────────
    refs_to_check: list[tuple[str, str]] = []
    for i in insns:
        refs_to_check.append((i.get("id", "?"), i.get("semantics_ref", "")))
    for fam, fdef in families.items():
        if isinstance(fdef, dict):
            refs_to_check.append((f"family:{fam}", fdef.get("semantics_ref", "")))

    bad_anchor = []
    for owner, sr in refs_to_check:
        m = RE_SEM_REF.match(sr) if isinstance(sr, str) else None
        if not m or f'<a id="{m.group(1)}">' not in contract_text:
            bad_anchor.append(owner)
    if not record("semantics_ref 锚点可达", 0, len(bad_anchor)):
        failures.append("semantics_ref 锚点不可达: " + ", ".join(bad_anchor[:10]))

    # ── 7. 合规版本头 ────────────────────────────────────────────────────
    header = None
    for line in contract_text.splitlines():
        if RE_VERSION_HEADER.match(line.strip()):
            header = line
            break
    header_ok = header is not None and "[SimRISC-" in header
    if not record("contract-fp.md 合规版本头", "含 [SimRISC-",
                  "含" if header_ok else ("无版本头" if header is None else "缺 spec 引用"),
                  ok=header_ok):
        failures.append("contract-fp.md 版本头缺失或未含 [SimRISC- 引用")

    # ── 输出 ─────────────────────────────────────────────────────────────
    print("check-fp-contract:")
    for name, exp, act, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: 期望={exp} 实际={act}")

    if failures:
        for f in failures:
            print(f"check-fp-contract: FAIL — {f}", file=sys.stderr)
        print(f"check-fp-contract: FAILED ({len(failures)} 项)", file=sys.stderr)
        print("exit 1")
        return 1

    print("check-fp-contract: PASS")
    print("exit 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
