"""Private next-stage properties; no published API compatibility is certified."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import next_workspace


class PrivateElementOptionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory(prefix='py-elk-next-options-')
        cls.workspace=Path(cls.folder.name)/'restored'
        next_workspace.restore(cls.workspace)

    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()

    def run_case(self,name):
        result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/platform/next_options_probe.py'),
                               '--workspace',str(self.workspace),'--case',name],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        value=json.loads(result.stdout)
        self.assertTrue(value['passed']);self.assertTrue(value['privateSource'])
        self.assertTrue(Path(value['modulePath']).is_relative_to(self.workspace))
        self.assertFalse(value['publicAPIIntegrated']);self.assertFalse(value['fullValidation'])

    def test_local_properties_override_global_without_losing_explicit_zero(self):self.run_case('precedence')
    def test_call_mapping_replaces_constructor_and_root_local_does_not_leak(self):self.run_case('call-replacement')
    def test_source_enum_ordinals_signed_values_and_vector_forms(self):self.run_case('typed')
    def test_native_invalid_value_and_duplicate_alias_errors(self):self.run_case('invalid')
    def test_restoring_a_checkpoint_keeps_an_existing_workspace(self):
        before=(self.workspace/'src/pyelk/__init__.py').read_bytes()
        with self.assertRaises(FileExistsError):next_workspace.restore(self.workspace)
        self.assertEqual((self.workspace/'src/pyelk/__init__.py').read_bytes(),before)

    def test_previous_source_checkpoint_is_reproducible_after_new_changes(self):
        histories=sorted((ROOT/next_workspace.STAGE/'checkpoints').glob('*.json'))
        self.assertTrue(histories,'A prior source checkpoint is required for this control')
        with tempfile.TemporaryDirectory(prefix='py-elk-previous-source-') as folder:
            destination=Path(folder)/'previous';next_workspace.restore(destination,manifest_path=histories[0])
            expected=json.loads(histories[0].read_bytes())['sourceTreeSha256']
            actual={n:next_workspace.digest(raw) for n,raw in next_workspace.files(destination/'src/pyelk').items()}
            self.assertEqual(actual,expected)


if __name__=='__main__':unittest.main()
