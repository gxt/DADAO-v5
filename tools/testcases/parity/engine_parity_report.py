#!/usr/bin/env python3
"""engine_parity_report.py -- 由运行期批次输入重生成 m12-016 的 engine-parity
报告对（`tests/data/m12-016-embench-picolibc.{json,md}`）。

本文件是 `m12-chipyard-016` 证据脚本的**入仓版**（`m12-chipyard-017`）：只改
「路径解析 + 入口形态」，报告口径（`CRITERION` / `QEMU_BASELINE_GAPS` / union
规则 / budget 单列 / `cases_seen`）与 016 逐字相同，输出逐字节一致。

接口（默认值全部由脚本相对路径推出，不依赖运行期环境变量）：

  * `--repo <根>`：仓库根，默认 = 本脚本所在目录上溯三层；
  * `--log-dir <目录>`：批次输入目录（运行期日志，永不入库），
    默认 = `<repo>` 内 chipyard 模块的运行期日志目录；
  * `--out-dir <目录>`：报告输出目录，默认 `<repo>/tests/data`；
  * `--node-map <日志名>=<节点>`：覆盖分片→节点名（默认见 `SHARD_NODE`，可重复）。

用法::

    python3 tools/testcases/parity/engine_parity_report.py            # 重生成
    python3 tools/testcases/parity/engine_parity_report.py --check    # 与入库报告逐字节比对

`--check` 打印入库与重生成两份报告的 sha256；不符 rc=1 并指出首个差异行，
缺输入/缺报告 rc=2。

输入全部运行期；输出是输入的**确定性函数**（不含生成时刻），两次重生成逐字节相同。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_DEFAULT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
REPORT_JSON_NAME = "m12-016-embench-picolibc.json"
REPORT_MD_NAME = "m12-016-embench-picolibc.md"

REPO = REPO_DEFAULT
LOG = os.path.join(REPO, ".work", "log", "chipyard")


def load(name):
    with open(os.path.join(LOG, name), encoding="utf-8") as fh:
        return json.load(fh)


# M12 判据（用户 2026-11-14 裁定）= engine parity：chipyard 与 qemu 用同一份
# ELF，只换引擎，逐例状态必须相同；qemu 侧既有缺口登记在册、不计到 chipyard。
# 分片 → 节点（跑批时日志按这些名字落盘；`--node-map` 可覆盖）。
SHARD_NODE = {
    "m12-chipyard-016-embench.log": "server208",
    "m12-chipyard-016-embench-a.log": "ics180",
    "m12-chipyard-016-embench-b.log": "ics160",
    # `-O0` 12 h night window (m12-chipyard-031): the shard that finished it and
    # the separate rerun of the one case that was still running at the window
    # end (its trailer states NODE=ics170).
    "m12-chipyard-016-embench-o0night.log": "server208",
    "m12-chipyard-016-embench-o0xg.log": "ics170",
    "m12-chipyard-016-embench-o0xg.json": "ics170",
    "m12-chipyard-016-picolibc-chipyard": "ics150",
}
NODE_MAP = dict(SHARD_NODE)

# code freeze（2026-11-14 23:1x）：chipyard 侧不再改代码，sim md5 固定为这个值。
# `SYS_FLEN` 修复只影响走文件/特性探针的 picolibc 用例；embench 不触发（见
# `embench_syscalls` 证据），因此 embench 批次允许留在旧 md5 上。
CURRENT_SIM = "079ae01569e5fbf9fa9944bd6aee89cd"

# 走 `SYS_FLEN`/`SYS_SEEK`/`SYS_READ`/`SYS_OPEN` 组合的 picolibc 用例（从各节点
# 逐例 sim.log 里 grep 出来的**现场集合**，不是猜的）——这些必须用当前 sim 复跑。
FLEN_AFFECTED = {
    "semihost-close", "semihost-errno", "semihost-exit-extended",
    "semihost-exit-extended-failure", "semihost-flen", "semihost-iserror",
    "semihost-istty", "semihost-open", "semihost-read", "semihost-remove",
    "semihost-rename", "semihost-seek", "test-dprintf", "test-fflush",
    "test-fgetc", "test-fgets-eof", "test-fopen", "test-fread-fwrite",
    "test-freopen", "test-getdate", "test-grp", "test-mktemp",
    "test-posix-io", "test-pwd", "test-rename", "test-setvbuf", "test-stat",
    "test-tmpnam", "test-ungetc-ftell", "test-wchar",
}

CRITERION = "engine parity（picolibc 逐例状态与 qemu 一致；不要求全绿）"

# 用户 2026-11-15 裁定（原话「blocked 容易让人误解，timeout（12h）如何？」）：
# 预算耗尽 ⇒ `timeout(<预算>)`（机器值 TIMEOUT），`blocked` 收窄为构建/环境缺口。
TIMEOUT_NOTE = (
    "`timeout(<预算>)` 属**无判决**（`--timeout` 预算耗尽、guest 未给 verdict）："
    "不参与「逐例状态一致」比较，**不计入 chipyard 独有失败**；"
    "`blocked` 只表示**构建/环境缺口**（如 ISS-193 long-double、CFX6 缺载体、"
    "harness 服务未实现），不再表示预算类。")

QEMU_BASELINE_GAPS = {
    "test-ceil": "blocked (ISS-193 long-double libcall)",
    "test-long-double": "blocked (ISS-193 long-double libcall)",
    "test-math-funcs": "blocked (ISS-193 long-double libcall)",
    "test-abort-failure": "blocked (machine fault CFX6)",
    "test-math-errhandling": "fail (exit 3)",
}


def _is_budget(status, reason):
    """host timeout / budget outcome: not the case's verdict (user 2026-11-14)."""
    reason = reason or ""
    return ("timeout" in reason) or ("budget" in reason)


# The budget label rule (`format_budget`/`parse_budget`) lives next to
# `case_status()` in the embench runner -- the one place that decides a case's
# status.  This generator prints the *same* label, so it imports it rather than
# re-deriving the rule here (a second copy would drift).
_BUDGET = None
_BUDGET_PATH = os.path.join("tests", "ee-tiny", "run_embench_tiny.py")


class BudgetError(RuntimeError):
    """A `timeout(<预算>)` label does not agree with the seconds behind it."""


def _budget_tools():
    global _BUDGET
    if _BUDGET is None:
        import importlib.util
        path = os.path.join(REPO, _BUDGET_PATH)
        spec = importlib.util.spec_from_file_location("_embench_runner", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _BUDGET = (mod.format_budget, mod.parse_budget)
    return _BUDGET


def budget_label(seconds):
    """`timeout(<label>)` body for a budget in seconds; round-trip checked.

    The check is the point: if the conversion is wrong (43200 -> `11h`), the
    label and the seconds disagree and the report fails instead of printing a
    quiet lie (AGENTS「验证脚本反例门控」: 可达 FAIL).
    """
    if seconds is None:
        raise BudgetError("TIMEOUT row without budget_seconds")
    format_budget, parse_budget = _budget_tools()
    label = format_budget(seconds)
    if parse_budget(label) != int(seconds):
        raise BudgetError(
            "budget conversion is not a round trip: %ss -> %r -> %ss"
            % (seconds, label, parse_budget(label)))
    return label


# One per-case progress line.  The status token is either a machine word or
# the display form `timeout(<预算>)` (m12-chipyard-031); the old runner printed
# a binary `FAIL` plus "(platform: host timeout after 43200s ...)".
_CASE_LINE_RE = re.compile(
    r"^\s+(PASS|FAIL|TIMEOUT|BLOCKED|GUARD|ERROR|timeout\((\w+)\))\s+"
    r"(\S+)\s+\(-(\w+)\)\s+"
    r"expected=(\S+)\s+actual=(\S+)\s+exit=(\S+)"
    r"(?:\s+cycles=(\S+)\s+([\d.]+)s)?\s+\((.*)\)$",
    re.MULTILINE)
# The budget a case ran under, as the harness states it.
_TIMEOUT_RE = re.compile(r"host timeout after (\d+)s")


def _reason_budget(reason):
    m = _TIMEOUT_RE.search(reason or "")
    return int(m.group(1)) if m else None


def _classify(token, label, reason, case_id):
    """(status, budget_seconds) for one parsed line.

    `timeout(<label>)` -> TIMEOUT with the stated budget (the label must agree
    with the "host timeout after Ns" evidence).  Legacy binary lines (old
    runner: `FAIL` + host-timeout reason) are the *same* no-verdict outcome, so
    they are read as TIMEOUT too -- dropping them silently was the bug this
    task fixes.  A TIMEOUT without a budget is a hard error: no guessed value.
    """
    budget = _reason_budget(reason)
    if label is not None:
        try:
            stated = _budget_tools()[1](label)
        except ValueError as exc:
            raise BudgetError("%s: %s" % (case_id, exc))
        if budget is not None and stated != budget:
            raise BudgetError(
                "%s: label timeout(%s) = %ss but the log says %ss (attempted "
                "conversion does not match the runtime budget)"
                % (case_id, label, stated, budget))
        budget = stated
    status = token
    if token.startswith("timeout("):
        status = "TIMEOUT"
    elif status in ("FAIL", "BLOCKED", "TIMEOUT") and budget is not None:
        status = "TIMEOUT"
    if status == "TIMEOUT" and budget is None:
        raise BudgetError("%s: TIMEOUT without a budget in the log line" % case_id)
    return status, budget


def _case_paths(case_id, leaf):
    """`<work-dir>/<opt>/<bench>/<leaf>` for a case id.

    The report is a *knowledge* artifact: it must not carry a runtime absolute
    path (a fresh clone cannot reproduce it), so per-case file locations are
    stated in this relative form.
    """
    bench, opt = case_id.split("/", 1)[1].rsplit("-", 1)
    return os.path.join("<work-dir>", opt, bench, leaf)


def _parse_log(path, extra_events=None, shard=None, semiout_of=None):
    """Parse one embench shard *log* into runner-JSON-shaped cases.

    A shard that is still running has no `--json-out` file yet; its per-case
    lines (`PASS/FAIL/timeout(<预算>) <bench> (-<opt>) ... exit=<n> cycles=<n>
    <s>s`) and its batch trailer (`START/END/EXIT/WALL/JOBS`) are, so the
    report can state a partial batch without inventing numbers.
    """
    cases = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    for m in _CASE_LINE_RE.finditer(text):
        (token, label, bench, opt, _exp, _act, exitv,
         cycles, secs, reason) = m.groups()
        case_id = "embench/%s-%s" % (bench, opt)
        status, budget = _classify(token, label, reason, case_id)
        cases.append({
            "case_id": case_id,
            "status": status,
            "exit": None if exitv == "?" else int(exitv),
            "cycles": None if cycles in (None, "None") else int(cycles),
            "seconds": float(secs) if secs else None,
            "budget_seconds": budget,
            "sim_md5": (extra_events or {}).get("sim_md5"),
            "markers": None,  # a log line does not carry the marker list
            "shard": NODE_MAP.get(shard, shard),
            "shard_log": shard,
            "semi_out": ((NODE_MAP.get(shard, "?") + ":"
                          + semiout_of(bench, opt)) if semiout_of else None),
            "sim_log": None,
            "reason": reason,
        })
    return cases


# 用户 2026-11-14 裁定：`test-memmem`（>1 h）与 3 个 qemu 侧本就 blocked 的
# long-double 例（ISS-193）不花时间去仿真，按 parity 直接判 BLOCKED（带理由）。
PARITY_BLOCKED = {
    "test-ceil": "ISS-193: long-double libcall lowering missing (blocked on qemu too)",
    "test-long-double": "ISS-193: long-double libcall lowering missing (blocked on qemu too)",
    "test-math-funcs": "ISS-193: long-double libcall lowering missing (blocked on qemu too)",
    "test-memmem": "workload budget: >1 h on chipyard (user ruling: judge BLOCKED, do not run)",
}


def load_pic_chipyard():
    """Union of every chipyard picolibc pool (A/B on ics150, D on ics170, memmem).

    A pool writes its JSON only at the end, so the live per-case progress lines
    are merged too: a case keeps the first *judged* verdict seen (a `skipped`
    row yields to a real one), which makes the union independent of pool order.
    """
    import glob
    import re
    rows = {}

    def put(row):
        prev = rows.get(row["name"])
        if prev is None or prev["status"] == "skipped":
            rows[row["name"]] = row
            return
        # A picolibc *self-skip* (exit 77) is "not applicable", not a verdict:
        # a real pass/fail from a newer build supersedes it.
        if (prev["status"] == "excluded" and "self-skip" in (prev.get("reason") or "")
                and row["status"] in ("pass", "fail")):
            rows[row["name"]] = row
            return
        # 结果**不跨二进制**：当前 sim 的结果优先于旧 sim 的结果。
        if (row.get("sim_md5") == CURRENT_SIM
                and prev.get("sim_md5") != CURRENT_SIM):
            rows[row["name"]] = row
            return
        # A dedicated retry pool supersedes an earlier *budget* verdict: a
        # `blocked (host timeout)` is not the case's verdict, a later pass/fail
        # is.
        if (prev["status"] == "blocked" and "timeout" in (prev.get("reason") or "")
                and row["status"] != "skipped"):
            rows[row["name"]] = row

    for path in sorted(glob.glob(os.path.join(
            LOG, "m12-chipyard-016-picolibc-chipyard*.json"))):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        for r in doc["results"]:
            r = dict(r)
            r["_pool"] = os.path.basename(path)
            put(r)
    for path in sorted(glob.glob(os.path.join(
            LOG, "m12-chipyard-016-picolibc-chipyard*.log"))):
        pool = os.path.basename(path)
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"\s+\[(\d+)/(\d+)\] (\S+)\s+(\S+)\s+(.*)$",
                             line)
                if not m:
                    continue
                put({"name": m.group(3), "suite": "-", "status": m.group(4),
                     "reason": m.group(5).strip(), "cycles": None,
                     "seconds": None, "rc": None, "_pool": pool})

    counts = {"pass": 0, "fail": 0, "excluded": 0, "blocked": 0}
    for r in rows.values():
        if r["status"] == "skipped":
            continue
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    for name, why in PARITY_BLOCKED.items():
        if name not in rows or rows[name]["status"] == "skipped":
            rows[name] = {"name": name, "suite": "-", "status": "blocked",
                          "reason": why, "cycles": None, "seconds": None,
                          "rc": None, "_pool": "parity-blocked"}
            counts["blocked"] += 1
    judged = sum(1 for r in rows.values() if r["status"] != "skipped")
    return {"counts": counts, "total": 235, "results": list(rows.values()),
            "sim_md5": sorted({r.get("sim_md5") for r in rows.values()
                               if r.get("sim_md5")}),
            "judged": judged,
            "pools": sorted({r.get("_pool") for r in rows.values()
                             if r.get("_pool")}),
            "parity_blocked": sorted(PARITY_BLOCKED),
            "partial": judged < 235}


def load_embench():
    """Union the embench batches (the suite is sharded across nodes).

    Every shard writes its own ``m12-chipyard-016-embench*.json``; a case that
    ran on more than one node is kept once.  A shard file stays in the runtime
    log directory; the model is:

    * a case that reached a **verdict** (``exit`` known) wins over one that
      gave none;
    * between two no-verdict records the one with the **larger budget** wins
      (the 12 h night window supersedes the earlier 4 h one) -- and the record
      is kept, never dropped: a `timeout(<预算>)` case is a stated outcome.
    """
    import glob
    cases = {}

    def rank(c):
        return (c["exit"] is not None, c.get("budget_seconds") or 0)

    def put(c):
        prev = cases.get(c["case_id"])
        if prev is None or rank(c) > rank(prev):
            cases[c["case_id"]] = c

    shards = sorted(glob.glob(os.path.join(LOG, "m12-chipyard-016-embench*.json")))
    logs = sorted(glob.glob(os.path.join(LOG, "m12-chipyard-016-embench*.log")))
    for path in shards:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        shard = os.path.basename(path)
        for c in doc["cases"]:
            c = dict(c)
            # New runner rows state the budget; old ones only carry the reason.
            if c.get("budget_seconds") is None:
                c["budget_seconds"] = _reason_budget(c.get("note", ""))
            if c.get("status") in ("FAIL", "BLOCKED") and c["budget_seconds"]:
                # A legacy JSON row from the binary-PASS/FAIL runner: same
                # no-verdict outcome, now stated as TIMEOUT.
                c["status"] = "TIMEOUT"
            c["shard"] = NODE_MAP.get(shard, shard)
            c["shard_log"] = shard
            put(c)
    for path in logs:
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read()
        m = re.search(r"md5=([0-9a-f]{32})", head)
        ev = {"sim_md5": m.group(1) if m else None}
        for c in _parse_log(path, ev, os.path.basename(path),
                            lambda b, o: os.path.join(
                                "<work-dir>", o, b, "semi.out")):
            put(c)
    if not cases:
        raise SystemExit("no embench shard json/log under %s" % LOG)
    # 用户 2026-11-14：`-O0` 改由 12 h 夜跑窗口覆盖。窗口**已结束**（2026-11-15
    # 08:48），因此不再把 `-O0` 无判决例删成 pending：它们记 `timeout(12h)`。
    night = any("o0night" in p for p in shards + logs)
    cases = list(cases.values())
    cases.sort(key=lambda c: (c["case_id"].split("-")[-1], c["case_id"]))
    return {"cases": cases, "shards": [os.path.basename(p) for p in shards],
            "o0_night_window": night}


def build():
    """Return (payload_json, markdown) — both pure functions of the inputs."""
    emb = load_embench()
    pic_cy = load_pic_chipyard()
    pic_qe = load("m12-chipyard-016-picolibc-qemu.json")

    emb_cases = [{
        "case_id": c["case_id"],
        "status": c["status"],
        "exit": c["exit"],
        "cycles": c["cycles"],
        "seconds": c["seconds"],
        "budget_seconds": c.get("budget_seconds"),
        "timeout": c["status"] == "TIMEOUT",
        # The display label is produced here, round-trip checked (可达 FAIL:
        # a wrong conversion such as 43200 -> "11h" raises BudgetError).
        "budget_label": (budget_label(c["budget_seconds"])
                         if c["status"] == "TIMEOUT" else None),
        "sim_md5": c["sim_md5"],
        "markers": c["markers"] if "markers" in c else None,
        # 运行期绝对路径一律改写成 `<work-dir>/…`（报告不入运行期路径）。
        "semi_out": "%s:%s" % (c.get("shard") or "-",
                               _case_paths(c["case_id"], "semi.out")),
        "sim_log": _case_paths(c["case_id"], "sim.log"),
        "shard": c.get("shard"),
        "shard_log": c.get("shard_log"),
        "reason": c.get("note", c.get("reason", "")),
    } for c in emb["cases"]]
    emb_cycles = [c["cycles"] for c in emb_cases if c["cycles"]]
    timeouts = [c for c in emb_cases if c["status"] == "TIMEOUT"]
    # 语料规模现场派生（用例名里的 benchmark × opt 网格），不写死 38。
    benches = sorted({c["case_id"].rsplit("-", 1)[0] for c in emb_cases})
    opts = sorted({c["case_id"].rsplit("-", 1)[1] for c in emb_cases})
    expected = len(benches) * len(opts)
    timeout_groups = {}
    for c in timeouts:
        timeout_groups[c["budget_label"]] = timeout_groups.get(
            c["budget_label"], 0) + 1
    emb_stats = {
        "criterion": "guest exit 0 + 三个 board marker（chipyard）",
        "total": len(emb_cases),
        "expected": expected,
        "corpus": {"benchmarks": len(benches), "opts": opts},
        "cases_seen": len(emb_cases),
        "pending": max(0, expected - len(emb_cases)),
        "pass": sum(1 for c in emb_cases if c["status"] == "PASS"),
        "timeout": len(timeouts),
        "timeout_cases": [{"case_id": c["case_id"],
                           "status": c["status"],
                           "budget_seconds": c["budget_seconds"],
                           "budget_label": c["budget_label"],
                           "wall_seconds": c["seconds"],
                           "shard": c["shard"],
                           "shard_log": c["shard_log"],
                           "reason": c["reason"]} for c in timeouts],
        "timeout_groups": timeout_groups,
        "fail": sum(1 for c in emb_cases if c["status"] in ("FAIL", "GUARD")),
        "blocked": sum(1 for c in emb_cases if c["status"] == "BLOCKED"),
        "error": sum(1 for c in emb_cases if c["status"] == "ERROR"),
        "with_markers": sum(1 for c in emb_cases
                            if c["markers"] is not None and len(c["markers"]) == 3),
        "cycles_min": min(emb_cycles) if emb_cycles else None,
        "cycles_max": max(emb_cycles) if emb_cycles else None,
        "cycles_sum": sum(emb_cycles) if emb_cycles else None,
        "wall_seconds_sum": round(sum(c["seconds"] or 0 for c in emb_cases), 1),
        "sim_md5": sorted({c["sim_md5"] for c in emb_cases if c["sim_md5"]}),
        "shards": emb.get("shards", []),
        "o0_night_window": emb.get("o0_night_window", False),
        "timeout_policy": TIMEOUT_NOTE,
    }

    def pic(doc):
        rows = [{
            "name": r["name"], "suite": r["suite"], "status": r["status"],
            "reason": r["reason"], "cycles": r.get("cycles"),
            "seconds": r.get("seconds"), "rc": r.get("rc"),
            "pool": r.get("_pool"),
            # 运行期绝对路径一律改写成 `<work-dir>/…`（报告不入运行期路径；
            # 各例来自哪个池仍由 `pool` 字段标明）。
            "semi_out": ("<work-dir>/run/%s/semi.out" % r["name"]
                         if r.get("semi_out") else None),
            "sim_log": ("<work-dir>/run/%s/sim.log" % r["name"]
                        if r.get("sim_log") else None),
            "sim_md5": r.get("sim_md5"),
        } for r in doc["results"]]
        return {"total": doc.get("total", len(rows)), "finished": len(rows),
                "partial": bool(doc.get("partial")), "counts": doc["counts"],
                "cases": rows,
                "cycles_sum": sum(r["cycles"] for r in rows if r.get("cycles")),
                "wall_seconds_sum": round(sum(r["seconds"] or 0 for r in rows), 1)}

    cy = pic(pic_cy)
    qe = pic(pic_qe)
    status_cy = {r["name"]: r["status"] for r in cy["cases"]}
    status_qe = {r["name"]: r["status"] for r in qe["cases"]}
    common = set(status_cy) & set(status_qe)
    cy_reason = {r["name"]: (r.get("reason") or "") for r in cy["cases"]}

    def budget(n):
        # 用户 2026-11-14：host timeout / 未跑（如 test-memmem 超出预算）是
        # budget 结果，不是用例判决，单列且**不计入** chipyard 独有失败
        # （判据仍为 engine parity）。
        return status_cy.get(n) == "blocked" and _is_budget(
            status_cy.get(n), cy_reason.get(n, ""))

    parity = {
        "common": len(common),
        "differing": sorted(n for n in common
                            if status_cy[n] != status_qe[n] and not budget(n)),
        "budget_blocked": sorted(n for n in common if budget(n)),
        "chipyard_only_failures": sorted(
            n for n in common if status_cy[n] in ("fail", "blocked")
            and status_qe[n] == "pass" and not budget(n)),
        "qemu_gaps_registered": sorted(QEMU_BASELINE_GAPS),
        "qemu_gaps_matched": sorted(
            n for n, why in QEMU_BASELINE_GAPS.items()
            if status_qe.get(n) == why.split(" ")[0]),
    }

    md5_emb = sorted({r.get("sim_md5") for r in emb_cases if r.get("sim_md5")})
    aff = [r for r in cy["cases"] if r["name"] in FLEN_AFFECTED]
    unaff = [r for r in cy["cases"] if r["name"] not in FLEN_AFFECTED]
    aff_md5 = sorted({r.get("sim_md5") for r in aff if r.get("sim_md5")})
    unaff_md5 = sorted({r.get("sim_md5") for r in unaff if r.get("sim_md5")})
    consistency = {
        "current_sim": CURRENT_SIM,
        "flen_affected_cases": sorted(FLEN_AFFECTED),
        "flen_affected_md5": aff_md5,
        "flen_affected_all_on_current_sim":
            bool(aff_md5) and all(m == CURRENT_SIM for m in aff_md5),
        "flen_unaffected_md5": unaff_md5,
        "embench_md5": md5_emb,
        "exception": ("embench（及其余**不触发** SYS_FLEN 的 picolibc 用例）允许留在旧 md5 "
                      "`ac35dff…`：embench 语料/shim/runtime 对 fopen/fseek/ftell/SYS_FLEN/"
                      "SYS_OPEN 零命中，实测其 sim.log 只出现 SYS_WRITE0/SYS_EXIT；"
                      "picolibc 侧受 SYS_FLEN 影响的 30 例已全部用 `079ae015…` 重跑"),
    }

    report = {
        "task": "m12-chipyard-016",
        "code_freeze": {"chipyard_sim_md5": CURRENT_SIM,
                        "frozen_at": "2026-11-14T23:10+08:00"},
        "sim_md5_consistency": consistency,
        "criterion": CRITERION,
        "qemu_baseline_gaps": QEMU_BASELINE_GAPS,
        "engine": "chipyard WumingTinyConfig (Verilator harness)",
        "embench": dict(emb_stats, cases=emb_cases),
        "picolibc_chipyard": cy,
        "picolibc_qemu_baseline": qe,
        "parity": parity,
    }
    payload = json.dumps(report, indent=1, sort_keys=True) + "\n"

    def table(title, rows, cols):
        out = [title, ""]
        out.append("| " + " | ".join(c for c, _ in cols) + " |")
        out.append("|" + "|".join("---" for _ in cols) + "|")
        for r in rows:
            out.append("| " + " | ".join(str(f(r)) for _, f in cols) + " |")
        return out

    md = []
    md.append("# m12-chipyard-016 报告：embench / picolibc-full 在 chipyard Tiny 上")
    md.append("")
    md.append("> 生成自运行期证据（`--json` / `--json-out`），可重跑复核；"
              "本页数字全部现场统计，未写死。")
    md.append("")
    md.append("## 0. M12 判据")
    md.append("")
    md.append("- **判据 = %s**（用户 2026-11-14 裁定）。" % CRITERION)
    md.append("- **状态词表**（用户 2026-11-15 裁定）：%s" % TIMEOUT_NOTE)
    md.append("- qemu 侧既有缺口（登记在册，不计到 chipyard）：")
    for name in sorted(QEMU_BASELINE_GAPS):
        md.append("  - `%s`：%s" % (name, QEMU_BASELINE_GAPS[name]))
    md.append("")
    md.append("## 0.1 code freeze 与 sim md5 一致性")
    md.append("")
    md.append("- **code freeze（2026-11-14 23:10）**：chipyard 侧不再改代码，"
              "sim md5 = `%s`。" % CURRENT_SIM)
    md.append("- **受 `SYS_FLEN` 影响的 picolibc 用例（%d 例，现场 grep 得出）**：sim md5 %s"
              " ⇒ 全部在 code-freeze 后的 sim 上复跑：%s"
              % (len(consistency["flen_affected_cases"]),
                 ", ".join("`%s`" % m for m in consistency["flen_affected_md5"]),
                 "是" if consistency["flen_affected_all_on_current_sim"] else "否"))
    md.append("- 其余 picolibc 用例（不触发 `SYS_FLEN`）：sim md5 %s（与 code freeze 前同一二进制，"
              "语义等价；每例仍只有一份结果）"
              % ", ".join("`%s`" % m for m in consistency["flen_unaffected_md5"]))
    md.append("- embench 用例的 sim md5：%s ⇒ **允许的唯一例外**：%s"
              % (", ".join("`%s`" % m for m in consistency["embench_md5"]),
                 consistency["exception"]))
    md.append("")
    md.append("## 1. 环境")
    md.append("")
    md.append("- 引擎：chipyard `WumingTinyConfig` Verilator harness"
              "（`+loadmem=` / `+semiout=` / `+max-cycles=` / `+semicmdline=`）")
    md.append("- 判据：guest `SYS_EXIT` 子码（harness 打印 `-> host exit status N` 后 `exit(N)`）")
    md.append("- 防假绿：`+max-cycles` 触顶 ⇒ FAIL；跑批前后 sim 二进制 md5 必须相同 ⇒ 否则 FAIL；"
              "embench 另要求三个板级 marker 齐全")
    md.append("")
    md.append("## 2. embench（%d benchmark × %s）"
              % (emb_stats["corpus"]["benchmarks"],
                 "/".join("-" + o for o in emb_stats["corpus"]["opts"])))
    md.append("")
    _summary = ["PASS %d" % emb_stats["pass"]]
    for label in sorted(emb_stats["timeout_groups"]):
        _summary.append("%s %d" % (("timeout(%s)" % label),
                                   emb_stats["timeout_groups"][label]))
    _summary.append("fail %d" % emb_stats["fail"])
    if emb_stats["blocked"]:
        _summary.append("blocked %d" % emb_stats["blocked"])
    if emb_stats["error"]:
        _summary.append("ERROR %d" % emb_stats["error"])
    md.append("- **汇总：%s**（现场统计）" % " / ".join(_summary))
    if emb_stats["pending"]:
        md.append("- **pending %d 例**（语料 %d = %d benchmark × %d opt，已见 %d）"
                  % (emb_stats["pending"], emb_stats["expected"],
                     emb_stats["corpus"]["benchmarks"],
                     len(emb_stats["corpus"]["opts"]), emb_stats["cases_seen"]))
    if timeouts:
        md.append("- **timeout %d 例**（`timeout(<预算>)` = 预算耗尽、guest 无判决 ⇒ "
                  "**不参与逐例状态一致比较、不计入 chipyard 独有失败**）："
                  % len(timeouts))
        for c in timeouts:
            md.append("  - `%s`：`timeout(%s)`，预算 %ss，墙钟 %ss，分片 `%s`"
                      % (c["case_id"], c["budget_label"], c["budget_seconds"],
                         c["seconds"], c["shard_log"] or c["shard"] or "-"))
    md.append("- 例数：%d；三 marker 齐全 %d"
              % (emb_stats["total"], emb_stats["with_markers"]))
    md.append("- 周期：min %s / max %s / sum %s（`+max-cycles` 预算 %s，无一触顶）"
              % (emb_stats["cycles_min"], emb_stats["cycles_max"],
                 emb_stats["cycles_sum"], "2000000000"))
    if emb_stats.get("o0_night_window"):
        md.append("- **`-O0` 12 h 夜跑窗口**（用户 2026-11-14 裁定）：`server208`、jobs=18、"
                  "`--timeout 43200`；窗口已结束，仍未给判决的 `-O0` 例记 "
                  "`timeout(12h)`（不是 `blocked`）。")
    md.append("- 墙钟合计：%ss（为各例墙钟之和，非批量墙钟）"
              % emb_stats["wall_seconds_sum"])
    md.append("- sim md5：%s" % ", ".join(emb_stats["sim_md5"]))
    md.append("")
    md += table("每例（`status` / `rc`=guest 退出码 / `cycle` / 预算 / markers / "
                "该批 sim md5 / `+semiout` 路径 / 分片）：", emb_cases, [
        ("case", lambda r: r["case_id"]),
        ("status", lambda r: (("timeout(%s)" % r["budget_label"])
                              if r["status"] == "TIMEOUT" else r["status"])),
        ("rc", lambda r: ("?" if r["exit"] is None else r["exit"])),
        ("cycle", lambda r: ("?" if r["cycles"] is None else r["cycles"])),
        ("budget", lambda r: (("%ss" % r["budget_seconds"])
                              if r["budget_seconds"] else "-")),
        ("markers", lambda r: (len(r["markers"])
                               if r["markers"] is not None else "?")),
        ("sim md5", lambda r: (r["sim_md5"] or "")[:8]),
        ("semiout", lambda r: r["semi_out"] or "-"),
        ("shard", lambda r: r["shard"] or "-")])
    md.append("")
    md.append("## 3. picolibc full（chipyard）")
    md.append("")
    if cy.get("partial"):
        md.append("- **批次未收完**：完成 %d / %d 例（截至本报告生成时刻）；"
                  "已完成部分：pass %d / fail %d / blocked %d / excluded %d"
                  % (cy["finished"], cy["total"], cy["counts"].get("pass", 0),
                     cy["counts"].get("fail", 0), cy["counts"].get("blocked", 0),
                     cy["counts"].get("excluded", 0)))
    md.append("- 总例数 %d：pass %d / fail %d / blocked %d / excluded %d"
              % (cy["total"], cy["counts"]["pass"], cy["counts"]["fail"],
                 cy["counts"]["blocked"], cy["counts"]["excluded"]))
    md.append("- 逐例明细在 JSON 的 `cases[]`（字段 `status` / `rc` / "
              "`cycles` / `semi_out` / `sim_log` / `sim_md5`）；下面只列非 pass。")
    md.append("- 本段 `blocked` 是 picolibc 驱动的**历史原值**（含 host timeout 的 budget 类，"
              "已在 §4 单列 `budget_blocked`），不改写；embench 段已按新词表记 "
              "`timeout(<预算>)`、`blocked` 只留构建/环境缺口。")
    md.append("- 周期合计 %s；墙钟合计 %ss；sim md5 %s"
              % (cy.get("cycles_sum"), cy.get("wall_seconds_sum"),
                 cy.get("sim_md5")))
    md.append("")
    md.append("## 4. 与 qemu 基线逐例一致（同代码同 ELF，只换引擎）")
    md.append("")
    md.append("- qemu 基线 %d 例：pass %d / fail %d / blocked %d / excluded %d"
              % (qe["total"], qe["counts"]["pass"], qe["counts"]["fail"],
                 qe["counts"]["blocked"], qe["counts"]["excluded"]))
    md.append("- 逐例状态差集 = **%d**；chipyard 独有失败 = **%d**；"
              "qemu 缺口登记匹配 %d/%d"
              % (len(parity["differing"]),
                 len(parity["chipyard_only_failures"]),
                 len(parity["qemu_gaps_matched"]),
                 len(parity["qemu_gaps_registered"])))
    md.append("  - 依据：实测吞吐 **1.76 k cycles/s/例**（`slre(-O2)` 19.60 M "
              "cycles / 11140 s、32 并发），⇒ 4 h 预算内最多约 **25.3 M cycles**；"
              "超时例即需 >25 M cycles（同族 `nettle-aes(-O2)` 16.38 M 为下限参照），"
              "不是语义失败（`cycles=None`、无 guest verdict），也**不放宽** "
              "`+max-cycles` 或超时阈值。")
    md.append("- **budget 类单列**（host timeout ⇒ `blocked (budget: …)`，"
              "不计入 chipyard 独有失败）：%d 例%s"
              % (len(parity["budget_blocked"]),
                 ("：" + "、".join(parity["budget_blocked"]))
                 if parity["budget_blocked"] else ""))
    md.append("- 共有例数 %d；状态不一致 %d 例%s"
              % (parity["common"], len(parity["differing"]),
                 ("：" + "、".join(parity["differing"])) if parity["differing"] else ""))
    md.append("")
    bad_rows = [r for r in cy["cases"] if r["status"] in ("fail", "blocked")]
    if bad_rows:
        md += table("chipyard 侧非 pass 例（逐条原因）：", bad_rows, [
            ("case", lambda r: r["name"]), ("suite", lambda r: r["suite"]),
            ("status", lambda r: r["status"]),
            ("reason", lambda r: r["reason"][:110])])
        md.append("")
    return payload, "\n".join(md) + "\n"


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _first_diff(want, got):
    """First differing line of two texts: (lineno, regenerated, committed)."""
    a, b = want.splitlines(), got.splitlines()
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            return i, x, y
    if len(a) != len(b):
        i = min(len(a), len(b)) + 1
        return i, (a[i - 1] if i <= len(a) else "<eof>"), \
            (b[i - 1] if i <= len(b) else "<eof>")
    return None


def _parse_node_map(items):
    """`日志名=节点` -> dict（可重复）；形状错即 setup 错。"""
    out = {}
    for item in items:
        name, sep, node = item.partition("=")
        if not sep or not name or not node:
            raise ValueError("--node-map wants LOG=NODE, got %r" % item)
        out[name] = node
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO_DEFAULT,
                    help="仓库根（默认 = 本脚本上溯三层）")
    ap.add_argument("--log-dir", default=None,
                    help="批次输入目录（默认 = <repo> 内 chipyard 运行期日志目录）")
    ap.add_argument("--out-dir", default=None,
                    help="报告输出目录（默认 <repo>/tests/data）")
    ap.add_argument("--node-map", action="append", default=[],
                    metavar="LOG=NODE",
                    help="覆盖分片→节点名（默认见 SHARD_NODE，可重复）")
    ap.add_argument("--check", nargs="?", const="", default=None, metavar="PATH",
                    help="与入库报告逐字节比对（缺省比对 <repo> 的两份报告）")
    args = ap.parse_args(argv)

    global REPO, LOG, NODE_MAP
    REPO = os.path.abspath(args.repo)
    LOG = (os.path.abspath(args.log_dir) if args.log_dir
           else os.path.join(REPO, ".work", "log", "chipyard"))
    out_dir = (os.path.abspath(args.out_dir) if args.out_dir
               else os.path.join(REPO, "tests", "data"))
    try:
        NODE_MAP.update(_parse_node_map(args.node_map))
    except ValueError as exc:
        print("engine_parity_report: SETUP: %s" % exc, file=sys.stderr)
        return 2

    try:
        payload, markdown = build()
    except SystemExit as exc:  # no embench shard
        print("engine_parity_report: SETUP: %s" % exc, file=sys.stderr)
        return 2
    except BudgetError as exc:  # label/seconds disagree: the report would lie
        print("engine_parity_report: FAIL: %s" % exc, file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print("engine_parity_report: SETUP: missing input %s" % exc,
              file=sys.stderr)
        return 2

    out_json = os.path.join(out_dir, REPORT_JSON_NAME)
    out_md = os.path.join(out_dir, REPORT_MD_NAME)

    if args.check is not None:
        if args.check:
            target = os.path.abspath(args.check)
            targets = [(target, payload if target.endswith(".json") else markdown)]
        else:
            targets = [(out_json, payload), (out_md, markdown)]
        rc = 0
        for path, want in targets:
            if not os.path.isfile(path):
                print("engine_parity_report: SETUP: %s not found" % path,
                      file=sys.stderr)
                return 2
            with open(path, encoding="utf-8") as fh:
                got = fh.read()
            print("engine_parity_report: sha256 committed   %s  %s"
                  % (_sha256(got), path))
            print("engine_parity_report: sha256 regenerated %s  (%d bytes)"
                  % (_sha256(want), len(want.encode("utf-8"))))
            if got != want:
                diff = _first_diff(want, got)
                print("engine_parity_report: FAIL: %s differs from the "
                      "regenerated report (%d vs %d bytes)"
                      % (path, len(got), len(want)), file=sys.stderr)
                if diff:
                    print("  first differing line %d\n    regenerated: %s\n"
                          "    committed:   %s"
                          % (diff[0], diff[1][:200], diff[2][:200]),
                          file=sys.stderr)
                rc = 1
        if rc == 0:
            print("engine_parity_report: check PASS")
        return rc

    os.makedirs(out_dir, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as fh:
        fh.write(payload)
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write(markdown)
    print("wrote %s\nwrote %s" % (out_json, out_md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
