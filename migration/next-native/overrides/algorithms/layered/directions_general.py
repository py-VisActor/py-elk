# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P23A general caller plus P05B02 exact math.
"""Actual GraphTransformer over produced native shapes, with no slice guard.

The legacy directions.py and its historical bounded checks remain unchanged.
Source arithmetic is reused verbatim; typed property/Integer adapters are explicit.
"""
from .graph import Vec2
from .cell_layout import _maximum
from .integer_box_tokens import value_of_integer_box
from .native_adapters import _read_property
from .orthogonal_general import get_junction_points
from .ports import set_side as _source_set_side
from .property_access import read_layered_scalar


def _labels(shape):
    return shape.labels


def get_node_labels_padding(shape):
    return _read_property(shape, 'NODE_LABELS_PADDING')


def get_node_size_minimum(node):
    return _read_property(node, 'NODE_SIZE_MINIMUM')


def _negate_port_index(port, index):
    value = -index
    token = value_of_integer_box(value)
    if hasattr(port.properties, 'set_property'):
        port.properties.set_property('PORT_INDEX', value, integer_box=token)
    else:
        port.properties['PORT_INDEX'] = value
        if not hasattr(port, 'integer_box_identities'):
            port.integer_box_identities = {}
        port.integer_box_identities['PORT_INDEX'] = token


def _mirror_insets(value, axis):
    if axis == 'x':
        value.left, value.right = (value.right, value.left)
    else:
        value.top, value.bottom = (value.bottom, value.top)

def _mirror_placement(shape, axis):
    placement = shape.properties.get('NODE_LABELS_PLACEMENT')
    if placement is None:
        return
    first, second = ('H_LEFT', 'H_RIGHT') if axis == 'x' else ('V_TOP', 'V_BOTTOM')
    if first in placement:
        placement.remove(first)
        placement.add(second)
    elif second in placement:
        placement.remove(second)
        placement.add(first)

def _mirror_layer_constraint_x(node):
    constraint = node.properties.get('LAYER_CONSTRAINT', 'NONE')
    if constraint in {'FIRST', 'FIRST_SEPARATE', 'LAST', 'LAST_SEPARATE'}:
        node.properties['LAYER_CONSTRAINT'] = {'FIRST': 'LAST', 'FIRST_SEPARATE': 'LAST_SEPARATE', 'LAST': 'FIRST', 'LAST_SEPARATE': 'FIRST_SEPARATE'}[constraint]

def _mirror_in_layer_constraint_y(node):
    constraint = node.properties.get('IN_LAYER_CONSTRAINT', 'NONE')
    if constraint in {'TOP', 'BOTTOM'}:
        node.properties['IN_LAYER_CONSTRAINT'] = {'TOP': 'BOTTOM', 'BOTTOM': 'TOP'}[constraint]

def _mirror(graph, nodes, axis):
    offset = 0
    if getattr(graph.size, axis) == 0:
        for node in nodes:
            margin = node.margin.right if axis == 'x' else node.margin.bottom
            offset = _maximum(offset, getattr(node.pos, axis) + getattr(node.size, axis) + margin)
    else:
        offset = getattr(graph.size, axis) - getattr(graph.offset, axis)
    offset -= getattr(graph.offset, axis)
    sides = {'EAST': 'WEST', 'WEST': 'EAST'} if axis == 'x' else {'NORTH': 'SOUTH', 'SOUTH': 'NORTH'}
    for node in nodes:
        setattr(node.pos, axis, offset - getattr(node.size, axis) - getattr(node.pos, axis))
        _mirror_insets(node.padding, axis)
        _mirror_placement(node, axis)
        if 'POSITION' in node.properties:
            value = node.properties['POSITION']
            setattr(value, axis, offset - getattr(node.size, axis) - getattr(value, axis))
        alignment = node.properties.get('ALIGNMENT', 'AUTOMATIC')
        alignments = {'LEFT': 'RIGHT', 'RIGHT': 'LEFT'} if axis == 'x' else {'TOP': 'BOTTOM', 'BOTTOM': 'TOP'}
        if alignment in alignments:
            node.properties['ALIGNMENT'] = alignments[alignment]
        for port in node.ports:
            setattr(port.pos, axis, getattr(node.size, axis) - getattr(port.size, axis) - getattr(port.pos, axis))
            setattr(port.anchor, axis, getattr(port.size, axis) - getattr(port.anchor, axis))
            _source_set_side(port, sides.get(port.side, port.side))
            index = _read_property(port, 'PORT_INDEX')
            if index is not None:
                _negate_port_index(port, index)
            for edge in port.outgoing_edges:
                for point in edge.bend_points:
                    setattr(point, axis, offset - getattr(point, axis))
                for point in get_junction_points(edge):
                    setattr(point, axis, offset - getattr(point, axis))
                for label in _labels(edge):
                    setattr(label.pos, axis, offset - getattr(label.size, axis) - getattr(label.pos, axis))
            for label in _labels(port):
                setattr(label.pos, axis, getattr(port.size, axis) - getattr(label.size, axis) - getattr(label.pos, axis))
        if node.type == 'EXTERNAL_PORT':
            side = _read_property(node, 'EXT_PORT_SIDE')
            node.properties['EXT_PORT_SIDE'] = sides.get(side, side)
            (_mirror_layer_constraint_x if axis == 'x' else _mirror_in_layer_constraint_y)(node)
        for label in _labels(node):
            _mirror_placement(label, axis)
            setattr(label.pos, axis, getattr(node.size, axis) - getattr(label.size, axis) - getattr(label.pos, axis))
    _mirror_insets(graph.padding, axis)
    _mirror_insets(get_node_labels_padding(graph), axis)

def _transpose_vector(value):
    value.x, value.y = (value.y, value.x)

def _transpose_insets(value):
    value.top, value.bottom, value.left, value.right = (value.left, value.right, value.top, value.bottom)

def _transpose_placement(shape):
    old = shape.properties.get('NODE_LABELS_PLACEMENT')
    if not old:
        return
    result = {'INSIDE' if 'INSIDE' in old else 'OUTSIDE'}
    if 'H_PRIORITY' not in old:
        result.add('H_PRIORITY')
    for first, second in (('H_LEFT', 'V_TOP'), ('H_CENTER', 'V_CENTER'), ('H_RIGHT', 'V_BOTTOM')):
        if first in old:
            result.add(second)
            break
    for first, second in (('V_TOP', 'H_LEFT'), ('V_CENTER', 'H_CENTER'), ('V_BOTTOM', 'H_RIGHT')):
        if first in old:
            result.add(second)
            break
    shape.properties['NODE_LABELS_PLACEMENT'] = result

def _transpose_layer_constraint(node):
    layer = node.properties.get('LAYER_CONSTRAINT', 'NONE')
    inside = node.properties.get('IN_LAYER_CONSTRAINT', 'NONE')
    if layer in {'FIRST_SEPARATE', 'LAST_SEPARATE'}:
        node.properties['LAYER_CONSTRAINT'] = 'NONE'
        node.properties['IN_LAYER_CONSTRAINT'] = 'TOP' if layer == 'FIRST_SEPARATE' else 'BOTTOM'
    elif inside in {'TOP', 'BOTTOM'}:
        node.properties['LAYER_CONSTRAINT'] = 'FIRST_SEPARATE' if inside == 'TOP' else 'LAST_SEPARATE'
        node.properties['IN_LAYER_CONSTRAINT'] = 'NONE'

def _transpose(graph, nodes):
    sides = {'NORTH': 'WEST', 'WEST': 'NORTH', 'SOUTH': 'EAST', 'EAST': 'SOUTH', 'UNDEFINED': 'UNDEFINED'}
    for node in nodes:
        _transpose_vector(node.pos)
        _transpose_vector(node.size)
        _transpose_insets(node.padding)
        _transpose_placement(node)
        minimum = get_node_size_minimum(node)
        node.properties['NODE_SIZE_MINIMUM'] = Vec2(minimum.y, minimum.x)
        alignment = node.properties.get('ALIGNMENT', 'AUTOMATIC')
        if alignment in {'LEFT', 'RIGHT', 'TOP', 'BOTTOM'}:
            node.properties['ALIGNMENT'] = {'LEFT': 'TOP', 'RIGHT': 'BOTTOM', 'TOP': 'LEFT', 'BOTTOM': 'RIGHT'}[alignment]
        if 'POSITION' in node.properties:
            _transpose_vector(node.properties['POSITION'])
        for port in node.ports:
            _transpose_vector(port.pos)
            _transpose_vector(port.anchor)
            _transpose_vector(port.size)
            _source_set_side(port, sides[port.side])
            index = _read_property(port, 'PORT_INDEX')
            if index is not None:
                _negate_port_index(port, index)
            for edge in port.outgoing_edges:
                for point in edge.bend_points:
                    _transpose_vector(point)
                for point in get_junction_points(edge):
                    _transpose_vector(point)
                for label in _labels(edge):
                    _transpose_vector(label.pos)
                    _transpose_vector(label.size)
            for label in _labels(port):
                _transpose_vector(label.pos)
                _transpose_vector(label.size)
        if node.type == 'EXTERNAL_PORT':
            node.properties['EXT_PORT_SIDE'] = sides[_read_property(node, 'EXT_PORT_SIDE')]
            _transpose_layer_constraint(node)
        for label in _labels(node):
            _transpose_placement(label)
            _transpose_vector(label.size)
            _transpose_vector(label.pos)
    old = graph.properties.get('EDGE_LABELS_SIDE_SELECTION', 'SMART_DOWN')
    graph.properties['EDGE_LABELS_SIDE_SELECTION'] = {'ALWAYS_UP': 'ALWAYS_DOWN', 'ALWAYS_DOWN': 'ALWAYS_UP', 'DIRECTION_UP': 'DIRECTION_DOWN', 'DIRECTION_DOWN': 'DIRECTION_UP', 'SMART_UP': 'SMART_DOWN', 'SMART_DOWN': 'SMART_UP'}[old]
    _transpose_vector(graph.offset)
    _transpose_vector(graph.size)
    _transpose_insets(graph.padding)
    _transpose_insets(get_node_labels_padding(graph))

class GraphTransformer:
    source_name = 'GraphTransformer'

    def __init__(self, mode):
        self.mode = mode

    def get_layout_processor_configuration(self, graph):
        return None

    def process(self, graph, monitor):
        name = 'null' if self.mode is None else str(self.mode)
        monitor.begin('Graph transformation (' + name + ')', 1)
        nodes = list(graph.layerless_nodes)
        for layer in graph.layers:
            nodes.extend(layer.nodes)
        congruency = read_layered_scalar(graph, 'DIRECTION_CONGRUENCY', 'DIRECTION_CONGRUENCY_0')
        direction = read_layered_scalar(graph, 'DIRECTION', 'DIRECTION')
        internal = self.mode == 'TO_INTERNAL_LTR'
        if congruency == 'READING_DIRECTION':
            if direction == 'LEFT':
                _mirror(graph, nodes, 'x')
            elif direction == 'DOWN':
                _transpose(graph, nodes)
            elif direction == 'UP':
                if internal:
                    _transpose(graph, nodes)
                    _mirror(graph, nodes, 'y')
                else:
                    _mirror(graph, nodes, 'y')
                    _transpose(graph, nodes)
        elif internal:
            if direction == 'LEFT':
                _mirror(graph, nodes, 'x')
                _mirror(graph, nodes, 'y')
            elif direction == 'DOWN':
                _transpose(graph, nodes)
                _mirror(graph, nodes, 'x')
            elif direction == 'UP':
                _mirror(graph, nodes, 'x')
                _transpose(graph, nodes)
        elif direction == 'LEFT':
            _mirror(graph, nodes, 'x')
            _mirror(graph, nodes, 'y')
        elif direction == 'DOWN':
            _mirror(graph, nodes, 'x')
            _transpose(graph, nodes)
        elif direction == 'UP':
            _transpose(graph, nodes)
            _mirror(graph, nodes, 'x')
        monitor.done()
