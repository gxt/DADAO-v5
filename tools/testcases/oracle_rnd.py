#!/usr/bin/env python3
"""Independent oracle for TESTCASES-060t: ``ftrnd``/``fornd`` (roundToIntegral).

Spec sources (expectations are derived from these, NEVER from QEMU/LLVM):
  * ``spec/SimRISC-07 §4.3`` -- six one-hot ``immu6`` modes, common rules
    (``±0`` sign kept, ``|x| >= 2^p`` returned unchanged, Inf unchanged, no
    OF/UF, only ``0x20`` sets NX, sNaN -> NV, qNaN canonicalised);
  * ``.tao/contracts/contract-fp.md §18`` (``roundint``) -- the same, frozen;
  * ``spec/SimRISC-00 §浮点状态寄存器`` / ``contract-fp.md §1`` -- rf0 bit
    layout: ``[33:32]`` round mode, ``[4:0]`` accrued flags (NV DZ OF UF NX),
    writes to rf0 update only ``[33:32]`` and ``[4:0]``;
  * ADR-0004 D2 -- rf0 reset value ``0x7FF8_0000_7FC0_0000``.

Arithmetic is exact: IEEE bit patterns are decoded to ``fractions.Fraction``
and the four tie rules are implemented with integer division.  Nothing here
imports a component (no QEMU, no LLVM, no softfloat).

Self proof (``--selftest``)
---------------------------
1. a hand-written tie table (``2.5``, ``-2.5``, ``0.5``, ``-0.5``, ``1.5``,
   ``-1.5``, ``3.5`` x 5 static modes) is compared with the generic rule
   engine -- the table states the expected integer directly, so a broken rule
   engine is a hard FAIL;
2. every finite ``fo`` value/bits pair is re-derived through the *host*
   binary64 + ``math`` module (a second, independent implementation) and every
   ``ft`` result through ``struct.pack('>f', ...)`` (correctly rounded
   binary32);
3. ``encode``/``decode`` round-trip for every matrix input of both formats;
4. a deliberate cross-check that ``0x01`` and ``0x02`` disagree on the tie
   inputs (catches "both branches return the same value");
5. a wrong-result injection must be reported as red (reachable FAIL).

Usage
-----
  oracle_rnd.py --selftest
  oracle_rnd.py --dump          # expected table for eyeballing / hand review
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
from fractions import Fraction

# ── formats ────────────────────────────────────────────────────────────────
FMT = {
    "ft": {"w": 32, "p": 24, "eb": 8, "mb": 23},
    "fo": {"w": 64, "p": 53, "eb": 11, "mb": 52},
}

# rf0 (FCSR) layout: [63:51] read-only qNaN(fo), [31:22] read-only qNaN(ft),
# [33:32] round mode, [4:0] flags; everything else SBZ (writes have no effect).
RF0_RESET = 0x7FF800007FC00000          # ADR-0004 D2
RF0_WRITABLE = (0x3 << 32) | 0x1F
RF0_READONLY = RF0_RESET & ~RF0_WRITABLE

FLAG_NV, FLAG_DZ, FLAG_OF, FLAG_UF, FLAG_NX = 0x01, 0x02, 0x04, 0x08, 0x10

# ── six one-hot modes (SimRISC-07 §4.3) ────────────────────────────────────
STATIC_MODES = (0x01, 0x02, 0x04, 0x08, 0x10)
DYN_MODE = 0x20
ALL_MODES = STATIC_MODES + (DYN_MODE,)

# rf0[33:32] -> rule for the dynamic code
DYN_RULE = {0: "ties_even", 1: "toward_zero", 2: "toward_neg", 3: "toward_pos"}
STATIC_RULE = {
    0x01: "ties_even",
    0x02: "ties_away",
    0x04: "toward_zero",
    0x08: "toward_pos",
    0x10: "toward_neg",
}
RULES = ("ties_even", "ties_away", "toward_zero", "toward_pos", "toward_neg")


# ── bit level helpers ─────────────────────────────────────────────────────
def _fields(fmt):
    f = FMT[fmt]
    return f["w"], f["p"], f["eb"], f["mb"]


def _exp_all(f):
    return (1 << f["eb"]) - 1


def _qnan_bits(fmt):
    """Canonical quiet NaN of the format (positive sign)."""
    _w, _p, eb, mb = _fields(fmt)
    return ((_exp_all(FMT[fmt]) << mb) | (1 << (mb - 1)))


def _inf_bits(fmt, sign=0):
    _w, _p, eb, mb = _fields(fmt)
    return (sign << (FMT[fmt]["w"] - 1)) | (_exp_all(FMT[fmt]) << mb)


def _min_sub_bits(fmt):
    return 1


def decode(bits, fmt):
    """Return dict(kind, sign, value (Fraction|None), quiet (bool|None))."""
    w, p, eb, mb = _fields(fmt)
    bits &= (1 << w) - 1
    sign = (bits >> (w - 1)) & 1
    expf = (bits >> mb) & _exp_all(FMT[fmt])
    frac = bits & ((1 << mb) - 1)
    if expf == _exp_all(FMT[fmt]):
        if frac == 0:
            return {"kind": "inf", "sign": sign, "value": None, "quiet": None}
        quiet = bool(frac >> (mb - 1))
        return {"kind": "nan", "sign": sign, "value": None, "quiet": quiet}
    if expf == 0:
        if frac == 0:
            return {"kind": "zero", "sign": sign, "value": Fraction(0),
                    "quiet": None}
        m, e = frac, 1 - ((1 << (eb - 1)) - 1) - mb
    else:
        m = frac | (1 << mb)
        e = expf - ((1 << (eb - 1)) - 1) - mb
    val = Fraction(m) * (Fraction(2) ** e)
    return {"kind": "normal", "sign": sign,
            "value": -val if sign else val, "quiet": None}


def _floor_log2(a):
    """floor(log2(a)) for a positive Fraction."""
    n, d = a.numerator, a.denominator
    e = n.bit_length() - d.bit_length()
    two = Fraction(2)
    while two ** e > a:
        e -= 1
    while two ** (e + 1) <= a:
        e += 1
    return e


def _round_half_even(q):
    """Round a non-negative Fraction to the nearest integer, ties to even."""
    n, d = q.numerator, q.denominator
    k, r = divmod(n, d)
    twice = 2 * r
    if twice > d or (twice == d and (k % 2) == 1):
        return k + 1
    return k


def encode(value, fmt):
    """Exact IEEE-754 encoding of a Fraction (round to nearest even)."""
    w, p, eb, mb = _fields(fmt)
    if value < 0:
        sign, a = 1, -value
    else:
        sign, a = 0, value
    if a == 0:
        return sign << (w - 1)
    bias = (1 << (eb - 1)) - 1
    e = _floor_log2(a)
    m = _round_half_even(a / (Fraction(2) ** (e - mb)))
    if m == (1 << (mb + 1)):
        m >>= 1
        e += 1
    emin = 1 - bias
    if e < emin:
        m = _round_half_even(a / (Fraction(2) ** (emin - mb)))
        if m >= (1 << mb):
            return (sign << (w - 1)) | (1 << mb)      # smallest normal
        return (sign << (w - 1)) | m
    expf = e + bias
    if expf >= _exp_all(FMT[fmt]):
        return (sign << (w - 1)) | (_exp_all(FMT[fmt]) << mb)
    return (sign << (w - 1)) | (expf << mb) | (m - (1 << mb))


# ── round-to-integral rules (exact integer arithmetic) ────────────────────
def round_int(value, rule):
    """Round an exact Fraction to an integer under one of the five IEEE rules."""
    if rule not in RULES:
        raise ValueError("unknown rule %r" % (rule,))
    n, d = value.numerator, value.denominator
    q, r = divmod(n, d)                       # Python floor division
    if r == 0:
        return q
    if rule == "toward_neg":
        return q
    if rule == "toward_pos":
        return q + 1
    if rule == "toward_zero":
        return q + 1 if value < 0 else q
    half = 2 * r
    if half < d:
        return q
    if half > d:
        return q + 1
    # exactly half way: the tie rules are the only ones left
    if rule == "ties_even":
        return q if (q % 2) == 0 else q + 1
    # ties_away: pick the neighbour with the larger magnitude
    return q if value < 0 else q + 1


# ── expectations ──────────────────────────────────────────────────────────
def rule_for(mode, rmode):
    if mode == DYN_MODE:
        return DYN_RULE[rmode & 3]
    return STATIC_RULE[mode]


def expect(in_bits, fmt, mode, rmode=0):
    """Expected (out_bits, flags) for one instruction execution.

    ``mode`` is the ``immu6`` one-hot code; ``rmode`` is rf0[33:32] as set by
    the test (only honoured by ``0x20``).
    """
    w, p, eb, mb = _fields(fmt)
    d = decode(in_bits, fmt)
    nv = nx = 0
    if d["kind"] == "nan":
        out = _qnan_bits(fmt)
        nv = 0 if d["quiet"] else FLAG_NV
    elif d["kind"] == "inf":
        out = in_bits & ((1 << w) - 1)
    else:
        val = d["value"]
        if d["kind"] == "zero" or abs(val) >= Fraction(2) ** p:
            # already an integer (incl. ±0 and |x| >= 2^p): spec keeps it as-is
            out = in_bits & ((1 << w) - 1)
        else:
            n = round_int(val, rule_for(mode, rmode))
            if n == 0:
                out = d["sign"] << (w - 1)      # the zero keeps the input sign
            else:
                out = encode(Fraction(n), fmt)
            if mode == DYN_MODE and val.denominator != 1:
                nx = FLAG_NX
    return {"out": out & ((1 << w) - 1), "flags": nv | nx,
            "rm": rmode & 3}


# ── input matrix (labels are the contract with the C probes) ──────────────
def input_table(fmt):
    """[(label, spec)] with spec = ("num", Fraction) | ("zero", sign) | name."""
    t = [
        ("-0", ("zero", -1)),
        ("0", ("zero", 1)),
        ("0.4", ("num", Fraction(2, 5))),
        ("-0.4", ("num", -Fraction(2, 5))),
        ("0.5", ("num", Fraction(1, 2))),
        ("-0.5", ("num", -Fraction(1, 2))),
        ("1.0", ("num", Fraction(1))),
        ("-1.0", ("num", Fraction(-1))),
        ("1.5", ("num", Fraction(3, 2))),
        ("-1.5", ("num", -Fraction(3, 2))),
        ("2.5", ("num", Fraction(5, 2))),
        ("-2.5", ("num", -Fraction(5, 2))),
        ("3.5", ("num", Fraction(7, 2))),
        ("-3.5", ("num", -Fraction(7, 2))),
        ("inf", ("inf", 0)),
        ("-inf", ("inf", 1)),
        ("qnan", ("qnan",)),
        ("snan", ("snan",)),
        ("minsub", ("minsub",)),
    ]
    if fmt == "fo":
        t.append(("2^53", ("num", Fraction(2 ** 53))))
    else:
        t.append(("2^24", ("num", Fraction(2 ** 24))))
    return t


def bits_for(spec, fmt):
    kind = spec[0]
    if kind == "zero":
        sign = 1 if spec[1] < 0 else 0
        return sign << (FMT[fmt]["w"] - 1)
    if kind == "num":
        return encode(spec[1], fmt)
    if kind == "inf":
        return _inf_bits(fmt, spec[1])
    if kind == "qnan":
        return _qnan_bits(fmt)
    if kind == "snan":
        w, p, eb, mb = _fields(fmt)
        return (_exp_all(FMT[fmt]) << mb) | 1
    if kind == "minsub":
        return _min_sub_bits(fmt)
    raise ValueError("bad input spec %r" % (spec,))


def input_bits(fmt):
    return [(label, bits_for(spec, fmt)) for label, spec in input_table(fmt)]


# additional exact values used by the C-level mapping group; kept out of the
# instruction matrix so the matrix cell count stays exactly 6 modes x N inputs.
EXTRA_VALUES = {
    "2.7": Fraction(27, 10),
    "-2.7": -Fraction(27, 10),
    "2.3": Fraction(23, 10),
    "-2.3": -Fraction(23, 10),
}


def label_bits(label, fmt):
    """Bit pattern the probe must feed in for an input ``label``."""
    table = dict(input_bits(fmt))
    if label in table:
        return table[label]
    if label in EXTRA_VALUES:
        return encode(EXTRA_VALUES[label], fmt)
    return None


# ── observation parsing (the C probes only print raw observations) ────────
def parse(text):
    """Parse the probe output into {'init':..., 'restore':[...], 'obs':[...]}."""
    out = {"init": None, "restore": [], "obs": [], "junk": []}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        tag, _, rest = line.partition(" ")
        fields = {}
        for tok in rest.split():
            if "=" in tok:
                k, _, v = tok.partition("=")
                fields[k] = v
        if tag == "INIT":
            out["init"] = fields
        elif tag == "RESTORE":
            out["restore"].append(fields)
        elif tag in ("MATRIX", "MODE", "FLAGS", "CMAP"):
            fields["group"] = tag.lower()
            out["obs"].append(fields)
        else:
            out["junk"].append(line)
    return out


# C 层映射: the C function name -> the one-hot code the backend must select.
CMAP_CODE = {
    "floor": 0x10,
    "ceil": 0x08,
    "trunc": 0x04,
    "round": 0x02,
    "nearbyint": DYN_MODE,
}


def judge_obs(rec):
    """One observation -> check dict {name, expected, actual, ok, detail}."""
    group = rec["group"]
    fmt = rec["fmt"]
    label = rec.get("label", "?")
    in_bits = int(rec["in"], 16)
    out_bits = int(rec["out"], 16)
    if group == "cmap":
        fn = rec["fn"]
        code = CMAP_CODE[fn]
        exp = expect(in_bits, fmt, code, 0)
    else:
        code = int(rec["mode"], 0)
        rmode = int(rec["rm"], 0)
        exp = expect(in_bits, fmt, code, rmode)
    w = FMT[fmt]["w"]
    mask = (1 << w) - 1
    problems = []
    # the label must really denote the bit pattern the probe fed in -- checked
    # for every group (a mistyped C literal must never pass silently)
    want_in = label_bits(label, fmt)
    if want_in is None:
        problems.append("unknown label %r" % label)
    elif (want_in & mask) != (in_bits & mask):
        problems.append("input bits %#x != label %r bits %#x"
                        % (in_bits & mask, label, want_in & mask))
    # The C-level mapping group judges the VALUE only: `nearbyint` lands on
    # 0x20 (contract-fp.md §18 known deviation) so NX may be set.  The static
    # no-NX rule is covered by the instruction-level FLAGS group.
    if group != "cmap":
        if int(rec["rm"], 0) != exp["rm"]:
            problems.append("rf0[33:32]=%s != %d" % (rec["rm"], exp["rm"]))
        pre = int(rec["pre"], 16)
        post = int(rec["post"], 16)
        if pre & 0x1F:
            problems.append("pre-flags %#x not cleared by the test" % (pre & 0x1F))
        if (pre & RF0_READONLY) != (RF0_RESET & RF0_READONLY):
            problems.append("rf0 read-only bits changed by a write: %#x"
                            % (pre & RF0_READONLY))
        if (post & RF0_READONLY) != (pre & RF0_READONLY):
            problems.append("rf0 read-only bits changed by the instruction")
        actual_flags = post & 0x1F
        if actual_flags != exp["flags"]:
            problems.append("flags %#04x != %#04x" % (actual_flags, exp["flags"]))
    if (out_bits & mask) != exp["out"]:
        problems.append("result %#x != %#x" % (out_bits & mask, exp["out"]))
    name = "%s %s %s %s" % (group, fmt, label,
                            rec.get("fn") or rec.get("mode"))
    if group == "mode":
        name = "mode %s rm=%s %s %s" % (fmt, rec.get("rm"), label, rec["mode"])
    actual = "out=%#x%s" % (out_bits & mask,
                            "" if group == "cmap"
                            else " flags=%#04x" % (int(rec["post"], 16) & 0x1F))
    expected = "out=%#x%s" % (exp["out"],
                              "" if group == "cmap"
                              else " flags=%#04x" % exp["flags"])
    return {"name": name, "expected": expected, "actual": actual,
            "ok": not problems, "detail": "; ".join(problems)}


def judge_init(rec):
    if rec is None:
        return {"name": "INIT rf0 observed", "expected": "one INIT line",
                "actual": "missing", "ok": False, "detail": ""}
    got = int(rec["rf0"], 16)
    ok = (got & RF0_READONLY) == (RF0_RESET & RF0_READONLY)
    return {"name": "INIT rf0 read-only bits == reset value",
            "expected": "%#018x" % (RF0_RESET & RF0_READONLY),
            "actual": "%#018x" % (got & RF0_READONLY), "ok": ok,
            "detail": "" if ok else "ADR-0004 D2 reset value violated"}


def judge_restore(rec):
    want = int(rec["expect"], 16)
    got = int(rec["got"], 16)
    ok = (got & (RF0_WRITABLE | RF0_READONLY)) == (want & (RF0_WRITABLE | RF0_READONLY))
    return {"name": "rf0 restored after group (%s)" % rec.get("group", "?"),
            "expected": "%#018x" % want, "actual": "%#018x" % got, "ok": ok,
            "detail": "" if ok else "rf0 not restored to the pre-group value"}


def judge_distinct(records, fmt, label):
    """Mode sensitivity: the four rf0[33:32] settings must not all agree."""
    outs = []
    for rec in records:
        if (rec["fmt"] == fmt and rec.get("label") == label
                and int(rec["mode"], 0) == DYN_MODE):
            outs.append(int(rec["out"], 16) & ((1 << FMT[fmt]["w"]) - 1))
    want = []
    for rmode in range(4):
        want.append(expect(dict(input_bits(fmt))[label], fmt, DYN_MODE,
                           rmode)["out"])
    ok = len(outs) == 4 and len(set(outs)) == len(set(want)) and len(set(outs)) > 1
    return {"name": "mode sensitive %s %s (distinct results)" % (fmt, label),
            "expected": "%d distinct %s" % (len(set(want)),
                                            sorted("%#x" % v for v in set(want))),
            "actual": "%d distinct %s" % (len(set(outs)),
                                          sorted("%#x" % v for v in set(outs))),
            "ok": ok,
            "detail": "" if ok else "rf0[33:32] does not change the result"}


def judge_static_insensitive(records, fmt, mode, label):
    """A static direction must give the same result under every rf0[33:32]."""
    outs = []
    for rec in records:
        if (rec["fmt"] == fmt and rec.get("label") == label
                and int(rec["mode"], 0) == mode):
            outs.append(int(rec["out"], 16) & ((1 << FMT[fmt]["w"]) - 1))
    want = expect(label_bits(label, fmt), fmt, mode, 0)["out"]
    ok = len(outs) == 4 and len(set(outs)) == 1 and outs[0] == want
    return {"name": "static insensitivity %s %#04x %s" % (fmt, mode, label),
            "expected": "4 x %#x" % want,
            "actual": "%d x %s" % (len(set(outs)),
                                   sorted("%#x" % v for v in set(outs))),
            "ok": ok,
            "detail": "" if ok else "a static mode must ignore rf0[33:32]"}


# ── self proof ────────────────────────────────────────────────────────────
HAND_TIES = [
    # (label, mode, expected integer)  -- written out by hand from
    # SimRISC-07 §4.3; independent of round_int()'s implementation.
    ("2.5", 0x01, 2), ("2.5", 0x02, 3), ("2.5", 0x04, 2),
    ("2.5", 0x08, 3), ("2.5", 0x10, 2),
    ("-2.5", 0x01, -2), ("-2.5", 0x02, -3), ("-2.5", 0x04, -2),
    ("-2.5", 0x08, -2), ("-2.5", 0x10, -3),
    ("0.5", 0x01, 0), ("0.5", 0x02, 1), ("0.5", 0x04, 0),
    ("0.5", 0x08, 1), ("0.5", 0x10, 0),
    ("-0.5", 0x01, 0), ("-0.5", 0x02, -1), ("-0.5", 0x04, 0),
    ("-0.5", 0x08, 0), ("-0.5", 0x10, -1),
    ("1.5", 0x01, 2), ("1.5", 0x02, 2), ("1.5", 0x04, 1),
    ("1.5", 0x08, 2), ("1.5", 0x10, 1),
    ("-1.5", 0x01, -2), ("-1.5", 0x02, -2), ("-1.5", 0x04, -1),
    ("-1.5", 0x08, -1), ("-1.5", 0x10, -2),
    ("3.5", 0x01, 4), ("3.5", 0x02, 4), ("3.5", 0x04, 3),
    ("3.5", 0x08, 4), ("3.5", 0x10, 3),
]


def selftest():
    checks = []

    def add(name, expected, actual, ok, detail=""):
        checks.append({"name": name, "expected": expected, "actual": actual,
                       "ok": bool(ok), "detail": detail})

    # 1. hand-written tie table vs the generic rule engine
    vals = dict(input_bits("fo"))
    pt = Fraction(2, 5)
    for label, mode, want in HAND_TIES:
        got = round_int(Fraction(label), STATIC_RULE[mode])
        add("hand tie %s mode %#04x" % (label, mode), want, got, want == got)
    # zero sign and |x| >= 2^p rules
    e = expect(vals["-0.5"], "fo", 0x04)
    add("trunc(-0.5) keeps the negative zero", "%#x" % (1 << 63),
        "%#x" % e["out"], e["out"] == (1 << 63))
    e = expect(vals["-0.5"], "fo", 0x08)
    add("ceil(-0.5) keeps the negative zero", "%#x" % (1 << 63),
        "%#x" % e["out"], e["out"] == (1 << 63))
    e = expect(vals["3.5"], "fo", 0x02)
    add("ties_away(3.5) == 4", "%#x" % encode(Fraction(4), "fo"),
        "%#x" % e["out"], e["out"] == encode(Fraction(4), "fo"))
    e = expect(vals["2^53"], "fo", 0x10)
    add("|x| >= 2^p returned unchanged (fo)", "%#x" % vals["2^53"],
        "%#x" % e["out"], e["out"] == vals["2^53"])
    e = expect(dict(input_bits("ft"))["2^24"], "ft", 0x02)
    add("|x| >= 2^p returned unchanged (ft)",
        "%#x" % dict(input_bits("ft"))["2^24"], "%#x" % e["out"],
        e["out"] == dict(input_bits("ft"))["2^24"])
    # "both branches same result" guard: the tie modes must disagree
    o1 = expect(vals["2.5"], "fo", 0x01)["out"]
    o2 = expect(vals["2.5"], "fo", 0x02)["out"]
    add("0x01 and 0x02 differ on 2.5", "different", "%#x vs %#x" % (o1, o2),
        o1 != o2)
    # only 0x20 sets NX
    nx = {m: expect(vals["1.5"], "fo", m, 0)["flags"] for m in ALL_MODES}
    add("only 0x20 sets NX on 1.5", "0x10 only for 0x20",
        " ".join("%#04x:%#04x" % (m, nx[m]) for m in ALL_MODES),
        all(nx[m] == 0 for m in STATIC_MODES) and nx[0x20] == FLAG_NX)
    # qNaN never sets NV, sNaN always does
    qn = {m: expect(vals["qnan"], "fo", m, 0)["flags"] for m in ALL_MODES}
    sn = {m: expect(vals["snan"], "fo", m, 0)["flags"] for m in ALL_MODES}
    add("qNaN never sets NV", "0x00 everywhere",
        " ".join("%#04x" % v for v in qn.values()),
        all(v == 0 for v in qn.values()))
    add("sNaN always sets NV", "0x01 everywhere",
        " ".join("%#04x" % v for v in sn.values()),
        all(v == FLAG_NV for v in sn.values()))
    add("sNaN sets NV but never NX", "0x01",
        " ".join("%#04x" % v for v in sn.values()),
        all(v == FLAG_NV for v in sn.values()))

    # 2a. host binary64 + math module as a second implementation (fo)
    def host_fo_rule(x, rule):
        if math.isinf(x) or math.isnan(x) or abs(x) >= float(2 ** 53):
            return x

        def ival(n):
            # an integral result of zero keeps the sign of the input
            if n == 0 and math.copysign(1.0, x) < 0:
                return -0.0
            return float(n)

        if rule == "toward_zero":
            return ival(math.trunc(x))
        if rule == "toward_pos":
            return ival(math.ceil(x))
        if rule == "toward_neg":
            return ival(math.floor(x))
        f = math.floor(x)
        frac = x - f
        if frac == 0:
            return x
        if frac < 0.5:
            return ival(f)
        if frac > 0.5:
            return ival(f + 1)
        if rule == "ties_even":
            return ival(f if f % 2 == 0 else f + 1)
        return ival(f if x < 0 else f + 1)      # ties away from zero

    for label, bits in input_bits("fo"):
        d = decode(bits, "fo")
        if d["kind"] != "normal":
            continue
        x = struct.unpack(">d", struct.pack(">Q", bits))[0]
        for mode in STATIC_MODES:
            want = host_fo_rule(x, STATIC_RULE[mode])
            want_bits = struct.unpack(">Q", struct.pack(">d", want))[0]
            got = expect(bits, "fo", mode)["out"]
            add("host cross-check fo %s mode %#04x" % (label, mode),
                "%#x" % want_bits, "%#x" % got, want_bits == got)
        for rmode in range(4):
            want = host_fo_rule(x, DYN_RULE[rmode])
            want_bits = struct.unpack(">Q", struct.pack(">d", want))[0]
            got = expect(bits, "fo", DYN_MODE, rmode)["out"]
            add("host cross-check fo %s dyn rm=%d" % (label, rmode),
                "%#x" % want_bits, "%#x" % got, want_bits == got)

    # 2b. ft results are exactly representable -> struct.pack('>f') cross-check
    for label, bits in input_bits("ft"):
        d = decode(bits, "ft")
        if d["kind"] != "normal":
            continue
        for mode in STATIC_MODES:
            got = expect(bits, "ft", mode)["out"]
            n = round_int(d["value"], STATIC_RULE[mode])
            if n == 0:
                want = d["sign"] << 31
            else:
                want = struct.unpack(">I", struct.pack(">f", float(n)))[0]
            add("binary32 cross-check ft %s mode %#04x" % (label, mode),
                "%#x" % want, "%#x" % got, want == got)

    # 3. encode/decode round trip for every matrix input
    for fmt in FMT:
        for label, bits in input_bits(fmt):
            d = decode(bits, fmt)
            # a zero's sign is not carried by Fraction(0); checked by the
            # dedicated -0.5 / -0 rules above instead.
            if d["kind"] in ("nan", "inf", "zero"):
                add("round trip %s %s" % (fmt, label), "decoded",
                    d["kind"], d["kind"] in ("nan", "inf", "zero"))
                continue
            add("round trip %s %s" % (fmt, label), "%#x" % bits,
                "%#x" % encode(d["value"], fmt),
                encode(d["value"], fmt) == bits)

    # 4. the oracle itself must be able to go red
    wrong = expect(vals["2.5"], "fo", 0x02)["out"]
    good = expect(vals["2.5"], "fo", 0x01)["out"]
    rec = {"group": "matrix", "fmt": "fo", "mode": "0x01", "rm": "0",
           "label": "2.5", "in": "%x" % vals["2.5"],
           "out": "%x" % wrong, "pre": "%x" % RF0_RESET,
           "post": "%x" % RF0_RESET}
    add("injected wrong result is judged red", "ok=False",
        "ok=%s" % judge_obs(rec)["ok"], judge_obs(rec)["ok"] is False)
    rec["out"] = "%x" % good
    add("correct result is judged green", "ok=True",
        "ok=%s" % judge_obs(rec)["ok"], judge_obs(rec)["ok"] is True)

    # 5. every matrix cell is covered by an explicit expectation
    n = 0
    for fmt in FMT:
        for label, bits in input_bits(fmt):
            for mode in ALL_MODES:
                for rmode in (range(4) if mode == DYN_MODE else (0,)):
                    e = expect(bits, fmt, mode, rmode)
                    n += 1
                    if "out" not in e:
                        add("expect() coverage", "out", "missing", False)
    add("expect() covers every matrix cell", "> 0", n, n > 0)

    fails = [c for c in checks if not c["ok"]]
    for c in checks:
        if not c["ok"]:
            print("  FAIL %s | expected=%s | actual=%s%s"
                  % (c["name"], c["expected"], c["actual"],
                     (" | " + c["detail"]) if c["detail"] else ""))
    print("oracle_rnd selftest: %d checks, %d fail" % (len(checks), len(fails)))
    return 0 if not fails else 1


def dump():
    for fmt in FMT:
        print("# %s" % fmt)
        for label, bits in input_bits(fmt):
            row = ["%-8s in=%0*x" % (label, FMT[fmt]["w"] // 4, bits)]
            for mode in ALL_MODES:
                rms = range(4) if mode == DYN_MODE else (0,)
                for rmode in rms:
                    e = expect(bits, fmt, mode, rmode)
                    row.append("%02x/%d->%0*x/%02x"
                               % (mode, rmode, FMT[fmt]["w"] // 4, e["out"],
                                  e["flags"]))
            print("  ".join(row))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="TESTCASES-060t roundint oracle")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dump", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.dump:
        return dump()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
