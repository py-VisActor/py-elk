"""Independent fixed official facts and explicitly different native contracts."""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import validate_e08_api as api
from layout_checks import load


class E08ApiContractTests(unittest.TestCase):
    def test_all_original_requests_and_three_processes_are_bound(self):
        result=api.check();self.assertTrue(result['passed'],result)
        self.assertEqual((result['caseCount'],result['repeat'],result['actualProcesses'],result['expectedWorkerCrashProcesses']),(44,3,132,9))
        self.assertFalse(result['nativeRuntimeVerified'])

    def test_native_metadata_is_independently_bounded_and_separate_from_reference(self):
        expected=api.native_metadata_contract()
        self.assertEqual([len(expected['default'][k]) for k in ('algorithms','options','categories')],[1,9,1])
        self.assertEqual([len(expected['algorithmsEmpty'][k]) for k in ('algorithms','options','categories')],[0,9,0])
        self.assertEqual([len(load(ROOT/'references/metadata'/(k+'.json'))) for k in ('algorithms','options','categories')],[12,243,8])

    def test_same_process_accumulation_does_not_redefine_empty_native_registry(self):
        case=next(c for c in api.definitions()['cases'] if c['id']=='sequence-sequence-empty-default')
        queries=[e for e in case['expectedEvents'] if e['operation']=='knownLayoutAlgorithms']
        self.assertEqual([len(e['metadataIds']) for e in queries],[3,12,12])
        self.assertEqual(api.native_metadata_contract()['algorithmsEmpty']['algorithms'],[])

    def test_independent_repeated_validation_does_not_mutate_expected_registry(self):
        case=next(c for c in api.definitions()['cases'] if c['id']=='sequence-sequence-empty-default');before=copy.deepcopy(case)
        request=load(ROOT/api.SUITE/case['request'])
        for repeat in range(3):
            events=load(ROOT/api.SUITE/'oracle/observations'/case['id']/('repeat-'+str(repeat))/'observation.json')['events']
            api.validate_reference_events(case,request,events)
            self.assertEqual(case,before)

    def test_original_windows_and_posix_command_paths_keep_their_own_syntax(self):
        self.assertEqual(str(api.original_path(r'C:\original\checkout')/'tools/reference/capture_e08_api.cjs'),r'C:\original\checkout\tools\reference\capture_e08_api.cjs')
        self.assertEqual(str(api.original_path('/original/checkout')/'tools/reference/capture_e08_api.cjs'),'/original/checkout/tools/reference/capture_e08_api.cjs')
        with self.assertRaises(ValueError):api.original_path('relative/root')

    def test_upstream_python_progress_is_excluded_from_oracle_identity(self):
        original=load(ROOT/'UPSTREAM.json');changed=copy.deepcopy(original)
        changed['python']={'runtimeEvidence':'new-current-evidence','status':'new-host-progress'}
        changed['status']='new-progress'
        self.assertEqual(api.baseline_identity(original),api.baseline_identity(changed))
        changed['distribution']['sha256Files']['lib/elk.bundled.js']='0'*64
        self.assertNotEqual(api.baseline_identity(original),api.baseline_identity(changed))


if __name__=='__main__':unittest.main()
