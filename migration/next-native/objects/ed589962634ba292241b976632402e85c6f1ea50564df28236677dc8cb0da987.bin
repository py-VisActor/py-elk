# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P10E in references/e13-kernel-sources.json.
# Native identity-keyed view of the one shared source scratch buffer.
"""Real crossing dispatch and the source initializable traversal protocol."""
from .crossing_counter import CrossingsCounter, _connected_edges
from .hyperedge_crossings import HyperedgeCrossingsCounter


def initialize_crossing_receivers(initializables, order):
    """Call every actual hook in init_0 order; absent hooks are errors."""
    layer_index = 0
    while layer_index < len(order):
        for receiver in initializables:
            receiver.init_at_layer_level(layer_index, order)
        node_index = 0
        while node_index < len(order[layer_index]):
            for receiver in initializables:
                receiver.init_at_node_level(layer_index, node_index, order)
            ports = order[layer_index][node_index].ports
            port_index = 0
            while port_index < len(ports):
                for receiver in initializables:
                    receiver.init_at_port_level(layer_index, node_index, port_index, order)
                port = ports[port_index]
                edge_index = 0
                for edge in _connected_edges(port):
                    for receiver in initializables:
                        receiver.init_at_edge_level(
                            layer_index, node_index, port_index, edge_index, edge, order
                        )
                        edge_index += 1
                port_index += 1
            node_index += 1
        layer_index += 1
    for receiver in initializables:
        receiver.init_after_traversal()


class AllCrossingsCounter:
    def __init__(self, node_order):
        self.in_layer_edge_counts = [0] * len(node_order)
        self.has_north_south_ports = [False] * len(node_order)
        self.has_hyper_edges_east_of_index = [False] * len(node_order)
        self.n_ports = 0
        # Original host bindings for source portPositions[port.id], not scores.
        self._registered_ports = []

    def init_at_layer_level(self, layer_index, node_order):
        pass  # The fixed source layer hook is exactly empty.

    def init_at_node_level(self, layer_index, node_index, node_order):
        node = node_order[layer_index][node_index]
        self.has_north_south_ports[layer_index] = (
            int(self.has_north_south_ports[layer_index])
            | int(node.type == "NORTH_SOUTH_PORT")
        )

    def init_at_port_level(self, layer_index, node_index, port_index, node_order):
        port = node_order[layer_index][node_index].ports[port_index]
        port.id = self.n_ports
        self.n_ports += 1
        self._registered_ports.append(port)
        if len(port.outgoing_edges) + len(port.incoming_edges) > 1:
            if port.side == "EAST":
                self.has_hyper_edges_east_of_index[layer_index] = True
            elif port.side == "WEST" and layer_index > 0:
                self.has_hyper_edges_east_of_index[layer_index - 1] = True

    def init_at_edge_level(self, layer_index, node_index, port_index, edge_index, edge, node_order):
        port = node_order[layer_index][node_index].ports[port_index]
        if edge.source is port and edge.source.owner.layer is edge.target.owner.layer:
            self.in_layer_edge_counts[layer_index] += 1

    def init_after_traversal(self):
        positions = {port: 0 for port in self._registered_ports}
        self.hyperedge_crossings_counter = HyperedgeCrossingsCounter(positions)
        self.crossing_counter = CrossingsCounter(positions)

    def count_all_crossings(self, current_order):
        if len(current_order) == 0:
            return 0
        crossings = self.crossing_counter.count_in_layer_crossings_on_side(current_order[0], "WEST")
        crossings += self.crossing_counter.count_in_layer_crossings_on_side(current_order[-1], "EAST")
        for layer_index in range(len(current_order)):
            crossings += self.count_crossings_at(layer_index, current_order)
        return crossings

    def count_crossings_at(self, layer_index, current_order):
        total = 0
        left = current_order[layer_index]
        if layer_index < len(current_order) - 1:
            right = current_order[layer_index + 1]
            if self.has_hyper_edges_east_of_index[layer_index]:
                total = self.hyperedge_crossings_counter.count_crossings(left, right)
                total += self.crossing_counter.count_in_layer_crossings_on_side(left, "EAST")
                total += self.crossing_counter.count_in_layer_crossings_on_side(right, "WEST")
            else:
                total = self.crossing_counter.count_crossings_between_layers(left, right)
        if self.has_north_south_ports[layer_index]:
            total += self.crossing_counter.count_north_south_port_crossings_in_layer(left)
        return total
