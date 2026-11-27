#!/usr/bin/env python3
"""check_suite.py — verification entry of the kselftest suite (m18-linux-005).

Two jobs, both pointing at in-repo records rather than at a live run:

1. **Ledger/run consistency** — given a ``results.json`` produced by
   ``tools/linux/suite/run_suite.py``, re-run every suite check (baseline
   verdicts, triage ledger coverage, image manifest, derived counts).  Deleting
   a ledger row for a non-PASS case is red here.
2. **Patch applicability** — without any run: the adaptation patch manifest must
   match the locked kernel tree (upstream commit + per-file sha256) and the
   patch must still apply cleanly to a copy of the touched files; a patch that
   no longer applies is red here.

Usage:
  python3 tests/unit/linux/suite/check_suite.py --results <results.json>
  python3 tests/unit/linux/suite/check_suite.py --patches-only
  python3 tests/unit/linux/suite/check_suite.py --latest     # newest full-suite run

Exit: 0 = all checks pass, 1 = a check failed, 2 = setup error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.linux.suite import suite_cases   # noqa: E402
from tools.linux.suite import suite_checks  # noqa: E402
from tools.linux.suite import suite_paths   # noqa: E402


def latest_results(suite: str) -> Path:
    """Newest run that covers every case of the named suite's ``suite.yaml``.

    ``run_suite.py --only`` writes single-case runs (the fault-path evidence of
    m18-linux-014 makes nine of them per invocation).  A single-case run cannot
    satisfy S1/S3f -- the coverage checks describe the *suite*, not that run --
    so landing on one would report five failures that say nothing about the
    suite (F-R2).  ``--latest`` therefore skips those and picks the newest full
    run of *this* suite; ``--results <path>`` still takes any run on request.
    """
    wanted = {case.id for case in suite_cases.load_cases(suite_cases.suite_yaml(suite))}
    runs = sorted(suite_paths.runs_dir().glob("*/results.json"))
    full = [path for path in runs
            if wanted <= {case["id"]
                          for case in json.loads(path.read_text(encoding="utf-8"))["cases"]}]
    if not full:
        raise SystemExit(f"check_suite: no full-suite results.json for {suite} under "
                         f"{suite_paths.runs_dir()} (only single-case runs: "
                         f"{len(runs)}); run tools/linux/suite/run_suite.py "
                         f"--suite {suite} without --only first")
    return full[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default="kselftest",
                        choices=sorted(suite_cases.SUITES),
                        help="which suite's records to check (default: kselftest)")
    parser.add_argument("--results", type=Path, default=None,
                        help="results.json of the run to check")
    parser.add_argument("--latest", action="store_true",
                        help="use the newest run that covers every suite.yaml case "
                             "(single-case --only runs are skipped)")
    parser.add_argument("--patches-only", action="store_true",
                        help="only check the adaptation patch manifest/applicability "
                             "(kselftest) or the corpus provenance (ltp)")
    args = parser.parse_args()

    suite_yaml = suite_cases.suite_yaml(args.suite)
    failures: list[str] = []
    try:
        if args.patches_only:
            rep = suite_checks.Report()
            if args.suite == "ltp":
                suite_checks.check_ltp_source(rep)
            else:
                suite_checks.check_patches(rep)
            failures = rep.failures
        else:
            path = args.results or (latest_results(args.suite) if args.latest else None)
            if path is None:
                parser.error("give --results, --latest or --patches-only")
            if not path.is_file():
                raise SystemExit(f"check_suite: {path} not found")
            results = json.loads(path.read_text(encoding="utf-8"))
            failures = suite_checks.run_checks(results, path, suite_yaml)
    except (suite_cases.SuiteError, suite_checks.CheckError) as exc:
        print(f"check_suite: SETUP ERROR: {exc}", file=sys.stderr)
        return 2

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}", file=sys.stderr)
        print(f"check_suite: FAIL ({len(failures)} check(s))", file=sys.stderr)
        return 1
    print("check_suite: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
