#!/usr/bin/env python3
"""suite_checks.py — integrity checks of one suite run (m18-linux-005).

Checks are deliberately *not* "did every test pass": the suite exists to record
实况.  They assert that the run is attributable and that the in-repo records agree
with it:

  S1  the results cover exactly the case list of ``suite.yaml``;
  S2  every case's verdict equals its recorded baseline (``expect``) — a
      tampered criterion/value changes a verdict and lands here;
  S3  the triage ledger explains every non-PASS verdict with a legal class and
      evidence, has no stale rows, and its class counts match the run;
  S4  the adaptation patch manifest matches the locked kernel tree and the patch
      still applies cleanly (upstream commit + per-file sha256 + post-patch
      sha256); a patch that no longer applies is red here;
  S5  the image manifest belongs to this run's archive and ships every case plus
      the required devices/``/tmp``;
  S6  the printed counts are derived from the case records, not written down.

Each check prints ``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` and returns
its finding text, so the caller (``run_suite.py``) can fail the run.

Usage:  python3 tools/linux/suite/suite_checks.py <results.json>
Exit:   0 = all checks pass, 1 = at least one failed, 2 = unusable input.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import tomllib  # noqa: E402

from tools.linux import paths as linux_paths   # noqa: E402
from tools.linux.suite import suite_cases       # noqa: E402
from tools.linux.suite import suite_paths       # noqa: E402

PATCH_MANIFEST = suite_cases.PATCH_MANIFEST
NON_PASS = set(suite_cases.VERDICTS) - {"PASS"}


class CheckError(RuntimeError):
    """Unusable input for the checks (exit 2)."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Report:
    def __init__(self) -> None:
        self.checked = 0
        self.failures: list[str] = []

    def check(self, ident: str, name: str, ok: bool, expect, actual) -> bool:
        self.checked += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {ident} {name} | "
              f"期望={expect} 实际={actual}", flush=True)
        if not ok:
            self.failures.append(f"{ident} {name}: 期望={expect} 实际={actual}")
        return ok


def _locked_linux() -> dict:
    lock = _REPO_ROOT / "manifests" / "components.lock.toml"
    data = tomllib.loads(lock.read_text(encoding="utf-8"))
    for component in data.get("component", []):
        if component.get("name") == "linux":
            return component
    raise CheckError(f"{lock.name} has no linux component")


# ---------------------------------------------------------------------------
# S1/S2 — coverage and baseline
# ---------------------------------------------------------------------------

def check_coverage(rep: Report, results: dict, cases: list[suite_cases.Case]) -> None:
    want = [case.id for case in cases]
    got = [record["id"] for record in results["cases"]]
    rep.check("S1", "结果覆盖 suite.yaml 的全部用例（无缺无多）", got == want, want, got)
    rep.check("S1b", "每个用例都有 verdict", all(record.get("verdict") for record in results["cases"]),
              "all non-empty", {record["id"]: record.get("verdict") for record in results["cases"]})


def check_baseline(rep: Report, results: dict, cases: list[suite_cases.Case]) -> None:
    recorded = {case.id: case.expect for case in cases}
    actual = {record["id"]: record["verdict"] for record in results["cases"]}
    drift = {key: {"expect": recorded[key], "actual": actual.get(key)}
             for key in recorded if actual.get(key) != recorded[key]}
    rep.check("S2", "每个用例的 verdict == 记录的基线（篡改判据会落在这里）",
              not drift, "no drift", drift)


# ---------------------------------------------------------------------------
# S3 — triage ledger
# ---------------------------------------------------------------------------

def check_ledger(rep: Report, results: dict, cases: list[suite_cases.Case],
                 ledger: dict) -> None:
    rows = {row["id"]: row for row in ledger["rows"]}
    verdicts = {record["id"]: record["verdict"] for record in results["cases"]}
    non_pass = {key: value for key, value in verdicts.items() if value in NON_PASS}

    missing = sorted(set(non_pass) - set(rows))
    rep.check("S3a", "每条非 PASS 都在分诊台账有记录（分类计数 = 台账行数）",
              not missing, "covered", missing)

    mismatched = {key: {"verdict": value, "ledger": rows[key]["verdict"]}
                  for key, value in non_pass.items()
                  if key in rows and rows[key]["verdict"] != value}
    rep.check("S3b", "台账行的 verdict 与本次结果一致", not mismatched,
              "same", mismatched)

    stale = sorted(set(rows) - set(non_pass))
    rep.check("S3c", "台账没有过期行（PASS 用例不得留在台账里）", not stale,
              "none", stale)

    illegal = sorted(row["id"] for row in ledger["rows"]
                     if row["class"] not in suite_cases.CLASSES)
    rep.check("S3d", "台账分类都在 KERNEL_BUG/TEST_ADAPT/UNSUPPORTED/SUITE_ENV 内",
              not illegal, "none", illegal)

    empty = sorted(row["id"] for row in ledger["rows"]
                   if not str(row["evidence"]).strip()
                   or not str(row["recheck"]).strip())
    rep.check("S3e", "每条台账行都有证据与复评条件", not empty, "none", empty)

    # Counts are derived from the ledger rows and from the run, never written down.
    classes: dict[str, int] = {}
    for row in ledger["rows"]:
        classes[row["class"]] = classes.get(row["class"], 0) + 1
    rep.check("S3f", "台账行数 == 非 PASS 用例数", len(ledger["rows"]) == len(non_pass),
              len(non_pass), len(ledger["rows"]))
    print(f"  [INFO] S3 classes: {json.dumps(classes, sort_keys=True)} "
          f"(rows={len(ledger['rows'])}, non_pass={len(non_pass)})")


# ---------------------------------------------------------------------------
# S4 — adaptation patches
# ---------------------------------------------------------------------------

def check_patches(rep: Report) -> None:
    """Adaptation series: manifest <-> directory, then per-patch chain hashes.

    Two independent properties, both with a reachable FAIL:

      * the directory and the manifest name the **same** patch set (an
        unregistered ``*.patch`` or a manifest record without a file is red);
      * the series is applied one patch at a time and every step's before/after
        hash matches the manifest, so a tampered patch body, a drifted upstream
        file, or two patches touching the same file in the wrong order is red.
    """
    if not suite_cases.PATCH_MANIFEST.is_file():
        rep.check("S4a", "适配补丁 manifest 存在", False, "manifest.yaml", "missing")
        return
    manifest, unregistered, missing_files, order_mismatch = suite_cases.verify_patch_set()

    locked = _locked_linux()
    upstream = manifest["upstream"]
    rep.check("S4a", "manifest 的上游 commit == components.lock.toml",
              upstream["commit"] == locked.get("commit"),
              locked.get("commit"), upstream["commit"])

    rep.check("S4b", "补丁目录与 manifest 双向相等（未登记补丁也算红）",
              not unregistered, "no unregistered patch", unregistered)
    rep.check("S4c", "manifest 的补丁文件都在目录内", not missing_files,
              "all present", missing_files)
    rep.check("S4d", "manifest 顺序 == 文件名顺序（补丁链顺序确定）",
              not order_mismatch, "same order", order_mismatch)
    if unregistered or missing_files or order_mismatch:
        return

    bad = [patch["file"] for patch in manifest["patches"]
           if not (suite_cases.PATCH_DIR / patch["file"]).is_file()
           or _sha256(suite_cases.PATCH_DIR / patch["file"]) != patch["sha256"]]
    rep.check("S4e", "每个补丁本体的 sha256 == manifest（补丁未被篡改）",
              not bad, "no drift", bad)
    if bad:
        return

    # Manifest paths are relative to the selftests root (the suite copy's root).
    source = linux_paths.linux_source_dir() / "tools" / "testing" / "selftests"
    first_drift = [entry["path"] for entry in manifest["patches"][0]["files"]
                   if _sha256(source / entry["path"]) != entry["upstream_sha256"]]
    rep.check("S4f", "首个补丁的上游目标文件哈希 == manifest（锁定树未漂移）",
              not first_drift, "no drift", first_drift)
    if first_drift:
        return

    scratch = suite_paths.suite_root() / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=scratch, prefix="patch-check-"))
    try:
        # One copy per touched file, seeded from the locked tree: the chain is
        # replayed exactly as build_suite does it.
        for entry in (item for patch in manifest["patches"] for item in patch["files"]):
            dest = tmp / entry["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(source / entry["path"], dest)

        problems: list[str] = []
        for patch in manifest["patches"]:
            path = suite_cases.PATCH_DIR / patch["file"]
            drifted = [entry["path"] for entry in patch["files"]
                       if _sha256(tmp / entry["path"]) != entry["upstream_sha256"]]
            if drifted:
                problems.append(f"{patch['file']}: before-hash mismatch {drifted}")
                continue
            check = subprocess.run(
                ["git", "apply", "--check", "-p1", str(path)],
                cwd=str(tmp), capture_output=True, text=True)
            if check.returncode != 0:
                problems.append(f"{patch['file']}: {check.stderr.strip()}")
                continue
            apply = subprocess.run(
                ["git", "apply", "-p1", str(path)],
                cwd=str(tmp), capture_output=True, text=True)
            if apply.returncode != 0:
                problems.append(f"{patch['file']}: apply failed: {apply.stderr.strip()}")
                continue
            after = [entry["path"] for entry in patch["files"]
                     if _sha256(tmp / entry["path"]) != entry["patched_sha256"]]
            if after:
                problems.append(f"{patch['file']}: after-hash mismatch {after}")
        rep.check("S4g", "逐个补丁增量应用：应用前/后哈希 == manifest（链式不互撞）",
                  not problems, "chain ok", problems)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# S5/S6 — image and counts
# ---------------------------------------------------------------------------

def check_image(rep: Report, results: dict,
                manifest_path: Path | None = None) -> None:
    """S5: the manifest of *this run* describes the archive the run booted.

    ``manifest_path`` is the per-run snapshot written by ``run_suite.py``
    (``<run>/image-manifest.json``).  The live ``image/manifest.json`` is
    rewritten by every later image build, so a stored run checked against it
    goes red after an unrelated ``--only`` run rebuilt the image (F-R1/F-R2);
    the snapshot is the faithful record of what the run recorded.  Without a
    snapshot (runs made before snapshots existed) the live file is used, as
    before.
    """
    live = suite_paths.image_manifest()
    manifest_path = manifest_path or live
    if not manifest_path.is_file():
        rep.check("S5a", "镜像 manifest 存在", False, "manifest.json", "missing")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    same_archive = results["image"]["cpio_sha256"] == manifest["cpio"]["sha256"]
    if manifest_path != live:
        # The snapshot must be the very manifest the run recorded; otherwise the
        # cpio match would be against a file the run never saw.
        same_archive = same_archive and \
            _sha256(manifest_path) == results["image"]["manifest_sha256"]
    rep.check("S5a", "结果记录的 cpio sha256 == 镜像 manifest",
              same_archive,
              results["image"]["cpio_sha256"], manifest["cpio"]["sha256"])

    entries = {entry["name"]: entry for entry in manifest["entries"]}
    shipped = {case["id"]: case["path"] in entries for case in manifest["cases"]}
    rep.check("S5b", "镜像装载了 suite.yaml 的每个用例", all(shipped.values()),
              "all", [key for key, value in shipped.items() if not value])

    devices = {"dev/console": [240, 0], "dev/null": [1, 3], "dev/zero": [1, 5]}
    wrong = {name: entries.get(name, {}).get("rdev") for name, rdev in devices.items()
             if entries.get(name, {}).get("rdev") != rdev}
    rep.check("S5c", "设备节点与 K6 控制台一致（console 240:0 / null / zero）",
              not wrong, devices, wrong)
    tmp_mode = f"{0o041777:07o}"  # S_IFDIR | 1777, same formatting as the manifest
    rep.check("S5d", "/tmp 可写（mode 1777）",
              entries.get("tmp", {}).get("mode") == tmp_mode,
              tmp_mode, entries.get("tmp", {}).get("mode"))
    rep.check("S5e", "镜像含 /init 与 /cases", "init" in entries and "cases" in entries,
              ["init", "cases"], sorted(set(entries) & {"init", "cases"}))


def check_counts(rep: Report, results: dict) -> None:
    live: dict[str, int] = {}
    for record in results["cases"]:
        live[record["verdict"]] = live.get(record["verdict"], 0) + 1
    rep.check("S6a", "results.counts 现场重算一致", live == results["counts"],
              live, results["counts"])
    rep.check("S6b", "counts 合计 == 用例数",
              sum(results["counts"].values()) == len(results["cases"]),
              len(results["cases"]), sum(results["counts"].values()))


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def run_checks(results: dict, results_path: Path | None = None) -> list[str]:
    cases = suite_cases.load_cases()
    ledger = suite_cases.load_triage()
    rep = Report()
    print(f"[INFO] suite checks for {results_path or '<results>'}: "
          f"{len(cases)} case(s) in suite.yaml, {len(ledger['rows'])} ledger row(s)")
    check_coverage(rep, results, cases)
    check_baseline(rep, results, cases)
    check_ledger(rep, results, cases, ledger)
    check_patches(rep)
    snapshot = (results_path.parent / "image-manifest.json"
                if results_path is not None else None)
    check_image(rep, results,
                snapshot if snapshot is not None and snapshot.is_file() else None)
    check_counts(rep, results)
    print(f"[INFO] suite checks: {rep.checked - len(rep.failures)}/{rep.checked} passed")
    return rep.failures


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: suite_checks.py <results.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"suite_checks: SETUP ERROR: {path} not found", file=sys.stderr)
        return 2
    try:
        failures = run_checks(json.loads(path.read_text(encoding="utf-8")), path)
    except (suite_cases.SuiteError, CheckError) as exc:
        print(f"suite_checks: SETUP ERROR: {exc}", file=sys.stderr)
        return 2
    if failures:
        print(f"suite_checks: FAIL: {len(failures)} check(s) failed", file=sys.stderr)
        return 1
    print("suite_checks: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
