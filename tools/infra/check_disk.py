#!/usr/bin/env python3
"""Disk guard: warn when a filesystem holding a path crosses a threshold.

User rule (2026-11-10): before scheduling evaluation/test jobs on the master or
on a node, check free space first; above 90% must raise an alarm.

Usage:
  python3 tools/infra/check_disk.py [--path PATH ...] [--threshold 90]

Exit codes: 0 = all paths under threshold, 1 = at least one path over threshold.
This is an operational guard (not a gate): it prints one line per filesystem so
the result can be quoted verbatim in a dispatch note.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

DEFAULT_PATHS = ["."]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", action="append", default=None,
                    help="path to check (repeatable; default: repo root)")
    ap.add_argument("--threshold", type=float, default=90.0,
                    help="percent used that triggers ALERT (default 90)")
    args = ap.parse_args(argv)

    paths = args.path or DEFAULT_PATHS
    seen: dict[str, tuple[str, float]] = {}
    for raw in paths:
        path = os.path.abspath(raw)
        try:
            usage = shutil.disk_usage(path)
        except OSError as exc:
            print(f"check-disk: ERROR {path}: {exc}", file=sys.stderr)
            return 2
        total = usage.total / (1024 ** 3)
        used = usage.used / (1024 ** 3)
        # match `df` semantics: reserved blocks are not counted as free
        denom = usage.used + usage.free
        pct = (usage.used / denom * 100.0) if denom else 0.0
        dev = os.stat(path).st_dev
        key = f"dev:{dev}"
        if key in seen:
            continue
        seen[key] = (path, pct)
        state = "ALERT" if pct >= args.threshold else "ok"
        print(f"check-disk: {state} {path} used={pct:.0f}% "
              f"({used:.0f}G/{total:.0f}G, threshold {args.threshold:.0f}%)")

    worst = max(pct for _, pct in seen.values())
    if worst >= args.threshold:
        print(f"check-disk: FAIL (max {worst:.0f}% >= {args.threshold:.0f}%) "
              "— clean before scheduling jobs", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
