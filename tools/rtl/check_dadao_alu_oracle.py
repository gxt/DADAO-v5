#!/usr/bin/env python3
"""Generate independent RTL-009t ALU vectors and Scala expectations."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = ROOT / "tests/rtl/core/RTL-009t-alu-vectors.yaml"
DEFAULT_SCALA = (
    ROOT / "rtl/dadao/src/test/scala/dadao/DADAOALUOracleTable.scala"
)

OP = {
    "ADD": 1,
    "SUB": 2,
    "MUL": 3,
    "DIV": 4,
    "REM": 5,
    "CMP": 6,
    "AND": 7,
    "OR": 8,
    "XOR": 9,
    "XNOR": 10,
    "SHL": 11,
    "SHR": 12,
    "EXT": 13,
    "CS_N": 14,
    "CS_Z": 15,
    "CS_P": 16,
    "CS_EQ": 17,
    "CS_NE": 18,
    "SET_OW": 19,
    "SET_ZW": 20,
    "OR_W": 21,
    "ANDN_W": 22,
    "AIP_SI": 24,
}
WIDTH_CODES = {8: 0, 16: 1, 32: 2, 64: 3}
MASK64 = (1 << 64) - 1


@dataclass(frozen=True)
class Vector:
    name: str
    operation: int
    width: int
    signed: bool
    operand_a: int
    operand_b: int
    operand_c: int
    operand_d: int
    aux: int
    dual: bool
    expected_lo: int
    expected_hi: int
    expected_commit: bool


def width_mask(width: int) -> int:
    return (1 << width) - 1


def to_signed(value: int, width: int) -> int:
    value &= width_mask(width)
    sign = 1 << (width - 1)
    return value - (1 << width) if value & sign else value


def extend_value(value: int, width: int, signed: bool) -> int:
    value &= width_mask(width)
    if signed and value & (1 << (width - 1)):
        return value | (MASK64 ^ width_mask(width))
    return value & MASK64


def alu_result(
    operation: int,
    width: int,
    signed: bool,
    a: int,
    b: int,
    c: int,
    d: int,
    aux: int,
    dual: bool,
) -> tuple[int, int, bool]:
    mask = width_mask(width)
    aw = a & mask
    bw = b & mask

    if operation == OP["ADD"]:
        if width == 64 and dual:
            if signed:
                full = to_signed(aw, 64) + to_signed(bw, 64)
                return full & MASK64, (full >> 64) & MASK64, True
            full = aw + bw
            return full & MASK64, (full >> 64) & MASK64, True
        return extend_value(aw + bw, width, signed), 0, True

    if operation == OP["SUB"]:
        if width == 64 and dual:
            if signed:
                full = to_signed(aw, 64) - to_signed(bw, 64)
                return full & MASK64, (full >> 64) & MASK64, True
            return (aw - bw) & MASK64, int(aw < bw), True
        return extend_value(aw - bw, width, signed), 0, True

    if operation == OP["MUL"]:
        if width == 64 and dual:
            if signed:
                full = to_signed(aw, 64) * to_signed(bw, 64)
            else:
                full = aw * bw
            return full & MASK64, (full >> 64) & MASK64, True
        product = aw * bw
        if signed:
            # Narrow signed multiplication keeps the low width bits.
            product = to_signed(product, width)
        return extend_value(product, width, signed), 0, True

    if operation in {OP["DIV"], OP["REM"]}:
        if bw == 0:
            if operation == OP["DIV"]:
                return extend_value(mask, width, signed), 0, True
            return extend_value(aw, width, signed), 0, True

        if signed:
            sa = to_signed(aw, width)
            sb = to_signed(bw, width)
            minimum = -(1 << (width - 1))
            if sa == minimum and sb == -1:
                if operation == OP["DIV"]:
                    return extend_value(minimum, width, True), 0, True
                return 0, 0, True
            quotient = abs(sa) // abs(sb)
            if (sa < 0) != (sb < 0):
                quotient = -quotient
            remainder = sa - quotient * sb
            value = quotient if operation == OP["DIV"] else remainder
            return extend_value(value, width, True), 0, True

        value = aw // bw if operation == OP["DIV"] else aw % bw
        return extend_value(value, width, False), 0, True

    if operation == OP["CMP"]:
        left = to_signed(aw, width) if signed else aw
        right = to_signed(bw, width) if signed else bw
        if left < right:
            raw = MASK64
        elif left == right:
            raw = 0
        else:
            raw = 1
        return raw, 0, True

    if operation == OP["AND"]:
        return (a & b) & MASK64, 0, True
    if operation == OP["OR"]:
        return (a | b) & MASK64, 0, True
    if operation == OP["XOR"]:
        return (a ^ b) & MASK64, 0, True
    if operation == OP["XNOR"]:
        return (~(a ^ b)) & MASK64, 0, True

    if operation == OP["SHL"]:
        shifted = (aw << aux) & mask
        return extend_value(shifted, width, signed), 0, True

    if operation == OP["SHR"]:
        if signed:
            shifted = to_signed(aw, width) >> aux
        else:
            shifted = aw >> aux
        return extend_value(shifted, width, signed), 0, True

    if operation == OP["EXT"]:
        low_mask = (1 << (aux + 1)) - 1
        low = a & low_mask
        if signed and ((a >> aux) & 1):
            low |= MASK64 ^ low_mask
        return low & MASK64, 0, True

    if operation == OP["CS_N"]:
        return (c if to_signed(a, 64) < 0 else d) & MASK64, 0, True
    if operation == OP["CS_Z"]:
        return (c if a == 0 else d) & MASK64, 0, True
    if operation == OP["CS_P"]:
        return (c if to_signed(a, 64) > 0 else d) & MASK64, 0, True
    if operation == OP["CS_EQ"]:
        return d & MASK64, 0, a == b
    if operation == OP["CS_NE"]:
        return d & MASK64, 0, a != b

    if operation in {OP["SET_OW"], OP["SET_ZW"], OP["OR_W"], OP["ANDN_W"]}:
        shift = aux * 16
        lane_mask = 0xFFFF << shift
        replacement = (b & 0xFFFF) << shift
        if operation == OP["SET_OW"]:
            result = (MASK64 ^ lane_mask) | replacement
        elif operation == OP["SET_ZW"]:
            result = replacement
        elif operation == OP["OR_W"]:
            result = a | replacement
        else:
            result = a & ~replacement
        return result & MASK64, 0, True

    if operation == OP["AIP_SI"]:
        return (a + (b << 12)) & MASK64, 0, True

    raise AssertionError(f"unsupported operation {operation}")


def make_vector(
    name: str,
    operation: int,
    width: int,
    signed: bool,
    a: int,
    b: int = 0,
    c: int = 0,
    d: int = 0,
    aux: int = 0,
    dual: bool = False,
) -> Vector:
    lo, hi, commit = alu_result(
        operation,
        width,
        signed,
        a,
        b,
        c,
        d,
        aux,
        dual,
    )
    return Vector(
        name=name,
        operation=operation,
        width=width,
        signed=signed,
        operand_a=a & MASK64,
        operand_b=b & MASK64,
        operand_c=c & MASK64,
        operand_d=d & MASK64,
        aux=aux,
        dual=dual,
        expected_lo=lo,
        expected_hi=hi,
        expected_commit=commit,
    )


def generate_vectors() -> list[Vector]:
    vectors: list[Vector] = []

    for width in (8, 16, 32, 64):
        mask = width_mask(width)
        for signed in (False, True):
            suffix = "s" if signed else "u"
            vectors.extend(
                [
                    make_vector(
                        f"add-{width}-{suffix}-zero",
                        OP["ADD"],
                        width,
                        signed,
                        0,
                        0,
                    ),
                    make_vector(
                        f"add-{width}-{suffix}-carry",
                        OP["ADD"],
                        width,
                        signed,
                        mask,
                        1,
                    ),
                    make_vector(
                        f"sub-{width}-{suffix}-borrow",
                        OP["SUB"],
                        width,
                        signed,
                        0,
                        1,
                    ),
                    make_vector(
                        f"mul-{width}-{suffix}",
                        OP["MUL"],
                        width,
                        signed,
                        7,
                        9,
                    ),
                    make_vector(
                        f"div-{width}-{suffix}-normal",
                        OP["DIV"],
                        width,
                        signed,
                        100,
                        7,
                    ),
                    make_vector(
                        f"rem-{width}-{suffix}-normal",
                        OP["REM"],
                        width,
                        signed,
                        100,
                        7,
                    ),
                    make_vector(
                        f"div-{width}-{suffix}-zero",
                        OP["DIV"],
                        width,
                        signed,
                        100,
                        0,
                    ),
                    make_vector(
                        f"rem-{width}-{suffix}-zero",
                        OP["REM"],
                        width,
                        signed,
                        100,
                        0,
                    ),
                    make_vector(
                        f"cmp-{width}-{suffix}-less",
                        OP["CMP"],
                        width,
                        signed,
                        10,
                        20,
                    ),
                    make_vector(
                        f"cmp-{width}-{suffix}-equal",
                        OP["CMP"],
                        width,
                        signed,
                        10,
                        10,
                    ),
                    make_vector(
                        f"cmp-{width}-{suffix}-greater",
                        OP["CMP"],
                        width,
                        signed,
                        20,
                        10,
                    ),
                    make_vector(
                        f"shl-{width}-{suffix}",
                        OP["SHL"],
                        width,
                        signed,
                        1,
                        aux=width - 1,
                    ),
                    make_vector(
                        f"shr-{width}-{suffix}",
                        OP["SHR"],
                        width,
                        signed,
                        mask,
                        aux=width - 1,
                    ),
                ]
            )

    vectors.extend(
        [
            make_vector(
                "add-uo-dual-carry",
                OP["ADD"],
                64,
                False,
                MASK64,
                1,
                dual=True,
            ),
            make_vector(
                "add-so-dual-overflow",
                OP["ADD"],
                64,
                True,
                1 << 63,
                1 << 63,
                dual=True,
            ),
            make_vector(
                "sub-uo-dual-borrow",
                OP["SUB"],
                64,
                False,
                0,
                1,
                dual=True,
            ),
            make_vector(
                "mul-uo-dual",
                OP["MUL"],
                64,
                False,
                1 << 63,
                1 << 63,
                dual=True,
            ),
            make_vector(
                "mul-so-dual",
                OP["MUL"],
                64,
                True,
                to_signed(0xFFFFFFFFFFFFFFFE, 64),
                3,
                dual=True,
            ),
            make_vector(
                "and-o",
                OP["AND"],
                64,
                False,
                0xAAAAAAAAAAAAAAAA,
                0x5555555555555555,
            ),
            make_vector(
                "or-o",
                OP["OR"],
                64,
                False,
                0xAAAAAAAAAAAAAAAA,
                0x5555555555555555,
            ),
            make_vector(
                "xor-o",
                OP["XOR"],
                64,
                False,
                0xAAAAAAAAAAAAAAAA,
                0x5555555555555555,
            ),
            make_vector(
                "xnor-o",
                OP["XNOR"],
                64,
                False,
                0xAAAAAAAAAAAAAAAA,
                0x5555555555555555,
            ),
            make_vector(
                "ext-uo-31",
                OP["EXT"],
                64,
                False,
                0x80000000,
                aux=31,
            ),
            make_vector(
                "ext-so-31",
                OP["EXT"],
                64,
                True,
                0x80000000,
                aux=31,
            ),
            make_vector(
                "ext-uo-63",
                OP["EXT"],
                64,
                False,
                0x8000000000000000,
                aux=63,
            ),
            make_vector(
                "cs-n-true",
                OP["CS_N"],
                64,
                True,
                MASK64,
                c=11,
                d=22,
            ),
            make_vector(
                "cs-z-true",
                OP["CS_Z"],
                64,
                True,
                0,
                c=11,
                d=22,
            ),
            make_vector(
                "cs-p-true",
                OP["CS_P"],
                64,
                True,
                1,
                c=11,
                d=22,
            ),
            make_vector(
                "cs-eq-true",
                OP["CS_EQ"],
                64,
                True,
                5,
                5,
                d=33,
            ),
            make_vector(
                "cs-ne-false",
                OP["CS_NE"],
                64,
                True,
                5,
                5,
                d=33,
            ),
            make_vector(
                "set-ow",
                OP["SET_OW"],
                16,
                False,
                0,
                0x1234,
                aux=1,
            ),
            make_vector(
                "set-zw",
                OP["SET_ZW"],
                16,
                False,
                0,
                0x1234,
                aux=2,
            ),
            make_vector(
                "or-w",
                OP["OR_W"],
                16,
                False,
                0x00010000,
                0x8000,
                aux=1,
            ),
            make_vector(
                "andn-w",
                OP["ANDN_W"],
                16,
                False,
                MASK64,
                0x00FF,
                aux=3,
            ),
            make_vector(
                "aip-si-positive",
                OP["AIP_SI"],
                64,
                True,
                0xFC0000000000,
                1,
            ),
            make_vector(
                "aip-si-negative",
                OP["AIP_SI"],
                64,
                True,
                0xFC0000000000,
                MASK64,
            ),
            make_vector(
                "aip-si-max-page",
                OP["AIP_SI"],
                64,
                True,
                0,
                0x1FFFF,
            ),
        ]
    )
    return vectors


def vector_payload(vector: Vector) -> dict:
    return {
        "name": vector.name,
        "operation": vector.operation,
        "width": vector.width,
        "signed": vector.signed,
        "operand_a": f"0x{vector.operand_a:016x}",
        "operand_b": f"0x{vector.operand_b:016x}",
        "operand_c": f"0x{vector.operand_c:016x}",
        "operand_d": f"0x{vector.operand_d:016x}",
        "aux": vector.aux,
        "dual": vector.dual,
        "expected_lo": f"0x{vector.expected_lo:016x}",
        "expected_hi": f"0x{vector.expected_hi:016x}",
        "expected_commit": vector.expected_commit,
        "expected_valid": True,
    }


def emit_yaml(path: Path, vectors: list[Vector]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            [vector_payload(vector) for vector in vectors],
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def emit_scala(path: Path, vectors: list[Vector]) -> None:
    lines = [
        "package dadao",
        "",
        "// Generated by tools/rtl/check_dadao_alu_oracle.py.",
        "private[dadao] final case class DADAOALUOracleVector(",
        "    name: String,",
        "    operation: Int,",
        "    widthCode: Int,",
        "    signed: Boolean,",
        "    operandA: BigInt,",
        "    operandB: BigInt,",
        "    operandC: BigInt,",
        "    operandD: BigInt,",
        "    aux: Int,",
        "    dual: Boolean,",
        "    expectedLo: BigInt,",
        "    expectedHi: BigInt,",
        "    expectedCommit: Boolean",
        ")",
        "",
        "private[dadao] object DADAOALUOracleTable {",
        "  val vectors: Seq[DADAOALUOracleVector] = Seq(",
    ]
    for vector in vectors:
        lines.append(
            "    DADAOALUOracleVector("
            f'"{vector.name}", {vector.operation}, '
            f"{WIDTH_CODES[vector.width]}, "
            f"{str(vector.signed).lower()}, "
            f'BigInt("{vector.operand_a:016x}", 16), '
            f'BigInt("{vector.operand_b:016x}", 16), '
            f'BigInt("{vector.operand_c:016x}", 16), '
            f'BigInt("{vector.operand_d:016x}", 16), '
            f"{vector.aux}, {str(vector.dual).lower()}, "
            f'BigInt("{vector.expected_lo:016x}", 16), '
            f'BigInt("{vector.expected_hi:016x}", 16), '
            f"{str(vector.expected_commit).lower()}),"
        )
    lines.extend(
        [
            "  )",
            "}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RTL-009t independent ALU oracle vectors."
    )
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML)
    parser.add_argument("--scala", type=Path, default=DEFAULT_SCALA)
    parser.add_argument("--force-failure", action="store_true")
    args = parser.parse_args()

    vectors = generate_vectors()
    names = [vector.name for vector in vectors]
    if len(names) != len(set(names)):
        raise AssertionError("duplicate ALU oracle vector names")
    if len(vectors) < 100:
        raise AssertionError("ALU oracle vector set is unexpectedly small")

    if args.force_failure:
        raise AssertionError("forced ALU oracle failure")

    emit_yaml(args.yaml, vectors)
    emit_scala(args.scala, vectors)
    print(f"vectors={len(vectors)}")
    print(f"operations={len(set(v.operation for v in vectors))}")
    print(f"widths={sorted(set(v.width for v in vectors))}")
    print(f"yaml={args.yaml}")
    print(f"scala={args.scala}")

    print("ALU_ORACLE CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
