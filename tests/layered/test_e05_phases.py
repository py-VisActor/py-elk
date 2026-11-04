"""Approved E05 phase units; no claim of a complete native E05 pipeline."""
import copy
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from pyelk._errors import UnsupportedFeatureError
from pyelk.model import Graph
from pyelk.options import resolve_options
from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Layer, Vec2, set_layer, set_port_owner, set_source, set_target
from pyelk.algorithms.layered.phases import JavaRandom, greedy_cycle_breaker, network_simplex_layerer, layer_sweep, bk_node_placer
from pyelk.algorithms.layered.cycles import greedy_cycle_breaker as source_greedy_kernel
from pyelk.algorithms.layered.crossing import get_successor_constraints, _count_all, _PairCounter, _GreedySwitch, _Fenwick


def make_dag(count, pairs, *, order=None, edge_order=None):
    """Explicit importer prerequisites; this is a phase test, not production import."""
    order = list(range(count)) if order is None else order
    edge_order = list(range(len(pairs))) if edge_order is None else edge_order
    raw = {'id': 'r', 'business': {'$H': False, 'error': {'stack': 'keep'}},
           'children': [{'id': f'n{i}', 'width': 40, 'height': 30} for i in order],
           'edges': [{'id': f'e{i}', 'sources': [f'n{pairs[i][0]}'], 'targets': [f'n{pairs[i][1]}']} for i in edge_order]}
    origin = Graph.from_json(raw)
    graph = LGraph(origin, resolve_options(), JavaRandom(7))
    nodes = {i: LNode(graph, origin.node(f'n{i}'), size=Vec2(40, 30)) for i in order}
    graph.layerless_nodes[:] = [nodes[i] for i in order]
    edges = []
    for index in edge_order:
        a, b = pairs[index]
        edge = LEdge(origin.edge(f'e{index}'))
        source, target = LPort(), LPort()
        set_port_owner(source, nodes[a]); set_port_owner(target, nodes[b])
        set_source(edge, source); set_target(edge, target)
        edges.append(edge)
    return graph, nodes, edges


def capture_greedy_scratch(graph):
    """Observe actual Python locals at return without adding runtime hooks."""
    observed = {}
    previous = sys.gettrace()
    def trace(frame, event, arg):
        if frame.f_code is source_greedy_kernel.__code__:
            if event == 'return':
                observed.update({key: list(frame.f_locals[key]) for key in ['indegree', 'outdegree', 'marks']})
            return trace
        return None
    try:
        sys.settrace(trace)
        greedy_cycle_breaker(graph)
    finally:
        sys.settrace(previous)
    return observed


def make_proper(layers, pairs, *, seed=1):
    graph, nodes, edges = make_dag(sum(map(len,layers)), pairs)
    graph.random = JavaRandom(seed)
    graph.layerless_nodes.clear()
    for indices in layers:
        layer = Layer(graph)
        graph.layers.append(layer)
        for index in indices:
            node = nodes[index]
            set_layer(node,layer)
            node.properties['PORT_CONSTRAINTS'] = 'FIXED_SIDE'
            for port in node.ports:
                port.side = 'EAST' if port.outgoing_edges else 'WEST'
            node.ports.sort(key=lambda port: 0 if port.side == 'EAST' else 1)
            node.port_sides_cached = True
            for side in ('EAST','WEST'):
                values = [i for i,p in enumerate(node.ports) if p.side == side]
                if values:
                    node.port_side_indices[side] = values[0],values[-1]+1
    return graph,nodes,edges


class E05CrossingTests(unittest.TestCase):
    def test_original_six_node_multitrial_order_port_and_rng_vector(self):
        # Independent original generated phase vector: formal-dag-traces/
        # e05-crossing-six, phase8; this test has explicit phase prerequisites.
        graph,nodes,edges = make_proper([[0,1],[2,3],[5,4]],
            [(0,2),(0,3),(1,2),(1,3),(2,4),(3,5)])
        original = graph.origin.to_json()
        endpoints = [(edge,edge.source,edge.target) for edge in edges]
        layer_sweep(graph,strategy='BARYCENTER')
        self.assertEqual([[node.origin.id for node in layer.nodes] for layer in graph.layers],
                         [['n1','n0'],['n3','n2'],['n5','n4']])
        self.assertEqual([p.outgoing_edges[0].origin.id for p in nodes[0].ports],['e1','e0'])
        self.assertEqual([p.outgoing_edges[0].origin.id for p in nodes[1].ports],['e3','e2'])
        self.assertEqual((graph.random.seedhi,graph.random.seedlo,graph.random.primitive_draws),
                         (7733929,6400910,94))
        constraints = [nodes[i].properties['IN_LAYER_SUCCESSOR_CONSTRAINTS'] for i in nodes]
        self.assertTrue(all(value == [] for value in constraints))
        self.assertEqual(len({id(value) for value in constraints}),6)
        saved = [[node for node in layer.nodes] for layer in graph.layers]
        layer_sweep(graph,strategy='TWO_SIDED_GREEDY_SWITCH')
        self.assertEqual([layer.nodes for layer in graph.layers],saved)
        self.assertEqual((graph.random.seedhi,graph.random.seedlo,graph.random.primitive_draws),
                         (11665767,4283555,97))
        self.assertEqual([(edge,edge.source,edge.target) for edge in edges],endpoints)
        self.assertEqual(graph.origin.to_json(),original)
        self.assertTrue(all(node.properties['PORT_CONSTRAINTS'] == 'FIXED_ORDER' for node in nodes.values()))

    def test_greedy_switch_real_pair_improvement_and_stable_ties(self):
        graph,nodes,_ = make_proper([[0,1],[2,3],[4]],[(0,3),(1,2),(2,4),(3,4)])
        # Explicit fixed clockwise WEST order avoids a separate port-order
        # crossing at the join, so this control isolates the upper-node swap.
        nodes[4].ports.reverse()
        for layer in graph.layers:
            for index,node in enumerate(layer.nodes):
                node.id=index
                node.properties['PORT_CONSTRAINTS']='FIXED_ORDER'
        order = [list(layer.nodes) for layer in graph.layers]
        self.assertEqual(_count_all(order),1)
        counter = _PairCounter(order,0)
        self.assertEqual(counter.counts(nodes[0],nodes[1]),(1,0))
        minimizer = _GreedySwitch()
        self.assertTrue(minimizer.first(order,True))
        self.assertEqual(order[0],[nodes[1],nodes[0]])
        self.assertEqual(_count_all(order),0)
        self.assertFalse(minimizer.minimize(order,0,True,False))
        # Only the actual upper-node constraint read materializes its default.
        self.assertEqual(nodes[0].properties['IN_LAYER_SUCCESSOR_CONSTRAINTS'],[])

    def test_mutable_default_reuses_existing_empty_and_clones_per_node(self):
        graph,nodes,_ = make_proper([[0],[1,2]],[(0,1),(0,2)])
        existing=[]
        nodes[1].properties['IN_LAYER_SUCCESSOR_CONSTRAINTS']=existing
        self.assertIs(get_successor_constraints(nodes[1]),existing)
        self.assertIsNot(get_successor_constraints(nodes[0]),get_successor_constraints(nodes[2]))
        layer_sweep(graph,strategy='BARYCENTER')
        self.assertIs(nodes[1].properties['IN_LAYER_SUCCESSOR_CONSTRAINTS'],existing)

    def test_guarded_constraints_and_topology_reject_before_rng_or_id_mutation(self):
        for mutate in [lambda g,n,e:n[1].properties.update(IN_LAYER_SUCCESSOR_CONSTRAINTS=[n[2]]),
                         lambda g,n,e:n[1].properties.update(IN_LAYER_LAYOUT_UNIT=n[1]),
                         lambda g,n,e:n[1].properties.update(BARYCENTER_ASSOCIATES=[]),
                         lambda g,n,e:g.properties.update(THOROUGHNESS=8),
                         lambda g,n,e:g.properties.update(CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER=True),
                         lambda g,n,e:e[0].target.incoming_edges.append(e[0])]:
            graph,nodes,edges=make_proper([[0],[1,2]],[(0,1),(0,2)])
            mutate(graph,nodes,edges)
            for node in nodes.values(): node.id=71
            state=graph.random.state48
            with self.subTest(mutate=mutate),self.assertRaises(UnsupportedFeatureError):
                layer_sweep(graph,strategy='BARYCENTER')
            self.assertEqual([node.id for node in nodes.values()],[71]*3)
            self.assertEqual((graph.random.state48,graph.random.primitive_draws),(state,0))
        graph,_,_=make_proper([[0],[1,2]],[(0,1),(0,2)])
        with self.assertRaises(UnsupportedFeatureError):
            layer_sweep(graph,strategy='TWO_SIDED_GREEDY_SWITCH')

    def test_fenwick_remove_all_rank_and_empty_singleton_early_return(self):
        tree=_Fenwick(5)
        for value in (0,2,2,4): tree.add(value)
        self.assertEqual((tree.rank(0),tree.rank(2),tree.rank(3),tree.rank(5)),(0,1,3,4))
        tree.remove_all(2)
        self.assertEqual((tree.size,tree.rank(5)),(2,2))
        for layers,pairs in [([],[]),([[0]],[])]:
            graph,nodes,_=make_proper(layers,pairs)
            for node in nodes.values(): node.id=73
            graph.id=81
            state=graph.random.state48
            for strategy in ('BARYCENTER','TWO_SIDED_GREEDY_SWITCH'):
                layer_sweep(graph,strategy=strategy)
                self.assertEqual((graph.id,graph.random.state48,graph.random.primitive_draws),(81,state,0))
                self.assertTrue(all(node.id==73 and 'IN_LAYER_SUCCESSOR_CONSTRAINTS' not in node.properties for node in nodes.values()))


class E05PlacementTests(unittest.TestCase):
    def test_actual_fork_block_compaction_coordinates_and_source_model_isolation(self):
        # Official layered-fork phase13 prerequisites/effects, literal geometry.
        graph,nodes,edges=make_proper([[0],[1,2]],[(0,1),(0,2)])
        graph.properties['NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES']=True
        for node in nodes.values():
            node.properties['PORT_CONSTRAINTS']='FIXED_ORDER'
        for index,port in enumerate(nodes[0].ports):
            port.pos=Vec2(40,(index+1)*10)
        for index in (1,2):
            nodes[index].ports[0].pos=Vec2(0,15)
        origin=graph.origin.to_json()
        endpoint_order=[(edge,edge.source,edge.target) for edge in edges]
        state=graph.random.state48
        bk_node_placer(graph)
        self.assertEqual([nodes[i].pos.y for i in range(3)],[5,0,50])
        self.assertEqual([nodes[i].id for i in range(3)],[0,1,2])
        self.assertEqual([layer.id for layer in graph.layers],[0,1])
        self.assertEqual([(edge,edge.source,edge.target) for edge in edges],endpoint_order)
        self.assertEqual((graph.random.state48,graph.random.primitive_draws),(state,0))
        self.assertEqual(graph.origin.to_json(),origin)

    def test_decimal_operation_order_and_nonzero_margin_or_noncentered_actual_port(self):
        for heights,top,source_y,expected in [((1.0,.1),0,.5,[0,.45]),
                                               ((3,5),1,1.5,[1,0]),
                                               ((3,5),0,1,[1.5,0])]:
            graph,nodes,_=make_proper([[0],[1]],[(0,1)])
            graph.properties['NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES']=True
            for index,height in enumerate(heights):
                nodes[index].size.y=height
                nodes[index].ports[0].pos=Vec2(40 if index==0 else 0,source_y if index==0 else height/2)
            nodes[0].margin.top=top
            with self.subTest(heights=heights,top=top,source=source_y):
                bk_node_placer(graph)
                self.assertEqual([nodes[i].pos.y for i in (0,1)],expected)
                self.assertEqual(graph.random.primitive_draws,0)

    def test_true_tiny_multiport_margin_is_preserved(self):
        graph,nodes,_=make_proper([[0],list(range(1,8))],[(0,i) for i in range(1,8)])
        graph.properties['NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES']=True
        nodes[0].size.y=1e-14
        step=10+(1e-14-80)/8  # actual NodeSize source expression, not height/8
        position=0.0
        for port in nodes[0].ports:
            position+=step
            port.pos=Vec2(40,position)
        nodes[0].margin.bottom=position-1e-14
        for i in range(1,8):
            nodes[i].size.y=0
        before=nodes[0].margin.bottom
        self.assertGreater(before,0)
        bk_node_placer(graph)
        self.assertEqual(nodes[0].margin.bottom,before)
        self.assertTrue(all(math.isfinite(node.pos.y) for node in nodes.values()))
        self.assertEqual(graph.random.primitive_draws,0)

    def test_invalid_straightening_anchor_and_nonfinite_geometry_fail_before_mutation(self):
        for mutate in [lambda g,n:g.properties.pop('NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES'),
                         lambda g,n:g.properties.update(NODE_PLACEMENT_BK_FIXED_ALIGNMENT='BALANCED'),
                         lambda g,n:g.properties.update(NODE_PLACEMENT_BK_EDGE_STRAIGHTENING='OFF'),
                         lambda g,n:setattr(n[0].ports[0].anchor,'y',1),
                         lambda g,n:setattr(n[0].ports[0].pos,'y',float('nan')),
                         lambda g,n:n[0].properties.update(SPACING_INDIVIDUAL={})]:
            graph,nodes,_=make_proper([[0],[1]],[(0,1)])
            graph.properties['NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES']=True
            mutate(graph,nodes)
            state=graph.random.state48
            for node in nodes.values():node.id=71
            with self.subTest(mutate=mutate),self.assertRaises(UnsupportedFeatureError):
                bk_node_placer(graph)
            self.assertEqual([node.id for node in nodes.values()],[71,71])
            self.assertEqual([node.pos.y for node in nodes.values()],[0,0])
            self.assertEqual((graph.random.state48,graph.random.primitive_draws),(state,0))


class E05ApprovedGreedyTests(unittest.TestCase):
    def test_approved_network_simplex_wrapper_preserves_five_to_eight_node_paths(self):
        for count in range(5, 9):
            with self.subTest(nodes=count):
                graph, nodes, edges = make_dag(count, [(i, i+1) for i in range(count-1)],
                                               order=list(reversed(range(count))))
                original = graph.origin.to_json()
                endpoints = [(edge, edge.source, edge.target) for edge in edges]
                state = graph.random.state48
                network_simplex_layerer(graph)
                self.assertEqual([[node.origin.id for node in layer.nodes] for layer in graph.layers],
                                 [[f'n{i}'] for i in range(count)])
                self.assertEqual(graph.layerless_nodes, [])
                self.assertTrue(all(nodes[i].layer is graph.layers[i] for i in range(count)))
                self.assertEqual([(edge, edge.source, edge.target) for edge in edges], endpoints)
                self.assertEqual((graph.random.state48, graph.random.primitive_draws), (state, 0))
                self.assertEqual(graph.origin.to_json(), original)

    def test_real_generated_marks_for_fork_join_diamond_and_long_edge_inputs(self):
        # Actual generated source before-cleanup vectors, not final coordinates.
        # references/e05-source-components-B.json phase:GREEDY evidence points
        # to the original eight three-engine observations and raw scratch data.
        vectors = [
            (3, [(0, 1), (0, 2)], [0, 1, 2], [1, 3, 2]),
            (3, [(0, 2), (1, 2)], [0, 2, 1], [1, 3, 2]),
            (4, [(0, 1), (0, 2), (1, 3), (2, 3)], [0, 1, 3, 2], [1, 3, 4, 2]),
            (4, [(0, 1), (1, 2), (2, 3), (0, 3)], [0, 1, 2, 3], [1, 2, 3, 4]),
        ]
        for count, pairs, order, expected in vectors:
            with self.subTest(pairs=pairs):
                graph, nodes, edges = make_dag(count, pairs, order=order)
                original = copy.deepcopy(graph.origin.to_json())
                adjacency = {node: [(port, list(port.incoming_edges), list(port.outgoing_edges)) for port in node.ports]
                             for node in graph.layerless_nodes}
                state, draws = graph.random.state48, graph.random.primitive_draws
                scratch = capture_greedy_scratch(graph)
                self.assertEqual(scratch['marks'], expected)
                self.assertEqual(scratch['outdegree'], [0] * count)
                self.assertEqual([node.id for node in graph.layerless_nodes], list(range(count)))
                self.assertEqual(graph.layerless_nodes, [nodes[i] for i in order])
                self.assertEqual((graph.random.state48, graph.random.primitive_draws), (state, draws))
                self.assertEqual(graph.origin.to_json(), original)
                for node, ports in adjacency.items():
                    self.assertEqual([(p, p.incoming_edges, p.outgoing_edges) for p in node.ports], ports)
                self.assertTrue(all(scratch['marks'][edge.source.owner.id] < scratch['marks'][edge.target.owner.id] for edge in edges))
                self.assertTrue(all('REVERSED' not in edge.properties for edge in edges))

    def test_eight_node_fanin_fanout_and_dense_real_vectors(self):
        for pairs, order, expected in [
            ([(0, i) for i in range(1, 8)], list(range(8)), [1, 8, 7, 6, 5, 4, 3, 2]),
            ([(i, 7) for i in range(7)], [0, 7, 1, 2, 3, 4, 5, 6], [1, 8, 2, 3, 4, 5, 6, 7]),
            ([(i, j) for i in range(8) for j in range(i+1, 8)], list(range(8)), list(range(1, 9))),
        ]:
            with self.subTest(edges=len(pairs)):
                graph, _, _ = make_dag(8, pairs, order=order)
                self.assertEqual(capture_greedy_scratch(graph)['marks'], expected)
                self.assertEqual(graph.random.primitive_draws, 0)

    def test_cycle_parallel_disconnected_and_external_adjacency_fail_before_mutation(self):
        # Keep the historical method denominator. E06 independently approves
        # these former topology negatives. The ring vector is the actual fixed
        # worker seed7 vector (E06/A/cycle-probes.json); the other two are the
        # source sink/source drain and owner-same degree-skip paths.
        for count,pairs,expected_marks,reversed_ids,expected_rng in [
            (3,[(0,1),(1,2),(2,0)],[3,1,2],{'e0'},(12259095,10049325,1)),
            (2,[(0,1),(0,1)],[1,2],set(),None),
            (2,[(0,0),(0,1)],[1,2],set(),None),
        ]:
            with self.subTest(e06_approved=pairs):
                graph,nodes,edges=make_dag(count,pairs)
                before=graph.origin.to_json()
                geometry={n:(copy.deepcopy(n.pos),copy.deepcopy(n.size),[(p,p.side,copy.deepcopy(p.pos),copy.deepcopy(p.anchor)) for p in n.ports]) for n in nodes.values()}
                state=graph.random.state48
                scratch=capture_greedy_scratch(graph)
                self.assertEqual(scratch['marks'],expected_marks)
                self.assertEqual({e.origin.id for e in edges if e.properties.get('REVERSED')},reversed_ids)
                if expected_rng is None:
                    self.assertEqual((graph.random.state48,graph.random.primitive_draws),(state,0))
                else:
                    self.assertEqual((graph.random.seedhi,graph.random.seedlo,graph.random.primitive_draws),expected_rng)
                self.assertEqual([n.id for n in graph.layerless_nodes],list(range(count)))
                self.assertEqual(graph.origin.to_json(),before)
                for node,(pos,size,ports) in geometry.items():
                    self.assertEqual((vars(node.pos),vars(node.size)),(vars(pos),vars(size)))
                    self.assertEqual(node.ports,[p for p,_,_,_ in ports])
                    for port,side,position,anchor in ports:
                        self.assertEqual((port.side,vars(port.pos),vars(port.anchor)),(side,vars(position),vars(anchor)))
                for edge in edges:
                    if edge.source.owner is not edge.target.owner:
                        self.assertLess(scratch['marks'][edge.source.owner.id],scratch['marks'][edge.target.owner.id])
        for count, pairs in [(3, [(0, 1)])]:
            with self.subTest(pairs=pairs):
                graph, nodes, _ = make_dag(count, pairs)
                for node in nodes.values():
                    node.id = 81
                state = graph.random.state48
                endpoints = [(edge.source,edge.target) for node in graph.layerless_nodes
                             for port in node.ports for edge in port.outgoing_edges]
                scratch = capture_greedy_scratch(graph)
                self.assertEqual(scratch['marks'],[1,3,2])
                self.assertEqual([node.id for node in graph.layerless_nodes], list(range(count)))
                self.assertEqual([(edge.source,edge.target) for node in graph.layerless_nodes
                                  for port in node.ports for edge in port.outgoing_edges],endpoints)
                self.assertEqual((graph.random.state48, graph.random.primitive_draws), (state, 0))
        graph, nodes, edges = make_dag(3, [(0, 1), (0, 2)])
        edges[0].target.owner = LNode(graph, size=Vec2(1, 1))
        with self.assertRaises(UnsupportedFeatureError):
            greedy_cycle_breaker(graph)

    def test_default_priority_and_eight_node_source_guard_are_explicit(self):
        for value in [False, 1, -1, None, '0']:
            graph, _, edges = make_dag(3, [(0, 1), (0, 2)])
            edges[0].properties['PRIORITY_DIRECTION'] = value
            with self.subTest(priority=value):
                if type(value) is int:
                    before = [(edge.source,edge.target)for edge in edges]
                    self.assertEqual(capture_greedy_scratch(graph)['marks'],[1,3,2])
                    self.assertEqual([(edge.source,edge.target)for edge in edges],before)
                    self.assertEqual(edges[0].properties['PRIORITY_DIRECTION'],value)
                else:
                    with self.assertRaises(UnsupportedFeatureError):greedy_cycle_breaker(graph)
            self.assertEqual(graph.random.primitive_draws, 0)
        graph, _, _ = make_dag(9, [(i, i+1) for i in range(8)])
        before = graph.origin.to_json()
        greedy_cycle_breaker(graph)
        self.assertEqual(len(graph.layerless_nodes),9)
        self.assertEqual([node.id for node in graph.layerless_nodes],list(range(9)))
        self.assertEqual(graph.origin.to_json(),before)
        self.assertEqual(graph.random.primitive_draws,0)


if __name__ == '__main__':
    unittest.main()
