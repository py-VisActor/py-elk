# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others.
# Source: elkjs0.12.1 worker275e6caf, NetworkSimplexLayerer51972-52100.
# General driver source review: HOST-12/root/ns-driver-source-review-01.
"""Source-general layered rank assignment, including large-component pruning.

The bounded historical layering module remains unchanged. Reviewed arithmetic
methods are reused over a fresh private weighted graph; initialization,
subtree adjacency mutations and explicit DFS frames follow the general caller.
No node/edge count admission limit or alternative layout backend is used.
"""
import math
from collections import deque

from ...execution.diagnostics import BasicProgressMonitor
from .graph import Layer, set_layer
from .property_access import read_layered_scalar
from .layering import _NNode, _NEdge, _NetworkSimplex, _MAX_INT


def _connected_components(nodes):
    for index,node in enumerate(nodes):node.id=index
    visited=set();components=[]
    for first in nodes:
        if first in visited:continue
        ordered=[]
        def enter(node):
            visited.add(node);ordered.append(node)
            return iter((port,edge)for port in node.ports
                        for edge in [*port.incoming_edges,*port.outgoing_edges])
        frames=[enter(first)]
        while frames:
            try:port,edge=next(frames[-1])
            except StopIteration:frames.pop();continue
            opposite=edge.target if edge.source is port else edge.source
            if opposite.owner not in visited:frames.append(enter(opposite.owner))
        if not components or len(components[0])<len(ordered):components.insert(0,ordered)
        else:components.append(ordered)
    return components


def _refresh(node):
    # Source ChangeAwareArrayList invalidates the same incoming-then-outgoing
    # cached incident list. No adjacency changes occur during a solver DFS.
    node.connected[:]=[*node.incoming,*node.outgoing]


def _private_graph(ordered):
    nodes=[_NNode(node,index)for index,node in enumerate(ordered)]
    by_origin={node.origin:node for node in nodes};edges=[]
    for node in nodes:
        for port in node.origin.ports:
            for original in port.outgoing_edges:
                if original.source.owner is original.target.owner:continue
                priority=read_layered_scalar(original,'PRIORITY_SHORTNESS','PRIORITY_SHORTNESS_0')
                # The fixed source's weight and cut arrays use binary64
                # arithmetic, including sums exceeding exact integer range.
                edge=_NEdge(node,by_origin[original.target.owner],len(edges),
                            delta=1,weight=float(max(1,priority)))
                node.outgoing.append(edge);edge.target.incoming.append(edge);edges.append(edge)
    for node in nodes:_refresh(node)
    return nodes,edges


class _GeneralNetworkSimplex(_NetworkSimplex):
    """General source lifecycle with same-order iterative tight-tree DFS."""

    def __init__(self,nodes,edges,previous_layering_node_counts=None):
        self.nodes=nodes;self.edges=edges
        self.previous_layering_node_counts=previous_layering_node_counts
        self.subtree_nodes_stack=None

    def _remove_subtrees(self):
        self.subtree_nodes_stack=deque()
        leaves=deque(node for node in self.nodes if len(node.connected)==1)
        while leaves:
            node=leaves.popleft()
            if not node.connected:continue
            edge=node.connected[0];other=edge.other(node)
            if node.outgoing:other.incoming.remove(edge)
            else:other.outgoing.remove(edge)
            _refresh(other)
            if len(other.connected)==1:leaves.append(other)
            self.subtree_nodes_stack.appendleft((node,edge))
            self.nodes.remove(node)

    def _reattach_subtrees(self):
        while self.subtree_nodes_stack:
            node,edge=self.subtree_nodes_stack.popleft();other=edge.other(node)
            if edge.target is node:
                other.outgoing.append(edge);node.layer=other.layer+edge.delta
            else:
                other.incoming.append(edge);node.layer=other.layer-edge.delta
            _refresh(other)
            self.nodes.append(node)

    def _initialize(self):
        edges=[]
        for index,node in enumerate(self.nodes):
            node.id=index;node.tree=False
            edges.extend(node.outgoing)
        for index,edge in enumerate(edges):edge.id=index;edge.tree=False
        # Allocate over the surviving graph, after actual pruning/reordering.
        _NetworkSimplex.__init__(self,self.nodes,edges,self.previous_layering_node_counts)

    def tight_tree(self,node):
        node.tree=True;frames=[[node,iter(node.connected),1]]
        while frames:
            current,iterator,count=frames[-1]
            try:edge=next(iterator)
            except StopIteration:
                frames.pop()
                if frames:frames[-1][2]+=count
                else:return count
                continue
            if self.edge_visited[edge.id]:continue
            self.edge_visited[edge.id]=True;other=edge.other(current)
            if edge.tree or (not other.tree and edge.delta==edge.target.layer-edge.source.layer):
                if not edge.tree:edge.tree=True;self.tree_edges.append(edge)
                other.tree=True;frames.append([other,iter(other.connected),1])

    def postorder(self,node):
        frames=[[node,iter(node.connected),_MAX_INT]]
        while frames:
            current,iterator,lowest=frames[-1]
            try:edge=next(iterator)
            except StopIteration:
                self.po[current.id]=self.post_order
                result=min(lowest,self.post_order);self.low[current.id]=result
                self.post_order+=1;frames.pop()
                if frames:frames[-1][2]=min(frames[-1][2],result)
                else:return result
                continue
            if edge.tree and not self.edge_visited[edge.id]:
                self.edge_visited[edge.id]=True;other=edge.other(current)
                frames.append([other,iter(other.connected),_MAX_INT])

    def execute(self,iteration_limit,*,monitor=None):
        if monitor is None:monitor=BasicProgressMonitor()
        monitor.begin('Network simplex',1)
        if not self.nodes:monitor.done();return
        for node in self.nodes:node.layer=0
        remove_subtrees=len(self.nodes)>=40
        if remove_subtrees:self._remove_subtrees()
        self._initialize();self.feasible_tree()
        leave=self.leave_edge();iterations=0
        while leave is not None and iterations<iteration_limit:
            self.exchange(leave,self.enter_edge(leave))
            leave=self.leave_edge();iterations+=1
        if remove_subtrees:self._reattach_subtrees()
        self.balance(self.normalize())
        self.cut=None;self.edges=None;self.tree_edges=None;self.edge_visited=None
        self.low=None;self.po=None;self.subtree_nodes_stack=None
        monitor.done()


def _solve_component(ordered,iteration_limit,previous_counts,monitor):
    nodes,edges=_private_graph(ordered)
    solver=_GeneralNetworkSimplex(nodes,edges,previous_counts)
    solver.execute(iteration_limit,monitor=monitor)
    return nodes


def network_simplex_layerer(graph,*,monitor=None):
    """Run the actual component driver; no bounded-input admission domain."""
    if monitor is None:monitor=BasicProgressMonitor()
    monitor.begin('Network simplex layering',1)
    thoroughness=read_layered_scalar(graph,'THOROUGHNESS','THOROUGHNESS_0')*4
    if not graph.layerless_nodes:
        monitor.done();return
    components=_connected_components(graph.layerless_nodes)
    previous_counts=None
    for ordered in components:
        # Worker round_int is a clamp followed by signed32 truncation, not
        # Math.round. sqrt(component length) is positive and finite here.
        root=math.sqrt(len(ordered))
        cast_root=math.trunc(max(-(2**31),min(2**31-1,root)))
        iteration_limit=thoroughness*cast_root
        private_nodes=_solve_component(ordered,iteration_limit,previous_counts,monitor.sub_task(1))
        for node in private_nodes:
            while len(graph.layers)<=node.layer:graph.layers.append(Layer(graph))
            set_layer(node.origin,graph.layers[node.layer])
        if len(components)>1:previous_counts=[len(layer.nodes)for layer in graph.layers]
    graph.layerless_nodes.clear()
    monitor.done()
