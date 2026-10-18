#!/usr/bin/env python3
"""Run-directory artifacts for the user-mode suite drivers (INFRA-093t).

Every driver invocation gets its own run directory::

    <work-dir>/<YYYYMMDDTHHMMSSZ>-<suite>-<mode>/
        run.json   per-case results (same object written to --json-out)
        run.log    human-readable report
        meta.json  command line, UTC start/finish, toolchain sha256

A run directory is **never** reused: if the current-second timestamp already
exists, the helper waits for the next second instead of appending a suffix
(the directory-name shape is part of the contract, see docs/Process-08).

``--json-out`` remains the caller-visible results file; ``--report-out``
defaults to the same directory, same stem, ``.log`` extension.  The run
directory above is the durable, per-invocation record.

No third-party imports: this must run with the plain host Python.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone

RUN_TS_FORMAT = "%Y%m%dT%H%M%SZ"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_stamp(when: datetime | None = None) -> str:
    """Directory timestamp (``YYYYMMDDTHHMMSSZ``); UTC, second resolution."""
    return (when or datetime.now(timezone.utc)).strftime(RUN_TS_FORMAT)


def iso_utc(when: datetime | None = None) -> str:
    """ISO-8601 UTC timestamp for meta.json (``YYYY-MM-DDTHH:MM:SSZ``)."""
    return (when or datetime.now(timezone.utc)).strftime(ISO_FORMAT)


def sha256_file(path: str | None) -> str | None:
    """Streaming sha256 of *path*; ``None`` when the file is absent."""
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tool_entry(path: str | None) -> dict:
    ap = os.path.abspath(path) if path else None
    return {"path": ap, "sha256": sha256_file(ap)}


def toolchain_summary(clang: str, lld: str | None, qemu: str,
                      libc: str, musl_dir: str | None = None) -> dict:
    """Toolchain identity for meta.json.

    ``clang`` / ``qemu`` / ``libc`` are required by gate A2 (non-empty sha256
    or md5); ``lld`` and both libc flavours are recorded when present.
    """
    summary = {
        "clang": _tool_entry(clang),
        "lld": _tool_entry(lld),
        "qemu": _tool_entry(qemu),
        "libc": _tool_entry(libc),
    }
    if musl_dir:
        for name in ("libc.a", "libc.so"):
            key = name.replace(".", "_")
            summary[key] = _tool_entry(os.path.join(musl_dir, "lib", name))
    return summary


def create_run_dir(work_dir: str, suite: str, mode: str,
                   started: datetime | None = None) -> str:
    """Create the per-invocation run directory and return its path.

    Two runs must never share a directory.  A same-second collision waits for
    the next second (bounded) rather than reusing or suffixing the name:
    the ``<UTC>-<suite>-<mode>`` shape is contractual.
    """
    root = os.path.abspath(work_dir)
    os.makedirs(root, exist_ok=True)
    when = started or datetime.now(timezone.utc)
    for _ in range(5):
        candidate = os.path.join(root, f"{utc_stamp(when)}-{suite}-{mode}")
        try:
            os.makedirs(candidate)
        except FileExistsError:
            time.sleep(1)
            when = datetime.now(timezone.utc)
            continue
        return candidate
    raise RuntimeError(
        f"cannot allocate a unique run directory under {root} "
        f"for {suite}/{mode} (5 timestamps collided)")


def build_meta(argv: list[str], suite: str, mode: str, run_dir: str,
               started_utc: str, toolchain: dict) -> dict:
    """meta.json payload: command, UTC start/finish, toolchain digests."""
    finished = iso_utc()
    try:
        begin = datetime.strptime(started_utc, ISO_FORMAT).replace(
            tzinfo=timezone.utc)
        elapsed = max(0.0, (datetime.now(timezone.utc) - begin).total_seconds())
    except ValueError:
        elapsed = None
    return {
        "suite": suite,
        "mode": mode,
        "run_dir": os.path.abspath(run_dir),
        "driver": os.path.abspath(argv[0]) if argv else None,
        "command": [os.path.abspath(argv[0])] + list(argv[1:]) if argv else [],
        "cwd": os.getcwd(),
        "started_utc": started_utc,
        "finished_utc": finished,
        "duration_seconds": elapsed,
        "toolchain": toolchain,
    }


def _write_text(path: str, text: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def write_run_dir(run_dir: str, record: dict, report_text: str, meta: dict,
                  json_path: str | None = None,
                  report_path: str | None = None) -> dict:
    """Write run.json/run.log/meta.json, then the caller-facing copies.

    The run directory is the primary record; ``json_path`` / ``report_path``
    (if given) receive the same bytes so existing consumers keep working.
    """
    os.makedirs(run_dir, exist_ok=True)
    json_text = json.dumps(record, indent=2) + "\n"
    _write_text(os.path.join(run_dir, "run.json"), json_text)
    _write_text(os.path.join(run_dir, "run.log"), report_text)
    _write_text(os.path.join(run_dir, "meta.json"),
                json.dumps(meta, indent=2) + "\n")
    if json_path:
        _write_text(os.path.abspath(json_path), json_text)
    if report_path:
        _write_text(os.path.abspath(report_path), report_text)
    return {"run_dir": os.path.abspath(run_dir),
            "run_json": os.path.join(os.path.abspath(run_dir), "run.json"),
            "run_log": os.path.join(os.path.abspath(run_dir), "run.log"),
            "meta": os.path.join(os.path.abspath(run_dir), "meta.json")}
