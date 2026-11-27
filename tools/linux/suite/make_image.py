#!/usr/bin/env python3
"""make_image.py — build the suite initramfs (m18-linux-005).

The suite image is **independent** of the K6 image: K6's ``/init``, ``APPLETS``
and gate are untouched.  What it ships (lexicographic cpio order):

  .  cases  dev/  dev/console  dev/null  dev/zero  etc/  etc/passwd
  init  proc  tests/  tests/<dir>/  tests/<dir>/<prog>  tmp/

* ``init`` — ``suite_init.c`` (PID 1: mounts /proc and a writable /tmp, runs
  each case under a kernel-tick ``alarm``, brackets its output with markers);
* ``cases`` — one ``<id> <timeout> <user> /tests/<dir>/<prog>`` line per case
  (``user`` is ``root`` or ``nobody``; see ``suite.yaml``);
* ``dev/console`` (240:0, the semihosting console) plus
  ``dev/null``/``dev/zero``; no ``/dev/mem`` (the mm/pfnmap target skips at
  open() until this port supports the devmem mmap path -- see triage.yaml);
* ``etc/passwd`` — the minimal passwd database the tests look up (mlockall02's
  ``getpwnam("nobody")``);
* ``tmp`` mode 1777 (ramfs mounted on it by ``init``).

Determinism (acceptance 1: two runs produce the same verdict set; the archive
itself must not vary): ``SOURCE_DATE_EPOCH=0``, cpio mtime 0, uid/gid 0, sorted
entries, 4-byte alignment, and every payload is a build product of the same
inputs.  ``--inject`` breaks one property on purpose so the verifier below has a
reachable FAIL.

The archive writer helpers (``_newc_entry`` / ``parse_newc``) are imported from
``tools/linux/make_initramfs.py`` on purpose: one newc writer for both images, so
a fix to the format cannot drift between them.

Usage:
  python3 tools/linux/suite/make_image.py
  python3 tools/linux/suite/make_image.py --inject mtime|missing-case

Exit status: 0 = built and verified; 1 = verification failed; 2 = setup error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.linux import make_initramfs as newc  # noqa: E402
from tools.linux.suite import build_suite        # noqa: E402
from tools.linux.suite import suite_cases        # noqa: E402
from tools.linux.suite import suite_paths        # noqa: E402

SUITE_INIT_SOURCE = Path(__file__).resolve().with_name("suite_init.c")

#: /dev entries the guest expects: name -> (major, minor).
DEVICES = {
    "dev/console": (240, 0),   # arch/dadao semihosting console (K6 register)
    "dev/null": (1, 3),
    "dev/zero": (1, 5),
}

TMP_MODE = 0o041777  # S_IFDIR | 1777

#: Minimal passwd database.  LTP's mlockall02 setup() calls
#: ``getpwnam("nobody")`` and dereferences the result; without this file it
#: takes SIGSEGV instead of testing mlockall().  The uid/gid match the
#: supervisor's hard-coded drop target (suite_init.c) and the kernel's default
#: overflow uid for an unmapped user.
PASSWD = (b"root:x:0:0:root:/:/bin/sh\n"
          b"nobody:x:65534:65534:nobody:/:/bin/false\n")


class CheckError(RuntimeError):
    """The produced image violates a required property (exit 1)."""


class SetupError(RuntimeError):
    """Missing prerequisite / unusable input (exit 2)."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_init(cases: list[suite_cases.Case]) -> tuple[Path, bytes]:
    """Compile the supervisor with the cross CC of the suite being imaged.

    An LTP-only work root (a private replay of the locked kernel tree) has the
    LTP wrapper but never ran the kselftest builder, so pick the wrapper by the
    case kind instead of assuming the kselftest one exists.
    """
    ltp_only = bool(cases) and all(case.kind == "ltp" for case in cases)
    wrapper = suite_paths.ltp_cc_wrapper() if ltp_only else suite_paths.cc_wrapper()
    if not wrapper.is_file():
        raise SetupError(f"{wrapper} not found — run the suite builder first")
    out = suite_paths.image_dir() / "init"
    out.parent.mkdir(parents=True, exist_ok=True)
    env = {"SOURCE_DATE_EPOCH": "0", "PATH": "/usr/bin:/bin"}
    proc = subprocess.run(
        [str(wrapper), "-O2", "-fno-ident", "-Wall", str(SUITE_INIT_SOURCE),
         "-o", str(out)],
        capture_output=True, text=True, env=env)
    if proc.returncode != 0 or not out.is_file():
        raise SetupError(f"suite_init.c did not build (rc={proc.returncode}):\n"
                         f"{proc.stdout}{proc.stderr}")
    return out, out.read_bytes()


def cases_file_text(cases: list[suite_cases.Case]) -> bytes:
    lines = ["# <id> <timeout-seconds> <user> <argv...>  "
             "(tools/linux/suite/make_image.py)"]
    for case in cases:
        lines.append(f"{case.id} {case.timeout} {case.user} {case.image_path}")
    return ("\n".join(lines) + "\n").encode()


def image_entries(cases: list[suite_cases.Case], init_bytes: bytes,
                  cases_bytes: bytes, *, inject: str | None = None,
                  ) -> list[newc.Entry]:
    if inject == "missing-case" and cases:
        cases = cases[:-1]
    items: list[newc.Entry] = [
        newc.Entry(".", newc.MODE_DIR, "dir", b""),
        newc.Entry("cases", newc.MODE_FILE, "file", cases_bytes),
        newc.Entry("dev", newc.MODE_DIR, "dir", b""),
        newc.Entry("etc", newc.MODE_DIR, "dir", b""),
        newc.Entry("etc/passwd", newc.MODE_FILE, "file", PASSWD),
        newc.Entry("init", newc.MODE_FILE, "file", init_bytes),
        newc.Entry("proc", newc.MODE_DIR, "dir", b""),
        newc.Entry("tests", newc.MODE_DIR, "dir", b""),
        newc.Entry("tmp", TMP_MODE, "dir", b""),
    ]
    for name, (major, minor) in DEVICES.items():
        items.append(newc.Entry(name, newc.MODE_CHARDEV, "chardev", b"",
                                major, minor))
    dirs: set[str] = set()
    for case in cases:
        binary = suite_paths.build_dir() / case.dir / case.prog
        if not binary.is_file():
            raise SetupError(f"{binary} not built — run build_suite.py first")
        parent = f"tests/{case.dir}"
        while parent not in dirs and parent != "tests":
            dirs.add(parent)
            parent = parent.rsplit("/", 1)[0]
        items.append(newc.Entry(case.image_path, newc.MODE_FILE, "file",
                                binary.read_bytes()))
        for helper in case.helpers:
            helper_binary = suite_paths.build_dir() / case.dir / helper
            if not helper_binary.is_file():
                raise SetupError(f"{helper_binary} not built — run the suite "
                                 f"builder first")
            items.append(newc.Entry(case.helper_image_path(helper), newc.MODE_FILE,
                                    "file", helper_binary.read_bytes()))
    for name in dirs:
        items.append(newc.Entry(name, newc.MODE_DIR, "dir", b""))
    return sorted(items, key=lambda entry: entry.name)


def _dir_nlink(entries: list[newc.Entry], name: str) -> int:
    prefix = "" if name == "." else name + "/"
    subdirs = sum(
        1 for entry in entries
        if (entry.mode & 0o170000) == 0o040000 and entry.name != "."
        and entry.name.startswith(prefix) and "/" not in entry.name[len(prefix):])
    return 2 + subdirs


def build_cpio(entries: list[newc.Entry], *, inject: str | None = None) -> bytes:
    mtime = 0 if inject != "mtime" else int(time.time() * 1000) & 0xFFFFFFFF
    encoded = [
        newc._newc_entry(
            entry.name, index + 1, entry.mode, entry.data,
            nlink=(_dir_nlink(entries, entry.name)
                   if entry.kind == "dir" else 1),
            mtime=mtime, rdevmajor=entry.rdevmajor, rdevminor=entry.rdevminor)
        for index, entry in enumerate(entries)
    ]
    encoded.append(newc._newc_entry(newc.CPIO_TRAILER, 0, 0, b"", nlink=1,
                                    mtime=mtime))
    return b"".join(encoded)


def verify(archive: bytes, cases: list[suite_cases.Case],
           build_report: dict, init_bytes: bytes) -> list[dict]:
    """Re-parse the archive and assert the image contract (each check can fail)."""
    parsed = newc.parse_newc(archive)
    names = [entry["name"] for entry in parsed]
    if names[-1] != newc.CPIO_TRAILER:
        raise CheckError(f"last entry is {names[-1]!r}, not TRAILER!!!")
    if names[0] != ".":
        raise CheckError(f"first entry is {names[0]!r}, not '.'")
    body_names = names[1:-1]
    if body_names != sorted(body_names):
        raise CheckError("entries are not in lexicographic order")

    for entry in parsed:
        if (entry["mtime"], entry["uid"], entry["gid"]) != (0, 0, 0):
            raise CheckError(f"entry {entry['name']!r} is not deterministic: "
                             f"mtime={entry['mtime']} uid={entry['uid']} gid={entry['gid']}")

    expected: dict[str, tuple[int, tuple[int, int] | None]] = {
        ".": (newc.MODE_DIR, None),
        "cases": (newc.MODE_FILE, None),
        "dev": (newc.MODE_DIR, None),
        "etc": (newc.MODE_DIR, None),
        "etc/passwd": (newc.MODE_FILE, None),
        "init": (newc.MODE_FILE, None),
        "proc": (newc.MODE_DIR, None),
        "tests": (newc.MODE_DIR, None),
        "tmp": (TMP_MODE, None),
    }
    for name, rdev in DEVICES.items():
        expected[name] = (newc.MODE_CHARDEV, rdev)
    for case in cases:
        expected[case.image_path] = (newc.MODE_FILE, None)
        for helper in case.helpers:
            expected[case.helper_image_path(helper)] = (newc.MODE_FILE, None)
        parent = case.image_path.rsplit("/", 1)[0]
        while parent != "tests":
            expected[parent] = (newc.MODE_DIR, None)
            parent = parent.rsplit("/", 1)[0]

    present = {entry["name"]: entry for entry in parsed[:-1]}
    missing = sorted(set(expected) - set(present))
    if missing:
        raise CheckError(f"image is missing entries {missing}")
    extra = sorted(set(present) - set(expected))
    if extra:
        raise CheckError(f"image has unexpected entries {extra}")
    for name, (mode, rdev) in expected.items():
        if present[name]["mode"] != mode:
            raise CheckError(f"entry {name!r} mode is {present[name]['mode']:o}, "
                             f"expected {mode:o}")
        if rdev is not None and (present[name]["rdevmajor"],
                                 present[name]["rdevminor"]) != rdev:
            raise CheckError(
                f"{name!r} device is {present[name]['rdevmajor']}:"
                f"{present[name]['rdevminor']}, expected {rdev[0]}:{rdev[1]}")
    if present["init"]["body"] != init_bytes:
        raise CheckError("/init payload is not the compiled supervisor")
    if present["etc/passwd"]["body"] != PASSWD:
        raise CheckError("/etc/passwd payload differs from PASSWD")

    built = {record["id"]: record for record in build_report["cases"]}
    for case in cases:
        body = present[case.image_path]["body"]
        if _sha256(body) != built[case.id]["sha256"]:
            raise CheckError(f"{case.image_path} payload differs from the build "
                             f"product of case {case.id}")
        recorded = {helper["name"]: helper["sha256"]
                    for helper in built[case.id].get("helpers", [])}
        for helper in case.helpers:
            if helper not in recorded:
                raise CheckError(f"{case.id}: build report has no hash for helper "
                                 f"{helper}")
            got = _sha256(present[case.helper_image_path(helper)]["body"])
            if got != recorded[helper]:
                raise CheckError(f"{case.helper_image_path(helper)} payload differs "
                                 f"from the build product")
    if present["cases"]["body"] != cases_file_text(cases):
        raise CheckError("/cases content differs from the case list")

    return parsed


def build_image(inject: str | None = None,
                cases: list[suite_cases.Case] | None = None) -> dict:
    cases = list(cases) if cases is not None else suite_cases.load_cases()
    report_path = suite_paths.suite_root() / "build-report.json"
    if not report_path.is_file():
        raise SetupError(f"{report_path} not found — run build_suite.py first")
    build_report = json.loads(report_path.read_text(encoding="utf-8"))
    if {record["id"] for record in build_report["cases"]} != {case.id for case in cases}:
        raise SetupError("build report does not match suite.yaml — rebuild first")

    init_path, init_bytes = build_init(cases)
    cases_bytes = cases_file_text(cases)
    entries = image_entries(cases, init_bytes, cases_bytes, inject=inject)
    archive = build_cpio(entries, inject=inject)
    parsed = verify(archive, cases, build_report, init_bytes)

    # Determinism by construction: the writer is pure, so a second pass with the
    # same inputs must be byte-identical (a timestamp/order leak shows up here).
    if inject is None:
        rebuilt = build_cpio(image_entries(cases, init_bytes, cases_bytes))
        if rebuilt != archive:
            raise CheckError("two image builds from the same inputs differ")

    out = suite_paths.image_cpio()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(archive)

    record_entries = []
    for entry in parsed[:-1]:
        is_dir = (entry["mode"] & 0o170000) == 0o040000
        item = {"name": entry["name"], "mode": f"{entry['mode']:07o}",
                "kind": ("dir" if is_dir else
                         "chardev" if entry["mode"] == newc.MODE_CHARDEV else "file"),
                "size": len(entry["body"]),
                "sha256": _sha256(entry["body"])}
        if item["kind"] == "chardev":
            item["rdev"] = [entry["rdevmajor"], entry["rdevminor"]]
        record_entries.append(item)
    manifest = {
        "format": 1,
        "init": {"name": "init", "size": len(init_bytes),
                 "sha256": _sha256(init_bytes)},
        "cases": [{"id": case.id, "timeout": case.timeout,
                   "path": case.image_path,
                   "helpers": [case.helper_image_path(helper)
                               for helper in case.helpers],
                   "sha256": _sha256((suite_paths.build_dir() / case.dir
                                      / case.prog).read_bytes())}
                  for case in cases],
        "entries": record_entries,
        "cpio": {"name": out.name, "size": len(archive),
                 "sha256": _sha256(archive)},
        "mounts": {"proc": "/proc", "tmp": "/tmp"},
    }
    manifest_path = suite_paths.image_manifest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    print(f"[PASS] suite image: {len(record_entries)} entries, "
          f"{len(cases)} case(s), {len(archive)} B sha256={manifest['cpio']['sha256'][:12]}")
    print(f"[INFO] init: {len(init_bytes)} B sha256={manifest['init']['sha256'][:12]}")
    return {"init": str(init_path), "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="build the kselftest suite initramfs")
    parser.add_argument("--inject", choices=("mtime", "missing-case"),
                        help="evidence only: break determinism/completeness on purpose")
    args = parser.parse_args()
    try:
        build_image(args.inject)
    except SetupError as exc:
        print(f"make_image: SETUP ERROR: {exc}", file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"make_image: FAIL: {exc}", file=sys.stderr)
        return 1
    print("make_image: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
