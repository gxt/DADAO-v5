"""Hand-derived FP oracle checks from contract-fp and SimRISC-07."""
import copy
from pathlib import Path
import unittest

import yaml

try:
    from . import dadao_interp_v5 as model
    from . import fp_ref
except ImportError:
    import dadao_interp_v5 as model
    import fp_ref

ROOT = Path(__file__).resolve().parents[2]
RECORDS = {r['id']: r for _, _, r in model._RECORDS}


def word(iid, **fields):
    rec = RECORDS[iid]
    value = int(rec['value'], 0)
    for fld in rec['fields']:
        if fld['name'] not in fields:
            continue
        hi, lo = map(int, fld['bits'][1:-1].split(':'))
        mask = ((1 << (hi - lo + 1)) - 1) << lo
        value = (value & ~mask) | ((fields[fld['name']] << lo) & mask)
    return value


class FloatingGoldenTests(unittest.TestCase):
    def execute(self, iid, state=None, **fields):
        st, fault = model.run(word(iid, **fields), state or {})
        self.assertIsNone(fault, iid)
        return st

    def test_all_fp_records_are_supported_and_documented(self):
        fp_records = [r for _, _, r in model._RECORDS if r.get('scope') == 'fp']
        self.assertEqual(len(fp_records), 66)
        self.assertTrue(all(model.is_supported(r) for r in fp_records))
        reference = (ROOT / 'components/golden/INSTRUCTION_REFERENCE.md').read_text()
        for rec in fp_records:
            self.assertIn(rec['id'], reference)
            self.assertIn('伪代码（唯一执行顺序）', reference)

    def test_every_fp_identity_executes_a_contract_valid_smoke(self):
        checked = 0
        for rec in [r for _, _, r in model._RECORDS if r.get('scope') == 'fp']:
            fields = {}
            for fld in rec['fields']:
                name = fld['name']
                if name == 'rfha': fields[name] = 1
                elif name == 'rfhb': fields[name] = 3 if rec['mnemonic'].startswith('cs.') else 1
                elif name == 'rfhc': fields[name] = 2
                elif name == 'rfhd': fields[name] = 3
                elif name == 'rdha': fields[name] = 1
                elif name == 'rdhb': fields[name] = 2
                elif name == 'rdhc': fields[name] = 3
                elif name == 'rdhd': fields[name] = 4
                elif name == 'wpN': fields[name] = 0
                elif name == 'immu16': fields[name] = 0
                elif name == 'imms12': fields[name] = 0
                elif name == 'immu6': fields[name] = 2 if rec['mnemonic'] in ('ftroot', 'foroot') else 1
                elif name == 'rbhb': fields[name] = 1
            if rec['mnemonic'] in ('ldm.t', 'stm.t', 'ldm.o', 'stm.o'):
                fields['rdhc'] = 0
            inputs = {'rd': {'rd1': 1, 'rd2': 2, 'rd3': 3, 'rd4': 4},
                      'rb': {'rb1': 0x1000}, 'rf': {'rf1': 0, 'rf2': 0, 'rf3': 0}}
            with self.subTest(iid=rec['id']):
                after, fault = model.run(word(rec['id'], **fields), inputs)
                self.assertIsNone(fault)
                self.assertIsInstance(after, model.State)
            checked += 1
        self.assertEqual(checked, 66)

    def test_binary32_arithmetic_and_rounding_modes(self):
        st = self.execute('ftadd_orrr_rf', {'rf': {'rf1': 0x3F800000, 'rf2': 0x40000000}},
                          rfhb=3, rfhc=1, rfhd=2)
        self.assertEqual(st.rf[3] & 0xFFFFFFFF, 0x40400000)
        self.assertEqual(st.rf[0] & 0x1F, 0)
        one = 0x3F800000
        half_ulp = 0x33800000
        rne = self.execute('ftadd_orrr_rf', {'rf': {'rf0': 0x7FF800007FC00000,
                                                     'rf1': one, 'rf2': half_ulp}},
                           rfhb=3, rfhc=1, rfhd=2)
        rup = self.execute('ftadd_orrr_rf', {'rf': {'rf0': 0x7FF800037FC00000,
                                                     'rf1': one, 'rf2': half_ulp}},
                           rfhb=3, rfhc=1, rfhd=2)
        self.assertEqual(rne.rf[3] & 0xFFFFFFFF, one)
        self.assertEqual(rup.rf[3] & 0xFFFFFFFF, one + 1)
        self.assertEqual(rne.rf[0] & 0x1F, fp_ref.NX)
        self.assertEqual(rup.rf[0] & 0x1F, fp_ref.NX)

    def test_binary64_arithmetic_special_values_and_accrued_flags(self):
        st = self.execute('fodiv_orrr_rf', {'rf': {'rf0': 0x7FF8000000000004,
                                                    'rf1': 0x3FF0000000000000,
                                                    'rf2': 0}},
                           rfhb=3, rfhc=1, rfhd=2)
        self.assertEqual(st.rf[3], 0x7FF0000000000000)
        self.assertEqual(st.rf[0] & 0x1F, 0x6)
        # Division by zero adds DZ but preserves previously accrued NV.
        st = self.execute('fodiv_orrr_rf', {'rf': {'rf0': 0x7FF8000000000001,
                                                    'rf1': 0x3FF0000000000000,
                                                    'rf2': 0}},
                           rfhb=3, rfhc=1, rfhd=2)
        self.assertEqual(st.rf[0] & 0x1F, 0x3)

    def test_sign_classify_compare_and_integer_transfer(self):
        st = self.execute('ftsgnn_orrr_rf', {'rf': {'rf1': 0x3F800000,
                                                     'rf2': 0x80000000}},
                           rfhb=3, rfhc=1, rfhd=2)
        self.assertEqual(st.rf[3] & 0xFFFFFFFF, 0x3F800000)
        cls = self.execute('ftcls_orri_rf', {'rf': {'rf1': 0x80000000}},
                           rdhb=2, rfhc=1, immu6=1)
        self.assertEqual(cls.rd[2], 1 << 3)
        cmp = self.execute('ftqcmp_orrr_rf', {'rf': {'rf1': 0x7FC00000,
                                                      'rf2': 0x3F800000}},
                           rdhb=4, rfhc=1, rfhd=2)
        self.assertEqual(cmp.rd[4], fp_ref.F32.canonical_qnan)
        to_int = self.execute('ft2it_orri_rf', {'rf': {'rf1': 0xC1000000}},
                              rdhb=5, rfhc=1, immu6=1)
        self.assertEqual(to_int.rd[5], (1 << 64) - 8)
        from_int = self.execute('it2ft_orri_rf', {'rd': {'rd1': 16777217}},
                                rfhb=6, rdhc=1, immu6=1)
        self.assertEqual(from_int.rf[6] & 0xFFFFFFFF, 0x4B800000)
        self.assertEqual(from_int.rf[0] & 0x1F, fp_ref.NX)

    def test_fp_gap_and_legality_are_precise(self):
        for iid, fields in [('ftroot_orri_rf', {'rfhb': 3, 'rfhc': 1, 'immu6': 1}),
                            ('ft2ft_orri_rf', {'rfhb': 4, 'rfhc': 4, 'immu6': 1})]:
            _, fault = model.run(word(iid, **fields), {'rf': {'rf1': 0}})
            self.assertEqual(fault, 'ILLI')
        before = model.build_state({'rf': {'rf1': 0x80000000}})
        saved = copy.deepcopy(vars(before))
        with self.assertRaises(model.SpecificationGap):
            model.run(word('ftroot_orri_rf', rfhb=3, rfhc=1, immu6=2), state=before)
        self.assertEqual(vars(before), saved)
        with self.assertRaises(fp_ref.FPGap):
            fp_ref.convert_to_int(0x3FC00000, fp_ref.F32, 32, True, 0)

    def test_rf_memory_transfer_and_fcsr_mask(self):
        state = {'rb': {'rb2': 0x1000}, 'memory': [{'address': 0x1000, 'value': 0x3F800000, 'width': 4}]}
        st = self.execute('ld.t_rrii_rf', state, rfha=3, rbhb=2, imms12=0)
        self.assertEqual(st.rf[3] & 0xFFFFFFFF, 0x3F800000)
        moved = self.execute('rd2rf_orri_rf', {'rd': {'rd1': 0x100000010}},
                             rfhb=0, rdhc=1, immu6=1)
        self.assertEqual(moved.rf[0] & 0x1F, 0x10)
        self.assertEqual(moved.rf[0] >> 32 & 3, 1)
        self.assertEqual(moved.rf[0] & (0x7FF8000000000000 | 0x000000007FC00000),
                         0x7FF800007FC00000)


    def test_fma_single_rounding_counterexample(self):
        """contract-fp §20 / SimRISC-07 §2.5: the product is not pre-rounded."""
        st = self.execute('ftfma_rrrr_rf',
                          {'rf': {'rf2': 0x3F800001, 'rf3': 0x3F7FFFFE,
                                  'rf4': 0xBF800000}},
                          rfha=1, rfhb=2, rfhc=3, rfhd=4)
        self.assertEqual(st.rf[1] & 0xFFFFFFFF, 0xA8800000)   # -2**-46
        self.assertEqual(st.rf[0] & 0x1F, 0)
        # mul then add rounds the product and loses the difference.
        mul = self.execute('ftmul_orrr_rf',
                           {'rf': {'rf2': 0x3F800001, 'rf3': 0x3F7FFFFE}},
                           rfhb=1, rfhc=2, rfhd=3)
        add = self.execute('ftadd_orrr_rf',
                           {'rf': {'rf1': mul.rf[1], 'rf4': 0xBF800000}},
                           rfhb=5, rfhc=1, rfhd=4)
        self.assertEqual(add.rf[5] & 0xFFFFFFFF, 0)
        # 0 x Inf is invalid even when the addend is a qNaN.
        st = self.execute('ftfma_rrrr_rf',
                          {'rf': {'rf2': 0, 'rf3': 0x7F800000, 'rf4': 0x7FC00000}},
                          rfha=1, rfhb=2, rfhc=3, rfhd=4)
        self.assertEqual((st.rf[1] & 0xFFFFFFFF, st.rf[0] & 0x1F),
                         (0x7FC00000, fp_ref.NV))
        # Exact zero follows IEEE 754 §6.3: -0 under RDN, +0 otherwise.
        st = self.execute('ftfma_rrrr_rf',
                          {'rf': {'rf0': 2 << 32, 'rf2': 0x3F800000,
                                  'rf3': 0x3F800000, 'rf4': 0xBF800000}},
                          rfha=1, rfhb=2, rfhc=3, rfhd=4)
        self.assertEqual(st.rf[1] & 0xFFFFFFFF, 0x80000000)

    def test_round_to_integral_selectors_and_nexact(self):
        """contract-fp §18: one-hot selector; only 0x20 may set NX."""
        cases = [(0x01, 0x3FC00000, 0x40000000, 0), (0x02, 0x3FC00000, 0x40000000, 0),
                 (0x04, 0x3FC00000, 0x3F800000, 0), (0x08, 0x3FC00000, 0x40000000, 0),
                 (0x10, 0x3FC00000, 0x3F800000, 0),
                 (0x20, 0x3FC00000, 0x40000000, fp_ref.NX)]
        for sel, src, expected, flags in cases:
            with self.subTest(sel=sel):
                st = self.execute('ftrnd_orri_rf', {'rf': {'rf2': src}},
                                  rfhb=1, rfhc=2, immu6=sel)
                self.assertEqual(st.rf[1] & 0xFFFFFFFF, expected)
                self.assertEqual(st.rf[0] & 0x1F, flags)
        # trunc(-0.5) keeps the input sign; |x| >= 2**p is unchanged.
        st = self.execute('ftrnd_orri_rf', {'rf': {'rf2': 0xBF000000}},
                          rfhb=1, rfhc=2, immu6=0x04)
        self.assertEqual(st.rf[1] & 0xFFFFFFFF, 0x80000000)
        st = self.execute('ftrnd_orri_rf', {'rf': {'rf2': 0x4B800000}},
                          rfhb=1, rfhc=2, immu6=0x10)
        self.assertEqual(st.rf[1] & 0xFFFFFFFF, 0x4B800000)
        _, fault = model.run(word('ftrnd_orri_rf', rfhb=1, rfhc=2, immu6=0x03),
                             {'rf': {'rf2': 0}})
        self.assertEqual(fault, 'ILLI')

    def test_minmax_nan_zeros_and_order(self):
        """contract-fp §19: strict minimumNumber/maximumNumber."""
        zeros = {'rf2': 0x00000000, 'rf3': 0x80000000}
        st = self.execute('ftmin_orrr_rf', {'rf': zeros}, rfhb=1, rfhc=2, rfhd=3)
        self.assertEqual(st.rf[1] & 0xFFFFFFFF, 0x80000000)
        st = self.execute('ftmax_orrr_rf', {'rf': zeros}, rfhb=1, rfhc=2, rfhd=3)
        self.assertEqual(st.rf[1] & 0xFFFFFFFF, 0)
        # One NaN returns the number; sNaN still raises NV.
        st = self.execute('ftmin_orrr_rf',
                          {'rf': {'rf2': 0x7FC00000, 'rf3': 0x3F800000}},
                          rfhb=1, rfhc=2, rfhd=3)
        self.assertEqual((st.rf[1] & 0xFFFFFFFF, st.rf[0] & 0x1F),
                         (0x3F800000, 0))
        st = self.execute('ftmin_orrr_rf',
                          {'rf': {'rf2': 0x7F800001, 'rf3': 0x3F800000}},
                          rfhb=1, rfhc=2, rfhd=3)
        self.assertEqual((st.rf[1] & 0xFFFFFFFF, st.rf[0] & 0x1F),
                         (0x3F800000, fp_ref.NV))
        st = self.execute('fomin_orrr_rf',
                          {'rf': {'rf2': 0x7FF8000000000000,
                                  'rf3': 0x7FF0000000000001}},
                          rfhb=1, rfhc=2, rfhd=3)
        self.assertEqual((st.rf[1], st.rf[0] & 0x1F),
                         (fp_ref.F64.canonical_qnan, fp_ref.NV))


if __name__ == '__main__':
    unittest.main(verbosity=2)
