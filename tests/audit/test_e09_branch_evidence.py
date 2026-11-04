"""Actual219-branch observations and source-proof controls, without execution.

The class validates the real final portable receipts once, then copies exactly
the mapper/source-proof read closure. Every semantic control first passes219,
changes one target, rebinds raw bytes/SHA, and restores the shared fixture.
Missing actual receipts are errors; no skipped or invented candidate fixtures.
"""
import base64
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_fixture_support import copy_files, record_reads, frozen_e09_root
from layout_checks import load
from validate_e08_runtime import validate_layout_receipt
from validate_e09_coverage import validate_candidate_receipt
from validate_e09_branch_evidence import (MAP, INSTALLED, COVERAGE, check_geometry_source,
                                         decode, validate_branch_evidence)

ROOT = frozen_e09_root()


def bytes_of(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


class E09ActualBranchEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        geometry, coverage = load(ROOT / INSTALLED), load(ROOT / COVERAGE)
        # These are complete current-package gates, not saved result booleans.
        validate_layout_receipt(geometry, ROOT)
        validated = validate_candidate_receipt(coverage, ROOT)
        if validated['passed'] is not True:
            raise AssertionError(validated)
        mapping = load(ROOT / MAP)
        receipts = {'geometry': geometry, 'api': geometry['apiRuntime'], 'newcoverage': coverage}
        with record_reads(ROOT) as reads:
            positive = validate_branch_evidence(mapping, receipts, ROOT)
            source = check_geometry_source(ROOT)
        if positive['passed'] is not True or positive['verifiedBranchCount'] != 219 or source['passed'] is not True:
            raise AssertionError({'branches': positive, 'geometrySource': source})
        paths = set(reads) | {MAP, INSTALLED, COVERAGE, 'tools/reference/e09_host_lifecycle_probe.py'}
        if any(name.startswith(('test-runs/', '.git/', '.local/')) or '__pycache__' in name for name in paths):
            raise AssertionError('Portable branch fixture has an external/raw-run/cache dependency')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.copy_receipt = copy_files(ROOT, cls.root, paths)
        cls.mapping = load(cls.root / MAP)
        cls.geometry = load(cls.root / INSTALLED)
        cls.coverage = load(cls.root / COVERAGE)
        cls.receipts = {'geometry': cls.geometry, 'api': cls.geometry['apiRuntime'], 'newcoverage': cls.coverage}
        cls.proof_name = 'references/e09-geometry-premise.json'
        cls.proof_original = (cls.root / cls.proof_name).read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def positive(self):
        result = validate_branch_evidence(self.mapping, self.receipts, self.root)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['verifiedBranchCount'], 219)
        self.assertEqual(result['pending'], [])
        return result

    def rejected(self, target):
        result = validate_branch_evidence(self.mapping, self.receipts, self.root)
        self.assertFalse(result['passed'], result)
        self.assertIn(target, '\n'.join(result['errors']), result)
        return result

    @contextmanager
    def raw_observation(self, role, field=None):
        receipt = self.receipts[role]
        capture = (receipt[field] if field else receipt)['captures'][0]
        original = copy.deepcopy(capture)
        observed, _ = decode(capture)
        def publish():
            raw = bytes_of(observed)
            capture['observationBytesBase64'] = base64.b64encode(raw).decode()
            capture['observationSha256'] = hashlib.sha256(raw).hexdigest()
        try:
            yield observed, publish
        finally:
            capture.clear()
            capture.update(original)

    def test_actual_portable_positive_has219_distinct_witnesses_and11_source_components(self):
        with record_reads(self.root) as reads:
            result = self.positive()
            source = check_geometry_source(self.root)
        self.assertTrue(source['passed'], source)
        self.assertEqual(source['approvedComponentCount'], 11)
        self.assertEqual(len({(r['declarationId'], r['branch']) for r in result['verified']}), 219)
        self.assertTrue(all(r['witnesses'] and all(len(w['observationSha256']) >= 3 for w in r['witnesses'])
                            for r in result['verified']))
        self.assertTrue(reads <= set(self.copy_receipt['paths']), reads - set(self.copy_receipt['paths']))
        self.assertFalse(any(name.startswith(('test-runs/', '.git/', '.local/')) for name in reads))

    def test_empty_or_recounted_mapping_cannot_shrink219_required_branches(self):
        for kind in ('empty', 'recounted'):
            with self.subTest(kind=kind):
                self.positive()
                original = copy.deepcopy(self.mapping)
                try:
                    self.mapping['rows'] = [] if kind == 'empty' else self.mapping['rows'][:-1]
                    self.mapping['requiredBranchCount'] = len(self.mapping['rows'])
                    result = self.rejected('Frozen219 branch mapping/predicate denominator differs')
                    self.assertEqual(result['pendingBranchCount'], 219)
                finally:
                    self.mapping.clear()
                    self.mapping.update(original)

    def test_missing_geometry_role_remains_pending_even_when_other_observations_pass(self):
        self.positive()
        original = self.receipts.pop('geometry')
        try:
            result = self.rejected('All three current portable receipt roles are required')
            self.assertGreater(result['pendingBranchCount'], 0)
        finally:
            self.receipts['geometry'] = original

    def test_invalid_unselected_constructor_call_requires_its_actual_good_return(self):
        self.positive()
        with self.raw_observation('api') as (value, publish):
            value['lifecycle']['publicErrors']['emptyCallReplacesBadConstructor']['children'][0]['x'] = -1000000000
            publish()
            self.rejected('Call empty mapping did not replace constructor defaults')

    def test_timeout_recovery_cannot_borrow_successful_cancellation_recovery(self):
        for kind in ('pending-slot', 'empty-trace', 'wrong-recovery-graph'):
            with self.subTest(kind=kind):
                self.positive()
                # The unrelated cancellation recovery stays genuinely valid.
                api, _ = decode(self.receipts['api']['captures'][0])
                self.assertEqual(api['lifecycle']['cpuCancel']['afterRecovery']['pending'], 0)
                with self.raw_observation('newcoverage', 'lifecycleProbe') as (value, publish):
                    running = value['runningTimeout']
                    if kind == 'pending-slot':
                        running['afterRecovery']['pending'] = 1
                        target = 'Native snapshot pending denominator differs'
                    elif kind == 'empty-trace':
                        running['recoveryTrace'] = []
                        target = 'Recovery did not execute the real complete phase chain'
                    else:
                        running['recoveryResult'] = copy.deepcopy(api['lifecycle']['cpuCancel']['recoveryResult'])
                        target = 'Recovery graph geometry failed'
                    publish()
                    self.rejected(target)

    def test_close_trace_control_requires_a_previously_published_successful_trace(self):
        self.positive()
        with self.raw_observation('newcoverage', 'lifecycleProbe') as (value, publish):
            value['registry']['closedTrace']['before'] = []
            publish()
            self.rejected('Close had no previously published successful trace')

    def test_geometry_proof_false_approval_or_rebound_span_cannot_approve_new_lemma(self):
        for kind in ('approval', 'source-span'):
            with self.subTest(kind=kind):
                self.positive()
                control = check_geometry_source(self.root)
                self.assertTrue(control['passed'], control)
                value = load(self.root / self.proof_name)
                try:
                    if kind == 'approval':
                        value['sourceApproved'] = False
                    else:
                        row = value['facts']['components'][-1]
                        raw = base64.b64decode(row['sourceBytesBase64']) + b'// altered source\n'
                        row['sourceBytesBase64'] = base64.b64encode(raw).decode()
                        row['spanSha256'] = hashlib.sha256(raw).hexdigest()
                        row['endLine'] += 1
                    (self.root / self.proof_name).write_bytes(bytes_of(value))
                    result = check_geometry_source(self.root)
                    self.assertFalse(result['passed'], result)
                    self.assertIn('Geometry fixed source facts/approval differ', '\n'.join(result['errors']))
                finally:
                    (self.root / self.proof_name).write_bytes(self.proof_original)


if __name__ == '__main__':
    unittest.main()
