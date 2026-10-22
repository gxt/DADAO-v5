#!/usr/bin/env python3
"""标题章节号与结构尾段校验（SPEC-133t / SPEC-165t，21 册只读册）。

正文断言（任一不满足 ⇒ 非零退出）：
1. 标题深度 ≤ 4（无 `#####`）；
2. `##` = `N.`，`###` = `N.M`，`####` = `N.M.K`（仅数字 + 单空格 + 文本）；
3. 同册内编号全局唯一；
4. 层级连续：每个父节下的子号自 1 起、逐一递增（含根：正文自 `## 1.` 起）；
5. **父节存在（层级逐级）**：每个 ≥3 级标题的父号须作为其上一级（`L-1`）标题出现
   （禁 `##` 直挂 `####` 的"孤儿父节"）；
5b. **单包装层（SPEC-166t）**：正文 `##` 恰 1 个、且其下 `###` ≥2 ⇒ 该 `##` 是纯包装层
   （册名已表明分类，无再套一级的必要）⇒ FAIL。判据只认**结构**，不看标题文字；
   计数现场统计（不写死册名）。

结构尾段断言（SPEC-165t）：
6. 尾段 = 三个**无编号**二级段：`## 附录 A：汇编指令速查`、`## 附录 B：合法性检查`、
   `## 附录：版本与变更记录`；
7. `SimRISC-01`…`SimRISC-12` 须各有 A、B 两段且顺序固定（A 在前），**不得**有变更记录附录；
8. `SimRISC-00` **不得**有 A/B（无速查/合法性章），其变更记录附录须为**最后一个** `##`；
9. 其它只读册（DADAO/Toolchain/Machine）沿用「变更记录附录为最后一个 `##`、其下不校验编号」；
10. 尾段起点之后不得再出现**带编号**的二级标题（附录 A 被挪回册首 ⇒ 正文为空 ⇒ 红）。

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

# 尾段（均为无编号结构段）
APPENDIX_A = "## 附录 A：汇编指令速查"
APPENDIX_B = "## 附录 B：合法性检查"
APPENDIX_CHANGELOG = "## 附录：版本与变更记录"
APPENDIX_TITLES = (APPENDIX_A, APPENDIX_B, APPENDIX_CHANGELOG)


def lock_paths():
    return [REPO / m.group(1) for line in LOCK.read_text().splitlines()
            if (m := re.match(r'path\s*=\s*"([^"]+)"', line))]


def tail_start(lines: list[str]) -> int:
    """首个无编号尾段的行下标（无则 len(lines)）。"""
    for i, line in enumerate(lines):
        if line.strip() in APPENDIX_TITLES:
            return i
    return len(lines)


def check_body(p: Path, lines: list[str], end: int, errors: list[str], stats: dict) -> None:
    seq = []  # (level, num_tuple, lineno)
    for ln, line in enumerate(lines[:end], 1):
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

    if not any(lvl == 2 for lvl, _n, _ln in seq):
        errors.append(f"{p.name}: 正文无任何带编号 `##` 节（附录被挪到册首？）")
        return

    # 唯一性
    seen = {}
    for lvl, num, ln in seq:
        if num in seen:
            errors.append(f"{p.name}:L{ln}: 编号重复 {'.'.join(map(str,num))}（先见于 L{seen[num]}）")
        seen[num] = ln

    # 层级连续（父 `root` 的子号自 1 起 ⇒ 正文必自 `## 1.` 开始）
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

    # 父节存在（层级逐级）
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

    # 单包装层（SPEC-166t）：正文 `##` 恰 1 个且其下 `###` ≥2
    h2 = [(num, ln) for lvl, num, ln in seq if lvl == 2]
    if len(h2) == 1:
        root = h2[0][0]
        kids = [(_n, _ln) for lvl, _n, _ln in seq if lvl == 3 and _n[:-1] == root]
        if len(kids) >= 2:
            stats["wrapper"] += 1
            errors.append(
                f"{p.name}:L{h2[0][1]}: 单包装层：正文仅 1 个 `## {'.'.join(map(str,root))}.`，"
                f"其下却有 {len(kids)} 个 `###`（应删包装层，把 `###` 升为 `##`）"
            )


def check_tail(p: Path, lines: list[str], tail: list[str], errors: list[str], stats: dict) -> None:
    is_simrisc = p.name.startswith("SimRISC-")

    # 尾段后不得再有带编号二级标题
    seen_tail = False
    for ln, line in enumerate(lines, 1):
        if line.strip() in APPENDIX_TITLES:
            seen_tail = True
            continue
        if seen_tail and line.startswith("## ") and not line.startswith("## 附录"):
            errors.append(f"{p.name}:L{ln}: 附录段之后出现带编号 `##` 节: {line[:60]}")

    if is_simrisc and not p.name.startswith("SimRISC-00"):
        if APPENDIX_A not in tail:
            errors.append(f"{p.name}: 缺少 `{APPENDIX_A}`")
        if APPENDIX_B not in tail:
            errors.append(f"{p.name}: 缺少 `{APPENDIX_B}`")
        if APPENDIX_CHANGELOG in tail:
            errors.append(f"{p.name}: 变更记录附录只允许出现在 SimRISC-00")
        if APPENDIX_A in tail and APPENDIX_B in tail:
            if tail.index(APPENDIX_A) > tail.index(APPENDIX_B):
                errors.append(f"{p.name}: 附录顺序错误（须 A → B）")
        stats["with_a"] += APPENDIX_A in tail
        stats["with_b"] += APPENDIX_B in tail
    elif p.name.startswith("SimRISC-00"):
        for disallowed in (APPENDIX_A, APPENDIX_B):
            if disallowed in tail:
                errors.append(f"{p.name}: `{disallowed}` 不应出现在本册（无速查/合法性章）")
        if APPENDIX_CHANGELOG not in tail:
            errors.append(f"{p.name}: 缺少 `{APPENDIX_CHANGELOG}`")
        else:
            stats["changelog"] += 1
            idx = [i for i, l in enumerate(lines) if l.strip() == APPENDIX_CHANGELOG][-1]
            rest = [l for l in lines[idx + 1:] if l.startswith("## ") or l.startswith("# ")]
            if rest:
                errors.append(f"{p.name}: 变更记录附录不是最后一个 `##`（其后有 {rest[0][:40]!r}）")
    else:
        # 其它只读册：变更记录附录（若有）须为最后一个 `##`
        if APPENDIX_CHANGELOG in tail:
            stats["changelog"] += 1
            idx = [i for i, l in enumerate(lines) if l.strip() == APPENDIX_CHANGELOG][-1]
            rest = [l for l in lines[idx + 1:] if l.startswith("## ") or l.startswith("# ")]
            if rest:
                errors.append(f"{p.name}: 变更记录附录不是最后一个 `##`（其后有 {rest[0][:40]!r}）")


def main():
    files = lock_paths()
    errors: list[str] = []
    stats = {"h2": 0, "h3": 0, "h4": 0, "h5plus": 0, "wrapper": 0,
             "with_a": 0, "with_b": 0, "changelog": 0}
    for p in files:
        lines = p.read_text(encoding="utf-8").splitlines()
        end = tail_start(lines)
        check_body(p, lines, end, errors, stats)
        check_tail(p, lines, [l.strip() for l in lines[end:] if l.strip().startswith("## ")], errors, stats)

    total = stats["h2"] + stats["h3"] + stats["h4"]
    print(f"files={len(files)}  h2={stats['h2']}  h3={stats['h3']}  h4={stats['h4']}  "
          f"h5+={stats['h5plus']}  wrapper={stats['wrapper']}  total={total}  appendixA={stats['with_a']}  "
          f"appendixB={stats['with_b']}  changelog={stats['changelog']}")
    if errors:
        print(f"check-numbering: FAIL ({len(errors)} violation(s))")
        for e in errors:
            print("  " + e)
        return 1
    print("check-numbering: PASS (正文编号唯一连续、父节逐级、无单包装层、深度 ≤ 4；附录 A→B 顺序、"
          "变更记录仅 SimRISC-00 且为末段)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
