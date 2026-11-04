"""Actual routing kernel versus independent source-stage and numeric observations.

The stage adapter restores genuine JS predecessor data only in this test. It
does not accept an end-to-end candidate and is never imported by runtime code.
"""
import base64
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import UnsupportedFeatureError
from pyelk.model import Graph
from pyelk.options import resolve_options
from pyelk.algorithms.layered.graph import (
    Insets, LEdge, LGraph, LNode, LPort, Layer, Vec2, set_layer, set_port_owner, set_source, set_target,
)
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.algorithms.layered.routing import _compare_double, _minimum_difference, _sorted_distinct, orthogonal_edge_router

OBSERVATIONS = ROOT / "references/e05-routing-phase-observations.json"


class RecordingRandom(JavaRandom):
    def __init__(self, seed):
        self.widths = []
        super().__init__(seed)

    def next(self, bits):
        self.widths.append(bits)
        return super().next(bits)


def vector(value):
    return Vec2(value["x"], value["y"])


def edge_rows(state):
    result = {}
    for node in state["nodes"]:
        for port in node["ports"]:
            for edge in [*port["incoming"], *port["outgoing"]]:
                if edge["identity"] in result:
                    assert result[edge["identity"]] == edge
                result[edge["identity"]] = edge
    return result


def restore_stage(case):
    request = json.loads(base64.b64decode(case["requestBytesBase64"]))
    original = Graph.from_json(request["graph"])
    options = resolve_options(constructor=request["constructor"], layout_arguments=request["layoutArguments"],
                              local=request["graph"].get("layoutOptions"))
    state = case["before"]
    random_state = (state["random"]["seedhi"] << 24) | state["random"]["seedlo"]
    random = RecordingRandom(random_state ^ 0x5DEECE66D)
    graph = LGraph(original, options, random)
    graph.size, graph.offset, graph.padding = vector(state["size"]), vector(state["offset"]), Insets(**state["padding"])
    nodes, ports = {}, {}
    for row in state["nodes"]:
        origin_id = row["facts"]["originIdentifier"]
        origin = original.node(origin_id) if row["type"] == "NORMAL" else None
        node = LNode(graph, origin=origin, id=row["id"], type=row["type"], pos=vector(row["position"]),
                     size=vector(row["size"]), margin=Insets(**row["margin"]), padding=Insets(**row["padding"]),
                     properties=copy.deepcopy(row["properties"]))
        nodes[row["identity"]] = node
        for port_row in row["ports"]:
            port = LPort(side=port_row["side"], pos=vector(port_row["position"]), size=vector(port_row["size"]),
                         anchor=vector(port_row["anchor"]), properties=copy.deepcopy(port_row["properties"]))
            set_port_owner(port, node)
            ports[port_row["identity"]] = port
    for index, row in enumerate(state["layers"]):
        layer = Layer(graph, size=vector(row["size"]), id=index)
        graph.layers.append(layer)
        for identity in row["nodes"]:
            set_layer(nodes[identity], layer)
    edges = {}
    for identity, row in edge_rows(state).items():
        edge = LEdge(properties=copy.deepcopy(row["properties"]), bend_points=[vector(point) for point in row["bendPoints"]])
        set_source(edge, ports[row["source"]])
        set_target(edge, ports[row["target"]])
        edges[identity] = edge
    return graph, nodes, ports, edges


class SourceRoutingTests(unittest.TestCase):
    def test_actual_generated_rare_splitter_area_helpers(self):
        from pyelk.algorithms.layered import routing as routing
        document = json.loads((ROOT / "references/e05-routing-helper-observations.json").read_bytes())
        self.assertEqual(document["workerSha256"], "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86")
        self.assertEqual(len(document["records"]), 24)
        for row in document["records"]:
            case = row["input"]

            def make(value):
                segment = routing._Segment(incoming=list(value["incoming"]), outgoing=list(value["outgoing"]))
                routing._extent(segment)
                return segment

            segment, causing = make(case["segment"]), make(case["causing"])
            segment.split_by = causing
            for index, raw in enumerate(case["others"]):
                other = make(raw)
                routing._dependency("REGULAR", segment if index % 2 else other,
                                    other if index % 2 else segment, 1)
            areas = [routing._Area(*value) for value in case["areas"]]
            split = routing._Segment(incoming=list(segment.incoming))
            partner = routing._Segment(outgoing=list(segment.outgoing))
            split.split_by, split.split_partner, partner.split_partner = causing, partner, split
            routing._extent(split)
            routing._extent(partner)
            ratings = [routing._rate_area(segment, split, partner, area) for area in areas]
            chosen = routing._choose_area(segment, areas, 0, len(areas) - 1)
            position = routing._split_position(segment, areas, case["threshold"])
            self.assertEqual({"ratings": ratings, "chosen": chosen, "position": position,
                              "remainingAreas": [[area.start, area.end] for area in areas],
                              "extent": [segment.start, segment.end]}, row["result"])

    def test_real_source_receipt_denominators_and_request_bytes(self):
        document = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        self.assertEqual(document["caseCount"], len(document["cases"]))
        self.assertGreaterEqual(document["caseCount"], 37)
        self.assertEqual(len({case["id"] for case in document["cases"]}), len(document["cases"]))
        self.assertIs(document["nativeRuntimeAccepted"], False)
        for case in document["cases"]:
            raw = base64.b64decode(case["requestBytesBase64"], validate=True)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), case["requestSha256"])
            self.assertIs(case["producer"]["unmodifiedPrettyInstrumentedPublicContractsExact"], True)

    def test_all_actual_source_predecessors_produce_exact_routing_effects_and_rng(self):
        document = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        saw_split = False
        for case in document["cases"]:
            with self.subTest(case=case["id"]):
                graph, nodes, ports, edges = restore_stage(case)
                before_layers = [list(layer.nodes) for layer in graph.layers]
                orthogonal_edge_router(graph)
                after = case["after"]
                self.assertEqual((graph.size.x, graph.size.y), (after["size"]["x"], after["size"]["y"]))
                self.assertEqual((graph.random.seedhi, graph.random.seedlo), (after["random"]["seedhi"], after["random"]["seedlo"]))
                self.assertEqual(graph.random.widths, case["rngPrimitiveWidths"])
                self.assertEqual([layer.nodes for layer in graph.layers], before_layers)
                for row in after["nodes"]:
                    node = nodes[row["identity"]]
                    self.assertEqual((node.pos.x, node.pos.y), (row["position"]["x"], row["position"]["y"]))
                for identity, row in edge_rows(after).items():
                    edge = edges[identity]
                    self.assertEqual([(p.x, p.y) for p in edge.bend_points], [(p["x"], p["y"]) for p in row["bendPoints"]])
                    self.assertIs(edge.source, ports[row["source"]])
                    self.assertIs(edge.target, ports[row["target"]])
                    saw_split |= len(edge.bend_points) >= 4
                if case["id"] == "e05-crossing-six":
                    self.assertEqual(graph.random.widths, [31])
        self.assertTrue(saw_split, "The actual critical-cycle split case must stay in these receipts")

    def test_generated_number_order_distinct_and_signed_zero_vectors(self):
        document = json.loads((ROOT / "references/e05-routing-numeric-observations.json").read_text(encoding="utf-8"))
        self.assertEqual(document["workerSha256"], "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86")
        self.assertEqual(_compare_double(-0.0, 0.0), document["compareNegativePositiveZero"])
        for row in document["records"]:
            values = [-0.0 if value["negativeZero"] else value["value"] for value in row["input"]]
            actual = [{"value": value, "negativeZero": value == 0 and math.copysign(1, value) < 0}
                      for value in _sorted_distinct(values)]
            self.assertEqual(actual, row["sortedDistinct"])
            self.assertEqual(_minimum_difference(values), row["minimumDifference"]["value"])

    def test_bad_work_graph_is_rejected_before_routing_mutations(self):
        case = next(row for row in json.loads(OBSERVATIONS.read_text())["cases"] if row["id"] == "layered-diamond-right")
        for mutate in (lambda graph: setattr(graph.layers[0].nodes[0].pos, "y", float("inf")),
                       lambda graph: setattr(graph.layers[0].nodes[0].ports[0], "side", "NORTH")):
            graph, nodes, _, edges = restore_stage(case)
            mutate(graph)
            before_x = [node.pos.x for node in nodes.values()]
            with self.assertRaises(UnsupportedFeatureError):
                orthogonal_edge_router(graph)
            self.assertEqual(before_x, [node.pos.x for node in nodes.values()])
            self.assertTrue(all(not edge.bend_points for edge in edges.values()))


if __name__ == "__main__":
    unittest.main()
