"""Literal NORTH arithmetic on actual source predecessor states, no layout data path."""
import copy
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "tests/layered")]
from layout_checks import load
from test_e05_routing import restore_stage
from pyelk.algorithms.layered.processors import label_and_node_size_processor


class E06NodeSizeSourceTests(unittest.TestCase):
    def test_literal_north_negation_retains_double_negative_zero(self):
        # JSON.stringify loses JS -0; this source-derived control is separate
        # from the actual captured numeric-value comparisons below.
        case = load(ROOT / "references/e06-nodesize-phase-observations.json")["cases"][0]
        graph, _, ports, _ = restore_stage({**case, "before": case["calls"][0]["before"]})
        graph.properties["GRAPH_PROPERTIES"] = {"SELF_LOOPS"}
        north = [port for port in ports.values() if port.side == "NORTH"]
        self.assertTrue(north)
        for port in north:
            port.size.y = 0.0
        label_and_node_size_processor(graph)
        self.assertTrue(all(math.copysign(1, port.pos.y) == -1 for port in north))

    def test_actual_three_engine_predecessors_and_no_rng(self):
        document = load(ROOT / "references/e06-nodesize-phase-observations.json")
        self.assertIs(document["nativeRuntimeAccepted"], False)
        self.assertEqual(document["caseCount"], 3)
        saw_tiny = False
        for case in document["cases"]:
            self.assertEqual(len(case["calls"]), 1)
            call = case["calls"][0]
            value = {**case, "before": call["before"]}
            graph, nodes, ports, _ = restore_stage(value)
            graph.properties["GRAPH_PROPERTIES"] = {"SELF_LOOPS"}
            for row in call["before"]["nodes"]:
                node = nodes[row["identity"]]
                node.port_side_indices = {entry["side"]: (entry["first"], entry["last"])
                                          for entry in row["portSideIndices"]}
                node.port_sides_cached = True
                for port in row["ports"]:
                    ports[port["identity"]].id = port["id"]
            caches = {identity: copy.deepcopy(node.port_side_indices) for identity, node in nodes.items()}
            before_rng = graph.random.state48
            label_and_node_size_processor(graph)
            self.assertEqual(graph.random.state48, before_rng)
            self.assertEqual(graph.random.widths, [])
            self.assertEqual(call["rng"], [])
            for row in call["after"]["nodes"]:
                node = nodes[row["identity"]]
                self.assertEqual((node.size.x, node.size.y), (row["size"]["x"], row["size"]["y"]))
                self.assertEqual(node.port_side_indices, caches[row["identity"]])
                for expected in row["ports"]:
                    port = ports[expected["identity"]]
                    self.assertEqual(port.id, expected["id"])
                    self.assertEqual(port.side, expected["side"])
                    for field, actual in (("position", port.pos), ("size", port.size), ("anchor", port.anchor)):
                        for axis in ("x", "y"):
                            number = getattr(actual, axis)
                            self.assertEqual(number, expected[field][axis], (case["id"], field, axis))
                            if number == 0:
                                self.assertEqual(math.copysign(1, number), math.copysign(1, expected[field][axis]))
                    if case["id"] == "tiny-NORTH" and port.side == "NORTH":
                        self.assertNotEqual(port.pos.x, node.size.x / 3)
                        saw_tiny = True
        self.assertTrue(saw_tiny)
