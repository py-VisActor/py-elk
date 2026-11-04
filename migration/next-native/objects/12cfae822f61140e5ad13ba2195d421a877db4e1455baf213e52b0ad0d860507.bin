# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# ELK algorithm: Copyright Kiel University and others.
# Priority queue algorithm: Copyright2008 Google Inc., Apache-2.0.
# Fixed elkjs0.12.1 worker275e6caf; HOST19/root/coffman-graham-source-review-01.
"""Actual Coffman-Graham layering, including its boxed-identity comparator.

The native multimap and heap are narrow protocol adapters for this caller,
not transplanted Guava/GWT runtime classes. Raw cyclic direct-phase inputs
fail explicitly instead of imposing a Python recursion limit on valid DAGs.
"""
from .graph import Layer,set_layer
from .property_access import read_layered_scalar
from .integer_box_tokens import value_of_integer_box
from ...execution.diagnostics import BasicProgressMonitor
from ...execution.identity import identity_hash as _host_identity_hash
from ..triangulation import ValueMap
from weakref import WeakKeyDictionary


def _compare(first,second):return -1 if first<second else 1 if first>second else 0


def _outgoing(node):
    lists=[port.outgoing_edges for port in node.ports]
    return(edge for edges in lists for edge in edges)


def _incoming(node):
    lists=[port.incoming_edges for port in node.ports]
    return(edge for edges in lists for edge in edges)


class _TopoLists:
    def __init__(self,owner):
        self.map=ValueMap(lambda node:0 if node is None else owner.identity_hash(node),
                          lambda first,second:first is second)

    def get(self,node):
        values=self.map.get(node)
        # Source absent get returns a fresh collection, without inserting it.
        return []if values is None else values

    def put(self,node,value):
        values=self.map.get(node)
        if values is None:
            values=[value]
            self.map.put(node,values)
        else:values.append(value)

    def clear(self):
        # Source clears stored collections before clearing the same map.
        # Iterating values does not manufacture extra identity-hash requests.
        for bucket in self.map.buckets.values():
            for _,values in bucket:values.clear()
        self.map.buckets.clear();self.map.count=0


class _NodeQueue:
    """Comparator-directed narrow heap with Source offer/merge tie order."""
    def __init__(self,compare):self.heap=[];self.compare=compare

    def offer(self,item):
        if item is None:raise TypeError('A queue item is null')
        index=len(self.heap);self.heap.append(item)
        while index>0:
            child=index;index=(index-1)//2
            if self.compare(self.heap[index],item)<=0:
                self.heap[child]=item;return True
            self.heap[child]=self.heap[index]
        self.heap[index]=item
        return True

    def _merge(self,index):
        size=len(self.heap);value=self.heap[index]
        while index*2+1<size:
            child=index*2+1
            if child+1<size and self.compare(self.heap[child+1],self.heap[child])<0:child+=1
            if self.compare(value,self.heap[child])<0:break
            self.heap[index]=self.heap[child];index=child
        self.heap[index]=value

    def poll(self):
        if not self.heap:return None
        value=self.heap[0];last=self.heap.pop()
        if self.heap:
            self.heap[0]=last;self._merge(0)
        return value


_CONFIGURATION=None


def _configuration():
    global _CONFIGURATION
    if _CONFIGURATION is None:
        from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as Strategy
        p1,p2,p3,_,_=tuple(LayeredPhase)
        _CONFIGURATION=LayoutProcessorConfiguration()
        _CONFIGURATION.add_before(p1,Strategy.EDGE_AND_LAYER_CONSTRAINT_EDGE_REVERSER)
        _CONFIGURATION.add_before(p2,Strategy.LAYER_CONSTRAINT_PREPROCESSOR)
        _CONFIGURATION.add_before(p3,Strategy.LAYER_CONSTRAINT_POSTPROCESSOR)
    return _CONFIGURATION


class CoffmanGrahamLayerer:
    source_name='CoffmanGrahamLayerer'

    def __init__(self):
        _configuration()
        self._identity_codes=WeakKeyDictionary()
        self.in_topological=_TopoLists(self)
        self.node_mark=None;self.edge_mark=None
        self.in_degree=None;self.out_degree=None;self.topological_order=None

    def identity_hash(self,node):
        if node not in self._identity_codes:
            graph=node.graph if node.graph is not None else node.layer.graph
            method=getattr(graph,'identity_hash',None)
            code=method(node)if method is not None else _host_identity_hash(graph,node)
            # Preserve the first code obtained from the common allocator.
            # No second counter and no input JSON $H is involved.
            self._identity_codes[node]=code
        return self._identity_codes[node]

    def get_layout_processor_configuration(self,graph):return _configuration()

    def _can_add(self,node,layer):
        for edge in _outgoing(node):
            if edge.target.owner.layer is layer:return False
        return True

    def _compare_nodes_in_topological(self,first,second):
        first_values=self.in_topological.get(first)
        second_values=self.in_topological.get(second)
        i=len(first_values);j=len(second_values)
        while i>0 and j>0:
            i-=1;j-=1
            left=first_values[i];right=second_values[j]
            if left is not right:return _compare(left.value,right.value)
        # This is intentionally hasNext(i<size), not hasPrevious(i>0).
        first_has_next=i<len(first_values);second_has_next=j<len(second_values)
        if not first_has_next and not second_has_next:return _compare(first.id,second.id)
        return 1 if first_has_next else -1

    def _dfs(self,start,node):
        if self.node_mark[node.id]:return
        frames=[(node,_outgoing(node))];active={id(node)}
        while frames:
            current,edges=frames[-1]
            try:edge=next(edges)
            except StopIteration:
                self.node_mark[current.id]=True
                active.remove(id(current));frames.pop()
                continue
            target=edge.target.owner
            for transitive in _incoming(target):
                if transitive.source.owner is start:self.edge_mark[transitive.id]=True
            if self.node_mark[target.id]:continue
            if id(target)in active:
                raise RecursionError('Raw cyclic transitive reduction has no finite postorder')
            active.add(id(target));frames.append((target,_outgoing(target)))

    def _transitive_reduction(self,graph):
        for start in graph.layerless_nodes:
            for index in range(len(self.node_mark)):self.node_mark[index]=False
            for edge in _outgoing(start):self._dfs(start,edge.target.owner)

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Coffman-Graham Layering',1)
        if not graph.layerless_nodes:
            monitor.done();return
        width=read_layered_scalar(graph,'LAYERING_COFFMAN_GRAHAM_LAYER_BOUND',
                                  'LAYERING_COFFMAN_GRAHAM_LAYER_BOUND_0')
        if type(width)is not int:raise TypeError('The actual layer bound is an Integer')
        edge_index=0
        for index,node in enumerate(graph.layerless_nodes):
            node.id=index
            for edge in _outgoing(node):edge.id=edge_index;edge_index+=1
        count=len(graph.layerless_nodes)
        self.node_mark=[False]*count;self.edge_mark=[False]*edge_index
        self.in_degree=[0]*count;self.out_degree=[0]*count;self.topological_order=[0]*count
        self.in_topological.clear()
        self._transitive_reduction(graph)
        sources=_NodeQueue(self._compare_nodes_in_topological)
        for node in graph.layerless_nodes:
            for edge in _incoming(node):
                if not self.edge_mark[edge.id]:self.in_degree[node.id]+=1
            if self.in_degree[node.id]==0:sources.offer(node)
        index=0
        while sources.heap:
            node=sources.poll();self.topological_order[node.id]=index;index+=1
            for edge in _outgoing(node):
                if self.edge_mark[edge.id]:continue
                target=edge.target.owner;self.in_degree[target.id]-=1
                self.in_topological.put(target,value_of_integer_box(self.topological_order[node.id]))
                if self.in_degree[target.id]==0:sources.offer(target)
        sinks=_NodeQueue(lambda first,second:-_compare(self.topological_order[first.id],
                                                     self.topological_order[second.id]))
        for node in graph.layerless_nodes:
            for edge in _outgoing(node):
                if not self.edge_mark[edge.id]:self.out_degree[node.id]+=1
            if self.out_degree[node.id]==0:sinks.offer(node)
        layers=[]
        def create_layer():
            layer=Layer(graph);layers.append(layer);return layer
        current=create_layer()
        while sinks.heap:
            node=sinks.poll()
            if len(current.nodes)>=width or not self._can_add(node,current):current=create_layer()
            set_layer(node,current)
            for edge in _incoming(node):
                if self.edge_mark[edge.id]:continue
                source=edge.source.owner;self.out_degree[source.id]-=1
                if self.out_degree[source.id]==0:sinks.offer(source)
        for index in range(len(layers)-1,-1,-1):graph.layers.append(layers[index])
        graph.layerless_nodes.clear()
        monitor.done()
