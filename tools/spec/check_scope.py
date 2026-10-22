#!/usr/bin/env python3
"""check_scope.py — opcodes.yaml 范围分区门控（`scope`: m1 | fp | excluded | m3 | m8 | m9）。

职责（可执行、可失败；SPEC-086t §5.3）——**无写死计数**（INFRA-102t）：

  1. 每条记录**恰有** 1 个合法 `scope` ∈ ALLOWED_SCOPES（缺失/非法 ⇒ FAIL）。
  2. `id` 全局唯一（重复 ⇒ 分区并集/两两不交失去意义 ⇒ FAIL）。
  3. **分区不变量**（代替此前的 m1==156/fp==64/…/total==264 常量）：
     - **并集 == 全量**：各 scope 的 id 集合之并 == 全部记录 id 集合（无未分区记录）；
     - **两两不交**：任意两个 scope 的 id 集合交集为空；
     - **每 scope 非空**：6 个分区各自 ≥1 条（整族被静默清空 ⇒ FAIL）。
     计数只**现场统计并打印**，不参与比较。
  4. `scope == "excluded"` ⇔ `decode == "ILLI"`；`scope ∈ {m1, fp, m3, m8, m9}` ⇒ 无 `decode`
     且无旧字段（防回退）。
  5. `_rf`（RF 银行目的）的 scope 约束：`scope == "fp"` ⇒ `id.endswith("_rf")`；
     `id.endswith("_rf")` ⇒ `scope ∈ {fp, excluded}`。
  6. 旧 M1 排除布尔字段（见 OLD_FIELD）在非历史文件中已消失。

判据来源（Spec-first，不从实现反推）：
  * contracts/opcodes.yaml（每条记录 scope/decode/id）
  * SPEC-086t §5.3（分区口径与 `excluded ⇔ ILLI`）
  * ADR-0012 / ADR-0029 / ADR-0032 / ADR-0034 / ADR-0035 / SPEC-115t / SPEC-152t /
    SPEC-159t–SPEC-163t（历史演进：分区只增删记录，**不再改本脚本的期望计数**）

Usage: python3 tools/spec/check_scope.py [--yaml contracts/opcodes.yaml] [--repo-root .]
       python3 tools/spec/check_scope.py --self-test
"""
from __future__ import annotations

import argparse
import itertools
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml

# 旧字段名以拼接构造，避免本文件自身命中被扫（并保证 grep 静态搜索为 0）。
OLD_FIELD = "excluded" + "_m1"

# scope 词表（结构枚举，非计数）。
ALLOWED_SCOPES = ("m1", "fp", "excluded", "m3", "m8", "m9")
# 无 decode 的分区（excluded 是唯一带 decode: ILLI 的分区）。
PLAIN_SCOPES = tuple(s for s in ALLOWED_SCOPES if s != "excluded")

# 扫描「非历史」源文件的路径（相对仓库根）。
SCAN_DIRS = ("tools", "contracts", "spec", "tests", "docs")
SCAN_FILES = ("Makefile", "README.md", "AGENTS.md")
# 历史载体：保留旧字段字样，不参与消失性断言（SPEC-086t R2 / §3⑤）。
HISTORY_PREFIXES = (
    ".tao/adr/",
    ".tao/tasks/",
    ".tao/knowledge/lessons.md",
    ".tao/knowledge/issues.yaml",
)
SKIP_PARTS = {"__pycache__", ".git", ".work", ".cache", "node_modules"}


def iter_source_files(repo: Path):
    for d in SCAN_DIRS:
        root = repo / d
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_PARTS for part in p.parts):
                continue
            rel = p.relative_to(repo).as_posix()
            if any(rel == h or rel.startswith(h) for h in HISTORY_PREFIXES):
                continue
            if p.suffix in (".pyc",):
                continue
            yield p
    for f in SCAN_FILES:
        p = repo / f
        if p.is_file():
            yield p


def scan_old_field(repo: Path) -> list[str]:
    hits: list[str] = []
    for p in iter_source_files(repo):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if OLD_FIELD in text:
            hits.append(p.relative_to(repo).as_posix())
    return sorted(hits)


def check(records: list, repo: Path) -> tuple[list[tuple[str, str, str, bool]], list[str]]:
    """返回 (逐项结果, 失败说明)。结果元组 = (检查名, 期望, 实际, 是否通过)。"""
    results: list[tuple[str, str, str, bool]] = []
    failures: list[str] = []

    def record(name: str, expected, actual, ok: bool | None = None) -> bool:
        if ok is None:
            ok = str(expected) == str(actual)
        results.append((name, str(expected), str(actual), ok))
        return ok

    def fail(msg: str) -> None:
        failures.append(msg)

    # 1. scope 合法且存在
    invalid = [r.get("id", "?") for r in records
               if r.get("scope") not in ALLOWED_SCOPES]
    if not record("每条记录恰有合法 scope", "0 条", f"{len(invalid)} 条") or invalid:
        fail("scope 缺失/非法: " + ", ".join(invalid[:10])
             + (f" …（共 {len(invalid)}）" if len(invalid) > 10 else ""))

    # 2. id 唯一（分区集合运算的前提）
    ids = [r.get("id") for r in records]
    dup = sorted({rid for rid, n in Counter(ids).items() if n > 1})
    if not record("id 全局唯一", "0 条重复", f"{len(dup)} 条重复") or dup:
        fail("重复 id: " + ", ".join(str(d) for d in dup[:10]))

    # 3. 分区不变量：并集 == 全量、两两不交、每 scope 非空
    by_scope = {s: {r.get("id") for r in records if r.get("scope") == s}
                for s in ALLOWED_SCOPES}
    all_ids = {r.get("id") for r in records}
    union = set().union(*by_scope.values()) if by_scope else set()
    unpartitioned = sorted(x for x in all_ids - union if x is not None)
    if not record("分区并集 == 全量记录集", "0 条未分区",
                  f"{len(unpartitioned)} 条未分区") or unpartitioned:
        fail("有记录不在任何分区: " + ", ".join(unpartitioned[:10]))

    overlaps = []
    for a, b in itertools.combinations(ALLOWED_SCOPES, 2):
        inter = by_scope[a] & by_scope[b]
        if inter:
            overlaps.append(f"{a}∩{b}={sorted(x for x in inter if x is not None)[:5]}")
    if not record("分区两两不交", "0 对相交", f"{len(overlaps)} 对相交") or overlaps:
        fail("分区相交: " + "; ".join(overlaps[:5]))

    empty = [s for s, members in by_scope.items() if not members]
    if not record("每 scope 非空", "0 个空分区", f"{len(empty)} 个空分区") or empty:
        fail("空分区（整族被清空?）: " + ", ".join(empty))

    # 4a. scope == excluded ⇔ decode == ILLI（两个方向）
    bad_decode = [r.get("id", "?") for r in records
                  if r.get("scope") == "excluded" and r.get("decode") != "ILLI"]
    if not record("excluded ⇒ decode=ILLI", "0 条", f"{len(bad_decode)} 条") or bad_decode:
        fail("excluded 记录缺 decode: ILLI: " + ", ".join(bad_decode[:10]))
    extra_decode = [r.get("id", "?") for r in records
                    if r.get("scope") != "excluded" and "decode" in r]
    if not record("非 excluded ⇒ 无 decode", "0 条", f"{len(extra_decode)} 条") or extra_decode:
        fail("非 excluded 记录带 decode: " + ", ".join(extra_decode[:10]))

    # 4b. 非 excluded ⇒ 无旧字段（防回退）
    bad_old = [r.get("id", "?") for r in records
               if r.get("scope") in PLAIN_SCOPES and OLD_FIELD in r]
    if not record("非 excluded ⇒ 无旧字段", "0 条", f"{len(bad_old)} 条") or bad_old:
        fail("非 excluded 记录含旧字段: " + ", ".join(bad_old[:10]))

    # 5. `_rf`（RF 银行目的）记录的 scope 只允许 fp / excluded
    fp_bad = [r.get("id", "?") for r in records
              if r.get("scope") == "fp" and not str(r.get("id", "")).endswith("_rf")]
    if not record("scope:fp ⇒ id 以 _rf 结尾", "0 条", f"{len(fp_bad)} 条") or fp_bad:
        fail("fp 记录 id 不以 _rf 结尾: " + ", ".join(fp_bad[:10]))

    rf_bad = [r.get("id", "?") for r in records
              if str(r.get("id", "")).endswith("_rf")
              and r.get("scope") not in ("fp", "excluded")]
    if not record("id 以 _rf 结尾 ⇒ scope∈{fp,excluded}", "0 条",
                  f"{len(rf_bad)} 条") or rf_bad:
        fail("_rf 记录的 scope 非 fp/excluded: " + ", ".join(rf_bad[:10]))

    # 6. 旧字段在非历史文件中消失
    hits = scan_old_field(repo)
    if not record("旧字段在非历史文件中消失", "0 个文件",
                  f"{len(hits)} 个文件") or hits:
        fail("仍含旧字段的文件: " + ", ".join(hits[:10]))

    return results, failures


def run(yaml_path: Path, repo: Path) -> int:
    if not yaml_path.is_file():
        print(f"check-scope: FAIL — opcodes.yaml 未找到: {yaml_path}",
              file=sys.stderr)
        return 1
    records = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        print("check-scope: FAIL — opcodes.yaml 顶层必须是列表", file=sys.stderr)
        return 1

    results, failures = check(records, repo)
    counts = Counter(r.get("scope") for r in records)
    # 计数只作现场信息（不参与判据）。
    print("check-scope: 现场分区计数（信息，非判据）: "
          + ", ".join(f"{s}={counts.get(s, 0)}" for s in ALLOWED_SCOPES)
          + f", total={len(records)}")
    for name, exp, act, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: 期望={exp} 实际={act}")

    if failures:
        for f in failures:
            print(f"check-scope: FAIL — {f}", file=sys.stderr)
        print(f"check-scope: FAILED ({len(failures)} 项)", file=sys.stderr)
        return 1
    print("check-scope: PASS")
    return 0


# ---------------------------------------------------------------------------
# --self-test：临时树注入（不改真实 contracts/），逐例断言 rc，收敛为
# 「每类不变量都有可达 FAIL 路径」。
# ---------------------------------------------------------------------------
def self_test() -> int:
    repo = Path(__file__).resolve().parents[2]
    base_text = (repo / "contracts" / "opcodes.yaml").read_text(encoding="utf-8")

    def dumped(records) -> str:
        return yaml.safe_dump(records, allow_unicode=True, sort_keys=False)

    def mut(fn):
        records = yaml.safe_load(base_text)
        fn(records)
        return dumped(records)

    def drop_all_scope(records, scope):
        records[:] = [r for r in records if r["scope"] != scope]

    def add_dup_id(records):
        records.append(dict(records[0]))

    def add_unpartitioned(records):
        records.append({**records[0], "id": "zzz_unpartitioned", "scope": "bogus"})

    def break_decode(records):
        ex = next(r for r in records if r["scope"] == "excluded")
        del ex["decode"]

    def add_decode_to_plain(records):
        next(r for r in records if r["scope"] == "m1")["decode"] = "ILLI"

    def break_fp_rf(records):
        rec = next(r for r in records if r["scope"] == "fp")
        rec["id"] = rec["id"].replace("_rf", "_zz")

    def move_rf_to_m1(records):
        rec = next(r for r in records if r["scope"] == "fp")
        rec["scope"] = "m1"

    def flip_one_scope(records):
        """把一条 m1 记录改到 m9（单值 scope ⇒ 分区天然不交；仅证明重分区不误报）。"""
        next(r for r in records if r["scope"] == "m1")["scope"] = "m9"

    def delete_one_m1(records):
        idx = next(i for i, r in enumerate(records) if r["scope"] == "m1")
        del records[idx]

    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "INFRA-102t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="check-scope-", dir=tmp_root))
    ok = True
    try:
        cases = [
            ("baseline", base_text, 0),
            ("empty-scope-m3", mut(lambda rs: drop_all_scope(rs, "m3")), 1),
            ("duplicate-id", mut(add_dup_id), 1),
            ("invalid-scope", mut(add_unpartitioned), 1),
            ("excluded-no-decode", mut(break_decode), 1),
            ("plain-with-decode", mut(add_decode_to_plain), 1),
            ("fp-id-not-rf", mut(break_fp_rf), 1),
            ("rf-scope-m1", mut(move_rf_to_m1), 1),
            ("record-deleted-from-m1", mut(delete_one_m1), 0),
            ("scope-flip-m1-to-m9", mut(flip_one_scope), 0),
        ]
        for i, (name, text, expect_rc) in enumerate(cases, 1):
            path = tmpdir / f"opcodes-{i}.yaml"
            path.write_text(text, encoding="utf-8")
            if i > 1 and text == base_text:
                print(f"[FAIL] self-test case{i} {name}: 空注入")
                ok = False
                continue
            rc = run(path, repo)
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
    parser.add_argument("--yaml", default=None,
                        help="opcodes.yaml 路径（默认 <repo>/contracts/opcodes.yaml）")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--self-test", action="store_true",
                        help="临时树注入自检（每类不变量都有可达 FAIL 路径）")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve() if args.repo_root \
        else Path(__file__).resolve().parents[2]
    if args.self_test:
        return self_test()
    yaml_path = Path(args.yaml) if args.yaml \
        else repo / "contracts" / "opcodes.yaml"
    return run(yaml_path, repo)


if __name__ == "__main__":
    raise SystemExit(main())
