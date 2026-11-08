#!/usr/bin/env python3
"""check-milestones-fresh: 里程碑台账「任务流水（已开工）」+「待开始（未开工）」双表门控（L1）。

背景（用户 2026-10-18 原话，逐字）：
  「milestones.md中的任务流水表格又乱了，这个表格换成列表，而且按时间序，未完成
    的任务也需要列上；这个要求明确写到文档里，不要再乱了；另外，该文档后面的信息
    应按时更新；最后的历史台账指针没用，删除」

用户 2026-11-08 授权（逐字）：
  「milestone中，是不是把待开始的任务单独列出来，要不然实在找不到，其完成时间
    可以不写，只会增加困惑性」
  ⇒ 未开工任务单独成表、**不写时间**；流水表只留已开工 / 已完成的。

体例硬约束（拆表后）：
  1. 两个二级标题**必须都存在**：`## 任务流水（已开工）`、`## 待开始（未开工）`。
  2. 流水表列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`，状态 ∈ {`待验收`,
     `待返工`,`已验证`}——**`待开始` 不得出现在流水表**；`已验证` 不带 `（登记）`，
     其余带；**按完成时间倒序**（同一时间按编号升序）。
  3. 待开始表列 = `| 编号 | 一句改动 |`——**恰好 2 格**（无时间列、无状态列），
     不判次序；任务书状态必须是 `待开始`。
  4. 两表「一句改动」均 ≤120 字符，且不得含 `.work/<具体路径>`；细节写各任务书。
  5. 状态以任务书 `**状态**` 为准（不一致 ⇒ FAIL）。

五断言（每条均有可达 FAIL，见 `--self-test` 五类注入）：
  A1 **状态一致**：流水行状态 == 任务书 `**状态**`；待开始行任务书状态 == `待开始`。
  A2 **覆盖**：两表并集覆盖 `.tao/tasks/**` 的每份任务书、`INTEG-*m` 册列出的任务号、
     `milestones.md` 正文出现的任务号；**已归档**任务号（`.tao/archive/**` 有册）豁免，
     正文出现但全仓无册的任务号 ⇒ FAIL（悬空号）。
  A3 **长度**：两表每行「一句改动」≤ 120 字符（中文按 1 字符计）。
  A4 **次序**：**只对流水表**按完成时间**倒序**；同一时间按编号升序。待开始表不判。
  A5 **格式**：流水表恰好 4 格、状态枚举、时间 = `YYYY-MM-DD HH:MM` + `（登记）` 规则；
     待开始表恰好 2 格、同一编号不重复；两表编号不得重复出现；「一句改动」不得含
     `.work/`（细节归任务书）。

fail-closed：任一小节缺失 / 小节无表 / 表头不符 / 两表皆空 ⇒ FAIL。
不依赖 `.work/**`（易失）；只读仓库内文件。

Usage:
    python3 tools/infra/check_milestones_fresh.py [--root DIR] [--self-test]
Exit code: 0 = PASS；1 = FAIL。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MILESTONES_REL = Path(".tao/knowledge/milestones.md")
TASKS_REL = Path(".tao/tasks")
ARCHIVE_REL = Path(".tao/archive")
INTEG_M_GLOB = "INTEG-*m-*.md"

FLOW_HEADING = "## 任务流水（已开工）"
TODO_HEADING = "## 待开始（未开工）"
FLOW_HEADER = ("编号", "状态", "完成时间", "一句改动")
TODO_HEADER = ("编号", "一句改动")

TODO_STATUS = "待开始"
FLOW_STATUSES = ("待验收", "待返工", "已验证")
FINAL = "已验证"
MAX_SUMMARY = 120

TASK_ID_RE = re.compile(r"\b(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?\b")
ROW_ID_RE = re.compile(r"^(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?$")
TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})(（登记）)?$")
STATUS_RE = re.compile(r"^\*\*状态\*\*[：:]\s*([^\s*]+)", re.MULTILINE)
TASK_FILE_RE = re.compile(
    r"^((?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?)-.*\.md$")


def task_index(root: Path) -> dict[str, Path]:
    """任务号 → 任务书路径（`.tao/tasks/**` 优先，其次 `.tao/archive/**`）。"""
    index: dict[str, Path] = {}
    for reldir in (ARCHIVE_REL, TASKS_REL):  # tasks 后写 ⇒ 覆盖 archive
        d = root / reldir
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.md")):
            m = TASK_FILE_RE.match(p.name)
            if m:
                index[m.group(1)] = p
    return index


def book_status(path: Path) -> str | None:
    m = STATUS_RE.search(path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_sep(line: str) -> bool:
    cells = split_row(line)
    return bool(cells) and all(c and set(c) <= {"-", ":"} for c in cells)


def section_rows(
    text: str, heading: str, header: tuple[str, ...]
) -> tuple[list[tuple[int, str, list[str]]] | None, list[str]]:
    """解析一个小节。

    返回 `(data_rows, problems)`：
      - 小节缺失 ⇒ `(None, [])`；
      - 小节无表 / 表头不符 / 缺分隔行 ⇒ `([...], [problem...])`。
    `data_rows` = `[(行号, 原始行, 单元格)]`。
    """
    lines = text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == heading)
    except StopIteration:
        return None, []
    tlines: list[tuple[int, str]] = []
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            break
        if lines[i].startswith("|"):
            tlines.append((i + 1, lines[i]))
    if not tlines:
        return [], ["小节无表格"]
    problems: list[str] = []
    if tuple(split_row(tlines[0][1])) != header:
        problems.append(
            f"表头须为 `| {' | '.join(header)} |`，实得 {split_row(tlines[0][1])}")
    data_at = 1
    if len(tlines) < 2 or not is_sep(tlines[1][1]):
        problems.append("表头后缺分隔行（`| --- |`）")
    else:
        data_at = 2
    rows = [(n, raw, split_row(raw)) for n, raw in tlines[data_at:]]
    return rows, problems


def parse_time(cell: str) -> tuple[datetime, bool] | None:
    m = TIME_RE.match(cell)
    if not m:
        return None
    try:
        dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return dt, bool(m.group(3))


def audit(root: Path) -> int:
    print("=" * 72)
    print("check-milestones-fresh — 任务流水（已开工）+ 待开始（未开工）（L1）")
    print("=" * 72)
    errors: list[str] = []

    ms_path = root / MILESTONES_REL
    if not ms_path.is_file():
        print(f"  ERROR: 台账不存在: {MILESTONES_REL} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    text = ms_path.read_text(encoding="utf-8")

    flow_rows, flow_problems = section_rows(text, FLOW_HEADING, FLOW_HEADER)
    todo_rows, todo_problems = section_rows(text, TODO_HEADING, TODO_HEADER)

    missing = [h for h, r in ((FLOW_HEADING, flow_rows), (TODO_HEADING, todo_rows))
               if r is None]
    if missing:
        for h in missing:
            print(f"  ERROR: 缺小节 `{h}` ⇒ fail-closed")
        print(f"结果: FAIL ({len(missing)} 项)")
        return 1
    assert flow_rows is not None and todo_rows is not None
    for h, problems in ((FLOW_HEADING, flow_problems), (TODO_HEADING, todo_problems)):
        for p in problems:
            errors.append(f"{h}: {p}")
            print(f"  ERROR: `{h}` {p}")
    if not flow_rows and not todo_rows:
        errors.append("两表皆空 ⇒ vacuous FAIL")
        print("  ERROR: 「任务流水」与「待开始」两表皆无数据行 ⇒ vacuous FAIL")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print(f"  流水行（现场统计）: {len(flow_rows)}")
    print(f"  待开始行（现场统计）: {len(todo_rows)}")

    index = task_index(root)
    if not index:
        print("  ERROR: `.tao/tasks/**` 与 `.tao/archive/**` 均无任务书 ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1

    # 只有 `t` 册（普通任务）必须在表；`k`/`m` 是启动/里程碑册，按「所列任务号」核
    todo_books = {i: p for i, p in index.items()
                  if TASKS_REL.as_posix() in p.as_posix() and i.endswith("t")}
    print(f"  任务书索引（现场统计）: 活册 {len(todo_books)} / 含归档 {len(index)}")

    # ---------- 流水表：格式 + 长度 + 状态 ----------
    seen_flow: dict[str, int] = {}
    flow_parsed: list[tuple[int, str, datetime, str]] = []
    for lineno, _raw, cells in flow_rows:
        if len(cells) != 4:
            errors.append(f"L{lineno}: 流水表须 4 格，实得 {len(cells)} 格（或含内嵌 `|`）")
            print(f"  L{lineno} FAIL 格式: {len(cells)} 格")
            continue
        tid, status, tcell, summary = cells
        if not ROW_ID_RE.match(tid):
            errors.append(f"L{lineno}: 编号 `{tid}` 不合 `<PREFIX>-nnn<suffix>`")
        if tid in seen_flow:
            errors.append(f"L{lineno}: 编号 `{tid}` 重复（首次 L{seen_flow[tid]}）")
        seen_flow[tid] = lineno
        if status not in FLOW_STATUSES:
            if status == TODO_STATUS:
                errors.append(f"L{lineno} {tid}: 流水表不得出现 `待开始`"
                              f"（未开工须入「待开始（未开工）」表）")
                print(f"    L{lineno} {tid} 流水表不得出现 `待开始`")
            else:
                errors.append(f"L{lineno} {tid}: 状态 `{status}` 不在 {FLOW_STATUSES}")
        got = parse_time(tcell)
        if got is None:
            errors.append(f"L{lineno} {tid}: 时间 `{tcell}` 须为 `YYYY-MM-DD HH:MM`"
                          f"{'' if status == FINAL else ' + `（登记）`'}")
        else:
            dt, registered = got
            if status == FINAL and registered:
                errors.append(f"L{lineno} {tid}: `已验证` 不得带 `（登记）`"
                              f"（完成时间须为落地时间）")
            if status != FINAL and not registered:
                errors.append(f"L{lineno} {tid}: 未完成任务时间须加注 `（登记）`")
            flow_parsed.append((lineno, tid, dt, status))
        if len(summary) > MAX_SUMMARY:
            errors.append(f"L{lineno} {tid}: 一句改动 {len(summary)} 字符 > {MAX_SUMMARY}")
        if ".work/" in summary:
            errors.append(f"L{lineno} {tid}: 一句改动含 `.work/` 路径（细节归任务书）")
        if "\n" in summary or not summary:
            errors.append(f"L{lineno} {tid}: 一句改动为空或跨行")

    # ---------- 待开始表：格式 + 长度 ----------
    seen_todo: dict[str, int] = {}
    todo_parsed: list[tuple[int, str]] = []
    for lineno, _raw, cells in todo_rows:
        if len(cells) != 2:
            errors.append(f"L{lineno}: 待开始行须恰好 2 格（无时间列、无状态列），"
                          f"实得 {len(cells)} 格")
            print(f"  L{lineno} FAIL 格式: 待开始行 {len(cells)} 格（须 2 格）")
            continue
        tid, summary = cells
        if not ROW_ID_RE.match(tid):
            errors.append(f"L{lineno}: 编号 `{tid}` 不合 `<PREFIX>-nnn<suffix>`")
        if tid in seen_todo:
            errors.append(f"L{lineno}: 编号 `{tid}` 在待开始表重复（首次 L{seen_todo[tid]}）")
        seen_todo[tid] = lineno
        if len(summary) > MAX_SUMMARY:
            errors.append(f"L{lineno} {tid}: 一句改动 {len(summary)} 字符 > {MAX_SUMMARY}")
        if ".work/" in summary:
            errors.append(f"L{lineno} {tid}: 一句改动含 `.work/` 路径（细节归任务书）")
        if not summary:
            errors.append(f"L{lineno} {tid}: 一句改动为空")
        todo_parsed.append((lineno, tid))

    for tid in sorted(set(seen_flow) & set(seen_todo)):
        errors.append(f"编号 `{tid}` 同时出现在流水表与待开始表")

    # ---------- A1 状态一致 ----------
    print("-" * 72)
    print("  A1 状态一致（流水行 == 任务书；待开始行任务书 == `待开始`）")
    for lineno, tid, _dt, status in flow_parsed:
        p = index.get(tid)
        if p is None:
            errors.append(f"L{lineno} {tid}: 无任务书（.tao/tasks/** 与 archive/** 均无）")
            print(f"    L{lineno} {tid} MISSING 任务书")
            continue
        bs = book_status(p)
        if bs is None:
            errors.append(f"L{lineno} {tid}: 任务书无头部 `**状态**`（{p.relative_to(root)}）")
        elif bs != status:
            errors.append(f"L{lineno} {tid}: 表 `{status}` ≠ 任务书 `{bs}`"
                          f"（{p.relative_to(root)}）")
            print(f"    L{lineno} {tid} MISMATCH 表={status} 册={bs}")
    for lineno, tid in todo_parsed:
        p = index.get(tid)
        if p is None:
            errors.append(f"L{lineno} {tid}: 无任务书（.tao/tasks/** 与 archive/** 均无）")
            print(f"    L{lineno} {tid} MISSING 任务书")
            continue
        bs = book_status(p)
        if bs is None:
            errors.append(f"L{lineno} {tid}: 任务书无头部 `**状态**`（{p.relative_to(root)}）")
        elif bs != TODO_STATUS:
            errors.append(f"L{lineno} {tid}: 待开始表行任务书状态须为 `{TODO_STATUS}`，"
                          f"实为 `{bs}`（{p.relative_to(root)}）")
            print(f"    L{lineno} {tid} 待开始表行状态不符 表={TODO_STATUS} 册={bs}")
    print(f"    A1 核验 {len(flow_parsed)} 流水行 + {len(todo_parsed)} 待开始行")

    # ---------- A2 覆盖 ----------
    print("-" * 72)
    print("  A2 覆盖（两表并集 ⊇ 活册 / m 册列号 / 正文号）")
    table_ids = set(seen_flow) | set(seen_todo)
    for tid, p in sorted(todo_books.items()):
        if tid not in table_ids:
            errors.append(f"覆盖: 活任务册 {tid} 未列入台账表（{p.relative_to(root)}）")
    m_books = sorted((root / TASKS_REL).rglob(INTEG_M_GLOB))
    m_books_src = TASKS_REL.as_posix()
    if not m_books:
        # 归档边界：`Process-04 §4.1` 要求 INTEG m **自归档** ⇒ 里程碑收尾后活册可为空。
        # 此时回退 `archive/**` 的 INTEG m；两处皆无才 fail-closed（语义不变）。
        m_books = sorted((root / ARCHIVE_REL).rglob(INTEG_M_GLOB))
        m_books_src = ARCHIVE_REL.as_posix()
    if not m_books:
        errors.append("覆盖: `.tao/tasks/integ/` 与 `.tao/archive/**` 均无 `INTEG-*m-*.md` 核验册 ⇒ vacuous")
    for p in m_books:
        for tid in sorted(set(TASK_ID_RE.findall(p.read_text(encoding="utf-8")))):
            if tid not in table_ids and not (ARCHIVE_REL.as_posix() in index.get(tid, Path()).as_posix()):
                errors.append(f"覆盖: `{p.name}` 列出的 {tid} 未列入台账表")
    body = re.sub(r"(?ms)^\|.*?$", "", text)  # 去表行后扫正文
    for tid in sorted(set(TASK_ID_RE.findall(body))):
        if tid in table_ids:
            continue
        p = index.get(tid)
        if p is None:
            errors.append(f"覆盖: 正文任务号 {tid} 全仓无册（悬空号）")
        elif ARCHIVE_REL.as_posix() not in p.as_posix():
            errors.append(f"覆盖: 正文任务号 {tid} 未列入台账表（{p.relative_to(root)}）")
    print(f"    活册 {len(todo_books)} 份 / m 册 {len(m_books)} 份（源 = {m_books_src}）"
          f" / 两表 {len(table_ids)} 行（流水 {len(seen_flow)} + 待开始 {len(seen_todo)}）")

    # ---------- A4 次序（仅流水表） ----------
    print("-" * 72)
    print("  A4 次序（仅流水表：时间倒序；同一时间按编号升序；待开始表不判）")
    for (pl, pt, pd, _ps), (cl, ct, cd, _cs) in zip(flow_parsed, flow_parsed[1:]):
        if pd > cd or (pd == cd and pt < ct):
            continue
        errors.append(f"次序: L{cl} {ct}（{cd:%Y-%m-%d %H:%M}）应排在 "
                      f"L{pl} {pt}（{pd:%Y-%m-%d %H:%M}）之前")
        print(f"    L{pl} {pt} → L{cl} {ct} 逆序")
    print(f"    相邻对 {max(0, len(flow_parsed) - 1)} 个（现场统计）")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print(f"结果: PASS（流水 {len(flow_parsed)} 行 / 待开始 {len(todo_parsed)} 行；"
          f"状态一致 / 覆盖 / ≤{MAX_SUMMARY} 字符 / 流水倒序 / 格式）")
    return 0


# --------------------------------------------------------------------------
# self-test：临时树 + 五类注入（各自可达 FAIL）
# --------------------------------------------------------------------------
BASE_MS = """# 项目里程碑

## 任务流水（已开工）

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| SPEC-101t | 已验证 | 2026-10-02 10:00 | 第二新：完成，短句 |
| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |

## 待开始（未开工）

| 编号 | 一句改动 |
| --- | --- |
| QEMU-103t | 未开工：待开始表 |
"""

BOOKS = {
    "SPEC-101t": "**状态**：已验证\n",
    "INFRA-102t": "**状态**：待验收\n",
    "QEMU-103t": "**状态**：待开始\n",
}


def write_tree(root: Path, ms: str, books: dict[str, str]) -> None:
    (root / ".tao/knowledge").mkdir(parents=True)
    (root / ".tao/tasks/infra").mkdir(parents=True)
    (root / ".tao/tasks/spec").mkdir(parents=True)
    (root / ".tao/tasks/qemu").mkdir(parents=True)
    (root / ".tao/tasks/integ").mkdir(parents=True)
    (root / MILESTONES_REL).write_text(ms, encoding="utf-8")
    for tid, body in books.items():
        mod = {"SPEC": "spec", "INFRA": "infra", "QEMU": "qemu"}[tid.split("-")[0]]
        (root / ".tao/tasks" / mod / f"{tid}-x.md").write_text(
            f"# {tid}\n\n{body}\n", encoding="utf-8")
    (root / ".tao/tasks/integ/INTEG-900m-x.md").write_text(
        "**状态**：待开始\n\n列出 `SPEC-101t` / `INFRA-102t`。\n", encoding="utf-8")


def _run(root: Path) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit(root)
    return rc, buf.getvalue()


def self_test() -> int:
    print("=" * 72)
    print("check-milestones-fresh --self-test（干净基线 PASS + 五类注入各自 FAIL）")
    print("=" * 72)
    ok = True

    def case(name: str, ms: str, marker: str) -> None:
        nonlocal ok
        with tempfile.TemporaryDirectory(prefix="milestones-fresh-") as td:
            root = Path(td)
            write_tree(root, ms, BOOKS)
            rc, out = _run(root)
        hit = marker in out
        good = rc == 1 and hit
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: rc={rc} marker={hit}")

    with tempfile.TemporaryDirectory(prefix="milestones-fresh-") as td:
        root = Path(td)
        write_tree(root, BASE_MS, BOOKS)
        rc, out = _run(root)
    print(f"  {'PASS' if rc == 0 else 'FAIL'}  干净基线: rc={rc}")
    ok &= rc == 0

    case("注入① 待开始放回流水表", BASE_MS.replace(
        "| QEMU-103t | 未开工：待开始表 |\n", "").replace(
        "| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |",
        "| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |\n"
        "| QEMU-103t | 待开始 | 2026-10-01 09:00（登记） | 未开工：待开始表 |"),
        "流水表不得出现")
    case("注入② 删待开始行（覆盖缺失）", BASE_MS.replace(
        "| QEMU-103t | 未开工：待开始表 |\n", ""), "未列入台账表")
    case("注入③ 待开始行带时间列", BASE_MS.replace(
        "| QEMU-103t | 未开工：待开始表 |",
        "| QEMU-103t | 2026-10-01 09:00（登记） | 未开工：待开始表 |"), "须恰好 2 格")
    case("注入④ 表状态与任务书不符", BASE_MS.replace(
        "| INFRA-102t | 待验收 |", "| INFRA-102t | 待返工 |"), "MISMATCH")
    case("注入⑤ 流水表次序打乱", BASE_MS.replace(
        "| SPEC-101t | 已验证 | 2026-10-02 10:00 | 第二新：完成，短句 |\n"
        "| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |",
        "| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |\n"
        "| SPEC-101t | 已验证 | 2026-10-02 10:00 | 第二新：完成，短句 |"), "逆序")

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None, help="检查另一棵树（默认仓库根）")
    ap.add_argument("--self-test", action="store_true", help="跑内置五类注入自检")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-milestones-fresh: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
