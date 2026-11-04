"""Default self-loop kernels; independent fixed-worker stage expectations.

The first two-loop control corresponds to the original request recorded by
trace_e06_graph.cjs (40x30 node, two original loops, seed1). Its source stage
facts are: all original ports hidden, restored order [src1,src0,tgt0,tgt1],
and post-offset local bends [(16,-10),(24,-10)]/[(8,-20),(32,-20)] by node(0,20).
No layout result/case name is consulted by production code.
"""
from copy import deepcopy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Layer, Vec2, set_source, set_target
from pyelk.algorithms.layered.loops import (
    SelfLoopHolder, self_loop_pre_processor, self_loop_port_restorer,
    self_loop_post_processor, self_loop_router, snapshot_holder,
)
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk._errors import UnsupportedFeatureError
from pyelk.model import Graph
from pyelk.options import resolve_options


def work(count=2):
    source = {"id": "r", "children": [{"id": "n", "width": 40, "height": 30}],
              "edges": [{"id": f"l{i}", "sources": ["n"], "targets": ["n"]} for i in range(count)]}
    origin = Graph.from_json(source)
    graph = LGraph(origin, resolve_options(), JavaRandom(1))
    node = LNode(graph, origin.node("n"), size=Vec2(40, 30),
                 properties={"PORT_CONSTRAINTS": "FREE", "ORIGINAL_PORT_CONSTRAINTS": "FREE"})
    graph.layerless_nodes.append(node)
    ports, edges = [], []
    for i in range(count):
        source_port = LPort(node, side="EAST")
        target_port = LPort(node, side="WEST")
        node.ports.extend([source_port, target_port])
        edge = LEdge(origin.edge(f"l{i}"))
        set_source(edge, source_port)
        set_target(edge, target_port)
        ports.extend([source_port, target_port])
        edges.append(edge)
    return graph, node, ports, edges


def layered(graph, node):
    graph.layerless_nodes.clear()
    layer = Layer(graph, [node])
    graph.layers.append(layer)
    node.layer = layer
    node.properties["PORT_CONSTRAINTS"] = "FIXED_SIDE"


class LoopProcessorTests(unittest.TestCase):
    def test_actual_two_loop_hidden_identity_and_bfs_order(self):
        graph, node, ports, edges = work()
        state, model = graph.random.state48, graph.origin.to_json()
        self_loop_pre_processor(graph)
        holder = node.properties["SELF_LOOP_HOLDER"]
        self.assertIsInstance(holder, SelfLoopHolder)
        self.assertEqual(node.ports, [])
        self.assertEqual(list(holder.ports), ports)
        self.assertEqual([[p.port for p in loop.ports] for loop in holder.loops], [ports[:2], ports[2:]])
        self.assertEqual([port.id for port in ports], [1, 1, 1, 1])
        self.assertTrue(holder.are_ports_hidden)
        self.assertEqual(holder.routing_slot_count, [0] * 5)
        for port, wrapper in holder.ports.items():
            self.assertIsNone(port.owner)
            self.assertEqual(port.incoming_edges + port.outgoing_edges, [])
            self.assertTrue(wrapper.had_only_self_loops and wrapper.is_hidden)
        for index, loop in enumerate(holder.loops):
            self.assertIs(loop.edges[0].edge, edges[index])
            self.assertIsNone(edges[index].source)
            self.assertIsNone(edges[index].target)
            self.assertIsNone(loop.labels)
        self.assertEqual(graph.random.state48, state)
        self.assertEqual(graph.random.primitive_draws, 0)
        self.assertEqual(graph.origin.to_json(), model)

    def test_actual_stacked_restore_retains_side_cache_and_anchor(self):
        graph, node, ports, edges = work()
        self_loop_pre_processor(graph)
        layered(graph, node)
        node.port_sides_cached = True
        node.port_side_indices = {side: (0, 0) for side in ("NORTH", "EAST", "SOUTH", "WEST")}
        cached = deepcopy(node.port_side_indices)
        self_loop_port_restorer(graph)
        self.assertEqual(node.ports, [ports[2], ports[0], ports[1], ports[3]])
        self.assertTrue(node.port_sides_cached)
        self.assertEqual(node.port_side_indices, cached)
        self.assertEqual(node.properties["PORT_CONSTRAINTS"], "FIXED_SIDE")
        holder = node.properties["SELF_LOOP_HOLDER"]
        self.assertFalse(holder.are_ports_hidden)
        for port in ports:
            self.assertIs(port.owner, node)
            self.assertEqual(port.side, "NORTH")
            self.assertEqual((port.anchor.x, port.anchor.y), (0, 0))
            self.assertEqual(port.incoming_edges + port.outgoing_edges, [])
        for loop in holder.loops:
            self.assertEqual(loop.self_loop_type, "ONE_SIDE")
            self.assertEqual(loop.ports_by_side, {"NORTH": loop.ports})
        self.assertTrue(all(edge.source is edge.target is None for edge in edges))
        self.assertEqual(graph.random.primitive_draws, 0)

    def test_actual_post_reconnects_original_edges_then_offsets_local_bends(self):
        graph, node, ports, edges = work()
        self_loop_pre_processor(graph)
        layered(graph, node)
        self_loop_port_restorer(graph)
        node.pos = Vec2(0, 20)
        edges[0].bend_points = [Vec2(16, -10), Vec2(24, -10)]
        edges[1].bend_points = [Vec2(8, -20), Vec2(32, -20)]
        bend_identities = [list(edge.bend_points) for edge in edges]
        model = graph.origin.to_json()
        self_loop_post_processor(graph)
        self.assertEqual([[(p.x, p.y) for p in edge.bend_points] for edge in edges],
                         [[(16, 10), (24, 10)], [(8, 0), (32, 0)]])
        for i, edge in enumerate(edges):
            self.assertIs(edge.source, ports[2*i])
            self.assertIs(edge.target, ports[2*i+1])
            self.assertEqual(edge.source.outgoing_edges, [edge])
            self.assertEqual(edge.target.incoming_edges, [edge])
            self.assertIs(edge.origin, graph.origin.edge(f"l{i}"))
            self.assertEqual(edge.bend_points, bend_identities[i])
            self.assertNotIn("JUNCTION_POINTS", edge.properties)
        self.assertEqual(graph.origin.to_json(), model)
        self.assertEqual(graph.random.primitive_draws, 0)

    def test_actual_28_loop_bound_and_stacked_order(self):
        graph, node, ports, _ = work(28)
        self_loop_pre_processor(graph)
        layered(graph, node)
        self_loop_port_restorer(graph)
        self.assertEqual(node.ports, ports[::2][::-1] + ports[1::2])
        self.assertEqual(len(node.ports), 56)

    def test_actual_two_loop_router_slots_margin_bends_and_zero_random_draws(self):
        graph, node, ports, edges = work()
        self_loop_pre_processor(graph)
        layered(graph, node)
        self_loop_port_restorer(graph)
        # Actual prepared NodeSize state from the fixed worker's 40x30/2loop
        # request: restored NORTH port list has x8,16,24,32 and zero y/anchor.
        for port, x in zip(node.ports, (8, 16, 24, 32)):
            port.pos = Vec2(x, 0)
        state = graph.random.state48
        self_loop_router(graph)
        holder = node.properties["SELF_LOOP_HOLDER"]
        self.assertEqual([loop.routing_slot for loop in holder.loops], [[0, 0, 0, 0, 0], [0, 1, 0, 0, 0]])
        self.assertEqual(holder.routing_slot_count, [0, 2, 0, 0, 0])
        self.assertEqual([loop.occupied_sides for loop in holder.loops], [["NORTH"], ["NORTH"]])
        self.assertEqual([port.id for port in node.ports], [0, 1, 2, 3])
        self.assertEqual([[(point.x, point.y) for point in edge.bend_points] for edge in edges],
                         [[(16, -10), (24, -10)], [(8, -20), (32, -20)]])
        self.assertEqual((node.margin.top, node.margin.right, node.margin.bottom, node.margin.left), (20, 0, 0, 0))
        self.assertTrue(all(edge.source is edge.target is None for edge in edges))
        self.assertEqual(graph.random.state48, state)
        self.assertEqual(graph.random.primitive_draws, 0)

    def test_actual_zero_width_28_loops_keeps_two_bends_and_nested_slots(self):
        graph, node, ports, edges = work(28)
        node.size = Vec2(0, 0)
        self_loop_pre_processor(graph)
        layered(graph, node)
        self_loop_port_restorer(graph)
        self_loop_router(graph)
        holder = node.properties["SELF_LOOP_HOLDER"]
        self.assertEqual([loop.routing_slot[1] for loop in holder.loops], list(range(28)))
        self.assertEqual(holder.routing_slot_count, [0, 28, 0, 0, 0])
        self.assertEqual(node.margin.top, 280)
        self.assertTrue(all(len(edge.bend_points) == 2 and edge.bend_points[0].x == edge.bend_points[1].x == 0 for edge in edges))
        self.assertEqual(graph.random.primitive_draws, 0)

    def test_router_invalid_nested_order_rejects_before_ids_positions_or_rng(self):
        graph, node, ports, edges = work()
        self_loop_pre_processor(graph)
        layered(graph, node)
        self_loop_port_restorer(graph)
        node.ports[0], node.ports[1] = node.ports[1], node.ports[0]
        ids = [port.id for port in node.ports]
        before = [(p.pos.x, p.pos.y) for p in ports]
        with self.assertRaises(UnsupportedFeatureError):
            self_loop_router(graph)
        self.assertEqual([port.id for port in node.ports], ids)
        self.assertEqual([(p.pos.x, p.pos.y) for p in ports], before)
        self.assertEqual([edge.bend_points for edge in edges], [[], []])
        self.assertEqual(graph.random.primitive_draws, 0)

    def test_shared_port_and_29_edge_controls_reject_before_mutation(self):
        for excessive in (False, True):
            graph, node, ports, edges = work(29 if excessive else 2)
            if not excessive:
                set_source(edges[1], ports[0])
            original_ports = list(node.ports)
            endpoints = [(edge.source, edge.target) for edge in edges]
            with self.assertRaises(UnsupportedFeatureError):
                self_loop_pre_processor(graph)
            self.assertEqual(node.ports, original_ports)
            self.assertNotIn("SELF_LOOP_HOLDER", node.properties)
            self.assertEqual([(edge.source, edge.target) for edge in edges], endpoints)
            self.assertEqual(graph.random.primitive_draws, 0)

    def test_pure_observer_exposes_hidden_geometry_without_default_writes(self):
        graph, node, ports, edges = work(1)
        self_loop_pre_processor(graph)
        holder = node.properties["SELF_LOOP_HOLDER"]
        from pyelk.algorithms.layered.pipeline import _trace_value
        identities = {}
        before = [(port.owner, dict(port.properties), list(port.incoming_edges), list(port.outgoing_edges)) for port in ports]
        observation = snapshot_holder(holder, lambda value: _trace_value(value, identities))
        self.assertTrue(observation["arePortsHidden"])
        self.assertEqual(observation["ports"][0]["pos"], {"x": 0.0, "y": 0.0})
        self.assertIsNone(observation["ports"][0]["owner"])
        self.assertIsNone(observation["loops"][0]["edges"][0]["edge"]["source"])
        self.assertIn("traceId", observation["ports"][0]["reference"])
        self.assertEqual(before, [(port.owner, dict(port.properties), list(port.incoming_edges), list(port.outgoing_edges)) for port in ports])
        self.assertEqual(graph.random.primitive_draws, 0)


if __name__ == "__main__":
    unittest.main()
