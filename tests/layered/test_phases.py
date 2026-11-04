"""Real phase kernels on explicit source preconditions, not a layout facade.

The small ADT factory supplies the intervening processors' documented inputs;
it does not implement or claim those processors. Complete pipeline acceptance
and installed-candidate conformance are separate root/V checks.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import UnsupportedFeatureError
from pyelk.model import Graph
from pyelk.options import resolve_options
from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Vec2, set_source, set_target, set_port_owner
from pyelk.algorithms.layered.phases import (JavaRandom, greedy_cycle_breaker, network_simplex_layerer,
                                            layer_sweep, bk_node_placer, orthogonal_edge_router)


def make_graph(sizes, *, order=None, edge_order=None, seed=1, local=None, constructor=None, arguments=None):
    order = list(range(len(sizes))) if order is None else order
    edge_order = list(range(max(0, len(sizes) - 1))) if edge_order is None else edge_order
    data = {"id": "r", "business": {"$H": False, "error": {"stack": "keep"}},
            "children": [{"id": "n" + str(i), "width": sizes[i][0], "height": sizes[i][1]} for i in order],
            "edges": [{"id": "e" + str(i), "sources": ["n" + str(i)], "targets": ["n" + str(i+1)]} for i in edge_order]}
    origin = Graph.from_json(data)
    options = resolve_options(constructor=constructor, layout_arguments=arguments, local=local)
    graph = LGraph(origin, options, JavaRandom(seed), properties={"DIRECTION": "RIGHT",
                    "NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES": True, "NODE_PLACEMENT_BK_FIXED_ALIGNMENT": "NONE",
                    "GRAPH_PROPERTIES": set()})
    nodes = {i: LNode(graph, origin.node("n" + str(i)), size=Vec2(*sizes[i]), properties={"PORT_CONSTRAINTS": "FREE"}) for i in order}
    graph.layerless_nodes[:] = [nodes[i] for i in order]
    for i in edge_order:
        edge = LEdge(origin.edge("e" + str(i)))
        source, target = LPort(side="EAST"), LPort(side="WEST")
        set_port_owner(source, nodes[i]); set_port_owner(target, nodes[i+1])
        set_source(edge, source); set_target(edge, target)
    return graph, nodes


def prepare_sides(graph):
    """Explicit preconditions of reviewed A PortSideProcessor/PortListSorter."""
    for layer in graph.layers:
        for node in layer.nodes:
            node.properties["PORT_CONSTRAINTS"] = "FIXED_SIDE"
            node.ports.sort(key=lambda port: {"EAST": 1, "WEST": 3}[port.side])
            node.port_sides_cached = True
            node.port_side_indices = {port.side: (i, i + 1) for i, port in enumerate(node.ports)}


def prepare_centered_ports(graph):
    """Explicit source precondition; not a substitute production processor."""
    for layer in graph.layers:
        for node in layer.nodes:
            for port in node.ports:
                port.pos.x = node.size.x if port.side == "EAST" else 0.0
                port.pos.y = node.size.y / 2


def prepare_layer_bounds(graph):
    for layer in graph.layers:
        node = layer.nodes[0]
        layer.size.x = max(0.0, node.size.x + node.margin.left + node.margin.right)
        top = node.pos.y - node.margin.top
        bottom = node.pos.y + node.size.y + node.margin.bottom
        layer.size.y = bottom - top


def run_ordering(graph):
    greedy_cycle_breaker(graph)
    network_simplex_layerer(graph)
    prepare_sides(graph)
    layer_sweep(graph, strategy="BARYCENTER")
    layer_sweep(graph, strategy="TWO_SIDED_GREEDY_SWITCH")


class GeneratedRandomTests(unittest.TestCase):
    def test_generated_oracle_vectors_include_signed32_long_and_reseed(self):
        # Actual fixed generated worker bridge; B/rng-oracle.json (108 ops).
        vectors = {
            1: [1, 1685660, 27520057, 54685644, 446064254, 155629808, 0, 1, 1, 6, 13136569,
                0.15273620134152177, 2943695534161593524, -412758810, 1, 3290634, -273489099],
            -17: [0, 12483548, 48652605, 49063014, 1689732966, 1012549297, 0, 0, 0, 5, 1229257914,
                  0.7091278778469472, -3425513545471796191, -825310564, 0, 8901335, -1055136188],
            2147483647: [1, 15220386, 56956544, 109870076, 1713237812, -1518519476, 0, 0, 1, 0, 1536490112,
                         0.6621157785100991, 1437350359193338828, 1148718049, 0, 6437757, 828468781],
        }
        for seed, expected in vectors.items():
            with self.subTest(seed=seed):
                random = JavaRandom(seed)
                actual = [random.next(bits) for bits in (1, 24, 26, 27, 31, 32)]
                actual += [random.next_int(bound) for bound in (1, 2, 3, 7, 2147483647)]
                actual += [random.next_double(), random.next_long()]
                random.set_seed(actual[-1])
                actual += [random.next(bits) for bits in (32, 1, 24, 32)]
                self.assertEqual(actual, expected)
                self.assertEqual(random.primitive_draws, 19)  # 6+5+2+2+4; reseed draws0.

    def test_diagnostics_and_reset_do_not_consume_draws_or_change_other_streams(self):
        first, second = JavaRandom(7), JavaRandom(7)
        state = first.state48
        self.assertEqual((first.seedhi << 24) + first.seedlo, state)
        first.next_float()
        self.assertEqual(second.state48, state)
        self.assertEqual(first.primitive_draws, 1)
        first.set_seed(7)
        self.assertEqual(first.state48, state)
        self.assertEqual(first.primitive_draws, 1)
        with self.assertRaises(AttributeError):
            first.state48 = 0

    def test_invalid_random_arguments_fail_without_implicit_coercion(self):
        for seed in (True, 1.0, "1", -(2**63)-1, 2**63):
            with self.subTest(seed=seed), self.assertRaises(ValueError): JavaRandom(seed)
        random = JavaRandom(1)
        for bits in (False, 0, 33, 1.0):
            with self.subTest(bits=bits), self.assertRaises(ValueError): random.next(bits)
        for bound in (False, 0, -1, 2**31, "3"):
            with self.subTest(bound=bound), self.assertRaises(ValueError): random.next_int(bound)
        self.assertEqual(random.primitive_draws, 0)


class PhaseKernelTests(unittest.TestCase):
    def test_greedy_drains_real_degree_queues_without_random_draw_or_reversal(self):
        graph, nodes = make_graph([(7, 3)] * 4, order=[2, 0, 3, 1], edge_order=[2, 0, 1])
        original = graph.origin.to_json()
        before_ports = {node: list(node.ports) for node in graph.layerless_nodes}
        greedy_cycle_breaker(graph)
        self.assertEqual([node.id for node in graph.layerless_nodes], [0, 1, 2, 3])
        self.assertEqual(graph.random.primitive_draws, 0)
        self.assertEqual(graph.origin.to_json(), original)
        for node in graph.layerless_nodes:
            self.assertEqual(node.ports, before_ports[node])
            for port in node.ports:
                for edge in port.outgoing_edges:
                    self.assertIs(edge.source, port)
                    self.assertFalse(edge.properties.get("REVERSED", False))

    def test_network_simplex_unique_tight_path_ranks_follow_edges_not_input_order(self):
        graph, nodes = make_graph([(11, 3), (29, 31), (5, 17), (23, 7)], order=[2, 0, 3, 1], edge_order=[1, 2, 0])
        network_simplex_layerer(graph)
        self.assertEqual(graph.layerless_nodes, [])
        self.assertEqual([layer.nodes for layer in graph.layers], [[nodes[i]] for i in range(4)])
        self.assertTrue(all(nodes[i].layer is graph.layers[i] for i in range(4)))
        self.assertEqual(graph.random.primitive_draws, 0)

    def test_singleton_layer_sweeps_take_the_real_early_return(self):
        graph, nodes = make_graph([(0, 0)])
        network_simplex_layerer(graph); prepare_sides(graph)
        nodes[0].id = 43; graph.layers[0].id = 19
        before = graph.random.state48
        for strategy in ("BARYCENTER", "TWO_SIDED_GREEDY_SWITCH"):
            layer_sweep(graph, strategy=strategy)
        self.assertEqual(graph.random.state48, before)
        self.assertEqual(graph.random.primitive_draws, 0)
        self.assertEqual((nodes[0].id, graph.layers[0].id), (43, 19))
        self.assertEqual(nodes[0].properties["PORT_CONSTRAINTS"], "FIXED_SIDE")

    def test_layer_sweeps_match_actual_generated_state_and_mutable_order_writes(self):
        # States are actual final second-sweep states from V21 PRETTY traces.
        for n, seed, halves in [(2, 1, (12222700, 16415130)), (4, 1, (3477873, 6933220)),
                                (3, 7, (15871827, 5288541)), (3, -17, (2945233, 14100439))]:
            with self.subTest(n=n, seed=seed):
                graph, _ = make_graph([(9, 5)] * n, seed=seed, order=list(reversed(range(n))))
                run_ordering(graph)
                self.assertEqual((graph.random.seedhi, graph.random.seedlo), halves)
                self.assertEqual(graph.random.primitive_draws, n + 8)
                self.assertEqual([layer.id for layer in graph.layers], list(range(n)))
                self.assertEqual([layer.nodes[0].id for layer in graph.layers], [0] * n)
                ports = [port for layer in graph.layers for port in layer.nodes[0].ports]
                self.assertEqual([port.id for port in ports], list(range(2 * (n - 1))))
                self.assertTrue(all(layer.nodes[0].properties["PORT_CONSTRAINTS"] == "FIXED_ORDER" for layer in graph.layers))

    def test_bk_uses_center_port_differences_and_real_candidate_selection(self):
        graph, nodes = make_graph([(11, 3), (29, 31), (5, 17), (23, 7)])
        run_ordering(graph); prepare_centered_ports(graph)
        before = graph.random.state48
        bk_node_placer(graph)
        self.assertEqual([nodes[i].pos.y for i in range(4)], [14, 0, 7, 12])
        self.assertEqual([nodes[i].id for i in range(4)], [0, 1, 2, 3])
        self.assertEqual([nodes[i].pos.x for i in range(4)], [0, 0, 0, 0])
        self.assertEqual(graph.random.state48, before)

    def test_orthogonal_zero_slot_branch_accumulates_real_width_and_layer_gap(self):
        graph, nodes = make_graph([(11, 3), (29, 31), (5, 17), (23, 7)])
        run_ordering(graph); prepare_centered_ports(graph); bk_node_placer(graph); prepare_layer_bounds(graph)
        before = graph.random.state48
        orthogonal_edge_router(graph)
        self.assertEqual([nodes[i].pos.x for i in range(4)], [0, 31, 80, 105])
        self.assertEqual(graph.size.x, 128)
        self.assertEqual(graph.random.state48, before)
        self.assertTrue(all(not edge.bend_points for node in nodes.values() for port in node.ports for edge in port.outgoing_edges))

    def test_zero_sizes_and_zero_spacing_are_distinct_ranks_with_same_x(self):
        graph, nodes = make_graph([(0, 0)] * 3, local={"elk.layered.spacing.nodeNodeBetweenLayers": 0})
        run_ordering(graph); prepare_centered_ports(graph); bk_node_placer(graph); prepare_layer_bounds(graph)
        orthogonal_edge_router(graph)
        self.assertEqual(len(graph.layers), 3)
        self.assertEqual([nodes[i].pos.x for i in range(3)], [0, 0, 0])
        self.assertEqual(graph.size.x, 0)

    def test_routing_accepts_real_binary64_layer_bounds_for_decimal_heights(self):
        # A's independently admitted counterexample: (.45 + .1) - .45 differs
        # from .1. ORTHO reads layer width, not the calculator's layer height.
        variants = [(1.0, .1), (.1, 1.0), (10.0, .1, .3),
                    (1_000_000.0, .1, .2, 999_999.99), (1e-300, 1e-320)]
        rounded_bounds_seen = False
        for heights in variants:
            with self.subTest(heights=heights):
                graph, nodes = make_graph([(10, height) for height in heights])
                run_ordering(graph); prepare_centered_ports(graph); bk_node_placer(graph); prepare_layer_bounds(graph)
                bounds = [layer.size.y for layer in graph.layers]
                rounded_bounds_seen |= any(layer.size.y != node.size.y for layer, node in zip(graph.layers, nodes.values()))
                before_draws = graph.random.primitive_draws
                orthogonal_edge_router(graph)
                self.assertEqual([node.pos.x for node in nodes.values()], [30 * i for i in range(len(heights))])
                self.assertEqual(graph.size.x, 30 * len(heights) - 20)
                self.assertEqual([layer.size.y for layer in graph.layers], bounds)
                self.assertEqual(graph.random.primitive_draws, before_draws)
                if heights == (1.0, .1):
                    self.assertEqual(nodes[1].pos.y, .45)
                    self.assertEqual(bounds[1], .10000000000000003)
        self.assertTrue(rounded_bounds_seen)

    def test_phase_topology_numeric_and_adjacency_guards_reject_without_rng_draw(self):
        for mutate in (lambda g,n: n[0].size.__setattr__("x", True),
                       lambda g,n: n[0].ports[0].outgoing_edges.append(n[0].ports[0].outgoing_edges[0])):
            graph, nodes = make_graph([(7, 3), (11, 5)])
            mutate(graph, nodes)
            with self.assertRaises(UnsupportedFeatureError): greedy_cycle_breaker(graph)
            self.assertEqual(graph.random.primitive_draws, 0)
        for mutate in (lambda g,n: n[0].size.__setattr__('x',1_000_001),
                       lambda g,n: n[1].properties.update(LAYER_CONSTRAINT='LAST')):
            graph,nodes=make_graph([(7,3),(11,5)])
            mutate(graph,nodes)
            endpoints=[(e,e.source,e.target)for n in nodes.values() for p in n.ports for e in p.outgoing_edges]
            dimensions=[(n.size.x,n.size.y)for n in nodes.values()]
            original=graph.origin.to_json()
            greedy_cycle_breaker(graph)
            self.assertEqual([(e,e.source,e.target)for n in nodes.values() for p in n.ports for e in p.outgoing_edges],endpoints)
            self.assertEqual([(n.size.x,n.size.y)for n in nodes.values()],dimensions)
            self.assertEqual(graph.origin.to_json(),original)
            self.assertEqual(graph.random.primitive_draws,0)
        graph, _ = make_graph([(1, 1)] * 9)
        with self.assertRaises(UnsupportedFeatureError): network_simplex_layerer(graph)

    def test_bk_checks_unproven_processor_preconditions_itself(self):
        for mutate in (lambda g,n: g.properties.pop("NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES"),
                       lambda g,n: n[0].ports[0].anchor.__setattr__("y", 1),
                       lambda g,n: n[0].properties.update(PORT_CONSTRAINTS="FREE")):
            graph, nodes = make_graph([(7, 3), (11, 5)])
            run_ordering(graph); prepare_centered_ports(graph); mutate(graph, nodes)
            before = [node.pos.y for node in nodes.values()]
            with self.assertRaises(UnsupportedFeatureError): bk_node_placer(graph)
            self.assertEqual([node.pos.y for node in nodes.values()], before)
        # Actual pinned generated BK private-kernel probes independently give
        # these positions and unchanged offset; these former E04 restrictions
        # are now covered by the complete reviewed BK block implementation.
        for top, port_y, expected in [(1, 1.5, [1, 0]), (0, 1, [1.5, 0])]:
            graph, nodes = make_graph([(7, 3), (11, 5)])
            run_ordering(graph); prepare_centered_ports(graph)
            nodes[0].margin.top = top
            nodes[0].ports[0].pos.y = port_y
            bk_node_placer(graph)
            self.assertEqual([nodes[index].pos.y for index in (0, 1)], expected)
            self.assertEqual((graph.offset.x, graph.offset.y), (0, 0))

    def test_sweep_checks_ordering_preconditions_before_consuming_randomness(self):
        for mutate in (lambda g,n: n[0].properties.update(PORT_CONSTRAINTS="FREE"),
                       lambda g,n: setattr(n[0], "port_sides_cached", False),
                       lambda g,n: n[0].port_side_indices.update(EAST=(3, 4)),
                       lambda g,n: setattr(n[0].ports[0], "side", "NORTH")):
            graph, nodes = make_graph([(7, 3), (11, 5)])
            network_simplex_layerer(graph); prepare_sides(graph); mutate(graph, nodes)
            before = graph.random.state48
            with self.assertRaises(UnsupportedFeatureError): layer_sweep(graph, strategy="BARYCENTER")
            self.assertEqual(graph.random.state48, before)
            self.assertEqual(graph.random.primitive_draws, 0)
        graph, _ = make_graph([(7, 3), (11, 5)])
        with self.assertRaises(UnsupportedFeatureError): layer_sweep(graph, strategy="MEDIAN")

    def test_orthogonal_checks_alignment_epsilon_and_real_layer_bounds(self):
        for delta, expected_bends in [(0.0005, []), (0.0011, [(17, 2.5), (17, 2.5011)]),
                                      (0.01, [(17, 2.5), (17, 2.51)])]:
            graph, nodes = make_graph([(7, 3), (11, 5)])
            run_ordering(graph); prepare_centered_ports(graph); bk_node_placer(graph); prepare_layer_bounds(graph)
            nodes[1].pos.y += delta
            orthogonal_edge_router(graph)
            edge = nodes[0].ports[0].outgoing_edges[0]
            self.assertEqual([(point.x, point.y) for point in edge.bend_points], expected_bends)
        # An exact epsilon comparison uses zero-height anchors, avoiding the
        # cancellation in (2.5 +0.001)-2.5, which is slightly less than0.001.
        graph, nodes = make_graph([(0, 0), (0, 0)])
        run_ordering(graph); prepare_centered_ports(graph); bk_node_placer(graph); prepare_layer_bounds(graph)
        nodes[1].pos.y = 0.001
        orthogonal_edge_router(graph)
        self.assertEqual(nodes[0].ports[0].outgoing_edges[0].bend_points, [])
        self.assertEqual(graph.size.x, 20)
        graph, _ = make_graph([(7, 3), (11, 5)])
        run_ordering(graph); prepare_centered_ports(graph); bk_node_placer(graph)
        with self.assertRaises(UnsupportedFeatureError): orthogonal_edge_router(graph)

    def test_all_19_nonempty_e04_inputs_match_official_bk_and_route_coordinates(self):
        suite = ROOT / "tests/fixtures/suites/E04"
        cases = json.loads((suite / "cases.json").read_text(encoding="utf8"))["cases"]
        checked = 0
        for case in cases:
            request = json.loads((suite / case["request"]).read_text(encoding="utf8"))
            source_nodes = request["graph"].get("children", [])
            if not source_nodes:
                continue
            with self.subTest(case=case["id"]):
                node_index = {node["id"]: i for i, node in enumerate(source_nodes)}
                links = request["graph"].get("edges", [])
                by_source = {edge["sources"][0]: edge["targets"][0] for edge in links}
                targets = set(by_source.values())
                first = next(node["id"] for node in source_nodes if node["id"] not in targets)
                path = [first]
                while path[-1] in by_source: path.append(by_source[path[-1]])
                path_index = {identity: i for i, identity in enumerate(path)}
                sizes = [(source_nodes[node_index[identity]]["width"], source_nodes[node_index[identity]]["height"]) for identity in path]
                options = resolve_options(constructor=request["constructor"], layout_arguments=request["layoutArguments"], local=request["graph"].get("layoutOptions"))
                graph, nodes = make_graph(sizes, order=[path_index[node["id"]] for node in source_nodes],
                                         edge_order=[path_index[edge["sources"][0]] for edge in links],
                                         seed=options.values["org.eclipse.elk.randomSeed"], local=request["graph"].get("layoutOptions"),
                                         constructor=request["constructor"], arguments=request["layoutArguments"])
                original = copy.deepcopy(graph.origin.to_json())
                run_ordering(graph); prepare_centered_ports(graph); bk_node_placer(graph); prepare_layer_bounds(graph)
                orthogonal_edge_router(graph)
                observed = json.loads((suite / "oracle" / case["id"] / "run-01/observation.json").read_text(encoding="utf8"))["result"]
                padding = options.values["org.eclipse.elk.padding"]
                for expected in observed["children"]:
                    actual = nodes[path_index[expected["id"]]]
                    self.assertAlmostEqual(actual.pos.x, expected["x"] - padding.left, delta=1e-6)
                    self.assertAlmostEqual(actual.pos.y, expected["y"] - padding.top, delta=1e-6)
                self.assertAlmostEqual(graph.size.x, observed["width"] - padding.left - padding.right, delta=1e-6)
                self.assertEqual(graph.origin.to_json(), original)
                checked += 1
        self.assertEqual(checked, 19)


if __name__ == "__main__":
    unittest.main()
