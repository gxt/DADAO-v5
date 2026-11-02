#!/usr/bin/env python3
"""Emit the DADAO cfx alias **runtime table** ``contracts/cfx-aliases.txt``.

See ``.tao/contracts/contract-cfx-aliases.md`` (generated) for the alias
contract and ``ADR-0017`` D3/D4/D8/D10 for the decisions.

The aliases are *data*, not code (LLVM-135t): the assembler and the
MCInstPrinter both read this one text file at run time, so renaming a cfx or
renumbering its registers is a data update -- no LLVM rebuild.

The content is derived from the *same* spec sources as
``tools/spec/gen_cfx_aliases.py`` -- the committed projector whose output
``.tao/contracts/contract-cfx-aliases.md`` is drift-gated by
``tools/spec/check_cfx_aliases.py``.  This script reuses that projector's
functions verbatim, so the runtime table cannot drift from the v5 contract.

Table grammar (``format=2``; consumed by
``llvm/lib/Target/DADAO/MCTargetDesc/DADAOCfxAliasTable.cpp``; ``format=1``
tables remain readable for backward compatibility)::

    # format=2
    scalar <name> <cfxha> [canonical]
    reg    <name> <cfxha> <cg> <rc-base> <rc-count> [canonical]
    array  <name-base> <cfxha> <cg> <rc-base> <count> <stride> [canonical]

* ``scalar`` -- ``cfx_<cfxname>`` <=> ``cfx<code>`` (12 entries);
* ``reg``    -- contiguous register array (``rc = rc-base + N``, stride 1);
* ``array``  -- stride-indexed register array (``rc = rc-base + N*stride``);
  both are written ``name[N]`` (ADR-0017 D10);
* ``canonical`` -- preferred spelling when several names share an encoding
  (the printer picks canonical first, then the lexicographically first name).

The header ``regs=`` count is the *contract-level expanded alias count*
(``len(build_register_aliases(...))``: every array element counts once), not
the number of data rows.

Usage
-----
* Generate: ``python3 tools/llvm/gen_cfx_alias_table.py``
* Verify:   ``python3 tools/llvm/gen_cfx_alias_table.py --check``  (drift gate)
* Elsewhere: ``python3 tools/llvm/gen_cfx_alias_table.py --out /tmp/t.txt``
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.spec.gen_cfx_aliases import (  # noqa: E402
    SPEC_D12, SPEC_D13, build_register_aliases, build_scalar_aliases,
    parse_cfxcode_table, parse_register_tables, read_file,
)

DEFAULT_OUT = ROOT / "contracts" / "cfx-aliases.txt"
FORMAT_LINE = "# format=2"

RANGE_RE = re.compile(r"^(.*)\[(\d+)\.\.(\d+)\]$")
VARIABLE_RE = re.compile(r"^(.*)\[(\d+)\.\.\S*N\S*\]$")


def split_range(raw: str) -> tuple[str, int]:
    """'x[0..63]' -> ('x', 64); 'x[0..N-1]' -> ('x', 64); 'x' -> ('x', 1)."""
    m = RANGE_RE.match(raw)
    if m:
        name, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
        return name, hi - lo + 1
    m = VARIABLE_RE.match(raw)
    if m:
        return m.group(1), 64
    return raw, 1


def rc_base(rc: str) -> int:
    """Lower bound of the spec 'rc' column ('8-15' -> 8, '0-(N-1)' -> 0)."""
    m = re.match(r"^(\d+)", rc.strip())
    assert m, f"unparsed rc column {rc!r}"
    return int(m.group(1))


def alias_rows(entries: list[dict], cfx_map: dict[str, int]):
    """Yield one row per alias from the parsed register tables.

    Stride-indexed spec rows (``rc = 4i+K``) become a single ``array`` row
    (``name-base``, count, stride) -- not 16 concrete ``reg`` rows.  All other
    rows keep the historical ``reg`` shape (``name``, count from ``split_range``,
    stride 1).  Rows: ``(cfxha, cg, base, count, stride, name)``.
    """
    rows: list[tuple[int, int, int, int, int, str]] = []
    for entry in entries:
        if entry["is_generic"]:
            targets = sorted(cfx_map.items(), key=lambda x: x[1])
        else:
            m = re.match(r"cfx_([a-z]+)_", entry["regname"])
            if not m or m.group(1) not in cfx_map:
                continue
            targets = [(m.group(1), cfx_map[m.group(1)])]
        for cfxname, cfxha in targets:
            assert 0 <= cfxha <= 63, f"bad cfxha for cfx_{cfxname}: {cfxha}"
            assert 0 <= entry["cg"] <= 63, (
                f"bad cg for cfx_{cfxname}_{entry['tail']}: {entry['cg']}")
            if entry["stride"]:
                name = f"cfx_{cfxname}_{entry['array_base']}"
                base = entry["array_offset"]
                count = entry["expand_count"]
                stride = entry["stride"]
                assert 0 <= base < 64 and 1 <= count <= 64, (
                    f"bad array span for {name}: base={base} count={count}")
                assert base + (count - 1) * stride <= 63, (
                    f"array leaves the 6-bit space for {name}: "
                    f"{base}+({count}-1)*{stride}")
                rows.append((cfxha, entry["cg"], base, count, stride, name))
            else:
                alias = f"cfx_{cfxname}_{entry['tail']}"
                name, count = split_range(alias)
                base = rc_base(entry["rc"])
                assert 0 <= base < 64 and 1 <= count <= 64, (
                    f"bad rc span for {alias}: base={base} count={count}")
                assert base + count <= 64, (
                    f"rc span leaves the 6-bit space for {alias}: "
                    f"{base}+{count}")
                rows.append((cfxha, entry["cg"], base, count, 1, name))
    return rows


def render() -> tuple[str, int, int]:
    """Return (table_text, num_scalars, num_expanded_regs)."""
    d12 = read_file(SPEC_D12)
    d13 = read_file(SPEC_D13)
    cfx_map = parse_cfxcode_table(d12)
    entries = (parse_register_tables(d12, "DADAO-12")
               + parse_register_tables(d13, "DADAO-13"))
    scalars = build_scalar_aliases(cfx_map)
    # Contract-level expanded alias count (arrays count once per element).
    expanded = build_register_aliases(entries, cfx_map)

    scalar_rows: list[tuple[int, str]] = []
    for alias, _code_str, code in scalars:
        assert 0 <= code <= 63, f"cfxha out of range for {alias}: {code}"
        scalar_rows.append((code, alias))
    scalar_rows.sort()

    rows = alias_rows(entries, cfx_map)
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[5]))
    array_rows = [r for r in rows if r[4] != 1]
    reg_rows = [r for r in rows if r[4] == 1]
    # cg7 §3.8: exactly four stride-4 arrays of 16 elements per cfx.
    assert len(array_rows) == 4 * len(cfx_map), (
        f"expected {4 * len(cfx_map)} array rows, got {len(array_rows)}")
    assert all(r[3] == 16 and r[4] == 4 for r in array_rows), (
        "cg7 arrays must be count=16 stride=4")
    assert not any(re.search(r"_space_.*\[", r[5]) for r in reg_rows), (
        "literal-bracket space_* rows are superseded by 'array'")

    names = [a for _c, a in scalar_rows] + [r[5] for r in rows]
    assert len(names) == len(set(names)), "duplicate alias name in the table"
    assert sum(1 if r[4] == 1 else r[3] for r in rows) == len(expanded), (
        f"row expansion {sum(1 if r[4] == 1 else r[3] for r in rows)} "
        f"!= contract alias count {len(expanded)}")

    L: list[str] = []
    L.append(FORMAT_LINE)
    L.append("# DADAO cfx alias runtime table -- AUTO-GENERATED, DO NOT EDIT.")
    L.append("# Generator: tools/llvm/gen_cfx_alias_table.py "
             "(drift gate: --check)")
    L.append("# Projector: tools/spec/gen_cfx_aliases.py <- "
             "spec/DADAO-12-SEE-主管系统运行环境.md, "
             "spec/DADAO-13-HEE-超管系统运行环境.md")
    L.append("# Contract: .tao/contracts/contract-cfx-aliases.md "
             "(ADR-0017 D3/D4/D8/D10)")
    L.append("# Grammar: scalar <name> <cfxha> [canonical]")
    L.append("#          reg    <name> <cfxha> <cg> <rc-base> <rc-count> "
             "[canonical]")
    L.append("#          array  <name-base> <cfxha> <cg> <rc-base> <count> "
             "<stride> [canonical]")
    L.append("# Read at run time from <exe-dir>/../share/dadao/cfx-aliases.txt "
             "(or $DADAO_CFX_ALIAS_FILE / --dadao-cfx-alias=).")
    L.append(f"# scalars={len(scalar_rows)} regs={len(expanded)}")
    for code, alias in scalar_rows:
        L.append(f"scalar {alias} {code} canonical")
    for cfxha, cg, base, count, stride, name in rows:
        if stride == 1:
            L.append(f"reg {name} {cfxha} {cg} {base} {count} canonical")
        else:
            L.append(f"array {name} {cfxha} {cg} {base} {count} {stride} "
                     f"canonical")
    L.append("")

    return "\n".join(L), len(scalar_rows), len(expanded)


def report_drift(out: Path, expected: str, actual: str) -> None:
    exp_lines, act_lines = expected.splitlines(), actual.splitlines()
    print(f"gen_cfx_alias_table: DRIFT: {out} does not match the spec", file=sys.stderr)
    for idx in range(max(len(exp_lines), len(act_lines))):
        exp = exp_lines[idx] if idx < len(exp_lines) else "<missing line>"
        act = act_lines[idx] if idx < len(act_lines) else "<missing line>"
        if exp != act:
            print(f"  first difference at line {idx + 1}:", file=sys.stderr)
            print(f"    expected: {exp}", file=sys.stderr)
            print(f"    actual  : {act}", file=sys.stderr)
            break
    print("  regenerate with: python3 tools/llvm/gen_cfx_alias_table.py",
          file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="output path (default: contracts/cfx-aliases.txt)")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed table is up to date; never write")
    args = ap.parse_args(argv)

    text, n_scalar, n_reg = render()
    out = Path(args.out)

    if args.check:
        if not out.is_file():
            print(f"gen_cfx_alias_table: FAIL: {out} is missing", file=sys.stderr)
            return 1
        actual = out.read_text(encoding="utf-8")
        if actual != text:
            report_drift(out, text, actual)
            return 1
        print(f"gen_cfx_alias_table: OK {out} "
              f"({n_scalar} scalars, {n_reg} regs) -- in sync with spec")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"gen_cfx_alias_table: wrote {out} "
          f"({n_scalar} scalars, {n_reg} regs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
