#!/usr/bin/env python3
"""Atomics integration driver (TESTCASES-056t).

Builds and runs the five probes in ``tests/inst/atomics/`` for ONE link mode per
invocation (static first, then dynamic, exactly like the libc-test driver) and
judges them with the independent oracle in ``oracle_atomics.py``.

What it does NOT do
-------------------
* It never replaces the libc-test driver (``run_libc_test_user_suite.py``):
  the 19 thread cases are run by that driver from the evidence script.
* It never invents an expectation: every expected value comes from
  ``oracle_atomics.py`` (pure Python, no component product imported).  The
  probes only print raw observations.
* It never turns a known component defect into a pass: a cell listed as
  ``xfail`` in the oracle must match the *defect's exact signature*; a cell
  that recovers the semantic value is reported as ``XPASS`` and fails the run
  (that is the signal to delete the xfail entry after the fix).  Both defects
  measured here (``ISS-312``/``ISS-313``) are fixed by the ``LLVM-121t``
  rework, so the expectation table now carries no xfail cell; the machinery is
  kept and exercised by ``oracle.selftest_xfail()`` in ``--inject`` mode.

Checks per probe
----------------
counter.c        N*M mutex increments, ``--rounds`` rounds, exact COUNT and SUM
c11_alltypes.c   full (type x op x order) matrix + shared-object cells
atomic_builtins.c the ``__atomic_*`` matrix, neighbour bytes of sub-word RMW,
                 and no ``__atomic_*``/``__sync_*`` undefined symbol in the
                 object or the linked image (link-time libcall assertion)
aba_treiber.c    Treiber invariants + tagged-ABA replay, ``--rounds`` rounds
barrier_probe.c  structural: ``fence`` count in ``clang -S`` and
                 ``llvm-objdump -d`` == the oracle's a_barrier site count, and
                 every ``fence`` carries the full-barrier immediate 4095
                 (0xFFF, all six access classes); the runtime ordering
                 observation is a note, not a check (a single-hart user-mode
                 run is insensitive)

Usage
-----
  run_atomics_probe.py --link-mode static  --json-out /tmp/.../static.json
  run_atomics_probe.py --link-mode dynamic --json-out /tmp/.../dynamic.json
  run_atomics_probe.py --link-mode static  --json-out ... --inject

``--json-out`` is required (the run is an artifact, not a console dump).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_atomics as oracle  # noqa: E402

TOOLCHAIN_BIN = os.path.join(".dadao", "cross-toolchain", "bin")
DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_OBJDUMP = os.path.join(TOOLCHAIN_BIN, "llvm-objdump")
DEFAULT_MUSL = os.path.join(".work", "source", "musl")
DEFAULT_SYSROOT = os.path.join(".dadao", "dadao-unknown-elf")
# Build products and run scratch live under /tmp (never in the tree); the
# evidence script keeps the stage log under .work/log/<module>/<TASK>/.
DEFAULT_WORK_DIR = os.path.join("/tmp", "opencode", "TESTCASES-056t",
                                "probe-work")
PROBE_DIR = os.path.join("tests", "inst", "atomics")

PROBES = ["counter", "c11_alltypes", "atomic_builtins", "aba_treiber",
          "barrier_probe"]


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, timeout=None, cwd=None):
    """Run a command, never raise, return (rc, stdout+stderr, seconds)."""
    t0 = time.time()
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout,
                           cwd=cwd, text=True, errors="replace")
        return p.returncode, p.stdout, time.time() - t0
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, out + "\n<timeout after %ss>\n" % timeout, timeout
    except FileNotFoundError as e:
        return 127, str(e), 0.0


class Ctx(object):
    def __init__(self, args):
        self.args = args
        self.mode = args.link_mode
        self.checks = []
        self.notes = []
        self.builds = []
        self.work = os.path.abspath(args.work_dir)
        self.out = os.path.join(self.work, args.link_mode)
        os.makedirs(os.path.join(self.out, "boot"), exist_ok=True)
        self.rtlib = None

    def add(self, name, expected, actual, ok, kind="check", detail=""):
        self.checks.append({"name": name, "expected": expected,
                            "actual": actual, "ok": bool(ok), "kind": kind,
                            "detail": detail})
        return ok

    def note(self, name, value):
        self.notes.append({"name": name, "value": value})


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def clang_resource_include(ctx):
    rc, out, _ = run([ctx.args.clang, "-print-resource-dir"])
    if rc != 0:
        raise SystemExit("clang -print-resource-dir failed: %s" % out)
    return os.path.join(out.strip(), "include")


def compile_flags(ctx):
    m = ctx.args.musl
    inc = [
        "-nostdinc",
        "-isystem", clang_resource_include(ctx),
        "-I", os.path.join(m, "arch", "dadao"),
        "-I", os.path.join(m, "arch", "generic"),
        "-I", os.path.join(m, "obj", "include"),
        "-I", os.path.join(m, "include"),
        "-I", os.path.join(m, "src", "internal"),
        "-I", os.path.join(m, "obj", "src", "internal"),
    ]
    return inc


def source_of(probe):
    return os.path.join(PROBE_DIR, probe + ".c")


def compile_probe(ctx, probe, src, tag=""):
    """Compile (and link) one probe for the current link mode."""
    flags = compile_flags(ctx)
    obj = os.path.join(ctx.out, "%s%s.o" % (probe, tag))
    elf = os.path.join(ctx.out, "%s%s.elf" % (probe, tag))
    cmd = [ctx.args.clang, "--target=dadao-unknown-elf"] + flags + [
        "-std=c11", "-O2", "-Wall", "-fno-builtin"]
    if ctx.mode == "dynamic":
        cmd.append("-fPIC")
    cmd += ["-c", src, "-o", obj]
    rc, out, secs = run(cmd)
    ctx.builds.append({"probe": probe + tag, "step": "compile", "rc": rc,
                       "cmd": " ".join(cmd), "log": out[-4000:]})
    if rc != 0:
        return obj, elf, rc, out
    crt = os.path.join(ctx.args.musl, "lib", "crt1.o")
    lib = os.path.join(ctx.args.musl, "lib",
                       "libc.a" if ctx.mode == "static" else "libc.so")
    link = [ctx.args.ldlld, "-o", elf, crt, obj, "--start-group", lib,
            ctx.rtlib, "--end-group"]
    if ctx.mode == "dynamic":
        link += ["-dynamic-linker", "/lib/ld-musl-dadao.so.1"]
    rc2, out2, _ = run(link)
    ctx.builds.append({"probe": probe + tag, "step": "link", "rc": rc2,
                       "cmd": " ".join(link), "log": out2[-4000:]})
    return obj, elf, rc if rc != 0 else rc2, out + out2


def run_elf(ctx, elf, argv=(), timeout=None):
    cmd = [ctx.args.qemu]
    if ctx.mode == "dynamic":
        cmd += ["-L", ctx.args.sysroot]
    cmd += [elf] + [str(a) for a in argv]
    return run(cmd, timeout=timeout if timeout is not None else ctx.args.timeout)


def undefined_atomic_symbols(ctx, path):
    """Count undefined __atomic_*/__sync_* symbols in an object or ELF."""
    rc, out, _ = run([ctx.args.objdump, "--syms", path])
    if rc != 0:
        return None, out
    n = 0
    for line in out.splitlines():
        if "UND" not in line:
            continue
        if "__atomic_" in line or "__sync_" in line:
            n += 1
    return n, out


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def check_counter(ctx):
    elf = os.path.join(ctx.out, "counter.elf")
    if not os.path.exists(elf):
        ctx.add("counter build", 0, "missing elf", False)
        return
    for r in range(1, ctx.args.rounds + 1):
        rc, out, secs = run_elf(ctx, elf, [ctx.args.threads, ctx.args.iters])
        ctx.add("counter round %d exit" % r, 0, rc, rc == 0,
                detail="%.1fs" % secs)
        obs = oracle.parse_counter(out)
        for c in oracle.compare_counter(obs, ctx.args.threads,
                                        ctx.args.iters,
                                        "counter round %d" % r):
            ctx.add(c["name"], c["expected"], c["actual"], c["ok"],
                    detail=c["detail"])


def check_c11(ctx):
    elf = os.path.join(ctx.out, "c11_alltypes.elf")
    if not os.path.exists(elf):
        ctx.add("c11 build", 0, "missing elf", False)
        return
    rc, out, secs = run_elf(ctx, elf)
    ctx.add("c11 exit", 0, rc, rc == 0, detail="%.1fs" % secs)
    obs, ptrs = oracle.parse_c11(out)
    for c in oracle.compare_c11(obs, ptrs):
        ctx.add(c["name"], c["expected"], c["actual"], c["ok"], c["kind"],
                c["detail"])
    ctx.note("c11_cells", len([k for k in obs]))
    ctx.note("c11_ptr_a", ptrs.get("a"))
    ctx.note("c11_ptr_b", ptrs.get("b"))


def check_builtins(ctx):
    obj = os.path.join(ctx.out, "atomic_builtins.o")
    elf = os.path.join(ctx.out, "atomic_builtins.elf")
    if not os.path.exists(elf):
        ctx.add("builtins build", 0, "missing elf", False)
        return
    rc, out, secs = run_elf(ctx, elf)
    ctx.add("builtins exit", 0, rc, rc == 0, detail="%.1fs" % secs)
    obs = oracle.parse_builtins(out)
    for c in oracle.compare_builtins(obs):
        ctx.add(c["name"], c["expected"], c["actual"], c["ok"], c["kind"],
                c["detail"])
    for what, path in (("object", obj), ("elf", elf)):
        n, log = undefined_atomic_symbols(ctx, path)
        if n is None:
            ctx.add("builtins %s undefined-symbol scan" % what, "readable",
                    "llvm-objdump failed", False)
        else:
            ctx.add("builtins %s __atomic_/__sync_ undefined" % what, 0, n,
                    n == 0)


def check_aba(ctx):
    elf = os.path.join(ctx.out, "aba_treiber.elf")
    if not os.path.exists(elf):
        ctx.add("aba build", 0, "missing elf", False)
        return
    for r in range(1, ctx.args.rounds + 1):
        rc, out, secs = run_elf(ctx, elf, [ctx.args.threads,
                                           ctx.args.aba_iters])
        ctx.add("aba round %d exit" % r, 0, rc, rc == 0,
                detail="%.1fs" % secs)
        obs, notes = oracle.parse_aba(out)
        for c in oracle.compare_aba(obs, ctx.args.threads, ctx.args.aba_iters,
                                    "aba round %d" % r):
            ctx.add(c["name"], c["expected"], c["actual"], c["ok"])
        for n in notes:
            # Disclosed platform limit: recorded, never a passing check.
            ctx.note("platform_limit", n)
        if r == 1 and "ABA_NOTE same_value_write" in out:
            ctx.note("same_value_write", "undetectable (sc compares the "
                                          "whole 8-byte word value)")


def fence_lines(text):
    vals = []
    for line in text.splitlines():
        m = re.search(r"\bfence\s+[^,]+,\s*(0x[0-9a-fA-F]+|\d+)\b", line)
        if m:
            vals.append(int(m.group(1), 0))
    return vals


def check_barrier(ctx):
    src = source_of("barrier_probe")
    with open(src) as f:
        sites = oracle.barrier_expected(f.read())
    ctx.add("barrier a_barrier sites (oracle)", "> 0", sites, sites > 0)
    elf = os.path.join(ctx.out, "barrier_probe.elf")
    if not os.path.exists(elf):
        ctx.add("barrier build", 0, "missing elf", False)
        return
    rc, out, _ = run_elf(ctx, elf)
    ctx.add("barrier exit", 0, rc, rc == 0)
    ctx.note("barrier_runtime",
             "; ".join(l for l in out.splitlines() if l.startswith("BARRIER_")))
    # Runtime ordering is insensitive on a single-hart user-mode run: a note.
    ctx.note("barrier_runtime_note",
             "insensitive observation (one guest hart, host SC memory); "
             "not a hard criterion -- insensitive is not equivalent")
    asm = os.path.join(ctx.out, "barrier_probe.s")
    flags = compile_flags(ctx)
    cmd = [ctx.args.clang, "--target=dadao-unknown-elf"] + flags + [
        "-std=c11", "-O2", "-fno-builtin"]
    if ctx.mode == "dynamic":
        cmd.append("-fPIC")
    cmd += ["-S", src, "-o", asm]
    rc, out, _ = run(cmd)
    ctx.add("barrier clang -S", 0, rc, rc == 0, detail=out[-500:])
    if rc == 0:
        with open(asm) as f:
            vals = fence_lines(f.read())
        ctx.add("barrier fence count (asm)", sites, len(vals),
                len(vals) == sites)
        bad = [v for v in vals if v != 4095]
        ctx.add("barrier fence immediate all 0xFFF (asm)", [], bad,
                not bad, detail="0xFFF = all six access classes")
    rc, out, _ = run([ctx.args.objdump, "-d", elf])
    if rc != 0:
        ctx.add("barrier objdump", 0, rc, False, detail=out[-500:])
    else:
        vals = fence_lines(out)
        ctx.add("barrier fence count (objdump)", sites, len(vals),
                len(vals) == sites)
        bad = [v for v in vals if v != 4095]
        ctx.add("barrier fence immediate all 0xFFF (objdump)", [], bad,
                not bad)


# ---------------------------------------------------------------------------
# injections (reachable-FAIL self test)
# ---------------------------------------------------------------------------
def _mutate(src, dst, old, new):
    with open(src) as f:
        text = f.read()
    if old not in text:
        raise RuntimeError("injection anchor not found in %s" % src)
    with open(dst, "w") as f:
        f.write(text.replace(old, new, 1))
    return md5(src), md5(dst)


def inject_counter(ctx):
    """A non-atomic read-modify-write must lose updates -> COUNT != N*M."""
    src = source_of("counter")
    dst = os.path.join(ctx.out, "inject_counter.c")
    # The memory clobber is what makes this a *lost update* injection: without
    # it the optimiser keeps the counter in a register and the run is exact.
    before, after = _mutate(
        src, dst,
        "        pthread_mutex_lock(&mu);\n        shared_count++;\n"
        "        pthread_mutex_unlock(&mu);\n",
        "        shared_count++; /* injected: no mutex */\n"
        '        __asm__ __volatile__("" : : : "memory");\n')
    if before == after:
        return ctx.add("inject counter: file changed", "different", "same",
                       False)
    obj, elf, rc, log = compile_probe(ctx, "counter", dst, tag="-inject")
    if rc != 0:
        return ctx.add("inject counter: build", 0, rc, False, detail=log[-600:])
    rc, out, secs = run_elf(ctx, elf, [ctx.args.threads, ctx.args.iters])
    obs = oracle.parse_counter(out)
    expect = ctx.args.threads * ctx.args.iters
    lost = obs.get("COUNTER_COUNT") != expect or rc != 0
    ctx.add("inject counter (no mutex) -> lost updates", "COUNT != %d or "
            "rc != 0" % expect,
            "COUNT=%s SUM=%s rc=%s" % (obs.get("COUNTER_COUNT"),
                                       obs.get("COUNTER_SUM"), rc), lost,
            detail="%.1fs (private slots stay exact: ISS-294 signature)" % secs)
    return lost


def inject_aba(ctx):
    """Treat a failed CAS as success -> duplicated/lost nodes."""
    src = source_of("aba_treiber")
    dst = os.path.join(ctx.out, "inject_aba.c")
    before, after = _mutate(
        src, dst,
        "        if (atomic_compare_exchange_weak_explicit(&head, &old, new,\n"
        "                                                  memory_order_acq_rel,\n"
        "                                                  memory_order_acquire))\n"
        "            return p;\n",
        "        if (1) /* injected: CAS result ignored */\n"
        "            return p;\n")
    if before == after:
        return ctx.add("inject aba: file changed", "different", "same", False)
    obj, elf, rc, log = compile_probe(ctx, "aba_treiber", dst, tag="-inject")
    if rc != 0:
        return ctx.add("inject aba: build", 0, rc, False, detail=log[-600:])
    rc, out, secs = run_elf(ctx, elf, [ctx.args.threads, ctx.args.aba_iters])
    obs, notes = oracle.parse_aba(out)
    expect = ctx.args.threads * ctx.args.aba_iters
    bad = (obs.get("ABA_POPS") != expect
           or obs.get("ABA_NODE_MISMATCH", 0) != 0
           or obs.get("ABA_EMPTY_FINAL") != 1
           or rc != 0)
    ctx.add("inject aba (CAS failure treated as success)", "invariant red",
            "pops=%s mismatch=%s empty=%s rc=%s" % (
                obs.get("ABA_POPS"), obs.get("ABA_NODE_MISMATCH"),
                obs.get("ABA_EMPTY_FINAL"), rc), bad,
            detail="%.1fs" % secs)
    return bad


def inject_barrier(ctx):
    """a_barrier degraded to an empty statement -> fence count 0 vs sites."""
    src = source_of("barrier_probe")
    with open(src) as f:
        text = f.read()
    sites = oracle.barrier_expected(text)  # oracle: shipped source
    dst = os.path.join(ctx.out, "inject_barrier.c")
    with open(dst, "w") as f:
        f.write(re.sub(r"(?m)^[ \t]*a_barrier\(\);[ \t]*$", "    ;", text))
    if md5(dst) == md5(src):
        return ctx.add("inject barrier: file changed", "different", "same",
                       False)
    flags = compile_flags(ctx)
    asm = os.path.join(ctx.out, "inject_barrier.s")
    cmd = [ctx.args.clang, "--target=dadao-unknown-elf"] + flags + [
        "-std=c11", "-O2", "-fno-builtin"]
    if ctx.mode == "dynamic":
        cmd.append("-fPIC")
    cmd += ["-S", dst, "-o", asm]
    rc, out, _ = run(cmd)
    if rc != 0:
        return ctx.add("inject barrier: compile", 0, rc, False,
                       detail=out[-400:])
    with open(asm) as f:
        vals = fence_lines(f.read())
    red = len(vals) != sites
    ctx.add("inject barrier (empty a_barrier) -> fence count mismatch",
            "%d fences" % sites, "%d fences" % len(vals), red,
            detail="oracle sites from the shipped probe, build from the "
                   "degraded copy")
    return red


def injection_mode(ctx):
    injs = [("counter-no-mutex", inject_counter),
            ("aba-cas-ignored", inject_aba),
            ("barrier-empty", inject_barrier)]
    src_md5 = {p: md5(source_of(p)) for p in PROBES}
    red = []
    for name, fn in injs:
        ok = fn(ctx)
        red.append((name, bool(ok)))
    # The repository sources must be untouched by the injections.
    for p in PROBES:
        now = md5(source_of(p))
        ctx.add("inject source %s unchanged" % p, src_md5[p], now,
                now == src_md5[p], detail="md5")
    # Restored/original build must be green again.
    check_c11(ctx)
    ctx.add("inject: original c11 green after injections",
            "no fail", "see c11 checks",
            not any(c["name"].startswith("c11") and not c["ok"]
                    for c in ctx.checks))
    for name, ok in red:
        ctx.add("injection %s went red" % name, "red", "red" if ok
                else "stayed green", ok)
    # The xfail machinery must stay verifiable now that no cell is xfail:
    # synthetic observations (exact signature -> XFAIL, semantic value ->
    # XPASS red, changed signature -> red) are judged by the same helpers the
    # real comparison path uses.
    for c in oracle.selftest_xfail():
        ctx.add(c["name"], c["expected"], c["actual"], c["ok"],
                detail=c["detail"])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--link-mode", choices=("static", "dynamic"),
                    required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--objdump", default=DEFAULT_OBJDUMP)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--sysroot", default=DEFAULT_SYSROOT)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--rounds", type=int, default=5,
                    help="rounds for the concurrency probes (default 5)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--iters", type=int, default=250000,
                    help="mutex increments per thread (default: ISS-294 "
                         "reproduction size)")
    ap.add_argument("--aba-iters", type=int, default=10000,
                    help="push/pop pairs per thread (default 10000)")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--inject", action="store_true",
                    help="injection self-test (reachable FAIL)")
    args = ap.parse_args(argv)

    ctx = Ctx(args)
    rc, out, _ = run([args.clang, "--target=dadao-unknown-elf", "-rtlib="
                      "compiler-rt", "-print-libgcc-file-name"])
    if rc != 0:
        raise SystemExit("cannot resolve compiler-rt: %s" % out)
    ctx.rtlib = out.strip()

    env = {
        "clang": {"path": args.clang, "md5": md5(args.clang)},
        "ldlld": {"path": args.ldlld, "md5": md5(args.ldlld)},
        "qemu": {"path": args.qemu, "md5": md5(args.qemu)},
        "musl": args.musl,
        "libc": {"path": os.path.join(args.musl, "lib", "libc.a"),
                 "md5": md5(os.path.join(args.musl, "lib", "libc.a"))},
        "libc_so": {"path": os.path.join(args.musl, "lib", "libc.so"),
                    "md5": md5(os.path.join(args.musl, "lib", "libc.so"))},
        "rtlib": ctx.rtlib,
    }

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futs = [pool.submit(compile_probe, ctx, p, source_of(p)) for p in PROBES]
        for f, p in zip(futs, PROBES):
            obj, elf, rc, log = f.result()
            ctx.add("build %s" % p, 0, rc, rc == 0, detail=log[-600:])

    if args.inject:
        injection_mode(ctx)
    else:
        check_counter(ctx)
        check_c11(ctx)
        check_builtins(ctx)
        check_aba(ctx)
        check_barrier(ctx)

    counts = {"pass": 0, "fail": 0, "xfail": 0}
    defects = {}
    for c in ctx.checks:
        if not c["ok"]:
            counts["fail"] += 1
        elif c["kind"] == "xfail":
            counts["xfail"] += 1
            defects[c["detail"]] = defects.get(c["detail"], 0) + 1
        else:
            counts["pass"] += 1
    result = "PASS" if counts["fail"] == 0 else "FAIL"
    doc = {
        "task": "TESTCASES-056t",
        "mode": args.link_mode,
        "params": {"threads": args.threads, "iters": args.iters,
                   "aba_iters": args.aba_iters, "rounds": args.rounds,
                   "inject": bool(args.inject)},
        "env": env,
        "builds": ctx.builds,
        "checks": ctx.checks,
        "notes": ctx.notes,
        "known_defects": defects,
        "summary": {"total": len(ctx.checks), "pass": counts["pass"],
                    "fail": counts["fail"], "xfail": counts["xfail"],
                    "notes": len(ctx.notes)},
        "result": result,
    }
    json_out = os.path.abspath(args.json_out)
    os.makedirs(os.path.dirname(json_out), exist_ok=True)
    with open(json_out, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")

    for c in ctx.checks:
        if c["ok"] and c["kind"] == "xfail":
            tag = "XFAIL"
        elif c["ok"]:
            tag = "PASS "
        else:
            tag = "FAIL "
        print("  %s %s | expected=%s | actual=%s%s" % (
            tag, c["name"], c["expected"], c["actual"],
            (" | " + c["detail"]) if c["detail"] else ""))
    for n in ctx.notes:
        print("  NOTE  %s = %s" % (n["name"], n["value"]))
    print("%s (%s): total=%d pass=%d fail=%d xfail=%d notes=%d"
          % (result, args.link_mode, len(ctx.checks), counts["pass"],
             counts["fail"], counts["xfail"], len(ctx.notes)))
    for label, n in sorted(defects.items()):
        print("  known defect [%s]: %d cell(s) measured, not counted as pass"
              % (label, n))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
