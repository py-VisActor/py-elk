"""Actual disconnected NS driver vectors, independently captured from ELK."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import UnsupportedFeatureError
from pyelk.algorithms.layered.graph import (
    LGraph, LNode, LPort, LEdge, set_port_owner, set_source, set_target,
)
import pyelk.algorithms.layered.layering as ns
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.model import Graph
from pyelk.options import resolve_options


def graph_for(count, pairs, *, separate=False, direction="RIGHT"):
    model = Graph.from_json({"id": "r", "children": [{"id": i} for i in range(count)]})
    graph = LGraph(model, resolve_options(local={"elk.separateConnectedComponents": separate}), JavaRandom(17))
    graph.properties["DIRECTION"] = direction
    nodes = [LNode(graph, origin=model.node(i)) for i in range(count)]
    graph.layerless_nodes[:] = nodes
    edges = []
    for a, b in pairs:
        source, target = LPort(side="EAST"), LPort(side="WEST")
        set_port_owner(source, nodes[a]); set_port_owner(target, nodes[b])
        edge = LEdge(); set_source(edge, source); set_target(edge, target)
        edges.append(edge)
    return graph, nodes, edges


def run_observed(graph):
    events = []
    original = ns._NetworkSimplex.execute

    def execute(solver, limit):
        row = {"component": [n.origin.origin.id for n in solver.nodes],
               "previous": solver.previous_layering_node_counts, "limit": limit,
               "beforeLayers": [[n.origin.id for n in layer.nodes] for layer in graph.layers]}
        original(solver, limit)
        row["ranks"] = [n.layer for n in solver.nodes]
        events.append(row)

    with patch.object(ns._NetworkSimplex, "execute", execute):
        ns.network_simplex_layerer(graph)
    return events


class E07NetworkSimplexTests(unittest.TestCase):
    def test_actual_head_promotion_is_neither_full_sort_nor_plain_discovery(self):
        # Actual sizes-one-two-three-two source capture SHA80c24c529329bdd2...
        # Its exact before/after events are also recorded in A/ns-replay-01.
        graph, nodes, _ = graph_for(8, [(1, 2), (3, 4), (4, 5), (6, 7)])
        events = run_observed(graph)
        self.assertEqual([(e["component"], e["previous"], e["limit"], e["ranks"]) for e in events], [
            ([3, 4, 5], None, 56, [0, 1, 2]),
            ([1, 2], [1, 1, 1], 28, [0, 1]),
            ([0], [2, 2, 1], 28, [0]),
            ([6, 7], [3, 2, 1], 28, [0, 1]),
        ])
        self.assertEqual([[n.origin.id for n in l.nodes] for l in graph.layers], [[3, 1, 0, 6], [4, 2, 7], [5]])
        self.assertEqual([n.id for n in nodes], list(range(8)))
        self.assertEqual(graph.layerless_nodes, [])

    def test_equal_largest_component_keeps_discovery_position(self):
        graph, _, _ = graph_for(8, [(0, 1), (1, 2), (3, 4), (5, 6), (6, 7)], direction="UP")
        events = run_observed(graph)
        self.assertEqual([e["component"] for e in events], [[0, 1, 2], [3, 4], [5, 6, 7]])
        self.assertEqual([e["previous"] for e in events], [None, [1, 1, 1], [2, 2, 1]])
        self.assertEqual([[n.origin.id for n in l.nodes] for l in graph.layers], [[0, 3, 5], [1, 4, 6], [2, 7]])

    def test_actual_parallel_diamond_then_chain_and_isolate(self):
        graph, _, edges = graph_for(8, [(0, 1), (0, 2), (1, 3), (2, 3), (0, 3), (0, 3), (4, 5), (5, 6)], direction="DOWN")
        endpoints = [(e.source, e.target) for e in edges]
        events = run_observed(graph)
        self.assertEqual([(e["component"], e["previous"], e["ranks"]) for e in events], [
            ([0, 1, 3, 2], None, [0, 1, 2, 1]),
            ([4, 5, 6], [1, 2, 1], [0, 1, 2]),
            ([7], [2, 3, 2], [0]),
        ])
        self.assertEqual([[n.origin.id for n in l.nodes] for l in graph.layers], [[0, 4, 7], [1, 2, 5], [3, 6]])
        self.assertEqual([(e.source, e.target) for e in edges], endpoints)

    def test_actual_flexible_longest_component_then_shorter_chain(self):
        graph, _, _ = graph_for(8, [(0, 1), (1, 2), (2, 3), (0, 4), (4, 3), (5, 6), (6, 7)])
        events = run_observed(graph)
        self.assertEqual([(e["component"], e["previous"], e["ranks"]) for e in events], [
            ([0, 1, 2, 3, 4], None, [0, 1, 2, 3, 2]),
            ([5, 6, 7], [1, 1, 2, 1], [0, 1, 2]),
        ])
        self.assertEqual([[n.origin.id for n in l.nodes] for l in graph.layers], [[0, 5], [1, 6], [2, 4, 7], [3]])

    def test_isolates_still_solve_separately_with_actual_cumulative_counts(self):
        graph, _, _ = graph_for(8, [])
        events = run_observed(graph)
        self.assertEqual([e["component"] for e in events], [[0], [1], [2], [3], [4], [5], [6], [7]])
        self.assertEqual([e["previous"] for e in events], [None, [1], [2], [3], [4], [5], [6], [7]])
        self.assertEqual([[n.origin.id for n in l.nodes] for l in graph.layers], [list(range(8))])
        self.assertEqual(len({id(e["previous"]) for e in events[1:]}), 7)

    def test_normalize_adds_previous_counts_only_within_current_rank_interval(self):
        nodes = [ns._NNode(None, i, layer=i + 7) for i in range(3)]
        previous = [4, 3, 2, 1]
        solver = ns._NetworkSimplex(nodes, [], previous)
        self.assertEqual(solver.normalize(), [5, 4, 3])
        self.assertEqual([n.layer for n in nodes], [0, 1, 2])
        self.assertEqual(previous, [4, 3, 2, 1])

    def test_actual_direction_and_rng_and_input_are_preserved(self):
        for direction in ("RIGHT", "LEFT", "DOWN", "UP"):
            with self.subTest(direction=direction):
                graph, _, edges = graph_for(8, [(1, 2), (3, 4), (4, 5), (6, 7)], direction=direction)
                origin = graph.origin.to_json()
                state = (graph.random.state48, graph.random.primitive_draws)
                endpoints = [(e.source, e.target) for e in edges]
                ns.network_simplex_layerer(graph)
                self.assertEqual(graph.properties["DIRECTION"], direction)
                self.assertEqual(graph.origin.to_json(), origin)
                self.assertEqual((graph.random.state48, graph.random.primitive_draws), state)
                self.assertEqual([(e.source, e.target) for e in edges], endpoints)

    def test_default_true_or_nonboolean_false_cannot_bypass_split_caller_guard(self):
        for separate in (True, 0, None, "false"):
            graph, nodes, _ = graph_for(3, [(0, 1)])
            graph.options = replace(graph.options, values={**graph.options.values, "org.eclipse.elk.separateConnectedComponents": separate})
            with self.subTest(separate=separate), self.assertRaises(UnsupportedFeatureError):
                ns.network_simplex_layerer(graph)
            self.assertEqual(graph.layerless_nodes, nodes)
            self.assertEqual(graph.layers, [])
            self.assertTrue(all(n.id == 0 for n in nodes))

    def test_disconnected_permission_retains_actual_dag_and_adjacency_guards(self):
        for pairs in ([(0, 1), (1, 0)], [(0, 1), (1, 2), (2, 0)]):
            graph, nodes, _ = graph_for(4, pairs)
            with self.assertRaises(UnsupportedFeatureError): ns.network_simplex_layerer(graph)
            self.assertEqual(graph.layerless_nodes, nodes)
            self.assertEqual(graph.layers, [])
        graph, nodes, edges = graph_for(3, [(0, 1)])
        edges[0].target.incoming_edges.clear()
        with self.assertRaises(UnsupportedFeatureError): ns.network_simplex_layerer(graph)
        self.assertEqual(graph.layerless_nodes, nodes)


if __name__ == "__main__":
    unittest.main()
