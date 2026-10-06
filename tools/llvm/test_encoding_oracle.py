#!/usr/bin/env python3
"""
Independent encoding oracle for DADAO M1 instructions.
Verifies that llvm-mc produces correct encodings by independent calculation.
Covers all 9 formats and branch instructions.

B5 fix: Uses proper .text section parsing instead of searching the whole ELF.
"""
import subprocess
import sys
import struct
import glob
import os
import tempfile

def encode_rrrr(op, ra, rb, rc, rd):
    """Encode rrrr format: op[31:24] ra[23:18] rb[17:12] rc[11:6] rd[5:0]"""
    return (op << 24) | (ra << 18) | (rb << 12) | (rc << 6) | rd

def encode_rrri(op, ra, rb, rc, imm6):
    """Encode rrri format: op[31:24] ra[23:18] rb[17:12] rc[11:6] imm6[5:0]"""
    return (op << 24) | (ra << 18) | (rb << 12) | (rc << 6) | (imm6 & 0x3F)

def encode_rrii(op, ra, rb, imm12):
    """Encode rrii format: op[31:24] ra[23:18] rb[17:12] imm12[11:0]"""
    return (op << 24) | (ra << 18) | (rb << 12) | (imm12 & 0xFFF)

def encode_riii(op, ra, imm18):
    """Encode riii format: op[31:24] ra[23:18] imm18[17:0]"""
    return (op << 24) | (ra << 18) | (imm18 & 0x3FFFF)

def encode_iiii(op, imm24):
    """Encode iiii format: op[31:24] imm24[23:0]"""
    return (op << 24) | (imm24 & 0xFFFFFF)

def encode_rwii(op, ra, wp, imm16):
    """Encode rwii format: op[31:24] ra[23:18] wp[17:16] imm16[15:0]"""
    return (op << 24) | (ra << 18) | ((wp & 3) << 16) | (imm16 & 0xFFFF)

def encode_orrr(op, ha, rb, rc, rd):
    """Encode orrr format: op[31:24] ha[23:18] rb[17:12] rc[11:6] rd[5:0]"""
    return (op << 24) | (ha << 18) | (rb << 12) | (rc << 6) | rd

def encode_orri(op, ha, rb, rc, imm6):
    """Encode orri format: op[31:24] ha[23:18] rb[17:12] rc[11:6] imm6[5:0]"""
    return (op << 24) | (ha << 18) | (rb << 12) | (rc << 6) | (imm6 & 0x3F)

def encode_oiii(op, ha, imm18):
    """Encode oiii format: op[31:24] ha[23:18] imm18[17:0]"""
    return (op << 24) | (ha << 18) | (imm18 & 0x3FFFF)

# Register encodings
REG = {
    'rd0': 0, 'rd8': 8, 'rd16': 16, 'rd24': 24, 'rd32': 32, 'rd40': 40, 'rd48': 48, 'rd56': 56, 'rd63': 63,
    'rb0': 0, 'rb1': 1, 'rb8': 8, 'rb16': 16, 'rb24': 24, 'rb32': 32, 'rb40': 40, 'rb48': 48, 'rb56': 56, 'rb63': 63,
    'ra0': 0, 'ra8': 8, 'ra16': 16, 'ra24': 24, 'ra32': 32, 'ra40': 40, 'ra48': 48, 'ra56': 56, 'ra63': 63,
    'rf0': 0, 'rf4': 4, 'rf6': 6, 'rf8': 8, 'rf10': 10, 'rf12': 12, 'rf14': 14, 'rf16': 16,
    'rf18': 18, 'rf20': 20, 'rf63': 63,
}

# Test cases: (assembly, expected_encoding)
TESTS = [
    # rrrr format: add.uo {rd8, rd0}, rd0, rd0
    ("add.uo {rd8, rd0}, rd0, rd0", encode_rrrr(0x50, 8, 0, 0, 0)),
    # rrrr format: add.so {rd8, rd0}, rd0, rd0
    ("add.so {rd8, rd0}, rd0, rd0", encode_rrrr(0x51, 8, 0, 0, 0)),
    
    # rrri format: ldm.ub {rd8}, [rb1, rd0]
    ("ldm.ub {rd8}, [rb1, rd0]", encode_rrri(0x28, 8, 1, 0, 1)),
    
    # rrii format: ld.ub rd8, [rb1, 1]
    ("ld.ub rd8, [rb1, 1]", encode_rrii(0x10, 8, 1, 1)),
    # rrii format: st.b rd0, [rb1, 1]
    ("st.b rd0, [rb1, 1]", encode_rrii(0x18, 0, 1, 1)),
    # rrii format: cmp.ui rd8, rd0, 1
    ("cmp.ui rd8, rd0, 1", encode_rrii(0x5C, 8, 0, 1)),
    # rrii format: cmp.si rd8, rd0, 1
    ("cmp.si rd8, rd0, 1", encode_rrii(0x5D, 8, 0, 1)),
    
    # riii format: add.si rd8, 1
    ("add.si rd8, 1", encode_riii(0x59, 8, 1)),
    # riii format: add.si rb1, 1
    ("add.si rb1, 1", encode_riii(0x5B, 1, 1)),
    # riii format: br.n {rd0}?, [rb0, 4] (4 bytes >> 2 = 1)
    ("br.n {rd0}?, [rb0, 4]", encode_riii(0x68, 0, 1)),
    # riii format: br.nn {rd0}?, [rb0, 4] (4 bytes >> 2 = 1)
    ("br.nn {rd0}?, [rb0, 4]", encode_riii(0x69, 0, 1)),
    # riii format: br.z {rd0}?, [rb0, 4] (4 bytes >> 2 = 1)
    ("br.z {rd0}?, [rb0, 4]", encode_riii(0x6A, 0, 1)),
    # riii format: br.nz {rd0}?, [rb0, 4] (4 bytes >> 2 = 1)
    ("br.nz {rd0}?, [rb0, 4]", encode_riii(0x6B, 0, 1)),
    # riii format: br.p {rd0}?, [rb0, 4] (4 bytes >> 2 = 1)
    ("br.p {rd0}?, [rb0, 4]", encode_riii(0x6C, 0, 1)),
    # riii format: br.np {rd0}?, [rb0, 4] (4 bytes >> 2 = 1)
    ("br.np {rd0}?, [rb0, 4]", encode_riii(0x6D, 0, 1)),
    # riii format: ret rd0, 0
    ("ret rd0, 0", encode_riii(0x76, 0, 0)),
    
    # iiii format: call [rb0, 4] (4 bytes >> 2 = 1)
    ("call [rb0, 4]", encode_iiii(0x74, 1)),
    # iiii format: jump [rb0, 4] (4 bytes >> 2 = 1)
    ("jump [rb0, 4]", encode_iiii(0x70, 1)),
    # oiii format: swym 0 (op=0x77, ha=0x22)
    ("swym 0", encode_oiii(0x77, 0x22, 0)),
    
    # rwii format: set.zw rd8, wp0, 1
    ("set.zw rd8, wp0, 1", encode_rwii(0x4C, 8, 0, 1)),
    # rwii format: or.w rd8, wp0, 1
    ("or.w rd8, wp0, 1", encode_rwii(0x48, 8, 0, 1)),
    
    # orrr format: add.ub rd8, rd0, rd0 (op=0x43, ha=0x20)
    ("add.ub rd8, rd0, rd0", encode_orrr(0x43, 0x20, 8, 0, 0)),
    # orrr format: add.sb rd8, rd0, rd0 (op=0x43, ha=0x21)
    ("add.sb rd8, rd0, rd0", encode_orrr(0x43, 0x21, 8, 0, 0)),
    # orrr format: add.uw rd8, rd0, rd0 (op=0x42, ha=0x20)
    ("add.uw rd8, rd0, rd0", encode_orrr(0x42, 0x20, 8, 0, 0)),
    # orrr format: add.sw rd8, rd0, rd0 (op=0x42, ha=0x21)
    ("add.sw rd8, rd0, rd0", encode_orrr(0x42, 0x21, 8, 0, 0)),
    # orrr format: add.ut rd8, rd0, rd0 (op=0x41, ha=0x20)
    ("add.ut rd8, rd0, rd0", encode_orrr(0x41, 0x20, 8, 0, 0)),
    # orrr format: add.st rd8, rd0, rd0 (op=0x41, ha=0x21)
    ("add.st rd8, rd0, rd0", encode_orrr(0x41, 0x21, 8, 0, 0)),
    
    # orri format: ext.uo rd8, rd0, 1 (op=0x40, ha=0x18)
    ("ext.uo rd8, rd0, 1", encode_orri(0x40, 0x18, 8, 0, 1)),
    # orri format: rd2rd {rd8}, {rd0} (op=0x40, ha=0x2C)
    ("rd2rd {rd8}, {rd0}", encode_orri(0x40, 0x2C, 8, 0, 1)),
    
    # oiii format: fence 0xf (op=0x77, ha=0x00)
    ("fence 0xf", encode_oiii(0x77, 0x00, 0xf)),

    # === New tests for LLVM-008t: migrated from disassembly.s + basic-encoding.s ===

    # rrii_load.s: ld.ub rd8, [rb0, 1] (op=0x10, ha=8, hb=0, imm12=1)
    ("ld.ub rd8, [rb0, 1]", encode_rrii(0x10, 8, 0, 1)),
    # rrii_load.s: ld.sb rd1, [rb2, -1] (op=0x13, ha=1, hb=2, imm12=-1)
    ("ld.sb rd1, [rb2, -1]", encode_rrii(0x13, 1, 2, -1)),

    # rrri.s: ldm.ub {rd8:rd9}, [rb0, rd1] (op=0x28, ha=8, hb=0, hc=1, hd=2)
    ("ldm.ub {rd8:rd9}, [rb0, rd1]", encode_rrri(0x28, 8, 0, 1, 2)),

    # rrrr.s: add.uo {rd8, rd9}, rd10, rd11 (op=0x50)
    ("add.uo {rd8, rd9}, rd10, rd11", encode_rrrr(0x50, 8, 9, 10, 11)),
    # rrrr.s: add.so {rd8, rd9}, rd10, rd11 (op=0x51)
    ("add.so {rd8, rd9}, rd10, rd11", encode_rrrr(0x51, 8, 9, 10, 11)),

    # riii_branch.s: br.n {rd0}?, [rb0, 16] (16 bytes >> 2 = 4, op=0x68)
    ("br.n {rd0}?, [rb0, 16]", encode_riii(0x68, 0, 4)),
    # riii_branch.s: br.nn {rd0}?, [rb0, 16] (16 bytes >> 2 = 4, op=0x69)
    ("br.nn {rd0}?, [rb0, 16]", encode_riii(0x69, 0, 4)),
    # riii_branch.s: br.z {rd0}?, [rb0, 16] (16 bytes >> 2 = 4, op=0x6A)
    ("br.z {rd0}?, [rb0, 16]", encode_riii(0x6A, 0, 4)),
    # riii_branch.s: br.nz {rd0}?, [rb0, 16] (16 bytes >> 2 = 4, op=0x6B)
    ("br.nz {rd0}?, [rb0, 16]", encode_riii(0x6B, 0, 4)),
    # riii_branch.s: br.p {rd0}?, [rb0, 16] (16 bytes >> 2 = 4, op=0x6C)
    ("br.p {rd0}?, [rb0, 16]", encode_riii(0x6C, 0, 4)),
    # riii_branch.s: br.np {rd0}?, [rb0, 16] (16 bytes >> 2 = 4, op=0x6D)
    ("br.np {rd0}?, [rb0, 16]", encode_riii(0x6D, 0, 4)),

    # LLVM-049t: br.z/br.nz bank variants (expression-offset bypass must select
    # by operand bank).  Same register/offset, RD bank -> 0x6A/0x6B, RB -> 0x72/0x73.
    ("br.z {rd16}?, [rb0, 16]", encode_riii(0x6A, 16, 4)),
    ("br.nz {rd16}?, [rb0, 16]", encode_riii(0x6B, 16, 4)),
    ("br.z {rb16}?, [rb0, 16]", encode_riii(0x72, 16, 4)),
    ("br.nz {rb16}?, [rb0, 16]", encode_riii(0x73, 16, 4)),

    # rrii_branch.s: br.eq {rd8, rd0}?, [rb0, 16] (16 bytes >> 2 = 4, op=0x6E)
    ("br.eq {rd8, rd0}?, [rb0, 16]", encode_rrii(0x6E, 8, 0, 4)),

    # oiii.s: swym 42 (op=0x77, ha=0x22)
    ("swym 42", encode_oiii(0x77, 0x22, 42)),

    # orrr.s: or.o rd8, rd9, rd10 (op=0x40, ha=0x09)
    ("or.o rd8, rd9, rd10", encode_orrr(0x40, 0x09, 8, 9, 10)),

    # orrr.s: sub.o rd8, rb9, rb10 (M3, ADR-0012 D9.1; op=0x40, ha=0x33)
    # dst rd8 -> hb, src rb9 -> hc, src rb10 -> hd
    ("sub.o rd8, rb9, rb10", encode_orrr(0x40, 0x33, 8, 9, 10)),

    # rb_ops.s: rb2rd {rd8:rd9}, {rb9:rb10} (op=0x40, ha=0x36)
    ("rb2rd {rd8:rd9}, {rb9:rb10}", encode_orri(0x40, 0x36, 8, 9, 2)),
    # rb_ops.s: rd2rd {rd8}, {rd1} (op=0x40, ha=0x2C)
    ("rd2rd {rd8}, {rd1}", encode_orri(0x40, 0x2C, 8, 1, 1)),
    # basic-encoding.s: add.si rd8, -1 (op=0x59, ha=8, imms18=-1)
    ("add.si rd8, -1", encode_riii(0x59, 8, -1)),
    # basic-encoding.s: br.n {rd0}?, [rb0, 8] (8 bytes >> 2 = 2, forward fixup)
    ("br.n {rd0}?, [rb0, 8]", encode_riii(0x68, 0, 2)),

    # rwii.s: set.zw rd8, wp0, 0x1234 (op=0x4C, ha=8, wp=0, immu16=0x1234)
    ("set.zw rd8, wp0, 0x1234", encode_rwii(0x4C, 8, 0, 0x1234)),

    # === RA instructions (LLVM-011t) ===
    # rrii format: ld.o ra1, [rb2, 0] (op=0x24, ha=1, hb=2, imm12=0)
    ("ld.o ra1, [rb2, 0]", encode_rrii(0x24, 1, 2, 0)),
    # rrii format: st.o ra1, [rb2, 8] (op=0x25, ha=1, hb=2, imm12=8)
    ("st.o ra1, [rb2, 8]", encode_rrii(0x25, 1, 2, 8)),
    # rrri format: ldm.o {ra1:ra2}, [rb2, rd3] (op=0x3C, ha=1, hb=2, hc=3, hd=2)
    ("ldm.o {ra1:ra2}, [rb2, rd3]", encode_rrri(0x3C, 1, 2, 3, 2)),
    # rrri format: stm.o {ra1:ra2}, [rb2, rd3] (op=0x3D, ha=1, hb=2, hc=3, hd=2)
    ("stm.o {ra1:ra2}, [rb2, rd3]", encode_rrri(0x3D, 1, 2, 3, 2)),
    # orri format: rd2ra {ra1:ra3}, {rd2:rd4} (op=0x40, ha=0x2D, hb=1, hc=2, hd=3)
    ("rd2ra {ra1:ra3}, {rd2:rd4}", encode_orri(0x40, 0x2D, 1, 2, 3)),
    # orri format: ra2rd {rd1:rd3}, {ra2:ra4} (op=0x40, ha=0x2E, hb=1, hc=2, hd=3)
    ("ra2rd {rd1:rd3}, {ra2:ra4}", encode_orri(0x40, 0x2E, 1, 2, 3)),
    # Boundary: ld.o ra0, [rb0, 0] (op=0x24, ha=0, hb=0, imm12=0)
    ("ld.o ra0, [rb0, 0]", encode_rrii(0x24, 0, 0, 0)),
    # Boundary: st.o ra63, [rb63, 0] (op=0x25, ha=63, hb=63, imm12=0)
    ("st.o ra63, [rb63, 0]", encode_rrii(0x25, 63, 63, 0)),
    # Boundary: ldm.o immu6=1 → single register (count=1)
    # NOTE: immu6=0 (count=0, encoding 0x3c000000) → ILLI, new syntax cannot express.
    #       Covered by .4byte 0x3c000000 in ra.s lit test.
    ("ldm.o {ra0}, [rb0, rd0]", encode_rrri(0x3C, 0, 0, 0, 1)),
    # Boundary: rd2ra {ra0:ra62}, {rd0:rd62} (op=0x40, ha=0x2D, hb=0, hc=0, hd=63)
    ("rd2ra {ra0:ra62}, {rd0:rd62}", encode_orri(0x40, 0x2D, 0, 0, 63)),
    # Boundary: ra2rd {rd63:rf61}, {ra63:rb61} (op=0x40, ha=0x2E, hb=63, hc=63, hd=63)
    ("ra2rd {rd63:rf61}, {ra63:rb61}", encode_orri(0x40, 0x2E, 63, 63, 63)),

    # === FP instructions (LLVM-029t, scope: fp; 60 unique cases) ===
    # Expected words are derived from contracts/opcodes.yaml op/ha/field
    # layout -- not read back from llvm-mc (docs/fp-oracle-design.md).
    ("ld.t rf4, [rb2, 16]", encode_rrii(0x16, 4, 2, 16)),
    ("st.t rf6, [rb3, 24]", encode_rrii(0x17, 6, 3, 24)),
    ("ld.o rf8, [rb4, 32]", encode_rrii(0x26, 8, 4, 32)),
    ("st.o rf10, [rb5, 40]", encode_rrii(0x27, 10, 5, 40)),
    ("ldm.t {rf4:rf6}, [rb2, rd3]", encode_rrri(0x2E, 4, 2, 3, 3)),
    ("stm.t {rf8:rf10}, [rb4, rd5]", encode_rrri(0x2F, 8, 4, 5, 3)),
    ("ldm.o {rf12:rf14}, [rb6, rd7]", encode_rrri(0x3E, 12, 6, 7, 3)),
    ("stm.o {rf16:rf18}, [rb8, rd9]", encode_rrri(0x3F, 16, 8, 9, 3)),
    ("set.w rf4, wp0, 0x1234", encode_rwii(0x4F, 4, 0, 0x1234)),
    ("cs.eq {rd8, rd0}?, rf4, rf6", encode_rrrr(0x5E, 8, 0, 4, 6)),
    ("cs.ne {rd10, rd2}?, rf8, rf10", encode_rrrr(0x5F, 10, 2, 8, 10)),
    ("cs.n {rd12}?, rf4, rf6, rf8", encode_rrrr(0x61, 12, 4, 6, 8)),
    ("cs.z {rd14}?, rf10, rf12, rf14", encode_rrrr(0x63, 14, 10, 12, 14)),
    ("cs.p {rd16}?, rf16, rf18, rf20", encode_rrrr(0x65, 16, 16, 18, 20)),
    ("ftadd rf4, rf6, rf8", encode_orrr(0x44, 0x10, 4, 6, 8)),
    ("ftsub rf4, rf6, rf8", encode_orrr(0x44, 0x11, 4, 6, 8)),
    ("ftmul rf4, rf6, rf8", encode_orrr(0x44, 0x12, 4, 6, 8)),
    ("ftdiv rf4, rf6, rf8", encode_orrr(0x44, 0x13, 4, 6, 8)),
    ("ftrem rf4, rf6, rf8", encode_orrr(0x44, 0x14, 4, 6, 8)),
    ("ftsclb rf4, rf6, rf8", encode_orrr(0x44, 0x15, 4, 6, 8)),
    ("ftsgnn rf4, rf6, rf8", encode_orrr(0x44, 0x16, 4, 6, 8)),
    ("ftsgnj rf4, rf6, rf8", encode_orrr(0x44, 0x17, 4, 6, 8)),
    ("foadd rf4, rf6, rf8", encode_orrr(0x44, 0x18, 4, 6, 8)),
    ("fosub rf4, rf6, rf8", encode_orrr(0x44, 0x19, 4, 6, 8)),
    ("fomul rf4, rf6, rf8", encode_orrr(0x44, 0x1A, 4, 6, 8)),
    ("fodiv rf4, rf6, rf8", encode_orrr(0x44, 0x1B, 4, 6, 8)),
    ("forem rf4, rf6, rf8", encode_orrr(0x44, 0x1C, 4, 6, 8)),
    ("fosclb rf4, rf6, rf8", encode_orrr(0x44, 0x1D, 4, 6, 8)),
    ("fosgnn rf4, rf6, rf8", encode_orrr(0x44, 0x1E, 4, 6, 8)),
    ("fosgnj rf4, rf6, rf8", encode_orrr(0x44, 0x1F, 4, 6, 8)),
    ("ftqcmp rd4, rf6, rf8", encode_orrr(0x44, 0x20, 4, 6, 8)),
    ("ftscmp rd4, rf6, rf8", encode_orrr(0x44, 0x21, 4, 6, 8)),
    ("foqcmp rd4, rf6, rf8", encode_orrr(0x44, 0x28, 4, 6, 8)),
    ("foscmp rd4, rf6, rf8", encode_orrr(0x44, 0x29, 4, 6, 8)),
    ("ftcls {rd4:rd6}, {rf8:rf10}", encode_orri(0x44, 0x00, 4, 8, 3)),
    ("ft2fo {rf4:rf6}, {rf8:rf10}", encode_orri(0x44, 0x01, 4, 8, 3)),
    ("ft2ft {rf10:rf12}, {rf14:rf16}", encode_orri(0x44, 0x02, 10, 14, 3)),
    ("ftroot rf4, rf6, 2", encode_orri(0x44, 0x06, 4, 6, 2)),
    ("focls {rd8:rd10}, {rf12:rf14}", encode_orri(0x44, 0x08, 8, 12, 3)),
    ("fo2ft {rf4:rf6}, {rf8:rf10}", encode_orri(0x44, 0x09, 4, 8, 3)),
    ("fo2fo {rf10:rf12}, {rf14:rf16}", encode_orri(0x44, 0x0A, 10, 14, 3)),
    ("foroot rf4, rf6, 2", encode_orri(0x44, 0x0E, 4, 6, 2)),
    ("ft2it {rd4:rd6}, {rf8:rf10}", encode_orri(0x44, 0x30, 4, 8, 3)),
    ("ft2io {rd10:rd12}, {rf14:rf16}", encode_orri(0x44, 0x31, 10, 14, 3)),
    ("ft2ut {rd8:rd10}, {rf12:rf14}", encode_orri(0x44, 0x32, 8, 12, 3)),
    ("ft2uo {rd14:rd16}, {rf18:rf20}", encode_orri(0x44, 0x33, 14, 18, 3)),
    ("it2ft {rf4:rf6}, {rd8:rd10}", encode_orri(0x44, 0x34, 4, 8, 3)),
    ("io2ft {rf10:rf12}, {rd14:rd16}", encode_orri(0x44, 0x35, 10, 14, 3)),
    ("ut2ft {rf8:rf10}, {rd12:rd14}", encode_orri(0x44, 0x36, 8, 12, 3)),
    ("uo2ft {rf14:rf16}, {rd18:rd20}", encode_orri(0x44, 0x37, 14, 18, 3)),
    ("fo2it {rd4:rd6}, {rf8:rf10}", encode_orri(0x44, 0x38, 4, 8, 3)),
    ("fo2io {rd10:rd12}, {rf14:rf16}", encode_orri(0x44, 0x39, 10, 14, 3)),
    ("fo2ut {rd8:rd10}, {rf12:rf14}", encode_orri(0x44, 0x3A, 8, 12, 3)),
    ("fo2uo {rd14:rd16}, {rf18:rf20}", encode_orri(0x44, 0x3B, 14, 18, 3)),
    ("it2fo {rf4:rf6}, {rd8:rd10}", encode_orri(0x44, 0x3C, 4, 8, 3)),
    ("rd2rf {rf10:rf12}, {rd14:rd16}", encode_orri(0x40, 0x3D, 10, 14, 3)),
    ("io2fo {rf8:rf10}, {rd12:rd14}", encode_orri(0x44, 0x3D, 8, 12, 3)),
    ("rf2rd {rd14:rd16}, {rf18:rf20}", encode_orri(0x40, 0x3E, 14, 18, 3)),
    ("ut2fo {rf4:rf6}, {rd8:rd10}", encode_orri(0x44, 0x3E, 4, 8, 3)),
    ("uo2fo {rf10:rf12}, {rd14:rd16}", encode_orri(0x44, 0x3F, 10, 14, 3)),
]

def parse_elf_text_section(data):
    """Parse ELF file and extract .text section content.
    
    Returns text_data or None if .text not found.
    Supports both 32-bit and 64-bit ELF, both little-endian and big-endian.
    """
    if len(data) < 16:
        return None
    
    # Check ELF magic
    if data[:4] != b'\x7fELF':
        return None
    
    # Determine endianness: ei_data (byte 5) = 1 for LE, 2 for BE
    ei_data = data[5]
    if ei_data == 1:
        endian = '<'  # little-endian
    elif ei_data == 2:
        endian = '>'  # big-endian
    else:
        return None
    
    # Determine 32/64 bit: ei_class (byte 4)
    ei_class = data[4]
    if ei_class == 1:  # 32-bit
        e_shoff = struct.unpack_from(endian + 'I', data, 32)[0]
        e_shentsize = struct.unpack_from(endian + 'H', data, 46)[0]
        e_shnum = struct.unpack_from(endian + 'H', data, 48)[0]
        e_shstrndx = struct.unpack_from(endian + 'H', data, 50)[0]
        sh_name_off = 0
        sh_offset_off = 16
        sh_size_off = 20
    elif ei_class == 2:  # 64-bit
        e_shoff = struct.unpack_from(endian + 'Q', data, 40)[0]
        e_shentsize = struct.unpack_from(endian + 'H', data, 58)[0]
        e_shnum = struct.unpack_from(endian + 'H', data, 60)[0]
        e_shstrndx = struct.unpack_from(endian + 'H', data, 62)[0]
        sh_name_off = 0
        sh_offset_off = 24
        sh_size_off = 32
    else:
        return None
    
    if e_shnum == 0 or e_shoff == 0:
        return None
    
    # Read section header string table
    shstrtab_hdr_off = e_shoff + e_shstrndx * e_shentsize
    if ei_class == 1:
        shstrtab_offset = struct.unpack_from(endian + 'I', data, shstrtab_hdr_off + sh_offset_off)[0]
        shstrtab_size = struct.unpack_from(endian + 'I', data, shstrtab_hdr_off + sh_size_off)[0]
    else:
        shstrtab_offset = struct.unpack_from(endian + 'Q', data, shstrtab_hdr_off + sh_offset_off)[0]
        shstrtab_size = struct.unpack_from(endian + 'Q', data, shstrtab_hdr_off + sh_size_off)[0]
    
    shstrtab = data[shstrtab_offset:shstrtab_offset + shstrtab_size]
    
    # Find .text section
    for i in range(e_shnum):
        hdr_off = e_shoff + i * e_shentsize
        name_idx = struct.unpack_from(endian + 'I', data, hdr_off + sh_name_off)[0]
        name_end = shstrtab.find(b'\0', name_idx)
        if name_end == -1:
            continue
        name = shstrtab[name_idx:name_end].decode('ascii', errors='replace')
        
        if name == '.text':
            if ei_class == 1:
                offset = struct.unpack_from(endian + 'I', data, hdr_off + sh_offset_off)[0]
                size = struct.unpack_from(endian + 'I', data, hdr_off + sh_size_off)[0]
            else:
                offset = struct.unpack_from(endian + 'Q', data, hdr_off + sh_offset_off)[0]
                size = struct.unpack_from(endian + 'Q', data, hdr_off + sh_size_off)[0]
            return data[offset:offset + size]
    
    return None

def run_test(asm, expected, llvm_mc, tmp_dir):
    """Run a single test case."""
    obj_path = os.path.join(tmp_dir, 'test_enc.o')
    try:
        result = subprocess.run(
            [llvm_mc, '--triple=dadao-unknown-elf', '-filetype=obj', '-o', obj_path, '-'],
            input=asm.encode(),
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            return False, f"Assembly failed: {result.stderr.decode()}"
        
        # Read the object file
        with open(obj_path, 'rb') as f:
            data = f.read()
        
        # Parse .text section
        text_data = parse_elf_text_section(data)
        if text_data is None:
            return False, "Could not find .text section in ELF"
        
        if len(text_data) < 4:
            return False, f".text section too small: {len(text_data)} bytes"
        
        # Read the first instruction (big-endian)
        actual = struct.unpack_from('>I', text_data, 0)[0]
        
        if actual == expected:
            return True, "OK"
        else:
            return False, f"Encoding mismatch: expected {expected:08x}, got {actual:08x}"
    except Exception as e:
        return False, str(e)

def main():
    # Try common paths for llvm-mc
    candidates = [
        os.path.join(os.environ.get('DADAO_ROOT', ''), '.work/build/llvm/bin/llvm-mc'),
        '/home/ubuntu/DADAO-v5/.work/build/llvm/bin/llvm-mc',
        '/mnt/tao/DADAO-v5/.work/build/llvm/bin/llvm-mc',
    ]
    llvm_mc = None
    for c in candidates:
        if c and os.path.exists(c):
            llvm_mc = c
            break
    if llvm_mc is None:
        llvm_mc = candidates[-1]  # fallback to last
    
    if not os.path.exists(llvm_mc):
        print(f"Error: llvm-mc not found at {llvm_mc}", file=sys.stderr)
        sys.exit(1)
    
    passed = 0
    failed = 0
    failures = []
    
    # Use a temporary directory for test files
    with tempfile.TemporaryDirectory(prefix='dadao_oracle_') as tmp_dir:
        for asm, expected in TESTS:
            ok, msg = run_test(asm, expected, llvm_mc, tmp_dir)
            if ok:
                passed += 1
            else:
                failed += 1
                failures.append((asm, expected, msg))
                print(f"FAIL: {asm}", file=sys.stderr)
                print(f"  Expected: {expected:08x}", file=sys.stderr)
                print(f"  {msg}", file=sys.stderr)
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(TESTS)} tests", file=sys.stderr)
    
    if failures:
        print("\nFailed tests:", file=sys.stderr)
        for asm, expected, msg in failures:
            print(f"  {asm}", file=sys.stderr)
        sys.exit(1)
    else:
        print("All encoding tests passed!", file=sys.stderr)
        # Cross-check: unique oracle test count >= lit OBJ line count
        lit_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), 'tests', 'lit', 'MC', 'Dadao')
        obj_count = 0
        for sfile in glob.glob(os.path.join(lit_dir, '*.s')):
            with open(sfile) as f:
                for line in f:
                    if '; OBJ:' in line:
                        obj_count += 1
        n_unique = len(set((a, e) for a, e in TESTS))
        if obj_count > 0 and n_unique < obj_count:
            print(f"CROSS-CHECK FAIL: oracle tests ({n_unique}) < lit OBJ lines ({obj_count})",
                  file=sys.stderr)
            sys.exit(1)
        print(f"Cross-check OK: oracle tests ({n_unique}) >= lit OBJ lines ({obj_count})",
              file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
