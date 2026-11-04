"""Local approved split/join kernels; manual layers do not claim DAG layout."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import UnsupportedFeatureError
from pyelk.model import Graph
from pyelk.options import resolve_options
from pyelk.algorithms.layered.graph import (
    LEdge, LGraph, LNode, LPort, Layer, Vec2, set_layer, set_port_owner,
    set_source, set_target, set_target_and_insert_at_index,
)
from pyelk.algorithms.layered.long_edges import get_junction_points, join_at
from pyelk.algorithms.layered.processors import long_edge_joiner, long_edge_splitter
from pyelk.algorithms.layered.processors import (
    port_side_processor, port_list_sorter, label_and_node_size_processor,
    innermost_node_margin_calculator,
)
from pyelk.algorithms.layered.import_export import import_graph, export_layout
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.execution import create_context


def layered_graph(count=4):
    origin = Graph.from_json({"id": "root", "children": [
        {"id": "n" + str(i), "width": 10, "height": 10} for i in range(count)]})
    graph = LGraph(origin, resolve_options(), None)
    for node in origin.nodes[1:]:
        layer = Layer(graph)
        graph.layers.append(layer)
        set_layer(LNode(graph, origin=node, size=Vec2(10, 10)), layer)
    return graph


def connect(source, target, **properties):
    a, b = LPort(side="EAST"), LPort(side="WEST")
    set_port_owner(a, source)
    set_port_owner(b, target)
    edge = LEdge(properties=properties)
    set_source(edge, a)
    set_target(edge, b)
    return edge


def fan(count, *, incoming=False, tiny=False):
    graph = layered_graph(count + 1)
    nodes = [layer.nodes[0] for layer in graph.layers]
    graph.layers = [Layer(graph), Layer(graph)]
    for node in nodes:
        set_layer(node, graph.layers[1 if (node is nodes[0]) == incoming else 0])
        node.properties['PORT_CONSTRAINTS'] = 'FREE'
        node.size.y = 1e-14 if tiny and node is nodes[0] else 0 if tiny else 10
    edges = [connect(nodes[i], nodes[0]) if incoming else connect(nodes[0], nodes[i])
             for i in range(1, count + 1)]
    return graph, nodes[0], edges


class E05ProcessorAndTransferTests(unittest.TestCase):
    def test_literal_west_range_reversal_leaves_the_last_port(self):
        for count, expected in [(1, [0]), (2, [0, 1]), (3, [0, 1, 2]),
                                (4, [2, 1, 0, 3]), (7, [5, 4, 3, 2, 1, 0, 6])]:
            graph, target, edges = fan(count, incoming=True)
            port_side_processor(graph)
            port_list_sorter(graph)
            with self.subTest(count=count):
                self.assertEqual([edges.index(p.incoming_edges[0]) for p in target.ports], expected)
                self.assertEqual(target.port_side_indices['WEST'], (0, count))

    def test_iterative_multiport_float_real_margin_and_graph_default_identity(self):
        graph, source, _ = fan(7, tiny=True)
        original = graph.origin.to_json()
        port_side_processor(graph)
        port_list_sorter(graph)
        label_and_node_size_processor(graph)
        step = 10 + (1e-14 - 80) / 8
        position, expected = 0.0, []
        for _ in range(7):
            position += step
            expected.append(position)
        self.assertNotEqual(step, 1e-14 / 8)
        self.assertEqual([p.pos.y for p in source.ports], expected)
        innermost_node_margin_calculator(graph)
        self.assertEqual(source.margin.bottom, 2.4344978758017533e-15)
        self.assertEqual(source.size.y, 1e-14)
        padding, margin = graph.properties['NODE_LABELS_PADDING'], graph.properties['SPACING_PORTS_SURROUNDING']
        self.assertEqual(vars(padding), {'top': 5, 'right': 5, 'bottom': 5, 'left': 5})
        self.assertEqual(vars(margin), {'top': 0, 'right': 0, 'bottom': 0, 'left': 0})
        label_and_node_size_processor(graph)
        self.assertIs(graph.properties['NODE_LABELS_PADDING'], padding)
        self.assertIs(graph.properties['SPACING_PORTS_SURROUNDING'], margin)
        self.assertTrue(all(key not in source.properties for key in ('NODE_SIZE_OPTIONS', 'NODE_SIZE_CONSTRAINTS', 'NODE_LABELS_PLACEMENT', 'PORT_LABELS_PLACEMENT')))
        self.assertEqual(graph.origin.to_json(), original)

    def test_west_context_order_and_normal_filter_preserve_dummy_geometry(self):
        graph, target, _ = fan(7, incoming=True, tiny=True)
        port_side_processor(graph)
        port_list_sorter(graph)
        label_and_node_size_processor(graph)
        self.assertEqual([p.id for p in target.ports], list(range(7)))
        step = 10 + (1e-14 - 80) / 8
        self.assertEqual(target.ports[-1].pos.y, step)
        # Source-created long-edge prerequisite; NodeSize's adapter rejects it
        # through the NORMAL predicate, preserving even volatile port IDs.
        dummy = LNode(graph, type='LONG_EDGE', size=Vec2(0, 1), properties={'PORT_CONSTRAINTS': 'FIXED_POS'})
        set_layer(dummy, graph.layers[0])
        for side in ('WEST', 'EAST'):
            port = LPort(id=91, side=side)
            set_port_owner(port, dummy)
        label_and_node_size_processor(graph)
        self.assertEqual((dummy.size.x, dummy.size.y), (0, 1))
        self.assertEqual([(p.id, p.pos.y, p.anchor.y) for p in dummy.ports], [(91, 0, 0), (91, 0, 0)])

    def test_transfer_offsets_bends_junctions_and_original_model_once(self):
        raw = {'id': 'r', 'business': {'error': {'stack': 'keep'}}, 'children': [
            {'id': 'a', 'width': 10, 'height': 10}, {'id': 'b', 'width': 10, 'height': 10}],
            'edges': [{'id': 'e', 'sources': ['a'], 'targets': ['b']}]}
        context = create_context(raw)
        graph = import_graph(context, JavaRandom(context.seed))
        nodes = list(graph.layerless_nodes)
        graph.layerless_nodes.clear()
        for index, node in enumerate(nodes):
            layer = Layer(graph)
            graph.layers.append(layer)
            set_layer(node, layer)
            node.pos.x = index * 40
            for port in node.ports:
                port.pos = Vec2(10 if port.side == 'EAST' else 0, 5)
        edge = next(edge for node in nodes for port in node.ports for edge in port.outgoing_edges)
        edge.bend_points = [Vec2(25, 5)]
        get_junction_points(edge).append(Vec2(25, 5))
        graph.size = Vec2(50, 10)
        graph.offset = Vec2(2, 3)
        result = export_layout(graph)
        self.assertEqual(result['edges'][0]['sections'][0]['bendPoints'], [{'x': 39, 'y': 20}])
        self.assertEqual(result['edges'][0]['junctionPoints'], [{'x': 39, 'y': 20}])
        self.assertEqual(result['edges'][0]['sections'][0]['startPoint'], {'x': 24, 'y': 20})
        self.assertEqual((result['width'], result['height']), (74, 34))
        self.assertEqual(result['business'], raw['business'])
        self.assertEqual(graph.origin.to_json(), raw)
        self.assertNotIn('layoutOptions', result['children'][0])
        broken = import_graph(create_context(raw), JavaRandom(7))
        edge = next(e for n in broken.layerless_nodes for p in n.ports for e in p.outgoing_edges)
        set_source(edge, None)
        with self.assertRaises(UnsupportedFeatureError):
            export_layout(broken)


class LongEdgeKernelTests(unittest.TestCase):
    def test_indexed_target_replaces_destination_position_and_same_port_moves(self):
        old, target = LPort(), LPort()
        before, survivor, dropped, after = [LEdge() for _ in range(4)]
        set_target(survivor, old)
        for edge in (before, dropped, after):
            set_target(edge, target)
        set_target_and_insert_at_index(survivor, target, 1)
        set_target(dropped, None)
        self.assertEqual(old.incoming_edges, [])
        self.assertEqual(target.incoming_edges, [before, survivor, after])
        set_target_and_insert_at_index(survivor, target, 0)
        self.assertEqual(target.incoming_edges, [survivor, before, after])
        set_target_and_insert_at_index(survivor, None, 0)
        self.assertIsNone(survivor.target)
        self.assertEqual(target.incoming_edges, [before, after])

    def test_invalid_index_is_atomic_and_never_treats_boolean_as_integer(self):
        a, b, edge = LPort(), LPort(), LEdge()
        set_target(edge, a)
        for index in (-1, 1, True, 0.5):
            with self.subTest(index=index), self.assertRaises((TypeError, ValueError)):
                set_target_and_insert_at_index(edge, b, index)
            self.assertIs(edge.target, a)
            self.assertEqual(a.incoming_edges, [edge])
            self.assertEqual(b.incoming_edges, [])

    def test_real_per_rank_dummy_chain_and_current_edge_origins(self):
        graph = layered_graph()
        start, end = graph.layers[0].nodes[0], graph.layers[-1].nodes[0]
        shared = {"opaque": []}
        edge = connect(start, end, business=shared, JUNCTION_POINTS=[Vec2(1, 2)])
        original_target = edge.target
        long_edge_splitter(graph)
        dummies = [node for layer in graph.layers for node in layer.nodes if node.type == "LONG_EDGE"]
        self.assertEqual(len(dummies), 2)
        first, second = dummies
        self.assertIs(first.origin, None)
        self.assertIs(first.properties["ORIGIN"], edge)
        self.assertEqual((first.size.x, first.size.y), (0, 1))
        self.assertEqual([(p.side, p.pos.y, p.anchor.y) for p in first.ports], [("WEST", 0, 0), ("EAST", 0, 0)])
        middle = first.ports[1].outgoing_edges[0]
        final = second.ports[1].outgoing_edges[0]
        self.assertIs(second.properties["ORIGIN"], middle)
        self.assertIs(first.properties["LONG_EDGE_SOURCE"], edge.source)
        self.assertIs(first.properties["LONG_EDGE_TARGET"], original_target)
        self.assertIs(second.properties["LONG_EDGE_TARGET"], original_target)
        self.assertNotIn("LONG_EDGE_HAS_LABEL_DUMMIES", first.properties)
        self.assertIs(second.properties["LONG_EDGE_HAS_LABEL_DUMMIES"], False)
        self.assertIs(middle.properties["business"], shared)
        self.assertIsNot(middle.properties, edge.properties)
        self.assertNotIn("JUNCTION_POINTS", middle.properties)
        self.assertNotIn("JUNCTION_POINTS", final.properties)
        self.assertEqual(edge.properties["JUNCTION_POINTS"][0].x, 1)
        for rank, layer in enumerate(graph.layers[:-1]):
            for node in layer.nodes:
                for port in node.ports:
                    for segment in port.outgoing_edges:
                        self.assertIs(segment.target.owner.layer, graph.layers[rank + 1])

    def test_join_restores_original_object_order_and_copies_vectors_in_chain_order(self):
        graph = layered_graph()
        edge = connect(graph.layers[0].nodes[0], graph.layers[-1].nodes[0])
        target = edge.target
        before, after = LEdge(), LEdge()
        set_target(before, target)
        set_target(after, target)
        # Deliberately make the original edge the middle item at the final port.
        set_target_and_insert_at_index(edge, target, 1)
        long_edge_splitter(graph)
        dummies = [n for layer in graph.layers for n in layer.nodes if n.type == "LONG_EDGE"]
        middle = dummies[0].ports[1].outgoing_edges[0]
        final = dummies[1].ports[1].outgoing_edges[0]
        # Splitting itself removes/appends each generated segment. The join
        # must preserve the dropped segment's current slot, not invent a saved
        # pre-split destination order. Place that final segment between peers.
        set_target_and_insert_at_index(final, target, 1)
        self.assertEqual(target.incoming_edges, [before, final, after])
        edge.bend_points.append(Vec2(1, 1))
        middle.bend_points.append(Vec2(2, 2))
        final.bend_points.append(Vec2(3, 3))
        get_junction_points(middle).append(Vec2(20, 21))
        get_junction_points(final).append(Vec2(30, 31))
        long_edge_joiner(graph)
        self.assertEqual(target.incoming_edges, [before, edge, after])
        self.assertEqual([(p.x, p.y) for p in edge.bend_points], [(1, 1), (2, 2), (3, 3)])
        self.assertEqual([(p.x, p.y) for p in edge.properties["JUNCTION_POINTS"]], [(20, 21), (30, 31)])
        self.assertIsNot(edge.bend_points[1], middle.bend_points[0])
        self.assertIsNot(edge.properties["JUNCTION_POINTS"][0], middle.properties["JUNCTION_POINTS"][0])
        self.assertTrue(all(n.type == "NORMAL" for layer in graph.layers for n in layer.nodes))
        self.assertTrue(all(n.layer is not None for n in dummies))
        self.assertIsNone(middle.source)
        self.assertIsNone(middle.target)
        self.assertIsNone(final.source)
        self.assertIsNone(final.target)

    def test_junction_getter_materializes_independent_empty_chains_and_join_reads_both(self):
        a, b = LEdge(), LEdge()
        self.assertNotIn("JUNCTION_POINTS", a.properties)
        first, second = get_junction_points(a), get_junction_points(b)
        self.assertIsNot(first, second)
        self.assertIs(first, get_junction_points(a))
        self.assertEqual((first, second), ([], []))
        graph = layered_graph(3)
        original = connect(graph.layers[0].nodes[0], graph.layers[-1].nodes[0])
        long_edge_splitter(graph)
        dummy = next(n for n in graph.layers[1].nodes if n.type == "LONG_EDGE")
        dropped = dummy.ports[1].outgoing_edges[0]
        self.assertNotIn("JUNCTION_POINTS", original.properties)
        self.assertNotIn("JUNCTION_POINTS", dropped.properties)
        join_at(dummy)
        self.assertEqual(original.properties["JUNCTION_POINTS"], [])
        self.assertEqual(dropped.properties["JUNCTION_POINTS"], [])
        self.assertIsNot(original.properties["JUNCTION_POINTS"], dropped.properties["JUNCTION_POINTS"])

    def test_adjacent_short_layers_and_unreviewed_thickness_fail_closed(self):
        graph = layered_graph(2)
        edge = connect(graph.layers[0].nodes[0], graph.layers[1].nodes[0])
        long_edge_splitter(graph)
        long_edge_joiner(graph)
        self.assertEqual(sum(len(layer.nodes) for layer in graph.layers), 2)
        self.assertNotIn("JUNCTION_POINTS", edge.properties)
        graph = layered_graph(3)
        connect(graph.layers[0].nodes[0], graph.layers[-1].nodes[0], EDGE_THICKNESS=0)
        with self.assertRaises(UnsupportedFeatureError):
            long_edge_splitter(graph)


if __name__ == "__main__":
    unittest.main()
