# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# HOST18/root/simple-placement-source-review-01.
"""Actual two-pass Simple node placement over current native graph geometry."""
from .graph_info import get_graph_properties
from ...execution.diagnostics import BasicProgressMonitor
from ..radial import _maximum


_HIERARCHY_CONFIGURATION=None


def _configuration():
    global _HIERARCHY_CONFIGURATION
    if _HIERARCHY_CONFIGURATION is None:
        from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy
        _HIERARCHY_CONFIGURATION=LayoutProcessorConfiguration()
        _HIERARCHY_CONFIGURATION.add_before(tuple(LayeredPhase)[4],
                                            IntermediateProcessorStrategy.HIERARCHICAL_PORT_POSITION_PROCESSOR)
    return _HIERARCHY_CONFIGURATION


class SimpleNodePlacer:
    source_name='SimpleNodePlacer'

    def __init__(self):_configuration()

    def get_layout_processor_configuration(self,graph):
        return _configuration()if'EXTERNAL_PORTS'in get_graph_properties(graph)else None

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Simple node placement',1)
        # Actual bare property may be null. Only an adjacent node pair reaches
        # the original Spacings dereference; empty/singleton layers do not.
        spacings=graph.properties.get('SPACINGS')
        maximum_height=0.0
        for layer in graph.layers:
            layer.size.y=0.0
            previous=None
            for node in layer.nodes:
                if previous is not None:layer.size.y+=spacings.get_vertical_spacing_nodes(node,previous)
                layer.size.y+=node.margin.top+node.size.y+node.margin.bottom
                previous=node
            maximum_height=_maximum(maximum_height,layer.size.y)
        for layer in graph.layers:
            position=(maximum_height-layer.size.y)/2
            previous=None
            for node in layer.nodes:
                if previous is not None:position+=spacings.get_vertical_spacing_nodes(node,previous)
                position+=node.margin.top
                node.pos.y=position
                position+=node.size.y+node.margin.bottom
                previous=node
        monitor.done()
