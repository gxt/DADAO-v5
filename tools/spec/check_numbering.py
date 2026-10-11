#!/usr/bin/env python3
"""SPEC-133t 标题章节号结构性校验（21 册只读册）。

断言（任一不满足 ⇒ 非零退出）：
1. 标题深度 ≤ 4（无 `#####`）；
2. `##` = `N.`，`###` = `N.M`，`####` = `N.M.K`（仅数字 + 单空格 + 文本）；
3. 同册内编号全局唯一；
4. 层级连续：每个父节下的子号自 1 起、逐一递增；
5. **父节存在（层级逐级）**：每个 ≥3 级标题的父号须作为其上一级（`L-1`）标题出现
   （禁 `##` 直挂 `####` 的"孤儿父节"）。
所有计数**现场统计**（不写死）。
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCK = REPO / "manifests" / "spec-readonly.lock.toml"

HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# `##` → `N.` ; `###` → `N.M` ; `####` → `N.M.K`
H2_RE = re.compile(r"^(\d+)\.\s+\S")
H3_RE = re.compile(r"^(\d+)\.(\d+)\s+\S")
H4_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\s+\S")


def lock_paths():
    return [REPO / m.group(1) for line in LOCK.read_text().splitlines()
            if (m := re.match(r'path\s*=\s*"([^"]+)"', line))]


def main():
    files = lock_paths()
    errors = []
    stats = {"h2": 0, "h3": 0, "h4": 0, "h5plus": 0}
    for p in files:
        lines = p.read_text(encoding="utf-8").splitlines()
        seq = []  # (level, num_tuple, lineno)
        for ln, line in enumerate(lines, 1):
            m = HEADER_RE.match(line)
            if not m:
                continue
            lvl = len(m.group(1))
            title = m.group(2)
            if lvl == 1:
                continue
            if lvl > 4:
                stats["h5plus"] += 1
                errors.append(f"{p.name}:L{ln}: 深度 >4（{lvl} 级）: {line}")
                continue
            stats[f"h{lvl}"] += 1
            if lvl == 2:
                mm = H2_RE.match(title)
                num = (int(mm.group(1)),) if mm else None
            elif lvl == 3:
                mm = H3_RE.match(title)
                num = (int(mm.group(1)), int(mm.group(2))) if mm else None
            else:
                mm = H4_RE.match(title)
                num = (int(mm.group(1)), int(mm.group(2)), int(mm.group(3))) if mm else None
            if num is None:
                errors.append(f"{p.name}:L{ln}: 编号不符 `N`/`N.M`/`N.M.K` 形: {line}")
                continue
            seq.append((lvl, num, ln))

        # 唯一性
        seen = {}
        for lvl, num, ln in seq:
            if num in seen:
                errors.append(f"{p.name}:L{ln}: 编号重复 {'.'.join(map(str,num))}（先见于 L{seen[num]}）")
            seen[num] = ln

        # 层级连续
        expected = {}  # parent_num -> next child index
        for lvl, num, ln in seq:
            parent = num[:-1]
            idx = num[-1]
            want = expected.get(parent, 1)
            if idx != want:
                errors.append(
                    f"{p.name}:L{ln}: 编号不连续 {'.'.join(map(str,num))}（父 {parent or 'root'} 期望第 {want} 个子）"
                )
            expected[parent] = idx + 1

        # 父节存在（层级逐级）：L 级（L≥3）标题的父号须在 (L-1) 级标题集内
        by_level = {}
        for lvl, num, _ln in seq:
            by_level.setdefault(lvl, set()).add(num)
        for lvl, num, ln in seq:
            if lvl < 3:
                continue
            parent = num[:-1]
            if parent not in by_level.get(lvl - 1, set()):
                up = ".".join(map(str, parent)) or "root"
                errors.append(
                    f"{p.name}:L{ln}: 父节缺失 {'.'.join(map(str,num))}"
                    f"（无 {lvl-1} 级标题 {up}；禁跳级）"
                )

    total = stats["h2"] + stats["h3"] + stats["h4"]
    print(f"files={len(files)}  h2={stats['h2']}  h3={stats['h3']}  h4={stats['h4']}  h5+={stats['h5plus']}  total={total}")
    if errors:
        print(f"check-numbering: FAIL ({len(errors)} violation(s))")
        for e in errors:
            print("  " + e)
        return 1
    print("check-numbering: PASS (21 册编号唯一且连续、父节逐级、深度 ≤ 4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
