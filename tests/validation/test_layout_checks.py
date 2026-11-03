"""Validator regressions using real official fixtures and explicitly synthetic captures.

Synthetic candidate observations test the checker only, never Python layout.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_validation_cases import generate
from layout_checks import (ABS_TOL, ROOT, compare_captures, compare_observations, contained, contract,
                           determinism, diff, geometry, input_preservation, load, seed_of, sha256, validate_suite, verify_capture, write)


class ComparisonTests(unittest.TestCase):
    def test_absolute_tolerance(self):
        a = {"result": {"x": 0.0}}
        self.assertTrue(diff(a, {"result": {"x": ABS_TOL}}, tolerant=True)["passed"])
        self.assertFalse(diff(a, {"result": {"x": ABS_TOL * 1.001}}, tolerant=True)["passed"])
        self.assertFalse(diff(a, {"result": {"x": ABS_TOL}})["passed"])

    def test_relative_tolerance(self):
        a = {"result": {"x": 1e8}}
        self.assertTrue(diff(a, {"result": {"x": 1e8 + 0.09}}, tolerant=True)["passed"])
        self.assertFalse(diff(a, {"result": {"x": 1e8 + 0.11}}, tolerant=True)["passed"])

    def test_only_geometry_numbers_receive_tolerance(self):
        for path in ("weight", "randomSeed", "id", "priority"):
            self.assertFalse(diff({path: 1}, {path: 1 + 1e-10}, tolerant=True)["passed"])
        self.assertFalse(diff({"result": {"data": {"x": 1}}}, {"result": {"data": {"x": 1 + 1e-10}}}, tolerant=True)["passed"])

    def test_ports_labels_nested_sections_and_input_mutation_coordinates(self):
        structures = [
            {"children": [{"children": [{"ports": [{"labels": [{"x": 1}]}]}]}]},
            {"children": [{"edges": [{"sections": [{"bendPoints": [{"y": 1}]}]}]}]},
            {"edges": [{"labels": [{"height": 1}], "junctionPoints": [{"x": 1}]}]},
        ]
        for structure in structures:
            a = {"result": structure, "inputAfter": copy.deepcopy(structure)}
            b = json.loads(json.dumps(a).replace(': 1', ': 1.0000001'))
            self.assertTrue(diff(a, b, tolerant=True)["passed"])
            self.assertFalse(diff(a, b)["passed"])

    def test_booleans_are_not_numbers(self):
        self.assertFalse(diff({"result": {"x": True}}, {"result": {"x": 1}}, tolerant=True)["passed"])
        self.assertTrue(diff(1, 1.0)["passed"])

    def test_no_model_array_sorting(self):
        result = diff({"children": [{"id": "a"}, {"id": "b"}]}, {"children": [{"id": "b"}, {"id": "a"}]})
        self.assertFalse(result["passed"])
        self.assertEqual(result["differences"][0]["path"], "/children/0/id")

    def test_object_key_order_is_not_model_order(self):
        self.assertTrue(diff({"a": 1, "b": 2}, {"b": 2, "a": 1})["passed"])

    def test_all_missing_extra_fields_and_array_tail_are_reported(self):
        result = diff({"a": 1, "b": None, "c": [1, 2]}, {"a": 2, "x": 3, "c": [1]})
        self.assertEqual({d["path"] for d in result["differences"]}, {"/a", "/b", "/x", "/c", "/c/1"})

    def test_pointer_escaping(self):
        self.assertEqual(diff({"a~/b": 1}, {"a~/b": 2})["differences"][0]["path"], "/a~0~1b")

    def test_no_truncation(self):
        self.assertEqual(len(diff(list(range(500)), [None] * 500)["differences"]), 500)

    def test_nonfinite_duplicate_keys_and_overflow_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "bad.json"
            for text in ('{"x": NaN}', '{"x": Infinity}', '{"x": 1e999}', '{"x": 1, "x": 2}'):
                p.write_text(text, encoding="utf-8")
                with self.subTest(text=text), self.assertRaises(ValueError):
                    load(p)
        with self.assertRaises(ValueError):
            diff(float("nan"), 1)

    def test_containment_and_write_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "one.json", {})
            with self.assertRaises(FileExistsError):
                write(root / "one.json", {})
            for path in ("../outside.json", "/absolute", "C:/absolute", "..\\outside", "missing.json"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    contained(root, path)


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = ROOT / "references/layout"
        cls.index = verify_capture(cls.reference)
        cls.case = next(c for c in cls.index["cases"] if c["id"] == "layered-diamond-right")
        cls.original = load(cls.reference / cls.case["observations"][0])
        cls.request = load(cls.reference / cls.case["request"])
        cls.policy = cls.case["definition"]["geometry"]

    def altered_geometry(self, change):
        observation = copy.deepcopy(self.original)
        change(observation["result"])
        return geometry(self.request, observation, self.policy)

    def assert_geometry_code(self, change, code):
        result = self.altered_geometry(change)
        self.assertFalse(result["passed"])
        self.assertIn(code, {e["code"] for e in result["errors"]})

    def test_official_positives_geometry_and_determinism(self):
        for case in self.index["cases"]:
            with self.subTest(case=case["id"]):
                req = load(self.reference / case["request"])
                observations = [load(self.reference / p) for p in case["observations"]]
                self.assertTrue(determinism(observations, req)["passed"])
                for obs in observations:
                    self.assertEqual(obs["outcome"], case["definition"]["expectedOutcome"])
                    result = geometry(req, obs, case["definition"]["geometry"])
                    if case["definition"]["geometry"]:
                        self.assertTrue(result["passed"], result)

    def test_generated_requests_equal_committed_inputs(self):
        current = ROOT / "tests/fixtures/validation"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "new"
            self.assertEqual(generate(target), len(self.index["cases"]))
            for p in target.rglob("*.json"):
                self.assertEqual(p.read_bytes(), (current / p.relative_to(target)).read_bytes())

    def test_duplicate_case_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "suite"
            shutil.copytree(ROOT / "tests/fixtures/validation", target)
            suite = load(target / "cases.json")
            suite["cases"].append(suite["cases"][0])
            (target / "cases.json").write_text(json.dumps(suite), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                validate_suite(target / "cases.json")

    def test_dimensions_missing_or_negative_fail(self):
        self.assert_geometry_code(lambda g: g["children"][0].pop("width"), "invalid_number")
        self.assert_geometry_code(lambda g: g["children"][0].update(width=-1), "invalid_number")

    def test_root_padding_and_extent_fail(self):
        self.assert_geometry_code(lambda g: g.update(width=1), "root_padding_bounds")

    def test_overlap_detected_independently(self):
        self.assert_geometry_code(lambda g: g["children"][1].update(x=g["children"][0]["x"], y=g["children"][0]["y"]), "node_overlap")

    def test_direction_layer_spacing(self):
        p = copy.deepcopy(self.policy)
        p["betweenLayers"] = 1000
        result = geometry(self.request, self.original, p)
        self.assertIn("direction_or_layer_spacing", {e["code"] for e in result["errors"]})

    def test_duplicate_node_identity(self):
        self.assert_geometry_code(lambda g: g["children"][1].update(id=g["children"][0]["id"]), "id_identity")

    def test_bad_endpoint(self):
        self.assert_geometry_code(lambda g: g["edges"][0]["targets"].__setitem__(0, "missing"), "endpoint_identity")

    def test_section_topology_and_id(self):
        self.assert_geometry_code(lambda g: g["edges"][0]["sections"][0].update(incomingShape="missing"), "section_connectivity")
        self.assert_geometry_code(lambda g: g["edges"][0]["sections"][0].pop("id"), "section_id")

    def test_diagonal_route(self):
        self.assert_geometry_code(lambda g: g["edges"][0]["sections"][0].update(bendPoints=[{"x": -1, "y": -2}]), "non_orthogonal_segment")

    def test_endpoint_border_and_root_bounds(self):
        self.assert_geometry_code(lambda g: g["edges"][0]["sections"][0]["startPoint"].update(x=-1, y=-2), "endpoint_not_on_node_border")
        self.assert_geometry_code(lambda g: g["edges"][0]["sections"][0]["startPoint"].update(x=-1, y=-2), "route_outside_root")

    def test_unsupported_nested_ports_labels_frames_fail_closed(self):
        for key, value in (("ports", [{"id": "port"}]), ("labels", [{"text": "test"}]), ("children", [{"id": "nested"}])):
            with self.subTest(key=key):
                result = self.altered_geometry(lambda g: g["children"][0].update({key: value}))
                self.assertEqual(result["status"], "UNSUPPORTED")
                self.assertFalse(result["passed"])
        result = self.altered_geometry(lambda g: g["layoutOptions"].update({"elk.json.shapeCoords": "ROOT"}))
        self.assertEqual(result["status"], "UNSUPPORTED")

    def test_not_checked_is_not_pass(self):
        self.assertIsNone(geometry(self.request, self.original, None)["passed"])

    def test_missing_contract_fields_fail(self):
        obs = copy.deepcopy(self.original)
        obs.pop("inputAfter")
        with self.assertRaises(ValueError):
            contract(obs)

    def test_input_side_effect_coordinates_receive_tolerance(self):
        obs = copy.deepcopy(self.original)
        obs["inputAfter"]["children"][0]["x"] += ABS_TOL / 10
        result = compare_observations(self.original, obs)
        self.assertTrue(result["coordinateTolerance"]["passed"])
        self.assertFalse(result["exact"]["passed"])

    def test_private_hash_and_generated_section_id_are_preserved(self):
        for change in (lambda o: o["result"].pop("$H"), lambda o: o["result"]["edges"][0]["sections"][0].update(id="new")):
            obs = copy.deepcopy(self.original)
            change(obs)
            self.assertFalse(compare_observations(self.original, obs)["coordinateTolerance"]["passed"])

    def test_determinism_detects_mutation_and_single_run(self):
        obs = copy.deepcopy(self.original)
        obs["result"]["children"][0]["x"] += 1e-10
        self.assertFalse(determinism([self.original, obs], self.request)["passed"])
        self.assertFalse(determinism([self.original], self.request)["passed"])

    def test_zero_seed_not_deterministic_claim(self):
        request = copy.deepcopy(self.request)
        request["graph"]["layoutOptions"]["elk.randomSeed"] = "0"
        self.assertIsNone(seed_of(request))
        self.assertFalse(determinism([self.original, self.original], request)["passed"])
        for value in (True, 1.5, "1.5", "invalid", 2 ** 40):
            request["graph"]["layoutOptions"]["elk.randomSeed"] = value
            self.assertIsNone(seed_of(request))

    def test_input_preservation_goal_is_separate_from_upstream_observation(self):
        self.assertFalse(input_preservation(self.request, self.original)["preserved"])
        observation = copy.deepcopy(self.original)
        observation["inputAfter"] = copy.deepcopy(self.request["graph"])
        self.assertTrue(input_preservation(self.request, observation)["preserved"])
        self.assertFalse(compare_observations(self.original, observation)["coordinateTolerance"]["passed"])

    def test_constructor_defaults_are_replaced_not_merged(self):
        request = {"graph": {}, "constructor": {"defaultLayoutOptions": {"elk.randomSeed": 7}}, "layoutArguments": {}}
        self.assertEqual(seed_of(request), 7)
        request["layoutArguments"] = {"layoutOptions": {}}
        self.assertIsNone(seed_of(request))

    def test_same_engine_cannot_count_as_python_acceptance(self):
        with self.assertRaisesRegex(ValueError, "roles"):
            compare_captures(self.reference, self.reference)
        self.assertTrue(compare_captures(self.reference, self.reference, replay=True)["passed"])

    def synthetic_capture(self, directory, change=None):
        """Test-only protocol fixture. No layout code, no production candidate claim."""
        shutil.copytree(self.reference, directory)
        index = load(directory / "index.json")
        index["role"] = "candidate"
        for case in index["cases"]:
            for path in case["observations"]:
                p = directory / path
                obs = load(p)
                obs["engine"] = {"name": "pyelk", "version": "SYNTHETIC-VALIDATOR-TEST"}
                if change and case["id"] == self.case["id"]:
                    change(obs)
                p.write_text(json.dumps(obs), encoding="utf-8")
                index["files"][path] = sha256(p)
        (directory / "index.json").write_text(json.dumps(index), encoding="utf-8")

    def test_batch_match_and_mismatch_report_do_not_promote_ledger(self):
        ledger_hash = sha256(ROOT / "docs/compatibility.json")
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "synthetic"
            self.synthetic_capture(candidate)
            self.assertTrue(compare_captures(self.reference, candidate)["passed"])
            candidate = Path(directory) / "mutated"
            self.synthetic_capture(candidate, lambda o: o["result"]["children"][0].update(x=999))
            self.assertFalse(compare_captures(self.reference, candidate)["passed"])
        self.assertEqual(sha256(ROOT / "docs/compatibility.json"), ledger_hash)

    def test_geometry_can_pass_while_coordinates_fail(self):
        observation = copy.deepcopy(self.original)
        observation["result"]["width"] += 10
        self.assertTrue(geometry(self.request, observation, self.policy)["passed"])
        self.assertFalse(compare_observations(self.original, observation)["coordinateTolerance"]["passed"])

    def test_tampered_observation_hash_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "capture"
            shutil.copytree(self.reference, target)
            (target / self.case["observations"][0]).write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                verify_capture(target)

    def test_case_denominator_cannot_be_shrunk(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "capture"
            shutil.copytree(self.reference, target)
            index = load(target / "index.json")
            index["cases"].pop()
            (target / "index.json").write_text(json.dumps(index), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "denominator"):
                verify_capture(target)

    def test_request_seed_swap_rejected_even_after_rehash(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "synthetic"
            self.synthetic_capture(target)
            index = load(target / "index.json")
            case = next(c for c in index["cases"] if c["id"] == self.case["id"])
            request_path = target / case["request"]
            request = load(request_path)
            request["graph"]["layoutOptions"]["elk.randomSeed"] = 99
            request_path.write_text(json.dumps(request), encoding="utf-8")
            case["requestSha256"] = index["files"][case["request"]] = sha256(request_path)
            for name in case["observations"]:
                p = target / name
                observation = load(p)
                observation["requestSha256"] = case["requestSha256"]
                p.write_text(json.dumps(observation), encoding="utf-8")
                index["files"][name] = sha256(p)
            (target / "index.json").write_text(json.dumps(index), encoding="utf-8")
            verify_capture(target)
            with self.assertRaisesRegex(ValueError, "request differs"):
                compare_captures(self.reference, target)

    def test_missing_adapter_process_is_incomplete_not_layout_error(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write(target / "command.json", [str(target / "missing-python")])
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_layout.py"), "candidate", "--command-json",
                                     str(target / "command.json"), "--out", str(target / "capture")], capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            index = load(target / "capture/index.json")
            self.assertEqual(index["status"], "INCOMPLETE")
            self.assertEqual(index["cases"][0]["observations"], [])

    def test_raw_metadata_cli_retains_all_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write(target / "expected.json", [{"id": "option", "defaultValue": 1}])
            write(target / "actual.json", [{"id": "option", "defaultValue": 1 + 1e-10}])
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_layout.py"), "json", "--expected",
                                     str(target / "expected.json"), "--actual", str(target / "actual.json"), "--out", str(target / "diff.json")], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(load(target / "diff.json")["coordinateTolerance"]["passed"])

    def test_cli_mismatch_and_harness_error_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            bad = copy.deepcopy(self.original)
            bad["result"]["children"][0]["x"] += 10
            write(target / "bad.json", bad)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_layout.py"), "pair", "--expected",
                                     str(self.reference / self.case["observations"][0]), "--actual", str(target / "bad.json"),
                                     "--out", str(target / "diff.json")], capture_output=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(load(target / "diff.json")["coordinateTolerance"]["differences"])
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_layout.py"), "verify", str(target / "absent")], capture_output=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
