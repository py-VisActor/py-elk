# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; HOST18/B/depth-first-source-review-01.
"""Actual general edge reversal and cached depth-first cycle removal.

Native continuation frames retain the recursive visit/active/exit order without
adding a Python call-stack limit to valid native work graphs.
"""
from .graph import LPort,Vec2,set_port_owner,set_source,set_target
from .native_properties import CanonicalPropertyMap
from .ports import set_side
from .property_access import read_layered_scalar
from .self_loops_general import _is_self_loop
from ...execution.diagnostics import BasicProgressMonitor
from ...execution.node_micro import VectorChain


def _boolean(holder,key):
    value=holder.properties.get(key)
    if value is None:return False
    if type(value)is not bool:raise TypeError('An actual native Boolean property is required')
    return value


def _provide_collector_port(node,output):
    key='OUTPUT_COLLECT'if output else'INPUT_COLLECT'
    for port in node.ports:
        if _boolean(port,key):return port
    port=LPort(properties=CanonicalPropertyMap())
    port.properties[key]=True
    set_port_owner(port,node)
    set_side(port,'EAST'if output else'WEST')
    port.pos.x=node.size.x if output else 0.0
    port.pos.y=node.size.y/2
    return port


def reverse_edge(edge,adapt_ports=True):
    old_source=edge.source;old_target=edge.target
    set_source(edge,None)
    set_target(edge,None)
    if adapt_ports and _boolean(old_target,'INPUT_COLLECT'):
        set_source(edge,_provide_collector_port(old_target.owner,True))
    else:set_source(edge,old_target)
    if adapt_ports and _boolean(old_source,'OUTPUT_COLLECT'):
        set_target(edge,_provide_collector_port(old_source.owner,False))
    else:set_target(edge,old_source)
    for label in edge.labels:
        placement=read_layered_scalar(label,'EDGE_LABELS_PLACEMENT','EDGE_LABELS_PLACEMENT')
        if placement=='TAIL':label.properties['EDGE_LABELS_PLACEMENT']='HEAD'
        elif placement=='HEAD':label.properties['EDGE_LABELS_PLACEMENT']='TAIL'
    reversed_=_boolean(edge,'REVERSED')
    edge.properties['REVERSED']=not reversed_
    bends=VectorChain()
    for point in edge.bend_points:bends.insert(0,Vec2(point.x,point.y))
    edge.bend_points=bends


_CONFIGURATION=None


def _configuration():
    global _CONFIGURATION
    if _CONFIGURATION is None:
        from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy
        _CONFIGURATION=LayoutProcessorConfiguration()
        _CONFIGURATION.add_after(tuple(LayeredPhase)[4],IntermediateProcessorStrategy.REVERSED_EDGE_RESTORER)
    return _CONFIGURATION


def _outgoing(node):
    lists=[port.outgoing_edges for port in node.ports]
    return(edge for edges in lists for edge in edges)


class DepthFirstCycleBreaker:
    source_name='DepthFirstCycleBreaker'

    def __init__(self):
        _configuration()
        self.sources=None;self.visited=None;self.active=None;self.edges_to_be_reversed=None

    def get_layout_processor_configuration(self,graph):return _configuration()

    def _dfs(self,node):
        if self.visited[node.id]:return
        self.visited[node.id]=True
        self.active[node.id]=True
        frames=[(node,_outgoing(node))]
        while frames:
            current,edges=frames[-1]
            try:edge=next(edges)
            except StopIteration:
                self.active[current.id]=False
                frames.pop()
                continue
            if _is_self_loop(edge):continue
            target=edge.target.owner
            if self.active[target.id]:self.edges_to_be_reversed.append(edge)
            elif not self.visited[target.id]:
                self.visited[target.id]=True
                self.active[target.id]=True
                frames.append((target,_outgoing(target)))

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Depth-first cycle removal',1)
        nodes=graph.layerless_nodes;count=len(nodes)
        self.sources=[]
        self.visited=[False]*count
        self.active=[False]*count
        self.edges_to_be_reversed=[]
        for index,node in enumerate(nodes):
            node.id=index
            incoming=[port.incoming_edges for port in node.ports]
            if not any(incoming):self.sources.append(node)
        for source in self.sources:self._dfs(source)
        for index in range(count):
            if not self.visited[index]:self._dfs(nodes[index])
        for edge in self.edges_to_be_reversed:
            reverse_edge(edge,True)
            graph.properties['CYCLIC']=True
        self.sources=None
        self.visited=None
        self.active=None
        self.edges_to_be_reversed=None
        monitor.done()


# Remaining actual P1 strategies. The reviewed DepthFirst/reverse bodies above
# remain unchanged; all new variants share only the true graph operations.
from collections import deque
from .strategy_collections import NodeIdentities,NodeSet,outgoing,incoming
from .native_adapters import _stored_key,_has_property
from .integer_box_tokens import value_of_integer_box,holder_integer_box_identity
from .interactive_order import interactive_reference_point
from ..radial import _maximum
from ..triangulation import ValueMap
from ...execution.diagnostics import number_text


_CYCLE_CONFIGURATIONS={}
_DEFAULT_LOWLINK=value_of_integer_box(2147483647)


def _cycle_configuration(name,interactive=False):
    if name not in _CYCLE_CONFIGURATIONS:
        from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as Strategy
        cfg=LayoutProcessorConfiguration()
        if interactive:cfg.add_before(tuple(LayeredPhase)[0],Strategy.INTERACTIVE_EXTERNAL_PORT_POSITIONER)
        cfg.add_after(tuple(LayeredPhase)[4],Strategy.REVERSED_EDGE_RESTORER)
        _CYCLE_CONFIGURATIONS[name]=cfg
    return _CYCLE_CONFIGURATIONS[name]


def _bare(holder,name):
    key=_stored_key(holder,name)
    return None if key is None else holder.properties[key]


def _integer(holder,name,default=None):
    value=_bare(holder,name)
    if value is None:value=default
    if type(value)is not int:raise TypeError('An actual Integer '+name+' is required')
    return value


def _layered_integer(holder,name,symbol=None):
    value=read_layered_scalar(holder,name,symbol or name)
    if type(value)is not int:raise TypeError('An actual Integer '+name+' is required')
    return value


def _set_integer(holder,name,value):
    token=value_of_integer_box(value)
    setter=getattr(holder.properties,'set_property',None)
    if setter is not None:
        setter(name,value,integer_box=token)
        identities=getattr(holder,'integer_box_identities',None)
        if identities is None:holder.integer_box_identities=holder.properties.integer_boxes
        else:identities[name]=token
    else:
        holder.properties[name]=value
        identities=getattr(holder,'integer_box_identities',None)
        if identities is None:identities={};holder.integer_box_identities=identities
        identities[name]=token


def _integer_box(holder,name,default):
    if _bare(holder,name)is None:return default
    identities=getattr(holder.properties,'integer_boxes',None)
    if identities is not None and name in identities:return identities[name]
    return holder_integer_box_identity(holder,name,default)


def _group_enforced(graph):
    return read_layered_scalar(graph,'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CB_GROUP_ORDER_STRATEGY',
                               'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CB_GROUP_ORDER_STRATEGY_0')=='ENFORCED'


def _group_id(node):
    return _layered_integer(node,'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CYCLE_BREAKING_ID',
                             'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CYCLE_BREAKING_ID_0')


def _connected(node):
    lists=[edges for port in node.ports for edges in(port.incoming_edges,port.outgoing_edges)]
    return(edge for edges in lists for edge in edges)


class GroupModelOrderCalculator:
    def __init__(self):self.first_separate_nodes=0;self.last_separate_nodes=0

    def compute(self,node,offset,small_offset=None):
        value=0.0
        constraint=read_layered_scalar(node,'LAYERING_LAYER_CONSTRAINT','LAYERING_LAYER_CONSTRAINT_0')
        if constraint=='FIRST_SEPARATE':
            value=2*-offset+self.first_separate_nodes;self.first_separate_nodes+=1
        elif constraint=='FIRST':value=-offset
        elif constraint=='LAST':value=offset
        elif constraint=='LAST_SEPARATE':
            value=2*offset+self.last_separate_nodes;self.last_separate_nodes+=1
        if _has_property(node,'MODEL_ORDER'):
            if small_offset is None:value+=_integer(node,'MODEL_ORDER')
            else:value+=_group_id(node)*small_offset+_integer(node,'MODEL_ORDER')
        return value


class GreedyCycleBreaker:
    source_name='GreedyCycleBreaker'

    def __init__(self):
        _cycle_configuration('Greedy');self.sources=deque();self.sinks=deque()
        self.indegree=None;self.outdegree=None;self.mark=None;self.layered_graph=None;self.random=None

    def get_layout_processor_configuration(self,graph):return _cycle_configuration('Greedy')

    def choose_node_with_max_outflow(self,nodes):return nodes[self.random.next_int(len(nodes))]

    def _update_neighbors(self,node):
        for port in node.ports:
            for edge in list(port.incoming_edges)+list(port.outgoing_edges):
                connected=edge.target if edge.source is port else edge.source;endpoint=connected.owner
                if node is endpoint:continue
                priority=_layered_integer(edge,'PRIORITY_DIRECTION','PRIORITY_DIRECTION_0')
                if priority<0:priority=0
                index=endpoint.id
                if self.mark[index]==0:
                    if edge.target is connected:
                        self.indegree[index]-=priority+1
                        if self.indegree[index]<=0 and self.outdegree[index]>0:self.sources.append(endpoint)
                    else:
                        self.outdegree[index]-=priority+1
                        if self.outdegree[index]<=0 and self.indegree[index]>0:self.sinks.append(endpoint)

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Greedy cycle removal',1);self.layered_graph=graph;nodes=graph.layerless_nodes;remaining=len(nodes)
        self.indegree=[0.0]*remaining;self.outdegree=[0.0]*remaining;self.mark=[0]*remaining
        for index,node in enumerate(nodes):
            node.id=index
            for port in node.ports:
                for edge in port.incoming_edges:
                    if edge.source.owner is node:continue
                    priority=_layered_integer(edge,'PRIORITY_DIRECTION','PRIORITY_DIRECTION_0')
                    self.indegree[index]+=priority+1 if priority>0 else 1
                for edge in port.outgoing_edges:
                    if edge.target.owner is node:continue
                    priority=_layered_integer(edge,'PRIORITY_DIRECTION','PRIORITY_DIRECTION_0')
                    self.outdegree[index]+=priority+1 if priority>0 else 1
            if self.outdegree[index]==0:self.sinks.append(node)
            elif self.indegree[index]==0:self.sources.append(node)
        right=-1;left=1;candidates=[];self.random=graph.properties.get('RANDOM')
        while remaining>0:
            while self.sinks:
                node=self.sinks.popleft();self.mark[node.id]=right;right-=1;self._update_neighbors(node);remaining-=1
            while self.sources:
                node=self.sources.popleft();self.mark[node.id]=left;left+=1;self._update_neighbors(node);remaining-=1
            if remaining>0:
                maximum=-2147483648
                for node in nodes:
                    if self.mark[node.id]!=0:continue
                    outflow=self.outdegree[node.id]-self.indegree[node.id]
                    if outflow>=maximum:
                        if outflow>maximum:candidates.clear();maximum=outflow
                        candidates.append(node)
                node=self.choose_node_with_max_outflow(candidates);self.mark[node.id]=left;left+=1
                self._update_neighbors(node);remaining-=1
        shift=len(nodes)+1
        for index in range(len(nodes)):
            if self.mark[index]<0:self.mark[index]+=shift
        for node in nodes:
            for port in list(node.ports):
                for edge in list(port.outgoing_edges):
                    if self.mark[node.id]>self.mark[edge.target.owner.id]:
                        reverse_edge(edge,True);graph.properties['CYCLIC']=True
        self.indegree=None;self.outdegree=None;self.mark=None;self.sources.clear();self.sinks.clear();monitor.done()


class GreedyModelOrderCycleBreaker(GreedyCycleBreaker):
    source_name='GreedyModelOrderCycleBreaker'

    def choose_node_with_max_outflow(self,nodes):
        selected=None;minimum=2147483647
        offset=float(_maximum(len(self.layered_graph.layerless_nodes),_integer(self.layered_graph,'MAX_MODEL_ORDER_NODES')))
        big_offset=offset*_integer(self.layered_graph,'CB_NUM_MODEL_ORDER_GROUPS');calculator=GroupModelOrderCalculator()
        enforced=_group_enforced(self.layered_graph)
        for node in nodes:
            if _has_property(node,'MODEL_ORDER'):
                value=calculator.compute(node,big_offset,offset)if enforced else calculator.compute(node,offset)
                if minimum>value:minimum=value;selected=node
        return selected if selected is not None else super().choose_node_with_max_outflow(nodes)


class InteractiveCycleBreaker:
    source_name='InteractiveCycleBreaker'

    def __init__(self):_cycle_configuration('Interactive',True)

    def get_layout_processor_configuration(self,graph):return _cycle_configuration('Interactive',True)

    @staticmethod
    def _find_cycles(node,reversed_edges):
        node.id=-1;frames=[(node,outgoing(node))]
        while frames:
            current,edges=frames[-1]
            try:edge=next(edges)
            except StopIteration:current.id=0;frames.pop();continue
            target=edge.target.owner
            if target is current:continue
            if target.id<0:reversed_edges.append(edge)
            elif target.id>0:target.id=-1;frames.append((target,outgoing(target)))

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Interactive cycle breaking',1);reversed_edges=[]
        for source in graph.layerless_nodes:
            source.id=1;source_x=interactive_reference_point(source).x
            for edge in outgoing(source):
                target=edge.target.owner
                if target is not source and interactive_reference_point(target).x<source_x:reversed_edges.append(edge)
        for edge in reversed_edges:reverse_edge(edge,True)
        reversed_edges.clear()
        for node in graph.layerless_nodes:
            if node.id>0:self._find_cycles(node,reversed_edges)
        for edge in reversed_edges:reverse_edge(edge,True)
        reversed_edges.clear();monitor.done()


class ModelOrderCycleBreaker:
    source_name='ModelOrderCycleBreaker'

    def __init__(self):_cycle_configuration('ModelOrder')

    def get_layout_processor_configuration(self,graph):return _cycle_configuration('ModelOrder')

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Model order cycle breaking',1);reversed_edges=[]
        offset=float(_maximum(len(graph.layerless_nodes),_integer(graph,'MAX_MODEL_ORDER_NODES')))
        big_offset=offset*_integer(graph,'CB_NUM_MODEL_ORDER_GROUPS');enforced=_group_enforced(graph)
        for source in graph.layerless_nodes:
            calculator=GroupModelOrderCalculator()
            source_order=calculator.compute(source,big_offset,offset)if enforced else calculator.compute(source,offset)
            for edge in outgoing(source):
                target=edge.target.owner
                target_order=calculator.compute(target,big_offset,offset)if enforced else calculator.compute(target,offset)
                if target_order<source_order:reversed_edges.append(edge)
        for edge in reversed_edges:reverse_edge(edge,True);graph.properties['CYCLIC']=True
        reversed_edges.clear();monitor.done()


class _NodeOrderBase(NodeIdentities):
    def __init__(self):
        super().__init__();self.graph=None;self.sources=None;self.sinks=None;self.visited=None
        self.active=None;self.bfs_queue=None;self.edges_to_be_reversed=None

    def _group_edges(self,node,breadth=False):
        groups={};enforced=_group_enforced(self.graph)
        for edge in outgoing(node):
            target=edge.target.owner;present=_has_property(target,'MODEL_ORDER')if breadth else _bare(target,'MODEL_ORDER')is not None
            if present:
                if enforced:
                    maximum=_integer(self.graph,'MAX_MODEL_ORDER_NODES')
                    order=float(maximum)*_group_id(target)+_integer(target,'MODEL_ORDER')
                else:order=_integer(target,'MODEL_ORDER')
                if order in groups:groups[order].add(edge)
                else:groups[order]=NodeSet(self,[edge])
            else:groups[2147483647-len(groups)]=NodeSet(self,[edge])
        return[(key,groups[key])for key in sorted(groups)]

    def _reverse_all(self):
        for edge in self.edges_to_be_reversed:reverse_edge(edge,True);self.graph.properties['CYCLIC']=True


class BFSNodeOrderCycleBreaker(_NodeOrderBase):
    source_name='BFSNodeOrderCycleBreaker'

    def __init__(self):super().__init__();_cycle_configuration('BFSNodeOrder')

    def get_layout_processor_configuration(self,graph):return _cycle_configuration('BFSNodeOrder')

    def _bfs(self,node):
        if self.visited[node.id]:return
        self.visited[node.id]=True
        for _,edges in self._group_edges(node,True):
            edge=edges.values()[0]
            if _is_self_loop(edge):continue
            target=edge.target.owner
            if self.visited[target.id]and not self.sources.contains(node)and not self.sinks.contains(target):
                self.edges_to_be_reversed.extend(edges.values())
            else:self.bfs_queue.append(target)

    def _loop(self):
        while self.bfs_queue:self._bfs(self.bfs_queue.popleft())

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Breadth-first cycle removal',1);self.graph=graph;self._identity_graph=graph
        nodes=graph.layerless_nodes;self.bfs_queue=deque();self.sources=NodeSet(self);self.sinks=NodeSet(self)
        self.visited=[False]*len(nodes);self.edges_to_be_reversed=[]
        for index,node in enumerate(nodes):
            node.id=index
            if not any(port.incoming_edges for port in node.ports):self.sources.add(node)
            if not any(port.outgoing_edges for port in node.ports):self.sinks.add(node)
        for source in self.sources.values():self.bfs_queue.append(source);self._loop()
        self._loop();changed=True
        while changed:
            changed=False
            for index,node in enumerate(nodes):
                if not self.visited[index]:self.bfs_queue.append(node);changed=True;break
            self._loop()
        self._reverse_all();self.sources=None;self.visited=None;self.bfs_queue=None;self.edges_to_be_reversed=None;monitor.done()


class DFSNodeOrderCycleBreaker(_NodeOrderBase):
    source_name='DFSNodeOrderCycleBreaker'

    def __init__(self):super().__init__();_cycle_configuration('DFSNodeOrder')

    def get_layout_processor_configuration(self,graph):return _cycle_configuration('DFSNodeOrder')

    def _visit(self,node):
        if self.visited[node.id]:return
        self.visited[node.id]=True;self.active[node.id]=True
        frames=[(node,iter(self._group_edges(node)))]
        while frames:
            current,groups=frames[-1]
            try:_,edges=next(groups)
            except StopIteration:self.active[current.id]=False;frames.pop();continue
            edge=edges.values()[0]
            if _is_self_loop(edge):continue
            target=edge.target.owner
            if self.active[target.id]:self.edges_to_be_reversed.extend(edges.values())
            elif not self.visited[target.id]:
                self.visited[target.id]=True;self.active[target.id]=True
                frames.append((target,iter(self._group_edges(target))))

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Depth-first cycle removal',1);self.graph=graph;self._identity_graph=graph
        nodes=graph.layerless_nodes;self.sources=[];self.visited=[False]*len(nodes);self.active=[False]*len(nodes);self.edges_to_be_reversed=[]
        for index,node in enumerate(nodes):
            node.id=index
            if not any(port.incoming_edges for port in node.ports):self.sources.append(node)
        for source in self.sources:self._visit(source)
        for index,node in enumerate(nodes):
            if not self.visited[index]:self._visit(node)
        self._reverse_all();self.sources=None;self.visited=None;self.active=None;self.edges_to_be_reversed=None;monitor.done()


class _Tarjan:
    """Actual33816-33898 mutable-property Tarjan with explicit continuations."""
    def __init__(self,owner,reversed_edges,components,node_to_scc):
        self.owner=owner;self.reversed_edges=reversed_edges;self.components=components
        self.node_to_scc=node_to_scc;self.stack=[];self.index=0

    def reset(self,graph):
        for node in graph.layerless_nodes:
            node.properties['TARJAN_ON_STACK']=False
            _set_integer(node,'TARJAN_LOWLINK',-1);_set_integer(node,'TARJAN_ID',-1)
            self.stack.clear()
            for edge in _connected(node):edge.properties['IS_PART_OF_CYCLE']=False

    def _enter(self,node,frames):
        _set_integer(node,'TARJAN_ID',self.index)
        _set_integer(node,'TARJAN_LOWLINK',self.index)
        self.index+=1;self.stack.append(node);node.properties['TARJAN_ON_STACK']=True
        frames.append([node,_connected(node),None])

    def _strongly_connected(self,node):
        frames=[];self._enter(node,frames)
        while frames:
            current,edges,pending=frames[-1]
            if pending is not None:
                _set_integer(current,'TARJAN_LOWLINK',min(_integer(current,'TARJAN_LOWLINK',2147483647),
                                                        _integer(pending,'TARJAN_LOWLINK',2147483647)))
                frames[-1][2]=None
            try:edge=next(edges)
            except StopIteration:
                # Source uses boxed object identity, including the >=128
                # fresh-valueOf behavior; numeric equality is not equivalent.
                if (_integer_box(current,'TARJAN_LOWLINK',_DEFAULT_LOWLINK)
                        is _integer_box(current,'TARJAN_ID',value_of_integer_box(-1))):
                    component=NodeSet(self.owner)
                    while True:
                        popped=self.stack.pop();popped.properties['TARJAN_ON_STACK']=False;component.add(popped)
                        if popped is current:break
                    if len(component)>1:
                        index=len(self.components);self.components.append(component)
                        for member in component.values():self.node_to_scc.put(member,value_of_integer_box(index))
                frames.pop();continue
            reversed_=any(old is edge for old in self.reversed_edges)
            if edge.source.owner is not current and not reversed_:continue
            if edge.source.owner is current and reversed_:continue
            target=edge.source.owner if edge.target.owner is current else edge.target.owner
            if _integer(target,'TARJAN_ID',-1)==-1:
                frames[-1][2]=target;self._enter(target,frames)
            elif _boolean(target,'TARJAN_ON_STACK'):
                _set_integer(current,'TARJAN_LOWLINK',min(_integer(current,'TARJAN_LOWLINK',2147483647),
                                                        _integer(target,'TARJAN_ID',-1)))

    def run(self,graph):
        self.index=0;self.stack=[]
        for node in graph.layerless_nodes:
            if _integer(node,'TARJAN_ID',-1)==-1:self._strongly_connected(node);self.stack.clear()


class SCCModelOrderCycleBreaker(NodeIdentities):
    source_name='SCCModelOrderCycleBreaker'

    def __init__(self):
        super().__init__();_cycle_configuration('SCC')
        self.graph=None;self.strongly_connected_components=[];self.reversed_edges=[]
        self.node_to_scc=ValueMap(lambda node:0 if node is None else self.identity_hash(node),lambda a,b:a is b)

    def get_layout_processor_configuration(self,graph):return _cycle_configuration('SCC')

    def find_nodes(self,offset,big_offset):
        for component in self.strongly_connected_components:
            selected=None;calculator=GroupModelOrderCalculator();maximum=-2147483648
            for node in component.values():
                enforced=_group_enforced(self.graph)
                value=calculator.compute(node,big_offset,offset)if enforced else calculator.compute(node,offset)
                if selected is None or maximum<value:selected=node;maximum=value
            for edge in outgoing(selected):
                if component.contains(edge.target.owner):self.reversed_edges.append(edge)

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Model order cycle breaking',1);self.graph=graph;self._identity_graph=graph;self.reversed_edges=[]
        offset=float(_maximum(len(graph.layerless_nodes),_integer(graph,'MAX_MODEL_ORDER_NODES')))
        while True:
            tarjan=_Tarjan(self,self.reversed_edges,self.strongly_connected_components,self.node_to_scc)
            tarjan.reset(graph);tarjan.run(graph)
            if not self.strongly_connected_components:break
            self.find_nodes(offset,offset*_integer(graph,'CB_NUM_MODEL_ORDER_GROUPS'))
            for edge in self.reversed_edges:
                reverse_edge(edge,False)
                source=edge.source.owner
                _set_integer(source,'LAYERING_LAYER_ID',_layered_integer(source,'LAYERING_LAYER_ID','LAYERING_LAYER_ID_0')+1)
                graph.properties['CYCLIC']=True
            self.strongly_connected_components.clear();self.node_to_scc.buckets.clear();self.node_to_scc.count=0;self.reversed_edges.clear()
        monitor.done();monitor.log('Execution Time: '+number_text(monitor.total_time))

    def _extreme_nodes(self,component,offset,big_offset):
        minimum=None;maximum=None;minimum_order=2147483647;maximum_order=-2147483648
        enforced=_group_enforced(self.graph);calculator=GroupModelOrderCalculator()
        for node in component.values():
            value=calculator.compute(node,big_offset,offset)if enforced else calculator.compute(node,offset)
            if minimum is None or maximum is None:
                minimum=node;minimum_order=value;maximum=node;maximum_order=value
            else:
                if minimum_order>value:minimum=node;minimum_order=value
                if maximum_order<value:maximum=node;maximum_order=value
        return minimum,maximum


class SCConnectivity(SCCModelOrderCycleBreaker):
    source_name='SCConnectivity'

    def find_nodes(self,offset,big_offset):
        for component in self.strongly_connected_components:
            if len(component)<=1:continue
            minimum,maximum=self._extreme_nodes(component,offset,big_offset)
            if sum(1 for _ in incoming(minimum))>sum(1 for _ in outgoing(maximum)):
                for edge in incoming(minimum):
                    if component.contains(edge.source.owner):self.reversed_edges.append(edge)
            else:
                for edge in outgoing(maximum):
                    if component.contains(edge.target.owner):self.reversed_edges.append(edge)


class SCCNodeTypeCycleBreaker(SCCModelOrderCycleBreaker):
    source_name='SCCNodeTypeCycleBreaker'

    def find_nodes(self,offset,big_offset):
        for component in self.strongly_connected_components:
            if len(component)<=1:continue
            minimum,maximum=self._extreme_nodes(component,offset,big_offset)
            group_default=value_of_integer_box(0)
            minimum_group=_integer_box(minimum,'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CYCLE_BREAKING_ID',group_default)
            preferred_source=_integer_box(self.graph,'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CB_PREFERRED_SOURCE_ID',None)
            if minimum_group is preferred_source:
                for edge in incoming(minimum):
                    if component.contains(edge.source.owner):self.reversed_edges.append(edge)
            elif (_integer_box(maximum,'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CYCLE_BREAKING_ID',group_default)
                    is _integer_box(self.graph,'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CB_PREFERRED_TARGET_ID',None)):
                for edge in outgoing(maximum):
                    # Literal source50870 tests the source owner here.
                    if component.contains(edge.source.owner):self.reversed_edges.append(edge)
            elif sum(1 for _ in incoming(minimum))>sum(1 for _ in outgoing(maximum)):
                for edge in incoming(minimum):
                    if component.contains(edge.source.owner):self.reversed_edges.append(edge)
            else:
                for edge in outgoing(maximum):
                    if component.contains(edge.target.owner):self.reversed_edges.append(edge)
