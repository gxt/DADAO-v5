#!/usr/bin/env python3
"""Emit the DADAO LLVM ``DADAOCfxAlias.inc`` cfx alias lookup tables.

See ``.tao/knowledge/contract-cfx-aliases.md`` (generated) for the alias
contract and ``ADR-0017`` D3/D4/D8 (Toolchain-01 §13) for the decisions.

The tables are derived from the *same* spec sources as
``tools/spec/gen_cfx_aliases.py`` -- the committed projector whose output
``.tao/knowledge/contract-cfx-aliases.md`` is drift-gated by
``tools/spec/check_cfx_aliases.py``.  This script reuses that projector's
functions verbatim, so the C++ table cannot drift from the v5 alias contract.

Tables emitted
--------------
* scalar aliases   ``cfx_<cfxname>``            <=> ``cfx<code>``          (13)
* generic tails    ``cfx_<cfxname>_<tail>``     ->  ``(cg, rc)``           (66)
* specific aliases ``cfx_<cfxname>_<tail>``     ->  ``(cfxha, cg, rc)``    (34)

Array registers (ADR-0017 D10) carry RcCount > 1 and are indexed by the
single-subscript form ``cfx_<...>[N]`` (rc = RcBase + N).  The generic
``scratch_regs[0..N-1]`` row is variable-size (hardware N in [2,64]); it is
emitted with RcBase=0/RcCount=64 so any rc in 0..63 is accepted (the assembler
cannot know the per-cfx N).

The emitted file is ``#include``-d by ``DADAOAsmParser.cpp`` inside the
component worktree (``.work/source/llvm-project``); the committed patch
``components/llvm-project/patches/**/AsmParser/DADAOCfxAlias.inc.patch`` is
produced from it by ``tools/infra/make_patch.py`` (raw ``git diff``).  Hence
this generator ships with its product (see ``AGENTS.md``).

Usage
-----
* Generate:  ``python3 tools/llvm/gen_cfx_alias_table.py``
* Elsewhere: ``python3 tools/llvm/gen_cfx_alias_table.py --out /path/DADAOCfxAlias.inc``
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

DEFAULT_OUT = (ROOT / ".work" / "source" / "llvm-project" / "llvm" / "lib"
               / "Target" / "DADAO" / "AsmParser" / "DADAOCfxAlias.inc")

RANGE_RE = re.compile(r"^(.*)\[(\d+)\.\.(\d+)\]$")
VARIABLE_RE = re.compile(r"^(.*)\[(\d+)\.\.\S*N\S*\]$")


def split_range(raw: str) -> tuple[str, int, int]:
    """'x[0..63]' -> ('x', 0, 64); 'x[0..N-1]' -> ('x', 0, 64); 'x' -> ('x', -1, 1)."""
    m = RANGE_RE.match(raw)
    if m:
        name, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
        return name, lo, hi - lo + 1
    m = VARIABLE_RE.match(raw)
    if m:
        return m.group(1), int(m.group(2)), 64
    return raw, -1, 1


def rc_base(rc: str) -> int:
    """Lower bound of the spec 'rc' column ('8-15' -> 8, '0-(N-1)' -> 0, '3' -> 3)."""
    m = re.match(r"^(\d+)", rc.strip())
    assert m, f"unparsed rc column {rc!r}"
    return int(m.group(1))


def cstr(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render() -> tuple[str, int, int, int]:
    """Return (table_text, num_scalars, num_generic, num_specific)."""
    d12 = read_file(SPEC_D12)
    d13 = read_file(SPEC_D13)
    cfx_map = parse_cfxcode_table(d12)
    entries = (parse_register_tables(d12, "DADAO-12")
               + parse_register_tables(d13, "DADAO-13"))
    generic = [e for e in entries if e["is_generic"]]
    specific = [e for e in entries if not e["is_generic"]]
    scalars = build_scalar_aliases(cfx_map)
    specifics = build_register_aliases(specific, cfx_map)

    # Validate every scalar/range is understandable before emitting.
    for e in generic:
        _name, _lo, _cnt = split_range(e["tail"])
        base = rc_base(e["rc"])
        cnt = _cnt if _cnt > 1 else 1
        assert 0 <= base < 64 and 1 <= cnt <= 64, f"bad generic {e['tail']!r} rc={e['rc']!r}"
    for alias, _ha, _cg, rc, _src in specifics:
        _name, _lo, cnt = split_range(alias)
        base = rc_base(rc)
        assert 0 <= base < 64 and 1 <= cnt <= 64, f"bad specific {alias!r} rc={rc!r}"

    L: list[str] = []
    L.append("//===-- DADAOCfxAlias.inc - DADAO cfx alias lookup tables --*- C++ -*-===//")
    L.append("//")
    L.append("// Part of the LLVM Project, under the Apache License v2.0 with LLVM")
    L.append("// Exceptions. See https://llvm.org/LICENSE.txt for license information.")
    L.append("// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception")
    L.append("//")
    L.append("//===----------------------------------------------------------------------===//")
    L.append("//")
    L.append("// cfx assembly alias tables (ADR-0017 D3/D4/D8; Toolchain-01 \u00a713).")
    L.append("// MECHANICALLY GENERATED from spec/DADAO-12/13 register tables through the")
    L.append("// committed projector tools/spec/gen_cfx_aliases.py (the same source that")
    L.append("// produces the drift-gated .tao/knowledge/contract-cfx-aliases.md).")
    L.append("// Generator: tools/llvm/gen_cfx_alias_table.py")
    L.append("//")
    L.append("//   cfx_<cfxname>           <=> cfx<code>            (13 scalar aliases)")
    L.append("//   cfx_<cfxname>_<tail>    ->  (cfxha, cg, rc)      (66 generic tails)")
    L.append("//   cfx_<cfxname>_<regname> ->  (cfxha, cg, rc)      (34 cfx-specific)")
    L.append("//")
    L.append("// Array registers (ADR-0017 D10) have RcCount > 1 and are addressed by the")
    L.append("// single-subscript form cfx_<...>[N] (rc = RcBase + N, 0 <= N < RcCount).")
    L.append("//===----------------------------------------------------------------------===//")
    L.append("")
    L.append("namespace {")
    L.append("")
    L.append("// Scalar aliases: cfx_<cfxname> <=> cfx<code> (ADR-0017 D3).")
    L.append("struct CfxScalarAlias { const char *Name; unsigned Code; };")
    L.append("static const CfxScalarAlias CfxScalarAliases[] = {")
    for alias, _code_str, code in scalars:
        L.append(f"  {{{cstr(alias)}, {code}}},")
    L.append("};")
    L.append("")
    L.append("// Generic register tails: cfx_<cfxname>_<tail> -> (cg, rc); cfxha comes")
    L.append("// from the cfxname (ADR-0017 D4).  RcCount > 1 => array.")
    L.append("struct CfxRegTail { const char *Tail; unsigned Cg; unsigned RcBase; unsigned RcCount; };")
    L.append("static const CfxRegTail CfxRegTails[] = {")
    for e in generic:
        name, _lo, cnt = split_range(e["tail"])
        base = rc_base(e["rc"])
        if cnt <= 1:
            cnt = 1
        L.append(f"  {{{cstr(name)}, {e['cg']}, {base}, {cnt}}},")
    L.append("};")
    L.append("")
    L.append("// cfx-specific register aliases (cg >= 8): full alias -> (cfxha, cg, rc).")
    L.append("struct CfxSpecificAlias { const char *Name; unsigned Cfxha; unsigned Cg; unsigned RcBase; unsigned RcCount; };")
    L.append("static const CfxSpecificAlias CfxSpecificAliases[] = {")
    for alias, cfxha, cg, rc, _src in specifics:
        name, _lo, cnt = split_range(alias)
        base = rc_base(rc)
        if cnt <= 1:
            cnt = 1
        L.append(f"  {{{cstr(name)}, {cfxha}, {cg}, {base}, {cnt}}},")
    L.append("};")
    L.append("")
    L.append("} // namespace")
    L.append("")

    return "\n".join(L), len(scalars), len(generic), len(specifics)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="output path for DADAOCfxAlias.inc "
                         "(default: the component worktree copy)")
    args = ap.parse_args(argv)

    text, n_scalar, n_generic, n_specific = render()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"gen_cfx_alias_table: wrote {out} "
          f"({n_scalar} scalar, {n_generic} generic, {n_specific} specific)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
