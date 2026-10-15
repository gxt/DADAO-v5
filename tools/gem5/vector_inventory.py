#!/usr/bin/env python3
"""Inventory spec-derived ISA vectors available for gem5 execution gates."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_M1 = {
    "ret_riii_ra",
    "cfx2rd_crrr_cfx",
    "cfx2rc_crrr_cfx",
    "escape_ciii_cfx",
    "trap_ciii_cfx",
}
FP_PROBES = (
    ROOT / "tools/qemu/min_rom_probe_034t.py",
    ROOT / "tools/qemu/min_rom_probe_035t.py",
    ROOT / "tools/qemu/min_rom_probe_036t.py",
    ROOT / "tools/qemu/min_rom_probe_037t.py",
)


def fp_function(opcode: dict) -> str:
    mnemonic = opcode["mnemonic"].replace(".", "_")
    suffix = "_rf" if opcode["id"] in {
        "set.w_rwii_rf",
        "cs.eq_rrrr_rf", "cs.ne_rrrr_rf", "cs.n_rrrr_rf",
        "cs.z_rrrr_rf", "cs.p_rrrr_rf",
    } or "_rrii_rf" in opcode["id"] or "_rrri_rf" in opcode["id"] else ""
    return mnemonic + suffix


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    opcodes = yaml.safe_load((ROOT / "contracts/opcodes.yaml").read_text())
    vectors = []
    for path in sorted((ROOT / "tests/vectors").glob("*/*.yaml")):
        vectors.extend(yaml.safe_load(path.read_text()) or [])

    by_id = {opcode["id"]: opcode for opcode in opcodes}
    if len(by_id) != len(opcodes):
        raise SystemExit("gem5-vectors: duplicate opcode id")
    encoding = {
        vector["id"]
        for vector in vectors
        if vector.get("class") == "encoding"
        and vector.get("status") == "active"
    }
    encoding.update(RUNTIME_M1)
    encoding.add("sub.o_orrr_dbb")
    encoding.update(
        opcode["id"] for opcode in opcodes
        if opcode["scope"] == "excluded"
    )

    probe_text = "\n".join(path.read_text() for path in FP_PROBES)
    missing_fp_functions = []
    for opcode in opcodes:
        if opcode["scope"] != "fp":
            continue
        function = fp_function(opcode)
        defined = re.search(
            rf"^def {re.escape(function)}\(", probe_text, re.MULTILINE)
        exercised = probe_text.count(f"{function}(") >= 2
        if not defined or not exercised:
            missing_fp_functions.append(
                f"{opcode['id']} -> {function}()")
        else:
            encoding.add(opcode["id"])
    if missing_fp_functions:
        raise SystemExit(
            "gem5-vectors: FP probe function coverage missing: " +
            ", ".join(missing_fp_functions)
        )
    for vector in vectors:
        if vector.get("class") != "encoding" or vector.get("status") != "active":
            continue
        opcode = by_id.get(vector["id"])
        if opcode is None:
            raise SystemExit(f"gem5-vectors: unknown encoding id {vector['id']}")
        word = int(vector["encoding"]["word"], 0)
        mask = int(opcode["mask"], 0)
        value = int(opcode["value"], 0)
        if word & mask != value:
            raise SystemExit(
                f"gem5-vectors: {vector['id']} word {word:#010x} violates "
                f"mask/value {mask:#010x}/{value:#010x}"
            )

    missing = [opcode for opcode in opcodes if opcode["id"] not in encoding]
    print(
        "gem5-vectors: "
        f"{len(encoding)}/{len(opcodes)} opcodes have executable coverage "
        "evidence; "
        f"missing by scope={dict(sorted(Counter(x['scope'] for x in missing).items()))}"
    )
    for opcode in missing:
        print(f"  NEED {opcode['id']} ({opcode['scope']}, {opcode['format']})")
    if args.require_complete and missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
