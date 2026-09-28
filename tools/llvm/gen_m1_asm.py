#!/usr/bin/env python3
"""Generate 178 M1 assembly test lines (new syntax) from contracts/opcodes.yaml.

Each line is a valid DADAO new-syntax assembly instruction for llvm-mc.
Register bank per id is derived from opcodes.yaml field definitions.

Usage:
    python3 tools/llvm/gen_m1_asm.py                    # print to stdout
    python3 tools/llvm/gen_m1_asm.py -o /tmp/m1.s       # write to file
"""
import argparse
import os
import sys

import yaml

# ── Register bank helpers ───────────────────────────────────────────

DUAL = {'add.uo', 'add.so', 'sub.uo', 'sub.so', 'mul.uo', 'mul.so'}
CS_SINGLE = {'cs.n', 'cs.z', 'cs.p'}
CS_DOUBLE = {'cs.eq', 'cs.ne'}
BLOCKCOPY = {'rd2rd', 'rd2ra', 'ra2rd', 'rb2rb', 'rd2rb', 'rb2rd',
             'rd2rf', 'rf2rd'}


def _bank(fields, role, default_bank=None):
    """Return the register bank for the first field matching *role*."""
    for f in fields:
        if f.get('role') == role:
            return f.get('bank', default_bank)
    return default_bank


def _first_reg_bank(fields, default='rd'):
    """Return the bank of the first register field (by field order)."""
    for f in fields:
        if f.get('bank') in ('rd', 'rb', 'rf', 'ra'):
            return f['bank']
    return default


def _dst_bank(fields):
    """dst bank; falls back to first register field (for stores)."""
    b = _bank(fields, 'dst')
    if b is not None:
        return b
    return _first_reg_bank(fields)


def _src_bank(fields, n=0):
    count = 0
    for f in fields:
        if f.get('role') == 'src' and f.get('bank') in ('rd', 'rb', 'rf', 'ra'):
            if count == n:
                return f['bank']
            count += 1
    return 'rd'


# ── Per-format generators ───────────────────────────────────────────

def gen_rrii(e):
    m = e['mnemonic']
    fs = e['fields']
    if m in ('jump', 'call'):
        return f"{m} [rb3, rd0, 24i]"
    if m.startswith('br.'):
        # Two-register branch: rdha, rdhb
        rd_fields = [f for f in fs if f.get('bank') == 'rd']
        if len(rd_fields) == 1:
            # Should not happen for rrii, but guard
            return f"{m} {{rd8}}?, [rb0, 4i]"
        return f"{m} {{rd8, rd0}}?, [rb0, 4i]"
    if m.startswith('cmp.'):
        dst = _dst_bank(fs)
        src = _src_bank(fs)
        return f"{m} {dst}8, {src}0, 1"
    # ld./st. memory (rrii)
    dst = _dst_bank(fs)
    return f"{m} {dst}8, [rb0, 1]"


def gen_rrri(e):
    m = e['mnemonic']
    fs = e['fields']
    dst = _dst_bank(fs)
    # base register (rb)
    rb = 'rb'
    # offset register (rd)
    rd = 'rd'
    return f"{m} {{{dst}8:{dst}10}}, [rb0, rd1]"


def gen_riii(e):
    m = e['mnemonic']
    fs = e['fields']
    if m == 'ret':
        return "ret rd0, 0"
    r = _dst_bank(fs)
    if m.startswith('br.'):
        return f"{m} {{{r}8}}?, [rb0, 4i]"
    return f"{m} {r}8, 1"


def gen_iiii(e):
    m = e['mnemonic']
    return f"{m} [rb0, 2i]"


def gen_rwii(e):
    m = e['mnemonic']
    fs = e['fields']
    dst = _dst_bank(fs)
    return f"{m} {dst}8, wp2, 0x1234"


def gen_rrrr(e):
    m = e['mnemonic']
    if m in DUAL:
        return f"{m} {{rd8, rd9}}, rd10, rd11"
    if m in CS_SINGLE:
        return f"{m} {{rd1}}?, rd2, rd3, rd4"
    if m in CS_DOUBLE:
        return f"{m} {{rd8, rd0}}?, rd9, rd10"
    raise ValueError(f"unexpected rrrr mnemonic: {m}")


def gen_orrr(e):
    m = e['mnemonic']
    fs = e['fields']
    dst = _dst_bank(fs)
    src1 = _src_bank(fs, 0)
    src2 = _src_bank(fs, 1)
    return f"{m} {dst}8, {src1}9, {src2}10"


def gen_orri(e):
    m = e['mnemonic']
    fs = e['fields']
    dst = _dst_bank(fs)
    src = _src_bank(fs)
    if m in BLOCKCOPY:
        return f"{m} {{{dst}8:{dst}10}}, {{{src}1:{src}3}}"
    return f"{m} {dst}8, {src}0, 1"


def gen_oiii(e):
    m = e['mnemonic']
    if m == 'fence':
        return "fence 0xf"
    return f"{m} 0"


GENERATORS = {
    'rrii': gen_rrii,
    'rrri': gen_rrri,
    'riii': gen_riii,
    'iiii': gen_iiii,
    'rwii': gen_rwii,
    'rrrr': gen_rrrr,
    'orrr': gen_orrr,
    'orri': gen_orri,
    'oiii': gen_oiii,
}


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--output', help='Write .s to file instead of stdout')
    parser.add_argument('opcodes', nargs='?',
                        default=os.path.join(os.path.dirname(__file__),
                                             '..', '..', 'contracts', 'opcodes.yaml'),
                        help='Path to opcodes.yaml (default: contracts/opcodes.yaml)')
    args = parser.parse_args()

    entries = yaml.safe_load(open(args.opcodes))
    m1 = [e for e in entries if not e.get('excluded_m1')]

    lines = []
    for e in m1:
        fmt = e['format']
        gen = GENERATORS.get(fmt)
        if gen is None:
            raise ValueError(f"no generator for format {fmt} (id={e['id']})")
        lines.append(gen(e))

    text = '\n'.join(lines) + '\n'
    if args.output:
        with open(args.output, 'w') as f:
            f.write(text)
        print(f"Wrote {len(lines)} lines to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    print(f"M1 count: {len(lines)}", file=sys.stderr)


if __name__ == '__main__':
    main()
