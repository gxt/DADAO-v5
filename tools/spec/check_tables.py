#!/usr/bin/env python3
"""check_tables.py — `spec/SimRISC-00` 四张 OPC 子表 ⇔ `contracts/opcodes.yaml` 逐格一致性。

**独立 oracle**：期望网格**现场派生**自机器可读真源 `contracts/opcodes.yaml`
（每条记录的 `(op, ha)` → `(子表, 行, 列)`，格内容 = 记录 `id`），再与
`spec/SimRISC-00` 的四张子表文本**双向**比对（缺格 / 多格 / 内容不符 均 FAIL）。
**禁**任何字面网格（同一病根教训：`validate_instrinfo --self-test`）。

结构性映射（编码布局，非格内容；4 条）：
  * `op 0x40` = `OPC-octa`（64 位）、`0x41` = `OPC-tetra`、`0x42` = `OPC-wyde`、`0x43` = `OPC-byte`
  * `ha` 6 位：行 = `ha[5:3]`（表 `AAA-xxx`），列 = `ha[2:0]`（表 `xxx-BBB`）
因此表内格位总数 / 非空格数 / 记录数一律**现场统计并打印**，不写死。

用法：
  python3 tools/spec/check_tables.py [--yaml PATH] [--spec PATH]
  python3 tools/spec/check_tables.py --self-test     # 3 类注入（临时树；不碰真实文件）

退出码：0 = 全部一致；1 = 有格不符 / 自检失败；2 = 输入缺失。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = ROOT / "contracts" / "opcodes.yaml"
DEFAULT_SPEC = ROOT / "spec" / "SimRISC-00-指令系统设计.md"

# op → 子表（编码布局常量；格内容一律不写死）
OP_TABLE = {0x40: "OPC-octa", 0x41: "OPC-tetra", 0x42: "OPC-wyde", 0x43: "OPC-byte"}

SECTION_RE = re.compile(r"^###\s+4\.\d+\s+(OPC-(?:octa|tetra|wyde|byte))\s*指令编码")
HEADER_CELL_RE = re.compile(r"^xxx-([01]{3})$")
ROW_CELL_RE = re.compile(r"^([01]{3})-xxx$")


def _as_int(value, what: str) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    try:
        return int(text, 16) if text.lower().startswith("0x") else int(text)
    except ValueError as exc:  # pragma: no cover - 输入损坏才触发
        raise SystemExit(f"ERROR: {what} 无法解析为整数: {value!r}") from exc


def expected_grid(records: list[dict]) -> tuple[dict[tuple[str, int, int], str], list[str], dict[str, int]]:
    """从 opcodes.yaml 记录现场派生期望网格。"""
    grid: dict[tuple[str, int, int], str] = {}
    problems: list[str] = []
    per_table: dict[str, int] = {name: 0 for name in OP_TABLE.values()}
    for rec in records:
        op = _as_int(rec["op"], f"{rec.get('id')}.op")
        table = OP_TABLE.get(op)
        if table is None:
            continue
        rid = rec["id"]
        if "ha" not in rec:
            problems.append(f"{rid}: op {op:#04x} 属 {table} 但没有 `ha` 字段")
            continue
        ha = _as_int(rec["ha"], f"{rid}.ha")
        if not 0 <= ha <= 0x3F:
            problems.append(f"{rid}: ha={ha:#04x} 超出 6 位")
            continue
        key = (table, (ha >> 3) & 0x7, ha & 0x7)
        if key in grid:
            problems.append(f"{key[0]} 行{key[1]:03b} 列{key[2]:03b}: "
                            f"{grid[key]} 与 {rid} 撞格")
            continue
        grid[key] = rid
        per_table[table] += 1
    return grid, problems, per_table


def parse_spec(text: str) -> tuple[dict[tuple[str, int, int], str], dict[str, int], list[str]]:
    """解析 SimRISC-00 四张 MISC 子表（列顺序按表头现场读取，不假定顺序）。"""
    cells: dict[tuple[str, int, int], str] = {}
    grid_size: dict[str, int] = {}
    problems: list[str] = []
    table = None
    cols: list[int] = []
    for line in text.splitlines():
        if line.startswith("### "):
            m = SECTION_RE.match(line)
            table, cols = (m.group(1), []) if m else (None, [])
            continue
        if table is None or not line.startswith("|"):
            continue
        fields = [f.strip() for f in line.split("|")[1:-1]]
        if not cols:
            header = fields[1:] if fields else []
            parsed = [HEADER_CELL_RE.match(f) for f in header]
            if header and all(parsed):
                cols = [int(m.group(1), 2) for m in parsed]
                grid_size[table] = grid_size.get(table, 0) + len(cols) * 8
            continue
        if not fields:
            continue
        row_m = ROW_CELL_RE.match(fields[0])
        if not row_m:
            continue
        row = int(row_m.group(1), 2)
        for i, col in enumerate(cols):
            cell = fields[1 + i] if 1 + i < len(fields) else ""
            if cell:
                cells[(table, row, col)] = cell
    for name in OP_TABLE.values():
        if grid_size.get(name, 0) == 0:
            problems.append(f"spec 中未找到 {name} 子表（或其表头不可解析）")
    return cells, grid_size, problems


def compare(expected, actual):
    mismatches: list[str] = []
    for key in sorted(expected):
        want = expected[key]
        got = actual.get(key, "")
        if got != want:
            mismatches.append(f"{key[0]} 行{key[1]:03b} 列{key[2]:03b}: 期望={want!r} 实际={got or '<空格>'!r}")
    for key in sorted(set(actual) - set(expected)):
        mismatches.append(f"{key[0]} 行{key[1]:03b} 列{key[2]:03b}: 期望=<无记录> 实际={actual[key]!r}")
    return mismatches


def run(yaml_path: Path, spec_path: Path, verbose: bool = True) -> int:
    records = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    expected, exp_problems, per_table = expected_grid(records)
    actual, grid_size, parse_problems = parse_spec(spec_path.read_text(encoding="utf-8"))
    problems = exp_problems + parse_problems
    mismatches = compare(expected, actual)

    total_cells = sum(grid_size.values())
    if verbose:
        for name in OP_TABLE.values():
            bad = [m for m in mismatches if m.startswith(name + " ")]
            print(f"[{'FAIL' if bad else 'PASS'}] {name}: 记录={per_table[name]} "
                  f"表格={grid_size.get(name, 0)} 非空={sum(1 for k in actual if k[0] == name)} "
                  f"不符={len(bad)}")
        for msg in problems + mismatches:
            print(f"[FAIL] {msg}")
        print(f"check_tables: {len(OP_TABLE)} 表 {len(expected)} 条记录 / {total_cells} 格，"
              f"{len(mismatches)} 格不符，{len(problems)} 项结构问题"
              f"（期望由 {yaml_path.name} 现场派生）")
    return 1 if (mismatches or problems) else 0


def _patch_record(yaml_text: str, rid: str, field: str, new_value: str) -> str:
    """把某条记录的某字段改成 new_value（自检用；断言确实命中 1 处）。"""
    anchor = f"- id: {rid}\n"
    start = yaml_text.index(anchor)
    end = yaml_text.find("\n- id: ", start + 1)
    block = yaml_text[start:end if end != -1 else len(yaml_text)]
    pat = re.compile(rf"^(  {re.escape(field)}: )'[^']*'$", re.M)
    matches = pat.findall(block)
    assert len(matches) == 1, (rid, field, len(matches))
    patched = pat.sub(rf"\g<1>'{new_value}'", block, count=1)
    return yaml_text[:start] + patched + (yaml_text[end:] if end != -1 else "")


def _replace_cell(spec_text: str, old: str, new: str) -> str:
    assert spec_text.count(old) == 1, (old, spec_text.count(old))
    return spec_text.replace(old, new, 1)


def self_test() -> int:
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "SPEC-152t-rework"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="check_tables-", dir=tmp_root))
    yaml_text = DEFAULT_YAML.read_text(encoding="utf-8")
    spec_text = DEFAULT_SPEC.read_text(encoding="utf-8")
    # 自检取真实记录 id 现场派生（不写死任何网格；取第一条四表记录与第一条带 ha 记录）。
    records = yaml.safe_load(yaml_text)
    sample = next(r for r in records if _as_int(r["op"], "op") in OP_TABLE and "ha" in r)
    sample_id, sample_ha = sample["id"], _as_int(sample["ha"], "ha")
    other_ha = f"0x{(sample_ha ^ 0x1):02X}"  # 同行相邻列 ⇒ 必撞/必偏格

    cases = [
        ("baseline", yaml_text, spec_text, True, "未注入 ⇒ 期望 rc=0"),
        ("yaml-cell-changed", _patch_record(yaml_text, sample_id, "ha", other_ha),
         spec_text, False, f"改 opcodes.yaml 一格（{sample_id}.ha {sample_ha:#04x}→{other_ha}）⇒ 期望 rc!=0"),
        ("spec-cell-changed", yaml_text,
         _replace_cell(spec_text, f"| {sample_id}", f"| x_{sample_id}"), False,
         f"改 spec 表一格（{sample_id} → x_...）⇒ 期望 rc!=0"),
        ("spec-cell-deleted", yaml_text,
         _replace_cell(spec_text, f"| {sample_id}", "| " + " " * len(sample_id)), False,
         f"删 spec 表一格（{sample_id}）⇒ 期望 rc!=0"),
    ]

    ok = True
    try:
        for i, (name, y_txt, s_txt, expect_zero, desc) in enumerate(cases, 1):
            y_path = tmpdir / f"opcodes-{i}.yaml"
            s_path = tmpdir / f"spec-{i}.md"
            y_path.write_text(y_txt, encoding="utf-8")
            s_path.write_text(s_txt, encoding="utf-8")
            if i > 1 and y_txt == yaml_text and s_txt == spec_text:
                print(f"[FAIL] self-test case{i} {name}: 空注入（文件未变化）")
                ok = False
                continue
            rc = run(y_path, s_path, verbose=False)
            good = (rc == 0) if expect_zero else (rc != 0)
            print(f"[{'PASS' if good else 'FAIL'}] self-test case{i} {name}: 期望={'0' if expect_zero else '非0'} "
                  f"实际={rc}（{desc}）")
            ok = ok and good
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="四张 OPC 子表 ⇔ opcodes.yaml 逐格一致性")
    ap.add_argument("--yaml", type=Path, default=DEFAULT_YAML)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--self-test", action="store_true", help="3 类注入自检（临时树）")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    for p in (args.yaml, args.spec):
        if not p.is_file():
            print(f"[FAIL] 输入缺失: {p}")
            return 2
    return run(args.yaml, args.spec)


if __name__ == "__main__":
    raise SystemExit(main())
