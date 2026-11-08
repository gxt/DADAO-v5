#!/usr/bin/env python3
"""check-milestones-fresh: 里程碑台账三表门控（待开始 / 进行中 / 已验证；L1）。

用户 2026-11-08 授权（逐字）：
  「milestones：把待开始的列表放在任务流水前面，或者分为三类，第一类待开始，第二类
    进行中，第三类已验证；前两类，写一个预估时间；第三类，写完成时间；状态这一栏
    可以删除」
  ⇒ 三分表、待开始置前、前两类写**预估时间**、第三类写**完成时间**、**删除状态列**。

沿革（用户 2026-10-18 原话，逐字）：
  「milestones.md中的任务流水表格又乱了，这个表格换成列表，而且按时间序，未完成
    的任务也需要列上；这个要求明确写到文档里，不要再乱了；另外，该文档后面的信息
    应按时更新；最后的历史台账指针没用，删除」

体例硬约束（三分表后）：
  1. 三个二级标题**必须都存在**（顺序：待开始 → 进行中 → 已验证）：
     `## 待开始（未开工）`、`## 进行中（已提交待验收 / 待返工）`、`## 已验证`。
  2. 待开始表 / 进行中表列 = `| 编号 | 预估时间 | 一句改动 |`；已验证表列 =
     `| 编号 | 完成时间 | 一句改动 |`。**无状态列**——类别即状态。
  3. 预估时间格式 `N h` / `N–M h` / `N 天` / `N–M 天`（亦允许 `min`）；
     完成时间 `YYYY-MM-DD HH:MM`，**不得带 `（登记）`**。
  4. 三表「一句改动」均 ≤120 字符，且不得含 `.work/<具体路径>`；细节写各任务书。
  5. 类别 = 任务书 `**状态**`：`待开始` → 待开始表；`待验收` / `待返工` → 进行中表；
     `已验证` → 已验证表。

五断言（每条均有可达 FAIL，见 `--self-test` 十一类注入）：
  A1 **分类一致**：表行所属类别 == 任务书 `**状态**` 的映射（见上）；不一致 ⇒ FAIL。
  A2 **覆盖**：三表并集覆盖 `.tao/tasks/**` 的每份任务书、`INTEG-*m` 册列出的任务号、
     `milestones.md` 正文出现的任务号；**已归档**任务号（`.tao/archive/**` 有册）豁免，
     正文出现但全仓无册的任务号 ⇒ FAIL（悬空号）。
  A3 **长度**：三表每行「一句改动」≤ 120 字符（中文按 1 字符计）。
  A4 **次序**：**只对已验证表**按完成时间**倒序**（同一时间按编号升序）；前两表不判。
  A5 **格式**：三表各恰好 3 格；三表须按 `待开始 → 进行中 → 已验证` 排列；
     待开始/进行中时间列 = 预估格式；已验证时间列 =
     `YYYY-MM-DD HH:MM` 且不带 `（登记）`；**任何表不得出现状态列/状态值**；
     同一编号不重复、且不得跨表重复；「一句改动」不得含 `.work/`。

fail-closed：任一标题/表头/分隔行缺失、三表皆空 ⇒ FAIL。
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

TODO_HEADING = "## 待开始（未开工）"
WIP_HEADING = "## 进行中（已提交待验收 / 待返工）"
DONE_HEADING = "## 已验证"

TODO_HEADER = ("编号", "预估时间", "一句改动")
WIP_HEADER = ("编号", "预估时间", "一句改动")
DONE_HEADER = ("编号", "完成时间", "一句改动")

TODO_STATUSES = ("待开始",)
WIP_STATUSES = ("待验收", "待返工")
DONE_STATUSES = ("已验证",)

# (标题, 表头, 允许的任务书状态, 时间列种类)
TABLES = (
    (TODO_HEADING, TODO_HEADER, TODO_STATUSES, "est"),
    (WIP_HEADING, WIP_HEADER, WIP_STATUSES, "est"),
    (DONE_HEADING, DONE_HEADER, DONE_STATUSES, "done"),
)

# 类别即状态：任何表都不得再出现这些值作为独立单元格（状态列）。
STATUS_VALUES = ("待开始", "待验收", "待返工", "已验证")

MAX_SUMMARY = 120

TASK_ID_RE = re.compile(r"\b(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?\b")
ROW_ID_RE = re.compile(r"^(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?$")
TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})(（登记）)?$")
EST_RE = re.compile(r"^\d+(?:\.\d+)?(?:–\d+(?:\.\d+)?)?\s*(?:h|天|min)$")
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
    got_header = split_row(tlines[0][1])
    if tuple(got_header) != header:
        problems.append(
            f"表头须为 `| {' | '.join(header)} |`，实得 {got_header}")
        if any("状态" in c for c in got_header):
            problems.append("不得出现状态列（类别即状态）")
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


def check_rows(
    heading: str,
    rows: list[tuple[int, str, list[str]]],
    kind: str,
    errors: list[str],
    seen: dict[str, tuple[str, int]],
) -> list[tuple[int, str, datetime | None]]:
    """逐行格式 / 长度 / 状态列 / 重复检查；返回 `(行号, 编号, 完成时间|None)`。"""
    parsed: list[tuple[int, str, datetime | None]] = []
    for lineno, _raw, cells in rows:
        if len(cells) != 3:
            errors.append(f"`{heading}` L{lineno}: 行须恰好 3 格"
                          f"（`| 编号 | 时间 | 一句改动 |`；或含内嵌 `|`），实得 {len(cells)} 格")
            continue
        tid, tcell, summary = cells
        if not ROW_ID_RE.match(tid):
            errors.append(f"`{heading}` L{lineno}: 编号 `{tid}` 不合 `<PREFIX>-nnn<suffix>`")
        if tid in seen:
            prev_h, prev_l = seen[tid]
            kind_word = "同表重复" if prev_h == heading else "跨表重复"
            errors.append(f"`{heading}` L{lineno}: 编号 `{tid}` {kind_word}"
                          f"（首次 `{prev_h}` L{prev_l}）")
        else:
            seen[tid] = (heading, lineno)
        bad = [c for c in cells if c in STATUS_VALUES]
        if bad:
            errors.append(f"`{heading}` L{lineno}: 表内不得出现状态值/状态列 {bad}（类别即状态）")
        if kind == "est":
            if not EST_RE.match(tcell):
                errors.append(f"`{heading}` L{lineno} {tid}: 预估时间 `{tcell}` 不合格式"
                              f"（`N h` / `N–M h` / `N 天` / `N–M 天` / `min`）")
            parsed.append((lineno, tid, None))
        else:
            got = parse_time(tcell)
            if got is None:
                errors.append(f"`{heading}` L{lineno} {tid}: 完成时间 `{tcell}`"
                              f"须为 `YYYY-MM-DD HH:MM`")
            else:
                dt, registered = got
                if registered:
                    errors.append(f"`{heading}` L{lineno} {tid}: `已验证` 完成时间不得带"
                                  f" `（登记）`（须为落地时间）")
                parsed.append((lineno, tid, dt))
        if len(summary) > MAX_SUMMARY:
            errors.append(f"`{heading}` L{lineno} {tid}: 一句改动 {len(summary)} 字符 > {MAX_SUMMARY}")
        if ".work/" in summary:
            errors.append(f"`{heading}` L{lineno} {tid}: 一句改动含 `.work/` 路径（细节归任务书）")
        if not summary:
            errors.append(f"`{heading}` L{lineno} {tid}: 一句改动为空")
    return parsed


def audit(root: Path) -> int:
    print("=" * 72)
    print("check-milestones-fresh — 待开始 / 进行中 / 已验证（L1）")
    print("=" * 72)
    errors: list[str] = []

    ms_path = root / MILESTONES_REL
    if not ms_path.is_file():
        print(f"  ERROR: 台账不存在: {MILESTONES_REL} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    text = ms_path.read_text(encoding="utf-8")

    sections: dict[str, list[tuple[int, str, list[str]]]] = {}
    missing: list[str] = []
    for heading, header, _statuses, _kind in TABLES:
        rows, problems = section_rows(text, heading, header)
        if rows is None:
            missing.append(heading)
            continue
        sections[heading] = rows
        for p in problems:
            errors.append(f"`{heading}`: {p}")
    if missing:
        for h in missing:
            print(f"  ERROR: 缺小节 `{h}` ⇒ fail-closed")
        print(f"结果: FAIL ({len(missing)} 项)")
        return 1
    lines = text.split("\n")
    order = [next(i for i, l in enumerate(lines) if l.strip() == heading)
             for heading, _h, _s, _k in TABLES]
    if order != sorted(order):
        errors.append("A5 次序: 三表须按 `待开始 → 进行中 → 已验证` 排列，"
                      f"实得标题行号 {order}")
    if all(not rows for rows in sections.values()):
        print("  ERROR: 三表皆无数据行 ⇒ vacuous FAIL")
        print("结果: FAIL (1 项)")
        return 1
    for heading, header, statuses, kind in TABLES:
        print(f"  {heading[3:]} 行（现场统计）: {len(sections[heading])}")

    index = task_index(root)
    if not index:
        print("  ERROR: `.tao/tasks/**` 与 `.tao/archive/**` 均无任务书 ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1

    # 只有 `t` 册（普通任务）必须在表；`k`/`m` 是启动/里程碑册，按「所列任务号」核
    todo_books = {i: p for i, p in index.items()
                  if TASKS_REL.as_posix() in p.as_posix() and i.endswith("t")}
    print(f"  任务书索引（现场统计）: 活册 {len(todo_books)} / 含归档 {len(index)}")

    # ---------- A5 格式 + A3 长度（三表逐行） ----------
    seen: dict[str, tuple[str, int]] = {}
    parsed: dict[str, list[tuple[int, str, datetime | None]]] = {}
    for heading, _header, _statuses, kind in TABLES:
        parsed[heading] = check_rows(heading, sections[heading], kind, errors, seen)

    # ---------- A1 分类一致 ----------
    print("-" * 72)
    print("  A1 分类一致（表类别 == 任务书 `**状态**` 映射）")
    for heading, _header, statuses, _kind in TABLES:
        for lineno, tid, _dt in parsed[heading]:
            p = index.get(tid)
            if p is None:
                errors.append(f"A1: `{heading}` L{lineno} {tid}: 无任务书"
                              f"（.tao/tasks/** 与 archive/** 均无）")
                continue
            bs = book_status(p)
            if bs is None:
                errors.append(f"A1: `{heading}` L{lineno} {tid}: 任务书无头部 `**状态**`"
                              f"（{p.relative_to(root)}）")
            elif bs not in statuses:
                errors.append(f"A1: `{heading}` L{lineno} {tid}: MISMATCH 表类别={heading}"
                              f"（允许 {list(statuses)}）册={bs}（{p.relative_to(root)}）")
    print(f"    A1 核验 " + " + ".join(
        f"{heading[3:]} {len(parsed[heading])} 行" for heading, _h, _s, _k in TABLES))

    # ---------- A2 覆盖 ----------
    print("-" * 72)
    print("  A2 覆盖（三表并集 ⊇ 活册 / m 册列号 / 正文号）")
    table_ids = set(seen)
    for tid, p in sorted(todo_books.items()):
        if tid not in table_ids:
            errors.append(f"覆盖: 活任务册 {tid} 未列入台账三表（{p.relative_to(root)}）")
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
                errors.append(f"覆盖: `{p.name}` 列出的 {tid} 未列入台账三表")
    body = re.sub(r"(?ms)^\|.*?$", "", text)  # 去表行后扫正文
    for tid in sorted(set(TASK_ID_RE.findall(body))):
        if tid in table_ids:
            continue
        p = index.get(tid)
        if p is None:
            errors.append(f"覆盖: 正文任务号 {tid} 全仓无册（悬空号）")
        elif ARCHIVE_REL.as_posix() not in p.as_posix():
            errors.append(f"覆盖: 正文任务号 {tid} 未列入台账三表（{p.relative_to(root)}）")
    print(f"    活册 {len(todo_books)} 份 / m 册 {len(m_books)} 份（源 = {m_books_src}）"
          f" / 三表 {len(table_ids)} 行（" + " + ".join(
              f"{heading[3:]} {len(parsed[heading])}" for heading, _h, _s, _k in TABLES) + "）")

    # ---------- A4 次序（仅已验证表） ----------
    print("-" * 72)
    print("  A4 次序（仅已验证表：完成时间倒序；同一时间按编号升序；前两表不判）")
    done = [(lineno, tid, dt) for lineno, tid, dt in parsed[DONE_HEADING] if dt is not None]
    for (pl, pt, pd), (cl, ct, cd) in zip(done, done[1:]):
        if pd > cd or (pd == cd and pt < ct):
            continue
        errors.append(f"A4 次序: L{cl} {ct}（{cd:%Y-%m-%d %H:%M}）应排在 "
                      f"L{pl} {pt}（{pd:%Y-%m-%d %H:%M}）之前（逆序）")
    print(f"    相邻对 {max(0, len(done) - 1)} 个（现场统计）")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print("结果: PASS（" + " / ".join(
        f"{heading[3:]} {len(parsed[heading])} 行" for heading, _h, _s, _k in TABLES)
        + f"；分类一致 / 覆盖 / ≤{MAX_SUMMARY} 字符 / 已验证倒序 / 格式 / 无状态列）")
    return 0


# --------------------------------------------------------------------------
# self-test：临时树 + 十一类注入（各自可达 FAIL）
# --------------------------------------------------------------------------
BASE_MS = """# 项目里程碑

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| QEMU-103t | 1 h | 未开工：待开始表 |

## 进行中（已提交待验收 / 待返工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| INFRA-102t | 2–3 h | 待验收：进行中短句 |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| SPEC-101t | 2026-10-02 10:00 | 第二新：完成，短句 |
| INFRA-104t | 2026-10-01 09:00 | 更早：完成，短句 |
"""

BOOKS = {
    "SPEC-101t": "**状态**：已验证\n",
    "INFRA-102t": "**状态**：待验收\n",
    "QEMU-103t": "**状态**：待开始\n",
    "INFRA-104t": "**状态**：已验证\n",
}


def write_tree(root: Path, ms: str, books: dict[str, str]) -> None:
    (root / ".tao/knowledge").mkdir(parents=True)
    for mod in ("infra", "spec", "qemu", "integ"):
        (root / ".tao/tasks" / mod).mkdir(parents=True)
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


def _swap_done_first(ms: str) -> str:
    """把「已验证」节移到最前（三表次序反例）。"""
    head, *sections = ms.split("\n## ")
    done_idx = next(i for i, s in enumerate(sections) if s.startswith(DONE_HEADING[3:]))
    done = sections.pop(done_idx)
    return head + "\n## " + done + "".join("\n## " + s for s in sections)


def self_test() -> int:
    print("=" * 72)
    print("check-milestones-fresh --self-test（干净基线 PASS + 十一类注入各自 FAIL）")
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

    case("注入① 待开始行放进进行中表", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |\n", "").replace(
        "| INFRA-102t | 2–3 h | 待验收：进行中短句 |",
        "| INFRA-102t | 2–3 h | 待验收：进行中短句 |\n"
        "| QEMU-103t | 1 h | 未开工：待开始表 |"), "MISMATCH")
    case("注入② 预估时间格式非法", BASE_MS.replace(
        "| QEMU-103t | 1 h |", "| QEMU-103t | soon |"), "预估时间")
    case("注入③ 完成时间带（登记）", BASE_MS.replace(
        "2026-10-02 10:00 |", "2026-10-02 10:00（登记） |"), "不得带")
    case("注入④ 同号跨表重复", BASE_MS.replace(
        "| INFRA-102t | 2–3 h | 待验收：进行中短句 |",
        "| INFRA-102t | 2–3 h | 待验收：进行中短句 |\n"
        "| QEMU-103t | 1 h | 重复行 |"), "跨表重复")
    case("注入⑤ 已验证表次序打乱", BASE_MS.replace(
        "| SPEC-101t | 2026-10-02 10:00 | 第二新：完成，短句 |\n"
        "| INFRA-104t | 2026-10-01 09:00 | 更早：完成，短句 |",
        "| INFRA-104t | 2026-10-01 09:00 | 更早：完成，短句 |\n"
        "| SPEC-101t | 2026-10-02 10:00 | 第二新：完成，短句 |"), "逆序")
    case("注入⑥ 已验证表加回状态列", BASE_MS.replace(
        "| 编号 | 完成时间 | 一句改动 |\n| --- | --- | --- |\n",
        "| 编号 | 状态 | 完成时间 | 一句改动 |\n| --- | --- | --- | --- |\n"), "状态列")
    case("注入⑦ 三表次序打乱（已验证置前）", _swap_done_first(BASE_MS), "三表须按")
    case("注入⑧ 待开始行缺失（覆盖）", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |\n", ""), "未列入台账三表")
    case("注入⑨ 缺「进行中」小节", BASE_MS.replace(
        "\n## 进行中（已提交待验收 / 待返工）\n", "\n"), "缺小节")
    case("注入⑩ 一句改动超长（A3）", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |",
        "| QEMU-103t | 1 h | " + "长" * 121 + " |"), f"字符 > {MAX_SUMMARY}")
    case("注入⑪ 一句改动含 `.work` 路径", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |",
        "| QEMU-103t | 1 h | 见 .work/log/x |"), "`.work/` 路径")

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None, help="检查另一棵树（默认仓库根）")
    ap.add_argument("--self-test", action="store_true", help="跑内置十一类注入自检")
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
