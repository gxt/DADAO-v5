#!/usr/bin/env python3
"""check-milestone: 里程碑台账所列任务号真实存在（A2，2026-10-17）。

**核验册（``m`` 册）机制已删除**（用户 2026-11-10，经主会话转达：「m13-infra-001 的裁定
是我做的，可删掉核验册机制」；此前 2026-11-08 已定 M11 起不建 ``m`` 册、M12 起编号
``mNN-<module>-<NNNN>`` 无后缀）。本脚本不再识别或校验任何 ``m`` 册，改为直接核验
**里程碑台账**：

  - 台账来源：``--file PATH``（显式，可重复）或自动发现 ``.tao/knowledge/milestones*.md``
    （M11 的 ``milestones.md`` 若在则一并校验；M12 起为 ``milestones-m12.md`` /
    ``milestones-m13.md``）；一本都找不到 ⇒ fail-closed。
  - 每本台账须有 ``项目里程碑 = <M n>`` 断言（否则 vacuous FAIL）。
  - 台账中出现的任务号（``PREFIX-<3 位数字><后缀>`` 或 M12 起的
    ``mNN-<module>-<3–4 位数字>``）须在 ``.tao/tasks/**`` **或** ``.tao/archive/**``
    有对应任务书文件名（归档 = 已完成任务，**算「真实存在」**）；否则 FAIL。
  - 台账里零个任务号 ⇒ vacuous FAIL（扫描面为空 = 无从核验）。

配套（**里程碑收尾路径**，见 ``Makefile`` 的 ``check-milestone``）：
本脚本 + ``check_tasks.py --strict``（漏收尾 = 0）。**不入 L1**：收尾专项依赖
归档 / L3 报告等收口产物（日常不存在），日常 L1 不应常态红。

Usage:
    python3 tools/infra/check_milestone_tasks.py [--root DIR] [--file PATH] [--self-test]

``--root DIR`` 检查另一棵树（默认仓库根）；``--file PATH`` 只查指定台账（相对 ``--root``）。
Exit code: 台账缺失 / 无里程碑断言 / 任务目录缺失 / 台账零任务号 / 所列任务号不存在 ⇒ 非零。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_REL = Path(".tao") / "knowledge"
LEDGER_GLOB = "milestones*.md"
TASKS_REL = Path(".tao") / "tasks"
ARCHIVE_REL = Path(".tao") / "archive"

# 台账里程碑断言：`项目里程碑 = M8`（容忍粗体 / 反引号包裹）
CURRENT_RE = re.compile(r"项目里程碑\s*=\s*[*`]{0,2}M(\d+)\b")
# 任务号：M11 及以前 = PREFIX-<3 位数字><后缀>；M12 起 = mNN-<module>-<3–4 位数字>（无后缀）
TASK_ID_RE = re.compile(
    r"\b(?:(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?"
    r"|m\d{2}-[a-z][a-z0-9]*-\d{3,4})\b")
# 任务书文件名前缀 = 任务号
TASK_FILE_RE = re.compile(
    r"^((?:(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG|GEM5)-\d{3}[a-z]?"
    r"|m\d{2}-[a-z][a-z0-9]*-\d{3,4}))(?:-|\.md$)")


def current_milestone(text: str) -> tuple[int | None, int]:
    """返回 (台账自报里程碑号, 断言命中数)。"""
    nums = [int(m.group(1)) for m in CURRENT_RE.finditer(text)]
    return (max(nums) if nums else None), len(nums)


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


def discover_ledgers(root: Path) -> list[Path]:
    """`.tao/knowledge/milestones*.md` 下的全部台账（M11 `milestones.md` + M12 起分册）。"""
    d = root / KNOWLEDGE_REL
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob(LEDGER_GLOB) if p.is_file())


def _label(root: Path, ledger: Path) -> str:
    try:
        return ledger.relative_to(root).as_posix()
    except ValueError:
        return str(ledger)


def audit(root: Path, ledger: Path) -> int:
    """核验一本台账：里程碑断言 + 所列任务号真实存在。返回 0/1。"""
    label = _label(root, ledger)
    print("=" * 72)
    print("check-milestone — 里程碑台账所列任务号真实存在（A2）")
    print("=" * 72)

    text = ledger.read_text(encoding="utf-8")
    cur, hits = current_milestone(text)
    if cur is None:
        print(f"  [{label}] ERROR: 无「项目里程碑 = M<n>」断言 ⇒ 扫描面 vacuous")
        print("结果: FAIL (1 项)")
        return 1
    print(f"  [{label}] 项目里程碑 = M{cur}（断言 {hits} 处，取最大 n）")

    tasks_dir = root / TASKS_REL
    if not tasks_dir.is_dir():
        print(f"  [{label}] ERROR: 任务目录不存在: {TASKS_REL} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1
    index = task_index(root)
    print(f"  [{label}] 任务号索引（现场统计）: {len(index)} 个（.tao/tasks/** ∪ .tao/archive/**）")
    if not index:
        print(f"  [{label}] ERROR: 索引为空（无任何任务书）⇒ 扫描面 vacuous")
        print("结果: FAIL (1 项)")
        return 1

    ids = sorted(set(TASK_ID_RE.findall(text)))
    if not ids:
        print(f"  [{label}] ERROR: 台账未列出任何任务号 ⇒ 无法核验（vacuous）")
        print("结果: FAIL (1 项)")
        return 1
    miss = missing_ids(ids, index)
    print(f"  [{label}] 台账所列任务号 {len(ids)} 个（现场统计）；缺失 {len(miss)} 个")

    errors: list[str] = []
    for i in ids:
        where = index.get(i, "MISSING")
        if where == "MISSING":
            print(f"    MISSING {i}")
            errors.append(f"{label}: 任务号 {i} 在 .tao/tasks/** 与 .tao/archive/** 均不存在")
        elif where.startswith(ARCHIVE_REL.as_posix()):
            print(f"    {i} -> {where}（已归档）")

    print("-" * 72)
    print(f"  核验任务号（现场统计）: {len(ids)}")
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print(f"结果: PASS (M{cur}；台账所列任务号全部真实存在)")
    return 0


def _assert(name: str, expected: object, actual: object) -> bool:
    ok = expected == actual
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: expect={expected} actual={actual}")
    return ok


def _run_audit(root: Path, ledger: Path) -> tuple[int, str]:
    """跑 audit 并捕获 stdout（自检用：rc + 输出文本）。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit(root, ledger)
    return rc, buf.getvalue()


def _write_tree(root: Path, ledgers: dict[str, str], files: dict[str, str]) -> None:
    """造最小自检树：`.tao/knowledge/<台账>` + `.tao/tasks/infra/<任务书>`。"""
    (root / ".tao" / "knowledge").mkdir(parents=True)
    (root / ".tao" / "tasks" / "infra").mkdir(parents=True)
    for name, body in ledgers.items():
        (root / ".tao" / "knowledge" / name).write_text(body + "\n", encoding="utf-8")
    for name, body in files.items():
        (root / ".tao" / "tasks" / "infra" / name).write_text(body + "\n", encoding="utf-8")


def _run_main(argv: list[str]) -> tuple[int, str]:
    """以给定 argv 跑 main() 并捕获输出（自检用：覆盖台账发现 / --file 分支）。"""
    buf = io.StringIO()
    saved = sys.argv
    sys.argv = ["check_milestone_tasks.py", *argv]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = main()
    finally:
        sys.argv = saved
    return rc, buf.getvalue()


def self_test() -> int:
    print("=" * 72)
    print("check-milestone --self-test（内置反例 ⇒ 期望 FAIL）")
    print("=" * 72)
    ok = True

    text = ("| SPEC-137t | 已验证 | — | … 项目里程碑 = `M7` |\n"
            "| INFRA-085t | 已验证 | — | … 项目里程碑 = `M8` |\n"
            "## M9（规划）\n> 候选\n")
    ok &= _assert("里程碑取断言最大值（M9 规划不算）", 8, current_milestone(text)[0])
    ok &= _assert("无断言 ⇒ None", None, current_milestone("## 历史\n无断言\n")[0])

    ids = sorted(set(TASK_ID_RE.findall(
        "**依赖**：`INFRA-085t`/`056t`、`SPEC-137t`；见 `ISS-246` 与 `ADR-0025`。")))
    ok &= _assert("只抽任务号（不含 ISS/ADR）", ["INFRA-085t", "SPEC-137t"], ids)

    new_ids = sorted(set(TASK_ID_RE.findall("见 m12-infra-901 与 m12-gem5-1001；旧 INFRA-085t")))
    ok &= _assert("新编号识别（M12）",
                  ["INFRA-085t", "m12-gem5-1001", "m12-infra-901"], new_ids)
    ok &= _assert("新编号任务书文件名匹配", True,
                  bool(TASK_FILE_RE.match("m12-infra-901-描述.md")))
    ok &= _assert("非任务号文件名不匹配", False, bool(TASK_FILE_RE.match("README.md")))

    existing = {"INFRA-085t": ".tao/tasks/infra/INFRA-085t-x.md"}
    ok &= _assert("缺失号检出", ["SPEC-137t"], missing_ids(ids, existing))
    ok &= _assert("全部存在 ⇒ 空", [], missing_ids(["INFRA-085t"], existing))

    # ── 台账发现：M11 `milestones.md` + M12 起分册；其它 md 不算台账 ──
    with tempfile.TemporaryDirectory(prefix="check-milestone-selftest-") as td:
        tmp = Path(td)

        found_dir = tmp / "discover"
        _write_tree(found_dir, {"milestones.md": "项目里程碑 = M11",
                                "milestones-m12.md": "项目里程碑 = M12",
                                "milestones-m13.md": "项目里程碑 = M13",
                                "lessons.md": "不是台账"},
                    {"INFRA-085t-x.md": "正文"})
        ok &= _assert("台账自动发现（3 本，排除其它 md）", 3, len(discover_ledgers(found_dir)))
        empty_dir = tmp / "no-ledger"
        _write_tree(empty_dir, {"lessons.md": "不是台账"}, {"INFRA-085t-x.md": "正文"})
        ok &= _assert("无台账 ⇒ 发现为空", 0, len(discover_ledgers(empty_dir)))

        # ── 端到端：PASS 分支（号存在 / 号仅存于归档）──
        good = tmp / "good"
        _write_tree(good, {"milestones-m13.md": "项目里程碑 = M13\n| m13-infra-901 | 1 h | … |"},
                    {"m13-infra-901-x.md": "正文"})
        rc, out = _run_audit(good, good / ".tao/knowledge/milestones-m13.md")
        ok &= _assert("台账所列号存在 ⇒ PASS", 0, rc)
        ok &= _assert("台账所列号存在 ⇒ 不报 MISSING", False, "MISSING" in out)

        archived = tmp / "archived"
        _write_tree(archived, {"milestones-m13.md": "项目里程碑 = M13\n见 INFRA-085t"},
                    {"m13-infra-901-x.md": "正文"})
        (archived / ".tao" / "archive" / "M12" / "infra").mkdir(parents=True)
        (archived / ".tao" / "archive" / "M12" / "infra" / "INFRA-085t-x.md").write_text(
            "正文\n", encoding="utf-8")
        rc, out = _run_audit(archived, archived / ".tao/knowledge/milestones-m13.md")
        ok &= _assert("号仅存于归档 ⇒ PASS（归档算存在）", 0, rc)
        ok &= _assert("归档号 ⇒ 标注已归档", True, "（已归档）" in out)

        # ── 端到端：FAIL 分支（号不存在 / 零号 / 无断言 / 无任务目录 / 无台账）──
        missing = tmp / "missing"
        _write_tree(missing, {"milestones-m13.md": "项目里程碑 = M13\n列 INFRA-999t"},
                    {"INFRA-085t-x.md": "正文"})
        rc, out = _run_audit(missing, missing / ".tao/knowledge/milestones-m13.md")
        ok &= _assert("台账号不存在 ⇒ FAIL", 1, rc)
        ok &= _assert("台账号不存在 ⇒ 指名 MISSING", True, "MISSING INFRA-999t" in out)

        zero = tmp / "zero-ids"
        _write_tree(zero, {"milestones-m13.md": "项目里程碑 = M13\n（无任务号）"},
                    {"INFRA-085t-x.md": "正文"})
        rc, out = _run_audit(zero, zero / ".tao/knowledge/milestones-m13.md")
        ok &= _assert("台账零任务号 ⇒ FAIL", 1, rc)
        ok &= _assert("台账零任务号 ⇒ vacuous", True, "vacuous" in out)

        no_assert = tmp / "no-assert"
        _write_tree(no_assert, {"milestones-m13.md": "## 历史\n无断言\n"},
                    {"INFRA-085t-x.md": "正文"})
        rc, out = _run_audit(no_assert, no_assert / ".tao/knowledge/milestones-m13.md")
        ok &= _assert("台账无里程碑断言 ⇒ FAIL", 1, rc)
        ok &= _assert("台账无断言 ⇒ 报 vacuous", True, "vacuous" in out)

        no_tasks = tmp / "no-tasks"
        (no_tasks / ".tao" / "knowledge").mkdir(parents=True)
        (no_tasks / ".tao" / "knowledge" / "milestones-m13.md").write_text(
            "项目里程碑 = M13\n", encoding="utf-8")
        rc, out = _run_audit(no_tasks, no_tasks / ".tao/knowledge/milestones-m13.md")
        ok &= _assert("任务目录缺失 ⇒ FAIL（fail-closed）", 1, rc)
        ok &= _assert("任务目录缺失 ⇒ 指名", True, "任务目录不存在" in out)

        # ── main()：自动发现双台账 / --file 单册 / 无台账 fail-closed ──
        dual = tmp / "dual"
        _write_tree(dual, {"milestones-m12.md": "项目里程碑 = M12\n列 m12-infra-901",
                           "milestones-m13.md": "项目里程碑 = M13\n列 m13-infra-901"},
                    {"m12-infra-901-x.md": "正文", "m13-infra-901-y.md": "正文"})
        rc, out = _run_main(["--root", str(dual)])
        ok &= _assert("自动发现双台账 ⇒ PASS", 0, rc)
        ok &= _assert("自动发现 ⇒ 两本都核", True,
                      "milestones-m12.md" in out and "milestones-m13.md" in out)

        rc, out = _run_main(["--root", str(dual), "--file",
                             ".tao/knowledge/milestones-m13.md"])
        ok &= _assert("--file 单册 ⇒ PASS", 0, rc)
        ok &= _assert("--file 单册 ⇒ 只核该册", False, "milestones-m12.md" in out)

        rc, out = _run_main(["--root", str(empty_dir)])
        ok &= _assert("无任何台账 ⇒ FAIL（fail-closed）", 1, rc)
        ok &= _assert("无任何台账 ⇒ 指名", True, "未找到里程碑台账" in out)

        rc, out = _run_main(["--root", str(dual), "--file", ".tao/knowledge/nope.md"])
        ok &= _assert("--file 不存在 ⇒ FAIL", 1, rc)

    print("-" * 72)
    print("self-test: PASS" if ok else "self-test: FAIL")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None,
                        help="检查另一棵树（默认仓库根）")
    parser.add_argument("--file", type=Path, action="append", default=None,
                        help="只查指定台账（相对 --root；可重复；默认自动发现 milestones*.md）")
    parser.add_argument("--self-test", action="store_true",
                        help="跑内置反例自检（不读仓库）")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-milestone: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1

    if args.file:
        ledgers = [p if p.is_absolute() else root / p for p in args.file]
        absent = [p for p in ledgers if not p.is_file()]
        for p in absent:
            print(f"check-milestone: ERROR: 台账不存在: {_label(root, p)}", file=sys.stderr)
        if absent:
            return 1
    else:
        ledgers = discover_ledgers(root)
        if not ledgers:
            print(f"check-milestone: ERROR: 未找到里程碑台账"
                  f"（{KNOWLEDGE_REL.as_posix()}/{LEDGER_GLOB}）⇒ fail-closed",
                  file=sys.stderr)
            return 1

    print(f"  台账（现场统计）: {len(ledgers)} 本")
    rc = 0
    for ledger in ledgers:
        rc |= audit(root, ledger)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
