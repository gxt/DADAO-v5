#!/usr/bin/env python3
"""Independent scalar oracle checks from SimRISC-00–06/08–10.

Only encoding fields come from opcodes.yaml. Expected arithmetic is calculated
here with Python integers, not model helpers, host fixed-width arithmetic,
LLVM, QEMU, or vector generators. Every applicable repository arithmetic vector
is recomputed, including signed width and truncate-toward-zero cases.
"""
import copy
from pathlib import Path
import unittest

import yaml

try:
    from . import dadao_interp_v5 as model
except ImportError:
    import dadao_interp_v5 as model

U64 = 2**64 - 1
ROOT = Path(__file__).resolve().parents[2]
RECORDS = {r['id']: r for _, _, r in model._RECORDS}


def word(iid, **fields):
    """Encode fields from the normative table; never derive expected semantics."""
    rec = RECORDS[iid]
    result = int(rec['value'], 0)
    known = {f['name'] for f in rec['fields']}
    if set(fields) - known:
        raise ValueError(f'unknown fields: {set(fields) - known}')
    for f in rec['fields']:
        if f['name'] not in fields:
            continue
        hi, lo = map(int, f['bits'][1:-1].split(':'))
        mask = (2 ** (hi - lo + 1) - 1) << lo
        result = (result & ~mask) | ((fields[f['name']] << lo) & mask)
    return result


def signed(value, width):
    value %= 2**width
    return value - 2**width if value >= 2**(width - 1) else value


def reference(base, width, sign, left, right):
    """SimRISC-04/08/09/10 arithmetic, including defined div/rem edge cases."""
    a = signed(left, width) if sign else left % 2**width
    b = signed(right, width) if sign else right % 2**width
    if base == 'add':
        result = a + b
    elif base == 'sub':
        result = a - b
    elif base == 'mul':
        result = a * b
    elif base == 'cmp':
        # SimRISC-04/08/09/10: sources are truncated to the operation width,
        # but the -1/0/1 result fills all 64 bits (no zero extension of -1).
        return ((a > b) - (a < b)) % 2**64
    elif b == 0:
        result = -1 if base == 'div' else a
    else:
        # Integer magnitudes avoid Python floor division of negatives.
        quotient, _ = divmod(abs(a), abs(b))
        quotient *= -1 if (a < 0) != (b < 0) else 1
        result = quotient if base == 'div' else a - quotient * b
    return (signed(result, width) if sign else result % 2**width) % 2**64


class ScalarSpecTests(unittest.TestCase):
    def execute(self, iid, inputs=None, pc=model.DEFAULT_PC, **fields):
        state, fault = model.run(word(iid, **fields), inputs, pc=pc)
        self.assertIsNone(fault, iid)
        return state

    def fault(self, kind, iid, inputs=None, **fields):
        instruction = word(iid, **fields)
        rec, _ = model.decode(instruction)
        before = model.build_state(inputs, mem_width=model.mem_width_for(rec))
        snapshot = copy.deepcopy(vars(before))
        after, actual = model.run(instruction, state=before)
        self.assertEqual(actual, kind)
        self.assertEqual(vars(after), snapshot)
        self.assertEqual(vars(before), snapshot)

    def test_scope_and_decode_validation(self):
        for rec in RECORDS.values():
            if rec['scope'] in ('fp', 'excluded') or rec['format'].startswith('c'):
                with self.subTest(iid=rec['id']):
                    if rec['scope'] == 'fp':
                        self.assertTrue(model.is_supported(rec))
                    else:
                        self.assertFalse(model.is_supported(rec))
                        with self.assertRaises(model.Unsupported):
                            model.run(int(rec['value'], 0))
        for invalid in (-1, 2**32, True, 1.5, '0x100000000'):
            with self.assertRaises(ValueError):
                model.decode(invalid)
        self.assertEqual(model.run('0x00000000')[1], 'UNDI')
        self.assertEqual(model.run(0, pc=3)[1], 'IALIGN')
        self.assertEqual(model.run(word('fence_ciii_cfx'), pc=3)[1], 'IALIGN')
        inputs = {'memory': [{'address': 0x1000, 'value': 0x42}]}
        failed, fault = model.run(word('ld.ub_rrii_rd', rdha=1, rbhb=2), inputs, pc=3)
        self.assertEqual(fault, 'IALIGN')
        self.assertEqual(vars(failed), vars(model.build_state(inputs, pc=3, mem_width=1)))

    def test_input_validation(self):
        self.assertEqual(model.build_state({'rd': {'rd1': '0xff', 'rd2': 255}}).rd[1:3], [255, 255])
        for inputs in ({'rd': {'rd64': 1}}, {'rd': {'rb1': 1}}, {'rd': {'rd1': -1}},
                       {'rd': {'rd1': 2**64}}, {'rd': {'rd0': 1}},
                       {'rb': {'rb0': 1}}, {'ra': {'ra0': 2**54}},
                       {'typo': {}}, {'rd': []}, {'memory': {}},
                       {'memory': [{'address': 0, 'value': 1, 'width': 2.0}]}, {'memory': [{'address': 0, 'width': 1, 'value': 2**64}]}):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                model.build_state(inputs)

    def test_arithmetic_width_sign_matrix(self):
        checks = 0
        for rec in RECORDS.values():
            mn = rec['mnemonic']
            if rec['format'] != 'orrr' or not rec['id'].endswith('_rd'):
                continue
            parts = mn.split('.')
            if len(parts) != 2:
                continue
            base, suffix = parts
            if base not in ('add', 'sub', 'mul', 'div', 'rem', 'cmp'):
                continue
            width = {'b': 8, 'w': 16, 't': 32, 'o': 64}[suffix[-1]]
            sign = suffix.startswith('s')
            values = (0, 1, 2, 3, 2**(width-1)-1, 2**(width-1),
                      2**width-1, U64, 0xFEDCBA9876543281)
            for a in values:
                for b in values:
                    with self.subTest(iid=rec['id'], a=a, b=b):
                        result = self.execute(rec['id'], {'rd': {'rd1': U64, 'rd2': a, 'rd3': b}},
                                              rdhb=1, rdhc=2, rdhd=3)
                        self.assertEqual(result.rd[1], reference(base, width, sign, a, b))
                        checks += 1
        self.assertGreater(checks, 0)
        print(f'ARITH_MATRIX checked={checks}')

    def test_repository_arithmetic_inputs_independently(self):
        # Every applicable vector input is recomputed, irrespective of its
        # stored expected_state. Other instruction families are separately tested.
        checks = 0
        for path in sorted((ROOT / 'tests/inst/base').glob('*.yaml')):
            vectors = yaml.safe_load(path.read_text())
            for vec in vectors:
                if vec.get('status', 'active') != 'active' or vec.get('expected_fault'):
                    continue
                rec = RECORDS.get(vec.get('id'))
                if rec is None or rec['format'] != 'orrr' or not rec['id'].endswith('_rd'):
                    continue
                parts = rec['mnemonic'].split('.')
                if len(parts) != 2:
                    continue
                base, suffix = parts
                if base not in ('add', 'sub', 'mul', 'div', 'rem', 'cmp'):
                    continue
                instruction = int(vec['encoding']['word'], 0)
                _, fields = model.decode(instruction)
                if fields['rdhb'] == 0:
                    continue
                inputs = vec.get('input_state') or {}
                def operand(idx):
                    return 0 if idx == 0 else int(str((inputs.get('rd') or {}).get(f'rd{idx}', 0)), 0)
                width = {'b': 8, 'w': 16, 't': 32, 'o': 64}[suffix[-1]]
                expected = reference(base, width, suffix.startswith('s'),
                                     operand(fields['rdhc']), operand(fields['rdhd']))
                actual, fault = model.run(instruction, inputs)
                with self.subTest(vector=vec['id']):
                    self.assertIsNone(fault)
                    self.assertEqual(actual.rd[fields['rdhb']], expected)
                    stored = (vec.get('expected_state') or {}).get('rd', {})
                    if f"rd{fields['rdhb']}" in stored:
                        self.assertEqual(int(stored[f"rd{fields['rdhb']}"], 0), expected)
                checks += 1
        self.assertGreater(checks, 0)
        print(f'ARITH_VECTOR_INPUTS independently_recomputed={checks}')

    def test_repository_shift_extend_inputs_independently(self):
        checks = 0
        for path in sorted((ROOT / 'tests/inst/base').glob('*.yaml')):
            for index, vec in enumerate(yaml.safe_load(path.read_text())):
                if vec.get('status', 'active') != 'active' or vec.get('expected_fault'):
                    continue
                rec = RECORDS.get(vec.get('id'))
                if rec is None or not rec['mnemonic'].startswith(('shl.', 'shr.', 'ext.')):
                    continue
                instruction = int(vec['encoding']['word'], 0)
                _, fields = model.decode(instruction)
                inputs = vec.get('input_state') or {}
                registers = inputs.get('rd') or {}
                def read(idx):
                    return 0 if idx == 0 else int(str(registers.get(f'rd{idx}', 0)), 0)
                base, suffix = rec['mnemonic'].split('.')
                width = {'b': 8, 'w': 16, 't': 32, 'o': 64}[suffix[-1]]
                amount = fields['immu6'] if rec['format'] == 'orri' else read(fields['rdhd']) % 64
                source = read(fields['rdhc'])
                with self.subTest(file=path.name, index=index, iid=vec['id']):
                    self.assertNotEqual(fields['rdhb'], 0)
                    self.assertLess(amount, width)
                    if base == 'ext':
                        expected = signed(source, amount + 1) if suffix.startswith('s') else source % 2**(amount + 1)
                    else:
                        value = signed(source, width) if suffix.startswith('s') else source % 2**width
                        shifted = value << amount if base == 'shl' else value >> amount
                        expected = signed(shifted, width) if suffix.startswith('s') else shifted % 2**width
                    expected %= 2**64
                    actual, fault = model.run(instruction, inputs)
                    self.assertIsNone(fault)
                    self.assertEqual(actual.rd[fields['rdhb']], expected)
                    stored = (vec.get('expected_state') or {}).get('rd', {})
                    if f"rd{fields['rdhb']}" in stored:
                        self.assertEqual(int(stored[f"rd{fields['rdhb']}"], 0), expected)
                checks += 1
        self.assertGreater(checks, 0)
        print(f'SHIFT_EXT_VECTOR_INPUTS independently_recomputed={checks}')

    def test_dual_destination_sources_snapshot(self):
        for iid in ('add.uo_rrrr_rd', 'add.so_rrrr_rd', 'sub.so_rrrr_rd',
                    'mul.uo_rrrr_rd', 'mul.so_rrrr_rd'):
            for a, b in ((U64, 1), (2**63, U64), (17, 23)):
                sign = '.so_' in iid
                left, right = (signed(a, 64), signed(b, 64)) if sign else (a, b)
                op = iid.split('.')[0]
                result = {'add': left + right, 'sub': left - right, 'mul': left * right}[op] % 2**128
                for hi, lo in ((2, 3), (0, 3), (2, 0)):
                    state = self.execute(iid, {'rd': {'rd2': a, 'rd3': b}}, rdha=hi, rdhb=lo, rdhc=2, rdhd=3)
                    if hi:
                        self.assertEqual(state.rd[hi], result // 2**64)
                    if lo:
                        self.assertEqual(state.rd[lo], result % 2**64)
                self.fault('ILLI', iid, rdha=0, rdhb=0)
                self.fault('ILLI', iid, rdha=1, rdhb=1)

    def test_sub_unsigned_borrow_high_half(self):
        # ADR-0049: rdHA = borrow (0/1), rdHB = (C - D) mod 2^64.
        inputs = {'rd': {'rd3': 0, 'rd4': 1}}
        borrow = self.execute('sub.uo_rrrr_rd', inputs, rdha=1, rdhb=2, rdhc=3, rdhd=4)
        self.assertEqual(borrow.rd[1:3], [1, U64])
        near = self.execute('sub.uo_rrrr_rd', {'rd': {'rd3': 5, 'rd4': 7}},
                            rdha=1, rdhb=2, rdhc=3, rdhd=4)
        self.assertEqual(near.rd[1:3], [1, U64 - 1])     # -2
        low = self.execute('sub.uo_rrrr_rd', inputs, rdha=0, rdhb=2, rdhc=3, rdhd=4)
        self.assertEqual(low.rd[2], U64)                  # high discarded
        ordinary = self.execute('sub.uo_rrrr_rd', {'rd': {'rd3': 9, 'rd4': 1}},
                                rdha=1, rdhb=2, rdhc=3, rdhd=4)
        self.assertEqual(ordinary.rd[1:3], [0, 8])
        self.fault('ILLI', 'sub.uo_rrrr_rd', inputs, rdha=1, rdhb=1, rdhc=3, rdhd=4)

    def test_wyde_and_extension(self):
        for bank in ('rd', 'rb'):
            for position in range(4):
                for mnemonic in ('set.zw', 'or.w', 'andn.w') + (('set.ow',) if bank == 'rd' else ()):
                    old = 0x123456789ABCDEF0
                    value = 0x8123
                    mask = 65535 << (16 * position)
                    inserted = value << (16 * position)
                    expected = {'set.zw': inserted, 'set.ow': (U64 ^ mask) | inserted,
                                'or.w': old | inserted, 'andn.w': old & (U64 ^ inserted)}[mnemonic]
                    st = self.execute(f'{mnemonic}_rwii_{bank}', {bank: {f'{bank}1': old}}, **{f'{bank}ha': 1, 'wpN': position, 'immu16': value})
                    self.assertEqual(getattr(st, bank)[1], expected)
        for sign in ('u', 's'):
            for fmt in ('orri', 'orrr'):
                for bit in (0, 7, 31, 63):
                    src = 2**bit | 3
                    fields = {'rdhb': 1, 'rdhc': 2}
                    fields['immu6' if fmt == 'orri' else 'rdhd'] = bit if fmt == 'orri' else 3
                    st = self.execute(f'ext.{sign}o_{fmt}_rd', {'rd': {'rd2': src, 'rd3': bit}}, **fields)
                    expected = signed(src, bit+1) % 2**64 if sign == 's' else src % 2**(bit+1)
                    self.assertEqual(st.rd[1], expected)

    def test_branches_and_conditional_assignment(self):
        for value in (0, 1, U64):
            predicates = {'n': value >= 2**63, 'nn': value < 2**63,
                          'z': value == 0, 'nz': value != 0,
                          'p': 0 < value < 2**63, 'np': value == 0 or value >= 2**63}
            for cond, taken in predicates.items():
                st = self.execute(f'br.{cond}_riii_rd', {'rd': {'rd1': value}}, rdha=1, imms18=-2)
                self.assertEqual(st.pc, model.DEFAULT_PC - 8 if taken else model.DEFAULT_PC + 4)
            for cond in ('n', 'z', 'p'):
                st = self.execute(f'cs.{cond}_rrrr_rd', {'rd': {'rd1': value, 'rd3': 7, 'rd4': 9}}, rdha=1, rdhb=2, rdhc=3, rdhd=4)
                self.assertEqual(st.rd[2], 7 if predicates[cond] else 9)
        for same in (False, True):
            inputs = {'rd': {'rd1': 1, 'rd2': 1 if same else 2, 'rd3': 7, 'rd4': 9}}
            for cond in ('eq', 'ne'):
                taken = same if cond == 'eq' else not same
                st = self.execute(f'br.{cond}_rrii_rd', inputs, rdha=1, rdhb=2, imms12=3)
                self.assertEqual(st.pc, model.DEFAULT_PC + (12 if taken else 4))
                st = self.execute(f'cs.{cond}_rrrr_rd', inputs, rdha=1, rdhb=2, rdhc=3, rdhd=4)
                self.assertEqual(st.rd[3], 9 if taken else 7)
        for value in (0, 2**48):
            for cond in ('z', 'nz'):
                st = self.execute(f'br.{cond}_riii_rb', {'rb': {'rb1': value}}, rbha=1, imms18=3)
                taken = (value == 0) if cond == 'z' else (value != 0)
                self.assertEqual(st.pc, model.DEFAULT_PC + (12 if taken else 4))

    def test_shift_matrix_and_bounds(self):
        checks = 0
        for rec in RECORDS.values():
            if not model.is_supported(rec) or not rec['mnemonic'].startswith(('shl.', 'shr.')):
                continue
            base, suffix = rec['mnemonic'].split('.')
            width = {'b': 8, 'w': 16, 't': 32, 'o': 64}[suffix[-1]]
            for source in (0, U64, 1, 2**(width-1), 0xFEDCBA9876543281):
                for amount in (0, 1, width-1):
                    fields = {'rdhb': 1, 'rdhc': 2}
                    if rec['format'] == 'orri':
                        fields['immu6'] = amount
                    else:
                        fields['rdhd'] = 3
                    st = self.execute(rec['id'], {'rd': {'rd1': U64, 'rd2': source, 'rd3': amount + 64}}, **fields)
                    value = signed(source, width) if suffix.startswith('s') else source % 2**width
                    result = value << amount if base == 'shl' else value >> amount
                    expected = (signed(result, width) if suffix.startswith('s') else result % 2**width) % 2**64
                    self.assertEqual(st.rd[1], expected)
                    checks += 1
            if width < 64:
                fields = {'rdhb': 1, 'rdhc': 2}
                fields['immu6' if rec['format'] == 'orri' else 'rdhd'] = width if rec['format'] == 'orri' else 3
                self.fault('ILLI', rec['id'], {'rd': {'rd3': width}}, **fields)
        print(f'SHIFT_MATRIX checked={checks}')

    def test_address_arithmetic_compare(self):
        inputs = {'rb': {'rb2': 2**48 + 5, 'rb3': 6}, 'rd': {'rd3': 7}}
        for iid, expected in (('add.o_orrr_bbd', 2**48+12), ('sub.o_orrr_bbd', 2**48-2)):
            st = self.execute(iid, inputs, rbhb=1, rbhc=2, rdhd=3)
            self.assertEqual(st.rb[1], expected)
        st = self.execute('sub.o_orrr_dbb', inputs, rdhb=1, rbhc=2, rbhd=3)
        self.assertEqual(st.rd[1], 2**48-1)
        st = self.execute('cmp.uo_orrr_dbb', inputs, rdhb=1, rbhc=2, rbhd=3)
        self.assertEqual(st.rd[1], 1)

    def test_register_blocks_and_ra0_sbz(self):
        for bank in ('rd', 'rb'):
            iid = f'{bank}2{bank}_orri_{bank}'
            for dst, src, count in ((1, 1, 1), (1, 2, 2), (2, 1, 2)):
                self.fault('ILLI', iid, **{f'{bank}hb': dst, f'{bank}hc': src, 'immu6': count})
        st = self.execute('rd2rb_orri_rb', {'rd': {'rd1': U64, 'rd2': 3}}, rbhb=1, rdhc=1, immu6=2)
        self.assertEqual(st.rb[1:3], [U64, 3])
        st = self.execute('rd2ra_orri_ra', {'rd': {'rd1': U64}}, rahb=0, rdhc=1, immu6=1)
        self.assertEqual(st.ra[0], 2**54-1)
        self.fault('ILLI', 'rd2ra_orri_ra', rahb=63, rdhc=1, immu6=2)
        self.fault('ILLI', 'ra2rd_orri_ra', rdhb=0, rahc=0, immu6=1)

    def test_memory_width_endian_zero_sources_and_wrap(self):
        address = 0x1000
        for suffix, width in (('b', 1), ('w', 2), ('t', 4), ('o', 8)):
            st = self.execute(f'st.{suffix}_rrii_rd', {'rb': {'rb2': 2**48+address}, 'rd': {'rd1': 0xFEDCBA9876543281}}, rdha=1, rbhb=2, imms12=0)
            self.assertEqual([st.mem[address+i] for i in range(width)], list((0xFEDCBA9876543281 % 2**(width*8)).to_bytes(width, 'big')))
            zero = self.execute(f'st.{suffix}_rrii_rd', {'rb': {'rb2': address}}, rdha=0, rbhb=2, imms12=0)
            self.assertEqual(zero.load_mem(address, width), 0)
            if width < 8:
                for sign in ('s', 'u'):
                    result = self.execute(f'ld.{sign}{suffix}_rrii_rd', {'rb': {'rb2': address}, 'memory': [{'address': address, 'width': width, 'value': 2**(width*8)-1}]}, rdha=1, rbhb=2, imms12=0)
                    self.assertEqual(result.rd[1], U64 if sign == 's' else 2**(width*8)-1)
            if width > 1:
                self.fault('MALIGN', f'st.{suffix}_rrii_rd', {'rb': {'rb2': address+1}}, rdha=1, rbhb=2, imms12=0)
        st = self.execute('st.o_rrii_rb', {'rb': {'rb2': address}}, rbha=0, rbhb=2, imms12=0)
        self.assertEqual(st.load_mem(address, 8), model.DEFAULT_PC)
        st = self.execute('st.b_rrii_rd', {'rd': {'rd1': 12}}, rdha=1, rbhb=1, imms12=-1)
        self.assertEqual(st.mem[2**48-1], 12)
        st = self.execute('ld.o_rrii_ra', {'rb': {'rb2': address}, 'memory': [{'address': address, 'value': U64}]}, raha=0, rbhb=2, imms12=0)
        self.assertEqual(st.ra[0], 2**54-1)

    def test_multi_load_address_snapshot(self):
        st = self.execute('ldm.o_rrri_rd', {'rb': {'rb1': 0x1000}, 'rd': {'rd2': 8}, 'memory': [{'address': 0x1008, 'value': 3}, {'address': 0x1010, 'value': 7}]}, rdha=2, rbhb=1, rdhc=2, immu6=2)
        self.assertEqual(st.rd[2:4], [3, 7])
        self.fault('ILLI', 'stm.o_rrri_rd', rdha=63, rbhb=1, rdhc=0, immu6=2)
        st = self.execute('stm.o_rrri_rd', {'rb': {'rb1': 0x1000}, 'rd': {'rd1': 9}}, rdha=0, rbhb=1, rdhc=0, immu6=2)
        self.assertEqual((st.load_mem(0x1000, 8), st.load_mem(0x1008, 8)), (0, 9))

    def test_full_width_pc_and_repeated_steps(self):
        full_pc = 0xABCDFFFFFFFFFFFC
        before = model.build_state({}, full_pc)
        saved = copy.deepcopy(vars(before))
        first, fault = model.run(word('swym_oiii_imm'), state=before)
        self.assertIsNone(fault)
        self.assertEqual(vars(before), saved)
        self.assertEqual((first.pc, first.rb[0], first.pc_next), (0, 0xABCE000000000000, 0))
        second, fault = model.run(word('add.si_riii_rd', rdha=1, imms18=1), state=first)
        self.assertIsNone(fault)
        self.assertEqual((second.pc, second.rb[0], second.rd[1]), (4, 0xABCE000000000004, 1))
        target = self.execute('jump_rrii_rb', {'rb': {'rb1': 0xFEDCFFFFFFFFFFFC}, 'rd': {'rd2': 8}}, rbha=1, rdhb=2, imms12=0)
        self.assertEqual((target.pc, target.rb[0]), (4, 0xFEDD000000000004))
        misaligned = self.execute('jump_rrii_rb', {'rb': {'rb1': 3}}, rbha=1, rdhb=0, imms12=0)
        faulted, fault = model.run(0, state=misaligned)
        self.assertEqual(fault, 'IALIGN')
        self.assertEqual(vars(faulted), vars(misaligned))

    def test_ras_push_cases(self):
        retaddr = model.DEFAULT_PC + 4
        def call(ra):
            return self.execute('call_iiii_ra', {'ra': ra}, imms24=2)
        empty = call({'ra63': (123 << 48) | 17})
        self.assertEqual((empty.ra[0], empty.ra[63]), (1 << 48, (1 << 48) | retaddr))
        recurse = call({'ra0': 63 << 48, 'ra63': (1 << 48) | retaddr})
        self.assertEqual((recurse.ra[0], recurse.ra[63]), (63 << 48, (2 << 48) | retaddr))
        saturated = call({'ra0': 1 << 48, 'ra63': (65535 << 48) | retaddr})
        self.assertEqual((saturated.ra[0], saturated.ra[62], saturated.ra[63]), (2 << 48, (65535 << 48) | retaddr, (1 << 48) | retaddr))
        self.fault('RASOF', 'call_iiii_ra', {'ra': {'ra0': 63 << 48, 'ra63': (1 << 48) | 99}}, imms24=2)
        spill = call({'ra0': (63 << 48) | 0x1000, 'ra1': (7 << 48) | 9, 'ra63': (1 << 48) | 99})
        self.assertEqual(spill.ra[0], (63 << 48) | 0xFF8)
        self.assertEqual(spill.load_mem(0xFF8, 8), (7 << 48) | 9)

    def test_ras_pop_cases(self):
        self.fault('RASUF', 'ret_riii_ra', {'ra': {'ra63': 1 << 48}}, rdha=0, imms18=0)
        self.fault('RASUF', 'ret_riii_ra', {'ra': {'ra0': 1 << 48, 'ra63': 12}}, rdha=1, imms18=7)
        self.fault('ILLI', 'ret_riii_ra', rdha=0, imms18=1)
        recurse = self.execute('ret_riii_ra', {'ra': {'ra0': 1 << 48, 'ra63': (2 << 48) | 0x100}}, rdha=1, imms18=-1)
        self.assertEqual((recurse.ra[0], recurse.ra[63], recurse.pc, recurse.rd[1]), (1 << 48, (1 << 48) | 0x100, 0x100, U64))
        pop = self.execute('ret_riii_ra', {'ra': {'ra0': 2 << 48, 'ra62': (3 << 48) | 0x200, 'ra63': (1 << 48) | 0x100}}, rdha=0, imms18=0)
        self.assertEqual((pop.ra[0], pop.ra[63], pop.pc), (1 << 48, (3 << 48) | 0x200, 0x100))
        for count in (0, 1, 3):
            inputs = {'ra': {'ra0': 0x1000}, 'memory': [{'address': 0x1000, 'value': (count << 48) | 0x200}]}
            if count == 0:
                self.fault('RASUF', 'ret_riii_ra', inputs, rdha=1, imms18=9)
            else:
                state = self.execute('ret_riii_ra', inputs, rdha=1, imms18=9)
                self.assertEqual(state.pc, 0x200)
                self.assertEqual(state.ra[0], 0x1008 | ((1 << 48) if count > 1 else 0))
                if count > 1:
                    self.assertEqual(state.ra[63], ((count-1) << 48) | 0x200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
