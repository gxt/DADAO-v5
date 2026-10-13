#!/usr/bin/env python3
"""SPEC-133t：`check_spec_refs` 匹配器自证（前导号剥离后的引用命中语义）。

断言（任一不满足 ⇒ 非零退出）：
- 编号引用命中：`§3.1` 命中标题 `3.1 存取RD寄存器`；`§5.1` 命中 `5.1 判定（入口 tag）`。
- 标题引用命中：`§存取RD寄存器` 命中 `3.1 存取RD寄存器`（前导号被剥离后命中）。
                 `§1. 运行模式与核芯功能扩展` 命中 `1. 运行模式与核芯功能扩展`。
- 前缀误命中不发生：`§5` 不命中 `5.1 …`；`§2.2` 不命中 `2.20 …`。
- 子串误命中不发生：`§存取RD` 不命中 `3.1 存取RD寄存器`。
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.infra.check_spec_refs import _header_matches  # noqa: E402

CASES = [
    # (header, section, expected)
    ("3.1 存取RD寄存器", "3.1", True),            # 编号引用命中
    ("5.1 判定（入口 tag）", "5.1", True),          # 编号引用命中
    ("3.1 存取RD寄存器", "存取RD寄存器", True),      # 标题引用命中（剥离前导号）
    ("1. 运行模式与核芯功能扩展", "1. 运行模式与核芯功能扩展", True),  # 带点的编号+标题命中
    ("1. 运行模式与核芯功能扩展", "运行模式与核芯功能扩展", True),      # 剥离前导号后命中
    ("5.1 判定（入口 tag）", "5", False),           # 前缀误命中不发生
    ("2.2 虚实地址转换", "2.20", False),            # 数值前缀误命中不发生
    ("3.1 存取RD寄存器", "存取RD", False),           # 子串误命中不发生
]

fails = 0
for header, section, expected in CASES:
    got = _header_matches(header, section)
    ok = (got == expected)
    if not ok:
        fails += 1
    print(f"  [{'OK' if ok else 'FAIL'}] header={header!r:40s} section={section!r:20s} "
          f"expect={expected} got={got}")

if fails:
    print(f"matcher-selftest: FAIL ({fails}/{len(CASES)})")
    sys.exit(1)
print(f"matcher-selftest: PASS ({len(CASES)}/{len(CASES)} 断言, 计数现场统计)")
sys.exit(0)
