# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P12B in references/e13-kernel-sources.json.
# Source runtime observed, not copied; native identity-membership relations only.
"""Stateful source model-order port comparator, including literal cache guards."""
from .model_order_barycenter import calculate_model_order_or_group_order

_SIDES = {'UNDEFINED': 0, 'NORTH': 1, 'EAST': 2, 'SOUTH': 3, 'WEST': 4}


def _reference_layer(layer, first, second):
    for node in layer:
        if node is first:
            return -1
        elif node is second:
            return 1
    return 0


class ModelOrderPortComparator:
    def __init__(self, graph, previous_layer, strategy, target_node_model_order=None, port_model_order=False):
        self.bigger_than = {}
        self.smaller_than = {}
        self.graph = graph
        self.previous_layer = previous_layer
        self.strategy = strategy
        self.target_node_model_order = target_node_model_order
        self.port_model_order = port_model_order

    @classmethod
    def from_layer(cls, graph, previous_layer, strategy, target_node_model_order=None, port_model_order=False):
        return cls(graph, list(previous_layer.nodes), strategy, target_node_model_order, port_model_order)

    def _update_associations(self, bigger, smaller, reverse_order):
        if reverse_order < 0:
            bigger, smaller = smaller, bigger
        bigger_bigger = self.bigger_than[bigger]
        smaller_bigger = self.bigger_than[smaller]
        bigger_smaller = self.smaller_than[bigger]
        smaller_smaller = self.smaller_than[smaller]
        bigger_bigger.add(smaller)
        smaller_smaller.add(bigger)
        # P12B's narrowly proven identity-membership adaptation covers source
        # self-comparisons and cyclic caches; it assumes no DAG or node limit.
        for very_small in smaller_bigger:
            bigger_bigger.add(very_small)
            self.smaller_than[very_small].add(bigger)
            self.smaller_than[very_small].update(bigger_smaller)
        for very_big in bigger_smaller:
            smaller_smaller.add(very_big)
            self.bigger_than[very_big].add(smaller)
            self.bigger_than[very_big].update(smaller_bigger)

    def _check_port_model_order(self, first, second):
        count = len(first.owner.ports)
        if 'MODEL_ORDER' in first.properties and 'MODEL_ORDER' in second.properties:
            a = calculate_model_order_or_group_order(first, second, self.graph, count)
            b = calculate_model_order_or_group_order(second, first, self.graph, count)
            return -1 if a < b else 1 if a > b else 0
        return 0

    def _return_order(self, first, second, result, reverse_order):
        if result > 0:
            self._update_associations(first, second, reverse_order)
            return reverse_order
        self._update_associations(second, first, reverse_order)
        return -reverse_order

    def compare(self, first, second):
        if first in self.bigger_than:
            if second in self.bigger_than[first]:
                return 1
        else:
            self.bigger_than[first] = set()
        if second in self.bigger_than:
            if first in self.bigger_than[second]:
                return -1
        else:
            self.bigger_than[second] = set()
        if first in self.smaller_than:
            if second in self.smaller_than[first]:
                return -1
        else:
            self.smaller_than[first] = set()
        if second in self.smaller_than:
            # This reads bigger_than, as in the fixed generated source.
            if first in self.bigger_than[second]:
                return 1
        else:
            self.smaller_than[second] = set()
        if first.side != second.side:
            a, b = _SIDES[first.side], _SIDES[second.side]
            result = -1 if a < b else 1 if a > b else 0
            self._update_associations(first if result > 0 else second, second if result > 0 else first, 1)
            return result
        reverse_order = 1
        if first.incoming_edges and second.incoming_edges:
            if first.side in ('WEST', 'NORTH', 'SOUTH'):
                reverse_order = -reverse_order
            first_source = first.incoming_edges[0].source
            second_source = second.incoming_edges[0].source
            first_node, second_node = first_source.owner, second_source.owner
            if first_node is second_node:
                for port in first_node.ports:
                    if first_source is port:
                        self._update_associations(second, first, reverse_order)
                        return -reverse_order
                    elif second_source is port:
                        self._update_associations(first, second, reverse_order)
                        return reverse_order
            if first_node.type == 'LONG_EDGE' and second_node.type == 'LONG_EDGE' and first_node.layer.id == second_node.layer.id and first_node.layer.id == first.owner.layer.id:
                result = _reference_layer(first_node.layer.nodes, first_node, second_node)
                if result != 0:
                    if first.side == 'EAST':
                        reverse_order = -reverse_order
                    return self._return_order(first, second, result, reverse_order)
            result = _reference_layer(self.previous_layer, first_node, second_node)
            if result != 0:
                return self._return_order(first, second, result, reverse_order)
            if self.port_model_order:
                result = self._check_port_model_order(first, second)
                if result != 0:
                    return self._return_order(first, second, result, reverse_order)
        if first.outgoing_edges and second.outgoing_edges:
            if first.side in ('WEST', 'SOUTH'):
                reverse_order = -reverse_order
            first_target = first.properties.get('LONG_EDGE_TARGET_NODE')
            second_target = second.properties.get('LONG_EDGE_TARGET_NODE')
            if self.strategy == 'PREFER_NODES' and first_target is not None and second_target is not None and 'MODEL_ORDER' in first_target.properties and 'MODEL_ORDER' in second_target.properties:
                a = calculate_model_order_or_group_order(first_target, second_target, self.graph, self.graph.properties['MAX_MODEL_ORDER_NODES'])
                b = calculate_model_order_or_group_order(second_target, first_target, self.graph, self.graph.properties['MAX_MODEL_ORDER_NODES'])
                return self._return_order(first, second, 1 if a > b else -1, reverse_order)
            if self.port_model_order:
                result = self._check_port_model_order(first, second)
                if result != 0:
                    return self._return_order(first, second, result, reverse_order)
            a, b = 0, 0
            first_edge, second_edge = first.outgoing_edges[0], second.outgoing_edges[0]
            if 'MODEL_ORDER' in first_edge.properties:
                a = calculate_model_order_or_group_order(first_edge, second_edge, self.graph, len(first.outgoing_edges) + len(first.incoming_edges))
            if 'MODEL_ORDER' in second_edge.properties:
                b = calculate_model_order_or_group_order(second_edge, first_edge, self.graph, len(second.outgoing_edges) + len(second.incoming_edges))
            if first_target is not None and first_target is second_target:
                return self._return_order(first, second, 1 if a > b else -1, reverse_order)
            if self.target_node_model_order is not None:
                if first_target in self.target_node_model_order:
                    a = self.target_node_model_order[first_target].value
                if second_target in self.target_node_model_order:
                    b = self.target_node_model_order[second_target].value
            return self._return_order(first, second, 1 if a > b else -1, reverse_order)
        if first.incoming_edges and second.outgoing_edges:
            self._update_associations(first, second, reverse_order)
            return 1
        elif first.outgoing_edges and second.incoming_edges:
            self._update_associations(second, first, reverse_order)
            return -1
        elif 'MODEL_ORDER' in first.properties and 'MODEL_ORDER' in second.properties:
            count = len(first.owner.ports)
            a = calculate_model_order_or_group_order(first, second, self.graph, count)
            b = calculate_model_order_or_group_order(second, first, self.graph, count)
            if first.side in ('WEST', 'SOUTH'):
                reverse_order = -reverse_order
            return self._return_order(first, second, 1 if a > b else -1, reverse_order)
        else:
            self._update_associations(second, first, reverse_order)
            return -reverse_order
