"""Historical E10 protocol controls on its authenticated original platform cell."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import e10
sys.path.insert(0,str(ROOT/'tests/audit'))
from audit_fixture_support import frozen_e09_root
ROOT=frozen_e09_root()


class E10PlatformValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cell=e10.load(ROOT/'references/e10/windows-3.13.json')

    def positive(self):
        result=e10.validate_cell(self.cell,root=ROOT)
        self.assertTrue(result['passed'],result['errors'])
        self.assertEqual(result['caseCount'],6)
        self.assertFalse(result['fullValidation'])

    def raw_mutation(self,mutate):
        self.positive();cell=copy.deepcopy(self.cell)
        observation=e10.embedded_json(base64.b64decode(cell['observationBytesBase64']))
        mutate(observation)
        raw=(json.dumps(observation,ensure_ascii=False,indent=2)+'\n').encode()
        cell['observationBytesBase64']=base64.b64encode(raw).decode()
        cell['observationSha256']=hashlib.sha256(raw).hexdigest()
        result=e10.validate_cell(cell,root=ROOT)
        self.assertFalse(result['passed'])
        self.assertTrue(result['errors'])
        self.positive()

    def test_actual_minor_cannot_be_relabelled_as_another_matrix_cell(self):
        self.positive();cell=copy.deepcopy(self.cell);cell['pythonMinor']='3.11'
        result=e10.validate_cell(cell,root=ROOT)
        self.assertFalse(result['passed']);self.assertIn('CPython minor',' '.join(result['errors']))
        for field in ('minor','os'):
            cell=copy.deepcopy(self.cell)
            observation=e10.embedded_json(base64.b64decode(cell['observationBytesBase64']))
            engines=[observation['engine'],*[row['observation']['engine'] for row in observation['cases']]]
            if field=='minor':
                cell.update(pythonMinor='3.11',id='windows-cpython-3.11')
                for engine in engines:engine['versionInfo'][:2]=[3,11]
            else:
                cell.update(os='Linux',id='linux-cpython-3.13')
                for engine in engines:engine['platform']['system']='Linux'
            raw=json.dumps(observation,indent=2).encode()
            cell.update(observationBytesBase64=base64.b64encode(raw).decode(),observationSha256=hashlib.sha256(raw).hexdigest())
            result=e10.validate_cell(cell,root=ROOT)
            self.assertFalse(result['passed'],field);self.assertTrue(result['errors'])
        self.positive()

    def test_changed_installed_runtime_bytes_are_rejected_after_raw_sha_rebinding(self):
        self.raw_mutation(lambda value:value['installed']['packageFilesSha256'].__setitem__('api.py','0'*64))
        cell=copy.deepcopy(self.cell);cell['installation'].update(artifactKind='sdist',artifactSha256=e10.SDIST_SHA)
        result=e10.validate_cell(cell,root=ROOT)
        self.assertFalse(result['passed']);self.assertTrue(result['errors'])

    def test_corrupted_geometry_is_recomputed_from_original_request_and_oracle(self):
        self.raw_mutation(lambda value:value['cases'][1]['observation']['result']['children'][0].__setitem__('x',-1000))

    def test_wrong_process_and_incomplete_matrix_do_not_claim_eight_platforms(self):
        self.positive();cell=copy.deepcopy(self.cell);cell['command']['pid']=cell['launcherPid']
        self.assertFalse(e10.validate_cell(cell,root=ROOT)['passed'])
        result=e10.validate_matrix([self.cell],root=ROOT)
        self.assertFalse(result['passed']);self.assertEqual(result['expectedCells'],8)
        self.assertEqual(result['measuredPassedCells'],1)
        self.assertIn('eight distinct',' '.join(result['errors']))

if __name__=='__main__':unittest.main()
