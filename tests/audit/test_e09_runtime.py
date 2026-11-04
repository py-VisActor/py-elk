"""Original E09 byte/role controls using its authenticated historical universe."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_checks
from layout_checks import load, sha256
from audit_fixture_support import copy_files, record_reads, frozen_e09_root
from validate_e09_runtime import AUDIT, APPROVALS, COVERAGE, check
from validate_e08_runtime import check as e08_check

REPOSITORY_ROOT = ROOT
ROOT = frozen_e09_root()


class E09CurrentRuntimeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Derive the real read closure from a passing current audit, then use
        # independent byte copies for every mutation. No old PASS fixture.
        with patch.object(layout_checks, "ROOT", ROOT), record_reads(ROOT) as reads:
            positive = check(ROOT)
        if not positive["passed"]:
            raise AssertionError("Actual current E09 receipt is required: " + str(positive["errors"]))
        cls.directory = tempfile.TemporaryDirectory(prefix="pyelk-e09-audit-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        cls.copy_profile = copy_files(ROOT, cls.root, reads)

    def setUp(self):
        self.saved = {}

    def tearDown(self):
        for name, raw in self.saved.items():
            (self.root / name).write_bytes(raw)

    def save(self, name, value):
        path = self.root / name
        self.saved.setdefault(name, path.read_bytes())
        path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())

    def audit(self):
        with patch.object(layout_checks, "ROOT", self.root):
            return check(self.root)

    def rebind(self, name):
        audit = load(self.root / AUDIT)
        audit["filesSha256"][name] = sha256(self.root / name)
        self.save(AUDIT, audit)
        fingerprint = sha256(self.root / AUDIT)
        for name in ("UPSTREAM.json", "docs/compatibility.json"):
            declaration = load(self.root / name)
            host = declaration["python"]["nativeHost"] if name == "UPSTREAM.json" else declaration["nativeHost"]
            host["evidence"]["sha256"] = fingerprint
            self.save(name, declaration)

    def review_mutation(self, mutate):
        approval = load(self.root / APPROVALS)
        row = approval["reviewEvidence"]["V-host-audit"]
        review = load(self.root / row["path"])
        mutate(review)
        self.save(row["path"], review)
        row["sha256"] = sha256(self.root / row["path"])
        self.save(APPROVALS, approval)
        self.rebind(APPROVALS)

    def negative(self, mutate, message):
        self.assertEqual(self.audit()["errors"], [])
        mutate()
        result = self.audit()
        self.assertFalse(result["passed"])
        self.assertTrue(result["errors"])
        if message:
            self.assertIn(message, " ".join(result["errors"]))

    def test_actual_positive_closure_has_no_backend_or_development_cache(self):
        with record_reads(self.root) as reads:
            self.assertTrue(self.audit()["passed"])
        self.assertLessEqual(reads, set(self.copy_profile["paths"]))
        self.assertFalse((self.root / ".local").exists())
        self.assertFalse((self.root / ".git").exists())

    def test_current_production_edit_invalidates_source_approval(self):
        name = "src/pyelk/algorithms/layered/scope.py"
        def mutate():
            path = self.root / name
            self.saved[name] = path.read_bytes()
            path.write_bytes(path.read_bytes() + b"\n# changed current policy\n")
        self.negative(mutate, "Approved E09 production bytes differ")

    def test_declined_independent_review_cannot_be_rebound_to_approval(self):
        self.negative(lambda: self.review_mutation(lambda value: value.update(accepted=False)),
                      "independent review rejected/incomplete")

    def test_accepted_review_must_cover_every_required_file(self):
        self.negative(lambda: self.review_mutation(lambda value: value["filesSha256"].pop("scripts/check.py")),
                      "review omits required files")

    def test_current_declaration_cannot_point_to_historical_e08(self):
        def mutate():
            value = load(self.root / "UPSTREAM.json")
            value["python"]["runtimeEvidence"] = "references/e08-runtime-audit.json"
            self.save("UPSTREAM.json", value)
        self.negative(mutate, "current declaration/evidence differs")

    def test_full_reference_catalogue_cannot_shrink_to_native_registry(self):
        def mutate():
            value = load(self.root / "UPSTREAM.json")
            value["metadataCapture"]["counts"] = {"algorithms": 1, "options": 9, "categories": 1}
            self.save("UPSTREAM.json", value)
        self.negative(mutate, "denominator")

    def test_branch_capture_cannot_switch_actual_candidate_interpreter(self):
        def mutate():
            value = load(self.root / COVERAGE)
            value["candidatePython"] += ".different"
            self.save(COVERAGE, value)
            self.rebind(COVERAGE)
        self.negative(mutate, "")

    def test_e08_historical_success_explicitly_does_not_certify_current_code(self):
        result = e08_check(REPOSITORY_ROOT, historical=True)
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["currentPackageBytesValidated"])
        self.assertFalse(result["currentDistributionMetadataValidated"])
        self.assertTrue(result["historicalPackageBytesValidated"])
        self.assertFalse(result["runtimeReexecuted"])


if __name__ == "__main__":
    unittest.main()
