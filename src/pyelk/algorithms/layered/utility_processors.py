# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 ConstraintsPostprocessor35243, NodePlacementRepeater40145,
# InteractiveExternalPortPositioner38144-38346, original native adapters only.
"""Actual utility processors and interactive external-port coordinate state."""
import math

from ...execution.diagnostics import BasicProgressMonitor
from .cell_layout import _maximum
from .port_label_placement import _minimum
from .graph_info import get_graph_properties
from .integer_box_tokens import value_of_integer_box
from .native_adapters import (_read_property, LGraphAdapter, NodeMarginCalculator,
                              calculate_label_and_node_sizes)
from .property_access import read_layered_scalar


def _set_integer(holder, key, value):
    token = value_of_integer_box(value)
    values = holder.properties
    if hasattr(values, 'set_property'):
        values.set_property(key, value, integer_box=token)
    else:
        values[key] = value
        if not hasattr(holder, 'integer_box_identities'):
            holder.integer_box_identities = {}
        holder.integer_box_identities[key] = token


def constraints_postprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Constraints Postprocessor', 1)
    layer_index = 0
    for layer in graph.layers:
        position = 0
        node_layer = False
        for node in layer.nodes:
            if node.type == 'NORMAL':
                node_layer = True
                _set_integer(node, 'LAYERING_LAYER_ID', layer_index)
                _set_integer(node, 'CROSSING_MINIMIZATION_POSITION_ID', position)
                position += 1
        if node_layer:
            layer_index += 1
    monitor.done()


def node_placement_repeater(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Node placement repeater', 1)
    from .phase_factories import NodePlacementStrategy
    selected = read_layered_scalar(
        graph, 'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY_RECOMPUTE_NODE_PLACEMENT',
        'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY_RECOMPUTE_NODE_PLACEMENT_0')
    placer = NodePlacementStrategy[selected].create()
    graph.properties['NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY_DEFAULT'] = None
    for layer in graph.layers:
        for node in layer.nodes:
            node.properties['NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY'] = None
            node.properties['NODE_SIZE_CONSTRAINTS'] = None
            node.pos.y = 0.0
    adapter = LGraphAdapter(graph, True, True, lambda node: node.type == 'NORMAL')
    calculate_label_and_node_sizes(adapter)
    NodeMarginCalculator(adapter).process()
    placer.process(graph, monitor)
    monitor.done()


def _connected_edges(node):
    for port in node.ports:
        first = second = 0
        while first < len(port.incoming_edges) or second < len(port.outgoing_edges):
            if first < len(port.incoming_edges):
                edge = port.incoming_edges[first]
                first += 1
            else:
                edge = port.outgoing_edges[second]
                second += 1
            yield edge


class InteractiveExternalPortPositioner:
    source_name = 'InteractiveExternalPortPositioner'

    def __init__(self):
        # Source prototype initializers; the cached processor does not reset
        # these accumulated bounds at the start of a subsequent process call.
        self.max_x = self.max_y = -math.inf
        self.min_x = self.min_y = math.inf

    def get_layout_processor_configuration(self, graph):
        return None

    @staticmethod
    def _y(node, first):
        for edge in _connected_edges(node):
            other = edge.target.owner if first else edge.source.owner
            return other.pos.y + other.size.y / 2
        return None

    @staticmethod
    def _north_south_x(dummy):
        port = dummy.ports[0]
        if port.outgoing_edges and port.incoming_edges:
            raise ValueError('Interactive layout does not support NORTH/SOUTH ports with incoming _and_ outgoing edges.')
        if port.outgoing_edges:
            result = math.inf
            for edge in port.outgoing_edges:
                node = edge.target.owner
                result = _minimum(result, node.pos.x - _read_property(node, 'MARGINS').left)
            return result
        if port.incoming_edges:
            result = -math.inf
            for edge in port.incoming_edges:
                node = edge.source.owner
                result = _maximum(result, (node.pos.x + node.size.x) + _read_property(node, 'MARGINS').right)
            return result
        return None

    def process(self, graph, monitor=None):
        # The actual Source process does not begin, finish or read its monitor.
        if 'EXTERNAL_PORTS' not in get_graph_properties(graph):
            return
        for node in graph.layerless_nodes:
            if node.type == 'NORMAL':
                margins = _read_property(node, 'MARGINS')
                self.min_x = _minimum(self.min_x, node.pos.x - margins.left)
                self.max_x = _maximum(self.max_x, (node.pos.x + node.size.x) + margins.right)
                self.min_y = _minimum(self.min_y, node.pos.y - margins.top)
                self.max_y = _maximum(self.max_y, (node.pos.y + node.size.y) + margins.bottom)
        for node in graph.layerless_nodes:
            if node.type == 'NORMAL':
                continue
            if node.type != 'EXTERNAL_PORT':
                raise ValueError('The node type ' + str(node.type) + ' is not supported by the org.eclipse.elk.alg.layered.intermediate.InteractiveExternalPortPositioner')
            constraint = read_layered_scalar(node, 'LAYER_CONSTRAINT', 'LAYERING_LAYER_CONSTRAINT_0')
            if constraint == 'FIRST_SEPARATE':
                node.pos.x = self.min_x - 10
                value = self._y(node, True)
                if value is not None:
                    node.pos.y = value
                continue
            if constraint == 'LAST_SEPARATE':
                node.pos.x = self.max_x + 10
                value = self._y(node, False)
                if value is not None:
                    node.pos.y = value
                continue
            internal = node.properties.get('IN_LAYER_CONSTRAINT')
            if internal in ('TOP', 'BOTTOM'):
                value = self._north_south_x(node)
                if value is not None:
                    node.pos.x = value + 10
                node.pos.y = self.min_y - 10 if internal == 'TOP' else self.max_y + 10
