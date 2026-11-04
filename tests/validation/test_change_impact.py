"""Development selection is conservative and cannot be final acceptance."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from change_impact import changed_since, input_hashes, plan_changes, relative_name, select_steps
from preflight import assertion_inventory


class ChangeImpactTests(unittest.TestCase):
    def test_api_changes_include_boundary_and_real_conformance(self):
        plan = plan_changes(["src/pyelk/api.py"])
        self.assertTrue({"api", "execution", "contract", "conformance", "audit"} <= set(plan["groups"]))
        self.assertFalse(plan["fallbackToFull"])
        self.assertIs(plan["finalAcceptance"], False)

    def test_unknown_scripts_configs_and_packaged_readme_require_full(self):
        for name in ("scripts/new_validator.py", "pyproject.toml", "README.md", "docs/compatibility.json", "new-input.data",
                     "src/pyelk/_licenses/NOTICE-E07.md", "docs/decisions/0006-e07-directions-components.md"):
            self.assertTrue(plan_changes([name])["fallbackToFull"], name)

    def test_test_selection_keeps_owner_pattern_and_validation_labels(self):
        steps = [("api-tests", ["python", "-m", "unittest", "discover", "-s", "tests/api", "-v"]),
                 ("bootstrap", ["python", "bootstrap.py"]), ("source-audit", ["python", "audit.py"])]
        plan = plan_changes(["tests/api/test_e04_api.py"])
        selected = select_steps(steps, plan)
        self.assertEqual(selected[0][0], "api-tests--test_e04_api")
        self.assertEqual(selected[0][1][-3:], ["-p", "test_e04_api.py", "-v"])
        self.assertEqual([n for n, _ in selected[-2:]], ["bootstrap", "source-audit"])

    def test_shared_helper_selects_entire_group_even_with_specific_test(self):
        plan = plan_changes(["tests/audit/audit_fixture_support.py", "tests/audit/test_e07_runtime.py"])
        self.assertIsNone(plan["specificTests"]["audit"])

    def test_added_deleted_unknown_files_are_not_hidden_by_hash_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "src").mkdir()
            (root / "src/module.py").write_bytes(b"one")
            before = {"inputFilesSha256": input_hashes(root)}
            (root / "src/module.py").unlink(); (root / "unknown.conf").write_bytes(b"new")
            self.assertEqual(changed_since(before, root), ["src/module.py", "unknown.conf"])
            self.assertTrue(plan_changes(changed_since(before, root))["fallbackToFull"])

    def test_generated_outputs_and_caches_are_not_full_check_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("test-runs/output.txt", ".local/tool.bin", "src/__pycache__/module.pyc"):
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"generated")
            (root / "settings.conf").write_bytes(b"input")
            self.assertEqual(set(input_hashes(root)), {"settings.conf"})

    def test_nested_fixture_directory_names_are_real_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("tests/fixtures/build/request.json", "tests/fixtures/dist/case.json", "tests/fixtures/test-runs/input.json"):
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"input")
            self.assertEqual(len(input_hashes(root)), 3)

    def test_model_changes_include_direct_layered_consumer(self):
        self.assertIn("layered", plan_changes(["src/pyelk/model/ordered.py"])["groups"])

    def test_untrusted_changed_paths_do_not_escape_repository(self):
        for name in ("../src/a.py", "/tmp/a.py", "C:/src/a.py", "src\\a.py", "src//a.py", "./a.py"):
            with self.assertRaises(ValueError):
                relative_name(name)

    def test_inventory_preserves_rejection_checks_without_inferring_support(self):
        rows = assertion_inventory()
        api = [row for row in rows if row["path"] == "tests/api/test_e04_api.py"]
        self.assertTrue(any(row["test"] == "test_worker_callable_is_rejected_without_executing_it" for row in api))
        self.assertTrue(all("human-review-required" in row["disposition"] for row in api))
        self.assertFalse(any(row["test"] == "test_down_direction_uses_real_transforms_and_preserves_input" for row in api))
        self.assertFalse(any(row["test"] == "test_former_slice_exclusions_execute_and_preserve_caller_data" for row in api))

    def test_inventory_only_cli_never_claims_smoke_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); manifest = base / "baseline.json"
            manifest.write_text(json.dumps({"inputFilesSha256": input_hashes(ROOT)}), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/preflight.py"), "--baseline", str(manifest),
                                     "--out", str(base / "inventory"), "--inventory-only"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((base / "inventory/report.json").read_bytes())
            self.assertEqual(report["status"], "INVENTORY_ONLY")
            self.assertIs(report["passed"], None)
            self.assertIs(report["smokeExecuted"], False)
