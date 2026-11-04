"""Thin saved-data controls for final acceptance; no product/oracle execution."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

from scripts.iteration import migration_acceptance as acceptance


class MigrationAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.publication_path = 'docs/releases/evidence/published-0.1.0/publication.json'
        prefix = 'docs/releases/evidence/published-0.1.0/'
        m7 = acceptance.load('docs/iterations/E16_E19_ACCEPTANCE.json')
        cls.publication_inputs = (
            acceptance.load(cls.publication_path), m7['publishedPayload'],
            acceptance.load(prefix + 'wheel-installed.json'),
            acceptance.load(prefix + 'sdist-installed.json'),
            acceptance.load(prefix + 'verification.json'),
            acceptance.load(prefix + 'independent-publication-audit.json'),
        )
        manifest = acceptance.load('references/full-native-closure/algorithms.manifest.json')
        raw = (acceptance.ROOT / 'references/full-native-closure/algorithms.zip').read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest['archive']['sha256']:
            raise ValueError('Actual M7 archive digest differs')
        record = m7['performance39']['report']
        member = next(item for item in manifest['members'] if item['path'] == record['path'])
        with zipfile.ZipFile(acceptance.ROOT / 'references/full-native-closure/algorithms.zip') as archive:
            payload = archive.read(record['path'])
        if hashlib.sha256(payload).hexdigest() != record['sha256'] or record['sha256'] != member['sha256']:
            raise ValueError('Actual performance raw is not the bound M7 member')
        cls.profiles = json.loads(payload)['profiles']

    def publication_rejects(self, position, change):
        values = copy.deepcopy(self.publication_inputs)
        change(values[position])
        with self.assertRaises(ValueError):
            acceptance.check_publication(*values)

    def test_actual_uploaded_downloaded_and_installed_artifacts(self):
        self.assertIsNone(acceptance.check_publication(*self.publication_inputs))

    def test_publication_or_payload_artifact_sha_mismatch_rejected(self):
        for name in self.publication_inputs[0]['uploadedArtifactsSha256']:
            with self.subTest(artifact=name):
                self.publication_rejects(0, lambda value: value['uploadedArtifactsSha256'].__setitem__(name, '0' * 64))
        self.publication_rejects(1, lambda value: value['wheel'].__setitem__('sha256', '0' * 64))

    def test_actual_installations_cannot_substitute_prepared_artifacts(self):
        for position, key in ((2, 'artifactSha256'), (2, 'wheelSha256'), (2, 'sdistSha256'),
                              (3, 'artifactSha256'), (3, 'wheelSha256'), (3, 'sdistSha256')):
            with self.subTest(installation=position, field=key):
                self.publication_rejects(position, lambda value: value.__setitem__(key, '0' * 64))

    def test_download_and_independent_audit_must_link_same_bytes(self):
        wheel_name = 'py_visactor_elk-0.1.0-py3-none-any.whl'
        self.publication_rejects(4, lambda value: value['expectedArtifactsSha256'].__setitem__(wheel_name, '0' * 64))
        self.publication_rejects(5, lambda value: value['publishedArtifactsSha256'].__setitem__(wheel_name, '0' * 64))
        for position, field in ((4, 'passed'), (5, 'passed'), (5, 'uploadedArtifactsEqualPyPIDownloadsByteForByte')):
            for wrong in (False, 1):
                with self.subTest(record=position, field=field, wrong=wrong):
                    self.publication_rejects(position, lambda value: value.__setitem__(field, wrong))

    def test_actual_39_profile_determinism(self):
        self.assertIsNone(acceptance.check_performance(self.profiles))

    def test_duplicate_missing_or_wrong_performance_profile_rejected(self):
        profiles = copy.deepcopy(self.profiles)
        profiles[-1] = copy.deepcopy(profiles[0])
        with self.assertRaises(ValueError): acceptance.check_performance(profiles)
        with self.assertRaises(ValueError): acceptance.check_performance(self.profiles[:-1])
        profiles = copy.deepcopy(self.profiles)
        profiles[0]['nodes'] = 95
        with self.assertRaises(ValueError): acceptance.check_performance(profiles)
        profiles = copy.deepcopy(self.profiles)
        profiles[-1]['options'] = {}
        with self.assertRaises(ValueError): acceptance.check_performance(profiles)

    def test_unstable_empty_or_invalid_result_hash_rejected(self):
        original = self.profiles[0]['samples'][0]['resultSha256']
        other = ('0' if original[0] != '0' else '1') + original[1:]
        for wrong in (other, '', False, 'x' * 64):
            with self.subTest(wrong=wrong):
                profiles = copy.deepcopy(self.profiles)
                profiles[0]['samples'][1]['resultSha256'] = wrong
                with self.assertRaises(ValueError): acceptance.check_performance(profiles)
        profiles = copy.deepcopy(self.profiles)
        profiles[0]['samples'].pop()
        with self.assertRaises(ValueError): acceptance.check_performance(profiles)

    def test_validated_actual_saved_publication(self):
        publication = self.publication_inputs[0]
        result = acceptance.validated('Actual publication', lambda: copy.deepcopy(publication), self.publication_path)
        self.assertEqual(result, publication)

    def test_cached_boolean_number_confusion_rejected(self):
        # Ordinary Python equality accepts both substitutions. The acceptance
        # cache must preserve JSON types before it can support a scoped result.
        for saved, recomputed in ((True, 1), (False, 0), (1, True), (0, False)):
            with self.subTest(saved=saved, recomputed=recomputed):
                with patch.object(acceptance, 'load', return_value={'field': saved}):
                    with self.assertRaises(ValueError):
                        acceptance.validated('Typed cache', lambda: {'field': recomputed}, 'unused.json')


if __name__ == '__main__':
    unittest.main()
