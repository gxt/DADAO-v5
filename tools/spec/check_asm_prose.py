#!/usr/bin/env python3
"""Check prose fenced-code blocks for old DADAO assembly format (violations of ADR-0013).

Scans markdown files and reports lines inside fenced code blocks that use
the **old** assembly syntax (pre-ADR-0013).  Two modes:

* **report** (default): emit ``file:line  rule  original`` for each violation,
  exit 0 regardless.
* ``--strict``: same output, but exit 1 if any violation was found.

Rules (old-format ⇒ violation)
------------------------------
R1  Memory access missing ``[...]``  — ``ld.*/st.*/ldm.*/stm.*/cfxld/cfxst`` operands
    must use ``[rbN, …]`` address; bare ``rbN, imm`` ⇒ violation.
R2  Jump/branch target missing ``[...]`` — ``jump/call/br.*/cs.`` must use ``[...]``;
    ``br.*/cs.`` conditions must use ``{…}?``.
R2' Byte-offset alignment — numeric byte offsets in ``jump/call/br.*/escape`` operands
    (``[rb0, N]``, ``[rbN, rdN, N]``, ``[excp_cause_ip, N]``) must be ``%4==0``.
    Symbolic offsets and ``ld.*/st.*`` memory offsets are **not** checked.
R3  cfx operand shape — ``cfx2rd/cfx2rc`` must be long form (``cfxHA, cgHB, rcHC, rdHD``)
    or alias form (``<cfxreg>, rdHD``).
R4  ``#`` comment — bare ``#`` used as comment inside assembly (not ``#define``/``#include``
    /``#if``…  C-preprocessor directives).
R5  Multi-register group — ``ldm/stm``/block-copy/format-convert must use ``{start:end}``
    range notation; old form ``rdN, …, count`` ⇒ violation.
R6  Operand shape from opcodes.yaml — for each mnemonic, ``opcodes.yaml`` lists all
    valid format variants (e.g. ``add.so`` has both ``rrrr`` and ``orrr``).  The checker
    counts operands (``{…}`` = one operand) and verifies the count matches at least one
    known format's expected count.  Only flag when **no** format variant matches.
    Block-copy/format-convert (``ra2rd``, ``ft2fo``, etc.) additionally require ``{…}``.

Scan scope
----------
* ``spec/**/*.md``  (excl. ``spec/SimRISC-0.5.3/``)
* ``docs/**/*.md``  (excl. ``m1-retrospective.md``, ``testcases-009t-audit.md``,
  ``self-consistency.md``)
* ``.tao/knowledge/contract-*.md`` + ``.tao/adr/*.md``  (excl. ``lessons.md``)

Only fenced code blocks (```…```) are inspected; generated regions delimited by
``<!-- ASSEMBLY_LIST_* -->`` / ``<!-- LEGALITY_* -->`` are excluded.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

# Files explicitly excluded
_EXCLUDE_FILES = {
    ROOT / "docs" / "m1-retrospective.md",
    ROOT / "docs" / "testcases-009t-audit.md",
    ROOT / "docs" / "self-consistency.md",
    ROOT / ".tao" / "knowledge" / "lessons.md",
}

_EXCLUDE_DIRS = {
    ROOT / "spec" / "SimRISC-0.5.3",
}

# Override root for --root mode (set by CLI before scanning)
_override_root: Path | None = None

# ---------------------------------------------------------------------------
# Violation dataclass
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    file: Path
    line: int       # 1-based line in original file
    rule: str
    original: str   # the offending line (stripped)

# ---------------------------------------------------------------------------
# Load opcodes.yaml for operand-shape rules (R6)
# ---------------------------------------------------------------------------

def _load_opcode_formats() -> dict[str, set[str]]:
    """Return ``{mnemonic: {format, ...}}`` from opcodes.yaml (all variants)."""
    yaml_path = ROOT / "contracts" / "opcodes.yaml"
    if not yaml_path.exists():
        return {}
    result: dict[str, set[str]] = {}
    try:
        import yaml  # type: ignore
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            for entry in data:
                mn = entry.get("mnemonic", "")
                fmt = entry.get("format", "")
                if mn and fmt:
                    result.setdefault(mn, set()).add(fmt)
    except Exception:
        # Fallback: simple regex parse
        current_mn = ""
        current_fmt = ""
        for line in yaml_path.read_text().splitlines():
            m = re.match(r"^\s*mnemonic:\s*(\S+)", line)
            if m:
                current_mn = m.group(1)
            m = re.match(r"^\s*format:\s*(\S+)", line)
            if m:
                current_fmt = m.group(1)
                if current_mn and current_fmt:
                    result.setdefault(current_mn, set()).add(current_fmt)
                    current_mn = ""
                    current_fmt = ""
    return result

# ---------------------------------------------------------------------------
# Build cfx alias set from cfx-aliases.md
# ---------------------------------------------------------------------------

_CFX_ALIAS_PATTERN = re.compile(r"^\|\s*`(cfx_[\w⟨⟩\[\].−\d]+)`\s*\|")

# All known cfxnames (from the scalar alias table)
_CFX_NAMES = [
    "umon", "jmon", "smon", "hmon", "ptw", "tlb", "cache",
    "hart", "llc", "pmem", "timer", "uart", "power",
]

def _load_cfx_aliases() -> tuple[set[str], dict[str, tuple[int, int]]]:
    """Load cfx alias names and their index ranges from ``.tao/knowledge/contract-cfx-aliases.md``.

    Templates with ``⟨cfxname⟩`` are expanded to all known cfx names.
    Returns ``(aliases, ranges)`` where ``ranges`` maps base name (without
    ``[lo..hi]``) to ``(lo, hi)`` for range-indexed registers.
    """
    alias_path = ROOT / ".tao" / "knowledge" / "contract-cfx-aliases.md"
    if not alias_path.exists():
        return set(), {}
    aliases: set[str] = set()
    ranges: dict[str, tuple[int, int]] = {}
    for line in alias_path.read_text().splitlines():
        m = _CFX_ALIAS_PATTERN.match(line)
        if m:
            name = m.group(1)
            if "⟨cfxname⟩" in name:
                # Expand template for all cfx names
                for cfxn in _CFX_NAMES:
                    expanded = name.replace("⟨cfxname⟩", cfxn)
                    aliases.add(expanded)
                    # For range-indexed, also add base name (without [lo..hi])
                    base = re.sub(r"\[\d+\.\.\d+(?:−\d+)?\]$", "", expanded)
                    if base != expanded:
                        aliases.add(base)
            else:
                aliases.add(name)
                # For range-indexed, also add base name
                base = re.sub(r"\[\d+\.\.\d+(?:−\d+)?\]$", "", name)
                if base != name:
                    aliases.add(base)
        # Parse range-indexed entries: | `cfx_ptw_ptbr[0..63]` | … | … | 0-63 | … |
        # The [lo..hi] in the name is the array index range.
        if line.startswith("|") and "[" in line and ".." in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 2:
                cell0 = cells[0].strip("`")
                # Extract base name and range from [lo..hi] in the name
                bracket_match = re.search(r"\[(\d+)\.\.(\d+)\]", cell0)
                if bracket_match:
                    base_name = cell0[:bracket_match.start()]
                    idx_lo = int(bracket_match.group(1))
                    idx_hi = int(bracket_match.group(2))
                    # Expand templates
                    if "⟨cfxname⟩" in base_name:
                        for cfxn in _CFX_NAMES:
                            ranges[base_name.replace("⟨cfxname⟩", cfxn)] = (idx_lo, idx_hi)
                    else:
                        ranges[base_name] = (idx_lo, idx_hi)
    return aliases, ranges

# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def _should_exclude(p: Path) -> bool:
    if p in _EXCLUDE_FILES:
        return True
    for d in _EXCLUDE_DIRS:
        try:
            p.relative_to(d)
            return True
        except ValueError:
            pass
    return False

def collect_files(root: Path | None = None) -> list[Path]:
    """Collect markdown files in scope.

    If *root* is given (``--root`` mode), scan all ``*.md`` files under that
    root recursively.  Otherwise fall back to the default in-repo scan
    directories (spec/, docs/, .tao/knowledge/).
    """
    files: list[Path] = []
    seen: set[Path] = set()
    if root is not None:
        # --root mode: scan all *.md under the given root
        for p in sorted(root.rglob("*.md")):
            rp = p.resolve()
            if rp not in seen and not _should_exclude(p):
                seen.add(rp)
                files.append(p)
    else:
        patterns = [
            (ROOT / "spec", "**/*.md"),
            (ROOT / "docs", "**/*.md"),
            (ROOT / ".tao" / "knowledge", "contract-*.md"),
            (ROOT / ".tao" / "adr", "*.md"),
        ]
        for base, pat in patterns:
            for p in sorted(base.glob(pat)):
                rp = p.resolve()
                if rp not in seen and not _should_exclude(p):
                    seen.add(rp)
                    files.append(p)
    return files

# ---------------------------------------------------------------------------
# Fenced-code-block extraction
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```(\w*)")

# Markers for generated regions to skip
_GEN_START = re.compile(r"<!--\s*(ASSEMBLY_LIST_START|LEGALITY_START)\s*-->")
_GEN_END   = re.compile(r"<!--\s*(ASSEMBLY_LIST_END|LEGALITY_END)\s*-->")

@dataclass
class CodeBlock:
    lang: str           # language tag (e.g. "simrisc", "asm")
    lines: list[str]    # raw lines (no fence markers)
    start_line: int     # 1-based line number of first content line

def extract_code_blocks(filepath: Path) -> list[CodeBlock]:
    """Extract fenced code blocks, excluding generated regions."""
    blocks: list[CodeBlock] = []
    raw_lines = filepath.read_text(errors="replace").splitlines()

    in_fence = False
    in_generated = False
    fence_lang = ""
    block_lines: list[str] = []
    block_start = 0

    for i, line in enumerate(raw_lines, 1):
        # Track generated regions
        if _GEN_START.search(line):
            in_generated = True
            continue
        if _GEN_END.search(line):
            in_generated = False
            continue

        if not in_fence:
            m = _FENCE_RE.match(line)
            if m:
                in_fence = True
                fence_lang = m.group(1)
                block_lines = []
                block_start = i + 1
        else:
            if line.startswith("```"):
                in_fence = False
                if not in_generated and block_lines:
                    blocks.append(CodeBlock(
                        lang=fence_lang,
                        lines=block_lines,
                        start_line=block_start,
                    ))
            else:
                block_lines.append(line)

    return blocks

# ---------------------------------------------------------------------------
# Format-aware operand-count validation (R6)
# ---------------------------------------------------------------------------

# Expected operand count per format (counting {...} as one operand).
# rrrr: dual-dst form = 3 (brace-pair + 2 regs); cs form = 4 (brace + 3 regs)
# orri block-copy = 2 (two brace-pairs)
_FORMAT_OP_COUNTS: dict[str, set[int]] = {
    "rrrr": {3, 4},   # 3 = dual-dst {rdHA,rdHB},rdHC,rdHD; 4 = cs {cond}?,dst,src1,src2
    "rrri": {2},      # ldm/stm: {rdHA:…}, [rbHB, rdHC]
    "rrii": {2, 3},   # 2 = ld/st rdHA, [rbHB, imm]; 3 = jump [rbHA, rdHB, immi]
    "riii": {1, 2},   # 1 = add.si rdHA, imm; 2 = br.n {rdHA}?, [rb0, immi]
    "iiii": {1},      # jump [rb0, immi]
    "rwii": {3},      # set.zw rdHA, wpN, immu16
    "orrr": {2, 3},   # 3 = and.o rdHB, rdHC, rdHD; 2 = lr_nn.o rdHC, [rbHD] (rdHB implicit rd0)
    "orri": {2, 3},   # 2 = ext.uo rdHB, rdHC, hd; 3 = ra2rd {rd8:rd10}, {ra1:ra3}
    "oiii": {1},      # fence 0 / swym 0
    # cfx family (SPEC-103t/ISS-077: previously absent ⇒ operand count silently skipped)
    "crrr": {2, 4},   # 4 = cfx2rd cfxHA, cgHB, rcHC, rdHD; 2 = alias cfx_<name>, rdHD
    "crii": {2},      # cfxld/cfxst cfxHA, [rbHB, immu12]
    "ciii": {2},      # escape cfxHA, [excp_cause_ip, imms20]; trap cfxHA, immu18
}


def _count_operands(operands_str: str) -> int:
    """Count comma-separated operand groups, treating ``{…}`` and ``[…]`` each as one operand."""
    if not operands_str.strip():
        return 0
    count = 0
    depth = 0  # tracks both {…} and […]
    for ch in operands_str:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count + 1


def _get_valid_operand_counts(formats: set[str]) -> set[int]:
    """Return the union of valid operand counts for the given format set."""
    counts: set[int] = set()
    for fmt in formats:
        counts |= _FORMAT_OP_COUNTS.get(fmt, set())
    return counts


# ---------------------------------------------------------------------------
# Rule checks
# ---------------------------------------------------------------------------

# R1: Memory access: ld.*/st.*/ldm.*/stm.*/cfxld/cfxst must have [...]
_LD_ST_RE = re.compile(
    r"^\s*"
    r"(ld(?:m)?\.[a-z]+|st(?:m)?\.[a-z]+|cfxld|cfxst)"
    r"\s+"
)
# Matches old-style: rdN, rbN, imm  (no brackets)
# New style: rdN, [rbN, imm]  (has brackets)
_NEEDS_BRACKET_MNEMONICS = re.compile(
    r"^\s*"
    r"(ld(?:m)?\.[a-z]+|st(?:m)?\.[a-z]+|cfxld|cfxst)"
    r"\s"
)

# R2: Jump/branch/call must have [...]
# Note: cs.* is NOT here — it needs {...}? but not [...]
_JUMP_BR_RE = re.compile(
    r"^\s*"
    r"(jump|call|br\.[a-z]+)"
    r"\s"
)

# R2b: cs.* needs {...}? but not [...]
_CS_RE = re.compile(
    r"^\s*"
    r"cs\.[a-z]+"
    r"\s"
)

# R4: # comment (not #define / #include / #if / #else / #endif / #pragma / #undef)
_CPP_DIRECTIVES = re.compile(r"^\s*#\s*(define|include|if|else|elif|endif|pragma|undef|ifdef|ifndef|error|warning|line)\b")

# R5: Multi-register: ldm/stm with old-style count (e.g. "ldm.ub rd8, rb0, rd1, 3")
# New style: ldm.ub {rd8:rd10}, [rb0, rd1]
_LDM_STM_RE = re.compile(r"^\s*(ldm|stm)\.[a-z]+\s")

# cfx2rd/cfx2rc alias form
_CFX2_RE = re.compile(r"^\s*(cfx2rd|cfx2rc)\s")

# escape
_ESCAPE_RE = re.compile(r"^\s*escape\s")

# Old-style cfx: cfx2rd cfx_X, rdN (non-alias) or cfx2rd cfxHA, cgHB, rcHC, rdHD
# Long form: cfx2rd cfxHA, cgHB, rcHC, rdHD  (4 operands, middle two are cg/rc)
# Alias form: cfx2rd cfx_<name>_<reg>, rdHD  (2 operands)
# Old bad: cfx2rd cfx_X, rdN (where cfx_X is not a valid alias)

# Register patterns
_REG = r"(?:rd|rb|ra|rf)\d+"
_CG_REG = r"cg\d+"
_RC_REG = r"rc\d+"
_CFX_NUM = r"cfx\d+"
_CFX_ALIAS = r"cfx_[\w]+"

def _is_cfx_long_form(operands: str) -> bool:
    """Check if operands match long form: cfxHA, cgHB, rcHC, rdHD.

    Accepts both concrete values (cfx63, cg8, rc1, rd8) and
    placeholder templates (cfxHA, cgHB, rcHC, rdHD).
    """
    parts = [p.strip() for p in operands.split(",")]
    if len(parts) != 4:
        return False
    # First: cfxN, cfx_alias (scalar), or placeholder cfxHA
    if not (re.match(r"^cfx\d+$", parts[0])
            or re.match(r"^cfx_\w+$", parts[0])
            or re.match(r"^cfxH[A-Z]$", parts[0])):
        return False
    # Second: cg register or placeholder cgHB
    if not (re.match(r"^cg\d+$", parts[1])
            or re.match(r"^cgH[A-Z]$", parts[1])):
        return False
    # Third: rc register or placeholder rcHC
    if not (re.match(r"^rc\d+$", parts[2])
            or re.match(r"^rcH[A-Z]$", parts[2])):
        return False
    # Fourth: rd register or placeholder rdHD
    if not (re.match(r"^rd\d+$", parts[3])
            or re.match(r"^rdH[A-Z]$", parts[3])):
        return False
    return True

def _is_cfx_alias_form(operands: str, cfx_aliases: set[str], cfx_ranges: dict[str, tuple[int, int]] = {}) -> bool:
    """Check if operands match alias form: <cfxreg>, rdHD (2 operands).

    Also accepts array-indexed form: <cfxreg>[N], rdHD where N is in the
    valid range for that register (per ADR-0017 D10).
    """
    parts = [p.strip() for p in operands.split(",")]
    if len(parts) != 2:
        return False
    # First must be a cfx alias (possibly with [N] subscript)
    first = parts[0]
    if first in cfx_aliases:
        pass  # exact match
    elif "[" in first and first.endswith("]"):
        # Array-indexed: name[N]
        bracket_pos = first.index("[")
        base_name = first[:bracket_pos]
        index_str = first[bracket_pos + 1:-1]
        if base_name not in cfx_aliases:
            return False
        try:
            idx = int(index_str)
        except ValueError:
            return False
        if base_name in cfx_ranges:
            lo, hi = cfx_ranges[base_name]
            if not (lo <= idx <= hi):
                return False
        else:
            # Base name has no range → can't use [N]
            return False
    else:
        return False
    # Second must be rd register
    if not re.match(r"^rd\d+$", parts[1]):
        return False
    return True

def _check_line(
    line: str,
    lineno: int,
    filepath: Path,
    opcode_formats: dict[str, set[str]],
    cfx_aliases: set[str],
    cfx_ranges: dict[str, tuple[int, int]] = {},
    is_asm_block: bool = True,
) -> list[Violation]:
    """Check a single line for violations.  May return 0, 1, or multiple."""
    violations: list[Violation] = []
    stripped = line.strip()

    # Skip empty lines, labels, comments
    if not stripped or stripped.startswith(";") or stripped.endswith(":"):
        return violations

    # Strip inline ; comments for operand checks (but keep original for reporting)
    code_part = stripped.split(";")[0].rstrip()

    # R4: # comment (not C preprocessor directive)
    # Only check in assembly blocks (simrisc/asm); non-asm blocks may use
    # # for directory trees, markdown templates, etc.
    if is_asm_block and stripped.startswith("#"):
        if not _CPP_DIRECTIVES.match(stripped):
            violations.append(Violation(filepath, lineno, "R4(#注释)", stripped))
            return violations  # don't double-count
        # #define etc. — these are OK in assembly context (C preprocessor)
        return violations

    # Extract mnemonic (first token)
    tokens = stripped.split()
    if not tokens:
        return violations
    mnemonic = tokens[0].lower()

    # R1: Memory access must have [...]
    if _NEEDS_BRACKET_MNEMONICS.match(code_part):
        # Check if the rest of the operand has [...]
        after_mn = code_part[len(mnemonic):].strip()
        # New format: rdN, [rbN, imm]  — must have [
        if "[" not in after_mn:
            # Special: ldm/stm with {start:end} also OK
            # ldm/stm in new format: {rdN:rdM}, [rbN, ...]
            # But the mnemonic check already covers ld/st, and ldm/stm are separate
            violations.append(Violation(filepath, lineno, "R1(访存缺[])", stripped))

    # R2: Jump/branch/call must have [...]
    if _JUMP_BR_RE.match(code_part):
        after_mn = code_part[len(mnemonic):].strip()
        # Check for [...] in target
        if "[" not in after_mn:
            # Old style: jump label, br.nz rd, label, etc.
            violations.append(Violation(filepath, lineno, "R2(跳转缺[])", stripped))
        else:
            # Has [...], check additional constraints
            # br.*: conditions must use {...}?
            if mnemonic.startswith("br."):
                if "{" not in after_mn or "}?" not in after_mn:
                    violations.append(Violation(
                        filepath, lineno,
                        "R2(条件缺{...}?)", stripped
                    ))

    # R2b: cs.* conditions must use {...}? (no [...] needed)
    if _CS_RE.match(code_part):
        after_mn = code_part[len(mnemonic):].strip()
        if "{" not in after_mn or "}?" not in after_mn:
            violations.append(Violation(
                filepath, lineno,
                "R2(条件缺{...}?)", stripped
            ))

    # R2': Byte-offset alignment for jump/call/br.*/escape
    # Numeric offsets in [...] must be %4==0 (byte-addressed instruction stream).
    # Symbolic offsets (labels) are NOT checked.
    # ld.*/st.* offsets are NOT checked (imms12, no alignment requirement).
    if mnemonic in ("jump", "call", "escape") or mnemonic.startswith("br."):
        if "[" in code_part:
            for bracket_match in re.finditer(r"\[([^\]]+)\]", code_part):
                bracket_content = bracket_match.group(1)
                parts = [p.strip() for p in bracket_content.split(",")]
                # Check last part (offset): must be numeric AND %4==0
                if parts:
                    offset_val = parts[-1]
                    num = None
                    # Decimal integer (explicit base 10 to reject leading zeros like '06')
                    m_dec = re.match(r"^(-?\d+)$", offset_val)
                    if m_dec:
                        num = int(offset_val, 10)
                    else:
                        # Hex integer (0x prefix)
                        m_hex = re.match(r"^(-?0x[\da-fA-F]+)$", offset_val, re.I)
                        if m_hex:
                            num = int(offset_val, 16)
                    if num is not None and num % 4 != 0:
                        violations.append(Violation(
                            filepath, lineno,
                            "R2'(偏移非4倍数)", stripped
                        ))

    # R3: cfx2rd/cfx2rc shape
    if mnemonic in ("cfx2rd", "cfx2rc"):
        after_mn = code_part[len(mnemonic):].strip()
        if not _is_cfx_long_form(after_mn) and not _is_cfx_alias_form(after_mn, cfx_aliases, cfx_ranges):
            violations.append(Violation(filepath, lineno, "R3(cfx操作数形)", stripped))

    # R5: ldm/stm with old-style count
    if mnemonic.startswith("ldm.") or mnemonic.startswith("stm."):
        after_mn = code_part[len(mnemonic):].strip()
        # Old style: rdN, rbN, rdN, count  (no {}, no [])
        # New style: {rdN:rdM}, [rbN, rdN]
        if "{" not in after_mn:
            violations.append(Violation(filepath, lineno, "R5(多寄存器缺{})", stripped))

    # R6: Operand shape from opcodes.yaml — data-driven.
    # For mnemonics with known formats, check if operand count matches any valid format.
    # Additionally, when the mnemonic has an rrrr variant, require {…} (dual-dst or condition).
    # Only flag when the mnemonic is in opcodes.yaml AND (count doesn't match OR rrrr needs {}).
    if mnemonic in opcode_formats:
        after_mn = code_part[len(mnemonic):].strip()
        formats = opcode_formats[mnemonic]
        valid_counts = _get_valid_operand_counts(formats)
        if valid_counts:
            actual_count = _count_operands(after_mn)
            if actual_count not in valid_counts:
                violations.append(Violation(
                    filepath, lineno,
                    "R6(操作数形态不符)", stripped
                ))
            elif "rrrr" in formats and "{" not in after_mn and actual_count >= 3:
                # mnemonic has rrrr variant (dual-dst / cs), which requires {…}
                # Old form: add.so rd0, rd4, rd2, rd3 (4 bare regs)
                # New form: add.so {rdHA, rdHB}, rdHC, rdHD
                # Exception: if mnemonic ALSO has orrr variant, 3-operands without {}
                # is valid (orrr address arithmetic). Only flag when count matches rrrr
                # specifically AND there's no orrr variant accepting this count.
                orrr_counts = _FORMAT_OP_COUNTS.get("orrr", set())
                if actual_count not in orrr_counts:
                    violations.append(Violation(
                        filepath, lineno,
                        "R6(rrrr缺{})", stripped
                    ))

    # R6b: Block-copy / format-convert (ra2rd, rb2rb, etc. and ft2fo, etc.)
    # These are orri format with immu6 = count
    # Old: ra2rd rd8, ra1, 3  (3 operands)
    # New: ra2rd {rd8:rd10}, {ra1:ra3}
    _BLOCK_COPY_RE = re.compile(
        r"^\s*"
        r"(ra2rd|rb2rb|rb2rd|rd2ra|rd2rb|rd2rd|rd2rf|rf2rd"
        r"|ft2fo|fo2ft|ft2ut|ut2ft|ft2uo|uo2ft|ft2so|so2ft"
        r"|fo2ut|ut2fo|fo2uo|uo2fo|fo2so|so2fo"
        r"|ut2uo|uo2ut|ut2so|so2ut"
        r"|uo2so|so2uo)"
        r"\s"
    )
    if _BLOCK_COPY_RE.match(code_part):
        after_mn = code_part[len(mnemonic):].strip()
        if "{" not in after_mn:
            violations.append(Violation(filepath, lineno, "R6(块复制/格式转换缺{})", stripped))

    # R4 (inline): Check for # used as inline comment (after an instruction)
    # e.g. "set.rd rd2, 0  # loop variable"
    # Only check in assembly blocks; require a recognized mnemonic before #
    if is_asm_block and ";" not in stripped and "#" in stripped:
        # Must have a recognized mnemonic-like token before #
        # Match: word.word (instruction mnemonic) followed by operands then #
        m = re.search(r"\s#", stripped)
        if m:
            before_hash = stripped[:m.start()]
            # Check if there's an instruction mnemonic (word.word pattern) before
            if re.match(r"^[a-zA-Z][\w]*\.[\w]+", before_hash):
                violations.append(Violation(filepath, lineno, "R4(行内#注释)", stripped))

    return violations

# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan(
    opcode_formats: dict[str, set[str]],
    cfx_aliases: set[str],
    cfx_ranges: dict[str, tuple[int, int]] = {},
    root: Path | None = None,
) -> list[Violation]:
    """Scan all files in scope and return violations."""
    violations: list[Violation] = []
    for filepath in collect_files(root):
        blocks = extract_code_blocks(filepath)
        for block in blocks:
            # Only check assembly blocks (simrisc, asm, or empty lang)
            # Non-assembly blocks (python, yaml, c, etc.) are skipped
            is_asm_block = block.lang.lower() in ("simrisc", "asm", "")
            for i, line in enumerate(block.lines):
                vl = _check_line(
                    line,
                    block.start_line + i,
                    filepath,
                    opcode_formats,
                    cfx_aliases,
                    cfx_ranges,
                    is_asm_block=is_asm_block,
                )
                violations.extend(vl)
    return violations

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _relpath(p: Path) -> str:
    """Relative path from effective root (repo root or --root override)."""
    effective = _override_root if _override_root else ROOT
    try:
        return str(p.relative_to(effective))
    except ValueError:
        return str(p)

def report(violations: list[Violation]) -> None:
    """Print violation report grouped by file."""
    # Summary
    rule_counts: dict[str, int] = {}
    for v in violations:
        rule_counts[v.rule] = rule_counts.get(v.rule, 0) + 1

    if not violations:
        print("check-asm-prose: PASS (0 violations)")
        return

    print(f"check-asm-prose: {len(violations)} violation(s) found")
    print()
    print("--- violation list ---")
    current_file = None
    for v in violations:
        rel = _relpath(v.file)
        if rel != current_file:
            current_file = rel
            print(f"\n{rel}:")
        print(f"  L{v.line}: [{v.rule}] {v.original}")

    print()
    print("--- rule hit statistics ---")
    for rule, count in sorted(rule_counts.items()):
        print(f"  {rule}: {count}")
    print(f"  total: {len(violations)}")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 if any violation is found (for CI gating).",
    )
    parser.add_argument(
        "--files", nargs="*",
        help="Only check these files (relative to repo root or --root).",
    )
    parser.add_argument(
        "--root", type=str, default=None,
        help="Override scan root directory (default: repo root).",
    )
    args = parser.parse_args()

    root_override: Path | None = None
    if args.root:
        root_override = Path(args.root).resolve()
        if not root_override.is_dir():
            print(f"ERROR: --root directory does not exist: {root_override}", file=sys.stderr)
            sys.exit(1)
        # Set module-level override for _relpath()
        global _override_root
        _override_root = root_override

    opcode_formats = _load_opcode_formats()
    cfx_aliases, cfx_ranges = _load_cfx_aliases()
    had_out_of_scope = False

    # Effective root for --files resolution
    effective_root = root_override if root_override else ROOT

    if args.files:
        # Filter to specific files — fail-closed
        target_files = {(effective_root / f).resolve() for f in args.files}
        in_scope = {fp.resolve() for fp in collect_files(root_override)}
        out_of_scope = target_files - in_scope
        for tf in sorted(out_of_scope, key=str):
            print(f"ERROR: --files argument outside scan scope: {tf}", file=sys.stderr)
        violations: list[Violation] = []
        for filepath in collect_files(root_override):
            if filepath.resolve() not in target_files:
                continue
            blocks = extract_code_blocks(filepath)
            for block in blocks:
                is_asm_block = block.lang.lower() in ("simrisc", "asm", "")
                for i, line in enumerate(block.lines):
                    vl = _check_line(
                        line,
                        block.start_line + i,
                        filepath,
                        opcode_formats,
                        cfx_aliases,
                        cfx_ranges,
                        is_asm_block=is_asm_block,
                    )
                    violations.extend(vl)
        had_out_of_scope = bool(out_of_scope)
    else:
        violations = scan(opcode_formats, cfx_aliases, cfx_ranges, root_override)

    if had_out_of_scope:
        # --files contained paths outside the scan scope: fail-closed.  Do not
        # print PASS (0 violations) here, or stdout would contradict the exit
        # code; emit an explicit FAIL marker instead.
        print("check-asm-prose: FAIL (out-of-scope --files)")
    if violations or not had_out_of_scope:
        # report() prints PASS when clean.  Skip it only on the out-of-scope
        # clean path, where the FAIL marker above must stand alone; still call
        # it to list violations when there are any.
        report(violations)

    if (args.strict and violations) or had_out_of_scope:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
