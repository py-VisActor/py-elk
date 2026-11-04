# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Worker275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# P18A in references/e13-kernel-sources.json; original native graph views.
"""Full source in-layer reordering and layer/graph extent calculation."""
import math

from ...execution.diagnostics import BasicProgressMonitor
from .graph import Insets, set_layer
from .port_distribution import _maximum, _minimum


def in_layer_constraint_processor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Layer constraint edge reversal', 1)
    for layer in graph.layers:
        insertion_index = -1
        bottom_nodes = []
        nodes = list(layer.nodes)
        for index, node in enumerate(nodes):
            constraint = node.properties.get('IN_LAYER_CONSTRAINT', 'NONE')
            if insertion_index == -1:
                if constraint != 'TOP':
                    insertion_index = index
            elif constraint == 'TOP':
                set_layer(node, None)
                set_layer(node, layer, insertion_index)
                insertion_index += 1
            if constraint == 'BOTTOM':
                bottom_nodes.append(node)
        for node in bottom_nodes:
            set_layer(node, None)
            set_layer(node, layer)
    monitor.done()


def _surrounding_spacing(graph):
    # Actual Core SPACING_PORTS_SURROUNDING_0 / Layered alias is type4.
    # Request only on the source external-boundary branches; cache its fresh
    # zero-margin default on this native holder, not on the raw origin.
    value = graph.properties.get('SPACING_PORTS_SURROUNDING')
    if value is None:
        value = Insets()
        graph.properties['SPACING_PORTS_SURROUNDING'] = value
    return value


def layer_size_and_graph_height_calculator(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Layer size calculation', 1)
    minimum_y, maximum_y = math.inf, -math.inf
    found_nodes = False
    for layer in graph.layers:
        layer.size.x = 0.0
        layer.size.y = 0.0
        if not layer.nodes:
            continue
        found_nodes = True
        for node in layer.nodes:
            width = node.size.x + node.margin.left + node.margin.right
            layer.size.x = _maximum(layer.size.x, width)
        first = layer.nodes[0]
        top = first.pos.y - first.margin.top
        if first.type == 'EXTERNAL_PORT':
            top -= _surrounding_spacing(graph).top
        last = layer.nodes[-1]
        bottom = last.pos.y + last.size.y + last.margin.bottom
        if last.type == 'EXTERNAL_PORT':
            bottom += _surrounding_spacing(graph).bottom
        layer.size.y = bottom - top
        minimum_y = _minimum(minimum_y, top)
        maximum_y = _maximum(maximum_y, bottom)
    if not found_nodes:
        minimum_y = 0.0
        maximum_y = 0.0
    graph.size.y = maximum_y - minimum_y
    graph.offset.y -= minimum_y
    monitor.done()
