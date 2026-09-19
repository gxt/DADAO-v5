#!/usr/bin/env python3
"""validate_decodetree.py — 校验 insn.decode 与 opcodes.yaml 的一致性。

检查：
  1. insn.decode 中每条 pattern 的 mask/value 与 opcodes.yaml 一致
  2. 每条 pattern 有对应的 trans_* 函数名
  3. opcodes.yaml 中每条记录在 insn.decode 中有对应 pattern
  4. 无遗漏、无多余

用法：
  python3 validate_decodetree.py <insn.decode> [opcodes.yaml]
"""

import os
import re
import sys
from collections import Counter

try:
    import yaml as _yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def _to_int(val):
    if isinstance(val, int):
        return val
    return int(str(val).strip(), 0)


def pattern_to_mask_value(pattern):
    """将 decodetree 模式字符串（binary notation）转换回 mask 和 value。"""
    mask = 0
    value = 0
    for ch in pattern:
        mask <<= 1
        value <<= 1
        if ch == '0':
            mask |= 1
        elif ch == '1':
            mask |= 1
            value |= 1
        elif ch == '.':
            pass  # don't-care
    return mask, value


def mask_value_to_pattern(mask, value):
    """将32位 mask/value 转换为 decodetree 模式字符串（binary notation）。"""
    bits = []
    for i in range(32):
        bit_pos = 31 - i
        bit_mask = 1 << bit_pos
        if mask & bit_mask:
            bits.append('1' if (value & bit_mask) else '0')
        else:
            bits.append('.')
    return ''.join(bits)


def parse_decode_file(path):
    """解析 insn.decode 文件，返回 [(pattern, func_name, format)] 列表。"""
    entries = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # 格式: FUNC_NAME  PATTERN  @FORMAT
            tokens = line.split()
            if len(tokens) < 3:
                continue
            func_name = tokens[0]
            pattern = tokens[1]
            fmt = tokens[2] if len(tokens) >= 3 else ""
            if not re.match(r'^[01.]+$', pattern):
                continue
            if not func_name[0].isalpha():
                continue
            entries.append((pattern, func_name, fmt, lineno))
    return entries


def sanitize_name(insn_name):
    return re.sub(r'[^A-Za-z0-9]', '_', insn_name)


def is_misc_entry(rec):
    return _to_int(rec["mask"]) == 0xFFFC0000


def build_unique_func_names(records):
    base_counts = Counter(sanitize_name(r["insn"]) for r in records)
    func_names = []
    for rec in records:
        base = sanitize_name(rec["insn"])
        if base_counts[base] > 1:
            func_names.append(f"{base}_{rec['format']}")
        else:
            func_names.append(base)
    return func_names


def main():
    if len(sys.argv) < 2:
        print("用法: validate_decodetree.py <insn.decode> [opcodes.yaml]",
              file=sys.stderr)
        sys.exit(1)

    decode_path = sys.argv[1]
    yaml_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        REPO_ROOT, "contracts", "opcodes.yaml")

    print(f"validate_decodetree:")
    print(f"  decode: {decode_path}")
    print(f"  yaml:   {yaml_path}")
    print()

    # 加载 decode 文件
    decode_entries = parse_decode_file(decode_path)
    decode_by_func = {}
    for pattern, func, fmt, lineno in decode_entries:
        decode_by_func[func] = (pattern, fmt, lineno)

    # 加载 yaml
    with open(yaml_path, encoding="utf-8") as f:
        records = _yaml.safe_load(f)

    errors = []

    # 构建唯一函数名映射
    func_names = build_unique_func_names(records)

    # 检查1: 每条 yaml 记录在 decode 中有对应 pattern
    for rec, func_base in zip(records, func_names):
        insn = rec["insn"]
        func = func_base
        mask = _to_int(rec["mask"])
        value = _to_int(rec["value"])

        if func not in decode_by_func:
            errors.append(f"YAML 有但 decode 缺: {insn} → trans_{func}")
            continue

        pattern, fmt, lineno = decode_by_func[func]
        pat_mask, pat_value = pattern_to_mask_value(pattern)

        if pat_mask != mask or pat_value != value:
            expected = mask_value_to_pattern(mask, value)
            errors.append(
                f"mask/value 不匹配: {insn} (line {lineno})\n"
                f"  yaml:    mask=0x{mask:08X} value=0x{value:08X} → {expected}\n"
                f"  decode:  pattern={pattern}")

        # 检查格式是否正确
        if is_misc_entry(rec) and fmt != "@misc":
            errors.append(f"格式错误: {insn} 应为 @misc，实际为 {fmt}")
        elif not is_misc_entry(rec) and fmt != "@main":
            errors.append(f"格式错误: {insn} 应为 @main，实际为 {fmt}")

    # 检查2: decode 中每条 pattern 在 yaml 中有对应记录
    yaml_funcs = {fn for fn in func_names}
    for pattern, func, fmt, lineno in decode_entries:
        if func not in yaml_funcs:
            errors.append(f"decode 有但 YAML 缺: {func} (line {lineno})")

    # 检查3: swym 存根特殊验证
    for rec, func_base in zip(records, func_names):
        if rec.get("mnemonic") == "swym":
            print(f"  [INFO] swym → trans_{func_base}（应为 NOP 存根）")

    # 报告
    print()
    print(f"[结果]")
    print(f"  YAML 记录数: {len(records)}")
    print(f"  decode pattern 数: {len(decode_entries)}")
    print(f"  错误数: {len(errors)}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print()
        print("validate_decodetree: FAIL")
        sys.exit(1)
    else:
        print("  OK: 所有 pattern 与 opcodes.yaml 一致")
        print()
        print("validate_decodetree: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
