"""Bounded NS kernels; these tests do not claim the whole DAG pipeline."""
from itertools import product
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import UnsupportedFeatureError
from pyelk.model import Graph
from pyelk.options import resolve_options
from pyelk.algorithms.layered.graph import (
    LEdge, LGraph, LNode, LPort, Vec2, set_port_owner, set_source, set_target,
)
from pyelk.algorithms.layered.layering import (
    _NNode, _NEdge, _NetworkSimplex, network_simplex_layerer,
    _component_order, _private_graph,
)
from pyelk.algorithms.layered.phases import JavaRandom


def graph_for(count, edges, order=None):
    raw = {"id": "root", "business": {"keep": [1, 2]}, "children": [
        {"id": index, "width": index + 0.1, "height": index + 0.2}
        for index in range(count)]}
    origin = Graph.from_json(raw)
    graph = LGraph(origin, resolve_options(), JavaRandom(7))
    nodes = [LNode(graph, origin=node, size=Vec2(node.to_json()["width"], node.to_json()["height"]))
             for node in origin.nodes[1:]]
    graph.layerless_nodes = [nodes[index] for index in (range(count) if order is None else order)]
    actual_edges = []
    for source, target in edges:
        a, b = LPort(side="EAST"), LPort(side="WEST")
        set_port_owner(a, nodes[source])
        set_port_owner(b, nodes[target])
        edge = LEdge()
        set_source(edge, a)
        set_target(edge, b)
        actual_edges.append(edge)
    return graph, nodes, actual_edges


def ranks(graph):
    return {node.origin.id: index for index, layer in enumerate(graph.layers) for node in layer.nodes}


class NetworkSimplexKernelTests(unittest.TestCase):
    def test_empty_singleton_path_fork_join_diamond_and_skip(self):
        cases = [
            (0, [], {}), (1, [], {0: 0}),
            (4, [(0, 1), (1, 2), (2, 3), (0, 3)], {0: 0, 1: 1, 2: 2, 3: 3}),
            (3, [(0, 1), (0, 2)], {0: 0, 1: 1, 2: 1}),
            (3, [(0, 2), (1, 2)], {0: 0, 1: 0, 2: 1}),
            (4, [(0, 1), (0, 2), (1, 3), (2, 3)], {0: 0, 1: 1, 2: 1, 3: 2}),
        ]
        for count, edges, expected in cases:
            with self.subTest(count=count, edges=edges):
                graph, _, _ = graph_for(count, edges)
                network_simplex_layerer(graph)
                self.assertEqual(ranks(graph), expected)
                self.assertEqual(graph.layerless_nodes, [])
                self.assertTrue(all(layer.nodes for layer in graph.layers))

    def test_objective_matches_exhaustive_small_graph_search(self):
        # Independently enumerate all feasible normalized ranks, rather than
        # reproducing simplex pivots, to check every connected four-node DAG
        # with its labels already in a topological order.
        possible = [(a, b) for a in range(4) for b in range(a + 1, 4)]
        checked = 0
        for mask in range(1, 1 << len(possible)):
            edges = [edge for index, edge in enumerate(possible) if mask & (1 << index)]
            seen, pending = set(), [0]
            while pending:
                node = pending.pop()
                if node not in seen:
                    seen.add(node)
                    pending.extend(b if a == node else a for a, b in edges if a == node or b == node)
            if len(seen) != 4:
                continue
            best = min(sum(values[b] - values[a] for a, b in edges)
                       for values in product(range(4), repeat=4)
                       if min(values) == 0 and all(values[b] > values[a] for a, b in edges))
            graph, _, _ = graph_for(4, list(reversed(edges)), [2, 0, 3, 1])
            network_simplex_layerer(graph)
            result = ranks(graph)
            self.assertEqual(sum(result[b] - result[a] for a, b in edges), best, (mask, result))
            self.assertTrue(all(result[b] > result[a] for a, b in edges))
            checked += 1
        self.assertEqual(checked, 38)

    def test_private_dfs_order_and_public_identity_input_rng_are_preserved(self):
        graph, nodes, edges = graph_for(4, [(0, 1), (0, 2), (1, 3), (2, 3)], [2, 0, 3, 1])
        before = graph.origin.to_json()
        stream = (graph.random.state48, graph.random.primitive_draws)
        endpoints = [(edge.source, edge.target) for edge in edges]
        network_simplex_layerer(graph)
        # Source component DFS starts at work node2, follows incoming0 then
        # that node's outgoing1, then3; output within each rank follows this DFS.
        self.assertEqual([[node.origin.id for node in layer.nodes] for layer in graph.layers], [[0], [2, 1], [3]])
        self.assertEqual([node.id for node in nodes], [1, 3, 0, 2])
        self.assertEqual(graph.origin.to_json(), before)
        self.assertEqual((graph.random.state48, graph.random.primitive_draws), stream)
        self.assertEqual([(edge.source, edge.target) for edge in edges], endpoints)
        self.assertTrue(all(node.pos.x == node.pos.y == 0 for node in nodes))

    def test_dense_eight_and_source_literal_minimal_span(self):
        graph, _, edges = graph_for(8, [(a, b) for a in range(8) for b in range(a + 1, 8)], list(reversed(range(8))))
        network_simplex_layerer(graph)
        self.assertEqual(ranks(graph), dict(enumerate(range(8))))
        self.assertEqual(sum(edge.target.owner.layer is not edge.source.owner.layer for edge in edges), 28)
        a, b, node, target = [_NNode(None, index) for index in range(4)]
        a.layer, b.layer, node.layer, target.layer = 0, 1, 3, 10
        first, second, outgoing = _NEdge(b, node), _NEdge(a, node), _NEdge(node, target)
        node.connected = [first, second, outgoing]
        # The second incoming edge does not lower min-in and therefore enters
        # the generated ternary's min-out arm. A textbook rewrite returns7.
        self.assertEqual(_NetworkSimplex.minimal_span(node), (2, 3))

    def test_unreviewed_topologies_and_priorities_fail_before_mutation(self):
        # E06 separately approves the worker's literal initialize_4 behavior:
        # every nonself parallel LEdge creates its own unit-weight NEdge, while
        # owner-same loops are skipped. These were E05 domain negatives; they
        # are now explicit kernel positives, without widening validate_e05_slice.
        for count, pairs, expected_ranks, private_count in [
            (2, [(0, 1), (0, 1)], {0: 0, 1: 1}, 2),
            (1, [(0, 0)], {0: 0}, 0),
        ]:
            with self.subTest(e06_source_positive=pairs):
                graph, _, edges = graph_for(count, pairs)
                _, private = _private_graph(_component_order(graph.layerless_nodes))
                self.assertEqual(len(private), private_count)
                self.assertTrue(all(edge.delta == 1 and edge.weight == 1 for edge in private))
                endpoints = [(edge.source, edge.target) for edge in edges]
                network_simplex_layerer(graph)
                self.assertEqual(ranks(graph), expected_ranks)
                self.assertEqual([(edge.source, edge.target) for edge in edges], endpoints)
        bad = [(3, [(0, 1), (1, 2), (2, 0)]), (3, [(0, 1)]),
               (9, [(index, index + 1) for index in range(8)])]
        for count, edges in bad:
            graph, _, _ = graph_for(count, edges)
            before = list(graph.layerless_nodes)
            with self.subTest(count=count, edges=edges), self.assertRaises(UnsupportedFeatureError):
                network_simplex_layerer(graph)
            self.assertEqual(graph.layerless_nodes, before)
            self.assertEqual(graph.layers, [])
        for priority in (True, 1, None):
            graph, _, edges = graph_for(2, [(0, 1)])
            edges[0].properties["PRIORITY_SHORTNESS"] = priority
            with self.subTest(priority=priority), self.assertRaises(UnsupportedFeatureError):
                network_simplex_layerer(graph)
        for thoroughness in (True, 1, None):
            graph, _, _ = graph_for(2, [(0, 1)])
            graph.properties["THOROUGHNESS"] = thoroughness
            with self.subTest(thoroughness=thoroughness), self.assertRaises(UnsupportedFeatureError):
                network_simplex_layerer(graph)


if __name__ == "__main__":
    unittest.main()
