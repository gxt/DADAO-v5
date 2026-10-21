#!/usr/bin/env python3
"""Per-worktree gate lock: turn "run the gates serially" into a mechanical mutex.

Why (``ISS-229`` / ``INFRA-099t``): running ``make check-modules`` (L2) and
``make check-full`` (L3) concurrently in one worktree gave a *false* FAIL
(``L3_EXIT=2``, Embench 37/38, ``stddef.h not found``) because one gate read
the install root while the other was re-staging it; earlier, a manual
``make build-mc`` concurrent with L2's ``install-host -> build-mc`` corrupted
the build tree (``clang-23`` bloated / segfault).  Until now the only defence
was the ``NOTE (concurrency)`` comment in the Makefile.

Mechanism: every target listed in the Makefile's ``GATE_LOCKED_TARGETS`` is a
*gate*: its body (prerequisites included) lives in ``_locked-<target>`` and is
run by this script under one ``flock(2)`` on ``<repo>/.dadao/gate.lock``.

Semantics:

* **Nested calls pass through.**  A locked target started from inside another
  locked target (``check-modules -> test-semihost -> install-host -> build-mc``)
  inherits ``DADAO_GATE_LOCK_HELD`` and skips re-acquisition -- the ancestor
  already holds the lock.  The pass-through is *verified*: the holder pid
  recorded in the lock file must be an ancestor of this process, so a stale or
  spoofed environment marker cannot switch the mutex off.  (Where ``/proc`` is
  unavailable the ancestry cannot be checked and the marker is trusted --
  without that fallback a nested call would deadlock on its own lock; the
  self-test reports that case as SKIP.)
* **Independent processes wait**, bounded by ``--wait`` (``GATE_LOCK_WAIT``,
  default 3600 s).  On timeout the diagnosis names the lock file and the holder
  (pid / start time / target / command) and exits 75 -- never blocks forever.
* ``--failfast`` (``GATE_LOCK_FAILFAST=1``): one non-blocking attempt, rc 75.
* **Lock unusable** (parent missing/unwritable, ``flock(2)`` unavailable) =>
  rc 69 and the target does not run.  Silently skipping the mutex is not an
  option.

The lock file content is a one-line JSON holder record, rewritten on acquire
and cleared on release; it exists only to make *waiting* diagnosable.

CLI::

    gate_lock.py run --lock <path> [--wait S] [--failfast 0|1] --target NAME -- CMD...
    gate_lock.py --self-test [--keep]

``--self-test`` injects the three required classes -- same-tree nesting
allowed / independent process rejected / lock unavailable reported -- plus the
controls that keep each of them reachable (marker without an ancestral holder
must still acquire; a bounded wait must proceed once the holder releases).
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

try:  # POSIX only; a missing flock(2) is a hard error, not a silent pass
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX host
    fcntl = None  # type: ignore[assignment]

EXIT_BUSY = 75          # lock held / wait bound exhausted (EX_TEMPFAIL)
EXIT_UNAVAILABLE = 69   # lock unusable (EX_UNAVAILABLE)
ENV_HELD = "DADAO_GATE_LOCK_HELD"
ENV_VERBOSE = "DADAO_GATE_LOCK_VERBOSE"
POLL_INTERVAL = 0.2
# Ancestor inspection needs /proc; without it the nesting check degrades to the
# environment marker only (documented in the docstring) -- otherwise a nested
# call could never prove it is nested and would deadlock on its own lock.
PROC_AVAILABLE = Path("/proc/self/stat").is_file()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _say(message: str) -> None:
    print(f"gate-lock: {message}", file=sys.stderr, flush=True)


def _verbose() -> bool:
    return os.environ.get(ENV_VERBOSE, "") not in ("", "0")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_holder(lock_path: Path) -> dict:
    """Read the holder record; tolerate an empty/garbled file (diagnostics only)."""
    try:
        raw = lock_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"raw": raw}
    return data if isinstance(data, dict) else {"raw": raw}


def describe(holder: dict) -> str:
    """Human-readable holder, e.g. ``pid=4242, since ..., target=check``."""
    if not holder:
        return "holder unknown (lock file empty or unreadable)"
    if "raw" in holder:
        return f"raw={holder['raw']!r}"
    parts = []
    if holder.get("pid") is not None:
        stale = PROC_AVAILABLE and not _pid_alive(holder["pid"])
        parts.append(f"pid={holder['pid']}" + (" [stale: process gone]" if stale else ""))
    if holder.get("started"):
        parts.append(f"since {holder['started']}")
    if holder.get("target"):
        parts.append(f"target={holder['target']}")
    cmd = holder.get("cmd")
    if cmd:
        parts.append("cmd=" + (" ".join(map(str, cmd)) if isinstance(cmd, list) else str(cmd)))
    return ", ".join(parts) if parts else "holder unknown (no fields)"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def ancestor_pids() -> list[int]:
    """This process' ancestors (nearest first), via /proc; [] when unavailable."""
    out: list[int] = []
    pid = os.getpid()
    for _ in range(64):
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return out
        # `comm` may contain spaces/parens -> parse the fields after the last ')'
        try:
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
        except (IndexError, ValueError):
            return out
        if ppid <= 1:
            return out
        out.append(ppid)
        pid = ppid
    return out


def _same_path(value: str, lock_path: Path) -> bool:
    try:
        return Path(value).resolve() == lock_path
    except OSError:
        return False


def _spawn(cmd: list[str], env: dict, lock_path: Path) -> int:
    env = dict(env)
    env[ENV_HELD] = str(lock_path)
    try:
        # close_fds=False keeps the parent make's jobserver pipe (an fd > 2 that
        # make marked inheritable) alive for the re-entered make; otherwise a
        # `make -jN` gate degenerates into "jobserver unavailable: using -j1".
        # The lock fd itself is NOT leaked: Python opens it non-inheritable.
        return subprocess.call(cmd, env=env, close_fds=False)
    except FileNotFoundError:
        _say(f"cannot run {cmd[0]!r}: not found (rc={EXIT_UNAVAILABLE})")
        return EXIT_UNAVAILABLE


def _open_lock(lock_path: Path, target: str):
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        return os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError as exc:
        _say(
            f"UNAVAILABLE {lock_path}: {exc.strerror or exc} -- refusing to run target "
            f"'{target}' without the worktree mutex (rc={EXIT_UNAVAILABLE})"
        )
        return None


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        _say("run: no command given")
        return 2
    lock_path = Path(args.lock).resolve()
    failfast = str(args.failfast).strip().lower() in ("1", "true", "yes", "on")
    target = args.target or cmd[0]

    if fcntl is None or not hasattr(fcntl, "flock"):
        _say(
            f"UNAVAILABLE: flock(2) is not available on this platform -- refusing to run "
            f"target '{target}' without the worktree mutex (rc={EXIT_UNAVAILABLE})"
        )
        return EXIT_UNAVAILABLE

    # Nested (same make tree)?  The marker alone is not trusted: the recorded
    # holder must be an *ancestor* of this process.
    marker = os.environ.get(ENV_HELD, "")
    if marker and _same_path(marker, lock_path):
        holder = read_holder(lock_path)
        nested = isinstance(holder.get("pid"), int) and (
            not PROC_AVAILABLE or holder["pid"] in ancestor_pids()
        )
        if nested:
            if _verbose():
                _say(f"nested: {lock_path} already held by an ancestor ({describe(holder)}); not re-acquiring")
            return _spawn(cmd, os.environ, lock_path)
        _say(
            f"warning: {ENV_HELD}={marker} but no ancestor holds {lock_path} "
            f"({describe(holder)}); acquiring the lock normally"
        )

    fd = _open_lock(lock_path, target)
    if fd is None:
        return EXIT_UNAVAILABLE

    deadline = time.monotonic() + max(0.0, args.wait)
    waited_from = None
    holder: dict = {}
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
                _say(f"UNAVAILABLE {lock_path}: flock failed: {exc} -- refusing to run target '{target}' (rc={EXIT_UNAVAILABLE})")
                os.close(fd)
                return EXIT_UNAVAILABLE
        holder = read_holder(lock_path)
        if failfast:
            _say(
                f"BUSY {lock_path} is held by {describe(holder)}; GATE_LOCK_FAILFAST=1 so "
                f"target '{target}' is refused immediately (rc={EXIT_BUSY}; re-run without "
                f"GATE_LOCK_FAILFAST to wait, or wait for the holder to finish)"
            )
            os.close(fd)
            return EXIT_BUSY
        if waited_from is None:
            waited_from = time.monotonic()
            _say(
                f"WAIT {lock_path} is held by {describe(holder)}; target '{target}' waits up "
                f"to {args.wait:g}s (GATE_LOCK_WAIT)"
            )
        if time.monotonic() >= deadline:
            _say(
                f"BUSY wait bound exhausted after {args.wait:g}s (GATE_LOCK_WAIT) for target "
                f"'{target}'; {lock_path} is still held by {describe(holder)} (rc={EXIT_BUSY}; "
                f"raise GATE_LOCK_WAIT for a longer hold, e.g. a full L3 run)"
            )
            os.close(fd)
            return EXIT_BUSY
        time.sleep(POLL_INTERVAL)

    record = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "target": target,
        "started": _utc_now(),
        "cwd": os.getcwd(),
        "cmd": cmd,
    }
    try:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, (json.dumps(record) + "\n").encode("utf-8"))
    except OSError as exc:  # diagnostics only; the lock itself is held
        _say(f"warning: cannot record holder info in {lock_path}: {exc}")
    if waited_from is not None:
        _say(
            f"ACQUIRED {lock_path} after {time.monotonic() - waited_from:.1f}s "
            f"(previous holder: {describe(holder)})"
        )

    try:
        return _spawn(cmd, os.environ, lock_path)
    finally:
        try:
            os.ftruncate(fd, 0)
        except OSError:
            pass
        os.close(fd)  # releases the flock


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _selftest_tmpdir() -> str:
    for candidate in (os.environ.get("TMPDIR", ""), "/tmp/opencode"):
        if candidate and Path(candidate).is_dir():
            return candidate
    return tempfile.gettempdir()


def cmd_self_test(keep: bool) -> int:
    script = str(Path(__file__).resolve())
    py = sys.executable
    tmp = Path(tempfile.mkdtemp(prefix="gate-lock-selftest-", dir=_selftest_tmpdir()))
    lock = tmp / "gate.lock"
    env = {k: v for k, v in os.environ.items() if k not in (ENV_HELD,)}
    env[ENV_VERBOSE] = "1"
    failures = 0
    checks = 0

    def report(name: str, ok: bool, detail: str) -> None:
        nonlocal failures, checks
        checks += 1
        print(f"self-test {name}: {'PASS' if ok else 'FAIL'} ({detail})", flush=True)
        if not ok:
            failures += 1

    def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)

    try:
        # S1 -- same-tree nesting is allowed (and verified as such).
        inner = [py, script, "run", "--lock", str(lock), "--wait", "0",
                 "--target", "inner", "--", py, "-c", "print('inner-ran')"]
        outer = [py, script, "run", "--lock", str(lock), "--wait", "5",
                 "--target", "outer", "--"] + inner
        p = run(outer)
        report(
            "S1 same-tree-nesting-allowed",
            p.returncode == 0 and "inner-ran" in p.stdout and "nested:" in p.stderr,
            f"rc={p.returncode}, inner-ran={'inner-ran' in p.stdout}, nested-marker={'nested:' in p.stderr}",
        )

        # S1b -- the marker alone must NOT disable the mutex (no ancestral holder).
        # Needs /proc to tell "not an ancestor"; without it the marker is trusted
        # by design, so the case is reported as SKIP instead of a false FAIL.
        if PROC_AVAILABLE:
            spoof_env = dict(env)
            spoof_env[ENV_HELD] = str(lock)
            p = subprocess.run(
                [py, script, "run", "--lock", str(lock), "--wait", "1", "--target", "spoof",
                 "--", py, "-c", "print('spoof-ran')"],
                capture_output=True, text=True, env=spoof_env,
            )
            report(
                "S1b stale-marker-still-acquires",
                p.returncode == 0 and "no ancestor holds" in p.stderr and "spoof-ran" in p.stdout,
                f"rc={p.returncode}, warning={'no ancestor holds' in p.stderr}",
            )
        else:
            print("self-test S1b stale-marker-still-acquires: SKIP (no /proc: marker is trusted)", flush=True)

        # S2 -- an independent process is rejected while the lock is held.
        holder = subprocess.Popen(
            [py, script, "run", "--lock", str(lock), "--wait", "10", "--target", "holder",
             "--", py, "-c", "import time; time.sleep(2.0)"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        recorded = False
        t0 = time.monotonic()
        while time.monotonic() - t0 < 5.0:
            if read_holder(lock).get("pid"):
                recorded = True
                break
            time.sleep(0.05)
        t0 = time.monotonic()
        intruder = run([py, script, "run", "--lock", str(lock), "--wait", "0.6",
                        "--target", "intruder", "--", py, "-c", "print('intruder-ran')"])
        elapsed = time.monotonic() - t0
        report(
            "S2 independent-process-rejected",
            intruder.returncode == EXIT_BUSY
            and "held by" in intruder.stderr
            and "pid=" in intruder.stderr
            and "intruder-ran" not in intruder.stdout
            and elapsed < 2.0,
            f"rc={intruder.returncode} (want {EXIT_BUSY}), elapsed={elapsed:.2f}s, "
            f"holder-reported={'pid=' in intruder.stderr}",
        )
        t0 = time.monotonic()
        fast = run([py, script, "run", "--lock", str(lock), "--wait", "60", "--failfast", "1",
                    "--target", "failfast", "--", py, "-c", "print('failfast-ran')"])
        fast_elapsed = time.monotonic() - t0
        report(
            "S2b failfast-immediate",
            fast.returncode == EXIT_BUSY and fast_elapsed < 1.0 and "GATE_LOCK_FAILFAST=1" in fast.stderr,
            f"rc={fast.returncode} (want {EXIT_BUSY}), elapsed={fast_elapsed:.2f}s",
        )
        # S4 -- bounded wait proceeds once the holder releases.
        t0 = time.monotonic()
        waiter = run([py, script, "run", "--lock", str(lock), "--wait", "10",
                      "--target", "waiter", "--", py, "-c", "print('waiter-ran')"])
        wait_elapsed = time.monotonic() - t0
        holder_rc = holder.wait(timeout=10)
        report(
            "S4 bounded-wait-then-proceed",
            waiter.returncode == 0 and "waiter-ran" in waiter.stdout and wait_elapsed >= 0.3,
            f"rc={waiter.returncode}, elapsed={wait_elapsed:.2f}s, holder-rc={holder_rc}",
        )
        report(
            "S2c holder-record-written",
            recorded,
            f"holder pid recorded={'yes' if recorded else 'no'}",
        )

        # S3 -- an unusable lock path is a hard, explicit failure (command not run).
        blocker = tmp / "not-a-dir"
        blocker.write_text("x")
        p = run([py, script, "run", "--lock", str(blocker / "gate.lock"), "--wait", "1",
                 "--target", "unavailable", "--", py, "-c", "print('unavailable-ran')"])
        report(
            "S3 lock-unavailable-fails-closed",
            p.returncode == EXIT_UNAVAILABLE
            and "UNAVAILABLE" in p.stderr
            and "unavailable-ran" not in p.stdout,
            f"rc={p.returncode} (want {EXIT_UNAVAILABLE}), refused-to-run="
            f"{'unavailable-ran' not in p.stdout}",
        )

        # Green restore: the lock is free again after every holder exited.
        p = run([py, script, "run", "--lock", str(lock), "--wait", "1",
                 "--target", "final", "--", py, "-c", "print('final-ran')"])
        report(
            "S5 released-lock-reacquired",
            p.returncode == 0 and "final-ran" in p.stdout,
            f"rc={p.returncode}",
        )
    finally:
        if keep:
            print(f"self-test tmp kept: {tmp}", flush=True)
        else:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)

    print(f"self-test: {checks - failures}/{checks} PASS", flush=True)
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gate_lock.py",
        description="Per-worktree gate lock (INFRA-099t / ISS-229).",
    )
    parser.add_argument("--self-test", action="store_true", help="run the injection self-test and exit")
    parser.add_argument("--keep", action="store_true", help="keep the self-test temp dir")
    sub = parser.add_subparsers(dest="mode")

    run_p = sub.add_parser("run", help="run CMD under the worktree lock")
    run_p.add_argument("--lock", required=True, help="lock file path (Makefile: $(GATE_LOCK))")
    run_p.add_argument("--wait", type=float, default=3600.0, help="wait bound in seconds (GATE_LOCK_WAIT)")
    run_p.add_argument("--failfast", nargs="?", const="1", default="0", help="1 = one non-blocking attempt")
    run_p.add_argument("--target", default="", help="target name (for the holder record / diagnostics)")
    run_p.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command to run")

    args = parser.parse_args(argv)
    if args.self_test:
        return cmd_self_test(args.keep)
    if args.mode == "run":
        return cmd_run(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
