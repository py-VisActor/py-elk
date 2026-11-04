# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P10A in references/e13-kernel-sources.json.
# Native shallow-copy/commuting identity-set adapters; no runtime transplanted.
# Existing Apache-noticed GWT sort is called unchanged.
"""Actual sweep order capture/copy and NS-aware transfer to live graph."""
from .ports import _cache_sides, _compare_combined, _source_sort, is_order_fixed, set_side

def deep_copy_node_order(node_order):
    if node_order is None:
        return None
    return [list(row) for row in node_order]

def assert_correct_port_sides(dummy):
    original = dummy.properties.get('IN_LAYER_LAYOUT_UNIT')
    source_port = dummy.ports[0].properties.get('ORIGIN')
    for port in original.ports:
        if port is source_port:
            if port.side == 'NORTH' and dummy.id > original.id:
                set_side(port, 'SOUTH')
                if port.explicitly_supplied_port_anchor:
                    height = float(port.size.y)
                    anchor_y = float(port.anchor.y)
                    port.anchor.y = height - anchor_y
            elif port.side == 'SOUTH' and original.id > dummy.id:
                set_side(port, 'NORTH')
                if port.explicitly_supplied_port_anchor:
                    height = float(port.size.y)
                    anchor_y = float(port.anchor.y)
                    port.anchor.y = -(height - anchor_y)
            break
    return original

class SweepCopy:

    def __init__(self, node_order_or_copy):
        if isinstance(node_order_or_copy, SweepCopy):
            self.node_order = deep_copy_node_order(node_order_or_copy.node_order)
            self.port_orders = list(node_order_or_copy.port_orders)
        else:
            self.node_order = deep_copy_node_order(node_order_or_copy)
            self.port_orders = [[list(node.ports) for node in row] for row in node_order_or_copy]

    def transfer_node_and_port_orders_to_graph(self, graph):
        update_order = []
        seen = set()
        for layer_index, layer in enumerate(graph.layers):
            north_south_dummies = []
            for node_index in range(len(layer.nodes)):
                node = self.node_order[layer_index][node_index]
                node.id = node_index
                if node.type == 'NORTH_SOUTH_PORT':
                    north_south_dummies.append(node)
                layer.nodes[node_index] = node
                node.ports.clear()
                node.ports.extend(self.port_orders[layer_index][node_index])
                if not is_order_fixed(node.properties.get('PORT_CONSTRAINTS', 'UNDEFINED')):
                    node.properties['PORT_CONSTRAINTS'] = 'FIXED_ORDER'
            for dummy in north_south_dummies:
                original = assert_correct_port_sides(dummy)
                for node in (original, dummy):
                    if id(node) not in seen:
                        seen.add(id(node))
                        update_order.append(node)
        for node in update_order:
            _source_sort(node.ports, _compare_combined)
            node.port_sides_cached = True
            _cache_sides(node)
