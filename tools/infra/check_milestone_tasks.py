#!/usr/bin/env python3
"""check-milestone: 当前里程碑的 ``m`` 册存在 + 其列出的任务号真实存在（A2，2026-10-17）。

背景：``m`` 册（``.tao/tasks/<模块>/<PREFIX>-<nnn>m-<描述>.md``）是模块里程碑的
**核验载体**：它逐条引用本期任务号、给出核验结论。两类漏项会让里程碑「看起来
做完了」而实际没收口：

  ① **漏开 ``m`` 册**——当前里程碑已推进，但没有模块里程碑核验册；
  ② **漏立任务**——``m`` 册里列了某个任务号，但 ``.tao/tasks/**`` 里根本没有
     对应的任务书（号是凭记忆写的 / 册被删了）。

本门控把它们落为机械判据（**fail-closed**）：

  - **当前里程碑** = ``.tao/knowledge/milestones.md`` 中 ``项目里程碑 = <M n>``
    断言的**最大 n**（现场统计；``M9（规划）`` 之类不构成断言）。
    无任何断言 ⇒ vacuous FAIL。
  - **① ``m`` 册存在**：``.tao/tasks/**`` 下须有 ``<PREFIX>-<nnn>m-*.md``；
    若该册**自报**里程碑（头部 ``**项目里程碑**：M n``，或文件名里的 ``-M n-``
    标签）且与当前不符 ⇒ FAIL（防「拿旧册顶替」）。
  - **② 任务号真实存在**：``m`` 册正文出现的全部任务号
    （``INFRA/SPEC/LLVM/QEMU/TESTCASES/INTEG-<3 位数字><后缀>``）须在
    ``.tao/tasks/**`` **或** ``.tao/archive/**`` 有对应任务书文件名
    （归档册 = 已完成任务，**算「真实存在」**）；否则 FAIL。
    ``m`` 册一个任务号都没列 ⇒ vacuous FAIL（无法核验）。

配套（**里程碑收尾路径**，见 ``Makefile`` 的 ``check-milestone``）：
本脚本 + ``check_tasks.py --strict``（漏收尾 = 0）。**不入 L1**：``m`` 册未建前
本门控必然红（预期收口信号），日常 L1 不应常态红。

Usage:
    python3 tools/infra/check_milestone_tasks.py [--root DIR] [--self-test]

``--root DIR`` 检查另一棵树（默认仓库根）。
Exit code: 无 ``m`` 册 / 任务号不存在 / 里程碑标签不符 / vacuous ⇒ 非零。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MILESTONES_REL = Path(".tao") / "knowledge" / "milestones.md"
TASKS_REL = Path(".tao") / "tasks"
ARCHIVE_REL = Path(".tao") / "archive"

# 当前里程碑断言：`项目里程碑 = M8`（容忍粗体 / 反引号包裹）
CURRENT_RE = re.compile(r"项目里程碑\s*=\s*[*`]{0,2}M(\d+)\b")
# m 册命名惯例：<PREFIX>-<nnn>m-<描述>.md
MBOOK_NAME_RE = re.compile(r"^[A-Z]+-\d{3}m-.*\.md$")
# m 册头部自报里程碑：`**项目里程碑**：M8`
FIELD_M_RE = re.compile(r"\*\*项目里程碑\*\*[：:]\s*[*`]{0,2}M(\d+)\b")
# 文件名里程碑标签：`-M8-`
NAME_M_RE = re.compile(r"(?:^|[-_])M(\d+)(?:[-_.]|$)")
# 任务号：PREFIX-<3 位数字><后缀>
TASK_ID_RE = re.compile(r"\b(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG)-\d{3}[a-z]?\b")
# 任务书文件名前缀 = 任务号
TASK_FILE_RE = re.compile(r"^((?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG)-\d{3}[a-z]?)(?:-|\.md$)")


def current_milestone(text: str) -> tuple[int | None, int]:
    """返回 (当前里程碑号, 断言命中数)。"""
    nums = [int(m.group(1)) for m in CURRENT_RE.finditer(text)]
    return (max(nums) if nums else None), len(nums)


def declared_milestones(name: str, text: str) -> set[int]:
    """m 册自报的里程碑号集合（头部字段 + 文件名标签）。"""
    found: set[int] = set()
    m = FIELD_M_RE.search(text)
    if m:
        found.add(int(m.group(1)))
    m2 = NAME_M_RE.search(name)
    if m2:
        found.add(int(m2.group(1)))
    return found


def missing_ids(ids: list[str], existing: dict[str, str]) -> list[str]:
    return [i for i in ids if i not in existing]


def task_index(root: Path) -> dict[str, str]:
    """任务号 → 相对路径（`.tao/tasks/**` 优先，其次 `.tao/archive/**`）。"""
    index: dict[str, str] = {}
    for reldir in (ARCHIVE_REL, TASKS_REL):  # tasks 后写 ⇒ 覆盖 archive
        d = root / reldir
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.md")):
            m = TASK_FILE_RE.match(p.name)
            if m:
                index[m.group(1)] = p.relative_to(root).as_posix()
    return index


def audit(root: Path) -> int:
    print("=" * 72)
    print("check-milestone — 当前里程碑 m 册 + 所列任务号真实存在（A2）")
    print("=" * 72)

    errors: list[str] = []

    ms_path = root / MILESTONES_REL
    if not ms_path.is_file():
        print(f"  ERROR: 里程碑台账不存在: {MILESTONES_REL} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    cur, hits = current_milestone(ms_path.read_text(encoding="utf-8"))
    if cur is None:
        print(f"  ERROR: {MILESTONES_REL} 中无「项目里程碑 = M<n>」断言 ⇒ 扫描面 vacuous")
        print("结果: FAIL (1 项)")
        return 1
    print(f"  当前里程碑（现场统计）: M{cur}（`项目里程碑 = M<n>` 断言 {hits} 处，取最大 n）")

    tasks_dir = root / TASKS_REL
    if not tasks_dir.is_dir():
        print(f"  ERROR: 任务目录不存在: {TASKS_REL} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    all_md = sorted(p for p in tasks_dir.rglob("*.md") if p.is_file())
    books = [p for p in all_md if MBOOK_NAME_RE.match(p.name)]
    print(f"  `.tao/tasks/**` 任务书（现场统计）: {len(all_md)} 份；其中 m 册: {len(books)} 份")

    qualified: list[Path] = []
    for p in books:
        rel = p.relative_to(root).as_posix()
        declared = declared_milestones(p.name, p.read_text(encoding="utf-8"))
        if declared and cur not in declared:
            errors.append(f"{rel}: m 册自报里程碑 {sorted('M%d' % d for d in declared)} "
                          f"≠ 当前 M{cur}（不得以旧册顶替）")
            print(f"  [{rel}] 里程碑标签不符: {sorted('M%d' % d for d in declared)}")
            continue
        qualified.append(p)
        print(f"  [{rel}] 里程碑标签: "
              f"{sorted('M%d' % d for d in declared) if declared else '（未自报，按命名惯例归当前）'}")

    if not qualified:
        errors.append(f"当前里程碑 M{cur} 在 .tao/tasks/** 下无 m 册（里程碑核验册未开）")
        print(f"  ERROR: 当前里程碑 M{cur} 无 m 册 ⇒ ① 漏开")

    index = task_index(root)
    print(f"  任务号索引（现场统计）: {len(index)} 个（.tao/tasks/** ∪ .tao/archive/**）")

    checked = 0
    for p in qualified:
        rel = p.relative_to(root).as_posix()
        ids = sorted(set(TASK_ID_RE.findall(p.read_text(encoding="utf-8"))))
        if not ids:
            errors.append(f"{rel}: 未列出任何任务号 ⇒ ② 无法核验（vacuous）")
            print(f"  [{rel}] ERROR: 未列出任何任务号 ⇒ vacuous")
            continue
        miss = missing_ids(ids, index)
        checked += len(ids)
        print(f"  [{rel}] 列出任务号 {len(ids)} 个（现场统计）；缺失 {len(miss)} 个")
        for i in ids:
            where = index.get(i, "MISSING")
            if where == "MISSING":
                print(f"    MISSING {i}")
                errors.append(f"{rel}: 任务号 {i} 在 .tao/tasks/** 与 .tao/archive/** 均不存在")
            elif where.startswith(ARCHIVE_REL.as_posix()):
                print(f"    {i} -> {where}（已归档）")

    print("-" * 72)
    print(f"  核验任务号（现场统计）: {checked}")
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print(f"结果: PASS (M{cur} 有 m 册；所列任务号全部真实存在)")
    return 0


def _assert(name: str, expected: object, actual: object) -> bool:
    ok = expected == actual
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: expect={expected} actual={actual}")
    return ok


def self_test() -> int:
    print("=" * 72)
    print("check-milestone --self-test（内置反例 ⇒ 期望 FAIL）")
    print("=" * 72)
    ok = True

    text = ("| SPEC-137t | 已验证 | — | … 项目里程碑 = `M7` |\n"
            "| INFRA-085t | 已验证 | — | … 项目里程碑 = `M8` |\n"
            "## M9（规划）\n> 候选\n")
    ok &= _assert("当前里程碑取断言最大值（M9 规划不算）", 8, current_milestone(text)[0])
    ok &= _assert("无断言 ⇒ None", None, current_milestone("## 历史\n无断言\n")[0])

    ok &= _assert("头部自报 M8", {8},
                  declared_milestones("INFRA-086m-核验.md", "**项目里程碑**：M8"))
    ok &= _assert("文件名标签 M7", {7},
                  declared_milestones("INFRA-072m-M7-infra模块里程碑核验.md", "无头部"))
    ok &= _assert("未自报 ⇒ 空集", set(),
                  declared_milestones("INFRA-086m-infra模块里程碑核验.md", "无头部"))

    ids = sorted(set(TASK_ID_RE.findall(
        "**依赖**：`INFRA-085t`/`056t`、`SPEC-137t`；见 `ISS-246` 与 `ADR-0025`。")))
    ok &= _assert("只抽任务号（不含 ISS/ADR）", ["INFRA-085t", "SPEC-137t"], ids)

    existing = {"INFRA-085t": ".tao/tasks/infra/INFRA-085t-x.md"}
    ok &= _assert("缺失号检出", ["SPEC-137t"], missing_ids(ids, existing))
    ok &= _assert("全部存在 ⇒ 空", [], missing_ids(["INFRA-085t"], existing))

    # 命名惯例：<PREFIX>-<nnn>m-*.md 命中，t 册 / k 册不命中
    ok &= _assert("m 册命名命中", True, bool(MBOOK_NAME_RE.match("INFRA-086m-infra模块里程碑核验.md")))
    ok &= _assert("t 册命名不命中", False, bool(MBOOK_NAME_RE.match("INFRA-086t-门控.md")))

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None,
                        help="检查另一棵树（默认仓库根）")
    parser.add_argument("--self-test", action="store_true",
                        help="跑内置反例自检（不读仓库）")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-milestone: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
