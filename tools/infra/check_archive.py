#!/usr/bin/env python3
"""check-archive: ``.tao/archive/M<i>/`` 归档结构 + 任务书字段门控（INFRA-116t / 117t）。

规则真源 = ``docs/Process-04-里程碑归档规范.md`` §2/§4/§5/§6/§7/§8。
本门控把「归档目录只允许什么」与「每份册必须是什么态」落为**机械检查**：

  1. **三件套**：``README.md`` / ``m<i>-retrospective.md`` / ``issues-closed.md``
     存在且非空。
  2. **根文件封闭**：只允许三件套 ``README.md`` / ``m<i>-retrospective.md`` /
     ``issues-closed.md``；所有任务书（含 ``INTEG-*m`` 核验册）一律放模块子目录。
  3. **子目录封闭**：只允许 6 个模块名（``infra``/``integ``/``llvm``/``qemu``/
     ``spec``/``testcases``）；``notes/`` 等一律 FAIL。
  4. **任务书字段**：模块子目录的每份 ``*.md`` 须有 ``**状态**``
     ∈ {``已验证``,``里程碑``}，``**项目里程碑**`` 的里程碑号 == 所在归档号
     （尾随历史括注按编号判定、不计错；**新归档应写裸 ``M<i>``**）。
  5. **任务清单计数**：README §1 的模块计数 == 模块目录实际 ``*.md`` 数（现场统计）。
  6. **任务流水对应**：README 的「任务流水 / changelog / 台账快照」节须有表格；
     编号列格式（M7+）要求流水 ID 集合 == 模块 ``t`` 册集合，或 == ``t`` 册 + ``m`` 册集合
     （``m`` 可入可不入流水），且行状态 == 任务书状态；日期列格式（M1–M6 历史
     ``changelog``）只要求表格非空。
  7. **README 必备节**：「MEMORY」节、「指针 / 相关索引」节；M9 起另须「终局证据」。
  8. **issues 快照**：``issues-closed.md`` 须含 ``ISS-<数字>`` 或等价计数表。

设计要点：
  - **计数现场统计、不写死**；
  - **fail-closed**：无 ``M<i>`` 目录 / 无任务书 / 流水表空 ⇒ FAIL；
  - **严格默认**（``INFRA-117t`` 归一）：无过渡 flag / 常量，任何违规即 rc=1。

Usage:
    python3 tools/infra/check_archive.py [--root DIR] [--self-test]

``--root DIR`` 检查另一棵树（默认仓库根）；``--self-test`` 用临时树跑
「基线 PASS + 13 类注入 FAIL」自检。

Exit code: 0 = 无违规；1 = 有违规。
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
# 任务册 ID（`-t` / `-k` / `-m` 后缀）。
_TASK_ID_RE = re.compile(r"^([A-Z]+-\d+[a-z])")

@dataclass(frozen=True)
class Violation:
    """一条违规；key = (里程碑, 类别, 主体)，用于报告去重/排序。"""

    key: tuple[str, str, str]
    message: str


@dataclass
class AuditResult:
    real: list[Violation] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    per_milestone: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.real


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


def _check_readme(mdir: Path, mnum: int, t_ids: set[str],
                  m_ids: set[str], status_map: dict[str, str], add) -> list[str]:
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
        allowed = [t_ids, t_ids | m_ids]
        if t_ids and set(flow_ids) not in allowed:
            missing = sorted(t_ids - set(flow_ids))
            extra = sorted(set(flow_ids) - t_ids - m_ids)
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


def audit(root: Path) -> AuditResult:
    res = AuditResult()

    def add(v: Violation) -> None:
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
            add(Violation((mdir.name, "rootfile", e.name),
                          f"归档根出现不允许的文件: {e.name}"))

        # ④ 任务书字段（模块子目录；含 integ/ 下的 m 册）
        task_ids: set[str] = set()
        t_ids: set[str] = set()
        m_ids: set[str] = set()
        status_map: dict[str, str] = {}
        for mod in MODULES:
            for p in _module_task_files(mdir, mod, add):
                status, _pm = _check_task_fields(p, mdir, mnum, add)
                res.stats["tasks"] = res.stats.get("tasks", 0) + 1
                if status not in TERMINAL_STATUS:
                    res.stats["bad_status"] = res.stats.get("bad_status", 0) + 1
                tid_match = _TASK_ID_RE.match(p.name)
                if tid_match:
                    tid = tid_match.group(1)
                    task_ids.add(tid)
                    if tid.endswith("m"):
                        m_ids.add(tid)
                    else:
                        t_ids.add(tid)
                    if status:
                        status_map[tid] = status

        if not task_ids:
            add(Violation((mdir.name, "task", "vacuous"),
                          "归档内无任何任务书（扫描面 vacuous）"))

        # ⑤⑥⑦ README
        readme = mdir / "README.md"
        if readme.is_file() and readme.stat().st_size:
            summary = _check_readme(mdir, mnum, t_ids, m_ids, status_map, add)
            res.per_milestone.append(f"  {mdir.name}: 册 {len(task_ids)}"
                                     + ("；" + "；".join(summary) if summary else ""))

        # ⑧ issues 快照
        if (mdir / "issues-closed.md").is_file() and (mdir / "issues-closed.md").stat().st_size:
            _check_issues(mdir, add)

    res.real.sort(key=lambda v: (v.key, v.message))
    return res


# ── 输出 ──────────────────────────────────────────────────────────────────────
def _print_report(root: Path, res: AuditResult) -> None:
    print("=" * 72)
    print("check-archive — `.tao/archive/M<i>/` 结构与册字段门控（INFRA-116t/117t/118t）")
    print("=" * 72)
    print(f"  检查根（现场）: {root}")
    print(f"  模式: 严格（默认；无过渡 flag）")
    print(f"  归档目录（现场统计）: {len(res.milestones)} 个 —— {' '.join(res.milestones)}")
    print(f"  扫描归档册（现场统计）: {res.stats.get('tasks', 0)} 份")
    for line in res.per_milestone:
        print(line)

    if res.real:
        print()
        print(f"VIOLATION（{len(res.real)} 条）:")
        for v in res.real:
            print(f"  [{v.key[0]}/{v.key[1]}/{v.key[2]}] {v.message}")

    print("-" * 72)
    if res.ok:
        print("结果: PASS")
    else:
        print(f"结果: FAIL（违规 {len(res.real)} 条）")


# ── 自检（临时树：基线 PASS + 13 类注入 FAIL，各自可达）──────────────────────
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


def _mutate_copy(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst)


def _check_case(name: str, root: Path,
                expect_rc: int, expect_keys: set[tuple[str, str, str]]) -> bool:
    res = audit(root)
    rc = 0 if res.ok else 1
    keys = {v.key for v in res.real}
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
        results.append(_check_case("baseline", baseline, 0, set()))

        def inject(idx: int, label: str, mutate, keys: set[tuple[str, str, str]]) -> None:
            tree = base / f"case{idx}"
            _mutate_copy(baseline, tree)
            mutate(tree / ".tao" / "archive" / "M9")
            print(f"自检 {idx + 1}：注入 {label}")
            results.append(_check_case(label, tree, 1, keys))

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
        inject(13, "根级核验册",
               lambda m: _write(m / "INTEG-999m-核验.md", "# m\n"),
               {("M9", "rootfile", "INTEG-999m-核验.md")})
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
    parser.add_argument("--self-test", action="store_true",
                        help="用临时树跑可达 FAIL 自检")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-archive: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    res = audit(root)
    _print_report(root, res)
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
