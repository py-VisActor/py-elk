# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# Source: HOST14 Root SL03 and V SL01/02/04-07/12-14 source approvals.
"""Source-general native self-loop data and independently reviewed leaves.

The historical bounded loops module is read-only. Four processor integration,
port restoration and routing are separate source blocks, not no-op fallbacks.
"""
from collections import deque
from collections.abc import Mapping
import math

from .graph import Vec2,set_source,set_target,set_port_owner
from ...execution.diagnostics import BasicProgressMonitor
from ...execution.enum_identity import PORT_SIDE_DOMAIN,PORT_SIDE_ORDER,enum_identity_hash
from ...execution.enum_collections import EnumKeyMap
from .cell_layout import _maximum
from .property_access import read_layered_scalar
from .native_adapters import _read_property,_has_property,_stored_key
from .brandes_koepf_general import _LinkedIdentityMap
from .ports import _source_sort,set_side
from ..radial import IdentitySet
from ..disco import _IdentityMap
from .orthogonal_general import _Segment,_dependency,_break_cycles
from .port_label_placement import _minimum
from .spline_math import NubSpline

_SIDES=('UNDEFINED','NORTH','EAST','SOUTH','WEST')
_AREA_DOMAIN='org.eclipse.elk.alg.layered.intermediate.loops.ordering.PortRestorer$PortSideArea'
_AREAS=('START','MIDDLE','END')
_TYPE_DOMAIN='org.eclipse.elk.alg.layered.intermediate.loops.SelfLoopType'
_TYPES=('ONE_SIDE','TWO_SIDES_CORNER','TWO_SIDES_OPPOSING','THREE_SIDES','FOUR_SIDES')


class _EnumLists:
    """Narrow stable-key ArrayListMultimap caller, no runtime facade."""
    def __init__(self,domain,order):self.map=EnumKeyMap(domain,order)
    def append(self,key,value):
        values=self.map.get(key)
        if values is None:values=[value];self.map.put(key,values)
        else:values.append(value)
    def __getitem__(self,key):
        value=self.map.get(key)
        return []if value is None else value
    def __contains__(self,key):return self.map.get(key)is not None
    def __iter__(self):return iter(self.map.keys())
    def __len__(self):return len(self.map.keys())


class _TargetAreas:
    def __init__(self):
        # Source ArrayTable first indexes every row, then every column. Those
        # shared enum hash requests cannot vanish behind fixed tuple indexes.
        for side in _SIDES:enum_identity_hash(PORT_SIDE_DOMAIN,side)
        for area in _AREAS:enum_identity_hash(_AREA_DOMAIN,area)
        self.cells=[[None for area in _AREAS]for side in _SIDES]
        for side in _SIDES:
            for area in _AREAS:self.put(side,area,[])
    def _index(self,side,area):
        enum_identity_hash(PORT_SIDE_DOMAIN,side);enum_identity_hash(_AREA_DOMAIN,area)
        return _SIDES.index(side),_AREAS.index(area)
    def put(self,side,area,value):
        row,column=self._index(side,area);self.cells[row][column]=value
    def get(self,side,area):
        row,column=self._index(side,area);return self.cells[row][column]
    def values(self):return [value for row in self.cells for value in row]


def _graph(node):
    if node.graph is None and node.layer is not None:return node.layer.graph
    return node.graph


def _is_self_loop(edge):
    if edge.source is None or edge.target is None:return False
    return edge.source.owner is not None and edge.source.owner is edge.target.owner


def _outgoing_edges(node):
    # Capture the actual adjacency-list objects before walking their contents.
    return (edge for edges in [port.outgoing_edges for port in node.ports]for edge in edges)


def _incoming_edges(node):
    return (edge for edges in [port.incoming_edges for port in node.ports]for edge in edges)


def needs_self_loop_processing(node):
    return node.type=='NORMAL'and any(_is_self_loop(edge)for edge in _outgoing_edges(node))


def _label_spacing(node):
    result=None
    if _has_property(node,'SPACING_INDIVIDUAL'):
        individual=_read_property(node,'SPACING_INDIVIDUAL')
        if not isinstance(individual,Mapping):raise TypeError('An actual individual spacing holder is required')
        key='org.eclipse.elk.spacing.labelLabel'
        if key in individual:result=individual[key]
    graph=_graph(node)
    if result is None and graph is not None:
        result=read_layered_scalar(graph,'SPACING_LABEL_LABEL','SPACING_LABEL_LABEL')
    return result


class SelfLoopEdge:
    def __init__(self,l_edge,sl_source,sl_target):
        self.l_edge=l_edge;self.sl_source=sl_source;self.sl_target=sl_target
        self.sl_hyper_loop=None
        sl_source.outgoing_sl_edges.append(self)
        sl_target.incoming_sl_edges.append(self)
    def is_inline(self):
        return any(read_layered_scalar(label,'EDGE_LABELS_INLINE','EDGE_LABELS_INLINE_0')
                   for label in self.l_edge.labels)


class SelfLoopPort:
    def __init__(self,l_port):
        self.incoming_sl_edges=[];self.outgoing_sl_edges=[];self.l_port=l_port
        self.had_only_self_loops=all(_is_self_loop(edge)for edge in
                                    (*l_port.incoming_edges,*l_port.outgoing_edges))
        self.is_hidden=False
    def get_sl_net_flow(self):return len(self.incoming_sl_edges)-len(self.outgoing_sl_edges)


class SelfHyperLoopLabels:
    def __init__(self,sl_loop):
        self.l_labels=[];self.size=Vec2();self.position=Vec2();self.id=0
        node=sl_loop.sl_holder.l_node;graph=_graph(node)
        if graph is None:raise TypeError('The actual self-loop label graph is null')
        self.layout_direction=read_layered_scalar(graph,'DIRECTION','DIRECTION')
        self.label_label_spacing=_label_spacing(node)
        if self.label_label_spacing is None:raise TypeError('The actual label spacing is null')
        self.alignment=None;self.side=None
    def add_labels(self,labels):
        for label in labels:
            self.l_labels.append(label);self._update_size(label)
    def _update_size(self,label):
        if self.layout_direction in('LEFT','RIGHT'):
            self.size.x=_maximum(self.size.x,label.size.x)
            self.size.y+=label.size.y
            if len(self.l_labels)>1:self.size.y+=self.label_label_spacing
        else:
            self.size.x+=label.size.x
            self.size.y=_maximum(self.size.y,label.size.y)
            if len(self.l_labels)>1:self.size.x+=self.label_label_spacing
    def apply_placement(self,offset):
        x=self.position.x;y=self.position.y
        if self.layout_direction in('LEFT','RIGHT'):
            for label in self.l_labels:
                if self.alignment=='LEFT'or self.side=='EAST':label.pos.x=x
                elif self.alignment=='RIGHT'or self.side=='WEST':label.pos.x=x+self.size.x-label.size.x
                else:label.pos.x=x+(self.size.x-label.size.x)/2
                label.pos.y=y;label.pos.x+=offset.x;label.pos.y+=offset.y
                y+=label.size.y+self.label_label_spacing
        else:
            for label in self.l_labels:
                label.pos.x=x
                label.pos.y=y+self.size.y-label.size.y if self.side=='NORTH'else y
                label.pos.x+=offset.x;label.pos.y+=offset.y
                x+=label.size.x+self.label_label_spacing


def _loop_type(sides):
    if 'UNDEFINED'in sides:raise ValueError('Port sides must not contain UNDEFINED')
    count=len(sides)
    if count==1:return 'ONE_SIDE'
    if count==2:
        return 'TWO_SIDES_OPPOSING'if('EAST'in sides and'WEST'in sides or
                                     'NORTH'in sides and'SOUTH'in sides)else'TWO_SIDES_CORNER'
    if count==3:return 'THREE_SIDES'
    if count==4:return 'FOUR_SIDES'
    return None


class SelfHyperLoop:
    def __init__(self,sl_holder):
        self.sl_ports=[];self.sl_edges=IdentitySet(_graph(sl_holder.l_node))
        self.occupied_port_sides=set();self.routing_slot=[0]*5
        self.sl_holder=sl_holder;self.leftmost_port=None;self.rightmost_port=None
        self.sl_labels=None;self.sl_ports_by_side=None;self.self_loop_type=None
    def add_edge(self,edge):
        if self.sl_edges.contains(edge):return
        self.sl_edges.add(edge);edge.sl_hyper_loop=self
        if not any(old is edge.sl_source for old in self.sl_ports):self.sl_ports.append(edge.sl_source)
        if not any(old is edge.sl_target for old in self.sl_ports):self.sl_ports.append(edge.sl_target)
        if edge.l_edge.labels:
            if self.sl_labels is None:self.sl_labels=SelfHyperLoopLabels(self)
            self.sl_labels.add_labels(edge.l_edge.labels)
    def compute_ports_per_side(self):
        # Only per-key ordered lists and key membership/count are consumed in
        # this approved leaf. A future key-set iterator has its own caller.
        self.sl_ports_by_side=_EnumLists(PORT_SIDE_DOMAIN,PORT_SIDE_ORDER)
        for port in self.sl_ports:self.sl_ports_by_side.append(port.l_port.side,port)
        self.self_loop_type=_loop_type(self.sl_ports_by_side)
    def set_routing_slot(self,side,slot):
        index=_SIDES.index(side);self.routing_slot[index]=slot
        self.sl_holder.routing_slot_count[index]=_maximum(self.sl_holder.routing_slot_count[index],slot+1)


class SelfLoopHolder:
    def __init__(self,node):
        self.sl_hyper_loops=[];self.sl_ports=_LinkedIdentityMap(_graph(node))
        self.routing_slot_count=[0]*5;self.l_node=node;self.are_ports_hidden=False
    def port_for(self,port):
        # LinkedHashMap contains -> conditional put -> get, including real
        # shared allocator requests even for a previously mapped native port.
        if self.sl_ports.get(port)is None:self.sl_ports.put(port,SelfLoopPort(port))
        return self.sl_ports.get(port)
    def initialize(self):
        sl_edges=[]
        for edge in _outgoing_edges(self.l_node):
            if _is_self_loop(edge):
                sl_edges.append(SelfLoopEdge(edge,self.port_for(edge.source),self.port_for(edge.target)))
        for _,port in self.sl_ports.items():port.l_port.id=0
        for _,port in self.sl_ports.items():
            if port.l_port.id==0:self.sl_hyper_loops.append(self._initialize_hyper_loop(port))
    def _initialize_hyper_loop(self,port):
        loop=SelfHyperLoop(self);queue=deque([port])
        while queue:
            current=queue.popleft();current.l_port.id=1
            for edge in current.outgoing_sl_edges:
                loop.add_edge(edge)
                if edge.sl_target.l_port.id==0:queue.append(edge.sl_target)
            for edge in current.incoming_sl_edges:
                loop.add_edge(edge)
                if edge.sl_source.l_port.id==0:queue.append(edge.sl_source)
        return loop


def self_loop_postprocessor(graph,*,monitor=None):
    """Actual source post phase: restore all edges before applying labels."""
    monitor=BasicProgressMonitor(False,False)if monitor is None else monitor
    monitor.begin('Self-Loop post-processing',1)
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type!='NORMAL'or not _has_property(node,'SELF_LOOP_HOLDER'):continue
            holder=_read_property(node,'SELF_LOOP_HOLDER')
            for loop in holder.sl_hyper_loops:
                for edge in loop.sl_edges.values():
                    native=edge.l_edge
                    set_source(native,edge.sl_source.l_port)
                    set_target(native,edge.sl_target.l_port)
                    for point in native.bend_points:
                        point.x+=node.pos.x;point.y+=node.pos.y
            for loop in holder.sl_hyper_loops:
                if loop.sl_labels is not None:loop.sl_labels.apply_placement(node.pos)
    monitor.done()


def assign_port_sides(holder):
    """Actual three distribution strategies; only hidden ports change side."""
    strategy=read_layered_scalar(holder.l_node,'EDGE_ROUTING_SELF_LOOP_DISTRIBUTION',
                                'EDGE_ROUTING_SELF_LOOP_DISTRIBUTION_0')
    if strategy=='NORTH':
        for loop in holder.sl_hyper_loops:
            for port in loop.sl_ports:
                if port.is_hidden:set_side(port.l_port,'NORTH')
    elif strategy=='NORTH_SOUTH':
        north=south=0
        for loop in holder.sl_hyper_loops:
            hidden=[port for port in loop.sl_ports if port.is_hidden]
            if north<=south:side='NORTH';north+=len(hidden)
            else:side='SOUTH';south+=len(hidden)
            for port in hidden:set_side(port.l_port,side)
    elif strategy=='EQUALLY':
        loops=list(holder.sl_hyper_loops)
        def compare(first,second):
            a=len(second.sl_ports);b=len(first.sl_ports)
            return -1 if a<b else 0 if a==b else 1
        _source_sort(loops,compare)
        targets=(('NORTH','NORTH'),('SOUTH','SOUTH'),('EAST','EAST'),('WEST','WEST'),
                 ('WEST','NORTH'),('NORTH','EAST'),('SOUTH','WEST'),('EAST','SOUTH'))
        for index,loop in enumerate(loops):_assign_to_target(loop,*targets[index%len(targets)])


def _assign_to_target(loop,first,second):
    if first!=second:
        def compare(left,right):
            a=len(left.l_port.incoming_edges)-len(left.l_port.outgoing_edges)
            b=len(right.l_port.incoming_edges)-len(right.l_port.outgoing_edges)
            return -1 if a<b else 0 if a==b else 1
        _source_sort(loop.sl_ports,compare)
    split=len(loop.sl_ports)//2
    for port in loop.sl_ports[:split]:
        if port.is_hidden:set_side(port.l_port,first)
    for port in loop.sl_ports[split:]:
        if port.is_hidden:set_side(port.l_port,second)


def _hide_ports(holder):
    node=holder.l_node;nested=getattr(node,'nested_graph',None)
    order_fixed=_read_property(node,'PORT_CONSTRAINTS')in('FIXED_ORDER','FIXED_RATIO','FIXED_POS')
    # Preserve both source reads before the OR, even with fixed order true.
    hierarchy_mode=(nested is not None and'EXTERNAL_PORTS'in _read_property(nested,'GRAPH_PROPERTIES'))
    if order_fixed or hierarchy_mode:return
    for _,port in holder.sl_ports.items():
        if port.had_only_self_loops:
            set_port_owner(port.l_port,None);port.is_hidden=True;holder.are_ports_hidden=True


def self_loop_preprocessor(graph,*,monitor=None):
    monitor=BasicProgressMonitor(False,False)if monitor is None else monitor
    monitor.begin('Self-Loop pre-processing',1)
    for node in graph.layerless_nodes:
        if needs_self_loop_processing(node):
            holder=SelfLoopHolder(node)
            node.properties['SELF_LOOP_HOLDER']=holder
            holder.initialize()
            for loop in holder.sl_hyper_loops:
                for edge in loop.sl_edges.values():
                    set_source(edge.l_edge,None);set_target(edge.l_edge,None)
            _hide_ports(holder)
    monitor.done()


def _sorted_two_side_port_sides(loop):
    sides=list(loop.sl_ports_by_side)
    _source_sort(sides,lambda first,second:_SIDES.index(first)-_SIDES.index(second))
    if sides[0]=='NORTH'and sides[1]=='WEST':sides[0],sides[1]='WEST','NORTH'
    return sides


def _extreme_port(ports,maximum):
    iterator=iter(ports)
    try:result=next(iterator)
    except StopIteration:raise ValueError('No value present')from None
    for port in iterator:
        comparison=result.l_port.id-port.l_port.id
        # Literal BinaryOperator ties: min retains first, max selects later.
        if (comparison<=0 if maximum else comparison>0):result=port
    return result


class RoutingDirector:
    def __init__(self):self.port_penalties=None
    def _compute_penalties(self,holder):
        self.port_penalties=[];total=0
        for port in holder.l_node.ports:
            total+=1 if not port.incoming_edges and not port.outgoing_edges else 3
            self.port_penalties.append(total)
    def _edge_penalty(self,holder,left,right):
        if self.port_penalties is None:self._compute_penalties(holder)
        count=len(holder.l_node.ports);left_id=left.l_port.id;before=right.l_port.id-1
        if before<0:before=count-1
        if left_id<=before:return self.port_penalties[before]-self.port_penalties[left_id]
        return self.port_penalties[count-1]-self.port_penalties[left_id]+self.port_penalties[before]
    def _opposing(self,loop):
        sides=_sorted_two_side_port_sides(loop);holder=loop.sl_holder
        first_left=_extreme_port(loop.sl_ports_by_side[sides[0]],False)
        first_right=_extreme_port(loop.sl_ports_by_side[sides[1]],True)
        first_penalty=self._edge_penalty(holder,first_left,first_right)
        second_left=_extreme_port(loop.sl_ports_by_side[sides[1]],False)
        second_right=_extreme_port(loop.sl_ports_by_side[sides[0]],True)
        second_penalty=self._edge_penalty(holder,second_left,second_right)
        if first_penalty<=second_penalty:loop.leftmost_port=first_left;loop.rightmost_port=first_right
        else:loop.leftmost_port=second_left;loop.rightmost_port=second_right
    def _four_sides(self,loop):
        ports=loop.sl_ports;holder=loop.sl_holder;worst_left=ports[-1];worst_right=ports[0]
        worst=self._edge_penalty(holder,worst_left,worst_right)
        for index in range(1,len(ports)):
            current_left=ports[index-1];current_right=ports[index]
            penalty=self._edge_penalty(holder,current_left,current_right)
            if penalty>worst:worst_left=current_left;worst_right=current_right;worst=penalty
        loop.leftmost_port=worst_right;loop.rightmost_port=worst_left
    @staticmethod
    def _three_sides(loop):
        missing=next((side for side in _SIDES[1:]if side not in loop.sl_ports_by_side),None)
        left,right={'NORTH':('EAST','WEST'),'EAST':('SOUTH','NORTH'),
                    'SOUTH':('WEST','EAST'),'WEST':('NORTH','SOUTH')}[missing]
        loop.leftmost_port=_extreme_port(loop.sl_ports_by_side[left],False)
        loop.rightmost_port=_extreme_port(loop.sl_ports_by_side[right],True)
    def determine_routes(self,holder):
        for index,port in enumerate(holder.l_node.ports):port.id=index
        for loop in holder.sl_hyper_loops:
            _source_sort(loop.sl_ports,lambda first,second:
                         -1 if first.l_port.id<second.l_port.id else 0 if first.l_port.id==second.l_port.id else 1)
        for loop in holder.sl_hyper_loops:
            kind=loop.self_loop_type
            if kind=='ONE_SIDE':
                side=loop.sl_ports[0].l_port.side
                loop.leftmost_port=_extreme_port(loop.sl_ports_by_side[side],False)
                loop.rightmost_port=_extreme_port(loop.sl_ports_by_side[side],True)
            elif kind=='TWO_SIDES_CORNER':
                sides=_sorted_two_side_port_sides(loop)
                loop.leftmost_port=_extreme_port(loop.sl_ports_by_side[sides[0]],False)
                loop.rightmost_port=_extreme_port(loop.sl_ports_by_side[sides[1]],True)
            elif kind=='TWO_SIDES_OPPOSING':self._opposing(loop)
            elif kind=='THREE_SIDES':self._three_sides(loop)
            elif kind=='FOUR_SIDES':self._four_sides(loop)
            else:raise TypeError('The actual self-loop type is null or invalid')
            current=loop.leftmost_port.l_port.side;target=loop.rightmost_port.l_port.side
            right={'NORTH':'EAST','EAST':'SOUTH','SOUTH':'WEST','WEST':'NORTH'}
            while current!=target:
                loop.occupied_port_sides.add(current);current=right.get(current,'UNDEFINED')
            loop.occupied_port_sides.add(current)
        self.port_penalties=None


def _north_south_connection_sides(port):
    sides=set();dummy=_read_property(port,'PORT_DUMMY')
    if dummy is not None:
        for candidate in dummy.ports:
            if (candidate.properties.get('ORIGIN')is port and
                    (candidate.incoming_edges or candidate.outgoing_edges)):
                sides.add(candidate.side)
    return sides


def _north_prefix(port):
    if port.side!='NORTH':return False
    sides=_north_south_connection_sides(port);east='EAST'in sides;west='WEST'in sides
    return west or west and east


def _south_prefix(port):
    return port.side=='SOUTH'and'EAST'in _north_south_connection_sides(port)


def _port_split_index(ports):
    positive=0
    while positive<len(ports):
        if ports[positive].get_sl_net_flow()>0:break
        positive+=1
    if positive>0 and positive<len(ports)-1:return positive
    nonnegative=0
    while nonnegative<len(ports):
        if ports[nonnegative].get_sl_net_flow()>0:break
        nonnegative+=1
    if nonnegative>0 and positive<len(ports)-1:return nonnegative
    return len(ports)//2


class PortRestorer:
    def __init__(self):self.target_areas=None;self.sl_loops_by_type=None
    def _add(self,ports,side,area,prepend):
        hidden=[port for port in ports if port.is_hidden];hidden.reverse()
        target=self.target_areas.get(side,area)
        if prepend:target[0:0]=hidden
        else:target.extend(hidden)
    def _side_add(self,loop,side,area,prepend):self._add(loop.sl_ports_by_side[side],side,area,prepend)
    def _one_side(self,ordering):
        loops=self.sl_loops_by_type['ONE_SIDE']
        if ordering=='REVERSE_STACKED':loops.reverse()
        for loop in loops:
            side=loop.sl_ports[0].l_port.side;ports=list(loop.sl_ports)
            _source_sort(ports,lambda first,second:
                         -1 if first.get_sl_net_flow()<second.get_sl_net_flow()else
                         0 if first.get_sl_net_flow()==second.get_sl_net_flow()else 1)
            if ordering=='SEQUENCED':self._add(ports,side,'MIDDLE',False)
            elif ordering in('STACKED','REVERSE_STACKED'):
                split=_port_split_index(ports)
                self._add(ports[:split],side,'MIDDLE',True)
                self._add(ports[split:],side,'MIDDLE',False)
    def _restore(self,holder):
        node=holder.l_node;old=list(node.ports);index=0;target=node.ports;target.clear()
        def add(side,area):
            for port in self.target_areas.get(side,area):set_port_owner(port.l_port,node)
        def prefix(predicate):
            nonlocal index
            while index<len(old):
                if not predicate(old[index]):return
                target.append(old[index]);index+=1
        add('NORTH','START');prefix(_north_prefix);add('NORTH','MIDDLE')
        prefix(lambda p:p.side=='NORTH');add('NORTH','END')
        add('EAST','START');add('EAST','MIDDLE');prefix(lambda p:p.side=='EAST');add('EAST','END')
        add('SOUTH','START');prefix(_south_prefix);add('SOUTH','MIDDLE')
        prefix(lambda p:p.side=='SOUTH');add('SOUTH','END')
        add('WEST','START');prefix(lambda p:p.side=='WEST');add('WEST','MIDDLE');add('WEST','END')
    def restore_ports(self,holder):
        self.target_areas=_TargetAreas();self.sl_loops_by_type=_EnumLists(_TYPE_DOMAIN,_TYPES)
        for loop in holder.sl_hyper_loops:self.sl_loops_by_type.append(loop.self_loop_type,loop)
        ordering=read_layered_scalar(holder.l_node,'EDGE_ROUTING_SELF_LOOP_ORDERING',
                                    'EDGE_ROUTING_SELF_LOOP_ORDERING_0')
        self._one_side(ordering)
        for loop in self.sl_loops_by_type['TWO_SIDES_CORNER']:
            sides=_sorted_two_side_port_sides(loop)
            self._side_add(loop,sides[0],'END',True);self._side_add(loop,sides[1],'START',False)
        for loop in self.sl_loops_by_type['THREE_SIDES']:
            keys=loop.sl_ports_by_side
            if 'NORTH'in keys:
                if 'EAST'in keys:
                    if 'SOUTH'in keys:sides=None if'WEST'in keys else('NORTH','EAST','SOUTH')
                    else:sides=('WEST','NORTH','EAST')
                else:sides=('SOUTH','WEST','NORTH')
            else:sides=('EAST','SOUTH','WEST')
            self._side_add(loop,sides[0],'END',True);self._side_add(loop,sides[1],'MIDDLE',False)
            self._side_add(loop,sides[2],'START',False)
        for loop in self.sl_loops_by_type['FOUR_SIDES']:
            for side in loop.sl_ports_by_side:self._side_add(loop,side,'MIDDLE',False)
        for loop in self.sl_loops_by_type['TWO_SIDES_OPPOSING']:
            sides=_sorted_two_side_port_sides(loop)
            self._side_add(loop,sides[0],'END',True);self._side_add(loop,sides[1],'START',False)
        self._restore(holder)
        for ports in self.target_areas.values():
            for port in ports:port.is_hidden=False
        holder.are_ports_hidden=False;self.sl_loops_by_type=None


def self_loop_port_restorer(graph,*,monitor=None):
    monitor=BasicProgressMonitor(False,False)if monitor is None else monitor
    monitor.begin('Self-Loop ordering',1);restorer=PortRestorer()
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type!='NORMAL'or not _has_property(node,'SELF_LOOP_HOLDER'):continue
            holder=_read_property(node,'SELF_LOOP_HOLDER')
            if holder.are_ports_hidden:
                constraints=node.properties.get('ORIGINAL_PORT_CONSTRAINTS')
                if constraints is None:raise TypeError('The actual original port constraints are null')
                if constraints in('UNDEFINED','FREE'):assign_port_sides(holder)
                if constraints in('UNDEFINED','FREE','FIXED_SIDE'):
                    for loop in holder.sl_hyper_loops:loop.compute_ports_per_side()
                    restorer.restore_ports(holder)
            else:
                for loop in holder.sl_hyper_loops:loop.compute_ports_per_side()
    monitor.done()


def _labels_overlap(first,second):
    a=first.sl_labels;b=second.sl_labels
    if a is None or b is None:return False
    if a.side!=b.side or a.side in('EAST','WEST'):return False
    start_a=a.position.x;end_a=start_a+a.size.x
    start_b=b.position.x;end_b=start_b+b.size.x
    return start_a<=end_b and end_a>=start_b


class RoutingSlotAssigner:
    def __init__(self):
        self.hyper_edge_segments=None;self.sl_loop_to_segment=None;self.sl_loop_activity=None

    @staticmethod
    def _label_crossings(holder):
        count=0
        for loop in holder.sl_hyper_loops:
            if loop.sl_labels is not None:loop.sl_labels.id=count;count+=1
        matrix=[[False]*count for _ in range(count)]
        for first_index,first in enumerate(holder.sl_hyper_loops):
            if first.sl_labels is not None:
                for second in holder.sl_hyper_loops[first_index+1:]:
                    if second.sl_labels is not None:
                        overlap=_labels_overlap(first,second)
                        matrix[first.sl_labels.id][second.sl_labels.id]=overlap
                        matrix[second.sl_labels.id][first.sl_labels.id]=overlap
        return matrix
    def _activity(self,holder):
        ports=holder.l_node.ports
        for loop in holder.sl_hyper_loops:
            active=[False]*len(ports);self.sl_loop_activity.put(loop,active)
            index=loop.leftmost_port.l_port.id-1;target=loop.rightmost_port.l_port.id
            while index!=target:
                index=(index+1)%len(ports);active[index]=True
    def _crossings(self,upper,lower):
        active=self.sl_loop_activity.get(lower);count=0
        for port in upper.sl_ports:
            if active[port.l_port.id]:count+=1
        return count
    def _create_graph(self,holder,matrix):
        self.hyper_edge_segments=[];graph=_graph(holder.l_node)
        self.sl_loop_to_segment=_IdentityMap(graph)
        for loop in holder.sl_hyper_loops:
            segment=_Segment();self.hyper_edge_segments.append(segment)
            self.sl_loop_to_segment.put(loop,segment)
        self.sl_loop_activity=_IdentityMap(graph);self._activity(holder)
        for index,first in enumerate(holder.sl_hyper_loops[:-1]):
            for second in holder.sl_hyper_loops[index+1:]:
                first_above=self._crossings(first,second);second_above=self._crossings(second,first)
                a=self.sl_loop_to_segment.get(first);b=self.sl_loop_to_segment.get(second)
                if first_above<second_above:_dependency('REGULAR',a,b,second_above-first_above)
                elif second_above<first_above:_dependency('REGULAR',b,a,first_above-second_above)
                elif (first_above!=0 or first.sl_labels is not None and second.sl_labels is not None
                      and matrix[first.sl_labels.id][second.sl_labels.id]):
                    _dependency('REGULAR',a,b,0);_dependency('REGULAR',b,a,0)
    def _raw_segment_slots(self):
        sinks=deque()
        for segment in self.hyper_edge_segments:
            segment.in_weight=len(segment.incoming_dependencies)
            segment.out_weight=len(segment.outgoing_dependencies)
            if segment.out_weight==0:segment.slot=0;sinks.append(segment)
        while sinks:
            segment=sinks.popleft();next_slot=segment.slot+1
            for dependency in segment.incoming_dependencies:
                source=dependency.source;source.slot=_maximum(source.slot,next_slot)
                source.out_weight-=1
                if source.out_weight==0:sinks.append(source)
    def _raw_loop_slots(self,holder):
        for loop in holder.sl_hyper_loops:
            slot=self.sl_loop_to_segment.get(loop).slot
            for side in _SIDES:
                if side in loop.occupied_port_sides:loop.set_routing_slot(side,slot)
    def _shift_side(self,holder,side,next_free,matrix):
        loops=[loop for loop in holder.sl_hyper_loops if side in loop.occupied_port_sides]
        index=_SIDES.index(side)
        def compare(first,second):
            a=first.routing_slot[index];b=second.routing_slot[index]
            return -1 if a<b else 0 if a==b else 1
        _source_sort(loops,compare)
        minimum=2147483647;maximum=-2147483648
        for port in holder.l_node.ports:
            if port.side==side:minimum=min(minimum,port.id);maximum=max(maximum,port.id)
        if minimum==2147483647:
            for slot,loop in enumerate(loops):loop.set_routing_slot(side,slot)
        else:
            assigned=[-1]*len(matrix)
            for loop in loops:
                active=self.sl_loop_activity.get(loop);lowest=0
                for port_id in range(minimum,maximum+1):
                    if active[port_id]:lowest=_maximum(lowest,next_free[port_id])
                if loop.sl_labels is not None:
                    ours=loop.sl_labels.id;conflicts=set()
                    for other in range(len(matrix)):
                        if matrix[ours][other]:conflicts.add(assigned[other])
                    while lowest in conflicts:lowest+=1
                loop.set_routing_slot(side,lowest)
                for port_id in range(minimum,maximum+1):
                    if active[port_id]:next_free[port_id]=lowest+1
                if loop.sl_labels is not None:assigned[loop.sl_labels.id]=lowest
    def assign_slots(self,holder):
        matrix=self._label_crossings(holder);self._create_graph(holder,matrix)
        # Actual Internal RANDOM getter occurs even for an empty graph. A null
        # value only fails if the real generic chooser subsequently needs it.
        random=_graph(holder.l_node).properties.get('RANDOM')
        _break_cycles(self.hyper_edge_segments,random)
        self._raw_segment_slots();self._raw_loop_slots(holder)
        next_free=[0]*len(holder.l_node.ports)
        for side in('NORTH','EAST','SOUTH','WEST'):self._shift_side(holder,side,next_free,matrix)
        self.hyper_edge_segments=None;self.sl_loop_to_segment=None;self.sl_loop_activity=None


class LabelPlacer:
    """Actual SL45 label side/alignment selection; no geometric router."""
    @staticmethod
    def _assign(loop,side,alignment,reference):
        labels=loop.sl_labels;labels.side=side;labels.alignment=alignment
        labels.alignment_reference_sl_port=reference
    @staticmethod
    def _clear_inline(loop):
        for label in loop.sl_labels.l_labels:
            key=_stored_key(label,'EDGE_LABELS_INLINE')
            if key is not None:del label.properties[key]
    def _one_simple(self,loop,side):
        self._clear_inline(loop)
        if side in('EAST','WEST'):
            top=loop.leftmost_port
            if loop.rightmost_port.l_port.pos.y<top.l_port.pos.y:top=loop.rightmost_port
            self._assign(loop,side,'TOP',top)
        elif side in('NORTH','SOUTH'):self._assign(loop,side,'CENTER',None)
    def _one_sequenced(self,loops,side):
        for index,port in enumerate(loops[0].sl_holder.l_node.ports):port.id=index
        def compare(a,b):
            x=a.leftmost_port.l_port.id;y=b.leftmost_port.l_port.id
            if side!='NORTH':x,y=y,x
            return -1 if x<y else 0 if x==y else 1
        _source_sort(loops,compare);left=0;right=len(loops)-1
        while left<right:
            a=loops[left];b=loops[right]
            self._assign(a,side,'RIGHT',a.rightmost_port if side=='NORTH'else a.leftmost_port)
            self._assign(b,side,'LEFT',b.leftmost_port if side=='NORTH'else b.rightmost_port)
            left+=1;right-=1
        if left==right:self._assign(loops[left],side,'CENTER',None)
    def _corner(self,loop):
        self._clear_inline(loop);left=loop.leftmost_port;right=loop.rightmost_port
        if left.l_port.side=='NORTH':self._assign(loop,'NORTH','LEFT',left)
        elif right.l_port.side=='NORTH':self._assign(loop,'NORTH','RIGHT',right)
        elif left.l_port.side=='SOUTH':self._assign(loop,'SOUTH','RIGHT',left)
        elif right.l_port.side=='SOUTH':self._assign(loop,'SOUTH','LEFT',right)
    def _opposing_three(self,loop):
        sides=loop.occupied_port_sides
        inline=any(read_layered_scalar(label,'EDGE_LABELS_INLINE','EDGE_LABELS_INLINE_0')
                   for label in loop.sl_labels.l_labels)
        if 'NORTH'in sides:
            if 'SOUTH'in sides:
                if 'WEST'in sides:
                    if 'EAST'not in sides:self._assign(loop,'WEST'if inline else'NORTH',
                        'CENTER'if inline else'RIGHT',None if inline else loop.rightmost_port)
                else:self._assign(loop,'EAST'if inline else'NORTH','CENTER'if inline else'LEFT',
                                  None if inline else loop.leftmost_port)
            else:self._assign(loop,'NORTH','CENTER',None)
        else:self._assign(loop,'SOUTH','CENTER',None)
    def _assign_all(self,holder):
        ordering=read_layered_scalar(holder.l_node,'EDGE_ROUTING_SELF_LOOP_ORDERING',
                                    'EDGE_ROUTING_SELF_LOOP_ORDERING_0')
        north=[];south=[]
        for loop in holder.sl_hyper_loops:
            if loop.sl_labels is None:continue
            kind=loop.self_loop_type
            if kind=='ONE_SIDE':
                side=next(side for side in _SIDES if side in loop.occupied_port_sides)
                if ordering=='SEQUENCED'and side=='NORTH':north.append(loop)
                elif ordering=='SEQUENCED'and side=='SOUTH':south.append(loop)
                else:self._one_simple(loop,side)
            elif kind=='TWO_SIDES_CORNER':self._corner(loop)
            elif kind in('TWO_SIDES_OPPOSING','THREE_SIDES'):self._opposing_three(loop)
            elif kind=='FOUR_SIDES':
                self._clear_inline(loop)
                # Both source locals intentionally read the leftmost port.
                self._assign(loop,'SOUTH'if loop.leftmost_port.l_port.side=='NORTH'else'NORTH',
                             'CENTER',None)
        if ordering=='SEQUENCED':
            if north:self._one_sequenced(north,'NORTH')
            if south:self._one_sequenced(south,'SOUTH')
    @staticmethod
    def _coordinates(loop):
        labels=loop.sl_labels;reference=getattr(labels,'alignment_reference_sl_port',None)
        if labels.alignment=='CENTER':labels.position.x=(loop.sl_holder.l_node.size.x-labels.size.x)/2
        elif labels.alignment=='LEFT':labels.position.x=reference.l_port.pos.x+reference.l_port.anchor.x
        elif labels.alignment=='RIGHT':labels.position.x=reference.l_port.pos.x+reference.l_port.anchor.x-labels.size.x
        elif labels.alignment=='TOP':labels.position.y=reference.l_port.pos.y+reference.l_port.anchor.y
        else:raise TypeError('The actual label alignment is null')
    def place_labels(self,holder):
        self._assign_all(holder)
        for loop in holder.sl_hyper_loops:
            if loop.sl_labels is not None:self._coordinates(loop)


def _turn(side,direction):
    if side not in _SIDES[1:]:return 'UNDEFINED'
    return _SIDES[1:][(_SIDES.index(side)-1+(1 if direction==0 else -1))%4]


def _spacing(node,key,symbol):
    result=None
    if _has_property(node,'SPACING_INDIVIDUAL'):
        individual=_read_property(node,'SPACING_INDIVIDUAL')
        if not isinstance(individual,Mapping):raise TypeError('An actual individual spacing holder is required')
        from .native_properties import canonical_property_key
        canonical=canonical_property_key(key)
        if canonical in individual:result=individual[canonical]
    graph=_graph(node)
    if result is None and graph is not None:result=read_layered_scalar(graph,key,symbol)
    if result is None:raise TypeError('The actual inherited spacing is null')
    return result


class OrthogonalSelfLoopRouter:
    @staticmethod
    def _baseline(holder,side,distance):
        node=holder.l_node;margin=node.margin
        if side=='NORTH':return -float(margin.top)-distance
        if side=='EAST':return node.size.x+margin.right+distance
        if side=='SOUTH':return node.size.y+margin.bottom+distance
        if side=='WEST':return -float(margin.left)-distance
        return -1.0
    def _positions(self,holder,edge_gap,label_gap,node_gap):
        positions=[[0.0]*int(count)for count in holder.routing_slot_count]
        for side in('NORTH','SOUTH'):
            values=positions[_SIDES.index(side)]
            for loop in holder.sl_hyper_loops:
                labels=loop.sl_labels
                if labels is not None and labels.side==side:
                    index=int(loop.routing_slot[_SIDES.index(side)])
                    values[index]=_maximum(values[index],labels.size.y)
        for side in('NORTH','EAST','SOUTH','WEST'):
            current=self._baseline(holder,side,node_gap);factor=-1 if side in('NORTH','WEST')else 1
            values=positions[_SIDES.index(side)]
            for index,size in enumerate(values):
                if size>0:size+=label_gap
                values[index]=current;current+=factor*(size+edge_gap)
        return positions
    @staticmethod
    def _base(side,slot,positions):
        position=positions[_SIDES.index(side)][int(slot)]
        if side in('NORTH','SOUTH'):return Vec2(0.0,position)
        if side in('EAST','WEST'):return Vec2(position,0.0)
        return None
    def _outer(self,edge,port,positions,bends):
        loop=edge.sl_hyper_loop;native=port.l_port;side=native.side
        point=self._base(side,loop.routing_slot[_SIDES.index(side)],positions)
        anchor=Vec2(native.pos.x+native.anchor.x,native.pos.y+native.anchor.y)
        if side in('NORTH','SOUTH'):point.x+=anchor.x
        elif side in('EAST','WEST'):point.y+=anchor.y
        bends.append(point)
    @staticmethod
    def _adjust(point,side,size):
        if side=='NORTH':point.y-=size.y/2
        elif side=='SOUTH':point.y+=size.y/2
        elif side=='WEST':point.x-=size.x/2
        elif side=='EAST':point.x+=size.x/2
    def _corners(self,edge,direction,positions,bends):
        source=edge.sl_source.l_port;target=edge.sl_target.l_port
        if source.side==target.side:return
        loop=edge.sl_hyper_loop;label_side=None;label_size=None;inline=edge.is_inline()
        if inline and loop.sl_labels is not None:
            label_side=loop.sl_labels.side;label_size=loop.sl_labels.size
        current=source.side
        while current!=target.side:
            following=_turn(current,direction)
            a=self._base(current,loop.routing_slot[_SIDES.index(current)],positions)
            b=self._base(following,loop.routing_slot[_SIDES.index(following)],positions)
            if inline and label_side is not None and label_size is not None:
                if current==label_side:self._adjust(a,label_side,label_size)
                elif following==label_side:self._adjust(b,label_side,label_size)
            a.x+=b.x;a.y+=b.y;bends.append(a);current=following
    @staticmethod
    def _direction(edge):
        source=edge.sl_source.l_port;target=edge.sl_target.l_port
        if source.side==target.side:return 0 if source.id<target.id else 1
        if _turn(source.side,0)==target.side:return 0
        if _turn(source.side,1)==target.side:return 1
        return 0 if _turn(source.side,0)in edge.sl_hyper_loop.occupied_port_sides else 1
    @staticmethod
    def _update_margin(size,margin,point):
        margin.left=_maximum(margin.left,-float(point.x))
        margin.right=_maximum(margin.right,point.x-size.x)
        margin.top=_maximum(margin.top,-float(point.y))
        margin.bottom=_maximum(margin.bottom,point.y-size.y)
    @staticmethod
    def _place_labels(loop,labels,positions,gap):
        side=labels.side;position=positions[_SIDES.index(side)][int(loop.routing_slot[_SIDES.index(side)])]
        if any(read_layered_scalar(label,'EDGE_LABELS_INLINE','EDGE_LABELS_INLINE_0')for label in labels.l_labels):gap=0.0
        if side=='NORTH':position-=gap+labels.size.y;labels.position.y=position
        elif side=='SOUTH':position+=gap;labels.position.y=position
        elif side=='WEST':position-=gap+labels.size.x;labels.position.x=position
        elif side=='EAST':position+=gap;labels.position.x=position
    def modify_bend_points(self,edge,direction,bends):return bends
    def route(self,holder):
        from .graph import Insets
        node=holder.l_node;size=node.size;margin=node.margin
        edge_gap=_spacing(node,'SPACING_EDGE_EDGE','SPACING_EDGE_EDGE')
        label_gap=_spacing(node,'SPACING_EDGE_LABEL','SPACING_EDGE_LABEL_0')
        node_gap=_spacing(node,'SPACING_NODE_SELF_LOOP','SPACING_NODE_SELF_LOOP')
        new=Insets(margin.top,margin.right,margin.bottom,margin.left)
        positions=self._positions(holder,edge_gap,label_gap,node_gap)
        for loop in holder.sl_hyper_loops:
            for edge in loop.sl_edges.values():
                direction=self._direction(edge);bends=[]
                self._outer(edge,edge.sl_source,positions,bends);self._corners(edge,direction,positions,bends)
                self._outer(edge,edge.sl_target,positions,bends)
                bends=self.modify_bend_points(edge,direction,bends)
                native=edge.l_edge;native.bend_points.clear();native.bend_points.extend(bends)
                for point in bends:self._update_margin(size,new,point)
            labels=loop.sl_labels
            if labels is not None:
                self._place_labels(loop,labels,positions,label_gap)
                point=Vec2(labels.position.x,labels.position.y);self._update_margin(size,new,point)
                point.x+=labels.size.x;point.y+=labels.size.y;self._update_margin(size,new,point)
        margin.top=new.top;margin.right=new.right;margin.bottom=new.bottom;margin.left=new.left


def _number_sign(value):
    # Original host projection of the intrinsic, including signed zero/NaN.
    value=float(value)
    if value==0 or math.isnan(value):return value
    return -1.0 if value<0 else 1.0


def _near_zero(point):
    if point.x>=-0.01 and point.x<=0.01:point.x=0.0
    if point.y>=-0.01 and point.y<=0.01:point.y=0.0
    return point


class PolylineSelfLoopRouter(OrthogonalSelfLoopRouter):
    def modify_bend_points(self,edge,direction,bends):
        source=edge.sl_source.l_port;target=edge.sl_target.l_port
        bends.insert(0,Vec2(source.pos.x+source.anchor.x,source.pos.y+source.anchor.y))
        bends.append(Vec2(target.pos.x+target.anchor.x,target.pos.y+target.anchor.y))
        iterator=iter(bends);corner=next(iterator);following=next(iterator);result=[]
        for next_point in iterator:
            previous=corner;corner=following;following=next_point
            a=_near_zero(Vec2(previous.x-corner.x,previous.y-corner.y))
            b=_near_zero(Vec2(following.x-corner.x,following.y-corner.y))
            distance=10.0;distance=_minimum(distance,abs(a.x+a.y)/2)
            distance=_minimum(distance,abs(b.x+b.y)/2)
            a.x=_number_sign(a.x)*distance;a.y=_number_sign(a.y)*distance
            b.x=_number_sign(b.x)*distance;b.y=_number_sign(b.y)*distance
            a.x+=corner.x;a.y+=corner.y;b.x+=corner.x;b.y+=corner.y
            result.extend((a,b))
        return result


class SplineSelfLoopRouter(OrthogonalSelfLoopRouter):
    def modify_bend_points(self,edge,direction,bends):
        gap=_spacing(edge.sl_hyper_loop.sl_holder.l_node,'SPACING_EDGE_LABEL','SPACING_EDGE_LABEL_0')
        source=edge.sl_source.l_port;target=edge.sl_target.l_port
        points=[Vec2(source.pos.x+source.anchor.x,source.pos.y+source.anchor.y)]
        current=source.side;first=bends[0]
        for second in bends[1:]:
            points.append(first);middle=Vec2(first.x+second.x,first.y+second.y)
            middle.x*=0.5;middle.y*=0.5
            angle={'NORTH':4.71238898038469,'SOUTH':1.5707963267948966,
                   'WEST':3.141592653589793}.get(current,0.0)
            offset=Vec2(math.cos(angle),math.sin(angle));offset.x*=gap;offset.y*=gap
            middle.x+=offset.x;middle.y+=offset.y;points.append(middle)
            first=second;current=_turn(current,direction)
        points.append(bends[-1]);points.append(Vec2(target.pos.x+target.anchor.x,target.pos.y+target.anchor.y))
        return NubSpline(points).get_bezier_control_points()


class SelfLoopRouter:
    """Source processor lifetime: director and slot assigner belong to it."""
    source_name='SelfLoopRouter'
    def __init__(self):
        self.routing_director=RoutingDirector();self.routing_slot_assigner=RoutingSlotAssigner()
    def process(self,graph,*,monitor=None):
        monitor=BasicProgressMonitor(False,False)if monitor is None else monitor
        monitor.begin('Self-Loop routing',1)
        routing=read_layered_scalar(graph,'EDGE_ROUTING','EDGE_ROUTING')
        router=(PolylineSelfLoopRouter()if routing=='POLYLINE'else
                SplineSelfLoopRouter()if routing=='SPLINES'else OrthogonalSelfLoopRouter())
        if _read_property(graph,'org.eclipse.elk.labels.labelManager')is not None:
            raise TypeError('The actual LabelManager cannot be cast to a supported implementation')
        for layer in graph.layers:
            for node in layer.nodes:
                if node.type!='NORMAL'or not _has_property(node,'SELF_LOOP_HOLDER'):continue
                holder=_read_property(node,'SELF_LOOP_HOLDER')
                self.routing_director.determine_routes(holder);LabelPlacer().place_labels(holder)
                self.routing_slot_assigner.assign_slots(holder);router.route(holder)
        monitor.done()


def self_loop_router(graph,*,monitor=None):
    """One-shot convenience; factories bind one SelfLoopRouter.process instance."""
    return SelfLoopRouter().process(graph,monitor=monitor)
