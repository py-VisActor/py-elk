# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P22A native hierarchy resize source.
"""Transfer child layout to its actual native parent without raw JSON rules."""
from .cell_layout import _maximum
from .graph import LPort, Vec2
from .graph_configurator import _graph_of
from .native_adapters import _read_property
from .native_transfer import ElkGraphLayoutTransferrer
from .ports import _divide, set_side
from .resize_general import clear_layers, resize_graph_no_really


def resize_native_node(node, new_size, move_ports):
    old = Vec2(node.size.x, node.size.y)
    width_ratio = _divide(new_size.x, old.x)
    height_ratio = _divide(new_size.y, old.y)
    width_diff = new_size.x - old.x
    height_diff = new_size.y - old.y
    if move_ports:
        fixed = _read_property(node, 'PORT_CONSTRAINTS') == 'FIXED_POS'
        for port in node.ports:
            if port.side == 'NORTH':
                if not fixed:
                    port.pos.x *= width_ratio
            elif port.side == 'EAST':
                port.pos.x += width_diff
                if not fixed:
                    port.pos.y *= height_ratio
            elif port.side == 'SOUTH':
                if not fixed:
                    port.pos.x *= width_ratio
                port.pos.y += height_diff
            elif port.side == 'WEST' and not fixed:
                port.pos.y *= height_ratio
    for label in node.labels:
        mid_x = label.pos.x + label.size.x / 2
        mid_y = label.pos.y + label.size.y / 2
        width_percent = _divide(mid_x, old.x)
        height_percent = _divide(mid_y, old.y)
        if width_percent + height_percent >= 1:
            if width_percent - height_percent > 0 and mid_y >= 0:
                label.pos.x += width_diff
                label.pos.y += height_diff * height_percent
            elif width_percent - height_percent < 0 and mid_x >= 0:
                label.pos.x += width_diff * width_percent
                label.pos.y += height_diff
    node.size.x, node.size.y = new_size.x, new_size.y
    node.properties['NODE_SIZE_CONSTRAINTS'] = set()


def graph_layout_to_node(node, graph):
    for child in graph.layerless_nodes:
        origin = child.properties.get('ORIGIN')
        if isinstance(origin, LPort):
            position = ElkGraphLayoutTransferrer.external_port_position(
                graph, child, origin.size.x, origin.size.y)
            origin.pos.x, origin.pos.y = position.x, position.y
            set_side(origin, _read_property(child, 'EXT_PORT_SIDE'))
    size = Vec2(graph.size.x + graph.padding.left + graph.padding.right,
                graph.size.y + graph.padding.top + graph.padding.bottom)
    if 'EXTERNAL_PORTS' in _read_property(graph, 'GRAPH_PROPERTIES'):
        node.properties['PORT_CONSTRAINTS'] = 'FIXED_POS'
        _read_property(_graph_of(node), 'GRAPH_PROPERTIES').add('NON_FREE_PORTS')
        resize_native_node(node, size, False)
    else:
        resize_native_node(node, size, True)


def resize_hierarchical_graph(graph):
    constraints = _read_property(graph, 'NODE_SIZE_CONSTRAINTS')
    options = _read_property(graph, 'NODE_SIZE_OPTIONS')
    calculated = Vec2(graph.size.x + graph.padding.left + graph.padding.right,
                      graph.size.y + graph.padding.top + graph.padding.bottom)
    adjusted = Vec2(calculated.x, calculated.y)
    if 'MINIMUM_SIZE' in constraints:
        minimum = _read_property(graph, 'NODE_SIZE_MINIMUM')
        if 'DEFAULT_MINIMUM_SIZE' in options:
            if minimum.x <= 0:
                minimum.x = 20.0
            if minimum.y <= 0:
                minimum.y = 20.0
        adjusted.x = _maximum(calculated.x, minimum.x)
        adjusted.y = _maximum(calculated.y, minimum.y)
    # This source variant always resizes, including fixedGraphSize=true.
    resize_graph_no_really(graph, calculated, adjusted)


def hierarchical_node_resizing_processor(graph, *, monitor):
    monitor.begin('Resize child graph to fit parent.', 1)
    clear_layers(graph)
    resize_hierarchical_graph(graph)
    parent = getattr(graph, 'parent_node', None)
    if parent is not None:
        graph_layout_to_node(parent, graph)
    monitor.done()
