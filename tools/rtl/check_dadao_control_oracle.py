#!/usr/bin/env python3
"""Generate independent RTL-011t control, CFX and RAS oracle vectors."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, replace
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts/opcodes.yaml"
DEFAULT_YAML = ROOT / "tests/rtl/core/RTL-011t-control-vectors.yaml"
DEFAULT_SCALA = (
    ROOT / "rtl/dadao/src/test/scala/dadao/DADAOControlOracleTable.scala"
)

TEST_PC = 0xFC00_0000_0000
MASK48 = (1 << 48) - 1
MASK64 = (1 << 64) - 1
ALL_ONES = MASK64

CFX_UMON = 0
CFX_JMON = 1
CFX_SMON = 2
CFX_HMON = 3
CFX_POWER = 63

MODE_USER = 0
MODE_JAIL = 1
MODE_SUPV = 2
MODE_HYPV = 3

CAUSE_TRAP = 1 << 0
CAUSE_MEM = 1 << 1
CAUSE_REG = 1 << 2
CAUSE_ESC = 1 << 3
CAUSE_PERM = 1 << 7
CAUSE_ILLI = 1 << 8


def load_opcodes() -> list[dict]:
    data = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise AssertionError("opcodes.yaml root must be a sequence")
    for index, entry in enumerate(data):
        entry["id_index"] = index
    return data


OPCODE_ENTRIES = load_opcodes()
OPCODE_BY_ID = {entry["id"]: entry for entry in OPCODE_ENTRIES}


def set_field(word: int, low: int, width: int, value: int) -> int:
    mask = ((1 << width) - 1) << low
    return (word & ~mask) | ((value << low) & mask)


def sign_extend(value: int, width: int) -> int:
    value &= (1 << width) - 1
    sign = 1 << (width - 1)
    if value & sign:
        value |= MASK64 ^ ((1 << width) - 1)
    return value & MASK64


def encode_control(
    instruction_id: str,
    slot0: int = 0,
    slot1: int = 0,
    immediate: int = 0,
) -> int:
    word = int(OPCODE_BY_ID[instruction_id]["value"], 16)
    if instruction_id == "jump_iiii_rb" or instruction_id == "call_iiii_ra":
        return set_field(word, 0, 24, immediate)
    if instruction_id == "ret_riii_ra":
        return set_field(set_field(word, 18, 6, slot0), 0, 18, immediate)
    if instruction_id in {"jump_rrii_rb", "call_rrii_ra"}:
        word = set_field(word, 18, 6, slot0)
        word = set_field(word, 12, 6, slot1)
        return set_field(word, 0, 12, immediate)
    word = set_field(word, 18, 6, slot0)
    if instruction_id in {"br.eq_rrii_rd", "br.ne_rrii_rd"}:
        word = set_field(word, 12, 6, slot1)
        return set_field(word, 0, 12, immediate)
    return set_field(word, 0, 18, immediate)


@dataclass(frozen=True)
class ControlExpected:
    is_control: bool
    is_branch: bool
    is_jump: bool
    is_call: bool
    is_ret: bool
    taken: bool
    target: int
    next_rb0: int
    call_return_address: int
    ret_rd_write: bool
    ret_rd_addr: int
    ret_rd_value: int
    read0_bank: int
    read0_addr: int
    read1_bank: int
    read1_addr: int


@dataclass(frozen=True)
class ControlVector:
    name: str
    instruction_id: str
    instruction_index: int
    word: int
    coverage: bool
    category: str
    current_rb0: int
    read0_value: int
    read1_value: int
    popped_return_address: int
    expected: ControlExpected


def branch_taken(instruction_id: str, left: int, right: int) -> bool:
    predicates = {
        "br.n_riii_rd": bool(left >> 63),
        "br.nn_riii_rd": not bool(left >> 63),
        "br.z_riii_rd": left == 0,
        "br.nz_riii_rd": left != 0,
        "br.p_riii_rd": left != 0 and not bool(left >> 63),
        "br.np_riii_rd": left == 0 or bool(left >> 63),
        "br.eq_rrii_rd": left == right,
        "br.ne_rrii_rd": left != right,
        "br.z_riii_rb": left == 0,
        "br.nz_riii_rb": left != 0,
    }
    return predicates[instruction_id]


def compute_control_expected(
    instruction_id: str,
    slot0: int,
    slot1: int,
    immediate: int,
    current_rb0: int,
    read0_value: int,
    read1_value: int,
    popped_return_address: int,
) -> ControlExpected:
    is_branch = instruction_id.startswith("br.")
    is_jump = instruction_id.startswith("jump_")
    is_call = instruction_id.startswith("call_")
    is_ret = instruction_id == "ret_riii_ra"
    immediate_width = (
        24
        if instruction_id in {"jump_iiii_rb", "call_iiii_ra"}
        else 12
        if instruction_id
        in {
            "br.eq_rrii_rd",
            "br.ne_rrii_rd",
            "jump_rrii_rb",
            "call_rrii_ra",
        }
        else 18
    )
    offset = (sign_extend(immediate, immediate_width) << 2) & MASK64
    indexed = instruction_id in {"jump_rrii_rb", "call_rrii_ra"}
    taken = (
        branch_taken(instruction_id, read0_value, read1_value)
        if is_branch
        else True
    )
    if is_ret:
        target = popped_return_address & MASK48
    elif indexed:
        target = (read0_value + read1_value + offset) & MASK64
    else:
        target = (current_rb0 + offset) & MASK64
    has_read0 = is_branch or indexed
    read0_bank = (
        1
        if has_read0
        and (
            instruction_id.endswith("_rb")
            or instruction_id in {"jump_rrii_rb", "call_rrii_ra"}
        )
        else 0
    )
    has_read1 = instruction_id in {
        "br.eq_rrii_rd",
        "br.ne_rrii_rd",
        "jump_rrii_rb",
        "call_rrii_ra",
    }
    return ControlExpected(
        is_control=True,
        is_branch=is_branch,
        is_jump=is_jump,
        is_call=is_call,
        is_ret=is_ret,
        taken=taken,
        target=target,
        next_rb0=target if taken else (current_rb0 + 4) & MASK64,
        call_return_address=(current_rb0 + 4) & MASK48,
        ret_rd_write=is_ret and slot0 != 0,
        ret_rd_addr=slot0,
        ret_rd_value=sign_extend(immediate, 18) if is_ret else 0,
        read0_bank=read0_bank,
        read0_addr=slot0 if has_read0 else 0,
        read1_bank=0 if has_read1 else 0,
        read1_addr=slot1 if has_read1 else 0,
    )


def add_control(
    vectors: list[ControlVector],
    *,
    name: str,
    instruction_id: str,
    slot0: int,
    slot1: int,
    immediate: int,
    current_rb0: int,
    read0_value: int,
    read1_value: int,
    category: str,
    coverage: bool = True,
    popped_return_address: int = 0,
) -> None:
    word = encode_control(instruction_id, slot0, slot1, immediate)
    expected = compute_control_expected(
        instruction_id,
        slot0,
        slot1,
        immediate,
        current_rb0,
        read0_value,
        read1_value,
        popped_return_address,
    )
    vectors.append(
        ControlVector(
            name=name,
            instruction_id=instruction_id,
            instruction_index=OPCODE_BY_ID[instruction_id]["id_index"],
            word=word,
            coverage=coverage,
            category=category,
            current_rb0=current_rb0,
            read0_value=read0_value & MASK64,
            read1_value=read1_value & MASK64,
            popped_return_address=popped_return_address & MASK48,
            expected=expected,
        )
    )


def build_control_vectors() -> list[ControlVector]:
    vectors: list[ControlVector] = []
    branch_cases = [
        ("br.n_riii_rd", ALL_ONES, 0, True, "predicate"),
        ("br.n_riii_rd", 1, 0, False, "predicate"),
        ("br.nn_riii_rd", 0, 0, True, "predicate"),
        ("br.nn_riii_rd", ALL_ONES, 0, False, "predicate"),
        ("br.z_riii_rd", 0, 0, True, "predicate"),
        ("br.z_riii_rd", 1, 0, False, "predicate"),
        ("br.nz_riii_rd", 1, 0, True, "predicate"),
        ("br.nz_riii_rd", 0, 0, False, "predicate"),
        ("br.p_riii_rd", 1, 0, True, "predicate"),
        ("br.p_riii_rd", 0, 0, False, "predicate"),
        ("br.np_riii_rd", 0, 0, True, "predicate"),
        ("br.np_riii_rd", 1, 0, False, "predicate"),
        ("br.eq_rrii_rd", 7, 7, True, "predicate"),
        ("br.eq_rrii_rd", 7, 8, False, "predicate"),
        ("br.ne_rrii_rd", 7, 8, True, "predicate"),
        ("br.ne_rrii_rd", 7, 7, False, "predicate"),
        ("br.z_riii_rb", 0, 0, True, "rb0"),
        ("br.z_riii_rb", TEST_PC, 0, False, "rb0"),
        ("br.nz_riii_rb", TEST_PC, 0, True, "rb0"),
        ("br.nz_riii_rb", 0, 0, False, "rb0"),
    ]
    for index, (instruction_id, left, right, expected_taken, category) in enumerate(
        branch_cases
    ):
        imm = -1 if index % 2 else 1
        add_control(
            vectors,
            name=f"control-{instruction_id}-{index:02d}",
            instruction_id=instruction_id,
            slot0=3,
            slot1=2,
            immediate=imm,
            current_rb0=TEST_PC,
            read0_value=left,
            read1_value=right,
            category=category,
        )
        if vectors[-1].expected.taken != expected_taken:
            raise AssertionError(f"predicate mismatch for {instruction_id}")

    jump_cases = [
        ("jump_iiii_rb", -0x80_0000, "immediate-min"),
        ("jump_iiii_rb", 0x7F_FFFF, "immediate-max"),
        ("jump_iiii_rb", -2, "immediate-negative"),
        ("jump_rrii_rb", -2, "indexed"),
        ("jump_rrii_rb", 1, "indexed"),
    ]
    for index, (instruction_id, immediate, category) in enumerate(jump_cases):
        add_control(
            vectors,
            name=f"control-{instruction_id}-{index:02d}",
            instruction_id=instruction_id,
            slot0=2 if instruction_id == "jump_rrii_rb" else 0,
            slot1=3 if instruction_id == "jump_rrii_rb" else 0,
            immediate=immediate,
            current_rb0=TEST_PC,
            read0_value=TEST_PC + 0x100,
            read1_value=0x20,
            category=category,
        )

    add_control(
        vectors,
        name="control-br.n-18bit-min",
        instruction_id="br.n_riii_rd",
        slot0=1,
        slot1=0,
        immediate=-0x2_0000,
        current_rb0=TEST_PC,
        read0_value=ALL_ONES,
        read1_value=0,
        category="immediate-min-18",
    )
    add_control(
        vectors,
        name="control-br.n-18bit-max",
        instruction_id="br.n_riii_rd",
        slot0=1,
        slot1=0,
        immediate=0x1_FFFF,
        current_rb0=TEST_PC,
        read0_value=ALL_ONES,
        read1_value=0,
        category="immediate-max-18",
    )
    add_control(
        vectors,
        name="control-br.eq-12bit-min",
        instruction_id="br.eq_rrii_rd",
        slot0=1,
        slot1=2,
        immediate=-0x800,
        current_rb0=TEST_PC,
        read0_value=7,
        read1_value=7,
        category="immediate-min-12",
    )
    add_control(
        vectors,
        name="control-br.eq-12bit-max",
        instruction_id="br.eq_rrii_rd",
        slot0=1,
        slot1=2,
        immediate=0x7FF,
        current_rb0=TEST_PC,
        read0_value=7,
        read1_value=7,
        category="immediate-max-12",
    )
    add_control(
        vectors,
        name="control-call.rrii-12bit-min",
        instruction_id="call_rrii_ra",
        slot0=2,
        slot1=3,
        immediate=-0x800,
        current_rb0=TEST_PC,
        read0_value=TEST_PC + 0x200,
        read1_value=0x40,
        category="immediate-min-12",
    )
    add_control(
        vectors,
        name="control-call.rrii-12bit-max",
        instruction_id="call_rrii_ra",
        slot0=2,
        slot1=3,
        immediate=0x7FF,
        current_rb0=TEST_PC,
        read0_value=TEST_PC + 0x200,
        read1_value=0x40,
        category="immediate-max-12",
    )
    add_control(
        vectors,
        name="control-ret-18bit-min",
        instruction_id="ret_riii_ra",
        slot0=1,
        slot1=0,
        immediate=-0x2_0000,
        current_rb0=TEST_PC,
        read0_value=0,
        read1_value=0,
        category="immediate-min-18",
        popped_return_address=0x0000_FC00_0000_1234,
    )
    add_control(
        vectors,
        name="control-ret-18bit-max",
        instruction_id="ret_riii_ra",
        slot0=1,
        slot1=0,
        immediate=0x1_FFFF,
        current_rb0=TEST_PC,
        read0_value=0,
        read1_value=0,
        category="immediate-max-18",
        popped_return_address=0x0000_FC00_0000_1234,
    )
    add_control(
        vectors,
        name="control-jump-high64-wrap",
        instruction_id="jump_iiii_rb",
        slot0=0,
        slot1=0,
        immediate=1,
        current_rb0=MASK64 - 3,
        read0_value=0,
        read1_value=0,
        category="full-64bit",
    )

    call_cases = [
        ("call_iiii_ra", -2),
        ("call_iiii_ra", 1),
        ("call_rrii_ra", -2),
        ("call_rrii_ra", 1),
    ]
    for index, (instruction_id, immediate) in enumerate(call_cases):
        add_control(
            vectors,
            name=f"control-{instruction_id}-{index:02d}",
            instruction_id=instruction_id,
            slot0=2 if instruction_id == "call_rrii_ra" else 0,
            slot1=3 if instruction_id == "call_rrii_ra" else 0,
            immediate=immediate,
            current_rb0=TEST_PC,
            read0_value=TEST_PC + 0x200,
            read1_value=0x40,
            category="call",
        )

    add_control(
        vectors,
        name="control-ret-rd0",
        instruction_id="ret_riii_ra",
        slot0=0,
        slot1=0,
        immediate=0,
        current_rb0=TEST_PC,
        read0_value=0,
        read1_value=0,
        category="ret",
        popped_return_address=0x0000_FC00_0000_1234,
    )
    add_control(
        vectors,
        name="control-ret-rd1",
        instruction_id="ret_riii_ra",
        slot0=1,
        slot1=0,
        immediate=-1,
        current_rb0=TEST_PC,
        read0_value=0,
        read1_value=0,
        category="ret",
        popped_return_address=0x0000_FC00_0000_5678,
    )
    return vectors


def build_cfx_vectors() -> list[dict]:
    return [
        {
            "kind": "cfx",
            "name": "cfx2rd-self-scratch",
            "category": "cfx2rd",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [
                [CFX_POWER, 6, 1, 0x1234_5678_9ABC_DEF0]
            ],
            "steps": [
                {
                    "op": "cfx2rd",
                    "cfxha": CFX_POWER,
                    "cg": 6,
                    "rc": 1,
                    "rd": 5,
                    "rd_value": 0,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 4,
                    "expected_rd_valid": True,
                    "expected_rd_addr": 5,
                    "expected_rd_data": 0x1234_5678_9ABC_DEF0,
                }
            ],
            "expected": {
                "mode": MODE_HYPV,
                "cfx": CFX_POWER,
                "cause": 0,
                "cause_ip": 0,
                "trap_num": 0,
                "sync_num": 0,
                "escape_num": 0,
                "hmon_global_mask": ALL_ONES,
            },
        },
        {
            "kind": "cfx",
            "name": "cfx2rc-self-scratch",
            "category": "cfx2rc",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [],
            "steps": [
                {
                    "op": "cfx2rc",
                    "cfxha": CFX_POWER,
                    "cg": 6,
                    "rc": 2,
                    "rd": 6,
                    "rd_value": 0x0FED_CBA9_8765_4321,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 4,
                    "expected_rd_valid": False,
                    "expected_rd_addr": 6,
                    "expected_rd_data": 0,
                }
            ],
            "expected": {
                "mode": MODE_HYPV,
                "cfx": CFX_POWER,
                "cause": 0,
                "cause_ip": 0,
                "trap_num": 0,
                "sync_num": 0,
                "escape_num": 0,
                "hmon_global_mask": ALL_ONES,
            },
        },
        {
            "kind": "cfx",
            "name": "trap-power-to-hmon",
            "category": "trap",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [
                [CFX_HMON, 3, 10, TEST_PC + 0x300],
                [CFX_HMON, 3, 8, MODE_SUPV],
                [CFX_HMON, 3, 9, 5],
                [CFX_HMON, 8, 1, 3],
            ],
            "steps": [
                {
                    "op": "trap",
                    "cfxha": CFX_HMON,
                    "immediate": 0x55,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 0x300,
                    "expected_rd_valid": False,
                }
            ],
            "expected": {
                "mode": MODE_SUPV,
                "cfx": CFX_HMON,
                "mask": 5,
                "cause": CAUSE_TRAP,
                "cause_ip": TEST_PC,
                "trap_num": 1,
                "sync_num": 0,
                "escape_num": 0,
                "hmon_global_mask": ALL_ONES,
            },
        },
        {
            "kind": "cfx",
            "name": "trap-escape-restores-frame",
            "category": "trap_escape",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [
                [CFX_HMON, 3, 10, TEST_PC + 0x300],
                [CFX_HMON, 3, 8, MODE_SUPV],
                [CFX_HMON, 3, 9, 5],
                [CFX_HMON, 8, 1, 3],
            ],
            "steps": [
                {
                    "op": "trap",
                    "cfxha": CFX_HMON,
                    "immediate": 0x55,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 0x300,
                    "expected_rd_valid": False,
                },
                {
                    "op": "escape",
                    "cfxha": CFX_HMON,
                    "immediate": 1,
                    "current_ip": TEST_PC + 0x300,
                    "expected_next_ip": TEST_PC + 4,
                    "expected_rd_valid": False,
                },
            ],
            "expected": {
                "mode": MODE_HYPV,
                "cfx": CFX_HMON,
                "mask": ALL_ONES,
                "cause": CAUSE_TRAP,
                "cause_ip": TEST_PC,
                "trap_num": 1,
                "sync_num": 0,
                "escape_num": 1,
                "hmon_global_mask": 3,
            },
        },
        {
            "kind": "cfx",
            "name": "cfx2rd-power-denied-by-hmon",
            "category": "cfxperm",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [
                [CFX_HMON, 3, 10, TEST_PC + 0x300],
                [CFX_HMON, 3, 2, ALL_ONES],
            ],
            "steps": [
                {
                    "op": "cfx2rd",
                    "cfxha": CFX_HMON,
                    "cg": 4,
                    "rc": 0,
                    "rd": 5,
                    "rd_value": 0,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 0x300,
                    "expected_rd_valid": False,
                }
            ],
            "expected": {
                "mode": MODE_HYPV,
                "cfx": CFX_HMON,
                "cause": CAUSE_PERM,
                "cause_ip": TEST_PC,
                "trap_num": 0,
                "sync_num": 1,
                "escape_num": 0,
                "hmon_global_mask": ALL_ONES,
            },
        },
        {
            "kind": "cfx",
            "name": "cfx2rc-readonly-cfxreg",
            "category": "cfxreg",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [
                [CFX_HMON, 3, 10, TEST_PC + 0x340],
            ],
            "steps": [
                {
                    "op": "cfx2rc",
                    "cfxha": CFX_POWER,
                    "cg": 4,
                    "rc": 0,
                    "rd": 7,
                    "rd_value": 0xDEAD_BEEF,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 0x340,
                    "expected_rd_valid": False,
                }
            ],
            "expected": {
                "mode": MODE_HYPV,
                "cfx": CFX_HMON,
                "cause": CAUSE_REG,
                "cause_ip": TEST_PC,
                "trap_num": 0,
                "sync_num": 1,
                "escape_num": 0,
                "hmon_global_mask": ALL_ONES,
            },
        },
        {
            "kind": "cfx",
            "name": "reserved-cfx-illi",
            "category": "illi",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [
                [CFX_HMON, 3, 10, TEST_PC + 0x380],
            ],
            "steps": [
                {
                    "op": "cfx2rd",
                    "cfxha": 6,
                    "cg": 4,
                    "rc": 0,
                    "rd": 5,
                    "rd_value": 0,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 0x380,
                    "expected_rd_valid": False,
                }
            ],
            "expected": {
                "mode": MODE_HYPV,
                "cfx": CFX_HMON,
                "cause": CAUSE_ILLI,
                "cause_ip": TEST_PC,
                "trap_num": 0,
                "sync_num": 1,
                "escape_num": 0,
                "hmon_global_mask": ALL_ONES,
            },
        },
        {
            "kind": "cfx",
            "name": "escape-without-frame-cfxesc",
            "category": "cfxesc",
            "initial_mode": MODE_HYPV,
            "initial_cfx": CFX_POWER,
            "initial_mask": ALL_ONES,
            "register_writes": [
                [CFX_POWER, 3, 10, TEST_PC + 0x3C0],
            ],
            "steps": [
                {
                    "op": "escape",
                    "cfxha": CFX_HMON,
                    "immediate": 0,
                    "current_ip": TEST_PC,
                    "expected_next_ip": TEST_PC + 0x3C0,
                    "expected_rd_valid": False,
                }
            ],
            "expected": {
                "mode": MODE_HYPV,
                "cfx": CFX_POWER,
                "cause": CAUSE_ESC,
                "cause_ip": TEST_PC,
                "trap_num": 0,
                "sync_num": 1,
                "escape_num": 0,
                "hmon_global_mask": ALL_ONES,
            },
        },
    ]


def build_ras_vectors() -> list[dict]:
    return [
        {
            "kind": "ras",
            "name": "C1-push-empty",
            "request": {"push": True, "pop": False, "address": 0xFC00_0000_0100},
            "initial": {"ra_cnt": 0, "mr_ptr": 0, "top_count": 0},
            "expected": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 1, "fault": "none"},
        },
        {
            "kind": "ras",
            "name": "C2-recursive-fold",
            "request": {"push": True, "pop": False, "address": 0xFC00_0000_0100},
            "initial": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 2},
            "expected": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 3, "fault": "none"},
        },
        {
            "kind": "ras",
            "name": "C3a-push-new",
            "request": {"push": True, "pop": False, "address": 0xFC00_0000_0200},
            "initial": {"ra_cnt": 2, "mr_ptr": 0, "top_count": 1},
            "expected": {"ra_cnt": 3, "mr_ptr": 0, "top_count": 1, "fault": "none"},
        },
        {
            "kind": "ras",
            "name": "C3b-spill-oldest",
            "request": {"push": True, "pop": False, "address": 0xFC00_0000_0500},
            "initial": {
                "ra_cnt": 63,
                "mr_ptr": 0xFC00_0000_4000,
                "top_count": 3,
            },
            "expected": {
                "ra_cnt": 63,
                "mr_ptr": 0xFC00_0000_3FF8,
                "top_count": 1,
                "fault": "none",
                "mem_req": True,
                "mem_write": True,
                "mem_addr": 0xFC00_0000_3FF8,
            },
        },
        {
            "kind": "ras",
            "name": "D1-cold-underflow",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {"ra_cnt": 0, "mr_ptr": 0, "top_count": 0},
            "expected": {"ra_cnt": 0, "mr_ptr": 0, "top_count": 0, "fault": "RASUF"},
        },
        {
            "kind": "ras",
            "name": "D2-recursive-decrement",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 2},
            "expected": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 1, "fault": "none"},
        },
        {
            "kind": "ras",
            "name": "D3-normal-pop",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {"ra_cnt": 2, "mr_ptr": 0, "top_count": 1},
            "expected": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 1, "fault": "none"},
        },
        {
            "kind": "ras",
            "name": "D4a-zero-top-count",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 0},
            "expected": {"ra_cnt": 1, "mr_ptr": 0, "top_count": 0, "fault": "RASUF"},
        },
        {
            "kind": "ras",
            "name": "D4b-restore-single",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {
                "ra_cnt": 0,
                "mr_ptr": 0xFC00_0000_6000,
                "restore_count": 1,
            },
            "expected": {
                "ra_cnt": 0,
                "mr_ptr": 0xFC00_0000_6008,
                "fault": "none",
                "mem_req": True,
                "mem_write": False,
            },
        },
        {
            "kind": "ras",
            "name": "D4b-restore-many",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {
                "ra_cnt": 0,
                "mr_ptr": 0xFC00_0000_6000,
                "restore_count": 3,
            },
            "expected": {
                "ra_cnt": 1,
                "mr_ptr": 0xFC00_0000_6008,
                "top_count": 2,
                "fault": "none",
            },
        },
        {
            "kind": "ras",
            "name": "D4b-zero-count-rasuf",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {
                "ra_cnt": 0,
                "mr_ptr": 0xFC00_0000_6000,
                "restore_count": 0,
            },
            "expected": {
                "ra_cnt": 0,
                "mr_ptr": 0xFC00_0000_6000,
                "fault": "RASUF",
            },
        },
        {
            "kind": "ras",
            "name": "D4b-memory-read-fault",
            "request": {"push": False, "pop": True, "address": 0},
            "initial": {
                "ra_cnt": 0,
                "mr_ptr": 0xFC00_0000_6000,
                "memory_fault": "UNMAPPED",
            },
            "expected": {
                "ra_cnt": 0,
                "mr_ptr": 0xFC00_0000_6000,
                "fault": "UNMAPPED",
            },
        },
    ]


def validate_control_vectors(vectors: list[ControlVector]) -> None:
    names = [vector.name for vector in vectors]
    if len(names) != len(set(names)):
        raise AssertionError("duplicate control vector names")
    expected_ids = {
        "br.n_riii_rd",
        "br.nn_riii_rd",
        "br.z_riii_rd",
        "br.nz_riii_rd",
        "br.p_riii_rd",
        "br.np_riii_rd",
        "br.eq_rrii_rd",
        "br.ne_rrii_rd",
        "br.z_riii_rb",
        "br.nz_riii_rb",
        "jump_iiii_rb",
        "jump_rrii_rb",
        "call_iiii_ra",
        "call_rrii_ra",
        "ret_riii_ra",
    }
    covered = {vector.instruction_id for vector in vectors if vector.coverage}
    if covered != expected_ids:
        raise AssertionError(f"control coverage mismatch: {covered ^ expected_ids}")
    if not any(
        vector.instruction_id.endswith("_rb")
        and vector.expected.read0_addr == 0
        for vector in vectors
    ):
        raise AssertionError("missing rb0 special-address control vector")
    if not any(
        vector.expected.is_call
        and vector.expected.call_return_address
        == (vector.current_rb0 + 4) & MASK48
        for vector in vectors
    ):
        raise AssertionError("missing call return-address coverage")
    if not any(
        vector.expected.is_ret
        and vector.expected.next_rb0 >> 48 == 0
        and vector.expected.next_rb0 == vector.popped_return_address
        for vector in vectors
    ):
        raise AssertionError("missing zero-extended ret return coverage")


def validate_cfx_vectors(vectors: list[dict]) -> None:
    required = {
        "cfx2rd",
        "cfx2rc",
        "trap",
        "trap_escape",
        "cfxperm",
        "cfxreg",
        "illi",
        "cfxesc",
    }
    categories = {vector["category"] for vector in vectors}
    if categories != required:
        raise AssertionError(f"CFX category mismatch: {categories ^ required}")
    for vector in vectors:
        steps = vector["steps"]
        if not steps:
            raise AssertionError(f"CFX vector has no steps: {vector['name']}")
        for step in steps:
            if step["expected_next_ip"] % 4 != 0:
                raise AssertionError(f"misaligned CFX next IP: {vector['name']}")
            if step["expected_rd_valid"]:
                if step["expected_rd_addr"] == 0:
                    raise AssertionError(f"RD0 write leak: {vector['name']}")
            elif step.get("expected_rd_data", 0) != 0:
                raise AssertionError(f"invalid RD data leak: {vector['name']}")


def validate_ras_vectors(vectors: list[dict]) -> None:
    required = {
        "C1-push-empty",
        "C2-recursive-fold",
        "C3a-push-new",
        "C3b-spill-oldest",
        "D1-cold-underflow",
        "D2-recursive-decrement",
        "D3-normal-pop",
        "D4a-zero-top-count",
        "D4b-restore-single",
        "D4b-restore-many",
        "D4b-zero-count-rasuf",
        "D4b-memory-read-fault",
    }
    names = {vector["name"] for vector in vectors}
    if names != required:
        raise AssertionError(f"RAS scenario mismatch: {names ^ required}")


def hex64(value: int) -> str:
    return f"0x{value & MASK64:016x}"


def control_payload(vector: ControlVector) -> dict:
    expected = vector.expected
    return {
        "kind": "control",
        "name": vector.name,
        "instruction_id": vector.instruction_index,
        "instruction": vector.instruction_id,
        "word": f"0x{vector.word:08x}",
        "coverage": vector.coverage,
        "category": vector.category,
        "current_rb0": hex64(vector.current_rb0),
        "read0_value": hex64(vector.read0_value),
        "read1_value": hex64(vector.read1_value),
        "popped_return_address": f"0x{vector.popped_return_address:012x}",
        "expected": {
            "is_control": expected.is_control,
            "is_branch": expected.is_branch,
            "is_jump": expected.is_jump,
            "is_call": expected.is_call,
            "is_ret": expected.is_ret,
            "taken": expected.taken,
            "target": hex64(expected.target),
            "next_rb0": hex64(expected.next_rb0),
            "call_return_address": f"0x{expected.call_return_address:012x}",
            "ret_rd_write": expected.ret_rd_write,
            "ret_rd_addr": expected.ret_rd_addr,
            "ret_rd_value": hex64(expected.ret_rd_value),
            "read0_bank": expected.read0_bank,
            "read0_addr": expected.read0_addr,
            "read1_bank": expected.read1_bank,
            "read1_addr": expected.read1_addr,
        },
    }


def normalize_ras_vectors(vectors: list[dict]) -> list[dict]:
    result: list[dict] = []
    address_a = 0xFC00_0000_0100
    address_b = 0xFC00_0000_0200
    oldest = 0xFC00_0000_0100
    for vector in vectors:
        name = vector["name"]
        initial = vector["initial"]
        request = vector["request"]
        expected = vector["expected"]
        mr_ptr = int(initial.get("mr_ptr", 0))
        top_count = int(initial.get("top_count", 0))
        top_addr = (
            address_a
            if name in {"C2-recursive-fold", "D2-recursive-decrement"}
            else address_b
            if name == "D3-normal-pop"
            else address_a
            if name == "C3a-push-new"
            else 0
        )
        next_top_count = 1 if name == "D3-normal-pop" else 0
        next_top_addr = address_a if name == "D3-normal-pop" else 0
        if name == "C3a-push-new":
            next_top_count = 1
            next_top_addr = address_a

        response_names = {
            "C3b-spill-oldest",
            "D4b-restore-single",
            "D4b-restore-many",
            "D4b-zero-count-rasuf",
            "D4b-memory-read-fault",
        }
        response_valid = name in response_names
        response_count = int(initial.get("restore_count", 0))
        response_fault_name = initial.get("memory_fault", "")
        response_fault = bool(response_fault_name)
        fault_map = {
            "none": 0,
            "RASOF": 0x8A,
            "RASUF": 0x8B,
            "UNMAPPED": 0x87,
        }
        expected_fault_name = expected.get("fault", "none")
        expected_top_count = int(expected.get("top_count", top_count))
        expected_top_addr = (
            address_a
            if name in {"C1-push-empty", "C2-recursive-fold", "D2-recursive-decrement", "D3-normal-pop"}
            else address_b
            if name == "C3a-push-new"
            else address_a
            if name == "D4b-restore-many"
            else int(request.get("address", 0))
            if name == "C3b-spill-oldest"
            else 0
        )
        mem_req = name in response_names
        result.append(
            {
                "kind": "ras",
                "name": name,
                "initial_ra_cnt": int(initial.get("ra_cnt", 0)),
                "initial_mr_ptr": mr_ptr,
                "initial_top_count": top_count,
                "initial_top_addr": top_addr,
                "initial_next_top_count": next_top_count,
                "initial_next_top_addr": next_top_addr,
                "initial_oldest_addr": oldest if name == "C3b-spill-oldest" else 0,
                "request_push": bool(request["push"]),
                "request_pop": bool(request["pop"]),
                "request_addr": int(request.get("address", 0)),
                "response_valid": response_valid,
                "response_count": response_count,
                "response_address": address_a,
                "response_fault": response_fault,
                "response_fault_code": fault_map.get(response_fault_name, 0),
                "expected_done": True,
                "expected_fault_code": fault_map[expected_fault_name],
                "expected_ra_cnt": int(expected.get("ra_cnt", initial.get("ra_cnt", 0))),
                "expected_mr_ptr": int(expected.get("mr_ptr", mr_ptr)),
                "expected_top_count": expected_top_count,
                "expected_top_addr": expected_top_addr,
                "expected_mem_req_valid": mem_req,
                "expected_mem_req_write": name == "C3b-spill-oldest",
                "expected_mem_req_addr": mr_ptr - 8
                if name == "C3b-spill-oldest"
                else mr_ptr,
            }
        )
    return result


def emit_yaml(
    path: Path,
    control: list[ControlVector],
    cfx: list[dict],
    ras: list[dict],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "task": "RTL-011t",
            "generator": "tools/rtl/check_dadao_control_oracle.py",
            "immutable_during_test": True,
        },
        "control": [control_payload(vector) for vector in control],
        "cfx": cfx,
        "ras": normalize_ras_vectors(ras),
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def emit_scala(
    path: Path,
    control_vectors: list[ControlVector],
    cfx_vectors: list[dict],
    ras_vectors: list[dict],
) -> None:
    lines = [
        "package dadao",
        "",
        "// Generated by tools/rtl/check_dadao_control_oracle.py.",
        "private[dadao] final case class DADAOControlOracleVector(",
        "    name: String,",
        "    instructionId: Int,",
        "    word: BigInt,",
        "    coverage: Boolean,",
        "    category: String,",
        "    currentRb0: BigInt,",
        "    read0Value: BigInt,",
        "    read1Value: BigInt,",
        "    poppedReturnAddress: BigInt,",
        "    expectedIsControl: Boolean,",
        "    expectedIsBranch: Boolean,",
        "    expectedIsJump: Boolean,",
        "    expectedIsCall: Boolean,",
        "    expectedIsRet: Boolean,",
        "    expectedTaken: Boolean,",
        "    expectedTarget: BigInt,",
        "    expectedNextRb0: BigInt,",
        "    expectedCallReturnAddress: BigInt,",
        "    expectedRetRdWrite: Boolean,",
        "    expectedRetRdAddr: Int,",
        "    expectedRetRdValue: BigInt,",
        "    expectedRead0Bank: Int,",
        "    expectedRead0Addr: Int,",
        "    expectedRead1Bank: Int,",
        "    expectedRead1Addr: Int",
        ")",
        "",
        "private[dadao] object DADAOControlOracleTable {",
        "  val vectors: Seq[DADAOControlOracleVector] = Seq(",
    ]
    for vector in control_vectors:
        expected = vector.expected
        values = [
            f'      "{vector.name}",',
            f"      {vector.instruction_index},",
            f'      BigInt("{vector.word:08x}", 16),',
            f"      {str(vector.coverage).lower()},",
            f'      "{vector.category}",',
            f'      BigInt("{vector.current_rb0:016x}", 16),',
            f'      BigInt("{vector.read0_value:016x}", 16),',
            f'      BigInt("{vector.read1_value:016x}", 16),',
            f'      BigInt("{vector.popped_return_address:012x}", 16),',
            f"      {str(expected.is_control).lower()},",
            f"      {str(expected.is_branch).lower()},",
            f"      {str(expected.is_jump).lower()},",
            f"      {str(expected.is_call).lower()},",
            f"      {str(expected.is_ret).lower()},",
            f"      {str(expected.taken).lower()},",
            f'      BigInt("{expected.target:016x}", 16),',
            f'      BigInt("{expected.next_rb0:016x}", 16),',
            f'      BigInt("{expected.call_return_address:012x}", 16),',
            f"      {str(expected.ret_rd_write).lower()},",
            f"      {expected.ret_rd_addr},",
            f'      BigInt("{expected.ret_rd_value:016x}", 16),',
            f"      {expected.read0_bank},",
            f"      {expected.read0_addr},",
            f"      {expected.read1_bank},",
            f"      {expected.read1_addr}",
        ]
        lines.append("    DADAOControlOracleVector(")
        lines.extend(values)
        lines.append("    ),")
    lines.extend(["  )", "}", ""])
    lines.extend(
        [
            "private[dadao] final case class DADAOCfxOracleRegisterWrite(",
            "    cfxha: Int,",
            "    cg: Int,",
            "    rc: Int,",
            "    data: BigInt",
            ")",
            "",
            "private[dadao] final case class DADAOCfxOracleStep(",
            "    op: String,",
            "    cfxha: Int,",
            "    cg: Int,",
            "    rc: Int,",
            "    rd: Int,",
            "    rdValue: BigInt,",
            "    immediate: BigInt,",
            "    currentIp: BigInt,",
            "    expectedNextIp: BigInt,",
            "    expectedRdValid: Boolean,",
            "    expectedRdAddr: Int,",
            "    expectedRdData: BigInt",
            ")",
            "",
            "private[dadao] final case class DADAOCfxOracleExpected(",
            "    runMode: Int,",
            "    cfxCode: Int,",
            "    cfxMask: BigInt,",
            "    causeId: BigInt,",
            "    causeIp: BigInt,",
            "    trapNum: BigInt,",
            "    syncNum: BigInt,",
            "    escapeNum: BigInt,",
            "    hmonGlobalMask: BigInt",
            ")",
            "",
            "private[dadao] final case class DADAOCfxOracleVector(",
            "    name: String,",
            "    initialMode: Int,",
            "    initialCfx: Int,",
            "    initialMask: BigInt,",
            "    registerWrites: Seq[DADAOCfxOracleRegisterWrite],",
            "    steps: Seq[DADAOCfxOracleStep],",
            "    expected: DADAOCfxOracleExpected",
            ")",
            "",
            "private[dadao] object DADAOCfxOracleTable {",
            "  val vectors: Seq[DADAOCfxOracleVector] = Seq(",
        ]
    )
    for vector in cfx_vectors:
        expected = vector["expected"]
        writes = vector.get("register_writes", [])
        write_items = ", ".join(
            "DADAOCfxOracleRegisterWrite("
            f"{write[0]}, {write[1]}, {write[2]}, "
            f'BigInt("{write[3]:016x}", 16))'
            for write in writes
        )
        step_items = ", ".join(
            "DADAOCfxOracleStep("
            f'"{step["op"]}", '
            f'{step.get("cfxha", 0)}, '
            f'{step.get("cg", 0)}, '
            f'{step.get("rc", 0)}, '
            f'{step.get("rd", 0)}, '
            f'BigInt("{step.get("rd_value", 0):016x}", 16), '
            f'BigInt("{step.get("immediate", 0):05x}", 16), '
            f'BigInt("{step["current_ip"]:016x}", 16), '
            f'BigInt("{step["expected_next_ip"]:016x}", 16), '
            f'{str(step["expected_rd_valid"]).lower()}, '
            f'{step.get("expected_rd_addr", step.get("rd", 0))}, '
            f'BigInt("{step.get("expected_rd_data", 0):016x}", 16))'
            for step in vector["steps"]
        )
        lines.extend(
            [
                "    DADAOCfxOracleVector(",
                f'      "{vector["name"]}",',
                f'      {vector["initial_mode"]},',
                f'      {vector["initial_cfx"]},',
                f'      BigInt("{vector["initial_mask"]:016x}", 16),',
                f"      Seq({write_items}),",
                f"      Seq({step_items}),",
                "      DADAOCfxOracleExpected(",
                f'        {expected["mode"]},',
                f'        {expected["cfx"]},',
                f'        BigInt("{expected.get("mask", vector["initial_mask"]):016x}", 16),',
                f'        BigInt("{expected.get("cause", 0):016x}", 16),',
                f'        BigInt("{expected.get("cause_ip", 0):016x}", 16),',
                f'        BigInt("{expected["trap_num"]:016x}", 16),',
                f'        BigInt("{expected["sync_num"]:016x}", 16),',
                f'        BigInt("{expected["escape_num"]:016x}", 16),',
                f'        BigInt("{expected["hmon_global_mask"]:016x}", 16)',
                "      )",
                "    ),",
            ]
        )
    lines.extend(["  )", "}", ""])
    lines.extend(
        [
            "private[dadao] final case class DADAORasOracleVector(",
            "    name: String,",
            "    initialRaCnt: Int,",
            "    initialMrPtr: BigInt,",
            "    initialTopCount: Int,",
            "    initialTopAddr: BigInt,",
            "    initialNextTopCount: Int,",
            "    initialNextTopAddr: BigInt,",
            "    initialOldestAddr: BigInt,",
            "    requestPush: Boolean,",
            "    requestPop: Boolean,",
            "    requestAddr: BigInt,",
            "    responseValid: Boolean,",
            "    responseCount: Int,",
            "    responseAddress: BigInt,",
            "    responseFault: Boolean,",
            "    responseFaultCode: Int,",
            "    expectedDone: Boolean,",
            "    expectedFaultCode: Int,",
            "    expectedRaCnt: Int,",
            "    expectedMrPtr: BigInt,",
            "    expectedTopCount: Int,",
            "    expectedTopAddr: BigInt,",
            "    expectedMemReqValid: Boolean,",
            "    expectedMemReqWrite: Boolean,",
            "    expectedMemReqAddr: BigInt",
            ")",
            "",
            "private[dadao] object DADAORasOracleTable {",
            "  val vectors: Seq[DADAORasOracleVector] = Seq(",
        ]
    )
    for vector in normalize_ras_vectors(ras_vectors):
        values = [
            f'      "{vector["name"]}",',
            f'      {vector["initial_ra_cnt"]},',
            f'      BigInt("{vector["initial_mr_ptr"]:012x}", 16),',
            f'      {vector["initial_top_count"]},',
            f'      BigInt("{vector["initial_top_addr"]:012x}", 16),',
            f'      {vector["initial_next_top_count"]},',
            f'      BigInt("{vector["initial_next_top_addr"]:012x}", 16),',
            f'      BigInt("{vector["initial_oldest_addr"]:012x}", 16),',
            f'      {str(vector["request_push"]).lower()},',
            f'      {str(vector["request_pop"]).lower()},',
            f'      BigInt("{vector["request_addr"]:012x}", 16),',
            f'      {str(vector["response_valid"]).lower()},',
            f'      {vector["response_count"]},',
            f'      BigInt("{vector["response_address"]:012x}", 16),',
            f'      {str(vector["response_fault"]).lower()},',
            f'      {vector["response_fault_code"]},',
            f'      {str(vector["expected_done"]).lower()},',
            f'      {vector["expected_fault_code"]},',
            f'      {vector["expected_ra_cnt"]},',
            f'      BigInt("{vector["expected_mr_ptr"]:012x}", 16),',
            f'      {vector["expected_top_count"]},',
            f'      BigInt("{vector["expected_top_addr"]:012x}", 16),',
            f'      {str(vector["expected_mem_req_valid"]).lower()},',
            f'      {str(vector["expected_mem_req_write"]).lower()},',
            f'      BigInt("{vector["expected_mem_req_addr"]:012x}", 16)',
        ]
        lines.append("    DADAORasOracleVector(")
        lines.extend(values)
        lines.append("    ),")
    lines.extend(["  )", "}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def corrupt(
    control: list[ControlVector],
    cfx: list[dict],
    ras: list[dict],
    failure_mode: str,
) -> None:
    if failure_mode == "taken":
        first = control[0]
        control[0] = replace(
            first,
            expected=replace(first.expected, taken=not first.expected.taken),
        )
    elif failure_mode == "return-address":
        first = next(vector for vector in control if vector.expected.is_call)
        index = control.index(first)
        control[index] = replace(
            first,
            expected=replace(
                first.expected,
                call_return_address=(first.expected.call_return_address + 4) & MASK48,
            ),
        )
    elif failure_mode == "ret-high16":
        first = next(vector for vector in control if vector.expected.is_ret)
        index = control.index(first)
        control[index] = replace(
            first,
            expected=replace(
                first.expected,
                next_rb0=first.expected.next_rb0 | (1 << 48),
            ),
        )
    elif failure_mode == "cfx-permission":
        vector = next(item for item in cfx if item["category"] == "cfxperm")
        vector["expected"]["cause"] = CAUSE_REG
    elif failure_mode == "ras-fault":
        vector = next(item for item in ras if item["name"] == "D1-cold-underflow")
        vector["expected"]["fault"] = "none"
    else:
        raise AssertionError(f"unknown failure mode: {failure_mode}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RTL-011t independent control/CFX/RAS oracle vectors."
    )
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML)
    parser.add_argument("--scala", type=Path, default=DEFAULT_SCALA)
    parser.add_argument(
        "--failure-mode",
        choices=[
            "taken",
            "return-address",
            "ret-high16",
            "cfx-permission",
            "ras-fault",
        ],
    )
    parser.add_argument("--force-failure", action="store_true")
    args = parser.parse_args()

    control = build_control_vectors()
    cfx = build_cfx_vectors()
    ras = build_ras_vectors()
    validate_control_vectors(control)
    validate_cfx_vectors(cfx)
    validate_ras_vectors(ras)

    if args.failure_mode:
        control_copy = copy.deepcopy(control)
        cfx_copy = copy.deepcopy(cfx)
        ras_copy = copy.deepcopy(ras)
        corrupt(control_copy, cfx_copy, ras_copy, args.failure_mode)
        raise AssertionError(f"forced {args.failure_mode} control oracle failure")
    if args.force_failure:
        raise AssertionError("forced control oracle failure")

    emit_yaml(args.yaml, control, cfx, ras)
    emit_scala(args.scala, control, cfx, ras)
    print(f"control_vectors={len(control)}")
    print(f"control_instruction_ids={len({v.instruction_id for v in control})}")
    print(f"cfx_vectors={len(cfx)}")
    print(f"ras_vectors={len(ras)}")
    print(f"yaml={args.yaml}")
    print(f"scala={args.scala}")
    print("CONTROL_ORACLE CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
