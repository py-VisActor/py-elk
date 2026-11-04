# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# elkjs0.12.1 worker275e6caf, 55426-55480.
"""Interactive placement preserving original dummy positions and type spacing."""
import math
from ...execution.diagnostics import BasicProgressMonitor
from .graph_info import get_graph_properties
from .port_distribution import _maximum

_HIERARCHY_CONFIGURATION = None


def hierarchy_configuration():
    global _HIERARCHY_CONFIGURATION
    if _HIERARCHY_CONFIGURATION is None:
        from .layout_configuration import LayoutProcessorConfiguration, LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy
        _HIERARCHY_CONFIGURATION = LayoutProcessorConfiguration()
        _HIERARCHY_CONFIGURATION.add_before(tuple(LayeredPhase)[4],
            IntermediateProcessorStrategy.HIERARCHICAL_PORT_POSITION_PROCESSOR)
    return _HIERARCHY_CONFIGURATION


class InteractiveNodePlacer:
    source_name = 'InteractiveNodePlacer'

    def __init__(self):
        hierarchy_configuration()
        self.spacings = None

    def get_layout_processor_configuration(self, graph):
        return hierarchy_configuration() if 'EXTERNAL_PORTS' in get_graph_properties(graph) else None

    def place_nodes(self, layer):
        minimum = -math.inf
        previous_type = 'NORMAL'
        for node in layer.nodes:
            kind = node.type
            if kind != 'NORMAL':
                original = node.properties.get('ORIGINAL_DUMMY_NODE_POSITION')
                if original is None:
                    minimum = _maximum(minimum, 0.0)
                    node.pos.y = minimum + self.spacings.get_vertical_spacing(kind, previous_type)
                else:
                    node.pos.y = original
            spacing = self.spacings.get_vertical_spacing(kind, previous_type)
            threshold = minimum + spacing + node.margin.top
            if node.pos.y < threshold: node.pos.y = threshold
            minimum = (node.pos.y + node.size.y) + node.margin.bottom
            previous_type = kind

    def process(self, graph, monitor=None):
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('Interactive node placement', 1)
        self.spacings = graph.properties.get('SPACINGS')
        for layer in graph.layers: self.place_nodes(layer)
        monitor.done()
