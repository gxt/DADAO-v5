#!/usr/bin/env python3
"""engine_parity_pending.py -- 列出 picolibc 侧仍缺终态判决的用例。

本文件是 `m12-chipyard-016` 证据脚本 `pending.py` 的入仓版
（`m12-chipyard-017`）：口径与输出行数/顺序原样保留，只改路径解析与入口。

判决来源：每个池的逐例进度日志 + 每个池的 JSON，都在
`<repo>` 内 chipyard 模块的运行期日志目录里的
`m12-chipyard-016-picolibc-chipyard*`（永不入库）。

规则（用户 2026-11-14）：

  * ``pass`` / ``fail`` / ``excluded`` 与非 budget 的 ``blocked`` 是终态；
  * ``blocked (host timeout)`` **不是**终态：它是 budget 产物，等专用重跑池；
  * 任何来源都没出现过的用例 ⇒ pending；
  * 一个用例保留首个终态判决；后来的 pass/fail 可覆盖 budget ``blocked``。

清单真源 = qemu 基线 JSON（同 ELF 集合、同 runner），`INVENTORY` 是它的规模。

用法::

    python3 tools/testcases/parity/engine_parity_pending.py [--repo <根>] [--log-dir <目录>]

输出三行：pending 数 / 逗号分隔用例名 / `known=… terminal=… pending=… inventory=…`。
（embench 侧 pending = `38 - cases_seen`，见报告 JSON 的 `embench` 段。）
"""
import argparse
import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_DEFAULT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
INVENTORY = 235
PARITY_BLOCKED = {"test-ceil", "test-long-double", "test-math-funcs",
                  "test-memmem"}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO_DEFAULT,
                    help="仓库根（默认 = 本脚本上溯三层）")
    ap.add_argument("--log-dir", default=None,
                    help="批次输入目录（默认 = <repo> 内 chipyard 运行期日志目录）")
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    LOG = (os.path.abspath(args.log_dir) if args.log_dir
           else os.path.join(repo, ".work", "log", "chipyard"))

    rows = {}

    def put(name, status, reason):
        prev = rows.get(name)
        if prev is None:
            rows[name] = (status, reason)
        elif prev[0] == "skipped" and status != "skipped":
            rows[name] = (status, reason)
        elif prev[0] == "blocked" and "timeout" in prev[1] and status != "skipped":
            rows[name] = (status, reason)

    for path in sorted(glob.glob(os.path.join(LOG, "m12-chipyard-016-picolibc-chipyard*.json"))):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        for r in doc["results"]:
            put(r["name"], r["status"], r.get("reason") or "")
    for path in sorted(glob.glob(os.path.join(LOG, "m12-chipyard-016-picolibc-chipyard*.log"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"\s+\[\d+/\d+\] (\S+)\s+(\S+)\s+(.*)$", line)
                if m:
                    put(m.group(1), m.group(2), m.group(3))

    # The inventory comes from the qemu baseline (same ELF set, same runner).
    inv_path = os.path.join(LOG, "m12-chipyard-016-picolibc-qemu.json")
    try:
        with open(inv_path, encoding="utf-8") as fh:
            inventory = [r["name"] for r in json.load(fh)["results"]]
    except FileNotFoundError:
        print("engine_parity_pending: SETUP: missing input %s" % inv_path,
              file=sys.stderr)
        return 2

    def terminal(name):
        status, reason = rows.get(name, (None, ""))
        if status in ("pass", "fail", "excluded"):
            return True
        if status == "blocked" and "timeout" not in reason:
            return True
        if name in PARITY_BLOCKED:
            return True
        return False

    pending = [n for n in inventory if not terminal(n)]
    # a case that never appeared at all is pending too; the runner's EXCLUDED
    # table is terminal, so only the inventory minus what we saw matters.
    print(len(pending))
    print(",".join(pending))
    print("known=%d terminal=%d pending=%d inventory=%d"
          % (len(rows), len(rows) - len(pending), len(pending), INVENTORY))
    return 0


if __name__ == "__main__":
    sys.exit(main())
