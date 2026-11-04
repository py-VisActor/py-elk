# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Mechanical ELK cells port: elkjs0.12.1 lib/elk-worker.js C01-C07 in
# references/e13-cell-sources.json. Worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Exact external Java build identity remains unresolved.
"""Native node-spacing cells; no text estimation or layout backend.

The three container areas are source BEGIN/CENTER/END, not an input-size cap.
Node/port context preparation and placement adapters are owned by callers.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

from .graph import Insets, Vec2

BEGIN, CENTER, END = 0, 1, 2
VERTICAL, HORIZONTAL = 0, 1


def _maximum(*values):
    if any(math.isnan(x) for x in values): return math.nan
    value = max(values)
    if value == 0:
        return 0.0 if any(x == 0 and math.copysign(1.0, x) > 0 for x in values) else -0.0
    return value


@dataclass
class Rectangle:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


class Cell:
    def __init__(self):
        self.padding = Insets()
        self.cell_rectangle = Rectangle()
        self.contributes_to_minimum_width = False
        self.contributes_to_minimum_height = False

    def get_minimum_width(self):
        raise NotImplementedError('Abstract cell minimum width')

    def get_minimum_height(self):
        raise NotImplementedError('Abstract cell minimum height')

    def apply_horizontal_layout(self, x, width):
        self.cell_rectangle.x = x; self.cell_rectangle.width = width

    def apply_vertical_layout(self, y, height):
        self.cell_rectangle.y = y; self.cell_rectangle.height = height


class AtomicCell(Cell):
    def __init__(self):
        super().__init__()
        self.minimum_content_area_size = Vec2()

    def get_minimum_width(self):
        return self.minimum_content_area_size.x+self.padding.left+self.padding.right

    def get_minimum_height(self):
        return self.minimum_content_area_size.y+self.padding.top+self.padding.bottom


def apply_horizontal_layout(cell, x, width):
    if cell is not None: cell.apply_horizontal_layout(x, width)


def apply_vertical_layout(cell, y, height):
    if cell is not None: cell.apply_vertical_layout(y, height)


def min_width_of_cell(cell, respect_contribution_flag):
    if cell is None or respect_contribution_flag and not cell.contributes_to_minimum_width:
        return 0
    if isinstance(cell, AtomicCell) and cell.minimum_content_area_size.x == 0:
        return 0
    return cell.get_minimum_width()


def min_height_of_cell(cell, respect_contribution_flag):
    if cell is None or respect_contribution_flag and not cell.contributes_to_minimum_height:
        return 0
    if isinstance(cell, AtomicCell) and cell.minimum_content_area_size.y == 0:
        return 0
    return cell.get_minimum_height()


class ContainerCell(Cell):
    def layout_children_horizontally(self):
        raise NotImplementedError('Abstract horizontal child layout')

    def layout_children_vertically(self):
        raise NotImplementedError('Abstract vertical child layout')


def _sum_with_gaps(values, gap):
    result, active = 0.0, 0
    for value in values:
        if value > 0:
            result += value; active += 1
    if active > 1: result += gap*(active-1)
    return result


class StripContainerCell(ContainerCell):
    def __init__(self, mode, symmetrical=False, gap=0.0):
        super().__init__()
        self.cells = [None, None, None]
        self.container_mode = mode; self.symmetrical = symmetrical; self.gap = gap

    def set_cell(self, area, cell):
        self.cells[area] = cell

    def get_cell(self, area):
        return self.cells[area]

    def _minimums(self, horizontal, respect):
        fn = min_width_of_cell if horizontal else min_height_of_cell
        values = [fn(cell, respect) for cell in self.cells]
        if self.symmetrical:
            values[0] = _maximum(values[0], values[2]); values[2] = values[0]
        return values

    def _cross_maximum(self, horizontal):
        values = [(cell.get_minimum_width() if horizontal else cell.get_minimum_height())
                  for cell in self.cells if cell is not None and
                  (cell.contributes_to_minimum_width if horizontal else cell.contributes_to_minimum_height)]
        return _maximum(*values) if values else 0.0

    def get_minimum_width(self):
        width = (self._cross_maximum(True) if self.container_mode == VERTICAL else
                 _sum_with_gaps(self._minimums(True, True), self.gap))
        return width+self.padding.left+self.padding.right if width > 0 else 0

    def get_minimum_height(self):
        height = (_sum_with_gaps(self._minimums(False, True), self.gap) if self.container_mode == VERTICAL else
                  self._cross_maximum(False))
        return height+self.padding.top+self.padding.bottom if height > 0 else 0

    def layout_children_horizontally(self):
        rect, padding = self.cell_rectangle, self.padding
        if self.container_mode == VERTICAL:
            x, width = rect.x+padding.left, rect.width-padding.left-padding.right
            for cell in self.cells: apply_horizontal_layout(cell, x, width)
        else:
            widths = self._minimums(True, False)
            apply_horizontal_layout(self.cells[BEGIN], rect.x+padding.left, widths[0])
            apply_horizontal_layout(self.cells[END], rect.x+rect.width-padding.right-widths[2], widths[2])
            free = rect.width-padding.left-padding.right
            if widths[0] > 0:
                free -= widths[0]+self.gap; widths[0] += self.gap
            if widths[2] > 0: free -= widths[2]+self.gap
            widths[1] = _maximum(widths[1], free)
            apply_horizontal_layout(self.cells[CENTER], rect.x+padding.left+widths[0]-(widths[1]-free)/2, widths[1])
        for cell in self.cells:
            if isinstance(cell, ContainerCell): cell.layout_children_horizontally()

    def layout_children_vertically(self):
        rect, padding = self.cell_rectangle, self.padding
        if self.container_mode == VERTICAL:
            heights = self._minimums(False, False)
            apply_vertical_layout(self.cells[BEGIN], rect.y+padding.top, heights[0])
            apply_vertical_layout(self.cells[END], rect.y+rect.height-padding.bottom-heights[2], heights[2])
            free = rect.height-padding.top-padding.bottom
            if heights[0] > 0:
                heights[0] += self.gap; free -= heights[0]
            if heights[2] > 0: free -= heights[2]+self.gap
            heights[1] = _maximum(heights[1], free)
            apply_vertical_layout(self.cells[CENTER], rect.y+padding.top+heights[0]-(heights[1]-free)/2, heights[1])
        else:
            y, height = rect.y+padding.top, rect.height-padding.top-padding.bottom
            for cell in self.cells: apply_vertical_layout(cell, y, height)
        for cell in self.cells:
            if isinstance(cell, ContainerCell): cell.layout_children_vertically()


class GridContainerCell(ContainerCell):
    def __init__(self, tabular=False, symmetrical=False, gap=0.0):
        super().__init__()
        self.cells = [[None]*3 for _ in range(3)]
        self.center_cell_rect = Rectangle()
        self.center_cell_minimum_size = None
        self.tabular = tabular; self.symmetrical = symmetrical; self.gap = gap
        self.only_center_cell_contributes_to_minimum_size = False

    def set_cell(self, row, col, cell):
        self.cells[row][col] = cell

    def get_cell(self, row, col):
        return self.cells[row][col]

    def set_center_cell_minimum_size(self, minimum_size):
        self.center_cell_minimum_size = Vec2(minimum_size.x, minimum_size.y)

    def _min_width_column(self, col, row, respect):
        width = 0.0
        if row is None:
            for i in range(3): width = _maximum(width, min_width_of_cell(self.cells[i][col], respect))
        else:
            width = min_width_of_cell(self.cells[row][col], respect)
        if col == CENTER and self.center_cell_minimum_size is not None:
            width = _maximum(width, self.center_cell_minimum_size.x)
        return width

    def _min_column_widths(self, row, respect):
        widths = [self._min_width_column(col, row, respect) for col in range(3)]
        if self.symmetrical:
            widths[0] = _maximum(widths[0], widths[2]); widths[2] = widths[0]
        return widths

    def _min_row_heights(self, respect):
        heights = []
        for row in range(3):
            height = 0.0
            for col in range(3): height = _maximum(height, min_height_of_cell(self.cells[row][col], respect))
            if row == CENTER and self.center_cell_minimum_size is not None:
                height = _maximum(height, self.center_cell_minimum_size.y)
            heights.append(height)
        if self.symmetrical:
            heights[0] = _maximum(heights[0], heights[2]); heights[2] = heights[0]
        return heights

    def get_minimum_width(self):
        width = 0.0
        if self.only_center_cell_contributes_to_minimum_size:
            if self.center_cell_minimum_size is not None: width = self.center_cell_minimum_size.x
            elif self.cells[1][1] is not None: width = self.cells[1][1].get_minimum_width()
        elif self.tabular:
            width = _sum_with_gaps(self._min_column_widths(None, True), self.gap)
        else:
            for row in range(3): width = _maximum(width, _sum_with_gaps(self._min_column_widths(row, True), self.gap))
        return width+self.padding.left+self.padding.right if width > 0 else 0

    def get_minimum_height(self):
        if self.only_center_cell_contributes_to_minimum_size:
            if self.center_cell_minimum_size is not None: height = self.center_cell_minimum_size.y
            elif self.cells[1][1] is not None: height = self.cells[1][1].get_minimum_height()
            else: height = 0.0
        else: height = _sum_with_gaps(self._min_row_heights(True), self.gap)
        return height+self.padding.top+self.padding.bottom if height > 0 else 0

    def _apply_width_column(self, col, x, widths):
        for row in range(3): apply_horizontal_layout(self.cells[row][col], x, widths[col])

    def _apply_height_row(self, row, y, heights):
        for col in range(3): apply_vertical_layout(self.cells[row][col], y, heights[row])

    def _apply_widths_to_row(self, row, widths):
        rect, padding = self.cell_rectangle, self.padding
        self._apply_width_column(BEGIN, rect.x+padding.left, widths)
        self._apply_width_column(END, rect.x+rect.width-padding.right-widths[2], widths)
        free = rect.width-padding.left-padding.right
        if widths[0] > 0:
            widths[0] += self.gap; free -= widths[0]
        if widths[2] > 0:
            widths[2] += self.gap; free -= widths[2]
        center_width = _maximum(0.0, free)
        widths[1] = _maximum(widths[1], free)
        self._apply_width_column(CENTER, rect.x+padding.left+widths[0]-(widths[1]-free)/2, widths)
        if row == CENTER:
            self.center_cell_rect.width = center_width
            self.center_cell_rect.x = rect.x+padding.left+(center_width-free)/2

    def layout_children_horizontally(self):
        if self.tabular:
            widths = self._min_column_widths(None, False)
            for row in range(3): self._apply_widths_to_row(row, widths)
        else:
            for row in range(3): self._apply_widths_to_row(row, self._min_column_widths(row, False))

    def layout_children_vertically(self):
        rect, padding = self.cell_rectangle, self.padding
        heights = self._min_row_heights(False)
        self._apply_height_row(BEGIN, rect.y+padding.top, heights)
        self._apply_height_row(END, rect.y+rect.height-padding.bottom-heights[2], heights)
        free = rect.height-padding.top-padding.bottom
        if heights[0] > 0:
            heights[0] += self.gap; free -= heights[0]
        if heights[2] > 0:
            heights[2] += self.gap; free -= heights[2]
        self.center_cell_rect.height = _maximum(0.0, free)
        self.center_cell_rect.y = rect.y+padding.top+(self.center_cell_rect.height-free)/2
        heights[1] = _maximum(heights[1], free)
        self._apply_height_row(CENTER, rect.y+padding.top+heights[0]-(heights[1]-free)/2, heights)


def _alignment(value, horizontal):
    if value is None:
        raise ValueError(('Horizontal' if horizontal else 'Vertical')+' alignment cannot be null')
    if isinstance(value, str):
        return (('LEFT', 'CENTER', 'RIGHT') if horizontal else ('TOP', 'CENTER', 'BOTTOM')).index(value)
    return int(value)


class LabelCell(Cell):
    """Source label group, deliberately not an AtomicCell.

    Labels carry mutable ``pos`` and ``size`` Vec2-compatible fields. This
    helper uses supplied dimensions and performs no text measurement.
    """
    def __init__(self, gap=0.0, node_label_location=None, horizontal_layout_mode=None):
        super().__init__()
        self.horizontal_alignment = CENTER; self.vertical_alignment = CENTER
        self.labels = []; self.minimum_content_area_size = Vec2(); self.gap = gap
        if isinstance(node_label_location, bool) and horizontal_layout_mode is None:
            self.horizontal_layout_mode = node_label_location
        else:
            self.horizontal_layout_mode = True if horizontal_layout_mode is None else horizontal_layout_mode
            if node_label_location is not None:
                self.horizontal_alignment = node_label_location.horizontal_alignment
                self.vertical_alignment = node_label_location.vertical_alignment

    def get_minimum_width(self):
        return self.minimum_content_area_size.x+self.padding.left+self.padding.right

    def get_minimum_height(self):
        return self.minimum_content_area_size.y+self.padding.top+self.padding.bottom

    def set_horizontal_alignment(self, value):
        _alignment(value, True)
        self.horizontal_alignment = value
        return self

    def set_vertical_alignment(self, value):
        _alignment(value, False)
        self.vertical_alignment = value
        return self

    def add_label(self, label):
        self.labels.append(label); size = label.size
        if self.horizontal_layout_mode:
            self.minimum_content_area_size.x = _maximum(self.minimum_content_area_size.x, size.x)
            self.minimum_content_area_size.y += size.y
            if len(self.labels) > 1: self.minimum_content_area_size.y += self.gap
        else:
            self.minimum_content_area_size.x += size.x
            self.minimum_content_area_size.y = _maximum(self.minimum_content_area_size.y, size.y)
            if len(self.labels) > 1: self.minimum_content_area_size.x += self.gap

    def apply_label_layout(self):
        rect, padding = self.cell_rectangle, self.padding
        horizontal = _alignment(self.horizontal_alignment, True)
        vertical = _alignment(self.vertical_alignment, False)
        if self.horizontal_layout_mode:
            y = rect.y
            if vertical == CENTER: y += (rect.height-self.minimum_content_area_size.y)/2
            elif vertical == END: y += rect.height-self.minimum_content_area_size.y
            for label in self.labels:
                if horizontal == BEGIN: x = rect.x+padding.left
                elif horizontal == CENTER: x = rect.x+padding.left+(rect.width-label.size.x)/2
                else: x = rect.x+rect.width-padding.right-label.size.x
                label.pos.x, label.pos.y = x, y
                y += label.size.y+self.gap
        else:
            x = rect.x
            if horizontal == CENTER: x += (rect.width-self.minimum_content_area_size.x)/2
            elif horizontal == END: x += rect.width-self.minimum_content_area_size.x
            for label in self.labels:
                if vertical == BEGIN: y = rect.y+padding.top
                elif vertical == CENTER: y = rect.y+padding.top+(rect.height-label.size.y)/2
                else: y = rect.y+rect.height-padding.bottom-label.size.y
                label.pos.x, label.pos.y = x, y
                x += label.size.x+self.gap
