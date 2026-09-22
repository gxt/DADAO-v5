#!/usr/bin/env python3
"""009t-audit.py — ISA 向量全量再审计：独立重推导/覆盖统计脚本。

功能：
  1. 读取 contracts/opcodes.yaml + tests/vectors/isa/*.yaml
  2. 按 contract-isa.md 公式逐条重算 semantic/boundary/overlap 期望值
  3. 与向量数据比对，报告 mismatch
  4. 输出逐族统计（case 数、active/deferred、各类分布）

覆盖范围：
  - rrrr 128-bit add/sub/mul (§3.1.1/§3.1.4)
  - orrr fixed-width add/sub/mul/div/rem/cmp (§3.1.2/§3.1.5/§3.2.2)
  - orrr logic and/or/xor/xnor .b/.w/.t/.o (§3.3)
  - orrr/orri shift/extend .ub/.sb/.uw/.sw/.ut/.st/.uo/.so (§3.4.1/§3.4.2)
  - riii add.si/rela.si (§3.1.3/§4.7)
  - rrii cmp.ui/cmp.si (§3.2.1)
  - rrrr cs.n/z/p/eq/ne (§3.5)
  - rwii set.zw/set.ow/or.w/andn.w -rd/-rb (§3.6)
  - orri block assignment rd2rd/rd2ra/ra2rd/rb2rb/rd2rb/rb2rd (§3.7/§4.3)
  - rrii ld/st -rd/-rb/-ra (§4.1.1/§4.2/§4.9.1)
  - rrri ldm/stm -rd/-rb/-ra (§4.1.2)
  - riii/rrii br.* (§5.2)
  - iiii/rrii jump (§5.3)
  - iiii/rrii call (§5.4, 含 §5.6.1 RA 压栈)
  - riii ret (§5.5)
  - orrr cmp.uo-rb / add.so-rb / sub.so-rb (§4.5.1/§4.6)

跳过（nop 类，不产生期望状态）：
  - swym-iiii、fence

使用：
  python3 tools/testcases/009t-audit.py [--verbose]

退出码：0 = 全部通过，1 = 有 mismatch。
"""

import argparse
import glob
import os
import re
import sys
from collections import defaultdict

try:
    import yaml as _yaml
except ImportError:
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_int(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip()
        if s.startswith(("0x", "0X")):
            return int(s, 16)
        return int(s)
    raise ValueError("not an integer: %r" % (val,))


def _hex64(v):
    return "0x%016X" % (v & 0xFFFFFFFFFFFFFFFF)


def _sign_extend(val, bits):
    """Sign-extend a value from `bits` bits to Python int."""
    if val & (1 << (bits - 1)):
        return val - (1 << bits)
    return val


def _zero_extend(val, bits):
    """Zero-extend (mask to bits)."""
    return val & ((1 << bits) - 1)


# ---------------------------------------------------------------------------
# Load opcodes.yaml
# ---------------------------------------------------------------------------

def load_opcodes(path):
    with open(path) as fh:
        records = _yaml.safe_load(fh)
    by_key = {}
    for rec in records:
        key = (rec["insn"], rec["format"])
        by_key[key] = rec
    return records, by_key


# ---------------------------------------------------------------------------
# Extract field value from encoding word
# ---------------------------------------------------------------------------

def extract_field(word, fields, field_name):
    """Return integer value of named field from word, or None."""
    for fld in fields:
        if fld["name"] == field_name:
            m = re.match(r"\[(\d+):(\d+)\]", fld.get("bits", ""))
            if m:
                hi, lo = int(m.group(1)), int(m.group(2))
                return (word >> lo) & ((1 << (hi - lo + 1)) - 1)
    return None


# ---------------------------------------------------------------------------
# Recompute expected_state for a given case
# Returns (expected_dict, mismatch_list)
# ---------------------------------------------------------------------------

def recompute_expected(case, word, fields, by_key, verbose=False):
    """Recompute expected_state based on contract-isa.md formulas.

    Returns (expected_rd, expected_rb, expected_ra, expected_memory,
             expected_pc, mismatches).
    Only returns non-None for fields that can be recomputed.
    """
    insn = case.get("insn", "")
    mnemonic = case.get("mnemonic", "")
    fmt = case.get("format", "")
    cls = case.get("class", "")
    status = case.get("status", "active")
    input_state = case.get("input_state", {})
    actual_exp = case.get("expected_state", {})
    actual_pc = case.get("expected_pc")

    mismatches = []

    # Only recompute active semantic/boundary/overlap cases
    if status != "active" or cls not in ("semantic", "boundary", "overlap"):
        return None, None, None, None, None, mismatches

    # Skip deferred cases
    if case.get("deferred_reason"):
        return None, None, None, None, None, mismatches

    # Skip fault cases (expected_fault != null)
    if case.get("expected_fault"):
        return None, None, None, None, None, mismatches

    # Get pre-set register values
    inp_rd = input_state.get("rd", {})
    inp_rb = input_state.get("rb", {})
    inp_ra = input_state.get("ra", {})

    # rb0 = PC (hardwired). Test vectors use rb0 = 0xFFFF00000000 (RAM entry, ADR-0004 D2.2)
    # This is not in input_state; read from notes or use convention.
    RB0_PC = 0xFFFF_0000_0000  # Default convention for test vectors

    def get_rd(name):
        if name == "rd0":
            return 0
        v = inp_rd.get(name)
        return _to_int(v) if v is not None else None

    def get_rb(name):
        if name == "rb0":
            return RB0_PC
        v = inp_rb.get(name)
        return _to_int(v) if v is not None else None

    def get_ra(name):
        v = inp_ra.get(name)
        return _to_int(v) if v is not None else None

    def _do_ra_push(inp_ra_dict, exp_ra_dict, return_addr):
        """RA push (§5.6.1): push return_addr into ra63 stack."""
        old_ra63_val = inp_ra_dict.get("ra63")
        old_ra63 = _to_int(old_ra63_val) if old_ra63_val is not None else 0
        old_high = (old_ra63 >> 48) & 0xFFFF
        old_low = old_ra63 & 0xFFFFFFFFFFFF
        new_low = return_addr & 0xFFFFFFFFFFFF

        if old_high == 0:
            # Case 1: ra63 invalid → new entry with ref_count=1
            exp_ra_dict["ra63"] = _hex64((0x0001 << 48) | new_low)
        elif old_high != 0xFFFF and new_low == old_low:
            # Case 2: recursive call → increment ref_count
            exp_ra_dict["ra63"] = _hex64(((old_high + 1) << 48) | new_low)
        else:
            # Case 3: shift push
            exp_ra_dict["ra63"] = _hex64((0x0001 << 48) | new_low)
            # Shift old ra63 → ra62, ra62 → ra61, etc.
            # For simplicity, only handle single-level shift (most test cases)
            # Read current ra62 from input or expected
            for n in range(62, 0, -1):
                src_name = "ra%d" % (n + 1)  # ra63, ra62, ...
                dst_name = "ra%d" % n         # ra62, ra61, ...
                # Source: from input_state (original before push)
                src_val = inp_ra_dict.get(src_name)
                if src_val is not None:
                    if dst_name not in exp_ra_dict:  # don't overwrite already-set
                        exp_ra_dict[dst_name] = src_val
                else:
                    break  # No more entries to shift

    # Extract common fields — use get() with default None to avoid short-circuit issues
    def _ef(name):
        v = extract_field(word, fields, name)
        return v

    ha = _ef("rdha")
    if ha is None:
        ha = _ef("rbha")
    if ha is None:
        ha = _ef("raha")
    hb = _ef("rdhb")
    if hb is None:
        hb = _ef("rbhb")
    if hb is None:
        hb = _ef("rahb")
    hc = _ef("rdhc")
    if hc is None:
        hc = _ef("rbhc")
    if hc is None:
        hc = _ef("rahc")
    hd = _ef("rdhd")
    if hd is None:
        hd = _ef("rbhd")

    # Helper to get register value by bank and index
    def get_reg(bank, idx):
        if idx == 0:
            return 0
        name = "%s%d" % (bank, idx)
        if bank == "rd":
            return get_rd(name)
        elif bank == "rb":
            return get_rb(name)
        elif bank == "ra":
            return get_ra(name)
        return None

    expected_rd = {}
    expected_rb = {}
    expected_ra = {}
    expected_memory = None
    expected_pc = None

    # ── rrrr 128-bit add/sub (§3.1.1) ──────────────────────────────────
    if fmt == "rrrr" and any(mnemonic.startswith(p) for p in ("add.uo", "add.so", "sub.uo", "sub.so")):
        rdha = ha
        rdhb = hb
        rdhc = hc
        rdhd = hd
        src_c = get_rd("rd%d" % rdhc) if rdhc else None
        src_d = get_rd("rd%d" % rdhd) if rdhd else None
        if src_c is not None and src_d is not None:
            is_signed = ".so" in mnemonic or ".so" in mnemonic
            is_sub = "sub" in mnemonic
            if is_signed:
                c128 = _sign_extend(src_c, 64)
                d128 = _sign_extend(src_d, 64)
            else:
                c128 = src_c
                d128 = src_d
            if is_sub:
                result = c128 - d128
            else:
                result = c128 + d128
            hi = (result >> 64) & 0xFFFFFFFFFFFFFFFF
            lo = result & 0xFFFFFFFFFFFFFFFF
            if not is_signed:
                # unsigned: hi = carry/borrow (0 or 1)
                hi = 1 if (result >> 64) != 0 else 0
            if rdha != 0:
                expected_rd["rd%d" % rdha] = _hex64(hi)
            if rdhb != 0:
                expected_rd["rd%d" % rdhb] = _hex64(lo)

    # ── rrrr mul.uo/mul.so (§3.1.4) ────────────────────────────────────
    elif fmt == "rrrr" and any(mnemonic.startswith(p) for p in ("mul.uo", "mul.so")):
        rdha = ha
        rdhb = hb
        rdhc = hc
        rdhd = hd
        src_c = get_rd("rd%d" % rdhc) if rdhc else None
        src_d = get_rd("rd%d" % rdhd) if rdhd else None
        if src_c is not None and src_d is not None:
            is_signed = ".so" in mnemonic
            if is_signed:
                c = _sign_extend(src_c, 64)
                d = _sign_extend(src_d, 64)
                result = c * d
            else:
                result = src_c * src_d
            hi = (result >> 64) & 0xFFFFFFFFFFFFFFFF
            lo = result & 0xFFFFFFFFFFFFFFFF
            if rdha != 0:
                expected_rd["rd%d" % rdha] = _hex64(hi)
            if rdhb != 0:
                expected_rd["rd%d" % rdhb] = _hex64(lo)

    # ── orrr fixed-width add/sub (§3.1.2) ──────────────────────────────
    elif fmt == "orrr" and mnemonic.startswith(("add.", "sub.")) and \
            any(s in mnemonic for s in (".ub", ".sb", ".uw", ".sw", ".ut", ".st")):
        rdhb = hb
        rdhc = hc
        rdhd = hd
        src_c = get_rd("rd%d" % rdhc) if rdhc else None
        src_d = get_rd("rd%d" % rdhd) if rdhd else None
        if src_c is not None and src_d is not None:
            # Determine size
            if ".ub" in mnemonic or ".sb" in mnemonic:
                N = 8
            elif ".uw" in mnemonic or ".sw" in mnemonic:
                N = 16
            elif ".ut" in mnemonic or ".st" in mnemonic:
                N = 32
            else:
                N = 64
            mask = (1 << N) - 1
            c = src_c & mask
            d = src_d & mask
            is_signed = mnemonic.split(".")[-1].startswith("s")
            is_sub = "sub" in mnemonic
            if is_signed:
                c = _sign_extend(c, N)
                d = _sign_extend(d, N)
                if is_sub:
                    result = c - d
                else:
                    result = c + d
                # Truncate to N bits then sign-extend to 64
                result_n = result & mask
                result = _sign_extend(result_n, N)
            else:
                if is_sub:
                    result = (c - d) & mask
                else:
                    result = (c + d) & mask
                # Zero-extend to 64
                result = result & mask
            if rdhb != 0:
                expected_rd["rd%d" % rdhb] = _hex64(result & 0xFFFFFFFFFFFFFFFF)

    # ── orrr mul/div/rem fixed-width (§3.1.5) ──────────────────────────
    elif fmt == "orrr" and any(mnemonic.startswith(p) for p in ("mul.", "div.", "rem.")) and \
            any(s in mnemonic for s in (".ub", ".sb", ".uw", ".sw", ".ut", ".st", ".uo", ".so")):
        rdhb = hb
        rdhc = hc
        rdhd = hd
        src_c = get_rd("rd%d" % rdhc) if rdhc else None
        src_d = get_rd("rd%d" % rdhd) if rdhd else None
        if src_c is not None and src_d is not None:
            # Determine size
            if ".ub" in mnemonic or ".sb" in mnemonic:
                N = 8
            elif ".uw" in mnemonic or ".sw" in mnemonic:
                N = 16
            elif ".ut" in mnemonic or ".st" in mnemonic:
                N = 32
            else:
                N = 64
            mask = (1 << N) - 1
            c = src_c & mask
            d = src_d & mask
            is_signed = mnemonic.split(".")[-1].startswith("s")
            if is_signed:
                c = _sign_extend(c, N)
                d = _sign_extend(d, N)
            op = mnemonic.split(".")[0]  # mul/div/rem
            if d == 0:
                # div by zero → ILLI, skip (handled by legality)
                pass
            elif is_signed and op == "div" and c == -(1 << (N - 1)) and d == -1:
                # overflow → ILLI
                pass
            else:
                if op == "mul":
                    result = c * d
                elif op == "div":
                    # truncate toward zero
                    if c >= 0 and d >= 0:
                        result = c // d
                    elif c < 0 and d < 0:
                        result = (-c) // (-d)
                    elif c < 0:
                        result = -((-c) // d)
                    else:
                        result = -(c // (-d))
                else:  # rem
                    # truncate toward zero, sign = dividend
                    if c >= 0 and d >= 0:
                        result = c % d
                    elif c < 0 and d < 0:
                        result = -((-c) % (-d))
                    elif c < 0:
                        result = -((-c) % d)
                    else:
                        result = c % (-d)
                # Truncate to N bits
                result_n = result & mask
                if is_signed:
                    result = _sign_extend(result_n, N)
                else:
                    result = result_n
                if rdhb != 0:
                    expected_rd["rd%d" % rdhb] = _hex64(result & 0xFFFFFFFFFFFFFFFF)

    # ── orrr cmp fixed-width (§3.2.2) ──────────────────────────────────
    elif fmt == "orrr" and mnemonic.startswith("cmp.") and insn != "cmp.uo-rb" and \
            any(s in mnemonic for s in (".ub", ".sb", ".uw", ".sw", ".ut", ".st", ".uo", ".so")):
        rdhb = hb
        rdhc = hc
        rdhd = hd
        src_c = get_rd("rd%d" % rdhc) if rdhc else None
        src_d = get_rd("rd%d" % rdhd) if rdhd else None
        if src_c is not None and src_d is not None:
            if ".ub" in mnemonic or ".sb" in mnemonic:
                N = 8
            elif ".uw" in mnemonic or ".sw" in mnemonic:
                N = 16
            elif ".ut" in mnemonic or ".st" in mnemonic:
                N = 32
            else:
                N = 64
            mask = (1 << N) - 1
            c = src_c & mask
            d = src_d & mask
            is_signed = mnemonic.split(".")[-1].startswith("s")
            if is_signed:
                c = _sign_extend(c, N)
                d = _sign_extend(d, N)
            if c < d:
                result = -1
            elif c == d:
                result = 0
            else:
                result = 1
            if rdhb != 0:
                expected_rd["rd%d" % rdhb] = _hex64(result & 0xFFFFFFFFFFFFFFFF)

    # ── orrr cmp.uo-rb (§4.6) ──────────────────────────────────────────
    elif fmt == "orrr" and insn == "cmp.uo-rb":
        rdhb = hb
        rbhc = hc
        rbhd = hd
        src_c = get_rb("rb%d" % rbhc) if rbhc else None
        src_d = get_rb("rb%d" % rbhd) if rbhd else None
        if src_c is not None and src_d is not None:
            # Compare full 64 bits unsigned
            c = src_c & 0xFFFFFFFFFFFFFFFF
            d = src_d & 0xFFFFFFFFFFFFFFFF
            if c < d:
                result = -1
            elif c == d:
                result = 0
            else:
                result = 1
            if rdhb != 0:
                expected_rd["rd%d" % rdhb] = _hex64(result & 0xFFFFFFFFFFFFFFFF)

    # ── orrr add.so-rb / sub.so-rb (§4.5.1) ────────────────────────────
    elif fmt == "orrr" and insn in ("add.so-rb", "sub.so-rb"):
        rbhb = hb
        rbhc = hc
        rdhd = hd
        src_c = get_rb("rb%d" % rbhc) if rbhc else None
        src_d = get_rd("rd%d" % rdhd) if rdhd else None
        if src_c is not None and src_d is not None:
            is_sub = "sub" in mnemonic
            if is_sub:
                result = (src_c - src_d) & 0xFFFFFFFFFFFFFFFF
            else:
                result = (src_c + src_d) & 0xFFFFFFFFFFFFFFFF
            expected_rb["rb%d" % rbhb] = _hex64(result)

    # ── orrr logic and/or/xor/xnor .b/.w/.t/.o (§3.3) ─────────────────
    elif fmt == "orrr" and any(mnemonic.startswith(p) for p in ("and.", "or.", "xor.", "xnor.")):
        rdhb = hb
        rdhc = hc
        rdhd = hd
        src_c = get_rd("rd%d" % rdhc) if rdhc else None
        src_d = get_rd("rd%d" % rdhd) if rdhd else None
        if src_c is not None and src_d is not None:
            if ".b" in mnemonic:
                N = 8
            elif ".w" in mnemonic:
                N = 16
            elif ".t" in mnemonic:
                N = 32
            else:
                N = 64
            mask = (1 << N) - 1
            c = src_c & mask
            d = src_d & mask
            if mnemonic.startswith("and."):
                result = c & d
            elif mnemonic.startswith("or."):
                result = c | d
            elif mnemonic.startswith("xor."):
                result = c ^ d
            else:  # xnor
                result = (~c ^ d) & mask  # Actually XNOR = NOT XOR
                # XNOR: same=1, diff=0 → ~(c^d) masked
                result = (~(c ^ d)) & mask
            # Only modify low N bits, keep upper bits from rdhb initial
            rdhb_val = get_rd("rd%d" % rdhb) if rdhb else None
            if rdhb_val is not None:
                if N < 64:
                    upper = rdhb_val & ~mask
                    result = upper | (result & mask)
                if rdhb != 0:
                    expected_rd["rd%d" % rdhb] = _hex64(result)

    # ── orrr/orri shift/extend (§3.4.1/§3.4.2) ────────────────────────
    elif (fmt in ("orrr", "orri")) and any(mnemonic.startswith(p) for p in ("shl.", "shr.", "ext.")):
        rdhb = hb
        rdhc = hc
        src_c = get_rd("rd%d" % rdhc) if rdhc else None

        # Determine shamt/ext_pos
        if fmt == "orrr":
            # shamt/ext_pos from rdhd register value
            rdhd_idx = hd
            shamt_val = get_rd("rd%d" % rdhd_idx) if rdhd_idx is not None else None
        else:  # orri
            shamt_val = _ef("immu6")  # orri uses immu6 field for shamt/ext_pos
            if shamt_val is None:
                shamt_val = hd  # fallback

        if src_c is not None and shamt_val is not None:
            # Determine N
            if ".ub" in mnemonic or ".sb" in mnemonic:
                N = 7
            elif ".uw" in mnemonic or ".sw" in mnemonic:
                N = 15
            elif ".ut" in mnemonic or ".st" in mnemonic:
                N = 31
            else:
                N = 63

            if mnemonic.startswith("ext."):
                # Extend: rdhb[hd:0] = rdhc[hd:0], rdhb[N:hd+1] = sign/zero_extend(rdhc[hd])
                hd_val = shamt_val & ((1 << (N.bit_length())) - 1)
                if hd_val > N:
                    pass  # ILLI, handled by legality
                else:
                    rdhb_val = get_rd("rd%d" % rdhb) if rdhb else 0
                    # Copy bits [hd:0] from src
                    low_mask = (1 << (hd_val + 1)) - 1
                    result = (src_c & low_mask) | (rdhb_val & ~low_mask)
                    # Extend bit hd to [N:hd+1]
                    extend_bit = (src_c >> hd_val) & 1
                    if ".s" in mnemonic and extend_bit:
                        # Sign extend: fill with 1s
                        ext_mask = ((1 << (N - hd_val)) - 1) << (hd_val + 1)
                        result = result | ext_mask
                    else:
                        # Zero extend: clear bits [N:hd+1]
                        ext_mask = ((1 << (N - hd_val)) - 1) << (hd_val + 1)
                        result = result & ~ext_mask
                    # Keep upper bits [63:N+1] unchanged
                    if N < 63:
                        upper_mask = ~((1 << (N + 1)) - 1)
                        result = (result & ((1 << (N + 1)) - 1)) | (rdhb_val & upper_mask)
                    if rdhb != 0:
                        expected_rd["rd%d" % rdhb] = _hex64(result)
            else:
                # Shift
                shamt = shamt_val & ((1 << (N.bit_length())) - 1)
                if shamt > N:
                    pass  # ILLI
                else:
                    rdhb_val = get_rd("rd%d" % rdhb) if rdhb else 0
                    low_mask = (1 << (N + 1)) - 1
                    c_low = src_c & low_mask
                    if mnemonic.startswith("shl."):
                        result_low = (c_low << shamt) & low_mask
                    elif "u" in mnemonic.split(".")[-1]:
                        # Logical right shift
                        result_low = (c_low >> shamt) & low_mask
                    else:
                        # Arithmetic right shift
                        c_signed = _sign_extend(c_low, N + 1)
                        result = c_signed >> shamt
                        result_low = result & low_mask
                    # Keep upper bits [63:N+1] unchanged
                    if N < 63:
                        upper_mask = ~((1 << (N + 1)) - 1)
                        result = result_low | (rdhb_val & upper_mask)
                    else:
                        result = result_low
                    if rdhb != 0:
                        expected_rd["rd%d" % rdhb] = _hex64(result)

    # ── riii add.si / rela.si (§3.1.3/§4.7) ───────────────────────────
    elif fmt == "riii" and insn in ("add.si-rd", "add.si-rb", "rela.si-rb"):
        # ha = dest register
        # immediate: hb[5:0] + hc[5:0] + hd[5:0] = 18 bits signed
        imm18_raw = ((word >> 12) & 0x3F) << 12 | ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm18 = _sign_extend(imm18_raw, 18)

        if insn == "add.si-rd":
            rdha = ha
            src_a = get_rd("rd%d" % rdha) if rdha else None
            if src_a is not None:
                result = (src_a + imm18) & 0xFFFFFFFFFFFFFFFF
                if rdha != 0:
                    expected_rd["rd%d" % rdha] = _hex64(result)
        elif insn == "add.si-rb":
            rbha = ha
            src_a = get_rb("rb%d" % rbha) if rbha else None
            if src_a is not None:
                result = (src_a + imm18) & 0xFFFFFFFFFFFFFFFF
                expected_rb["rb%d" % rbha] = _hex64(result)
        elif insn == "rela.si-rb":
            rbha = ha
            src_a = get_rb("rb%d" % rbha) if rbha else None
            if src_a is not None:
                # rela.si: rbha = rb0 + (imms18 << 12)
                # PC = rb0 (current instruction address)
                shifted = imm18 << 12
                result = (RB0_PC + shifted) & 0xFFFFFFFFFFFFFFFF
                expected_rb["rb%d" % rbha] = _hex64(result)

    # ── rrii cmp.ui/cmp.si (§3.2.1) ────────────────────────────────────
    elif fmt == "rrii" and insn in ("cmp.ui-rd", "cmp.si-rd"):
        rdha = ha
        rdhb = hb
        # immediate: hc[5:0] + hd[5:0] = 12 bits
        imm12_raw = ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        if insn == "cmp.ui-rd":
            imm12 = imm12_raw & 0xFFF  # zero-extend
        else:
            imm12 = _sign_extend(imm12_raw, 12)
        src_b = get_rd("rd%d" % rdhb) if rdhb else None
        if src_b is not None:
            c = src_b & 0xFFFFFFFFFFFFFFFF
            d = imm12 & 0xFFFFFFFFFFFFFFFF
            if insn == "cmp.si-rd":
                c = _sign_extend(src_b, 64)
                d = _sign_extend(imm12 & 0xFFFFFFFFFFFFFFFF, 64)
            if c < d:
                result = -1
            elif c == d:
                result = 0
            else:
                result = 1
            if rdha != 0:
                expected_rd["rd%d" % rdha] = _hex64(result & 0xFFFFFFFFFFFFFFFF)

    # ── rrrr cs.n/z/p (§3.5) ───────────────────────────────────────────
    elif fmt == "rrrr" and mnemonic.startswith("cs."):
        rdha = ha
        rdhb = hb
        rdhc = hc
        rdhd = hd
        src_a = get_rd("rd%d" % rdha) if rdha else None
        if src_a is not None:
            src_a_signed = _sign_extend(src_a, 64)
            if insn in ("cs.n-rd",):
                cond = src_a_signed < 0
            elif insn in ("cs.z-rd",):
                cond = src_a == 0
            elif insn in ("cs.p-rd",):
                cond = src_a_signed > 0
            elif insn in ("cs.eq-rd",):
                src_b = get_rd("rd%d" % rdhb) if rdhb else None
                cond = (src_a == src_b) if src_b is not None else False
            elif insn in ("cs.ne-rd",):
                src_b = get_rd("rd%d" % rdhb) if rdhb else None
                cond = (src_a != src_b) if src_b is not None else False
            else:
                cond = False

            if insn in ("cs.n-rd", "cs.z-rd", "cs.p-rd"):
                if cond:
                    val = get_rd("rd%d" % rdhc) if rdhc else None
                else:
                    val = get_rd("rd%d" % rdhd) if rdhd else None
                if val is not None and rdhb != 0:
                    expected_rd["rd%d" % rdhb] = _hex64(val)
            elif insn in ("cs.eq-rd", "cs.ne-rd"):
                if cond:
                    val = get_rd("rd%d" % rdhd) if rdhd else None
                    if val is not None and rdhc != 0:
                        expected_rd["rd%d" % rdhc] = _hex64(val)

    # ── rwii set.zw/set.ow/or.w/andn.w (§3.6) ─────────────────────────
    elif fmt == "rwii":
        dst_idx = ha
        # wyde position: wpN = hb[5:4] = word[17:16]
        wp = (word >> 16) & 0x3
        # immu16: hb[3:0] (high 4) + hc[5:0] (mid 6) + hd[5:0] (low 6)
        # immu16_hi = word[15:12], immu16_mid = word[11:6], immu16_lo = word[5:0]
        immu16 = ((word >> 12) & 0xF) << 12 | ((word >> 6) & 0x3F) << 6 | (word & 0x3F)

        # Determine destination bank from insn suffix
        is_rb = insn.endswith("-rb")
        if is_rb:
            src_a = get_rb("rb%d" % dst_idx) if dst_idx else None
        else:
            src_a = get_rd("rd%d" % dst_idx) if dst_idx else None
        if src_a is not None:
            wyde_shift = wp * 16
            wyde_mask = 0xFFFF << wyde_shift

            if mnemonic.startswith("set.zw"):
                result = (immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF
            elif mnemonic.startswith("set.ow"):
                result = (immu16 << wyde_shift) | ~wyde_mask & 0xFFFFFFFFFFFFFFFF
            elif mnemonic.startswith("or.w"):
                result = src_a | ((immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF)
            elif mnemonic.startswith("andn.w"):
                result = src_a & ~((immu16 << wyde_shift) & 0xFFFFFFFFFFFFFFFF)
            else:
                result = src_a

            if is_rb:
                if dst_idx != 0:
                    expected_rb["rb%d" % dst_idx] = _hex64(result)
            else:
                if dst_idx != 0:
                    expected_rd["rd%d" % dst_idx] = _hex64(result)

    # ── rrii ld/st single (§4.1.1) ─────────────────────────────────────
    elif fmt == "rrii" and any(insn.startswith(p) for p in ("ld.", "st.")) and \
            "-rd" in insn:
        rdha = ha
        rbhb = hb
        # imms12: hc[5:0] + hd[5:0] = 12 bits signed
        imm12_raw = ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm12 = _sign_extend(imm12_raw, 12)
        base = get_rb("rb%d" % rbhb) if rbhb else None
        if base is not None:
            addr = (base + imm12) & 0xFFFFFFFFFFFFFFFF
            # For semantic cases, we need memory content from input_state
            mem = case.get("input_state", {}).get("memory", [])
            mem_val = None
            for m in (mem if isinstance(mem, list) else []):
                if isinstance(m, dict):
                    maddr = m.get("address")
                    if maddr and int(maddr, 16) == addr:
                        mval = m.get("value")
                        if mval:
                            mem_val = _to_int(mval)
                        break

            if insn.startswith("ld."):
                if mem_val is not None:
                    if ".sb" in insn:
                        val = _sign_extend(mem_val & 0xFF, 8)
                    elif ".ub" in insn:
                        val = mem_val & 0xFF
                    elif ".sw" in insn:
                        val = _sign_extend(mem_val & 0xFFFF, 16)
                    elif ".uw" in insn:
                        val = mem_val & 0xFFFF
                    elif ".st" in insn:
                        val = _sign_extend(mem_val & 0xFFFFFFFF, 32)
                    elif ".ut" in insn:
                        val = mem_val & 0xFFFFFFFF
                    else:  # .o
                        val = mem_val & 0xFFFFFFFFFFFFFFFF
                    if rdha != 0:
                        expected_rd["rd%d" % rdha] = _hex64(val)
            else:  # store
                src_a = get_rd("rd%d" % rdha) if rdha else None
                if src_a is not None:
                    # Store: memory value should match
                    if ".b" in insn:
                        expected_memory = [{"address": _hex64(addr).replace("0x", "0x").lower(),
                                           "value": _hex64(src_a & 0xFF)}]
                    elif ".w" in insn:
                        expected_memory = [{"address": _hex64(addr).replace("0x", "0x").lower(),
                                           "value": _hex64(src_a & 0xFFFF)}]
                    elif ".t" in insn:
                        expected_memory = [{"address": _hex64(addr).replace("0x", "0x").lower(),
                                           "value": _hex64(src_a & 0xFFFFFFFF)}]
                    else:  # .o
                        expected_memory = [{"address": _hex64(addr).replace("0x", "0x").lower(),
                                           "value": _hex64(src_a)}]

    # ── riii br.* (§5.2) ──────────────────────────────────────────────
    elif fmt == "riii" and insn.startswith("br."):
        # Condition check
        rdha = ha
        imm18_raw = ((word >> 12) & 0x3F) << 12 | ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm18 = _sign_extend(imm18_raw, 18)

        # Determine source register based on -rb/-rd variant
        if insn in ("br.z-rb", "br.nz-rb"):
            rbha = ha
            src_a = get_rb("rb%d" % rbha) if rbha else None
            if src_a is None and rbha is not None:
                src_a = 0  # unset register defaults to 0
            if src_a is not None:
                cond_map = {
                    "br.z-rb": src_a == 0,
                    "br.nz-rb": src_a != 0,
                }
                cond = cond_map.get(insn, False)
            else:
                cond = False
        else:
            src_a = get_rd("rd%d" % rdha) if rdha else None
            if src_a is None and rdha is not None:
                src_a = 0  # unset register defaults to 0
            if src_a is not None:
                src_a_signed = _sign_extend(src_a, 64)
                cond_map = {
                    "br.n": src_a_signed < 0,
                    "br.nn": src_a_signed >= 0,
                    "br.z": src_a == 0,
                    "br.nz": src_a != 0,
                    "br.p": src_a_signed > 0,
                    "br.np": src_a_signed <= 0,
                }
                cond = cond_map.get(insn.split("-")[0], False)
            else:
                cond = False

        if cond:
            # Taken: PC = rb0 + (imm18 << 2)
            expected_pc = _hex64(RB0_PC + (imm18 << 2))
        else:
            # Not taken: PC = rb0 + 4
            expected_pc = _hex64(RB0_PC + 4)

    # ── rrii br.eq/br.ne (§5.2.1) ──────────────────────────────────────
    elif fmt == "rrii" and insn.startswith("br."):
        rdha = ha
        rdhb = hb
        imm12_raw = ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm12 = _sign_extend(imm12_raw, 12)
        src_a = get_rd("rd%d" % rdha) if rdha else None
        if src_a is None and rdha is not None:
            src_a = 0
        src_b = get_rd("rd%d" % rdhb) if rdhb else None
        if src_b is None and rdhb is not None:
            src_b = 0
        if src_a is not None and src_b is not None:
            if insn == "br.eq-rd":
                cond = (src_a == src_b)
            else:
                cond = (src_a != src_b)
            if cond:
                expected_pc = _hex64(RB0_PC + (imm12 << 2))
            else:
                expected_pc = _hex64(RB0_PC + 4)

    # ── iiii jump (§5.3) ───────────────────────────────────────────────
    elif fmt == "iiii" and insn == "jump-iiii":
        imm24_raw = word & 0xFFFFFF
        imm24 = _sign_extend(imm24_raw, 24)
        expected_pc = _hex64(RB0_PC + (imm24 << 2))

    # ── rrii jump (§5.3) ───────────────────────────────────────────────
    elif fmt == "rrii" and insn == "jump-rrii":
        rbha = ha
        rdhb = hb
        imm12_raw = ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm12 = _sign_extend(imm12_raw, 12)
        base = get_rb("rb%d" % rbha) if rbha is not None else None
        offset = get_rd("rd%d" % rdhb) if rdhb is not None else None
        if base is not None and offset is not None:
            expected_pc = _hex64((base + offset + (imm12 << 2)) & 0xFFFFFFFFFFFFFFFF)

    # ── iiii call (§5.4) ───────────────────────────────────────────────
    elif fmt == "iiii" and insn == "call-iiii":
        imm24_raw = word & 0xFFFFFF
        imm24 = _sign_extend(imm24_raw, 24)
        expected_pc = _hex64(RB0_PC + (imm24 << 2))
        # RA push (§5.6.1)
        return_addr = RB0_PC + 4
        _do_ra_push(inp_ra, expected_ra, return_addr)

    # ── rrii call (§5.4) ───────────────────────────────────────────────
    elif fmt == "rrii" and insn == "call-rrii":
        rbha = ha
        rdhb = hb
        imm12_raw = ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm12 = _sign_extend(imm12_raw, 12)
        base = get_rb("rb%d" % rbha) if rbha is not None else None
        offset = get_rd("rd%d" % rdhb) if rdhb is not None else None
        if base is not None and offset is not None:
            expected_pc = _hex64((base + offset + (imm12 << 2)) & 0xFFFFFFFFFFFFFFFF)
            # RA push (§5.6.1)
            return_addr = RB0_PC + 4
            _do_ra_push(inp_ra, expected_ra, return_addr)

    # ── riii ret (§5.5) ────────────────────────────────────────────────
    elif fmt == "riii" and insn == "ret-riii":
        # ret: PC = ra63 low 48 bits
        ra63 = get_ra("ra63")
        if ra63 is not None:
            expected_pc = _hex64(ra63 & 0xFFFFFFFFFFFF)
            # rdha = sign_extend(imms18)
            rdha_idx = ha
            if rdha_idx is not None:
                imm18_raw = ((word >> 12) & 0x3F) << 12 | ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
                imm18 = _sign_extend(imm18_raw, 18)
                if rdha_idx != 0:
                    expected_rd["rd%d" % rdha_idx] = _hex64(imm18 & 0xFFFFFFFFFFFFFFFF)

    # ── orri block assignment rd2rd/rd2ra/ra2rd/rb2rb/rd2rb/rb2rd (§3.7/§4.3/§4.9.3) ──
    elif fmt == "orri" and insn in ("rd2rd", "rd2ra", "ra2rd", "rb2rb", "rd2rb", "rb2rd"):
        # Block assignment: copy immu6 registers from src to dst
        # Sequential semantics (contract-isa.md:467): ascending order,
        # each pair read-then-write. Overlapping writes are visible to
        # later reads.
        dst_idx = hb  # bits[17:12]
        src_idx = hc  # bits[11:6]
        immu6 = extract_field(word, fields, "immu6")
        if dst_idx is not None and src_idx is not None and immu6 is not None and immu6 > 0:
            bank_map = {
                "rd2rd": ("rd", "rd"),
                "rd2ra": ("rd", "ra"),
                "ra2rd": ("ra", "rd"),
                "rb2rb": ("rb", "rb"),
                "rd2rb": ("rd", "rb"),
                "rb2rd": ("rb", "rd"),
            }
            src_bank, dst_bank = bank_map[insn]
            # Sequential: read-then-write per pair in ascending order.
            # Track writes so overlapping reads see updated values.
            for i in range(immu6):
                # Read source: check expected (already written) first,
                # then fall back to input_state.
                src_name = "%s%d" % (src_bank, src_idx + i)
                if src_bank == "rd":
                    src_val = expected_rd.get(src_name)
                elif src_bank == "rb":
                    src_val = expected_rb.get(src_name)
                elif src_bank == "ra":
                    src_val = expected_ra.get(src_name)
                else:
                    src_val = None
                if src_val is None:
                    src_val = get_reg(src_bank, src_idx + i)
                if src_val is None:
                    break
                src_val = _to_int(src_val)
                dst_name = "%s%d" % (dst_bank, dst_idx + i)
                if dst_bank == "rd":
                    if dst_idx + i != 0:
                        expected_rd[dst_name] = _hex64(src_val)
                elif dst_bank == "rb":
                    if dst_idx + i != 0:
                        expected_rb[dst_name] = _hex64(src_val)
                elif dst_bank == "ra":
                    expected_ra[dst_name] = _hex64(src_val)

    # ── rrii ld.o/st.o-rb (§4.2) ──────────────────────────────────────
    elif fmt == "rrii" and insn in ("ld.o-rb", "st.o-rb"):
        rbha = ha
        rbhb = hb
        imm12_raw = ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm12 = _sign_extend(imm12_raw, 12)
        base = get_rb("rb%d" % rbhb) if rbhb else None
        if base is not None:
            addr = (base + imm12) & 0xFFFFFFFFFFFFFFFF
            if insn == "ld.o-rb":
                mem = case.get("input_state", {}).get("memory", [])
                for m in (mem if isinstance(mem, list) else []):
                    if isinstance(m, dict):
                        maddr = m.get("address")
                        if maddr and int(maddr, 16) == addr:
                            mval = m.get("value")
                            if mval:
                                expected_rb["rb%d" % rbha] = _hex64(_to_int(mval))
                            break
            else:  # st.o-rb
                src_a = get_rb("rb%d" % rbha) if rbha else None
                if src_a is not None:
                    expected_memory = [{"address": _hex64(addr).lower(),
                                       "value": _hex64(src_a)}]

    # ── rrii ld.o/st.o-ra (§4.9.1) ────────────────────────────────────
    elif fmt == "rrii" and insn in ("ld.o-ra", "st.o-ra"):
        raha = ha
        rbhb = hb
        imm12_raw = ((word >> 6) & 0x3F) << 6 | (word & 0x3F)
        imm12 = _sign_extend(imm12_raw, 12)
        base = get_rb("rb%d" % rbhb) if rbhb else None
        if base is not None:
            addr = (base + imm12) & 0xFFFFFFFFFFFFFFFF
            if insn == "ld.o-ra":
                mem = case.get("input_state", {}).get("memory", [])
                for m in (mem if isinstance(mem, list) else []):
                    if isinstance(m, dict):
                        maddr = m.get("address")
                        if maddr and int(maddr, 16) == addr:
                            mval = m.get("value")
                            if mval:
                                expected_ra["ra%d" % raha] = _hex64(_to_int(mval))
                            break
            else:  # st.o-ra
                src_a = get_ra("ra%d" % raha) if raha else None
                if src_a is not None:
                    expected_memory = [{"address": _hex64(addr).lower(),
                                       "value": _hex64(src_a)}]

    # ── rrri ldm/stm (§4.1.2) ──────────────────────────────────────────
    elif fmt == "rrri" and any(insn.startswith(p) for p in ("ldm.", "stm.")):
        rdha = ha
        rbhb = hb
        rdhc = hc
        immu6 = extract_field(word, fields, "immu6")
        base_val = get_rb("rb%d" % rbhb) if rbhb else None
        offset_val = get_rd("rd%d" % rdhc) if rdhc else None
        if base_val is not None and offset_val is not None and immu6 and immu6 > 0:
            addr_base = (base_val + offset_val) & 0xFFFFFFFFFFFFFFFF

            # Determine destination bank from insn suffix
            if "-ra" in insn:
                dst_bank = "ra"
            elif "-rb" in insn:
                dst_bank = "rb"
            else:
                dst_bank = "rd"

            if insn.startswith("ldm."):
                # Load multiple: read from memory, write to registers
                mem = case.get("input_state", {}).get("memory", [])
                for i in range(immu6):
                    addr_i = (addr_base + i * 8) & 0xFFFFFFFFFFFFFFFF
                    mem_val = None
                    for m in (mem if isinstance(mem, list) else []):
                        if isinstance(m, dict):
                            maddr = m.get("address")
                            if maddr and int(maddr, 16) == addr_i:
                                mval = m.get("value")
                                if mval:
                                    mem_val = _to_int(mval)
                                break
                    if mem_val is not None:
                        dst_idx = rdha + i
                        if ".sb" in insn:
                            val = _sign_extend(mem_val & 0xFF, 8)
                        elif ".ub" in insn:
                            val = mem_val & 0xFF
                        elif ".sw" in insn:
                            val = _sign_extend(mem_val & 0xFFFF, 16)
                        elif ".uw" in insn:
                            val = mem_val & 0xFFFF
                        elif ".st" in insn:
                            val = _sign_extend(mem_val & 0xFFFFFFFF, 32)
                        elif ".ut" in insn:
                            val = mem_val & 0xFFFFFFFF
                        else:  # .o
                            val = mem_val & 0xFFFFFFFFFFFFFFFF
                        dst_name = "%s%d" % (dst_bank, dst_idx)
                        if dst_bank == "rd":
                            if dst_idx != 0:
                                expected_rd[dst_name] = _hex64(val)
                        elif dst_bank == "rb":
                            if dst_idx != 0:
                                expected_rb[dst_name] = _hex64(val)
                        elif dst_bank == "ra":
                            expected_ra[dst_name] = _hex64(val)
                    else:
                        break  # memory content not available
            else:
                # Store multiple: read registers, write to memory
                src_vals = []
                all_available = True
                for i in range(immu6):
                    src_idx = rdha + i
                    v = get_reg(dst_bank, src_idx)
                    if v is None:
                        all_available = False
                        break
                    src_vals.append(v)
                if all_available:
                    expected_memory = []
                    for i, sv in enumerate(src_vals):
                        addr_i = (addr_base + i * 8) & 0xFFFFFFFFFFFFFFFF
                        if ".b" in insn:
                            expected_memory.append({"address": _hex64(addr_i).lower(),
                                                    "value": _hex64(sv & 0xFF)})
                        elif ".w" in insn:
                            expected_memory.append({"address": _hex64(addr_i).lower(),
                                                    "value": _hex64(sv & 0xFFFF)})
                        elif ".t" in insn:
                            expected_memory.append({"address": _hex64(addr_i).lower(),
                                                    "value": _hex64(sv & 0xFFFFFFFF)})
                        else:  # .o
                            expected_memory.append({"address": _hex64(addr_i).lower(),
                                                    "value": _hex64(sv)})

    return expected_rd, expected_rb, expected_ra, expected_memory, expected_pc, mismatches


# ---------------------------------------------------------------------------
# Compare expected vs actual
# ---------------------------------------------------------------------------

def compare_states(expected, actual, label):
    """Compare expected dict vs actual dict, return mismatches."""
    mismatches = []
    if expected is None or actual is None:
        return mismatches
    if not isinstance(actual, dict):
        return mismatches
    for key, exp_val in expected.items():
        act_val = actual.get(key)
        if act_val is None:
            mismatches.append("%s: missing %s (expected %s)" % (label, key, exp_val))
        elif _to_int(act_val) != _to_int(exp_val):
            mismatches.append("%s: %s mismatch: expected %s, got %s"
                              % (label, key, exp_val, act_val))
    return mismatches


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def audit_file(filepath, by_key, verbose=False):
    """Audit a single YAML file, return (file_stats, mismatches)."""
    fname = os.path.basename(filepath)
    try:
        with open(filepath) as fh:
            cases = _yaml.safe_load(fh)
    except Exception as e:
        return {"file": fname, "error": str(e)}, []

    if not cases or not isinstance(cases, list):
        return {"file": fname, "total": 0}, []

    stats = {
        "file": fname,
        "total": len(cases),
        "active": 0,
        "deferred": 0,
        "sbo_active": 0,   # active semantic/boundary/overlap cases
        "recomputed": 0,   # cases where expected values were produced
        "by_class": defaultdict(int),
        "by_insn": defaultdict(int),
    }
    all_mismatches = []

    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            continue
        enc = case.get("encoding")
        if isinstance(enc, dict) and enc.get("reserved"):
            continue  # Skip reserved
        status = case.get("status", "active")
        cls = case.get("class", "")
        insn = case.get("insn", "")
        mnemonic = case.get("mnemonic", "")
        fmt = case.get("format", "")

        stats["by_class"][cls] += 1
        stats["by_insn"][insn] += 1
        if status == "active":
            stats["active"] += 1
        else:
            stats["deferred"] += 1

        # Only audit active semantic/boundary/overlap without fault
        if status != "active" or cls not in ("semantic", "boundary", "overlap"):
            continue
        if case.get("expected_fault"):
            continue
        if case.get("deferred_reason"):
            continue

        stats["sbo_active"] += 1

        # Get encoding word
        word = None
        fields = []
        if isinstance(enc, dict) and "word" in enc:
            word = _to_int(enc["word"])
        key = (insn, fmt)
        if key in by_key:
            fields = by_key[key].get("fields", [])

        if word is None:
            continue

        tag = "%s case[%d] %s" % (fname, i, mnemonic)

        # Recompute
        exp_rd, exp_rb, exp_ra, exp_mem, exp_pc, mismatches = \
            recompute_expected(case, word, fields, by_key, verbose)

        # Track if any expected values were produced
        has_exp = False
        for v in (exp_rd, exp_rb, exp_ra, exp_mem, exp_pc):
            if v is not None:
                if isinstance(v, dict) and len(v) > 0:
                    has_exp = True
                    break
                elif not isinstance(v, dict):
                    has_exp = True
                    break
        if has_exp:
            stats["recomputed"] += 1
        else:
            stats.setdefault("skipped_list", []).append(
                "%s[%d] %s %s %s" % (fname, i, insn, mnemonic, fmt))

        # Compare
        actual_state = case.get("expected_state", {}) or {}
        if isinstance(actual_state, dict):
            actual_rd = actual_state.get("rd", {})
            actual_rb = actual_state.get("rb", {})
            actual_ra = actual_state.get("ra", {})

            mismatches.extend(compare_states(exp_rd, actual_rd, tag + " rd"))
            mismatches.extend(compare_states(exp_rb, actual_rb, tag + " rb"))
            mismatches.extend(compare_states(exp_ra, actual_ra, tag + " ra"))

            # Compare memory (for store instructions)
            if exp_mem is not None and isinstance(exp_mem, list) and len(exp_mem) > 0:
                actual_mem = actual_state.get("memory", [])
                if isinstance(actual_mem, list):
                    for exp_m in exp_mem:
                        if isinstance(exp_m, dict):
                            exp_addr = exp_m.get("address")
                            exp_val = exp_m.get("value")
                            found = False
                            for act_m in actual_mem:
                                if isinstance(act_m, dict):
                                    act_addr = act_m.get("address")
                                    act_val = act_m.get("value")
                                    if act_addr and exp_addr and int(act_addr, 16) == int(exp_addr, 16):
                                        found = True
                                        if act_val and exp_val and _to_int(act_val) != _to_int(exp_val):
                                            mismatches.append("%s: memory[%s] mismatch: expected %s, got %s"
                                                              % (tag, exp_addr, exp_val, act_val))
                                        break
                            if not found and exp_addr:
                                mismatches.append("%s: memory[%s] missing (expected %s)"
                                                  % (tag, exp_addr, exp_val))

        # Compare expected_pc
        actual_pc = case.get("expected_pc")
        if exp_pc is not None and actual_pc is not None:
            if _to_int(exp_pc) != _to_int(actual_pc):
                mismatches.append("%s: expected_pc mismatch: expected %s, got %s"
                                  % (tag, exp_pc, actual_pc))

        all_mismatches.extend(mismatches)

    return stats, all_mismatches


def main():
    parser = argparse.ArgumentParser(description="ISA 向量全量再审计")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

    opcodes_path = os.path.join(repo_dir, "contracts", "opcodes.yaml")
    if not os.path.exists(opcodes_path):
        print("ERROR: contracts/opcodes.yaml not found", file=sys.stderr)
        sys.exit(1)

    all_records, by_key = load_opcodes(opcodes_path)

    isa_dir = os.path.join(repo_dir, "tests", "vectors", "isa")
    yaml_files = sorted(glob.glob(os.path.join(isa_dir, "*.yaml")))

    print("=" * 70)
    print("ISA 向量全量再审计 — 重推导比对")
    print("=" * 70)

    total_cases = 0
    total_active = 0
    total_deferred = 0
    total_sbo_active = 0
    total_recomputed = 0
    total_mismatches = []
    all_stats = []

    for fpath in yaml_files:
        stats, mismatches = audit_file(fpath, by_key, args.verbose)
        all_stats.append(stats)
        total_cases += stats.get("total", 0)
        total_active += stats.get("active", 0)
        total_deferred += stats.get("deferred", 0)
        total_sbo_active += stats.get("sbo_active", 0)
        total_recomputed += stats.get("recomputed", 0)
        total_mismatches.extend(mismatches)

        fname = stats.get("file", "?")
        print("\n--- %s ---" % fname)
        print("  Total: %d, Active: %d, Deferred: %d" % (
            stats.get("total", 0), stats.get("active", 0), stats.get("deferred", 0)))
        print("  SBO active: %d, Recomputed: %d" % (
            stats.get("sbo_active", 0), stats.get("recomputed", 0)))
        if stats.get("by_class"):
            for cls in ("encoding", "legality", "semantic", "boundary", "overlap"):
                cnt = stats["by_class"].get(cls, 0)
                if cnt:
                    print("  %s: %d" % (cls, cnt))
        if mismatches:
            for m in mismatches:
                print("  MISMATCH: %s" % m)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("Files: %d" % len(yaml_files))
    print("Total cases: %d (active: %d, deferred: %d)" % (
        total_cases, total_active, total_deferred))
    total_skipped = total_sbo_active - total_recomputed
    print("Active semantic/boundary/overlap: %d (recomputed: %d, skipped: %d)" % (
        total_sbo_active, total_recomputed, total_skipped))
    print("Mismatches: %d" % len(total_mismatches))

    # Collect all skipped cases from all files
    all_skipped = []
    for s in all_stats:
        all_skipped.extend(s.get("skipped_list", []))

    if all_skipped:
        print("\nSKIPPED CASES (no expected values produced — nop/inherent):")
        for sk in all_skipped:
            print("  - %s" % sk)

    if total_mismatches:
        print("\nALL MISMATCHES:")
        for m in total_mismatches:
            print("  - %s" % m)
        sys.exit(1)
    else:
        print("\nRecomputed %d/%d active semantic/boundary/overlap cases: 0 mismatches." % (
            total_recomputed, total_sbo_active))
        sys.exit(0)


if __name__ == "__main__":
    main()
