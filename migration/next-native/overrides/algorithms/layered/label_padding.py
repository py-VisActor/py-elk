# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed worker275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# P17A in references/e13-kernel-sources.json; generic adapter supplied by caller.
"""Actual inside-node label padding without applying shape geometry."""
from .cell_layout import BEGIN, CENTER, END
from .graph import Insets
from .node_size import NodeContext
from .node_size_cells import create_node_label_cells
from .port_distribution import _maximum


def compute_inside_node_label_padding(node, layout_direction):
    context = NodeContext(node, transparent_north_south_edges=False)
    create_node_label_cells(context, layout_direction not in ('UP', 'DOWN'))
    container = context.inside_node_label_container
    padding = Insets()
    for column in (BEGIN, CENTER, END):
        cell = container.get_cell(BEGIN, column)
        if cell is not None:
            padding.top = _maximum(padding.top, cell.get_minimum_height())
    for column in (BEGIN, CENTER, END):
        cell = container.get_cell(END, column)
        if cell is not None:
            padding.bottom = _maximum(padding.bottom, cell.get_minimum_height())
    for row in (BEGIN, CENTER, END):
        cell = container.get_cell(row, BEGIN)
        if cell is not None:
            padding.left = _maximum(padding.left, cell.get_minimum_width())
    for row in (BEGIN, CENTER, END):
        cell = container.get_cell(row, END)
        if cell is not None:
            padding.right = _maximum(padding.right, cell.get_minimum_width())
    if padding.top > 0:
        padding.top += container.padding.top
        padding.top += container.gap
    if padding.bottom > 0:
        padding.bottom += container.padding.bottom
        padding.bottom += container.gap
    if padding.left > 0:
        padding.left += container.padding.left
        padding.left += container.gap
    if padding.right > 0:
        padding.right += container.padding.right
        padding.right += container.gap
    return padding
