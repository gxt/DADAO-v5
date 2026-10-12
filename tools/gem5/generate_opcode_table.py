#!/usr/bin/env python3
"""Generate the gem5 defined-encoding predicate from the ISA contract."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/opcodes.yaml"
OUTPUT = ROOT / ".work/source/gem5/src/arch/dadao/opcode_table.hh"


def render() -> str:
    opcodes = yaml.safe_load(CONTRACT.read_text())
    rows = sorted({(int(x["mask"], 0), int(x["value"], 0)) for x in opcodes})
    lines = [
        "// Generated from contracts/opcodes.yaml by",
        "// tools/gem5/generate_opcode_table.py. Do not edit by hand.",
        "#ifndef __ARCH_DADAO_OPCODE_TABLE_HH__",
        "#define __ARCH_DADAO_OPCODE_TABLE_HH__",
        "#include <cstdint>",
        "namespace gem5::DadaoISA {",
        "inline constexpr bool isDefinedEncoding(uint32_t word)",
        "{",
        "    return",
    ]
    lines += [
        f"        ((word & 0x{mask:08x}U) == 0x{value:08x}U) ||"
        for mask, value in rows
    ]
    lines[-1] = lines[-1][:-3] + ";"
    lines += ["}", "}", "#endif", ""]
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != expected:
            raise SystemExit("gem5 opcode table is stale")
    else:
        OUTPUT.write_text(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
