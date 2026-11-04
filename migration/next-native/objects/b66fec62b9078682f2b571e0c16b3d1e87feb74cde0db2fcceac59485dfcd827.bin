# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P13C in references/e13-kernel-sources.json.
# Native indexed side view is original host code, not a Guava/GWT list transplant.
"""Real adjacent greedy port swaps with live physical side-view writes."""
from .crossing_counter import CrossingsCounter, _side_view
from .ports import _cache_sides, is_order_fixed
from .two_node_crossings import BetweenLayerEdgeTwoNodeCrossingsCounter


class _LiveSidePorts:
    def __init__(self, node, side):
        if not node.port_sides_cached:
            _cache_sides(node)
        begin, end = node.port_side_indices.get(side, (0, 0))
        self.node = node
        self.indices = range(end - 1, begin - 1, -1) if side in ('SOUTH', 'WEST') else range(begin, end)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        return self.node.ports[self.indices[index]]

    def __setitem__(self, index, value):
        self.node.ports[self.indices[index]] = value


class GreedyPortDistributor:
    def __init__(self):
        self.n_ports = 0
        self._registered_ports = []

    def init_at_edge_level(self, layer_index, node_index, port_index, edge_index, edge, node_order):
        pass

    def init_at_layer_level(self, layer_index, node_order):
        pass

    def init_at_port_level(self, layer_index, node_index, port_index, node_order):
        pass

    def init_at_node_level(self, layer_index, node_index, node_order):
        ports = node_order[layer_index][node_index].ports
        self.n_ports += len(ports)
        self._registered_ports.extend(ports)

    def init_after_traversal(self):
        self.port_pos = {port: 0 for port in self._registered_ports}
        self.crossings_counter = CrossingsCounter(self.port_pos)

    def distribute_ports_while_sweeping(self, node_order, current_index, forward):
        if forward and current_index > 0:
            self.crossings_counter.init_for_counting_between(node_order[current_index - 1], node_order[current_index])
        elif not forward and current_index < len(node_order) - 1:
            self.crossings_counter.init_for_counting_between(node_order[current_index], node_order[current_index + 1])
        else:
            self.crossings_counter._init_positions_for_in_layer(node_order[current_index], 'WEST' if forward else 'EAST')
        return self.distribute_ports_in_layer(node_order, current_index, forward)

    def distribute_ports_in_layer(self, node_order, current_index, forward):
        side = 'WEST' if forward else 'EAST'
        improved = False
        for node in node_order[current_index]:
            if is_order_fixed(node.properties.get('PORT_CONSTRAINTS', 'UNDEFINED')):
                continue
            nested = getattr(node, 'nested_graph', None)
            hierarchical = bool(_side_view(node, side)) and nested is not None
            if hierarchical:
                order = [list(layer.nodes) for layer in nested.layers]
                self.hierarchical_crossings_counter = BetweenLayerEdgeTwoNodeCrossingsCounter(order, 0 if forward else len(order) - 1)
            improved = int(improved) | int(self.distribute_ports_on_node(node, side, hierarchical))
        return improved

    def distribute_ports_on_node(self, node, side, use_hierarchical_cross_counter):
        ports = _LiveSidePorts(node, side)
        improved = False
        while True:
            continue_switching = False
            for index in range(len(ports) - 1):
                upper, lower = ports[index], ports[index + 1]
                if self.switching_decreases_crossings(upper, lower, use_hierarchical_cross_counter):
                    improved = True
                    self.crossings_counter.switch_ports(ports[index], ports[index + 1])
                    lower = ports[index + 1]
                    ports[index + 1] = ports[index]
                    ports[index] = lower
                    continue_switching = True
            if not continue_switching:
                return improved

    def switching_decreases_crossings(self, upper_port, lower_port, use_hierarchical_cross_counter):
        upper_lower, lower_upper = self.crossings_counter.count_crossings_between_ports_in_both_orders(upper_port, lower_port)
        if use_hierarchical_cross_counter:
            upper = upper_port.properties.get('PORT_DUMMY')
            lower = lower_port.properties.get('PORT_DUMMY')
            if upper is not None and lower is not None:
                self.hierarchical_crossings_counter.count_both_side_crossings(upper, lower)
                upper_lower += self.hierarchical_crossings_counter.upper_lower_crossings
                lower_upper += self.hierarchical_crossings_counter.lower_upper_crossings
        return upper_lower > lower_upper
