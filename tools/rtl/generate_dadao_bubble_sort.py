#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts/opcodes.yaml"


def field_range(text: str) -> tuple[int, int]:
    high, low = text.strip("[]").split(":")
    return int(high), int(low)


def encode(opcode_id: str, **values: int) -> int:
    entries = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    entry = next(item for item in entries if item["id"] == opcode_id)
    word = int(entry["value"], 16)
    fields = {field["name"]: field for field in entry["fields"]}

    for name, value in values.items():
        high, low = field_range(fields[name]["bits"])
        width = high - low + 1
        if value < 0 or value >= (1 << width):
            raise ValueError(f"{name}={value} does not fit in {width} bits")
        mask = ((1 << width) - 1) << low
        word = (word & ~mask) | (value << low)
    return word


def generate() -> tuple[list[tuple[str, int]], list[int], list[int]]:
    initial = [5, 1, 4, 2, 3]
    program: list[tuple[str, int]] = []

    def emit(assembly: str, opcode_id: str, **values: int) -> None:
        program.append((assembly, encode(opcode_id, **values)))

    for index, value in enumerate(initial, start=1):
        emit(
            f"set.zw rd{index}, wp0, {value}",
            "set.zw_rwii_rd",
            rdha=index,
            wpN=0,
            immu16=value,
        )

    for pass_index in range(len(initial) - 1):
        for left in range(1, len(initial) - pass_index):
            right = left + 1
            emit(
                f"cmp.uo rd7, rd{left}, rd{right}  # pass {pass_index + 1}",
                "cmp.uo_orrr_rd",
                rdhb=7,
                rdhc=left,
                rdhd=right,
            )
            emit(
                f"br.np rd7, +4",
                "br.np_riii_rd",
                rdha=7,
                imms18=4,
            )
            emit(
                f"rd2rd rd6, rd{left}, 1",
                "rd2rd_orri_rd",
                rdhb=6,
                rdhc=left,
                immu6=1,
            )
            emit(
                f"rd2rd rd{left}, rd{right}, 1",
                "rd2rd_orri_rd",
                rdhb=left,
                rdhc=right,
                immu6=1,
            )
            emit(
                f"rd2rd rd{right}, rd6, 1",
                "rd2rd_orri_rd",
                rdhb=right,
                rdhc=6,
                immu6=1,
            )

    for index in range(len(initial)):
        emit(
            f"st.w rd{index + 1}, [rb2, {index * 2}]",
            "st.w_rrii_rd",
            rdha=index + 1,
            rbhb=2,
            imms12=index * 2,
        )
    for index in range(len(initial)):
        emit(
            f"ld.uw rd{index + 8}, [rb2, {index * 2}]",
            "ld.uw_rrii_rd",
            rdha=index + 8,
            rbhb=2,
            imms12=index * 2,
        )
    emit("swym 0", "swym_oiii_imm", immu18=0)

    expected = sorted(initial)
    return program, initial, expected


def write_outputs(
    program: list[tuple[str, int]],
    initial: list[int],
    expected: list[int],
) -> None:
    yaml_path = ROOT / "tests/rtl/core/RTL-012t-bubble-sort-program.yaml"
    scala_path = (
        ROOT
        / "rtl/dadao/src/test/scala/dadao/DADAOBubbleSortProgram.scala"
    )
    hex_path = ROOT / "tests/rtl/core/RTL-012t-bubble-sort-program.hex"
    bin_path = ROOT / "tests/rtl/core/RTL-012t-bubble-sort-program.bin"

    yaml_lines = [
        "metadata:",
        "  task: RTL-012t",
        "  generator: tools/rtl/generate_dadao_bubble_sort.py",
        "  immutable_during_test: true",
        f"  initial_values: {initial}",
        f"  expected_values: {expected}",
        "program:",
    ]
    for index, (assembly, word) in enumerate(program):
        if assembly.startswith("#"):
            continue
        yaml_lines.extend(
            [
                f"- pc_offset: {index * 4}",
                f"  assembly: {assembly!r}",
                f"  word: '0x{word:08x}'",
            ]
        )
    yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    scala_lines = [
        "package dadao",
        "",
        "private[dadao] object DADAOBubbleSortProgram {",
        "  val initialValues: Seq[BigInt] = Seq(",
        "    " + ", ".join(str(value) for value in initial),
        "  )",
        "  val expectedValues: Seq[BigInt] = Seq(",
        "    " + ", ".join(str(value) for value in expected),
        "  )",
        "  val words: Seq[BigInt] = Seq(",
    ]
    for start in range(0, len(program), 4):
        chunk = program[start : start + 4]
        rendered = ", ".join(f'BigInt("{word:08x}", 16)' for _, word in chunk)
        scala_lines.append(f"    {rendered},")
    scala_lines.extend(["  )", "}", ""])
    scala_path.write_text("\n".join(scala_lines), encoding="utf-8")

    words = [word for _, word in program]
    hex_path.write_text(
        "".join(f"{word:08x}\n" for word in words),
        encoding="ascii",
    )
    bin_path.write_bytes(
        b"".join(word.to_bytes(4, byteorder="big") for word in words)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the RTL-012t DADAO bubble-sort program."
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    program, initial, expected = generate()
    if args.write:
        write_outputs(program, initial, expected)

    print(f"instructions={len(program)}")
    print(f"input={initial}")
    print(f"output={expected}")
    for index, (assembly, word) in enumerate(program):
        print(f"{index * 4:04x}: {word:08x}  {assembly}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
