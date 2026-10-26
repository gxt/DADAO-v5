#!/usr/bin/env python3
"""libc-test 用户态 smoke 代表集（L2；TESTCASES-075t）。

`check-tset-libc-smoke` 的载体。代表集**机械派生**，无手工清单（`Process-07 §3`）：

  1. 用真实驱动 `run_libc_test_user_suite.py::discover()` 现场枚举用例；
  2. **类别 = 语料顶层目录**（`api` / `functional` / `math` / `musl` /
     `regression`，由上游目录结构决定，不写死清单）；
  3. 每类取**源码字节数最小**的用例（ties 按 case id）——确定性规则，既保证
     每类都有代表，又把 L2 耗时压在受控范围；
  4. 结构断言：类别非空、**选出的类别集合 == 现场派生的语料类别集合**、代表
     不重复、census 自洽；计数现场统计，不写死。

选中后把 `--filter '^(a|b|...)$'` 交给原驱动执行；驱动语义、期望值、分类器
均**未改动**。`--list` 只打印代表集（供门控/证据核对）。

用法：
    python3 tools/testcases/tset/libc-test/run_smoke.py --list
    python3 tools/testcases/tset/libc-test/run_smoke.py --link-mode static \
        --json-out /tmp/.../libc-smoke.json
（其余参数原样转发给 `run_libc_test_user_suite.py`。）
"""

from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
DRIVER = os.path.join(HERE, "run_libc_test_user_suite.py")
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases"))
# HERE 最后插入 ⇒ 优先于旧路径薄 wrapper（同名模块，TESTCASES-075t）
sys.path.insert(0, HERE)

import run_libc_test_user_suite as driver  # noqa: E402


def select(src_root: str):
    """返回 (selected, discovered, excluded_n, census, corpus_categories)。

    selected = [(category, source_bytes, case_id)]，每类取源码字节最小者。
    """
    cases, excluded, census = driver.discover(src_root)
    if not cases:
        raise SystemExit(f"run_smoke: ERROR: no libc-test case under {src_root} "
                         "(run 'make fetch' first)")
    # 类别从**源码路径**独立派生（不直接用 case.cid，避免与选择逻辑同源恒真）。
    corpus_categories = set()
    for case in cases:
        for path in case.sources:
            rel = os.path.relpath(path, src_root)
            if not rel.startswith(".." + os.sep) and rel != "..":
                corpus_categories.add(rel.split(os.sep)[0])
    best = {}
    for case in cases:
        sizes = []
        for path in case.sources:
            try:
                sizes.append(os.path.getsize(path))
            except OSError as exc:
                raise SystemExit(f"run_smoke: ERROR: cannot stat {path}: {exc}")
        key = (sum(sizes), case.cid)
        category = case.cid.split("/")[0]
        if category not in best or key < best[category]:
            best[category] = key
    selected = [(cat, best[cat][0], best[cat][1]) for cat in sorted(best)]
    return selected, len(cases), len(excluded), census, corpus_categories


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=driver.DEFAULT_SRC,
                    help="libc-test source root (default: %(default)s)")
    ap.add_argument("--list", action="store_true", help="只打印代表集")
    args, passthrough = ap.parse_known_args()

    if any(a == "--filter" or a.startswith("--filter=") for a in passthrough):
        sys.stderr.write("run_smoke: ERROR: --filter is owned by the smoke "
                         "selector\n")
        return 2

    src_root = os.path.join(driver.abspath(args.src), "src")
    if not os.path.isdir(src_root):
        sys.stderr.write(f"run_smoke: ERROR: libc-test source not found: "
                         f"{src_root} (run 'make fetch' first)\n")
        return 2

    selected, discovered, excluded_n, census, corpus_categories = select(src_root)
    selected_categories = {row[0] for row in selected}
    ids = [row[2] for row in selected]
    errs = []
    if not selected:
        errs.append("代表集为空")
    if selected_categories != corpus_categories:
        errs.append(f"类别覆盖不全: 缺 {sorted(corpus_categories - selected_categories)}")
    for category, _size, cid in selected:
        if cid.split("/")[0] != category:
            errs.append(f"代表 id 与类别不符: {category} -> {cid}")
    if len(ids) != len(set(ids)):
        errs.append("代表集有重复 id")
    if not census.get("census_ok", False):
        errs.append("驱动 census 不自洽")

    print("check-tset-libc-smoke: 代表集机械派生 —— 每顶层类别取源码最小用例")
    print(f"  corpus: {src_root} (manifest-locked, 现场枚举)")
    print(f"  发现用例 {discovered} / 结构排除 {excluded_n} (现场统计)")
    print(f"  类别数 {len(corpus_categories)} / 代表数 {len(selected)} (现场统计)")
    for category, size, cid in selected:
        print(f"  {category:12s} -> {cid:40s} source_bytes={size}")
    if errs:
        for err in errs:
            print(f"  FAIL: {err}")
        print("结果: FAIL (代表集结构断言)")
        return 1
    print("  结构断言: PASS (类别全覆盖 / 无重复 / census)")

    if args.list:
        print("结果: PASS (--list；未执行 guest)")
        return 0

    pattern = "^(%s)$" % "|".join(re.escape(cid) for cid in ids)
    sys.argv = [DRIVER, "--src", args.src] + passthrough + ["--filter", pattern]
    print(f"  转发: --filter {pattern}")
    sys.stdout.flush()
    import runpy
    runpy.run_path(DRIVER, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
