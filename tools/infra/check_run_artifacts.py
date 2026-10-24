#!/usr/bin/env python3
"""L1 gate: test-run artifacts and log naming (INFRA-093t).

Assertions (rules = docs/Process-08-测试运行产物与日志组织规范.md):

A1  the three user-mode drivers have no fixed output fallback
    - ``--json-out`` is ``required=True`` (argparse)
    - ``DEFAULT_LOG_DIR`` no longer appears in the source
    - ``--report-out`` is derived from ``--json-out`` (same stem + ``.log``)
    - the driver uses the per-run directory helper (``create_run_dir``)
A2  every run directory (``^\\d{8}T\\d{6}Z-``) under ``.work/tests/**`` (and the
    configured test-artifacts root) carries ``run.json`` / ``run.log`` /
    ``meta.json``; ``meta.json`` has a non-empty ``command``, ``started_utc``,
    ``finished_utc`` and a ``toolchain`` block whose ``clang`` / ``qemu`` /
    ``libc`` entries each carry a non-empty sha256 (or md5).
    ``authoritative/latest`` must point at an existing directory.  No run root
    at all => SKIP, printed.
A3  files added to ``.work/log/**`` after the epoch marker
    (``.work/log/.run-artifacts-epoch``) must be named either
    ``check-<name>.log`` or ``<TASK-ID>-<purpose>.(log|json|txt)``.
    Files present at landing (snapshot in ``.run-artifacts-baseline``) and
    files with ``mtime <= epoch`` are exempt.  No marker => SKIP, printed.
    The in-flight legacy ``llvm-ts-user-*`` files of the current dynamic run
    are explicitly exempt until the separate migration task moves them.
    ``--legacy-status`` is the mechanical criterion for deleting that
    exemption: rc=0 (no legacy files left) => delete ``INFLIGHT_LEGACY``;
    rc=1 (files remain) => keep it (ISS-282 ③).

Exit: 0 = PASS (or documented SKIP), 1 = FAIL.  ``--self-test`` runs each
assertion's injection: baseline green, then one injected counter-example per
assertion must turn red.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

DRIVERS = (
    "run_libc_test_user_suite.py",
    "run_llvm_ts_user.py",
    "run_embench_user_suite.py",
)
RUN_DIR_RE = re.compile(r"^\d{8}T\d{6}Z-")
TASK_ID = r"(?:INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG)-\d{3}[a-z]?"
LEGAL_LOG_NAMES = (
    re.compile(r"^check-[A-Za-z0-9][A-Za-z0-9._-]*\.log$"),
    re.compile(rf"^{TASK_ID}-[A-Za-z0-9][A-Za-z0-9._-]*\.(?:log|json|txt)$"),
)
# Temporary exemption: the dynamic run that was already in flight when this
# gate landed writes these legacy fixed names.  Removed by the migration task.
INFLIGHT_LEGACY = re.compile(
    r"^llvm-ts-user-[A-Za-z0-9._-]+\.(?:json|log|stdout|stderr)$")
LOG_MARKER = ".run-artifacts-epoch"
LOG_BASELINE = ".run-artifacts-baseline"
EPOCH_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _driver_dir(root: str | None) -> str:
    if root:
        return os.path.join(root, "tools", "testcases")
    return os.path.join(REPO_ROOT, "tools", "testcases")


# ---------------------------------------------------------------------------
# A1 -- drivers have no fixed default output path
# ---------------------------------------------------------------------------

def check_a1(root: str | None, out) -> list[str]:
    problems = []
    ddir = _driver_dir(root)
    for name in DRIVERS:
        local = []
        path = os.path.join(ddir, name)
        if not os.path.isfile(path):
            local.append(f"A1 {name}: driver not found at {path}")
            problems += local
            for p in local:
                out(f"[FAIL] {p}")
            continue
        text = _read(path)
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            local.append(f"A1 {name}: cannot parse source ({exc})")
            problems += local
            for p in local:
                out(f"[FAIL] {p}")
            continue
        json_arg = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute)
                    and func.attr == "add_argument"):
                continue
            if not node.args:
                continue
            first = node.args[0]
            if (isinstance(first, ast.Constant)
                    and first.value == "--json-out"):
                json_arg = node
                break
        if json_arg is None:
            local.append(f"A1 {name}: no --json-out argument")
        else:
            required = None
            for kw in json_arg.keywords:
                if kw.arg == "required" and isinstance(kw.value, ast.Constant):
                    required = kw.value.value
            if required is not True:
                local.append(
                    f"A1 {name}: --json-out is not required=True "
                    f"(required={required!r})")
        if "DEFAULT_LOG_DIR" in text:
            local.append(
                f"A1 {name}: DEFAULT_LOG_DIR is still present "
                "(no fixed output fallback allowed)")
        if not re.search(
                r"os\.path\.splitext\(json_out\)\[0\]\s*\+\s*"
                r"[\"']\.log[\"']", text):
            local.append(
                f"A1 {name}: --report-out default is not derived from "
                "--json-out (expected splitext(json_out)[0] + '.log')")
        if "create_run_dir" not in text:
            local.append(
                f"A1 {name}: no per-run directory creation "
                "(create_run_dir) found")
        if local:
            problems += local
            for p in local:
                out(f"[FAIL] {p}")
        else:
            out(f"[PASS] A1 {name}")
    return problems


# ---------------------------------------------------------------------------
# A2 -- run directories carry the three-piece artifact set
# ---------------------------------------------------------------------------

def _hash_nonempty(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(isinstance(value.get(key), str) and value[key].strip()
                   for key in ("sha256", "md5"))
    return False


def _meta_problems(meta_path: str) -> list[str]:
    problems = []
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"meta.json unreadable: {exc}"]
    command = meta.get("command")
    ok_command = (isinstance(command, list) and len(command) > 0) or \
        (isinstance(command, str) and bool(command.strip()))
    if not ok_command:
        problems.append("meta.json: empty command")
    if not (isinstance(meta.get("started_utc"), str)
            and meta["started_utc"].strip()):
        problems.append("meta.json: missing started_utc")
    if not (isinstance(meta.get("finished_utc"), str)
            and meta["finished_utc"].strip()):
        problems.append("meta.json: missing finished_utc")
    toolchain = meta.get("toolchain")
    if not isinstance(toolchain, dict):
        problems.append("meta.json: missing toolchain block")
    else:
        for key in ("clang", "qemu", "libc"):
            if not _hash_nonempty(toolchain.get(key)):
                problems.append(
                    f"meta.json: toolchain.{key} has no non-empty "
                    "sha256/md5")
    return problems


def _run_roots(root: str | None) -> list[str]:
    if root:
        return [os.path.join(root, ".work", "tests")]
    roots = [os.path.join(REPO_ROOT, ".work", "tests")]
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
        import paths  # noqa: PLC0415
        roots.append(str(paths.test_artifacts_dir()))
    except Exception:
        pass
    seen, unique = set(), []
    for item in roots:
        real = os.path.abspath(item)
        if real not in seen:
            seen.add(real)
            unique.append(real)
    return unique


def check_a2(root: str | None, out) -> list[str]:
    problems = []
    roots = [r for r in _run_roots(root) if os.path.isdir(r)]
    if not roots:
        out("[SKIP] A2 no run-artifact root present "
            "(.work/tests or configured test-artifacts dir)")
        return problems
    run_dirs = []
    for base in roots:
        for dirpath, dirnames, _files in os.walk(base):
            if RUN_DIR_RE.match(os.path.basename(dirpath)):
                run_dirs.append(dirpath)
                dirnames[:] = []
    if not run_dirs:
        out(f"[PASS] A2 no run directories yet under "
            f"{', '.join(roots)} (0 checked)")
    for run_dir in run_dirs:
        local = []
        rel = os.path.relpath(run_dir, root or REPO_ROOT)
        missing = [name for name in ("run.json", "run.log", "meta.json")
                   if not os.path.isfile(os.path.join(run_dir, name))]
        if missing:
            local.append(f"A2 {rel}: missing {', '.join(missing)}")
            problems += local
            for p in local:
                out(f"[FAIL] {p}")
            continue
        for name in ("run.json", "run.log"):
            if os.path.getsize(os.path.join(run_dir, name)) == 0:
                local.append(f"A2 {rel}: empty {name}")
        for detail in _meta_problems(os.path.join(run_dir, "meta.json")):
            local.append(f"A2 {rel}: {detail}")
        if local:
            problems += local
            for p in local:
                out(f"[FAIL] {p}")
        else:
            out(f"[PASS] A2 {rel}")
    # authoritative/latest pointer (only when an authoritative set exists)
    for base in roots:
        auth = os.path.join(base, "authoritative")
        if not os.path.isdir(auth):
            continue
        latest = os.path.join(auth, "latest")
        rel_auth = os.path.relpath(auth, root or REPO_ROOT)
        if not os.path.lexists(latest):
            problems.append(f"A2 {rel_auth}/latest is missing")
            continue
        if os.path.islink(latest):
            target = os.path.realpath(latest)
        elif os.path.isfile(latest):
            raw = _read(latest).strip()
            target = os.path.realpath(
                raw if os.path.isabs(raw) else os.path.join(auth, raw))
        else:
            target = latest
        if not os.path.isdir(target):
            problems.append(
                f"A2 {rel_auth}/latest does not point at a directory "
                f"({target})")
        else:
            out(f"[PASS] A2 {rel_auth}/latest -> {target}")
    return problems


# ---------------------------------------------------------------------------
# A3 -- new .work/log files follow the naming rules
# ---------------------------------------------------------------------------

def _parse_epoch(text: str) -> float:
    stamp = text.strip().splitlines()[0].strip()
    for fmt in EPOCH_FORMATS:
        try:
            return datetime.strptime(stamp, fmt).replace(
                tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    try:
        return float(stamp)
    except ValueError:
        raise ValueError(f"unparseable epoch marker content: {stamp!r}")


def check_a3(root: str | None, out) -> list[str]:
    problems = []
    base = (os.path.join(root, ".work", "log") if root
            else os.path.join(REPO_ROOT, ".work", "log"))
    marker = os.path.join(base, LOG_MARKER)
    if not os.path.isdir(base) or not os.path.isfile(marker):
        out(f"[SKIP] A3 no epoch marker ({LOG_MARKER}); "
            "existing logs are not judged")
        return problems
    try:
        epoch = _parse_epoch(_read(marker))
    except ValueError as exc:
        return [f"A3 {exc}"]
    baseline = set()
    baseline_path = os.path.join(base, LOG_BASELINE)
    if os.path.isfile(baseline_path):
        baseline = {line.strip() for line in
                    _read(baseline_path).splitlines() if line.strip()}
    checked = exempt = bad = 0
    legacy = 0
    for dirpath, _dirnames, filenames in os.walk(base):
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, base)
            if name in (LOG_MARKER, LOG_BASELINE):
                continue
            if rel in baseline:
                exempt += 1
                continue
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime <= epoch:
                exempt += 1
                continue
            if INFLIGHT_LEGACY.match(name):
                exempt += 1
                legacy += 1
                continue
            checked += 1
            if not any(rx.match(name) for rx in LEGAL_LOG_NAMES):
                bad += 1
                problems.append(
                    f"A3 .work/log/{rel}: illegal name (expected "
                    "check-<name>.log or <TASK-ID>-<purpose>.(log|json|txt))")
    if bad:
        out(f"[FAIL] A3 {checked} new file(s) checked, {bad} illegal, "
            f"{exempt} exempt (epoch/baseline/legacy; legacy={legacy})")
    else:
        out(f"[PASS] A3 {checked} new file(s) checked, {bad} illegal, "
            f"{exempt} exempt (epoch/baseline/legacy; legacy={legacy})")
    return problems


def legacy_status(root: str | None = None) -> int:
    """Mechanical criterion for deleting the ``INFLIGHT_LEGACY`` exemption.

    ``rc=0``: no ``llvm-ts-user-*`` file is left under ``.work/log/**`` => the
    migration (ISS-278 second step) is complete and ``INFLIGHT_LEGACY`` must
    be deleted together with this subcommand.  ``rc=1``: files remain => the
    exemption is still load-bearing; keep it and do not widen it.
    """
    base = (os.path.join(root, ".work", "log") if root
            else os.path.join(REPO_ROOT, ".work", "log"))
    remaining = []
    for dirpath, _dirnames, filenames in os.walk(base):
        for name in filenames:
            if INFLIGHT_LEGACY.match(name):
                remaining.append(os.path.relpath(
                    os.path.join(dirpath, name), base))
    if remaining:
        print(f"legacy-status: FAIL ({len(remaining)} llvm-ts-user-* file(s) "
              "remain; keep INFLIGHT_LEGACY)")
        for rel in remaining[:10]:
            print(f"  .work/log/{rel}")
        if len(remaining) > 10:
            print(f"  ... and {len(remaining) - 10} more")
        return 1
    print("legacy-status: PASS (no llvm-ts-user-* file left; delete "
          "INFLIGHT_LEGACY and this subcommand)")
    return 0


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_checks(root: str | None, out=print) -> list[str]:
    problems = []
    problems += check_a1(root, out)
    problems += check_a2(root, out)
    problems += check_a3(root, out)
    return problems


def _make_tree(base: str) -> str:
    return tempfile.mkdtemp(prefix="run-artifacts-", dir=base)


def _write(path: str, text: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _clean_tree(tree: str) -> None:
    src = os.path.join(REPO_ROOT, "tools", "testcases")
    dst = os.path.join(tree, "tools", "testcases")
    os.makedirs(dst, exist_ok=True)
    for name in DRIVERS:
        shutil.copyfile(os.path.join(src, name), os.path.join(dst, name))
    # One valid run directory + authoritative latest pointer.
    run = os.path.join(tree, ".work", "tests", "20260101T000000Z-demo-static")
    os.makedirs(run)
    _write(os.path.join(run, "run.json"), "{}\n")
    _write(os.path.join(run, "run.log"), "demo\n")
    _write(os.path.join(run, "meta.json"), json.dumps({
        "command": ["python3", "driver.py", "--link-mode", "static"],
        "started_utc": "2026-01-01T00:00:00Z",
        "finished_utc": "2026-01-01T00:00:01Z",
        "toolchain": {
            "clang": {"path": "/x/clang", "sha256": "a" * 64},
            "qemu": {"path": "/x/qemu-dadao", "sha256": "b" * 64},
            "libc": {"path": "/x/libc.a", "sha256": "c" * 64},
        },
    }) + "\n")
    auth = os.path.join(tree, ".work", "tests", "authoritative")
    os.makedirs(auth)
    os.symlink(os.path.join("..", "20260101T000000Z-demo-static"),
               os.path.join(auth, "latest"))
    # Epoch: safely in the past; logs created now are "new".
    log = os.path.join(tree, ".work", "log")
    os.makedirs(os.path.join(log, "testcases"), exist_ok=True)
    stamp = (datetime.now(timezone.utc) - timedelta(seconds=120)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    _write(os.path.join(log, LOG_MARKER), stamp + "\n")
    _write(os.path.join(log, LOG_BASELINE), "")
    _write(os.path.join(log, "check-demo.log"), "ok\n")
    _write(os.path.join(log, "testcases", "INFRA-093t-demo.log"), "ok\n")


def self_test(base: str) -> int:
    os.makedirs(base, exist_ok=True)
    outcomes = []

    def fresh():
        tree = _make_tree(base)
        _clean_tree(tree)
        return tree

    # 1. clean baseline must be green.
    tree = fresh()
    out = []
    rc = 1 if run_checks(tree, out.append) else 0
    outcomes.append(("clean baseline", 0, rc))
    shutil.rmtree(tree, ignore_errors=True)

    # 2. A1: --json-out loses required=True.
    tree = fresh()
    path = os.path.join(tree, "tools", "testcases",
                        "run_libc_test_user_suite.py")
    text = _read(path)
    injected = text.replace('"--json-out", required=True',
                            '"--json-out", default=None', 1)
    assert injected != text, "A1 injection did not apply"
    _write(path, injected)
    out = []
    rc = 1 if run_checks(tree, out.append) else 0
    outcomes.append(("A1 required=True removed", 1, rc))
    shutil.rmtree(tree, ignore_errors=True)

    # 3. A1: a fixed DEFAULT_LOG_DIR fallback reappears.
    tree = fresh()
    path = os.path.join(tree, "tools", "testcases", "run_llvm_ts_user.py")
    _write(path, _read(path) + '\nDEFAULT_LOG_DIR = ".work/log/testcases"\n')
    out = []
    rc = 1 if run_checks(tree, out.append) else 0
    outcomes.append(("A1 fixed fallback reappears", 1, rc))
    shutil.rmtree(tree, ignore_errors=True)

    # 4. A2: a run directory without meta.json.
    tree = fresh()
    broken = os.path.join(tree, ".work", "tests",
                          "20260102T000000Z-broken-static")
    os.makedirs(broken)
    _write(os.path.join(broken, "run.json"), "{}\n")
    _write(os.path.join(broken, "run.log"), "x\n")
    out = []
    rc = 1 if run_checks(tree, out.append) else 0
    outcomes.append(("A2 missing meta.json", 1, rc))
    shutil.rmtree(tree, ignore_errors=True)

    # 5. A2: meta.json without finished_utc (Process-08 §1.1 requires it).
    tree = fresh()
    meta_path = os.path.join(tree, ".work", "tests",
                             "20260101T000000Z-demo-static", "meta.json")
    meta = json.loads(_read(meta_path))
    meta.pop("finished_utc")
    _write(meta_path, json.dumps(meta) + "\n")
    out = []
    rc = 1 if run_checks(tree, out.append) else 0
    outcomes.append(("A2 missing finished_utc", 1, rc))
    shutil.rmtree(tree, ignore_errors=True)

    # 6. A3: an illegal new log name under .work/log.
    tree = fresh()
    _write(os.path.join(tree, ".work", "log", "testcases",
                        "check_issues.log"), "x\n")
    out = []
    rc = 1 if run_checks(tree, out.append) else 0
    outcomes.append(("A3 illegal log name", 1, rc))
    shutil.rmtree(tree, ignore_errors=True)

    ok = True
    for name, want, got in outcomes:
        verdict = "PASS" if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"[SELFTEST] {name}: expected rc={want} actual rc={got} "
              f"=> {verdict}")
    print("check-run-artifacts --self-test: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="INFRA-093t: run artifacts + log naming gate (L1)")
    ap.add_argument("--root", default=None,
                    help="temporary tree for self-test/CI (default: repo)")
    ap.add_argument("--self-test", action="store_true",
                    help="run baseline + one injected counter-example per "
                         "assertion")
    ap.add_argument("--legacy-status", action="store_true",
                    help="mechanical criterion for the INFLIGHT_LEGACY "
                         "exemption (ISS-282 ③): rc=0 => no llvm-ts-user-* "
                         "file left, delete the exemption; rc=1 => keep it")
    args = ap.parse_args()
    if args.legacy_status:
        return legacy_status(args.root)
    if args.self_test:
        base = os.environ.get("DADAO_TMP",
                              "/tmp/opencode/INFRA-093t")
        return self_test(base)
    problems = run_checks(args.root)
    if problems:
        print(f"check-run-artifacts: FAIL ({len(problems)} problem(s))")
        for p in problems:
            print("  " + p)
        return 1
    print("check-run-artifacts: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
