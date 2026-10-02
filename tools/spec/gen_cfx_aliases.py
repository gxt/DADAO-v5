#!/usr/bin/env python3
"""Generate ``docs/spec/cfx-aliases.md`` from spec cfx tables.

Sources
-------
* ``spec/DADAO-12-SEE-主管系统运行环境.md`` -- cfxha↔cfxname table + cg0-7 tables
* ``spec/DADAO-13-HEE-超管系统运行环境.md`` -- cg3 (hypv) table

Two alias types per ADR-0017 D3/D4:
  1. **Scalar**: ``cfx_<cfxname>``  ⇔  ``cfx<code>``
  2. **Register**: ``cfx_<cfxname>_<tail>``  ⇔  ``(cfxha, cg, rc)``

Generic registers (cg0-7, regname contains ``⟨cfxname⟩``) are expanded
for each non-reserved cfxname.  cfx-specific registers (cg8+, no placeholder)
are included verbatim.  Range-indexed registers (``[0..63]`` etc.) are
**not** expanded.

Usage
-----
* Generate:  ``python3 tools/spec/gen_cfx_aliases.py``
* Verify:    ``python3 tools/spec/gen_cfx_aliases.py --verify``
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_D12 = ROOT / "spec/DADAO-12-SEE-主管系统运行环境.md"
SPEC_D13 = ROOT / "spec/DADAO-13-HEE-超管系统运行环境.md"
OUTPUT = ROOT / "docs/spec/cfx-aliases.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_cfxcode_table(text: str) -> dict[str, int]:
    """Parse cfxha↔cfxname table → {cfxname: cfxha} (non-reserved only)."""
    result: dict[str, int] = {}
    in_table = False
    header_seen = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table and header_seen:
                break  # end of table
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        if cells[0] in ("cfxcode", "cfxha") and cells[1] == "cfxname":
            in_table = True
            header_seen = True
            continue
        if not in_table:
            continue
        if cells[1] == "reserved":
            continue
        # Handle range cfxcodes (e.g. "19-61")
        code_str = cells[0]
        if "-" in code_str and not code_str.startswith("0x"):
            continue  # range → reserved
        try:
            code = int(code_str)
        except ValueError:
            continue
        name = cells[1]
        result[name] = code
    return result


def parse_register_tables(text: str, source_file: str) -> list[dict]:
    """Parse all cg/rc/regname tables → list of {cg, rc, tail, source, line}.

    * Skips rows where regname is ``—``, ``...``, contains ``reserved``,
      or contains range brackets (``0-(N−1)`` etc.) -- those are
      variable-size or placeholder rows.
    * Keeps ``[0..63]`` style rows as-is (not expanded).
    * For regname containing ``⟨cfxname⟩``, extracts the tail after the
      placeholder.
    """
    entries: list[dict] = []
    in_table = False
    header_seen = False

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table and header_seen:
                in_table = False
                header_seen = False
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        # Detect table header
        if cells[0] == "cg" and cells[1] == "rc":
            in_table = True
            header_seen = True
            continue
        if not in_table:
            continue
        # Skip separator rows
        if all(set(c) <= {":", "-", " "} for c in cells[:4]):
            continue
        cg_str = cells[0]
        rc_str = cells[1]
        regname = cells[3]
        # Skip reserved/placeholder/range-of-variable rows
        if regname in ("—", "...", ""):
            continue
        if "reserved" in regname.lower():
            continue
        # Skip variable-size range (e.g. "0-(N−1)")
        if re.search(r"\d+-\(.*\)", rc_str):
            continue
        # Parse rc (may be range like "0-63" or "8-15")
        # Keep as string for range values
        # Parse cg
        try:
            cg = int(cg_str)
        except ValueError:
            continue
        # Determine tail: remove ``cfx_⟨cfxname⟩_`` prefix or ``cfx_<name>_`` prefix
        placeholder = "cfx_⟨cfxname⟩_"
        if placeholder in regname:
            tail = regname[len(placeholder):]
            is_generic = True
        else:
            # cfx-specific: extract tail after ``cfx_<cfxname>_``
            m = re.match(r"cfx_([a-z]+)_(.+)", regname)
            if m:
                tail = m.group(2)
            else:
                tail = regname
            is_generic = False
        entries.append({
            "cg": cg,
            "rc": rc_str,
            "tail": tail,
            "regname": regname,
            "is_generic": is_generic,
            "source": f"{source_file}:{lineno}",
        })
    return entries


def build_scalar_aliases(cfx_map: dict[str, int]) -> list[tuple[str, str, int]]:
    """Build scalar aliases: (alias, code_str, cfxcode)."""
    result = []
    for name, code in sorted(cfx_map.items(), key=lambda x: x[1]):
        alias = f"cfx_{name}"
        code_str = f"cfx{code}"
        result.append((alias, code_str, code))
    return result


def build_register_aliases(
    entries: list[dict],
    cfx_map: dict[str, int],
) -> list[tuple[str, int, int, str, str]]:
    """Build register aliases: (alias, cfxha, cg, rc, source).

    For generic entries (containing ⟨cfxname⟩), expand for each non-reserved cfxname.
    For cfx-specific entries, use the cfxname extracted from the regname.
    """
    result: list[tuple[str, int, int, str, str]] = []
    for entry in entries:
        if entry["is_generic"]:
            # Expand for each non-reserved cfxname
            for cfxname, cfxcode in sorted(cfx_map.items(), key=lambda x: x[1]):
                alias = f"cfx_{cfxname}_{entry['tail']}"
                result.append((alias, cfxcode, entry["cg"], entry["rc"], entry["source"]))
        else:
            # cfx-specific: extract cfxname from regname
            m = re.match(r"cfx_([a-z]+)_", entry["regname"])
            if m:
                cfxname = m.group(1)
                if cfxname in cfx_map:
                    cfxha = cfx_map[cfxname]
                    alias = f"cfx_{cfxname}_{entry['tail']}"
                    result.append((alias, cfxha, entry["cg"], entry["rc"], entry["source"]))
    return result


def render_markdown(
    scalar_aliases: list[tuple[str, str, int]],
    register_aliases: list[tuple[str, int, int, str, str]],
    cfx_map: dict[str, int],
    generic_entries: list[dict],
    specific_entries: list[dict],
) -> str:
    """Render the cfx-aliases.md content."""
    lines: list[str] = []
    lines.append("# cfx 别名表")
    lines.append("")
    lines.append("<!-- AUTO-GENERATED by tools/spec/gen_cfx_aliases.py — DO NOT EDIT -->")
    lines.append("")
    lines.append("本文档由生成器从 spec 寄存器表机械生成。**禁止手工维护** ✗。")
    lines.append("")
    lines.append("生成来源：")
    lines.append(f"- `spec/DADAO-12-SEE-主管系统运行环境.md`（cfxha↔cfxname 表 + cg0-7/cg4-7 寄存器表 + 各 cfx 专有寄存器表）")
    lines.append(f"- `spec/DADAO-13-HEE-超管系统运行环境.md`（cg3 hypv 寄存器表）")
    lines.append(f"- 生成器：`tools/spec/gen_cfx_aliases.py`")
    lines.append("")
    lines.append("映射规则见 `ADR-0017`（D3 标量别名、D4 寄存器别名查表、D8 机械生成、D9 独立生成附录）。")
    lines.append("")

    # Scalar aliases
    lines.append("## 1. 标量别名（`cfx_<cfxname>` ⇔ `cfx<code>`）")
    lines.append("")
    lines.append("Per ADR-0017 D3：`cfx_<cfxname>` 是 `cfxHA` 的宏别名。")
    lines.append("")
    lines.append("| 别名 | cfxha | cfxname |")
    lines.append("|------|---------|---------|")
    for alias, code_str, code in scalar_aliases:
        cfxname = alias[4:]  # remove "cfx_" prefix
        lines.append(f"| `{alias}` | `{code}` | {cfxname} |")
    lines.append("")

    # Register aliases — generic
    lines.append("## 2. 寄存器别名（`cfx_<cfxname>_<tail>` ⇔ `(cfxha, cg, rc)`）")
    lines.append("")
    lines.append("Per ADR-0017 D4：寄存器别名查 spec 寄存器表的 `cg`/`rc` 列。")
    lines.append("")
    lines.append("### 2.1 通用寄存器（cg0-7，所有 cfx 共有）")
    lines.append("")
    lines.append("以下模板适用于**所有非保留 cfx**（`⟨cfxname⟩` 由各 cfxname 替换）。")
    lines.append("")
    lines.append("| 别名模板 | cg | rc | 说明 |")
    lines.append("|----------|----|----|------|")
    for entry in generic_entries:
        lines.append(f"| `cfx_⟨cfxname⟩_{entry['tail']}` | {entry['cg']} | {entry['rc']} | — |")
    lines.append("")
    lines.append("展开后共 {} cfxname × {} 模板 = {} 条目。".format(
        len(cfx_map), len(generic_entries), len(cfx_map) * len(generic_entries)))
    lines.append("")

    # Register aliases — cfx-specific
    lines.append("### 2.2 专有寄存器（cg8+，各 cfx 独有）")
    lines.append("")
    lines.append("| 别名 | cfxha | cg | rc | 来源 |")
    lines.append("|------|-------|----|----|------|")
    # Group by cfxname for readability
    current_cfx = None
    for alias, cfxha, cg, rc, source in register_aliases:
        # Check if this is a specific (non-generic) entry
        cfxname = alias.split("_")[1]
        if cfxname != current_cfx:
            current_cfx = cfxname
        lines.append(f"| `{alias}` | {cfxha} | {cg} | {rc} | {source} |")
    lines.append("")

    # Statistics
    total_register = len(register_aliases) + len(cfx_map) * len(generic_entries)
    lines.append("## 3. 统计")
    lines.append("")
    lines.append(f"- 标量别名：{len(scalar_aliases)} 条")
    lines.append(f"- 寄存器别名（展开后）：{total_register} 条")
    lines.append(f"  - 通用（cg0-7 展开）：{len(cfx_map)} × {len(generic_entries)} = {len(cfx_map) * len(generic_entries)} 条")
    lines.append(f"  - 专有（cg8+）：{len(register_aliases)} 条")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    verify = "--verify" in sys.argv

    # 1. Parse sources
    d12_text = read_file(SPEC_D12)
    d13_text = read_file(SPEC_D13)

    cfx_map = parse_cfxcode_table(d12_text)
    assert len(cfx_map) >= 10, f"Expected ≥10 cfxnames, got {len(cfx_map)}: {cfx_map}"

    generic_entries = parse_register_tables(d12_text, "DADAO-12") + \
                      parse_register_tables(d13_text, "DADAO-13")
    # Separate generic vs specific
    generic_only = [e for e in generic_entries if e["is_generic"]]
    specific_only = [e for e in generic_entries if not e["is_generic"]]

    # 2. Build aliases
    scalar_aliases = build_scalar_aliases(cfx_map)
    register_aliases = build_register_aliases(specific_only, cfx_map)

    # 3. Render
    content = render_markdown(
        scalar_aliases, register_aliases, cfx_map,
        generic_only, specific_only,
    )

    if verify:
        existing = read_file(OUTPUT)
        if existing == content:
            print(f"check-cfx-aliases: PASS (byte-identical)")
            sys.exit(0)
        else:
            # Show diff summary
            existing_lines = existing.splitlines()
            new_lines = content.splitlines()
            print(f"check-cfx-aliases: MISMATCH ({len(existing_lines)} vs {len(new_lines)} lines)")
            for i, (a, b) in enumerate(zip(existing_lines, new_lines)):
                if a != b:
                    print(f"  line {i+1}: expected {b!r}")
                    print(f"  line {i+1}: got      {a!r}")
                    break
            sys.exit(1)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8")
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        print(f"gen_cfx_aliases: wrote {OUTPUT} ({len(scalar_aliases)} scalar, "
              f"{len(specific_only)} specific registers, "
              f"{len(generic_only)} generic templates × {len(cfx_map)} cfxnames)")
        print(f"  sha256: {sha}")


if __name__ == "__main__":
    main()
