# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P13A in references/e13-kernel-sources.json.
# Existing Apache-noticed GWT sort/RNG called unchanged; host entropy is separate.
"""Actual median crossing heuristic, including source extrema and weight writes."""
from ...execution.entropy import random_unit
from .ports import _source_sort, double_compare
from .port_distribution import _minimum, _maximum


class MedianHeuristic:
    def __init__(self, random, *, host_random=random_unit):
        self.random = random
        host_random()

    def compare(self, first, second):
        if 'WEIGHT' not in first.properties:
            return 1
        if 'WEIGHT' not in second.properties:
            return -1
        a, b = first.properties['WEIGHT'], second.properties['WEIGHT']
        if a is not None and b is not None:
            return double_compare(a, b)
        elif a is not None:
            return -1
        elif b is not None:
            return 1
        return 0

    def calculate_medians(self, nodes, reference_layer):
        minimum = 4.9e-324
        maximum = 1.7976931348623157e308
        revisit = []
        for node in nodes:
            connected = []
            for incoming in (True, False):
                for port in node.ports:
                    for edge in port.incoming_edges if incoming else port.outgoing_edges:
                        target, source = edge.target.owner, edge.source.owner
                        if target.layer.id == reference_layer:
                            connected.append(target)
                        if source.layer.id == reference_layer:
                            connected.append(source)
            if not connected:
                revisit.append(node)
            else:
                _source_sort(connected, self.compare)
                value = connected[len(connected) // 2].properties['WEIGHT']
                if value is None:
                    raise TypeError('Actual median weight is required')
                node.properties['WEIGHT'] = value
                minimum = _minimum(minimum, value)
                maximum = _maximum(maximum, value)
        average = (maximum + minimum) / 2
        for node in revisit:
            node.properties['WEIGHT'] = average

    def init_after_traversal(self):
        pass

    def init_at_edge_level(self, layer_index, node_index, port_index, edge_index, edge, node_order):
        pass

    def init_at_layer_level(self, layer_index, node_order):
        pass

    def init_at_node_level(self, layer_index, node_index, node_order):
        pass

    def init_at_port_level(self, layer_index, node_index, port_index, node_order):
        pass

    def always_improves(self):
        return False

    def is_deterministic(self):
        return True

    def minimize_crossings(self, order, free_layer_index, forward, first_sweep):
        row = list(order[free_layer_index])
        self.calculate_medians(row, free_layer_index - 1 if forward else free_layer_index + 1)
        _source_sort(row, self.compare)
        for index, node in enumerate(row):
            order[free_layer_index][index] = node
        return False

    def set_first_layer_order(self, order, forward):
        index = 0 if forward else max(0, len(order) - 1)
        row = list(order[index])
        for node in row:
            node.properties['WEIGHT'] = self.random.next_double()
        _source_sort(row, self.compare)
        for position, node in enumerate(row):
            order[index][position] = node
            node.properties['WEIGHT'] = float(position + 1)
        return False
