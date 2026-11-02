#!/usr/bin/env python3
"""规则引用双向门控（SPEC-071t；INFRA-102t 去代码内常量）。

门控 1（ID 存在性）：每条指令 rule_refs 的所有 id 必须 ∈ legality_rules.yaml 的 id 集合。

门控 2（孤儿规则）：`status: active` 且 0 引用的规则必须出现在**显式数据文件**
`tools/spec/data/rule_ref_exemptions.yaml`（运行时/兜底规则，不由编码 legality
表达式触发）。该文件是唯一真源——此前豁免集合写死在代码里（`EXPECTED_ORPHAN_EXEMPTIONS`），
每增删一条运行时规则都要改脚本。

数据文件断言（fail-closed，「文件被引用」）：
  * 文件存在且可解析；`exemptions` 非空（空清单 ⇒ FAIL，防「清空即放行」）；
  * 每条含非空 `id` + `reason`，id 唯一；
  * 每个 id 存在于 legality_rules.yaml 且 `status == active`；
  * 现场孤儿集合 == 文件 id 集合（双向：新孤儿/过期条目都红）。
  `status: deferred` 允许 0 引用。

退出 0 = 通过；退出 1 = 失败（打印定位信息）。

Usage: python3 tools/spec/check_rule_refs.py [--repo-root .] [--self-test]
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
OPCODES_REL = "contracts/opcodes.yaml"
RULES_REL = "contracts/legality_rules.yaml"
EXEMPTIONS_REL = "tools/spec/data/rule_ref_exemptions.yaml"


def load_exemptions(path: Path) -> tuple[set[str], list[str]]:
    """读取豁免数据文件；返回 (id 集合, 结构问题列表)。"""
    problems: list[str] = []
    if not path.is_file():
        return set(), [f"豁免数据文件缺失: {path}（孤儿规则必须显式登记）"]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return set(), [f"豁免数据文件不可解析: {path}: {exc}"]
    if not isinstance(data, dict):
        return set(), [f"豁免数据文件顶层必须是映射: {path}"]
    entries = data.get("exemptions")
    if not isinstance(entries, list) or not entries:
        return set(), [f"豁免数据文件 exemptions 为空/非列表（vacuous）: {path}"]
    ids: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"exemptions[{i}] 不是映射")
            continue
        rid = entry.get("id")
        reason = entry.get("reason")
        if not isinstance(rid, str) or not rid.strip():
            problems.append(f"exemptions[{i}] 缺非空 id")
            continue
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f"exemptions[{i}] ({rid}) 缺非空 reason")
        if rid in ids:
            problems.append(f"exemptions 重复 id: {rid}")
        ids.add(rid)
    return ids, problems


def run(repo: Path) -> int:
    opcodes_path = repo / OPCODES_REL
    rules_path = repo / RULES_REL
    exemptions_path = repo / EXEMPTIONS_REL

    if not opcodes_path.is_file() or not rules_path.is_file():
        print(f"check-rule-refs: FAIL — 缺少输入: {opcodes_path} / {rules_path}",
              file=sys.stderr)
        return 1
    opcodes = yaml.safe_load(opcodes_path.read_text(encoding="utf-8"))
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))["rules"]
    valid_ids = {r["id"] for r in rules}
    status_by_id = {r["id"]: r.get("status") for r in rules}

    exempt_ids, problems = load_exemptions(exemptions_path)
    failures: list[str] = list(problems)

    # ── 门控 1：ID 存在性 ──
    gate1_fail = False
    for oc in opcodes:
        for ref in oc.get("rule_refs", []):
            if ref not in valid_ids:
                print(f"FAIL [Gate 1] 指令 {oc['id']}：rule_ref '{ref}' "
                      f"不在 legality_rules.yaml 中", file=sys.stderr)
                gate1_fail = True

    # ── 数据文件自身合法性 ──
    stale = sorted(exempt_ids - valid_ids)
    not_active = sorted(rid for rid in exempt_ids & valid_ids
                        if status_by_id.get(rid) != "active")
    if stale:
        failures.append("豁免条目不存在于 legality_rules.yaml: " + ", ".join(stale))
    if not_active:
        failures.append("豁免条目不是 status: active: " + ", ".join(not_active))

    # ── 门控 2：现场孤儿集合 == 数据文件集合（双向）──
    referenced = {ref for oc in opcodes for ref in oc.get("rule_refs", [])}
    live_orphans = {r["id"] for r in rules
                    if r.get("status") == "active" and r["id"] not in referenced}
    new_orphans = sorted(live_orphans - exempt_ids)
    stale_exemptions = sorted(exempt_ids - live_orphans)
    if new_orphans:
        failures.append("未登记的孤儿规则（active 且 0 引用）: "
                        + ", ".join(new_orphans))
    if stale_exemptions:
        failures.append("豁免条目已非孤儿（被引用或非 active）: "
                        + ", ".join(stale_exemptions))

    # 现场信息（非判据）
    ref_count: dict[str, int] = {rid: 0 for rid in valid_ids}
    for oc in opcodes:
        for ref in oc.get("rule_refs", []):
            if ref in ref_count:
                ref_count[ref] += 1

    print(f"[{'PASS' if not problems else 'FAIL'}] 豁免数据文件已加载: "
          f"{EXEMPTIONS_REL}（{len(exempt_ids)} 条；数据文件被本门控引用）")
    print(f"[{'PASS' if not new_orphans else 'FAIL'}] 未登记孤儿规则: "
          f"期望=0 个 实际={len(new_orphans)} 个")
    print(f"[{'PASS' if not stale_exemptions else 'FAIL'}] 过期豁免条目: "
          f"期望=0 个 实际={len(stale_exemptions)} 个")
    print(f"[{'PASS' if not stale else 'FAIL'}] 豁免 id 存在性: "
          f"期望=0 个 实际={len(stale)} 个")
    print(f"[{'PASS' if not not_active else 'FAIL'}] 豁免 id 状态 active: "
          f"期望=0 个 实际={len(not_active)} 个")

    if gate1_fail:
        failures.append("门控 1（rule_refs id 存在性）失败")

    if failures:
        for f in failures:
            print(f"check-rule-refs: FAIL — {f}", file=sys.stderr)
        print(f"check-rule-refs: FAIL (gate1={'FAIL' if gate1_fail else 'PASS'})",
              file=sys.stderr)
        return 1

    active_referenced = sum(1 for r in rules
                            if r.get("status") == "active"
                            and r["id"] not in exempt_ids
                            and ref_count.get(r["id"], 0) > 0)
    deferred = sum(1 for r in rules if r.get("status") == "deferred")
    total_refs = sum(ref_count.values())
    print(f"check-rule-refs: PASS "
          f"(规则 {len(rules)} 条: "
          f"active 被引用 {active_referenced}, "
          f"active 豁免 {len(exempt_ids)}（数据文件）, "
          f"deferred {deferred}; "
          f"指令引用 {total_refs} 处)")
    return 0


def self_test() -> int:
    """临时树注入：逐例断言 rc（数据文件为唯一真源，含「文件缺失/清空」路径）。"""
    repo = Path(__file__).resolve().parents[2]
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "INFRA-102t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="check-rule-refs-", dir=tmp_root))
    try:
        for rel in (OPCODES_REL, RULES_REL, EXEMPTIONS_REL):
            dst = tmpdir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((repo / rel).read_bytes())
        base_ex = (tmpdir / EXEMPTIONS_REL).read_text(encoding="utf-8")
        ex_data = yaml.safe_load(base_ex)
        op_path = tmpdir / OPCODES_REL
        ex_path = tmpdir / EXEMPTIONS_REL

        def write_ex(data) -> None:
            ex_path.write_text(yaml.safe_dump(data, allow_unicode=True,
                                              sort_keys=False))

        def reset() -> None:
            op_path.write_bytes((repo / OPCODES_REL).read_bytes())
            ex_path.write_text(base_ex, encoding="utf-8")

        def op_mut(fn) -> None:
            op = yaml.safe_load((repo / OPCODES_REL).read_text(encoding="utf-8"))
            fn(op)
            op_path.write_text(yaml.safe_dump(op, allow_unicode=True,
                                              sort_keys=False))

        def drop_ref(op):
            for oc in op:
                if oc.get("rule_refs"):
                    oc["rule_refs"] = list(oc["rule_refs"])[1:]
                    return
            raise AssertionError("no rule_refs")

        def add_bogus_ref(op):
            op[0]["rule_refs"] = list(op[0].get("rule_refs") or []) + ["no_such_rule"]

        cases = [
            ("baseline", 0),
            ("exemptions-file-missing", 1),
            ("exemptions-empty", 1),
            ("exemptions-stale-entry", 1),
            ("new-orphan-rule", 1),
            ("exempted-rule-now-referenced", 1),
            ("gate1-unknown-rule-ref", 1),
            ("exemption-missing-reason", 1),
        ]
        ok = True
        for i, (name, expect_rc) in enumerate(cases, 1):
            reset()
            if name == "exemptions-file-missing":
                ex_path.unlink()
            elif name == "exemptions-empty":
                write_ex({"version": 1, "exemptions": []})
            elif name == "exemptions-stale-entry":
                data = yaml.safe_load(base_ex)
                data["exemptions"].append({"id": "no_such_rule", "reason": "x"})
                write_ex(data)
            elif name == "new-orphan-rule":
                # 删掉一条豁免 ⇒ 该 active 规则变成未登记孤儿（反向：文件少一条）。
                data = yaml.safe_load(base_ex)
                data["exemptions"] = data["exemptions"][1:]
                write_ex(data)
            elif name == "exempted-rule-now-referenced":
                # 给某条被豁免的规则制造引用 ⇒ 豁免条目过期。
                target = ex_data["exemptions"][0]["id"]
                op_mut(lambda op: op[0].__setitem__(
                    "rule_refs", list(op[0].get("rule_refs") or []) + [target]))
            elif name == "gate1-unknown-rule-ref":
                op_mut(add_bogus_ref)
            elif name == "exemption-missing-reason":
                data = yaml.safe_load(base_ex)
                data["exemptions"][0]["reason"] = ""
                write_ex(data)
            rc = run(tmpdir)
            good = rc == expect_rc
            print(f"[{'PASS' if good else 'FAIL'}] self-test case{i} {name}: "
                  f"期望 rc={expect_rc} 实际 rc={rc}")
            ok = ok and good
        reset()
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        rc = self_test()
        print(f"self-test: {'PASS' if rc == 0 else 'FAIL'}")
        return rc
    repo = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT_DEFAULT
    return run(repo)


if __name__ == "__main__":
    raise SystemExit(main())
