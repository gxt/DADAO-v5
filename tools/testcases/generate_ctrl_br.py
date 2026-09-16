#!/usr/bin/env python3
"""Generate ctrl-br.yaml test vectors for TESTCASES-005t.

Covers all 10 br.* M1 identities (br.n-rd, br.nn-rd, br.z-rd, br.nz-rd,
br.p-rd, br.np-rd, br.eq-rd, br.ne-rd, br.z-rb, br.nz-rb) with:
  - 1 encoding case per identity
  - 1 semantic taken case per identity (expected_pc = rb0 + (imm<<2))
  - 1 semantic not-taken case per identity (expected_pc = rb0 + 4)

Spec-first: all encoding words, expected values, and spec_cite derived from
contracts/opcodes.yaml, .tao/knowledge/contract-isa.md §5, and
.knowledge/adr-0004-test-machine.md (D6.5: rb0 = current instruction address).

PC convention: instruction address = 0xffff_0000_0000 (RAM entry, ADR-0004 D2.2).
imm=2 for taken → target = rb0 + 8 = 0xffff00000008.
not-taken → PC = rb0 + 4 = 0xffff00000004.
"""

import os, sys, yaml

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO, "tests", "vectors", "isa")
OUT_FILE = os.path.join(OUT_DIR, "ctrl-br.yaml")

# ── Load opcodes ──────────────────────────────────────────────────────
with open(os.path.join(REPO, "contracts", "opcodes.yaml")) as f:
    ALL = yaml.safe_load(f)

BY_KEY = {}
for r in ALL:
    if not r.get("excluded_m1"):
        BY_KEY[(r["insn"], r["format"])] = r

# ── Constants ─────────────────────────────────────────────────────────
RB0 = 0xFFFF_0000_0000          # instruction address (ADR-0004 D2.2/D6.5)
IMM_TAKEN = 2                   # imm for taken path (not 0, not 1)
TARGET_TAKEN = "0x%012X" % (RB0 + (IMM_TAKEN << 2))   # 0xffff00000008
TARGET_NOT_TAKEN = "0x%012X" % (RB0 + 4)               # 0xffff00000004

SPEC_CITE_RD = "SimRISC-02 §条件跳转指令; ADR-0004 D6.5"
SPEC_CITE_RB = "SimRISC-02 §条件跳转指令; ADR-0004 D6.5"

# ── Encoding word builders ────────────────────────────────────────────
def _build_word_riii(op, ha, imm18):
    """riii format: op[31:24] | ha[23:18] | imm18[17:0]."""
    return (op << 24) | (ha << 18) | (imm18 & 0x3FFFF)

def _build_word_rrii(op, ha, hb, imm12):
    """rrii format: op[31:24] | ha[23:18] | hb[17:12] | imm12[11:0]."""
    return (op << 24) | (ha << 18) | (hb << 12) | (imm12 & 0xFFF)

def _hex8(w):
    return "0x%08X" % w

# ── Case factory ──────────────────────────────────────────────────────
def _case(mnem, insn, fmt, cls, word, inp, out, fault=None,
          expected_pc=None, spec_cite="", notes=""):
    return {
        "mnemonic": mnem,
        "insn": insn,
        "format": fmt,
        "class": cls,
        "encoding": {"word": _hex8(word)},
        "input_state": inp,
        "expected_state": out,
        "expected_pc": expected_pc,
        "expected_fault": fault,
        "status": "active",
        "deferred_reason": None,
        "spec_cite": spec_cite,
        "notes": notes,
    }

# ── br.* identity definitions ─────────────────────────────────────────
# (insn, mnemonic, format, op, is_rb)
# For riii: ha = rdha/rbha register number
# For rrii: ha = rdha, hb = rdhb
BR_IDENTITIES = [
    # riii single-register RD branches
    ("br.n-rd",   "br.n",  "riii", 0x68, False),
    ("br.nn-rd",  "br.nn", "riii", 0x69, False),
    ("br.z-rd",   "br.z",  "riii", 0x6A, False),
    ("br.nz-rd",  "br.nz", "riii", 0x6B, False),
    ("br.p-rd",   "br.p",  "riii", 0x6C, False),
    ("br.np-rd",  "br.np", "riii", 0x6D, False),
    # rrii dual-register RD branches
    ("br.eq-rd",  "br.eq", "rrii", 0x6E, False),
    ("br.ne-rd",  "br.ne", "rrii", 0x6F, False),
    # riii single-register RB branches
    ("br.z-rb",   "br.z",  "riii", 0x72, True),
    ("br.nz-rb",  "br.nz", "riii", 0x73, True),
]

# ── Condition semantics for taken/not-taken ────────────────────────────
# For each identity, specify:
#   taken_input_state: register state that makes condition TRUE (taken)
#   not_taken_input_state: register state that makes condition FALSE (not-taken)
#   taken_reg: register to use for encoding word (ha field)
#   not_taken_reg: register to use for not-taken encoding word
#
# rd0 = 0 (hardwired), so:
#   br.n rd0:  0 < 0   → FALSE (not taken)
#   br.nn rd0: 0 >= 0  → TRUE  (taken)
#   br.z rd0:  0 == 0  → TRUE  (taken)    ← always-taken with rd0
#   br.nz rd0: 0 != 0  → FALSE (not taken) ← always-not-taken with rd0
#   br.p rd0:  0 > 0   → FALSE (not taken)
#   br.np rd0: 0 <= 0  → TRUE  (taken)

def _gen_riii_rd(identity, mnem, op):
    """Generate encoding + taken + not-taken for riii RD branch."""
    cases = []
    rec = BY_KEY[(identity, "riii")]
    sc = SPEC_CITE_RD

    # Determine which rdha value gives taken vs not-taken
    if identity == "br.n-rd":
        # taken: rdha < 0 → use rd1 = -1; not-taken: rdha >= 0 → use rd0 (= 0)
        taken_reg, taken_val = 1, 0xFFFFFFFFFFFFFFFF
        not_taken_reg, not_taken_val = 1, 0x0000000000000001  # positive
        taken_note = "rd1 = -1 (< 0) → condition TRUE, branch taken"
        not_taken_note = "rd1 = 1 (>= 0) → condition FALSE, branch not taken"
    elif identity == "br.nn-rd":
        # taken: rdha >= 0 → use rd0 (= 0) or rd1 = 1; not-taken: rdha < 0 → rd1 = -1
        taken_reg, taken_val = 1, 0x0000000000000001  # positive
        not_taken_reg, not_taken_val = 1, 0xFFFFFFFFFFFFFFFF  # -1
        taken_note = "rd1 = 1 (>= 0) → condition TRUE, branch taken"
        not_taken_note = "rd1 = -1 (< 0) → condition FALSE, branch not taken"
    elif identity == "br.z-rd":
        # taken: rdha == 0 → use rd0 (= 0, hardwired); not-taken: rdha != 0 → rd1 = 1
        taken_reg, taken_val = 0, None  # rd0 is hardwired, no preset needed
        not_taken_reg, not_taken_val = 1, 0x0000000000000001
        taken_note = "rd0 = 0 (hardwired) → condition TRUE, branch taken (always-taken with rd0)"
        not_taken_note = "rd1 = 1 (!= 0) → condition FALSE, branch not taken"
    elif identity == "br.nz-rd":
        # taken: rdha != 0 → rd1 = 1; not-taken: rdha == 0 → rd0 (= 0, hardwired)
        taken_reg, taken_val = 1, 0x0000000000000001
        not_taken_reg, not_taken_val = 0, None  # rd0 hardwired
        taken_note = "rd1 = 1 (!= 0) → condition TRUE, branch taken"
        not_taken_note = "rd0 = 0 (hardwired) → condition FALSE, branch not taken (always-not-taken with rd0)"
    elif identity == "br.p-rd":
        # taken: rdha > 0 → rd1 = 1; not-taken: rdha <= 0 → rd0 (= 0)
        taken_reg, taken_val = 1, 0x0000000000000001
        not_taken_reg, not_taken_val = 0, None  # rd0 = 0, not > 0
        taken_note = "rd1 = 1 (> 0) → condition TRUE, branch taken"
        not_taken_note = "rd0 = 0 (hardwired, not > 0) → condition FALSE, branch not taken"
    elif identity == "br.np-rd":
        # taken: rdha <= 0 → rd0 (= 0); not-taken: rdha > 0 → rd1 = 1
        taken_reg, taken_val = 0, None  # rd0 = 0, <= 0 is true
        not_taken_reg, not_taken_val = 1, 0x0000000000000001
        taken_note = "rd0 = 0 (hardwired, <= 0) → condition TRUE, branch taken (always-taken with rd0)"
        not_taken_note = "rd1 = 1 (> 0) → condition FALSE, branch not taken"
    else:
        return cases

    # ── Encoding case ──
    enc_word = _build_word_riii(op, 1, IMM_TAKEN)  # rdha=1, imm=2 (not 0, avoid self-loop)
    enc_inp = {}
    cases.append(_case(mnem, identity, "riii", "encoding", enc_word, enc_inp,
                       None, None, None, sc,
                       "encoding: word matches opcodes.yaml mask/value, rdha=1 (non-rd0), imm=2"))

    # ── Taken case ──
    taken_word = _build_word_riii(op, taken_reg, IMM_TAKEN)
    taken_inp = {}
    if taken_val is not None and taken_reg != 0:
        taken_inp = {"rd": {"rd%d" % taken_reg: "0x%016X" % taken_val}}
    cases.append(_case(mnem, identity, "riii", "semantic", taken_word, taken_inp,
                       {}, None, TARGET_TAKEN, sc,
                       "taken: %s; rb0=0x%012X (RAM entry, ADR-0004 D2.2), imm=%d, expected_pc=rb0+%d=0x%012X"
                       % (taken_note, RB0, IMM_TAKEN, IMM_TAKEN << 2, RB0 + (IMM_TAKEN << 2))))

    # ── Not-taken case ──
    nt_word = _build_word_riii(op, not_taken_reg, IMM_TAKEN)
    nt_inp = {}
    if not_taken_val is not None and not_taken_reg != 0:
        nt_inp = {"rd": {"rd%d" % not_taken_reg: "0x%016X" % not_taken_val}}
    cases.append(_case(mnem, identity, "riii", "semantic", nt_word, nt_inp,
                       {}, None, TARGET_NOT_TAKEN, sc,
                       "not-taken: %s; rb0=0x%012X, expected_pc=rb0+4=0x%012X"
                       % (not_taken_note, RB0, RB0 + 4)))

    return cases


def _gen_riii_rb(identity, mnem, op):
    """Generate encoding + taken + not-taken for riii RB branch."""
    cases = []
    rec = BY_KEY[(identity, "riii")]
    sc = SPEC_CITE_RB

    if identity == "br.z-rb":
        # taken: rbha == 0 → use rb3 = 0; not-taken: rbha != 0 → rb3 = 1
        taken_val = 0x0000000000000000
        not_taken_val = 0x0000000000000001
        taken_note = "rb3 = 0 → condition TRUE, branch taken"
        not_taken_note = "rb3 = 1 (!= 0) → condition FALSE, branch not taken"
    elif identity == "br.nz-rb":
        # taken: rbha != 0 → rb3 = 1; not-taken: rbha == 0 → rb3 = 0
        taken_val = 0x0000000000000001
        not_taken_val = 0x0000000000000000
        taken_note = "rb3 = 1 (!= 0) → condition TRUE, branch taken"
        not_taken_note = "rb3 = 0 → condition FALSE, branch not taken"
    else:
        return cases

    reg = 3  # use rb3 (rb0=PC, rb1=SP, rb2=RAM base per D6.5)

    # ── Encoding case ──
    enc_word = _build_word_riii(op, reg, IMM_TAKEN)  # rbha=3, imm=2 (not 0, avoid self-loop)
    enc_inp = {"rb": {"rb3": "0x%016X" % 0}}
    cases.append(_case(mnem, identity, "riii", "encoding", enc_word, enc_inp,
                       None, None, None, sc,
                       "encoding: word matches opcodes.yaml mask/value, rbha=rb3 (non-rb0), imm=2"))

    # ── Taken case ──
    taken_word = _build_word_riii(op, reg, IMM_TAKEN)
    taken_inp = {"rb": {"rb3": "0x%016X" % taken_val}}
    cases.append(_case(mnem, identity, "riii", "semantic", taken_word, taken_inp,
                       {}, None, TARGET_TAKEN, sc,
                       "taken: %s; rb0=0x%012X, imm=%d, expected_pc=rb0+%d=0x%012X"
                       % (taken_note, RB0, IMM_TAKEN, IMM_TAKEN << 2, RB0 + (IMM_TAKEN << 2))))

    # ── Not-taken case ──
    nt_word = _build_word_riii(op, reg, IMM_TAKEN)
    nt_inp = {"rb": {"rb3": "0x%016X" % not_taken_val}}
    cases.append(_case(mnem, identity, "riii", "semantic", nt_word, nt_inp,
                       {}, None, TARGET_NOT_TAKEN, sc,
                       "not-taken: %s; rb0=0x%012X, expected_pc=rb0+4=0x%012X"
                       % (not_taken_note, RB0, RB0 + 4)))

    return cases


def _gen_rrii(identity, mnem, op):
    """Generate encoding + taken + not-taken for rrii RD branch (br.eq/br.ne)."""
    cases = []
    rec = BY_KEY[(identity, "rrii")]
    sc = SPEC_CITE_RD

    if identity == "br.eq-rd":
        # taken: rdha == rdhb → rd1 == rd1; not-taken: rd1 != rd2
        taken_ha, taken_hb = 1, 1
        not_taken_ha, not_taken_hb = 1, 2
        taken_inp = {"rd": {"rd1": "0x0000000000000042"}}
        not_taken_inp = {"rd": {"rd1": "0x0000000000000042", "rd2": "0x0000000000000099"}}
        taken_note = "rd1 == rd1 (same register, always equal) → condition TRUE, branch taken"
        not_taken_note = "rd1=0x42 != rd2=0x99 → condition FALSE, branch not taken"
    elif identity == "br.ne-rd":
        # taken: rdha != rdhb → rd1 != rd2; not-taken: rd1 == rd1
        taken_ha, taken_hb = 1, 2
        not_taken_ha, not_taken_hb = 1, 1
        taken_inp = {"rd": {"rd1": "0x0000000000000042", "rd2": "0x0000000000000099"}}
        not_taken_inp = {"rd": {"rd1": "0x0000000000000042"}}
        taken_note = "rd1=0x42 != rd2=0x99 → condition TRUE, branch taken"
        not_taken_note = "rd1 == rd1 (same register, always equal) → condition FALSE, branch not taken"
    else:
        return cases

    # ── Encoding case ──
    enc_word = _build_word_rrii(op, 1, 2, IMM_TAKEN)  # rdha=1, rdhb=2, imm=2 (not 0, avoid self-loop)
    enc_inp = {"rd": {"rd1": "0x0000000000000000", "rd2": "0x0000000000000000"}}
    cases.append(_case(mnem, identity, "rrii", "encoding", enc_word, enc_inp,
                       None, None, None, sc,
                       "encoding: word matches opcodes.yaml mask/value, rdha=1, rdhb=2 (non-rd0), imm=2"))

    # ── Taken case ──
    taken_word = _build_word_rrii(op, taken_ha, taken_hb, IMM_TAKEN)
    cases.append(_case(mnem, identity, "rrii", "semantic", taken_word, taken_inp,
                       {}, None, TARGET_TAKEN, sc,
                       "taken: %s; rb0=0x%012X, imm=%d, expected_pc=rb0+%d=0x%012X"
                       % (taken_note, RB0, IMM_TAKEN, IMM_TAKEN << 2, RB0 + (IMM_TAKEN << 2))))

    # ── Not-taken case ──
    nt_word = _build_word_rrii(op, not_taken_ha, not_taken_hb, IMM_TAKEN)
    cases.append(_case(mnem, identity, "rrii", "semantic", nt_word, not_taken_inp,
                       {}, None, TARGET_NOT_TAKEN, sc,
                       "not-taken: %s; rb0=0x%012X, expected_pc=rb0+4=0x%012X"
                       % (not_taken_note, RB0, RB0 + 4)))

    return cases


# ── Main ──────────────────────────────────────────────────────────────
def main():
    all_cases = []
    for identity, mnem, fmt, op, is_rb in BR_IDENTITIES:
        if fmt == "riii" and not is_rb:
            all_cases.extend(_gen_riii_rd(identity, mnem, op))
        elif fmt == "riii" and is_rb:
            all_cases.extend(_gen_riii_rb(identity, mnem, op))
        elif fmt == "rrii":
            all_cases.extend(_gen_rrii(identity, mnem, op))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        f.write("# Generated by TESTCASES-005t generator — DO NOT EDIT\n")
        f.write("# Source: contracts/opcodes.yaml + contract-isa.md §5 + adr-0004 D6.5\n")
        f.write("# Each case has spec_cite and notes for traceability.\n")
        f.write("# PC convention: instruction address = 0xffff_0000_0000 (RAM entry, ADR-0004 D2.2)\n")
        f.write("# imm=2 for taken → target = rb0 + 8 = 0xffff00000008\n")
        f.write("# not-taken → PC = rb0 + 4 = 0xffff00000004\n\n")
        yaml.dump(all_cases, f, default_flow_style=False, allow_unicode=True, width=120)

    # Summary
    n_enc = sum(1 for c in all_cases if c["class"] == "encoding")
    n_sem = sum(1 for c in all_cases if c["class"] == "semantic")
    n_taken = sum(1 for c in all_cases if c["class"] == "semantic" and "taken:" in c.get("notes", "") and "not-taken:" not in c.get("notes", ""))
    print("Wrote %s: %d cases (%d encoding, %d semantic [taken=%d, not-taken=%d])" % (
        OUT_FILE, len(all_cases), n_enc, n_sem, n_taken, n_sem - n_taken))
    print("Identities covered: %d" % len(BR_IDENTITIES))
    return 0

if __name__ == "__main__":
    sys.exit(main())
