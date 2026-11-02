#!/usr/bin/env python3
"""任务书自查清单（报告型，非门控）。

列出**两组**供收尾 / `/status` 可见的信息：

1. **漏收尾（主表）**：「完成区已填（非占位）但 ``**状态**`` 仍为 ``待验收``」的任务书
   —— 即疑似「漏 /complete」的任务。
2. **已立但仍未开工（附表）**：``**状态**`` 仍为 ``待开始`` 的任务书 —— 即**队列可见性**
   （已落盘、未派工；``k``/``m`` 类亦计入）。

判据
----
* **状态命中（主表）**：任务书首个 ``**状态**：<值>`` 行的值**以 ``待验收`` 开头**
  （兼容 ``待验收（…）`` 变体；``待返工``/``已验证``/``待开始`` 不计入）。
* **状态命中（附表）**：同法，值**以 ``待开始`` 开头**（不含 ``待验收``/``待返工``/``已验证``）。
* **完成区已填**：提取 ``## 完成区`` 段（至下一个 ``^## `` 标题或文件末），
  要求 ``**测试结果**`` 与 ``**验收结果**`` **至少一项非空**；仅去掉字段标签
  与占位（``（待填写）``/``(待填写)``）及空白后仍为空者视为**未填**。
  （``**新发现/坑**``、``**遗留问题**`` 等字段不计入——避免仅「新发现」有字
  就误判为已填；见任务书 INFRA-029t 开放问题①裁定。）
* 无 ``## 完成区`` 的文件（``k``/``m`` 类）**不进主表**；附表不看完成区。

退出码
------
* 默认**恒为 0**（报告型，即使列出多个也不阻断）。
* ``--strict`` 且**主表**（漏收尾）计数 > 0 ⇒ 返回 1（附表**不影响**退出码——未开工属队列状态、非缺陷）。
* 硬错误（仓库根 / ``.tao/tasks`` 不存在）⇒ 返回 2。

本工具**只读**，不修改任何文件。不并入 ``make check`` 阻断路径。

Usage::

    python3 tools/infra/check_tasks.py [--repo-root DIR] [--strict]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# tools/infra/check_tasks.py → 仓库根
ROOT = Path(__file__).resolve().parents[2]

# 任务书状态行：**状态**：待验收 | **状态**: 待验收（…）
RE_STATUS = re.compile(r"^\*\*状态\*\*[：:]\s*(.+?)\s*$")

# 完成区内的字段标签行（用于切分字段值的边界）。
# 允许标签后带一个括号限定语，如 ``**验收结果**（round 4 全量重跑）：``。
RE_FIELD_LABEL = re.compile(
    r"^\*\*[^*]+\*\*(?:\s*[（(][^）)]*[）)])?\s*[：:]"
)
# 字段标签后的可选括号限定语
RE_LABEL_QUALIFIER = re.compile(r"^\s*[（(][^）)]*[）)]")

# 完成区起始标题（精确匹配二级标题）
RE_COMPLETION_HEADING = re.compile(r"^##\s+完成区\s*$")
# 下一个二级标题（排除 ### 等）
RE_H2 = re.compile(r"^##\s")

# 计入「已填」判据的字段（至少一项非空）
COMPLETION_FIELDS = ("测试结果", "验收结果")

# 占位标记：剥离后仍为空 ⇒ 视为未填
PLACEHOLDER_RE = re.compile(r"[（(]\s*待填写\s*[）)]")


def read_status(text: str) -> str | None:
    """返回任务书首个 ``**状态**`` 行的值；无则 None。"""
    for line in text.splitlines():
        m = RE_STATUS.match(line.strip())
        if m:
            return m.group(1)
    return None


def extract_completion(text: str) -> str | None:
    """返回 ``## 完成区`` 段正文（不含标题行）；无该段 ⇒ None。"""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if RE_COMPLETION_HEADING.match(line.strip()):
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start, len(lines)):
        if RE_H2.match(lines[i]):
            end = i
            break
    return "\n".join(lines[start:end])


def field_value(section: str, field: str) -> str:
    """提取命名字段的值：标签行冒号后的余文 + 后继行（至下个字段标签或段末）。

    兼容标签后带括号限定语的写法，如 ``**验收结果**（round 4 全量重跑）：``。
    """
    lines = section.splitlines()
    marker = f"**{field}**"
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith(marker):
            continue
        after = stripped[len(marker):]
        after = RE_LABEL_QUALIFIER.sub("", after)
        if after[:1] in ("：", ":"):
            start = (i, after[1:])
            break
        if not after.strip():
            # 标签独占一行，值在后续行
            start = (i, "")
            break
    if start is None:
        return ""
    i0, same_line = start
    parts = [same_line]
    for line in lines[i0 + 1:]:
        if RE_FIELD_LABEL.match(line.strip()):
            break
        parts.append(line)
    return "\n".join(parts)


def is_field_filled(section: str, field: str) -> bool:
    value = field_value(section, field)
    value = PLACEHOLDER_RE.sub("", value)
    return bool(value.strip())


def is_completion_filled(section: str) -> bool:
    """``测试结果`` 或 ``验收结果`` 至少一项非空 ⇒ 已填。"""
    return any(is_field_filled(section, f) for f in COMPLETION_FIELDS)


def scan(repo_root: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str]], int]:
    """返回 (漏收尾命中 [(相对路径, 状态)], 未开工命中 [(相对路径, 状态)], 扫描文件数)。"""
    tasks_dir = repo_root / ".tao" / "tasks"
    if not tasks_dir.is_dir():
        raise FileNotFoundError(f"tasks 目录不存在: {tasks_dir}")

    pending: list[tuple[str, str]] = []
    not_started: list[tuple[str, str]] = []
    scanned = 0
    for path in sorted(tasks_dir.glob("**/*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"跳过（读取失败）: {path}: {exc}")
            continue
        scanned += 1

        status = read_status(text)
        if status is None:
            continue
        rel = path.relative_to(repo_root).as_posix()

        if status.startswith("待开始"):
            not_started.append((rel, status))
            continue
        if not status.startswith("待验收"):
            continue
        section = extract_completion(text)
        if section is None:
            continue  # k/m 类无完成区，跳过
        if not is_completion_filled(section):
            continue
        pending.append((rel, status))
    return pending, not_started, scanned


def main() -> int:
    parser = argparse.ArgumentParser(
        description="任务书自查清单（报告型，非门控）：漏收尾 + 已立未开工"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="仓库根目录（默认：脚本向上 2 级）",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="**漏收尾**（完成区已填 + 状态待验收）计数 > 0 时以非零退出（默认报告型恒 0；已立未开工附表不影响）",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve() if args.repo_root else ROOT

    try:
        pending, not_started, scanned = scan(repo_root)
    except FileNotFoundError as exc:
        print(f"check-tasks: ERROR — {exc}", file=sys.stderr)
        return 2

    print("── 任务书自查清单（报告型，非门控）──")
    print(f"仓库根: {repo_root}")
    print(f"扫描任务书: {scanned} 个（.tao/tasks/ 下全部 .md）")
    print()
    if pending:
        print("① 完成区已填但状态仍为「待验收」的任务（疑似漏 /complete）：")
        for rel, status in pending:
            print(f"  {rel} | {status}")
    else:
        print("① 完成区已填但状态仍为「待验收」的任务：（无）")
    print()
    if not_started:
        print("② 已立但仍为「待开始」的任务（队列可见性，非缺陷）：")
        for rel, status in not_started:
            print(f"  {rel} | {status}")
    else:
        print("② 已立但仍为「待开始」的任务：（无）")
    print()
    print(f"计数（① 漏收尾）: {len(pending)}")
    print(f"计数（② 已立未开工）: {len(not_started)}")
    print(
        "提示：① 完成区已填但状态仍为「待验收」——疑似漏 /complete（报告型，不阻断）；"
        "② 已落盘待开工——供收尾 / `/status` 判队列，不阻断。"
    )

    if args.strict and pending:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
