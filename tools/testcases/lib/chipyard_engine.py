#!/usr/bin/env python3
"""chipyard_engine.py -- Machine-v5-Tiny Verilator-harness run path (m12-chipyard-016).

The tset / picolibc drivers own their corpus enumeration, build lines and
oracles.  This module only swaps the *engine* that runs an already-built ELF:

    qemu     : ``qemu-system-dadao -M dadao-tiny,bootrom-image=... -kernel <elf>``
    chipyard : ``simulator-chipyard.harness-WumingTinyConfig +loadmem=<elf> ...``

Invocation (the pattern ``tests/inst`` has used since m12-chipyard-004)::

    simulator-chipyard.harness-WumingTinyConfig +permissive \
        +loadmem=<elf> +semiout=<out> +max-cycles=<N> [+semicmdline=<line>] \
        +permissive-off none

What the driver reads back
--------------------------
* **guest exit status**: the harness's semihosting responder prints
  ``[WumingSemi] SYS_EXIT(0x18) ... cycle=<N> -> host exit status <S>`` on
  stderr and then calls ``exit(<S>)``.  Only that line makes the process
  status a *guest* status -- a simulator that dies for another reason (a
  ``$fatal``, a missing service, a crash) never produces it.
* **cycle count**: the same line carries the core's simulation cycle counter at
  the ``SYS_EXIT`` trap, i.e. the cycles the guest actually executed.
* **console output / markers**: ``+semiout=<file>`` receives every byte the
  guest writes through ``SYS_WRITEC``/``SYS_WRITE0``/``SYS_WRITE`` (handle 1),
  isolated from the simulator's own stdout.
* **argv for ``SYS_GET_CMDLINE``**: ``+semicmdline=<line>`` -- the same
  space-joined command line QEMU builds from ``-semihosting-config arg=...``.

Fail-closed rules (anti-false-green)
------------------------------------
1. ``+max-cycles`` exhaustion is a **FAIL**, never a pass: the TestDriver prints
   ``*** FAILED *** (timeout) after N simulation cycles`` and ``$fatal``s.
2. The simulator binary's md5 must be the same before and after the run: a
   batch that runs against a binary replaced mid-flight is a **FAIL**.
3. A run whose guest exit status cannot be read from the ``SYS_EXIT`` line is
   **BLOCKED** (platform-side stop), never the case's own verdict.
4. A semihosting service the harness does not implement is **BLOCKED** with the
   service number, never a silent ``0``.

Nothing here decides a case's expected value -- that stays with the corpus.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import time

# The module's own repo root (the harness libs are resolved relative to it, so a
# node run does not depend on the caller's cwd).
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

DEFAULT_SIM = ("sims/verilator/simulator-chipyard.harness-WumingTinyConfig")
DEFAULT_CHIPYARD_ROOT = ".work/source/chipyard"
DEFAULT_MAX_CYCLES = 2_000_000_000

ENGINES = ("qemu", "chipyard")

# `[WumingSemi] SYS_EXIT(0x18) reason=0x20026 code=0x0 cycle=12345 -> host exit status 0`
_SYS_EXIT_RE = re.compile(
    r"\[WumingSemi\] SYS_EXIT\(0x[0-9a-fA-F]+\) reason=0x([0-9a-fA-F]+) "
    r"code=0x([0-9a-fA-F]+) cycle=(\d+) -> host exit status (-?\d+)")
# The TestDriver pads the reason field: `*** FAILED ***      (timeout) after
#      200001 simulation cycles`.
_MAX_CYCLES_RE = re.compile(
    r"\*\*\* FAILED \*\*\*\s*\(timeout\)\s+after\s+(\d+)\s+"
    r"simulation cycles")
_UNIMPLEMENTED_RE = re.compile(
    r"\[WumingSemi\] ERROR: semihosting op 0x([0-9a-fA-F]+) is not implemented")
_VERILATOR_ERROR_RE = re.compile(r"^%Error", re.MULTILINE)


def abspath(repo_root, path):
    return path if os.path.isabs(path) else os.path.join(str(repo_root), path)


def default_sim(repo_root):
    return abspath(repo_root, os.path.join(DEFAULT_CHIPYARD_ROOT, DEFAULT_SIM))


def default_env(repo_root):
    """``LD_LIBRARY_PATH`` the harness binary was linked against."""
    root = abspath(repo_root, DEFAULT_CHIPYARD_ROOT)
    libdirs = [os.path.join(root, ".conda-env", "riscv-tools", "lib"),
               os.path.join(root, ".conda-env", "lib")]
    libdirs = [d for d in libdirs if os.path.isdir(d)]
    old = os.environ.get("LD_LIBRARY_PATH", "")
    if old:
        libdirs.append(old)
    return {"LD_LIBRARY_PATH": ":".join(libdirs)}


def _shared_guard_available():
    """True when ``tools/infra/writer_guard.py`` provides the run-wide guard.

    m13-infra-003 adds a *read* guard (`start_guard`/`finish_guard`) that hashes
    every binary a batch reads at start and at end and fails when one changed --
    exactly the anti-false-green rule this module needs for the simulator.  When
    it is importable the runners call it themselves (that task wires both
    runners), so the per-run md5 check here stands down instead of duplicating
    the enforcement; on a tree without it (this task's base) the local check is
    the only one and stays active.
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    return os.path.isfile(os.path.join(root, "infra", "writer_guard.py"))


def enforce_sim_md5():
    """Whether this module should hash the simulator binary per run."""
    return not _shared_guard_available()


def md5_of(path):
    """Full md5 of a file (``None`` when it cannot be read)."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return b""


def run(elf, outdir, *, sim, timeout, max_cycles=DEFAULT_MAX_CYCLES,
        cmdline=None, env_extra=None, cwd=None):
    """Run one ELF on the chipyard Tiny harness; return the raw observation."""
    os.makedirs(outdir, exist_ok=True)
    semiout = os.path.join(outdir, "semi.out")
    log_path = os.path.join(outdir, "sim.log")
    for path in (semiout, log_path):
        if os.path.exists(path):
            os.unlink(path)

    cmd = [str(sim), "+permissive", "+loadmem=%s" % elf,
           "+semiout=%s" % semiout, "+max-cycles=%s" % max_cycles]
    if cmdline:
        cmd.append("+semicmdline=%s" % cmdline)
    cmd += ["+permissive-off", "none"]

    # The harness binary's DT_NEEDED (libriscv/libfesvr) come from the
    # component's conda env; the build also embeds an rpath to the *build*
    # machine, so a node run needs LD_LIBRARY_PATH or it dies with rc=127.
    env = dict(os.environ)
    env.update(default_env(_REPO))
    if env_extra:
        env.update(env_extra)

    md5_before = md5_of(sim)
    timed_out = False
    rc = None
    started = time.monotonic()
    with open(log_path, "wb") as log:
        try:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, timeout=timeout,
                                  env=env, cwd=cwd)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    seconds = time.monotonic() - started
    md5_after = md5_of(sim)

    text = _read(log_path).decode("utf-8", "replace")
    m = _SYS_EXIT_RE.search(text)
    guest_exit = int(m.group(4)) if m else None
    guest_cycles = int(m.group(3)) if m else None
    m = _MAX_CYCLES_RE.search(text)
    tried_cycles = int(m.group(1)) if m else None
    m = _UNIMPLEMENTED_RE.search(text)
    unimplemented_op = int(m.group(1), 16) if m else None

    return {
        "elf": str(elf), "cmd": cmd, "rc": rc, "timed_out": timed_out,
        "seconds": round(seconds, 2),
        "semiout": _read(semiout), "log": log_path, "sim_text": text,
        "guest_exit": guest_exit, "guest_cycles": guest_cycles,
        "max_cycles": int(max_cycles),
        "cycles_exhausted": tried_cycles is not None,
        "tripped_cycles": tried_cycles,
        "unimplemented_op": unimplemented_op,
        "verilator_error": bool(_VERILATOR_ERROR_RE.search(text)),
        "sim_md5_before": md5_before, "sim_md5_after": md5_after,
        "sim_stable": (md5_before is not None and md5_before == md5_after),
    }


def evaluate(elf, outdir, *, sim, timeout, sim_md5=None,
             max_cycles=DEFAULT_MAX_CYCLES, cmdline=None, env_extra=None,
             cwd=None):
    """Run and normalise the outcome.

    Returned dict:

    * ``status`` ``None`` when the guest really exited (the caller applies its
      own oracle to ``exit``), else ``"FAIL"`` (anti-false-green: the platform
      ran the wrong binary, or the cycle budget was exhausted) or ``"BLOCKED"``
      (a platform gap stopped the case before its verdict);
    * ``exit`` the guest exit status when the guest really exited;
    * ``cycles`` the executed simulation cycles at the ``SYS_EXIT`` trap;
    * ``reason`` human-readable evidence for a non-``None`` status;
    * ``gap`` ``(kind, evidence)`` for a BLOCKED case;
    * ``semiout`` the guest console bytes (markers);
    * ``md5`` the simulator binary's md5 (same before and after);
    * ``seconds`` wall clock.
    """
    result = {"status": None, "exit": None, "cycles": None, "reason": "",
              "gap": None, "semiout": b"", "md5": None, "seconds": 0.0,
              "cmd": [], "log": None, "max_cycles": int(max_cycles),
              "cycles_exhausted": False}
    if sim_md5 is not None and enforce_sim_md5() and md5_of(sim) != sim_md5:
        result.update(status="FAIL",
                      reason=("simulator binary changed before the run: md5 %s "
                              "!= suite baseline %s" % (md5_of(sim), sim_md5)),
                      md5=md5_of(sim))
        return result

    obs = run(elf, outdir, sim=sim, timeout=timeout, max_cycles=max_cycles,
              cmdline=cmdline, env_extra=env_extra, cwd=cwd)
    result.update(semiout=obs["semiout"], seconds=obs["seconds"],
                  cmd=obs["cmd"], log=obs["log"], md5=obs["sim_md5_after"],
                  cycles=obs["guest_cycles"],
                  cycles_exhausted=obs["cycles_exhausted"],
                  tripped_cycles=obs["tripped_cycles"])

    if enforce_sim_md5() and not obs["sim_stable"]:
        result.update(
            status="FAIL",
            reason=("simulator binary replaced during the run: md5 %s -> %s"
                    % (obs["sim_md5_before"], obs["sim_md5_after"])))
        return result
    if obs["timed_out"]:
        result.update(status="BLOCKED",
                      reason="host timeout after %ss (no guest verdict)"
                             % timeout,
                      gap=("time budget", "no SYS_EXIT within %ss" % timeout))
        return result
    if obs["cycles_exhausted"]:
        result.update(
            status="FAIL",
            reason=("+max-cycles=%s exhausted after %d simulation cycles "
                    "(the guest never reached SYS_EXIT)" %
                    (obs["max_cycles"], obs["sim_cycles"]
                     if "sim_cycles" in obs else obs["max_cycles"])),
            gap=("cycle budget", "+max-cycles exhausted"))
        return result
    if obs["unimplemented_op"] is not None:
        result.update(
            status="BLOCKED",
            reason=("chipyard harness: semihosting op 0x%02x is not implemented"
                    % obs["unimplemented_op"]),
            gap=("semihosting service",
                 "op 0x%02x not implemented by the harness responder"
                 % obs["unimplemented_op"]))
        return result
    if obs["guest_exit"] is None:
        why = ("simulator exited without a guest SYS_EXIT (rc=%s)" % obs["rc"])
        if obs["verilator_error"]:
            why += "; log contains a %Error line"
        result.update(status="BLOCKED", reason=why,
                      gap=("simulator/loader", why))
        return result
    if obs["rc"] != obs["guest_exit"]:
        result.update(
            status="BLOCKED",
            reason=("process status %s != the harness-reported guest status %d"
                    % (obs["rc"], obs["guest_exit"])),
            gap=("simulator/loader", "process status / guest status mismatch"))
        return result
    result.update(exit=obs["guest_exit"])
    return result
