#!/usr/bin/env python3
"""check-archive: ``.tao/archive/M<i>/`` 归档结构 + 任务书字段门控（INFRA-116t）。

规则真源 = ``docs/Process-04-里程碑归档规范.md`` §2/§4/§5/§6/§7/§8。
本门控把「归档目录只允许什么」与「每份册必须是什么态」落为**机械检查**：

  1. **三件套**：``README.md`` / ``m<i>-retrospective.md`` / ``issues-closed.md``
     存在且非空。
  2. **根文件封闭**：只允许三件套 + ``INTEG-*m-*.md`` 核验册（**仅历史归档 M9/M10**
     可置根；新归档放 ``integ/``）。
  3. **子目录封闭**：只允许 6 个模块名（``infra``/``integ``/``llvm``/``qemu``/
     ``spec``/``testcases``）；``notes/`` 等一律 FAIL。
  4. **任务书字段**：模块子目录与根级 ``m`` 册的每份 ``*.md`` 须有 ``**状态**``
     ∈ {``已验证``,``里程碑``}，``**项目里程碑**`` 的里程碑号 == 所在归档号
     （尾随历史括注按编号判定、不计错；**新归档应写裸 ``M<i>``**）。
  5. **任务清单计数**：README §1 的模块计数 == 模块目录实际 ``*.md`` 数（现场统计）。
  6. **任务流水对应**：README 的「任务流水 / changelog / 台账快照」节须有表格；
     编号列格式（M7+）要求流水 ID 集合 == 模块任务书 ID 集合（根级 ``m`` 可入可不入）
     且行状态 == 任务书状态；日期列格式（M1–M6 历史 ``changelog``）只要求表格非空。
  7. **README 必备节**：「MEMORY」节、「指针 / 相关索引」节；M9 起另须「终局证据」。
  8. **issues 快照**：``issues-closed.md`` 须含 ``ISS-<数字>`` 或等价计数表。

设计要点：
  - **计数现场统计、不写死**；
  - **fail-closed**：无 ``M<i>`` 目录 / 无任务书 / 流水表空 ⇒ FAIL；
  - **过渡常量** ``PENDING_117``：仅 ``--pending-ok`` 豁免，默认（严格）命中即 FAIL；
    ``INFRA-117t`` 完成归一后删除该常量与该 flag。

Usage:
    python3 tools/infra/check_archive.py [--pending-ok] [--root DIR] [--self-test]

``--root DIR`` 检查另一棵树（默认仓库根）；``--self-test`` 用临时树跑
「基线 PASS + 注入 FAIL + 过渡边界」自检。

Exit code: 0 = 无违规（严格）/ 仅剩 PENDING_117（过渡）；1 = 有违规。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_REL = Path(".tao") / "archive"

# 模块子目录封闭集合（docs/Process-04 §5）。
MODULES = ("infra", "integ", "llvm", "qemu", "spec", "testcases")
# 归档册终态（docs/Process-04 §4.1）：`已验证` / `里程碑`，精确值、不带括注
# （不做 t/k/m 后缀映射：历史 `INTEG-037m` 记为 `已验证`）。
TERMINAL_STATUS = ("已验证", "里程碑")
# 任务流水节的同义标题（M1–M8 历史归档用 changelog / 台账快照）。
FLOW_ALIASES = ("任务流水", "changelog", "台账快照")
# 根级 INTEG 核验册仅历史归档（M9/M10）可置根；新归档应放 integ/。
ROOT_INTEG_HISTORICAL = frozenset({"M9", "M10"})
# 根级 INTEG 核验册文件名（`INTEG-037m-M9里程碑核验.md` / `INTEG-052m-...`）。
_ROOT_INTEG_RE = re.compile(r"^INTEG-\d+m-.+\.md$")
_TASK_ID_RE = re.compile(r"^([A-Z]+-\d+[a-z])")

# ── 过渡常量（INFRA-116t → INFRA-117t）────────────────────────────────────────
# 这些是**已知、待 117 归一**的缺口；`--pending-ok` 只豁免本表（逐条对账：
# 表内项必须在现场**命中**，否则按 STALE 报红）。117 完成后整表与 flag 删除。
PENDING_117: dict[tuple[str, str, str], str] = {
    ("M2", "task", "TESTCASES-019t"): "状态带括注 `已验证（第 3 轮返工后）`；117 规范化为精确值",
    ("M2", "task", "SPEC-064t"): "状态带括注 `已验证（**…**）`；117 规范化为精确值 + 状态注记",
    ("M7", "dir", "notes"): "`notes/` 补充记录目录；117 并入 `m7-retrospective.md` 附录",
    ("M9", "flow", "§2"): "README 缺「任务流水（冻结）」节；117 从里程碑台账回填",
    ("M9", "memory", "§4"): "README 缺「MEMORY 摘录」节；117 补齐",
    ("M10", "flow", "§2"): "README 缺「任务流水（冻结）」节；117 从里程碑台账回填",
    ("M10", "memory", "§4"): "README 缺「MEMORY 摘录」节；117 补齐",
}


@dataclass(frozen=True)
class Violation:
    """一条违规；key = (里程碑, 类别, 主体)，用于 PENDING_117 逐条对账。"""

    key: tuple[str, str, str]
    message: str


@dataclass
class AuditResult:
    real: list[Violation] = field(default_factory=list)
    pending_hits: list[Violation] = field(default_factory=list)
    stale_pending: list[tuple[str, str, str]] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    per_milestone: list[str] = field(default_factory=list)
    pending_ok: bool = False

    @property
    def ok(self) -> bool:
        # 严格模式：PENDING_117 同样是违规（不豁免）⇒ 非绿。
        return (not self.real and not self.stale_pending
                and (self.pending_ok or not self.pending_hits))


# ── 文本/表格解析 ──────────────────────────────────────────────────────────────
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*)$", re.M)
_SEP_CELL_RE = re.compile(r"^:?-{3,}:?$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _headings(text: str) -> list[tuple[int, int, str, int]]:
    """(start_offset, level, title, end_of_heading_line)。"""
    return [
        (m.start(), len(m.group(1)), m.group(2).strip(), m.end())
        for m in _HEADING_RE.finditer(text)
    ]


def _section_body(text: str, idx: int, heads: list[tuple[int, int, str, int]]) -> str:
    """该标题到下一个同级/更高级标题之间的正文（含更深子节）。"""
    _, level, _, end = heads[idx]
    stop = len(text)
    for j in range(idx + 1, len(heads)):
        if heads[j][1] <= level:
            stop = heads[j][0]
            break
    return text[end:stop]


def _tables(body: str) -> list[list[list[str]]]:
    """解析 markdown 表格（行首 `|` 连续块；第 2 行为分隔行才算表）。"""
    blocks: list[list[str]] = []
    cur: list[str] = []
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("|"):
            cur.append(s)
            continue
        if len(cur) >= 2:
            blocks.append(cur)
        cur = []
    if len(cur) >= 2:
        blocks.append(cur)

    tables: list[list[list[str]]] = []
    for block in blocks:
        rows = [[c.strip() for c in r.strip("|").split("|")] for r in block]
        if len(rows[1]) == 0:
            continue
        if all(_SEP_CELL_RE.match(c.replace(" ", "")) for c in rows[1]):
            tables.append(rows)
    return tables


def _hcell(cell: str) -> str:
    return re.sub(r"[\s*`]", "", cell)


def _field_value(text: str, label: str) -> str | None:
    """`**<label>**：值` 的值（行内下一字段 `**x**：` 之前）；无该字段 ⇒ None。"""
    m = re.search(r"\*\*" + label + r"\*\*\s*[:：][ \t　]*([^\n]*)", text)
    if not m:
        return None
    rest = m.group(1)
    nxt = re.search(r"\*\*[^*\n]+\*\*\s*[:：]", rest)
    if nxt:
        rest = rest[: nxt.start()]
    return rest.strip(" \t　")


def _pm_status(value: str | None, mnum: int) -> tuple[bool, str]:
    """`**项目里程碑**` 判定：里程碑号 == 归档号；尾随历史括注按编号判定。"""
    if value is None:
        return False, "缺 `**项目里程碑**` 字段"
    m = re.match(r"M(\d+)(.*)$", value.strip())
    if not m:
        return False, f"字段不以 `M<n>` 开头: {value!r}"
    if int(m.group(1)) != mnum:
        return False, f"里程碑号 {m.group(1)} != M{mnum}"
    tail = m.group(2).strip()
    if tail and not (tail.startswith("（") or tail.startswith("(")):
        return False, f"尾随非括注内容: {tail!r}"
    return True, tail


# ── 结构检查 ──────────────────────────────────────────────────────────────────
def _module_task_files(mdir: Path, mod: str, add) -> list[Path]:
    d = mdir / mod
    if not d.is_dir():
        return []
    out: list[Path] = []
    for e in sorted(d.iterdir()):
        if e.is_dir():
            add(Violation((mdir.name, "dir", f"{mod}/{e.name}"),
                          f"模块子目录内不得再有子目录: {mod}/{e.name}/"))
        elif e.suffix == ".md":
            out.append(e)
        else:
            add(Violation((mdir.name, "rootfile", f"{mod}/{e.name}"),
                          f"模块子目录内出现非 .md 文件: {mod}/{e.name}"))
    return out


def _check_task_fields(path: Path, mdir: Path, mnum: int, add) -> tuple[str | None, str | None]:
    text = _read(path)
    tid_match = _TASK_ID_RE.match(path.name)
    tid = tid_match.group(1) if tid_match else path.name
    status = _field_value(text, "状态")
    pm = _field_value(text, "项目里程碑")

    if status is None:
        add(Violation((mdir.name, "task", tid), f"缺 `**状态**` 字段: {path.relative_to(mdir)}"))
    elif status not in TERMINAL_STATUS:
        add(Violation((mdir.name, "task", tid),
                      f"状态非终态: `{status}`（只允许 {'/'.join(TERMINAL_STATUS)}）: "
                      f"{path.relative_to(mdir)}"))

    ok, detail = _pm_status(pm, mnum)
    if not ok:
        add(Violation((mdir.name, "task", tid),
                      f"`**项目里程碑**` 不符: {detail}: {path.relative_to(mdir)}"))
    return status, pm


def _check_readme(mdir: Path, mnum: int, task_ids: set[str],
                  root_ids: set[str], status_map: dict[str, str], add) -> list[str]:
    """README 四类断言；返回摘要行（打印用）。"""
    path = mdir / "README.md"
    text = _read(path)
    heads = _headings(text)
    titles = [h[2] for h in heads]
    summary: list[str] = []

    # ⑤ 任务清单计数（§1）
    actual = {
        mod: len([p for p in (mdir / mod).glob("*.md")]) if (mdir / mod).is_dir() else 0
        for mod in MODULES
    }
    count_rows: list[tuple[str, int]] = []
    count_tables = 0
    for i, (_, _, title, _) in enumerate(heads):
        if "任务清单" not in title:
            continue
        for rows in _tables(_section_body(text, i, heads)):
            header = [_hcell(c) for c in rows[0]]
            if "模块" not in header or "数量" not in header:
                continue
            count_tables += 1
            mi, ci = header.index("模块"), header.index("数量")
            for row in rows[2:]:
                if len(row) <= max(mi, ci):
                    add(Violation((mdir.name, "count", "§1"),
                                  f"任务清单行格数不足: {row}"))
                    continue
                label = row[mi].strip("` ")
                try:
                    n = int(re.sub(r"[^0-9]", "", row[ci]))
                except ValueError:
                    add(Violation((mdir.name, "count", label or "§1"),
                                  f"任务清单数量非整数: {row[ci]!r}"))
                    continue
                if label in MODULES:
                    count_rows.append((label, n))
                elif "顶层" in label:
                    pass  # 根级核验册单列，不计入模块计数
                else:
                    add(Violation((mdir.name, "count", label or "§1"),
                                  f"任务清单出现未知模块行: {label!r}"))

    if count_tables == 0 or not count_rows:
        add(Violation((mdir.name, "count", "§1"), "缺「任务清单」模块计数表（或表为空）"))
    else:
        declared = dict(count_rows)
        for mod in MODULES:
            if actual[mod] and mod not in declared:
                add(Violation((mdir.name, "count", mod),
                              f"任务清单缺模块行 `{mod}`（目录实有 {actual[mod]} 册）"))
            elif mod in declared and declared[mod] != actual[mod]:
                add(Violation((mdir.name, "count", mod),
                              f"任务清单计数 {declared[mod]} != 目录实际 {actual[mod]}（{mod}）"))
        summary.append("清单 " + "/".join(f"{m}={actual[m]}" for m in MODULES))

    # ⑥ 任务流水对应
    alias_bodies = [
        _section_body(text, i, heads)
        for i, (_, _, title, _) in enumerate(heads)
        if any(a in title for a in FLOW_ALIASES)
    ]
    num_tables: list[tuple[list[list[str]], list[str]]] = []
    date_table = False
    for body in alias_bodies:
        for rows in _tables(body):
            header = [_hcell(c) for c in rows[0]]
            if "日期" in header and len(rows) > 2:
                date_table = True
            if "编号" in header:
                num_tables.append((rows, header))

    if not alias_bodies:
        add(Violation((mdir.name, "flow", "§2"),
                      "README 缺「任务流水」节（别名: " + "/".join(FLOW_ALIASES) + "）"))
    elif not num_tables and not date_table:
        add(Violation((mdir.name, "flow", "§2"), "任务流水节无有效表格（或表为空）"))
    elif num_tables:
        rows, header = num_tables[0]
        id_i = header.index("编号")
        st_i = header.index("状态") if "状态" in header else None
        if st_i is None:
            add(Violation((mdir.name, "flow", "§2"), "任务流水表缺 `状态` 列"))
        flow_ids: list[str] = []
        flow_status: dict[str, str] = {}
        seen: set[str] = set()
        for row in rows[2:]:
            if len(row) <= id_i:
                add(Violation((mdir.name, "flow", "§2"), f"流水行格数不足: {row}"))
                continue
            fid = row[id_i].strip("` *")
            if not re.fullmatch(r"[A-Z]+-\d+[a-z]", fid):
                add(Violation((mdir.name, "flow", "§2"), f"流水编号列格式非法: {fid!r}"))
                continue
            if fid in seen:
                add(Violation((mdir.name, "flow", fid), "流水表编号重复"))
                continue
            seen.add(fid)
            flow_ids.append(fid)
            if st_i is None or len(row) <= st_i:
                add(Violation((mdir.name, "flow", fid), "流水行缺 `状态` 格"))
                continue
            flow_status[fid] = row[st_i].strip()
        if not flow_ids:
            add(Violation((mdir.name, "flow", "§2"), "任务流水表无数据行（vacuous）"))
        allowed = [task_ids, task_ids | root_ids]
        if task_ids and set(flow_ids) not in allowed:
            missing = sorted(task_ids - set(flow_ids))
            extra = sorted(set(flow_ids) - task_ids - root_ids)
            add(Violation((mdir.name, "flow", "§2"),
                          "流水 ID 集合 != 任务书 ID 集合"
                          + (f"；缺册 {missing}" if missing else "")
                          + (f"；多册 {extra}" if extra else "")))
        for fid, row_status in flow_status.items():
            if fid in status_map and row_status != status_map[fid]:
                add(Violation((mdir.name, "flow", fid),
                              f"流水状态 `{row_status}` != 任务书状态 `{status_map[fid]}`"))
        summary.append(f"流水 {len(flow_ids)} 行")

    # ⑦ MEMORY / 指针 / 终局证据
    if not any("MEMORY" in t for t in titles):
        add(Violation((mdir.name, "memory", "§4"), "README 缺「MEMORY 摘录」节"))
    if not any(("指针" in t) or ("相关索引" in t) for t in titles):
        add(Violation((mdir.name, "pointer", "§5"), "README 缺「指针 / 相关索引」节"))
    if mnum >= 9 and not any("终局证据" in t for t in titles):
        add(Violation((mdir.name, "evidence", "§3"), "M9 起 README 须有「终局证据」节"))
    return summary


def _check_issues(mdir: Path, add) -> None:
    path = mdir / "issues-closed.md"
    text = _read(path)
    if re.search(r"ISS-\d+", text):
        return
    has_count_table = any(
        "数量" in [_hcell(c) for c in rows[0]] for rows in _tables(text)
    )
    if not has_count_table:
        add(Violation((mdir.name, "issues", "issues-closed.md"),
                      "issues 快照空壳：既无 `ISS-<数字>` 也无计数表"))


def _milestone_dirs(root: Path, add) -> list[Path]:
    adir = root / ARCHIVE_REL
    if not adir.is_dir():
        add(Violation(("*", "archive", "missing"), f"归档目录不存在: {adir}"))
        return []
    # 只认 M<数字>（排除 SimRISC-* 等）。
    dirs = [d for d in adir.iterdir() if d.is_dir() and re.fullmatch(r"M\d+", d.name)]
    if not dirs:
        add(Violation(("*", "archive", "vacuous"), f"{adir} 下无 M<i> 归档目录（vacuous）"))
    return sorted(dirs, key=lambda p: int(p.name[1:]))


def audit(root: Path, pending_ok: bool) -> AuditResult:
    res = AuditResult(pending_ok=pending_ok)
    pending_keys = set(PENDING_117)

    def add(v: Violation) -> None:
        if v.key in pending_keys:
            res.pending_hits.append(v)
        else:
            res.real.append(v)

    for mdir in _milestone_dirs(root, add):
        mnum = int(mdir.name[1:])
        res.milestones.append(mdir.name)

        # ① 三件套
        for name in ("README.md", f"m{mnum}-retrospective.md", "issues-closed.md"):
            p = mdir / name
            if not p.is_file():
                add(Violation((mdir.name, "archive", name), f"缺三件套文件: {name}"))
            elif p.stat().st_size == 0:
                add(Violation((mdir.name, "archive", name), f"三件套文件为空: {name}"))

        # ②③ 根文件 / 子目录封闭
        for e in sorted(mdir.iterdir()):
            if e.is_dir():
                if e.name not in MODULES:
                    add(Violation((mdir.name, "dir", e.name),
                                  f"归档根出现非模块目录: {e.name}/（notes 等补充记录须并入回顾附录）"))
                continue
            if e.name in ("README.md", f"m{mnum}-retrospective.md", "issues-closed.md"):
                continue
            if _ROOT_INTEG_RE.match(e.name):
                if mdir.name not in ROOT_INTEG_HISTORICAL:
                    add(Violation((mdir.name, "rootfile", e.name),
                                  f"根级核验册只允许历史归档 {sorted(ROOT_INTEG_HISTORICAL)} 保留；"
                                  f"新归档应放 integ/: {e.name}"))
                continue
            add(Violation((mdir.name, "rootfile", e.name),
                          f"归档根出现不允许的文件: {e.name}"))

        # ④ 任务书字段（模块子目录 + 根级 m 册）
        task_ids: set[str] = set()
        status_map: dict[str, str] = {}
        for mod in MODULES:
            for p in _module_task_files(mdir, mod, add):
                status, _pm = _check_task_fields(p, mdir, mnum, add)
                res.stats["tasks"] = res.stats.get("tasks", 0) + 1
                if status not in TERMINAL_STATUS:
                    res.stats["bad_status"] = res.stats.get("bad_status", 0) + 1
                tid_match = _TASK_ID_RE.match(p.name)
                if tid_match:
                    task_ids.add(tid_match.group(1))
                    if status:
                        status_map[tid_match.group(1)] = status
        root_ids: set[str] = set()
        for e in sorted(mdir.iterdir()):
            if not (e.is_file() and _ROOT_INTEG_RE.match(e.name)):
                continue
            status, _pm = _check_task_fields(e, mdir, mnum, add)
            res.stats["tasks"] = res.stats.get("tasks", 0) + 1
            tid_match = _TASK_ID_RE.match(e.name)
            if tid_match:
                root_ids.add(tid_match.group(1))
                if status:
                    status_map[tid_match.group(1)] = status

        if not task_ids and not root_ids:
            add(Violation((mdir.name, "task", "vacuous"),
                          "归档内无任何任务书（扫描面 vacuous）"))

        # ⑤⑥⑦ README
        readme = mdir / "README.md"
        if readme.is_file() and readme.stat().st_size:
            summary = _check_readme(mdir, mnum, task_ids, root_ids, status_map, add)
            res.per_milestone.append(f"  {mdir.name}: 册 {len(task_ids) + len(root_ids)}"
                                     + ("；" + "；".join(summary) if summary else ""))

        # ⑧ issues 快照
        if (mdir / "issues-closed.md").is_file() and (mdir / "issues-closed.md").stat().st_size:
            _check_issues(mdir, add)

    if pending_ok:
        hit = {v.key for v in res.pending_hits}
        res.stale_pending = sorted(pending_keys - hit)
    res.real.sort(key=lambda v: (v.key, v.message))
    res.pending_hits.sort(key=lambda v: (v.key, v.message))
    return res


# ── 输出 ──────────────────────────────────────────────────────────────────────
def _print_report(root: Path, res: AuditResult, pending_ok: bool) -> None:
    print("=" * 72)
    print("check-archive — `.tao/archive/M<i>/` 结构与册字段门控（INFRA-116t）")
    print("=" * 72)
    print(f"  检查根（现场）: {root}")
    print(f"  模式: {'--pending-ok（过渡）' if pending_ok else '严格'}")
    print(f"  归档目录（现场统计）: {len(res.milestones)} 个 —— {' '.join(res.milestones)}")
    print(f"  扫描归档册（现场统计）: {res.stats.get('tasks', 0)} 份")
    for line in res.per_milestone:
        print(line)

    if res.real:
        print()
        print(f"VIOLATION（{len(res.real)} 条）:")
        for v in res.real:
            print(f"  [{v.key[0]}/{v.key[1]}/{v.key[2]}] {v.message}")

    if pending_ok:
        print()
        print(f"PENDING（PENDING_117，{len(res.pending_hits)} 条）:")
        for v in res.pending_hits:
            print(f"  [{v.key[0]}/{v.key[1]}/{v.key[2]}] {v.message}")
        if res.stale_pending:
            print()
            print("STALE PENDING（常量项在现场未命中 ⇒ 常量须更新）:")
            for key in res.stale_pending:
                print(f"  [{key[0]}/{key[1]}/{key[2]}] {PENDING_117[key]}")
    elif res.pending_hits:
        print()
        print(f"VIOLATION-PENDING_117（严格模式不豁免，{len(res.pending_hits)} 条）:")
        for v in res.pending_hits:
            print(f"  [{v.key[0]}/{v.key[1]}/{v.key[2]}] {v.message}")

    print("-" * 72)
    if res.ok:
        suffix = f"（仅剩 PENDING_117 {len(res.pending_hits)} 条，待 INFRA-117t 归一）" if pending_ok else ""
        print(f"结果: PASS{suffix}")
    else:
        print(f"结果: FAIL（违规 {len(res.real)} 条"
              + (f" + PENDING_117 {len(res.pending_hits)} 条（严格模式）" if res.pending_hits and not pending_ok else "")
              + (f" + STALE PENDING {len(res.stale_pending)} 条" if res.stale_pending else "")
              + "）")


# ── 自检（临时树：基线 PASS + 注入 FAIL + 过渡边界）────────────────────────────
_BASE_TASK = """# INFRA-001t 示例任务

**模块**：infra
**项目里程碑**：{pm}
**状态**：{status}
"""

def _base_readme(name: str, *, count: int, flow: bool, flow_id: str,
                 memory: bool, evidence: bool) -> str:
    num = name[1:]
    parts = [f"# {name} 归档（Archive）", "",
             f"## 1. {name} 任务清单（1 个，按模块）", "",
             "| 模块 | 数量 |", "|---|---|", f"| infra | {count} |", ""]
    if flow:
        parts += ["## 2. 任务流水（冻结）", "",
                  "| 编号 | 状态 | 完成时间 | 一句改动 |", "| --- | --- | --- | --- |",
                  f"| {flow_id} | 已验证 | 2026-10-01 00:00 | 示例改动 |", ""]
    if evidence:
        parts += ["## 3. 终局证据", "", "| 套件 | 结果 |", "|---|---|", "| L1 | rc=0 |", ""]
    if memory:
        parts += ["## 4. MEMORY 摘录", "", f"0 行（指针见 `m{num}-retrospective.md`）。", ""]
    parts += ["## 5. 指针", "", "- `.tao/knowledge/milestones.md`", ""]
    return "\n".join(parts)

_BASE_ISSUES = """# {m} 阶段已关闭 Issue

| id | title |
| --- | --- |
| `ISS-001` | 示例 |
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_milestone(base: Path, name: str, *, status: str = "已验证",
                     pm: str | None = None, flow: bool = True,
                     flow_id: str = "INFRA-001t", count: int = 1,
                     memory: bool = True, evidence: bool = True,
                     task_name: str = "INFRA-001t-示例任务.md") -> Path:
    mdir = base / ".tao" / "archive" / name
    num = name[1:]
    _write(mdir / "README.md",
           _base_readme(name, count=count, flow=flow, flow_id=flow_id,
                        memory=memory, evidence=evidence))
    _write(mdir / f"m{num}-retrospective.md", f"# {name} 回顾\n")
    _write(mdir / "issues-closed.md", _BASE_ISSUES.format(m=name))
    _write(mdir / "infra" / task_name,
           _BASE_TASK.format(pm=pm or name, status=status))
    return mdir


def _build_historical(base: Path, name: str,
                      extra: dict[str, dict[str, str]] | None = None) -> Path:
    """M1–M6 形态：日期列 changelog、无终局证据；计数按目录实际现场统计。"""
    mdir = base / ".tao" / "archive" / name
    num = name[1:]
    _write(mdir / "infra" / "INFRA-001t-示例任务.md",
           _BASE_TASK.format(pm=name, status="已验证"))
    for mod, files in (extra or {}).items():
        for fname, text in files.items():
            _write(mdir / mod / fname, text)
    counts = {
        mod: len(list((mdir / mod).glob("*.md")))
        for mod in MODULES if (mdir / mod).is_dir()
    }
    rows = "\n".join(f"| {mod} | {n} |" for mod, n in counts.items())
    _write(mdir / "README.md", f"""# {name} 归档（Archive）

## 1. {name} 任务清单（{sum(counts.values())} 个，按模块）

| 模块 | 数量 |
|---|---|
{rows}

## 2. changelog（{name} 时期）

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-09-01 | 示例条目 | infra |

## 3. MEMORY 摘录（{name} 时期）

| 项目 | 状态 |
|---|---|
| 示例 | 完成 |

## 4. 指针

- `.tao/knowledge/milestones.md`
""")
    _write(mdir / f"m{num}-retrospective.md", f"# {name} 回顾\n")
    _write(mdir / "issues-closed.md", _BASE_ISSUES.format(m=name))
    return mdir


def _build_baseline(root: Path) -> None:
    _build_milestone(root, "M9")
    _build_historical(root, "M6")


def _build_pending_tree(root: Path) -> None:
    """M2 两册状态括注 + M7 notes/ + M9/M10 README 缺流水/MEMORY（= PENDING_117）。"""
    _build_historical(root, "M2", extra={
        "testcases": {"TESTCASES-019t-示例.md":
                      _BASE_TASK.format(pm="M2", status="已验证（第 3 轮返工后）")},
        "spec": {"SPEC-064t-示例.md":
                 _BASE_TASK.format(pm="M2", status="已验证（**补填**）")},
    })
    m7 = _build_milestone(root, "M7")
    _write(m7 / "notes" / "record.md", "# 补充记录\n")
    _build_milestone(root, "M9", flow=False, memory=False)
    _build_milestone(root, "M10", flow=False, memory=False)


def _mutate_copy(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst)


def _check_case(name: str, root: Path, pending_ok: bool,
                expect_rc: int, expect_keys: set[tuple[str, str, str]]) -> bool:
    res = audit(root, pending_ok)
    rc = 0 if res.ok else 1
    keys = {v.key for v in res.real} | {v.key for v in res.pending_hits}
    if pending_ok:
        keys |= {(k[0], "stale-" + k[1], k[2]) for k in res.stale_pending}
    ok = (rc == expect_rc) and expect_keys <= keys
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: 期望 rc={expect_rc} "
          f"命中键={sorted(expect_keys) or '∅'} / 实际 rc={rc} 命中={sorted(keys) or '∅'}")
    return ok


def self_test() -> int:
    base = Path(tempfile.mkdtemp(prefix="check-archive-selftest-"))
    results: list[bool] = []
    try:
        baseline = base / "baseline"
        _build_baseline(baseline)
        print("自检 1：基线（M9 五节 + M6 历史 changelog）")
        results.append(_check_case("baseline", baseline, False, 0, set()))

        def inject(idx: int, label: str, mutate, keys: set[tuple[str, str, str]]) -> None:
            tree = base / f"case{idx}"
            _mutate_copy(baseline, tree)
            mutate(tree / ".tao" / "archive" / "M9")
            print(f"自检 {idx + 1}：注入 {label}")
            results.append(_check_case(label, tree, False, 1, keys))

        inject(1, "根级杂项文件", lambda m: _write(m / "extra.md", "# x\n"),
               {("M9", "rootfile", "extra.md")})
        inject(2, "notes/ 目录",
               lambda m: _write(m / "notes" / "r.md", "# r\n"),
               {("M9", "dir", "notes")})
        inject(3, "状态非终态",
               lambda m: _write(m / "infra" / "INFRA-001t-示例任务.md",
                                _BASE_TASK.format(pm="M9", status="待验收")),
               {("M9", "task", "INFRA-001t")})
        inject(4, "项目里程碑字段不符",
               lambda m: _write(m / "infra" / "INFRA-001t-示例任务.md",
                                _BASE_TASK.format(pm="M8", status="已验证")),
               {("M9", "task", "INFRA-001t")})
        inject(5, "任务清单计数不符",
               lambda m: _write(m / "README.md",
                                _read(m / "README.md").replace("| infra | 1 |", "| infra | 2 |")),
               {("M9", "count", "infra")})
        inject(6, "流水缺册",
               lambda m: _write(m / "README.md",
                                _read(m / "README.md").replace(
                                    "| INFRA-001t | 已验证 | 2026-10-01 00:00 | 示例改动 |\n", "")),
               {("M9", "flow", "§2")})
        inject(7, "流水多册",
               lambda m: _write(m / "README.md",
                                _read(m / "README.md").replace(
                                    "| INFRA-001t | 已验证 | 2026-10-01 00:00 | 示例改动 |",
                                    "| INTEG-999t | 已验证 | 2026-10-01 00:00 | 幽灵册 |")),
               {("M9", "flow", "§2")})
        inject(8, "issues 快照空壳",
               lambda m: _write(m / "issues-closed.md", "# 空壳\n\n无内容。\n"),
               {("M9", "issues", "issues-closed.md")})
        inject(9, "缺 MEMORY 节",
               lambda m: _write(m / "README.md",
                                re.sub(r"## 4\. MEMORY 摘录.*?(?=## 5\.)", "", _read(m / "README.md"),
                                       flags=re.S)),
               {("M9", "memory", "§4")})
        inject(10, "缺终局证据节",
               lambda m: _write(m / "README.md",
                                re.sub(r"## 3\. 终局证据.*?(?=## 4\.)", "", _read(m / "README.md"),
                                       flags=re.S)),
               {("M9", "evidence", "§3")})
        inject(11, "流水状态与任务书不符",
               lambda m: _write(m / "README.md",
                                _read(m / "README.md").replace(
                                    "| INFRA-001t | 已验证 |", "| INFRA-001t | 里程碑 |")),
               {("M9", "flow", "INFRA-001t")})
        inject(12, "历史归档缺三件套",
               lambda m: (m / "issues-closed.md").unlink(),
               {("M9", "archive", "issues-closed.md")})

        print(f"自检 {len(results) + 1}：过渡边界（PENDING_117 树）")
        ptree = base / "pending"
        _build_pending_tree(ptree)
        results.append(_check_case("pending:strict", ptree, False, 1, set(PENDING_117)))
        pres = audit(ptree, True)
        strict = audit(ptree, False)
        strict_keys = {v.key for v in strict.real} | {v.key for v in strict.pending_hits}
        boundary_ok = (
            pres.ok
            and strict_keys == set(PENDING_117)
            and not pres.stale_pending
            and {v.key for v in pres.pending_hits} == set(PENDING_117)
        )
        print(f"自检 {len(results) + 1}：--pending-ok 边界")
        print(f"  [{'PASS' if boundary_ok else 'FAIL'}] pending:--pending-ok "
              f"期望 rc=0 且 PENDING 命中 == 常量 {len(PENDING_117)} 条 / "
              f"实际 rc={0 if pres.ok else 1} 命中={len(pres.pending_hits)} "
              f"strict 唯一键={sorted(strict_keys) == sorted(set(PENDING_117))}")
        results.append(boundary_ok)

        stale_ok = audit(baseline, True)
        stale = bool(stale_ok.stale_pending) and not stale_ok.ok
        print(f"自检 {len(results) + 1}：常量对账（未命中即 STALE）")
        print(f"  [{'PASS' if stale else 'FAIL'}] pending:stale 常量未命中 ⇒ FAIL "
              f"（实际 rc={0 if stale_ok.ok else 1}，stale={len(stale_ok.stale_pending)}）")
        results.append(stale)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    passed = sum(1 for r in results if r)
    print("-" * 72)
    print(f"自检结果: {passed}/{len(results)} 用例符合预期")
    return 0 if passed == len(results) else 1


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=None,
                        help="检查另一棵树（默认仓库根）")
    parser.add_argument("--pending-ok", action="store_true",
                        help="过渡模式：只豁免显式 PENDING_117（INFRA-117t 后删除）")
    parser.add_argument("--self-test", action="store_true",
                        help="用临时树跑可达 FAIL 自检")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-archive: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    res = audit(root, args.pending_ok)
    _print_report(root, res, args.pending_ok)
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
