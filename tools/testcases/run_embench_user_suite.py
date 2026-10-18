#!/usr/bin/env python3
"""Embench-IoT user-mode suite runner (TESTCASES-046t, static round first).

Drives every Embench-IoT benchmark from ``<embench-src>/src/*/`` at each
requested optimisation level through the **user-mode** (``qemu-dadao``) flow,
in exactly one link mode per invocation (``--link-mode static|dynamic``, no
default: the two rounds are separate runs by design).

Pipeline per (benchmark, optimisation level)::

    clang --target=dadao-unknown-elf -<O> -nostdinc <musl headers> \
          -I <src>/support -I <src>/examples/dadao -I <src>/<b> \
          -std=gnu99 -ffreestanding -fno-builtin \
          -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=1 \
          -c <support/{main,beebsc}.c> <src>/<b>/*.c <hosted board shim>  -> *.o

    # static line: P1 musl products, lld DEFAULT base (never -T dadao.lds)
    ld.lld -o <b>.elf <musl>/lib/crt1.o <objs> <musl>/lib/libc.a
    qemu-dadao <b>.elf

    # dynamic line: P2 musl products (``--libc`` overrides the file; the P2
    # ``libc.so`` ships in the target sysroot, not in the musl build tree)
    ld.lld -o <b>.elf <musl>/lib/crt1.o <objs> <libc.so> \
           -dynamic-linker /lib/ld-musl-dadao.so.1
    qemu-dadao -L <guest-root> <b>.elf

Base address (ISS-247): the link line carries **no** ``-T``/linker script, so
lld's default base is used.  ``tests/scripts/dadao.lds`` (``RAM ORIGIN =
0xFC00_0000_0000``) cannot be loaded by ``qemu-user`` on this 47-bit host VA
(``Unable to find a guest_base ...``).  The driver records the link command and
the minimum ``PT_LOAD`` virtual address of every produced ELF and refuses an
image whose minimum ``PT_LOAD`` is the scripted base.

Independent oracle (AGENTS.md "Independent oracle")
---------------------------------------------------
The expectation is **never** derived from LLVM, QEMU or anything in this repo:

* Embench's own ``support/main.c`` returns ``!correct``, where ``correct`` is
  the benchmark's own ``verify_benchmark()`` verdict on its own computed
  result.  So *guest exit status 0* is the benchmark's self-check passing --
  the expectation is the constant ``0`` fixed by the upstream source, not a
  value read back from the implementation.
* The suite source tree is manifest-locked (``components/embench-iot``), so the
  corpus itself is the upstream benchmark set.
* The three board hooks (``initialise_board`` / ``start_trigger`` /
  ``stop_trigger``) are hosted-shimmed by ``tests/scripts/embench_user_boardsupport.c``
  (the component's semihosting board shim cannot work in user mode); each hook
  writes a marker, and a *passing* case must show all three markers in its
  captured stdout -- an independent observation that ``support/main.c`` really
  ran the benchmark body through the hooks.

Classification (counted live, never hard-coded)
-----------------------------------------------
* ``pass``       built + ran + guest exit 0 + the three board markers observed.
* ``fail``       built + ran, but the case's own verdict is non-zero (guest exit
                 != 0, including a machine fault exit ``0x80|cause``) or the
                 markers are missing although the exit is 0.  A real defect.
* ``known-fail`` the build/run failure is attributable to **ISS-246**
                 (``__thread``: clang ``thread-local storage is not supported
                 for the current target`` / backend ``GlobalTLSAddress``).  The
                 record carries the issue id and the matching diagnostic line.
                 Nothing else may be relabelled this way.
* ``excluded``   declared up front, structural: an immediate subdirectory of
                 ``src/`` without a ``.c`` translation unit (not an Embench
                 benchmark source).  Counted live; never a silent skip.
* ``blocked``    a backend / library / toolchain gap prevents building or
                 running: compile/link failure, missing symbol, qemu killed by a
                 host signal, or timeout (``blocked > 0 => rc = 1``, the
                 ISS-248 gate rule: incomplete coverage must not look green).
                 A guest that dies in the **loader** (musl ldso prints
                 ``Error relocating`` before ``support/main.c`` runs, so no
                 board marker appears) is the same kind of gap -- the
                 benchmark's own verdict was never reached, so it must not be
                 reported as a true ``fail`` of the benchmark either.

Exit status: 0 = no ``fail`` and no ``blocked``; 1 = otherwise; 2 = setup error
(missing tool / source / library product / zero benchmarks).

Structural closure (lessons §2.21): the driver enumerates ``src/*/`` live and
requires the executed set to equal the discovered set (per requested
optimisation level); a case that is silently skipped makes the run fail.

Counting is live: total = discovered benchmarks x requested opt levels.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import struct
import subprocess
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases"))
import paths as _paths  # noqa: E402
import run_artifacts as _run_artifacts  # noqa: E402

TOOLCHAIN_BIN = str(_paths.host_toolchain_bin())

DEFAULT_CLANG = os.path.join(TOOLCHAIN_BIN, "clang")
DEFAULT_LDLD = os.path.join(TOOLCHAIN_BIN, "ld.lld")
DEFAULT_QEMU = os.path.join(TOOLCHAIN_BIN, "qemu-dadao")
DEFAULT_EMBENCH_SRC = ".work/source/embench-iot"
DEFAULT_MUSL = ".work/source/musl"
DEFAULT_SHIM = "tests/scripts/embench_user_boardsupport.c"
DEFAULT_WORK_DIR = str(_paths.test_artifacts_dir() / "embench-user")
DEFAULT_OPTS = "O0,O2"
DEFAULT_TIMEOUT = 60
DYNAMIC_LINKER = "/lib/ld-musl-dadao.so.1"

# musl port include set -- identical to tools/infra/build_musl.py and
# tools/testcases/run_suite.py (the esoteric include dirs are required with
# -nostdinc).
MUSL_INCLUDE_DIRS = ("arch/dadao", "arch/generic", "obj/src/internal",
                     "src/include", "src/internal", "obj/include", "include")

# The expected guest exit status for a passing case: Embench's support/main.c
# returns !correct.  Injected (wrong) by the evidence script's counter-example.
EXPECTED_GUEST_EXIT = 0

# ISS-246 is the ONLY admitted known-fail cause for this suite.
ISS246_PATTERNS = (
    "thread-local storage is not supported",
    "GlobalTLSAddress",
)
ISS246_ID = "ISS-246"

# Machine fault exits (ADR-0004 D5.8): a guest exited through a machine fault;
# the case reached the benchmark and its own verdict failed -> `fail`, not a
# harness `blocked`.
FAULT_NAMES = {
    0x87: "UNMAPPED", 0x88: "ILLI", 0x89: "UNDI", 0x8A: "RASOF",
    0x8B: "RASUF", 0x8C: "MALIGN", 0x8D: "IALIGN",
}

# The scripted base of tests/scripts/dadao.lds (ISS-247) -- an image linked
# there cannot be loaded by qemu-user on this host and is rejected here.
SCRIPTED_BASE = 0xFC0000000000

BOARD_MARKERS = (b"[board:init]", b"[board:start]", b"[board:stop]")

PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3


class SetupError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def run(cmd, timeout=None):
    """Run cmd; return (rc, stdout, stderr, timed_out). rc is None on timeout."""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
        return (proc.returncode,
                proc.stdout.decode("utf-8", errors="replace"),
                proc.stderr.decode("utf-8", errors="replace"), False)
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode("utf-8", errors="replace")
        err = (exc.stderr or b"").decode("utf-8", errors="replace")
        return None, out, err, True


def require_file(path: str, what: str) -> None:
    if not os.path.isfile(path):
        raise SetupError(f"{what} not found: {path}")


def require_exec(path: str, what: str) -> None:
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        raise SetupError(f"{what} not executable: {path}")


def elf_program_headers(path: str):
    """Minimal ELF64 big-endian program-header reader (independent of QEMU)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ValueError(f"{path}: not an ELF file")
    if data[4] != 2 or data[5] != 2:
        raise ValueError(f"{path}: expected ELFCLASS64/ELFDATA2MSB, "
                         f"got class={data[4]} data={data[5]}")
    (e_phoff,) = struct.unpack_from(">Q", data, 32)
    (e_phentsize, e_phnum) = struct.unpack_from(">HH", data, 54)
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, _p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, \
            _p_align = struct.unpack_from(">IIQQQQQQ", data, off)
        phdrs.append(dict(type=p_type, offset=p_offset, vaddr=p_vaddr,
                          filesz=p_filesz, memsz=p_memsz))
        if p_type == PT_INTERP:
            phdrs[-1]["interp"] = data[p_offset:p_offset + p_filesz]
    return phdrs


def min_pt_load(path: str) -> int:
    return min(p["vaddr"] for p in elf_program_headers(path) if p["type"] == PT_LOAD)


def pt_interp(path: str) -> bytes:
    for p in elf_program_headers(path):
        if p["type"] == PT_INTERP:
            return p.get("interp", b"")
    return b""


def has_pt_dynamic(path: str) -> bool:
    return any(p["type"] == PT_DYNAMIC for p in elf_program_headers(path))


def discover(src_root: str):
    """Return (benchmarks, excluded) from the live source tree.

    A benchmark is an immediate subdirectory carrying >= 1 ``*.c`` file.  A
    subdirectory without one is a declared structural exclusion (with reason),
    never a silent skip.
    """
    benchmarks, excluded = [], []
    for entry in sorted(os.listdir(src_root)):
        d = os.path.join(src_root, entry)
        if not os.path.isdir(d):
            continue
        if glob.glob(os.path.join(d, "*.c")):
            benchmarks.append(entry)
        else:
            excluded.append((entry, "no .c translation unit under src/%s/ "
                                     "(structural: not an Embench benchmark "
                                     "source)" % entry))
    return benchmarks, excluded


class Case:
    __slots__ = ("bench", "opt", "klass", "exit", "reason", "elf",
                 "min_pt_load", "interp", "markers", "link_cmd", "outdir")

    def __init__(self, bench, opt):
        self.bench = bench
        self.opt = opt
        self.klass = "blocked"
        self.exit = None
        self.reason = ""
        self.elf = ""
        self.min_pt_load = None
        self.interp = ""
        self.markers = []
        self.link_cmd = []
        self.outdir = ""

    def as_dict(self, mode):
        return dict(mode=mode, benchmark=self.bench, opt=self.opt,
                    klass=self.klass, exit=self.exit, reason=self.reason,
                    elf=self.elf, min_pt_load=(None if self.min_pt_load is None
                                               else hex(self.min_pt_load)),
                    pt_interp=self.interp, board_markers=self.markers,
                    link_cmd=self.link_cmd, work_dir=self.outdir)


def iss246_hit(text: str):
    for pat in ISS246_PATTERNS:
        idx = text.find(pat)
        if idx >= 0:
            line = text[:idx].count("\n")
            snippet = text.splitlines()[line].strip()
            return pat, snippet
    return None


def build_and_run(bench, opt, cfg, work_dir):
    res = Case(bench, opt)
    outdir = os.path.join(work_dir, cfg["mode"], opt, bench)
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    res.outdir = outdir

    src_root = cfg["embench_src"]
    incs = []
    for d in (cfg["musl_include_dirs"]
              + [os.path.join(src_root, "support"),
                 os.path.join(src_root, "examples", "dadao"),
                 os.path.join(src_root, "src", bench)]):
        incs += ["-I", d]
    cflags = (["-target", "dadao-unknown-elf", "-" + opt, "-nostdinc"]
              + incs
              + ["-std=gnu99", "-ffreestanding", "-fno-builtin",
                 "-DWARMUP_HEAT=1", "-DGLOBAL_SCALE_FACTOR=1"])

    sources = [os.path.join(src_root, "support", "main.c"),
               os.path.join(src_root, "support", "beebsc.c"),
               cfg["shim"]] + sorted(glob.glob(
                   os.path.join(src_root, "src", bench, "*.c")))
    objs = []
    for idx, src in enumerate(sources):
        obj = os.path.join(outdir, f"{idx:02d}_{os.path.splitext(os.path.basename(src))[0]}.o")
        rc, _o, err, timed = run([cfg["clang"]] + cflags + ["-c", src, "-o", obj])
        if timed or rc != 0:
            hit = iss246_hit(err)
            if hit:
                res.klass = "known-fail"
                res.reason = (f"{ISS246_ID} {hit[0]!r}: {hit[1]} "
                              f"(clang rc={rc} on {os.path.basename(src)})")
            elif timed:
                res.klass = "blocked"
                res.reason = f"compile timeout on {os.path.basename(src)}"
            else:
                res.klass = "blocked"
                first = err.strip().splitlines()[0] if err.strip() else "(no stderr)"
                res.reason = (f"compile error rc={rc} on "
                              f"{os.path.basename(src)}: {first[:200]}")
            return res
        objs.append(obj)

    if cfg["mode"] == "static":
        link = ([cfg["ldlld"], "-o", os.path.join(outdir, bench + ".elf"),
                 cfg["crt1"]] + objs + [cfg["libc"]])
    else:
        link = ([cfg["ldlld"], "-o", os.path.join(outdir, bench + ".elf"),
                 cfg["crt1"]] + objs + [cfg["libc"],
                 "-dynamic-linker", DYNAMIC_LINKER])
    res.link_cmd = link
    rc, _o, err, timed = run(link)
    elf = os.path.join(outdir, bench + ".elf")
    if timed or rc != 0:
        res.klass = "blocked"
        if timed:
            res.reason = "link timeout"
        else:
            first = err.strip().splitlines()[0] if err.strip() else "(no stderr)"
            res.reason = f"link error rc={rc}: {first[:200]}"
        return res
    res.elf = elf

    # Link-shape checks: lld default base (ISS-247) and the modality (ISS-*
    # PT_INTERP absence/presence), read straight out of the file.
    try:
        res.min_pt_load = min_pt_load(elf)
        res.interp = pt_interp(elf).decode("utf-8", errors="replace").rstrip("\0")
    except ValueError as exc:
        res.klass = "blocked"
        res.reason = f"ELF parse failed: {exc}"
        return res
    if res.min_pt_load == SCRIPTED_BASE:
        res.klass = "blocked"
        res.reason = (f"ELF min PT_LOAD is the scripted dadao.lds base "
                      f"0x{SCRIPTED_BASE:x} (ISS-247: qemu-user cannot load it)")
        return res
    if cfg["mode"] == "static" and res.interp:
        res.klass = "blocked"
        res.reason = f"static image carries PT_INTERP {res.interp!r}"
        return res
    if cfg["mode"] == "static" and has_pt_dynamic(elf):
        res.klass = "blocked"
        res.reason = ("static image carries PT_DYNAMIC (the library on the "
                      "link line is a shared object, not an archive)")
        return res
    if cfg["mode"] == "dynamic" and res.interp != DYNAMIC_LINKER:
        res.klass = "blocked"
        res.reason = (f"dynamic image PT_INTERP {res.interp!r} != "
                      f"{DYNAMIC_LINKER!r}")
        return res
    if cfg["mode"] == "dynamic" and not has_pt_dynamic(elf):
        res.klass = "blocked"
        res.reason = ("dynamic image has no PT_DYNAMIC (the library on the "
                      "link line is an archive, not libc.so)")
        return res

    cmd = [cfg["qemu"]]
    if cfg["mode"] == "dynamic":
        cmd += ["-L", cfg["guest_root"]]
    cmd += [elf]
    rc, stdout, stderr, timed = run(cmd, timeout=cfg["timeout"])
    res.markers = [m.decode() for m in BOARD_MARKERS if m in stdout.encode()]
    if timed:
        res.klass = "blocked"
        res.reason = f"timeout after {cfg['timeout']}s"
        return res
    if rc is None:
        res.klass = "blocked"
        res.reason = "qemu did not return an exit code"
        return res
    if rc < 0:
        res.klass = "blocked"
        res.reason = f"qemu killed by signal {-rc}"
        return res
    res.exit = rc
    if rc != EXPECTED_GUEST_EXIT:
        # musl's ldso prints "Error relocating ..." and exits before
        # support/main.c can run (no board marker).  That is a loader/library
        # gap, not the benchmark's own verdict -> `blocked`, never `fail`.
        if not res.markers and "Error relocating" in stderr:
            first = stderr.strip().splitlines()[0] if stderr.strip() else "(no stderr)"
            res.klass = "blocked"
            res.reason = (f"loader aborted before main (ldso): {first[:200]}")
            return res
        res.klass = "fail"
        if rc in FAULT_NAMES:
            res.reason = (f"machine fault {FAULT_NAMES[rc]} (0x{rc:02X}); "
                          f"expected exit {EXPECTED_GUEST_EXIT}")
        else:
            res.reason = f"guest exit {rc}, expected {EXPECTED_GUEST_EXIT}"
        return res
    missing = [m.decode() for m in BOARD_MARKERS if m.decode() not in res.markers]
    if missing:
        res.klass = "fail"
        res.reason = f"exit 0 but board markers missing: {missing}"
        return res
    res.klass = "pass"
    res.reason = "exit 0 (verify_benchmark passed) + 3 board markers"
    return res


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Embench-IoT user-mode suite (TESTCASES-046t)")
    ap.add_argument("--link-mode", choices=("static", "dynamic"), required=True,
                    help="exactly one link mode per invocation (no default)")
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldlld", default=DEFAULT_LDLD)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--embench-src", default=DEFAULT_EMBENCH_SRC)
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--libc", default=None,
                    help="override the library file put on the link line "
                         "(default: <musl>/lib/libc.a for static, "
                         "<musl>/lib/libc.so for dynamic; the P2 libc.so ships "
                         "in the target sysroot)")
    ap.add_argument("--shim", default=DEFAULT_SHIM)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--opt", default=DEFAULT_OPTS,
                    help="comma-separated optimisation levels (default O0,O2)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="per-case timeout in seconds (124/timeout => blocked)")
    ap.add_argument("--json-out", required=True,
                    help="per-case JSON result file (required; relative paths "
                         "resolve against the caller's CWD).  The driver also "
                         "creates <work-dir>/<UTC>-embench-user-<mode>/ with "
                         "run.json/run.log/meta.json (INFRA-093t)")
    ap.add_argument("--report-out", default=None,
                    help="human-readable report (default: same path as "
                         "--json-out with a .log extension)")
    args = ap.parse_args()
    started_utc = _run_artifacts.iso_utc()
    json_out = abspath(args.json_out)
    report_out = (abspath(args.report_out) if args.report_out else
                  os.path.splitext(json_out)[0] + ".log")

    mode = args.link_mode
    cfg = {
        "mode": mode,
        "clang": abspath(args.clang),
        "ldlld": abspath(args.ldlld),
        "qemu": abspath(args.qemu),
        "embench_src": abspath(args.embench_src),
        "shim": abspath(args.shim),
        "timeout": args.timeout,
    }
    musl = abspath(args.musl)
    cfg["musl_include_dirs"] = [os.path.join(musl, d) for d in MUSL_INCLUDE_DIRS]
    cfg["crt1"] = os.path.join(musl, "lib", "crt1.o")
    cfg["libc"] = (abspath(args.libc) if args.libc else
                   os.path.join(musl, "lib",
                                "libc.a" if mode == "static" else "libc.so"))
    work_dir = abspath(args.work_dir)

    try:
        require_exec(cfg["clang"], "clang")
        require_exec(cfg["ldlld"], "ld.lld")
        require_exec(cfg["qemu"], "qemu-dadao")
        require_file(cfg["shim"], "hosted board shim")
        require_file(cfg["crt1"], "musl crt1.o")
        require_file(cfg["libc"], f"libc {os.path.basename(cfg['libc'])}")
        for d in cfg["musl_include_dirs"]:
            if not os.path.isdir(d):
                raise SetupError(f"musl include dir not found: {d}")
        if not os.path.isdir(cfg["embench_src"]):
            raise SetupError(f"embench source not found: {cfg['embench_src']} "
                             "(run 'make fetch' first)")
        src_root = os.path.join(cfg["embench_src"], "src")
        if not os.path.isdir(src_root):
            raise SetupError(f"benchmark source root not found: {src_root}")
        benchmarks, excluded = discover(src_root)
        if not benchmarks:
            raise SetupError(f"no benchmarks found under {src_root}")
        opts = [o.strip().lstrip("-") for o in args.opt.split(",") if o.strip()]
        if not opts:
            raise SetupError("no optimisation levels requested")

        if mode == "dynamic":
            # Guest root: qemu-dadao resolves PT_INTERP relative to -L.
            guest_root = os.path.join(work_dir, mode, "root")
            os.makedirs(os.path.join(guest_root, "lib"), exist_ok=True)
            ldso = os.path.join(guest_root, "lib", "ld-musl-dadao.so.1")
            shutil.copyfile(cfg["libc"], ldso)
            cfg["guest_root"] = guest_root
        os.makedirs(work_dir, exist_ok=True)
    except SetupError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    # INFRA-093t: one directory per invocation; never a shared fixed path.
    run_dir = _run_artifacts.create_run_dir(work_dir, "embench-user", mode)

    lines = []
    def emit(text=""):
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        lines.append(text)

    emit(f"run_embench_user_suite: mode={mode} "
         f"{len(benchmarks)} benchmark(s) x {len(opts)} opt level(s) {opts} "
         f"(现场统计, 非写死)")
    emit(f"  benchmarks: {', '.join(benchmarks)}")
    emit(f"  oracle: expected guest exit {EXPECTED_GUEST_EXIT} "
         f"(support/main.c returns !correct; verify_benchmark is the case's own check)")
    emit(f"  link base: lld default (no -T / no linker script; ISS-247)")
    emit(f"  work dir: {work_dir}")

    results = []
    for opt in opts:
        for bench in benchmarks:
            res = build_and_run(bench, opt, cfg, work_dir)
            act = "?" if res.exit is None else str(res.exit)
            base = "?" if res.min_pt_load is None else hex(res.min_pt_load)
            emit(f"  {res.klass.upper():10s} {bench} (-{opt}) exit={act} "
                 f"base={base} markers={len(res.markers)}/3  ({res.reason})")
            results.append(res)

    # Structural closure: executed set == discovered set (per opt level).
    executed = sorted({(r.bench, r.opt) for r in results})
    expected_set = sorted((b, o) for o in opts for b in benchmarks)
    closure_ok = executed == expected_set
    if not closure_ok:
        emit(f"[FAIL] closure: executed {len(executed)} case(s) != discovered "
             f"{len(expected_set)} (benchmarks={len(benchmarks)} x opts={len(opts)})")

    counts = {k: sum(1 for r in results if r.klass == k)
              for k in ("pass", "fail", "known-fail", "excluded", "blocked")}
    counts["excluded"] = len(excluded)
    total = len(results)
    emit(f"\nembench-user: mode={mode} total={total} pass={counts['pass']} "
         f"fail={counts['fail']} known-fail={counts['known-fail']} "
         f"excluded={counts['excluded']} blocked={counts['blocked']}")
    for name, reason in excluded:
        emit(f"  EXCLUDED {name}: {reason}")
    if counts["known-fail"]:
        for r in results:
            if r.klass == "known-fail":
                emit(f"  KNOWN-FAIL {r.bench} (-{r.opt}): {r.reason}")

    # Artifacts: JSON records + human-readable report.
    record = dict(mode=mode, expected_exit=EXPECTED_GUEST_EXIT,
                  total=total, counts=counts,
                  excluded=[dict(benchmark=n, reason=r)
                            for n, r in excluded],
                  closure_ok=closure_ok,
                  cases=[r.as_dict(mode) for r in results])
    report_text = "\n".join(lines) + "\n"
    extra = []
    for r in results:
        extra.append(f"{r.bench} (-{r.opt}) {r.klass} exit={r.exit} "
                     f"base={r.min_pt_load} reason={r.reason}")
        extra.append("  link: " + " ".join(r.link_cmd))
    report_text += "\n".join(extra) + "\n"
    meta = _run_artifacts.build_meta(
        sys.argv, "embench-user", mode, run_dir, started_utc,
        _run_artifacts.toolchain_summary(
            cfg["clang"], cfg["ldlld"], cfg["qemu"], cfg["libc"], musl))
    written = _run_artifacts.write_run_dir(
        run_dir, record, report_text, meta, json_out, report_out)
    emit(f"  artifacts: {json_out} , {report_out}")
    emit(f"  run dir: {written['run_dir']} (run.json/run.log/meta.json)")

    ok = (counts["fail"] == 0 and counts["blocked"] == 0 and closure_ok)
    emit("run_embench_user_suite: " + ("PASS" if ok else "FAIL"))
    if not ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
