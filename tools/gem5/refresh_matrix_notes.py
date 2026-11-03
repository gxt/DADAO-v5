#!/usr/bin/env python3
"""Refresh the stale notes of the GEM5-002t semantic matrix (GEM5-013t).

The matrix (``.tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv``) is the
2026-11-01 baseline snapshot; four cell families were written before the later
contract closures and still carry "open point" wording.  This tool rewrites
*only* those cells, using the already-effective contracts -- it adds no new
semantics and never touches ``tests/``, ``spec/`` or ``contracts/``:

* ``g1_note`` for the 12 ``lr.*`` rows (SPEC-182t F1: ``hb`` is SBZ, plus the
  F8.1 reservation granularity);
* ``g1_note`` for the 12 ``sc.*`` rows (SPEC-181t: ``sc`` destination
  ``rdhb == rd0`` is ILLI, plus the F8.1 reservation granularity);
* ``g1_note`` for the 8 ``convert_f2i`` rows (SPEC-181t F5.3: finite inexact
  raises NX);
* ``g1_note`` for the 12 ``contract-fp §5`` arithmetic rows (SPEC-181t F5.1
  ``rem`` and F5.2 C1 ``sclb`` third source ``rdHD``);
* ``exceptions`` of the 12 ``sc.*`` rows (append the missing ILLI rule);
* ``semantics``/``operands`` of ``ftsclb``/``fosclb`` (``rfHD`` -> ``rdHD``,
  matching ``contracts/opcodes.yaml``).

Row sets are derived from live contract metadata (mnemonic families /
``contract_ref`` / the obsolete cell text itself), never from a hard-coded id
list.  ``--apply`` asserts that every selected row still carries the expected
old wording before writing (no blind overwrite) and is idempotent.  ``--check``
recomputes the whole file and compares it byte for byte, so any drift in a
target cell fails with the offending row listed.

``--baseline <git-rev>`` additionally compares every non-target cell with
``git show <rev>:<matrix>`` to prove the refresh changed nothing else.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / ".tao/knowledge/refs/GEM5-002t-semantic-matrix.tsv"
OPCODES = ROOT / "contracts/opcodes.yaml"

TARGET_COLUMNS = ("g1_note", "exceptions", "semantics", "operands")

OLD_LR = "缺规则（见报告发现 F1）"
OLD_F2I = "spec 未明（contract-fp §16 开放点）"
OLD_ARITH = "rem/sclb 边界 spec 未给逐位细则"

LR_NOTE = ("lr 的 hb(rdHB) 为 SBZ 固定零字段，hb!=rd0 ⇒ ILLI（encode_sbz，"
           "SPEC-182t）；数据目的为 rdHC；保留标记粒度=精确地址+访问宽度，"
           "异常/中断进入、另一条 lr、同地址同宽度 store 清标记"
           "（contract-isa §14.2）")
SC_NOTE = ("sc 目的 rdhb==rd0 ⇒ ILLI（dst_rd0，SPEC-181t）；保留标记粒度="
           "精确地址+访问宽度，异常/中断进入清标记，sc 执行后清全部标记；"
           "可伪失败，软件重试（contract-isa §14.2）")
F2I_NOTE = ("饱和值按目标宽度符号性取；有限 inexact ⇒ NX（contract-fp §3，"
            "SPEC-181t F5.3）")
ARITH_NOTE = ("IEEE 语义按 contract-fp §5：rem 精确且不置 NX/OF/UF；sclb 第三源 "
              "rdHD 为 rd 组有符号 64 位指数；边界未明处按 IEEE 754-2019（§16）")
SC_ILLI_SUFFIX = "；sc 目的 rdhb == rd0 → ILLI"

F2I_MNEMONIC = re.compile(r"^f[to]2(it|io|ut|uo)$")
ARITH_MNEMONIC = re.compile(r"^f[to](add|sub|mul|div|rem|sclb)$")


def load_contract() -> list[dict]:
    try:
        import yaml  # type: ignore
    except ImportError:
        raise SystemExit("refresh-matrix-notes: PyYAML is required")
    return yaml.safe_load(OPCODES.read_text(encoding="utf-8"))


def family_ids(contract: list[dict]) -> dict[str, list[str]]:
    """Live contract-derived row sets (no id list, no matrix content)."""
    return {
        "lr": [row["id"] for row in contract
               if row["mnemonic"].startswith("lr.")],
        "sc": [row["id"] for row in contract
               if row["mnemonic"].startswith("sc.")],
        "f2i": [row["id"] for row in contract
                if F2I_MNEMONIC.match(row["mnemonic"])],
        "arith": [row["id"] for row in contract
                  if ARITH_MNEMONIC.match(row["mnemonic"])],
        "sclb": [row["id"] for row in contract
                 if row["mnemonic"] in ("ftsclb", "fosclb")],
    }


def read_matrix(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    return fields, rows


def read_text_matrix(text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return list(reader.fieldnames or []), list(reader)


def render(fields: list[str], rows: list[dict[str, str]]) -> str:
    out = ["\t".join(fields)]
    for row in rows:
        out.append("\t".join(row.get(name, "") for name in fields))
    return "\n".join(out) + "\n"


def refresh_note(row: dict[str, str], old_token: str, new_text: str,
                 family: str, errors: list[str]) -> None:
    """Replace one stale note; idempotent, and never a blind overwrite."""
    note = row["g1_note"]
    if note == new_text:
        return
    if old_token not in note:
        errors.append(f"{row['id']}: g1_note has neither the stale {family} "
                      f"wording nor the refreshed sentence ({note!r})")
        return
    row["g1_note"] = new_text


def apply_refresh(fields: list[str], rows: list[dict[str, str]],
                  contract: list[dict], errors: list[str]
                  ) -> tuple[list[dict[str, str]], dict[str, int]]:
    ids = family_ids(contract)
    by_id = {row["id"]: row for row in rows}
    counts = {name: len(value) for name, value in ids.items()}

    def need(entry_id: str) -> dict[str, str] | None:
        row = by_id.get(entry_id)
        if row is None:
            errors.append(f"{entry_id}: missing from the matrix")
        return row

    for entry_id in ids["lr"]:
        row = need(entry_id)
        if row is not None:
            refresh_note(row, OLD_LR, LR_NOTE, "lr", errors)

    for entry_id in ids["sc"]:
        row = need(entry_id)
        if row is None:
            continue
        refresh_note(row, OLD_LR, SC_NOTE, "sc", errors)
        if "rdhb == rd0" not in row["exceptions"]:
            row["exceptions"] = row["exceptions"] + SC_ILLI_SUFFIX
        if SC_ILLI_SUFFIX not in row["exceptions"]:
            errors.append(f"{entry_id}: exceptions lack the sc ILLI rule "
                          f"({row['exceptions']!r})")

    for entry_id in ids["f2i"]:
        row = need(entry_id)
        if row is not None:
            refresh_note(row, OLD_F2I, F2I_NOTE, "convert_f2i", errors)

    for entry_id in ids["arith"]:
        row = need(entry_id)
        if row is not None:
            refresh_note(row, OLD_ARITH, ARITH_NOTE, "FP arith", errors)

    for entry_id in ids["sclb"]:
        row = need(entry_id)
        if row is None:
            continue
        row["operands"] = row["operands"].replace("rfhd[rf]", "rdhd[rd]")
        row["semantics"] = row["semantics"].replace("rfHD", "rdHD")
        if "rdhd[rd]" not in row["operands"] or "rdHD" not in row["semantics"]:
            errors.append(f"{entry_id}: operands/semantics not on rdHD "
                          f"({row['operands']!r} / {row['semantics']!r})")

    counts["notes"] = (counts["lr"] + counts["sc"] + counts["f2i"] +
                       counts["arith"])
    return rows, counts


def check_structure(fields: list[str], rows: list[dict[str, str]],
                    errors: list[str]) -> None:
    if len(rows) != 264:
        errors.append(f"matrix has {len(rows)} rows, expected 264")
    if len(fields) != 29:
        errors.append(f"matrix has {len(fields)} columns, expected 29")
    for name in TARGET_COLUMNS:
        if name not in fields:
            errors.append(f"matrix lost column {name!r}")
    for row in rows:
        for name in fields:
            if "\t" in row.get(name, ""):
                errors.append(f"{row['id']}: embedded tab in {name}")


def check_old_tokens(rows: list[dict[str, str]], sclb_ids: list[str],
                    errors: list[str]) -> None:
    """No stale note may survive; the rfHD wording only matters for scaleB.

    ``rfhd``/``rfHD`` are valid operands of other FP ids (fma addend, etc.), so
    the rf->rd check is restricted to the ids whose third operand is ``rdHD``.
    """
    for token in (OLD_LR, OLD_F2I, OLD_ARITH):
        hits = [row["id"] for row in rows if token in row["g1_note"]]
        if hits:
            errors.append(f"stale token {token!r} still in {len(hits)} row(s): "
                          f"{hits[:5]}")
    by_id = {row["id"]: row for row in rows}
    for entry_id in sclb_ids:
        row = by_id.get(entry_id)
        if row is None:
            continue
        if "rfhd[rf]" in row["operands"] or "rfHD" in row["semantics"]:
            errors.append(f"{entry_id}: stale rfHD wording survives")


def baseline_errors(rev: str, fields: list[str], rows: list[dict[str, str]],
                    errors: list[str]) -> None:
    rel = MATRIX.relative_to(ROOT)
    proc = subprocess.run(["git", "-C", str(ROOT), "show",
                           f"{rev}:{rel}"], capture_output=True, text=True)
    if proc.returncode != 0:
        errors.append(f"cannot read {rev}:{rel}: {proc.stderr.strip()}")
        return
    old_fields, old_rows = read_text_matrix(proc.stdout)
    if old_fields != fields:
        errors.append(f"column set differs from {rev} ({len(old_fields)} -> "
                      f"{len(fields)})")
        return
    if [row["id"] for row in old_rows] != [row["id"] for row in rows]:
        errors.append(f"row id order differs from {rev}")
        return
    for old, new in zip(old_rows, rows):
        for name in fields:
            if name in TARGET_COLUMNS:
                continue
            if old[name] != new[name]:
                errors.append(f"{new['id']}: non-target column {name} changed "
                              f"({old[name]!r} -> {new[name]!r})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="write the refreshed matrix in place")
    parser.add_argument("--check", action="store_true",
                        help="verify the matrix on disk is fully refreshed")
    parser.add_argument("--baseline", metavar="GIT_REV", default=None,
                        help="also require non-target cells to equal GIT_REV's")
    args = parser.parse_args()
    if not args.apply and not args.check:
        args.check = True

    contract = load_contract()
    fields, rows = read_matrix(MATRIX)
    errors: list[str] = []

    on_disk = render(fields, rows)
    refreshed_rows, counts = apply_refresh(fields, rows, contract, errors)
    expected = render(fields, refreshed_rows)

    check_structure(fields, refreshed_rows, errors)

    if args.apply:
        if errors:
            for error in errors:
                print(f"refresh-matrix-notes: {error}", file=sys.stderr)
            print("refresh-matrix-notes: refusing to write (pre-state "
                  "mismatch)", file=sys.stderr)
            return 1
        if expected != on_disk:
            MATRIX.write_text(expected, encoding="utf-8")
            print(f"refresh-matrix-notes: applied "
                  f"({counts['notes']} notes, {counts['sc']} sc "
                  f"exceptions, {counts['sclb']} sclb fields)")
        else:
            print("refresh-matrix-notes: already up to date (no write)")
        return 0

    # --check: recompute the whole file and compare byte for byte, so a stale
    # target cell (old sentence or missing ILLI) is reported per row.
    if expected != on_disk:
        _, disk_rows = read_matrix(MATRIX)
        want = {row["id"]: row for row in refreshed_rows}
        for row in disk_rows:
            target = want.get(row["id"])
            if target is None:
                errors.append(f"{row['id']}: unexpected row")
                continue
            for name in TARGET_COLUMNS:
                if row[name] != target[name]:
                    errors.append(f"{row['id']}: {name} not refreshed "
                                  f"({row[name]!r})")
    check_old_tokens(rows, family_ids(contract)["sclb"], errors)
    if args.baseline:
        baseline_errors(args.baseline, fields, rows, errors)

    if errors:
        for error in errors[:40]:
            print(f"refresh-matrix-notes: {error}", file=sys.stderr)
        if len(errors) > 40:
            print(f"refresh-matrix-notes: ... {len(errors) - 40} more",
                  file=sys.stderr)
        return 1

    print(f"refresh-matrix-notes: OK (notes {counts['notes']} "
          f"[lr {counts['lr']} / sc {counts['sc']} / f2i {counts['f2i']} / "
          f"arith {counts['arith']}], sc exceptions "
          f"{counts['sc']}, sclb fields {counts['sclb']}, rows "
          f"{len(rows)}, columns {len(fields)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
