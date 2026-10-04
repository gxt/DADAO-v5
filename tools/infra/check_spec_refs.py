#!/usr/bin/env python3
"""spec 引用审计器 — Check 1 引用有效性 + Check 2 无引用规范断言.

审计对象: .tao/knowledge/contract-*.md
引用目标: spec/*.md (SimRISC-00~04, DADAO-11~23)

Check 1: 每个 [SimRISC-XX §...] / [DADAO-XX §...] 可解析到 spec/ 真实内容。
         三类命中: 标题(#1~4) > 粗体引子(> **X**：/ **X**) > 正文行。
Check 2: 含规范标记(ILLI/UNDI/MALIGN/IALIGN/保留/reserved/必须 等) 且既无
         spec 引用也无 [spec-decision]/ADR 引用的断言 → 报「无引用断言」。

         引用作用域（block scope，非逐行）: 合约以「前导行 + 块」方式标注来源。
         一条规范断言满足以下任一即视为已引用：
           (a) 本行含 spec 引用 / [spec-decision] / ADR 引用；
           (b) 同块内、**本行之前**已有引用行（前导继承；不含后置继承）；
           (c) 本块为 **表格/引用块**（其紧邻前导块的结构化投影/附注），且紧邻
               前一块为非标题的带引用块。**列表不参与 (c)**——空行分隔的列表
               视为独立断言序列，须逐条自带引用。
         节标题（#1~6）是结构而非断言，不参与 Check 2。
         详见 INFRA-011t 审阅记录「行级误报率评估」与下方 Check 2 作用域实现。

fail-closed: 有违规 → exit 1; 无违规 → exit 0.

Usage:
    python3 tools/infra/check_spec_refs.py [--contract-dir DIR] [--spec-dir DIR]
"""

import argparse
import os
import re
import sys
from pathlib import Path

# ── 显式排除名单（机械生成投影，非叙述合约，无来源头/§ 引用）──────────────
# 与 tools/infra/check_spec_drift.py 的 EXCLUDED_CONTRACTS 同步：
# 新增任何生成投影务必同步两处排除名单。
_EXCLUDED_CONTRACTS = frozenset({
    "contract-cfx-aliases.md",  # cfx 别名表（生成物，见 spec/README.md 投影表）
    "contract-asm-list.md",     # 汇编指令表（生成物，见 spec/README.md 投影表）
})

# ── prefix → spec file mapping ───────────────────────────────────────────────

SPEC_PREFIX_MAP = {
    "SimRISC-00": "SimRISC-00-指令系统设计.md",
    "SimRISC-01": "SimRISC-01-取数存数.md",
    "SimRISC-02": "SimRISC-02-寄存器复制.md",
    "SimRISC-03": "SimRISC-03-16位立即数操作.md",
    "SimRISC-04": "SimRISC-04-64位数据运算.md",
    "SimRISC-05": "SimRISC-05-64位地址运算.md",
    "SimRISC-06": "SimRISC-06-控制流.md",
    "SimRISC-07": "SimRISC-07-浮点运算.md",
    "SimRISC-08": "SimRISC-08-32位数据运算.md",
    "SimRISC-09": "SimRISC-09-16位数据运算.md",
    "SimRISC-10": "SimRISC-10-8位数据运算.md",
    "SimRISC-11": "SimRISC-11-其它.md",
    "SimRISC-12": "SimRISC-12-待定.md",
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


def line_has_cite(line: str) -> bool:
    """Line carries a spec reference or an explicit decision marker."""
    return check_line_has_spec_ref(line) or check_line_has_decision(line)


# Heading (#1~6): structural, never a normative assertion.
_HEADING_RE = re.compile(r"^\s*#{1,6}\s")


def is_inheriting_child_line(line: str) -> bool:
    """Whether `line` opens a block that may inherit its immediately-preceding
    cited lead-in's citation.

    Scope is deliberately narrow (architect xcheck G1/EXP-B): only a **table**
    (a structured projection of its caption) or a **blockquote** (an annotation
    attached to the preceding block) may inherit across a blank line. A bare
    **list** is treated as a sequence of independent assertions and thus must
    carry its own citation per line — a blank-separated list does not inherit.
    """
    if not line.strip():
        return False
    s = line.lstrip()
    return s.startswith("|") or s.startswith(">")


# ── main audit ───────────────────────────────────────────────────────────────

def audit(contract_dir: Path, spec_dir: Path) -> int:
    """Run both checks. Returns violation count (0 = pass)."""
    contract_files = sorted(
        p for p in contract_dir.glob("contract-*.md")
        if p.name not in _EXCLUDED_CONTRACTS
    )
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
    # 作用域模型: 逐行判定取代为「引用块作用域」判定（见 INFRA-011t 审阅记录
    # 「行级误报率评估」）。一条规范断言满足以下任一即视为已引用:
    #   (a) 本行含 spec 引用 / [spec-decision] / ADR 引用;
    #   (b) 同一块（连续非空行）内、**本行之前**的引用行（前导继承，不含后置）;
    #   (c) 本块为 table/blockquote（其前导块的结构化投影/附注），且紧邻前一块为
    #       非标题的带引用块。列表不参与 (c)。
    # 节标题（#1~6）是结构，不参与 Check 2。
    check2_violations: list[dict] = []

    for cfile in contract_files:
        content = cfile.read_text(encoding="utf-8")
        raw_lines = content.splitlines()
        n_lines = len(raw_lines)

        # Code-block tracking (skipped by Check 2).
        in_code = [False] * n_lines
        cur_code = False
        for i, line in enumerate(raw_lines):
            cur_code = is_in_code_block(line, cur_code)
            in_code[i] = cur_code

        # Block ids: a block = maximal run of consecutive non-blank lines.
        block_id = [-1] * n_lines
        block_first: dict[int, int] = {}
        bid = -1
        prev_blank = True
        for i, line in enumerate(raw_lines):
            if line.strip() == "":
                prev_blank = True
                continue
            if prev_blank:
                bid += 1
            block_id[i] = bid
            block_first.setdefault(bid, i)
            prev_blank = False

        # Per-block citation presence (code lines excluded) — used by rule (c).
        block_has_cite: dict[int, bool] = {}
        for i, line in enumerate(raw_lines):
            if block_id[i] >= 0 and not in_code[i] and line_has_cite(line):
                block_has_cite[block_id[i]] = True

        # Rule (b) is LEADING-only: for each line, whether an earlier line of the
        # same block already carried a citation (a later citation must NOT
        # retroactively cover this line — see architect xcheck G1 / EXP-D).
        preceding_cite = [False] * n_lines
        _seen_cite: dict[int, bool] = {}
        for i, line in enumerate(raw_lines):
            bid_i = block_id[i]
            if bid_i < 0:
                continue
            preceding_cite[i] = _seen_cite.get(bid_i, False)
            if not in_code[i] and line_has_cite(line):
                _seen_cite[bid_i] = True

        def _preceding_block_has_cite(idx: int) -> bool:
            """Immediately preceding non-blank block carries a citation, and is
            not a heading (heading cannot serve as a source lead-in)."""
            fb = block_first[block_id[idx]]
            p = fb - 1
            while p >= 0 and raw_lines[p].strip() == "":
                p -= 1
            if p < 0 or _HEADING_RE.match(raw_lines[p]):
                return False
            pb = block_id[p]
            return pb >= 0 and block_has_cite.get(pb, False)

        for i, line in enumerate(raw_lines):
            if in_code[i]:
                continue
            if not _NORMATIVE_RE.search(line):
                continue
            if line_has_cite(line):
                continue  # (a)
            if _HEADING_RE.match(line):
                continue  # headings are structure, not assertions
            bid_i = block_id[i]
            if preceding_cite[i]:
                continue  # (b) LEADING citation earlier in the same block
            block_first_line = raw_lines[block_first[bid_i]]
            if is_inheriting_child_line(block_first_line) and _preceding_block_has_cite(i):
                continue  # (c) table/blockquote introduced by a cited lead-in

            # Normative assertion without any spec reference → violation
            check2_violations.append({
                "file": str(cfile),
                "line": i + 1,
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
