# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P26A source-approved insertion/removal.
"""Real center-label dummy insertion and removal over native graph objects."""
from ...execution.diagnostics import BasicProgressMonitor
from .cell_layout import _maximum
from .graph import LNode, Vec2
from .long_edges_general import _floor, join_at, split_edge
from .native_properties import CanonicalPropertyMap
from .property_access import read_layered_scalar


def _outgoing(node):
    for port in node.ports:
        yield from port.outgoing_edges


def _placement(label):
    return read_layered_scalar(label, 'EDGE_LABELS_PLACEMENT', 'EDGE_LABELS_PLACEMENT')


def _all_inline(labels):
    return all(read_layered_scalar(label, 'EDGE_LABELS_INLINE', 'EDGE_LABELS_INLINE_0')
               for label in labels)


def retrieve_thickness(edge):
    thickness = read_layered_scalar(edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0')
    if thickness < 0:
        thickness = 0.0
        edge.properties['EDGE_THICKNESS'] = thickness
    return thickness


def create_label_dummy(graph, edge, thickness, represented_labels):
    dummy = LNode(graph, type='LABEL', properties=CanonicalPropertyMap())
    dummy.integer_box_identities = dummy.properties.integer_boxes
    dummy.properties['ORIGIN'] = edge
    dummy.properties['REPRESENTED_LABELS'] = represented_labels
    dummy.properties['PORT_CONSTRAINTS'] = 'FIXED_POS'
    dummy.properties['LONG_EDGE_SOURCE'] = edge.source
    dummy.properties['LONG_EDGE_TARGET'] = edge.target
    split_edge(edge, dummy)
    port_y = _floor(thickness / 2)
    for port in dummy.ports:
        port.pos.y = port_y
    return dummy


def label_dummy_inserter(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Label dummy insertions', 1)
    new_dummies = []
    edge_spacing = read_layered_scalar(graph, 'SPACING_EDGE_LABEL', 'SPACING_EDGE_LABEL_0')
    label_spacing = read_layered_scalar(graph, 'SPACING_LABEL_LABEL', 'SPACING_LABEL_LABEL')
    direction = read_layered_scalar(graph, 'DIRECTION', 'DIRECTION')
    vertical = direction in ('UP', 'DOWN')
    for node in graph.layerless_nodes:
        for edge in _outgoing(node):
            if edge.source.owner is edge.target.owner or not any(
                    _placement(label) == 'CENTER' for label in edge.labels):
                continue
            thickness = retrieve_thickness(edge)
            represented = []
            dummy = create_label_dummy(graph, edge, thickness, represented)
            new_dummies.append(dummy)
            size = dummy.size
            index = 0
            while index < len(edge.labels):
                label = edge.labels[index]
                index += 1
                if _placement(label) == 'CENTER':
                    if vertical:
                        size.x += label.size.x + label_spacing
                        size.y = _maximum(size.y, label.size.y)
                    else:
                        size.x = _maximum(size.x, label.size.x)
                        size.y += label.size.y + label_spacing
                    represented.append(label)
                    edge.labels.pop(index - 1)
                    index -= 1
            if vertical:
                size.x -= label_spacing
                size.y += edge_spacing + thickness
            else:
                size.y += (edge_spacing - label_spacing) + thickness
    graph.layerless_nodes.extend(new_dummies)
    monitor.done()


def place_horizontal(labels, label_pos, label_spacing, label_space):
    for label in labels:
        label.pos.x = label_pos.x + (label_space.x - label.size.x) / 2
        label.pos.y = label_pos.y
        label_pos.y += label.size.y + label_spacing


def place_vertical(labels, label_pos, label_spacing, label_space, left_aligned, direction):
    inline = _all_inline(labels)
    effective = reversed(labels) if direction == 'UP' else labels
    for label in effective:
        label.pos.x = label_pos.x
        if inline:
            label.pos.y = label_pos.y + (label_space.y - label.size.y) / 2
        elif left_aligned:
            label.pos.y = label_pos.y
        else:
            label.pos.y = label_pos.y + label_space.y - label.size.y
        label_pos.x += label.size.x + label_spacing


def label_dummy_remover(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Label dummy removal', 1)
    edge_spacing = read_layered_scalar(graph, 'SPACING_EDGE_LABEL', 'SPACING_EDGE_LABEL_0')
    label_spacing = read_layered_scalar(graph, 'SPACING_LABEL_LABEL', 'SPACING_LABEL_LABEL')
    direction = read_layered_scalar(graph, 'DIRECTION', 'DIRECTION')
    for layer in graph.layers:
        index = 0
        while index < len(layer.nodes):
            node = layer.nodes[index]
            index += 1
            if node.type == 'LABEL':
                edge = node.properties.get('ORIGIN')
                thickness = read_layered_scalar(edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0')
                below = node.properties.get('LABEL_SIDE') == 'BELOW'
                position = Vec2(node.pos.x, node.pos.y)
                if below:
                    position.y += thickness + edge_spacing
                represented = node.properties.get('REPRESENTED_LABELS')
                space = Vec2(node.size.x, node.size.y + (
                    0 if _all_inline(represented) else (-thickness) - edge_spacing))
                # Source reads the property again after the inline-space query.
                represented = node.properties.get('REPRESENTED_LABELS')
                if direction in ('UP', 'DOWN'):
                    place_vertical(represented, position, label_spacing, space, below, direction)
                else:
                    place_horizontal(represented, position, label_spacing, space)
                edge.labels.extend(represented)
                join_at(node, add_unnecessary_bendpoints=(
                    read_layered_scalar(graph, 'EDGE_ROUTING', 'EDGE_ROUTING') == 'POLYLINE'))
                layer.nodes.pop(index - 1)
                index -= 1
    monitor.done()
