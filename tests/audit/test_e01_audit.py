"""Negative controls for source evidence and the required parallel/retro workflow."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load
from validate_e01_audit import check, check_plan
from audit_fixture_support import copy_files, e01_paths


class ParallelPlanTests(unittest.TestCase):
    def altered(self, mutate):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            for name in ("iteration-plan.json", "TASKS.md", "PARALLEL_EXECUTION.md"):
                shutil.copyfile(ROOT / "docs" / name, root / "docs" / name)
            plan_path = root / "docs/iteration-plan.json"
            plan = load(plan_path)
            # Keep this fixture independent of completed retrospectives on disk.
            for item in plan["iterations"] + plan["integration"]:
                item["status"] = "planned"
            # Negative controls must not inherit verified gates/evidence from live progress.
            for gate in plan["gates"]:
                gate["status"] = "unverified"
                gate["evidence"] = []
            mutate(plan)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            return check_plan(root)

    def test_current_plan(self):
        self.assertEqual(self.altered(lambda p: None), [])

    def test_slot_limit_is_explicit(self):
        errors = self.altered(lambda p: p["coordination"].update(maxSubagents=4))
        self.assertIn("Parallel slot limits differ", errors)

    def test_dependency_cycle_rejected(self):
        errors = self.altered(lambda p: p["iterations"][0].update(dependsOn=["E02"]))
        self.assertTrue(any("cycle" in e for e in errors))

    def test_complete_requires_retrospective(self):
        errors = self.altered(lambda p: p["iterations"][0].update(status="complete", evidence=[]))
        self.assertTrue(any("retrospective" in e for e in errors))

    def test_verified_gate_requires_evidence(self):
        errors = self.altered(lambda p: p["gates"][0].update(status="verified", evidence=[]))
        self.assertIn("Verified gate requires evidence: algorithm-source", errors)

    def test_every_round_has_parallel_strategy(self):
        errors = self.altered(lambda p: p["iterations"][5].pop("parallelStrategy"))
        self.assertTrue(any("parallel strategy: E06" in e for e in errors))

    def test_retro_and_stable_barrier_cannot_be_disabled(self):
        errors = self.altered(lambda p: p["coordination"].update(stableValidationBarrierRequired=False))
        self.assertTrue(any("Stable validation" in e for e in errors))

    def test_standalone_release_cannot_depend_on_integration(self):
        errors = self.altered(lambda p: p["iterations"][0].update(dependsOn=["I0"]))
        self.assertIn("Standalone package must precede integration", errors)

    def test_complete_cannot_bypass_dependencies_and_gates(self):
        def mutate(plan):
            plan["iterations"][3].update(status="complete", evidence=[{"path": "docs/TASKS.md", "sha256": "0" * 64}], retrospective="PARALLEL_EXECUTION.md")
        errors = self.altered(mutate)
        self.assertTrue(any("incomplete dependencies: E04" in e for e in errors))
        self.assertTrue(any("unverified gates: E04" in e for e in errors))
        self.assertTrue(any("Evidence SHA256 mismatch" in e for e in errors))
        self.assertTrue(any("Retrospective must belong" in e for e in errors))

    def test_verified_gate_cannot_use_forged_evidence(self):
        errors = self.altered(lambda p: p["gates"][0].update(status="verified", evidence=[{"path": "docs/TASKS.md", "sha256": "0" * 64}]))
        self.assertTrue(any("Evidence SHA256 mismatch" in e for e in errors))

    def test_first_release_iteration_denominator_is_exact(self):
        errors = self.altered(lambda p: p["firstReleaseIterations"].pop())
        self.assertIn("First-release iteration denominator differs", errors)

    def test_standalone_policy_cannot_be_changed(self):
        errors = self.altered(lambda p: p.update(mermaidIntegrationRequiredForFirstRelease=True))
        self.assertIn("Standalone integration policy differs", errors)


class EvidenceTests(unittest.TestCase):
    def test_actual_audit(self):
        self.assertEqual(check()["errors"], [])

    def test_tampered_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_files(ROOT, root, e01_paths(ROOT))
            path = root / "references/layered-default-path.json"
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertTrue(any("SHA256 mismatch" in e for e in check(root)["errors"]))

    def rehashed_mapping(self, mutate):
        from layout_checks import sha256
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_files(ROOT, root, e01_paths(ROOT))
            path = root / "references/port-map.json"
            data = load(path)
            mutate(data)
            path.write_text(json.dumps(data), encoding="utf-8")
            manifest_path = root / "references/e01-audit.json"
            manifest = load(manifest_path)
            manifest["filesSha256"]["references/port-map.json"] = sha256(path)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            return check(root)["errors"]

    def test_component_denominator_cannot_be_shrunk_even_after_rehash(self):
        def mutate(data):
            data["components"].pop()
            data["totals"]["mappedComponents"] -= 1
        self.assertTrue(any("component denominator" in e for e in self.rehashed_mapping(mutate)))

    def test_duplicate_layer_sweep_cannot_be_deduplicated(self):
        def mutate(data):
            data["defaultSingleEdgeSequence"] = list(dict.fromkeys(data["defaultSingleEdgeSequence"]))
            data["totals"]["defaultSingleEdgeCalls"] = len(data["defaultSingleEdgeSequence"])
        self.assertTrue(any("processor sequence" in e for e in self.rehashed_mapping(mutate)))

    def test_mapped_option_default_cannot_be_faked(self):
        def mutate(data):
            component = next(c for c in data["components"] if c["id"] == "option:org.eclipse.elk.separateConnectedComponents")
            component["declaredDefault"] = 1
        self.assertTrue(any("option default" in e for e in self.rehashed_mapping(mutate)))

    def test_source_audit_cannot_claim_python_algorithms(self):
        errors = self.rehashed_mapping(lambda d: d["totals"].update(pythonAlgorithmsVerified=1))
        self.assertTrue(any("cannot certify Python" in e for e in errors))

    def test_empty_or_missing_python_symbol_is_rejected(self):
        for mutation in (lambda d: d["components"][0]["pythonTargets"][0].update(symbol=""),
                         lambda d: d["components"][0]["pythonTargets"][0].pop("symbol"),
                         lambda d: d["components"][0]["pythonTargets"][0].update(symbol="pyelk.class")):
            self.assertTrue(any("Invalid planned Python symbol" in e for e in self.rehashed_mapping(mutation)))

    def test_wrong_source_span_is_detected_offline_against_path_index(self):
        errors = self.rehashed_mapping(lambda d: d["components"][0]["sourceRefs"][0].update(spanSha256="0" * 64))
        self.assertTrue(any("Source span differs from path audit" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
