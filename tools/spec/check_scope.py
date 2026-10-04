#!/usr/bin/env python3
"""check_scope.py — opcodes.yaml 范围分区门控（`scope`: m1 | fp | excluded）。

职责（可执行、可失败；SPEC-086t §5.3）：
  1. 每条记录**恰有** 1 个合法 `scope` ∈ {m1, fp, excluded}（缺失/非法 ⇒ FAIL）。
  2. 分区计数：m1 == 152、fp == 60、excluded == 15、total == 227。
  3. `scope == "excluded"` ⇔ `decode == "ILLI"`；`scope ∈ {m1, fp}` ⇒ 无 `decode`
     且无旧字段（防回退）。
  4. `scope == "fp"` ⇔ `id.endswith("_rf")`（结构性判据，源自 spec/契约）。
  5. 旧 M1 排除布尔字段（见 OLD_FIELD）在非历史文件中已消失。
  6. 输出「检查名 + 期望/实际 + 退出码」；任一失败非零退出。

判据来源（Spec-first，不从实现反推）：
  * contracts/opcodes.yaml（每条记录 scope/decode/id）
  * SPEC-086t §5.3（计数 152/60/15/227；fp ⇔ _rf）

Usage: python3 tools/spec/check_scope.py [--yaml contracts/opcodes.yaml] [--repo-root .]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# 旧字段名以拼接构造，避免本文件自身命中被扫（并保证 grep 静态搜索为 0）。
OLD_FIELD = "excluded" + "_m1"

EXPECTED_M1 = 152
EXPECTED_FP = 60
EXPECTED_EXCLUDED = 15
EXPECTED_TOTAL = 227

ALLOWED_SCOPES = ("m1", "fp", "excluded")

# 扫描「非历史」源文件的路径（相对仓库根）。
SCAN_DIRS = ("tools", "contracts", "spec", "tests", "docs")
SCAN_FILES = ("Makefile", "README.md", "AGENTS.md")
# 历史载体：保留旧字段字样，不参与消失性断言（SPEC-086t R2 / §3⑤）。
HISTORY_PREFIXES = (
    ".tao/adr/",
    ".tao/tasks/",
    ".tao/knowledge/changelog.md",
    ".tao/knowledge/MEMORY.md",
    ".tao/knowledge/lessons.md",
    ".tao/knowledge/issues.yaml",
    "docs/spec-065t-legality-proposal.md",
    "spec/SimRISC-0.5.3/",
)
SKIP_PARTS = {"__pycache__", ".git", ".work", ".cache", "node_modules"}

results: list[tuple[str, str, str]] = []  # (check_name, expected, actual)


def record(name: str, expected: str, actual: str) -> bool:
    ok = expected == actual
    results.append((name, expected, actual))
    return ok


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yaml", default=None,
                        help="opcodes.yaml 路径（默认 <repo>/contracts/opcodes.yaml）")
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve() if args.repo_root \
        else Path(__file__).resolve().parents[2]
    yaml_path = Path(args.yaml) if args.yaml \
        else repo / "contracts" / "opcodes.yaml"

    if not yaml_path.is_file():
        print(f"check-scope: FAIL — opcodes.yaml 未找到: {yaml_path}",
              file=sys.stderr)
        return 1
    records = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        print("check-scope: FAIL — opcodes.yaml 顶层必须是列表", file=sys.stderr)
        return 1

    failures: list[str] = []

    # 1. scope 合法且存在
    invalid = [r.get("id", "?") for r in records
               if r.get("scope") not in ALLOWED_SCOPES]
    if not record("每条记录恰有合法 scope", "0 条", f"{len(invalid)} 条") \
            or invalid:
        failures.append(
            "scope 缺失/非法: " + ", ".join(invalid[:10])
            + (f" …（共 {len(invalid)}）" if len(invalid) > 10 else ""))

    # 2. 分区计数
    n_m1 = sum(1 for r in records if r.get("scope") == "m1")
    n_fp = sum(1 for r in records if r.get("scope") == "fp")
    n_ex = sum(1 for r in records if r.get("scope") == "excluded")
    total = len(records)
    checks = {
        "m1 计数": (EXPECTED_M1, n_m1),
        "fp 计数": (EXPECTED_FP, n_fp),
        "excluded 计数": (EXPECTED_EXCLUDED, n_ex),
        "total 计数": (EXPECTED_TOTAL, total),
    }
    for name, (exp, act) in checks.items():
        if not record(name, str(exp), str(act)):
            failures.append(f"{name}: 期望 {exp}，实际 {act}")

    # 3a. scope == excluded ⇒ decode == ILLI（R1 方案 B）
    bad_decode = [r.get("id", "?") for r in records
                  if r.get("scope") == "excluded" and r.get("decode") != "ILLI"]
    if not record("scope==excluded ⇒ decode=ILLI", "0 条",
                  f"{len(bad_decode)} 条") or bad_decode:
        failures.append("excluded 记录缺 decode: ILLI: "
                        + ", ".join(bad_decode[:10]))

    # 3b. scope ∈ {m1, fp} ⇒ 无 decode、无旧字段（防回退；R1 方案 B）
    bad_plain = [r.get("id", "?") for r in records
                 if r.get("scope") in ("m1", "fp")
                 and ("decode" in r or OLD_FIELD in r)]
    if not record("scope∈{m1,fp} ⇒ 无 decode/旧字段", "0 条",
                  f"{len(bad_plain)} 条") or bad_plain:
        failures.append("m1/fp 记录含 decode/旧字段: "
                        + ", ".join(bad_plain[:10]))

    # 4. scope == fp ⇔ id.endswith("_rf")
    fp_bad = [r.get("id", "?") for r in records
              if (r.get("scope") == "fp") != str(r.get("id", "")).endswith("_rf")]
    if not record("scope:fp ⇔ id 以 _rf 结尾", "0 条",
                  f"{len(fp_bad)} 条") or fp_bad:
        failures.append("fp ∉ _rf 或 _rf ∉ fp: " + ", ".join(fp_bad[:10]))

    # 5. 旧字段在非历史文件中消失
    hits = scan_old_field(repo)
    if not record("旧字段在非历史文件中消失", "0 个文件",
                  f"{len(hits)} 个文件") or hits:
        failures.append("仍含旧字段的文件: " + ", ".join(hits[:10]))

    # 输出
    for name, exp, act in results:
        flag = "PASS" if exp == act else "FAIL"
        print(f"[{flag}] {name}: 期望={exp} 实际={act}")

    if failures:
        for f in failures:
            print(f"check-scope: FAIL — {f}", file=sys.stderr)
        print(f"check-scope: FAILED ({len(failures)} 项)", file=sys.stderr)
        return 1

    print("check-scope: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
