#!/usr/bin/env python3
"""gem5 SE tset baseline (GEM5-021t).

Runs the three tset suites (libc-test, llvm-ts, embench) in **static** link
mode on both engines -- QEMU user mode and gem5 syscall emulation -- and joins
the two per-case JSONs by case id:

    python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py \
        --work-dir <runtime dir> --json-out <runtime dir>/baseline.json

The drivers do the enumeration, the build lines and the verdicts; this script
only orchestrates the two runs and produces the cross-table.  Nothing here
decides a case's expected value, and no case is ever counted as ``pass`` on
gem5 SE unless the driver's own oracle said so.

Classification used in the report (counted from the JSONs, never written by
hand):

* ``both_pass``      -- both engines reached the case's own verdict "pass";
* ``blocked``        -- gem5 SE could not run the case to a verdict (static-ELF
                        gate, unimplemented syscall, timeout, non-guest end);
                        reported with the capability gap, never as pass/fail;
* ``gem5_only_fail`` -- QEMU passed (or admitted a known-fail) and gem5 SE
                        reached a *non-pass* verdict;
* ``qemu_only_fail`` -- gem5 SE passed and QEMU did not.  ADR-0048 D5: this
                        direction is **not** accepted as a gem5 win; it is
                        listed separately for a QEMU/spec investigation.

Outputs: the full per-case baseline JSON under ``--json-out`` (runtime
directory, not committed) and a compact summary (JSON + Markdown) under
``--summary-dir`` -- the summary carries ids, counts and evidence, never a
runtime path.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))

SUITES = ("libc-test", "llvm-ts", "embench")

DRIVERS = {
    "libc-test": os.path.join(
        "tools", "testcases", "tset", "libc-test",
        "run_libc_test_user_suite.py"),
    "llvm-ts": os.path.join(
        "tools", "testcases", "tset", "llvm-ts", "run_llvm_ts_user.py"),
    "embench": os.path.join(
        "tools", "testcases", "tset", "embench", "run_embench_user_suite.py"),
}

# The driver's JSON key that names a case, per suite.
CASE_KEY = {
    "libc-test": lambda c: c["case"],
    "llvm-ts": lambda c: c["case"],
    "embench": lambda c: f"{c['benchmark']}-{c['opt']}",
}

# Statuses as the drivers report them.
PASS_STATUSES = ("pass",)
NON_PASS_STATUSES = ("fail", "known-fail", "blocked")

# Which layer has to change for a capability bucket.  Used by the gap
# inventory; the driver evidence (syscall number/name, ELF fact) is kept
# per case in the JSON.
CHANGE_SURFACE = {
    "heap/VMA (brk)": "syscall: brk (SEWorkload syscall table + VMA/heap map)",
    "heap/VMA (mmap)": "syscall: mmap + anonymous VMA allocation",
    "heap/VMA (munmap)": "syscall: munmap + VMA teardown",
    "heap/VMA (mremap)": "syscall: mremap",
    "heap/VMA (madvise)": "syscall: madvise (advisory)",
    "threads/futex": "syscall: clone/clone3/futex + TLS block per thread",
    "signals": "syscall: rt_sigaction/rt_sigprocmask + signal frame",
    "file I/O": "syscall: file syscalls + guest fd table",
    "time/clocks": "syscall: clock_gettime/nanosleep (+ SE clock source)",
    "process info": "syscall: getpid/uname/getuid family",
    "SysV IPC": "syscall: SysV IPC (msg/sem/shm) + guest kernel objects",
    "IPC/socket/pipe": "syscall: pipe2/socket family + guest pipe/socket objects",
    "process creation/exec": "syscall: execve/fork/wait4 + multi-process SE support",
    "resource limits": "syscall: prlimit64/getrlimit (+ per-process limit state)",
    "scheduling": "syscall: sched_*/setpriority (single-thread SE: report values)",
    "random": "syscall: getrandom (+ deterministic SE entropy source)",
    "process startup/TLS": "process: arch_prctl/TLS setup in the SE loader",
    "loader/ELF modality": "loader: static ET_EXEC only (ET_DYN/PT_INTERP later)",
    "time budget": "simulator: per-case budget / engine speed (not a capability)",
    "simulator/loader": "simulator: SE loader/exit modelling",
    "other": "syscall: number not in the capability buckets -- inspect evidence",
}


def abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def component_lock_commit(name: str):
    """The locked upstream commit for a component (single source of truth)."""
    path = os.path.join(REPO_ROOT, "manifests", "components.lock.toml")
    try:
        text = open(path).read()
    except OSError:
        return None
    for m in re.finditer(r"\[\[component\]\](.*?)(?=\n\[\[component\]\]|\Z)",
                         text, re.S):
        body = m.group(1)
        if re.search(r'^name\s*=\s*"%s"' % re.escape(name), body, re.M):
            cm = re.search(r'^commit\s*=\s*"([0-9a-f]+)"', body, re.M)
            return cm.group(1) if cm else None
    return None


def series_patches(path="components/gem5/series"):
    try:
        with open(os.path.join(REPO_ROOT, path)) as fh:
            return sum(1 for line in fh if line.strip()
                       and not line.strip().startswith("#"))
    except OSError:
        return None


def engine_build(banner_path):
    """Engine identity of the run that produced the snapshot.

    ``gem5.opt`` prints its version and compile time in the per-case simulator
    log; the sha256 is taken from the driver records when they carry one (a
    shared build tree may be rebuilt by another task after the snapshot, so a
    hash read *now* would not describe these numbers).
    """
    build = dict(component_lock_commit=component_lock_commit("gem5"),
                 series_patches=series_patches(), gem5_version=None,
                 gem5_compiled=None, gem5_opt_sha256=None,
                 banner_source=(os.path.basename(banner_path)
                                if banner_path else None))
    if banner_path:
        try:
            with open(banner_path, "r", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        mv = re.search(r"^gem5 version (.+)$", text, re.M)
        mc = re.search(r"^gem5 compiled (.+)$", text, re.M)
        build["gem5_version"] = mv.group(1).strip() if mv else None
        build["gem5_compiled"] = mc.group(1).strip() if mc else None
    return build


def iso_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def sanitize(text):
    """Keep runtime locations out of the committed summary.

    The drivers quote the corpus/ELF location in their reasons; the summary is
    a knowledge artifact, so any absolute prefix in front of a repo-relative
    root marker (``.work/`` / ``.dadao/``) is dropped.  Nothing is hardcoded:
    a worktree or build tree may live anywhere, and the marker is the stable
    part.  Stray per-task temp directories are dropped the same way.
    """
    if not text:
        return text
    text = " ".join(str(text).split())
    text = re.sub(r"(?<![\w.])/(?:[^\s:/]+/+)*(?=\.(?:work|dadao)/)", "", text)
    text = re.sub(r"/tmp/opencode/[^/\s]+/", "", text)
    text = text.replace(".work/source/", "").replace(".dadao/", "")
    return text


def short(text, limit=240):
    """Trim a driver reason for the committed summary (full text stays in the
    runtime JSON); never drops the leading evidence."""
    if not text:
        return None
    text = sanitize(text)
    return text if len(text) <= limit else text[:limit - 1] + "…"


def driver_command(suite, engine, args, work_dir):
    cmd = [sys.executable, os.path.join(REPO_ROOT, DRIVERS[suite]),
           "--link-mode", "static", "--engine", engine,
           "--jobs", str(args.jobs),
           "--work-dir", os.path.join(work_dir, f"drv-{suite}-{engine}"),
           "--json-out", os.path.join(work_dir, f"{suite}-{engine}.json"),
           "--report-out", os.path.join(work_dir, f"{suite}-{engine}.log")]
    if engine == "gem5-se":
        cmd += ["--gem5-timeout", str(args.gem5_timeout)]
    if suite == "llvm-ts":
        cmd += ["--timeout", str(args.qemu_timeout)]
    return cmd


def run_driver(suite, engine, args, work_dir):
    cmd = driver_command(suite, engine, args, work_dir)
    log_path = os.path.join(work_dir, f"{suite}-{engine}.driver.log")
    print(f"[run] {suite}/{engine}: {' '.join(cmd)}", flush=True)
    with open(log_path, "wb") as log:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, stdout=log,
                              stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL)
    with open(os.path.join(work_dir, f"{suite}-{engine}.driver.rc"), "w") as fh:
        fh.write(f"{proc.returncode}\n")
    print(f"[run] {suite}/{engine}: rc={proc.returncode} log={log_path}",
          flush=True)
    return proc.returncode


def load_cases(suite, path):
    with open(path, "r") as fh:
        record = json.load(fh)
    cases = {}
    for case in record.get("cases", []):
        cases[CASE_KEY[suite](case)] = case
    return record, cases


def gap_of(case):
    gap = case.get("gap") or {}
    return gap.get("capability") or None


def compare_suite(suite, qemu_record, qemu_cases, gem5_record, gem5_cases,
                  qemu_rc, gem5_rc):
    """Cross-table for one suite; every count is derived from the two JSONs."""
    keys = sorted(set(qemu_cases) | set(gem5_cases))
    rows = []
    cross = dict(both_pass=[], gem5_only_fail=[], qemu_only_fail=[],
                 gem5_blocked=[], blocked_but_qemu_pass=[],
                 qemu_blocked_gem5_pass=[], both_non_pass=[])
    for key in keys:
        q = qemu_cases.get(key)
        g = gem5_cases.get(key)
        q_status = q.get("klass") if q else "absent"
        g_status = g.get("klass") if g else "absent"
        row = dict(case=key, qemu_status=q_status, gem5_status=g_status,
                   qemu_exit=None if not q else q.get("exit"),
                   gem5_exit=None if not g else g.get("exit"),
                   gem5_capability=None if not g else gap_of(g),
                   gem5_reason=None if not g else g.get("reason"),
                   qemu_reason=None if not q else q.get("reason"))
        rows.append(row)
        if q_status in PASS_STATUSES and g_status in PASS_STATUSES:
            cross["both_pass"].append(key)
        elif g_status == "blocked":
            cross["gem5_blocked"].append(key)
            if q_status in PASS_STATUSES:
                cross["blocked_but_qemu_pass"].append(key)
        elif g_status in ("fail", "known-fail", "absent") and \
                q_status in PASS_STATUSES:
            cross["gem5_only_fail"].append(key)
        elif g_status in PASS_STATUSES and q_status in ("fail", "known-fail",
                                                        "blocked", "absent"):
            cross["qemu_only_fail"].append(key)
            if q_status == "blocked":
                cross["qemu_blocked_gem5_pass"].append(key)
        elif q_status in NON_PASS_STATUSES and g_status in NON_PASS_STATUSES:
            cross["both_non_pass"].append(key)
    counts = {k: len(v) for k, v in cross.items()}
    return dict(
        qemu=dict(rc=qemu_rc, engine=qemu_record.get("engine", "qemu"),
                  counts=qemu_record.get("counts", {}),
                  discovered=qemu_record.get("discovered"),
                  total=qemu_record.get("total")),
        gem5=dict(rc=gem5_rc, engine=gem5_record.get("engine", "gem5-se"),
                  counts=gem5_record.get("counts", {}),
                  discovered=gem5_record.get("discovered"),
                  total=gem5_record.get("total"),
                  timeout=gem5_record.get("gem5_timeout")),
        cross_counts=counts, cross=cross, cases=rows)


def gap_inventory(suites):
    buckets = {}
    for suite, data in suites.items():
        for row in data["cases"]:
            if row["gem5_status"] != "blocked":
                continue
            cap = row["gem5_capability"] or "unattributed"
            entry = buckets.setdefault(cap, dict(capability=cap, cases=[]))
            entry["cases"].append(dict(suite=suite, case=row["case"],
                                       reason=row["gem5_reason"],
                                       qemu_status=row["qemu_status"]))
    out = []
    for cap, entry in buckets.items():
        cases = sorted(entry["cases"], key=lambda c: (c["suite"], c["case"]))
        out.append(dict(
            capability=cap,
            blocked_cases=len(cases),
            representative_cases=[f"{c['suite']}:{c['case']}" for c in cases[:5]],
            required_change=CHANGE_SURFACE.get(cap, CHANGE_SURFACE["other"]),
            cases=cases,
        ))
    out.sort(key=lambda e: (-e["blocked_cases"], e["capability"]))
    return out


def load_recheck(suite, path):
    """Per-case result of a longer-budget rerun of the timeout cases."""
    with open(path) as fh:
        record = json.load(fh)
    rows = []
    for case in record.get("cases", []):
        rows.append(dict(case=CASE_KEY[suite](case),
                         gem5_status=case.get("klass"),
                         gem5_exit=case.get("exit"),
                         gem5_capability=(case.get("gap") or {}).get(
                             "capability"),
                         gem5_reason=short(case.get("reason"))))
    passed = sorted(r["case"] for r in rows if r["gem5_status"] == "pass")
    blocked = sorted(r["case"] for r in rows if r["gem5_status"] == "blocked")
    other_rows = [r for r in rows if r["gem5_status"] not in ("pass", "blocked")]
    other = sorted(r["case"] for r in other_rows)
    return dict(timeout_seconds=record.get("gem5_timeout"),
                total=len(rows), passed=passed, still_blocked=blocked,
                other=other,
                other_cases=[dict(case=r["case"], status=r["gem5_status"],
                                  reason=r["gem5_reason"])
                             for r in other_rows],
                cases=rows)


def build_summary(suites, gap_list, args, stamp, recheck=None, build=None):
    totals = dict(qemu_pass=0, gem5_pass=0, blocked=0, blocked_but_qemu_pass=0,
                  gem5_only_fail=0, qemu_only_fail=0, both_pass=0)
    for data in suites.values():
        q = data["qemu"]["counts"]
        g = data["gem5"]["counts"]
        totals["qemu_pass"] += q.get("pass", 0)
        totals["gem5_pass"] += g.get("pass", 0)
        totals["both_pass"] += data["cross_counts"]["both_pass"]
        totals["blocked"] += data["cross_counts"]["gem5_blocked"]
        totals["blocked_but_qemu_pass"] += \
            data["cross_counts"]["blocked_but_qemu_pass"]
        totals["gem5_only_fail"] += data["cross_counts"]["gem5_only_fail"]
        totals["qemu_only_fail"] += data["cross_counts"]["qemu_only_fail"]
    return dict(
        task="GEM5-021t",
        generated_utc=stamp,
        scope=("static link mode only (ADR-0048 D4 static first); dynamic "
               "linking/TLS/threads are outside this round"),
        engines=dict(
            qemu="qemu-user (qemu-dadao, same static ELF)",
            gem5_se=("gem5 syscall emulation: component build's gem5.opt + "
                     "configs/dadao/se.py --binary <elf> (GEM5-014t)"),
        ),
        jobs=args.jobs,
        gem5_timeout_seconds=args.gem5_timeout,
        suites={name: dict(
            qemu=data["qemu"], gem5=data["gem5"],
            cross_counts=data["cross_counts"], cross=data["cross"],
            cases=[dict(case=r["case"], qemu_status=r["qemu_status"],
                        gem5_status=r["gem5_status"], qemu_exit=r["qemu_exit"],
                        gem5_exit=r["gem5_exit"],
                        gem5_capability=r["gem5_capability"],
                        gem5_reason=short(r["gem5_reason"]),
                        qemu_reason=short(r["qemu_reason"]))
                   for r in data["cases"]],
        ) for name, data in suites.items()},
        totals=totals,
        gap_inventory=gap_list,
        timeout_recheck=recheck or {},
        build=build or {},
        snapshot_note=("数字为 2026-11-06 的快照；随 GEM5-022t（brk/mmap 等 SE "
                       "能力）与后续任务落地，同一命令会得到不同计数。"),
    )


def markdown(summary):
    lines = []

    def out(text=""):
        lines.append(text)

    out("# GEM5-021t gem5 SE tset 基线（static）")
    out()
    out(f"生成：{summary['generated_utc']}（计数全部由本脚本从两份驱动 JSON 现场统计）")
    out()
    out(f"> **快照说明**：{summary.get('snapshot_note', '')}")
    out()
    out(f"范围：{summary['scope']}")
    out()
    out("## 总览")
    out()
    t = summary["totals"]
    out(f"- QEMU user 通过：{t['qemu_pass']}")
    out(f"- gem5 SE 通过：{t['gem5_pass']}")
    out(f"- 两侧都通过（both_pass）：{t['both_pass']}")
    out(f"- gem5 SE blocked：{t['blocked']}（其中 QEMU 通过 = {t['blocked_but_qemu_pass']}）")
    out(f"- gem5_only_fail（QEMU 通过、gem5 非通过且未 blocked）：{t['gem5_only_fail']}")
    out(f"- qemu_only_fail（gem5 通过、QEMU 未通过，ADR-0048 D5 需定位）：{t['qemu_only_fail']}")
    recheck = summary.get("timeout_recheck") or {}
    if recheck:
        extra_pass = sum(len(d["passed"]) for d in recheck.values())
        extra_fail = sum(len(d["other"]) for d in recheck.values())
        out(f"- 超预算重测另计（不计入上表）：通过 {extra_pass}、非通过 {extra_fail}"
            f"（超时案例在更长预算下重跑，见下节）")
    out()
    out("## 分套件")
    out()
    for name, data in summary["suites"].items():
        qc = data["qemu"]["counts"]
        gc = data["gem5"]["counts"]
        out(f"### {name}")
        out()
        out(f"- 发现/执行：QEMU discovered={data['qemu']['discovered']} "
            f"total={data['qemu']['total']}；gem5 discovered={data['gem5']['discovered']} "
            f"total={data['gem5']['total']}")
        out(f"- QEMU 计数：{qc}")
        out(f"- gem5 计数：{gc}（SE 超时 {data['gem5']['timeout']}s/例）")
        cc = data["cross_counts"]
        out(f"- 交叉：both_pass={cc['both_pass']} gem5_blocked={cc['gem5_blocked']} "
            f"(QEMU 通过 {cc['blocked_but_qemu_pass']}) "
            f"gem5_only_fail={cc['gem5_only_fail']} "
            f"qemu_only_fail={cc['qemu_only_fail']} both_non_pass={cc['both_non_pass']}")
        out()
    out("## gem5_only_fail（QEMU 通过、gem5 未通过）")
    out()
    any_row = False
    for name, data in summary["suites"].items():
        for row in data["cases"]:
            if row["gem5_status"] not in ("fail", "known-fail"):
                continue
            if row["qemu_status"] != "pass":
                continue
            any_row = True
            out(f"- {name}:{row['case']} gem5={row['gem5_status']} "
                f"exit={row['gem5_exit']} — {row['gem5_reason']}")
    if not any_row:
        out("（无）")
    out()
    out("## qemu_only_fail（gem5 通过、QEMU 未通过；ADR-0048 D5 单列）")
    out()
    any_row = False
    for name, data in summary["suites"].items():
        for row in data["cases"]:
            if row["gem5_status"] == "pass" and row["qemu_status"] != "pass":
                any_row = True
                out(f"- {name}:{row['case']} qemu={row['qemu_status']} "
                    f"exit={row['qemu_exit']} — {row['qemu_reason']}")
    if not any_row:
        out("（无）")
    out()
    out("## gem5 SE 缺口分类")
    out()
    gaps = summary["gap_inventory"]
    if not gaps:
        out("（无 blocked）")
    else:
        out("| 能力 | blocked 案例数 | 代表案例 | 所需改动面 |")
        out("| --- | --- | --- | --- |")
        for gap in gaps:
            reps = "、".join(gap["representative_cases"]) or "-"
            out(f"| {gap['capability']} | {gap['blocked_cases']} | {reps} | "
                f"{gap['required_change']} |")
    out()
    out("## 超预算重测（120s 超时案例在更长预算下重跑）")
    out()
    recheck = summary.get("timeout_recheck") or {}
    if not recheck:
        out("（未重测）")
    else:
        for suite, data in recheck.items():
            out(f"- {suite}：重测 {data['total']} 例（预算 {data['timeout_seconds']}s）"
                f"→ 通过 {len(data['passed'])}、仍 blocked {len(data['still_blocked'])}、"
                f"其他 {len(data['other'])}")
            if data["passed"]:
                out(f"  - 通过：{', '.join(data['passed'])}")
            if data["still_blocked"]:
                out(f"  - 仍 blocked：{', '.join(data['still_blocked'])}")
            for row in data.get("other_cases") or []:
                out(f"  - 非通过 {row['case']}（{row['status']}）：{row['reason']}")
    out()
    out("## 引擎与快照")
    out()
    build = summary.get("build") or {}
    out(f"- gem5 组件锁定 commit：`{build.get('component_lock_commit')}`")
    out(f"- 分支补丁集：`components/gem5/series` {build.get('series_patches')} 条")
    out(f"- 快照引擎：gem5 `{build.get('gem5_version')}`，编译于 "
        f"`{build.get('gem5_compiled')}`（banner 取自运行期 sim 日志）")
    if build.get("gem5_opt_sha256"):
        out(f"- gem5.opt sha256：`{build['gem5_opt_sha256']}`")
    else:
        out("- gem5.opt sha256：不可复原（共享构建树在快照后被并行任务重建覆盖）；"
            "同一 `commit`+`series` 可由 `make build-gem5` 复现")
    out()
    out("## 复跑")
    out()
    out("```")
    out("JOBS=32 python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py \\")
    out("    --work-dir <runtime dir> --json-out <runtime dir>/gem5-se-baseline.json")
    out("```")
    out()
    out("驱动层单套件：给三个 tset 驱动加 `--engine qemu|gem5-se`；gem5 SE 走 "
        "`configs/dadao/se.py --binary <elf>`，只接受静态 `ET_EXEC`。")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="gem5 SE tset baseline (GEM5-021t)")
    ap.add_argument("--work-dir", required=True,
                    help="runtime directory for per-case artifacts/JSONs")
    ap.add_argument("--json-out", required=True,
                    help="full baseline JSON (runtime; per-case detail)")
    ap.add_argument("--summary-dir", default=".tao/knowledge/refs",
                    help="where the compact summary JSON+Markdown go")
    ap.add_argument("--suites", default=",".join(SUITES),
                    help="comma-separated subset (default: all three)")
    ap.add_argument("--jobs", type=int, default=32)
    ap.add_argument("--gem5-timeout", type=int, default=120)
    ap.add_argument("--qemu-timeout", type=int, default=300)
    ap.add_argument("--aggregate-only", action="store_true",
                    help="reuse the driver JSONs already in --work-dir")
    ap.add_argument("--engine-banner", default=None,
                    help="a per-case gem5 simulator log from the snapshot run; "
                         "its banner pins the engine version/compile time")
    ap.add_argument("--recheck", default=None,
                    help="comma-separated suite=json: longer-budget rerun of "
                         "the timeout cases (reported separately, never "
                         "merged into the primary counts)")
    args = ap.parse_args()

    work_dir = abspath(args.work_dir)
    os.makedirs(work_dir, exist_ok=True)
    suites_wanted = [s.strip() for s in args.suites.split(",") if s.strip()]
    unknown = [s for s in suites_wanted if s not in SUITES]
    if unknown:
        sys.stderr.write(f"ERROR: unknown suite(s) {unknown}\n")
        return 2

    if not args.aggregate_only:
        for suite in suites_wanted:
            for engine in ("qemu", "gem5-se"):
                run_driver(suite, engine, args, work_dir)

    suites = {}
    for suite in suites_wanted:
        qemu_path = os.path.join(work_dir, f"{suite}-qemu.json")
        gem5_path = os.path.join(work_dir, f"{suite}-gem5-se.json")
        for path in (qemu_path, gem5_path):
            if not os.path.isfile(path):
                sys.stderr.write(f"ERROR: missing driver JSON: {path}\n")
                return 2
        qemu_record, qemu_cases = load_cases(suite, qemu_path)
        gem5_record, gem5_cases = load_cases(suite, gem5_path)
        qemu_rc = read_rc(os.path.join(work_dir, f"{suite}-qemu.driver.rc"))
        gem5_rc = read_rc(os.path.join(work_dir, f"{suite}-gem5-se.driver.rc"))
        suites[suite] = compare_suite(suite, qemu_record, qemu_cases,
                                      gem5_record, gem5_cases, qemu_rc, gem5_rc)

    gap_list = gap_inventory(suites)
    recheck = {}
    if args.recheck:
        for spec in args.recheck.split(","):
            if not spec.strip():
                continue
            suite, _, path = spec.partition("=")
            suite = suite.strip()
            if suite not in SUITES or not path:
                sys.stderr.write(f"ERROR: bad --recheck {spec!r}\n")
                return 2
            recheck[suite] = load_recheck(suite, abspath(path))
    build = engine_build(abspath(args.engine_banner)
                         if args.engine_banner else None)
    stamp = iso_utc()
    summary = build_summary(suites, gap_list, args, stamp, recheck, build)

    json_out = abspath(args.json_out)
    os.makedirs(os.path.dirname(json_out) or ".", exist_ok=True)
    with open(json_out, "w") as fh:
        json.dump(summary, fh, indent=2)

    summary_dir = abspath(args.summary_dir)
    os.makedirs(summary_dir, exist_ok=True)
    summary_json = os.path.join(summary_dir, "GEM5-021t-baseline-summary.json")
    summary_md = os.path.join(summary_dir, "GEM5-021t-baseline-summary.md")
    with open(summary_json, "w") as fh:
        json.dump(summary, fh, indent=2)
    with open(summary_md, "w") as fh:
        fh.write(markdown(summary))

    print(f"baseline JSON: {json_out}")
    print(f"summary: {summary_json}")
    print(f"markdown: {summary_md}")
    t = summary["totals"]
    print(f"totals: qemu_pass={t['qemu_pass']} gem5_pass={t['gem5_pass']} "
          f"both_pass={t['both_pass']} blocked={t['blocked']} "
          f"(qemu_pass-blocked={t['blocked_but_qemu_pass']}) "
          f"gem5_only_fail={t['gem5_only_fail']} "
          f"qemu_only_fail={t['qemu_only_fail']}")
    return 0


def read_rc(path):
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    sys.exit(main())
