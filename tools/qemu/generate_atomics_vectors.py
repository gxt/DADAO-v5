#!/usr/bin/env python3
"""Generate the L3 atomic vectors — `fence` + the 24 `lr`/`sc` identities.

Source of truth (Spec-first; nothing is read back from QEMU or LLVM):
  * contracts/opcodes.yaml          — encoding (op/ha/mask/value), id, format
  * spec/SimRISC-12: fence指令 / LR-SC指令     — fence bit fields, lr/sc semantics
  * .tao/adr/adr-0034-atomics-encoding.md — `D2` (fence fields), `D6`
    (alignment per data width, reservation rules)
  * user ruling 2026-10-21 「甲」    — alignment = per data width
    (.b=1 / .w=2 / .t=4 / .o=8)

Independent oracle (hand-derived from the spec, not from the implementation):

  big-endian byte offset   k     = addr & 7
  value extraction         v     = (word >> ((8 - k - W) * 8)) & (2**(8W) - 1)
  store-conditional merge  new   = (word & ~(m << shift)) | ((val & m) << shift)
                                   with m = 2**(8W) - 1, shift = (8 - k - W) * 8
  lr narrow widths are zero-extended to 64 bits; sc.o has k = 0 by definition.

The vectors carry `sequence: [word, ...]` where the semantic answer needs more
than one instruction (`sc` can only succeed after a same-word `lr`; the
"reservation is cleared on failure" rule needs lr → failing sc → sc).
`sequence` is an optional harness field: without it the emitted binary is
byte-identical to the single-word path (tests/scripts/build_test_binary.py).

Output (wired into `check-qemu-semantics` by the Makefile carrier list):
  tests/vectors/atomics/atomics-lrsc.yaml
  tests/vectors/atomics/atomics-fence.yaml

Usage:
  python3 tools/qemu/generate_atomics_vectors.py           # write both YAMLs
  python3 tools/qemu/generate_atomics_vectors.py --check   # fail on drift
"""

from __future__ import annotations

import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES = os.path.join(ROOT, "contracts", "opcodes.yaml")
OUT_DIR = os.path.join(ROOT, "tests", "vectors", "atomics")
OUT_LRSC = os.path.join(OUT_DIR, "atomics-lrsc.yaml")
OUT_FENCE = os.path.join(OUT_DIR, "atomics-fence.yaml")

SPEC_LRSC = "SimRISC-12: LR-SC指令"
SPEC_FENCE = "SimRISC-12: fence指令"

WIDTH = {"o": 8, "t": 4, "w": 2, "b": 1}

# RAM window (ADR-0004 R3 rev. 2026-10-11): 48-bit canonical form below.
WORD_A = 0x0000FC0000001000          # 8-byte aligned data word
WORD_B = 0x0000FC0000001100          # second 8-byte word (address-mismatch cases)
BASE_WORD = 0x0102030405060708       # 8 distinct bytes: every k/W shift is visible
SC_VAL = 0xA1B2C3D4E5F60718          # distinct bytes; high bits prove truncation
SENTINEL = 0xDEADBEEFCAFEF00D        # untouched-register marker

# fence field bits (immu18[11:6] = pred, immu18[5:0] = succ; SimRISC-12: fence指令)
F_R, F_W, F_I, F_O = 0x01, 0x02, 0x04, 0x08
F_SBZ = 0x30


def _int(v):
    if isinstance(v, int):
        return v
    return int(str(v).strip(), 0)


def _hex64(v):
    return "0x%016X" % (v & 0xFFFFFFFFFFFFFFFF)


def _hex48(v):
    return "0x%012X" % (v & 0xFFFFFFFFFFFF)


def be_extract(word, k, width):
    """Independent oracle: big-endian extraction of `width` bytes at offset k."""
    shift = (8 - k - width) * 8
    return (word >> shift) & ((1 << (width * 8)) - 1)


def be_merge(word, k, width, val):
    """Independent oracle: big-endian merge of `val`'s low `width` bytes at k."""
    mask = (1 << (width * 8)) - 1
    shift = (8 - k - width) * 8
    return (word & ~(mask << shift)) | ((val & mask) << shift)


def mem_chunks(word, base, width):
    """Split an 8-byte word into `width`-byte memory entries (harness loader).

    The loader writes each entry with a `width`-wide store derived from the
    vector's mnemonic, so the chunks reproduce the word byte for byte while the
    loader additionally proves that each chunk is storable at that address.
    """
    out = []
    for i in range(0, 8, width):
        chunk = (word >> ((8 - i - width) * 8)) & ((1 << (width * 8)) - 1)
        out.append({"address": _hex48(base + i),
                    "value": "0x%0*X" % (width * 2, chunk)})
    return out


def case(rec, cls, word, input_state, expected_state, fault, cite, notes,
         sequence=None):
    c = {
        "mnemonic": rec["mnemonic"],
        "id": rec["id"],
        "format": rec["format"],
        "class": cls,
        "encoding": {"word": "0x%08X" % word},
        "input_state": input_state,
        "expected_state": expected_state,
        "expected_pc": None,
        "expected_fault": fault,
        "status": "active",
        "deferred_reason": None,
        "spec_cite": cite,
        "notes": notes,
    }
    if sequence is not None:
        c["sequence"] = ["0x%08X" % w for w in sequence]
    return c


def state(rd=None, rb=None, memory=None):
    return {
        "rd": {k: _hex64(v) for k, v in (rd or {}).items()},
        "rb": {k: _hex48(v) for k, v in (rb or {}).items()},
        "ra": {},
        "memory": memory or [],
    }


# ---------------------------------------------------------------------------
# encoding helpers
# ---------------------------------------------------------------------------

def build_word(rec, hb, hc, hd):
    return ((_int(rec["op"]) << 24) | (_int(rec["ha"]) << 18)
            | ((hb & 0x3F) << 12) | ((hc & 0x3F) << 6) | (hd & 0x3F))


def lr_word(rec, dest_rd, addr_rb, dest_field=None):
    """lr: hb must be rd0, hc = destination rd, hd = address rb."""
    return build_word(rec, 0 if dest_field is None else dest_field,
                      dest_rd, addr_rb)


def sc_word(rec, flag_rd, data_rd, addr_rb):
    """sc: hb = rdHB (0/1 result), hc = rdHC (data), hd = rbHD (address)."""
    return build_word(rec, flag_rd, data_rd, addr_rb)


def fence_word(rec, immu18):
    """Fence word: op/ha come from opcodes.yaml (no hardcoded encoding)."""
    return ((_int(rec["op"]) << 24) | (_int(rec["ha"]) << 18)
            | (immu18 & 0x3FFFF))


# ---------------------------------------------------------------------------
# lr / sc cases
# ---------------------------------------------------------------------------

LR_K = {"o": [0, 0, 0],          # 3 encodings (nn/an/ar): only k=0 is legal
        "t": [0, 4, 4],          # addr & 7 == 4 is LEGAL for .t (user ruling 甲)
        "w": [0, 4, 2],
        "b": [0, 3, 7]}

SC_K = {"o": [0, 0, 0],
        "t": [0, 4, 4],
        "w": [0, 2, 6],
        "b": [0, 3, 7]}

# Misaligned addresses per width (width > 1 only; every byte address is aligned
# for .b, which is exactly the ruling 「甲」).
MISALIGN = {"o": 4, "t": 2, "w": 1}


def gen_lr_cases(rec):
    width_char = rec["mnemonic"].split(".")[1]
    width = WIDTH[width_char]
    k = LR_K[width_char][["nn", "an", "ar"].index(rec["mnemonic"].split(".")[2])]
    out = []

    # 1. semantic (also proves the reservation: the trailing sc succeeds)
    addr = WORD_A + k
    lr = lr_word(rec, dest_rd=2, addr_rb=4)
    sc_rec = SC_BY_MNEMONIC["sc.%s.nn" % width_char]
    seq = [lr, sc_word(sc_rec, flag_rd=5, data_rd=6, addr_rb=4)]
    merged = be_merge(BASE_WORD, k, width, SC_VAL)
    out.append(case(
        rec, "semantic", lr,
        state(rd={"rd1": SENTINEL, "rd2": 0, "rd5": 0xFFFFFFFFFFFFFFFF,
                  "rd6": SC_VAL},
              rb={"rb4": addr},
              memory=mem_chunks(BASE_WORD, WORD_A, width)),
        state(rd={"rd1": SENTINEL,
                  "rd2": be_extract(BASE_WORD, k, width),
                  "rd5": 0},
              memory=mem_chunks(merged, WORD_A, width)),
        None, SPEC_LRSC,
        "%s: k=%d W=%d -> rd2 = zero-extended big-endian window = 0x%X; the "
        "reservation is proven by the trailing sc (rd5=0, word merged)"
        % (rec["mnemonic"], k, width, be_extract(BASE_WORD, k, width)),
        sequence=seq))

    # 2. boundary: the highest legal k for this width (o: none beyond k=0)
    if width < 8:
        k_hi = 8 - width
        addr_hi = WORD_A + k_hi
        word = lr_word(rec, dest_rd=2, addr_rb=5)
        out.append(case(
            rec, "boundary", word,
            state(rd={"rd1": SENTINEL, "rd2": 0}, rb={"rb5": addr_hi},
                  memory=mem_chunks(BASE_WORD, WORD_A, width)),
            state(rd={"rd1": SENTINEL,
                      "rd2": be_extract(BASE_WORD, k_hi, width)},
                  memory=mem_chunks(BASE_WORD, WORD_A, width)),
            None, SPEC_LRSC + "; 用户裁定 2026-10-21「甲」",
            "boundary %s: k=%d (= 8-W, still naturally aligned) is legal and "
            "reads the last W bytes of the word" % (rec["mnemonic"], k_hi)))

    # 3. MALIGN: below the *data width* alignment (user ruling 「甲」)
    if width > 1:
        off = MISALIGN[width_char]
        word = lr_word(rec, dest_rd=2, addr_rb=4)
        out.append(case(
            rec, "legality", word,
            state(rb={"rb4": WORD_A + off}),
            None, "MALIGN", SPEC_LRSC + "; 用户裁定 2026-10-21「甲」",
            "legality %s: addr & %d != 0 -> MALIGN, never ILLI/CFXMEM"
            % (rec["mnemonic"], width - 1)))

    # 4. ILLI: hand-encoded hb != rd0
    word = lr_word(rec, dest_rd=2, addr_rb=4, dest_field=2)
    out.append(case(
        rec, "legality", word, state(), None, "ILLI", SPEC_LRSC,
        "legality %s: rdHB = rd2 != rd0 -> ILLI (lr carries only two operands)"
        % rec["mnemonic"]))

    return out


def gen_sc_cases(rec):
    width_char = rec["mnemonic"].split(".")[1]
    width = WIDTH[width_char]
    order = rec["mnemonic"].split(".")[2]
    k = SC_K[width_char][["nn", "nr", "ar"].index(order)]
    lr_rec = LR_BY_MNEMONIC["lr.%s.nn" % width_char]
    out = []

    # 1. success: an `lr` of the same width/address immediately precedes it
    lr = lr_word(lr_rec, dest_rd=2, addr_rb=4)
    sc = sc_word(rec, flag_rd=5, data_rd=6, addr_rb=4)
    merged = be_merge(BASE_WORD, k, width, SC_VAL)
    out.append(case(
        rec, "semantic", sc,
        state(rd={"rd1": SENTINEL, "rd2": 0, "rd5": 0xFFFFFFFFFFFFFFFF,
                  "rd6": SC_VAL},
              rb={"rb4": WORD_A + k},
              memory=mem_chunks(BASE_WORD, WORD_A, width)),
        state(rd={"rd1": SENTINEL,
                  "rd2": be_extract(BASE_WORD, k, width),
                  "rd5": 0},
              memory=mem_chunks(merged, WORD_A, width)),
        None, SPEC_LRSC,
        "%s after %s: k=%d W=%d -> rd5=0 (success), only the addressed W bytes "
        "change (merged word 0x%X)"
        % (rec["mnemonic"], lr_rec["mnemonic"], k, width, merged),
        sequence=[lr, sc]))

    # 2. failure: no reservation at all -> no write, rdHB=1
    sc_only = sc_word(rec, flag_rd=5, data_rd=6, addr_rb=4)
    out.append(case(
        rec, "semantic", sc_only,
        state(rd={"rd1": SENTINEL, "rd5": 0xFFFFFFFFFFFFFFFF, "rd6": SC_VAL},
              rb={"rb4": WORD_A + k},
              memory=mem_chunks(BASE_WORD, WORD_A, width)),
        state(rd={"rd1": SENTINEL, "rd5": 1},
              memory=mem_chunks(BASE_WORD, WORD_A, width)),
        None, SPEC_LRSC,
        "failure %s: no lr was executed -> rd5=1, memory unchanged"
        % rec["mnemonic"]))

    # 3. failure: reservation held for a DIFFERENT word -> no write, rdHB=1
    lr_a = lr_word(lr_rec, dest_rd=2, addr_rb=4)
    sc_b = sc_word(rec, flag_rd=5, data_rd=6, addr_rb=5)
    out.append(case(
        rec, "semantic", sc_b,
        state(rd={"rd1": SENTINEL, "rd2": 0, "rd5": 0xFFFFFFFFFFFFFFFF,
                  "rd6": SC_VAL},
              rb={"rb4": WORD_A, "rb5": WORD_B + k},
              memory=mem_chunks(BASE_WORD, WORD_A, width)
                     + mem_chunks(BASE_WORD, WORD_B, width)),
        state(rd={"rd1": SENTINEL,
                  "rd2": be_extract(BASE_WORD, 0, width), "rd5": 1},
              memory=mem_chunks(BASE_WORD, WORD_A, width)
                     + mem_chunks(BASE_WORD, WORD_B, width)),
        None, SPEC_LRSC,
        "failure %s: the reservation is for word A, sc targets word B -> "
        "rd5=1, neither word is written" % rec["mnemonic"],
        sequence=[lr_a, sc_b]))

    # 4. reservation is cleared on FAILURE: lr A, failing sc B, then sc A must
    #    fail too (if the reservation survived, the last sc would succeed and
    #    write word A -> the expected memory word A would break).
    sc_b2 = sc_word(rec, flag_rd=5, data_rd=6, addr_rb=5)
    sc_a2 = sc_word(rec, flag_rd=5, data_rd=6, addr_rb=4)
    out.append(case(
        rec, "semantic", sc_a2,
        state(rd={"rd1": SENTINEL, "rd2": 0, "rd5": 0xFFFFFFFFFFFFFFFF,
                  "rd6": SC_VAL},
              rb={"rb4": WORD_A + k, "rb5": WORD_B + k},
              memory=mem_chunks(BASE_WORD, WORD_A, width)
                     + mem_chunks(BASE_WORD, WORD_B, width)),
        state(rd={"rd1": SENTINEL,
                  "rd2": be_extract(BASE_WORD, k, width), "rd5": 1},
              memory=mem_chunks(BASE_WORD, WORD_A, width)
                     + mem_chunks(BASE_WORD, WORD_B, width)),
        None, SPEC_LRSC,
        "clear-on-failure %s: lr A -> sc B (fails) -> sc A must also fail "
        "(rd5=1, word A unchanged); a surviving reservation would write A"
        % rec["mnemonic"],
        sequence=[lr_a, sc_b2, sc_a2]))

    # 5. MALIGN without a reservation (alignment is checked first)
    if width > 1:
        off = MISALIGN[width_char]
        out.append(case(
            rec, "legality", sc_word(rec, flag_rd=5, data_rd=6, addr_rb=4),
            state(rd={"rd5": 0xFFFFFFFFFFFFFFFF, "rd6": SC_VAL},
                  rb={"rb4": WORD_A + off},),
            None, "MALIGN", SPEC_LRSC + "; 用户裁定 2026-10-21「甲」",
            "legality %s: addr & %d != 0 -> MALIGN even with no reservation"
            % (rec["mnemonic"], width - 1)))
        # 6. MALIGN with a reservation held (must not fall through to the CAS)
        lr_ok = lr_word(lr_rec, dest_rd=2, addr_rb=4)
        out.append(case(
            rec, "legality", sc_word(rec, flag_rd=5, data_rd=6, addr_rb=5),
            state(rd={"rd2": 0, "rd5": 0xFFFFFFFFFFFFFFFF, "rd6": SC_VAL},
                  rb={"rb4": WORD_A, "rb5": WORD_A + off},
                  memory=mem_chunks(BASE_WORD, WORD_A, width)),
            None, "MALIGN", SPEC_LRSC + "; 用户裁定 2026-10-21「甲」",
            "legality %s: a held reservation does not bypass the width "
            "alignment check (MALIGN)" % rec["mnemonic"],
            sequence=[lr_ok, sc_word(rec, flag_rd=5, data_rd=6, addr_rb=5)]))

    return out


# ---------------------------------------------------------------------------
# fence cases
# ---------------------------------------------------------------------------

def fence_fields(pred, succ, fm=0):
    return (fm << 12) | ((pred & 0x3F) << 6) | (succ & 0x3F)


def gen_fence_cases(rec):
    out = []
    pred_ok = {
        "noop (pred=succ=0)": (0, 0),
        "succ-only R": (0, F_R),
        "pred-only R": (F_R, 0),
        "R->R": (F_R, F_R),
        "W->W": (F_W, F_W),
        "R->W": (F_R, F_W),
        "W->R": (F_W, F_R),
        "R|W->R|W": (F_R | F_W, F_R | F_W),
        "acquire (R -> R|W, LLVM 0x043)": (F_R, F_R | F_W),
        "release (R|W -> W, LLVM 0x0C2)": (F_R | F_W, F_W),
        "acq_rel (R|W|I|O -> R|W|I|O, LLVM 0x3CF)":
            (F_R | F_W | F_I | F_O, F_R | F_W | F_I | F_O),
        "I/O classes (pred=I|O -> succ=I)": (F_I | F_O, F_I),
    }
    for name, (pred, succ) in pred_ok.items():
        immu18 = fence_fields(pred, succ)
        out.append(case(
            rec, "semantic", fence_word(rec, immu18),
            state(rd={"rd1": SENTINEL}), state(rd={"rd1": SENTINEL}),
            None, SPEC_FENCE,
            "fence fm=0 pred=0x%02X succ=0x%02X (%s): legal, no architecture "
            "state changes (bar ordering itself is asserted by the evidence "
            "script via -d op; pred=succ=0 emits no barrier at all)"
            % (pred, succ, name)))

    bad = {
        "fm=1 (reserved)": fence_fields(F_R, F_R, fm=1),
        "fm=8 (TSO-reserved, undefined)": fence_fields(F_R, F_R, fm=8),
        "fm=63 (reserved)": fence_fields(0, 0, fm=63),
        "pred[11:10] SBZ != 0 (bit 4)": fence_fields(F_SBZ, F_R),
        "pred[11:10] SBZ != 0 (bit 5)": fence_fields(0x20, F_R),
        "succ[5:4] SBZ != 0 (bit 4)": fence_fields(F_R, F_SBZ),
        "succ[5:4] SBZ != 0 (bit 5)": fence_fields(F_R, 0x20),
    }
    for name, immu18 in bad.items():
        out.append(case(
            rec, "legality", fence_word(rec, immu18), state(), None, "ILLI",
            SPEC_FENCE + "; ADR-0034 D2",
            "legality fence %s -> ILLI" % name))

    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

OPCODES_DB = {}
SC_BY_MNEMONIC = {}
LR_BY_MNEMONIC = {}

HEADER_LRSC = (
    "# Generated by tools/qemu/generate_atomics_vectors.py — DO NOT EDIT\n"
    "# Source: contracts/opcodes.yaml + spec/SimRISC-12: LR-SC指令 + ADR-0034 D6\n"
    "# Independent oracle (hand-derived, no QEMU feedback):\n"
    "#   k = addr & 7; shift = (8 - k - W) * 8\n"
    "#   lr  value  = (word >> shift) & (2**(8W) - 1)        [zero-extended]\n"
    "#   sc  word'  = (word & ~(m << shift)) | ((val & m) << shift), m = 2**(8W)-1\n"
    "# Alignment = per data width (.b=1/.w=2/.t=4/.o=8; user ruling 2026-10-21 甲)\n"
    "# `sequence:` runs several raw encodings back to back (sc needs a prior lr).\n\n")

HEADER_FENCE = (
    "# Generated by tools/qemu/generate_atomics_vectors.py — DO NOT EDIT\n"
    "# Source: contracts/opcodes.yaml + spec/SimRISC-12: fence指令 + ADR-0034 D1/D2\n"
    "# fence immu18 = fm[17:12] | pred[11:6] | succ[5:0];\n"
    "# field bits R=1<<0 W=1<<1 I=1<<2 O=1<<3; SBZ = field bits [5:4].\n"
    "# Legality: fm != 0 or SBZ != 0 => ILLI; pred = succ = 0 => no-op.\n"
    "# Independent oracle: the fields above are decoded by hand from the spec;\n"
    "# the barrier *strength* is asserted by the evidence script (TCG op dump),\n"
    "# because a barrier has no architecturally visible state change.\n\n")


def main() -> int:
    with open(OPCODES, encoding="utf-8") as fh:
        records = yaml.safe_load(fh)
    for r in records:
        OPCODES_DB[r["mnemonic"]] = r
        if r.get("mnemonic", "").startswith(("lr.",)):
            LR_BY_MNEMONIC[r["mnemonic"]] = r
        if r.get("mnemonic", "").startswith(("sc.",)):
            SC_BY_MNEMONIC[r["mnemonic"]] = r

    lr_recs = [OPCODES_DB[m] for m in sorted(LR_BY_MNEMONIC)]
    sc_recs = [OPCODES_DB[m] for m in sorted(SC_BY_MNEMONIC)]
    assert len(lr_recs) == 12, len(lr_recs)
    assert len(sc_recs) == 12, len(sc_recs)
    fence_rec = OPCODES_DB["fence"]

    lrsc_cases = []
    for rec in lr_recs:
        lrsc_cases.extend(gen_lr_cases(rec))
    for rec in sc_recs:
        lrsc_cases.extend(gen_sc_cases(rec))
    fence_cases = gen_fence_cases(fence_rec)

    lrsc_text = HEADER_LRSC + yaml.dump(
        lrsc_cases, default_flow_style=False, allow_unicode=True, width=120)
    fence_text = HEADER_FENCE + yaml.dump(
        fence_cases, default_flow_style=False, allow_unicode=True, width=120)

    if "--check" in sys.argv:
        bad = 0
        for path, text in ((OUT_LRSC, lrsc_text), (OUT_FENCE, fence_text)):
            try:
                with open(path, encoding="utf-8") as fh:
                    committed = fh.read()
            except FileNotFoundError:
                print("generate_atomics_vectors: MISSING %s" % path)
                bad = 1
                continue
            if committed != text:
                print("generate_atomics_vectors: DRIFT %s" % path)
                bad = 1
        if bad:
            return 1
        print("generate_atomics_vectors: PASS (%d lr/sc + %d fence cases, "
              "byte-identical)" % (len(lrsc_cases), len(fence_cases)))
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    for path, text in ((OUT_LRSC, lrsc_text), (OUT_FENCE, fence_text)):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print("generate_atomics_vectors: wrote %s (%d cases) and %s (%d cases)"
          % (os.path.relpath(OUT_LRSC, ROOT), len(lrsc_cases),
             os.path.relpath(OUT_FENCE, ROOT), len(fence_cases)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
