#!/usr/bin/env python3
"""check_scope.py — opcodes.yaml 范围分区门控（`scope`: m1 | fp | excluded | m3 | m8 | m9）。

职责（可执行、可失败；SPEC-086t §5.3）：
  1. 每条记录**恰有** 1 个合法 `scope` ∈ {m1, fp, excluded, m3, m8, m9}（缺失/非法 ⇒ FAIL）。
  2. 分区计数：m1 == 156、fp == 60、excluded == 31、m3 == 1、m8 == 7、m9 == 9、total == 264。
  3. `scope == "excluded"` ⇔ `decode == "ILLI"`；`scope ∈ {m1, fp, m3, m8, m9}` ⇒ 无 `decode`
     且无旧字段（防回退）。
  4. `_rf`（RF 银行目的）的 scope 约束：`scope == "fp"` ⇒ `id.endswith("_rf")`；
     `id.endswith("_rf")` ⇒ `scope ∈ {fp, excluded}`（其余 scope 不得出现 RF 记录）。
     `excluded` 分支是 SPEC-161t 立册期留下的防线（`ftrnd`/`fornd` 当时为 RF 目的且
     `scope: excluded`）；SPEC-162t 翻转后已无此类记录，判据保留以**防回退**。
  5. 旧 M1 排除布尔字段（见 OLD_FIELD）在非历史文件中已消失。
  6. 输出「检查名 + 期望/实际 + 退出码」；任一失败非零退出。

判据来源（Spec-first，不从实现反推）：
  * contracts/opcodes.yaml（每条记录 scope/decode/id）
  * SPEC-086t §5.3（计数 151/60/15/227；fp ⇔ _rf）
  * SPEC-115t（re-scope：trap/escape/cfx2rd/cfx2rc excluded → m1；计数更新为
    155/60/11/227，总数 227 不变）
  * ADR-0012 D9.1/D9.5（新增 scope: m3，total 227→228，M1 不变）
  * ADR-0012 D10（新增 scope: m8 = rev.o/.t/.w/.b 4 条；M1/fp/excluded/m3 不变）
  * ADR-0012 D11（新增 scope: m8 = ctlz/cttz/ctpop 3 条 ⇒ m8 4→7、total 231→234；
    M1/fp/excluded/m3 不变）
  * ADR-0029 D1（恢复 ISA 指令 aip.si（IP 相对寻址，op 0x5A）⇒ M1 155→156、
    total 234→235；fp/excluded/m3/m8 不变）
  * ADR-0032 D4 / SPEC-152t（新增 scope: m9 = rol.o/.t/.w/.b 8 条 ⇒ m9 0→8、
    total 235→243；M1/fp/excluded/m3/m8 不变）
  * ADR-0034 D3–D5（`lr`/`sc` 由 8 条重排为 24 条、删除 `lr.*.nr` 与 `sc.*.an`、
    命名 `<lr|sc>.<b|w|t|o>.<序>` ⇒ excluded 11→27、total 243→259；M1/fp/m3/m8/m9 不变）
  * ADR-0035 D5/D7（新增 `clmul.o`（rrrr，op 0x56），scope excluded ⇒ excluded 27→28、
    total 259→260；M1/fp/m3/m8/m9 不变）
  * ADR-0035 D7（实现后落：`clmul.o` 的 LLVM 后端与 QEMU 执行语义均已落地 ⇒
    scope excluded→m9 ⇒ excluded 28→27、m9 8→9、total 260 不变；M1/fp/m3/m8 不变）
   * SPEC-163t（用户 2026-10-22 裁定：删除 `cs.eq_rrrr_rf`/`cs.ne_rrrr_rf` 两条死指令 ⇒
     fp 60→58、total 260→258；M1/excluded/m3/m8/m9 不变；0x5E/0x5F 腾空给 SPEC-157t FMA）
   * SPEC-161t（`ftrnd`/`fornd` 立册：754-2019 六种取整，`immu6` one-hot 六档 ⇒
     excluded 27→29、total 258→260；M1/fp/m3/m8/m9 不变）
   * SPEC-162t（`ftrnd`/`fornd` 实现落地后翻转：excluded→fp ⇒ fp 58→60、excluded 29→27、
     total 260 不变；M1/m3/m8/m9 不变）
   * SPEC-159t（`ftmin`/`ftmax`/`fomin`/`fomax` 立册：IEEE 754-2019 §9.6
     `minimumNumber`/`maximumNumber`，`orrr`、`op 0x44`、`ha 0x26/0x27/0x2E/0x2F` ⇒
     excluded 27→31、total 260→264；M1/fp/m3/m8/m9 不变）

Usage: python3 tools/spec/check_scope.py [--yaml contracts/opcodes.yaml] [--repo-root .]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# 旧字段名以拼接构造，避免本文件自身命中被扫（并保证 grep 静态搜索为 0）。
OLD_FIELD = "excluded" + "_m1"

EXPECTED_M1 = 156
EXPECTED_FP = 60
EXPECTED_EXCLUDED = 31
EXPECTED_M3 = 1
EXPECTED_M8 = 7
EXPECTED_M9 = 9
EXPECTED_TOTAL = 264

ALLOWED_SCOPES = ("m1", "fp", "excluded", "m3", "m8", "m9")

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
    n_m3 = sum(1 for r in records if r.get("scope") == "m3")
    n_m8 = sum(1 for r in records if r.get("scope") == "m8")
    n_m9 = sum(1 for r in records if r.get("scope") == "m9")
    total = len(records)
    checks = {
        "m1 计数": (EXPECTED_M1, n_m1),
        "fp 计数": (EXPECTED_FP, n_fp),
        "excluded 计数": (EXPECTED_EXCLUDED, n_ex),
        "m3 计数": (EXPECTED_M3, n_m3),
        "m8 计数": (EXPECTED_M8, n_m8),
        "m9 计数": (EXPECTED_M9, n_m9),
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

    # 3b. scope ∈ {m1, fp, m3, m8, m9} ⇒ 无 decode、无旧字段（防回退；R1 方案 B）
    bad_plain = [r.get("id", "?") for r in records
                 if r.get("scope") in ("m1", "fp", "m3", "m8", "m9")
                 and ("decode" in r or OLD_FIELD in r)]
    if not record("scope∈{m1,fp,m3,m8,m9} ⇒ 无 decode/旧字段", "0 条",
                  f"{len(bad_plain)} 条") or bad_plain:
        failures.append("m1/fp/m3/m8/m9 记录含 decode/旧字段: "
                        + ", ".join(bad_plain[:10]))

    # 4. `_rf`（RF 银行目的）记录的 scope 只允许 fp / excluded
    #    SPEC-161t：原判据为 `scope == fp ⇔ id.endswith("_rf")`——该等价式在引入
    #    「已定义编码但未实现」的 RF 目的指令（`ftrnd`/`fornd`，scope: excluded）后不再
    #    成立。保留原判据的**双向防线**并显式列出第三类：
    #      a) scope == fp ⇒ id 以 `_rf` 结尾（防非 RF 记录混入 fp）；
    #      b) id 以 `_rf` 结尾 ⇒ scope ∈ {fp, excluded}（防 M1/m3/m8/m9 出现 RF 记录）。
    fp_bad = [r.get("id", "?") for r in records
              if r.get("scope") == "fp" and not str(r.get("id", "")).endswith("_rf")]
    if not record("scope:fp ⇒ id 以 _rf 结尾", "0 条",
                  f"{len(fp_bad)} 条") or fp_bad:
        failures.append("fp 记录 id 不以 _rf 结尾: " + ", ".join(fp_bad[:10]))

    rf_bad = [r.get("id", "?") for r in records
              if str(r.get("id", "")).endswith("_rf")
              and r.get("scope") not in ("fp", "excluded")]
    if not record("id 以 _rf 结尾 ⇒ scope∈{fp,excluded}", "0 条",
                  f"{len(rf_bad)} 条") or rf_bad:
        failures.append("_rf 记录的 scope 非 fp/excluded: "
                        + ", ".join(rf_bad[:10]))

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
