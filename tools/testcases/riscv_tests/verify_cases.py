#!/usr/bin/env python3
"""Independent oracle / structural check for the riscv-tests port corpus.

This file deliberately does **not** import extract.py or gen.py.  It re-derives
every expected value from RISC-V semantics using a different representation
(`struct` for signed views, Python big integers) and re-checks the structural
invariants of the committed data:

  * upstream-index: exactly one row per upstream RV64 ISA file;
  * inventory: same name set, one row per file, valid class;
  * every `port` row has a case file, every non-port row has none;
  * case files: upstream path/sha256 match the index, test numbers unique;
  * expected values match the independent semantic model.

`--inject` corrupts one expected value in memory and requires the check to fail
(a check that cannot fail is not a check).

Exit: 0 PASS; 1 FAIL.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML is required\n")
    sys.exit(2)

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
BASE = os.path.join(REPO_ROOT, "tests", "riscv-tests")
CLASSES = ("port", "rewrite", "na")
MASK64 = 0xFFFFFFFFFFFFFFFF


def u64(x):
    return x & MASK64


def as_signed(x, bits):
    fmt = ">q" if bits == 64 else ">i"
    raw = struct.pack(">Q" if bits == 64 else ">I", x & ((1 << bits) - 1))
    return struct.unpack(fmt, raw)[0]


def trunc_div(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def model(op, a, b):
    """RISC-V semantics, independent implementation."""
    a = u64(a)
    b = u64(b)
    if op in ("add", "addi"):
        return u64(a + b)
    if op == "sub":
        return u64(a - b)
    if op in ("addw", "addiw"):
        return u64(as_signed(u64(a + b) & 0xFFFFFFFF, 32))
    if op == "subw":
        return u64(as_signed(u64(a - b) & 0xFFFFFFFF, 32))
    if op in ("and", "andi"):
        return a & b
    if op in ("or", "ori"):
        return a | b
    if op in ("xor", "xori"):
        return a ^ b
    if op in ("sll", "slli"):
        return u64(a << (b & 63))
    if op in ("srl", "srli"):
        return u64(a >> (b & 63))
    if op in ("sra", "srai"):
        return u64(as_signed(a, 64) >> (b & 63))
    if op in ("sllw", "slliw"):
        v = (a & 0xFFFFFFFF) << (b & 31)
        return u64(as_signed(v & 0xFFFFFFFF, 32))
    if op in ("srlw", "srliw"):
        v = (a & 0xFFFFFFFF) >> (b & 31)
        return u64(as_signed(v, 32))
    if op in ("sraw", "sraiw"):
        v = as_signed(a & 0xFFFFFFFF, 32) >> (b & 31)
        return u64(as_signed(v & 0xFFFFFFFF, 32))
    if op in ("slt", "slti"):
        return 1 if as_signed(a, 64) < as_signed(b, 64) else 0
    if op in ("sltu", "sltiu"):
        return 1 if a < b else 0
    if op == "mul":
        return u64(a * b)
    if op == "mulh":
        return u64((as_signed(a, 64) * as_signed(b, 64)) >> 64)
    if op == "mulhu":
        return u64((a * b) >> 64)
    if op in ("div", "divu"):
        if b == 0:
            return MASK64
        if op == "divu":
            return u64(a // b)
        sa, sb = as_signed(a, 64), as_signed(b, 64)
        if sa == -(1 << 63) and sb == -1:
            return u64(sa)
        return u64(trunc_div(sa, sb))
    if op in ("rem", "remu"):
        if b == 0:
            return a
        if op == "remu":
            return u64(a % b)
        sa, sb = as_signed(a, 64), as_signed(b, 64)
        if sa == -(1 << 63) and sb == -1:
            return 0
        return u64(sa - trunc_div(sa, sb) * sb)
    raise KeyError(op)


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check(inject=None, out=print) -> int:
    problems = []

    index = load_yaml(os.path.join(BASE, "upstream-index.yaml"))
    inv = load_yaml(os.path.join(BASE, "inventory.yaml"))
    files = index.get("files", [])
    entries = inv.get("entries", [])

    if len(files) != 114:
        problems.append(f"upstream-index has {len(files)} file(s), want 114")
    if len(entries) != 114:
        problems.append(f"inventory has {len(entries)} row(s), want 114")
    names = [(f["suite"], f["name"]) for f in files]
    if len(set(names)) != len(names):
        problems.append("upstream-index has duplicate (suite,name)")
    inv_names = [(e["suite"], e["name"]) for e in entries]
    if len(set(inv_names)) != len(inv_names):
        problems.append("inventory has duplicate (suite,name)")
    if set(names) != set(inv_names):
        missing = sorted(set(names) - set(inv_names))
        extra = sorted(set(inv_names) - set(names))
        problems.append(f"inventory/index name mismatch: missing={missing} "
                        f"extra={extra}")
    by_name = {(f["suite"], f["name"]): f for f in files}
    counts = {c: 0 for c in CLASSES}
    for e in entries:
        if e.get("class") not in CLASSES:
            problems.append(f"{e['suite']}/{e['name']}: bad class "
                            f"{e.get('class')!r}")
            continue
        counts[e["class"]] += 1
        expected_cases = os.path.join(BASE, e["cases"]) if e.get("cases") else None
        if e["class"] == "port":
            if not e.get("cases"):
                problems.append(f"{e['suite']}/{e['name']}: port row without "
                                f"case file")
                continue
        else:
            if e.get("cases"):
                problems.append(f"{e['suite']}/{e['name']}: non-port row must "
                                f"not name a case file")
            continue
        if not os.path.isfile(expected_cases):
            problems.append(f"{e['suite']}/{e['name']}: missing {e['cases']}")
            continue
        doc = load_yaml(expected_cases)
        want_up = f"isa/{e['suite']}/{e['name']}.S"
        if doc.get("upstream") != want_up:
            problems.append(f"{e['cases']}: upstream {doc.get('upstream')!r} "
                            f"!= {want_up!r}")
        idx = by_name.get((e["suite"], e["name"]))
        if not idx or doc.get("upstream_sha256") != idx["sha256"]:
            problems.append(f"{e['cases']}: sha256 does not match upstream-index")
        seen = set()
        for c in doc.get("cases", []):
            tn = c["testnum"]
            if tn in seen:
                problems.append(f"{e['cases']}: duplicate testnum {tn}")
            seen.add(tn)
            got = int(c["expected"], 16)
            if inject and inject == f"{e['suite']}/{e['name']}#{tn}":
                got ^= 1
            want = model(c["op"], int(c["src1"], 16), int(c["src2"], 16))
            if got != want:
                problems.append(
                    f"{e['cases']} test {tn} ({c['op']}): expected "
                    f"0x{got:016x} != oracle 0x{want:016x}")

    declared = {e["cases"] for e in entries if e.get("cases")}
    on_disk = {os.path.relpath(os.path.join(dp, fn), BASE)
               for dp, _, fns in os.walk(os.path.join(BASE, "cases"))
               for fn in fns if fn.endswith(".yaml")}
    if declared != on_disk:
        problems.append(f"case file set mismatch: undeclared={sorted(on_disk - declared)} "
                        f"missing={sorted(declared - on_disk)}")

    for p in problems:
        out(f"[FAIL] {p}")
    if problems:
        out(f"verify_cases: FAIL ({len(problems)} problem(s))")
        return 1
    out(f"verify_cases: PASS (114 upstream file(s); "
        f"port={counts['port']} rewrite={counts['rewrite']} na={counts['na']})")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inject", default=None,
                    help="suite/name#testnum whose expected value is flipped "
                         "in memory; the check must then fail")
    args = ap.parse_args(argv)
    return check(inject=args.inject)


if __name__ == "__main__":
    sys.exit(main())
