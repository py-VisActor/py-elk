# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Adapted from fixed elkjs 0.12.1 lib/elk-worker.js, E13-P04D.
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Source cell creators and padding; supplied labels retain their real sizes."""
from __future__ import annotations

from dataclasses import dataclass

from .cell_layout import (AtomicCell, GridContainerCell, LabelCell, StripContainerCell,
                          BEGIN, CENTER, END, HORIZONTAL, VERTICAL, _maximum)
from .graph import Insets, Vec2
from .node_size_math import get_labels_bounds


@dataclass(frozen=True)
class NodeLabelLocation:
    name: str
    horizontal_alignment: str | None
    vertical_alignment: str | None
    container_row: int | None
    container_column: int | None
    assigned_placements: tuple[frozenset[str], ...]

    def is_inside(self):
        return self.name.startswith("IN_")

    def outside_side(self):
        if self.name.startswith("OUT_T_"): return "NORTH"
        if self.name.startswith("OUT_B_"): return "SOUTH"
        if self.name.startswith("OUT_L_"): return "WEST"
        if self.name.startswith("OUT_R_"): return "EAST"
        return "UNDEFINED"


def _location(name, horizontal, vertical, row, column, placements):
    return NodeLabelLocation(name, horizontal, vertical, row, column,
                             tuple(frozenset(p) for p in placements))


# The order and assigned sets are the actual source enumerator, not a heuristic
# based on missing components or a default visual location.
NODE_LABEL_LOCATIONS = (
    _location("OUT_T_L", "LEFT", "BOTTOM", BEGIN, BEGIN, [("OUTSIDE", "V_TOP", "H_LEFT")]),
    _location("OUT_T_C", "CENTER", "BOTTOM", BEGIN, CENTER, [("OUTSIDE", "V_TOP", "H_CENTER"), ("OUTSIDE", "V_TOP", "H_CENTER", "H_PRIORITY")]),
    _location("OUT_T_R", "RIGHT", "BOTTOM", BEGIN, END, [("OUTSIDE", "V_TOP", "H_RIGHT")]),
    _location("OUT_B_L", "LEFT", "TOP", END, BEGIN, [("OUTSIDE", "V_BOTTOM", "H_LEFT")]),
    _location("OUT_B_C", "CENTER", "TOP", END, CENTER, [("OUTSIDE", "V_BOTTOM", "H_CENTER"), ("OUTSIDE", "V_BOTTOM", "H_CENTER", "H_PRIORITY")]),
    _location("OUT_B_R", "RIGHT", "TOP", END, END, [("OUTSIDE", "V_BOTTOM", "H_RIGHT")]),
    _location("OUT_L_T", "RIGHT", "TOP", BEGIN, BEGIN, [("OUTSIDE", "H_LEFT", "V_TOP", "H_PRIORITY")]),
    _location("OUT_L_C", "RIGHT", "CENTER", CENTER, BEGIN, [("OUTSIDE", "H_LEFT", "V_CENTER"), ("OUTSIDE", "H_LEFT", "V_CENTER", "H_PRIORITY")]),
    _location("OUT_L_B", "RIGHT", "BOTTOM", END, BEGIN, [("OUTSIDE", "H_LEFT", "V_BOTTOM", "H_PRIORITY")]),
    _location("OUT_R_T", "LEFT", "TOP", BEGIN, END, [("OUTSIDE", "H_RIGHT", "V_TOP", "H_PRIORITY")]),
    _location("OUT_R_C", "LEFT", "CENTER", CENTER, END, [("OUTSIDE", "H_RIGHT", "V_CENTER"), ("OUTSIDE", "H_RIGHT", "V_CENTER", "H_PRIORITY")]),
    _location("OUT_R_B", "LEFT", "BOTTOM", END, END, [("OUTSIDE", "H_RIGHT", "V_BOTTOM", "H_PRIORITY")]),
    *(_location("IN_" + row_name + "_" + column_name, horizontal, vertical, row, column,
                [("INSIDE", vertical_flag, horizontal_flag),
                 ("INSIDE", vertical_flag, horizontal_flag, "H_PRIORITY")])
      for row_name, vertical, row, vertical_flag in
          (("T", "TOP", BEGIN, "V_TOP"), ("C", "CENTER", CENTER, "V_CENTER"), ("B", "BOTTOM", END, "V_BOTTOM"))
      for column_name, horizontal, column, horizontal_flag in
          (("L", "LEFT", BEGIN, "H_LEFT"), ("C", "CENTER", CENTER, "H_CENTER"), ("R", "RIGHT", END, "H_RIGHT"))),
    _location("UNDEFINED", None, None, None, None, ()),
)


def from_node_label_placement(placement):
    selected = frozenset(placement)
    for location in NODE_LABEL_LOCATIONS:
        if selected in location.assigned_placements: return location
    return NODE_LABEL_LOCATIONS[-1]


def create_node_label_cell_containers(context, only_inside=False):
    symmetry = "ASYMMETRICAL" not in context.size_options
    tabular = "FORCE_TABULAR_NODE_LABELS" in context.size_options
    context.inside_node_label_container = GridContainerCell(tabular, symmetry, context.label_cell_spacing)
    if context.node_labels_padding is not None:
        p = context.node_labels_padding
        context.inside_node_label_container.padding = Insets(p.top, p.right, p.bottom, p.left)
    context.node_container_middle_row.set_cell(CENTER, context.inside_node_label_container)
    if not only_inside:
        for side, mode, padding_side in (("NORTH", HORIZONTAL, "bottom"), ("SOUTH", HORIZONTAL, "top"),
                                         ("WEST", VERTICAL, "right"), ("EAST", VERTICAL, "left")):
            container = StripContainerCell(mode, symmetry, context.label_cell_spacing)
            setattr(container.padding, padding_side, context.node_label_spacing)
            context.outside_node_label_containers[side] = container


def retrieve_node_label_cell(context, location, horizontal_layout_mode):
    cell = context.node_label_cells.get(location.name)
    if cell is None:
        cell = LabelCell(context.label_label_spacing, location, horizontal_layout_mode)
        context.node_label_cells[location.name] = cell
        if location.is_inside():
            context.inside_node_label_container.set_cell(location.container_row, location.container_column, cell)
        else:
            side = location.outside_side()
            container = context.outside_node_label_containers[side]
            if side in {"NORTH", "SOUTH"}:
                cell.contributes_to_minimum_height = True
                container.set_cell(location.container_column, cell)
            elif side in {"WEST", "EAST"}:
                cell.contributes_to_minimum_width = True
                container.set_cell(location.container_row, cell)
    return cell


def handle_node_label(context, label, only_inside, horizontal_layout_mode):
    properties = getattr(label, "properties", {})
    placement = (properties["NODE_LABELS_PLACEMENT"] if "NODE_LABELS_PLACEMENT" in properties
                 else context.node_label_placement)
    location = from_node_label_placement(placement)
    if location.name == "UNDEFINED" or only_inside and not location.is_inside(): return
    retrieve_node_label_cell(context, location, horizontal_layout_mode).add_label(label)


def create_node_label_cells(context, horizontal_layout_mode):
    create_node_label_cell_containers(context, True)
    for label in getattr(context.node, "labels", ()):
        handle_node_label(context, label, True, horizontal_layout_mode)


def create_inside_port_label_cell(context, container, area, side):
    cell = AtomicCell()
    container.set_cell(area, cell)
    context.inside_port_label_cells[side] = cell


def calculate_width_due_to_labels(context, side):
    cell = context.inside_port_label_cells[side]
    minimum = cell.minimum_content_area_size
    for stage in context.port_contexts.get(side, ()):
        if stage.port_label_cell is not None:
            minimum.x = _maximum(minimum.x, stage.port_label_cell.get_minimum_width())
    if minimum.x > 0:
        if side == "EAST": cell.padding.right = context.port_label_spacing_horizontal
        elif side == "WEST": cell.padding.left = context.port_label_spacing_horizontal


def setup_top_and_bottom_padding(context, side):
    margins = context.surrounding_port_margins
    if margins is not None:
        padding = context.inside_port_label_cells[side].padding
        padding.top, padding.bottom = margins.top, margins.bottom


def setup_east_or_west_port_label_cell(context, side):
    if "INSIDE" in context.port_labels_placement: calculate_width_due_to_labels(context, side)
    setup_top_and_bottom_padding(context, side)


def setup_north_or_south_port_label_cell(context, side):
    padding = context.inside_port_label_cells[side].padding
    if side == "NORTH" and context.port_label_spacing_vertical >= 0:
        padding.top = context.port_label_spacing_vertical
    elif side == "SOUTH" and context.port_label_spacing_vertical >= 0:
        padding.bottom = context.port_label_spacing_vertical
    if context.surrounding_port_margins is not None:
        padding.left = context.surrounding_port_margins.left
        padding.right = context.surrounding_port_margins.right


def compute_inside_part(label_position, label_size, port_size, offset, side):
    if side == "NORTH": return _maximum(0, label_size.y + label_position.y - (port_size.y + offset))
    if side == "SOUTH": return _maximum(0, -label_position.y - offset)
    if side == "EAST": return _maximum(0, -label_position.x - offset)
    if side == "WEST": return _maximum(0, label_size.x + label_position.x - (port_size.x + offset))
    return 0


def setup_node_padding_for_ports_with_offset(context):
    padding = context.node_container.padding
    for side in ("NORTH", "EAST", "SOUTH", "WEST"):
        for stage in context.port_contexts.get(side, ()):
            port = stage.port
            offset = 0
            if "PORT_BORDER_OFFSET" in port.properties:
                offset = port.properties["PORT_BORDER_OFFSET"]
                if offset < 0:
                    direction = {"NORTH": "top", "SOUTH": "bottom", "EAST": "right", "WEST": "left"}.get(port.side)
                    if direction is not None: setattr(padding, direction, _maximum(getattr(padding, direction), -offset))
            if not context.port_labels_placement.intersection({"INSIDE", "OUTSIDE"}):
                bounds = get_labels_bounds(port)
                inside = compute_inside_part(Vec2(bounds.x, bounds.y), Vec2(bounds.width, bounds.height), port.size, offset, port.side)
                symmetrical = "ASYMMETRICAL" not in context.node.properties.get("NODE_SIZE_OPTIONS", {"DEFAULT_MINIMUM_SIZE"})
                direction = {"NORTH": "top", "SOUTH": "bottom", "EAST": "right", "WEST": "left"}.get(port.side)
                opposite = {"top": "bottom", "bottom": "top", "right": "left", "left": "right"}.get(direction)
                if direction is not None:
                    larger = inside > getattr(padding, direction)
                    setattr(padding, direction, _maximum(getattr(padding, direction), inside))
                    if symmetrical and larger:
                        setattr(padding, direction, _maximum(getattr(padding, direction), getattr(padding, opposite)))
                        setattr(padding, opposite, getattr(padding, direction) + offset)


def set_node_padding(context):
    if "COMPUTE_PADDING" not in context.size_options: return
    node_rect = context.node_container.cell_rectangle
    client = context.inside_node_label_container.center_cell_rect
    padding = context.node.padding
    padding.left, padding.top = client.x - node_rect.x, client.y - node_rect.y
    padding.right = node_rect.x + node_rect.width - (client.x + client.width)
    padding.bottom = node_rect.y + node_rect.height - (client.y + client.height)


def place_horizontal_outer_node_label_container(context, overhang, side):
    container = context.outside_node_label_containers[side]
    rectangle = container.cell_rectangle
    rectangle.width, rectangle.height = container.get_minimum_width(), container.get_minimum_height()
    rectangle.width = _maximum(rectangle.width, context.node_size.x)
    if rectangle.width > context.node_size.x and not overhang: rectangle.width = context.node_size.x
    rectangle.x = -(rectangle.width - context.node_size.x) / 2
    if side == "NORTH": rectangle.y = -rectangle.height
    elif side == "SOUTH": rectangle.y = context.node_size.y
    container.layout_children_horizontally()
    container.layout_children_vertically()


def place_vertical_outer_node_label_container(context, overhang, side):
    container = context.outside_node_label_containers[side]
    rectangle = container.cell_rectangle
    rectangle.width, rectangle.height = container.get_minimum_width(), container.get_minimum_height()
    rectangle.height = _maximum(rectangle.height, context.node_size.y)
    if rectangle.height > context.node_size.y and not overhang: rectangle.height = context.node_size.y
    rectangle.y = -(rectangle.height - context.node_size.y) / 2
    if side == "WEST": rectangle.x = -rectangle.width
    elif side == "EAST": rectangle.x = context.node_size.x
    container.layout_children_horizontally()
    container.layout_children_vertically()
