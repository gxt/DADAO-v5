#!/usr/bin/env python3
"""DADAO-v5 roundint integration driver (TESTCASES-060t).

Builds the three probes in ``tests/roundint/`` (one optimisation level per
invocation), runs them under ``qemu-dadao`` (user mode, static musl) and judges
every observation with the independent oracle in ``oracle_rnd.py``.

What this driver does NOT do
----------------------------
* It never invents an expectation: the C probes print raw observations only
  (``in``/``out``/``pre``/``post`` bit patterns); every expected value comes
  from ``oracle_rnd.py``, which derives it from ``spec/SimRISC-07: 取整（roundToIntegral）`` +
  ``contract-fp.md §18`` with exact ``Fraction`` arithmetic.
* It never reads a value back from QEMU/LLVM to build an expectation: the
  disassembly check only asserts *which* instruction the backend selected and
  with which ``immu6`` -- the value expectations stay spec-derived.
* It never turns a silent skip into a pass: a missing observation group is a
  FAIL (structural coverage is checked against the oracle's own tables).

Checks per probe
----------------
rnd_matrix.c  6 modes x (21 inputs) per format, full 64-bit result comparison
              (``±0`` by sign, ``|x| >= 2^p`` unchanged, Inf/NaN), rf0 flags,
              rf0[33:32] read-back, rf0 write mask (read-only bits never move)
              and the C-level mapping of floor/ceil/trunc/round/nearbyint
              (value + per-symbol disassembly: one ftrnd/fornd with the right
              one-hot code, no libcall).
rnd_mode.c    the dynamic code 0x20 under all four rf0[33:32] directions
              (per-case oracle comparison + "the four results are not all
              equal"), the five static directions under the same four rf0
              values (they must be identical: static ignores rf0[33:32]), and
              an rf0 restore assertion after every group.
rnd_flags.c   static directions never set NX; 0x20 sets NX iff the finite
              input is not integral; qNaN never sets NV; sNaN always does;
              Inf sets nothing; DZ/OF/UF never set.

Usage
-----
  run_rnd_probe.py --opt O0 --json-out /tmp/.../o0.json
  run_rnd_probe.py --opt O2 --json-out /tmp/.../o2.json
  run_rnd_probe.py --opt O2 --json-out ... --inject   # reachable-FAIL proof

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
import oracle_rnd as oracle  # noqa: E402

TOOLCHAIN_BIN = os.path.join(".dadao", "cross-toolchain", "bin")
DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_OBJDUMP = os.path.join(TOOLCHAIN_BIN, "llvm-objdump")
DEFAULT_MUSL = os.path.join(".work", "source", "musl")
DEFAULT_WORK_DIR = os.path.join("/tmp", "opencode", "TESTCASES-060t",
                                "probe-work")
PROBE_DIR = os.path.join("tests", "roundint")
PROBES = ("rnd_matrix", "rnd_mode", "rnd_flags")
SOURCES = tuple(p + ".c" for p in PROBES) + ("rnd_common.h",)

# The task fixes these mode-sensitivity inputs (design point B).  They are the
# task's requirement, not a count: the number of cases per group is derived
# from the observations and from oracle.ALL_MODES / oracle.input_table().
MODE_LABELS = ("2.5", "-2.5", "1.5", "-0.5")

OBJ_RE = re.compile(r"^[0-9a-f]+\s+<([^>]+)>:\s*$")
MNEM_RE = re.compile(r"\s(\w+(?:\.\w+)?)\s")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tool_id(path):
    """Cheap but auditable tool identity.

    ``clang``/``lld`` in the install root are multi-GB binaries; hashing them
    costs ~15 s per run (measured), which would dominate this probe.  Large
    files are identified by size + mtime + resolved path, small ones by md5.
    """
    st = os.stat(path)
    ident = {"path": os.path.realpath(path), "size": st.st_size,
             "mtime": int(st.st_mtime)}
    if st.st_size <= (64 << 20):
        ident["md5"] = md5(path)
    else:
        ident["md5"] = None
        ident["note"] = "skipped for size; size+mtime+path identify it"
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


def source_of(probe, root=PROBE_DIR):
    return os.path.join(root, probe + ".c")


def compile_probe(ctx, probe, src, tag="", out_dir=None):
    out_dir = out_dir or ctx.out
    obj = os.path.join(out_dir, "%s%s.o" % (probe, tag))
    elf = os.path.join(out_dir, "%s%s.elf" % (probe, tag))
    cmd = ([ctx.args.clang, "--target=dadao-unknown-elf"]
           + compile_flags(ctx)
           + ["-std=c11", "-" + ctx.args.opt, "-Wall", "-fno-builtin",
              "-c", src, "-o", obj])
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


# ── judgement helpers ─────────────────────────────────────────────────────
def add_judged(ctx, check):
    return ctx.add(check["name"], check["expected"], check["actual"],
                   check["ok"], check.get("detail", ""))


def judge_probe(ctx, probe, text):
    """Judge one probe's full output; returns the parsed observation dict."""
    parsed = oracle.parse(text)
    ctx.add("%s: no unparsed output" % probe, 0, len(parsed["junk"]),
            not parsed["junk"], detail="; ".join(parsed["junk"][:3]))
    add_judged(ctx, oracle.judge_init(parsed["init"]))
    for rec in parsed["obs"]:
        add_judged(ctx, oracle.judge_obs(rec))
    for rec in parsed["restore"]:
        add_judged(ctx, oracle.judge_restore(rec))
    # a probe that printed nothing must not look green
    ctx.add("%s: observations present" % probe, "> 0",
            len(parsed["obs"]), len(parsed["obs"]) > 0)
    ctx.add("%s: rf0 restore lines present" % probe, ">= 1",
            len(parsed["restore"]), len(parsed["restore"]) >= 1)
    return parsed


def group(parsed, name):
    return [r for r in parsed["obs"] if r["group"] == name]


def check_coverage(ctx, probe, parsed, expected_groups=("matrix", "cmap")):
    """Structural coverage derived from the oracle tables, never hard-coded."""
    for name in expected_groups:
        rows = group(parsed, name)
        ctx.add("%s: %s group present" % (probe, name), "> 0", len(rows),
                len(rows) > 0)
    matrix = group(parsed, "matrix")
    if matrix:
        for fmt in oracle.FMT:
            rows = [r for r in matrix if r["fmt"] == fmt]
            modes = {int(r["mode"], 0) for r in rows}
            labels = {r["label"] for r in rows}
            want_modes = set(oracle.ALL_MODES)
            want_labels = {lbl for lbl, _ in oracle.input_bits(fmt)}
            ctx.add("%s: matrix modes covered (%s)" % (probe, fmt),
                    "all six one-hot codes", len(modes), modes == want_modes,
                    detail="missing %s" % sorted(want_modes - modes))
            ctx.add("%s: matrix inputs covered (%s)" % (probe, fmt),
                    "%d labels" % len(want_labels), len(labels),
                    labels == want_labels,
                    detail="missing %s extra %s"
                           % (sorted(want_labels - labels),
                              sorted(labels - want_labels)))
    cmap = group(parsed, "cmap")
    if cmap:
        for fmt in oracle.FMT:
            fns = {r["fn"] for r in cmap if r["fmt"] == fmt}
            ctx.add("%s: C mapping functions covered (%s)" % (probe, fmt),
                    "%d functions" % len(oracle.CMAP_CODE), len(fns),
                    fns == set(oracle.CMAP_CODE))
    flags = group(parsed, "flags")
    if flags:
        for fmt in oracle.FMT:
            modes = {int(r["mode"], 0) for r in flags if r["fmt"] == fmt}
            ctx.add("%s: flag modes covered (%s)" % (probe, fmt),
                    "all six one-hot codes", len(modes),
                    modes == set(oracle.ALL_MODES))
    mode = group(parsed, "mode")
    if mode:
        for fmt in oracle.FMT:
            labels = {r["label"] for r in mode
                      if r["fmt"] == fmt and int(r["mode"], 0) == 0x20}
            ctx.add("%s: dynamic mode-sensitivity inputs (%s)" % (probe, fmt),
                    list(MODE_LABELS), sorted(labels),
                    labels == set(MODE_LABELS))
            static_modes = {int(r["mode"], 0) for r in mode
                            if int(r["mode"], 0) != 0x20}
            ctx.add("%s: static insensitivity modes (%s)" % (probe, fmt),
                    list(oracle.STATIC_MODES), sorted(static_modes),
                    static_modes == set(oracle.STATIC_MODES))


def check_aggregates(ctx, probe, parsed):
    """Cross-case checks: mode sensitivity and static insensitivity.

    ISS-323: one static cell is identified by ``(fmt, mode, label)``.  The
    dedup set lives OUTSIDE the per-format loop, so every cell is judged
    exactly once (previously the same cell was judged once per format).
    A duplicated raw cell still makes the oracle's shape check red
    (``judge_static_insensitive`` requires exactly 4 rf0 rows per cell), so
    the dedup cannot hide a duplicated observation.
    """
    mode = group(parsed, "mode")
    if mode:
        for fmt in oracle.FMT:
            for label in MODE_LABELS:
                add_judged(ctx, oracle.judge_distinct(mode, fmt, label))
        static = [r for r in mode if int(r["mode"], 0) != 0x20]
        seen = set()
        for rec in static:
            key = (rec["fmt"], int(rec["mode"], 0), rec["label"])
            if key in seen:
                continue
            seen.add(key)
            add_judged(ctx, oracle.judge_static_insensitive(
                static, key[0], key[1], key[2]))


def disasm_symbols(ctx, obj):
    rc, out, _ = run([ctx.args.objdump, "-d", "--no-show-raw-insn", obj])
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


def check_cmap_mapping(ctx, probe, obj):
    """The backend must select exactly one ftrnd/fornd with the right code."""
    blocks, _ = disasm_symbols(ctx, obj)
    total = 0
    for fn, code in sorted(oracle.CMAP_CODE.items()):
        for suffix in ("", "f"):
            sym = "cmap_" + fn + suffix
            body = blocks.get(sym)
            if body is None:
                ctx.add("cmap %s symbol present" % sym, "present", "missing",
                        False)
                continue
            mn_mono = "ftrnd" if suffix == "f" else "fornd"
            mn_other = "fornd" if suffix == "f" else "ftrnd"
            text = "\n".join(body)
            n_expected = len(re.findall(r"\b%s\b" % mn_mono, text))
            n_other = len(re.findall(r"\b%s\b" % mn_other, text))
            call = len(re.findall(r"\bcall\b", text))
            imm = None
            for line in body:
                m = re.search(r"\b%s\s+\S+,\s*\S+,\s*(\d+)" % mn_mono, line)
                if m:
                    imm = int(m.group(1))
            total += n_expected
            ok = n_expected == 1 and n_other == 0 and call == 0 and imm == code
            ctx.add("cmap %s -> %s immu6=%#04x" % (sym, mn_mono, code),
                    "1 x %s immu6=%#04x, 0 calls" % (mn_mono, code),
                    "%d x %s, %d x %s, %d calls, immu6=%s"
                    % (n_expected, mn_mono, n_other, mn_other, call, imm),
                    ok)
    ctx.add("%s: C mapping instruction count" % probe,
            "10 (5 ftrnd + 5 fornd)", total, total == 10)


def check_probe(ctx, probe, src=None, tag="", label_suffix=""):
    src = src or source_of(probe)
    obj, elf, rc, log = compile_probe(ctx, probe, src, tag=tag)
    ctx.add("build %s%s" % (probe, label_suffix), 0, rc, rc == 0,
            detail=log[-600:])
    if rc != 0:
        return None, None
    rc, out, secs = run_elf(ctx, elf)
    ctx.add("run %s%s exit" % (probe, label_suffix), 0, rc, rc == 0,
            detail="%.2fs" % secs)
    parsed = judge_probe(ctx, probe + label_suffix, out)
    expected = {"rnd_matrix": ("matrix", "cmap"),
                "rnd_mode": ("mode",),
                "rnd_flags": ("flags",)}[probe]
    check_coverage(ctx, probe + label_suffix, parsed, expected)
    check_aggregates(ctx, probe + label_suffix, parsed)
    return obj, parsed


# ── injections (reachable-FAIL proof) ────────────────────────────────────
def _copy_probe_dir(dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for name in SOURCES:
        shutil.copyfile(os.path.join(PROBE_DIR, name),
                        os.path.join(dst, name))


def _mutate(path, pairs):
    with open(path) as f:
        text = f.read()
    for old, new in pairs:
        if text.count(old) != 1:
            raise RuntimeError("injection anchor %r not unique in %s"
                               % (old, path))
        text = text.replace(old, new, 1)
    with open(path, "w") as f:
        f.write(text)


def red_cells(ctx, parsed):
    """Judge a probe output and return the red checks (nothing added to ctx)."""
    out = []
    checks = [oracle.judge_init(parsed["init"])]
    checks += [oracle.judge_obs(r) for r in parsed["obs"]]
    checks += [oracle.judge_restore(r) for r in parsed["restore"]]
    out = [c for c in checks if not c["ok"]]
    return out


def injection_mode(ctx):
    """Two real injections: 0x01/0x02 swapped; static mode routed to 0x20."""
    src_md5 = {name: md5(os.path.join(PROBE_DIR, name)) for name in SOURCES}

    # baseline (the same code path as the normal run) must be green first
    obj, parsed = check_probe(ctx, "rnd_matrix")
    green_before = not [c for c in ctx.checks if not c["ok"]]
    ctx.add("inject: baseline matrix green before injections", "no FAIL",
            "see matrix checks", green_before)

    # ── injection 1: swap 0x01 (ties-even) and 0x02 (ties-away) ──
    d1 = os.path.join(ctx.out, "inject-swap")
    _copy_probe_dir(d1)
    _mutate(os.path.join(d1, "rnd_common.h"), [
        ('case 0x01: F("1"); break;', 'case 0x01: F("2"); break;'),
        ('case 0x02: F("2"); break;', 'case 0x02: F("1"); break;'),
    ])
    changed = md5(os.path.join(d1, "rnd_common.h")) != src_md5["rnd_common.h"]
    ctx.add("inject 1: source copy really changed", "different md5",
            "different" if changed else "same", changed)
    obj, elf, rc, log = compile_probe(ctx, "rnd_matrix",
                                      os.path.join(d1, "rnd_matrix.c"),
                                      tag="-inject-swap", out_dir=d1)
    ctx.add("inject 1: build", 0, rc, rc == 0, detail=log[-600:])
    if rc == 0:
        rc, out, _ = run_elf(ctx, elf)
        ctx.add("inject 1: run exit", 0, rc, rc == 0)
        parsed = oracle.parse(out)
        reds = red_cells(ctx, parsed)
        tie = [c for c in reds if c["name"].startswith("matrix")
               and re.search(r" (0\.5|1\.5|2\.5|3\.5|-0\.5|-1\.5|-2\.5"
                             r"|-3\.5) 0x0[12]$", c["name"])]
        ctx.add("inject 1 (0x01/0x02 swapped): tie cells go red",
                ">= 2 red tie cells", "%d red / %d total"
                % (len(tie), len(reds)), len(tie) >= 2,
                detail="; ".join(c["name"] for c in tie[:4]))

    # ── injection 2: the five static directions routed through the real
    #    status (NX) path, i.e. the instruction code becomes 0x20 while the
    #    probe still records the static code (NX appears where 0 is required)
    d2 = os.path.join(ctx.out, "inject-nx")
    _copy_probe_dir(d2)
    _mutate(os.path.join(d2, "rnd_common.h"), [
        ('case 0x01: F("1"); break;', 'case 0x01: F("32"); break;'),
        ('case 0x02: F("2"); break;', 'case 0x02: F("32"); break;'),
        ('case 0x04: F("4"); break;', 'case 0x04: F("32"); break;'),
        ('case 0x08: F("8"); break;', 'case 0x08: F("32"); break;'),
        ('case 0x10: F("16"); break;', 'case 0x10: F("32"); break;'),
    ])
    changed = md5(os.path.join(d2, "rnd_common.h")) != src_md5["rnd_common.h"]
    ctx.add("inject 2: source copy really changed", "different md5",
            "different" if changed else "same", changed)
    obj, elf, rc, log = compile_probe(ctx, "rnd_flags",
                                      os.path.join(d2, "rnd_flags.c"),
                                      tag="-inject-nx", out_dir=d2)
    ctx.add("inject 2: build", 0, rc, rc == 0, detail=log[-600:])
    if rc == 0:
        rc, out, _ = run_elf(ctx, elf)
        ctx.add("inject 2: run exit", 0, rc, rc == 0)
        parsed = oracle.parse(out)
        reds = red_cells(ctx, parsed)
        nxf = [c for c in reds if c["name"].startswith("flags")
               and re.search(r" (1\.5|0\.5|-0\.5|minsub) 0x(01|02|04|08|10)$",
                             c["name"])]
        ctx.add("inject 2 (static routed to 0x20): NX cells go red",
                ">= 1 red NX cell", "%d red / %d total"
                % (len(nxf), len(reds)), len(nxf) >= 1,
                detail="; ".join(c["name"] for c in nxf[:4]))

    # ── injection 3: duplicate one static observation cell ──
    # ISS-323: the dedup key must collapse the duplicate (judged once) and the
    # uniqueness assertion must go red, proving the assertion is reachable.
    obj, elf, rc, log = compile_probe(ctx, "rnd_mode", source_of("rnd_mode"),
                                      tag="-inject-dup")
    ctx.add("inject 3: build", 0, rc, rc == 0, detail=log[-600:])
    if rc == 0:
        rc, out, _ = run_elf(ctx, elf)
        parsed = oracle.parse(out)
        static = [r for r in parsed["obs"]
                  if r["group"] == "mode" and int(r["mode"], 0) != 0x20]
        ctx.add("inject 3: static rows present", "> 0", len(static),
                len(static) > 0)
        if static:
            parsed["obs"].append(dict(static[0]))
            scratch = Ctx(ctx.args)
            check_aggregates(scratch, "inject-dup", parsed)
            red = [c for c in scratch.checks if not c["ok"]
                   and c["name"].startswith("static insensitivity ")]
            judged = [c for c in scratch.checks
                      if c["name"].startswith("static insensitivity ")]
            unique = len({(r["fmt"], int(r["mode"], 0), r["label"])
                          for r in parsed["obs"]
                          if r["group"] == "mode" and int(r["mode"], 0) != 0x20})
            ctx.add("inject 3 (duplicate static cell): judged once, check goes red",
                    "1 red static-insensitivity check, judged == distinct cells",
                    "%d red, %d distinct cells judged %d"
                    % (len(red), unique, len(judged)),
                    len(red) >= 1 and len(judged) == unique,
                    detail="the extra row violates the oracle's 4-rows-per-cell shape")

    # ── the repository sources were never touched ──
    for name in SOURCES:
        now = md5(os.path.join(PROBE_DIR, name))
        ctx.add("inject: repo source %s unchanged" % name, src_md5[name], now,
                now == src_md5[name], detail="md5")

    # ── green again with the shipped sources ──
    obj, elf, rc, log = compile_probe(ctx, "rnd_matrix", source_of("rnd_matrix"),
                                      tag="-restored")
    if rc == 0:
        rc, out, _ = run_elf(ctx, elf)
        reds = red_cells(ctx, oracle.parse(out))
        ctx.add("inject: shipped matrix green again", "0 red", len(reds),
                not reds, detail="; ".join(c["name"] for c in reds[:3]))


# ── main ─────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--opt", choices=("O0", "O2"), required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--objdump", default=DEFAULT_OBJDUMP)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--inject", action="store_true",
                    help="reachable-FAIL self test (two real injections)")
    args = ap.parse_args(argv)

    ctx = Ctx(args)
    rc, out, _ = run([args.clang, "--target=dadao-unknown-elf",
                      "-rtlib=compiler-rt", "-print-libgcc-file-name"])
    if rc != 0:
        raise SystemExit("cannot resolve compiler-rt: %s" % out)
    ctx.rtlib = out.strip()

    env = {
        "clang": tool_id(args.clang),
        "ldlld": tool_id(args.ldlld),
        "qemu": tool_id(args.qemu),
        "libc_a": tool_id(os.path.join(args.musl, "lib", "libc.a")),
        "crt1": tool_id(os.path.join(args.musl, "lib", "crt1.o")),
        "rtlib": ctx.rtlib,
    }

    if args.inject:
        injection_mode(ctx)
    else:
        for probe in PROBES:
            obj, _ = check_probe(ctx, probe)
            if probe == "rnd_matrix" and obj is not None:
                check_cmap_mapping(ctx, probe, obj)

    fails = [c for c in ctx.checks if not c["ok"]]
    result = "PASS" if not fails else "FAIL"
    doc = {
        "task": "TESTCASES-060t",
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

    for c in ctx.checks:
        if not c["ok"]:
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
