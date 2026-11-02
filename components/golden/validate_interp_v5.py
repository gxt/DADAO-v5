#!/usr/bin/env python3
"""Replay ISA vectors against the scalar golden; see README.md for verdicts.

Encoding PASS checks identity and static legality only. Execution PASS checks
fault/state/PC assertions. Skips never count as verification of semantics.
"""
import argparse
import copy
from pathlib import Path
import re
import sys

import yaml

from dadao_interp_v5 import (DEFAULT_PC, MASK64, Fault, Unsupported, SpecificationGap, build_state,
                             check_legality, decode, is_supported,
                             mem_width_for, run)

VECTORS_DIR = Path(__file__).resolve().parents[2] / 'tests/vectors/isa'
BUCKETS = ('PASS-encoding', 'PASS-execution', 'FAIL', 'SKIP-deferred',
           'SKIP-scope', 'SKIP-machine')
CLASSES = {'encoding', 'legality', 'semantic', 'boundary', 'overlap'}
FAULTS = {'ILLI', 'UNDI', 'MALIGN', 'IALIGN', 'RASOF', 'RASUF',
          'UNMAPPED', 'CFXMEM'}
MACHINE_FAULTS = {'UNMAPPED', 'CFXMEM'}


def _parse_int(value, bits=64):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f'expected an integer/hex string, got {value!r}')
    n = int(value, 16) if isinstance(value, str) else value
    if not 0 <= n < (1 << bits):
        raise ValueError(f'value {value!r} outside unsigned {bits}-bit range')
    return n


def _check_state_shape(state):
    if state is None:
        return
    if not isinstance(state, dict):
        raise ValueError('state must be a mapping or null')
    unknown = set(state) - {'rd', 'rb', 'ra', 'rf', 'memory'}
    if unknown:
        raise ValueError(f'unknown state fields: {sorted(unknown)}')
    for bank in ('rd', 'rb', 'ra', 'rf'):
        regs = state.get(bank, {})
        if not isinstance(regs, dict):
            raise ValueError(f'{bank} must be a mapping')
        for name, value in regs.items():
            if not isinstance(name, str) or not re.fullmatch(bank + r'(0|[1-9][0-9]?)', name):
                raise ValueError(f'invalid register name: {name!r}')
            if int(name[2:]) > 63:
                raise ValueError(f'invalid register number: {name}')
            if name in ('rd0', 'rb0'):
                raise ValueError(f'{name} is implicit; use expected_pc to assert PC')
            _parse_int(value)
    entries = state.get('memory', [])
    if not isinstance(entries, list):
        raise ValueError('memory must be a list')
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {'address', 'value', 'width'}:
            raise ValueError('invalid memory entry')
        _parse_int(entry['address'], 48)
        _parse_int(entry['value'])
        if 'width' in entry and (type(entry['width']) is not int or entry['width'] not in (1, 2, 4, 8)):
            raise ValueError('memory width must be 1, 2, 4 or 8 bytes')


def compare_state(st, expected, width):
    """Compare only explicitly asserted values; invalid assertions raise errors."""
    _check_state_shape(expected)
    bad = []
    for bank in ('rd', 'rb', 'ra', 'rf'):
        for name, value in ((expected or {}).get(bank) or {}).items():
            have = getattr(st, bank)[int(name[2:])]
            want = _parse_int(value)
            if have != want:
                bad.append(f'{name}: golden=0x{have:016X} vector=0x{want:016X}')
    for entry in ((expected or {}).get('memory') or []):
        addr = _parse_int(entry['address'], 48)
        size = entry.get('width', width)
        have = st.load_mem(addr, size)
        want = _parse_int(entry['value']) & ((1 << (8 * size)) - 1)
        if have != want:
            bad.append(f'mem[0x{addr:X}]+{size}: golden=0x{have:X} vector=0x{want:X}')
    return bad


def _architectural(st):
    return {key: copy.deepcopy(getattr(st, key))
            for key in ('rd', 'rb', 'ra', 'rf', 'mem', 'pc', 'pc_next')}


def _imm64_loader_words(value):
    """Instruction count used by build_test_binary.py's wyde loader."""
    value = _parse_int(value)
    return 1 + sum(bool((value >> shift) & 0xFFFF) for shift in (16, 32, 48))


def _vector_pc(input_state):
    """Derive test instruction IP after the test binary's input-state loader."""
    state = input_state or {}
    count = 0
    for bank in ('rd', 'rb'):
        for name, value in sorted((state.get(bank) or {}).items()):
            if bank == 'rd' and name == 'rd0':
                continue
            if bank == 'rb' and name == 'rb0':
                continue
            count += _imm64_loader_words(value)
    for _, value in sorted((state.get('ra') or {}).items()):
        count += _imm64_loader_words(value) + 1
    for entry in state.get('memory') or []:
        count += _imm64_loader_words(entry['address'])
        count += _imm64_loader_words(entry['value']) + 1
    return (DEFAULT_PC + count * 4) & MASK64


def _check_vector(t):
    if not isinstance(t, dict):
        raise ValueError('vector must be a mapping')
    if t.get('class') not in CLASSES:
        raise ValueError(f'unknown vector class: {t.get("class")!r}')
    status = t.get('status', 'active')
    if status not in ('active', 'deferred'):
        raise ValueError(f'unknown status: {status!r}')
    if status == 'active' and t.get('deferred_reason'):
        raise ValueError('active vector cannot carry deferred_reason')
    if not isinstance(t.get('spec_cite'), str) or not t['spec_cite'].strip():
        raise ValueError('spec_cite must identify the normative source')
    _check_state_shape(t['input_state'])
    _check_state_shape(t.get('expected_state'))
    want_fault = t.get('expected_fault')
    if want_fault is not None and want_fault not in FAULTS:
        raise ValueError(f'unknown expected_fault: {want_fault!r}')
    if t.get('expected_pc') is not None:
        _parse_int(t['expected_pc'], 48)
    word = _parse_int(t['encoding']['word'], 32)
    reserved = t['encoding'].get('reserved', False)
    if type(reserved) is not bool:
        raise ValueError('encoding.reserved must be boolean')
    rec = fields = None
    decode_fault = None
    try:
        rec, fields = decode(word)
    except Fault as ex:
        decode_fault = ex.kind
    if reserved:
        if rec is not None or decode_fault != 'UNDI':
            raise ValueError('reserved vector actually decodes as a defined instruction')
        if t.get('id') is not None or t.get('mnemonic') is not None:
            raise ValueError('reserved vector must not claim an instruction identity')
        if t['class'] != 'legality' or want_fault != 'UNDI' or status != 'active':
            raise ValueError('reserved vector must be active legality expecting UNDI')
    elif rec is None:
        raise ValueError(f'defined vector decodes as {decode_fault}')
    else:
        for key in ('id', 'mnemonic', 'format'):
            if t.get(key) != rec[key]:
                raise ValueError(f'{key} mismatch: decoded={rec[key]!r} vector={t.get(key)!r}')

    # Validate architectural input constraints even for encoding and skipped
    # cases; a skip must not silently bless an impossible initial state.
    vector_pc = (_vector_pc(t['input_state'])
                 if rec is not None and rec.get('mnemonic') == 'aip.si'
                 else DEFAULT_PC)
    build_state(t['input_state'], pc=vector_pc, mem_width=mem_width_for(rec) if rec else 8)
    cls = t['class']
    if cls in ('encoding', 'legality'):
        if t.get('expected_state') is not None or t.get('expected_pc') is not None:
            raise ValueError(f'{cls} cannot carry state/PC assertions')
    if cls == 'encoding' and want_fault is not None:
        raise ValueError('encoding vectors must expect no fault')
    if cls == 'legality' and want_fault is None:
        raise ValueError('legality vector must assert a fault')
    if status == 'deferred':
        if not isinstance(t.get('deferred_reason'), str) or not t['deferred_reason'].strip():
            raise ValueError('deferred vector needs a reason')
        if t.get('expected_state') is not None or t.get('expected_pc') is not None:
            raise ValueError('deferred vector cannot claim state/PC assertions')
        return 'SKIP-deferred', t['deferred_reason']
    if rec is not None and not is_supported(rec):
        return 'SKIP-scope', f'{rec["id"]}: not implemented by this scalar model'
    if want_fault in MACHINE_FAULTS:
        return 'SKIP-machine', f'{want_fault}: address permissions/mapping not modeled'
    if cls == 'encoding':
        try:
            check_legality(rec, fields)
        except Fault as ex:
            return 'FAIL', f'static legality={ex.kind}, vector expects legal encoding'
        return 'PASS-encoding', ''

    width = mem_width_for(rec) if rec else 8
    before = build_state(t['input_state'], pc=vector_pc, mem_width=width)
    saved = _architectural(before)
    try:
        st, got_fault = run(word, state=before)
    except SpecificationGap as ex:
        return 'FAIL', f'SPEC-GAP: {ex}'
    except Unsupported as ex:
        # A supported instruction reaching Unsupported is a real implementation
        # gap, not permission for the validator to silently skip this case.
        return 'FAIL', str(ex)
    if _architectural(before) != saved:
        return 'FAIL', 'run mutated its input State'
    if got_fault != want_fault:
        return 'FAIL', f'fault golden={got_fault} vector={want_fault}'
    if got_fault is not None:
        if _architectural(st) != saved:
            return 'FAIL', 'fault changed architectural state (not precise)'
        bad = compare_state(st, t.get('expected_state'), width)
        if t.get('expected_pc') is not None and st.pc != _parse_int(t['expected_pc'], 48):
            bad.append('fault PC differs from explicit expected_pc')
        return ('FAIL', '; '.join(bad)) if bad else ('PASS-execution', '')

    expected = t.get('expected_state')
    if expected is None:
        raise ValueError('successful execution vector needs expected_state (possibly empty with expected_pc)')
    asserts_state = any(bool(value) for value in expected.values())
    is_swym = rec['id'] == 'swym_oiii_imm'
    if not asserts_state and t.get('expected_pc') is None and not is_swym:
        raise ValueError('successful execution vector has no observable assertion')
    bad = compare_state(st, expected, width)
    if t.get('expected_pc') is not None:
        want_pc = _parse_int(t['expected_pc'], 48)
        if st.pc_next != want_pc:
            bad.append(f'pc: golden=0x{st.pc_next:X} vector=0x{want_pc:X}')
    if st.pc != st.pc_next or (st.rb[0] & ((1 << 48) - 1)) != st.pc_next:
        bad.append('retired pc/rb0/pc_next disagree')
    if is_swym:
        # Empty expected_state for NOP means no register/memory side effects,
        # not an empty check. Check all banks plus sequential full-width rb0.
        after = _architectural(st)
        expected_nop = copy.deepcopy(saved)
        next_rb0 = (before.rb[0] + 4) & MASK64
        expected_nop['rb'][0] = next_rb0
        expected_nop['pc'] = expected_nop['pc_next'] = next_rb0 & ((1 << 48) - 1)
        if after != expected_nop:
            bad.append('swym changed state beyond sequential PC advancement')
    return ('FAIL', '; '.join(bad)) if bad else ('PASS-execution', '')


def check_vector(t, fname, idx):
    tag = f'{fname}#{idx}'
    if isinstance(t, dict):
        tag += f' {t.get("id") or "reserved"} [{t.get("class")}]'
    try:
        bucket, detail = _check_vector(t)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as ex:
        bucket, detail = 'FAIL', f'invalid vector: {ex}'
    return bucket, f'{tag} :: {detail}' if detail else ''


def main(paths=None):
    paths = sorted(VECTORS_DIR.glob('*.yaml')) if paths is None else [Path(p) for p in paths]
    buckets = dict.fromkeys(BUCKETS, 0)
    details = []
    if not paths:
        print('FAIL: no vector files selected')
        return 1
    print(f'{"file":28s} {"encoding":>8s} {"execute":>8s} {"FAIL":>5s} {"SKIP":>5s}')
    for path in paths:
        counts = dict.fromkeys(BUCKETS, 0)
        try:
            with path.open() as stream:
                vecs = yaml.safe_load(stream)
            if not isinstance(vecs, list) or not vecs:
                raise ValueError('vector file must contain a nonempty list')
        except (OSError, ValueError, yaml.YAMLError) as ex:
            buckets['FAIL'] += 1
            details.append(f'FAIL: {path}: {ex}')
            continue
        for i, t in enumerate(vecs):
            bucket, detail = check_vector(t, str(path), i)
            counts[bucket] += 1
            buckets[bucket] += 1
            if detail:
                details.append(f'[{bucket}] {detail}')
        print(f'{path.name:28s} {counts["PASS-encoding"]:8d} {counts["PASS-execution"]:8d} '
              f'{counts["FAIL"]:5d} {sum(n for k,n in counts.items() if k.startswith("SKIP")):5d}')
    print('TOTAL ' + str(sum(buckets.values())) + ': ' + ' '.join(f'{k}={v}' for k,v in buckets.items()))
    for detail in details:
        print(detail)
    if not (buckets['PASS-encoding'] + buckets['PASS-execution']):
        print('FAIL: no case was verified (empty or all skipped)')
        return 1
    return int(buckets['FAIL'] != 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', help='YAML files; default tests/vectors/isa/*.yaml')
    args = parser.parse_args()
    sys.exit(main(args.paths or None))
