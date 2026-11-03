#!/usr/bin/env python3
"""Generate RTL-009t execution descriptors from opcodes.yaml."""

from __future__ import annotations

import argparse
import collections
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS = ROOT / "contracts/opcodes.yaml"
DEFAULT_OUTPUT = ROOT / "rtl/dadao/src/main/scala/dadao/DADAOExecTable.scala"

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

SPECIAL = {
    "NONE": 0,
    "SET_WYDE": 1,
    "COPY_BLOCK": 2,
}

COPY_MNEMONICS = {
    "rd2rd",
    "rb2rb",
    "rb2rd",
    "rd2rb",
    "ra2rd",
    "rd2ra",
}

SYSTEM_MNEMONICS = {"cfx2rd", "cfx2rc", "escape", "trap"}


@dataclass(frozen=True)
class RegRef:
    bank: int
    low: int
    width: int

    @property
    def valid(self) -> bool:
        return self.bank >= 0


@dataclass(frozen=True)
class Descriptor:
    ident: int
    operation: int
    width_code: int
    signed: bool
    dest_read: bool
    dst_count: int
    src_count: int
    dst0: RegRef
    dst1: RegRef
    src0: RegRef
    src1: RegRef
    src2: RegRef
    imm_mode: int
    imm_low: int
    imm_width: int
    wyde_pos_low: int
    wyde_pos_width: int
    special: int


INVALID_REF = RegRef(-1, 0, 0)


def parse_bits(field: dict, record_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"\[(\d+):(\d+)\]", str(field["bits"]))
    if match is None:
        raise ValueError(
            f"{record_id}: malformed bits for {field['name']}: {field['bits']}"
        )
    high, low = map(int, match.groups())
    return low, high - low + 1


def register_ref(record: dict, field: dict) -> RegRef:
    record_id = str(record["id"])
    bank_name = str(field["bank"])
    if bank_name not in BANK_CODES:
        raise ValueError(f"{record_id}: unsupported bank {bank_name}")
    low, width = parse_bits(field, record_id)
    if width != 6:
        raise ValueError(
            f"{record_id}: register field {field['name']} is not 6 bits"
        )
    return RegRef(BANK_CODES[bank_name], low, width)


def partition(record: dict) -> str:
    record_id = str(record["id"])
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
    if mnemonic in COPY_MNEMONICS:
        return "rtl009"
    return "rtl009"


def operation_for(record: dict) -> int:
    mnemonic = str(record["mnemonic"])
    record_id = str(record["id"])

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
    if mnemonic.startswith("cs."):
        return {
            "cs.n": OP["CS_N"],
            "cs.z": OP["CS_Z"],
            "cs.p": OP["CS_P"],
            "cs.eq": OP["CS_EQ"],
            "cs.ne": OP["CS_NE"],
        }[mnemonic]

    base = mnemonic.split(".")[0]
    operation_names = {
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
    if base not in operation_names:
        raise ValueError(f"{record_id}: unsupported RTL-009t mnemonic")
    return OP[operation_names[base]]


def width_and_signed(record: dict) -> tuple[int, bool]:
    mnemonic = str(record["mnemonic"])
    if mnemonic in COPY_MNEMONICS:
        return 64, False
    if mnemonic in {"set.ow", "set.zw", "or.w", "andn.w"}:
        return 16, False
    if mnemonic == "add.si":
        return 64, True
    if mnemonic == "cmp.si":
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

    suffixes = {
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
    for suffix, result in suffixes.items():
        if mnemonic.endswith(suffix):
            return result
    raise ValueError(
        f"{record['id']}: cannot determine width/signedness for {mnemonic}"
    )


def immediate_for(record: dict) -> tuple[int, int, int, int, int]:
    record_id = str(record["id"])
    imm_fields = [
        field
        for field in record.get("fields", [])
        if str(field["role"]) == "imm"
    ]
    wyde_fields = [
        field
        for field in record.get("fields", [])
        if str(field["role"]) == "wyde_pos"
    ]
    if not imm_fields:
        if wyde_fields:
            raise ValueError(f"{record_id}: wyde position without immediate")
        return IMM["NONE"], 0, 0, -1, 0
    if len(imm_fields) != 1:
        raise ValueError(f"{record_id}: multiple immediate fields")

    field = imm_fields[0]
    low, width = parse_bits(field, record_id)
    name = str(field["name"])
    mode_by_name = {
        "immu6": IMM["IMMU6"],
        "imms12": IMM["IMMS12"],
        "immu12": IMM["IMMU12"],
        "imms18": IMM["IMMS18"],
        "immu16": IMM["IMMU16_WYDE"],
    }
    if name not in mode_by_name:
        raise ValueError(f"{record_id}: unsupported immediate field {name}")
    mode = mode_by_name[name]

    wyde_low = -1
    wyde_width = 0
    if mode == IMM["IMMU16_WYDE"]:
        if len(wyde_fields) != 1:
            raise ValueError(
                f"{record_id}: IMMU16_WYDE requires one wyde-position field"
            )
        wyde_low, wyde_width = parse_bits(wyde_fields[0], record_id)
        if (low, width, wyde_low, wyde_width) != (0, 16, 16, 2):
            raise ValueError(
                f"{record_id}: unexpected rwii bit layout"
            )
    elif wyde_fields:
        raise ValueError(f"{record_id}: unexpected wyde-position field")
    return mode, low, width, wyde_low, wyde_width


def build_descriptor(record: dict, ident: int) -> Descriptor:
    record_id = str(record["id"])
    mnemonic = str(record["mnemonic"])

    destinations = [
        register_ref(record, field)
        for field in record.get("fields", [])
        if str(field["role"]) == "dst"
    ]
    sources = [
        register_ref(record, field)
        for field in record.get("fields", [])
        if str(field["role"]) == "src"
    ]
    if not destinations or len(destinations) > 2:
        raise ValueError(
            f"{record_id}: unsupported destination count {len(destinations)}"
        )

    dest_read = mnemonic in {"add.si", "or.w", "andn.w"}
    if dest_read:
        sources.insert(0, destinations[0])
    if len(sources) > 3:
        raise ValueError(f"{record_id}: more than three source operands")

    width, signed = width_and_signed(record)
    imm_mode, imm_low, imm_width, wyde_low, wyde_width = immediate_for(
        record
    )
    special = (
        SPECIAL["COPY_BLOCK"]
        if mnemonic in COPY_MNEMONICS
        else SPECIAL["SET_WYDE"]
        if mnemonic in {"set.ow", "set.zw", "or.w", "andn.w"}
        else SPECIAL["NONE"]
    )

    dst0, dst1 = (destinations + [INVALID_REF, INVALID_REF])[:2]
    src0, src1, src2 = (sources + [INVALID_REF] * 3)[:3]
    return Descriptor(
        ident=ident,
        operation=operation_for(record),
        width_code=WIDTH_CODES[width],
        signed=signed,
        dest_read=dest_read,
        dst_count=len(destinations),
        src_count=len(sources),
        dst0=dst0,
        dst1=dst1,
        src0=src0,
        src1=src1,
        src2=src2,
        imm_mode=imm_mode,
        imm_low=imm_low,
        imm_width=imm_width,
        wyde_pos_low=wyde_low,
        wyde_pos_width=wyde_width,
        special=special,
    )


def scala_ref(ref: RegRef) -> str:
    return f"DADAOExecRegRef({ref.bank}, {ref.low}, {ref.width})"


def scala_entry(entry: Descriptor) -> str:
    return (
        "    DADAOExecEntry("
        f"{entry.ident}, {entry.operation}, {entry.width_code}, "
        f"{str(entry.signed).lower()}, {str(entry.dest_read).lower()}, "
        f"{entry.dst_count}, {entry.src_count}, "
        f"{scala_ref(entry.dst0)}, {scala_ref(entry.dst1)}, "
        f"{scala_ref(entry.src0)}, {scala_ref(entry.src1)}, "
        f"{scala_ref(entry.src2)}, "
        f"{entry.imm_mode}, {entry.imm_low}, {entry.imm_width}, "
        f"{entry.wyde_pos_low}, {entry.wyde_pos_width}, "
        f"{entry.special}),"
    )


def emit_scala(path: Path, descriptors: list[Descriptor], ids: list[str]) -> None:
    lines = [
        "package dadao",
        "",
        "// Generated by tools/rtl/generate_dadao_exec_table.py.",
        "// Source: contracts/opcodes.yaml.",
        "private[dadao] final case class DADAOExecRegRef(",
        "    bank: Int,",
        "    low: Int,",
        "    width: Int",
        ") {",
        "  def valid: Boolean = bank >= 0",
        "}",
        "",
        "private[dadao] final case class DADAOExecEntry(",
        "    id: Int,",
        "    operation: Int,",
        "    widthCode: Int,",
        "    signed: Boolean,",
        "    destRead: Boolean,",
        "    dstCount: Int,",
        "    srcCount: Int,",
        "    dst0: DADAOExecRegRef,",
        "    dst1: DADAOExecRegRef,",
        "    src0: DADAOExecRegRef,",
        "    src1: DADAOExecRegRef,",
        "    src2: DADAOExecRegRef,",
        "    immMode: Int,",
        "    immLow: Int,",
        "    immWidth: Int,",
        "    wydePosLow: Int,",
        "    wydePosWidth: Int,",
        "    special: Int",
        ")",
        "",
        "private[dadao] object DADAOExecWidth {",
        "  val W8: Int = 0",
        "  val W16: Int = 1",
        "  val W32: Int = 2",
        "  val W64: Int = 3",
        "}",
        "",
        "private[dadao] object DADAOExecImmMode {",
        "  val None: Int = 0",
        "  val Immu6: Int = 1",
        "  val Imms12: Int = 2",
        "  val Immu12: Int = 3",
        "  val Imms18: Int = 4",
        "  val Immu16Wyde: Int = 5",
        "}",
        "",
        "private[dadao] object DADAOExecSpecial {",
        "  val None: Int = 0",
        "  val SetWyde: Int = 1",
        "  val CopyBlock: Int = 2",
        "}",
        "",
        "private[dadao] object DADAOExecOperation {",
        *[
            f"  val {name}: Int = {code}"
            for name, code in {
                "Add": OP["ADD"],
                "Sub": OP["SUB"],
                "Mul": OP["MUL"],
                "Div": OP["DIV"],
                "Rem": OP["REM"],
                "Cmp": OP["CMP"],
                "And": OP["AND"],
                "Or": OP["OR"],
                "Xor": OP["XOR"],
                "Xnor": OP["XNOR"],
                "Shl": OP["SHL"],
                "Shr": OP["SHR"],
                "Ext": OP["EXT"],
                "CsN": OP["CS_N"],
                "CsZ": OP["CS_Z"],
                "CsP": OP["CS_P"],
                "CsEq": OP["CS_EQ"],
                "CsNe": OP["CS_NE"],
                "SetOw": OP["SET_OW"],
                "SetZeroWyde": OP["SET_ZW"],
                "OrW": OP["OR_W"],
                "AndnW": OP["ANDN_W"],
                "CopyBlock": OP["COPY_BLOCK"],
                "AipSi": OP["AIP_SI"],
            }.items()
        ],
        "}",
        "",
        "private[dadao] object DADAOExecTable {",
        "  val entries: Seq[DADAOExecEntry] = Seq(",
        *[scala_entry(entry) for entry in descriptors],
        "  )",
        "  val ids: Seq[String] = Seq(",
        *[f'    "{record_id}",' for record_id in ids],
        "  )",
        "  val rtl009Count: Int = 106",
        "  val swymCount: Int = 1",
        "  val memoryCount: Int = 30",
        "  val controlCount: Int = 15",
        "  val systemCount: Int = 4",
        "}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RTL-009t execution descriptor table."
    )
    parser.add_argument("--ops", type=Path, default=DEFAULT_OPS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records = yaml.safe_load(args.ops.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("opcodes.yaml must contain a top-level list")

    counts = collections.Counter()
    descriptors: list[Descriptor] = []
    ids: list[str] = []
    for ident, record in enumerate(records):
        if str(record["scope"]) != "m1":
            continue
        family = partition(record)
        counts[family] += 1
        if family != "rtl009":
            continue
        descriptors.append(build_descriptor(record, ident))
        ids.append(str(record["id"]))

    expected = {
        "swym": 1,
        "rtl009": 106,
        "memory": 30,
        "control": 15,
        "system": 4,
    }
    if dict(counts) != expected:
        raise SystemExit(
            f"M1 partition mismatch: expected={expected}, got={dict(counts)}"
        )
    if len(descriptors) != 106 or len(set(ids)) != 106:
        raise SystemExit("RTL-009t descriptor id coverage mismatch")

    emit_scala(args.output, descriptors, ids)
    print(
        f"generated {args.output}: 106 descriptors; "
        f"partition={dict(sorted(counts.items()))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
