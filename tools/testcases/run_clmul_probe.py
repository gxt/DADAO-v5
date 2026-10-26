#!/usr/bin/env python3
"""DADAO-v5 ``clmul.o`` integration driver (TESTCASES-057t).

Builds and runs the three probes in ``tests/inst/clmul/`` for ONE optimisation
level per invocation, and judges every observation with the independent
oracle in ``oracle_clmul.py``.

What this driver does NOT do
----------------------------
* It never invents an expectation: the probes print raw observations only
  (operands, halves, intermediate GHASH values, CRC words).  Every expected
  value is computed by ``oracle_clmul.py`` from GF(2)[x] polynomial arithmetic
  and the published standards' vectors -- never from QEMU or LLVM output.
* It never turns a missing observation into a pass: the record sets are
  compared with the oracle's own tables (missing *and* extra records are red).
* It never picks the clmul path for the probe: instruction selection is
  asserted structurally (one `clmul.o` per intrinsic spelling, `rd0` on the
  discarded side) as well as semantically.

Checks
------
clmul_edges.c   boundary cells (0, 1, top bit, (1<<63)^2 -> bit 126, all ones,
                1<<k * 1<<m) + 64 seeded random cells, each judged on all
                three compiler-visible exits (low half via generic
                ``llvm.clmul``, high half via ``llvm.dadao.clmul.hi``, the
                ``__int128`` builtin) plus the ``{lo,hi}`` pair intrinsic; the
                ``rev.o`` bit reversal used by the GHASH bridge is judged too
                (a broken reversal must not look like a clmul defect).
clmul_ghash.c   GHASH(H,A,C) end to end: GCM specification Appendix B test
                cases 1-4 (published H, every X_i and GHASH), zero H,
                H = all ones, single block, two-block chain, AAD + partial
                blocks; the last step (len(A)||len(C)) included.
clmul_crc32c.c  CRC-32C (Castagnoli) through a clmul folding kernel +
                GF(2) Barrett reduction, at lengths 0/1/7/8/9/15/16/17/63/64/
                65/1000 and the classic published vectors, judged against the
                bit-serial reference; ``"123456789" -> 0xE3069283`` pins the
                parameters.

Usage
-----
  run_clmul_probe.py --opt O0 --json-out /tmp/.../o0.json
  run_clmul_probe.py --opt O2 --json-out /tmp/.../o2.json
  run_clmul_probe.py --opt O2 --json-out ... --inject   # reachable-FAIL proof

``--json-out`` is required (the run is an artifact, not a console dump).
Exit: 0 = all checks green; 1 = at least one FAIL; 2 = setup error.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_clmul as oracle  # noqa: E402

TOOLCHAIN_BIN = os.path.join(".dadao", "cross-toolchain", "bin")
DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_OBJDUMP = os.path.join(TOOLCHAIN_BIN, "llvm-objdump")
DEFAULT_MUSL = os.path.join(".work", "source", "musl")
DEFAULT_WORK_DIR = os.path.join("/tmp", "opencode", "TESTCASES-057t",
                                "probe-work")
PROBE_DIR = os.path.join("tests", "inst", "clmul")
IR_SOURCE = "clmul_ir.ll"
PROBES = ("clmul_edges", "clmul_ghash", "clmul_crc32c")
SOURCES = tuple(p + ".c" for p in PROBES) + (IR_SOURCE,)

# Per-symbol instruction expectations for the IR object: exactly one
# `clmul.o` per spelling, and the discarded half must be `rd0` (that is the
# half binding: rdhA = high, rdhB = low -- ADR-0035 D2).
ASM_IR = {
    "clmul_generic_lo": {"clmul.o": 1, "dst0": "rd0"},   # high half dropped
    "clmul_intr_hi": {"clmul.o": 1, "dst1": "rd0"},      # low half dropped
    "clmul_pair_lo": {"clmul.o": 1},
    "clmul_pair_hi": {"clmul.o": 1},
}
# Whole-object expectations for the algorithm probes.  The kernels are static
# functions: at -O0 only the out-of-line wrapper holds the instruction (one
# site, four calls), at -O2 they are inlined/unrolled (more sites), so the
# count is asserted as a lower bound.  ``mul_max`` is the stronger half of the
# GHASH assertion: that probe contains no ordinary multiply at all, so any
# `mul.uo` there means the carry-less multiply was expanded into a bit-by-bit
# sequence (exactly the LLVM-122t F2 defect, which emitted 14 `mul.uo`) or the
# probe stopped using the instruction.
ASM_OBJ = {
    "clmul_ghash": {"clmul_min": 1, "mul_max": 0},
    "clmul_crc32c": {"clmul_min": 1},
}

OBJ_RE = re.compile(r"^[0-9a-f]+\s+<([^>]+)>:\s*$")
CLMUL_RE = re.compile(r"\bclmul\.o\s+\{([^}]*)\}")


# ── small helpers ─────────────────────────────────────────────────────────
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tool_id(path):
    st = os.stat(path)
    return {"path": os.path.realpath(path), "size": st.st_size,
            "md5": md5(path)}


def run(cmd, timeout=None):
    """Run a command, never raise: (rc, stdout+stderr, seconds)."""
    t0 = time.time()
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout,
                           text=True, errors="replace")
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
        self.checks = []
        self.notes = []
        self.builds = []
        self.runs = []
        self.work = os.path.abspath(args.work_dir)
        self.out = os.path.join(self.work, args.opt)
        os.makedirs(self.out, exist_ok=True)
        self.rtlib = None
        self.probe_dir = args.probe_dir
        self.src_md5 = {}

    def add(self, name, expected, actual, ok, detail=""):
        self.checks.append({"name": name, "expected": expected,
                            "actual": actual, "ok": bool(ok),
                            "detail": detail})
        return bool(ok)

    def note(self, name, value):
        self.notes.append({"name": name, "value": value})


# ── build / run ───────────────────────────────────────────────────────────
def clang_resource_include(ctx):
    rc, out, _ = run([ctx.args.clang, "-print-resource-dir"])
    if rc != 0:
        raise SystemExit("clang -print-resource-dir failed: %s" % out)
    return os.path.join(out.strip(), "include")


def compile_flags(ctx):
    m = ctx.args.musl
    return [
        "-nostdinc",
        "-isystem", clang_resource_include(ctx),
        "-I", os.path.join(m, "arch", "dadao"),
        "-I", os.path.join(m, "arch", "generic"),
        "-I", os.path.join(m, "obj", "include"),
        "-I", os.path.join(m, "include"),
        "-I", os.path.join(m, "src", "internal"),
        "-I", os.path.join(m, "obj", "src", "internal"),
    ]


def compile_c(ctx, src, obj):
    cmd = ([ctx.args.clang, "--target=dadao-unknown-elf"]
           + compile_flags(ctx)
           + ["-std=c11", "-" + ctx.args.opt, "-Wall", "-c", src, "-o", obj])
    rc, out, _secs = run(cmd)
    return rc, out, cmd


def compile_ir(ctx, src, obj):
    cmd = [ctx.args.clang, "--target=dadao-unknown-elf", "-" + ctx.args.opt,
           "-c", src, "-o", obj]
    rc, out, _secs = run(cmd)
    return rc, out, cmd


def link(ctx, elf, objs):
    cmd = ([ctx.args.ldlld, "-o", elf,
            os.path.join(ctx.args.musl, "lib", "crt1.o")] + objs
           + ["--start-group", os.path.join(ctx.args.musl, "lib", "libc.a"),
              ctx.rtlib, "--end-group"])
    rc, out, secs = run(cmd)
    return rc, out, cmd


def build_ir_object(ctx):
    """Compile tests/inst/clmul/clmul_ir.ll (the paths with no C spelling)."""
    obj = os.path.join(ctx.out, "clmul_ir.o")
    rc, log, cmd = compile_ir(ctx, os.path.join(ctx.probe_dir, IR_SOURCE),
                              obj)
    ctx.builds.append({"probe": "clmul_ir", "step": "compile-ir", "rc": rc,
                       "cmd": " ".join(cmd), "log": log[-4000:]})
    return obj, rc, log


def build_probe(ctx, probe, src, ir_obj, tag="", out_dir=None):
    """Compile one C probe, link it with the IR object, return (obj, elf, rc)."""
    out_dir = out_dir or ctx.out
    obj = os.path.join(out_dir, "%s%s.o" % (probe, tag))
    elf = os.path.join(out_dir, "%s%s.elf" % (probe, tag))
    rc, log, cmd = compile_c(ctx, src, obj)
    ctx.builds.append({"probe": probe + tag, "step": "compile-c", "rc": rc,
                       "cmd": " ".join(cmd), "log": log[-4000:]})
    if rc != 0:
        return obj, elf, rc, log
    rc2, log2, cmd2 = link(ctx, elf, [obj, ir_obj])
    ctx.builds.append({"probe": probe + tag, "step": "link", "rc": rc2,
                       "cmd": " ".join(cmd2), "log": log2[-4000:]})
    return obj, elf, rc if rc != 0 else rc2, log + log2


def run_elf(ctx, elf, timeout=120):
    return run([ctx.args.qemu, elf], timeout=timeout)


# ── judging ───────────────────────────────────────────────────────────────
def add_judged(ctx, check):
    return ctx.add(check["name"], check["expected"], check["actual"],
                   check["ok"], check.get("detail", ""))


def judge_group(ctx, checks):
    """Add a judged list; return the number of red checks."""
    red = 0
    for c in checks:
        if not c["ok"]:
            red += 1
        add_judged(ctx, c)
    return red


def disasm_blocks(ctx, obj):
    rc, out, _ = run([ctx.args.objdump, "-d", obj])
    blocks, cur, order = {}, None, []
    for line in out.splitlines():
        m = OBJ_RE.match(line.strip())
        if m:
            cur = m.group(1).strip()
            blocks[cur] = []
            order.append(cur)
            continue
        if cur is not None:
            blocks[cur].append(line)
    return rc, blocks, out


def clmul_sites(body):
    """(count, [(dst0, dst1), ...]) of clmul.o instructions in one block."""
    n, dsts = 0, []
    for line in body:
        for m in CLMUL_RE.finditer(line):
            n += 1
            parts = [p.strip() for p in m.group(1).split(",")]
            dsts.append(tuple(parts))
    return n, dsts


def check_asm(ctx):
    """Structural: which instruction the compiler selected, and its halves."""
    ir_obj = os.path.join(ctx.out, "clmul_ir.o")
    rc, blocks, out = disasm_blocks(ctx, ir_obj)
    ctx.add("objdump clmul_ir.o", 0, rc, rc == 0, detail=out[-300:])
    for sym, spec in ASM_IR.items():
        body = blocks.get(sym)
        if body is None:
            ctx.add("asm/%s: symbol present" % sym, "present", "missing",
                    False)
            continue
        n, dsts = clmul_sites(body)
        ctx.add("asm/%s: clmul.o count" % sym, spec["clmul.o"], n,
                n == spec["clmul.o"],
                detail="one instruction per compiler-visible spelling")
        for pos in ("dst0", "dst1"):
            if pos not in spec:
                continue
            idx = 0 if pos == "dst0" else 1
            got = dsts[0][idx] if dsts and len(dsts[0]) > idx else "?"
            ctx.add("asm/%s: %s (discarded half)" % (sym, pos),
                    spec[pos], got, got == spec[pos],
                    detail="rd0 on the discarded side == the half binding "
                           "the probe's values rely on")
    for probe, spec in ASM_OBJ.items():
        obj = os.path.join(ctx.out, probe + ".o")
        rc, blocks, out = disasm_blocks(ctx, obj)
        if rc != 0:
            ctx.add("objdump %s.o" % probe, 0, rc, False, detail=out[-300:])
            continue
        total = 0
        mul = 0
        per_sym = {}
        for sym, body in blocks.items():
            n, _ = clmul_sites(body)
            if n:
                per_sym[sym] = n
            total += n
            for line in body:
                toks = line.split()
                if len(toks) >= 2 and toks[1] == "mul.uo":
                    mul += 1
        ctx.add("asm/%s.o: clmul.o count" % probe,
                ">= %d" % spec["clmul_min"], total,
                total >= spec["clmul_min"],
                detail="per symbol: %s (-O0 keeps the wrapper out of line)"
                % per_sym)
        if "mul_max" in spec:
            ctx.add("asm/%s.o: ordinary mul.uo count" % probe,
                    "<= %d" % spec["mul_max"], mul, mul <= spec["mul_max"],
                    detail="a non-zero count means the carry-less multiply "
                           "was expanded into mul.uo (LLVM-122t F2)")


# ── injections (reachable FAIL) ───────────────────────────────────────────
def _mutate(src, dst, old, new):
    with open(src) as f:
        text = f.read()
    if text.count(old) != 1:
        raise RuntimeError("injection anchor appears %d times in %s"
                           % (text.count(old), src))
    before = md5(src)
    with open(dst, "w") as f:
        f.write(text.replace(old, new, 1))
    return before, md5(dst)


def _red_by(ctx, name, checks):
    red = [c for c in checks if not c["ok"]]
    total = len(checks)
    ctx.add(name, ">= 1 red", "%d/%d red" % (len(red), total),
            bool(red) and total > 0,
            detail="first: %s" % (red[0]["name"] if red else "-"))
    return bool(red)


def inject_oracle(ctx, parsed):
    """Wrong expectations must be caught by the same judging code."""
    _red_by(ctx, "inject oracle: GHASH expected value flipped 1 bit -> red",
            oracle.judge_ghash(parsed["clmul_ghash"],
                               mutation="ghash_bitflip"))
    _red_by(ctx, "inject oracle: CRC-32C with the IEEE polynomial -> red",
            oracle.judge_crc(parsed["clmul_crc32c"],
                             mutation="crc_ieee_poly"))
    _red_by(ctx, "inject oracle: clmul.o high/low halves swapped -> red",
            oracle.judge_edges(parsed["clmul_edges"],
                               mutation="clmul_half_swap"))
    _red_by(ctx, "inject oracle: clmul.o replaced by ordinary multiply -> red",
            oracle.judge_edges(parsed["clmul_edges"],
                               mutation="clmul_ordinary_mul"))
    _red_by(ctx, "inject oracle: rev.o modelled as identity -> red",
            oracle.judge_rev(parsed["clmul_edges"], mutation="rev_identity"))


def inject_c_side(ctx):
    """`clmul.o` -> ordinary `*` in a temporary copy of each probe."""
    inj_dir = os.path.join(ctx.out, "inject-c")
    shutil.rmtree(inj_dir, ignore_errors=True)
    os.makedirs(inj_dir)
    anchor = ("\treturn __builtin_dadao_clmul(a, b);\n")
    degraded = ("\t/* injected: ordinary multiply instead of clmul.o */\n"
                "\treturn (u128)a * (u128)b;\n")
    for probe, group, judge in (
            ("clmul_ghash", "clmul_ghash", oracle.judge_ghash),
            ("clmul_crc32c", "clmul_crc32c", oracle.judge_crc)):
        src = os.path.join(ctx.probe_dir, probe + ".c")
        dst = os.path.join(inj_dir, probe + ".c")
        before, after = _mutate(src, dst, anchor, degraded)
        if before == after:
            ctx.add("inject %s: file changed" % probe, "different", "same",
                    False)
            continue
        shutil.copy(os.path.join(ctx.probe_dir, IR_SOURCE), inj_dir)
        obj = os.path.join(inj_dir, probe + "-inject.o")
        rc, log, _cmd = compile_c(ctx, dst, obj)
        ir_obj = os.path.join(ctx.out, "clmul_ir.o")
        elf = os.path.join(inj_dir, probe + "-inject.elf")
        rc2, log2, _cmd2 = link(ctx, elf, [obj, ir_obj])
        if rc != 0 or rc2 != 0:
            ctx.add("inject %s: build" % probe, 0, rc if rc else rc2, False,
                    detail=(log + log2)[-500:])
            continue
        rc3, out, _ = run_elf(ctx, elf)
        checks = judge(oracle.parse(out))
        _red_by(ctx, "inject C side %s (clmul.o -> *) -> judged red" % probe,
                checks)
        # The same injection must also break the *structural* assertion, i.e.
        # "clmul.o count >= N" is a reachable-FAIL check, not a tautology.
        rc4, blocks, _ = disasm_blocks(ctx, obj)
        total = 0
        for body in blocks.values():
            total += clmul_sites(body)[0]
        ctx.add("inject C side %s: object loses clmul.o" % probe, "0", total,
                rc4 == 0 and total == 0,
                detail="structural check (>= %d) would fail"
                % ASM_OBJ.get(probe, {}).get("clmul_min", 1))


def injection_mode(ctx, parsed):
    inject_oracle(ctx, parsed)
    inject_c_side(ctx)
    # The repository sources must be untouched by any injection.
    for name in SOURCES:
        path = os.path.join(ctx.probe_dir, name)
        ctx.add("inject source %s unchanged" % name, ctx.src_md5[name],
                md5(path), md5(path) == ctx.src_md5[name], detail="md5")
    # The pristine build judged in this same run must be green.
    fails = [c for c in ctx.checks
             if not c["ok"] and not c["name"].startswith("inject")]
    ctx.add("inject: original build green after injections", "no fail",
            "%d fail" % len(fails), not fails,
            detail="; ".join(c["name"] for c in fails[:3]))


# ── main ──────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--opt", choices=("O0", "O2"), required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--probe-dir", default=PROBE_DIR,
                    help="probe sources (default %(default)s); the evidence "
                         "script points this at a mutated copy to prove the "
                         "driver exits non-zero on a real defect")
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--objdump", default=DEFAULT_OBJDUMP)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--inject", action="store_true",
                    help="injection self-test (reachable FAIL)")
    args = ap.parse_args(argv)

    ctx = Ctx(args)
    for name in SOURCES:
        path = os.path.join(ctx.probe_dir, name)
        if not os.path.exists(path):
            raise SystemExit("missing probe source %s" % path)
        ctx.src_md5[name] = md5(path)
    rc, out, _ = run([args.clang, "--target=dadao-unknown-elf", "-rtlib="
                      "compiler-rt", "-print-libgcc-file-name"])
    if rc != 0:
        raise SystemExit("cannot resolve compiler-rt: %s" % out)
    ctx.rtlib = out.strip()

    env = {
        "opt": args.opt,
        "clang": tool_id(args.clang),
        "ldlld": tool_id(args.ldlld),
        "qemu": tool_id(args.qemu),
        "libc": {"path": os.path.join(args.musl, "lib", "libc.a"),
                 "md5": md5(os.path.join(args.musl, "lib", "libc.a"))},
        "rtlib": ctx.rtlib,
        "oracle_md5": md5(os.path.join(HERE, "oracle_clmul.py")),
    }

    t0 = time.time()
    ir_obj, ir_rc, ir_log = build_ir_object(ctx)
    ctx.add("build clmul_ir.ll", 0, ir_rc, ir_rc == 0, detail=ir_log[-600:])
    ir_warns = [l for l in ir_log.splitlines() if "warning:" in l]
    ctx.add("build clmul_ir.ll: no compiler warnings", 0, len(ir_warns),
            not ir_warns, detail="; ".join(ir_warns[:3]))
    for probe in PROBES:
        obj, elf, rc, log = build_probe(ctx, probe,
                                        os.path.join(ctx.probe_dir,
                                                     probe + ".c"), ir_obj)
        ctx.add("build %s" % probe, 0, rc, rc == 0, detail=log[-600:])
        # -Wall is on: a clean build is part of the deliverable.
        warns = [l for l in log.splitlines() if "warning:" in l]
        ctx.add("build %s: no compiler warnings" % probe, 0, len(warns),
                not warns, detail="; ".join(warns[:3]))
    build_secs = time.time() - t0

    parsed_all = {}
    run_secs = 0.0
    for probe in PROBES:
        elf = os.path.join(ctx.out, probe + ".elf")
        if not os.path.exists(elf):
            ctx.add("run %s" % probe, "elf present", "missing", False)
            continue
        rc, out, secs = run_elf(ctx, elf, timeout=args.timeout)
        run_secs += secs
        ctx.add("run %s exit" % probe, 0, rc, rc == 0,
                detail="%.2fs" % secs)
        ctx.runs.append({"probe": probe, "rc": rc, "seconds": round(secs, 3)})
        parsed_all[probe] = oracle.parse(out)
        ctx.add("%s: no unparsed output" % probe, 0,
                len(parsed_all[probe]["junk"]), not parsed_all[probe]["junk"],
                detail="; ".join(parsed_all[probe]["junk"][:3]))

    # The oracle proves itself first (identities + published vectors).
    oracle_checks = oracle.selftest_checks()
    judge_group(ctx, oracle_checks)

    edges = parsed_all.get("clmul_edges", oracle.parse(""))
    judge_group(ctx, oracle.judge_rev(edges))
    judge_group(ctx, oracle.judge_edges(edges))
    judge_group(ctx, oracle.judge_ghash(parsed_all.get("clmul_ghash",
                                                       oracle.parse(""))))
    judge_group(ctx, oracle.judge_crc(parsed_all.get("clmul_crc32c",
                                                     oracle.parse(""))))

    check_asm(ctx)

    ctx.note("levels", "two optimisation levels are run by the Makefile "
                       "target: -O0 and -O2")
    ctx.note("GHASH KAT", "GCM specification Appendix B cases 1-4 "
                          "(H, X_i and GHASH(H,A,C) all published)")
    ctx.note("CRC-32C parameters", "poly 0x1EDC6F41 (reflected 0x82F63B78), "
                                   "init/xorout 0xFFFFFFFF, refin/refout true")
    ctx.note("edges records", len(parsed_all.get("clmul_edges",
                                                 oracle.parse(""))["edge"]))
    ctx.note("ghash records", len(parsed_all.get("clmul_ghash",
                                                 oracle.parse(""))["gout"]))
    ctx.note("crc records", len(parsed_all.get("clmul_crc32c",
                                               oracle.parse(""))["crc"]))

    if args.inject:
        injection_mode(ctx, parsed_all)

    counts = {"pass": 0, "fail": 0}
    for c in ctx.checks:
        if c["ok"]:
            counts["pass"] += 1
        else:
            counts["fail"] += 1
    result = "PASS" if counts["fail"] == 0 else "FAIL"
    doc = {
        "task": "TESTCASES-057t",
        "opt": args.opt,
        "env": env,
        "builds": ctx.builds,
        "runs": ctx.runs,
        "checks": ctx.checks,
        "notes": ctx.notes,
        "summary": {"total": len(ctx.checks), "pass": counts["pass"],
                    "fail": counts["fail"],
                    "compile_seconds": round(build_secs, 2),
                    "run_seconds": round(run_secs, 2)},
        "result": result,
    }
    json_out = os.path.abspath(args.json_out)
    os.makedirs(os.path.dirname(json_out), exist_ok=True)
    with open(json_out, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")

    for c in ctx.checks:
        print("  %s %s | expected=%s | actual=%s%s" % (
            "PASS" if c["ok"] else "FAIL", c["name"], c["expected"],
            c["actual"], (" | " + c["detail"]) if c["detail"] else ""))
    for n in ctx.notes:
        print("  NOTE  %s = %s" % (n["name"], n["value"]))
    print("%s (%s): total=%d pass=%d fail=%d compile=%.1fs run=%.2fs"
          % (result, args.opt, len(ctx.checks), counts["pass"],
             counts["fail"], build_secs, run_secs))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
