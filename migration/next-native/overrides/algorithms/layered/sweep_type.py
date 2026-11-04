# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P11A in references/e13-kernel-sources.json.
# Native NodeInfo view uses binary64 math; no runtime collection transplanted.
"""Actual path-influence decision for a source GraphInfo view."""
from dataclasses import dataclass
from .crossing_counter import _side_view
from .ports import is_order_fixed

@dataclass(eq=False)
class NodeInfo:
    connected_edges: float = 0.0
    hierarchical_influence: float = 0.0
    random_influence: float = 0.0

def _has_connected_port(ports):
    return any((port.incoming_edges or port.outgoing_edges for port in ports))

def _outgoing_edges(node):
    for port in node.ports:
        yield from port.outgoing_edges

class LayerSweepTypeDecider:

    def __init__(self, graph_data):
        self.graph_data = graph_data
        self.node_info = [None] * len(graph_data.current_node_order)

    def init_at_layer_level(self, layer_index, node_order):
        node_order[layer_index][0].layer.id = layer_index
        self.node_info[layer_index] = [None] * len(node_order[layer_index])

    def init_at_node_level(self, layer_index, node_index, node_order):
        node_order[layer_index][node_index].id = node_index
        self.node_info[layer_index][node_index] = NodeInfo()

    def init_at_edge_level(self, layer_index, node_index, port_index, edge_index, edge, node_order):
        pass

    def init_at_port_level(self, layer_index, node_index, port_index, node_order):
        pass

    def init_after_traversal(self):
        pass

    def _info(self, node):
        return self.node_info[node.layer.id][node.id]

    def transfer_info_to(self, current, target):
        target_info = self._info(target)
        target_info.hierarchical_influence += current.hierarchical_influence
        target_info.random_influence += current.random_influence
        target_info.connected_edges += current.connected_edges
        target_info.connected_edges += 1.0

    def use_bottom_up(self):
        data = self.graph_data
        boundary = data.l_graph.properties.get('CROSSING_MINIMIZATION_HIERARCHICAL_SWEEPINESS', 0.1)
        if boundary < -1 or not data.has_parent:
            return True
        if is_order_fixed(data.parent.properties.get('PORT_CONSTRAINTS', 'UNDEFINED')):
            return True
        if len(_side_view(data.parent, 'EAST')) < 2 and len(_side_view(data.parent, 'WEST')) < 2:
            return True
        if data.cross_minimizer.is_deterministic():
            return False
        paths_to_random = 0.0
        paths_to_hierarchical = 0.0
        ns_dummies = []
        for layer in data.current_node_order:
            for node in layer:
                if node.type == 'NORTH_SOUTH_PORT':
                    ns_dummies.append(node)
                    continue
                current = self._info(node)
                if node.type == 'EXTERNAL_PORT':
                    current.hierarchical_influence = 1.0
                    if node.properties.get('ORIGIN').side == 'EAST':
                        paths_to_hierarchical += current.connected_edges
                else:
                    west = _side_view(node, 'WEST')
                    if not west or not _has_connected_port(west):
                        current.random_influence = 1.0
                    else:
                        east = _side_view(node, 'EAST')
                        if not east or not _has_connected_port(east):
                            paths_to_random += current.connected_edges
                for edge in _outgoing_edges(node):
                    paths_to_random += current.random_influence
                    paths_to_hierarchical += current.hierarchical_influence
                    self.transfer_info_to(current, edge.target.owner)
                for port in _side_view(node, 'NORTH') + _side_view(node, 'SOUTH'):
                    dummy = port.properties.get('PORT_DUMMY')
                    if dummy is not None:
                        paths_to_random += current.random_influence
                        paths_to_hierarchical += current.hierarchical_influence
                        self.transfer_info_to(current, dummy)
            for node in ns_dummies:
                current = self._info(node)
                for edge in _outgoing_edges(node):
                    paths_to_random += current.random_influence
                    paths_to_hierarchical += current.hierarchical_influence
                    self.transfer_info_to(current, edge.target.owner)
            ns_dummies.clear()
        all_paths = paths_to_random + paths_to_hierarchical
        normalized = float('inf') if all_paths == 0 else (paths_to_random - paths_to_hierarchical) / all_paths
        return normalized >= boundary
