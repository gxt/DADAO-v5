#!/usr/bin/env python3
"""Generate the6 reg-*.yaml test vector files for TESTCASES-003t.

Reads contracts/opcodes.yaml and produces:
  reg-arith.yaml, reg-logic.yaml, reg-shift-extend.yaml,
  reg-compare.yaml, reg-cond-assign.yaml, reg-imm-block.yaml

All encoding words, expected values, and spec_cite are derived from
contracts/opcodes.yaml, .tao/knowledge/contract-isa.md, and
.tao/knowledge/adr-0004-test-machine.md.  No LLVM/QEMU reverse-engineering.
"""

import os, sys, yaml, copy

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "tests", "vectors", "isa")

def _int(v):
    if isinstance(v, int): return v
    return int(str(v).strip(), 0)

# ── Load opcodes ──────────────────────────────────────────────────────
with open(os.path.join(REPO, "contracts", "opcodes.yaml")) as f:
    ALL = yaml.safe_load(f)

M1 = [r for r in ALL if not r.get("excluded_m1")]

# ── Map (insn, format) → file ─────────────────────────────────────────
FILE_MAP = {
    "reg-arith.yaml": [],
    "reg-logic.yaml": [],
    "reg-shift-extend.yaml": [],
    "reg-compare.yaml": [],
    "reg-cond-assign.yaml": [],
    "reg-imm-block.yaml": [],
}

# Build a dict for quick lookup: (insn, format) → rec
BY_KEY = {(r["insn"], r["format"]): r for r in M1}

# ── Assign identities to files ────────────────────────────────────────
LOGIC = {"and", "or", "xor", "xnor"}
SHIFT = {"shl", "shr", "ext"}
COMPARE = {"cmp"}
COND = {"cs"}
IMM_BLOCK_RWII = {"set.zw", "set.ow", "or.w", "andn.w"}  # rwii format
BLOCK = {"rd2rd", "rb2rb", "rb2rd", "rd2rb", "ra2rd", "rd2ra"}
ARITH_MISC_OCTA = {"add.so-rb", "sub.so-rb"}
ARITH_DIVREM = {"div", "rem"}

def _base_mnem(insn):
    """Extract base mnemonic from insn string.
    'add.uo-rd' → 'add', 'and.o' → 'and', 'shl.uo' → 'shl',
    'set.zw-rd' → 'set.zw', 'cs.n-rd' → 'cs', 'rd2rd' → 'rd2rd',
    'cmp.uo-rb' → 'cmp'
    """
    # First remove bank suffix (-rd/-rb/-rf etc.)
    if '-' in insn:
        insn = insn.split('-')[0]
    # Now strip the data-width suffix (.uo/.so/.o/.b/.w/.t etc.)
    # but NOT for names like 'set.zw', 'rd2rd', 'cs.n'
    dot_parts = insn.split('.')
    if len(dot_parts) == 2:
        suffix = dot_parts[1]
        if suffix in ('o', 'b', 'w', 't', 'uo', 'so', 'ub', 'sb', 'uw', 'sw', 'ut', 'st'):
            return dot_parts[0]
    return insn

def _classify(insn, fmt):
    """Return which file this (insn, format) belongs to.
    Returns None if it doesn't belong to any reg-* file."""
    # Strip bank suffix for matching
    base = insn.split('-')[0] if '-' in insn else insn

    # Direct insn matches for block moves and immediate block instructions
    if base in BLOCK: return "reg-imm-block.yaml"
    if base in IMM_BLOCK_RWII and fmt == "rwii": return "reg-imm-block.yaml"

    # For MISC subtable entries, base has suffix like "and.o", "add.ub"
    # Strip the .suffix to get the operation
    parts = base.split('.')
    op = parts[0] if len(parts) > 1 else base

    # Check if this is a MISC-octa/tetra/wyde/byte instruction
    # These are opcodes 0x40-0x43 with orrr/orri format
    is_misc = fmt in ("orrr", "orri")

    # Check if this is a QFC main table entry that belongs to reg-* files
    # rrrr: add.uo/so-rd, sub.uo/so-rd, mul.uo/so-rd, cs.n/z/p/eq/ne-rd
    # riii: add.si-rd, add.si-rb, rela.si-rb
    # rrii: cmp.ui/si-rd
    # rwii: or.w/andn.w/set.zw/set.ow -rd/-rb
    is_qfc_reg = False
    if fmt == "rrrr" and op in ("add", "sub", "mul", "cs"):
        is_qfc_reg = True
    if fmt == "riii" and op in ("add", "rela"):
        is_qfc_reg = True
    if fmt == "rrii" and op == "cmp":
        is_qfc_reg = True
    if fmt == "rwii" and base in IMM_BLOCK_RWII:
        is_qfc_reg = True

    if not is_misc and not is_qfc_reg:
        return None  # This is a mem/ctrl/misc entry

    # Now classify within reg-* files
    if base in BLOCK: return "reg-imm-block.yaml"
    if base in IMM_BLOCK_RWII and fmt == "rwii": return "reg-imm-block.yaml"

    if op == "cs": return "reg-cond-assign.yaml"
    if op == "cmp": return "reg-compare.yaml"
    if op in LOGIC: return "reg-logic.yaml"
    if op in SHIFT: return "reg-shift-extend.yaml"

    # Everything else is arith
    return "reg-arith.yaml"

for key, rec in BY_KEY.items():
    insn, fmt = key
    fname = _classify(insn, fmt)
    if fname is not None:
        FILE_MAP[fname].append(rec)

# ── Encoding word construction helpers ─────────────────────────────────
def _build_word_rrrr(rec, rdha, rdhb, rdhc, rdhd):
    op = _int(rec["op"])
    return (op << 24) | (rdha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd

def _build_word_orrr(rec, rdhb, rdhc, rdhd):
    op = _int(rec["op"])
    ha = _int(rec["ha"])
    return (op << 24) | (ha << 18) | (rdhb << 12) | (rdhc << 6) | rdhd

def _build_word_orri(rec, rdhb, rdhc, immu6):
    op = _int(rec["op"])
    ha = _int(rec["ha"])
    return (op << 24) | (ha << 18) | (rdhb << 12) | (rdhc << 6) | immu6

def _build_word_rrii(rec, rdha, rdhb, imm12):
    op = _int(rec["op"])
    return (op << 24) | (rdha << 18) | (rdhb << 12) | (imm12 & 0xFFF)

def _build_word_riii(rec, rdha, imm18):
    op = _int(rec["op"])
    return (op << 24) | (rdha << 18) | (imm18 & 0x3FFFF)

def _build_word_rwii(rec, rdha, wpN, immu16):
    op = _int(rec["op"])
    hi4 = (immu16 >> 12) & 0xF
    mid6 = (immu16 >> 6) & 0x3F
    lo6 = immu16 & 0x3F
    return (op << 24) | (rdha << 18) | (wpN << 16) | (hi4 << 12) | (mid6 << 6) | lo6

# ── Semantic expected-value helpers ────────────────────────────────────
def _sext(val, bits):
    """Sign-extend a value from `bits` width to Python int."""
    mask = (1 << bits) - 1
    v = val & mask
    if v & (1 << (bits - 1)):
        v -= (1 << bits)
    return v

def _uext(val, bits):
    """Zero-extend (truncate to bits)."""
    return val & ((1 << bits) - 1)

def _hex64(v):
    return "0x%016X" % (v & 0xFFFFFFFFFFFFFFFF)

def _arith_result(insn, a, b, bits=64):
    """Compute result for add/sub/orrr format (3-register, rdhb = dst).
    Per contract-isa §3.1.2/§3.1.5: source operands truncated to `bits` width,
    result truncated to `bits`, then sign-extended (.s*) or zero-extended (.u*) to 64 bits."""
    mask = (1 << bits) - 1
    a, b = a & mask, b & mask
    # Determine sign extension: .s* suffix → signed, .u* → unsigned
    is_signed = (".so" in insn or ".sb" in insn or ".sw" in insn or ".st" in insn)
    if "add" in insn:
        result = (a + b) & mask
    elif "sub" in insn:
        result = (a - b) & mask  # truncate to size first, then extend
    elif "mul" in insn:
        result = (a * b) & mask
    elif "div" in insn:
        if is_signed:
            sa, sb = _sext(a, bits), _sext(b, bits)
            if sb == 0: return None  # div by zero
            result = int(sa / sb) & mask  # truncate toward zero, keep size bits
        else:
            if b == 0: return None
            result = (a // b) & mask
    elif "rem" in insn:
        if is_signed:
            sa, sb = _sext(a, bits), _sext(b, bits)
            if sb == 0: return None
            # Truncate-toward-zero remainder (C99): r = a - trunc(a/b) * b
            # Python's % uses floor-mod; must not use it for signed rem
            result = (sa - int(sa / sb) * sb) & mask
        else:
            if b == 0: return None
            result = (a % b) & mask
    else:
        return 0
    # Extend to 64 bits: signed → sign-extend, unsigned → zero-extend
    if is_signed:
        return _sext(result, bits) & 0xFFFFFFFFFFFFFFFF
    else:
        return result & mask  # zero-extended (high bits already 0)

def _logic_result(insn, rdhc_val, rdhd_val, rdhb_old, bits):
    """Compute logic result. rdhb = dst, bits = width."""
    mask = (1 << bits) - 1
    src1, src2 = rdhc_val & mask, rdhd_val & mask
    bm = _base_mnem(insn)
    if bm == "and":  res = src1 & src2
    elif bm == "or": res = src1 | src2
    elif bm == "xor": res = src1 ^ src2
    elif bm == "xnor": res = ~(src1 ^ src2) & mask
    else: res = 0
    # High bits unchanged
    high_mask = ~mask & 0xFFFFFFFFFFFFFFFF
    return (rdhb_old & high_mask) | (res & mask)

def _cmp_result(a, b, bits, signed=False):
    """Compare result: -1/0/1 as64-bit."""
    mask = (1 << bits) - 1
    a, b = a & mask, b & mask
    if signed:
        a, b = _sext(a, bits), _sext(b, bits)
    if a < b: return -1 & 0xFFFFFFFFFFFFFFFF
    elif a == b: return 0
    else: return 1

def _shl_result(src_val, shamt, N, rdhb_old):
    """Left shift: rdhb[N:0] = (src[N:0] << shamt), high unchanged."""
    mask_N = (1 << (N + 1)) - 1
    result = ((src_val & mask_N) << shamt) & mask_N
    high_mask = ~mask_N & 0xFFFFFFFFFFFFFFFF
    return (rdhb_old & high_mask) | result

def _shr_result(src_val, shamt, N, rdhb_old, signed=False):
    """Right shift."""
    mask_N = (1 << (N + 1)) - 1
    src_N = src_val & mask_N
    if signed and (src_N & (1 << N)):
        # Arithmetic: replicate sign bit
        result = (src_N >> shamt) | (~((1 << (N + 1 - shamt)) - 1) & mask_N)
    else:
        result = src_N >> shamt
    result = result & mask_N
    high_mask = ~mask_N & 0xFFFFFFFFFFFFFFFF
    return (rdhb_old & high_mask) | result

def _ext_result(src_val, ext_start, N, rdhb_old, signed=False):
    """Extend: rdhb[ext_start:0] = src[ext_start:0],
    rdhb[N:ext_start+1] = sign/zero_extend(src[ext_start])."""
    mask_start = (1 << (ext_start + 1)) - 1
    mask_N = (1 << (N + 1)) - 1
    low = src_val & mask_start
    sign_bit = (src_val >> ext_start) & 1
    if signed and sign_bit:
        high_fill = (~mask_start & mask_N)
    else:
        high_fill = 0
    result = (low | high_fill) & mask_N
    high_mask = ~mask_N & 0xFFFFFFFFFFFFFFFF
    return (rdhb_old & high_mask) | result

# ── Case generation ───────────────────────────────────────────────────
def _case(mnem, insn, fmt, cls, enc_word, input_state, expected_state,
          expected_fault=None, status="active", deferred_reason=None,
          expected_pc=None, spec_cite="", notes=""):
    c = {
        "mnemonic": mnem,
        "insn": insn,
        "format": fmt,
        "class": cls,
        "encoding": {"word": "0x%08X" % enc_word},
        "input_state": input_state,
        "expected_state": expected_state,
        "expected_pc": expected_pc,
        "expected_fault": expected_fault,
        "status": status,
        "deferred_reason": deferred_reason,
        "spec_cite": spec_cite,
        "notes": notes,
    }
    return c

# ── Determine bit-width from mnemonic suffix ──────────────────────────
def _get_bits(mnem):
    """Return bit-width from mnemonic suffix."""
    if ".ub" in mnem or ".sb" in mnem or ".b" in mnem: return 8
    if ".uw" in mnem or ".sw" in mnem or ".w" in mnem: return 16
    if ".ut" in mnem or ".st" in mnem or ".t" in mnem: return 32
    return 64  # .uo / .so / .o / default

# ── Generate per-identity cases ───────────────────────────────────────
def gen_encoding(rec, word, input_state=None):
    """Generate encoding case: fields legal, no fault."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    inp = input_state if input_state is not None else {}
    return _case(mnem, insn, fmt, "encoding",
                 word, inp, None, None, "active", None, None, sc,
                 "encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI")

def gen_semantic_orrr_arith(rec, a_val, b_val, rdhb_old=0):
    """Generate semantic case for orrr arith (add/sub/div/rem) or orrr logic."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    bits = _get_bits(mnem)

    # Build word: rdhb=1, rdhc=2(src), rdhd=3(src)
    word = _build_word_orrr(rec, 1, 2, 3)

    bm = _base_mnem(insn)
    if bm in LOGIC:
        expected = _logic_result(insn, a_val, b_val, rdhb_old, bits)

        inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(a_val), "rd3": _hex64(b_val)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
        notes = "logic %s: rd2=%s, rd3=%s, bits=%d" % (bm, hex(a_val), hex(b_val), bits)
    else:
        result = _arith_result(insn, a_val, b_val, bits)
        if result is None:
            return None  # skip div-by-zero
        expected = result
        inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(a_val), "rd3": _hex64(b_val)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
        notes = "%s: rd2=%s, rd3=%s, bits=%d" % (mnem, hex(a_val), hex(b_val), bits)

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_semantic_orrr_arith_rb(rec, a_val, b_val, rbhb_old=0):
    """Semantic for add.so-rb / sub.so-rb (orrr, rb dst)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    word = _build_word_orrr(rec, 1, 0, 3)
    # rbhb=1(rb1), rbhc=0(rb0=src but rb0=PC, use rb2), rdhd=3(rd3)
    # Actually: rbhb=1, rbhc=2, rdhd=3
    word = _build_word_orrr(rec, 1, 2, 3)

    result = _arith_result(insn, a_val, b_val, 64)
    if result is None: return None

    inp = {"rd": {"rd3": _hex64(b_val)}, "rb": {"rb1": _hex64(rbhb_old), "rb2": _hex64(a_val)}}
    out = {"rd": {}, "rb": {"rb1": _hex64(result)}, "ra": {}, "memory": []}
    notes = "%s: rb2=%s, rd3=%s, full64-bit" % (mnem, hex(a_val), hex(b_val))

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_boundary_orrr_arith(rec, a_val, b_val, rdhb_old=0):
    """Boundary case for orrr arith/logic."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    bits = _get_bits(mnem)

    word = _build_word_orrr(rec, 1, 2, 3)
    bm = _base_mnem(insn)

    if bm in LOGIC:
        expected = _logic_result(insn, a_val, b_val, rdhb_old, bits)
        inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(a_val), "rd3": _hex64(b_val)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
        notes = "boundary logic: rd2=%s, rd3=%s, bits=%d" % (hex(a_val), hex(b_val), bits)
    else:
        result = _arith_result(insn, a_val, b_val, bits)
        if result is None: return None
        expected = result
        inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(a_val), "rd3": _hex64(b_val)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
        notes = "boundary %s: rd2=%s, rd3=%s" % (mnem, hex(a_val), hex(b_val))

    return _case(mnem, insn, fmt, "boundary", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_boundary_orrr_arith_rb(rec, a_val, b_val, rbhb_old=0):
    """Boundary for add.so-rb / sub.so-rb."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    word = _build_word_orrr(rec, 1, 2, 3)
    result = _arith_result(insn, a_val, b_val, 64)
    if result is None: return None

    inp = {"rd": {"rd3": _hex64(b_val)}, "rb": {"rb1": _hex64(rbhb_old), "rb2": _hex64(a_val)}}
    out = {"rd": {}, "rb": {"rb1": _hex64(result)}, "ra": {}, "memory": []}
    notes = "boundary %s: rb2=%s, rd3=%s" % (mnem, hex(a_val), hex(b_val))

    return _case(mnem, insn, fmt, "boundary", word, inp, out, None,
                 "active", None, None, sc, notes)

# ── Shift / Extend (orrr and orri) ────────────────────────────────────
def _get_N(insn, mnem):
    """Get N for shift/extend from mnemonic suffix."""
    if ".ub" in mnem or ".sb" in mnem or ".b" in mnem: return 7
    if ".uw" in mnem or ".sw" in mnem or ".w" in mnem: return 15
    if ".ut" in mnem or ".st" in mnem or ".t" in mnem: return 31
    return 63

def gen_shift_orrr_semantic(rec, src_val, shamt, rdhb_old=0):
    """Semantic for shl/shr/extend orrr: shamt from rd3 (register)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    N = _get_N(insn, mnem)

    # orrr: rdhb=1(dst), rdhc=2(src), rdhd=3(shamt register)
    word = _build_word_orrr(rec, 1, 2, 3)

    bm = _base_mnem(insn)
    if bm == "shl":
        expected = _shl_result(src_val, shamt, N, rdhb_old)
    elif bm == "shr":
        signed = ".s" in mnem
        expected = _shr_result(src_val, shamt, N, rdhb_old, signed)
    elif bm == "ext":
        signed = ".s" in mnem
        expected = _ext_result(src_val, shamt, N, rdhb_old, signed)
    else:
        return None

    inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(src_val), "rd3": _hex64(shamt)}}
    out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
    notes = "%s: rd2(src)=%s, rd3(shamt)=%d, N=%d" % (mnem, hex(src_val), shamt, N)

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_shift_orrr_boundary(rec, src_val, shamt, rdhb_old=0):
    """Boundary for shl/shr/extend orrr (shamt=N)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    N = _get_N(insn, mnem)

    word = _build_word_orrr(rec, 1, 2, 3)

    bm = _base_mnem(insn)
    if bm == "shl":
        expected = _shl_result(src_val, shamt, N, rdhb_old)
    elif bm == "shr":
        signed = ".s" in mnem
        expected = _shr_result(src_val, shamt, N, rdhb_old, signed)
    elif bm == "ext":
        signed = ".s" in mnem
        expected = _ext_result(src_val, shamt, N, rdhb_old, signed)
    else:
        return None

    inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(src_val), "rd3": _hex64(shamt)}}
    out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
    notes = "boundary %s: rd2(src)=%s, rd3(shamt)=%d=N, N=%d" % (mnem, hex(src_val), shamt, N)

    return _case(mnem, insn, fmt, "boundary", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_shift_orri_semantic(rec, src_val, immu6, rdhb_old=0):
    """Semantic for shl/shr/extend orri: immu6 in hd."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    N = _get_N(insn, mnem)

    word = _build_word_orri(rec, 1, 2, immu6)

    bm = _base_mnem(insn)
    if bm == "shl":
        expected = _shl_result(src_val, immu6, N, rdhb_old)
    elif bm == "shr":
        signed = ".s" in mnem
        expected = _shr_result(src_val, immu6, N, rdhb_old, signed)
    elif bm == "ext":
        signed = ".s" in mnem
        expected = _ext_result(src_val, immu6, N, rdhb_old, signed)
    else:
        return None

    inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(src_val)}}
    out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
    notes = "%s orri: rd2(src)=%s, immu6=%d, N=%d" % (mnem, hex(src_val), immu6, N)

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_shift_orri_boundary(rec, src_val, immu6, rdhb_old=0):
    """Boundary for shl/shr/extend orri (immu6=N)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    N = _get_N(insn, mnem)

    word = _build_word_orri(rec, 1, 2, immu6)

    bm = _base_mnem(insn)
    if bm == "shl":
        expected = _shl_result(src_val, immu6, N, rdhb_old)
    elif bm == "shr":
        signed = ".s" in mnem
        expected = _shr_result(src_val, immu6, N, rdhb_old, signed)
    elif bm == "ext":
        signed = ".s" in mnem
        expected = _ext_result(src_val, immu6, N, rdhb_old, signed)
    else:
        return None

    inp = {"rd": {"rd1": _hex64(rdhb_old), "rd2": _hex64(src_val)}}
    out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
    notes = "boundary %s orri: rd2(src)=%s, immu6=%d=N, N=%d" % (mnem, hex(src_val), immu6, N)

    return _case(mnem, insn, fmt, "boundary", word, inp, out, None,
                 "active", None, None, sc, notes)

# ── Compare ────────────────────────────────────────────────────────────
def gen_compare_semantic(rec, a_val, b_val, rdha_old=0):
    """Semantic for cmp (orrr or rrii)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")
    bits = _get_bits(mnem)
    signed = ".s" in mnem

    if fmt == "orrr":
        word = _build_word_orrr(rec, 1, 2, 3)
        expected = _cmp_result(a_val, b_val, bits, signed)
        # cmp.uo-rb: rbhc(rb2)=src, rbhd(rb3)=src; others: rdhc(rd2), rdhd(rd3)
        if "-rb" in insn:
            inp = {"rb": {"rb2": _hex64(a_val), "rb3": _hex64(b_val)}}
        else:
            inp = {"rd": {"rd2": _hex64(a_val), "rd3": _hex64(b_val)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
        notes = "%s: %s=%s, %s=%s, bits=%d, signed=%s" % (
            mnem, "rb2" if "-rb" in insn else "rd2", hex(a_val),
            "rb3" if "-rb" in insn else "rd3", hex(b_val), bits, signed)
    else:  # rrii
        imm = b_val & 0xFFF
        word = _build_word_rrii(rec, 1, 2, imm)
        b_ext = _sext(imm, 12) if signed else imm
        expected = _cmp_result(a_val, b_ext, bits, signed)
        inp = {"rd": {"rd2": _hex64(a_val)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
        notes = "%s: rd2=%s, imm=%d, bits=%d, signed=%s" % (mnem, hex(a_val), b_ext, bits, signed)

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_compare_encoding(rec):
    """Encoding case for cmp."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    if fmt == "orrr":
        word = _build_word_orrr(rec, 1, 0, 0)
    else:  # rrii
        word = _build_word_rrii(rec, 1, 0, 0)

    return _case(mnem, insn, fmt, "encoding", word, {}, None, None,
                 "active", None, None, sc,
                 "encoding: word matches mask/value, rdhb=rd1 (non-rd0), fields legal")

# ── Conditional assignment ────────────────────────────────────────────
def gen_cs_semantic(rec, cond_val, val_true, val_false, taken):
    """Semantic for cs.* (rrrr). taken=True means condition is met."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    # cs.n/z/p: rdha=cond(src), rdhb=dst, rdhc=val_true(src), rdhd=val_false(src)
    # cs.eq/ne: rdha=a(src), rdhb=b(src), rdhc=dst, rdhd=val(src)
    if "cs.eq" in insn or "cs.ne" in insn:
        # rdha=1, rdhb=2, rdhc=3(dst), rdhd=4
        word = _build_word_rrrr(rec, 1, 2, 3, 4)
        expected = val_true if taken else 0  # cs.eq/ne: rdhc=rdhd if taken, else unchanged
        # Actually: cs.eq rdha,rdhb,rdhc,rdhd: if rdha==rdhb then rdhc=rdhd
        # So expected = val_false (rdhd) if taken, else rdhc unchanged
        # Wait: rdhc is dst, rdhd is the value to assign
        # cs.eq: if rdha==rdhb, rdhc=rdhd
        if "cs.eq" in insn:
            taken = (cond_val == val_true)  # rdha vs rdhb
            rdha_val = cond_val
            rdhb_val = val_true  # use as comparison target
            rdhc_old = 0xAAAA
            rdhd_val = val_false  # value to assign if taken
            expected = rdhd_val if taken else rdhc_old
            inp = {"rd": {"rd1": _hex64(rdha_val), "rd2": _hex64(rdhb_val),
                          "rd3": _hex64(rdhc_old), "rd4": _hex64(rdhd_val)}}
            out = {"rd": {"rd3": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
            notes = "cs.eq: rd1=%s, rd2=%s → %s, rd4→rd3" % (
                hex(rdha_val), hex(rdhb_val), "taken" if taken else "not taken")
        else:  # cs.ne
            rdha_val = cond_val
            rdhb_val = val_true
            rdhc_old = 0xAAAA
            rdhd_val = val_false
            taken = (rdha_val != rdhb_val)
            expected = rdhd_val if taken else rdhc_old
            inp = {"rd": {"rd1": _hex64(rdha_val), "rd2": _hex64(rdhb_val),
                          "rd3": _hex64(rdhc_old), "rd4": _hex64(rdhd_val)}}
            out = {"rd": {"rd3": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
            notes = "cs.ne: rd1=%s, rd2=%s → %s, rd4→rd3" % (
                hex(rdha_val), hex(rdhb_val), "taken" if taken else "not taken")
    else:
        # cs.n/z/p: rdha=cond(src), rdhb=dst, rdhc=val_true(src), rdhd=val_false(src)
        word = _build_word_rrrr(rec, 1, 2, 3, 4)
        rdha_val = cond_val
        rdhc_val = val_true
        rdhd_val = val_false

        if "cs.n" in insn:
            taken = (_sext(rdha_val, 64) < 0)
        elif "cs.z" in insn:
            taken = (rdha_val == 0)
        else:  # cs.p
            taken = (_sext(rdha_val, 64) > 0)

        expected = rdhc_val if taken else rdhd_val
        inp = {"rd": {"rd1": _hex64(rdha_val), "rd2": _hex64(0),
                      "rd3": _hex64(rdhc_val), "rd4": _hex64(rdhd_val)}}
        out = {"rd": {"rd2": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
        notes = "%s: rd1=%s → %s, rd3/rd4→rd2" % (
            mnem, hex(rdha_val), "taken" if taken else "not taken")

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

# ── Immediate / Block ─────────────────────────────────────────────────
def gen_imm_semantic(rec, wpN, immu16, rdha_old=0):
    """Semantic for set.zw/set.ow/or.w/andn.w (rwii)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    word = _build_word_rwii(rec, 1, wpN, immu16)

    wyde_shift = wpN * 16
    wyde_mask = 0xFFFF << wyde_shift

    if "set.zw" in insn:
        expected = (immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF
    elif "set.ow" in insn:
        expected = (~0xFFFF << wyde_shift) & 0xFFFFFFFFFFFFFFFF
        expected = expected | ((immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF)
    elif "or.w" in insn and fmt == "rwii":
        expected = rdha_old | ((immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF)
    elif "andn.w" in insn:
        expected = rdha_old & ~((immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF)
        expected = expected & 0xFFFFFFFFFFFFFFFF
    else:
        return None

    inp = {"rd": {"rd1": _hex64(rdha_old)}}
    out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
    notes = "%s: wp%d, immu16=0x%04X, rd1(old)=%s" % (mnem, wpN, immu16, hex(rdha_old))

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_imm_rb_semantic(rec, wpN, immu16, rbha_old=0):
    """Semantic for set.zw-rb/or.w-rb/andn.w-rb (rwii, rb dst)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    word = _build_word_rwii(rec, 1, wpN, immu16)

    wyde_shift = wpN * 16

    if "set.zw" in insn:
        expected = (immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF
    elif "or.w" in insn:
        expected = rbha_old | ((immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF)
    elif "andn.w" in insn:
        expected = rbha_old & ~((immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF)
        expected = expected & 0xFFFFFFFFFFFFFFFF
    else:
        return None

    inp = {"rb": {"rb1": _hex64(rbha_old)}}
    out = {"rd": {}, "rb": {"rb1": _hex64(expected)}, "ra": {}, "memory": []}
    notes = "%s: wp%d, immu16=0x%04X, rb1(old)=%s" % (mnem, wpN, immu16, hex(rbha_old))

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_block_semantic(rec, dst_reg, src_reg, count, src_bank, dst_bank):
    """Semantic for block move instructions."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    # For orri: ha(minor_op)|hb(dst)|hc(src)|hd(immu6)
    word = _build_word_orri(rec, dst_reg, src_reg, count)

    # Build source values
    src_vals = [0x10 + i for i in range(count)]
    inp = {}
    if src_bank == "rd":
        inp["rd"] = {}
        for i in range(count):
            inp["rd"]["rd%d" % (src_reg + i)] = _hex64(src_vals[i])
    elif src_bank == "rb":
        inp["rb"] = {}
        for i in range(count):
            inp["rb"]["rb%d" % (src_reg + i)] = _hex64(src_vals[i])
    elif src_bank == "ra":
        inp["ra"] = {}
        for i in range(count):
            inp["ra"]["ra%d" % (src_reg + i)] = _hex64(src_vals[i])

    # Build expected state
    out = {"rd": {}, "rb": {}, "ra": {}, "memory": []}
    if dst_bank == "rd":
        for i in range(count):
            out["rd"]["rd%d" % (dst_reg + i)] = _hex64(src_vals[i])
    elif dst_bank == "rb":
        for i in range(count):
            out["rb"]["rb%d" % (dst_reg + i)] = _hex64(src_vals[i])
    elif dst_bank == "ra":
        for i in range(count):
            out["ra"]["ra%d" % (dst_reg + i)] = _hex64(src_vals[i])

    notes = "%s: %s%d..%d → %s%d..%d, count=%d" % (
        mnem, src_bank, src_reg, src_reg + count - 1,
        dst_bank, dst_reg, dst_reg + count - 1, count)

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

# ── rela.si-rb special case ───────────────────────────────────────────
def gen_rela_si_semantic(rec, rbha_old, imm18, pc_addr):
    """Semantic for rela.si-rb: rbha = (PC & ~0xfff) + (sign_ext(imms18) << 12).
    rbha[63:48] preserved."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "riii"
    sc = "SimRISC-02 §PC相对寻址; ADR-0004 D6.5"

    word = _build_word_riii(rec, 1, imm18 & 0x3FFFF)

    # PC = rb0 = current instruction address (ADR-0004 D6.5)
    pc_base = pc_addr & ~0xFFF
    imm_s = _sext(imm18, 18)
    result_low48 = (pc_base + (imm_s << 12)) & 0xFFFFFFFFFFFF
    # Preserve rbha[63:48]
    result = (rbha_old & 0xFFFF000000000000) | result_low48

    inp = {"rb": {"rb1": _hex64(rbha_old)}}
    out = {"rd": {}, "rb": {"rb1": _hex64(result)}, "ra": {}, "memory": []}
    notes = "rela.si: PC=0x%012X (RAM entry, ADR-0004 D2.2), imms18=%d, (PC&~0xfff)=0x%012X, (imms18<<12)=0x%012X, result_low48=0x%012X, rb1[63:48] preserved" % (
        pc_addr, imm_s, pc_base, imm_s << 12, result_low48)

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

# ── rrrr arith (128-bit result) ───────────────────────────────────────
def gen_rrrr_arith_semantic(rec, a_val, b_val, rdha_old=0, rdhb_old=0):
    """Semantic for add.uo/so, sub.uo/so, mul.uo/so (rrrr)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "rrrr"
    sc = rec.get("spec_cite", "")

    # rrrr: rdha=1(dst_hi), rdhb=2(dst_lo), rdhc=3(src), rdhd=4(src)
    word = _build_word_rrrr(rec, 1, 2, 3, 4)

    bm = _base_mnem(insn)
    if "add" in insn:
        if "uo" in insn:
            result128 = a_val + b_val
        else:  # so
            sa, sb = _sext(a_val, 64), _sext(b_val, 64)
            result128 = sa + sb
    elif "sub" in insn:
        if "uo" in insn:
            result128 = a_val - b_val
        else:  # so
            sa, sb = _sext(a_val, 64), _sext(b_val, 64)
            result128 = sa - sb
    elif "mul" in insn:
        if "uo" in insn:
            result128 = a_val * b_val
        else:  # so
            sa, sb = _sext(a_val, 64), _sext(b_val, 64)
            result128 = sa * sb
    else:
        return None

    hi = (result128 >> 64) & 0xFFFFFFFFFFFFFFFF
    lo = result128 & 0xFFFFFFFFFFFFFFFF

    # For rrrr with one dst = rd0: rdha=rd0 means hi is discarded
    # For encoding, use rdha=1, rdhb=2 (both non-rd0)
    inp = {"rd": {"rd3": _hex64(a_val), "rd4": _hex64(b_val)}}
    out = {"rd": {"rd1": _hex64(hi), "rd2": _hex64(lo)}, "rb": {}, "ra": {}, "memory": []}
    notes = "%s: rd3=%s, rd4=%s → rd1(hi)=%s, rd2(lo)=%s" % (
        mnem, hex(a_val), hex(b_val), hex(hi), hex(lo))

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

def gen_rrrr_arith_overlap(rec, a_val, b_val):
    """Overlap for rrrr arith: rdha=rdhb (non-rd0) → ILLI."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "rrrr"
    sc = rec.get("spec_cite", "")

    # rdha=rdhb=1 → ILLI
    word = _build_word_rrrr(rec, 1, 1, 3, 4)

    inp = {"rd": {"rd1": _hex64(a_val), "rd3": _hex64(a_val), "rd4": _hex64(b_val)}}
    out = None

    return _case(mnem, insn, fmt, "overlap", word, inp, out, "ILLI",
                 "active", None, None, sc,
                 "overlap: rdha=rdhb=rd1 (same non-rd0 register) → ILLI")

def gen_rrrr_arith_boundary(rec, a_val, b_val):
    """Boundary for rrrr arith."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "rrrr"
    sc = rec.get("spec_cite", "")

    word = _build_word_rrrr(rec, 1, 2, 3, 4)

    bm = _base_mnem(insn)
    if "add" in insn:
        if "uo" in insn:
            result128 = a_val + b_val
        else:
            sa, sb = _sext(a_val, 64), _sext(b_val, 64)
            result128 = sa + sb
    elif "sub" in insn:
        if "uo" in insn:
            result128 = a_val - b_val
        else:
            sa, sb = _sext(a_val, 64), _sext(b_val, 64)
            result128 = sa - sb
    elif "mul" in insn:
        if "uo" in insn:
            result128 = a_val * b_val
        else:
            sa, sb = _sext(a_val, 64), _sext(b_val, 64)
            result128 = sa * sb
    else:
        return None

    hi = (result128 >> 64) & 0xFFFFFFFFFFFFFFFF
    lo = result128 & 0xFFFFFFFFFFFFFFFF

    inp = {"rd": {"rd3": _hex64(a_val), "rd4": _hex64(b_val)}}
    out = {"rd": {"rd1": _hex64(hi), "rd2": _hex64(lo)}, "rb": {}, "ra": {}, "memory": []}
    notes = "boundary %s: rd3=%s, rd4=%s" % (mnem, hex(a_val), hex(b_val))

    return _case(mnem, insn, fmt, "boundary", word, inp, out, None,
                 "active", None, None, sc, notes)

# ── riii arith (add.si-rd, add.si-rb) ─────────────────────────────────
def gen_riii_semantic(rec, rdha_old, imm18, bank="rd"):
    """Semantic for add.si-rd / add.si-rb."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "riii"
    sc = rec.get("spec_cite", "")

    word = _build_word_riii(rec, 1, imm18 & 0x3FFFF)

    imm_s = _sext(imm18, 18)
    expected = (rdha_old + imm_s) & 0xFFFFFFFFFFFFFFFF

    if bank == "rd":
        inp = {"rd": {"rd1": _hex64(rdha_old)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
    else:
        inp = {"rb": {"rb1": _hex64(rdha_old)}}
        out = {"rd": {}, "rb": {"rb1": _hex64(expected)}, "ra": {}, "memory": []}

    notes = "%s: %s1(old)=%s, imms18=%d → %s1=%s" % (
        mnem, bank, hex(rdha_old), imm_s, bank, hex(expected))

    return _case(mnem, insn, fmt, "semantic", word, inp, out, None,
                 "active", None, None, sc, notes)

# ── Block encoding ────────────────────────────────────────────────────
def gen_block_encoding(rec, dst_reg, src_reg, count):
    """Encoding case for block move instructions."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "orri"
    sc = rec.get("spec_cite", "")

    word = _build_word_orri(rec, dst_reg, src_reg, count)

    return _case(mnem, insn, fmt, "encoding", word, {}, None, None,
                 "active", None, None, sc,
                 "encoding: dst=%d, src=%d, count=%d, fields legal" % (dst_reg, src_reg, count))

# ── Deferred overlap case for cs.* (C-27, TESTCASES-009t legacy) ─────
def gen_cs_overlap_deferred(rec):
    """Generate deferred overlap case for cs.* (rrrr): rdha=rdhb=1 (same register).
    Deferred C-27: condition & source register aliasing semantics not yet specified."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    sc = rec.get("spec_cite", "")

    # rdha=rdhb=1 → same non-rd0 register (overlap condition)
    word = _build_word_rrrr(rec, 1, 1, 2, 4)

    # Input values matching the original semantic test values per cs variant
    # NOTE: check "cs.ne" and "cs.eq" BEFORE "cs.n" (substring match issue)
    if "cs.ne" in insn:
        inp = {"rd": {"rd1": _hex64(0x2A), "rd2": _hex64(0x63),
                       "rd3": _hex64(0xAAAA), "rd4": _hex64(0xBBBB)}}
    elif "cs.eq" in insn:
        inp = {"rd": {"rd1": _hex64(0x2A), "rd2": _hex64(0x2A),
                       "rd3": _hex64(0xAAAA), "rd4": _hex64(0xBBBB)}}
    elif "cs.n" in insn:
        inp = {"rd": {"rd1": _hex64(0xFFFFFFFFFFFFFFFF), "rd2": _hex64(0),
                       "rd3": _hex64(0xAAAA), "rd4": _hex64(0xBBBB)}}
    elif "cs.z" in insn:
        inp = {"rd": {"rd1": _hex64(0), "rd2": _hex64(0),
                       "rd3": _hex64(0xAAAA), "rd4": _hex64(0xBBBB)}}
    elif "cs.p" in insn:
        inp = {"rd": {"rd1": _hex64(1), "rd2": _hex64(0),
                       "rd3": _hex64(0xAAAA), "rd4": _hex64(0xBBBB)}}
    else:
        return None

    notes = "overlap C-27: %s snapshot — condition & source register aliasing deferred" % mnem
    return _case(mnem, insn, fmt, "overlap", word, inp, None, None,
                 "deferred", "C-27", None, sc, notes)


# ── Legality case generation (TESTCASES-010t) ────────────────────────
# Maps instruction operation to the applicable legality rule for rd0/rb0 dest violations.
# Rule spec_cite values come from contracts/legality_rules.yaml.

_ILLI_RULES = {
    # orrr single-dest (rdhb): rd_dest_rd0
    "rd_dest_rd0": "SimRISC-01 §rd0 为目的寄存器约定",
    # rrrr dual-dest (rdha, rdhb): dual_dest_both_rd0
    "dual_dest_both_rd0": "SimRISC-01 §加减操作",
    # orrr rb-dest (rbhb): rb_dest_rb0
    "rb_dest_rb0": "SimRISC-02 §rb0 为目的寄存器约定",
    # orri block move immu6=0
    "multi_immu6_zero": "SimRISC-01 §存取RD寄存器",
    # ra2rd dest rdhb=rd0
    "ra2rd_dest_rd0": "SimRISC-02 §寄存器组之间块赋值",
    # ra block immu6=0
    "ra_multi_immu6_zero": "SimRISC-02 §存取RA寄存器、§寄存器组之间块赋值",
}


def _get_illi_rule_id(rec):
    """Return the legality rule id for rd0/rb0 dest violation.
    Routes by the destination field's bank in opcodes.yaml, NOT by insn name."""
    fmt = rec["format"]
    if fmt == "rrrr":
        return "dual_dest_both_rd0"
    # Check destination field bank from opcodes.yaml
    for field in rec.get("fields", []):
        if field.get("role") == "dst":
            if field.get("bank") == "rb":
                return "rb_dest_rb0"
            break
    return "rd_dest_rd0"


def gen_legality_rd0(rec):
    """Generate a legality case where the destination register is rd0 (or rb0 for rb-dest).
    The encoding word is valid (decodable) but the operand field violates a legality rule."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = rec["format"]
    rule_id = _get_illi_rule_id(rec)
    rule_cite = _ILLI_RULES[rule_id]
    sc = rec.get("spec_cite", "")

    if fmt == "rrrr":
        # rdha=0, rdhb=0 → both rd0 → ILLI (dual_dest_both_rd0)
        word = _build_word_rrrr(rec, 0, 0, 0, 0)
    elif fmt == "orrr":
        # rdhb=0 → rd0 as dest → ILLI (rd_dest_rd0 or rb_dest_rb0)
        op_base = _base_mnem(insn)
        is_divrem = op_base in ("div", "rem")
        rdhd = 1 if is_divrem else 0  # avoid div-by-zero fault
        word = _build_word_orrr(rec, 0, 0, rdhd)
    elif fmt == "orri":
        # rdhb=0 → rd0 as dest; hd=0 is valid shamt/ext-bit for all sizes
        word = _build_word_orri(rec, 0, 0, 0)
    elif fmt == "rrii":
        # rdha=0 → rd0 as dest
        word = _build_word_rrii(rec, 0, 0, 0)
    elif fmt == "riii":
        # rdha=0 → rd0 as dest
        word = _build_word_riii(rec, 0, 0)
    else:
        return None

    notes = "legality %s: dest=rd0/rb0 → ILLI (%s)" % (mnem, rule_id)
    return _case(mnem, insn, fmt, "legality", word, {}, None, "ILLI",
                 "active", None, None, "%s; %s" % (sc, rule_cite), notes)


def gen_riii_boundary_overflow(rec, bank):
    """Boundary case for add.si-rd / add.si-rb: overflow wrap-around.
    rdha/rbha = INT64_MAX, imms18 = 1 → result = INT64_MIN (wrap-around, no fault)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "riii"
    sc = rec.get("spec_cite", "")

    INT64_MAX = 0x7FFFFFFFFFFFFFFF
    imm18 = 1  # 18-bit signed = 1
    word = _build_word_riii(rec, 1, imm18)

    # Expected: (INT64_MAX +1) & 0xFFFFFFFFFFFFFFFF = 0x8000000000000000 = INT64_MIN
    expected = (INT64_MAX + 1) & 0xFFFFFFFFFFFFFFFF

    if bank == "rd":
        inp = {"rd": {"rd1": _hex64(INT64_MAX)}}
        out = {"rd": {"rd1": _hex64(expected)}, "rb": {}, "ra": {}, "memory": []}
    else:
        inp = {"rb": {"rb1": _hex64(INT64_MAX)}}
        out = {"rd": {}, "rb": {"rb1": _hex64(expected)}, "ra": {}, "memory": []}

    notes = "boundary %s: %s1=INT64_MAX(0x7FFFFFFFFFFFFFFF), imms18=1 → overflow wrap to INT64_MIN(0x8000000000000000)" % (
        mnem, "rd" if bank == "rd" else "rb")
    return _case(mnem, insn, fmt, "boundary", word, inp, out, None,
                 "active", None, None, sc, notes)


# ── Block move legality (TESTCASES-011t) ──────────────────────────────
def gen_block_legality_multi_immu6_zero(rec):
    """Legality case for block move (orri): immu6=0 → ILLI.
    rd2rd/rb2rb/rb2rd/rd2rb: multi_immu6_zero.
    ra2rd/rd2ra: ra_multi_immu6_zero."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "orri"
    if insn in ("ra2rd", "rd2ra"):
        rule_id = "ra_multi_immu6_zero"
    else:
        rule_id = "multi_immu6_zero"
    rule_cite = _ILLI_RULES[rule_id]
    sc = rec.get("spec_cite", "")
    word = _build_word_orri(rec, 1, 3, 0)
    notes = "legality %s: immu6=0 → ILLI (%s)" % (mnem, rule_id)
    return _case(mnem, insn, fmt, "legality", word, {}, None, "ILLI",
                 "active", None, None, "%s; %s" % (sc, rule_cite), notes)


def gen_ra2rd_legality_dest_rd0(rec):
    """Legality case for ra2rd: rdhb=rd0 → ILLI (ra2rd_dest_rd0)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "orri"
    rule_id = "ra2rd_dest_rd0"
    rule_cite = _ILLI_RULES[rule_id]
    sc = rec.get("spec_cite", "")
    word = _build_word_orri(rec, 0, 3, 1)
    notes = "legality %s: rdhb=rd0 → ILLI (%s)" % (mnem, rule_id)
    return _case(mnem, insn, fmt, "legality", word, {}, None, "ILLI",
                 "active", None, None, "%s; %s" % (sc, rule_cite), notes)


def gen_rwii_legality_dest_rd0(rec):
    """Legality case for rwii (rd-dest): rdha=rd0 → ILLI (rd_dest_rd0)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "rwii"
    rule_id = "rd_dest_rd0"
    rule_cite = _ILLI_RULES[rule_id]
    sc = rec.get("spec_cite", "")
    word = _build_word_rwii(rec, 0, 0, 0)
    notes = "legality %s: rdha=rd0 → ILLI (%s)" % (mnem, rule_id)
    return _case(mnem, insn, fmt, "legality", word, {}, None, "ILLI",
                 "active", None, None, "%s; %s" % (sc, rule_cite), notes)


def gen_rwii_legality_dest_rb0(rec):
    """Legality case for rwii (rb-dest): rbha=rb0 → ILLI (rb_dest_rb0)."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "rwii"
    rule_id = "rb_dest_rb0"
    rule_cite = _ILLI_RULES[rule_id]
    sc = rec.get("spec_cite", "")
    word = _build_word_rwii(rec, 0, 0, 0)
    notes = "legality %s: rbha=rb0 → ILLI (%s)" % (mnem, rule_id)
    return _case(mnem, insn, fmt, "legality", word, {}, None, "ILLI",
                 "active", None, None, "%s; %s" % (sc, rule_cite), notes)


def gen_block_overlap(rec):
    """Generate overlap case for block move (orri).
    Sequential semantics (contract-isa.md:467): ascending order, each pair
    read-then-write. For same-bank overlapping ranges (rd2rd, rb2rb with
    dst=src+1, count=2), later reads see earlier writes.
    For cross-bank (rb2rd, rd2rb, ra2rd, rd2ra): no register aliasing,
    verifies basic block move semantics."""
    mnem = rec["mnemonic"]
    insn = rec["insn"]
    fmt = "orri"
    sc = rec.get("spec_cite", "")

    count = 2
    is_same_bank = insn in ("rd2rd", "rb2rb")
    if insn == "rd2rd":
        src_bank, dst_bank, src_reg, dst_reg = "rd", "rd", 2, 3
    elif insn == "rb2rb":
        src_bank, dst_bank, src_reg, dst_reg = "rb", "rb", 2, 3
    elif insn == "rb2rd":
        src_bank, dst_bank, src_reg, dst_reg = "rb", "rd", 3, 3
    elif insn == "rd2rb":
        src_bank, dst_bank, src_reg, dst_reg = "rd", "rb", 3, 3
    elif insn == "ra2rd":
        src_bank, dst_bank, src_reg, dst_reg = "ra", "rd", 3, 3
    elif insn == "rd2ra":
        src_bank, dst_bank, src_reg, dst_reg = "rd", "ra", 3, 3
    else:
        return None

    word = _build_word_orri(rec, dst_reg, src_reg, count)

    src_vals = [0x10 + i for i in range(count)]
    inp = {}
    if src_bank == "rd":
        inp["rd"] = {"rd%d" % (src_reg + i): _hex64(src_vals[i]) for i in range(count)}
    elif src_bank == "rb":
        inp["rb"] = {"rb%d" % (src_reg + i): _hex64(src_vals[i]) for i in range(count)}
    elif src_bank == "ra":
        inp["ra"] = {"ra%d" % (src_reg + i): _hex64(src_vals[i]) for i in range(count)}

    # Sequential semantics: ascending order, read-then-write per pair.
    # For same-bank overlap (dst=src+1, count=2):
    #   pair0: read src[0], write dst[0]  → dst[0] = src[0]
    #   pair1: read src[1] (overlaps dst[0], now has new value), write dst[1]
    # So dst[1] gets the VALUE JUST WRITTEN to dst[0], not the original src[1].
    if is_same_bank:
        # After pair0: dst[0] = original src[0]
        # pair1: read src[1] which IS dst[0] → reads new value = original src[0]
        # So dst[1] = original src[0] too
        final_vals = [src_vals[0], src_vals[0]]  # both get src[0]
    else:
        # No aliasing: each dst gets its corresponding src
        final_vals = list(src_vals)

    out = {"rd": {}, "rb": {}, "ra": {}, "memory": []}
    if dst_bank == "rd":
        for i in range(count):
            out["rd"]["rd%d" % (dst_reg + i)] = _hex64(final_vals[i])
    elif dst_bank == "rb":
        for i in range(count):
            out["rb"]["rb%d" % (dst_reg + i)] = _hex64(final_vals[i])
    elif dst_bank == "ra":
        for i in range(count):
            out["ra"]["ra%d" % (dst_reg + i)] = _hex64(final_vals[i])

    if is_same_bank:
        notes = ("overlap %s: %s%d..%d → %s%d..%d, count=%d, "
                 "sequential semantics: dst overlaps src → "
                 "dst[1] reads dst[0]'s new value" % (
                     mnem, src_bank, src_reg, src_reg + count - 1,
                     dst_bank, dst_reg, dst_reg + count - 1, count))
    else:
        notes = ("overlap %s: %s%d..%d → %s%d..%d, count=%d, "
                 "cross-bank no aliasing, verifies basic block move semantics" % (
                     mnem, src_bank, src_reg, src_reg + count - 1,
                     dst_bank, dst_reg, dst_reg + count - 1, count))

    return _case(mnem, insn, fmt, "overlap", word, inp, out, None,
                 "active", None, None, sc, notes)


# ── Main generation logic ─────────────────────────────────────────────
# Files that need legality cases (TESTCASES-010t)
_TARGET_FILES_010T = {"reg-arith.yaml", "reg-logic.yaml", "reg-shift-extend.yaml", "reg-compare.yaml"}

def _op_from_insn(insn):
    """Get the operation name from insn for matching.
    'and.o' → 'and', 'add.so-rb' → 'add.so', 'rd2rd' → 'rd2rd',
    'set.zw-rd' → 'set.zw', 'cs.n-rd' → 'cs.n'
    """
    base = insn.split('-')[0] if '-' in insn else insn
    return base

def generate_file(filename, recs):
    """Generate all cases for a file."""
    cases = []
    deferred_overlap = []  # collected separately, appended at end (ordering match)

    for rec in recs:
        mnem = rec["mnemonic"]
        insn = rec["insn"]
        fmt = rec["format"]
        sc = rec.get("spec_cite", "")
        bits = _get_bits(mnem)
        op = _op_from_insn(insn)

        # Determine operation type
        is_block = op in BLOCK
        is_imm_block = op in IMM_BLOCK_RWII and fmt == "rwii"
        is_logic = op.split('.')[0] in LOGIC if '.' in op else op in LOGIC
        is_logic = is_logic and not is_imm_block  # or.w-rd is imm, not logic
        is_shift = op.split('.')[0] in SHIFT if '.' in op else op in SHIFT
        is_compare = op.split('.')[0] in COMPARE if '.' in op else op in COMPARE
        is_cond = op.split('.')[0] in COND if '.' in op else op in COND
        is_arith_rb = op in ("add.so", "sub.so") and fmt == "orrr"
        is_rela = "rela.si" in insn
        is_divrem = op.split('.')[0] in ("div", "rem") if '.' in op else False
        is_mul = op.split('.')[0] == "mul" if '.' in op else False

        # ── Encoding case ──
        enc_input_state = None  # may be set for div/rem
        if fmt == "rrrr":
            if "cs.eq" in insn or "cs.ne" in insn:
                enc_word = _build_word_rrrr(rec, 1, 2, 3, 4)
            else:
                enc_word = _build_word_rrrr(rec, 1, 2, 0, 0)
        elif fmt == "orrr":
            if is_divrem:
                enc_word = _build_word_orrr(rec, 1, 0, 1)  # rdhd=1 (rd1=divisor)
                enc_input_state = {"rd": {"rd1": "0x0000000000000001"}}  # non-zero to avoid div_by_zero
            else:
                enc_word = _build_word_orrr(rec, 1, 0, 0)
        elif fmt == "orri":
            if is_block:
                cases.append(gen_block_encoding(rec, 1, 3, 1))
                enc_word = None
            else:
                enc_word = _build_word_orri(rec, 1, 0, 1)
        elif fmt == "rrii":
            enc_word = _build_word_rrii(rec, 1, 0, 0)
        elif fmt == "riii":
            enc_word = _build_word_riii(rec, 1, 0)
        elif fmt == "rwii":
            enc_word = _build_word_rwii(rec, 1, 0, 0)
        else:
            enc_word = None

        if enc_word is not None:
            cases.append(gen_encoding(rec, enc_word, enc_input_state))

        # ── Semantic case ──
        if is_logic:
            c = gen_semantic_orrr_arith(rec, 0xAAAAAAAAAAAAAAAA, 0x5555555555555555, 0)
            if c: cases.append(c)
        elif is_shift:
            N = _get_N(insn, mnem)
            shamt = min(2, N)
            src_val = 0x0F0F0F0F0F0F0F0F
            if fmt == "orrr":
                c = gen_shift_orrr_semantic(rec, src_val, shamt, 0)
                if c: cases.append(c)
            else:  # orri
                c = gen_shift_orri_semantic(rec, src_val, shamt, 0)
                if c: cases.append(c)
        elif is_compare:
            if fmt == "orrr":
                c = gen_compare_semantic(rec, 10, 20)
            else:
                c = gen_compare_semantic(rec, 10, 5)
            if c: cases.append(c)
        elif is_cond:
            if "cs.n-" in insn:
                cases.append(gen_cs_semantic(rec, 0xFFFFFFFFFFFFFFFF, 0xAAAA, 0xBBBB, True))
            elif "cs.z-" in insn:
                cases.append(gen_cs_semantic(rec, 0, 0xAAAA, 0xBBBB, True))
            elif "cs.p-" in insn:
                cases.append(gen_cs_semantic(rec, 1, 0xAAAA, 0xBBBB, True))
            elif "cs.eq-" in insn:
                cases.append(gen_cs_semantic(rec, 42, 42, 0xBBBB, True))
            elif "cs.ne-" in insn:
                cases.append(gen_cs_semantic(rec, 42, 99, 0xBBBB, True))
        elif is_imm_block:
            if "set.zw" in insn and "-rd" in insn:
                cases.append(gen_imm_semantic(rec, 0, 0x1234, 0))
            elif "set.ow" in insn:
                cases.append(gen_imm_semantic(rec, 0, 0x1234, 0))
            elif "or.w" in insn and "-rd" in insn:
                cases.append(gen_imm_semantic(rec, 0, 0xFF00, 0x00FF00FF00FF00FF))
            elif "andn.w" in insn and "-rd" in insn:
                cases.append(gen_imm_semantic(rec, 0, 0xFF00, 0xFFFFFFFFFFFFFFFF))
            elif "set.zw" in insn and "-rb" in insn:
                cases.append(gen_imm_rb_semantic(rec, 0, 0x1234, 0))
            elif "or.w" in insn and "-rb" in insn:
                cases.append(gen_imm_rb_semantic(rec, 0, 0xFF00, 0x00FF00FF00FF00FF))
            elif "andn.w" in insn and "-rb" in insn:
                cases.append(gen_imm_rb_semantic(rec, 0, 0xFF00, 0xFFFFFFFFFFFFFFFF))
        elif is_block:
            if insn == "rd2rd":
                cases.append(gen_block_semantic(rec, 1, 3, 1, "rd", "rd"))
            elif insn == "rb2rb":
                cases.append(gen_block_semantic(rec, 1, 3, 1, "rb", "rb"))
            elif insn == "rb2rd":
                cases.append(gen_block_semantic(rec, 1, 3, 1, "rb", "rd"))
            elif insn == "rd2rb":
                cases.append(gen_block_semantic(rec, 1, 3, 1, "rd", "rb"))
            elif insn == "ra2rd":
                cases.append(gen_block_semantic(rec, 1, 3, 1, "ra", "rd"))
            elif insn == "rd2ra":
                cases.append(gen_block_semantic(rec, 1, 3, 1, "rd", "ra"))
        elif is_rela:
            c = gen_rela_si_semantic(rec, 0, 1, 0xFFFF00000000)
            if c: cases.append(c)
        elif is_arith_rb:
            c = gen_semantic_orrr_arith_rb(rec, 100, 30, 0)
            if c: cases.append(c)
        elif fmt == "rrrr":
            c = gen_rrrr_arith_semantic(rec, 100, 30)
            if c: cases.append(c)
        elif fmt == "orrr" and is_divrem:
            c = gen_semantic_orrr_arith(rec, 100, 7, 0)
            if c: cases.append(c)
        elif fmt == "orrr" and not is_logic and not is_shift and not is_compare:
            # MISC byte/wyde/tetra arith
            c = gen_semantic_orrr_arith(rec, 50, 30, 0)
            if c: cases.append(c)
        elif fmt == "riii":
            if is_rela:
                pass  # handled above
            elif "-rb" in insn:
                c = gen_riii_semantic(rec, 0x10000, 1, "rb")
                if c: cases.append(c)
            else:
                c = gen_riii_semantic(rec, 100, 7, "rd")
                if c: cases.append(c)

        # ── Boundary case ──
        if is_shift:
            N = _get_N(insn, mnem)
            src_val = 0x0F0F0F0F0F0F0F0F
            if fmt == "orrr":
                c = gen_shift_orrr_boundary(rec, src_val, N, 0)
                if c: cases.append(c)
            else:  # orri
                c = gen_shift_orri_boundary(rec, src_val, N, 0)
                if c: cases.append(c)
        elif is_logic:
            c = gen_boundary_orrr_arith(rec, 0xFFFF0000FFFF0000, 0x0000FFFF0000FFFF, 0)
            if c: cases.append(c)
        elif is_compare or is_cond or is_imm_block or is_block or is_rela:
            pass  # boundary not required per inventory for these
        elif is_arith_rb:
            c = gen_boundary_orrr_arith_rb(rec, 0x8000000000000000, 1, 0)
            if c: cases.append(c)
        elif fmt == "rrrr":
            c = gen_rrrr_arith_boundary(rec, 0x8000000000000000, 0x8000000000000000)
            if c: cases.append(c)
        elif fmt == "orrr" and is_divrem:
            # For signed div/rem, use negative dividend to exercise sign extension
            is_signed_dr = (".so" in mnem or ".sb" in mnem or ".sw" in mnem or ".st" in mnem)
            if is_signed_dr:
                c = gen_boundary_orrr_arith(rec, 0x80, 7, 0)  # 0x80 as signed = -128
            else:
                c = gen_boundary_orrr_arith(rec, 100, 7, 0)
            if c: cases.append(c)
        elif fmt == "orrr" and not is_logic and not is_shift and not is_compare:
            # For signed variants, use values that produce negative result (sign bit set)
            # so sign extension is exercised: e.g. add.sb(0x40,0x40)=0x80 → sign-extend
            is_signed_misc = (".so" in mnem or ".sb" in mnem or ".sw" in mnem or ".st" in mnem)
            if is_signed_misc:
                c = gen_boundary_orrr_arith(rec, 0x40, 0x40, 0)
            else:
                c = gen_boundary_orrr_arith(rec, 0x80, 0x80, 0)
            if c: cases.append(c)
        elif fmt == "riii" and not is_rela:
            bank = "rb" if "-rb" in insn else "rd"
            c = gen_riii_semantic(rec, 0x7FFFFFFFFFFFFFFF, 1, bank)
            if c: cases.append(c)

        # ── Overlap case (rrrr only, for arith) ──
        if fmt == "rrrr" and not is_cond and not is_compare:
            c = gen_rrrr_arith_overlap(rec, 100, 30)
            if c: cases.append(c)

        # ── Deferred overlap case for cs.* (C-27) ──
        if is_cond and filename == "reg-cond-assign.yaml":
            c = gen_cs_overlap_deferred(rec)
            if c: deferred_overlap.append(c)

        # ── Legality case (TESTCASES-010t: rd0/rb0 dest → ILLI) ──
        # Only for the 4 target files in this task
        if filename in _TARGET_FILES_010T:
            c = gen_legality_rd0(rec)
            if c: cases.append(c)

        # ── Legality case (TESTCASES-011t: cs.* rdhb=rd0 → ILLI) ──
        if is_cond and filename == "reg-cond-assign.yaml":
            # cs.n/z/p: rdhb is dst → rdhb=0 → ILLI (rd_dest_rd0)
            # cs.eq/ne: rdhc is dst → rdhc=0 → ILLI (rd_dest_rd0)
            if "cs.eq" in insn or "cs.ne" in insn:
                word = _build_word_rrrr(rec, 1, 2, 0, 3)  # rdhc=0 (dst=rd0)
            else:
                word = _build_word_rrrr(rec, 1, 0, 3, 4)  # rdhb=0 (dst=rd0)
            rule_id = "rd_dest_rd0"
            rule_cite = _ILLI_RULES[rule_id]
            sc = rec.get("spec_cite", "")
            notes = "legality %s: dest=rd0 → ILLI (%s)" % (mnem, rule_id)
            cases.append(_case(mnem, insn, fmt, "legality", word, {}, None, "ILLI",
                               "active", None, None, "%s; %s" % (sc, rule_cite), notes))

        # ── Legality case (TESTCASES-011t: reg-imm-block) ──
        if is_block and filename == "reg-imm-block.yaml":
            # orri block moves: immu6=0 → ILLI
            cases.append(gen_block_legality_multi_immu6_zero(rec))
            # ra2rd additional: rdhb=rd0 → ILLI
            if insn == "ra2rd":
                cases.append(gen_ra2rd_legality_dest_rd0(rec))
        if is_imm_block and filename == "reg-imm-block.yaml":
            # rwii: rd/rb dest = rd0/rb0 → ILLI
            if "-rd" in insn:
                cases.append(gen_rwii_legality_dest_rd0(rec))
            elif "-rb" in insn:
                cases.append(gen_rwii_legality_dest_rb0(rec))

        # ── Overlap case (TESTCASES-011t: block move overlap) ──
        if is_block and filename == "reg-imm-block.yaml":
            c = gen_block_overlap(rec)
            if c: cases.append(c)

        # ── Boundary overflow case for add.si-rd / add.si-rb (TESTCASES-010t) ──
        if filename == "reg-arith.yaml" and fmt == "riii" and not is_rela and "add.si" in insn:
            bank = "rb" if "-rb" in insn else "rd"
            c = gen_riii_boundary_overflow(rec, bank)
            if c: cases.append(c)

    # Append deferred overlap cases at end (ordering: encoding/semantic first, then overlap)
    cases.extend(deferred_overlap)
    return cases


# ── Generate all files ────────────────────────────────────────────────
os.makedirs(OUT, exist_ok=True)

for fname, recs in FILE_MAP.items():
    if not recs:
        continue
    cases = generate_file(fname, recs)
    path = os.path.join(OUT, fname)
    with open(path, "w") as f:
        f.write("# Generated by TESTCASES-003t generator — DO NOT EDIT\n")
        f.write("# Source: contracts/opcodes.yaml + contract-isa.md + adr-0004\n")
        f.write("# Each case has spec_cite and notes for traceability.\n\n")
        yaml.dump(cases, f, default_flow_style=False, allow_unicode=True, width=120)
    print("Wrote %s: %d cases for %d identities" % (fname, len(cases), len(recs)))

print("\nDone. Total identities: %d" % sum(len(v) for v in FILE_MAP.values()))
