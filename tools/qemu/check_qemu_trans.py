#!/usr/bin/env python3
"""check_qemu_trans.py — lint: 每条 insn 是否有对应的 trans_* 函数定义。

用法：
  python3 tools/qemu/check_qemu_trans.py [--yaml <opcodes.yaml>] [--src <patches_dir>] [--strict]

默认：
  - 读 contracts/opcodes.yaml
  - 递归搜索 components/qemu/patches/ 下的 **.patch**（树形补丁集：`<上游相对路径>.patch`）
  - 默认 exit 0；--strict 且存在缺失时 exit 1
  - 扫不到任何补丁文件时**无条件**非零退出（无法校验 ≠ 通过）
"""

import argparse
import glob
import os
import re
import sys

# 复用 validate_decodetree 的命名函数（DRY）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from validate_decodetree import build_unique_func_names  # noqa: E402

try:
    import yaml as _yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def collect_trans_defs(src_dir):
    """从 patch 文件中收集所有 trans_* 函数定义名（精确匹配）。

    补丁集为树形（`patches/<上游相对路径>.patch`），故须**递归**搜索。
    返回 (定义名集合, 补丁文件数)。
    """
    trans_defs = set()
    patch_files = sorted(glob.glob(os.path.join(src_dir, "**", "*.patch"),
                                   recursive=True))
    pattern = re.compile(r'static\s+bool\s+(trans_\w+)\s*\(')
    for pf in patch_files:
        with open(pf, encoding="utf-8") as f:
            for line in f:
                # patch 格式：+ 前缀表示新增行；匹配定义
                # 但也搜索上下文行，因为有些定义在旧代码中
                m = pattern.search(line)
                if m:
                    trans_defs.add(m.group(1))
    return trans_defs, len(patch_files)


def main():
    parser = argparse.ArgumentParser(
        description="检查每条 insn 是否有对应的 trans_* 函数定义")
    parser.add_argument("--yaml", default=os.path.join(REPO_ROOT, "contracts",
                                                        "opcodes.yaml"),
                        help="opcodes.yaml 路径（默认 contracts/opcodes.yaml）")
    parser.add_argument("--src", "--patches",
                        default=os.path.join(REPO_ROOT, "components", "qemu",
                                             "patches"),
                        help="patch 文件目录（默认 components/qemu/patches/）")
    parser.add_argument("--strict", action="store_true",
                        help="存在缺失时 exit 1（默认 exit 0）")
    args = parser.parse_args()

    # 加载 opcodes.yaml
    with open(args.yaml, encoding="utf-8") as f:
        records = _yaml.safe_load(f)

    # 派生 trans_* 函数名
    func_names = build_unique_func_names(records)

    # 收集源中的 trans 定义
    trans_defs, n_patches = collect_trans_defs(args.src)
    if n_patches == 0:
        sys.exit(f"ERROR: 在 {args.src} 下未找到任何 .patch 文件；"
                 "无法校验（补丁集为树形，请检查 --src 是否为 patches/ 根）")

    # 比对
    missing = []
    for rec, func_name in zip(records, func_names):
        expected = f"trans_{func_name}"
        if expected not in trans_defs:
            is_m1 = not rec.get("excluded_m1", False)
            missing.append({
                "insn": rec["insn"],
                "func": expected,
                "is_m1": is_m1,
            })

    # 分 M1 / excluded 统计
    total = len(records)
    m1_total = sum(1 for r in records if not r.get("excluded_m1", False))

    missing_total = len(missing)
    found_total = total - missing_total
    missing_m1 = sum(1 for m in missing if m["is_m1"])
    found_m1 = m1_total - missing_m1

    # 输出 MISSING 明细
    for m in missing:
        tag = " [M1]" if m["is_m1"] else ""
        print(f"MISSING: {m['insn']} -> {m['func']}{tag}")

    # 汇总
    print(f"check_qemu_trans: {found_total}/{total} insns have trans impl"
          f" (M1 {found_m1}/{m1_total})")

    if args.strict and missing_total > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
