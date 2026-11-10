#!/usr/bin/env python3
"""m13-testcases-003: 120 s gem5 SE instruction-count sampling of long-tail cases.

For every case of a case list (the ``run_engine_ratio.py --case-list`` shape)
this tool builds the *same* guest ELF with the case's own suite driver and runs
it through the *same* gem5 SE configuration (``configs/dadao/se.py --binary``,
the driver's own argv / stdin / cwd / guest root), with one difference: the
simulator launch is wrapped in a sample window.  After ``--sample-seconds`` the
simulator receives ``SIGINT`` (``timeout -s INT <N>`` semantics) and the case is
recorded with ``simInsts`` read from the simulator's own ``m5out/stats.txt``.

Why SIGINT: gem5 dumps its statistics on the normal interpreter exit path
(``exitSimLoop("user interrupt received")`` returns from ``m5.simulate``, and
``m5.simulate`` registers ``atexit.register(stats.dump)``), so an interrupted
run still leaves a complete stats file -- no debug build, no ``--debug-*``
consumer, no source change.

How the build line is reused (never re-implemented): each suite's driver is the
owner of the corpus, the compile/link flags, the run cwd, the guest argv/stdin
and the guest root.  This tool calls the driver's own ``main()`` with the
driver's own flags and replaces exactly one seam -- ``gem5_se_engine.evaluate``
(the driver's engine boundary) -- with the sampling launcher.  Everything else
(selection, per-case work dir, ELF-modality gate, classification) stays the
driver's.

Outcomes, per case (never collapsed into one number):

* ``completed``        -- gem5 ended on its own before the window expired;
* ``interrupted_sigint`` -- the window expired, ``SIGINT`` was delivered and gem5
                          exited by itself (statistics dumped);
* ``killed_after_sigint`` -- ``SIGINT`` did not end it inside the grace period,
                          so it was killed (no statistics: ``MISSING``);
* ``launch_failed``    -- the simulator could not be started;
* ``elf_gate``         -- the driver's ELF-modality gate rejected the image
                          before any simulator run;
* ``not_sampled``      -- the driver never reached the engine for this case
                          (e.g. the build failed); the driver's own reason is
                          kept in ``note``.

``simInsts`` is an integer or the string ``MISSING`` -- a truncated run without
statistics is recorded as data, never as ``0``.

Outputs: ``--json-out`` (per-case record, runtime directory, not committed) and
a compact table on stdout.  Nothing here changes a source, a case, an
expectation or a gate, and nothing is deleted: a stale ``m5out`` of a previous
attempt is renamed aside (``*.prev-<stamp>``), never removed.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))

TASK = "m13-testcases-003"

SUITES = ("libc-test", "llvm-ts")

DRIVERS = {
    "libc-test": os.path.join(
        "tools", "testcases", "tset", "libc-test",
        "run_libc_test_user_suite.py"),
    "llvm-ts": os.path.join(
        "tools", "testcases", "tset", "llvm-ts", "run_llvm_ts_user.py"),
}

ENGINE_MODULE = os.path.join("tools", "testcases", "lib", "gem5_se_engine.py")

# The engine's own capability bucket for a run that stopped at a time bound;
# the sampling window is exactly that (a measurement limit, not a verdict).
WINDOW_CAPABILITY = "time budget"
WINDOW_KIND = "sampling-window"

EXIT_CAUSE_RE = re.compile(r"^GEM5_EXIT_CAUSE=(.*)$", re.MULTILINE)
SIM_INSTS_RE = re.compile(r"^simInsts[ \t]+([0-9][0-9.eE+-]*)[ \t]*(?:#.*)?$",
                          re.MULTILINE)


def abspath(path: str, root: str = REPO_ROOT) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def iso_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S")


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:      # pragma: no cover - fixed path
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# the simulator launch (same command shape as gem5_se_engine.run_gem5_se)
# ---------------------------------------------------------------------------
def build_cmd(gem5, m5out, config, elf, guest_out, guest_err, guest_in,
              argv=(), cwd=None, interp_dir=None, redirect=()):
    """The SE command line, identical to ``gem5_se_engine.run_gem5_se``.

    Kept in lockstep by ``--self-test``: that check captures the command the
    engine itself would run (with its child-spawn replaced by a recording stub)
    and compares it with this builder.
    """
    cmd = [gem5, "--outdir", m5out, config, "--binary", elf,
           "--guest-stdout", guest_out, "--guest-stderr", guest_err,
           "--guest-stdin", guest_in]
    if argv:
        cmd += ["--args", " ".join(shlex.quote(a) for a in argv)]
    if cwd:
        cmd += ["--cwd", cwd]
    if interp_dir:
        cmd += ["--interp-dir", interp_dir]
    for app, host in redirect:
        cmd += ["--redirect", f"{app}={host}"]
    return cmd


def archive_if_exists(path: str):
    """Move a previous artifact aside (never delete it)."""
    if not os.path.exists(path):
        return None
    moved = f"{path}.prev-{stamp()}-{os.getpid()}"
    os.rename(path, moved)
    return moved


def read_exit_cause(sim_log: str):
    """``GEM5_EXIT_CAUSE`` from the tail of the simulator log (or ``None``).

    The line is printed when ``m5.simulate`` returns, so the tail is enough and
    a long run's log is never loaded whole.
    """
    try:
        size = os.path.getsize(sim_log)
        with open(sim_log, "r", errors="replace") as fh:
            fh.seek(max(0, size - 65536))
            text = fh.read()
    except OSError:
        return None
    match = EXIT_CAUSE_RE.search(text)
    return match.group(1).strip() if match else None


def read_sim_insts(m5out: str):
    """``(simInsts, note)``; ``simInsts`` is an int or ``"MISSING"``."""
    path = os.path.join(m5out, "stats.txt")
    try:
        with open(path, "r", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return "MISSING", "no stats.txt (simulation did not dump statistics)"
    matches = SIM_INSTS_RE.findall(text)
    if not matches:
        return "MISSING", "stats.txt has no simInsts row"
    try:
        return int(float(matches[-1])), "stats.txt"
    except ValueError:                           # pragma: no cover - regex shape
        return "MISSING", "unparsable simInsts value"


def wait_and_interrupt(proc, window_seconds, grace_seconds):
    """Run the sample window; return ``(rc, signalled, escalated)``."""
    try:
        return proc.wait(timeout=window_seconds), False, False
    except subprocess.TimeoutExpired:
        pass
    # start_new_session=True => the child is its own process group, so the
    # signal reaches the simulator (and nothing of ours) even if it forked.
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    except OSError:
        try:
            proc.send_signal(signal.SIGINT)
        except OSError:
            pass
    try:
        return proc.wait(timeout=grace_seconds), True, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            proc.kill()
        return proc.wait(), True, True


def sample_one(elf, outdir, *, gem5, config, window_seconds, grace_seconds,
               argv=(), stdin_path=None, cwd=None, interp_dir=None,
               redirect=(), reaper=None):
    """Launch one SE run, stop it after the window, read the statistics.

    ``reaper`` is the drivers' ``proc_reap`` module (when available): the child
    is registered there so an external SIGTERM/SIGINT to this runner kills the
    simulator too, instead of leaving 48 orphans behind.
    """
    os.makedirs(outdir, exist_ok=True)
    m5out = os.path.join(outdir, "m5out")
    guest_out = os.path.join(outdir, "guest.stdout")
    guest_err = os.path.join(outdir, "guest.stderr")
    guest_in = stdin_path or os.devnull
    sim_log = os.path.join(outdir, "sim.log")
    moved = [moved for moved in (archive_if_exists(m5out),
                                 archive_if_exists(guest_out),
                                 archive_if_exists(guest_err),
                                 archive_if_exists(sim_log)) if moved]

    cmd = build_cmd(gem5, m5out, config, elf, guest_out, guest_err, guest_in,
                    argv=argv, cwd=cwd, interp_dir=interp_dir,
                    redirect=redirect)
    result = dict(cmd=cmd, m5out=m5out, sim_log=sim_log, rc=None,
                  exit_cause=None, seconds=None, outcome=None, simInsts="MISSING",
                  note=None, archived=moved, window_seconds=window_seconds)
    started = time.monotonic()
    proc = None
    try:
        with open(sim_log, "wb") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, cwd=None,
                                    start_new_session=True)
            if reaper is not None:
                reaper.track(proc)
            rc, signalled, escalated = wait_and_interrupt(
                proc, window_seconds, grace_seconds)
    except OSError as exc:
        result.update(outcome="launch_failed", note=f"{type(exc).__name__}: {exc}",
                      seconds=round(time.monotonic() - started, 2))
        return result
    finally:
        if proc is not None and reaper is not None:
            reaper.release(proc)

    result["seconds"] = round(time.monotonic() - started, 2)
    result["rc"] = rc
    result["exit_cause"] = read_exit_cause(sim_log)
    result["outcome"] = ("interrupted_sigint" if signalled and not escalated
                         else "killed_after_sigint" if escalated
                         else "completed")
    sim_insts, note = read_sim_insts(m5out)
    result["simInsts"] = sim_insts
    result["note"] = note
    return result


# ---------------------------------------------------------------------------
# the sampling seam installed over the driver's engine boundary
# ---------------------------------------------------------------------------
class Sampler:
    """``gem5_se_engine.evaluate`` replacement used by the suite drivers."""

    def __init__(self, engine, mode, work_dir, grace_seconds, case_by_dir,
                 reaper=None):
        self.engine = engine
        self.mode = mode
        self.work_dir = os.path.normpath(work_dir)
        self.grace_seconds = grace_seconds
        self.case_by_dir = case_by_dir
        self.reaper = reaper
        self.results = {}
        self.lock = threading.Lock()

    def _case_of(self, outdir):
        case_dir = os.path.normpath(os.path.dirname(outdir))
        try:
            rel = os.path.relpath(case_dir,
                                  os.path.join(self.work_dir, self.mode))
        except ValueError:                       # pragma: no cover - same drive
            return None, os.path.basename(case_dir)
        return self.case_by_dir.get(rel), rel

    def _record(self, cid, row):
        with self.lock:
            self.results[cid] = row

    def evaluate(self, elf, outdir, *, gem5, config, timeout, musl_root,
                 argv=(), stdin_path=None, cwd=None, max_insts=0,
                 interp_dir=None, redirect=()):
        cid, rel = self._case_of(outdir)
        gate = self.engine.static_gate(elf, interp_dir=interp_dir)
        if gate:
            row = dict(case=cid, elfin=rel, outcome="elf_gate", simInsts="MISSING",
                       exit_cause=None, seconds=None, note=gate)
            self._record(cid or f"unknown:{rel}", row)
            return dict(status="BLOCKED", exit=None, reason=gate,
                        gap=dict(capability="loader/ELF modality",
                                 kind="elf-modality", syscall=None,
                                 syscall_name=None, evidence=gate),
                        stdout=b"", stderr=b"", seconds=0.0, cmd=[],
                        sim_log=None, m5out=None, timed_out=False,
                        exit_cause=None)
        run = sample_one(elf, outdir, gem5=gem5, config=config,
                         window_seconds=timeout,
                         grace_seconds=self.grace_seconds, argv=argv,
                         stdin_path=stdin_path, cwd=cwd,
                         interp_dir=interp_dir, redirect=redirect,
                         reaper=self.reaper)
        row = dict(case=cid, elfin=rel, outcome=run["outcome"],
                   simInsts=run["simInsts"], exit_cause=run["exit_cause"],
                   seconds=run["seconds"], rc=run["rc"],
                   window_seconds=run["window_seconds"], note=run["note"])
        self._record(cid or f"unknown:{rel}", row)
        reason = (f"sampled {run['window_seconds']}s -> SIGINT "
                  f"({run['outcome']}); simInsts={run['simInsts']}"
                  if run["outcome"] != "completed" else
                  f"completed before the {run['window_seconds']}s window; "
                  f"simInsts={run['simInsts']}")
        return dict(status="BLOCKED", exit=None, reason=reason,
                    gap=dict(capability=WINDOW_CAPABILITY, kind=WINDOW_KIND,
                             syscall=None, syscall_name=None,
                             evidence=reason),
                    stdout=b"", stderr=b"", seconds=run["seconds"] or 0.0,
                    cmd=run["cmd"], sim_log=run["sim_log"],
                    m5out=run["m5out"], timed_out=True,
                    exit_cause=run["exit_cause"])


# ---------------------------------------------------------------------------
# driver invocation (the driver keeps corpus, flags, cwd, argv, guest root)
# ---------------------------------------------------------------------------
def case_dirname(suite, driver, cid):
    """The driver's own per-case directory name (its outdir layout)."""
    if suite == "llvm-ts":
        slug = getattr(driver, "_slug", None)
        if slug is None:
            raise AttributeError(
                "llvm-ts driver has no _slug(): refusing to guess its per-case "
                "directory name (the sampling seam maps results by it)")
        return slug(cid)
    return cid


def driver_argv(suite, driver_path, mode, jobs, work_dir, json_out,
                report_out, window_seconds, ids):
    cmd = [driver_path, "--link-mode", mode, "--engine", "gem5-se",
           "--jobs", str(jobs), "--work-dir", work_dir,
           "--json-out", json_out, "--report-out", report_out,
           "--gem5-timeout", str(window_seconds)]
    if suite == "libc-test":
        alternation = "|".join(re.escape(cid) for cid in ids)
        cmd += ["--filter", "^(?:" + alternation + ")$"]
    elif suite == "llvm-ts":
        for cid in ids:
            cmd += ["--only", "^" + re.escape(cid) + "$"]
    else:                                        # pragma: no cover - SUITES fixed
        raise ValueError(f"no case selection flag for suite {suite!r}")
    return cmd


def run_driver(suite, driver, argv):
    """Call the driver's own ``main()`` with *argv*; return its exit code."""
    saved = sys.argv
    sys.argv = argv
    try:
        return driver.main()
    finally:
        sys.argv = saved


def driver_json_cases(path):
    try:
        with open(path, "r") as fh:
            record = json.load(fh)
    except (OSError, ValueError):
        return None
    return {case["case"]: case for case in record.get("cases", [])
            if case.get("case")}


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def summarize(results, selection):
    counts = dict(requested=0, sampled=0, completed=0, interrupted_sigint=0,
                  killed_after_sigint=0, launch_failed=0, elf_gate=0,
                  not_sampled=0, missing_stats=0, unaccounted=0)
    for suite, ids in selection.items():
        counts["requested"] += len(ids)
    for key, row in results.items():
        outcome = row.get("outcome") or "unaccounted"
        counts[outcome] = counts.get(outcome, 0) + 1
        if outcome not in ("not_sampled", "elf_gate", "unaccounted",
                           "launch_failed"):
            counts["sampled"] += 1
        if row.get("simInsts") == "MISSING":
            counts["missing_stats"] += 1
    return counts


def build_report(args, selection, results, driver_rc, driver_jsons,
                 listed_total):
    return dict(
        task=TASK,
        generated_utc=iso_utc(),
        link_mode=args.link_mode,
        sample_seconds=args.sample_seconds,
        grace_seconds=args.grace_seconds,
        jobs=args.jobs,
        case_list=dict(source=os.path.basename(args.case_list),
                       field="timeout_recheck.<suite>.still_blocked",
                       total=listed_total,
                       selected=sum(len(ids) for ids in selection.values()),
                       by_suite={s: len(ids) for s, ids in selection.items()}),
        selection=selection,
        runs=driver_rc,
        driver_json=[os.path.basename(path) for path in driver_jsons],
        counts=summarize(results, selection),
        cases=dict(sorted(results.items())),
        note=("sampling only: every run was stopped at the sample window (or "
              "ended on its own); no verdict is recorded, no source, case or "
              "expectation was changed"),
    )


# ---------------------------------------------------------------------------
# self-test (no corpus and no simulator run)
# ---------------------------------------------------------------------------
class _RecordingReap:
    """Stand-in for the engine's child-spawn: records, never runs anything."""

    def __init__(self):
        self.cmds = []

    def run_tracked(self, cmd, timeout=None, **kwargs):
        self.cmds.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, b"", b"")


def self_test(work_dir, repo_root):
    os.makedirs(work_dir, exist_ok=True)
    checks = []

    def check(name, want, got):
        checks.append((name, want, got))

    engine = load_module("_m13_engine_for_selftest",
                         os.path.join(repo_root, ENGINE_MODULE))

    # 1. the builder must produce the command the engine itself would run.
    fake = os.path.join(work_dir, "cmd")
    os.makedirs(fake, exist_ok=True)
    misc = dict(gem5=os.path.join(fake, "gem5.opt"),
                config=os.path.join(fake, "se.py"),
                argv=["-a", "x y"], stdin_path=os.path.join(fake, "in"),
                cwd=os.path.join(fake, "cwd"),
                interp_dir=os.path.join(fake, "root"),
                redirect=[("/lib", os.path.join(fake, "root", "lib"))])
    reap = _RecordingReap()
    engine.proc_reap = reap
    engine.run_gem5_se(os.path.join(fake, "a.elf"), os.path.join(fake, "out"),
                       timeout=7, **misc)
    engine_cmd = reap.cmds[0]
    mine = build_cmd(misc["gem5"], os.path.join(fake, "out", "m5out"),
                     misc["config"], os.path.join(fake, "a.elf"),
                     os.path.join(fake, "out", "guest.stdout"),
                     os.path.join(fake, "out", "guest.stderr"),
                     misc["stdin_path"], argv=misc["argv"], cwd=misc["cwd"],
                     interp_dir=misc["interp_dir"],
                     redirect=misc["redirect"])
    check("cmd identical to engine", engine_cmd, mine)
    mutated = list(mine)
    mutated[mutated.index("--guest-stdout") + 1] = "/g/out/other"
    check("cmd comparison can fail", True, mutated != engine_cmd)

    # 2. statistics parsing: present / zero / absent row / absent file.
    m5out = os.path.join(work_dir, "stats-ok", "m5out")
    os.makedirs(m5out, exist_ok=True)
    with open(os.path.join(m5out, "stats.txt"), "w") as fh:
        fh.write("simSeconds  1.5  # simulated\n"
                 "simInsts    12345678  # Number of instructions simulated\n")
    check("simInsts parsed", 12345678, read_sim_insts(m5out)[0])
    zero = os.path.join(work_dir, "stats-zero", "m5out")
    os.makedirs(zero, exist_ok=True)
    with open(os.path.join(zero, "stats.txt"), "w") as fh:
        fh.write("simInsts 0 # nothing retired\n")
    check("simInsts 0 is data, not MISSING", 0, read_sim_insts(zero)[0])
    norow = os.path.join(work_dir, "stats-norow", "m5out")
    os.makedirs(norow, exist_ok=True)
    with open(os.path.join(norow, "stats.txt"), "w") as fh:
        fh.write("simSeconds 1.0 # simulated\n")
    check("stats without simInsts", "MISSING", read_sim_insts(norow)[0])
    check("missing stats.txt", "MISSING",
          read_sim_insts(os.path.join(work_dir, "no-such", "m5out"))[0])

    # 3. exit cause parsing (the interrupted/completed discriminator).
    log = os.path.join(work_dir, "sim.log")
    with open(log, "w") as fh:
        fh.write("gem5 Simulator System\nGEM5_EXIT_CAUSE=user interrupt received\n")
    check("exit cause parsed", "user interrupt received", read_exit_cause(log))
    with open(log, "w") as fh:
        fh.write("gem5 Simulator System\n")
    check("exit cause absent", None, read_exit_cause(log))

    # 4. outcome classification of the wait/interrupt protocol.
    class _Proc:
        def __init__(self, finishes, ignores_sigint=False):
            self.finishes = finishes
            self.ignores = ignores_sigint
            self.killed = False
            self.signalled = None
            self.waits = 0
            # A pid that cannot exist: getpgid() raises, so the fake exercises
            # the send_signal fallback and never touches a real process.
            self.pid = 2 ** 31 - 1

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1 and not self.finishes:
                raise subprocess.TimeoutExpired(cmd="gem5", timeout=timeout)
            if self.ignores and not self.killed:
                raise subprocess.TimeoutExpired(cmd="gem5", timeout=timeout)
            return 0

        def kill(self):
            self.killed = True

        def send_signal(self, signo):
            self.signalled = signo

    check("completed before the window", (0, False, False),
          wait_and_interrupt(_Proc(finishes=True), 5, 5))
    check("interrupted by SIGINT", (0, True, False),
          wait_and_interrupt(_Proc(finishes=False), 5, 5))
    check("killed after SIGINT", (0, True, True),
          wait_and_interrupt(_Proc(finishes=False, ignores_sigint=True), 5, 5))

    # 5. case-list reading, pilot narrowing and the shard suite set.
    case_list = os.path.join(work_dir, "case-list.json")
    with open(case_list, "w") as fh:
        json.dump(dict(link_mode="static", timeout_recheck=dict(
            **{"libc-test": dict(still_blocked=["functional/a"]),
               "llvm-ts": dict(still_blocked=["MultiSource/X/b"]),
               "embench": dict(still_blocked=["crc32-0"])})), fh)
    ratio = load_module("_m13_ratio_for_selftest",
                        os.path.join(repo_root, "tools", "testcases", "tset",
                                     "gem5-se-baseline", "run_engine_ratio.py"))
    selection = ratio.load_selection(case_list, ["libc-test", "llvm-ts"],
                                     "recheck")
    check("selection read", {"libc-test": ["functional/a"],
                             "llvm-ts": ["MultiSource/X/b"]}, selection)
    narrowed, subset = ratio.narrow_selection(selection, ["MultiSource/X/b"])
    check("pilot narrowing", ({"llvm-ts": ["MultiSource/X/b"]}, True),
          (narrowed, subset))
    try:
        ratio.narrow_selection(selection, ["nope"])
        check("pilot rejects unknown", "ValueError", "no exception")
    except ValueError:
        check("pilot rejects unknown", "ValueError", "ValueError")
    check("link mode read", "static", ratio.record_link_mode(case_list))
    check("link mode conflict", True,
          bool(ratio.link_mode_conflict("static", "dynamic")))

    # 6. the per-case directory mapping (results are joined by it).
    driver_shape = type("D", (), {
        "_slug": staticmethod(lambda cid: re.sub(r"[^A-Za-z0-9._-]+", "_", cid))})
    check("libc dirname is the id", "functional/a",
          case_dirname("libc-test", driver_shape, "functional/a"))
    check("llvm dirname is the slug", "MultiSource_X_b",
          case_dirname("llvm-ts", driver_shape, "MultiSource/X/b"))

    # 7. the report records the listed total and the (possibly narrowed)
    #    selection separately.
    report = build_report(
        argparse.Namespace(case_list=case_list, link_mode="static",
                           sample_seconds=120, grace_seconds=120, jobs=48),
        narrowed, {}, {"llvm-ts": 1}, [], 2)
    check("report listed vs selected",
          (2, 1), (report["case_list"]["total"],
                   report["case_list"]["selected"]))
    check("report counts requested", 1, report["counts"]["requested"])

    # 8. a driver run that never reached the engine is recorded, not dropped.
    os.makedirs(os.path.join(work_dir, "drv"), exist_ok=True)
    sampler = Sampler(engine, "static", os.path.join(work_dir, "run"),
                      grace_seconds=5, case_by_dir={"functional/a": "functional/a"})
    gate_ret = sampler.evaluate("/g/absent.elf",
                                os.path.join(work_dir, "run", "static",
                                             "functional/a", "gem5-se"),
                                gem5="/g/gem5.opt", config="/g/se.py",
                                timeout=5, musl_root="/g/musl")
    check("elf gate stops before gem5", "BLOCKED", gate_ret["status"])
    check("elf gate recorded", "elf_gate",
          sampler.results["functional/a"]["outcome"])

    failed = 0
    for name, want, got in checks:
        ok = want == got
        failed += 0 if ok else 1
        print(f"self-test {'PASS' if ok else 'FAIL'} {name}: "
              f"expected={want!r} actual={got!r}")
    print(f"self-test: {len(checks) - failed}/{len(checks)} checks passed")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=f"{TASK}: gem5 SE instruction-count sampling (simInsts) "
                    f"of the long-tail cases -- SIGINT at the sample window, "
                    f"then read m5out/stats.txt")
    ap.add_argument("--case-list", default=None,
                    help="case list in the run_engine_ratio format "
                         "(timeout_recheck.<suite>.still_blocked); required "
                         "unless --self-test")
    ap.add_argument("--link-mode", choices=("static", "dynamic"), default="static")
    ap.add_argument("--sample-seconds", type=int, default=120,
                    help="sample window per case: SIGINT after this many "
                         "seconds, then read m5out/stats.txt (default 120)")
    ap.add_argument("--grace-seconds", type=int, default=120,
                    help="how long the simulator may take to dump statistics "
                         "after SIGINT before it is killed (default 120)")
    ap.add_argument("--jobs", type=int, default=48,
                    help="cases in flight (handed to the suite driver; "
                         "default 48)")
    ap.add_argument("--work-dir", required=True,
                    help="runtime directory for the per-case build/run trees")
    ap.add_argument("--json-out", default=None,
                    help="per-case sampling JSON (runtime; required unless "
                         "--self-test)")
    ap.add_argument("--suites", default=None,
                    help="comma-separated suites to sample (default: the "
                         "suites the case list carries)")
    ap.add_argument("--only", action="append", default=None, metavar="CASE",
                    help="sample only this case id (repeatable; the id must be "
                         "part of the case list)")
    ap.add_argument("--repo-root", default=REPO_ROOT,
                    help="repository whose built toolchain/gem5/musl the "
                         "drivers must use (default: this script's repo).  A "
                         "worktree without built artifacts points this at the "
                         "checkout that has them")
    ap.add_argument("--gem5-bin", default=None,
                    help="gem5.opt override (default: the driver's own default)")
    ap.add_argument("--gem5-config", default=None,
                    help="SE config override (default: the driver's own default)")
    ap.add_argument("--self-test", action="store_true",
                    help="check the launch builder, statistics parsing, the "
                         "outcome protocol and the case mapping without "
                         "building or running anything")
    args = ap.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    work_dir = abspath(args.work_dir, repo_root)
    os.makedirs(work_dir, exist_ok=True)

    if args.self_test:
        return self_test(work_dir, repo_root)
    if not args.case_list or not args.json_out:
        sys.stderr.write("ERROR: --case-list and --json-out are required\n")
        return 2
    if args.jobs < 1 or args.sample_seconds < 1 or args.grace_seconds < 1:
        sys.stderr.write("ERROR: --jobs/--sample-seconds/--grace-seconds must "
                         "be >= 1\n")
        return 2

    case_list = abspath(args.case_list, repo_root)
    try:
        ratio = load_module("_m13_ratio_loader",
                            os.path.join(repo_root, "tools", "testcases",
                                         "tset", "gem5-se-baseline",
                                         "run_engine_ratio.py"))
        with open(case_list, "r") as fh:
            record = json.load(fh)
        available = sorted((record.get("timeout_recheck") or {}))
        if not available:
            raise ValueError(f"{os.path.basename(case_list)}: no "
                             f"timeout_recheck record")
        suites = ([s.strip() for s in args.suites.split(",") if s.strip()]
                  if args.suites else available)
        unknown = [s for s in suites if s not in available]
        if unknown:
            raise ValueError(f"suite(s) {unknown} not in the case list "
                             f"(carries {available})")
        no_driver = [s for s in suites if s not in SUITES]
        if no_driver:
            raise ValueError(f"no driver for suite(s) {no_driver} "
                             f"(this tool drives {list(SUITES)})")
        conflict = ratio.link_mode_conflict(ratio.record_link_mode(case_list),
                                            args.link_mode)
        if conflict:
            raise ValueError(f"{os.path.basename(case_list)}: {conflict}")
        selection = ratio.load_selection(case_list, suites, "recheck")
        listed_total = sum(len(ids) for ids in selection.values())
        selection, _subset = ratio.narrow_selection(selection, args.only)
    except (OSError, ValueError, KeyError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    total = sum(len(ids) for ids in selection.values())
    print(f"[plan] sample {total} case(s) "
          + ", ".join(f"{s}={len(ids)}" for s, ids in selection.items())
          + f"; link-mode={args.link_mode}; jobs={args.jobs}; "
            f"window={args.sample_seconds}s; grace={args.grace_seconds}s",
          flush=True)

    engine = None
    grace = args.grace_seconds
    driver_rc = {}
    driver_jsons = []
    all_results = {}
    overall = 0
    for suite in suites:
        ids = selection.get(suite) or []
        if not ids:
            continue
        driver_path = os.path.join(repo_root, DRIVERS[suite])
        driver = load_module(f"_m13_driver_{suite.replace('-', '_')}",
                             driver_path)
        # The sampler must replace the very module object the driver calls, not
        # a second copy of it: this is the driver's own engine boundary.
        engine = driver.gem5_se_engine
        case_by_dir = {}
        for cid in ids:
            dirname = case_dirname(suite, driver, cid)
            if dirname in case_by_dir and case_by_dir[dirname] != cid:
                sys.stderr.write(
                    f"ERROR: {suite}: cases {case_by_dir[dirname]!r} and "
                    f"{cid!r} share the per-case directory {dirname!r}; the "
                    f"sampling seam cannot tell them apart\n")
                return 2
            case_by_dir[dirname] = cid

        suite_work = os.path.join(work_dir, suite)
        os.makedirs(suite_work, exist_ok=True)
        json_out = os.path.join(suite_work, f"{suite}-gem5-se-sampled.json")
        report_out = os.path.join(suite_work, f"{suite}-gem5-se-sampled.log")
        sampler = Sampler(engine, args.link_mode, suite_work, grace, case_by_dir,
                          reaper=getattr(driver, "proc_reap", None))
        engine.evaluate = sampler.evaluate
        argv = driver_argv(suite, driver_path, args.link_mode, args.jobs,
                           suite_work, json_out, report_out,
                           args.sample_seconds, ids)
        if args.gem5_bin:
            argv += ["--gem5", args.gem5_bin]
        if args.gem5_config:
            argv += ["--gem5-config", args.gem5_config]
        print(f"[run] {suite}: driver={os.path.basename(driver_path)} "
              f"cases={len(ids)}", flush=True)
        rc = run_driver(suite, driver, argv)
        driver_rc[suite] = rc
        print(f"[run] {suite}: driver rc={rc}", flush=True)
        if rc >= 2:
            sys.stderr.write(
                f"ERROR: {suite} driver exited {rc} (setup error); its log is "
                f"{os.path.basename(report_out)}\n")
            return 3
        driver_json = json_out if os.path.isfile(json_out) else None
        if driver_json:
            driver_jsons.append(driver_json)
        reported = driver_json_cases(driver_json) if driver_json else None
        stray = sorted(k for k in sampler.results if k not in set(ids))
        if stray:
            sys.stderr.write(
                "ERROR: the driver ran case(s) that do not map back to the "
                f"case list ({stray}); the per-case record would be wrong\n")
            return 2
        for cid in ids:
            key = cid
            if key in sampler.results:
                row = dict(sampler.results[key])
                row.update(suite=suite, case=cid)
                all_results[f"{suite}:{cid}"] = row
                continue
            case = (reported or {}).get(cid) or {}
            all_results[f"{suite}:{cid}"] = dict(
                suite=suite, case=cid, outcome="not_sampled",
                simInsts="MISSING", exit_cause=None, seconds=None,
                rc=None, note=case.get("reason") or
                "the driver produced no record for this case")

    unaccounted = [key for key, row in all_results.items()
                   if row.get("outcome") in (None, "unaccounted")]
    report = build_report(args, selection, all_results, driver_rc, driver_jsons,
                          listed_total)
    report["counts"]["unaccounted"] = len(unaccounted)
    json_out = abspath(args.json_out, repo_root)
    os.makedirs(os.path.dirname(json_out) or ".", exist_ok=True)
    with open(json_out, "w") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    counts = report["counts"]
    for key, row in report["cases"].items():
        print(f"[sample] {key} simInsts={row.get('simInsts')} "
              f"outcome={row.get('outcome')} "
              f"exit_cause={row.get('exit_cause')} "
              f"seconds={row.get('seconds')}"
              + (f" note={row.get('note')}" if row.get("note") else ""),
              flush=True)
    print("[counts] " + ", ".join(f"{k}={v}" for k, v in counts.items()),
          flush=True)
    print(f"[out] {os.path.basename(json_out)} "
          f"({os.path.getsize(json_out)} B)", flush=True)
    if counts["requested"] != counts["sampled"] + counts["not_sampled"] + \
            counts["elf_gate"] + counts["launch_failed"]:
        print("[counts] WARNING: requested != sampled + not_sampled + "
              "elf_gate + launch_failed", flush=True)
    if unaccounted:
        print(f"[counts] FAIL: {len(unaccounted)} case(s) without any record",
              flush=True)
        overall = 1
    return overall


if __name__ == "__main__":
    sys.exit(main())
