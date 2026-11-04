# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Copyright (c) Kiel University and others.
# Copyright (C) 2011 The Guava Authors (the scoped fuzzy-equality operation).
# Adapted from fixed elkjs 0.12.1 lib/elk-worker.js, E13-P04C.
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# See NOTICE-Guava-DoubleMath.md for the Apache helper's scope and changes.
"""Real port-size minima and cell contributions over prepared source cells.

The caller supplies the real NodeContext, label cells and adapted port groups.
This module does not invent label measurements or run the full node-size chain.
"""
from __future__ import annotations

import math

from .cell_layout import Rectangle, _maximum
from .graph import Vec2
from .node_size import get_port_alignment
from .ports import _divide


_INSIDE_LOCATIONS = frozenset(("IN_T_L", "IN_T_C", "IN_T_R", "IN_C_L", "IN_C_C",
                               "IN_C_R", "IN_B_L", "IN_B_C", "IN_B_R"))
_LOCATIONS = ("OUT_T_L", "OUT_T_C", "OUT_T_R", "OUT_B_L", "OUT_B_C", "OUT_B_R",
              "OUT_L_T", "OUT_L_C", "OUT_L_B", "OUT_R_T", "OUT_R_C", "OUT_R_B",
              "IN_T_L", "IN_T_C", "IN_T_R", "IN_C_L", "IN_C_C", "IN_C_R",
              "IN_B_L", "IN_B_C", "IN_B_R", "UNDEFINED")


def _fuzzy_equals(first, second):
    # Scoped Guava DoubleMath.fuzzyEquals, inlined at the actual ratio callers.
    # The source's fixed .01 tolerance satisfies its nonnegative precondition.
    return (abs(first - second) <= 0.01 or first == second
            or math.isnan(first) and math.isnan(second))


def min_size_required_to_respect_spacing(spacing, second_ratio):
    return 0 if _fuzzy_equals(0, second_ratio) else _divide(spacing, second_ratio)


def get_labels_bounds(port):
    bounds = None
    for label in getattr(port, "labels", ()):
        current = Rectangle(label.pos.x, label.pos.y, label.size.x, label.size.y)
        if bounds is None:
            bounds = current
        else:
            # The source ElkRectangle.union also normalizes reversed extents.
            x1 = -_maximum(-bounds.x, -current.x)
            y1 = -_maximum(-bounds.y, -current.y)
            x2 = _maximum(bounds.x + bounds.width, current.x + current.width)
            y2 = _maximum(bounds.y + bounds.height, current.y + current.height)
            if x2 < x1: x1, x2 = x2, x1
            if y2 < y1: y1, y2 = y2, y1
            bounds = Rectangle(x1, y1, x2 - x1, y2 - y1)
    return bounds if bounds is not None else Rectangle()


def compute_horizontal_port_margins(context, side):
    for stage in context.port_contexts.get(side, ()):
        width = stage.port_label_cell.get_minimum_width() if stage.port_label_cell else 0
        if width > 0:
            if stage.labels_next_to_port:
                port_width = stage.port.size.x
                if width > port_width:
                    overhang = (width - port_width) / 2
                    stage.port_margin.left = overhang
                    stage.port_margin.right = overhang
            else:
                stage.port_margin.right = context.port_label_spacing_horizontal + width
        elif not context.port_labels_placement.intersection({"INSIDE", "OUTSIDE"}):
            bounds = get_labels_bounds(stage.port)
            if bounds.x < 0: stage.port_margin.left = -bounds.x
            if bounds.x + bounds.width > stage.port.size.x:
                stage.port_margin.right = bounds.x + bounds.width - stage.port.size.x


def compute_vertical_port_margins(context, side):
    for stage in context.port_contexts.get(side, ()):
        cell = stage.port_label_cell
        height = cell.get_minimum_height() if cell else 0
        if height > 0:
            if stage.labels_next_to_port:
                port_height = stage.port.size.y
                if height > port_height:
                    if context.port_labels_treat_as_group or len(cell.labels) == 1:
                        overhang = (height - port_height) / 2
                        stage.port_margin.top = overhang
                        stage.port_margin.bottom = overhang
                    else:
                        first_height = cell.labels[0].size.y
                        first_overhang = (first_height - port_height) / 2
                        stage.port_margin.top = _maximum(0, first_overhang)
                        stage.port_margin.bottom = height - first_overhang - port_height
            else:
                stage.port_margin.bottom = context.port_label_spacing_vertical + height
        elif not context.port_labels_placement.intersection({"INSIDE", "OUTSIDE"}):
            bounds = get_labels_bounds(stage.port)
            if bounds.y < 0: stage.port_margin.top = -bounds.y
            if bounds.y + bounds.height > stage.port.size.y:
                stage.port_margin.bottom = bounds.y + bounds.height - stage.port.size.y


def _setup_margins(context, side, *, vertical):
    ports = context.port_contexts.get(side, ())
    placement = context.port_labels_placement
    outside = "OUTSIDE" in placement
    efficient = ("ALWAYS_SAME_SIDE" not in placement and "ALWAYS_OTHER_SAME_SIDE" not in placement
                 and ("SPACE_EFFICIENT" in placement or len(ports) == 2))
    uniform = "UNIFORM_PORT_SPACING" in context.size_options
    if vertical: compute_vertical_port_margins(context, side)
    else: compute_horizontal_port_margins(context, side)
    leading, trailing = ("top", "bottom") if vertical else ("left", "right")
    if outside:
        first, last = ports[0], ports[-1]
        setattr(first.port_margin, leading, 0)
        setattr(last.port_margin, trailing, 0)
        if efficient and not first.labels_next_to_port: setattr(first.port_margin, trailing, 0)
    if uniform:
        maximum_leading, maximum_trailing = 0, 0
        for stage in ports:
            maximum_leading = _maximum(maximum_leading, getattr(stage.port_margin, leading))
            maximum_trailing = _maximum(maximum_trailing, getattr(stage.port_margin, trailing))
        for stage in ports:
            setattr(stage.port_margin, leading, maximum_leading)
            setattr(stage.port_margin, trailing, maximum_trailing)
        if outside:
            setattr(first.port_margin, leading, 0)
            setattr(last.port_margin, trailing, 0)


def setup_horizontal_port_margins(context, side):
    _setup_margins(context, side, vertical=False)


def setup_vertical_port_margins(context, side):
    _setup_margins(context, side, vertical=True)


def _port_size_plus_spacing(context, side, *, vertical):
    ports = context.port_contexts.get(side, ())
    result = 0
    for index, stage in enumerate(ports):
        margin = stage.port_margin
        result += (margin.top + stage.port.size.y + margin.bottom if vertical
                   else margin.left + stage.port.size.x + margin.right)
        if index + 1 < len(ports): result += context.port_port_spacing
    return result


def port_width_plus_port_port_spacing(context, side):
    return _port_size_plus_spacing(context, side, vertical=False)


def port_height_plus_port_port_spacing(context, side):
    return _port_size_plus_spacing(context, side, vertical=True)


def _calculate_port_placement_size(context, side, *, vertical):
    cell = context.inside_port_label_cells[side]
    ports = context.port_contexts.get(side, ())
    axis, leading, trailing = ("y", "top", "bottom") if vertical else ("x", "left", "right")
    if context.port_constraints == "FIXED_POS":
        border = 0
        for stage in ports:
            border = _maximum(border, getattr(stage.port_position, axis) + getattr(stage.port.size, axis))
        setattr(cell.padding, leading, 0)
        setattr(cell.minimum_content_area_size, axis, border)
        return
    if not ports:
        setattr(cell.padding, leading, 0)
        setattr(cell.padding, trailing, 0)
        return
    if context.port_constraints == "FIXED_RATIO":
        minimum = 0
        has_labels = "PORT_LABELS" in context.size_constraints
        if vertical and has_labels: setup_vertical_port_margins(context, side)
        previous = None
        previous_ratio = previous_size = 0
        for stage in ports:
            ratio = stage.port.properties.get("PORT_RATIO_OR_POSITION", 0)
            size = getattr(stage.port.size, axis)
            # Source horizontal repeats this stage within the loop; vertical
            # performs it once before iteration. Keep the observable ordering.
            if not vertical and has_labels: setup_horizontal_port_margins(context, side)
            surrounding = context.surrounding_port_margins
            if previous is None:
                if surrounding is not None and getattr(surrounding, leading) > 0:
                    spacing = getattr(surrounding, leading) + getattr(stage.port_margin, leading)
                    minimum = _maximum(minimum, min_size_required_to_respect_spacing(spacing, ratio))
            else:
                required = (previous_size + getattr(previous.port_margin, trailing)
                            + context.port_port_spacing + getattr(stage.port_margin, leading))
                minimum = _maximum(minimum, 0 if _fuzzy_equals(previous_ratio, ratio)
                                   else _divide(required, ratio - previous_ratio))
            previous, previous_ratio, previous_size = stage, ratio, size
        surrounding = context.surrounding_port_margins
        if surrounding is not None and getattr(surrounding, trailing) > 0:
            required = previous_size + getattr(surrounding, trailing)
            if "INSIDE" in context.port_labels_placement: required += getattr(previous.port_margin, trailing)
            minimum = _maximum(minimum, 0 if _fuzzy_equals(previous_ratio, 1)
                               else _divide(required, 1 - previous_ratio))
        setattr(cell.padding, leading, 0)
        setattr(cell.minimum_content_area_size, axis, minimum)
        return
    setattr(cell.padding, leading, getattr(context.surrounding_port_margins, leading))
    setattr(cell.padding, trailing, getattr(context.surrounding_port_margins, trailing))
    if "PORT_LABELS" in context.size_constraints: _setup_margins(context, side, vertical=vertical)
    minimum = _port_size_plus_spacing(context, side, vertical=vertical)
    if get_port_alignment(context, side) == "DISTRIBUTED": minimum += 2 * context.port_port_spacing
    setattr(cell.minimum_content_area_size, axis, minimum)


def calculate_horizontal_port_placement_size(context):
    for side in ("NORTH", "SOUTH"): _calculate_port_placement_size(context, side, vertical=False)


def calculate_vertical_port_placement_size(context):
    for side in ("EAST", "WEST"): _calculate_port_placement_size(context, side, vertical=True)


def configure_cell_system_size_contributions(context):
    constraints = context.size_constraints
    if not constraints: return
    cells = context.inside_port_label_cells
    middle = context.node_container_middle_row
    if "PORTS" in constraints:
        cells["NORTH"].contributes_to_minimum_width = True
        cells["SOUTH"].contributes_to_minimum_width = True
        free = context.port_constraints not in {"FIXED_RATIO", "FIXED_POS"}
        cells["EAST"].contributes_to_minimum_height = free
        cells["WEST"].contributes_to_minimum_height = free
        middle.contributes_to_minimum_height = free
        if "PORT_LABELS" in constraints:
            cells["NORTH"].contributes_to_minimum_height = True
            cells["SOUTH"].contributes_to_minimum_height = True
            cells["EAST"].contributes_to_minimum_width = True
            cells["WEST"].contributes_to_minimum_width = True
            middle.contributes_to_minimum_width = True
    inside = context.inside_node_label_container
    if "NODE_LABELS" in constraints:
        inside.contributes_to_minimum_height = inside.contributes_to_minimum_width = True
        middle.contributes_to_minimum_height = middle.contributes_to_minimum_width = True
        overhang = "OUTSIDE_NODE_LABELS_OVERHANG" in context.size_options
        for location in _LOCATIONS:
            cell = context.node_label_cells.get(location)
            if cell is not None:
                contributes = location in _INSIDE_LOCATIONS or not overhang
                cell.contributes_to_minimum_height = contributes
                cell.contributes_to_minimum_width = contributes
    if "MINIMUM_SIZE" in constraints and "MINIMUM_SIZE_ACCOUNTS_FOR_PADDING" in context.size_options:
        middle.contributes_to_minimum_height = True
        middle.contributes_to_minimum_height = True  # Duplicate is literal source.
        if not inside.contributes_to_minimum_height:
            inside.contributes_to_minimum_height = inside.contributes_to_minimum_width = True
            inside.only_center_cell_contributes_to_minimum_size = True


def update_vertical_inside_port_label_cell_padding(context):
    if context.port_constraints in {"FIXED_RATIO", "FIXED_POS"}: return
    cells = context.inside_port_label_cells
    top_border = (context.node_container.padding.top + cells["NORTH"].get_minimum_height()
                  + context.label_cell_spacing)
    bottom_border = (context.node_container.padding.bottom + cells["SOUTH"].get_minimum_height()
                     + context.label_cell_spacing)
    east, west = cells["EAST"], cells["WEST"]
    top = _maximum(0, east.padding.top - top_border)
    top = _maximum(top, west.padding.top - top_border)
    bottom = _maximum(0, east.padding.bottom - bottom_border)
    bottom = _maximum(bottom, west.padding.bottom - bottom_border)
    east.padding.top = west.padding.top = top
    east.padding.bottom = west.padding.bottom = bottom


def get_minimum_node_or_client_area_size(context):
    supplied = context.node.properties.get("NODE_SIZE_MINIMUM", Vec2())
    minimum = Vec2(supplied.x, supplied.y)
    if "DEFAULT_MINIMUM_SIZE" in context.size_options:
        if minimum.x <= 0: minimum.x = 20
        if minimum.y <= 0: minimum.y = 20
    return minimum


def get_minimum_node_size(context):
    if "MINIMUM_SIZE" in context.size_constraints and "MINIMUM_SIZE_ACCOUNTS_FOR_PADDING" not in context.size_options:
        return get_minimum_node_or_client_area_size(context)
    return None


def set_node_width(context):
    size = context.node_size
    if not context.size_constraints or context.size_constraints == {"PORT_LABELS"}:
        width = size.x
    else:
        width = context.node_container.get_minimum_width()
        if context.topdown_layout: width = _maximum(size.x, width)
        if "NODE_LABELS" in context.size_constraints and "OUTSIDE_NODE_LABELS_OVERHANG" not in context.size_options:
            width = _maximum(width, context.outside_node_label_containers["NORTH"].get_minimum_width())
            width = _maximum(width, context.outside_node_label_containers["SOUTH"].get_minimum_width())
        minimum = get_minimum_node_size(context)
        if minimum is not None: width = _maximum(width, minimum.x)
    fixed = context.node.graph.properties.get("NODE_SIZE_FIXED_GRAPH_SIZE", False)
    size.x = _maximum(size.x, width) if fixed else width
    rectangle = context.node_container.cell_rectangle
    rectangle.x, rectangle.width = 0, width
    context.node_container.layout_children_horizontally()


def set_node_height(context):
    size = context.node_size
    if not context.size_constraints or context.size_constraints == {"PORT_LABELS"}:
        height = size.y
    else:
        height = context.node_container.get_minimum_height()
        if context.topdown_layout: height = _maximum(size.y, height)
        if "NODE_LABELS" in context.size_constraints and "OUTSIDE_NODE_LABELS_OVERHANG" not in context.size_options:
            height = _maximum(height, context.outside_node_label_containers["EAST"].get_minimum_height())
            height = _maximum(height, context.outside_node_label_containers["WEST"].get_minimum_height())
        minimum = get_minimum_node_size(context)
        if minimum is not None: height = _maximum(height, minimum.y)
        if "PORTS" in context.size_constraints and context.port_constraints in {"FIXED_RATIO", "FIXED_POS"}:
            height = _maximum(height, context.inside_port_label_cells["EAST"].get_minimum_height())
            height = _maximum(height, context.inside_port_label_cells["WEST"].get_minimum_height())
    fixed = context.node.graph.properties.get("NODE_SIZE_FIXED_GRAPH_SIZE", False)
    size.y = _maximum(size.y, height) if fixed else height
    rectangle = context.node_container.cell_rectangle
    rectangle.y, rectangle.height = 0, height
    context.node_container.layout_children_vertically()
