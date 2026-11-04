"""Two targeted controls on the immutable E09/E10 historical material."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import e11_history


class HistoricalEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Recompute the genuine archived raw observations first; never import
        # its product or use a saved passed boolean as the positive fixture.
        result=e11_history.check(ROOT)
        if not result['passed']:raise AssertionError(result['errors'])
        cls.original_result=result

    def fixture(self):
        folder=tempfile.TemporaryDirectory(prefix='pyelk-e11-history-control-')
        self.addCleanup(folder.cleanup)
        root=Path(folder.name);destination=root/e11_history.HISTORY
        destination.mkdir(parents=True)
        for source in (ROOT/e11_history.HISTORY).iterdir():
            if source.is_file():shutil.copyfile(source,destination/source.name)
        self.assertEqual(len(e11_history.material(root)['src/pyelk/api.py'])>0,True)
        return root,destination

    def test_changed_archive_or_wheel_bytes_cannot_reuse_original_manifest(self):
        root,folder=self.fixture()
        for name in ('audit-material.zip','py_elk-0.0.1a0-py3-none-any.whl'):
            target=folder/name;original=target.read_bytes()
            try:
                target.write_bytes(original+b'changed')
                with self.assertRaisesRegex(ValueError,'Historical (archive|wheel) bytes differ'):
                    e11_history.material(root)
            finally:target.write_bytes(original)
            self.assertIn('src/pyelk/api.py',e11_history.material(root))

    def test_rebinding_manifest_cannot_promote_changed_history_to_current(self):
        root,folder=self.fixture();path=folder/'manifest.json';original=path.read_bytes()
        manifest=json.loads(original)
        manifest['productFilesSha256']['api.py']=hashlib.sha256(b'new product').hexdigest()
        path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Historical manifest bytes differ'):
            e11_history.material(root)
        path.write_bytes(original)
        self.assertIn('src/pyelk/api.py',e11_history.material(root))
        self.assertTrue(self.original_result['historicalPackageBytesValidated'])
        self.assertFalse(self.original_result['currentPackageBytesValidated'])
        self.assertFalse(self.original_result['runtimeReexecuted'])
        self.assertFalse(self.original_result['fullValidation'])


if __name__=='__main__':unittest.main()
