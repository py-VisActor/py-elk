"""Bounded cyclic kernels; source vectors are from the fixed worker, not Python."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import UnsupportedFeatureError
from pyelk.model import Graph
from pyelk.options import resolve_options
from pyelk.execution import create_context
from pyelk.algorithms.layered.graph import (
    LEdge, LGraph, LNode, LPort, Layer, Vec2,
    set_layer, set_port_owner, set_source, set_target,
)
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.algorithms.layered.cycles import (
    greedy_cycle_breaker, reverse_edge, restore_reversed_edges,
)
from pyelk.algorithms.layered.layering import (
    network_simplex_layerer, _component_order, _private_graph,
)
from pyelk.algorithms.layered.import_export import import_graph, export_layout
from pyelk.algorithms.layered.long_edges import long_edge_splitter, long_edge_joiner


def make_graph(count, pairs, *, seed=1):
    """Explicit phase input, without bypassing a production importer guard."""
    raw = {"id": "root", "children": [{"id": f"node-{i}", "width": 0, "height": 0} for i in range(count)],
           "edges": [{"id": f"edge-{i}", "sources": [f"node-{a}"], "targets": [f"node-{b}"]}
                     for i, (a, b) in enumerate(pairs)]}
    model = Graph.from_json(raw)
    graph = LGraph(model, resolve_options(), JavaRandom(seed))
    nodes = [LNode(graph, origin=model.node(f"node-{i}")) for i in range(count)]
    graph.layerless_nodes[:] = nodes
    edges = []
    for index, (a, b) in enumerate(pairs):
        edge = LEdge(origin=model.edge(f"edge-{index}"))
        source, target = LPort(), LPort()
        set_port_owner(source, nodes[a]); set_port_owner(target, nodes[b])
        set_source(edge, source); set_target(edge, target)
        edges.append(edge)
    return graph, nodes, edges


def observe(graph):
    observed = {}
    previous = sys.gettrace()
    def trace(frame, event, arg):
        if frame.f_code is greedy_cycle_breaker.__code__:
            if event == "return":
                observed.update({key: list(frame.f_locals[key]) for key in ("indegree", "outdegree", "marks")})
            return trace
        return None
    try:
        sys.settrace(trace)
        greedy_cycle_breaker(graph)
    finally:
        sys.settrace(previous)
    return observed


class CycleKernelTests(unittest.TestCase):
    def test_fixed_generated_greedy_scratch_reversal_and_rng_vectors(self):
        # A/cycle-probes.json records all18 real engine calls and original
        # request bytes. These explicit vectors need no ignored run directory.
        cases = [
            (3, [(0,1),(1,2),(2,0)], 1, [1,0,1], [1,0,0], [1,2,3], {2}, (12262101,7545863,1)),
            (3, [(0,1),(1,2),(2,0)], 7, [1,1,0], [0,1,0], [3,1,2], {0}, (12259095,10049325,1)),
            (3, [(0,1),(1,2),(2,0),(0,2)], 17, [1,0,1], [2,0,0], [1,2,3], {2}, (12286148,4295383,1)),
            (2, [(0,1),(1,0)], -17, [1,0], [1,0], [1,2], {1}, (4488061,14985317,1)),
            (8, [(i,(i+1)%8) for i in range(8)], 7,
             [1,1,1,1,1,1,0,1], [0,0,0,0,0,1,0,0], [4,5,6,7,8,1,2,3], {4}, (12259095,10049325,1)),
            (4, [(a,b) for a in range(4) for b in range(4) if a!=b], 2,
             [2,0,3,1], [2,0,3,1], [2,4,1,3], {1,3,4,5,9,11}, (15123781,9454008,3)),
        ]
        for count,pairs,seed,indeg,outdeg,marks,reversed_ids,rng in cases:
            with self.subTest(count=count,seed=seed,pairs=pairs):
                graph,nodes,edges=make_graph(count,pairs,seed=seed)
                before=graph.origin.to_json()
                scratch=observe(graph)
                self.assertEqual(scratch,{"indegree":indeg,"outdegree":outdeg,"marks":marks})
                self.assertEqual({i for i,e in enumerate(edges) if e.properties.get("REVERSED")},reversed_ids)
                self.assertEqual((graph.random.seedhi,graph.random.seedlo,graph.random.primitive_draws),rng)
                self.assertTrue(graph.properties["CYCLIC"])
                self.assertEqual(graph.origin.to_json(),before)
                for edge in edges:
                    self.assertLess(marks[edge.source.owner.id],marks[edge.target.owner.id])

    def test_unique_maximum_still_consumes_next31(self):
        graph,_,_=make_graph(3,[(0,1),(1,2),(2,0),(0,2)],seed=17)
        bounds=[]
        original=graph.random.next_int
        def next_int(bound):
            bounds.append(bound)
            return original(bound)
        graph.random.next_int=next_int
        greedy_cycle_breaker(graph)
        self.assertEqual(bounds,[1])
        self.assertEqual(graph.random.primitive_draws,1)

    def test_reverse_preserves_port_geometry_junctions_and_copies_bends(self):
        graph,nodes,edges=make_graph(2,[(0,1)])
        edge=edges[0]
        old_source,old_target=edge.source,edge.target
        for index,port in enumerate([old_source,old_target]):
            port.side=["EAST","WEST"][index]
            port.pos=Vec2(index+.1,index+.2);port.anchor=Vec2(index+.3,index+.4)
        bends=[Vec2(.1,.3),Vec2(.2,.4)]
        junctions=[Vec2(.9,.8)]
        edge.bend_points=bends;edge.properties["JUNCTION_POINTS"]=junctions
        ports=[(p,p.side,copy.copy(p.pos),copy.copy(p.anchor)) for p in [old_source,old_target]]
        original=graph.origin.to_json()
        reverse_edge(edge,adapt_ports=True)
        self.assertIs(edge.source,old_target);self.assertIs(edge.target,old_source)
        self.assertEqual([(p.x,p.y) for p in edge.bend_points],[(.2,.4),(.1,.3)])
        self.assertIsNot(edge.bend_points,bends)
        self.assertTrue(all(a is not b for a in bends for b in edge.bend_points))
        self.assertIs(edge.properties["JUNCTION_POINTS"],junctions)
        self.assertTrue(edge.properties["REVERSED"])
        reverse_edge(edge,adapt_ports=False)
        self.assertIs(edge.source,old_source);self.assertIs(edge.target,old_target)
        self.assertIn("REVERSED",edge.properties);self.assertIs(edge.properties["REVERSED"],False)
        for port,side,pos,anchor in ports:
            self.assertEqual((port.side,port.pos.x,port.pos.y,port.anchor.x,port.anchor.y),(side,pos.x,pos.y,anchor.x,anchor.y))
        self.assertEqual(graph.origin.to_json(),original)

    def test_empty_and_one_point_chain_allocate_new_objects(self):
        for original in ([],[Vec2(1,2)]):
            graph,_,edges=make_graph(2,[(0,1)])
            edge=edges[0];edge.bend_points=original
            reverse_edge(edge,adapt_ports=False)
            self.assertIsNot(edge.bend_points,original)
            if original:self.assertIsNot(edge.bend_points[0],original[0])

    def test_restorer_per_port_snapshot_does_not_reverse_a_second_time(self):
        graph,nodes,edges=make_graph(2,[(0,1)])
        edge=edges[0];original=(edge.source,edge.target)
        edge.bend_points=[Vec2(1,2),Vec2(3,4)]
        reverse_edge(edge,adapt_ports=False)
        graph.properties["CYCLIC"]=True
        # Visit the reversed source before its restored source. The edge then
        # appears again in the later port snapshot, but its explicitfalse stops.
        layer=Layer(graph);graph.layers.append(layer)
        for node in reversed(nodes):set_layer(node,layer)
        graph.layerless_nodes.clear()
        state=graph.random.state48
        restore_reversed_edges(graph)
        self.assertEqual((edge.source,edge.target),original)
        self.assertEqual([(p.x,p.y) for p in edge.bend_points],[(1,2),(3,4)])
        self.assertIs(edge.properties["REVERSED"],False)
        self.assertTrue(graph.properties["CYCLIC"])
        self.assertEqual(graph.random.state48,state)

    def test_self_loops_skip_degree_and_reversal_dag_draws_none(self):
        graph,_,edges=make_graph(2,[(0,0),(0,1),(0,1),(1,1)])
        endpoints=[(e.source,e.target) for e in edges]
        state=graph.random.state48
        observe(graph)
        self.assertEqual([(e.source,e.target) for e in edges],endpoints)
        self.assertTrue(all("REVERSED" not in e.properties for e in edges))
        self.assertNotIn("CYCLIC",graph.properties)
        self.assertEqual(graph.random.state48,state)

    def test_ring_two_both_port_orders_have_same_marks_and_one_draw(self):
        for reverse_ports in (False,True):
            graph,nodes,edges=make_graph(2,[(0,1),(1,0)],seed=-17)
            if reverse_ports:
                for node in nodes:node.ports.reverse()
            self.assertEqual(observe(graph)["marks"],[1,2])
            self.assertEqual(graph.random.primitive_draws,1)

    def test_unreviewed_inputs_fail_before_mutation(self):
        graph,nodes,edges=make_graph(2,[(0,1)])
        edge=edges[0];source,target=edge.source,edge.target
        target.properties['INPUT_COLLECT']=True
        reverse_edge(edge,adapt_ports=True)
        self.assertIs(edge.source.owner,nodes[1]);self.assertIsNot(edge.source,target)
        self.assertIs(edge.target,source);self.assertIs(edge.properties['REVERSED'],True)
        self.assertIs(edge.source.properties['OUTPUT_COLLECT'],True)
        self.assertEqual(target.incoming_edges,[])
        self.assertEqual(graph.random.primitive_draws,0)
        for value in (None,0):
            graph,_,edges=make_graph(2,[(0,1)])
            edge=edges[0];edge.properties['REVERSED']=value
            endpoints=(edge.source,edge.target)
            properties=dict(edge.properties)
            with self.assertRaises(UnsupportedFeatureError):reverse_edge(edge,adapt_ports=True)
            self.assertEqual((edge.source,edge.target),endpoints)
            self.assertEqual(edge.properties,properties)
        graph,_,_=make_graph(9,[(i,i+1) for i in range(8)])
        greedy_cycle_breaker(graph)
        self.assertEqual([n.id for n in graph.layerless_nodes],list(range(9)))
        self.assertEqual(graph.random.primitive_draws,0)
        graph,_,_=make_graph(2,[(0,1)]*29)
        greedy_cycle_breaker(graph)
        self.assertEqual(sum(len(p.outgoing_edges)for n in graph.layerless_nodes for p in n.ports),29)
        self.assertEqual(graph.random.primitive_draws,0)
        graph,_,edges=make_graph(2,[(0,1)])
        edges[0].properties["PRIORITY_DIRECTION"]=1
        endpoints=[(e.source,e.target)for e in edges]
        greedy_cycle_breaker(graph)
        self.assertEqual([(e.source,e.target)for e in edges],endpoints)
        self.assertEqual(graph.random.primitive_draws,0)
        graph,nodes,_=make_graph(2,[(0,1)])
        nodes[0].size.x=1_000_001
        greedy_cycle_breaker(graph)
        self.assertEqual(nodes[0].size.x,1_000_001)
        self.assertEqual(graph.random.primitive_draws,0)
        for invalid in (True,-1,float('nan'),float('inf'),10**400):
            graph,nodes,_=make_graph(2,[(0,1)])
            nodes[0].size.x=invalid
            with self.subTest(dimension=invalid),self.assertRaises(UnsupportedFeatureError):greedy_cycle_breaker(graph)
            self.assertEqual(graph.random.primitive_draws,0)

    def test_ns_preserves_parallel_private_edges_and_true_reversal_provenance(self):
        graph,nodes,edges=make_graph(3,[(0,1),(1,2),(2,0),(0,2),(0,2)],seed=1)
        original=graph.origin.to_json()
        greedy_cycle_breaker(graph)
        endpoints=[(e.source,e.target,e.properties.copy()) for e in edges]
        private_nodes,private_edges=_private_graph(_component_order(graph.layerless_nodes))
        self.assertEqual(len(private_nodes),3)
        self.assertEqual(len(private_edges),5)
        self.assertEqual(sum(len(node.outgoing) for node in private_nodes),5)
        state=graph.random.state48
        network_simplex_layerer(graph)
        rank={node:i for i,layer in enumerate(graph.layers) for node in layer.nodes}
        self.assertTrue(all(rank[e.target.owner]>rank[e.source.owner] for e in edges))
        self.assertEqual([(e.source,e.target,e.properties) for e in edges],endpoints)
        self.assertEqual(graph.origin.to_json(),original)
        self.assertEqual(graph.random.state48,state)

    def test_ns_ring_rank_separation_for_two_through_eight(self):
        for n in range(2,9):
            for seed in (-17,1,7):
                with self.subTest(n=n,seed=seed):
                    graph,nodes,edges=make_graph(n,[(i,(i+1)%n) for i in range(n)],seed=seed)
                    # Same original graph with a different genuine port order.
                    if seed==7:
                        for node in nodes:node.ports.reverse()
                    greedy_cycle_breaker(graph)
                    self.assertEqual(sum(e.properties.get("REVERSED",False) for e in edges),1)
                    network_simplex_layerer(graph)
                    self.assertEqual(len(graph.layers),n)
                    self.assertTrue(all(len(layer.nodes)==1 for layer in graph.layers))

    def test_ns_pressure_multiplicity_and_hidden_loop_equivalent(self):
        graph,_,edges=make_graph(8,[(i,i+1) for i in range(7)]+[(0,7)]*21)
        network_simplex_layerer(graph)
        self.assertEqual(len(graph.layers),8)
        self.assertEqual(sum(len(node.ports) for layer in graph.layers for node in layer.nodes),56)
        self.assertEqual(len(edges),28)
        graph,nodes,edges=make_graph(1,[(0,0)]*28)
        endpoints=[(e.source,e.target) for e in edges]
        network_simplex_layerer(graph)
        self.assertEqual([layer.nodes for layer in graph.layers],[[nodes[0]]])
        self.assertEqual([(e.source,e.target) for e in edges],endpoints)

    def test_import_records_source_loop_flag_original_constraints_and_fresh_ports(self):
        source,_,_=make_graph(3,[(0,1),(0,1),(1,2),(2,0),(1,1)])
        raw=source.origin.to_json();raw['business']={'$H':False,'error':{'stack':'keep'}}
        original=copy.deepcopy(raw)
        graph=import_graph(create_context(raw),JavaRandom(1))
        ports=[p for n in graph.layerless_nodes for p in n.ports]
        edges={e for p in ports for e in p.outgoing_edges}
        self.assertEqual((len(ports),len(set(ports)),len(edges)),(10,10,5))
        self.assertEqual(graph.properties['GRAPH_PROPERTIES'],{'SELF_LOOPS'})
        self.assertTrue(all(n.properties['ORIGINAL_PORT_CONSTRAINTS']=='FREE' for n in graph.layerless_nodes))
        self.assertTrue(all(len(p.incoming_edges)+len(p.outgoing_edges)==1 for p in ports))
        self.assertEqual(raw,original);self.assertEqual(graph.origin.to_json(),original)

    def test_pressure_split_join_counts_and_cyclic_true_flag_shallow_propagation(self):
        raw=make_graph(8,[(i,i+1) for i in range(7)]+[(0,7)]*21)[0].origin.to_json()
        graph=import_graph(create_context(raw),JavaRandom(1))
        originals={e for n in graph.layerless_nodes for p in n.ports for e in p.outgoing_edges}
        network_simplex_layerer(graph);long_edge_splitter(graph)
        nodes=[n for layer in graph.layers for n in layer.nodes]
        self.assertEqual(len(nodes),134)  # 8 +21*(gap7-1), real V pressure input.
        self.assertEqual(sum(len(n.ports) for n in nodes),308)
        self.assertEqual(sum(len(p.outgoing_edges) for n in nodes for p in n.ports),154)
        long_edge_joiner(graph)
        self.assertEqual({e for layer in graph.layers for n in layer.nodes for p in n.ports for e in p.outgoing_edges},originals)
        graph,nodes,edges=make_graph(4,[(0,1),(1,2),(2,3),(3,0)],seed=1)
        endpoints=[(e.source,e.target) for e in edges]
        greedy_cycle_breaker(graph)
        reversed_original=next(e for e in edges if e.properties.get('REVERSED'))
        network_simplex_layerer(graph);long_edge_splitter(graph)
        generated=[e for layer in graph.layers for n in layer.nodes for p in n.ports for e in p.outgoing_edges if e.origin is reversed_original.origin and e is not reversed_original]
        self.assertEqual(len(generated),2)
        self.assertTrue(all(e.properties['REVERSED'] is True for e in generated))
        long_edge_joiner(graph);restore_reversed_edges(graph)
        self.assertEqual([(e.source,e.target) for e in edges],endpoints)
        self.assertIs(reversed_original.properties['REVERSED'],False)
        self.assertTrue(all(e.source is None and e.target is None and e.properties['REVERSED'] is True for e in generated))

    def test_export_rejects_wrong_original_direction_even_at_equal_coordinates(self):
        raw=make_graph(2,[(0,1)])[0].origin.to_json()
        graph=import_graph(create_context(raw),JavaRandom(1))
        network_simplex_layerer(graph)
        edge=next(e for layer in graph.layers for n in layer.nodes for p in n.ports for e in p.outgoing_edges)
        old_source,old_target=edge.source,edge.target
        set_source(edge,old_target);set_target(edge,old_source)
        # Both source and target node.pos remain(0,0), and no private true flag
        # reveals the wrong orientation. Only original typed identity detects it.
        edge.properties['REVERSED']=False
        before_layers=list(graph.layers);before=graph.origin.to_json()
        with self.assertRaises(UnsupportedFeatureError):export_layout(graph)
        self.assertEqual(graph.layers,before_layers)
        self.assertEqual(graph.origin.to_json(),before)


if __name__=="__main__":
    unittest.main()
