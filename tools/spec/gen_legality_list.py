#!/usr/bin/env python3
"""Generate legality checklist sections for spec/SimRISC-01~12.

Sources
-------
* ``contracts/legality_rules.yaml`` -- 15 rules (active + deferred)
* ``contracts/opcodes.yaml`` -- 228 entries, 191 with ``rule_refs``

Reuses ``classify()``, ``SECTION_ORDER``, ``CLASS_TO_SPEC`` from
``tools/llvm/gen_asm_list.py`` (DRY: no duplicated classification logic).

Usage
-----
* Dry-run (print only):  ``python3 tools/spec/gen_legality_list.py --dry-run``
* Apply (write files):   ``python3 tools/spec/gen_legality_list.py --apply``
* Verify (check diff=0): ``python3 tools/spec/gen_legality_list.py --verify``
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# DRY: reuse classification logic from gen_asm_list
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.llvm.gen_asm_list import classify, SECTION_ORDER, CLASS_TO_SPEC

OPCODES = ROOT / "contracts/opcodes.yaml"
RULES = ROOT / "contracts/legality_rules.yaml"

LEGALITY_START = "<!-- LEGALITY_START -->"
LEGALITY_END = "<!-- LEGALITY_END -->"

# Rule id → semantic group (二级语义)
SEMANTIC_MAP: dict[str, str] = {
    "dst_rd0":           "目的寄存器约束",
    "dst_rd0_nonzero":   "目的寄存器约束",
    "dst_dual_same":     "目的寄存器约束",
    "dst_rb0":           "目的寄存器约束",
    "dst_rf0":           "目的寄存器约束",
    "mreg_zero":         "操作数范围",
    "mreg_range_overflow": "操作数范围",
    "mreg_range_overlap": "操作数组合",
    "excp_malign":       "数据对齐",
    "excp_ialign":       "指令对齐",
    "encode_sbz":        "编码合法性",
    "encode_fp_root_n":  "编码合法性",
    "excp_undi":         "编码合法性",
    "excp_rasof":        "控制流",
    "excp_rasuf":        "控制流",
}

# Global rules not referenced by any instruction's rule_refs;
# explicit chapter assignment per task constraints.
GLOBAL_RULE_CHAPTER: dict[str, str] = {
    "excp_ialign": "控制流",
    "excp_rasof":  "控制流",
    "excp_rasuf":  "控制流",
    # excp_undi 属 ch00 兜底，ch00 无生成区 ⇒ 不出现在任何章的渲染中
}

# Short trigger-condition summaries per rule
RULE_SUMMARY: dict[str, str] = {
    "dst_rd0":           "目的 rd0 → ILLI",
    "dst_rd0_nonzero":   "ret 目的 rd0 时 imms18≠0 → ILLI",
    "dst_dual_same":     "双目的同为 rd0 或同寄存器 → ILLI",
    "dst_rb0":           "目的 rb0 → ILLI",
    "dst_rf0":           "浮点目的 rf0 → ILLI",
    "mreg_zero":         "immu6=0 → ILLI",
    "mreg_range_overflow": "起始+immu6>64 → ILLI",
    "mreg_range_overlap": "源/目的范围交集 → ILLI",
    "excp_malign":       "未对齐访问 → MALIGN",
    "excp_ialign":       "PC[1:0]≠0 → IALIGN",
    "encode_sbz":        "SBZ 非零 → ILLI",
    "encode_fp_root_n":  "ftroot/foroot n≠2 → ILLI",
    "excp_undi":         "保留编码 → UNDI",
    "excp_rasof":        "RAS 上溢 → RASOF",
    "excp_rasuf":        "RAS 下溢 → RASUF",
}

# Semantic group display order within each fault group
SEMANTIC_ORDER = [
    "目的寄存器约束",
    "操作数范围",
    "操作数组合",
    "编码合法性",
    "数据对齐",
    "指令对齐",
    "控制流",
]


def load_data() -> tuple[list[dict], list[dict]]:
    """Load opcodes and rules."""
    entries = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    rules_data = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    rules = rules_data["rules"] if isinstance(rules_data, dict) else rules_data
    return entries, rules


def build_rule_to_chapters(entries: list[dict]) -> dict[str, set[str]]:
    """Map each rule_id to the set of chapter names where it applies."""
    rule_to_chapters: dict[str, set[str]] = {}
    for entry in entries:
        cls = classify(entry)
        for ref in entry.get("rule_refs", []):
            rule_to_chapters.setdefault(ref, set()).add(cls)
    # Add global rules
    for rule_id, chapter in GLOBAL_RULE_CHAPTER.items():
        rule_to_chapters.setdefault(rule_id, set()).add(chapter)
    return rule_to_chapters


def build_chapter_entries(entries: list[dict]) -> dict[str, list[dict]]:
    """Group entries by chapter (using classify())."""
    by_class: dict[str, list[dict]] = {}
    for entry in entries:
        by_class.setdefault(classify(entry), []).append(entry)
    return by_class


def build_rule_entries(entries: list[dict]) -> dict[str, list[dict]]:
    """Map each rule_id to the list of entries that reference it."""
    rule_entries: dict[str, list[dict]] = {}
    for entry in entries:
        for ref in entry.get("rule_refs", []):
            rule_entries.setdefault(ref, []).append(entry)
    return rule_entries


def render_chapter_legality(
    chapter: str,
    chapter_entries: list[dict],
    rules: list[dict],
    rule_to_chapters: dict[str, set[str]],
    rule_entries: dict[str, list[dict]],
) -> str:
    """Render the legality section for one chapter.

    Returns a string including LEGALITY_START/END markers.
    """
    # Find rules applicable to this chapter
    applicable_rules: list[dict] = []
    for rule in rules:
        rule_id = rule["id"]
        chapters = rule_to_chapters.get(rule_id, set())
        if chapter in chapters:
            applicable_rules.append(rule)

    # Find non-M1 entries in this chapter (not referenced by any rule), split by scope
    fp_entries = [e for e in chapter_entries
                  if e.get("scope") == "fp" and not e.get("rule_refs")]
    excluded_entries = [e for e in chapter_entries if e.get("scope") == "excluded"]

    # If no rules and no non-M1 entries, still render an empty area
    # (per task: "该章无任何规则的 M1 指令时，仍渲染空区")
    if not applicable_rules and not fp_entries and not excluded_entries:
        return f"{LEGALITY_START}\n## 合法性检查\n\n（本章无适用规则）\n{LEGALITY_END}"

    # Group rules by fault × semantic
    # Structure: fault → semantic → list of (rule, matching_entries)
    fault_groups: dict[str, dict[str, list[tuple[dict, list[dict]]]]] = {}
    for rule in applicable_rules:
        fault = rule["fault"]
        rule_id = rule["id"]
        semantic = SEMANTIC_MAP.get(rule_id, "其它")
        # Get entries in this chapter that reference this rule
        all_rule_ents = rule_entries.get(rule_id, [])
        chapter_rule_ents = [e for e in all_rule_ents if classify(e) == chapter]
        fault_groups.setdefault(fault, {}).setdefault(semantic, []).append(
            (rule, chapter_rule_ents)
        )

    # Render
    lines = [LEGALITY_START, "## 合法性检查", ""]

    # Fault display order
    fault_order = ["ILLI", "UNDI", "MALIGN", "IALIGN", "RASOF", "RASUF"]

    for fault in fault_order:
        if fault not in fault_groups:
            continue
        sem_groups = fault_groups[fault]
        for semantic in SEMANTIC_ORDER:
            if semantic not in sem_groups:
                continue
            rule_list = sem_groups[semantic]
            for rule, matching_ents in rule_list:
                rule_id = rule["id"]
                kind_tag = "（动态）" if rule["kind"] == "dynamic" else ""
                summary = RULE_SUMMARY.get(rule_id, "")
                status_tag = f"（{rule['status']}）" if rule.get("status") != "active" else ""
                # Build instruction list string
                if matching_ents:
                    insn_list = ", ".join(
                        f"`{e['id']}`" for e in sorted(matching_ents, key=lambda x: x["id"])
                    )
                    insn_count = len(matching_ents)
                    lines.append(
                        f"* `{rule_id}`{kind_tag}{status_tag}：{summary} — "
                        f"{insn_list}（{insn_count} 条）"
                    )
                else:
                    # Global rule with no per-instruction references
                    lines.append(f"* `{rule_id}`{kind_tag}{status_tag}：{summary}")

    # Add non-M1 instructions note, split by scope
    if fp_entries:
        lines.append("")
        lines.append("**scope: fp（无附加合法性规则）：**")
        for e in sorted(fp_entries, key=lambda x: x["id"]):
            lines.append(f"* `{e['id']}`")
    if excluded_entries:
        lines.append("")
        lines.append("**scope: excluded（decode ILLI）：**")
        for e in sorted(excluded_entries, key=lambda x: x["id"]):
            lines.append(f"* `{e['id']}`：decode ILLI")

    lines.append(LEGALITY_END)
    return "\n".join(lines)


def inject_legality(spec_path: Path, legality_block: str, dry_run: bool = False) -> str | None:
    """Inject legality block into a spec file.

    The block is placed right after ``<!-- ASSEMBLY_LIST_END -->``.

    Returns the diff description, or None if no change needed.
    """
    content = spec_path.read_text(encoding="utf-8")

    # Find ASSEMBLY_LIST_END
    if "<!-- ASSEMBLY_LIST_END -->" not in content:
        return f"WARNING: {spec_path} has no <!-- ASSEMBLY_LIST_END --> marker, cannot inject"

    # Build new content
    lines = content.split("\n")
    asm_end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "<!-- ASSEMBLY_LIST_END -->":
            asm_end_idx = i
            break

    if asm_end_idx is None:
        return f"WARNING: {spec_path} marker not found after split, cannot inject"

    # Find existing legality block boundaries
    legality_start_idx = None
    legality_end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == LEGALITY_START:
            legality_start_idx = i
        if line.strip() == LEGALITY_END:
            legality_end_idx = i
            break

    if legality_start_idx is not None and legality_end_idx is not None:
        # Replace existing legality block
        before = lines[:legality_start_idx]
        after = lines[legality_end_idx + 1:]
        new_lines = before + legality_block.split("\n") + after
    else:
        # Insert new legality block right after ASSEMBLY_LIST_END
        before = lines[:asm_end_idx + 1]  # include ASSEMBLY_LIST_END
        after = lines[asm_end_idx + 1:]
        new_lines = before + [""] + legality_block.split("\n") + [""] + after

    new_content = "\n".join(new_lines)

    if new_content == content:
        return None  # No change

    if not dry_run:
        spec_path.write_text(new_content, encoding="utf-8")

    return f"{'Would inject' if dry_run else 'Injected'} into {spec_path}"


def verify_legality(spec_path: Path, expected_block: str) -> bool:
    """Verify that the spec file contains the expected legality block."""
    content = spec_path.read_text(encoding="utf-8")
    return expected_block in content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Print legality blocks without writing")
    group.add_argument("--apply", action="store_true", help="Inject legality blocks into spec files")
    group.add_argument("--verify", action="store_true", help="Verify spec files match expected content")
    args = parser.parse_args()

    entries, rules = load_data()
    rule_to_chapters = build_rule_to_chapters(entries)
    chapter_entries = build_chapter_entries(entries)
    rule_entries_map = build_rule_entries(entries)

    # Generate legality blocks for each chapter
    chapter_blocks: dict[str, str] = {}
    verify_failed = False
    for cls in SECTION_ORDER:
        if cls not in CLASS_TO_SPEC:
            continue
        spec_rel = CLASS_TO_SPEC[cls]
        spec_path = ROOT / spec_rel
        if not spec_path.exists():
            print(f"gen-legality: WARNING: {spec_path} not found, skipping", file=sys.stderr)
            continue

        ents = chapter_entries.get(cls, [])
        block = render_chapter_legality(cls, ents, rules, rule_to_chapters, rule_entries_map)
        chapter_blocks[cls] = block

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"Chapter: {cls} → {spec_rel}")
            print(f"{'='*60}")
            print(block)
        elif args.apply:
            result = inject_legality(spec_path, block, dry_run=False)
            if result:
                print(f"gen-legality: {result}")
            else:
                print(f"gen-legality: {spec_rel} unchanged (idempotent)")
        elif args.verify:
            ok = verify_legality(spec_path, block)
            status = "OK" if ok else "MISMATCH"
            print(f"gen-legality: {spec_rel} {status}")
            if not ok:
                print(f"  Expected block not found in {spec_path}")
                verify_failed = True

    # ISS-122: --verify must fail (non-zero) on MISMATCH; --dry-run/--apply unchanged.
    return 1 if verify_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
