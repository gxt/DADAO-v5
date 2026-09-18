#!/usr/bin/env python3
"""Validate DADAOInstrInfo.td against contracts/opcodes.yaml.

Checks:
  1. 178 M1 instruction defs exist (no more, no fewer)
  2. Each def's mnemonic/format/op matches opcodes.yaml
  3. 9 format classes are used (rrrr/rrri/rrii/riii/iiii/rwii/orrr/orri/oiii)
  4. No crrr/crii/ciii format classes defined
  5. rwii wyde-position field is hb[5:4] (bits 17:16 in inst word)
  6. MISC sub-table instructions have 'let ha = 0xNN'
  7. All patterns are []
  8. excluded_m1 instructions are NOT defined
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TD_PATH = ROOT / ".work" / "source" / "llvm-project" / "llvm" / "lib" / "Target" / "DADAO" / "DADAOInstrInfo.td"
YAML_PATH = ROOT / "contracts" / "opcodes.yaml"
FORMATS_TD = ROOT / ".work" / "source" / "llvm-project" / "llvm" / "lib" / "Target" / "DADAO" / "DADAOInstrFormats.td"


def parse_format_class_blocks(formats_src: str) -> dict[str, str]:
    """Parse DADAOInstrFormats.td into {class_name: body_text} blocks.

    Each block is the content between { } of a class definition.
    Only classes starting with 'DADAO' are returned.
    """
    blocks = {}
    class_pat = re.compile(r'^class\s+(DADAO\w+)\s*<[^>]*>\s*(?::\s*\w+\s*<[^>]*>)?\s*\{', re.MULTILINE)
    for m in class_pat.finditer(formats_src):
        cls_name = m.group(1)
        start = m.end()
        depth = 1
        pos = start
        while pos < len(formats_src) and depth > 0:
            if formats_src[pos] == '{':
                depth += 1
            elif formats_src[pos] == '}':
                depth -= 1
            pos += 1
        blocks[cls_name] = formats_src[start:pos-1]
    return blocks


def load_m1_opcodes():
    with open(YAML_PATH) as f:
        opcodes = yaml.safe_load(f)
    return [op for op in opcodes if not op.get("excluded_m1", False)]


def load_excluded_opcodes():
    with open(YAML_PATH) as f:
        opcodes = yaml.safe_load(f)
    return [op for op in opcodes if op.get("excluded_m1", False)]


def parse_td_defs(td_content: str) -> dict:
    """Parse instruction defs from DADAOInstrInfo.td."""
    defs = {}
    # Match: def NAME : CLASS<...> { ... }
    pattern = re.compile(
        r'^def (\w+) : (DADAO\w+)<([^>]+)>\s*\{([^}]*)\}',
        re.MULTILINE | re.DOTALL
    )
    for m in pattern.finditer(td_content):
        name = m.group(1)
        classname = m.group(2)
        params = m.group(3)
        body = m.group(4)

        if not classname.startswith("DADAO"):
            continue
        # Skip Operand defs
        if classname == "Operand":
            continue

        # Extract op value
        op_match = re.search(r'let op = (0x[0-9A-Fa-f]+)', body)
        op_val = op_match.group(1) if op_match else None

        # Extract ha value
        ha_match = re.search(r'let ha = (0x[0-9A-Fa-f]+)', body)
        ha_val = ha_match.group(1) if ha_match else None

        # Extract format from class name
        fmt_map = {
            "DADAORrrr": "rrrr", "DADAORrri": "rrri", "DADAORrii": "rrii",
            "DADAORiii": "riii", "DADAOIiii": "iiii", "DADAORwii": "rwii",
            "DADAOOrrr": "orrr", "DADAOOrri": "orri", "DADAOOiii": "oiii",
        }
        fmt = fmt_map.get(classname)

        # Extract mnemonic from params
        mn_match = re.search(r'"([^"]+)"', params)
        mnemonic = mn_match.group(1) if mn_match else None

        defs[name] = {
            "class": classname,
            "format": fmt,
            "mnemonic": mnemonic,
            "op": op_val,
            "ha": ha_val,
        }

    return defs


def main() -> int:
    errors = 0
    warnings = 0

    # Load data
    m1_opcodes = load_m1_opcodes()
    excluded = load_excluded_opcodes()
    td_content = TD_PATH.read_text()
    defs = parse_td_defs(td_content)

    print(f"=== Validation: DADAOInstrInfo.td vs opcodes.yaml ===")
    print(f"M1 opcodes in YAML: {len(m1_opcodes)}")
    print(f"Excluded opcodes in YAML: {len(excluded)}")
    print(f"Defs in TD: {len(defs)}")
    print()

    # Check 1: def count
    if len(defs) != 178:
        print(f"FAIL: Expected 178 defs, got {len(defs)}")
        errors += 1
    else:
        print(f"PASS: 178 instruction defs")

    # Check 2: Build lookup from YAML (insn -> op)
    yaml_by_insn = {op["insn"]: op for op in m1_opcodes}

    # Check 3: Each YAML M1 instruction has a matching def
    # Some insn names appear twice (ext.uo in orrr and orri); disambiguate with format
    name_count: dict[str, int] = {}
    for op in m1_opcodes:
        base = op["insn"].replace(".", "_").replace("-", "_")
        name_count[base] = name_count.get(base, 0) + 1

    for op in m1_opcodes:
        base = op["insn"].replace(".", "_").replace("-", "_")
        if name_count[base] > 1:
            defname = f"{base}_{op['format']}"
        else:
            defname = base
        if defname not in defs:
            print(f"FAIL: Missing def for {op['insn']} (expected {defname})")
            errors += 1
            continue

        td_def = defs[defname]

        # Check mnemonic
        if td_def["mnemonic"] != op["mnemonic"]:
            print(f"FAIL: {defname}: mnemonic mismatch: TD={td_def['mnemonic']}, YAML={op['mnemonic']}")
            errors += 1

        # Check format
        if td_def["format"] != op["format"]:
            print(f"FAIL: {defname}: format mismatch: TD={td_def['format']}, YAML={op['format']}")
            errors += 1

        # Check op value
        yaml_op = op["op"].lower()
        td_op = td_def["op"].lower() if td_def["op"] else None
        if td_op != yaml_op:
            print(f"FAIL: {defname}: op mismatch: TD={td_op}, YAML={yaml_op}")
            errors += 1

        # Check ha value for MISC instructions
        if "ha" in op:
            yaml_ha = op["ha"].lower()
            td_ha = td_def["ha"].lower() if td_def["ha"] else None
            if td_ha != yaml_ha:
                print(f"FAIL: {defname}: ha mismatch: TD={td_ha}, YAML={yaml_ha}")
                errors += 1

    # Check 4: No excluded instructions are defined
    for op in excluded:
        base = op["insn"].replace(".", "_").replace("-", "_")
        # Check both the base name and format-disambiguated name
        if base in defs:
            print(f"FAIL: Excluded instruction {op['insn']} has a def ({base})")
            errors += 1
        fmt_name = f"{base}_{op['format']}"
        if fmt_name in defs:
            print(f"FAIL: Excluded instruction {op['insn']} has a def ({fmt_name})")
            errors += 1

    # Check 5: Format classes used
    formats_used = set()
    for d in defs.values():
        if d["format"]:
            formats_used.add(d["format"])
    expected_formats = {"rrrr", "rrri", "rrii", "riii", "iiii", "rwii", "orrr", "orri", "oiii"}
    if formats_used != expected_formats:
        missing = expected_formats - formats_used
        extra = formats_used - expected_formats
        if missing:
            print(f"FAIL: Missing format classes: {missing}")
            errors += 1
        if extra:
            print(f"FAIL: Unexpected format classes: {extra}")
            errors += 1
    else:
        print(f"PASS: All 9 format classes used: {sorted(formats_used)}")

    # Check 6: No crrr/crii/ciii classes
    formats_td = FORMATS_TD.read_text()
    for forbidden in ["DADAOCrrr", "DADAOCrii", "DADAOCiii"]:
        if forbidden in formats_td:
            print(f"FAIL: Forbidden format class {forbidden} found in DADAOInstrFormats.td")
            errors += 1
    if not any(f in formats_td for f in ["DADAOCrrr", "DADAOCrii", "DADAOCiii"]):
        print(f"PASS: No crrr/crii/ciii format classes")

    # Check 7: Pattern = [] for all defs
    pattern_count = td_content.count("let Pattern = [];")
    if pattern_count != 178:
        print(f"FAIL: Expected 178 'let Pattern = [];', found {pattern_count}")
        errors += 1
    else:
        print(f"PASS: All 178 defs have Pattern = []")

    # Check 8: Bit field bindings in format classes (strengthened — per-class block parsing)
    # Parse DADAOInstrFormats.td into per-class blocks and verify each one
    # declares correct bits<> fields and Inst bindings.

    fmt_classes_spec = {
        "DADAORrrr": {
            "bits": {"ra": 6, "rb": 6, "rc": 6, "rd": 6},
            "bindings": {"ha": "ra", "hb": "rb", "hc": "rc", "hd": "rd"},
        },
        "DADAORrri": {
            "bits": {"ra": 6, "rb": 6, "rc": 6, "imm6": 6},
            "bindings": {"ha": "ra", "hb": "rb", "hc": "rc", "hd": "imm6"},
        },
        "DADAORrii": {
            "bits": {"ra": 6, "rb": 6, "imm12": 12},
            "bindings": {"ha": "ra", "hb": "rb", "hc": "imm12{11-6}", "hd": "imm12{5-0}"},
        },
        "DADAORiii": {
            "bits": {"ra": 6, "imm18": 18},
            "bindings": {"ha": "ra", "hb": "imm18{17-12}", "hc": "imm18{11-6}", "hd": "imm18{5-0}"},
        },
        "DADAOIiii": {
            "bits": {"imm24": 24},
            "bindings": {"ha": "imm24{23-18}", "hb": "imm24{17-12}", "hc": "imm24{11-6}", "hd": "imm24{5-0}"},
        },
        "DADAORwii": {
            "bits": {"ra": 6, "wp": 2, "imm16": 16},
            "bindings": {"ha": "ra", "hb{5-4}": "wp", "hb{3-0}": "imm16{15-12}", "hc": "imm16{11-6}", "hd": "imm16{5-0}"},
        },
        "DADAOOrrr": {
            "bits": {"rb": 6, "rc": 6, "rd": 6},
            "bindings": {"hb": "rb", "hc": "rc", "hd": "rd"},
        },
        "DADAOOrri": {
            "bits": {"rb": 6, "rc": 6, "imm6": 6},
            "bindings": {"hb": "rb", "hc": "rc", "hd": "imm6"},
        },
        "DADAOOiii": {
            "bits": {"imm18": 18},
            "bindings": {"hb": "imm18{17-12}", "hc": "imm18{11-6}", "hd": "imm18{5-0}"},
        },
    }

    class_blocks = parse_format_class_blocks(formats_td)
    all_fmt_checks_ok = True

    for cls_name, spec in fmt_classes_spec.items():
        if cls_name not in class_blocks:
            print(f"FAIL: Format class {cls_name} not found in DADAOInstrFormats.td")
            errors += 1
            all_fmt_checks_ok = False
            continue

        body = class_blocks[cls_name]

        # 8a: Check bits<> field declarations
        for field_name, width in spec["bits"].items():
            bits_pat = rf'bits<\s*{width}\s*>\s+{re.escape(field_name)}\s*;'
            if not re.search(bits_pat, body):
                print(f"FAIL: {cls_name}: missing declaration 'bits<{width}> {field_name};'")
                errors += 1
                all_fmt_checks_ok = False

        # 8b: Check let bindings to Inst positions
        for lhs, rhs in spec["bindings"].items():
            # For sub-bit-field bindings like hb{5-4}, use exact pattern
            let_pat = rf'let\s+{re.escape(lhs)}\s*=\s*{re.escape(rhs)}\s*;'
            if not re.search(let_pat, body):
                print(f"FAIL: {cls_name}: missing binding 'let {lhs} = {rhs};'")
                errors += 1
                all_fmt_checks_ok = False

    if all_fmt_checks_ok:
        print(f"PASS: All 9 format classes have correct bits<> declarations and Inst bindings")

    # Check 9: No AsmParser/Disassembler implementations
    dadao_dir = TD_PATH.parent
    if (dadao_dir / "DADAOAsmParser.cpp").exists():
        print(f"FAIL: DADAOAsmParser.cpp should not exist yet")
        errors += 1
    else:
        print(f"PASS: No AsmParser implementation")

    if (dadao_dir / "DADAODisassembler.cpp").exists():
        print(f"FAIL: DADAODisassembler.cpp should not exist yet")
        errors += 1
    else:
        print(f"PASS: No Disassembler implementation")

    # Check 10: Format count breakdown
    fmt_counts: dict[str, int] = {}
    for d in defs.values():
        f = d["format"]
        fmt_counts[f] = fmt_counts.get(f, 0) + 1
    yaml_fmt_counts: dict[str, int] = {}
    for op in m1_opcodes:
        f = op["format"]
        yaml_fmt_counts[f] = yaml_fmt_counts.get(f, 0) + 1

    print(f"\nFormat breakdown (TD vs YAML):")
    all_fmts = sorted(set(list(fmt_counts.keys()) + list(yaml_fmt_counts.keys())))
    for f in all_fmts:
        td_c = fmt_counts.get(f, 0)
        yaml_c = yaml_fmt_counts.get(f, 0)
        status = "OK" if td_c == yaml_c else "MISMATCH"
        print(f"  {f}: TD={td_c}, YAML={yaml_c} [{status}]")
        if td_c != yaml_c:
            errors += 1

    print(f"\n=== Result: {errors} errors, {warnings} warnings ===")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
