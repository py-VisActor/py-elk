# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P14C in references/e13-kernel-sources.json.
"""Actual adjacent GreedySwitch node sweeps with live counter notifications."""
from .crossing_matrix import CrossingMatrixFiller
from .switch_decider import SwitchDecider


class GreedySwitchHeuristic:
    def __init__(self, greedy_type, graph_data):
        self.graph_data = graph_data
        self.greedy_switch_type = greedy_type
        self.n_ports = 0
        self._registered_ports = []

    def init_at_edge_level(self, layer_index, node_index, port_index, edge_index, edge, node_order):
        pass

    def init_at_node_level(self, layer_index, node_index, node_order):
        pass

    def init_after_traversal(self):
        self.port_positions = {port: 0 for port in self._registered_ports}

    def init_at_layer_level(self, layer_index, node_order):
        node_order[layer_index][0].layer.id = layer_index

    def init_at_port_level(self, layer_index, node_index, port_index, node_order):
        self.n_ports += 1
        self._registered_ports.append(node_order[layer_index][node_index].ports[port_index])

    def always_improves(self):
        return self.greedy_switch_type != 'ONE_SIDED_GREEDY_SWITCH'

    def is_deterministic(self):
        return True

    def set_up(self, order, free_layer_index, forward):
        self.current_node_order = order
        side = 0 if forward else 1
        matrix = CrossingMatrixFiller(self.greedy_switch_type, self.current_node_order, free_layer_index, side)
        self.switch_decider = SwitchDecider(free_layer_index, self.current_node_order, matrix, self.port_positions, self.graph_data, self.greedy_switch_type == 'ONE_SIDED_GREEDY_SWITCH')

    def switch_if_improves(self, layer_index, upper_index, lower_index):
        continued = False
        if self.switch_decider.does_switch_reduce_crossings(upper_index, lower_index):
            self.switch_decider.notify_of_switch(self.current_node_order[layer_index][upper_index], self.current_node_order[layer_index][lower_index])
            layer = self.current_node_order[layer_index]
            temporary = layer[lower_index]
            layer[lower_index] = layer[upper_index]
            layer[upper_index] = temporary
            continued = True
        return continued

    def sweep_downward_in_layer(self, layer_index):
        continued = False
        length = len(self.current_node_order[layer_index])
        for upper in range(length - 1):
            lower = upper + 1
            continued = int(continued) | int(self.switch_if_improves(layer_index, upper, lower))
        return continued

    def continue_switching_until_no_improvement_in_layer(self, free_layer_index):
        improved = False
        while True:
            continued = self.sweep_downward_in_layer(free_layer_index)
            improved = int(improved) | int(continued)
            if not continued:
                return improved

    def minimize_crossings(self, order, free_layer_index, forward, first_sweep):
        self.set_up(order, free_layer_index, forward)
        return self.continue_switching_until_no_improvement_in_layer(free_layer_index)

    def set_first_layer_order(self, order, forward):
        start = 0 if forward else len(order) - 1
        self.set_up(order, start, forward)
        return self.sweep_downward_in_layer(start)
