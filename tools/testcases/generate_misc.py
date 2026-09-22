#!/usr/bin/env python3
"""Generate misc.yaml test vectors for TESTCASES-007t.

Covers 3 M1 identities in tests/vectors/isa/misc.yaml:
  - swym-iiii (iiii): encoding + semantic (nop-like, no architectural state change)
  - illi (oiii): legality only (always ILLI; encoding/semantic exempt per F6)
  - fence (oiii): encoding + legality (SBZ non-zero → ILLI) + semantic

Spec-first: all encoding words, expected values, and spec_cite derived from
contracts/opcodes.yaml, .tao/knowledge/contract-isa.md §7/§8/§9,
contracts/legality_rules.yaml (sbz_nonzero rule), and
.tao/knowledge/adr-0004-test-machine.md.

Encoding derivations:
  - swym 0: op=0x77, immu24=0 → word=0x77000000
    mask=0xFF000000, value=0x77000000 → (0x77000000 & 0xFF000000)==0x77000000 ✓
  - illi 0: op=0x00, ha=0x00, immu18=0 → word=0x00000000
    mask=0xFFFC0000, value=0x00000000 → (0x00000000 & 0xFFFC0000)==0x00000000 ✓
  - fence 0: op=0x00, ha=0x01, immu18=0 → word=0x00040000
    mask=0xFFFC0000, value=0x00040000 → (0x00040000 & 0xFFFC0000)==0x00040000 ✓
  - fence with SBZ non-zero (ILLI): ha=0x01, immu18_hi=1 → word=0x00050000
    (0x00050000 & 0xFFFC0000)==0x00040000 ✓; bits[17:12]=0x01≠0 → ILLI
"""

import os
import sys

# REPO derived from this file's location (tools/testcases/generate_misc.py)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO, "tests", "vectors", "isa")
OUT_FILE = os.path.join(OUT_DIR, "misc.yaml")

GENERATOR_PATH = "tools/testcases/generate_misc.py"

# ── Encoding words ────────────────────────────────────────────────────
SWYM_WORD0 = 0x77000000       # swym 0 (nop)
ILLI_WORD0 = 0x00000000       # illi 0 (always ILLI; also §8.3 all-zero word)
FENCE_WORD0 = 0x00040000      # fence 0 (barrier type=0, all SBZ zero)
FENCE_SBZ_NONZERO = 0x00050000  # fence with immu18_hi=1 (bits[17:12]≠0, SBZ → ILLI)

MASK_SWYM = 0xFF000000
VALUE_SWYM = 0x77000000
MASK_OIII = 0xFFFC0000
VALUE_ILLI = 0x00000000
VALUE_FENCE = 0x00040000


def _hex8(w):
    return "0x%08X" % w


def _verify(word, mask, value):
    assert (word & mask) == value, \
        "encoding verification failed: (0x%08X & 0x%08X) != 0x%08X" % (word, mask, value)


# Verify all encodings before generating
_verify(SWYM_WORD0, MASK_SWYM, VALUE_SWYM)
_verify(ILLI_WORD0, MASK_OIII, VALUE_ILLI)
_verify(FENCE_WORD0, MASK_OIII, VALUE_FENCE)
_verify(FENCE_SBZ_NONZERO, MASK_OIII, VALUE_FENCE)


def _case(mnemonic, insn, fmt, cls, word, input_state, expected_state,
          expected_fault=None, expected_pc=None, spec_cite="", notes="",
          status="active", deferred_reason=None):
    return {
        "mnemonic": mnemonic,
        "insn": insn,
        "format": fmt,
        "class": cls,
        "encoding": {"word": _hex8(word)},
        "input_state": input_state,
        "expected_state": expected_state,
        "expected_pc": expected_pc,
        "expected_fault": expected_fault,
        "status": status,
        "deferred_reason": deferred_reason,
        "spec_cite": spec_cite,
        "notes": notes,
    }


def generate():
    cases = []

    # ── swym-iiii ─────────────────────────────────────────────────────
    # F10: encoding case — word matches mask/value, decodable, no fault
    cases.append(_case(
        mnemonic="swym",
        insn="swym-iiii",
        fmt="iiii",
        cls="encoding",
        word=SWYM_WORD0,
        input_state={},
        expected_state=None,
        expected_fault=None,
        expected_pc=None,
        spec_cite="SimRISC-04 §占位指令",
        notes="encoding: swym 0 (nop), word=0x77000000; "
              "opcodes.yaml mask=0xFF000000 value=0x77000000; "
              "no fault, no architectural state change",
    ))

    # F10: semantic case — nop-like, no state change
    cases.append(_case(
        mnemonic="swym",
        insn="swym-iiii",
        fmt="iiii",
        cls="semantic",
        word=SWYM_WORD0,
        input_state={},
        expected_state={},
        expected_fault=None,
        expected_pc=None,
        spec_cite="SimRISC-04 §占位指令",
        notes="semantic: swym 0 (nop); "
              "除 PC 自增外无任何架构副作用（§7.1）; "
              "expected_state={}: no registers/memory changed",
    ))

    # ── illi (oiii) ───────────────────────────────────────────────────
    # F6: illi is always ILLI → encoding/semantic exempt; coverage via legality
    cases.append(_case(
        mnemonic="illi",
        insn="illi",
        fmt="oiii",
        cls="legality",
        word=ILLI_WORD0,
        input_state={},
        expected_state=None,
        expected_fault="ILLI",
        expected_pc=None,
        spec_cite="SimRISC-04 §非法指令; SimRISC-00 §MISC-AMO 指令编码",
        notes="illi always triggers ILLI (§9.1); "
              "encoding/semantic exempt per F6 (schema.md §encoding 类对恒 fault 指令的豁免); "
              "this word=0x00000000 is also §8.3 all-zero word (illi 0); "
              "coverage for (illi, oiii) satisfied by this legality case",
    ))

    # ── fence (oiii) ──────────────────────────────────────────────────
    # F10: encoding case — word matches mask/value, decodable, no fault
    cases.append(_case(
        mnemonic="fence",
        insn="fence",
        fmt="oiii",
        cls="encoding",
        word=FENCE_WORD0,
        input_state={},
        expected_state=None,
        expected_fault=None,
        expected_pc=None,
        status="deferred",
        deferred_reason="fence 实现缺失（ISS-056）：trans_fence 为 ILLI 桩，nop/SBZ 语义未实现；用户 2026-09-21 裁定 deferred",
        spec_cite="SimRISC-04 §fence指令",
        notes="encoding: fence 0 (barrier type=0, all SBZ bits zero); "
              "opcodes.yaml mask=0xFFFC0000 value=0x00040000; "
              "immu18=0 → bits[17:4] all zero (SBZ satisfied); "
              "nop-like, no architectural state change",
    ))

    # F10: legality — SBZ non-zero → ILLI
    cases.append(_case(
        mnemonic="fence",
        insn="fence",
        fmt="oiii",
        cls="legality",
        word=FENCE_SBZ_NONZERO,
        input_state={},
        expected_state=None,
        expected_fault="ILLI",
        expected_pc=None,
        status="deferred",
        deferred_reason="fence 实现缺失（ISS-056）：trans_fence 为 ILLI 桩，nop/SBZ 语义未实现；用户 2026-09-21 裁定 deferred",
        spec_cite="SimRISC-04 §fence指令; ADR-0004 D5.3",
        notes="fence with SBZ non-zero: immu18_hi=0x01 (bits[17:12]≠0); "
              "legality_rules.yaml rule=sbz_nonzero: "
              "SBZ (Should Be Zero) fields non-zero → ILLI; "
              "fence bits[17:4] are SBZ per §7.3; "
              "this word=0x00050000 has bits[17:4]=0x001≠0",
    ))

    # F10: semantic — nop-like, no state change
    cases.append(_case(
        mnemonic="fence",
        insn="fence",
        fmt="oiii",
        cls="semantic",
        word=FENCE_WORD0,
        input_state={},
        expected_state=None,  # deferred ⇒ 必须 null（validator 规则）
        expected_fault=None,
        expected_pc=None,
        status="deferred",
        deferred_reason="fence 实现缺失（ISS-056）：trans_fence 为 ILLI 桩，nop/SBZ 语义未实现；用户 2026-09-21 裁定 deferred",
        spec_cite="SimRISC-04 §fence指令",
        notes="semantic: fence 0 (nop-like in M1); "
              "memory barrier, no register/memory change in M1 context; "
              "expected_state={}: no registers/memory changed; "
              "expected_pc=null (PC顺延不算改变PC, schema.md §expected_pc)",
    ))

    return cases


def write_yaml(cases):
    """Write misc.yaml with a header pointing to this generator."""
    import yaml

    header = (
        "# Generated by %s — DO NOT EDIT\n"
        "# Source: contracts/opcodes.yaml + contract-isa.md §7/§8/§9 "
        "+ legality_rules.yaml (sbz_nonzero)\n"
        "# Each case has spec_cite and notes for traceability.\n"
        "# Covers: swym-iiii (iiii), illi (oiii), fence (oiii) — 3 M1 identities\n"
        "# F6: illi encoding/semantic exempt (always ILLI), coverage via legality\n"
        "# F10: swym/fence encoding words verified against opcodes.yaml mask/value\n"
    ) % GENERATOR_PATH

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        f.write(header)
        yaml.dump(cases, f, default_flow_style=False, sort_keys=False,
                  allow_unicode=True, width=120)


def main():
    cases = generate()
    print("Generated %d cases for misc.yaml:" % len(cases))
    for i, c in enumerate(cases):
        print("  [%d] %s %s %s" % (i, c["insn"], c["format"], c["class"]))
    write_yaml(cases)
    print("Written to: %s" % OUT_FILE)


if __name__ == "__main__":
    main()
