# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P13D in references/e13-kernel-sources.json.
# Native identity slot adapter; no GWT collection runtime transplanted.
"""Actual neighbouring-node north/south crossing scores used by GreedySwitch."""
from .crossing_counter import _side_view
from .two_node_crossings import _ordered_side_ports


def _origin_port(node):
    return node.ports[0].properties.get('ORIGIN')


def _number_of_ns_edges(node, side):
    count = 0.0
    for port in _side_view(node, side):
        if port.properties.get('PORT_DUMMY') is not None:
            count += 1.0
    return count


def _first_degree(node, side):
    ports = _side_view(node, side)
    if not ports:
        return 0.0
    return float(len(ports[0].incoming_edges) + len(ports[0].outgoing_edges))


class NorthSouthEdgeNeighbouringNodeCrossingsCounter:
    def __init__(self, nodes):
        self.layer = nodes
        self.port_positions = {}
        self.upper_lower_crossings = 0.0
        self.lower_upper_crossings = 0.0
        for node in nodes:
            for side in ('SOUTH', 'NORTH'):
                position = 0
                for port in _ordered_side_ports(node, side):
                    self.port_positions[port] = position
                    position += 1

    def count_two_ns_dummies(self, further, closer):
        if self.port_positions[_origin_port(further)] > self.port_positions[_origin_port(closer)]:
            self.upper_lower_crossings = _first_degree(closer, 'EAST')
            self.lower_upper_crossings = _first_degree(further, 'WEST')
        else:
            self.upper_lower_crossings = _first_degree(closer, 'WEST')
            self.lower_upper_crossings = _first_degree(further, 'EAST')

    def process_normal_with_long_edge_dummy(self, upper, lower):
        if upper.type == 'NORMAL' and lower.type == 'LONG_EDGE':
            self.upper_lower_crossings = _number_of_ns_edges(upper, 'SOUTH')
            self.lower_upper_crossings = _number_of_ns_edges(upper, 'NORTH')
        if lower.type == 'NORMAL' and upper.type == 'LONG_EDGE':
            self.upper_lower_crossings = _number_of_ns_edges(lower, 'NORTH')
            self.lower_upper_crossings = _number_of_ns_edges(lower, 'SOUTH')

    def count_crossings(self, upper, lower):
        self.upper_lower_crossings = 0.0
        self.lower_upper_crossings = 0.0
        if upper.type == 'NORTH_SOUTH_PORT' and lower.type == 'NORTH_SOUTH_PORT' and upper.properties.get('ORIGIN') is lower.properties.get('ORIGIN'):
            if _origin_port(upper).side == 'NORTH':
                self.count_two_ns_dummies(upper, lower)
            else:
                self.count_two_ns_dummies(lower, upper)
        if upper.type == 'NORTH_SOUTH_PORT' and lower.type == 'LONG_EDGE':
            if _origin_port(upper).side == 'NORTH':
                self.upper_lower_crossings = 1.0
            else:
                self.lower_upper_crossings = 1.0
        elif lower.type == 'NORTH_SOUTH_PORT' and upper.type == 'LONG_EDGE':
            if _origin_port(lower).side == 'NORTH':
                self.lower_upper_crossings = 1.0
            else:
                self.upper_lower_crossings = 1.0
        self.process_normal_with_long_edge_dummy(upper, lower)
