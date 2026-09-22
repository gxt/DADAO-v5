#!/usr/bin/env python3
"""spec 引用审计器 — Check 1 引用有效性 + Check 2 无引用规范断言.

审计对象: .tao/knowledge/contract-*.md
引用目标: spec/*.md (SimRISC-00~04, DADAO-11~23)

Check 1: 每个 [SimRISC-XX §...] / [DADAO-XX §...] 可解析到 spec/ 真实内容。
         三类命中: 标题(#1~4) > 粗体引子(> **X**：/ **X**) > 正文行。
Check 2: 含规范标记(ILLI/UNDI/MALIGN/IALIGN/保留/reserved/必须 等) 且既无
         spec 引用也无 [spec-decision]/ADR 引用的行 → 报「无引用断言」。

fail-closed: 有违规 → exit 1; 无违规 → exit 0.

Usage:
    python3 tools/infra/check_spec_refs.py [--contract-dir DIR] [--spec-dir DIR]
"""

import argparse
import os
import re
import sys
from pathlib import Path

# ── prefix → spec file mapping ───────────────────────────────────────────────

SPEC_PREFIX_MAP = {
    "SimRISC-00": "SimRISC-00-指令系统设计.md",
    "SimRISC-01": "SimRISC-01-数据类指令.md",
    "SimRISC-02": "SimRISC-02-地址类指令.md",
    "SimRISC-03": "SimRISC-03-浮点类指令.md",
    "SimRISC-04": "SimRISC-04-系统类指令.md",
    "DADAO-11":   "DADAO-11-AEE-应用程序运行环境.md",
    "DADAO-12":   "DADAO-12-SEE-主管系统运行环境.md",
    "DADAO-13":   "DADAO-13-HEE-超管系统运行环境.md",
    "DADAO-21":   "DADAO-21-ABI-应用程序二进制接口.md",
    "DADAO-22":   "DADAO-22-SBI-主管系统二进制接口.md",
    "DADAO-23":   "DADAO-23-HBI-超管系统二进制接口.md",
}

# ── regex patterns ────────────────────────────────────────────────────────────

# Prefix search anchor: [SimRISC-XX § or [DADAO-XX § or [SimRISC-0X § (template)
_PREFIX_ANCHOR = re.compile(r"\[(SimRISC-(?:\d+|0X)|DADAO-\d+) §")

# Headers: # / ## / ### / ####  heading text
_HEADER_RE = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)

# Bold blockquote: > **text** or > **text**：
_BOLD_BQ_RE = re.compile(r"^>\s*\*\*(.+?)\*\*", re.MULTILINE)

# Bold inline: **text**
_BOLD_INLINE_RE = re.compile(r"\*\*(.+?)\*\*")

# Check 2: normative markers
_NORMATIVE_MARKERS = [
    "ILLI", "UNDI", "MALIGN", "IALIGN",
    "保留", "reserved", "Reserved",
    "必须", "应当", "不得", "需要",
    "MUST", "SHALL", "REQUIRED",
    "SBZ",
]
_NORMATIVE_RE = re.compile("|".join(re.escape(m) for m in _NORMATIVE_MARKERS))

# Decision markers (exclude from Check 2)
_SPEC_DECISION_RE = re.compile(r"\[spec-decision\]")
_ADR_REF_RE = re.compile(r"ADR-\d{4}")

# (Lnn) line-number suffix
_LN_SUFFIX_RE = re.compile(r"\s*\(L\d+\)$")


# ── bracket-aware ref extraction ─────────────────────────────────────────────

def extract_refs(line: str) -> list[tuple[str, str, str]]:
    """Extract [Prefix §section] refs, handling ] inside titles like bits[63:48].

    Returns list of (prefix, section_name, full_match_text).
    """
    refs: list[tuple[str, str, str]] = []
    pos = 0
    while pos < len(line):
        m = _PREFIX_ANCHOR.search(line[pos:])
        if not m:
            break
        start = pos + m.start()
        prefix = m.group(1)
        # section starts after '[PREFIX §'
        sec_start = start + 1 + len(prefix) + 2  # '[' + prefix + ' §'
        i = sec_start
        depth = 1
        while i < len(line) and depth > 0:
            ch = line[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            i += 1
        if depth == 0:
            section = line[sec_start : i - 1].strip()
            refs.append((prefix, section, line[start:i]))
        pos = i
    return refs


# ── helpers ──────────────────────────────────────────────────────────────────

def load_spec_file(spec_dir: Path, prefix: str) -> str | None:
    """Load spec file content by prefix. Returns None if not found."""
    filename = SPEC_PREFIX_MAP.get(prefix)
    if not filename:
        return None
    path = spec_dir / filename
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _header_matches(header: str, section: str) -> bool:
    """Check if section_name matches a spec header.

    1. Exact / prefix (section：) via _text_matches
    2. Split: header splits on '、' and section is one of the parts
    """
    if _text_matches(header, section):
        return True
    if "、" in header and section in header.split("、"):
        return True
    return False


_TEXT_LEAD_IN = set("：:（(，,")


def _text_matches(text: str, section: str) -> bool:
    """Check if section matches text: exact or followed by a lead-in char.

    Lead-in chars: ：: （(  ,
    No arbitrary substring (§数据表 must NOT match 数据表示).
    Allows §版本 to match **版本：0.5.3** and §RD寄存器 to match
    RD寄存器（Data registers）.
    """
    if section == text:
        return True
    if len(text) > len(section) and text.startswith(section) and text[len(section)] in _TEXT_LEAD_IN:
        return True
    return False


# N1 (reviewer, 2026-09-21): 不含 "如"/"下" 单字；"如下" 由下方显式 startswith 处理，
# 避免 `section如…`/`section下…` 被误判为 lead-in。
_LEAD_IN_CHARS = set("：:（(，,")


def _line_start_matches(line: str, section: str) -> bool:
    """Check if section appears at start of a stripped line with a lead-in.

    Lead-in: section is followed by one of ：: （(  , '如下' or is at end of line.
    Prevents false positives like §数据 matching 数据寄存器又可称为...
    while allowing §...处理规则 matching ...处理规则如下：
    """
    stripped = line.strip()
    if not stripped.startswith(section):
        return False
    rest = stripped[len(section):]
    if not rest:
        return True  # section is the entire line
    if rest[0] in _LEAD_IN_CHARS:
        return True
    if rest.startswith("如下"):
        return True
    return False


def resolve_section(spec_content: str, section_name: str) -> tuple[str, bool]:
    """Try to find section_name in spec content.

    Returns (hit_type, found) where hit_type is 'header'/'bold'/'text'/''.
    Resolution order: header → bold marker → text (line-start).

    Matching is exact (not substring) to prevent false positives like
    §数据表 matching 数据表示. For compound references (containing §),
    each part is checked independently.
    """
    # Split compound references on §
    parts = [p.strip() for p in section_name.split("§") if p.strip()]

    if len(parts) > 1:
        # Compound: each part must be found
        # First part: header prefix/split match
        # Subsequent parts: header exact/prefix/split match
        all_found = True
        worst_type = "text"
        for part in parts:
            part_found = False
            # Check headers (exact / prefix / split)
            for m in _HEADER_RE.finditer(spec_content):
                if _header_matches(m.group(1).strip(), part):
                    part_found = True
                    worst_type = "header"
                    break
            if not part_found:
                # Check bold (exact match only)
                for m in _BOLD_BQ_RE.finditer(spec_content):
                    if _text_matches(m.group(1).strip(), part):
                        part_found = True
                        if worst_type != "header":
                            worst_type = "bold"
                        break
                if not part_found:
                    bold_inline = re.compile(r"\*\*" + re.escape(part) + r"\*\*")
                    if bold_inline.search(spec_content):
                        part_found = True
                        if worst_type != "header":
                            worst_type = "bold"
                if not part_found:
                    # Line-start text search (with lead-in)
                    for sl in spec_content.splitlines():
                        if _line_start_matches(sl, part):
                            part_found = True
                            break
            if not part_found:
                all_found = False
                break
        if all_found:
            return worst_type, True
        return "", False

    # Simple (non-compound) reference
    # 1. Check headers (#1~4) — exact / prefix / split match
    for m in _HEADER_RE.finditer(spec_content):
        if _header_matches(m.group(1).strip(), section_name):
            return "header", True

    # 2. Check bold markers — exact match only
    for m in _BOLD_BQ_RE.finditer(spec_content):
        if _text_matches(m.group(1).strip(), section_name):
            return "bold", True
    bold_inline_search = re.compile(r"\*\*" + re.escape(section_name) + r"\*\*")
    if bold_inline_search.search(spec_content):
        return "bold", True

    # 3. Line-start text search (with lead-in)
    for sl in spec_content.splitlines():
        if _line_start_matches(sl, section_name):
            return "text", True

    return "", False


def is_in_code_block(line: str, in_code: bool) -> bool:
    """Track code block state (``` delimited)."""
    if line.strip().startswith("```"):
        return not in_code
    return in_code


def check_line_has_spec_ref(line: str) -> bool:
    """Check if line contains any [SimRISC-XX §...] or [DADAO-XX §...] ref."""
    return bool(_PREFIX_ANCHOR.search(line))


def check_line_has_decision(line: str) -> bool:
    """Check if line has [spec-decision] or ADR-NNNN marker."""
    return bool(_SPEC_DECISION_RE.search(line) or _ADR_REF_RE.search(line))


# ── main audit ───────────────────────────────────────────────────────────────

def audit(contract_dir: Path, spec_dir: Path) -> int:
    """Run both checks. Returns violation count (0 = pass)."""
    contract_files = sorted(contract_dir.glob("contract-*.md"))
    if not contract_files:
        print("ERROR: no contract-*.md files found", file=sys.stderr)
        return 1

    # ── Check 1: reference validity ──────────────────────────────────────
    check1_violations: list[dict] = []
    check1_hit_stats = {"header": 0, "bold": 0, "text": 0}
    check1_total_refs = 0
    check1_ln_count = 0

    # Cache spec contents
    spec_cache: dict[str, str] = {}

    for cfile in contract_files:
        content = cfile.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), 1):
            refs = extract_refs(line)
            for prefix, section, full_match in refs:
                check1_total_refs += 1

                # Strip optional (Lnn) suffix
                ln_match = _LN_SUFFIX_RE.search(section)
                if ln_match:
                    check1_ln_count += 1
                    section = section[: ln_match.start()].strip()

                # Load spec file
                if prefix not in spec_cache:
                    spec_cache[prefix] = load_spec_file(spec_dir, prefix) or ""
                spec_content = spec_cache[prefix]

                spec_file = SPEC_PREFIX_MAP.get(prefix)
                spec_path = spec_dir / spec_file if spec_file else None

                # Check file exists
                if not spec_content or not spec_path or not spec_path.is_file():
                    check1_violations.append({
                        "file": str(cfile),
                        "line": lineno,
                        "ref": full_match,
                        "reason": "文件不存在",
                        "hit_type": "",
                    })
                    continue

                # Try to resolve section
                hit_type, found = resolve_section(spec_content, section)
                if found:
                    check1_hit_stats[hit_type] += 1
                else:
                    check1_violations.append({
                        "file": str(cfile),
                        "line": lineno,
                        "ref": full_match,
                        "reason": "节标题未找到",
                        "hit_type": "",
                    })

    # ── Check 2: normative assertions without spec reference ─────────────
    check2_violations: list[dict] = []

    for cfile in contract_files:
        content = cfile.read_text(encoding="utf-8")
        in_code = False
        for lineno, line in enumerate(content.splitlines(), 1):
            in_code = is_in_code_block(line, in_code)
            if in_code:
                continue

            # Does the line have normative markers?
            if not _NORMATIVE_RE.search(line):
                continue

            # Does the line have a spec reference or decision marker?
            if check_line_has_spec_ref(line) or check_line_has_decision(line):
                continue

            # This line has normative markers but no spec reference → violation
            check2_violations.append({
                "file": str(cfile),
                "line": lineno,
                "text": line.rstrip(),
            })

    # ── Report ───────────────────────────────────────────────────────────
    total_violations = len(check1_violations) + len(check2_violations)

    print("=" * 72)
    print("spec 引用审计报告")
    print("=" * 72)
    print()

    # -- Check 1 summary --
    print(f"Check 1 — 引用有效性")
    print(f"  总引用数: {check1_total_refs}")
    print(f"  (Lnn) 行号形态: {check1_ln_count} 处")
    if check1_ln_count == 0:
        print(f"  注: 本轮无 (Lnn) 实例")
    print(f"  命中类型统计: 标题={check1_hit_stats['header']}, "
          f"粗体={check1_hit_stats['bold']}, 正文={check1_hit_stats['text']}")
    resolved = sum(check1_hit_stats.values())
    print(f"  成功解析: {resolved}")
    print(f"  失败: {len(check1_violations)}")
    print()

    if check1_violations:
        print("  失败明细:")
        for v in check1_violations:
            relpath = os.path.relpath(v["file"], start=os.getcwd())
            print(f"    {relpath}:{v['line']}  {v['ref']}")
            print(f"      原因: {v['reason']}")
        print()

    # -- Check 2 summary --
    print(f"Check 2 — 无引用规范断言")
    print(f"  命中数: {len(check2_violations)}")
    print()

    if check2_violations:
        print("  命中明细:")
        for v in check2_violations:
            relpath = os.path.relpath(v["file"], start=os.getcwd())
            display_text = v["text"]
            if len(display_text) > 100:
                display_text = display_text[:97] + "..."
            print(f"    {relpath}:{v['line']}")
            print(f"      {display_text}")
        print()

    # -- Final verdict --
    print("-" * 72)
    if total_violations == 0:
        print("结果: PASS (0 violations)")
    else:
        print(f"结果: FAIL ({total_violations} violations: "
              f"{len(check1_violations)} Check1 + {len(check2_violations)} Check2)")
    print("-" * 72)

    return total_violations


def main():
    parser = argparse.ArgumentParser(description="spec 引用审计器")
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--contract-dir",
        type=Path,
        default=default_root / ".tao" / "knowledge",
        help="合约文件目录 (default: .tao/knowledge)",
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        default=default_root / "spec",
        help="spec 文件目录 (default: spec/)",
    )
    args = parser.parse_args()

    violations = audit(args.contract_dir, args.spec_dir)
    sys.exit(1 if violations > 0 else 0)


if __name__ == "__main__":
    main()
