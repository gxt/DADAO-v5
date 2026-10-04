#!/usr/bin/env python3
"""Generate the complete DADAO assembly-instruction list.

See ``.tao/knowledge/contract-asm-list.md`` (generated) and
``spec/Process-01-组件补丁组织与构建编排.md`` (spec-writing conventions).

Sources
-------
* ``contracts/opcodes.yaml`` -- the authoritative encoding table
  (per-record ``scope`` = m1 | fp | excluded), with per-field ``role``/``bank``.

Derivation rules (validated against ``tests/lit/MC/Dadao/*.s``)
---------------------------------------------------------------
* operands are the fields whose ``role`` is one of dst/src/imm/wyde_pos/
  cfxcode/cfx_cg/cfx_rc; ``opx`` fields are already encoded in the
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
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts/opcodes.yaml"

OPERAND_ROLES = {"dst", "src", "imm", "wyde_pos", "cfxcode", "cfx_cg", "cfx_rc"}
SPLIT_SUFFIX = re.compile(r"^(imms?\d+|immu?\d+)_(?:hi|mid|lo|b\d+_\d+)$")

# 双目的指令（rrrr 格式，rdha/rdhb 均为 dst 的双目标寄存器指令）
_DUAL_TARGET_MNEMONICS = frozenset({"add.uo", "add.so", "sub.uo", "sub.so", "mul.uo", "mul.so"})

# 多寄存器指令（orri 格式，immu6 = 连续寄存器个数，源和目的都用组记法）
_MULTI_REG_MNEMONICS = frozenset({
    # 寄存器复制（8 条）
    "ra2rd", "rb2rb", "rb2rd", "rd2ra", "rd2rb", "rd2rd", "rd2rf", "rf2rd",
    # 浮点格式转换（20 条）
    "ft2fo", "fo2ft", "ft2ft", "fo2fo", "ft2it", "ft2io", "ft2ut", "ft2uo",
    "fo2it", "fo2io", "fo2ut", "fo2uo", "it2ft", "io2ft", "ut2ft", "uo2ft",
    "it2fo", "io2fo", "ut2fo", "uo2fo",
    # 浮点分类（2 条）
    "focls", "ftcls",
})

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
               "immu24": "1", "imms12": "1", "imms14": "8", "imms18": "1",
               "imms20": "8", "imms24": "1", "imms26": "8", "wpN": "0"}

# ADR-0013 D10: assembly-layer field name mapping for ×4 address fields.
# Encoding-level names (imms12/18/24) are renamed to byte-domain names
# (imms14/20/26) in the assembly form column.  Only applies to branch/jump/
# escape; load/store (imms12) and ret (imms18) keep encoding names.
_ASM_IMM_RENAME = {"imms12": "imms14", "imms18": "imms20", "imms24": "imms26"}


def _asm_imm_name(name: str) -> str:
    """Map encoding-level immediate field name to assembly-layer name."""
    return _ASM_IMM_RENAME.get(name, name)


def base_imm(name: str) -> str:
    m = SPLIT_SUFFIX.match(name)
    return m.group(1) if m else name


def operands(entry: dict) -> list[dict]:
    out = []
    fmt = entry.get("format", "")
    for field in entry.get("fields", []):
        name = field.get("name", "")
        base = base_imm(name)
        # Infer kind from field name and format
        if name == "wpN":
            kind, bank = "wpN", None
        elif name == "cfxha":
            kind, bank = "cfxcode", None
        elif name == "cghb":
            kind, bank = "cfx_cg", None
        elif name == "rchc":
            kind, bank = "cfx_rc", None
        elif name.startswith("imm") or name == "imms12" or name == "immu6":
            kind, bank = "imm", field.get("bank")
        else:
            bank = field.get("bank")
            kind = "reg"
        if out and out[-1]["kind"] == kind == "imm":
            continue
        out.append({"kind": kind, "bank": bank, "name": base, "role": field.get("role")})
    return out


FIELD_RE = re.compile(r"^(rd|rb|ra|rf|cg|rc|cfx)([a-z]{2})$")


def field_name(name: str) -> str:
    """rdha -> rdHA；cfxha -> cfxHA；imms12/wpN 原样。"""
    m = FIELD_RE.match(name)
    return m.group(1) + m.group(2).upper() if m else name


# 无显式寄存器操作数的指令：由用户裁定其 feature
FEATURE_OVERRIDE = {
    "jump": "rb",
    # call 压栈 / ret 弹栈均走 RegRAS（ra）——用户裁定 2026-09-25
    "call": "ra", "ret": "ra",
    "swym": "imm", "illi": "imm", "fence": "imm",
    "escape": "cfx", "trap": "cfx",
}


def primary_feature(entry: dict, ops: list[dict]) -> str:
    """指令的 feature：insn 后缀（-rd/-rb/-ra/-rf）优先；否则取 dst 的寄存器组；再否则由 FEATURE_OVERRIDE 指定。"""
    mnemonic = entry["mnemonic"]
    insn = entry["id"]
    if mnemonic in FEATURE_OVERRIDE:
        return FEATURE_OVERRIDE[mnemonic]
    if mnemonic.startswith("cfx"):
        return "cfx"
    # 浮点类指令统一 rf
    if classify(entry) == "浮点运算":
        return "rf"
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
    """章节分类（优先级：rwii > 取数存数 > 控制流 > 寄存器复制 > 浮点运算 > 位宽 > 64位运算 > 其它）。"""
    m = entry["mnemonic"]
    # 待定（用户裁定：暂不归类）
    if m in ("cfxld", "cfxst", "fence") \
            or m.startswith(("lr_", "sc_")):
        return "待定"
    if entry["format"] == "rwii":
        return "16位立即数操作"
    if m.startswith(("ld.", "st.", "ldm.", "stm.")):
        return "取数存数"
    if m.startswith(("br.", "jump", "call", "ret")):
        return "控制流"
    if m.startswith("cs.") or re.fullmatch(r"(rd|rb|ra|rf)2(rd|rb|ra|rf)", m):
        return "寄存器复制"
    # 浮点：操作数含 rf 寄存器，或助记符为 fo*/ft* 或形如 *2f*/*2rf*（格式转换）
    if (any(f.get("bank") == "rf" for f in entry["fields"])
            or m.startswith(("fo", "ft"))
            or re.search(r"2f|2rf", m)):
        return "浮点运算"
    if m.startswith(("lr_", "sc_")):
        return "其它"
    if re.search(r"\.(ub|sb|b)$", m):
        return "8位数据运算"
    if re.search(r"\.(uw|sw|w)$", m) or m in ("set.zw", "set.ow"):
        return "16位数据运算"
    if re.search(r"\.(ut|st|t)$", m):
        return "32位数据运算"
    if re.search(r"\.(uo|so|o)$", m) or m == "add.si" or m.startswith("cmp."):
        # 64 位运算按寄存器组分：rb（地址）→ 地址运算；其余 → 数据运算
        return "64位地址运算" if any(f.get("bank") == "rb" for f in entry["fields"]) else "64位数据运算"
    return "其它"


SECTION_ORDER = ["取数存数", "寄存器复制", "16位立即数操作", "64位数据运算", "64位地址运算", "控制流", "浮点运算", "32位数据运算", "16位数据运算", "8位数据运算", "其它", "待定"]

# 章节「范围/状态」标（用户裁定 2026-10-03：`scope` 表范围、`deferred` 表状态，二者正交）。
# 章节名 → 标题后缀（含 `｜` 之后的内容）。
SECTION_BADGES = {
    "浮点运算": "**scope: fp（已实现）**",
    "待定": "**deferred** — 暂不归类，待必须启用时",
}


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
    # 双目的指令（rrrr 格式，rdha/rdhb 均为 dst）：{rd8, rd9}, rd10, rd11
    if entry["format"] == "rrrr" and entry["mnemonic"] in _DUAL_TARGET_MNEMONICS:
        dst_rds = [op for op in ops if op.get("role") == "dst" and op.get("bank") == "rd"]
        srcs = [op for op in ops if op.get("role") == "src"]
        if len(dst_rds) >= 2 and len(srcs) >= 2:
            inner = ", ".join(EXAMPLES["rd"][(attempt + i) % len(EXAMPLES["rd"])] for i in range(2))
            rest = ", ".join(EXAMPLES["rd"][(attempt + i + 2) % len(EXAMPLES["rd"])] for i in range(2))
            return f"{entry['mnemonic']} {{{inner}}}, {rest}"
    # 多寄存器指令（orri 格式，immu6 = 连续寄存器个数）—— 源和目的都用组记法
    if entry["format"] == "orri" and entry["mnemonic"] in _MULTI_REG_MNEMONICS:
        reg_ops = [op for op in ops if op["kind"] == "reg"]
        if len(reg_ops) >= 2:
            dst_op, src_op = reg_ops[0], reg_ops[1]
            dst_pool = EXAMPLES.get(dst_op.get("bank") or "rd", ["rd8"])
            src_pool = EXAMPLES.get(src_op.get("bank") or "rd", ["rd8"])
            dst_start = dst_pool[(attempt) % len(dst_pool)]
            src_start = src_pool[(attempt + 1) % len(src_pool)]
            dst_group = _range(dst_start, 3)
            src_group = _range(src_start, 3)
            return f"{entry['mnemonic']} {dst_group}, {src_group}"
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
    """按 spec/Toolchain-01-汇编语言.md 的语法渲染一条指令。

    field=True 时，寄存器用字段名（rdHA/rbHB/cgHB…）、立即数用字段名（imms12/wpN/immu16…），
    供表格的「汇编形式」列使用；否则给出具体示例（rd8/rb3/…）。
    """
    mnemonic = entry["mnemonic"]
    fmt = entry["format"]
    R = lambda op, nth=0: _reg(op, attempt, nth, field)
    IM = lambda op, lit: _asm_imm_name(op['name']) if field else lit
    imm_ops = [op for op in ops if op["kind"] in ("imm", "wpN")]

    # br.* —— 条件寄存器 + 目标地址（基址恒为 rb0）
    if mnemonic.startswith("br."):
        conds = ", ".join(R(op, i) for i, op in enumerate(ops) if op["kind"] == "reg")
        off = imm_ops[-1] if imm_ops else None
        offi = IM(off, "8") if off else "imms20"
        return f"{mnemonic} {{{conds}}}?, [rb0, {offi}]"

    # cs.* —— 条件寄存器在前，其余保持原序
    if mnemonic.startswith("cs."):
        ncond = 2 if mnemonic in ("cs.eq", "cs.ne") else 1
        conds = ", ".join(R(ops[i], i) for i in range(min(ncond, len(ops))))
        rest = ", ".join(R(op, ncond + i) for i, op in enumerate(ops[ncond:]))
        return f"{mnemonic} {{{conds}}}?, {rest}" if rest else f"{mnemonic} {{{conds}}}?"

    # jump/call
    if mnemonic in ("jump", "call") and fmt == "iiii":
        off = IM(imm_ops[-1], "8") if imm_ops else "imms26"
        return f"{mnemonic} [rb0, {off}]"
    if mnemonic in ("jump", "call") and fmt == "rrii":
        off = IM(imm_ops[-1], "8") if imm_ops else "imms14"
        return f"{mnemonic} [{R(ops[0])}, {R(ops[1], 1)}, {off}]"

    # ldm.*/stm.* —— 目的寄存器组（count 由组推出）+ 地址
    if mnemonic.startswith(("ldm.", "stm.")):
        dst = R(ops[0])
        if field:
            # 字段名渲染：起点字段 + 个数字段（rrri 的 immu6），显式写出终点
            start = field_name(ops[0]["name"])
            cnt = next((field_name(o["name"]) for o in ops if o.get("role") == "imm"),
                       "immu6")
            group = f"{{{start}:{start}+{cnt}-1}}"
        else:
            group = _range(dst, 3)
        return f"{mnemonic} {group}, [{R(ops[1], 1)}, {R(ops[2], 2)}]"

    # 多寄存器指令（orri 格式，immu6 = 连续寄存器个数）—— 源和目的都用组记法
    if fmt == "orri" and mnemonic in _MULTI_REG_MNEMONICS:
        reg_ops = [op for op in ops if op["kind"] == "reg"]
        if len(reg_ops) >= 2:
            dst_op, src_op = reg_ops[0], reg_ops[1]
            if field:
                # 字段名渲染：{dstHB:dstHB+immu6-1}, {srcHC:srcHC+immu6-1}
                dst_start = field_name(dst_op["name"])
                src_start = field_name(src_op["name"])
                dst_group = f"{{{dst_start}:{dst_start}+immu6-1}}"
                src_group = f"{{{src_start}:{src_start}+immu6-1}}"
            else:
                # 示例渲染：{rd8:rd10}, {ra1:ra3}（count=3）
                dst_group = _range(R(dst_op, 0), 3)
                src_group = _range(R(src_op, 1), 3)
            return f"{mnemonic} {dst_group}, {src_group}"

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
        return f"{mnemonic} cfxHA, [excp_cause_ip, imms20]"
    if mnemonic == "trap":
        return f"{mnemonic} cfxHA, immu18"

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
    # 双目的指令（rrrr 格式，rdha/rdhb 均为 dst）：{rdHA, rdHB}, rdHC, rdHD
    if fmt == "rrrr" and mnemonic in _DUAL_TARGET_MNEMONICS:
        dst_rds = [op for op in ops if op.get("role") == "dst" and op.get("bank") == "rd"]
        srcs = [op for op in ops if op.get("role") == "src"]
        if len(dst_rds) >= 2 and len(srcs) >= 2:
            if field:
                inner = ", ".join(field_name(op["name"]) for op in dst_rds[:2])
                rest = ", ".join(field_name(op["name"]) for op in srcs[:2])
            else:
                inner = ", ".join(R(op, i) for i, op in enumerate(dst_rds[:2]))
                rest = ", ".join(R(op, i + 2) for i, op in enumerate(srcs[:2]))
            return f"{mnemonic} {{{inner}}}, {rest}"

    if field:
        # 默认：按原顺序渲染（寄存器用字段名、立即数用字段名）
        tokens = [
            field_name(op["name"]) if op["kind"] != "imm" else field_name(op["name"])
            for op in ops
        ]
        return f"{mnemonic} " + ", ".join(tokens) if tokens else mnemonic
    return example_line(entry, ops, attempt)


def new_template(entry: dict, ops: list[dict]) -> str:
    """Generic (placeholder) form in the new syntax, for the table column.

    .. deprecated::
        Dead code — no call sites remain.  Will be removed in a future cleanup.
    """
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


CLASS_TO_SPEC = {
    "取数存数":     "spec/SimRISC-01-取数存数.md",
    "寄存器复制":   "spec/SimRISC-02-寄存器复制.md",
    "16位立即数操作": "spec/SimRISC-03-16位立即数操作.md",
    "64位数据运算":  "spec/SimRISC-04-64位数据运算.md",
    "64位地址运算":  "spec/SimRISC-05-64位地址运算.md",
    "控制流":       "spec/SimRISC-06-控制流.md",
    "浮点运算":     "spec/SimRISC-07-浮点运算.md",
    "32位数据运算":  "spec/SimRISC-08-32位数据运算.md",
    "16位数据运算":  "spec/SimRISC-09-16位数据运算.md",
    "8位数据运算":   "spec/SimRISC-10-8位数据运算.md",
    "其它":         "spec/SimRISC-11-其它.md",
    "待定":         "spec/SimRISC-12-待定.md",
}

ASSEMBLY_LIST_START = "<!-- ASSEMBLY_LIST_START -->"
ASSEMBLY_LIST_END = "<!-- ASSEMBLY_LIST_END -->"


def _section_content(cls: str, entries: list[dict]) -> str:
    """Return the markdown table content for one category."""
    if cls in SECTION_BADGES:
        header = f"### {cls}（{len(entries)} 条）｜ {SECTION_BADGES[cls]}"
    else:
        header = f"### {cls}（{len(entries)} 条）"
    lines = [header, ""]
    lines.append("| 助记符 | format | feature | 汇编形式 | id |")
    lines.append("|---|---|---|---|---|")
    body = []
    for entry in entries:
        ops = operands(entry)
        ident = entry["id"]
        feature = ident.rsplit("_", 1)[-1]
        form = new_form(entry, ops, 0, field=True)
        body.append((
            ident,
            f"| `{entry['mnemonic']}` | `{entry['format']}` | `{feature}` | `{form}` | `{ident}` |",
        ))
    for _, row in sorted(body):
        lines.append(row)
    return "\n".join(lines) + "\n"


def embed_spec(entries: list[dict]) -> int:
    """Embed assembly tables into spec files, one per category."""
    by_class: dict[str, list[dict]] = {}
    for entry in entries:
        by_class.setdefault(classify(entry), []).append(entry)

    section_contents: dict[str, str] = {}
    for cls in SECTION_ORDER:
        if cls in by_class:
            section_contents[cls] = _section_content(cls, by_class[cls])

    for cls in SECTION_ORDER:
        if cls not in CLASS_TO_SPEC:
            continue
        spec_path = ROOT / CLASS_TO_SPEC[cls]
        if not spec_path.exists():
            print(f"gen-asm-list: WARNING: {spec_path} not found, skipping", flush=True)
            continue

        content = spec_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Build the new section block (with surrounding blank lines)
        section = section_contents.get(cls, "")
        new_block = (
            f"{ASSEMBLY_LIST_START}\n"
            f"## 汇编指令速查\n\n"
            f"{section}\n"
            f"{ASSEMBLY_LIST_END}"
        )

        # If markers already exist, replace the existing block (idempotent)
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if line.strip() == ASSEMBLY_LIST_START:
                start_idx = i
            if line.strip() == ASSEMBLY_LIST_END:
                end_idx = i
                break

        if start_idx is not None and end_idx is not None:
            # Replace existing block (preserve lines before and after)
            before_lines = lines[:start_idx]
            after_lines = lines[end_idx + 1:]
            new_content = "\n".join(before_lines) + "\n" + new_block + "\n" + "\n".join(after_lines)
        else:
            # First insertion: find the end of the header block (consecutive '>' lines
            # at the top, possibly preceded by title/blank lines).
            header_end = 0
            in_header = False
            for i, line in enumerate(lines):
                if line.startswith(">"):
                    header_end = i + 1
                    in_header = True
                elif in_header:
                    # First non-'>' line after a '>' line = end of header block
                    break
            # Insert right after the last '>' line, preserving all content
            before = "\n".join(lines[:header_end])
            after = "\n".join(lines[header_end:])
            new_content = before + "\n\n" + new_block + "\n" + after

        spec_path.write_text(new_content, encoding="utf-8")
        count = len(by_class.get(cls, []))
        print(f"gen-asm-list: embedded {cls}（{count} 条）-> {spec_path}")

    return 0


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
            scope = "" if entry.get("scope", "m1") == "m1" \
                else f"  // scope: {entry.get('scope')}"
            lines.append(f"{text}{scope}")
        lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default=None)
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
        "'new' (spec/Toolchain-01-汇编语言.md)",
    )
    parser.add_argument(
        "--embed-spec",
        action="store_true",
        help="embed assembly tables into spec/SimRISC-XX-*.md files",
    )
    args = parser.parse_args()

    entries = yaml.safe_load(OPCODES.read_text())

    if args.embed_spec:
        return embed_spec(entries)

    # --- 从 entries 推导计数（消除硬编码）---
    total = len(entries)
    n_m1 = sum(1 for e in entries if e.get("scope") == "m1")
    n_fp = sum(1 for e in entries if e.get("scope") == "fp")
    n_excluded = sum(1 for e in entries if e.get("scope") == "excluded")

    if args.plain:
        header = (
            f"// DADAO 指令清单（{'新语法（规范草案，待实现）' if args.syntax == 'new' else '旧语法（当前已实现）'}）\n"
            f"// 生成器：tools/llvm/gen_asm_list.py --plain --syntax {args.syntax}\n"
            f"// 来源：contracts/opcodes.yaml（{total} 条 = M1 {n_m1} + scope fp {n_fp} + scope excluded {n_excluded}）\n"
            f"// 新语法规范：spec/Toolchain-01-汇编语言.md\n\n"
        )
        text = header + "\n".join(plain_lines(entries, args.syntax)) + "\n"
        if args.output is not None:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"gen-asm-list: {len(entries)} entries ({args.syntax} syntax) -> {args.output}")
        else:
            sys.stdout.write(text)
            print(f"gen-asm-list: {len(entries)} entries ({args.syntax} syntax) -> stdout", file=sys.stderr)
        return 0

    # --- 范围/状态统计（从 entries 推导；scope 表范围、deferred 表状态，二者正交）---
    _by_class_tmp: dict[str, list[dict]] = {}
    for entry in entries:
        _by_class_tmp.setdefault(classify(entry), []).append(entry)
    _fp_chapter = len(_by_class_tmp.get("浮点运算", []))
    _pending_chapter = len(_by_class_tmp.get("待定", []))

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
        if cls in SECTION_BADGES:
            rows.append(
                f"\n### {cls}（{len(by_class[cls])} 条）｜ {SECTION_BADGES[cls]}\n"
            )
        else:
            rows.append(f"\n### {cls}（{len(by_class[cls])} 条）\n")
        rows.append("| 助记符 | format | feature | 汇编形式 | id |")
        rows.append("|---|---|---|---|---|")
        body = []
        for entry in by_class[cls]:
            ops = operands(entry)
            # id 为权威值（opcodes.yaml），feature 由 id 末段取出
            ident = entry["id"]
            feature = ident.rsplit("_", 1)[-1]
            form = new_form(entry, ops, 0, field=True)
            body.append((
                ident,
                f"| `{entry['mnemonic']}` | `{entry['format']}` | `{feature}` | `{form}` | `{ident}` |",
            ))
        rows.extend(row for _, row in sorted(body))  # 每个表格按 id 升序排序

    header = f"""# DADAO 汇编指令表（新语法）

> **生成器**：`tools/llvm/gen_asm_list.py`（生成物，勿手工编辑；改生成器后重跑）
> **源**：`contracts/opcodes.yaml`（{total} 条 = M1 {n_m1} + `scope: fp` {n_fp} + `scope: excluded` {n_excluded}）
> **语法**：`spec/Toolchain-01-汇编语言.md`（**v1 生效，待实现**）
> **分章**：取数存数 / **寄存器复制**（`cs.*` 与寄存器组→寄存器组） / **16位立即数操作**（rwii 格式） / **64位数据运算** / **64位地址运算** / 控制流 / 浮点运算 / **32位数据运算** / **16位数据运算** / **8位数据运算** / 其它 / **待定**（暂不归类：`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）
> **范围与状态**（用户裁定 2026-10-03：`scope` 表范围、`deferred` 表状态，二者正交）：**浮点运算**（{_fp_chapter} 条）为 `scope: fp`（已实现）；**待定**（{_pending_chapter} 条）为 **deferred**（暂不归类）；其余 {n_m1} 条为 `scope: m1` 当前有效书写形式
> **注（`scope: fp` 范围总账 = {n_fp} 条）**：浮点运算章 {_fp_chapter} 条（MISC-RF 子表）+ 取数存数 8 条（`ld.*`/`st.*`/`ldm.*`/`stm.*` 的 `rf` 形式）+ 寄存器复制 7 条（`cs.eq/ne/n/z/p-rf` 与 `rd2rf`/`rf2rd`）+ 16位立即数操作 1 条（`set.w-rf`）
> **注（`ldm.*`/`stm.*` 的组记法）**：汇编形式列的 `{{rdHA:rdHA+immu6-1}}` 表示「以 `rdHA` 为起点、个数由 `immu6` 字段决定的连续寄存器组」（字面语法见 `spec/Toolchain-01-汇编语言.md` §4.2）
> **列**：助记符 ｜ format ｜ feature ｜ 汇编形式（字段名，如 `rdHA`） ｜ id（= 助记符_format_feature）

## 立即数范围速查

| 字段 | 范围 | 说明 |
|---|---|---|
| `imms12` | s12: -2048..2047 | 访存偏移（字节，无 `%4` 要求） |
| `imms14` | bytes: [-8192, 8188]，`%4==0` | 跳转/分支 rrii 偏移（字节→编码 `>>2`） |
| `imms18` | s18: -131072..131071 | `ret` 返回值（非地址，无 `%4` 要求） |
| `imms20` | bytes: [-524288, 524284]，`%4==0` | 跳转/分支 riii 偏移 + `escape` 偏移（字节→编码 `>>2`） |
| `imms24` | s24: -8388608..8388607 | 编码层字段（非汇编层直接使用） |
| `imms26` | bytes: [-33554432, 33554428]，`%4==0` | 跳转 iiii 偏移（字节→编码 `>>2`） |
| `immu6` | u6: 0..63 | |
| `immu12` | u12: 0..4095 | |
| `immu16` | u16: 0..65535 | |
| `immu18` | u18: 0..262143 | |
| `immu24` | u24: 0..16777215 | |
| `wpN` | wyde 位置 0..3 | |
"""

    out = Path(args.output) if args.output is not None else ROOT / ".tao/knowledge/contract-asm-list.md"
    out.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"gen-asm-list: {len(entries)} entries -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
