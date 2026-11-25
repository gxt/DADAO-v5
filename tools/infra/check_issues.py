#!/usr/bin/env python3
"""`resolved_by` field-constraint check.

Reads the per-milestone ledgers ``.tao/knowledge/issues-*.yaml`` (split from the
former single ``issues.yaml``, user ruling 2026-11-25) and checks the
`status` / `resolved_by` field constraints, the ID shape, global ID uniqueness and
that every entry sits in the ledger that owns its milestone.  The M1 stage's issue-blocking gate is retired: M1 was
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

import issues_store

#: 分册前就存在的重复编号（用户 2026-11-25 裁定：存量条目不重编）。它们必须
#: 逐条列在这里，**新增**重复一律失败；一旦某条不再重复（被人工去重）也必须
#: 从这里删掉，否则判「陈旧登记」——列表因此不能悄悄扩大。
KNOWN_LEGACY_DUPLICATES = {
    "ISS-518": 2,  # M16 / M17（两册各一条）
    "ISS-530": 2,  # M16 / M18
    "ISS-536": 2,  # M16 / M18
    "ISS-537": 2,  # M16 / M17
    "ISS-538": 2,  # M16 / M18
    "ISS-539": 2,  # M16 / M18
}


def _is_blank(value) -> bool:
    """True for None or a whitespace-only string (i.e. `resolved_by` 未填写)."""
    return value is None or (isinstance(value, str) and not value.strip())


def main():
    # Fail-closed: missing ledgers → exit 1.
    try:
        pairs = issues_store.load_all_with_file()
    except SystemExit as exc:  # issues_store raises SystemExit with a message
        print(f"check_issues: FAIL — {exc}", file=sys.stderr)
        sys.exit(1)
    issues = [issue for _, issue in pairs]

    # 分册规则（用户 2026-11-25）：ID 全局唯一、两种格式并存、
    # 且 m16–m19 文件里的条目里程碑必须与文件一致（left 收一切无归属项）。
    seen_ids: dict[str, str] = {}
    seen_legacy: dict[str, int] = {}
    n_id_dup = 0
    n_id_shape = 0
    n_ledger_mismatch = 0
    for path, issue in pairs:
        key = issues_store.file_key(path)
        issue_id = str(issue.get("id"))
        if issue_id in seen_ids:
            if issue_id in KNOWN_LEGACY_DUPLICATES:
                seen_legacy[issue_id] = seen_legacy.get(issue_id, 1) + 1
                errors_id = None
            else:
                n_id_dup += 1
                errors_id = (f"  DUPLICATE id: {issue_id} in {path.name} "
                             f"(first seen in {seen_ids[issue_id]})")
        else:
            seen_ids[issue_id] = path.name
            errors_id = None
        old = re.fullmatch(r"ISS-\d+", issue_id)
        new = re.fullmatch(r"ISS-([a-z0-9]+)-(\d{3,})", issue_id)
        if not old and not new:
            n_id_shape += 1
            shape_err = (f"  BAD id shape: {issue_id} in {path.name} "
                         f"(expected ISS-<digits> or ISS-<file>-NNN)")
        elif new and new.group(1) != key:
            n_id_shape += 1
            shape_err = (f"  BAD id prefix: {issue_id} in {path.name} "
                         f"(new-shape IDs must carry this file's key '{key}')")
        else:
            shape_err = None
        ms = str(issue.get("milestone") or "").upper()
        if key == "left":
            bad_ledger = ms in issues_store.MILESTONES
        else:
            bad_ledger = ms != key.upper()
        if bad_ledger:
            n_ledger_mismatch += 1
            ledger_err = (f"  LEDGER MISMATCH: {issue_id} in {path.name} "
                          f"(milestone={issue.get('milestone')!r})")
        else:
            ledger_err = None
        id_errors = [e for e in (errors_id, shape_err, ledger_err) if e]
        for e in id_errors:
            print(e, file=sys.stderr)

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

    for legacy, count in sorted(KNOWN_LEGACY_DUPLICATES.items()):
        if seen_legacy.get(legacy, 1) != count:
            n_id_dup += 1
            print(f"  STALE legacy-duplicate entry: {legacy} "
                  f"(registered {count}×, now {seen_legacy.get(legacy, 1)}×) — "
                  f"去重后请从 KNOWN_LEGACY_DUPLICATES 删除该行", file=sys.stderr)

    if n_id_dup or n_id_shape or n_ledger_mismatch:
        print(
            f"check_issues: FAIL — 分册规则: id 重复 {n_id_dup} / "
            f"id 形状或前缀 {n_id_shape} / 文件与里程碑不符 {n_ledger_mismatch}",
            file=sys.stderr,
        )
        sys.exit(1)

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

    if seen_legacy:
        print(f"check_issues: 存量重复编号 {len(seen_legacy)} 个（已登记、冻结）："
              f"{', '.join(sorted(seen_legacy))}")
    print(f"check_issues: {n_open} open, {n_closed} closed "
          f"({len(pairs)} entries in {len(issues_store.paths())} ledgers)")
    print(
        f"check_issues: resolved_by / closed_in 约束 OK "
        f"({n_closed} closed → 非空+M<i> / {n_open} open → null)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
