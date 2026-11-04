"""Affected twenty-option parsing, source default resolution and host boundaries."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/iteration'))
import next_workspace


class PrivateNodeContextOptionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='py-elk-node-options-')
        cls.workspace = Path(cls.folder.name)/'restored'
        next_workspace.restore(cls.workspace)

    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()

    def run_case(self,name):
        result = subprocess.run([sys.executable,'-I',str(ROOT/'tools/platform/next_node_options_probe.py'),
                                 '--workspace',str(self.workspace),'--case',name],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        record = json.loads(result.stdout)
        self.assertTrue(record['passed']); self.assertTrue(record['privateSource'])
        self.assertTrue(Path(record['modulePath']).is_relative_to(self.workspace))
        self.assertFalse(record['publicAPIIntegrated']); self.assertFalse(record['fullValidation'])

    def test_core_algorithm_and_global_defaults_remain_distinct_and_targeted(self): self.run_case('defaults-and-targets')
    def test_explicit_empty_false_and_node_individual_override_preserve_scopes(self): self.run_case('presence-and-individual')
    def test_source_enum_vector_insets_and_numeric_token_rules(self): self.run_case('source-tokens')
    def test_source_whitespace_and_control_character_boundaries(self): self.run_case('source-whitespace')
    def test_added_schemas_keep_the_affected_bounded_path_and_its_declared_admission(self): self.run_case('bounded-admission')
    def test_native_invalid_properties_and_original_raw_values(self): self.run_case('invalid-and-raw-preservation')


if __name__ == '__main__': unittest.main()
