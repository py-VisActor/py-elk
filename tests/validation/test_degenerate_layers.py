"""Real oracle regression plus explicit synthetic geometry-only controls."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import contained, geometry, load


class DegenerateLayerGeometryTests(unittest.TestCase):
    def test_official_zero_spacing_zero_width_chain_has_distinct_layers(self):
        directory = ROOT / "tests/fixtures/suites/E04"
        case = next(c for c in load(directory / "cases.json")["cases"] if c["id"] == "e04-zero-spacing-padding")
        request = load(contained(directory, case["request"]))
        observed = load(directory / "oracle" / case["id"] / "run-01/observation.json")
        self.assertTrue(geometry(request, observed, case["geometry"])["passed"])
        conservative = {**case["geometry"], "forwardEdges": False}
        self.assertIn("same_layer_spacing", {e["code"] for e in geometry(request, observed, conservative)["errors"]})

    def synthetic_chain(self, cyclic=False):
        nodes = [{"id": name, "width": 0, "height": 0} for name in "abc"]
        pairs = [("a", "b"), ("b", "c")] + ([("c", "a")] if cyclic else [])
        edges = [{"id": str(i), "sources": [a], "targets": [b]} for i, (a, b) in enumerate(pairs)]
        original = {"id": "root", "children": nodes, "edges": edges}
        result = copy.deepcopy(original)
        result.update(x=0, y=0, width=0, height=0)
        for node in result["children"]:
            node.update(x=0, y=0)
        for edge in result["edges"]:
            edge["sections"] = [{"id": edge["id"] + "_s0", "startPoint": {"x": 0, "y": 0}, "endPoint": {"x": 0, "y": 0}}]
        policy = {"profile": "basic-flat-orthogonal", "direction": "RIGHT", "padding": dict.fromkeys(("top", "right", "bottom", "left"), 0),
                  "nodeNode": 20, "betweenLayers": 0, "forwardEdges": True}
        return {"graph": original}, {"outcome": "returned", "result": result}, policy

    def test_transitive_input_reachability_proves_different_layers(self):
        request, observed, policy = self.synthetic_chain()
        self.assertTrue(geometry(request, observed, policy)["passed"])

    def test_cyclic_input_cannot_waive_same_axis_spacing(self):
        request, observed, policy = self.synthetic_chain(cyclic=True)
        self.assertIn("same_layer_spacing", {e["code"] for e in geometry(request, observed, policy)["errors"]})

    def test_nonreachable_siblings_still_require_spacing(self):
        directory = ROOT / "references/layout/layered-fork"
        request = load(directory / "request.json")
        observed = load(directory / "run-01/observation.json")
        case = next(c for c in load(ROOT / "tests/fixtures/validation/cases.json")["cases"] if c["id"] == "layered-fork")
        by_id = {n["id"]: n for n in observed["result"]["children"]}
        targets = [e["targets"][0] for e in request["graph"]["edges"]]
        first, second = sorted((by_id[name] for name in targets), key=lambda n: n["y"])
        second["y"] = first["y"] + first["height"] + case["geometry"]["nodeNode"] / 2
        codes = {e["code"] for e in geometry(request, observed, case["geometry"])["errors"]}
        self.assertIn("same_layer_spacing", codes)
        self.assertNotIn("node_overlap", codes)

    def test_candidate_edges_cannot_invent_the_reachability_exemption(self):
        request, observed, policy = self.synthetic_chain()
        request["graph"]["edges"] = []
        self.assertIn("same_layer_spacing", {e["code"] for e in geometry(request, observed, policy)["errors"]})


if __name__ == "__main__":
    unittest.main()
