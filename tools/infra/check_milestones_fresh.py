#!/usr/bin/env python3
"""check-milestones-fresh: 里程碑台账「任务流水」的体例 / 状态一致性门控（L1）。

背景（用户 2026-10-18 原话，逐字）：
  「milestones.md中的任务流水表格又乱了，这个表格换成列表，而且按时间序，未完成
    的任务也需要列上；这个要求明确写到文档里，不要再乱了；另外，该文档后面的信息
    应按时更新；最后的历史台账指针没用，删除」

体例硬约束（`milestones.md`「体例约定（硬约束）」；本脚本把可机械判的部分落为门控）：
  1. 任务流水**保留表格**，列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；
     **一句改动 ≤120 字符**；细节写各任务书（本页只做索引）。
  2. **按完成时间倒序**；**未完成任务也必须列**，时间列 = **登记时间**并加注
     `（登记）`；同一时间按任务编号升序。
  3. **状态以任务书 `**状态**` 为准**（不一致 ⇒ FAIL）。
  4. 表格之后的进度信息须同步刷新（本脚本只管表格；计数**不写死**）。

五断言（每条均有可达 FAIL，见 `--self-test` 五类注入）：
  A1 **状态一致**：表行状态 == 该任务书头部 `**状态**`（任务书缺失 ⇒ FAIL）。
  A2 **覆盖**：`.tao/tasks/**` 的每份任务书、`INTEG-*m` 册列出的任务号、
     `milestones.md` 正文出现的任务号，都必须在流水表内；正文/`m` 册中出现的
     **已归档**任务号（`.tao/archive/**` 有册）豁免（历史行不要求回填到当前流水）。
     正文出现但全仓无册的任务号 ⇒ FAIL（悬空号）。
  A3 **长度**：每行「一句改动」≤ 120 字符（中文按 1 字符计）。
  A4 **次序**：按完成时间（未完成 = 登记时间）**倒序**；同一时间按编号升序。
  A5 **格式**：恰好 4 格、无内嵌 `|`/换行；状态 ∈ {`待开始`,`待验收`,`待返工`,
     `已验证`}；时间 = `YYYY-MM-DD HH:MM`；未完成必须带 `（登记）`，`已验证` 不得带；
     「一句改动」不得含 `.work/<具体路径>`（细节归任务书）。

不依赖 `.work/**`（易失）；只读仓库内文件。
fail-closed：流水表不存在 / 无数据行 / 无 `INTEG-*m` 册 ⇒ FAIL。

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

STATUSES = ("待开始", "待验收", "待返工", "已验证")
FINAL = "已验证"
MAX_SUMMARY = 120

TASK_ID_RE = re.compile(r"\b(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG)-\d{3}[a-z]?\b")
ROW_ID_RE = re.compile(r"^(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG)-\d{3}[a-z]?$")
TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})(（登记）)?$")
STATUS_RE = re.compile(r"^\*\*状态\*\*[：:]\s*([^\s*]+)", re.MULTILINE)
TASK_FILE_RE = re.compile(
    r"^((?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG)-\d{3}[a-z]?)-.*\.md$")


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


def flow_rows(text: str) -> list[tuple[int, str, list[str]]]:
    """返回 [(行号, 原始行, 单元格)]；只取「## 任务流水」小节内的表行。"""
    lines = text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## 任务流水")
    except StopIteration:
        return []
    out: list[tuple[int, str, list[str]]] = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0] in ("编号", "---") or set(cells[0]) <= {"-"}:
            continue
        out.append((i + 1, line, cells))
    return out


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
    print("check-milestones-fresh — 任务流水 体例 / 状态一致性（L1）")
    print("=" * 72)
    errors: list[str] = []

    ms_path = root / MILESTONES_REL
    if not ms_path.is_file():
        print(f"  ERROR: 台账不存在: {MILESTONES_REL} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    text = ms_path.read_text(encoding="utf-8")
    rows = flow_rows(text)
    if not rows:
        print("  ERROR: `## 任务流水` 小节无数据行 ⇒ vacuous FAIL")
        print("结果: FAIL (1 项)")
        return 1
    print(f"  流水行（现场统计）: {len(rows)}")

    index = task_index(root)
    if not index:
        print("  ERROR: `.tao/tasks/**` 与 `.tao/archive/**` 均无任务书 ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1

    # 只有 `t` 册（普通任务）必须在流水；`k`/`m` 是启动/里程碑册，按「所列任务号」核
    todo_books = {i: p for i, p in index.items()
                  if TASKS_REL.as_posix() in p.as_posix() and i.endswith("t")}
    print(f"  任务书索引（现场统计）: 活册 {len(todo_books)} / 含归档 {len(index)}")

    # ---------- 逐行：格式 + 长度 + 状态 ----------
    seen: dict[str, int] = {}
    parsed: list[tuple[int, str, datetime, str]] = []
    for lineno, raw, cells in rows:
        if len(cells) != 4:
            errors.append(f"L{lineno}: 表格须 4 格，实得 {len(cells)} 格（或含内嵌 `|`）")
            print(f"  L{lineno} FAIL 格式: {len(cells)} 格")
            continue
        tid, status, tcell, summary = cells
        if not ROW_ID_RE.match(tid):
            errors.append(f"L{lineno}: 编号 `{tid}` 不合 `<PREFIX>-nnn<suffix>`")
        if tid in seen:
            errors.append(f"L{lineno}: 编号 `{tid}` 重复（首次 L{seen[tid]}）")
        seen[tid] = lineno
        if status not in STATUSES:
            errors.append(f"L{lineno} {tid}: 状态 `{status}` 不在 {STATUSES}")
        got = parse_time(tcell)
        if got is None:
            errors.append(f"L{lineno} {tid}: 时间 `{tcell}` 须为 `YYYY-MM-DD HH:MM`"
                          f"{'' if status == FINAL else ' + `（登记）`'}")
            continue
        dt, registered = got
        if status == FINAL and registered:
            errors.append(f"L{lineno} {tid}: `已验证` 不得带 `（登记）`"
                          f"（完成时间须为落地时间）")
        if status != FINAL and not registered:
            errors.append(f"L{lineno} {tid}: 未完成任务时间须加注 `（登记）`")
        if len(summary) > MAX_SUMMARY:
            errors.append(f"L{lineno} {tid}: 一句改动 {len(summary)} 字符 > {MAX_SUMMARY}")
        if ".work/" in summary:
            errors.append(f"L{lineno} {tid}: 一句改动含 `.work/` 路径（细节归任务书）")
        if "\n" in summary or not summary:
            errors.append(f"L{lineno} {tid}: 一句改动为空或跨行")
        parsed.append((lineno, tid, dt, status))

    # ---------- A1 状态一致 ----------
    print("-" * 72)
    print("  A1 状态一致（表行 == 任务书 `**状态**`）")
    for lineno, tid, _dt, status in parsed:
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
    print(f"    A1 核验 {len(parsed)} 行")

    # ---------- A2 覆盖 ----------
    print("-" * 72)
    print("  A2 覆盖（活册 / m 册列号 / 正文号 ⇒ 必须在流水）")
    table_ids = {tid for _l, tid, _d, _s in parsed}
    for tid, p in sorted(todo_books.items()):
        if tid not in table_ids:
            errors.append(f"覆盖: 活任务册 {tid} 未列入流水（{p.relative_to(root)}）")
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
                errors.append(f"覆盖: `{p.name}` 列出的 {tid} 未列入流水")
    body = re.sub(r"(?ms)^\|.*?$", "", text)  # 去表行后扫正文
    for tid in sorted(set(TASK_ID_RE.findall(body))):
        if tid in table_ids:
            continue
        p = index.get(tid)
        if p is None:
            errors.append(f"覆盖: 正文任务号 {tid} 全仓无册（悬空号）")
        elif ARCHIVE_REL.as_posix() not in p.as_posix():
            errors.append(f"覆盖: 正文任务号 {tid} 未列入流水（{p.relative_to(root)}）")
    print(f"    活册 {len(todo_books)} 份 / m 册 {len(m_books)} 份（源 = {m_books_src}） / 流水 {len(table_ids)} 行")

    # ---------- A4 次序 ----------
    print("-" * 72)
    print("  A4 次序（时间倒序；同一时间按编号升序）")
    for (pl, pt, pd, _ps), (cl, ct, cd, _cs) in zip(parsed, parsed[1:]):
        if pd > cd or (pd == cd and pt < ct):
            continue
        errors.append(f"次序: L{cl} {ct}（{cd:%Y-%m-%d %H:%M}）应排在 "
                      f"L{pl} {pt}（{pd:%Y-%m-%d %H:%M}）之前")
        print(f"    L{pl} {pt} → L{cl} {ct} 逆序")
    print(f"    相邻对 {max(0, len(parsed) - 1)} 个（现场统计）")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print(f"结果: PASS ({len(parsed)} 行；状态一致 / 覆盖 / ≤{MAX_SUMMARY} 字符 / 倒序 / 格式)")
    return 0


# --------------------------------------------------------------------------
# self-test：临时树 + 五类注入（各自可达 FAIL）
# --------------------------------------------------------------------------
BASE_MS = """# 项目里程碑

## 任务流水

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| SPEC-101t | 已验证 | 2026-10-02 10:00 | 第二新：完成，短句 |
| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |
| QEMU-103t | 待开始 | 2026-10-01 09:00（登记） | 未完成：同时间按编号 |
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

    def case(name: str, ms: str, books: dict[str, str], marker: str) -> None:
        nonlocal ok
        with tempfile.TemporaryDirectory(prefix="milestones-fresh-") as td:
            root = Path(td)
            write_tree(root, ms, books)
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

    case("注入① 状态不一致", BASE_MS.replace("| INFRA-102t | 待验收 |",
                                          "| INFRA-102t | 已验证 |"), BOOKS, "MISMATCH")
    case("注入② 覆盖缺失（活册未列）", BASE_MS.replace(
        "| QEMU-103t | 待开始 | 2026-10-01 09:00（登记） | 未完成：同时间按编号 |\n", ""),
        BOOKS, "未列入流水")
    case("注入③ 一句改动超长", BASE_MS.replace(
        "第二新：完成，短句", "长" * 121), BOOKS, "> 120")
    case("注入④ 次序颠倒", BASE_MS.replace(
        "| SPEC-101t | 已验证 | 2026-10-02 10:00 | 第二新：完成，短句 |\n"
        "| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |",
        "| INFRA-102t | 待验收 | 2026-10-01 09:00（登记） | 未完成：带登记注 |\n"
        "| SPEC-101t | 已验证 | 2026-10-02 10:00 | 第二新：完成，短句 |"),
        BOOKS, "逆序")
    case("注入⑤ 格式（已验证带登记）", BASE_MS.replace(
        "| SPEC-101t | 已验证 | 2026-10-02 10:00 |",
        "| SPEC-101t | 已验证 | 2026-10-02 10:00（登记） |"), BOOKS, "不得带")

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
