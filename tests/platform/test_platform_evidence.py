"""Archive/guard controls; no layout, interpreter installation or platform run."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

from scripts.iteration import platform_evidence as evidence


class PlatformEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = evidence.load(evidence.ROOT / evidence.MANIFEST)
        cls.raw = (evidence.ROOT / evidence.ARCHIVE).read_bytes()

    def rewrite(self, change):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            members = [(copy.copy(i), archive.read(i)) for i in archive.infolist()]
        members = change(members)
        buffer = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for info, value in members: archive.writestr(info, value)
        raw = buffer.getvalue(); m = copy.deepcopy(self.manifest)
        m['archive'] = {'bytes': len(raw), 'sha256': evidence.digest(raw)}
        return m, raw

    def test_exact_archived_baseline_and_frozen_logs(self):
        values = evidence.decode_archive(self.manifest, self.raw)
        self.assertEqual(self.manifest['baseline'], {'distributionName': 'py-elk', 'version': '0.0.1a0'})
        self.assertEqual(len(self.manifest['selectedCells']), 10)
        result = evidence.verify_frozen_validation(evidence.ROOT, values)
        self.assertEqual((result['steps'], result['testMethods'], result['skipped']), (37, 917, 1))
        self.assertEqual((result['rawFiles'], result['logs'], result['rawLogBytes']), (111, 74, 202901))

    def test_wrong_outer_archive_sha_rejected(self):
        with self.assertRaises(ValueError): evidence.decode_archive(self.manifest, self.raw + b'x')

    def test_missing_and_duplicate_zip_members_rejected(self):
        for change in (lambda a: a[1:], lambda a: a + [a[0]]):
            m, raw = self.rewrite(change)
            with self.assertRaises(ValueError): evidence.decode_archive(m, raw)

    def test_individual_sha_rejected_even_with_rebound_outer_archive(self):
        m, raw = self.rewrite(lambda a: [(a[0][0], a[0][1] + b'x')] + a[1:])
        with self.assertRaises(ValueError): evidence.decode_archive(m, raw)

    def test_escaping_and_noncanonical_member_names_rejected(self):
        for name in ('../escape', '/absolute', 'C:/absolute', 'a\\b', 'a//b', 'a/./b'):
            with self.assertRaises(ValueError): evidence.safe_path(evidence.ROOT, name)
        m = copy.deepcopy(self.manifest); m['archivedFiles'][0]['path'] = '../escape'
        with self.assertRaises(ValueError): evidence.decode_archive(m, self.raw)

    def test_symlink_zip_member_rejected(self):
        def change(a):
            a[0][0].external_attr = 0o120777 << 16
            return a
        m, raw = self.rewrite(change)
        with self.assertRaises(ValueError): evidence.decode_archive(m, raw)

    def test_duplicate_cell_and_false_numeric_denominator_rejected(self):
        m = copy.deepcopy(self.manifest); m['selectedCells'][-1] = m['selectedCells'][0]
        with self.assertRaises(ValueError): evidence.validate_manifest(m)
        m = copy.deepcopy(self.manifest); m['archivedFiles'][0]['bytes'] = False
        with self.assertRaises(ValueError): evidence.validate_manifest(m)
        m = copy.deepcopy(self.manifest); m['baseline']['version'] = '0.1.0'
        with self.assertRaises(ValueError): evidence.validate_manifest(m)

    def test_changed_frozen_log_rejected(self):
        values = evidence.decode_archive(self.manifest, self.raw)
        name = evidence.FROZEN_FOLDER + '/bootstrap-tests-command/stderr.log'
        values[name] = values[name].replace(b'Ran 16 tests', b'Ran 17 tests')
        with self.assertRaises(ValueError): evidence.verify_frozen_validation(evidence.ROOT, values)

    def test_product_process_and_ignored_workspace_access_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); old = root / 'test-runs' / 'old.json'
            old.parent.mkdir(); old.write_text('{}')
            with evidence.offline_guard(root, root):
                with self.assertRaisesRegex(RuntimeError, 'pyelk'): __import__('pyelk')
                with self.assertRaisesRegex(RuntimeError, 'process execution'):
                    subprocess.Popen([sys.executable, '-c', 'raise SystemExit(99)'])
                with self.assertRaisesRegex(RuntimeError, 'ignored workspace'): old.read_bytes()


if __name__ == '__main__': unittest.main()
