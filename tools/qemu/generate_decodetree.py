#!/usr/bin/env python3
"""从 contracts/opcodes.yaml 生成 QEMU decodetree 文件和 trans_* 存根。

生成物：
  1. insn.decode  — decodetree 模式文件（256 条 pattern，两种格式）
  2. translate_stubs.c.inc — trans_* 存根函数

decodetree 格式说明：
  - @main 格式：提取 ha/hb/hc/hd 四个字段（主表指令，mask=0xFF000000）
  - @misc 格式：提取 hb/hc/hd 三个字段（MISC 子表指令，mask=0xFFFC0000）
    ha 是 opcode 的一部分，包含在 pattern 的固定位中

每条 pattern 的 mask/value 直接取自 opcodes.yaml，不自行推断。

产物路径约定：
  默认输出到 /tmp/opencode/QEMU-004t/（与全局临时目录约定一致）。
  不得将产物默认写入仓库根目录；需要入库时用 --out-decode/--out-stubs
  显式指定目标路径。

用法：
  python3 generate_decodetree.py [--yaml PATH] [--out-decode FILE] [--out-stubs FILE]
"""

import argparse
import os
import re
import sys
from collections import Counter

try:
    import yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DEFAULT_YAML = os.path.join(REPO_ROOT, "contracts", "opcodes.yaml")
DEFAULT_OUT_DIR = "/tmp/opencode/QEMU-004t"


def load_opcodes(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _to_int(val):
    if isinstance(val, int):
        return val
    return int(str(val).strip(), 0)


def mask_value_to_pattern(mask, value):
    """将32位 mask/value 转换为 QEMU decodetree 模式字符串。

    使用 binary notation（每字符1位），输出恰好32字符。
    每位：mask=1 → 用value，mask=0 → '.'。
    """
    bits = []
    for i in range(32):
        bit_pos = 31 - i
        bit_mask = 1 << bit_pos
        if mask & bit_mask:
            bits.append('1' if (value & bit_mask) else '0')
        else:
            bits.append('.')
    return ''.join(bits)


def sanitize_name(insn_name):
    """将 insn 名转换为合法 C 标识符。"""
    return re.sub(r'[^A-Za-z0-9]', '_', insn_name)


def is_misc_entry(rec):
    """判断是否为 MISC 子表条目（mask=0xFFFC0000）。"""
    return _to_int(rec["mask"]) == 0xFFFC0000


def build_unique_func_names(records):
    """为每条记录构建唯一的 trans_* 函数名。

    大多数记录用 insn 字段即可；当 sanitize(insn) 冲突时（如 ext.uo 同时
    出现在 orrr 和 orri 中），追加 _{format} 后缀。
    """
    base_counts = Counter(sanitize_name(r["insn"]) for r in records)

    func_names = []
    for rec in records:
        base = sanitize_name(rec["insn"])
        if base_counts[base] > 1:
            func = f"{base}_{rec['format']}"
        else:
            func = base
        func_names.append(func)
    return func_names


def generate_decode_file(records, out_path):
    """生成 insn.decode 文件。"""
    func_names = build_unique_func_names(records)

    lines = []
    lines.append("# DADAO instruction decoding")
    lines.append("# Auto-generated from contracts/opcodes.yaml")
    lines.append("# 256 patterns; blank cells trigger UNDI")
    lines.append("")
    lines.append("# Field declarations")
    lines.append("%ha       18:6")
    lines.append("%hb       12:6")
    lines.append("%hc        6:6")
    lines.append("%hd        0:6")
    lines.append("")
    lines.append("&main     ha hb hc hd")
    lines.append("&misc     hb hc hd")
    lines.append("")
    lines.append("# @main: main table entries — ha/hb/hc/hd are fields")
    lines.append("@main     ........ ........ ........ ........  &main  %ha %hb %hc %hd")
    lines.append("# @misc: MISC sub-table entries — hb/hc/hd are fields, ha is opcode part")
    lines.append("@misc     ........ ........ ........ ........  &misc  %hb %hc %hd")
    lines.append("")

    for rec, func in zip(records, func_names):
        mask = _to_int(rec["mask"])
        value = _to_int(rec["value"])
        pattern = mask_value_to_pattern(mask, value)
        fmt = "@misc" if is_misc_entry(rec) else "@main"
        lines.append(f"{func}  {pattern}  {fmt}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  insn.decode: {len(records)} 条 pattern → {out_path}")


def generate_stubs(records, out_path):
    """生成 trans_* 存根函数。"""
    func_names = build_unique_func_names(records)

    lines = []
    lines.append("/* DADAO decodetree trans_* stubs")
    lines.append(" * Auto-generated from contracts/opcodes.yaml")
    lines.append(" * All stubs trigger ILLI except swym (NOP).")
    lines.append(" */")
    lines.append("")

    for rec, func in zip(records, func_names):
        mnemonic = rec.get("mnemonic", rec["insn"])
        arg_type = "arg_misc" if is_misc_entry(rec) else "arg_main"

        if mnemonic == "swym":
            lines.append(f"static bool trans_{func}(DisasContext *ctx, {arg_type} *a)")
            lines.append("{")
            lines.append("    /* swym: NOP */")
            lines.append("    return true;")
            lines.append("}")
        else:
            lines.append(f"static bool trans_{func}(DisasContext *ctx, {arg_type} *a)")
            lines.append("{")
            lines.append(f"    /* {rec['insn']} - stub: ILLI */")
            lines.append("    gen_exception_illegal(ctx);")
            lines.append("    return true;")
            lines.append("}")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  trans_* stubs: {len(func_names)} 条 → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="从 opcodes.yaml 生成 decodetree 文件")
    parser.add_argument("--yaml", default=DEFAULT_YAML, help="opcodes.yaml 路径")
    parser.add_argument("--out-decode", default=None, help="insn.decode 输出路径")
    parser.add_argument("--out-stubs", default=None, help="trans_* 存根输出路径")
    args = parser.parse_args()

    records = load_opcodes(args.yaml)
    print(f"generate_decodetree: 加载 {len(records)} 条记录")

    out_decode = args.out_decode or os.path.join(DEFAULT_OUT_DIR, "insn.decode")
    out_stubs = args.out_stubs or os.path.join(DEFAULT_OUT_DIR, "translate_stubs.c.inc")

    # 确保输出目录存在
    os.makedirs(os.path.dirname(out_decode), exist_ok=True)
    os.makedirs(os.path.dirname(out_stubs), exist_ok=True)

    generate_decode_file(records, out_decode)
    generate_stubs(records, out_stubs)
    print("generate_decodetree: 完成")


if __name__ == "__main__":
    main()
