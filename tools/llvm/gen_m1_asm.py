#!/usr/bin/env python3
"""
Generate 178 M1 assembly test lines from contracts/opcodes.yaml.
Each line is a valid DADAO assembly instruction that can be assembled by llvm-mc.
"""
import yaml
import sys

def generate_operand(field, format_type):
    """Generate a valid operand value based on field properties."""
    role = field.get('role', '')
    bank = field.get('bank', '')
    bits = field.get('bits', '')
    signed = field.get('signed', False)
    
    if bank == 'rd':
        # Use rd8 for destination, rd0 for source (except rd0 which is special)
        if role == 'dst':
            return 'rd8'
        else:
            return 'rd0'
    elif bank == 'rb':
        return 'rb1'  # rb1 is stack pointer, valid for most uses
    elif bank == 'rf':
        return 'rf0'
    elif bank == 'ra':
        return 'ra0'
    elif bank == 'imm':
        # Generate a small immediate value
        if '12' in bits:
            return '1' if not signed else '1'
        elif '18' in bits:
            return '1' if not signed else '1'
        elif '24' in bits:
            return '1' if not signed else '1'
        elif '16' in bits:
            return '1'
        elif '6' in bits:
            return '1'
        else:
            return '1'
    elif role == 'wyde_pos':
        return '0'  # wp0
    else:
        return '0'

def generate_asm_line(insn_data):
    """Generate a valid assembly line for an instruction."""
    mnemonic = insn_data['mnemonic']
    fmt = insn_data.get('format', '')
    fields = insn_data.get('fields', [])
    
    # Generate operands based on format
    operands = []
    
    if fmt == 'rrrr':
        # 4 registers
        for f in fields:
            if f.get('bank') in ['rd', 'rb', 'rf', 'ra']:
                operands.append(generate_operand(f, fmt))
    elif fmt == 'rrri':
        # 3 registers + immediate
        for f in fields:
            if f.get('bank') in ['rd', 'rb', 'rf', 'ra']:
                operands.append(generate_operand(f, fmt))
        for f in fields:
            if f.get('bank') == 'imm':
                operands.append(generate_operand(f, fmt))
    elif fmt == 'rrii':
        # 2 registers + 2 immediates (combined as 12-bit)
        reg_count = 0
        imm_found = False
        for f in fields:
            if f.get('bank') in ['rd', 'rb', 'rf', 'ra'] and reg_count < 2:
                operands.append(generate_operand(f, fmt))
                reg_count += 1
            elif f.get('bank') == 'imm' and not imm_found:
                operands.append('1')
                imm_found = True
    elif fmt == 'riii':
        # 1 register + immediate
        for f in fields:
            if f.get('bank') in ['rd', 'rb', 'rf', 'ra']:
                operands.append(generate_operand(f, fmt))
                break
        for f in fields:
            if f.get('bank') == 'imm':
                operands.append('1')
                break
    elif fmt == 'iiii':
        # Just immediate
        operands.append('1')
    elif fmt == 'rwii':
        # 1 register + wyde position + immediate
        reg_done = False
        wyde_done = False
        imm_done = False
        for f in fields:
            if f.get('bank') in ['rd', 'rb'] and not reg_done:
                operands.append(generate_operand(f, fmt))
                reg_done = True
            elif f.get('role') == 'wyde_pos' and not wyde_done:
                operands.append('0')  # wp0
                wyde_done = True
            elif f.get('bank') == 'imm' and not imm_done:
                operands.append('1')
                imm_done = True
    elif fmt == 'orrr':
        # minor-opcode + 3 registers (ha is set by def)
        for f in fields:
            if f.get('bank') in ['rd', 'rb', 'rf', 'ra']:
                operands.append(generate_operand(f, fmt))
    elif fmt == 'orri':
        # minor-opcode + 2 registers + immediate
        # Skip ha (minor_op), then: rdhb (dst), rdhc (src), imm6
        dst_done = False
        src_done = False
        imm_done = False
        for f in fields:
            if f.get('role') == 'minor_op':
                continue  # Skip minor opcode
            if f.get('role') == 'dst' and not dst_done:
                operands.append(generate_operand(f, fmt))
                dst_done = True
            elif f.get('role') == 'src' and f.get('bank') in ['rd', 'rb', 'rf', 'ra'] and not src_done:
                operands.append(generate_operand(f, fmt))
                src_done = True
            elif f.get('bank') == 'imm' and not imm_done:
                operands.append('1')
                imm_done = True
    elif fmt == 'oiii':
        # minor-opcode + immediate
        operands.append('1')
    else:
        # Default: just use 1
        operands.append('1')
    
    # Special cases for specific mnemonics
    if mnemonic == 'illi':
        return f'{mnemonic} 0'
    elif mnemonic == 'swym':
        return f'{mnemonic} 0'
    elif mnemonic == 'fence':
        return f'{mnemonic} 0xf'
    elif mnemonic == 'ret':
        return f'ret rd0, 0'
    elif mnemonic.startswith('br.'):
        # Branch instructions need special handling
        if fmt == 'riii':
            # Single register branch
            return f'{mnemonic} rd0, 1'
        elif fmt == 'rrii':
            # Two register branch
            return f'{mnemonic} rd0, rd0, 1'
    elif mnemonic == 'call':
        if fmt == 'iiii':
            return f'{mnemonic} 1'
        elif fmt == 'rrii':
            return f'{mnemonic} rb1, rd0, 1'
    elif mnemonic == 'jump':
        if fmt == 'iiii':
            return f'{mnemonic} 1'
        elif fmt == 'rrii':
            return f'{mnemonic} rb1, rd0, 1'
    
    return f'{mnemonic} {", ".join(operands)}'

def main():
    with open('/mnt/tao/DADAO-v5/contracts/opcodes.yaml', 'r') as f:
        data = yaml.safe_load(f)
    
    count = 0
    for insn in data:
        if insn.get('excluded_m1'):
            continue
        
        asm_line = generate_asm_line(insn)
        print(asm_line)
        count += 1
    
    print(f'# Total: {count} instructions', file=sys.stderr)

if __name__ == '__main__':
    main()
