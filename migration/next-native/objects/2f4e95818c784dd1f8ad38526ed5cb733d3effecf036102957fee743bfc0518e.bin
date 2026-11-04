# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P09B in references/e13-kernel-sources.json.
# Existing Apache-noticed GWT sort/RNG helpers called unchanged.
# Native intrinsic min/max adapter is original host code; no runtime transplanted.
# Actual distribution; complete crossing counters/scheduler remain separate.
"""Actual port distribution math; whole crossing counts/scheduler are separate."""
import math
from .port_ranks import NodeRelativePortRanker, LayerTotalPortRanker
from .ports import _compare_side, _divide, _source_sort, double_compare, is_order_fixed

def _minimum(left, right):
    if math.isnan(left) or math.isnan(right):
        return float('nan')
    if left == 0 and right == 0:
        return -0.0 if math.copysign(1, left) < 0 or math.copysign(1, right) < 0 else 0.0
    return left if left < right else right

def _maximum(left, right):
    if math.isnan(left) or math.isnan(right):
        return float('nan')
    if left == 0 and right == 0:
        return 0.0 if math.copysign(1, left) > 0 or math.copysign(1, right) > 0 else -0.0
    return left if left > right else right

class _BarycenterPortDistribution:

    def _position_of(self, node):
        return self.node_positions[node.layer.id][node.id]

    def _deal_with_north_south_ports(self, absurdly_large, port, dummy):
        incoming = False
        outgoing = False
        for dummy_port in dummy.ports:
            if dummy_port.properties.get('ORIGIN') is port:
                if dummy_port.outgoing_edges:
                    outgoing = True
                elif dummy_port.incoming_edges:
                    incoming = True
        if incoming and incoming ^ outgoing:
            position = float(self._position_of(dummy))
            return -position if port.side == 'NORTH' else absurdly_large - position
        if outgoing and incoming ^ outgoing:
            position = float(self._position_of(dummy))
            return position + 1
        if incoming and outgoing:
            return 0.0 if port.side == 'NORTH' else absurdly_large / 2
        return 0.0

    def _iterate_ports(self, node, ports):
        self.min_barycenter = 0.0
        self.max_barycenter = 0.0
        absurdly_large = float(2 * len(node.layer.nodes) + 1)
        for port in ports:
            north_south = port.side in ('NORTH', 'SOUTH')
            total = 0.0
            if north_south:
                dummy = port.properties.get('PORT_DUMMY')
                if dummy is None:
                    continue
                total += self._deal_with_north_south_ports(absurdly_large, port, dummy)
            else:
                in_layer = False
                for edge in port.outgoing_edges:
                    connected = edge.target
                    if connected.owner.layer is node.layer:
                        self.in_layer_ports.append(port)
                        in_layer = True
                        break
                    total += self.port_ranks[connected]
                if in_layer:
                    continue
                for edge in port.incoming_edges:
                    connected = edge.source
                    if connected.owner.layer is node.layer:
                        self.in_layer_ports.append(port)
                        in_layer = True
                        break
                    total -= self.port_ranks[connected]
                if in_layer:
                    continue
            degree = len(port.incoming_edges) + len(port.outgoing_edges)
            if degree > 0:
                self.port_barycenters[port] = total / degree
                self.min_barycenter = _minimum(self.min_barycenter, self.port_barycenters[port])
                self.max_barycenter = _maximum(self.max_barycenter, self.port_barycenters[port])
            elif north_south:
                self.port_barycenters[port] = total

    def _calculate_in_layer_barycenters(self, node):
        node_position = self._position_of(node) + 1
        layer_size = len(node.layer.nodes) + 1
        for port in self.in_layer_ports:
            total = 0.0
            count = 0
            for edge in port.incoming_edges:
                connected = edge.source
                if connected.owner.layer is node.layer:
                    total += self._position_of(connected.owner) + 1
                    count += 1
            for edge in port.outgoing_edges:
                connected = edge.target
                if connected.owner.layer is node.layer:
                    total += self._position_of(connected.owner) + 1
                    count += 1
            barycenter = _divide(total, count)
            if port.side == 'EAST':
                self.port_barycenters[port] = self.min_barycenter - barycenter if barycenter < node_position else self.max_barycenter + (layer_size - barycenter)
            elif port.side == 'WEST':
                self.port_barycenters[port] = self.max_barycenter + barycenter if barycenter < node_position else self.min_barycenter - (layer_size - barycenter)

    def distribute_ports(self, node, ports):
        self.in_layer_ports.clear()
        self._iterate_ports(node, ports)
        if self.in_layer_ports:
            self._calculate_in_layer_barycenters(node)

    def compare(self, first, second):
        different_side = _compare_side(first, second)
        if different_side != 0:
            return different_side
        a = self.port_barycenters[first]
        b = self.port_barycenters[second]
        if a == 0 and b == 0:
            return 0
        if a == 0:
            return -1
        if b == 0:
            return 1
        return double_compare(a, b)

    def distribute_node(self, node, side):
        if not is_order_fixed(node.properties.get('PORT_CONSTRAINTS', 'UNDEFINED')):
            for selected_side in (side, 'SOUTH', 'NORTH'):
                self.distribute_ports(node, (port for port in node.ports if port.side == selected_side))
            _source_sort(node.ports, self.compare)

    def distribute_ports_while_sweeping(self, node_order, current_index, forward):
        free = node_order[current_index]
        for index, node in enumerate(free):
            self.node_positions[node.layer.id][node.id] = index
        side = 'WEST' if forward else 'EAST'
        not_first = current_index != 0 if forward else current_index != len(node_order) - 1
        if not_first:
            fixed = node_order[current_index - 1 if forward else current_index + 1]
            self.calculate_port_ranks(fixed, 'OUTPUT' if forward else 'INPUT')
            for node in free:
                self.distribute_node(node, side)
            self.calculate_port_ranks(free, 'INPUT' if forward else 'OUTPUT')
            for node in fixed:
                if getattr(node, 'nested_graph', None) is None:
                    self.distribute_node(node, 'EAST' if forward else 'WEST')
        else:
            for node in free:
                self.distribute_node(node, side)
        return False

class NodeRelativePortDistributor(_BarycenterPortDistribution, NodeRelativePortRanker):
    pass

class LayerTotalPortDistributor(_BarycenterPortDistribution, LayerTotalPortRanker):
    pass

def create_barycenter_port_distributor(random, node_order):
    kind = NodeRelativePortDistributor if random.next(1) != 0 else LayerTotalPortDistributor
    return kind(len(node_order))
