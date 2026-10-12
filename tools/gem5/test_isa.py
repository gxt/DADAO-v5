#!/usr/bin/env python3
"""Run independent spec-derived add.si vectors through gem5 AtomicSimpleCPU."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(
    subprocess.check_output(
        [sys.executable, str(ROOT / "tools/infra/paths.py"), "test_artifacts_dir"],
        text=True,
    ).strip()
) / "gem5"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gem5", type=Path,
                        default=Path(os.environ.get(
                            "DADAO_GEM5_BINARY",
                            ROOT / ".work/source/gem5/build/DADAO/gem5.opt")))
    parser.add_argument("--profile", choices=("current", "skeleton"),
                        default="current",
                        help="select the current suite or the GEM5-003t suite")
    parser.add_argument("--vector-root", type=Path,
                        default=ROOT / "tests/vectors/isa",
                        help="read ISA YAML files from this directory")
    args = parser.parse_args()
    gem5 = args.gem5.resolve()
    vector_root = args.vector_root.resolve()
    if not gem5.is_file():
        raise SystemExit(f"gem5-isa: missing {gem5}; run make build-gem5")
    if not vector_root.is_dir():
        raise SystemExit(f"gem5-isa: missing vector root {vector_root}")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    vectors = yaml.safe_load((vector_root / "reg-arith.yaml").read_text())
    cases = [
        x for x in vectors
        if x.get("id") == "add.si_riii_rd"
        and x.get("class") in {"semantic", "legality"}
        and x.get("status") == "active"
        and (x.get("class") == "legality" or
             x.get("input_state", {}).get("rd", {}).get("rd1"))
    ]
    if len(cases) < 3:
        raise SystemExit("gem5-isa: expected at least two active add.si semantic vectors")
    arithmetic = [x for x in vectors if x.get("id") == "add.uo_rrrr_rd"
                  and x.get("class") in {"semantic", "boundary", "legality"}
                  and x.get("status") == "active"]
    reserved = yaml.safe_load((vector_root / "reserved.yaml").read_text())
    rb_arithmetic = [x for x in vectors if x.get("id") == "add.si_riii_rb"
                     and x.get("class") in {"semantic", "legality"}
                     and x.get("status") == "active"]
    scalar = []
    control = []
    if args.profile == "current":
        scalar_ids = {
            "or.w_rwii_rd", "andn.w_rwii_rd", "set.zw_rwii_rd",
            "set.ow_rwii_rd", "cmp.ui_rrii_rd", "cmp.si_rrii_rd",
        }
        for filename in ("reg-imm-block.yaml", "reg-compare.yaml"):
            scalar.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if x.get("id") in scalar_ids
                and x.get("class") in {"semantic", "legality"}
                and x.get("status") == "active")
        for filename in ("ctrl-br.yaml", "ctrl-jump.yaml"):
            control.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if x.get("class") == "semantic"
                and x.get("status") == "active")
        for case in control:
            case["initial_pc"] = 0xFC0000000000
            case["image_addr"] = 0xFC0000000000
    cases += arithmetic + rb_arithmetic + scalar + control + reserved
    # SimRISC-04: imms18 is signed; 0x3ffff sign-extends to -1.
    cases.append({"encoding": {"word": "0x5907ffff"},
                  "input_state": {"rd": {"rd1": "0x0"}},
                  "expected_state": {"rd": {"rd1": "0xffffffffffffffff"}}})
    cases.append({"encoding": {"word": "0x00000000"},
                  "expected_fault": "UNDI", "input_state": {}})
    cases.append({"encoding": {"word": "0x510420c4"},
                  "expected_fault": "ILLI", "input_state": {}})
    cases.append({"encoding": {"word": "0x59040001"},
                  "initial_pc": 0xFFFFFFFF0002,
                  "expected_fault": "IALIGN", "input_state": {}})
    for number, case in enumerate(cases):
        word = int(case["encoding"]["word"], 0)
        rom = ARTIFACTS / f"isa_{number}.bin"
        rom.write_bytes(word.to_bytes(4, "big"))
        initial_rd = case.get("input_state", {}).get("rd", {})
        expected_rd = (case.get("expected_state") or {}).get("rd", {})
        initial_rb = case.get("input_state", {}).get("rb", {})
        expected_rb = (case.get("expected_state") or {}).get("rb", {})
        initial = int(initial_rd.get("rd1", "0"), 0)
        expected = int(expected_rd["rd1"], 0) if "rd1" in expected_rd else initial
        command = [
            str(gem5), "--outdir", str(ARTIFACTS / f"run_{number}"),
            str(ROOT / "tests/gem5/isa_fixture.py"),
            "--rom", str(rom), "--initial-rd1", hex(initial),
            "--expected-rd1", hex(expected),
            "--initial-rd", json.dumps(initial_rd),
            "--expected-rd", json.dumps(expected_rd),
            "--initial-rb", json.dumps(initial_rb),
            "--expected-rb", json.dumps(expected_rb),
            "--expected-fault", case.get("expected_fault") or "none",
            "--initial-pc", hex(case.get("initial_pc", 0xFFFFFFFF0000)),
            "--image-addr", hex(case.get("image_addr", 0xFFFFFFFF0000)),
        ]
        if case.get("expected_pc") is not None:
            command += ["--expected-pc", case["expected_pc"]]
        print(f"gem5-isa: vector {number} word={word:#010x}", flush=True)
        result = subprocess.run(command, timeout=30, check=False)
        if result.returncode:
            return result.returncode
    print(f"gem5-isa: PASS {len(cases)} {args.profile} spec vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
