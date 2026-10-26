#!/usr/bin/env python3
"""llvm-test-suite 用户态 smoke 代表集（L2；TESTCASES-075t）。

`check-tset-llvm-smoke` 的载体。代表集**机械派生**，无手工清单（`Process-07 §3`）：

  1. 用真实驱动 `run_llvm_ts_user.py::discover()` 现场枚举用例；
  2. **类别 = 上游套件的三棵树**（`MultiSource/Applications`、
     `MultiSource/Benchmarks`、`SingleSource/Benchmarks`，由驱动现场给出）；
  3. 每类取**源码字节数最小**的用例（ties 按 case id）——确定性规则，既保证
     每棵树都有代表，又把 L2 耗时压在受控范围（套件里有 mafft/nbench 等
     分钟级基准，不能整树进 L2）；
  4. 结构断言：类别非空、**选出的树集合 == 现场派生的树集合**、代表不重复、
     census 自洽；计数现场统计，不写死。

选中后把逐条 `--only '^<case>$'` 交给原驱动执行；驱动语义、期望值、分类器
均**未改动**。`--list` 只打印代表集（供门控/证据核对）。

用法：
    python3 tools/testcases/tset/llvm-ts/run_smoke.py --list
    python3 tools/testcases/tset/llvm-ts/run_smoke.py --link-mode static \
        --jobs 4 --json-out /tmp/.../llvm-smoke.json
（其余参数原样转发给 `run_llvm_ts_user.py`。）
"""

from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
DRIVER = os.path.join(HERE, "run_llvm_ts_user.py")
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases"))
# HERE 最后插入 ⇒ 优先于旧路径薄 wrapper（同名模块，TESTCASES-075t）
sys.path.insert(0, HERE)

import run_llvm_ts_user as driver  # noqa: E402


def select(suite_root: str):
    """返回 (selected, discovered, excluded_n, census, corpus_trees)。

    selected = [(tree, source_bytes, case_id)]，每棵树取源码字节最小者。
    """
    cases, excluded, census = driver.discover(suite_root)
    if not cases:
        raise SystemExit(f"run_smoke: ERROR: no llvm-test-suite case under "
                         f"{suite_root} (run 'make fetch' first)")
    corpus_trees = {case.tree for case in cases}
    best = {}
    for case in cases:
        sizes = []
        for path in case.sources:
            try:
                sizes.append(os.path.getsize(path))
            except OSError as exc:
                raise SystemExit(f"run_smoke: ERROR: cannot stat {path}: {exc}")
        key = (sum(sizes), case.cid)
        if case.tree not in best or key < best[case.tree]:
            best[case.tree] = key
    selected = [(tree, best[tree][0], best[tree][1]) for tree in sorted(best)]
    return selected, len(cases), len(excluded), census, corpus_trees


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite-src", default=driver.DEFAULT_SRC,
                    help="llvm-test-suite source root (default: %(default)s)")
    ap.add_argument("--list", action="store_true", help="只打印代表集")
    args, passthrough = ap.parse_known_args()

    for owned in ("--only", "--limit"):
        if any(a == owned or a.startswith(owned + "=") for a in passthrough):
            sys.stderr.write(f"run_smoke: ERROR: {owned} is owned by the smoke "
                             "selector\n")
            return 2

    suite_root = driver.abspath(args.suite_src)
    if not os.path.isdir(suite_root):
        sys.stderr.write(f"run_smoke: ERROR: llvm-test-suite source not found: "
                         f"{suite_root} (run 'make fetch' first)\n")
        return 2

    try:
        selected, discovered, excluded_n, census, corpus_trees = select(
            suite_root)
    except driver.SetupError as exc:
        sys.stderr.write(f"run_smoke: ERROR: {exc}\n")
        return 2
    selected_trees = {row[0] for row in selected}
    ids = [row[2] for row in selected]
    errs = []
    for tree, _size, cid in selected:
        if not cid.startswith(tree + "/"):
            errs.append(f"代表 id 与树不符: {tree} -> {cid}")
    if not selected:
        errs.append("代表集为空")
    if selected_trees != corpus_trees:
        errs.append(f"树覆盖不全: 缺 {sorted(corpus_trees - selected_trees)}")
    if len(ids) != len(set(ids)):
        errs.append("代表集有重复 id")
    if not census.get("a_census_ok", False):
        errs.append("驱动 census 不自洽")

    print("check-tset-llvm-smoke: 代表集机械派生 —— 每棵树取源码最小用例")
    print(f"  corpus: {suite_root} (manifest-locked, 现场枚举)")
    print(f"  发现用例 {discovered} / 结构排除 {excluded_n} (现场统计)")
    print(f"  树数 {len(corpus_trees)} / 代表数 {len(selected)} (现场统计)")
    for tree, size, cid in selected:
        print(f"  {tree:30s} -> {cid:55s} source_bytes={size}")
    if errs:
        for err in errs:
            print(f"  FAIL: {err}")
        print("结果: FAIL (代表集结构断言)")
        return 1
    print("  结构断言: PASS (树全覆盖 / 无重复 / census)")

    if args.list:
        print("结果: PASS (--list；未执行 guest)")
        return 0

    only_args = []
    for cid in ids:
        only_args += ["--only", "^%s$" % re.escape(cid)]
    sys.argv = ([DRIVER, "--suite-src", args.suite_src] + passthrough
                + only_args)
    print("  转发: " + " ".join(only_args))
    sys.stdout.flush()
    import runpy
    runpy.run_path(DRIVER, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
