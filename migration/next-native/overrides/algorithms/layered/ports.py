# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Copyright (c) Kiel University and others.
# Port-list insertion/merge helpers: Copyright 2008 Google Inc., Apache-2.0.
# Python adaptation keeps the fixed comparison/buffer sequence, uses native
# lists and preserves mixed-index behavior; see _licenses/NOTICE-GWT-Ports.md.
# Ported from fixed elkjs 0.12.1 lib/elk-worker.js, commit
# 624ae90aa37110033a8af59c5ccbb292708b4317; worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# E13-P01 source review: references/e13-ports-sources.json.
# This independent migration workspace is not the current release package.
"""Source port initialization, with typed internal properties and geometry.

Option parsing and graph import supply these inputs. This module adds no node
or port count restriction and performs no public option/admission selection.
"""
from __future__ import annotations

import math
import struct

from .graph import LPort, Vec2


def _divide(left: float, right: float) -> float:
    """Native IEEE division for JS intrinsic `/`, including a zero axis."""
    if right != 0:
        return left / right
    if left == 0 or math.isnan(left) or math.isnan(right):
        return math.nan
    return math.copysign(math.inf, math.copysign(1.0, left) * math.copysign(1.0, right))


def is_side_fixed(constraints: str) -> bool:
    return constraints not in ("FREE", "UNDEFINED")


def is_order_fixed(constraints: str) -> bool:
    return constraints in ("FIXED_ORDER", "FIXED_RATIO", "FIXED_POS")


def set_side(port: LPort, side: str) -> None:
    """Fixed LPort.setSide: a supplied anchor survives side changes."""
    if side is None:
        raise TypeError("A port side is required")
    port.side = side
    if not port.explicitly_supplied_port_anchor:
        if side == "NORTH":
            port.anchor.x, port.anchor.y = port.size.x / 2, 0.0
        elif side == "EAST":
            port.anchor.x, port.anchor.y = port.size.x, port.size.y / 2
        elif side == "SOUTH":
            port.anchor.x, port.anchor.y = port.size.x / 2, port.size.y
        elif side == "WEST":
            port.anchor.x, port.anchor.y = 0.0, port.size.y / 2


def calc_port_offset(port: LPort, side: str) -> float:
    node = port.owner
    if side == "NORTH":
        return -(port.pos.y + port.size.y)
    if side == "EAST":
        return port.pos.x - node.size.x
    if side == "SOUTH":
        return port.pos.y - node.size.y
    if side == "WEST":
        return -(port.pos.x + port.size.x)
    return 0.0


def calc_port_side(port: LPort, direction: str) -> str:
    node = port.owner
    node_width, node_height = node.size.x, node.size.y
    if node_width <= 0 and node_height <= 0:
        return "UNDEFINED"
    xpos, ypos, width, height = port.pos.x, port.pos.y, port.size.x, port.size.y
    if direction in ("RIGHT", "LEFT"):
        if xpos < 0:
            return "WEST"
        if xpos + width > node_width:
            return "EAST"
    elif direction in ("DOWN", "UP"):
        if ypos < 0:
            return "NORTH"
        if ypos + height > node_height:
            return "SOUTH"
    width_percent = _divide(xpos + width / 2, node_width)
    height_percent = _divide(ypos + height / 2, node_height)
    if width_percent + height_percent <= 1 and width_percent - height_percent <= 0:
        return "WEST"
    if width_percent + height_percent >= 1 and width_percent - height_percent >= 0:
        return "EAST"
    return "NORTH" if height_percent < 0.5 else "SOUTH"


def initialize_port(port: LPort, port_constraints: str, direction: str,
                    anchor_position: Vec2 | None = None) -> None:
    """Mirror initializePort; properties use source internal canonical names.

    The caller copies selected typed properties before this call. In particular,
    absence of PORT_BORDER_OFFSET differs from an explicit zero value.
    """
    port_side = port.side
    if port_side == "UNDEFINED" and is_side_fixed(port_constraints):
        port_side = calc_port_side(port, direction)
        set_side(port, port_side)
        if ("PORT_BORDER_OFFSET" not in port.properties and port_side != "UNDEFINED"
                and (port.pos.x != 0 or port.pos.y != 0)):
            port.properties["PORT_BORDER_OFFSET"] = calc_port_offset(port, port_side)
    if port_constraints == "FIXED_RATIO":
        ratio = 0.0
        if port_side in ("NORTH", "SOUTH"):
            node_width = port.owner.size.x
            if node_width > 0:
                ratio = port.pos.x / node_width
        elif port_side in ("EAST", "WEST"):
            node_height = port.owner.size.y
            if node_height > 0:
                ratio = port.pos.y / node_height
        port.properties["PORT_RATIO_OR_POSITION"] = ratio
    if anchor_position is not None:
        port.anchor.x, port.anchor.y = anchor_position.x, anchor_position.y
        port.explicitly_supplied_port_anchor = True
    elif is_side_fixed(port_constraints) and port_side != "UNDEFINED":
        if port_side == "NORTH":
            port.anchor.x = port.size.x / 2
        elif port_side == "EAST":
            port.anchor.x, port.anchor.y = port.size.x, port.size.y / 2
        elif port_side == "SOUTH":
            port.anchor.x, port.anchor.y = port.size.x / 2, port.size.y
        elif port_side == "WEST":
            port.anchor.y = port.size.y / 2
    else:
        port.anchor.x, port.anchor.y = port.size.x / 2, port.size.y / 2


_SIDE_ORDER = {"UNDEFINED": 0, "NORTH": 1, "EAST": 2, "SOUTH": 3, "WEST": 4}


def double_compare(left: float, right: float) -> int:
    """Original IEEE bit-order adapter to the observed Double total order.

    All NaNs form the final equivalence class. For other values, mapping the
    IEEE sign/magnitude bits to a monotone unsigned key also separates -0/+0.
    This host implementation does not copy the generated GWT comparator.
    """
    left_nan, right_nan = math.isnan(left), math.isnan(right)
    if left_nan or right_nan:
        return (left_nan > right_nan) - (left_nan < right_nan)
    def key(value):
        bits = struct.unpack(">Q", struct.pack(">d", value))[0]
        return (~bits & ((1 << 64) - 1)) if bits >> 63 else bits | (1 << 63)
    a, b = key(left), key(right)
    return (a > b) - (a < b)


def process_port_sides(graph) -> None:
    """Source PortSideProcessor traversal, including layerless nodes."""
    from .native_adapters import _read_property
    from .property_access import read_layered_scalar
    def process_node(node):
        fixed = is_side_fixed(read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0'))
        for port in node.ports:
            if not fixed or port.side == "UNDEFINED":
                dummy = _read_property(port, 'PORT_DUMMY')
                side = (_read_property(dummy, 'EXT_PORT_SIDE') if dummy is not None else
                        "EAST" if len(port.incoming_edges) - len(port.outgoing_edges) < 0 else "WEST")
                set_side(port, side)
        if not fixed:
            node.properties["PORT_CONSTRAINTS"] = "FIXED_SIDE"
    for node in graph.layerless_nodes:
        process_node(node)
    for layer in graph.layers:
        for node in layer.nodes:
            process_node(node)


def _compare_side(left: LPort, right: LPort) -> int:
    return _SIDE_ORDER[left.side] - _SIDE_ORDER[right.side]


def _compare_fixed(left: LPort, right: LPort) -> int:
    from .property_access import read_layered_scalar
    constraints = read_layered_scalar(left.owner, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
    if _compare_side(left, right) != 0 or not is_order_fixed(constraints):
        return 0
    if constraints == "FIXED_ORDER":
        first, second = left.properties.get("PORT_INDEX"), right.properties.get("PORT_INDEX")
        if first is not None and second is not None:
            difference = first - second
            if difference != 0:
                return difference
    if left.side == "NORTH":
        return double_compare(left.pos.x, right.pos.x)
    if left.side == "EAST":
        return double_compare(left.pos.y, right.pos.y)
    if left.side == "SOUTH":
        return double_compare(right.pos.x, left.pos.x)
    if left.side == "WEST":
        return double_compare(right.pos.y, left.pos.y)
    raise RuntimeError("Port side is undefined")


def _compare_combined(left: LPort, right: LPort) -> int:
    side = _compare_side(left, right)
    return side if side != 0 else _compare_fixed(left, right)


def _real_degree(port: LPort, *, incoming: bool) -> int:
    return sum(not edge.properties.get("REVERSED", False)
               for edge in (port.incoming_edges if incoming else port.outgoing_edges))


def _compare_degree(left: LPort, right: LPort) -> int:
    if _compare_side(left, right) != 0:
        return 0
    if left.side == "EAST":
        return _real_degree(right, incoming=False) - _real_degree(left, incoming=False)
    if left.side == "WEST":
        return _real_degree(left, incoming=True) - _real_degree(right, incoming=True)
    return 0


def _find_side_range(ports, side):
    """Literal generated low/high and stale-low read, including empty input."""
    if not ports:
        return 0, 0
    low, current = 0, ports[0].side
    lower, upper = _SIDE_ORDER[side], _SIDE_ORDER[side] + 1
    while low < len(ports) - 1 and _SIDE_ORDER[current] < lower:
        low += 1
        current = ports[low].side
    high = low
    while high < len(ports) - 1 and _SIDE_ORDER[current] < upper:
        high += 1
        current = ports[low].side
    return low, high


def _reverse_south_west(ports):
    if len(ports) <= 1:
        return
    for side in ("SOUTH", "WEST"):
        low, high = _find_side_range(ports, side)
        if high > low + 2:
            for i in range((high - low) // 2):
                ports[low + i], ports[high - i - 1] = ports[high - i - 1], ports[low + i]


def _cache_sides(node):
    ranges, first, current = {}, 0, "NORTH"
    for index, port in enumerate(node.ports):
        if port.side != current:
            if first != index:
                ranges[current] = (first, index)
            current, first = port.side, index
    ranges[current] = (first, len(node.ports))
    node.port_side_indices = ranges


def _source_sort(items, compare):
    """Adapt the fixed GWT Arrays comparator insertion/merge process.

    Source callers sort the complete array with a non-null comparator. The
    comparator can be non-transitive for mixed present/missing port indices,
    so changing the comparison schedule to Timsort would change behavior.
    """
    def merge_sort(temp, array, low, high, offset):
        if high - low < 7:
            for i in range(low + 1, high):
                j = i
                while j > low and compare(array[j - 1], array[j]) > 0:
                    array[j], array[j - 1] = array[j - 1], array[j]
                    j -= 1
            return
        temp_low, temp_high = low + offset, high + offset
        temp_mid = temp_low + ((temp_high - temp_low) >> 1)
        merge_sort(array, temp, temp_low, temp_mid, -offset)
        merge_sort(array, temp, temp_mid, temp_high, -offset)
        if compare(temp[temp_mid - 1], temp[temp_mid]) <= 0:
            while low < high:
                array[low] = temp[temp_low]
                low += 1
                temp_low += 1
            return
        top = temp_mid
        while low < high:
            if top >= temp_high or (temp_low < temp_mid and compare(temp[temp_low], temp[top]) <= 0):
                array[low] = temp[temp_low]
                temp_low += 1
            else:
                array[low] = temp[top]
                top += 1
            low += 1
    merge_sort(list(items), items, 0, len(items), 0)


def sort_port_lists(graph, strategy: str = "INPUT_ORDER") -> None:
    """Source PortListSorter, including its actual comparator sort process."""
    from .property_access import read_layered_scalar
    for layer in graph.layers:
        for node in layer.nodes:
            constraints = read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
            if is_order_fixed(constraints):
                _source_sort(node.ports, _compare_combined)
            elif is_side_fixed(constraints):
                _source_sort(node.ports, _compare_side)
                _reverse_south_west(node.ports)
                if strategy == "PORT_DEGREE":
                    _source_sort(node.ports, _compare_degree)
            node.port_sides_cached = True
            _cache_sides(node)
