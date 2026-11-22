#!/usr/bin/env python3
"""Suite definition loader (``tests/unit/linux/suite/suite.yaml``).

The suite definition is in-repo data: which kselftest programs the image ships,
how long each may run (guest-side), and the **recorded baseline verdict** of the
current implementation.  Everything else (which tests exist, what they print)
comes from the locked kernel tree, never from this file.

Schema (strict: an unknown key is an error, so a typo cannot silently drop a
case):

  format: 1
  cases:
    - id: timers-nanosleep        # unique, used in markers and the ledger
      dir: timers                 # kselftest target directory (may be nested)
      prog: nanosleep             # program name inside that directory
      timeout: 60                 # guest-side seconds (kernel-tick alarm)
      expect: PASS                # recorded baseline verdict
      note: ...                   # optional, human context
      stall: true                 # optional: the case wedges the machine; it is
                                  # ordered last so the rest of the run survives

Verdict vocabulary (results, not triage classes):
  PASS / FAIL / SKIP / TIMEOUT / SIGNAL / MISSING / HOST_TIMEOUT
  PASS means rc=0 **and** at least one sub-test really passed; a program that
  only skips (rc=0 with ``# Totals: pass:0 skip:N`` or rc=4) is SKIP, so a
  skipped case can never be reported as a real pass.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml  # noqa: E402

SUITE_YAML = _REPO_ROOT / "tests" / "unit" / "linux" / "suite" / "suite.yaml"
TRIAGE_YAML = _REPO_ROOT / "tests" / "unit" / "linux" / "suite" / "triage.yaml"
PATCH_DIR = _REPO_ROOT / "tests" / "unit" / "linux" / "suite" / "patches" / "kselftest"
PATCH_MANIFEST = PATCH_DIR / "manifest.yaml"

VERDICTS = ("PASS", "FAIL", "SKIP", "TIMEOUT", "SIGNAL", "MISSING",
            "HOST_TIMEOUT")
CLASSES = ("KERNEL_BUG", "TEST_ADAPT", "UNSUPPORTED", "SUITE_ENV")

_CASE_KEYS = {"id", "dir", "prog", "timeout", "expect", "note", "stall"}
_TOP_KEYS = {"format", "cases"}


class SuiteError(RuntimeError):
    """The suite definition or the ledger is malformed (exit 2)."""


@dataclass(frozen=True)
class Case:
    id: str
    dir: str
    prog: str
    timeout: int
    expect: str
    note: str = ""
    stall: bool = False

    @property
    def top(self) -> str:
        """Top-level selftests directory (the copy unit)."""
        return self.dir.split("/", 1)[0]

    @property
    def image_path(self) -> str:
        """Path of the program inside the suite image."""
        return f"tests/{self.dir}/{self.prog}"


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise SuiteError(f"{path} not found (the suite definition is in-repo data)")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SuiteError(f"{path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SuiteError(f"{path}: top level must be a mapping")
    return data


def load_cases(path: Path | None = None) -> list[Case]:
    data = _load_yaml(path or SUITE_YAML)
    unknown = set(data) - _TOP_KEYS
    if unknown:
        raise SuiteError(f"{path or SUITE_YAML}: unknown key(s) {sorted(unknown)}")
    if data.get("format") != 1:
        raise SuiteError(f"{path or SUITE_YAML}: format must be 1")
    rows = data.get("cases")
    if not isinstance(rows, list) or not rows:
        raise SuiteError(f"{path or SUITE_YAML}: 'cases' must be a non-empty list")

    cases: list[Case] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SuiteError(f"case #{index}: must be a mapping")
        unknown = set(row) - _CASE_KEYS
        if unknown:
            raise SuiteError(f"case #{index}: unknown key(s) {sorted(unknown)}")
        missing = _CASE_KEYS - {"note", "stall"} - set(row)
        if missing:
            raise SuiteError(f"case #{index}: missing key(s) {sorted(missing)}")
        case = Case(id=str(row["id"]), dir=str(row["dir"]), prog=str(row["prog"]),
                    timeout=int(row["timeout"]), expect=str(row["expect"]),
                    note=str(row.get("note", "")),
                    stall=bool(row.get("stall", False)))
        if case.id in seen:
            raise SuiteError(f"duplicate case id {case.id!r}")
        if case.expect not in VERDICTS:
            raise SuiteError(f"case {case.id}: expect={case.expect!r} not in {VERDICTS}")
        if case.timeout <= 0:
            raise SuiteError(f"case {case.id}: timeout must be > 0")
        if "/" in case.prog or not case.prog:
            raise SuiteError(f"case {case.id}: prog must be a bare name")
        seen.add(case.id)
        cases.append(case)
    # A `stall` case is known to wedge the machine (host sees no console output
    # at all): it must run last, otherwise the rest of the suite would never be
    # reached.  One order for build, image and run -- sorted here, once.
    return ([case for case in cases if not case.stall]
            + [case for case in cases if case.stall])


def load_triage(path: Path | None = None) -> dict:
    """The in-repo triage ledger (one row per non-PASS verdict)."""
    data = _load_yaml(path or TRIAGE_YAML)
    unknown = set(data) - {"format", "rows"}
    if unknown:
        raise SuiteError(f"{path or TRIAGE_YAML}: unknown key(s) {sorted(unknown)}")
    if data.get("format") != 1:
        raise SuiteError(f"{path or TRIAGE_YAML}: format must be 1")
    rows = data.get("rows") or []
    if not isinstance(rows, list):
        raise SuiteError(f"{path or TRIAGE_YAML}: 'rows' must be a list")
    required = {"id", "class", "verdict", "case_output", "evidence", "recheck"}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SuiteError(f"triage row #{index}: must be a mapping")
        missing = required - set(row)
        if missing:
            raise SuiteError(f"triage row #{index}: missing key(s) {sorted(missing)}")
        if row["class"] not in CLASSES:
            raise SuiteError(f"triage row #{index} ({row['id']}): class "
                             f"{row['class']!r} not in {CLASSES}")
        if row["verdict"] not in VERDICTS or row["verdict"] == "PASS":
            raise SuiteError(f"triage row #{index} ({row['id']}): verdict "
                             f"{row['verdict']!r} must be a non-PASS verdict")
        for key in ("case_output", "evidence", "recheck"):
            if not str(row[key]).strip():
                raise SuiteError(f"triage row #{index} ({row['id']}): {key} is empty")
    return {"format": 1, "rows": rows}


# ---------------------------------------------------------------------------
# adaptation-patch manifest (one record per patch file, order = apply order)
# ---------------------------------------------------------------------------

_PATCH_TOP_KEYS = {"format", "upstream", "patches"}
_PATCH_KEYS = {"file", "sha256", "class", "why", "files"}
_PATCH_FILE_KEYS = {"path", "upstream_sha256", "patched_sha256"}


def load_patch_manifest(path: Path | None = None) -> dict:
    """Load and validate ``patches/kselftest/manifest.yaml``.

    Every patch file in the directory must have exactly one record here (and the
    record order is the apply order), so ``build_suite`` and ``suite_checks``
    read one definition instead of walking the directory on their own:

      file             patch file name inside the patch directory
      sha256           hash of the patch text itself
      class            triage class of the adaptation (TEST_ADAPT / SUITE_ENV / ...)
      why              why the test's assumption is wrong for this machine
      files            per touched file: ``upstream_sha256`` (hash **before** this
                       patch is applied: the locked kernel tree for the first
                       patch, the previous patch's result for a chained one) and
                       ``patched_sha256`` (hash after applying it)
    """
    data = _load_yaml(path or PATCH_MANIFEST)
    unknown = set(data) - _PATCH_TOP_KEYS
    if unknown:
        raise SuiteError(f"{path or PATCH_MANIFEST}: unknown key(s) {sorted(unknown)}")
    if data.get("format") != 1:
        raise SuiteError(f"{path or PATCH_MANIFEST}: format must be 1")
    upstream = data.get("upstream")
    if not isinstance(upstream, dict) or not {"component", "version", "commit"} <= set(upstream):
        raise SuiteError(f"{path or PATCH_MANIFEST}: 'upstream' needs component/version/commit")
    patches = data.get("patches")
    if not isinstance(patches, list) or not patches:
        raise SuiteError(f"{path or PATCH_MANIFEST}: 'patches' must be a non-empty list")
    seen: set[str] = set()
    for index, patch in enumerate(patches):
        if not isinstance(patch, dict):
            raise SuiteError(f"patch #{index}: must be a mapping")
        unknown = set(patch) - _PATCH_KEYS
        if unknown:
            raise SuiteError(f"patch #{index}: unknown key(s) {sorted(unknown)}")
        missing = _PATCH_KEYS - set(patch)
        if missing:
            raise SuiteError(f"patch #{index}: missing key(s) {sorted(missing)}")
        if patch["class"] not in CLASSES:
            raise SuiteError(f"patch #{index} ({patch['file']}): class "
                             f"{patch['class']!r} not in {CLASSES}")
        if not str(patch["why"]).strip():
            raise SuiteError(f"patch #{index} ({patch['file']}): why is empty")
        if patch["file"] in seen:
            raise SuiteError(f"patch #{index}: duplicate file {patch['file']!r}")
        seen.add(patch["file"])
        entries = patch["files"]
        if not isinstance(entries, list) or not entries:
            raise SuiteError(f"patch #{index} ({patch['file']}): 'files' must be non-empty")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != _PATCH_FILE_KEYS:
                raise SuiteError(f"patch #{index}: file entry needs exactly "
                                 f"{sorted(_PATCH_FILE_KEYS)}")
    return data


def patch_dir_files(path: Path | None = None) -> list[str]:
    """``*.patch`` files actually present in the patch directory."""
    directory = (path or PATCH_DIR)
    return sorted(item.name for item in directory.glob("*.patch"))


def verify_patch_set(path: Path | None = None) -> tuple[dict, list[str], list[str], list[str]]:
    """Bidirectional set check: patch directory <-> manifest.

    Returns ``(manifest, unregistered, missing_files, order_mismatch)`` where
    ``unregistered`` are patches present in the directory but absent from the
    manifest, ``missing_files`` are manifest records whose patch file is gone,
    and ``order_mismatch`` lists manifest record names that are not in
    lexicographic order (the apply order must be the file-name order, otherwise
    a chain's "before" hash is ambiguous).
    """
    manifest = load_patch_manifest(path)
    present = patch_dir_files(path)
    declared = [patch["file"] for patch in manifest["patches"]]
    unregistered = sorted(set(present) - set(declared))
    missing_files = sorted(set(declared) - set(present))
    order_mismatch = [name for name, other in zip(declared, sorted(declared))
                      if name != other]
    return manifest, unregistered, missing_files, order_mismatch
