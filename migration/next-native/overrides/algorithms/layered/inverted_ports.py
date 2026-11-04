# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P07A in references/e13-kernel-sources.json.
# Standalone processor; crossing/provider scheduling remains separate.
"""Actual inverted-port dummy splitting; full pipeline wiring is separate."""
from .graph import LNode, LPort, LEdge, set_layer, set_port_owner, set_source, set_target
from .ports import is_side_fixed, set_side

def _new_dummy(graph, edge, pending):
    node = LNode(graph, type='LONG_EDGE', properties={'ORIGIN': edge, 'PORT_CONSTRAINTS': 'FIXED_POS'})
    pending.append(node)
    incoming = LPort()
    set_port_owner(incoming, node)
    set_side(incoming, 'WEST')
    outgoing = LPort()
    set_port_owner(outgoing, node)
    set_side(outgoing, 'EAST')
    return (node, incoming, outgoing)

def _new_segment(edge):
    new = LEdge(origin=edge.origin, properties=dict(edge.properties))
    new.properties.pop('JUNCTION_POINTS', None)
    new.labels = []
    return new

def _property_reference(node, key, value):
    if value is None:
        node.properties.pop(key, None)
    else:
        node.properties[key] = value

def _set_long_edge_source_and_target(dummy, incoming, outgoing):
    source = incoming.incoming_edges[0].source
    target = outgoing.outgoing_edges[0].target
    _property_reference(dummy, 'LONG_EDGE_SOURCE', source.owner.properties.get('LONG_EDGE_SOURCE') if source.owner.type == 'LONG_EDGE' else source)
    _property_reference(dummy, 'LONG_EDGE_TARGET', target.owner.properties.get('LONG_EDGE_TARGET') if target.owner.type == 'LONG_EDGE' else target)

def _move_head_labels(edge, new, *, preserve_marker):
    labels = getattr(edge, 'labels', None)
    if labels is None:
        if edge.origin is not None and edge.origin.to_json().get('labels'):
            raise ValueError('Actual native label views are required')
        return
    for label in list(labels):
        if label.properties.get('EDGE_LABELS_PLACEMENT', 'CENTER') == 'HEAD':
            if not preserve_marker or 'END_LABEL_EDGE' not in label.properties:
                label.properties['END_LABEL_EDGE'] = edge
            for index, item in enumerate(labels):
                if item is label:
                    labels.pop(index)
                    break
            new.labels.append(label)

def create_east_port_side_dummies(graph, port, edge, pending):
    if edge.source.owner is port.owner:
        return
    dummy, incoming, outgoing = _new_dummy(graph, edge, pending)
    set_target(edge, incoming)
    new = _new_segment(edge)
    set_source(new, outgoing)
    set_target(new, port)
    _set_long_edge_source_and_target(dummy, incoming, outgoing)
    _move_head_labels(edge, new, preserve_marker=True)

def create_west_port_side_dummies(graph, port, edge, pending):
    if edge.target.owner is port.owner:
        return
    dummy, incoming, outgoing = _new_dummy(graph, edge, pending)
    old_target = edge.target
    set_target(edge, incoming)
    new = _new_segment(edge)
    set_source(new, outgoing)
    set_target(new, old_target)
    _move_head_labels(edge, new, preserve_marker=False)
    _set_long_edge_source_and_target(dummy, incoming, outgoing)

def inverted_port_processor(graph):
    current = None
    pending = []
    for layer in graph.layers:
        previous = current
        current = layer
        for node in pending:
            set_layer(node, previous)
        pending.clear()
        for node in layer.nodes:
            if node.type != 'NORMAL' or not is_side_fixed(node.properties.get('PORT_CONSTRAINTS', 'UNDEFINED')):
                continue
            for port in node.ports:
                if port.incoming_edges and port.side == 'EAST':
                    for edge in list(port.incoming_edges):
                        create_east_port_side_dummies(graph, port, edge, pending)
            for port in node.ports:
                if port.outgoing_edges and port.side == 'WEST':
                    for edge in list(port.outgoing_edges):
                        create_west_port_side_dummies(graph, port, edge, pending)
    for node in pending:
        set_layer(node, current)
