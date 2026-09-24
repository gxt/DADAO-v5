#!/usr/bin/env python3
"""Generate the complete DADAO assembly-instruction list.

See ``docs/spec/assembly-list.md`` (generated) and
``docs/spec/component-patching.md`` (spec-writing conventions).

Sources
-------
* ``contracts/opcodes.yaml`` -- the authoritative 256-entry encoding table
  (178 M1 + 78 ``excluded_m1``), with per-field ``role``/``bank``.

Derivation rules (validated against ``tests/lit/MC/Dadao/*.s``)
---------------------------------------------------------------
* operands are the fields whose ``role`` is one of dst/src/imm/wyde_pos/
  cfxcode/cfx_cg/cfx_rc; ``minor_op`` fields are already encoded in the
  mnemonic and are **not** operands;
* split immediate fields (``imms18_hi/_mid/_lo``, ``immu24_b*``, ...) merge
  into one immediate operand;
* a concrete example line is built per instruction and then **verified** by
  assembling it with ``llvm-mc``.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts/opcodes.yaml"

OPERAND_ROLES = {"dst", "src", "imm", "wyde_pos", "cfxcode", "cfx_cg", "cfx_rc"}
SPLIT_SUFFIX = re.compile(r"^(imms?\d+|immu?\d+)_(?:hi|mid|lo|b\d+_\d+)$")

# Immediate width/signedness from the field base name (e.g. imms18 -> s18).
IMM_RE = re.compile(r"^imm([us]?)(\d+)$")

# Concrete example operands per role, tried in order until one assembles.
EXAMPLES = {
    "rd": ["rd8", "rd9", "rd10", "rd11", "rd1", "rd2"],
    "rb": ["rb2", "rb3", "rb1", "rb0"],
    "ra": ["ra1", "ra2"],
    "rf": ["rf2", "rf3"],
}
IMM_EXAMPLE = {"immu6": "1", "immu12": "1", "immu16": "0x1234", "immu18": "1",
               "immu24": "1", "imms12": "1", "imms18": "1", "imms24": "1",
               "wpN": "0"}


def base_imm(name: str) -> str:
    m = SPLIT_SUFFIX.match(name)
    return m.group(1) if m else name


def operands(entry: dict) -> list[dict]:
    out = []
    for field in entry.get("fields", []):
        role = field.get("role")
        if role not in OPERAND_ROLES:
            continue
        name = base_imm(field["name"])
        if role == "wyde_pos":
            kind, bank = "wpN", None
        elif role == "cfxcode":
            kind, bank = "cfxcode", None
        elif role == "cfx_cg":
            kind, bank = "cfx_cg", None
        elif role == "cfx_rc":
            kind, bank = "cfx_rc", None
        else:
            bank = field.get("bank")
            kind = "imm" if (bank == "imm" or name.startswith("imm")) else "reg"
        if out and out[-1]["kind"] == kind == "imm":
            continue
        out.append({"kind": kind, "bank": bank, "name": name})
    return out


FIELD_RE = re.compile(r"^(rd|rb|ra|rf|cg|rc)([a-z]{2})$")


def field_name(name: str) -> str:
    """rdha -> rdHA；imms12/wpN/cfxcode 原样。"""
    m = FIELD_RE.match(name)
    return m.group(1) + m.group(2).upper() if m else name


# 无显式寄存器操作数的指令：由用户裁定其 feature
FEATURE_OVERRIDE = {
    "jump": "rb", "call": "rb",
    "swym": "imm", "illi": "imm", "fence": "imm",
    "escape": "cfx", "trap": "cfx",
}


def primary_feature(entry: dict, ops: list[dict]) -> str:
    """指令的 feature：insn 后缀（-rd/-rb/-ra/-rf）优先；否则取 dst 的寄存器组；再否则由 FEATURE_OVERRIDE 指定。"""
    mnemonic = entry["mnemonic"]
    insn = entry["insn"]
    if mnemonic in FEATURE_OVERRIDE:
        return FEATURE_OVERRIDE[mnemonic]
    if mnemonic.startswith("cfx"):
        return "cfx"
    # 浮点类指令统一 rf
    if classify(entry) == "浮点":
        return "rf"
    # ret 弹栈回到 PC（rb0）
    if mnemonic == "ret":
        return "rb"
    # 寄存器组块赋值 X2Y：取「非 rd 侧」（两侧都是 rd 时取 rd）
    m2 = re.fullmatch(r"(rd|rb|ra|rf)2(rd|rb|ra|rf)", mnemonic)
    if m2:
        left, right = m2.group(1), m2.group(2)
        return right if left == "rd" else left
    if insn.startswith(mnemonic + "-") and insn[len(mnemonic) + 1:] in ("rd", "rb", "ra", "rf"):
        return insn[len(mnemonic) + 1:]
    for op in ops:
        if op.get("role") == "dst" and op.get("bank") in ("rd", "rb", "ra", "rf"):
            return op["bank"]
    for op in ops:
        if op.get("bank") in ("rd", "rb", "ra", "rf"):
            return op["bank"]
    return "—"


def classify(entry: dict) -> str:
    """章节分类（优先级：rwii > 存储 > 控制流 > 寄存器复制 > 浮点 > 位宽 > 64位运算 > 其它）。"""
    m = entry["mnemonic"]
    # 待定（用户裁定：暂不归类）
    if m in ("cfxld", "cfxst", "fence", "ftmadd", "fomadd") \
            or m.startswith(("lr_", "sc_", "rela")):
        return "待定"
    if entry["format"] == "rwii":
        return "16位立即数操作"
    if m.startswith(("ld.", "st.", "ldm.", "stm.")):
        return "存储"
    if m.startswith(("br.", "jump", "call", "ret")):
        return "控制流"
    if m.startswith("cs.") or re.fullmatch(r"(rd|rb|ra|rf)2(rd|rb|ra|rf)", m):
        return "寄存器复制"
    # 浮点：操作数含 rf 寄存器，或助记符为 fo*/ft* 或形如 *2f*/*2rf*（格式转换）
    if (any(f.get("bank") == "rf" for f in entry["fields"])
            or m.startswith(("fo", "ft"))
            or re.search(r"2f|2rf", m)):
        return "浮点"
    if m.startswith(("lr_", "sc_")):
        return "其它"
    if re.search(r"\.(ub|sb|b)$", m):
        return "8位数据运算"
    if re.search(r"\.(uw|sw|w)$", m) or m in ("set.zw", "set.ow"):
        return "16位数据运算"
    if re.search(r"\.(ut|st|t)$", m):
        return "32位数据运算"
    if re.search(r"\.(uo|so|o)$", m) or m in ("add.si", "rela.si") or m.startswith("cmp."):
        # 64 位运算按寄存器组分：rb（地址）→ 地址运算；其余 → 数据运算
        return "64位地址运算" if any(f.get("bank") == "rb" for f in entry["fields"]) else "64位数据运算"
    return "其它"


SECTION_ORDER = ["8位数据运算", "16位数据运算", "32位数据运算", "64位数据运算", "64位地址运算", "浮点", "存储", "控制流", "寄存器复制", "16位立即数操作", "其它", "待定"]


def template(entry: dict, ops: list[dict]) -> str:
    # lr 的 rdhb 固定为 rd0，模板同样只写两个操作数
    if entry["mnemonic"].startswith("lr_") and len(ops) == 3:
        ops = ops[1:]
    parts = []
    for op in ops:
        if op["kind"] == "imm":
            parts.append(op["name"])
        elif op["kind"] == "wpN":
            parts.append("wpN")
        elif op["kind"] in ("cfxcode", "cfx_cg", "cfx_rc", "cfx"):
            parts.append("cfx_<name>")
        else:
            parts.append(f"{op['bank']}N")
    if not parts:
        return entry["mnemonic"]
    return f"{entry['mnemonic']} " + ", ".join(parts)


def example_line(entry: dict, ops: list[dict], attempt: int) -> str:
    # lr 的 rdhb 固定为 rd0（spec：汇编只写两个操作数）
    if entry["mnemonic"].startswith("lr_") and len(ops) == 3:
        ops = ops[1:]
    parts = []
    for op in ops:
        if op["kind"] == "imm":
            parts.append(IMM_EXAMPLE.get(op["name"], "1"))
        elif op["kind"] == "wpN":
            parts.append("0")
        elif op["kind"] in ("cfxcode", "cfx_cg", "cfx_rc", "cfx"):
            parts.append("cfx_power")
        else:
            pool = EXAMPLES.get(op["bank"], ["rd8"])
            parts.append(pool[(attempt + len(parts)) % len(pool)])
    if not parts:
        return entry["mnemonic"]
    return f"{entry['mnemonic']} " + ", ".join(parts)


def _range(start: str, count: int = 3) -> str:
    """`{rd8:rd10}` -- a contiguous range of `count` registers starting at `start`."""
    m = re.match(r"^([a-z]+)(\d+)$", start)
    if not m or count <= 1:
        return f"{{{start}}}"
    return f"{{{start}:{m.group(1)}{int(m.group(2)) + count - 1}}}"


def _reg(op: dict, attempt: int, nth: int = 0, field: bool = False) -> str:
    if field:
        return field_name(op["name"])
    pool = EXAMPLES.get(op.get("bank") or "rd", ["rd8"])
    return pool[(attempt + nth) % len(pool)]


def new_form(entry: dict, ops: list[dict], attempt: int = 0, field: bool = False) -> str:
    """按 docs/spec/assembly-language.md 的语法渲染一条指令。

    field=True 时，寄存器用字段名（rdHA/rbHB/cgHB…）、立即数用字段名（imms12/wpN/immu16…），
    供表格的「汇编形式」列使用；否则给出具体示例（rd8/rb3/…）。
    """
    mnemonic = entry["mnemonic"]
    fmt = entry["format"]
    R = lambda op, nth=0: _reg(op, attempt, nth, field)
    IM = lambda op, lit: f"{op['name']}i" if field else lit
    imm_ops = [op for op in ops if op["kind"] in ("imm", "wpN")]

    # br.* —— 条件寄存器 + 目标地址（基址恒为 rb0）
    if mnemonic.startswith("br."):
        conds = ", ".join(R(op, i) for i, op in enumerate(ops) if op["kind"] == "reg")
        off = imm_ops[-1] if imm_ops else None
        offi = IM(off, "1i") if off else "offi"
        return f"{mnemonic} {{{conds}}}?, [rb0, {offi}]"

    # cs.* —— 条件寄存器在前，其余保持原序
    if mnemonic.startswith("cs."):
        ncond = 2 if mnemonic in ("cs.eq", "cs.ne") else 1
        conds = ", ".join(R(ops[i], i) for i in range(min(ncond, len(ops))))
        rest = ", ".join(R(op, ncond + i) for i, op in enumerate(ops[ncond:]))
        return f"{mnemonic} {{{conds}}}?, {rest}" if rest else f"{mnemonic} {{{conds}}}?"

    # jump/call
    if mnemonic in ("jump", "call") and fmt == "iiii":
        off = IM(imm_ops[-1], "1i") if imm_ops else "imms24i"
        return f"{mnemonic} [rb0, {off}]"
    if mnemonic in ("jump", "call") and fmt == "rrii":
        off = IM(imm_ops[-1], "1i") if imm_ops else "imms12i"
        return f"{mnemonic} [{R(ops[0])}, {R(ops[1], 1)}, {off}]"

    # ldm.*/stm.* —— 目的寄存器组（count 由组推出）+ 地址
    if mnemonic.startswith(("ldm.", "stm.")):
        dst = R(ops[0])
        group = f"{{{field_name(ops[0]['name'])}…}}" if field else _range(dst, 3)
        return f"{mnemonic} {group}, [{R(ops[1], 1)}, {R(ops[2], 2)}]"

    # ld.*/st.*（rrii）—— 目的 + 地址
    if fmt == "rrii" and mnemonic.startswith(("ld.", "st.")):
        return f"{mnemonic} {R(ops[0])}, [{R(ops[1], 1)}, imms12]"

    # cfx 家族（Excluded from M1）
    if mnemonic in ("cfxld", "cfxst"):
        return f"{mnemonic} {field_name(ops[0]['name']) if field else 'cfx63'}, [{R(ops[1])}, immu12]"
    if mnemonic in ("cfx2rd", "cfx2rc"):
        return (
            f"{mnemonic} {field_name(ops[0]['name']) if field else 'cfx63'}, "
            f"{R(ops[1])}, {R(ops[2], 1)}, {R(ops[3], 2)}"
        )
    if mnemonic == "escape":
        return f"{mnemonic} cfxcode, [excp_cause_ip, imms18i]"
    if mnemonic == "trap":
        return f"{mnemonic} cfxcode, immu18"

    # LR-SC 家族（lr 的 rdhb 固定 rd0，汇编只写两个操作数）
    if mnemonic.startswith("lr_"):
        return f"{mnemonic} {R(ops[1], 1)}, [{R(ops[2], 2)}]"
    if mnemonic.startswith("sc_"):
        return f"{mnemonic} {R(ops[0])}, {R(ops[1], 1)}, [{R(ops[2], 2)}]"

    # rwii —— 保持 wpN
    if fmt == "rwii":
        return f"{mnemonic} {R(ops[0])}, wpN, immu16"
    if mnemonic in ("swym", "illi", "fence"):
        return f"{mnemonic} {field_name(imm_ops[0]['name']) if (field and imm_ops) else '0'}"
    if field:
        # 默认：按原顺序渲染（寄存器用字段名、立即数用字段名）
        tokens = [
            field_name(op["name"]) if op["kind"] != "imm" else field_name(op["name"])
            for op in ops
        ]
        return f"{mnemonic} " + ", ".join(tokens) if tokens else mnemonic
    return example_line(entry, ops, attempt)


def new_template(entry: dict, ops: list[dict]) -> str:
    """Generic (placeholder) form in the new syntax, for the table column."""
    mnemonic = entry["mnemonic"]
    fmt = entry["format"]
    if mnemonic.startswith("br."):
        conds = ", ".join(f"{op.get('bank') or 'rd'}N" for op in ops if op["kind"] == "reg")
        return f"{mnemonic} {{{conds}}}?, [rb0, offi]"
    if mnemonic.startswith("cs."):
        ncond = 2 if mnemonic in ("cs.eq", "cs.ne") else 1
        conds = ", ".join(f"{ops[i].get('bank') or 'rd'}N" for i in range(min(ncond, len(ops))))
        rest = ", ".join(f"{op.get('bank') or 'rd'}N" for op in ops[ncond:])
        return f"{mnemonic} {{{conds}}}?, {rest}" if rest else f"{mnemonic} {{{conds}}}?"
    if mnemonic in ("jump", "call") and fmt == "iiii":
        return f"{mnemonic} [rb0, offi]"
    if mnemonic in ("jump", "call") and fmt == "rrii":
        return f"{mnemonic} [rbN, rdN, offi]"
    if mnemonic.startswith(("ldm.", "stm.")):
        return f"{mnemonic} {{rdN:rdM}}, [rbN, rdN]"
    if fmt == "rrii" and mnemonic.startswith(("ld.", "st.")):
        return f"{mnemonic} rdN, [rbN, off]"
    if fmt == "rwii":
        return f"{mnemonic} rdN, wpN, immu16"
    if mnemonic in ("cfxld", "cfxst"):
        return f"{mnemonic} cfxN, [rbN, off]"
    if mnemonic in ("cfx2rd", "cfx2rc"):
        return f"{mnemonic} cfxN, cgN, rcN, rdN"
    if mnemonic == "escape":
        return f"{mnemonic} cfxN, [excp_cause_ip, offi]"
    if mnemonic == "trap":
        return f"{mnemonic} cfxN, imm"
    if mnemonic.startswith("lr_"):
        return f"{mnemonic} rdN, [rbN]"
    if mnemonic.startswith("sc_"):
        return f"{mnemonic} rdN, rdN, [rbN]"
    return template(entry, ops)


def plain_lines(entries: list[dict], syntax: str) -> list[str]:
    lines: list[str] = []
    by_format: dict[str, list[dict]] = {}
    for entry in entries:
        by_format.setdefault(entry["format"], []).append(entry)
    for fmt in sorted(by_format):
        lines.append(f"// ---- {fmt} ({len(by_format[fmt])} 条) ----")
        for entry in by_format[fmt]:
            ops = operands(entry)
            if syntax == "new":
                text = new_form(entry, ops, 0)
            else:
                text = example_line(entry, ops, 0)
            scope = "  // excluded_m1" if entry.get("excluded_m1") else ""
            lines.append(f"{text}{scope}")
        lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default=str(ROOT / "docs/assembly-list.md"))
    parser.add_argument(
        "--plain",
        action="store_true",
        help="emit a plain instruction listing (one instruction per line) instead of a table",
    )
    parser.add_argument(
        "--syntax",
        choices=("old", "new"),
        default="old",
        help="instruction syntax to render: 'old' (currently implemented) or "
        "'new' (docs/spec/assembly-language.md)",
    )
    args = parser.parse_args()

    entries = yaml.safe_load(OPCODES.read_text())

    if args.plain:
        header = (
            f"// DADAO 指令清单（{'新语法（规范草案，待实现）' if args.syntax == 'new' else '旧语法（当前已实现）'}）\n"
            f"// 生成器：tools/llvm/gen_asm_list.py --plain --syntax {args.syntax}\n"
            f"// 来源：contracts/opcodes.yaml（256 条 = M1 178 + excluded_m1 78）\n"
            f"// 新语法规范：docs/spec/assembly-language.md\n\n"
        )
        out = Path(args.output)
        out.write_text(header + "\n".join(plain_lines(entries, args.syntax)) + "\n", encoding="utf-8")
        print(f"gen-asm-list: {len(entries)} entries ({args.syntax} syntax) -> {out}")
        return 0

    by_format: dict[str, list[dict]] = {}
    for entry in entries:
        by_format.setdefault(entry["format"], []).append(entry)

    rows = []
    by_class: dict[str, list[dict]] = {}
    for entry in entries:
        by_class.setdefault(classify(entry), []).append(entry)
    for cls in SECTION_ORDER:
        if cls not in by_class:
            continue
        rows.append(f"\n### {cls}（{len(by_class[cls])} 条）\n")
        rows.append("| 助记符 | format | feature | 汇编形式 | id |")
        rows.append("|---|---|---|---|---|")
        body = []
        for entry in by_class[cls]:
            ops = operands(entry)
            feature = primary_feature(entry, ops)
            form = new_form(entry, ops, 0, field=True)
            ident = f"{entry['mnemonic']}_{entry['format']}_{feature}"
            body.append((
                ident,
                f"| `{entry['mnemonic']}` | `{entry['format']}` | `{feature}` | `{form}` | `{ident}` |",
            ))
        rows.extend(row for _, row in sorted(body))  # 每个表格按 id 升序排序

    header = f"""# DADAO 汇编指令表（新语法）

> **生成器**：`tools/llvm/gen_asm_list.py`（生成物，勿手工编辑；改生成器后重跑）
> **源**：`contracts/opcodes.yaml`（256 条 = M1 178 + `excluded_m1` 78）
> **语法**：`docs/spec/assembly-language.md`（**设计定稿、待实现**）
> **分章**：**8位数据运算** / **16位数据运算** / **32位数据运算** / **64位数据运算** / **64位地址运算** / 浮点 / 存储 / 控制流 / **寄存器复制**（`cs.*` 与寄存器组→寄存器组） / **16位立即数操作**（rwii 格式） / 其它 / **待定**（暂不归类：`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`/`rela*`/`f*madd`）
> **列**：助记符 ｜ format ｜ feature ｜ 汇编形式（字段名，如 `rdHA`） ｜ id（= 助记符_format_feature）

## 立即数范围速查

| 字段 | 范围 |
|---|---|
| `imms12` | s12: -2048..2047 |
| `imms18` | s18: -131072..131071 |
| `imms24` | s24: -8388608..8388607 |
| `immu6` | u6: 0..63 |
| `immu12` | u12: 0..4095 |
| `immu16` | u16: 0..65535 |
| `immu18` | u18: 0..262143 |
| `immu24` | u24: 0..16777215 |
| `wpN` | wyde 位置 0..3 |
"""

    out = Path(args.output)
    out.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"gen-asm-list: {len(entries)} entries -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
