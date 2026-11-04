"""Independent synthetic profile controls derived from preserved official fixtures.

These tests exercise comparison tooling only. No Python layout algorithm runs.
Every candidate below is explicitly synthetic; real candidate acceptance is separate.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import compare_observations, load

PROFILE = "native-basic-layered-v1"


def fixture(case_id="layered-chain", *, graph_update=None, original_hash=None, hash_owner="root"):
    directory = ROOT / "references/layout" / case_id
    request = load(directory / "request.json")
    reference = load(directory / "run-01/observation.json")
    if graph_update:
        graph_update(request["graph"])
        # Preserve the factual geometric output and mirror requested business data only.
        for key in ("business",):
            if key in request["graph"]:
                reference["result"][key] = copy.deepcopy(request["graph"][key])
    if original_hash is not None:
        # A one-element list distinguishes a supplied null from no extra user key.
        target = request["graph"] if hash_owner == "root" else request["graph"]["children"][0]
        target["$H"] = original_hash[0]
        result = reference["result"] if hash_owner == "root" else reference["result"]["children"][0]
        if original_hash[0] not in (None, False, 0):
            result["$H"] = original_hash[0]
        # For falsy collisions retain the actual-style overwritten integer.
    if reference["outcome"] == "returned":
        reference["inputAfter"] = copy.deepcopy(reference["result"])
    raw = (json.dumps(request, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    reference["requestSha256"] = hashlib.sha256(raw).hexdigest()
    reference["diagnostics"] = {"fixturePurpose": "synthetic comparator control, not an official capture for the altered request"}
    candidate = copy.deepcopy(reference)
    candidate["engine"] = {"name": "pyelk", "version": "SYNTHETIC-PROFILE-TEST"}
    candidate["inputAfter"] = copy.deepcopy(request["graph"])
    candidate["constructorAfter"] = copy.deepcopy(request["constructor"])
    candidate["argumentsAfter"] = copy.deepcopy(request["layoutArguments"])
    if candidate["outcome"] == "returned":
        for original, result in [(request["graph"], candidate["result"]),
                                 *zip(request["graph"].get("children", []), candidate["result"].get("children", []))]:
            if "$H" not in original:
                result.pop("$H", None)
    return raw, reference, candidate


class IndependentNativeProfileControls(unittest.TestCase):
    def compare(self, raw, reference, candidate):
        return compare_observations(reference, candidate, profile=PROFILE, request=raw)

    def test_native_positive_keeps_all_raw_differences(self):
        raw, reference, candidate = fixture()
        report = self.compare(raw, reference, candidate)
        self.assertTrue(report["passed"])
        self.assertTrue(report["publicContract"]["passed"])
        self.assertTrue(report["inputPreservation"]["preserved"])
        self.assertFalse(report["rawStrict"]["passed"])
        self.assertTrue(report["exact"]["differences"])
        self.assertTrue(any(a["rule"] == "GWT-SHAPE-HASH-01" for a in report["adaptations"]))
        self.assertEqual(report["lifecycleObservations"]["acceptance"], "NOT_ASSESSED")

    def test_strict_remains_default_and_does_not_adapt(self):
        _, reference, candidate = fixture()
        report = compare_observations(reference, candidate)
        self.assertEqual(report["profile"], "strict")
        self.assertFalse(report["passed"])
        self.assertEqual(report["adaptations"], [])

    def test_original_byte_context_is_required_and_path_is_supported(self):
        raw, reference, candidate = fixture()
        for invalid in (None, json.loads(raw), raw.decode("utf-8")):
            with self.subTest(type=type(invalid).__name__), self.assertRaises(ValueError):
                compare_observations(reference, candidate, profile=PROFILE, request=invalid)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "request.json"
            p.write_bytes(raw)
            self.assertTrue(compare_observations(reference, candidate, profile=PROFILE, request=p)["passed"])

    def test_reformatted_or_wrong_fingerprint_bytes_cannot_substitute(self):
        raw, reference, candidate = fixture()
        rewritten = json.dumps(json.loads(raw), separators=(",", ":")).encode()
        with self.assertRaises(ValueError):
            self.compare(rewritten, reference, candidate)
        reference["requestSha256"] = candidate["requestSha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.compare(raw, reference, candidate)

    def test_user_falsy_hash_collision_rejects_candidate_copying_reference_overwrite(self):
        for owner in ("root", "child"):
            for user_value in (0, False, None):
                with self.subTest(owner=owner, user_value=user_value):
                    raw, reference, candidate = fixture(original_hash=[user_value], hash_owner=owner)
                    report = self.compare(raw, reference, candidate)
                    self.assertFalse(report["passed"])
                    self.assertTrue(report["publicContract"]["violations"])
                    self.assertTrue(report["inputPreservation"]["preserved"])

    def test_user_truthy_hash_is_preserved_exactly(self):
        for owner in ("root", "child"):
            for user_value in (777, "user-hash"):
                with self.subTest(owner=owner, user_value=user_value):
                    raw, reference, candidate = fixture(original_hash=[user_value], hash_owner=owner)
                    self.assertTrue(self.compare(raw, reference, candidate)["passed"])

    def test_candidate_cannot_copy_new_reference_hash(self):
        for owner in ("root", "child"):
            raw, reference, candidate = fixture()
            target = candidate["result"] if owner == "root" else candidate["result"]["children"][0]
            original = reference["result"] if owner == "root" else reference["result"]["children"][0]
            target["$H"] = original["$H"]
            self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_reference_added_hash_must_be_finite_integer_not_bool_or_string(self):
        for bad in (True, False, 13.5, "13", None):
            with self.subTest(bad=bad):
                raw, reference, candidate = fixture()
                reference["result"]["$H"] = bad
                reference["inputAfter"] = copy.deepcopy(reference["result"])
                self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_nested_business_hash_and_stack_are_never_projected(self):
        raw, reference, candidate = fixture(graph_update=lambda g: g["business"].update({"$H": False, "error": {"stack": "retain-user-data"}}))
        self.assertTrue(self.compare(raw, reference, candidate)["passed"])
        candidate["result"]["business"]["$H"] = 0
        self.assertFalse(self.compare(raw, reference, candidate)["passed"])
        raw, reference, candidate = fixture(graph_update=lambda g: g["business"].update({"error": {"stack": "retain-user-data"}}))
        candidate["result"]["business"]["error"].pop("stack")
        self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_reference_hash_on_edge_is_not_a_shape_adaptation(self):
        raw, reference, candidate = fixture()
        reference["result"]["edges"][0]["$H"] = 123
        reference["inputAfter"] = copy.deepcopy(reference["result"])
        self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_all_candidate_inputs_are_exact_even_for_tiny_geometry_changes(self):
        for mutate in (
            lambda c: c["inputAfter"]["children"][0].update(width=c["inputAfter"]["children"][0]["width"] + 1e-10),
            lambda c: c["constructorAfter"].update(defaultLayoutOptions={}),
            lambda c: c["argumentsAfter"].update(layoutOptions={}),
        ):
            raw, reference, candidate = fixture()
            mutate(candidate)
            report = self.compare(raw, reference, candidate)
            self.assertFalse(report["passed"])
            self.assertFalse(report["inputPreservation"]["preserved"])

    def test_successful_reference_input_after_must_exactly_equal_result(self):
        raw, reference, candidate = fixture()
        reference["inputAfter"]["children"][0]["x"] += 1e-10
        self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_error_profile_preserves_named_errors_and_known_hash_mutation_only(self):
        raw, reference, candidate = fixture("error-unknown-endpoint")
        self.assertTrue(self.compare(raw, reference, candidate)["passed"])
        for field in ("name", "message"):
            altered = copy.deepcopy(candidate)
            altered["error"][field] += "-changed"
            self.assertFalse(self.compare(raw, reference, altered)["passed"])
        reference["inputAfter"]["unexpectedMutation"] = True
        self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_reference_call_argument_mutation_is_not_adaptable(self):
        for after in ("constructorAfter", "argumentsAfter"):
            raw, reference, candidate = fixture()
            reference[after]["injected"] = True
            self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_coordinate_tolerance_remains_separate_from_raw_exact(self):
        raw, reference, candidate = fixture()
        candidate["result"]["children"][0]["x"] += 1e-7
        report = self.compare(raw, reference, candidate)
        self.assertTrue(report["passed"])
        self.assertFalse(report["publicContract"]["exact"]["passed"])
        candidate["result"]["children"][0]["x"] += 1
        self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_section_ids_and_model_order_remain_strict(self):
        for mutate in (
            lambda c: c["result"]["edges"][0]["sections"][0].update(id="different-section"),
            lambda c: c["result"]["children"].reverse(),
            lambda c: c["result"]["edges"][0]["targets"].__setitem__(0, "different-target"),
        ):
            raw, reference, candidate = fixture()
            mutate(candidate)
            self.assertFalse(self.compare(raw, reference, candidate)["passed"])

    def test_comparison_does_not_mutate_either_observation(self):
        raw, reference, candidate = fixture()
        before = copy.deepcopy((reference, candidate))
        self.compare(raw, reference, candidate)
        self.assertEqual((reference, candidate), before)

    def test_unknown_profile_and_worker_parameters_fail_closed(self):
        raw, reference, candidate = fixture()
        with self.assertRaises(ValueError):
            compare_observations(reference, candidate, profile="invented-profile", request=raw)
        request = json.loads(raw)
        request["constructor"]["workerUrl"] = None
        replacement = (json.dumps(request) + "\n").encode()
        reference["requestSha256"] = candidate["requestSha256"] = hashlib.sha256(replacement).hexdigest()
        reference["constructorAfter"] = copy.deepcopy(request["constructor"])
        candidate["constructorAfter"] = copy.deepcopy(request["constructor"])
        with self.assertRaises(ValueError):
            self.compare(replacement, reference, candidate)

    def test_success_cannot_claim_layered_when_constructor_registration_excludes_it(self):
        for algorithms in ([], ["stress"]):
            with self.subTest(algorithms=algorithms):
                raw, reference, candidate = fixture()
                request = json.loads(raw)
                request["constructor"]["algorithms"] = algorithms
                reference["constructorAfter"] = copy.deepcopy(request["constructor"])
                candidate["constructorAfter"] = copy.deepcopy(request["constructor"])
                replacement = (json.dumps(request) + "\n").encode()
                reference["requestSha256"] = candidate["requestSha256"] = hashlib.sha256(replacement).hexdigest()
                with self.assertRaises(ValueError):
                    self.compare(replacement, reference, candidate)

    def test_child_coordinate_mode_cannot_bypass_flat_profile_scope(self):
        raw, reference, candidate = fixture()
        request = json.loads(raw)
        local = {"elk.json.shapeCoords": "ROOT"}
        request["graph"]["children"][0]["layoutOptions"] = local
        reference["result"]["children"][0]["layoutOptions"] = copy.deepcopy(local)
        reference["inputAfter"] = copy.deepcopy(reference["result"])
        candidate["result"]["children"][0]["layoutOptions"] = copy.deepcopy(local)
        candidate["inputAfter"] = copy.deepcopy(request["graph"])
        replacement = (json.dumps(request) + "\n").encode()
        reference["requestSha256"] = candidate["requestSha256"] = hashlib.sha256(replacement).hexdigest()
        with self.assertRaises(ValueError):
            self.compare(replacement, reference, candidate)

    def test_draft_contract_definition_is_not_an_executable_frozen_profile(self):
        raw, reference, candidate = fixture()
        original_load = load
        def altered_definition(path):
            value = original_load(path)
            if Path(path).name == "native-contract.json":
                value["status"] = "draft"
            return value
        with patch("layout_checks.load", side_effect=altered_definition):
            with self.assertRaises(ValueError):
                self.compare(raw, reference, candidate)


if __name__ == "__main__":
    unittest.main()
