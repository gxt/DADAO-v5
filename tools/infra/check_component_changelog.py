#!/usr/bin/env python3
"""check-component-changelog: L1 组件 changelog 形态门控（INFRA-084t）。

体例真源：`docs/Process-01-组件补丁组织与构建编排.md §10` — 组件 changelog 为
**列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**` +
**摘要另起缩进行** `  - 摘要：<正文>`；节 = `## M<k>`（节序 M1→M2→…）。

本门控**只做形态断言**（**5 条**；**不做**内容/语义校验，**不**解析表格、**不** `split('|')`）：

  ① 不得出现**表格分隔行**（形如 `| --- |` / `|---|---|`）；
  ② 每条条目形如 `^- \\*\\*<YYYY-MM-DD>`（顶格 `- **` + 日期；所有顶格 `- ` 行都须是条目）；
  ③ 每条条目**紧接着**一条**缩进行**（摘要，形如 `  - 摘要：`）；
  ④ 存在 `^## M\\d+` 节、且**节序严格递增**（至少 1 节）；
  ⑤ **覆盖全部** `components/*/changelog.md`（现场 glob 派生；命中文件集为空 ⇒ **vacuous FAIL**）。

计数一律**现场统计**、不写死（`lessons §2`）。任一断言失败 ⇒ rc=1。

`--self-test`：在 `/tmp/opencode/INFRA-084t/` 的**临时树**上逐条注入反例 ⇒ 断言可达 FAIL，
`cp` + md5 还原后回绿（**不改真实仓库**；**禁** `git checkout`/`restore`/`stash`）。

`--root DIR` 仅供 self-test / 复用（默认仓库根）：断言 ⑤ 的「扫描面为空」需要它。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TMP_BASE = Path("/tmp/opencode/INFRA-084t")

ENTRY_RE = re.compile(r"^- \*\*\d{4}-\d{2}-\d{2}")
TOP_BULLET_RE = re.compile(r"^- ")
SUMMARY_RE = re.compile(r"^ +- 摘要：")
SECTION_RE = re.compile(r"^## M(\d+)\s*$")


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _is_table_separator(line: str) -> bool:
    """形如 `|---|---|` / `| --- |`（只含 `|`/`-`/`:`/空白，且含 `|` 与 ≥2 个 `-`）。"""
    s = line.strip()
    if "|" not in s or s.count("-") < 2:
        return False
    return set(s) <= set("|:- \t")


def check_text(text: str) -> list[tuple[str, bool, str]]:
    lines = text.split("\n")
    out: list[tuple[str, bool, str]] = []

    seps = [i + 1 for i, l in enumerate(lines) if _is_table_separator(l)]
    out.append(("① 无表格分隔行", not seps,
                f"分隔行 {len(seps)} 处" + (f"（行 {seps[:5]}）" if seps else "")))

    bullets = [(i, l) for i, l in enumerate(lines) if TOP_BULLET_RE.match(l)]
    bad = [(i + 1, l) for i, l in bullets if not ENTRY_RE.match(l)]
    out.append(("② 条目头形态", not bad,
                f"{len(bullets) - len(bad)}/{len(bullets)} 条形如 `- **<YYYY-MM-DD> …**`"
                + (f"；越形 {len(bad)} 处（行 {[b[0] for b in bad[:5]]}）" if bad else "")))

    entries = [i for i, l in enumerate(lines) if ENTRY_RE.match(l)]
    no_sum = [i + 1 for i in entries
              if i + 1 >= len(lines) or not SUMMARY_RE.match(lines[i + 1])]
    out.append(("③ 摘要缩进行", not no_sum,
                f"{len(entries) - len(no_sum)}/{len(entries)} 条紧接 `  - 摘要：` 缩进行"
                + (f"；缺摘要 {len(no_sum)} 处（行 {no_sum[:5]}）" if no_sum else "")))

    nums = [int(m.group(1)) for m in (SECTION_RE.match(l) for l in lines) if m]
    order_ok = bool(nums) and all(b > a for a, b in zip(nums, nums[1:]))
    out.append(("④ 里程碑分节", order_ok,
                f"{len(nums)} 节 M{nums}，节序严格递增={order_ok}"
                if nums else "0 节（缺 `## M<k>`）"))
    return out


def check_tree(root: Path) -> tuple[bool, list[str]]:
    files = sorted((root / "components").glob("*/changelog.md"))
    lines: list[str] = []
    if not files:
        lines.append("  [FAIL] ⑤ 覆盖检查: components/*/changelog.md 扫描面为空 —— vacuous FAIL")
        lines.append("check-component-changelog: FAIL")
        return False, lines
    lines.append(f"  [PASS] ⑤ 覆盖检查: {len(files)} 个 components/*/changelog.md（现场 glob 派生）")
    allok = True
    total = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        checks = check_text(text)
        n_entries = sum(1 for l in text.split("\n") if ENTRY_RE.match(l))
        n_sec = sum(1 for l in text.split("\n") if SECTION_RE.match(l))
        lines.append(f"  {path.relative_to(root).as_posix()}（{n_entries} 条 / {n_sec} 节）")
        for name, ok, detail in checks:
            allok = allok and ok
            total += 1
            lines.append(f"    [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    lines.append(f"  汇总: {len(files)} 文件 × 4 断言 = {total} 项（现场统计）")
    lines.append(f"check-component-changelog: {'PASS' if allok else 'FAIL'}")
    return allok, lines


def _copy_pristine(tmp: Path) -> dict[str, str]:
    dst = tmp / "components"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    sums: dict[str, str] = {}
    for p in sorted((REPO_ROOT / "components").glob("*/changelog.md")):
        target = dst / p.parent.name / "changelog.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        sums[target.relative_to(tmp).as_posix()] = md5(target)
    return sums


def self_test() -> int:
    tmp = TMP_BASE / "self-test-l1"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    sums = _copy_pristine(tmp)
    rel = "components/llvm-project/changelog.md"
    rc_all = 0

    ok, out = check_tree(tmp)
    print(f"  [self-test] 基线（未注入）rc={0 if ok else 1}")
    if not ok:
        print("check-component-changelog: --self-test FAIL — 基线不绿")
        return 1
    print(f"  [self-test] 基线覆盖: {[l.strip() for l in out if '⑤' in l][0]}")

    def run_inject(name: str, expect: str, mutate, root: Path | None = None) -> None:
        nonlocal rc_all
        if root is None:
            path = tmp / rel
            lines = path.read_text(encoding="utf-8").split("\n")
            path.write_text("\n".join(mutate(lines)), encoding="utf-8")
            target = tmp
        else:
            target = root
        ok2, out2 = check_tree(target)
        fails = [l.strip() for l in out2 if "[FAIL]" in l]
        hit = any(expect in f for f in fails)
        print(f"  [self-test] 注入「{name}」⇒ rc={0 if ok2 else 1}（期望 FAIL，命中 `{expect}`={hit}）")
        for f in fails:
            print(f"      {f}")
        if root is None:
            shutil.copy2(REPO_ROOT / rel, tmp / rel)
            restored = md5(tmp / rel) == sums[rel]
            ok3, _ = check_tree(tmp)
            print(f"      cp+md5 还原后 rc={0 if ok3 else 1}（还原前 md5 对账={restored}）")
            if not ok3 or not restored:
                rc_all = 1
        if ok2 or not hit:
            rc_all = 1

    def inj_sep(lines: list[str]) -> list[str]:
        i = next(i for i, l in enumerate(lines) if SECTION_RE.match(l))
        return lines[:i] + ["|---|---|"] + lines[i:]

    def inj_head(lines: list[str]) -> list[str]:
        i = next(i for i, l in enumerate(lines) if ENTRY_RE.match(l))
        lines[i] = lines[i].replace("- **", "- ", 1)
        return lines

    def inj_summary(lines: list[str]) -> list[str]:
        i = next(i for i, l in enumerate(lines) if SUMMARY_RE.match(l))
        del lines[i]
        return lines

    def inj_section_order(lines: list[str]) -> list[str]:
        secs = [j for j, l in enumerate(lines) if SECTION_RE.match(l)]
        j = secs[-1]
        lines[j] = "## M0"
        return lines

    def inj_section_missing(lines: list[str]) -> list[str]:
        return [l for l in lines if not SECTION_RE.match(l)]

    empty = TMP_BASE / "self-test-empty-tree"
    if empty.exists():
        shutil.rmtree(empty)
    empty.mkdir(parents=True)

    run_inject("① 插表格分隔行 ⇒ ① FAIL", "① 无表格分隔行", inj_sep)
    run_inject("② 改条目头形态（去 `**`）⇒ ② FAIL", "② 条目头形态", inj_head)
    run_inject("③ 删摘要行 ⇒ ③ FAIL", "③ 摘要缩进行", inj_summary)
    run_inject("④ 乱节序（末节 M8→M0）⇒ ④ FAIL", "④ 里程碑分节", inj_section_order)
    run_inject("④b 缺节（删全部 `## M`）⇒ ④ FAIL", "④ 里程碑分节", inj_section_missing)
    run_inject("⑤ 扫描面为空（空树）⇒ ⑤ vacuous FAIL", "⑤ 覆盖检查", None, root=empty)

    ok_real, _ = check_tree(REPO_ROOT)
    print(f"  [self-test] 真实仓库复跑 rc={0 if ok_real else 1}")
    if not ok_real:
        rc_all = 1
    print(f"check-component-changelog: --self-test {'PASS' if rc_all == 0 else 'FAIL'}")
    return rc_all


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO_ROOT))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    print("check-component-changelog — L1 组件 changelog 形态门控（列表式 + 按里程碑分节）")
    ok, lines = check_tree(Path(args.root))
    for line in lines:
        print(line)
    print("-" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
