# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 SemiInteractiveCrossMinProcessor41933-42010.
"""Position-based actual normal-node successor constraints."""
from ...execution.diagnostics import BasicProgressMonitor
from .ports import _source_sort, double_compare
from .north_south_ports import _successors


def semi_interactive_crossmin_processor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Semi-Interactive Crossing Minimization Processor', 1)
    added = False
    for layer in graph.layers:
        nodes = [node for node in layer.nodes
                 if node.type == 'NORMAL' and 'POSITION' in node.properties]
        _source_sort(nodes, lambda first, second: double_compare(
            first.properties.get('POSITION').y, second.properties.get('POSITION').y))
        previous = None
        for current in nodes:
            if previous is not None:
                _successors(previous).append(current)
            previous = current
        # Source reduce presence, including a one-node result, sets this flag.
        added = bool(added | (previous is not None))
    if added:
        graph.properties['IN_LAYER_SUCCESSOR_CONSTRAINTS_BETWEEN_NON_DUMMIES'] = True
    monitor.done()
