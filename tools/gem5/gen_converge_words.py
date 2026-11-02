#!/usr/bin/env python3
"""Generate one legal instruction word per DADAO id (GEM5-013t).

Inputs (read-only, contract-side only):

* ``contracts/opcodes.yaml`` -- field names, bit ranges, ``value`` and the
  ``legality`` expressions.  No C++ execution semantics, no QEMU/LLVM.
* ``tools/gem5/gen_decode_table.py::batch_of()`` -- the single source of the
  owner batch for every id (never written by hand here).

For every id a backtracking search picks a value per field so that the whole
``legality`` expression holds.  ``aligned(N)`` is a *run-time* constraint (the
convergence harness starts every register at an 8-byte aligned address) and is
therefore not part of the search; it is reported per row instead.

The output is a deterministic, sorted ``converge_words.inc`` consumed by
``src/arch/dadao/exec/converge_test.cc``:

    struct ConvergeWord { const char *id; uint32_t word; uint8_t owner; };

Exit codes: 0 all 264 ids solved, 1 otherwise (the offending ids are listed --
no id is skipped and no value is guessed from a mnemonic).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts/opcodes.yaml"
DEFAULT_OUT = ROOT / ".work/build/gem5/converge_words.inc"

# Candidate field values, by role (`docs`-level rule in the task book): the
# search only has to find *one* legal word, so the sets stay deliberately small.
# Destinations: 0 last -- `rdhb == rd0` (SBZ fields, e.g. lr) is satisfied only
# by 0, while every `!= rd0` rule picks a non-zero register first.
DEST_REGS = (2, 5, 6, 0)
# Sources: rd0 first -- rd0 is the only register whose value the architecture
# fixes (0), so the word never depends on arbitrary register contents.  Some
# instructions consume a register *value* as a bit position (ext.*_orrr,
# contract-isa §6.4.2: >63 is ILLI) and must not trip over the harness's
# 0x1000 sentinel fill.
SRC_REGS = (0, 2, 3, 4, 5, 6)
COUNTS = (1, 2, 4, 8, 16, 32)          # immu6: counts / one-hot / root n
IMMU18 = (0, 1)                        # fence / escape / trap
SIGNED_IMMS = (0, 1, 8, 16, 32)        # imms12 / imms18 / imms24
CFXHA = (0, 1, 15, 16, 62)

BITS_RE = re.compile(r"^\[(\d+):(\d+)\]$")
NAME_RE = re.compile(r"\b([A-Za-z_]\w*)\b")
BITS_REF_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]")
NO_OVERLAP_RE = re.compile(
    r"no_overlap\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*,\s*"
    r"([A-Za-z_]\w*)\s*\)")
ALIGNED_RE = re.compile(r"aligned\(\s*(\d+)\s*\)")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"gen_converge_words: cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_contract():
    try:
        import yaml  # type: ignore
    except ImportError:
        raise SystemExit("gen_converge_words: PyYAML is required")
    rows = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("gen_converge_words: contracts/opcodes.yaml is not a list")
    return rows


def field_candidates(field: dict, width: int) -> tuple[int, ...]:
    name = field["name"]
    role = field["role"]
    if name == "cfxha":
        values = CFXHA
    elif name == "immu6":
        values = COUNTS
    elif name == "immu18":
        values = IMMU18
    elif name.startswith("imms"):
        values = SIGNED_IMMS
    elif role == "imm":
        values = SIGNED_IMMS
    elif role == "dst":
        values = DEST_REGS
    else:
        values = SRC_REGS
    return tuple(v for v in values if v < (1 << width))


def evaluate(expr: str, values: dict[str, int]) -> bool:
    """Evaluate one legality expression over concrete field values.

    ``aligned(N)`` is a run-time constraint and evaluates to True here.
    """
    text = ALIGNED_RE.sub("True", expr)

    def sub_no_overlap(match: re.Match) -> str:
        a, b, n = (values[name] for name in match.groups())
        return f"({a} + {n} <= {b} or {b} + {n} <= {a})"

    text = NO_OVERLAP_RE.sub(sub_no_overlap, text)

    def sub_bits(match: re.Match) -> str:
        name, hi, lo = match.group(1), int(match.group(2)), int(match.group(3))
        width = hi - lo + 1
        return str((values[name] >> lo) & ((1 << width) - 1))

    text = BITS_REF_RE.sub(sub_bits, text)

    def sub_name(match: re.Match) -> str:
        name = match.group(1)
        if name in values:
            return str(values[name])
        # `rd0`/`rb0`/`ra0`/`rf0` are the architectural zero/FCSR registers.
        if re.fullmatch(r"r[dbfa]0", name):
            return "0"
        if name in ("and", "or", "not", "True", "False"):
            return name
        raise SystemExit(
            f"gen_converge_words: unknown identifier {name!r} in {expr!r}")

    text = NAME_RE.sub(sub_name, text)
    text = text.replace("&&", " and ").replace("||", " or ")
    text = re.sub(r"!(?!=)", " not ", text)
    return bool(eval(text, {"__builtins__": {}}, {}))  # noqa: S307 (trusted input)


def solve(row: dict) -> tuple[dict[str, int], int] | None:
    """Return (field values, number of aligned() rows) or None."""
    fields = []
    for field in row["fields"]:
        match = BITS_RE.match(field["bits"])
        if match is None:
            raise SystemExit(f"{row['id']}: bad bits {field['bits']!r}")
        hi, lo = int(match.group(1)), int(match.group(2))
        fields.append((field["name"], hi, lo,
                       field_candidates(field, hi - lo + 1)))

    legality = [expr for expr in (row.get("legality") or ())]
    # `aligned` never constrains the field choice (see module docstring).
    checked = [expr for expr in legality if not ALIGNED_RE.search(expr)]
    aligned_rows = sum(1 for expr in legality if ALIGNED_RE.search(expr))

    names = [entry[0] for entry in fields]
    for combination in itertools.product(*(entry[3] for entry in fields)):
        values = dict(zip(names, combination))
        if all(evaluate(expr, values) for expr in checked):
            return values, aligned_rows
    return None


def encode(row: dict, values: dict[str, int]) -> int:
    word = int(row["value"], 16)
    mask = int(row["mask"], 16)
    for field in row["fields"]:
        hi, lo = (int(x) for x in BITS_RE.match(field["bits"]).groups())
        word |= values[field["name"]] << lo
    if (word & mask) != int(row["value"], 16):
        raise SystemExit(f"{row['id']}: field bits collide with the opcode mask")
    return word


def render(rows: list[tuple[str, int, str]]) -> str:
    lines = [
        "// Generated by tools/gem5/gen_converge_words.py -- do not edit.",
        "// 264 legal words: contracts/opcodes.yaml fields/legality, owner batch",
        "// from tools/gem5/gen_decode_table.py::batch_of().",
        "struct ConvergeWord",
        "{",
        "    const char *id;",
        "    uint32_t word;",
        "    uint8_t owner;",
        "};",
        "",
        "inline constexpr ConvergeWord kConvergeWords[] = {",
    ]
    for entry_id, word, batch in sorted(rows):
        lines.append(f'    {{"{entry_id}", 0x{word:08x}u, '
                     f'{int(batch[1:])}}},')
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    gen_decode = load_module("gen_decode_table",
                             ROOT / "tools/gem5/gen_decode_table.py")
    gdt = gen_decode
    with gdt.MATRIX.open(newline="", encoding="utf-8") as stream:
        matrix_rows = {row["id"]: row for row in csv.DictReader(
            stream, delimiter="\t")}

    rows = load_contract()
    solved: list[tuple[str, int, str]] = []
    unsolved: list[str] = []
    aligned_rows = 0
    batches: dict[str, int] = {}
    for row in rows:
        entry_id = row["id"]
        matrix_row = matrix_rows.get(entry_id)
        if matrix_row is None:
            unsolved.append(entry_id)
            continue
        batch = gdt.batch_of(matrix_row, entry_id)
        solution = solve(row)
        if solution is None:
            unsolved.append(entry_id)
            continue
        values, aligned = solution
        word = encode(row, values)
        solved.append((entry_id, word, batch))
        aligned_rows += aligned
        batches[batch] = batches.get(batch, 0) + 1

    if unsolved:
        print(f"gen-converge-words: {len(unsolved)} id(s) without a legal word:",
              file=sys.stderr)
        for entry_id in unsolved:
            print(f"  {entry_id}", file=sys.stderr)
        return 1
    if len(solved) != 264:
        print(f"gen-converge-words: {len(solved)} ids, expected 264",
              file=sys.stderr)
        return 1

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(solved), encoding="utf-8")

    counts = " ".join(f"{name}={batches[name]}"
                      for name in sorted(batches))
    print(f"gen-converge-words: {len(solved)}/264 words ({counts}); "
          f"aligned() rows {aligned_rows}; out {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
