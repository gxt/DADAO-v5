#!/usr/bin/env python3
"""run_suite.py — one command: build → image → boot → collect → ledger.

What it does, in order:

1. ``build_suite.build_all()``  — cross-build every case in ``suite.yaml``
   (static musl, suite copy, adaptation patches applied to the copy);
2. ``make_image.build_image()`` — the suite initramfs (``/init`` supervisor,
   ``/cases``, test binaries, ``/dev`` entries, 1777 ``/tmp``);
3. kernel: pin every ``CONFIG_DADAO_*`` probe off, point
   ``CONFIG_INITRAMFS_SOURCE`` at the suite archive, ``make vmlinux`` through
   ``tools/linux/make_vmlinux.py`` (skipped when the archive and the built
   ``vmlinux`` are unchanged — the hash is the record);
4. boot QEMU ``-M kaiwu-vast`` and read the console until the guest prints
   ``SUITE DONE`` (the host kill is only liveness; a case that overruns is
   killed *in the guest* by ``suite_init``'s kernel-tick alarm);
5. attribute every case by its ``SUITE CASE BEGIN/END`` markers, write
   ``results.json`` + ``summary.txt``, then run the suite checks
   (``suite_checks.py``): baseline verdicts, triage ledger, patch manifest,
   image manifest.

Exit status: 0 = the skeleton ran and every check passed; 1 = a check failed
(a case's verdict deviating from its recorded baseline is a check failure — the
*case* failing does not by itself decide the exit status); 2 = setup error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time as _time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.linux import config_pins                  # noqa: E402
from tools.linux import make_defconfig as defconfig  # noqa: E402
from tools.linux import paths as linux_paths         # noqa: E402
from tools.linux.suite import build_suite            # noqa: E402
from tools.linux.suite import make_image             # noqa: E402
from tools.linux.suite import suite_cases            # noqa: E402
from tools.linux.suite import suite_checks           # noqa: E402
from tools.linux.suite import suite_paths            # noqa: E402
from tools.qemu import k0_boot_probe as k0           # noqa: E402

JOBS = os.environ.get("JOBS", "32")
HOST_TIMEOUT_BASE = int(os.environ.get("SUITE_HOST_TIMEOUT", "600"))
#: No-progress net: a guest that prints nothing for this long is treated as
#: stalled (a case stuck in an uninterruptible syscall cannot honour its own
#: alarm, and the remaining cases are then reported missing).
IDLE_TIMEOUT = int(os.environ.get("SUITE_IDLE_TIMEOUT", "120"))

BUILD = linux_paths.linux_build_dir()
VMLINUX = BUILD / "vmlinux"
KERNEL_RECORD = "kernel-image.json"

#: The K6 continuation symbol lives in ``arch/dadao/Kconfig`` (not
#: ``Kconfig.debug``), so it is not part of the pin set; it is kept as a name,
#: never as a hand-written ``CONFIG_DADAO_X=v`` container element
#: (``check-config-pins`` C4), and it is what lets the boot reach ``/init``.
SUITE_SHELL_LINE = "CONFIG_DADAO_K6_SHELL=y"

AUTO_MARKER = "SUITE START"
DONE_MARKER = "SUITE DONE"
BEGIN_RE = re.compile(r"^SUITE CASE BEGIN (\S+)\s*$")
END_RE = re.compile(r"^SUITE CASE END (\S+) rc=(-?\d+) status=(\w+)\s*$")


class SetupError(RuntimeError):
    """Missing prerequisite (exit 2)."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# kernel image
# ---------------------------------------------------------------------------

def kernel_image_config() -> int:
    """Land the suite image's config slice in the shared build tree."""
    cpio = suite_paths.image_cpio()
    if not cpio.is_file():
        raise SetupError(f"{cpio} not found — build the suite image first")
    if not (BUILD / ".config").is_file():
        rc = subprocess.call([sys.executable,
                              str(_REPO_ROOT / "tools" / "linux" / "make_defconfig.py"),
                              "--jobs", JOBS])
        if rc != 0:
            return rc
    lines = config_pins.config_lines(build_suite.CONFIG_PINS) + [
        SUITE_SHELL_LINE,
        f'CONFIG_INITRAMFS_SOURCE="{cpio}"',
    ]
    return defconfig.apply_config_lines(lines)


def restore_default_initramfs() -> None:
    """Point the shared build tree's ``CONFIG_INITRAMFS_SOURCE`` back at the K6 image.

    The suite kernel is built in the *shared* out-of-tree kernel build directory
    (`tools/linux/paths.py`), and its image is selected through that one config
    line.  Leaving it at the suite archive would silently make every later image
    built from this tree (e.g. ``make check-linux-k6``) embed the suite rootfs:
    the gate would then boot ``suite_init`` and report 19 false failures.  The
    suite owns that mutation, so it also reverts it — always, success or not.
    """
    k6_cpio = linux_paths.linux_initramfs_dir() / "initramfs.cpio"
    if not k6_cpio.is_file():
        print("[WARN] no K6 initramfs archive to restore "
              f"({k6_cpio}); the build tree keeps the suite image", flush=True)
        return
    rc = defconfig.apply_config_lines([f'CONFIG_INITRAMFS_SOURCE="{k6_cpio}"'])
    print(f"[INFO] shared build tree: CONFIG_INITRAMFS_SOURCE -> K6 image (rc={rc})",
          flush=True)


def build_kernel(cpio_sha: str) -> int:
    record = suite_paths.suite_root() / KERNEL_RECORD
    if record.is_file() and VMLINUX.is_file():
        saved = json.loads(record.read_text(encoding="utf-8"))
        if saved.get("cpio_sha256") == cpio_sha and \
                saved.get("vmlinux_sha256") == _sha256_file(VMLINUX):
            print(f"[INFO] kernel: unchanged since the last suite image "
                  f"(cpio sha256={cpio_sha[:12]}) — skipped rebuild")
            return 0
    rc = subprocess.call([sys.executable,
                          str(_REPO_ROOT / "tools" / "linux" / "make_vmlinux.py"),
                          "--jobs", JOBS, "--skip-code-range"])
    if rc != 0:
        return rc
    record.write_text(json.dumps({
        "format": 1,
        "cpio_sha256": cpio_sha,
        "vmlinux_sha256": _sha256_file(VMLINUX),
        "jobs": JOBS,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


# ---------------------------------------------------------------------------
# boot + collect
# ---------------------------------------------------------------------------

def firmware() -> str:
    k0.load_contract()
    if not k0.ABI:
        raise SetupError("the boot contract is empty — cannot build the bootrom")
    scratch = suite_paths.suite_root() / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(scratch / "bootrom"), name="bootrom_suite.bin")


def boot(host_timeout: int) -> tuple[int, str, list[str], str]:
    qemu = linux_paths.toolchain_bin() / "qemu-system-dadao"
    if not os.access(qemu, os.X_OK):
        raise SetupError(f"{qemu} missing — run 'make install-host'")
    if not VMLINUX.is_file():
        raise SetupError(f"{VMLINUX} missing — build the kernel first")
    cmd = [str(qemu), "-machine", f"kaiwu-vast,bootrom-image={firmware()}",
           "-display", "none", "-serial", "none",
           "-chardev", "stdio,id=semi",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-kernel", str(VMLINUX)]

    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines: list[str] = []
    done = threading.Event()

    def reader() -> None:
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace")
            lines.append(line)
            if line.strip().startswith(DONE_MARKER):
                done.set()
        done.set()

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    start = _time.monotonic()
    seen = -1
    progress = start
    reason = "guest-done"
    while True:
        if done.wait(1.0):
            break
        if len(lines) != seen:
            seen = len(lines)
            progress = _time.monotonic()
        if _time.monotonic() - progress > IDLE_TIMEOUT:
            reason = "idle"   # no console output: the guest is not progressing
            break
        if _time.monotonic() - start > host_timeout:
            reason = "total"  # liveness budget spent
            break
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    thread.join(timeout=5)
    rc = proc.returncode if reason == "guest-done" else 124
    return int(rc), "".join(lines), cmd, reason


def parse_console(text: str, cases: list[suite_cases.Case]) -> list[dict]:
    """Attribute each case's lines to its BEGIN/END markers."""
    seen: dict[str, dict] = {}
    current: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        begin = BEGIN_RE.match(line)
        if begin:
            current, body = begin.group(1), []
            seen.setdefault(current, {"id": current, "rc": None,
                                      "status": "not-finished", "output": ""})
            continue
        end = END_RE.match(line)
        if end and current == end.group(1):
            record = seen[current]
            record["rc"] = int(end.group(2))
            record["status"] = end.group(3)
            record["output"] = "\n".join(body)
            current = None
            continue
        if current:
            body.append(line)
            continue

    records = []
    for case in cases:
        record = seen.get(case.id)
        if record is None:
            records.append({"id": case.id, "rc": None, "status": "missing",
                            "output": ""})
        else:
            records.append(record)
    return records


#: kselftest's own exit codes (tools/testing/selftests/kselftest.h).
KSFT_SKIP_EXIT = 4


def skipped_only(output: str) -> bool:
    """True when a program printed sub-tests but every one of them skipped.

    Derived from the program's own TAP output (``# Totals: pass:0 ... skip:N``),
    never from a per-case list: a case that passes some sub-tests and skips
    others stays PASS.
    """
    totals = re.search(r"#\s*Totals:\s*pass:(\d+).*?skip:(\d+)", output)
    if not totals:
        return False
    return int(totals.group(1)) == 0 and int(totals.group(2)) > 0


def verdict_of(record: dict) -> str:
    status = record["status"]
    if status == "missing":
        return "MISSING"
    if status == "timeout":
        return "TIMEOUT"
    if status == "not-finished":
        return "HOST_TIMEOUT"
    if status == "signal":
        return "SIGNAL"
    if status != "exit":
        return "FAIL"
    if record["rc"] == KSFT_SKIP_EXIT:
        return "SKIP"
    if record["rc"] != 0:
        return "FAIL"
    return "SKIP" if skipped_only(record.get("output", "")) else "PASS"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def _run_boots(args, groups, run_dir: Path) -> tuple[list[dict], list[dict]]:
    """Build + boot every group; return (case records, boot records)."""
    records: list[dict] = []
    boots: list[dict] = []
    for index, group in enumerate(groups, start=1):
        label = "+".join(case.id for case in group)
        print(f"[INFO] boot {index}/{len(groups)}: {label}", flush=True)
        if not args.skip_build:
            built = build_suite.build_all(cases=group)
            if built["failed"]:
                raise SetupError(f"build failed for {built['failed']}")
            make_image.build_image(cases=group)
        else:
            print("[INFO] build/image: skipped on request", flush=True)

        cpio_sha = _sha256_file(suite_paths.image_cpio())
        rc = kernel_image_config()
        if rc != 0:
            raise SetupError(f"config slice did not apply (rc={rc})")
        rc = build_kernel(cpio_sha)
        if rc != 0:
            raise SetupError(f"kernel build failed (rc={rc})")

        host_timeout = HOST_TIMEOUT_BASE + sum(case.timeout for case in group)
        print(f"[INFO] boot: host liveness timeout {host_timeout} s", flush=True)
        rc, console, cmd, stop_reason = boot(host_timeout)
        console_log = run_dir / f"console-{index}.log"
        console_log.write_text(console, encoding="utf-8")

        for case, record in zip(group, parse_console(console, group)):
            record["verdict"] = verdict_of(record)
            record["timeout"] = case.timeout
            record["console"] = str(console_log)
            records.append(record)
        boots.append({"cases": [case.id for case in group],
                      "console": str(console_log),
                      "cpio_sha256": cpio_sha,
                      "qemu_rc": rc, "host_timeout": host_timeout,
                      "stop_reason": stop_reason,
                      "qemu_cmd": cmd})
    return records, boots


def main() -> int:
    parser = argparse.ArgumentParser(description="run the kselftest suite once")
    parser.add_argument("--only", action="append", default=[],
                        help="build/run only these case ids (evidence)")
    parser.add_argument("--skip-build", action="store_true",
                        help="reuse built binaries and the current image "
                             "(single-boot debugging only)")
    parser.add_argument("--skip-checks", action="store_true",
                        help="collect results but skip the suite checks")
    parser.add_argument("--expect", default=str(suite_cases.SUITE_YAML),
                        help="suite definition (default: in-repo suite.yaml)")
    args = parser.parse_args()

    try:
        cases = suite_cases.load_cases(Path(args.expect))
        if args.only:
            wanted = set(args.only)
            unknown = wanted - {case.id for case in cases}
            if unknown:
                raise SetupError(f"unknown case id(s) {sorted(unknown)}")
            cases = [case for case in cases if case.id in wanted]

        stamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
        run_dir = suite_paths.runs_dir() / stamp
        run_dir.mkdir(parents=True, exist_ok=True)

        # A `stall` case wedges the machine, so a boot can carry at most one of
        # them: the ordinary cases share one boot, every stall case gets its own.
        groups: list[list[suite_cases.Case]] = []
        ordinary = [case for case in cases if not case.stall]
        if ordinary:
            groups.append(ordinary)
        groups += [[case] for case in cases if case.stall]

        try:
            records, boots = _run_boots(args, groups, run_dir)
        finally:
            # Never leave the shared build tree pointing at the suite image.
            restore_default_initramfs()

        order = {case.id: index for index, case in enumerate(cases)}
        records.sort(key=lambda record: order[record["id"]])
        counts: dict[str, int] = {}
        for record in records:
            counts[record["verdict"]] = counts.get(record["verdict"], 0) + 1
        results = {
            "format": 1,
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "suite": str(Path(args.expect).name),
            "kernel": {"vmlinux": str(VMLINUX),
                       "sha256": _sha256_file(VMLINUX)},
            "image": {"cpio_sha256": boots[-1]["cpio_sha256"],
                      "manifest_sha256": _sha256_file(suite_paths.image_manifest())},
            "idle_timeout": IDLE_TIMEOUT,
            "boots": boots,
            "cases": records,
            "counts": counts,
        }
        results_path = run_dir / "results.json"
        # Snapshot the image manifest this run was checked against.  The live
        # ``image/manifest.json`` is rewritten by *every* later image build (the
        # ``--only`` fault-path runs rebuild a one-case image), so comparing a
        # stored run with the live file later turns a correct run red for a
        # reason that has nothing to do with it (F-R1).  ``suite_checks`` uses
        # this snapshot when it exists; the live file stays the fallback for
        # runs made before snapshots existed.
        (run_dir / "image-manifest.json").write_text(
            suite_paths.image_manifest().read_text(encoding="utf-8"),
            encoding="utf-8")
        results_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")

        summary = [f"suite run {stamp}",
                   f"boots: {len(boots)} ({', '.join(b['stop_reason'] for b in boots)})",
                   f"results: {results_path}",
                   "verdicts: " + ", ".join(f"{key}={value}"
                                            for key, value in sorted(counts.items()))]
        for record in records:
            summary.append(f"  {record['verdict']:12s} {record['id']:28s} "
                           f"rc={record['rc']} status={record['status']}")
        summary_path = run_dir / "summary.txt"
        summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")
        print("\n".join(summary))
        print(f"[INFO] json: {results_path}")

        if args.skip_checks:
            print("run_suite: PASS (checks skipped on request)")
            return 0
        failures = suite_checks.run_checks(results, results_path)
        if failures:
            print(f"\nrun_suite: FAIL: {len(failures)} check(s) failed",
                  file=sys.stderr)
            return 1
        print("\nrun_suite: PASS")
        return 0
    except (SetupError, suite_cases.SuiteError, make_image.SetupError) as exc:
        print(f"run_suite: SETUP ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
