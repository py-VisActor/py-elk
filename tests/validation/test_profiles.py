"""Explicit native-profile tooling tests; synthetic outputs are not Python layout.

Official observations supply reference data. Native candidate observations below
are constructed solely to test the validator's contract, geometry and CLI gates.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_checks
from layout_checks import NATIVE_PROFILE, compare_captures, compare_observations, load, sha256

REFERENCE = ROOT / "references/layout"


def fixture(case_id="layered-diamond-right"):
    index = load(REFERENCE / "index.json")
    case = next(case for case in index["cases"] if case["id"] == case_id)
    raw = (REFERENCE / case["request"]).read_bytes()
    request = json.loads(raw)
    reference = load(REFERENCE / case["observations"][0])
    return raw, request, reference, candidate_for(reference, request)


def candidate_for(reference, request):
    """Test-only desired observation. Never called by a layout implementation."""
    candidate = copy.deepcopy(reference)
    candidate["engine"] = {"name": "pyelk", "version": "SYNTHETIC-PROFILE-VALIDATOR-TEST"}
    candidate.update(inputAfter=copy.deepcopy(request["graph"]),
                     constructorAfter=copy.deepcopy(request["constructor"]),
                     argumentsAfter=copy.deepcopy(request["layoutArguments"]))
    if candidate["outcome"] == "returned":
        original, result = request["graph"], candidate["result"]
        for before, after in [(original, result), *zip(original.get("children", []), result.get("children", []))]:
            if "$H" not in before:
                after.pop("$H", None)
    return candidate


def reidentify(request, reference, candidate):
    raw = (json.dumps(request, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    for observation in (reference, candidate):
        observation["requestSha256"] = hashlib.sha256(raw).hexdigest()
    candidate.update(inputAfter=copy.deepcopy(request["graph"]), constructorAfter=copy.deepcopy(request["constructor"]),
                     argumentsAfter=copy.deepcopy(request["layoutArguments"]))
    return raw


class ObservationProfileTests(unittest.TestCase):
    def native(self, reference, candidate, raw):
        return compare_observations(reference, candidate, profile=NATIVE_PROFILE, request=raw)

    def test_strict_default_matches_explicit_and_old_field_meanings(self):
        index = load(REFERENCE / "index.json")
        for case in index["cases"]:
            raw, _, reference, candidate = fixture(case["id"])
            default = compare_observations(reference, candidate)
            explicit = compare_observations(reference, candidate, profile="strict")
            self.assertEqual(default, explicit)
            self.assertEqual(default["rawStrict"]["exact"], default["exact"])
            self.assertEqual(default["rawStrict"]["coordinateTolerance"], default["coordinateTolerance"])
            self.assertEqual(default["passed"], default["coordinateTolerance"]["passed"])

    def test_all_twenty_five_synthetic_native_pairs_match_without_hiding_raw(self):
        index = load(REFERENCE / "index.json")
        raw_mismatches = 0
        for case in index["cases"]:
            with self.subTest(case=case["id"]):
                raw, _, reference, candidate = fixture(case["id"])
                result = self.native(reference, candidate, raw)
                self.assertTrue(result["passed"], result)
                self.assertTrue(result["inputPreservation"]["preserved"])
                self.assertEqual(result["lifecycleObservations"]["acceptance"], "NOT_ASSESSED")
                raw_mismatches += not result["rawStrict"]["passed"]
        self.assertGreater(raw_mismatches, 0)

    def test_original_request_and_observations_are_not_mutated(self):
        raw, request, reference, candidate = fixture()
        before = copy.deepcopy((request, reference, candidate))
        self.native(reference, candidate, raw)
        self.assertEqual((request, reference, candidate), before)

    def test_matching_successful_results_must_each_stay_in_flat_model_scope(self):
        mutations = [
            ("root-ports", lambda graph: graph.update(ports=[{"id": "p"}])),
            ("root-label", lambda graph: graph.update(labels=[{"text": "extra"}])),
            ("child-ports", lambda graph: graph["children"][0].update(ports=[{"id": "p"}])),
            ("child-label", lambda graph: graph["children"][0].update(labels=[{"text": "extra"}])),
            ("nested-child", lambda graph: graph["children"][0].update(children=[{"id": "nested", "width": 1, "height": 1}])),
            ("nested-edge", lambda graph: graph["children"][0].update(edges=[{"id": "nested-edge"}])),
            ("edge-label", lambda graph: graph["edges"][0].update(labels=[{"text": "extra"}])),
            ("hyperedge", lambda graph: graph["edges"][0].update(sources=["a", "b"])),
            ("primitive-edge", lambda graph: graph["edges"][0].update(source="a", target="b")),
            ("unknown-endpoint", lambda graph: graph["edges"][0].update(targets=["missing"])),
            ("alternate-root-frame", lambda graph: graph["layoutOptions"].update({"elk.json.shapeCoords": "ROOT"})),
            ("alternate-child-frame", lambda graph: graph["children"][0].update(layoutOptions={"elk.json.edgeCoords": "ROOT"})),
        ]
        for identity, mutate in mutations:
            for side in ("reference", "candidate", "both"):
                with self.subTest(identity=identity, side=side):
                    raw, _, reference, candidate = fixture()
                    if side in ("reference", "both"):
                        mutate(reference["result"])
                        reference["inputAfter"] = copy.deepcopy(reference["result"])
                    if side in ("candidate", "both"):
                        mutate(candidate["result"])
                    report = self.native(reference, candidate, raw)
                    self.assertFalse(report["passed"])
                    scope_sides = {item.get("side") for item in report["publicContract"]["violations"]
                                   if item["path"] == "/result"}
                    self.assertIn("reference" if side == "both" else side, scope_sides)
                    if side == "both":
                        self.assertIn("candidate", scope_sides)

    def test_path_and_bytes_are_equivalent_but_parsed_dict_is_not_evidence(self):
        raw, request, reference, candidate = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_bytes(raw)
            self.assertEqual(self.native(reference, candidate, raw), self.native(reference, candidate, path))
        with self.assertRaisesRegex(ValueError, "Path or bytes"):
            self.native(reference, candidate, request)

    def test_reserialized_request_identity_and_unknown_profile_are_rejected(self):
        raw, request, reference, candidate = fixture()
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.native(reference, candidate, json.dumps(request).encode())
        with self.assertRaisesRegex(ValueError, "Unknown comparison profile"):
            compare_observations(reference, candidate, profile="invented", request=raw)
        with self.assertRaisesRegex(ValueError, "Path or bytes"):
            compare_observations(reference, candidate, profile=NATIVE_PROFILE)

    def test_duplicate_keys_and_nonfinite_request_context_fail(self):
        _, _, reference, candidate = fixture()
        for raw in (b'{"schema":"py-elk-layout-request/v1","constructor":{},"constructor":{},"graph":null,"layoutArguments":{}}',
                    b'{"schema":"py-elk-layout-request/v1","constructor":{},"graph":NaN,"layoutArguments":{}}'):
            digest = hashlib.sha256(raw).hexdigest()
            reference["requestSha256"] = candidate["requestSha256"] = digest
            with self.assertRaises(ValueError):
                self.native(reference, candidate, raw)

    def test_reference_and_candidate_engine_identity_are_required(self):
        raw, _, reference, candidate = fixture()
        for key, value in (("version", "0.12.0"), ("entrypointSha256", "0" * 64), ("name", "other")):
            changed = copy.deepcopy(reference)
            changed["engine"][key] = value
            with self.assertRaisesRegex(ValueError, "engine identity"):
                self.native(changed, candidate, raw)
        candidate["engine"]["name"] = "elkjs"
        with self.assertRaisesRegex(ValueError, "pyelk candidate"):
            self.native(reference, candidate, raw)

    def test_omission_and_null_option_container_are_distinct(self):
        for owner, key in (("constructor", "defaultLayoutOptions"), ("layoutArguments", "layoutOptions"), ("graph", "layoutOptions")):
            for value in (None, False, 0, ""):
                raw, request, reference, candidate = fixture()
                request[owner][key] = value
                raw = reidentify(request, reference, candidate)
                with self.subTest(owner=owner, value=value), self.assertRaisesRegex(ValueError, "option containers"):
                    self.native(reference, candidate, raw)

    def test_explicit_worker_parameters_never_use_truthiness(self):
        for key in ("workerUrl", "workerFactory"):
            for value in (None, False, ""):
                _, request, reference, candidate = fixture()
                request["constructor"][key] = value
                raw = reidentify(request, reference, candidate)
                with self.assertRaisesRegex(ValueError, "worker"):
                    self.native(reference, candidate, raw)

    def test_success_requires_layered_registration(self):
        for algorithms in ([], ["stress"], None, "layered", [False], ["org.eclipse.elk.layered"]):
            _, request, reference, candidate = fixture()
            request["constructor"]["algorithms"] = algorithms
            raw = reidentify(request, reference, candidate)
            with self.subTest(algorithms=algorithms), self.assertRaisesRegex(ValueError, "layered to be registered"):
                self.native(reference, candidate, raw)
        _, request, reference, candidate = fixture()
        request["constructor"]["algorithms"] = ["layered", "stress", "unknown-registration-name"]
        raw = reidentify(request, reference, candidate)
        reference["constructorAfter"] = copy.deepcopy(request["constructor"])
        self.assertTrue(self.native(reference, candidate, raw)["passed"])

    def test_selectors_are_presence_based_and_ambiguous_aliases_fail(self):
        for options in ({"algorithm": "layered"}, {"elk.algorithm": "layered", "org.eclipse.elk.algorithm": "layered"},
                        {"elk.algorithm": "stress"}, {"elk.edgeRouting": "POLYLINE"}):
            _, request, reference, candidate = fixture()
            request["graph"]["layoutOptions"] = options
            raw = reidentify(request, reference, candidate)
            with self.assertRaisesRegex(ValueError, "selector"):
                self.native(reference, candidate, raw)

    def test_alternate_child_frame_and_hierarchy_fail_closed(self):
        for options in ({"elk.json.shapeCoords": "ROOT"}, {"elk.json.edgeCoords": "ROOT"}, {"elk.hierarchyHandling": "INCLUDE_CHILDREN"}):
            _, request, reference, candidate = fixture()
            request["graph"]["children"][0]["layoutOptions"] = options
            raw = reidentify(request, reference, candidate)
            with self.assertRaisesRegex(ValueError, "outside native profile scope"):
                self.native(reference, candidate, raw)

    def test_draft_or_boolean_revision_contract_is_not_usable(self):
        raw, _, reference, candidate = fixture()
        original_load = layout_checks.load
        for change in ({"status": "draft"}, {"revision": True}):
            def altered(path):
                value = original_load(path)
                if path.name == "native-contract.json":
                    value.update(change)
                return value
            with patch.object(layout_checks, "load", side_effect=altered), self.assertRaisesRegex(ValueError, "definition identity"):
                self.native(reference, candidate, raw)

    def test_input_preservation_does_not_apply_coordinate_tolerance(self):
        _, request, reference, candidate = fixture()
        request["graph"]["children"][0]["x"] = 10.0
        raw = reidentify(request, reference, candidate)
        candidate["inputAfter"]["children"][0]["x"] += 1e-8
        result = self.native(reference, candidate, raw)
        self.assertFalse(result["inputPreservation"]["preserved"])
        self.assertFalse(result["passed"])

    def test_non_graph_or_non_array_return_cannot_pass_by_equal_copy(self):
        raw, _, reference, candidate = fixture()
        for changed in (None, [], {"id": "root", "children": None}):
            ref = copy.deepcopy(reference)
            actual = copy.deepcopy(candidate)
            ref["result"] = ref["inputAfter"] = copy.deepcopy(changed)
            actual["result"] = copy.deepcopy(changed)
            self.assertFalse(self.native(ref, actual, raw)["passed"])

    def test_result_logging_and_timing_numbers_remain_exact(self):
        raw, _, reference, candidate = fixture()
        reference["result"]["logging"] = {"name": "phase", "executionTime": 1.0}
        reference["inputAfter"] = copy.deepcopy(reference["result"])
        candidate["result"]["logging"] = {"name": "phase", "executionTime": 1.0 + 1e-10}
        self.assertFalse(self.native(reference, candidate, raw)["passed"])


def synthetic_capture(directory, change=None):
    shutil.copytree(REFERENCE, directory)
    index = load(directory / "index.json")
    index["role"] = "candidate"
    for case in index["cases"]:
        request = load(directory / case["request"])
        for repetition, name in enumerate(case["observations"]):
            p = directory / name
            observation = candidate_for(load(p), request)
            if change:
                change(case["id"], repetition, observation)
            p.write_text(json.dumps(observation), encoding="utf-8")
            index["files"][name] = sha256(p)
    (directory / "index.json").write_text(json.dumps(index), encoding="utf-8")


class CaptureProfileTests(unittest.TestCase):
    def test_full_synthetic_native_capture_uses_selected_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "synthetic-native"
            synthetic_capture(target)
            result = compare_captures(REFERENCE, target, profile=NATIVE_PROFILE)
            self.assertTrue(result["passed"])
            self.assertEqual(result["caseCount"], 25)
            self.assertTrue(any(not comparison["rawStrict"]["passed"] for case in result["cases"] for comparison in case["comparison"]))
            self.assertFalse(compare_captures(REFERENCE, target)["passed"])

    def test_geometric_failure_overrides_a_tolerant_public_match(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "negative-root-size"
            def change(identity, repetition, observation):
                if identity == "layered-empty":
                    observation["result"]["width"] = -1e-7
            synthetic_capture(target, change)
            result = compare_captures(REFERENCE, target, profile=NATIVE_PROFILE)
            case = next(c for c in result["cases"] if c["id"] == "layered-empty")
            self.assertTrue(case["comparison"][0]["passed"])
            self.assertFalse(case["geometry"][0]["passed"])
            self.assertFalse(case["passed"])
            self.assertFalse(result["passed"])

    def test_fresh_process_determinism_overrides_tolerant_public_match(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nondeterministic"
            def change(identity, repetition, observation):
                if identity == "layered-diamond-right" and repetition:
                    observation["result"]["width"] += 1e-7
            synthetic_capture(target, change)
            result = compare_captures(REFERENCE, target, profile=NATIVE_PROFILE)
            case = next(c for c in result["cases"] if c["id"] == "layered-diamond-right")
            self.assertTrue(all(c["passed"] for c in case["comparison"]))
            self.assertFalse(case["candidateDeterminism"]["passed"])
            self.assertFalse(result["passed"])

    def test_raw_coordinate_failure_overrides_legal_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "coordinate-drift"
            def change(identity, repetition, observation):
                if identity == "layered-diamond-right":
                    observation["result"]["width"] += 10
            synthetic_capture(target, change)
            result = compare_captures(REFERENCE, target, profile=NATIVE_PROFILE)
            case = next(c for c in result["cases"] if c["id"] == "layered-diamond-right")
            self.assertTrue(all(g["passed"] for g in case["geometry"]))
            self.assertFalse(case["comparison"][0]["passed"])
            self.assertFalse(result["passed"])

    def test_replay_never_uses_native_host_projection(self):
        with self.assertRaisesRegex(ValueError, "replay requires"):
            compare_captures(REFERENCE, REFERENCE, replay=True, profile=NATIVE_PROFILE)


class ProfileCliTests(unittest.TestCase):
    def test_pair_selects_native_profile_and_requires_original_request(self):
        raw, _, reference, candidate = fixture()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "request.json").write_bytes(raw)
            for name, value in (("reference", reference), ("candidate", candidate)):
                (target / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
            base = [sys.executable, str(ROOT / "scripts/validate_layout.py"), "pair", "--expected", str(target / "reference.json"),
                    "--actual", str(target / "candidate.json"), "--profile", NATIVE_PROFILE]
            result = subprocess.run([*base, "--request", str(target / "request.json"), "--out", str(target / "native.json")], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = load(target / "native.json")
            self.assertTrue(report["passed"])
            self.assertFalse(report["rawStrict"]["passed"])
            missing = subprocess.run([*base, "--out", str(target / "missing.json")], capture_output=True)
            self.assertEqual(missing.returncode, 2, missing.stderr)

    def test_replay_and_raw_json_do_not_accept_native_flag(self):
        for action in ("replay", "json"):
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_layout.py"), action, "--profile", NATIVE_PROFILE], capture_output=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
