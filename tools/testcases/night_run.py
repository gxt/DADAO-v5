#!/usr/bin/env python3
"""night_run.py -- `make night-run` 的实现（TESTCASES-076t，P6；INFRA-127t 独立锁）。

回归运行（Make 目标仍名 `night-run`、本脚本仍名 `night_run.py`；历史名，
语义 = 全量回归成员集）= **tset full（libc-test / llvm-ts / Embench）+
长 arch（QEMU system cfx + gem5 FS inst/arch）+ gem5 SE tset（static）**，由调用者
``setsid nohup make night-run > log 2>&1 &`` 脱离会话（不自带 `nohup`，避免嵌套）。

成员可用性证据（`TESTCASES-105t`；**不重跑全量**）：
* gem5 SE static  —— `.tao/knowledge/refs/GEM5-021t-baseline-summary.json`
  （`TESTCASES-103t` 预算/分类全量，复用 `tset/gem5-se-baseline` 驱动）；
* gem5 SE dynamic —— `.tao/knowledge/refs/TESTCASES-104t-dynamic-summary.json`
  （`TESTCASES-104t` 动态档全量；成员本身跑 static，不重复 dynamic）；
* gem5 FS inst/arch —— `docs/TestReports/M11-三平台一致矩阵.md`（`GEM5-017t/018t` 矩阵）。
每次跑建一个只读报告目录（`docs/Process-09 §8`）：

    <test-artifacts>/night/<local YYYY-MM-DD-HH>/
        manifest.tsv   scope<TAB>suite<TAB>rc<TAB>log（逐成员一行）
        meta.json      command / started_utc / finished_utc / members
                       + host / machine_id / git_commit / toolchain_id
        run.log        汇总（各成员 rc + 日志指针）

纪律
----
* **同一天不覆盖**：目录已存在且非空 ⇒ rc=2（`--allow-overwrite` 显式放行）；
  ``docs/Process-08 §1.1`` 的「禁两次跑写同一目录」。
* **顺序执行**（一次只跑一个长任务），逐成员日志落
  ``.work/log/testcases/check-night-<date>-<suite>.log``。
* 任一成员 rc != 0 ⇒ 整体 rc=1，但**其余成员照跑**（回归运行要一次拿到全景）。
* 结尾打印 ``[exit marker] rc=N``（`docs/Process-09 §8`）。

``--self-test`` 用假成员（``true``/``false``）验证：全绿 ⇒ rc=0 且报告门控 PASS；
红成员 ⇒ rc=1 且 manifest 记 rc、报告门控 FAIL；同日重跑 ⇒ 拒绝。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import report_io

REPO_ROOT = Path(__file__).resolve().parents[2]

# 默认成员：scope:suite=命令（tset full + 长 arch + gem5 SE/FS）
GEM5_SE_DIR = ".work/tests/night-gem5-se"


def _gem5_se_member(suite: str) -> str:
    """gem5 SE static member: 103t driver + a cross-failure rc guard.

    The baseline driver returns 0 after writing its report even when a case is
    ``gem5_only_fail``/``qemu_only_fail``; the trailing python exits non-zero on
    those counts (and on a missing/empty result JSON) so the member's rc is not
    vacuous.
    """
    json_out = f"{GEM5_SE_DIR}/{suite}.json"
    return (
        "python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py"
        f" --suites {suite} --link-mode static --jobs 8"
        f" --work-dir {GEM5_SE_DIR}/{suite}"
        f" --json-out {json_out}"
        f" --summary-dir {GEM5_SE_DIR}/summary-{suite}"
        " && python3 -c 'import json,sys;"
        f"t=json.load(open(\"{json_out}\"))[\"totals\"];"
        "bad=t[\"gem5_only_fail\"]+t[\"qemu_only_fail\"];"
        "print(\"gem5_se_cross_fail\",bad);"
        "sys.exit(0 if bad==0 else 1)'"
    )


DEFAULT_MEMBERS = [
    # QEMU user/system（既有成员，语义/预算不变）。
    "tset:libc-test=make check-tset-libc-full",
    "tset:llvm-ts=make check-tset-llvm-full",
    "tset:embench=make check-tset-embench-full",
    "arch:cfx=make check-arch",
    # gem5 SE（TESTCASES-105t）：static 档，复用 TESTCASES-103t 的
    # `tset/gem5-se-baseline` 驱动（同一 script 同时跑 QEMU-user 与 gem5-SE 并
    # 逐 case 对照）。成员可用性证据（全量落盘，本成员不重复）：
    #   static  .tao/knowledge/refs/GEM5-021t-baseline-summary.json
    #   dynamic .tao/knowledge/refs/TESTCASES-104t-dynamic-summary.json
    # 每个套件用独立 summary-dir，避免同名的 GEM5-021t-baseline-summary.json 互相覆盖。
    "tset:gem5-se-libc=" + _gem5_se_member("libc-test"),
    "tset:gem5-se-llvm=" + _gem5_se_member("llvm-ts"),
    "tset:gem5-se-embench=" + _gem5_se_member("embench"),
    # gem5 FS（TESTCASES-105t）：复用 `tools/testcases/parity/run_parity.py`
    # 的 inst + arch（裸机 E2E），与 QEMU system 同 case 集比较状态/退出码，
    # 不比时序；该驱动自身对 gem5_only_fail/diff 返回非零。成员可用性证据：
    # docs/TestReports/M11-三平台一致矩阵.md。
    "arch:gem5-fs=python3 tools/testcases/parity/run_parity.py"
    " --profiles tiny,vast --scopes inst,arch --jobs 8"
    " --work-dir .work/tests/night-gem5-fs/run"
    " --json .work/tests/night-gem5-fs/matrix.json"
    " --markdown .work/tests/night-gem5-fs/matrix.md --allow-repo-write",
]

# 每成员整轮墙钟预算（秒）；缺省 = 无超时（QEMU 四个成员保持既有语义/预算）。
# 超时以 rc=124 落 manifest，报告门控单列 "超时"，不并成普通失败（任务书目标 5）。
MEMBER_TIMEOUTS = {
    ("tset", "gem5-se-libc"): 3600,
    ("tset", "gem5-se-llvm"): 10800,
    ("tset", "gem5-se-embench"): 3600,
    ("arch", "gem5-fs"): 14400,
}
TIMEOUT_RC = 124

HEADER = report_io.HEADER


def utc_now() -> str:
    return report_io.utc_now()


def today() -> str:
    # User-facing night directory uses the local date + hour; meta.json
    # still records UTC start/finish timestamps for auditability.
    return datetime.now().astimezone().strftime("%Y-%m-%d-%H")


def host_name() -> str:
    return socket.gethostname()


def machine_id(cli_value: str | None = None) -> str:
    """Machine label: ``--machine`` > ``NIGHT_MACHINE_ID`` > hostname."""
    for candidate in (cli_value, os.environ.get("NIGHT_MACHINE_ID"), host_name()):
        if candidate and candidate.strip():
            return candidate.strip()
    return host_name()


def git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True)
    except OSError:
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


def toolchain_summary() -> str:
    """Installed clang/ld.lld content identity (build-id/sha256), for cross-machine comparison."""
    sys.path.insert(0, str(REPO_ROOT / "tools" / "infra"))
    try:
        import paths  # noqa: PLC0415
        import toolchain_id as tid  # noqa: PLC0415
    except ImportError:
        return ""
    bin_dir = paths.host_toolchain_bin()
    parts: list[str] = []
    for name in ("clang", "ld.lld"):
        tool = bin_dir / name
        if not tool.is_file():
            parts.append(f"{name}=absent")
            continue
        kind, value = tid.content_id(tool)
        parts.append(f"{name}={kind}:{value}")
    return ";".join(parts)


def parse_member(raw: str) -> tuple[str, str, str]:
    try:
        key, cmd = raw.split("=", 1)
        scope, suite = key.split(":", 1)
    except ValueError:
        raise SystemExit(f"ERROR: --member 需形如 scope:suite=cmd，得到 {raw!r}")
    if not scope or not suite or not cmd.strip():
        raise SystemExit(f"ERROR: --member 字段为空：{raw!r}")
    return scope, suite, cmd


def run_member(cmd: str, log: Path, timeout: int | None) -> int:
    """Run one member sequentially; a timeout kills the whole process group.

    ``timeout=None`` keeps the historical behaviour (plain ``subprocess.call``)
    so the QEMU members and ``--member`` overrides are unchanged.  A timeout is
    reported as :data:`TIMEOUT_RC` (124) and left in the member log.
    """
    with log.open("w") as fh:
        if timeout is None:
            return subprocess.call(["bash", "-lc", cmd], cwd=REPO_ROOT,
                                   stdout=fh, stderr=subprocess.STDOUT)
        proc = subprocess.Popen(["bash", "-lc", cmd], cwd=REPO_ROOT,
                                stdout=fh, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            fh.write(f"\ncheck-night: TIMEOUT after {timeout}s\n")
            fh.flush()
            return TIMEOUT_RC


def run_night(root: Path, date: str, members: list[tuple[str, str, str]],
              allow_overwrite: bool, logdir: Path | None = None,
              machine: str | None = None,
              timeouts: dict[tuple[str, str], int] | None = None) -> int:
    report = root / "night" / date
    if report.exists() and any(report.iterdir()) and not allow_overwrite:
        sys.stderr.write(
            f"check-night: FAIL — 报告目录已存在（同一天不覆盖）：{report}\n"
            "  换一天（--date）或显式 --allow-overwrite。\n")
        return 2
    report.mkdir(parents=True, exist_ok=True)
    logdir = (logdir or (REPO_ROOT / ".work" / "log" / "testcases")).resolve()
    logdir.mkdir(parents=True, exist_ok=True)
    timeouts = timeouts or {}

    started = utc_now()
    rows: list[tuple[str, str, int, str]] = []
    for scope, suite, cmd in members:
        log = logdir / f"check-night-{date}-{suite}.log"
        timeout = timeouts.get((scope, suite))
        timeout_note = "" if timeout is None else f", timeout {timeout}s"
        print(f"check-night: [{scope}:{suite}] $ {cmd}  (log {log}{timeout_note})",
              flush=True)
        rc = run_member(cmd, log, timeout)
        if rc == TIMEOUT_RC:
            print(f"check-night: [{scope}:{suite}] TIMEOUT (rc={rc})", flush=True)
        else:
            print(f"check-night: [{scope}:{suite}] rc={rc}", flush=True)
        try:
            log_ref = str(log.relative_to(REPO_ROOT))
        except ValueError:
            log_ref = str(log)
        rows.append((scope, suite, rc, log_ref))
    finished = utc_now()

    report_io.write_manifest(report, rows)
    report_io.write_meta(report, {
        "command": "make night-run",
        "started_utc": started,
        "finished_utc": finished,
        "host": host_name(),
        "machine_id": machine_id(machine),
        "git_commit": git_commit(),
        "toolchain_id": toolchain_summary(),
        "members": [{"scope": s, "suite": u, "cmd": cmd,
                     "timeout_seconds": timeouts.get((s, u))}
                    for s, u, cmd in members],
    })
    (report / "run.log").write_text(
        "\n".join([
            f"check-night {date}  ({started} .. {finished})",
            *[f"  {s}:{u}\trc={rc}\t{log}" for s, u, rc, log in rows],
        ]) + "\n")

    failed = [f"{s}:{u}" for s, u, rc, _ in rows if rc != 0]
    timed_out = [f"{s}:{u}" for s, u, rc, _ in rows if rc == TIMEOUT_RC]
    total = len(rows)
    if failed:
        print(f"check-night: FAIL — {len(failed)}/{total} member(s) red: {', '.join(failed)}")
        if timed_out:
            print(f"check-night: timeout member(s): {', '.join(timed_out)}")
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
    green = [
        ("tset", "libc-test", "echo ok"), ("tset", "llvm-ts", "echo ok"),
        ("tset", "embench", "echo ok"), ("arch", "cfx", "echo ok"),
        ("tset", "gem5-se-libc", "echo ok"),
        ("tset", "gem5-se-llvm", "echo ok"),
        ("tset", "gem5-se-embench", "echo ok"),
        ("arch", "gem5-fs", "echo ok"),
    ]
    red = [m for m in green]
    red[2] = ("tset", "embench", "echo fail; false")
    red[6] = ("tset", "gem5-se-embench", "echo fail; false")

    rc = run_night(base, "2026-10-27-00", green, allow_overwrite=False, logdir=base / "logs")
    checks.append(("green night => rc=0", rc == 0, f"rc={rc}"))
    rep = report_gate.check(base, "2026-10-27-00")
    checks.append(("green night => report gate PASS", not rep.errors,
                   "errors=" + ("; ".join(rep.errors)[:100] if rep.errors else "-")))

    rc = run_night(base, "2026-10-28-00", red, allow_overwrite=False, logdir=base / "logs")
    checks.append(("red member => rc=1", rc == 1, f"rc={rc}"))
    rep = report_gate.check(base, "2026-10-28-00")
    checks.append(("red night => report gate FAIL", bool(rep.errors),
                   "errors=" + ("; ".join(rep.errors)[:100] if rep.errors else "-")))

    rows = (base / "night" / "2026-10-28-00" / "manifest.tsv").read_text().splitlines()
    emb = [ln for ln in rows if "\tembench\t" in ln]
    checks.append(("manifest records rc=1 for red member",
                   bool(emb) and emb[0].split("\t")[2] == "1", str(emb)))

    rc = run_night(base, "2026-10-29-00", [("tset", "gem5-se-embench", "sleep 5")],
                   allow_overwrite=False, logdir=base / "logs",
                   timeouts={("tset", "gem5-se-embench"): 1})
    checks.append(("member timeout => overall rc=1", rc == 1, f"rc={rc}"))
    trow = (base / "night" / "2026-10-29-00" / "manifest.tsv").read_text().splitlines()
    to = [ln for ln in trow if "\tgem5-se-embench\t" in ln]
    checks.append(("manifest records rc=124 for timeout",
                   bool(to) and to[0].split("\t")[2] == "124", str(to)))
    rep = report_gate.check(base, "2026-10-29-00")
    checks.append(("timeout is reported separately",
                   any("超时" in e for e in rep.errors),
                   "errors=" + ("; ".join(rep.errors)[:100] if rep.errors else "-")))

    rc = run_night(base, "2026-10-27-00", green, allow_overwrite=False, logdir=base / "logs")
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
    ap = argparse.ArgumentParser(description="回归运行编排 + 报告落盘")
    ap.add_argument("--root", default=str(REPO_ROOT / ".dadao" / "tests"))
    ap.add_argument("--date", default=None, help="报告日期（默认 UTC 今天）")
    ap.add_argument("--member", action="append", default=None,
                    help="scope:suite=cmd（可重复；默认 tset full ×3 + arch + gem5 SE ×3 + gem5 FS）")
    ap.add_argument("--allow-overwrite", action="store_true")
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--machine", default=None,
                    help="meta.machine_id（默认 NIGHT_MACHINE_ID，再默认 hostname）")
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
                     Path(args.log_dir) if args.log_dir else None, args.machine,
                     MEMBER_TIMEOUTS)


if __name__ == "__main__":
    sys.exit(main())
