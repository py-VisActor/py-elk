"""Direction phase regressions from the fixed worker, plus aliasing controls."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import UnsupportedFeatureError
from pyelk.algorithms.layered.directions import (
    direction_preprocessor, direction_postprocessor, resolve_direction,
    from_direction, get_node_labels_padding, get_node_size_minimum,
)
from pyelk.algorithms.layered.graph import (
    Insets, LEdge, LGraph, LNode, LPort, Vec2, Layer,
    set_port_owner, set_source, set_target, set_layer,
)
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.model import Graph
from pyelk.options import resolve_options


def chain(direction):
    model = Graph.from_json({"id": "r", "children": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                             "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]},
                                       {"id": "bc", "sources": ["b"], "targets": ["c"]}]})
    graph = LGraph(model, resolve_options(), JavaRandom(17))
    graph.properties["DIRECTION"] = direction
    graph.padding = Insets(3, 13, 11, 7)
    nodes = [LNode(graph, origin=model.node(name), size=Vec2(*size))
             for name, size in zip(("a", "b", "c"), ((7, 13), (.3, 2.7), (41, 0)))]
    graph.layerless_nodes[:] = nodes
    sides = {"RIGHT": ("EAST", "WEST"), "LEFT": ("WEST", "EAST"),
             "DOWN": ("SOUTH", "NORTH"), "UP": ("NORTH", "SOUTH")}[direction]
    edges = []
    for index in range(2):
        source, target = LPort(side=sides[0]), LPort(side=sides[1])
        set_port_owner(source, nodes[index]); set_port_owner(target, nodes[index + 1])
        edge = LEdge(origin=model.edge(("ab", "bc")[index]))
        set_source(edge, source); set_target(edge, target); edges.append(edge)
    return graph, nodes, edges


def geometry(nodes):
    return [(n.pos.x, n.pos.y, n.size.x, n.size.y,
             [(p.side, p.pos.x, p.pos.y) for p in n.ports]) for n in nodes]


class E07DirectionTests(unittest.TestCase):
    def test_real_preprocessor_asymmetric_chain_vectors(self):
        # Actual three-engine captures: A/direction-probes/*-asymmetric-chain.
        # Inputs/expected values were read from worker before/after frames;
        # 24 complete phase replays are additionally retained in this run.
        vectors = {
            "LEFT": (Insets(3, 7, 11, 13), [
                (34, 0, 7, 13, [("EAST", 7, 0)]),
                (40.7, 0, .3, 2.7, [("WEST", .3, 0), ("EAST", .3, 0)]),
                (0, 0, 41, 0, [("WEST", 41, 0)])]),
            "DOWN": (Insets(7, 11, 13, 3), [
                (0, 0, 13, 7, [("EAST", 0, 0)]),
                (0, 0, 2.7, .3, [("WEST", 0, 0), ("EAST", 0, 0)]),
                (0, 0, 0, 41, [("WEST", 0, 0)])]),
            "UP": (Insets(7, 3, 13, 11), [
                (0, 0, 13, 7, [("EAST", 13, 0)]),
                (10.3, 0, 2.7, .3, [("WEST", 2.7, 0), ("EAST", 2.7, 0)]),
                (13, 0, 0, 41, [("WEST", 0, 0)])]),
        }
        for direction, (padding, expected) in vectors.items():
            with self.subTest(direction=direction):
                graph, nodes, edges = chain(direction)
                originals = [(e.source, e.target) for e in edges]
                state = graph.random.state48
                direction_preprocessor(graph)
                self.assertEqual(geometry(nodes), expected)
                self.assertEqual(vars(graph.padding), vars(padding))
                self.assertEqual(graph.properties["DIRECTION"], direction)
                self.assertEqual([(e.source, e.target) for e in edges], originals)
                self.assertEqual(graph.random.state48, state)

    def test_real_postprocessor_transpose_then_up_mirror(self):
        # Actual UP source POST input, after routing/restoration, not the
        # unprocessed PRE output. Port order is actual post-sort order.
        graph, nodes, edges = chain("UP")
        graph.size = Vec2(55.7, 41); graph.padding = Insets(7, 3, 13, 11)
        graph.properties["EDGE_LABELS_SIDE_SELECTION"] = "SMART_UP"
        for node, pos, size in zip(nodes, ((0, 17), (33, 20.35), (55.7, 0)), ((13, 7), (2.7, .3), (0, 41))):
            node.pos = Vec2(*pos); node.size = Vec2(*size)
        nodes[1].ports.reverse()
        for node in nodes:
            for port in node.ports:
                port.side = "EAST" if port.outgoing_edges else "WEST"
                port.pos = Vec2(node.size.x if port.side == "EAST" else 0, node.size.y / 2)
        direction_postprocessor(graph)
        self.assertEqual(geometry(nodes), [
            (17, 42.7, 7, 13, [("NORTH", 3.5, 0)]),
            (20.35, 20, .3, 2.7, [("NORTH", .15, 0), ("SOUTH", .15, 2.7)]),
            (0, 0, 41, 0, [("SOUTH", 20.5, 0)])])
        self.assertEqual(vars(graph.size), {"x": 41, "y": 55.7})
        self.assertEqual(vars(graph.padding), vars(Insets(3, 13, 11, 7)))
        self.assertEqual(graph.properties["EDGE_LABELS_SIDE_SELECTION"], "SMART_DOWN")

    def test_present_mutable_defaults_remain_shared_except_new_minimum(self):
        graph, nodes, edges = chain("DOWN")
        padding = Insets(1, 2, 3, 4)
        minimum = Vec2(11, 19)
        graph.properties["NODE_LABELS_PADDING"] = padding
        nodes[0].properties["NODE_SIZE_MINIMUM"] = minimum
        junctions = [Vec2(2, 7)]; edges[0].properties["JUNCTION_POINTS"] = junctions
        edges[0].bend_points[:] = [Vec2(3, 13)]
        direction_preprocessor(graph)
        self.assertIs(graph.properties["NODE_LABELS_PADDING"], padding)
        self.assertEqual(vars(padding), vars(Insets(4, 3, 2, 1)))
        self.assertIsNot(nodes[0].properties["NODE_SIZE_MINIMUM"], minimum)
        self.assertEqual(vars(nodes[0].properties["NODE_SIZE_MINIMUM"]), {"x": 19, "y": 11})
        self.assertEqual(vars(minimum), {"x": 11, "y": 19})
        self.assertIs(edges[0].properties["JUNCTION_POINTS"], junctions)
        self.assertEqual(vars(junctions[0]), {"x": 7, "y": 2})
        self.assertEqual(vars(edges[0].bend_points[0]), {"x": 13, "y": 3})

    def test_default_getters_clone_per_holder_and_reuse_present_objects(self):
        graph, nodes, _ = chain("DOWN")
        a, b = get_node_labels_padding(graph), get_node_labels_padding(nodes[0])
        self.assertIsNot(a, b)
        a.top = 19
        self.assertEqual(b.top, 5)
        self.assertIs(get_node_labels_padding(graph), a)
        x, y = get_node_size_minimum(nodes[0]), get_node_size_minimum(nodes[1])
        self.assertIsNot(x, y)
        x.x = 23
        self.assertEqual(y.x, 0)
        self.assertIs(get_node_size_minimum(nodes[0]), x)

    def test_side_cache_and_layer_dimensions_are_not_transformed(self):
        graph, nodes, _ = chain("DOWN")
        graph.layerless_nodes.clear()
        layer = Layer(graph); layer.size = Vec2(101, 203); graph.layers.append(layer)
        for node in nodes:
            set_layer(node, layer)
            node.port_sides_cached = True; node.port_side_indices = {"NORTH": (0, 1)}
            node.margin = Insets(1, 2, 3, 4)
        direction_preprocessor(graph)
        self.assertEqual(vars(layer.size), {"x": 101, "y": 203})
        self.assertEqual(layer.nodes, nodes)
        for node in nodes:
            self.assertTrue(node.port_sides_cached)
            self.assertEqual(node.port_side_indices, {"NORTH": (0, 1)})
            self.assertEqual(vars(node.margin), vars(Insets(1, 2, 3, 4)))

    def test_right_does_not_materialize_direction_defaults(self):
        graph, nodes, edges = chain("RIGHT")
        before = geometry(nodes)
        direction_preprocessor(graph); direction_postprocessor(graph)
        self.assertEqual(geometry(nodes), before)
        self.assertEqual(graph.properties, {"DIRECTION": "RIGHT"})
        self.assertTrue(all("NODE_SIZE_MINIMUM" not in n.properties for n in nodes))
        self.assertTrue(all("JUNCTION_POINTS" not in e.properties for e in edges))

    def test_undefined_resolution_and_literal_port_side_mapping(self):
        self.assertEqual(resolve_direction("UNDEFINED"), "RIGHT")
        self.assertEqual(from_direction("UNDEFINED"), "UNDEFINED")
        self.assertEqual([from_direction(d) for d in ("RIGHT", "LEFT", "DOWN", "UP")],
                         ["EAST", "WEST", "SOUTH", "NORTH"])
        for invalid in ("", "right", "AUTO", None):
            with self.subTest(value=invalid), self.assertRaises(UnsupportedFeatureError):
                resolve_direction(invalid)

    def test_invalid_geometry_and_adjacency_fail_before_mutation(self):
        for invalid in (True, float("nan"), float("inf"), 10 ** 400):
            graph, nodes, _ = chain("UP")
            nodes[1].pos.x = invalid
            before = copy.deepcopy(graph.padding)
            with self.subTest(value=str(invalid)), self.assertRaises(UnsupportedFeatureError):
                direction_preprocessor(graph)
            self.assertEqual(vars(graph.padding), vars(before))
            self.assertNotIn("NODE_LABELS_PADDING", graph.properties)
        graph, nodes, edges = chain("LEFT")
        edges[0].target.incoming_edges.clear()
        before = geometry(nodes)
        with self.assertRaises(UnsupportedFeatureError): direction_preprocessor(graph)
        self.assertEqual(geometry(nodes), before)


if __name__ == "__main__":
    unittest.main()
