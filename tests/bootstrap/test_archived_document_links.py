"""Archive storage prefixes must not relocate authored documentation links."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('bootstrap_archive_links',ROOT/'scripts/validate_bootstrap.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ArchivedDocumentLinks(unittest.TestCase):
    def test_document_and_source_origins(self):
        examples={
            'references/next-native-evidence/14/README.md':'README.md',
            'references/next-native-evidence/16/docs/E11_LICENSE_PROPOSAL.md':'docs/E11_LICENSE_PROPOSAL.md',
            'references/next-native-evidence/18/test-runs/caller/snapshot/src/pyelk/model/README.md':'src/pyelk/model/README.md',
            'docs/NEW_SESSION.md':'docs/NEW_SESSION.md',
        }
        for storage,original in examples.items():
            with self.subTest(storage=storage):
                self.assertEqual(module.documentation_origin(ROOT,ROOT/storage),ROOT/original)

    def test_only_known_archive_storage_is_mapped(self):
        path=ROOT/'references/other/docs/missing.md'
        self.assertEqual(module.documentation_origin(ROOT,path),path)


if __name__=='__main__':unittest.main()
