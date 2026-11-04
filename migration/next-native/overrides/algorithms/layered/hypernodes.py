# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 HypernodesProcessor37968-38089.
"""Actual bend-based hypernode movement and N/S port rewiring."""
from ...execution.diagnostics import BasicProgressMonitor
from .graph import LPort, set_port_owner, set_source, set_target
from .native_properties import CanonicalPropertyMap
from .ports import set_side
from .property_access import read_layered_scalar
from .long_edges_general import _absolute_anchor
from .orthogonal_general import get_junction_points
from .port_label_placement import _minimum


def _port(node, side):
    port = LPort(properties=CanonicalPropertyMap())
    port.integer_box_identities = port.properties.integer_boxes
    set_port_owner(port, node)
    set_side(port, side)
    return port


def move_hypernode(graph, node, right):
    bends = []
    bend_x = diff_x = diff_y = 2147483647.0
    if right:
        bend_x = graph.size.x
        for port in node.ports:
            for edge in port.outgoing_edges:
                if edge.bend_points:
                    first = edge.bend_points[0]
                    if first.x < bend_x:
                        diff_x = bend_x - first.x
                        diff_y = 2147483647.0
                        bends.clear()
                        bend_x = first.x
                    if first.x <= bend_x:
                        bends.append(edge)
                        if len(edge.bend_points) > 1:
                            diff_y = _minimum(diff_y, abs(edge.bend_points[1].y - first.y))
    else:
        for port in node.ports:
            for edge in port.incoming_edges:
                if edge.bend_points:
                    last = edge.bend_points[-1]
                    if last.x > bend_x:
                        diff_x = last.x - bend_x
                        diff_y = 2147483647.0
                        bends.clear()
                        bend_x = last.x
                    if last.x >= bend_x:
                        bends.append(edge)
                        if len(edge.bend_points) > 1:
                            diff_y = _minimum(diff_y, abs(edge.bend_points[-2].y - last.y))
    if bends and diff_x > node.size.x / 2 and diff_y > node.size.y / 2:
        north = _port(node, 'NORTH')
        north.pos.x = node.size.x / 2
        south = _port(node, 'SOUTH')
        south.pos.x = node.size.x / 2
        south.pos.y = node.size.y
        for edge in bends:
            if right:
                first = edge.bend_points.pop(0)
                second = _absolute_anchor(edge.target) if len(edge.bend_points) == 0 else edge.bend_points[0]
                set_source(edge, south if second.y >= first.y else north)
            else:
                first = edge.bend_points.pop()
                second = _absolute_anchor(edge.source) if len(edge.bend_points) == 0 else edge.bend_points[-1]
                set_target(edge, south if second.y >= first.y else north)
            junctions = get_junction_points(edge)
            if junctions is not None:
                for index, point in enumerate(junctions):
                    if point.x == first.x and point.y == first.y:
                        junctions.pop(index)
                        break
        node.pos.x = bend_x - node.size.x / 2


def hypernodes_processor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Hypernodes processing', 1)
    for layer in graph.layers:
        for node in layer.nodes:
            enabled = read_layered_scalar(node, 'HYPERNODE', 'HYPERNODE')
            if type(enabled) is not bool:
                raise TypeError('Actual HYPERNODE Boolean required')
            if enabled and len(node.ports) <= 2:
                top = bottom = right = left = 0
                for port in node.ports:
                    if port.side == 'NORTH':top += 1
                    elif port.side == 'EAST':right += 1
                    elif port.side == 'SOUTH':bottom += 1
                    elif port.side == 'WEST':left += 1
                if top == 0 and bottom == 0:
                    move_hypernode(graph, node, left <= right)
    monitor.done()
