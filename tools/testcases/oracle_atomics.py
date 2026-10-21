#!/usr/bin/env python3
"""Independent oracle for TESTCASES-056t (atomics integration).

This module is the *only* place where expected values are produced.  It is
pure Python: it imports no component product (no clang/qemu/musl binding, no
probe object) and never reads an expectation back from a run.  Two kinds of
derivation are used, both from the published semantics, not from the
implementation:

  * value semantics (C11 / ``__atomic_*``): a hand-written model of the
    operation -- ``fetch_add`` returns the old value and leaves ``old+1``,
    ``compare_exchange`` reports 1/0 and updates ``expected`` on failure, and
    arithmetic is wrapped to the object width for signed/unsigned tags;
  * invariants (concurrency): exact arithmetic on the parameters
    (``N*M``, ``T*K``) and state predicates (empty stack, every node popped
    exactly once, tagged ABA rejected).

Measured component defects
--------------------------
The suite *measures* two backend defects instead of hiding them.  A cell that
is listed here as ``xfail`` is checked against the exact defective observation
(not against "anything goes"), and a cell that starts matching the semantic
expectation again is reported as ``xpass`` -- i.e. the defect is gone and the
expectation list must be updated.  Nothing xfail is ever counted as a pass.

  DEFECT_ATOMIC_STORE  every ``atomic_store``/``__atomic_store_n`` to a shared
      object stores the object's *address* instead of the value
      (DADAO LowerATOMIC_STORE reads ATOMIC_STORE operand 2, which is the
      pointer: LLVM's AtomicSDNode keeps ``(chain, value, ptr)`` for stores).
  DEFECT_NARROW_CAS    ``compare_exchange`` on a 1/2/4-byte object whose
      compared value has its top bit set never succeeds: the promoted i64
      comparison value is sign-extended while ``lr.{b,w,t}`` zero-extends.

Command line (used by the evidence script and for spot checks)::

  oracle_atomics.py --dump-c11 | --dump-builtins | --dump-aba T K
"""
import argparse
import re
import sys

NA = "na"

# --- type table (tag, kind, width, init) -----------------------------------
# Values are canonically representable (no top bit set) so the core matrix is
# about the API, not about the narrow-CAS defect; the edge cells cover that.
TYPES = [
    ("char", "signed", 1, 10),
    ("short", "signed", 2, 1000),
    ("int", "signed", 4, 100000),
    ("long", "signed", 8, 10000000000),
    ("unsigned", "unsigned", 4, 2000000000),
    ("size_t", "unsigned", 8, 3000000000),
]

RMW_ORDERS = ["relaxed", "acquire", "release", "acq_rel", "seq_cst"]
LOAD_ORDERS = ["relaxed", "acquire", "seq_cst"]
STORE_ORDERS = ["relaxed", "release", "seq_cst"]

# RMW operand and final-value model (single-threaded, object starts at INIT).
RMW_OPS = [
    ("exchange", lambda init, w: init + 1),
    ("fetch_add", lambda init, w: init + 1),
    ("fetch_sub", lambda init, w: init - 2),
    ("fetch_or", lambda init, w: init | 5),
    ("fetch_and", lambda init, w: init & 0x0C),
    ("fetch_xor", lambda init, w: init ^ 0x0F),
]

DEFECT_ATOMIC_STORE = "atomic-store-address"
DEFECT_NARROW_CAS = "narrow-cas-sext"

# Shared-store payloads (one per tag) and the RMW control sequence on sg_rmw.
SHARED_STORE_VALUE = {
    "char": 42,
    "short": 4321,
    "int": 424242,
    "long": 4242424242,
    "unsigned": 2100000000,
    "size_t": 3100000000,
    "pointer": ("ptr", "b"),
}
SHARED_RMW_EXPECT = [
    # (key suffix, ret, fin)
    ("exchange_shared", 100, 777),
    ("fetch_add_shared", 777, 782),
    ("cas_shared", 1, 900),
]


def _mask(width):
    return (1 << (8 * width)) - 1


def _wrap(value, width, kind):
    """Wrap a value into the object's width; signed tags come back signed."""
    v = value & _mask(width)
    if kind == "signed" and v >= (1 << (8 * width - 1)):
        v -= 1 << (8 * width)
    return v


def _case(cid, tag, op, order, ret, fin, exp=None, xfail=None, defect=None):
    return {
        "id": cid,
        "tag": tag,
        "op": op,
        "order": order,
        "ret": ret,
        "fin": fin,
        "exp": exp,
        "xfail": xfail,
        "defect": defect,
    }


# ---------------------------------------------------------------------------
# C11 value model
# ---------------------------------------------------------------------------
def c11_expect():
    """Expected cells for c11_alltypes.c, derived from the C11 value model."""
    cases = []
    for tag, kind, width, init in TYPES:
        def add(op, order, ret, fin, exp=None, xfail=None, defect=None):
            cid = "%s %s %s" % (tag, op, order)
            cases.append(_case(cid, tag, op, order, ret, fin, exp, xfail,
                               defect))

        for order in LOAD_ORDERS:
            add("load", order, init, init)
        if kind == "signed":
            add("load_neg", "seq_cst", -1, -1)
        for order in STORE_ORDERS:
            add("store", order, NA, _wrap(init + 1, width, kind))
        for op, fn in RMW_OPS:
            for order in RMW_ORDERS:
                add(op, order, init, _wrap(fn(init, width), width, kind))
        for op in ("compare_exchange_strong", "compare_exchange_weak"):
            for order in RMW_ORDERS:
                add(op + "_ok", order, 1, _wrap(init + 1, width, kind), init)
                add(op + "_fail", order, 0, init, init)

    # Pointer row: load/store/exchange/CAS, symbolic values ("a"/"b"/"null").
    p = "pointer"
    for order in LOAD_ORDERS:
        cases.append(_case("%s load %s" % (p, order), p, "load", order,
                           ("ptr", "a"), ("ptr", "a")))
    for order in STORE_ORDERS:
        cases.append(_case("%s store %s" % (p, order), p, "store", order, NA,
                           ("ptr", "b")))
    for order in RMW_ORDERS:
        cases.append(_case("%s exchange %s" % (p, order), p, "exchange", order,
                           ("ptr", "a"), ("ptr", "b")))
    for op in ("compare_exchange_strong", "compare_exchange_weak"):
        for order in RMW_ORDERS:
            cases.append(_case("%s %s_ok %s" % (p, op, order), p, op + "_ok",
                               order, 1, ("ptr", "b"), ("ptr", "a")))
            cases.append(_case("%s %s_fail %s" % (p, op, order), p, op + "_fail",
                               order, 0, ("ptr", "a"), ("ptr", "a")))

    # Narrow-CAS edge cells: semantic success, measured failure (defect).
    edges = [
        ("char", "signed", 1, -1),
        ("short", "signed", 2, -1000),
        ("int", "signed", 4, -1),
        ("long", "signed", 8, -1),          # control: 8-byte is not widened
        ("unsigned", "unsigned", 4, 0x80000000),
        ("uchar", "unsigned", 1, 200),
        ("ushort", "unsigned", 2, 40000),
    ]
    for tag, kind, width, init in edges:
        v = _wrap(init, width, kind)
        cid = "%s compare_exchange_edge_ok seq_cst" % tag
        if kind == "signed" and width == 8:
            cases.append(_case(cid, tag, "compare_exchange_edge_control",
                               "seq_cst", 1, 0, v))
        else:
            cases.append(_case(
                cid, tag, "compare_exchange_edge_ok", "seq_cst",
                ret=1, fin=0, exp=v,
                xfail=DEFECT_NARROW_CAS,
                defect=dict(ret=0, fin=v, exp=v)))

    # Shared-object cells (the real cross-thread path).
    for tag in ("char", "short", "int", "long", "unsigned", "size_t",
                "pointer"):
        kind, width = _type_info(tag)
        value = SHARED_STORE_VALUE[tag]
        cid = "%s store_shared release" % tag
        if tag == "pointer":
            cases.append(_case(cid, tag, "store_shared", "release", NA, value,
                               xfail=DEFECT_ATOMIC_STORE,
                               defect=dict(ret=NA, fin=("addr",))))
        else:
            cases.append(_case(cid, tag, "store_shared", "release", NA,
                               _wrap(value, width, kind),
                               xfail=DEFECT_ATOMIC_STORE,
                               defect=dict(ret=NA, fin=("addr",))))
    for op, ret, fin in SHARED_RMW_EXPECT:
        cases.append(_case("int %s seq_cst" % op, "int", op, "seq_cst", ret,
                           fin))
    return cases


def _type_info(tag):
    for t, kind, width, init in TYPES:
        if t == tag:
            return kind, width
    if tag == "pointer":
        return "pointer", 8
    if tag == "uchar":
        return "unsigned", 1
    if tag == "ushort":
        return "unsigned", 2
    raise KeyError(tag)


# ---------------------------------------------------------------------------
# __atomic_* value model
# ---------------------------------------------------------------------------
BUILTIN_WIDTHS = [
    # (width, init, arg)
    (1, 0x11, 0x22),
    (2, 0x1122, 0x3344),
    (4, 0x11223344, 0x55667788),
    (8, 0x1122334455667788, 0x5566778899AABBCC),
]
BUILTIN_SHARED_VALUE = {1: 0x22, 2: 0x3344, 4: 0x55667788,
                        8: 0x5566778899AABBCC}


def builtins_expect():
    cases = []
    for width, init, arg in BUILTIN_WIDTHS:
        def add(op, order, ret, fin, exp=None, xfail=None, defect=None):
            cid = "%d %s %s" % (width, op, order)
            cases.append(_case(cid, "w%d" % width, op, order, ret, fin, exp,
                               xfail, defect))

        for order in RMW_ORDERS:
            add("load_n", order, init, init)
            add("store_n", order, NA, arg)
            add("exchange_n", order, init, arg)
            add("fetch_add", order, init, (init + 1) & _mask(width))
            add("fetch_sub", order, init, (init - 2) & _mask(width))
            add("fetch_and", order, init, init & arg)
            add("fetch_or", order, init, init | arg)
            add("fetch_xor", order, init, init ^ arg)
            add("compare_exchange_ok", order, 1, arg, init)
            add("compare_exchange_fail", order, 0, init, init)
        top = init | (1 << (8 * width - 1))
        cid = "%d compare_exchange_edge seq_cst" % width
        if width == 8:
            cases.append(_case(cid, "w%d" % width, "compare_exchange_edge",
                               "seq_cst", 1, 0, top))
        else:
            cases.append(_case(
                cid, "w%d" % width, "compare_exchange_edge", "seq_cst",
                ret=1, fin=0, exp=top,
                xfail=DEFECT_NARROW_CAS,
                defect=dict(ret=0, fin=top, exp=top)))
    for width, init, _arg in BUILTIN_WIDTHS:
        m = _mask(width)
        cases.append(_case("%d load_n shared" % width, "w%d" % width,
                           "load_n_shared", "none", init, init))
        cases.append(_case(
            "%d store_n shared" % width, "w%d" % width, "store_n_shared",
            "none", NA, BUILTIN_SHARED_VALUE[width],
            xfail=DEFECT_ATOMIC_STORE, defect=dict(ret=NA, fin=("addr",))))
        del m
    return cases


# ---------------------------------------------------------------------------
# Parsers: probe text -> observed dicts
# ---------------------------------------------------------------------------
_CASE_RE = re.compile(r"^CASE (\S+) (\S+) (\S+) ret=(\S+)(.*)$")
_SCASE_RE = re.compile(r"^SCASE (\S+) (\S+) (\S+) addr=(\S+) ret=(\S+) "
                       r"fin=(\S+)$")
_BUILTIN_RE = re.compile(r"^BUILTIN w=(\d+) op=(\S+) order=(\S+) "
                         r"ret=(\S+) fin=(\S+)(.*)$")
_SBUILTIN_RE = re.compile(r"^SBUILTIN w=(\d+) op=(\S+) addr=(\S+) "
                          r"(?:ret=(\S+) )?fin=(\S+)$")
_ABA_RE = re.compile(r"^(ABA_[A-Z_]+)=(.*)$")


def _kv(tail):
    return dict(re.findall(r"(\w+)=(\S+)", tail))


def parse_c11(text):
    obs = {}
    ptrs = {}
    for line in text.splitlines():
        m = re.match(r"^PTR_A=([0-9a-f]+)$", line)
        if m:
            ptrs["a"] = int(m.group(1), 16)
            continue
        m = re.match(r"^PTR_B=([0-9a-f]+)$", line)
        if m:
            ptrs["b"] = int(m.group(1), 16)
            continue
        m = _CASE_RE.match(line)
        if m:
            tag, op, order, ret = m.group(1), m.group(2), m.group(3), m.group(4)
            tail = _kv(m.group(5))
            obs[(tag, op, order)] = {
                "ret": ret, "fin": tail.get("fin"), "exp": tail.get("exp"),
                "kind": "case",
            }
            continue
        m = _SCASE_RE.match(line)
        if m:
            tag, op, order, addr, ret, fin = m.groups()
            obs[(tag, op, order)] = {
                "ret": ret, "fin": fin, "addr": addr, "kind": "scase",
            }
    return obs, ptrs


def parse_builtins(text):
    obs = {}
    for line in text.splitlines():
        m = _BUILTIN_RE.match(line)
        if m:
            w, op, order, ret, fin, tail = m.groups()
            kv = _kv(tail)
            obs[(int(w), op, order)] = {
                "ret": ret, "fin": fin,
                "neigh": int(kv.get("neigh", "0")),
                "exp": kv.get("exp"), "kind": "builtin",
            }
            continue
        m = _SBUILTIN_RE.match(line)
        if m:
            w, op, addr, ret, fin = m.groups()
            ret = ret or NA
            # The shared cells are printed with the plain builtin name; the
            # oracle names them <op>_shared so they cannot be confused with the
            # local matrix cells.
            obs[(int(w), op + "_shared", "none")] = {
                "ret": ret, "fin": fin, "addr": addr, "kind": "sbuiltin",
            }
    return obs


def parse_counter(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"^(COUNTER_[A-Z_]+)=(-?\d+)$", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def parse_aba(text):
    out, notes = {}, []
    for line in text.splitlines():
        if line.startswith("ABA_NOTE "):
            notes.append(line[len("ABA_NOTE "):])
            continue
        m = _ABA_RE.match(line)
        if m:
            v = m.group(2).strip()
            out[m.group(1)] = int(v) if re.fullmatch(r"-?\d+", v) else v
    return out, notes


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------
def _same_int(expected, actual_str):
    if expected == NA:
        return actual_str == NA
    if actual_str is None or actual_str == NA:
        return False
    return int(actual_str) == expected


def _same_ptr(expected, actual_str, ptrs):
    label = expected[1]
    if label == "null":
        return int(actual_str, 16) == 0
    if label not in ptrs:
        return False
    return int(actual_str, 16) == ptrs[label]


def _same_value(expected, actual_str, ptrs):
    if isinstance(expected, tuple) and expected and expected[0] == "ptr":
        return _same_ptr(expected, actual_str, ptrs)
    if isinstance(expected, tuple) and expected and expected[0] == "addr":
        return False  # checked by the caller with the observed address
    return _same_int(expected, actual_str)


def _store_defect_value(addr_str, tag):
    """The measured wrong value: the object's own address, cut to the width."""
    kind, width = _type_info(tag)
    addr = int(addr_str, 16) & _mask(width)
    if kind == "signed" and addr >= (1 << (8 * width - 1)):
        addr -= 1 << (8 * width)
    return addr


def _check(name, expected, actual, ok, kind="check", detail=""):
    return {"name": name, "expected": expected, "actual": actual, "ok": ok,
            "kind": kind, "detail": detail}


def compare_c11(obs, ptrs):
    checks = []
    expected = c11_expect()
    expected_keys = {(c["tag"], c["op"], c["order"]) for c in expected}
    for c in expected:
        cid = c["id"]
        o = obs.get((c["tag"], c["op"], c["order"]))
        if o is None:
            checks.append(_check(cid, "present", "missing", False,
                                 detail="cell not emitted by the probe"))
            continue
        fields = [("ret", c["ret"]), ("fin", c["fin"])]
        if c["exp"] is not None:
            fields.append(("exp", c["exp"]))
        if c["xfail"] == DEFECT_ATOMIC_STORE:
            # The defect signature: the address was stored instead of VALUE.
            addr = o.get("addr")
            if addr is None:
                checks.append(_check(cid, "addr field", "missing", False))
                continue
            bad = _store_defect_value(addr, c["tag"])
            semantic = (
                o["ret"] == NA
                and _same_value(c["fin"], o["fin"], ptrs))
            if semantic:
                checks.append(_check(cid, "defect signature", "semantic value",
                                     False,
                                     detail="XPASS: %s is fixed -- remove "
                                            "the xfail entry" % c["xfail"]))
            elif ((int(o["fin"], 16) == bad) if c["tag"] == "pointer"
                  else _same_int(bad, o["fin"])):
                checks.append(_check(cid, "stored == address (defect)", "match",
                                     True, kind="xfail", detail=c["xfail"]))
            else:
                checks.append(_check(cid, "stored == address (defect)",
                                     o["fin"], False,
                                     detail="defect signature changed"))
            continue
        if c["xfail"] == DEFECT_NARROW_CAS:
            sig = c["defect"]
            got = (o["ret"], o["fin"], o["exp"])
            want = (str(sig["ret"]),
                    _norm(sig["fin"]),
                    _norm(sig["exp"]))
            semantics = (o["ret"] == "1" and _same_value(c["fin"], o["fin"], ptrs))
            if semantics:
                checks.append(_check(cid, "defect signature", "semantic value",
                                     False,
                                     detail="XPASS: %s is fixed -- remove "
                                            "the xfail entry" % c["xfail"]))
            elif got == want:
                checks.append(_check(cid, "cas fails on top-bit value",
                                     "match", True, kind="xfail",
                                     detail=c["xfail"]))
            else:
                checks.append(_check(cid, "cas fails on top-bit value",
                                     str(got), False,
                                     detail="defect signature changed"))
            continue
        detail = []
        ok = True
        for fname, fval in fields:
            got = o.get(fname)
            good = _same_value(fval, got, ptrs)
            if not good:
                ok = False
            detail.append("%s exp=%s got=%s" % (fname, _show(fval), got))
        checks.append(_check(cid, "value semantics", "; ".join(detail), ok))
    for key in obs:
        if key not in expected_keys and obs[key].get("kind") in ("case", "scase"):
            checks.append(_check(" ".join(key), "known cell", "unexpected",
                                 False, detail="probe emitted a cell the "
                                               "oracle does not model"))
    return checks


def _norm(v):
    if isinstance(v, tuple):
        return v[1] if v[0] == "ptr" else str(v)
    return str(v)


def _show(v):
    if isinstance(v, tuple):
        return "/".join(str(x) for x in v)
    return str(v)


def compare_builtins(obs):
    checks = []
    expected = builtins_expect()
    keys = {(int(c["tag"][1:]), c["op"], c["order"]) for c in expected}
    for c in expected:
        width = int(c["tag"][1:])
        o = obs.get((width, c["op"], c["order"]))
        cid = c["id"]
        if o is None:
            checks.append(_check(cid, "present", "missing", False,
                                 detail="cell not emitted by the probe"))
            continue
        if c["xfail"] == DEFECT_ATOMIC_STORE:
            addr = o.get("addr")
            if addr is None:
                checks.append(_check(cid, "addr field", "missing", False))
                continue
            bad = int(addr, 16) & _mask(width)
            if o["fin"] == str(c["fin"]):
                checks.append(_check(cid, "defect signature", "semantic value",
                                     False,
                                     detail="XPASS: %s is fixed -- remove "
                                            "the xfail entry" % c["xfail"]))
            elif int(o["fin"]) == bad:
                checks.append(_check(cid, "stored == address (defect)", "match",
                                     True, kind="xfail", detail=c["xfail"]))
            else:
                checks.append(_check(cid, "stored == address (defect)",
                                     o["fin"], False,
                                     detail="defect signature changed"))
            continue
        if c["xfail"] == DEFECT_NARROW_CAS:
            sig = c["defect"]
            got = (o["ret"], o["fin"], o["exp"])
            want = (str(sig["ret"]), str(sig["fin"]), str(sig["exp"]))
            if o["ret"] == "1" and o["fin"] == str(c["fin"]):
                checks.append(_check(cid, "defect signature", "semantic value",
                                     False,
                                     detail="XPASS: %s is fixed -- remove "
                                            "the xfail entry" % c["xfail"]))
            elif got == want:
                checks.append(_check(cid, "cas fails on top-bit value",
                                     "match", True, kind="xfail",
                                     detail=c["xfail"]))
            else:
                checks.append(_check(cid, "cas fails on top-bit value",
                                     str(got), False,
                                     detail="defect signature changed"))
            continue
        ok = o["ret"] == _norm(c["ret"]) and o["fin"] == str(c["fin"])
        detail = "ret exp=%s got=%s; fin exp=%s got=%s" % (
            _norm(c["ret"]), o["ret"], c["fin"], o["fin"])
        if c["exp"] is not None:
            ok = ok and o.get("exp") == str(c["exp"])
            detail += "; exp exp=%s got=%s" % (c["exp"], o.get("exp"))
        if c["op"] not in ("store_n_shared", "load_n_shared"):
            ok = ok and o.get("neigh") == 1
            detail += "; neigh=%s" % o.get("neigh")
        checks.append(_check(cid, "value semantics", detail, ok))
    for key in obs:
        if key not in keys:
            checks.append(_check("w%d %s %s" % key, "known cell",
                                 "unexpected", False))
    return checks


def counter_expect(threads, iters):
    return {"COUNTER_THREADS": threads, "COUNTER_ITERS": iters,
            "COUNTER_COUNT": threads * iters,
            "COUNTER_SUM": threads * iters, "COUNTER_RC": 0}


def compare_counter(obs, threads, iters, label):
    checks = []
    for key, want in counter_expect(threads, iters).items():
        got = obs.get(key)
        checks.append(_check("%s %s" % (label, key), want, got, got == want))
    return checks


def aba_expect(threads, iters):
    return {
        "ABA_THREADS": threads,
        "ABA_ITER": iters,
        "ABA_NODES": threads * iters,
        "ABA_PUSHES": threads * iters,
        "ABA_POPS": threads * iters,
        "ABA_EMPTY_FINAL": 1,
        "ABA_NODE_MISMATCH": 0,
        "ABA_BAD_NODE": 0,
        "ABA_PTR_FITS": 1,
        "ABA_CREATED": threads,
        "ABA_TAGGED": "cas_rejected",
        "ABA_TAGGED_HEAD_OK": 1,
    }


def compare_aba(obs, threads, iters, label):
    checks = []
    for key, want in aba_expect(threads, iters).items():
        got = obs.get(key)
        checks.append(_check("%s %s" % (label, key), want, got, got == want))
    return checks


def barrier_expected(source_text):
    """Number of a_barrier statements = the structural expectation.

    Line-anchored on purpose: documentation may mention the token, a call site
    is a line of its own.  This is the independent oracle for the fence count.
    """
    return len(re.findall(r"(?m)^[ \t]*a_barrier\(\);[ \t]*$", source_text))


def main(argv=None):
    ap = argparse.ArgumentParser(description="TESTCASES-056t oracle")
    ap.add_argument("--dump-c11", action="store_true")
    ap.add_argument("--dump-builtins", action="store_true")
    ap.add_argument("--dump-aba", nargs=2, type=int, metavar=("T", "K"))
    ap.add_argument("--barrier-sites", metavar="SOURCE")
    args = ap.parse_args(argv)
    if args.dump_c11:
        for c in c11_expect():
            print(c["id"], c["ret"], c["fin"], c["exp"], c["xfail"])
    if args.dump-builtins:
        for c in builtins_expect():
            print(c["id"], c["ret"], c["fin"], c["exp"], c["xfail"])
    if args.dump_aba:
        t, k = args.dump_aba
        for k2, v in aba_expect(t, k).items():
            print(k2, v)
    if args.barrier_sites:
        with open(args.barrier_sites) as f:
            print(barrier_expected(f.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
