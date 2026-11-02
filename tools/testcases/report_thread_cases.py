#!/usr/bin/env python3
"""Thread-case truth report for the libc-test user suite (TESTCASES-052t / T3).

Reads the per-case JSON that ``run_libc_test_user_suite.py`` writes for the
static and the dynamic round, restricts it to the thread/``__clone`` case set
(the 19 ``blocked`` cases of the TESTCASES-047t baseline plus the
ISS-257-prone ``regression/pthread_create-oom``), and prints / emits:

  * one line per case: baseline class -> this-run class, exit code, reason;
  * per-round counts (pass / fail / blocked / known-fail / excluded);
  * the baseline->run drift list.

This tool only *reports*: it never re-labels a case and never edits a run
JSON.  The qualitative root-cause attribution of each non-pass lives in the
task book and in ``.tao/knowledge/issues.yaml``.

Exit status: 0 when every requested case is present exactly once in both runs
and the input JSONs are well formed; 2 otherwise (missing/duplicate case, bad
input).  A non-pass case is *data*, not an error -- the caller asserts on the
emitted report.

Usage:
  tools/testcases/report_thread_cases.py \
      --run-static  /tmp/opencode/TESTCASES-052t/sub-static.json \
      --run-dynamic /tmp/opencode/TESTCASES-052t/sub-dynamic.json \
      --baseline-static  .work/tests/authoritative/<...>/run.json \
      --baseline-dynamic .work/tests/authoritative/<...>/run.json \
      --json-out /tmp/opencode/TESTCASES-052t/thread-report.json
"""

import argparse
import json
import sys

# The 19 target cases (TESTCASES-047t baseline: blocked with reason matching
# `__clone` / `posix_spawn` / `popen`, dynamic round).  Order = baseline order.
TARGET_CASES = [
    "functional/popen",
    "functional/spawn",
    "functional/pthread_cancel",
    "functional/pthread_cancel-points",
    "functional/pthread_cond",
    "functional/pthread_mutex",
    "functional/pthread_mutex_pi",
    "functional/pthread_robust",
    "functional/pthread_tsd",
    "functional/sem_init",
    "regression/pthread-robust-detach",
    "regression/pthread_cancel-sem_wait",
    "regression/pthread_cond-smasher",
    "regression/pthread_cond_wait-cancel_ignored",
    "regression/pthread_exit-cancel",
    "regression/pthread_exit-dtor",
    "regression/pthread_once-deadlock",
    "regression/pthread_rwlock-ebusy",
    "regression/raise-race",
]

# Thread-adjacent, but NOT one of the 19: its static-round outcome is the
# ISS-257 RLIMIT_AS/host-SIGTRAP flake, not a thread-capability signal.
EXTRA_CASES = ["regression/pthread_create-oom"]


def load_run(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def index_cases(doc, path, wanted):
    out = {}
    dup = []
    for case in doc.get("cases", []):
        cid = case.get("case")
        if cid not in wanted:
            continue
        if cid in out:
            dup.append(cid)
        out[cid] = case
    missing = [c for c in wanted if c not in out]
    if missing or dup:
        sys.stderr.write(
            f"report_thread_cases: FAIL — {path}: missing={missing} dup={dup}\n")
        sys.exit(2)
    return out


def klass_of(case):
    return case.get("klass", "?")


def reason_of(case):
    text = case.get("reason") or case.get("first_error") or ""
    return " ".join(text.split())[:160]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-static", required=True)
    ap.add_argument("--run-dynamic", required=True)
    ap.add_argument("--baseline-static", default=None)
    ap.add_argument("--baseline-dynamic", default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    wanted = TARGET_CASES + EXTRA_CASES
    if len(TARGET_CASES) != 19 or len(set(TARGET_CASES)) != 19:
        sys.stderr.write("report_thread_cases: FAIL — target list is not 19 unique cases\n")
        return 2

    rounds = {
        "static": (load_run(args.run_static),
                   load_run(args.baseline_static) if args.baseline_static else None),
        "dynamic": (load_run(args.run_dynamic),
                    load_run(args.baseline_dynamic) if args.baseline_dynamic else None),
    }

    report = {"target_cases": TARGET_CASES, "extra_cases": EXTRA_CASES, "rounds": {}}
    emit = (lambda *a: None) if args.quiet else print

    for mode, (run, baseline) in rounds.items():
        run_cases = index_cases(run, args.run_static if mode == "static" else args.run_dynamic, wanted)
        base_cases = (index_cases(baseline, f"baseline-{mode}", wanted)
                      if baseline else {})
        counts = {}
        drift = []
        rows = []
        for cid in wanted:
            case = run_cases[cid]
            new_k = klass_of(case)
            old_k = klass_of(base_cases[cid]) if cid in base_cases else "n/a"
            counts[new_k] = counts.get(new_k, 0) + 1
            if old_k != new_k:
                drift.append({"case": cid, "baseline": old_k, "run": new_k})
            rows.append({"case": cid,
                         "in_target_19": cid in TARGET_CASES,
                         "baseline_klass": old_k,
                         "klass": new_k,
                         "exit": case.get("exit"),
                         "reason": reason_of(case)})
        report["rounds"][mode] = {"counts": counts, "drift": drift, "cases": rows}

        emit(f"== {mode}: {len(wanted)} thread cases"
             f" (19 target + {len(EXTRA_CASES)} extra)")
        for row in rows:
            tag = "" if row["in_target_19"] else "  [not in 19]"
            emit(f"  {row['klass']:<10} exit={str(row['exit']):<5}"
                 f" {row['case']:<45} {row['baseline_klass']}->{row['klass']}{tag}")
            if row["klass"] != "pass":
                emit(f"      reason: {row['reason']}")
        emit(f"  counts (thread subset): {counts}")
        emit(f"  drift vs baseline: {len(drift)} case(s)")
        for d in drift:
            emit(f"    {d['case']}: {d['baseline']} -> {d['run']}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1, ensure_ascii=False)
            f.write("\n")
        emit(f"report: {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
