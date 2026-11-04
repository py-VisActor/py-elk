# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P10D in references/e13-kernel-sources.json, including support bytes.
# Existing Apache-noticed sort/signed helpers called unchanged.
# Original native identity/relative-token adapters; no collection/hash runtime copied.
"""Actual shared-port bundle inversion and interval-corner crossing score."""
from dataclasses import dataclass, field
from .phases import _signed
from .ports import _source_sort

@dataclass(eq=False)
class _Hyperedge:
    birth_order: int
    edges: list = field(default_factory=list)
    ports: list = field(default_factory=list)
    lower_left: int = 0
    lower_right: int = 0
    upper_left: int = 0
    upper_right: int = 0

@dataclass(eq=False)
class _Corner:
    hyperedge: _Hyperedge
    position: int
    opposite_position: int
    type: str

def _compare_hyperedges(first, second):
    if first.upper_left < second.upper_left:
        return -1
    if first.upper_left > second.upper_left:
        return 1
    if first.upper_right < second.upper_right:
        return -1
    if first.upper_right > second.upper_right:
        return 1
    return first.birth_order - second.birth_order

def _compare_corners(first, second):
    if first.position < second.position:
        return -1
    if first.position > second.position:
        return 1
    if first.opposite_position < second.opposite_position:
        return -1
    if first.opposite_position > second.opposite_position:
        return 1
    if first.hyperedge is not second.hyperedge:
        return first.hyperedge.birth_order - second.hyperedge.birth_order
    if first.type == 'UPPER' and second.type == 'LOWER':
        return -1
    if first.type == 'LOWER' and second.type == 'UPPER':
        return 1
    return 0

class HyperedgeCrossingsCounter:

    def __init__(self, port_positions):
        self.port_positions = port_positions

    def _build_hyperedges(self, left, right):
        source_count = 0
        for node in left:
            for port in node.ports:
                count = 0
                for edge in port.outgoing_edges:
                    if node.layer is not edge.target.owner.layer:
                        count += 1
                if count > 0:
                    self.port_positions[port] = source_count
                    source_count += 1
        target_count = 0
        for node in right:
            north_count = 0
            for port in node.ports:
                if port.side == 'NORTH':
                    for edge in port.incoming_edges:
                        if node.layer is not edge.source.owner.layer:
                            north_count += 1
                            break
                else:
                    break
            other_count = 0
            for port in reversed(node.ports):
                count = 0
                for edge in port.incoming_edges:
                    if node.layer is not edge.source.owner.layer:
                        count += 1
                if count > 0:
                    if port.side == 'NORTH':
                        self.port_positions[port] = target_count
                        target_count += 1
                    else:
                        self.port_positions[port] = target_count + north_count + other_count
                        other_count += 1
            target_count += other_count
        port_to_hyperedge = {}
        active = {}
        birth = 0
        for node in left:
            for source in node.ports:
                for edge in source.outgoing_edges:
                    target = edge.target
                    if node.layer is not target.owner.layer:
                        source_he = port_to_hyperedge.get(source)
                        target_he = port_to_hyperedge.get(target)
                        if source_he is None and target_he is None:
                            hyperedge = _Hyperedge(birth)
                            birth += 1
                            active[hyperedge] = None
                            hyperedge.edges.append(edge)
                            hyperedge.ports.append(source)
                            port_to_hyperedge[source] = hyperedge
                            hyperedge.ports.append(target)
                            port_to_hyperedge[target] = hyperedge
                        elif source_he is None:
                            target_he.edges.append(edge)
                            target_he.ports.append(source)
                            port_to_hyperedge[source] = target_he
                        elif target_he is None:
                            source_he.edges.append(edge)
                            source_he.ports.append(target)
                            port_to_hyperedge[target] = source_he
                        elif source_he is target_he:
                            source_he.edges.append(edge)
                        else:
                            source_he.edges.append(edge)
                            for port in target_he.ports:
                                port_to_hyperedge[port] = source_he
                            source_he.edges.extend(target_he.edges)
                            source_he.ports.extend(target_he.ports)
                            active.pop(target_he)
        hyperedges = list(active)
        left_reference = left[0].layer
        right_reference = right[0].layer
        for hyperedge in hyperedges:
            hyperedge.upper_left = source_count
            hyperedge.upper_right = target_count
            for port in hyperedge.ports:
                position = self.port_positions[port]
                if port.owner.layer is left_reference:
                    if position < hyperedge.upper_left:
                        hyperedge.upper_left = position
                    if position > hyperedge.lower_left:
                        hyperedge.lower_left = position
                elif port.owner.layer is right_reference:
                    if position < hyperedge.upper_right:
                        hyperedge.upper_right = position
                    if position > hyperedge.lower_right:
                        hyperedge.lower_right = position
        return (hyperedges, target_count)

    def count_crossings(self, left, right):
        hyperedges, target_count = self._build_hyperedges(left, right)
        _source_sort(hyperedges, _compare_hyperedges)
        south = [hyperedge.upper_right for hyperedge in hyperedges]
        compress = [0] * (target_count + 1)
        for position in south:
            compress[position] = 1
        delta = 0
        for index in range(len(compress)):
            if compress[index] == 1:
                compress[index] = delta
            else:
                delta -= 1
        q = 0
        for index in range(len(south)):
            south[index] += compress[south[index]]
            q = max(q, south[index] + 1)
        first_index = 1
        while first_index < q:
            first_index *= 2
        tree_size = 2 * first_index - 1
        first_index -= 1
        tree = [0.0] * tree_size
        crossings = 0.0
        for position in south:
            index = position + first_index
            tree[index] += 1.0
            while index > 0:
                if index % 2 > 0:
                    crossings += tree[index + 1]
                index = _signed(int((index - 1) / 2), 32)
                tree[index] += 1.0
        for side in ('left', 'right'):
            corners = []
            for hyperedge in hyperedges:
                upper = hyperedge.upper_left if side == 'left' else hyperedge.upper_right
                lower = hyperedge.lower_left if side == 'left' else hyperedge.lower_right
                corners.append(_Corner(hyperedge, upper, lower, 'UPPER'))
                corners.append(_Corner(hyperedge, lower, upper, 'LOWER'))
            _source_sort(corners, _compare_corners)
            opened = 0.0
            for corner in corners:
                if corner.type == 'UPPER':
                    opened += 1.0
                elif corner.type == 'LOWER':
                    opened -= 1.0
                    crossings += opened
        return crossings
