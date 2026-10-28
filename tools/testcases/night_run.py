#!/usr/bin/env python3
"""night_run.py -- `make check-night` 的实现（TESTCASES-076t，P6）。

夜跑 = **tset full（libc-test / llvm-ts / Embench）+ 长 arch**，由调用者
``setsid nohup make check-night > log 2>&1 &`` 脱离会话（不自带 `nohup`，避免嵌套）。
每次跑建一个只读报告目录（`docs/Process-09 §8`）：

    <test-artifacts>/night/<YYYY-MM-DD>/
        manifest.tsv   scope<TAB>suite<TAB>rc<TAB>log（逐成员一行）
        meta.json      command / started_utc / finished_utc / members
        run.log        汇总（各成员 rc + 日志指针）

纪律
----
* **同一天不覆盖**：目录已存在且非空 ⇒ rc=2（`--allow-overwrite` 显式放行）；
  ``docs/Process-08 §1.1`` 的「禁两次跑写同一目录」。
* **顺序执行**（一次只跑一个长任务），逐成员日志落
  ``.work/log/testcases/check-night-<date>-<suite>.log``。
* 任一成员 rc != 0 ⇒ 整体 rc=1，但**其余成员照跑**（夜跑要一次拿到全景）。
* 结尾打印 ``[exit marker] rc=N``（`docs/Process-09 §8`）。

``--self-test`` 用假成员（``true``/``false``）验证：全绿 ⇒ rc=0 且报告门控 PASS；
红成员 ⇒ rc=1 且 manifest 记 rc、报告门控 FAIL；同日重跑 ⇒ 拒绝。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import report_io

REPO_ROOT = Path(__file__).resolve().parents[2]

# 默认成员：scope:suite=命令（tset full + 长 arch）
DEFAULT_MEMBERS = [
    "tset:libc-test=make check-tset-libc-full",
    "tset:llvm-ts=make check-tset-llvm-full",
    "tset:embench=make check-tset-embench-full",
    "arch:cfx=make check-arch",
]

HEADER = report_io.HEADER


def utc_now() -> str:
    return report_io.utc_now()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_member(raw: str) -> tuple[str, str, str]:
    try:
        key, cmd = raw.split("=", 1)
        scope, suite = key.split(":", 1)
    except ValueError:
        raise SystemExit(f"ERROR: --member 需形如 scope:suite=cmd，得到 {raw!r}")
    if not scope or not suite or not cmd.strip():
        raise SystemExit(f"ERROR: --member 字段为空：{raw!r}")
    return scope, suite, cmd


def run_night(root: Path, date: str, members: list[tuple[str, str, str]],
              allow_overwrite: bool, logdir: Path | None = None) -> int:
    report = root / "night" / date
    if report.exists() and any(report.iterdir()) and not allow_overwrite:
        sys.stderr.write(
            f"check-night: FAIL — 报告目录已存在（同一天不覆盖）：{report}\n"
            "  换一天（--date）或显式 --allow-overwrite。\n")
        return 2
    report.mkdir(parents=True, exist_ok=True)
    logdir = (logdir or (REPO_ROOT / ".work" / "log" / "testcases")).resolve()
    logdir.mkdir(parents=True, exist_ok=True)

    started = utc_now()
    rows: list[tuple[str, str, int, str]] = []
    for scope, suite, cmd in members:
        log = logdir / f"check-night-{date}-{suite}.log"
        print(f"check-night: [{scope}:{suite}] $ {cmd}  (log {log})", flush=True)
        with log.open("w") as fh:
            rc = subprocess.call(["bash", "-lc", cmd], cwd=REPO_ROOT,
                                 stdout=fh, stderr=subprocess.STDOUT)
        print(f"check-night: [{scope}:{suite}] rc={rc}", flush=True)
        try:
            log_ref = str(log.relative_to(REPO_ROOT))
        except ValueError:
            log_ref = str(log)
        rows.append((scope, suite, rc, log_ref))
    finished = utc_now()

    report_io.write_manifest(report, rows)
    report_io.write_meta(report, {
        "command": "make check-night",
        "started_utc": started,
        "finished_utc": finished,
        "members": [{"scope": s, "suite": u, "cmd": cmd} for s, u, cmd in members],
    })
    (report / "run.log").write_text(
        "\n".join([
            f"check-night {date}  ({started} .. {finished})",
            *[f"  {s}:{u}\trc={rc}\t{log}" for s, u, rc, log in rows],
        ]) + "\n")

    failed = [f"{s}:{u}" for s, u, rc, _ in rows if rc != 0]
    total = len(rows)
    if failed:
        print(f"check-night: FAIL — {len(failed)}/{total} member(s) red: {', '.join(failed)}")
        print(f"check-night: report {report}")
        print(f"[exit marker] rc=1")
        return 1
    print(f"check-night: PASS ({total}/{total} member(s) green)")
    print(f"check-night: report {report}")
    print("[exit marker] rc=0")
    return 0


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def cmd_selftest(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_night_report as report_gate  # noqa: E402

    base = Path(tempfile.mkdtemp(prefix="night-run-selftest-",
                                 dir=args.tmp_root or "/tmp/opencode"))
    checks: list[tuple[str, bool, str]] = []
    green = [("tset", "libc-test", "echo ok"), ("tset", "llvm-ts", "echo ok"),
             ("tset", "embench", "echo ok"), ("arch", "cfx", "echo ok")]
    red = [("tset", "libc-test", "echo ok"), ("tset", "llvm-ts", "echo ok"),
           ("tset", "embench", "echo fail; false"), ("arch", "cfx", "echo ok")]

    rc = run_night(base, "2026-10-27", green, allow_overwrite=False, logdir=base / "logs")
    checks.append(("green night => rc=0", rc == 0, f"rc={rc}"))
    rep = report_gate.check(base, "2026-10-27")
    checks.append(("green night => report gate PASS", not rep.errors,
                   "errors=" + ("; ".join(rep.errors)[:100] if rep.errors else "-")))

    rc = run_night(base, "2026-10-28", red, allow_overwrite=False, logdir=base / "logs")
    checks.append(("red member => rc=1", rc == 1, f"rc={rc}"))
    rep = report_gate.check(base, "2026-10-28")
    checks.append(("red night => report gate FAIL", bool(rep.errors),
                   "errors=" + ("; ".join(rep.errors)[:100] if rep.errors else "-")))

    rows = (base / "night" / "2026-10-28" / "manifest.tsv").read_text().splitlines()
    emb = [ln for ln in rows if "\tembench\t" in ln]
    checks.append(("manifest records rc=1 for red member",
                   bool(emb) and emb[0].split("\t")[2] == "1", str(emb)))

    rc = run_night(base, "2026-10-27", green, allow_overwrite=False, logdir=base / "logs")
    checks.append(("same-date rerun refused => rc=2", rc == 2, f"rc={rc}"))

    fails = sum(0 if ok else 1 for _, ok, _ in checks)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})")
    print(f"night_run --self-test: {'PASS' if fails == 0 else 'FAIL'} "
          f"({len(checks) - fails}/{len(checks)})")
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"  kept: {base}")
    return 0 if fails == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="夜跑编排 + 报告落盘")
    ap.add_argument("--root", default=str(REPO_ROOT / ".dadao" / "tests"))
    ap.add_argument("--date", default=None, help="报告日期（默认 UTC 今天）")
    ap.add_argument("--member", action="append", default=None,
                    help="scope:suite=cmd（可重复；默认 tset full × 3 + arch）")
    ap.add_argument("--allow-overwrite", action="store_true")
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--tmp-root", default=None)
    args = ap.parse_args(argv)

    if args.self_test:
        return cmd_selftest(args)

    date = args.date or today()
    members = [parse_member(m) for m in (args.member or DEFAULT_MEMBERS)]
    if args.dry_run:
        print(f"check-night: DRY-RUN date={date} root={args.root} members={len(members)}")
        for scope, suite, cmd in members:
            print(f"  {scope}:{suite}  $ {cmd}")
        return 0
    return run_night(Path(args.root), date, members, args.allow_overwrite,
                     Path(args.log_dir) if args.log_dir else None)


if __name__ == "__main__":
    sys.exit(main())
