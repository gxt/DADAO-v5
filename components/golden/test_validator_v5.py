#!/usr/bin/env python3
"""Adversarial checks for the vector runner; fixtures use SimRISC-04/12 words."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

import dadao_interp_v5 as model
import validate_interp_v5 as validator


def addition():
    # SimRISC-04: add.uo {rd1,rd2},rd3,rd4; hi=0, lo=3+4.
    return dict(id='add.uo_rrrr_rd', mnemonic='add.uo', format='rrrr',
                encoding={'word': '0x500420C4'}, **{'class': 'semantic'},
                input_state={'rd': {'rd3': '0x3', 'rd4': '0x4'}},
                expected_state={'rd': {'rd1': '0x0', 'rd2': '0x7'}},
                expected_fault=None, expected_pc=None, status='active',
                spec_cite='SimRISC-04 §3.1')


class ValidatorTests(unittest.TestCase):
    def verdict(self, case):
        return validator.check_vector(case, 'synthetic', 0)[0]

    def test_correct_execution(self):
        self.assertEqual(self.verdict(addition()), 'PASS-execution')

    def test_wrong_expected_result(self):
        case = addition()
        case['expected_state']['rd']['rd2'] = '0x8'
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_wrong_identity_or_word(self):
        for key, value in [('id', 'sub.uo_rrrr_rd'), ('mnemonic', 'sub.uo'), ('format', 'orrr')]:
            with self.subTest(key=key):
                case = addition(); case[key] = value
                self.assertEqual(self.verdict(case), 'FAIL')
        case = addition(); case['encoding']['word'] = '0x510420C4'
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_wrong_encoding_identity(self):
        case = addition(); case['class'] = 'encoding'; case['expected_state'] = None
        self.assertEqual(self.verdict(case), 'PASS-encoding')
        case['id'] = 'add.so_rrrr_rd'
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_wrong_fault_and_pc(self):
        case = addition(); case['expected_fault'] = 'ILLI'
        self.assertEqual(self.verdict(case), 'FAIL')
        case = addition(); case['expected_pc'] = '0xFC0000000008'
        self.assertEqual(self.verdict(case), 'FAIL')
        case['expected_pc'] = '0xFC0000000004'
        self.assertEqual(self.verdict(case), 'PASS-execution')

    def test_illegal_encoding(self):
        case = addition(); case['encoding']['word'] = '0x50000000'
        case['class'] = 'encoding'; case['expected_state'] = None
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_precise_fault_cannot_hide_state_damage(self):
        case = addition(); case['encoding']['word'] = '0x50000000'
        case['class'] = 'legality'; case['expected_state'] = None
        case['expected_fault'] = 'ILLI'
        self.assertEqual(self.verdict(case), 'PASS-execution')
        def broken_run(word, state):
            damaged = copy.deepcopy(state); damaged.rd[3] = 0xBAD
            return damaged, 'ILLI'
        with patch.object(validator, 'run', broken_run):
            self.assertEqual(self.verdict(case), 'FAIL')

    def test_fault_explicit_assertions_are_not_ignored(self):
        case = addition(); case['encoding']['word'] = '0x50000000'
        case['expected_fault'] = 'ILLI'
        case['expected_state'] = {'rd': {'rd3': '0x3'}}
        case['expected_pc'] = '0xFC0000000000'
        self.assertEqual(self.verdict(case), 'PASS-execution')
        case['expected_state']['rd']['rd3'] = '0xBAD'
        self.assertEqual(self.verdict(case), 'FAIL')
        case['expected_state']['rd']['rd3'] = '0x3'
        case['expected_pc'] = '0x1'
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_input_state_mutation_detected(self):
        real = model.run
        def broken_run(word, state):
            out = real(word, state=state)
            state.rd[9] = 123
            return out
        with patch.object(validator, 'run', broken_run):
            self.assertEqual(self.verdict(addition()), 'FAIL')

    def test_swym_empty_state_means_no_side_effect(self):
        case = dict(id='swym_oiii_imm', mnemonic='swym', format='oiii',
                    encoding={'word': '0x47880000'}, **{'class': 'semantic'},
                    input_state={}, expected_state={}, expected_fault=None,
                    spec_cite='SimRISC-11: 占位指令')
        self.assertEqual(self.verdict(case), 'PASS-execution')
        real = model.run
        def broken_run(word, state):
            st, fault = real(word, state=state); st.rd[10] = 1
            return st, fault
        with patch.object(validator, 'run', broken_run):
            self.assertEqual(self.verdict(case), 'FAIL')

    def test_success_without_observation_fails(self):
        case = addition(); case['expected_state'] = {}
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_active_reason_cannot_turn_failure_into_skip(self):
        case = addition(); case['deferred_reason'] = 'hide failure'
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_deferred_and_scope_explicit(self):
        case = addition(); case['status'] = 'deferred'
        case['deferred_reason'] = 'unsettled'; case['expected_state'] = None
        self.assertEqual(self.verdict(case), 'SKIP-deferred')
        # Defined fence is outside this scalar model, regardless of machine ILLI.
        case = dict(id='fence_ciii_cfx', mnemonic='fence', format='ciii',
                    encoding={'word': '0x79000000'}, **{'class': 'encoding'},
                    input_state={}, expected_state=None, expected_fault=None,
                    spec_cite='SimRISC-11: fence')
        rec, _ = model.decode(0x79000000)
        self.assertEqual(rec['id'], case['id'])
        self.assertEqual(self.verdict(case), 'SKIP-scope')

    def test_unknown_class_status_fault_or_state_fails(self):
        for key, value in [('class', 'semantci'), ('status', 'unknown'),
                           ('expected_fault', 'FAKE'), ('expected_state', {'rdd': {'rd1': '0x0'}})]:
            with self.subTest(key=key):
                case = addition(); case[key] = value
                self.assertEqual(self.verdict(case), 'FAIL')
        for name in ['rd64', 'rd-1', 'rb1', 'rd0', 'rd01']:
            with self.subTest(name=name):
                case = addition(); case['expected_state'] = {'rd': {name: '0x0'}}
                self.assertEqual(self.verdict(case), 'FAIL')

    def test_encoding_input_state_is_validated(self):
        case = addition(); case['class'] = 'encoding'; case['expected_state'] = None
        case['input_state'] = {'ra': {'ra0': '0xffffffffffffffff'}}
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_out_of_range_assertion_not_masked(self):
        case = addition(); case['expected_state']['rd']['rd2'] = (1 << 64) + 7
        self.assertEqual(self.verdict(case), 'FAIL')
        for value in [-1, 1 << 32, True]:
            case = addition(); case['encoding']['word'] = value
            self.assertEqual(self.verdict(case), 'FAIL')

    def test_machine_fault_is_skip_not_pass(self):
        case = addition(); case['class'] = 'legality'; case['expected_state'] = None
        for fault in ('UNMAPPED', 'CFXMEM'):
            case['expected_fault'] = fault
            self.assertEqual(self.verdict(case), 'SKIP-machine')

    def test_reserved_identity_is_checked(self):
        case = dict(id=None, mnemonic=None, format=None, encoding={'word': '0x00000000', 'reserved': True},
                    **{'class': 'legality'}, input_state={}, expected_state=None,
                    expected_fault='UNDI', spec_cite='SimRISC-00 §QFC')
        self.assertEqual(self.verdict(case), 'PASS-execution')
        case['encoding']['word'] = '0x500420C4'
        self.assertEqual(self.verdict(case), 'FAIL')

    def test_cli_empty_invalid_all_skipped_and_real_failure(self):
        root = Path('/tmp/opencode/GOLDEN-001t'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp, contextlib.redirect_stdout(io.StringIO()):
            p = Path(tmp) / 'vectors.yaml'
            self.assertEqual(validator.main([]), 1)
            self.assertEqual(validator.main([p]), 1)
            for content in ['', '[]', '{}', '[bad', '- null']:
                p.write_text(content)
                self.assertEqual(validator.main([p]), 1)
            case = addition(); case['status'] = 'deferred'; case['deferred_reason'] = 'pending'
            case['expected_state'] = None
            p.write_text(yaml.safe_dump([case])); self.assertEqual(validator.main([p]), 1)
            p.write_text(yaml.safe_dump([addition()])); self.assertEqual(validator.main([p]), 0)
            case = addition(); case['expected_state']['rd']['rd2'] = '0xBAD'
            p.write_text(yaml.safe_dump([case])); self.assertEqual(validator.main([p]), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
