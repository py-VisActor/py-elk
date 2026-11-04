# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P22D actual fixed-ratio/position coordinates.
"""Actual east/west hierarchy port positioning before edge routing."""
from .graph import Vec2
from .graph_configurator import _graph_of
from .property_access import read_layered_scalar


def border_to_content_coordinates(node, horizontal, vertical):
    graph = _graph_of(node)
    padding, offset, position = graph.padding, graph.offset, node.pos
    if horizontal:
        position.x = position.x - padding.left - offset.x
    if vertical:
        position.y = position.y - padding.top - offset.y


def fix_coordinates(layer, graph):
    constraints = read_layered_scalar(graph, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
    if constraints not in ('FIXED_RATIO', 'FIXED_POS'):
        return
    height = Vec2(graph.size.x + graph.padding.left + graph.padding.right,
                  graph.size.y + graph.padding.top + graph.padding.bottom).y
    for node in layer.nodes:
        if node.type != 'EXTERNAL_PORT':
            continue
        side = node.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
        if side not in ('EAST', 'WEST'):
            continue
        final_y = node.properties.get('PORT_RATIO_OR_POSITION', 0.0)
        if constraints == 'FIXED_RATIO':
            final_y *= height
        node.pos.y = final_y - node.properties.get('PORT_ANCHOR').y
        border_to_content_coordinates(node, False, True)


def hierarchical_port_position_processor(graph, *, monitor):
    monitor.begin('Hierarchical port position processing', 1)
    layers = graph.layers
    if len(layers) > 0:
        fix_coordinates(layers[0], graph)
    if len(layers) > 1:
        fix_coordinates(layers[-1], graph)
    monitor.done()
