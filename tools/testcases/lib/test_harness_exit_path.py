#!/usr/bin/env python3
"""Harness self-test: FAIL-path exit semantics + readable exit codes.

Covers two previously-broken harness behaviours (ISS-309 / ISS-319):

1. ISS-309 — a deliberately failing vector must land on the generated FAIL
   label and exit with guest code 1.  With the old `br.nz` offset (implicit
   `PC+4` base) it lands one word early, on the PASS block's semihosting trap,
   and QEMU dies with SIGABRT instead.
2. ISS-319 — negative host return codes (signals) must be rendered readably
   (SIGABRT + two's-complement), and a real timeout must be reported as a
   timeout, not as an unknown exit code.

Usage:
  python3 tools/testcases/lib/test_harness_exit_path.py            # green path
  python3 tools/testcases/lib/test_harness_exit_path.py --inject   # prove FAIL is reachable
Exit: 0 = all checks passed; 1 = at least one check failed.
"""
import argparse
import copy
import os
import struct
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))          # tools/testcases/lib
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

import build_test_binary as btb          # noqa: E402
import run_qemu_test as rqt              # noqa: E402

VECTOR = os.path.join(REPO, "tests", "inst", "base", "reg-arith.yaml")
TRAMPOLINE = os.path.join(HERE, "trampoline.bin")
WORK = os.path.join("/tmp", "opencode", "TESTCASES-061t", "harness-exit")


def _fail_case():
    """First semantic case with expected RD state, with one expectation flipped."""
    with open(VECTOR) as f:
        cases = yaml.safe_load(f)
    for case in cases:
        if case.get("class") != "semantic":
            continue
        rd = (case.get("expected_state") or {}).get("rd") or {}
        if not rd:
            continue
        bad = copy.deepcopy(case)
        reg = sorted(rd)[0]
        bad["expected_state"]["rd"][reg] = hex(int(rd[reg], 16) ^ 1)
        return case, bad
    raise SystemExit("no semantic case with expected_state.rd found")


def _write_bin(blob, name):
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, name)
    with open(path, "wb") as f:
        f.write(blob)
    return path


def _run(blob, name, timeout=9):
    qemu = rqt.find_qemu()
    if not qemu:
        raise SystemExit("qemu-system-dadao not found")
    path = _write_bin(blob, name)
    return rqt.run_qemu(qemu, TRAMPOLINE, path, timeout=timeout)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject", action="store_true",
                    help="simulate the pre-ISS-309 offset and require a trap")
    args = ap.parse_args(argv)

    checks = []

    def check(name, expected, actual, ok):
        checks.append((name, expected, actual, ok))
        print("  [%s] %s: expected=%s actual=%s"
              % ("PASS" if ok else "FAIL", name, expected, actual))

    good_case, bad_case = _fail_case()
    print("harness exit-path self-test: vector=%s case=%s"
          % (os.path.relpath(VECTOR, REPO), good_case.get("id")))

    # -- green PASS case: the untouched expectation must exit 0 -------------
    rc, _err, timed_out, _d = _run(btb.build_test_binary(good_case), "pass.bin")
    check("PASS case exits 0", "rc=0", "rc=%s" % rc, rc == 0 and not timed_out)

    # -- deliberately failing case: must exit guest FAIL (1), not a signal -
    if args.inject:
        original = btb.encode_br_nz_rd

        def old_offset(rdha, imms18):
            # pre-ISS-309: offset counted from PC+4, i.e. one word short
            return original(rdha, imms18 - 1)

        btb.encode_br_nz_rd = old_offset
        try:
            rc, _err, timed_out, _d = _run(btb.build_test_binary(bad_case),
                                           "fail-inject.bin")
        finally:
            btb.encode_br_nz_rd = original
        check("inject (old br.nz offset): failure lands in the trap",
              "host signal (negative rc), i.e. NOT guest rc=1",
              "rc=%s timed_out=%s" % (rc, timed_out), rc < 0 and not timed_out)
        return 0 if all(c[3] for c in checks) else 1

    rc, _err, timed_out, _d = _run(btb.build_test_binary(bad_case), "fail.bin")
    check("deliberately failing case lands on FAIL label",
          "rc=1 (guest SYS_EXIT)", "rc=%s timed_out=%s" % (rc, timed_out),
          rc == 1 and not timed_out)

    # -- ISS-319: readable formatting + real timeout ------------------------
    status, desc = rqt.interpret_exit_code(-6)
    check("SIGABRT is readable", "FAIL + SIGABRT, no '0x-6'",
          "%s / %s" % (status, desc),
          status == "FAIL" and "SIGABRT" in desc and "0x-6" not in desc)

    status, desc = rqt.interpret_exit_code(-1)
    check("timeout is a timeout", "INCONCLUSIVE + Timeout",
          "%s / %s" % (status, desc),
          status == "INCONCLUSIVE" and desc.startswith("Timeout"))

    # spin at the current PC forever (jump rb0, rd0, 0) -> real timeout
    spin = struct.pack(">I", 0x71000000)
    rc, _err, timed_out, _d = _run(spin, "spin.bin", timeout=1)
    status, desc = rqt.interpret_exit_code(rc)
    check("real timeout case", "timed_out=True, INCONCLUSIVE/Timeout",
          "rc=%s timed_out=%s -> %s / %s" % (rc, timed_out, status, desc),
          timed_out and status == "INCONCLUSIVE" and desc.startswith("Timeout"))

    ok = all(c[3] for c in checks)
    print("%s: %d/%d checks passed"
          % ("PASS" if ok else "FAIL", sum(1 for c in checks if c[3]),
             len(checks)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
