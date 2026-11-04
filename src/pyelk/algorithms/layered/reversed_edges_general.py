# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf $process_46 41550-41568.
"""Actual unrestricted reversed-edge restoration and per-port snapshots."""
from ...execution.diagnostics import BasicProgressMonitor
from .cycles_general import reverse_edge


def reversed_edge_restorer(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Restoring reversed edges', 1)
    for layer in graph.layers:
        for node in layer.nodes:
            for port in node.ports:
                edges = list(port.outgoing_edges)
                for edge in edges:
                    reversed_value = edge.properties.get('REVERSED')
                    if reversed_value is None:
                        reversed_value = False
                    if type(reversed_value) is not bool:
                        raise TypeError('Actual InternalProperties.REVERSED Boolean required')
                    if reversed_value:
                        reverse_edge(edge, False)
    monitor.done()
