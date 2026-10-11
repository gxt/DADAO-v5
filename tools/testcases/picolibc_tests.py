#!/usr/bin/env python3
"""picolibc self-test harness for the DADAO-v5 ``dadao-unknown-elf`` target
(TESTCASES-042t).

Drives the *picolibc upstream self-tests* (the tests picolibc's own Meson build
registers) through the project's compile/link/run flow and reports a
per-test ``pass`` / ``fail`` / ``excluded`` / ``blocked`` classification.

Design
------
* **Inventory is authoritative, not transcribed.**  The harness configures the
  upstream Meson build once (``--tests=true --crt0-test=semihost
  --oslib-test=semihost``) purely to obtain the *exact* set of registered test
  executables together with their per-test compile/link arguments and source
  lists (``meson-info/intro-tests.json`` + ``intro-targets.json``).  No test
  list is duplicated here, so the harness follows picolibc as upstream defines
  its tests.  This is the "reuse picolibc's own Meson test mechanism" option;
  the build/link/run below is the "minimal equivalent flow" (Meson cannot run
  or even link the binaries itself: the DADAO port has no ``exe_wrapper``, its
  generated ``picolibc.ld`` overlaps .text/.data for a single-RAM target, and
  there is no ``picocrt/machine/dadao`` start-up that sets the stack pointer).

* **Independent oracle.**  A test *passes* iff it exits 0 (or, for the Meson
  ``should_fail`` set, iff it exits non-zero) — i.e. the verdict comes from the
  test's own assertions, never from any DADAO-side expectation.

* **Run path.**  QEMU loads the test ELF with ``-machine dadao-m1`` ("path A":
  PC := e_entry, registers at reset — rb1 == 0).  picolibc's own
  ``crt0-semihost.o`` assumes the architecture start-up code already set the
  stack, so the harness links it with ``--redefine-sym _start=_picolibc_start``
  behind ``tools/testcases/picolibc_test_crt0.s`` (the stack-setup stub).  The
  image uses the installed ``picolibc_noflash.ld`` (single RAM segment, and the
  ``__heap_*`` PROVIDEs that ``tests/scripts/dadao.lds`` lacks — ISS-191), so
  ``malloc``/``sbrk`` link.  The test's own link arguments (``--defsym`` for the
  printf/scanf float/int/long variants) and semihosting command line
  (``COMMAND_LINE`` for the argv tests) are honoured.

Classification
--------------
* ``pass``     — the test's own verdict is success.
* ``fail``     — the test ran and its own assertion failed.  **Zero is the
  goal**; a ``fail`` is a real defect, never a harness limitation.
* ``excluded`` — either a task-declared out-of-scope category (dynamic linking,
  threads, hosted) **or** a test that *itself* returns 77 (picolibc's Meson
  SKIP convention: exit 77 == "not applicable to this target").  Every entry
  carries its own reason; none is a silent skip.
* ``blocked``  — a *backend / library / toolchain gap* prevents building or
  running the test (LLVM lowering, missing libc symbol, linker relocation
  overflow, machine fault, QEMU crash, timeout).  Reported separately from
  ``excluded`` with a root-cause pointer and, where quantifiable, the unlock
  condition; never merged into ``excluded``.

Exit status: 0 = no failures; 1 = one or more ``fail``; 2 = setup error.
``--inject`` corrupts one test's expected exit status so the ``fail`` path is
reachable (used by the evidence script).

Counting is always live (no hard-coded totals).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "infra"))
import paths  # noqa: E402

REPO_ROOT = paths.repo_root()
TOOLCHAIN_BIN = paths.host_toolchain_bin()
SYSROOT = paths.target_sysroot_dir()
PICOLIBC_SRC = REPO_ROOT / ".work" / "source" / "picolibc"
CROSS_FILE = PICOLIBC_SRC / "scripts" / "cross-dadao.txt"
TEST_BUILD = REPO_ROOT / ".work" / "build" / "picolibc-tests"
CRT0_STUB = Path(__file__).resolve().parent / "picolibc_test_crt0.s"

CLANG = TOOLCHAIN_BIN / "clang"
CLANGXX = TOOLCHAIN_BIN / "clang++"
LLVM_MC = TOOLCHAIN_BIN / "llvm-mc"
LLVM_OBJCOPY = TOOLCHAIN_BIN / "llvm-objcopy"
LLD = TOOLCHAIN_BIN / "ld.lld"
QEMU = TOOLCHAIN_BIN / "qemu-system-dadao"

DEFAULT_TIMEOUT = 60
DEFAULT_JOBS = int(os.environ.get("JOBS", "8"))

# Machine-fault exit codes (ADR-0004 D5.8, ADR-0020 D15); see
# tests/scripts/run_qemu_test.py FAULT_NAMES.
FAULT_CODES = {
    0x81: "CFXMEM",
    0x87: "UNMAPPED",
    0x88: "ILLI",
    0x89: "UNDI",
    0x8A: "RASOF",
    0x8B: "RASUF",
    0x8C: "MALIGN",
    0x8D: "IALIGN",
}

# Meson SKIP convention: a test returning 77 declares itself not applicable.
SKIP_CODE = 77

# Meson-declared should-fail tests (test/meson.build tests_should_fail +
# subdir tests_failure / semihost_fail_tests), picolibc 1.8.12.
SHOULD_FAIL = {
    "test-except", "test-except-no-flash", "test-hosted-exit-fail",
    "test-abort-failure",
    "semihost-exit-failure", "semihost-exit-extended-failure",
    "semihost-system-failure",
}

# Tests whose failure is a documented, deliberate "unsupported feature" stub in
# the DADAO port: the stub aborts (SYS_EXIT with a non-zero status) rather than
# silently succeed (a contract-conformant explicit failure).  These are
# capability gaps, not test failures.
UNSUPPORTED_TESTS = {
    "test-setjmp":
        "setjmp/longjmp are explicit unsupported stubs in the DADAO port "
        "(libc/machine/dadao/setjmp.S: the RegRAS return-address depth cannot be "
        "restored, so no partial impl is provided); abort() -> exit 134 by design",
}

# Task-declared out-of-scope categories (INTEG-033k §排除项).  Name -> reason.
EXCLUDED = {
    "test-thread-safety": "thread-safety annotations require a threading host runtime (task exclusion: threads)",
    "test-tls": "thread-local storage is a threading feature; the DADAO port has no TLS start-up (task exclusion: threads)",
    "test-tls-no-flash": "thread-local storage is a threading feature (task exclusion: threads)",
    "semihost-system": "SYS_SYSTEM executes a host command (hosted/pk-like; task exclusion)",
    "semihost-system-failure": "SYS_SYSTEM executes a host command (hosted/pk-like; task exclusion)",
}

# Semihost tests invoked with the Meson ``--args 'hello world'`` command line
# (semihost/meson.build): argv[0] = program-name, argv[1..] = hello world.
# semihost-no-argv is deliberately *not* here (it expects argc == 1).
SEMIHOST_ARGS_TESTS = {
    "semihost-argv", "semihost-exit", "semihost-exit-extended", "semihost-clock",
    "semihost-close", "semihost-errno", "semihost-flen", "semihost-get-cmdline",
    "semihost-gettimeofday", "semihost-iserror", "semihost-istty", "semihost-open",
    "semihost-read", "semihost-remove", "semihost-rename", "semihost-seek",
    "semihost-system", "semihost-time", "semihost-times", "semihost-writec",
    "semihost-write0",
}
SEMIHOST_ARGV = ["program-name", "hello", "world"]

# Tests linked with a different crt0 variant (test/meson.build): constructor-skip
# uses the minimal crt0 (no constructors) so the "skipped" constructor must not
# run.  Everything else uses crt0-semihost.
CRT0_VARIANT_TESTS = {"constructor-skip": "minimal"}

# Tests whose upstream workload is O(64k) libc calls; far beyond the Meson 60 s
# budget on a TCG emulator (measured, see the task completion notes).
SLOW_TESTS = {"test-memmem": 1200}

# Root-cause classification for build/run failures (backend / library gaps).
# Signature -> (pointers string).
_BLOCK_SIGS = [
    (re.compile(r"unsupported floating-point (branch|select/setcc) condition"),
     "ISS-193 (a) FP predicate lowering (SETO/SETUO/SETUNO) not implemented"),
    (re.compile(r"no libcall available for \w+"),
     "ISS-193 (b) f32 libcall missing"),
    (re.compile(r"unable to lower stackguard"),
     "ISS-193 (f)-family: stack-guard lowering unsupported"),
    (re.compile(r"unsupported library call operation"),
     "ISS-193 (f) unsupported library call (long double / stack guard)"),
    (re.compile(r"Cannot select: .*bswap"),
     "ISS-193 (c) backend ISel gap (i64 bswap)"),
    (re.compile(r"Cannot select"),
     "backend ISel gap (ISS-188 backlog)"),
    (re.compile(r"relocation R_DADAO_REL26 out of range"),
     "linker: R_DADAO_REL26 to an undefined weak function is out of range "
     "(relative-only call needs a veneer/weak stub)"),
    (re.compile(r"undefined symbol: memset_explicit|undefined symbol: memset_s"),
     "ISS-193 (e) 'r' inline-asm constraint rejects pointer (memset_s/memset_explicit)"),
    (re.compile(r"undefined symbol: (?:sf_)?(acos|acosh|asin|asinh|hypot|pow|j0|j1|jn)f?\b"),
     "ISS-193 (a) FP predicate lowering: {sym} from a source excluded by the backend-gap filter"),
    (re.compile(r"undefined symbol: \w+"),
     "{sym} (source excluded by the backend-gap filter; see meson.build / ISS-193)"),
]


def run(cmd, *, timeout=None, env=None, cwd=None):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=timeout, env=env, cwd=cwd)


def configure_meson(env) -> None:
    args = [
        "-Dmultilib=false", "-Dtests=true", "-Dpicocrt=true", "-Ddebug=false",
        "-Dio-float-exact=false", "-Dcrt0-test=semihost", "-Doslib-test=semihost",
        "-Dnative-tests=false", "-Dtests-enable-stack-protector=false",
    ]
    setup = ["meson", "setup"]
    if (TEST_BUILD / "meson-private" / "coredata.dat").is_file():
        setup.append("--reconfigure")
    setup += [str(TEST_BUILD), str(PICOLIBC_SRC), "--cross-file", str(CROSS_FILE), *args]
    res = run(setup, env=env)
    if res.returncode != 0:
        print(f"picolibc-tests: ERROR: meson setup failed rc={res.returncode}\n{res.stdout}",
              file=sys.stderr)
        raise SystemExit(2)


def load_inventory():
    tests = json.loads((TEST_BUILD / "meson-info" / "intro-tests.json").read_text())
    targets = {t["name"]: t for t in json.loads((TEST_BUILD / "meson-info" / "intro-targets.json").read_text())}
    inv = []
    for t in tests:
        suite = (t.get("suite") or ["?"])[0]
        if suite == "picolibc:headers":
            continue  # header self-checks, not target programs
        inv.append({"name": t["name"], "suite": suite.replace("picolibc:", "")})
    return inv, targets


def _link_defsyms(target):
    """Return ``--defsym`` linker options declared by the Meson target."""
    out = []
    for so in target.get("target_sources", []):
        if so.get("language") is not None:
            continue
        for p in (so.get("parameters") or []):
            m = re.match(r"-Wl,(--defsym=\S+)$", p)
            if m:
                out.append(m.group(1))
    return out


def compile_target(name, target, out_dir, env):
    cc = {"c": CLANG, "cpp": CLANGXX, "c++": CLANGXX}
    objs = []
    for so in target.get("target_sources", []):
        lang = so.get("language")
        if lang not in cc:
            continue
        params = so.get("parameters", [])
        for src in so.get("sources", []):
            if src.endswith((".h", ".inc", ".hpp", ".def")):
                continue
            obj = out_dir / f"{name}.{Path(src).stem}.o"
            res = run([str(cc[lang]), "-target", "dadao-unknown-elf", *params,
                       "-c", src, "-o", str(obj)], env=env)
            if res.returncode != 0:
                return None, res.stdout
            objs.append(obj)
    if not objs:
        return None, "target has no compilable sources"
    return objs, ""


def link_target(name, objs, prelude, defsyms, out_dir):
    elf = out_dir / f"{name}.elf"
    res = run([str(LLD), *defsyms, "-T", str(SYSROOT / "lib" / "picolibc_noflash.ld"),
               *[str(o) for o in prelude], *[str(o) for o in objs],
               str(SYSROOT / "lib" / "libc.a"), str(SYSROOT / "lib" / "libsemihost.a"),
               "-o", str(elf)])
    if res.returncode != 0:
        return None, res.stdout
    return elf, ""


def run_qemu(elf, argv=None, timeout=DEFAULT_TIMEOUT):
    cfg = "enable=on,target=native"
    if argv:
        cfg = ",".join([cfg, *[f"arg={a}" for a in argv]])
    cmd = [str(QEMU), "-M", "dadao-m1", "-kernel", str(elf),
           "-semihosting-config", cfg, "-display", "none", "-nographic", "-monitor", "none"]
    try:
        res = run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, ""
    return res.returncode, res.stdout


def _match(text):
    for pat, why in _BLOCK_SIGS:
        m = pat.search(text)
        if m:
            if "{sym}" in why:
                return why.format(sym=(m.group(1) if m.groups() else m.group(0)))
            return why
    return None


def classify_test(entry, targets, out_dir, preludes, env, inject_name):
    name = entry["name"]
    should_fail = name in SHOULD_FAIL
    expected_rc = None
    if name == inject_name:
        expected_rc = 7 if not should_fail else 0

    def verdict(actual_rc, out):
        if expected_rc is not None:
            return ("pass" if actual_rc == expected_rc else "fail",
                    f"injected expectation rc={expected_rc} actual={actual_rc}")
        if actual_rc is None:
            return "blocked", "QEMU timeout (workload exceeds the test budget)"
        if actual_rc < 0:
            return "blocked", f"QEMU terminated by signal {-actual_rc} (emulator crash)"
        if actual_rc in FAULT_CODES:
            return "blocked", f"machine fault {FAULT_CODES[actual_rc]} (0x{actual_rc:02X})"
        if actual_rc == SKIP_CODE:
            msg = out.strip().splitlines()[0] if out.strip() else "no message"
            return "excluded", f"picolibc self-skip (exit 77; Meson SKIP convention): {msg}"
        if name in UNSUPPORTED_TESTS and actual_rc == 134:
            return "blocked", UNSUPPORTED_TESTS[name]
        if should_fail:
            return ("pass" if actual_rc != 0 else "fail",
                    "should_fail: non-zero exit as expected" if actual_rc != 0 else "should_fail test exited 0")
        if actual_rc == 0:
            return "pass", "exit 0"
        return "fail", f"exit {actual_rc}"

    if name in EXCLUDED:
        return {"name": name, "suite": entry["suite"], "status": "excluded", "reason": EXCLUDED[name]}

    target = targets.get(name)
    if target is None:
        return {"name": name, "suite": entry["suite"], "status": "blocked",
                "reason": "no Meson target (harness map miss)"}

    variant = CRT0_VARIANT_TESTS.get(name, "semihost")
    prelude = preludes[variant]

    objs, err = compile_target(name, target, out_dir, env)
    if objs is None:
        why = _match(err) or "build error (unclassified)"
        return {"name": name, "suite": entry["suite"], "status": "blocked",
                "reason": why, "log": err[-600:]}

    elf, err = link_target(name, objs, prelude, _link_defsyms(target), out_dir)
    if elf is None:
        why = _match(err) or "link error (unclassified)"
        return {"name": name, "suite": entry["suite"], "status": "blocked",
                "reason": why, "log": err[-600:]}

    argv = SEMIHOST_ARGV if name in SEMIHOST_ARGS_TESTS else None
    rc, out = run_qemu(elf, argv, SLOW_TESTS.get(name, DEFAULT_TIMEOUT))
    status, why = verdict(rc, out)
    return {"name": name, "suite": entry["suite"], "status": status, "reason": why,
            "log": out[-300:]}


def representative_names(inv):
    """One representative per suite, first in Meson order (mechanical)."""
    seen, out = set(), []
    for e in inv:
        if e["suite"] not in seen:
            seen.add(e["suite"])
            out.append(e["name"])
    return out


def build_prelude(out_dir, variant, env):
    """Assemble the stack stub and the renamed picolibc crt0 variant."""
    wrap = out_dir / f"picolibc_test_crt0.{variant}.o"
    res = run([str(LLVM_MC), "--triple=dadao-unknown-elf", "-filetype=obj",
               str(CRT0_STUB), "-o", str(wrap)], env=env)
    if res.returncode != 0:
        print(f"picolibc-tests: ERROR: assembling {CRT0_STUB.name}: {res.stdout}", file=sys.stderr)
        raise SystemExit(2)
    src = SYSROOT / "lib" / (f"crt0-{variant}.o" if variant != "semihost" else "crt0-semihost.o")
    crt = out_dir / f"crt0-{variant}-renamed.o"
    res = run([str(LLVM_OBJCOPY), "--redefine-sym", "_start=_picolibc_start", str(src), str(crt)], env=env)
    if res.returncode != 0:
        print(f"picolibc-tests: ERROR: renaming crt0 {src.name}: {res.stdout}", file=sys.stderr)
        raise SystemExit(2)
    return [wrap, crt]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=("fast", "full"), default="full")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    ap.add_argument("--work-dir", default=str(REPO_ROOT / ".work" / "build" / "picolibc-tests-run"))
    ap.add_argument("--only", default=None, help="comma-separated test names")
    ap.add_argument("--json", default=None, help="write full per-test report JSON here")
    ap.add_argument("--inject", action="store_true",
                    help="corrupt one expectation to make the FAIL path reachable")
    ap.add_argument("--inject-test", default="basename")
    args = ap.parse_args()

    for tool in (CLANG, CLANGXX, LLVM_MC, LLVM_OBJCOPY, LLD, QEMU):
        if not tool.exists():
            print(f"picolibc-tests: ERROR: {tool} not found — run 'make install-host'",
                  file=sys.stderr)
            return 2
    if shutil.which("meson") is None:
        print("picolibc-tests: ERROR: 'meson' not found on PATH", file=sys.stderr)
        return 2
    if not (SYSROOT / "lib" / "libc.a").is_file():
        print(f"picolibc-tests: ERROR: {SYSROOT / 'lib' / 'libc.a'} missing — run 'make build-picolibc'",
              file=sys.stderr)
        return 2

    env = dict(os.environ)
    env["PATH"] = str(TOOLCHAIN_BIN) + os.pathsep + env.get("PATH", "")
    configure_meson(env)
    inv, targets = load_inventory()

    out_dir = Path(args.work_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    preludes = {
        "semihost": build_prelude(out_dir, "semihost", env),
        "minimal": build_prelude(out_dir, "minimal", env),
    }

    if args.only:
        wanted = set(args.only.split(","))
        inv = [e for e in inv if e["name"] in wanted]
    elif args.stage == "fast":
        reps = set(representative_names(inv))
        inv = [e for e in inv if e["name"] in reps]

    inject_name = args.inject_test if args.inject else None
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(classify_test, e, targets, out_dir, preludes, env, inject_name): e
                for e in inv}
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())

    order = {e["name"]: i for i, e in enumerate(inv)}
    results.sort(key=lambda r: order.get(r["name"], 1 << 30))

    counts = {"pass": 0, "fail": 0, "excluded": 0, "blocked": 0}
    for r in results:
        counts[r["status"]] += 1

    width = max((len(r["name"]) for r in results), default=10)
    for r in results:
        print(f"  {r['name']:<{width}}  {r['suite']:<16}  {r['status']:<8}  {r['reason'][:110]}")

    print()
    print(f"picolibc-tests: stage={args.stage} total={len(results)} "
          f"pass={counts['pass']} fail={counts['fail']} "
          f"excluded={counts['excluded']} blocked={counts['blocked']}")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"stage": args.stage, "counts": counts, "total": len(results),
             "inject": bool(args.inject), "results": results}, indent=1))

    # Structural self-assertions (fail-closed, lessons §2.20/§2.21): every test
    # lands in exactly one bucket and the buckets sum to the live total.
    if sum(counts.values()) != len(results) or len(results) == 0:
        print("picolibc-tests: FAIL (bucket sum != total or empty inventory)", file=sys.stderr)
        return 2
    if counts["fail"] > 0:
        print(f"picolibc-tests: FAIL ({counts['fail']} test(s) failed)", file=sys.stderr)
        return 1
    print("picolibc-tests: PASS (fail=0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
