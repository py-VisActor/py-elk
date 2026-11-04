# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# E13-P05B source binding: references/e13-kernel-sources.json.
# Exact external Java build identity remains unresolved.
"""Actual intermediate GraphTransformer; no final JSON rotation.

PRE and POST retain their source-defined mode names. Native shape/label views
carry real data; external-port creation and hierarchy drivers are separate.
"""
from __future__ import annotations
import math
from ..._errors import UnsupportedFeatureError
from .graph import Insets, LGraph, LNode, Vec2
from .long_edges import get_junction_points
from .ports import set_side as _source_set_side
from .cell_layout import _maximum
_ASPECT_RATIO_DEFAULT = 1.600000023841858
_DIRECTIONS = {'RIGHT', 'LEFT', 'DOWN', 'UP'}
_SIDES = {'UNDEFINED', 'NORTH', 'EAST', 'SOUTH', 'WEST'}
_ALIGNMENTS = {'AUTOMATIC', 'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'CENTER'}

def _outside(message):
    raise UnsupportedFeatureError('UNSUPPORTED_PHASE_INPUT', '', message)

def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False

def _vector(value):
    return isinstance(value, Vec2) and _finite(value.x) and _finite(value.y)

def _insets(value):
    return isinstance(value, Insets) and all((_finite(getattr(value, k)) for k in ('top', 'right', 'bottom', 'left')))

def resolve_direction(direction):
    if direction == 'UNDEFINED':
        return 'RIGHT' if _ASPECT_RATIO_DEFAULT >= 1 else 'DOWN'
    if direction not in _DIRECTIONS:
        _outside('Unknown layout direction')
    return direction

def from_direction(direction):
    result = {'RIGHT': 'EAST', 'LEFT': 'WEST', 'DOWN': 'SOUTH', 'UP': 'NORTH', 'UNDEFINED': 'UNDEFINED'}
    if direction not in result:
        _outside('Unknown layout direction')
    return result[direction]

def get_node_labels_padding(element):
    if not isinstance(element, (LGraph, LNode)):
        _outside('Label padding requires native property holder')
    value = element.properties.get('NODE_LABELS_PADDING')
    if value is None:
        value = Insets(5, 5, 5, 5)
        element.properties['NODE_LABELS_PADDING'] = value
    if not _insets(value):
        _outside('Label padding must be finite Insets')
    return value

def get_node_size_minimum(node):
    if not isinstance(node, LNode):
        _outside('Minimum size requires native node holder')
    value = node.properties.get('NODE_SIZE_MINIMUM')
    if value is None:
        value = Vec2()
        node.properties['NODE_SIZE_MINIMUM'] = value
    if not _vector(value):
        _outside('Minimum size must be finite Vec2')
    return value

def _labels(shape):
    if not hasattr(shape, 'labels'):
        origin = getattr(shape, 'origin', None)
        if origin is not None and origin.to_json().get('labels'):
            _outside('Labels require actual native shape views')
        return ()
    return shape.labels

def _nodes(graph):
    if not isinstance(graph, LGraph):
        _outside('Direction transformation requires native LGraph')
    nodes = list(graph.layerless_nodes)
    for layer in graph.layers:
        if layer.graph is not graph:
            _outside('Layer graph ownership differs')
        nodes.extend(layer.nodes)
    if len(set(nodes)) != len(nodes):
        _outside('Direction transformation requires distinct native nodes')
    if graph.properties.get('DIRECTION') not in _DIRECTIONS:
        _outside('Direction must be resolved by global prepare')
    if graph.properties.get('DIRECTION_CONGRUENCY', 'READING_DIRECTION') not in {'READING_DIRECTION', 'ROTATION'}:
        _outside('Unknown native direction congruency')
    if not _vector(graph.size) or not _vector(graph.offset) or (not _insets(graph.padding)):
        _outside('Graph frame must be finite')
    if 'NODE_LABELS_PADDING' in graph.properties and (not _insets(graph.properties['NODE_LABELS_PADDING'])):
        _outside('Stored label padding must be finite')
    if graph.properties.get('EDGE_LABELS_SIDE_SELECTION', 'SMART_DOWN') not in {'ALWAYS_UP', 'ALWAYS_DOWN', 'DIRECTION_UP', 'DIRECTION_DOWN', 'SMART_UP', 'SMART_DOWN'}:
        _outside('Unknown native edge-label side selection')
    members, ports, edges = (set(nodes), set(), set())
    for node in nodes:
        if node.graph is not graph:
            _outside('Node graph ownership differs')
        if not all((_vector(v) for v in (node.pos, node.size))) or not all((_insets(v) for v in (node.margin, node.padding))):
            _outside('Node geometry must be finite')
        if node.size.x < 0 or node.size.y < 0:
            _outside('Node size must be nonnegative')
        if node.properties.get('ALIGNMENT', 'AUTOMATIC') not in _ALIGNMENTS:
            _outside('Unknown native alignment')
        if 'POSITION' in node.properties and (not _vector(node.properties['POSITION'])):
            _outside('Native position must be finite Vec2')
        if 'NODE_SIZE_MINIMUM' in node.properties and (not _vector(node.properties['NODE_SIZE_MINIMUM'])):
            _outside('Native minimum must be finite Vec2')
        if node.type == 'EXTERNAL_PORT' and node.properties.get('EXT_PORT_SIDE') not in _SIDES:
            _outside('External-port node requires actual side property')
        for port in node.ports:
            if port in ports or port.owner is not node:
                _outside('Port graph ownership differs')
            ports.add(port)
            if port.side not in _SIDES:
                _outside('Unknown native port side')
            if 'PORT_INDEX' in port.properties and type(port.properties['PORT_INDEX']) is not int:
                _outside('Native port index must be integer')
            if not all((_vector(v) for v in (port.pos, port.size, port.anchor))) or port.size.x < 0 or port.size.y < 0:
                _outside('Port geometry must be finite with nonnegative size')
            for edge in port.outgoing_edges:
                if edge in edges or edge.source is not port or edge.target is None:
                    _outside('Outgoing adjacency differs')
                if edge.target.owner not in members or edge.target not in edge.target.owner.ports or edge not in edge.target.incoming_edges:
                    _outside('Target adjacency differs')
                if not all((_vector(point) for point in edge.bend_points)):
                    _outside('Bends must be native finite vectors')
                if 'JUNCTION_POINTS' in edge.properties and (type(edge.properties['JUNCTION_POINTS']) is not list or not all((_vector(point) for point in edge.properties['JUNCTION_POINTS']))):
                    _outside('Junctions must be native finite vector chain')
                edges.add(edge)
            for edge in port.incoming_edges:
                if edge.target is not port or edge.source is None or edge.source.owner not in members or (edge not in edge.source.outgoing_edges):
                    _outside('Incoming adjacency differs')
    for shape in [*nodes, *ports, *edges]:
        if 'NODE_LABELS_PLACEMENT' in shape.properties:
            placement = shape.properties['NODE_LABELS_PLACEMENT']
            if type(placement) is not set and (type(placement) is not frozenset or placement):
                _outside('Native nonempty label placement requires mutable set')
        for label in _labels(shape):
            if not _vector(label.pos) or not _vector(label.size):
                _outside('Label requires real finite position and size')
    return nodes

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
            if 'PORT_INDEX' in port.properties:
                port.properties['PORT_INDEX'] = -port.properties['PORT_INDEX']
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
            node.properties['EXT_PORT_SIDE'] = sides.get(node.properties['EXT_PORT_SIDE'], node.properties['EXT_PORT_SIDE'])
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
            if 'PORT_INDEX' in port.properties:
                port.properties['PORT_INDEX'] = -port.properties['PORT_INDEX']
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
            node.properties['EXT_PORT_SIDE'] = sides[node.properties['EXT_PORT_SIDE']]
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

def _process(graph, *, to_internal):
    nodes = _nodes(graph)
    direction = graph.properties['DIRECTION']
    reading = graph.properties.get('DIRECTION_CONGRUENCY', 'READING_DIRECTION') == 'READING_DIRECTION'
    if reading:
        if direction == 'LEFT':
            _mirror(graph, nodes, 'x')
        elif direction == 'DOWN':
            _transpose(graph, nodes)
        elif direction == 'UP':
            if to_internal:
                _transpose(graph, nodes)
                _mirror(graph, nodes, 'y')
            else:
                _mirror(graph, nodes, 'y')
                _transpose(graph, nodes)
    elif direction == 'LEFT':
        _mirror(graph, nodes, 'x')
        _mirror(graph, nodes, 'y')
    elif direction == 'DOWN':
        if to_internal:
            _transpose(graph, nodes)
            _mirror(graph, nodes, 'x')
        else:
            _mirror(graph, nodes, 'x')
            _transpose(graph, nodes)
    elif direction == 'UP':
        if to_internal:
            _mirror(graph, nodes, 'x')
            _transpose(graph, nodes)
        else:
            _transpose(graph, nodes)
            _mirror(graph, nodes, 'x')

def direction_preprocessor(graph):
    """Source PRE factory: TO_INPUT_DIRECTION."""
    _process(graph, to_internal=False)

def direction_postprocessor(graph):
    """Source POST factory: TO_INTERNAL_LTR."""
    _process(graph, to_internal=True)
