#!/usr/bin/env python3
"""M1-gate issue blocker check + `resolved_by` field-constraint check.

Reads .tao/knowledge/issues.yaml and checks that no open issue blocks M1-gate.
Fail-closed: if the file is missing, exit 1.

字段约束（本文件头声明，INFRA-080t 起机械校验；用户 2026-10-14 裁定「A」= 两条都补、并入 L1）：
  - `status: closed` ⇒ `resolved_by` **必填**（非 null、非空串、非纯空白；任务号或明确文本均可）；
  - `status: open`   ⇒ `resolved_by` 应为 `null`（空串视为 null 等价）。

Usage: python3 tools/infra/check_issues.py
"""

import sys
import os

import yaml

ISSUES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".tao", "knowledge", "issues.yaml")


def _is_blank(value) -> bool:
    """True for None or a whitespace-only string (i.e. `resolved_by` 未填写)."""
    return value is None or (isinstance(value, str) and not value.strip())


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
    n_closed_missing = 0
    n_open_stale = 0
    errors = []

    for issue in issues:
        status = issue.get("status")
        resolved_by = issue.get("resolved_by")
        if status == "open":
            n_open += 1
            blocks = issue.get("blocks") or []
            if "M1-gate" in blocks:
                n_blocking += 1
                errors.append(
                    f"  BLOCKER: {issue['id']} — {issue['title']}"
                )
            # 字段约束：open ⇒ resolved_by 为 null（空串视为 null 等价）。
            if not _is_blank(resolved_by):
                n_open_stale += 1
                errors.append(
                    f"  UNEXPECTED resolved_by: {issue.get('id')} "
                    f"(status=open ⇒ resolved_by 应为 null，实为 {resolved_by!r})"
                )
        elif status == "closed":
            n_closed += 1
            # 字段约束：closed ⇒ resolved_by 必填（非 null/空串/纯空白）。
            if _is_blank(resolved_by):
                n_closed_missing += 1
                errors.append(
                    f"  MISSING resolved_by: {issue.get('id')} "
                    f"(status=closed ⇒ resolved_by 必填非空)"
                )
        else:
            errors.append(f"  INVALID STATUS: {issue.get('id')} has status '{status}'")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(
            f"check_issues: FAIL — {n_open} open, {n_closed} closed "
            f"({n_blocking} blocking M1-gate; "
            f"resolved_by: {n_closed_missing} closed 缺填 / {n_open_stale} open 非空)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"check_issues: {n_open} open, {n_closed} closed "
        f"({n_blocking} blocking M1-gate: 0)"
    )
    print(
        f"check_issues: resolved_by 约束 OK "
        f"({n_closed} closed → 非空 / {n_open} open → null)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
