#!/usr/bin/env python3
"""check_l3_report.py -- L3 报告**存在性 + 结构 + 覆盖 + 结果**门控
（TESTCASES-083t，里程碑收尾专项）。

判据（``docs/Process-07 §1.1`` / ``docs/Process-09 §8``：只消费报告，**不内联跑
长套件**）
---------------------------------------------------------------------------
报告根：``<test-artifacts>/l3/<YYYYMMDDTHHMMSSZ>/``（``l3_run.py`` 写）

1. **存在性**：``l3/`` 下至少一个 stamp 目录；``--stamp`` 指定时该目录必须存在。
   否则 ⇒ FAIL（提示「先跑 ``make check-full``」，**不是** SKIP）。
2. **三件套**：``manifest.tsv`` / ``meta.json`` / ``run.log`` 存在且非空；
   ``meta.json`` 的 ``command``（须指向 check-full）/ ``started_utc`` /
   ``finished_utc`` / ``commit`` 非空，``toolchain.{clang,qemu}`` 有非空 id（libc/lld 记录但非必需）。
3. **结构**：``manifest.tsv`` 表头 = ``scope\tsuite\trc\tlog``，数据行 ≥1、四列、
   ``rc`` 为整数、``log`` 非空且**文件真实存在且非空**（防伪造全绿）。
4. **覆盖**：至少四种 scope（inst/arch/unit/tset）且 L3 直接清单
   （``l3_run.DEFAULT_MEMBERS``，单一真源）的每个 ``scope:suite`` 都在 —— 缺 ⇒ FAIL。
5. **结果**：任一 ``rc != 0`` ⇒ FAIL；``run.log`` 的 ``[exit marker] rc=N`` 须与
   manifest 一致（全绿 N=0；有红 N=1），不一致 ⇒ FAIL（防「伪造全绿」）。

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

from report_io import HEADER

REPO_ROOT = Path(__file__).resolve().parents[2]
STAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
EXIT_RE = re.compile(r"\[exit marker\] rc=(\d+)")
REQUIRED_SCOPES = {"inst", "arch", "unit", "tset"}
REQUIRED_TOOLS = ("clang", "qemu")   # libc/lld 只记录：L3 的 inst/arch/unit 不依赖 musl


class Report:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []
        self.errors: list[str] = []
        self.info: list[str] = []

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def ok(self, msg: str) -> None:
        self.info.append(msg)


def expected_members() -> list[tuple[str, str]]:
    """L3 直接清单（单一真源 = ``l3_run.DEFAULT_MEMBERS``）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import l3_run  # noqa: PLC0415

    return [(scope, suite) for scope, suite, _cmd in l3_run.DEFAULT_MEMBERS]


def latest_stamp_dir(l3_root: Path) -> Path | None:
    if not l3_root.is_dir():
        return None
    dirs = sorted(p for p in l3_root.iterdir() if p.is_dir() and STAMP_RE.match(p.name))
    return dirs[-1] if dirs else None


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _tool_ok(entry) -> bool:
    if not isinstance(entry, dict):
        return False
    return any(_nonempty_str(entry.get(key)) for key in ("id", "sha256", "md5"))


def _resolve_log(value: str, repo_root: Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else repo_root / p


def check(root: Path, stamp: str | None, repo_root: Path = REPO_ROOT) -> Report:
    rep = Report()
    l3_root = root / "l3"
    if not l3_root.is_dir():
        rep.fail(f"L3 报告目录不存在：{l3_root}（先跑 `make check-full`；"
                 "它由主会话按队列/里程碑触发）")
        return rep

    if stamp:
        target = l3_root / stamp
        if not target.is_dir():
            rep.fail(f"指定 stamp 的 L3 报告不存在：{target}")
            return rep
    else:
        target = latest_stamp_dir(l3_root)
        if target is None:
            rep.fail(f"{l3_root} 下没有 <YYYYMMDDTHHMMSSZ> 报告目录（先跑 `make check-full`）")
            return rep
    rep.ok(f"report dir = {target}")

    # 2. 三件套 + meta
    for name in ("manifest.tsv", "meta.json", "run.log"):
        p = target / name
        if not p.is_file() or p.stat().st_size == 0:
            rep.fail(f"缺少/空的报告文件：{p}")

    meta: dict = {}
    meta_p = target / "meta.json"
    if meta_p.is_file() and meta_p.stat().st_size:
        try:
            meta = json.loads(meta_p.read_text())
        except json.JSONDecodeError as exc:
            rep.fail(f"meta.json 不是合法 JSON：{exc}")
            meta = {}
        for key in ("command", "started_utc", "finished_utc", "commit"):
            if not _nonempty_str(meta.get(key)):
                rep.fail(f"meta.json 缺非空字段 {key!r}")
        command = meta.get("command")
        if _nonempty_str(command) and "check-full" not in command:
            rep.fail(f"meta.json command 不指向 check-full：{command!r}")
        toolchain = meta.get("toolchain")
        if not isinstance(toolchain, dict):
            rep.fail("meta.json 缺 toolchain 摘要块")
        else:
            for tool in REQUIRED_TOOLS:
                if not _tool_ok(toolchain.get(tool)):
                    rep.fail(f"meta.json toolchain.{tool} 缺非空 content id")

    # 3. 结构 + 日志真实存在
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
                    continue
                log = _resolve_log(row["log"], repo_root)
                if not log.is_file() or log.stat().st_size == 0:
                    rep.fail(f"manifest.tsv:{n} 指向的日志缺失/为空（伪造全绿？）：{log}")
                rep.rows.append(row)
            rep.ok(f"manifest rows = {len(rep.rows)}")

    # 4. 覆盖
    if rep.rows:
        scopes = {r["scope"] for r in rep.rows}
        missing_scopes = sorted(REQUIRED_SCOPES - scopes)
        if missing_scopes:
            rep.fail(f"manifest 缺 scope 行：{', '.join(missing_scopes)}"
                     f"（L3 至少覆盖四 scope：{', '.join(sorted(REQUIRED_SCOPES))}）")
        present = {(r["scope"], r["suite"]) for r in rep.rows}
        missing = [f"{s}:{u}" for s, u in expected_members() if (s, u) not in present]
        if missing:
            rep.fail("manifest 缺 L3 成员行：" + ", ".join(missing))

    # 5. 结果 + exit marker 一致性
    red = [(r["scope"], r["suite"], r["rc"]) for r in rep.rows if int(r["rc"]) != 0]
    if red:
        rep.fail("manifest 有非零 rc 行：" + ", ".join(
            f"{s}/{u} rc={rc}" for s, u, rc in red))
    elif rep.rows:
        rep.ok("all manifest rows rc == 0")

    run_log_p = target / "run.log"
    if run_log_p.is_file() and run_log_p.stat().st_size:
        markers = EXIT_RE.findall(run_log_p.read_text())
        if not markers:
            rep.fail("run.log 缺 `[exit marker] rc=N`")
        else:
            actual = int(markers[-1])
            want = 1 if red else 0
            if actual != want:
                rep.fail(f"run.log exit marker rc={actual} 与 manifest 不一致"
                         f"（期望 rc={want}；伪造全绿？）")
            else:
                rep.ok(f"run.log exit marker rc={actual} == manifest")
    return rep


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _write_report(dirp: Path, rows: list[tuple[str, str, int]], logs: Path, *,
                  meta: bool = True, write_logs: bool = True,
                  marker: int | None = None) -> None:
    dirp.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(HEADER)]
    for scope, suite, rc in rows:
        log = logs / f"{scope}-{suite}.log"
        if write_logs:
            log.write_text(f"{scope}:{suite} rc={rc}\n")
        lines.append(f"{scope}\t{suite}\t{rc}\t{log}")
    (dirp / "manifest.tsv").write_text("\n".join(lines) + "\n")
    want = marker if marker is not None else (1 if any(rc for _s, _u, rc in rows) else 0)
    (dirp / "run.log").write_text(f"L3 summary\n[exit marker] rc={want}\n")
    if meta:
        (dirp / "meta.json").write_text(json.dumps({
            "command": "make check-full",
            "started_utc": "2026-10-27T00:00:00Z",
            "finished_utc": "2026-10-27T02:00:00Z",
            "commit": "deadbeef",
            "toolchain": {
                "clang": {"path": "/x/clang", "id": "build-id:aa"},
                "qemu": {"path": "/x/qemu", "id": "build-id:bb"},
                "libc": {"path": "/x/libc.so", "id": "build-id:cc"},
            },
        }) + "\n")


GREEN_ROWS = [(scope, suite, 0) for scope, suite in expected_members()]


def cmd_selftest(args: argparse.Namespace) -> int:
    base = Path(tempfile.mkdtemp(prefix="l3-report-selftest-",
                                 dir=args.tmp_root or "/tmp/opencode"))
    checks: list[tuple[str, bool, str]] = []

    def expect(name: str, root: Path, want_ok: bool,
               stamp: str | None = None) -> None:
        rep = check(root, stamp, repo_root=base)
        ok = (not rep.errors) == want_ok
        detail = "errors=" + ("; ".join(rep.errors)[:140] if rep.errors else "-")
        checks.append((name, ok, detail))

    r1 = base / "a"                                  # 无 l3 目录
    r1.mkdir()
    expect("missing l3/ => FAIL", r1, False)

    r2 = base / "b"
    (r2 / "l3").mkdir(parents=True)                  # l3 下无 stamp 目录
    expect("empty l3/ => FAIL", r2, False)

    r3 = base / "c"
    (r3 / "l3" / "20261027T000000Z").mkdir(parents=True)
    expect("stamp dir without files => FAIL", r3, False)

    r4 = base / "d"
    _write_report(r4 / "l3" / "20261027T000000Z", [], r4 / "logs")
    expect("empty manifest => FAIL", r4, False)

    r5 = base / "e"
    _write_report(r5 / "l3" / "20261027T000000Z",
                  [(s, u, (1 if u == "fp-fma" else 0)) for s, u, _ in GREEN_ROWS],
                  r5 / "logs")
    expect("non-zero rc row => FAIL", r5, False)

    r6 = base / "f"
    _write_report(r6 / "l3" / "20261027T000000Z",
                  [row for row in GREEN_ROWS if row[0] != "tset"], r6 / "logs")
    expect("missing tset scope => FAIL", r6, False)

    r7 = base / "g"
    _write_report(r7 / "l3" / "20261027T000000Z",
                  [row for row in GREEN_ROWS if row[1] != "fp-clmul"], r7 / "logs")
    expect("missing fp-clmul member => FAIL", r7, False)

    r8 = base / "h"
    _write_report(r8 / "l3" / "20261027T000000Z", GREEN_ROWS, r8 / "logs",
                  write_logs=False)               # 伪造全绿：日志不存在
    expect("forged green (missing logs) => FAIL", r8, False)

    r9 = base / "i"
    _write_report(r9 / "l3" / "20261027T000000Z", GREEN_ROWS, r9 / "logs",
                  marker=1)                       # 伪造全绿：marker 说红
    expect("forged green (marker rc=1) => FAIL", r9, False)

    r10 = base / "j"
    _write_report(r10 / "l3" / "20261027T000000Z", GREEN_ROWS, r10 / "logs",
                  meta=False)
    expect("missing meta.json => FAIL", r10, False)

    r11 = base / "k"
    _write_report(r11 / "l3" / "20261027T000000Z", GREEN_ROWS, r11 / "logs")
    expect("green report => PASS", r11, True)

    r12 = base / "l"
    _write_report(r12 / "l3" / "20261026T000000Z", GREEN_ROWS, r12 / "logs")
    expect("--stamp points to absent dir => FAIL", r12, False,
           stamp="20261027T000000Z")

    fails = sum(0 if ok else 1 for _, ok, _ in checks)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})")
    print(f"check_l3_report --self-test: {'PASS' if fails == 0 else 'FAIL'} "
          f"({len(checks) - fails}/{len(checks)})")
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"  kept: {base}")
    return 0 if fails == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L3 报告存在性/结构/覆盖/结果门控")
    ap.add_argument("--root", default=str(REPO_ROOT / ".dadao" / "tests"),
                    help="test-artifacts 根（.dadao/tests）")
    ap.add_argument("--stamp", default=None,
                    help="指定报告戳 YYYYMMDDTHHMMSSZ（默认最新）")
    ap.add_argument("--repo-root", default=str(REPO_ROOT),
                    help="manifest log 列的相对根（fixture/自检用）")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--tmp-root", default=None)
    args = ap.parse_args(argv)

    if args.self_test:
        return cmd_selftest(args)
    if args.stamp and not STAMP_RE.match(args.stamp):
        sys.stderr.write(f"ERROR: --stamp 必须是 YYYYMMDDTHHMMSSZ，得到 {args.stamp!r}\n")
        return 2

    rep = check(Path(args.root), args.stamp, repo_root=Path(args.repo_root))
    for line in rep.info:
        print(f"check-l3-report: {line}")
    if rep.errors:
        for err in rep.errors:
            print(f"check-l3-report: FAIL — {err}")
        print("check-l3-report: FAIL")
        return 1
    print("check-l3-report: PASS (see docs/Process-07 §1.1 / Process-09 §8)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
