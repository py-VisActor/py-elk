# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P08D in references/e13-kernel-sources.json.
# Source collection/primitive runtime is observed, not transplanted.
# Independent subtype; central box provenance and complete crossing remain separate.
"""Actual ModelOrder subtype, including source cache direction and reset."""
from .barycenter_order import BarycenterHeuristic
from .ports import _source_sort, double_compare
from .integer_box_tokens import holder_integer_box_identity, value_of_integer_box
_GROUP_STRATEGY = 'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY'
_ENFORCED_GROUPS = 'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_ENFORCED_GROUP_ORDERS'
_GROUP_ID = 'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID'
_DEFAULT_GROUP_ID_BOX = value_of_integer_box(0)

def calculate_model_order_or_group_order(element, other, parent, offset):
    enforced = parent.properties.get(_GROUP_STRATEGY, 'ONLY_WITHIN_GROUP') == 'ENFORCED'
    enforced_orders = parent.properties.get(_ENFORCED_GROUPS, (1, 2, 6, 7, 10, 11))
    if 'MODEL_ORDER' in element.properties:
        if enforced:
            group = element.properties.get(_GROUP_ID, 0)
            other_group = other.properties.get(_GROUP_ID, 0)
            if group in enforced_orders and other_group in enforced_orders:
                return float(offset) * float(group) + float(element.properties['MODEL_ORDER'])
        else:
            return element.properties['MODEL_ORDER']
    else:
        return -1
    return element.properties['MODEL_ORDER']

class ModelOrderBarycenterHeuristic(BarycenterHeuristic):

    def __init__(self, constraint_resolver, random, port_distributor, *, box_identity_getter=holder_integer_box_identity):
        super().__init__(constraint_resolver, random, port_distributor)
        self.bigger_than = {}
        self.smaller_than = {}
        self.box_identity_getter = box_identity_getter

    def _compare_transitive(self, first, second):
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
            if first in self.smaller_than[second]:
                return 1
        else:
            self.smaller_than[second] = set()
        return 0

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

    def _compare_barycenter(self, first, second):
        a = self.states[first].barycenter
        b = self.states[second].barycenter
        if a is not None and b is not None:
            result = double_compare(a, b)
            if result < 0:
                self._update_associations(first, second)
            elif result > 0:
                self._update_associations(second, first)
            return result
        if a is not None:
            self._update_associations(first, second)
            return -1
        if b is not None:
            self._update_associations(second, first)
            return 1
        return 0

    def compare(self, first, second):
        if 'LAYERING_LAYER_CONSTRAINT' in first.properties and first.properties['LAYERING_LAYER_CONSTRAINT'] in ('FIRST_SEPARATE', 'LAST_SEPARATE') or ('LAYERING_LAYER_CONSTRAINT' in second.properties and second.properties['LAYERING_LAYER_CONSTRAINT'] in ('FIRST_SEPARATE', 'LAST_SEPARATE')):
            return 0
        graph = first.graph
        transitive = self._compare_transitive(first, second)
        if transitive != 0:
            return transitive
        if 'MODEL_ORDER' in first.properties and 'MODEL_ORDER' in second.properties:
            offset = graph.properties.get('MAX_MODEL_ORDER_NODES')
            if offset is None:
                raise TypeError('Actual MAX_MODEL_ORDER_NODES is required')
            a = calculate_model_order_or_group_order(first, second, graph, offset)
            b = calculate_model_order_or_group_order(second, first, graph, offset)
            result = -1 if a < b else 1 if a > b else 0
            if graph.properties.get(_GROUP_STRATEGY, 'ONLY_WITHIN_GROUP') == 'ONLY_WITHIN_GROUP':
                first_box = self.box_identity_getter(first, _GROUP_ID, _DEFAULT_GROUP_ID_BOX)
                second_box = self.box_identity_getter(second, _GROUP_ID, _DEFAULT_GROUP_ID_BOX)
                if first_box is not second_box:
                    result = 0
            if result < 0:
                self._update_associations(first, second)
                return result
            if result > 0:
                self._update_associations(second, first)
                return result
        return self._compare_barycenter(first, second)

    def _insertion_sort(self, nodes):
        for index in range(1, len(nodes)):
            current = nodes[index]
            target = index
            while target > 0 and self.compare(nodes[target - 1], current) > 0:
                nodes[target] = nodes[target - 1]
                target -= 1
            nodes[target] = current
        self.bigger_than = {}
        self.smaller_than = {}

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
            if not nodes[0].graph.properties.get('CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER', False):
                self.constraint_resolver.process_constraints(nodes)

def create_barycenter_heuristic(graph, constraint_resolver, random, port_distributor, *, box_identity_getter=holder_integer_box_identity):
    if graph.properties.get('CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER', False):
        return ModelOrderBarycenterHeuristic(constraint_resolver, random, port_distributor, box_identity_getter=box_identity_getter)
    return BarycenterHeuristic(constraint_resolver, random, port_distributor)
