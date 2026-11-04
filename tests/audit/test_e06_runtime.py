"""Current E06 receipt checks, with semantically rebound negative controls."""
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
from validate_e06_runtime import (
    AUDIT, INSTALLED, APPROVALS, REQUIRED_FILES, check, validate_metadata,
    historical_material, historical_metadata, HISTORICAL_METADATA,
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


class MetadataReceiptTests(unittest.TestCase):
    def test_lf_and_email_crlf_payload_preserve_raw_identity(self):
        with metadata_fixture() as (root, summary, raw):
            first = validate_metadata(summary, root)
            crlf = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            summary["distributionMetadata"] = receipt(crlf)
            second = validate_metadata(summary, root)
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["readmeSha256"], second["readmeSha256"])
            self.assertEqual(second["normalization"], "email CRLF to LF only")
            self.assertIs(second["historicalExecutionAuthenticated"], False)

    def test_content_and_terminal_newline_are_never_stripped(self):
        with metadata_fixture() as (root, summary, raw):
            for mutated in (raw + b"\n", raw[:-1], raw + b"changed", raw.replace(b"\n\n", b"\n\n\r", 1)):
                with self.subTest(suffix=mutated[-20:]):
                    summary["distributionMetadata"] = receipt(mutated)
                    with self.assertRaisesRegex(ValueError, "README bytes"):
                        validate_metadata(summary, root)

    def test_duplicate_headers_and_unsafe_archive_member_rejected(self):
        with metadata_fixture() as (root, summary, raw):
            summary["distributionMetadata"] = receipt(b"Name: other\n" + raw)
            with self.assertRaisesRegex(ValueError, "duplicate METADATA"):
                validate_metadata(summary, root)
            for path in ("../py_elk-0.0.1a0.dist-info/METADATA", "py_elk-0.0.1a0.dist-info/../METADATA", "py_elk-0.0.1a0.dist-info\\METADATA"):
                summary["distributionMetadata"] = receipt(raw)
                summary["distributionMetadata"]["archivePath"] = path
                with self.assertRaisesRegex(ValueError, "METADATA archive"):
                    validate_metadata(summary, root)

    def test_rebound_python_dependency_and_development_classification_fail(self):
        with metadata_fixture() as (root, summary, raw):
            changes = [(b"Requires-Python: >=3.11", b"Requires-Python: >=3.12", "Requires-Python"),
                       (b"build==1.6.1", b"build==0.0.1", "Requires-Dist"),
                       (b"Development Status :: 3 - Alpha", b"Development Status :: 5 - Production/Stable", "classifiers")]
            for old, new, error in changes:
                self.assertIn(old, raw)
                summary["distributionMetadata"] = receipt(raw.replace(old, new))
                with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                    validate_metadata(summary, root)

    def test_rebound_version_name_and_extra_do_not_match_current_project(self):
        with metadata_fixture() as (root, summary, raw):
            for old, new, error in [(b"Version: 0.0.1a0", b"Version: 0.0.2a0", "version"),
                                    (b"Name: py-elk", b"Name: unrelated", "name"),
                                    (b"Provides-Extra: dev", b"Provides-Extra: other", "extras")]:
                summary["distributionMetadata"] = receipt(raw.replace(old, new))
                with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                    validate_metadata(summary, root)

    def test_invalid_bytes_and_missing_metadata_do_not_validate(self):
        with metadata_fixture() as (root, summary, raw):
            summary["distributionMetadata"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "METADATA bytes"):
                validate_metadata(summary, root)
            summary["distributionMetadata"] = receipt(raw)
            summary["distributionMetadata"]["bytesBase64"] = "not!base64"
            with self.assertRaises(ValueError):
                validate_metadata(summary, root)
            summary.pop("distributionMetadata")
            with self.assertRaises(KeyError):
                validate_metadata(summary, root)


@contextmanager
def offline_copy():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        copy_files(ROOT, root, runtime_paths(ROOT, "E06"))
        # These tests exercise the frozen E06 package, even after E07 changes
        # the current sources, README and declarations.
        declarations, package = historical_material(root)
        for name, raw in package.items():
            target = root / "src/pyelk" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for name, value in declarations.items():
            save(root / name, value)
        material = load(root / "references/history/E06/metadata-material.json")
        for name in HISTORICAL_METADATA:
            (root / name).write_bytes(base64.b64decode(material["files"][name]["bytesBase64"], validate=True))
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


class E06CurrentRuntimeTests(unittest.TestCase):
    def negative(self, path, mutate, message):
        with offline_copy() as root:
            self.assertEqual(check(root)["errors"], [], "The unmodified audit fixture must pass")
            value = load(root / path)
            mutate(value)
            save(root / path, value)
            rebind(root, path)
            result = check(root)
            self.assertEqual(result["status"], "FAIL", result)
            self.assertIs(result["currentPackageBytesValidated"], False)
            self.assertIn(message, " ".join(result["errors"]))

    def test_actual_current_e06_receipt_passes_without_raw_runs(self):
        with offline_copy() as root:
            self.assertFalse((root / "test-runs").exists())
            self.assertFalse((root / ".local").exists())
            result = check(root)
            self.assertEqual(result["errors"], [], result)
            self.assertIs(result["currentPackageBytesValidated"], True)
            self.assertIs(result["currentDistributionMetadataValidated"], True)
            for key in ("historicalPackageBytesValidated", "historicalWheelAuthenticated", "runtimeReexecuted", "mathematicalEquivalenceAutomaticallyProved"):
                self.assertIs(result[key], False)

    def test_new_current_runtime_cannot_be_certified_from_history(self):
        with offline_copy() as root:
            source = root / "src/pyelk/algorithms/layered/cycles.py"
            source.write_bytes(source.read_bytes() + b"\n# changed current package\n")
            result = check(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("Current package bytes", " ".join(result["errors"]))
            past = check(root, historical=True)
            self.assertEqual(past["errors"], [], past)
            self.assertIs(past["currentPackageBytesValidated"], False)
            self.assertIs(past["historicalPackageBytesValidated"], True)

    def test_historical_metadata_cannot_rebind_archive_or_frozen_readme(self):
        with offline_copy() as root:
            material = load(root / "references/history/E06/metadata-material.json")
            row = material["files"]["README.md"]
            raw = base64.b64decode(row["bytesBase64"], validate=True) + b"changed\n"
            row.update(sha256=hashlib.sha256(raw).hexdigest(), bytesBase64=base64.b64encode(raw).decode("ascii"))
            save(root / "references/history/E06/metadata-material.json", material)
            self.assertIn("Historical metadata material", " ".join(check(root, historical=True)["errors"]))
        with offline_copy() as root:
            installed = load(root / INSTALLED)
            raw = base64.b64decode(installed["distributionMetadata"]["bytesBase64"], validate=True)
            installed["distributionMetadata"] = receipt(raw.replace(b"\r\n", b"\n"))
            save(root / INSTALLED, installed)
            with self.assertRaisesRegex(ValueError, "Historical METADATA receipt"):
                historical_metadata(root, installed)

    def test_all_source_approvals_are_required_even_after_sha_rebinding(self):
        self.negative(APPROVALS, lambda value: value["approvals"].pop(), "source gate")

    def test_full_scope_and_original_case_denominators_cannot_shrink(self):
        self.negative(AUDIT, lambda value: value["coverageDenominators"].update(selectedMasterCases=14), "denominator")
        self.negative(AUDIT, lambda value: value["scope"].update(maximumInternalNodes=64), "bounded scope")
        self.negative(INSTALLED, lambda value: value["cases"].pop(), "Installed case IDs")

    def test_every_packaged_license_and_python_file_is_required(self):
        self.negative(INSTALLED, lambda value: value["packageFilesSha256"].pop("_licenses/NOTICE-E06.md"), "file denominator")
        with offline_copy() as root:
            (root / "src/pyelk/_licenses/extra-source-LICENSE.txt").write_bytes(b"new required license\n")
            result = check(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("file denominator", " ".join(result["errors"]))

    def test_repetition_and_real_e06_command_roles_are_required(self):
        self.negative(INSTALLED, lambda value: value.update(repeat=2), ">=3")
        def wrong_approval(value):
            row = next(row for row in value["commands"] if row["name"] == "source-approval")
            row["argv"][1] = "scripts/validate_e05_source_bindings.py"
        self.negative(INSTALLED, wrong_approval, "source approval")

    def test_rebound_metadata_cannot_hide_different_python_requirement(self):
        def mutate(value):
            raw = base64.b64decode(value["distributionMetadata"]["bytesBase64"], validate=True)
            self.assertIn(b"Requires-Python: >=3.11", raw)
            value["distributionMetadata"] = receipt(raw.replace(b"Requires-Python: >=3.11", b"Requires-Python: >=3.12"))
        self.negative(INSTALLED, mutate, "Requires-Python")

    def test_nested_full_acceptance_and_missing_metadata_are_rejected(self):
        self.negative(AUDIT, lambda value: value.update(nested={"fullAlgorithmAccepted": True}), "fullAlgorithmAccepted")
        self.negative(AUDIT, lambda value: value.update(nested={"mathematicalEquivalenceAutomaticallyProved": True}), "mathematicalEquivalenceAutomaticallyProved")
        self.negative(INSTALLED, lambda value: value.pop("distributionMetadata"), "distributionMetadata")


if __name__ == "__main__":
    unittest.main()
