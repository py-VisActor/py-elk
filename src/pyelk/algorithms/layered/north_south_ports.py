# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Components P06A/P06B/P06C in references/e13-kernel-sources.json.
# Native helpers only; crossing and provider schedule integration are separate.
"""North/south dummy builders; processing order and crossing are separate."""
from .graph import LNode, LPort, LEdge, Vec2, set_layer, set_port_owner, set_source, set_target
from .ports import set_side, is_side_fixed, is_order_fixed, _source_sort
from .orthogonal_general import get_junction_points
from .long_edges_general import _absolute_anchor
from .native_properties import CanonicalPropertyMap
from .property_access import read_layered_scalar

def _new_dummy(graph, origin=None):
    dummy = LNode(graph, type='NORTH_SOUTH_PORT', properties=CanonicalPropertyMap({'PORT_CONSTRAINTS': 'FIXED_POS'}))
    dummy.integer_box_identities = dummy.properties.integer_boxes
    if origin is not None:
        dummy.properties['ORIGIN'] = origin
    return dummy

def _new_dummy_port(dummy, original, side):
    port = LPort(properties=CanonicalPropertyMap({'ORIGIN': original}))
    port.integer_box_identities = port.properties.integer_boxes
    set_side(port, side)
    set_port_owner(port, dummy)
    return port

def create_dummy_node(graph, in_port, out_port, dummy_nodes):
    dummy = _new_dummy(graph)
    hint = 0
    if in_port is not None:
        dummy.properties['ORIGIN'] = in_port.owner
        dummy_input = _new_dummy_port(dummy, in_port, 'WEST')
        for edge in list(in_port.incoming_edges):
            set_target(edge, dummy_input)
        in_port.properties['PORT_DUMMY'] = dummy
        hint += 1
    if out_port is not None:
        dummy.properties['ORIGIN'] = out_port.owner
        dummy_output = _new_dummy_port(dummy, out_port, 'EAST')
        for edge in list(out_port.outgoing_edges):
            set_source(edge, dummy_output)
        out_port.properties['PORT_DUMMY'] = dummy
        hint += 1
    dummy.properties['CROSSING_HINT'] = hint
    dummy_nodes.append(dummy)
    return dummy

def create_north_south_self_loop_dummy_nodes(graph, edge, north_nodes, south_nodes, side):
    old_source, old_target = (edge.source, edge.target)
    north = _new_dummy(graph, old_source.owner)
    north_output = _new_dummy_port(north, old_source, side)
    old_source.properties['PORT_DUMMY'] = north
    south = _new_dummy(graph, old_target.owner)
    south_input = _new_dummy_port(south, old_target, side)
    old_target.properties['PORT_DUMMY'] = south
    set_source(edge, north_output)
    set_target(edge, south_input)
    north_nodes.insert(0, north)
    south_nodes.append(south)
    north.properties['CROSSING_HINT'] = 1
    south.properties['CROSSING_HINT'] = 1

def create_dummy_nodes(graph, ports, dummy_nodes, opposing_side_dummy_nodes, barycenter_associates):
    incoming = []
    outgoing = []
    mixed = []
    same_side_loops = []
    north_south_loops = []
    for port in ports:
        for edge in list(port.outgoing_edges):
            if edge.source.owner is edge.target.owner:
                if port.side == edge.target.side:
                    same_side_loops.append(edge)
                    continue
                elif port.side == 'NORTH' and edge.target.side == 'SOUTH':
                    north_south_loops.append(edge)
                    continue
    for edge in north_south_loops:
        create_north_south_self_loop_dummy_nodes(graph, edge, dummy_nodes, opposing_side_dummy_nodes, 'EAST')
    for edge in same_side_loops:
        dummy = _new_dummy(graph, edge)
        _new_dummy_port(dummy, edge.target, 'WEST')
        _new_dummy_port(dummy, edge.source, 'EAST')
        edge.source.properties['PORT_DUMMY'] = dummy
        edge.target.properties['PORT_DUMMY'] = dummy
        set_source(edge, None)
        set_target(edge, None)
        dummy_nodes.append(dummy)
        dummy.properties['CROSSING_HINT'] = 2
    for port in ports:
        has_in = bool(port.incoming_edges)
        has_out = bool(port.outgoing_edges)
        if has_in and has_out:
            mixed.append(port)
        elif has_in:
            incoming.append(port)
        elif has_out:
            outgoing.append(port)
    for port in incoming:
        barycenter_associates.append(create_dummy_node(graph, port, None, dummy_nodes))
    for port in outgoing:
        barycenter_associates.append(create_dummy_node(graph, None, port, dummy_nodes))
    for port in mixed:
        barycenter_associates.append(create_dummy_node(graph, port, port, dummy_nodes))

def _ports(node, side):
    return [port for port in node.ports if port.side == side]

def _successors(node):
    value = node.properties.get('IN_LAYER_SUCCESSOR_CONSTRAINTS')
    if value is None:
        value = []
        node.properties['IN_LAYER_SUCCESSOR_CONSTRAINTS'] = value
    return value

def _model_order_input_reversing(ports):
    incoming = []
    outgoing = []
    for port in ports:
        (incoming if port.incoming_edges else outgoing).append(port)
    return list(reversed(incoming)) + outgoing

def _sort_port_list(node):
    count = len(node.ports)
    incoming = 0
    mixed = count
    outgoing = 2 * count
    for port in node.ports:
        if port.side in {'EAST', 'WEST'}:
            port.id = -1
        elif port.side in {'NORTH', 'SOUTH'}:
            if port.incoming_edges and port.outgoing_edges:
                port.id = mixed
                mixed += 1
            elif port.incoming_edges:
                port.id = incoming
                incoming += 1
            elif port.outgoing_edges:
                port.id = outgoing
                outgoing += 1
            else:
                port.id = incoming
                incoming += 1
    order = {'UNDEFINED': 0, 'NORTH': 1, 'EAST': 2, 'SOUTH': 3, 'WEST': 4}

    def compare(first, second):
        if first.side != second.side:
            return order[first.side] - order[second.side]
        if first.id == second.id:
            return 0
        return first.id - second.id if first.side == 'NORTH' else second.id - first.id
    _source_sort(node.ports, compare)

def north_south_port_preprocessor(graph):
    north_nodes = []
    south_nodes = []
    strategy = read_layered_scalar(graph, 'CONSIDER_MODEL_ORDER_STRATEGY', 'CONSIDER_MODEL_ORDER_STRATEGY_0')
    for layer in graph.layers:
        pointer = -1
        for node in list(layer.nodes):
            pointer += 1
            constraints = read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
            if node.type != 'NORMAL' or not is_side_fixed(constraints):
                continue
            if not is_order_fixed(constraints) and strategy == 'NONE':
                _sort_port_list(node)
            node.properties['IN_LAYER_LAYOUT_UNIT'] = node
            north_nodes.clear()
            south_nodes.clear()
            associates = []
            ports = _ports(node, 'NORTH')
            if strategy != 'NONE':
                ports = _model_order_input_reversing(ports)
            create_dummy_nodes(graph, ports, north_nodes, south_nodes, associates)
            insert_point = pointer
            successor = node
            for dummy in north_nodes:
                set_layer(dummy, layer, insert_point)
                pointer += 1
                dummy.properties['IN_LAYER_LAYOUT_UNIT'] = node
                original = dummy.ports[0].properties['ORIGIN']
                if not read_layered_scalar(original, 'ALLOW_NON_FLOW_PORTS_TO_SWITCH_SIDES', 'ALLOW_NON_FLOW_PORTS_TO_SWITCH_SIDES_0'):
                    _successors(dummy).append(successor)
            ports = list(reversed(_ports(node, 'SOUTH')))
            if strategy != 'NONE':
                ports = _model_order_input_reversing(ports)
            create_dummy_nodes(graph, ports, south_nodes, None, associates)
            predecessor = node
            for dummy in south_nodes:
                pointer += 1
                set_layer(dummy, layer, pointer)
                dummy.properties['IN_LAYER_LAYOUT_UNIT'] = node
                original = dummy.ports[0].properties['ORIGIN']
                if not read_layered_scalar(original, 'ALLOW_NON_FLOW_PORTS_TO_SWITCH_SIDES', 'ALLOW_NON_FLOW_PORTS_TO_SWITCH_SIDES_0'):
                    _successors(predecessor).append(dummy)
            if associates:
                node.properties['BARYCENTER_ASSOCIATES'] = associates

def _process_input_port(port, add_junctions):
    original = port.properties['ORIGIN']
    x = _absolute_anchor(original).x
    y = port.owner.pos.y
    for edge in list(port.incoming_edges):
        set_target(edge, original)
        edge.bend_points.append(Vec2(x, y))
        if add_junctions:
            get_junction_points(edge).append(Vec2(x, y))

def _process_output_port(port, add_junctions):
    original = port.properties['ORIGIN']
    x = _absolute_anchor(original).x
    y = port.owner.pos.y
    for edge in list(port.outgoing_edges):
        set_source(edge, original)
        edge.bend_points.insert(0, Vec2(x, y))
        if add_junctions:
            get_junction_points(edge).append(Vec2(x, y))

def _process_spline_input_port(port):
    original = port.properties['ORIGIN']
    original.properties['SPLINE_NS_PORT_Y_COORD'] = port.owner.pos.y
    for edge in list(port.incoming_edges):
        set_target(edge, original)

def _process_spline_output_port(port):
    original = port.properties['ORIGIN']
    original.properties['SPLINE_NS_PORT_Y_COORD'] = port.owner.pos.y
    for edge in list(port.outgoing_edges):
        set_source(edge, original)

def north_south_port_postprocessor(graph):
    routing = read_layered_scalar(graph, 'EDGE_ROUTING', 'EDGE_ROUTING')
    for layer in graph.layers:
        for node in list(layer.nodes):
            if node.type != 'NORTH_SOUTH_PORT':
                continue
            if routing == 'SPLINES':
                for port in node.ports:
                    if port.incoming_edges:
                        _process_spline_input_port(port)
                    if port.outgoing_edges:
                        _process_spline_output_port(port)
            elif isinstance(node.properties.get('ORIGIN'), LEdge):
                edge = node.properties['ORIGIN']
                input_port = _ports(node, 'WEST')[0]
                output_port = _ports(node, 'EAST')[0]
                original_input = input_port.properties['ORIGIN']
                original_output = output_port.properties['ORIGIN']
                set_source(edge, original_output)
                set_target(edge, original_input)
                edge.bend_points.append(Vec2(_absolute_anchor(original_output).x, output_port.owner.pos.y))
                edge.bend_points.append(Vec2(_absolute_anchor(original_input).x, input_port.owner.pos.y))
            else:
                same_origin = False
                if len(node.ports) >= 2:
                    first = node.ports[0].properties.get('ORIGIN')
                    same_origin = all((port.properties.get('ORIGIN') is first for port in node.ports[1:]))
                for port in node.ports:
                    if port.incoming_edges:
                        _process_input_port(port, same_origin)
                    if port.outgoing_edges:
                        _process_output_port(port, same_origin)
            set_layer(node, None)
