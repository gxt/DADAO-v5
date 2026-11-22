#!/usr/bin/env python3
"""run_embench_tiny.py -- Embench-IoT end-to-end gate (INTEG-025t, M6).

Compiles every Embench-IoT benchmark from ``<embench-src>/src/*/`` with the
DADAO cross toolchain at each requested optimisation level, links it against
the frozen M6 runtime (crt0 + freestanding mem/str runtime + Embench board
shim) and runs it under **QEMU** (default) or the **chipyard Tiny Verilator
harness** (``--engine chipyard``, m12-chipyard-016), judging the **guest
process exit code**.  The build pipeline is identical for both engines; only
the "run an already-built ELF" step differs (``tools/testcases/lib/
chipyard_engine.py``).

Value channel (Embench convention, see ``support/main.c``): ``main`` returns
``!correct`` -- i.e. the guest exit code is ``0`` iff the benchmark's own
result verification passed.  So the per-case judgement is: guest exit == 0
(PASS) else FAIL.  (There is no "correct" string; Embench reports via the exit
code -- confirmed in ``.work/log/integ/embench-analysis.md``.)  The chipyard
engine additionally requires the board shim's three console markers
(``[board:init]`` / ``[board:start]`` / ``[board:stop]``) in the ``+semiout``
sink, so "exited 0 without ever running the benchmark" cannot pass.


Pipeline per (benchmark, optimisation level):

    clang -target dadao-unknown-elf -<O> -ffreestanding -fno-builtin \
          -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=1 \
          -c support/{main,beebsc}.c <src>/<b>/*.c <boardsupport>.c  -> *.o
    clang ... -c tests/tset/embench/embench_runtime.c                    -> *.o
    llc  -march=dadao -O0 -filetype=obj mem_runtime_user.ll            -> *.o
    llvm-mc --triple=dadao -filetype=obj crt0_user.s                   -> crt0.o
    ld.lld -T tests/ee-tiny/tests_freestanding_tiny.lds *.o                        -> <b>.elf
    timeout N qemu-system-dadao \
            -machine kaiwu-tiny,bootrom-image=<fixed 64 KiB firmware> \
            -kernel <b>.elf -semihosting-config enable=on,target=native -> guest exit
     # or (--engine chipyard):
     timeout N simulator-chipyard.harness-WumingTinyConfig +permissive \
             +loadmem=<b>.elf +semiout=<out> +max-cycles=<N> +permissive-off none

Judgement (fail-closed):
  * every (benchmark, level) must build and exit 0  -> PASS
  * build-step non-zero / non-zero or faulted exit -> FAIL
  * the ``--timeout`` budget running out with no guest verdict -> ``TIMEOUT``,
    shown as ``timeout(<budget>)`` (e.g. ``timeout(12h)``): the case gave **no
    verdict**, so it is neither a pass nor a chipyard-only failure
  * a platform/environment gap (unimplemented semihosting service, loader or
    simulator stop before the guest's own verdict) -> ``BLOCKED``
  * chipyard: +max-cycles exhausted, or the sim binary's md5 changing during
    the run -> FAIL; board markers missing -> FAIL
  * source tree missing / zero benchmarks / missing tool -> setup error (2)

Status vocabulary (user ruling 2026-11-15: "blocked 容易让人误解"):

  PASS / FAIL / TIMEOUT / BLOCKED / GUARD / ERROR.  ``blocked`` means a
  **build/environment gap** only (ISS-193 long-double, a missing CFX6 carrier,
  an unimplemented harness service); a **budget** outcome is ``timeout(<预算>)``
  and its machine value in ``--json-out`` is ``TIMEOUT``.  The budget label is
  derived live from ``--timeout`` (``43200 -> 12h``, ``3600 -> 1h``,
  ``5400 -> 90m``), never hardcoded.

Structural closure (AGENTS.md「验证脚本反例门控」): the benchmark corpus IS ``<embench-src>/src/``
(a manifest-locked component, so it cannot silently change).  The driver
enumerates that directory live and requires *every* discovered benchmark to be
compiled, linked and executed -- the executed set must equal the discovered set,
so a driver bug cannot silently skip a benchmark.  Counts are reported live
(never hardcoded; AGENTS.md「验证脚本反例门控」).

Exit status:
  0  every case PASS
  1  at least one case FAIL (a TIMEOUT is not a pass either)
  2  setup error (missing tool / source / zero benchmarks)

``--inject`` is a built-in counter-example self-test: after a green baseline it
re-judges one PASSing case against a wrong expected value (1) and requires the
judgement to FAIL -- proving the comparison is live.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys

# 本文件在 `tests/ee-tiny/run_embench_tiny.py`（m15-testcases-011 从 `tools/testcases/tset/embench/`
# 迁入；TESTCASES-076t 曾从集成驱动目录迁入）⇒ 仓库根在 2 层之上。
REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

# Install root (ADR-0016 D7/D9): resolve tools from the single source of truth
# (tools/infra/paths.py) instead of hardcoding .dadao/.
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
import paths as _dadao_paths  # noqa: E402
import writer_guard  # noqa: E402
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases", "lib"))
import chipyard_engine  # noqa: E402
import machine_profile  # noqa: E402

_TARGET_BIN = str(_dadao_paths.host_toolchain_bin())

DEFAULT_CLANG = os.path.join(_TARGET_BIN, "clang")
DEFAULT_LLC = os.path.join(_TARGET_BIN, "llc")
DEFAULT_LLVM_MC = os.path.join(_TARGET_BIN, "llvm-mc")
DEFAULT_LDLD = os.path.join(_TARGET_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(_TARGET_BIN, "qemu-system-dadao")
DEFAULT_EMBENCH_SRC = ".work/source/embench-iot"
DEFAULT_INCLUDE = "tests/tset/embench/embench_include"
DEFAULT_RUNTIME = "tests/tset/embench/embench_runtime.c"
# 资产归属（m15-testcases-011/012）：`mem_runtime_user.ll`/`crt0_user.s` 在
# `tests/ee-user/`；Tiny 的 lds 在 `tests/ee-tiny/`。
DEFAULT_MEM_RUNTIME = "tests/ee-user/mem_runtime_user.ll"
DEFAULT_CRT0 = "tests/ee-tiny/crt0_tiny_freestanding.S"
DEFAULT_LDS = "tests/ee-tiny/tests_freestanding_tiny.lds"
DEFAULT_BOOTROM = str(_dadao_paths.test_artifacts_dir()
                      / "bootrom" / "tiny" / "bootrom_tiny.bin")
DEFAULT_BOARDSUPPORT = "examples/dadao/boardsupport.c"
# Work dir under the SDK test-artifacts root (ADR-0016 D6 / Process-05 §6),
# resolved through paths.py (D7); never hardcoded.
DEFAULT_WORK_DIR = str(_dadao_paths.test_artifacts_dir() / "m6-embench")
DEFAULT_OPTS = "O0,O2"
DEFAULT_TIMEOUT = 60
DEFAULT_ENGINE = "qemu"
# Chipyard Tiny (m12-chipyard-016): the Verilator harness runs the same ELF via
# `+loadmem=`; the runner only swaps the run step.
MARKERS = ("[board:init]", "[board:start]", "[board:stop]")

# Machine fault exit codes (spec/Kaiwu §7.1): monitor 0xC0-0xFF
# (bit5:4 = run mode, bit3:0 = cause index) and other cfx 0x80-0xBF
# (bit5:0 = cfxHA).
_MONITOR_FAULT_NAMES = {
    0: "CFXTRAP", 1: "CFXMEM", 2: "CFXREG", 3: "CFXESC", 7: "CFXPERM",
    8: "ILLI", 9: "UNDI", 10: "RASOF", 11: "RASUF", 12: "MALIGN",
    13: "IALIGN",
}
FAULT_NAMES = {0xC0 | (mode << 4) | idx: name
               for mode in range(4)
               for idx, name in _MONITOR_FAULT_NAMES.items()}
FAULT_NAMES.update({code: "CFX%d" % (code & 0x3F)
                    for code in range(0x80, 0xC0)})


def _abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def _run(cmd, timeout=None):
    """Run cmd; return (rc, stdout, stderr, timed_out).

    rc is None on timeout.  The command's own exit code is captured directly
    (no shell pipe, so nothing can swallow it).
    """
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
            False,
        )
    except subprocess.TimeoutExpired:
        return None, "", "", True


def _require_exec(path: str, what: str) -> None:
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        sys.stderr.write(f"ERROR: {what} not found / not executable: {path}\n")
        sys.stderr.write("       run 'make install-host' first\n")
        sys.exit(2)


def discover_benchmarks(src_root: str):
    """Every immediate subdir of src_root that contains >= 1 ``*.c`` file.

    Sorted; the corpus is the source tree itself (manifest-locked component).
    """
    found = []
    for entry in sorted(os.listdir(src_root)):
        d = os.path.join(src_root, entry)
        if os.path.isdir(d) and glob.glob(os.path.join(d, "*.c")):
            found.append(entry)
    return found


def format_budget(seconds):
    """Display form of a ``--timeout`` budget, derived live (never hardcoded).

    Rules: a whole number of hours -> ``<n>h`` (43200 -> ``12h``, 3600 ->
    ``1h``); else a whole number of minutes -> ``<n>m`` (5400 -> ``90m``);
    else ``<n>s``.  ``parse_budget`` is the exact inverse -- the report
    generator round-trips the label through it, so a wrong conversion is
    caught instead of printed.
    """
    s = int(seconds)
    if s % 3600 == 0:
        return "%dh" % (s // 3600)
    if s % 60 == 0:
        return "%dm" % (s // 60)
    return "%ds" % s


def parse_budget(label):
    """``12h``/``90m``/``45s`` -> seconds (inverse of :func:`format_budget`)."""
    unit = label[-1:]
    scale = {"h": 3600, "m": 60, "s": 1}.get(unit)
    if scale is None or not label[:-1].isdigit():
        raise ValueError("bad budget label %r" % (label,))
    return int(label[:-1]) * scale


class CaseResult:
    __slots__ = ("bench", "opt", "expected", "actual", "passed", "reason",
                 "profile", "case_id", "engine", "cycles", "seconds",
                 "sim_md5", "markers", "semi_out", "sim_log",
                 "budget_seconds", "timeout", "gap")

    def __init__(self, bench, opt, expected, profile="tiny", budget_seconds=None):
        self.bench = bench
        self.opt = opt
        self.expected = expected
        self.actual = None
        self.passed = False
        self.reason = ""
        self.profile = profile
        self.case_id = "embench/%s-%s" % (bench, opt)
        self.engine = "qemu"
        self.cycles = None
        self.seconds = None
        self.sim_md5 = None
        self.markers = []
        self.semi_out = None
        self.sim_log = None
        # The batch's --timeout, carried per case so the JSON states the budget
        # each case ran under (the JSONL sink may be the only survivor).
        self.budget_seconds = budget_seconds
        self.timeout = False   # host budget exhausted, no guest verdict
        self.gap = False       # build/environment gap (BLOCKED)


def verdict(rc, expected):
    """(passed, reason) for a guest exit code against an expected value.

    Single source of truth for the per-case judgement, so the ``--inject``
    counter-example self-test exercises exactly the same comparison.
    """
    if rc == expected:
        return True, "match"
    if rc in FAULT_NAMES:
        return False, f"machine fault {FAULT_NAMES[rc]} (0x{rc:02X})"
    return False, "non-zero guest exit"


def build_and_run(bench, opt, tools, work_dir, timeout, verbose=False):
    """Build one (benchmark, opt) through the fixed pipeline; run under QEMU."""
    res = CaseResult(bench, opt, 0, budget_seconds=timeout)
    res.profile = tools.get("profile", "tiny")
    outdir = os.path.join(work_dir, opt, bench)
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)

    cf = [
        "-target", "dadao-unknown-elf", "-" + opt, "-ffreestanding",
        "-fno-builtin", "-std=gnu99", "-DWARMUP_HEAT=1", "-DGLOBAL_SCALE_FACTOR=1",
    ]
    src_root = tools["embench_src"]
    inc_dirs = [
        tools["include"],
        os.path.join(src_root, "support"),
        os.path.join(src_root, "examples", "dadao"),
        os.path.join(src_root, "src", bench),
    ]
    incs = [f for d in inc_dirs for f in ("-I", d)]

    # 1. compile every translation unit of the benchmark + support.
    sources = [
        os.path.join(src_root, "support", "main.c"),
        os.path.join(src_root, "support", "beebsc.c"),
        os.path.join(src_root, "examples", "dadao", "boardsupport.c"),
    ] + sorted(glob.glob(os.path.join(src_root, "src", bench, "*.c")))
    for src in sources:
        obj = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + ".o")
        rc, _o, err, timed = _run([tools["clang"]] + cf + incs + ["-c", src, "-o", obj])
        if timed or rc != 0:
            res.reason = f"clang failed on {os.path.basename(src)} (rc={rc}): {err.strip()[:200]}"
            return res

    # 2. freestanding runtime (C).
    rc, _o, err, timed = _run(
        [tools["clang"], "-target", "dadao-unknown-elf", "-" + opt,
         "-ffreestanding", "-fno-builtin", "-std=gnu99",
         "-I", tools["include"], "-c", tools["runtime"],
         "-o", os.path.join(outdir, "embench_runtime.o")]
    )
    if timed or rc != 0:
        res.reason = f"clang failed on embench_runtime.c (rc={rc}): {err.strip()[:200]}"
        return res

    # 3. memory runtime (.ll -> .o via llc).
    rc, _o, err, timed = _run(
        [tools["llc"], "-march=dadao", "-O0", "-filetype=obj",
         tools["mem_runtime"], "-o", os.path.join(outdir, "mem_runtime.o")]
    )
    if timed or rc != 0:
        res.reason = f"llc failed (rc={rc}): {err.strip()[:200]}"
        return res

    # 4. crt0 stub (assembly -> .o).
    rc, _o, err, timed = _run(
        [tools["llvm_mc"], "--triple=dadao", "-filetype=obj", tools["crt0"],
         "-o", os.path.join(outdir, "crt0.o")]
    )
    if timed or rc != 0:
        res.reason = f"llvm-mc failed on crt0 (rc={rc}): {err.strip()[:200]}"
        return res

    # 5. link (ld.lld).
    elf = os.path.join(outdir, bench + ".elf")
    objs = sorted(glob.glob(os.path.join(outdir, "*.o")))
    rc, _o, err, timed = _run([tools["ldlld"], "-L", os.path.dirname(tools["lds"]),
                              "-T", tools["lds"]] + objs + ["-o", elf])
    if timed or rc != 0:
        res.reason = f"ld.lld failed (rc={rc}): {err.strip()[:200]}"
        return res

    # 6. run on the selected engine; guest exit code == the case's verdict.
    res.engine = tools["engine"]
    if res.engine == "chipyard":
        return _run_chipyard(res, elf, outdir, tools, timeout, verbose)

    rc, _o, err, timed = _run(
        [tools["qemu"], "-machine",
         "kaiwu-tiny,bootrom-image=" + tools["bootrom"], "-kernel", elf,
         "-semihosting-config", "enable=on,target=native",
         "-display", "none", "-nographic"],
        timeout=timeout,
    )
    if timed:
        res.timeout = True
        res.reason = (f"host timeout after {timeout}s (no guest verdict; qemu)")
        return res
    if rc is None:
        res.reason = "qemu did not return an exit code"
        return res
    if rc < 0:
        res.reason = f"qemu killed by signal {-rc}"
        return res
    res.actual = rc
    res.passed, res.reason = verdict(rc, res.expected)
    if verbose:
        sys.stdout.write(f"    [steps] clang/llc/mc/ld.lld=0 qemu={rc}\n")
    return res


def _run_chipyard(res, elf, outdir, tools, timeout, verbose=False):
    """Run one built ELF on the chipyard Tiny harness and judge it.

    Fail-closed (m12-chipyard-016): a ``+max-cycles`` trip or a simulator binary
    whose md5 changed during the run is a FAIL; a case that exits 0 without the
    board shim's markers is a FAIL; anything the platform stopped before the
    guest's own verdict is not a pass.
    """
    obs = chipyard_engine.evaluate(
        elf, outdir, sim=tools["chipyard"], timeout=timeout,
        sim_md5=tools["sim_md5"], max_cycles=tools["max_cycles"],
        env_extra=tools["chipyard_env"],
    )
    res.seconds = obs["seconds"]
    res.cycles = obs["cycles"]
    res.sim_md5 = obs["md5"]
    res.semi_out = os.path.join(outdir, "semi.out")
    res.sim_log = obs["log"]
    text = obs["semiout"].decode("utf-8", "replace")
    res.markers = [m for m in MARKERS if m in text]
    if obs["status"] == "FAIL":
        res.reason = "guard: " + obs["reason"]
        return res
    if obs["status"] == "BLOCKED":
        if "timeout" in obs["reason"]:
            # The --timeout budget ran out with no guest verdict: the case gave
            # *no judgement* (user 2026-11-15).  Shown `timeout(<budget>)`,
            # machine value TIMEOUT, never counted as a chipyard-only failure.
            res.timeout = True
            res.reason = obs["reason"]
        else:
            # A build/environment gap (unimplemented semihosting service, a
            # loader/simulator stop): `blocked`, not a budget outcome.
            res.gap = True
            res.reason = obs["reason"]
        return res
    missing = [m for m in MARKERS if m not in res.markers]
    if missing:
        res.actual = obs["exit"]
        res.reason = ("guest exit %s but board markers missing (%s)"
                      % (obs["exit"], ", ".join(missing)))
        return res
    res.actual = obs["exit"]
    res.passed, res.reason = verdict(res.actual, res.expected)
    if verbose:
        sys.stdout.write(f"    [steps] clang/llc/mc/ld.lld=0 chipyard={res.actual} "
                         f"cycles={res.cycles} markers={len(res.markers)}\n")
    return res


def case_status(res):
    """Machine status -- single source of truth for JSON *and* the log line.

    ``TIMEOUT`` = the ``--timeout`` budget ran out and the guest gave no
    verdict (user ruling 2026-11-15); ``BLOCKED`` = a build/environment gap
    only (ISS-193 long-double, a missing carrier, an unimplemented harness
    service).  A budget outcome is never ``BLOCKED``.
    """
    if res.passed:
        return "PASS"
    if res.timeout:
        return "TIMEOUT"
    if res.gap:
        return "BLOCKED"
    if res.reason.startswith("guard:"):
        return "GUARD"
    if res.actual is None:
        return "ERROR"
    return "FAIL"


def display_status(res):
    """Human form of :func:`case_status`: ``TIMEOUT`` -> ``timeout(12h)``.

    The budget comes from the case's own ``--timeout`` (现场派生), so the label
    states the window the case actually ran under.
    """
    status = case_status(res)
    if status == "TIMEOUT":
        return "timeout(%s)" % format_budget(res.budget_seconds)
    return status


def status_counts(results):
    """``{display status: count}`` for the batch trailer (live, no hardcoding).

    Keyed by the *display* form so a budget outcome shows up as
    ``timeout(12h)`` rather than being lumped into "failed".
    """
    counts = {}
    for res in results:
        label = display_status(res)
        counts[label] = counts.get(label, 0) + 1
    return counts


def case_row(res):
    """One JSON-report row for a finished case (single source of truth).

    ``--json-out`` writes the whole list at the end; ``--jsonl-out`` appends
    exactly these rows as cases finish, so a reader can union the two forms.
    ``budget_seconds`` is the batch's ``--timeout`` and ``timeout`` flags a
    case that exhausted it (no guest verdict) -- both live, never hardcoded.
    """
    status = case_status(res)
    return {
        "case_id": res.case_id,
        "profile": res.profile,
        "scope": "embench",
        "engine": res.engine,
        "status": status,
        "exit": res.actual,
        "cycles": res.cycles,
        "seconds": res.seconds,
        "budget_seconds": res.budget_seconds,
        "timeout": status == "TIMEOUT",
        "sim_md5": res.sim_md5,
        "markers": res.markers,
        "semi_out": res.semi_out,
        "sim_log": res.sim_log,
        "arch_visible": {"guest_exit": res.actual,
                         "expected_exit": res.expected,
                         "reason": res.reason},
        "note": res.reason,
    }


def write_json(path, results, engine="qemu"):
    rows = [case_row(res) for res in results]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"scope": "embench", "engine": engine,
                   "profile": results[0].profile if results else None,
                   "cases": rows},
                  fh, indent=1, sort_keys=True)
        fh.write("\n")


def iso_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


class JsonlSink:
    """Append-on-completion JSONL (``--jsonl-out``), flushed per case.

    A long batch must be observable while it runs (``docs/Process-08 §1.9``);
    the final ``--json-out`` stays the authoritative record.  A write failure
    raises ``OSError`` -- it is never swallowed into a silent partial file.
    """

    def __init__(self, path):
        self.fh = open(path, "w", encoding="utf-8")

    def write(self, res):
        row = case_row(res)
        row["ts"] = iso_utc()
        line = json.dumps(row, sort_keys=True) + "\n"
        self.fh.write(line)
        self.fh.flush()
        os.fsync(self.fh.fileno())

    def close(self):
        self.fh.close()


def _report(res, opt):
    actual = "?" if res.actual is None else str(res.actual)
    status = display_status(res)
    extra = ""
    if res.engine == "chipyard":
        extra = f" cycles={res.cycles} {res.seconds}s"
    sys.stdout.write(
        f"  {status}  {res.bench} (-{opt})  expected={res.expected} "
        f"actual={actual} exit={actual}{extra}  ({res.reason})\n"
    )
    sys.stdout.flush()


def run_suite(benchmarks, opts, tools, work_dir, timeout, verbose=False,
              jobs=1, on_case=None):
    """Run every (bench, opt) case; ``jobs`` > 1 fans out to a thread pool.

    The chipyard engine needs it: one Verilator run takes minutes, and the cases
    are independent (each has its own build + run directory).  ``on_case`` is
    called once per completed case, under the report lock, before the next
    case's output (used by ``--jsonl-out`` for incremental visibility).
    """
    tasks = [(opt, bench) for opt in opts for bench in benchmarks]
    results = []
    if jobs <= 1:
        for opt, bench in tasks:
            res = build_and_run(bench, opt, tools, work_dir, timeout, verbose)
            _report(res, opt)
            if on_case:
                on_case(res)
            results.append(res)
        return results

    import concurrent.futures
    import threading

    lock = threading.Lock()

    def one(task):
        opt, bench = task
        res = build_and_run(bench, opt, tools, work_dir, timeout, verbose)
        with lock:
            _report(res, opt)
            if on_case:
                on_case(res)
        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for fut in concurrent.futures.as_completed(
                [pool.submit(one, t) for t in tasks]):
            results.append(fut.result())
    order = {t: i for i, t in enumerate(tasks)}
    results.sort(key=lambda r: order[(r.opt, r.bench)])
    return results


def main():
    ap = argparse.ArgumentParser(description="Embench E2E gate (INTEG-025t)")
    ap.add_argument("--clang", default=os.environ.get("CLANG", DEFAULT_CLANG))
    ap.add_argument("--llc", default=os.environ.get("LLC", DEFAULT_LLC))
    ap.add_argument("--llvm-mc", dest="llvm_mc",
                    default=os.environ.get("LLVM_MC", DEFAULT_LLVM_MC))
    ap.add_argument("--ldlld", default=os.environ.get("LDLLD", DEFAULT_LDLD))
    ap.add_argument("--qemu", default=os.environ.get("QEMU_SYSTEM_DADAO", DEFAULT_QEMU))
    ap.add_argument("--embench-src", default=DEFAULT_EMBENCH_SRC)
    ap.add_argument("--include", default=DEFAULT_INCLUDE)
    ap.add_argument("--runtime", default=DEFAULT_RUNTIME)
    ap.add_argument("--mem-runtime", dest="mem_runtime", default=DEFAULT_MEM_RUNTIME)
    ap.add_argument("--crt0", default=DEFAULT_CRT0)
    ap.add_argument("--lds", default=DEFAULT_LDS)
    ap.add_argument("--bootrom", default=DEFAULT_BOOTROM)
    ap.add_argument("--profile",
                    default=os.environ.get("DADAO_TEST_PROFILE") or "tiny",
                    choices=sorted(machine_profile.all_profiles()),
                    help="machine profile (default tiny)")
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--opt", default=DEFAULT_OPTS,
                    help="comma-separated optimisation levels, e.g. 'O0,O2'")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--engine", default=os.environ.get("DADAO_TEST_ENGINE")
                    or DEFAULT_ENGINE, choices=("qemu", "chipyard"),
                    help="run engine: qemu (kaiwu-tiny) or chipyard (Verilator "
                         "Tiny harness; m12-chipyard-016)")
    ap.add_argument("--chipyard", default=None,
                    help="simulator-chipyard harness binary (engine chipyard)")
    ap.add_argument("--max-cycles", dest="max_cycles", type=int,
                    default=int(os.environ.get("DADAO_CHIPYARD_MAX_CYCLES")
                                or 2000000000),
                    help="+max-cycles budget; tripping it is a FAIL")
    ap.add_argument("--only", default=None,
                    help="comma-separated benchmark names to run (sharding)")
    ap.add_argument("--jobs", type=int, default=1,
                    help="concurrent (bench, opt) cases (default 1; the "
                         "chipyard engine wants ~cores/2)")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--json-out", default=None,
                    help="optional: write one JSON record per (bench, opt) "
                         "(GEM5-017t)")
    ap.add_argument("--jsonl-out", dest="jsonl_out", default=None,
                    help="optional: append one JSON line per completed case, "
                         "flushed immediately (fields = --json-out cases[] + "
                         "ts; m16-testcases-001)")
    ap.add_argument("--inject", action="store_true",
                    help="counter-example self-test: re-judge one PASSing case "
                         "against a wrong expected value and require FAIL")
    writer_guard.add_arguments(ap)
    args = ap.parse_args()
    prof = machine_profile.load(args.profile)
    if not machine_profile.suite_enabled(prof, "tset/embench"):
        sys.stderr.write("ERROR: profile %r does not run embench "
                         "(contracts/tests-matrix.yaml)\n" % prof.name)
        return 2
    if args.lds == DEFAULT_LDS:
        args.lds = ("tests/ee-tiny/tests_freestanding_tiny.lds"
                    if prof.name == "tiny"
                    else "tests/shared/linker/dadao-%s.lds" % prof.name)

    tools = {
        "clang": _abspath(args.clang),
        "llc": _abspath(args.llc),
        "llvm_mc": _abspath(args.llvm_mc),
        "ldlld": _abspath(args.ldlld),
        "qemu": _abspath(args.qemu),
        "embench_src": _abspath(args.embench_src),
        "include": _abspath(args.include),
        "runtime": _abspath(args.runtime),
        "mem_runtime": _abspath(args.mem_runtime),
        "crt0": _abspath(args.crt0),
        "lds": _abspath(args.lds),
        "bootrom": _abspath(args.bootrom),
        "profile": prof.name,
        "engine": args.engine,
        "chipyard": (os.path.abspath(args.chipyard) if args.chipyard
                     else chipyard_engine.default_sim(REPO_ROOT)),
        "chipyard_env": chipyard_engine.default_env(REPO_ROOT),
        "max_cycles": args.max_cycles,
        "sim_md5": None,
    }
    work_dir = _abspath(args.work_dir)
    opts = [o.strip().lstrip("-") for o in args.opt.split(",") if o.strip()]

    needed = ["clang", "llc", "llvm_mc", "ldlld"]
    if args.engine == "qemu":
        needed.append("qemu")
    else:
        needed.append("chipyard")
    for key in needed:
        _require_exec(tools[key], key)
    if args.engine == "chipyard":
        tools["sim_md5"] = chipyard_engine.md5_of(tools["chipyard"])
        if tools["sim_md5"] is None:
            sys.stderr.write("ERROR: cannot read the chipyard simulator binary: "
                             f"{tools['chipyard']}\n")
            sys.exit(2)
    if not os.path.isdir(tools["embench_src"]):
        sys.stderr.write(
            f"ERROR: embench source not found: {tools['embench_src']}\n"
            "       run 'make fetch' first (component embench-iot)\n"
        )
        sys.exit(2)
    for key in ("include", "runtime", "mem_runtime", "crt0", "lds"):
        if not os.path.exists(tools[key]):
            sys.stderr.write(f"ERROR: {key} not found: {tools[key]}\n")
            sys.exit(2)

    # ISS-373: refuse on an active writer, then hash what we read at both ends.
    guard = writer_guard.start_guard(
        args, [tools["clang"], tools["llc"], tools["llvm_mc"], tools["ldlld"],
               tools["qemu"], tools["bootrom"]], label="run_embench_e2e")

    src_root = os.path.join(tools["embench_src"], "src")
    if not os.path.isdir(src_root):
        sys.stderr.write(f"ERROR: benchmark source root not found: {src_root}\n")
        sys.exit(2)
    benchmarks = discover_benchmarks(src_root)
    if args.only:
        wanted = [b.strip() for b in args.only.split(",") if b.strip()]
        unknown = [b for b in wanted if b not in benchmarks]
        if unknown:
            sys.stderr.write("ERROR: --only names not in the corpus: %s\n"
                             % ", ".join(unknown))
            return 2
        benchmarks = [b for b in benchmarks if b in set(wanted)]
    if not benchmarks:
        sys.stderr.write(f"ERROR: no benchmarks found under {src_root}\n")
        sys.exit(2)
    if not opts:
        sys.stderr.write("ERROR: no optimisation levels requested\n")
        sys.exit(2)

    os.makedirs(work_dir, exist_ok=True)
    sys.stdout.write(
        f"run_embench_e2e: {len(benchmarks)} benchmark(s) x {len(opts)} opt "
        f"level(s) {opts} (现场统计; 非写死), engine={tools['engine']}, "
        f"work dir {work_dir}\n"
    )
    if tools["engine"] == "chipyard":
        sys.stdout.write(
            f"  chipyard sim: {tools['chipyard']} md5={tools['sim_md5']} "
            f"max-cycles={tools['max_cycles']}\n")
    sys.stdout.write(f"  benchmarks: {', '.join(benchmarks)}\n")
    # Flush the batch identity before the first (possibly hours-long) case so
    # a progress board can read done/total while the batch is still starting.
    sys.stdout.flush()

    # Incremental visibility (m16-testcases-001): open the sink *before* the
    # first case so an unwritable path fails now, not after hours of work.
    sink = None
    if args.jsonl_out:
        try:
            sink = JsonlSink(args.jsonl_out)
        except OSError as exc:
            sys.stderr.write(f"ERROR: cannot open --jsonl-out "
                             f"{args.jsonl_out}: {exc}\n")
            return 2

    try:
        results = run_suite(benchmarks, opts, tools, work_dir, args.timeout,
                            args.verbose, max(1, args.jobs),
                            on_case=sink.write if sink else None)
    except OSError as exc:
        if sink is None:
            raise
        sink.close()
        sys.stderr.write(f"ERROR: cannot append --jsonl-out "
                         f"{args.jsonl_out}: {exc}\n")
        return 2
    if sink is not None:
        sink.close()

    # Anti-false-green: the batch must have run against one simulator binary.
    if tools["engine"] == "chipyard":
        md5_end = chipyard_engine.md5_of(tools["chipyard"])
        if md5_end != tools["sim_md5"]:
            sys.stdout.write(
                f"\n[FAIL] simulator binary changed during the run: md5 "
                f"{tools['sim_md5']} -> {md5_end}\n")
            return 1

    if args.json_out:
        try:
            write_json(args.json_out, results, tools["engine"])
        except OSError as exc:
            sys.stderr.write(f"ERROR: cannot write --json-out {args.json_out}: "
                             f"{exc}\n")
            return 2

    # Structural closure (§2.21): executed set == discovered set (no silent skip).
    executed = sorted({r.bench for r in results})
    if executed != sorted(benchmarks):
        sys.stdout.write(
            f"[FAIL] executed set != discovered set "
            f"(discovered={len(benchmarks)} executed={len(executed)})\n"
        )
        return 1

    hits = sum(1 for r in results if r.actual is not None)
    passed = sum(1 for r in results if r.passed)
    by_status = status_counts(results)
    sys.stdout.write(
        f"\nResults: {passed}/{len(results)} passed, "
        f"{len(results) - passed} not passed; live hits {hits}/{len(results)} "
        f"(逐项命中; 现场统计)\n"
    )
    sys.stdout.write("  verdicts: %s\n" % ", ".join(
        "%s %d" % (k, v) for k, v in sorted(by_status.items())))
    if tools["engine"] == "chipyard":
        cyc = [r.cycles for r in results if r.cycles is not None]
        secs = sum(r.seconds or 0.0 for r in results)
        if cyc:
            sys.stdout.write(
                f"  chipyard: cycles min={min(cyc)} max={max(cyc)} "
                f"sum={sum(cyc)}; wall {secs:.1f}s; sim md5={tools['sim_md5']}\n")

    # ---- built-in counter-example self-test -------------------------------
    if args.inject:
        green = [r for r in results if r.passed]
        if not green:
            sys.stderr.write("INJECT: FAIL -- no baseline-PASSing case to inject into\n")
            return 2
        target = green[0]
        wrong_expected = (target.expected + 1) % 256
        wrong_passed, _reason = verdict(target.actual, wrong_expected)
        sys.stdout.write(
            f"\nINJECT: case={target.bench} (-{target.opt}) "
            f"expected {target.expected} -> {wrong_expected} "
            f"(actual={target.actual})\n"
        )
        if wrong_passed:
            sys.stderr.write(
                "INJECT: FAIL -- judgement did NOT detect the wrong expected value "
                "(comparison is not live)\n"
            )
            return 1
        sys.stdout.write(
            "INJECT: PASS -- judgement correctly reported FAIL on a wrong value\n"
        )
        return 0 if writer_guard.finish_guard(guard) else 1

    guard_ok = writer_guard.finish_guard(guard)
    if passed != len(results) or hits != len(results):
        sys.stdout.write("run_embench_e2e: FAIL\n")
        return 1
    if not guard_ok:
        return 1
    sys.stdout.write("run_embench_e2e: PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
