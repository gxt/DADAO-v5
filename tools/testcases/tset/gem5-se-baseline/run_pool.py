#!/usr/bin/env python3
"""m13-testcases-005: case-level batch test pool (multi-node, append-only).

Implements the queue protocol of ``docs/Process-09 §16`` and the per-case
progress rule of ``docs/Process-08 §1.9``:

* **scheduling unit = one case** (never a suite).  Every case is one
  independent command on a node, calling the *existing* tset driver with its
  own per-case selection flag, its own ``--work-dir``, its own ``--json-out``
  and its own ``budget_s``.  No build/compare logic is re-implemented here;
  the driver's per-case record is the verdict.
* **results land as they happen**: each finished case appends one
  ``progress.jsonl`` line (``case``/``status``/``exit``/``seconds``/``reason``/
  ``fingerprint``/``utc``, plus ``suite``/``class``/``attempt``/``node``), and
  every state change appends one ``state.jsonl`` line
  (``pending``->``running``->``done|failed|timeout|blocked``, with UTC, node,
  attempt).  Both files are opened per append and fsync'ed: a kill loses at
  most the rows of the cases that were in flight.
* **idempotent resume**: ``--resume`` skips every case whose latest progress
  row says ``done``; ``--retry N`` re-queues ``failed``/``timeout`` cases up to
  ``N`` extra attempts, and ``attempt`` (counted from the recorded ``running``
  states) makes the retries visible.
* **node list is input, never code**: hosts come from ``--hosts`` only.  Per
  node the pool asks ``tools/infra/remote.py status`` for
  ``loadavg``/``disk_alert``/``running`` and opens
  ``min(idle cores, --jobs-per-node)`` slots; a node that is above the disk
  alert, already running a build/emulation, or loaded above its core count
  gets **0 slots** and its reason is printed.
* **xlong isolation**: ``class=xlong`` cases go to a *separate* queue served
  only by ``--xlong-hosts`` slots, so a long case never takes a main-queue
  slot and never blocks it.
* **metrics**: throughput (cases/h), wait amplification
  ``Σ(case seconds) / (wall clock × nodes active)`` (Process-09 §16.2, the
  formula is used as written), per node idle rate while work remained, and the
  barrier count (a queue that never waits for "a whole batch" has 0; retry
  waves are reported apart).  Read the amplification together with the slots:
  it is 1.0 when every node is busy end to end with one case in flight, and it
  grows with the number of slots per node (it then measures work density), so
  the §16.2 "≈1 is good" criterion is applied at one slot per node.

``budget_s`` is handed to the driver as its per-case budget (``--timeout`` and,
for the SE engine, ``--gem5-timeout``).  llvm-ts treats ``--timeout`` as a
floor for the few genuinely slow programs it records in its own timeout table;
the pool does not override that table (the driver owns the budget policy).

Exit status is about the *pool*, not about case verdicts: 0 = the queue ran to
completion and every case has a terminal record (whatever the verdict); 2 = bad
input / no usable node slot; 3 = a progress row could not be written (fail
closed: without the durable row the pool would fake progress); 130 = stopped by
a signal (the unfinished cases stay pending for ``--resume``).  A failing case
is a *result*, recorded in ``by_status`` (and, when the driver produced no
verdict at all, in ``pool_errors``) -- it never stops the pool and never changes
the exit code.

Node side: intermediate files stay in ``.work/`` of the node repository; the
per-case verdict travels back in the single ssh round trip (one
``POOL_RECORD`` line), so no second transfer is needed.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))

_INFRA = os.path.join(REPO_ROOT, "tools", "infra")
if _INFRA not in sys.path:
    sys.path.insert(0, _INFRA)
import remote  # noqa: E402  (transport is reused, not re-implemented)

TASK = "m13-testcases-005"
EVIDENCE_DIR = ".work/evidence/" + TASK

SUITES = ("libc-test", "llvm-ts", "embench")
DRIVERS = {
    "libc-test": "tools/testcases/tset/libc-test/run_libc_test_user_suite.py",
    "llvm-ts": "tools/testcases/tset/llvm-ts/run_llvm_ts_user.py",
    "embench": "tools/testcases/tset/embench/run_embench_user_suite.py",
}
# Per-suite "run exactly this one case" flag of the existing driver.  llvm-ts
# spells it --only; libc-test/embench spell the same thing --filter (a regex
# over case ids).  The pool always anchors the regex to the single id, so both
# spellings mean exactly "this case and no other": no new driver behaviour.
CASE_SELECT_FLAG = {"libc-test": "--filter", "llvm-ts": "--only",
                    "embench": "--filter"}
ENGINES = ("qemu", "gem5-se")
CLASSES = ("short", "normal", "long", "xlong")
LINK_MODES = ("static", "dynamic")
TERMINAL = ("done", "failed", "timeout", "blocked")
REQUIRED_CASE_KEYS = ("case", "suite", "link_mode", "budget_s", "class")

STATUS_OK = 0
STATUS_BAD_INPUT = 2
STATUS_PROGRESS_FAILED = 3

STOP = threading.Event()


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
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


def slug(text: str) -> str:
    """Filesystem-safe, bounded name for a case id (node-side directory)."""
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "case"
    if len(safe) <= 60:
        return safe
    return safe[:50] + "-" + hashlib.md5(text.encode()).hexdigest()[:8]


def node_label(host: str, index: int, total: int) -> str:
    """Short label for metrics/rows; ``#i`` only when ``--hosts`` repeats one."""
    base = host.split("@")[-1]
    return base if total == 1 else f"{base}#{index + 1}"


def short(text, limit=300):
    if text is None:
        return None
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


# ---------------------------------------------------------------------------
# case list
# ---------------------------------------------------------------------------
def load_cases(path: str):
    """One case per line; every field is validated (never guessed)."""
    cases, seen = [], set()
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: "
                                 f"not JSON ({exc})")
            if not isinstance(record, dict):
                raise ValueError(f"{os.path.basename(path)}:{lineno}: not an object")
            missing = [k for k in REQUIRED_CASE_KEYS if k not in record]
            if missing:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: missing "
                                 f"{', '.join(missing)}")
            if record["suite"] not in SUITES:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: unknown "
                                 f"suite {record['suite']!r} (expected "
                                 f"{list(SUITES)})")
            if record["link_mode"] not in LINK_MODES:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: unknown "
                                 f"link_mode {record['link_mode']!r}")
            if record["class"] not in CLASSES:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: unknown "
                                 f"class {record['class']!r} (expected "
                                 f"{list(CLASSES)})")
            budget = record["budget_s"]
            if not isinstance(budget, (int, float)) or isinstance(budget, bool) \
                    or budget <= 0:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: budget_s "
                                 f"must be a positive number (got {budget!r})")
            key = record["case"]
            if key in seen:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: duplicate "
                                 f"case {record['case']!r} (one queue entry per "
                                 f"case id)")
            seen.add(key)
            cases.append(dict(case=record["case"], suite=record["suite"],
                              link_mode=record["link_mode"],
                              budget_s=int(round(budget)),
                              klass_of_case=record["class"],
                              expect=record.get("expect")))
    if not cases:
        raise ValueError(f"{os.path.basename(path)}: no case in the list")
    return cases


# ---------------------------------------------------------------------------
# per-case driver command (reuses the driver's own single-case selection)
# ---------------------------------------------------------------------------
def driver_argv(case, engine, work_dir, json_out, report_out):
    """One case, one driver invocation, its own work dir and budget."""
    suite = case["suite"]
    cmd = ["python3", DRIVERS[suite],
           "--link-mode", case["link_mode"],
           "--engine", engine,
           "--jobs", "1",
           "--work-dir", work_dir,
           "--json-out", json_out,
           "--report-out", report_out,
           "--timeout", str(case["budget_s"]),
           "--gem5-timeout", str(case["budget_s"])]
    pattern = "^" + re.escape(case["case"]) + "$"
    cmd += [CASE_SELECT_FLAG[suite], pattern]
    return cmd


# The node-side extractor turns the driver JSON into one compact line: the
# full record (with compile/link argv) stays on the node, the verdict travels.
EXTRACT_PY = (
    "import json,sys\n"
    "d=json.load(open(sys.argv[1]))\n"
    "cs=d.get('cases') or []\n"
    "c=cs[0] if len(cs)==1 else None\n"
    "out={'counts':d.get('counts') or {},'total':d.get('total'),"
    "'records':len(cs)}\n"
    "if c is not None:\n"
    "    out['record']={k:c.get(k) for k in "
    "('case','klass','exit','reason','run_seconds','engine')}\n"
    "print('POOL_RECORD '+json.dumps(out,ensure_ascii=False))\n"
)


def node_script(argv, case_dir, json_out, hard_seconds):
    """One shell script per case: run, report rc, echo the compact verdict."""
    run = " ".join(shlex.quote(a) for a in argv)
    return "\n".join([
        "set -u",
        f"rm -f {shlex.quote(json_out)}",
        f"mkdir -p {shlex.quote(case_dir)}",
        f"timeout -k 10 -s TERM {int(hard_seconds)} {run} "
        f"> {shlex.quote(case_dir + '/driver.out')} 2>&1",
        "rc=$?",
        "printf 'POOL_RC=%s\\n' \"$rc\"",
        f"if [ -f {shlex.quote(json_out)} ]; then",
        f"  python3 -c {shlex.quote(EXTRACT_PY)} {shlex.quote(json_out)} "
        f"2>/dev/null || true",
        "fi",
        "exit 0",
    ])


def parse_verdict(stdout: str):
    """``(rc, record dict or None)`` from the node's POOL_* lines."""
    rc, record = None, None
    for line in stdout.splitlines():
        if line.startswith("POOL_RC="):
            try:
                rc = int(line.split("=", 1)[1])
            except ValueError:
                rc = None
        elif line.startswith("POOL_RECORD "):
            try:
                payload = json.loads(line.split(" ", 1)[1])
            except ValueError:
                payload = None
            if isinstance(payload, dict):
                rec = payload.get("record")
                if rec is None:
                    record = None
                else:
                    record = dict(rec)
                    record.update(counts=payload.get("counts") or {},
                                  total=payload.get("total"),
                                  records=payload.get("records"))
    return rc, record


def classify(record, driver_rc, transport_rc=None, hard=False):
    """Map the driver record to the protocol state (never a new taxonomy).

    Returns ``(status, exit, reason, source)``.  ``pass``/attributed
    ``known-fail`` => ``done`` (the case reached its verdict); ``fail`` =>
    ``failed``; a timeout (driver reason, the node-side ``timeout`` wrapper's
    rc 124, or the controller's hard kill) => ``timeout``; any other
    ``blocked`` => ``blocked``.  ``source`` separates a *case* failure
    (``driver``) from a failure of the pool to obtain a verdict (``transport``
    / ``no-record`` / ``node-hard-cap`` / ``hard-timeout``), so the pool's exit
    code never depends on a case verdict.
    """
    if hard:
        return "timeout", None, "hard timeout: the pool killed the case", \
            "hard-timeout"
    if transport_rc not in (None, 0):
        return "failed", None, f"transport failed (ssh rc={transport_rc})", \
            "transport"
    if driver_rc == 124:
        return "timeout", None, "timeout: node-side hard cap (rc=124)", \
            "node-hard-cap"
    if not record:
        return "failed", None, (
            f"driver produced no case record (rc={driver_rc}); see the "
            f"per-case driver.out on the node"), "no-record"
    klass = record.get("klass")
    reason = short(record.get("reason"))
    exit_code = record.get("exit")
    if klass == "pass":
        return "done", exit_code, reason, "driver"
    if klass == "known-fail":
        return "done", exit_code, f"known-fail (attributed): {reason}", "driver"
    if klass == "fail":
        return "failed", exit_code, reason, "driver"
    if klass == "blocked":
        if reason and str(reason).lower().startswith("timeout"):
            return "timeout", exit_code, reason, "driver"
        return "blocked", exit_code, reason, "driver"
    return "failed", exit_code, \
        f"unclassified driver klass {klass!r}: {reason}", "driver"


# ---------------------------------------------------------------------------
# node state (remote.py status + one probe for nproc/cpu)
# ---------------------------------------------------------------------------
def parse_status(text: str):
    """``{host: {rc, commit, worktree, disk_alert, loadavg, running, ...}}``."""
    hosts, current = {}, None
    for line in text.splitlines():
        head = re.match(r"^=== (\S+) \(rc=(-?\d+), log=.*\) ===$", line)
        if head:
            current = head.group(1)
            hosts[current] = {"rc": int(head.group(2))}
            continue
        if current and "=" in line and not line.startswith(" "):
            key, value = line.split("=", 1)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                hosts[current][key] = value
    return hosts


PROBE_PY = (
    "import os\n"
    "print('NPROC %d' % (os.cpu_count() or 0))\n"
    "m='unknown'\n"
    "try:\n"
    "    for line in open('/proc/cpuinfo',errors='replace'):\n"
    "        if line.startswith('model name'):\n"
    "            m=line.split(':',1)[1].strip(); break\n"
    "except OSError:\n"
    "    pass\n"
    "print('CPU '+m)\n"
)


def parse_probe(text: str):
    nproc, cpu = None, None
    for line in text.splitlines():
        if line.startswith("NPROC "):
            try:
                nproc = int(line.split(" ", 1)[1])
            except ValueError:
                nproc = None
        elif line.startswith("CPU "):
            cpu = line.split(" ", 1)[1].strip() or None
    return nproc, cpu


def decide_slots(state, nproc, cap, allow_busy=False):
    """``(main slots, why)`` for one node -- the only place policy lives."""
    if state is None:
        return 0, "no status record"
    if state.get("rc") != 0:
        return 0, f"status failed (rc={state.get('rc')})"
    alert = state.get("disk_alert")
    if alert is None:
        return 0, "disk_alert not reported"
    if alert != "ok":
        return 0, f"disk_alert={alert}"
    running = state.get("running") or "none"
    if running != "none" and not allow_busy:
        return 0, f"busy: {short(running, 90)}"
    try:
        load1 = float(str(state.get("loadavg", "")).split()[0])
    except (ValueError, IndexError):
        load1 = None
    if nproc is None:
        return 0, "nproc unknown"
    idle = nproc if load1 is None else nproc - int(math.ceil(load1))
    if idle <= 0:
        return 0, f"loadavg1={load1} >= nproc={nproc}"
    return min(cap, idle), f"idle={idle}, cap={cap}"


# ---------------------------------------------------------------------------
# progress / state logs (append-only, one open per row, fsync)
# ---------------------------------------------------------------------------
class Journal:
    def __init__(self, run_dir: str, inject_failure: bool = False):
        self.progress = os.path.join(run_dir, "progress.jsonl")
        self.state = os.path.join(run_dir, "state.jsonl")
        self.lock = threading.Lock()
        self.inject_failure = inject_failure

    def _append(self, path: str, row: dict):
        line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def progress_row(self, row: dict):
        with self.lock:
            if self.inject_failure:
                self.inject_failure = False
                raise OSError("INJECTED progress write failure")
            self._append(self.progress, row)

    def state_row(self, case: str, state: str, node=None, attempt=None, why=None):
        row = dict(utc=iso_utc(), case=case, state=state, node=node,
                   attempt=attempt)
        if why:
            row["why"] = short(why)
        with self.lock:
            self._append(self.state, row)


def read_jsonl(path: str):
    rows = []
    if not os.path.isfile(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(f"{os.path.basename(path)}:{lineno}: {exc}")
    return rows


def plan_resume(case_rows, progress_rows, state_rows, retry):
    """``({case: skip_reason}, {case: attempts_used}, {case: note})``.

    Every *terminal* record is skipped (the idempotent continuation): ``done``
    and ``blocked`` outright (``blocked`` is a definite platform gap, never a
    transient failure), while ``failed``/``timeout`` are re-queued only when an
    attempt is left under ``--retry``.  A case whose retry quota is
    **exhausted** is skipped as well -- it is not re-queued, so ``attempt`` can
    never exceed ``1 + --retry`` across repeated resumes; ``notes`` carries the
    same fact for the human log only.  ``attempts_used`` counts the recorded
    ``running`` states, so an interrupted case counts as an attempt even though
    it produced no verdict.
    """
    latest, attempts = {}, {}
    for row in progress_rows:
        latest[row.get("case")] = row
    for row in state_rows:
        if row.get("state") == "running":
            attempts[row.get("case")] = attempts.get(row.get("case"), 0) + 1
    skip, notes = {}, {}
    for case in case_rows:
        status = (latest.get(case["case"]) or {}).get("status")
        if status == "done":
            skip[case["case"]] = "done"
        elif status == "blocked":
            # Terminal verdict (a platform gap): re-running it would only
            # rewrite a settled record.
            skip[case["case"]] = "blocked (terminal, never retried)"
        elif status in ("failed", "timeout"):
            used = attempts.get(case["case"], 0)
            if used >= 1 + retry:
                note = (f"{status}, attempts={used} >= 1+--retry {retry}: "
                        f"not retried (quota exhausted)")
                # Not queued again: the quota is a hard cap, not a hint.
                skip[case["case"]] = note
                notes[case["case"]] = note
    return skip, attempts, notes


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
def remote_exec(ns, host, script, timeout):
    argv = remote.build_shell(ns, host, script)
    proc = subprocess.run(argv, capture_output=True, text=True,
                          errors="replace", timeout=timeout,
                          stdin=subprocess.DEVNULL)
    return proc.returncode, proc.stdout, proc.stderr


def case_run(ns, host, label, case, engine, journal, node_fingerprint,
             hard_extra, grace=60):
    """Run one case on one node; append its rows; return the progress row."""
    case_dir = (f"{EVIDENCE_DIR}/runtime/{slug(_RUN_NAME)}/{slug(label)}/"
                f"{slug(case['case'])}")
    json_out = f"{case_dir}/result.json"
    report_out = f"{case_dir}/result.log"
    work_dir = f"{case_dir}/wd"
    hard = case["budget_s"] + hard_extra
    argv = driver_argv(case, engine, work_dir, json_out, report_out)
    script = node_script(argv, case_dir, json_out, hard)

    attempt = next_attempt(case["case"])
    journal.state_row(case["case"], "running", node=label, attempt=attempt)
    started = iso_utc()
    t0 = time.monotonic()
    transport_rc, stdout, stderr = None, "", ""
    hard_hit = False
    try:
        transport_rc, stdout, stderr = remote_exec(ns, host, script,
                                                   hard + grace)
    except subprocess.TimeoutExpired:
        hard_hit = True
    except OSError as exc:
        transport_rc, stderr = 255, f"{type(exc).__name__}: {exc}"
    finally:
        seconds = round(time.monotonic() - t0, 3)

    driver_rc, record = parse_verdict(stdout)
    status, exit_code, reason, source = classify(record, driver_rc,
                                                 transport_rc, hard=hard_hit)
    if source == "transport" and stderr:
        reason = f"{reason}; {short(stderr, 120)}"
    row = dict(case=case["case"], suite=case["suite"],
               **{"class": case["klass_of_case"]},
               status=status, exit=exit_code, seconds=seconds,
               reason=reason, utc=iso_utc(), started_utc=started,
               attempt=attempt, node=label,
               engine=engine, link_mode=case["link_mode"], source=source,
               klass=(record or {}).get("klass"),
               run_seconds=(record or {}).get("run_seconds"),
               fingerprint=node_fingerprint)
    journal.progress_row(row)
    journal.state_row(case["case"], status, node=label, attempt=attempt,
                      why=reason)
    print(f"[{status:7s}] {case['case']} node={label} attempt={attempt} "
          f"{seconds:7.2f}s exit={exit_code} {reason or ''}", flush=True)
    return row


_ATTEMPT = {}
_ATTEMPT_LOCK = threading.Lock()
_RUN_NAME = "pool"


def next_attempt(case):
    with _ATTEMPT_LOCK:
        _ATTEMPT[case] = _ATTEMPT.get(case, 0) + 1
        return _ATTEMPT[case]


def pending_attempt(case):
    with _ATTEMPT_LOCK:
        return _ATTEMPT.get(case, 0) + 1


def run_slots(pending, slots, engine, journal, node_fingerprints, hard_extra):
    """Every slot thread pulls single cases until the queue drains.

    No thread ever waits for another case to finish: the only wait is the final
    join, i.e. the closing drain (Process-09 §16.2 "屏障 -> 0 除收尾").
    """
    work = queue.Queue()
    for case in pending:
        work.put(case)
    rows, errors, lock = [], [], threading.Lock()
    per_node = {}
    for label, _host in slots:
        per_node.setdefault(label, dict(busy=0.0, slots=0))
        per_node[label]["slots"] += 1

    def worker(label, host):
        while True:
            if STOP.is_set():
                return
            try:
                case = work.get_nowait()
            except queue.Empty:
                return
            try:
                row = case_run(ns=_NS, host=host, label=label, case=case,
                               engine=engine, journal=journal,
                               node_fingerprint=node_fingerprints[label],
                               hard_extra=hard_extra)
            except OSError as exc:  # durable progress row failed: fail closed
                with lock:
                    errors.append((case["case"], str(exc)))
                STOP.set()
                return
            with lock:
                rows.append(row)
                per_node[label]["busy"] += row["seconds"]

    threads = [threading.Thread(target=worker, args=(label, host), daemon=True)
               for label, host in slots]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    busy = {label: dict(stat) for label, stat in per_node.items()}
    return rows, busy, errors


def merge_busy(total: dict, new: dict):
    for label, stat in new.items():
        cur = total.setdefault(label, dict(busy=0.0, slots=0))
        cur["busy"] += stat["busy"]
        cur["slots"] = max(cur["slots"], stat["slots"])


def metrics(rows, wall, busy):
    """Process-09 §16.2 indicators, computed from what actually happened.

    The §16.2 formula divides by ``nodes`` (not by slots).  That is reported as
    ``value`` **and** the slot-normalised form is reported as
    ``value_per_slot``: with more than one slot per node the node form grows
    with the concurrency (it then measures work density and is structurally
    <= 1 only at one slot per node), so both numbers are printed and the
    criterion is read against ``value_per_slot`` when slots != nodes.
    """
    total = sum(row["seconds"] for row in rows)
    nodes = [label for label, stat in busy.items() if stat["slots"] and
             any(row["node"] == label for row in rows)]
    slots_total = sum(busy[label]["slots"] for label in nodes)
    amplification = None
    per_slot = None
    if wall > 0 and nodes:
        amplification = round(total / (wall * len(nodes)), 3)
    if wall > 0 and slots_total:
        per_slot = round(total / (wall * slots_total), 3)
    idle = {}
    for label in nodes:
        slots = busy[label]["slots"]
        idle[label] = round(max(0.0, 1.0 - busy[label]["busy"] / (wall * slots)),
                            3) if wall > 0 and slots else None
    return dict(
        executed=len(rows), wall_seconds=round(wall, 3), nodes_active=nodes,
        sum_case_seconds=round(total, 3),
        slots={label: busy[label]["slots"] for label in nodes},
        slots_total=slots_total,
        throughput_per_hour=(round(len(rows) / wall * 3600.0, 1)
                             if wall > 0 else None),
        wait_amplification=dict(
            value=amplification,
            formula="sum(case seconds) / (wall seconds * nodes active)",
            nodes_active=len(nodes), slots_total=slots_total,
            value_per_slot=per_slot,
            formula_per_slot=("sum(case seconds) / (wall seconds * slots "
                              "total)")),
        idle_rate=idle,
    )


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------
def build_plan(args):
    """Read node state, decide slots, and split cases into the two queues."""
    cases = load_cases(args.cases)
    hosts = [h for h in re.split(r"[,\s]+", args.hosts or "") if h]
    if not hosts:
        raise ValueError("--hosts is required (comma separated; the node list "
                         "is input, never built in)")
    for host in hosts:
        if host.startswith("-"):
            raise ValueError(f"refusing host that looks like an option: {host}")
    xlong = [h for h in re.split(r"[,\s]+", args.xlong_hosts or "") if h] \
        if args.xlong_hosts else list(hosts)
    unknown = [h for h in xlong if h not in hosts]
    if unknown:
        raise ValueError(f"--xlong-hosts not in --hosts: {unknown}")

    status_text = ""
    if args.status_json:
        with open(args.status_json, "r", encoding="utf-8") as fh:
            status_text = fh.read()
        argv = None
    else:
        argv = [sys.executable, os.path.join("tools", "infra", "remote.py"),
                "status", "--hosts", ",".join(dict.fromkeys(hosts)),
                "--repo", args.node_repo, "--log-prefix", TASK]
        if args.local:
            argv.append("--local")
    os.makedirs(args.run_dir, exist_ok=True)
    if argv is not None:
        proc = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True,
                              text=True, errors="replace")
        status_text = proc.stdout
        with open(os.path.join(args.run_dir, "status.log"), "w",
                  encoding="utf-8") as fh:
            fh.write(proc.stdout)
            fh.write("\n--- stderr ---\n")
            fh.write(proc.stderr)
        if proc.returncode != 0:
            print(f"[warn] remote.py status rc={proc.returncode} "
                  f"(a node that cannot be read gets 0 slots)", flush=True)
    states = parse_status(status_text)

    ns = SimpleNamespace(**{"repo": args.node_repo, "local": args.local,
                            "ssh_arg": list(args.ssh_arg)})
    cap = args.jobs_per_node if args.jobs_per_node else 48
    plan_nodes, fingerprints = {}, {}
    driver_md5 = {suite: md5_file(os.path.join(REPO_ROOT, path))
                  for suite, path in DRIVERS.items()}
    for index, host in enumerate(hosts):
        label = node_label(host, index, len(hosts))
        if args.local:
            nproc, cpu = os.cpu_count(), "local"
        else:
            rc, out, _err = remote_exec(
                ns, host, "python3 -c " + shlex.quote(PROBE_PY), 120)
            nproc, cpu = parse_probe(out) if rc == 0 else (None, None)
        slots, why = decide_slots(states.get(host), nproc, cap, args.allow_busy)
        is_xlong_host = host in xlong
        xlong_slots = min(args.xlong_jobs_per_node, slots) if is_xlong_host else 0
        plan_nodes[label] = dict(host=host, slots_main=slots,
                                 slots_xlong=xlong_slots, why=why,
                                 xlong_host=is_xlong_host, nproc=nproc,
                                 cpu_model=cpu)
        state = states.get(host) or {}
        fingerprints[label] = dict(
            node=label, cpu_model=cpu, nproc=nproc,
            commit=state.get("commit"), worktree=state.get("worktree"),
            engine=args.engine, qemu_md5=state.get("qemu_md5"),
            musl_head=state.get("musl_head"), driver_md5=driver_md5)
    main_cases = [c for c in cases if c["klass_of_case"] != "xlong"]
    xlong_cases = [c for c in cases if c["klass_of_case"] == "xlong"]
    plan = dict(generated_utc=iso_utc(), task=TASK, engine=args.engine,
                hosts=hosts, xlong_hosts=xlong, nodes=plan_nodes,
                queues=dict(main=len(main_cases), xlong=len(xlong_cases)),
                cases=dict(main=[c["case"] for c in main_cases],
                           xlong=[c["case"] for c in xlong_cases]),
                main_slots=sum(n["slots_main"] for n in plan_nodes.values()),
                xlong_slots=(sum(n["slots_xlong"] for n in plan_nodes.values())
                             if xlong_cases else 0),
                fingerprint=fingerprints)
    return plan, cases, main_cases, xlong_cases, ns


def print_plan(plan):
    print(f"[plan] engine={plan['engine']} hosts={len(plan['hosts'])} "
          f"main_cases={plan['queues']['main']} "
          f"xlong_cases={plan['queues']['xlong']} "
          f"main_slots={plan['main_slots']} "
          f"xlong_slots={plan['xlong_slots']}", flush=True)
    for label, node in plan["nodes"].items():
        print(f"[plan]   {label}: main={node['slots_main']} "
              f"xlong={node['slots_xlong']} nproc={node['nproc']} "
              f"({node['why']})", flush=True)


# ---------------------------------------------------------------------------
# self-test (no node, no corpus)
# ---------------------------------------------------------------------------
def _check(checks, name, want, got):
    checks.append((name, want, got))


def self_test(tmpdir: str) -> int:
    os.makedirs(tmpdir, exist_ok=True)
    checks = []

    # -- case list validation ------------------------------------------------
    good = os.path.join(tmpdir, "cases.jsonl")
    with open(good, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(case="functional/argv", suite="libc-test",
                                 link_mode="static", budget_s=60,
                                 **{"class": "short"})) + "\n")
        fh.write(json.dumps(dict(case="MultiSource/Applications/aha",
                                 suite="llvm-ts", link_mode="static",
                                 budget_s=300, **{"class": "xlong"})) + "\n")
    cases = load_cases(good)
    _check(checks, "cases count", 2, len(cases))
    _check(checks, "cases class kept", "xlong", cases[1]["klass_of_case"])
    for bad_line, why in (
            (dict(case="a", suite="libc-test", link_mode="static",
                  budget_s=60), "missing class"),
            (dict(case="a", suite="nope", link_mode="static", budget_s=60,
                  **{"class": "short"}), "unknown suite"),
            (dict(case="a", suite="libc-test", link_mode="static",
                  budget_s=0, **{"class": "short"}), "zero budget"),
            (dict(case="a", suite="libc-test", link_mode="static",
                  budget_s=60, **{"class": "weird"}), "unknown class")):
        path = os.path.join(tmpdir, "bad.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(bad_line) + "\n")
        try:
            load_cases(path)
            _check(checks, f"reject {why}", "ValueError", "no exception")
        except ValueError:
            _check(checks, f"reject {why}", "ValueError", "ValueError")
    dup = os.path.join(tmpdir, "dup.jsonl")
    row = dict(case="a", suite="libc-test", link_mode="static", budget_s=60,
               **{"class": "short"})
    with open(dup, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n" + json.dumps(row) + "\n")
    try:
        load_cases(dup)
        _check(checks, "reject duplicate", "ValueError", "no exception")
    except ValueError:
        _check(checks, "reject duplicate", "ValueError", "ValueError")

    # -- per-case selection is anchored to exactly one case ------------------
    case = dict(case="functional/argv", suite="libc-test", link_mode="static",
                budget_s=60, klass_of_case="short")
    argv = driver_argv(case, "qemu", "wd", "r.json", "r.log")
    _check(checks, "libc selection flag", ["--filter"],
           [a for a in argv if a in ("--filter", "--only")])
    _check(checks, "libc selection anchored", "^functional/argv$",
           argv[argv.index("--filter") + 1])
    _check(checks, "libc budget", "60", argv[argv.index("--timeout") + 1])
    _check(checks, "libc work dir per case", "wd", argv[argv.index("--work-dir") + 1])
    _check(checks, "engine passed", "qemu", argv[argv.index("--engine") + 1])
    llvm = driver_argv(dict(case="MultiSource/Applications/aha",
                            suite="llvm-ts", link_mode="dynamic",
                            budget_s=300, klass_of_case="long"),
                       "gem5-se", "wd", "r.json", "r.log")
    _check(checks, "llvm selection flag", ["--only"],
           [a for a in llvm if a in ("--filter", "--only")])
    _check(checks, "llvm only anchored", "^MultiSource/Applications/aha$",
           llvm[llvm.index("--only") + 1])
    _check(checks, "llvm link mode", "dynamic",
           llvm[llvm.index("--link-mode") + 1])
    _check(checks, "llvm gem5 budget", "300",
           llvm[llvm.index("--gem5-timeout") + 1])
    _check(checks, "llvm jobs single", "1", llvm[llvm.index("--jobs") + 1])

    # -- node script + verdict parsing --------------------------------------
    script = node_script(["python3", "driver.py", "--x", "a b"], "/d/case",
                         "/d/case/result.json", 90)
    _check(checks, "script quotes argv", "'a b'" in script, True)
    _check(checks, "script has hard cap", "timeout -k 10 -s TERM 90" in script, True)
    _check(checks, "script reports rc", "POOL_RC=%s" in script, True)
    rc, record = parse_verdict(
        "noise\nPOOL_RC=1\nPOOL_RECORD " + json.dumps(dict(
            counts={"pass": 0, "fail": 1}, total=1, records=1,
            record=dict(case="a", klass="fail", exit=1, reason="exit 1",
                        run_seconds=0.2, engine="qemu"))) + "\n")
    _check(checks, "parse rc", 1, rc)
    _check(checks, "parse klass", "fail", record["klass"])
    _check(checks, "parse run_seconds", 0.2, record["run_seconds"])
    rc2, record2 = parse_verdict("POOL_RC=2\n")
    _check(checks, "parse rc without record", 2, rc2)
    _check(checks, "parse record absent", None, record2)

    # -- classification: every protocol state has a reachable input ---------
    def rec(**kw):
        base = dict(case="a", klass="pass", exit=0, reason="exit 0",
                    run_seconds=1.0, engine="qemu")
        base.update(kw)
        return base
    _check(checks, "pass -> done", "done", classify(rec(), 0)[0])
    _check(checks, "known-fail -> done", "done",
           classify(rec(klass="known-fail"), 0)[0])
    _check(checks, "known-fail reason labelled", True,
           classify(rec(klass="known-fail", reason="ISS-251"), 0)[2]
           .startswith("known-fail (attributed)"))
    _check(checks, "fail -> failed", "failed",
           classify(rec(klass="fail", exit=1, reason="exit 1"), 1)[0])
    _check(checks, "timeout reason -> timeout", "timeout",
           classify(rec(klass="blocked", exit=None,
                        reason="timeout after 2s (blocked, not pass/fail)"),
                    1)[0])
    _check(checks, "blocked -> blocked", "blocked",
           classify(rec(klass="blocked", exit=None,
                        reason="no PT_INTERP"), 1)[0])
    _check(checks, "no record -> failed", "failed", classify(None, 1)[0])
    _check(checks, "node hard cap rc=124 -> timeout", "timeout",
           classify(None, 124)[0])
    _check(checks, "transport rc -> failed", "failed",
           classify(rec(), 0, transport_rc=255)[0])
    _check(checks, "controller kill -> timeout", "timeout",
           classify(rec(), 0, hard=True)[0])
    _check(checks, "unknown klass -> failed", "failed",
           classify(rec(klass="???"), 0)[0])

    # -- node state -> slots (status-driven, no hardcoded node list) --------
    idle = {"rc": 0, "disk_alert": "ok", "running": "none",
            "loadavg": "0.00 0.00 0.00", "commit": "abc"}
    _check(checks, "idle 64 cores cap 48", (48, "idle=64, cap=48"),
           decide_slots(idle, 64, 48))
    _check(checks, "explicit cap wins", 8, decide_slots(idle, 64, 8)[0])
    _check(checks, "loaded node shrinks slots", 4,
           decide_slots(dict(idle, loadavg="60.0 60.0 60.0"), 64, 48)[0])
    _check(checks, "zero free cores -> 0", 0,
           decide_slots(dict(idle, loadavg="64.0 64.0 64.0"), 64, 48)[0])
    _check(checks, "running build -> 0", 0,
           decide_slots(dict(idle, running="gem5.opt --outdir x"), 64, 48)[0])
    _check(checks, "running build allowed -> slots", 48,
           decide_slots(dict(idle, running="gem5.opt --outdir x"), 64, 48,
                        allow_busy=True)[0])
    _check(checks, "disk alert -> 0", 0,
           decide_slots(dict(idle, disk_alert="ALERT"), 64, 48)[0])
    _check(checks, "status rc!=0 -> 0", 0,
           decide_slots(dict(idle, rc=255), 64, 48)[0])
    _check(checks, "no status -> 0", 0, decide_slots(None, 64, 48)[0])
    _check(checks, "unknown nproc -> 0", 0, decide_slots(idle, None, 48)[0])
    _check(checks, "why names the blockers", True,
           "busy" in decide_slots(dict(idle, running="make"), 64, 48)[1])

    status_text = "\n".join([
        "=== gxt@a (rc=0, log=x.log) ===",
        "commit=deadbeef",
        "worktree=clean",
        "disk_alert=ok",
        "loadavg=1.00 2.00 3.00",
        "running=none",
        "=== gxt@b (rc=255, log=y.log) ===",
        "",
        "host -> rc",
        "overall rc=1",
    ])
    parsed = parse_status(status_text)
    _check(checks, "status hosts", ["gxt@a", "gxt@b"], list(parsed))
    _check(checks, "status commit", "deadbeef", parsed["gxt@a"]["commit"])
    _check(checks, "status rc b", 255, parsed["gxt@b"]["rc"])
    _check(checks, "status loadavg", "1.00 2.00 3.00",
           parsed["gxt@a"]["loadavg"])
    _check(checks, "status key with digit", "abc",
           parse_status("=== h (rc=0, log=x) ===\nqemu_md5=abc\n")["h"]
           ["qemu_md5"])
    _check(checks, "probe parse", (64, "Xeon"),
           parse_probe("NPROC 64\nCPU Xeon\n"))
    _check(checks, "node labels unique", ["h#1", "h#2"],
           [node_label("gxt@h", 0, 2), node_label("gxt@h", 1, 2)])
    _check(checks, "single node label plain", "h",
           node_label("gxt@h", 0, 1))

    # -- resume / retry planning -------------------------------------------
    rows_all = [dict(case="a", suite="libc-test", link_mode="static",
                     class_="short")] + \
        [dict(case=cid, suite="libc-test", link_mode="static")
         for cid in "bcd"]
    progress = [dict(case="a", status="done", attempt=1),
                dict(case="b", status="failed", attempt=1),
                dict(case="c", status="timeout", attempt=1),
                dict(case="d", status="blocked", attempt=1)]
    states = [dict(case="b", state="running", attempt=1),
              dict(case="c", state="running", attempt=1)]
    skip, attempts, notes = plan_resume(rows_all, progress, states, retry=0)
    # retry 0 => a failed case has no budget left: it must not run again on
    # --resume either (terminal record, retry is opt-in).
    _check(checks, "retry 0 skips done/exhausted/blocked",
           ["a", "b", "c", "d"], sorted(skip))
    _check(checks, "retry 0 reports the exhausted case", True, "b" in notes)
    _check(checks, "blocked is skipped as terminal", True, "d" in skip)
    _check(checks, "attempts from state rows", 1, attempts.get("b"))
    skip2, _a2, notes2 = plan_resume(rows_all, progress, states, retry=2)
    _check(checks, "retry 2 re-queues b", False, "b" in skip2)
    _check(checks, "retry 2 re-queues c", False, "c" in skip2)
    _check(checks, "retry 2 still skips blocked", True, "d" in skip2)
    _check(checks, "retry 2 has no exhausted note", {}, notes2)

    # after the retry the quota is spent: a further --resume must NOT re-run it
    # (this is the "attempt <= 1 + --retry" cap across repeated resumes).
    p3 = list(progress) + [dict(case="b", status="failed", attempt=2)]
    s3 = list(states) + [dict(case="b", state="running", attempt=2)]
    skip3, attempts3, notes3 = plan_resume(rows_all, p3, s3, retry=1)
    _check(checks, "exhausted retry is skipped", True, "b" in skip3)
    _check(checks, "exhausted retry is still reported", True, "b" in notes3)
    _check(checks, "attempts counted from state rows", 2, attempts3.get("b"))
    pending3 = [c["case"] for c in rows_all if c["case"] not in skip3]
    _check(checks, "exhausted case is not queued again", ["c"], pending3)
    skip4, attempts4, _n4 = plan_resume(rows_all, p3, s3, retry=1)
    _check(checks, "a further resume keeps the same cap", True,
           "b" in skip4 and attempts4.get("b") == 2)

    # -- metrics ------------------------------------------------------------
    busy = {"n1": dict(busy=10.0, slots=1), "n2": dict(busy=10.0, slots=1)}
    rows_m = [dict(node="n1", seconds=6.0), dict(node="n1", seconds=4.0),
              dict(node="n2", seconds=5.0), dict(node="n2", seconds=5.0)]
    met = metrics(rows_m, 10.0, busy)
    _check(checks, "amplification 20/(10*2)", 1.0,
           met["wait_amplification"]["value"])
    _check(checks, "throughput 4/10s", 1440.0, met["throughput_per_hour"])
    _check(checks, "idle 0 when busy", 0.0, met["idle_rate"]["n1"])
    met2 = metrics(rows_m, 20.0, busy)
    _check(checks, "amplification drops when idle grows", 0.5,
           met2["wait_amplification"]["value"])
    _check(checks, "idle rises with wall", 0.5, met2["idle_rate"]["n1"])
    _check(checks, "empty run has no amplification", None,
           metrics([], 0.0, busy)["wait_amplification"]["value"])
    # slot-normalised form: 2 slots per node means work density 2x the node form
    busy2 = {"n1": dict(busy=20.0, slots=2), "n2": dict(busy=20.0, slots=2)}
    met3 = metrics(rows_m, 10.0, busy2)
    _check(checks, "nodes form ignores slots", 1.0,
           met3["wait_amplification"]["value"])
    _check(checks, "per-slot form divides by slots", 0.5,
           met3["wait_amplification"]["value_per_slot"])
    _check(checks, "slots_total reported", 4, met3["slots_total"])
    _check(checks, "nodes_active reported", 2,
           met3["wait_amplification"]["nodes_active"])

    # -- journal: append-only, resumable, and the injected failure is loud --
    journal_dir = os.path.join(tmpdir, "journal")
    shutil.rmtree(journal_dir, ignore_errors=True)
    os.makedirs(journal_dir, exist_ok=True)
    journal = Journal(journal_dir)
    journal.progress_row(dict(case="a", status="done"))
    journal.progress_row(dict(case="b", status="failed"))
    journal.state_row("a", "running", node="n1", attempt=1)
    _check(checks, "progress rows appended", 2,
           len(read_jsonl(journal.progress)))
    _check(checks, "state rows appended", 1, len(read_jsonl(journal.state)))
    injected = Journal(journal_dir, inject_failure=True)
    try:
        injected.progress_row(dict(case="c", status="done"))
        _check(checks, "injected progress failure raises", "OSError",
               "no exception")
    except OSError:
        _check(checks, "injected progress failure raises", "OSError", "OSError")
    _check(checks, "injected failure wrote nothing", 2,
           len(read_jsonl(injected.progress)))

    failed = 0
    for name, want, got in checks:
        passed = want == got
        failed += 0 if passed else 1
        print(f"self-test {'PASS' if passed else 'FAIL'} {name}: "
              f"expected={want!r} actual={got!r}")
    print(f"self-test: {len(checks) - failed}/{len(checks)} checks passed")
    return STATUS_OK if failed == 0 else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=f"{TASK}: case-level batch test pool (Process-09 §16)")
    ap.add_argument("--cases", default=None,
                    help="cases.jsonl (one {case,suite,link_mode,budget_s,class} "
                         "per line; required unless --self-test)")
    ap.add_argument("--run-dir", default=EVIDENCE_DIR + "/runtime/pool",
                    help="runtime directory for progress.jsonl / state.jsonl "
                         "(relative paths resolve against the repository root)")
    ap.add_argument("--hosts", default="",
                    help="comma separated node list (ssh targets); the only "
                         "source of node identity")
    ap.add_argument("--xlong-hosts", default="",
                    help="nodes allowed to run class=xlong (default: all "
                         "--hosts); these get their own slots")
    ap.add_argument("--node-repo", default="~/DADAO-v5",
                    help="repository path on the nodes (default: %(default)s)")
    ap.add_argument("--engine", choices=ENGINES, default="qemu")
    ap.add_argument("--jobs-per-node", type=int, default=0,
                    help="slot cap per node (default: min(idle cores, 48))")
    ap.add_argument("--xlong-jobs-per-node", type=int, default=1,
                    help="extra slots per xlong host, outside the main quota "
                         "(default 1)")
    ap.add_argument("--xlong-budget", type=int, default=0,
                    help="budget override for class=xlong in seconds "
                         "(0 = keep the case's own budget_s)")
    ap.add_argument("--hard-extra", type=int, default=600,
                    help="seconds added to budget_s for the node-side hard cap "
                         "and the ssh timeout (build overhead; default 600)")
    ap.add_argument("--resume", action="store_true",
                    help="skip cases whose latest progress row is done; "
                         "failed/timeout are re-queued only with --retry")
    ap.add_argument("--retry", type=int, default=0,
                    help="extra attempts for failed/timeout cases (default 0)")
    ap.add_argument("--dry-run", action="store_true",
                    help="read node state, print and write the dispatch plan, "
                         "run nothing")
    ap.add_argument("--status-json", default=None,
                    help="read a recorded `remote.py status` output instead of "
                         "asking the nodes (planning/evidence only)")
    ap.add_argument("--allow-busy", action="store_true",
                    help="do not give 0 slots to a node that reports a running "
                         "build (NOT for baseline timing)")
    ap.add_argument("--local", action="store_true",
                    help="run the commands on this host instead of over ssh "
                         "(self-test only; labels still come from --hosts)")
    ap.add_argument("--ssh-arg", action="append", default=[], metavar="ARG",
                    help="extra ssh option (repeatable)")
    ap.add_argument("--inject-progress-failure", action="store_true",
                    help="evidence only: fail the first progress write so the "
                         "fail-closed path is reachable")
    ap.add_argument("--self-test", action="store_true",
                    help="unit checks on synthetic records (no node, no corpus)")
    args = ap.parse_args()

    global _NS, _RUN_NAME
    if args.self_test:
        base = args.run_dir if os.path.isabs(args.run_dir) else \
            os.path.join(REPO_ROOT, args.run_dir)
        return self_test(os.path.join(base, "selftest"))

    if not args.cases:
        sys.stderr.write("ERROR: --cases is required\n")
        return STATUS_BAD_INPUT
    if args.retry < 0:
        sys.stderr.write("ERROR: --retry must be >= 0\n")
        return STATUS_BAD_INPUT
    if args.jobs_per_node < 0 or args.xlong_jobs_per_node < 0:
        sys.stderr.write("ERROR: --jobs-per-node / --xlong-jobs-per-node must "
                         "be >= 0\n")
        return STATUS_BAD_INPUT
    if args.hard_extra < 0:
        sys.stderr.write("ERROR: --hard-extra must be >= 0\n")
        return STATUS_BAD_INPUT
    run_dir = args.run_dir if os.path.isabs(args.run_dir) else \
        os.path.join(REPO_ROOT, args.run_dir)
    args.run_dir = run_dir
    os.makedirs(run_dir, exist_ok=True)
    _RUN_NAME = os.path.basename(run_dir.rstrip(os.sep)) or "pool"
    journal = Journal(run_dir, inject_failure=args.inject_progress_failure)

    try:
        plan, cases, main_cases, xlong_cases, ns = build_plan(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return STATUS_BAD_INPUT
    print_plan(plan)
    with open(os.path.join(run_dir, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2, ensure_ascii=False)
    if not plan["main_slots"] and not plan["xlong_slots"]:
        sys.stderr.write("ERROR: no worker slot on any node (see the plan "
                         "reasons above)\n")
        return STATUS_BAD_INPUT
    if args.dry_run:
        print(f"[dry-run] plan written, nothing executed "
              f"(main queue {len(main_cases)}, xlong queue "
              f"{len(xlong_cases)})", flush=True)
        return STATUS_OK

    # --- resume / retry plan ----------------------------------------------
    try:
        progress_rows = read_jsonl(journal.progress)
        state_rows = read_jsonl(journal.state)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"ERROR: cannot read the logs: {exc}\n")
        return STATUS_BAD_INPUT
    if progress_rows and not args.resume:
        sys.stderr.write(
            f"ERROR: progress.jsonl already has {len(progress_rows)} row(s); "
            f"pass --resume (idempotent continuation) or use a fresh --run-dir\n")
        return STATUS_BAD_INPUT
    resume_skips, attempts_used, retry_notes = plan_resume(
        cases, progress_rows, state_rows, args.retry)
    with _ATTEMPT_LOCK:
        _ATTEMPT.update(attempts_used)
    for case in cases:
        if case["klass_of_case"] == "xlong" and args.xlong_budget:
            case["budget_s"] = args.xlong_budget
    pending_main = [c for c in main_cases if c["case"] not in resume_skips]
    pending_xlong = [c for c in xlong_cases if c["case"] not in resume_skips]
    for case in cases:
        if case["case"] in resume_skips:
            continue
        journal.state_row(case["case"], "pending",
                          attempt=pending_attempt(case["case"]))
    print(f"[resume] skipped_done={len(resume_skips)} "
          f"pending_main={len(pending_main)} "
          f"pending_xlong={len(pending_xlong)} "
          f"retry={args.retry}", flush=True)
    for cid, note in retry_notes.items():
        print(f"[resume] not retried: {cid}: {note}", flush=True)

    # --- dispatch ----------------------------------------------------------
    _NS = ns
    main_slots = [(label, node["host"])
                  for label, node in plan["nodes"].items()
                  for _ in range(node["slots_main"])]
    xlong_slots = [(label, node["host"])
                   for label, node in plan["nodes"].items()
                   for _ in range(node["slots_xlong"])]
    fingerprints = {label: dict(fp) for label, fp in
                    plan["fingerprint"].items()}

    started = time.monotonic()
    executed, waves, barriers = [], 0, 0
    queued = {case["case"] for case in pending_main + pending_xlong}
    queue_main, queue_xlong = list(pending_main), list(pending_xlong)
    busy_total = {}
    errors = []
    while True:
        waves += 1
        groups = [(name, pending, slots)
                  for name, pending, slots in (("main", queue_main, main_slots),
                                              ("xlong", queue_xlong, xlong_slots))
                  if pending]
        if not groups:
            break
        for name, pending, slots in groups:
            if not slots:
                sys.stderr.write(
                    f"ERROR: {len(pending)} {name} case(s) but no {name} slot "
                    f"on any node\n")
                return STATUS_BAD_INPUT
        # The two queues are served by their own slot groups, at the same time:
        # an xlong case never waits for the main queue and never takes one of
        # its slots.
        outcomes = {}

        def run_group(name, pending, slots):
            try:
                outcomes[name] = run_slots(pending, slots, args.engine,
                                           journal, fingerprints,
                                           args.hard_extra)
            except Exception as exc:  # noqa: BLE001 - report, never hide
                outcomes[name] = ([], {}, [("<queue>", f"{type(exc).__name__}: "
                                           f"{exc}")])

        runners = [threading.Thread(target=run_group,
                                    args=(name, pending, slots))
                   for name, pending, slots in groups]
        for runner in runners:
            runner.start()
        for runner in runners:
            runner.join()
        for name, _pending, _slots in groups:
            rows, busy, wave_errors = outcomes[name]
            executed += rows
            merge_busy(busy_total, busy)
            errors += wave_errors
        if errors:
            break
        if STOP.is_set():
            break
        if args.retry <= 0:
            break
        # A retry wave is the only extra drain: collect failed/timeout cases
        # that still have an attempt left.  blocked (a definite platform gap)
        # is never retried.
        retry_main, retry_xlong = [], []
        for case in pending_main + pending_xlong:
            last = [row for row in executed if row["case"] == case["case"]]
            if not last:
                continue
            row = last[-1]
            if row["status"] in ("failed", "timeout") and \
                    row["attempt"] <= args.retry:
                (retry_xlong if case["klass_of_case"] == "xlong"
                 else retry_main).append(case)
        if not retry_main and not retry_xlong:
            break
        print(f"[retry] wave {waves + 1}: {len(retry_main)} main + "
              f"{len(retry_xlong)} xlong case(s) re-queued "
              f"(attempt <= {args.retry + 1})", flush=True)
        barriers += 1
        for case in retry_main + retry_xlong:
            journal.state_row(case["case"], "pending",
                              attempt=pending_attempt(case["case"]),
                              why=f"retry (attempt {args.retry + 1})")
        queue_main, queue_xlong = retry_main, retry_xlong
        pending_main, pending_xlong = retry_main, retry_xlong
    wall = time.monotonic() - started
    unrecorded = sorted(queued - {row["case"] for row in executed
                                  if row["status"] in TERMINAL})
    if errors:
        for case, message in errors:
            sys.stderr.write(f"ERROR: progress write failed for {case!r}: "
                             f"{message}\n")
        sys.stderr.write("ERROR: stopped fail-closed -- a case without a "
                         "durable progress row is not progress\n")
        return STATUS_PROGRESS_FAILED

    # --- summary -----------------------------------------------------------
    met = metrics(executed, wall, busy_total)
    by_status, by_class = {}, {}
    for row in executed:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
        by_class[row["class"]] = by_class.get(row["class"], 0) + 1
    pool_failed = [row["case"] for row in executed
                   if row["status"] == "failed" and row["source"] != "driver"]
    summary = dict(
        task=TASK, generated_utc=iso_utc(), engine=args.engine,
        case_file=os.path.basename(args.cases),
        hosts=plan["hosts"], xlong_hosts=plan["xlong_hosts"],
        nodes={label: dict(main=node["slots_main"],
                           xlong=node["slots_xlong"], why=node["why"],
                           nproc=node["nproc"])
               for label, node in plan["nodes"].items()},
        queues=plan["queues"], resumed_skipped=sorted(resume_skips),
        retry=args.retry, retry_waves=max(0, waves - 1),
        barriers=barriers, interrupted=STOP.is_set(),
        executed=met["executed"], by_status=by_status, by_class=by_class,
        wall_seconds=met["wall_seconds"],
        sum_case_seconds=met["sum_case_seconds"],
        slots_total=met["slots_total"],
        slots=met["slots"],
        throughput_per_hour=met["throughput_per_hour"],
        wait_amplification=met["wait_amplification"],
        idle_rate=met["idle_rate"],
        pool_errors=pool_failed,
        fingerprint=plan["fingerprint"],
    )
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print(f"[done] executed={met['executed']} wall={met['wall_seconds']}s "
          f"throughput={met['throughput_per_hour']}/h "
          f"amp={met['wait_amplification']['value']} "
          f"amp_per_slot={met['wait_amplification']['value_per_slot']} "
          f"slots_total={met['slots_total']} "
          f"idle={met['idle_rate']} barriers={barriers} "
          f"by_status={by_status}", flush=True)
    print(f"summary: {os.path.join(run_dir, 'summary.json')}", flush=True)
    if STOP.is_set():
        print(f"[stop] {len(unrecorded)} case(s) left without a verdict "
              f"(pending for --resume): {unrecorded}", flush=True)
        return 130
    if unrecorded:
        sys.stderr.write(f"ERROR: {len(unrecorded)} queued case(s) ended "
                         f"without a terminal record: {unrecorded}\n")
        return 1
    if pool_failed:
        # A case that could not be given a verdict is a *recorded result*
        # (failed/no-record/transport), not a pool crash: the pool still ran to
        # completion, so the exit code stays 0 and the list is in the summary.
        sys.stderr.write(f"[warn] {len(pool_failed)} case(s) ended without a "
                         f"driver verdict (see summary.pool_errors): "
                         f"{pool_failed}\n")
    return STATUS_OK


def _install_signals():
    def handler(signum, _frame):
        if not STOP.is_set():
            print(f"[signal] {signal.Signals(signum).name}: stop dispatching, "
                  f"wait for the in-flight cases", flush=True)
        STOP.set()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, handler)


if __name__ == "__main__":
    _install_signals()
    try:
        sys.exit(main())
    except OSError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        sys.exit(STATUS_PROGRESS_FAILED)
