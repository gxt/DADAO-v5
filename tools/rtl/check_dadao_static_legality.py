#!/usr/bin/env python3
"""Independent checker for generated DADAO static-legality metadata."""

from __future__ import annotations

import argparse
import collections
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS = ROOT / "contracts/opcodes.yaml"
DEFAULT_SCALA = (
    ROOT / "rtl/dadao/src/main/scala/dadao/DADAODecoderTable.scala"
)

KIND_CODES = {
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


def field_offset(record: dict, name: str) -> int:
    for field in record.get("fields", []):
        if str(field["name"]) != name:
            continue
        match = re.fullmatch(r"\[(\d+):(\d+)\]", str(field["bits"]))
        if match is None:
            raise AssertionError(
                f"{record['id']}: malformed field {name}={field['bits']}"
            )
        high, low = map(int, match.groups())
        assert high - low + 1 == 6, (
            f"{record['id']}: {name} is not a 6-bit field"
        )
        return low
    raise AssertionError(f"{record['id']}: field {name} not found")


def expected_checks(record: dict) -> set[tuple[int, int, int, int, int]]:
    checks: set[tuple[int, int, int, int, int]] = set()

    def add(
        kind: str,
        a: int = 0,
        b: int = 0,
        c: int = 0,
        limit: int = 0,
    ) -> None:
        checks.add((KIND_CODES[kind], a, b, c, limit))

    for raw_expression in record.get("legality", []):
        expression = str(raw_expression)

        match = re.fullmatch(
            r"(rdha|rdhb|rdhc|rbha|rbhb|rbhc|rfha|rfhb|rfhc)"
            r" != (rd0|rb0|rf0)",
            expression,
        )
        if match:
            add(
                "dest-not-zero",
                a=field_offset(record, match.group(1)),
            )
            continue

        if expression == "!(rdha == rd0 && imms18 != 0)":
            add(
                "ret-rd0-immediate-zero",
                a=field_offset(record, "rdha"),
            )
            continue

        match = re.fullmatch(
            r"!\((\w+) == (\w+) && (\w+) == (\w+)\)",
            expression,
        )
        if match:
            assert match.group(2) == match.group(4)
            assert match.group(1) != match.group(3)
            add(
                "dual-destination-distinct",
                a=field_offset(record, match.group(1)),
                b=field_offset(record, match.group(3)),
            )
            continue

        match = re.fullmatch(
            r"!\((\w+) == (\w+) && (\w+) != (\w+)\)",
            expression,
        )
        if match:
            assert match.group(1) == match.group(3)
            assert match.group(4) in {"rd0", "rb0", "rf0"}
            add(
                "dual-destination-distinct",
                a=field_offset(record, match.group(1)),
                b=field_offset(record, match.group(2)),
            )
            continue

        if expression == "immu6 != 0":
            add(
                "count-nonzero",
                a=field_offset(record, "immu6"),
            )
            continue

        if expression == (
            "cfxha <= 5 || (cfxha >= 15 && cfxha <= 18) || cfxha >= 62"
        ):
            add(
                "cfx-reserved",
                a=field_offset(record, "cfxha"),
            )
            continue

        match = re.fullmatch(r"(\w+) \+ immu6 <= 64", expression)
        if match:
            add(
                "range-limit-64",
                a=field_offset(record, match.group(1)),
                b=field_offset(record, "immu6"),
            )
            continue

        match = re.fullmatch(
            r"no_overlap\((\w+), (\w+), immu6\)",
            expression,
        )
        if match:
            add(
                "range-overlap",
                a=field_offset(record, match.group(1)),
                b=field_offset(record, match.group(2)),
                c=field_offset(record, "immu6"),
            )
            continue

        match = re.fullmatch(r"immu6 <= (\d+)", expression)
        if match:
            add(
                "count-at-most",
                a=field_offset(record, "immu6"),
                limit=int(match.group(1)),
            )
            continue

        match = re.fullmatch(r"immu6 == (\d+)", expression)
        if match:
            add(
                "count-equals",
                a=field_offset(record, "immu6"),
                limit=int(match.group(1)),
            )
            continue

        match = re.fullmatch(
            r"(?:immu18|imms18)\[(\d+):(\d+)\] == 0",
            expression,
        )
        if match:
            high, low = map(int, match.groups())
            add(
                "fixed-bits-zero",
                limit=((1 << (high - low + 1)) - 1) << low,
            )
            continue

        if re.fullmatch(r"aligned\(\d+\)", expression):
            continue

        raise AssertionError(
            f"{record['id']}: unclassified legality expression {expression}"
        )

    return checks


def parse_generated(
    scala_path: Path,
) -> list[tuple[int, int, int, int, int, int]]:
    text = scala_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"DADAODecoderStaticCheckEntry\("
        r"(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)"
    )
    return [tuple(map(int, match.groups())) for match in pattern.finditer(text)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify DADAO generated static-legality metadata."
    )
    parser.add_argument("--ops", type=Path, default=DEFAULT_OPS)
    parser.add_argument("--scala", type=Path, default=DEFAULT_SCALA)
    parser.add_argument("--force-failure", action="store_true")
    args = parser.parse_args()

    records = yaml.safe_load(args.ops.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise AssertionError("opcodes.yaml must contain a list")

    scope_counts = collections.Counter(
        str(record["scope"]) for record in records
    )
    assert len(records) == 264
    assert scope_counts == {
        "m1": 156,
        "fp": 66,
        "m3": 1,
        "m8": 7,
        "m9": 34,
    }

    expected: set[tuple[int, int, int, int, int, int]] = set()
    all_expressions: set[str] = set()
    dynamic_expressions: list[str] = []
    for index, record in enumerate(records):
        legality = [str(value) for value in record.get("legality", [])]
        all_expressions.update(legality)
        dynamic_expressions.extend(
            expression for expression in legality if expression.startswith("aligned(")
        )
        if str(record["scope"]) != "m1":
            continue
        for check in expected_checks(record):
            expected.add((index, *check))

    generated_rows = parse_generated(args.scala)
    generated = set(generated_rows)
    assert len(generated_rows) == len(generated), "duplicate generated checks"
    assert generated == expected, (
        "generated static checks differ from opcodes.yaml: "
        f"missing={len(expected - generated)}, "
        f"extra={len(generated - expected)}"
    )

    kind_counts = collections.Counter(row[1] for row in generated_rows)
    print(
        "opcodes=264 m1=156 fp=66 excluded=0 "
        "m3=1 m8=7 m9=34"
    )
    print(
        f"legality_unique_expressions={len(all_expressions)} "
        f"dynamic_alignment_occurrences={len(dynamic_expressions)}"
    )
    print(f"static_checks={len(generated_rows)}")
    print(
        "kind_counts="
        + ",".join(
            f"{kind}:{kind_counts[kind]}"
            for kind in sorted(kind_counts)
        )
    )

    if args.force_failure:
        raise AssertionError("forced static-legality checker failure")

    print("STATIC_LEGALITY CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
