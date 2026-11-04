"""Changed JSON import/export component only, restored private source."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/iteration'))
import next_workspace


class PrivateJsonTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='py-elk-json-host-')
        cls.workspace = Path(cls.folder.name)/'restored'
        next_workspace.restore(cls.workspace)

    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()

    def run_case(self, name):
        result = subprocess.run([sys.executable, '-I', str(ROOT/'tools/platform/next_json_probe.py'),
                                 '--workspace', str(self.workspace), '--case', name],
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        record = json.loads(result.stdout)
        self.assertTrue(record['passed']); self.assertTrue(record['privateSource'])
        self.assertTrue(Path(record['modulePath']).is_relative_to(self.workspace))
        self.assertFalse(record['publicAPIIntegrated']); self.assertFalse(record['fullValidation'])

    def test_coordinate_modes_keep_original_owner_and_root_position(self): self.run_case('coordinate-ownership')
    def test_coordinate_ordinals_share_strict_native_enum_parser(self): self.run_case('coordinate-ordinals')
    def test_detached_root_selfedge_and_label_keep_the_original_json(self): self.run_case('detached-edge')
    def test_empty_geometry_preserves_original_section_fields_and_inverse_links(self): self.run_case('conditional-section-fields')
    def test_primitive_geometry_and_provider_side_effects_use_one_state(self): self.run_case('primitive-and-state')
    def test_bad_ids_points_and_section_relations_do_not_mutate_input(self): self.run_case('invalid-imports')


if __name__ == '__main__': unittest.main()
