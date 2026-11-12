#!/usr/bin/env python3
"""Check QFC/MISC cell coverage and emit reserved-cell decoder vectors."""

from __future__ import annotations

import argparse
import collections
from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS = ROOT / "contracts/opcodes.yaml"
DEFAULT_OUTPUT = (
    ROOT
    / "rtl/dadao/src/test/scala/dadao/"
    / "DADAOReservedCoverageTable.scala"
)

OP_MASK = 0xFF000000
SUBTABLE_MASK = 0xFFFC0000
SUBTABLE_CELL_SHIFT = 18
SUBTABLE_CELL_COUNT = 64
MAIN_CELL_COUNT = 256

MISC_TABLES = {
    0x40: "OPC-octa",
    0x41: "OPC-tetra",
    0x42: "OPC-wyde",
    0x43: "OPC-byte",
    0x44: "OPC-RF",
    0x47: "OPC-MISC",
}


@dataclass(frozen=True)
class ReservedCell:
    domain: str
    op: int
    cell: int
    word: int


def parse_int(value: object, field: str, record_id: str) -> int:
    if not isinstance(value, str):
        raise AssertionError(f"{record_id}: {field} is not a string")
    return int(value, 0)


def representative_word(op: int, cell: int | None) -> int:
    if cell is None:
        return (op << 24) | 0x00040001
    return (op << 24) | (cell << SUBTABLE_CELL_SHIFT) | 0x00000001


def matches(word: int, record: dict) -> bool:
    record_id = str(record["id"])
    mask = parse_int(record["mask"], "mask", record_id)
    value = parse_int(record["value"], "value", record_id)
    return (word & mask) == value


def build_coverage(records: list[dict]) -> tuple[
    list[ReservedCell],
    dict[str, int],
]:
    by_op: dict[int, list[dict]] = collections.defaultdict(list)
    for record in records:
        record_id = str(record["id"])
        op_value = record.get("opc", record.get("op"))
        op = parse_int(op_value, "opc", record_id)
        by_op[op].append(record)

    reserved: list[ReservedCell] = []
    main_defined = 0
    main_reserved = 0
    subcell_defined = 0
    subcell_reserved = 0

    for op in range(MAIN_CELL_COUNT):
        op_records = by_op.get(op, [])
        if op in MISC_TABLES:
            if not op_records:
                raise AssertionError(
                    f"missing MISC dispatcher definitions for op=0x{op:02x}"
                )
            for record in op_records:
                record_id = str(record["id"])
                mask = parse_int(record["mask"], "mask", record_id)
                if mask != SUBTABLE_MASK:
                    raise AssertionError(
                        f"{record_id}: MISC mask must be 0x{SUBTABLE_MASK:08x}"
                    )
            main_defined += 1
            continue

        if not op_records:
            main_reserved += 1
            reserved.append(
                ReservedCell(
                    domain="main",
                    op=op,
                    cell=-1,
                    word=representative_word(op, None),
                )
            )
            continue

        if len(op_records) != 1:
            raise AssertionError(
                f"op=0x{op:02x} has {len(op_records)} direct definitions"
            )
        record = op_records[0]
        record_id = str(record["id"])
        mask = parse_int(record["mask"], "mask", record_id)
        if mask != OP_MASK:
            raise AssertionError(
                f"{record_id}: direct op mask must be 0x{OP_MASK:08x}"
            )
        main_defined += 1

    for op in MISC_TABLES:
        op_records = by_op.get(op, [])
        by_cell: dict[int, list[dict]] = collections.defaultdict(list)
        for record in op_records:
            record_id = str(record["id"])
            value = parse_int(record["value"], "value", record_id)
            cell = (value >> SUBTABLE_CELL_SHIFT) & 0x3F
            by_cell[cell].append(record)

        for cell in range(SUBTABLE_CELL_COUNT):
            cell_records = by_cell.get(cell, [])
            if not cell_records:
                subcell_reserved += 1
                reserved.append(
                    ReservedCell(
                        domain=MISC_TABLES[op],
                        op=op,
                        cell=cell,
                        word=representative_word(op, cell),
                    )
                )
                continue
            if len(cell_records) != 1:
                names = ",".join(str(record["id"]) for record in cell_records)
                raise AssertionError(
                    f"{MISC_TABLES[op]} cell {cell:02x} duplicated: {names}"
                )
            subcell_defined += 1

    for cell in reserved:
        matched = [
            str(record["id"]) for record in records if matches(cell.word, record)
        ]
        if matched:
            raise AssertionError(
                f"reserved representative 0x{cell.word:08x} matches "
                f"{','.join(matched)}"
            )

    counts = {
        "main_defined": main_defined,
        "main_reserved": main_reserved,
        "subcell_defined": subcell_defined,
        "subcell_reserved": subcell_reserved,
        "reserved_total": len(reserved),
    }
    if counts["main_defined"] + counts["main_reserved"] != MAIN_CELL_COUNT:
        raise AssertionError(
            f"main cell count mismatch: {counts}"
        )
    if (
        counts["subcell_defined"] + counts["subcell_reserved"]
        != len(MISC_TABLES) * SUBTABLE_CELL_COUNT
    ):
        raise AssertionError(
            f"subtable cell count mismatch: {counts}"
        )
    return reserved, counts


def emit_scala(path: Path, reserved: list[ReservedCell]) -> None:
    lines = [
        "package dadao",
        "",
        "// Generated by tools/rtl/check_dadao_cell_coverage.py.",
        "// Source domain: QFC main table and six OPC subtables.",
        "private[dadao] final case class DADAOReservedCoverageCell(",
        "    domain: String,",
        "    op: Int,",
        "    cell: Int,",
        "    word: BigInt",
        ")",
        "",
        "private[dadao] object DADAOReservedCoverageTable {",
        "  val cells: Seq[DADAOReservedCoverageCell] = Seq(",
    ]
    for cell in reserved:
        lines.append(
            "    DADAOReservedCoverageCell("
            f'"{cell.domain}", 0x{cell.op:02x}, {cell.cell}, '
            f'BigInt("{cell.word:08x}", 16)),'
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
        description="Verify QFC/MISC reserved-cell coverage."
    )
    parser.add_argument("--ops", type=Path, default=DEFAULT_OPS)
    parser.add_argument("--emit-scala", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force-failure", action="store_true")
    args = parser.parse_args()

    records = yaml.safe_load(args.ops.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise AssertionError("opcodes.yaml must contain a list")

    reserved, counts = build_coverage(records)
    emit_scala(args.emit_scala, reserved)

    print("QFC_MAIN_CELLS=256")
    print(f"MISC_SUBTABLES={len(MISC_TABLES)}")
    print(f"MISC_SUBCELLS={len(MISC_TABLES) * SUBTABLE_CELL_COUNT}")
    for name, value in counts.items():
        print(f"{name.upper()}={value}")
    print(f"emitted={args.emit_scala}")

    if args.force_failure:
        raise AssertionError("forced cell-coverage checker failure")

    print("CELL_COVERAGE CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
