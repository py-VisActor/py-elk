# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P08A in references/e13-kernel-sources.json.
# Actual calculator only; source rank producer and caller integration are separate.
"""Actual same-layer/associate calculation; caller ranks and sorting are separate."""
from dataclasses import dataclass

@dataclass(eq=False)
class BarycenterState:
    node: object
    degree: float = 0.0
    summed_weight: float = 0.0
    barycenter: float | None = None
    visited: bool = False

class BarycenterCalculator:

    def __init__(self, random, states, port_ranks):
        self.random = random
        self.states = states
        self.port_ranks = port_ranks

    def _steps(self, node, forward):
        state = self.states[node]
        for port in node.ports:
            for edge in port.incoming_edges if forward else port.outgoing_edges:
                fixed = edge.source if forward else edge.target
                other = fixed.owner
                if other.layer is node.layer:
                    if other is not node:
                        yield other
                        state.degree += self.states[other].degree
                        state.summed_weight += self.states[other].summed_weight
                else:
                    state.summed_weight += self.port_ranks[fixed]
                    state.degree += 1.0
        associates = node.properties.get('BARYCENTER_ASSOCIATES')
        if associates is not None:
            for associate in associates:
                if associate.layer is node.layer:
                    yield associate
                    state.degree += self.states[associate].degree
                    state.summed_weight += self.states[associate].summed_weight
        if state.degree > 0:
            state.summed_weight += self.random.next(24) * 2 ** (-24) * 0.07000000029802322 - 0.03500000014901161
            state.barycenter = state.summed_weight / state.degree

    def _enter(self, node, forward):
        state = self.states[node]
        state.visited = True
        state.degree = 0.0
        state.summed_weight = 0.0
        state.barycenter = None
        return iter(self._steps(node, forward))

    def calculate(self, node, forward):
        if self.states[node].visited:
            return
        stack = [self._enter(node, forward)]
        while stack:
            try:
                child = next(stack[-1])
            except StopIteration:
                stack.pop()
                continue
            if not self.states[child].visited:
                stack.append(self._enter(child, forward))

    def calculate_all(self, nodes, forward):
        for node in nodes:
            self.states[node].visited = False
        for node in nodes:
            self.calculate(node, forward)
