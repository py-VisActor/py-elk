# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P12C in references/e13-kernel-sources.json.
# Runtime collections observed, not copied; source membership-only adaptation.
"""Actual node model-order comparator with explicit recursive continuations."""
from .model_order_barycenter import calculate_model_order_or_group_order
from .model_order_ports import ModelOrderPortComparator


def _first_port(node, incoming):
    for port in node.ports:
        if port.incoming_edges if incoming else port.outgoing_edges:
            return port
    return None


def _previous_source(node):
    for port in node.ports:
        if port.incoming_edges:
            source = port.incoming_edges[0].source
            if source.owner.layer.id == node.layer.id - 1:
                return source
    return None


def _dummy_neighbors(node):
    source = _first_port(node, True).incoming_edges[0].source
    target = _first_port(node, False).outgoing_edges[0].target
    return source, target


class ModelOrderNodeComparator:
    def __init__(self, graph, previous_layer, ordering_strategy, long_edge_ordering_strategy='EQUAL', before_ports=False):
        self.bigger_than = {}
        self.smaller_than = {}
        self.graph = graph
        self.ordering_strategy = ordering_strategy
        self.long_edge_node_order = long_edge_ordering_strategy
        self.before_ports = before_ports
        self.previous_layer = previous_layer

    @classmethod
    def from_layer(cls, graph, previous_layer, ordering_strategy, long_edge_ordering_strategy='EQUAL', before_ports=False):
        return cls(graph, list(previous_layer.nodes), ordering_strategy, long_edge_ordering_strategy, before_ports)

    def _update_associations(self, bigger, smaller):
        bigger_bigger = self.bigger_than[bigger]
        smaller_bigger = self.bigger_than[smaller]
        bigger_smaller = self.smaller_than[bigger]
        smaller_smaller = self.smaller_than[smaller]
        bigger_bigger.add(smaller)
        smaller_smaller.add(bigger)
        for very_small in smaller_bigger:
            bigger_bigger.add(very_small)
            self.smaller_than[very_small].add(bigger)
            self.smaller_than[very_small].update(bigger_smaller)
        for very_big in bigger_smaller:
            smaller_smaller.add(very_big)
            self.bigger_than[very_big].add(smaller)
            self.bigger_than[very_big].update(smaller_bigger)

    def _edge_model_order(self, node):
        port = _first_port(node, True)
        if port is not None:
            edge = port.incoming_edges[0]
            return edge.properties['MODEL_ORDER']
        return {'DUMMY_NODE_OVER': 2147483647, 'DUMMY_NODE_UNDER': -2147483648, 'EQUAL': 0}[self.long_edge_node_order]

    def _return_order(self, first, second, greater):
        if greater:
            self._update_associations(first, second)
            return 1
        self._update_associations(second, first)
        return -1

    def _compare(self, first, second):
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
            # Literal fixed source uses biggerThan here.
            if first in self.bigger_than[second]:
                return 1
        else:
            self.smaller_than[second] = set()
        if self.ordering_strategy == 'PREFER_EDGES' or 'MODEL_ORDER' not in first.properties or 'MODEL_ORDER' not in second.properties:
            first_source, second_source = _previous_source(first), _previous_source(second)
            if first_source is not None and second_source is not None:
                first_node, second_node = first_source.owner, second_source.owner
                if first_node is not None and first_node is second_node:
                    for port in first_node.ports:
                        if port is first_source:
                            self._update_associations(second, first)
                            return -1
                        elif port is second_source:
                            self._update_associations(first, second)
                            return 1
                    return self._return_order(first, second, self._edge_model_order(first) > self._edge_model_order(second))
                for previous in self.previous_layer:
                    if previous is first_node:
                        self._update_associations(second, first)
                        return -1
                    elif previous is second_node:
                        self._update_associations(first, second)
                        return 1
            if (first_source is not None) != (second_source is not None):
                result = yield from self._handle_helper_dummy_nodes(first, second)
                if result != 0:
                    self._update_associations(first if result > 0 else second, second if result > 0 else first)
                    return result
                if 'MODEL_ORDER' not in first.properties or 'MODEL_ORDER' not in second.properties:
                    return self._return_order(first, second, self._edge_model_order(first) > self._edge_model_order(second))
            if first_source is None and second_source is None:
                result = yield from self._handle_helper_dummy_nodes(first, second)
                if result != 0:
                    self._update_associations(first if result > 0 else second, second if result > 0 else first)
                    return result
        if 'MODEL_ORDER' in first.properties and 'MODEL_ORDER' in second.properties:
            a = calculate_model_order_or_group_order(first, second, self.graph, self.graph.properties['MAX_MODEL_ORDER_NODES'])
            b = calculate_model_order_or_group_order(second, first, self.graph, self.graph.properties['MAX_MODEL_ORDER_NODES'])
            return self._return_order(first, second, a > b)
        self._update_associations(second, first)
        return -1

    def _handle_helper_dummy_nodes(self, first, second):
        if first.type == 'LONG_EDGE' and second.type == 'NORMAL':
            source, target = _dummy_neighbors(first)
            source_node, target_node = source.owner, target.owner
            layer_id = first.layer.id
            if source_node.layer.id != layer_id and target_node.layer.id != layer_id:
                return 0
            if source_node is second or target_node is second:
                self._update_associations(first, second)
                return 1
            return (yield (source_node, second))
        elif first.type == 'NORMAL' and second.type == 'LONG_EDGE':
            source, target = _dummy_neighbors(second)
            source_node, target_node = source.owner, target.owner
            # Literal first-node layer, including recursive cross-layer calls.
            layer_id = first.layer.id
            if source_node.layer.id != layer_id and target_node.layer.id != layer_id:
                return 0
            if source_node is first or target_node is first:
                self._update_associations(second, first)
                return -1
            return (yield (first, source_node))
        elif first.type == 'LONG_EDGE' and second.type == 'LONG_EDGE':
            first_source, first_target = _dummy_neighbors(first)
            second_source, second_target = _dummy_neighbors(second)
            first_source_node, first_target_node = first_source.owner, first_target.owner
            second_source_node, second_target_node = second_source.owner, second_target.owner
            first_source_feedback = first_target_feedback = False
            second_source_feedback = second_target_feedback = False
            first_reference, second_reference = first, second
            if first_source_node.layer.id == first.layer.id:
                first_source_feedback = True
                first_reference = first_source_node
            elif first_target_node.layer.id == first.layer.id:
                first_target_feedback = True
                first_reference = first_target_node
            if second_source_node.layer.id == second.layer.id:
                second_source_feedback = True
                second_reference = second_source_node
            elif second_target_node.layer.id == second.layer.id:
                second_target_feedback = True
                second_reference = second_target_node
            if first_reference is second_reference:
                if self.before_ports:
                    if first_source_feedback and second_source_feedback:
                        result = ModelOrderPortComparator(self.graph, self.previous_layer, self.ordering_strategy, None, second_target_feedback).compare(first_source, second_source)
                        if result > 0:
                            self._update_associations(second, first)
                            return 1
                        self._update_associations(first, second)
                        return -1
                    elif first_source_feedback and second_target_feedback:
                        self._update_associations(second, first)
                        return 1
                    elif first_target_feedback and second_source_feedback:
                        self._update_associations(first, second)
                        return -1
                    elif first_target_feedback and second_target_feedback:
                        return 0
                else:
                    for port in first_reference.ports:
                        if first_source is port:
                            self._update_associations(second, first)
                            return -1
                        elif second_source is port:
                            self._update_associations(first, second)
                            return 1
            return (yield (first_reference, second_reference))
        else:
            return 0

    def _drive(self, continuation):
        stack = [continuation]
        result = None
        while stack:
            try:
                first, second = stack[-1].send(result)
                result = None
                stack.append(self._compare(first, second))
            except StopIteration as done:
                result = done.value
                stack.pop()
        return result

    def compare(self, first, second):
        return self._drive(self._compare(first, second))

    def handle_helper_dummy_nodes(self, first, second):
        return self._drive(self._handle_helper_dummy_nodes(first, second))
