# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# HOST17/root/spline-final-conversion-source-review-01.
"""Actual final spline control points and chain-to-cubic conversion."""
import math

from .graph import Vec2
from .cell_layout import Rectangle
from .spline_math import NubSpline
from .property_access import read_layered_scalar
from .native_adapters import _stored_key,_has_property
from .self_loops_general import _is_self_loop,_number_sign
from ..disco import contains_point,intersects_segment


def _absolute_anchor(port):
    point=Vec2()
    for vector in(port.owner.pos,port.pos,port.anchor):
        point.x+=vector.x;point.y+=vector.y
    return point


def _ns_y(port):
    value=port.properties.get('SPLINE_NS_PORT_Y_COORD')
    if value is None:raise TypeError('The actual splines.nsPortY value is null')
    return value


def _port_direction(side):
    return {'NORTH':4.71238898038469,'SOUTH':1.5707963267948966,
            'WEST':3.141592653589793}.get(side,0.0)


def _abs_min(first,second):return first if abs(first)<abs(second)else second


def calculate_bezier_bend_points(owner,edge_chain,surviving_edge):
    if len(edge_chain)==0:return
    points=[];edge=surviving_edge if surviving_edge is not None else edge_chain[0]
    source=edge.source
    if source.owner.type not in('NORMAL','NORTH_SOUTH_PORT','EXTERNAL_PORT','BREAKING_POINT'):
        raise ValueError('The target node of the edge must be a normal node or a northSouthPort.')
    points.append(_absolute_anchor(source))
    if source.side in('NORTH','SOUTH'):
        source_y=_ns_y(source)
        points.append(Vec2(_absolute_anchor(source).x,source_y))
    last=None;add_midpoint=False
    for current in edge_chain:
        bends=current.bend_points
        if bends:
            if add_midpoint:
                last.x+=bends[0].x;last.y+=bends[0].y;last.x*=0.5;last.y*=0.5
                points.append(last);add_midpoint=False
            else:add_midpoint=True
            last=Vec2(bends[-1].x,bends[-1].y)
            points.extend(bends);bends.clear()
    target=edge.target
    if target.side in('NORTH','SOUTH'):
        target_y=_ns_y(target)
        points.append(Vec2(_absolute_anchor(target).x,target_y))
    points.append(_absolute_anchor(target))
    if owner.spline_routing_mode=='CONSERVATIVE':
        first=points[0];second=points[1];angle=_port_direction(source.side)
        vector=Vec2(math.cos(angle),math.sin(angle));vector.x*=5;vector.y*=5
        difference=Vec2(second.x-first.x,second.y-first.y)
        beginning=Vec2(_abs_min(vector.x,difference.x),_abs_min(vector.y,difference.y))
        beginning.x+=first.x;beginning.y+=first.y;points.insert(1,beginning)
        last=points[-1];before_last=points[-2];angle=_port_direction(target.side)
        vector=Vec2(math.cos(angle),math.sin(angle));vector.x*=5;vector.y*=5
        difference=Vec2(before_last.x-last.x,before_last.y-last.y)
        ending=Vec2(_abs_min(vector.x,difference.x),_abs_min(vector.y,difference.y))
        ending.x+=last.x;ending.y+=last.y;points.insert(len(points)-1,ending)
    # If the selected survivor is not in edge_chain, its preexisting points
    # remain: only chains actually visited above were cleared by the source.
    edge.bend_points.extend(NubSpline(points).get_bezier_control_points())


def _bare_property(element,name):
    # These Source SF25 Properties have id-only constructors: undefined/nullish
    # defaults are hosted as None, without materializing a property cell.
    key=_stored_key(element,name)
    return None if key is None else element.properties[key]


def _remove_property(element,name):
    key=_stored_key(element,name)
    if key is not None:del element.properties[key]


def _node_box(node):
    position=node.pos;size=node.size;margin=node.margin
    return Rectangle(position.x-margin.left,position.y-margin.top,
                     size.x+(margin.left+margin.right),size.y+(margin.top+margin.bottom))


def _integer_power(base,exponent):
    # This Source caller only supplies degree2 exponents 0,1,2.
    result=1.0;value=base;remaining=exponent if exponent>=0 else -exponent
    while remaining>0:
        if remaining%2==0:value*=value;remaining//=2
        else:result*=value;remaining-=1
    return 1.0/result if exponent<0 else result


def _quadratic_samples(points):
    result=[];t=0.0
    for _ in range(2):
        t+=0.5;x=0.0;y=0.0
        for index,coefficient in enumerate((1.0,2.0,1.0)):
            point=points[index]
            factor=coefficient*_integer_power(1-t,2-index)*_integer_power(t,index)
            x+=point.x*factor;y+=point.y*factor
        result.append(Vec2(x,y))
    return result


def _sloppy_center(edge,source_y,target_y):
    incoming=0.0;outgoing=0.0
    if edge.source is not None:
        for port in edge.target.owner.ports:incoming+=len(port.incoming_edges)
    else:incoming=1.0
    if edge.target is not None:
        for port in edge.source.owner.ports:outgoing+=len(port.outgoing_edges)
    else:outgoing=1.0
    value=_number_sign(outgoing-incoming);difference=0 if math.isnan(value)else int(value)
    return (target_y+source_y)/2+(target_y-source_y)*(0.4*difference)


def _sloppy_points(edge,segment):
    information=segment.edge_information.get(edge)
    start=segment.bounding_box.x;end=segment.bounding_box.x+segment.bounding_box.width
    source_y=information.start_y;target_y=information.end_y;down=source_y<target_y
    source_straight=Vec2(start,source_y);target_straight=Vec2(end,target_y)
    center_x=(start+end)/2
    source_vertical=Vec2(center_x,source_y);target_vertical=Vec2(center_x,target_y)
    center_y=_sloppy_center(edge,source_y,target_y)
    first=_absolute_anchor(segment.source_port);middle=Vec2(center_x,center_y)
    last=_absolute_anchor(segment.target_port);approximation=_quadratic_samples((first,middle,last))
    source_shortcut=False;node=segment.source_port.owner
    if node is not None and node.layer is not None and information.normal_source_node:
        needs=down and node.id<len(node.layer.nodes)-1 or not down and node.id>0
        if needs:
            index=node.id+1 if down else node.id-1;box=_node_box(node.layer.nodes[index])
            source_shortcut=not(intersects_segment(box,first,approximation[0])or
                contains_point(box,first)and contains_point(box,approximation[0]))
        else:source_shortcut=True
    target_shortcut=False;node=segment.target_port.owner
    if node is not None and node.layer is not None and information.normal_target_node:
        needs=down and node.id>0 or not down and node.id<len(node.layer.nodes)-1
        if needs:
            index=node.id-1 if down else node.id+1;box=_node_box(node.layer.nodes[index])
            target_shortcut=not(intersects_segment(box,approximation[0],last)or
                contains_point(box,approximation[0])and contains_point(box,last))
        else:target_shortcut=True
    if source_shortcut and target_shortcut:edge.bend_points.append(middle)
    if not source_shortcut:edge.bend_points.extend((source_straight,source_vertical))
    if not target_shortcut:edge.bend_points.extend((target_vertical,target_straight))


class FinalSplineBendpointsCalculator:
    source_name='FinalSplineBendpointsCalculator'
    def __init__(self):
        self.edge_edge_spacing=0.0;self.edge_node_spacing=0.0
    def calculate_control_points(self,segment):
        if segment.handled:return
        segment.handled=True
        for edge in segment.edges.values():
            if segment.is_straight and len(segment.edges.values())<=1:
                start=segment.bounding_box.x;end=segment.bounding_box.x+segment.bounding_box.width
                segment.edges.values()[0].bend_points.append(Vec2(start+(end-start)/2,
                                                                 segment.center_control_point_y))
                continue
            information=segment.edge_information.get(edge)
            if information.inverted_left or information.inverted_right:
                self._conservative_points(edge,segment,True);continue
            sloppy=(self.spline_routing_mode=='SLOPPY'and
                    (information.normal_source_node or information.normal_target_node)and
                    self._allows_sloppy(segment)and len(segment.edges.values())<=1)
            if sloppy:_sloppy_points(edge,segment)
            else:self._conservative_points(edge,segment,False)
        if segment.inverse_order:
            for edge in segment.edges.values():edge.bend_points.reverse()
    def _conservative_points(self,edge,segment,inverted):
        start=segment.bounding_box.x;end=segment.bounding_box.x+segment.bounding_box.width
        information=segment.edge_information.get(edge);source_y=information.start_y;target_y=information.end_y
        source=Vec2(end if inverted and information.inverted_left else start,source_y)
        target=Vec2(start if inverted and information.inverted_right else end,target_y)
        center_x=start
        if not segment.is_west_of_initial_layer:center_x+=self.edge_node_spacing
        center_x+=segment.x_delta+segment.rank*self.edge_edge_spacing
        source_vertical=Vec2(center_x,source_y);target_vertical=Vec2(center_x,target_y)
        edge.bend_points.extend((source,source_vertical))
        if len(segment.edges.values())>1:edge.bend_points.append(Vec2(center_x,segment.center_control_point_y))
        edge.bend_points.extend((target_vertical,target))
    def _allows_sloppy(self,segment):
        if self.compaction_strategy=='NONE':return True
        start=segment.bounding_box.x;end=segment.bounding_box.x+segment.bounding_box.width
        if segment.initial_segment:
            node=segment.source_node;threshold=node.layer.size.x-node.size.x/2
            distance=start-(node.pos.x+node.size.x)
            if distance>threshold:return False
        if segment.last_segment:
            node=segment.target_node;threshold=node.layer.size.x-node.size.x/2
            distance=node.pos.x-end
            if distance>threshold:return False
        return True
    def process(self,graph,monitor=None):
        # Actual Source wrapper deliberately ignores the passed monitor.
        self.edge_edge_spacing=read_layered_scalar(graph,'SPACING_EDGE_EDGE_BETWEEN_LAYERS',
                                                  'SPACING_EDGE_EDGE_BETWEEN_LAYERS_0')
        self.edge_node_spacing=read_layered_scalar(graph,'SPACING_EDGE_NODE_BETWEEN_LAYERS',
                                                  'SPACING_EDGE_NODE_BETWEEN_LAYERS_0')
        self.spline_routing_mode=read_layered_scalar(graph,'EDGE_ROUTING_SPLINES_MODE','EDGE_ROUTING_SPLINES_MODE_0')
        self.compaction_strategy=read_layered_scalar(graph,'COMPACTION_POST_COMPACTION_STRATEGY',
                                                   'COMPACTION_POST_COMPACTION_STRATEGY_0')
        for layer in graph.layers:
            for index,node in enumerate(layer.nodes):node.id=index
        start_edges=[]
        for layer in graph.layers:
            for node in layer.nodes:
                lists=[port.outgoing_edges for port in node.ports]
                for edges in lists:
                    for edge in edges:
                        if not _is_self_loop(edge)and _has_property(edge,'SPLINE_ROUTE_START'):
                            start_edges.append(edge)
        for edge in start_edges:
            segments=_bare_property(edge,'SPLINE_ROUTE_START')
            for segment in segments:self.calculate_control_points(segment)
            _remove_property(edge,'SPLINE_ROUTE_START')
        for edge in start_edges:
            survivor=_bare_property(edge,'SPLINE_SURVIVING_EDGE')
            chain=_bare_property(edge,'SPLINE_EDGE_CHAIN')
            if chain is None:raise TypeError('The actual splines.edgeChain is null')
            calculate_bezier_bend_points(self,chain,survivor)
            _remove_property(edge,'SPLINE_EDGE_CHAIN')
