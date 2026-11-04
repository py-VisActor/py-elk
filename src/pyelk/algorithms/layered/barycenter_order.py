# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P08C in references/e13-kernel-sources.json.
# Existing Apache-noticed GWT sort/RNG are called unchanged, not copied here.
# Base caller; forced ModelOrder subtype and actual rank producer remain separate.
"""Actual Barycenter caller; live rank producer and scheduler are separate."""
import math
from .barycenter import BarycenterCalculator
from .ports import _source_sort, double_compare

class BarycenterHeuristic:

    def __init__(self, constraint_resolver, random, port_distributor):
        self.constraint_resolver = constraint_resolver
        self.random = random
        self.port_distributor = port_distributor

    def init_after_traversal(self):
        self.states = self.constraint_resolver.states
        self.port_ranks = self.port_distributor.port_ranks
        self.calculator = BarycenterCalculator(self.random, self.states, self.port_ranks)

    def init_at_layer_level(self, index, node_order):
        node_order[index][0].layer.id = index

    def compare(self, left, right):
        a = self.states[left].barycenter
        b = self.states[right].barycenter
        if a is not None and b is not None:
            return double_compare(a, b)
        if a is not None:
            return -1
        if b is not None:
            return 1
        return 0

    def randomize_barycenters(self, nodes):
        for node in nodes:
            state = self.states[node]
            state.barycenter = self.random.next_double()
            state.summed_weight = state.barycenter
            state.degree = 1.0

    def fill_unknown_barycenters(self, nodes, pre_ordered):
        if pre_ordered:
            previous = -1
            for index, node in enumerate(nodes):
                state = self.states[node]
                if state.barycenter is None:
                    following = previous + 1
                    for later in nodes[index + 1:]:
                        value = self.states[later].barycenter
                        if value is not None:
                            following = value
                            break
                    value = (previous + following) / 2
                    state.barycenter = value
                    state.summed_weight = value
                    state.degree = 1.0
                previous = state.barycenter
        else:
            maximum = 0.0
            for node in nodes:
                value = self.states[node].barycenter
                if value is not None:
                    if math.isnan(value):
                        maximum = float('nan')
                    elif not math.isnan(maximum):
                        maximum = max(maximum, value)
            maximum += 2
            for node in nodes:
                state = self.states[node]
                if state.barycenter is None:
                    value = self.random.next(24) * 2 ** (-24) * maximum - 1
                    state.barycenter = value
                    state.summed_weight = value
                    state.degree = 1.0

    def _insertion_sort(self, nodes):
        raise TypeError('Forced insertion sort requires ModelOrderBarycenterHeuristic')

    def minimize_layer(self, nodes, pre_ordered, randomize, forward):
        if randomize:
            self.randomize_barycenters(nodes)
        else:
            self.calculator.calculate_all(nodes, forward)
            self.fill_unknown_barycenters(nodes, pre_ordered)
        if len(nodes) > 1:
            if nodes[0].graph.properties.get('CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER', False):
                self._insertion_sort(nodes)
            else:
                _source_sort(nodes, self.compare)
            self.constraint_resolver.process_constraints(nodes)

    @staticmethod
    def _start_index(forward, length):
        return 0 if forward else max(0, length - 1)

    def minimize_crossings(self, order, free_layer_index, forward, first_sweep):
        if free_layer_index != self._start_index(forward, len(order)):
            fixed = order[free_layer_index - (1 if forward else -1)]
            self.port_distributor.calculate_port_ranks(fixed, 'OUTPUT' if forward else 'INPUT')
        row = order[free_layer_index]
        pre_ordered = not first_sweep or row[0].type == 'EXTERNAL_PORT'
        nodes = list(row)
        self.minimize_layer(nodes, pre_ordered, False, forward)
        for index, node in enumerate(nodes):
            row[index] = node
        return False

    def set_first_layer_order(self, order, forward):
        start = self._start_index(forward, len(order))
        row = order[start]
        nodes = list(row)
        self.minimize_layer(nodes, False, True, forward)
        for index, node in enumerate(nodes):
            row[index] = node
        return False
