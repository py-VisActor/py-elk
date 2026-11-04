# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P19B hierarchy controller source.
"""Actual bottom-up graph iterators and concrete hierarchy-aware sweep barrier.

Compound preprocessing/postprocessing are required real callbacks. The existing
flat provider remains unchanged until those algorithms are connected.
"""
from collections import deque

from ..._errors import UnsupportedFeatureError
from ...execution.diagnostics import BasicProgressMonitor
from .diagnostic_strings import layer_text, node_list_text
from .layer_sweep import LayerSweepCrossingMinimizer
from .property_access import read_layered_scalar


def graph_text(graph):
    state = getattr(graph, '_source_session', None)
    nodes = lambda: node_list_text(graph.layerless_nodes, state)
    layers = lambda: '[' + ', '.join('null' if layer is None else layer_text(layer, state)
                                   for layer in graph.layers) + ']'
    if len(graph.layers) == 0:
        return 'G-unlayered' + nodes()
    if len(graph.layerless_nodes) == 0:
        return 'G-layered' + layers()
    return 'G[layerless' + nodes() + ', layers' + layers() + ']'


def collect_all_graphs_bottom_up(root):
    collected = deque((root,))
    pending = deque((root,))
    while pending:
        graph = pending.popleft()
        for node in graph.layerless_nodes:
            nested = getattr(node, 'nested_graph', None)
            if nested is not None:
                collected.appendleft(nested)
                pending.appendleft(nested)
    return collected


class _ProcessorCursor:
    """The reached ArrayList iterator protocol over the actual live list."""
    def __init__(self, processors):
        self.processors = processors
        self.index = 0

    def has_next(self):
        return self.index < len(self.processors)

    def next(self):
        processor = self.processors[self.index]
        self.index += 1
        return processor


def hierarchical_layout(provider, graph, monitor):
    graphs = collect_all_graphs_bottom_up(graph)
    parent_strategy = read_layered_scalar(
        graph, 'CROSSING_MINIMIZATION_STRATEGY', 'CROSSING_MINIMIZATION_STRATEGY_0')
    for current in graphs:
        strategy = read_layered_scalar(
            current, 'CROSSING_MINIMIZATION_STRATEGY', 'CROSSING_MINIMIZATION_STRATEGY_0')
        if strategy != parent_strategy:
            name = 'null' if strategy is None else str(strategy)
            raise UnsupportedFeatureError('UNSUPPORTED_GRAPH', '',
                'The hierarchy aware processor ' + name + ' in child node ' + graph_text(current)
                + ' is only allowed if the root node specifies the same hierarchical processor.')
    root_type = read_layered_scalar(graph, 'CROSSING_MINIMIZATION_GREEDY_SWITCH_HIERARCHICAL_TYPE',
                                    'CROSSING_MINIMIZATION_GREEDY_SWITCH_HIERARCHICAL_TYPE_0')
    for current in graphs:
        current.properties['CROSSING_MINIMIZATION_GREEDY_SWITCH_HIERARCHICAL_TYPE'] = root_type
    work = 0.0
    graph_algorithms = []
    for current in graphs:
        provider.graph_configurator.prepare_graph_for_layout(current)
        processors = current.properties['PROCESSORS']
        work += len(processors)
        graph_algorithms.append((current, _ProcessorCursor(processors)))
    monitor.begin('Recursive hierarchical layout', work)
    root_processors = graph_algorithms[-1][1]
    slot_index = 0
    while root_processors.has_next():
        for current, processors in graph_algorithms:
            while processors.has_next():
                processor = processors.next()
                if isinstance(processor, LayerSweepCrossingMinimizer):
                    if getattr(current, 'parent_node', None) is None:
                        processor.process(current, monitor.sub_task(1))
                        slot_index += 1
                    break
                processor.process(current, monitor.sub_task(1))
                slot_index += 1
    monitor.done()


def do_compound_layout(provider, graph, monitor=None, *, preprocessor, postprocessor):
    the_monitor = monitor
    if the_monitor is None:
        the_monitor = BasicProgressMonitor()
        the_monitor._max_levels = 0
    the_monitor.begin('Layered layout', 2)
    preprocessor.process(graph, monitor=the_monitor.sub_task(1))
    hierarchical_layout(provider, graph, the_monitor.sub_task(1))
    postprocessor(graph, monitor=the_monitor.sub_task(1))
    the_monitor.done()
