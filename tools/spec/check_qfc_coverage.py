#!/usr/bin/env python3
"""check_qfc_coverage.py — QFC 表 ↔ contracts/opcodes.yaml 双向覆盖校验。

独立 oracle：本脚本直接从规范 `spec/SimRISC-00-指令系统设计.md` 解析 QFC
主表 + 全部 MISC 子表，再与机器可读编码表 `contracts/opcodes.yaml` 做双向
比对，用于发现「规范表 ↔ 编码表」之间的漏填/错填。

定位：lint，informational，**永不阻断**（始终 exit 0）。只读，不修改任何
yaml/规范文件。

QFC 表结构（SimRISC 0.5.3）：
  - 主表：行头 `RRRR-Rxxx`（5 位），列头 `xxxx-xCCC`（3 位）
      bits[7:3] = int("RRRR-R", 2)
      bits[2:0] = int("CCC", 2)
      op = (bits[7:3] << 3) | bits[2:0]
  - MISC 子表：行头 `RRR-xxx`（3 位），列头 `xxx-CCC`（3 位）
      ha[5:3] = int("RRR", 2)
      ha[2:0] = int("CCC", 2)
      ha = (ha[5:3] << 3) | ha[2:0]
      op 由主表中指向该子表的 `MISC-*` 单元格决定（不硬编码）
  - 单元格语义：
      空白       → reserved（UNDI 保留），不计入指令集合
      `MISC-*`   → 子表指针，不是具体指令，不计入指令集合
      `名称-格式` → 一条具体指令

比对逻辑：
  1. 解析 QFC → `(op, ha_or_None)` 集合 qfc_opids
  2. 读 opcodes.yaml → `(op, ha_or_None)` 集合 yaml_opids
     （ha 统一转为整数比较；主表指令无 ha 记为 None）
  3. 报告双向差异，并对每条差异按 M1 内/外分类
     （M1 范围定义见 `contracts/opcodes.yaml` 头部与
      `.tao/knowledge/contract-isa.md`：M1 外 = 浮点 RF / 特权 cfx / LR-SC）
  4. 数量汇总；exit 0（lint 警告不阻断）
"""

import os
import re
import sys

try:
    import yaml as _yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC_PATH = os.path.join(REPO_ROOT, "spec", "SimRISC-00-指令系统设计.md")
YAML_PATH = os.path.join(REPO_ROOT, "contracts", "opcodes.yaml")

# ────────────────────────────── 通用工具 ──────────────────────────────

def _cells(line):
    """把 markdown 表格行拆成单元格；非表格行返回 None。"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _to_int(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        val = val.strip()
        if val.lower().startswith("0x"):
            return int(val, 16)
        return int(val)
    raise ValueError(f"无法转换为整数: {val!r}")


def parse_md_table(section_lines, row_re, col_re):
    """解析一个 markdown 表格。

    返回 (cells, reserved, header_ok)：
      cells    — {(row_key, col_key): text}，仅非空白单元格
      reserved — 空白单元格数量
      header_ok— 是否找到表头与分隔行
    row_re/col_re 均带一个捕获组，group(1) 是二进制串。
    """
    header = None
    sep_idx = None
    for idx, line in enumerate(section_lines):
        cs = _cells(line)
        if cs is None:
            continue
        if header is None:
            if any(col_re.match(c) for c in cs):
                header = cs
            continue
        if sep_idx is None:
            if any(c.startswith("---") for c in cs):
                sep_idx = idx
            continue
        break

    if header is None or sep_idx is None:
        return {}, 0, False

    col_vals = []
    for c in header[1:]:
        m = col_re.match(c)
        col_vals.append(int(m.group(1), 2) if m else None)

    cells = {}
    reserved = 0
    for line in section_lines[sep_idx + 1:]:
        cs = _cells(line)
        if not cs:
            continue
        rm = row_re.match(cs[0])
        if rm is None:
            continue
        row_val = int(rm.group(1).replace("-", ""), 2)
        for ci, cell in enumerate(cs[1:]):
            if ci >= len(col_vals) or col_vals[ci] is None:
                continue
            if not cell:
                reserved += 1
                continue
            cells[(row_val, col_vals[ci])] = cell
    return cells, reserved, True


# ────────────────────────────── 规范解析 ──────────────────────────────

ROW_MAIN = re.compile(r"^(\d{4}-\d)xxx$")
COL_MAIN = re.compile(r"^xxxx-x(\d{3})$")
ROW_SUB = re.compile(r"^(\d{3})-xxx$")
COL_SUB = re.compile(r"^xxx-(\d{3})$")

MISC_PTR = re.compile(r"^MISC-(.+)$")


def _split_sections(lines):
    """按 markdown 标题切分主表与 MISC 子表区段。

    返回 (main_lines, {sub_name: sub_lines})。
    """
    main_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## SimRISC QFC"):
            main_start = i
            break
    if main_start is None:
        return None, {}

    main_end = None
    for i in range(main_start + 1, len(lines)):
        if lines[i].startswith("###"):
            main_end = i
            break
    if main_end is None:
        main_end = len(lines)

    sub_starts = [(i, line.strip()) for i, line in enumerate(lines)
                  if line.startswith("###") and "MISC-" in line]
    subs = {}
    for j, (i, title) in enumerate(sub_starts):
        if j + 1 < len(sub_starts):
            end = sub_starts[j + 1][0]
        else:
            end = len(lines)
            for k in range(i + 1, len(lines)):
                if lines[k].startswith("## "):
                    end = k
                    break
        m = re.search(r"MISC-[A-Za-z0-9_]+", title)
        name = m.group(0) if m else title
        subs[name] = lines[i:end]

    return lines[main_start:main_end], subs


def parse_spec(spec_path):
    """解析规范 QFC 表。

    返回 dict：
      qfc_opids   — set((op, ha_or_None))，仅具体指令
      pointers    — {op: 'MISC-xxx'} 主表子表指针
      sub_stats   — [(name, op, count)] 各子表指令数
      reserved    — 空白（reserved）单元格总数
      errors      — 结构性错误（指针/子表对不上）
    """
    with open(spec_path, encoding="utf-8") as f:
        lines = f.readlines()

    main_lines, subs = _split_sections(lines)
    result = {"qfc_opids": set(), "names": {}, "pointers": {},
              "sub_stats": [], "reserved": 0, "errors": []}
    if main_lines is None:
        result["errors"].append("未找到 '## SimRISC QFC' 主表区段")
        return result

    main_cells, main_reserved, ok = parse_md_table(main_lines, ROW_MAIN, COL_MAIN)
    if not ok:
        result["errors"].append("主表未找到表头/分隔行")
        return result
    result["reserved"] += main_reserved

    for (row_val, col_val), text in main_cells.items():
        op = (row_val << 3) | col_val
        m = MISC_PTR.match(text)
        if m:
            result["pointers"][op] = text
        else:
            result["qfc_opids"].add((op, None))
            result["names"][(op, None)] = text

    # 按主表指针解析子表（op 由指针决定，不硬编码）
    for op, name in sorted(result["pointers"].items()):
        if name not in subs:
            result["errors"].append(f"主表指针 {name}@op=0x{op:02X} 找不到对应子表区段")
            continue
        cells, reserved, ok = parse_md_table(subs[name], ROW_SUB, COL_SUB)
        if not ok:
            result["errors"].append(f"子表 {name} 未找到表头/分隔行")
            continue
        result["reserved"] += reserved
        for (row_val, col_val), text in cells.items():
            ha = (row_val << 3) | col_val
            result["qfc_opids"].add((op, ha))
            result["names"][(op, ha)] = text
        result["sub_stats"].append((name, op, len(cells)))

    # 反向：有子表区段但主表无指针
    for name in subs:
        if name not in result["pointers"].values():
            result["errors"].append(f"子表区段 {name} 在主表中无对应 MISC 指针")

    return result


def load_yaml(yaml_path):
    """读 opcodes.yaml，返回 (op, ha_or_None) → record 映射。"""
    with open(yaml_path, encoding="utf-8") as f:
        data = _yaml.safe_load(f)
    records = {}
    for rec in data:
        op = _to_int(rec["op"])
        ha = rec.get("ha")
        ha = _to_int(ha) if ha is not None else None
        records[(op, ha)] = rec
    return records


# ────────────────────────────── M1 分类 ──────────────────────────────

# QFC 单元格名称格式为「指令-格式」，分类前剥掉格式后缀
_QFC_FORMATS = {"rrrr", "rrii", "rrri", "riii", "iiii", "rwii",
                "orrr", "orri", "oiii", "crrr", "crii", "ciii"}


def _strip_format(name):
    head, sep, tail = name.rpartition("-")
    if sep and tail in _QFC_FORMATS:
        return head
    return name


def classify_m1(op, ha, name, misc_name=None):
    """判断一条编码是否属于 M1 范围外，并给出类别。

    M1 外类别（contracts/opcodes.yaml 头部 + contract-isa.md）：
      - 浮点 RF：MISC-RF 子表，或名称含 -rf / ft*/fo* / rd2rf / rf2rd
      - 特权 cfx：cfx2rd/cfx2rc/cfxld/cfxst/escape/trap
      - LR-SC 原子：MISC-AMO 子表的 lr_*/sc_*

    misc_name 是该 (op) 对应的 MISC 子表名（由主表指针给出，不硬编码）；
    主表指令为 None。返回 (in_m1: bool, category: str)。
    """
    n = _strip_format(name or "")
    if misc_name == "MISC-RF":
        return False, "浮点（MISC-RF）"
    if misc_name == "MISC-AMO" and re.match(r"^(lr_|sc_)", n):
        return False, "LR-SC 原子"
    if (re.match(r"^(ft|fo)", n) or "-rf-" in n or n.endswith("-rf")
            or "2rf" in n or "rf2" in n):
        return False, "浮点（RF）"
    if n.startswith("cfx") or n.startswith("escape") or n.startswith("trap"):
        return False, "特权 cfx"
    if re.match(r"^(lr_|sc_)", n):
        return False, "LR-SC 原子"
    return True, "M1 内"


# ────────────────────────────── 主流程 ──────────────────────────────

def main():
    print("check_qfc_coverage: QFC 表 ↔ contracts/opcodes.yaml 双向覆盖校验")
    print(f"  spec: {os.path.relpath(SPEC_PATH, REPO_ROOT)}")
    print(f"  yaml: {os.path.relpath(YAML_PATH, REPO_ROOT)}")
    print()

    if not os.path.isfile(SPEC_PATH) or not os.path.isfile(YAML_PATH):
        print("[WARN] 输入文件缺失，跳过检查（informational，不阻断）")
        sys.exit(0)

    spec = parse_spec(SPEC_PATH)
    qfc_opids = spec["qfc_opids"]

    yaml_records = load_yaml(YAML_PATH)
    yaml_opids = set(yaml_records)

    # ── QFC 解析汇总 ──
    main_concrete = sum(1 for (op, ha) in qfc_opids if ha is None)
    print("[QFC 解析]")
    print(f"  主表具体指令单元格: {main_concrete}")
    for name, op, count in spec["sub_stats"]:
        print(f"  {name:<10} (op=0x{op:02X}): {count}")
    print(f"  子表指针: " + ", ".join(
        f"{n}@0x{o:02X}" for o, n in sorted(spec["pointers"].items())))
    print(f"  reserved（空白）单元格: {spec['reserved']}")
    print(f"  QFC (op,ha) 指令总数: {len(qfc_opids)}")
    print()

    print("[YAML 解析]")
    print(f"  记录数: {len(yaml_records)}，distinct (op,ha): {len(yaml_opids)}")
    print()

    if spec["errors"]:
        print("[QFC 结构告警]")
        for e in spec["errors"]:
            print(f"  ! {e}")
        print()

    # ── 双向差异 ──
    qfc_only = qfc_opids - yaml_opids
    yaml_only = yaml_opids - qfc_opids

    def fmt(op, ha):
        return f"op=0x{op:02X} ha={'null' if ha is None else '0x%02X' % ha}"

    print("[双向差异]")
    print(f"  QFC-only（QFC 有、yaml 缺）: {len(qfc_only)}")
    print(f"  YAML-only（yaml 有、QFC 不含）: {len(yaml_only)}")
    print()

    print("[差异分类]（M1 内差异 = 真实缺口/错误；M1 外差异 = 已知范围排除）")
    if not qfc_only and not yaml_only:
        print("  （无差异）")
    m1_in_diffs = 0
    for op, ha in sorted(qfc_only, key=lambda x: (x[0], -1 if x[1] is None else x[1])):
        name = spec["names"].get((op, ha), "")
        in_m1, cat = classify_m1(op, ha, name,
                                 misc_name=spec["pointers"].get(op))
        m1_in_diffs += 1 if in_m1 else 0
        print(f"  QFC-only  {fmt(op, ha)}  {name or '?'}  → {cat}")
    for op, ha in sorted(yaml_only, key=lambda x: (x[0], -1 if x[1] is None else x[1])):
        rec = yaml_records[(op, ha)]
        name = rec.get("insn", "?")
        if rec.get("excluded_m1"):
            in_m1, cat = False, "M1 外（yaml excluded_m1）"
        else:
            in_m1, cat = classify_m1(op, ha, name,
                                     misc_name=spec["pointers"].get(op))
        m1_in_diffs += 1 if in_m1 else 0
        print(f"  YAML-only {fmt(op, ha)}  {name}  → {cat}")
    print()

    # ── M1 范围说明 ──
    qfc_m1_out = []
    qfc_cats = {}
    for op, ha in qfc_opids:
        in_m1, cat = classify_m1(op, ha, spec["names"].get((op, ha), ""),
                                 misc_name=spec["pointers"].get(op))
        if not in_m1:
            qfc_m1_out.append((op, ha))
            qfc_cats[cat] = qfc_cats.get(cat, 0) + 1
    yaml_excl = {k for k, r in yaml_records.items() if r.get("excluded_m1")}
    print("[M1 范围]")
    print(f"  QFC 中 M1 外条目: {len(qfc_m1_out)}"
          + (f"（{', '.join(f'{k}={v}' for k, v in sorted(qfc_cats.items()))}）"
             if qfc_cats else ""))
    print(f"  yaml 中 excluded_m1 条目: {len(yaml_excl)}")
    if set(qfc_m1_out) == yaml_excl:
        print("  → QFC 与 yaml 的 M1 外条目集合一致")
    else:
        print(f"  ! QFC 与 yaml 的 M1 外条目集合不一致: "
              f"仅 QFC {len(set(qfc_m1_out) - yaml_excl)}，"
              f"仅 yaml {len(yaml_excl - set(qfc_m1_out))}")
    print()

    print("[汇总]")
    print(f"  QFC 指令数: {len(qfc_opids)}")
    print(f"  YAML 指令数: {len(yaml_opids)}")
    print(f"  差异总数: {len(qfc_only) + len(yaml_only)}（M1 内: {m1_in_diffs}，"
          f"M1 外: {len(qfc_only) + len(yaml_only) - m1_in_diffs}）")
    if m1_in_diffs:
        print(f"  ! 存在 {m1_in_diffs} 条 M1 内差异——须人工核查编码表/规范")
    elif not qfc_only and not yaml_only:
        print("  OK: QFC 表与 opcodes.yaml 双向完全一致")
    else:
        print("  OK: 所有差异均为 M1 范围外（已知排除项）")
    print()

    print("check_qfc_coverage: done (informational, exit 0)")
    sys.exit(0)


if __name__ == "__main__":
    main()
