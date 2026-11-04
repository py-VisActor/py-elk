"""Historical accounting controls on the authenticated original E10 samples."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import e10_benchmark
sys.path.insert(0,str(ROOT/'tests/audit'))
from audit_fixture_support import frozen_e09_root
ROOT=frozen_e09_root()


class PublicBenchmarkReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=e10_benchmark.e10.load(ROOT/'references/e10-benchmark.json')

    def test_real_public_samples_recompute_without_launching_layout(self):
        result=e10_benchmark.validate(self.receipt,root=ROOT)
        self.assertTrue(result['passed'],result['errors'])
        self.assertEqual((result['captures'],result['warmups'],result['measuredSamples']),(18,3,15))
        self.assertFalse(result['fullValidation'])
        self.assertFalse(result['runtimeReexecuted'])
        for case in result['statistics'].values():
            self.assertEqual(case['publicElapsedSeconds']['p95NearestRank'],case['publicElapsedSeconds']['maximum'])

    def test_raw_rebinding_cannot_hide_wrong_usage_geometry_or_missing_samples(self):
        positive=e10_benchmark.validate(self.receipt,root=ROOT)
        self.assertTrue(positive['passed'],positive['errors'])
        def bad_metric(v):v['metrics']['workerPeakRssBytes']+=v['metrics']['parentPeakRssBytes']
        def reused_driver(v):v['usage']['childrenBefore']['ru_utime']=.1
        def bad_geometry(v):v['result']['children'][0]['x']=-1000
        def untyped_pid(v):
            v['worker']['pid']=True
            v['worker']['snapshotAfterReturn']['jobs'][0]['pid']=True
        for mutate in (bad_metric,reused_driver,bad_geometry,untyped_pid):
            with self.subTest(mutation=mutate.__name__):
                value=copy.deepcopy(self.receipt);row=value['captures'][1]
                observation=json.loads(base64.b64decode(row['observationBytesBase64']))
                mutate(observation);raw=(json.dumps(observation)+'\n').encode()
                row['observationBytesBase64']=base64.b64encode(raw).decode()
                row['observationSha256']=hashlib.sha256(raw).hexdigest()
                self.assertFalse(e10_benchmark.validate(value,root=ROOT)['passed'])
        value=copy.deepcopy(self.receipt);value['captures'].pop()
        self.assertFalse(e10_benchmark.validate(value,root=ROOT)['passed'])


if __name__=='__main__':unittest.main()
