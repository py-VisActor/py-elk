# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P09A in references/e13-kernel-sources.json.
# Source indexed slots represented by native port-identity maps; no runtime copied.
# Actual rank producer; complete distribution/counters/scheduler are separate.
"""Actual port-rank producer; distribution/reordering/counters are separate."""

class _PortRanker:

    def __init__(self, num_layers):
        self.in_layer_ports = []
        self.node_positions = [None] * num_layers
        self.n_ports = 0
        self._ports = []
        self.min_barycenter = 0.0
        self.max_barycenter = 0.0

    def init_at_layer_level(self, layer_index, node_order):
        self.node_positions[layer_index] = [0] * len(node_order[layer_index])

    def init_at_node_level(self, layer_index, node_index, node_order):
        node_order[layer_index][node_index].id = node_index
        self.node_positions[layer_index][node_index] = node_index

    def init_at_port_level(self, layer_index, node_index, port_index, node_order):
        port = node_order[layer_index][node_index].ports[port_index]
        port.id = self.n_ports
        self.n_ports += 1
        self._ports.append(port)

    def init_after_traversal(self):
        self.port_ranks = {port: 0.0 for port in self._ports}
        self.port_barycenters = {port: 0.0 for port in self._ports}

    def calculate_port_ranks(self, layer, port_type):
        consumed = 0.0
        for node in layer:
            consumed += self.calculate_node_port_ranks(node, consumed, port_type)

class NodeRelativePortRanker(_PortRanker):

    def calculate_node_port_ranks(self, node, rank_sum, port_type):
        if port_type == 'INPUT':
            ports = [port for port in node.ports if port.incoming_edges]
            count = len(ports)
            north_count = sum((port.side == 'NORTH' for port in ports))
            increment = 1 / (count + 1)
            north_pos = rank_sum + north_count * increment
            rest_pos = rank_sum + 1 - increment
            for port in ports:
                if port.side == 'NORTH':
                    self.port_ranks[port] = north_pos
                    north_pos -= increment
                else:
                    self.port_ranks[port] = rest_pos
                    rest_pos -= increment
        elif port_type == 'OUTPUT':
            ports = [port for port in node.ports if port.outgoing_edges]
            increment = 1 / (len(ports) + 1)
            position = rank_sum + increment
            for port in ports:
                self.port_ranks[port] = position
                position += increment
        else:
            raise ValueError('Port type is undefined')
        return 1.0

class LayerTotalPortRanker(_PortRanker):

    def calculate_node_port_ranks(self, node, rank_sum, port_type):
        if port_type == 'INPUT':
            ports = [port for port in node.ports if port.incoming_edges]
            count = len(ports)
            north_count = sum((port.side == 'NORTH' for port in ports))
            north_pos = rank_sum + north_count
            rest_pos = rank_sum + count
            for port in ports:
                if port.side == 'NORTH':
                    self.port_ranks[port] = north_pos
                    north_pos -= 1
                else:
                    self.port_ranks[port] = rest_pos
                    rest_pos -= 1
            return float(count)
        if port_type == 'OUTPUT':
            position = 0.0
            for port in node.ports:
                if port.outgoing_edges:
                    position += 1
                    self.port_ranks[port] = rank_sum + position
            return position
        raise ValueError('Port type is undefined')
