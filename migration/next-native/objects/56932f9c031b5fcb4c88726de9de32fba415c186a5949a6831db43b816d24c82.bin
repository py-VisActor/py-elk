# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P22F/G actual hierarchy port routing.
"""Restore and route real north/south hierarchy dummies over general axes."""
from .cell_layout import _maximum
from ...execution.identity import identity_hash
from .graph import LEdge, LPort, Vec2, set_layer, set_port_owner, set_source, set_target
from .hierarchical_port_position import border_to_content_coordinates
from .native_adapters import LGraphAdapter, LNodeAdapter, NodeMarginCalculator, _read_property
from .native_properties import CanonicalPropertyMap
from .native_transfer import _sum_vectors
from .orthogonal_axes import routing_generator
from .ports import _divide, _source_sort, double_compare, set_side
from .property_access import read_layered_scalar


def _ratio(node):
    return node.properties.get('PORT_RATIO_OR_POSITION', 0.0)


def _ext_size(node):
    value = node.properties.get('EXT_PORT_SIZE')
    if value is None:
        value = Vec2()
        node.properties['EXT_PORT_SIZE'] = value
    return value


def _new_port(node):
    port = LPort(properties=CanonicalPropertyMap())
    port.integer_box_identities = port.properties.integer_boxes
    port.labels = []
    set_port_owner(port, node)
    return port


def _new_edge():
    edge = LEdge(properties=CanonicalPropertyMap())
    edge.integer_box_identities = edge.properties.integer_boxes
    edge.labels = []
    return edge


def _incoming(node):
    lists = [port.incoming_edges for port in node.ports]
    for edges in lists:
        yield from edges


def _connected(node):
    ports = list(node.ports)
    for port in ports:
        yield from port.incoming_edges
        yield from port.outgoing_edges


def _add_identity(graph, items, value):
    # Every reached LinkedHashSet.add requests its key's stable source hash,
    # including duplicate adds; iteration still follows first insertion.
    if value is not None:
        method = getattr(graph, 'identity_hash', None)
        method(value) if method is not None else identity_hash(graph, value)
    if not any(item is value for item in items):
        items.append(value)


def assign_ascending_coordinates(dummies, graph):
    spacing = read_layered_scalar(graph, 'SPACING_PORT_PORT', 'SPACING_PORT_PORT')
    following = dummies[0].pos.x + dummies[0].size.x + dummies[0].margin.right + spacing
    for index in range(1, len(dummies)):
        node = dummies[index]
        position, size, margin = node.pos, node.size, node.margin
        delta = position.x - margin.left - following
        if delta < 0:
            position.x -= delta
        graph.size.x = _maximum(graph.size.x, position.x + size.x)
        following = position.x + size.x + margin.right + spacing


def calculate_north_south_dummy_positions(dummy):
    port = dummy.ports[0]
    count = len(port.incoming_edges) + len(port.outgoing_edges)
    if count == 0:
        dummy.pos.x = 0.0
    else:
        total = 0.0
        for edge in port.incoming_edges:
            other = edge.source
            total += other.owner.pos.x + other.pos.x + other.anchor.x
        for edge in port.outgoing_edges:
            other = edge.target
            total += other.owner.pos.x + other.pos.x + other.anchor.x
        anchor = dummy.properties.get('PORT_ANCHOR')
        offset = 0.0 if anchor is None else anchor.x
        dummy.pos.x = _divide(total, len(port.incoming_edges) + len(port.outgoing_edges)) - offset


def correct_slanted_edge_segments(layer):
    for node in layer.nodes:
        if node.type != 'EXTERNAL_PORT':
            continue
        side = node.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
        if side in ('EAST', 'WEST'):
            for edge in _connected(node):
                bends = edge.bend_points
                if len(bends) == 0:
                    continue
                source = edge.source
                if source.owner is node:
                    bends[0].y = _sum_vectors(source.owner.pos, source.pos, source.anchor).y
                target = edge.target
                if target.owner is node:
                    bends[-1].y = _sum_vectors(target.owner.pos, target.pos, target.anchor).y


def ensure_unique_positions(dummies, graph):
    if len(dummies) == 0:
        return
    ordered = list(dummies)
    _source_sort(ordered, lambda a, b: double_compare(a.pos.x, b.pos.x))
    assign_ascending_coordinates(ordered, graph)


def restore_proper_order(dummies, graph):
    if len(dummies) == 0:
        return
    ordered = list(dummies)
    _source_sort(ordered, lambda a, b: double_compare(_ratio(a), _ratio(b)))
    assign_ascending_coordinates(ordered, graph)


def fix_coordinates(layer, constraints, graph):
    padding, offset = graph.padding, graph.offset
    actual = Vec2(graph.size.x + graph.padding.left + graph.padding.right,
                  graph.size.y + graph.padding.top + graph.padding.bottom)
    height = actual.y
    for node in layer.nodes:
        if node.type != 'EXTERNAL_PORT':
            continue
        side = node.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
        port_size = _ext_size(node)
        position = node.pos
        if side == 'EAST':
            position.x = graph.size.x + padding.right - offset.x
        elif side == 'WEST':
            position.x = -offset.x - padding.left
        required = 0.0
        if side in ('EAST', 'WEST'):
            if constraints == 'FIXED_RATIO':
                position.y = actual.y * _ratio(node) - node.properties.get('PORT_ANCHOR').y
                required = position.y + port_size.y
                border_to_content_coordinates(node, False, True)
            elif constraints == 'FIXED_POS':
                position.y = _ratio(node) - node.properties.get('PORT_ANCHOR').y
                required = position.y + port_size.y
                border_to_content_coordinates(node, False, True)
        height = _maximum(height, required)
    graph.size.y += height - actual.y
    for node in layer.nodes:
        if node.type != 'EXTERNAL_PORT':
            continue
        side = node.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
        if side == 'NORTH':
            node.pos.y = -offset.y - padding.top
        elif side == 'SOUTH':
            node.pos.y = graph.size.y + padding.bottom - offset.y


def restore_dummy(dummy, graph):
    side = dummy.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
    port = dummy.ports[0]
    if side == 'NORTH':
        set_side(port, 'SOUTH')
    elif side == 'SOUTH':
        set_side(port, 'NORTH')
    if 'PORT_LABELS' in _read_property(graph, 'NODE_SIZE_CONSTRAINTS'):
        horizontal = read_layered_scalar(dummy, 'SPACING_LABEL_PORT_HORIZONTAL', 'SPACING_LABEL_PORT_HORIZONTAL')
        vertical = read_layered_scalar(dummy, 'SPACING_LABEL_PORT_VERTICAL', 'SPACING_LABEL_PORT_VERTICAL')
        between = read_layered_scalar(dummy, 'SPACING_LABEL_LABEL', 'SPACING_LABEL_LABEL')
        placement = _read_property(graph, 'PORT_LABELS_PLACEMENT')
        if 'INSIDE' in placement:
            current_y = vertical
            center = dummy.size.x / 2 - port.pos.x
            for label in port.labels:
                label.pos.y = current_y
                label.pos.x = center - label.size.x / 2
                current_y += label.size.y + between
        elif 'OUTSIDE' in placement:
            for label in port.labels:
                label.pos.x = horizontal + dummy.size.x - port.pos.x
        NodeMarginCalculator(LGraphAdapter(graph, False, False)).process_node(LNodeAdapter(None, dummy, False))


def restore_north_south_dummies(graph):
    restored = []
    if 'EXT_PORT_REPLACED_DUMMIES' not in graph.properties:
        return restored
    for dummy in graph.properties['EXT_PORT_REPLACED_DUMMIES']:
        restore_dummy(dummy, graph)
        restored.append(dummy)
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type != 'EXTERNAL_PORT':
                continue
            replaced = node.properties.get('EXT_PORT_REPLACED_DUMMY')
            if replaced is not None:
                output = _new_port(node)
                set_side(output, node.properties.get('EXT_PORT_SIDE', 'UNDEFINED'))
                incoming = replaced.ports[0]
                edge = _new_edge()
                set_source(edge, output)
                set_target(edge, incoming)
    for dummy in restored:
        set_layer(dummy, graph.layers[-1])
    return restored


def remove_temporary_north_south_dummies(graph):
    remove = []
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type != 'EXTERNAL_PORT' or 'EXT_PORT_REPLACED_DUMMY' not in node.properties:
                continue
            incoming = outgoing = origin = None
            for port in node.ports:
                if port.side == 'WEST':
                    incoming = port
                elif port.side == 'EAST':
                    outgoing = port
                else:
                    origin = port
            to_origin = origin.outgoing_edges[0]
            incoming_bends = list(to_origin.bend_points)
            first = Vec2(origin.pos.x, origin.pos.y)
            first.x += node.pos.x
            first.y += node.pos.y
            incoming_bends.insert(0, first)
            outgoing_bends = [Vec2(point.x, point.y) for point in reversed(to_origin.bend_points)]
            last = Vec2(origin.pos.x, origin.pos.y)
            last.x += node.pos.x
            last.y += node.pos.y
            outgoing_bends.append(last)
            replaced = node.properties.get('EXT_PORT_REPLACED_DUMMY')
            port = replaced.ports[0]
            for edge in list(incoming.incoming_edges):
                set_target(edge, port)
                edge.bend_points.extend(Vec2(point.x, point.y) for point in incoming_bends)
            for edge in list(outgoing.outgoing_edges):
                set_source(edge, port)
                edge.bend_points[0:0] = [Vec2(point.x, point.y) for point in outgoing_bends]
            set_source(to_origin, None)
            set_target(to_origin, None)
            remove.append(node)
    for node in remove:
        set_layer(node, None)


class HierarchicalPortOrthogonalEdgeRouter:
    source_name = 'HierarchicalPortOrthogonalEdgeRouter'

    def __init__(self):
        self.northern_ext_port_edge_routing_height = 0.0

    def set_north_south_dummy_coordinates(self, graph, dummies):
        constraints = read_layered_scalar(graph, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
        size, padding = graph.size, graph.padding
        width = size.x + padding.left + padding.right
        north_y = 0.0 - padding.top - graph.offset.y
        south_y = size.y + padding.top + padding.bottom - graph.offset.y
        north, south = [], []
        for dummy in dummies:
            if constraints in ('FREE', 'FIXED_SIDE', 'FIXED_ORDER'):
                calculate_north_south_dummy_positions(dummy)
            elif constraints == 'FIXED_RATIO':
                anchor = dummy.properties.get('PORT_ANCHOR')
                offset = 0.0 if anchor is None else anchor.x
                dummy.pos.x = width * _ratio(dummy) - offset
                border_to_content_coordinates(dummy, True, False)
            elif constraints == 'FIXED_POS':
                anchor = dummy.properties.get('PORT_ANCHOR')
                offset = 0.0 if anchor is None else anchor.x
                dummy.pos.x = _ratio(dummy) - offset
                border_to_content_coordinates(dummy, True, False)
                size.x = _maximum(size.x, dummy.pos.x + dummy.size.x / 2)
            side = dummy.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
            if side == 'NORTH':
                dummy.pos.y = north_y
                north.append(dummy)
            elif side == 'SOUTH':
                dummy.pos.y = south_y
                south.append(dummy)
        if constraints in ('FREE', 'FIXED_SIDE'):
            ensure_unique_positions(north, graph)
            ensure_unique_positions(south, graph)
        elif constraints == 'FIXED_ORDER':
            restore_proper_order(north, graph)
            restore_proper_order(south, graph)

    def route_edges(self, graph, dummies):
        north_sources, north_targets, south_sources, south_targets = [], [], [], []
        node_spacing = read_layered_scalar(graph, 'SPACING_NODE_NODE', 'SPACING_NODE_NODE_0')
        edge_spacing = read_layered_scalar(graph, 'SPACING_EDGE_EDGE', 'SPACING_EDGE_EDGE')
        for dummy in dummies:
            side = dummy.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
            if side == 'NORTH':
                _add_identity(graph, north_targets, dummy)
                for edge in _incoming(dummy):
                    _add_identity(graph, north_sources, edge.source.owner)
            elif side == 'SOUTH':
                _add_identity(graph, south_targets, dummy)
                for edge in _incoming(dummy):
                    _add_identity(graph, south_sources, edge.source.owner)
        if len(north_sources) != 0:
            generator = routing_generator(2, edge_spacing)
            slots = generator.route(graph, north_sources, north_targets, -node_spacing - graph.offset.y)
            if slots > 0:
                self.northern_ext_port_edge_routing_height = node_spacing + (slots - 1) * edge_spacing
                graph.offset.y += self.northern_ext_port_edge_routing_height
                graph.size.y += self.northern_ext_port_edge_routing_height
        if len(south_sources) != 0:
            generator = routing_generator(1, edge_spacing)
            slots = generator.route(graph, south_sources, south_targets,
                                    graph.size.y + node_spacing - graph.offset.y)
            if slots > 0:
                graph.size.y += node_spacing + (slots - 1) * edge_spacing

    def process(self, graph, *, monitor):
        monitor.begin('Orthogonally routing hierarchical port edges', 1)
        self.northern_ext_port_edge_routing_height = 0.0
        dummies = restore_north_south_dummies(graph)
        self.set_north_south_dummy_coordinates(graph, dummies)
        self.route_edges(graph, dummies)
        remove_temporary_north_south_dummies(graph)
        constraints = read_layered_scalar(graph, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
        layers = graph.layers
        fix_coordinates(layers[0], constraints, graph)
        fix_coordinates(layers[-1], constraints, graph)
        correct_slanted_edge_segments(graph.layers[0])
        correct_slanted_edge_segments(graph.layers[-1])
        monitor.done()
