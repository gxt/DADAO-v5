#!/usr/bin/env python3
# Verilator driver for the m12-chipyard-011 FP unit bench.
#
# Feeds `tb_fp_unit` (which drives `WumingFPUnitHarness`) and checks every
# result three ways:
#
#   * mine      -- the DADAO RTL (`WumingFP.scala`)
#   * hardfloat -- berkeley-hardfloat's `RoundAnyRawFNToRecFN`, instantiated
#                  next to mine inside the bench (ops 4-7 only)
#   * oracle    -- `fp_ref.round_exact`, the exact rational model derived from
#                  the IEEE definitions in spec/SimRISC-07
#
# The recoded outputs are compared by the IEEE value they denote
# (`fp_ref.recfn_value`): the recoding of zero has several equivalent spellings
# and both implementations pick different ones, so comparing raw bits there
# would be a false alarm.  Flags are compared exactly (the bench prints
# hardfloat's in its own order, which is reversed here).
#
# Usage: unit_run.py --bin PATH --workdir DIR [--n N] [--seed S] [--keep]

import argparse
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fp_ref as F  # noqa: E402

# rounding configurations: op -> (ie, isig, oe, osig)
CONFIGS = {
    4: ("ft", F.FT[0], F.FT[1] + 2, F.FT[0], F.FT[1]),
    5: ("fo", F.FO[0], F.FO[1] + 2, F.FO[0], F.FO[1]),
    6: ("fo2ft", F.FO[0], F.FO[1] + 2, F.FT[0], F.FT[1]),
    7: ("ft2fo", F.FT[0], F.FT[1] + 2, F.FO[0], F.FO[1]),
}


def rev5(x):
    out = 0
    for i in range(5):
        out = (out << 1) | ((x >> i) & 1)
    return out


def run_vectors(binary, path):
    out = subprocess.run([binary, "--vectors", path], check=True,
                         capture_output=True, text=True).stdout
    res = []
    for line in out.splitlines():
        f = line.split()
        if not f or f[0] != "V":
            continue
        res.append(dict(op=int(f[1]), in_lo=int(f[2], 16),
                        in_hi=int(f[3], 16), mode=int(f[4]),
                        in_extra=int(f[5], 16),
                        out=int(f[7], 16) << 64 | int(f[6], 16),
                        flags=int(f[8], 16),
                        hf_out=int(f[10], 16) << 64 | int(f[9], 16),
                        hf_flags=int(f[11], 16)))
    return res


_shown = {}


def requires_show(op):
    _shown[op] = _shown.get(op, 0) + 1
    return _shown[op] <= 4


def _write(args, name, lines):
    """Write one vector file and return its path."""
    path = os.path.join(args.workdir, name)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def is_uf_boundary(out, flags, hf_flags, ew, sw):
    """hardfloat reports `UF|NX` where spec/SimRISC-07 §1.4 (tininess detected
    *after* rounding) does not: the rounded result is exactly the smallest
    normal, so it is not tiny.  Only that exact difference is tolerated, and
    only when the result magnitude is the smallest normal.
    """
    if hf_flags != (flags | F.UF) or (flags & F.UF) or not (flags & F.NX):
        return False
    v = out & ((1 << (ew + sw)) - 1)
    exp = (v >> (sw - 1)) & ((1 << ew) - 1)
    return exp == 1


def is_cmp_snan_quiet_divergence(ew, sw, a, b, signaling, mine, hf_flags):
    """hardfloat's *quiet* compare raises `NV` for an sNaN input; spec/SimRISC-07
    §4 (and QEMU) raise no flag on a quiet compare.  Only that exact difference
    is tolerated, so the signalling forms (where the rule agrees) still assert
    the hardfloat flag bit for bit."""
    if signaling or mine != 0 or hf_flags != F.NV:
        return False
    ra = F.raw_from_fn(ew, sw, a)
    rb = F.raw_from_fn(ew, sw, b)
    return F._is_snan(ra, sw) or F._is_snan(rb, sw)


def fn_val(x, ew, sw):
    """An IEEE binary word with every NaN collapsed to one value (hardfloat
    canonicalises the payload, this core propagates it)."""
    if F.raw_from_fn(ew, sw, x)["is_nan"]:
        return "nan"
    return x & ((1 << (ew + sw)) - 1)


def check(args):
    rng = random.Random(args.seed)
    fails = 0
    summary = []

    # ── encode / decode (ops 0-3) and classify (8-9) ──────────────────────
    lines = []
    exp = {}
    for ew, sw, op in ((F.FT[0], F.FT[1], 0), (F.FO[0], F.FO[1], 2),
                       (F.FT[0], F.FT[1], 8), (F.FO[0], F.FO[1], 9)):
        for x in F.sample_fn(ew, sw, args.n, rng):
            lines.append(f"{op} {x:x} 0 0")
            exp[(op, x)] = x
    # decode: feed recFN words
    for ew, sw, op in ((F.FT[0], F.FT[1], 1), (F.FO[0], F.FO[1], 3)):
        for x in F.sample_fn(ew, sw, args.n, rng):
            rc = F.recfn_from_fn(ew, sw, x)
            lines.append(f"{op} {rc & ((1 << 64) - 1):x} {rc >> 64:x} 0")
            exp[(op, rc)] = x
    # sign injection
    for _ in range(args.n):
        hc = rng.getrandbits(64)
        hd = rng.getrandbits(64)
        for op, pos, inv in ((10, 31, False), (11, 31, True),
                             (12, 63, False), (13, 63, True)):
            lines.append(f"{op} {hc:x} {hd:x} 0")
            exp[(op, (hc, hd))] = F.sign_inject(hc, hd, pos, inv)

    vpath = os.path.join(args.workdir, "vectors_ctrl.txt")
    with open(vpath, "w") as f:
        f.write("\n".join(lines) + "\n")
    got = run_vectors(args.bin, vpath)
    if len(got) != len(lines):
        print(f"  [FAIL] vector count: sent {len(lines)} got {len(got)}")
        fails += 1
    per_op = {}
    for r in got:
        op = r["op"]
        if op in (0, 1, 2, 3, 8, 9):
            send = (r["in_hi"] << 64) | r["in_lo"]
            if op == 0:
                want = F.recfn_from_fn(F.FT[0], F.FT[1], send)
            elif op == 2:
                want = F.recfn_from_fn(F.FO[0], F.FO[1], send)
            elif op == 1:
                want = F.fn_from_recfn(F.FT[0], F.FT[1], send)
            elif op == 3:
                want = F.fn_from_recfn(F.FO[0], F.FO[1], send)
            elif op == 8:
                want = F.classify_fn(F.FT[0], F.FT[1], send)
            else:
                want = F.classify_fn(F.FO[0], F.FO[1], send)
            if r["out"] != want:
                fails += 1
                per_op[op] = per_op.get(op, 0) + 1
                if requires_show(op):
                    print(f"  [FAIL] op{op} in={send:x} want={want:x} "
                          f"got={r['out']:x}")
        else:
            hc, hd = r["in_lo"], r["in_hi"]
            pos, inv = {10: (31, False), 11: (31, True),
                        12: (63, False), 13: (63, True)}[op]
            want = F.sign_inject(hc, hd, pos, inv)
            if r["out"] != want:
                fails += 1
                per_op[op] = per_op.get(op, 0) + 1
                if requires_show(op):
                    print(f"  [FAIL] op{op} hc={hc:x} hd={hd:x} "
                          f"want={want:x} got={r['out']:x}")
    print(f"  ctrl per-op failures: {per_op}")
    summary.append(("encode/decode/classify/sign", len(got), fails))
    base_fail = fails

    # ── rounding: mine vs hardfloat vs the exact oracle ───────────────────
    for op, (name, ie, isig, oe, osig) in CONFIGS.items():
        packs = [F.raw_pack(r, ie, isig) for r in
                 F.sample_raw(ie, isig, args.n, rng)]
        lines = [f"{op} {p & ((1 << 64) - 1):x} {p >> 64:x} {mode}"
                 for p in packs for mode in (F.RNE, F.RTZ, F.RDN, F.RUP, F.RNA)]
        vpath = os.path.join(args.workdir, f"vectors_op{op}.txt")
        with open(vpath, "w") as f:
            f.write("\n".join(lines) + "\n")
        got = run_vectors(args.bin, vpath)
        if len(got) != len(lines):
            print(f"  [FAIL] {name}: vector count {len(lines)} vs {len(got)}")
            fails += 1
        bad_hf = bad_flag = bad_oracle = 0
        for r in got:
            rp = (r["in_hi"] << 64) | r["in_lo"]
            raw = F.raw_unpack(rp, ie, isig)
            mine_v = F.recfn_value(r["out"], oe, osig)
            hf_v = F.recfn_value(r["hf_out"], oe, osig)
            ol, ofl = F.round_exact(ie, isig, oe, osig, raw, r["mode"])
            or_v = F.recfn_value(ol, oe, osig)
            if mine_v != hf_v:
                bad_hf += 1
                if bad_hf <= 6:
                    print(f"  [DIFF] {name} mode={r['mode']} "
                          f"pack={rp:x} mine={r['out']:x} hf={r['hf_out']:x} "
                          f"mine_v={mine_v:x} hf_v={hf_v:x}")
            if r["flags"] != rev5(r["hf_flags"]):
                bad_flag += 1
                if bad_flag <= 6:
                    print(f"  [FLAG] {name} mode={r['mode']} pack={rp:x} "
                          f"mine={r['flags']:x} hf={rev5(r['hf_flags']):x}")
            if mine_v != or_v or r["flags"] != ofl:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} mode={r['mode']} pack={rp:x} "
                          f"mine_v={mine_v:x}/{r['flags']:x} "
                          f"oracle={or_v:x}/{ofl:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff={bad_hf} "
              f"hf-flag-diff={bad_flag} oracle-diff={bad_oracle}")
        fails += bad_hf + bad_flag + bad_oracle
        summary.append((name, len(got), bad_hf + bad_flag + bad_oracle))

    # ── conversions (m12-chipyard-012): mine vs hardfloat vs the oracle ─────
    MODES = (F.RNE, F.RTZ, F.RDN, F.RUP, F.RNA)
    # op -> (name, srcExp, srcSig, intWidth) / i2f (name, intWidth, outE, outS)
    F2I = {14: ("f2i ft->t32", F.FT[0], F.FT[1], 32),
           15: ("f2i ft->o64", F.FT[0], F.FT[1], 64),
           16: ("f2i fo->t32", F.FO[0], F.FO[1], 32),
           17: ("f2i fo->o64", F.FO[0], F.FO[1], 64)}
    I2F = {18: ("i2f t32->ft", 32, F.FT[0], F.FT[1]),
           19: ("i2f o64->ft", 64, F.FT[0], F.FT[1]),
           20: ("i2f t32->fo", 32, F.FO[0], F.FO[1]),
           21: ("i2f o64->fo", 64, F.FO[0], F.FO[1])}
    F2F = {22: ("f2f ft2fo", F.FT[0], F.FT[1], F.FO[0], F.FO[1], False),
           23: ("f2f fo2ft", F.FO[0], F.FO[1], F.FT[0], F.FT[1], True)}

    for op, (name, ew, sw, iw) in F2I.items():
        vals = F.sample_fn(ew, sw, args.n, rng)
        lines = [f"{op} {x:x} {signed:x} {mode}"
                 for x in vals for signed in (0, 1) for mode in MODES]
        got = run_vectors(args.bin, _write(args, f"vectors_op{op}.txt", lines),
                          )
        bad_hf = bad_flag = bad_oracle = 0
        for r in got:
            x, signed = r["in_lo"], bool(r["in_hi"] & 1)
            want, wflags = F.f2i_exact(ew, sw, x, iw, signed, r["mode"])
            if r["out"] != want or r["flags"] != wflags:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} x={x:x} signed={signed} "
                          f"mode={r['mode']} want={want:x}/{wflags:x} "
                          f"got={r['out']:x}/{r['flags']:x}")
            if r["out"] != r["hf_out"]:
                bad_hf += 1
                if bad_hf <= 6:
                    print(f"  [DIFF] {name} x={x:x} signed={signed} "
                          f"mode={r['mode']} mine={r['out']:x} "
                          f"hf={r['hf_out']:x}")
            if r["flags"] != r["hf_flags"]:
                bad_flag += 1
                if bad_flag <= 6:
                    print(f"  [FLAG] {name} x={x:x} signed={signed} "
                          f"mode={r['mode']} mine={r['flags']:x} "
                          f"hf={r['hf_flags']:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff={bad_hf} "
              f"hf-flag-diff={bad_flag} oracle-diff={bad_oracle}")
        fails += bad_hf + bad_flag + bad_oracle
        summary.append((name, len(got), bad_hf + bad_flag + bad_oracle))

    for op, (name, iw, oe, osig) in I2F.items():
        vals = F.sample_ints(iw, args.n, rng)
        lines = [f"{op} {v:x} {signed:x} {mode}"
                 for v in vals for signed in (0, 1) for mode in MODES]
        got = run_vectors(args.bin, _write(args, f"vectors_op{op}.txt", lines))
        bad_hf = bad_flag = bad_oracle = 0
        for r in got:
            v, signed = r["in_lo"], bool(r["in_hi"] & 1)
            want_rec, wflags = F.i2f_exact(iw, oe, osig, v, signed, r["mode"])
            want = F.fn_from_recfn(oe, osig, want_rec)
            if r["out"] != want or r["flags"] != wflags:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} v={v:x} signed={signed} "
                          f"mode={r['mode']} want={want:x}/{wflags:x} "
                          f"got={r['out']:x}/{r['flags']:x}")
            if fn_val(r["out"], oe, osig) != fn_val(r["hf_out"], oe, osig):
                bad_hf += 1
                if bad_hf <= 6:
                    print(f"  [DIFF] {name} v={v:x} signed={signed} "
                          f"mode={r['mode']} mine={r['out']:x} "
                          f"hf={r['hf_out']:x}")
            if r["flags"] != r["hf_flags"]:
                bad_flag += 1
                if bad_flag <= 6:
                    print(f"  [FLAG] {name} v={v:x} signed={signed} "
                          f"mode={r['mode']} mine={r['flags']:x} "
                          f"hf={r['hf_flags']:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff={bad_hf} "
              f"hf-flag-diff={bad_flag} oracle-diff={bad_oracle}")
        fails += bad_hf + bad_flag + bad_oracle
        summary.append((name, len(got), bad_hf + bad_flag + bad_oracle))

    for op, (name, sew, ssw, dew, dsw, force_inf) in F2F.items():
        vals = F.sample_fn(sew, ssw, args.n, rng)
        lines = [f"{op} {x:x} 0 {mode}" for x in vals for mode in MODES]
        got = run_vectors(args.bin, _write(args, f"vectors_op{op}.txt", lines))
        bad_hf = bad_flag = bad_oracle = 0
        for r in got:
            x = r["in_lo"]
            want_rec, wflags = F.f2f_exact(sew, ssw, dew, dsw, x, r["mode"],
                                           force_inf)
            want = F.fn_from_recfn(dew, dsw, want_rec)
            if r["out"] != want or r["flags"] != wflags:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} x={x:x} mode={r['mode']} "
                          f"want={want:x}/{wflags:x} got={r['out']:x}/{r['flags']:x}")
            if fn_val(r["out"], dew, dsw) != fn_val(r["hf_out"], dew, dsw):
                bad_hf += 1
                if bad_hf <= 6:
                    print(f"  [DIFF] {name} x={x:x} mode={r['mode']} "
                          f"mine={r['out']:x} hf={r['hf_out']:x}")
            if r["flags"] != r["hf_flags"]:
                bad_flag += 1
                if bad_flag <= 6:
                    print(f"  [FLAG] {name} x={x:x} mode={r['mode']} "
                          f"mine={r['flags']:x} hf={r['hf_flags']:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff={bad_hf} "
              f"hf-flag-diff={bad_flag} oracle-diff={bad_oracle}")
        fails += bad_hf + bad_flag + bad_oracle
        summary.append((name, len(got), bad_hf + bad_flag + bad_oracle))

    # ── the divide-by-zero (`DZ`) lane of the rounding primitive ───────────
    # m12-011 tied `infiniteExc` to zero, so this lane had never been
    # compared.  With the flag raised the primitive's own output pattern for a
    # plain normal input is not an architectural value (the real producer, the
    # division family, drives `in.isInf`, arriving in m12-chipyard-014), so
    # what is asserted here is: the `DZ` bit is raised (plus the `NX` of an
    # inexact input), the sign is the input's, the result is ±Infinity for the
    # input shapes the division family drives (`in` zero or infinite), and the
    # whole value/flag word equals hardfloat's bit for bit.
    vals = F.sample_fn(F.FT[0], F.FT[1], args.n, rng)
    lines = [f"24 {x:x} 0 {mode}" for x in vals for mode in MODES]
    got = run_vectors(args.bin, _write(args, "vectors_op24.txt", lines))
    dz_bad = dz_hf = 0
    dz_inf_checked = 0
    for r in got:
        x = r["in_lo"]
        raw = F.raw_from_fn(F.FT[0], F.FT[1], x)
        _, own_flags = F.round_exact(F.FT[0], F.FT[1], F.FT[0], F.FT[1],
                                     raw, F.RNE)
        want_flags = F.DZ | (own_flags & F.NX)
        if F.recfn_value(r["out"], F.FT[0], F.FT[1]) != \
                F.recfn_value(r["hf_out"], F.FT[0], F.FT[1]) or \
                r["flags"] != r["hf_flags"]:
            dz_hf += 1
            if dz_hf <= 6:
                print(f"  [DIFF] dz x={x:x} mine={r['out']:x}/{r['flags']:x} "
                      f"hf={r['hf_out']:x}/{r['hf_flags']:x}")
        inf_pattern = (raw["sign"] << (F.FT[0] + F.FT[1])) | \
            ((6 << (F.FT[0] - 2)) << (F.FT[1] - 1))
        want_value = r["out"]
        if raw["is_zero"] or raw["is_inf"]:
            want_value = inf_pattern
            dz_inf_checked += 1
        if r["flags"] != want_flags or r["out"] != want_value or \
                (not raw["is_nan"] and
                 (r["out"] >> (F.FT[0] + F.FT[1])) != raw["sign"]):
            dz_bad += 1
            if dz_bad <= 6:
                print(f"  [ORACLE] dz x={x:x} want={want_value:x}/{want_flags:x} "
                      f"got={r['out']:x}/{r['flags']:x}")
    ndz = sum(1 for r in got if (r["flags"] & F.DZ) != 0)
    print(f"  dz lane: {len(got)} vectors | hf-diff={dz_hf} oracle-diff={dz_bad} "
          f"dz-flag-raised={ndz} inf-shape-checked={dz_inf_checked}")
    fails += dz_hf + dz_bad
    summary.append(("dz lane", len(got), dz_hf + dz_bad))

    # ── arithmetic family (m12-chipyard-013) ──────────────────────────────
    # add/sub/mul/fma: value compared against hardfloat's RTL (NaNs collapsed,
    # since the two implementations pick different NaN payloads) and against
    # the exact oracle bit for bit (the DADAO payload rule is part of the
    # contract).  compare: value against hardfloat's lt/eq/gt and the NaN
    # constant, flags against hardfloat's own form (signalling compare raises
    # NV on any unordered pair; quiet compare raises it for an sNaN input
    # only, a documented divergence from spec/SimRISC-07 §4, which the core
    # follows).  min/max have no hardfloat counterpart: oracle only.
    BIN = {25: ("add ft", F.FT, False), 26: ("sub ft", F.FT, True),
           27: ("mul ft", F.FT, None),
           29: ("add fo", F.FO, False), 30: ("sub fo", F.FO, True),
           31: ("mul fo", F.FO, None)}
    FMA = {28: ("fma ft", F.FT), 32: ("fma fo", F.FO)}
    CMP = {33: ("qcmp ft", F.FT, False), 34: ("scmp ft", F.FT, True),
           35: ("qcmp fo", F.FO, False), 36: ("scmp fo", F.FO, True)}
    MM = {37: ("min ft", F.FT, False), 38: ("max ft", F.FT, True),
          39: ("min fo", F.FO, False), 40: ("max fo", F.FO, True)}
    MODES = (F.RNE, F.RTZ, F.RDN, F.RUP, F.RNA)

    for op, (name, (ew, sw), sub) in BIN.items():
        pairs = F.sample_pairs(ew, sw, args.n, rng)
        lines = [f"{op} {a:x} {b:x} {mode} 0"
                 for (a, b) in pairs for mode in MODES]
        got = run_vectors(args.bin, _write(args, f"vectors_op{op}.txt", lines))
        bad_hf = bad_flag = bad_oracle = uf_boundary = 0
        for r in got:
            a, b, mode = r["in_lo"], r["in_hi"], r["mode"]
            if sub is None:
                want, wflags = F.mul_exact(ew, sw, a, b, mode)
            else:
                want, wflags = F.add_exact(ew, sw, a, b, sub, mode)
            if r["out"] != want or r["flags"] != wflags:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} a={a:x} b={b:x} mode={mode} "
                          f"want={want:x}/{wflags:x} got={r['out']:x}/{r['flags']:x}")
            if fn_val(r["out"], ew, sw) != fn_val(r["hf_out"], ew, sw):
                bad_hf += 1
                if bad_hf <= 6:
                    print(f"  [DIFF] {name} a={a:x} b={b:x} mode={mode} "
                          f"mine={r['out']:x} hf={r['hf_out']:x}")
            if r["flags"] != r["hf_flags"]:
                if is_uf_boundary(r["out"], r["flags"], r["hf_flags"], ew, sw):
                    uf_boundary += 1
                    continue
                bad_flag += 1
                if bad_flag <= 6:
                    print(f"  [FLAG] {name} a={a:x} b={b:x} mode={mode} "
                          f"mine={r['flags']:x} hf={r['hf_flags']:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff={bad_hf} "
              f"hf-flag-diff={bad_flag} uf-boundary={uf_boundary} "
              f"oracle-diff={bad_oracle}")
        fails += bad_hf + bad_flag + bad_oracle
        summary.append((name, len(got), bad_hf + bad_flag + bad_oracle))

    for op, (name, (ew, sw)) in FMA.items():
        triples = F.sample_fma_triples(ew, sw, args.n, rng)
        lines = [f"{op} {a:x} {b:x} {mode} {c:x}"
                 for (a, b, c) in triples for mode in MODES]
        got = run_vectors(args.bin, _write(args, f"vectors_op{op}.txt", lines))
        bad_hf = bad_flag = bad_oracle = uf_boundary = 0
        for r in got:
            a, b, c, mode = r["in_lo"], r["in_hi"], r["in_extra"], r["mode"]
            want, wflags = F.fma_exact(ew, sw, a, b, c, mode)
            if r["out"] != want or r["flags"] != wflags:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} a={a:x} b={b:x} c={c:x} "
                          f"mode={mode} want={want:x}/{wflags:x} "
                          f"got={r['out']:x}/{r['flags']:x}")
            if fn_val(r["out"], ew, sw) != fn_val(r["hf_out"], ew, sw):
                bad_hf += 1
                if bad_hf <= 6:
                    print(f"  [DIFF] {name} a={a:x} b={b:x} c={c:x} "
                          f"mode={mode} mine={r['out']:x} hf={r['hf_out']:x}")
            if r["flags"] != r["hf_flags"]:
                if is_uf_boundary(r["out"], r["flags"], r["hf_flags"], ew, sw):
                    uf_boundary += 1
                    continue
                bad_flag += 1
                if bad_flag <= 6:
                    print(f"  [FLAG] {name} a={a:x} b={b:x} c={c:x} "
                          f"mode={mode} mine={r['flags']:x} hf={r['hf_flags']:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff={bad_hf} "
              f"hf-flag-diff={bad_flag} uf-boundary={uf_boundary} "
              f"oracle-diff={bad_oracle}")
        fails += bad_hf + bad_flag + bad_oracle
        summary.append((name, len(got), bad_hf + bad_flag + bad_oracle))

    for op, (name, (ew, sw), signaling) in CMP.items():
        pairs = F.sample_pairs(ew, sw, max(1, args.n // 4), rng)
        lines = [f"{op} {a:x} {b:x} 0 0" for (a, b) in pairs]
        got = run_vectors(args.bin, _write(args, f"vectors_op{op}.txt", lines))
        bad_hf = bad_flag = bad_oracle = quiet_snan = 0
        for r in got:
            a, b = r["in_lo"], r["in_hi"]
            want, wflags = F.cmp_exact(ew, sw, a, b, signaling)
            if r["out"] != want or r["flags"] != wflags:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} a={a:x} b={b:x} "
                          f"want={want:x}/{wflags:x} got={r['out']:x}/{r['flags']:x}")
            if r["out"] != r["hf_out"]:
                bad_hf += 1
                if bad_hf <= 6:
                    print(f"  [DIFF] {name} a={a:x} b={b:x} "
                          f"mine={r['out']:x} hf={r['hf_out']:x}")
            if r["flags"] != r["hf_flags"]:
                if is_cmp_snan_quiet_divergence(ew, sw, a, b, signaling,
                                                r["flags"], r["hf_flags"]):
                    quiet_snan += 1
                    continue
                bad_flag += 1
                if bad_flag <= 6:
                    print(f"  [FLAG] {name} a={a:x} b={b:x} "
                          f"mine={r['flags']:x} hf={r['hf_flags']:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff={bad_hf} "
              f"hf-flag-diff={bad_flag} hf-quiet-snan-divergence={quiet_snan} "
              f"oracle-diff={bad_oracle}")
        fails += bad_hf + bad_flag + bad_oracle
        summary.append((name, len(got), bad_hf + bad_flag + bad_oracle))

    for op, (name, (ew, sw), is_max) in MM.items():
        pairs = F.sample_pairs(ew, sw, max(1, args.n // 4), rng)
        lines = [f"{op} {a:x} {b:x} 0 0" for (a, b) in pairs]
        got = run_vectors(args.bin, _write(args, f"vectors_op{op}.txt", lines))
        bad_oracle = 0
        for r in got:
            a, b = r["in_lo"], r["in_hi"]
            want, wflags = F.minmax_exact(ew, sw, a, b, is_max)
            if r["out"] != want or r["flags"] != wflags:
                bad_oracle += 1
                if bad_oracle <= 6:
                    print(f"  [ORACLE] {name} a={a:x} b={b:x} "
                          f"want={want:x}/{wflags:x} got={r['out']:x}/{r['flags']:x}")
        print(f"  {name}: {len(got)} vectors | hf-value-diff=n/a "
              f"hf-flag-diff=n/a oracle-diff={bad_oracle}")
        fails += bad_oracle
        summary.append((name, len(got), bad_oracle))

    # ── FCSR (clocked) ────────────────────────────────────────────────────
    fpath = os.path.join(args.workdir, "fcsr.txt")
    seq = [
        (0, 0x0, 0x00),  # reset value read back
        (0, 0x0, 0x01),  # NV accumulates
        (0, 0x0, 0x02),  # DZ accumulates on top
        (0, 0x0, 0x04),  # OF
        (0, 0x0, 0x08),  # UF
        (0, 0x0, 0x10),  # NX
        (1, 0x0, 0x00),  # software clear: all five flags drop
        (1, 0x7FF800037FC00003, 0x00),  # mode <- 11b (RUP), flags <- 3
        (0, 0x0, 0x10),  # NX accumulates on top of 3
        (1, 0x0000000000000000, 0x00),  # write everything: only [33:32],[4:0] take
    ]
    with open(fpath, "w") as f:
        for en, data, ff in seq:
            f.write(f"{en} {data:x} {ff}\n")
    out = subprocess.run([args.bin, "--fcsr", fpath], check=True,
                         capture_output=True, text=True).stdout
    reads = [int(l.split()[4], 16) for l in out.splitlines() if l.startswith("F")]
    const = 0x7FF800007FC00000
    want = [
        const | 0x00,
        const | 0x01,
        const | 0x03,
        const | 0x07,
        const | 0x0F,
        const | 0x1F,
        const | 0x00,
        (const | (3 << 32) | 0x03),
        (const | (3 << 32) | 0x13),
        (const & ~0x300000000) | 0x00,
    ]
    fcsr_bad = 0
    for i, (g, w) in enumerate(zip(reads, want)):
        if g != w:
            fcsr_bad += 1
            print(f"  [FAIL] fcsr step {i}: want={w:016x} got={g:016x}")
    print(f"  fcsr: {len(reads)} steps | mismatches={fcsr_bad}")
    fails += fcsr_bad
    summary.append(("fcsr", len(reads), fcsr_bad))

    print("== fp unit summary ==")
    for name, n, nf in summary:
        print(f"  {name:24s} vectors={n:6d} failed={nf}")
    print(f"  TOTAL failed={fails}")
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260111)
    args = ap.parse_args()
    os.makedirs(args.workdir, exist_ok=True)
    return check(args)


if __name__ == "__main__":
    sys.exit(main())
