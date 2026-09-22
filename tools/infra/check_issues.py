#!/usr/bin/env python3
"""M1-gate issue blocker check.

Reads docs/issues.yaml and checks that no open issue blocks M1-gate.
Fail-closed: if the file is missing, exit 1.

Usage: python3 tools/infra/check_issues.py
"""

import sys
import os

import yaml

ISSUES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "issues.yaml")


def main():
    # Fail-closed: missing file → exit 1
    if not os.path.isfile(ISSUES_PATH):
        print(f"check_issues: FAIL — {ISSUES_PATH} not found (fail-closed)", file=sys.stderr)
        sys.exit(1)

    with open(ISSUES_PATH, "r", encoding="utf-8") as f:
        issues = yaml.safe_load(f)

    if not isinstance(issues, list):
        print("check_issues: FAIL — issues.yaml must be a list", file=sys.stderr)
        sys.exit(1)

    n_open = 0
    n_closed = 0
    n_blocking = 0
    errors = []

    for issue in issues:
        status = issue.get("status")
        if status == "open":
            n_open += 1
            blocks = issue.get("blocks") or []
            if "M1-gate" in blocks:
                n_blocking += 1
                errors.append(
                    f"  BLOCKER: {issue['id']} — {issue['title']}"
                )
        elif status == "closed":
            n_closed += 1
        else:
            errors.append(f"  INVALID STATUS: {issue.get('id')} has status '{status}'")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(
            f"check_issues: FAIL — {n_open} open, {n_closed} closed "
            f"({n_blocking} blocking M1-gate)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"check_issues: {n_open} open, {n_closed} closed "
        f"({n_blocking} blocking M1-gate: 0)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
