# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P14A in references/e13-kernel-sources.json.
"""Actual lazy ordered pair matrix backed by the real TwoNode counter."""
from .two_node_crossings import BetweenLayerEdgeTwoNodeCrossingsCounter


class CrossingMatrixFiller:
    def __init__(self, greedy_switch_type, graph, free_layer_index, direction):
        self.direction = direction
        self.one_sided = greedy_switch_type == 'ONE_SIDED_GREEDY_SWITCH'
        # A negative JS array property is undefined, never Python's last row.
        free_layer = graph[free_layer_index] if free_layer_index >= 0 else None
        self.is_crossing_matrix_filled = [[False for _ in free_layer] for _ in free_layer]
        self.crossing_matrix = [[0.0 for _ in free_layer] for _ in free_layer]
        self.in_between_layer_crossing_counter = BetweenLayerEdgeTwoNodeCrossingsCounter(graph, free_layer_index)

    def fill_crossing_matrix(self, upper, lower):
        counter = self.in_between_layer_crossing_counter
        if self.one_sided:
            if self.direction == 1:
                counter.count_eastern_edge_crossings(upper, lower)
            elif self.direction == 0:
                counter.count_western_edge_crossings(upper, lower)
        else:
            counter.count_both_side_crossings(upper, lower)
        self.crossing_matrix[upper.id][lower.id] = counter.upper_lower_crossings
        self.crossing_matrix[lower.id][upper.id] = counter.lower_upper_crossings

    def get_crossing_matrix_entry(self, upper, lower):
        if not self.is_crossing_matrix_filled[upper.id][lower.id]:
            self.fill_crossing_matrix(upper, lower)
            self.is_crossing_matrix_filled[upper.id][lower.id] = True
            self.is_crossing_matrix_filled[lower.id][upper.id] = True
        return self.crossing_matrix[upper.id][lower.id]
