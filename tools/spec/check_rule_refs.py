#!/usr/bin/env python3
"""规则引用双向门控（SPEC-071t）。

门控 1（ID 存在性）：每条指令 rule_refs 的所有 id 必须 ∈ legality_rules.yaml 的 id 集合。
门控 2（孤儿规则）：status: active 的规则至少被 1 条指令引用。
  豁免清单：{excp_ialign, excp_rasof, excp_rasuf, excp_undi}——
  运行时/兜底规则，不由编码 legality 表达式触发。
  status: deferred 允许 0 引用。

退出 0 = 通过；退出 1 = 失败（打印定位信息）。
"""

import os
import sys
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES_PATH = os.path.join(REPO_ROOT, "contracts", "opcodes.yaml")
RULES_PATH = os.path.join(REPO_ROOT, "contracts", "legality_rules.yaml")

# 显式豁免清单：active 规则中不由 legality 表达式引用的运行时/兜底规则。
# 检查器断言此清单恰好为这 4 条（多/少/改名 ⇒ 自身 FAIL）。
EXPECTED_ORPHAN_EXEMPTIONS = frozenset({
    "excp_ialign",
    "excp_rasof",
    "excp_rasuf",
    "excp_undi",
})


def main():
    with open(OPCODES_PATH, encoding="utf-8") as f:
        opcodes = yaml.safe_load(f)
    with open(RULES_PATH, encoding="utf-8") as f:
        rules_data = yaml.safe_load(f)

    rules = rules_data["rules"]
    valid_ids = {r["id"] for r in rules}

    # ── 自检：豁免清单恰好为预期集合 ──
    actual_exempt = set()
    for r in rules:
        if r["status"] == "active" and r["id"] not in {
            ref for oc in opcodes for ref in oc.get("rule_refs", [])
        }:
            actual_exempt.add(r["id"])

    # 预期豁免 = 那些 active 但不由 legality 映射的规则
    # 如果实际豁免集合 ≠ 预期集合，检查器自身报 FAIL
    if actual_exempt != EXPECTED_ORPHAN_EXEMPTIONS:
        print("FAIL: 孤儿豁免清单自检失败", file=sys.stderr)
        print(f"  预期: {sorted(EXPECTED_ORPHAN_EXEMPTIONS)}", file=sys.stderr)
        print(f"  实际: {sorted(actual_exempt)}", file=sys.stderr)
        missing = EXPECTED_ORPHAN_EXEMPTIONS - actual_exempt
        extra = actual_exempt - EXPECTED_ORPHAN_EXEMPTIONS
        if missing:
            print(f"  预期有但实际无（规则被意外引用）: {sorted(missing)}", file=sys.stderr)
        if extra:
            print(f"  实际有但预期无（新孤儿规则）: {sorted(extra)}", file=sys.stderr)
        sys.exit(1)

    # ── 门控 1：ID 存在性 ──
    gate1_fail = False
    for oc in opcodes:
        for ref in oc.get("rule_refs", []):
            if ref not in valid_ids:
                print(f"FAIL [Gate 1] 指令 {oc['id']}：rule_ref '{ref}' "
                      f"不在 legality_rules.yaml 中", file=sys.stderr)
                gate1_fail = True

    # ── 门控 2：孤儿规则 ──
    # 统计每条规则被多少条指令引用
    ref_count = {rid: 0 for rid in valid_ids}
    for oc in opcodes:
        for ref in oc.get("rule_refs", []):
            if ref in ref_count:
                ref_count[ref] += 1

    gate2_fail = False
    for r in rules:
        rid = r["id"]
        if r["status"] == "deferred":
            continue  # deferred 允许 0 引用
        # active 规则：豁免清单内的允许 0 引用
        if rid in EXPECTED_ORPHAN_EXEMPTIONS:
            continue
        if ref_count.get(rid, 0) == 0:
            print(f"FAIL [Gate 2] active 规则 '{rid}' 未被任何指令引用（孤儿）",
                  file=sys.stderr)
            gate2_fail = True

    if gate1_fail or gate2_fail:
        print(f"check-rule-refs: FAIL (gate1={'FAIL' if gate1_fail else 'OK'}, "
              f"gate2={'FAIL' if gate2_fail else 'OK'})", file=sys.stderr)
        sys.exit(1)

    # 打印摘要
    active_referenced = sum(1 for r in rules
                            if r["status"] == "active"
                            and r["id"] not in EXPECTED_ORPHAN_EXEMPTIONS
                            and ref_count.get(r["id"], 0) > 0)
    active_exempt = sum(1 for r in rules
                        if r["status"] == "active"
                        and r["id"] in EXPECTED_ORPHAN_EXEMPTIONS)
    deferred = sum(1 for r in rules if r["status"] == "deferred")
    total_refs = sum(ref_count.values())

    print(f"check-rule-refs: PASS "
          f"(规则 {len(rules)} 条: "
          f"active 被引用 {active_referenced}, "
          f"active 豁免 {active_exempt}, "
          f"deferred {deferred}; "
          f"指令引用 {total_refs} 处)")

    sys.exit(0)


if __name__ == "__main__":
    main()
