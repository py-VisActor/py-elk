# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P08B in references/e13-kernel-sources.json.
# Guava support is behavior-only; native identity-map/list adapter is original host code.
# Standalone resolver; actual sorting/ranks/counters/scheduler remain separate.
"""Actual ordered Forster constraint groups; upstream sorting is separate."""
from dataclasses import dataclass
from .barycenter import BarycenterState

def _remove_identity(items, value):
    for index, item in enumerate(items):
        if item is value:
            items.pop(index)
            return True
    return False

def _contains_identity(items, value):
    return any((item is value for item in items))

def _successors(node):
    value = node.properties.get('IN_LAYER_SUCCESSOR_CONSTRAINTS')
    if value is None:
        value = []
        node.properties['IN_LAYER_SUCCESSOR_CONSTRAINTS'] = value
    return value

@dataclass(eq=False)
class ConstraintGroup:
    nodes: list
    outgoing_constraints: list | None = None
    incoming_constraints: list | None = None
    incoming_constraints_count: int = 0
    summed_weight: float = 0.0
    degree: float = 0.0

class ForsterConstraintResolver:

    def __init__(self, node_order):
        self.constraints_between_non_dummies = bool(node_order and node_order[0] and node_order[0][0].graph.properties.get('IN_LAYER_SUCCESSOR_CONSTRAINTS_BETWEEN_NON_DUMMIES', False))
        self.states = {}
        self.constraint_groups = {}
        self.layout_units = {}
        for layer in node_order:
            for node in layer:
                self._init_node(node, True)

    def _init_node(self, node, full_init):
        self.constraint_groups[node] = ConstraintGroup([node])
        if full_init:
            self.states[node] = BarycenterState(node)
            unit = node.properties.get('IN_LAYER_LAYOUT_UNIT')
            if unit is not None:
                members = self.layout_units.setdefault(unit, [])
                if not _contains_identity(members, node):
                    members.append(node)

    @staticmethod
    def _outgoing(group):
        if group.outgoing_constraints is None:
            group.outgoing_constraints = []
        return group.outgoing_constraints

    def _build(self, groups, only_normal):
        for group in groups:
            group.outgoing_constraints = None
            group.incoming_constraints_count = 0
        last_normal = None
        for group in groups:
            node = group.nodes[0]
            if only_normal and node.type != 'NORMAL':
                continue
            for successor in _successors(node):
                if not only_normal or successor.type == 'NORMAL':
                    target = self.constraint_groups[successor]
                    self._outgoing(group).append(target)
                    target.incoming_constraints_count += 1
            if not only_normal and node.type == 'NORMAL':
                if last_normal is not None:
                    for previous_member in self.layout_units.get(last_normal, []):
                        for current_member in self.layout_units.get(node, []):
                            target = self.constraint_groups[current_member]
                            self._outgoing(self.constraint_groups[previous_member]).append(target)
                            target.incoming_constraints_count += 1
                last_normal = node

    def _find_violation(self, groups):
        active = []
        for group in groups:
            if self.states[group.nodes[0]].barycenter is None:
                raise TypeError('Constraint head barycenter must not be null')
            group.incoming_constraints = None
            if group.outgoing_constraints is not None and len(group.outgoing_constraints) > 0 and (group.incoming_constraints_count == 0):
                active.append(group)
        while active:
            group = active.pop(0)
            if group.incoming_constraints is not None and len(group.incoming_constraints) > 0:
                for predecessor in group.incoming_constraints:
                    left = self.states[predecessor.nodes[0]].barycenter
                    right = self.states[group.nodes[0]].barycenter
                    if left == right:
                        if groups.index(predecessor) > groups.index(group):
                            return (predecessor, group)
                    elif left > right:
                        return (predecessor, group)
            for successor in self._outgoing(group):
                if successor.incoming_constraints is None:
                    successor.incoming_constraints = []
                successor.incoming_constraints.insert(0, group)
                if successor.incoming_constraints_count == len(successor.incoming_constraints):
                    active.append(successor)
        return None

    def _set_barycenter(self, group, value):
        for node in group.nodes:
            self.states[node].barycenter = value

    def _merge_group(self, first, second):
        merged = ConstraintGroup(first.nodes + second.nodes)
        if first.outgoing_constraints is not None:
            merged.outgoing_constraints = list(first.outgoing_constraints)
            _remove_identity(merged.outgoing_constraints, second)
            if second.outgoing_constraints is not None:
                for candidate in second.outgoing_constraints:
                    if candidate is first:
                        continue
                    if _contains_identity(merged.outgoing_constraints, candidate):
                        candidate.incoming_constraints_count -= 1
                    else:
                        merged.outgoing_constraints.append(candidate)
        elif second.outgoing_constraints is not None:
            merged.outgoing_constraints = list(second.outgoing_constraints)
            _remove_identity(merged.outgoing_constraints, first)
        merged.summed_weight = first.summed_weight + second.summed_weight
        merged.degree = first.degree + second.degree
        a = self.states[first.nodes[0]].barycenter
        b = self.states[second.nodes[0]].barycenter
        if merged.degree > 0:
            self._set_barycenter(merged, merged.summed_weight / merged.degree)
        elif a is not None and b is not None:
            self._set_barycenter(merged, (a + b) / 2)
        elif a is not None:
            self._set_barycenter(merged, a)
        elif b is not None:
            self._set_barycenter(merged, b)
        return merged

    def _handle(self, first, second, groups):
        merged = self._merge_group(first, second)
        inserted = False
        index = 0
        while index < len(groups):
            group = groups[index]
            index += 1
            if group is first or group is second:
                groups.pop(index - 1)
                index -= 1
            elif not inserted and self.states[group.nodes[0]].barycenter > self.states[merged.nodes[0]].barycenter:
                index -= 1
                groups.insert(index, merged)
                index += 1
                inserted = True
            elif group.outgoing_constraints is not None and len(group.outgoing_constraints) > 0:
                first_removed = _remove_identity(group.outgoing_constraints, first)
                second_removed = _remove_identity(group.outgoing_constraints, second)
                if first_removed or second_removed:
                    group.outgoing_constraints.append(merged)
                    merged.incoming_constraints_count += 1
        if not inserted:
            groups.append(merged)

    def _process(self, nodes, only_normal):
        groups = [self.constraint_groups[node] for node in nodes]
        self._build(groups, only_normal)
        while True:
            pair = self._find_violation(groups)
            if pair is None:
                break
            self._handle(pair[0], pair[1], groups)
        nodes.clear()
        for group in groups:
            for node in group.nodes:
                nodes.append(node)
                self.states[node].barycenter = self.states[group.nodes[0]].barycenter

    def process_constraints(self, nodes):
        if self.constraints_between_non_dummies:
            self._process(nodes, True)
            for node in nodes:
                self._init_node(node, False)
        self._process(nodes, False)
