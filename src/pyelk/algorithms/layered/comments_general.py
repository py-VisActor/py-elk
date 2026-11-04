# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; actual Comment pre/margin/post source blocks.
"""Actual comment-box topology, spacing, margin and port placement."""
from ...execution.diagnostics import BasicProgressMonitor
from .cell_layout import _maximum
from .cycles_general import reverse_edge
from .graph import _remove_identity, set_port_owner, set_source, set_target
from .ports import is_side_fixed
from .property_access import read_layered_scalar
from .spacings import _double, _property, get_individual_or_default


_COMMENT_COMMENT = _property('SPACING_COMMENT_COMMENT')
_COMMENT_NODE = _property('SPACING_COMMENT_NODE')


def _is_comment(node):
    value = read_layered_scalar(node, 'COMMENT_BOX', 'COMMENT_BOX')
    if type(value) is not bool:
        raise TypeError('Actual COMMENT_BOX Boolean required')
    return value


def _spacing(node, descriptor):
    return _double(get_individual_or_default(node, descriptor))


def process_comments(node):
    margin = node.margin
    top = node.properties.get('TOP_COMMENTS')
    bottom = node.properties.get('BOTTOM_COMMENTS')
    if top is None and bottom is None:
        return
    comment_spacing = _spacing(node, _COMMENT_COMMENT)
    node_spacing = _spacing(node, _COMMENT_NODE)
    top_width = 0.0
    if top is not None:
        max_height = 0.0
        for box in top:
            max_height = _maximum(max_height, box.size.y)
            top_width += box.size.x
        top_width += comment_spacing * (len(top) - 1)
        margin.top += max_height + node_spacing
    bottom_width = 0.0
    if bottom is not None:
        max_height = 0.0
        for box in bottom:
            max_height = _maximum(max_height, box.size.y)
            bottom_width += box.size.x
        bottom_width += comment_spacing * (len(bottom) - 1)
        margin.bottom += max_height + node_spacing
    width = _maximum(top_width, bottom_width)
    if width > node.size.x:
        protrusion = (width - node.size.x) / 2
        margin.left = _maximum(margin.left, protrusion)
        margin.right = _maximum(margin.right, protrusion)


def comment_node_margin_calculator(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Node margin calculation', 1)
    for layer in graph.layers:
        for node in layer.nodes:
            process_comments(node)
    monitor.done()


def get_box_port(box):
    node_port = box.properties.get('COMMENT_CONN_PORT')
    for port in box.ports:
        for edge in port.outgoing_edges:
            set_target(edge, node_port)
            return port
        for edge in port.incoming_edges:
            set_source(edge, node_port)
            return port
    return None


def place_comment_boxes(node, top, bottom):
    position, size, margin = node.pos, node.size, node.margin
    comment_spacing = _spacing(node, _COMMENT_COMMENT)
    if top is not None:
        width = comment_spacing * (len(top) - 1)
        max_height = 0.0
        for box in top:
            width += box.size.x
            max_height = _maximum(max_height, box.size.y)
        x = position.x - (width - size.x) / 2
        baseline = (position.y - margin.top) + max_height
        increment = size.x / (len(top) + 1)
        anchor_x = increment
        for box in top:
            box.pos.x = x
            box.pos.y = baseline - box.size.y
            x += box.size.x + comment_spacing
            box_port = get_box_port(box)
            box_port.pos.x = box.size.x / 2 - box_port.anchor.x
            box_port.pos.y = box.size.y
            node_port = box.properties.get('COMMENT_CONN_PORT')
            if len(node_port.incoming_edges) + len(node_port.outgoing_edges) == 1:
                node_port.pos.x = anchor_x - node_port.anchor.x
                node_port.pos.y = 0.0
                set_port_owner(node_port, node)
            anchor_x += increment
    if bottom is not None:
        width = comment_spacing * (len(bottom) - 1)
        max_height = 0.0
        for box in bottom:
            width += box.size.x
            max_height = _maximum(max_height, box.size.y)
        x = position.x - (width - size.x) / 2
        baseline = ((position.y + size.y) + margin.bottom) - max_height
        increment = size.x / (len(bottom) + 1)
        anchor_x = increment
        for box in bottom:
            box.pos.x = x
            box.pos.y = baseline
            x += box.size.x + comment_spacing
            box_port = get_box_port(box)
            box_port.pos.x = box.size.x / 2 - box_port.anchor.x
            box_port.pos.y = 0.0
            node_port = box.properties.get('COMMENT_CONN_PORT')
            if len(node_port.incoming_edges) + len(node_port.outgoing_edges) == 1:
                node_port.pos.x = anchor_x - node_port.anchor.x
                node_port.pos.y = size.y
                set_port_owner(node_port, node)
            anchor_x += increment


def comment_postprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Comment post-processing', 1)
    for layer in graph.layers:
        boxes = []
        for node in layer.nodes:
            top = node.properties.get('TOP_COMMENTS')
            bottom = node.properties.get('BOTTOM_COMMENTS')
            if top is not None or bottom is not None:
                place_comment_boxes(node, top, bottom)
                if top is not None:
                    boxes.extend(top)
                if bottom is not None:
                    boxes.extend(bottom)
        # Actual Source appends only; hidden box.layer/graph and lists stay.
        layer.nodes.extend(boxes)
    monitor.done()


def remove_hierarchical_port_dummy_node(opposite_port):
    dummy = opposite_port.properties.get('PORT_DUMMY')
    if dummy is not None:
        layer = dummy.layer
        _remove_identity(layer.nodes, dummy)
        if len(layer.nodes) == 0:
            graph = dummy.graph if dummy.graph is not None else dummy.layer.graph
            _remove_identity(graph.layers, layer)


def _neighbor_ports(port):
    for edge in port.incoming_edges:
        yield edge.source
    for edge in port.outgoing_edges:
        yield edge.target


def process_box(box, edge, opposite_port, real_node):
    only_top = only_bottom = False
    constraints = read_layered_scalar(real_node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
    if is_side_fixed(constraints):
        north = south = False
        stop = False
        for port in real_node.ports:
            for neighbor in _neighbor_ports(port):
                if not _is_comment(neighbor.owner):
                    if port.side == 'NORTH':
                        north = True
                        stop = True
                        break
                    if port.side == 'SOUTH':
                        south = True
                        stop = True
                        break
            if stop:
                break
        only_top = south and not north
        only_bottom = north and not south
    if not only_top and not only_bottom and len(real_node.labels) != 0:
        label_position = 0.0
        for label in real_node.labels:
            label_position += label.pos.y + label.size.y / 2
        label_position /= len(real_node.labels)
        top_first = label_position >= real_node.size.y / 2
    else:
        top_first = not only_bottom
    if top_first:
        top = real_node.properties.get('TOP_COMMENTS')
        if top is None:
            selected = []
            real_node.properties['TOP_COMMENTS'] = selected
        elif only_top:
            selected = top
        else:
            bottom = real_node.properties.get('BOTTOM_COMMENTS')
            if bottom is None:
                selected = []
                real_node.properties['BOTTOM_COMMENTS'] = selected
            else:
                selected = top if len(top) <= len(bottom) else bottom
    else:
        bottom = real_node.properties.get('BOTTOM_COMMENTS')
        if bottom is None:
            selected = []
            real_node.properties['BOTTOM_COMMENTS'] = selected
        elif only_bottom:
            selected = bottom
        else:
            top = real_node.properties.get('TOP_COMMENTS')
            if top is None:
                selected = []
                real_node.properties['TOP_COMMENTS'] = selected
            else:
                selected = bottom if len(bottom) <= len(top) else top
    selected.append(box)
    box.properties['COMMENT_CONN_PORT'] = opposite_port
    if edge.target is opposite_port:
        set_target(edge, None)
        if len(opposite_port.incoming_edges) + len(opposite_port.outgoing_edges) == 0:
            set_port_owner(opposite_port, None)
        remove_hierarchical_port_dummy_node(opposite_port)
    else:
        set_source(edge, None)
        if len(opposite_port.incoming_edges) + len(opposite_port.outgoing_edges) == 0:
            set_port_owner(opposite_port, None)
    edge.bend_points.clear()


def comment_preprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Comment pre-processing', 1)
    comment_count = 0
    index = 0
    while index < len(graph.layerless_nodes):
        node = graph.layerless_nodes[index]
        index += 1
        if _is_comment(node):
            comment_count += 1
            count = 0
            edge = opposite = None
            for port in node.ports:
                count += len(port.incoming_edges) + len(port.outgoing_edges)
                if len(port.incoming_edges) == 1:
                    edge = port.incoming_edges[0]
                    opposite = edge.source
                if len(port.outgoing_edges) == 1:
                    edge = port.outgoing_edges[0]
                    opposite = edge.target
            if (count == 1 and len(opposite.incoming_edges) + len(opposite.outgoing_edges) == 1
                    and not _is_comment(opposite.owner)):
                process_box(node, edge, opposite, opposite.owner)
                graph.layerless_nodes.pop(index - 1)
                index -= 1
            else:
                reverse = []
                for port in node.ports:
                    for outgoing in port.outgoing_edges:
                        if len(outgoing.target.outgoing_edges) != 0:
                            reverse.append(outgoing)
                    for incoming in port.incoming_edges:
                        if len(incoming.source.incoming_edges) != 0:
                            reverse.append(incoming)
                for edge in reverse:
                    reverse_edge(edge, True)
    if monitor.record_logs:
        monitor.log('Found ' + str(comment_count) + ' comment boxes')
    monitor.done()
