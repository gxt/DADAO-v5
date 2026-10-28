#!/usr/bin/env python3
"""check_night_report.py -- 夜跑报告**存在性 + 结构**门控（TESTCASES-076t，P6）。

判据（`docs/Process-09 §8` 的「里程碑层」口径：只消费报告，**不内联跑长套件**）
-------------------------------------------------------------------------------
报告根：``<test-artifacts>/night/<YYYY-MM-DD>/``

1. **存在性**：``night/`` 下至少一个本地日期 ``YYYY-MM-DD-HH`` 目录；``--date`` 指定时该目录
   必须存在。否则 ⇒ FAIL（提示「先跑 ``make check-night``」，**不是** SKIP）。
2. **三件套**：``manifest.tsv`` / ``meta.json`` / ``run.log`` 均存在且非空；
   ``meta.json`` 的 ``command`` / ``started_utc`` / ``finished_utc`` 非空。
3. **结构**：``manifest.tsv`` 表头 = ``scope\tsuite\trc\tlog``，数据行 ≥1、四列、
   ``rc`` 为整数（计数现场统计）。
4. **覆盖**：必须含 ``tset`` 的三套件（``libc-test`` / ``llvm-ts`` / ``embench``）
   与 ``arch`` 一行 —— 缺 ⇒ FAIL（防"只跑了半个夜跑"也绿）。
5. **结果**：任一 ``rc != 0`` ⇒ FAIL（报告存在但夜跑红，里程碑不得绿）。

退出码：0 PASS / 1 FAIL / 2 用法错误。``--self-test`` 用临时树逐条注入。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}$")
HEADER = ["scope", "suite", "rc", "log"]
REQUIRED_TSET = {"libc-test", "llvm-ts", "embench"}
REQUIRED_SCOPES = {"arch"}


class Report:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []
        self.errors: list[str] = []
        self.info: list[str] = []

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def ok(self, msg: str) -> None:
        self.info.append(msg)


def latest_date_dir(night_root: Path) -> Path | None:
    if not night_root.is_dir():
        return None
    dirs = sorted(p for p in night_root.iterdir() if p.is_dir() and DATE_RE.match(p.name))
    return dirs[-1] if dirs else None


def check(root: Path, date: str | None) -> Report:
    rep = Report()
    night_root = root / "night"
    if not night_root.is_dir():
        rep.fail(f"夜跑报告目录不存在：{night_root}（先跑 `make check-night`；"
                 "它由主会话 setsid nohup 启动）")
        return rep

    if date:
        target = night_root / date
        if not target.is_dir():
            rep.fail(f"指定日期的夜跑报告不存在：{target}")
            return rep
    else:
        target = latest_date_dir(night_root)
        if target is None:
            rep.fail(f"{night_root} 下没有 <YYYY-MM-DD> 报告目录（先跑 `make check-night`）")
            return rep
    rep.ok(f"report dir = {target}")

    # 2. 三件套
    for name in ("manifest.tsv", "meta.json", "run.log"):
        p = target / name
        if not p.is_file() or p.stat().st_size == 0:
            rep.fail(f"缺少/空的报告文件：{p}")

    meta_p = target / "meta.json"
    if meta_p.is_file() and meta_p.stat().st_size:
        try:
            meta = json.loads(meta_p.read_text())
        except json.JSONDecodeError as exc:
            rep.fail(f"meta.json 不是合法 JSON：{exc}")
            meta = {}
        for key in ("command", "started_utc", "finished_utc"):
            if not str(meta.get(key) or "").strip():
                rep.fail(f"meta.json 缺非空字段 {key!r}")

    # 3. 结构
    man_p = target / "manifest.tsv"
    if man_p.is_file() and man_p.stat().st_size:
        lines = [ln for ln in man_p.read_text().splitlines() if ln.strip()]
        if not lines:
            rep.fail("manifest.tsv 为空（vacuous）")
        else:
            header = lines[0].split("\t")
            if header != HEADER:
                rep.fail(f"manifest.tsv 表头应为 {HEADER}，实际 {header}")
            body = lines[1:]
            if not body:
                rep.fail("manifest.tsv 只有表头、没有数据行（vacuous）")
            for n, ln in enumerate(body, start=2):
                cols = ln.split("\t")
                if len(cols) != len(HEADER):
                    rep.fail(f"manifest.tsv:{n} 列数 {len(cols)} != {len(HEADER)}")
                    continue
                row = dict(zip(HEADER, cols))
                try:
                    int(row["rc"])
                except ValueError:
                    rep.fail(f"manifest.tsv:{n} rc 不是整数：{row['rc']!r}")
                    continue
                if not row["log"].strip():
                    rep.fail(f"manifest.tsv:{n} log 为空")
                else:
                    lp = Path(row["log"])
                    if not lp.is_absolute():
                        lp = REPO_ROOT / lp
                    if not lp.is_file() or lp.stat().st_size == 0:
                        rep.fail(f"manifest.tsv:{n} log 不存在/为空：{lp}")
                rep.rows.append(row)
            rep.ok(f"manifest rows = {len(rep.rows)}")

    # 4. 覆盖
    if rep.rows:
        tset = {r["suite"] for r in rep.rows if r["scope"] == "tset"}
        missing = sorted(REQUIRED_TSET - tset)
        if missing:
            rep.fail(f"manifest 缺 tset 套件行：{', '.join(missing)}（夜跑 = tset full + 长 arch）")
        scopes = {r["scope"] for r in rep.rows}
        miss_scopes = sorted(REQUIRED_SCOPES - scopes)
        if miss_scopes:
            rep.fail(f"manifest 缺 scope 行：{', '.join(miss_scopes)}")

    # 5. 结果
    red = [(r["scope"], r["suite"], r["rc"]) for r in rep.rows if int(r["rc"]) != 0]
    if red:
        rep.fail("manifest 有非零 rc 行：" + ", ".join(f"{s}/{u} rc={rc}" for s, u, rc in red))
    elif rep.rows:
        rep.ok("all manifest rows rc == 0")
    return rep


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _write_report(dirp: Path, rows: list[tuple[str, str, int]], *, meta: bool = True) -> None:
    dirp.mkdir(parents=True, exist_ok=True)
    logs = dirp / "logs"
    logs.mkdir(exist_ok=True)
    lines = ["\t".join(HEADER)]
    for scope, suite, rc in rows:
        log = logs / f"check-night-{suite}.log"
        log.write_text(f"{suite} rc={rc}\n")
        lines.append(f"{scope}\t{suite}\t{rc}\t{log}")
    (dirp / "manifest.tsv").write_text("\n".join(lines) + "\n")
    (dirp / "run.log").write_text("night summary\n")
    if meta:
        (dirp / "meta.json").write_text(json.dumps({
            "command": "make check-night",
            "started_utc": "2026-10-27-00T00:00:00Z",
            "finished_utc": "2026-10-27-00T02:00:00Z",
        }) + "\n")


GREEN_ROWS = [("tset", "libc-test", 0), ("tset", "llvm-ts", 0),
              ("tset", "embench", 0), ("arch", "cfx", 0)]


def cmd_selftest(args: argparse.Namespace) -> int:
    base = Path(tempfile.mkdtemp(prefix="night-report-selftest-",
                                 dir=args.tmp_root or "/tmp/opencode"))
    checks: list[tuple[str, bool, str]] = []

    def expect(name: str, root: Path, want_ok: bool, date: str | None = None) -> None:
        rep = check(root, date)
        ok = (not rep.errors) == want_ok
        detail = "errors=" + ("; ".join(rep.errors)[:120] if rep.errors else "-")
        checks.append((name, ok, detail))

    r1 = base / "a"                                  # 无 night 目录
    r1.mkdir()
    expect("missing night/ => FAIL", r1, False)

    r2 = base / "b"
    (r2 / "night").mkdir(parents=True)               # night 下无日期目录
    expect("empty night/ => FAIL", r2, False)

    r3 = base / "c"
    (r3 / "night" / "2026-10-27-00").mkdir(parents=True)  # 日期目录但无三件套
    expect("date dir without files => FAIL", r3, False)

    r4 = base / "d"
    _write_report(r4 / "night" / "2026-10-27-00",
                  [("tset", "libc-test", 0), ("arch", "cfx", 0)])   # 缺两套件
    expect("missing tset suites => FAIL", r4, False)

    r5 = base / "e"
    _write_report(r5 / "night" / "2026-10-27-00",
                  [(s, u, (1 if u == "embench" else 0)) for s, u, _ in GREEN_ROWS])
    expect("non-zero rc row => FAIL", r5, False)

    r6 = base / "f"
    _write_report(r6 / "night" / "2026-10-27-00", GREEN_ROWS)
    expect("green report => PASS", r6, True)

    r7 = base / "g"
    _write_report(r7 / "night" / "2026-10-27-00", GREEN_ROWS, meta=False)
    expect("missing meta.json => FAIL", r7, False)

    r8 = base / "h"
    _write_report(r8 / "night" / "2026-10-26-00", GREEN_ROWS)
    expect("--date points to absent dir => FAIL", r8, False, date="2026-10-27-00")

    fails = sum(0 if ok else 1 for _, ok, _ in checks)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})")
    print(f"check_night_report --self-test: {'PASS' if fails == 0 else 'FAIL'} "
          f"({len(checks) - fails}/{len(checks)})")
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"  kept: {base}")
    return 0 if fails == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="夜跑报告存在性/结构门控")
    ap.add_argument("--root", default=str(REPO_ROOT / ".dadao" / "tests"),
                    help="test-artifacts 根（.dadao/tests）")
    ap.add_argument("--date", default=None, help="指定报告日期 YYYY-MM-DD（默认最新）")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--tmp-root", default=None)
    args = ap.parse_args(argv)

    if args.self_test:
        return cmd_selftest(args)
    if args.date and not DATE_RE.match(args.date):
        sys.stderr.write(f"ERROR: --date 必须是 YYYY-MM-DD，得到 {args.date!r}\n")
        return 2

    rep = check(Path(args.root), args.date)
    for line in rep.info:
        print(f"check-night-report: {line}")
    if rep.errors:
        for err in rep.errors:
            print(f"check-night-report: FAIL — {err}")
        print("check-night-report: FAIL")
        return 1
    print("check-night-report: PASS (see docs/Process-09 §8)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
