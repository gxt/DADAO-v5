#!/usr/bin/env python3
"""validate_vectors.py — `tests/inst` 的载体结构、inventory 同步与覆盖率声明门控。

Spec-first：判定依据 `contracts/opcodes.yaml` 与 `tests/inst/inventory.md`；**不**读取
LLVM/QEMU 产物，不从实现反推。

载体模型（`ISS-413` / `m13-testcases-030`；YAML 载体已于 `m13-testcases-043` 全退役）：
  * **`.S`**（`tests/inst/<册>/<id>.S`）是**唯一**执行型载体：类级/逐例覆盖由 L2
    `make check-inst-asm` 逐镜像执行承担（链例比结果字节流、故障例比 monitor 段退出码）。
    本脚本只断言载体**结构完好**：
      - stem 是 `contracts/opcodes.yaml` 的**任一** scope 身份（拼错/孤儿 ⇒ 报错）；
      - 同一 stem 只能有一个 `.S`（`run_asm_suite` 按 stem 去重会让第二份静默失效）；
      - 含 ≥1 用例行（链例或故障例），检查点号 1..N 连续（复用
        `run_asm_suite.scan_source`，与执行门控同一真源）；
      - **非 id 载体**（文件 stem 不是 opcode 身份，如保留编码）必须在
        `NON_ID_CARRIERS` **显式登记**并由 `tests/inst.yaml` 索引（不做目录级豁免）。
  * inventory 的 `file` 列必须指向现场存在的载体（basename 在 `tests/inst/<册>/` 下唯一命中）。
  * inventory 的 M1 行集 == `contracts/opcodes.yaml` 的 `scope == "m1"` 身份集（无缺/无多/无重复）；
    每行至少声明一类覆盖（不得静默缺席）。

YAML 逐 case 校验（schema/类级覆盖）与两条 `br.*` 守卫（PC 期望必须存在、
taken+not-taken 双路径）已随 YAML 退役删除（原守卫判据见 `tests/inst/MIGRATION.md §5.5`）：
br 双路径覆盖改由**执行证据**承担
（`.S` 的 `__LAND_IP` 查目标 IP + 三平台跑批，见 `tests/inst/MIGRATION.md`）。

退出码：有错误 `exit(1)` 并列出载体/行；无错误 `exit(0)`。
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "inst"))
# `.S` 载体的结构扫描与 L2 执行门控（`check-inst-asm`）**同一真源**：点号/用例行
# 的解析只在这里写一次，避免「门控和 validator 各认一套语法」。
import run_asm_suite  # noqa: E402

# 非 opcode 身份的载体（**显式登记**，逐文件；不得放宽成「某目录下任意 `.S` 豁免」）。
# 键 = 相对仓库根的 posix 路径，值 = 理由。登记项必须：现场存在、含用例行、
# 由 `tests/inst.yaml` 索引（`check-tests-index` 的载体↔索引双向断言）。
NON_ID_CARRIERS = {
    "tests/inst/00-isa-design/undi_reserved.S":
        "保留编码（QFC 空白格）⇒ UNDI；无 opcode 身份，索引 id = inst-00-isa-design-001",
    "tests/inst/00-isa-design/pseudo_set.rd_imm.S":
        "伪指令 set.rd rd, imm64 的展开；伪指令不是硬件指令（SimRISC-00 §5），"
        "索引 id = inst-00-isa-design-002",
    "tests/inst/00-isa-design/pseudo_set.rd_reg.S":
        "伪指令 set.rd rd, rs 的展开（rb2rd/rf2rd/ra2rd/rd2rd），"
        "索引 id = inst-00-isa-design-003",
    "tests/inst/00-isa-design/pseudo_set.rb_imm.S":
        "伪指令 set.rb rb, imm64 的展开（rb 无 set.ow），"
        "索引 id = inst-00-isa-design-004",
    "tests/inst/00-isa-design/pseudo_set.rb_reg.S":
        "伪指令 set.rb rb, rs 的展开（rd2rb/rb2rb），"
        "索引 id = inst-00-isa-design-005",
    "tests/inst/00-isa-design/pseudo_set.ft_imm32.S":
        "伪指令 set.ft rf, imm32 的展开（2× set.w，窄写：高 32 保持），"
        "索引 id = inst-00-isa-design-006",
    "tests/inst/00-isa-design/pseudo_set.fo_imm64.S":
        "伪指令 set.fo rf, imm64 的展开（整 64 位；imm=0 ⇒ rd2rf rd0），"
        "索引 id = inst-00-isa-design-007",
    "tests/inst/00-isa-design/pseudo_set.rf_reg.S":
        "伪指令 set.rf rf, rs 的展开（rd2rf/rf2rf，整 64 位：高 32 被覆盖），"
        "索引 id = inst-00-isa-design-008",
    "tests/inst/00-isa-design/atomic_rmw.S":
        "原子 RMW 的合成序（lr→计算→sc→失败重试），跨 24 条 lr/sc 身份而非单个 id"
        "⇒ 无 opcode 身份，索引 id = inst-00-isa-design-009",
}

DECL_NA = {"", "—", "-", "n/a", "na", "none"}
CLASSES = ("encoding", "legality", "semantic", "boundary", "overlap")


def _unquote(cell):
    return cell.strip().strip("`").strip()


def load_opcodes(path):
    """返回 (m1_records, by_id, duplicate_ids, all_records)。"""
    with open(path) as fh:
        records = _yaml.safe_load(fh)
    if not isinstance(records, list):
        raise ValueError("opcodes.yaml top-level must be a list")
    m1 = [r for r in records if r.get("scope") == "m1"]
    by_id = {}
    dups = []
    for rec in m1:
        rid = rec["id"]
        if rid in by_id:
            dups.append(rid)
        by_id[rid] = rec
    return m1, by_id, dups, records


def parse_inventory(path):
    """解析 inventory.md 中含 `id`+`format` 表头的 Markdown 表。"""
    rows = []
    header = None
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line.startswith("|"):
                header = None
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            low = [c.lower() for c in cells]
            if "id" in low and "format" in low:
                header = low
                continue
            if header is None:
                continue
            if cells and all(set(c) <= set("-: ") and "-" in c for c in cells):
                continue
            row = {header[i]: cells[i] for i in range(min(len(header), len(cells)))}
            rows.append(row)
    return rows


def scan_asm_carriers(repo_dir, known_ids, errors):
    """现场扫描 `.S` 载体：返回 {id: 相对路径}（结构与孤儿断言，fail-closed）。"""
    out = {}
    for path in sorted(glob.glob(os.path.join(repo_dir, "tests", "inst", "*", "*.S"))):
        stem = os.path.basename(path)[:-2]
        rel = os.path.relpath(path, repo_dir).replace(os.sep, "/")
        registered = rel in NON_ID_CARRIERS
        if stem in out:
            errors.append("ASM CARRIER DUPLICATE: id '%s' 有多个 .S 载体（%s / %s）"
                          % (stem, out[stem], rel))
            continue
        if stem not in known_ids:
            if not registered:
                errors.append(
                    "ASM CARRIER ORPHAN: %s 的 stem '%s' 不是 opcodes.yaml 的身份"
                    "（若非 id 载体，须在 validate_vectors.NON_ID_CARRIERS 显式登记）"
                    % (rel, stem))
                continue
        info = run_asm_suite.scan_source(Path(path))
        if not info["checks"] and not info["faults"]:
            errors.append("ASM CARRIER EMPTY: %s 没有用例行（链例/故障例均 0）" % rel)
            continue
        if not info["pts_ok"]:
            errors.append("ASM CARRIER POINTS: %s 检查点号不是 1..N 连续"
                          "（失败点号 ≠ 用例序号）" % rel)
        out[stem] = rel
    # 登记项必须现场存在（改名/删除登记载体 ⇒ 红，而不是静默失效）
    for rel in sorted(NON_ID_CARRIERS):
        if not os.path.isfile(os.path.join(repo_dir, rel)):
            errors.append("NON-ID CARRIER MISSING: 登记的非 id 载体不存在: %s" % rel)
    # 登记的目录不得有「未登记的 `.S`」——逐文件登记，不做目录级豁免
    for rel in sorted(NON_ID_CARRIERS):
        parent = os.path.dirname(os.path.join(repo_dir, rel))
        for path in sorted(glob.glob(os.path.join(parent, "*.S"))):
            other = os.path.relpath(path, repo_dir).replace(os.sep, "/")
            if other not in NON_ID_CARRIERS:
                errors.append(
                    "NON-ID CARRIER UNSET: %s 所在的非 id 载体目录里存在未登记的 .S: %s"
                    % (rel, other))
    return out


def main():
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "..", ".."))
    opcodes_path = os.path.join(repo_dir, "contracts", "opcodes.yaml")
    if not os.path.exists(opcodes_path):
        print("ERROR: contracts/opcodes.yaml not found", file=sys.stderr)
        sys.exit(1)

    try:
        _m1, by_id, dups, all_records = load_opcodes(opcodes_path)
    except (ValueError, KeyError) as exc:
        print("ERROR: cannot load contracts/opcodes.yaml: %s" % exc, file=sys.stderr)
        sys.exit(1)

    errors = []
    for rid in dups:
        errors.append("opcodes.yaml: duplicate M1 id '%s'" % rid)
    m1_keys = set(by_id)

    inventory_path = os.path.join(repo_dir, "tests", "inst", "inventory.md")
    if not os.path.exists(inventory_path):
        print("ERROR: tests/inst/inventory.md not found", file=sys.stderr)
        sys.exit(1)

    inv_rows = parse_inventory(inventory_path)
    inv_keys = set()
    declared = {}
    inv_files = {}
    for row in inv_rows:
        rid = _unquote(row.get("id", ""))
        if not rid:
            continue
        if rid in inv_keys:
            errors.append("inventory.md: duplicate row id '%s'" % rid)
            continue
        inv_keys.add(rid)
        cells = [_unquote(row.get(c, "")) for c in CLASSES]
        declared[rid] = any(c.lower() not in DECL_NA for c in cells)
        inv_files[rid] = _unquote(row.get("file", ""))

    # ── 载体：`.S` 现场索引 ──────────────────────────────────────────
    known_ids = {rec["id"] for rec in all_records if rec.get("id")}
    asm_carriers = scan_asm_carriers(repo_dir, known_ids, errors)

    # ── inventory `file` 列无悬空引用（载体 basename 必须现场存在）──────
    live_basenames = {os.path.basename(p)
                      for p in glob.glob(os.path.join(repo_dir, "tests", "inst",
                                                      "*", "*"))}
    for rid in sorted(inv_files):
        f = inv_files[rid]
        if not f or f.lower() in DECL_NA or f.lower().startswith("deferred"):
            continue
        if os.path.basename(f) not in live_basenames:
            errors.append("INVENTORY DANGLING CARRIER: '%s' 的 file 列 '%s' "
                          "在 tests/inst/<册>/ 下不存在" % (rid, f))

    # inventory 同步（R2）：M1 行集 == opcodes M1 身份集
    for rid in sorted(m1_keys - inv_keys):
        errors.append("INVENTORY MISSING: M1 id '%s' has no inventory.md row" % rid)
    for rid in sorted(inv_keys - m1_keys):
        errors.append("INVENTORY EXTRA: inventory.md row '%s' is not an M1 "
                      "identity" % rid)

    # 覆盖率声明：每个 M1 身份须在 inventory 中声明至少一类覆盖
    covered = 0
    for rid in m1_keys:
        if rid in inv_keys and declared.get(rid):
            covered += 1
        elif rid in inv_keys:
            errors.append("COVERAGE MISSING: '%s' has no coverage "
                          "declaration in inventory.md" % rid)

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print("validate_vectors: FAILED (%d error(s))" % len(errors), file=sys.stderr)
        sys.exit(1)

    print("validate_vectors: %d/%d M1 identities covered OK "
          "(inventory sync OK; %d .S carriers, %d non-id carriers)"
          % (covered, len(m1_keys), len(asm_carriers), len(NON_ID_CARRIERS)))
    sys.exit(0)


if __name__ == "__main__":
    main()
