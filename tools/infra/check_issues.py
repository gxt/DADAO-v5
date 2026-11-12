#!/usr/bin/env python3
"""`resolved_by` field-constraint check.

Reads .tao/knowledge/issues.yaml and checks the `status` / `resolved_by` field
constraints only.  The M1 stage's issue-blocking gate is retired: M1 was
reached 2026-09-22 and no gate is in force, so the `blocks` field stays a
descriptive slot that takes no part in the verdict (`INFRA-113t`).
Fail-closed: if the file is missing, exit 1.

字段约束（本文件头声明，INFRA-080t 起机械校验；用户 2026-10-14 裁定「A」= 两条都补、并入 L1）：
  - `status: closed` ⇒ `resolved_by` **必填**（非 null、非空串、非纯空白；任务号或明确文本均可）；
  - `status: closed` ⇒ `closed_in` **必填**，形如 `M13`（里程碑编号，供归档直接按里程碑取集）；
  - `status: open`   ⇒ `resolved_by` 与 `closed_in` 均应为 `null`（空串视为 null 等价）。

Usage: python3 tools/infra/check_issues.py
"""

import re
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
    n_closed_missing = 0
    n_closed_bad_ms = 0
    n_open_stale = 0
    n_open_ms = 0
    errors = []

    for issue in issues:
        status = issue.get("status")
        resolved_by = issue.get("resolved_by")
        closed_in = issue.get("closed_in")
        if status == "open":
            n_open += 1
            # 字段约束：open ⇒ resolved_by 为 null（空串视为 null 等价）。
            if not _is_blank(resolved_by):
                n_open_stale += 1
                errors.append(
                    f"  UNEXPECTED resolved_by: {issue.get('id')} "
                    f"(status=open ⇒ resolved_by 应为 null，实为 {resolved_by!r})"
                )
            # 字段约束：open ⇒ closed_in 为 null。
            if not _is_blank(closed_in):
                n_open_ms += 1
                errors.append(
                    f"  UNEXPECTED closed_in: {issue.get('id')} "
                    f"(status=open ⇒ closed_in 应为 null，实为 {closed_in!r})"
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
            # 字段约束：closed ⇒ closed_in 必填且形如 M<数字>。
            if _is_blank(closed_in):
                n_closed_bad_ms += 1
                errors.append(
                    f"  MISSING closed_in: {issue.get('id')} "
                    f"(status=closed ⇒ closed_in 必填，形如 'M13')"
                )
            elif not re.fullmatch(r"M\d+", str(closed_in)):
                n_closed_bad_ms += 1
                errors.append(
                    f"  BAD closed_in: {issue.get('id')} "
                    f"(应为 'M<数字>'，实为 {closed_in!r})"
                )
        else:
            errors.append(f"  INVALID STATUS: {issue.get('id')} has status '{status}'")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(
            f"check_issues: FAIL — {n_open} open, {n_closed} closed "
            f"(resolved_by: {n_closed_missing} closed 缺填 / "
            f"{n_open_stale} open 非空; "
            f"closed_in: {n_closed_bad_ms} closed 缺填或非法 / "
            f"{n_open_ms} open 非空)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"check_issues: {n_open} open, {n_closed} closed")
    print(
        f"check_issues: resolved_by / closed_in 约束 OK "
        f"({n_closed} closed → 非空+M<i> / {n_open} open → null)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
