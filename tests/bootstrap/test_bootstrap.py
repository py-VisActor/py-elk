"""Negative controls for the scaffold, coverage ledger and source provenance."""
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import upstream
from validate_bootstrap import check, local_file


@contextmanager
def altered_json(name, transform):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for dirname in ("src", "scripts", "examples", "tests", "docs", "references", "tools", "benchmarks"):
            if (ROOT / dirname).is_dir():
                shutil.copytree(ROOT / dirname, root / dirname,
                                ignore=shutil.ignore_patterns("__pycache__"))
        for path in ROOT.iterdir():
            if path.is_file():
                shutil.copy2(path, root / path.name)
        target = root / name
        value = json.loads(target.read_text(encoding="utf-8"))
        transform(value)
        target.write_text(json.dumps(value), encoding="utf-8")
        yield root


class BootstrapTests(unittest.TestCase):
    def test_current_source(self):
        self.assertEqual(check()["errors"], [])

    def test_algorithm_cannot_disappear(self):
        with altered_json("docs/compatibility.json", lambda data: data["algorithms"].pop()) as root:
            self.assertIn("Coverage denominator differs: algorithms", check(root)["errors"])

    def test_option_cannot_disappear(self):
        with altered_json("docs/compatibility.json", lambda data: data["options"].pop()) as root:
            self.assertIn("Coverage denominator differs: options", check(root)["errors"])

    def test_fake_coordinate_verification_rejected(self):
        with altered_json("docs/compatibility.json", lambda data: data["algorithms"][0].update(coordinates="coordinates_verified")) as root:
            self.assertTrue(any("Verified stage requires evidence" in error for error in check(root)["errors"]))

    def test_missing_evidence_rejected(self):
        def transform(data):
            data["algorithms"][0].update(coordinates="coordinates_verified", evidence=[{"path": "missing.json", "sha256": "0" * 64}])
        with altered_json("docs/compatibility.json", transform) as root:
            self.assertTrue(any("Invalid evidence" in error for error in check(root)["errors"]))

    def test_metadata_corruption_rejected(self):
        with altered_json("references/metadata/algorithms.json", lambda data: data.pop()) as root:
            self.assertTrue(any("Metadata snapshot hash differs" in error for error in check(root)["errors"]))

    def test_unrequested_legacy_profile_rejected(self):
        with altered_json("UPSTREAM.json", lambda data: data["integrationPolicy"].update(legacyElkCompatibilityRequired=True)) as root:
            self.assertIn("An unwanted legacy ELK compatibility profile was added", check(root)["errors"])

    def test_fixture_cannot_escape(self):
        self.assertFalse(local_file(ROOT / "tests/fixtures", "../../README.md"))

    def test_mermaid_cannot_block_basic_release(self):
        with altered_json("UPSTREAM.json", lambda data: data["releasePlan"].update(firstReleaseDependsOnMermaid=True)) as root:
            self.assertIn("Basic package release must precede independent Mermaid integration", check(root)["errors"])

    def test_release_profile_cannot_invent_options(self):
        with altered_json("docs/release-profiles.json", lambda data: data["profiles"][0]["options"].append("org.eclipse.elk.invented")) as root:
            self.assertIn("Release profile names an unknown option", check(root)["errors"])

    def test_source_commit_drift_rejected(self):
        with patch.object(upstream, "git", return_value=b"wrong\n"):
            with self.assertRaisesRegex(ValueError, "Source commit differs"):
                upstream.verify_source(Path("unused"), {"javascript": {"commit": "expected"}})

    def test_dirty_source_rejected(self):
        with patch.object(upstream, "git", side_effect=[b"expected\n", b" M source.js\n"]):
            with self.assertRaisesRegex(ValueError, "dirty"):
                upstream.verify_source(Path("unused"), {"javascript": {"commit": "expected"}})

    def test_source_hash_drift_rejected(self):
        lock = {"javascript": {"commit": "expected"}, "sourceSha256": {"source.js": "0" * 64}}
        with patch.object(upstream, "git", side_effect=[b"expected\n", b"", b"changed"]):
            with self.assertRaisesRegex(ValueError, "Source hash differs"):
                upstream.verify_source(Path("unused"), lock)

    def test_archive_traversal_rejected(self):
        for name in ("../escape", "/absolute", "package/../../escape", "package\\escape", "package/C:/escape"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                upstream.safe_member(name)


if __name__ == "__main__":
    unittest.main()
