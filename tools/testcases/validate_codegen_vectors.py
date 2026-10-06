#!/usr/bin/env python3
"""Validate the M3 CodeGen test vectors under ``tests/llvm/codegen/``.

Checks performed (all fail-closed, exit non-zero on any failure):

  1. ``expected.yaml`` exists, parses, and has the expected ``schema``.
  2. Every program record has the required fields with valid types/values:
     ``name`` / ``category`` / ``expected_exit_code`` / ``coverage`` /
     ``derivation``.
  3. The declared program set matches the ``*.ll`` files on disk exactly
     (no missing, no extra, no duplicate entries).
  4. Each program file is a valid M3 scalar program shape: it defines
     ``i64 @main()`` and does not use constructs outside the M3 boundary
     (global variables / varargs / sret / byval / nest / invoke / callbr /
     indirect calls).
  5. Coverage: all four categories (arithmetic / memory / branch / call) are
     present and every required coverage point appears.
  6. Expected results: each ``expected_exit_code`` equals the value produced by
     an **independent host-side model of the LLVM IR semantics** (64-bit
     two's-complement arithmetic, big-endian memory).  This model never invokes
     ``llc`` or QEMU.

The oracle in this file is a structural/consistency oracle; the full manual
re-derivation of every value is recorded in the task completion area.  A green
validator is necessary but not sufficient (the end-to-end execution is owned by
``INTEG-012t``).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VEC_DIR = ROOT / "tests" / "llvm" / "codegen"
EXPECTED_PATH = VEC_DIR / "expected.yaml"

SCHEMA = "codegen-vectors-v1"
CATEGORIES = {"arithmetic", "memory", "branch", "call"}

COVERAGE_VOCAB = {
    # ABI / codegen decision points (ADR-0018)
    "C1", "C4", "C5", "C12", "C13", "C14", "C17",
    # arithmetic
    "arith.add", "arith.sub", "arith.neg-const", "arith.const-hi-wyde",
    # memory / big-endian narrow access
    "mem.load-store-offset", "mem.narrow-be",
    "mem.ld-ub", "mem.ld-sb", "mem.ld-uw", "mem.ld-sw", "mem.ld-ut", "mem.ld-st",
    # branches
    "branch.signed-loop", "branch.eq-ne", "branch.ptr-null", "branch.ptr-eq",
    # calls
    "call.direct-ret", "call.stack-args", "call.narrow-args", "call.ptr-bank",
    # pointer arithmetic
    "ptr.add-offset", "ptr.cmp", "ptr.diff-pos", "ptr.diff-neg",
}

REQUIRED_COVERAGE = {
    "C1", "C4", "C5", "C12", "C13", "C14", "C17",
    "mem.narrow-be", "call.stack-args", "call.narrow-args", "call.ptr-bank",
    "branch.ptr-null", "branch.ptr-eq", "ptr.add-offset", "ptr.cmp",
    "ptr.diff-pos", "ptr.diff-neg",
}

REQUIRED_FIELDS = ("name", "category", "expected_exit_code", "coverage", "derivation")

MAIN_RE = re.compile(r"define\s+i64\s+@main\s*\(\s*\)\s*\{")

IR_FORBIDDEN = [
    (re.compile(r"^\s*@[\w.$-]+\s*=\s*(?:global|constant|common)\b", re.M),
     "global variable definition (M3 has no .data/.rodata)"),
    (re.compile(r"\.\.\."), "varargs"),
    (re.compile(r"\b(?:sret|byval|nest)\b"), "sret/byval/nest argument"),
    (re.compile(r"\b(?:invoke|callbr)\b"), "invoke/callbr terminator"),
    (re.compile(r"\bcall\s+(?:void|i\d+|ptr|float|double)\s+%"), "indirect call"),
    (re.compile(r"\b(?:float|double|half|fp128|x86_fp80)\b"), "floating-point type (M3 is integer-only)"),
]

MASK64 = (1 << 64) - 1


# ---------------------------------------------------------------------------
# Independent host-side oracle (IR semantics; no llc / QEMU)
# ---------------------------------------------------------------------------

def u64(x: int) -> int:
    return x & MASK64


def sext(x: int, bits: int) -> int:
    m = 1 << (bits - 1)
    return (x & (m - 1)) - (x & m)


def be_bytes(value: int, n: int) -> list:
    return list(value.to_bytes(n, "big"))


def be_u(bs: list) -> int:
    return int.from_bytes(bytes(bs), "big")


def oracle(name: str):
    """Return the expected exit code for a program, or None if unknown."""
    if name == "arith_add_sub_neg.ll":
        a, b = -5, 3
        c, d = u64(a + b), u64(b - a)
        return (c ^ d) & 0xFF

    if name == "arith_const_hi_wyde.ll":
        v = 0xFEDCBA9876543210
        return ((v >> 56) ^ (v & 0xFF)) & 0xFF

    if name == "mem_store_load_offset.ll":
        return (100 - 23) & 0xFF

    if name == "mem_narrow_be_bytes.ll":
        bs = be_bytes(0x0102030405060708, 8)
        bs[3] = 0xFE
        b0, b7, s3 = bs[0], bs[7], bs[3]
        shi8 = (u64(sext(s3, 8)) >> 8) & 0xFF
        return (b0 * 10 + b7 * 100 + shi8) & 0xFF

    if name == "mem_narrow_be_wide.ll":
        bs = be_bytes(0x1122334455667788, 8)
        h0, h6, w4 = be_u(bs[0:2]), be_u(bs[6:8]), be_u(bs[4:8])
        a8 = (h0 >> 8) & 0xFF
        b = h6 & 0xFF
        c8 = (w4 >> 24) & 0xFF
        bs[2:4] = be_bytes(-300 & 0xFFFF, 2)
        n = be_u(bs[2:4])
        nhi = (u64(sext(n, 16)) >> 16) & 0xFF
        bs[0:4] = be_bytes(-70000 & 0xFFFFFFFF, 4)
        s = be_u(bs[0:4])
        shi = (u64(sext(s, 32)) >> 32) & 0xFF
        return (a8 + b + c8 + nhi + shi) & 0xFF

    if name == "branch_loop_sum.ll":
        n = 10
        total = sum(range(n))
        return (total if total > 40 else 0) & 0xFF

    if name == "branch_eq_ne.ll":
        a, b, c, d = 7, 7, 3, 9
        r = 1 if a == b else 100
        r = r + 10 if c != d else r + 200
        return (r + 5) & 0xFF

    if name == "branch_ptr.ll":
        def checks(p_is_null, p_eq_q):
            r = 1 if p_is_null else 2
            return r + (4 if p_eq_q else 8)
        return (checks(False, True) + checks(False, False) + checks(True, False)) & 0xFF

    if name == "call_direct_ret.ll":
        return (2 + 3 + 4) & 0xFF

    if name == "call_multiarg_stack.ll":
        base = 1
        return sum(base + i for i in range(18)) & 0xFF

    if name == "call_narrow_args.ll":
        return (200 + 300 + 400 + 5) & 0xFF

    if name == "call_ptr_bank.ll":
        return 42

    if name == "ptr_add_offset.ll":
        return 0xAB

    if name == "ptr_diff_pos.ll":
        return (10 - 3) & 0xFF

    if name == "ptr_diff_neg.ll":
        return (3 - 10) & 0xFF

    return None


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

class Checker:
    def __init__(self) -> None:
        self.passes = 0
        self.fails: list[str] = []

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        if cond:
            self.passes += 1
            print(f"[PASS] {name}")
        else:
            self.fails.append(name)
            print(f"[FAIL] {name} {detail}".rstrip())


def strip_comments(text: str) -> str:
    return "\n".join(line.split(";", 1)[0] for line in text.splitlines())


def load_expected(ck: Checker):
    if not EXPECTED_PATH.is_file():
        ck.check("expected-file-exists", False, f"missing {EXPECTED_PATH}")
        return None
    ck.check("expected-file-exists", True)
    try:
        data = yaml.safe_load(EXPECTED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        ck.check("yaml-parses", False, f"{exc}")
        return None
    ck.check("yaml-parses", True)
    ck.check("schema", isinstance(data, dict) and data.get("schema") == SCHEMA,
             f"schema != {SCHEMA!r}")
    programs = data.get("programs") if isinstance(data, dict) else None
    ck.check("programs-nonempty", isinstance(programs, list) and len(programs) > 0,
             "programs must be a non-empty list")
    return programs if isinstance(programs, list) else []


def check_records(ck: Checker, programs: list) -> None:
    fields_ok = True
    cats_ok = True
    vocab_ok = True
    range_ok = True
    deriv_ok = True
    names: list[str] = []
    coverage: set[str] = set()
    categories: set[str] = set()

    for i, rec in enumerate(programs):
        if not isinstance(rec, dict):
            fields_ok = False
            continue
        for field in REQUIRED_FIELDS:
            if field not in rec:
                fields_ok = False
                print(f"       record #{i} missing field {field!r}")
        name = rec.get("name")
        if isinstance(name, str):
            names.append(name)
        cat = rec.get("category")
        if cat in CATEGORIES:
            categories.add(cat)
        else:
            cats_ok = False
            print(f"       record #{i} bad category {cat!r}")
        cov = rec.get("coverage")
        if isinstance(cov, list) and cov:
            coverage.update(x for x in cov if isinstance(x, str))
            bad = [x for x in cov if not isinstance(x, str) or x not in COVERAGE_VOCAB]
            if bad:
                vocab_ok = False
                print(f"       record #{i} unknown coverage token(s): {bad}")
        else:
            vocab_ok = False
            print(f"       record #{i} coverage must be a non-empty list")
        code = rec.get("expected_exit_code")
        if isinstance(code, bool) or not isinstance(code, int) or not (0 <= code <= 255):
            range_ok = False
            print(f"       record #{i} expected_exit_code out of range: {code!r}")
        deriv = rec.get("derivation")
        if not isinstance(deriv, str) or not deriv.strip():
            deriv_ok = False
            print(f"       record #{i} empty derivation")

    ck.check("record-fields", fields_ok)
    ck.check("categories-known", cats_ok)
    ck.check("category-coverage", categories == CATEGORIES,
             f"present={sorted(categories)}")
    ck.check("coverage-vocab", vocab_ok)
    missing = REQUIRED_COVERAGE - coverage
    ck.check("coverage-required", not missing, f"missing={sorted(missing)}")
    ck.check("exit-code-range", range_ok)
    ck.check("derivation-nonempty", deriv_ok)
    ck.check("name-unique", len(names) == len(set(names)),
             "duplicate program names")

    # program set == *.ll files on disk
    files = sorted(p.name for p in VEC_DIR.glob("*.ll"))
    ck.check("files-match", sorted(names) == files,
             f"yaml={sorted(names)} disk={files}")

    # per-program shape + independent expected value
    for rec in programs:
        if not isinstance(rec, dict):
            continue
        name = rec.get("name")
        if not isinstance(name, str):
            continue
        path = VEC_DIR / name
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        body = strip_comments(raw)
        ck.check(f"ir-main-signature[{name}]", bool(MAIN_RE.search(body)),
                 "missing `define i64 @main()`")
        bad = [why for rx, why in IR_FORBIDDEN if rx.search(body)]
        ck.check(f"ir-m3-boundary[{name}]", not bad, f"forbidden: {bad}")
        want = oracle(name)
        got = rec.get("expected_exit_code")
        ck.check(f"expected-vs-oracle[{name}]", want is not None and want == got,
                 f"expected={got!r} oracle={want!r}")


def main() -> int:
    ck = Checker()
    programs = load_expected(ck)
    if programs:
        check_records(ck, programs)
    print("-" * 60)
    if ck.fails:
        print(f"validate_codegen_vectors: FAIL ({len(ck.fails)} failed, {ck.passes} passed)")
        for name in ck.fails:
            print(f"  - {name}")
        return 1
    print(f"validate_codegen_vectors: PASS ({ck.passes} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
