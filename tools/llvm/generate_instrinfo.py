#!/usr/bin/env python3
"""Generate DADAOInstrInfo.td from contracts/opcodes.yaml.

Reads the M1 instruction encoding table (opcodes.yaml) and produces:
  1. DADAOInstrInfo.td — Operand classes + 178 M1 instruction defs

Only M1 entries (excluded_m1 absent or false) are emitted. Each instruction
inherits the appropriate format class from DADAOInstrFormats.td and binds
its operands to the format's bits<> fields via `let` statements.

Bit encoding (contract-isa.md §2.1):
  32-bit instruction, big-endian:
    bits[31:24] = op[7:0]    (8 bits)
    bits[23:18] = ha[5:0]    (6 bits)
    bits[17:12] = hb[5:0]    (6 bits)
    bits[11:6]  = hc[5:0]    (6 bits)
    bits[5:0]   = hd[5:0]    (6 bits)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_m1_opcodes():
    """Load M1 opcodes from contracts/opcodes.yaml, filtering excluded."""
    with open(ROOT / "contracts" / "opcodes.yaml") as f:
        opcodes = yaml.safe_load(f)
    return [op for op in opcodes if not op.get("excluded_m1", False)]


def sanitize_name(insn_name: str) -> str:
    """Convert insn name to a valid TableGen def name."""
    return insn_name.replace(".", "_").replace("-", "_")


def make_unique_names(m1_opcodes: list) -> dict[tuple[str, str], str]:
    """Generate unique def names for all M1 opcodes."""
    name_count: dict[str, int] = {}
    for op in m1_opcodes:
        base = sanitize_name(op["insn"])
        name_count[base] = name_count.get(base, 0) + 1

    result: dict[tuple[str, str], str] = {}
    for op in m1_opcodes:
        base = sanitize_name(op["insn"])
        if name_count[base] > 1:
            unique = f"{base}_{op['format']}"
        else:
            unique = base
        result[(op["insn"], op["format"])] = unique

    return result


def get_format_class(fmt: str) -> str:
    """Map format string to TableGen class name."""
    return {
        "rrrr": "DADAORrrr", "rrri": "DADAORrri", "rrii": "DADAORrii",
        "riii": "DADAORiii", "iiii": "DADAOIiii", "rwii": "DADAORwii",
        "orrr": "DADAOOrrr", "orri": "DADAOOrri", "oiii": "DADAOOiii",
    }[fmt]


def get_reg_type(bank: str) -> str:
    """Map register bank to Operand type."""
    return {"rd": "GPRD", "rb": "GPRB", "rf": "GPRF", "ra": "GPRA"}[bank]


def get_operands_and_bindings(op: dict) -> list[dict]:
    """Return ordered list of operand info dicts.

    Each dict: {yaml_name, fmt_name, operand_type, role, is_output}
    yaml_name: the field name from opcodes.yaml (e.g. 'rdha', 'rbhb')
    fmt_name: the format class field name (e.g. 'ra', 'rb', 'imm12')
    operand_type: the Operand class (e.g. 'GPRD', 'imms12')
    role: 'dst', 'src', 'imm', 'wyde_pos'
    is_output: True if dst, False otherwise
    """
    fmt = op["format"]
    fields = op["fields"]
    result = []

    # Determine the format field mapping based on format
    # Each format has fixed positional field names
    fmt_field_idx = 0
    seen_imm = False

    for field in fields:
        name = field["name"]
        role = field["role"]
        bank = field["bank"]

        if role == "minor_op":
            continue
        if role in ("cfxcode", "cfx_cg", "cfx_rc"):
            continue

        if role == "wyde_pos":
            result.append({
                "yaml_name": name, "fmt_name": "wp",
                "operand_type": "wydepos", "role": "wyde_pos",
                "is_output": False,
            })
        elif role == "imm":
            # Only add once per instruction (skip sub-fields like imm12_hi/imm12_lo)
            imm_info = _get_imm_operand(fmt, field, fields)
            if imm_info and not seen_imm:
                seen_imm = True
                result.append({
                    "yaml_name": name, "fmt_name": imm_info["fmt_name"],
                    "operand_type": imm_info["operand_type"], "role": "imm",
                    "is_output": False,
                })
        elif role == "dst":
            fmt_name = _get_reg_field_name(fmt, len([o for o in result if o["role"] in ("dst", "src")]))
            result.append({
                "yaml_name": name, "fmt_name": fmt_name,
                "operand_type": get_reg_type(bank), "role": "dst",
                "is_output": True,
            })
        elif role == "src":
            fmt_name = _get_reg_field_name(fmt, len([o for o in result if o["role"] in ("dst", "src")]))
            result.append({
                "yaml_name": name, "fmt_name": fmt_name,
                "operand_type": get_reg_type(bank), "role": "src",
                "is_output": False,
            })

    return result


def _get_reg_field_name(fmt: str, reg_idx: int) -> str:
    """Get the format field name for the reg_idx-th register operand.

    For formats with minor-op (orrr/orri/oiii), registers start from rb.
    For other formats, registers start from ra.
    """
    if fmt in ("orrr", "orri"):
        # minor-op in ha, registers in hb, hc, (hd for orrr)
        return ["rb", "rc", "rd"][reg_idx]
    elif fmt == "oiii":
        # minor-op in ha, no registers (only imm18)
        return "rb"  # shouldn't be called for oiii with registers
    else:
        # rrrr/rrri/rrii/riii: registers start from ra
        return ["ra", "rb", "rc", "rd"][reg_idx]


def _get_imm_operand(fmt: str, field: dict, all_fields: list) -> dict | None:
    """Determine the immediate operand info, or None if this is a sub-field."""
    name = field["name"]

    if fmt == "rwii":
        return {"fmt_name": "imm16", "operand_type": "immu16"} if name == "immu16_hi" else None
    if fmt == "iiii":
        if name.startswith("imms24") and name == "imms24_b23_18":
            return {"fmt_name": "imm24", "operand_type": "imms24"}
        if name.startswith("immu24") and name == "immu24_b23_18":
            return {"fmt_name": "imm24", "operand_type": "immu24"}
        return None
    if fmt == "riii":
        if name.startswith("imms18") and name == "imms18_hi":
            return {"fmt_name": "imm18", "operand_type": "imms18"}
        if name.startswith("immu18") and name == "immu18_hi":
            return {"fmt_name": "imm18", "operand_type": "immu18"}
        return None
    if fmt == "rrii":
        if name.startswith("imms12") and name == "imms12_hi":
            return {"fmt_name": "imm12", "operand_type": "imms12"}
        if name.startswith("immu12") and name == "immu12_hi":
            return {"fmt_name": "imm12", "operand_type": "immu12"}
        return None
    if fmt in ("rrri", "orri"):
        return {"fmt_name": "imm6", "operand_type": "immu6"} if name == "immu6" else None
    if fmt == "oiii":
        if name.startswith("immu18") and name == "immu18_hi":
            return {"fmt_name": "imm18", "operand_type": "immu18"}
        if name.startswith("imms18") and name == "imms18_hi":
            return {"fmt_name": "imm18", "operand_type": "imms18"}
        return None
    return None


def generate_instrinfo_td(m1_opcodes: list) -> str:
    """Generate DADAOInstrInfo.td content."""
    lines = []
    lines.append("//===-- DADAOInstrInfo.td - DADAO Instruction defs -----*- tablegen -*-===//")
    lines.append("//")
    lines.append("// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.")
    lines.append("// See https://llvm.org/LICENSE.txt for license information.")
    lines.append("// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception")
    lines.append("//")
    lines.append("//===----------------------------------------------------------------------===//")
    lines.append("//")
    lines.append("// DADAO M1 instruction definitions (178 instructions).")
    lines.append("// Auto-generated from contracts/opcodes.yaml by tools/llvm/generate_instrinfo.py.")
    lines.append("// DO NOT EDIT MANUALLY.")
    lines.append("//")
    lines.append("// Each def uses the format class's field names as operand names")
    lines.append("// in OutOperandList/InOperandList (e.g. GPRD:$ra, imms12:$imm12).")
    lines.append("// TableGen automatically binds operand values to the format class's")
    lines.append("// bits<> fields since they share the same name.")
    lines.append("//")
    lines.append("//===----------------------------------------------------------------------===//")
    lines.append("")
    lines.append("include \"DADAOInstrFormats.td\"")
    lines.append("")
    lines.append("//===----------------------------------------------------------------------===//")
    lines.append("// Operand types")
    lines.append("//===----------------------------------------------------------------------===//")
    lines.append("")

    # Operand definitions
    operands = [
        ("imms12", "12-bit signed immediate (rrii: hc[5:0]+hd[5:0])", "DecodeSImm12"),
        ("immu12", "12-bit unsigned immediate (rrii)", "DecodeUImm12"),
        ("imms18", "18-bit signed immediate (riii: hb[5:0]+hc[5:0]+hd[5:0])", "DecodeSImm18"),
        ("immu18", "18-bit unsigned immediate (oiii)", "DecodeUImm18"),
        ("immu16", "16-bit unsigned immediate (rwii: hb[3:0]+hc+hd)", "DecodeUImm16"),
        ("immu6",  "6-bit unsigned immediate (rrri/orri: hd[5:0])", "DecodeUImm6"),
        ("imms24", "24-bit signed immediate (iiii: ha+hb+hc+hd)", "DecodeSImm24"),
        ("immu24", "24-bit unsigned immediate (iiii, swym)", "DecodeUImm24"),
        ("wydepos", "2-bit wyde-position (rwii: hb[5:4])", "DecodeWydePos"),
    ]

    for name, desc, decoder in operands:
        lines.append(f"// {desc}")
        lines.append(f"def {name} : Operand<i64> {{")
        lines.append(f"  let EncoderMethod = \"\";  // LLVM-006t adds")
        lines.append(f"  let DecoderMethod = \"{decoder}\";  // LLVM-008t implements")
        lines.append(f"  let PrintMethod = \"\";")
        lines.append(f"  let MIOperandInfo = (ops);")
        lines.append("}")
        lines.append("")

    lines.append("//===----------------------------------------------------------------------===//")
    lines.append("// M1 instruction definitions (178 total)")
    lines.append("//===----------------------------------------------------------------------===//")
    lines.append("")

    # Group by format for readability
    by_format: dict[str, list] = {}
    for op in m1_opcodes:
        fmt = op["format"]
        by_format.setdefault(fmt, []).append(op)

    unique_names = make_unique_names(m1_opcodes)
    format_order = ["rrii", "rrri", "rrrr", "riii", "iiii", "rwii", "orrr", "orri", "oiii"]

    for fmt in format_order:
        ops = by_format.get(fmt, [])
        if not ops:
            continue
        lines.append(f"// --- {fmt} format ({len(ops)} instructions) ---")
        lines.append("")
        for op in ops:
            defname = unique_names[(op["insn"], op["format"])]
            classname = get_format_class(fmt)

            # Get operand info with format field bindings
            operands_info = get_operands_and_bindings(op)

            # Build OutOperandList and InOperandList using FORMAT field names
            out_ops = []
            in_ops = []
            for oi in operands_info:
                entry = f"{oi['operand_type']}:${oi['fmt_name']}"
                if oi["is_output"]:
                    out_ops.append(entry)
                else:
                    in_ops.append(entry)

            out_str = ", ".join(out_ops) if out_ops else ""
            in_str = ", ".join(in_ops) if in_ops else ""

            # Build the def line
            if fmt in ("rrrr", "rrri", "rrii", "riii", "orrr", "orri"):
                line = f"def {defname} : {classname}<\"{op['mnemonic']}\"> {{"
            else:
                line = f"def {defname} : {classname}<\"{op['mnemonic']}\"> {{"

            lines.append(line)
            lines.append(f"  let OutOperandList = (outs {out_str});")
            lines.append(f"  let InOperandList = (ins {in_str});")

            # Set op value
            op_val = int(op["op"], 16)
            lines.append(f"  let op = 0x{op_val:02X};")

            # For MISC sub-table instructions, set ha (minor-op)
            if "ha" in op:
                ha_val = int(op["ha"], 16)
                lines.append(f"  let ha = 0x{ha_val:02X};")

            # NOTE: No explicit `let ra = rdha;` bindings needed.
            # The operand names in OutOperandList/InOperandList match the format
            # class field names (ra, rb, rc, rd, imm12, etc.), so TableGen
            # automatically binds the operand values to the bits<> fields.

            lines.append("  let Pattern = [];")
            lines.append("}")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    m1_opcodes = load_m1_opcodes()
    print(f"Loaded {len(m1_opcodes)} M1 opcodes")

    by_fmt: dict[str, int] = {}
    for op in m1_opcodes:
        by_fmt[op["format"]] = by_fmt.get(op["format"], 0) + 1
    for fmt, count in sorted(by_fmt.items()):
        print(f"  {fmt}: {count}")

    td_content = generate_instrinfo_td(m1_opcodes)
    out_path = ROOT / ".work" / "source" / "llvm-project" / "llvm" / "lib" / "Target" / "DADAO" / "DADAOInstrInfo.td"
    out_path.write_text(td_content)
    print(f"\nWrote {out_path}")

    instr_defs = len(re.findall(r'^def \w+ : DADAO', td_content, re.MULTILINE))
    print(f"Generated {instr_defs} instruction defs")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
