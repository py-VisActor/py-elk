"""Current explicit CI rules and exact frozen-byte fallback; no product execution."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import ci_selected


class FullNativeCIPlanTests(unittest.TestCase):
    def manifest(self):
        return ci_selected.load(ROOT/'docs/iterations/full-native-ci-checks.json')

    def selected(self,paths):
        selection=ci_selected.plan(paths,self.manifest())
        self.assertTrue(selection['passed'],selection['unplannedPaths'])
        self.assertIs(selection['fullValidation'],False)
        self.assertIs(selection['impactExhaustivenessProven'],False)
        return {row['id']for row in selection['commands']},selection

    def test_current_sources_and_release_paths_select_real_checks_not_e11_ast_gate(self):
        for name in('src/pyelk/algorithms/fixed.py','src/pyelk/execution/json_transfer.py',
                    'src/pyelk/execution/full_worker.py','src/pyelk/api.py'):
            with self.subTest(path=name):
                names,selection=self.selected([name])
                self.assertLessEqual({'native-imports','native-host'},names)
                self.assertNotIn('release-source',names)
                self.assertFalse(any('e11_package.py'in row['argv']for row in selection['commands']))
        for name in('.gitattributes','.github/workflows/publish-pypi.yml',
                    'docs/releases/0.1.0-readiness.json','docs/releases/evidence/0.1.0-delta.json',
                    'scripts/iteration/release_readiness.py'):
            with self.subTest(path=name):
                names,selection=self.selected([name]);self.assertIn('release-readiness',names)
                command=next(row['argv']for row in selection['commands']if row['id']=='release-readiness')
                self.assertEqual(command,[sys.executable,'scripts/iteration/release_readiness.py','--source-only'])
        names,_=self.selected(['docs/implementation-backlog.json',
                              'docs/changes/20261104-next-native-19-validation.json'])
        self.assertLessEqual({'release-readiness','completion-metadata'},names)
        names,selection=self.selected(['scripts/validate_full_performance.py','tests/platform/test_full_performance.py'])
        self.assertEqual(names,{'performance-plan','performance-owner'})
        command=next(row['argv']for row in selection['commands']if row['id']=='performance-plan')
        self.assertEqual(command,[sys.executable,'scripts/validate_full_performance.py','--plan-only'])
        names,_=self.selected(['scripts/advanced_geometry.py','tests/fixtures/suites/full-option-effects/geometry-frames/manifest.json'])
        self.assertLessEqual({'advanced-geometry'},names)
        names,selection=self.selected(['scripts/validate_option_effects.py','tests/fixtures/suites/full-option-effects/protocol-saved/cases.json'])
        self.assertEqual(names,{'option-effects-saved','advanced-geometry'})
        command=next(row['argv']for row in selection['commands']if row['id']=='option-effects-saved')
        self.assertNotIn('--capture',command);self.assertIn('tests/fixtures/suites/full-option-effects/protocol-saved/reference',command)
        names,selection=self.selected(['scripts/iteration/option_coverage.py','docs/option-coverage.json'])
        self.assertEqual(names,{'option-coverage-structure','option-evidence-restore','option-evidence-strict'})
        self.assertEqual(next(row['argv']for row in selection['commands']if row['id']=='option-coverage-structure'),[sys.executable,'scripts/iteration/option_coverage.py','--check-structure'])

    def test_frozen_reference_fallback_rechecks_exact_bytes_and_rejects_changed_bytes(self):
        manifest=self.manifest();baseline=manifest['savedEvidence']['path']
        self.assertEqual(baseline,'docs/releases/evidence/development-frozen/report.json')
        name='references/e13-cell-sources.json'
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder)
            for item in(baseline,name):
                target=root/item;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/item,target)
            selection=ci_selected.plan([name],manifest,root)
            self.assertTrue(selection['passed']);self.assertEqual(selection['commands'],[])
            self.assertEqual(selection['savedEvidenceByteRechecks'],[{'path':name,'sha256':ci_selected.digest(root/name)}])
            (root/name).write_bytes((root/name).read_bytes()+b'\n')
            selection=ci_selected.plan([name],manifest,root)
            self.assertFalse(selection['passed']);self.assertEqual(selection['unplannedPaths'],[name])

    def test_independent_evidence_archives_select_only_their_consumers(self):
        for stem, check in (('options', 'option-evidence-strict'),
                            ('branches', 'declared-branches'),
                            ('algorithms', 'algorithm-acceptance')):
            for suffix in ('.zip', '.manifest.json'):
                with self.subTest(archive=stem + suffix):
                    names,_ = self.selected(['references/full-native-closure/' + stem + suffix])
                    self.assertIn(check, names)
                    if stem != 'options':
                        self.assertNotIn('option-evidence-restore', names)
                        self.assertNotIn('option-evidence-strict', names)
        names,_ = self.selected(['tests/fixtures/suites/full-option-effects/geometry-contracts/manifest.json'])
        self.assertEqual(names, {'advanced-geometry'})

    def test_algorithm_manifest_direct_dependencies_are_really_in_git_index(self):
        manifest=ci_selected.load(ROOT/'references/full-native-closure/algorithms.manifest.json')
        tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf8').split('\0'))
        missing=sorted(row['path'] for row in manifest['requiredRepositoryFiles'] if row['path'] not in tracked)
        self.assertFalse(missing, 'Direct archive dependencies would be missing from a fresh checkout: '+repr(missing))

    def test_unknown_code_stops_all_commands_and_docs_select_no_runtime(self):
        manifest=self.manifest()
        with tempfile.TemporaryDirectory()as folder,patch.object(ci_selected.subprocess,'run')as process:
            selection=ci_selected.plan(['src/pyelk/api.py','scripts/unplanned_future_check.py'],manifest)
            self.assertFalse(selection['passed']);self.assertEqual(selection['unplannedPaths'],['scripts/unplanned_future_check.py'])
            result=ci_selected.execute(selection,Path(folder)/'unknown')
            self.assertFalse(result['passed']);self.assertEqual(result['executed'],[]);process.assert_not_called()
            selection=ci_selected.plan(['docs/NEW_SESSION.md'],manifest)
            self.assertTrue(selection['passed']);self.assertEqual(selection['commands'],[])


if __name__=='__main__':unittest.main()
