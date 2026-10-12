#!/usr/bin/env python3
"""Inventory spec-derived ISA vectors available for gem5 execution gates."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    opcodes = yaml.safe_load((ROOT / "contracts/opcodes.yaml").read_text())
    vectors = []
    for path in sorted((ROOT / "tests/vectors/isa").glob("*.yaml")):
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
        f"{len(encoding)}/{len(opcodes)} opcodes have active encoding vectors; "
        f"missing by scope={dict(sorted(Counter(x['scope'] for x in missing).items()))}"
    )
    for opcode in missing:
        print(f"  NEED {opcode['id']} ({opcode['scope']}, {opcode['format']})")
    if args.require_complete and missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
