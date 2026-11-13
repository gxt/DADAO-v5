#!/usr/bin/env python3
"""check_fp_ieee_audit.py — FP-IEEE 对齐审计册门控（m13-integ-009）。

职责（可执行、可失败；计数一律**现场统计**，不写死 66/52/48）：

  1. 覆盖：`contracts/fp_semantics.yaml` 的 `scope: fp` 记录数 ==
     `contracts/opcodes.yaml` 中 `scope` 含 `fp` 的 id 数（双向一致）。
  2. 表 A == `spec/SimRISC-07` 附录 A 的 52 行：mnemonic **集合与顺序**逐项一致
     （附录 A 是生成区，机器解析，不从实现反推）。
  3. 表 B == 合同 66 条里不在附录 A 的那部分（集合相等、无重复、无遗漏）。
  4. 行完整性：表 A/B 每行 6 列且
     - IEEE 列含 `§<数字>`（章节号可核对）；
     - 行为列引用的 `P<n>` 在 §3 行为模式表中已定义；每个已定义模式至少被引用一次；
     - 结论列 ∈ {一致, 偏离, IEEE 未规定}；
     - 动作列含 {不改, 改 spec 措辞, 改实现, 立子任务} 之一；
     - 影响面列非空。
  5. 偏离收口：结论=偏离 的行，动作列必须带任务号（`mNN-<module>-<NNN[N]>`）
     或「需立册」，且该指令出现在 §2 结论摘要（防止「表里偏离、摘要不提」）。
  6. 摘要计数与表格一致：§2 的「一致 N 行 / 未规定 N 行 / 偏离 N 行」== 现场统计。

退出 0 = 通过；退出 1 = 失败。逐项打印「检查名 + 期望/实际 + rc」。

Spec-first：判据来自 `contracts/fp_semantics.yaml`、`contracts/opcodes.yaml`、
`spec/SimRISC-07` 附录 A（不以本册自身为真源）。

Usage: python3 tools/spec/check_fp_ieee_audit.py [--repo-root .]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPORT = Path("docs/TestReports/M13-FP-IEEE对齐审计.md")
FP_SEM = Path("contracts/fp_semantics.yaml")
OPCODES = Path("contracts/opcodes.yaml")
SPEC07 = Path("spec/SimRISC-07-浮点运算.md")

CONCLUSIONS = ("一致", "偏离", "IEEE 未规定")
ACTIONS = ("不改", "改 spec 措辞", "改实现", "立子任务")
RE_CLAUSE = re.compile(r"§\d+(?:\.\d+)*")
RE_MODE = re.compile(r"\bP(\d+)\b")
RE_TASK = re.compile(r"m1[0-9]-[a-z]+-\d{3,4}")
RE_TABLE_A = re.compile(r"^## 4\. 表 A")
RE_TABLE_B = re.compile(r"^## 5\. 表 B")
RE_SECTION_3 = re.compile(r"^## 3\. 行为模式")
RE_SECTION_6 = re.compile(r"^## 6\. IEEE")
RE_SUMMARY_COUNT = re.compile(r"\*\*(一致|IEEE 未规定|偏离) (\d+) 行\*\*")


class Checker:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.failures = 0

    def check(self, name: str, ok: bool, expected: str, actual: str) -> bool:
        rc = 0 if ok else 1
        if not ok:
            self.failures += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: 期望 {expected} / 实际 "
              f"{actual} (rc={rc})")
        return ok


def contract_ids(root: Path) -> list[str]:
    data = yaml.safe_load((root / FP_SEM).read_text(encoding="utf-8"))
    return [rec["id"] for rec in data["instructions"]]


def opcode_fp_ids(root: Path) -> list[str]:
    entries = yaml.safe_load((root / OPCODES).read_text(encoding="utf-8"))
    return [e["id"] for e in entries if "fp" in (e.get("scope") or [])]


def appendix_a(root: Path) -> list[tuple[str, str]]:
    text = (root / SPEC07).read_text(encoding="utf-8")
    body = text.split("<!-- ASSEMBLY_LIST_START -->")[1]
    body = body.split("<!-- ASSEMBLY_LIST_END -->")[0]
    rows: list[tuple[str, str]] = []
    for line in body.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        mnemonic = cells[0].strip("`")
        ident = cells[-1].strip("`")
        rows.append((mnemonic, ident))
    return rows


def report_tables(root: Path) -> tuple[list[list[str]], list[list[str]], str]:
    text = (root / REPORT).read_text(encoding="utf-8")
    lines = text.splitlines()
    table_a: list[list[str]] = []
    table_b: list[list[str]] = []
    where = None
    for line in lines:
        if RE_TABLE_A.match(line):
            where = "A"
            continue
        if RE_TABLE_B.match(line):
            where = "B"
            continue
        if line.startswith("## "):
            where = None
            continue
        if where and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0] in ("指令", "") or set(cells[0]) <= set("- "):
                continue
            (table_a if where == "A" else table_b).append(cells)
    return table_a, table_b, text


def legend_modes(text: str) -> set[str]:
    modes: set[str] = set()
    inside = False
    for line in text.splitlines():
        if RE_SECTION_3.match(line):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside and line.startswith("| P"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            modes.add(cells[0])
    return modes


def summary_section(text: str) -> str:
    start = text.find("## 2. 结论摘要")
    end = text.find("## 3. 行为模式")
    if start < 0 or end < 0:
        return ""
    return text[start:end]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--raw", type=Path, default=None,
                        help="把逐条审计表另存为 TSV（运行期目录用）")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    c = Checker(root)

    ids = contract_ids(root)
    fp_opcodes = opcode_fp_ids(root)
    app = appendix_a(root)
    table_a, table_b, text = report_tables(root)
    modes = legend_modes(text)

    # 1. 合同与 opcodes 双向一致（现场计数）
    c.check("1a contract fp 计数", len(ids) == len(set(ids)),
            "无重复 id", f"{len(ids)} 条")
    c.check("1b opcodes fp 集合 == contract",
            set(ids) == set(fp_opcodes),
            f"{len(set(ids))} 个 id 双向一致",
            f"contract={len(set(ids))} opcodes={len(set(fp_opcodes))} "
            f"差={sorted(set(ids) ^ set(fp_opcodes))}")

    # 2. 表 A 与附录 A 集合 + 顺序
    app_mnemonics = [m for m, _ in app]
    app_ids = [i for _, i in app]
    a_mnemonics = [row[0].strip("`") for row in table_a]
    c.check("2a 附录 A 行数", len(app) > 0, ">0", str(len(app)))
    c.check("2b 表 A 行数 == 附录 A", len(table_a) == len(app),
            str(len(app)), str(len(table_a)))
    c.check("2c 表 A 顺序 == 附录 A", a_mnemonics == app_mnemonics,
            "逐项同序",
            "首个差异=" + _first_diff(a_mnemonics, app_mnemonics))
    c.check("2d 表 A 无重复", len(set(a_mnemonics)) == len(a_mnemonics),
            "无重复", f"{len(set(a_mnemonics))} 个不同")

    # 3. 表 B == 合同 − 附录 A
    rest = [i for i in ids if i not in set(app_ids)]
    b_ids = [row[0].strip("`") for row in table_b]
    c.check("3a 表 B 行数 == 合同−附录A", len(table_b) == len(rest),
            str(len(rest)), str(len(table_b)))
    c.check("3b 表 B 集合 == 合同−附录A", set(b_ids) == set(rest),
            "集合相等",
            f"缺={sorted(set(rest) - set(b_ids))} 多="
            f"{sorted(set(b_ids) - set(rest))}")
    c.check("3c 表 A/B 合计 == 合同", len(table_a) + len(table_b) == len(ids),
            str(len(ids)), str(len(table_a) + len(table_b)))

    # 4. 行完整性
    bad_cols, bad_clause, bad_mode, bad_conc, bad_act, bad_impact = ([] for _ in
                                                                    range(6))
    for row in table_a + table_b:
        label = row[0]
        if len(row) != 6:
            bad_cols.append(f"{label}({len(row)} 列)")
            continue
        _, clause, mode, concl, action, impact = row
        if not RE_CLAUSE.search(clause) and not (
                concl == "IEEE 未规定" and "无对应" in clause):
            bad_clause.append(label)
        m = RE_MODE.search(mode)
        if not m or m.group(0) not in modes:
            bad_mode.append(label)
        if concl not in CONCLUSIONS:
            bad_conc.append(f"{label}={concl}")
        if not any(tok in action for tok in ACTIONS):
            bad_act.append(label)
        if not impact.strip():
            bad_impact.append(label)
    c.check("4a 每行 6 列", not bad_cols, "6 列", str(bad_cols))
    c.check("4b IEEE 列含章节号", not bad_clause, "含 §<数字>", str(bad_clause))
    c.check("4c 行为列引用已定义模式", not bad_mode, "P<n> 均定义",
            str(bad_mode))
    c.check("4d 结论列取值", not bad_conc, f"∈{CONCLUSIONS}", str(bad_conc))
    c.check("4e 动作列取值", not bad_act, f"含{ACTIONS} 之一", str(bad_act))
    c.check("4f 影响面非空", not bad_impact, "非空", str(bad_impact))

    used = {RE_MODE.search(row[2]).group(0) for row in table_a + table_b
            if len(row) == 6 and RE_MODE.search(row[2])}
    c.check("4g 模式表无未引用项", modes and used <= modes,
            f"已定义 {len(modes)} 个均被引用",
            f"未引用={sorted(modes - used)} 未定义={sorted(used - modes)}")

    # 5. 偏离收口
    summary = summary_section(text)
    dev_rows = [row for row in table_a + table_b
                if len(row) == 6 and row[3] == "偏离"]
    bad_dev = []
    for row in dev_rows:
        action = row[4]
        if not (RE_TASK.search(action) or "需立册" in action):
            bad_dev.append(f"{row[0]}(动作无任务号/需立册)")
        if row[0].strip("`") not in summary:
            bad_dev.append(f"{row[0]}(摘要未提)")
    c.check("5a 偏离行有后续动作", not bad_dev, "任务号或需立册 + 摘要提及",
            str(bad_dev))

    # 5b. 结论与动作语义自洽：一致/未规定 不得要求「改实现」；偏离 必须给出
    #     改实现或改 spec 措辞（否则「偏离」无收口方向）。
    bad_pair = []
    for row in table_a + table_b:
        if len(row) != 6:
            continue
        concl, action = row[3], row[4]
        if concl in ("一致", "IEEE 未规定") and "改实现" in action:
            bad_pair.append(f"{row[0]}({concl} 却要改实现)")
        if concl == "偏离" and not ("改实现" in action or "改 spec 措辞" in action):
            bad_pair.append(f"{row[0]}(偏离但动作无方向)")
    c.check("5b 结论↔动作自洽", not bad_pair, "一致/未规定⇒不改实现；偏离⇒有方向",
            str(bad_pair))

    # 6. 摘要计数 == 现场统计
    counts = {"一致": 0, "IEEE 未规定": 0, "偏离": 0}
    for row in table_a + table_b:
        if len(row) == 6 and row[3] in counts:
            counts[row[3]] += 1
    stated = {m.group(1): int(m.group(2))
              for m in RE_SUMMARY_COUNT.finditer(summary)}
    c.check("6a 摘要计数与表格一致", stated == counts,
            f"表格统计 {counts}", f"摘要声明 {stated}")

    if args.raw is not None:
        id_of = {m.upper(): i for m, i in app}
        rows = [(n, id_of.get(n.upper(), n)) for n in a_mnemonics]
        rows += [(i, i) for i in b_ids]
        by_id = {r[0].strip("`"): r for r in table_a + table_b}
        name_of = {i: m for m, i in app}
        out = ["id\tmnemonic\torder\tieee\tmode\tconclusion\taction\timpact"]
        for order, (mnemonic, ident) in enumerate(rows, start=1):
            row = by_id.get(mnemonic) or by_id.get(ident)
            if row is None or len(row) != 6:
                continue
            cells = [c.replace("\t", " ") for c in row[1:]]
            out.append("\t".join([ident, name_of.get(ident, ident),
                                   str(order)] + cells))
        args.raw.parent.mkdir(parents=True, exist_ok=True)
        args.raw.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"raw: {args.raw} ({len(out) - 1} 行)")

    print(f"\nsummary: 合同 {len(ids)} 条 / 附录 A {len(app)} 行 / 表 A "
          f"{len(table_a)} + 表 B {len(table_b)}；一致 {counts['一致']}、"
          f"IEEE 未规定 {counts['IEEE 未规定']}、偏离 {counts['偏离']}；"
          f"failures {c.failures}")
    return 0 if c.failures == 0 else 1


def _first_diff(a: list[str], b: list[str]) -> str:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"#{i} 表A={x} 附录A={y}"
    return "长度不同" if len(a) != len(b) else "无"


if __name__ == "__main__":
    sys.exit(main())
