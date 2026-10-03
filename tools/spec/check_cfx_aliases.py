#!/usr/bin/env python3
"""Drift gate: verify ``.tao/knowledge/contract-cfx-aliases.md`` is up-to-date.

Regenerates the alias table from spec sources and compares byte-for-byte
against the checked-in file.  **Non-zero exit on any mismatch.**

Exit codes
----------
* 0 -- PASS (byte-identical)
* 1 -- MISMATCH (generated content differs from checked-in file)
* 2 -- ERROR (missing source file, parse failure, etc.)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Reuse all generation logic from gen_cfx_aliases
from tools.spec.gen_cfx_aliases import (
    OUTPUT,
    build_register_aliases,
    build_scalar_aliases,
    parse_cfxcode_table,
    parse_register_tables,
    read_file,
    render_markdown,
    SPEC_D12,
    SPEC_D13,
)


def main() -> None:
    # Validate source files exist
    for src in (SPEC_D12, SPEC_D13):
        if not src.exists():
            print(f"check-cfx-aliases: ERROR — source file missing: {src}", file=sys.stderr)
            sys.exit(2)

    if not OUTPUT.exists():
        print(f"check-cfx-aliases: ERROR — generated file missing: {OUTPUT}", file=sys.stderr)
        print("Run: python3 tools/spec/gen_cfx_aliases.py", file=sys.stderr)
        sys.exit(1)

    # Regenerate
    d12_text = read_file(SPEC_D12)
    d13_text = read_file(SPEC_D13)

    cfx_map = parse_cfxcode_table(d12_text)
    all_entries = parse_register_tables(d12_text, "DADAO-12") + \
                  parse_register_tables(d13_text, "DADAO-13")
    generic_only = [e for e in all_entries if e["is_generic"]]
    specific_only = [e for e in all_entries if not e["is_generic"]]

    scalar_aliases = build_scalar_aliases(cfx_map)
    register_aliases = build_register_aliases(specific_only, cfx_map)

    expected = render_markdown(
        scalar_aliases, register_aliases, cfx_map,
        generic_only, specific_only,
    )

    actual = read_file(OUTPUT)

    if actual == expected:
        print("check-cfx-aliases: PASS (byte-identical)")
        sys.exit(0)
    else:
        actual_lines = actual.splitlines()
        expected_lines = expected.splitlines()
        print(f"check-cfx-aliases: MISMATCH "
              f"({len(actual_lines)} actual vs {len(expected_lines)} expected lines)")
        # Show first difference
        for i, (a, e) in enumerate(zip(actual_lines, expected_lines)):
            if a != e:
                print(f"  line {i+1}:")
                print(f"    expected: {e!r}")
                print(f"    actual:   {a!r}")
                break
        else:
            if len(actual_lines) != len(expected_lines):
                print(f"  line count differs: {len(actual_lines)} vs {len(expected_lines)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
