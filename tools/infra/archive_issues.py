#!/usr/bin/env python3
"""归档期从 `issues.yaml` 抽取某里程碑的 `closed` 项。

判据（单一）：`status: closed` **且** `closed_in == <里程碑>`。
不再按 `resolved_by` 的任务提交日反推 —— 任务号后缀、跨里程碑提交、文本型
`resolved_by`（如「用户裁定」）都会让反推失准。

用法：
  python3 tools/infra/archive_issues.py --milestone M13              # 只打印，不写文件
  python3 tools/infra/archive_issues.py --milestone M13 --write PATH # 写归档册
  python3 tools/infra/archive_issues.py --milestone M13 --check PATH # 校验归档册 == 现场集

退出码：0 = 一致 / 1 = 不一致或缺文件 / 2 = 用法或数据错误。
"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ISSUES = os.path.join(ROOT, ".tao", "knowledge", "issues.yaml")


def load(milestone: str) -> list[dict]:
    with open(ISSUES, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise SystemExit("issues.yaml must be a list")
    picked = [
        x for x in data
        if x.get("status") == "closed" and str(x.get("closed_in")) == milestone
    ]
    picked.sort(key=lambda x: int(str(x["id"]).split("-")[1]))
    return picked


def render(milestone: str, rows: list[dict]) -> str:
    lines = [
        f"<!-- 由 tools/infra/archive_issues.py 按 closed_in == {milestone} 生成，勿手改 -->",
        "",
        f"# {milestone} 阶段已关闭 Issue",
        "",
        f"> **判据**：`status: closed` 且 `closed_in == {milestone}`（关闭时写定，归档直接取集）。",
        f"> **计数**：**{len(rows)} 条**。",
        "",
        "| id | scope | resolved_by | title |",
        "| --- | --- | --- | --- |",
    ]
    for r in rows:
        scope = ", ".join(r.get("scope") or [])
        title = str(r.get("title", "")).replace("|", "\\|")
        lines.append(f"| {r['id']} | [{scope}] | {r.get('resolved_by')} | {title} |")
    if not rows:
        lines.append("| — | — | — | 本里程碑无关闭项 |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--milestone", required=True, help="里程碑编号，如 M13")
    ap.add_argument("--write", metavar="PATH", help="写入归档册")
    ap.add_argument("--check", metavar="PATH", help="校验归档册与现场集一致")
    args = ap.parse_args()

    rows = load(args.milestone)
    text = render(args.milestone, rows)

    if args.write:
        with open(args.write, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"archive_issues: wrote {args.write} ({len(rows)} rows)")
        return 0

    if args.check:
        if not os.path.isfile(args.check):
            print(f"archive_issues: FAIL — {args.check} not found", file=sys.stderr)
            return 1
        with open(args.check, "r", encoding="utf-8") as f:
            have = f.read()
        if have != text:
            print(f"archive_issues: FAIL — {args.check} != 现场集 ({len(rows)} rows)", file=sys.stderr)
            return 1
        print(f"archive_issues: PASS ({len(rows)} rows, closed_in == {args.milestone})")
        return 0

    print(text)
    print(f"archive_issues: {len(rows)} row(s) for {args.milestone}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
