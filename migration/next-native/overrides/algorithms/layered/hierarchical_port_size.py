# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P22C actual north/south dummy sizes.
"""Actual hierarchy dummy width ramp over physical side-filtered ports."""
from .property_access import read_layered_scalar


def set_widths(nodes, top_down, delta):
    width = 0.0
    step = delta
    if not top_down:
        width = delta * (len(nodes) - 1)
        step *= -1
    for node in nodes:
        node.properties['ALIGNMENT'] = 'CENTER'
        node.size.x = width
        for port in node.ports:
            if port.side == 'EAST':
                port.pos.x = width
        width += step


def hierarchical_port_dummy_size_processor(graph, *, monitor):
    monitor.begin('Hierarchical port dummy size processing', 1)
    northern, southern = [], []
    spacing = read_layered_scalar(graph, 'SPACING_EDGE_EDGE_BETWEEN_LAYERS',
                                  'SPACING_EDGE_EDGE_BETWEEN_LAYERS_0')
    delta = spacing * 2
    for layer in graph.layers:
        northern.clear()
        southern.clear()
        for node in layer.nodes:
            if node.type == 'EXTERNAL_PORT':
                side = node.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
                if side == 'NORTH':
                    northern.append(node)
                elif side == 'SOUTH':
                    southern.append(node)
        set_widths(northern, True, delta)
        set_widths(southern, False, delta)
    monitor.done()
