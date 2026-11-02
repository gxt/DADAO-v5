#!/usr/bin/env python3
"""Permanent gate for ```simrisc prose code blocks in ``spec/`` (SPEC-103t / ISS-077).

Why
---
Before this gate the only permanent check on the new assembly syntax in spec
prose was ``check_asm_prose.py`` (ADR-0013 old-format rules).  It does **not**
verify that every instruction line matches the generated instruction table, so
a typo'd / removed mnemonic or a wrong operand shape could silently survive in
the 12 chapters.  This gate closes that gap.

Source of truth
---------------
``contracts/opcodes.yaml`` — the authoritative encoding table (projected into
the generated asm-list by ``tools/llvm/gen_asm_list.py``).  The mnemonic set and
the valid operand counts are read from ``opcodes.yaml``; nothing is hardcoded
except the small assembler **pseudo-instruction exception table** below.

Checks (per instruction line in a ```simrisc block)
---------------------------------------------------
* label / comment / directive / empty lines are skipped;
* pseudo-instruction lines are exempt from both checks (their expansion is what
  the real instruction table governs);
* the mnemonic MUST be a real instruction in ``contracts/opcodes.yaml``;
* the operand count MUST match at least one ``format`` variant of that
  instruction (reusing the format→count table from ``check_asm_prose``).

Contract projection check (INFRA-103t)
--------------------------------------
``.tao/contracts/contract-isa.md`` 的「伪指令」小节表格只允许保留的 8 条
合成型伪指令（``PSEUDO_INSTRUCTIONS``）；把已删除的 1:1 别名（``not.o`` /
``neg.o`` / ``return`` / ``nop`` …）塞回表格 ⇒ FAIL（标题带「已删除」的小节按
历史注记处理）。这是 ``ISS-160``/``ISS-329`` 的可达 FAIL 路径。

Scan scope
----------
``spec/**/*.md``.  Generated
regions (``<!-- ASSEMBLY_LIST_* -->`` / ``<!-- LEGALITY_* -->``) are skipped by
``extract_code_blocks`` — their truth is gated by ``check-asm-list`` /
``check-legality-drift``.

Usage
-----
* ``python3 tools/spec/check_spec_codeblocks.py``           # scan repo spec/
* ``python3 tools/spec/check_spec_codeblocks.py --root DIR``# scan all *.md under DIR (fixtures)

Exit 0 = all lines valid; exit 1 = at least one violation.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.spec.check_asm_prose import (  # noqa: E402
    _count_operands,
    _get_valid_operand_counts,
    _load_opcode_formats,
    extract_code_blocks,
)

SPEC_DIR = ROOT / "spec"

# Assembler pseudo-instructions (SimRISC-00: 伪指令 / spec/Toolchain-01: 伪指令).
# These are expanded by the assembler into real instructions, so they are
# exempt from the opcodes.yaml lookup and the operand-count check.
# 合法伪指令（权威定义 = `spec/Toolchain-01 §6`；`ADR-0013 D11` 只保留 8 条合成型
# = 4 个助记符 × 2 种形态）。`nop`/`return`/`not.*`/`neg.*` 已删除，不再放行。
PSEUDO_INSTRUCTIONS = frozenset({
    "set.rd", "set.rb", "set.ft", "set.fo",
})

_MNEMONIC_RE = re.compile(r"^[a-z][a-z0-9_.]*$")

# `contract-isa.md` 的「伪指令」小节表格：第一列必须是保留的伪指令。
CONTRACT_ISA = ROOT / ".tao/contracts/contract-isa.md"
_PSEUDO_HEADING_RE = re.compile(r"^(#{2,6})\s+.*伪指令")
_TABLE_ROW_RE = re.compile(r"^\|\s*`([a-z][a-z0-9_.]*)[\s`{]")


def scan_contract_pseudo_instructions(
    contract: Path | None = None,
) -> list[str]:
    """契约「伪指令」表格只能列保留的 8 条（`ADR-0013 D11`）。

    这是 `ISS-160`/`ISS-329` 的可达 FAIL 路径：把已删除的 1:1 别名（`not.o`/
    `neg.o`/`return`/`nop` …）塞回 `contract-isa` 的「伪指令」小节 ⇒ FAIL。
    标题带「已删除」的小节按历史注记处理（不解析表格）。
    """
    path = contract if contract is not None else CONTRACT_ISA
    if not path.is_file():
        return [f"{path}: 契约文件缺失（fail-closed）"]
    violations: list[str] = []
    in_pseudo = False
    heading_level = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = _PSEUDO_HEADING_RE.match(line)
        if m:
            in_pseudo = "已删除" not in line
            heading_level = len(m.group(1))
            continue
        if not in_pseudo:
            continue
        h = re.match(r"^(#{1,6})\s+", line)
        if h and len(h.group(1)) <= heading_level:
            in_pseudo = False
            continue
        row = _TABLE_ROW_RE.match(line)
        if row and row.group(1) not in PSEUDO_INSTRUCTIONS:
            violations.append(
                f"{path}:{lineno}: 伪指令表中的 '{row.group(1)}' 不在保留集合 "
                f"{sorted(PSEUDO_INSTRUCTIONS)}（`ADR-0013 D11` 已删除该别名）"
            )
    return violations


def collect_files(root: Path | None = None) -> list[Path]:
    """Collect markdown files to scan.

    *root* given ⇒ every ``*.md`` under it (fixture mode).
    Otherwise scan ``spec/**/*.md``.
    """
    if root is not None:
        return sorted(root.rglob("*.md"))
    return sorted(SPEC_DIR.rglob("*.md"))


def _relpath(p: Path, effective: Path) -> str:
    try:
        return str(p.relative_to(effective))
    except ValueError:
        return str(p)


def check_line(
    line: str,
    filepath: Path,
    lineno: int,
    opcode_formats: dict[str, set[str]],
) -> tuple[list[str], bool]:
    """Return (violations, is_instruction) for one code-block line.

    ``is_instruction`` is True when the line carried a mnemonic that the gate
    actually validated (i.e. a real or pseudo instruction, not a label/comment).
    """
    violations: list[str] = []
    stripped = line.strip()

    # Skip empty / comment / directive / label lines.
    if not stripped:
        return violations, False
    if stripped.startswith((";", "//", "#")):
        return violations, False
    if stripped.endswith(":"):
        return violations, False

    code = stripped.split(";")[0].strip()  # strip inline ; comments
    if not code:
        return violations, False

    tokens = code.split()
    mnemonic = tokens[0].lower()
    if not _MNEMONIC_RE.match(mnemonic):
        return violations, False

    # Pseudo-instructions: exempt (expansion is governed by real instructions).
    if mnemonic in PSEUDO_INSTRUCTIONS:
        return violations, True

    if mnemonic not in opcode_formats:
        violations.append(
            f"{filepath}:{lineno}: 未知助记符 '{mnemonic}'（不在 contracts/opcodes.yaml）"
        )
        return violations, True

    after_mn = code[len(tokens[0]):].strip()
    valid_counts = _get_valid_operand_counts(opcode_formats[mnemonic])
    if valid_counts:
        actual = _count_operands(after_mn)
        if actual not in valid_counts:
            violations.append(
                f"{filepath}:{lineno}: '{mnemonic}' 操作数个数 {actual} "
                f"不在合法集合 {sorted(valid_counts)}（format {sorted(opcode_formats[mnemonic])}）"
            )
    return violations, True


def scan(
    opcode_formats: dict[str, set[str]],
    root: Path | None = None,
) -> tuple[list[str], int]:
    """Return (violations, instruction_line_count)."""
    effective = root if root is not None else ROOT
    violations: list[str] = []
    scanned = 0
    for filepath in collect_files(root):
        for block in extract_code_blocks(filepath):
            if block.lang.lower() != "simrisc":
                continue
            for i, line in enumerate(block.lines):
                rel = _relpath(filepath, effective)
                vl, is_insn = check_line(
                    line,
                    Path(rel),
                    block.start_line + i,
                    opcode_formats,
                )
                if is_insn:
                    scanned += 1
                violations.extend(vl)
    return violations, scanned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=str, default=None,
        help="Scan all *.md under this directory (fixture mode) instead of repo spec/.",
    )
    args = parser.parse_args()

    root_override: Path | None = None
    if args.root:
        root_override = Path(args.root).resolve()
        if not root_override.is_dir():
            print(f"check-spec-codeblocks: ERROR --root not a directory: {root_override}",
                  file=sys.stderr)
            return 1

    opcode_formats = _load_opcode_formats()
    if not opcode_formats:
        # Fail closed: without the truth source we cannot validate anything.
        print("check-spec-codeblocks: ERROR cannot load contracts/opcodes.yaml "
              "(mnemonic table empty)", file=sys.stderr)
        return 1

    violations, scanned = scan(opcode_formats, root_override)
    if root_override is None:
        # 契约投影层（非 fixture 模式）：伪指令表不得列已删除别名。
        contract_violations = scan_contract_pseudo_instructions()
        violations.extend(contract_violations)
    if violations:
        for v in violations:
            print(f"FAIL: {v}", file=sys.stderr)
        print(f"check-spec-codeblocks: FAIL ({len(violations)} violation(s) "
              f"in {scanned} instruction line(s))", file=sys.stderr)
        return 1

    print(f"check-spec-codeblocks: PASS ({scanned} instruction line(s) checked "
          f"against contracts/opcodes.yaml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
