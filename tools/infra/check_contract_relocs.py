#!/usr/bin/env python3
"""check-contract-relocs: 两份契约的重定位类型表机械一致（B5，2026-10-17）。

背景：重定位类型号 / 名有两个**人读正文落点**——

  - ``.tao/contracts/contract-elf.md`` **§2.2「类型与编号」**（ELF 对象 ABI 侧）；
  - ``.tao/contracts/contract-dynlink.md`` **§4.3「DADAO 重定位类型总表」**（动态链接侧）。

两边都是**人读表**（非生成物）⇒ 会漂移。本门控把「两份现行表逐行一致」落为机械
判据：**类型号 ↔ 名**的映射必须**完全相同**（本轮只比号与名；公式 / 场景列不在
判据内）。

**区分「现行表」与「历史注记」**（关键）：

  - 只解析**两个小节内**的**表格行**（``| <号> | `R_DADAO_<名>` | …``）；
  - 小节内的**散文注记**（如「原 `R_DADAO_REL32`（`14`）/ `NUM` `14 → 15` 已撤回」）
    与**其它小节的历史表**（如 `contract-dynlink §4.4` 的改号前占用、`§9.1` 的候选表）
    **不参与**比对 ⇒ 旧值可以留在历史注记里，**以现行表为准**。

附加自洽断言（防「两边同错 / 表被删行」）：

  - 每个表**非空**（vacuous ⇒ FAIL）；
  - 表内**号唯一、名唯一**；
  - 号**从 0 起密集无空档**（契约自身「全密无空档」口径）。

本工具**只读**，不改任何契约（不一致由 architect 决定以哪边为准 + 补授权）。

Usage:
    python3 tools/infra/check_contract_relocs.py [--root DIR] [--self-test]

``--root DIR`` 检查另一棵树（默认仓库根）。
Exit code: 不一致 / 表缺失 / vacuous / 自洽断言失败 ⇒ 非零。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (标签, 文件, 小节标题锚点)
SECTIONS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("elf", ".tao/contracts/contract-elf.md", re.compile(r"^###\s*§2\.2\b")),
    ("dynlink", ".tao/contracts/contract-dynlink.md", re.compile(r"^###\s*§4\.3\b")),
)

# 表格行：| <号> | `R_DADAO_<名>` | …
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*`?R_DADAO_([A-Za-z0-9_]+)`?\s*\|")
# 小节结束：下一个 1~3 级标题（§2.2 → §2.3 / §4.3 → §4.4）
NEXT_HEADING_RE = re.compile(r"^#{1,3}\s")

_MAX_TEXT = 160


def extract_section(lines: list[str], heading: re.Pattern[str]) -> tuple[int, list[tuple[int, str]]] | None:
    """返回 (标题行号, [(行号, 行文本)]) —— 小节内除标题外的全部行；找不到 ⇒ None。"""
    for i, line in enumerate(lines):
        if heading.match(line):
            body: list[tuple[int, str]] = []
            for j in range(i + 1, len(lines)):
                if NEXT_HEADING_RE.match(lines[j]):
                    break
                body.append((j + 1, lines[j]))
            return i + 1, body
    return None


def parse_rows(body: list[tuple[int, str]]) -> list[tuple[int, str, int]]:
    """返回 [(类型号, 类型名（去 R_DADAO_ 前缀）, 行号)]。"""
    rows: list[tuple[int, str, int]] = []
    for lineno, line in body:
        m = ROW_RE.match(line)
        if m:
            rows.append((int(m.group(1)), m.group(2), lineno))
    return rows


def table_errors(label: str, rows: list[tuple[int, str, int]]) -> list[str]:
    """单表自洽断言（非空 / 号名唯一 / 号密集）。"""
    errors: list[str] = []
    if not rows:
        return [f"{label}: 小节内未解析到任何类型表行 ⇒ vacuous（表被删/标题改名？）"]

    nums = [r[0] for r in rows]
    names = [r[1] for r in rows]
    dup_nums = sorted({n for n in nums if nums.count(n) > 1})
    dup_names = sorted({n for n in names if names.count(n) > 1})
    if dup_nums:
        errors.append(f"{label}: 类型号重复 {dup_nums}")
    if dup_names:
        errors.append(f"{label}: 类型名重复 {dup_names}")
    if nums != list(range(len(nums))):
        errors.append(f"{label}: 类型号非「0 起密集无空档」（实际 {nums}）")
    return errors


def compare(label_a: str, a: list[tuple[int, str, int]],
            label_b: str, b: list[tuple[int, str, int]]) -> list[str]:
    """两份现行表的 (号, 名) 映射逐项比对。"""
    errors: list[str] = []
    map_a = {n: name for n, name, _ in a}
    map_b = {n: name for n, name, _ in b}
    for n in sorted(set(map_a) | set(map_b)):
        if n not in map_a:
            errors.append(f"号 {n}: 只在 {label_b}（{map_b[n]}），{label_a} 缺失")
        elif n not in map_b:
            errors.append(f"号 {n}: 只在 {label_a}（{map_a[n]}），{label_b} 缺失")
        elif map_a[n] != map_b[n]:
            errors.append(f"号 {n}: 名不一致 —— {label_a}=R_DADAO_{map_a[n]} vs "
                          f"{label_b}=R_DADAO_{map_b[n]}")
    return errors


def audit(root: Path) -> int:
    print("=" * 72)
    print("check-contract-relocs — 契约重定位类型表一致（contract-elf §2.2 ↔ contract-dynlink §4.3）")
    print("=" * 72)

    parsed: dict[str, list[tuple[int, str, int]]] = {}
    errors: list[str] = []

    for label, rel, heading in SECTIONS:
        path = root / rel
        if not path.is_file():
            errors.append(f"{label}: 文件不存在: {rel}")
            print(f"  [{label}] ERROR: 文件不存在: {rel} ⇒ fail-closed")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        got = extract_section(lines, heading)
        if got is None:
            errors.append(f"{label}: 未找到小节标题 {heading.pattern}: {rel}")
            print(f"  [{label}] ERROR: 未找到小节标题 {heading.pattern}")
            continue
        heading_lineno, body = got
        rows = parse_rows(body)
        parsed[label] = rows
        print(f"  [{label}] {rel}:{heading_lineno} — 表行 {len(rows)} 条（现场统计）"
              + (f"，号 {rows[0][0]}..{rows[-1][0]}" if rows else ""))
        errors.extend(table_errors(label, rows))

    if len(parsed) == len(SECTIONS):
        errors.extend(compare(SECTIONS[0][0], parsed[SECTIONS[0][0]],
                              SECTIONS[1][0], parsed[SECTIONS[1][0]]))

    for e in errors:
        print(f"  VIOLATION: {e[:_MAX_TEXT]}")

    print("-" * 72)
    if errors:
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print("结果: PASS (两份现行表的类型号 / 名逐项一致)")
    return 0


def _assert(name: str, expected: int, actual: int) -> bool:
    ok = expected == actual
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: expect={expected} actual={actual}")
    return ok


def _fixture(elf_rows: list[str], dyn_rows: list[str]) -> tuple[list[str], list[str]]:
    """构造两侧小节文本（含历史注记散文，用于证明「注记不参与」）。"""
    elf = ["### §2.2 类型与编号", "", "| 编号 | 名 |", "|---|---|", *elf_rows, "",
           "注：历史 `R_DADAO_REL32` = `14` 已撤回。"]
    dyn = ["### §4.3 总表", "", "| 编号 | 名 |", "|---|---|", *dyn_rows, "",
           "注：原 `NUM` `14 → 15` 已撤回（旧值仅历史注记）。"]
    return elf, dyn


def self_test() -> int:
    print("=" * 72)
    print("check-contract-relocs --self-test（内置反例 ⇒ 期望 FAIL）")
    print("=" * 72)
    ok = True

    rows = ["| 0 | `R_DADAO_NONE` |", "| 1 | `R_DADAO_REL26` |", "| 2 | `R_DADAO_NUM` |"]

    elf, dyn = _fixture(rows, rows)
    a = parse_rows(list(enumerate(elf, 1)))
    b = parse_rows(list(enumerate(dyn, 1)))
    ok &= _assert("两表一致（0 起密集）⇒ 0 项", 0,
                  len(table_errors("elf", a) + table_errors("dyn", b)
                      + compare("elf", a, "dyn", b)))

    # 反例 1：号 1 的名不一致（REL26 vs REL20）
    bad = ["| 0 | `R_DADAO_NONE` |", "| 1 | `R_DADAO_REL20` |", "| 2 | `R_DADAO_NUM` |"]
    bad_b = parse_rows(list(enumerate(bad, 1)))
    ok &= _assert("号 1 名不一致 ⇒ 1 项", 1, len(compare("elf", a, "dyn", bad_b)))

    # 反例 2：一侧少一行（号 2 只在 elf）
    short_b = parse_rows(list(enumerate(rows[:2], 1)))
    ok &= _assert("号只在一侧 ⇒ 1 项", 1, len(compare("elf", a, "dyn", short_b)))

    # 反例 3：表被删空 ⇒ vacuous 1 项
    ok &= _assert("空表 ⇒ vacuous", 1, len(table_errors("elf", [])))

    # 反例 4：号有空档（0,2）⇒ 自洽断言 1 项
    gap = parse_rows(list(enumerate(["| 0 | `R_DADAO_NONE` |", "| 2 | `R_DADAO_REL20` |"], 1)))
    ok &= _assert("号非密集（0,2）⇒ 1 项", 1, len(table_errors("elf", gap)))

    # 正例：契约 §4.4 风格的历史注记文本不产生表行
    hist = ["- **事实**：`ABS48`=0、`REL26`=1 … `R_DADAO_NUM`=6。"]
    ok &= _assert("历史注记不产生表行", 0, len(parse_rows(list(enumerate(hist, 1)))))

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None,
                        help="检查另一棵树（默认仓库根）")
    parser.add_argument("--self-test", action="store_true",
                        help="跑内置反例自检（不读仓库）")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-contract-relocs: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
