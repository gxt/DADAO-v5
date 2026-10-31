"""Reap children when a test runner is killed from outside (TESTCASES-085t).

The llvm-ts driver runs every qemu in its own session (``start_new_session``)
so that a timeout can ``killpg`` the whole emulator, and the libc/embench
drivers run theirs in the runner's process group.  When an external
``SIGTERM``/``SIGINT``/``SIGHUP`` hits the runner, Python's default action
terminates it *without* running ``finally``/``atexit``, so an own-session
qemu survives as ``ppid=1`` (a real leak seen in the nightly run).

This module keeps a registry of the children a runner spawned itself and, on
those signals, kills them before re-raising the signal with its default
action (the runner still dies *by signal*, rc=143/130/129).  Only the standard
library is used; the registry is modified only by :func:`track` /
:func:`release` (atomic add/discard under the GIL), and the signal handler
works on a snapshot and never takes a lock.

Safety rules (no global kill-by-name, no matching on external process-listing
output):

* the runner's own pid and process group are never signalled;
* an own-session record (``pgid == pid``) is killed with ``killpg``, anything
  else with ``kill(pid)`` -- the runner's own group is never ``killpg``'d;
* a recorded ``/proc/<pid>/stat`` start time is compared with the live one so
  a recycled PID is skipped;
* on cleanup, direct children of this process (``ppid == os.getpid()``) that
  are not registered yet (the window between ``Popen`` returning and
  ``track``) are swept too;
* when ``/proc`` is unavailable the start-time check and the sweep degrade to
  the registry alone instead of failing.
"""

import atexit
import os
import signal
import subprocess
import time

__all__ = [
    "track",
    "release",
    "kill_tracked",
    "install",
    "uninstall",
    "popen_tracked",
    "run_tracked",
]

# pid -> (pid, pgid, own_group, starttime-or-None)
_REGISTRY = {}
_HANDLER_SIGNOS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
_saved_handlers = {}
_installed = False
_HAS_PROC = os.path.isdir("/proc")


def _stat_fields(pid):
    """Tokens of ``/proc/<pid>/stat`` after the ``(comm)`` field, or None.

    Field 3 (``state``) becomes index 0, so ``ppid`` is index 1, ``pgrp``
    index 2 and ``starttime`` (field 22) index 19.  The comm may contain
    spaces and parentheses, hence the split at the *last* ``)``.
    """
    if not _HAS_PROC:
        return None
    try:
        with open("/proc/%d/stat" % pid, "r") as fh:
            data = fh.read()
    except OSError:
        return None
    close = data.rfind(")")
    if close < 0:
        return None
    return data[close + 2:].split()


def _starttime(pid):
    fields = _stat_fields(pid)
    if not fields or len(fields) < 20:
        return None
    try:
        return int(fields[19])
    except ValueError:
        return None


def _still_same(pid, recorded):
    """False when the pid is ours/gone or has been reused by another process."""
    if pid == os.getpid():
        return False
    if not _HAS_PROC:
        return True                    # no /proc: fall back to the pid alone
    current = _starttime(pid)
    if current is None:
        return False                   # gone (or unreadable) => nothing to do
    return recorded is None or current == recorded


def _signal_one(pid, pgid, signo, own_group):
    """Signal one registered/direct child; returns True when a signal was sent."""
    if pid == os.getpid():
        return False
    own_group = bool(own_group and pgid == pid)
    if own_group and pgid == os.getpgrp():
        return False                   # never killpg our own process group
    try:
        if own_group:
            os.killpg(pgid, signo)
        else:
            os.kill(pid, signo)
    except OSError:
        return False
    return True


def _direct_children():
    """(pid, pgrp) of every direct child of this process (empty without /proc)."""
    if not _HAS_PROC:
        return []
    try:
        names = os.listdir("/proc")
    except OSError:
        return []
    me = os.getpid()
    children = []
    for name in names:
        if not name.isdigit():
            continue
        fields = _stat_fields(int(name))
        if not fields or len(fields) < 20:
            continue
        try:
            if int(fields[1]) == me and fields[0] != "Z":
                children.append((int(name), int(fields[2])))
        except (IndexError, ValueError):
            continue
    return children


def track(proc):
    """Register ``proc`` and return it (no-op for objects without ``pid``)."""
    pid = getattr(proc, "pid", None)
    if pid is None:
        return proc
    try:
        pgid = os.getpgid(pid)
    except OSError:
        pgid = pid
    _REGISTRY[pid] = (pid, pgid, pgid == pid, _starttime(pid))
    return proc


def release(proc):
    """Drop ``proc`` from the registry (call from ``finally``)."""
    pid = getattr(proc, "pid", None)
    if pid is not None:
        _REGISTRY.pop(pid, None)


def kill_tracked(signo=signal.SIGKILL):
    """Kill every live registered child plus unregistered direct children.

    Returns the list of pids a signal was actually sent to.  Reads a snapshot
    of the registry only, so it is safe to call from a signal handler.
    """
    killed = []
    handled = set()
    for pid, pgid, own_group, starttime in tuple(_REGISTRY.values()):
        if not _still_same(pid, starttime):
            continue
        handled.add(pid)
        if _signal_one(pid, pgid, signo, own_group):
            killed.append(pid)
    for pid, pgid in _direct_children():
        if pid in handled:
            continue
        if _signal_one(pid, pgid, signo, pgid == pid):
            killed.append(pid)
    return killed


def _handler(signo, frame):
    # A worker thread can spawn one more child right after the first sweep
    # (e.g. the llvm-ts driver starts its -strace probe when the just-killed
    # qemu returns rc=-9).  Give the threads a moment and sweep again, so that
    # late child is not orphaned either; the budget is bounded (2 x 50 ms).
    try:
        kill_tracked()
        time.sleep(0.05)
        kill_tracked()
        time.sleep(0.05)
        kill_tracked()
    except Exception:                  # never let cleanup hide the signal
        pass
    signal.signal(signo, signal.SIG_DFL)
    os.kill(os.getpid(), signo)        # die *by* the signal (rc=128+signo)


def _atexit_cleanup():
    kill_tracked()


def install():
    """Install the SIGTERM/SIGINT/SIGHUP cleanup handler (idempotent).

    ``atexit`` is registered once and acts only as a fallback for a normal
    exit path that forgot to ``release``.
    """
    global _installed
    if _installed:
        return
    _installed = True
    for signo in _HANDLER_SIGNOS:
        _saved_handlers[signo] = signal.getsignal(signo)
        signal.signal(signo, _handler)
    atexit.register(_atexit_cleanup)


def uninstall():
    """Restore the handlers saved by :func:`install` (idempotent)."""
    global _installed
    if not _installed:
        return
    _installed = False
    for signo in _HANDLER_SIGNOS:
        try:
            signal.signal(signo, _saved_handlers.get(signo, signal.SIG_DFL))
        except (OSError, ValueError):
            pass
    _saved_handlers.clear()
    try:
        atexit.unregister(_atexit_cleanup)
    except (AttributeError, ValueError):
        pass


def popen_tracked(cmd, **kwargs):
    """``subprocess.Popen`` + immediate :func:`track`.

    ``start_new_session`` (and every other Popen kwarg) stays the caller's
    decision.
    """
    return track(subprocess.Popen(cmd, **kwargs))


def run_tracked(cmd, timeout=None, **kwargs):
    """``subprocess.run`` equivalent whose child is tracked while it runs.

    Same timeout semantics as ``subprocess.run``: on expiry the *pid* is
    killed (no ``killpg``), output is collected and a ``TimeoutExpired`` is
    raised carrying it.  ``input``/``cwd``/``stdout``/``stderr`` pass through.
    """
    input_data = kwargs.pop("input", None)
    if input_data is not None:
        if "stdin" in kwargs:
            raise ValueError("stdin and input arguments may not both be used.")
        kwargs["stdin"] = subprocess.PIPE
    proc = popen_tracked(cmd, **kwargs)
    try:
        try:
            out, err = proc.communicate(input=input_data, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            raise subprocess.TimeoutExpired(cmd, timeout, output=out,
                                            stderr=err)
        return subprocess.CompletedProcess(cmd, proc.returncode, out, err)
    finally:
        release(proc)
