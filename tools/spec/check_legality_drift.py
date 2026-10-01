#!/usr/bin/env python3
"""Drift gate: verify LEGALITY sections in spec/SimRISC-01..12 match expected content.

Reuses ``render_chapter_legality()`` from ``gen_legality_list.py`` (DRY).
Performs **exact whole-block comparison** (not substring match).

Exit 0 = all consistent; exit 1 = any drift / structural violation.

Checks
------
1. SimRISC-01..12 each contain exactly one ``LEGALITY_START/END`` pair.
2. SimRISC-00 must NOT contain ``LEGALITY_START/END``.
3. ``LEGALITY_START`` must immediately follow ``ASSEMBLY_LIST_END`` (one blank line gap OK).
4. Content between markers must exactly match the expected block
   (rendered from ``contracts/`` via ``gen_legality_list.render_chapter_legality``).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.spec.gen_legality_list import (  # noqa: E402
    CLASS_TO_SPEC,
    LEGALITY_END,
    LEGALITY_START,
    SECTION_ORDER,
    build_chapter_entries,
    build_rule_entries,
    build_rule_to_chapters,
    classify,
    load_data,
    render_chapter_legality,
)

# Chapters that MUST have exactly one LEGALITY section
REQUIRED_CHAPTERS = [cls for cls in SECTION_ORDER if cls in CLASS_TO_SPEC]

# Chapter that MUST NOT have a LEGALITY section
FORBIDDEN_CHAPTER = "指令系统设计"  # SimRISC-00


def count_markers(text: str, marker: str) -> int:
    """Count exact occurrences of a marker line in text."""
    return sum(1 for line in text.splitlines() if line.strip() == marker)


def extract_block(text: str) -> str | None:
    """Extract content between LEGALITY_START and LEGALITY_END (inclusive of markers)."""
    lines = text.splitlines()
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == LEGALITY_START:
            start_idx = i
        elif line.strip() == LEGALITY_END and start_idx is not None:
            end_idx = i
            break
    if start_idx is not None and end_idx is not None:
        return "\n".join(lines[start_idx : end_idx + 1])
    return None


def check_proximity(spec_text: str) -> str | None:
    """Check that LEGALITY_START is near ASSEMBLY_LIST_END.

    Returns error message if violated, None if OK.
    Accepts 0-2 blank lines between ASSEMBLY_LIST_END and LEGALITY_START.
    """
    lines = spec_text.splitlines()
    asm_end_idx = None
    legality_start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "<!-- ASSEMBLY_LIST_END -->":
            asm_end_idx = i
        if line.strip() == LEGALITY_START:
            legality_start_idx = i
    if asm_end_idx is None or legality_start_idx is None:
        return None  # Not applicable
    gap = legality_start_idx - asm_end_idx
    if gap < 1 or gap > 3:
        return (
            f"LEGALITY_START at line {legality_start_idx + 1} is {gap} lines "
            f"after ASSEMBLY_LIST_END (line {asm_end_idx + 1}); expected 1-3"
        )
    return None


def main() -> int:
    entries, rules = load_data()
    rule_to_chapters = build_rule_to_chapters(entries)
    chapter_entries = build_chapter_entries(entries)
    rule_entries_map = build_rule_entries(entries)

    errors: list[str] = []
    checked = 0

    # --- Check 1: SimRISC-00 must NOT have LEGALITY markers ---
    spec00_path = ROOT / "spec" / "SimRISC-00-指令系统设计.md"
    if spec00_path.exists():
        text00 = spec00_path.read_text(encoding="utf-8")
        cnt_start = count_markers(text00, LEGALITY_START)
        cnt_end = count_markers(text00, LEGALITY_END)
        if cnt_start > 0 or cnt_end > 0:
            errors.append(
                f"SimRISC-00: forbidden LEGALITY markers found "
                f"(START={cnt_start}, END={cnt_end})"
            )

    # --- Check 2-4: SimRISC-01..12 ---
    for cls in REQUIRED_CHAPTERS:
        spec_rel = CLASS_TO_SPEC[cls]
        spec_path = ROOT / spec_rel
        if not spec_path.exists():
            errors.append(f"{cls}: spec file not found: {spec_path}")
            continue

        spec_text = spec_path.read_text(encoding="utf-8")

        # 2a: exactly one START and one END
        cnt_start = count_markers(spec_text, LEGALITY_START)
        cnt_end = count_markers(spec_text, LEGALITY_END)
        if cnt_start != 1 or cnt_end != 1:
            errors.append(
                f"{cls} ({spec_path.name}): expected exactly 1 LEGALITY "
                f"START+END pair, found START={cnt_start} END={cnt_end}"
            )
            continue  # Can't do content check if markers are wrong

        # 2b: proximity check
        proximity_err = check_proximity(spec_text)
        if proximity_err:
            errors.append(f"{cls} ({spec_path.name}): {proximity_err}")

        # 3: content comparison
        actual_block = extract_block(spec_text)
        if actual_block is None:
            errors.append(f"{cls} ({spec_path.name}): could not extract LEGALITY block")
            continue

        ents = chapter_entries.get(cls, [])
        expected_block = render_chapter_legality(
            cls, ents, rules, rule_to_chapters, rule_entries_map
        )

        if actual_block != expected_block:
            # Find first differing line
            actual_lines = actual_block.splitlines()
            expected_lines = expected_block.splitlines()
            first_diff = None
            for i, (a, e) in enumerate(zip(actual_lines, expected_lines)):
                if a != e:
                    first_diff = i + 1
                    break
            if first_diff is None:
                first_diff = min(len(actual_lines), len(expected_lines)) + 1
            errors.append(
                f"{cls} ({spec_path.name}): LEGALITY content drift "
                f"(first diff at line {first_diff}, "
                f"expected {len(expected_lines)} lines, "
                f"got {len(actual_lines)} lines)"
            )
        else:
            checked += 1

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        print(f"\n{len(errors)} violation(s) found, {checked} OK", file=sys.stderr)
        return 1

    print(f"check-legality-drift: {checked} chapters OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
