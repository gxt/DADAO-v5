#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS = ROOT / "contracts/opcodes.yaml"
DEFAULT_OUT = (
    ROOT / "rtl/dadao/src/main/scala/dadao/DADAODecoderTable.scala"
)

SCOPE_CODES = {
    "m1": 0,
    "fp": 1,
    "excluded": 2,
    "m3": 3,
    # RTL currently implements only M1. M8/M9 are recognized encodings but
    # share the unsupported-scope code with M3.
    "m8": 3,
    "m9": 3,
}

STATIC_CHECK_CODES = {
    "dest-not-zero": 1,
    "dual-destination-distinct": 2,
    "ret-rd0-immediate-zero": 3,
    "count-nonzero": 4,
    "range-limit-64": 5,
    "range-overlap": 6,
    "count-at-most": 7,
    "count-equals": 8,
    "fixed-bits-zero": 9,
    "cfx-reserved": 10,
}


def parse_int(value: object, field: str, record_id: str) -> int:
    if not isinstance(value, str):
        raise ValueError(f"{record_id}: {field} is not a string")
    return int(value, 0)


def parse_field_offset(record: dict, field_name: str) -> int:
    record_id = str(record["id"])
    for field in record.get("fields", []):
        if str(field["name"]) != field_name:
            continue
        match = re.fullmatch(r"\[(\d+):(\d+)\]", str(field["bits"]))
        if match is None:
            raise ValueError(
                f"{record_id}: unsupported bits for {field_name}: "
                f"{field['bits']}"
            )
        high = int(match.group(1))
        low = int(match.group(2))
        if high - low + 1 != 6:
            raise ValueError(
                f"{record_id}: {field_name} is not a 6-bit field"
            )
        return low
    raise ValueError(f"{record_id}: field {field_name} not found")


def static_checks_for(record: dict) -> list[tuple[int, int, int, int, int]]:
    if str(record.get("scope")) != "m1":
        return []

    record_id = str(record["id"])
    checks: set[tuple[int, int, int, int, int]] = set()

    def add(
        kind_name: str,
        field_a: int = 0,
        field_b: int = 0,
        field_c: int = 0,
        limit: int = 0,
    ) -> None:
        checks.add(
            (
                STATIC_CHECK_CODES[kind_name],
                field_a,
                field_b,
                field_c,
                limit,
            )
        )

    for expression_value in record.get("legality", []):
        expression = str(expression_value)

        match = re.fullmatch(
            r"(rdha|rdhb|rdhc|rbha|rbhb|rbhc|rfha|rfhb|rfhc)"
            r" != (rd0|rb0|rf0)",
            expression,
        )
        if match is not None:
            add(
                "dest-not-zero",
                field_a=parse_field_offset(record, match.group(1)),
            )
            continue

        if expression == "!(rdha == rd0 && imms18 != 0)":
            add(
                "ret-rd0-immediate-zero",
                field_a=parse_field_offset(record, "rdha"),
            )
            continue

        match = re.fullmatch(
            r"!\((\w+) == (\w+) && (\w+) == (\w+)\)",
            expression,
        )
        if match is not None:
            if (
                match.group(2) != match.group(4)
                or match.group(1) == match.group(3)
            ):
                raise ValueError(
                    f"{record_id}: unsupported dual-zero expression: "
                    f"{expression}"
                )
            add(
                "dual-destination-distinct",
                field_a=parse_field_offset(record, match.group(1)),
                field_b=parse_field_offset(record, match.group(3)),
            )
            continue

        match = re.fullmatch(
            r"!\((\w+) == (\w+) && (\w+) != (\w+)\)",
            expression,
        )
        if match is not None:
            if (
                match.group(1) != match.group(3)
                or match.group(4) not in {"rd0", "rb0", "rf0"}
            ):
                raise ValueError(
                    f"{record_id}: unsupported dual-same expression: "
                    f"{expression}"
                )
            add(
                "dual-destination-distinct",
                field_a=parse_field_offset(record, match.group(1)),
                field_b=parse_field_offset(record, match.group(2)),
            )
            continue

        if expression == "immu6 != 0":
            add(
                "count-nonzero",
                field_a=parse_field_offset(record, "immu6"),
            )
            continue

        if expression == (
            "cfxha <= 5 || (cfxha >= 15 && cfxha <= 18) || cfxha >= 62"
        ):
            add(
                "cfx-reserved",
                field_a=parse_field_offset(record, "cfxha"),
            )
            continue

        match = re.fullmatch(r"(\w+) \+ immu6 <= 64", expression)
        if match is not None:
            add(
                "range-limit-64",
                field_a=parse_field_offset(record, match.group(1)),
                field_b=parse_field_offset(record, "immu6"),
            )
            continue

        match = re.fullmatch(
            r"no_overlap\((\w+), (\w+), immu6\)",
            expression,
        )
        if match is not None:
            add(
                "range-overlap",
                field_a=parse_field_offset(record, match.group(1)),
                field_b=parse_field_offset(record, match.group(2)),
                field_c=parse_field_offset(record, "immu6"),
            )
            continue

        match = re.fullmatch(r"immu6 <= (\d+)", expression)
        if match is not None:
            add(
                "count-at-most",
                field_a=parse_field_offset(record, "immu6"),
                limit=int(match.group(1)),
            )
            continue

        match = re.fullmatch(r"immu6 == (\d+)", expression)
        if match is not None:
            add(
                "count-equals",
                field_a=parse_field_offset(record, "immu6"),
                limit=int(match.group(1)),
            )
            continue

        match = re.fullmatch(
            r"(?:immu18|imms18)\[(\d+):(\d+)\] == 0",
            expression,
        )
        if match is not None:
            high = int(match.group(1))
            low = int(match.group(2))
            width = high - low + 1
            add(
                "fixed-bits-zero",
                limit=((1 << width) - 1) << low,
            )
            continue

        if re.fullmatch(r"aligned\(\d+\)", expression):
            # Alignment depends on the runtime effective address.
            continue

        raise ValueError(
            f"{record_id}: unsupported static legality expression: "
            f"{expression}"
        )

    return sorted(checks)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the DADAO decoder lookup table."
    )
    parser.add_argument("--ops", type=Path, default=DEFAULT_OPS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    records = yaml.safe_load(args.ops.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("opcodes.yaml must contain a top-level list")

    formats = sorted(
        {
            str(record["format"])
            for record in records
            if record.get("format") is not None
        }
    )
    format_codes = {name: index for index, name in enumerate(formats)}
    if len(format_codes) >= 16:
        raise SystemExit("format code space requires more than 4 bits")

    seen_ids: set[str] = set()
    seen_encodings: set[tuple[int, int]] = set()
    entries: list[tuple[int, int, int, int, int]] = []
    ids: list[str] = []
    swym_id: int | None = None
    static_checks: list[tuple[int, int, int, int, int, int]] = []

    for index, record in enumerate(records):
        record_id = str(record["id"])
        if record_id in seen_ids:
            raise SystemExit(f"duplicate id: {record_id}")
        seen_ids.add(record_id)

        mask = parse_int(record["mask"], "mask", record_id)
        value = parse_int(record["value"], "value", record_id)
        if value & ~mask:
            raise SystemExit(f"{record_id}: value has bits outside mask")
        encoding = (mask, value)
        if encoding in seen_encodings:
            raise SystemExit(f"{record_id}: duplicate mask/value encoding")
        seen_encodings.add(encoding)

        scope_name = str(record["scope"])
        if scope_name not in SCOPE_CODES:
            raise SystemExit(f"{record_id}: unsupported scope {scope_name}")
        format_name = str(record["format"])
        if format_name not in format_codes:
            raise SystemExit(f"{record_id}: unsupported format {format_name}")

        if str(record["mnemonic"]) == "swym":
            swym_id = index
        for kind, field_a, field_b, field_c, limit in static_checks_for(
            record
        ):
            static_checks.append(
                (index, kind, field_a, field_b, field_c, limit)
            )
        entries.append(
            (
                value,
                mask,
                index,
                format_codes[format_name],
                SCOPE_CODES[scope_name],
            )
        )
        ids.append(record_id)

    if swym_id is None:
        raise SystemExit("opcodes.yaml does not define swym")
    if len(entries) > 0x1FF:
        raise SystemExit("decoder id requires more than 9 bits")

    lines = [
        "package dadao",
        "",
        "// Generated by tools/rtl/generate_dadao_decoder_table.py.",
        "// Source: contracts/opcodes.yaml.",
        "private[dadao] final case class DADAODecoderTableEntry(",
        "    value: BigInt,",
        "    mask: BigInt,",
        "    id: Int,",
        "    format: Int,",
        "    scope: Int",
        ")",
        "",
        "private[dadao] final case class "
        "DADAODecoderStaticCheckEntry(",
        "    id: Int,",
        "    kind: Int,",
        "    fieldA: Int,",
        "    fieldB: Int,",
        "    fieldC: Int,",
        "    limit: Int",
        ")",
        "",
        "private[dadao] object DADAODecoderTable {",
        f"  val swymId: Int = {swym_id}",
        "  val entries: Seq[DADAODecoderTableEntry] = Seq(",
    ]
    for value, mask, ident, format_code, scope_code in entries:
        lines.append(
            "    DADAODecoderTableEntry("
            f"BigInt(\"{value:08x}\", 16), "
            f"BigInt(\"{mask:08x}\", 16), "
            f"{ident}, {format_code}, {scope_code}),"
        )
    lines.extend(
        [
            "  )",
            "  val staticChecks: Seq[DADAODecoderStaticCheckEntry] = Seq(",
            *[
                "    DADAODecoderStaticCheckEntry("
                f"{ident}, {kind}, {field_a}, {field_b}, "
                f"{field_c}, {limit}),"
                for ident, kind, field_a, field_b, field_c, limit
                in static_checks
            ],
            "  )",
            "  val ids: Seq[String] = Seq(",
            *[f'    "{record_id}",' for record_id in ids],
            "  )",
            "  val formatNames: Seq[String] = Seq(",
            *[f'    "{name}",' for name in formats],
            "  )",
            "}",
            "",
        ]
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"generated {args.output}: {len(entries)} entries, "
        f"{len(formats)} formats, {len(static_checks)} static checks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
