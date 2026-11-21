#!/usr/bin/env python3
"""check_boot_contract.py — 启动 ABI 三方一致性门控（`m14-spec-001`／`m14-spec-003`）。

校验对象（Spec-first；期望值一律**现场派生**，不写死条数）：
  * `spec/Kaiwu-测试机运行环境.md` **§6.3**（规范正文，唯一真源）
  * `.tao/contracts/contract-linux-boot.md`（人读契约 0.2.0）
  * `contracts/linux-boot.yaml`（机器可读投影）

断言（任一不满足 ⇒ 非零退出）：
  1. boot info 表：正文 `§6.3` 表 ↔ 契约 §4 表 ↔ YAML `boot_info.fields`
     **逐字段**（偏移/宽度/字段名/取值）相等，且行数相等；
  2. boot info 布局：偏移递增不重叠、宽度 ∈ {1,2,4,8}、自然对齐、
     `max(offset+width) == size`、`size ≤ 页大小`、`va` 页对齐；
  2b. 地址术语与启动模型（用户 2026-11-13 裁定）：正文/契约须逐项出现
     `address_model.required_terms`（`VA`/`addr[41:0]`/`ptw_enable`/`PTBR`/`CFXMEM`/
     `预建`/`2 TiB`/`VA = PA + 2 TiB`），且不得出现 `forbidden_terms`（旧口径与**旧地址**，
     回潮即 FAIL）；boot info 的 `kind: va` 字段语义须写 VA、`kind: pa` 字段（`ptbr`）须写 PA；
     启动模型页大小/`ptw_enable`/寄存器与 YAML 一致；
  2c. **内核窗口与偏置（硬断言）**：`va_pa_offset == 2 TiB`、`va_layout.kernel = [2 TiB, 3 TiB)`、
     用户空间终点接内核窗口起点、正文与契约明写 `[2 TiB, 3 TiB)`；每个固定分区的
     `VA − PA == va_pa_offset`（即 `VA = PA + 2 TiB`）、全部落在内核窗口内；`ram_base` ==
     内核窗口起点；正文/契约的预建页表映射 == 内核窗口基址 + 1 个 512 MiB 超页；
  3. 内存分区：正文 `§6.3` 表 ↔ 契约 §2 表 ↔ YAML `memory_map`（区间/大小/用途）相等；
     区间与大小由 YAML 数值**现场格式化**，不读正文里的字面量；
  4. 进入时状态：正文表 ↔ 契约表 ↔ YAML `entry_state` 相等；
  5. 装载规则：YAML `rules` 的 id 集合/顺序 == 契约规则表 id；`rule` 文本与契约
     「规定」列逐字相等；每个 id 在正文 `§6.3` 与契约中**各出现且仅一次**；
  6. 交叉：`kernel_base`/`initramfs_base`/`ptbr`/`ram_base` 与对应分区起点（`ptbr` 比 PA 侧）、
     页表页大小 == `1 << page_size_log2`，各分区不越过 `ram_base + ram_size`；
  7. `not_defined` 的每项在正文与契约的「不定义」句中**逐项点名**；
  8. 全册无「设备树/DTB/DTS 由本机传入」类表述：正文中提及 设备树/DTB/DTS 的行，
     只允许落在 `§6.3` 且含否定措辞（不引入/不得按/不定义/不是/无），或落在
     版本附录（历史）内；
  9. YAML 的 `display` 与 `value` 回读一致（dev 值不得与 `value` 脱钩）。

用法：
  python3 tests/unit/linux/check_boot_contract.py [--root DIR]
  python3 tests/unit/linux/check_boot_contract.py --self-test     # 注入自检（临时树；不碰真实文件）

退出码：0 = 全部一致；1 = 有不一致 / 自检失败；2 = 输入缺失或无法解析。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

SPEC_REL = Path("spec/Kaiwu-测试机运行环境.md")
CONTRACT_REL = Path(".tao/contracts/contract-linux-boot.md")
YAML_REL = Path("contracts/linux-boot.yaml")

MIB = 1 << 20
KIB = 1 << 10

APPENDIX_RE = re.compile(r"^##\s+附录：版本与变更记录\s*$")
DTB_RE = re.compile(r"设备树|DTB|DTS")
DTB_NEGATIONS = ("不引入", "不得按", "不定义", "不是 DTB", "无 DTB")
PA_RE = re.compile(r"(?<![A-Za-z])PA(?![A-Za-z])")


# ── 通用工具 ────────────────────────────────────────────────────────────────

def norm(cell: str) -> str:
    """单元格归一化：去反引号、折叠空白（排版差异不算语义差异）。"""
    return re.sub(r"\s+", " ", cell.replace("`", "")).strip()


def fmt_addr(value: int) -> str:
    """地址格式（VA/PA 通用）：0x + 4 位一组下划线（`0x0001_0000` / `0x0200_0000_0000` 形）。"""
    digits = f"{value:08x}"
    if len(digits) % 4:
        digits = digits.rjust((len(digits) + 3) // 4 * 4, "0")
    groups = [digits[i:i + 4] for i in range(0, len(digits), 4)]
    return "0x" + "_".join(groups)


def fmt_size(size: int) -> str:
    if size % MIB == 0:
        return f"{size // MIB} MiB"
    if size % KIB == 0:
        return f"{size // KIB} KiB"
    return f"{size} B"


def split_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [c.strip() for c in text.split("|")]


def is_separator(line: str) -> bool:
    cells = split_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells)


def parse_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = text.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i])
                i += 1
            header = split_row(block[0])
            rows = [split_row(l) for l in block[1:] if not is_separator(l)]
            rows = [r for r in rows if any(c for c in r)]
            tables.append((header, rows))
        else:
            i += 1
    return tables


def pick_table(tables, header: list[str], what: str):
    want = [norm(h) for h in header]
    hits = [t for t in tables if [norm(h) for h in t[0]] == want]
    if not hits:
        raise ValueError(f"未找到表头为 {header} 的表格（{what}）")
    return hits


def section_block(text: str, heading_prefix: str) -> str:
    """取以 `heading_prefix` 起始的 `###` 小节正文（到下一个 `##`/`###` 为止）。"""
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.startswith(heading_prefix):
            start = idx
            break
    if start is None:
        return ""
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## ") or lines[idx].startswith("### "):
            end = idx
            break
    return "\n".join(lines[start:end])


def parse_int(cell: str, what: str) -> int:
    text = norm(cell)
    if not text.startswith("0x"):
        raise ValueError(f"{what}: 期望十六进制字面量，实际 {cell!r}")
    return int(text, 16)


def check_display(field: dict) -> str | None:
    """`display` 与 `value` 回读一致；返回错误串或 None。"""
    display = norm(str(field.get("display", "")))
    value = field.get("value")
    if value == "runtime":
        return None if display == "运行期" else f"{field['name']}: runtime 的 display 应为 运行期，实际 {display!r}"
    if not display:
        return f"{field['name']}: 缺 display"
    try:
        shown = int(display, 16) if display.startswith("0x") else int(display, 10)
    except ValueError:
        return f"{field['name']}: display 不可解析为整数: {display!r}"
    if shown != value:
        return f"{field['name']}: display {display!r} ≠ value {value!r}"
    return None


# ── 主检查 ──────────────────────────────────────────────────────────────────

class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.stats: list[str] = []

    def ok(self, name: str, expected, actual) -> None:
        print(f"  [PASS] {name} | expected={expected} actual={actual}")

    def bad(self, name: str, expected, actual) -> None:
        print(f"  [FAIL] {name} | expected={expected} actual={actual}")
        self.fails.append(name)

    def check(self, name: str, expected, actual) -> None:
        if expected == actual:
            self.ok(name, expected, actual)
        else:
            self.bad(name, expected, actual)

    def stat(self, text: str) -> None:
        self.stats.append(text)
        print(f"  [STAT] {text}")


def run_checks(root: Path) -> tuple[int, Report]:
    rep = Report()
    spec_path = root / SPEC_REL
    contract_path = root / CONTRACT_REL
    yaml_path = root / YAML_REL
    for path in (spec_path, contract_path, yaml_path):
        if not path.is_file():
            print(f"ERROR: 输入缺失: {path}", file=sys.stderr)
            return 2, rep

    spec_text = spec_path.read_text(encoding="utf-8")
    contract_text = contract_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    block = section_block(spec_text, "### 6.3 ")
    if not block:
        print("ERROR: 正文缺 §6.3 小节", file=sys.stderr)
        return 2, rep
    rep.stat(f"§6.3 正文行数（现场统计）={len(block.splitlines())}")

    spec_tables = parse_tables(block)
    contract_tables = parse_tables(contract_text)

    # ── 1. boot info 逐字段 ────────────────────────────────────────────────
    try:
        spec_bi = pick_table(spec_tables, ["偏移", "宽度", "字段", "值", "语义"], "正文 §6.3 boot info")[0][1]
        contract_bi = pick_table(contract_tables, ["偏移", "宽度", "字段", "值", "语义"], "契约 §4")[0][1]
    except ValueError as exc:
        rep.bad("boot-info-table", "表存在", str(exc))
        spec_bi, contract_bi = [], []
    fields = data["boot_info"]["fields"]

    rep.check("boot-info 行数 正文==YAML", len(fields), len(spec_bi))
    rep.check("boot-info 行数 契约==YAML", len(fields), len(contract_bi))
    n = min(len(spec_bi), len(contract_bi), len(fields))
    for i in range(n):
        f = fields[i]
        exp = (f["offset"], f["width"], f["name"], norm(f["display"]))
        s = (parse_int(spec_bi[i][0], "正文偏移"), int(norm(spec_bi[i][1])), norm(spec_bi[i][2]), norm(spec_bi[i][3]))
        c = (parse_int(contract_bi[i][0], "契约偏移"), int(norm(contract_bi[i][1])), norm(contract_bi[i][2]), norm(contract_bi[i][3]))
        sem_s, sem_c = norm(spec_bi[i][4]), norm(contract_bi[i][4])
        rep.check(f"boot-info[{i}] 正文==YAML", exp, s)
        rep.check(f"boot-info[{i}] 契约==YAML", exp, c)
        rep.check(f"boot-info[{i}] 语义列 正文==契约", sem_s, sem_c)
        kind = f.get("kind")
        if kind == "va":
            rep.check(f"boot-info[{i}] {f['name']} 语义标注 VA", True, "VA" in sem_s and "VA" in sem_c)
            rep.check(f"boot-info[{i}] {f['name']} 语义不得写 PA", False,
                      bool(PA_RE.search(sem_s)) or bool(PA_RE.search(sem_c)))
        elif kind == "pa":
            rep.check(f"boot-info[{i}] {f['name']} 语义标注 PA", True, "PA" in sem_s and "PA" in sem_c)
        elif kind not in ("scalar", "runtime"):
            rep.bad(f"boot-info[{i}] kind", "va/pa/scalar/runtime", kind)

    # ── 2. boot info 布局 ─────────────────────────────────────────────────
    bi = data["boot_info"]
    offsets_ok = True
    prev_end = 0
    for f in fields:
        off, width = f["offset"], f["width"]
        if width not in (1, 2, 4, 8):
            rep.bad(f"{f['name']} 宽度", "∈{1,2,4,8}", width)
            offsets_ok = False
        if off % width != 0:
            rep.bad(f"{f['name']} 自然对齐", f"offset % {width} == 0", off)
            offsets_ok = False
        if off < prev_end:
            rep.bad(f"{f['name']} 不重叠", f">= {prev_end}", off)
            offsets_ok = False
        prev_end = max(prev_end, off + width)
    rep.check("boot-info 偏移递增不重叠/自然对齐", True, offsets_ok)
    rep.check("boot-info max(offset+width) == size", bi["size"], prev_end)

    by_name = {f["name"]: f for f in fields}
    page_log2 = by_name["page_size_log2"]["value"]
    page_size = 1 << page_log2
    rep.check("boot-info size ≤ 页大小", True, bi["size"] <= page_size)
    rep.check("boot-info va 页对齐", 0, bi["va"] % page_size)
    rep.check("boot-info 顶部 size == size 字段值", bi["size"], by_name["size"]["value"])
    rep.check("端序声明", "big", bi["endianness"])
    rep.check("正文 §6.3 明写 boot info VA", True, fmt_addr(bi["va"]) in block)
    rep.check("契约 §4 明写 boot info VA", True, fmt_addr(bi["va"]) in contract_text)
    for f in fields:
        err = check_display(f)
        if err:
            rep.bad(f"{f['name']} display 回读", "display == value", err)

    # ── 2b. 地址术语与启动模型（用户 2026-11-13 裁定）────────────────────
    am = data["address_model"]
    sm = data["startup_model"]
    rep.check("地址模型：ABI 地址为 VA", "va", am["abi_addresses"])
    for term in am["required_terms"]:
        rep.check(f"正文 §6.3 术语 {term}", True, term in block)
        rep.check(f"契约术语 {term}", True, term in contract_text)
    for term in am["forbidden_terms"]:
        rep.check(f"正文 §6.3 无旧口径「{term}」", 0, block.count(term))
        rep.check(f"契约无旧口径「{term}」", 0, contract_text.count(term))
    rep.check("启动模型页大小 == 1 << page_size_log2", page_size, sm["page_size"])
    rep.check("启动模型 PTW 已开（ptw_enable=1）", 1, sm["ptw_enable"])
    rep.check("启动模型预建页表（非 loader 代写）", True, sm.get("prebuilt_page_table"))
    rep.check("启动模型入口寄存器", "rb16", sm["entry_register"])
    rep.check("启动模型 boot info 寄存器", "rb17", sm["boot_info_register"])
    rep.check("正文写明 ptw_enable=0 ⇒ CFXMEM（硬约束）", True,
              "CFXMEM" in block and "ptw_enable = 0" in block)

    # ── 2c. 内核 VA 窗口与 VA = PA + 2 TiB（硬断言；用户 2026-11-13 裁定）──
    va_layout = data["va_layout"]
    two_tib = 1 << 41
    rep.check("偏置 va_pa_offset == 2 TiB", two_tib, am["va_pa_offset"])
    rep.check("内核窗口起点 == 2 TiB", two_tib, va_layout["kernel"]["start"])
    rep.check("内核窗口终点 == 3 TiB", two_tib + (1 << 40), va_layout["kernel"]["end"])
    rep.check("用户空间起点 == 0", 0, va_layout["user"]["start"])
    rep.check("用户空间终点 == 内核窗口起点", va_layout["kernel"]["start"], va_layout["user"]["end"])
    window_text = "[2 TiB, 3 TiB)"
    rep.check("正文 §6.3 明写内核窗口 [2 TiB, 3 TiB)", True, window_text in block)
    rep.check("契约明写内核窗口 [2 TiB, 3 TiB)", True, window_text in contract_text)
    rep.check("ram_base == 内核窗口起点（VA）", va_layout["kernel"]["start"],
              by_name["ram_base"]["value"])
    sup = sm["superpage_size"]
    sm_map = (f"VA [{fmt_addr(va_layout['kernel']['start'])}, "
              f"{fmt_addr(va_layout['kernel']['start'] + sup)}) → PA [0, {fmt_addr(sup)})")
    rep.check("正文 §6.3 预建页表映射 == 窗口基址 1 个超页", True, sm_map in block)
    rep.check("契约预建页表映射 == 窗口基址 1 个超页", True, sm_map in contract_text)
    # 旧地址回潮：旧值 = 当前 VA − 偏置（现场派生，不写死字面量），不得再出现在正文/契约。
    legacy_pairs = (("boot info", bi["va"]),
                    ("kernel_base", by_name["kernel_base"]["value"]),
                    ("initramfs_base", by_name["initramfs_base"]["value"]))
    for what, va in legacy_pairs:
        legacy = fmt_addr(va - am["va_pa_offset"])
        rep.check(f"正文 §6.3 无旧地址（{what} 旧值 {legacy}）", 0, block.count(legacy))
        rep.check(f"契约无旧地址（{what} 旧值 {legacy}）", 0, contract_text.count(legacy))

    # ── 3. 内存分区 ────────────────────────────────────────────────────────
    mem = data["memory_map"]
    spec_mem = pick_table(spec_tables, ["区间（VA）", "大小", "用途"], "正文 §6.3 内存分区")[0][1]
    contract_mem = pick_table(contract_tables, ["区间（VA）", "大小", "用途"], "契约 §2")[0][1]
    rep.check("内存分区 行数 正文==YAML", len(mem), len(spec_mem))
    rep.check("内存分区 行数 契约==YAML", len(mem), len(contract_mem))
    for i, row in enumerate(mem[:min(len(spec_mem), len(contract_mem), len(mem))]):
        if row["start"] is None:
            span, size_cell = "其余", "—"
        else:
            span = f"[{fmt_addr(row['start'])}, {fmt_addr(row['end'])})"
            size_cell = fmt_size(row["end"] - row["start"])
        exp = (span, size_cell, norm(row["use"]))
        got_s = (norm(spec_mem[i][0]), norm(spec_mem[i][1]), norm(spec_mem[i][2]))
        got_c = (norm(contract_mem[i][0]), norm(contract_mem[i][1]), norm(contract_mem[i][2]))
        rep.check(f"内存分区[{i}] 正文==YAML", exp, got_s)
        rep.check(f"内存分区[{i}] 契约==YAML", exp, got_c)

    for row in mem:
        if "boot info" in norm(row["use"]):
            rep.check(f"分区 {row['name']} 描述不得写 PA", False, bool(PA_RE.search(row["use"])))

    rows_by_name = {r["name"]: r for r in mem}
    reps = rows_by_name.get("rest")
    if reps is not None and reps["start"] is not None:
        rep.bad("内存分区 rest 行", "start=null", reps["start"])
    # 交叉：字段 ↔ 分区起点（`ptbr` 是 PA，比 PA 侧）
    for fname, row_name in (("kernel_base", "kernel"), ("initramfs_base", "initramfs")):
        rep.check(f"字段 {fname} == 分区 {row_name} 起点",
                  rows_by_name[row_name]["start"], by_name[fname]["value"])
    rep.check("字段 boot_info.va == 分区 boot_info 起点",
              rows_by_name["boot_info"]["start"], bi["va"])
    rep.check("字段 ptbr == 分区 page_table 的 PA 起点（PTBR 记 PA）",
              rows_by_name["page_table"]["pa_start"], by_name["ptbr"]["value"])
    rep.check("分区 page_table 的 VA 起点 == 偏置", am["va_pa_offset"],
              rows_by_name["page_table"]["start"])
    rep.check("页表页大小 == 1 << page_size_log2", page_size,
              rows_by_name["page_table"]["end"] - rows_by_name["page_table"]["start"])
    # 交叉：VA = PA + offset、落在内核窗口内、不越过 RAM 上限
    for row in mem:
        if row["start"] is None:
            continue
        rep.check(f"分区 {row['name']} VA − PA == 偏置（VA = PA + 2 TiB）", am["va_pa_offset"],
                  row["start"] - row["pa_start"])
        rep.check(f"分区 {row['name']} 落在内核窗口内", True,
                  va_layout["kernel"]["start"] <= row["start"]
                  and row["end"] <= va_layout["kernel"]["end"])
    limit = by_name["ram_base"]["value"] + by_name["ram_size"]["value"]
    for row in mem:
        if row["start"] is not None:
            rep.check(f"分区 {row['name']} 不越过 ram 上限", True, row["end"] <= limit)

    # ── 4. 进入时状态 ─────────────────────────────────────────────────────
    state = data["entry_state"]
    spec_state = pick_table(spec_tables, ["项", "值"], "正文 §6.3 进入时状态")[0][1]
    contract_state = pick_table(contract_tables, ["项", "值"], "契约 §5")[0][1]
    rep.check("进入时状态 行数 正文==YAML", len(state), len(spec_state))
    rep.check("进入时状态 行数 契约==YAML", len(state), len(contract_state))
    for i, row in enumerate(state[:min(len(spec_state), len(contract_state), len(state))]):
        exp = (norm(row["item"]), norm(row["value"]))
        rep.check(f"进入状态[{i}] 正文==YAML", exp, (norm(spec_state[i][0]), norm(spec_state[i][1])))
        rep.check(f"进入状态[{i}] 契约==YAML", exp, (norm(contract_state[i][0]), norm(contract_state[i][1])))

    entry_by_item = {norm(r["item"]): norm(r["value"]) for r in state}
    ptw_cell = entry_by_item.get("PTW", "")
    rep.check("进入状态 PTW 含 ptw_enable/PTBR/偏置", True,
              all(t in ptw_cell for t in ("ptw_enable", "PTBR", "VA = PA + 2 TiB")))
    rep.check("进入状态 rb17 == boot info VA", True,
              fmt_addr(bi["va"]) in entry_by_item.get("rb17", ""))
    rep.check("进入状态 rb16 == 入口 VA", True,
              fmt_addr(by_name["kernel_base"]["value"]) in entry_by_item.get("rb16", ""))
    rep.check("进入状态 rb17 标注 boot info VA", True, "boot info VA" in entry_by_item.get("rb17", ""))
    rep.check("进入状态 hart 写明其它 hart 未定义", True, "其它 hart" in entry_by_item.get("hart", ""))

    # ── 5. 装载规则 ───────────────────────────────────────────────────────
    rules = data["rules"]
    contract_rows: list[list[str]] = []
    for header, rows in contract_tables:
        if [norm(h) for h in header] == ["规则", "规定", "来源"]:
            contract_rows.extend(rows)
    rep.check("规则 条数（YAML/契约表）", len(rules), len(contract_rows))
    yaml_ids = [r["id"] for r in rules]
    contract_ids = [norm(r[0]) for r in contract_rows]
    rep.check("规则 id 集合/顺序", yaml_ids, contract_ids)
    for rule, row in zip(rules, contract_rows):
        if norm(row[0]) != rule["id"]:
            continue
        rep.check(f"规则 {rule['id']} 规定文本", norm(rule["rule"]), norm(row[1]))
        rep.check(f"规则 {rule['id']} 正文唯一断言句", 1, block.count(rule["id"]))
        rep.check(f"规则 {rule['id']} 契约出现次数", 1, contract_text.count(rule["id"]))
    cats: dict[str, int] = {}
    for r in rules:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    rep.stat("规则分类计数（现场统计）=" + ", ".join(f"{k}:{v}" for k, v in sorted(cats.items())))

    # ── 6. 不定义范围逐项点名 ─────────────────────────────────────────────
    for token in data["not_defined"]:
        line = next((l for l in block.splitlines() if "不定义" in l and token in l), "")
        rep.check(f"正文不定义句点名 {token}", True, bool(line))
        line_c = next((l for l in contract_text.splitlines() if "不定义" in l and token in l), "")
        rep.check(f"契约不定义句点名 {token}", True, bool(line_c))

    # ── 7. 全册无「由本机传入设备树」类表述 ──────────────────────────────
    lines = spec_text.splitlines()
    app = next((i for i, l in enumerate(lines) if APPENDIX_RE.match(l)), len(lines))
    block_start = next(i for i, l in enumerate(lines) if l.startswith("### 6.3 "))
    block_end = block_start + len(block.splitlines())
    hits = 0
    for i, line in enumerate(lines):
        if not DTB_RE.search(line):
            continue
        hits += 1
        if i >= app:
            continue  # 历史附录：只作记录
        in_block = block_start <= i < block_end
        negated = any(neg in line for neg in DTB_NEGATIONS)
        rep.check(f"L{i + 1} 设备树/DTB 提及须为 §6.3 否定句", True, in_block and negated)
    rep.stat(f"设备树/DTB/DTS 提及行数（现场统计）={hits}")

    print()
    for s in rep.stats:
        print(f"  [SUM] {s}")
    return (0 if not rep.fails else 1), rep


# ── 自检：6 类注入（临时树） ────────────────────────────────────────────────

INJECTIONS = [
    {
        "name": "偏移错（正文 §6.3 boot info 的 version 偏移 0x04 → 0x05）",
        "file": SPEC_REL,
        "old": "| `0x04` | 2 | `version` |",
        "new": "| `0x05` | 2 | `version` |",
    },
    {
        "name": "magic 错（契约 §4 的 magic 值 0x4442_494E → 0x4442_494F）",
        "file": CONTRACT_REL,
        "old": "| `0x00` | 4 | `magic` | `0x4442_494E` |",
        "new": "| `0x00` | 4 | `magic` | `0x4442_494F` |",
    },
    {
        "name": "入口/基址错（YAML kernel_base 0x20000100000 → 0x20000101000）",
        "file": YAML_REL,
        "old": "value: 0x20000100000",
        "new": "value: 0x20000101000",
    },
    {
        "name": "字段缺失（契约 §4 删 cmdline_size 行）",
        "file": CONTRACT_REL,
        "old": "| `0x40` | 8 | `cmdline_size` | `0` | K0 无命令行，保留字段 |\n",
        "new": "",
    },
    {
        "name": "术语缺失（正文 §6.3 把 CFXMEM 写成 CFXPERM）",
        "file": SPEC_REL,
        "old": "**直接报 `CFXMEM`**",
        "new": "**直接报 `CFXPERM`**",
    },
    {
        "name": "地址术语回退（boot info 页改称「固定 PA」）",
        "file": SPEC_REL,
        "old": "boot info 页（固定 VA `0x0200_0001_0000`",
        "new": "boot info 页（固定 PA `0x0200_0001_0000`",
    },
    {
        "name": "旧地址回潮（契约 kernel_base 改回旧值 0x0010_0000）",
        "file": CONTRACT_REL,
        "old": "| `0x18` | 8 | `kernel_base` | `0x0200_0010_0000` |",
        "new": "| `0x18` | 8 | `kernel_base` | `0x0010_0000` |",
    },
    {
        "name": "偏置回潮（YAML va_pa_offset 2 TiB → 1 TiB）",
        "file": YAML_REL,
        "old": "va_pa_offset: 0x20000000000",
        "new": "va_pa_offset: 0x10000000000",
    },
]


def self_test() -> int:
    here = ROOT
    tmp = Path(tempfile.mkdtemp(prefix="boot-contract-selftest-"))
    try:
        for rel in (SPEC_REL, CONTRACT_REL, YAML_REL):
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(here / rel, dst)
        original = {rel: (here / rel).read_text(encoding="utf-8") for rel in (SPEC_REL, CONTRACT_REL, YAML_REL)}

        print("── self-test 基线（未注入应 PASS）──")
        rc, _ = run_checks(tmp)
        if rc != 0:
            print(f"self-test: 基线未通过（rc={rc}）", file=sys.stderr)
            return 1

        failures = 0
        for inj in INJECTIONS:
            rel: Path = inj["file"]
            path = tmp / rel
            text = original[rel]
            count = text.count(inj["old"])
            print(f"\n── self-test 注入：{inj['name']}（命中 {count} 处）──")
            if count != 1:
                print("  [FAIL] 注入点不唯一，判据失效", file=sys.stderr)
                failures += 1
                continue
            path.write_text(text.replace(inj["old"], inj["new"]), encoding="utf-8")
            rc_bad, rep_bad = run_checks(tmp)
            print(f"  [{'PASS' if rc_bad != 0 else 'FAIL'}] 注入后应非零退出 | expected=rc!=0 actual=rc={rc_bad}")
            if rc_bad == 0:
                failures += 1
            path.write_text(original[rel], encoding="utf-8")
            rc_good, _ = run_checks(tmp)
            print(f"  [{'PASS' if rc_good == 0 else 'FAIL'}] 还原后应回绿 | expected=rc=0 actual=rc={rc_good}")
            if rc_good != 0:
                failures += 1

        print(f"\nself-test: {len(INJECTIONS)} 类注入，失败 {failures} 项")
        return 0 if failures == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 ABI 三方一致性门控")
    parser.add_argument("--root", type=Path, default=ROOT, help="仓库根（默认本脚本上两级）")
    parser.add_argument("--self-test", action="store_true", help="6 类注入自检（临时树）")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    print("── 启动 ABI 三方一致性检查（§6.3 ↔ contract-linux-boot.md ↔ linux-boot.yaml）──")
    rc, rep = run_checks(args.root)
    print(f"\n结果：{'PASS' if rc == 0 else 'FAIL'}（失败项 {len(rep.fails)}，退出码 {rc}）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
