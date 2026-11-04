# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Worker275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# P18D in references/e13-kernel-sources.json; old long_edges.py unchanged.
"""Full source split/join with labels, thickness and typed junction chains."""
import math

from ...execution.diagnostics import BasicProgressMonitor
from ...execution.node_micro import VectorChain
from .graph import LEdge, LNode, LPort, Vec2, set_layer, set_port_owner, set_source, set_target, set_target_and_insert_at_index
from .native_properties import CanonicalPropertyMap
from .orthogonal_general import get_junction_points
from .ports import set_side
from .property_access import read_layered_scalar


def _floor(value):
    if value == 0 or not math.isfinite(value):
        return value
    return float(math.floor(value))


def _absolute_anchor(port):
    # Source sum_0 starts at a new (+0,+0) vector, then adds in this order.
    result = Vec2()
    for value in (port.owner.pos, port.pos, port.anchor):
        result.x += value.x
        result.y += value.y
    return result


def _copy_properties(target, source):
    properties = CanonicalPropertyMap(source.properties,
                                      getattr(source, 'integer_box_identities', None))
    target.properties = properties
    target.integer_box_identities = properties.integer_boxes


def move_head_labels(old, new):
    index = 0
    while index < len(old.labels):
        label = old.labels[index]
        index += 1
        placement = read_layered_scalar(label, 'EDGE_LABELS_PLACEMENT', 'EDGE_LABELS_PLACEMENT')
        if placement == 'HEAD':
            old.labels.pop(index - 1)
            index -= 1
            new.labels.append(label)
            if 'END_LABEL_EDGE' not in label.properties:
                label.properties['END_LABEL_EDGE'] = old


def set_dummy_node_properties(dummy, incoming, outgoing):
    first, last = incoming.source.owner, outgoing.target.owner
    if first.type == 'LONG_EDGE':
        dummy.properties['LONG_EDGE_SOURCE'] = first.properties.get('LONG_EDGE_SOURCE')
        dummy.properties['LONG_EDGE_TARGET'] = first.properties.get('LONG_EDGE_TARGET')
        dummy.properties['LONG_EDGE_HAS_LABEL_DUMMIES'] = first.properties.get('LONG_EDGE_HAS_LABEL_DUMMIES', False)
    elif first.type == 'LABEL':
        dummy.properties['LONG_EDGE_SOURCE'] = first.properties.get('LONG_EDGE_SOURCE')
        dummy.properties['LONG_EDGE_TARGET'] = first.properties.get('LONG_EDGE_TARGET')
        dummy.properties['LONG_EDGE_HAS_LABEL_DUMMIES'] = True
    elif last.type == 'LABEL':
        dummy.properties['LONG_EDGE_SOURCE'] = last.properties.get('LONG_EDGE_SOURCE')
        dummy.properties['LONG_EDGE_TARGET'] = last.properties.get('LONG_EDGE_TARGET')
        dummy.properties['LONG_EDGE_HAS_LABEL_DUMMIES'] = True
    else:
        dummy.properties['LONG_EDGE_SOURCE'] = incoming.source
        dummy.properties['LONG_EDGE_TARGET'] = outgoing.target


def split_edge(edge, dummy):
    old_target = edge.target
    thickness = read_layered_scalar(edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0')
    if thickness < 0:
        thickness = 0.0
        edge.properties['EDGE_THICKNESS'] = thickness
    dummy.size.y = thickness
    position = _floor(thickness / 2)
    incoming = LPort()
    incoming.properties = CanonicalPropertyMap()
    incoming.integer_box_identities = incoming.properties.integer_boxes
    incoming.labels = []
    set_side(incoming, 'WEST')
    set_port_owner(incoming, dummy)
    incoming.pos.y = position
    outgoing = LPort()
    outgoing.properties = CanonicalPropertyMap()
    outgoing.integer_box_identities = outgoing.properties.integer_boxes
    outgoing.labels = []
    set_side(outgoing, 'EAST')
    set_port_owner(outgoing, dummy)
    outgoing.pos.y = position
    set_target(edge, incoming)
    generated = LEdge()
    generated.labels = []
    _copy_properties(generated, edge)
    generated.properties['JUNCTION_POINTS'] = None
    set_source(generated, outgoing)
    set_target(generated, old_target)
    set_dummy_node_properties(dummy, edge, generated)
    move_head_labels(edge, generated)
    return generated


def long_edge_splitter(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Edge splitting', 1)
    if len(graph.layers) <= 2:
        monitor.done()
        return
    next_layer = graph.layers[0]
    layer_index = 1
    while layer_index < len(graph.layers):
        layer = next_layer
        next_layer = graph.layers[layer_index]
        layer_index += 1
        for node in layer.nodes:
            for port in node.ports:
                for edge in port.outgoing_edges:
                    target_layer = edge.target.owner.layer
                    if target_layer is not layer and target_layer is not next_layer:
                        dummy = LNode(graph, type='LONG_EDGE', properties=CanonicalPropertyMap())
                        dummy.integer_box_identities = dummy.properties.integer_boxes
                        dummy.labels = []
                        dummy.properties['ORIGIN'] = edge
                        dummy.properties['PORT_CONSTRAINTS'] = 'FIXED_POS'
                        set_layer(dummy, next_layer)
                        split_edge(edge, dummy)
    monitor.done()


def join_at(dummy, *, add_unnecessary_bendpoints=False):
    incoming = next(port for port in dummy.ports if port.side == 'WEST').incoming_edges
    outgoing = next(port for port in dummy.ports if port.side == 'EAST').outgoing_edges
    count = len(incoming)
    unnecessary = _absolute_anchor(dummy.ports[0])
    while count > 0:
        count -= 1
        surviving, dropped = incoming[0], outgoing[0]
        targets = dropped.target.incoming_edges
        index = next(index for index, edge in enumerate(targets) if edge is dropped)
        set_target_and_insert_at_index(surviving, dropped.target, index)
        set_source(dropped, None)
        set_target(dropped, None)
        if add_unnecessary_bendpoints:
            surviving.bend_points.append(Vec2(unnecessary.x, unnecessary.y))
        for point in dropped.bend_points:
            surviving.bend_points.append(Vec2(point.x, point.y))
        for label in dropped.labels:
            surviving.labels.append(label)
        surviving_junctions = get_junction_points(surviving)
        dropped_junctions = get_junction_points(dropped)
        if dropped_junctions is not None:
            if surviving_junctions is None:
                surviving_junctions = VectorChain()
                surviving.properties['JUNCTION_POINTS'] = surviving_junctions
            for point in dropped_junctions:
                surviving_junctions.append(Vec2(point.x, point.y))


def long_edge_joiner(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Edge joining', 1)
    unnecessary = read_layered_scalar(graph, 'UNNECESSARY_BENDPOINTS', 'UNNECESSARY_BENDPOINTS_0')
    for layer in graph.layers:
        index = 0
        while index < len(layer.nodes):
            node = layer.nodes[index]
            index += 1
            if node.type == 'LONG_EDGE':
                join_at(node, add_unnecessary_bendpoints=unnecessary)
                layer.nodes.pop(index - 1)
                index -= 1
    monitor.done()
