#!/usr/bin/env python3
"""m13-testcases-001: static long-tail engine time ratio (gem5 SE vs qemu-user).

Takes the cases that still timed out at the 1200 s recheck of GEM5-021t
(``timeout_recheck.<suite>.still_blocked``) and measures, per case, the wall
clock of the *same* built ELF on both engines:

    qemu_seconds = driver ``run_seconds`` of ``--engine qemu``
    gem5_seconds = driver ``run_seconds`` of ``--engine gem5-se``
    ratio        = gem5_seconds / qemu_seconds

This script adds **no engine code**: it drives the three tset drivers
(``tset/libc-test``, ``tset/llvm-ts``, ``tset/embench``) exactly as
``run_gem5_se_baseline.py`` does, with the case selection the drivers already
support (``--filter`` / ``--only``), and joins their per-case JSONs.  Every
number comes from a driver record; nothing is estimated here.

Measurement settings (a measurement, never a verdict):

* both engines run at the same ``--jobs`` so the concurrency (and therefore the
  scheduling pressure) is identical on both sides;
* the per-case budget is ``--gem5-timeout`` / ``--qemu-timeout`` (default
  3600 s); a case that hits it keeps its ``*_seconds`` but is flagged
  ``*_timeout`` and kept out of the ratio distribution (a truncated run is not
  a ratio);
* ``--repeats N`` runs every engine round N times and reports the per-case
  relative range ``(max-min)/mean*100`` as repeatability evidence.

Outputs (both carry ids, counts and evidence only -- never a runtime path):

* ``--json-out``  full per-case JSON;
* ``--md-out``    human report (default: same stem as ``--json-out`` + ``.md``).

A case missing from either driver record, or a record without ``run_seconds``,
is a hard error (``ok=false``, exit 1): a silent skip would fake a ratio.

Nothing here changes a source, a case, an expectation or a gate.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shlex
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

ENGINES = ("qemu", "gem5-se")
ENGINE_LABEL = {"qemu": "qemu", "gem5-se": "gem5"}

DEFAULT_CASE_LIST = ".tao/knowledge/refs/GEM5-021t-baseline-summary.json"
DEFAULT_GEM5 = ".work/source/gem5/build/DADAO/gem5.opt"
DEFAULT_SE_CONFIG = ".work/source/gem5/configs/dadao/se.py"
DEFAULT_MUSL = ".work/source/musl"
DEFAULT_QEMU = ".dadao/cross-toolchain/bin/qemu-dadao"

TASK = "m13-testcases-001"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def abspath(repo: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(repo, path)


def iso_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def md5_file(path: str):
    try:
        digest = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def first_line(cmd, cwd=None):
    """First non-empty line of a command's stdout, or ``None`` (never fatal).

    Used for engine identity only; a missing binary must not stop the
    measurement (it is already required by the drivers).
    """
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.strip():
            return line.strip()
    return None


def git_head(path: str):
    try:
        proc = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              stdin=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def git_dirty(path: str) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", path, "status", "--porcelain", "-uall"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode != 0 or bool(proc.stdout.strip())


def cpu_model():
    try:
        with open("/proc/cpuinfo", "r", errors="replace") as fh:
            for line in fh:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


def sanitize(text):
    """Drop absolute runtime prefixes from a reason (summary stays path-free)."""
    if not text:
        return text
    text = " ".join(str(text).split())
    text = re.sub(r"/tmp/opencode/[^/\s]+/", "", text)
    text = re.sub(r"(?<![\w.])/(?:[^\s:/]+/+)*(?=\.(?:work|dadao)/)", "", text)
    text = text.replace(".work/source/", "").replace(".dadao/", "")
    return text


def short(text, limit=240):
    if not text:
        return None
    text = sanitize(text)
    return text if len(text) <= limit else text[:limit - 1] + "…"


# ---------------------------------------------------------------------------
# case selection (the 1200 s recheck of GEM5-021t)
# ---------------------------------------------------------------------------
def load_selection(path: str, suites):
    """``{suite: [case ids]}`` of the still-blocked cases of the 1200 s recheck.

    The field is ``timeout_recheck.<suite>.still_blocked`` in the GEM5-021t
    summary.  A missing/empty field for a requested suite is an error: the
    selection is never guessed or widened to "all timeout cases".
    """
    with open(path, "r") as fh:
        record = json.load(fh)
    recheck = record.get("timeout_recheck") or {}
    if not recheck:
        raise ValueError(f"{os.path.basename(path)}: no timeout_recheck record")
    out = {}
    for suite in suites:
        data = recheck.get(suite) or {}
        ids = list(data.get("still_blocked") or [])
        if not ids:
            raise ValueError(
                f"{os.path.basename(path)}: timeout_recheck.{suite}."
                f"still_blocked is empty/missing")
        out[suite] = ids
    return out


def narrow_selection(selection, only):
    """Keep the case ids named by ``--only`` (pilot subset).

    Every requested id must be part of the selection; a typo would otherwise
    silently shrink the measurement.
    """
    if not only:
        return selection, False
    known = {cid: suite for suite, ids in selection.items() for cid in ids}
    unknown = [cid for cid in only if cid not in known]
    if unknown:
        raise ValueError(f"--only case(s) not in the recheck selection: {unknown}")
    picked = {}
    for cid in only:
        picked.setdefault(known[cid], []).append(cid)
    for suite in picked:
        picked[suite] = [cid for cid in selection[suite] if cid in picked[suite]]
    return picked, True


def category_of(suite: str, cid: str) -> str:
    """Coarse class for the ratio-vs-category view (derived, never authored)."""
    parts = cid.split("/")
    if suite == "libc-test":
        return parts[0] if len(parts) > 1 else cid
    if len(parts) >= 3 and parts[0] == "MultiSource" and parts[1] == "Benchmarks":
        return "/".join(parts[:3])
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return cid


# ---------------------------------------------------------------------------
# driver invocation
# ---------------------------------------------------------------------------
def driver_command(repo, suite, engine, args, work_dir, rep, cases):
    cmd = [sys.executable, os.path.join(repo, DRIVERS[suite]),
           "--link-mode", "static", "--engine", engine,
           "--jobs", str(args.jobs),
           "--work-dir", os.path.join(work_dir, f"drv-{suite}-{engine}-r{rep}"),
           "--json-out", os.path.join(work_dir, f"{suite}-{engine}-r{rep}.json"),
           "--report-out", os.path.join(work_dir, f"{suite}-{engine}-r{rep}.log"),
           "--gem5-timeout", str(args.gem5_timeout),
           "--timeout", str(args.qemu_timeout)]
    if suite == "libc-test":
        alternation = "|".join(re.escape(c) for c in cases)
        cmd += ["--filter", "^(?:" + alternation + ")$"]
    elif suite == "llvm-ts":
        for cid in cases:
            cmd += ["--only", "^" + re.escape(cid) + "$"]
    else:
        raise ValueError(f"no case selection flag for suite {suite!r}")
    if args.gem5_bin:
        cmd += ["--gem5", args.gem5_bin]
    if args.gem5_config:
        cmd += ["--gem5-config", args.gem5_config]
    if args.qemu_bin:
        cmd += ["--qemu", args.qemu_bin]
    return cmd


def run_driver(repo, suite, engine, args, work_dir, rep, cases):
    """Run one engine round; return ``(rc, json path)``.

    A driver exit code 1 is expected (a case that stays ``blocked``/``fail``
    makes the driver report non-zero); the JSON is the product and is parsed
    either way.
    """
    cmd = driver_command(repo, suite, engine, args, work_dir, rep, cases)
    log_path = os.path.join(work_dir, f"{suite}-{engine}-r{rep}.driver.log")
    print(f"[run] {suite}/{engine} rep={rep}: {' '.join(shlex.quote(c) for c in cmd)}",
          flush=True)
    with open(log_path, "wb") as log:
        proc = subprocess.run(cmd, cwd=repo, stdout=log,
                              stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL)
    with open(log_path + ".rc", "w") as fh:
        fh.write(f"{proc.returncode}\n")
    print(f"[run] {suite}/{engine} rep={rep}: rc={proc.returncode}", flush=True)
    return proc.returncode, os.path.join(work_dir, f"{suite}-{engine}-r{rep}.json")


def load_driver(path):
    with open(path, "r") as fh:
        record = json.load(fh)
    cases = {}
    for case in record.get("cases", []):
        cases[case["case"]] = case
    return record, cases


def driver_json_complete(path, cases) -> bool:
    """True when the JSON exists and covers every selected case with a time."""
    if not os.path.isfile(path):
        return False
    try:
        _, found = load_driver(path)
    except (OSError, ValueError):
        return False
    return all(cid in found and found[cid].get("run_seconds") is not None
               for cid in cases)


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------
def percentile(values, pct):
    """Linear-interpolated percentile (no third-party dependency)."""
    data = sorted(values)
    if not data:
        return None
    if len(data) == 1:
        return data[0]
    pos = (len(data) - 1) * pct / 100.0
    lo = int(pos)
    hi = min(lo + 1, len(data) - 1)
    frac = pos - lo
    return data[lo] * (1.0 - frac) + data[hi] * frac


def distribution(values):
    data = [v for v in values if v is not None]
    if not data:
        return dict(n=0, min=None, median=None, p90=None, max=None)
    return dict(n=len(data), min=round(min(data), 4),
                median=round(percentile(data, 50), 4),
                p90=round(percentile(data, 90), 4), max=round(max(data), 4))


def relative_range(values):
    """``(max-min)/mean*100``; ``None`` for fewer than two samples/zero mean."""
    data = [float(v) for v in values if v is not None]
    if len(data) < 2:
        return None
    mean = sum(data) / len(data)
    if mean <= 0:
        return None
    return round((max(data) - min(data)) / mean * 100.0, 2)


def is_timeout_reason(reason) -> bool:
    return bool(reason) and str(reason).startswith("timeout after")


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
def collect_rows(selection, per_rep, repeats, inject=None):
    """Join the engine records into one row per selected case.

    ``per_rep`` is ``[{(suite, engine): {case: record}}, ...]`` (one map per
    repeat).  ``inject`` names a case whose qemu measurement is deliberately
    dropped -- evidence-only, it must surface in ``missing``.
    """
    rows, missing = [], []
    for suite, ids in selection.items():
        for cid in ids:
            row = dict(case=cid, suite=suite, category=category_of(suite, cid),
                       gem5_seconds=None, qemu_seconds=None, ratio=None,
                       gem5_klass=None, gem5_exit=None, gem5_gap=None,
                       gem5_timeout=False, qemu_klass=None, qemu_exit=None,
                       qemu_timeout=False, repeats={}, variance_pct={})
            for engine in ENGINES:
                values, first = [], None
                for rep, maps in enumerate(per_rep):
                    case = (maps.get((suite, engine)) or {}).get(cid)
                    if case is None:
                        missing.append(dict(case=cid, suite=suite,
                                            engine=engine, repeat=rep + 1,
                                            why="case absent from driver JSON"))
                        continue
                    seconds = case.get("run_seconds")
                    if inject is not None and inject == cid and engine == "qemu":
                        missing.append(dict(case=cid, suite=suite,
                                            engine=engine, repeat=rep + 1,
                                            why="INJECTED missing measurement "
                                                "(evidence run)"))
                        continue
                    if seconds is None:
                        missing.append(dict(case=cid, suite=suite,
                                            engine=engine, repeat=rep + 1,
                                            why="driver record has no run_seconds"))
                        continue
                    values.append(float(seconds))
                    if first is None:
                        first = case
                label = ENGINE_LABEL[engine]
                row["repeats"][engine] = [round(v, 2) for v in values]
                row["variance_pct"][engine] = relative_range(values)
                if not values:
                    continue
                row[f"{label}_seconds"] = round(sum(values) / len(values), 2)
                row[f"{label}_klass"] = first.get("klass")
                row[f"{label}_exit"] = first.get("exit")
                if engine == "gem5-se":
                    row["gem5_gap"] = (first.get("gap") or {}).get("capability")
                row[f"{label}_timeout"] = is_timeout_reason(first.get("reason"))
            if row["gem5_seconds"] and row["qemu_seconds"]:
                row["ratio"] = round(row["gem5_seconds"] / row["qemu_seconds"], 3)
            elif row["gem5_seconds"] is not None and row["qemu_seconds"] is not None:
                # Both measured, but one rounds to 0.00 s (sub-5 ms guest):
                # the ratio is undefined, not missing.
                row["ratio_undefined"] = ("a measured time rounds to 0.00 s; "
                                          "ratio undefined")
            rows.append(row)
    return rows, missing


def ratio_summary(rows):
    """Distribution and outliers over the untruncated rows only."""
    clean = [r for r in rows if r["ratio"] is not None
             and not r["gem5_timeout"] and not r["qemu_timeout"]]
    stats = distribution([r["ratio"] for r in clean])
    outliers = []
    if stats["median"]:
        lo, hi = stats["median"] / 3.0, stats["median"] * 3.0
        for row in clean:
            if row["ratio"] < lo or row["ratio"] > hi:
                outliers.append(dict(case=row["case"], suite=row["suite"],
                                     ratio=row["ratio"]))
    by_category = {}
    for row in clean:
        by_category.setdefault(row["category"], []).append(row["ratio"])
    categories = {
        name: dict(distribution(values), cases=len(values))
        for name, values in sorted(by_category.items())}
    return dict(ratio=stats, cases_in_distribution=len(clean),
                excluded_truncated=sum(
                    1 for r in rows if r["ratio"] is not None
                    and (r["gem5_timeout"] or r["qemu_timeout"])),
                outliers=outliers, by_category=categories)


def repeatability(rows, limit_pct):
    values = [v for row in rows for v in row["variance_pct"].values()
              if v is not None]
    if not values:
        return dict(limit_pct=limit_pct, samples=0, max_variance_pct=None,
                    comparable=None, note="no repeated measurement")
    worst = max(values)
    comparable = worst < limit_pct
    return dict(
        limit_pct=limit_pct, samples=len(values),
        max_variance_pct=round(worst, 2), comparable=comparable,
        note=None if comparable else
        "relative range >= limit: per-case time is not comparable across "
        "runs on this host/load; report as 时间不可比")


# ---------------------------------------------------------------------------
# fingerprint
# ---------------------------------------------------------------------------
def gem5_banner(work_dir: str):
    """``(version, compiled)`` from the first simulator log under *work_dir*.

    ``gem5.opt --version`` is not a supported flag (it prints usage), so the
    engine identity comes from the per-case banner the SE run writes into
    ``sim.log`` (the same source GEM5-021t used).  Returns ``(None, None)``
    when no log is present (e.g. an aggregate-only run of a deleted tree).
    """
    version = compiled = None
    if not work_dir:
        return version, compiled
    for root, _dirs, files in os.walk(work_dir):
        if "sim.log" not in files:
            continue
        try:
            with open(os.path.join(root, "sim.log"), "r",
                      errors="replace") as fh:
                text = fh.read(200000)
        except OSError:
            continue
        mv = re.search(r"^gem5 version (.+)$", text, re.M)
        mc = re.search(r"^gem5 compiled (.+)$", text, re.M)
        if mv:
            version = mv.group(1).strip()
            compiled = mc.group(1).strip() if mc else None
            break
    return version, compiled


def fingerprint(repo, args, work_dir=None):
    gem5 = args.gem5_bin or os.environ.get("GEM5_SE_BIN") or \
        abspath(repo, DEFAULT_GEM5)
    qemu = args.qemu_bin or abspath(repo, DEFAULT_QEMU)
    musl = abspath(repo, DEFAULT_MUSL)
    drivers = {suite: md5_file(os.path.join(repo, path))
               for suite, path in DRIVERS.items()}
    drivers["gem5_se_engine.py"] = md5_file(
        os.path.join(repo, "tools", "testcases", "lib", "gem5_se_engine.py"))
    gem5_version, gem5_compiled = gem5_banner(work_dir)
    return dict(
        host=platform.node(),
        cpu_model=cpu_model(),
        nproc=os.cpu_count(),
        jobs=args.jobs,
        engines=list(args.engines),
        gem5_timeout_seconds=args.gem5_timeout,
        qemu_timeout_seconds=args.qemu_timeout,
        gem5_binary=os.path.basename(gem5),
        gem5_md5=md5_file(gem5),
        gem5_version=gem5_version,
        gem5_compiled=gem5_compiled,
        qemu_binary=os.path.basename(qemu),
        qemu_md5=md5_file(qemu),
        qemu_version=first_line([qemu, "--version"]),
        musl_head=git_head(musl),
        musl_dirty=git_dirty(musl) if os.path.isdir(musl) else None,
        driver_md5=drivers,
        loadavg=[round(v, 2) for v in os.getloadavg()] if hasattr(
            os, "getloadavg") else None,
    )


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def build_report(args, selection, rows, missing, summary, repeat, prints):
    # Acceptance is "both engines measured on every case"; a ratio needs two
    # non-zero times, so a sub-5 ms guest leaves ratio null (flagged in the
    # row) without failing the run.
    ok = not missing and all(
        row["gem5_seconds"] is not None and row["qemu_seconds"] is not None
        for row in rows)
    return dict(
        task=TASK,
        generated_utc=iso_utc(),
        scope=("static long-tail: the cases that still timed out at the "
               "GEM5-021t 1200 s recheck, re-run with the per-case budget "
               "below on gem5 SE and qemu-user; times measured by the tset "
               "drivers' own run_seconds"),
        selection=dict(
            source=os.path.basename(args.case_list),
            field="timeout_recheck.<suite>.still_blocked",
            total=sum(len(ids) for ids in selection.values()),
            by_suite={suite: len(ids) for suite, ids in selection.items()},
            subset=args.only is not None),
        engines=dict(qemu="qemu-user (same guest ELF)",
                     gem5_se="gem5 syscall emulation (configs/dadao/se.py "
                             "--binary <elf>)"),
        jobs=args.jobs,
        repeats=args.repeats,
        fingerprint=prints,
        rows=rows,
        summary=summary,
        repeatability=repeat,
        missing=missing,
        ok=ok,
    )


def markdown(report):
    lines = []

    def out(text=""):
        lines.append(text)

    fp = report["fingerprint"]
    sel = report["selection"]
    out(f"# {report['task']}：static 长尾 {sel['total']} 例 gem5/qemu 运行时间比")
    out()
    out(f"生成：{report['generated_utc']}（数值全部由驱动 JSON 现场统计，无估算）")
    out()
    out(f"范围：{report['scope']}")
    out()
    out("## 执行环境指纹")
    out()
    out(f"- 节点：`{fp['host']}`；CPU：{fp['cpu_model']}；nproc={fp['nproc']}")
    out(f"- 并发：{fp['jobs']}（两引擎同值）；engines={','.join(fp['engines'])}")
    out(f"- 预算：gem5 {fp['gem5_timeout_seconds']}s / qemu "
        f"{fp['qemu_timeout_seconds']}s（每例）")
    out(f"- gem5：`{fp['gem5_binary']}` md5=`{fp['gem5_md5']}` "
        f"版本：{fp.get('gem5_version')}（编译于 {fp.get('gem5_compiled')}）")
    out(f"- qemu：`{fp['qemu_binary']}` md5=`{fp['qemu_md5']}` "
        f"版本：{fp['qemu_version']}")
    out(f"- musl HEAD：`{fp['musl_head']}`（dirty={fp['musl_dirty']}）")
    out(f"- 统计时 loadavg：{fp['loadavg']}")
    out()
    out("## 总览")
    out()
    out(f"- 选中案例：{sel['total']}（" + "、".join(
        f"{suite} {n}" for suite, n in sel["by_suite"].items()) + "）")
    measured = sum(1 for row in report["rows"]
                   if row["gem5_seconds"] is not None
                   and row["qemu_seconds"] is not None)
    out(f"- 两引擎都有测量：{measured}/{len(report['rows'])}；"
        f"缺失测量条目：{len(report['missing'])}")
    stat = report["summary"]["ratio"]
    out(f"- 比值分布（两引擎都未截断，n={stat['n']}）：min={stat['min']} "
        f"median={stat['median']} P90={stat['p90']} max={stat['max']}")
    out(f"- 截断（timeout）已单列、未计入分布："
        f"{report['summary']['excluded_truncated']} 例")
    rep = report["repeatability"]
    if rep["samples"]:
        out(f"- 重复性：{rep['samples']} 个重复样本，最大相对极差 "
            f"{rep['max_variance_pct']}%（限 {rep['limit_pct']}%）"
            f"{'；可比' if rep['comparable'] else '；**时间不可比**'}")
        if rep["note"]:
            out(f"  - 说明：{rep['note']}")
    out()
    out("## 比值分布（按类别）")
    out()
    cats = report["summary"]["by_category"]
    if not cats:
        out("（无可比样本）")
    else:
        out("| 类别 | n | min | median | P90 | max |")
        out("| --- | --- | --- | --- | --- | --- |")
        for name, row in cats.items():
            out(f"| {name} | {row['n']} | {row['min']} | {row['median']} | "
                f"{row['p90']} | {row['max']} |")
    out()
    out("## 离群（超出中位数 1/3–3 倍）")
    out()
    outliers = report["summary"]["outliers"]
    if not outliers:
        out("（无）")
    else:
        for row in outliers:
            out(f"- {row['suite']}:{row['case']} ratio={row['ratio']}")
    out()
    out("## 逐例")
    out()
    out("| suite | case | qemu_s | gem5_s | ratio | gem5_klass | exit | 备注 |")
    out("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in report["rows"]:
        note = []
        if row["gem5_timeout"]:
            note.append("gem5 截断")
        if row["qemu_timeout"]:
            note.append("qemu 截断")
        if row["gem5_gap"]:
            note.append(f"gap={row['gem5_gap']}")
        if row.get("ratio_undefined"):
            note.append("ratio 未定义")
        out(f"| {row['suite']} | {row['case']} | {row['qemu_seconds']} | "
            f"{row['gem5_seconds']} | {row['ratio']} | {row['gem5_klass']} | "
            f"{row['gem5_exit']} | {'; '.join(note) or '-'} |")
    out()
    if report["missing"]:
        out("## 缺失（FAIL）")
        out()
        for row in report["missing"]:
            out(f"- {row['suite']}:{row['case']} {row['engine']} "
                f"rep={row['repeat']}：{row['why']}")
        out()
    out("## 方法与口径")
    out()
    out("- 两引擎跑**同一个**已构建 ELF（驱动各自编译同一源，链接模式 static）；"
        "`*_seconds` 取驱动的 `run_seconds`（仅 guest 运行墙钟，不含编译）。")
    out("- `ratio = gem5_seconds / qemu_seconds`；仅在两引擎都未截断时纳入分布。")
    out("- 两引擎同 `--jobs`，调度压力一致；比值是 wall-clock 之比，不是指令数之比。")
    out("- 未改动任何源码、用例、期望或门控；本文件只记录观察，不做裁定。")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# self-test (no engine, no corpus)
# ---------------------------------------------------------------------------
def _synthetic_selection(tmpdir):
    record = dict(timeout_recheck=dict(
        **{"libc-test": dict(still_blocked=["functional/a", "regression/b"]),
           "llvm-ts": dict(still_blocked=["MultiSource/Benchmarks/Foo/bar"])}))
    path = os.path.join(tmpdir, "summary.json")
    with open(path, "w") as fh:
        json.dump(record, fh)
    return path


def _synthetic_driver(tmpdir, name, cases, engine):
    record = dict(engine=engine, cases=cases, counts={}, total=len(cases),
                  discovered=len(cases))
    path = os.path.join(tmpdir, name)
    with open(path, "w") as fh:
        json.dump(record, fh)
    return path


def self_test(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)
    checks = []

    def check(name, want, got):
        checks.append((name, want, got))

    summary_path = _synthetic_selection(tmpdir)
    selection = load_selection(summary_path, ["libc-test", "llvm-ts"])
    check("selection libc", ["functional/a", "regression/b"],
          selection["libc-test"])
    check("selection llvm", ["MultiSource/Benchmarks/Foo/bar"],
          selection["llvm-ts"])
    check("selection total", 3, sum(len(v) for v in selection.values()))
    narrowed, subset = narrow_selection(selection, ["regression/b"])
    check("narrow keeps id", {"libc-test": ["regression/b"]}, narrowed)
    check("narrow marks subset", True, subset)
    try:
        narrow_selection(selection, ["nope"])
        check("narrow rejects unknown", "ValueError", "no exception")
    except ValueError:
        check("narrow rejects unknown", "ValueError", "ValueError")

    check("category llvm", "MultiSource/Benchmarks/Foo",
          category_of("llvm-ts", "MultiSource/Benchmarks/Foo/bar"))
    check("category libc", "functional", category_of("libc-test", "functional/a"))

    g = [dict(case="functional/a", klass="blocked", exit=None,
              reason="timeout after 3600s (SE, not a verdict)",
              gap=dict(capability="time budget", kind="timeout"),
              run_seconds=20.0),
         dict(case="regression/b", klass="pass", exit=0, reason="exit 0",
              gap=None, run_seconds=40.0),
         dict(case="MultiSource/Benchmarks/Foo/bar", klass="pass", exit=0,
              reason="exit 0", gap=None, run_seconds=14.0)]
    q = [dict(case="functional/a", klass="blocked", exit=None,
              reason="timeout after 3600s (blocked, not pass/fail)",
              gap=None, run_seconds=2.0),
         dict(case="regression/b", klass="pass", exit=0, reason="exit 0",
              gap=None, run_seconds=4.0),
         dict(case="MultiSource/Benchmarks/Foo/bar", klass="pass", exit=0,
              reason="exit 0", gap=None, run_seconds=2.0)]
    maps = [dict({("libc-test", "gem5-se"): {c["case"]: c for c in g},
                  ("libc-test", "qemu"): {c["case"]: c for c in q},
                  ("llvm-ts", "gem5-se"): {g[2]["case"]: g[2]},
                  ("llvm-ts", "qemu"): {q[2]["case"]: q[2]}})]
    rows, missing = collect_rows(selection, maps, 1)
    check("rows", 3, len(rows))
    check("no missing", [], missing)
    by_case = {row["case"]: row for row in rows}
    check("ratio 40/4", 10.0, by_case["regression/b"]["ratio"])
    check("ratio 14/2", 7.0, by_case["MultiSource/Benchmarks/Foo/bar"]["ratio"])
    check("gem5 timeout flag", True,
          by_case["functional/a"]["gem5_timeout"])
    check("qemu timeout flag", True,
          by_case["functional/a"]["qemu_timeout"])
    dist = ratio_summary(rows)
    check("distribution excludes truncated", 2,
          dist["cases_in_distribution"])
    check("distribution median", 8.5, dist["ratio"]["median"])
    check("distribution min", 7.0, dist["ratio"]["min"])
    check("distribution max", 10.0, dist["ratio"]["max"])

    # reachable FAIL path: drop one qemu measurement -> must be reported.
    rows2, missing2 = collect_rows(selection, maps, 1,
                                   inject="MultiSource/Benchmarks/Foo/bar")
    check("injection surfaces missing", 1, len(missing2))
    check("injection names engine", "qemu", missing2[0]["engine"])
    check("injection clears ratio", None,
          {row["case"]: row for row in rows2}[
              "MultiSource/Benchmarks/Foo/bar"]["ratio"])

    check("variance 10.0/10.4", 3.92, relative_range([10.0, 10.4]))
    check("variance 10/12", 18.18, relative_range([10.0, 12.0]))
    check("variance single sample", None, relative_range([10.0]))
    rep = repeatability([dict(variance_pct={"gem5-se": 4.0, "qemu": 1.0})], 5.0)
    check("repeatability comparable", True, rep["comparable"])
    rep2 = repeatability([dict(variance_pct={"gem5-se": 12.0, "qemu": 1.0})], 5.0)
    check("repeatability flagged", False, rep2["comparable"])

    cmd = driver_command("/repo", "libc-test", "gem5-se",
                         argparse.Namespace(jobs=48, gem5_timeout=3600,
                                            qemu_timeout=3600, gem5_bin=None,
                                            gem5_config=None, qemu_bin=None),
                         "/w", 1, ["functional/a", "regression/b"])
    check("libc filter anchored", "^(?:functional/a|regression/b)$",
          cmd[cmd.index("--filter") + 1])
    check("libc gem5 budget", "3600", cmd[cmd.index("--gem5-timeout") + 1])
    check("libc qemu budget", "3600", cmd[cmd.index("--timeout") + 1])
    cmd2 = driver_command("/repo", "llvm-ts", "qemu",
                          argparse.Namespace(jobs=48, gem5_timeout=3600,
                                             qemu_timeout=3600, gem5_bin=None,
                                             gem5_config=None, qemu_bin=None),
                          "/w", 1, ["MultiSource/Benchmarks/Foo/bar"])
    check("llvm only anchored", "^MultiSource/Benchmarks/Foo/bar$",
          cmd2[cmd2.index("--only") + 1])
    check("sanitize drops temp dir",
          "in /x: boom", sanitize("/tmp/opencode/t1/in /x: boom"))

    banner_dir = os.path.join(tmpdir, "banner")
    os.makedirs(os.path.join(banner_dir, "a"), exist_ok=True)
    with open(os.path.join(banner_dir, "a", "sim.log"), "w") as fh:
        fh.write("gem5 version 25.1.0.1\n"
                 "gem5 compiled Nov  9 2026 15:26:01\n")
    version, compiled = gem5_banner(banner_dir)
    check("gem5 banner version", "25.1.0.1", version)
    check("gem5 banner compiled", "Nov  9 2026 15:26:01", compiled)
    check("gem5 banner absent", (None, None),
          gem5_banner(os.path.join(tmpdir, "no-such-dir")))

    path_ok = _synthetic_driver(tmpdir, "ok.json", [
        dict(case="a", run_seconds=1.0), dict(case="b", run_seconds=2.0)],
        "qemu")
    check("resume sees complete JSON", True,
          driver_json_complete(path_ok, ["a", "b"]))
    check("resume sees uncovered case", False,
          driver_json_complete(path_ok, ["a", "c"]))
    path_bad = _synthetic_driver(tmpdir, "bad.json",
                                 [dict(case="a", run_seconds=None)], "qemu")
    check("resume rejects record without time", False,
          driver_json_complete(path_bad, ["a"]))

    report = build_report(
        argparse.Namespace(case_list=summary_path, jobs=48, repeats=1,
                           only=None),
        selection, rows, missing, ratio_summary(rows),
        repeatability(rows, 5.0),
        dict(host="h", cpu_model="c", nproc=64, jobs=48,
             engines=["qemu", "gem5-se"], gem5_timeout_seconds=3600,
             qemu_timeout_seconds=3600, gem5_binary="gem5.opt",
             gem5_md5="0" * 32, gem5_version="gem5 version t",
             qemu_binary="qemu-dadao", qemu_md5="1" * 32,
             qemu_version="qemu t", musl_head="abc", musl_dirty=False,
             loadavg=[0.0, 0.0, 0.0]))
    md = markdown(report)
    check("report ok", True, report["ok"])
    check("markdown has fingerprint", True, "## 执行环境指纹" in md)
    check("markdown has per-case table", True, "| suite | case |" in md)
    check("markdown no tmp path", False, "/tmp/opencode/" in md)
    report2 = build_report(
        argparse.Namespace(case_list=summary_path, jobs=48, repeats=1,
                           only=None),
        selection, rows2, missing2, ratio_summary(rows2),
        repeatability(rows2, 5.0), report["fingerprint"])
    check("missing makes ok false", False, report2["ok"])
    check("markdown lists missing", True, "## 缺失（FAIL）" in markdown(report2))

    # A measured 0.00 s (sub-5 ms guest) is not a missing measurement: the
    # ratio is undefined but the case still counts as measured.
    sel_zero = {"libc-test": ["functional/zero"]}
    zero_maps = [dict({
        ("libc-test", "gem5-se"): {"functional/zero": dict(
            case="functional/zero", klass="pass", exit=0, reason="exit 0",
            run_seconds=5.0)},
        ("libc-test", "qemu"): {"functional/zero": dict(
            case="functional/zero", klass="pass", exit=0, reason="exit 0",
            run_seconds=0.0)}})]
    rows_zero, missing_zero = collect_rows(sel_zero, zero_maps, 1)
    check("zero-qemu leaves ratio null", None, rows_zero[0]["ratio"])
    check("zero-qemu is flagged", True,
          bool(rows_zero[0].get("ratio_undefined")))
    report_zero = build_report(
        argparse.Namespace(case_list=summary_path, jobs=48, repeats=1,
                           only=None),
        sel_zero, rows_zero, missing_zero, ratio_summary(rows_zero),
        repeatability(rows_zero, 5.0), report["fingerprint"])
    check("zero-qemu still ok", True, report_zero["ok"])

    failed = 0
    for name, want, got in checks:
        passed = want == got
        failed += 0 if passed else 1
        print(f"self-test {'PASS' if passed else 'FAIL'} {name}: "
              f"expected={want!r} actual={got!r}")
    print(f"self-test: {len(checks) - failed}/{len(checks)} checks passed")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=f"{TASK}: gem5 SE vs qemu-user wall-clock ratio on the "
                    f"static long-tail cases")
    ap.add_argument("--repo-root", default=REPO_ROOT,
                    help="repository root the drivers resolve against and the "
                         "default artifact roots live under (default: this "
                         "script's repository).  A worktree without a built "
                         "toolchain must pass the repository that has one")
    ap.add_argument("--case-list", default=DEFAULT_CASE_LIST,
                    help="GEM5-021t summary JSON carrying timeout_recheck")
    ap.add_argument("--suites", default="libc-test,llvm-ts",
                    help="comma-separated suites to measure (default: the two "
                         "that carry still_blocked cases)")
    ap.add_argument("--only", action="append", default=None, metavar="CASE",
                    help="measure only this case id (repeatable; pilot).  The "
                         "id must be part of the recheck selection")
    ap.add_argument("--work-dir", required=True,
                    help="runtime directory for driver JSONs/logs")
    ap.add_argument("--json-out", default=None,
                    help="per-case + summary JSON (knowledge artifact); "
                         "required unless --self-test")
    ap.add_argument("--md-out", default=None,
                    help="human report (default: --json-out with .md)")
    ap.add_argument("--jobs", type=int, default=48,
                    help="cases in flight per engine round (same for both "
                         "engines; default 48)")
    ap.add_argument("--gem5-timeout", type=int, default=3600)
    ap.add_argument("--qemu-timeout", type=int, default=3600)
    ap.add_argument("--engines", default="qemu,gem5-se",
                    help="comma-separated engines to run (default both)")
    ap.add_argument("--repeats", type=int, default=1,
                    help="engine rounds per engine (repeatability; default 1)")
    ap.add_argument("--aggregate-only", action="store_true",
                    help="reuse the driver JSONs already in --work-dir")
    ap.add_argument("--resume", action="store_true",
                    help="skip a (suite, engine, repeat) round whose JSON in "
                         "--work-dir already covers every selected case (a "
                         "long run can be continued after an interruption)")
    ap.add_argument("--gem5-bin", default=None)
    ap.add_argument("--gem5-config", default=None)
    ap.add_argument("--qemu-bin", default=None)
    ap.add_argument("--variance-limit", type=float, default=5.0,
                    help="repeatability limit in percent (default 5)")
    ap.add_argument("--inject-missing-qemu-seconds", default=None,
                    metavar="CASE",
                    help="evidence only: drop that case's qemu measurement so "
                         "the missing-measurement FAIL path is reachable")
    ap.add_argument("--self-test", action="store_true",
                    help="check selection/aggregation/statistics on synthetic "
                         "records (no engine, writes only under --work-dir)")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo_root)
    work_dir = abspath(repo, args.work_dir)
    os.makedirs(work_dir, exist_ok=True)

    if args.self_test:
        return self_test(work_dir)
    if not args.json_out:
        sys.stderr.write("ERROR: --json-out is required\n")
        return 2

    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    unknown = [s for s in suites if s not in SUITES]
    if unknown:
        sys.stderr.write(f"ERROR: unknown suite(s) {unknown}\n")
        return 2
    if args.repeats < 1:
        sys.stderr.write("ERROR: --repeats must be >= 1\n")
        return 2
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    unknown = [e for e in engines if e not in ENGINES]
    if unknown:
        sys.stderr.write(f"ERROR: unknown engine(s) {unknown}\n")
        return 2
    args.engines = engines

    try:
        selection = load_selection(abspath(repo, args.case_list), suites)
        selection, _ = narrow_selection(selection, args.only)
    except (OSError, ValueError, KeyError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    print(f"[plan] selection: " + ", ".join(
        f"{suite}={len(ids)}" for suite, ids in selection.items()) +
        f"; engines={engines}; jobs={args.jobs}; repeats={args.repeats}; "
        f"budgets gem5={args.gem5_timeout}s qemu={args.qemu_timeout}s",
        flush=True)

    driver_rc = {}
    skipped = []
    if not args.aggregate_only:
        for rep in range(1, args.repeats + 1):
            for suite, ids in selection.items():
                for engine in engines:
                    path = os.path.join(
                        work_dir, f"{suite}-{engine}-r{rep}.json")
                    if args.resume and driver_json_complete(path, ids):
                        print(f"[skip] {suite}/{engine} rep={rep}: complete "
                              f"JSON reused", flush=True)
                        skipped.append(f"{suite}/{engine}/r{rep}")
                        continue
                    rc, _ = run_driver(repo, suite, engine, args, work_dir,
                                       rep, ids)
                    driver_rc[f"{suite}/{engine}/r{rep}"] = rc

    per_rep = []
    for rep in range(1, args.repeats + 1):
        maps = {}
        for suite in selection:
            for engine in engines:
                path = os.path.join(work_dir, f"{suite}-{engine}-r{rep}.json")
                if not os.path.isfile(path):
                    sys.stderr.write(f"ERROR: missing driver JSON: {path}\n")
                    return 2
                _, cases = load_driver(path)
                maps[(suite, engine)] = cases
        per_rep.append(maps)

    rows, missing = collect_rows(selection, per_rep, args.repeats,
                                 inject=args.inject_missing_qemu_seconds)
    summary = ratio_summary(rows)
    repeat = repeatability(rows, args.variance_limit)
    prints = fingerprint(repo, args, work_dir)
    report = build_report(args, selection, rows, missing, summary, repeat,
                          prints)
    report["driver_rc"] = driver_rc
    report["reused_rounds"] = skipped

    json_out = abspath(repo, args.json_out)
    md_out = abspath(repo, args.md_out) if args.md_out else \
        os.path.splitext(json_out)[0] + ".md"
    for path in (json_out, md_out):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(json_out, "w") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    with open(md_out, "w") as fh:
        fh.write(markdown(report))

    stat = summary["ratio"]
    print(f"[done] cases={len(rows)} missing={len(missing)} "
          f"ratio(n={stat['n']}) min={stat['min']} median={stat['median']} "
          f"p90={stat['p90']} max={stat['max']} "
          f"repeatable={repeat['comparable']}")
    print(f"JSON: {json_out}")
    print(f"Markdown: {md_out}")
    if missing:
        sys.stderr.write(
            f"ERROR: {len(missing)} measurement(s) missing -- see 'missing' "
            f"in the JSON (never silently skipped)\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
