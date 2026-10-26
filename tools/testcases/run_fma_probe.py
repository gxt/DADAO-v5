#!/usr/bin/env python3
"""DADAO-v5 fma integration driver (TESTCASES-058t).

Builds the three probes in ``tests/inst/fma/`` for ONE optimisation level per
invocation, runs them under ``qemu-dadao`` (user mode, static musl) and judges
every observation with the independent oracle in ``oracle_fma.py``.

What this driver does NOT do
----------------------------
* It never invents an expectation: the probes print raw observations only
  (``in``/``out``/``pre``/``post`` bit patterns and hashes); every expected
  value, flag and data stream comes from ``oracle_fma.py``, which derives it
  from ``spec/SimRISC-07 §2.5`` + ``contract-fp.md §20`` with exact
  ``Fraction`` arithmetic (no softfloat, no host ``fma``).
* It never turns a missing observation into a pass: the observation set is
  compared with the oracle's own tables (missing *and* extra records are red).
* It never reads a value back from QEMU/LLVM to build an expectation.  The
  disassembly checks only assert *which* instruction the backend selected.

Checks
------
fma_edges.c   single-rounding discriminators (C path, asm path and the
              two-step ``round(a*b)+c`` value in one run, all three judged),
              qNaN/sNaN in every position, ``0xInf`` with a qNaN addend (NV),
              ``Inf+(-Inf)`` (NV), same-sign Inf, Inf addend, exact-zero sign
              under RNE/RDN, overflow (OF|NX) / RTZ (max finite), exact and
              inexact subnormals, underflow to zero, NX, ties under all four
              rf0[33:32] directions (positive and negative), the C library
              name ``fma``/``fmaf`` end-to-end and ``acc += a*b`` contraction.
fma_dot.c     dot products of 16/64/256 doubles, two spellings (``fma`` and
              contracted ``acc += a*b``), every intermediate accumulator
              hashed; 4x4 GEMM (16 cells).
fma_horner.c  Horner degree 5/9 (double) and 5 (single), every intermediate
              hashed; accumulated flags asserted.

Instruction selection (per symbol, both -O0 and -O2): the fused kernels hold a
fused instruction and no ``fomul``/``foadd``/``rf2rf``; ``sel_two_step`` holds
``fomul``+``foadd`` (positive control: a silently broken counter cannot pass).
No ``fma``/``fmaf``/``fmal`` undefined symbol in any object and no such symbol
in the linked image (link-time libcall assertion).

Usage
-----
  run_fma_probe.py --opt O0 --json-out /tmp/.../o0.json
  run_fma_probe.py --opt O2 --json-out /tmp/.../o2.json
  run_fma_probe.py --opt O2 --json-out ... --inject   # reachable-FAIL proof

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
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_fma as oracle  # noqa: E402

TOOLCHAIN_BIN = os.path.join(".dadao", "cross-toolchain", "bin")
DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_OBJDUMP = os.path.join(TOOLCHAIN_BIN, "llvm-objdump")
DEFAULT_NM = os.path.join(TOOLCHAIN_BIN, "llvm-nm")
DEFAULT_MUSL = os.path.join(".work", "source", "musl")
DEFAULT_WORK_DIR = os.path.join("/tmp", "opencode", "TESTCASES-058t",
                                "probe-work")
PROBE_DIR = os.path.join("tests", "inst", "fma")
PROBES = ("fma_edges", "fma_dot", "fma_horner")
SOURCES = tuple(p + ".c" for p in PROBES) + ("fma_common.h",)

# Per-symbol instruction mix.  ``exact`` values are structural (one fused
# instruction per format in the wrapper; no two-step instruction in a fused
# kernel); ``min`` values tolerate loop unrolling at -O2 while still proving
# the instruction is selected.
ASM_SYMBOLS = {
    "fma_edges": {
        "sel_fma": {"exact": {"fofma": 1, "ftfma": 1, "fomul": 0,
                             "foadd": 0, "rf2rf": 0}},
        # control: the deliberately wrong two-step path must really exist, so
        # a "zero fomul/foadd" count cannot pass for the wrong reason.
        "sel_two_step": {"exact": {"fofma": 0, "ftfma": 0, "rf2rf": 0},
                        "min": {"fomul": 1, "foadd": 1}},
    },
    "fma_dot": {
        "dot_fma_run": {"min": {"fofma": 1},
                        "exact": {"fomul": 0, "foadd": 0, "rf2rf": 0}},
        "dot_contract_run": {"min": {"fofma": 1},
                             "exact": {"fomul": 0, "foadd": 0, "rf2rf": 0}},
        "gemm4": {"min": {"fofma": 1},
                  "exact": {"fomul": 0, "foadd": 0, "rf2rf": 0}},
    },
    "fma_horner": {
        "horner_d": {"min": {"fofma": 1},
                     "exact": {"fomul": 0, "foadd": 0, "rf2rf": 0}},
        "horner_f": {"min": {"ftfma": 1},
                     "exact": {"fomul": 0, "foadd": 0, "rf2rf": 0}},
    },
}

FP_MNEMONICS = ("fofma", "ftfma", "fomul", "foadd", "rf2rf")
OBJ_RE = re.compile(r"^[0-9a-f]+\s+<([^>]+)>:\s*$")
LIBCALL_NAMES = ("fma", "fmaf", "fmal")
FMA_IR_RE = re.compile(
    r"(?m)^(\s*)(%[\w.]+) = (?:tail )?call (float|double) "
    r"@llvm\.fma\.f(32|64)\((?:float|double) (%[\w.]+), "
    r"(?:float|double) (%[\w.]+), (?:float|double) (%[\w.]+)\)$")


# ── small helpers ─────────────────────────────────────────────────────────
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tool_id(path):
    st = os.stat(path)
    ident = {"path": os.path.realpath(path), "size": st.st_size,
             "mtime": int(st.st_mtime)}
    ident["md5"] = md5(path) if st.st_size <= (64 << 20) else None
    return ident


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
        self.obs = []
        self.alg = []
        self.work = os.path.abspath(args.work_dir)
        self.out = os.path.join(self.work, args.opt)
        os.makedirs(self.out, exist_ok=True)

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
    """Include paths only.

    NOTE: no ``-fno-builtin`` here.  It would turn the C library names
    ``fma``/``fmaf`` back into out-of-line libm calls (measured: -O0 emitted
    ``call [rb0, 0]`` and pulled musl's ``fma`` into the image), i.e. the
    probe would no longer exercise the fused instruction.  With builtins
    enabled (the LLVM-123t ``fma``/``fmaf`` const-builtin path) both -O0 and
    -O2 emit exactly one fofma/ftfma, which the libcall check asserts.
    """
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


def compile_probe(ctx, probe, src, tag="", out_dir=None):
    out_dir = out_dir or ctx.out
    obj = os.path.join(out_dir, "%s%s.o" % (probe, tag))
    elf = os.path.join(out_dir, "%s%s.elf" % (probe, tag))
    cmd = ([ctx.args.clang, "--target=dadao-unknown-elf"]
           + compile_flags(ctx)
           + ["-std=c11", "-" + ctx.args.opt, "-Wall", "-c", src,
              "-o", obj])
    rc, out, secs = run(cmd)
    ctx.builds.append({"probe": probe + tag, "step": "compile", "rc": rc,
                       "cmd": " ".join(cmd), "log": out[-4000:]})
    if rc != 0:
        return obj, elf, rc, out
    link = [ctx.args.ldlld, "-o", elf, os.path.join(ctx.args.musl, "lib",
                                                    "crt1.o"), obj,
            "--start-group", os.path.join(ctx.args.musl, "lib", "libc.a"),
            ctx.rtlib, "--end-group"]
    rc2, out2, _ = run(link)
    ctx.builds.append({"probe": probe + tag, "step": "link", "rc": rc2,
                       "cmd": " ".join(link), "log": out2[-4000:]})
    return obj, elf, rc if rc != 0 else rc2, out + out2


def run_elf(ctx, elf, timeout=120):
    return run([ctx.args.qemu, elf], timeout=timeout)


# ── judgement ─────────────────────────────────────────────────────────────
def add_judged(ctx, check):
    return ctx.add(check["name"], check["expected"], check["actual"],
                   check["ok"], check.get("detail", ""))


def judge_edges(ctx, parsed):
    ctx.add("edges: no unparsed output", 0, len(parsed["junk"]),
            not parsed["junk"], detail="; ".join(parsed["junk"][:3]))
    for rec in parsed["init"]:
        for c in oracle.judge_init(rec):
            add_judged(ctx, c)
    for rec in parsed["obs"]:
        ctx.obs.append(rec)
        for c in oracle.judge_obs(rec):
            add_judged(ctx, c)
    for rec in parsed["restore"]:
        for c in oracle.judge_restore(rec):
            add_judged(ctx, c)


def judge_alg(ctx, probe, parsed):
    ctx.add("%s: no unparsed output" % probe, 0, len(parsed["junk"]),
            not parsed["junk"], detail="; ".join(parsed["junk"][:3]))
    for rec in parsed["init"]:
        for c in oracle.judge_init(rec):
            add_judged(ctx, c)
    for rec in parsed["alg"]:
        ctx.alg.append(rec)
        for c in oracle.judge_alg(rec):
            add_judged(ctx, c)
    for rec in parsed["restore"]:
        for c in oracle.judge_restore(rec):
            add_judged(ctx, c)


def check_coverage(ctx, parsed):
    """Structural coverage, derived live from the oracle tables."""
    expected = Counter()
    for label, fmt, a, b, c, rm in oracle.DISC_CASES:
        for grp in ("disc", "discasm", "csel"):
            expected[(grp, fmt, label)] += 1
    for label, fmt, a, b, c, rm in oracle.SPECIAL_CASES:
        expected[("special", fmt, label)] += 1
    for label, fmt, a, b, c, rm in oracle.CPATH_CASES:
        expected[("cpath", fmt, label)] += 1
    for label, fmt, a, b, c, rm in oracle.CONTRACT_CASES:
        expected[("contract", fmt, label)] += 1
    actual = Counter((r["group"], r["fmt"], r["label"])
                     for r in parsed["obs"])
    missing, extra = expected - actual, actual - expected
    ctx.add("edges: observation set == oracle tables", "no missing/extra",
            "missing=%d extra=%d" % (sum(missing.values()),
                                     sum(extra.values())),
            not missing and not extra,
            detail="%s" % (list(missing)[:2] + list(extra)[:2]))
    for fmt in oracle.FMT:
        rms = sorted({r["rm"] for r in parsed["obs"]
                      if r["group"] == "special" and r["fmt"] == fmt})
        ctx.add("edges: four rounding modes covered (%s)" % fmt,
                [0, 1, 2, 3], rms, rms == [0, 1, 2, 3])
        ndisc = len([r for r in parsed["obs"]
                     if r["group"] == "disc" and r["fmt"] == fmt])
        ctx.add("edges: discriminators per format (%s)" % fmt, ">= 2",
                ndisc, ndisc >= 2)


def check_alg_coverage(ctx, parsed_alg):
    dots = {(r["len"], r.get("form")) for r in parsed_alg
            if r["group"] == "dot"}
    want_dots = {(n, f) for n in oracle.DOT_LENGTHS
                 for f in ("fma", "contract")}
    ctx.add("dot: lengths x spellings covered", sorted(want_dots),
            sorted(dots), dots == want_dots, detail="missing=%s"
            % sorted(want_dots - dots))
    gemm = {(r["row"], r["col"]) for r in parsed_alg
            if r["group"] == "gemm"}
    want_gemm = {(i, j) for i in range(oracle.GEMM_N)
                 for j in range(oracle.GEMM_N)}
    ctx.add("gemm: 4x4 cells covered", len(want_gemm), len(gemm),
            gemm == want_gemm, detail="missing=%s" % sorted(want_gemm - gemm))
    horner = {(r.get("fmt", "fo"), r["deg"]) for r in parsed_alg
              if r["group"] == "horner"}
    want_horner = ({("fo", d) for d in oracle.HORNER_DEGS_FO} |
                   {("ft", d) for d in oracle.HORNER_DEGS_FT})
    ctx.add("horner: formats x degrees covered", sorted(want_horner),
            sorted(horner), horner == want_horner,
            detail="missing=%s" % sorted(want_horner - horner))


# ── disassembly / libcall ─────────────────────────────────────────────────
def disasm_blocks(ctx, obj):
    rc, out, _ = run([ctx.args.objdump, "-d", "--no-show-raw-insn", obj])
    ctx.add("objdump %s" % os.path.basename(obj), 0, rc, rc == 0,
            detail=out[-300:])
    blocks, cur = {}, None
    for line in out.splitlines():
        m = OBJ_RE.match(line.strip())
        if m:
            cur = m.group(1).strip()
            blocks[cur] = Counter()
            continue
        if cur is None:
            continue
        toks = line.split()
        if len(toks) >= 2 and toks[1].startswith(FP_MNEMONICS):
            blocks[cur][toks[1]] += 1
    return blocks


def check_asm(ctx):
    for probe, syms in ASM_SYMBOLS.items():
        obj = os.path.join(ctx.out, probe + ".o")
        blocks = disasm_blocks(ctx, obj)
        for sym, spec in syms.items():
            body = blocks.get(sym)
            if body is None:
                ctx.add("%s/%s symbol present" % (probe, sym), "present",
                        "missing", False)
                continue
            for mn, want in spec.get("exact", {}).items():
                got = body.get(mn, 0)
                ctx.add("%s/%s: %s count" % (probe, sym, mn),
                        "== %d" % want, got, got == want)
            for mn, want in spec.get("min", {}).items():
                got = body.get(mn, 0)
                ctx.add("%s/%s: %s count" % (probe, sym, mn),
                        ">= %d" % want, got, got >= want)


def libcall_symbols(ctx, path, undefined_only):
    cmd = [ctx.args.nm]
    if undefined_only:
        cmd.append("-u")
    cmd.append(path)
    rc, out, _ = run(cmd)
    hits = []
    for line in out.splitlines():
        toks = line.split()
        if not toks:
            continue
        name = toks[-1]
        if name in LIBCALL_NAMES or name.startswith("__fma"):
            hits.append(line.strip())
    return rc, hits, out


def check_libcall(ctx, probe):
    obj = os.path.join(ctx.out, probe + ".o")
    elf = os.path.join(ctx.out, probe + ".elf")
    for what, path, undef in (("object", obj, True), ("image", elf, False)):
        rc, hits, out = libcall_symbols(ctx, path, undef)
        if rc != 0:
            ctx.add("%s %s symbol scan" % (probe, what), "readable",
                    "llvm-nm rc=%d" % rc, False, detail=out[-300:])
            continue
        ctx.add("%s %s: no fma libcall symbol" % (probe, what), [], hits,
                not hits, detail="fma/fmaf/fmal must lower to fofma/ftfma")
    # The call instruction itself: a relocation to fma/fmaf/fmal would mean the
    # fused instruction was not selected (nm alone cannot see the target of an
    # intra-object call).
    rc, out, _ = run([ctx.args.objdump, "-dr", "--no-show-raw-insn", obj])
    hits = []
    for line in out.splitlines():
        toks = line.split()
        if not toks or not toks[0].startswith("R_"):
            continue
        if toks[-1] in LIBCALL_NAMES or toks[-1].startswith("__fma"):
            hits.append(line.strip())
    ctx.add("%s object: no relocation to fma/fmaf/fmal" % probe, [], hits,
            rc == 0 and not hits,
            detail="a call target would appear as R_* fma")


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


def judge_edges_records(records, mutation=None):
    """Judge a list of OBS records; returns (red, total)."""
    red = total = 0
    for rec in records:
        total += 1
        if not all(c["ok"] for c in oracle.judge_obs(rec, mutation)):
            red += 1
    return red, total


def inject_oracle(ctx):
    disc = [r for r in ctx.obs if r["group"] == "disc"]
    red, total = judge_edges_records(disc, "two_step")
    ctx.add("inject oracle (expect the two-step value on disc) -> red",
            "all %d red" % total, "%d/%d red" % (red, total),
            total > 0 and red == total,
            detail="models a wrong two-step oracle")
    snan = [r for r in ctx.obs if r["group"] == "special"
            and r["label"] in ("snan_a", "snan_c")]
    red2, total2 = judge_edges_records(snan, "flags_zero")
    ctx.add("inject oracle (sNaN NV expected 0) -> red",
            "all %d red" % total2, "%d/%d red" % (red2, total2),
            total2 > 0 and red2 == total2)


def inject_c_side(ctx):
    """Replace the C `fma`/`fmaf` call path by `a*b+c` (task's first item)."""
    inj = os.path.join(ctx.out, "inject-c")
    shutil.rmtree(inj, ignore_errors=True)
    shutil.copytree(PROBE_DIR, inj)
    anchor = (
        "\tif (fmt[1] == 't')\n"
        "\t\treturn fma_bits_f(fmaf(fma_val_f(a), fma_val_f(b),\n"
        "\t\t\t\t       fma_val_f(c)));\n"
        "\treturn fma_bits_d(fma(fma_val_d(a), fma_val_d(b), fma_val_d(c)));\n")
    degraded = (
        "\tif (fmt[1] == 't') {\n"
        "\t\tvolatile float prod = fma_val_f(a) * fma_val_f(b);\n"
        "\t\treturn fma_bits_f(prod + fma_val_f(c));\n"
        "\t} else {\n"
        "\t\tvolatile double prod = fma_val_d(a) * fma_val_d(b);\n"
        "\t\treturn fma_bits_d(prod + fma_val_d(c));\n"
        "\t}\n")
    before, after = _mutate(os.path.join(inj, "fma_common.h"),
                            os.path.join(inj, "fma_common.h"),
                            anchor, degraded)
    if before == after:
        return ctx.add("inject C path: header changed", "different", "same",
                       False)
    obj, elf, rc, log = compile_probe(ctx, "fma_edges",
                                      os.path.join(inj, "fma_edges.c"),
                                      tag="-inject-c")
    if rc != 0:
        return ctx.add("inject C path: build", 0, rc, False,
                       detail=log[-500:])
    rc, out, _ = run_elf(ctx, elf)
    parsed = oracle.parse(out)
    disc = [r for r in parsed["obs"] if r["group"] == "disc"]
    red, total = judge_edges_records(disc)
    ctx.add("inject C path (fma -> a*b+c) -> discriminators red",
            "all %d red" % total, "%d/%d red" % (red, total),
            total > 0 and red == total, detail="guest rc=%d" % rc)


def inject_lowering(ctx):
    """Degrade `llvm.fma` to fmul+fadd at the instruction-selection boundary.

    This is the IR that instruction selection consumes: rewriting the fused
    intrinsic into two separate operations is exactly the lowering regression
    (``ISD::FMA`` expanded to ``FMUL``+``FADD``) that the discriminators must
    catch.  The fused inline asm in the probe is untouched (it *is* the
    instruction); the C/intrinsic path is what changes.
    """
    ir_dir = os.path.join(ctx.out, "inject-ir")
    os.makedirs(ir_dir, exist_ok=True)
    src = os.path.join(PROBE_DIR, "fma_edges.c")
    ir = os.path.join(ir_dir, "fma_edges.ll")
    cmd = ([ctx.args.clang, "--target=dadao-unknown-elf"] + compile_flags(ctx)
           + ["-std=c11", "-" + ctx.args.opt, "-S", "-emit-llvm", src,
              "-o", ir])
    rc, out, _ = run(cmd)
    if rc != 0:
        return ctx.add("inject lowering: emit LLVM IR", 0, rc, False,
                       detail=out[-500:])
    with open(ir) as f:
        text = f.read()
    count = [0]

    def repl(m):
        count[0] += 1
        ind, res, ty, _bits, x, y, z = m.groups()
        mul = "%%fma.mul.%d" % count[0]
        return ("%s%s = fmul %s %s, %s\n%s%s = fadd %s %s, %s"
                % (ind, mul, ty, x, y, ind, res, ty, mul, z))

    degraded = FMA_IR_RE.sub(repl, text)
    if count[0] == 0:
        return ctx.add("inject lowering: llvm.fma rewritten", "> 0", 0, False,
                       detail="no llvm.fma call found in the IR")
    path = os.path.join(ir_dir, "fma_edges-degraded.ll")
    with open(path, "w") as f:
        f.write(degraded)
    obj = os.path.join(ir_dir, "fma_edges-degraded.o")
    elf = os.path.join(ir_dir, "fma_edges-degraded.elf")
    rc, out, _ = run([ctx.args.clang, "--target=dadao-unknown-elf", "-" +
                      ctx.args.opt, "-c", path, "-o", obj])
    if rc != 0:
        return ctx.add("inject lowering: compile degraded IR", 0, rc, False,
                       detail=out[-500:])
    rc, out, _ = run([ctx.args.ldlld, "-o", elf,
                      os.path.join(ctx.args.musl, "lib", "crt1.o"), obj,
                      "--start-group", os.path.join(ctx.args.musl, "lib",
                                                    "libc.a"), ctx.rtlib,
                      "--end-group"])
    if rc != 0:
        return ctx.add("inject lowering: link degraded IR", 0, rc, False,
                       detail=out[-500:])
    rc, out, _ = run_elf(ctx, elf)
    parsed = oracle.parse(out)
    disc = [r for r in parsed["obs"] if r["group"] == "disc"]
    red, total = judge_edges_records(disc)
    blocks = disasm_blocks(ctx, obj)
    body = blocks.get("sel_fma", Counter())
    ctx.add("inject lowering: sel_fma lost its fused instruction",
            "fofma+ftfma = 0", "fofma=%d ftfma=%d fomul=%d foadd=%d"
            % (body.get("fofma", 0), body.get("ftfma", 0),
               body.get("fomul", 0), body.get("foadd", 0)),
            body.get("fofma", 0) == 0 and body.get("ftfma", 0) == 0
            and body.get("fomul", 0) > 0 and body.get("foadd", 0) > 0,
            detail="%d llvm.fma calls degraded to fmul+fadd" % count[0])
    ctx.add("inject lowering (fmul+fadd) -> discriminators red",
            "all %d red" % total, "%d/%d red" % (red, total),
            total > 0 and red == total, detail="guest rc=%d" % rc)


def injection_mode(ctx):
    inject_oracle(ctx)
    inject_c_side(ctx)
    inject_lowering(ctx)
    # The repository sources must be untouched by any injection.
    for name in SOURCES:
        path = os.path.join(PROBE_DIR, name)
        ctx.add("inject source %s unchanged" % name, ctx.src_md5[name],
                md5(path), md5(path) == ctx.src_md5[name], detail="md5")
    # The pristine build judged above must stay green.
    fails = [c for c in ctx.checks
             if not c["ok"] and not c["name"].startswith("inject")
             and not c["name"].startswith("objdump")
             and not c["name"].startswith("edges/inject")]
    ctx.add("inject: original build green after injections", "no fail",
            "see run checks", not fails)


# ── main ──────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--opt", choices=("O0", "O2"), required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--objdump", default=DEFAULT_OBJDUMP)
    ap.add_argument("--nm", default=DEFAULT_NM)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--inject", action="store_true",
                    help="injection self-test (reachable FAIL)")
    args = ap.parse_args(argv)

    ctx = Ctx(args)
    ctx.src_md5 = {}
    for name in SOURCES:
        path = os.path.join(PROBE_DIR, name)
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
    }

    t0 = time.time()
    for probe in PROBES:
        obj, elf, rc, log = compile_probe(ctx, probe,
                                          os.path.join(PROBE_DIR,
                                                       probe + ".c"))
        ctx.add("build %s" % probe, 0, rc, rc == 0, detail=log[-600:])
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
        ctx.runs.append({"probe": probe, "rc": rc, "seconds": secs})
        parsed_all[probe] = out

    parsed = oracle.parse(parsed_all.get("fma_edges", ""))
    judge_edges(ctx, parsed)
    check_coverage(ctx, parsed)
    for probe in ("fma_dot", "fma_horner"):
        judge_alg(ctx, probe, oracle.parse(parsed_all.get(probe, "")))
    # coverage over the raw ALG records of both probes
    raw_alg = []
    for probe in ("fma_dot", "fma_horner"):
        raw_alg.extend(oracle.parse(parsed_all.get(probe, ""))["alg"])
    check_alg_coverage(ctx, raw_alg)

    check_asm(ctx)
    for probe in PROBES:
        check_libcall(ctx, probe)

    if args.inject:
        injection_mode(ctx)

    counts = {"pass": 0, "fail": 0}
    for c in ctx.checks:
        if c["ok"]:
            counts["pass"] += 1
        else:
            counts["fail"] += 1
    result = "PASS" if counts["fail"] == 0 else "FAIL"
    doc = {
        "task": "TESTCASES-058t",
        "opt": args.opt,
        "env": env,
        "builds": ctx.builds,
        "runs": ctx.runs,
        "checks": ctx.checks,
        "notes": ctx.notes,
        "summary": {"total": len(ctx.checks), "pass": counts["pass"],
                    "fail": counts["fail"],
                    "observations": len(ctx.obs), "algorithm": len(raw_alg),
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
    print("%s (%s): total=%d pass=%d fail=%d observations=%d algorithm=%d "
          "compile=%.1fs run=%.1fs"
          % (result, args.opt, len(ctx.checks), counts["pass"],
             counts["fail"], len(ctx.obs), len(raw_alg), build_secs,
             run_secs))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
