# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Adapted from fixed elkjs 0.12.1 lib/elk-worker.js, E13-P04E.
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Real per-port label staging and source rectangle strip overlap removal.

GWT sort remains the separately attributed helper in ports.py. The active
comparator-unique collection below is an original native representation, not
a port of the TreeMap runtime. Labels carry actual caller-supplied dimensions.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field

from .cell_layout import Rectangle, _maximum
from .ports import _source_sort, double_compare


def _minimum(*values):
    return -_maximum(*(-value for value in values))


def _maxd(values):
    maximum = -sys.float_info.max
    for value in values:
        if value > maximum: maximum = value
    return maximum


@dataclass(eq=False)
class _RectangleNode:
    original: Rectangle
    rectangle: Rectangle
    overlapping: list = field(default_factory=list)


class RectangleStripOverlapRemover:
    def __init__(self, direction):
        self.direction = direction
        self.gap = 5
        self.start_coordinate = 0
        self.nodes = []

    def add(self, rectangle):
        transformed = (rectangle if self.direction in {"UP", "DOWN"}
                       else Rectangle(rectangle.y, 0, rectangle.height, rectangle.width))
        self.nodes.append(_RectangleNode(rectangle, transformed))

    @staticmethod
    def _compare_right(first, second):
        return double_compare(first.rectangle.x + first.rectangle.width,
                              second.rectangle.x + second.rectangle.width)

    def remove_overlaps(self):
        _source_sort(self.nodes, lambda a,b: double_compare(a.rectangle.x, b.rectangle.x))
        # Source TreeSet: ascending right border, retain first key on equality.
        # Overlap-list insertion order follows this active order exactly.
        active = []
        for current in self.nodes:
            while active and active[0].rectangle.x + active[0].rectangle.width < current.rectangle.x:
                active.pop(0)
            for previous in active:
                previous.overlapping.append(current)
                current.overlapping.append(previous)
            index = 0
            while index < len(active) and self._compare_right(current, active[index]) > 0:
                index += 1
            if index == len(active) or self._compare_right(current, active[index]) != 0:
                active.insert(index, current)
        placed = set()
        strip_size = 0
        for current in self.nodes:
            y = 0
            _source_sort(current.overlapping, lambda a,b: double_compare(a.rectangle.y, b.rectangle.y))
            for previous in current.overlapping:
                if previous in placed:
                    other = previous.rectangle
                    if y < other.y + other.height + self.gap and y + current.rectangle.height + self.gap > other.y:
                        y = other.y + other.height + self.gap
            current.rectangle.y = y
            placed.add(current)
            strip_size = _maximum(strip_size, current.rectangle.y + current.rectangle.height)
        for node in self.nodes:
            rectangle, original = node.rectangle, node.original
            if self.direction == "UP": original.y = self.start_coordinate - rectangle.height - rectangle.y
            elif self.direction == "DOWN": original.y += self.start_coordinate
            elif self.direction == "LEFT": original.x = self.start_coordinate - rectangle.height - rectangle.y
            elif self.direction == "RIGHT": original.x = self.start_coordinate + rectangle.y
        return strip_size


def is_first_outside_port_label_placed_differently(context, side):
    ports = context.port_contexts.get(side, ())
    if len(ports) >= 2:
        return (not ports[0].labels_next_to_port and "ALWAYS_SAME_SIDE" not in context.port_labels_placement
                and (len(ports) == 2 or "SPACE_EFFICIENT" in context.port_labels_placement))
    return False


def port_label_border_offset_for_port_side(context, side):
    padding = context.node_container.padding
    if side == "NORTH": return padding.top + context.port_label_spacing_vertical
    if side == "SOUTH": return padding.bottom + context.port_label_spacing_vertical
    if side == "EAST": return padding.right + context.port_label_spacing_horizontal
    if side == "WEST": return padding.left + context.port_label_spacing_horizontal
    return 0


def _size_rectangle(cell):
    cell.cell_rectangle.width = cell.minimum_content_area_size.x + cell.padding.left + cell.padding.right
    cell.cell_rectangle.height = cell.minimum_content_area_size.y + cell.padding.top + cell.padding.bottom
    return cell.cell_rectangle


def simple_inside_port_label_placement(context, side):
    maximum_height = 0
    border = port_label_border_offset_for_port_side(context, side)
    horizontal, vertical = context.port_label_spacing_horizontal, context.port_label_spacing_vertical
    for stage in context.port_contexts.get(side, ()):
        cell = stage.port_label_cell
        if cell is None or not cell.labels: continue
        port = stage.port
        size = port.size
        offset = port.properties.get("PORT_BORDER_OFFSET", 0)
        rect = _size_rectangle(cell)
        if side in {"NORTH", "SOUTH"}:
            rect.x = (size.x - rect.width) / 2 if stage.labels_next_to_port else size.x + horizontal
            if side == "NORTH":
                rect.y = size.y + offset + border
                cell.set_vertical_alignment("TOP")
            else:
                rect.y = -offset - border - rect.height
                cell.set_vertical_alignment("BOTTOM")
            cell.set_horizontal_alignment("CENTER")
        elif side in {"EAST", "WEST"}:
            if side == "EAST":
                rect.x = -offset - border - rect.width
                cell.set_horizontal_alignment("RIGHT")
            else:
                rect.x = size.x + offset + border
                cell.set_horizontal_alignment("LEFT")
            if stage.labels_next_to_port:
                height = rect.height if context.port_labels_treat_as_group else cell.labels[0].size.y
                rect.y = (size.y - height) / 2
            else: rect.y = size.y + vertical
            cell.set_vertical_alignment("CENTER")
        if side in {"NORTH", "SOUTH"}: maximum_height = _maximum(maximum_height, rect.height)
    if maximum_height > 0:
        context.inside_port_label_cells[side].minimum_content_area_size.y = maximum_height


def simple_outside_port_label_placement(context, side):
    special = is_first_outside_port_label_placed_differently(context, side)
    above = "ALWAYS_OTHER_SAME_SIDE" in context.port_labels_placement
    for stage in context.port_contexts.get(side, ()):
        cell = stage.port_label_cell
        if cell is None or not cell.labels: continue
        size = stage.port.size
        rect = _size_rectangle(cell)
        if side in {"NORTH", "SOUTH"}:
            if stage.labels_next_to_port:
                rect.x = (size.x - rect.width) / 2
                cell.set_horizontal_alignment("CENTER")
            elif special or above:
                rect.x = -rect.width - context.port_label_spacing_horizontal
                cell.set_horizontal_alignment("RIGHT")
            else:
                rect.x = size.x + context.port_label_spacing_horizontal
                cell.set_horizontal_alignment("LEFT")
            rect.y = (-rect.height - context.port_label_spacing_vertical if side == "NORTH"
                      else size.y + context.port_label_spacing_vertical)
            cell.set_vertical_alignment("BOTTOM" if side == "NORTH" else "TOP")
        elif side in {"EAST", "WEST"}:
            if stage.labels_next_to_port:
                height = rect.height if context.port_labels_treat_as_group else cell.labels[0].size.y
                rect.y = (size.y - height) / 2
                cell.set_vertical_alignment("CENTER")
            elif special or above:
                rect.y = -rect.height - context.port_label_spacing_vertical
                cell.set_vertical_alignment("BOTTOM")
            else:
                rect.y = size.y + context.port_label_spacing_vertical
                cell.set_vertical_alignment("TOP")
            rect.x = (size.x + context.port_label_spacing_horizontal if side == "EAST"
                      else -rect.width - context.port_label_spacing_horizontal)
            cell.set_horizontal_alignment("LEFT" if side == "EAST" else "RIGHT")
        special = False


def constrained_inside_port_label_placement(context, side):
    if side in {"EAST", "WEST"}:
        simple_inside_port_label_placement(context, side)
        return
    cell = context.inside_port_label_cells[side]
    bounds = cell.cell_rectangle
    left = bounds.x + _maxd((cell.padding.left, context.surrounding_port_margins.left, context.node_label_spacing))
    right = bounds.x + bounds.width - _maxd((cell.padding.right, context.surrounding_port_margins.right, context.node_label_spacing))
    remover = RectangleStripOverlapRemover("DOWN" if side == "NORTH" else "UP")
    remover.gap = context.port_label_spacing_vertical
    start = -math.inf if side == "NORTH" else math.inf
    for stage in context.port_contexts.get(side, ()):
        cell = stage.port_label_cell
        if cell is None or not cell.labels: continue
        rect = _size_rectangle(cell)
        cell.set_vertical_alignment("TOP" if side == "NORTH" else "BOTTOM")
        cell.set_horizontal_alignment("RIGHT")
        rect.x = stage.port_position.x - (rect.width - stage.port.size.x) / 2
        actual_left = _minimum(left, stage.port_position.x)
        actual_right = _maximum(right, stage.port_position.x + stage.port.size.x)
        if rect.x < actual_left: rect.x = actual_left
        elif rect.x + rect.width > actual_right: rect.x = actual_right - rect.width
        remover.add(rect)
        start = (_maximum(start, stage.port_position.y + stage.port.size.y) if side == "NORTH"
                 else _minimum(start, stage.port_position.y))
    start += context.port_label_spacing_vertical if side == "NORTH" else -context.port_label_spacing_vertical
    remover.start_coordinate = start
    height = remover.remove_overlaps()
    if height > 0: context.inside_port_label_cells[side].minimum_content_area_size.y = height
    for stage in context.port_contexts.get(side, ()):
        cell = stage.port_label_cell
        if cell is None or not cell.labels: continue
        cell.cell_rectangle.x -= stage.port_position.x
        cell.cell_rectangle.y -= stage.port_position.y


def constrained_outside_port_label_placement(context, side):
    ports = context.port_contexts.get(side, ())
    if len(ports) <= 2 or side in {"EAST", "WEST"}:
        simple_outside_port_label_placement(context, side)
        return
    special = "SPACE_EFFICIENT" in context.port_labels_placement
    remover = RectangleStripOverlapRemover("UP" if side == "NORTH" else "DOWN")
    remover.gap = context.port_label_spacing_horizontal
    start = math.inf if side == "NORTH" else -math.inf
    for stage in ports:
        cell = stage.port_label_cell
        if cell is None or not cell.labels: continue
        rect = _size_rectangle(cell)
        if special:
            rect.x = stage.port_position.x - rect.width - context.port_label_spacing_horizontal
            special = False
        else: rect.x = stage.port_position.x + stage.port.size.x + context.port_label_spacing_horizontal
        cell.set_vertical_alignment("BOTTOM" if side == "NORTH" else "TOP")
        cell.set_horizontal_alignment("RIGHT")
        remover.add(rect)
        start = (_minimum(start, stage.port_position.y) if side == "NORTH"
                 else _maximum(start, stage.port_position.y + stage.port.size.y))
    start += -context.port_label_spacing_vertical if side == "NORTH" else context.port_label_spacing_vertical
    remover.start_coordinate = start
    remover.remove_overlaps()
    for stage in ports:
        cell = stage.port_label_cell
        if cell is None or not cell.labels: continue
        cell.cell_rectangle.x -= stage.port_position.x
        cell.cell_rectangle.y -= stage.port_position.y


def place_port_labels(context, side):
    constrained = "PORT_LABELS" not in context.size_constraints or context.port_constraints == "FIXED_POS"
    if "INSIDE" in context.port_labels_placement:
        (constrained_inside_port_label_placement if constrained else simple_inside_port_label_placement)(context, side)
    elif "OUTSIDE" in context.port_labels_placement:
        (constrained_outside_port_label_placement if constrained else simple_outside_port_label_placement)(context, side)
