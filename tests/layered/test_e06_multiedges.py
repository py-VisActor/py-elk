"""Real E06 import/pipeline/API multiplicity and identity controls.

No dedicated multiedge runtime algorithm exists with default mergeEdges=false.
Coordinates in the two-edge control come from an independent fixed-worker
request; the long-edge pressure denominator is also source-derived and observed.
"""
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tests/conformance'))
from native_worker_controls import guarded_worker

from pyelk import ELK
from pyelk.execution import create_context
from pyelk.algorithms.layered.import_export import import_graph
from pyelk.algorithms.layered.phases import JavaRandom


def graph_for(links, *, count=2, seed=1):
    nodes = [{"id": "n" + str(i), "width": 40 if i == 0 else 30, "height": 30 if i == 0 else 20}
             for i in range(count)]
    return {"id": "r", "layoutOptions": {"elk.randomSeed": seed}, "children": nodes,
            "edges": [{"id": "e" + str(i), "sources": ["n" + str(a)], "targets": ["n" + str(b)]}
                      for i, (a, b) in enumerate(links)]}


def native(graph):
    before = deepcopy(graph)
    instance = ELK()
    instance._controller._worker_target=guarded_worker
    with patch("subprocess.Popen", side_effect=AssertionError("Native layout cannot launch an engine")):
        result = asyncio.run(instance.layout(graph))
    trace = instance.last_trace
    instance.terminateWorker()
    if graph != before:
        raise AssertionError("The caller's graph was mutated")
    return result, trace


class MultiedgeTests(unittest.TestCase):
    def test_real_import_allocates_distinct_ports_and_edges_for_all28(self):
        data = graph_for([(0, 1)] * 28)
        context = create_context(data)
        before = deepcopy(data)
        work = import_graph(context, JavaRandom(1))
        nodes = work.layerless_nodes
        ports = [port for node in nodes for port in node.ports]
        edges = [edge for port in ports for edge in port.outgoing_edges]
        self.assertEqual(len(ports), 56)
        self.assertEqual(len(set(ports)), 56)
        self.assertEqual(len(edges), 28)
        self.assertEqual(len(set(edges)), 28)
        self.assertEqual([edge.origin.id for edge in edges], ["e" + str(i) for i in range(28)])
        self.assertTrue(all(len(port.incoming_edges) + len(port.outgoing_edges) == 1 for port in ports))
        self.assertTrue(all(port.origin is None and port.size.x == port.size.y == 0 for port in ports))
        self.assertNotIn("HYPEREDGES", work.properties["GRAPH_PROPERTIES"])
        self.assertNotIn("SELF_LOOPS", work.properties["GRAPH_PROPERTIES"])
        self.assertEqual(data, before)

    def test_public_two_parallel_edges_match_actual_reference_sections(self):
        data = graph_for([(0, 1), (0, 1)])
        result, trace = native(data)
        self.assertEqual(len(trace), 19)
        self.assertEqual([row["strategy"] for row in trace if row["processor"] == "LayerSweepCrossingMinimizer"],
                         ["BARYCENTER", "TWO_SIDED_GREEDY_SWITCH"])
        expected = [
            {"id": "e0_s0", "startPoint": {"x": 52, "y": 32},
             "endPoint": {"x": 72, "y": 28.666666666666664},
             "bendPoints": [{"x": 62, "y": 32}, {"x": 62, "y": 28.666666666666664}],
             "incomingShape": "n0", "outgoingShape": "n1"},
            {"id": "e1_s0", "startPoint": {"x": 52, "y": 22}, "endPoint": {"x": 72, "y": 22},
             "incomingShape": "n0", "outgoingShape": "n1"},
        ]
        self.assertEqual([edge["id"] for edge in result["edges"]], ["e0", "e1"])
        self.assertEqual([edge["sections"] for edge in result["edges"]], [[expected[0]], [expected[1]]])

    def test_real_parallel_long_edges_split_to134nodes_then_restore_same_heads(self):
        data = graph_for([(i, i + 1) for i in range(7)] + [(0, 7)] * 21, count=8, seed=17)
        result, trace = native(data)
        first = trace[0]["before"]
        heads = {edge["originId"]: edge["traceId"] for edge in first["edges"]}
        split = next(row["after"] for row in trace if row["processor"] == "LongEdgeSplitter")
        self.assertEqual(len(split["nodes"]), 134)
        self.assertEqual(len(split["edges"]), 154)
        self.assertEqual(sum(len(node["ports"]) for node in split["nodes"]), 308)
        joined = next(row["after"] for row in trace if row["processor"] == "LongEdgeJoiner")
        self.assertEqual(len(joined["nodes"]), 8)
        self.assertEqual(len(joined["edges"]), 28)
        self.assertEqual({edge["originId"]: edge["traceId"] for edge in joined["edges"]}, heads)
        self.assertEqual([edge["id"] for edge in result["edges"]], ["e" + str(i) for i in range(28)])
        for index, edge in enumerate(result["edges"]):
            self.assertEqual(edge["sources"], data["edges"][index]["sources"])
            self.assertEqual(edge["targets"], data["edges"][index]["targets"])
            self.assertEqual(len(edge["sections"]), 1)
            self.assertEqual(edge["sections"][0]["id"], edge["id"] + "_s0")

    def test_mixed_reciprocal_parallel_loop_restores_original_directions_and_business(self):
        data = graph_for([(0, 1), (0, 1), (1, 0), (0, 0)], seed=-17)
        data["business"] = {"$H": False, "error": {"stack": "root-business"}}
        for index, edge in enumerate(data["edges"]):
            edge["business"] = {"ordinal": index, "$H": 0, "false": False}
        result, trace = native(data)
        self.assertEqual(len(trace), 23)
        self.assertEqual(result["business"], data["business"])
        self.assertEqual([edge["id"] for edge in result["edges"]], [edge["id"] for edge in data["edges"]])
        for expected, actual in zip(data["edges"], result["edges"]):
            for key in ("id", "sources", "targets", "business"):
                self.assertEqual(actual[key], expected[key])
            self.assertEqual(len(actual["sections"]), 1)
            section = actual["sections"][0]
            self.assertEqual(section["id"], expected["id"] + "_s0")
            self.assertEqual(section["incomingShape"], expected["sources"][0])
            self.assertEqual(section["outgoingShape"], expected["targets"][0])
        self.assertEqual([row["processor"] for row in trace if row["processor"].startswith("SelfLoop")],
                         ["SelfLoopPreProcessor", "SelfLoopPortRestorer", "SelfLoopRouter", "SelfLoopPostProcessor"])


if __name__ == "__main__":
    unittest.main()
