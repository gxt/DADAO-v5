#!/usr/bin/env python3
"""L1 gate: shared build-tree / install-root writer guard (``ISS-373``).

Why: parallel tasks share ``.work/`` and the install root (task worktrees symlink
them into the main worktree), so one session's rebuild silently replaced the
binaries another session was reading => false FAIL, and the mirror image (a batch
that read the *old* binary) is a false PASS.  The mechanism and its boundary are
in ``docs/Process-07 §2.1``; the registry/guard itself is
``tools/infra/writer_guard.py``.

This gate proves, on a throw-away tree (never the real registry, never a real
build), that the four required behaviours are real and each has a reachable
FAIL path:
  W1  writer active  => reader entry refuses (rc 75) and does not execute the
                         binary; ``--allow-concurrent`` passes and is logged.
  W2  binary replaced while the batch runs => FAIL ("二进制在跑批期间被替换");
                         unchanged => green (the control that keeps W2 honest).
  W3  stale records (pid gone / pid recycled / garbled) are detected, ignored by
                         readers, removed by ``clean`` (idempotent) and auto-
                         purged by the next writer.
  W4  normal path not disturbed: a writer's record exists while it runs and is
                         cleared after; a reader nested inside its own writer
                         (same make tree: ``install-host -> check-install-tools``)
                         is *not* refused.
  W5  state-dir override is never silent: ``--state-dir`` /
                         ``DADAO_WRITER_STATE_DIR`` prints a WARNING on stderr
                         and logs it; the default path stays quiet.

Plus the wiring that keeps the above from rotting (mechanical, reachable FAIL):

  S1  every declared batch/evidence entry still calls
      ``writer_guard.start_guard`` *and* ``writer_guard.finish_guard``;
  S2  ``Makefile``'s ``WRITER_TARGET_COMPONENTS`` covers every gate-locked
      target that writes the shared trees (``build-*`` / ``install-*``), names
      only known components, and every guarded target is gate-locked;
  S3  ``make`` really expands a guarded target into a ``writer_guard.py run``
      command (and an unguarded one without it);
  S4  ``check-writer-guards`` is wired into ``_locked-check`` (L1).

Usage:  python3 tools/infra/check_writer_guards.py [--keep] [--verbose]
Exit:   0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "tools" / "infra" / "writer_guard.py"
MAKEFILE = REPO / "Makefile"
ENV_STATE = "DADAO_WRITER_STATE_DIR"

# Declared batch / evidence entries (docs/Process-07 §2.1).  Each one must keep
# the start/finish guard calls -- that is S1, so a silent regression goes red.
READER_ENTRIES = [
    "tests/ee-tiny/run_asm_suite.py",
    "tools/testcases/arch/run_m5_e2e.py",
    # run_{rnd,minmax,fma,clmul}_probe.py 已退役（入口文件删除）：前三者
    # m13-testcases-044、clmul m15-testcases-008
    "tools/testcases/unit/run_codegen_e2e.py",
    "tools/testcases/unit/run_elf_e2e.py",
    "tools/testcases/diff_ir_lli.py",
    "tests/ee-user/run_libc_test_user_suite.py",
    "tests/ee-user/run_llvm_ts_user.py",
    "tests/ee-user/run_embench_user_suite.py",
    "tests/ee-tiny/run_embench_e2e.py",
    "tools/testcases/l3_run.py",
    "tools/testcases/night_run.py",
    "tools/gem5/check_tiny_hmon.py",
    "tests/ee-tiny/picolibc_tests.py",
    "tools/qemu/user_mode_smoke.py",
    "tools/qemu/semantics_gate.py",
    "tools/qemu/k0_boot_probe.py",
    "tests/ee-tiny/run_semihosting_smoke.py",
]


class Report:
    def __init__(self, verbose: bool = False):
        self.checks = 0
        self.failures = 0
        self.verbose = verbose

    def check(self, name: str, ok: bool, detail: str) -> bool:
        self.checks += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  ({detail})", flush=True)
        if not ok:
            self.failures += 1
        return ok

    def note(self, text: str) -> None:
        if self.verbose:
            print(f"        {text}", flush=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _makefile_var(text: str, name: str) -> str:
    """Value of a (possibly backslash-continued) make assignment."""
    pattern = re.compile(rf"^{re.escape(name)}\s*[?:]?=\s*(.*)$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    value = match.group(1)
    lines = [value]
    tail = text[match.end():].splitlines()[1:]
    for line in tail:
        if lines[-1].rstrip().endswith("\\"):
            lines[-1] = lines[-1].rstrip()[:-1]
            lines.append(line)
        else:
            break
    return " ".join(part.strip() for part in lines if part.strip())


def _parse_writer_table(text: str) -> dict[str, list[str]]:
    raw = _makefile_var(text, "WRITER_TARGET_COMPONENTS")
    table: dict[str, list[str]] = {}
    for token in raw.split():
        if ":" not in token:
            table[token] = []
            continue
        target, comps = token.split(":", 1)
        table[target] = [c for c in comps.split(",") if c]
    return table


def _gate_locked_targets(text: str) -> list[str]:
    raw = _makefile_var(text, "GATE_LOCKED_TARGETS")
    return raw.split()


def _known_components() -> set[str]:
    sys.path.insert(0, str(REPO / "tools" / "infra"))
    import writer_guard  # noqa: E402

    return set(writer_guard.COMPONENTS)


def _run(cmd: list[str], env: dict, timeout: float = 120.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True,
                          text=True, timeout=timeout)


def _spawn_writer(env: dict, component: str, seconds: float,
                  extra: list[str] | None = None) -> subprocess.Popen:
    """Start a live writer (``writer_guard.py run`` sleeping) and wait for its record."""
    args = [sys.executable, str(GUARD), "run", "--component", component,
            "--target", "gate-holder", "--"] + (extra or []) + [
        sys.executable, "-c", f"import time; time.sleep({seconds})"]
    proc = subprocess.Popen(args, cwd=str(REPO), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    state = Path(env[ENV_STATE])
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if any(p.name.startswith(component) for p in state.glob("*.json")):
            return proc
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("writer record never appeared")


def _stub_binary(path: Path, marker: Path) -> None:
    path.write_text("#!/bin/sh\n: > %r\nexit 2\n" % str(marker), encoding="utf-8")
    path.chmod(0o755)


# ---------------------------------------------------------------------------
# static wiring (S1-S4)
# ---------------------------------------------------------------------------

def static_checks(rep: Report) -> None:
    print("S1 reader entries still call the guard", flush=True)
    missing = []
    for rel in READER_ENTRIES:
        text = _read(REPO / rel)
        if "writer_guard.start_guard(" not in text \
                or "writer_guard.finish_guard(" not in text:
            missing.append(rel)
    rep.check("S1 guarded-reader-wiring", not missing,
              f"entries={len(READER_ENTRIES)} (live count), missing={missing or 0}")

    print("S2 Makefile writer table covers the shared-tree writers", flush=True)
    text = _read(MAKEFILE)
    table = _parse_writer_table(text)
    gate_locked = _gate_locked_targets(text)
    known = _known_components()
    derived = sorted(t for t in gate_locked
                     if t.startswith("build-") or t.startswith("install-"))
    uncovered = [t for t in derived if t not in table]
    not_locked = [t for t in table if t not in gate_locked]
    bad_comp = sorted({c for comps in table.values() for c in comps if c not in known})
    no_comp = sorted(t for t, comps in table.items() if not comps)
    rep.check("S2a every gate-locked build-/install- target registers",
              not uncovered,
              f"derived={len(derived)} live count, uncovered={uncovered or 0}")
    rep.check("S2b every registered target is gate-locked", not not_locked,
              f"registered={len(table)}, not-gate-locked={not_locked or 0}")
    rep.check("S2c every registered component exists in writer_guard.COMPONENTS",
              not bad_comp and not no_comp,
              f"known={sorted(known)}, unknown={bad_comp or 0}, "
              f"targets-without-component={no_comp or 0}")

    print("S3 make expands guarded targets through writer_guard", flush=True)
    cases = {"build-gem5": ["gem5"], "install-host": ["llvm", "qemu"]}
    probe = Path(tempfile.mkdtemp(prefix="writer-guard-make-"))
    try:
        mk = probe / "probe.mk"
        for target, comps in cases.items():
            mk.write_text(
                "include %s\n"
                "probe-writer:\n"
                "\t@echo '$(call writer-wrapped,%s)'\n"
                "probe-plain:\n"
                "\t@echo '$(call writer-wrapped,%s)'\n" % (MAKEFILE, target,
                                                           "check-inst-asm"),
                encoding="utf-8")
            out = _run(["make", "-f", str(mk), "--no-print-directory",
                        "probe-writer"], dict(os.environ))
            line = out.stdout.strip()
            expected = " ".join(f"--component {c}" for c in comps)
            rep.check(f"S3a make-wraps-{target}",
                      out.returncode == 0 and "writer_guard.py run" in line
                      and expected in line and f"--target {target}" in line,
                      f"rc={out.returncode}, has-components={expected in line}")
            rep.note(line)
        out = _run(["make", "-f", str(mk), "--no-print-directory", "probe-plain"],
                   dict(os.environ))
        line = out.stdout.strip()
        rep.check("S3b unguarded-target-not-wrapped",
                  out.returncode == 0 and "writer_guard.py run" not in line
                  and "_locked-check-inst-asm" in line,
                  f"rc={out.returncode}, wrapped={'writer_guard.py run' in line}")
    finally:
        shutil.rmtree(probe, ignore_errors=True)

    print("S4 gate is wired into L1", flush=True)
    match = re.search(r"^_locked-check:(.*)$", text, re.MULTILINE)
    prereqs = match.group(1).split() if match else []
    rep.check("S4 check-writer-guards-in-L1",
              "check-writer-guards" in prereqs,
              f"in _locked-check prerequisites="
              f"{'check-writer-guards' in prereqs}, prereqs={len(prereqs)}")


# ---------------------------------------------------------------------------
# functional classes (W1-W4)
# ---------------------------------------------------------------------------

def check_w1(rep: Report, tmp: Path, env: dict) -> None:
    print("W1 writer active => reader refuses", flush=True)
    state = Path(env[ENV_STATE])
    stub = tmp / "qemu-system-dadao"
    marker = tmp / "stub-ran"
    _stub_binary(stub, marker)
    bootrom = tmp / "bootrom.bin"
    bootrom.write_bytes(b"\x00\x01")

    def entry(*extra: str) -> subprocess.CompletedProcess:
        # `.S` 批量入口（`m13-testcases-043`：YAML 代表集入口 `run_qemu_smoke.py` 已退役）。
        # 只跑 1 个载体（3 个故障镜像）⇒ stub qemu 下秒级。
        return _run([sys.executable, "tests/ee-tiny/run_asm_suite.py",
                     "--qemu", str(stub), "--bootrom", str(bootrom),
                     "--platforms", "qemu", "--vectors", "tests/inst/00-isa-design",
                     "--id", "undi_reserved",
                     "--work-dir", str(tmp / "asm"),
                     "--log-dir", str(tmp / "asm-log")] + list(extra), env)

    # injection: a live writer for qemu => the real entry must refuse, and must
    # not have started a single binary.
    holder = _spawn_writer(env, "llvm", 6.0)
    try:
        marker.unlink(missing_ok=True)
        p = entry()
        refused = (p.returncode == 75 and "REFUSED" in p.stderr
                   and not marker.exists())
        rep.check("W1a real-entry-refused", refused,
                  f"rc={p.returncode} (want 75), "
                  f"refuse-msg={'REFUSED' in p.stderr}, "
                  f"binary-executed={marker.exists()}")

        marker.unlink(missing_ok=True)
        p2 = entry("--allow-concurrent")
        overrides = state / "overrides.log"
        allowed = (p2.returncode != 75 and "REFUSED" not in p2.stderr
                   and marker.exists() and overrides.is_file()
                   and "run_asm_suite.py" in overrides.read_text())
        rep.check("W1b allow-concurrent-passes-and-logs", allowed,
                  f"rc={p2.returncode} (want != 75), "
                  f"binary-executed={marker.exists()}, "
                  f"override-logged={overrides.is_file()}")
    finally:
        holder.wait(timeout=30)

    # restore: no writer => the entry is not refused any more.
    marker.unlink(missing_ok=True)
    p3 = entry()
    rep.check("W1c green-after-writer-gone",
              p3.returncode != 75 and "REFUSED" not in p3.stderr and marker.exists(),
              f"rc={p3.returncode} (!= 75), binary-executed={marker.exists()}")


def check_w2(rep: Report, tmp: Path, env: dict) -> None:
    print("W2 binary replaced mid-batch => FAIL", flush=True)
    fake = tmp / "gem5.opt"
    fake.write_bytes(b"v1")
    green = _run([sys.executable, "tools/infra/writer_guard.py", "read-run",
                  "--binary", str(fake), "--", sys.executable, "-c",
                  "print('batch-ran')"], env)
    rep.check("W2a control-unchanged-is-green",
              green.returncode == 0 and "batch-ran" in green.stdout,
              f"rc={green.returncode}, ran={'batch-ran' in green.stdout}")
    red = _run([sys.executable, "tools/infra/writer_guard.py", "read-run",
                "--binary", str(fake), "--", sys.executable, "-c",
                "open(%r,'wb').write(b'v2')" % str(fake)], env)
    rep.check("W2b replaced-mid-run-fails",
              red.returncode == 1 and "二进制在跑批期间被替换" in red.stderr,
              f"rc={red.returncode} (want 1), "
              f"fail-msg={'二进制在跑批期间被替换' in red.stderr}")
    removed = _run([sys.executable, "tools/infra/writer_guard.py", "read-run",
                    "--binary", str(tmp / "never-existed"), "--",
                    sys.executable, "-c", "print('ok')"], env)
    rep.check("W2c missing-binary-at-both-ends-is-green", removed.returncode == 0,
              f"rc={removed.returncode}")


def check_w3(rep: Report, tmp: Path, env: dict) -> None:
    print("W3 stale records are detected, ignored and cleaned", flush=True)
    state = Path(env[ENV_STATE])
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    expires = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))
    stale = {"schema": "dadao-writer/1", "component": "gem5", "target": "crashed",
             "pid": dead.pid, "pid_start": 1, "host": os.uname().nodename,
             "started": now, "duration": 3600, "expires": expires,
             "git_head": "deadbeef", "cwd": str(tmp), "cmd": []}
    (state / "gem5.json").write_text(json.dumps(stale))
    reused = dict(stale, component="qemu", target="pid-reused", pid=os.getpid(),
                  pid_start=1)
    (state / "qemu.json").write_text(json.dumps(reused))

    p = _run([sys.executable, "tools/infra/writer_guard.py", "status"], env)
    detected = (p.stdout.count("stale") >= 2)
    rep.check("W3a stale-detected", detected,
              f"rc={p.returncode}, stale-lines={p.stdout.count('stale')}")
    # a stale record must never block a reader
    q = _run([sys.executable, "tools/infra/writer_guard.py", "check",
              "--component", "gem5", "--component", "qemu"], env)
    rep.check("W3b stale-does-not-block-readers", q.returncode == 0,
              f"rc={q.returncode} (want 0)")
    # a garbled record has no component: it must fail closed for every reader
    (state / "llvm.json").write_text("{garbled")
    g = _run([sys.executable, "tools/infra/writer_guard.py", "check",
              "--component", "llvm"], env)
    rep.check("W3c garbled-record-fails-closed", g.returncode == 75,
              f"rc={g.returncode} (want 75)")
    c1 = _run([sys.executable, "tools/infra/writer_guard.py", "clean"], env)
    c2 = _run([sys.executable, "tools/infra/writer_guard.py", "clean"], env)
    rep.check("W3d clean-removes-then-idempotent",
              "removed 3 record" in c1.stdout and "removed 0 record" in c2.stdout,
              f"first={c1.stdout.strip()!r}, second={c2.stdout.strip()!r}")
    g2 = _run([sys.executable, "tools/infra/writer_guard.py", "check",
               "--component", "llvm"], env)
    rep.check("W3e green-after-clean", g2.returncode == 0,
              f"rc={g2.returncode} (want 0)")

    # a stale record is also purged by the next writer start
    (state / "gem5.json").write_text(json.dumps(stale))
    r = _run([sys.executable, "tools/infra/writer_guard.py", "run",
              "--component", "gem5", "--target", "next", "--",
              sys.executable, "-c", "pass"], env)
    rep.check("W3f next-writer-purges-stale",
              r.returncode == 0 and "cleaned 1 stale" in r.stderr
              and not (state / "gem5.json").exists(),
              f"rc={r.returncode}, purged={'cleaned 1 stale' in r.stderr}")


def check_w5(rep: Report, tmp: Path, env: dict) -> None:
    """W5: overriding the registry path must never be silent (main ruling ⑤)."""
    print("W5 state-dir override is never silent", flush=True)
    state = Path(env[ENV_STATE])
    over = state / "state-dir-override.log"
    over.unlink(missing_ok=True)
    p = _run([sys.executable, "tools/infra/writer_guard.py", "status"], env)
    rep.check("W5a override-warning-on-stderr-and-log",
              p.returncode == 0
              and "WARNING: writer-state-dir overridden" in p.stderr
              and over.is_file()
              and "env DADAO_WRITER_STATE_DIR" in over.read_text(),
              f"rc={p.returncode}, "
              f"stderr-warning={'WARNING: writer-state-dir overridden' in p.stderr}, "
              f"logged={over.is_file()}")
    # a real batch entry warns too (it uses the same resolver)
    entry_env = dict(env)
    entry_env["DADAO_WRITER_STATE_DIR"] = str(state)
    stub = tmp / "qemu-sdd"
    _stub_binary(stub, tmp / "sdd-marker")
    bootrom = tmp / "bootrom2.bin"
    bootrom.write_bytes(b"\x00")
    q = _run([sys.executable, "tests/ee-tiny/run_asm_suite.py",
              "--qemu", str(stub), "--bootrom", str(bootrom),
              "--platforms", "qemu", "--vectors", "tests/inst/00-isa-design",
              "--id", "undi_reserved",
              "--work-dir", str(tmp / "asm2"),
              "--log-dir", str(tmp / "asm2-log")], entry_env)
    rep.check("W5b real-entry-warns",
              "WARNING: writer-state-dir overridden" in q.stderr,
              f"rc={q.returncode}, "
              f"warning={'WARNING: writer-state-dir overridden' in q.stderr}")
    # control: the default registry path must not emit the warning
    plain_env = {k: v for k, v in os.environ.items() if k != ENV_STATE}
    r = _run([sys.executable, "tools/infra/writer_guard.py", "status"], plain_env)
    rep.check("W5c default-path-no-warning",
              r.returncode == 0
              and "writer-state-dir overridden" not in r.stderr,
              f"rc={r.returncode}, "
              f"warning={'writer-state-dir overridden' in r.stderr}")


def check_w4(rep: Report, tmp: Path, env: dict) -> None:
    print("W4 normal path is not disturbed", flush=True)
    state = Path(env[ENV_STATE])
    fake = tmp / "gem5.opt"
    fake.write_bytes(b"v9")
    during = _run([sys.executable, "tools/infra/writer_guard.py", "run",
                   "--component", "gem5", "--target", "lifecycle", "--",
                   sys.executable, "-c",
                   "import os,sys; sys.exit(0 if os.path.isfile(%r) else 3)"
                   % str(state / "gem5.json")], env)
    rep.check("W4a record-present-while-writer-runs", during.returncode == 0,
              f"rc={during.returncode} (want 0)")
    rep.check("W4b record-cleared-after-writer", not (state / "gem5.json").exists(),
              f"leftover={(state / 'gem5.json').exists()}")

    # a reader nested inside its own writer (same make tree) is not refused:
    # install-host writes the install root and then checks it in the same run.
    nested_code = (
        "import sys; sys.path.insert(0, %r); import writer_guard\n"
        "g = writer_guard.ReadGuard([%r])\n"
        "g.start()\n"
        "print('GUARD-OK')\n"
        "sys.exit(0 if g.finish() else 1)\n"
    ) % (str(REPO / "tools" / "infra"), str(fake))
    nested = _run([sys.executable, "tools/infra/writer_guard.py", "run",
                   "--component", "gem5", "--target", "outer", "--",
                   sys.executable, "-c", nested_code], env)
    rep.check("W4c nested-reader-not-refused",
              nested.returncode == 0 and "GUARD-OK" in nested.stdout,
              f"rc={nested.returncode}, guard-ok={'GUARD-OK' in nested.stdout}")

    # and a plain batch with no writer at all stays green
    plain = _run([sys.executable, "tools/infra/writer_guard.py", "read-run",
                  "--binary", str(fake), "--", sys.executable, "-c",
                  "print('plain-ok')"], env)
    rep.check("W4d plain-batch-green",
              plain.returncode == 0 and "plain-ok" in plain.stdout,
              f"rc={plain.returncode}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true", help="keep the temp tree")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    rep = Report(verbose=args.verbose)
    tmp = Path(tempfile.mkdtemp(prefix="writer-guard-gate-"))
    env = dict(os.environ)
    env[ENV_STATE] = str(tmp / "writers")
    Path(env[ENV_STATE]).mkdir(parents=True, exist_ok=True)
    try:
        static_checks(rep)
        check_w1(rep, tmp, env)
        check_w2(rep, tmp, env)
        check_w3(rep, tmp, env)
        check_w4(rep, tmp, env)
        check_w5(rep, tmp, env)
    finally:
        if args.keep:
            print(f"temp tree kept: {tmp}", flush=True)
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f"check-writer-guards: {rep.checks - rep.failures}/{rep.checks} PASS",
          flush=True)
    return 0 if rep.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
