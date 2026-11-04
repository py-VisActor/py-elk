"""E07 current-byte receipts and semantic mutations with a passing baseline."""
from contextlib import contextmanager
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load, sha256
from audit_fixture_support import copy_files, runtime_paths
from validate_e07_runtime import (
    AUDIT, INSTALLED, APPROVALS, REQUIRED_FILES, check, validate_metadata,
    historical_material, historical_metadata,
)


def save(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def receipt(raw):
    return {"archivePath": "py_elk-0.0.1a0.dist-info/METADATA",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytesBase64": base64.b64encode(raw).decode("ascii")}


@contextmanager
def metadata_fixture():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in ("pyproject.toml", "README.md"):
            shutil.copyfile(ROOT / name, root / name)
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        headers = ["Metadata-Version: 2.4", "Name: " + project["name"], "Version: " + project["version"],
                   "Summary: " + project["description"], "Requires-Python: " + project["requires-python"],
                   "Description-Content-Type: text/markdown"]
        headers += ["Classifier: " + value for value in project.get("classifiers", [])]
        headers += ["Requires-Dist: " + value for value in project.get("dependencies", [])]
        for extra, values in project.get("optional-dependencies", {}).items():
            headers.append("Provides-Extra: " + extra)
            headers += ['Requires-Dist: ' + value + '; extra == "' + extra + '"' for value in values]
        raw = ("\n".join(headers) + "\n\n").encode("utf-8") + (root / "README.md").read_bytes()
        yield root, {"wheelVersion": project["version"], "distributionMetadata": receipt(raw)}, raw


@contextmanager
def offline_copy():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        copy_files(ROOT, root, runtime_paths(ROOT, "E07"))
        # Preserve the original current-byte mutation controls on E07's frozen
        # package. The actual current E08 package has its own independent audit.
        declarations, package = historical_material(root)
        for path in (root / "src/pyelk").rglob("*"):
            if path.is_file() and path.relative_to(root / "src/pyelk").as_posix() not in package:
                path.unlink()
        for name, raw in package.items():
            target = root / "src/pyelk" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for name, document in declarations.items():
            save(root / name, document)
        summary = load(root / INSTALLED)
        for name, raw in historical_metadata(root, summary).items():
            (root / name).write_bytes(raw)
        yield root


def rebind(root, changed):
    if changed in REQUIRED_FILES:
        audit = load(root / AUDIT)
        audit["filesSha256"][changed] = sha256(root / changed)
        save(root / AUDIT, audit)
    fingerprint = sha256(root / AUDIT)
    for path in ("UPSTREAM.json", "docs/compatibility.json"):
        document = load(root / path)
        def visit(value):
            if type(value) is dict:
                if value.get("path") == AUDIT and "sha256" in value:
                    value["sha256"] = fingerprint
                for child in value.values():
                    visit(child)
            elif type(value) is list:
                for child in value:
                    visit(child)
        visit(document)
        save(root / path, document)


class E07MetadataTests(unittest.TestCase):
    def test_current_metadata_wrapper_keeps_raw_identity_and_no_execution_claim(self):
        with metadata_fixture() as (root, summary, raw):
            result = validate_metadata(summary, root)
            self.assertEqual(result["status"], "E07_DISTRIBUTION_METADATA_VALIDATED")
            self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertIs(result["historicalExecutionAuthenticated"], False)

    def test_historical_mode_never_certifies_a_changed_current_package(self):
        with offline_copy() as root:
            self.assertEqual(check(root, historical=True)["errors"], [])
            source = root / "src/pyelk/api.py"
            source.write_bytes(source.read_bytes() + b"\n# E08 current edit\n")
            archived = check(root, historical=True)
            self.assertEqual(archived["errors"], [])
            self.assertIs(archived["historicalPackageBytesValidated"], True)
            self.assertIs(archived["currentPackageBytesValidated"], False)
            self.assertIn("Current package bytes", " ".join(check(root)["errors"]))

    def test_historical_archive_is_pinned_even_if_its_manifest_is_rebound(self):
        with offline_copy() as root:
            self.assertEqual(check(root, historical=True)["errors"], [])
            path = root / "references/history/E07/py_elk-0.0.1a0-py3-none-any.whl"
            path.write_bytes(path.read_bytes() + b"mutation")
            material = load(root / "references/history/E07/material.json")
            material["wheel"]["sha256"] = sha256(path)
            save(root / "references/history/E07/material.json", material)
            self.assertIn("Historical wheel", " ".join(check(root, historical=True)["errors"]))

    def test_historical_readme_is_pinned_even_after_local_rebinding(self):
        with offline_copy() as root:
            self.assertEqual(check(root, historical=True)["errors"], [])
            path = root / "references/history/E07/metadata-material.json"
            material = load(path)
            raw = base64.b64decode(material["files"]["README.md"]["bytesBase64"]) + b"changed"
            material["files"]["README.md"] = {"bytesBase64": base64.b64encode(raw).decode("ascii"),
                                                    "sha256": hashlib.sha256(raw).hexdigest()}
            save(path, material)
            self.assertIn("Historical metadata material", " ".join(check(root, historical=True)["errors"]))

    def test_rebound_metadata_still_requires_current_readme_and_python_requirement(self):
        with metadata_fixture() as (root, summary, raw):
            for changed, message in [(raw + b"\n", "README bytes"),
                                     (raw.replace(b"Requires-Python: >=3.11", b"Requires-Python: >=3.12"), "Requires-Python")]:
                summary["distributionMetadata"] = receipt(changed)
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    validate_metadata(summary, root)


class E07CurrentRuntimeTests(unittest.TestCase):
    def assert_baseline(self, root):
        result = check(root)
        self.assertEqual(result["errors"], [], result)
        self.assertIs(result["currentPackageBytesValidated"], True)
        self.assertIs(result["currentDistributionMetadataValidated"], True)

    def negative(self, path, mutate, message):
        with offline_copy() as root:
            self.assert_baseline(root)
            value = load(root / path)
            mutate(value)
            save(root / path, value)
            rebind(root, path)
            result = check(root)
            self.assertEqual(result["status"], "FAIL", result)
            self.assertIs(result["currentPackageBytesValidated"], False)
            self.assertIn(message, " ".join(result["errors"]))

    def test_current_e07_receipts_pass_without_raw_runs_and_never_authenticate_execution(self):
        with offline_copy() as root:
            self.assertFalse((root / "test-runs").exists())
            self.assertFalse((root / ".local").exists())
            result = check(root)
            self.assertEqual(result["errors"], [], result)
            self.assertEqual(result["sourceValidation"]["componentCounts"], {"A": 4, "B": 3, "R": 26})
            self.assertIs(result["currentPackageBytesValidated"], True)
            for key in ("historicalWheelAuthenticated", "runtimeReexecuted", "mathematicalEquivalenceAutomaticallyProved"):
                self.assertIs(result[key], False)

    def test_missing_receipts_do_not_create_a_current_certificate(self):
        with tempfile.TemporaryDirectory() as directory:
            result = check(Path(directory))
            self.assertEqual(result["status"], "FAIL")
            self.assertIs(result["currentPackageBytesValidated"], False)
            self.assertIs(result["currentDistributionMetadataValidated"], False)
            self.assertIs(result["runtimeReexecuted"], False)

    def test_each_new_source_approval_is_required_even_after_sha_rebinding(self):
        def remove_direction(value):
            value["approvals"] = [row for row in value["approvals"] if row["componentId"] != "direction:transpose"]
        self.negative(APPROVALS, remove_direction, "source gate")

    def test_full_scope_and_original_case_denominators_cannot_shrink(self):
        self.negative(AUDIT, lambda value: value["coverageDenominators"].update(selectedMasterCases=21), "denominator")
        self.negative(AUDIT, lambda value: value["scope"].update(directions=["RIGHT", "UNDEFINED"]), "bounded scope")
        self.negative(AUDIT, lambda value: value["scope"].update(separateConnectedComponents=[True]), "bounded scope")
        self.negative(INSTALLED, lambda value: value["cases"].pop(), "Installed case IDs")

    def test_new_python_and_all_five_license_bytes_are_bound(self):
        self.negative(INSTALLED, lambda value: value["packageFilesSha256"].pop("_licenses/NOTICE-E07.md"), "file denominator")
        with offline_copy() as root:
            self.assert_baseline(root)
            source = root / "src/pyelk/algorithms/layered/directions.py"
            source.write_bytes(source.read_bytes() + b"\n# changed after capture\n")
            result = check(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("Current package bytes", " ".join(result["errors"]))
        with offline_copy() as root:
            self.assert_baseline(root)
            (root / "src/pyelk/_licenses/additional.txt").write_bytes(b"new source notice\n")
            self.assertIn("file denominator", " ".join(check(root)["errors"]))

    def test_repetitions_and_e07_source_command_role_are_required(self):
        self.negative(INSTALLED, lambda value: value.update(repeat=2), ">=3")
        def old_source_command(value):
            row = next(row for row in value["commands"] if row["name"] == "source-approval")
            row["argv"][1] = "scripts/validate_e06_source_bindings.py"
        self.negative(INSTALLED, old_source_command, "source approval")

    def test_current_metadata_cannot_be_rebound_to_a_stale_readme(self):
        def stale_readme(value):
            raw = base64.b64decode(value["distributionMetadata"]["bytesBase64"], validate=True)
            value["distributionMetadata"] = receipt(raw + b"\nstale metadata\n")
        self.negative(INSTALLED, stale_readme, "README bytes")
        self.negative(INSTALLED, lambda value: value.pop("distributionMetadata"), "distributionMetadata")

    def test_nested_full_acceptance_and_static_execution_promotion_are_rejected(self):
        self.negative(AUDIT, lambda value: value.update(nested={"fullAlgorithmAccepted": True}), "fullAlgorithmAccepted")
        self.negative(AUDIT, lambda value: value.update(nested={"runtimeReexecuted": True}), "runtimeReexecuted")
        self.negative(INSTALLED, lambda value: value.update(nested={"historicalExecutionAuthenticated": True}), "historicalExecutionAuthenticated")


if __name__ == "__main__":
    unittest.main()
