"""Explicit Node-dependent synthetic collector controls, not default offline tests.

Run: python tests/contract/live_collector_failclosed.py --out NEW_DIRECTORY
Uses a copied collector and a clearly synthetic pinned package. The real upstream,
collector, references and their hashes are never modified by these controls.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CollectorTimeoutControls(unittest.TestCase):
    output = None
    node = "node"

    def run_synthetic(self, name, force_zero_exit):
        directory = self.output / name
        directory.mkdir()
        fixture_root = directory / "synthetic-project"
        fixture_root.mkdir()
        package = fixture_root / "package"
        (package / "lib").mkdir(parents=True)
        source = """// SYNTHETIC TEST PACKAGE: never an official elkjs artifact.
module.exports = class SyntheticELK {
  constructor() { FORCE_ZERO_EXIT }
  layout(graph) { return Promise.resolve(graph); }
  terminateWorker() { return new Promise(() => {}); }
};
""".replace("FORCE_ZERO_EXIT", "process.on('beforeExit', () => { process.exitCode = 0; });" if force_zero_exit else "")
        entry = package / "lib/elk.bundled.js"
        entry.write_text(source, encoding="utf-8", newline="\n")
        fixture_lock = json.loads((ROOT / "UPSTREAM.json").read_text(encoding="utf-8"))
        fixture_lock["distribution"]["sha256Files"] = {"lib/elk.bundled.js": hashlib.sha256(entry.read_bytes()).hexdigest()}
        fixture_lock["syntheticFixture"] = True
        (fixture_root / "UPSTREAM.json").write_text(json.dumps(fixture_lock), encoding="utf-8")
        collector = (ROOT / "tools/reference/capture_contracts.cjs").read_text(encoding="utf-8")
        original = "const ROOT = path.resolve(__dirname, '../..');"
        self.assertEqual(collector.count(original), 1)
        # Only relocate the copied tool's project root; its control flow stays exact.
        collector = collector.replace(original, "const ROOT = " + json.dumps(fixture_root.as_posix()) + ";")
        copied = fixture_root / "capture_contracts.cjs"
        copied.write_text(collector, encoding="utf-8", newline="\n")
        capture = directory / "synthetic-capture"
        argv = [self.node, str(copied), str(package), str(capture), "--only", "constructor-empty-object"]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15)
        (directory / "stdout.log").write_bytes(result.stdout)
        (directory / "stderr.log").write_bytes(result.stderr)
        (directory / "command.json").write_text(json.dumps({"argv": argv, "cwd": str(ROOT), "exitCode": result.returncode,
                                                             "synthetic": True}, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", errors="replace"))
        index = json.loads((capture / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["status"], "INCOMPLETE")
        self.assertEqual(index["probeCount"], 1)
        probe = index["probes"][0]
        self.assertEqual(probe["observation"]["calls"][0]["outcome"], "returned")
        self.assertEqual(probe["observation"]["finalTermination"]["outcome"], "timed_out")
        self.assertEqual(probe["process"]["exitCode"], 0 if force_zero_exit else 3)

    def test_final_termination_timeout_sets_nonzero_child_and_incomplete_parent(self):
        self.run_synthetic("cleanup-timeout", False)

    def test_parent_rejects_timeout_even_when_child_exit_is_forced_zero(self):
        self.run_synthetic("cleanup-timeout-spoofed-exit-zero", True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--node", default="node")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(exist_ok=False)
    CollectorTimeoutControls.output = args.out.resolve()
    CollectorTimeoutControls.node = args.node
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CollectorTimeoutControls))
    report = {"status": "SYNTHETIC_COLLECTOR_CONTROLS_PASS" if result.wasSuccessful() else "FAIL",
              "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "synthetic": True, "officialProbesAffected": 0, "pythonAlgorithmsVerified": 0,
              "limitation": "Test-only copied collector and package; not official layout or native runtime evidence."}
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
