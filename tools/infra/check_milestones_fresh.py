#!/usr/bin/env python3
"""check-milestones-fresh: 里程碑台账三表门控（待开始 / 进行中 / 已验证；L1）。

用户 2026-11-08 授权（逐字）：
  「milestones：把待开始的列表放在任务流水前面，或者分为三类，第一类待开始，第二类
    进行中，第三类已验证；前两类，写一个预估时间；第三类，写完成时间；状态这一栏
    可以删除」
  ⇒ 三分表、待开始置前、前两类写**预估时间**、第三类写**完成时间**、**删除状态列**。

用户 2026-11-08 追加授权（逐字，INFRA-143t）：
  「这个问题的关键不是引入新状态，而是派单后，应该把对应任务移动到第二类表格中，
    第二类表格应该增加：派单时间」
  ⇒ **不引入新状态**：**派单即**把该行移入「进行中」表并填**派单时间**
    （`YYYY-MM-DD HH:MM`）；「待开始」表 = 尚未派单。

沿革（用户 2026-10-18 原话，逐字）：
  「milestones.md中的任务流水表格又乱了，这个表格换成列表，而且按时间序，未完成
    的任务也需要列上；这个要求明确写到文档里，不要再乱了；另外，该文档后面的信息
    应按时更新；最后的历史台账指针没用，删除」

体例硬约束（三分表 + 派单时间后）：
  1. 三个二级标题**必须都存在**（顺序：待开始 → 进行中 → 已验证）：
     `## 待开始（未开工）`、
     `## 进行中（已派单：待开始 / 待验收 / 待返工）`、`## 已验证`。
  2. 待开始表列 = `| 编号 | 预估时间 | 一句改动 |`；进行中表列 =
     `| 编号 | 派单时间 | 预估时间 | 一句改动 |`；已验证表列 =
     `| 编号 | 完成时间 | 一句改动 |`。**无状态列**——表位置即状态。
  3. 派单时间 / 完成时间格式 `YYYY-MM-DD HH:MM`（完成时间**不得带 `（登记）`**）；
     预估时间格式 `N h` / `N–M h` / `N 天` / `N–M 天`（亦允许 `min`）。
  4. 三表「一句改动」均 ≤120 字符，且不得含 `.work/<具体路径>`；细节写各任务书。
  5. 表位置映射（**可判定性**：`待开始` 册可出现在前两表任一）：
     待开始表 ⇒ 任务书 `待开始`（未派单）；
     进行中表 ⇒ 任务书 ∈ {`待开始`（已派单、实现中）, `待验收`, `待返工`}
     **且派单时间必填**；已验证表 ⇒ 任务书 `已验证`。

六断言（每条均有可达 FAIL，见 `--self-test`：十四类注入 + A6 双台账八类 + R1 六类）：
  A1 **分类一致**：表行所属表 == 任务书 `**状态**` 的映射（见上）；不一致 ⇒ FAIL。
  A2 **覆盖**：三表并集覆盖 `.tao/tasks/**` 的每份任务书、`INTEG-*m` 册列出的任务号、
     `milestones.md` 正文出现的任务号；**已归档**任务号（`.tao/archive/**` 有册）豁免，
     正文出现但全仓无册的任务号 ⇒ FAIL（悬空号）。
  A3 **长度**：三表每行「一句改动」≤ 120 字符（中文按 1 字符计）。
  A4 **次序**：**只对已验证表**按完成时间**倒序**（同一时间按编号升序）；前两表不判。
  A5 **格式**：待开始 / 已验证表各恰好 3 格，进行中表恰好 4 格；三表须按
     `待开始 → 进行中 → 已验证` 排列；待开始表**不得含派单时间**（未派单）；
     进行中表派单时间 `YYYY-MM-DD HH:MM` + 预估格式；已验证表时间列 =
     `YYYY-MM-DD HH:MM` 且不带 `（登记）`；**任何表不得出现状态列/状态值**；
     同一编号不重复、且不得跨表重复；「一句改动」不得含 `.work/`。

A6 **台账路由（双台账；用户 2026-11-08「milestones.md 改为 milestones-m12.md」）**：
   每份台账取其头部 `项目里程碑 = M<n>` 断言（缺失 ⇒ FAIL）；`.tao/knowledge/milestones*.md`
   按断言各自拥有该号（`milestones.md` 另兜底 ≤ 自身号的历史号）。任务号按**任务书
   `**项目里程碑**` 字段**（无活册的新格式号按 `mNN-` 前缀）定所属台账；行/正文号
   落在**非所属**台账 ⇒ FAIL（跨台账错放）。归档册豁免（历史行不迁移）。

R1 **台账一致性（靠规则，不靠记忆；INFRA-145t）**：读 `git worktree list --porcelain`
  与本地分支（`git for-each-ref refs/heads/`；已并入 `master`/`main` 的分支豁免），
  凡任务号匹配 `<PREFIX>-\\d{3}[a-z]?` 或 `mNN-<module>-NNNN` 者（= 有 worktree 或
  未合并分支 ⇒ 在跑；**只核属本台账的号**）：
    - 该任务号**不得**在「待开始」表（逐条指名 `L??`）；
    - 必须在「进行中」表（派单时间格式已由 A5 校验）；若其任务书 `**状态**` 已是
      `已验证`，则必须在「已验证」表；
    - 未列入任何表 ⇒ FAIL。非 git 树（`--root` 自检树）⇒ 打印跳过。

fail-closed：任一标题/表头/分隔行缺失、三表皆空 ⇒ FAIL。
不依赖 `.work/**`（易失）；只读仓库内文件。

Usage:
    python3 tools/infra/check_milestones_fresh.py [--file PATH] [--root DIR] [--self-test]
       `--file` 默认 `.tao/knowledge/milestones.md`；`--root` 下按同一相对路径解析。
Exit code: 0 = PASS；1 = FAIL。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MILESTONES_REL = Path(".tao/knowledge/milestones.md")
MILESTONES_M12_REL = Path(".tao/knowledge/milestones-m12.md")
KNOWLEDGE_REL = Path(".tao/knowledge")
LEDGER_GLOB = "milestones*.md"
TASKS_REL = Path(".tao/tasks")
ARCHIVE_REL = Path(".tao/archive")
INTEG_M_GLOB = "INTEG-*m-*.md"

TODO_HEADING = "## 待开始（未开工）"
WIP_HEADING = "## 进行中（已派单：待开始 / 待验收 / 待返工）"
DONE_HEADING = "## 已验证"

TODO_HEADER = ("编号", "预估时间", "一句改动")
WIP_HEADER = ("编号", "派单时间", "预估时间", "一句改动")
DONE_HEADER = ("编号", "完成时间", "一句改动")

# `待开始` 可出现在前两表任一：表位置区分「未派单 / 已派单」（不引入新状态）。
TODO_STATUSES = ("待开始",)
WIP_STATUSES = ("待开始", "待验收", "待返工")
DONE_STATUSES = ("已验证",)

# (标题, 表头, 允许的任务书状态, 表种类)
TABLES = (
    (TODO_HEADING, TODO_HEADER, TODO_STATUSES, "todo"),
    (WIP_HEADING, WIP_HEADER, WIP_STATUSES, "wip"),
    (DONE_HEADING, DONE_HEADER, DONE_STATUSES, "done"),
)

CELL_NAMES = {"todo": TODO_HEADER, "wip": WIP_HEADER, "done": DONE_HEADER}

# 表位置即状态：任何表都不得再出现这些值作为独立单元格（状态列）。
STATUS_VALUES = ("待开始", "待验收", "待返工", "已验证")

MAX_SUMMARY = 120

# 旧格式（M11 及以前）：`<PREFIX>-nnn<suffix>`；新格式（M12 起，用户 2026-11-08）：
# `<mNN>-<module>-<NNNN>`（无 k/t/m 后缀）。两种并存，旧编号不迁移。
_OLD_ID = r"(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?"
_NEW_ID = r"m\d{2}-[a-z][a-z0-9]*-\d{3,4}"
TASK_ID_RE = re.compile(rf"\b(?:{_OLD_ID}|{_NEW_ID})\b")
ROW_ID_RE = re.compile(rf"^(?:{_OLD_ID}|{_NEW_ID})$")
TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})(（登记）)?$")
DISPATCH_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})$")
EST_RE = re.compile(r"^\d+(?:\.\d+)?(?:–\d+(?:\.\d+)?)?\s*(?:h|天|min)$")
STATUS_RE = re.compile(r"^\*\*状态\*\*[：:]\s*([^\s*]+)", re.MULTILINE)
TASK_FILE_RE = re.compile(
    rf"^((?:{_OLD_ID}|{_NEW_ID}))-.*\.md$")

# 台账路由（A6）：任务书头 `**项目里程碑**：M12` 与台账头 `项目里程碑 = M12` 断言。
MILESTONE_FIELD_RE = re.compile(r"^\*\*项目里程碑\*\*[：:]\s*M(\d+)\b", re.MULTILINE)
LEDGER_ASSERT_RE = re.compile(r"项目里程碑\s*=\s*M(\d+)\b")
NEW_PREFIX_RE = re.compile(r"^m(\d{2})-")


def book_milestone(path: Path) -> int | None:
    """任务书 `**项目里程碑**` 字段 → 里程碑号（`M12` ⇒ 12）。

    兼容归档册的尾注（`M9（用户 2026-10-24 裁定…）`）；字段缺失 ⇒ None。
    """
    m = MILESTONE_FIELD_RE.search(path.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def ledger_milestone(path: Path) -> int | None:
    """台账头 `项目里程碑 = M<n>` 断言 → 里程碑号；缺失 ⇒ None（调用方 fail-closed）。"""
    if not path.is_file():
        return None
    m = LEDGER_ASSERT_RE.search(path.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def id_milestone(tid: str) -> int | None:
    """新格式号的里程碑前缀（`m12-infra-001` ⇒ 12）；旧格式 ⇒ None。"""
    m = NEW_PREFIX_RE.match(tid)
    return int(m.group(1)) if m else None


def _file_task_id(path: Path) -> str:
    """任务书文件名 → 任务号（不匹配 ⇒ 空串）。"""
    m = TASK_FILE_RE.match(path.name)
    return m.group(1) if m else ""


def tid_milestone(tid: str, index: dict[str, Path]) -> int | None:
    """任务号 → 里程碑号：活册 `**项目里程碑**` 字段优先，其次新格式 `mNN-` 前缀。"""
    p = index.get(tid)
    if p is not None:
        n = book_milestone(p)
        if n is not None:
            return n
    return id_milestone(tid)


def ledger_owners(root: Path) -> dict[int, Path]:
    """里程碑号 → 台账路径（现场扫描 `.tao/knowledge/milestones*.md` 的断言）。"""
    owners: dict[int, Path] = {}
    kdir = root / KNOWLEDGE_REL
    if not kdir.is_dir():
        return owners
    for p in sorted(kdir.glob(LEDGER_GLOB)):
        n = ledger_milestone(p)
        if n is not None:
            owners.setdefault(n, p.resolve())
    return owners


def home_ledger(root: Path, ms: int | None, owners: dict[int, Path]) -> Path | None:
    """任务号所属台账：`M<n>` 自有台账；`≤ milestones.md 断言号` 归历史台账；其余无主。"""
    if ms is None:
        return None
    if ms in owners:
        return owners[ms]
    legacy = (root / MILESTONES_REL).resolve()
    legacy_ms = ledger_milestone(legacy)
    if legacy_ms is not None and ms <= legacy_ms:
        return legacy
    return None


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


# 任务号（分支名/worktree 分支须**整串**匹配，避免 `INFRA-145t-fix` 之类误命中）
BRANCH_TASK_RE = re.compile(rf"^(?:{_OLD_ID}|{_NEW_ID})$")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None


def running_tasks(root: Path) -> tuple[dict[str, str], str]:
    """在跑任务号 → 来源（`worktree` / `branch`）；非 git 树 ⇒ 空集。

    「在跑」= `git worktree list` 里检出的任务分支，或**未合并**的本地任务分支
    （已并入 `master`/`main` 的分支 = 已落地，豁免；分支未删不应把已验证任务拉回
    进行中）。用 `--root` 指向自检树（无 git）时返回空集并注明跳过。
    """
    probe = _git(root, "rev-parse", "--git-dir")
    if probe is None:
        return {}, "git 不可用 ⇒ R1 跳过"
    if probe.returncode != 0:
        return {}, "非 git 仓库（--root 自检树）⇒ R1 跳过"

    found: dict[str, str] = {}
    wt = _git(root, "worktree", "list", "--porcelain")
    if wt is not None and wt.returncode == 0:
        for line in wt.stdout.splitlines():
            if line.startswith("branch refs/heads/"):
                name = line[len("branch refs/heads/"):]
                if BRANCH_TASK_RE.match(name):
                    found.setdefault(name, "worktree")

    refs = _git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    all_branches = refs.stdout.split() if refs is not None and refs.returncode == 0 else []
    base = None
    for cand in ("master", "main"):
        r = _git(root, "rev-parse", "--verify", "-q", f"refs/heads/{cand}")
        if r is not None and r.returncode == 0:
            base = cand
            break
    if base is None:
        base = next((b for b in all_branches if not BRANCH_TASK_RE.match(b)), None)
    for b in all_branches:
        if not BRANCH_TASK_RE.match(b) or b in found:
            continue
        merged = False
        if base is not None:
            mb = _git(root, "merge-base", "--is-ancestor",
                      f"refs/heads/{b}", f"refs/heads/{base}")
            merged = mb is not None and mb.returncode == 0
        if not merged:
            found[b] = "branch"
    return found, f"R1 在跑任务号（worktree/未合并分支，现场统计）: {len(found)} 个"


def check_running_consistency(
    running: dict[str, str],
    seen: dict[str, tuple[str, int]],
    index: dict[str, Path],
    errors: list[str],
) -> None:
    """R1：在跑任务号 ⇒ 不得在「待开始」；在「进行中」（或已验证表，若册已`已验证`）。"""
    for tid in sorted(running):
        src = "worktree" if running[tid] == "worktree" else "未合并分支"
        loc = seen.get(tid)
        heading, lineno = loc if loc else ("", 0)
        if loc and heading == TODO_HEADING:
            errors.append(f"R1: `{TODO_HEADING}` L{lineno} {tid}: 有 {src} 但台账在「待开始」"
                          f"（派单即须移入「进行中」并填派单时间）")
        elif loc and heading == WIP_HEADING:
            pass  # 派单时间格式由 A5 校验
        elif loc and heading == DONE_HEADING:
            pass  # 册状态一致性由 A1 校验
        else:
            errors.append(f"R1: {tid}: 有 {src} 但未列入「进行中」/「已验证」表")
        p = index.get(tid)
        bs = book_status(p) if p else None
        if bs == "已验证" and not (loc and heading == DONE_HEADING):
            where = f"`{heading}` L{lineno}" if loc else "三表之外"
            errors.append(f"R1: {tid}: 任务书 `**状态**` 已 `已验证`，但台账在 {where}"
                          f"（须在「已验证」表）")


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
            problems.append("不得出现状态列（表位置即状态）")
        if header is TODO_HEADER and any("派单时间" in c for c in got_header):
            problems.append("「待开始」表不得有派单时间列（未派单任务）")
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


def parse_dispatch(cell: str) -> datetime | None:
    m = DISPATCH_RE.match(cell)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def check_rows(
    heading: str,
    rows: list[tuple[int, str, list[str]]],
    kind: str,
    errors: list[str],
    seen: dict[str, tuple[str, int]],
) -> list[tuple[int, str, datetime | None]]:
    """逐行格式 / 长度 / 状态列 / 重复检查；返回 `(行号, 编号, 完成时间|None)`。"""
    parsed: list[tuple[int, str, datetime | None]] = []
    width = 4 if kind == "wip" else 3
    for lineno, _raw, cells in rows:
        if len(cells) != width:
            hint = ""
            if kind == "wip" and len(cells) == 3:
                hint = "（缺派单时间：进行中行必须填 `YYYY-MM-DD HH:MM`）"
            elif kind == "todo" and len(cells) == 4:
                hint = "（「待开始」表行不得含派单时间：派单后须移入进行中表）"
            errors.append(f"`{heading}` L{lineno}: 行须恰好 {width} 格"
                          f"（`| {' | '.join(CELL_NAMES[kind])} |`；或含内嵌 `|`），"
                          f"实得 {len(cells)} 格{hint}")
            continue
        if kind == "wip":
            tid, dcell, tcell, summary = cells
        else:
            tid, tcell, summary = cells
            dcell = None
        if not ROW_ID_RE.match(tid):
            errors.append(f"`{heading}` L{lineno}: 编号 `{tid}` 不合"
                          f"`<PREFIX>-nnn<suffix>` / `mNN-<module>-NNNN`")
        if tid in seen:
            prev_h, prev_l = seen[tid]
            kind_word = "同表重复" if prev_h == heading else "跨表重复"
            errors.append(f"`{heading}` L{lineno}: 编号 `{tid}` {kind_word}"
                          f"（首次 `{prev_h}` L{prev_l}）")
        else:
            seen[tid] = (heading, lineno)
        bad = [c for c in cells if c in STATUS_VALUES]
        if bad:
            errors.append(f"`{heading}` L{lineno}: 表内不得出现状态值/状态列 {bad}（表位置即状态）")
        if kind == "wip":
            if parse_dispatch(dcell) is None:
                errors.append(f"`{heading}` L{lineno} {tid}: 派单时间 `{dcell}`"
                              f"须为 `YYYY-MM-DD HH:MM`")
        if kind in ("todo", "wip"):
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


def audit(root: Path, ledger_rel: Path = MILESTONES_REL) -> int:
    print("=" * 72)
    print(f"check-milestones-fresh — 待开始 / 进行中 / 已验证（L1）；台账 = {ledger_rel}")
    print("=" * 72)
    errors: list[str] = []

    ms_path = root / ledger_rel
    if not ms_path.is_file():
        print(f"  ERROR: 台账不存在: {ledger_rel} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    text = ms_path.read_text(encoding="utf-8")

    me = ledger_milestone(ms_path)
    if me is None:
        print(f"  ERROR: 台账缺 `项目里程碑 = M<n>` 断言（A6 路由依据）"
              f": {ledger_rel} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    owners = ledger_owners(root)
    mine = ms_path.resolve()

    def owned(ms: int | None) -> bool:
        return home_ledger(root, ms, owners) == mine

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
        # 归档边界（Process-04 §4.1）：里程碑已归档 ⇒ 活台账允许为空。
        lm = ledger_milestone(root / ledger_rel)
        archived = lm is not None and (root / ".tao" / "archive" / f"M{lm}" / "README.md").is_file()
        if archived:
            print(f"  NOTE: M{lm} 已归档（.tao/archive/M{lm}/）⇒ 活台账三表允许为空")
        else:
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

    # 只有 `t` 册（普通任务）与新格式 `mNN-<module>-NNNN` 册必须在表；`k`/`m` 是
    # 启动/里程碑册，按「所列任务号」核。本台账只收**所属**任务号（A6 路由）。
    live = {i: p for i, p in index.items() if TASKS_REL.as_posix() in p.as_posix()}
    task_books = {i: p for i, p in live.items()
                  if i.endswith("t") or NEW_PREFIX_RE.match(i)}
    for tid, p in sorted(task_books.items()):
        if book_milestone(p) is None:
            errors.append(f"A6: 活任务册 {tid} 无头部 `**项目里程碑**` 字段"
                          f"（{p.relative_to(root)}；台账路由依据）")
    todo_books = {i: p for i, p in task_books.items() if owned(book_milestone(p))}
    print(f"  任务书索引（现场统计）: 属本台账活任务册 {len(todo_books)}"
          f" / 活任务册 {len(task_books)} / 含归档 {len(index)}")

    # ---------- A5 格式 + A3 长度（三表逐行） ----------
    seen: dict[str, tuple[str, int]] = {}
    parsed: dict[str, list[tuple[int, str, datetime | None]]] = {}
    for heading, _header, _statuses, kind in TABLES:
        parsed[heading] = check_rows(heading, sections[heading], kind, errors, seen)

    # ---------- A1 分类一致 ----------
    print("-" * 72)
    print("  A1 分类一致（表位置 == 任务书 `**状态**` 映射）")
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
                errors.append(f"A1: `{heading}` L{lineno} {tid}: MISMATCH 表={heading}"
                              f"（允许 {list(statuses)}）册={bs}（{p.relative_to(root)}）")
    print(f"    A1 核验 " + " + ".join(
        f"{heading[3:]} {len(parsed[heading])} 行" for heading, _h, _s, _k in TABLES))

    # ---------- A6 台账路由（行号所属台账 == 本台账） ----------
    print("-" * 72)
    print("  A6 台账路由（行所属里程碑台账 == 本台账；归档册豁免）")
    routed = 0
    for heading, _header, _statuses, _kind in TABLES:
        for lineno, tid, _dt in parsed[heading]:
            p = index.get(tid)
            if p is None or ARCHIVE_REL.as_posix() in p.as_posix():
                continue
            ms = tid_milestone(tid, index)
            home = home_ledger(root, ms, owners)
            routed += 1
            if home != mine:
                where = home.relative_to(root).as_posix() if home else "无台账（该里程碑未建）"
                ms_label = f"M{ms}" if ms is not None else "?"
                errors.append(f"A6: `{heading}` L{lineno} {tid}: 册 `**项目里程碑**` = "
                              f"{ms_label}，所属台账 `{where}` ≠ 本台账 `{ledger_rel.as_posix()}`"
                              f"（跨台账错放）")
    print(f"    A6 逐条核验 {routed} 个活册行（归档册豁免）")

    # ---------- R1 台账一致性（worktree / 未合并分支 ⇒ 进行中） ----------
    print("-" * 72)
    print("  R1 台账一致性（在跑任务号不得在「待开始」；须在「进行中」/「已验证」）")
    running_all, note = running_tasks(root)
    running = {t: s for t, s in running_all.items() if owned(tid_milestone(t, index))}
    print(f"    {note}")
    print(f"    属本台账在跑 {len(running)} 个 / 在跑合计 {len(running_all)} 个（异台账略过）")
    check_running_consistency(running, seen, index, errors)
    print(f"    R1 逐条核验 {len(running)} 个在跑任务号")

    # ---------- A2 覆盖 ----------
    print("-" * 72)
    print("  A2 覆盖（三表并集 ⊇ 本台账活册 / 本台账 m 册列号 / 正文号）")
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
    m_books = [p for p in m_books if owned(tid_milestone(_file_task_id(p), index))]
    for p in m_books:
        for tid in sorted(set(TASK_ID_RE.findall(p.read_text(encoding="utf-8")))):
            if tid not in table_ids and not (ARCHIVE_REL.as_posix() in index.get(tid, Path()).as_posix()):
                errors.append(f"覆盖: `{p.name}` 列出的 {tid} 未列入台账三表")
    body = re.sub(r"(?ms)^\|.*?$", "", text)  # 去表行后扫正文
    for tid in sorted(set(TASK_ID_RE.findall(body))):
        if tid in table_ids:
            continue
        p = index.get(tid)
        home = home_ledger(root, tid_milestone(tid, index), owners)
        if home is None and p is None and id_milestone(tid) is None:
            home = (root / MILESTONES_REL).resolve()  # 旧格式悬空号归历史台账
        if home != mine:
            continue
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
# self-test：临时树 + 十四类注入（各自可达 FAIL）
# --------------------------------------------------------------------------
BASE_MS = """# 项目里程碑

> **项目里程碑 = M11**

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| QEMU-103t | 1 h | 未开工：待开始表 |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| INFRA-102t | 2026-10-01 08:00 | 2–3 h | 待验收：进行中短句 |
| QEMU-105t | 2026-10-02 09:00 | 1 h | 待开始：已派单实现中 |

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
    "QEMU-105t": "**状态**：待开始\n",
}


def write_tree(root: Path, ms: str, books: dict[str, str],
               m_body: str = "列出 `SPEC-101t` / `INFRA-102t`。",
               ledger: str | None = None) -> None:
    (root / ".tao/knowledge").mkdir(parents=True, exist_ok=True)
    for mod in ("infra", "spec", "qemu", "integ", "testcases"):
        (root / ".tao/tasks" / mod).mkdir(parents=True, exist_ok=True)
    (root / MILESTONES_REL).write_text(ms, encoding="utf-8")
    if ledger is not None:
        (root / MILESTONES_M12_REL).write_text(ledger, encoding="utf-8")
    mod_of = {"SPEC": "spec", "INFRA": "infra", "QEMU": "qemu",
              "TESTCASES": "testcases"}
    for tid, body in books.items():
        mod = mod_of.get(tid.split("-")[0]) or tid.split("-")[1]
        (root / ".tao/tasks" / mod / f"{tid}-x.md").write_text(
            f"# {tid}\n\n{book_milestone_field(tid)}\n{body}\n", encoding="utf-8")
    (root / ".tao/tasks/integ/INTEG-900m-x.md").write_text(
        f"**项目里程碑**：M11\n**状态**：待开始\n\n{m_body}\n", encoding="utf-8")


def book_milestone_field(tid: str) -> str:
    """任务书头的 `**项目里程碑**` 字段（新格式取 `mNN` 前缀，旧格式默认 M11）。"""
    n = id_milestone(tid)
    return f"**项目里程碑**：M{n if n is not None else 11}"


def _run(root: Path, ledger: Path = MILESTONES_REL) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit(root, ledger)
    return rc, buf.getvalue()


def _swap_done_first(ms: str) -> str:
    """把「已验证」节移到最前（三表次序反例）。"""
    head, *sections = ms.split("\n## ")
    done_idx = next(i for i, s in enumerate(sections) if s.startswith(DONE_HEADING[3:]))
    done = sections.pop(done_idx)
    return head + "\n## " + done + "".join("\n## " + s for s in sections)


# --------------------------------------------------------------------------
# R1 self-test：真 git 临时仓库 + worktree / 未合并分支 / 已合并分支
# --------------------------------------------------------------------------
R1_MS = """# 项目里程碑

> **项目里程碑 = M11**

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
{todo}

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
{wip}

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
{done}
"""


def _r1_ms(todo: str = "", wip: str = "", done: str = "") -> str:
    return R1_MS.format(todo=todo, wip=wip, done=done)


def _git_run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_git(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for args in (("init", "-q"), ("symbolic-ref", "HEAD", "refs/heads/master"),
                 ("-c", "user.email=selftest@example.invalid",
                  "-c", "user.name=selftest", "commit", "-q", "--allow-empty",
                  "-m", "init")):
        p = _git_run(root, *args)
        if p.returncode != 0:
            raise RuntimeError(f"git {args[0]} 失败: {p.stderr.strip()}")


def r1_self_test() -> bool:
    ok = True

    def case(name: str, ms: str, books: dict[str, str], setup, want_rc: int,
             marker: str) -> None:
        nonlocal ok
        with tempfile.TemporaryDirectory(prefix="milestones-r1-") as td:
            base = Path(td)
            repo = base / "repo"
            _init_git(repo)
            write_tree(repo, ms, books, m_body="列出 `SPEC-101t`。")
            _git_run(repo, "add", "-A")
            _git_run(repo, "commit", "-q", "-m", "ledger")
            setup(repo, base)
            rc, out = _run(repo)
        good = rc == want_rc and marker in out
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: rc={rc} 期望 {want_rc}"
              f" marker={marker!r}")

    spec_done = "| SPEC-101t | 2026-10-02 10:00 | 完成短句 |"
    wip_row = "| TESTCASES-901t | 2026-11-08 10:00 | 1 h | 已派单实现中 |"
    todo_row = "| TESTCASES-901t | 1 h | 在跑却留待开始 |"
    book_open = {"TESTCASES-901t": "**状态**：待开始\n",
                 "SPEC-101t": "**状态**：已验证\n"}
    book_done = {"TESTCASES-901t": "**状态**：已验证\n",
                 "SPEC-101t": "**状态**：已验证\n"}

    def wt(tid: str):
        def setup(repo: Path, base: Path) -> None:
            _git_run(repo, "worktree", "add", "-q", "-b", tid, str(base / f"wt-{tid}"))
        return setup

    def branch(tid: str):
        """仅本地分支、无 worktree，且**未合并**（在 master 之上多一个提交）。"""
        def setup(repo: Path, base: Path) -> None:
            _git_run(repo, "branch", tid)
            tree = _git_run(repo, "write-tree").stdout.strip()
            commit = _git_run(repo, "-c", "user.email=selftest@example.invalid",
                              "-c", "user.name=selftest", "commit-tree", tree,
                              "-p", "master", "-m", "advance").stdout.strip()
            _git_run(repo, "update-ref", f"refs/heads/{tid}", commit)
        return setup

    def merged(tid: str):
        def setup(repo: Path, base: Path) -> None:
            _git_run(repo, "branch", tid, "master")
        return setup

    case("R1 注入① worktree 在跑却留「待开始」⇒ FAIL 指名",
         _r1_ms(todo=todo_row, done=spec_done), book_open, wt("TESTCASES-901t"),
         1, "有 worktree 但台账在「待开始」")
    case("R1 基线① worktree 在跑且已移入「进行中」⇒ PASS",
         _r1_ms(wip=wip_row, done=spec_done), book_open, wt("TESTCASES-901t"),
         0, "R1 在跑任务号")
    case("R1 注入② 仅未合并本地分支却留「待开始」⇒ FAIL 指名",
         _r1_ms(todo=todo_row, done=spec_done), book_open, branch("TESTCASES-901t"),
         1, "有 未合并分支 但台账在「待开始」")
    case("R1 基线② 已并入 master 的分支 ⇒ 豁免（已验证行 PASS）",
         _r1_ms(done="| QEMU-903t | 2026-10-03 10:00 | 合并后已删 |\n" + spec_done),
         {"QEMU-903t": "**状态**：已验证\n", "SPEC-101t": "**状态**：已验证\n"},
         merged("QEMU-903t"), 0, "R1 在跑任务号")
    case("R1 注入③ 册已 `已验证` 但行留「进行中」⇒ FAIL",
         _r1_ms(wip=wip_row, done=spec_done), book_done, wt("TESTCASES-901t"),
         1, "任务书 `**状态**` 已 `已验证`")
    case("R1 基线③ 册已 `已验证` 且在「已验证」表 ⇒ PASS",
         _r1_ms(done="| TESTCASES-901t | 2026-10-03 10:00 | 完成短句 |\n" + spec_done),
         book_done, wt("TESTCASES-901t"), 0, "R1 在跑任务号")
    return ok


def self_test() -> int:
    print("=" * 72)
    print("check-milestones-fresh --self-test（十四类注入 + A6 双台账八类 + R1 六类，各自可达 FAIL）")
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

    wip_row = "| INFRA-102t | 2026-10-01 08:00 | 2–3 h | 待验收：进行中短句 |"
    case("注入① 进行中行缺派单时间", BASE_MS.replace(
        wip_row, "| INFRA-102t | 2–3 h | 待验收：进行中短句 |"), "缺派单时间")
    case("注入② 待开始表行带派单时间", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |",
        "| QEMU-103t | 2026-11-01 10:00 | 1 h | 未开工：待开始表 |"),
        "不得含派单时间")
    case("注入③ 派单时间格式非法", BASE_MS.replace(
        wip_row, "| INFRA-102t | 2026/10/01 08:00 | 2–3 h | 待验收：进行中短句 |"),
        "须为 `YYYY-MM-DD HH:MM`")
    case("注入④ 状态映射不符（已验证行留进行中）", BASE_MS.replace(
        "| INFRA-104t | 2026-10-01 09:00 | 更早：完成，短句 |\n", "").replace(
        wip_row, wip_row + "\n| INFRA-104t | 2026-10-03 10:00 | 1 h | 已验证却留进行中 |"),
        "MISMATCH")
    case("注入⑤ 已验证表次序打乱", BASE_MS.replace(
        "| SPEC-101t | 2026-10-02 10:00 | 第二新：完成，短句 |\n"
        "| INFRA-104t | 2026-10-01 09:00 | 更早：完成，短句 |",
        "| INFRA-104t | 2026-10-01 09:00 | 更早：完成，短句 |\n"
        "| SPEC-101t | 2026-10-02 10:00 | 第二新：完成，短句 |"), "逆序")
    case("注入⑥ 预估时间格式非法", BASE_MS.replace(
        "| QEMU-103t | 1 h |", "| QEMU-103t | soon |"), "预估时间")
    case("注入⑦ 完成时间带（登记）", BASE_MS.replace(
        "2026-10-02 10:00 |", "2026-10-02 10:00（登记） |"), "不得带")
    case("注入⑧ 同号跨表重复", BASE_MS.replace(
        wip_row, wip_row + "\n"
        "| QEMU-103t | 2026-10-03 11:00 | 1 h | 重复行 |"), "跨表重复")
    case("注入⑨ 已验证表加回状态列", BASE_MS.replace(
        "| 编号 | 完成时间 | 一句改动 |\n| --- | --- | --- |\n",
        "| 编号 | 状态 | 完成时间 | 一句改动 |\n| --- | --- | --- | --- |\n"), "状态列")
    case("注入⑩ 三表次序打乱（已验证置前）", _swap_done_first(BASE_MS), "三表须按")
    case("注入⑪ 待开始行缺失（覆盖）", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |\n", ""), "未列入台账三表")
    case("注入⑫ 缺「进行中」小节", BASE_MS.replace(
        "\n## 进行中（已派单：待开始 / 待验收 / 待返工）\n", "\n"), "缺小节")
    case("注入⑬ 一句改动超长（A3）", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |",
        "| QEMU-103t | 1 h | " + "长" * 121 + " |"), f"字符 > {MAX_SUMMARY}")
    case("注入⑭ 一句改动含 `.work` 路径", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |",
        "| QEMU-103t | 1 h | 见 .work/log/x |"), "`.work/` 路径")

    print("-" * 72)
    print("  A6 双台账路由（M11 → milestones.md；M12 → milestones-m12.md；跨台账错放 FAIL）")

    def route(name: str, ms11: str, ms12: str | None, books: dict[str, str],
              ledger: Path, want_rc: int, marker: str, mutate=None) -> None:
        nonlocal ok
        with tempfile.TemporaryDirectory(prefix="milestones-route-") as td:
            root = Path(td)
            write_tree(root, ms11, books, ledger=ms12)
            if mutate is not None:
                mutate(root)
            rc, out = _run(root, ledger)
        good = rc == want_rc and marker in out
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: rc={rc} 期望 {want_rc}"
              f" marker={marker!r}")

    M12_MS = """# 项目里程碑

> **项目里程碑 = M12**

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m12-infra-902 | 1 h | M12 待开始行 |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m12-infra-901 | 2026-11-08 21:00 | 1 h | M12 进行中行 |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
"""
    m12_wip = "| m12-infra-901 | 2026-11-08 21:00 | 1 h | M12 进行中行 |"
    m12_book = {**BOOKS, "m12-infra-901": "**状态**：待开始\n",
                "m12-infra-902": "**状态**：待开始\n"}
    route("A6 基线① M11 台账 PASS", BASE_MS, M12_MS, m12_book,
          MILESTONES_REL, 0, "结果: PASS")
    route("A6 基线② M12 台账（--file）PASS", BASE_MS, M12_MS, m12_book,
          MILESTONES_M12_REL, 0, "结果: PASS")
    route("A6 注入① M12 行写进 M11 台账 ⇒ 跨台账 FAIL", BASE_MS.replace(
        wip_row, wip_row + "\n| m12-infra-901 | 2026-11-08 21:00 | 1 h | 错放 M11 |"),
        M12_MS, m12_book, MILESTONES_REL, 1, "跨台账错放")
    route("A6 注入② M11 行写进 M12 台账 ⇒ 跨台账 FAIL", BASE_MS, M12_MS.replace(
        m12_wip, m12_wip + "\n| QEMU-103t | 2026-11-08 21:00 | 1 h | 错放 M12 |"),
        m12_book, MILESTONES_M12_REL, 1, "跨台账错放")
    route("A6 注入③ M12 活册未列入 M12 台账 ⇒ 覆盖 FAIL", BASE_MS, M12_MS.replace(
        m12_wip + "\n", ""), m12_book, MILESTONES_M12_REL, 1, "未列入台账三表")
    route("A6 基线③ M12 台账不存在 ⇒ M12 册不属 M11（跳过、非 vacuous）",
          BASE_MS, None, m12_book, MILESTONES_REL, 0, "结果: PASS")
    route("A6 注入④ 跳过不等于 vacuous：M11 台账坏仍 FAIL", BASE_MS.replace(
        "| QEMU-103t | 1 h | 未开工：待开始表 |\n", ""), None, m12_book,
        MILESTONES_REL, 1, "未列入台账三表")
    route("A6 注入⑤ 活任务册缺 `**项目里程碑**` 字段 ⇒ FAIL", BASE_MS, M12_MS,
          m12_book, MILESTONES_REL, 1, "无头部 `**项目里程碑**` 字段",
          mutate=lambda root: (root / ".tao/tasks/spec/SPEC-101t-x.md").write_text(
              "# SPEC-101t\n\n**状态**：已验证\n", encoding="utf-8"))

    print("-" * 72)
    print("  R1 台账一致性（真 git 临时仓库：worktree / 未合并分支 / 已合并分支）")
    ok &= r1_self_test()

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None, help="检查另一棵树（默认仓库根）")
    ap.add_argument("--file", type=Path, default=MILESTONES_REL,
                    help="台账相对路径（默认 `.tao/knowledge/milestones.md`）")
    ap.add_argument("--self-test", action="store_true", help="跑内置十四类注入自检")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-milestones-fresh: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root, args.file)


if __name__ == "__main__":
    raise SystemExit(main())
