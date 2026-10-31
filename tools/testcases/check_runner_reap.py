#!/usr/bin/env python3
"""Self-check: a runner killed from outside must not leave qemu orphans.

TESTCASES-085t.  Four modes (see the task file for the rationale):

  helper            synthetic driver: own-session child, same-group child, a
                    timeout path and a decoy; SIGTERM/SIGINT/SIGHUP rounds.
  converted-runners the real libc-test / embench ``run()`` helpers, driven
                    through ``proc_reap.run_tracked``.
  runner-fake       the real llvm-ts runner + a fake ``qemu-dadao`` that only
                    sleeps; SIGTERM the runner and watch the fake qemu die.
  runner-real       the real runner + the real qemu (single XSBench case);
                    requires ``qemu-dadao`` to be idle beforehand.

Exit codes: 0 = PASS, 1 = FAIL, 2 = usage error.  Every check prints
``[PASS]/[FAIL] <name>: <evidence>`` with pids and a
``ps -o pid,ppid,pgid,sid,stat,cmd`` line.  All waits are bounded by
``--timeout-cap`` (seconds) and every process this script starts is killed in
``finally``.  Scratch space is ``/tmp/opencode/TESTCASES-085t/`` (``--keep``
keeps the directory, as does any failure).
"""

import argparse
import os
import signal
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TMP_ROOT = "/tmp/opencode/TESTCASES-085t"
LLVM_RUNNER = os.path.join(REPO_ROOT, "tools", "testcases", "tset", "llvm-ts",
                           "run_llvm_ts_user.py")
QEMU_NAME = "qemu-dadao"

DRIVER_SIGNALS = r'''import os
import subprocess
import sys

REPO = {repo!r}
sys.path.insert(0, os.path.join(REPO, "tools", "testcases"))
import proc_reap  # noqa: E402

run_dir = sys.argv[1]
marker = sys.argv[2]


def path(name):
    return os.path.join(run_dir, name)


def write_pid(name, pid):
    tmp = path(name + ".tmp")
    with open(tmp, "w") as fh:
        fh.write("%d\n" % pid)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path(name))


proc_reap.install()

try:
    proc_reap.run_tracked(
        ["/bin/sh", "-c",
         "echo $$ > %s; exec sleep 30" % path("timeout.pid")], timeout=1)
except subprocess.TimeoutExpired:
    pass
else:
    print("NO_TIMEOUT", flush=True)
    sys.exit(5)

own = proc_reap.popen_tracked(
    [sys.executable, "-c", "import time; time.sleep(120)", marker],
    start_new_session=True)
write_pid("own.pid", own.pid)
same = proc_reap.popen_tracked(
    [sys.executable, "-c", "import time; time.sleep(120)", marker])
write_pid("same.pid", same.pid)
write_pid("ready", 0)
own.wait()
'''

DRIVER_CONVERTED = r'''import importlib.util
import os
import sys
import threading
import time

REPO = {repo!r}
sys.path.insert(0, os.path.join(REPO, "tools", "testcases"))
import proc_reap  # noqa: E402

run_dir = sys.argv[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


libc = load("tc085_libc_runner",
            "tools/testcases/tset/libc-test/run_libc_test_user_suite.py")
emb = load("tc085_embench_runner",
           "tools/testcases/tset/embench/run_embench_user_suite.py")

proc_reap.install()


def call(mod, tag):
    cmd = ["/bin/sh", "-c",
           "echo $$ > %s; exec sleep 120" % os.path.join(run_dir, tag + ".pid")]
    try:
        mod.run(cmd, timeout=300)
    except BaseException as exc:      # the outer checker reports the verdict
        print("%s: %r" % (tag, exc), flush=True)


threads = [threading.Thread(target=call, args=(libc, "libc")),
           threading.Thread(target=call, args=(emb, "embench"))]
for th in threads:
    th.daemon = True
    th.start()

deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    if all(os.path.exists(os.path.join(run_dir, tag + ".pid"))
           for tag in ("libc", "embench")):
        break
    time.sleep(0.05)
with open(os.path.join(run_dir, "ready"), "w") as fh:
    fh.write("ok\n")
while True:
    time.sleep(60)
'''


# ---------------------------------------------------------------------------
# /proc helpers (no psutil; pgrep is only used for extra evidence, never for
# the assertion -- the assertion scans /proc itself)
# ---------------------------------------------------------------------------
def proc_fields(pid):
    try:
        with open("/proc/%d/stat" % pid, "r") as fh:
            data = fh.read()
    except OSError:
        return None
    close = data.rfind(")")
    if close < 0:
        return None
    return data[close + 2:].split()


def proc_alive(pid):
    if not pid:
        return False
    fields = proc_fields(pid)
    if fields:
        return fields[0] != "Z"       # a zombie is already dead for our purpose
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def proc_ppid(pid):
    fields = proc_fields(pid)
    return int(fields[1]) if fields and len(fields) > 1 else None


def qemu_named_pids(name=QEMU_NAME):
    pids = []
    try:
        names = os.listdir("/proc")
    except OSError:
        return pids
    for entry in names:
        if not entry.isdigit():
            continue
        try:
            with open("/proc/%s/comm" % entry, "r") as fh:
                comm = fh.read().strip()
        except OSError:
            continue
        if comm == name:
            pids.append(int(entry))
    return pids


def pids_with_marker(marker):
    needle = marker.encode()
    pids = []
    try:
        names = os.listdir("/proc")
    except OSError:
        return pids
    for entry in names:
        if not entry.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % entry, "rb") as fh:
                cmdline = fh.read()
        except OSError:
            continue
        if needle in cmdline:
            pids.append(int(entry))
    return pids


def pgrep_lines(*args):
    """``pgrep`` output for evidence only; None when pgrep is unavailable."""
    try:
        res = subprocess.run(["pgrep"] + list(args), stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return [line for line in res.stdout.decode().split() if line]


def describe_pids(pids):
    """pid(comm=..., ppid=..., cmd=...) per pid -- evidence for a FAIL."""
    rows = []
    for pid in pids:
        fields = proc_fields(pid)
        ppid = int(fields[1]) if fields and len(fields) > 1 else "?"
        try:
            with open("/proc/%d/comm" % pid, "r") as fh:
                comm = fh.read().strip()
        except OSError:
            comm = "?"
        try:
            with open("/proc/%d/cmdline" % pid, "rb") as fh:
                cmd = fh.read().replace(b"\0", b" ").decode(
                    "utf-8", "replace").strip()
        except OSError:
            cmd = "?"
        rows.append("%d(comm=%s ppid=%s cmd=%s)" % (pid, comm, ppid, cmd[:160]))
    return " ".join(rows) or "(none)"


def ps_snapshot(pids):
    live = [str(p) for p in pids if isinstance(p, int) and p > 0]
    if not live:
        return "(no pid)"
    res = subprocess.run(["ps", "-o", "pid,ppid,pgid,sid,stat,cmd", "-p",
                          ",".join(live)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    rows = res.stdout.decode("utf-8", "replace").strip().splitlines()
    return " || ".join(row.strip() for row in rows[1:]) or "(gone)"


def wait_value(predicate, timeout, interval=0.05):
    """Return the first truthy value of ``predicate`` (or its last value)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


def wait_until(predicate, timeout, interval=0.05):
    return bool(wait_value(predicate, timeout, interval))


def wait_proc(proc, timeout):
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def read_pid(run_dir, name):
    try:
        with open(os.path.join(run_dir, name), "r") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def file_tail(path, limit=4000):
    try:
        with open(path, "r", errors="replace") as fh:
            data = fh.read()
    except OSError:
        return "(no log)"
    return data[-limit:].replace("\n", " | ")


def kill_pid(pid):
    for signo in (signal.SIGKILL,):
        try:
            os.kill(pid, signo)
        except OSError:
            pass


class Checker:
    def __init__(self):
        self.failures = 0
        self.procs = []
        self.pids = []
        self.groups = []

    def track(self, proc):
        self.procs.append(proc)
        return proc

    def track_pid(self, pid):
        if pid:
            self.pids.append(pid)
        return pid

    def track_group(self, pid):
        if pid:
            self.groups.append(pid)
        return pid

    def check(self, name, ok, evidence):
        print("[%s] %s: %s" % ("PASS" if ok else "FAIL", name, evidence),
              flush=True)
        if not ok:
            self.failures += 1
        return ok

    def cleanup(self):
        for pgid in reversed(self.groups):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except OSError:
                pass
        for pid in reversed(self.pids):
            kill_pid(pid)
        for proc in reversed(self.procs):
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    kill_pid(proc.pid)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass


def spawn_decoy(chk, tag):
    marker = "TC085t-decoy-%s-%d" % (tag, os.getpid())
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(300)", marker],
        start_new_session=True)
    chk.track(proc)
    time.sleep(0.1)
    chk.check("decoy alive (%s)" % tag, proc_alive(proc.pid),
              "pid=%d %s" % (proc.pid, ps_snapshot([proc.pid])))
    return proc, marker


# ---------------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------------
def mode_helper(chk, run_dir, cap):
    driver = os.path.join(run_dir, "driver_signals.py")
    with open(driver, "w") as fh:
        fh.write(DRIVER_SIGNALS.format(repo=REPO_ROOT))
    marker = "TC085t-child-%d-%d" % (os.getpid(), int(time.time()))
    decoy, _decoy_marker = spawn_decoy(chk, "helper")
    rounds = (("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT),
              ("SIGHUP", signal.SIGHUP))
    for signame, signo in rounds:
        rdir = os.path.join(run_dir, "round-" + signame)
        os.makedirs(rdir, exist_ok=True)
        log = os.path.join(rdir, "driver.log")
        with open(log, "wb") as lf:
            drv = subprocess.Popen([sys.executable, driver, rdir, marker],
                                   stdout=lf, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        chk.track(drv)
        ready = wait_until(
            lambda: os.path.exists(os.path.join(rdir, "ready")), cap)
        if not chk.check(signame + " driver ready", ready,
                         "pid=%d log=%s" % (drv.pid, file_tail(log))):
            for nm in ("own.pid", "same.pid"):
                pid = read_pid(rdir, nm)
                if pid:
                    chk.track_pid(pid)
                    chk.track_group(pid)
            try:
                os.killpg(drv.pid, signal.SIGKILL)
            except OSError:
                kill_pid(drv.pid)
            continue
        tpid = read_pid(rdir, "timeout.pid")
        chk.check(
            signame + " timeout child reaped", tpid is not None
            and not proc_alive(tpid),
            "pid=%s ps=%s" % (tpid, ps_snapshot([tpid])))
        apid = read_pid(rdir, "own.pid")
        bpid = read_pid(rdir, "same.pid")
        chk.track_pid(apid)
        chk.track_group(apid)
        chk.track_pid(bpid)
        before = ps_snapshot([drv.pid, apid, bpid])
        chk.check(signame + " children registered",
                  proc_alive(apid) and proc_alive(bpid),
                  "before: " + before)
        os.kill(drv.pid, signo)
        rc = wait_proc(drv, 5)
        chk.check(signame + " driver exited by signal", rc == -signo,
                  "rc=%r expected=%d ps=%s"
                  % (rc, -signo, ps_snapshot([drv.pid])))
        gone = wait_until(
            lambda: not proc_alive(apid) and not proc_alive(bpid), 5)
        chk.check(signame + " children reaped", gone,
                  "after: " + ps_snapshot([apid, bpid]))
        chk.check(signame + " decoy survived", proc_alive(decoy.pid),
                  "pid=%d ps=%s" % (decoy.pid, ps_snapshot([decoy.pid])))
        left = pids_with_marker(marker)
        chk.check(signame + " no marker process left", not left,
                  "proc-scan=%r pgrep=%r %s"
                  % (left, pgrep_lines("-f", marker), describe_pids(left)))
    kill_pid(decoy.pid)


def mode_converted(chk, run_dir, cap):
    driver = os.path.join(run_dir, "driver_converted.py")
    with open(driver, "w") as fh:
        fh.write(DRIVER_CONVERTED.format(repo=REPO_ROOT))
    decoy, _decoy_marker = spawn_decoy(chk, "converted")
    log = os.path.join(run_dir, "driver.log")
    with open(log, "wb") as lf:
        drv = subprocess.Popen([sys.executable, driver, run_dir],
                               stdout=lf, stderr=subprocess.STDOUT,
                               start_new_session=True)
    chk.track(drv)
    ready = wait_until(
        lambda: os.path.exists(os.path.join(run_dir, "ready")), cap)
    if chk.check("converted driver ready", ready,
                 "pid=%d log=%s" % (drv.pid, file_tail(log))):
        apid = read_pid(run_dir, "libc.pid")
        bpid = read_pid(run_dir, "embench.pid")
        chk.track_pid(apid)
        chk.track_pid(bpid)
        chk.check("converted children registered",
                  proc_alive(apid) and proc_alive(bpid),
                  "before: " + ps_snapshot([drv.pid, apid, bpid]))
        os.kill(drv.pid, signal.SIGTERM)
        rc = wait_proc(drv, 5)
        chk.check("converted driver exited by signal", rc == -signal.SIGTERM,
                  "rc=%r expected=%d" % (rc, -signal.SIGTERM))
        gone = wait_until(
            lambda: not proc_alive(apid) and not proc_alive(bpid), 5)
        chk.check("converted children reaped", gone,
                  "after: " + ps_snapshot([apid, bpid]))
        chk.check("converted decoy survived", proc_alive(decoy.pid),
                  "pid=%d" % decoy.pid)
    kill_pid(decoy.pid)


def mode_runner_fake(chk, run_dir, cap):
    fake = os.path.join(run_dir, "qemu-dadao")
    pidfile = os.path.join(run_dir, "fake.pid")
    with open(fake, "w") as fh:
        fh.write("#!/bin/sh\necho $$ > '%s'\nsleep 120\n" % pidfile)
    os.chmod(fake, 0o755)
    decoy, _decoy_marker = spawn_decoy(chk, "fake")
    log = os.path.join(run_dir, "runner.log")
    cmd = [sys.executable, LLVM_RUNNER,
           "--link-mode", "dynamic",
           "--only", "SingleSource/Benchmarks/Stanford/Queens",
           "--qemu", fake,
           "--json-out", os.path.join(run_dir, "fake.json"),
           "--work-dir", os.path.join(run_dir, "work")]
    with open(log, "wb") as lf:
        runner = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=lf,
                                  stderr=subprocess.STDOUT,
                                  start_new_session=True)
    chk.track(runner)
    ready = wait_until(lambda: os.path.exists(pidfile), cap)
    if chk.check("fake qemu started", ready,
                 "runner=%d fake=%s log=%s"
                 % (runner.pid, fake, file_tail(log))):
        qpid = read_pid(run_dir, "fake.pid")
        chk.track_pid(qpid)
        chk.track_group(qpid)
        chk.check("fake qemu ppid is runner",
                  proc_ppid(qpid) == runner.pid,
                  "before: " + ps_snapshot([runner.pid, qpid]))
        os.kill(runner.pid, signal.SIGTERM)
        rc = wait_proc(runner, 10)
        chk.check("fake-run runner exited by signal",
                  rc == -signal.SIGTERM,
                  "rc=%r expected=%d" % (rc, -signal.SIGTERM))
        gone = wait_until(lambda: not proc_alive(qpid), 5)
        chk.check("fake qemu reaped", gone,
                  "after: " + ps_snapshot([qpid]))
        left = pids_with_marker(fake)
        chk.check("no fake qemu left", not left,
                  "proc-scan=%r pgrep=%r %s"
                  % (left, pgrep_lines("-f", fake), describe_pids(left)))
        chk.check("fake-mode decoy survived", proc_alive(decoy.pid),
                  "pid=%d" % decoy.pid)
    kill_pid(decoy.pid)


def mode_runner_real(chk, run_dir, cap):
    pre = qemu_named_pids()
    if not chk.check("precondition: no qemu-dadao running", not pre,
                     "proc-scan=%r pgrep=%r %s"
                     % (pre, pgrep_lines("-x", QEMU_NAME),
                        describe_pids(pre))):
        print("[FAIL] runner-real skipped: another qemu is running; refusing "
              "to touch processes this check did not start", flush=True)
        return
    decoy, _decoy_marker = spawn_decoy(chk, "real")
    log = os.path.join(run_dir, "runner.log")
    cmd = [sys.executable, LLVM_RUNNER,
           "--link-mode", "dynamic",
           "--only", "MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench",
           "--json-out", os.path.join(run_dir, "real.json"),
           "--work-dir", os.path.join(run_dir, "work")]
    with open(log, "wb") as lf:
        runner = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=lf,
                                  stderr=subprocess.STDOUT,
                                  start_new_session=True)
    chk.track(runner)

    def qemu_child():
        for pid in qemu_named_pids():
            if proc_ppid(pid) == runner.pid:
                return pid
        return None

    qpid = wait_value(qemu_child, cap, interval=0.2)
    if chk.check("real qemu child started", bool(qpid),
                 "runner=%d qemu=%s log=%s"
                 % (runner.pid, qpid, file_tail(log))):
        chk.track_pid(qpid)
        chk.track_group(qpid)
        chk.check("real qemu ppid is runner", proc_ppid(qpid) == runner.pid,
                  "before: " + ps_snapshot([runner.pid, qpid]))
        os.kill(runner.pid, signal.SIGTERM)
        rc = wait_proc(runner, 10)
        chk.check("real-run runner exited by signal", rc == -signal.SIGTERM,
                  "rc=%r expected=%d" % (rc, -signal.SIGTERM))
        gone = wait_until(lambda: not proc_alive(qpid), 10)
        chk.check("real qemu reaped", gone,
                  "after: " + ps_snapshot([qpid]))
        left = qemu_named_pids()
        chk.check("no qemu-dadao left", not left,
                  "proc-scan=%r pgrep=%r %s"
                  % (left, pgrep_lines("-x", QEMU_NAME), describe_pids(left)))
        chk.check("real-mode decoy survived", proc_alive(decoy.pid),
                  "pid=%d ps=%s" % (decoy.pid, ps_snapshot([decoy.pid])))
    kill_pid(decoy.pid)


MODES = {
    "helper": mode_helper,
    "converted-runners": mode_converted,
    "runner-fake": mode_runner_fake,
    "runner-real": mode_runner_real,
}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="TESTCASES-085t: runner orphan-reap self-check")
    ap.add_argument("--mode", required=True, choices=sorted(MODES))
    ap.add_argument("--timeout-cap", type=int, default=180,
                    help="upper bound in seconds for every wait (default 180)")
    ap.add_argument("--keep", action="store_true",
                    help="keep /tmp/opencode/TESTCASES-085t/<mode>-*")
    args = ap.parse_args(argv)
    if args.timeout_cap <= 0:
        sys.stderr.write("ERROR: --timeout-cap must be > 0\n")
        return 2
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_dir = os.path.join(TMP_ROOT, "%s-%s-%d"
                           % (args.mode, stamp, os.getpid()))
    os.makedirs(run_dir)
    chk = Checker()
    print("[INFO] mode=%s run_dir=%s python=%s proc=%s"
          % (args.mode, run_dir, sys.version.split()[0],
             os.path.isdir("/proc")), flush=True)
    try:
        MODES[args.mode](chk, run_dir, args.timeout_cap)
    finally:
        chk.cleanup()
    ok = chk.failures == 0
    print("[%s] %s: failures=%d" % ("PASS" if ok else "FAIL", args.mode,
                                    chk.failures), flush=True)
    if ok and not args.keep:
        _rmtree(run_dir)
    else:
        print("[INFO] kept: %s" % run_dir, flush=True)
    return 0 if ok else 1


def _rmtree(path):
    try:
        import shutil
        shutil.rmtree(path)
    except OSError:
        pass


if __name__ == "__main__":
    sys.exit(main())
