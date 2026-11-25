#!/usr/bin/env python3
"""归档期从分册后的 `issues-*.yaml` 抽取某里程碑的 `closed` 项。

拆册后的口径（用户 2026-11-25）：里程碑收尾时**先** `--write`/`--check` 生成并
核对快照，**再**把这些 `closed` 项从活台账删除（`issues-left` 只留未解决项）。
删除后 `--check` 不再适用（活台账已无该集），改用 `--verify` 对快照做离线自检
（行数 / ID 唯一 / 计数行一致）。

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
import re
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import issues_store  # noqa: E402


def load(milestone: str) -> list[dict]:
    data = issues_store.load_all()
    picked = [
        x for x in data
        if x.get("status") == "closed" and str(x.get("closed_in")) == milestone
    ]
    picked.sort(key=issues_store.sort_key)
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
    ap.add_argument("--check", metavar="PATH",
                    help="收尾时一次性核对：归档册须与活台账的 closed 集逐字节一致"
                         "（拆册后条目会在收尾时从活台账删除，故本开关不再适用于已清理的里程碑）")
    ap.add_argument("--verify", metavar="PATH",
                    help="离线自检归档册本身（行数/ID 唯一/计数行一致）；活台账已清理时用它")
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

    if args.verify:
        if not os.path.isfile(args.verify):
            print(f"archive_issues: FAIL — {args.verify} not found", file=sys.stderr)
            return 1
        with open(args.verify, "r", encoding="utf-8") as f:
            body = f.read()
        ids = re.findall(r"^\|\s*(ISS-[^\s|]+)\s*\|", body, re.M)
        problems = []
        if len(ids) != len(set(ids)):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            problems.append(f"duplicate ids: {dup}")
        m = re.search(r"\*\*计数\*\*：\*\*(\d+) 条\*\*", body)
        if not m:
            problems.append("缺少「**计数**：**N 条**」行")
        elif int(m.group(1)) != len(ids):
            problems.append(f"计数行 {m.group(1)} != 实际行 {len(ids)}")
        if problems:
            for e in problems:
                print(f"archive_issues: FAIL — {args.verify}: {e}", file=sys.stderr)
            return 1
        print(f"archive_issues: PASS verify ({len(ids)} rows, ids unique, 计数一致)")
        return 0

    print(text)
    print(f"archive_issues: {len(rows)} row(s) for {args.milestone}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
