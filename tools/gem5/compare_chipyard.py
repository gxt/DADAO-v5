#!/usr/bin/env python3
"""compare_chipyard.py -- 「chipyard 实测 vs gem5 模型」对策脚手架（m16-gem5-007）.

把**同一个 ELF** 在两个引擎上跑一遍，并把差异归因到周期模型的**类（族）**：

    chipyard : ``simulator-chipyard.harness-WumingTinyConfig +loadmem=<elf>``
               With ``+verbose`` the WumingCore prints one
               ``WumingCore: exec ip=.. inst=.. cycle=..`` line per executed
               instruction, so the per-instruction cost is the cycle delta
               between consecutive EXEC entries -- the *same* method
               docs/core-wuming-cycle-model.md §5 uses.  The SYS_EXIT line
               carries the cycle counter at the exit trap.
    gem5     : ``configs/dadao/se_timing.py`` (TimingSimpleCPU + NoncoherentXBar
               + SimpleMemory, ``--wuming-cycles`` on) and the same ELF with the
               per-instruction table **off**.  ``on - off`` is the cycle count
               the model actually charged, i.e. a measured number, not the sum
               of a table read back.

Stages (each one re-runnable; ``all`` = build + run + report):

    build   compile the embench subset through the existing e2e driver
            (``tests/ee-tiny/run_embench_tiny.py``, tiny profile)
            and record the ELF facts + the corpus' own expected exit code
    run     run every case on both engines and keep the raw observations
    report  join the two sides, attribute the cycles to the model classes and
            write the markdown report

Every number in the report is produced here from raw simulator output; the
script carries **no cycle figure** -- class figures come from
``contracts/wuming-cycles.yaml`` (the live parse of
docs/core-wuming-cycle-model.md), and the wrapper refuses to run when the table
does not match the document.

Checks the report must pass (all live, any FAIL -> non-zero exit):

  C1  guest verdict: exit code == the corpus' expected exit, and the three
      board markers are present, on **both** engines;
  C2  same dynamic stream: chipyard EXEC count == gem5 ``simInsts``;
  C3  cycle accounting (chipyard): sum of per-instruction deltas + the tail
      entry == the SYS_EXIT cycle counter;
  C4  cycle accounting (gem5): the per-class model cost, recomputed here from
      the table rows, == the measured ``on - off`` difference;
  C5  instruction join: every traced ``inst`` word equals the word the
      toolchain's disassembly puts at that IP (no silent mnemonic guess).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "infra"))
sys.path.insert(0, str(ROOT / "tools" / "testcases" / "lib"))

import chipyard_engine                                       # noqa: E402
import gem5_se_engine                                        # noqa: E402
import machine_profile as _machine_profile                   # noqa: E402
import paths as _paths                                       # noqa: E402

DOC = ROOT / "docs/core-wuming-cycle-model.md"
YAML = ROOT / "contracts/wuming-cycles.yaml"
PROCESS_PATCH = ROOT / "components/gem5/patches/src/arch/dadao/process.cc.patch"
GEM5 = ROOT / ".work/source/gem5/build/DADAO/gem5.opt"
CONFIG = ROOT / ".work/source/gem5/configs/dadao/se_timing.py"
E2E = ROOT / "tests" / "ee-tiny" / "run_embench_tiny.py"

# The e2e driver's freestanding runtime prints these through the board shim;
# a guest that exits 0 without ever running the benchmark would miss them.
MARKERS = (b"[board:init]", b"[board:start]", b"[board:stop]")

# The harness counts `+max-cycles` in *harness* clocks, and the core's own
# cycle counter (the one in the `exec`/`SYS_EXIT` lines) advances one per two
# harness clocks: measured live -- a run that trips at harness clock N has its
# last core cycle at N/2 (m16-gem5-007; e.g. +max-cycles=1200000 trips with the
# last `exec` at core cycle 599607).  The option is therefore a *core* cycle
# budget and the plusarg gets HARNESS_CLOCKS times that.
HARNESS_CLOCKS = 2

EXEC_RE = re.compile(
    r"WumingCore: exec ip=0x([0-9a-fA-F]+) inst=0x([0-9a-fA-F]+) "
    r"cycle=\s*(\d+)")
SYS_EXIT_RE = re.compile(
    r"\[WumingSemi\] SYS_EXIT\(0x[0-9a-fA-F]+\) reason=0x([0-9a-fA-F]+) "
    r"code=0x([0-9a-fA-F]+) cycle=\s*(\d+) -> host exit status (-?\d+)")
MAXCYCLES_RE = re.compile(
    r"\*\*\* FAILED \*\*\*\s*\(timeout\)\s+after\s+(\d+)\s+"
    r"simulation cycles")
OBJDUMP_LINE_RE = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s)+)\s*(.*)$")
# The loadmem model reports the window it streamed the image into; instructions
# outside it are the fixed BootROM/hmon firmware, which gem5 SE does not run.
LOADED_RE = re.compile(r"loaded \[0x([0-9a-fA-F]+), 0x([0-9a-fA-F]+)\)")

# Provisional rows never drive gem5's model (wuming_latency.hh |provisional|);
# the same rule applies to the Python side so the two cannot drift.
PROVISIONAL = ("推断", "未测", "待实测")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def die(msg):
    sys.stderr.write(f"compare_chipyard: {msg}\n")
    raise SystemExit(2)


def run_cmd(cmd, *, log_path, timeout=None, env=None, stdin=subprocess.DEVNULL):
    """Run one command, keep its combined output in ``log_path``."""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "wb") as log:
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                              stdin=stdin, timeout=timeout, env=env)
    return proc.returncode


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write("\n")


# ---------------------------------------------------------------------------
# provenance: the machine profile and gem5's own constants
# ---------------------------------------------------------------------------
def machine_profile(name="tiny"):
    """Merged machine profile (contracts/machine.yaml + tests/ee-<env>/runtime.yaml)."""
    prof = _machine_profile.load(name)
    return prof.to_dict()


def stack_base():
    """``StackBase`` of the DADAO SE process, read from the component patch.

    The SE loader writes argv/env at the top of its stack reservation, so a
    Kaiwu-Tiny image (whose own stack sits in SRAM) needs a reservation
    that reaches that high; the value lives in the patch, never here.
    """
    text = PROCESS_PATCH.read_text(encoding="utf-8")
    m = re.search(r"constexpr Addr StackBase = (0x[0-9a-fA-F]+)U?LL;", text)
    if not m:
        die(f"{PROCESS_PATCH}: cannot find `constexpr Addr StackBase`")
    return int(m.group(1), 16)


def tiny_layout():
    """(mem_base, mem_size, max_stack) for running a tiny ELF under gem5 SE.

    * ``mem_base``/``mem_size``: the flat memory must cover the Tiny SRAM window
      *and* gem5's stack reservation, i.e. everything from the SRAM base up to
      ``StackBase``.
    * ``max_stack``: the reservation is ``[StackBase - max_stack, StackBase)``;
      the guest's own SP (profile ``sp``) has to fall inside it, and the
      reservation must not intrude into the image, so the size is chosen to end
      at the 64 KiB page that holds ``sp``.
    """
    prof = machine_profile("tiny")
    base, size = prof["ram_base"], prof["ram_size"]
    sb = stack_base()
    sp = prof["sp"]
    page = 0x10000                      # DADAO page size (spec: 64 KiB)
    limit = sp & ~(page - 1)
    if not (base <= limit < sb):
        die(f"tiny layout: SP {sp:#x} is not inside the SRAM window "
            f"[{base:#x}, {base + size:#x})")
    return {"mem_base": base, "mem_size": sb - base, "max_stack": sb - limit,
            "stack_base": sb, "sp": sp, "ram_base": base, "ram_size": size}


# ---------------------------------------------------------------------------
# cycle table (contracts/wuming-cycles.yaml) -- the model's own figures
# ---------------------------------------------------------------------------
def load_table():
    import yaml
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    by_mnemonic = {}
    for entry in data["instructions"]:
        by_mnemonic.setdefault(entry["mnemonic"], []).append(entry)
    return data, by_mnemonic


def family_of(entry):
    return "/".join(entry["klass"])


def is_provisional(entry):
    prov = entry.get("provenance") or ""
    return (not prov) or any(tag in prov for tag in PROVISIONAL)


def model_total_cycles(entry, ctx):
    """The cycles ``wuming_latency.hh`` charges for one instruction.

    Mirrors the C++ policy row by row (``staticCycles`` / ``dynamicCycles`` /
    ``swymCycles``) using only row fields and the runtime inputs the trace can
    carry; returns ``None`` when the row needs an input this scaffold cannot
    observe, so the caller can report it instead of assuming a value.

    One input is genuinely unobservable here: the ``trap`` tag (``immu18``).
    A Kaiwu-Tiny image reaches the host only through semihosting, so a
    ``trap`` is taken as the semihosting branch; if a program ever took the
    cfx/hmon branch instead, this would under-count 3 cycles per trap and the
    C4 check (table-sum vs measured ``on - off``) would go red -- a loud
    failure, never a silent one.
    """
    if is_provisional(entry):
        return 0
    klasses = entry["klass"]
    dyn = entry.get("dynamic")
    if "D" in klasses:
        n = ctx.get("elements")
        if n is None:
            return None
        w = entry.get("elem_width") or 0
        pe, pb = entry.get("per_element"), entry.get("per_beat")
        if pe is None or pb is None or w == 0:
            return 0
        return pe * n + pb * ((n * w + 7) // 8)
    if "D′" in klasses:
        n = ctx.get("elements")
        if n is None:
            return None
        base, step = entry.get("n_base"), entry.get("n_step")
        if base is None or step is None:
            return 0
        return base + step * n
    if dyn == "mul-config":
        return entry.get("default_cycles") or 0      # yaml: from the table
    if dyn == "ras-kind":
        if ctx.get("ras_mem") is None:
            return None
        figure = (entry.get("mem_cycles") if ctx["ras_mem"]
                  else entry.get("default_cycles"))
        return figure or 0
    if dyn == "trap-target":
        lo = (entry.get("range") or [0])[0]
        if entry.get("semihost_mask") and ctx.get("immu18") is None:
            # the semihosting tag is decided at trap time; every `trap` in a
            # semihosting-only Tiny image takes the F branch
            return entry.get("host_cycles") or 0
        if entry.get("semihost_mask") and \
                (ctx["immu18"] & entry["semihost_mask"]) == entry["semihost_value"]:
            return entry.get("host_cycles") or 0
        return lo or 0
    if dyn == "range":
        if entry["mnemonic"] == "escape":
            off = (ctx.get("imms18") or 0) & 1
            rng = entry.get("range") or [0, 0]
            cyc = rng[0] + off
            return min(cyc, rng[1])
        # C class: one ld/st, evaluated on the block model at one element.
        pe, pb = entry.get("per_element"), entry.get("per_beat")
        if pe is None or pb is None:
            return 0
        return pe + pb
    if dyn == "exponent-diff":
        d = ctx.get("exp_diff")
        if d is None:
            return None
        return (entry.get("dyn_base") or 0) + d + (entry.get("dyn_add") or 0)
    if dyn == "variant" or dyn == "hit-miss":
        return None
    if dyn:
        return None
    value = entry.get("value")
    if value is None:
        return None
    if entry["mnemonic"] == "swym":
        return value + (ctx.get("immu18") or 0)
    return value


def model_extra(entry, ctx):
    """Extra cycles after execute(): the document counts EXEC-to-writeback and
    TimingSimpleCPU already spends one cycle in execute()."""
    total = model_total_cycles(entry, ctx)
    if total is None:
        return None
    return total - 1 if total > 1 else 0


# ---------------------------------------------------------------------------
# disassembly join: IP -> (instruction word, mnemonic, operand text)
# ---------------------------------------------------------------------------
def disassemble(elf, out_path):
    tool = str(_paths.host_toolchain_bin() / "llvm-objdump")
    rc = run_cmd([tool, "-d", str(elf)], log_path=out_path)
    if rc != 0:
        die(f"llvm-objdump failed on {elf} (rc={rc}); see {out_path}")
    table = {}
    for line in Path(out_path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = OBJDUMP_LINE_RE.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        word = int(m.group(2).replace(" ", ""), 16)
        text = m.group(3).strip()
        if text.startswith("<") or not text:
            continue                      # a data word inside .text
        mnemonic = text.split()[0]
        table[addr] = {"word": word, "mnemonic": mnemonic, "text": text}
    return table


def element_count(text):
    """Element count of a block transfer from its register-list operand.

    ``ldm.o {rd32:rd33}, [rb63, rd34]`` -> 2, ``rd2rd {rd4:rd11}`` -> 8.
    ``None`` when the operand is not a brace list (caller reports it).
    """
    m = re.search(r"\{([^}]*)\}", text)
    if not m:
        return None
    count = 0
    for part in m.group(1).split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            lo, hi = (p.strip() for p in part.split(":", 1))
            mlo = re.search(r"(\d+)$", lo)
            mhi = re.search(r"(\d+)$", hi)
            if not (mlo and mhi):
                return None
            count += abs(int(mhi.group(1)) - int(mlo.group(1))) + 1
        else:
            count += 1
    return count


def bank_of(text):
    m = re.match(r"[a-z0-9.]+\s+\{?(r[dbaf])\d", text)
    return m.group(1) if m else None


def pick_row(entries, text):
    """The row of a mnemonic that a disassembled form actually uses.

    A mnemonic can carry several ids (rd/rb/rf/ra bank variants), e.g.
    ``ld.o rf`` is class B4 while ``ld.o rd`` is class C; the id's suffix names
    the bank, and the disassembly names the destination bank, so the join is
    mechanical.  Returns ``(entry, ambiguous)``.
    """
    if len(entries) == 1:
        return entries[0], False
    bank = bank_of(text)
    if bank:
        exact = [e for e in entries if e["id"].rsplit("_", 1)[-1] == bank]
        if len(exact) == 1:
            return exact[0], False
    # Same mnemonic, same class and figure in every variant: no ambiguity.
    sig = {(tuple(e["klass"]), e.get("value"), e.get("dynamic")) for e in entries}
    if len(sig) == 1:
        return entries[0], False
    return entries[0], True


# ---------------------------------------------------------------------------
# stage: build
# ---------------------------------------------------------------------------
def stage_build(args):
    work = Path(args.work_dir)
    build_dir = work / "embench"
    json_out = work / "embench.json"
    cmd = [sys.executable, str(E2E), "--opt", args.opt, "--engine", "qemu",
           "--work-dir", str(build_dir), "--timeout", str(args.build_timeout),
           "--jobs", str(args.jobs), "--json-out", str(json_out)]
    if args.only:
        cmd += ["--only", args.only]
    rc = run_cmd(cmd, log_path=work / "build.log")
    if rc != 0:
        die(f"embench build failed (rc={rc}); see {work / 'build.log'}")
    driver = read_json(json_out)
    cases = []
    for row in driver["cases"]:
        if row["status"] != "PASS":
            die(f"build case {row['case_id']} is {row['status']}: "
                f"{row.get('note', '')}")
        # case_id is "<scope>/<bench>-<opt>" (the driver's own naming).
        scope, _, tail = row["case_id"].rpartition("/")
        bench, _, opt = tail.rpartition("-")
        if not bench or not opt:
            die(f"cannot split case id {row['case_id']!r} into bench/opt")
        elf = build_dir / opt / bench / f"{bench}.elf"
        if not elf.is_file():
            die(f"built ELF missing: {elf}")
        facts = gem5_se_engine.elf_header(str(elf))
        cases.append({
            "bench": bench, "opt": opt, "elf": str(elf),
            "elf_md5": md5_of(elf), "expected_exit": row["exit"],
            "load_lo": min(p["vaddr"] for p in facts["phdrs"]),
            "load_hi": max(p["vaddr"] + p["filesz"] for p in facts["phdrs"]),
            "engine_build": driver.get("engine"),
            # The e2e corpus' board shim writes these through semihosting; a
            # guest that exits 0 without ever running the benchmark misses one.
            "markers": [m.decode() for m in MARKERS],
        })
    write_json(work / "cases.json", {"opt": args.opt, "cases": cases,
                                     "driver_report": str(json_out)})
    sys.stdout.write(f"build: {len(cases)} case(s) -> {work / 'cases.json'}\n")
    return 0


# ---------------------------------------------------------------------------
# stage: run
# ---------------------------------------------------------------------------
def run_chipyard(elf, outdir, args, layout):
    """Run one ELF on the Tiny harness with the per-instruction trace on."""
    outdir.mkdir(parents=True, exist_ok=True)
    semi = outdir / "semi.out"
    trace = outdir / "chipyard.trace"
    log = outdir / "chipyard.log"
    for path in (semi, trace, log):
        if path.exists():
            path.unlink()
    cmd = [str(args.chipyard_sim), "+permissive", f"+loadmem={elf}",
           f"+semiout={semi}", f"+max-cycles={HARNESS_CLOCKS * args.max_cycles}",
           "+verbose", "+permissive-off", "none"]
    env = dict(os.environ)
    env.update(chipyard_engine.default_env(str(ROOT)))
    md5_before = md5_of(args.chipyard_sim)
    started = time.monotonic()
    timed_out = False
    deadline = started + args.chipyard_timeout
    killer = {"fired": False}

    def kill():
        killer["fired"] = True
        proc.kill()

    timer = threading.Timer(args.chipyard_timeout, kill)
    timer.start()
    n_exec = 0
    sys_exit = None
    maxcycle_trip = None
    try:
        with open(trace, "w", encoding="utf-8") as tr, \
                open(log, "w", encoding="utf-8") as lg:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, env=env,
                                    text=True, bufsize=1 << 20)
            for line in proc.stdout:
                m = EXEC_RE.search(line)
                if m:
                    tr.write(f"{m.group(1)} {m.group(2)} {m.group(3)}\n")
                    n_exec += 1
                    continue
                m = SYS_EXIT_RE.search(line)
                if m:
                    sys_exit = {"reason": int(m.group(1), 16),
                                "code": int(m.group(2), 16),
                                "cycle": int(m.group(3)),
                                "status": int(m.group(4))}
                    lg.write(line)
                    continue
                m = MAXCYCLES_RE.search(line)
                if m:
                    maxcycle_trip = int(m.group(1))
                lg.write(line)
            rc = proc.wait()
    finally:
        timer.cancel()
        if time.monotonic() > deadline:
            timed_out = True
    seconds = time.monotonic() - started
    markers = [m.decode() for m in MARKERS if m in semi.read_bytes()] \
        if semi.exists() else []
    return {
        "cmd": cmd, "rc": rc, "seconds": round(seconds, 2),
        "timed_out": timed_out or killer["fired"],
        "exec_count": n_exec, "sys_exit": sys_exit,
        "max_cycles_tripped": maxcycle_trip is not None,
        "markers": markers, "sim_md5": md5_of(args.chipyard_sim),
        "sim_stable": md5_of(args.chipyard_sim) == md5_before,
        "trace": str(trace), "log": str(log), "semi_out": str(semi),
    }


def gem5_stats(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8",
                                     errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("simInsts", "simOps",
                                            "system.cpu.numCycles"):
            try:
                out[parts[0]] = int(float(parts[1]))
            except ValueError:
                pass
    return out


def run_gem5(elf, outdir, args, layout, *, cycles_on):
    outdir.mkdir(parents=True, exist_ok=True)
    for path in (outdir / "m5out",):
        if path.exists():
            shutil.rmtree(path)
    m5out = outdir / "m5out"
    semi = outdir / "semi.out"
    log = outdir / "gem5.log"
    cmd = [str(args.gem5), f"--outdir={m5out}", str(args.gem5_config),
           "--binary", str(elf), "--cycle-table", str(args.table),
           "--mem-base", hex(layout["mem_base"]),
           "--mem-size", str(layout["mem_size"]),
           "--max-stack", str(layout["max_stack"]),
           "--semihost", "on", "--console-out", str(semi),
           "--guest-stdin", "/dev/null"]
    if cycles_on:
        cmd.append("--wuming-cycles")
    if args.max_insts:
        cmd += ["--max-insts", str(args.max_insts)]
    started = time.monotonic()
    rc = run_cmd(cmd, log_path=log, timeout=args.gem5_timeout)
    seconds = time.monotonic() - started
    stats = gem5_stats(m5out / "stats.txt") if (m5out / "stats.txt").is_file() else {}
    markers = [m.decode() for m in MARKERS
               if semi.is_file() and m in semi.read_bytes()]
    return {
        "cmd": cmd, "rc": rc, "seconds": round(seconds, 2),
        "wuming_cycles": cycles_on, "insts": stats.get("simInsts"),
        "cycles": stats.get("system.cpu.numCycles"),
        "markers": markers, "semi_out": str(semi), "log": str(log),
        "outdir": str(m5out), "gem5_md5": md5_of(args.gem5),
        "cycles_on": cycles_on,
    }


def stage_run(args):
    work = Path(args.work_dir)
    manifest = read_json(work / "cases.json")
    layout = tiny_layout()
    cases = manifest["cases"]
    if args.only:
        wanted = {b.strip() for b in args.only.split(",") if b.strip()}
        missing = sorted(wanted - {c["bench"] for c in cases})
        if missing:
            die(f"--only names no built case: {', '.join(missing)} "
                f"(built: {', '.join(sorted(c['bench'] for c in cases))})")
        cases = [c for c in cases if c["bench"] in wanted]
    results = {}
    lock = threading.Lock()

    def one(case):
        bench = case["bench"]
        outdir = work / "runs" / bench
        outdir.mkdir(parents=True, exist_ok=True)
        res = {"bench": bench, "opt": case["opt"], "elf": case["elf"],
               "elf_md5": case["elf_md5"],
               "expected_exit": case["expected_exit"],
               "layout": layout}
        try:
            one_engines(case, outdir, res)
        except Exception as exc:                       # noqa: BLE001
            # A crashed case keeps a record: the report then reports it as a
            # missing/failed engine instead of silently dropping the row.
            res["error"] = f"{type(exc).__name__}: {exc}"
            sys.stdout.write(f"[error] {bench}: {res['error']}\n")
        with lock:
            results[bench] = res

    def one_engines(case, outdir, res):
        bench = case["bench"]
        if args.engine in ("both", "chipyard"):
            sys.stdout.write(f"[chipyard] {bench}: start\n")
            sys.stdout.flush()
            res["chipyard"] = run_chipyard(case["elf"], outdir, args, layout)
            sys.stdout.write(
                f"[chipyard] {bench}: rc={res['chipyard']['rc']} "
                f"exec={res['chipyard']['exec_count']} "
                f"cycles={(res['chipyard']['sys_exit'] or {}).get('cycle')} "
                f"{res['chipyard']['seconds']}s\n")
            sys.stdout.flush()
        if args.engine in ("both", "gem5"):
            sys.stdout.write(f"[gem5] {bench}: start\n")
            sys.stdout.flush()
            res["gem5_on"] = run_gem5(case["elf"], outdir / "gem5-on", args,
                                      layout, cycles_on=True)
            res["gem5_off"] = run_gem5(case["elf"], outdir / "gem5-off", args,
                                       layout, cycles_on=False)
            sys.stdout.write(
                f"[gem5] {bench}: rc={res['gem5_on']['rc']} "
                f"insts={res['gem5_on']['insts']} "
                f"cycles={res['gem5_on']['cycles']} "
                f"off={res['gem5_off']['cycles']} "
                f"{res['gem5_on']['seconds']}s\n")
            sys.stdout.flush()

    jobs = max(1, args.jobs)
    threads = []
    queue = list(cases)

    def worker():
        while True:
            with lock:
                if not queue:
                    return
                case = queue.pop(0)
            one(case)

    for _ in range(min(jobs, len(cases))):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    # Merge at *field* level: re-running one engine (e.g. after a rebuild) must
    # not throw away the other engine's observation for the same case.
    merged = {}
    for record in (read_json(work / "runs.json")["cases"]
                   if (work / "runs.json").is_file() else []):
        merged.setdefault(record["bench"], {}).update(record)
    # ... and a foreign record is only the *fallback*: whatever this
    # invocation just measured wins, so re-running one engine refreshes it.
    if args.merge_from:
        other_dir = Path(args.merge_from)
        for record in read_json(other_dir / "runs.json")["cases"]:
            merged.setdefault(record["bench"], {}).update(record)
        # a case that came from the foreign dir also has to be described here
        other_cases = {c["bench"]: c for c in
                       read_json(other_dir / "cases.json")["cases"]}
        known = {c["bench"] for c in manifest["cases"]}
        for bench in merged:
            if bench not in known and bench in other_cases:
                manifest["cases"].append(other_cases[bench])
                known.add(bench)
        write_json(work / "cases.json", manifest)
    for bench, record in results.items():
        merged.setdefault(bench, {}).update(record)
    order = [c["bench"] for c in manifest["cases"]]
    write_json(work / "runs.json",
               {"opt": manifest["opt"], "layout": layout,
                "cases": [merged[b] for b in order if b in merged]})
    sys.stdout.write(f"run: {len(results)} case(s) -> {work / 'runs.json'}\n")
    return 0


# ---------------------------------------------------------------------------
# stage: report
# ---------------------------------------------------------------------------
def load_trace(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            ip, inst, cycle = line.split()
            rows.append((int(ip, 16), int(inst, 16), int(cycle)))
    return rows


def analyse_case(case, by_mnemonic, objdump_cache, table):
    bench = case["bench"]
    chip = case.get("chipyard")
    res = {"bench": bench, "opt": case["opt"], "checks": [], "fails": []}

    def check(name, ok, detail):
        res["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            res["fails"].append(f"{bench}/{name}: {detail}")

    if chip is None or "gem5_on" not in case:
        check("C0 both engines ran", False, "missing engine record")
        return res

    elf = case["elf"]
    if elf not in objdump_cache:
        objdump_cache[elf] = disassemble(elf, Path(case["elf"]).parent / "disasm.txt")
    disasm = objdump_cache[elf]
    trace = load_trace(chip["trace"])

    # ---- verdicts (C1) ----------------------------------------------------
    cy_exit = (chip["sys_exit"] or {}).get("status")
    on, off = case["gem5_on"], case["gem5_off"]
    expected = case["expected_exit"]
    check("C1a chipyard guest exit", cy_exit == expected,
          f"expected={expected} actual={cy_exit}")
    check("C1b gem5 guest exit", on["rc"] == expected,
          f"expected={expected} actual={on['rc']}")
    want = case.get("markers", [])
    check("C1c chipyard board markers", chip["markers"] == want,
          f"{len(chip['markers'])}/{len(want)} {want}")
    check("C1d gem5 board markers", on["markers"] == want,
          f"{len(on['markers'])}/{len(want)} {want}")
    check("C1e chipyard sim binary stable", chip["sim_stable"], "md5 before == after")

    # ---- same dynamic instruction stream (C2) ----------------------------
    # The harness boots the fixed BootROM/hmon firmware first; only the window
    # it streamed the image into is the application.  gem5 SE runs the ELF
    # alone, so the comparison is on that window (the firmware count is
    # reported, never silently mixed in).
    text = Path(chip["log"]).read_text(encoding="utf-8", errors="replace")
    m = LOADED_RE.search(text)
    if m:
        app_lo, app_hi = int(m.group(1), 16), int(m.group(2), 16)
    else:
        app_lo, app_hi = case["load_lo"], case["load_hi"]
    app = [row for row in trace if app_lo <= row[0] < app_hi]
    boot = [row for row in trace if not (app_lo <= row[0] < app_hi)]
    cy_insts = len(app)
    g_insts = on["insts"]
    check("C2 same instruction count", cy_insts == g_insts,
          f"chipyard(app window)= {cy_insts} gem5={g_insts} "
          f"chipyard boot/firmware={len(boot)}")

    # ---- chipyard per-instruction deltas (C3, C5) ------------------------
    fam = {}
    unresolved = 0
    ambiguous = 0
    join_bad = 0
    for idx, (ip, inst, cycle) in enumerate(app):
        hit = disasm.get(ip)
        if hit is None or hit["word"] != inst:
            join_bad += 1
            label = ("A", "unknown")
        else:
            entries = by_mnemonic.get(hit["mnemonic"])
            if not entries:
                unresolved += 1
                label = ("A", "unknown")
            else:
                entry, amb = pick_row(entries, hit["text"])
                ambiguous += int(amb)
                label = (family_of(entry), hit["mnemonic"])
        nxt = app[idx + 1][2] if idx + 1 < len(app) else None
        cost = None if nxt is None else nxt - cycle
        slot = fam.setdefault(label, {"n": 0, "cycles": 0})
        slot["n"] += 1
        if cost is not None:
            slot["cycles"] += cost
    total_at_exit = (chip["sys_exit"] or {}).get("cycle")
    attributed = sum(s["cycles"] for s in fam.values())
    # The application's own cycle count: from its first EXEC entry to the
    # SYS_EXIT trap (the BootROM/hmon firmware is excluded).
    app_cycles = (None if (not app or total_at_exit is None)
                  else total_at_exit - app[0][2])
    tail = 0 if app_cycles is None else app_cycles - attributed
    check("C3 chipyard cycle accounting",
          app_cycles is not None and 0 <= tail <= 64,
          f"app cycles={app_cycles} sum(deltas)={attributed} tail={tail}")
    check("C5 instruction join (word at IP)", join_bad == 0,
          f"mismatched={join_bad}/{len(trace)}")

    # ---- gem5: measured model part and the per-class recomputation (C4) --
    g_on = on["cycles"]
    g_off = off["cycles"]
    model_measured = None if (g_on is None or g_off is None) else g_on - g_off
    model_expected = 0
    per_class = {}
    unobservable = {}
    for idx, (ip, inst, _cycle) in enumerate(app):
        hit = disasm.get(ip)
        if hit is None or hit["word"] != inst:
            continue
        entries = by_mnemonic.get(hit["mnemonic"])
        if not entries:
            continue
        entry, _amb = pick_row(entries, hit["text"])
        ctx = {"elements": element_count(hit["text"])}
        if entry.get("dynamic") == "ras-kind":
            ctx["ras_mem"] = False          # RegRAS unless the doc/table says
        extra = model_extra(entry, ctx)
        key = family_of(entry)
        slot = per_class.setdefault(key, {"n": 0, "extra": 0})
        slot["n"] += 1
        if extra is None:
            unobservable[key] = unobservable.get(key, 0) + 1
            continue
        slot["extra"] += extra
        model_expected += extra
    check("C4 gem5 model accounting",
          model_measured is not None and model_expected == model_measured,
          f"table-recomputed={model_expected} measured(on-off)={model_measured} "
          f"unobservable={sum(unobservable.values())}")

    # ---- assemble the per-family table ----------------------------------
    # `fam` is keyed by (class, mnemonic) for the trace side and `per_class`
    # by class for the model side; the report groups both to the class, which
    # is the taxonomy the cycle model itself uses (§2).
    agg = {}
    for (klass, _mnemonic), slot in fam.items():
        row = agg.setdefault(klass, {"family": klass, "n": 0,
                                     "chipyard_cycles": 0, "gem5_cycles": 0})
        row["n"] += slot["n"]
        row["chipyard_cycles"] += slot["cycles"]
    for klass, slot in per_class.items():
        row = agg.setdefault(klass, {"family": klass, "n": 0,
                                     "chipyard_cycles": 0, "gem5_cycles": 0})
        row["n"] = max(row["n"], slot["n"])
        row["gem5_cycles"] += slot["extra"]
    for row in agg.values():
        row["delta"] = row["gem5_cycles"] - row["chipyard_cycles"]
    # mnemonic detail (top contributors) for the per-case table
    detail = []
    for (klass, mnemonic), slot in fam.items():
        if not mnemonic or mnemonic == "unknown":
            continue
        detail.append({"family": klass, "mnemonic": mnemonic, "n": slot["n"],
                       "chipyard_cycles": slot["cycles"]})
    detail.sort(key=lambda r: -r["chipyard_cycles"])
    res.update({
        "insts": cy_insts, "chipyard_cycles": app_cycles,
        "chipyard_exit_cycle": total_at_exit,
        "chipyard_boot_insts": len(boot), "app_window": [app_lo, app_hi],
        "gem5_cycles": g_on, "gem5_model_cycles": model_measured,
        "gem5_fetch_cycles": g_off, "model_expected": model_expected,
        "unobservable": unobservable, "ambiguous_rows": ambiguous,
        "unresolved_mnemonics": unresolved, "tail": tail,
        "ratio_gem5_over_chipyard": (None if not app_cycles else g_on / app_cycles),
        "by_family": sorted(agg.values(), key=lambda r: -r["chipyard_cycles"]),
        "mnemonics": detail[:12],
        "chipyard_seconds": chip["seconds"], "gem5_seconds": on["seconds"],
        "chipyard_md5": chip["sim_md5"], "gem5_md5": on.get("gem5_md5"),
    })
    return res


def pct(part, whole):
    if not whole:
        return "-"
    return f"{100.0 * part / whole:+.1f}%"


def render_report(rep):
    meta, layout = rep["meta"], rep["layout"]
    cases = [c for c in rep["cases"] if c.get("checks") is not None]
    out = []
    w = out.append
    # docs/TestReports/README.md 的体例：首行快照标记 + 头 40 行含
    # 生成时间 / 数据来源 / 机器指纹 / 复现（L1 `check-test-reports` R2/R4）。
    w("<!-- 现场生成，勿手改 -->")
    w("")
    w("# M17 — wuming 时序：chipyard 实测 vs gem5 模型")
    w("")
    w("> 本文件由 `tools/gem5/compare_chipyard.py report` 生成，**禁手改**：表里每个数字")
    w("> 都来自同一次运行的两个引擎原始输出，改数据就重跑。")
    w("")
    w(f"- 生成时间：{meta['generated_at']}（UTC）；ELF 优化级 `-{meta['opt']}`，同一文件双跑")
    w(f"- 数据来源：chipyard `+verbose` 的逐指令 `exec` 轨迹（`ip/inst/cycle`）、"
      f"gem5 `stats.txt` 的 `simInsts`/`numCycles`（hooks on/off 各一次）、"
      f"两者各自 `semi.out` 的板级打点")
    w(f"- 机器指纹：{meta['host']['machine']} / {meta['host']['cores']} 核；"
      f"chipyard `{meta['host']['chipyard_md5']}`、gem5 `{meta['host']['gem5_md5']}`、"
      f"周期表 `{meta['table_sha']}`、doc `{meta['doc_sha']}`")
    w("- 复现：§6 一条命令（build 复用 embench e2e 驱动，run 双引擎，report 只读原始输出）")
    w(f"- 机器画像 `tiny`：SRAM `{layout['ram_base']:#x}` + {layout['ram_size'] // 1024 // 1024} MiB，"
      f"SP `{layout['sp']:#x}`（`contracts/machine.yaml` + `tests/ee-tiny/runtime.yaml`）")
    w(f"- gem5 `se_timing`：TimingSimpleCPU + NoncoherentXBar + SimpleMemory，1 GHz；"
      f"mem `{layout['mem_base']:#x}`+"
      f"{layout['mem_size'] / 1024 / 1024:.2f} MiB（至 `StackBase`），"
      f"`--max-stack {layout['max_stack']}`（栈预留与 SRAM 窗口由 `StackBase` 与 SP 现场推出）")
    w("- `report` 先跑 `gen_wuming_cycles.py --check`：周期表不是文档的活解析就直接停")
    w(f"- 规模：{len(cases)} 例（embench-IoT 子集，取全语料指令数最小的 {len(cases)} 个；"
      f"选择依据由 `run.sh` 现场复算）")
    w("")
    w("口径：")
    w("")
    w("- chipyard 每指令拍数 = 相邻 `exec` 进入拍差（与 `docs/core-wuming-cycle-model.md`")
    w("  §5 同一方法）；只统计 `+loadmem` 装载窗内的**应用**指令，BootROM/hmon 固件单列。")
    w("- gem5 每类拍数 = 生成表逐行求和（`on − off` 实测差值对账，C4）；")
    w("  `gem5 取指/基础` = hooks off 的周期（1 拍/指令 + 指令侧内存时序）。")
    w("- 比值 = gem5 周期 / chipyard 周期（模型 / 实测）；>1.5 的例在 §3 给归因。")
    w("")

    w("## 1. 总览")
    w("")
    w("| 例 | 应用指令数 | 固件指令 | chipyard 周期 | gem5 周期 | gem5 模型部分 | "
      "gem5 取指/基础 | 比值 | Δ 周期 | chipyard 墙钟 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for c in cases:
        ratio = c.get("ratio_gem5_over_chipyard")
        w(f"| `{c['bench']}` | {c['insts']} | {c['chipyard_boot_insts']} | "
          f"{c['chipyard_cycles']} | {c['gem5_cycles']} | {c['gem5_model_cycles']} | "
          f"{c['gem5_fetch_cycles']} | {ratio:.2f} | "
          f"{c['gem5_cycles'] - c['chipyard_cycles']:+d} | "
          f"{c['chipyard_seconds']:.0f} s |")
    w("")
    w("Δ 周期 = gem5 − chipyard（正 = 模型比硬件贵）。")
    w("")

    w("## 2. 逐族拍数（周期模型 §2 的类）")
    w("")
    for c in cases:
        w(f"### `{c['bench']}`")
        w("")
        w(f"- 应用指令 {c['insts']}，chipyard {c['chipyard_cycles']} 拍"
          f"（含取指摊销，逐指令实测），gem5 {c['gem5_cycles']} 拍 = 模型 "
          f"{c['gem5_model_cycles']} + 取指/基础 {c['gem5_fetch_cycles']}；"
          f"未解析助记符 {c['unresolved_mnemonics']} 条、歧义行 {c['ambiguous_rows']} 条"
          f"（两者为 0 时逐族归因即完整；gem5 列是**额外**拍数，execute 的 1 拍记在"
          f"「取指/基础」里）")
        w("")
        w("| 族（类） | 指令数 | chipyard 拍 | chipyard/指令 | gem5 模型拍（额外） "
          "| gem5/指令 | Δ 拍 |")
        w("|---|---|---|---|---|---|---|")
        for f in sorted(c["by_family"], key=lambda s: -s["chipyard_cycles"]):
            n = f["n"] or 1
            w(f"| {f['family']} | {f['n']} | {f['chipyard_cycles']} | "
              f"{f['chipyard_cycles'] / n:.2f} | {f['gem5_cycles']} | "
              f"{f['gem5_cycles'] / n:.2f} | {f['delta']:+d} |")
        w("")

    w("## 3. 归因（比值 >1.5 的例：哪一族贡献多少）")
    w("")
    w("`Δ = gem5 − chipyard`。每例把 Δ 拆成「逐族模型差」与「gem5 取指/基础」两部分；")
    w("后者是 TimingSimpleCPU 的指令侧时序（模型之外），硬件侧没有对应项 —— chipyard 的")
    w("取指代价已经摊销在它的逐指令拍差里（这正是 §5 的测量方法）。")
    w("")
    for c in cases:
        rows = [f for f in c["by_family"] if f["delta"] != 0]
        fetch = c["gem5_fetch_cycles"]
        total_delta = c["gem5_cycles"] - c["chipyard_cycles"]
        ratio = c.get("ratio_gem5_over_chipyard")
        head = f"### `{c['bench']}`：Δ {total_delta:+d} 拍，比值 {ratio:.2f}"
        if ratio is not None and ratio > 1.5:
            head += "（>1.5，归因如下）"
        w(head)
        w("")
        tail = c["tail"]
        denom = sum(abs(f["delta"]) for f in rows) + abs(fetch) + abs(tail)
        w("| 来源 | Δ 拍 | 占 |Δ| | 每指令差异 | 归因 |")
        w("|---|---|---|---|---|")
        for f in sorted(rows, key=lambda s: -abs(s["delta"])):
            n = f["n"] or 1
            w(f"| {f['family']} | {f['delta']:+d} | "
              f"{100.0 * abs(f['delta']) / denom:.1f}% | {f['delta'] / n:+.2f} | "
              f"{attribution_note(f, n)} |")
        w(f"| gem5 取指/基础（模型外） | {fetch:+d} | "
          f"{100.0 * abs(fetch) / denom:.1f}% | {fetch / (c['insts'] or 1):+.2f} | "
          f"TimingSimpleCPU 每条指令的取指/内存时序；chipyard 侧无对应项 |")
        w(f"| chipyard 退出尾部 | {-tail:+d} | "
          f"{100.0 * abs(tail) / denom:.1f}% | {-tail / (c['insts'] or 1):+.2f} | "
          f"最后一条应用到 `SYS_EXIT` 的拍数（模型按 1 拍的 trap 计） |")
        dominant = max(list(rows) + [
            {"family": "gem5 取指/基础", "delta": fetch},
            {"family": "chipyard 退出尾部", "delta": -tail}],
            key=lambda s: abs(s["delta"]))
        w("")
        w(f"主导项：**{dominant['family']}**（{dominant['delta']:+d} 拍，"
          f"占 |Δ| 的 {100.0 * abs(dominant['delta']) / denom:.1f}%）。")
        w("")

    w("## 4. 检查（任一 FAIL 则本报告判红）")
    w("")
    w("| 例 | 检查 | 结果 | 现场值 |")
    w("|---|---|---|---|")
    for c in cases:
        for chk in c["checks"]:
            w(f"| `{c['bench']}` | {chk['check']} | {'PASS' if chk['ok'] else 'FAIL'} "
              f"| `{chk['detail']}` |")
    w("")
    fails = [f for c in cases for f in c["fails"]]
    w(f"**汇总结论：{'PASS' if not fails else 'FAIL'}**（"
      f"{sum(len(c['checks']) for c in cases)} 条检查，{len(fails)} 条 FAIL）")
    w("")

    w("## 5. 已知口径偏差（引用，属 `m16-chipyard-001` 回填项）")
    w("")
    w("- `rd2rd` 类实测 `1+N`（文档 §3 02 行写的 `1+N` 与该实测一致）；")
    w("- `ra2rd`/`rd2ra` 实测 `1+N`，而文档该行仍标「未测」⇒ 模型按 provenance 规则计 0；")
    w("- `stm` 比模型多 1 拍且零方差（`stm.o` N=8 实测 73、`stm.b` 17）。")
    w("")
    w("三条都不是本任务的修改项：本报告的 chipyard 列按**实测**呈现、gem5 列按**生成表**")
    w("呈现，因此它们只会以 `D′`/`D` 两行的差值形式出现，不做任何修补。")
    w("")

    w("## 6. 复现")
    w("")
    w("```")
    w("python3 tools/gem5/compare_chipyard.py all \\")
    w(f"    --only {','.join(c['bench'] for c in cases)} --opt {meta['opt']} \\")
    w("    --work-dir <运行期目录> --jobs 3 --max-cycles 60000000 \\")
    w("    --md docs/TestReports/M17-wuming-timing.md")
    w("```")
    w("")
    w("`build` 复用 `tests/ee-tiny/run_embench_tiny.py` 的编译行（tiny")
    w("profile + freestanding runtime），ELF 与 L2 `check-tset-embench-*` 同源；`run` 每例")
    w("跑 chipyard 一次（带 `+verbose` 轨迹）+ gem5 两次（hooks on/off）；`report` 只读")
    w("原始输出并重跑周期表门控。")
    return "\n".join(out) + "\n"


def attribution_note(f, n):
    """One-line explanation for a family's delta, from the numbers alone."""
    per = f["delta"] / n
    fam = f["family"]
    if fam == "C":
        return f"单次访存 {per:+.2f} 拍/指令（模型 1 元素 + 1 beat；硬件含背压/往返）"
    if fam in ("A3/A4", "A3", "A4"):
        return f"RAS 调用/返回 {per:+.2f} 拍/指令（模型按 RegRAS/MemRAS 取固定值）"
    if fam == "A2":
        return f"分支/跳转 {per:+.2f} 拍/指令（取指惩罚在模型里是 1 拍）"
    if fam == "D":
        return f"多元素访存 {per:+.2f} 拍/指令（元素+beat 模型 vs 硬件流水）"
    if fam == "D′":
        return f"块复制 {per:+.2f} 拍/指令（1+N 模型）"
    if fam == "B1":
        return f"乘法 {per:+.2f} 拍/指令（模型取「可配」初值 3 拍）"
    if fam == "B3":
        return f"除法/取余 {per:+.2f} 拍/指令（文档标「待实测」⇒ 模型计 0，provenance 规则）"
    if fam.startswith("B"):
        return f"FP {per:+.2f} 拍/指令（宽度分档模型）"
    if fam in ("F/G1/G2", "F", "G1", "G2"):
        return f"`trap`（semihosting）{per:+.2f} 拍/指令：硬件 1 拍 + 宿主往返，模型只计 1 拍"
    if fam == "A":
        return f"寄存器算术 {per:+.2f} 拍/指令（模型按 1 拍，硬件含取指摊销）"
    return f"{per:+.2f} 拍/指令"


def stage_report(args):
    work = Path(args.work_dir)
    manifest = read_json(work / "cases.json")
    runs = read_json(work / "runs.json")
    table, by_mnemonic = load_table()
    # The table must still be a live parse of the document: `--check`
    # regenerates both artifacts in memory and compares them byte for byte, so
    # a stale copy (or a hand-edited figure) stops the report here instead of
    # silently becoming the "model".
    gen = ROOT / "tools/gem5/gen_wuming_cycles.py"
    rc = run_cmd([sys.executable, str(gen), "--check",
                  "--source", str(ROOT / ".work/source/gem5")],
                 log_path=work / "table-check.log")
    if rc != 0:
        die(f"cycle table is not a live parse of {DOC.name} (gen --check "
            f"rc={rc}); see {work / 'table-check.log'}")
    doc_text = DOC.read_text(encoding="utf-8")
    if not doc_text.strip():
        die(f"{DOC} is empty")
    objdump_cache = {}
    cases = []
    # Observations come from `runs.json`; the *expectations* (the corpus' own
    # exit code and marker set) come from `cases.json`, i.e. from the build
    # stage that read them out of the corpus -- never from the run that is
    # being judged.
    expect = {c["bench"]: c for c in manifest["cases"]}
    wanted = ({b.strip() for b in args.only.split(",") if b.strip()}
              if args.only else None)
    for case in runs["cases"]:
        if wanted is not None and case["bench"] not in wanted:
            continue
        want = expect.get(case["bench"], {})
        case = dict(case)
        case["expected_exit"] = want.get("expected_exit", case.get("expected_exit"))
        case["markers"] = want.get("markers", [])
        cases.append(analyse_case(case, by_mnemonic, objdump_cache, table))
    graded = [c for c in cases if c.get("checks")]
    # Selection table: instruction counts of *every* built benchmark (cheap
    # gem5-only numbers) so the subset choice is a measured decision.
    # One binary per engine: a report measured across two builds would be
    # meaningless, so a disagreement stops it here (the fingerprint then names
    # the binary that actually produced the numbers, not whatever is on disk).
    binaries = {
        "chipyard": {c["chipyard_md5"] for c in cases if c.get("checks")},
        "gem5": {c["gem5_md5"] for c in cases if c.get("checks")},
    }
    many = {k: v for k, v in binaries.items() if len(v) > 1}
    if many:
        die(f"runs used more than one engine binary: {many}")
    binaries = {k: (sorted(v)[0] if v else "?") for k, v in binaries.items()}
    report = {
        "meta": {
            "generated_at": args.stamp or time.strftime(
                "%Y-%m-%d %H:%M:%S", time.gmtime()),
            "opt": runs["opt"], "table_sha": md5_of(YAML),
            "doc_sha": md5_of(DOC), "cases": [c["bench"] for c in cases],
            # fingerprints of the two engines actually used, so a report can be
            # tied to the binaries that produced it
            "host": {
                "machine": platform.machine(), "cores": os.cpu_count(),
                "chipyard_md5": binaries["chipyard"],
                "gem5_md5": binaries["gem5"],
            },
        },
        "layout": runs["layout"],
        "cases": cases,
    }
    write_json(args.out_json, report)
    md = render_report(report)
    Path(args.md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md).write_text(md, encoding="utf-8")
    fails = [f for c in cases for f in (c.get("fails") or [])]
    if not graded:
        fails.append("no case was analysed (missing engine records)")
    for line in fails:
        sys.stdout.write(f"[FAIL] {line}\n")
    sys.stdout.write(
        f"report: {len(cases)} case(s), "
        f"{sum(len(c.get('checks') or []) for c in cases)} checks, "
        f"{len(fails)} FAIL -> {args.md}\n")
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("build", "run", "report", "all"))
    ap.add_argument("--only", default="",
                    help="comma-separated embench benchmarks (build/run)")
    ap.add_argument("--opt", default="O2", help="optimisation level to build")
    ap.add_argument("--work-dir", required=True,
                    help="runtime directory for ELFs, traces and raw records")
    ap.add_argument("--out-json", default=None,
                    help="comparison JSON (default <work-dir>/compare.json)")
    ap.add_argument("--md", default=None,
                    help="markdown report to write (required by `report`)")
    ap.add_argument("--jobs", type=int, default=1,
                    help="how many cases to run concurrently")
    ap.add_argument("--engine", choices=("both", "chipyard", "gem5"),
                    default="both")
    ap.add_argument("--gem5", default=str(GEM5))
    ap.add_argument("--gem5-config", default=str(CONFIG))
    ap.add_argument("--table", default=str(YAML))
    ap.add_argument("--chipyard-sim", default=None,
                    help="Verilator harness binary (default: the component "
                         "source tree's WumingTinyConfig)")
    ap.add_argument("--max-cycles", type=int, default=200_000_000,
                    help="chipyard *core* cycle budget (the +max-cycles plusarg "
                         "gets HARNESS_CLOCKS times this); a trip is a FAIL")
    ap.add_argument("--chipyard-timeout", type=int, default=10800)
    ap.add_argument("--gem5-timeout", type=int, default=3600)
    ap.add_argument("--build-timeout", type=int, default=300)
    ap.add_argument("--max-insts", type=int, default=0,
                    help="gem5 instruction cap (0 = none; a cap hit is a FAIL)")
    ap.add_argument("--stamp", default=None,
                    help="generation stamp for the report (default: now); a "
                         "fixed stamp makes two report runs byte-identical, "
                         "which is how the evidence script proves the report "
                         "is a function of the measurements alone")
    ap.add_argument("--merge-from", default=None,
                    help="run stage: another work dir whose case records are "
                         "merged in (lets a long subset be measured in "
                         "parallel processes without losing records)")
    args = ap.parse_args()

    if args.chipyard_sim is None:
        args.chipyard_sim = str(chipyard_engine.default_sim(str(ROOT)))
    if args.out_json is None:
        args.out_json = str(Path(args.work_dir) / "compare.json")
    if args.stage in ("report", "all") and not args.md:
        die("--md is required by `report`")
    for path in (args.gem5, args.gem5_config, args.chipyard_sim, args.table):
        if not Path(path).is_file():
            die(f"missing: {path}")

    rc = 0
    if args.stage in ("build", "all"):
        rc |= stage_build(args)
    if args.stage in ("run", "all") and rc == 0:
        rc |= stage_run(args)
    if args.stage in ("report", "all") and rc == 0:
        rc |= stage_report(args)
    return rc


if __name__ == "__main__":
    sys.exit(main())
