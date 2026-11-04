"""Rebound semantic controls for the current E05 installed evidence."""
from contextlib import contextmanager
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load, sha256
from validate_e05_runtime import (AUDIT, INSTALLED, REQUIRED_FILES, SUITE, check,
                                 historical_material, HISTORICAL_MATERIAL, HISTORICAL_WHEEL)
from audit_fixture_support import copy_files, runtime_paths


def save(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


@contextmanager
def offline_copy():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        copy_files(ROOT, root, runtime_paths(ROOT, "E05"))
        declarations, package = historical_material(ROOT)
        for name, document in declarations.items():
            save(root / name, document)
        for name, raw in package.items():
            target = root / "src/pyelk" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        yield root


def rebind(root, changed):
    if changed in REQUIRED_FILES:
        audit = load(root / AUDIT)
        audit["filesSha256"][changed] = sha256(root / changed)
        save(root / AUDIT, audit)
    fingerprint = sha256(root / AUDIT)
    for name in ("UPSTREAM.json", "docs/compatibility.json"):
        document = load(root / name)

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
        save(root / name, document)


class E05RuntimeEvidenceTests(unittest.TestCase):
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

    def test_actual_current_receipt_passes_without_raw_runs_or_installed_venv(self):
        with offline_copy() as root:
            result = check(root)
            self.assertEqual(result["errors"], [], result)
            self.assertIs(result["currentPackageBytesValidated"], True)
            self.assertIs(result["runtimeReexecuted"], False)
            self.assertIs(result["historicalWheelAuthenticated"], False)

    def test_historical_mode_does_not_certify_changed_current_runtime(self):
        with offline_copy() as root:
            self.assertEqual(check(root)["errors"], [])
            target = root / "src/pyelk/algorithms/layered/routing.py"
            target.write_bytes(target.read_bytes() + b"\n# later current runtime\n")
            self.assertEqual(check(root)["status"], "FAIL")
            result = check(root, historical=True)
            self.assertEqual(result["errors"], [], result)
            self.assertIs(result["currentPackageBytesValidated"], False)
            self.assertIs(result["historicalPackageBytesValidated"], True)
            self.assertIs(result["runtimeReexecuted"], False)

    def test_frozen_archive_and_declarations_cannot_rebind_their_identity(self):
        with offline_copy() as root:
            target = root / HISTORICAL_WHEEL
            target.write_bytes(target.read_bytes() + b"changed archive")
            result = check(root, historical=True)
            self.assertIn("Historical wheel bytes differ", " ".join(result["errors"]))
        with offline_copy() as root:
            target = root / HISTORICAL_MATERIAL
            material = load(target)
            declaration = material["declarations"]["UPSTREAM.json"]
            changed = base64.b64decode(declaration["bytesBase64"]) + b"\n"
            declaration.update(bytesBase64=base64.b64encode(changed).decode("ascii"),
                               sha256=hashlib.sha256(changed).hexdigest())
            save(target, material)
            result = check(root, historical=True)
            self.assertIn("Historical declaration bytes differ", " ".join(result["errors"]))

    def test_rebound_scope_and_coverage_cannot_expand_or_shrink(self):
        self.negative(AUDIT, lambda d: d["scope"].update(maximumNodes=9), "bounded scope")
        self.negative(AUDIT, lambda d: d["coverageDenominators"].update(sliceCases=35), "denominator")
        self.negative(SUITE, lambda d: d["cases"].pop(), "all36")

    def test_rebound_runtime_success_requires_every_real_case_check(self):
        for key in ("passed", "nativePublicExact", "candidateGeometry", "candidateInputPreserved"):
            with self.subTest(key=key):
                self.negative(INSTALLED, lambda d: d["cases"][0].update({key: False}), "case check failed")

    def test_rebound_request_identity_seed_and_repetitions_remain_bound(self):
        self.negative(INSTALLED, lambda d: d["cases"][0].update(requestSha256="0" * 64), "request SHA")
        self.negative(INSTALLED, lambda d: d["cases"][0]["candidateDeterminism"].update(seed=991), "deterministic context")
        self.negative(INSTALLED, lambda d: d["cases"][0].update(repetitionsCompared=2), "repetitions differ")

    def test_current_package_cannot_borrow_an_old_wheel_receipt(self):
        with offline_copy() as root:
            path = root / "src/pyelk/algorithms/layered/routing.py"
            path.write_bytes(path.read_bytes() + b"\n# later implementation\n")
            result = check(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("Current package bytes differ", " ".join(result["errors"]))

    def test_capture_must_use_full_source_gate_same_suite_and_clean_environment(self):
        self.negative(INSTALLED, lambda d: d["commands"][1]["argv"].__setitem__(2, "--with-upstream"), "source approval command")
        self.negative(INSTALLED, lambda d: d["commands"][5].update(environmentPolicy="inherited"), "environment is not isolated")

        def other_suite(document):
            argv = document["commands"][5]["argv"]
            argv[argv.index("--cases") + 1] = "tests/fixtures/suites/E04/cases.json"
        self.negative(INSTALLED, other_suite, "same E05 suite")

    def test_full_algorithm_release_and_boolean_count_promotions_fail(self):
        self.negative(AUDIT, lambda d: d["runtimeClaims"].update(fullAlgorithmAccepted=True), "runtime claims")
        self.negative(AUDIT, lambda d: d.update(pythonAlgorithmsVerified=False), "Full algorithm count")
        self.negative(INSTALLED, lambda d: d.update(packagePublished=True), "publication")

    def test_failed_or_timed_out_command_cannot_be_rebound_as_success(self):
        self.negative(INSTALLED, lambda d: d["commands"][4].update(exitCode=1), "command failed")
        self.negative(INSTALLED, lambda d: d["commands"][4].update(timedOut=True), "timed out")
