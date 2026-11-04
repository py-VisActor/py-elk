"""Fixed official coverage membership and original-only regression premises."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from layout_checks import load
from build_e09_suite import check, definitions, host_definitions, math_request
from e07_geometry_premise import premises
from validate_e09_coverage import RECORD, verify_reference, numeric_reference, decode_capture, logs_of


class E09CoverageTests(unittest.TestCase):
    def test_all_25_original_master_requests_and_144_cases_are_reproducible(self):
        result=check();self.assertEqual(result['caseCount'],144);self.assertEqual(result['masterCount'],25)
        suite,raws=definitions();masters=[x for x in suite['cases'] if x['origin']=='master-original']
        self.assertEqual(len(masters),25)
        self.assertEqual(sum(x['expectedOutcome']=='threw' for x in masters),3)
        self.assertEqual(suite['fullReferenceCounts'],{'algorithms':12,'options':243,'categories':8})
        for name,count in (('algorithms',12),('options',243),('categories',8)):
            self.assertEqual(len(load(ROOT/'references/metadata'/ (name+'.json'))),count)
        for case in suite['cases']:
            if case['origin']!='fixed-lcg-0xE0900001':continue
            request=load(ROOT/'tests/fixtures/suites/E09'/case['request'])
            with self.subTest(case=case['id']):
                self.assertLessEqual(len(request['graph']['children']),8)
                self.assertLessEqual(len(request['graph']['edges']),28)
                self.assertIsNotNone(premises(math_request(request)))

    def test_actual_three_process_official_facts_and_real_bk_witnesses_validate(self):
        value=load(ROOT/RECORD);result=verify_reference(value)
        self.assertIs(result['passed'],True);self.assertEqual(result['repeat'],3)
        self.assertTrue(result['bkNonemptyMarkedWitness']);self.assertTrue(result['bkInfeasibleWitness'])
        self.assertGreater(result['nonzeroMeasuredLeafCount'],0)
        by_id={x['definition']['id']:x for x in value['cases']}
        self.assertIn('Marked edges: [e_root.e7 0[n_root.n1] -> 2[n_root.n4]]',logs_of(decode_capture(by_id['generated-07']['captures'][0])))
        self.assertIn('bk node placement breaks on n_root.n5 which should have been after n_root.n1',logs_of(decode_capture(by_id['generated-04']['captures'][0])))

    def test_number_oracle_preserves_all_fixed_original_bits_and_three_real_repeats(self):
        rows=numeric_reference();self.assertEqual(len(rows),298)
        self.assertIn({'bitsHex':'8000000000000000','string':'0'},[{k:r[k] for k in ('bitsHex','string')} for r in rows])
        self.assertEqual(len(host_definitions()['publicCases']),52)

if __name__=='__main__':unittest.main()
