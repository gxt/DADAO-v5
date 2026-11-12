#!/usr/bin/env python3
"""Generate independent RTL-010t memory vectors and Scala expectations."""

from __future__ import annotations

import argparse
import copy
import re
from dataclasses import dataclass, replace
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts/opcodes.yaml"
DEFAULT_YAML = ROOT / "tests/rtl/core/RTL-010t-memory-vectors.yaml"
DEFAULT_SCALA = (
    ROOT / "rtl/dadao/src/test/scala/dadao/DADAOMemoryOracleTable.scala"
)

RAM_BASE = 0xFC00_0000_0000
RAM_SIZE = 0x100_0000
BOOT_ROM_BASE = 0xFFFF_FFFF_0000
BOOT_ROM_SIZE = 0x1_0000
LEGACY_EXIT_BASE = 0xFFFF_8000_0000
TEST_PC = RAM_BASE
DATA_BASE = RAM_BASE + 0x100

REG_BANK = {"rd": 0, "rb": 1, "ra": 2}
FAULT = {
    "none": 0x00,
    "unmapped": 0x87,
    "illi": 0x88,
    "undi": 0x89,
    "rasof": 0x8A,
    "rasuf": 0x8B,
    "malign": 0x8C,
    "ialign": 0x8D,
}
MASK64 = (1 << 64) - 1
MAX_MEMORY_ENTRIES = 16


@dataclass(frozen=True)
class RegValue:
    bank: int
    index: int
    value: int


@dataclass(frozen=True)
class MemoryEntry:
    index: int
    address: int
    data: int
    writable: bool
    fault: bool
    fault_code: int


@dataclass(frozen=True)
class MemoryVector:
    name: str
    instruction_id: int
    word: int
    coverage: bool
    category: str
    width_bytes: int
    signed: bool
    is_block: bool
    is_store: bool
    count: int
    initial_registers: tuple[RegValue, ...]
    initial_memory: tuple[MemoryEntry, ...]
    expected_registers: tuple[RegValue, ...]
    expected_memory: tuple[MemoryEntry, ...]
    expected_pc: int
    expected_fault: bool
    expected_fault_code: int
    expected_data_requests: int


def parse_bits(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"\[(\d+):(\d+)\]", text)
    if not match:
        raise AssertionError(f"unsupported field bits: {text}")
    high = int(match.group(1))
    low = int(match.group(2))
    return low, high - low + 1


def set_field(word: int, low: int, width: int, value: int) -> int:
    mask = ((1 << width) - 1) << low
    return (word & ~mask) | ((value << low) & mask)


def encode(entry: dict, values: dict[str, int]) -> int:
    word = int(entry["value"], 16)
    fields = {field["name"]: field for field in entry["fields"]}
    for name, value in values.items():
        if name not in fields:
            raise AssertionError(
                f"{entry['id']} has no field {name}; fields={list(fields)}"
            )
        low, width = parse_bits(fields[name]["bits"])
        word = set_field(word, low, width, value)
    return word & 0xFFFF_FFFF


def width_for(mnemonic: str) -> int:
    suffix = mnemonic.split(".")[-1]
    if suffix in {"b", "ub", "sb"}:
        return 1
    if suffix in {"w", "uw", "sw"}:
        return 2
    if suffix in {"t", "ut", "st"}:
        return 4
    if suffix == "o":
        return 8
    raise AssertionError(f"unsupported memory mnemonic: {mnemonic}")


def signed_for(mnemonic: str) -> bool:
    return mnemonic.split(".")[-1] in {"sb", "sw", "st"}


def align_down(address: int) -> int:
    return address & ~0x7


def beat_bytes(beat: int) -> list[int]:
    return [(beat >> ((7 - index) * 8)) & 0xFF for index in range(8)]


def bytes_to_beat(values: list[int]) -> int:
    result = 0
    for value in values:
        result = (result << 8) | (value & 0xFF)
    return result


def read_guest(
    beat: int,
    offset: int,
    size_bytes: int,
    signed: bool,
) -> int:
    data = beat_bytes(beat)
    raw = bytes_to_beat(data[offset : offset + size_bytes])
    value_mask = (1 << (size_bytes * 8)) - 1
    sign = 1 << (size_bytes * 8 - 1)
    if signed and raw & sign:
        raw |= MASK64 ^ value_mask
    return raw & MASK64


def write_guest(
    beat: int,
    value: int,
    offset: int,
    size_bytes: int,
) -> int:
    data = beat_bytes(beat)
    value &= (1 << (size_bytes * 8)) - 1
    for index in range(size_bytes):
        shift = (size_bytes - 1 - index) * 8
        data[offset + index] = (value >> shift) & 0xFF
    return bytes_to_beat(data)


def initial_beat(address: int, ordinal: int) -> int:
    # Every naturally aligned narrow signed lane has its sign bit set.
    seed = 0x8976_6754_8532_F1F0
    return (
        seed ^ ((address - DATA_BASE) & 0xFFFF_FFFF_FFFF)
        ^ ((ordinal + 1) * 0x0101_0101_0101_0101)
    ) & MASK64


def source_value(index: int) -> int:
    return (0xEEDD_CCBB_AA99_8877 - index * 0x1111_1111_1111_1111) & MASK64


def register_sequence(values: dict[tuple[int, int], int]) -> tuple[RegValue, ...]:
    return tuple(
        RegValue(bank, index, value & MASK64)
        for (bank, index), value in sorted(values.items())
    )


def memory_sequence(
    entries: dict[int, MemoryEntry],
) -> tuple[MemoryEntry, ...]:
    return tuple(entries[index] for index in sorted(entries))


def make_positive_vector(entry: dict) -> MemoryVector:
    instruction_id = int(entry["id_index"])
    mnemonic = entry["mnemonic"]
    fields = entry["fields"]
    size_bytes = width_for(mnemonic)
    signed = signed_for(mnemonic)
    is_block = entry["id"].startswith(("ldm.", "stm."))
    is_store = entry["id"].startswith(("st.", "stm."))
    count = 3 if is_block else 1
    start_reg = 8
    base_reg = 2
    offset_reg = 1

    if is_block:
        word = encode(
            entry,
            {
                fields[0]["name"]: start_reg,
                "rbhb": base_reg,
                "rdhc": offset_reg,
                "immu6": count,
            },
        )
        base_address = DATA_BASE
    else:
        word = encode(
            entry,
            {
                fields[0]["name"]: start_reg,
                "rbhb": base_reg,
                "imms12": 0,
            },
        )
        base_address = DATA_BASE + (8 - size_bytes)

    bank = REG_BANK[fields[0]["bank"]]
    addresses = [
        base_address + index * size_bytes for index in range(count)
    ]
    aligned_addresses = sorted({align_down(address) for address in addresses})
    initial_beats = {
        address: initial_beat(address, ordinal)
        for ordinal, address in enumerate(aligned_addresses)
    }

    initial_registers = {
        (REG_BANK["rb"], base_reg): base_address,
    }
    if is_block:
        initial_registers[(REG_BANK["rd"], offset_reg)] = 0

    for index in range(count):
        register_index = start_reg + index
        if is_store:
            initial_registers[(bank, register_index)] = source_value(index)
        else:
            initial_registers[(bank, register_index)] = (
                0xD000_0000_0000_0000 + register_index
            )

    expected_registers: dict[tuple[int, int], int] = {}
    if not is_store:
        for index, address in enumerate(addresses):
            beat = initial_beats[align_down(address)]
            expected_registers[(bank, start_reg + index)] = read_guest(
                beat,
                address & 0x7,
                size_bytes,
                signed,
            )

    expected_beats = dict(initial_beats)
    if is_store:
        for index, address in enumerate(addresses):
            aligned = align_down(address)
            value = initial_registers[(bank, start_reg + index)]
            expected_beats[aligned] = write_guest(
                expected_beats[aligned],
                value,
                address & 0x7,
                size_bytes,
            )

    initial_memory = {
        memory_index: MemoryEntry(
            memory_index,
            address,
            data,
            writable=True,
            fault=False,
            fault_code=FAULT["none"],
        )
        for memory_index, (address, data) in enumerate(
            initial_beats.items(),
            start=1,
        )
    }
    memory_address_to_index = {
        memory.address: memory.index for memory in initial_memory.values()
    }
    expected_memory = {
        memory_address_to_index[address]: replace(
            initial_memory[memory_address_to_index[address]],
            data=data,
        )
        for address, data in expected_beats.items()
    }

    return MemoryVector(
        name=f"positive-{entry['id']}",
        instruction_id=instruction_id,
        word=word,
        coverage=True,
        category=(
            "block_store"
            if is_block and is_store
            else "block_load"
            if is_block
            else "single_store"
            if is_store
            else "single_load"
        ),
        width_bytes=size_bytes,
        signed=signed,
        is_block=is_block,
        is_store=is_store,
        count=count,
        initial_registers=register_sequence(initial_registers),
        initial_memory=memory_sequence(initial_memory),
        expected_registers=register_sequence(expected_registers),
        expected_memory=memory_sequence(expected_memory),
        expected_pc=TEST_PC + 4,
        expected_fault=False,
        expected_fault_code=FAULT["none"],
        expected_data_requests=count,
    )


def replace_register(
    registers: tuple[RegValue, ...],
    bank: int,
    index: int,
    value: int,
) -> tuple[RegValue, ...]:
    values = {(register.bank, register.index): register.value for register in registers}
    values[(bank, index)] = value & MASK64
    return register_sequence(values)


def fault_single(
    template: MemoryVector,
    *,
    name: str,
    base_address: int,
    fault_code: int,
) -> MemoryVector:
    registers = replace_register(
        template.initial_registers,
        REG_BANK["rb"],
        2,
        base_address,
    )
    expected_registers = (
        ()
        if template.is_store
        else tuple(
            register
            for register in registers
            if 0xD000_0000_0000_0000
            <= register.value
            <= 0xDFFF_FFFF_FFFF_FFFF
        )
    )
    return replace(
        template,
        name=name,
        coverage=False,
        category="fault_single",
        initial_registers=registers,
        initial_memory=(),
        expected_registers=expected_registers,
        expected_memory=(),
        expected_pc=TEST_PC,
        expected_fault=True,
        expected_fault_code=fault_code,
        expected_data_requests=0,
    )


def build_fault_vectors(by_id: dict[str, MemoryVector]) -> list[MemoryVector]:
    vectors = [
        fault_single(
            by_id["ld.ub_rrii_rd"],
            name="fault-single-load-unmapped",
            base_address=LEGACY_EXIT_BASE,
            fault_code=FAULT["unmapped"],
        ),
        fault_single(
            by_id["st.b_rrii_rd"],
            name="fault-single-store-bootrom",
            base_address=BOOT_ROM_BASE,
            fault_code=FAULT["illi"],
        ),
        fault_single(
            by_id["ld.ut_rrii_rd"],
            name="fault-single-load-misaligned",
            base_address=DATA_BASE + 2,
            fault_code=FAULT["malign"],
        ),
        fault_single(
            by_id["ld.ut_rrii_rd"],
            name="fault-priority-unmapped-over-misaligned",
            base_address=LEGACY_EXIT_BASE + 2,
            fault_code=FAULT["unmapped"],
        ),
    ]

    store = by_id["stm.o_rrri_rd"]
    late_unmapped_base = RAM_BASE + RAM_SIZE - 8
    first_beat = 0x1122_3344_5566_7788
    first_memory = MemoryEntry(
        1,
        late_unmapped_base,
        first_beat,
        writable=True,
        fault=False,
        fault_code=FAULT["none"],
    )
    late_unmapped_registers = replace_register(
        replace_register(
            store.initial_registers,
            REG_BANK["rb"],
            2,
            late_unmapped_base,
        ),
        REG_BANK["rd"],
        1,
        0,
    )
    vectors.append(
        replace(
            store,
            name="fault-block-store-late-unmapped",
            coverage=False,
            category="fault_block_store",
            count=2,
            word=set_field(store.word, 0, 6, 2),
            initial_registers=late_unmapped_registers,
            initial_memory=(first_memory,),
            expected_registers=(),
            expected_memory=(first_memory,),
            expected_pc=TEST_PC,
            expected_fault=True,
            expected_fault_code=FAULT["unmapped"],
            expected_data_requests=0,
        )
    )

    load = by_id["ldm.o_rrri_rd"]
    count_two_word = set_field(load.word, 0, 6, 2)
    load_registers = replace_register(
        load.initial_registers,
        REG_BANK["rb"],
        2,
        DATA_BASE,
    )
    good_memory = MemoryEntry(
        1,
        DATA_BASE,
        0xAABB_CCDD_EEFF_0011,
        writable=True,
        fault=False,
        fault_code=FAULT["none"],
    )
    bad_memory = MemoryEntry(
        2,
        DATA_BASE + 8,
        0,
        writable=True,
        fault=True,
        fault_code=FAULT["unmapped"],
    )
    vectors.append(
        replace(
            load,
            name="fault-block-load-late-response",
            coverage=False,
            category="fault_block_response",
            count=2,
            word=count_two_word,
            initial_registers=load_registers,
            initial_memory=(good_memory, bad_memory),
            expected_registers=tuple(
                register
                for register in load_registers
                if 0xD000_0000_0000_0000
                <= register.value
                <= 0xDFFF_FFFF_FFFF_FFFF
            ),
            expected_memory=(good_memory, bad_memory),
            expected_pc=TEST_PC,
            expected_fault=True,
            expected_fault_code=FAULT["unmapped"],
            expected_data_requests=2,
        )
    )

    zero_count = replace_register(
        load.initial_registers,
        REG_BANK["rb"],
        2,
        DATA_BASE,
    )
    vectors.append(
        replace(
            load,
            name="fault-block-load-zero-count",
            coverage=False,
            category="fault_static",
            count=0,
            word=set_field(load.word, 0, 6, 0),
            initial_registers=zero_count,
            initial_memory=(),
            expected_registers=tuple(
                register
                for register in zero_count
                if 0xD000_0000_0000_0000
                <= register.value
                <= 0xDFFF_FFFF_FFFF_FFFF
            ),
            expected_memory=(),
            expected_pc=TEST_PC,
            expected_fault=True,
            expected_fault_code=FAULT["illi"],
            expected_data_requests=0,
        )
    )

    overflow_registers = replace_register(
        replace_register(
            load.initial_registers,
            REG_BANK["rb"],
            2,
            DATA_BASE,
        ),
        REG_BANK["rd"],
        8,
        0xD000_0000_0000_0008,
    )
    overflow_word = encode(
        next(entry for entry in OPCODE_ENTRIES if entry["id"] == "ldm.o_rrri_rd"),
        {"rdha": 63, "rbhb": 2, "rdhc": 1, "immu6": 2},
    )
    vectors.append(
        replace(
            load,
            name="fault-block-load-range-overflow",
            coverage=False,
            category="fault_static",
            count=2,
            word=overflow_word,
            initial_registers=overflow_registers,
            initial_memory=(),
            expected_registers=tuple(
                register
                for register in overflow_registers
                if 0xD000_0000_0000_0000
                <= register.value
                <= 0xDFFF_FFFF_FFFF_FFFF
            ),
            expected_memory=(),
            expected_pc=TEST_PC,
            expected_fault=True,
            expected_fault_code=FAULT["illi"],
            expected_data_requests=0,
        )
    )

    return vectors


def load_opcodes() -> list[dict]:
    data = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise AssertionError("opcodes.yaml root must be a sequence")
    for index, entry in enumerate(data):
        entry["id_index"] = index
    return data


OPCODE_ENTRIES = load_opcodes()


def build_vectors() -> list[MemoryVector]:
    memory_entries = [
        entry
        for entry in OPCODE_ENTRIES
        if entry.get("scope") == "m1"
        and entry["id"].startswith(("ld.", "st.", "ldm.", "stm."))
    ]
    if len(memory_entries) != 30:
        raise AssertionError(
            f"expected 30 M1 memory instructions, got {len(memory_entries)}"
        )

    positive = [make_positive_vector(entry) for entry in memory_entries]
    by_id = {entry["id"]: vector for entry, vector in zip(memory_entries, positive)}
    return positive + build_fault_vectors(by_id)


def validate_vectors(vectors: list[MemoryVector]) -> None:
    names = [vector.name for vector in vectors]
    if len(names) != len(set(names)):
        raise AssertionError("duplicate memory oracle vector names")

    positive = [vector for vector in vectors if vector.coverage]
    ids = [vector.instruction_id for vector in positive]
    if len(ids) != 30 or len(set(ids)) != 30:
        raise AssertionError("positive vectors do not cover 30 unique ids")

    widths = {vector.width_bytes for vector in positive}
    if widths != {1, 2, 4, 8}:
        raise AssertionError(f"missing memory widths: {sorted(widths)}")
    if not any(vector.signed for vector in positive if vector.width_bytes < 8):
        raise AssertionError("missing signed narrow load/store coverage")

    for vector in vectors:
        if vector.expected_pc % 4 != 0:
            raise AssertionError(f"misaligned expected pc in {vector.name}")
        if vector.expected_fault:
            if vector.expected_fault_code == FAULT["none"]:
                raise AssertionError(f"fault vector has no code: {vector.name}")
        elif vector.expected_fault_code != FAULT["none"]:
            raise AssertionError(f"success vector has fault code: {vector.name}")
        if any(
            memory.index == 0
            for memory in vector.initial_memory + vector.expected_memory
        ):
            raise AssertionError(f"memory vector uses instruction index 0: {vector.name}")


def corrupt_vector(
    vectors: list[MemoryVector],
    failure_mode: str,
) -> None:
    def changed_registers(vector: MemoryVector) -> list[RegValue]:
        initial = {
            (register.bank, register.index): register.value
            for register in vector.initial_registers
        }
        return [
            register
            for register in vector.expected_registers
            if initial.get((register.bank, register.index)) != register.value
        ]

    if failure_mode == "endianness":
        index = next(
            index
            for index, vector in enumerate(vectors)
            if vector.coverage
            and vector.category == "single_store"
            and vector.width_bytes == 4
        )
        memory = vectors[index].expected_memory[0]
        data = memory.data
        swapped = int.from_bytes(data.to_bytes(8, "big")[::-1], "little")
        vectors[index] = replace(
            vectors[index],
            expected_memory=(replace(memory, data=swapped),),
        )
    elif failure_mode == "wstrb":
        index = next(
            index
            for index, vector in enumerate(vectors)
            if vector.coverage and vector.category == "single_store"
        )
        memory = vectors[index].expected_memory[0]
        vectors[index] = replace(
            vectors[index],
            expected_memory=(replace(memory, data=0),),
        )
    elif failure_mode == "extension":
        index = next(
            index
            for index, vector in enumerate(vectors)
            if vector.coverage
            and vector.category == "single_load"
            and vector.signed
            and vector.width_bytes == 1
        )
        vector = vectors[index]
        register = changed_registers(vector)[0]
        values = {
            (item.bank, item.index): item.value
            for item in vector.expected_registers
        }
        values[(register.bank, register.index)] = register.value & 0xFF
        vectors[index] = replace(
            vector,
            expected_registers=register_sequence(values),
        )
    elif failure_mode == "priority":
        index = next(
            index
            for index, vector in enumerate(vectors)
            if vector.name == "fault-priority-unmapped-over-misaligned"
        )
        vectors[index] = replace(
            vectors[index],
            expected_fault_code=FAULT["malign"],
        )
    elif failure_mode == "partial-commit":
        index = next(
            index
            for index, vector in enumerate(vectors)
            if vector.name == "fault-block-load-late-response"
        )
        vector = vectors[index]
        register = next(
            register
            for register in vector.initial_registers
            if 0xD000_0000_0000_0000
            <= register.value
            <= 0xDFFF_FFFF_FFFF_FFFF
        )
        values = {
            (item.bank, item.index): item.value
            for item in vector.expected_registers
        }
        values[(register.bank, register.index)] ^= 0x55
        vectors[index] = replace(
            vector,
            expected_registers=register_sequence(values),
        )
    elif failure_mode == "block-stride":
        index = next(
            index
            for index, vector in enumerate(vectors)
            if vector.coverage and vector.category == "block_load"
        )
        vector = vectors[index]
        target = changed_registers(vector)[1]
        values = {
            (item.bank, item.index): item.value
            for item in vector.expected_registers
        }
        values[(target.bank, target.index)] ^= 0x1F
        vectors[index] = replace(
            vector,
            expected_registers=register_sequence(values),
        )
    else:
        raise AssertionError(f"unknown failure mode: {failure_mode}")


def hex_value(value: int) -> str:
    return f"0x{value & MASK64:016x}"


def register_payload(registers: tuple[RegValue, ...]) -> list[dict]:
    return [
        {
            "bank": register.bank,
            "index": register.index,
            "value": hex_value(register.value),
        }
        for register in registers
    ]


def memory_payload(memory: tuple[MemoryEntry, ...]) -> list[dict]:
    return [
        {
            "index": entry.index,
            "address": f"0x{entry.address:016x}",
            "data": hex_value(entry.data),
            "writable": entry.writable,
            "fault": entry.fault,
            "fault_code": entry.fault_code,
        }
        for entry in memory
    ]


def vector_payload(vector: MemoryVector) -> dict:
    return {
        "name": vector.name,
        "instruction_id": vector.instruction_id,
        "word": f"0x{vector.word:08x}",
        "coverage": vector.coverage,
        "category": vector.category,
        "width_bytes": vector.width_bytes,
        "signed": vector.signed,
        "is_block": vector.is_block,
        "is_store": vector.is_store,
        "count": vector.count,
        "initial_registers": register_payload(vector.initial_registers),
        "initial_memory": memory_payload(vector.initial_memory),
        "expected_registers": register_payload(vector.expected_registers),
        "expected_memory": memory_payload(vector.expected_memory),
        "expected_pc": f"0x{vector.expected_pc:016x}",
        "expected_fault": vector.expected_fault,
        "expected_fault_code": vector.expected_fault_code,
        "expected_data_requests": vector.expected_data_requests,
    }


def emit_yaml(path: Path, vectors: list[MemoryVector]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            [vector_payload(vector) for vector in vectors],
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def scala_registers(registers: tuple[RegValue, ...]) -> str:
    if not registers:
        return "Seq.empty"
    values = [
        f"DADAOMemoryRegValue({register.bank}, {register.index}, "
        f'BigInt("{register.value:016x}", 16))'
        for register in registers
    ]
    return "Seq(" + ", ".join(values) + ")"


def scala_memory(memory: tuple[MemoryEntry, ...]) -> str:
    if not memory:
        return "Seq.empty"
    values = [
        "DADAOMemoryValue("
        f"{entry.index}, "
        f'BigInt("{entry.address:016x}", 16), '
        f'BigInt("{entry.data:016x}", 16), '
        f"{str(entry.writable).lower()}, "
        f"{str(entry.fault).lower()}, "
        f"{entry.fault_code})"
        for entry in memory
    ]
    return "Seq(" + ", ".join(values) + ")"


def emit_scala(path: Path, vectors: list[MemoryVector]) -> None:
    lines = [
        "package dadao",
        "",
        "// Generated by tools/rtl/check_dadao_memory_oracle.py.",
        "private[dadao] final case class DADAOMemoryRegValue(",
        "    bank: Int,",
        "    index: Int,",
        "    value: BigInt",
        ")",
        "",
        "private[dadao] final case class DADAOMemoryValue(",
        "    index: Int,",
        "    address: BigInt,",
        "    data: BigInt,",
        "    writable: Boolean,",
        "    fault: Boolean,",
        "    faultCode: Int",
        ")",
        "",
        "private[dadao] final case class DADAOMemoryOracleVector(",
        "    name: String,",
        "    instructionId: Int,",
        "    word: BigInt,",
        "    coverage: Boolean,",
        "    category: String,",
        "    widthBytes: Int,",
        "    signed: Boolean,",
        "    isBlock: Boolean,",
        "    isStore: Boolean,",
        "    count: Int,",
        "    initialRegisters: Seq[DADAOMemoryRegValue],",
        "    initialMemory: Seq[DADAOMemoryValue],",
        "    expectedRegisters: Seq[DADAOMemoryRegValue],",
        "    expectedMemory: Seq[DADAOMemoryValue],",
        "    expectedPc: BigInt,",
        "    expectedFault: Boolean,",
        "    expectedFaultCode: Int,",
        "    expectedDataRequests: Int",
        ")",
        "",
        "private[dadao] object DADAOMemoryOracleTable {",
        "  val vectors: Seq[DADAOMemoryOracleVector] = Seq(",
    ]
    for vector in vectors:
        lines.extend(
            [
                "    DADAOMemoryOracleVector(",
                f'      "{vector.name}",',
                f"      {vector.instruction_id},",
                f'      BigInt("{vector.word:08x}", 16),',
                f"      {str(vector.coverage).lower()},",
                f'      "{vector.category}",',
                f"      {vector.width_bytes},",
                f"      {str(vector.signed).lower()},",
                f"      {str(vector.is_block).lower()},",
                f"      {str(vector.is_store).lower()},",
                f"      {vector.count},",
                f"      {scala_registers(vector.initial_registers)},",
                f"      {scala_memory(vector.initial_memory)},",
                f"      {scala_registers(vector.expected_registers)},",
                f"      {scala_memory(vector.expected_memory)},",
                f'      BigInt("{vector.expected_pc:016x}", 16),',
                f"      {str(vector.expected_fault).lower()},",
                f"      {vector.expected_fault_code},",
                f"      {vector.expected_data_requests}",
                "    ),",
            ]
        )
    lines.extend(["  )", "}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RTL-010t independent memory oracle vectors."
    )
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML)
    parser.add_argument("--scala", type=Path, default=DEFAULT_SCALA)
    parser.add_argument(
        "--failure-mode",
        choices=[
            "endianness",
            "wstrb",
            "extension",
            "priority",
            "partial-commit",
            "block-stride",
        ],
    )
    parser.add_argument("--force-failure", action="store_true")
    args = parser.parse_args()

    canonical = build_vectors()
    validate_vectors(canonical)
    vectors = copy.deepcopy(canonical)

    if args.failure_mode:
        corrupt_vector(vectors, args.failure_mode)
        if vectors == canonical:
            raise AssertionError(
                f"{args.failure_mode} corruption did not change vectors"
            )
        raise AssertionError(
            f"forced {args.failure_mode} memory oracle failure detected"
        )
    if args.force_failure:
        raise AssertionError("forced memory oracle failure")

    emit_yaml(args.yaml, vectors)
    emit_scala(args.scala, vectors)

    positive = [vector for vector in vectors if vector.coverage]
    print(f"vectors={len(vectors)}")
    print(f"positive_vectors={len(positive)}")
    print(f"instruction_ids={len({vector.instruction_id for vector in positive})}")
    print(f"fault_vectors={len(vectors) - len(positive)}")
    print(f"widths={sorted({vector.width_bytes for vector in positive})}")
    print(f"yaml={args.yaml}")
    print(f"scala={args.scala}")
    print("MEMORY_ORACLE CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
