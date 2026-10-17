#!/usr/bin/env python3
"""check-contracts-pending: 契约「待定」类标记必须带 ADR/ISS 指针（B4，2026-10-17）。

背景：`.tao/contracts/**` 是人读契约正文（归一化叙述）。契约里出现
「待定 / 待裁定 / TODO / TBD」这类**未决标记**时，若不同时给出**决策落点**
（`ADR-<n>`）或**问题落点**（`ISS-<n>`），该标记就会变成无人认领的悬空状态
（既不知道谁来定、也不知道何时定）。本门控把它落为机械判据：

  - 标记（行内命中即算）：``待…定``（含 ``待定`` / ``待裁定`` / ``待用户裁定`` /
    ``待后继 ADR 定`` 等）、``TODO``、``TBD``；
  - 指针：同一行必须出现 ``ADR-<3~4 位数字>`` 或 ``ISS-<3~4 位数字>``
    ——**只认带编号的指针**（光写「待后继 ADR 定」不算：它没有落点）；
  - 不计入的上下文：**行内代码跨度**（`` `…` ``）与**中文引号引用**（``「…」``）
    内的字样是「引用/约定说明」，不是待定项（例：`来源标注` 约定句里引用的
    「待用户裁定」）。

口径：**行级**判定（行 = 契约正文的一条语句；本仓库契约为一行一句的长行体例）。
**不得**为了变绿而放宽判据（如允许「块级」指针或删除标记文字）——命中即为真实
待补指针项，由 architect 决定补指针 / 另立任务 / 改契约（本工具只读）。

设计要点（`docs/Process-07 §5`）：
  - **fail-closed**：`.tao/contracts/` 缺失、或**无任何** ``*.md`` ⇒ 非零；
  - **计数现场统计、不写死**；
  - **可达 FAIL**：`--self-test` 内置「反例 ⇒ 期望 FAIL」用例（不写死真实文件内容）。

Usage:
    python3 tools/infra/check_contracts_pending.py [--root DIR] [--self-test]

``--root DIR`` 检查另一棵树（默认仓库根）；契约目录 = ``<root>/.tao/contracts``。
Exit code: 有未带指针的待定标记 / 扫描面 vacuous ⇒ 非零；``--self-test`` 有断言
不符 ⇒ 非零。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_REL = Path(".tao") / "contracts"

# 未决标记：`待…定`（≤12 个非标点字符） / TODO / TBD
MARKER_RE = re.compile(r"待[^，。；：、\n|》」』]{0,12}?定|\btodo\b|\btbd\b",
                       re.IGNORECASE)
# 决策 / 问题落点：只认「带编号」的指针
POINTER_RE = re.compile(r"\b(?:ADR|ISS)-\d{3,4}\b")
# 引用上下文：行内代码跨度、中文引号
CODE_SPAN_RE = re.compile(r"`[^`]*`")
QUOTE_RE = re.compile(r"「[^」]*」")

_MAX_TEXT = 120


def mask_quoted(line: str) -> str:
    """抹掉「引用 / 约定说明」上下文（代码跨度 + 中文引号），保留位置无关内容。"""
    return QUOTE_RE.sub("", CODE_SPAN_RE.sub("", line))


def scan_lines(lines: list[str]) -> list[tuple[int, str, str]]:
    """返回 [(行号, 标记, 原行)]——命中了标记但同行无指针的行。"""
    violations: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(lines, 1):
        m = MARKER_RE.search(mask_quoted(line))
        if not m:
            continue
        if POINTER_RE.search(line):
            continue
        violations.append((lineno, m.group(0), line.strip()))
    return violations


def count_markers(lines: list[str]) -> int:
    """标记总命中数（含已带指针者），用于「自证非空转」的现场统计。"""
    return sum(1 for line in lines if MARKER_RE.search(mask_quoted(line)))


def audit(root: Path) -> int:
    print("=" * 72)
    print("check-contracts-pending — 契约待定标记须带 ADR-/ISS- 指针（B4）")
    print("=" * 72)

    d = root / CONTRACTS_REL
    if not d.is_dir():
        print(f"  ERROR: 契约目录不存在: {CONTRACTS_REL} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1

    files = sorted(p for p in d.rglob("*.md") if p.is_file())
    print(f"  契约文件（现场统计）: {len(files)} 个（{CONTRACTS_REL}/**/*.md）")
    if not files:
        print(f"  ERROR: {CONTRACTS_REL}/ 下无任何 *.md ⇒ 扫描面 vacuous（fail-closed）")
        print("结果: FAIL (1 项)")
        return 1

    total_lines = 0
    total_markers = 0
    violations: list[tuple[str, int, str, str]] = []
    for p in files:
        lines = p.read_text(encoding="utf-8").splitlines()
        total_lines += len(lines)
        total_markers += count_markers(lines)
        for lineno, marker, text in scan_lines(lines):
            rel = p.relative_to(root).as_posix()
            violations.append((rel, lineno, marker, text))

    print(f"  扫描行数（现场统计）: {total_lines}")
    print(f"  待定标记命中（现场统计，含已带指针者）: {total_markers}")
    print(f"  判据: 标记行须同行含 ADR-<n> / ISS-<n>；代码跨度与「」引用不计")

    for rel, lineno, marker, text in violations:
        print(f"  VIOLATION: {rel}:{lineno}: [{marker}] {text[:_MAX_TEXT]}")

    print("-" * 72)
    if not violations:
        print("结果: PASS (所有待定标记均带 ADR-/ISS- 指针)")
        return 0
    print(f"结果: FAIL ({len(violations)} 项未带指针)")
    return 1


def _assert(name: str, expected: int, actual: int) -> bool:
    ok = expected == actual
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: expect={expected} actual={actual}")
    return ok


def self_test() -> int:
    print("=" * 72)
    print("check-contracts-pending --self-test（内置反例 ⇒ 期望 FAIL）")
    print("=" * 72)
    ok = True

    # 反例 1：裸「待定」无指针 ⇒ 1 项
    ok &= _assert(
        "裸待定无指针",
        1,
        len(scan_lines(["| 1 | 超时口径 | 待定 |"])),
    )
    # 正例 1：同行带 ADR 指针 ⇒ 0 项
    ok &= _assert(
        "待定 + ADR 指针",
        0,
        len(scan_lines(["| 1 | 超时口径 | 待定，落点 ADR-0001 |"])),
    )
    # 正例 2：同行带 ISS 指针 ⇒ 0 项
    ok &= _assert(
        "待裁定 + ISS 指针",
        0,
        len(scan_lines(["- 绑定时机：待裁定（ISS-246）"])),
    )
    # 反例 2：只写「待后继 ADR 定」（无编号）⇒ 1 项
    ok &= _assert(
        "待后继 ADR 定（无编号指针）",
        1,
        len(scan_lines(["- 布局：待后继 ADR 定"])),
    )
    # 正例 3：引用 / 约定说明内的字样不计（代码跨度 + 「」）
    ok &= _assert(
        "引用上下文不计",
        0,
        len(scan_lines(["> 约定：未定者标 `[spec-decision]` 并写明「待用户裁定」"])),
    )
    # 反例 3：TODO / TBD ⇒ 各 1 项
    ok &= _assert(
        "TODO 无指针",
        1,
        len(scan_lines(["- TODO: 补 §4 表"])),
    )
    ok &= _assert(
        "TBD 无指针",
        1,
        len(scan_lines(["- TBD"])),
    )
    # 反例 4：带编号但号段过短（ADR-12）不算指针 ⇒ 1 项
    ok &= _assert(
        "ADR-12 非合法指针",
        1,
        len(scan_lines(["- 待定（ADR-12）"])),
    )

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
        print(f"check-contracts-pending: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
