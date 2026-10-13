#!/usr/bin/env python3
"""Drift gate: verify ``.tao/knowledge/contract-asm-list.md`` is up-to-date.

Regenerates the assembly-instruction list with
``tools/llvm/gen_asm_list.py`` into a **temporary file** (never overwriting the
checked-in artifact) and compares byte-for-byte against the checked-in file.
**Non-zero exit on any mismatch.**  Symmetric to
``tools/spec/check_cfx_aliases.py``.

Exit codes
----------
* 0 -- PASS (byte-identical)
* 1 -- MISMATCH (generated content differs from checked-in file)
* 2 -- ERROR (missing source/generator/artifact, or generator non-zero exit)
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "tools/llvm/gen_asm_list.py"
OPCODES = ROOT / "contracts/opcodes.yaml"
CHECKED_IN = ROOT / ".tao/knowledge/contract-asm-list.md"


def main() -> int:
    # Validate inputs exist before invoking the generator.
    if not OPCODES.exists():
        print(f"check-asm-list-drift: ERROR — source file missing: {OPCODES}", file=sys.stderr)
        return 2
    if not GENERATOR.exists():
        print(f"check-asm-list-drift: ERROR — generator missing: {GENERATOR}", file=sys.stderr)
        return 2
    if not CHECKED_IN.exists():
        print(f"check-asm-list-drift: ERROR — generated file missing: {CHECKED_IN}", file=sys.stderr)
        print("Run: python3 tools/llvm/gen_asm_list.py", file=sys.stderr)
        return 2

    # Regenerate into a temporary path (never touch the checked-in artifact).
    with tempfile.TemporaryDirectory(prefix="check-asm-list-drift-") as tmpdir:
        tmp = Path(tmpdir) / "contract-asm-list.md"
        proc = subprocess.run(
            [sys.executable, str(GENERATOR), "-o", str(tmp)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(
                f"check-asm-list-drift: ERROR — generator exited {proc.returncode}",
                file=sys.stderr,
            )
            if proc.stdout:
                print(proc.stdout, file=sys.stderr, end="")
            if proc.stderr:
                print(proc.stderr, file=sys.stderr, end="")
            return 2
        if not tmp.exists():
            print("check-asm-list-drift: ERROR — generator produced no output", file=sys.stderr)
            return 2
        expected = tmp.read_bytes()

    actual = CHECKED_IN.read_bytes()

    if actual == expected:
        print("check-asm-list-drift: PASS (byte-identical)")
        return 0

    actual_lines = actual.decode("utf-8", errors="replace").splitlines()
    expected_lines = expected.decode("utf-8", errors="replace").splitlines()
    print(
        f"check-asm-list-drift: MISMATCH "
        f"({len(actual_lines)} actual vs {len(expected_lines)} expected lines)"
    )
    for i, (a, e) in enumerate(zip(actual_lines, expected_lines)):
        if a != e:
            print(f"  line {i+1}:")
            print(f"    expected: {e!r}")
            print(f"    actual:   {a!r}")
            break
    else:
        if len(actual_lines) != len(expected_lines):
            print(f"  line count differs: {len(actual_lines)} vs {len(expected_lines)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
