"""Actual small check before malformed receipt controls for the change audit."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("iteration_changes", ROOT / "scripts/iteration/check_changes.py")
audit = importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class IterationChangeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.folder = Path(cls.directory.name)
        argv = [sys.executable, "-m", "unittest", "discover", "-s", "tests/validation", "-p", "test_change_impact.py", "-v"]
        started = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, check=True)
        for stream, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
            (cls.folder / (stream + ".log")).write_bytes(raw)
        import re
        count = int(re.search(rb"Ran (\d+) tests?", result.stderr)[1])
        cls.command = {"argv": argv, "cwd": str(ROOT), "exitCode": result.returncode, "timedOut": False,
                       "elapsedSeconds": time.monotonic() - started,
                       "stdoutSha256": hashlib.sha256(result.stdout).hexdigest(),
                       "stderrSha256": hashlib.sha256(result.stderr).hexdigest()}
        cls.definition = {"id": "actual-impact-check", "directory": str(cls.folder), "argv": argv, "cwd": str(ROOT), "tests": count}

    def setUp(self):
        (self.folder / "command.json").write_text(json.dumps(self.command), encoding="utf-8")

    def test_genuine_command_and_original_logs_are_preserved(self):
        value = audit.verify_check(self.definition)
        self.assertEqual(value["tests"], self.definition["tests"])
        self.assertEqual(value["actualCommand"], self.command)
        self.assertTrue(value["originalMaterial"]["stderr"]["bytesBase64"])

    def test_boolean_exit_or_changed_original_log_cannot_be_a_pass(self):
        self.assertEqual(audit.verify_check(self.definition)["tests"], self.definition["tests"])
        changed = copy.deepcopy(self.command);changed["exitCode"] = False
        (self.folder / "command.json").write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "failed"):
            audit.verify_check(self.definition)
        self.setUp()
        path = self.folder / "stderr.log";raw = path.read_bytes()
        try:
            path.write_bytes(raw + b" changed")
            with self.assertRaisesRegex(ValueError, "log bytes"):
                audit.verify_check(self.definition)
        finally:
            path.write_bytes(raw)
        self.assertEqual(audit.verify_check(self.definition)["tests"], self.definition["tests"])

    def test_wrong_command_or_empty_check_selection_is_rejected(self):
        definition = copy.deepcopy(self.definition);definition["argv"][-1] = "--different"
        with self.assertRaisesRegex(ValueError, "identity"):
            audit.verify_check(definition)
        manifest = self.folder / "manifest.json";baseline = self.folder / "baseline.json"
        manifest.write_text(json.dumps({"iteration": "fixture", "checks": []}), encoding="utf-8")
        baseline.write_text(json.dumps({"inputFilesSha256": {"README.md": "0" * 64}}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Missing or duplicate"):
            audit.check(manifest, baseline)


if __name__ == "__main__":
    unittest.main()
