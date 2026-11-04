# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P13B in references/e13-kernel-sources.json.
# Existing Apache-noticed source sort called unchanged, native identity maps only.
"""Actual lazy two-node between-layer adjacency multiplicity counter."""
from dataclasses import dataclass
from .crossing_counter import _side_view
from .ports import _source_sort


def _ordered_side_ports(node, side):
    if side in ('NORTH', 'EAST'):
        return _side_view(node, side)
    if side in ('SOUTH', 'WEST'):
        return list(reversed(_side_view(node, side)))
    return []


@dataclass(eq=False)
class Adjacency:
    position: int
    cardinality: float = 1.0
    current_cardinality: float = 1.0

    def reset(self):
        self.current_cardinality = self.cardinality


def _compare_adjacencies(first, second):
    return -1 if first.position < second.position else 0 if first.position == second.position else 1


class AdjacencyList:
    def __init__(self, counter, node, side):
        self.counter = counter
        self.node = node
        self.side = side
        self.adjacency_list = []
        self.current_index = 0
        self.current_size = 0.0
        self.size = 0.0
        for port in _ordered_side_ports(node, side):
            for edge in port.incoming_edges if side == 'WEST' else port.outgoing_edges:
                self_loop = edge.source is not None and edge.target is not None and edge.source.owner is not None and edge.source.owner is edge.target.owner
                if not self_loop and edge.source.owner.layer is not edge.target.owner.layer:
                    adjacent_port = edge.source if side == 'WEST' else edge.target
                    position = counter.port_positions[adjacent_port]
                    if self.adjacency_list and self.adjacency_list[-1].position == position:
                        self.adjacency_list[-1].cardinality += 1.0
                        self.adjacency_list[-1].current_cardinality += 1.0
                    else:
                        self.adjacency_list.append(Adjacency(position))
                    self.size += 1.0
                    self.current_size += 1.0
        _source_sort(self.adjacency_list, _compare_adjacencies)

    def current_adjacency(self):
        return self.adjacency_list[self.current_index]

    def count_below_first(self):
        return self.current_size - self.current_adjacency().current_cardinality

    def remove_first(self):
        if self.current_size == 0:
            return
        current = self.current_adjacency()
        if current.current_cardinality == 1:
            self.current_index += 1
            if self.current_index < len(self.adjacency_list):
                self.current_adjacency().reset()
        else:
            current.current_cardinality -= 1.0
        self.current_size -= 1.0


class BetweenLayerEdgeTwoNodeCrossingsCounter:
    def __init__(self, current_node_order, free_layer_index):
        self.port_positions = {}
        self.eastern_adjacencies = {}
        self.western_adjacencies = {}
        self.current_node_order = current_node_order
        self.free_layer_index = free_layer_index
        self.upper_lower_crossings = 0.0
        self.lower_upper_crossings = 0.0
        if free_layer_index > 0:
            self._set_port_positions_for_layer(free_layer_index - 1, 'EAST')
        if free_layer_index < len(current_node_order) - 1:
            self._set_port_positions_for_layer(free_layer_index + 1, 'WEST')

    def _set_port_positions_for_layer(self, layer_index, side):
        position = 0
        for node in self.current_node_order[layer_index]:
            for port in _ordered_side_ports(node, side):
                self.port_positions[port] = position
                position += 1

    def get_adjacency_for(self, node, side, adjacencies):
        if len(adjacencies) == 0:
            for free_node in self.current_node_order[self.free_layer_index]:
                adjacencies[free_node] = AdjacencyList(self, free_node, side)
        result = adjacencies[node]
        result.current_index = 0
        result.current_size = result.size
        if result.current_size != 0:
            result.current_adjacency().reset()
        return result

    def _merge_adjacency_lists(self):
        while self.upper_adjacencies.current_size != 0 and self.lower_adjacencies.current_size != 0:
            if self.upper_adjacencies.current_adjacency().position > self.lower_adjacencies.current_adjacency().position:
                self.upper_lower_crossings += self.upper_adjacencies.current_size
                self.lower_adjacencies.remove_first()
            elif self.lower_adjacencies.current_adjacency().position > self.upper_adjacencies.current_adjacency().position:
                self.lower_upper_crossings += self.lower_adjacencies.current_size
                self.upper_adjacencies.remove_first()
            else:
                self.upper_lower_crossings += self.upper_adjacencies.count_below_first()
                self.lower_upper_crossings += self.lower_adjacencies.count_below_first()
                self.upper_adjacencies.remove_first()
                self.lower_adjacencies.remove_first()

    def _add_side_crossings(self, upper, lower, side):
        adjacencies = self.western_adjacencies if side == 'WEST' else self.eastern_adjacencies
        self.upper_adjacencies = self.get_adjacency_for(upper, side, adjacencies)
        self.lower_adjacencies = self.get_adjacency_for(lower, side, adjacencies)
        if self.upper_adjacencies.current_size == 0 or self.lower_adjacencies.current_size == 0:
            return
        self._merge_adjacency_lists()

    def _count(self, upper, lower, sides):
        self.upper_lower_crossings = 0.0
        self.lower_upper_crossings = 0.0
        if upper is lower:
            return
        for side in sides:
            self._add_side_crossings(upper, lower, side)

    def count_both_side_crossings(self, upper, lower):
        self._count(upper, lower, ('WEST', 'EAST'))

    def count_eastern_edge_crossings(self, upper, lower):
        self._count(upper, lower, ('EAST',))

    def count_western_edge_crossings(self, upper, lower):
        self._count(upper, lower, ('WEST',))
