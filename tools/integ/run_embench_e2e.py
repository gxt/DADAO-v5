#!/usr/bin/env python3
"""run_embench_e2e.py -- Embench-IoT end-to-end gate (INTEG-025t, M6).

Compiles every Embench-IoT benchmark from ``<embench-src>/src/*/`` with the
DADAO cross toolchain at each requested optimisation level, links it against
the frozen M6 runtime (crt0 + freestanding mem/str runtime + Embench board
shim) and runs it under QEMU, judging the **guest process exit code**.

Value channel (Embench convention, see ``support/main.c``): ``main`` returns
``!correct`` -- i.e. the guest exit code is ``0`` iff the benchmark's own
result verification passed.  So the per-case judgement is: guest exit == 0
(PASS) else FAIL.  (There is no "correct" string; Embench reports via the exit
code -- confirmed in ``.work/log/integ/embench-analysis.md``.)

Pipeline per (benchmark, optimisation level):

    clang -target dadao-unknown-elf -<O> -ffreestanding -fno-builtin \
          -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=1 \
          -c support/{main,beebsc}.c <src>/<b>/*.c <boardsupport>.c  -> *.o
    clang ... -c tests/scripts/embench_runtime.c                    -> *.o
    llc  -march=dadao -O0 -filetype=obj dadao_mem_runtime.ll        -> *.o
    llvm-mc --triple=dadao -filetype=obj codegen_crt0.s             -> crt0.o
    ld.lld -T dadao.lds *.o                                         -> <b>.elf
    timeout N qemu-system-dadao -M dadao-m1 -kernel <b>.elf \
            -semihosting-config enable=on,target=native             -> guest exit

Judgement (fail-closed):
  * every (benchmark, level) must build and exit 0  -> PASS
  * build-step non-zero / non-zero or faulted exit / timeout -> FAIL
  * source tree missing / zero benchmarks / missing tool -> setup error (2)

Structural closure (lessons §8.35): the benchmark corpus IS ``<embench-src>/src/``
(a manifest-locked component, so it cannot silently change).  The driver
enumerates that directory live and requires *every* discovered benchmark to be
compiled, linked and executed -- the executed set must equal the discovered set,
so a driver bug cannot silently skip a benchmark.  Counts are reported live
(never hardcoded; lessons §8.34).

Exit status:
  0  every case PASS
  1  at least one case FAIL
  2  setup error (missing tool / source / zero benchmarks)

``--inject`` is a built-in counter-example self-test: after a green baseline it
re-judges one PASSing case against a wrong expected value (1) and requires the
judgement to FAIL -- proving the comparison is live.
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

# Install root (ADR-0016 D7/D9): resolve tools from the single source of truth
# (tools/infra/paths.py) instead of hardcoding .dadao/.
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
import paths as _dadao_paths  # noqa: E402

_TARGET_BIN = str(_dadao_paths.host_toolchain_bin())

DEFAULT_CLANG = os.path.join(_TARGET_BIN, "clang")
DEFAULT_LLC = os.path.join(_TARGET_BIN, "llc")
DEFAULT_LLVM_MC = os.path.join(_TARGET_BIN, "llvm-mc")
DEFAULT_LDLD = os.path.join(_TARGET_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(_TARGET_BIN, "qemu-system-dadao")
DEFAULT_EMBENCH_SRC = ".work/source/embench-iot"
DEFAULT_INCLUDE = "tests/scripts/embench_include"
DEFAULT_RUNTIME = "tests/scripts/embench_runtime.c"
DEFAULT_MEM_RUNTIME = "tests/scripts/dadao_mem_runtime.ll"
DEFAULT_CRT0 = "tests/scripts/codegen_crt0.s"
DEFAULT_LDS = "tests/scripts/dadao.lds"
DEFAULT_BOARDSUPPORT = "examples/dadao/boardsupport.c"
# Work dir under the SDK test-artifacts root (ADR-0016 D6 / Process-05 §6),
# resolved through paths.py (D7); never hardcoded.
DEFAULT_WORK_DIR = str(_dadao_paths.test_artifacts_dir() / "m6-embench")
DEFAULT_OPTS = "O0,O2"
DEFAULT_TIMEOUT = 60

# Machine fault exit codes (ADR-0004 D5.8): 0x80 | spec cause bit index.
FAULT_NAMES = {
    0x87: "UNMAPPED", 0x88: "ILLI", 0x89: "UNDI", 0x8A: "RASOF",
    0x8B: "RASUF", 0x8C: "MALIGN", 0x8D: "IALIGN",
}


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


class CaseResult:
    __slots__ = ("bench", "opt", "expected", "actual", "passed", "reason")

    def __init__(self, bench, opt, expected):
        self.bench = bench
        self.opt = opt
        self.expected = expected
        self.actual = None
        self.passed = False
        self.reason = ""


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
    res = CaseResult(bench, opt, 0)
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
    rc, _o, err, timed = _run([tools["ldlld"], "-T", tools["lds"]] + objs + ["-o", elf])
    if timed or rc != 0:
        res.reason = f"ld.lld failed (rc={rc}): {err.strip()[:200]}"
        return res

    # 6. run under QEMU; guest exit code == process exit code.
    rc, _o, err, timed = _run(
        [tools["qemu"], "-M", "dadao-m1", "-kernel", elf,
         "-semihosting-config", "enable=on,target=native",
         "-display", "none", "-nographic"],
        timeout=timeout,
    )
    if timed:
        res.reason = f"qemu timeout after {timeout}s"
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


def run_suite(benchmarks, opts, tools, work_dir, timeout, verbose=False):
    results = []
    for opt in opts:
        for bench in benchmarks:
            res = build_and_run(bench, opt, tools, work_dir, timeout, verbose)
            actual = "?" if res.actual is None else str(res.actual)
            status = "PASS" if res.passed else "FAIL"
            sys.stdout.write(
                f"  {status}  {bench} (-{opt})  expected={res.expected} actual={actual} "
                f"exit={actual}  ({res.reason})\n"
            )
            sys.stdout.flush()
            results.append(res)
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
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--opt", default=DEFAULT_OPTS,
                    help="comma-separated optimisation levels, e.g. 'O0,O2'")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--inject", action="store_true",
                    help="counter-example self-test: re-judge one PASSing case "
                         "against a wrong expected value and require FAIL")
    args = ap.parse_args()

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
    }
    work_dir = _abspath(args.work_dir)
    opts = [o.strip().lstrip("-") for o in args.opt.split(",") if o.strip()]

    for key in ("clang", "llc", "llvm_mc", "ldlld", "qemu"):
        _require_exec(tools[key], key)
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

    src_root = os.path.join(tools["embench_src"], "src")
    if not os.path.isdir(src_root):
        sys.stderr.write(f"ERROR: benchmark source root not found: {src_root}\n")
        sys.exit(2)
    benchmarks = discover_benchmarks(src_root)
    if not benchmarks:
        sys.stderr.write(f"ERROR: no benchmarks found under {src_root}\n")
        sys.exit(2)
    if not opts:
        sys.stderr.write("ERROR: no optimisation levels requested\n")
        sys.exit(2)

    os.makedirs(work_dir, exist_ok=True)
    sys.stdout.write(
        f"run_embench_e2e: {len(benchmarks)} benchmark(s) x {len(opts)} opt "
        f"level(s) {opts} (现场统计; 非写死), work dir {work_dir}\n"
    )
    sys.stdout.write(f"  benchmarks: {', '.join(benchmarks)}\n")

    results = run_suite(benchmarks, opts, tools, work_dir, args.timeout, args.verbose)

    # Structural closure (§8.35): executed set == discovered set (no silent skip).
    executed = sorted({r.bench for r in results})
    if executed != sorted(benchmarks):
        sys.stdout.write(
            f"[FAIL] executed set != discovered set "
            f"(discovered={len(benchmarks)} executed={len(executed)})\n"
        )
        return 1

    hits = sum(1 for r in results if r.actual is not None)
    passed = sum(1 for r in results if r.passed)
    sys.stdout.write(
        f"\nResults: {passed}/{len(results)} passed, "
        f"{len(results) - passed} failed; live hits {hits}/{len(results)} "
        f"(逐项命中; 现场统计)\n"
    )

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
        return 0

    if passed != len(results) or hits != len(results):
        sys.stdout.write("run_embench_e2e: FAIL\n")
        return 1
    sys.stdout.write("run_embench_e2e: PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
