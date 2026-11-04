"""E07 component boundaries, with fixed-worker observations as expectations.

The literal row examples come from the original elkjs 0.12.1 worker captures
under test-runs/20261103-E07-01/B. These tests exercise the approved component
operations alone; they do not substitute Python output for full-layout truth.
"""
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import UnsupportedFeatureError
from pyelk.algorithms.layered.components import (
    combine_components, finish_component, resize_graph, split_components,
)
from pyelk.algorithms.layered.graph import (
    Insets, LEdge, LGraph, LNode, LPort, Layer, Vec2, set_layer, set_source, set_target,
)
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.model import Graph
from pyelk.options import resolve_options


def work(sizes=((40, 30), (15, 25), (20, 10), (10, 15)),
         edges=((0, 2), (1, 3)), *, separate=True, spacing=20):
    raw = {"id": "r", "children": [
        {"id": str(i), "width": w, "height": h} for i, (w, h) in enumerate(sizes)],
        "edges": [{"id": f"e{i}", "sources": [str(a)], "targets": [str(b)]}
                  for i, (a, b) in enumerate(edges)]}
    origin = Graph.from_json(raw)
    graph = LGraph(origin, resolve_options(local={
        "elk.separateConnectedComponents": separate,
        "elk.spacing.componentComponent": spacing,
    }), JavaRandom(17), properties={"GRAPH_PROPERTIES": set(), "PROCESSORS": []})
    graph.properties["RANDOM"] = graph.random
    nodes = [LNode(graph, origin.node(str(i)), size=Vec2(*size)) for i, size in enumerate(sizes)]
    graph.layerless_nodes.extend(nodes)
    actual = []
    for i, (a, b) in enumerate(edges):
        p, q = LPort(nodes[a], side="EAST"), LPort(nodes[b], side="WEST")
        nodes[a].ports.append(p)
        nodes[b].ports.append(q)
        edge = LEdge(origin.edge(f"e{i}"))
        set_source(edge, p)
        set_target(edge, q)
        actual.append(edge)
    return graph, nodes, actual


class ComponentBoundaryTests(unittest.TestCase):
    def test_source_interleaved_discovery_order_and_original_identity(self):
        graph, nodes, edges = work()
        source = graph.origin.to_json()
        result = split_components(graph)
        self.assertEqual([c.layerless_nodes for c in result], [[nodes[0], nodes[2]], [nodes[1], nodes[3]]])
        self.assertEqual(graph.layerless_nodes, nodes)
        self.assertTrue(all(n.id == 1 for n in nodes))
        self.assertTrue(all(n.graph is c for c in result for n in c.layerless_nodes))
        self.assertIs(edges[0].source.owner, nodes[0])
        self.assertIs(edges[0].target.owner, nodes[2])
        self.assertEqual(graph.origin.to_json(), source)

    def test_shallow_properties_and_fresh_geometry_and_external_side_set(self):
        graph, nodes, _ = work()
        graph.padding = Insets(7, 13, 11, 5)
        graph.properties["NODE_SIZE_MINIMUM"] = Vec2(123, 456)
        graph.properties["EXT_PORT_CONNECTIONS"] = {"NORTH"}
        result = split_components(graph)
        for component in result:
            self.assertIsNot(component.properties, graph.properties)
            for key in ("RANDOM", "GRAPH_PROPERTIES", "PROCESSORS"):
                self.assertIs(component.properties[key], graph.properties[key])
            self.assertIs(component.random, graph.random)
            self.assertIs(component.options, graph.options)
            self.assertEqual(vars(component.padding), vars(graph.padding))
            self.assertIsNot(component.padding, graph.padding)
            self.assertIsNot(component.offset, graph.offset)
            self.assertIsNot(component.size, graph.size)
            self.assertNotIn("NODE_SIZE_MINIMUM", component.properties)
            self.assertEqual(component.properties["EXT_PORT_CONNECTIONS"], set())
        self.assertIsNot(result[0].properties["EXT_PORT_CONNECTIONS"], result[1].properties["EXT_PORT_CONNECTIONS"])
        self.assertEqual((graph.properties["NODE_SIZE_MINIMUM"].x, graph.properties["NODE_SIZE_MINIMUM"].y), (123, 456))
        self.assertEqual(graph.properties["EXT_PORT_CONNECTIONS"], {"NORTH"})

    def test_false_is_same_unsorted_graph_and_does_not_touch_scratch_ids(self):
        graph, nodes, _ = work(separate=False)
        for i, node in enumerate(nodes):
            node.id = 20 + i
        props = dict(graph.properties)
        self.assertEqual(split_components(graph), [graph])
        self.assertEqual(graph.layerless_nodes, nodes)
        self.assertEqual([n.id for n in nodes], [20, 21, 22, 23])
        self.assertEqual(graph.properties, props)

    def test_selfloop_dfs_terminates_without_duplication(self):
        graph, nodes, edges = work(((15, 25), (40, 30)), ((0, 0),))
        result = split_components(graph)
        self.assertEqual([c.layerless_nodes for c in result], [[nodes[0]], [nodes[1]]])
        self.assertIs(edges[0].source.owner, edges[0].target.owner)

    def test_finish_keeps_literal_layer_order_and_clears_actual_lists(self):
        graph, nodes, _ = work()
        graph.layerless_nodes[:] = [nodes[3]]
        a, b = Layer(graph), Layer(graph)
        graph.layers[:] = [a, b]
        for node in (nodes[2], nodes[0]):
            set_layer(node, a)
        set_layer(nodes[1], b)
        finish_component(graph)
        self.assertEqual(graph.layerless_nodes, [nodes[3], nodes[2], nodes[0], nodes[1]])
        self.assertEqual(graph.layers, [])
        self.assertEqual(a.nodes, [])
        self.assertEqual(b.nodes, [])
        self.assertTrue(all(n.layer is None for n in nodes))

    def test_official_two_post_up_chains_row_geometry(self):
        # Official combine.before/after: local sizes(40,60)/(15,60), area sort
        # puts the second chain first; packing is in restored public axes.
        target, nodes, edges = work()
        target.padding = Insets(7, 13, 11, 5)
        components = split_components(target)
        components[0].size = Vec2(40, 60)
        components[1].size = Vec2(15, 60)
        for node, xy in zip(nodes, ((0, 30), (0, 35), (10, 0), (2.5, 0))):
            node.pos = Vec2(*xy)
        combine_components(components, target)
        self.assertEqual(target.layerless_nodes, [nodes[1], nodes[3], nodes[0], nodes[2]])
        self.assertEqual([(n.pos.x, n.pos.y) for n in nodes], [(35, 30), (0, 35), (45, 0), (2.5, 0)])
        self.assertEqual((target.size.x, target.size.y), (75, 60))
        self.assertTrue(all(n.graph is target for n in nodes))
        self.assertTrue(all("JUNCTION_POINTS" in e.properties for e in edges))
        resize_graph(target)
        self.assertEqual((target.size.x, target.size.y), (75, 60))

    def test_official_eight_unequal_isolates_stable_area_tie_and_rows(self):
        sizes = ((10, 5), (3, 10), (20, 3), (4, 7), (5, 6), (8, 2), (0, 8), (12, 9))
        target, nodes, _ = work(sizes, (), spacing=3.5)
        components = split_components(target)
        for graph in components:
            graph.size = Vec2(graph.layerless_nodes[0].size.x, graph.layerless_nodes[0].size.y)
        combine_components(components, target)
        self.assertEqual([n.origin.id for n in target.layerless_nodes], ["6", "5", "3", "1", "4", "0", "2", "7"])
        self.assertEqual([(n.pos.x, n.pos.y) for n in nodes],
                         [(8.5, 13.5), (22.5, 0), (0, 23), (15, 0), (0, 13.5), (3.5, 0), (0, 0), (0, 29.5)])
        self.assertEqual((target.size.x, target.size.y), (25.5, 38.5))

    def test_all_zero_rectangles_with_zero_spacing_remain_stable(self):
        target, nodes, _ = work(((0, 0),) * 8, (), spacing=0)
        components = split_components(target)
        combine_components(components, target)
        self.assertEqual(target.layerless_nodes, nodes)
        self.assertEqual((target.size.x, target.size.y), (0, 0))
        self.assertTrue(all((n.pos.x, n.pos.y) == (0, 0) for n in nodes))

    def test_rows_translate_existing_bend_and_junction_objects_once(self):
        target, nodes, edges = work()
        components = split_components(target)
        components[0].size, components[1].size = Vec2(80, 40), Vec2(45, 25)
        bend, junction = Vec2(10, 3), Vec2(20, 8)
        edges[0].bend_points[:] = [bend]
        edges[0].properties["JUNCTION_POINTS"] = [junction]
        combine_components(components, target)
        self.assertIs(edges[0].bend_points[0], bend)
        self.assertIs(edges[0].properties["JUNCTION_POINTS"][0], junction)
        self.assertEqual((bend.x, bend.y, junction.x, junction.y), (10, 48, 20, 53))
        self.assertEqual((target.size.x, target.size.y), (80, 85))

    def test_single_distinct_graph_moves_offset_but_same_target_is_early_return(self):
        target, nodes, edges = work(((40, 30), (20, 10)), ((0, 1),))
        component = split_components(target)[0]
        component.offset = Vec2(3.5, 7.25)
        component.size = Vec2(80, 30)
        bend = Vec2(5, 6)
        edges[0].bend_points[:] = [bend]
        combine_components([component], target)
        self.assertEqual([(n.pos.x, n.pos.y) for n in nodes], [(3.5, 7.25), (3.5, 7.25)])
        self.assertEqual((bend.x, bend.y), (8.5, 13.25))
        self.assertEqual((target.size.x, target.size.y), (80, 30))
        target.offset = Vec2(100, 200)
        before = [(n.pos.x, n.pos.y) for n in nodes]
        combine_components([target], target)
        self.assertEqual([(n.pos.x, n.pos.y) for n in nodes], before)

    def test_distinct_singleton_real_add_zero_changes_signed_zero(self):
        target, nodes, _ = work(((1, 1),), ())
        component = split_components(target)[0]
        component.size = Vec2(1, 1)
        component.offset = Vec2(-0.0, -0.0)
        nodes[0].pos = Vec2(-0.0, -0.0)
        combine_components([component], target)
        self.assertEqual(math.copysign(1, component.offset.x), 1)
        self.assertEqual(math.copysign(1, nodes[0].pos.x), 1)

    def test_empty_combine_only_clears_nodes_and_size(self):
        target, _, _ = work(((1, 1),), ())
        target.size, target.offset = Vec2(8, 9), Vec2(3, 4)
        combine_components([], target)
        self.assertEqual(target.layerless_nodes, [])
        self.assertEqual((target.size.x, target.size.y), (0, 0))
        self.assertEqual((target.offset.x, target.offset.y), (3, 4))

    def test_resize_preserves_missing_enumset_defaults_and_literal_float_order(self):
        target, _, _ = work(((1, 1),), ())
        target.size, target.offset = Vec2(0.1, 0.2), Vec2(7, 8)
        target.padding = Insets(0.3, 0.4, 0.5, 0.6)
        before = dict(target.properties)
        resize_graph(target)
        self.assertEqual(target.size.x, ((0.1 + 0.6) + 0.4) - 0.6 - 0.4)
        self.assertEqual(target.size.y, ((0.2 + 0.3) + 0.5) - 0.3 - 0.5)
        self.assertEqual(target.properties, before)
        self.assertEqual((target.offset.x, target.offset.y), (7, 8))
        self.assertNotEqual(target.size.x, 0.1)

    def test_component_operations_do_not_draw_or_reset_shared_random(self):
        target, _, _ = work()
        state = (target.random.state48, target.random.primitive_draws)
        components = split_components(target)
        for graph in components:
            graph.size = Vec2(10, 10)
            finish_component(graph)
        combine_components(components, target)
        resize_graph(target)
        self.assertEqual((target.random.state48, target.random.primitive_draws), state)

    def test_invalid_ownership_does_not_reset_ids_or_move_nodes(self):
        target, nodes, _ = work()
        nodes[0].id = 123
        nodes[1].graph = object()
        before = list(target.layerless_nodes)
        with self.assertRaises(UnsupportedFeatureError):
            split_components(target)
        self.assertEqual(nodes[0].id, 123)
        self.assertEqual(target.layerless_nodes, before)

    def test_non_default_sizing_rejects_before_size_offset_or_properties_mutate(self):
        for key, value in (("NODE_SIZE_CONSTRAINTS", {"MINIMUM_SIZE"}),
                           ("NODE_SIZE_OPTIONS", set()),
                           ("CONTENT_ALIGNMENT", {"H_CENTER", "V_TOP"}),
                           ("NODE_SIZE_FIXED_GRAPH_SIZE", True)):
            target, _, _ = work(((1, 1),), ())
            target.properties[key] = value
            target.size, target.offset = Vec2(0.1, 0.2), Vec2(7, 8)
            before = dict(target.properties)
            with self.assertRaises(UnsupportedFeatureError):
                resize_graph(target)
            self.assertEqual((target.size.x, target.size.y, target.offset.x, target.offset.y), (0.1, 0.2, 7, 8))
            self.assertEqual(target.properties, before)

    def test_bad_component_geometry_rejects_before_target_clear_or_sort(self):
        target, nodes, edges = work()
        components = split_components(target)
        components[0].size = Vec2(10, 10)
        components[1].size = Vec2(float("inf"), 10)
        before = list(components)
        with self.assertRaises(UnsupportedFeatureError):
            combine_components(components, target)
        self.assertEqual(target.layerless_nodes, nodes)
        self.assertEqual(components, before)
        self.assertTrue(all("JUNCTION_POINTS" not in e.properties for e in edges))

    def test_shared_port_29edges_and_nine_nodes_are_rejected_without_mutation(self):
        for count, endpoints in ((9, ()), (2, ((0, 1),) * 29), (2, ((0, 1),) * 2)):
            target, nodes, edges = work(((1, 1),) * count, endpoints)
            if len(edges) == 2:
                first = edges[0].source
                other = edges[1].source
                set_source(edges[1], first)
                nodes[0].ports.remove(other)
            before = list(target.layerless_nodes)
            with self.assertRaises(UnsupportedFeatureError):
                split_components(target)
            self.assertEqual(target.layerless_nodes, before)
            self.assertTrue(all(n.id == 0 for n in nodes))


if __name__ == "__main__":
    unittest.main()
