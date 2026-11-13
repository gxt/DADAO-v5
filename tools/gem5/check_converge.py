#!/usr/bin/env python3
"""Single convergence gate: all 264 DADAO ids, all 7 batches (GEM5-013t).

Run it directly (``python3 tools/gem5/check_converge.py``); it is not hooked to
a Makefile target yet (see the task book, open point 1).

Checks, in order (any failure -> rc=1, each step prints its real rc/counts):

1. ``gen_decode_table.py --check`` -- the B0 table is not stale;
2. ``make check-gem5-decode`` -- B0 264/264 + 388/388 + 28/28 + 2/2, 0 fail;
3. contract / decode table / semantic matrix id sets are equal (two-way) and
   the live ``batch_of()`` counts are the 7 published batch counts;
4. ``converge_words.inc`` + ``converge_test.cc`` -- 264/264 ids decode to their
   own id, the owner batch neither returns NotB* nor Illegal, the other six
   batches return exactly their NotB* with zero side effects (1848/1848);
5. ``check_b1..b7`` -- per-batch [PASS] counts equal the frozen baselines, no
   [FAIL], and the bN-id lines cover the 264 ids once each;
6. structural: ``inst.cc`` has exactly one UnimplementedInstruction (inside the
   batch guard) and one dispatchBatch call; ``dispatch.cc`` has exactly seven
   cases, each calling its own executeBk; no other file calls another batch's
   core;
7. ``refresh_matrix_notes.py --check`` -- the 44 old notes / 12 sc exceptions /
   2 scaleB fields are refreshed and nothing else moved.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / ".tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv"
OPCODES = ROOT / "contracts/opcodes.yaml"

# Frozen per-batch [PASS] baselines (GEM5-006t..GEM5-012t, re-measured
# 2026-11-02 before this task).  A drop here is a regression, never a change of
# expectation.  b1 re-frozen 2026-11-13 (m13-gem5-008 adds the ldm
# address-register-overlap assertions).
PASS_BASELINE = {1: 2156, 2: 1160, 3: 4248, 4: 3696, 5: 1215, 6: 1362,
                 7: 2979}
DECODE_BASELINE = {"positive": 264, "negative": 388, "legality": 28,
                   "legacy": 2}

CONVERGE_ID = re.compile(r"^\[PASS\] converge-id (\S+)$", re.MULTILINE)
CONVERGE_SUMMARY = re.compile(
    r"^summary: ids (\d+)/(\d+), boundary (\d+)/(\d+), failures (\d+)$",
    re.MULTILINE)
DECODE_SUMMARY = re.compile(
    r"positive (\d+)/(\d+), negative (\d+)/(\d+), legality (\d+)/(\d+), "
    r"legacy (\d+)/(\d+), failures (\d+)")
MATRIX_SUMMARY = re.compile(
    r"notes (\d+) \[lr (\d+) / sc (\d+) / f2i (\d+) / arith (\d+)\], "
    r"sc exceptions (\d+), sclb fields (\d+), rows (\d+), columns (\d+)")
COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)


class Gate:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, ok: bool, name: str, detail: str = "") -> bool:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"
              + (f" -- {detail}" if detail else ""))
        if not ok:
            self.failures += 1
        return ok

    def fail(self, name: str, detail: str) -> None:
        self.check(False, name, detail)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"check-gem5-converge: cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text)


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    print(f"check-gem5-converge: run: {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def two_way_diff(name: str, a: set[str], b: set[str], gate: Gate) -> None:
    only_a = sorted(a - b)
    only_b = sorted(b - a)
    gate.check(not only_a and not only_b, name,
               f"{len(a)} vs {len(b)} ids" +
               (f"; only-left {only_a[:5]}" if only_a else "") +
               (f"; only-right {only_b[:5]}" if only_b else ""))


# ---------------------------------------------------------------------------
# 1-3: B0 table, decode gate, three-way id agreement
# ---------------------------------------------------------------------------
def checks_decode(source: Path, gate: Gate) -> tuple[list, dict[str, int]]:
    gdt = load_module("gen_decode_table", ROOT / "tools/gem5/gen_decode_table.py")

    proc = run([sys.executable, "tools/gem5/gen_decode_table.py", "--check",
                "--source", str(source)])
    counts = {name: int(value) for name, value in
              re.findall(r"'(B\d)': (\d+)", proc.stdout)}
    gate.check(proc.returncode == 0 and "264 rows" in proc.stdout,
               "gen_decode_table --check",
               f"rc={proc.returncode}, batches {counts}")

    proc = run(["make", "check-gem5-decode"])
    match = DECODE_SUMMARY.search(proc.stdout)
    ok = proc.returncode == 0 and match is not None
    detail = f"rc={proc.returncode}"
    if match is not None:
        values = [int(x) for x in match.groups()]
        got = {"positive": values[0], "negative": values[2],
               "legality": values[4], "legacy": values[6]}
        ok = ok and got == DECODE_BASELINE and values[8] == 0
        detail += (", " + " ".join(f"{k} {v}/{DECODE_BASELINE[k]}"
                                   for k, v in got.items()) +
                   f", failures {values[8]}")
    else:
        detail += ", summary line missing"
    gate.check(ok, "make check-gem5-decode (B0)", detail)

    # Three-way id set agreement, all sides live.
    import yaml  # noqa: F401  (fail early with a clear message if missing)
    contract = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    contract_ids = {row["id"] for row in contract}
    entries = gdt.load_entries()
    decode_ids = {entry.id for entry in entries}
    with MATRIX.open(newline="", encoding="utf-8") as stream:
        matrix_ids = {row["id"] for row in csv.DictReader(stream, delimiter="\t")}

    gate.check(len(contract_ids) == 264 and len(decode_ids) == 264 and
               len(matrix_ids) == 264, "id set sizes",
               f"contract {len(contract_ids)}, decode {len(decode_ids)}, "
               f"matrix {len(matrix_ids)}")
    two_way_diff("contract == decode table", contract_ids, decode_ids, gate)
    two_way_diff("contract == semantic matrix", contract_ids, matrix_ids, gate)

    live = {name: 0 for name in gdt.BATCH_COUNTS}
    for entry in entries:
        live[entry.batch] = live.get(entry.batch, 0) + 1
    gate.check(live == gdt.BATCH_COUNTS and sum(live.values()) == 264,
               "batch_of() counts", f"{live}, sum {sum(live.values())}")
    gate.check("B0" not in live and "B8" not in live,
               "no batch 0 / batch 8 ids", f"{sorted(live)}")
    return entries, live


# ---------------------------------------------------------------------------
# 4: converge harness (dispatch + 1848 boundaries)
# ---------------------------------------------------------------------------
def check_converge_harness(source: Path, entries, cxx: str,
                           gate: Gate) -> None:
    words = ROOT / ".work/build/gem5/converge_words.inc"
    proc = run([sys.executable, "tools/gem5/gen_converge_words.py", "--out",
                str(words)])
    gate.check(proc.returncode == 0 and words.exists(),
               "gen_converge_words.py", f"rc={proc.returncode}")
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        return

    exe = ROOT / ".work/build/gem5/dadao-converge-test"
    exe.parent.mkdir(parents=True, exist_ok=True)
    arch = source / "src/arch/dadao"
    cmd = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
           "-I", str(source / "src"), "-I", str(words.parent),
           str(arch / "decode/decode.cc")]
    cmd += [str(arch / f"exec/b{n}.cc") for n in range(1, 8)]
    cmd += [str(arch / "exec/fp_soft.cc"), str(arch / "exec/dispatch.cc"),
            str(arch / "exec/converge_test.cc"), "-o", str(exe)]
    built = run(cmd)
    gate.check(built.returncode == 0, "converge harness compile",
               f"rc={built.returncode}")
    if built.returncode != 0:
        print(built.stdout[-4000:], file=sys.stderr)
        print(built.stderr[-4000:], file=sys.stderr)
        return

    proc = run([str(exe)])
    harness_ids = sorted(set(CONVERGE_ID.findall(proc.stdout)))
    match = CONVERGE_SUMMARY.search(proc.stdout)
    detail = f"rc={proc.returncode}"
    ok = proc.returncode == 0 and match is not None
    if match is not None:
        ids_ok, ids_total, bound_ok, bound_total, failures = (
            int(x) for x in match.groups())
        ok = ok and ids_ok == 264 and ids_total == 264 and \
            bound_ok == 1848 and bound_total == 1848 and failures == 0
        detail += (f", ids {ids_ok}/{ids_total}, boundary "
                   f"{bound_ok}/{bound_total}, failures {failures}")
    else:
        detail += ", summary line missing"
    for line in proc.stdout.splitlines():
        if line.startswith("[FAIL]"):
            print(f"  harness: {line}", file=sys.stderr)
    gate.check(ok, "converge harness (dispatch + 1848 boundaries)", detail)

    live_ids = {entry.id for entry in entries}
    two_way_diff("converge ids == contract ids", set(harness_ids), live_ids,
                 gate)
    gate.check(len(harness_ids) == 264, "converge id line count",
               f"{len(harness_ids)}/264")


# ---------------------------------------------------------------------------
# 5: B1-B7 zero regression + per-batch id partition
# ---------------------------------------------------------------------------
def check_batches(gate: Gate) -> None:
    seen: dict[str, int] = {}
    for n in range(1, 8):
        proc = run([sys.executable, f"tools/gem5/check_b{n}.py"])
        passes = proc.stdout.count("[PASS]")
        fails = proc.stdout.count("[FAIL]") + proc.stderr.count("[FAIL]")
        ids = re.findall(rf"^\[PASS\] b{n}-id (\S+)$", proc.stdout,
                         re.MULTILINE)
        ok = (proc.returncode == 0 and fails == 0 and
              passes == PASS_BASELINE[n] and len(set(ids)) == len(ids))
        gate.check(ok, f"check_b{n}", f"rc={proc.returncode}, [PASS] "
                   f"{passes}/{PASS_BASELINE[n]}, [FAIL] {fails}, "
                   f"ids {len(ids)}")
        for entry_id in ids:
            if entry_id in seen:
                gate.fail("batch partition",
                          f"{entry_id} listed by B{seen[entry_id]} and B{n}")
            seen[entry_id] = n
    gate.check(len(seen) == 264, "bN-id union", f"{len(seen)}/264")


# ---------------------------------------------------------------------------
# 6: structural assertions on inst.cc / dispatch.cc
# ---------------------------------------------------------------------------
def check_structure(source: Path, gate: Gate) -> None:
    arch = source / "src/arch/dadao"
    inst = strip_comments((arch / "inst.cc").read_text(encoding="utf-8"))
    dispatch = strip_comments((arch / "exec/dispatch.cc")
                              .read_text(encoding="utf-8"))

    # The single UnimplementedInstruction construction, inside the batch guard.
    positions = [m.start() for m in
                 re.finditer(r"UnimplementedInstruction", inst)]
    guard = re.search(r"if\s*\(\s*batch\s*<\s*1\s*\|\|\s*batch\s*>\s*7\s*\)\s*\{",
                      inst)
    inside = False
    if guard is not None:
        depth = 0
        for idx in range(guard.end() - 1, len(inst)):
            if inst[idx] == "{":
                depth += 1
            elif inst[idx] == "}":
                depth -= 1
                if depth == 0:
                    end = idx
                    break
        else:
            end = -1
        inside = all(guard.start() <= pos <= end for pos in positions)
    gate.check(len(positions) == 1 and guard is not None and inside,
               "inst.cc: exactly one UnimplementedInstruction, inside the "
               "batch guard",
               f"{len(positions)} occurrence(s), guard={'yes' if guard else 'no'},"
               f" inside={inside}")

    calls = len(re.findall(r"\bdispatchBatch\s*\(", inst))
    gate.check(calls == 1, "inst.cc: exactly one dispatchBatch() call",
               f"{calls} call(s)")

    # dispatch.cc: seven cases, one per core, plus the unreachable default.
    cases = re.findall(r"case\s+(\d+)\s*:", dispatch)
    gate.check(sorted(int(c) for c in cases) == list(range(1, 8)),
               "dispatch.cc: seven cases", f"{sorted(int(c) for c in cases)}")
    body = re.split(r"case\s+\d+\s*:", dispatch)
    per_case_ok = True
    for index, chunk in enumerate(body[1:], start=1):
        chunk = chunk.split("default:")[0]
        if not re.search(rf"\bexecuteB{index}\s*\(", chunk):
            per_case_ok = False
            gate.fail("dispatch.cc: case -> core",
                      f"case {index} does not call executeB{index}")
    gate.check(per_case_ok, "dispatch.cc: each case calls its own core")
    gate.check(re.search(r"default\s*:\s*__builtin_unreachable\s*\(\s*\)",
                         dispatch) is not None,
               "dispatch.cc: default is __builtin_unreachable()")

    # No other file may call another batch's core.
    cross_ok = True
    own = re.compile(r"exec/b(\d)\.(?:cc|hh)$")
    for path in sorted(arch.rglob("*")):
        if not path.is_file() or path.suffix not in (".cc", ".hh", ".inc"):
            continue
        rel = path.relative_to(arch)
        text = strip_comments(path.read_text(encoding="utf-8"))
        for match in re.finditer(r"\bexecuteB(\d)\s*\(", text):
            k = int(match.group(1))
            if rel.as_posix() == "exec/dispatch.cc" or path.name.endswith(
                    "_test.cc"):
                continue
            owned = own.search(rel.as_posix())
            if owned is not None and int(owned.group(1)) == k:
                continue  # the core's own definition
            cross_ok = False
            gate.fail("executeB* call scope",
                      f"{rel} calls executeB{k}")
    gate.check(cross_ok, "executeB* only in dispatch.cc / own core / tests")


# ---------------------------------------------------------------------------
# 7: matrix notes refresh
# ---------------------------------------------------------------------------
def check_matrix(gate: Gate) -> None:
    proc = run([sys.executable, "tools/gem5/refresh_matrix_notes.py",
                "--check"])
    match = MATRIX_SUMMARY.search(proc.stdout)
    ok = proc.returncode == 0 and match is not None
    detail = f"rc={proc.returncode}"
    if match is not None:
        notes, lr, sc, f2i, arith, exceptions, sclb, rows, columns = (
            int(x) for x in match.groups())
        ok = ok and notes == 44 and lr == 12 and sc == 12 and f2i == 8 and \
            arith == 12 and exceptions == 12 and sclb == 2 and rows == 264 and \
            columns == 29
        detail += (f", notes {notes} (lr {lr}/sc {sc}/f2i {f2i}/arith {arith}), "
                   f"sc exceptions {exceptions}, sclb {sclb}, rows {rows}, "
                   f"columns {columns}")
    else:
        detail += ", summary line missing"
        print(proc.stderr[-2000:], file=sys.stderr)
    gate.check(ok, "refresh_matrix_notes --check", detail)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()
    source = args.source if args.source.is_absolute() else ROOT / args.source

    needed = [source / "src/arch/dadao/inst.cc",
              source / "src/arch/dadao/exec/dispatch.cc",
              source / "src/arch/dadao/exec/converge_test.cc"]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-converge: missing input(s); run `make apply-series` "
              "first:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    gate = Gate()
    entries, live = checks_decode(source, gate)
    check_converge_harness(source, entries, args.cxx, gate)
    check_batches(gate)
    check_structure(source, gate)
    check_matrix(gate)

    if gate.failures:
        print(f"check-gem5-converge: FAIL ({gate.failures} failed check(s))")
        return 1
    print("check-gem5-converge: PASS (ids 264/264, boundary 1848/1848, "
          "batches " + " ".join(f"B{n}={live[f'B{n}']}" for n in range(1, 8)) +
          ", matrix 44 notes / 12 sc exceptions / 2 sclb fields)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
