"""Audited omitted seed context never overrides explicit zero/invalid values."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_checks
from layout_checks import determinism, load

POLICY = "elkjs-0.12.1-default-seed-v1"


class DefaultSeedPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / "tests/fixtures/suites/E04/oracle/e04-default-two-positive"
        cls.request = load(directory / "request.json")
        cls.observed = load(directory / "run-01/observation.json")

    def test_legacy_default_remains_explicit_seed_only(self):
        self.assertFalse(determinism([self.observed, self.observed], self.request)["passed"])

    def test_explicit_source_policy_accepts_only_audited_default_and_exact_repeats(self):
        result = determinism([self.observed, copy.deepcopy(self.observed)], self.request, policy=POLICY)
        self.assertTrue(result["passed"])
        self.assertEqual(result["seed"], 1)
        self.assertEqual(result["seedSource"], "fixed-source-default")
        changed = copy.deepcopy(self.observed)
        changed["result"]["children"][0]["x"] += 1e-8
        self.assertFalse(determinism([self.observed, changed], self.request, policy=POLICY)["passed"])

    def test_explicit_zero_false_null_and_invalid_seed_never_fall_back(self):
        for value in (0, False, None, "0", "not-a-seed", 1.5):
            request = copy.deepcopy(self.request)
            request["graph"].setdefault("layoutOptions", {})["elk.randomSeed"] = value
            with self.subTest(seed=value):
                self.assertFalse(determinism([self.observed, self.observed], request, policy=POLICY)["passed"])

    def test_still_requires_two_real_observations(self):
        self.assertFalse(determinism([self.observed], self.request, policy=POLICY)["passed"])

    def test_selected_scope_alias_conflicts_are_not_mistaken_for_seed_evidence(self):
        for values in ({"elk.randomSeed": 7, "randomSeed": 17},
                       {"org.eclipse.elk.randomSeed": 7, "elk.randomSeed": False},
                       {"org.eclipse.elk.randomSeed": 7, "elk.randomSeed": 7}):
            for local in (True, False):
                request = copy.deepcopy(self.request)
                if local:
                    request["graph"]["layoutOptions"] = values
                else:
                    request["layoutArguments"] = {"layoutOptions": values}
                self.assertFalse(determinism([self.observed, self.observed], request, policy=POLICY)["passed"])

    def test_wrong_reference_engine_cannot_borrow_the_default(self):
        changed = copy.deepcopy(self.observed)
        changed["engine"]["entrypointSha256"] = "0" * 64
        with self.assertRaises(ValueError):
            determinism([changed, changed], self.request, policy=POLICY)

    def test_default_policy_cannot_be_forged_to_seed_seven_or_stale_source(self):
        original_load = layout_checks.load
        for mutate in (lambda d: d.update(defaultSeed=7), lambda d: d["sourceEvidence"].update(sha256="0" * 64)):
            def changed_load(path):
                document = original_load(path)
                if path.name == "e04-determinism-policy.json":
                    mutate(document)
                return document
            with patch.object(layout_checks, "load", side_effect=changed_load), self.assertRaises(ValueError):
                determinism([self.observed, self.observed], self.request, policy=POLICY)

    def test_unselected_constructor_seed_does_not_leak_through_empty_call_options(self):
        request = copy.deepcopy(self.request)
        request["constructor"] = {"defaultLayoutOptions": {"elk.randomSeed": 0}}
        request["layoutArguments"] = {"layoutOptions": {}}
        result = determinism([self.observed, self.observed], request, policy=POLICY)
        self.assertTrue(result["passed"])
        self.assertEqual(result["seedSource"], "fixed-source-default")


if __name__ == "__main__":
    unittest.main()
