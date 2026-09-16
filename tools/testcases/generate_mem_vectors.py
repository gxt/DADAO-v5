#!/usr/bin/env python3
"""Generate the 3 mem-*.yaml test vector files for TESTCASES-004t.

Reads contracts/opcodes.yaml and produces:
  mem-rd.yaml  (22 RD variants: ld.*/st.*/ldm.*/stm.* with RD dest/src)
  mem-rb.yaml  (4 RB variants: ld.o-rb/st.o-rb/ldm.o-rb/stm.o-rb)
  mem-ra.yaml  (4 RA variants: ld.o-ra/st.o-ra/ldm.o-ra/stm.o-ra)

All encoding words, expected values, and spec_cite are derived from
contracts/opcodes.yaml, .tao/knowledge/contract-isa.md, and
.tao/knowledge/adr-0004-test-machine.md.  No LLVM/QEMU reverse-engineering.

F10 design (方案B):
  - encoding class: base=rb3 (unused register), dest=rd1/ra1 (not rd0/ra0),
    store src=rd1/ra1 (not rd0/ra0), immu6=1 for multi.
  - input_state presets rb3=0x0000ffff00000000 (RAM base, 48-bit).
  - All encoding cases: expected_state=null, expected_pc=null,
    expected_fault=null, status=active.

Legality cases per instruction:
  - ILLI: rd0 dest / store src rd0 / rb0 base / immu6=0 (for RA)
  - MALIGN: misaligned address (only for instructions with align > 0)
  - UNMAPPED: addr=0 (base rb3=0 or rb0=0)

Boundary cases per instruction:
  - Valid edge addresses (zero offset, near RAM end), expected_fault=null,
    expected_state present.
"""

import os, sys, yaml

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "tests", "vectors", "isa")

def _int(v):
    if isinstance(v, int): return v
    return int(str(v).strip(), 0)

# ── Load opcodes ──────────────────────────────────────────────────────
with open(os.path.join(REPO, "contracts", "opcodes.yaml")) as f:
    ALL = yaml.safe_load(f)

M1 = [r for r in ALL if not r.get("excluded_m1")]
BY_KEY = {(r["insn"], r["format"]): r for r in M1}

# ── Constants ─────────────────────────────────────────────────────────
RAM_BASE = 0x0000FFFF00000000  # rb3 preset value
RAM_BASE_HEX = "0x0000ffff00000000"
RAM_END = 0x0000FFFF00FFFFFF   # RAM end (16 MiB)

# Register assignments for F10 encoding vectors
RB_BASE = 3   # rb3
RD_DEST = 1   # rd1 (not rd0)
RA_DEST = 1   # ra1 (not ra0)
RD_OFF  = 2   # rd2 for multi rdhc
IMMU6   = 1   # multi count

# ── Memory instruction identities (M1, excluded_m1 != true) ─────────
MEM_INSNS = [
    # (insn, mnemonic, format, op, bank, role_ha, align, is_multi)
    # ── RD bank, single load/store (rrii) ──
    ("ld.ub-rd",  "ld.ub",  "rrii", 0x10, "rd", "dst", 0, False),
    ("ld.uw-rd",  "ld.uw",  "rrii", 0x11, "rd", "dst", 2, False),
    ("ld.ut-rd",  "ld.ut",  "rrii", 0x12, "rd", "dst", 4, False),
    ("ld.sb-rd",  "ld.sb",  "rrii", 0x13, "rd", "dst", 0, False),
    ("ld.sw-rd",  "ld.sw",  "rrii", 0x14, "rd", "dst", 2, False),
    ("ld.st-rd",  "ld.st",  "rrii", 0x15, "rd", "dst", 4, False),
    ("st.b-rd",   "st.b",   "rrii", 0x18, "rd", "src", 0, False),
    ("st.w-rd",   "st.w",   "rrii", 0x19, "rd", "src", 2, False),
    ("st.t-rd",   "st.t",   "rrii", 0x1A, "rd", "src", 4, False),
    ("ld.o-rd",   "ld.o",   "rrii", 0x20, "rd", "dst", 8, False),
    ("st.o-rd",   "st.o",   "rrii", 0x21, "rd", "src", 8, False),
    # ── RD bank, multi load/store (rrri) ──
    ("ldm.ub-rd", "ldm.ub", "rrri", 0x28, "rd", "dst", 0, True),
    ("ldm.uw-rd", "ldm.uw", "rrri", 0x29, "rd", "dst", 2, True),
    ("ldm.ut-rd", "ldm.ut", "rrri", 0x2A, "rd", "dst", 4, True),
    ("ldm.sb-rd", "ldm.sb", "rrri", 0x2B, "rd", "dst", 0, True),
    ("ldm.sw-rd", "ldm.sw", "rrri", 0x2C, "rd", "dst", 2, True),
    ("ldm.st-rd", "ldm.st", "rrri", 0x2D, "rd", "dst", 4, True),
    ("stm.b-rd",  "stm.b",  "rrri", 0x30, "rd", "src", 0, True),
    ("stm.w-rd",  "stm.w",  "rrri", 0x31, "rd", "src", 2, True),
    ("stm.t-rd",  "stm.t",  "rrri", 0x32, "rd", "src", 4, True),
    ("ldm.o-rd",  "ldm.o",  "rrri", 0x38, "rd", "dst", 8, True),
    ("stm.o-rd",  "stm.o",  "rrri", 0x39, "rd", "src", 8, True),
    # ── RB bank ──
    ("ld.o-rb",   "ld.o",   "rrii", 0x22, "rb", "dst", 8, False),
    ("st.o-rb",   "st.o",   "rrii", 0x23, "rb", "src", 8, False),
    ("ldm.o-rb",  "ldm.o",  "rrri", 0x3A, "rb", "dst", 8, True),
    ("stm.o-rb",  "stm.o",  "rrri", 0x3B, "rb", "src", 8, True),
    # ── RA bank ──
    ("ld.o-ra",   "ld.o",   "rrii", 0x24, "ra", "dst", 8, False),
    ("st.o-ra",   "st.o",   "rrii", 0x25, "ra", "src", 8, False),
    ("ldm.o-ra",  "ldm.o",  "rrri", 0x3C, "ra", "dst", 8, True),
    ("stm.o-ra",  "stm.o",  "rrri", 0x3D, "ra", "src", 8, True),
]

# ── Encoding word construction ───────────────────────────────────────
def build_word_rrii(op, ha, hb, imm12):
    return (op << 24) | (ha << 18) | (hb << 12) | (imm12 & 0xFFF)

def build_word_rrri(op, ha, hb, hc, immu6):
    return (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | (immu6 & 0x3F)

def hex32(w):
    return "0x%08X" % (w & 0xFFFFFFFF)

def hex64(v):
    return "0x%016X" % (v & 0xFFFFFFFFFFFFFFFF)

# ── Case template ────────────────────────────────────────────────────
def make_case(mnem, insn, fmt, cls, word, input_state, expected_state,
              expected_fault=None, status="active", deferred_reason=None,
              expected_pc=None, spec_cite="", notes=""):
    return {
        "mnemonic": mnem,
        "insn": insn,
        "format": fmt,
        "class": cls,
        "encoding": {"word": hex32(word)},
        "input_state": input_state,
        "expected_state": expected_state,
        "expected_pc": expected_pc,
        "expected_fault": expected_fault,
        "status": status,
        "deferred_reason": deferred_reason,
        "spec_cite": spec_cite,
        "notes": notes,
    }

# ── Word builder helper ──────────────────────────────────────────────
def _build_encoding_word(rec, imms12=0):
    """Build encoding word with F10 registers.

    For rrii: EA = rb3 + sign_ext(imms12). The imms12 field encodes the
    address offset directly — rd2 has no role in rrii effective address.
    For rrri: EA = rb3 + rd2, with hc=rd2 and immu6=1.
    """
    insn, mnem, fmt, op, bank, role, align, is_multi = rec
    if bank == "rd":
        ha = RD_DEST
    elif bank == "rb":
        ha = 1  # rb1
    else:
        ha = RA_DEST  # ra1
    hb = RB_BASE  # rb3
    if fmt == "rrii":
        return build_word_rrii(op, ha, hb, imms12)
    else:
        return build_word_rrri(op, ha, hb, RD_OFF, IMMU6)

# ── Load result computation ──────────────────────────────────────────
def _load_result(mnem, mem_val):
    """Compute sign/zero-extended load result from memory value."""
    if ".ub" in mnem or ".b" in mnem:
        return mem_val & 0xFF
    elif ".sb" in mnem:
        v = mem_val & 0xFF
        if v & 0x80: v |= ~0xFF
        return v & 0xFFFFFFFFFFFFFFFF
    elif ".uw" in mnem or ".w" in mnem:
        return mem_val & 0xFFFF
    elif ".sw" in mnem:
        v = mem_val & 0xFFFF
        if v & 0x8000: v |= ~0xFFFF
        return v & 0xFFFFFFFFFFFFFFFF
    elif ".ut" in mnem or ".t" in mnem:
        return mem_val & 0xFFFFFFFF
    elif ".st" in mnem:
        v = mem_val & 0xFFFFFFFF
        if v & 0x80000000: v |= ~0xFFFFFFFF
        return v & 0xFFFFFFFFFFFFFFFF
    else:  # .o
        return mem_val

def _store_truncate(mnem, val):
    """Truncate value for store to memory."""
    if ".b" in mnem:
        return val & 0xFF
    elif ".w" in mnem:
        return val & 0xFFFF
    elif ".t" in mnem:
        return val & 0xFFFFFFFF
    else:
        return val

# ── Per-identity case generators ─────────────────────────────────────

def gen_encoding(rec):
    """Encoding case: valid fields, no fault. F10 方案B."""
    insn, mnem, fmt, op, bank, role, align, is_multi = rec
    key = (insn, fmt)
    oprec = BY_KEY[key]
    sc = oprec.get("spec_cite", "")
    word = _build_encoding_word(rec)

    # Verify mask/value
    mask = _int(oprec["mask"])
    value = _int(oprec["value"])
    assert (word & mask) == value, \
        f"Encoding mismatch for {insn}: word={hex32(word)}, mask={hex32(mask)}, value={hex32(value)}"

    inp = {"rb": {f"rb{RB_BASE}": RAM_BASE_HEX}}
    notes_str = (f"encoding: word matches opcodes.yaml mask/value, "
                 f"base=rb{RB_BASE}, {'immu6=1' if is_multi else 'imms12=0'}")
    return make_case(mnem, insn, fmt, "encoding", word, inp, None,
                     None, "active", None, None, sc, notes_str)


def gen_legality_illi(rec):
    """Legality ILLI case: rd0 dest / store src rd0 / rb0 base / immu6=0."""
    insn, mnem, fmt, op, bank, role, align, is_multi = rec
    key = (insn, fmt)
    oprec = BY_KEY[key]
    sc = oprec.get("spec_cite", "")

    if fmt == "rrii":
        if bank == "rd":
            ha = 0  # rd0
            hb = RB_BASE
            word = build_word_rrii(op, ha, hb, 0)
            reason = "rd0 as dest/src → ILLI (rd_dest_rd0 / store_src_rd0)"
        elif bank == "rb":
            ha = 0  # rb0
            hb = RB_BASE
            word = build_word_rrii(op, ha, hb, 0)
            reason = "rb0 as dest/src → ILLI (rb_dest_rb0 / rb_base_rb0_store)"
        else:  # ra
            # RA rrii has no rd0/rb0 destination constraint (ra无此约束).
            # rb0=PC≠0 (ADR-0004 D2.1/D6.5), so base=rb0 does NOT give addr=0.
            # ILLI coverage for RA is via rrri immu6=0 (below).
            # UNMAPPED coverage is via gen_legality_unmapped (rb3=0).
            return None
    else:  # rrri
        if bank == "rd":
            ha = 0  # rd0
            hb = RB_BASE
            hc = RD_OFF
            word = build_word_rrri(op, ha, hb, hc, IMMU6)
            reason = "rd0 as dest/src → ILLI (rd_dest_rd0 / store_src_rd0)"
        elif bank == "rb":
            ha = 0  # rb0
            hb = RB_BASE
            hc = RD_OFF
            word = build_word_rrri(op, ha, hb, hc, IMMU6)
            reason = "rb0 as dest/src → ILLI (rb_dest_rb0)"
        else:  # ra
            ha = RA_DEST
            hb = RB_BASE
            hc = RD_OFF
            word = build_word_rrri(op, ha, hb, hc, 0)  # immu6=0
            reason = "immu6=0 → ILLI (ra_multi_immu6_zero)"
            return make_case(mnem, insn, fmt, "legality", word, {}, None,
                             "ILLI", "active", None, None, sc, reason)

    return make_case(mnem, insn, fmt, "legality", word, {}, None,
                     "ILLI", "active", None, None, sc, reason)


def gen_legality_malign(rec):
    """Legality MALIGN case: misaligned address. Only for align > 0."""
    insn, mnem, fmt, op, bank, role, align, is_multi = rec
    if align == 0:
        return None  # No alignment requirement

    key = (insn, fmt)
    oprec = BY_KEY[key]
    sc = oprec.get("spec_cite", "")

    # Misaligned offset: align - 1
    misalign_off = align - 1

    # EA = RAM_BASE + misalign_off (misaligned within RAM)
    if fmt == "rrii":
        # rrii: encode misalignment into imms12; rd2 has no role in rrii EA
        word = _build_encoding_word(rec, misalign_off)
        inp = {"rb": {f"rb{RB_BASE}": hex64(RAM_BASE)}}
        notes = (f"legality MALIGN: EA={hex64(RAM_BASE + misalign_off)} "
                 f"(imms12={misalign_off}), align={align}B → MALIGN (0x8C), "
                 f"contract-isa §4.1.1, legality_rules data_malign")
    else:
        # rrri: EA = rb3 + rd2; rd2 preset to misalignment offset
        word = _build_encoding_word(rec)
        inp = {
            "rb": {f"rb{RB_BASE}": hex64(RAM_BASE)},
            "rd": {f"rd{RD_OFF}": hex64(misalign_off)},
        }
        notes = (f"legality MALIGN: EA={hex64(RAM_BASE + misalign_off)} "
                 f"(rd{RD_OFF} offset={misalign_off}), align={align}B → MALIGN (0x8C), "
                 f"contract-isa §4.1.1, legality_rules data_malign")
    return make_case(mnem, insn, fmt, "legality", word, inp, None,
                     "MALIGN", "active", None, None, sc, notes)


def gen_legality_unmapped(rec):
    """Legality UNMAPPED case: addr=0 (rb3 not preset)."""
    insn, mnem, fmt, op, bank, role, align, is_multi = rec
    key = (insn, fmt)
    oprec = BY_KEY[key]
    sc = oprec.get("spec_cite", "")

    word = _build_encoding_word(rec)

    # rb3 not preset → default 0 → EA=0 → unmapped
    inp = {"rb": {f"rb{RB_BASE}": "0x0000000000000000"}}
    notes = (f"legality UNMAPPED: base=rb3=0 → addr=0 → unmapped (0x87), "
             f"ADR-0004 D5.6")
    return make_case(mnem, insn, fmt, "legality", word, inp, None,
                     "UNMAPPED", "active", None, None, sc, notes)


def gen_semantic(rec, addr_offset=0x100, mem_val=0x42):
    """Semantic case: valid load/store with known values.

    For rrii: EA = rb3 + sign_ext(imms12). addr_offset is encoded into imms12.
    For rrri: EA = rb3 + rd2. addr_offset is preset in rd2.
    """
    insn, mnem, fmt, op, bank, role, align, is_multi = rec
    key = (insn, fmt)
    oprec = BY_KEY[key]
    sc = oprec.get("spec_cite", "")

    ea = RAM_BASE + addr_offset

    if bank == "rd":
        ha_name = f"rd{RD_DEST}"
    elif bank == "rb":
        ha_name = "rb1"
    else:
        ha_name = f"ra{RA_DEST}"

    if fmt == "rrii":
        # rrii: encode addr_offset into imms12 of the word; rd2 has no role
        word = _build_encoding_word(rec, addr_offset)
        if role == "dst":  # load
            inp = {
                "rb": {f"rb{RB_BASE}": hex64(RAM_BASE)},
                "memory": [{"address": hex64(ea), "value": hex64(mem_val)}]
            }
            if bank == "rd":
                inp["rd"] = {ha_name: hex64(0)}
            elif bank == "rb":
                inp["rb"][ha_name] = hex64(0)
            else:
                inp["ra"] = {ha_name: hex64(0)}

            result = _load_result(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {}, "memory": []}
            if bank == "rd":
                out["rd"] = {ha_name: hex64(result)}
            elif bank == "rb":
                out["rb"] = {ha_name: hex64(result)}
            else:
                out["ra"] = {ha_name: hex64(result)}

            notes = (f"{mnem}: {ha_name} <- mem[{hex64(ea)}] = {hex64(mem_val)}, "
                     f"result={hex64(result)}, imms12=0x{addr_offset:x}")
        else:  # store
            inp = {
                "rb": {f"rb{RB_BASE}": hex64(RAM_BASE)},
                "memory": []
            }
            if bank == "rd":
                inp["rd"] = {ha_name: hex64(mem_val)}
            elif bank == "rb":
                inp["rb"][ha_name] = hex64(mem_val)
            else:
                inp["ra"] = {ha_name: hex64(mem_val)}

            stored = _store_truncate(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {},
                   "memory": [{"address": hex64(ea), "value": hex64(stored)}]}
            notes = (f"{mnem}: mem[{hex64(ea)}] <- {ha_name}={hex64(mem_val)}, "
                     f"stored={hex64(stored)}, imms12=0x{addr_offset:x}")

    else:  # rrri — multi
        # rrri: EA = rb3 + rd2; addr_offset is preset in rd2
        word = _build_encoding_word(rec)
        inp = {
            "rd": {f"rd{RD_OFF}": hex64(addr_offset)},
            "rb": {f"rb{RB_BASE}": hex64(RAM_BASE)},
            "memory": [{"address": hex64(ea), "value": hex64(mem_val)}]
        }
        if bank == "rd":
            inp["rd"][ha_name] = hex64(0) if role == "dst" else hex64(mem_val)
        elif bank == "rb":
            inp["rb"][ha_name] = hex64(0) if role == "dst" else hex64(mem_val)
        else:
            inp["ra"] = {ha_name: hex64(0) if role == "dst" else hex64(mem_val)}

        if role == "dst":  # ldm
            result = _load_result(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {}, "memory": []}
            if bank == "rd":
                out["rd"] = {ha_name: hex64(result)}
            elif bank == "rb":
                out["rb"] = {ha_name: hex64(result)}
            else:
                out["ra"] = {ha_name: hex64(result)}
            notes = (f"{mnem}: {ha_name} <- mem[{hex64(ea)}] = {hex64(mem_val)}, "
                     f"result={hex64(result)}, rd{RD_OFF}(offset)={hex64(addr_offset)}, "
                     f"immu6={IMMU6}")
        else:  # stm
            stored = _store_truncate(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {},
                   "memory": [{"address": hex64(ea), "value": hex64(stored)}]}
            notes = (f"{mnem}: mem[{hex64(ea)}] <- {ha_name}={hex64(mem_val)}, "
                     f"stored={hex64(stored)}, rd{RD_OFF}(offset)={hex64(addr_offset)}, "
                     f"immu6={IMMU6}")

    return make_case(mnem, insn, fmt, "semantic", word, inp, out,
                     None, "active", None, None, sc, notes)


def gen_boundary(rec, addr_offset=0x0, mem_val=0xDEADBEEF):
    """Boundary case: zero offset, valid address, expected_fault=null.
    Uses addr_offset=0 by default (EA = RAM_BASE + 0 = RAM_BASE).

    For rrii: EA = rb3 + sign_ext(imms12). addr_offset is encoded into imms12.
    For rrri: EA = rb3 + rd2. addr_offset is preset in rd2.
    """
    insn, mnem, fmt, op, bank, role, align, is_multi = rec
    key = (insn, fmt)
    oprec = BY_KEY[key]
    sc = oprec.get("spec_cite", "")

    # Ensure alignment for the offset
    if align > 0:
        addr_offset = (addr_offset // align) * align

    ea = RAM_BASE + addr_offset

    if bank == "rd":
        ha_name = f"rd{RD_DEST}"
    elif bank == "rb":
        ha_name = "rb1"
    else:
        ha_name = f"ra{RA_DEST}"

    if fmt == "rrii":
        # rrii: encode addr_offset into imms12; rd2 has no role
        word = _build_encoding_word(rec, addr_offset)
        if role == "dst":  # load
            inp = {
                "rb": {f"rb{RB_BASE}": hex64(RAM_BASE)},
                "memory": [{"address": hex64(ea), "value": hex64(mem_val)}]
            }
            if bank == "rd":
                inp["rd"] = {ha_name: hex64(0)}
            elif bank == "rb":
                inp["rb"][ha_name] = hex64(0)
            else:
                inp["ra"] = {ha_name: hex64(0)}

            result = _load_result(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {}, "memory": []}
            if bank == "rd":
                out["rd"] = {ha_name: hex64(result)}
            elif bank == "rb":
                out["rb"] = {ha_name: hex64(result)}
            else:
                out["ra"] = {ha_name: hex64(result)}

            notes = (f"boundary: {ha_name} <- mem[{hex64(ea)}] = {hex64(mem_val)}, "
                     f"result={hex64(result)}, imms12=0x{addr_offset:x}")
        else:  # store
            inp = {
                "rb": {f"rb{RB_BASE}": hex64(RAM_BASE)},
                "memory": []
            }
            if bank == "rd":
                inp["rd"] = {ha_name: hex64(mem_val)}
            elif bank == "rb":
                inp["rb"][ha_name] = hex64(mem_val)
            else:
                inp["ra"] = {ha_name: hex64(mem_val)}

            stored = _store_truncate(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {},
                   "memory": [{"address": hex64(ea), "value": hex64(stored)}]}
            notes = (f"boundary: mem[{hex64(ea)}] <- {ha_name}={hex64(mem_val)}, "
                     f"stored={hex64(stored)}, imms12=0x{addr_offset:x}")

    else:  # rrri — multi
        # rrri: EA = rb3 + rd2; addr_offset is preset in rd2
        word = _build_encoding_word(rec)
        inp = {
            "rd": {f"rd{RD_OFF}": hex64(addr_offset)},
            "rb": {f"rb{RB_BASE}": hex64(RAM_BASE)},
            "memory": [{"address": hex64(ea), "value": hex64(mem_val)}]
        }
        if bank == "rd":
            inp["rd"][ha_name] = hex64(0) if role == "dst" else hex64(mem_val)
        elif bank == "rb":
            inp["rb"][ha_name] = hex64(0) if role == "dst" else hex64(mem_val)
        else:
            inp["ra"] = {ha_name: hex64(0) if role == "dst" else hex64(mem_val)}

        if role == "dst":  # ldm
            result = _load_result(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {}, "memory": []}
            if bank == "rd":
                out["rd"] = {ha_name: hex64(result)}
            elif bank == "rb":
                out["rb"] = {ha_name: hex64(result)}
            else:
                out["ra"] = {ha_name: hex64(result)}
            notes = (f"boundary: {ha_name} <- mem[{hex64(ea)}] = {hex64(mem_val)}, "
                     f"result={hex64(result)}, zero offset, immu6={IMMU6}")
        else:  # stm
            stored = _store_truncate(mnem, mem_val)
            out = {"rd": {}, "rb": {}, "ra": {},
                   "memory": [{"address": hex64(ea), "value": hex64(stored)}]}
            notes = (f"boundary: mem[{hex64(ea)}] <- {ha_name}={hex64(mem_val)}, "
                     f"stored={hex64(stored)}, zero offset, immu6={IMMU6}")

    return make_case(mnem, insn, fmt, "boundary", word, inp, out,
                     None, "active", None, None, sc, notes)


# ── Main ─────────────────────────────────────────────────────────────
def main():
    files = {
        "mem-rd.yaml": [],
        "mem-rb.yaml": [],
        "mem-ra.yaml": [],
    }

    for rec in MEM_INSNS:
        insn, mnem, fmt, op, bank, role, align, is_multi = rec

        if bank == "rd":
            fname = "mem-rd.yaml"
        elif bank == "rb":
            fname = "mem-rb.yaml"
        else:
            fname = "mem-ra.yaml"

        # 1. Encoding case
        files[fname].append(gen_encoding(rec))

        # 2. Legality: ILLI (rd0/rb0/immu6=0)
        illi = gen_legality_illi(rec)
        if illi is not None:
            files[fname].append(illi)

        # 3. Legality: MALIGN (if alignment required)
        malign = gen_legality_malign(rec)
        if malign is not None:
            files[fname].append(malign)

        # 4. Legality: UNMAPPED (addr=0)
        files[fname].append(gen_legality_unmapped(rec))

        # 5. Semantic case
        files[fname].append(gen_semantic(rec))

        # 6. Boundary case (zero offset, valid address)
        files[fname].append(gen_boundary(rec))

    # Write files
    for fname, cases in files.items():
        path = os.path.join(OUT, fname)
        with open(path, "w") as f:
            f.write("# Generated by TESTCASES-004t generator — DO NOT EDIT\n")
            f.write("# Source: contracts/opcodes.yaml + contract-isa.md + adr-0004\n")
            f.write("# F10 design: base=rb3 (unused), dest=rd1/ra1, immu6=1 for multi\n")
            f.write("# Each case has spec_cite and notes for traceability.\n\n")
            yaml.dump(cases, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"  {fname}: {len(cases)} cases")

    print(f"\nTotal: {sum(len(c) for c in files.values())} cases across 3 files")


if __name__ == "__main__":
    main()
