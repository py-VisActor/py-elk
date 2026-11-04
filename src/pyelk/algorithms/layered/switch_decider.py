# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P14B in references/e13-kernel-sources.json.
# Source default-list clone/cache adapter reused, no collection runtime copied.
"""Actual GreedySwitch constraints and real local, matrix and parent queries."""
from .crossing_counter import CrossingsCounter, _side_view
from .forster_constraints import _successors, _contains_identity
from .ns_neighbor_crossings import NorthSouthEdgeNeighbouringNodeCrossingsCounter


def _has_edges_on_side(node, side):
    for port in _side_view(node, side):
        if port.properties.get('PORT_DUMMY') is not None or port.incoming_edges or port.outgoing_edges:
            return True
    return False


class SwitchDecider:
    def __init__(self, free_layer_index, graph, crossing_matrix_filler, port_positions, graph_data, one_sided):
        self.crossing_matrix_filler = crossing_matrix_filler
        self.graph_data = graph_data
        if free_layer_index >= len(graph):
            raise IndexError('Greedy SwitchDecider: Free layer not in graph.')
        self.free_layer = graph[free_layer_index] if free_layer_index >= 0 else None
        self.left_in_layer_counter = CrossingsCounter(port_positions)
        self.left_in_layer_counter._init_positions_for_in_layer(self.free_layer, 'WEST')
        self.right_in_layer_counter = CrossingsCounter(port_positions)
        self.right_in_layer_counter._init_positions_for_in_layer(self.free_layer, 'EAST')
        self.north_south_counter = NorthSouthEdgeNeighbouringNodeCrossingsCounter(self.free_layer)
        self.count_crossings_caused_by_port_switch = not one_sided and graph_data.has_parent and not graph_data.use_bottom_up and self.free_layer[0].type == 'EXTERNAL_PORT'
        if self.count_crossings_caused_by_port_switch:
            self._init_parent_crossings_counters(free_layer_index, len(graph))

    def _init_parent_crossings_counters(self, free_layer_index, length):
        parent_data = self.graph_data.parent_graph_data
        order = parent_data.current_node_order
        positions = parent_data.port_positions
        self.parent_cross_counter = CrossingsCounter(positions)
        layer_index = self.graph_data.parent.layer.id
        left = order[layer_index - 1] if layer_index > 0 else []
        middle = order[layer_index]
        right = order[layer_index + 1] if layer_index < len(order) - 1 else []
        if free_layer_index == length - 1:
            self.parent_cross_counter.init_for_counting_between(middle, right)
        else:
            self.parent_cross_counter.init_for_counting_between(left, middle)

    def does_switch_reduce_crossings(self, upper_index, lower_index):
        upper, lower = self.free_layer[upper_index], self.free_layer[lower_index]
        constraints = _successors(upper)
        if constraints is not None and len(constraints) != 0 and _contains_identity(constraints, lower):
            return False
        neither_long = upper.type != 'LONG_EDGE' and lower.type != 'LONG_EDGE'
        upper_unit = upper.properties.get('IN_LAYER_LAYOUT_UNIT')
        lower_unit = lower.properties.get('IN_LAYER_LAYOUT_UNIT')
        different_units = upper_unit is not lower_unit
        have_units = upper_unit is not None and upper_unit is not upper or lower_unit is not None and lower_unit is not lower
        upper_north = _has_edges_on_side(upper, 'NORTH')
        lower_south = _has_edges_on_side(lower, 'SOUTH')
        have_units = int(have_units) | int(_has_edges_on_side(upper, 'SOUTH') or _has_edges_on_side(lower, 'NORTH'))
        unit_constraint = have_units and different_units or upper_north or lower_south
        if neither_long and unit_constraint or upper.type == 'NORTH_SOUTH_PORT' and lower.type == 'NORMAL' or lower.type == 'NORTH_SOUTH_PORT' and upper.type == 'NORMAL':
            return False
        upper, lower = self.free_layer[upper_index], self.free_layer[lower_index]
        left = self.left_in_layer_counter.count_in_layer_crossings_between_nodes_in_both_orders(upper, lower, 'WEST')
        right = self.right_in_layer_counter.count_in_layer_crossings_between_nodes_in_both_orders(upper, lower, 'EAST')
        self.north_south_counter.count_crossings(upper, lower)
        upper_lower = self.crossing_matrix_filler.get_crossing_matrix_entry(upper, lower) + left[0] + right[0] + self.north_south_counter.upper_lower_crossings
        lower_upper = self.crossing_matrix_filler.get_crossing_matrix_entry(lower, upper) + left[1] + right[1] + self.north_south_counter.lower_upper_crossings
        if self.count_crossings_caused_by_port_switch:
            upper_port = upper.properties.get('ORIGIN')
            lower_port = lower.properties.get('ORIGIN')
            first, second = self.parent_cross_counter.count_crossings_between_ports_in_both_orders(upper_port, lower_port)
            upper_lower += first
            lower_upper += second
        return upper_lower > lower_upper

    def notify_of_switch(self, upper, lower):
        self.left_in_layer_counter.switch_nodes(upper, lower, 'WEST')
        self.right_in_layer_counter.switch_nodes(upper, lower, 'EAST')
        if self.count_crossings_caused_by_port_switch:
            upper_port = upper.properties.get('ORIGIN')
            lower_port = lower.properties.get('ORIGIN')
            self.parent_cross_counter.switch_ports(upper_port, lower_port)
