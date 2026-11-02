#!/usr/bin/env python3
"""Generate the DADAO gem5 decode table and its 264-row assertion corpus.

Spec-first: the decode table is derived from ``contracts/opcodes.yaml`` (the
machine-readable projection of ``.tao/contracts/contract-isa.md`` /
``contract-fp.md``); the assertions are derived from
``.tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv`` (GEM5-002t, 264 rows).
The two inputs are cross-checked row by row, so a drift in either side fails
the generator instead of silently producing a table that disagrees with the
matrix.

Outputs (all generated, never hand-edited):

* ``<source>/src/arch/dadao/decode/decode_table.inc``      -- C++ decode table
* ``<source>/src/arch/dadao/decode/decode_assertions.inc`` -- C++ assertions
* ``components/gem5/decode-assertions.tsv``                -- human-readable
* ``components/gem5/decode-negative.tsv``                  -- negative corpus

``--check`` re-generates everything in memory and compares it byte for byte
with the files on disk (drift gate used by ``make check-gem5-decode``).

GEM5-005t adds the SPEC-181t data to the same corpus: the ``ftsclb``/
``fosclb`` third operand is ``rdhd`` (rd bank), 12 ``sc.*`` rows keep
``rdhb != rd0`` with the ``dst_rd0`` rule, plus generated legality cases and a
negative guard for the retired ``rfhd`` spelling.  The curated guards make a
contract regression fail here instead of silently emitting a stale table.

B0 scope: decode/format/field/opcode/sub-table dispatch only.  Execution
semantics (B1-B7) are not part of this table; the batch column only fixes the
B1-B7 boundary counts (38/8/42/63/28/30/55) from GEM5-002t-REPORT.md §5.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / ".tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv"
OPCODES = ROOT / "contracts/opcodes.yaml"
ASSERT_TSV = ROOT / "components/gem5/decode-assertions.tsv"
NEGATIVE_TSV = ROOT / "components/gem5/decode-negative.tsv"

BATCH_COUNTS = {"B1": 38, "B2": 8, "B3": 42, "B4": 63,
                "B5": 28, "B6": 30, "B7": 55}
BATCH_NAMES = ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]

# SPEC-181t regression nets (user ruling 2026-11-01, SPEC-181t 已确认口径
# F5.2/F8.2):
#   * F5.2 C1: ``ftsclb``/``fosclb`` third operand is ``rdHD`` (64-bit signed
#     integer exponent, ``rd0`` == exponent 0), same ``orrr`` encoding; the old
#     ``rfHD`` (rf bank) reading is invalid.
#   * F8.2: ``sc`` destination ``rdHB == rd0`` is ILLI (``dst_rd0``), while the
#     ``rdHC`` source reading rd0 as 0 stays legal.
# These lists are deliberately curated: if the contracts regress to the old
# spelling the generator fails instead of silently emitting a stale table.
SCALE_RD_EXPONENT_IDS = ("ftsclb_orrr_rf", "fosclb_orrr_rf")
LEGACY_SCALE_THIRD = ("rfhd", "rf")  # name/bank the third operand must NOT be
SC_RD0_IDS = (
    "sc.o.nn_orrr_rd", "sc.t.nn_orrr_rd", "sc.w.nn_orrr_rd", "sc.b.nn_orrr_rd",
    "sc.o.nr_orrr_rd", "sc.t.nr_orrr_rd", "sc.w.nr_orrr_rd", "sc.b.nr_orrr_rd",
    "sc.o.ar_orrr_rd", "sc.t.ar_orrr_rd", "sc.w.ar_orrr_rd", "sc.b.ar_orrr_rd",
)
SC_RD0_DST = "rdhb"
SC_RD0_SRC = "rdhc"

# Top opcode bytes that own a 6-bit [23:18] sub-table instead of a whole
# instruction.  Derived from the contracts; asserted below (not hardcoded in
# the decoder).
SUBTABLE_FORMATS = {"orrr", "orri", "oiii"}
COARSE_MASK = 0xFF000000
FINE_MASK = 0xFFFC0000

BITS_RE = re.compile(r"^\[(\d+):(\d+)\]$")
HEX_RE = re.compile(r"^0x[0-9a-fA-F]+$")


@dataclass(frozen=True)
class Field:
    name: str
    hi: int
    lo: int
    role: str
    bank: str
    signed: bool

    @property
    def width(self) -> int:
        return self.hi - self.lo + 1

    def mask(self) -> int:
        return ((1 << self.width) - 1) << self.lo


@dataclass(frozen=True)
class Entry:
    id: str
    mnemonic: str
    fmt: str
    scope: str
    contract_ref: str
    spec_cite: str
    mask: int
    value: int
    opc: int
    ha: int | None
    fields: tuple[Field, ...]
    rules: tuple[str, ...]
    legality: tuple[str, ...]
    batch: str

    @property
    def inst(self) -> int:
        """Deterministic encoding used by the assertion corpus."""
        return self.inst_with({})

    def field_values(self) -> list[int]:
        """Seeded per-field values (same seed as ``inst``)."""
        values: list[int] = []
        used: set[int] = set()
        for idx, field in enumerate(self.fields):
            value = (0x2A + idx * 11) & ((1 << field.width) - 1)
            while value in used:
                value = (value + 1) & ((1 << field.width) - 1)
            if value == 0:
                value = 1
            used.add(value)
            values.append(value)
        return values

    def inst_with(self, overrides: dict[str, int]) -> int:
        """Seeded encoding with named fields replaced by *overrides*."""
        names = {field.name for field in self.fields}
        unknown = sorted(set(overrides) - names)
        if unknown:
            raise SystemExit(f"{self.id}: no field named {unknown}")
        inst = self.value
        values = self.field_values()
        for idx, field in enumerate(self.fields):
            value = overrides.get(field.name, values[idx])
            if not 0 <= value < (1 << field.width):
                raise SystemExit(
                    f"{self.id}/{field.name}: override {value} does not fit "
                    f"in {field.width} bits")
            inst |= value << field.lo
        if (inst & self.mask) != self.value:
            raise SystemExit(f"{self.id}: field bits collide with the opcode mask")
        return inst

    def field_index(self, name: str) -> int:
        for idx, field in enumerate(self.fields):
            if field.name == name:
                return idx
        raise SystemExit(f"{self.id}: no field named {name!r}")


def fail(msg: str) -> None:
    raise SystemExit(f"gen_decode_table: {msg}")


def load_yaml(path: Path):
    try:
        import yaml  # type: ignore
    except ImportError:
        fail("PyYAML is required (python3 -c 'import yaml')")
    with path.open("rb") as stream:
        return yaml.safe_load(stream)


def parse_hex(text: str, what: str) -> int:
    if not HEX_RE.match(text):
        fail(f"{what}: not a hex constant: {text!r}")
    return int(text, 16)


def batch_of(row: dict, entry_id: str) -> str:
    """Map a matrix row to the B1-B7 implementation batch.

    The grouping is the one that reproduces the report's exact boundary
    counts: B1 38 / B2 8 / B3 42 / B4 63 / B5 28 / B6 30 / B7 55.
    """
    ref = row["contract_ref"]
    if ref.startswith("contract-fp §11"):
        return "B1"
    if ref.startswith("contract-fp §12"):
        return "B5"  # RF<->RD block moves: block-copy batch
    if ref.startswith("contract-fp §13"):
        return "B2"
    if ref.startswith("contract-fp"):
        return "B7"
    if ref.startswith("contract-isa §3."):
        return "B5" if ref.startswith("contract-isa §3.3.3") else "B1"
    if ref.startswith("contract-isa §4"):
        return "B5"
    if ref.startswith("contract-isa §5"):
        return "B2"
    if ref.startswith("contract-isa §6.5"):
        return "B5"
    if ref.startswith("contract-isa §6"):
        # 32/16/8-bit rev.t/.w/.b belong to the narrow-width batch.
        if entry_id.startswith(("rev.t", "rev.w", "rev.b")):
            return "B4"
        return "B3"
    if ref.startswith("contract-isa §7"):
        return "B3"
    if ref.startswith("contract-isa §8"):
        return "B5"
    if ref.startswith(("contract-isa §10", "contract-isa §11",
                       "contract-isa §12")):
        return "B4"
    if ref.startswith(("contract-isa §13", "contract-isa §14")):
        return "B6"
    if ref.startswith("spec/SimRISC-04"):
        return "B3"
    fail(f"{entry_id}: unmapped contract_ref {ref!r}")


def load_entries() -> list[Entry]:
    opcodes = load_yaml(OPCODES)
    if not isinstance(opcodes, list):
        fail("contracts/opcodes.yaml is not a list")
    if len(opcodes) != 264:
        fail(f"contracts/opcodes.yaml has {len(opcodes)} entries, expected 264")

    with MATRIX.open(newline="", encoding="utf-8") as stream:
        matrix_rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(matrix_rows) != 264:
        fail(f"matrix has {len(matrix_rows)} rows, expected 264")
    matrix = {row["id"]: row for row in matrix_rows}
    if len(matrix) != 264:
        fail("matrix has duplicate ids")

    entries: list[Entry] = []
    for raw in opcodes:
        entry_id = raw["id"]
        row = matrix.get(entry_id)
        if row is None:
            fail(f"{entry_id}: present in opcodes.yaml but absent from matrix")

        # Cross-check every matrix column that the decoder is built from.
        checks = {
            "mnemonic": raw["mnemonic"],
            "format": raw["format"],
            "scope": raw["scope"],
            "opc": raw["opc"],
        }
        for key, value in checks.items():
            if row[key] != value:
                fail(f"{entry_id}: matrix {key}={row[key]!r} != "
                     f"opcodes {key}={value!r}")
        for key in ("mask", "value"):
            if row[key].lower() != raw[key].lower():
                fail(f"{entry_id}: matrix {key}={row[key]!r} != "
                     f"opcodes {key}={raw[key]!r}")

        ha = raw.get("ha")
        if ha is not None:
            opx = row["opx"]
            if opx == "—":
                fail(f"{entry_id}: opcodes has ha but matrix opx is empty")
            opx_ha = parse_hex(opx.split("=", 1)[1], f"{entry_id} opx")
            if opx_ha != parse_hex(ha, f"{entry_id} ha"):
                fail(f"{entry_id}: matrix opx {opx} != opcodes ha {ha}")
        elif row["opx"] != "—":
            fail(f"{entry_id}: matrix opx {row['opx']} but opcodes has no ha")

        mask = parse_hex(raw["mask"], f"{entry_id} mask")
        value = parse_hex(raw["value"], f"{entry_id} value")
        if mask not in (COARSE_MASK, FINE_MASK):
            fail(f"{entry_id}: unexpected mask {raw['mask']}")
        if value & ~mask:
            fail(f"{entry_id}: value {raw['value']} has bits outside mask")
        opc = parse_hex(raw["opc"], f"{entry_id} opc")
        if opc != (value >> 24) & 0xFF:
            fail(f"{entry_id}: opc {raw['opc']} != top byte of value")
        ha_value = None
        if ha is not None:
            ha_value = parse_hex(ha, f"{entry_id} ha")
            if ha_value != (value >> 18) & 0x3F:
                fail(f"{entry_id}: ha {ha} != bits [23:18] of value")

        fields: list[Field] = []
        for field in raw["fields"]:
            m = BITS_RE.match(field["bits"])
            if not m:
                fail(f"{entry_id}/{field['name']}: bad bits {field['bits']}")
            hi, lo = int(m.group(1)), int(m.group(2))
            if not 0 <= lo <= hi <= 31:
                fail(f"{entry_id}/{field['name']}: bits out of range")
            fields.append(Field(field["name"], hi, lo, field["role"],
                                field["bank"], bool(field.get("signed", False))))
        if not 1 <= len(fields) <= 4:
            fail(f"{entry_id}: {len(fields)} fields (1..4 supported)")
        occupied = 0
        for field in fields:
            if occupied & field.mask():
                fail(f"{entry_id}: overlapping field {field.name}")
            if field.mask() & mask:
                fail(f"{entry_id}: field {field.name} overlaps the opcode mask")
            occupied |= field.mask()

        rules = tuple(raw.get("rule_refs") or ())
        legality = tuple(raw.get("legality") or ())
        entries.append(Entry(
            id=entry_id, mnemonic=raw["mnemonic"], fmt=raw["format"],
            scope=raw["scope"], contract_ref=row["contract_ref"],
            spec_cite=raw["spec_cite"], mask=mask, value=value, opc=opc,
            ha=ha_value, fields=tuple(fields), rules=rules,
            legality=legality, batch=batch_of(row, entry_id)))

    if len(entries) != 264 or {e.id for e in entries} != set(matrix):
        fail("entry id set mismatch between opcodes.yaml and matrix")
    return entries


def build_maps(entries: list[Entry]) -> tuple[dict[int, int], dict[int, int],
                                              list[list[int]]]:
    """Return (opcode -> entry index, opcode -> subtable index, subtable)."""
    coarse: dict[int, int] = {}
    subs: dict[int, tuple[int, dict[int, int]]] = {}
    for idx, entry in enumerate(entries):
        if entry.mask == COARSE_MASK:
            if entry.opc in coarse:
                fail(f"duplicate whole-opcode entry at 0x{entry.opc:02x}")
            coarse[entry.opc] = idx
        else:
            if entry.fmt not in SUBTABLE_FORMATS:
                fail(f"{entry.id}: fine mask on non-subtable format {entry.fmt}")
            top, table = subs.setdefault(entry.opc, (len(subs), {}))
            if entry.ha in table:
                fail(f"{entry.id}: duplicate sub-table slot "
                     f"0x{entry.opc:02x}/0x{entry.ha:02x}")
            table[entry.ha] = idx
    for top in coarse:
        if top in subs:
            fail(f"opcode 0x{top:02x} has both a coarse entry and a sub-table")
    # A top byte with a sub-table must not be reachable as a coarse entry.
    return coarse, {top: slot for top, (slot, _) in subs.items()}, [
        [table.get(ha, -1) for ha in range(64)]
        for _, (slot, table) in sorted(subs.items(), key=lambda kv: kv[1][0])
    ]


def validate_spec181t(entries: list[Entry]) -> None:
    """Curated SPEC-181t guards: the contracts must not regress.

    * ``ftsclb``/``fosclb`` third operand is ``rdhd`` in the ``rd`` bank
      (``orrr`` ``[5:0]``), not the old ``rfhd`` in the ``rf`` bank; the
      destination rule ``dst_rf0`` stays.
    * every ``sc.*`` keeps ``rdhb != rd0`` with the ``dst_rd0`` rule reference,
      the rule targets the destination ``rdhb`` only (``rdhc`` as a source may
      read rd0), and the ``sc`` id set is exactly the contract's ``sc.*`` rows.
    """
    by_id = {entry.id: entry for entry in entries}

    contract_sc = {entry.id for entry in entries
                   if entry.mnemonic.startswith("sc.")}
    if contract_sc != set(SC_RD0_IDS):
        missing = sorted(set(SC_RD0_IDS) - contract_sc)
        extra = sorted(contract_sc - set(SC_RD0_IDS))
        fail(f"sc id set changed (missing {missing}, unexpected {extra}); "
             "SPEC-181t F8.2 expects 12 sc.* rows")

    for entry_id in SCALE_RD_EXPONENT_IDS:
        entry = by_id.get(entry_id)
        if entry is None:
            fail(f"{entry_id}: missing from contracts/opcodes.yaml "
                 "(SPEC-181t F5.2 C1)")
        if len(entry.fields) != 3:
            fail(f"{entry_id}: {len(entry.fields)} fields, expected 3")
        third = entry.fields[2]
        if (third.name, third.bank) != ("rdhd", "rd"):
            fail(f"{entry_id}: third operand is {third.name}/{third.bank}, "
                 "expected rdhd/rd (SPEC-181t F5.2 C1: rfHD -> rdHD)")
        if (third.hi, third.lo, third.role) != (5, 0, "src"):
            fail(f"{entry_id}: third operand bits/role "
                 f"[{third.hi}:{third.lo}]/{third.role}, expected [5:0]/src")
        if "dst_rf0" not in entry.rules:
            fail(f"{entry_id}: dst_rf0 rule reference lost")

    for entry_id in SC_RD0_IDS:
        entry = by_id.get(entry_id)
        if entry is None:
            fail(f"{entry_id}: missing from contracts/opcodes.yaml "
                 "(SPEC-181t F8.2)")
        if "dst_rd0" not in entry.rules:
            fail(f"{entry_id}: dst_rd0 rule reference missing "
                 "(SPEC-181t F8.2: sc rdHB=rd0 => ILLI)")
        if f"{SC_RD0_DST} != rd0" not in entry.legality:
            fail(f"{entry_id}: legality lacks '{SC_RD0_DST} != rd0' "
                 f"(got {list(entry.legality)})")
        dst = entry.fields[entry.field_index(SC_RD0_DST)]
        if (dst.role, dst.bank, dst.hi, dst.lo) != ("dst", "rd", 17, 12):
            fail(f"{entry_id}: {SC_RD0_DST} is "
                 f"{dst.role}/{dst.bank}[{dst.hi}:{dst.lo}], expected "
                 "dst/rd[17:12]")
        src = entry.fields[entry.field_index(SC_RD0_SRC)]
        if src.role != "src":
            fail(f"{entry_id}: {SC_RD0_SRC} role is {src.role}, expected src")
        if any(SC_RD0_SRC in expr for expr in entry.legality):
            fail(f"{entry_id}: legality constrains {SC_RD0_SRC}; reading rd0 "
                 "as a source must stay legal")


def legality_cases(entries: list[Entry]) -> list[tuple[str, int, bool, str]]:
    """(id, inst, expect_illegal, reason) cases for the static legality data.

    GEM5-005t scope: the 12 ``sc.*`` destination-rd0 rule plus the scaleB
    exponent operand.  B0 still does not raise ILLI (B1-B6 execute), so these
    cases assert the legality metadata that those batches will enforce.
    """
    by_id = {entry.id: entry for entry in entries}
    cases: list[tuple[str, int, bool, str]] = []
    for entry_id in SC_RD0_IDS:
        entry = by_id[entry_id]
        cases.append((entry_id, entry.inst_with({SC_RD0_DST: 0}), True,
                      "sc dst rdHB=rd0 => ILLI (SimRISC-12 §1.1 / dst_rd0)"))
        cases.append((entry_id, entry.inst_with({SC_RD0_SRC: 0}), False,
                      "sc rdHC=rd0 reads 0 and stays legal"))
    for entry_id in SCALE_RD_EXPONENT_IDS:
        entry = by_id[entry_id]
        cases.append((entry_id, entry.inst_with({"rdhd": 0}), False,
                      "scaleB exponent rdHD=rd0 means exponent 0 (legal)"))
        cases.append((entry_id, entry.inst_with({"rfhb": 0}), True,
                      "scaleB dst rfHB=rf0 => ILLI (dst_rf0)"))
    return cases


def legacy_field_cases() -> list[tuple[str, int, str, str, str]]:
    """(id, field index, legacy name, legacy bank, reason) negative guards."""
    legacy_name, legacy_bank = LEGACY_SCALE_THIRD
    return [
        (entry_id, 2, legacy_name, legacy_bank,
         "SPEC-181t F5.2 C1: scaleB third operand is rdHD, not rfHD")
        for entry_id in SCALE_RD_EXPONENT_IDS
    ]


def cpp_str(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def gen_decode_table(entries: list[Entry], coarse: dict[int, int],
                     sub_slot: dict[int, int],
                     subtable: list[list[int]]) -> str:
    lines = [
        "// Generated by tools/gem5/gen_decode_table.py -- do not edit.",
        "// Source: contracts/opcodes.yaml (264 entries) + GEM5-002t matrix.",
        "// Included inside namespace gem5::DadaoISA::decode.",
        "namespace table {",
        "",
        "inline constexpr FieldDesc kFields[] = {",
    ]
    for entry in entries:
        for field in entry.fields:
            lines.append(
                f"    {{{cpp_str(field.name)}, {field.hi}, {field.lo}, "
                f"{cpp_str(field.role)}, {cpp_str(field.bank)}, "
                f"{'true' if field.signed else 'false'}}},")
    lines.append("};")
    lines.append("")
    for idx, entry in enumerate(entries):
        if entry.rules:
            lines.append(f"inline constexpr const char *kRules{idx}[] = {{"
                         + ", ".join(cpp_str(r) for r in entry.rules) + "};")
        if entry.legality:
            lines.append(
                f"inline constexpr const char *kLegality{idx}[] = {{"
                + ", ".join(cpp_str(r) for r in entry.legality) + "};")
    lines.append("")
    lines.append("inline constexpr DecodeEntry kEntries[] = {")
    first_field = 0
    for idx, entry in enumerate(entries):
        rules_ref = f"kRules{idx}" if entry.rules else "nullptr"
        legality_ref = f"kLegality{idx}" if entry.legality else "nullptr"
        ha = -1 if entry.ha is None else entry.ha
        lines.append(
            f"    {{{cpp_str(entry.id)}, {cpp_str(entry.mnemonic)}, "
            f"{cpp_str(entry.fmt)}, {cpp_str(entry.scope)}, "
            f"{cpp_str(entry.contract_ref)}, {cpp_str(entry.spec_cite)}, "
            f"0x{entry.mask:08x}u, 0x{entry.value:08x}u, 0x{entry.opc:02x}, "
            f"{ha}, {first_field}, {len(entry.fields)}, "
            f"{BATCH_NAMES.index(entry.batch) + 1}, {rules_ref}, "
            f"{len(entry.rules)}, {legality_ref}, "
            f"{len(entry.legality)}}},")
        first_field += len(entry.fields)
    lines.append("};")
    lines.append("")
    opcode_map = [coarse.get(opc, -1) for opc in range(256)]
    lines.append("inline constexpr int16_t kOpcodeEntry[256] = {")
    for start in range(0, 256, 16):
        lines.append("    " + ", ".join(
            str(v) for v in opcode_map[start:start + 16]) + ",")
    lines.append("};")
    lines.append("")
    slot_map = [sub_slot.get(opc, -1) for opc in range(256)]
    lines.append("inline constexpr int8_t kOpcodeSubtable[256] = {")
    for start in range(0, 256, 16):
        lines.append("    " + ", ".join(
            str(v) for v in slot_map[start:start + 16]) + ",")
    lines.append("};")
    lines.append("")
    lines.append("inline constexpr int16_t kSubtableEntries[%d][64] = {"
                 % len(subtable))
    for table in subtable:
        lines.append("    {" + ", ".join(str(v) for v in table) + "},")
    lines.append("};")
    lines.append("")
    lines.append("} // namespace table")
    lines.append("")
    return "\n".join(lines)


def field_sign_extend(value: int, width: int) -> int:
    return value - (1 << width) if value & (1 << (width - 1)) else value


def gen_assertions(entries: list[Entry]) -> str:
    lines = [
        "// Generated by tools/gem5/gen_decode_table.py -- do not edit.",
        "// 264 rows: one decode assertion per contracts/opcodes.yaml entry.",
        "",
    ]
    for idx, entry in enumerate(entries):
        if entry.legality:
            lines.append(
                f"inline constexpr const char *kAssertLegality{idx}[] = {{"
                + ", ".join(cpp_str(r) for r in entry.legality) + "};")
        if entry.rules:
            lines.append(
                f"inline constexpr const char *kAssertRules{idx}[] = {{"
                + ", ".join(cpp_str(r) for r in entry.rules) + "};")
    lines.append("inline constexpr RowAssert kRowAsserts[] = {")
    for idx, entry in enumerate(entries):
        fields = []
        for field in entry.fields:
            raw = (entry.inst >> field.lo) & ((1 << field.width) - 1)
            sext = field_sign_extend(raw, field.width) if field.signed else raw
            fields.append(
                f"{{{cpp_str(field.name)}, {field.hi}, {field.lo}, "
                f"{cpp_str(field.role)}, {cpp_str(field.bank)}, "
                f"{'true' if field.signed else 'false'}, 0x{raw:x}ull, "
                f"{sext}}}")
        while len(fields) < 4:
            fields.append("{nullptr, 0, 0, nullptr, nullptr, false, 0, 0}")
        ha = -1 if entry.ha is None else entry.ha
        legality_ref = f"kAssertLegality{idx}" if entry.legality else "nullptr"
        rules_ref = f"kAssertRules{idx}" if entry.rules else "nullptr"
        lines.append(
            f"    {{{cpp_str(entry.id)}, {cpp_str(entry.mnemonic)}, "
            f"{cpp_str(entry.fmt)}, {cpp_str(entry.scope)}, "
            f"{cpp_str(entry.contract_ref)}, {legality_ref}, "
            f"{len(entry.legality)}, {rules_ref}, {len(entry.rules)}, "
            f"0x{entry.mask:08x}u, "
            f"0x{entry.value:08x}u, 0x{entry.inst:08x}u, 0x{entry.opc:02x}, "
            f"{ha}, {BATCH_NAMES.index(entry.batch) + 1}, "
            f"{len(entry.fields)}, {{{', '.join(fields)}}}}},")
    lines.append("};")
    lines.append("inline constexpr size_t kRowAssertCount = "
                 "sizeof(kRowAsserts) / sizeof(kRowAsserts[0]);")
    lines.append("")
    lines.append("// GEM5-005t: static legality cases (B0 publishes the data; "
                 "B1-B6 raise the fault).")
    lines.append("inline constexpr LegalityCase kLegalityCases[] = {")
    for entry_id, inst, expect_illegal, reason in legality_cases(entries):
        lines.append(
            f"    {{{cpp_str(entry_id)}, 0x{inst:08x}u, "
            f"{'true' if expect_illegal else 'false'}, {cpp_str(reason)}}},")
    lines.append("};")
    lines.append("inline constexpr size_t kLegalityCaseCount = "
                 "sizeof(kLegalityCases) / sizeof(kLegalityCases[0]);")
    lines.append("")
    lines.append("// GEM5-005t: negative guard for the retired scaleB rf third "
                 "operand (SPEC-181t F5.2 C1).")
    lines.append("inline constexpr LegacyFieldCase kLegacyFieldCases[] = {")
    for entry_id, index, name, bank, reason in legacy_field_cases():
        lines.append(
            f"    {{{cpp_str(entry_id)}, {index}, {cpp_str(name)}, "
            f"{cpp_str(bank)}, {cpp_str(reason)}}},")
    lines.append("};")
    lines.append("inline constexpr size_t kLegacyFieldCaseCount = "
                 "sizeof(kLegacyFieldCases) / sizeof(kLegacyFieldCases[0]);")
    lines.append("")
    return "\n".join(lines)


def gen_negative(entries: list[Entry], coarse: dict[int, int],
                 sub_slot: dict[int, int],
                 subtable: list[list[int]]) -> tuple[str, str]:
    rows: list[dict[str, str]] = []

    # Every unused whole-opcode byte is an illegal encoding (UNDI/ILLI).
    for opc in range(256):
        if opc in coarse or opc in sub_slot:
            continue
        rows.append({"kind": "unused-opcode", "inst": f"0x{opc << 24:08x}",
                     "expected_id": "—", "expected_status": "Illegal",
                     "reason": "whole opcode byte not in contracts"})

    # Every empty sub-table slot is an illegal encoding.  The old 0.4.1
    # op-level table would happily decode several of these; this is the
    # coarse-mask regression guard (GEM5-002t F4).
    for top in sorted(sub_slot):
        table = subtable[sub_slot[top]]
        for ha in range(64):
            if table[ha] != -1:
                continue
            rows.append({"kind": "reserved-subtable",
                         "inst": f"0x{(top << 24) | (ha << 18):08x}",
                         "expected_id": "—", "expected_status": "Illegal",
                         "reason": f"opcode 0x{top:02x} sub-table 0x{ha:02x} "
                                   "is reserved"})

    # Explicit identity/encoding regressions from GEM5-002t §3 + deletions.
    by_id = {entry.id: entry for entry in entries}
    curate = [
        ("0x5e000000", "ftfma_rrrr_rf",
         "0x5E was cs.eq-ne-rf in PR#3; now ftfma (same encoding, new meaning)"),
        ("0x5f000000", "fofma_rrrr_rf",
         "0x5F was cs.ne-rf in PR#3; now fofma (same encoding, new meaning)"),
        ("0x76000000", "ret_riii_ra",
         "0x76 was trap in 0.4.1; now ret (same encoding, new meaning)"),
        ("0x77000000", None, "0x77 was escape/swym in the old tables; now ILLI"),
        ("0x78000000", None, "0x78 is unused; old tables had no such entry"),
        ("0x7c000000", None, "cfxld was deleted; 0x7C must be ILLI"),
        ("0x7d000000", None, "cfxst was deleted; 0x7D must be ILLI"),
        ("0x72000000", "br.z_riii_rb",
         "0x72 was cfx2rd in 0.4.1; now br.z (mnemonic-only-same class)"),
        ("0x73000000", "br.nz_riii_rb",
         "0x73 was cfx2rc in 0.4.1; now br.nz (mnemonic-only-same class)"),
        ("0x10000000", "ld.ub_rrii_rd",
         "0x10 was swym in 0.4.1; now ld.ub (coarse-mask regression)"),
        ("0x12000000", "ld.ut_rrii_rd",
         "0x12 was cmps in 0.4.1; now ld.ut (coarse-mask regression)"),
        ("0x1a000000", "st.t_rrii_rd",
         "0x1A was add in 0.4.1; now st.t (coarse-mask regression)"),
        ("0x40000000", None,
         "0x40/0x00 was ldo in 0.4.1; the 0x40 sub-table slot is reserved"),
        ("0x79000000", "fence_ciii_cfx",
         "fence moved from oiii to ciii 0x79 (ADR-0044)"),
        ("0x47880000", "swym_oiii_imm",
         "swym moved from 0x77 to 0x47/0x22 sub-table slot"),
        ("0x56000000", "clmul.o_rrrr_rd", "clmul.o is new in M9"),
        ("0x440c0000", "ftrnd_orri_rf", "ftrnd is new (roundint family)"),
        ("0x442c0000", "fornd_orri_rf", "fornd is new (roundint family)"),
    ]
    for inst, expected, reason in curate:
        if expected is not None:
            if expected not in by_id:
                fail(f"regression target {expected} is not in the contract")
            entry = by_id[expected]
            if (int(inst, 16) & entry.mask) != entry.value:
                fail(f"regression {inst} does not match {expected}")
        rows.append({"kind": "identity-regression", "inst": inst,
                     "expected_id": expected or "—",
                     "expected_status": "Decoded" if expected else "Illegal",
                     "reason": reason})

    # Same-encoding-different-meaning / new / deleted coverage from the matrix
    # classification columns is visible in the identity regressions above;
    # assert that the two same-encoding-different-meaning rows stayed put.
    covered = {r["expected_id"] for r in rows
               if r["kind"] == "identity-regression"}
    if not {"ftfma_rrrr_rf", "fofma_rrrr_rf"} <= covered:
        fail("same-encoding-different-meaning coverage lost")

    # C++ corpus.
    lines = [
        "// Generated by tools/gem5/gen_decode_table.py -- do not edit.",
        "// Negative/regression corpus: reserved encodings + identity checks.",
        "",
        "inline constexpr NegativeCase kNegativeCases[] = {",
    ]
    for row in rows:
        expected = "nullptr" if row["expected_id"] == "—" else \
            cpp_str(row["expected_id"])
        status = "true" if row["expected_status"] == "Decoded" else "false"
        lines.append(f"    {{0x{int(row['inst'], 16):08x}u, {expected}, "
                     f"{status}, {cpp_str(row['reason'])}}},")
    lines.append("};")
    lines.append("inline constexpr size_t kNegativeCaseCount = "
                 "sizeof(kNegativeCases) / sizeof(kNegativeCases[0]);")
    lines.append("")
    return "\n".join(lines), "\n".join(
        f"{r['kind']}\t{r['inst']}\t{r['expected_id']}\t"
        f"{r['expected_status']}\t{r['reason']}" for r in rows) + "\n"


def tsv_assertions(entries: list[Entry]) -> str:
    header = ["row", "id", "batch", "scope", "mnemonic", "format", "opc",
              "ha", "mask", "value", "inst", "fields", "legality", "rules",
              "contract_ref", "status"]
    out = ["\t".join(header)]
    for idx, entry in enumerate(entries):
        fields = []
        for field in entry.fields:
            raw = (entry.inst >> field.lo) & ((1 << field.width) - 1)
            fields.append(f"{field.name}[{field.hi}:{field.lo}]"
                          f"{field.role}/{field.bank}"
                          f"{'/s' if field.signed else ''}=0x{raw:x}")
        out.append("\t".join([
            str(idx + 1), entry.id, entry.batch, entry.scope,
            entry.mnemonic, entry.fmt, f"0x{entry.opc:02x}",
            "—" if entry.ha is None else f"ha=0x{entry.ha:02x}",
            f"0x{entry.mask:08x}", f"0x{entry.value:08x}",
            f"0x{entry.inst:08x}", ";".join(fields),
            ";".join(entry.legality), ";".join(entry.rules),
            entry.contract_ref, "Decoded"]))
    return "\n".join(out) + "\n"


def outputs(source: Path) -> dict[Path, str]:
    entries = load_entries()
    validate_spec181t(entries)
    counts: dict[str, int] = {name: 0 for name in BATCH_NAMES}
    for entry in entries:
        counts[entry.batch] += 1
    if counts != BATCH_COUNTS:
        fail(f"batch counts {counts} != {BATCH_COUNTS} (GEM5-002t §5)")
    if sum(counts.values()) != 264:
        fail("batch counts do not sum to 264")

    coarse, sub_slot, subtable = build_maps(entries)
    table = gen_decode_table(entries, coarse, sub_slot, subtable)
    assertions = gen_assertions(entries)
    negative_cpp, negative_tsv = gen_negative(entries, coarse, sub_slot,
                                              subtable)
    return {
        source / "src/arch/dadao/decode/decode_table.inc": table,
        source / "src/arch/dadao/decode/decode_assertions.inc": assertions,
        source / "src/arch/dadao/decode/decode_negative.inc": negative_cpp,
        ASSERT_TSV: tsv_assertions(entries),
        NEGATIVE_TSV: "kind\tinst\texpected_id\texpected_status\treason\n"
                      + negative_tsv,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=ROOT / ".work/source/gem5",
                        help="gem5 worktree (default .work/source/gem5)")
    parser.add_argument("--check", action="store_true",
                        help="compare generated files with the worktree")
    args = parser.parse_args()
    source = args.source if args.source.is_absolute() else ROOT / args.source

    generated = outputs(source)
    if args.check:
        bad = []
        for path, text in generated.items():
            if not path.exists():
                bad.append(f"missing: {path.relative_to(ROOT)}")
            elif path.read_text(encoding="utf-8") != text:
                bad.append(f"stale: {path.relative_to(ROOT)}")
        if bad:
            print("gen_decode_table: drift detected (regenerate with "
                  "tools/gem5/gen_decode_table.py):")
            for line in bad:
                print("  " + line)
            return 1
        print(f"gen_decode_table: OK (264 rows, batches {BATCH_COUNTS})")
        return 0

    for path, text in generated.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        try:
            shown = path.relative_to(ROOT)
        except ValueError:
            shown = path
        print(f"wrote {shown}")
    print(f"gen_decode_table: 264 rows; batches {BATCH_COUNTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
