"""Independent invariants for the reviewed import/intermediate/export branches."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk.algorithms.layered.graph import (
    Insets, LEdge, LGraph, LNode, LPort, Layer, Vec2,
    set_layer, set_port_owner, set_source, set_target,
)
from pyelk.model import Graph
from pyelk.options import resolve_options
from pyelk.execution import create_context
from pyelk._errors import UnsupportedFeatureError
from pyelk.algorithms.layered.import_export import import_graph, export_layout
from pyelk.algorithms.layered.processors import INTERMEDIATE_PROCESSORS as P
from pyelk.algorithms.layered.phases import (
    JavaRandom, greedy_cycle_breaker, network_simplex_layerer, layer_sweep,
    bk_node_placer, orthogonal_edge_router,
)


def graph():
    origin = Graph.from_json({"id": "root", "children": [{"id": "a", "width": 0, "height": 0}]})
    return LGraph(origin=origin, options=resolve_options(), random=object())


def request_graph(count=3):
    return {"id": "root", "business": {"$H": False, "error": {"stack": "caller"}},
            "children": [{"id": "n" + str(i), "width": 10, "height": 6} for i in range(count)],
            "edges": [{"id": "e" + str(i), "sources": ["n" + str(i)], "targets": ["n" + str(i+1)]} for i in range(count-1)]}


def imported(raw):
    context = create_context(raw)
    return import_graph(context, JavaRandom(context.seed))


def side_prepared(raw):
    value = imported(raw)
    P["EdgeAndLayerConstraintEdgeReverser"](value)
    greedy_cycle_breaker(value)
    P["LayerConstraintPreprocessor"](value)
    network_simplex_layerer(value)
    P["LayerConstraintPostprocessor"](value)
    P["LongEdgeSplitter"](value)
    P["PortSideProcessor"](value)
    P["PortListSorter"](value)
    return value


def run_reviewed(raw):
    value = side_prepared(raw)
    layer_sweep(value, strategy="BARYCENTER")
    layer_sweep(value, strategy="TWO_SIDED_GREEDY_SWITCH")
    P["InLayerConstraintProcessor"](value)
    P["LabelAndNodeSizeProcessor"](value)
    P["InnermostNodeMarginCalculator"](value)
    bk_node_placer(value)
    P["LayerSizeAndGraphHeightCalculator"](value)
    orthogonal_edge_router(value)
    P["LongEdgeJoiner"](value)
    P["EndLabelSorter"](value)
    P["ReversedEdgeRestorer"](value)
    return value


class LayeredHostGraphTests(unittest.TestCase):
    def test_identity_objects_and_mutable_defaults_are_independent(self):
        first, second = graph(), graph()
        a, b = LNode(first), LNode(first)
        self.assertIsNot(a, b)
        self.assertNotEqual(a, b)
        self.assertNotEqual(Vec2(), Vec2())
        a.pos.x = 3
        a.margin.left = 4
        a.properties["custom"] = []
        first.properties["trace"] = []
        self.assertEqual((b.pos.x, b.margin.left), (0, 0))
        self.assertEqual(b.properties, {})
        self.assertEqual(second.properties, {})
        self.assertEqual(first.origin.to_json()["children"][0]["width"], 0)
        port_a, port_b = LPort(), LPort()
        edge_a, edge_b = LEdge(), LEdge()
        port_a.anchor.y = 5
        edge_a.bend_points.append(Vec2())
        self.assertEqual(port_b.anchor.y, 0)
        self.assertEqual(edge_b.bend_points, [])
        self.assertEqual(Insets().top, 0)
        self.assertEqual(Layer(first).id, 0)

    def test_source_target_reassignment_retains_dual_ordered_adjacency(self):
        p, q, t = LPort(), LPort(), LPort()
        first, second = LEdge(), LEdge()
        set_source(first, p); set_source(second, p)
        set_target(first, t); set_target(second, t)
        self.assertEqual(p.outgoing_edges, [first, second])
        self.assertEqual(t.incoming_edges, [first, second])
        # The generated source removes then appends even for the same endpoint.
        set_source(first, p); set_target(first, t)
        self.assertEqual(p.outgoing_edges, [second, first])
        self.assertEqual(t.incoming_edges, [second, first])
        set_source(first, q)
        self.assertEqual(p.outgoing_edges, [second])
        self.assertEqual(q.outgoing_edges, [first])
        self.assertIs(first.source, q)
        self.assertIs(first.target, t)
        set_source(first, None); set_target(first, None)
        self.assertEqual(q.outgoing_edges, [])
        self.assertEqual(t.incoming_edges, [second])
        self.assertIsNone(first.source)
        self.assertIsNone(first.target)

    def test_port_owner_uses_identity_and_same_owner_moves_to_tail(self):
        g = graph()
        first, second = LNode(g), LNode(g)
        p, q = LPort(), LPort()
        set_port_owner(p, first); set_port_owner(q, first)
        self.assertEqual(first.ports, [p, q])
        set_port_owner(p, first)
        self.assertEqual(first.ports, [q, p])
        set_port_owner(p, second)
        self.assertEqual(first.ports, [q])
        self.assertEqual(second.ports, [p])
        self.assertIs(p.owner, second)
        set_port_owner(p, None)
        self.assertEqual(second.ports, [])
        self.assertIsNone(p.owner)

    def test_layer_membership_order_and_separate_layerless_ownership(self):
        g = graph()
        a, b, c = LNode(g), LNode(g), LNode(g)
        g.layerless_nodes.extend([a, b, c])
        left, right = Layer(g), Layer(g)
        set_layer(a, left); set_layer(b, left)
        set_layer(a, left)
        self.assertEqual(left.nodes, [b, a])
        set_layer(c, left, index=1)
        self.assertEqual(left.nodes, [b, c, a])
        set_layer(c, right)
        self.assertEqual(left.nodes, [b, a])
        self.assertEqual(right.nodes, [c])
        self.assertIs(c.layer, right)
        self.assertIs(c.graph, g)
        set_layer(c, None)
        self.assertEqual(right.nodes, [])
        self.assertIsNone(c.layer)
        # Source callers, not set_layer, own clearing/restoring this list.
        self.assertEqual(g.layerless_nodes, [a, b, c])

    def test_invalid_host_relations_are_rejected_before_mutation(self):
        g = graph(); a = LNode(g); layer = Layer(g)
        set_layer(a, layer)
        for index in (-1, 1, False, 0.5):
            with self.subTest(index=index), self.assertRaises((TypeError, ValueError)):
                set_layer(a, layer, index=index)
            self.assertEqual(layer.nodes, [a])
            self.assertIs(a.layer, layer)
        with self.assertRaises(ValueError):
            set_layer(a, None, index=0)
        p, e = LPort(), LEdge()
        set_source(e, p)
        with self.assertRaises(TypeError):
            set_source(e, a)
        self.assertIs(e.source, p)
        self.assertEqual(p.outgoing_edges, [e])


class ReviewedProcessorTests(unittest.TestCase):
    def test_import_uses_edge_sensitive_ordered_dfs_and_separate_public_order(self):
        raw = request_graph(4)
        nodes, edges = raw["children"], raw["edges"]
        raw["children"] = [nodes[i] for i in (2, 0, 3, 1)]
        raw["edges"] = [edges[i] for i in (1, 2, 0)]
        before = copy.deepcopy(raw)
        value = imported(raw)
        self.assertEqual([n.origin.id for n in value.layerless_nodes], ["n2", "n1", "n0", "n3"])
        self.assertEqual([n.id for n in value.layerless_nodes], [1, 1, 1, 1])
        self.assertTrue(all(n.graph is value for n in value.layerless_nodes))
        self.assertEqual(value.origin.to_json(), before)
        self.assertEqual(raw, before)

    def test_side_sort_cache_and_per_node_volatile_id_writes(self):
        value = side_prepared(request_graph(3))
        middle = value.layers[1].nodes[0]
        self.assertEqual([p.side for p in middle.ports], ["EAST", "WEST"])
        self.assertIs(middle.port_sides_cached, True)
        self.assertEqual(middle.port_side_indices, {"EAST": (0, 1), "WEST": (1, 2)})
        self.assertEqual(middle.properties["PORT_CONSTRAINTS"], "FIXED_SIDE")
        for port in middle.ports:
            port.id = 99
        P["LabelAndNodeSizeProcessor"](value)
        self.assertEqual([p.id for p in middle.ports], [0, 1])
        self.assertEqual([(p.pos.x, p.pos.y) for p in middle.ports], [(10, 3), (0, 3)])
        self.assertEqual([(p.anchor.x, p.anchor.y) for p in middle.ports], [(0, 0), (0, 0)])

    def test_singleton_empty_side_cache_and_zero_dimension_branch(self):
        raw = request_graph(1)
        raw["children"][0].update(width=0, height=0)
        value = side_prepared(raw)
        node = value.layers[0].nodes[0]
        self.assertEqual(node.port_side_indices, {"NORTH": (0, 0)})
        P["LabelAndNodeSizeProcessor"](value)
        self.assertEqual((node.size.x, node.size.y), (0, 0))
        P["InnermostNodeMarginCalculator"](value)
        self.assertEqual((node.margin.top, node.margin.right, node.margin.bottom, node.margin.left), (0, 0, 0, 0))

    def test_zero_height_ports_are_written_and_margins_recomputed(self):
        raw = request_graph(2)
        raw["children"][0]["height"] = 0
        value = side_prepared(raw)
        first = value.layers[0].nodes[0]
        first.ports[0].pos.y = 123
        P["LabelAndNodeSizeProcessor"](value)
        self.assertEqual(first.ports[0].pos.y, 0)
        first.margin = Insets(top=7, right=7, bottom=7, left=7)
        P["InnermostNodeMarginCalculator"](value)
        self.assertEqual((first.margin.top, first.margin.right, first.margin.bottom, first.margin.left), (0, 0, 0, 0))

    def test_changed_cell_and_graph_preconditions_fail_closed(self):
        for key, value in [("NODE_SIZE_CONSTRAINTS", {"MINIMUM_SIZE"}), ("NODE_SIZE_OPTIONS", {"COMPUTE_PADDING"})]:
            work = side_prepared(request_graph(2))
            work.layers[0].nodes[0].properties[key] = value
            with self.subTest(key=key), self.assertRaises(UnsupportedFeatureError):
                P["LabelAndNodeSizeProcessor"](work)
        work = side_prepared(request_graph(2))
        work.properties["GRAPH_PROPERTIES"] = {"EXTERNAL_PORTS"}
        with self.assertRaises(UnsupportedFeatureError):
            P["LabelAndNodeSizeProcessor"](work)

    def test_constraint_dummy_and_end_label_branches_reject(self):
        for key, value, stage in [("LAYER_CONSTRAINT", "FIRST", "LayerConstraintPreprocessor"),
                                  ("IN_LAYER_CONSTRAINT", "TOP", "InLayerConstraintProcessor"),
                                  ("END_LABELS", {}, "EndLabelSorter")]:
            work = side_prepared(request_graph(2))
            work.layers[0].nodes[0].properties[key] = value
            with self.subTest(key=key), self.assertRaises(UnsupportedFeatureError):
                P[stage](work)
        work = side_prepared(request_graph(2))
        edge = work.layers[0].nodes[0].ports[0].outgoing_edges[0]
        source, target = edge.source, edge.target
        edge.properties["REVERSED"] = True
        edge.bend_points = [Vec2(1, 2), Vec2(3, 4)]
        old_points = list(edge.bend_points)
        before_rng = (work.random.state48, work.random.primitive_draws)
        P["ReversedEdgeRestorer"](work)
        self.assertIs(edge.source, target)
        self.assertIs(edge.target, source)
        self.assertIs(edge.properties["REVERSED"], False)
        self.assertEqual([(p.x, p.y) for p in edge.bend_points], [(3, 4), (1, 2)])
        self.assertTrue(all(a is not b for a in edge.bend_points for b in old_points))
        self.assertEqual((work.random.state48, work.random.primitive_draws), before_rng)

    def test_layer_bounds_and_graph_offset_are_real_geometry_writes(self):
        work = side_prepared(request_graph(2))
        work.layers[0].nodes[0].pos.y = 5
        work.layers[1].nodes[0].pos.y = 8
        P["LayerSizeAndGraphHeightCalculator"](work)
        self.assertEqual([(l.size.x, l.size.y) for l in work.layers], [(10, 6), (10, 6)])
        self.assertEqual(work.size.y, 9)
        self.assertEqual(work.offset.y, -5)

    def test_export_preserves_business_model_order_and_exact_section_identity(self):
        raw = request_graph(2)
        raw["children"][1]["width"] = 20
        raw["children"][1]["height"] = 2
        raw["edges"][0]["id"] = "business/edge"
        raw["layoutOptions"] = {"elk.padding": "[top=2,right=3,bottom=5,left=7]",
                                "elk.layered.spacing.nodeNodeBetweenLayers": 19}
        before = copy.deepcopy(raw)
        work = run_reviewed(raw)
        result = export_layout(work)
        self.assertEqual([(n["x"], n["y"]) for n in result["children"]], [(7, 2), (36, 4)])
        self.assertEqual((result["width"], result["height"]), (59, 13))
        self.assertEqual(result["edges"][0]["sections"][0], {"id": "business/edge_s0", "startPoint": {"x": 17, "y": 5},
                         "endPoint": {"x": 36, "y": 5}, "incomingShape": "n0", "outgoingShape": "n1"})
        self.assertEqual(result["edges"][0]["container"], "root")
        self.assertIs(result["business"]["$H"], False)
        self.assertEqual(result["business"]["error"]["stack"], "caller")
        self.assertEqual(raw, before)
        self.assertEqual(work.origin.to_json(), before)
        self.assertFalse(work.layers)
        self.assertTrue(all(n.layer is None for n in work.layerless_nodes))
        self.assertNotIn("$H", result)

    def test_empty_graph_uses_leaf_branch_without_padding_layout(self):
        raw = request_graph(0)
        raw["layoutOptions"] = {"elk.padding": "[top=7,right=8,bottom=9,left=10]"}
        work = imported(raw)
        result = export_layout(work)
        self.assertEqual((result["x"], result["y"], result["width"], result["height"]), (0, 0, 0, 0))
        self.assertEqual(work.random.primitive_draws, 0)
        self.assertEqual(result["children"], [])
        self.assertNotIn("width", raw)


if __name__ == "__main__":
    unittest.main()
