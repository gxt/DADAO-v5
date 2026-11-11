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
                        out=int(f[6], 16) << 64 | int(f[5], 16),
                        flags=int(f[7], 16),
                        hf_out=int(f[9], 16) << 64 | int(f[8], 16),
                        hf_flags=int(f[10], 16)))
    return res


_shown = {}


def requires_show(op):
    _shown[op] = _shown.get(op, 0) + 1
    return _shown[op] <= 4


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
