# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; actual EndLabelPostprocessor35426-35484.
"""Actual endpoint-label cell writeback; preprocessor remains separate."""
from ...execution.diagnostics import BasicProgressMonitor


def end_label_postprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('End label post-processing', 1)
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type in ('NORMAL', 'EXTERNAL_PORT') and 'END_LABELS' in node.properties:
                cells = node.properties.get('END_LABELS')
                position = node.pos
                for _, cell in cells.items():
                    rectangle = cell.cell_rectangle
                    rectangle.x += position.x
                    rectangle.y += position.y
                    cell.apply_label_layout()
                node.properties['END_LABELS'] = None
    monitor.done()


# The preprocessor below adds the actual producer for the cells consumed above.
from ..disco import _IdentityMap
from .cell_layout import LabelCell, Rectangle, _maximum
from .label_side_selector import gather_labels
from .native_adapters import LLabelAdapter
from .port_label_placement import RectangleStripOverlapRemover, _minimum
from .property_access import read_layered_scalar


def create_configured_label_cell(labels, label_spacing, vertical):
    if labels is None or len(labels) == 0:
        return None
    cell = LabelCell(label_spacing, not vertical)
    for label in labels:
        cell.add_label(LLabelAdapter(label))
    rect, padding, minimum = cell.cell_rectangle, cell.padding, cell.minimum_content_area_size
    rect.height = (minimum.y + padding.top) + padding.bottom
    rect.width = (minimum.x + padding.left) + padding.right
    return cell


def _first_side(cell):
    # Actual LABEL_SIDE default UNKNOWN is the reviewed Internal Property, not
    # a metadata option. Its non-cloneable enum default does not materialize.
    value = cell.labels[0].element.properties.get('LABEL_SIDE')
    return 'UNKNOWN' if value is None else value


def _maximum_thickness(port):
    value = port.properties.get('MAX_EDGE_THICKNESS')
    return 0.0 if value is None else value


def place_end_label_cell(port, cell, edge_spacing):
    rect, node = cell.cell_rectangle, port.owner
    size, margin = node.size, node.margin
    # Source sum_0 starts from a fresh (+0,+0) vector, then adds pos/anchor.
    anchor_x = 0.0
    anchor_y = 0.0
    for vector in (port.pos, port.anchor):
        anchor_x += vector.x
        anchor_y += vector.y
    if port.side == 'NORTH':
        cell.set_vertical_alignment('BOTTOM')
        rect.y = (-margin.top - edge_spacing) - rect.height
        if _first_side(cell) == 'ABOVE':
            cell.set_horizontal_alignment('RIGHT')
            rect.x = ((anchor_x - _maximum_thickness(port)) - edge_spacing) - rect.width
        else:
            cell.set_horizontal_alignment('LEFT')
            rect.x = (anchor_x + _maximum_thickness(port)) + edge_spacing
    elif port.side == 'EAST':
        cell.set_horizontal_alignment('LEFT')
        rect.x = (size.x + margin.right) + edge_spacing
        if _first_side(cell) == 'ABOVE':
            cell.set_vertical_alignment('BOTTOM')
            rect.y = ((anchor_y - _maximum_thickness(port)) - edge_spacing) - rect.height
        else:
            cell.set_vertical_alignment('TOP')
            rect.y = (anchor_y + _maximum_thickness(port)) + edge_spacing
    elif port.side == 'SOUTH':
        cell.set_vertical_alignment('TOP')
        rect.y = (size.y + margin.bottom) + edge_spacing
        if _first_side(cell) == 'ABOVE':
            cell.set_horizontal_alignment('RIGHT')
            rect.x = ((anchor_x - _maximum_thickness(port)) - edge_spacing) - rect.width
        else:
            cell.set_horizontal_alignment('LEFT')
            rect.x = (anchor_x + _maximum_thickness(port)) + edge_spacing
    elif port.side == 'WEST':
        cell.set_horizontal_alignment('RIGHT')
        rect.x = (-margin.left - edge_spacing) - rect.width
        if _first_side(cell) == 'ABOVE':
            cell.set_vertical_alignment('BOTTOM')
            rect.y = ((anchor_y - _maximum_thickness(port)) - edge_spacing) - rect.height
        else:
            cell.set_vertical_alignment('TOP')
            rect.y = (anchor_y + _maximum_thickness(port)) + edge_spacing


def overlap_start_coordinate(node, side, edge_spacing):
    margin, size = node.margin, node.size
    if side == 'NORTH':
        return -margin.top - edge_spacing
    if side == 'SOUTH':
        return (size.y + margin.bottom) + edge_spacing
    if side == 'EAST':
        return (size.x + margin.right) + edge_spacing
    if side == 'WEST':
        return -margin.left - edge_spacing
    return 0.0


def remove_end_label_overlaps(node, cells, side, label_spacing, edge_spacing):
    direction = {'NORTH': 'UP', 'SOUTH': 'DOWN', 'EAST': 'RIGHT', 'WEST': 'LEFT'}.get(side)
    remover = RectangleStripOverlapRemover(direction)
    remover.gap = label_spacing
    remover.start_coordinate = overlap_start_coordinate(node, side, edge_spacing)
    for port in node.ports:
        if port.side == side and cells[port.id] is not None:
            remover.add(cells[port.id].cell_rectangle)
    remover.remove_overlaps()


def _union(rect, other):
    x1 = _minimum(rect.x, other.x)
    y1 = _minimum(rect.y, other.y)
    x2 = _maximum(rect.x + rect.width, other.x + other.width)
    y2 = _maximum(rect.y + rect.height, other.y + other.height)
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    rect.x, rect.y, rect.width, rect.height = x1, y1, x2 - x1, y2 - y1


def update_end_label_margins(node, cells):
    margin, size = node.margin, node.size
    rect = Rectangle(-margin.left, -margin.top,
                     (margin.left + size.x) + margin.right,
                     (margin.top + size.y) + margin.bottom)
    for cell in cells:
        if cell is not None:
            _union(rect, cell.cell_rectangle)
    margin.left = -rect.x
    margin.top = -rect.y
    margin.right = (rect.width - margin.left) - size.x
    margin.bottom = (rect.height - margin.top) - size.y


def process_end_label_node(node, edge_spacing, label_spacing, vertical):
    count = len(node.ports)
    cells = [None] * count
    for index in range(count):
        port = node.ports[index]
        port.id = index
        cells[index] = create_configured_label_cell(gather_labels(port), label_spacing, vertical)
    sides_with_labels = set()
    for port in node.ports:
        if cells[port.id] is not None:
            place_end_label_cell(port, cells[port.id], edge_spacing)
            sides_with_labels.add(port.side)
    # Both real remover calls occur even for empty sides/cells.
    for side in (('EAST', 'WEST') if vertical else ('NORTH', 'SOUTH')):
        remove_end_label_overlaps(node, cells, side, 2 * label_spacing, edge_spacing)
    port_to_cell = _IdentityMap(node.graph)
    for index, cell in enumerate(cells):
        if cell is not None:
            port_to_cell.put(node.ports[index], cell)
    if port_to_cell.items():
        node.properties['END_LABELS'] = port_to_cell
        update_end_label_margins(node, cells)


def end_label_preprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('End label pre-processing', 1)
    edge_spacing = read_layered_scalar(graph, 'SPACING_EDGE_LABEL', 'SPACING_EDGE_LABEL_0')
    label_spacing = read_layered_scalar(graph, 'SPACING_LABEL_LABEL', 'SPACING_LABEL_LABEL')
    vertical = read_layered_scalar(graph, 'DIRECTION', 'DIRECTION') in ('UP', 'DOWN')
    for layer in graph.layers:
        for node in layer.nodes:
            process_end_label_node(node, edge_spacing, label_spacing, vertical)
    monitor.done()
