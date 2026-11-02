#!/usr/bin/env python3
"""Shared writer for the machine-readable report trio (night / L3).

Both ``night_run.py`` (``.dadao/tests/night/<date>/``) and ``l3_run.py``
(``.dadao/tests/l3/<UTC>/``) emit the same three files with the same manifest
semantics (``docs/Process-09 §4``/``§8``):

    manifest.tsv   scope<TAB>suite<TAB>rc<TAB>log   (one row per member)
    meta.json      command / started_utc / finished_utc / ...
    run.log        human summary (+ ``[exit marker] rc=N`` where applicable)

Keeping ``HEADER`` and the writer here is the single source of truth for the
format: a second hand-rolled writer would drift (``TESTCASES-083t``).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HEADER = ["scope", "suite", "rc", "log"]
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
STAMP_FORMAT = "%Y%m%dT%H%M%SZ"


def utc_now(when: datetime | None = None) -> str:
    """ISO-8601 UTC timestamp (``YYYY-MM-DDTHH:MM:SSZ``)."""
    return (when or datetime.now(timezone.utc)).strftime(ISO_FORMAT)


def utc_stamp(when: datetime | None = None) -> str:
    """Report directory stamp (``YYYYMMDDTHHMMSSZ``)."""
    return (when or datetime.now(timezone.utc)).strftime(STAMP_FORMAT)


def write_manifest(report: Path, rows: list[tuple[str, str, int, str]]) -> None:
    """Write ``manifest.tsv`` (header + one row per member)."""
    lines = ["\t".join(HEADER)]
    for scope, suite, rc, log in rows:
        lines.append(f"{scope}\t{suite}\t{rc}\t{log}")
    (report / "manifest.tsv").write_text("\n".join(lines) + "\n")


def write_meta(report: Path, meta: dict) -> None:
    """Write ``meta.json`` (UTF-8, stable formatting)."""
    (report / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
