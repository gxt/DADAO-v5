#!/usr/bin/env python3
"""Independent checker for generated RTL-009t execution descriptors."""

from __future__ import annotations

import argparse
import collections
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS = ROOT / "contracts/opcodes.yaml"
DEFAULT_SCALA = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOExecTable.scala"
DEFAULT_VECTORS = ROOT / "tests/rtl/core/RTL-009t-exec-vectors.yaml"

BANK_CODES = {"rd": 0, "rb": 1, "ra": 2, "rf": 3}
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
    "COPY_BLOCK": 23,
    "AIP_SI": 24,
}
WIDTH_CODES = {8: 0, 16: 1, 32: 2, 64: 3}
IMM = {
    "NONE": 0,
    "IMMU6": 1,
    "IMMS12": 2,
    "IMMU12": 3,
    "IMMS18": 4,
    "IMMU16_WYDE": 5,
}
SPECIAL = {"NONE": 0, "SET_WYDE": 1, "COPY_BLOCK": 2}
COPY_MNEMONICS = {
    "rd2rd",
    "rb2rb",
    "rb2rd",
    "rd2rb",
    "ra2rd",
    "rd2ra",
}
SYSTEM_MNEMONICS = {"cfx2rd", "cfx2rc", "escape", "trap"}


def fields_by_role(record: dict, role: str) -> list[dict]:
    return [
        field
        for field in record.get("fields", [])
        if str(field["role"]) == role
    ]


def bits(field: dict, record_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"\[(\d+):(\d+)\]", str(field["bits"]))
    if match is None:
        raise AssertionError(f"{record_id}: bad bits {field['bits']}")
    high, low = map(int, match.groups())
    return low, high - low + 1


def ref_tokens(record: dict, field: dict) -> list[int]:
    record_id = str(record["id"])
    low, width = bits(field, record_id)
    if width != 6:
        raise AssertionError(
            f"{record_id}: register field is not 6 bits: {field['name']}"
        )
    return [BANK_CODES[str(field["bank"])], low, width]


def family(record: dict) -> str:
    mnemonic = str(record["mnemonic"])
    if mnemonic == "swym":
        return "swym"
    if mnemonic.startswith(("ld.", "st.", "ldm.", "stm.")):
        return "memory"
    if mnemonic.startswith("br.") or mnemonic in {
        "jump",
        "call",
        "ret",
    }:
        return "control"
    if mnemonic in SYSTEM_MNEMONICS:
        return "system"
    return "rtl009"


def operation(record: dict) -> int:
    mnemonic = str(record["mnemonic"])
    if mnemonic in COPY_MNEMONICS:
        return OP["COPY_BLOCK"]
    if mnemonic == "set.ow":
        return OP["SET_OW"]
    if mnemonic == "set.zw":
        return OP["SET_ZW"]
    if mnemonic == "or.w":
        return OP["OR_W"]
    if mnemonic == "andn.w":
        return OP["ANDN_W"]
    if mnemonic == "aip.si":
        return OP["AIP_SI"]
    if mnemonic in {
        "cs.n",
        "cs.z",
        "cs.p",
        "cs.eq",
        "cs.ne",
    }:
        return OP[mnemonic.upper().replace(".", "_")]
    base_to_op = {
        "add": "ADD",
        "sub": "SUB",
        "mul": "MUL",
        "div": "DIV",
        "rem": "REM",
        "cmp": "CMP",
        "and": "AND",
        "or": "OR",
        "xor": "XOR",
        "xnor": "XNOR",
        "shl": "SHL",
        "shr": "SHR",
        "ext": "EXT",
    }
    base = mnemonic.split(".")[0]
    if base not in base_to_op:
        raise AssertionError(f"{record['id']}: unknown operation")
    return OP[base_to_op[base]]


def width_signed(record: dict) -> tuple[int, bool]:
    mnemonic = str(record["mnemonic"])
    if mnemonic in COPY_MNEMONICS:
        return 64, False
    if mnemonic in {"set.ow", "set.zw", "or.w", "andn.w"}:
        return 16, False
    if mnemonic in {"add.si", "cmp.si"}:
        return 64, True
    if mnemonic == "cmp.ui":
        return 64, False
    if mnemonic == "aip.si":
        return 64, True
    if mnemonic in {"shl.b", "shl.w", "shl.t", "shl.o"}:
        return {
            "shl.b": 8,
            "shl.w": 16,
            "shl.t": 32,
            "shl.o": 64,
        }[mnemonic], False
    if mnemonic.startswith("cs."):
        return 64, True
    suffix_map = {
        ".ub": (8, False),
        ".sb": (8, True),
        ".uw": (16, False),
        ".sw": (16, True),
        ".ut": (32, False),
        ".st": (32, True),
        ".uo": (64, False),
        ".so": (64, True),
        ".o": (64, False),
    }
    for suffix, result in suffix_map.items():
        if mnemonic.endswith(suffix):
            return result
    raise AssertionError(f"{record['id']}: unknown width/signedness")


def immediate(record: dict) -> tuple[int, int, int, int, int]:
    record_id = str(record["id"])
    imm_fields = fields_by_role(record, "imm")
    wyde_fields = fields_by_role(record, "wyde_pos")
    if not imm_fields:
        return IMM["NONE"], 0, 0, -1, 0
    if len(imm_fields) != 1:
        raise AssertionError(f"{record_id}: multiple immediates")
    field = imm_fields[0]
    low, width = bits(field, record_id)
    mode = {
        "immu6": IMM["IMMU6"],
        "imms12": IMM["IMMS12"],
        "immu12": IMM["IMMU12"],
        "imms18": IMM["IMMS18"],
        "immu16": IMM["IMMU16_WYDE"],
    }[str(field["name"])]
    if mode == IMM["IMMU16_WYDE"]:
        if len(wyde_fields) != 1:
            raise AssertionError(f"{record_id}: missing wyde position")
        wyde_low, wyde_width = bits(wyde_fields[0], record_id)
    else:
        wyde_low, wyde_width = -1, 0
    return mode, low, width, wyde_low, wyde_width


def expected_tokens(record: dict, ident: int) -> list[int]:
    destinations = fields_by_role(record, "dst")
    sources = fields_by_role(record, "src")
    if not destinations or len(destinations) > 2 or len(sources) > 3:
        raise AssertionError(f"{record['id']}: invalid descriptor arity")
    dest_read = str(record["mnemonic"]) in {"add.si", "or.w", "andn.w"}
    if dest_read:
        sources.insert(0, destinations[0])
    if len(sources) > 3:
        raise AssertionError(f"{record['id']}: too many sources")

    width, signed = width_signed(record)
    imm_mode, imm_low, imm_width, wyde_low, wyde_width = immediate(record)
    special = (
        SPECIAL["COPY_BLOCK"]
        if str(record["mnemonic"]) in COPY_MNEMONICS
        else SPECIAL["SET_WYDE"]
        if str(record["mnemonic"]) in {
            "set.ow",
            "set.zw",
            "or.w",
            "andn.w",
        }
        else SPECIAL["NONE"]
    )
    invalid = [-1, 0, 0]
    dst_refs = [ref_tokens(record, field) for field in destinations]
    src_refs = [ref_tokens(record, field) for field in sources]
    dst_refs += [invalid] * (2 - len(dst_refs))
    src_refs += [invalid] * (3 - len(src_refs))

    tokens = [
        ident,
        operation(record),
        WIDTH_CODES[width],
        int(signed),
        int(dest_read),
        len(destinations),
        len(sources),
    ]
    for ref in dst_refs + src_refs:
        tokens.extend(ref)
    tokens.extend(
        [
            imm_mode,
            imm_low,
            imm_width,
            wyde_low,
            wyde_width,
            special,
        ]
    )
    return tokens


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check RTL-009t execution descriptor coverage."
    )
    parser.add_argument("--ops", type=Path, default=DEFAULT_OPS)
    parser.add_argument("--scala", type=Path, default=DEFAULT_SCALA)
    parser.add_argument("--emit-yaml", type=Path)
    parser.add_argument("--force-failure", action="store_true")
    args = parser.parse_args()

    records = yaml.safe_load(args.ops.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise AssertionError("opcodes.yaml must contain a list")

    counts = collections.Counter()
    expected: dict[int, list[int]] = {}
    expected_ids: list[str] = []
    exec_vectors = []
    for ident, record in enumerate(records):
        if str(record["scope"]) != "m1":
            continue
        group = family(record)
        counts[group] += 1
        if group != "rtl009":
            continue
        expected[ident] = expected_tokens(record, ident)
        expected_ids.append(str(record["id"]))
        destinations = fields_by_role(record, "dst")
        sources = fields_by_role(record, "src")
        dest_read = str(record["mnemonic"]) in {"add.si", "or.w", "andn.w"}
        source_count = len(sources) + int(dest_read)
        width, signed = width_signed(record)
        imm_mode, _, _, _, _ = immediate(record)
        special = (
            SPECIAL["COPY_BLOCK"]
            if str(record["mnemonic"]) in COPY_MNEMONICS
            else SPECIAL["SET_WYDE"]
            if str(record["mnemonic"]) in {
                "set.ow",
                "set.zw",
                "or.w",
                "andn.w",
            }
            else SPECIAL["NONE"]
        )
        exec_vectors.append(
            {
                "id": str(record["id"]),
                "instruction_id": ident,
                "operation": operation(record),
                "width": width,
                "signed": signed,
                "dest_read": dest_read,
                "dst_count": len(destinations),
                "src_count": source_count,
                "imm_mode": imm_mode,
                "special": special,
            }
        )

    if dict(counts) != {
        "swym": 1,
        "rtl009": 106,
        "memory": 30,
        "control": 15,
        "system": 4,
    }:
        raise AssertionError(f"bad M1 partition: {dict(counts)}")

    text = args.scala.read_text(encoding="utf-8")
    entry_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("DADAOExecEntry(")
    ]
    if len(entry_lines) != 106:
        raise AssertionError(
            f"generated entry count is {len(entry_lines)}, expected 106"
        )

    generated: dict[int, list[int]] = {}
    for line in entry_lines:
        tokens = re.findall(r"true|false|-?\d+", line)
        numeric = [int(token) if token not in {"true", "false"} else int(token == "true") for token in tokens]
        if len(numeric) != 28:
            raise AssertionError(
                f"descriptor token count {len(numeric)} != 28: {line}"
            )
        ident = numeric[0]
        if ident in generated:
            raise AssertionError(f"duplicate descriptor id {ident}")
        generated[ident] = numeric

    if generated != expected:
        missing = sorted(set(expected) - set(generated))
        extra = sorted(set(generated) - set(expected))
        mismatched = sorted(
            ident
            for ident in set(expected) & set(generated)
            if expected[ident] != generated[ident]
        )
        raise AssertionError(
            f"descriptor mismatch missing={missing[:5]} "
            f"extra={extra[:5]} fields={mismatched[:5]}"
        )

    id_block_match = re.search(
        r"val ids: Seq\[String\] = Seq\((.*?)\n  \)",
        text,
        re.S,
    )
    if id_block_match is None:
        raise AssertionError("generated ids list not found")
    generated_ids = re.findall(
        r'^\s*"([^"]+)",',
        id_block_match.group(1),
        re.M,
    )
    if generated_ids != expected_ids:
        raise AssertionError("generated ids list mismatch")

    if args.emit_yaml is not None:
        args.emit_yaml.parent.mkdir(parents=True, exist_ok=True)
        args.emit_yaml.write_text(
            yaml.safe_dump(exec_vectors, sort_keys=False),
            encoding="utf-8",
        )
        print(f"emitted={args.emit_yaml}")

    print(
        f"M1 partition: swym=1 rtl009=106 memory=30 control=15 system=4"
    )
    print(f"descriptors={len(generated)}")
    print(f"operation_kinds={len(set(token[1] for token in generated.values()))}")
    print(f"dest_read={sum(1 for token in generated.values() if token[4])}")
    print(f"dual_destination={sum(1 for token in generated.values() if token[5] == 2)}")

    if args.force_failure:
        raise AssertionError("forced execution-coverage checker failure")

    print("EXEC_COVERAGE CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
