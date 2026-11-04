"""Explicit source-derived rank premise; synthetic controls certify the checker only."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "tests/validation")]
from layout_checks import geometry, is_default_simple_ring
import test_degenerate_layers as degenerate


class RingGeometryPolicyTests(unittest.TestCase):
    def original(self):
        request, observed, policy = degenerate.DegenerateLayerGeometryTests().synthetic_chain(cyclic=True)
        return request, observed, {**policy, "forwardEdges": False, "rankSeparation": "default-greedy-simple-ring-v1"}

    def test_marker_requires_original_single_ring_and_default_strategy(self):
        request, observed, policy = self.original()
        self.assertTrue(is_default_simple_ring(request))
        self.assertTrue(geometry(request, observed, policy)["passed"])
        old = {k: v for k, v in policy.items() if k != "rankSeparation"}
        self.assertIn("same_layer_spacing", {e["code"] for e in geometry(request, observed, old)["errors"]})
        for mutate in (lambda d: d["graph"]["edges"].pop(),
                       lambda d: d["graph"]["edges"][0].update(targets=["a"]),
                       lambda d: d["graph"].update(layoutOptions={"elk.layered.cycleBreaking.strategy": "DFS"}),
                       lambda d: d["graph"]["children"][0].update(layoutOptions={"elk.direction": "RIGHT"})):
            value = copy.deepcopy(request)
            mutate(value)
            self.assertFalse(is_default_simple_ring(value))
            self.assertEqual(geometry(value, observed, policy)["errors"][0]["code"], "rank_separation_premise")

    def test_valid_ring_never_waives_overlap_or_original_endpoint_identity(self):
        request, observed, policy = self.original()
        for original, actual in zip(request["graph"]["children"], observed["result"]["children"]):
            original.update(width=10, height=10)
            actual.update(width=10, height=10)
        observed["result"].update(width=20, height=20)
        observed["result"]["edges"][0].update(targets=["c"])
        codes = {e["code"] for e in geometry(request, observed, policy)["errors"]}
        self.assertIn("node_overlap", codes)
        self.assertIn("original_endpoint_identity", codes)

    def test_two_disjoint_rings_cannot_claim_one_rank_chain(self):
        request, observed, policy = self.original()
        request["graph"]["children"] += [{"id": name, "width": 0, "height": 0} for name in "def"]
        request["graph"]["edges"] += [{"id": str(i + 3), "sources": [s], "targets": [t]}
                                      for i, (s, t) in enumerate((("d", "e"), ("e", "f"), ("f", "d")))]
        self.assertFalse(is_default_simple_ring(request))
        self.assertFalse(geometry(request, observed, policy)["passed"])
