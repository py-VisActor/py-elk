"""Original-only E09 rank lemma: real official regression and narrow controls."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import geometry, load
from e07_geometry_premise import premises as old_premises
from e09_geometry_premise import premises
from build_e09_suite import geometry_policy as _base_policy, math_request


def geometry_policy(request):
    return {**_base_policy(request), "rankSeparation": "default-layered-adjacent-edge-v3"}


class E09AdjacentRankGeometryTests(unittest.TestCase):
    def original_regression(self):
        material = load(ROOT / "references/e09-geometry-regression.json")
        values = {}
        for name, entry in material["material"].items():
            raw = base64.b64decode(entry["bytesBase64"], validate=True)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
            values[name] = json.loads(raw) if name not in ("stdout", "stderr") else raw
        self.assertEqual(values["observation"]["requestSha256"], material["material"]["request"]["sha256"])
        self.assertEqual(hashlib.sha256((ROOT / material["caseRequest"]).read_bytes()).hexdigest(),
                         material["material"]["request"]["sha256"])
        self.assertEqual(values["command"]["exitCode"], 0)
        self.assertIs(values["command"]["timedOut"], False)
        for name in ("stdout", "stderr"):
            self.assertEqual(hashlib.sha256(values[name]).hexdigest(), values["command"][name + "Sha256"])
        lock = load(ROOT / "UPSTREAM.json")
        engine = values["observation"]["engine"]
        self.assertEqual(engine["version"], lock["javascript"]["version"])
        self.assertEqual(engine["entrypointSha256"], lock["distribution"]["sha256Files"][engine["entrypoint"]])
        return math_request(values["request"]), values["observation"]

    def test_original_official_near_rank_regression_keeps_old_failure_and_new_positive(self):
        request, observation = self.original_regression()
        original = copy.deepcopy((request, observation))
        policy = geometry_policy(request)
        old = dict(policy, rankSeparation="default-layered-components-v2")
        self.assertIn("same_layer_spacing", {e["code"] for e in geometry(request, observation, old)["errors"]})
        self.assertNotIn(frozenset(("n6", "n0")), old_premises(request)["distinctRanks"])
        self.assertIn(frozenset(("n6", "n0")), premises(request)["distinctRanks"])
        self.assertTrue(geometry(request, observation, policy)["passed"])
        self.assertEqual((request, observation), original)

    def mixed_cycle(self):
        graph = {"id": "root", "layoutOptions": {"elk.direction": "RIGHT", "elk.padding": "[top=0,left=0,bottom=0,right=0]",
                  "elk.spacing.nodeNode": 20, "elk.layered.spacing.nodeNodeBetweenLayers": 0},
                 "children": [{"id": name, "width": 10, "height": 10} for name in "abcd"],
                 "edges": [{"id": str(index), "sources": [a], "targets": [b]}
                           for index, (a, b) in enumerate((("a", "b"), ("b", "c"), ("c", "d"), ("d", "a"), ("a", "a")))]}
        return {"schema": "py-elk-layout-request/v1", "graph": graph, "constructor": {}, "layoutArguments": {}}

    def test_only_original_nonself_adjacency_is_added_in_a_mixed_scc(self):
        request = self.mixed_cycle()
        self.assertEqual(old_premises(request)["distinctRanks"], set())
        actual = premises(request)["distinctRanks"]
        self.assertEqual(actual, {frozenset(pair) for pair in (("a", "b"), ("b", "c"), ("c", "d"), ("d", "a"))})
        self.assertNotIn(frozenset(("a", "a")), actual)
        self.assertNotIn(frozenset(("a", "c")), actual)

    def test_unrelated_true_same_layer_spacing_still_fails(self):
        request = self.mixed_cycle()
        result = copy.deepcopy(request["graph"])
        result.update(x=0, y=0, width=300, height=200)
        for node, (x, y) in zip(result["children"], ((0, 0), (100, 50), (0, 15), (200, 100))):
            node.update(x=x, y=y)
        observed = {"outcome": "returned", "result": result}
        self.assertIn("same_layer_spacing", {e["code"] for e in geometry(request, observed, geometry_policy(request))["errors"]})

    def test_candidate_added_edges_cannot_supply_original_rank_evidence(self):
        request = self.mixed_cycle()
        original = copy.deepcopy(request)
        result = copy.deepcopy(request["graph"])
        result["edges"].append({"id": "fake-ac", "sources": ["a"], "targets": ["c"]})
        result.update(x=0, y=0, width=300, height=200)
        for node, (x, y) in zip(result["children"], ((0, 0), (100, 50), (0, 15), (200, 100))):
            node.update(x=x, y=y)
        errors = {e["code"] for e in geometry(request, {"outcome": "returned", "result": result}, geometry_policy(request))["errors"]}
        self.assertIn("model_identity_or_order", errors)
        self.assertIn("same_layer_spacing", errors)
        self.assertNotIn(frozenset(("a", "c")), premises(request)["distinctRanks"])
        self.assertEqual(request, original)

    def test_nondefault_scope_or_unreviewed_input_never_gets_a_partial_lemma(self):
        for mutate in (lambda r: r["graph"]["layoutOptions"].update({"elk.layered.layering.strategy": "LONGEST_PATH"}),
                       lambda r: r["graph"]["layoutOptions"].update({"elk.randomSeed": 0}),
                       lambda r: r["graph"]["children"][0].update(ports=[{"id": "p"}]),
                       lambda r: r["graph"]["edges"][0].update(targets=["b", "c"])):
            request = self.mixed_cycle()
            mutate(request)
            self.assertIsNone(premises(request))

    def test_geometry_corruption_still_fails_after_rank_false_positive_is_removed(self):
        request, observation = self.original_regression()
        self.assertTrue(geometry(request, observation, geometry_policy(request))["passed"])
        observation["result"]["children"][0]["x"] = -100
        self.assertFalse(geometry(request, observation, geometry_policy(request))["passed"])


if __name__ == "__main__":
    unittest.main()
