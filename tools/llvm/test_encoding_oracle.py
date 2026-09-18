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
}

# Test cases: (assembly, expected_encoding)
TESTS = [
    # rrrr format: add.uo rd8, rd0, rd0, rd0
    ("add.uo rd8, rd0, rd0, rd0", encode_rrrr(0x50, 8, 0, 0, 0)),
    # rrrr format: add.so rd8, rd0, rd0, rd0
    ("add.so rd8, rd0, rd0, rd0", encode_rrrr(0x51, 8, 0, 0, 0)),
    
    # rrri format: ldm.ub rd8, rb1, rd0, 1
    ("ldm.ub rd8, rb1, rd0, 1", encode_rrri(0x28, 8, 1, 0, 1)),
    
    # rrii format: ld.ub rd8, rb1, 1
    ("ld.ub rd8, rb1, 1", encode_rrii(0x10, 8, 1, 1)),
    # rrii format: st.b rd0, rb1, 1
    ("st.b rd0, rb1, 1", encode_rrii(0x18, 0, 1, 1)),
    # rrii format: cmp.ui rd8, rd0, 1
    ("cmp.ui rd8, rd0, 1", encode_rrii(0x5C, 8, 0, 1)),
    # rrii format: cmp.si rd8, rd0, 1
    ("cmp.si rd8, rd0, 1", encode_rrii(0x5D, 8, 0, 1)),
    
    # riii format: add.si rd8, 1
    ("add.si rd8, 1", encode_riii(0x59, 8, 1)),
    # riii format: add.si rb1, 1
    ("add.si rb1, 1", encode_riii(0x5B, 1, 1)),
    # riii format: br.n rd0, 1
    ("br.n rd0, 1", encode_riii(0x68, 0, 1)),
    # riii format: br.nn rd0, 1
    ("br.nn rd0, 1", encode_riii(0x69, 0, 1)),
    # riii format: br.z rd0, 1
    ("br.z rd0, 1", encode_riii(0x6A, 0, 1)),
    # riii format: br.nz rd0, 1
    ("br.nz rd0, 1", encode_riii(0x6B, 0, 1)),
    # riii format: br.p rd0, 1
    ("br.p rd0, 1", encode_riii(0x6C, 0, 1)),
    # riii format: br.np rd0, 1
    ("br.np rd0, 1", encode_riii(0x6D, 0, 1)),
    # riii format: ret rd0, 0
    ("ret rd0, 0", encode_riii(0x76, 0, 0)),
    
    # iiii format: call 1
    ("call 1", encode_iiii(0x74, 1)),
    # iiii format: jump 1
    ("jump 1", encode_iiii(0x70, 1)),
    # iiii format: swym 0
    ("swym 0", encode_iiii(0x77, 0)),
    
    # rwii format: set.zw rd8, 0, 1
    ("set.zw rd8, 0, 1", encode_rwii(0x4C, 8, 0, 1)),
    # rwii format: or.w rd8, 0, 1
    ("or.w rd8, 0, 1", encode_rwii(0x48, 8, 0, 1)),
    
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
    # orri format: rd2rd rd8, rd0, 1 (op=0x40, ha=0x2C)
    ("rd2rd rd8, rd0, 1", encode_orri(0x40, 0x2C, 8, 0, 1)),
    
    # oiii format: illi 0 (op=0x00, ha=0x00)
    ("illi 0", encode_oiii(0x00, 0x00, 0)),
    # oiii format: fence 0xf (op=0x00, ha=0x01)
    ("fence 0xf", encode_oiii(0x00, 0x01, 0xf)),
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
    llvm_mc = '/mnt/tao/DADAO-v5/.work/build/llvm/bin/llvm-mc'
    
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
        sys.exit(0)

if __name__ == '__main__':
    main()
