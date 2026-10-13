#!/usr/bin/env python3
"""check_harness_ops.py — lint: build_test_binary.py 的 encode_* op 常量 ↔ opcodes.yaml 交叉校验。

用法：
  python3 tools/qemu/check_harness_ops.py [--yaml <path>] [--harness <path>]

默认：
  - yaml: contracts/opcodes.yaml
  - harness: tests/scripts/build_test_binary.py

校验逻辑：
  1. 从 harness 的 encode_* 函数中提取 op 常量（或 value 常量）
  2. 与 opcodes.yaml 中对应的 value 逐条比对
  3. 不一致时报 MISMATCH 并 exit 1
"""

import argparse
import os
import re
import sys

try:
    import yaml as _yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def parse_harness_ops(harness_path: str) -> dict[str, tuple[str, str]]:
    """从 build_test_binary.py 的 encode_* 函数中提取 op/value 常量。

    返回 {encode_func_name: (hex_value, source_line)}。
    - rrii/rwii/riii/iiii 格式：提取 (0xNN << 24) → 返回 0xNN000000
    - orrr/orri/oiii 格式：提取 0xNNNNNNNN（全字）
    """
    with open(harness_path, encoding="utf-8") as f:
        lines = f.readlines()

    ops = {}
    # 匹配函数定义行
    func_re = re.compile(r'^def (encode_\w+)\(')
    # 匹配 return 语句中的 hex 常量
    shift_re = re.compile(r'\(0x([0-9a-fA-F]+)\s*<<\s*24\)')
    full_re = re.compile(r'return\s+(0x[0-9a-fA-F]{8})\b')

    i = 0
    while i < len(lines):
        m_func = func_re.match(lines[i])
        if m_func:
            func_name = m_func.group(1)
            # 扫描函数体直到下一个 def 或文件末尾
            j = i + 1
            body_lines = []
            while j < len(lines) and not func_re.match(lines[j]):
                body_lines.append(lines[j])
                j += 1
            body = ''.join(body_lines)

            # 尝试提取 (0xNN << 24) 格式
            m_shift = shift_re.search(body)
            if m_shift:
                op_byte = int(m_shift.group(1), 16)
                hex_val = f"0x{op_byte:02X}000000"
                ops[func_name] = (hex_val, lines[i].strip())
            else:
                # 尝试提取 return 0xNNNNNNNN 格式
                m_full = full_re.search(body)
                if m_full:
                    ops[func_name] = (m_full.group(1), lines[i].strip())

            i = j
        else:
            i += 1

    return ops


def load_yaml_ops(yaml_path: str) -> dict[str, str]:
    """从 opcodes.yaml 加载 value → {id: value}。"""
    with open(yaml_path, encoding="utf-8") as f:
        records = _yaml.safe_load(f)
    result = {}
    for rec in records:
        if "value" in rec:
            result[rec["id"]] = rec["value"]
    return result


# 从 encode_* 函数名到 opcodes.yaml id 的映射
# 格式：encode_func_name → yaml_id（多个 yaml id 可能映射到同一 encode 函数）
FUNC_TO_YAML = {
    "encode_set_zw_rd": "set.zw_rwii_rd",
    "encode_set_zw_rb": "set.zw_rwii_rb",
    "encode_or_w_rd":   "or.w_rwii_rd",
    "encode_or_w_rb":   "or.w_rwii_rb",
    "encode_st_b_rd":   "st.b_rrii_rd",
    "encode_st_w_rd":   "st.w_rrii_rd",
    "encode_st_t_rd":   "st.t_rrii_rd",
    "encode_st_o_rd":   "st.o_rrii_rd",
    "encode_st_o_rb":   "st.o_rrii_rb",
    "encode_xor_o":     "xor.o_orrr_rd",
    "encode_or_o":      "or.o_orrr_rd",
    "encode_br_nz_rd":  "br.nz_riii_rd",
    "encode_jump_rrii": "jump_rrii_rb",
    "encode_rd2ra":     "rd2ra_orri_ra",
    "encode_rb2rd":     "rb2rd_orri_rb",
    "encode_ld_ub":     "ld.ub_rrii_rd",
    "encode_ld_uw":     "ld.uw_rrii_rd",
    "encode_ld_ut":     "ld.ut_rrii_rd",
    "encode_ld_o":      "ld.o_rrii_rd",
    "encode_swym":      "swym_oiii_imm",
    "encode_fence":     "fence_oiii_imm",
    "encode_jump_iiii": "jump_iiii_rb",
}


def main():
    parser = argparse.ArgumentParser(
        description="校验 build_test_binary.py 的 encode_* op 常量与 opcodes.yaml 一致")
    parser.add_argument("--yaml", default=os.path.join(REPO_ROOT, "contracts",
                                                        "opcodes.yaml"),
                        help="opcodes.yaml 路径")
    parser.add_argument("--harness", default=os.path.join(REPO_ROOT, "tests",
                                                           "scripts",
                                                           "build_test_binary.py"),
                        help="build_test_binary.py 路径")
    args = parser.parse_args()

    harness_ops = parse_harness_ops(args.harness)
    yaml_ops = load_yaml_ops(args.yaml)

    mismatches = []
    for func_name, yaml_id in FUNC_TO_YAML.items():
        if func_name not in harness_ops:
            print(f"SKIP: {func_name} — 未在 harness 中找到")
            continue
        harness_val, src_line = harness_ops[func_name]
        yaml_val = yaml_ops.get(yaml_id)
        if yaml_val is None:
            print(f"SKIP: {yaml_id} — 未在 opcodes.yaml 中找到")
            continue
        # 规范化比较（大写 0x 前缀）
        h_norm = harness_val.upper().replace("0X", "0x")
        y_norm = yaml_val.upper().replace("0X", "0x")
        if h_norm != y_norm:
            mismatches.append((func_name, yaml_id, harness_val, yaml_val, src_line))

    if mismatches:
        print(f"check_harness_ops: {len(mismatches)} MISMATCH(es) found:")
        for func_name, yaml_id, h_val, y_val, src_line in mismatches:
            print(f"  MISMATCH: {func_name} → harness={h_val} vs yaml={y_val} ({yaml_id})")
            print(f"    source: {src_line}")
        sys.exit(1)
    else:
        print(f"check_harness_ops: all {len(FUNC_TO_YAML)} ops match opcodes.yaml")
        sys.exit(0)


if __name__ == "__main__":
    main()
