# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Adapted from elkjs 0.12.1 lib/elk-worker.js process21733..21783 (E13-P04F).
"""Standalone real node-size process; whole layered caller remains separate."""
from .cell_layout import BEGIN, END
from .node_size import (NodeContext, create_port_contexts, place_horizontal_ports,
                        offset_southern_ports_by_node_size, place_vertical_ports, apply_port_positions)
from . import node_size_math as math_stage
from . import node_size_cells as cells_stage
from .port_label_placement import place_port_labels


def process_node_size(graph, node, apply_stuff=True, ignore_inside_port_labels=False, *,
                      adapted_port_edges=None, transparent_north_south_edges=True):
    context = NodeContext(node, adapted_port_edges=adapted_port_edges,
                          transparent_north_south_edges=transparent_north_south_edges)
    create_port_contexts(context, ignore_inside_port_labels)
    horizontal_layout_mode = True
    if graph is not None and "DIRECTION" in graph.properties:
        horizontal_layout_mode = graph.properties["DIRECTION"] in {"UNDEFINED", "LEFT", "RIGHT"}
    cells_stage.create_node_label_cell_containers(context, False)
    for label in getattr(node, "labels", ()):
        cells_stage.handle_node_label(context, label, False, horizontal_layout_mode)
    for container, area, side in ((context.node_container, BEGIN, "NORTH"),
                                  (context.node_container, END, "SOUTH"),
                                  (context.node_container_middle_row, BEGIN, "WEST"),
                                  (context.node_container_middle_row, END, "EAST")):
        cells_stage.create_inside_port_label_cell(context, container, area, side)
    for side in ("NORTH", "SOUTH"): cells_stage.setup_north_or_south_port_label_cell(context, side)
    for side in ("EAST", "WEST"): cells_stage.setup_east_or_west_port_label_cell(context, side)
    if "MINIMUM_SIZE" in context.size_constraints and "MINIMUM_SIZE_ACCOUNTS_FOR_PADDING" in context.size_options:
        context.inside_node_label_container.set_center_cell_minimum_size(
            math_stage.get_minimum_node_or_client_area_size(context))
    cells_stage.setup_node_padding_for_ports_with_offset(context)
    math_stage.calculate_horizontal_port_placement_size(context)
    math_stage.calculate_vertical_port_placement_size(context)
    math_stage.configure_cell_system_size_contributions(context)
    math_stage.set_node_width(context)
    place_horizontal_ports(context)
    for side in ("NORTH", "SOUTH"): place_port_labels(context, side)
    math_stage.update_vertical_inside_port_label_cell_padding(context)
    math_stage.set_node_height(context)
    if not apply_stuff: return context.node_size
    offset_southern_ports_by_node_size(context)
    place_vertical_ports(context)
    for side in ("EAST", "WEST"): place_port_labels(context, side)
    overhang = "OUTSIDE_NODE_LABELS_OVERHANG" in context.size_options
    for side in ("NORTH", "SOUTH"):
        cells_stage.place_horizontal_outer_node_label_container(context, overhang, side)
    for side in ("EAST", "WEST"):
        cells_stage.place_vertical_outer_node_label_container(context, overhang, side)
    for location in cells_stage.NODE_LABEL_LOCATIONS:
        cell = context.node_label_cells.get(location.name)
        if cell is not None: cell.apply_label_layout()
    for side in ("NORTH", "EAST", "SOUTH", "WEST"):
        for stage in context.port_contexts.get(side, ()):
            if stage.port_label_cell is not None: stage.port_label_cell.apply_label_layout()
    cells_stage.set_node_padding(context)
    node.size.x, node.size.y = context.node_size.x, context.node_size.y
    apply_port_positions(context)
    return context.node_size
