# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# HOST17/root/polyline-driver-source-review-01; V/polyline-math-source-review-01.
"""Actual cached Polyline P5; native graph geometry and value junction keys."""
from .graph import Vec2
from .orthogonal_general import _place_nodes_horizontally,_is_external_west_or_east,get_junction_points
from .self_loops_general import _is_self_loop
from .property_access import read_layered_scalar
from .graph_info import get_graph_properties
from ...execution.diagnostics import BasicProgressMonitor
from ..triangulation import ValueSet,_minimum
from ..fixed import _div
from ..radial import _maximum


def _absolute_anchor(port):
    point=Vec2()
    for vector in(port.owner.pos,port.pos,port.anchor):
        point.x+=vector.x;point.y+=vector.y
    return point


def _outgoing(node):
    return(edge for port in node.ports for edge in port.outgoing_edges)


def _connected(node):
    return(edge for port in node.ports
           for edges in(port.incoming_edges,port.outgoing_edges)for edge in edges)


def _west_in_layer_y_diff(layer):
    difference=0.0
    for node in layer.nodes:
        for edge in _outgoing(node):
            if layer is edge.target.owner.layer and edge.source.side=='WEST':
                source_y=_absolute_anchor(edge.source).y
                target_y=_absolute_anchor(edge.target).y
                difference=_maximum(difference,abs(target_y-source_y))
    return difference


def _is_in_layer_dummy(node):
    if node.type=='LONG_EDGE':
        for edge in _connected(node):
            if not _is_self_loop(edge) and edge.source.owner.layer is edge.target.owner.layer:
                return True
    return False


def _process_in_layer_edge(edge,layer_x,spacing):
    source=edge.source;target=edge.target
    source_y=_absolute_anchor(source).y
    mid_y=(source_y+_absolute_anchor(target).y)/2
    if source.side=='EAST':point=Vec2(layer_x+source.owner.layer.size.x+spacing,mid_y)
    else:point=Vec2(layer_x-spacing,mid_y)
    edge.bend_points.insert(0,point)


class PolylineEdgeRouter:
    source_name='PolylineEdgeRouter'

    def __init__(self):
        self.created_junction_points=ValueSet()

    def _add_bend_point(self,edge,point,add_junction,current_port):
        # Keep Source shortcircuit order: even a self-loop may evaluate its
        # current absolute anchor before the final self-loop exclusion.
        if (not _is_self_loop(edge) and edge.source.owner.layer is edge.target.owner.layer
                or not _point_equals(_absolute_anchor(current_port),point)) and not _is_self_loop(edge):
            bend=Vec2(point.x,point.y)
            if edge.source is current_port:edge.bend_points.insert(0,bend)
            else:edge.bend_points.append(bend)
            if add_junction and not self.created_junction_points.contains(point):
                chain=get_junction_points(edge)
                junction=Vec2(point.x,point.y)
                chain.append(junction)
                self.created_junction_points.add(junction)

    def _process_node(self,node,layer_left,max_difference):
        layer_right=layer_left+node.layer.size.x
        for port in node.ports:
            anchor=_absolute_anchor(port)
            if node.type=='NORTH_SOUTH_PORT':
                corresponding=port.properties.get('ORIGIN')
                anchor.x=_absolute_anchor(corresponding).x
                node.pos.x=anchor.x
            point=Vec2(0.0,anchor.y)
            if port.side=='EAST':point.x=layer_right
            elif port.side=='WEST':point.x=layer_left
            else:continue
            distance=abs(anchor.x-point.x)
            if distance<=max_difference and not _is_in_layer_dummy(node):continue
            add_junction=len(port.outgoing_edges)+len(port.incoming_edges)>1
            for edges in(port.incoming_edges,port.outgoing_edges):
                for edge in edges:
                    other=edge.target if edge.source is port else edge.source
                    if abs(_absolute_anchor(other).y-point.y)>1:
                        self._add_bend_point(edge,point,add_junction,port)

    def get_layout_processor_configuration(self,graph):
        from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as Strategy
        properties=get_graph_properties(graph)
        p1,p2,p3,p4,p5=tuple(LayeredPhase);configuration=LayoutProcessorConfiguration()
        def before(phase,name):configuration.add_before(phase,Strategy[name])
        def after(phase,name):configuration.add_after(phase,Strategy[name])
        before(p3,'INVERTED_PORT_PROCESSOR')
        if 'NORTH_SOUTH_PORTS'in properties:
            before(p3,'NORTH_SOUTH_PORT_PREPROCESSOR');after(p5,'NORTH_SOUTH_PORT_POSTPROCESSOR')
        if 'SELF_LOOPS'in properties:
            before(p1,'SELF_LOOP_PREPROCESSOR');after(p5,'SELF_LOOP_POSTPROCESSOR')
            before(p4,'SELF_LOOP_PORT_RESTORER');before(p4,'SELF_LOOP_ROUTER')
        if 'CENTER_LABELS'in properties:
            before(p2,'LABEL_DUMMY_INSERTER');before(p4,'LABEL_DUMMY_SWITCHER')
            before(p4,'LABEL_SIDE_SELECTOR');after(p5,'LABEL_DUMMY_REMOVER')
        if 'END_LABELS'in properties:
            before(p4,'LABEL_SIDE_SELECTOR');before(p4,'END_LABEL_PREPROCESSOR')
            after(p5,'END_LABEL_POSTPROCESSOR')
        return configuration

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Polyline edge routing',1)
        zone=read_layered_scalar(graph,'EDGE_ROUTING_POLYLINE_SLOPED_EDGE_ZONE_WIDTH',
                                 'EDGE_ROUTING_POLYLINE_SLOPED_EDGE_ZONE_WIDTH_0')
        node_spacing=read_layered_scalar(graph,'SPACING_NODE_NODE_BETWEEN_LAYERS',
                                         'SPACING_NODE_NODE_BETWEEN_LAYERS_0')
        edge_spacing=read_layered_scalar(graph,'SPACING_EDGE_EDGE_BETWEEN_LAYERS',
                                         'SPACING_EDGE_EDGE_BETWEEN_LAYERS_0')
        factor=_minimum(1.0,_div(edge_spacing,node_spacing))
        position=0.0;layer_spacing=0.0
        if graph.layers:
            position=0.4*factor*_west_in_layer_y_diff(graph.layers[0])
        for index,layer in enumerate(graph.layers):
            external=all(_is_external_west_or_east(node)for node in layer.nodes)
            if external and position>0:position-=node_spacing
            _place_nodes_horizontally(layer,position)
            max_difference=0.0
            for node in layer.nodes:
                current_difference=0.0
                for edge in _outgoing(node):
                    source_y=_absolute_anchor(edge.source).y
                    target_y=_absolute_anchor(edge.target).y
                    if layer is edge.target.owner.layer and not _is_self_loop(edge):
                        _process_in_layer_edge(edge,position,0.4*factor*abs(source_y-target_y))
                        if edge.source.side=='WEST':source_y=0.0;target_y=0.0
                    current_difference=_maximum(current_difference,abs(target_y-source_y))
                if node.type in('NORMAL','LABEL','LONG_EDGE','NORTH_SOUTH_PORT','BREAKING_POINT'):
                    self._process_node(node,position,zone)
                max_difference=_maximum(max_difference,current_difference)
            if index+1<len(graph.layers):
                difference=_west_in_layer_y_diff(graph.layers[index+1])
                max_difference=_maximum(max_difference,difference)
            layer_spacing=0.4*factor*max_difference
            if not external and index+1<len(graph.layers):layer_spacing+=node_spacing
            position+=layer.size.x+layer_spacing
        # Source clears the same backing map, only at successful completion.
        self.created_junction_points.map.buckets.clear()
        self.created_junction_points.map.count=0
        graph.size.x=position
        monitor.done()


def _point_equals(first,second):return first.x==second.x and first.y==second.y
