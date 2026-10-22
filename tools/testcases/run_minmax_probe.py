#!/usr/bin/env python3
"""DADAO-v5 min/max integration driver (TESTCASES-059t).

Builds the three probes in ``tests/minmax/`` (one optimisation level per
invocation), runs them under ``qemu-dadao`` (user mode, static musl) and
judges every observation with the independent oracle in ``oracle_minmax.py``.

What this driver does NOT do
----------------------------
* It never invents an expectation: the C probes print raw observations only
  (``a``/``b``/``c``/``out``/``pre``/``post`` bit patterns); every expected
  value and flag comes from ``oracle_minmax.py``, which derives it from
  ``spec/SimRISC-07 §2.4`` + ``contract-fp.md §19`` with exact
  ``fractions.Fraction`` arithmetic.
* It never reads a result back from QEMU/LLVM to build an expectation: the
  disassembly checks only assert *which* instruction the backend selected
  (``fomin``/``fomax``/``ftmin``/``ftmax``) and that no libcall is present.
* It never turns a silent skip into a pass: missing observation groups,
  missing symbols and vacuous counts are FAILs.

Checks per probe
----------------
minmax_matrix.c  the full boundary matrix (ordered both ways, equal,
                  ±0 four combinations, qNaN both orders, -qNaN, sNaN both
                  orders, two NaNs in four combinations, ±Inf, subnormals)
                  for ft/fo x min/max.  Every cell asserts VALUE and FLAGS
                  (NV/NX) as two separate checks.
minmax_clamp.c   a 1k-iteration clamp loop over boundary + random inputs
                  (``min(max(x,lo),hi)`` with C fmin/fmax), a 4x4 element-wise
                  min/max matrix with a NaN row and a ±0/Inf row, and an
                  integer min/max control on exactly representable integers.
minmax_c23.c     C23 minimum/maximum (NaN propagating, ``llvm.minimum``) vs
                  ``fminimum_num`` (minimumNumber) vs C ``fmin``/``fmax``
                  (llvm.minnum), plus per-symbol disassembly + ``llc`` counts:
                  c23 = one fomin/fomax + a NaN select, num/cmap = exactly one
                  minmax instruction, and ZERO calls (no libcall) everywhere.

Usage
-----
  run_minmax_probe.py --opt O0 --json-out /tmp/.../o0.json
  run_minmax_probe.py --opt O2 --json-out /tmp/.../o2.json
  run_minmax_probe.py --inject --json-out ...   # reachable-FAIL proof

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
# MINMAX_ORACLE_DIR lets --inject run the same driver against a temporary,
# deliberately wrong expectation table (expected-side injection) without ever
# touching the repository file.
_ORACLE_DIR = os.environ.get("MINMAX_ORACLE_DIR") or HERE
sys.path.insert(0, _ORACLE_DIR)
import oracle_minmax as oracle  # noqa: E402

TOOLCHAIN_BIN = os.path.join(".dadao", "cross-toolchain", "bin")
DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LLC = os.path.join(TOOLCHAIN_BIN, "llc")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_NM = os.path.join(TOOLCHAIN_BIN, "llvm-nm")
DEFAULT_OBJDUMP = os.path.join(TOOLCHAIN_BIN, "llvm-objdump")
DEFAULT_MUSL = os.path.join(".work", "source", "musl")
DEFAULT_WORK_DIR = os.path.join("/tmp", "opencode", "TESTCASES-059t",
                                "probe-work")
PROBE_DIR = os.path.join("tests", "minmax")
PROBES = ("minmax_matrix", "minmax_clamp", "minmax_c23")
CLAMP_N = 500                  # per format -> 1000 clamp iterations
SOURCES = tuple(p + ".c" for p in PROBES) + ("minmax_common.h",)

LIBCALL_NAMES = {
    "fmin", "fmax", "fminf", "fmaxf", "fminl", "fmaxl",
    "fminimum", "fmaximum", "fminimumf", "fmaximumf",
    "fminimuml", "fmaximuml",
}

# Per-symbol backend contract (LLVM-124t): exactly one minmax instruction;
# the C23 (NaN propagating) forms additionally need a NaN select (cs.z).
SYMBOLS = {
    "mm_c23_minimum_f64": ("fomin", True),
    "mm_c23_maximum_f64": ("fomax", True),
    "mm_c23_minimum_f32": ("ftmin", True),
    "mm_c23_maximum_f32": ("ftmax", True),
    "mm_c23_minimum_num_f64": ("fomin", False),
    "mm_c23_maximum_num_f64": ("fomax", False),
    "mm_c23_minimum_num_f32": ("ftmin", False),
    "mm_c23_maximum_num_f32": ("ftmax", False),
    "mm_c_fmin": ("fomin", False),
    "mm_c_fmax": ("fomax", False),
    "mm_c_fminf": ("ftmin", False),
    "mm_c_fmaxf": ("ftmax", False),
}

CLAMP_SYMBOLS = {
    "mm_clamp_f64": ("fomax", "fomin"),
    "mm_clamp_f32": ("ftmax", "ftmin"),
}

OBJ_RE = re.compile(r"^[0-9a-f]+\s+<([^>]+)>:\s*$")


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
    if st.st_size <= (64 << 20):
        ident["md5"] = md5(path)
    else:
        ident["md5"] = None
        ident["note"] = "skipped for size; size+mtime+path identify it"
    return ident


def run(cmd, timeout=None, env=None):
    """Run a command, never raise: (rc, stdout+stderr, seconds)."""
    t0 = time.time()
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout,
                           text=True, errors="replace", env=env)
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


def compile_probe(ctx, probe, src=None, tag="", out_dir=None, extra=()):
    src = src or os.path.join(PROBE_DIR, probe + ".c")
    out_dir = out_dir or ctx.out
    obj = os.path.join(out_dir, "%s%s.o" % (probe, tag))
    elf = os.path.join(out_dir, "%s%s.elf" % (probe, tag))
    cmd = ([ctx.args.clang, "--target=dadao-unknown-elf"]
           + compile_flags(ctx)
           + ["-std=c2x", "-" + ctx.args.opt, "-Wall"]
           + list(extra) + ["-c", src, "-o", obj])
    rc, out, secs = run(cmd)
    ctx.builds.append({"probe": probe + tag, "step": "compile", "rc": rc,
                       "cmd": " ".join(cmd), "log": out[-4000:]})
    if rc != 0:
        return obj, elf, rc, out
    link = [ctx.args.ldlld, "-o", elf,
            os.path.join(ctx.args.musl, "lib", "crt1.o"), obj,
            "--start-group", os.path.join(ctx.args.musl, "lib", "libc.a"),
            ctx.rtlib, "--end-group"]
    rc2, out2, _ = run(link)
    ctx.builds.append({"probe": probe + tag, "step": "link", "rc": rc2,
                       "cmd": " ".join(link), "log": out2[-4000:]})
    return obj, elf, rc if rc != 0 else rc2, out + out2


def run_elf(ctx, elf, timeout=120):
    return run([ctx.args.qemu, elf], timeout=timeout)


# ── judgement helpers ─────────────────────────────────────────────────────
def judge_probe(ctx, probe, text):
    parsed = oracle.parse(text)
    ctx.add("%s: no unparsed output" % probe, 0, len(parsed["junk"]),
            not parsed["junk"], detail="; ".join(parsed["junk"][:3]))
    ctx.add("%s: INIT line present" % probe, "1", 1 if parsed["init"] else 0,
            parsed["init"] is not None)
    ctx.add("%s: observations present" % probe, "> 0",
            len(parsed["obs"]), len(parsed["obs"]) > 0)
    ctx.add("%s: rf0 restore line present" % probe, "1",
            len(parsed["restore"]), len(parsed["restore"]) == 1)
    for c in [oracle.judge_init(parsed["init"])]:
        ctx.add(c["name"], c["expected"], c["actual"], c["ok"],
                c.get("detail", ""))
    for rec in parsed["obs"]:
        for c in oracle.judge_obs(rec):
            ctx.add(c["name"], c["expected"], c["actual"], c["ok"],
                    c.get("detail", ""))
    for rec in parsed["restore"]:
        c = oracle.judge_restore(rec)
        ctx.add(c["name"], c["expected"], c["actual"], c["ok"],
                c.get("detail", ""))
    return parsed


def group(parsed, name):
    return [r for r in parsed["obs"] if r["group"] == name]


def check_matrix_coverage(ctx, probe, parsed):
    rows = group(parsed, "matrix")
    for fmt in oracle.FMT:
        for op in ("min", "max"):
            labels = {r["label"] for r in rows
                      if r["fmt"] == fmt and r["op"] == op}
            ctx.add("%s: matrix %s %s pairs covered" % (probe, fmt, op),
                    "%d pairs" % len(oracle.PAIR_NAMES), len(labels),
                    labels == set(oracle.PAIR_NAMES),
                    detail="missing %s"
                           % sorted(set(oracle.PAIR_NAMES) - labels))
    ctx.add("%s: matrix rows = formats x ops x pairs" % probe,
            len(oracle.FMT) * 2 * len(oracle.PAIR_NAMES), len(rows),
            len(rows) == len(oracle.FMT) * 2 * len(oracle.PAIR_NAMES))


def check_clamp_coverage(ctx, probe, parsed):
    rows = group(parsed, "clamp")
    for fmt in oracle.FMT:
        mine = [r for r in rows if r["fmt"] == fmt]
        ctx.add("%s: clamp iterations (%s)" % (probe, fmt),
                "== declared n", len(mine),
                len(mine) == CLAMP_N)
        # boundary coverage derived from the observed bit patterns
        specials = {"qnan": 0, "snan": 0, "zero": 0, "inf": 0}
        for r in mine:
            for field in ("a", "b", "c"):
                kind = oracle.decode(int(r[field], 16), fmt)["kind"]
                if kind in specials:
                    specials[kind] += 1
        for name in specials:
            ctx.add("%s: clamp %s inputs seen (%s)" % (probe, name, fmt),
                    "> 0", specials[name], specials[name] > 0)
    mat = group(parsed, "mat4")
    for fmt in oracle.FMT:
        for op in ("min", "max"):
            cells = {(r["label"]) for r in mat
                     if r["fmt"] == fmt and r["op"] == op}
            want = {"r%dc%d" % (r, c) for r in range(4) for c in range(4)}
            ctx.add("%s: mat4 %s %s cells" % (probe, fmt, op), 16,
                    len(cells), cells == want)
    # operand table check: a/b must match MAT4/MAT4_B (no mistyped literal)
    idx = {"ft": 0, "fo": 1}
    bad = []
    for r in mat:
        rr, cc = int(r["label"][1]), int(r["label"][3])
        f = idx[r["fmt"]]
        if (int(r["a"], 16) != oracle.MAT4[r["fmt"]][rr][cc]
                or int(r["b"], 16) != oracle.MAT4_B[r["fmt"]][rr][cc]):
            bad.append(r["label"])
    ctx.add("%s: mat4 operands == table" % probe, 0, len(bad), not bad,
            detail="; ".join(bad[:4]))
    ints = group(parsed, "intcmp")
    for fmt in oracle.FMT:
        mine = [r for r in ints if r["fmt"] == fmt]
        xs = {int(r["xi"]) for r in mine}
        ctx.add("%s: int clamp xs (%s)" % (probe, fmt), 43, len(xs),
                xs == set(range(-21, 22)))
        los = {int(r["loi"]) for r in mine}
        his = {int(r["hii"]) for r in mine}
        ctx.add("%s: int clamp lo/hi (%s)" % (probe, fmt), "-5/5",
                "%s/%s" % (sorted(los), sorted(his)),
                los == {-5} and his == {5})


def check_c23_coverage(ctx, probe, parsed):
    rows = group(parsed, "c23")
    num = group(parsed, "num")
    cmap = group(parsed, "cmap")
    for name, rows_ in (("c23", rows), ("num", num), ("cmap", cmap)):
        for fmt in oracle.FMT:
            frows = [r for r in rows_ if r["fmt"] == fmt]
            for op in ("min", "max"):
                labels = {r["label"] for r in frows if r["op"] == op}
                ctx.add("%s: %s %s %s pairs" % (probe, name, fmt, op),
                        len(oracle.PAIR_NAMES), len(labels),
                        labels == set(oracle.PAIR_NAMES),
                        detail="missing %s"
                               % sorted(set(oracle.PAIR_NAMES) - labels))
    ctx.add("%s: c23/num/cmap rows" % probe,
            len(oracle.FMT) * 6 * len(oracle.PAIR_NAMES),
            len(rows) + len(num) + len(cmap),
            len(rows) + len(num) + len(cmap)
            == len(oracle.FMT) * 6 * len(oracle.PAIR_NAMES))


# ── disassembly / libcall checks ──────────────────────────────────────────
def disasm_symbols(ctx, obj, tool=None):
    tool = tool or ctx.args.objdump
    rc, out, _ = run([tool, "-d", "--no-show-raw-insn", obj])
    ctx.add("objdump %s" % os.path.basename(obj), 0, rc, rc == 0,
            detail=out[-400:])
    blocks, cur = {}, None
    for line in out.splitlines():
        m = OBJ_RE.match(line.strip())
        if m:
            cur = m.group(1)
            blocks[cur] = []
        elif cur is not None:
            blocks[cur].append(line)
    return blocks, out


def undefined_symbols(ctx, obj):
    rc, out, _ = run([ctx.args.nm, "-u", obj])
    ctx.add("nm -u %s" % os.path.basename(obj), 0, rc, rc == 0,
            detail=out[-400:])
    syms = set()
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "U" and len(parts) > 1:
            syms.add(parts[1])
        elif len(parts) == 2 and parts[0] == "U":
            syms.add(parts[1])
    return syms


def libcall_hits(syms):
    return sorted(syms & LIBCALL_NAMES)


def check_libcalls(ctx, probe, obj):
    syms = undefined_symbols(ctx, obj)
    hits = libcall_hits(syms)
    ctx.add("%s: no min/max libcall (nm -u)" % probe, "0", len(hits),
            not hits, detail=", ".join(hits))
    return not hits


def block_of(blocks, sym):
    body = blocks.get(sym)
    if body is None:
        return None
    return "\n".join(body)


def count_mnemonic(text, mnem):
    return len(re.findall(r"\b%s\b" % re.escape(mnem), text))


def check_c23_symbols(ctx, probe, obj):
    blocks, _ = disasm_symbols(ctx, obj)
    total_calls = 0
    total_minmax = 0
    for sym, (mnem, need_select) in sorted(SYMBOLS.items()):
        text = block_of(blocks, sym)
        if text is None:
            ctx.add("%s: symbol %s present" % (probe, sym), "present",
                    "missing", False)
            continue
        n = count_mnemonic(text, mnem)
        calls = count_mnemonic(text, "call")
        select = count_mnemonic(text, "cs.z")
        total_calls += calls
        total_minmax += n
        ok = n == 1 and calls == 0 and (select >= 1 if need_select else True)
        ctx.add("%s: %s -> 1 x %s%s, 0 calls" % (probe, sym, mnem,
                                                 ", >=1 cs.z" if need_select
                                                 else ""),
                "1 x %s, 0 calls" % mnem,
                "%d x %s, %d calls, %d cs.z" % (n, mnem, calls, select), ok)
    ctx.add("%s: every c23/num/cmap symbol has a body" % probe,
            len(SYMBOLS), len([s for s in SYMBOLS if s in blocks]),
            len([s for s in SYMBOLS if s in blocks]) == len(SYMBOLS))
    ctx.add("%s: total calls across the 12 symbols" % probe, 0, total_calls,
            total_calls == 0)
    ctx.add("%s: total minmax instructions across the 12 symbols" % probe,
            len(SYMBOLS), total_minmax, total_minmax == len(SYMBOLS))


def check_clamp_symbols(ctx, probe, obj):
    blocks, _ = disasm_symbols(ctx, obj)
    for sym, (first, second) in sorted(CLAMP_SYMBOLS.items()):
        text = block_of(blocks, sym)
        if text is None:
            ctx.add("%s: symbol %s present" % (probe, sym), "present",
                    "missing", False)
            continue
        n1, n2 = count_mnemonic(text, first), count_mnemonic(text, second)
        calls = count_mnemonic(text, "call")
        ctx.add("%s: %s -> 1 x %s + 1 x %s, 0 calls"
                % (probe, sym, first, second), "1+1, 0 calls",
                "%d+%d, %d calls" % (n1, n2, calls),
                n1 == 1 and n2 == 1 and calls == 0)


def check_llc_symbols(ctx, probe, llc_src):
    """Independent llc run: compile the C23 probe to IR, lower with the
    install-root llc and count instructions per symbol in its asm text."""
    asm = os.path.join(ctx.out, "%s.llc.s" % probe)
    cmd = [ctx.args.llc, "-mtriple=dadao-unknown-elf", llc_src, "-o", asm]
    rc, out, _ = run(cmd)
    ctx.add("%s: llc run" % probe, 0, rc, rc == 0, detail=out[-600:])
    if rc != 0:
        return
    with open(asm) as f:
        text = f.read()
    total_calls = 0
    checked = 0
    for sym, (mnem, need_select) in sorted(SYMBOLS.items()):
        start = None
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^%s:\s" % re.escape(sym), line):
                start = i
                break
        if start is None:
            ctx.add("%s: llc symbol %s present" % (probe, sym), "present",
                    "missing", False)
            continue
        body = []
        for line in lines[start + 1:]:
            if re.match(r"^\.Lfunc_end", line) or re.match(
                    r"^\S+:\s+@@ @", line):
                break
            body.append(line)
        body_text = "\n".join(body)
        n = count_mnemonic(body_text, mnem)
        calls = count_mnemonic(body_text, "call")
        select = count_mnemonic(body_text, "cs.z")
        total_calls += calls
        checked += 1
        ok = n == 1 and calls == 0 and (select >= 1 if need_select else True)
        ctx.add("%s: llc %s -> 1 x %s, 0 calls" % (probe, sym, mnem),
                "1 x %s, 0 calls" % mnem,
                "%d x %s, %d calls, %d cs.z" % (n, mnem, calls, select), ok)
    ctx.add("%s: llc symbols checked" % probe, len(SYMBOLS), checked,
            checked == len(SYMBOLS))
    ctx.add("%s: llc total calls" % probe, 0, total_calls, total_calls == 0)


def emit_ir(ctx, probe, src):
    ll = os.path.join(ctx.out, "%s.ll" % probe)
    cmd = ([ctx.args.clang, "--target=dadao-unknown-elf"]
           + compile_flags(ctx)
           + ["-std=c2x", "-" + ctx.args.opt, "-S", "-emit-llvm",
              src, "-o", ll])
    rc, out, _ = run(cmd)
    ctx.add("%s: emit-llvm" % probe, 0, rc, rc == 0, detail=out[-600:])
    return ll if rc == 0 else None


# ── one probe ─────────────────────────────────────────────────────────────
def check_probe(ctx, probe):
    obj, elf, rc, log = compile_probe(ctx, probe)
    ctx.add("build %s" % probe, 0, rc, rc == 0, detail=log[-800:])
    if rc != 0:
        return None, None
    rc, out, secs = run_elf(ctx, elf)
    ctx.note("runtime %s" % probe, "%.2fs" % secs)
    ctx.add("run %s exit" % probe, 0, rc, rc == 0, detail="%.2fs" % secs)
    parsed = judge_probe(ctx, probe, out)
    if probe == "minmax_matrix":
        check_matrix_coverage(ctx, probe, parsed)
    elif probe == "minmax_clamp":
        check_clamp_coverage(ctx, probe, parsed)
        check_clamp_symbols(ctx, probe, obj)
    elif probe == "minmax_c23":
        check_c23_coverage(ctx, probe, parsed)
        check_libcalls(ctx, probe, obj)
        check_c23_symbols(ctx, probe, obj)
        ll = emit_ir(ctx, probe, os.path.join(PROBE_DIR, probe + ".c"))
        if ll:
            check_llc_symbols(ctx, probe, ll)
    return obj, parsed


# ── injections (reachable-FAIL proof) ────────────────────────────────────
def _copy_probe_dir(dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for name in SOURCES:
        shutil.copyfile(os.path.join(PROBE_DIR, name),
                        os.path.join(dst, name))


def _mutate(path, pairs, replace_all=False):
    with open(path) as f:
        text = f.read()
    for old, new in pairs:
        count = text.count(old)
        if count == 0 or (count != 1 and not replace_all):
            raise RuntimeError("injection anchor %r occurs %d times in %s"
                               % (old[:60], count, path))
        text = text.replace(old, new)
    with open(path, "w") as f:
        f.write(text)


def _copy_oracle(dst, pairs):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    src = os.path.join(_ORACLE_DIR, "oracle_minmax.py")
    shutil.copyfile(src, os.path.join(dst, "oracle_minmax.py"))
    _mutate(os.path.join(dst, "oracle_minmax.py"), pairs)
    return dst


def _run_driver_with_oracle(ctx, oracle_dir, tag):
    """Run this driver in a subprocess against a temp oracle copy."""
    json_out = os.path.join(ctx.out, "inject-%s.json" % tag)
    env = dict(os.environ, MINMAX_ORACLE_DIR=oracle_dir)
    cmd = [sys.executable, os.path.abspath(__file__),
           "--opt", ctx.args.opt, "--json-out", json_out,
           "--work-dir", os.path.join(ctx.work, "inject-" + tag),
           "--clang", ctx.args.clang, "--ldlld", ctx.args.ldlld,
           "--qemu", ctx.args.qemu, "--nm", ctx.args.nm,
           "--objdump", ctx.args.objdump, "--llc", ctx.args.llc,
           "--musl", ctx.args.musl]
    rc, out, _ = run(cmd, timeout=600, env=env)
    doc = None
    if os.path.exists(json_out):
        with open(json_out) as f:
            doc = json.load(f)
    return rc, doc, out


def injection_mode(ctx):
    # the shipped code path must be green before the proof
    obj, _ = check_probe(ctx, "minmax_matrix")
    green = not [c for c in ctx.checks if not c["ok"]]
    ctx.add("inject: shipped matrix green before injections", "no FAIL",
            "%d FAIL" % len([c for c in ctx.checks if not c["ok"]]), green)

    src_md5 = {n: md5(os.path.join(PROBE_DIR, n)) for n in SOURCES}

    # ── injection 1: sNaN NV expected as 0 (expected-side) ──
    d1 = _copy_oracle(os.path.join(ctx.out, "oracle-nvn"),
                      [('''def minmax_number(a, b, fmt, ismax):
    """Hardware minimumNumber/maximumNumber (spec/SimRISC-07 §2.4)."""
    da, db = decode(a, fmt), decode(b, fmt)
    flags = FLAG_NV if ("snan" in (da["kind"], db["kind"])) else 0''',
                        '''def minmax_number(a, b, fmt, ismax):
    """Injected: sNaN must NOT raise NV (wrong)."""
    da, db = decode(a, fmt), decode(b, fmt)
    flags = 0''')])
    changed = md5(os.path.join(d1, "oracle_minmax.py")) != md5(
        os.path.join(HERE, "oracle_minmax.py"))
    ctx.add("inject 1: oracle copy really changed", "different md5",
            "different" if changed else "same", changed)
    rc, doc, out = _run_driver_with_oracle(ctx, d1, "nvn")
    reds = [c for c in (doc or {}).get("checks", []) if not c["ok"]]
    snan = [c for c in reds if c["name"].startswith("flags ")
            and "snan" in c["name"]]
    ctx.add("inject 1 (sNaN NV expected 0): sNaN flag cells go red",
            "rc=1 and >=1 sNaN flag cell red",
            "rc=%d, %d red, %d sNaN-flag red" % (rc, len(reds), len(snan)),
            rc == 1 and len(snan) >= 1,
            detail="; ".join(c["name"] for c in snan[:3]))

    # ── injection 2: one ±0 expectation swapped (expected-side) ──
    d2 = _copy_oracle(os.path.join(ctx.out, "oracle-zero"),
                      [('''    cmp = numeric_cmp(a, b, fmt)                  # rules 1-3, 6
    if ismax:
        return (a if cmp >= 0 else b), 0
    return (a if cmp <= 0 else b), 0''',
                        '''    cmp = numeric_cmp(a, b, fmt)                  # injected: swap zero sign
    res = (a if (cmp >= 0 if ismax else cmp <= 0) else b)
    if (res & ((1 << _f(fmt)["sign"]) - 1)) == 0:
        res ^= 1 << _f(fmt)["sign"]
    return res, 0''')])
    changed = md5(os.path.join(d2, "oracle_minmax.py")) != md5(
        os.path.join(HERE, "oracle_minmax.py"))
    ctx.add("inject 2: oracle copy really changed", "different md5",
            "different" if changed else "same", changed)
    rc, doc, out = _run_driver_with_oracle(ctx, d2, "zero")
    reds = [c for c in (doc or {}).get("checks", []) if not c["ok"]]
    zero = [c for c in reds if c["name"].startswith("value ")
            and "zeros_" in c["name"]]
    ctx.add("inject 2 (±0 expectation swapped): zero cells go red",
            "rc=1 and >=1 zero value cell red",
            "rc=%d, %d red, %d zero-value red" % (rc, len(reds), len(zero)),
            rc == 1 and len(zero) >= 1,
            detail="; ".join(c["name"] for c in zero[:3]))

    # ── injection 3: make the C23 path emit libcalls ──
    d3 = os.path.join(ctx.out, "inject-libcall")
    _copy_probe_dir(d3)
    _mutate(os.path.join(d3, "minmax_c23.c"), [
        ("/* ── exported functions (disassembled by the driver) ── */",
         "extern double fminimum(double, double);\n"
         "extern double fmaximum(double, double);\n"
         "extern float fminimumf(float, float);\n"
         "extern float fmaximumf(float, float);\n"
         "/* ── exported functions (disassembled by the driver) ── */"),
        ("__builtin_elementwise_minimum(a, b)", "fminimum(a, b)"),
        ("__builtin_elementwise_maximum(a, b)", "fmaximum(a, b)"),
    ], replace_all=True)
    # the two f32 forms use the same spellings; make them call the f32 names
    _mutate(os.path.join(d3, "minmax_c23.c"), [
        ("float mm_c23_minimum_f32(float a, float b)\n{\n\treturn fminimum(a, b);",
         "float mm_c23_minimum_f32(float a, float b)\n{\n\treturn fminimumf(a, b);"),
        ("float mm_c23_maximum_f32(float a, float b)\n{\n\treturn fmaximum(a, b);",
         "float mm_c23_maximum_f32(float a, float b)\n{\n\treturn fmaximumf(a, b);"),
    ])
    obj = os.path.join(d3, "minmax_c23-inject.o")
    cmd = ([ctx.args.clang, "--target=dadao-unknown-elf"] + compile_flags(ctx)
           + ["-std=c2x", "-" + ctx.args.opt, "-fno-builtin", "-c",
              os.path.join(d3, "minmax_c23.c"), "-o", obj])
    rc, out, _ = run(cmd)
    ctx.add("inject 3: build", 0, rc, rc == 0, detail=out[-800:])
    if rc == 0:
        syms = undefined_symbols(ctx, obj)
        hits = libcall_hits(syms)
        ctx.add("inject 3 (fminimum via libcall): no-libcall check goes red",
                ">=1 libcall", ", ".join(hits) or "none", bool(hits),
                detail="undefined: %s"
                       % ", ".join(sorted(s for s in syms
                                          if "min" in s or "max" in s)))

    # ── the repository sources were never touched ──
    for name in SOURCES:
        now = md5(os.path.join(PROBE_DIR, name))
        ctx.add("inject: repo source %s unchanged" % name, src_md5[name], now,
                now == src_md5[name], detail="md5")

    # ── green again with the shipped sources ──
    obj, elf, rc, log = compile_probe(ctx, "minmax_matrix",
                                      tag="-restored")
    if rc == 0:
        rc, out, _ = run_elf(ctx, elf)
        parsed = oracle.parse(out)
        reds = [c for r in parsed["obs"] for c in oracle.judge_obs(r)
                if not c["ok"]]
        ctx.add("inject: shipped matrix green again", "0 red", len(reds),
                not reds, detail="; ".join(c["name"] for c in reds[:3]))


# ── main ─────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--opt", choices=("O0", "O2"), default="O2")
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--llc", default=DEFAULT_LLC)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--nm", default=DEFAULT_NM)
    ap.add_argument("--objdump", default=DEFAULT_OBJDUMP)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--inject", action="store_true",
                    help="reachable-FAIL self test (three injections)")
    args = ap.parse_args(argv)

    ctx = Ctx(args)
    rc, out, _ = run([args.clang, "--target=dadao-unknown-elf",
                      "-rtlib=compiler-rt", "-print-libgcc-file-name"])
    if rc != 0:
        raise SystemExit("cannot resolve compiler-rt: %s" % out)
    ctx.rtlib = out.strip()

    env = {
        "clang": tool_id(args.clang),
        "llc": tool_id(args.llc),
        "ldlld": tool_id(args.ldlld),
        "qemu": tool_id(args.qemu),
        "nm": tool_id(args.nm),
        "objdump": tool_id(args.objdump),
        "libc_a": tool_id(os.path.join(args.musl, "lib", "libc.a")),
        "crt1": tool_id(os.path.join(args.musl, "lib", "crt1.o")),
        "rtlib": ctx.rtlib,
    }

    if args.inject:
        injection_mode(ctx)
    else:
        for probe in PROBES:
            check_probe(ctx, probe)

    fails = [c for c in ctx.checks if not c["ok"]]
    result = "PASS" if not fails else "FAIL"
    doc = {
        "task": "TESTCASES-059t",
        "opt": args.opt,
        "params": {"inject": bool(args.inject)},
        "env": env,
        "builds": ctx.builds,
        "checks": ctx.checks,
        "notes": ctx.notes,
        "summary": {"total": len(ctx.checks), "pass": len(ctx.checks)
                    - len(fails), "fail": len(fails)},
        "result": result,
    }
    json_out = os.path.abspath(args.json_out)
    os.makedirs(os.path.dirname(json_out), exist_ok=True)
    with open(json_out, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")

    for c in fails:
        print("  FAIL  %s | expected=%s | actual=%s%s"
              % (c["name"], c["expected"], c["actual"],
                 (" | " + c["detail"]) if c["detail"] else ""))
    for n in ctx.notes:
        print("  NOTE  %s = %s" % (n["name"], n["value"]))
    print("%s (-%s%s): total=%d pass=%d fail=%d"
          % (result, args.opt, " inject" if args.inject else "",
             len(ctx.checks), doc["summary"]["pass"], len(fails)))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
