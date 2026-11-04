"""Synthetic report controls test the closing validator, never certify layout."""
from contextlib import contextmanager
import copy
import base64
import hashlib
import json
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from change_impact import execution_context, input_hashes
from layout_checks import sha256
from validate_completion_state import CORE_STEPS, check, command_roles


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8", newline="\n")


@contextmanager
def synthetic_report():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory); report_path = root / "test-runs/full/report.json"
        plan = {"nextIteration": "E08", "gates": [{"id": "source", "status": "verified"}],
                "iterations": [{"id": "E07", "status": "complete", "evidence": []}]}
        save(root / "docs/iteration-plan.json", plan)
        (root / "src").mkdir(); (root / "src/module.py").write_bytes(b"protected source\n")
        rows = []
        for name in CORE_STEPS:
            d = report_path.parent / (name + "-command"); d.mkdir(parents=True)
            (d / "stdout.log").write_bytes(b"synthetic validator fixture only\n"); (d / "stderr.log").write_bytes(b"")
            command = {"argv": command_roles(report_path.parent)[name], "cwd": str(root.resolve()), "exitCode": 0,
                       "timedOut": False, "elapsedSeconds": 0.1,
                       "stdoutSha256": sha256(d / "stdout.log"), "stderrSha256": sha256(d / "stderr.log")}
            save(d / "command.json", command); rows.append({"name": name, **command})
        report = {"schema": "py-elk-development-check/v1", "status": "DEVELOPMENT_CHECKS_PASS", "passed": True,
                  "fullValidation": True, "checkMode": "full", "inputsUnchanged": True, "changedDuringExecution": [],
                  "plannedSteps": list(CORE_STEPS), "commands": rows, "inputFilesSha256": input_hashes(root),
                  "executionContext": execution_context(), "projectRoot": str(root.resolve()),
                  "completionPlanAtExecution": copy.deepcopy(plan),
                  "completionPlanBytesBase64": base64.b64encode((root / "docs/iteration-plan.json").read_bytes()).decode("ascii")}
        save(report_path, report)
        yield root, report_path, report


class CompletionStateTests(unittest.TestCase):
    def validate(self, root, path):
        return check(path, root, metadata_validator=lambda root: {"synthetic": True})

    def test_completion_only_record_with_unchanged_inputs_can_be_checked(self):
        with synthetic_report() as (root, path, _):
            save(root / "docs/changes/new.json", {"status": "complete", "pythonAlgorithmsVerified": 0})
            result = self.validate(root, path)
            self.assertTrue(result["completionValidated"], result)
            self.assertIs(result["runtimeReexecuted"], False)

    def test_source_test_reference_and_packaged_readme_changes_require_full(self):
        for name in ("src/module.py", "tests/new.py", "references/new.json", "README.md", "pyproject.toml"):
            with self.subTest(name=name), synthetic_report() as (root, path, _):
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"changed")
                self.assertIn("Non-completion inputs", " ".join(self.validate(root, path)["errors"]))

    def test_partial_or_missing_command_cannot_be_promoted_to_full(self):
        for field, value in (("checkMode", "affected"), ("fullValidation", False), ("commands", []), ("plannedSteps", [])):
            with self.subTest(field=field), synthetic_report() as (root, path, report):
                report[field] = value; save(path, report)
                self.assertFalse(self.validate(root, path)["completionValidated"])

    def test_log_rebinding_and_failed_command_are_rejected(self):
        with synthetic_report() as (root, path, _):
            (path.parent / "bootstrap-command/stdout.log").write_bytes(b"changed raw\n")
            self.assertIn("log differs", " ".join(self.validate(root, path)["errors"]))
        with synthetic_report() as (root, path, report):
            report["commands"][0]["exitCode"] = 1; save(path, report)
            self.assertFalse(self.validate(root, path)["completionValidated"])

    def test_gate_definition_change_is_not_completion_bookkeeping(self):
        with synthetic_report() as (root, path, report):
            plan = report["completionPlanAtExecution"]; plan["gates"][0]["status"] = "unverified"
            save(root / "docs/iteration-plan.json", plan)
            self.assertIn("Protected progress/gate", " ".join(self.validate(root, path)["errors"]))

    def test_changed_interpreter_and_source_writes_during_full_run_are_rejected(self):
        for edit in (lambda d: d["executionContext"].update(python="other"), lambda d: d.update(inputsUnchanged=False)):
            with synthetic_report() as (root, path, report):
                edit(report); save(path, report); self.assertFalse(self.validate(root, path)["completionValidated"])

    def test_completion_cannot_create_a_full_algorithm_or_publication_claim(self):
        with synthetic_report() as (root, path, _):
            save(root / "docs/changes/new.json", {"fullAlgorithmAccepted": True})
            self.assertFalse(self.validate(root, path)["completionValidated"])

    def test_rebound_owner_only_discovery_is_not_a_full_run(self):
        with synthetic_report() as (root, path, report):
            row = next(r for r in report["commands"] if r["name"] == "audit-tests")
            row["argv"] += ["-p", "test_e07_runtime.py"]
            save(path.parent / "audit-tests-command/command.json", {k:v for k,v in row.items() if k != "name"})
            save(path, report)
            self.assertIn("discover scope", " ".join(self.validate(root, path)["errors"]))

    def test_same_interpreter_with_changed_hash_seed_requires_full(self):
        with synthetic_report() as (root, path, _):
            with patch.dict("os.environ", {"PYTHONHASHSEED": "723614"}):
                self.assertIn("Interpreter/platform", " ".join(self.validate(root, path)["errors"]))

    def test_legitimate_fixture_named_build_is_never_metadata_only(self):
        with synthetic_report() as (root, path, report):
            p = root / "tests/fixtures/build/request.json"; p.parent.mkdir(parents=True); p.write_bytes(b"before")
            report["inputFilesSha256"] = input_hashes(root); save(path, report)
            p.write_bytes(b"after")
            self.assertIn("Non-completion", " ".join(self.validate(root, path)["errors"]))

    def test_rebound_plan_snapshot_cannot_lose_its_original_byte_binding(self):
        with synthetic_report() as (root, path, report):
            plan = report["completionPlanAtExecution"]
            plan["gates"][0]["status"] = "unverified"
            save(root / "docs/iteration-plan.json", plan); save(path, report)
            self.assertIn("Original plan snapshot", " ".join(self.validate(root, path)["errors"]))

    def test_protected_values_keep_json_types_when_snapshot_is_compared(self):
        with synthetic_report() as (root, path, report):
            plan = report["completionPlanAtExecution"]
            plan["gates"][0]["required"] = 1
            save(root / "docs/iteration-plan.json", plan)
            report["inputFilesSha256"] = input_hashes(root)
            report["completionPlanBytesBase64"] = base64.b64encode((root / "docs/iteration-plan.json").read_bytes()).decode("ascii")
            plan["gates"][0]["required"] = True
            save(root / "docs/iteration-plan.json", plan); save(path, report)
            self.assertIn("Original plan snapshot", " ".join(self.validate(root, path)["errors"]))
