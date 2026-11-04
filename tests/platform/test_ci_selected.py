"""Bounded CI policy controls; no layout, network or full checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/iteration'))
import ci_selected


class SelectedCITests(unittest.TestCase):
    def manifest(self):
        return ci_selected.load(ROOT/'docs/iterations/E11-ci-checks.json')

    def test_documentation_only_runs_no_unrelated_commands(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(ci_selected.subprocess, 'run') as process:
            selection = ci_selected.plan(['docs/iterations/E11.md', 'docs/NEW_SESSION.md'], self.manifest())
            result = ci_selected.execute(selection, Path(folder)/'new')
            self.assertTrue(result['passed']); self.assertEqual(result['executed'], [])
            self.assertEqual(selection['commands'], []); process.assert_not_called()

    def test_explicit_ci_change_selects_one_file_with_argv_and_no_shell(self):
        selection = ci_selected.plan(['scripts/iteration/ci_selected.py'], self.manifest())
        self.assertEqual([x['id'] for x in selection['commands']], ['ci-selector'])
        self.assertEqual(selection['commands'][0]['argv'], [sys.executable, '-m', 'unittest', 'discover',
                         '-s', 'tests/platform', '-p', 'test_ci_selected.py', '-v'])
        with tempfile.TemporaryDirectory() as folder, patch.object(ci_selected.subprocess, 'run') as process:
            process.return_value = ci_selected.subprocess.CompletedProcess([], 0, b'ok', b'')
            result = ci_selected.execute(selection, Path(folder)/'new')
            self.assertTrue(result['passed']); self.assertNotIn('shell', process.call_args.kwargs)
            self.assertEqual(process.call_args.args[0], selection['commands'][0]['argv'])

    def test_unknown_mutated_or_deleted_code_stops_and_final_full_is_gated(self):
        manifest = self.manifest()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root/'known.py').write_text('previously checked')
            original_sha = ci_selected.digest(root/'known.py')
            (root/'baseline.json').write_text(json.dumps({'inputFilesSha256': {'known.py': original_sha, 'gone.py': '0'*64}}))
            manifest['savedEvidence']['path'] = 'baseline.json'
            manifest['savedEvidence']['sha256'] = ci_selected.digest(root/'baseline.json')
            previous = ci_selected.plan(['known.py'], manifest, root)
            self.assertTrue(previous['passed']); self.assertEqual(previous['commands'], [])
            self.assertEqual(previous['savedEvidenceByteRechecks'], [{'path': 'known.py', 'sha256': original_sha}])
            (root/'known.py').write_text('changed')
            for paths in (['new.py'], ['known.py'], ['gone.py'], ['tests/fixtures/new.md']):
                with self.subTest(paths=paths), patch.object(ci_selected.subprocess, 'run') as process:
                    selection = ci_selected.plan(paths, manifest, root)
                    self.assertFalse(selection['passed']); self.assertEqual(selection['unplannedPaths'], paths)
                    result = ci_selected.execute(selection, root/('out-'+str(len(paths[0]))+'-'+Path(paths[0]).name), root)
                    self.assertFalse(result['passed']); process.assert_not_called()
            for path in ('../bad.py', '/bad.py', 'C:/bad.py'):
                with self.subTest(path=path), self.assertRaises(ValueError): ci_selected.safe_path(path)
            (root/'docs').mkdir()
            states = [{'id': 'E'+str(n), 'status': 'complete' if n in (9, 10) else 'planned'}
                      for n in range(9, 22)]
            for row in states:
                if 13 <= int(row['id'][1:]) <= 19:
                    row['implementationStatus'] = 'complete'
                if row['id'] in ('E11', 'E12'):
                    row['status'] = 'waiting'
            machine = {'iterations': states, 'validationPolicy': {'featureImplementationComplete': True}}

            def gate(value, environment):
                (root/'docs/iteration-plan.json').write_text(json.dumps(value))
                ci_selected.final_ready(root, environment)

            # Publication is still waiting and acceptance has not yet run.
            # Passing the permission gate must not launch a subprocess/full.
            with patch.object(ci_selected.subprocess, 'run') as process, \
                    patch.object(ci_selected.subprocess, 'check_output') as output:
                gate(machine, {'ALL_FEATURES_COMPLETE': 'true'})
                process.assert_not_called(); output.assert_not_called()
            for environment in ({}, {'ALL_FEATURES_COMPLETE': 'false'},
                                {'ALL_FEATURES_COMPLETE': True}, {'ALL_FEATURES_COMPLETE': 'TRUE'}):
                with self.subTest(environment=environment), self.assertRaises(ValueError):
                    gate(machine, environment)
            for value in (False, None, 1, 'true'):
                invalid = copy.deepcopy(machine)
                invalid['validationPolicy']['featureImplementationComplete'] = value
                with self.subTest(flag=value), self.assertRaises(ValueError):
                    gate(invalid, {'ALL_FEATURES_COMPLETE': 'true'})
            invalid = copy.deepcopy(machine); invalid.pop('validationPolicy')
            with self.assertRaises(ValueError): gate(invalid, {'ALL_FEATURES_COMPLETE': 'true'})
            for n in (9, 10):
                invalid = copy.deepcopy(machine)
                row = next(row for row in invalid['iterations'] if row['id'] == 'E'+str(n))
                row.update(status='waiting', implementationStatus='complete')
                with self.subTest(foundation=n), self.assertRaises(ValueError):
                    gate(invalid, {'ALL_FEATURES_COMPLETE': 'true'})
            for n in range(13, 20):
                invalid = copy.deepcopy(machine)
                row = next(row for row in invalid['iterations'] if row['id'] == 'E'+str(n))
                row['implementationStatus'] = 'planned'
                with self.subTest(incompleteFeature=n), self.assertRaises(ValueError):
                    gate(invalid, {'ALL_FEATURES_COMPLETE': 'true'})
                invalid['iterations'].remove(row)
                with self.subTest(missingFeature=n), self.assertRaises(ValueError):
                    gate(invalid, {'ALL_FEATURES_COMPLETE': 'true'})
            # The older complete status remains sufficient; no publication or
            # final-acceptance rows are needed for feature readiness.
            legacy = copy.deepcopy(machine)
            legacy['iterations'] = [row for row in legacy['iterations']
                                    if row['id'] not in ('E11', 'E12', 'E20', 'E21')]
            for row in legacy['iterations']:
                row['status'] = 'complete'; row.pop('implementationStatus', None)
            gate(legacy, {'ALL_FEATURES_COMPLETE': 'true'})


if __name__ == '__main__': unittest.main()
