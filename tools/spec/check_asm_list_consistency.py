#!/usr/bin/env python3
"""Check consistency between spec embedded tables and generator output.

Compares the content between ``<!-- ASSEMBLY_LIST_START -->`` and
``<!-- ASSEMBLY_LIST_END -->`` markers in each ``spec/SimRISC-XX-*.md``
file against the output of ``gen_asm_list.py --embed-spec`` (in-memory).

Exit 0 = all consistent; exit 1 = mismatch found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Reuse the generator's classification and table-building logic.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "llvm"))
from gen_asm_list import (  # noqa: E402
    ASSEMBLY_LIST_END,
    ASSEMBLY_LIST_START,
    CLASS_TO_SPEC,
    SECTION_ORDER,
    classify,
    _section_content,
    operands,
    yaml,
    OPCODES,
)

EXPECTED_START = "<!-- ASSEMBLY_LIST_START -->"
EXPECTED_END = "<!-- ASSEMBLY_LIST_END -->"
SECTION_HEADER = "## 汇编指令速查"


def extract_embedded(spec_text: str) -> str | None:
    """Extract the content between markers (excluding the markers themselves)."""
    m = re.search(
        rf"^{re.escape(EXPECTED_START)}\n(.*?)\n{re.escape(EXPECTED_END)}$",
        spec_text,
        re.MULTILINE | re.DOTALL,
    )
    return m.group(1) if m else None


def main() -> int:
    entries = yaml.safe_load(OPCODES.read_text())

    by_class: dict[str, list] = {}
    for entry in entries:
        by_class.setdefault(classify(entry), []).append(entry)

    errors: list[str] = []
    checked = 0

    for cls in SECTION_ORDER:
        if cls not in CLASS_TO_SPEC:
            continue
        spec_path = ROOT / CLASS_TO_SPEC[cls]
        if not spec_path.exists():
            errors.append(f"{cls}: spec file not found: {spec_path}")
            continue

        spec_text = spec_path.read_text(encoding="utf-8")
        embedded = extract_embedded(spec_text)
        if embedded is None:
            errors.append(f"{cls}: no ASSEMBLY_LIST markers in {spec_path.name}")
            continue

        # Build expected content: "## 汇编指令速查\n\n" + table
        expected = f"{SECTION_HEADER}\n\n{_section_content(cls, by_class.get(cls, []))}".rstrip("\n")

        if embedded.rstrip("\n") != expected:
            errors.append(
                f"{cls}: content mismatch in {spec_path.name}\n"
                f"  expected {len(expected.splitlines())} lines, "
                f"got {len(embedded.splitlines())} lines"
            )
        else:
            checked += 1

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        print(f"\n{len(errors)} inconsistency(ies) found, {checked} OK", file=sys.stderr)
        return 1

    print(f"check-asm-list-consistency: {checked} spec files OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
