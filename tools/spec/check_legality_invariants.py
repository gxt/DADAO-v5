#!/usr/bin/env python3
"""Legality invariants gate (SPEC-103t / ISS-079; SPEC-067t F4 coverage gap).

Covers two invariants that previously had no mechanical gate:

1. **``ftroot``/``foroot`` n=2 constraint** (``encode_fp_root_n``):
   every ``ftroot``/``foroot`` record in ``contracts/opcodes.yaml`` must carry
   the ``immu6 == 2`` legality expression and reference the
   ``encode_fp_root_n`` rule; that rule must exist, be ``active``, fault
   ``ILLI``, and its description must state ``n=2``.
   (``n != 2`` ⇒ ILLI lives in the ``immu6 == 2`` expression; the rule id ties
   the record to ``contracts/legality_rules.yaml``.)

2. **Rule rename registry**: the new id must be effective (present as a rule
   and referenced), the old id must have **0 hits** in the live contracts
   (``contracts/*.yaml``) — so a rename cannot silently regress.

Sources
-------
* ``contracts/opcodes.yaml``  (records: legality + rule_refs)
* ``contracts/legality_rules.yaml`` (rule ids / status / fault / description)
* raw text scan of ``contracts/*.yaml`` for the old ids

Exit 0 = all invariants hold; exit 1 = violation.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts" / "opcodes.yaml"
RULES = ROOT / "contracts" / "legality_rules.yaml"
CONTRACTS_DIR = ROOT / "contracts"

# n=2 constraint carrier.
ROOT_N_MNEMONICS = ("ftroot", "foroot")
ROOT_N_EXPR = "immu6 == 2"
ROOT_N_RULE = "encode_fp_root_n"

# Historical rule renames (old id → new id).  Source: SPEC-067t / SPEC-070t.
# The old id must stay dead (0 hits) in the live contracts.
RULE_RENAMES = {
    "fp_root_invalid_n": "encode_fp_root_n",
}


def load_contracts() -> tuple[list[dict], list[dict], dict[str, str]]:
    opcodes = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    rules_data = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    rules = rules_data["rules"] if isinstance(rules_data, dict) else rules_data
    raw = {p.name: p.read_text(encoding="utf-8") for p in sorted(CONTRACTS_DIR.glob("*.yaml"))}
    return opcodes, rules, raw


def main() -> int:
    opcodes, rules, raw = load_contracts()
    rules_by_id = {r["id"]: r for r in rules}
    errors: list[str] = []

    # ── 1. ftroot/foroot n=2 constraint ──────────────────────────────────
    for mnemonic in ROOT_N_MNEMONICS:
        entries = [e for e in opcodes if e.get("mnemonic") == mnemonic]
        if not entries:
            errors.append(f"opcodes.yaml: mnemonic '{mnemonic}' not found")
            continue
        for e in entries:
            legality = e.get("legality") or []
            if ROOT_N_EXPR not in legality:
                errors.append(
                    f"opcodes.yaml: '{e['id']}' legality 缺 '{ROOT_N_EXPR}' "
                    f"(实际 {legality})"
                )
            refs = e.get("rule_refs") or []
            if ROOT_N_RULE not in refs:
                errors.append(
                    f"opcodes.yaml: '{e['id']}' rule_refs 缺 '{ROOT_N_RULE}' "
                    f"(实际 {refs})"
                )

    rule = rules_by_id.get(ROOT_N_RULE)
    if rule is None:
        errors.append(f"legality_rules.yaml: 规则 '{ROOT_N_RULE}' 不存在")
    else:
        if rule.get("status") != "active":
            errors.append(
                f"legality_rules.yaml: '{ROOT_N_RULE}' status={rule.get('status')} ≠ active"
            )
        if rule.get("fault") != "ILLI":
            errors.append(
                f"legality_rules.yaml: '{ROOT_N_RULE}' fault={rule.get('fault')} ≠ ILLI"
            )
        if not re.search(r"n\s*=\s*2", rule.get("description") or ""):
            errors.append(
                f"legality_rules.yaml: '{ROOT_N_RULE}' description 未声明 n=2"
            )

    # ── 2. Rule rename registry ──────────────────────────────────────────
    for old_id, new_id in RULE_RENAMES.items():
        if new_id not in rules_by_id:
            errors.append(f"legality_rules.yaml: 新 id '{new_id}' 缺失")
        if old_id in rules_by_id:
            errors.append(f"legality_rules.yaml: 旧 id '{old_id}' 复活（应已改名）")
        for e in opcodes:
            if old_id in (e.get("rule_refs") or []):
                errors.append(f"opcodes.yaml: '{e['id']}' 仍引用旧 id '{old_id}'")
        # 0 raw hits across live contracts (catches comments too).
        for name, text in raw.items():
            if old_id in text:
                errors.append(f"contracts/{name}: 旧 id '{old_id}' 仍有命中（应 0）")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        print(f"check-legality-invariants: FAIL ({len(errors)} violation(s))",
              file=sys.stderr)
        return 1

    referenced = {rid: 0 for rid in rules_by_id}
    for e in opcodes:
        for ref in e.get("rule_refs") or []:
            if ref in referenced:
                referenced[ref] += 1
    print(
        f"check-legality-invariants: PASS "
        f"(root n=2: {len(ROOT_N_MNEMONICS)} mnemonics, rule '{ROOT_N_RULE}' "
        f"referenced {referenced.get(ROOT_N_RULE, 0)}×; "
        f"renames {len(RULE_RENAMES)} 项旧 id 0 命中)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
