#!/usr/bin/env python3
"""check_fp_contract.py — FP 语义合约门控（SPEC-087t；INFRA-102t 去写死计数）。

职责（可执行、可失败；**无期望常量、无族计数**）：
  1. 覆盖双向一致：`fp_semantics.yaml` 的 id 集合 == `opcodes.yaml` 中
     `scope == "fp"` 的 id 集合（缺/多/重复 ⇒ FAIL）。计数不写死。
  2. 族集合**现场双向**：`families` 段声明的族集合 == 记录中出现的族集合
     （声明了却无记录、或有记录却未声明 ⇒ FAIL）。每族 `required_keys`
     声明须 == REQUIRED_KEYS。
  3. 字段非空/格式：`family` 非空且已声明；`spec_cite` 匹配 `^SimRISC-0[0-7]\\b`；
     `semantics_ref` = `contract-fp.md#<anchor>` 且锚点可达。
  4. `legality_refs` 均存在于 `legality_rules.yaml`。
  5. **规则引用由 legality 表达式现场派生**（替代原 `FP_RULE_EXACT` 写死条数
     39/2/28/28/4/15）：把每条 FP 记录的 `opcodes.legality` 表达式分类到规则 id
     （分类表 = 语义文法，不是数量快照），要求 **派生的规则集合 == 记录的
     `rule_refs` 集合**（逐 id 双向；未知表达式 ⇒ FAIL，判据不可静默放宽）。
  6. 仅 FP 专属规则（dst_rf0/encode_fp_root_n）不得被 scope != fp 的记录引用。
  7. 交叉断言（SPEC-089t §2.9）：每个 scope: fp 记录的 `rule_refs` 集合 ==
     `fp_semantics.yaml` 同 id 的 `legality_refs` 集合（三方一致：
     `opcodes.legality` 表达式 ↔ `opcodes.rule_refs` ↔ `fp_semantics.legality_refs`）。
  8. 合规版本头：`contract-fp.md` 首个版本头行含 `[SimRISC-` 引用。

退出 0 = 通过；退出 1 = 失败。输出「检查名 + 期望/实际 + 退出码」。

Spec-first：判据来自 contracts/opcodes.yaml、contracts/legality_rules.yaml、
contracts/fp_semantics.yaml、.tao/contracts/contract-fp.md（不从 LLVM/QEMU 反推）。

Usage: python3 tools/spec/check_fp_contract.py [--repo-root .]
       python3 tools/spec/check_fp_contract.py --self-test
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml

# 每条记录必须声明的键（由 families 段逐族声明；与 fp_semantics 数据一致）。
REQUIRED_KEYS = ["family", "spec_cite", "semantics_ref", "legality_refs"]

RE_SPEC_CITE = re.compile(r"^SimRISC-0[0-7]\b")
RE_SEM_REF = re.compile(r"^contract-fp\.md#([A-Za-z0-9_\-]+)$")
RE_VERSION_HEADER = re.compile(r"^>\s*\*\*版本[：:]\s*\d+\.\d+\.\d+\s*\*\*")
RE_ZERO_COMPARE = re.compile(r"^(\w+)\s*!=\s*(rf0|rd0|rb0)$")
RE_RANGE_OVERFLOW = re.compile(r"^\w+\s*\+\s*immu6\s*<=\s*64$")
RE_ONEHOT_ALT = re.compile(r"^immu6\s*==\s*(\d+)$")

# 「目的为 0 号寄存器」类规则的比较对象 → 规则 id（语义文法）。
ZERO_COMPARE_RULES = {"rf0": "dst_rf0", "rd0": "dst_rd0", "rb0": "dst_rb0"}

# 仅 FP 专属规则（不被 M1 共享），非 fp 记录引用即 FAIL。
FP_SPECIFIC_RULES = ("dst_rf0", "encode_fp_root_n")


def classify_legality_expr(expr: str) -> str | None:
    """把一条 opcodes.legality 表达式分类到 legality 规则 id。

    这是**语义文法**（表达式形状 → 规则），不是数量快照：新增指令复用既有
    表达式形状时无需改动本表；出现新形状才需要在此登记（fail-closed）。
    """
    e = expr.strip()
    m = RE_ZERO_COMPARE.match(e)
    if m:
        return ZERO_COMPARE_RULES.get(m.group(2))
    if e == "immu6 != 0":
        return "mreg_zero"
    if RE_RANGE_OVERFLOW.match(e):
        return "mreg_range_overflow"
    if e.startswith("no_overlap("):
        return "mreg_range_overlap"
    if e == "immu6 == 2":
        # ftroot/foroot：仅当 n（=2）的平方根档有效（encode_fp_root_n）。
        return "encode_fp_root_n"
    if "||" in e:
        values = []
        for part in e.split("||"):
            m = RE_ONEHOT_ALT.match(part.strip())
            if not m:
                return None
            values.append(int(m.group(1)))
        if values and all(v > 0 and v & (v - 1) == 0 for v in values):
            return "encode_onehot"
        return None
    return None


def derive_rule_refs(record: dict) -> tuple[set[str], list[str]]:
    """由一条记录的 legality 表达式现场派生规则集合。返回 (规则集, 未识别表达式)。"""
    derived: set[str] = set()
    unknown: list[str] = []
    for expr in (record.get("legality") or []):
        rule = classify_legality_expr(str(expr))
        if rule is None:
            unknown.append(str(expr))
        else:
            derived.add(rule)
    return derived, unknown


def load_inputs(repo: Path):
    paths = {
        "opcodes": repo / "contracts" / "opcodes.yaml",
        "rules": repo / "contracts" / "legality_rules.yaml",
        "sem": repo / "contracts" / "fp_semantics.yaml",
        "contract": repo / ".tao" / "contracts" / "contract-fp.md",
    }
    for key, path in paths.items():
        if not path.is_file():
            raise SystemExit(f"check-fp-contract: FAIL — 缺少文件({key}): {path}")
    return {
        "opcodes": yaml.safe_load(paths["opcodes"].read_text(encoding="utf-8")),
        "rules": yaml.safe_load(paths["rules"].read_text(encoding="utf-8"))["rules"],
        "sem": yaml.safe_load(paths["sem"].read_text(encoding="utf-8")),
        "contract_text": paths["contract"].read_text(encoding="utf-8"),
    }


def check(data) -> tuple[list[tuple[str, str, str, bool]], list[str]]:
    opcodes = data["opcodes"]
    rules = data["rules"]
    sem = data["sem"]
    contract_text = data["contract_text"]

    results: list[tuple[str, str, str, bool]] = []
    failures: list[str] = []

    def record(name: str, expected, actual, ok: bool | None = None) -> bool:
        if ok is None:
            ok = str(expected) == str(actual)
        results.append((name, str(expected), str(actual), ok))
        return ok

    def fail(msg: str) -> None:
        failures.append(msg)

    # ── 1. 覆盖双向一致（集合相等，不比较计数）──────────────────────────
    fp_ids = {o["id"] for o in opcodes if o.get("scope") == "fp"}
    insns = sem.get("instructions") or []
    sem_ids = [i.get("id") for i in insns]
    sem_id_set = set(sem_ids)

    if not record("id 无重复", "0 条", f"{len(sem_ids) - len(sem_id_set)} 条"):
        fail(f"id 重复: 列表 {len(sem_ids)}，去重 {len(sem_id_set)}")
    missing = sorted(fp_ids - sem_id_set)
    extra = sorted(sem_id_set - fp_ids)
    if not record("覆盖（opcodes:fp 侧缺）", "0 条", f"{len(missing)} 条") or missing:
        fail("fp_semantics 缺少 opcodes 侧 id: " + ", ".join(missing[:10]))
    if not record("覆盖（fp_semantics 多）", "0 条", f"{len(extra)} 条") or extra:
        fail("fp_semantics 多出 opcodes 侧 id: " + ", ".join(extra[:10]))

    # ── 2. 族集合现场双向 ────────────────────────────────────────────────
    families = sem.get("families") or {}
    declared = set(families)
    live_families = {i.get("family") for i in insns}
    undeclared = sorted(x for x in live_families - declared if x is not None)
    unused = sorted(declared - live_families)
    if not record("记录族均已声明", "0 个", f"{len(undeclared)} 个") or undeclared:
        fail("记录使用了未声明的族: " + ", ".join(str(x) for x in undeclared[:10]))
    if not record("声明族均有记录", "0 个", f"{len(unused)} 个") or unused:
        fail("families 段声明了无记录的族: " + ", ".join(unused[:10]))

    # 每族 required_keys 声明 == REQUIRED_KEYS
    bad_decl = [fam for fam, fdef in families.items()
                if not isinstance(fdef, dict)
                or sorted(fdef.get("required_keys") or []) != sorted(REQUIRED_KEYS)]
    if not record("每族 required_keys 声明", "0 个", f"{len(bad_decl)} 个") or bad_decl:
        fail("required_keys 声明缺失/不符: " + ", ".join(sorted(bad_decl)[:10]))

    bad_keys = []
    for i in insns:
        fdef = families.get(i.get("family")) or {}
        for key in (fdef.get("required_keys") or []):
            if key not in i:
                bad_keys.append(f"{i.get('id')}:{key}")
    if not record("记录含族 required_keys", "0 条", f"{len(bad_keys)} 条") or bad_keys:
        fail("记录缺 required_keys: " + ", ".join(bad_keys[:10]))

    # ── 3. spec_cite 合规 / family 非空 ─────────────────────────────────
    bad_cite = [i.get("id") for i in insns
                if not isinstance(i.get("spec_cite"), str)
                or not RE_SPEC_CITE.match(i.get("spec_cite", ""))]
    if not record("spec_cite 合规", "0 条", f"{len(bad_cite)} 条") or bad_cite:
        fail("spec_cite 缺失/不合规: " + ", ".join(bad_cite[:10]))

    bad_family = [i.get("id") for i in insns
                  if not isinstance(i.get("family"), str) or not i.get("family")]
    if not record("family 非空", "0 条", f"{len(bad_family)} 条") or bad_family:
        fail("family 缺失/为空: " + ", ".join(bad_family[:10]))

    # ── 4. legality_refs 均存在 ─────────────────────────────────────────
    rule_ids = {r["id"] for r in rules}
    ref_pairs = [(i.get("id"), ref) for i in insns
                 for ref in (i.get("legality_refs") or [])]
    bad_ref = [ref for _, ref in ref_pairs if ref not in rule_ids]
    if not record("legality_refs 均存在", "0 条", f"{len(bad_ref)} 条") or bad_ref:
        fail("legality_refs 指向不存在的规则: "
             + ", ".join(sorted(set(bad_ref))[:10]))

    # ── 5. 规则引用由 legality 表达式现场派生（替代写死条数）──────────────
    derived_mismatch = []
    unknown_expr = []
    fp_by_id = {o["id"]: o for o in opcodes if o.get("scope") == "fp"}
    fp_rule_universe: set[str] = set()
    for i in insns:
        oid = i.get("id")
        rec = fp_by_id.get(oid)
        if rec is None:
            continue  # 已由覆盖断言报出
        derived, unknown = derive_rule_refs(rec)
        fp_rule_universe |= derived
        unknown_expr.extend(f"{oid}:{u}" for u in unknown)
        declared_refs = set(i.get("legality_refs") or [])
        if derived != declared_refs:
            derived_mismatch.append(
                f"{oid}(派生缺:{sorted(declared_refs - derived)} "
                f"派生多:{sorted(derived - declared_refs)})")
    if not record("legality 表达式未识别", "0 条", f"{len(unknown_expr)} 条") \
            or unknown_expr:
        fail("legality 表达式无法分类（新增文法须登记）: "
             + ", ".join(unknown_expr[:10]))
    if not record("legality 表达式派生规则 == legality_refs", "0 条",
                  f"{len(derived_mismatch)} 条") or derived_mismatch:
        fail("规则引用与 legality 表达式不一致: "
             + "; ".join(derived_mismatch[:10]))

    # 派生出的规则集合须为 legality_rules.yaml 中真实存在的 id
    unknown_rules = sorted(fp_rule_universe - rule_ids)
    if not record("派生规则均已登记", "0 个", f"{len(unknown_rules)} 个") \
            or unknown_rules:
        fail("派生规则不在 legality_rules.yaml: " + ", ".join(unknown_rules[:10]))

    nonfp_hits = [f"{o['id']}:{ref}" for o in opcodes
                  if o.get("scope") != "fp"
                  for ref in (o.get("rule_refs") or []) if ref in FP_SPECIFIC_RULES]
    if not record("FP 专属规则未被非 fp 记录引用", "0 条", f"{len(nonfp_hits)} 条") \
            or nonfp_hits:
        fail("非 fp 记录引用了 FP 专属规则: " + ", ".join(nonfp_hits[:10]))

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
    if not record("semantics_ref 锚点可达", "0 条", f"{len(bad_anchor)} 条") or bad_anchor:
        fail("semantics_ref 锚点不可达: " + ", ".join(bad_anchor[:10]))

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
        fail("contract-fp.md 版本头缺失或未含 [SimRISC- 引用")

    # ── 8. opcodes.rule_refs ↔ fp_semantics.legality_refs 交叉断言 ───────
    sem_refs_by_id = {i.get("id"): (i.get("legality_refs") or []) for i in insns}
    cross_bad: list[str] = []
    for o in opcodes:
        if o.get("scope") != "fp":
            continue
        oid = o.get("id")
        a = sorted(set(o.get("rule_refs") or []))
        b = sorted(set(sem_refs_by_id.get(oid) or []))
        if a != b:
            missing = [x for x in b if x not in a]
            extra = [x for x in a if x not in b]
            cross_bad.append(f"{oid}(缺:{missing} 多:{extra})")
    if not record("opcodes.rule_refs == fp_semantics.legality_refs", "0 条",
                  f"{len(cross_bad)} 条") or cross_bad:
        fail("FP 双源 rule_refs 漂移: " + "; ".join(cross_bad[:10]))

    # 现场信息（非判据）：族计数只打印，不比较。
    print("  现场族计数（信息，非判据）: "
          + ", ".join(f"{k}={v}" for k, v in sorted(Counter(
              i.get("family") for i in insns).items())))
    print("  现场派生 FP 规则集合（信息，非判据）: "
          + ", ".join(sorted(fp_rule_universe)))
    return results, failures


def run(repo: Path) -> int:
    data = load_inputs(repo)
    results, failures = check(data)
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


# ---------------------------------------------------------------------------
# --self-test：临时树注入（复制 4 个输入到临时目录后逐例改动）。
# ---------------------------------------------------------------------------
def self_test() -> int:
    repo = Path(__file__).resolve().parents[2]
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "INFRA-102t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="check-fp-contract-", dir=tmp_root))

    src = {
        "contracts/opcodes.yaml": repo / "contracts" / "opcodes.yaml",
        "contracts/legality_rules.yaml": repo / "contracts" / "legality_rules.yaml",
        "contracts/fp_semantics.yaml": repo / "contracts" / "fp_semantics.yaml",
        ".tao/contracts/contract-fp.md": repo / ".tao" / "contracts" / "contract-fp.md",
    }
    for rel, path in src.items():
        dst = tmpdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(path.read_bytes())

    base_sem = yaml.safe_load((tmpdir / "contracts/fp_semantics.yaml").read_text())
    base_op = yaml.safe_load((tmpdir / "contracts/opcodes.yaml").read_text())

    def write_sem(sem) -> None:
        (tmpdir / "contracts/fp_semantics.yaml").write_text(
            yaml.safe_dump(sem, allow_unicode=True, sort_keys=False))

    def write_op(op) -> None:
        (tmpdir / "contracts/opcodes.yaml").write_text(
            yaml.safe_dump(op, allow_unicode=True, sort_keys=False))

    def reset() -> None:
        write_sem(yaml.safe_load(yaml.safe_dump(base_sem, allow_unicode=True)))
        write_op(yaml.safe_load(yaml.safe_dump(base_op, allow_unicode=True)))

    def sem_mut(fn):
        sem = yaml.safe_load(yaml.safe_dump(base_sem, allow_unicode=True))
        fn(sem)
        return sem

    def op_mut(fn):
        op = yaml.safe_load(yaml.safe_dump(base_op, allow_unicode=True))
        fn(op)
        return op

    # 每个 case 用 (sem, op) 变更对；None = 不改。
    plans = []

    def plan(name, expect_rc, sem=None, op=None):
        plans.append((name, expect_rc, sem, op))

    plan("baseline", 0)

    def drop_one(sem):
        sem["instructions"].pop(0)
    plan("sem-missing-id", 1, sem=sem_mut(drop_one))

    def add_extra(sem):
        extra = dict(sem["instructions"][0])
        extra["id"] = "zzz_extra_orri_rf"
        sem["instructions"].append(extra)
    plan("sem-extra-id", 1, sem=sem_mut(add_extra))

    def add_dup(sem):
        sem["instructions"].append(dict(sem["instructions"][0]))
    plan("sem-duplicate-id", 1, sem=sem_mut(add_dup))

    def break_family(sem):
        sem["instructions"][0]["family"] = "no_such_family"
    plan("record-undeclared-family", 1, sem=sem_mut(break_family))

    def drop_family(sem):
        sem["families"].pop(next(iter(sem["families"])))
    plan("family-declared-without-records", 1, sem=sem_mut(drop_family))

    def drop_rule_ref(sem):
        for i in sem["instructions"]:
            if i.get("legality_refs"):
                i["legality_refs"] = list(i["legality_refs"])[1:]
                return
        raise AssertionError("no record with legality_refs")

    def drop_rule_ref_op(op):
        for r in op:
            if r.get("scope") == "fp" and r.get("rule_refs"):
                r["rule_refs"] = list(r["rule_refs"])[1:]
                return
        raise AssertionError("no fp record with rule_refs")

    # 两个来源同时删同一条 ref（legality 表达式不变）⇒ 由派生断言捕获。
    plan("rule-ref-missing-vs-legality-expr", 1, sem=sem_mut(drop_rule_ref),
         op=op_mut(drop_rule_ref_op))

    def add_bogus_ref(sem):
        sem["instructions"][0]["legality_refs"] = ["no_such_rule"]
    plan("rule-ref-unknown", 1, sem=sem_mut(add_bogus_ref))

    def empty_cite(sem):
        sem["instructions"][0]["spec_cite"] = "nope"
    plan("spec-cite-invalid", 1, sem=sem_mut(empty_cite))

    def break_anchor(sem):
        sem["instructions"][0]["semantics_ref"] = "contract-fp.md#no_such_anchor"
    plan("semantics-anchor-unreachable", 1, sem=sem_mut(break_anchor))

    def add_unknown_expr(op):
        rec = next(r for r in op if r.get("scope") == "fp")
        rec["legality"] = list(rec.get("legality") or []) + ["mystery_expr > 3"]
    plan("unknown-legality-expression", 1, op=op_mut(add_unknown_expr))

    ok = True
    try:
        for i, (name, expect_rc, sem, op) in enumerate(plans, 1):
            reset()
            if sem is not None:
                write_sem(sem)
            if op is not None:
                write_op(op)
            rc = run(tmpdir)
            good = rc == expect_rc
            print(f"[{'PASS' if good else 'FAIL'}] self-test case{i} {name}: "
                  f"期望 rc={expect_rc} 实际 rc={rc}")
            ok = ok and good
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=None,
                        help="仓库根（默认: 脚本向上 2 级）")
    parser.add_argument("--self-test", action="store_true",
                        help="临时树注入自检")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    repo = Path(args.repo_root).resolve() if args.repo_root \
        else Path(__file__).resolve().parents[2]
    return run(repo)


if __name__ == "__main__":
    raise SystemExit(main())
