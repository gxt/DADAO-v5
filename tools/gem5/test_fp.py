#!/usr/bin/env python3
"""Run gem5 against the existing spec-derived DADAO FP probe cases."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(
    subprocess.check_output(
        [sys.executable, str(ROOT / "tools/infra/paths.py"),
         "test_artifacts_dir"],
        text=True,
    ).strip()
) / "gem5" / "fp"
PROBES = (
    ROOT / "tools/qemu/min_rom_probe_034t.py",
    ROOT / "tools/qemu/min_rom_probe_035t.py",
    ROOT / "tools/qemu/min_rom_probe_036t.py",
    ROOT / "tools/qemu/min_rom_probe_037t.py",
)


def load_probe(path: Path):
    name = f"_gem5_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gem5",
        type=Path,
        default=Path(os.environ.get(
            "DADAO_GEM5_BINARY",
            ROOT / ".work/source/gem5/build/DADAO/gem5.opt")),
    )
    parser.add_argument(
        "--inject",
        action="store_true",
        help="corrupt the first FP expected value; the gate must fail",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="run only this many cases (used for the initial red gate)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="skip this many cases while diagnosing a later failure",
    )
    args = parser.parse_args()
    gem5 = args.gem5.resolve()
    if not gem5.is_file():
        raise SystemExit(f"gem5-fp: missing {gem5}; run make build-gem5")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    selected = []
    for path in PROBES:
        module = load_probe(path)
        derivation = getattr(module, "verify_derivations", None)
        if derivation:
            failures = [name for name, ok in derivation() if not ok]
            if failures:
                raise SystemExit(
                    f"gem5-fp: independent oracle self-check failed: "
                    f"{failures[0]}"
                )
        for case in module.CASES:
            if case.e2e:
                continue
            selected.append((module, case))

    selected = selected[args.start:]
    if args.limit is not None:
        selected = selected[:args.limit]
    if args.inject:
        for _, case in selected:
            values = case.expect_rf or case.expect_rd
            if values:
                index = next(iter(values))
                values[index] ^= 1
                break
        else:
            raise SystemExit("gem5-fp: no value case available for injection")

    for number, (module, case) in enumerate(selected):
        value_case = bool(case.expect_rf or case.expect_rd)
        rom_data = (
            module.build_rom(case.insns)
            if value_case else module.build_fault_rom(case.insns)
        )
        expected_code = case.expect_exit
        rom = ARTIFACTS / f"fp_{number:03d}.bin"
        rom.write_bytes(rom_data)
        command = [
            str(gem5),
            "--outdir", str(ARTIFACTS / f"run_{number:03d}"),
            str(ROOT / "tests/gem5/fp_fixture.py"),
            "--rom", str(rom),
            "--expected-rd", json.dumps(case.expect_rd),
            "--expected-rf", json.dumps(case.expect_rf),
            "--expected-code", hex(expected_code),
            "--ticks", str((len(rom_data) // 4 + 2) * 1000 + 1),
        ]
        print(
            f"gem5-fp: case {number + 1}/{len(selected)} {case.name}",
            flush=True,
        )
        result = subprocess.run(command, timeout=30, check=False)
        if result.returncode:
            return result.returncode

    print(f"gem5-fp: PASS {len(selected)} spec-derived cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
