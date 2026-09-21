#!/usr/bin/env python3
"""check_lit_bytes.py — lit # OBJ: 字节 ↔ contracts/opcodes.yaml 独立校验。

遍历 tests/lit/MC/Dadao/*.s，提取 `# OBJ:` 行的 4 字节 + mnemonic，
在 contracts/opcodes.yaml 中查找 (word & mask) == value 的记录。

纯 Python + yaml；只读；不运行 LLVM 工具。

Exit 0: N patterns OK（N > 0 且 N == 独立计数）
Exit 1: 无匹配 / mnemonic 不匹配 / N == 0 / N != 独立计数
"""

import glob
import os
import re
import sys

import yaml

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIT_DIR = os.path.join(REPO_ROOT, "tests", "lit", "MC", "Dadao")
OPCODES_YAML = os.path.join(REPO_ROOT, "contracts", "opcodes.yaml")

# P1: mnemonic 提取遇 {{ 即停
# FileCheck 模式字面量：{{[0-9a-f]+:}} 和 {{.*}} 需逐字符转义
OBJ_RE = re.compile(
    r"#\s*OBJ:\s+\{\{\[0-9a-f\]\+:\}\}\s+"
    r"([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})"
    r"\{\{.*?\}\}"
    r"([A-Za-z][A-Za-z0-9._]*)"
)

# P2: 独立宽松计数 — 按 `# OBJ:` 字面出现次数
OBJ_LITERAL_RE = re.compile(r"#\s*OBJ:")


def load_opcodes(path: str) -> list[dict]:
    with open(path) as f:
        entries = yaml.safe_load(f)
    result = []
    for entry in entries:
        mask = int(entry["mask"], 16)
        value = int(entry["value"], 16)
        result.append({
            "insn": entry["insn"],
            "mnemonic": entry["mnemonic"],
            "mask": mask,
            "value": value,
        })
    return result


def find_match(word: int, opcodes: list[dict]) -> list[dict]:
    """返回所有 (word & mask) == value 的记录。"""
    return [e for e in opcodes if (word & e["mask"]) == e["value"]]


def main() -> int:
    opcodes = load_opcodes(OPCODES_YAML)

    lit_files = sorted(glob.glob(os.path.join(LIT_DIR, "*.s")))
    if not lit_files:
        print("check_lit_bytes: ERROR — no .s files found", file=sys.stderr)
        return 1

    # P2: 独立宽松计数
    independent_count = 0
    for fpath in lit_files:
        with open(fpath) as f:
            for line in f:
                if OBJ_LITERAL_RE.search(line):
                    independent_count += 1

    errors: list[str] = []
    n_matched = 0
    op_only_masks = 0

    for fpath in lit_files:
        fname = os.path.basename(fpath)
        with open(fpath) as f:
            for lineno, line in enumerate(f, 1):
                m = OBJ_RE.search(line)
                if not m:
                    continue
                b0, b1, b2, b3, mnemonic = m.groups()
                hex_str = b0 + b1 + b2 + b3
                word = int(hex_str, 16)

                matches = find_match(word, opcodes)
                if not matches:
                    errors.append(
                        f"  {fname}:{lineno}: word=0x{word:08X} — no match in opcodes.yaml"
                    )
                    continue
                if len(matches) > 1:
                    insns = [e["insn"] for e in matches]
                    errors.append(
                        f"  {fname}:{lineno}: word=0x{word:08X} — multiple matches: {insns}"
                    )
                    continue

                hit = matches[0]
                if mnemonic != hit["mnemonic"]:
                    errors.append(
                        f"  {fname}:{lineno}: mnemonic '{mnemonic}' != "
                        f"'{hit['mnemonic']}' (insn={hit['insn']})"
                    )
                    continue

                n_matched += 1
                # informational: mask 仅盖 op 字段
                if hit["mask"] == 0xFF000000:
                    op_only_masks += 1

    # P2: N == 独立计数
    if n_matched != independent_count:
        errors.append(
            f"  N ({n_matched}) != independent count ({independent_count})"
        )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    if n_matched == 0:
        print("check_lit_bytes: ERROR — N == 0 (no patterns extracted)", file=sys.stderr)
        return 1

    print(f"check_lit_bytes: {n_matched} patterns OK")
    if op_only_masks:
        print(f"  (info: {op_only_masks}/{n_matched} masks cover op-field only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
