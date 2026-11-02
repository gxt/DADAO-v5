#!/usr/bin/env python3
"""Compile and run the standalone DADAO B2 execution assertion harness.

The harness is plain C++17 (no gem5 dependencies), so the B2 semantics can be
checked without a full gem5 build.  It is compiled together with the B0 decode
core (the harness needs the contract-driven decode table).

The B2 id set printed by the harness (an explicit list, one id per line) is
cross-checked here against the *live* `batch_of()` set derived from
`contracts/opcodes.yaml` + the GEM5-002t matrix, so a batch boundary change can
never silently pass.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B2_ID = re.compile(r"^\[PASS\] b2-id (\S+)$", re.MULTILINE)

# contracts/opcodes.yaml rule_refs for the 8 B2 rows: dst_rd0 (4), dst_rb0 (3),
# set.w has none (contract-fp §13/§15: rf0 is a legal destination).
EXPECTED_RULES = {
    "or.w_rwii_rd": "dst_rd0",
    "andn.w_rwii_rd": "dst_rd0",
    "or.w_rwii_rb": "dst_rb0",
    "andn.w_rwii_rb": "dst_rb0",
    "set.zw_rwii_rd": "dst_rd0",
    "set.ow_rwii_rd": "dst_rd0",
    "set.zw_rwii_rb": "dst_rb0",
    "set.w_rwii_rf": None,
}


def live_b2_entries():
    """Derive the B2 rows from the contracts with the table generator."""
    path = ROOT / "tools/gem5/gen_decode_table.py"
    spec = importlib.util.spec_from_file_location("gen_decode_table", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return [entry for entry in module.load_entries() if entry.batch == "B2"]


def contract_rule_errors(entries) -> list[str]:
    """Cross-check the live rule_refs/spec_cite against the contract mapping."""
    errors: list[str] = []
    by_id = {entry.id: entry for entry in entries}
    for entry_id, rule in EXPECTED_RULES.items():
        entry = by_id.get(entry_id)
        if entry is None:
            errors.append(f"{entry_id}: missing from the live B2 set")
            continue
        expected = () if rule is None else (rule,)
        if entry.rules != expected:
            errors.append(
                f"{entry_id}: rule_refs {entry.rules!r} != {expected!r}")
        if not entry.spec_cite:
            errors.append(f"{entry_id}: missing spec_cite")
    for entry in entries:
        if any(rule not in ("dst_rd0", "dst_rb0") for rule in entry.rules):
            errors.append(f"{entry.id}: unknown rule_refs {entry.rules!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"),
                        help="gem5 worktree (default .work/source/gem5)")
    parser.add_argument("--out", type=Path,
                        default=Path(".work/build/gem5/dadao-b2-test"))
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    needed = [
        source / "src/arch/dadao/decode/decode.hh",
        source / "src/arch/dadao/exec/common.hh",
        source / "src/arch/dadao/exec/b2.hh",
        source / "src/arch/dadao/exec/b2.cc",
        source / "src/arch/dadao/exec/b2_test.cc",
    ]
    missing = [str(path) for path in needed if not path.exists()]
    if missing:
        print("check-gem5-b2: missing input(s); run `make apply-series` first:",
              file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(source / "src"),
        str(source / "src/arch/dadao/decode/decode.cc"),
        str(source / "src/arch/dadao/exec/b2.cc"),
        str(source / "src/arch/dadao/exec/b2_test.cc"),
        "-o", str(out),
    ]
    print("check-gem5-b2: compile:", " ".join(cmd))
    built = subprocess.run(cmd)
    if built.returncode != 0:
        print(f"check-gem5-b2: compile FAILED rc={built.returncode}",
              file=sys.stderr)
        return built.returncode

    print(f"check-gem5-b2: run: {out}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)

    failures = run.stdout.count("[FAIL]")
    reported = sorted(B2_ID.findall(run.stdout))
    entries = live_b2_entries()
    live = sorted(entry.id for entry in entries)
    rule_errors = contract_rule_errors(entries)

    ok = True
    if "B2 coverage 8/8" not in run.stdout:
        print("check-gem5-b2: FAIL -- missing 'B2 coverage 8/8' marker",
              file=sys.stderr)
        ok = False
    if len(reported) != 8:
        print(f"check-gem5-b2: FAIL -- harness listed {len(reported)} B2 ids, "
              "expected 8", file=sys.stderr)
        ok = False
    if reported != live:
        extra = sorted(set(reported) - set(live))
        missing_ids = sorted(set(live) - set(reported))
        print("check-gem5-b2: FAIL -- harness B2 id set != live batch_of() set",
              file=sys.stderr)
        if extra:
            print(f"  only in harness: {extra}", file=sys.stderr)
        if missing_ids:
            print(f"  only in contracts: {missing_ids}", file=sys.stderr)
        ok = False
    if rule_errors:
        print("check-gem5-b2: FAIL -- contract rule/spec_cite mismatch:",
              file=sys.stderr)
        for error in rule_errors:
            print(f"  {error}", file=sys.stderr)
        ok = False
    if failures != 0:
        print(f"check-gem5-b2: FAIL -- {failures} [FAIL] line(s)",
              file=sys.stderr)
        ok = False
    if run.returncode != 0:
        print(f"check-gem5-b2: FAIL -- harness rc={run.returncode}",
              file=sys.stderr)
        ok = False

    print(f"check-gem5-b2: b2 ids {len(reported)}/8, live {len(live)}, "
          f"failures {failures}, rc={run.returncode}")
    if not ok:
        return 1
    print("check-gem5-b2: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
