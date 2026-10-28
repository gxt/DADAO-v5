#!/usr/bin/env python3
"""Validate the M3 CodeGen test vectors under ``tests/unit/llvm/codegen/``.

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
     ``llc`` or QEMU.  Every expected code must lie in ``0x00..0x7F`` so it can
     never collide with a machine-fault code (``0x80..0xFF``; ADR-0004
     D5.7/D5.8; ISS-147).

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
VEC_DIR = ROOT / "tests" / "unit" / "llvm" / "codegen"
EXPECTED_PATH = VEC_DIR / "expected.yaml"

SCHEMA = "codegen-vectors-v1"
CATEGORIES = {"arithmetic", "memory", "branch", "call"}

COVERAGE_VOCAB = {
    # ABI / codegen decision points (ADR-0018)
    "C1", "C4", "C5", "C12", "C13", "C14", "C17",
    # arithmetic
    "arith.add", "arith.sub", "arith.neg-const", "arith.const-hi-wyde",
    "arith.i64-shift", "shift.imm-orri", "shift.register",
    "arith.narrow-extend", "ext.canonical-sext", "ext.canonical-zext",
    # memory / big-endian narrow access
    "mem.load-store-offset", "mem.narrow-be",
    "mem.ld-ub", "mem.ld-sb", "mem.ld-uw", "mem.ld-sw", "mem.ld-ut", "mem.ld-st",
    # branches
    "branch.signed-loop", "branch.eq-ne", "branch.ptr-null", "branch.ptr-eq",
    # calls
    "call.direct-ret", "call.stack-args", "call.narrow-args", "call.ptr-bank",
    # pointer arithmetic
    "ptr.add-offset", "ptr.cmp", "ptr.diff-pos", "ptr.diff-neg",
    # loop-carried pointer induction (LLVM-139t)
    "ptr.loop-bank",
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
    """Return the expected exit code for a program, or None if unknown.

    Every program masks its raw IR result with 127, so the guest exit code is
    always in 0x00..0x7F (ISS-147: clear of the machine-fault range 0x80..0xFF).
    """
    if name == "arith_add_sub_neg.ll":
        a, b = -5, 3
        c, d = u64(a + b), u64(b - a)
        return (c ^ d) & 0x7F

    if name == "arith_const_hi_wyde.ll":
        v = 0xFEDCBA9876543210
        return ((v >> 56) ^ (v & 0xFF)) & 0x7F

    if name == "mem_store_load_offset.ll":
        return (100 - 23) & 0x7F

    if name == "mem_narrow_be_bytes.ll":
        bs = be_bytes(0x0102030405060708, 8)
        bs[3] = 0xFE
        b0, b7, s3 = bs[0], bs[7], bs[3]
        shi8 = (u64(sext(s3, 8)) >> 8) & 0xFF
        return (b0 * 10 + b7 * 100 + shi8) & 0x7F

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
        return (a8 + b + c8 + nhi + shi) & 0x7F

    if name == "branch_loop_sum.ll":
        n = 10
        total = sum(range(n))
        return (total if total > 40 else 0) & 0x7F

    if name == "branch_eq_ne.ll":
        a, b, c, d = 7, 7, 3, 9
        r = 1 if a == b else 100
        r = r + 10 if c != d else r + 200
        return (r + 5) & 0x7F

    if name == "branch_ptr.ll":
        def checks(p_is_null, p_eq_q):
            r = 1 if p_is_null else 2
            return r + (4 if p_eq_q else 8)
        return (checks(False, True) + checks(False, False) + checks(True, False)) & 0x7F

    if name == "call_direct_ret.ll":
        return (2 + 3 + 4) & 0x7F

    if name == "call_multiarg_stack.ll":
        base = 1
        return sum(base + i for i in range(18)) & 0x7F

    if name == "call_narrow_args.ll":
        return (200 + 300 + 400 + 5) & 0x7F

    if name == "call_ptr_bank.ll":
        return 42

    if name == "ptr_add_offset.ll":
        return 0xAB & 0x7F

    if name == "ptr_diff_pos.ll":
        return (10 - 3) & 0x7F

    if name == "ptr_diff_neg.ll":
        return (3 - 10) & 0x7F

    if name == "m10-loop-pointer-bank.ll":
        # @walk_sum: p <- (p + 2) + i elements, element j holds 3*j + 1.
        # Count the mismatching sums for the two trip counts (n = 5, n = 3).
        def walk(n):
            p, total = 0, 0
            for i in range(n):
                total += 3 * p + 1
                p = (p + 2) + i
            return total
        return (walk(5) != 95) + (walk(3) != 24)

    if name == "m10-i64-shift.ll":
        # 18 comparisons: shl/lshr/ashr by {0,1,31,32,63} + variable n=37.
        def s64(x):
            x &= MASK64
            return x - (1 << 64) if x & (1 << 63) else x

        a, b, n = 0x0123456789ABCDEF, 0xFEDCBA9876543210, 37
        amounts = (0, 1, 31, 32, 63)
        want_shl = (0x0123456789ABCDEF, 0x02468ACF13579BDE,
                    0xC4D5E6F780000000, 0x89ABCDEF00000000,
                    0x8000000000000000)
        want_lshr = (0xFEDCBA9876543210, 0x7F6E5D4C3B2A1908,
                     0x00000001FDB97530, 0x00000000FEDCBA98,
                     0x0000000000000001)
        want_ashr = (0xFEDCBA9876543210, 0xFF6E5D4C3B2A1908,
                     0xFFFFFFFFFDB97530, 0xFFFFFFFFFEDCBA98,
                     0xFFFFFFFFFFFFFFFF)
        got = []
        for k in amounts:
            got.append((a << k) & MASK64)
        for k in amounts:
            got.append((b >> k) & MASK64)
        for k in amounts:
            got.append(u64(s64(b) >> k))
        got += [u64(a << n), u64(b >> n), u64(s64(b) >> n)]
        expected = list(want_shl) + list(want_lshr) + list(want_ashr)
        expected += [0x3579BDE000000000, 0x000000007F6E5D4,
                     0xFFFFFFFFFFF6E5D4]
        return sum(1 for x, y in zip(got, expected) if x != y)

    if name == "m10-narrow-extend.ll":
        def sdiv_trunc(x, y):
            q = abs(x) // abs(y)
            return -q if (x < 0) != (y < 0) else q

        def srem_trunc(x, y):
            return x - sdiv_trunc(x, y) * y

        def sx(x, bits):
            return sext(x, bits)

        def zx(x, bits):
            return x & ((1 << bits) - 1)

        cases = []
        # (width, op, a, b, sign_extend)
        cases += [(8, 'add', 127, 127, True)]
        cases += [(8, 'add', 127, 127, False)]
        cases += [(16, 'add', 32767, 1, False)]
        cases += [(32, 'sub', 0, 5, True)]
        cases += [(16, 'sub', 1, 32768, False)]
        cases += [(32, 'mul', 2147483648, 4294967295, True)]
        cases += [(16, 'mul', 65535, 3, False)]
        cases += [(8, 'udiv', 200, 7, False)]
        cases += [(32, 'urem', 4294967295, 7, False)]
        cases += [(8, 'sdiv', 128, 3, True)]
        cases += [(16, 'srem', 35536, 7, True)]
        cases += [(8, 'shl', 64, 1, False)]
        cases += [(32, 'shl', 1073741824, 1, False)]
        cases += [(16, 'lshr', 32768, 4, False)]
        cases += [(8, 'ashr', 128, 1, True)]
        cases += [(32, 'ashr', 2147483648, 31, True)]
        expected = [(-2 & MASK64), 0xFE, 0x8000,
                    (-5 & MASK64), 0x8001,
                    (-2147483648 & MASK64), 0xFFFD, 0x1C, 3,
                    (-42 & MASK64), (-5 & MASK64), 0x80,
                    0x80000000, 0x800, (-64 & MASK64),
                    (MASK64)]
        got = []
        for width, op, a, b, sign in cases:
            mask = (1 << width) - 1
            if op == 'add':
                r = (a + b) & mask
            elif op == 'sub':
                r = (a - b) & mask
            elif op == 'mul':
                r = (a * b) & mask
            elif op == 'udiv':
                r = (a & mask) // (b & mask)
            elif op == 'urem':
                r = (a & mask) % (b & mask)
            elif op == 'sdiv':
                r = sdiv_trunc(sx(a, width), sx(b, width)) & mask
            elif op == 'srem':
                r = srem_trunc(sx(a, width), sx(b, width)) & mask
            elif op == 'shl':
                r = (a << (b & (width - 1))) & mask
            elif op == 'lshr':
                r = (a & mask) >> (b & (width - 1))
            elif op == 'ashr':
                r = (sx(a, width) >> (b & (width - 1))) & mask
            else:
                return None
            got.append(u64(sx(r, width) if sign else r))
        return sum(1 for x, y in zip(got, expected) if x != y)

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
        if isinstance(code, bool) or not isinstance(code, int) or not (0 <= code <= 0x7F):
            range_ok = False
            print(f"       record #{i} expected_exit_code out of range 0x00..0x7F "
                  f"(machine-fault range 0x80..0xFF must be avoided; ISS-147): {code!r}")
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
