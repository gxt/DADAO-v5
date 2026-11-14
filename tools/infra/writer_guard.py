#!/usr/bin/env python3
"""Shared build-tree / install-root writer registry + fail-closed read guard.

Why (``ISS-373``, P1): several tasks share ``.work/build/**``, ``.work/source/**``
and the install root (``.dadao/**``, ``manifests/install-dirs.lock.toml``).
Task worktrees symlink ``.work``/``.dadao`` into the main worktree, so a build
started by one session *replaces binaries another session is reading*:

* ``m16-gem5-008`` rebuilt ``gem5.opt`` while three review batches were reading
  it => 0-byte / half-written / silently replaced binaries => **false FAIL**
  (blamed on the code until the environment was found);
* the mirror image is **false PASS**: a batch that read the *old* binary proves
  nothing about the current source.

``gate.lock`` (``docs/Process-07 §2``) only serializes make targets inside one
worktree and says nothing to a *reader*: a review runs
``python3 tools/testcases/inst/run_asm_suite.py`` directly, takes no lock, and
cannot tell that ``gem5.opt`` is being rewritten.

Two mechanisms, both mechanical:

1. **Writer registry** (``.dadao/writers/<component>.json``, one JSON record per
   active writer; collisions get ``<component>.<pid>.json`` so a second writer
   never clobbers a live record): every guarded build target is wrapped by
   ``writer_guard.py run``, which writes
   ``{schema, component, target, pid, pid_start, host, started, duration,
   expires, git_head, cwd, cmd}`` before the build starts and deletes the file
   after it ends (``finally`` + ``SIGTERM/SIGINT/SIGHUP`` handlers).
   Nested writers (same make tree) pass through: the recorded holder's pid is an
   *ancestor* of this process, so it is the same write in progress.
2. **Read guard** (``ReadGuard`` / ``start_guard``/``finish_guard``): a batch or
   evidence entry (a) refuses to start when a component it is about to read has
   a **live foreign writer** -- rc 75, unless ``--allow-concurrent``
   (``DADAO_ALLOW_CONCURRENT=1``) is given explicitly, which is logged to
   ``<state>/overrides.log``; (b) hashes every binary it uses **at start and at
   end**; any difference => FAIL ("binary was replaced while the batch ran").

Stale records (writer killed with SIGKILL, host rebooted, record garbled) are
detected mechanically -- never by memory:

* ``pid`` no longer exists (``kill(pid, 0)`` => ESRCH) => stale;
* ``pid`` alive but ``/proc/<pid>/stat`` start-time differs from the recorded
  ``pid_start`` => pid reuse => stale;
* record host != this host, or ``/proc`` unavailable => pid cannot be checked,
  so the record is stale only once ``expires`` (``started + duration``) passed;
* unparseable JSON => **treated as active** when reading (fail closed) and
  removable by ``clean``.

An ``expires`` that passed while the pid is still alive is *not* stale (a long
build is not a dead build): it stays live (fail closed for readers) and is
reported as ``overdue``.

Known boundary: the reader guards protect the wired entries only
(``check-writer-guards`` asserts each one still calls the guard); per-task
one-off probes (``tools/testcases/arch/min_rom_probe_*.py``) are not wired and
still rely on their task book's md5 assertions.

The registry path can be overridden for self-tests / diagnosis
(``--state-dir`` or ``DADAO_WRITER_STATE_DIR``).  That hook can bypass the
guard, so whenever it is in effect the process prints
``WARNING: writer-state-dir overridden via …; the writer registry (and therefore
the read guard) may be bypassed`` to stderr and appends the same fact to
``<state>/state-dir-override.log`` (never silent).

CLI::

    writer_guard.py run --component C [--component C ...] --target T
                        [--duration S] [--state-dir D] -- CMD...
    writer_guard.py begin --component C --target T [--duration S] [--state-dir D]
    writer_guard.py end   --component C [--state-dir D]
    writer_guard.py status [--json] [--state-dir D]
    writer_guard.py clean [--component C] [--state-dir D]
    writer_guard.py check --component C [--allow-concurrent] [--state-dir D]
    writer_guard.py read-run --component C --binary PATH [--binary PATH ...]
                        [--allow-concurrent] [--state-dir D] -- CMD...
    writer_guard.py --self-test [--keep]

Exit codes: ``check``/``read-run`` refuse with 75 (``EX_TEMPFAIL``, same code as
``gate_lock.py`` busy) when a live writer exists; the read guard fails with 1
when a snapshot differs; unusable state dir => 69 (never silently skipped).
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

EXIT_BUSY = 75          # a live writer holds the component (EX_TEMPFAIL)
EXIT_UNAVAILABLE = 69   # state dir unusable (EX_UNAVAILABLE)
EXIT_MISMATCH = 1       # binary changed between start and finish
SCHEMA = "dadao-writer/1"
ENV_STATE_DIR = "DADAO_WRITER_STATE_DIR"
ENV_ALLOW_CONCURRENT = "DADAO_ALLOW_CONCURRENT"
DEFAULT_DURATION = 4 * 3600
PROC_AVAILABLE = Path("/proc/self/stat").is_file()

# Components and the trees each one owns (repo-relative).  Longest prefix wins,
# so the QEMU binaries inside the shared install-root ``bin/`` map to ``qemu``
# while the rest of that ``bin/`` maps to ``llvm``.
COMPONENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "llvm": ("LLVM build tree + install-root LLVM tools",
             (".work/build/llvm",
              ".dadao/cross-toolchain/bin",
              ".dadao/host-tools/bin")),
    "qemu": ("QEMU build tree + install-root qemu binaries",
             (".work/build/qemu",
              ".dadao/cross-toolchain/bin/qemu-system-dadao",
              ".dadao/cross-toolchain/bin/qemu-dadao")),
    "gem5": ("gem5 source/build tree (gem5.opt)",
             (".work/source/gem5", ".work/build/gem5")),
    "chipyard": ("chipyard source/build tree (Verilator harness)",
                 (".work/source/chipyard",)),
    "bootrom": ("SEE bootrom images under the artifacts root",
                (".dadao/tests/bootrom",)),
    "sysroot": ("target sysroot + the musl/picolibc build trees it is built from",
                (".dadao/dadao-unknown-elf", ".work/source/musl",
                 ".work/source/picolibc")),
    "linux": ("Linux kernel build tree",
              (".work/build/linux",)),
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _say(message: str) -> None:
    print(f"writer-guard: {message}", file=sys.stderr, flush=True)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def _pid_start(pid: int) -> int | None:
    """The process start time (``/proc/<pid>/stat`` field 22), or None.

    Used to tell "the recorded pid is still the same process" from "the pid was
    recycled after a crash/reboot".
    """
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8",
                                                   errors="replace")
    except OSError:
        return None
    try:
        fields = stat.rsplit(")", 1)[1].split()
        return int(fields[19])          # starttime is field 22 overall
    except (IndexError, ValueError):
        return None


def _ancestors() -> list[int]:
    out: list[int] = []
    pid = os.getpid()
    for _ in range(64):
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8",
                                                       errors="replace")
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            return out
        if ppid <= 1:
            return out
        out.append(ppid)
        pid = ppid
    return out


def state_dir_source(override: str | os.PathLike | None = None) -> tuple[Path, str]:
    """Resolve the writer state dir and report where it came from.

    The override is a *test/diagnostic* hook only: pointing the registry
    somewhere else silently weakens the read guard, so every user of it warns
    (``_warn_state_override``).
    """
    if override:
        return Path(override).resolve(), "--state-dir"
    env = os.environ.get(ENV_STATE_DIR, "")
    if env:
        return Path(env).resolve(), f"env {ENV_STATE_DIR}"
    try:
        sys.path.insert(0, str(_REPO / "tools" / "infra"))
        import paths  # noqa: WPS433 (local import keeps --help independent)

        return (paths.sdk_dir() / "writers").resolve(), "sdk default"
    except (Exception, SystemExit):  # manifest missing/corrupt
        return (_REPO / ".dadao" / "writers").resolve(), "sdk default"


_WARNED_OVERRIDE = False


def _warn_state_override(path: Path, source: str) -> None:
    """Loud, once-per-process warning when the registry path is overridden."""
    global _WARNED_OVERRIDE
    if _WARNED_OVERRIDE:
        return
    _WARNED_OVERRIDE = True
    _say(f"WARNING: writer-state-dir overridden via {source} -> {path}; the "
         f"writer registry (and therefore the read guard) may be bypassed — "
         f"test/diagnostic hook only (ISS-373)")
    try:
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "state-dir-override.log", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": _fmt(_utc_now()), "pid": os.getpid(),
                                 "source": source, "state_dir": str(path),
                                 "argv": sys.argv, "cwd": os.getcwd()},
                                sort_keys=True) + "\n")
    except OSError:
        pass                     # already warned; unwritable is reported elsewhere


def state_dir(override: str | os.PathLike | None = None) -> Path:
    """Writer state directory: ``--state-dir`` > env > ``<sdk>/writers``."""
    path, source = state_dir_source(override)
    if source != "sdk default":
        _warn_state_override(path, source)
    return path


def _real(path: str | os.PathLike) -> str:
    return os.path.realpath(os.path.abspath(os.fspath(path)))


def component_of(path: str | os.PathLike) -> str | None:
    """Which component owns ``path`` (longest matching root), or None."""
    target = _real(path)
    best: tuple[int, str] | None = None
    for name, (_desc, roots) in COMPONENTS.items():
        for root in roots:
            real_root = _real(_REPO / root)
            if target == real_root or target.startswith(real_root + os.sep):
                if best is None or len(real_root) > best[0]:
                    best = (len(real_root), name)
    return best[1] if best else None


def derive_components(paths: list[str]) -> list[str]:
    """Components behind the binaries a reader is about to use (sorted)."""
    found = {component_of(p) for p in paths}
    return sorted(c for c in found if c)


def md5_of(path: str | os.PathLike) -> str:
    """``md5:<hex>`` / ``missing`` / ``unreadable:<errno>`` (never raises)."""
    try:
        with open(path, "rb") as fh:
            digest = hashlib.md5()
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        return "md5:" + digest.hexdigest()
    except FileNotFoundError:
        return "missing"
    except OSError as exc:
        return "unreadable:%s" % (exc.errno,)


def snapshot(paths: list[str]) -> dict[str, str]:
    """Map path -> content fingerprint (the start/finish comparison unit)."""
    return {p: md5_of(p) for p in paths}


def snapshot_diff(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Human-readable differences (empty = identical)."""
    out = []
    for path in sorted(set(before) | set(after)):
        old = before.get(path, "<absent-at-start>")
        new = after.get(path, "<absent-at-finish>")
        if old != new:
            out.append(f"{path}: {old} -> {new}")
    return out


# ---------------------------------------------------------------------------
# writer registry
# ---------------------------------------------------------------------------

def _record_paths(state: Path) -> list[Path]:
    try:
        return sorted(p for p in state.glob("*.json") if p.is_file())
    except OSError:
        return []


def read_record(path: Path) -> dict | None:
    """Parsed record, or None when unparseable/missing."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def evaluate(record: dict | None, path: Path, now: datetime | None = None) -> dict:
    """Mechanical status of one record: ``live`` / ``stale`` / ``unknown``."""
    now = now or _utc_now()
    if record is None:
        return {"state": "unknown", "reason": "record unreadable/garbled",
                "record": {}, "path": path}
    pid = record.get("pid")
    expires = _parse(record.get("expires")) or _parse(record.get("started"))
    host = record.get("host")
    this_host = socket.gethostname()
    if not isinstance(pid, int):
        return {"state": "unknown", "reason": "record has no integer pid",
                "record": record, "path": path}
    if host and host != this_host:
        if expires and now > expires:
            return {"state": "stale",
                    "reason": f"record from host {host!r} expired {_fmt(expires)}",
                    "record": record, "path": path}
        return {"state": "live",
                "reason": f"record from host {host!r} (pid not checkable here)",
                "record": record, "path": path}
    if not _pid_alive(pid):
        return {"state": "stale", "reason": f"pid {pid} is gone",
                "record": record, "path": path}
    recorded_start = record.get("pid_start")
    actual_start = _pid_start(pid) if PROC_AVAILABLE else None
    if isinstance(recorded_start, int) and actual_start is not None \
            and recorded_start != actual_start:
        return {"state": "stale",
                "reason": f"pid {pid} was recycled (start-time {actual_start} != "
                          f"{recorded_start})",
                "record": record, "path": path}
    if actual_start is None and expires and now > expires:
        return {"state": "stale",
                "reason": f"pid {pid} unverifiable and record expired {_fmt(expires)}",
                "record": record, "path": path}
    overdue = bool(expires and now > expires)
    return {"state": "live",
            "reason": "writer is running" + (
                f" (overdue: declared duration ended {_fmt(expires)})"
                if overdue else ""),
            "record": record, "path": path}


def describe(status_entry: dict) -> str:
    rec = status_entry.get("record") or {}
    parts = []
    if rec.get("component"):
        parts.append(f"component={rec['component']}")
    if rec.get("target"):
        parts.append(f"target={rec['target']}")
    if rec.get("pid") is not None:
        parts.append(f"pid={rec['pid']}")
    if rec.get("started"):
        parts.append(f"since {rec['started']}")
    if rec.get("host"):
        parts.append(f"host={rec['host']}")
    if rec.get("git_head"):
        parts.append(f"git={rec['git_head']}")
    return ", ".join(parts) if parts else "record fields unknown"


def all_status(state: Path, components: list[str] | None = None) -> list[dict]:
    wanted = set(components or [])
    out = []
    for path in _record_paths(state):
        record = read_record(path)
        comp = (record or {}).get("component")
        # A garbled record has no component: it cannot be attributed, so it is
        # kept for every query (fail closed) instead of being filtered away.
        if wanted and comp is not None and comp not in wanted:
            continue
        out.append(evaluate(record, path))
    return out


def live_records(state: Path, components: list[str] | None = None,
                 exclude_ancestors: bool = False) -> list[dict]:
    """Live (non-stale) records for ``components``.

    ``exclude_ancestors`` drops writers this process descends from (same make
    tree: the write already happened or is this pipeline's own prerequisite).
    Unreadable records count as live (fail closed).
    """
    ancestors = set(_ancestors()) if exclude_ancestors else set()
    out = []
    for entry in all_status(state, components):
        if entry["state"] == "stale":
            continue
        pid = (entry["record"] or {}).get("pid")
        if exclude_ancestors and isinstance(pid, int) and pid in ancestors:
            continue
        out.append(entry)
    return out


def purge_stale(state: Path, components: list[str] | None = None) -> list[str]:
    """Remove stale records; returns the removed file names (never live ones)."""
    removed = []
    for entry in all_status(state, components):
        if entry["state"] != "stale":
            continue
        try:
            entry["path"].unlink()
            removed.append(entry["path"].name)
        except OSError:
            pass
    return removed


def _git_head() -> str:
    try:
        out = subprocess.run(["git", "-C", str(_REPO), "rev-parse", "--short",
                              "HEAD"], capture_output=True, text=True,
                             timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    os.replace(tmp, path)


def begin(state: Path, components: list[str], target: str,
          duration: float = DEFAULT_DURATION,
          cmd: list[str] | None = None) -> list[Path]:
    """Register this process as writer of ``components``; returns record paths.

    Nested writers (a recorded holder is an ancestor of this process) register
    nothing -- their write is already covered by the ancestor's record.
    """
    state.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    purged = purge_stale(state, components)
    if purged:
        _say(f"cleaned {len(purged)} stale record(s) for "
             f"{','.join(components)}: {' '.join(purged)}")
    for comp in components:
        live = live_records(state, [comp])
        if any(isinstance((e["record"] or {}).get("pid"), int)
               and (e["record"]["pid"] in set(_ancestors())) for e in live):
            _say(f"nested: component {comp} is already being written by an "
                 f"ancestor ({describe(live[0])}); not registering a second record")
            continue
        name = f"{comp}.json"
        path = state / name
        if path.exists():
            name = f"{comp}.{os.getpid()}.json"
            path = state / name
            _say(f"WARN concurrent writer for component {comp}: {describe(live[0]) if live else 'record present'}"
                 f"; registering {name} instead of clobbering it")
        now = _utc_now()
        record = {
            "schema": SCHEMA,
            "component": comp,
            "target": target,
            "pid": os.getpid(),
            "pid_start": _pid_start(os.getpid()),
            "host": socket.gethostname(),
            "started": _fmt(now),
            "duration": int(duration),
            "expires": _fmt(now + timedelta(seconds=max(0, int(duration)))),
            "git_head": _git_head(),
            "cwd": os.getcwd(),
            "cmd": cmd or [],
            "token": uuid.uuid4().hex,
        }
        _write_record(path, record)
        created.append(path)
    return created


def end(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            _say(f"WARN cannot remove writer record {path}: {exc}")


# ---------------------------------------------------------------------------
# reader side
# ---------------------------------------------------------------------------

class ReadGuard:
    """Fail-closed guard around one batch/evidence run.

    ``start()`` refuses (rc 75) when a component it reads has a live foreign
    writer; ``finish()`` re-hashes the binaries and returns False (=> the entry
    must exit non-zero) when anything changed mid-run.
    """

    def __init__(self, paths: list[str], allow_concurrent: bool = False,
                 label: str = "", state: Path | None = None):
        self.paths = [p for p in (str(x) for x in paths if x)]
        self.allow_concurrent = allow_concurrent
        self.label = label or Path(sys.argv[0]).name
        self.state = state or state_dir()
        self.components: list[str] = []
        self.before: dict[str, str] = {}
        self._started = False
        self._finished = False

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> "ReadGuard":
        self.components = derive_components(self.paths)
        state = self.state
        if state.exists() and not os.access(state, os.W_OK):
            _say(f"UNAVAILABLE {state}: not writable -- refusing to run "
                 f"'{self.label}' without a readable writer registry "
                 f"(rc={EXIT_UNAVAILABLE})")
            raise SystemExit(EXIT_UNAVAILABLE)
        foreign = live_records(state, self.components, exclude_ancestors=True)
        if foreign and not self.allow_concurrent:
            lines = [f"REFUSED: a writer is active for "
                     f"{','.join(self.components)}:"]
            lines += [f"  - {describe(entry)} [{entry['reason']}]"
                      for entry in foreign]
            lines.append("  wait for it to finish, or pass --allow-concurrent "
                         "(DADAO_ALLOW_CONCURRENT=1) to run anyway and accept "
                         "that the binaries are moving")
            for line in lines:
                print(f"writer-guard: {line}", file=sys.stderr, flush=True)
            raise SystemExit(EXIT_BUSY)
        if foreign:
            self._log_override(foreign)
        self.before = snapshot(self.paths)
        self._started = True
        _say(f"start {self.label}: components={','.join(self.components) or '-'} "
             + " ".join(f"{p}={h}" for p, h in self.before.items()))
        _register_atexit(self)
        return self

    def finish(self) -> bool:
        if not self._started or self._finished:
            return True
        self._finished = True
        after = snapshot(self.paths)
        diff = snapshot_diff(self.before, after)
        _say(f"finish {self.label}: "
             + " ".join(f"{p}={h}" for p, h in after.items()))
        if not diff:
            return True
        print("", file=sys.stderr)
        print("writer-guard: FAIL 二进制在跑批期间被替换 "
              "(binary replaced while the batch ran)", file=sys.stderr)
        for line in diff:
            print(f"  {line}", file=sys.stderr)
        print("  => the observations above cannot be attributed to one binary; "
              "re-run when no writer is active (see docs/Process-07 §2.1)",
              file=sys.stderr, flush=True)
        return False

    # -- internals ----------------------------------------------------------
    def _log_override(self, foreign: list[dict]) -> None:
        now = _fmt(_utc_now())
        for entry in foreign:
            print(f"writer-guard: WARNING --allow-concurrent: ignoring active "
                  f"writer {describe(entry)} [{entry['reason']}]", file=sys.stderr)
        self.state.mkdir(parents=True, exist_ok=True)
        log = self.state / "overrides.log"
        try:
            with open(log, "a", encoding="utf-8") as fh:
                for entry in foreign:
                    fh.write(json.dumps({
                        "at": now, "reader": self.label, "argv": sys.argv,
                        "cwd": os.getcwd(), "pid": os.getpid(),
                        "components": self.components,
                        "writer": entry["record"],
                    }, sort_keys=True) + "\n")
        except OSError as exc:
            _say(f"WARN cannot append {log}: {exc}")
        else:
            _say(f"override recorded in {log}")


_GUARDS: list[ReadGuard] = []


def _register_atexit(guard: ReadGuard) -> None:
    _GUARDS.append(guard)


def _atexit_verify() -> None:
    """Safety net: an entry that returns/exits without ``finish_guard``.

    A mismatch must not slip through as a green run, so print the report and
    force the process status with ``os._exit`` (the interpreter is already
    shutting down at this point).
    """
    pending = [g for g in _GUARDS if g._started and not g._finished]
    if not pending:
        return
    failed = [g for g in pending if not g.finish()]
    if failed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(EXIT_MISMATCH)


import atexit  # noqa: E402  (kept next to its only use)

atexit.register(_atexit_verify)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--allow-concurrent`` switch to an entry's parser."""
    parser.add_argument(
        "--allow-concurrent", action="store_true",
        default=os.environ.get(ENV_ALLOW_CONCURRENT, "") not in ("", "0", "false"),
        help="run even though a build writer is active for a binary this entry "
             "reads; the override is logged to <state>/overrides.log (ISS-373)")


def start_guard(args: argparse.Namespace, paths: list[str],
                label: str = "") -> ReadGuard:
    """Construct + start the read guard (refusal exits 75)."""
    guard = ReadGuard(paths, allow_concurrent=bool(
        getattr(args, "allow_concurrent", False)), label=label)
    return guard.start()


def finish_guard(guard: ReadGuard | None) -> bool:
    """Finish the guard; False => the entry must exit non-zero."""
    return True if guard is None else guard.finish()


def default_reader_paths() -> list[str]:
    """Canonical binaries a whole-suite run (L3 / night) consumes."""
    rel = [
        ".dadao/cross-toolchain/bin/qemu-system-dadao",
        ".dadao/cross-toolchain/bin/qemu-dadao",
        ".work/build/qemu/qemu-system-dadao",
        ".work/source/gem5/build/DADAO/gem5.opt",
        ".work/source/chipyard/sims/verilator/simulator-chipyard.harness-WumingTinyConfig",
    ]
    return [str(_REPO / r) for r in rel]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _clean_components(values: list[str]) -> list[str]:
    unknown = [v for v in values if v not in COMPONENTS]
    if unknown:
        _say(f"unknown component(s) {unknown}; known: {sorted(COMPONENTS)}")
        raise SystemExit(2)
    return values


def cmd_run(args: argparse.Namespace) -> int:
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        _say("run: no command given")
        return 2
    comps = _clean_components(args.component)
    state = state_dir(args.state_dir)
    try:
        paths = begin(state, comps, args.target or cmd[0], args.duration, cmd)
    except OSError as exc:
        _say(f"UNAVAILABLE {state}: {exc} -- refusing to run '{args.target}' "
             f"without a writer registry (rc={EXIT_UNAVAILABLE})")
        return EXIT_UNAVAILABLE
    previous = {}
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        previous[sig] = signal.getsignal(sig)
        signal.signal(sig, _signalled)
    try:
        env = dict(os.environ)
        # close_fds=False keeps make's jobserver pipe alive for the re-entered
        # make (same reason as gate_lock.py).
        proc = subprocess.run(cmd, env=env, close_fds=False)
        return proc.returncode
    except FileNotFoundError:
        _say(f"cannot run {cmd[0]!r}: not found (rc={EXIT_UNAVAILABLE})")
        return EXIT_UNAVAILABLE
    finally:
        end(paths)
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def _signalled(signum, _frame):
    raise SystemExit(128 + signum)


def cmd_begin(args: argparse.Namespace) -> int:
    comps = _clean_components(args.component)
    paths = begin(state_dir(args.state_dir), comps, args.target, args.duration)
    for path in paths:
        print(path)
    return 0


def cmd_end(args: argparse.Namespace) -> int:
    comps = _clean_components(args.component)
    state = state_dir(args.state_dir)
    removed = 0
    for path in _record_paths(state):
        record = read_record(path)
        if not record or record.get("component") not in comps:
            continue
        if record.get("pid") != os.getpid() and args.force_pid is False:
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    print(f"removed {removed} record(s)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = state_dir(args.state_dir)
    comps = _clean_components(args.component) if args.component else None
    entries = all_status(state, comps)
    if args.json:
        print(json.dumps([{k: (str(v) if k == "path" else v)
                           for k, v in entry.items()} for entry in entries],
                         indent=1, sort_keys=True))
    else:
        if not entries:
            print(f"writer-guard: no writer records in {state}")
        for entry in entries:
            print(f"{entry['state']:<8} {entry['path'].name}  "
                  f"{describe(entry)}  [{entry['reason']}]")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    state = state_dir(args.state_dir)
    comps = _clean_components(args.component) if args.component else None
    removed = []
    for entry in all_status(state, comps):
        if entry["state"] == "live":
            continue
        try:
            entry["path"].unlink()
            removed.append(entry["path"].name)
        except OSError:
            pass
    print(f"removed {len(removed)} record(s): {' '.join(removed) or '-'}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    comps = _clean_components(args.component)
    state = state_dir(args.state_dir)
    foreign = live_records(state, comps, exclude_ancestors=True)
    if not foreign:
        print(f"writer-guard: no active writer for {','.join(comps)}")
        return 0
    for entry in foreign:
        _say(f"ACTIVE {describe(entry)} [{entry['reason']}]")
    if args.allow_concurrent:
        _say("--allow-concurrent: proceeding anyway (override logged)")
        probe = ReadGuard([], allow_concurrent=True, label="check",
                          state=state)
        probe.components = comps
        probe._log_override(foreign)
        return 0
    _say(f"REFUSED: component(s) {','.join(comps)} being written (rc={EXIT_BUSY})")
    return EXIT_BUSY


def cmd_read_run(args: argparse.Namespace) -> int:
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        _say("read-run: no command given")
        return 2
    binaries = [p for p in args.binary]
    guard = ReadGuard(binaries, allow_concurrent=args.allow_concurrent,
                      label=args.label or cmd[0], state=state_dir(args.state_dir))
    guard.start()
    proc = subprocess.run(cmd, close_fds=False)
    ok = guard.finish()
    return proc.returncode if ok else (proc.returncode or EXIT_MISMATCH)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _selftest_tmpdir() -> str:
    for candidate in (os.environ.get("TMPDIR", ""), "/tmp/opencode"):
        if candidate and Path(candidate).is_dir():
            return candidate
    return tempfile.gettempdir()


def cmd_self_test(keep: bool) -> int:
    tmp = Path(tempfile.mkdtemp(prefix="writer-guard-selftest-",
                                dir=_selftest_tmpdir()))
    state = tmp / "writers"
    fake = tmp / "gem5.opt"
    fake.write_bytes(b"v1")
    checks = 0
    failures = 0

    def report(name: str, ok: bool, detail: str) -> None:
        nonlocal checks, failures
        checks += 1
        print(f"self-test {name}: {'PASS' if ok else 'FAIL'} ({detail})",
              flush=True)
        if not ok:
            failures += 1

    env = {k: v for k, v in os.environ.items() if k != ENV_STATE_DIR}
    env[ENV_STATE_DIR] = str(state)

    def run(args: list[str], **kw) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(Path(__file__).resolve())]
                              + args, capture_output=True, text=True, env=env,
                              **kw)

    def spawn_writer(component: str, seconds: float) -> subprocess.Popen:
        """A *live* writer: ``run`` holds the record while it sleeps."""
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "run",
             "--component", component, "--target", "holder", "--",
             sys.executable, "-c", f"import time; time.sleep({seconds})"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if any(p.name.startswith(component) for p in state.glob("*.json")):
                return proc
            time.sleep(0.05)
        proc.kill()
        raise RuntimeError("writer record never appeared")

    try:
        # 1) registry lifecycle: record present while the writer runs, gone after.
        holder = spawn_writer("gem5", 2.0)
        record = state / "gem5.json"
        data = json.loads(record.read_text()) if record.is_file() else {}
        report("writer-record-while-running",
               record.is_file() and data.get("target") == "holder"
               and data.get("component") == "gem5"
               and isinstance(data.get("pid"), int) and data.get("host")
               and data.get("started") and data.get("git_head") is not None,
               f"fields={sorted(data)}, exists={record.is_file()}")

        # 2) reader refuses while a live writer exists, green once it is gone.
        p = run(["check", "--component", "gem5"])
        p2 = run(["check", "--component", "gem5", "--allow-concurrent"])
        refused = p.returncode == EXIT_BUSY and "ACTIVE" in p.stderr
        allowed = p2.returncode == 0
        holder.wait(timeout=15)
        report("end-clears-record", not record.exists(),
               f"exists-after-end={record.exists()}, writer-rc={holder.returncode}")
        p3 = run(["check", "--component", "gem5"])
        report("reader-refuses-live-writer",
               refused and allowed and p3.returncode == 0,
               f"refuse rc={p.returncode} (want {EXIT_BUSY}), "
               f"allow rc={p2.returncode}, cleared rc={p3.returncode}")

        # 3) stale (pid gone) is ignored by readers and removable by clean.
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        stale = {"schema": SCHEMA, "component": "gem5", "target": "crashed",
                 "pid": dead.pid, "pid_start": 1, "host": socket.gethostname(),
                 "started": _fmt(_utc_now()), "duration": 60,
                 "expires": _fmt(_utc_now() + timedelta(seconds=60)),
                 "git_head": "deadbeef", "cwd": str(tmp), "cmd": []}
        (state / "gem5.json").write_text(json.dumps(stale))
        p = run(["status"])
        p2 = run(["check", "--component", "gem5"])
        p3 = run(["clean"])
        p4 = run(["clean"])
        report("stale-detected-and-cleaned",
               "stale" in p.stdout and p2.returncode == 0
               and "removed 1 record" in p3.stdout
               and "removed 0 record" in p4.stdout,
               f"status-stale={'stale' in p.stdout}, read rc={p2.returncode}, "
               f"clean={p3.stdout.strip()!r}/{p4.stdout.strip()!r}")

        # 4) garbled record: readers fail closed, clean removes it.
        (state / "gem5.json").write_text("{not json")
        p = run(["check", "--component", "gem5"])
        p2 = run(["clean"])
        report("garbled-record-fails-closed",
               p.returncode == EXIT_BUSY and "removed 1 record" in p2.stdout,
               f"rc={p.returncode} (want {EXIT_BUSY}), clean={p2.stdout.strip()!r}")

        # 5) read guard: unchanged binary => green; replaced mid-run => FAIL.
        p = run(["read-run", "--component", "gem5", "--binary", str(fake),
                 "--", sys.executable, "-c", "print('batch-ran')"])
        report("read-run-green-when-unchanged",
               p.returncode == 0 and "batch-ran" in p.stdout,
               f"rc={p.returncode}")
        p = run(["read-run", "--component", "gem5", "--binary", str(fake), "--",
                 sys.executable, "-c",
                 "open(%r,'wb').write(b'v2')" % str(fake)])
        report("read-run-fails-on-replacement",
               p.returncode == EXIT_MISMATCH
               and "二进制在跑批期间被替换" in p.stderr,
               f"rc={p.returncode} (want {EXIT_MISMATCH}), "
               f"msg={'二进制在跑批期间被替换' in p.stderr}")

        # 6) read-run refuses while a writer is live.
        fake.write_bytes(b"v3")
        holder = spawn_writer("gem5", 2.0)
        p = run(["read-run", "--component", "gem5", "--binary", str(fake),
                 "--", sys.executable, "-c", "print('batch-ran')"])
        holder.wait(timeout=15)
        report("read-run-refuses-live-writer",
               p.returncode == EXIT_BUSY and "batch-ran" not in p.stdout,
               f"rc={p.returncode} (want {EXIT_BUSY}), "
               f"ran={'batch-ran' in p.stdout}")

        # 7) nested writer does not clobber the ancestor's record.
        outer = Path(__file__).resolve()
        inner = [sys.executable, str(outer), "begin", "--component", "gem5",
                 "--target", "inner"]
        p = run(["run", "--component", "gem5", "--target", "outer", "--",
                 *inner])
        report("nested-writer-passes-through",
               p.returncode == 0 and "nested:" in p.stderr
               and not (state / "gem5.json").exists(),
               f"rc={p.returncode}, nested={'nested:' in p.stderr}, "
               f"leftover={(state / 'gem5.json').exists()}")
    finally:
        if keep:
            print(f"self-test tmp kept: {tmp}", flush=True)
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f"self-test: {checks - failures}/{checks} PASS", flush=True)
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="writer_guard.py",
        description="Shared build-tree / install-root writer registry + read "
                    "guard (ISS-373; docs/Process-07 §2.1).")
    parser.add_argument("--self-test", action="store_true",
                        help="run the injection self-test and exit")
    parser.add_argument("--keep", action="store_true",
                        help="keep the self-test temp dir")
    sub = parser.add_subparsers(dest="mode")

    def add_state(p):
        p.add_argument("--state-dir", default=None,
                       help=f"registry dir (default: ${ENV_STATE_DIR} or "
                            f"<sdk>/writers)")

    run_p = sub.add_parser("run", help="register as writer, run CMD, deregister")
    run_p.add_argument("--component", action="append", required=True)
    run_p.add_argument("--target", default="")
    run_p.add_argument("--duration", type=float, default=DEFAULT_DURATION)
    add_state(run_p)
    run_p.add_argument("cmd", nargs=argparse.REMAINDER)

    begin_p = sub.add_parser("begin", help="register as writer (manual)")
    begin_p.add_argument("--component", action="append", required=True)
    begin_p.add_argument("--target", default="manual")
    begin_p.add_argument("--duration", type=float, default=DEFAULT_DURATION)
    add_state(begin_p)

    end_p = sub.add_parser("end", help="deregister this process' records")
    end_p.add_argument("--component", action="append", required=True)
    end_p.add_argument("--force-pid", action="store_true",
                       help="remove records of other pids too")
    add_state(end_p)

    status_p = sub.add_parser("status", help="list writer records + status")
    status_p.add_argument("--component", action="append", default=None)
    status_p.add_argument("--json", action="store_true")
    add_state(status_p)

    clean_p = sub.add_parser("clean", help="remove stale/garbled records")
    clean_p.add_argument("--component", action="append", default=None)
    add_state(clean_p)

    check_p = sub.add_parser("check", help="exit 75 if a live writer exists")
    check_p.add_argument("--component", action="append", required=True)
    check_p.add_argument("--allow-concurrent", action="store_true")
    add_state(check_p)

    rr_p = sub.add_parser("read-run", help="guard a read batch around CMD")
    rr_p.add_argument("--component", action="append", default=None,
                      help="informational; components are derived from --binary")
    rr_p.add_argument("--binary", action="append", required=True)
    rr_p.add_argument("--allow-concurrent", action="store_true")
    rr_p.add_argument("--label", default="")
    add_state(rr_p)
    rr_p.add_argument("cmd", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    if args.self_test:
        return cmd_self_test(args.keep)
    dispatch = {
        "run": cmd_run, "begin": cmd_begin, "end": cmd_end,
        "status": cmd_status, "clean": cmd_clean, "check": cmd_check,
        "read-run": cmd_read_run,
    }
    handler = dispatch.get(args.mode or "")
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
